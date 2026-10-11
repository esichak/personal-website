#!/usr/bin/env python3
"""What the published tracks and photos say about where and when: a report for the author, on the author's machine.

  python3 tools/privacy_audit.py                  # counts only: nothing in it names a trip or a place
  python3 tools/privacy_audit.py --radius 300     # a wider idea of "the same place"
  python3 tools/privacy_audit.py --min-cluster 5  # only places that five or more separate outings share
  python3 tools/privacy_audit.py --site _site     # also check a built site (GPX copies, text files, images)
  python3 tools/privacy_audit.py --list           # also each shared place's trips and rounded position: a terminal only
  python3 tools/privacy_audit.py --near           # asks for a private point (not echoed, not stored)

Read-only and offline: it opens files for reading and prints. It writes no file, fetches nothing, looks no place up and
adds nothing to the site. The build does not run it and neither does CI (a public repository's CI log is public). The
default report is counts: no trip, no coordinate, no name, no id, no local path. --list adds, for every place that
several outings share, the member trips and a position rounded to three decimals, between two AUTHOR ONLY lines, and it
prints to a terminal only unless --list-anyway is given too.

The default report also keeps away from the single record. It gives no earliest or latest start, and the spread of start
times only to the quarter hour and only at a point with three tracks or more on either side of it; hours are joined
until none holds one or two tracks; a count of places below three reads "fewer than 3", and a count of tracks is given
only when its tracks start or finish at three places or more; a group of one or two files gets no point total and no
spacing. Plain counts of files (how many carry a time, how many photos have EXIF) stay exact: they say nothing of where
or when. Nothing is rounded beyond that, so the difference between two lines of section 3 can still be small. --list
prints every figure exactly, for the author.

It reads what the build publishes. Every file of a trip's photos/ folder and every days/*.md with its GPX is counted
whatever its name: tools/build.py copies every file of photos/, and tools/lib/content.py reads every day file. An iCloud
conflict copy under rendered/ is not counted, because the build leaves those out, nor is a trip folder named like one,
because the build refuses it.

What it cannot say is what a place is: a shared start may be a trailhead, a car park, a hut or a front door. That reading
is the author's. It also cannot see a private place visited once, because one track is not a group; --near counts the
tracks that pass a point you type instead. docs/PRIVACY_NOTES.md holds the counts and the decisions that follow from them.

One side effect is not this tool's own: it reads tracks with the site's code, and importing tools/lib/geo.py makes sure
the git-ignored folders .cache/tiles and .cache/osm exist, as it does for every tool here. No file is created.
"""
import argparse
import getpass
import hashlib
import json
import math
import os
import re
import struct
import sys
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import frontmatter  # noqa: E402
import geo  # noqa: E402
import gpxroute  # noqa: E402
import tracks  # noqa: E402

BANNER = ('AUTHOR ONLY: trip names and rounded coordinates follow. Do not paste this into the repository, a commit message, '
          'an issue, a pull request, a CI log or a chat.')
SITE_CREATOR = 'Eric Sichak trip reports'    # the creator text tools/lib/tracks.write_gpx gives every track it writes
SIZES = (5, 10)                              # the group sizes counted beside --min-cluster
TIGHT_H, SPREAD_H = 1.5, 4.0                 # start times at one place: "within 90 minutes" and "spread over 4 hours"
TEXT_EXT = ('.html', '.svg', '.json', '.xml', '.js', '.css', '.txt')    # the built site's text files (GPX left out)
IMAGE_EXT = ('.webp', '.jpg', '.jpeg', '.png')
_COPY = re.compile(r' \d+(?:\.[^/]*)?$')
FEW = 3                                      # the default report gives no figure about fewer places, tracks or files than this
PAIR_GAP = 40                                # two numbers no further apart than this many characters may be one position
# a decimal number the way a text file writes a coordinate: up to three digits, a point, three or more decimals
_NUM = re.compile(r'(?<![\d.])-?\d{1,3}\.\d{3,}')
_LONG = re.compile(r'\.\d\d\d')                    # no such number without this: a quick first look at a file
_CSS_VALUE = re.compile(r'--[A-Za-z_][\w-]*:\s*$')    # what stands right before the value of a CSS custom property
_HM = re.compile(r'^\s*(\d{1,2}):(\d{2})')
HEAD = ['PRIVACY AUDIT: counts only. Nothing below names a trip or a place; --list does, for the author.',
        'Where and when are never about one track or one place: no earliest or latest start, the spread to the quarter '
        'hour, hours joined until none holds one or two tracks, "fewer than %d" for a count of places below that.' % FEW]


def conflict_copy(name):
    """True for an iCloud conflict copy: a file or folder whose name ends in a space and a number, before the extension
    when there is one ('meta 3.json', 'map-wide 4.webp', 'first-lap 2'). The checkout lives in iCloud Drive, which
    leaves thousands of these beside the real files under rendered/. Where the build leaves such a name out (rendered/,
    a trip folder) no count here includes it; where the build publishes it all the same (a trip's photos/, a day
    file) it is counted like any other file."""
    return bool(_COPY.search(name))


# ---------------------------------------------------------------- small maths

def quantile(values, p):
    """The p-quantile (p from 0 to 1) of the values, interpolated between neighbours; None for an empty list."""
    v = sorted(values)
    if not v:
        return None
    k = (len(v) - 1) * p
    f = int(math.floor(k))
    c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)


def hhmm(hours):
    """Hours since midnight as 'HH:MM', rounded to the minute (a few seconds short of eight is '08:00', never '07:60')."""
    m = int(round(hours * 60))
    return '%02d:%02d' % (m // 60, m % 60)


def hours_spread(hours):
    """The shortest stretch of the clock that holds every given hour of the day, in hours: 23:50 and 00:10 are 20 minutes
    apart, not 23 hours 40. 0.0 for fewer than two values."""
    v = sorted(h % 24.0 for h in hours)
    if len(v) < 2:
        return 0.0
    gaps = [b - a for a, b in zip(v, v[1:])] + [v[0] + 24.0 - v[-1]]
    return 24.0 - max(gaps)


def spread_point(values, p):
    """quantile(values, p) when at least FEW of the values lie at or below it and at least FEW at or above it; None
    otherwise. With fewer beyond it the figure is one record's own value or close to it: the 5% point of ten start
    times is all but the earliest of them."""
    n = len(values)
    k = (n - 1) * p
    if n == 0 or math.floor(k) < FEW - 1 or n - 1 - math.ceil(k) < FEW - 1:
        return None
    return quantile(values, p)


def quarter(hours):
    """Hours since midnight as 'HH:MM', to the nearest quarter of an hour: a figure about many tracks should not be one
    track's start time to the minute."""
    return hhmm(round(hours * 4) / 4.0)


def merged_hours(hist, *parts):
    """[(first hour, last hour, tracks)] from a Counter of hours of the day: the hours that have tracks, in order, an
    hour with fewer than FEW of them joined to the hours after it, so that no bucket is about one track or two. parts:
    Counters of groups within those tracks (the single-day reports, the rest) that are printed bucket by bucket beside
    this one; a bucket then also has none or at least FEW of each of them, or the two lines side by side would give a
    bucket of one away. A run at the end that is still short is joined to the buckets before it, as far back as it
    takes; [] when even all the hours together will not do."""
    def enough(first, last):
        span = range(first, last + 1)
        return sum(hist[h] for h in span) >= FEW and all(n == 0 or n >= FEW for n in (sum(p[h] for h in span) for p in parts))
    hours = sorted(h for h in hist if hist[h])
    out, first = [], None
    for h in hours:
        first = h if first is None else first
        if enough(first, h):
            out.append((first, h))
            first = None
    if first is not None:
        while out and not enough(first, hours[-1]):
            first = out.pop()[0]
        if enough(first, hours[-1]):
            out.append((first, hours[-1]))
    return [(a, b, sum(hist[h] for h in range(a, b + 1))) for a, b in out]


def few(n):
    """A count of places as the default report gives it: below FEW it reads 'fewer than 3', none included, so that no
    line is about one place or two and a zero cannot be told from a one."""
    return ('fewer than %d' % FEW) if n < FEW else str(n)


def few_of(n, total):
    """few(n) for a count out of `total` places. Within FEW of all of them it reads 'all but fewer than 3', the same
    whether two, one or none are left over: what is left over is not a figure about one place either."""
    if n < FEW:
        return few(n)
    return ('all but fewer than %d' % FEW) if total - n < FEW else str(n)


def _n(n, one, many=None):
    """'1 planned route', '2 planned routes', '1,234 points'."""
    return '{:,} {}'.format(n, one if n == 1 else (many or one + 's'))


def _m(metres):
    """'150 m', '12.5 m': a radius as the author typed it."""
    return ('%g' % metres) + ' m'


# ---------------------------------------------------------------- reading

def load_tracks(trips_dir):
    """Every GPX file under trips_dir (a folder laid out like content/trips) as one row, drafts included: they have no
    page, but they are in the repository.

    Returns (rows, trips, unread). A row is {'slug', 'day' (a day id, None for track.gpx), 'label' ('slug' or
    'slug#day'), 'kind', 'shape' ('single', 'day' of a multi-day trip, 'journal' day, 'other'), 'draft', 'activity',
    'tz', 'start_time', 'combined' (a multi-day trip's own track.gpx: the build puts the combined download at its
    address), 'path'}. trips are the content.load_trip dicts. unread is [(folder name, message)] for a folder
    content.load_trip refuses: counted, never fatal. A trip folder named like an iCloud conflict copy is skipped: the
    build refuses a folder whose name cannot be a page address. A day file named like one is read: the build reads
    every days/*.md and publishes its GPX."""
    rows, trips, unread = [], [], []
    for name in sorted(os.listdir(trips_dir)):
        folder = os.path.join(trips_dir, name)
        if conflict_copy(name) or not os.path.exists(os.path.join(folder, 'index.md')):
            continue
        try:
            t = content.load_trip(folder)
        except Exception as ex:    # a ContentError names the file and the field; anything else is a file nothing can parse
            unread.append((name, '%s: %s' % (type(ex).__name__, ex)))
            continue
        trips.append(t)
        days = t['days']
        base = {'slug': t['slug'], 'kind': t['kind'], 'draft': t['draft'], 'activity': str(t['activity']), 'tz': t['timezone']}
        if t['track']:
            lone = not days and t['kind'] not in ('multi-day', 'series')
            rows.append(dict(base, day=None, label=t['slug'], shape='single' if lone else 'other', path=t['track'],
                             start_time=t['start_time'], combined=bool(t['kind'] == 'multi-day' and days)))
        for d in days:
            if d['track']:
                rows.append(dict(base, day=d['id'], label='%s#%s' % (t['slug'], d['id']), path=d['track'],
                                 shape={'multi-day': 'day', 'series': 'journal'}.get(t['kind'], 'other'),
                                 start_time=d['start_time'], combined=False))
    return rows, trips, unread


def read_track(path):
    """One GPX through gpxroute.inspect (bounded, no DTD, nothing executed): {'segs': [[(lat, lon, ele|None, ts|None),
    ...], ...], 'pts': the same points in one list, 'contains': gpxroute's contents scan, 'waypoints': n}, or
    {'error': text} for a file that is unsafe, malformed or unreadable. A file with no track but a route (a planned
    line) gives each route as one segment."""
    try:
        info = gpxroute.inspect(path)
    except (gpxroute.GpxError, OSError) as ex:
        return {'error': str(ex)}
    segs = [s for trk in info['tracks'] for s in trk['segments']]
    if not segs:
        segs = [r['points'] for r in info['routes'] if r['points']]
    return {'segs': segs, 'pts': [p for s in segs for p in s], 'contains': info['contains'], 'waypoints': info['waypoints']}


def spacing(segs):
    """(median seconds, median metres) between consecutive points, never across a gap between segments; None for a
    value the file cannot give (no times, or fewer than two points in every segment)."""
    dts, dds = [], []
    for s in segs:
        for a, b in zip(s, s[1:]):
            dds.append(geo.hav(a, b))
            if a[3] is not None and b[3] is not None:
                dts.append(b[3] - a[3])
    return quantile(dts, .5), quantile(dds, .5)


def local_start(row):
    """(when, how) for a read track: its first timestamp as a local date-time (None without timestamps), read the way
    add_trip.py read it (tracks.local_start: the trip's `timezone:`, else tracks.guess_tz from where it starts). how is
    'field', 'guessed', or 'unknown' when the zone's name is one this system has no data for: UTC is used then."""
    name = row['tz'].strip() if isinstance(row['tz'], str) and row['tz'].strip() else None
    try:
        return tracks.local_start(row['pts'], name)[0], 'field' if name else 'guessed'
    # zoneinfo raises a KeyError subclass for an unknown zone; a time at the edge of the calendar (0001-01-01, which
    # some apps write for 'unset') overflows once a zone offset is applied
    except (KeyError, ValueError, OSError, TypeError, OverflowError):
        ts = next(p[3] for p in row['pts'] if p[3] is not None)
        return datetime.fromtimestamp(ts, timezone.utc), 'unknown'


def carried(r):
    """[(label, present)] in a fixed order: what one read file holds besides its points, their times and their
    elevations, from gpxroute's contents scan (which reports anything it does not know under unknown elements)."""
    c = r['contains']
    meta = set(c.get('metadata') or ())
    return [('a file name or time', bool(meta & {'name', 'time'})),
            ('track or route names', bool(c.get('names'))),
            ('descriptions or type text', bool(c.get('descriptions'))),
            ('file information beyond a name and a time', bool(meta - {'name', 'time'})),
            ('device or app extensions', bool(c.get('extensions'))),
            ('links', bool(c.get('links'))),
            ('waypoints', bool(r['waypoints'] or c.get('waypoint_names'))),
            ('named points', bool(c.get('point_names'))),
            ('GPS quality fields', bool(c.get('point_fields'))),
            ('other attributes', bool(c.get('attributes'))),
            ('extra namespaces', bool(c.get('namespaces'))),
            ('unknown elements', bool(c.get('other'))),
            ('loose text', bool(c.get('text'))),
            ('XML comments', bool(c.get('comments'))),
            ('an unusual version text', bool(c.get('version')))]


# ---------------------------------------------------------------- starts and finishes

def endpoints(recorded):
    """[(track index, 'S' | 'F', lat, lon)]: the first and the last point of every track, in track order (the start of
    track k is entry 2k, its finish entry 2k + 1)."""
    out = []
    for i, r in enumerate(recorded):
        out.append((i, 'S', r['pts'][0][0], r['pts'][0][1]))
        out.append((i, 'F', r['pts'][-1][0], r['pts'][-1][1]))
    return out


def neighbours(points, radius):
    """For each endpoint, the indices of the endpoints within radius metres of it, itself included."""
    near = [[i] for i in range(len(points))]
    for i, a in enumerate(points):
        for j in range(i + 1, len(points)):
            # a degree of latitude is more than 111,000 m, so a pair this far apart in latitude alone is out of reach
            if abs(a[2] - points[j][2]) * 111000.0 > radius * 1.01:
                continue
            if geo.hav(a[2:], points[j][2:]) <= radius:
                near[i].append(j)
                near[j].append(i)
    return near


def clusters(points, near):
    """Single-linkage groups of endpoints: two are in one group when a chain of links, each within the radius, joins
    them (so a group can be wider than the radius; diameter() says how wide). Each group is a list of indices; groups
    come in the order of their first endpoint."""
    parent = list(range(len(points)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i, js in enumerate(near):
        for j in js:
            a, b = find(i), find(j)
            if a != b:
                parent[max(a, b)] = min(a, b)
    groups = {}
    for i in range(len(points)):
        groups.setdefault(find(i), []).append(i)
    return [groups[k] for k in sorted(groups)]


def diameter(points, group):
    """Metres between the two endpoints of the group that are furthest apart."""
    return max((geo.hav(points[a][2:], points[b][2:]) for a in group for b in group), default=0.0)


def place_facts(group, points, recorded):
    """What one group adds up to: {'tracks': track indices, 'outings': slugs (a multi-day trip or a journal is one),
    'members': track labels, 'across': metres, 'starts': tracks that start in it, 'hours' / 'dates' / 'years': of
    those starts that have a timestamp, 'activities': Counter over its tracks, 'centre': (lat, lon) mean}."""
    tids = sorted(set(points[k][0] for k in group))
    when = [recorded[points[k][0]]['when'] for k in group if points[k][1] == 'S']
    timed = [w for w in when if w is not None]
    dates = set(w.date() for w in timed)
    return {'tracks': tids, 'outings': sorted(set(recorded[i]['slug'] for i in tids)),
            'members': sorted(recorded[i]['label'] for i in tids), 'across': diameter(points, group), 'starts': len(when),
            'hours': [w.hour + w.minute / 60.0 for w in timed], 'dates': dates, 'years': set(d.year for d in dates),
            'activities': Counter(recorded[i]['activity'] for i in tids),
            'centre': (sum(points[k][2] for k in group) / len(group), sum(points[k][3] for k in group) / len(group))}


# ---------------------------------------------------------------- images

def webp_chunks(data):
    """The chunk ids of a RIFF/WebP file in order, or None when the bytes are not one. 'EXIF', 'XMP ' and 'ICCP' are the
    metadata chunks; a plain photo is a single 'VP8 ' chunk."""
    if len(data) < 12 or data[:4] != b'RIFF' or data[8:12] != b'WEBP':
        return None
    out, i = [], 12
    while i + 8 <= len(data):
        out.append(data[i:i + 4].decode('latin-1'))
        n = struct.unpack('<I', data[i + 4:i + 8])[0]
        i += 8 + n + (n & 1)
    return out


def jpeg_metadata(data):
    """The kinds of metadata segment a JPEG carries before its image data ('EXIF', 'XMP', 'ICC', 'IPTC', 'COM' for a
    comment, 'APP' for any other application segment but the JFIF header and Adobe's colour marker), or None when the
    bytes are not a JPEG."""
    if data[:2] != b'\xff\xd8':
        return None
    out, i = set(), 2
    while i + 4 <= len(data) and data[i] == 0xFF:
        m = data[i + 1]
        if m == 0xFF:                                        # a fill byte before a marker
            i += 1
            continue
        if m in (0x01, 0xD8) or 0xD0 <= m <= 0xD7:           # markers that carry no length
            i += 2
            continue
        n = struct.unpack('>H', data[i + 2:i + 4])[0]
        head = data[i + 4:i + 4 + 64]
        if m == 0xE1 and head.startswith(b'Exif'):
            out.add('EXIF')
        elif m == 0xE1 and b'ns.adobe.com/xap' in head:
            out.add('XMP')
        elif m == 0xE2 and head.startswith(b'ICC_PROFILE'):
            out.add('ICC')
        elif m == 0xED:
            out.add('IPTC')
        elif m == 0xFE:
            out.add('COM')
        elif 0xE1 <= m <= 0xEF and not (m == 0xEE and head.startswith(b'Adobe')):
            out.add('APP')
        if m == 0xDA or n < 2:                               # start of scan: the rest is the picture
            break
        i += 2 + n
    return out


def png_metadata(data):
    """The kinds of metadata chunk a PNG carries ('EXIF', 'XMP', 'ICC', 'TEXT' for any other text chunk, 'TIME'), or
    None when the bytes are not a PNG."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    out, i = set(), 8
    while i + 8 <= len(data):
        n, kind = struct.unpack('>I', data[i:i + 4])[0], data[i + 4:i + 8]
        if kind == b'eXIf':
            out.add('EXIF')
        elif kind == b'iTXt' and data[i + 8:i + 8 + 17] == b'XML:com.adobe.xmp':
            out.add('XMP')
        elif kind in (b'tEXt', b'zTXt', b'iTXt'):
            out.add('TEXT')
        elif kind == b'iCCP':
            out.add('ICC')
        elif kind == b'tIME':
            out.add('TIME')
        i += 12 + n
    return out


def scan_images(paths):
    """Counts over image files: {'files', 'kinds': Counter('WebP' | 'JPEG' | 'PNG'), 'with': Counter of metadata kinds
    ('EXIF', 'XMP', 'ICC', ...; one per file that has it), 'unreadable': files whose bytes are not what the extension
    says, 'unchecked': other file types, not opened}."""
    scan = {'files': 0, 'kinds': Counter(), 'with': Counter(), 'unreadable': 0, 'unchecked': 0}
    for p in paths:
        scan['files'] += 1
        ext = os.path.splitext(p)[1].lower()
        if ext not in IMAGE_EXT:
            scan['unchecked'] += 1
            continue
        try:
            with open(p, 'rb') as fh:
                data = fh.read()
        except OSError:
            data = b''
        if ext == '.webp':
            kind, chunks = 'WebP', webp_chunks(data)
            found = None if chunks is None else set(lab for cid, lab in (('EXIF', 'EXIF'), ('XMP ', 'XMP'), ('ICCP', 'ICC'))
                                                    if cid in chunks)
        elif ext == '.png':
            kind, found = 'PNG', png_metadata(data)
        else:
            kind, found = 'JPEG', jpeg_metadata(data)
        scan['kinds'][kind] += 1
        if found is None:
            scan['unreadable'] += 1
        else:
            scan['with'].update(found)
    return scan


def image_lines(scan, pad):
    """Two report lines for a scan_images result."""
    kinds = ', '.join('{:,} {}'.format(n, k) for k, n in sorted(scan['kinds'].items())) or 'none'
    extra = ''.join('; with %s: %d' % (k, n) for k, n in sorted(scan['with'].items()) if k not in ('EXIF', 'XMP', 'ICC'))
    return [pad + '%s: %s' % (_n(scan['files'], 'file'), kinds),
            pad + 'with EXIF: %d; with XMP: %d; with an ICC colour profile: %d%s; not readable as an image: %d; '
                  'other file types (not checked): %d'
            % (scan['with']['EXIF'], scan['with']['XMP'], scan['with']['ICC'], extra, scan['unreadable'], scan['unchecked'])]


def _files_under(folder, copies=False):
    """Every file below folder, sorted. Conflict copies and anything inside a conflict-copy folder are left out, unless
    copies=True: that is for a trip's photos/, where the build publishes every file whatever its name."""
    out = []
    for dp, dn, fn in os.walk(folder):
        dn[:] = sorted(d for d in dn if copies or not conflict_copy(d))
        out += [os.path.join(dp, f) for f in sorted(fn) if copies or not conflict_copy(f)]
    return out


def _site_files(site):
    """(read, left out, other) for a built site: the text and image files that are read, sorted; how many text and
    image files are not read because their name, or the name of a folder above them, looks like an iCloud conflict
    copy (the build writes no such name of its own); and how many files are neither GPX, text nor image, which nothing
    here opens. A file directly in trips/<slug>/photos/ is always read: the build copies every file of a trip's
    photos/ folder, whatever its name."""
    read, left, other = [], 0, 0
    for dp, dn, fn in os.walk(site):
        dn.sort()
        parts = os.path.relpath(dp, site).split(os.sep)
        above = any(conflict_copy(x) for x in parts)
        photos = not above and len(parts) == 3 and parts[0] == 'trips' and parts[2] == 'photos'
        for f in sorted(fn):
            ext = os.path.splitext(f)[1].lower()
            if ext not in TEXT_EXT and ext not in IMAGE_EXT:
                other += ext != '.gpx'
            elif photos or not (above or conflict_copy(f)):
                read.append(os.path.join(dp, f))
            else:
                left += 1
    return read, left, other


# ---------------------------------------------------------------- positions written out in a text file

def end_index(rows):
    """(index, points): the first and the last point of every track that was read, to look for in text files. index is
    {thousandths of a degree: [(point number, 0 for the latitude or 1 for the longitude, the size of the coordinate)]};
    sizes are without their sign, because a page may write 'W' or a minus that a hyphen cannot be told from."""
    index, n = {}, 0
    for r in rows:
        if not r.get('pts'):
            continue
        for p in (r['pts'][0], r['pts'][-1]):
            for axis in (0, 1):
                size = abs(p[axis])
                index.setdefault(int(size * 1000), []).append((n, axis, size))
            n += 1
    return index, n


def written_positions(text, index):
    """What one text file holds that reads as a position: (own, pair).

    own is True when the file holds the latitude and the longitude of one indexed point (end_index): each as a number
    with three or more decimals that is the coordinate rounded or cut short to that many decimals, in either order,
    anywhere in the file, whatever is written between or around them (a comma, a key, an attribute name, a space). One
    number standing for both needs to be there twice.

    pair is 'loose' when two numbers of four or more decimals stand no more than PAIR_GAP characters apart and one
    could be a latitude (up to 90) and the other a longitude (up to 180); 'sized' when every such pair is between the
    values of CSS custom properties (--name: number), which is how the site writes the proportions of a photo row;
    None without such a pair. This one is a look-alike, not a known position: any two long decimals side by side
    count."""
    if not _LONG.search(text):
        return False, None
    counts, fine = Counter(), []
    for m in _NUM.finditer(text):
        s = m.group(0).lstrip('-')
        counts[s] += 1
        if len(s) - s.index('.') > 4:
            fine.append((m.start(), m.end(), float(s)))
    seen = {}
    for s in counts:
        size = float(s)
        unit = 10.0 ** (s.index('.') + 1 - len(s))                  # one unit of the last decimal written
        for k in range(int(size * 1000) - 1, int(size * 1000) + 2):
            for n, axis, x in index.get(k, ()):
                # cut short, the number is at most one unit below the coordinate; rounded, at most half a unit either
                # side of it; written with more decimals than the track has, it is the coordinate itself
                if -unit / 2 - 1e-9 <= x - size < unit or abs(x - size) < 1e-7:
                    seen.setdefault(n, (set(), set()))[axis].add(s)
    own = any(la and lo and (len(la | lo) > 1 or counts[min(la)] > 1) for la, lo in seen.values())
    pair = None
    for i, (a0, a1, a) in enumerate(fine):
        for j in range(i + 1, len(fine)):
            b0, _b1, b = fine[j]
            if b0 - a1 > PAIR_GAP:
                break
            if min(a, b) <= 90 and max(a, b) <= 180:
                if not (_CSS_VALUE.search(text, max(0, a0 - 80), a0) and _CSS_VALUE.search(text, max(0, b0 - 80), b0)):
                    return own, 'loose'
                pair = 'sized'
    return own, pair


# ---------------------------------------------------------------- the report, section by section

def _inventory(rows, trips, unread, bad, empty, rec, plan, listing):
    """Section 1: how many GPX files there are and of what kind, so every later count has its denominator. Files that
    could not be used are counted here and named only in the author's listing."""
    shape = Counter(r['shape'] for r in rec)
    parents = {s: len(set(r['slug'] for r in rec if r['shape'] == s)) for s in ('day', 'journal')}
    parts = [_n(shape['single'], 'single-day report'),
             '%s of %s' % (_n(shape['day'], 'day'), _n(parents['day'], 'multi-day trip')),
             '%s of %s' % (_n(shape['journal'], 'day'), _n(parents['journal'], 'journal'))]
    if shape['other']:
        parts.append('%d in another arrangement' % shape['other'])
    with_gpx = set(r['slug'] for r in rows)
    L = ['1. WHAT IS IN content/trips',
         '   GPX files: %d = %s + %s; unreadable: %d; with no track points: %d'
         % (len(rows), _n(len(rec), 'recorded track'), _n(len(plan), 'planned route'), len(bad), len(empty)),
         '   the recorded tracks: %s; %s in all' % ('; '.join(parts), _n(len(set(r['slug'] for r in rec)), 'report')),
         '   recorded tracks in a draft (no page and no download; the files stay in the repository, and the maps under '
         'rendered/site/ keep the line and the title of a trip they already draw until tools/render.py is run again): %d'
         % sum(1 for r in rec if r['draft']),
         '   trips with no GPX at all: %d; trip folders that could not be read: %d'
         % (sum(1 for t in trips if t['slug'] not in with_gpx), len(unread))]
    if listing:
        L += ['      unreadable GPX: %s: %s' % (gpxroute.printable_name(r['label'], 90), gpxroute.printable(r['error'], 160))
              for r in bad]
        L += ['      no track points: %s' % gpxroute.printable_name(r['label'], 90) for r in empty]
        L += ['      could not be read: %s: %s' % (gpxroute.printable_name(name, 90), gpxroute.printable(msg, 200))
              for name, msg in unread]
    return L


def _gap_line(dt, dd, listing):
    """How far apart a group's points are: the median of the files' medians, in seconds and in metres, with the middle
    80% of the files in brackets. The default report leaves out a figure that fewer than FEW files lie beyond
    (spread_point), so for a handful of files there is no range, and for fewer still no line of figures at all."""
    pick = quantile if listing else spread_point

    def figure(values, unit):
        mid, low, high = pick(values, .5), pick(values, .1), pick(values, .9)
        if mid is None:
            return None
        return '%.0f %s' % (mid, unit) + ('' if low is None or high is None else ' (%.0f to %.0f %s)' % (low, high, unit))
    metres = figure(dd, 'm')
    if metres is None:
        return "     typical gap between points: not given for so few files (it would be one file's own, or close to it)"
    secs = (figure(dt, 's') or 'too few files with times') if dt else 'no times'
    how = 'in brackets the middle 80% of files' if '(' in metres else 'too few files for a range'
    return "     typical gap between points (each file's median; %s): %s and %s" % (how, secs, metres)


def _carries(rec, plan, listing):
    """Section 2: what the files hold besides coordinates (times, elevation, creator text, anything else gpxroute's
    contents scan finds) and how closely the points are spaced. Free text from a file is printed only in the listing,
    and escaped there. A group of fewer than FEW files gets its counts but no point total and no spacing in the
    default report: those would be one file's own figures."""
    L = ['2. WHAT EACH GPX CARRIES BESIDES THE LINE']
    for lab, sub in (('recorded tracks', rec), ('planned routes', plan)):
        if not sub:
            continue
        n = len(sub)
        small = n < FEW and not listing
        L.append('   %s (%s; too few for a point total or a spacing that is not one file\'s own):' % (lab, _n(n, 'file')) if small
                 else '   %s (%s, %s):' % (lab, _n(n, 'file'), _n(sum(len(r['pts']) for r in sub), 'point')))
        for what, k in (('a time', 3), ('an elevation', 2)):
            full = sum(1 for r in sub if all(p[k] is not None for p in r['pts']))
            some = sum(1 for r in sub if any(p[k] is not None for p in r['pts'])) - full
            L.append('     %s on every point: %d; on some: %d; on none: %d' % (what, full, some, n - full - some))
        creators = Counter((r['contains'].get('creator') or '') for r in sub)
        other = sorted((k, v) for k, v in creators.items() if k not in ('', SITE_CREATOR))
        L.append('     creator text: this site\'s own in %d; another in %d; none in %d'
                 % (creators[SITE_CREATOR], sum(v for _k, v in other), creators['']))
        if listing:
            L += ['        another creator text: %s in %d' % (gpxroute.printable(k, 80), v) for k, v in other]
        found = Counter()
        for r in sub:
            found.update(label for label, on in carried(r) if on)
        labels = [label for label, _on in carried(sub[0])]
        present = '; '.join('%s in %d' % (k, found[k]) for k in labels if found[k])
        L.append('     also in the files: %s' % (present or 'nothing'))
        L.append('     in no file: %s' % (', '.join(k for k in labels if not found[k]) or 'nothing'))
        sp = [spacing(r['segs']) for r in sub]
        dt = [s[0] for s in sp if s[0] is not None]
        dd = [s[1] for s in sp if s[1] is not None]
        if dd and not small:
            L.append(_gap_line(dt, dd, listing))
    return L


def _ends(rec, radius, min_cluster, listing):
    """Section 3: how often starts and finishes repeat. Two measures, because they answer different questions: how many
    other tracks end within the radius of each end (honest about distance), and the places that chains of such ends
    make (one place per trailhead or doorstep, however many tracks). Both are given by track and by outing, since the
    days of one trip meet end to start. The listing adds each shared place's trips and rounded position.

    The default report says nothing that is about fewer than FEW places: a count of places below that reads 'fewer
    than 3' (few, few_of), a count of tracks is given only when the ends it counts lie at FEW places or more, and the
    places that outings share are described only when there are that many of them."""
    sizes = sorted(set([min_cluster] + [s for s in SIZES if s > min_cluster]))
    L = ['3. STARTS AND FINISHES (the same place: within %s; a shared place: %d or more separate outings)'
         % (_m(radius), min_cluster),
         '   tracks that finish within %s of their own start: %d of %d'
         % (_m(radius), sum(1 for r in rec if geo.hav(r['pts'][0], r['pts'][-1]) <= radius), len(rec))]
    pts = endpoints(rec)
    near = neighbours(pts, radius)
    groups = clusters(pts, near)
    place_of = dict((k, g) for g, group in enumerate(groups) for k in group)

    def tracks_at(ends):
        """How many tracks the given ends belong to, or why not: ends at fewer than FEW places are one place's size."""
        if not listing and len(set(place_of[k] for k in ends)) < FEW:
            return 'at fewer than %d places' % FEW
        return '%d' % len(set(pts[k][0] for k in ends))
    for by, unit, head in (
            (lambda i: i, 'tracks', '   tracks whose start or finish has the start or finish of other tracks within %s '
                                    '(the track itself counted):' % _m(radius)),
            (lambda i: rec[i]['slug'], 'outings', '   the same, a multi-day trip or a journal counted as one outing (last '
                                                  'night\'s camp is the next morning\'s start):')):
        share = [len(set(by(pts[j][0]) for j in js)) for js in near]
        L.append(head)
        for th in sizes:
            busy = [k for k in range(len(pts)) if share[k] >= th]
            either = tracks_at(busy)
            if either.startswith('at fewer'):
                L.append('     %d or more %s there: %s, so no count is given' % (th, unit, either))
            else:
                L.append('     %d or more %s there: start %s; finish %s; either %s'
                         % (th, unit, tracks_at([k for k in busy if k % 2 == 0]), tracks_at([k for k in busy if k % 2]), either))
    places = [place_facts(g, pts, rec) for g in groups]
    places.sort(key=lambda p: (-len(p['outings']), -len(p['tracks']), p['tracks'][0]))
    show = str if listing else few
    L.append('   places (starts and finishes chained together, each within %s of the next): %s' % (_m(radius), show(len(places))))
    used = ['%d or more outings: %s' % (th, show(sum(1 for p in places if len(p['outings']) >= th)))
            for th in sorted(set([2] + sizes))]
    L.append('     shared by ' + '; by '.join(used))
    shared = [p for p in places if len(p['outings']) >= min_cluster]
    if not listing and len(shared) < FEW:
        L.append('   places shared by %d or more outings: fewer than %d, so nothing more is said about them here (--list does, '
                 'for the author)' % (min_cluster, FEW))
        return L
    part = (lambda n, total: str(n)) if listing else few_of
    L.append('   the %s shared by %d or more outings:' % (_n(len(shared), 'place'), min_cluster))
    timed = [p for p in shared if len(p['hours']) >= 2]
    L.append('     tracks that start or finish at one of them: %d of %d'
             % (len(set(i for p in shared for i in p['tracks'])), len(rec)))
    L.append('     every start there on a different date: %s; starts in more than one calendar year: %s; more than one '
             'activity: %s' % (part(sum(1 for p in timed if len(p['dates']) == len(p['hours'])), len(timed)),
                               part(sum(1 for p in shared if len(p['years']) > 1), len(shared)),
                               part(sum(1 for p in shared if len(p['activities']) > 1), len(shared))))
    spread = [hours_spread(p['hours']) for p in timed]
    L.append('     start times all within %d minutes: %s; spread over %d hours or more: %s; wider than %s from end to end '
             '(a chain can be): %s'
             % (TIGHT_H * 60, part(sum(1 for x in spread if x <= TIGHT_H), len(timed)), SPREAD_H,
                part(sum(1 for x in spread if x >= SPREAD_H), len(timed)), _m(radius),
                part(sum(1 for p in shared if p['across'] > radius), len(shared))))
    if listing:
        L.append('   AUTHOR ONLY: each shared place, most outings first (position rounded to 3 decimals, about 100 m)')
        for n, p in enumerate(shared):
            h = p['hours']
            if h:
                starts = ('%s on %s in %s%s; start times %s to %s (middle half %s to %s)'
                          % (_n(p['starts'], 'start'), _n(len(p['dates']), 'date'), _n(len(p['years']), 'calendar year'),
                             '' if len(h) == p['starts'] else ' (%d without a time)' % (p['starts'] - len(h)),
                             hhmm(min(h)), hhmm(max(h)), hhmm(quantile(h, .25)), hhmm(quantile(h, .75))))
            elif p['starts']:
                starts = '%s, none with a time' % _n(p['starts'], 'start')
            else:
                starts = 'no track starts here, some finish'
            L.append('   place %d: %s, %s, %.0f m across; %s; %s'
                     % (n + 1, _n(len(p['outings']), 'outing'), _n(len(p['tracks']), 'track'), p['across'], starts,
                        ', '.join('%s %d' % kv for kv in sorted(p['activities'].items()))))
            L.append('      near %.3f, %.3f: %s' % (p['centre'][0], p['centre'][1],
                                                    ', '.join(gpxroute.printable_name(m, 90) for m in p['members'])))
    return L


def _clock_lines(sub, groups):
    """The by-hour and by-weekday lines of the default report for the tracks `sub`. groups: every set of tracks whose
    counts a reader can work out from the lines printed. That is all the tracks; and, when the single-day reports are
    set apart under them, those reports and the tracks that are not single-day reports as well, since one line taken
    from the other gives the rest. A bucket is given only when no group has one or two tracks in it, so both lines
    use the same buckets and neither a line nor the difference of the two is about one track."""
    def clock(rows):
        return Counter(r['when'].hour for r in rows), Counter(r['when'].weekday() for r in rows)
    mine, wd = clock(sub)
    hours, days = zip(*[clock(g) for g in groups])
    buckets = [(a, b, sum(mine[h] for h in range(a, b + 1))) for a, b, _n in merged_hours(hours[0], *hours[1:])]
    L = ['     by hour (hour: tracks; hours are joined until none holds one or two tracks%s): %s'
         % (', here, on the other line or between the two' if len(groups) > 1 else '',
            ', '.join(('%02d: %d' % (a, n)) if a == b else ('%02d to %02d: %d' % (a, b, n)) for a, b, n in buckets if n)
            or 'not given')]

    def whole(counts):
        return all(c == 0 or c >= FEW for c in counts)
    week, end = sum(wd[i] for i in range(5)), wd[5] + wd[6]
    if all(whole([d[i] for i in range(7)]) for d in days):
        L.append('     by weekday, Monday to Sunday: %s; on a Saturday or Sunday: %d%%'
                 % (' '.join(str(wd[i]) for i in range(7)), round(100.0 * end / len(sub))))
    elif all(whole([sum(d[i] for i in range(5)), d[5] + d[6]]) for d in days):
        L.append('     by weekday (a day with fewer than %d tracks is not shown on its own): Monday to Friday %d; Saturday or '
                 'Sunday %d, which is %d%%' % (FEW, week, end, round(100.0 * end / len(sub))))
    else:
        L.append('     by weekday: not given (fewer than %d tracks on one side of the weekend)' % FEW)
    return L


def _times(rec, listing):
    """Section 4: when tracks start, by the clock and by the weekday, in local time. Also whether the start_time a report
    page shows is the track's own first timestamp: if it is, hiding one would not hide the other (and after a track is
    cut short by hand, the count says whether start_time was changed with it).

    The default report gives the spread to the quarter hour and only at a point that FEW tracks or more lie on either
    side of, joins hours until none holds one or two tracks (_clock_lines), and names no earliest and no latest start:
    each of those would be one track's own time. The single-day reports are set apart from all tracks only when FEW
    or more tracks, or none, are not single-day reports. The listing has all of it to the minute."""
    L = ['4. START TIMES (each track\'s first timestamp, read in the trip\'s timezone: field, or in a zone guessed from '
         'where it starts)']
    timed = [r for r in rec if r['when'] is not None]
    single = [r for r in timed if r['shape'] == 'single']
    others = [r for r in timed if r['shape'] != 'single']
    apart = len(single) >= FEW and (not others or len(others) >= FEW)
    for lab, sub in (('all tracks with times', timed), ('single-day reports only', single)):
        if not sub:
            continue
        hrs = [r['when'].hour + r['when'].minute / 60.0 for r in sub]
        if listing:
            wd = Counter(r['when'].weekday() for r in sub)
            hist = Counter(int(h) for h in hrs)
            L.append('   %s (%d): earliest %s; 5%% before %s; a quarter before %s; half before %s; three quarters before %s; '
                     '95%% before %s; latest %s'
                     % ((lab, len(sub)) + tuple(hhmm(quantile(hrs, q)) for q in (0, .05, .25, .5, .75, .95, 1))))
            L.append('     by hour (hour: tracks): ' + ', '.join('%02d: %d' % (h, hist[h]) for h in range(24) if hist[h]))
            L.append('     by weekday, Monday to Sunday: %s; on a Saturday or Sunday: %d%%'
                     % (' '.join(str(wd[i]) for i in range(7)), round(100.0 * (wd[5] + wd[6]) / len(sub))))
        elif sub is single and 0 < len(others) < FEW:
            # the two groups side by side would give the one or two tracks between them away
            L.append('   %s: all but fewer than %d of the tracks above, so not shown apart' % (lab, FEW))
        elif len(sub) < FEW:
            L.append('   %s (%d): too few to say when they start without it being one track\'s own time' % (lab, len(sub)))
        else:
            marks = [(name, spread_point(hrs, q))
                     for q, name in ((.05, '5% before'), (.25, 'a quarter before'), (.5, 'half before'),
                                     (.75, 'three quarters before'), (.95, '95% before'))]
            L.append('   %s (%d), to the quarter hour: %s'
                     % (lab, len(sub), '; '.join('%s %s' % (name, quarter(v)) for name, v in marks if v is not None)
                        or 'too few for a spread (fewer than %d tracks would lie beyond any point of it)' % FEW))
            L += _clock_lines(sub, [timed, single, others] if (apart and others) else [timed])
    how = Counter(r['zone'] for r in timed)
    L.append('   tracks without timestamps: %d; read in a guessed zone (no timezone: field): %d; with a timezone: this '
             'system does not know (read as UTC): %d' % (len(rec) - len(timed), how['guessed'], how['unknown']))
    stated = [r for r in rec if r['start_time'] is not None and str(r['start_time']).strip()]
    same = 0
    for r in stated:
        m = _HM.match(str(r['start_time']))
        w = r['when']
        same += bool(m and w is not None and (int(m.group(1)), int(m.group(2))) == (w.hour, w.minute))
    by = Counter(r['shape'] for r in rec)
    got = Counter(r['shape'] for r in stated)
    L.append('   start_time in the front matter: %d of %s, %d of %s, %d of %s; equal to the track\'s first timestamp, to the '
             'minute: %d of %d'
             % (got['single'], _n(by['single'], 'single-day report'), got['day'], _n(by['day'], 'multi-day day'),
                got['journal'], _n(by['journal'], 'journal day'), same, len(stated)))
    return L


def _photos(trips_dir):
    """Section 5: metadata in the photo files of every trip (all sizes, drafts included). Every file of a photos/ folder
    is read, whatever its name: tools/build.py copies each one to the site, a name that looks like an iCloud conflict
    copy included. (A trip folder named like one is skipped, as everywhere here: the build refuses it.)"""
    paths = []
    for name in sorted(os.listdir(trips_dir)):
        folder = os.path.join(trips_dir, name, 'photos')
        if not conflict_copy(name) and os.path.isdir(folder):
            paths += [p for p in _files_under(folder, copies=True) if not os.path.basename(p).startswith('.')]
    return (['5. PHOTOS in content/trips/*/photos (every file there, whatever its name: the build publishes them all)']
            + image_lines(scan_images(paths), '   '))


def _front_matter(trips_dir):
    """[(is a day file, front-matter dict)] for every index.md and days/*.md that parses. A trip folder named like an
    iCloud conflict copy is left out (the build refuses it); a day file named like one is read, as the build reads it."""
    out = []
    for name in sorted(os.listdir(trips_dir)):
        folder = os.path.join(trips_dir, name)
        if conflict_copy(name) or not os.path.exists(os.path.join(folder, 'index.md')):
            continue
        days = os.path.join(folder, 'days')
        files = [(False, os.path.join(folder, 'index.md'))]
        if os.path.isdir(days):
            files += [(True, os.path.join(days, f)) for f in sorted(os.listdir(days)) if f.endswith('.md')]
        for is_day, p in files:
            try:
                with open(p, encoding='utf-8') as fh:
                    out.append((is_day, frontmatter.split(fh.read())[0]))
            except (OSError, ValueError):
                continue
    return out


def _repository(fm, rows, rendered_dir):
    """Section 6: what a reader of the public repository gets whether or not a page shows it: front-matter fields and
    the coordinates the map renderer writes into rendered/trips/<slug>/meta.json."""
    def has(key):
        return sum(1 for _d, m in fm if m.get(key) is not None and str(m.get(key)).strip())
    L = ['6. IN THE REPOSITORY, WHATEVER THE SITE SHOWS (a public repository publishes every file in it)',
         '   front matter: %s (%d index.md, %s); strava_id in %d; timezone in %d; start_time in %d; party in %d'
         % (_n(len(fm), 'file'), sum(1 for d, _m in fm if not d), _n(sum(1 for d, _m in fm if d), 'day file'),
            has('strava_id'), has('timezone'), has('start_time'), has('party'))]
    metas = with_ends = 0
    folder = os.path.join(rendered_dir, 'trips') if rendered_dir else ''
    for name in (sorted(os.listdir(folder)) if os.path.isdir(folder) else []):
        p = os.path.join(folder, name, 'meta.json')
        if conflict_copy(name) or not os.path.isfile(p):
            continue
        metas += 1
        try:
            with open(p, encoding='utf-8') as fh:
                m = json.load(fh)
        except (OSError, ValueError):
            continue
        with_ends += bool(isinstance(m, dict) and m.get('start') and m.get('end'))
    L.append('   rendered/trips/*/meta.json: %s; with the start and the end written out as coordinates: %d'
             % (_n(metas, 'file'), with_ends))
    L.append('   the %s themselves, and every earlier version of every file (git history; this tool does not read it)'
             % _n(len(rows), 'GPX file'))
    return L


def _near(rec, point, radius, listing, no):
    """The --near section: the tracks around one point the author typed. This is the check for a private place visited
    once, which no grouping can find. The point itself is never put into a line."""
    hit_end = [r for r in rec if geo.hav(r['pts'][0], point) <= radius or geo.hav(r['pts'][-1], point) <= radius]
    hit_any = [r for r in rec if any(abs(p[0] - point[0]) * 111000.0 <= radius * 1.01 and geo.hav(p, point) <= radius
                                     for p in r['pts'])]
    L = ['%d. NEAR THE POINT YOU TYPED (within %s; the point is not printed or stored)' % (no, _m(radius)),
         '   tracks that start or finish there: %d; tracks that pass within %s of it at any point: %d (of %d)'
         % (len(hit_end), _m(radius), len(hit_any), len(rec))]
    if listing and hit_any:
        L.append('      AUTHOR ONLY: ' + ', '.join(gpxroute.printable_name(r['label'], 90) for r in hit_any))
    return L


def _sha256(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _site(site, rows, fm, no):
    """The --site section: whether a built site's GPX copies are their sources byte for byte (the names are the ones
    build.copy_trip_assets writes), what its text files hold that reads as a position (written_positions: the tracks'
    own ends, and any two long decimals side by side), whether one holds a strava_id or a zone name from the front
    matter, and what metadata its images carry. Counts only: no number found in a file is ever printed."""
    same = diff = linked = missing = drafts = 0
    for r in rows:
        if r['combined']:
            continue
        pub = (os.path.join(site, 'trips', r['slug'], 'gpx', '%s-day-%s.gpx' % (r['slug'], r['day'])) if r['day']
               else os.path.join(site, 'trips', r['slug'], r['slug'] + '.gpx'))
        if not os.path.exists(pub):
            missing += 1
            drafts += bool(r['draft'])
        elif os.path.islink(pub):
            linked += 1
        elif _sha256(pub) == _sha256(r['path']):
            same += 1
        else:
            diff += 1
    L = ['%d. THE BUILT SITE in the folder given' % no,
         '   GPX copies: equal to the source byte for byte: %d; different: %d; a symlink to the source (a --link build: '
         'nothing to compare): %d; not in the folder: %d (in a draft: %d)' % (same, diff, linked, missing, drafts)]
    ids = set(str(m['strava_id']).strip() for _d, m in fm if m.get('strava_id') is not None) - {''}
    shortest = min([len(i) for i in ids if i.isdigit()] or [0])
    id_run = re.compile(r'\d{%d,}' % shortest) if shortest else None     # an id is a whole run of digits, never part of one
    zones = set(m['timezone'].strip() for _d, m in fm if isinstance(m.get('timezone'), str) and '/' in m['timezone'])
    index, n_ends = end_index(rows)
    files, left, other = _site_files(site)
    images = []
    n_text = own = loose = sized = with_id = with_zone = 0
    for p in files:
        if os.path.splitext(p)[1].lower() in IMAGE_EXT:
            images.append(p)
            continue
        n_text += 1
        with open(p, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
        mine, pair = written_positions(text, index)
        own += mine
        loose += pair == 'loose'
        sized += pair == 'sized'
        with_id += bool(id_run and (ids & set(id_run.findall(text))))
        with_zone += any(z in text for z in zones)
    L += ['   text files ({:,}: {}):'.format(n_text, ', '.join(e[1:] for e in TEXT_EXT)),
          '     holding the latitude and the longitude of the first or the last point of one GPX file of content/trips, each '
          'written with 3 or more decimals (rounded or cut short, in either order, whatever stands between them; {:,} points '
          'looked for): {}'.format(n_ends, own),
          '     holding two numbers of 4 or more decimals, no more than {} characters apart, that could be a latitude and a '
          'longitude (look-alikes, not known positions): {}; the same, but only as values of CSS custom properties (--name: '
          'number, which is how the site writes the proportions of a photo row): {}'.format(PAIR_GAP, loose, sized),
          '     with a strava_id from the front matter: {}; with a timezone name from the front matter: {}'
          .format(with_id, with_zone),
          '     not looked for: a position in another notation (degrees and minutes, whole numbers, an encoded line) or with '
          'fewer decimals, and what an image shows',
          '   not read: text or image files whose name, or a folder\'s above them, looks like an iCloud conflict copy (a trip\'s '
          'photos are read whatever their name): {:,}; files that are neither GPX, text nor image: {:,}'.format(left, other)]
    return L + ['   images:'] + image_lines(scan_images(images), '     ')


def audit(trips_dir, rendered_dir=None, radius=150.0, min_cluster=3, listing=False, site=None, near=None):
    """The report as a list of lines. trips_dir is laid out like content/trips, rendered_dir like rendered/. With
    listing=False the lines are counts only: no trip, coordinate, name, id or path, and no figure about where or when
    that fewer than FEW tracks or places stand behind. near: a (lat, lon) to count the tracks around; site: a built
    site folder to check as well."""
    rows, trips, unread = load_tracks(trips_dir)
    for r in rows:
        r.update(read_track(r['path']))
    bad = [r for r in rows if 'error' in r]
    empty = [r for r in rows if 'error' not in r and not r['pts']]
    ok = [r for r in rows if r.get('pts')]
    rec = [r for r in ok if r['kind'] != 'planned']
    plan = [r for r in ok if r['kind'] == 'planned']
    for r in rec:
        r['when'], r['zone'] = local_start(r)
    fm = _front_matter(trips_dir)
    L = [] if listing else list(HEAD)
    L += _inventory(rows, trips, unread, bad, empty, rec, plan, listing)
    L += _carries(rec, plan, listing)
    L += _ends(rec, radius, min_cluster, listing)
    L += _times(rec, listing)
    L += _photos(trips_dir)
    L += _repository(fm, rows, rendered_dir)
    no = 7
    if near is not None:
        L += _near(rec, near, radius, listing, no)
        no += 1
    if site:
        L += _site(site, rows, fm, no)
    L.append('WHAT THIS CANNOT TELL YOU: what any place is (nothing is looked up); a private place visited once (one track '
             'is not a group: --near counts the tracks around a point you type); what a photograph shows.')
    return L


# ---------------------------------------------------------------- cli

def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--radius', type=float, default=150.0, metavar='M',
                    help='metres within which two starts or finishes are the same place (default 150)')
    ap.add_argument('--min-cluster', type=int, default=3, metavar='N',
                    help='how many separate outings make a shared place (default 3, at least 2)')
    ap.add_argument('--list', action='store_true', dest='listing',
                    help='also name the trips and a rounded position for each shared place (a terminal only)')
    ap.add_argument('--list-anyway', action='store_true',
                    help='with --list: print it although the output is not a terminal (where it goes is yours to look after)')
    ap.add_argument('--near', action='store_true',
                    help='ask for a private "latitude, longitude" (not echoed, not stored) and count the tracks that pass it')
    ap.add_argument('--site', metavar='DIR', help='a built site folder to check as well (for example _site)')
    ap.add_argument('--content', metavar='DIR',
                    help='a folder laid out like content/, with trips/ inside (default: this checkout\'s)')
    ap.add_argument('--rendered', metavar='DIR', help='a folder laid out like rendered/ (default: this checkout\'s)')
    return ap


def main(argv=None, out=None, isatty=None):
    """Print the report to out (default: stdout). Returns 0; a usage error exits with status 2 (argparse) before
    anything is read. isatty: what to believe about out, for the tests."""
    out = out or sys.stdout
    ap = build_parser()
    a = ap.parse_args(argv)
    if not (math.isfinite(a.radius) and a.radius > 0):
        ap.error('--radius must be a number of metres above 0')
    if a.min_cluster < 2:
        ap.error('--min-cluster must be 2 or more (one track is not a shared place)')
    if a.listing and not a.list_anyway and not (out.isatty() if isatty is None else isatty):
        ap.error('--list names trips and coordinates, so it prints to a terminal only, and this output is going somewhere '
                 'else. Add --list-anyway if you mean it.')
    trips_dir = os.path.join(a.content, 'trips') if a.content else content.TRIPS_DIR
    if not os.path.isdir(trips_dir):
        ap.error('no trips/ folder to read (--content takes a folder laid out like content/)')
    if a.site and not os.path.isdir(a.site):
        ap.error('--site: the folder given does not exist')
    near = None
    if a.near:
        m = re.match(r'^\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*$',
                     getpass.getpass('latitude, longitude (not shown as you type): '))
        if not m or not -90 <= float(m.group(1)) <= 90 or not -180 <= float(m.group(2)) <= 180:
            ap.error('--near needs "latitude, longitude" in decimal degrees (what was typed is not repeated here)')
        near = (float(m.group(1)), float(m.group(2)))
    lines = audit(trips_dir, a.rendered or content.RENDERED, a.radius, a.min_cluster, a.listing, a.site, near)
    if a.listing:
        lines = [BANNER] + lines + [BANNER]
    try:
        out.write('\n'.join(lines) + '\n')
    except BrokenPipeError:      # piped into something that stopped reading (head, a pager that quit)
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
