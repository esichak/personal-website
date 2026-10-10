"""Safe GPX inspection and approximate measurement for tick-list goals (tools/ticklist.py, tools/render.py).

A goal's GPX is somebody's plan or somebody else's recording, not Eric's track, so this module never guesses: it keeps
routes (rte/rtept) and tracks (trk/trkseg/trkpt) apart, keeps every segment, measures each segment on its own (a gap
between segments is never bridged into a fictional traverse), reports elevation as full / partial / none instead of
inventing a profile, and never reads the timestamps as a date. Parsing is bounded: a size cap, a point cap, no DTD or
entity declarations, finite coordinates in range. The source bytes are never rewritten here; the importer copies the
file (or the chosen element, byte for byte) and records its SHA-256.
"""
import hashlib
import math
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import geo

MAX_BYTES = 30_000_000
MAX_POINTS = 500_000
METHOD = 'ticklist-gpx-1'
_BAD = re.compile(rb'<!\s*(DOCTYPE|ENTITY)', re.I)
_ROOT = re.compile(rb'<gpx\b[^>]*>', re.I)


class GpxError(ValueError):
    """The file cannot be used as a goal route; the message says why."""


class SelectionNeeded(GpxError):
    """The file holds several tracks / routes: the author must choose one (trk:<i> or rte:<i>)."""


class NoRoute(GpxError):
    """No track or route points (a waypoint-only or empty file): a valid idea, not a route."""


def _local(tag):
    return tag.rsplit('}', 1)[-1]


def _time(el):
    if el is None or not el.text:
        return None
    s = el.text.strip().replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(s.split('.')[0] + ('+00:00' if '+' not in s[10:] else '')).timestamp()
    except ValueError:
        return None


def _num(s, what, where):
    try:
        v = float(s)
    except (TypeError, ValueError):
        raise GpxError('%s: %s is not a number (%r)' % (where, what, s))
    if not math.isfinite(v):
        raise GpxError('%s: %s is not finite (%r)' % (where, what, s))
    return v


def _point(el, where):
    lat = _num(el.get('lat'), 'lat', where)
    lon = _num(el.get('lon'), 'lon', where)
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise GpxError('%s: coordinates out of range (lat %s, lon %s)' % (where, lat, lon))
    ele = time = None
    for ch in el:
        name = _local(ch.tag)
        if name == 'ele':
            ele = _num(ch.text, 'ele', where)
        elif name == 'time':
            time = _time(ch)
    return (lat, lon, ele, time)


def inspect(path):
    """{'tracks': [{'name', 'segments': [[(lat, lon, ele|None, time|None), ...], ...]}], 'routes': [{'name', 'points'}],
    'waypoints': n, 'bytes': n, 'sha256': hex}. GpxError for anything unsafe or malformed."""
    where = os.path.basename(str(path))
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        raise GpxError('%s: %d bytes is over the %d-byte limit' % (where, size, MAX_BYTES))
    with open(path, 'rb') as fh:
        data = fh.read()
    if _BAD.search(data):
        raise GpxError('%s: DOCTYPE and ENTITY declarations are not accepted' % where)
    try:
        root = ET.fromstring(data)
    except ET.ParseError as ex:
        raise GpxError('%s: not well-formed XML (%s)' % (where, ex))
    if _local(root.tag) != 'gpx':
        raise GpxError('%s: the root element is <%s>, not <gpx>' % (where, _local(root.tag)))
    info = {'tracks': [], 'routes': [], 'waypoints': 0, 'bytes': size, 'sha256': hashlib.sha256(data).hexdigest()}
    count = 0

    def name_of(el):
        for ch in el:
            if _local(ch.tag) == 'name':
                return (ch.text or '').strip() or None
        return None
    for el in root:
        kind = _local(el.tag)
        if kind == 'trk':
            segs = []
            for seg in el:
                if _local(seg.tag) != 'trkseg':
                    continue
                pts = [_point(p, where) for p in seg if _local(p.tag) == 'trkpt']
                count += len(pts)
                if count > MAX_POINTS:
                    raise GpxError('%s: more than %d points' % (where, MAX_POINTS))
                if pts:
                    segs.append(pts)
            info['tracks'].append({'name': name_of(el), 'segments': segs})
        elif kind == 'rte':
            pts = [_point(p, where) for p in el if _local(p.tag) == 'rtept']
            count += len(pts)
            if count > MAX_POINTS:
                raise GpxError('%s: more than %d points' % (where, MAX_POINTS))
            info['routes'].append({'name': name_of(el), 'points': pts})
        elif kind == 'wpt':
            _point(el, where)
            info['waypoints'] += 1
    return info


def candidates(info):
    """The selectable geometries, tracks first then routes, in file order; a route is one segment. Tracks and routes
    without points are left out."""
    out = []
    for i, t in enumerate(info['tracks']):
        if t['segments']:
            out.append({'type': 'trk', 'index': i, 'name': t['name'], 'segments': t['segments'],
                        'points': sum(len(s) for s in t['segments'])})
    for i, r in enumerate(info['routes']):
        if r['points']:
            out.append({'type': 'rte', 'index': i, 'name': r['name'], 'segments': [r['points']], 'points': len(r['points'])})
    return out


def describe(c):
    return '%s:%d%s (%d points, %d segment%s)' % (c['type'], c['index'], (' "%s"' % c['name']) if c['name'] else '', c['points'],
                                                 len(c['segments']), '' if len(c['segments']) == 1 else 's')


def select(info, choice=None):
    """The chosen candidate: the only one when there is one, else the one named by choice ('trk:0' / 'rte:1')."""
    cands = candidates(info)
    if not cands:
        raise NoRoute('no track or route points%s: an idea can be saved without a route, but this file is not one'
                      % ((' (%d waypoints only)' % info['waypoints']) if info['waypoints'] else ''))
    if choice is None:
        if len(cands) == 1:
            return cands[0]
        raise SelectionNeeded('the file holds %d routes / tracks; choose one with --select:\n  %s'
                              % (len(cands), '\n  '.join(describe(c) for c in cands)))
    m = re.fullmatch(r'(trk|rte):(\d+)', str(choice).strip())
    if not m:
        raise GpxError('--select must look like trk:0 or rte:1, got %r' % choice)
    for c in cands:
        if c['type'] == m.group(1) and c['index'] == int(m.group(2)):
            return c
    raise SelectionNeeded('%s is not in the file; the choices are:\n  %s' % (choice, '\n  '.join(describe(c) for c in cands)))


def measure(segments):
    """Approximate numbers from the selected geometry: each segment's own polyline length added up (nothing bridged),
    gain / loss only when every point has an elevation (the 3 m hysteresis tracks.compute_stats uses), high / low when any
    point has one. Nothing is read from timestamps but whether they exist."""
    pts = [p for seg in segments for p in seg]
    dist = sum((geo.cumdist(seg)[-1] if len(seg) > 1 else 0.0) for seg in segments)
    eles = [p[2] for p in pts if p[2] is not None]
    elevation = 'full' if pts and len(eles) == len(pts) else ('partial' if eles else 'none')
    gain = loss = None
    if elevation == 'full':
        g = l = 0.0
        for seg in segments:
            ref = seg[0][2]
            for p in seg[1:]:
                e = p[2]
                if e - ref >= 3:
                    g += e - ref
                    ref = e
                elif ref - e >= 3:
                    l += ref - e
                    ref = e
        gain, loss = int(round(g)), int(round(l))
    return {'distance_km': round(dist / 1000.0, 2), 'gain_m': gain, 'loss_m': loss,
            'high_m': int(round(max(eles))) if eles else None, 'low_m': int(round(min(eles))) if eles else None,
            'elevation': elevation, 'times': any(p[3] is not None for p in pts), 'points': len(pts),
            'segments': len(segments), 'sparse': len(pts) < 10}


def extract_bytes(path, cand):
    """The bytes to publish for a chosen candidate: the whole file when it is the only candidate, else a new document
    holding the original <gpx> start tag and the chosen <trk> / <rte> element sliced out of the source byte for byte."""
    with open(path, 'rb') as fh:
        data = fh.read()
    if len(candidates(inspect(path))) == 1:
        return data
    tag = cand['type'].encode()
    matches = list(re.finditer(rb'<' + tag + rb'\b.*?</' + tag + rb'\s*>', data, re.S))
    # candidates() skips empty tracks / routes, so count the element among all of its kind in file order
    if cand['index'] >= len(matches):
        raise GpxError('could not find %s:%d in the file' % (cand['type'], cand['index']))
    root = _ROOT.search(data)
    head = data[:root.end()] if root else b'<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">'
    if not head.lstrip().startswith(b'<?xml'):
        head = b'<?xml version="1.0" encoding="UTF-8"?>\n' + head
    return head + b'\n' + matches[cand['index']].group(0) + b'\n</gpx>\n'


def as_tracks(path, key, cat):
    """One mapkit.Track per segment of the published goal file, in file order (tracks, then routes), so the renderer
    draws gaps as gaps. The importer publishes one candidate; an older file with several is drawn whole, segment by
    segment, never joined."""
    import mapkit
    info = inspect(path)
    segs = [s for c in candidates(info) for s in c['segments']]
    return [mapkit.Track(seg, key, cat) for seg in segs if len(seg) > 1]
