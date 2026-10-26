#!/usr/bin/env python3
"""Render maps, elevation profiles, glyphs and tiles for the site into rendered/.

  python3 tools/render.py                 # everything that changed since the last render
  python3 tools/render.py SLUG [SLUG …]   # just these trips (region maps are refreshed too)
  python3 tools/render.py --site          # only the region / section overview maps
  python3 tools/render.py --force …       # ignore the change check
  python3 tools/render.py --status [SLUG …]   # what a run would draw and why; offline, draws nothing (exit 1: something to draw)
  python3 tools/render.py --list      # the same as --status
  python3 tools/render.py --jobs 2 --budget 3600   # a full re-render after a VERSION bump: run it again until nothing is
                                      # pending (it resumes through the hashes), then --site (docs/DEVELOPING.md)

Needs the internet (AWS Terrain Tiles + OpenStreetMap Overpass); downloads are cached in
~/Library/Caches/personal-website/ (lib/geo.py). Outputs are committed, so the GitHub Action never has to render anything.
A trip whose render fails keeps its last good maps, the run goes on with the others, and it ends with exit status 1.
Every meta.json records what drew it (meta['renderer']: VERSION, Python, cwebp, the day, whether OpenStreetMap came from
the cache); a run stops before drawing when cwebp is missing (--allow-png draws all the same, with PNG hillshades).
A tick-list goal whose GPX has no elevation, or only some, also gets meta['terrain']: its gain, loss, high and low
estimated from the terrain tiles along the line (terrain_block); a goal drawn before that gets the estimate alone.
"""
import argparse
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import fit_reader  # noqa: E402
import geo  # noqa: E402
import gpxroute  # noqa: E402
import mapkit  # noqa: E402
import renderkey  # noqa: E402
from mapkit import Track, render_map, render_profile, render_glyph, render_tile, render_sparkline, render_speed_chart  # noqa: E402
# the input hashes (and the rules they need) live in lib/renderkey.py, where the content checks read them too
from renderkey import VERSION, MIN_REGION_TRIPS, file_hash, trip_inputs, no_route, no_track, journal_parts, terrain_reason  # noqa: E402,F401
from sitegen.sitecheck import conflict_copy  # noqa: E402

MI, FT = geo.MI, geo.FT
OUT = os.path.join(ROOT, 'rendered')

REPORT = dict(legend=False, north=False, graticule=False, miles=True, chevrons=False, startend=True, gpsmax=True,
              png_scale=1.25, contour_density=0.75, peaks_max=3, trim=False)
SMALL = dict(road_levels=('motorway', 'trunk', 'primary', 'secondary', 'tertiary'), small_markers=True, gps_label='name', north=False,
             places_allow=[], skin=False, legend=False, miles=False, chevrons=False, startend=True, gpsmax=True,
             png_scale=2.0, contour_density=0.9, peaks_max=0, graticule=False, contour_labels=False, trails=False,
             track_eps=1.2, prio_avoid_track=True, trim=False)
OVERVIEW = dict(north=False, png_scale=1.5, graticule=False, contour_density=1.2, contour_labels=False, peaks_max=0, trails=False,
                poly_eps=0.8, min_water_px=40, road_levels=('motorway', 'trunk', 'primary'), places_max=3,
                places_by_rank=True, places_near_pins=140, overview_labels=True, cluster_px=26, miles=False, chevrons=False,
                startend=False, gpsmax=False, trim=False)


# ---------------------------------------------------------------- helpers

def cwebp_version():
    """The first line of `cwebp -version`, or None when cwebp is not installed."""
    if not shutil.which('cwebp'):
        return None
    try:
        out = subprocess.run(['cwebp', '-version'], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return (out.strip().splitlines() or [None])[0]


def osm_fetches():
    """Downloads so far: geo's own count plus each map served from a pool area this run downloaded (prefetch_osm), which
    geo counted once, in the parent, before any trip began."""
    return geo.CACHE['osm_miss'] + POOL_FETCHED[0]


def renderer_record(osm_before):
    """meta['renderer'] (gap9-05): which renderer, Python and cwebp drew a folder, on which day, and whether its
    OpenStreetMap data came from the cache, was fetched, or is missing (osm_fetches() since osm_before). Versions and a
    day: nothing about a trip."""
    osm = 'missing' if OSM_FAILED else ('fetched' if osm_fetches() > osm_before else 'cached')
    return {'version': VERSION, 'python': platform.python_version(), 'cwebp': cwebp_version(),
            'date': date.today().isoformat(), 'osm': osm}


# cwebp's quality for every hillshade (perf-05), chosen from a side-by-side at 1x and 2x before a round: in 2026 q88, q80
# and q75 looked the same at both, and q80 came out 29 to 35% smaller than q88 (docs/DEVELOPING.md, "A render round")
HILLSHADE_Q = 80


def optimize_images(folder, meta):
    """Hillshade PNGs -> WebP at HILLSHADE_Q (-m 6: the slowest, smallest method). Keeps the PNG only if cwebp is
    missing (and main() draws nothing then without --allow-png)."""
    if not shutil.which('cwebp'):
        return
    for f in sorted(os.listdir(folder)):
        if not f.endswith('.png'):
            continue
        src = os.path.join(folder, f)
        dst = src[:-4] + '.webp'
        subprocess.run(['cwebp', '-quiet', '-q', str(HILLSHADE_Q), '-m', '6', src, '-o', dst], check=True)
        os.remove(src)
    for m in meta.get('maps', {}).values():
        if m.get('png', '').endswith('.png'):
            m['png'] = m['png'][:-4] + '.webp'


def set_out(folder):
    os.makedirs(folder, exist_ok=True)
    mapkit.FRAG = folder
    mapkit.MAPPNG = folder


def load_track(path, key, cat, stats=None):
    pts = fit_reader.read_gpx(path)
    tr = Track(pts, key, cat)
    if stats and stats.get('distance_km') and tr.total > 0:
        f = stats['distance_km'] * 1000.0 / tr.total  # align mile markers with the published distance
        tr.cd = [d * f for d in tr.cd]
        tr.total = tr.cd[-1]
    if stats and stats.get('high_m'):
        tr.label_max_m = stats['high_m']  # GPS-max label matches the stats strip
    return tr


def frame_bbox(spec, tracks):
    """The lat/lon frame render_map will use (mirrors its bbox logic) — for one shared OSM download."""
    pts = [[(p[0], p[1]) for p in t['track'].raw] for t in tracks]
    if spec.get('pins'):
        pts.append([(pn['lat'], pn['lon']) for pn in spec['pins']])
    bbox = spec.get('bbox') or geo.bbox_of(pts)
    proj = geo.Proj(bbox, spec['w'], spec['h'], pad=spec.get('pad', 0.12))
    min_m = spec.get('min_extent_m')
    if min_m and proj.m_per_px * min(spec['w'], spec['h']) < min_m:
        s, w, n, e = bbox
        clat, clon = (s + n) / 2, (w + e) / 2
        hl = min_m / 2 / geo.M_PER_DEG_LAT
        hn = min_m / 2 / (geo.M_PER_DEG_LON_EQ * math.cos(math.radians(clat)))
        proj = geo.Proj((clat - hl, clon - hn, clat + hl, clon + hn), spec['w'], spec['h'], pad=0.0)
    return proj.bounds(margin=40)


def union(bbs):
    return (min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs))


CARD_W, CARD_H = 400, 267   # the card drawing (visual-01 step 2; core.GLYPH_SIZES['card'])
CARD_LINE = 3.5              # its line: the tile's 2.5 at twice the size would read thin in a 3:2 card slot
PANEL_WORDS = {'ski': 'ski', 'mtb': 'mountain bike', 'hike': 'hiking'}   # a panel map's alt text: 'Map of hiking trips in X'
OSM_FAILED = []
OSM_POOL = []  # (bbox, detail, data, fetched): larger areas fetched once and shared by every map inside them
POOL_FETCHED = [0]  # maps served from a pool area that this run downloaded rather than read from the cache


def _contains(outer, inner):
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def prefetch_osm(trips):
    """Group pending trips into ~15 km cells and fetch each cell's OpenStreetMap data once (report detail)."""
    cells = {}
    for t in trips:
        paths = [t['track']] if t['track'] else [d['track'] for d in t['days'] if d['track']]
        pts = []
        for p in paths:
            pts += [(q[0], q[1]) for q in fit_reader.read_gpx(p)][::5]
        if not pts:
            continue
        s_, w_, n_, e_ = geo.bbox_of([pts])
        lat_c, lon_c = (s_ + n_) / 2, (w_ + e_) / 2
        kx = math.cos(math.radians(lat_c))
        half_h = max(n_ - s_, (e_ - w_) * kx / 1.16, 0.012) * 0.75   # covers the phone (tall) frame
        half_w = max(e_ - w_, (n_ - s_) / kx * 2.25, 0.02) * 0.75    # covers the wide (1440×640) frame
        bb = (lat_c - half_h, lon_c - half_w, lat_c + half_h, lon_c + half_w)
        key = (round(lat_c / 0.12), round(lon_c / 0.16))
        cells.setdefault(key, []).append(bb)
    for key, bbs in sorted(cells.items(), key=lambda kv: -len(kv[1])):
        if len(bbs) < 2:
            continue
        u = union(bbs)
        if (u[2] - u[0]) > 0.4 or (u[3] - u[1]) > 0.5:
            continue  # too big to be worth sharing; those trips fetch their own
        t0 = time.time()
        before = geo.CACHE['osm_miss']
        data = fetch_osm(u, 'report', pooled=False)
        if data:
            OSM_POOL.append((u, 'report', data, geo.CACHE['osm_miss'] > before))
            print('  prefetched OSM for %d trips around %.3f,%.3f in %.0fs' % (len(bbs), (u[0] + u[2]) / 2, (u[1] + u[3]) / 2, time.time() - t0), flush=True)


def fetch_osm(bbox, detail, pooled=True):
    if pooled:
        for pb, pd, data, fetched in OSM_POOL:
            if pd == detail and _contains(pb, bbox):
                POOL_FETCHED[0] += fetched
                return data
    for attempt in range(3):
        try:
            return geo.osm_layers(bbox, detail)
        except Exception as ex:  # noqa: BLE001 — maps still render with terrain only
            err = str(ex)[:80]
            time.sleep(10 * (attempt + 1))
    print('  ! OSM download failed (%s); rendered terrain only — run render.py again later' % err)
    OSM_FAILED.append(bbox)
    return None


def extent_m(tracks):
    bb = geo.bbox_of([[(p[0], p[1]) for p in t.raw] for t in tracks])
    return geo.hav((bb[0], bb[1]), (bb[2], bb[3]))


def fmt_int(v):
    return '{:,}'.format(int(round(v)))


def aria_for(t, what='Map'):
    st = t['stats']
    bits = []
    if st.get('distance_km'):
        bits.append('%.1f miles' % (st['distance_km'] * 1000 / MI))
    if st.get('high_m'):
        bits.append('high point %s ft' % fmt_int(st['high_m'] * FT))
    shape = (t.get('route_shape') or '').replace('-', ' ')
    return '%s of %s%s%s' % (what, t['title'], (', ' + shape) if shape else '', (', ' + ', '.join(bits)) if bits else '')


def water_labels(opt, w, h):
    """map.water_labels: [{text, x, y}] with x/y as fractions of the map size (for lakes bigger than the frame)."""
    return [(o['x'] * w, o['y'] * h, o['text']) for o in (opt or []) if isinstance(o, dict)]


# ---------------------------------------------------------------- per trip

def is_flat(t):
    """Flat water — the same rule as core.is_flat: a paddling sub-type (SUP, Kayaking), or an 'other' trip with under
    30 m of relief (high minus low). Flat water gets speed charts instead of a profile and the flat map framing; rafting
    (moving water, real relief) keeps its profile."""
    if t['activity'] != 'other':
        return False
    st = t['stats']
    return t.get('subtype') in ('SUP', 'Kayaking') or ((st.get('high_m') or 0) - (st.get('low_m') or 0)) < 30


def planned_tracks(t):
    """A tick-list goal's line as one Track per segment (gpxroute.as_tracks: routes and tracks alike, gaps never bridged),
    so a two-part plan is drawn as two parts."""
    return gpxroute.as_tracks(t['track'], t['slug'], t['cat'])


TERRAIN_SOURCE = 'AWS Terrain Tiles'


def terrain_block(t):
    """meta['terrain'] for a goal whose published file has no elevation, or only some (renderkey.wants_terrain): the
    approximate gain, loss, high and low of the ground under its line, read from AWS Terrain Tiles at
    gpxroute.TERRAIN_ZOOM along every segment, gaps never bridged (gpxroute.measure_terrain), with the method, source,
    zoom, sample step, the file's own elevation ('none' or 'partial') and the day. None for every other trip. The
    build shows these values marked as terrain estimates and only where the file has none; index.md's stats stay the
    numbers measured from the file."""
    if not renderkey.wants_terrain(t):
        return None
    segs = [seg for c in gpxroute.candidates(gpxroute.inspect(t['track'])) for seg in c['segments']]
    got = gpxroute.measure_terrain(segs, geo.DEM(gpxroute.TERRAIN_ZOOM).sample)
    if got is None:
        return None
    return dict(got, method=gpxroute.TERRAIN_METHOD, source=TERRAIN_SOURCE, zoom=gpxroute.TERRAIN_ZOOM,
                step_m=gpxroute.TERRAIN_STEP_M, file_elevation=renderkey.file_elevation(t), date=date.today().isoformat())


def add_terrain(t, mf):
    """A goal whose maps are up to date but whose meta.json lacks its terrain estimate (renderkey.terrain_reason: drawn
    before render.py made one, or by an older method): the estimate alone is made and meta.json rewritten in place
    (written beside it, then renamed over it), every map left as it is. True when it was written."""
    if not renderkey.wants_terrain(t):
        return False
    try:
        with open(mf, encoding='utf-8') as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        return False
    if not isinstance(meta, dict) or not terrain_reason(t, meta):
        return False
    t0 = time.time()
    block = terrain_block(t)
    if block is None:
        return False
    meta['terrain'] = block
    tmp = '%s.tmp-%d' % (mf, os.getpid())
    with open(tmp, 'w') as fh:
        json.dump(meta, fh, indent=1, default=str)
    os.replace(tmp, mf)
    print('terrain  %-40s %5.0fs  (≈ %d m gain, maps unchanged)' % (t['slug'], time.time() - t0, block['gain_m']))
    return True


def render_single(t, meta):
    act, cat = t['activity'], t['cat']
    planned = t['kind'] == 'planned'
    if planned:
        trs = planned_tracks(t)
        if not trs:
            raise ValueError('%s: the planned GPX has no track or route points to draw' % t['slug'])
        tr = trs[0]
    else:
        trs = None
        tr = load_track(t['track'], t['slug'], cat, t['stats'])
    mo = t['map']
    peaks = mo.get('peaks') or []
    small = extent_m(trs or [tr]) < 3000
    flat = is_flat(t)
    style = 'planned' if planned else 'route'
    base = {}
    if small:
        base.update(min_extent_m=1000 if flat else 1400, hs_zoom=15)
    if flat:
        base.update(gpsmax=False, miles=False, water_labels=6)
    if planned:
        base.update(gpsmax=False, miles=False, chevrons=False, startend=True)
    aria = aria_for(t)
    # a tall route (its track box over renderkey.TALL to 1) gets a taller wide and column frame; the phone map keeps its
    # own (maps-03). meta.json records each map's size, and core.map_block takes it from there
    wh, ch = (800, 500) if renderkey.report_frame(t) == 'tall' else (640, 400)
    specs = [
        dict(REPORT, **base, name='map-wide', w=1440, h=wh, skin=(act == 'ski'), peaks_max=2, priority_peaks=peaks,
             places_allow=mo.get('places'), extra_water_labels=water_labels(mo.get('water_labels'), 1440, wh), aria=aria),
        dict(REPORT, **base, name='map-col', w=718, h=ch, png_scale=2.0, skin=(act == 'ski'), peaks_max=2, priority_peaks=peaks,
             places_allow=mo.get('places'), extra_water_labels=water_labels(mo.get('water_labels'), 718, ch), aria=aria),
        dict(SMALL, **{k: v for k, v in base.items() if k not in ('water_labels',)}, name='map-phone', w=390, h=336, scale_corner='bl',
             priority_peaks=peaks, reserve=[(0, 0, 60, 60), (390 - 208, 336 - 36, 390, 336)], pad_bottom_px=40, aria=aria),
    ]
    drawn = trs or [tr]
    trks = [{'track': x, 'style': style} for x in drawn]
    osm = fetch_osm(union([frame_bbox(s, trks) for s in specs]), 'report')
    for s in specs:
        s['tracks'] = [{'track': x, 'style': style, 'width': 3} for x in drawn]
        s['osm_data'] = osm
        m = render_map(s)
        meta['maps'][s['name']] = {'w': s['w'], 'h': s['h'], 'png': m.get('png'), 'base': m.get('base'), 'interval_ft': m.get('interval_ft'),
                                   'outbound_only': m.get('outbound_only'), 'base_gz_kb': m.get('base_gz_kb')}
    single_charts(t, meta, tr)
    if planned:
        terrain = terrain_block(t)
        if terrain:
            meta['terrain'] = terrain
    multi = [{'track': x, 'style': 'planned', 'cat': cat, 'width': 2.5, 'trim': mapkit.DEFAULT_TRIM} for x in drawn] if len(drawn) > 1 else None
    render_tile('tile', tr, 200, 152, cat, osm_detail=None, osm_data=osm, planned=planned, tracks=multi)
    # the card drawing (visual-01 step 2): a card's 3:2 slot without a photo, its line drawn for that size
    render_tile('card', tr, CARD_W, CARD_H, cat, osm_detail=None, osm_data=osm, planned=planned, width=CARD_LINE, tiny_disc=7,
                tracks=[dict(x, width=CARD_LINE) for x in multi] if multi else None)
    render_glyph('g112', drawn if len(drawn) > 1 else tr, 112, 64, cat, planned=planned)
    render_glyph('g64', drawn if len(drawn) > 1 else tr, 64, 48, cat, planned=planned, pad=5)
    meta['start'] = drawn[0].raw[0][:2]
    meta['end'] = drawn[-1].raw[-1][:2]
    meta['bbox'] = geo.bbox_of([[(p[0], p[1]) for x in drawn for p in x.raw]])


def axis_step(total_mi, w):
    """Mile-tick spacing (mapkit.axis_step): labels >= 56 px apart for sub-mile steps ('0 mi · 0.25 · 0.5'), >= 36 px
    otherwise (the first label reads "0 mi"; on phone charts, which have no y-axis gutter, the last one carries the unit)."""
    return mapkit.axis_step(total_mi, w)


def single_charts(t, meta, tr=None):
    act = t['activity']
    tr = tr or load_track(t['track'], t['slug'], t['cat'], t['stats'])
    flat = is_flat(t)
    if t['kind'] == 'planned':
        return
    if flat and any(p[3] for p in tr.raw):
        for nm, w, h in (('speed-wide', 1248, 112), ('speed-col', 718, 112), ('speed-phone', 358, 96)):
            info = render_speed_chart(nm, tr, w, h)
            meta['charts'][nm] = {'w': w, 'h': h, 'kind': 'speed', 'info': info}
        return
    if not tr.ele:
        return
    tot = tr.total / MI
    for nm, w, ph in (('profile-wide', 1248, 140), ('profile-col', 718, 110), ('profile-phone', 358, 100)):
        info = render_profile(nm, [tr], w, ph, dict(skin=(act == 'ski'), grade=False, axis_every_mi=axis_step(tot, w),
                                                    aria='Elevation profile of ' + t['title']))
        meta['charts'][nm] = dict({'w': w, 'kind': 'profile'}, **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in info.items()})


def day_gaps(days, trs):
    """Days that start somewhere else (> 500 m from the previous day's end) with no content transfer before them: separate
    crags, lesson sites, trailheads. The stitched profile breaks there (a plain divider, no TRANSFER)."""
    return [i for i in range(1, len(trs)) if not days[i]['transfer_before'] and trs[i - 1].raw and trs[i].raw
            and geo.hav(trs[i - 1].raw[-1][:2], trs[i].raw[0][:2]) > 500]


def multi_charts(t, meta, trs=None):
    days = t['days']
    trs = trs or [load_track(d['track'], '%s-%s' % (t['slug'], d['id']), t['cat'], d['stats']) for d in days]
    transfers = [(i - 1, i) for i, d in enumerate(days) if d['transfer_before'] and i > 0]
    gaps = day_gaps(days, trs)
    ski = t['activity'] == 'ski'
    tot = sum(tr.total for tr in trs) / MI
    for nm, w, phh in (('profile-wide', 1248, 140), ('profile-col', 718, 120), ('profile-phone', 358, 110)):
        info = render_profile(nm, trs, w, phh, dict(skin=False, day_tints=True, day_band=True, grade=False, transfers=transfers,
                                                     gaps=gaps, label_every_ft=4000, axis_every_mi=axis_step(tot, w),
                                                     aria='Stitched elevation profile of all %d days' % len(trs)))
        meta['charts'][nm] = dict({'w': w, 'kind': 'profile'}, **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in info.items()})
    for d, tr in zip(days, trs):
        for nm, w, phh in (('day-%s-profile-col' % d['id'], 718, 96), ('day-%s-profile-phone' % d['id'], 358, 88)):
            info = render_profile(nm, [tr], w, phh, dict(skin=ski, grade=False, label_every_ft=2000, axis_every_mi=axis_step(tr.total / MI, w),
                                                          aria='Elevation profile of day %s' % d['label']))
            meta['charts'][nm] = dict({'w': w, 'kind': 'profile'}, **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in info.items()})


def render_multi(t, meta):
    cat = t['cat']
    days = t['days']
    trs = [load_track(d['track'], '%s-%s' % (t['slug'], d['id']), cat, d['stats']) for d in days]
    mo = t['map']
    transfers = [(i - 1, i) for i, d in enumerate(days) if d['transfer_before'] and i > 0]
    hi_day = max(range(len(days)), key=lambda i: days[i]['stats'].get('high_m') or 0)

    no_huts = not any(d['hut'] for d in days)

    def ov_tracks(huts=True):
        out = []
        for i, tr in enumerate(trs):
            e = {'track': tr, 'style': 'route', 'trim': False, 'day_label': i + 1, 'i0': 0, 'i1': len(tr.raw) - 1}
            # every day ends on its numbered square; with huts the last day ends at the trip's end instead
            if huts and (i < len(trs) - 1 or no_huts):
                e['hut_end'] = {'n': i + 1, 'label': days[i]['hut']}
            if huts and i == hi_day:
                e['gpsmax'] = True
            out.append(e)
        return out
    ov = dict(REPORT, pad=0.10, poly_eps=0.6, min_water_px=30, road_levels=('motorway', 'trunk', 'primary', 'secondary', 'tertiary'),
              miles=False, chevrons=False, startend=False, gpsmax=False, graticule=False, contour_density=1.0, peaks_max=3,
              trails=False, priority_peaks=mo.get('peaks'), places_allow=mo.get('places'), transfers=transfers,
              water_near_track=40, bands_off=True, overall_startend=True, aria=aria_for(t))
    specs = [dict(ov, name='overview-wide', w=1440, h=560, png_scale=1.25),
             dict(ov, name='overview-col', w=718, h=440, png_scale=2.0, peaks_max=1)]
    osm_ov = fetch_osm(union([frame_bbox(s, ov_tracks()) for s in specs]), 'overview')
    for s in specs:
        s['tracks'] = ov_tracks()
        s['osm_data'] = osm_ov
        m = render_map(s)
        meta['maps'][s['name']] = {'w': s['w'], 'h': s['h'], 'png': m.get('png'), 'base': m.get('base'), 'base_gz_kb': m.get('base_gz_kb')}
    # the phone overview numbers each day's end as the wide one does (maps-05), without the hut names; the squares keep clear
    # of the scale bar (bottom left) and the credit tag (bottom right)
    ph_tracks = [dict(e, hut_end=({'n': e['hut_end']['n']} if e.get('hut_end') else None), gpsmax=False) for e in ov_tracks()]
    ph = dict(SMALL, name='overview-phone', w=390, h=260, pad=0.12, places_allow=[], day_labels=False, poly_eps=1.2, min_water_px=40,
              road_levels=('motorway', 'trunk', 'primary'), tracks=ph_tracks,
              miles=False, chevrons=False, startend=False, gpsmax=False, overall_startend=True, transfers=transfers, peaks_max=0,
              bands_off=True, priority_peaks=mo.get('peaks'), reserve=[(0, 0, 60, 60), (0, 260 - 40, 150, 260), (390 - 208, 260 - 36, 390, 260)],
              scale_corner='bl', osm_data=osm_ov, pad_bottom_px=40, aria=aria_for(t))
    m = render_map(ph)
    meta['maps']['overview-phone'] = {'w': 390, 'h': 260, 'png': m.get('png'), 'base': m.get('base'), 'base_gz_kb': m.get('base_gz_kb')}
    # day maps: one OSM download covering every day's frame
    day_specs = []
    ski = t['activity'] == 'ski'
    for i, tr in enumerate(trs):
        bb = geo.bbox_of([[(p[0], p[1]) for p in tr.raw]])
        others = [{'track': o, 'style': 'ghost', 'trim': False, 'i0': 0, 'i1': len(o.raw) - 1} for j, o in enumerate(trs) if j != i]
        me = {'track': tr, 'style': 'route', 'width': 3.5, 'trim': False, 'i0': 0, 'i1': len(tr.raw) - 1}
        aria = 'Map of day %s of %s' % (days[i]['label'], t['title'])
        # a day on one crag or slope gets render_single's framing: at least 1.4 km across, with a z15 hillshade (~2 m/px)
        tiny = dict(min_extent_m=1400, hs_zoom=15) if extent_m([tr]) < 3000 else {}
        day_specs.append((dict(REPORT, **tiny, name='day-%s-col' % days[i]['id'], w=718, h=400, bbox=bb, png_scale=2.0, peaks_max=2, trails=False,
                               priority_peaks=mo.get('peaks'), skin=ski, bands_off=True, aria=aria), [me] + others))
        day_specs.append((dict(SMALL, **tiny, name='day-%s-phone' % days[i]['id'], w=390, h=240, bbox=bb, scale_corner='bl', chevrons=False,
                               startend=True, gpsmax=True, bands_off=True, reserve=[(390 - 208, 240 - 36, 390, 240)], pad_bottom_px=40, aria=aria),
                          [dict(me, width=3)]))
    osm_days = fetch_osm(union([frame_bbox(s, tk) for s, tk in day_specs]), 'report')
    for s, tk in day_specs:
        s['tracks'] = tk
        s['osm_data'] = osm_days
        m = render_map(s)
        meta['maps'][s['name']] = {'w': s['w'], 'h': s['h'], 'png': m.get('png'), 'base': m.get('base'), 'base_gz_kb': m.get('base_gz_kb')}
    multi_charts(t, meta, trs)
    dom = (min(min(tr.ele) for tr in trs if tr.ele), max(max(tr.ele) for tr in trs if tr.ele))
    for d, tr in zip(days, trs):
        render_sparkline('spark-%s' % d['id'], tr, 96, 24, domain=dom)
        render_sparkline('spark-%s-cur' % d['id'], tr, 96, 24, color='{{route}}', stroke=2, domain=dom)
    render_tile('tile', None, 200, 152, cat, transfers=transfers, osm_data=osm_ov,
                tracks=[{'track': tr, 'style': 'cat', 'cat': cat, 'width': 2.5, 'trim': False, 'i0': 0, 'i1': len(tr.raw) - 1} for tr in trs])
    render_tile('card', None, CARD_W, CARD_H, cat, transfers=transfers, osm_data=osm_ov, tiny_disc=7,
                tracks=[{'track': tr, 'style': 'cat', 'cat': cat, 'width': CARD_LINE, 'trim': False, 'i0': 0, 'i1': len(tr.raw) - 1} for tr in trs])
    # connectors only for content transfers (CZ D2 -> D3); separate crags stay separate, tiny days read as spots
    render_glyph('g112', trs, 112, 64, cat, transfer_dash='2 2', transfers=transfers)
    render_glyph('g64', trs, 64, 48, cat, pad=5, transfer_dash='1.5 1.5', transfers=transfers)
    meta['start'] = trs[0].raw[0][:2]
    meta['end'] = trs[-1].raw[-1][:2]
    meta['bbox'] = geo.bbox_of([[(p[0], p[1]) for p in tr.raw] for tr in trs])


def render_series(t, meta):
    cat = t['cat']
    trs = []
    for d in t['days']:
        if not d['track']:
            continue
        pts = fit_reader.read_gpx(d['track'])
        tr = Track(mapkit.decimate(pts, 600), '%s-%s' % (t['slug'], d['id']), cat)
        if not tr.raw:
            continue
        trs.append((d, tr))
        set_out(os.path.join(t['rendered'], 'days'))
        render_glyph('%s-g64' % d['id'], tr, 64, 48, cat, pad=5)
        if tr.ele:
            render_sparkline('%s-spark' % d['id'], tr, 96, 24)
    set_out(t['rendered'])
    tracks = [{'track': tr, 'style': 'cat', 'cat': cat, 'width': 2.6, 'trim': False, 'casing': False, 'i0': 0, 'i1': len(tr.raw) - 1,
               'key': 'm-%s' % d['date'].strftime('%Y-%m') if d.get('date') else None}
              for d, tr in trs]
    # the start disc and end square carry the content dates, so the end reads as the last recording, not the finish
    first_d, last_d = trs[0][0].get('date') or t.get('date'), trs[-1][0].get('date') or t.get('end_date')
    ends = [d_.strftime('%b %d').upper().replace(' 0', ' ') if d_ else None for d_ in (first_d, last_d)]
    # the first recorded day of each month after the first, labelled with its month where the line starts that day (maps-06)
    months, seen = [], {first_d.strftime('%Y-%m')} if first_d else set()
    for d, tr in trs:
        if d.get('date') and d['date'].strftime('%Y-%m') not in seen:
            seen.add(d['date'].strftime('%Y-%m'))
            months.append((tr.raw[0][0], tr.raw[0][1], d['date'].strftime('%b').upper()))
    for nm, w, h in (('overview-tall', 560, 860), ('overview-phone', 390, 600)):
        extra = {'reserve': [(w - 208, h - 36, w, h)], 'pad_bottom_px': 40} if nm == 'overview-phone' else {}
        m = render_map(dict(name=nm, w=w, h=h, tracks=[dict(x) for x in tracks], osm=None, png_scale=1.5, legend=False, graticule=False,
                            contours=False, ocean=True, exaggeration=6.0, miles=False, chevrons=False, startend=False, gpsmax=False,
                            overall_startend=True, overall_labels=ends, point_labels=months, min_track_px=4, pad=0.06, north=False,
                            scale=True, trim=False,
                            scale_corner='bl',
                            aria='Every recorded day of %s' % t['title'], **extra))
        meta['maps'][nm] = {'w': w, 'h': h, 'png': m.get('png'), 'base': m.get('base'), 'base_gz_kb': m.get('base_gz_kb')}
    allt = [tr for _, tr in trs]
    render_glyph('g112', allt, 112, 64, cat, stroke=1.6, tiny_r=None)  # a thru-hike's days are short but joined: never spots
    render_glyph('g64', allt, 64, 48, cat, pad=5, stroke=1.4, tiny_r=None)
    render_tile('tile', None, 200, 152, cat, tracks=[dict(x, width=2) for x in tracks], tiny_disc=None)
    render_tile('card', None, CARD_W, CARD_H, cat, tracks=[dict(x, width=2.6) for x in tracks], tiny_disc=None)
    meta['start'] = allt[0].raw[0][:2]
    meta['end'] = allt[-1].raw[-1][:2]
    meta['bbox'] = geo.bbox_of([[(p[0], p[1]) for p in tr.raw] for tr in allt])


def render_trip(t, force=False):
    if no_route(t) or no_track(t):
        # a render left over from when the goal had a route, or the report a track, would show a line that no longer exists
        if os.path.exists(t['rendered']):
            shutil.rmtree(t['rendered'])
            print('removed render of %s (%s)' % (t['slug'], 'the goal has no route now' if no_route(t) else 'the report has no track now'))
        return False
    mf = os.path.join(t['rendered'], 'meta.json')
    h = trip_inputs(t)
    if not force and stored_hash(mf) == h:
        return add_terrain(t, mf)   # the maps are up to date; a goal may still lack its terrain estimate
    final = t['rendered']
    t0 = time.time()
    with drawing_into(final) as tmp:
        # render_single / render_multi / render_series write through t['rendered']: point it at the temp folder
        t['rendered'] = tmp
        try:
            set_out(tmp)
            meta = {'hash': h, 'inputs': renderkey.input_parts(t), 'slug': t['slug'], 'kind': t['kind'], 'maps': {}, 'charts': {}}
            del OSM_FAILED[:]
            osm_before = osm_fetches()
            if t['kind'] == 'series':
                render_series(t, meta)
            elif t['days']:
                render_multi(t, meta)
            else:
                render_single(t, meta)
            set_out(tmp)
            for f in os.listdir(tmp):
                if f.endswith('.meta.json'):
                    os.remove(os.path.join(tmp, f))
            if OSM_FAILED:
                meta['hash'] = None  # incomplete: the next run retries
                meta['osm_failed'] = True
            optimize_images(tmp, meta)
            meta['renderer'] = renderer_record(osm_before)
            with open(os.path.join(tmp, 'meta.json'), 'w') as fh:
                json.dump(meta, fh, indent=1, default=str)
        finally:
            t['rendered'] = final
    print('rendered %-40s %5.0fs%s' % (t['slug'], time.time() - t0, '  (OSM missing)' if OSM_FAILED else ''))
    return True


def stored_hash(mf):
    """The hash a meta.json records, or None: no file, or one that does not parse (it is drawn again, never a crash)."""
    try:
        with open(mf, encoding='utf-8') as fh:
            return json.load(fh).get('hash')
    except (OSError, ValueError, AttributeError):
        return None


def render_folders(tdir):
    """The trip render folders under rendered/trips/: not a file (.DS_Store), not a dot-name, not the temp or old folder
    of a render at work (<slug>.tmp-<pid>, <slug>.old), which belongs to that run, and not an iCloud conflict copy
    ('<slug> 2'), which tools/tidy.py lists and only its --delete removes (until 2026-10-25 a run removed them as renders
    of gone trips)."""
    if not os.path.isdir(tdir):
        return []
    return sorted(d for d in os.listdir(tdir) if not d.startswith('.') and '.tmp-' not in d and not d.endswith('.old')
                  and not conflict_copy(d) and os.path.isdir(os.path.join(tdir, d)))


class drawing_into(object):
    """with drawing_into(folder) as tmp: draw into <folder>.tmp-<pid>, and only when the block ends without an exception
    put it in the folder's place (the old folder is renamed to <folder>.old, the new one to the folder, the old one
    removed: a folder cannot be renamed over a folder that has files). A render that fails half-way, or that Ctrl+C
    stops, leaves the last good render where it was and no temp folder behind, so the site never gets a page whose map
    files are half there."""

    def __init__(self, folder):
        self.folder = folder
        self.tmp = '%s.tmp-%d' % (folder, os.getpid())
        self.old = folder + '.old'

    def __enter__(self):
        if os.path.exists(self.tmp):
            shutil.rmtree(self.tmp)
        os.makedirs(self.tmp)
        return self.tmp

    def __exit__(self, kind, value, tb):
        try:
            if kind is None:
                if os.path.exists(self.old):
                    shutil.rmtree(self.old)
                if os.path.exists(self.folder):
                    os.rename(self.folder, self.old)
                os.rename(self.tmp, self.folder)
                if os.path.exists(self.old):
                    shutil.rmtree(self.old, ignore_errors=True)
        finally:
            # whatever stopped the swap (Ctrl+C included): the last good render goes back, the temp folder goes
            if not os.path.exists(self.folder) and os.path.exists(self.old):
                os.rename(self.old, self.folder)
            if os.path.exists(self.tmp):
                shutil.rmtree(self.tmp, ignore_errors=True)
        return False


# ---------------------------------------------------------------- site maps

def goal_lines(t):
    """A tick-list goal's line for the region maps: the point list of every segment of its published file, in order
    (planned_tracks: a route-only file counts, and separate segments stay separate). [] for an idea without a route."""
    return [x.raw for x in planned_tracks(t)] if t['track'] else []


def start_of(t):
    if t['kind'] == 'planned':
        lines = goal_lines(t)
        return (lines[0][0][0], lines[0][0][1]) if lines else None
    tp = t['track'] or next((d['track'] for d in t['days'] if d['track']), None)
    p = fit_reader.read_gpx(tp)
    return p[0][0], p[0][1]


def site_tracks(t, width=2.5, opacity=0.9, part=None):
    """A trip's lines on a region map. part: one part of a journal (journal_parts): only its days are drawn, under the
    part's key, and the lines are a link to the first of those days (the journal has no pin of its own to follow). A day
    the part takes one stretch of ('146/2', content.day_points) is drawn with that stretch alone."""
    out = []
    key = t['slug']
    link = {}
    if t['kind'] == 'planned':
        lines = goal_lines(t)
    elif part is not None:
        lines = [part_points(t, part, d) for d in part['days']]
        key = part['key']
        link = {'href': part_href(t, part), 'title': part_name(t, part)}
    else:
        paths = [t['track']] if t['track'] else [d['track'] for d in t['days'] if d['track']]
        lines = [fit_reader.read_gpx(p) for p in paths]
    for pts in lines:
        tr = Track(mapkit.decimate(pts, 500), key, t['cat'])
        style = 'planned' if t['kind'] == 'planned' else 'cat'
        # planned routes on region maps: thin ink-3 dash (KEY_SYMBOLS['planned_site']); the 2.5px dash stays on the route's own map
        out.append(dict({'track': tr, 'style': style, 'cat': t['cat'], 'width': width, 'opacity': opacity, 'trim': False,
                         'i0': 0, 'i1': len(tr.raw) - 1, 'key': key, 'thin': style == 'planned'}, **link))
    return out


def drawn_stretches(part):
    """{day id: stretch number} for the days a part is drawn with one stretch of: its 'stretches', for the days it has."""
    ids = {d['id'] for d in part['days']}
    return {i: n for i, n in sorted((part.get('stretches') or {}).items()) if i in ids}


def part_glyph(key, part):
    """The name of a journal part's drawing in rendered/site/ (64×48, all of the part's days, not only what the map's frame
    shows): key is the region map's ('region-lake-tahoe'). build.py publishes it as assets/maps/<name>.svg."""
    return '%s-%s-g64' % (key, content.slugify(part['key']))


def part_points(t, part, d):
    """The fixes of one day of a journal part: the whole day, or the one stretch of it the part takes."""
    return content.day_points(d, (part.get('stretches') or {}).get(d['id']), 'content/trips/%s/index.md' % t['slug'])


def part_href(t, part):
    """The journal page at the part's first day."""
    return '@@ROOT@@' + t['url'] + '#' + content.day_anchor(part['days'][0]['label'])


def part_name(t, part):
    """'Tahoe Rim Trail: Pacific Crest Trail 2024, Day 147 to Day 153': what a part's line is called (its link's name)."""
    first, last = part['days'][0]['label'], part['days'][-1]['label']
    span = 'Day %s' % first if first == last else 'Day %s to Day %s' % (first, last)
    return '%s%s, %s' % ((part['title'] + ': ') if part.get('title') else '', t['title'], span)


def day_runs(t, days):
    """The days split into runs that follow one another in the journal: [[day, ...], ...]. A journal that comes through
    a region twice (the PCT in July, the Tahoe Rim Trail in September) has two runs there."""
    order = {d['id']: i for i, d in enumerate(t['days'])}
    runs = []
    for d in days:
        if runs and order[d['id']] == order[runs[-1][-1]['id']] + 1:
            runs[-1].append(d)
        else:
            runs.append([d])
    return runs


RESUME_M = 5000.0  # a listed day that starts within this of where the part's last listed day ended goes on with the same walk


def journal_pins(t, part, frame=None):
    """The pins of one part of a journal in a region: one for each run of its days that starts in the region, at the
    start of the run's first day (of the stretch the part takes of it, when it takes one), linking to that day on the
    journal page. A pin marks a start, so a run that comes in from outside (the PCT walking through) has none: its line
    is on the map, and is its own link (site_tracks). Nor has a run that goes on from where the part's last listed day
    ended (within RESUME_M): the days between them, left out of the part (days off in a town), start nothing new.
    frame: the (s, w, n, e) box of the region's own trips, which the map is framed by; None: every run has its pin."""
    pins, end = [], None
    for run in day_runs(t, part['days']):
        d = run[0]
        p = part_points(t, part, d)[0]
        resumed = end is not None and geo.hav(end, p) <= RESUME_M
        end = part_points(t, part, run[-1])[-1]
        if resumed:
            continue
        if frame is not None and not (frame[0] <= p[0] <= frame[2] and frame[1] <= p[1] <= frame[3]):
            continue
        pins.append({'lat': p[0], 'lon': p[1], 'cat': t['cat'], 'key': part['key'],
                     'title': '%s%s, Day %s' % ((part['title'] + ': ') if part.get('title') else '', t['title'], d['label']),
                     'href': '@@ROOT@@' + t['url'] + '#' + content.day_anchor(d['label'])})
    return pins


def render_site(trips, force=False):
    final = os.path.join(OUT, 'site')
    # which maps there are and what they draw: renderkey.site_jobs, which the content checks use for the same hash
    jobs, groups, mapped = renderkey.site_jobs(trips)
    h = renderkey.site_hash(jobs)
    # site_maps_stale is the one test: the new hash, or the one written before Phase 9 (also after a retitle, matched
    # with the titles the maps were drawn with), means the maps are up to date and nothing is drawn
    if not force and site_maps_stale(trips) is None:
        return False
    with drawing_into(final) as folder:
        draw_site(folder, h, jobs, groups, mapped)
    return True


def draw_site(folder, h, jobs, groups, mapped):
    """Draw every site map into `folder` (a temp folder that render_site swaps in once this has returned)."""
    set_out(folder)
    meta = {'hash': h, 'maps': {}}
    del OSM_FAILED[:]
    osm_before = osm_fetches()
    for key, region, ts, sizes, journals in jobs:
        t0 = time.time()
        pins = []
        for t in ts:
            lat, lon = start_of(t)
            pins.append({'lat': lat, 'lon': lon, 'cat': t['cat'], 'key': t['slug'], 'title': t['title'], 'href': '@@ROOT@@' + t['url']})
        tracks = [x for t in ts for x in site_tracks(t)]
        frame = {}
        if journals:
            # a journal passes through: the map stays framed by the region's own trips (the box render_map would work
            # out from them), and the journal's days are drawn where they cross it, cut off at the map's edge
            own = geo.bbox_of([[(p[0], p[1]) for p in x['track'].raw] for x in tracks] + [[(pn['lat'], pn['lon']) for pn in pins]])
            frame = {'bbox': own}
            for pt in journals:
                pins += journal_pins(pt['trip'], pt, own)
                lines = site_tracks(pt['trip'], part=pt)
                tracks += lines
                # the part's own drawing, for its row in the region's list: the journal's glyph is the whole journal
                render_glyph(part_glyph(key, pt), [x['track'] for x in lines], 64, 48, pt['trip']['cat'], pad=5, tiny_r=None)
        specs = [dict(OVERVIEW, name='%s-%s' % (key, v), w=w, h=h_, pins=pins, pad=0.10, priority_peaks=[p for t in ts for p in (t['map'].get('peaks') or [])][:6],
                      aria='Map of %s trips in %s' % (PANEL_WORDS.get(key.split('-', 1)[0], 'all'), region), **frame,
                      **({'scale_corner': 'bl', 'reserve': [(w - 208, h_ - 36, w, h_)], 'pad_bottom_px': 40} if v == 'phone' else {})) for w, h_, v in sizes]
        for s in specs:
            s['tracks'] = [dict(x) for x in tracks]
        osm = fetch_osm(union([frame_bbox(s, s['tracks']) for s in specs]), 'overview')
        for s in specs:
            s['osm_data'] = osm
            m = render_map(s)
            meta['maps'][s['name']] = {'w': s['w'], 'h': s['h'], 'png': m.get('png'), 'base': m.get('base'),
                                       'base_gz_kb': m.get('base_gz_kb'), 'region': region,
                                       'trips': [t['slug'] for t in ts], 'clusters': m.get('clusters')}
            if journals:
                # the journal days this map draws, part by part; 'trips' stays the region's own reports and planned routes
                # 'stretches' ({day id: number}) only on a part that takes one stretch of a day
                meta['maps'][s['name']]['journals'] = [dict({'slug': pt['trip']['slug'], 'key': pt['key'], 'title': pt['title'],
                                                             'days': [d['id'] for d in pt['days']], 'glyph': part_glyph(key, pt)},
                                                            **({'stretches': drawn_stretches(pt)} if drawn_stretches(pt) else {}))
                                                       for pt in journals]
        print('rendered site map %-28s %5.0fs' % (key, time.time() - t0))
    for f in os.listdir(folder):
        if f.endswith('.meta.json'):
            os.remove(os.path.join(folder, f))
    meta['regions'] = sorted(mapped)          # regions that have an overview map
    meta['all_regions'] = sorted(groups)      # every region, mapped or not
    if OSM_FAILED:
        meta['hash'] = None
    optimize_images(folder, meta)
    meta['renderer'] = renderer_record(osm_before)
    with open(os.path.join(folder, 'meta.json'), 'w') as fh:
        json.dump(meta, fh, indent=1, default=str)


def pending_reason(t, force=False):
    """Why a plain run would draw this (non-draft) trip, or None when its maps are up to date: the test render_trip
    makes, read from content/ and rendered/ only. A trip with nothing to draw is pending only while a render is left
    from when it had a route or a track (render_trip then removes it). A goal whose maps are up to date is pending while
    its meta.json lacks the terrain estimate its file needs (renderkey.terrain_reason); a run then makes that alone."""
    if no_route(t) or no_track(t):
        return ('the %s has no %s now: its old render is removed' % (('goal', 'route') if no_route(t) else ('report', 'track'))
                if os.path.exists(t['rendered']) else None)
    if force:
        return 'forced (--force)'
    mf = os.path.join(t['rendered'], 'meta.json')
    if not os.path.exists(mf):
        return 'new: no maps drawn yet'
    try:
        with open(mf, encoding='utf-8') as fh:
            meta = json.load(fh)
        stored = meta.get('hash')
    except (OSError, ValueError, AttributeError):
        return 'rendered/trips/%s/meta.json cannot be read' % t['slug']
    if stored is None or meta.get('osm_failed'):
        return 'OSM missing last time (drawn with terrain only)'
    if stored == trip_inputs(t):
        return terrain_reason(t, meta)   # None for every trip but a goal whose file lacks elevation and meta.json the estimate
    had = meta.get('inputs') if isinstance(meta.get('inputs'), dict) else {}
    if not had and stored in {trip_inputs(t, v) for v in range(max(1, VERSION - 3), VERSION)}:
        return 'renderer changed'      # drawn before the inputs were recorded: the same trip, an older renderer
    now = renderkey.input_parts(t)
    what = [w for k, w in (('files', 'track changed'), ('fields', 'title/map/stats changed'), ('version', 'renderer changed'))
            if k in had and had[k] != now[k]]
    if not what and all(k in had for k in ('files', 'fields', 'version')):
        return 'map frame changed (renderkey.report_frame)'   # the three parts agree: the frame is all the hash has left
    return ', '.join(what) or 'track, title, activity, kind, map: or stats changed'


def pending_trips(trips, slugs=(), force=False):
    """The trips a run would draw (slugs: only these), in the order given: render_trip draws exactly these. Trips with
    nothing to draw are left out (main clears their old renders on its own)."""
    return [t for t in trips if (not slugs or t['slug'] in slugs) and not no_route(t) and not no_track(t)
            and pending_reason(t, force) is not None]


def site_maps_stale(trips, force=False):
    """Why a run would draw the site maps again, or None when they are up to date (render_site's own test)."""
    if force:
        return 'forced (--force)'
    mf = os.path.join(OUT, 'site', 'meta.json')
    if not os.path.exists(mf):
        return 'not drawn yet'
    try:
        with open(mf, encoding='utf-8') as fh:
            meta = json.load(fh)
        stored = meta.get('hash')
    except (OSError, ValueError, AttributeError):
        return 'rendered/site/meta.json cannot be read'
    if stored is None:
        return 'OSM missing last time (drawn with terrain only)'
    jobs = renderkey.site_jobs(trips)[0]
    if stored in (renderkey.site_hash(jobs), renderkey.site_hash_with_titles(jobs)):
        return None
    # the hash written before Phase 9 holds every title as the maps were drawn: a trip retitled since (the build writes
    # its new title into the labels) still matches it with the title its pin shows, until the next site render writes
    # the new hash
    maps = meta.get('maps')
    drawn = renderkey.drawn_titles(renderkey.drawn_paths(os.path.join(OUT, 'site'), maps if isinstance(maps, dict) else {}))
    return None if drawn and stored == renderkey.site_hash_as_drawn(jobs, drawn) else 'a trip on a region or ski map changed'


def status(slugs=(), force=False, say=print):
    """render.py --status: one line per trip a run would draw, and why, then the site maps; fetches nothing and draws
    nothing. Returns 1 when anything is pending, else 0. Drafts are listed as skipped: render.py never draws one."""
    try:
        everything = content.load_all(include_drafts=True)
    except content.ContentError as ex:
        say('ERROR %s' % ex)
        return 1
    trips = [t for t in everything if not t['draft']]       # content.load_all()'s list, the one a run renders from
    named = [t for t in everything if not slugs or t['slug'] in slugs]
    pending = 0
    for t in named:
        why = 'draft, skipped (render.py leaves drafts out)' if t['draft'] else pending_reason(t, force)
        if why:
            say('%-44s %s' % (t['slug'], why))
            pending += 0 if t['draft'] else 1
    for slug in sorted(set(slugs) - {t['slug'] for t in everything}):
        say('%-44s no such trip (no content/trips/%s/index.md)' % (slug, slug))
    live = {t['slug'] for t in everything}
    tdir = os.path.join(OUT, 'trips')
    for d in ([] if slugs else render_folders(tdir)):
        if d not in live:
            say('%-44s no trip any more: its render is removed' % ('rendered/trips/' + d))
            pending += 1
    if not pending:
        say('trips: %s up to date' % ('all %d' % len(trips) if not slugs else ', '.join(t['slug'] for t in named if not t['draft']) or 'nothing'))
    site = site_maps_stale(trips, force and not slugs)
    say('site maps: %s' % ('up to date' if site is None else 'stale (%s)' % site))
    return 1 if pending or site else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('slugs', nargs='*')
    ap.add_argument('--site', action='store_true', help='only region/section maps')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--no-site', action='store_true', help='skip region/section maps')
    ap.add_argument('--charts', action='store_true', help='only re-render elevation profiles / speed charts (fast, offline)')
    ap.add_argument('--status', action='store_true', help='list what a run would draw and why, offline; draws and fetches nothing')
    ap.add_argument('--list', action='store_true', help='the same as --status')
    ap.add_argument('--allow-png', action='store_true', help='draw without cwebp (the hillshades stay PNG, larger)')
    ap.add_argument('--budget', type=float, help='stop starting new trips after this many seconds (run again to continue)')
    ap.add_argument('--jobs', type=int, default=1, help='render this many trips in parallel (uses fork; shares prefetched OSM)')
    a = ap.parse_args(argv)
    if a.status or a.list:
        return status(a.slugs, a.force)
    if not a.charts and cwebp_version() is None and not a.allow_png:
        # without it the hillshades would be committed as PNGs, about twice the size (gap9-05)
        print('cwebp is not installed (brew install webp); nothing drawn. --allow-png draws with PNG hillshades.')
        return 2
    if a.force and not a.slugs and not a.site:
        print('note: a full re-render is a VERSION bump in tools/lib/renderkey.py plus --budget, which resumes; '
              '--force redraws every trip on every run')
    trips = content.load_all()
    if a.charts:
        for t in trips:
            if (a.slugs and t['slug'] not in a.slugs) or t['kind'] in ('series', 'planned') or no_track(t):
                continue
            mf = os.path.join(t['rendered'], 'meta.json')
            if not os.path.exists(mf):
                continue
            meta = json.load(open(mf))
            set_out(t['rendered'])
            (multi_charts if t['days'] else single_charts)(t, meta)
            for f in os.listdir(t['rendered']):
                if f.endswith('.meta.json'):
                    os.remove(os.path.join(t['rendered'], f))
            json.dump(meta, open(mf, 'w'), indent=1, default=str)
            print('charts', t['slug'])
        return 0
    failed, drawn = [], []
    run = {'site': None, 'left': 0, 'pending': 0, 't0': time.time()}

    def attempt(fn, name, *args):
        """Run one render; an error is printed and remembered, and the run goes on with the next (its old maps stay)."""
        try:
            return fn(*args)
        except Exception as ex:   # noqa: BLE001 — a failed tile or a bad file must not stop the other trips
            print('! %s: %s' % (name, ex), flush=True)
            failed.append(name)
            return False

    def finished(slug, result):
        """A trip is done: remembered, and every 10th prints where the run stands (gap9-04)."""
        if result:
            drawn.append(slug)
        n = len(drawn) + len([f for f in failed if f != 'site maps'])
        if n and n % 10 == 0 and run['pending'] and run.get('said') != n:
            run['said'] = n
            per = (time.time() - run['t0']) / n
            left = max(0, run['pending'] - n) * per
            print('progress: %d of %d trips done, %.0f s a trip, about %d min left'
                  % (n, run['pending'], per, round(left / 60.0)), flush=True)
    def left():
        """Trips still to draw when a run stops: pending, and neither drawn nor failed in this run."""
        done = set(drawn) | set(failed)
        return len([t for t in pending_trips(trips, a.slugs, a.force) if t['slug'] not in done])
    if not a.site:
        t_start = time.time()
        for t in trips:
            if (no_route(t) or no_track(t)) and (not a.slugs or t['slug'] in a.slugs):
                render_trip(t)   # nothing to draw: only clears a render left from when the goal had a route, or the report a track
        # the journal is drawn by the one-at-a-time loop below only, as before: with --jobs that loop draws it alone, after
        # the pool (until 2026-10-25 --jobs skipped the loop, and with it the journal)
        pending = [t for t in pending_trips(trips, a.slugs, a.force) if t['kind'] != 'series']
        run['pending'] = len(pending_trips(trips, a.slugs, a.force))
        if len(pending) > 3:
            prefetch_osm(pending)
        if a.jobs > 1 and pending:
            import multiprocessing as mp
            from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
            with ProcessPoolExecutor(max_workers=a.jobs, mp_context=mp.get_context('fork')) as ex:
                todo = list(pending)
                running = {}
                while todo or running:
                    while todo and len(running) < a.jobs and not (a.budget and time.time() - t_start > a.budget):
                        t = todo.pop(0)
                        running[ex.submit(render_trip, t, a.force)] = t['slug']
                    if not running:
                        break
                    done, _ = wait(set(running), return_when=FIRST_COMPLETED)
                    for f in done:
                        slug = running.pop(f)
                        finished(slug, attempt(f.result, slug))
            if todo:
                run['left'] = left()
                print('budget used up; %d trips left — run again to continue' % run['left'])
                summary(run, trips, drawn, failed)
                return 1 if failed else 0
        to_draw = {t['slug'] for t in pending_trips(trips, a.slugs, a.force)}
        for t in ([t for t in trips if t['kind'] == 'series'] if a.jobs > 1 else trips):
            if a.slugs and t['slug'] not in a.slugs:
                continue
            if a.budget and time.time() - t_start > a.budget and t['slug'] in to_draw:
                run['left'] = left()
                print('budget used up; %d trips left — run again to continue' % run['left'])
                summary(run, trips, drawn, failed)
                return 1 if failed else 0
            finished(t['slug'], attempt(render_trip, t['slug'], t, a.force))
    if not a.no_site:
        run['site'] = bool(attempt(render_site, 'site maps', trips, a.force and (a.site or not a.slugs)))
    # drop renders of trips that no longer exist
    live = {t['slug'] for t in content.load_all(include_drafts=True)}
    tdir = os.path.join(OUT, 'trips')
    for d in render_folders(tdir):
        if d not in live:
            shutil.rmtree(os.path.join(tdir, d))
            print('removed stale render', d)
    cache_report()
    summary(run, trips, drawn, failed)
    if failed:
        print('%d failed, their last good maps kept: %s. Run python3 tools/render.py again for them.' % (len(failed), ', '.join(failed)))
        return 1
    return 0


def summary(run, trips, drawn, failed):
    """The run's last line (gap9-04), for the commit message of a render round: trips rendered, skipped (their hash
    unchanged), failed (named), drawn with OpenStreetMap missing, left for the next run, and whether the site maps were
    drawn. OSM missing is read back from the meta.json each rendered trip wrote (a --jobs worker's own list is not ours)."""
    osm = []
    for slug in drawn:
        try:
            with open(os.path.join(OUT, 'trips', slug, 'meta.json'), encoding='utf-8') as fh:
                if json.load(fh).get('osm_failed'):
                    osm.append(slug)
        except (OSError, ValueError, AttributeError):
            pass
    trip_failed = [f for f in failed if f != 'site maps']
    skipped = max(0, len(trips) - len(drawn) - len(trip_failed) - run['left'])
    site = {None: 'not drawn this run', True: 'drawn', False: 'up to date'}[run['site']] if 'site maps' not in failed else 'failed'
    print('summary: rendered %d, skipped %d (unchanged), failed %d%s, OSM missing %d%s, left %d; site maps %s; %.0f min'
          % (len(drawn), skipped, len(trip_failed), (' (%s)' % ', '.join(trip_failed)) if trip_failed else '', len(osm),
             (' (%s)' % ', '.join(osm)) if osm else '', run['left'], site, (time.time() - run['t0']) / 60.0))


def cache_report():
    """One line on the downloads behind this run (this process; with --jobs the workers count their own): tiles and
    OpenStreetMap answers read from the cache or fetched, and the oldest and newest day an answer used was fetched (an
    answer is never refreshed on its own: geo.overpass)."""
    c = geo.CACHE
    if not any(c[k] for k in ('tile_hit', 'tile_miss', 'osm_hit', 'osm_miss')):
        return
    dates = sorted(c['osm_dates'])
    print('caches (%s): tiles %d cached, %d fetched; OpenStreetMap %d cached, %d fetched%s' % (
        geo.cache_home(), c['tile_hit'], c['tile_miss'], c['osm_hit'], c['osm_miss'],
        ('; OpenStreetMap as of %s' % dates[0] if dates[0] == dates[-1] else '; OpenStreetMap as of %s to %s' % (dates[0], dates[-1]))
        if dates else ''))
    if c['osm_undated']:
        print('  %d of the OpenStreetMap answers were cached before answers carried a date: dated by their file' % c['osm_undated'])
    if os.path.join(ROOT, '.cache') in (os.path.dirname(geo.TILE_DIR), os.path.dirname(geo.OSM_DIR)):
        print('  the caches are still in .cache/ inside the checkout, which iCloud Drive offloads: move them once to %s '
              '(docs/DEVELOPING.md, "Render caches")' % geo.CACHE_HOME)


if __name__ == '__main__':
    sys.exit(main())
