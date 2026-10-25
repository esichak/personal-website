"""What a render was drawn from: the input hashes tools/render.py stores in meta.json and compares before drawing.

They live here, apart from render.py, so that the content checks (lib/checks.py) can tell a stale render from a current
one without importing the renderer (mapkit and its drawing code). render.py imports every name below and keeps using
them under its own names (render.trip_inputs, render.journal_parts, ...); the hashes are the very expressions render.py
always computed, so moving them re-renders nothing.

    renderkey.trip_inputs(t)          the hash in rendered/trips/<slug>/meta.json
    renderkey.site_hash(site_jobs(trips)[0])   the hash in rendered/site/meta.json (trips as content.load_all orders them)
"""
import hashlib
import json
import os

import content
import goals

VERSION = 7  # bump after renderer changes to force a full re-render
MIN_REGION_TRIPS = 3
INPUT_KEYS = ('title', 'activity', 'kind', 'map', 'stats', 'route_shape')


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


def input_fields(t):
    """The front-matter values a trip's render is drawn from, as the JSON text the hash covers."""
    keys = {k: t['meta'].get(k) for k in INPUT_KEYS}
    keys['days'] = [(d['id'], d['hut'], d['transfer_before'], d['stats'], d['label']) for d in t['days']]
    return json.dumps(keys, sort_keys=True, default=str)


def trip_inputs(t):
    return hashlib.sha1((input_fields(t) + file_hash(input_files(t)) + str(VERSION)).encode()).hexdigest()


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
        ski = [t for t in ts if t['activity'] == 'ski']
        if len(ski) >= 2:
            jobs.append(('ski-' + content.slugify(region), region, ski, [(506, 680, 'desktop'), (390, 480, 'phone')], []))
    return jobs, groups, mapped


def site_hash(jobs, inputs=trip_inputs):
    """The hash of rendered/site/meta.json for these jobs. inputs: trip_inputs, or a function that gives the same answers
    from a cache (the content checks hash each trip once per run)."""
    return hashlib.sha1((str(VERSION) + json.dumps([(j[0], [(t['slug'], t['title'], t['activity'], t['kind'], inputs(t)) for t in j[2]],
                                                    [(pt['key'], pt['title'], pt['trip']['title'], [d['id'] for d in pt['days']], inputs(pt['trip']))
                                                     + ((sorted((pt.get('stretches') or {}).items()),) if pt.get('stretches') else ())
                                                     for pt in j[4]])
                                                   for j in jobs], sort_keys=True)).encode()).hexdigest()
