"""What a render was drawn from: the input hashes tools/render.py stores in meta.json and compares before drawing.

They live here, apart from render.py, so that the content checks (lib/checks.py) can tell a stale render from a current
one without importing the renderer (mapkit and its drawing code). render.py imports every name below and keeps using
them under its own names (render.trip_inputs, render.journal_parts, ...); the hashes are the very expressions render.py
always computed, so moving them re-renders nothing.

    renderkey.trip_inputs(t)          the hash in rendered/trips/<slug>/meta.json
    renderkey.site_hash(site_jobs(trips)[0])   the hash in rendered/site/meta.json (trips as content.load_all orders them)
"""
import hashlib
import html
import json
import os
import re

import content
import goals

# bump once per render round, after the renderer changes (docs/DEVELOPING.md, "A render round"). A bump redraws every
# file under rendered/ (3,579 since the 2026 round); git keeps only the ones whose bytes change: 9.7 MB of packed history
# when only the SVG changed (a9baab9, 2026-09-28), 18.8 MB for the 2026 round (f2132d2, VERSION 8: the hillshades
# re-encoded at q80 too, 1,427 files changed). After a round, `git diff --stat -- rendered | tail -1` and the packed
# cost (docs/DEVELOPING.md, "Storage budget") go in the commit message.
VERSION = 8
PANEL_TRIPS = 5  # a region gets a Mountain biking or Hiking panel map from this many trips of the activity (maps-15)
MIN_REGION_TRIPS = 3
INPUT_KEYS = ('title', 'activity', 'kind', 'map', 'stats', 'route_shape')
# what a site map is drawn from: a trip's own inputs less its title, which a site map shows only as the text of its pin
# and cluster labels, and the build writes those from the trips as they are (core.relabel)
SITE_INPUT_KEYS = tuple(k for k in INPUT_KEYS if k != 'title')


def file_hash(paths):
    h = hashlib.sha1()
    for p in paths:
        if p and os.path.exists(p):
            with open(p, 'rb') as fh:
                h.update(fh.read())
    return h.hexdigest()


def input_files(t):
    """The GPX files a trip's render reads: its own track.gpx and every day's (None where there is none)."""
    return [t['track']] + [d['track'] for d in t['days']]


def input_fields(t, names=INPUT_KEYS):
    """The front-matter values a trip's render is drawn from, as the JSON text the hash covers."""
    keys = {k: t['meta'].get(k) for k in names}
    keys['days'] = [(d['id'], d['hut'], d['transfer_before'], d['stats'], d['label']) for d in t['days']]
    return json.dumps(keys, sort_keys=True, default=str)


TALL = 1.4   # a report map's track box taller than this (ground height / width) gets the tall frame (maps-03)
_SHAPES = {}
_POINT = re.compile(r'<(?:trkpt|rtept)\b([^>]*)>')
_LAT, _LON = re.compile(r'\blat\s*=\s*["\']([-0-9.]+)'), re.compile(r'\blon\s*=\s*["\']([-0-9.]+)')


def track_aspect(path):
    """A GPX file's track box, ground height over width, read with a regular expression (no parser: the content checks
    hash every trip on every run), cached by the file's size and time. None without two points apart."""
    try:
        st = os.stat(path)
    except (OSError, TypeError):
        return None
    key = (path, st.st_size, st.st_mtime)
    if key not in _SHAPES:
        lats, lons = [], []
        with open(path, encoding='utf-8', errors='replace') as fh:
            for m in _POINT.finditer(fh.read()):
                a, o = _LAT.search(m.group(1)), _LON.search(m.group(1))
                if a and o:
                    lats.append(float(a.group(1)))
                    lons.append(float(o.group(1)))
        if len(lats) < 2:
            _SHAPES[key] = None
        else:
            import math
            dy = (max(lats) - min(lats)) * 111320.0
            dx = (max(lons) - min(lons)) * 111320.0 * math.cos(math.radians((max(lats) + min(lats)) / 2))
            _SHAPES[key] = (dy / dx) if dx > 1 else (float('inf') if dy > 1 else None)
    return _SHAPES[key]


def report_frame(t):
    """'tall' when a single-day report's or a goal's map gets the 1440 x 800 / 718 x 500 frame (its track box is taller
    than TALL to 1 across), else None: the 1440 x 640 / 718 x 400 one (maps-03). Multi-day and journal maps keep theirs."""
    if t['kind'] not in ('trip', 'planned') or t['days'] or not t['track']:
        return None
    a = track_aspect(t['track'])
    return 'tall' if a is not None and a > TALL else None


FRAME_SINCE = 8   # the renderer version that drew tall routes in the tall frame (maps-03); before it, no frame in the hash


def trip_inputs(t, version=None):
    """The hash in rendered/trips/<slug>/meta.json. version: as an older renderer would have hashed the trip (render.py
    --status tells a version bump from a changed track that way)."""
    version = VERSION if version is None else version
    # the frame enters the hash only when it is not the default, so a later change of the rule redraws only those trips
    frame = report_frame(t) if version >= FRAME_SINCE else None
    return hashlib.sha1((input_fields(t) + file_hash(input_files(t)) + str(version) + ('|frame=' + frame if frame else '')).encode()).hexdigest()


def site_inputs(t):
    """trip_inputs without the title (SITE_INPUT_KEYS): what a trip changes on the region and ski maps."""
    return hashlib.sha1((input_fields(t, SITE_INPUT_KEYS) + file_hash(input_files(t)) + str(VERSION)).encode()).hexdigest()


def input_parts(t):
    """{'fields', 'files', 'version'}: the three things trip_inputs joins, each hashed on its own. render.py writes them
    into meta.json beside the hash, so `render.py --status` can say which of them changed since."""
    return {'fields': hashlib.sha1(input_fields(t).encode()).hexdigest(), 'files': file_hash(input_files(t)), 'version': VERSION}


def no_route(t):
    """A tick-list goal saved without a GPX (an idea): there is nothing to draw."""
    return t['kind'] == 'planned' and not t['track']


def no_track(t):
    """A report without a recording: no track.gpx of its own and no day with one. There is nothing to draw, and the site
    does not show a render left from when it had a track (sitegen.core.has_track)."""
    return t['kind'] != 'planned' and not (t['track'] or any(d['track'] for d in t['days']))


def goal_has_line(t):
    """Whether a tick-list goal has a line to draw on the region maps: render.goal_lines(t) is not empty, worked out
    without mapkit (gpxroute.as_tracks keeps every segment of more than one point)."""
    if not t['track']:
        return False
    import gpxroute
    return any(len(seg) > 1 for c in gpxroute.candidates(gpxroute.inspect(t['track'])) for seg in c['segments'])


_ELEVATION = {}


def file_elevation(t):
    """'full', 'partial' or 'none': how much of a tick-list goal's published line has an elevation (gpxroute.measure over
    every segment render.py draws), cached by the file's size and time. None for a report, for a goal without a GPX and
    for a file gpxroute refuses (the content checks report that one)."""
    if t['kind'] != 'planned' or not t['track']:
        return None
    try:
        st = os.stat(t['track'])
    except OSError:
        return None
    key = (t['track'], st.st_size, st.st_mtime)
    if key not in _ELEVATION:
        import gpxroute
        try:
            segs = [seg for c in gpxroute.candidates(gpxroute.inspect(t['track'])) for seg in c['segments']]
        except gpxroute.GpxError:
            segs = []
        _ELEVATION[key] = gpxroute.measure(segs)['elevation'] if segs else None
    return _ELEVATION[key]


def wants_terrain(t):
    """Whether render.py estimates a goal's gain from terrain data (meta.json 'terrain', gpxroute.measure_terrain): a goal
    whose published line has no elevation, or only some. A goal whose file has full elevation keeps the numbers measured
    from the file alone; a report never gets one."""
    return file_elevation(t) in ('none', 'partial')


def terrain_reason(t, meta):
    """Why a goal's meta.json needs its terrain estimate (written again), or None: render.py --status and render_trip ask
    this when the maps themselves are up to date, and the content checks for a published goal. meta: the meta.json
    object."""
    if not wants_terrain(t):
        return None
    have = meta.get('terrain') if isinstance(meta, dict) else None
    if not isinstance(have, dict):
        return 'no terrain estimate of the gain yet (the file has %s)' % (
            'no elevation' if file_elevation(t) == 'none' else 'elevation for only part of the line')
    import gpxroute
    if have.get('method') != gpxroute.TERRAIN_METHOD:
        return 'terrain estimate made by an older method (%s, now %s)' % (have.get('method'), gpxroute.TERRAIN_METHOD)
    return None


def journal_parts(trips):
    """{region: [part]}: a journal (kind: series) spans many regions and is filed under none of them; its region_days
    (content.py) say which days lie where, and those days are drawn on that region's map. A part is the content's own
    ({'region', 'title', 'key', 'days', 'stretches'}) with the journal under 'trip' and only the days that have a track. A part
    whose listed days hold no track has no entry."""
    parts = {}
    for t in trips:
        if t['kind'] != 'series':
            continue
        for rd in t.get('region_days') or []:
            days = [d for d in rd['days'] if d['track']]
            if days:
                parts.setdefault(rd['region'], []).append(dict(rd, days=days, trip=t))
    return parts


def site_jobs(trips):
    """(jobs, groups, mapped): the region and ski maps render_site draws. jobs: [(map key, region, trips, sizes, journal
    parts)]; groups: {region: trips filed under it}; mapped: the regions that get a region map. trips: content.load_all()'s
    list (no drafts, newest first): the order is part of the site hash."""
    groups = {}
    for t in trips:
        if t['kind'] == 'series' or not t['region']:
            continue
        if t['kind'] == 'planned' and not (goals.is_active(t.get('goal')) and goal_has_line(t)):
            # region maps show future routes: a completed or archived goal leaves them (the report it led to has its own
            # line), and an idea without a route, or a file with no line, has no place on a map yet
            continue
        groups.setdefault(t['region'], []).append(t)
    jobs = []
    mapped = []
    parts = journal_parts(trips)
    for region, ts in groups.items():
        # a report without a track has no line and no start to pin: it stays in the region's list (all_regions) and out
        # of the maps
        ts = [t for t in ts if not no_track(t)]
        # overview maps only where there is something to overview; one-off trips elsewhere are listed without a map
        if len(ts) >= MIN_REGION_TRIPS:
            mapped.append(region)
            # the region's own map also draws the journal days that lie in it; they are no report of the region, so they
            # do not count towards MIN_REGION_TRIPS, and the ski maps do not take them
            jobs.append(('region-' + content.slugify(region), region, ts, [(718, 620, 'desktop'), (390, 480, 'phone')],
                         parts.get(region, [])))
        # a section page's panel map (maps-15): ski from two trips of a region, rides and hikes from PANEL_TRIPS
        for act, least in (('ski', 2), ('mtb', PANEL_TRIPS), ('hike', PANEL_TRIPS)):
            some = [t for t in ts if t['activity'] == act]
            if len(some) >= least:
                jobs.append(('%s-%s' % (act, content.slugify(region)), region, some, [(506, 680, 'desktop'), (390, 480, 'phone')], []))
    return jobs, groups, mapped


def site_hash(jobs, inputs=site_inputs):
    """The hash of rendered/site/meta.json for these jobs. inputs: site_inputs, or a function that gives the same
    answers from a cache (the content checks hash each trip once per run). A trip's title is not in it (Phase 9): the
    build writes the titles into the maps' labels, so a retitle draws the trip's own maps again and no site map. A
    journal part's name and its journal's title stay: they are the line's own label."""
    return hashlib.sha1((str(VERSION) + json.dumps([(j[0], [(t['slug'], t['activity'], t['kind'], inputs(t)) for t in j[2]],
                                                    [(pt['key'], pt['title'], pt['trip']['title'], [d['id'] for d in pt['days']], inputs(pt['trip']))
                                                     + ((sorted((pt.get('stretches') or {}).items()),) if pt.get('stretches') else ())
                                                     for pt in j[4]])
                                                   for j in jobs], sort_keys=True)).encode()).hexdigest()


def site_hash_with_titles(jobs, inputs=trip_inputs):
    """The hash as render.py wrote it before Phase 9 (every title in it). A rendered/site/meta.json that carries it is
    up to date as well, until the site maps are drawn again and the new hash is written."""
    return hashlib.sha1((str(VERSION) + json.dumps([(j[0], [(t['slug'], t['title'], t['activity'], t['kind'], inputs(t)) for t in j[2]],
                                                    [(pt['key'], pt['title'], pt['trip']['title'], [d['id'] for d in pt['days']], inputs(pt['trip']))
                                                     + ((sorted((pt.get('stretches') or {}).items()),) if pt.get('stretches') else ())
                                                     for pt in j[4]])
                                                   for j in jobs], sort_keys=True)).encode()).hexdigest()


# the labels mapkit writes on a site map (core.relabel rewrites the same two at build time)
_PIN = re.compile(r'<a class="mk-pin" href="[^"]*" data-key="([^"]*)" aria-label="[^"]*"><title>([^<]*)</title>')
_CLUSTER = re.compile(r'<g class="mk-cluster" aria-hidden="true" data-keys="([^"]*)"><title>([^<]*)</title>')
_CLUSTER_HEAD = re.compile(r'\d+ reports? starts? here: ')   # mapkit.cluster_title's opening (copy-18, renderer 8)


def drawn_paths(site_dir, maps):
    """The fragment of each site map that meta.json lists (maps: its 'maps' object), as render.py wrote them."""
    return [os.path.join(site_dir, key + '.svg.html') for key in sorted(maps or {})]


def drawn_titles(paths):
    """{slug: title} as the site maps label each trip: a pin's <title>, or its place in a cluster's (the titles joined
    with '; ' in the order of data-keys, after 'N reports start here: ' since renderer 8). A cluster whose title does not
    split into one title per key (a title that holds '; ' itself, a repeated title, or 'and K more') says nothing about
    its trips; neither does a file that is not there."""
    out = {}
    for p in paths:
        try:
            with open(p, encoding='utf-8') as fh:
                s = fh.read()
        except OSError:
            continue
        for key, title in _PIN.findall(s):
            out.setdefault(html.unescape(key), html.unescape(title))
        for keys, titles in _CLUSTER.findall(s):
            titles = html.unescape(titles)
            head = _CLUSTER_HEAD.match(titles)
            ks, ts = html.unescape(keys).split(), titles[head.end() if head else 0:].split('; ')
            if len(ks) == len(ts):
                for k, t in zip(ks, ts):
                    out.setdefault(k, t)
    return out


def site_hash_as_drawn(jobs, drawn, inputs=trip_inputs):
    """site_hash_with_titles with each trip's title as the maps show it (drawn: drawn_titles): the hash render.py wrote
    before Phase 9, for maps whose trips have changed nothing since but a title, which the build writes into the labels.
    A trip whose title is not on the maps, or unchanged, keeps its own; inputs serves those (a cache), trip_inputs the
    others."""
    swapped = set()

    def swap(t):
        old = drawn.get(t['slug'])
        if old is None or old == t['title']:
            return t
        c = dict(t, title=old, meta=dict(t['meta'], title=old))
        swapped.add(id(c))
        return c
    again = [tuple(j[:2]) + ([swap(t) for t in j[2]],) + tuple(j[3:]) for j in jobs]
    try:
        return site_hash_with_titles(again, lambda t: trip_inputs(t) if id(t) in swapped else inputs(t))
    finally:
        swapped.clear()

