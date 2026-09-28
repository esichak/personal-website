#!/usr/bin/env python3
"""Render maps, elevation profiles, glyphs and tiles for the site into rendered/.

  python3 tools/render.py                 # everything that changed since the last render
  python3 tools/render.py SLUG [SLUG …]   # just these trips (region maps are refreshed too)
  python3 tools/render.py --site          # only the region / section overview maps
  python3 tools/render.py --force …       # ignore the change check

Needs the internet (AWS Terrain Tiles + OpenStreetMap Overpass); downloads are cached in .cache/.
Outputs are committed, so the GitHub Action never has to render anything.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import fit_reader  # noqa: E402
import geo  # noqa: E402
import mapkit  # noqa: E402
from mapkit import Track, render_map, render_profile, render_glyph, render_tile, render_sparkline, render_speed_chart  # noqa: E402

VERSION = 6  # bump after renderer changes to force a full re-render
MI, FT = geo.MI, geo.FT
OUT = os.path.join(ROOT, 'rendered')

REPORT = dict(legend=False, north=False, graticule=False, miles=True, chevrons=False, startend=True, gpsmax=True,
              png_scale=1.25, contour_density=0.75, peaks_max=3, trim=False)
SMALL = dict(road_levels=('motorway', 'trunk', 'primary', 'secondary', 'tertiary'), small_markers=True, gps_label='name', north=False,
             places_allow=[], skin=False, legend=False, miles=False, chevrons=False, startend=True, gpsmax=True,
             png_scale=2.0, contour_density=0.9, peaks_max=0, graticule=False, contour_labels=False, trails=False,
             track_eps=1.2, prio_avoid_track=True, trim=False)
OVERVIEW = dict(north=False, png_scale=1.5, graticule=False, contour_density=1.2, contour_labels=False, peaks_max=0, trails=False,
                poly_eps=0.8, min_water_px=40, road_levels=('motorway', 'trunk', 'primary', 'secondary'), places_max=3,
                places_by_rank=True, places_near_pins=60, overview_labels=True, cluster_px=26, miles=False, chevrons=False,
                startend=False, gpsmax=False, trim=False)


# ---------------------------------------------------------------- helpers

def optimize_images(folder, meta):
    """Hillshade PNGs -> WebP (q88: visually identical, ~6x smaller). Keeps the PNG only if cwebp is missing."""
    if not shutil.which('cwebp'):
        return
    import subprocess
    for f in sorted(os.listdir(folder)):
        if not f.endswith('.png'):
            continue
        src = os.path.join(folder, f)
        dst = src[:-4] + '.webp'
        subprocess.run(['cwebp', '-quiet', '-q', '88', '-m', '5', src, '-o', dst], check=True)
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


def file_hash(paths):
    h = hashlib.sha1()
    for p in paths:
        if p and os.path.exists(p):
            h.update(open(p, 'rb').read())
    return h.hexdigest()


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


OSM_FAILED = []


def fetch_osm(bbox, detail):
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

def render_single(t, meta):
    act, cat = t['activity'], t['cat']
    tr = load_track(t['track'], t['slug'], cat, t['stats'])
    mo = t['map']
    peaks = mo.get('peaks') or []
    small = extent_m([tr]) < 3000
    flat = (t['stats'].get('high_m') or 0) - (t['stats'].get('low_m') or 0) < 30 and act == 'other'
    planned = t['kind'] == 'planned'
    style = 'planned' if planned else 'route'
    base = {}
    if small:
        base.update(min_extent_m=1000 if flat else 1400, hs_zoom=15)
    if flat:
        base.update(gpsmax=False, miles=False, water_labels=6)
    if planned:
        base.update(gpsmax=False, miles=False, chevrons=False, startend=True)
    aria = aria_for(t)
    specs = [
        dict(REPORT, **base, name='map-wide', w=1440, h=640, skin=(act == 'ski'), peaks_max=2, priority_peaks=peaks,
             places_allow=mo.get('places'), extra_water_labels=water_labels(mo.get('water_labels'), 1440, 640), aria=aria),
        dict(REPORT, **base, name='map-col', w=718, h=400, png_scale=2.0, skin=(act == 'ski'), peaks_max=2, priority_peaks=peaks,
             places_allow=mo.get('places'), extra_water_labels=water_labels(mo.get('water_labels'), 718, 400), aria=aria),
        dict(SMALL, **{k: v for k, v in base.items() if k not in ('water_labels',)}, name='map-phone', w=390, h=336, scale_corner='bl',
             priority_peaks=peaks, reserve=[(0, 0, 60, 60), (390 - 208, 336 - 36, 390, 336)], pad_bottom_px=40, aria=aria),
    ]
    trks = [{'track': tr, 'style': style}]
    osm = fetch_osm(union([frame_bbox(s, trks) for s in specs]), 'report')
    for s in specs:
        s['tracks'] = [{'track': tr, 'style': style, 'width': 3 if s['name'] == 'map-phone' else 3}]
        s['osm_data'] = osm
        m = render_map(s)
        meta['maps'][s['name']] = {'w': s['w'], 'h': s['h'], 'png': m.get('png'), 'base': m.get('base'), 'interval_ft': m.get('interval_ft'),
                                   'outbound_only': m.get('outbound_only')}
    single_charts(t, meta, tr)
    render_tile('tile', tr, 200, 152, cat, osm_detail=None, osm_data=osm, planned=planned)
    render_glyph('g112', tr, 112, 64, cat, planned=planned)
    render_glyph('g64', tr, 64, 48, cat, planned=planned, pad=5)
    meta['start'] = tr.raw[0][:2]
    meta['end'] = tr.raw[-1][:2]
    meta['bbox'] = geo.bbox_of([[(p[0], p[1]) for p in tr.raw]])


def axis_step(total_mi, w):
    """Mile-tick spacing that keeps labels >= 36 px apart (the first label reads "0 mi"; on phone charts, which have no
    y-axis gutter, the last one carries the unit)."""
    plot_w = w - (0 if w < 500 else 72)
    for step in (1, 2, 5, 10, 20, 50, 100):
        if plot_w / max(total_mi / step, 1) >= 36:
            return step
    return 100


def single_charts(t, meta, tr=None):
    act = t['activity']
    tr = tr or load_track(t['track'], t['slug'], t['cat'], t['stats'])
    flat = (t['stats'].get('high_m') or 0) - (t['stats'].get('low_m') or 0) < 30 and act == 'other'
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


def multi_charts(t, meta, trs=None):
    days = t['days']
    trs = trs or [load_track(d['track'], '%s-%s' % (t['slug'], d['id']), t['cat'], d['stats']) for d in days]
    transfers = [(i - 1, i) for i, d in enumerate(days) if d['transfer_before'] and i > 0]
    tot = sum(tr.total for tr in trs) / MI
    for nm, w, phh in (('profile-wide', 1248, 140), ('profile-col', 718, 120), ('profile-phone', 358, 110)):
        info = render_profile(nm, trs, w, phh, dict(skin=False, day_tints=True, day_band=True, grade=False, transfers=transfers,
                                                     label_every_ft=4000, axis_every_mi=axis_step(tot, w),
                                                     aria='Stitched elevation profile of all %d days' % len(trs)))
        meta['charts'][nm] = dict({'w': w, 'kind': 'profile'}, **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in info.items()})
    for d, tr in zip(days, trs):
        for nm, w, phh in (('day-%s-profile-col' % d['id'], 718, 96), ('day-%s-profile-phone' % d['id'], 358, 88)):
            info = render_profile(nm, [tr], w, phh, dict(skin=True, grade=False, label_every_ft=2000, axis_every_mi=axis_step(tr.total / MI, w),
                                                          aria='Elevation profile of day %s' % d['label']))
            meta['charts'][nm] = dict({'w': w, 'kind': 'profile'}, **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in info.items()})


def render_multi(t, meta):
    cat = t['cat']
    days = t['days']
    trs = [load_track(d['track'], '%s-%s' % (t['slug'], d['id']), cat, d['stats']) for d in days]
    mo = t['map']
    transfers = [(i - 1, i) for i, d in enumerate(days) if d['transfer_before'] and i > 0]
    hi_day = max(range(len(days)), key=lambda i: days[i]['stats'].get('high_m') or 0)

    def ov_tracks(huts=True):
        out = []
        for i, tr in enumerate(trs):
            e = {'track': tr, 'style': 'route', 'trim': False, 'day_label': i + 1, 'i0': 0, 'i1': len(tr.raw) - 1}
            if huts and i < len(trs) - 1:
                e['hut_end'] = {'n': i + 1, 'label': days[i]['hut']}
            if huts and i == hi_day:
                e['gpsmax'] = True
            out.append(e)
        return out
    ov = dict(REPORT, pad=0.10, poly_eps=0.6, min_water_px=30, road_levels=('motorway', 'trunk', 'primary', 'secondary', 'tertiary'),
              miles=False, chevrons=False, startend=False, gpsmax=False, graticule=False, contour_density=1.0, peaks_max=3,
              trails=False, priority_peaks=mo.get('peaks'), places_allow=mo.get('places'), transfers=transfers,
              water_near_track=40, bands_off=True, aria=aria_for(t))
    specs = [dict(ov, name='overview-wide', w=1440, h=560, png_scale=1.25),
             dict(ov, name='overview-col', w=718, h=440, png_scale=2.0, peaks_max=1)]
    osm_ov = fetch_osm(union([frame_bbox(s, ov_tracks()) for s in specs]), 'overview')
    for s in specs:
        s['tracks'] = ov_tracks()
        s['osm_data'] = osm_ov
        m = render_map(s)
        meta['maps'][s['name']] = {'w': s['w'], 'h': s['h'], 'png': m.get('png'), 'base': m.get('base')}
    ph = dict(SMALL, name='overview-phone', w=390, h=260, pad=0.12, places_allow=[], day_labels=False, poly_eps=1.2, min_water_px=40,
              road_levels=('motorway', 'trunk', 'primary'), tracks=[dict(e, hut_end=None, gpsmax=False) for e in ov_tracks()],
              miles=False, chevrons=False, startend=False, gpsmax=False, overall_startend=True, transfers=transfers, peaks_max=0,
              bands_off=True, priority_peaks=mo.get('peaks'), reserve=[(0, 0, 60, 60), (390 - 208, 260 - 36, 390, 260)],
              scale_corner='bl', osm_data=osm_ov, pad_bottom_px=40, aria=aria_for(t))
    m = render_map(ph)
    meta['maps']['overview-phone'] = {'w': 390, 'h': 260, 'png': m.get('png'), 'base': m.get('base')}
    # day maps: one OSM download covering every day's frame
    day_specs = []
    for i, tr in enumerate(trs):
        bb = geo.bbox_of([[(p[0], p[1]) for p in tr.raw]])
        others = [{'track': o, 'style': 'ghost', 'trim': False, 'i0': 0, 'i1': len(o.raw) - 1} for j, o in enumerate(trs) if j != i]
        me = {'track': tr, 'style': 'route', 'width': 3.5, 'trim': False, 'i0': 0, 'i1': len(tr.raw) - 1}
        aria = 'Map of day %s of %s' % (days[i]['label'], t['title'])
        day_specs.append((dict(REPORT, name='day-%s-col' % days[i]['id'], w=718, h=400, bbox=bb, png_scale=2.0, peaks_max=2, trails=False,
                               priority_peaks=mo.get('peaks'), skin=True, bands_off=True, aria=aria), [me] + others))
        day_specs.append((dict(SMALL, name='day-%s-phone' % days[i]['id'], w=390, h=240, bbox=bb, scale_corner='bl', chevrons=False,
                               startend=True, gpsmax=True, bands_off=True, reserve=[(390 - 208, 240 - 36, 390, 240)], pad_bottom_px=40, aria=aria),
                          [dict(me, width=3)]))
    osm_days = fetch_osm(union([frame_bbox(s, tk) for s, tk in day_specs]), 'report')
    for s, tk in day_specs:
        s['tracks'] = tk
        s['osm_data'] = osm_days
        m = render_map(s)
        meta['maps'][s['name']] = {'w': s['w'], 'h': s['h'], 'png': m.get('png'), 'base': m.get('base')}
    multi_charts(t, meta, trs)
    dom = (min(min(tr.ele) for tr in trs if tr.ele), max(max(tr.ele) for tr in trs if tr.ele))
    for d, tr in zip(days, trs):
        render_sparkline('spark-%s' % d['id'], tr, 96, 24, domain=dom)
        render_sparkline('spark-%s-cur' % d['id'], tr, 96, 24, color='{{route}}', stroke=2, domain=dom)
    render_tile('tile', None, 200, 152, cat, transfers=transfers, osm_data=osm_ov,
                tracks=[{'track': tr, 'style': 'cat', 'cat': cat, 'width': 2.5, 'trim': False, 'i0': 0, 'i1': len(tr.raw) - 1} for tr in trs])
    render_glyph('g112', trs, 112, 64, cat, transfer_dash='2 2')
    render_glyph('g64', trs, 64, 48, cat, pad=5, transfer_dash='1.5 1.5')
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
    for nm, w, h in (('overview-tall', 560, 860), ('overview-phone', 390, 600)):
        extra = {'reserve': [(w - 208, h - 36, w, h)], 'pad_bottom_px': 40} if nm == 'overview-phone' else {}
        m = render_map(dict(name=nm, w=w, h=h, tracks=[dict(x) for x in tracks], osm=None, png_scale=1.5, legend=False, graticule=False,
                            contours=False, ocean=True, exaggeration=6.0, miles=False, chevrons=False, startend=False, gpsmax=False,
                            overall_startend=True, overall_labels=ends, min_track_px=4, pad=0.06, north=False, scale=True, trim=False,
                            scale_corner='bl',
                            aria='Every recorded day of %s' % t['title'], **extra))
        meta['maps'][nm] = {'w': w, 'h': h, 'png': m.get('png'), 'base': m.get('base')}
    allt = [tr for _, tr in trs]
    render_glyph('g112', allt, 112, 64, cat, stroke=1.6)
    render_glyph('g64', allt, 64, 48, cat, pad=5, stroke=1.4)
    render_tile('tile', None, 200, 152, cat, tracks=[dict(x, width=2) for x in tracks])
    meta['start'] = allt[0].raw[0][:2]
    meta['end'] = allt[-1].raw[-1][:2]
    meta['bbox'] = geo.bbox_of([[(p[0], p[1]) for p in tr.raw] for tr in allt])


def trip_inputs(t):
    files = [t['track']] + [d['track'] for d in t['days']]
    keys = {k: t['meta'].get(k) for k in ('title', 'activity', 'kind', 'map', 'stats', 'route_shape')}
    keys['days'] = [(d['id'], d['hut'], d['transfer_before'], d['stats'], d['label']) for d in t['days']]
    return hashlib.sha1((json.dumps(keys, sort_keys=True, default=str) + file_hash(files) + str(VERSION)).encode()).hexdigest()


def render_trip(t, force=False):
    mf = os.path.join(t['rendered'], 'meta.json')
    h = trip_inputs(t)
    if not force and os.path.exists(mf) and json.load(open(mf)).get('hash') == h:
        return False
    if os.path.exists(t['rendered']):
        shutil.rmtree(t['rendered'])
    set_out(t['rendered'])
    meta = {'hash': h, 'slug': t['slug'], 'kind': t['kind'], 'maps': {}, 'charts': {}}
    t0 = time.time()
    del OSM_FAILED[:]
    if t['kind'] == 'series':
        render_series(t, meta)
    elif t['days']:
        render_multi(t, meta)
    else:
        render_single(t, meta)
    set_out(t['rendered'])
    for f in os.listdir(t['rendered']):
        if f.endswith('.meta.json'):
            os.remove(os.path.join(t['rendered'], f))
    if OSM_FAILED:
        meta['hash'] = None  # incomplete: the next run retries
        meta['osm_failed'] = True
    optimize_images(t['rendered'], meta)
    json.dump(meta, open(mf, 'w'), indent=1, default=str)
    print('rendered %-40s %5.0fs%s' % (t['slug'], time.time() - t0, '  (OSM missing)' if OSM_FAILED else ''))
    return True


# ---------------------------------------------------------------- site maps

def start_of(t):
    tp = t['track'] or next((d['track'] for d in t['days'] if d['track']), None)
    p = fit_reader.read_gpx(tp)
    return p[0][0], p[0][1]


def site_tracks(t, width=2.5, opacity=0.9):
    out = []
    paths = [t['track']] if t['track'] else [d['track'] for d in t['days'] if d['track']]
    for p in paths:
        tr = Track(mapkit.decimate(fit_reader.read_gpx(p), 500), t['slug'], t['cat'])
        style = 'planned' if t['kind'] == 'planned' else 'cat'
        # planned routes on region maps: thin ink-3 dash (KEY_SYMBOLS['planned_site']); the 2.5px dash stays on the route's own map
        out.append({'track': tr, 'style': style, 'cat': t['cat'], 'width': width, 'opacity': opacity, 'trim': False,
                    'i0': 0, 'i1': len(tr.raw) - 1, 'key': t['slug'], 'thin': style == 'planned'})
    return out


def render_site(trips, force=False):
    folder = os.path.join(OUT, 'site')
    groups = {}
    for t in trips:
        if t['kind'] == 'series' or not t['region']:
            continue
        groups.setdefault(t['region'], []).append(t)
    jobs = []
    for region, ts in groups.items():
        jobs.append(('region-' + content.slugify(region), region, ts, [(718, 620, 'desktop'), (390, 480, 'phone')]))
        ski = [t for t in ts if t['activity'] == 'ski']
        if ski:
            jobs.append(('ski-' + content.slugify(region), region, ski, [(506, 680, 'desktop'), (390, 480, 'phone')]))
    h = hashlib.sha1((str(VERSION) + json.dumps([(j[0], [(t['slug'], t['title'], t['activity'], t['kind'], trip_inputs(t)) for t in j[2]])
                                                  for j in jobs], sort_keys=True)).encode()).hexdigest()
    mf = os.path.join(folder, 'meta.json')
    if not force and os.path.exists(mf) and json.load(open(mf)).get('hash') == h:
        return False
    if os.path.exists(folder):
        shutil.rmtree(folder)
    set_out(folder)
    meta = {'hash': h, 'maps': {}}
    del OSM_FAILED[:]
    for key, region, ts, sizes in jobs:
        t0 = time.time()
        pins = []
        for t in ts:
            lat, lon = start_of(t)
            pins.append({'lat': lat, 'lon': lon, 'cat': t['cat'], 'key': t['slug'], 'title': t['title'], 'href': '@@ROOT@@' + t['url']})
        tracks = [x for t in ts for x in site_tracks(t)]
        specs = [dict(OVERVIEW, name='%s-%s' % (key, v), w=w, h=h_, pins=pins, pad=0.10, priority_peaks=[p for t in ts for p in (t['map'].get('peaks') or [])][:6],
                      aria='Map of %s trips in %s' % ('ski' if key.startswith('ski-') else 'all', region),
                      **({'scale_corner': 'bl', 'reserve': [(w - 208, h_ - 36, w, h_)], 'pad_bottom_px': 40} if v == 'phone' else {})) for w, h_, v in sizes]
        for s in specs:
            s['tracks'] = [dict(x) for x in tracks]
        osm = fetch_osm(union([frame_bbox(s, s['tracks']) for s in specs]), 'overview')
        for s in specs:
            s['osm_data'] = osm
            m = render_map(s)
            meta['maps'][s['name']] = {'w': s['w'], 'h': s['h'], 'png': m.get('png'), 'base': m.get('base'), 'region': region,
                                       'trips': [t['slug'] for t in ts], 'clusters': m.get('clusters')}
        print('rendered site map %-28s %5.0fs' % (key, time.time() - t0))
    for f in os.listdir(folder):
        if f.endswith('.meta.json'):
            os.remove(os.path.join(folder, f))
    meta['regions'] = sorted(groups)
    if OSM_FAILED:
        meta['hash'] = None
    optimize_images(folder, meta)
    json.dump(meta, open(mf, 'w'), indent=1, default=str)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('slugs', nargs='*')
    ap.add_argument('--site', action='store_true', help='only region/section maps')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--no-site', action='store_true', help='skip region/section maps')
    ap.add_argument('--charts', action='store_true', help='only re-render elevation profiles / speed charts (fast, offline)')
    a = ap.parse_args()
    trips = content.load_all()
    if a.charts:
        for t in trips:
            if (a.slugs and t['slug'] not in a.slugs) or t['kind'] in ('series', 'planned'):
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
        return
    if not a.site:
        for t in trips:
            if a.slugs and t['slug'] not in a.slugs:
                continue
            render_trip(t, force=a.force)
    if not a.no_site:
        render_site(trips, force=a.force and (a.site or not a.slugs))
    # drop renders of trips that no longer exist
    live = {t['slug'] for t in content.load_all(include_drafts=True)}
    tdir = os.path.join(OUT, 'trips')
    for d in (os.listdir(tdir) if os.path.isdir(tdir) else []):
        if d not in live:
            shutil.rmtree(os.path.join(tdir, d))
            print('removed stale render', d)


if __name__ == '__main__':
    main()
