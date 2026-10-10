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
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime

import geo

MAX_BYTES = 30_000_000
MAX_POINTS = 500_000
METHOD = 'ticklist-gpx-1'
# A published goal file is served from the site's own origin as XML, so it must hold nothing a browser could run or
# fetch: no DTD or entity declarations (and no other <! markup but comments and CDATA), no processing instruction but
# the XML declaration (an xml-stylesheet instruction loads and applies XSLT), no XHTML / SVG / MathML namespace (script
# in those namespaces executes inside any XML document), no <script> and no javascript: URL anywhere.
_UNSAFE = [
    (re.compile(rb'<!(?!--|\[CDATA\[)', re.I), 'DOCTYPE, ENTITY and other <! declarations are not accepted'),
    (re.compile(rb'<\?(?!xml[\s?])', re.I), 'processing instructions (such as xml-stylesheet) are not accepted'),
    (re.compile(rb'http://www\.w3\.org/(1999/xhtml|2000/svg|1998/Math/MathML)', re.I), 'XHTML, SVG and MathML content is not accepted'),
    (re.compile(rb'<\s*script\b', re.I), '<script> is not accepted'),
    (re.compile(rb'javascript\s*:', re.I), 'javascript: URLs are not accepted'),
]


# the same checks again on the parsed document (namespaces resolved, character references decoded): the byte scan above
# cannot see '<svg:script>', 'xmlns="…/2000/sv&#103;"' or 'href="&#106;avascript:…"', and a browser would
_BAD_NS = ('http://www.w3.org/1999/xhtml', 'http://www.w3.org/2000/svg', 'http://www.w3.org/1998/math/mathml',
           'http://www.w3.org/1999/xlink', 'http://www.w3.org/2001/xml-events')
_BAD_ELEMENTS = frozenset(['script', 'iframe', 'object', 'embed', 'foreignobject', 'handler', 'listener', 'style'])
_BAD_SCHEMES = ('javascript:', 'vbscript:', 'data:', 'blob:', 'file:')
_CTRL = re.compile(r'[\x00-\x20\x7f\u200b-\u200f\u2028\u2029\ufeff]')


class GpxError(ValueError):
    """The file cannot be used as a goal route; the message says why."""


class SelectionNeeded(GpxError):
    """The file holds several tracks / routes: the author must choose one (trk:<i> or rte:<i>)."""


class NoRoute(GpxError):
    """No track or route points (a waypoint-only or empty file): a valid idea, not a route."""


def _local(tag):
    return tag.rsplit('}', 1)[-1]


_ZONE = re.compile(r'(Z|[+-]\d\d:?\d\d)$', re.I)


def _time(el):
    """A point's <time> as a unix timestamp, or None when it is absent or not an ISO date-time. Every xsd:dateTime form a
    GPX may carry is read: a trailing Z, +hh:mm or -hh:mm (also without the colon), fractions of a second, or no zone
    (taken as UTC). Only whether a file has times is ever used: a recorder's clock is not a trip date."""
    s = (el.text or '').strip() if el is not None else ''
    if not s:
        return None
    zone = '+00:00'
    m = _ZONE.search(s)
    if m and m.start() >= 10:   # after the date: '2026-07-04' alone ends in digits but carries no zone
        z, s = m.group(1), s[:m.start()]
        if z.upper() != 'Z':
            zone = z if ':' in z else z[:3] + ':' + z[3:]
    try:
        return datetime.fromisoformat(s.split('.')[0] + zone).timestamp()
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


# ---------------------------------------------------------------- what a file holds besides its line

_GEOMETRY = frozenset(['gpx', 'trk', 'trkseg', 'trkpt', 'rte', 'rtept', 'wpt', 'ele'])
_POINTS = frozenset(['trkpt', 'rtept', 'wpt'])
_FREE_TEXT = frozenset(['desc', 'cmt', 'src', 'keywords', 'type', 'sym', 'urlname'])
_LINKS = frozenset(['link', 'url'])
_FILE_INFO = frozenset(['author', 'email', 'copyright', 'bounds'])      # GPX 1.0 puts these straight under <gpx>
_POINT_FIELDS = frozenset(['magvar', 'geoidheight', 'fix', 'sat', 'hdop', 'vdop', 'pdop', 'ageofdgpsdata', 'dgpsid', 'course',
                           'speed', 'number'])
_XSI_LOCATION = '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
# where each geometry element belongs; one found anywhere else is not the line and is reported like any unknown element
_PLACE = {'trk': ('gpx',), 'rte': ('gpx',), 'wpt': ('gpx',), 'trkseg': ('trk',), 'trkpt': ('trkseg',), 'rtept': ('rte',),
          'ele': ('trkpt', 'rtept', 'wpt')}


def printable(text, limit=80):
    """Text taken from a GPX, safe to print in a report the author relies on: one line, every control or formatting
    character written as an escape (a track name must not be able to forge report lines, hide text or drive the
    terminal), quotes and backslashes escaped, cut to `limit` characters, wrapped in double quotes."""
    out = []
    for ch in str(text):
        cat = unicodedata.category(ch)
        if ch in '\r\n\t\x0b\x0c' or cat in ('Zl', 'Zp', 'Zs'):
            out.append(' ')
        elif cat.startswith('C'):                 # control, format (bidi, zero width), private use, unassigned
            out.append('\\u%04x' % ord(ch))
        elif ch in '"\\':
            out.append('\\' + ch)
        else:
            out.append(ch)
    line = re.sub(r' +', ' ', ''.join(out)).strip()
    if len(line) > limit:
        line = line[:limit - 1] + '…'
    return '"%s"' % line


def printable_name(name, limit=40):
    """An element or attribute name from a GPX, for a list in the report: the same escaping, no quotes."""
    return printable(name, limit)[1:-1]


def _contents(root, data):
    """Everything the document holds that is not the line itself. Every element is either geometry (gpx, trk, trkseg,
    trkpt, rte, rtept, wpt, ele, with lat / lon) or lands in one of these, so an empty result really means "nothing but
    the line", and something this code has never heard of is still reported (under 'other'):

    creator (the <gpx> creator text), names (tracks and routes), waypoint_names, point_names (count of named track or
    route points), descriptions (count of desc / cmt / src / keywords / type / sym texts), metadata (the tag names
    inside <metadata>, plus author / email / copyright / bounds / name / time found straight under <gpx>), extensions,
    links (link and url elements), times (any <time> on a point), point_fields (GPS quality fields such as sat or
    hdop), attributes (attribute names other than lat, lon, the root's version and creator), other (element names
    not covered above, outside <extensions> and <metadata>), text (loose text between elements), comments."""
    c = {'creator': (root.get('creator') or '').strip() or None, 'names': [], 'waypoint_names': [], 'point_names': 0,
         'descriptions': 0, 'metadata': set(), 'extensions': False, 'links': 0, 'times': False, 'point_fields': set(),
         'attributes': set(), 'other': set(), 'text': False, 'comments': b'<!--' in data}

    def attrs(el, own):
        for k in el.attrib:
            if k not in own:
                c['attributes'].add('schemaLocation' if k == _XSI_LOCATION else _local(k))

    def loose(el):
        if (el.text or '').strip() or any((ch.tail or '').strip() for ch in el):
            c['text'] = True

    def walk(el, parent, inside):
        name = _local(el.tag)
        if inside == 'extensions':
            return                                   # everything under <extensions> is reported as one thing
        if inside == 'metadata':
            if (el.text or '').strip() or el.attrib or len(el):
                c['metadata'].add(name)
            for ch in el:
                walk(ch, name, 'metadata')
            return
        if name == 'extensions':
            c['extensions'] = True
            return
        if name == 'metadata':
            for ch in el:
                walk(ch, name, 'metadata')
            if el.attrib:
                attrs(el, ())
            return
        if name in _GEOMETRY and el is not root and parent not in _PLACE.get(name, ()):
            c['other'].add(name)                     # e.g. a <trk> inside a <wpt>: points that are not on the line
            return
        if name in _GEOMETRY and name != 'ele':
            attrs(el, ('version', 'creator') if el is root else (('lat', 'lon') if name in _POINTS else ()))
            loose(el)
            for ch in el:
                walk(ch, name, None)
            return
        if name == 'ele':
            attrs(el, ())
            if len(el):
                c['other'].add(name)
            return
        text = (el.text or '').strip()
        if name == 'time':
            if parent in _POINTS:
                c['times'] = c['times'] or bool(text)
            elif text:
                c['metadata'].add(name)               # a file-level time (GPX 1.0) is file information
        elif name == 'name':
            if not text:
                pass
            elif parent in ('trk', 'rte'):
                c['names'].append(text)
            elif parent == 'wpt':
                c['waypoint_names'].append(text)
            elif parent in ('trkpt', 'rtept'):
                c['point_names'] += 1
            else:
                c['metadata'].add(name)               # the file's own name, straight under <gpx>
        elif name in _FREE_TEXT:
            if text:
                c['descriptions'] += 1
        elif name in _LINKS:
            c['links'] += 1
        elif name in _FILE_INFO:
            c['metadata'].add(name)
        elif name in _POINT_FIELDS:
            c['point_fields'].add(name)
        else:
            c['other'].add(name)
        if name not in _LINKS and name not in _FILE_INFO:
            attrs(el, ())
        if len(el) and name not in _LINKS and name not in _FILE_INFO:
            c['other'].add(name)                      # a simple field that holds elements is not a simple field
    walk(root, None, None)
    for k in ('metadata', 'point_fields', 'attributes', 'other'):
        c[k] = sorted(c[k])
    return c


def inspect(path):
    """{'tracks': [{'name', 'segments': [[(lat, lon, ele|None, time|None), ...], ...]}], 'routes': [{'name', 'points'}],
    'waypoints': n, 'bytes': n, 'sha256': hex}. GpxError for anything unsafe or malformed."""
    where = printable_name(os.path.basename(str(path)), 80)   # a file name is file text too: escaped in every message
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        raise GpxError('%s: %d bytes is over the %d-byte limit' % (where, size, MAX_BYTES))
    with open(path, 'rb') as fh:
        data = fh.read()
    return inspect_bytes(data, where)


def inspect_bytes(data, where):
    """inspect() on bytes already read (also run on the document extract_bytes assembles, so what is published is checked
    as a whole, not only as slices of a checked file)."""
    size = len(data)
    if size > MAX_BYTES:
        raise GpxError('%s: %d bytes is over the %d-byte limit' % (where, size, MAX_BYTES))
    # the safety scan runs on the UTF-8 text; a file in another encoding (a UTF-16 BOM, NUL bytes) would slip past it
    if data.startswith((b'\xff\xfe', b'\xfe\xff')) or b'\x00' in data:
        raise GpxError('%s: only UTF-8 (or ASCII) GPX files are accepted' % where)
    try:
        data.decode('utf-8')
    except UnicodeDecodeError:
        raise GpxError('%s: only UTF-8 (or ASCII) GPX files are accepted' % where)
    for rx, why in _UNSAFE:
        if rx.search(data):
            raise GpxError('%s: %s' % (where, why))
    _scan_parsed(data, where)
    try:
        root = ET.fromstring(data)
    except ET.ParseError as ex:
        raise GpxError('%s: not well-formed XML (%s)' % (where, ex))
    if _local(root.tag) != 'gpx':
        raise GpxError('%s: the root element is <%s>, not <gpx>' % (where, printable_name(_local(root.tag))))
    info = {'tracks': [], 'routes': [], 'waypoints': 0, 'bytes': size, 'sha256': hashlib.sha256(data).hexdigest(),
            'contains': _contents(root, data)}
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


def _scan_parsed(data, where):
    """Refuse what a browser's XML parser would see even though the raw bytes hide it: an encoding other than UTF-8 in the
    XML declaration (the bytes were checked as UTF-8; a browser would decode them as declared), any DOCTYPE or processing
    instruction, an XHTML / SVG / MathML / XLink namespace however the URI is spelled, a <script>-like element under any
    prefix, an on* event attribute, and any attribute whose value starts with a javascript: / vbscript: / data: scheme
    once character references are decoded and control characters dropped (browsers drop them from URLs too). A parse
    error here, including an encoding expat does not know, is reported as not well-formed."""
    import xml.parsers.expat as expat
    parser = expat.ParserCreate(namespace_separator=' ')
    bad = []

    def fail(why):
        if not bad:
            bad.append(why)

    def xmldecl(version, encoding, standalone):
        if encoding and encoding.strip().lower().replace('_', '-') not in ('utf-8', 'utf8'):
            fail('the XML declaration says encoding=%r; only UTF-8 files are accepted' % encoding)

    def doctype(*_a):
        fail('DOCTYPE, ENTITY and other <! declarations are not accepted')

    def pi(target, _data):
        fail('processing instructions (such as %s) are not accepted' % printable_name(target))

    def ns(prefix, uri):
        u = _CTRL.sub('', uri or '').lower().rstrip('/')
        if u in _BAD_NS or 'w3.org/1999/xhtml' in u or 'w3.org/2000/svg' in u or 'mathml' in u:
            fail('XHTML, SVG and MathML content is not accepted (namespace %r)' % uri)

    def start(name, attrs):
        local = name.rsplit(' ', 1)[-1].lower()
        if local in _BAD_ELEMENTS:
            fail('<%s> is not accepted' % printable_name(local))
        for k, v in attrs.items():
            kl = k.rsplit(' ', 1)[-1].lower()
            if kl.startswith('on') and len(kl) > 2:
                fail('event attributes such as %s are not accepted' % printable_name(kl))
            vv = _CTRL.sub('', v or '').lower()
            if vv.startswith(_BAD_SCHEMES):
                fail('%s: URLs are not accepted' % vv.split(':', 1)[0])
    parser.XmlDeclHandler = xmldecl
    parser.StartDoctypeDeclHandler = doctype
    parser.ProcessingInstructionHandler = pi
    parser.StartNamespaceDeclHandler = ns
    parser.StartElementHandler = start
    try:
        parser.Parse(data, True)
    except expat.ExpatError as ex:
        if bad:
            raise GpxError('%s: %s' % (where, bad[0]))
        raise GpxError('%s: not well-formed XML (%s)' % (where, ex))
    if bad:
        raise GpxError('%s: %s' % (where, bad[0]))


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
    return '%s:%d%s (%d points, %d segment%s)' % (c['type'], c['index'], (' ' + printable(c['name'], 60)) if c['name'] else '', c['points'],
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


def _layout(data):
    """(root start byte, byte after the root start tag, [(local name, start byte, end byte)] of every child element of
    the root), all from the parser's own positions: the root start tag ends where the first thing after it (text,
    comment, child) begins, so a '>' inside an attribute value or a '<gpx' inside a comment cannot mislead a slice."""
    import xml.parsers.expat as expat
    stack, out = [], []
    pos = {'root': None, 'after': None}
    parser = expat.ParserCreate(namespace_separator='}')

    def mark():
        if pos['root'] is not None and pos['after'] is None:
            pos['after'] = parser.CurrentByteIndex

    def start(name, attrs):
        mark()
        if pos['root'] is None:
            pos['root'] = parser.CurrentByteIndex
        stack.append((name, parser.CurrentByteIndex))

    def end(name):
        mark()
        nm, at = stack.pop()
        if len(stack) == 1:  # a child of the root
            close = data.index(b'>', parser.CurrentByteIndex) + 1
            out.append((nm.rsplit('}', 1)[-1], at, close))

    def other(*_a):
        mark()
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = other
    parser.CommentHandler = other
    parser.ProcessingInstructionHandler = other
    parser.DefaultHandler = other
    parser.Parse(data, True)
    return pos['root'], pos['after'], out


def _spans(data):
    return _layout(data)[2]


def extract_bytes(path, cand):
    """The bytes to publish for a chosen candidate: the whole file when it is the only candidate, else a new document
    holding the original <gpx> start tag and the chosen <trk> / <rte> element sliced out of the source byte for byte
    (its position comes from the XML parser, so comments or text that merely contain '<trk' cannot shift the choice)."""
    with open(path, 'rb') as fh:
        data = fh.read()
    if len(candidates(inspect(path))) == 1:
        return data
    kind = cand['type']
    root_at, after_root, spans = _layout(data)
    spans = [sp for sp in spans if sp[0] == kind]
    if cand['index'] >= len(spans):
        raise GpxError('could not find %s:%d in the file' % (kind, cand['index']))
    _nm, a, b = spans[cand['index']]
    head = data[:after_root]   # the declaration, anything before the root, and the whole root start tag
    root_name = re.match(rb'<([^\s/>]+)', data[root_at:]).group(1)
    if head.startswith(b'\xef\xbb\xbf'):
        head = head[3:]   # a UTF-8 byte order mark: dropped, so a declaration added below is not pushed behind it
    if not head.lstrip().startswith(b'<?xml'):
        head = b'<?xml version="1.0" encoding="UTF-8"?>\n' + head.lstrip()
    out = head + b'\n' + data[a:b] + b'\n</' + root_name + b'>\n'
    # the assembled document is checked as a whole, and must hold exactly the chosen geometry and nothing else
    where = printable_name(os.path.basename(str(path)), 80)
    got = candidates(inspect_bytes(out, where))
    if len(got) != 1 or got[0]['segments'] != cand['segments']:
        raise GpxError('%s: the extracted %s:%d does not reproduce the chosen geometry; publish the whole file or export '
                       'the route on its own' % (where, kind, cand['index']))
    return out


def as_tracks(path, key, cat):
    """One mapkit.Track per segment of the published goal file, in file order (tracks, then routes), so the renderer
    draws gaps as gaps. The importer publishes one candidate; an older file with several is drawn whole, segment by
    segment, never joined."""
    import mapkit
    info = inspect(path)
    segs = [s for c in candidates(info) for s in c['segments']]
    return [mapkit.Track(seg, key, cat) for seg in segs if len(seg) > 1]
