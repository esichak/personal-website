"""Phase 4: tools/privacy_audit.py, the author's read-only report on what the published tracks and photos add up to.

Every fixture is synthetic. Tracks are short lines of points beside latitude 10, longitude 10 (nowhere a real trip of
this site goes), written into helpers.make_trip folders in a temp dir under invented slugs, with an invented companion
and an invented id; time zones are ones no real trip uses. The tool runs in-process through main(argv, out, isatty)
with --content and --rendered pointed at the temp dir, so the real content/, rendered/ and _site/ are never read, and
nothing touches the network (the read-only test replaces socket.socket and every writing call with a failure).

What is asserted: the arithmetic (quantiles, clock spread, neighbourhoods, single-linkage groups), the image metadata
readers, every count of the default report on a known tree, that the default report names nothing (no slug, no
coordinate, no name, no id, no path) and gives no figure about one track or one place (no earliest or latest start, no
hour with one or two tracks, no count of places below three, no point total of a single file), that --list has those
figures exactly and is bannered, rounded and terminal-only, that --near never repeats what was typed, that --site finds
a track's own end however a text file writes it, that the files the build publishes are counted whatever their name and
the iCloud conflict copies it leaves out are not, and that neither the build nor CI runs the tool.
"""
import contextlib
import hashlib
import io
import math
import os
import re
import socket
import struct
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))

import gpx_fixtures as gx  # noqa: E402
import helpers  # noqa: E402
import privacy_audit as pa  # noqa: E402

LAT0, LON0 = 10.0, 10.0                              # an invented spot: no real track of the site is anywhere near it
M_LAT = 360.0 / (2 * math.pi * 6371000.0)            # degrees of latitude per metre on the sphere geo.hav measures
ZONE = 'Africa/Lagos'                                # UTC+1 all year, and no trip of the site uses it
NAME, STRAVA_ID = 'Sam Example', 123456789           # the invented companion and id the default report must never print
COORDINATE = re.compile(r'-?\d{1,3}\.\d{3,}')        # a number with three or more decimals: what a coordinate looks like


def utc(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def points(lat, lon, start, n=6, step_m=20.0, loop=False, times=True, eles=True):
    """n points stepping north step_m metres from (lat, lon), one a minute from `start` (a UTC datetime), in the shape
    gpx_fixtures.trk takes. loop=True walks out and comes back, so the last point is the first."""
    out = []
    for i in range(n):
        j = (n - 1 - i) if (loop and i > n // 2) else i
        when = (start + timedelta(minutes=i)).strftime('%Y-%m-%dT%H:%M:%SZ') if times else None
        out.append((round(lat + j * step_m * M_LAT, 6), lon, (2000 + i) if eles else None, when))
    return out


def track(lat, lon, start, **kw):
    """A GPX file's text: one track of points(...)."""
    return gx.gpx(gx.trk([points(lat, lon, start, **kw)], 'Synthetic line'))


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb' if isinstance(data, bytes) else 'w', **({} if isinstance(data, bytes) else {'encoding': 'utf-8'})) as fh:
        fh.write(data)


def webp(*chunks):
    """RIFF/WebP bytes holding the given (chunk id, data) pairs; an odd-length chunk is padded as the format says."""
    body = b'WEBP' + b''.join(cid + struct.pack('<I', len(d)) + d + (b'\0' if len(d) & 1 else b'') for cid, d in chunks)
    return b'RIFF' + struct.pack('<I', len(body)) + body


PLAIN = webp((b'VP8 ', b'ab'))                                             # what the site's photos are
TAGGED = webp((b'VP8X', b'\0' * 10), (b'VP8 ', b'ab'), (b'EXIF', b'Exif\0\0II'))


class Tree(unittest.TestCase):
    """A temp dir laid out like the checkout: content/trips/ and rendered/."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.content = os.path.join(self.tmp, 'content')
        self.trips = os.path.join(self.content, 'trips')
        self.rendered = os.path.join(self.tmp, 'rendered')
        os.makedirs(self.trips)

    def trip(self, slug, gpx_text, **meta):
        """A single-day trip folder whose track.gpx holds gpx_text."""
        meta.setdefault('timezone', ZONE)
        folder = helpers.make_trip(self.trips, slug, track=True, **meta)
        write(os.path.join(folder, 'track.gpx'), gpx_text)
        return folder

    def days(self, slug, kind, starts, **meta):
        """A multi-day trip or a journal: one day file and one GPX per (lat, start) of `starts`, each 500 m long."""
        meta.setdefault('timezone', ZONE)
        folder = helpers.make_trip(self.trips, slug, kind=kind, days=[{'date': s.strftime('%Y-%m-%d')} for _lat, s in starts], **meta)
        for i, (lat, s) in enumerate(starts):
            write(os.path.join(folder, 'days', '%02d.gpx' % (i + 1)), track(lat, LON0, s, step_m=100.0))
        return folder

    def run_audit(self, *args, isatty=False):
        out = io.StringIO()
        rc = pa.main(['--content', self.content, '--rendered', self.rendered] + list(args), out=out, isatty=isatty)
        self.assertEqual(rc, 0)
        return out.getvalue()

    def exact(self, *args):
        """The report with every figure exact, which is the author's listing (the default report rounds, joins or
        withholds whatever would be about one track or one place)."""
        return self.run_audit('--list', *args, isatty=True)

    def usage_error(self, *args, isatty=False):
        """The message of a refused command line: exit status 2, nothing on the output stream."""
        out, err = io.StringIO(), io.StringIO()
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stderr(err):
            pa.main(['--content', self.content, '--rendered', self.rendered] + list(args), out=out, isatty=isatty)
        self.assertEqual(cm.exception.code, 2)
        self.assertEqual(out.getvalue(), '')
        return err.getvalue()

    def snapshot(self):
        """Every entry below the temp dir: a file's mtime and SHA-256, a folder's name."""
        snap = {}
        for dp, dn, fn in os.walk(self.tmp):
            for d in dn:
                snap[os.path.join(dp, d)] = 'dir'
            for f in fn:
                p = os.path.join(dp, f)
                with open(p, 'rb') as fh:
                    snap[p] = (os.lstat(p).st_mtime_ns, hashlib.sha256(fh.read()).hexdigest())
        return snap

    def build(self):
        """Five loops from one spot (within 40 m of each other) on five dates at five hours; a pair of lines that start
        200 m apart somewhere else; a loner with no times and no elevation; a planned route on the shared spot; a draft
        with a companion and an id. Local time is UTC+1: the loops start at 06:00, 08:00, 13:00, 15:00 and 07:00."""
        for i, (day, hour) in enumerate(((1, 5), (8, 7), (15, 12), (22, 14), (29, 6))):
            self.trip('alpha-loop-%d' % i, track(LAT0 + i * 10 * M_LAT, LON0, utc(2026, 7, day, hour), loop=True),
                      date='2026-07-%02d' % day, start_time='06:00' if i == 0 else None)
        self.trip('pair-a', track(LAT0 + 0.2, LON0, utc(2026, 8, 1, 15), step_m=100.0), date='2026-08-01')
        self.trip('pair-b', track(LAT0 + 0.2 + 200 * M_LAT, LON0, utc(2026, 8, 2, 15), step_m=100.0), date='2026-08-02')
        self.trip('loner', track(LAT0 + 0.5, LON0, utc(2026, 8, 3, 15), step_m=100.0, times=False, eles=False), date='2026-08-03')
        self.trip('someday-goal', track(LAT0, LON0, utc(2026, 1, 1, 0), times=False), kind='planned')
        self.trip('hidden-draft', track(LAT0 + 0.7, LON0, utc(2026, 8, 4, 15), step_m=100.0), draft=True, date='2026-08-04',
                  party=NAME, strava_id=STRAVA_ID, start_time='09:30')


    def big(self):
        """45 single-day tracks, enough for no figure of the default report to be about fewer than three of anything:
        six shared places a fifth of a degree apart and twelve lone lines. Places 0, 2 and 4: six loops from one point,
        ten minutes apart from 06:00 local on six dates, and one line that starts there at 07:00 and ends 500 m away.
        Places 1, 3 and 5: four loops whose starts are 120 m apart in a row, at 05:00, 08:00, 11:00 and 14:00 local,
        the last two on one date. Places 0, 1 and 2 have one loop a year earlier; places 1 to 5 have one ride among
        the hikes. Weekdays, Monday to Sunday: 3 3 9 9 6 9 6."""
        for i in range(6):
            lat = LAT0 + 0.2 * i
            if i % 2 == 0:
                for j in range(6):
                    when = utc(2025, 6, 2, 5) if (i < 3 and j == 0) else utc(2026, 6, j + 1, 5, 10 * j)
                    self.trip('p%d-loop-%d' % (i, j), track(lat, LON0, when, loop=True), date=when.strftime('%Y-%m-%d'),
                              activity='mtb' if (i and j == 1) else 'hike')
                self.trip('p%d-out' % i, track(lat, LON0, utc(2026, 6, 10, 6), step_m=100.0), date='2026-06-10')
            else:
                for j, day in enumerate(((2025, 7, 2) if i < 3 else (2026, 7, 1), (2026, 7, 3), (2026, 7, 2), (2026, 7, 2))):
                    when = utc(day[0], day[1], day[2], 4 + 3 * j)
                    self.trip('p%d-loop-%d' % (i, j), track(lat + j * 120 * M_LAT, LON0, when, loop=True),
                              date=when.strftime('%Y-%m-%d'), activity='mtb' if j == 1 else 'hike')
        for k, hour in enumerate((2, 2, 3, 15, 15, 15, 16, 16, 18, 19, 19, 19)):      # 03:20 to 20:20 local, on a weekend
            when = utc(2026, 8, 1 + k % 2, hour, 20)
            self.trip('lone-%02d' % k, track(LAT0 + 2 + 0.1 * k, LON0, when, step_m=100.0), date=when.strftime('%Y-%m-%d'))


def body(report):
    """A default report without its two heading lines (the second one says what is left out, in so many words)."""
    return report.split('\n', 2)[2]


def hour_buckets(report):
    """The track counts of every 'by hour' line of a report."""
    return [int(n) for ln in report.split('\n') if ln.lstrip().startswith('by hour') for n in re.findall(r': (\d+)(?:,|$)', ln)]


class Arithmetic(unittest.TestCase):

    def test_quantile_and_clock_text(self):
        self.assertEqual(pa.quantile([5, 1, 3, 2, 4], .5), 3)
        self.assertEqual(pa.quantile([1, 2, 3, 4], .5), 2.5)                 # interpolated between the two middle values
        self.assertEqual(pa.quantile([10, 20], 0), 10)
        self.assertEqual(pa.quantile([10, 20], 1), 20)
        self.assertEqual(pa.quantile([10, 20, 30, 40, 50], .25), 20)
        self.assertEqual(pa.quantile([7], .9), 7)
        self.assertIsNone(pa.quantile([], .5))
        self.assertEqual(pa.hhmm(7.999), '08:00')                            # never '07:60'
        self.assertEqual(pa.hhmm(6.5), '06:30')
        self.assertEqual(pa.hhmm(0), '00:00')
        self.assertEqual(pa.hhmm(17 + 59 / 60.0), '17:59')

    def test_a_spread_point_needs_three_values_on_either_side(self):
        v = list(range(1, 46))                                                # 45 values
        self.assertAlmostEqual(pa.spread_point(v, .05), 3.2)                  # 2.2 places in: 1, 2 and 3 are at or below it
        self.assertAlmostEqual(pa.spread_point(v, .95), 42.8)                 # 43, 44 and 45 are at or above it
        self.assertEqual(pa.spread_point(v, .5), 23)
        self.assertEqual(pa.spread_point(v[::-1], .25), 12)                   # the order given does not matter
        self.assertIsNone(pa.spread_point(v[:40], .05))                       # 1.95 places in: only 1 and 2 are at or below it
        self.assertIsNone(pa.spread_point(v[:40], .95))
        self.assertEqual(pa.spread_point([1, 2, 3, 4, 5], .5), 3)             # 1, 2, 3 at or below; 3, 4, 5 at or above
        self.assertIsNone(pa.spread_point([1, 2, 3, 4, 5], .25))
        for n in range(5):
            self.assertIsNone(pa.spread_point(v[:n], .5), n)                  # the middle of four is between two tracks only
        for p in (0, 1):
            self.assertIsNone(pa.spread_point(list(range(1000)), p), p)       # never the smallest, never the largest
        self.assertEqual(pa.quantile(list(range(1000)), 0), 0)                # which quantile() itself still gives (--list)

    def test_quarter_hours(self):
        self.assertEqual(pa.quarter(7 + 7 / 60.0), '07:00')
        self.assertEqual(pa.quarter(7 + 8 / 60.0), '07:15')
        self.assertEqual(pa.quarter(12.5), '12:30')
        self.assertEqual(pa.quarter(12 + 44 / 60.0), '12:45')
        self.assertEqual(pa.quarter(0.1), '00:00')
        self.assertEqual(pa.quarter(23.95), '24:00')                          # "95% before 24:00", not "before 00:00"

    def test_hours_with_one_or_two_tracks_are_joined_to_the_next(self):
        hist = pa.Counter
        self.assertEqual(pa.merged_hours(hist({2: 1, 3: 8, 4: 5})), [(2, 3, 9), (4, 4, 5)])
        self.assertEqual(pa.merged_hours(hist({6: 3, 7: 2, 9: 1, 12: 4})), [(6, 6, 3), (7, 9, 3), (12, 12, 4)])
        self.assertEqual(pa.merged_hours(hist({6: 3, 12: 4, 17: 2})), [(6, 6, 3), (12, 17, 6)])   # a short run at the end joins the bucket before it
        self.assertEqual(pa.merged_hours(hist({6: 1, 7: 1, 8: 1})), [(6, 8, 3)])
        self.assertEqual(pa.merged_hours(hist({6: 1, 7: 1})), [])                                 # fewer than three in all: no bucket to give
        self.assertEqual(pa.merged_hours(hist({5: 0, 6: 3, 7: 0})), [(6, 6, 3)])
        self.assertEqual(pa.merged_hours(hist()), [])
        for counts in ({0: 1, 5: 2, 9: 1, 23: 1}, {h: 1 for h in range(24)}, {3: 2, 4: 2, 5: 2, 6: 2}, {1: 7}, {1: 2, 2: 2}):
            got = pa.merged_hours(hist(counts))
            self.assertTrue(all(n >= 3 for _a, _b, n in got), got)                                # never a bucket of one or two
            self.assertEqual(sum(n for _a, _b, n in got), sum(counts.values()))                   # and no track left out
            self.assertEqual([(a, b) for a, b, _n in got], sorted((a, b) for a, b, _n in got))

    def test_two_groups_side_by_side_share_buckets_that_give_neither_away(self):
        """All tracks and the single-day reports are printed hour by hour, one line under the other, so a reader can take
        one from the other. Hours are joined until all three (the two groups and what is between them) have none or
        three or more in every bucket."""
        hist = pa.Counter
        every = hist({2: 1, 3: 8, 4: 5, 5: 16, 12: 10, 14: 10, 15: 10})
        single = hist({3: 7, 4: 3, 5: 10, 12: 2, 14: 9, 15: 10})
        rest = every - single                                                # 02: 1, 03: 1, 04: 2, 05: 6, 12: 8, 14: 1
        self.assertEqual(pa.merged_hours(every), [(2, 3, 9), (4, 4, 5), (5, 5, 16), (12, 12, 10), (14, 14, 10), (15, 15, 10)])
        # on their own buckets the two lines would give away "02 to 03: 9" less "03: 7" (two tracks) and "14: 10" less "14: 9"
        got = pa.merged_hours(every, single, rest)
        # 02 to 04 hold four other tracks; 12 has two single-day reports and is joined with 14, whose one other track is then
        # one of nine; 15 has ten single-day reports and no other track
        self.assertEqual(got, [(2, 4, 14), (5, 5, 16), (12, 14, 20), (15, 15, 10)])
        for a, b, _n in got:
            for group in (every, single, rest):
                self.assertNotIn(sum(group[h] for h in range(a, b + 1)), (1, 2))
        self.assertEqual(pa.merged_hours(every, single, hist()), pa.merged_hours(every, single))
        self.assertEqual(pa.merged_hours(every, single), [(2, 3, 9), (4, 4, 5), (5, 5, 16), (12, 14, 20), (15, 15, 10)])
        self.assertEqual(pa.merged_hours(hist({6: 5, 7: 5}), hist({6: 4, 7: 5}), hist({6: 1})), [])   # one other track in all: no buckets
        self.assertEqual(pa.merged_hours(hist({6: 5, 7: 5}), hist({6: 3, 7: 4}), hist({6: 2, 7: 1})), [(6, 7, 10)])
        # a short run at the end goes back as far as it takes: 09 has one other track, 07 none, 06 three
        self.assertEqual(pa.merged_hours(hist({6: 6, 7: 5, 9: 4}), hist({6: 3, 7: 5, 9: 3}), hist({6: 3, 9: 1})), [(6, 9, 15)])
        self.assertEqual(pa.merged_hours(hist({6: 6, 7: 5, 9: 4}), hist({6: 3, 7: 5, 9: 4}), hist({6: 3})), [(6, 6, 6), (7, 7, 5), (9, 9, 4)])

    def test_a_count_of_places_below_three_is_not_given(self):
        self.assertEqual([pa.few(n) for n in (0, 1, 2, 3, 16)], ['fewer than 3', 'fewer than 3', 'fewer than 3', '3', '16'])
        self.assertEqual([pa.few_of(n, 16) for n in (0, 1, 2, 3, 13)], ['fewer than 3', 'fewer than 3', 'fewer than 3', '3', '13'])
        # one, two or no places left over read the same: the remainder would be a figure about one place too
        self.assertEqual([pa.few_of(n, 16) for n in (14, 15, 16)], ['all but fewer than 3'] * 3)
        self.assertEqual([pa.few_of(n, 4) for n in (2, 3, 4)], ['fewer than 3', 'all but fewer than 3', 'all but fewer than 3'])
        self.assertEqual(pa.FEW, 3)

    def test_clock_spread_goes_round_midnight(self):
        self.assertEqual(pa.hours_spread([6, 7, 15]), 9)
        self.assertAlmostEqual(pa.hours_spread([23 + 50 / 60.0, 10 / 60.0]), 20 / 60.0)    # 23:50 and 00:10: 20 minutes
        self.assertEqual(pa.hours_spread([0, 12]), 12)
        self.assertEqual(pa.hours_spread([3, 17]), 10)                       # the short way round: 17:00 to 03:00
        self.assertEqual(pa.hours_spread([5]), 0.0)
        self.assertEqual(pa.hours_spread([]), 0.0)
        self.assertEqual(pa.hours_spread([8, 8, 8]), 0.0)

    def test_neighbourhoods_stay_honest_while_groups_chain(self):
        # A, B, C in a line 120 m apart: A and C are 240 m apart. Each has its true neighbours; one chain joins all three.
        pts = [(i, 'S', LAT0 + i * 120 * M_LAT, LON0) for i in range(3)]
        near = pa.neighbours(pts, 150)
        self.assertEqual([sorted(n) for n in near], [[0, 1], [0, 1, 2], [1, 2]])
        groups = pa.clusters(pts, near)
        self.assertEqual(groups, [[0, 1, 2]])
        self.assertAlmostEqual(pa.diameter(pts, groups[0]), 240, delta=0.5)
        self.assertEqual(pa.clusters(pts, pa.neighbours(pts, 100)), [[0], [1], [2]])
        self.assertEqual(pa.diameter(pts, [1]), 0.0)

    def test_the_radius_is_inclusive_and_measured_on_the_ground(self):
        east = 100.0 / (111194.9 * math.cos(math.radians(LAT0)))             # 100 m of longitude at this latitude, in degrees
        pts = [(0, 'S', LAT0, LON0), (1, 'S', LAT0, LON0 + east), (2, 'S', LAT0 + 100 * M_LAT, LON0)]
        self.assertEqual([sorted(n) for n in pa.neighbours(pts, 101)], [[0, 1, 2], [0, 1], [0, 2]])   # the diagonal is 141 m
        self.assertEqual([sorted(n) for n in pa.neighbours(pts, 99)], [[0], [1], [2]])
        self.assertEqual([sorted(n) for n in pa.neighbours(pts, 142)], [[0, 1, 2]] * 3)
        d = pa.geo.hav(pts[0][2:], pts[2][2:])
        self.assertEqual(sorted(pa.neighbours(pts[::2], d)[0]), [0, 1])       # a point exactly on the radius is inside it

    def test_spacing_never_bridges_a_gap_between_segments(self):
        a = [(LAT0, LON0, None, 0.0), (LAT0 + 10 * M_LAT, LON0, None, 60.0)]
        b = [(LAT0 + 5000 * M_LAT, LON0, None, 7200.0)]                      # a second segment 5 km and two hours on
        dt, dd = pa.spacing([a, b])
        self.assertEqual(dt, 60.0)                                           # bridged, the medians would be an hour and 2.5 km
        self.assertAlmostEqual(dd, 10.0, delta=0.1)
        self.assertEqual(pa.spacing([a[:1], b]), (None, None))               # two one-point segments: nothing to measure
        dt, dd = pa.spacing([[(LAT0, LON0, None, None), (LAT0 + 10 * M_LAT, LON0, None, None)]])
        self.assertIsNone(dt)                                                # no times: no time gap, but still a distance
        self.assertAlmostEqual(dd, 10.0, delta=0.1)
        self.assertEqual(pa.spacing([[(LAT0, LON0, None, 0.0)]]), (None, None))

    def test_conflict_copy_names(self):
        for name in ('meta 3.json', 'map-wide 4.webp', 'first-lap 2', 'region-desktop.svg 3.html', 'region-desktop.base 12.svg',
                     '01 2.md', '01.sm 2.webp'):
            self.assertTrue(pa.conflict_copy(name), name)
        for name in ('meta.json', 'map-wide.webp', 'first-lap-2', '01.md', '01.sm.webp', 'day 2 notes.md', 'track.gpx', '2', 'a 2b.txt'):
            self.assertFalse(pa.conflict_copy(name), name)


class WrittenOut(unittest.TestCase):
    """What --site looks for in a text file. The point is invented: 10.54321 north, 100.12345 west, a three-digit
    longitude because that is the form the first version of this check could not see."""

    LAT, LON = 10.54321, -100.12345

    def index(self, lat=None, lon=None):
        """The index of one track from (lat, lon) to a point a fifth of a degree north and east of it."""
        lat, lon = (self.LAT, self.LON) if lat is None else (lat, lon)
        return pa.end_index([{'pts': [(lat, lon, None, None), (lat + 0.5, lon, None, None), (lat + 0.2, lon + 0.2, None, None)]}])[0]

    def own(self, text, index=None):
        return pa.written_positions(text, self.index() if index is None else index)[0]

    def test_the_index_holds_the_first_and_the_last_point_of_every_track_that_was_read(self):
        index, n = pa.end_index([{'pts': [(10.5, -100.25, None, None), (60.0, 60.0, None, None), (11.5, -101.25, None, None)]},
                                 {'error': 'not read'}, {'pts': []}, {'pts': [(12.0, 13.0, None, None)]}])
        self.assertEqual(n, 4)                                # two ends, then a one-point track's point as its first and its last
        self.assertEqual(sorted(index), [10500, 11500, 12000, 13000, 100250, 101250])        # the point in the middle is not looked for
        self.assertEqual(index[10500], [(0, 0, 10.5)])
        self.assertEqual(index[100250], [(0, 1, 100.25)])     # a longitude, without its sign
        self.assertEqual(index[101250], [(1, 1, 101.25)])
        self.assertEqual(index[12000], [(2, 0, 12.0), (3, 0, 12.0)])
        self.assertEqual(pa.end_index([]), ({}, 0))

    def test_a_tracks_own_end_is_seen_however_it_is_written(self):
        for text in ('<p>[10.54321, -100.12345]</p>',                                        # all the old pattern saw, and with two digits only
                     'var line = [[-100.12345, 10.54321], [-100.11345, 10.55321]];',         # longitude first, as web maps write it
                     '{"type":"LineString","coordinates":[[-100.12345,10.54321]]}',
                     '{"lat": 10.54321, "lng": -100.12345}',                                 # keyed
                     '{"lng": -100.12345, "name": "x", "lat": 10.54321}',
                     '<a data-lat="10.54321" data-lon="-100.12345">x</a>',                   # attributes
                     '<trkpt lat="10.54321" lon="-100.12345"/>',
                     'robots: 10.54321 -100.12345',                                          # a space, a semicolon, a slash, a query
                     '10.54321;-100.12345', '10.54321/-100.12345', 'https://example.test/?mlat=10.54321&mlon=-100.12345',
                     '<p>10.54321\u00b0N 100.12345\u00b0W</p>',                              # a letter for the hemisphere, no minus
                     '<p>lat-10.54321 lon-100.12345</p>',                                    # a hyphen that is not a minus
                     '<p>10.543, -100.123</p>',                                              # three decimals: what --list calls a position
                     '<p>10.5432, -100.1234</p>',                                            # cut short to four
                     '<p>10.5432, -100.1235</p>',                                            # rounded to four
                     '<p>10.54321000, -100.12345000</p>',                                    # more decimals than the track has
                     '<p>10.54321</p>' + '<i>x</i>' * 2000 + '<p>100.12345</p>',             # far apart, in one file
                     '<p>[10.74321, -99.92345]</p>'):                                        # the last point of the track
            self.assertIs(self.own(text), True, text)

    def test_what_is_not_a_tracks_own_end(self):
        for text in ('<p>10.54321 and no longitude</p>', '<p>-100.12345</p>', '',
                     '<p>10.54321 and again 10.54321</p>', '<p>10.543, 10.5432, 10.54321</p>',   # the latitude twice is not a longitude
                     '<p>-100.12345 100.123</p>',
                     '<p>10.54321, -99.92345</p>',                                           # the first point's latitude, the last point's longitude
                     '<p>11.04321, -100.12345</p>',                                          # a point in the middle of the track
                     '<p>10.54, -100.12</p>', '<p>10.5, -100.1</p>',                         # fewer than three decimals
                     '<p>10.544, -100.124</p>',                                              # next door: neither rounded nor cut short
                     '<p>10.5433, -100.1236</p>', '<p>10.5431, -100.1233</p>',
                     '<p>10.54322, -100.12346</p>',
                     '<p>1010.54321, 9100.12345</p>',                                        # longer numbers that end the same way
                     'v1.10.54321 and 2.100.12345',
                     '<path d="M10.5 100.1L12.25 30.75"/><svg viewBox="0 0 718.5 620.25">'):
            self.assertIs(self.own(text), False, text)

    def test_one_number_stands_for_both_only_when_it_is_there_twice(self):
        square = self.index(10.125, 10.125)                                                  # as far north as east
        self.assertIs(self.own('<p>10.125</p>', square), False)
        self.assertIs(self.own('<p>10.125 and then 99.5</p>', square), False)
        self.assertIs(self.own('<p>10.125, 10.125</p>', square), True)
        self.assertIs(self.own('<p>10.125, 10.1250</p>', square), True)

    def test_two_long_decimals_side_by_side_are_a_look_alike(self):
        def pair(text):
            return pa.written_positions(text, {})[1]
        self.assertEqual(pair('<p>12.3456, 101.2345</p>'), 'loose')
        self.assertEqual(pair('<p>-101.2345 12.3456</p>'), 'loose')                           # either order, either sign
        self.assertEqual(pair('{"a": 0.1234, "b": 2.5000}'), 'loose')                        # anything that fits: this count knows no track
        self.assertIsNone(pair('<p>101.2345, 120.3456</p>'))                                 # neither could be a latitude
        self.assertIsNone(pair('<p>12.3456, 181.2345</p>'))                                  # the second could not be a longitude
        self.assertEqual(pair('<p>90.0000, 180.0000</p>'), 'loose')
        self.assertIsNone(pair('<p>12.345, 101.234</p>'))                                    # three decimals each
        self.assertIsNone(pair('<p>12.3456, 101.234</p>'))
        self.assertIsNone(pair('<p>12.3456</p>'))
        self.assertIsNone(pair('<path d="M12.5 101.25L13.75 102.5"/><svg viewBox="0 0 718.5 620.25">'))
        self.assertEqual(pair('12.3456' + ' ' * 40 + '101.2345'), 'loose')                   # 40 characters between them
        self.assertIsNone(pair('12.3456' + ' ' * 41 + '101.2345'))
        self.assertEqual(pair('12.3456, 500.1234, 101.2345'), 'loose')                       # with a number between them that fits neither
        self.assertEqual(pa.PAIR_GAP, 40)

    def test_the_proportions_of_a_photo_row_are_counted_apart(self):
        def pair(text):
            return pa.written_positions(text, {})[1]
        self.assertEqual(pair('<div class="jrow" style="--n:3;--sum:4.1234;--ar:1.3333">'), 'sized')    # core.py writes these
        self.assertEqual(pair('<div style="--sum: 4.1234; --ar:1.3333"><a style="--ar:0.7500;--fg:2">'), 'sized')
        self.assertEqual(pair('<div style="--dx:-4.1234;--dy:-1.3333">'), 'sized')
        self.assertEqual(pair('<div style="--sum:4.1234" data-x="1.3333">'), 'loose')         # one of the two is no custom property
        self.assertEqual(pair('<div style="sum:4.1234;ar:1.3333">'), 'loose')                # nor is an ordinary property
        self.assertEqual(pair('{"--lat": 12.3456, "--lon": 101.2345}'), 'loose')             # nor a JSON key that looks like one
        # a page of photo rows is still searched: a position beside them is not hidden by them, before or after
        self.assertEqual(pair('<div style="--sum:4.1234;--ar:1.3333"><p>12.3456, 101.2345</p>'), 'loose')
        self.assertEqual(pair('<p>12.3456, 101.2345</p><div style="--sum:4.1234;--ar:1.3333">'), 'loose')
        self.assertEqual(pa.written_positions('<div style="--sum:4.1234;--ar:1.3333"><p>10.543, -100.123</p>', self.index()), (True, 'sized'))
        self.assertEqual(pa.written_positions('<p>10.543, -100.123</p>', self.index()), (True, None))
        self.assertEqual(pa.written_positions('<p>10.54321, -100.12345</p>', self.index()), (True, 'loose'))


class EdgeOfTheCalendar(unittest.TestCase):
    """Some apps write 0001-01-01T00:00:00Z for a time that was never set. A zone west of Greenwich puts that before
    year 1, which datetime cannot hold: the track is then read as UTC, like one whose zone is unknown, and the report
    is still made."""

    FIRST = -62135596800.0   # 0001-01-01T00:00:00Z

    def test_a_time_before_year_one_in_its_zone_is_read_as_utc(self):
        row = {'pts': [(10.0, 10.0, None, self.FIRST), (10.0, 10.001, None, self.FIRST + 60)], 'tz': 'America/Los_Angeles'}
        when, how = pa.local_start(row)
        self.assertEqual(how, 'unknown')
        self.assertEqual((when.year, when.month, when.day, when.hour, when.utcoffset()), (1, 1, 1, 0, timedelta(0)))

    def test_an_ordinary_time_in_the_same_zone_is_not_touched_by_the_fallback(self):
        row = {'pts': [(10.0, 10.0, None, 1700000000.0)], 'tz': 'America/Los_Angeles'}
        when, how = pa.local_start(row)
        self.assertEqual(how, 'field')
        self.assertEqual(when.utcoffset(), timedelta(hours=-8))


class Images(unittest.TestCase):

    @staticmethod
    def seg(marker, data):
        return b'\xff' + bytes([marker]) + struct.pack('>H', len(data) + 2) + data

    @staticmethod
    def png(*chunks):
        return b'\x89PNG\r\n\x1a\n' + b''.join(struct.pack('>I', len(d)) + kind + d + b'\0\0\0\0' for kind, d in chunks)

    def test_webp_chunks(self):
        self.assertEqual(pa.webp_chunks(webp((b'VP8 ', b'abc'))), ['VP8 '])                     # an odd length is padded
        full = webp((b'VP8X', b'\x2c' + b'\0' * 9), (b'ICCP', b'p' * 5), (b'VP8 ', b'xx'), (b'EXIF', b'Exif\0\0II'), (b'XMP ', b'<x/>'))
        self.assertEqual(pa.webp_chunks(full), ['VP8X', 'ICCP', 'VP8 ', 'EXIF', 'XMP '])
        self.assertIsNone(pa.webp_chunks(b'not a riff file at all'))
        self.assertIsNone(pa.webp_chunks(b'RIFF\x04\0\0\0WAVE'))
        self.assertIsNone(pa.webp_chunks(b''))

    def test_jpeg_segments(self):
        seg = self.seg
        soi, jfif, scan = b'\xff\xd8', seg(0xE0, b'JFIF\0'), seg(0xDA, b'')
        self.assertEqual(pa.jpeg_metadata(soi + jfif + scan), set())
        self.assertEqual(pa.jpeg_metadata(soi + jfif + seg(0xE1, b'Exif\0\0MM') + seg(0xE2, b'ICC_PROFILE\0') + scan), {'EXIF', 'ICC'})
        self.assertEqual(pa.jpeg_metadata(soi + seg(0xE1, b'http://ns.adobe.com/xap/1.0/\0<x/>') + seg(0xED, b'Photoshop 3.0\0')
                                          + seg(0xFE, b'a comment') + scan), {'XMP', 'IPTC', 'COM'})
        self.assertEqual(pa.jpeg_metadata(soi + seg(0xEE, b'Adobe\0') + scan), set())           # the colour marker is not metadata
        self.assertEqual(pa.jpeg_metadata(soi + seg(0xE2, b'MPF\0') + scan), {'APP'})           # any other application data
        self.assertEqual(pa.jpeg_metadata(soi + jfif + b'\xff' + seg(0xE1, b'Exif\0\0II') + scan), {'EXIF'})   # a fill byte
        self.assertEqual(pa.jpeg_metadata(soi + jfif + scan + seg(0xE1, b'Exif\0\0II')), set())  # after the picture starts: not read
        self.assertIsNone(pa.jpeg_metadata(b'RIFF'))
        self.assertIsNone(pa.jpeg_metadata(b''))

    def test_png_chunks(self):
        png = self.png
        self.assertEqual(pa.png_metadata(png((b'IHDR', b'\0' * 13), (b'IDAT', b'x'), (b'IEND', b''))), set())
        self.assertEqual(pa.png_metadata(png((b'IHDR', b'\0' * 13), (b'eXIf', b'II'), (b'iCCP', b'p'), (b'tIME', b'\0' * 7),
                                             (b'tEXt', b'Comment\0hello'), (b'iTXt', b'XML:com.adobe.xmp\0<x/>'), (b'IEND', b''))),
                         {'EXIF', 'ICC', 'TIME', 'TEXT', 'XMP'})
        self.assertEqual(pa.png_metadata(png((b'IHDR', b'\0' * 13), (b'zTXt', b'k\0\0x'))), {'TEXT'})
        self.assertIsNone(pa.png_metadata(b'GIF89a'))

    def test_scan_counts_one_per_file_and_never_opens_other_types(self):
        with tempfile.TemporaryDirectory() as d:
            files = {'a.webp': PLAIN, 'b.webp': TAGGED, 'c.WEBP': b'junk', 'd.jpg': b'\xff\xd8' + self.seg(0xE1, b'Exif\0\0II') + self.seg(0xDA, b''),
                     'e.jpeg': b'\xff\xd8' + self.seg(0xDA, b''), 'f.png': self.png((b'eXIf', b'II')), 'g.heic': b'anything',
                     'h.webp': webp((b'VP8X', b'\0' * 10), (b'ICCP', b'pp'), (b'XMP ', b'<x/>'), (b'VP8 ', b'ab'))}
            for name, data in files.items():
                write(os.path.join(d, name), data)
            scan = pa.scan_images(sorted(os.path.join(d, f) for f in files) + [os.path.join(d, 'gone.webp')])
        self.assertEqual(scan['files'], 9)
        self.assertEqual(dict(scan['kinds']), {'WebP': 5, 'JPEG': 2, 'PNG': 1})
        self.assertEqual(dict(scan['with']), {'EXIF': 3, 'ICC': 1, 'XMP': 1})
        self.assertEqual((scan['unreadable'], scan['unchecked']), (2, 1))          # the junk and the missing file; the .heic
        lines = pa.image_lines(scan, '   ')
        self.assertEqual(lines[0], '   9 files: 2 JPEG, 1 PNG, 5 WebP')
        self.assertEqual(lines[1], '   with EXIF: 3; with XMP: 1; with an ICC colour profile: 1; not readable as an image: 2; '
                                   'other file types (not checked): 1')
        other = pa.image_lines({'files': 1, 'kinds': pa.Counter(PNG=1), 'with': pa.Counter(TEXT=1), 'unreadable': 0, 'unchecked': 0}, '')
        self.assertEqual(other, ['1 file: 1 PNG', 'with EXIF: 0; with XMP: 0; with an ICC colour profile: 0; with TEXT: 1; '
                                                  'not readable as an image: 0; other file types (not checked): 0'])


class Report(Tree):

    def test_every_count_of_the_default_report(self):
        self.build()
        out = self.run_audit()
        lines = out.split('\n')
        self.assertEqual(lines[0], 'PRIVACY AUDIT: counts only. Nothing below names a trip or a place; --list does, for the author.')
        self.assertEqual(lines[1], 'Where and when are never about one track or one place: no earliest or latest start, the spread to the '
                                   'quarter hour, hours joined until none holds one or two tracks, "fewer than 3" for a count of places '
                                   'below that.')
        for want in (
                '   GPX files: 10 = 9 recorded tracks + 1 planned route; unreadable: 0; with no track points: 0',
                '   the recorded tracks: 9 single-day reports; 0 days of 0 multi-day trips; 0 days of 0 journals; 9 reports in all',
                '   recorded tracks in a draft (no page and no download; the files stay in the repository, and the maps under '
                'rendered/site/ keep the line and the title of a trip they already draw until tools/render.py is run again): 1',
                '   trips with no GPX at all: 0; trip folders that could not be read: 0',
                '   recorded tracks (9 files, 54 points):',
                '     a time on every point: 8; on some: 0; on none: 1',
                '     an elevation on every point: 8; on some: 0; on none: 1',
                "     creator text: this site's own in 0; another in 9; none in 0",
                '     also in the files: track or route names in 9',
                # nine files: a median has three of them on either side, the 10% and 90% points do not, so no range
                "     typical gap between points (each file's median; too few files for a range): 60 s and 20 m",
                # one planned route: how many files carry what, but no point total and no spacing, which would be that file's own
                "   planned routes (1 file; too few for a point total or a spacing that is not one file's own):",
                '     a time on every point: 0; on some: 0; on none: 1',
                '3. STARTS AND FINISHES (the same place: within 150 m; a shared place: 3 or more separate outings)',
                '   tracks that finish within 150 m of their own start: 5 of 9',
                # the five loops share one place: every count of tracks "there" would be that one place's size
                '     3 or more tracks there: at fewer than 3 places, so no count is given',
                '     5 or more tracks there: at fewer than 3 places, so no count is given',
                '     10 or more tracks there: at fewer than 3 places, so no count is given',
                '     3 or more outings there: at fewer than 3 places, so no count is given',
                '   places (starts and finishes chained together, each within 150 m of the next): 9',
                '     shared by 2 or more outings: fewer than 3; by 3 or more outings: fewer than 3; by 5 or more outings: fewer than 3; '
                'by 10 or more outings: fewer than 3',
                '   places shared by 3 or more outings: fewer than 3, so nothing more is said about them here (--list does, for the author)',
                # eight start times: only the middle has three tracks on either side; 06, 07 and 08 hold one track each
                '   all tracks with times (8), to the quarter hour: half before 14:00',
                '     by hour (hour: tracks; hours are joined until none holds one or two tracks): 06 to 08: 3, 13 to 16: 5',
                '     by weekday: not given (fewer than 3 tracks on one side of the weekend)',
                '   single-day reports only (8), to the quarter hour: half before 14:00',
                '   tracks without timestamps: 1; read in a guessed zone (no timezone: field): 0; with a timezone: this system does '
                'not know (read as UTC): 0',
                '   start_time in the front matter: 2 of 9 single-day reports, 0 of 0 multi-day days, 0 of 0 journal days; equal to '
                "the track's first timestamp, to the minute: 1 of 2",
                '5. PHOTOS in content/trips/*/photos (every file there, whatever its name: the build publishes them all)',
                '   0 files: none',
                '   front matter: 10 files (10 index.md, 0 day files); strava_id in 1; timezone in 10; start_time in 2; party in 1',
                '   rendered/trips/*/meta.json: 0 files; with the start and the end written out as coordinates: 0',
                '   the 10 GPX files themselves, and every earlier version of every file (git history; this tool does not read it)'):
            self.assertIn(want, lines)
        self.assertTrue(lines[-2].startswith('WHAT THIS CANNOT TELL YOU: what any place is'))
        self.assertEqual(lines[-1], '')
        self.assertEqual([ln[:2] for ln in lines if re.match(r'\d\. ', ln)], ['1.', '2.', '3.', '4.', '5.', '6.'])
        absent = [ln for ln in lines if ln.startswith('     in no file: ')]
        self.assertEqual(len(absent), 2)
        for label in ('device or app extensions', 'links', 'waypoints', 'named points', 'GPS quality fields', 'XML comments',
                      'unknown elements', 'a file name or time', 'descriptions or type text'):
            self.assertIn(label, absent[0])
        self.assertNotIn('track or route names', absent[0])
        # what the first version printed here, each a figure about one place or one track
        for gone in ('earliest', 'latest', 'either 5', 'the 1 place', 'at one of them', '6 points', '20 to 20 m', ' 06: 1', '16: 3',
                     'by 3 or more outings: 1', 'different date', '06:00', '16:00', '5 or more tracks there: start'):
            self.assertNotIn(gone, body(out))
        self.assertEqual(sum(1 for ln in lines if 'typical gap' in ln), 1)       # none for the planned route

    def test_the_listing_has_every_figure_exactly(self):
        self.build()
        out = self.exact()
        for want in (
                "     typical gap between points (each file's median; in brackets the middle 80% of files): 60 s (60 to 60 s) and "
                '20 m (20 to 100 m)',
                '   planned routes (1 file, 6 points):',
                "     typical gap between points (each file's median; in brackets the middle 80% of files): no times and 20 m (20 to 20 m)",
                '   tracks that finish within 150 m of their own start: 5 of 9',
                '     3 or more tracks there: start 5; finish 5; either 5',     # the planned route on the same spot is not a track
                '     5 or more tracks there: start 5; finish 5; either 5',
                '     10 or more tracks there: start 0; finish 0; either 0',
                '     3 or more outings there: start 5; finish 5; either 5',
                '   places (starts and finishes chained together, each within 150 m of the next): 9',
                '     shared by 2 or more outings: 1; by 3 or more outings: 1; by 5 or more outings: 1; by 10 or more outings: 0',
                '   the 1 place shared by 3 or more outings:',
                '     tracks that start or finish at one of them: 5 of 9',
                '     every start there on a different date: 1; starts in more than one calendar year: 0; more than one activity: 0',
                '     start times all within 90 minutes: 0; spread over 4 hours or more: 1; wider than 150 m from end to end (a chain '
                'can be): 0',
                '   all tracks with times (8): earliest 06:00; 5% before 06:21; a quarter before 07:45; half before 14:00; three '
                'quarters before 16:00; 95% before 16:00; latest 16:00',
                '     by hour (hour: tracks): 06: 1, 07: 1, 08: 1, 13: 1, 15: 1, 16: 3',
                '     by weekday, Monday to Sunday: 0 1 5 0 0 1 1; on a Saturday or Sunday: 25%'):
            self.assertIn(want, out.split('\n'))
        self.assertEqual(len([ln for ln in out.split('\n') if ln.startswith('   single-day reports only (8): earliest 06:00; 5% before 06:21;')]), 1)
        for masked in ('fewer than 3', 'quarter hour', 'are joined', 'no count is given', 'not given', 'too few'):
            self.assertNotIn(masked, out)

    def test_the_default_report_where_nothing_is_about_fewer_than_three(self):
        self.big()
        out = self.run_audit()
        lines = out.split('\n')
        for want in (
                '   GPX files: 45 = 45 recorded tracks + 0 planned routes; unreadable: 0; with no track points: 0',
                '   recorded tracks (45 files, 270 points):',
                # 30 loops step 20 m, 15 lines step 100 m: four files in ten are beyond each end of the range
                "     typical gap between points (each file's median; in brackets the middle 80% of files): 60 s (60 to 60 s) and "
                '20 m (20 to 100 m)',
                '   tracks that finish within 150 m of their own start: 30 of 45',
                # places 0, 2, 4: seven tracks start at the point and six finish there. Places 1, 3, 5: the two loops in the
                # middle of the row have three tracks within 150 m, the two at its ends have two
                '     3 or more tracks there: start 27; finish 24; either 27',
                '     5 or more tracks there: start 21; finish 18; either 21',
                '     10 or more tracks there: at fewer than 3 places, so no count is given',
                '     3 or more outings there: start 27; finish 24; either 27',
                '     5 or more outings there: start 21; finish 18; either 21',
                '     10 or more outings there: at fewer than 3 places, so no count is given',
                # six shared places, three ends of the lines out, 24 ends of the lone lines
                '   places (starts and finishes chained together, each within 150 m of the next): 33',
                '     shared by 2 or more outings: 6; by 3 or more outings: 6; by 5 or more outings: 3; by 10 or more outings: fewer than 3',
                '   the 6 places shared by 3 or more outings:',
                '     tracks that start or finish at one of them: 33 of 45',
                # five of the six have a ride among the hikes: the sixth is not to be worked out from this line
                '     every start there on a different date: 3; starts in more than one calendar year: 3; more than one activity: '
                'all but fewer than 3',
                '     start times all within 90 minutes: 3; spread over 4 hours or more: 3; wider than 150 m from end to end (a chain '
                'can be): 3',
                # to the minute these are 04:28, 06:10, 06:50, 14:00 and 20:08; the earliest is 03:20 and the latest 20:20
                '   all tracks with times (45), to the quarter hour: 5% before 04:30; a quarter before 06:15; half before 06:45; '
                'three quarters before 14:00; 95% before 20:15',
                # 03 has two tracks, 04 one; 17 has two, 19 one
                '     by hour (hour: tracks; hours are joined until none holds one or two tracks): 03 to 04: 3, 05: 3, 06: 18, 07: 3, 08: 3, '
                '11: 3, 14: 3, 16: 3, 17 to 19: 3, 20: 3',
                '     by weekday, Monday to Sunday: 3 3 9 9 6 9 6; on a Saturday or Sunday: 33%',
                '   single-day reports only (45), to the quarter hour: 5% before 04:30; a quarter before 06:15; half before 06:45; '
                'three quarters before 14:00; 95% before 20:15'):
            self.assertIn(want, lines)
        for gone in ('earliest', 'latest', '03:20', '20:20', '04:28', '20:08', '06:10', '06:50', 'more than one activity: 5'):
            self.assertNotIn(gone, body(out))
        self.assertEqual(hour_buckets(out), [3, 3, 18, 3, 3, 3, 3, 3, 3, 3] * 2)
        exact = self.exact()
        for want in (
                '     10 or more tracks there: start 0; finish 0; either 0',
                '     shared by 2 or more outings: 6; by 3 or more outings: 6; by 5 or more outings: 3; by 10 or more outings: 0',
                '     every start there on a different date: 3; starts in more than one calendar year: 3; more than one activity: 5',
                '   all tracks with times (45): earliest 03:20; 5% before 04:28; a quarter before 06:10; half before 06:50; three '
                'quarters before 14:00; 95% before 20:08; latest 20:20',
                '     by hour (hour: tracks): 03: 2, 04: 1, 05: 3, 06: 18, 07: 3, 08: 3, 11: 3, 14: 3, 16: 3, 17: 2, 19: 1, 20: 3'):
            self.assertIn(want, exact.split('\n'))

    def test_no_default_report_has_a_figure_about_one_track_or_one_place(self):
        """Whatever the tree, the counts-only report gives no extreme, no hour bucket below three and no count of places
        below three, and says nothing more about the shared places when there are fewer than three of them."""
        def loops(n, hours, lat=LAT0):
            for i in range(n):
                self.trip('t%d-%d' % (round(lat * 10), i), track(lat, LON0, utc(2026, 6, 1 + i, hours[i % len(hours)]), loop=True),
                          date='2026-06-%02d' % (1 + i))
        for grow in (lambda: loops(1, [5]), lambda: loops(2, [5, 9]), lambda: loops(4, [5, 9, 9, 13]),
                     lambda: loops(3, [7], LAT0 + 0.3), lambda: loops(5, [4, 4, 4, 20, 21], LAT0 + 0.6), self.build, self.big):
            grow()
            for args in ([], ['--min-cluster', '2'], ['--radius', '400'], ['--min-cluster', '5']):
                out = self.run_audit(*args)
                self.assertEqual(out.split('\n')[:2], pa.HEAD)
                out = body(out)
                self.assertIsNone(re.search(r'earliest|latest', out))
                self.assertTrue(all(n >= 3 for n in hour_buckets(out)), out)
                for n in re.findall(r'or more outings: (\d+)', out) + re.findall(r'of the next\): (\d+)', out) \
                        + re.findall(r'the (\d+) places? shared', out) + re.findall(r'(?:date|year|activity|minutes|more|be\)): (\d+)', out):
                    self.assertGreaterEqual(int(n), 3, out)
                if 'nothing more is said about them' in out:
                    self.assertNotIn('at one of them', out)
                    self.assertNotIn('different date', out)
                self.assertIsNone(re.search(r'(?:start|finish|either) [012]\b', out), out)

    def test_a_count_of_tracks_is_given_only_when_three_places_stand_behind_it(self):
        # at each of three spots three lines end that set out from three different points: the finishes meet, the starts never do
        for i in range(3):
            for j in range(3):
                step = 100.0 * (j + 1)
                self.trip('in-%d-%d' % (i, j), track(LAT0 + 0.2 * i - 5 * step * M_LAT, LON0, utc(2026, 6, 1 + 3 * i + j, 5), step_m=step),
                          date='2026-06-%02d' % (1 + 3 * i + j))
        out = self.run_audit()
        self.assertIn('     3 or more tracks there: start at fewer than 3 places; finish 9; either 9\n', out)
        self.assertIn('     5 or more tracks there: at fewer than 3 places, so no count is given\n', out)
        self.assertIn('each within 150 m of the next): 12\n     shared by 2 or more outings: 3; by 3 or more outings: 3; by 5 or more '
                      'outings: fewer than 3;', out)
        self.assertIn('   the 3 places shared by 3 or more outings:\n     tracks that start or finish at one of them: 9 of 9\n', out)
        self.assertIn('     3 or more tracks there: start 0; finish 9; either 9\n', self.exact())
        # with a fourth line into the first spot only, "5 or more" would be a count at one place... and with two spots, "3 or more" too
        two = self.run_audit('--radius', '150', '--min-cluster', '4')
        self.assertIn('     4 or more tracks there: at fewer than 3 places, so no count is given\n', two)
        self.assertIn('   places shared by 4 or more outings: fewer than 3, so nothing more is said about them here', two)

    def test_radius_and_min_cluster_change_the_result(self):
        self.build()
        wide = self.exact('--radius', '250')              # the pair's starts are 200 m apart, and so are its finishes
        self.assertIn('STARTS AND FINISHES (the same place: within 250 m;', wide)
        self.assertIn('each within 250 m of the next): 7\n', wide)
        self.assertIn('shared by 2 or more outings: 3; by 3 or more outings: 1;', wide)
        self.assertIn('tracks that finish within 250 m of their own start: 5 of 9', wide)
        self.assertIn('each within 250 m of the next): 7\n     shared by 2 or more outings: 3; by 3 or more outings: fewer than 3;',
                      self.run_audit('--radius', '250'))
        two = self.exact('--radius', '250', '--min-cluster', '2')
        self.assertIn('a shared place: 2 or more separate outings)', two)
        self.assertIn('     2 or more tracks there: start 7; finish 7; either 7\n     5 or more tracks there: start 5;', two)
        self.assertIn('shared by 2 or more outings: 3; by 5 or more outings: 1; by 10 or more outings: 0', two)
        self.assertIn('the 3 places shared by 2 or more outings:\n     tracks that start or finish at one of them: 7 of 9', two)
        # three places stand behind "2 or more" (the loops, the pair's starts, the pair's finishes), but tracks start at two of
        # them only and finish at two of them only: the default report gives the one count that is about all three
        two = self.run_audit('--radius', '250', '--min-cluster', '2')
        self.assertIn('     2 or more tracks there: start at fewer than 3 places; finish at fewer than 3 places; either 7\n'
                      '     5 or more tracks there: at fewer than 3 places, so no count is given\n', two)
        self.assertIn('shared by 2 or more outings: 3; by 5 or more outings: fewer than 3; by 10 or more outings: fewer than 3', two)
        self.assertIn('the 3 places shared by 2 or more outings:\n     tracks that start or finish at one of them: 7 of 9', two)
        six = self.exact('--min-cluster', '6')
        self.assertIn('     6 or more tracks there: start 0; finish 0; either 0\n     10 or more tracks there', six)
        self.assertNotIn('5 or more tracks there', six)
        self.assertIn('shared by 2 or more outings: 1; by 6 or more outings: 0; by 10 or more outings: 0', six)
        self.assertIn('the 0 places shared by 6 or more outings:', six)
        six = self.run_audit('--min-cluster', '6')
        self.assertNotIn('5 or more tracks there', six)
        self.assertIn('   places shared by 6 or more outings: fewer than 3, so nothing more is said about them here', six)
        self.assertIn('within 12.5 m', self.run_audit('--radius', '12.5'))
        # the four lines are 500 m long: their finish is "at their own start" only once the radius reaches that far
        self.assertIn('tracks that finish within 499 m of their own start: 5 of 9\n', self.run_audit('--radius', '499'))
        self.assertIn('tracks that finish within 501 m of their own start: 9 of 9\n', self.run_audit('--radius', '501'))
        for bad in (['--radius', '0'], ['--radius', '-5'], ['--radius', 'nan'], ['--radius', 'inf'], ['--min-cluster', '1'],
                    ['--min-cluster', '0'], ['--radius', 'wide'], ['--no-such-flag']):
            self.usage_error(*bad)
        self.assertIn('--radius must be a number of metres above 0', self.usage_error('--radius', '0'))
        self.assertIn('--min-cluster must be 2 or more', self.usage_error('--min-cluster', '1'))

    def test_a_multi_day_trip_is_many_tracks_and_one_outing(self):
        # day N+1 starts where day N ended: three tracks whose ends meet, one outing
        self.days('long-traverse', 'multi-day', [(LAT0 + i * 500 * M_LAT, utc(2026, 7, i + 1, 15)) for i in range(3)])
        self.days('long-journal', 'series', [(LAT0 + 0.3 + i * 0.01, utc(2026, 9, i + 1, 15)) for i in range(2)])
        out = self.exact('--min-cluster', '2')
        self.assertIn('GPX files: 5 = 5 recorded tracks + 0 planned routes;', out)
        self.assertIn('the recorded tracks: 0 single-day reports; 3 days of 1 multi-day trip; 2 days of 1 journal; 2 reports in all', out)
        self.assertIn('(the track itself counted):\n     2 or more tracks there: start 2; finish 2; either 3\n', out)
        self.assertIn("next morning's start):\n     2 or more outings there: start 0; finish 0; either 0\n", out)
        self.assertIn('each within 150 m of the next): 8\n     shared by 2 or more outings: 0; by 5 or more outings: 0;', out)
        self.assertIn('front matter: 7 files (2 index.md, 5 day files);', out)
        self.assertIn('0 of 0 single-day reports, 0 of 3 multi-day days, 0 of 2 journal days', out)
        self.assertNotIn('single-day reports only', out)
        out = self.run_audit('--min-cluster', '2')
        self.assertIn('the recorded tracks: 0 single-day reports; 3 days of 1 multi-day trip; 2 days of 1 journal; 2 reports in all', out)
        self.assertIn('(the track itself counted):\n     2 or more tracks there: at fewer than 3 places, so no count is given\n', out)
        self.assertNotIn('single-day reports only', out)

    def test_start_times_are_local_to_the_trip_zone_and_follow_its_daylight_time(self):
        self.trip('january', track(LAT0, LON0, utc(2026, 1, 10, 18, 20)), date='2026-01-11', timezone='Pacific/Auckland')   # UTC+13
        self.trip('july', track(LAT0 + 0.3, LON0, utc(2026, 7, 10, 18)), date='2026-07-11', timezone='Pacific/Auckland')    # UTC+12
        self.trip('march', track(LAT0 + 0.6, LON0, utc(2026, 3, 10, 22)), date='2026-03-11', timezone='Asia/Tokyo')         # UTC+9
        out = self.exact()
        self.assertIn('by hour (hour: tracks): 06: 1, 07: 2\n', out)
        self.assertIn('   all tracks with times (3): earliest 06:00; 5% before 06:06; a quarter before 06:30; half before 07:00; '
                      'three quarters before 07:10; 95% before 07:18; latest 07:20\n', out)
        # the local dates are a Sunday, a Saturday and a Wednesday; in UTC they would be a Saturday, a Friday and a Tuesday
        self.assertIn('by weekday, Monday to Sunday: 0 0 1 0 0 1 1; on a Saturday or Sunday: 67%', out)
        self.assertIn('read in a guessed zone (no timezone: field): 0; with a timezone: this system does not know (read as UTC): 0', out)
        # three tracks: any point of the spread would be one of them, and so would a weekday
        out = self.run_audit()
        self.assertIn('   all tracks with times (3), to the quarter hour: too few for a spread (fewer than 3 tracks would lie beyond any '
                      'point of it)\n     by hour (hour: tracks; hours are joined until none holds one or two tracks): 06 to 07: 3\n'
                      '     by weekday: not given (fewer than 3 tracks on one side of the weekend)\n', out)
        self.assertIsNone(re.search(r'0[67]:[0-5]\d', out))
        # a fourth and a fifth on weekdays: the weekdays are given together, the two weekend tracks are still not
        self.trip('april', track(LAT0 + 0.9, LON0, utc(2026, 4, 6, 20)), date='2026-04-07', timezone='Asia/Tokyo')     # 05:00 on a Tuesday
        self.trip('may', track(LAT0 + 1.2, LON0, utc(2026, 5, 6, 20)), date='2026-05-07', timezone='Asia/Tokyo')       # 05:00 on a Thursday
        out = self.run_audit()
        self.assertIn('   all tracks with times (5), to the quarter hour: half before 06:00\n', out)
        self.assertIn('     by weekday: not given (fewer than 3 tracks on one side of the weekend)\n', out)
        self.trip('june', track(LAT0 + 1.5, LON0, utc(2026, 6, 5, 20)), date='2026-06-06', timezone='Asia/Tokyo')      # 05:00 on a Saturday
        out = self.run_audit()
        self.assertIn('     by weekday (a day with fewer than 3 tracks is not shown on its own): Monday to Friday 3; Saturday or Sunday 3, '
                      'which is 50%\n', out)
        self.assertIn('     by hour (hour: tracks; hours are joined until none holds one or two tracks): 05: 3, 06 to 07: 3\n', out)

    def test_single_day_reports_are_not_set_apart_when_one_or_two_tracks_make_the_difference(self):
        for i in range(4):
            self.trip('day-%d' % i, track(LAT0 + 0.3 * i, LON0, utc(2026, 6, 1 + i, 5 + i)), date='2026-06-%02d' % (1 + i))
        self.days('long-traverse', 'multi-day', [(LAT0 + 3 + i, utc(2026, 7, 1 + i, 15)) for i in range(2)])
        out = self.run_audit()
        self.assertIn('   all tracks with times (6), to the quarter hour: half before 08:30\n', out)
        self.assertIn('   single-day reports only: all but fewer than 3 of the tracks above, so not shown apart\n', out)
        self.assertEqual(out.count('by hour'), 1)
        self.assertIn('   single-day reports only (4): earliest 06:00;', self.exact())
        # a third day: the two groups are three tracks apart, and each is given
        write(os.path.join(self.trips, 'long-traverse', 'days', '03.md'), helpers.frontmatter.render({'date': '2026-07-03'}, ''))
        write(os.path.join(self.trips, 'long-traverse', 'days', '03.gpx'), track(LAT0 + 5, LON0, utc(2026, 7, 3, 15), step_m=100.0))
        out = self.run_audit()
        self.assertIn('   all tracks with times (7), to the quarter hour: half before 09:00\n', out)
        self.assertIn('   single-day reports only (4), to the quarter hour: too few for a spread', out)
        self.assertEqual(out.count('by hour'), 2)
        # the reports start at 06, 07, 08 and 09, the three days at 16: one line under the other, any narrower bucket would
        # give a single report or a single day away, so both lines have the one bucket
        shared = '     by hour (hour: tracks; hours are joined until none holds one or two tracks, here, on the other line or between the two): '
        self.assertIn(shared + '06 to 16: 7\n', out)
        self.assertIn(shared + '06 to 16: 4\n', out)
        self.assertIn('     by hour (hour: tracks): 06: 1, 07: 1, 08: 1, 09: 1, 16: 3\n', self.exact())
        # one single-day report among them: nothing about when it starts
        for i in range(1, 4):
            os.remove(os.path.join(self.trips, 'day-%d' % i, 'track.gpx'))
        out = self.run_audit()
        self.assertIn("   single-day reports only (1): too few to say when they start without it being one track's own time\n", out)
        self.assertEqual(out.count('by hour'), 1)

    def test_weekdays_of_two_groups_side_by_side_give_neither_away(self):
        # seven single-day reports (four on a Monday, three on a Tuesday) and a three-day trip (Monday, Monday, Tuesday), all
        # starting at 06:00 local: by the day, "6 4" over "4 3" would say two days on the Monday and one on the Tuesday
        for i in range(7):
            when = utc(2026, 6, 1 if i < 4 else 2, 5)
            self.trip('day-%d' % i, track(LAT0 + 0.3 * i, LON0, when), date=when.strftime('%Y-%m-%d'))
        self.days('long-traverse', 'multi-day', [(LAT0 + 3 + i, utc(2026, 6, 1 if i < 2 else 2, 5)) for i in range(3)])
        out = self.run_audit()
        # ten start times: the quarter points have three of them on either side, the 5% and 95% points do not
        self.assertIn('   all tracks with times (10), to the quarter hour: a quarter before 06:00; half before 06:00; three quarters '
                      'before 06:00\n'
                      '     by hour (hour: tracks; hours are joined until none holds one or two tracks, here, on the other line or between '
                      'the two): 06: 10\n'
                      '     by weekday (a day with fewer than 3 tracks is not shown on its own): Monday to Friday 10; Saturday or Sunday 0, '
                      'which is 0%\n', out)
        self.assertIn('   single-day reports only (7), to the quarter hour: half before 06:00\n', out)
        self.assertIn('the two): 06: 7\n     by weekday (a day with fewer than 3 tracks is not shown on its own): Monday to Friday 7; '
                      'Saturday or Sunday 0, which is 0%\n', out)
        exact = self.exact()
        self.assertIn('     by weekday, Monday to Sunday: 6 4 0 0 0 0 0; on a Saturday or Sunday: 0%\n', exact)
        self.assertIn('     by weekday, Monday to Sunday: 4 3 0 0 0 0 0; on a Saturday or Sunday: 0%\n', exact)
        # a fourth day on the Monday: three days on it, and the Tuesday's one day keeps both lines off the single days
        write(os.path.join(self.trips, 'long-traverse', 'days', '04.md'), helpers.frontmatter.render({'date': '2026-06-01'}, ''))
        write(os.path.join(self.trips, 'long-traverse', 'days', '04.gpx'), track(LAT0 + 7, LON0, utc(2026, 6, 1, 5), step_m=100.0))
        self.assertIn('Monday to Friday 11; Saturday or Sunday 0', self.run_audit())
        # two more on the Tuesday: three days on each, and now every day can be shown on both lines
        for n in (5, 6):
            write(os.path.join(self.trips, 'long-traverse', 'days', '%02d.md' % n), helpers.frontmatter.render({'date': '2026-06-02'}, ''))
            write(os.path.join(self.trips, 'long-traverse', 'days', '%02d.gpx' % n), track(LAT0 + 7 + n, LON0, utc(2026, 6, 2, 5), step_m=100.0))
        out = self.run_audit()
        self.assertIn('     by weekday, Monday to Sunday: 7 6 0 0 0 0 0; on a Saturday or Sunday: 0%\n', out)
        self.assertIn('     by weekday, Monday to Sunday: 4 3 0 0 0 0 0; on a Saturday or Sunday: 0%\n', out)

    def test_a_missing_zone_is_guessed_by_the_importers_rule_and_an_unknown_one_is_read_as_utc(self):
        self.trip('no-zone', track(LAT0, LON0, utc(2026, 5, 5, 3)), date='2026-05-05', timezone=None)
        self.trip('odd-zone', track(LAT0 + 0.3, LON0, utc(2026, 5, 6, 9)), date='2026-05-06', timezone='Nowhere/Invented')
        self.trip('blank-zone', track(LAT0 + 0.6, LON0, utc(2026, 5, 7, 4)), date='2026-05-07', timezone='  ')
        with mock.patch.object(pa.tracks, 'guess_tz', return_value='Asia/Tokyo') as guess:      # tracks.guess_tz, not a copy of it
            out = self.exact()
        self.assertEqual(sorted(c.args for c in guess.call_args_list), [(LAT0, LON0), (round(LAT0 + 0.6, 6), LON0)])
        self.assertIn('by hour (hour: tracks): 09: 1, 12: 1, 13: 1\n', out)                    # 03:00 and 04:00 UTC in Tokyo; 09:00 UTC
        self.assertIn('read in a guessed zone (no timezone: field): 2; with a timezone: this system does not know (read as UTC): 1', out)
        self.assertIn('by hour (hour: tracks): 03: 1, 04: 1, 09: 1\n', self.exact())            # at 10 N 10 E the real rule says UTC

    def test_what_a_shared_place_adds_up_to(self):
        # X: three loops from one point in two calendar years, two activities, starting within an hour of each other
        for i, (when, act) in enumerate(((utc(2025, 6, 3, 5), 'hike'), (utc(2026, 6, 9, 5, 30), 'mtb'), (utc(2026, 6, 16, 6), 'hike'))):
            self.trip('x-%d' % i, track(LAT0, LON0, when, loop=True), date=when.strftime('%Y-%m-%d'), activity=act)
        # Y: three loops from one point, two of them on the same date, five hours apart
        for i, when in enumerate((utc(2026, 3, 3, 5), utc(2026, 3, 3, 10), utc(2026, 3, 10, 7))):
            self.trip('y-%d' % i, track(LAT0 + 0.2, LON0, when, loop=True), date=when.strftime('%Y-%m-%d'))
        # Z: three loops that start 120 m apart in a row, so the chain is 240 m from end to end; three hours apart
        for i, when in enumerate((utc(2026, 4, 1, 9), utc(2026, 4, 2, 11), utc(2026, 4, 3, 12))):
            self.trip('z-%d' % i, track(LAT0 + 0.4 + i * 120 * M_LAT, LON0, when, loop=True), date=when.strftime('%Y-%m-%d'))
        self.trip('w-finish-only', track(LAT0 + 0.6, LON0, utc(2026, 4, 9, 9), step_m=100.0), date='2026-04-09')
        out = self.run_audit()
        self.assertIn('each within 150 m of the next): 5\n     shared by 2 or more outings: 3; by 3 or more outings: 3; by 5 or more '
                      'outings: fewer than 3; by 10 or more outings: fewer than 3\n', out)
        self.assertIn('   the 3 places shared by 3 or more outings:\n     tracks that start or finish at one of them: 9 of 10\n', out)
        # three places are enough to be described together, but each of these counts is about one or two of them
        self.assertIn('every start there on a different date: fewer than 3; starts in more than one calendar year: fewer than 3; more '
                      'than one activity: fewer than 3\n', out)
        self.assertIn('start times all within 90 minutes: fewer than 3; spread over 4 hours or more: fewer than 3; wider than 150 m '
                      'from end to end (a chain can be): fewer than 3\n', out)
        listed = self.run_audit('--list', isatty=True)
        self.assertIn('every start there on a different date: 2; starts in more than one calendar year: 1; more than one activity: 1', listed)
        self.assertIn('start times all within 90 minutes: 1; spread over 4 hours or more: 1; wider than 150 m from end to end (a chain '
                      'can be): 1', listed)
        self.assertIn('   place 1: 3 outings, 3 tracks, 0 m across; 3 starts on 3 dates in 2 calendar years; start times 06:00 to 07:00 '
                      '(middle half 06:15 to 06:45); hike 2, mtb 1\n      near 10.000, 10.000: x-0, x-1, x-2\n', listed)
        self.assertIn('   place 2: 3 outings, 3 tracks, 0 m across; 3 starts on 2 dates in 1 calendar year; start times 06:00 to 11:00 '
                      '(middle half 07:00 to 09:30); hike 3\n      near 10.200, 10.000: y-0, y-1, y-2\n', listed)
        self.assertIn('   place 3: 3 outings, 3 tracks, 240 m across; 3 starts on 3 dates in 1 calendar year; start times 10:00 to 13:00 '
                      '(middle half 11:00 to 12:30); hike 3\n      near 10.401, 10.000: z-0, z-1, z-2\n', listed)
        self.assertNotIn('place 4', listed)

    def test_starts_and_finishes_are_counted_apart(self):
        # three lines fan out from one start to finishes 500 m, 1 km and 1.5 km away; a fourth line ends on that start
        for i in range(3):
            self.trip('fan-%d' % i, track(LAT0, LON0, utc(2026, 6, i + 1, 5), step_m=100.0 * (i + 1)), date='2026-06-0%d' % (i + 1))
        self.trip('inbound', track(LAT0 - 500 * M_LAT, LON0, utc(2026, 6, 9, 5), step_m=100.0), date='2026-06-09')
        out = self.exact()
        self.assertIn('tracks that finish within 150 m of their own start: 0 of 4\n', out)
        self.assertIn('(the track itself counted):\n     3 or more tracks there: start 3; finish 1; either 4\n', out)
        self.assertIn('each within 150 m of the next): 5\n     shared by 2 or more outings: 1; by 3 or more outings: 1;', out)
        out = self.run_audit()                           # one place: "start 3; finish 1" would be how it is used
        self.assertIn('tracks that finish within 150 m of their own start: 0 of 4\n', out)
        self.assertIn('(the track itself counted):\n     3 or more tracks there: at fewer than 3 places, so no count is given\n', out)
        # a place where one track starts and another only finishes has no pattern of start dates or hours to report
        self.trip('loop-here', track(LAT0 + 0.3, LON0, utc(2026, 6, 10, 5), loop=True), date='2026-06-10')
        self.trip('ends-here', track(LAT0 + 0.3 - 500 * M_LAT, LON0, utc(2026, 6, 11, 9), step_m=100.0), date='2026-06-11')
        two = self.run_audit('--min-cluster', '2', '--list', isatty=True)
        self.assertIn('   the 2 places shared by 2 or more outings:\n     tracks that start or finish at one of them: 6 of 6\n'
                      '     every start there on a different date: 1; starts in more than one calendar year: 0; more than one activity: 0\n'
                      '     start times all within 90 minutes: 1; spread', two)
        self.assertIn('   place 2: 2 outings, 2 tracks, 0 m across; 1 start on 1 date in 1 calendar year; start times 06:00 to 06:00 '
                      '(middle half 06:00 to 06:00); hike 2\n      near 10.300, 10.000: ends-here, loop-here\n', two)

    def test_rendered_meta_counts_only_files_with_both_ends(self):
        self.trip('one', track(LAT0, LON0, utc(2026, 6, 1, 5)), date='2026-06-01')
        for slug, text in (('one', '{"start": [1, 2], "end": [3, 4], "bbox": [1, 2, 3, 4]}'), ('two', '{"start": [1, 2]}'),
                           ('three', '{"end": [3, 4]}'), ('four', 'not json'), ('five', '[]'), ('six', '{"start": null, "end": null}')):
            write(os.path.join(self.rendered, 'trips', slug, 'meta.json'), text)
        os.makedirs(os.path.join(self.rendered, 'trips', 'seven'))
        write(os.path.join(self.rendered, 'site', 'meta.json'), '{"start": [1, 2], "end": [3, 4]}')
        self.assertIn('   rendered/trips/*/meta.json: 6 files; with the start and the end written out as coordinates: 1\n', self.run_audit())

    def test_a_name_from_the_content_cannot_reorder_the_listing(self):
        for i, slug in enumerate(('plain-a', 'odd\u202ename', 'plain-b')):
            self.trip(slug, track(LAT0, LON0, utc(2026, 6, i + 1, 5), loop=True), date='2026-06-0%d' % (i + 1))
        out = self.run_audit('--list', isatty=True)
        self.assertIn('      near 10.000, 10.000: odd\\u202ename, plain-a, plain-b\n', out)
        self.assertNotIn('\u202e', out)

    def test_a_reader_that_stops_early_is_not_an_error(self):
        self.build()

        class Closed(io.StringIO):
            def write(self, text):
                raise BrokenPipeError()
        self.assertEqual(pa.main(['--content', self.content, '--rendered', self.rendered], out=Closed(), isatty=False), 0)

    def test_what_a_file_carries_besides_its_line(self):
        pts = points(LAT0, LON0, utc(2026, 7, 1, 5))
        loaded = gx.gpx('<metadata><name>A file name</name><link href="https://example.test/r"><text>r</text></link></metadata>',
                        gx.wpt(LAT0, LON0, 'A named waypoint'),
                        '<trk><name>Synthetic line</name><desc>Words about it</desc><link href="https://example.test/t"><text>t</text></link>'
                        '<trkseg><trkpt lat="%s" lon="%s"><ele>1</ele><time>%s</time><name>pt</name><sat>7</sat>'
                        '<extensions><hr>120</hr></extensions></trkpt>%s</trkseg></trk>'
                        % (LAT0, LON0, pts[0][3], ''.join(gx.pt_xml('trkpt', p) for p in pts[1:])),
                        '<!-- a comment -->')
        self.trip('loaded', loaded, date='2026-07-01')
        self.trip('partial', gx.gpx(gx.trk([[(LAT0 + 0.3, LON0, 5, None)] + points(LAT0 + 0.3, LON0, utc(2026, 7, 2, 5), eles=False)])),
                  date='2026-07-02')
        folder = self.trip('own', '', date='2026-07-03')
        own = [(p[0] + 0.6, p[1], 100.0 + i, utc(2026, 7, 3, 5, i).timestamp()) for i, p in enumerate(pts)]
        pa.tracks.write_gpx(os.path.join(folder, 'track.gpx'), own, 'Own', kind='hike')         # what add_trip.py writes
        folder = self.trip('odd-creator', gx.gpx(gx.trk([points(LAT0 + 0.9, LON0, utc(2026, 7, 4, 5))]),
                                                 head=gx.HEAD.replace('synthetic fixture', 'pat‮account')), date='2026-07-04')
        self.trip('route-only', gx.gpx(gx.rte(points(LAT0 + 1.2, LON0, utc(2026, 7, 5, 5), n=4, times=False), 'A drawn line')), kind='planned')
        out = self.run_audit()
        self.assertIn('   recorded tracks (4 files, 25 points):\n     a time on every point: 3; on some: 1; on none: 0\n'
                      '     an elevation on every point: 3; on some: 1; on none: 0\n'
                      "     creator text: this site's own in 1; another in 3; none in 0\n", out)
        self.assertIn('     also in the files: a file name or time in 2; track or route names in 2; descriptions or type text in 2; '
                      'file information beyond a name and a time in 1; device or app extensions in 1; links in 1; waypoints in 1; '
                      'named points in 1; GPS quality fields in 1; XML comments in 1\n'
                      '     in no file: other attributes, extra namespaces, unknown elements, loose text, an unusual version text\n', out)
        # a route (rte) is read as the planned line; one file's point total is that file's own, so only the listing has it
        self.assertIn("   planned routes (1 file; too few for a point total or a spacing that is not one file's own):\n"
                      '     a time on every point: 0; on some: 0; on none: 1\n', out)
        self.assertNotIn('4 points', out)
        # four recorded files: even their middle has only two files on either side
        self.assertIn("     typical gap between points: not given for so few files (it would be one file's own, or close to it)\n", out)
        self.assertEqual(out.count('typical gap'), 1)
        for text in ('A named waypoint', 'A file name', 'Words about it', 'pat', 'account', 'example.test', pa.SITE_CREATOR):
            self.assertNotIn(text, out)
        listed = self.run_audit('--list', isatty=True)
        self.assertIn('   planned routes (1 file, 4 points):\n', listed)
        self.assertEqual(listed.count('typical gap between points (each file\'s median; in brackets the middle 80% of files): '), 2)
        self.assertIn('        another creator text: "pat\\u202eaccount" in 1\n', listed)       # escaped: it cannot reorder the line
        self.assertIn('        another creator text: "synthetic fixture" in 2\n', listed)
        self.assertNotIn('‮', listed)

    def test_the_default_report_names_nothing(self):
        self.build()
        self.days('long-traverse', 'multi-day', [(LAT0 + 0.9 + i * 500 * M_LAT, utc(2026, 7, i + 1, 15)) for i in range(2)], party=NAME)
        write(os.path.join(self.trips, 'alpha-loop-0', 'photos', '01.webp'), TAGGED)
        write(os.path.join(self.rendered, 'trips', 'alpha-loop-0', 'meta.json'), '{"start": [%s, %s], "end": [%s, %s]}' % ((LAT0, LON0) * 2))
        site = os.path.join(self.tmp, 'site')
        write(os.path.join(site, 'index.html'), '<p>%.5f, %.5f</p>' % (LAT0 + 0.12345, LON0 + 0.54321))
        with mock.patch.object(pa.getpass, 'getpass', return_value='%.6f, %.6f' % (LAT0 + 0.000123, LON0)):
            out = self.run_audit('--near', '--site', site)
        for slug in ('alpha-loop', 'pair-a', 'pair-b', 'loner', 'hidden-draft', 'someday-goal', 'long-traverse'):
            self.assertNotIn(slug, out)
        self.assertIsNone(COORDINATE.search(out), 'a coordinate-like number in the default report')
        for text in (NAME, 'Sam', str(STRAVA_ID), self.tmp, os.path.basename(self.tmp), ZONE, 'synthetic fixture', 'Synthetic line',
                     'AUTHOR ONLY', pa.BANNER):
            self.assertNotIn(text, out)
        self.assertIn('7. NEAR THE POINT YOU TYPED', out)
        self.assertIn('8. THE BUILT SITE in the folder given', out)

    def test_list_is_for_a_terminal_bannered_and_rounded(self):
        self.build()
        err = self.usage_error('--list', isatty=False)
        self.assertIn('--list names trips and coordinates, so it prints to a terminal only', err)
        self.assertNotIn('alpha-loop', err)
        out = self.run_audit('--list', isatty=True)
        lines = out.rstrip('\n').split('\n')
        self.assertEqual(lines[0], pa.BANNER)
        self.assertEqual(lines[-1], pa.BANNER)
        self.assertIn('AUTHOR ONLY', pa.BANNER)
        self.assertIn('Do not paste', pa.BANNER)
        self.assertNotIn('counts only', out)
        self.assertIn('   AUTHOR ONLY: each shared place, most outings first (position rounded to 3 decimals, about 100 m)\n'
                      '   place 1: 5 outings, 5 tracks, 40 m across; 5 starts on 5 dates in 1 calendar year; start times 06:00 to 15:00 '
                      '(middle half 07:00 to 13:00); hike 5\n'
                      '      near 10.000, 10.000: alpha-loop-0, alpha-loop-1, alpha-loop-2, alpha-loop-3, alpha-loop-4\n', out)
        self.assertNotIn('place 2', out)                                         # nothing else is shared by three outings
        self.assertIsNone(re.search(r'\d\.\d{4,}', out), 'more than three decimals in --list')
        self.assertNotIn(self.tmp, out)
        anyway = self.run_audit('--list', '--list-anyway', isatty=False)
        self.assertEqual(anyway, out)
        self.assertNotIn('alpha-loop', self.run_audit('--list-anyway', isatty=False))   # on its own it lists nothing
        two = self.run_audit('--list', '--min-cluster', '2', '--radius', '250', isatty=True)
        # the pair's two starts are one place and its two finishes, 500 m further on, another
        self.assertIn('   place 2: 2 outings, 2 tracks, 200 m across; 2 starts on 2 dates in 1 calendar year; start times 16:00 to 16:00 '
                      '(middle half 16:00 to 16:00); hike 2\n      near 10.201, 10.000: pair-a, pair-b\n', two)
        self.assertIn('   place 3: 2 outings, 2 tracks, 200 m across; no track starts here, some finish; hike 2\n'
                      '      near 10.205, 10.000: pair-a, pair-b\n', two)
        self.assertNotIn('place 4', two)

    def test_main_asks_the_stream_whether_it_is_a_terminal(self):
        self.build()

        class Stream(io.StringIO):
            tty = False

            def isatty(self):
                return self.tty
        args = ['--content', self.content, '--rendered', self.rendered, '--list']
        out = Stream()
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stderr(io.StringIO()):
            pa.main(args, out=out)
        self.assertEqual((cm.exception.code, out.getvalue()), (2, ''))
        out.tty = True
        self.assertEqual(pa.main(args, out=out), 0)
        self.assertTrue(out.getvalue().startswith(pa.BANNER + '\n'))

    def test_day_tracks_are_listed_with_their_day(self):
        self.days('long-traverse', 'multi-day', [(LAT0 + i * 500 * M_LAT, utc(2026, 7, i + 1, 15)) for i in range(2)])
        self.trip('day-hike', track(LAT0 + 500 * M_LAT, LON0, utc(2026, 8, 1, 6), loop=True), date='2026-08-01')
        out = self.run_audit('--list', '--min-cluster', '2', isatty=True)
        self.assertIn('   place 1: 2 outings, 3 tracks, 0 m across; 2 starts on 2 dates in 1 calendar year; start times 07:00 to 16:00 '
                      '(middle half 09:15 to 13:45); hike 3\n'
                      '      near 10.004, 10.000: day-hike, long-traverse#01, long-traverse#02\n', out)

    def test_an_unreadable_file_is_counted_and_named_only_for_the_author(self):
        self.build()
        self.trip('broken-xml', '<gpx><trk><trkseg><trkpt lat="x"', date='2026-08-09')
        self.trip('hostile-doctype', '<?xml version="1.0"?><!DOCTYPE gpx [<!ENTITY a "b">]><gpx/>', date='2026-08-10')
        self.trip('empty-file', '', date='2026-08-11')
        self.trip('no-points', gx.gpx(gx.trk([[]], 'Nothing in here'), gx.wpt(LAT0, LON0, 'Only a waypoint')), date='2026-08-12')
        helpers.make_trip(self.trips, 'no-gpx', date='2026-08-13')
        write(os.path.join(self.trips, 'bad-front-matter', 'index.md'), '---\ntitle: Never closed\n')
        os.makedirs(os.path.join(self.trips, 'not-a-trip'))
        out = self.run_audit()
        self.assertIn('GPX files: 14 = 9 recorded tracks + 1 planned route; unreadable: 3; with no track points: 1\n', out)
        self.assertIn('trips with no GPX at all: 1; trip folders that could not be read: 1\n', out)
        self.assertIn('front matter: 15 files (15 index.md, 0 day files)', out)
        for name in ('broken-xml', 'hostile-doctype', 'empty-file', 'no-points', 'bad-front-matter', 'no-gpx', 'DOCTYPE', 'well-formed',
                     'ContentError', 'is not closed', 'Only a waypoint'):
            self.assertNotIn(name, out)
        listed = self.run_audit('--list', isatty=True)
        self.assertIn('      unreadable GPX: broken-xml: "track.gpx: not well-formed XML', listed)
        self.assertIn('      unreadable GPX: hostile-doctype: "track.gpx: DOCTYPE, ENTITY and other <! declarations are not accepted"\n', listed)
        self.assertIn('      unreadable GPX: empty-file: ', listed)
        self.assertIn('      no track points: no-points\n', listed)
        self.assertIn('      could not be read: bad-front-matter: "ContentError: content/trips/bad-front-matter/index.md: front matter: ', listed)

    def test_copies_the_build_leaves_out_change_no_count(self):
        self.build()
        self.days('long-traverse', 'multi-day', [(LAT0 + 0.9 + i * 500 * M_LAT, utc(2026, 7, i + 1, 15)) for i in range(2)])
        write(os.path.join(self.trips, 'alpha-loop-0', 'photos', '01.webp'), PLAIN)
        write(os.path.join(self.rendered, 'trips', 'alpha-loop-0', 'meta.json'), '{"start": [1, 2], "end": [3, 4]}')
        site = os.path.join(self.tmp, 'site')
        write(os.path.join(site, 'index.html'), '<p>fine</p>')
        write(os.path.join(site, 'trips', 'alpha-loop-0', 'photos', '01.webp'), PLAIN)
        before = self.run_audit('--site', site)
        self.assertIn('   1 file: 1 WebP\n   with EXIF: 0;', before)
        self.assertIn('rendered/trips/*/meta.json: 1 file; with the start and the end written out as coordinates: 1\n', before)
        self.assertIn('GPX files: 12 = 11 recorded tracks + 1 planned route;', before)
        self.assertIn('   text files (1: html, svg, json, xml, js, css, txt):\n', before)
        self.assertIn('   not read: text or image files whose name, or a folder\'s above them, looks like an iCloud conflict copy (a '
                      'trip\'s photos are read whatever their name): 0; ', before)
        # what iCloud leaves behind where the build does not publish it: a copy of a trip folder (the build refuses a folder
        # with such a name), of rendered files, and of pages and map images in a site folder
        copy = os.path.join(self.trips, 'alpha-loop-0 2')
        write(os.path.join(copy, 'index.md'), helpers.frontmatter.render({'title': 'Copy', 'activity': 'hike', 'strava_id': 5, 'party': NAME}, ''))
        write(os.path.join(copy, 'track.gpx'), track(LAT0, LON0, utc(2026, 7, 30, 5), loop=True))
        write(os.path.join(copy, 'photos', '01.webp'), TAGGED)
        write(os.path.join(self.rendered, 'trips', 'alpha-loop-0 2', 'meta.json'), '{"start": [1, 2], "end": [3, 4]}')
        write(os.path.join(self.rendered, 'trips', 'alpha-loop-0', 'meta 3.json'), '{"start": [1, 2], "end": [3, 4]}')
        write(os.path.join(site, 'index 2.html'), '<p>%.5f, %.5f</p>' % (LAT0 + 0.12345, LON0 + 0.54321))
        write(os.path.join(site, 'trips 3', 'index.html'), '<p>%.5f, %.5f</p>' % (LAT0 + 0.12345, LON0 + 0.54321))
        write(os.path.join(site, 'trips', 'alpha-loop-0 2', 'photos', '01.webp'), TAGGED)
        write(os.path.join(site, 'trips', 'alpha-loop-0', 'map', 'map-wide 4.webp'), TAGGED)
        write(os.path.join(site, 'assets', 'maps', 'region-x-desktop.base 2.svg'), '<svg>%.5f, %.5f</svg>' % (LAT0, LON0))
        write(os.path.join(site, 'assets', 'unknown 2.bin'), b'x')                    # nor a text or an image: counted as that
        after = self.run_audit('--site', site)
        self.assertIn('   not read: text or image files whose name, or a folder\'s above them, looks like an iCloud conflict copy (a '
                      'trip\'s photos are read whatever their name): 5; files that are neither GPX, text nor image: 1\n', after)
        self.assertEqual(after.replace('whatever their name): 5; files that are neither GPX, text nor image: 1',
                                       'whatever their name): 0; files that are neither GPX, text nor image: 0'), before)

    def test_a_photo_or_a_day_named_like_a_copy_is_counted_because_the_build_publishes_it(self):
        """tools/build.py copies every file of a trip's photos/ folder and content.load_trip reads every days/*.md, whatever
        the name. The first version of the audit skipped a name that looks like an iCloud copy, so a photo with EXIF, or
        a day's track, could be on the site while the report showed a zero."""
        self.build()
        self.days('long-traverse', 'multi-day', [(LAT0 + 0.9 + i * 500 * M_LAT, utc(2026, 7, i + 1, 15)) for i in range(2)])
        photos = os.path.join(self.trips, 'alpha-loop-0', 'photos')
        write(os.path.join(photos, '01.webp'), PLAIN)
        site = os.path.join(self.tmp, 'site')
        write(os.path.join(site, 'index.html'), '<p>fine</p>')
        write(os.path.join(site, 'trips', 'alpha-loop-0', 'photos', '01.webp'), PLAIN)
        before = self.run_audit('--site', site)
        self.assertIn('   1 file: 1 WebP\n   with EXIF: 0;', before)
        self.assertIn('     1 file: 1 WebP\n     with EXIF: 0;', before)
        self.assertIn('GPX files: 12 = 11 recorded tracks + 1 planned route;', before)
        self.assertIn('2 days of 1 multi-day trip;', before)
        self.assertIn('front matter: 13 files (11 index.md, 2 day files); strava_id in 1; timezone in 11; start_time in 2;', before)
        self.assertIn('equal to the source byte for byte: 0; different: 0;', before)
        jpeg = b'\xff\xd8' + Images.seg(0xE1, b'Exif\0\0II') + Images.seg(0xDA, b'')
        for name, data in (('01 2.webp', TAGGED), ('01.sm 3.webp', TAGGED), ('IMG_0001 2.jpg', jpeg), ('.DS_Store', b'x')):
            write(os.path.join(photos, name), data)                                   # glob('photos/*') leaves a dot file out
            write(os.path.join(site, 'trips', 'alpha-loop-0', 'photos', name), data)
        days = os.path.join(self.trips, 'long-traverse', 'days')
        write(os.path.join(days, '01 2.md'), helpers.frontmatter.render({'day': '9', 'date': '2026-07-09', 'start_time': '05:00'}, ''))
        write(os.path.join(days, '01 2.gpx'), track(LAT0, LON0, utc(2026, 7, 9, 5), loop=True))      # from the loops' own spot
        with open(os.path.join(days, '01 2.gpx'), 'rb') as fh:
            write(os.path.join(site, 'trips', 'long-traverse', 'gpx', 'long-traverse-day-01 2.gpx'), fh.read())
        after = self.run_audit('--site', site)
        self.assertIn('   4 files: 1 JPEG, 3 WebP\n   with EXIF: 3;', after)
        self.assertIn('     4 files: 1 JPEG, 3 WebP\n     with EXIF: 3;', after)
        self.assertIn('   not read: text or image files whose name, or a folder\'s above them, looks like an iCloud conflict copy (a '
                      'trip\'s photos are read whatever their name): 0; ', after)
        self.assertIn('GPX files: 13 = 12 recorded tracks + 1 planned route;', after)
        self.assertIn('3 days of 1 multi-day trip;', after)
        self.assertIn('front matter: 14 files (11 index.md, 3 day files); strava_id in 1; timezone in 11; start_time in 3;', after)
        self.assertIn('equal to the source byte for byte: 1; different: 0;', after)
        self.assertIn('   place 1: 6 outings, 6 tracks, 40 m across; 6 starts on 6 dates', self.exact())
        self.assertIn('alpha-loop-3, alpha-loop-4, long-traverse#01 2\n', self.exact())

    def test_it_only_reads_and_never_goes_online(self):
        self.build()
        self.days('long-traverse', 'multi-day', [(LAT0 + 0.9 + i * 500 * M_LAT, utc(2026, 7, i + 1, 15)) for i in range(2)])
        write(os.path.join(self.trips, 'alpha-loop-0', 'photos', '01.webp'), TAGGED)
        write(os.path.join(self.rendered, 'trips', 'alpha-loop-0', 'meta.json'), '{"slug": "alpha-loop-0", "start": [1, 2], "end": [3, 4]}')
        site = os.path.join(self.tmp, 'site')
        write(os.path.join(site, 'index.html'), '<p>x</p>')
        write(os.path.join(site, 'trips', 'alpha-loop-0', 'alpha-loop-0.gpx'), 'not the same bytes')
        before, cwd = self.snapshot(), sorted(os.listdir(os.getcwd()))
        real_open = open

        def read_only_open(file, mode='r', *a, **k):
            if set(mode) & set('wax+'):
                raise AssertionError('the audit opened %r for writing (mode %r)' % (file, mode))
            return real_open(file, mode, *a, **k)

        def refuse(*a, **k):
            raise AssertionError('the audit tried to change something or go online: %r' % (a,))
        patches = [mock.patch('builtins.open', read_only_open), mock.patch.object(socket, 'socket', refuse),
                   mock.patch.object(pa.getpass, 'getpass', return_value='%s %s' % (LAT0, LON0))]
        patches += [mock.patch.object(os, name, refuse) for name in ('makedirs', 'mkdir', 'remove', 'unlink', 'rename', 'replace',
                                                                    'rmdir', 'symlink', 'link', 'utime', 'chmod', 'truncate')]
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            out = self.run_audit('--site', site, '--near', '--list', isatty=True)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(sorted(os.listdir(os.getcwd())), cwd)
        self.assertIn('meta.json: 1 file; with the start and the end written out as coordinates: 1', out)
        self.assertIn('   1 file: 1 WebP\n   with EXIF: 1; with XMP: 0;', out)
        self.assertIn('GPX copies: equal to the source byte for byte: 0; different: 1;', out)
        with open(pa.__file__, encoding='utf-8') as fh:
            src = fh.read()
        for banned in ('subprocess', 'urllib', 'http.client', 'socket', 'shutil', 'tempfile', 'os.remove', 'os.rename', 'os.replace',
                       'os.makedirs', 'os.mkdir', 'os.unlink', 'os.symlink', '.write_text', '.write_bytes', 'os.system', 'os.popen',
                       'webbrowser', 'smtplib', 'ftplib', 'requests'):
            self.assertNotIn(banned, src)
        opens = re.findall(r'\bopen\(([^)\n]*)\)', src)
        self.assertGreaterEqual(len(opens), 4)
        for args in opens:                                                        # every open() in the tool is a read
            self.assertRegex(args, r"^\w+, (?:'rb'|encoding='utf-8'(?:, errors='replace')?)$")
        self.assertEqual(re.findall(r'\.write\(', src), ['.write('])              # the one write is to the output stream

    def test_near_counts_tracks_around_a_typed_point_and_never_repeats_it(self):
        self.build()
        typed = '%.6f, %.6f' % (LAT0 + 0.2 + 250 * M_LAT, LON0)                  # 250 m up pair-a's line; pair-b starts 50 m from it
        with mock.patch.object(pa.getpass, 'getpass', return_value=typed) as ask:
            out = self.run_audit('--near')
        ask.assert_called_once_with('latitude, longitude (not shown as you type): ')
        self.assertIn('7. NEAR THE POINT YOU TYPED (within 150 m; the point is not printed or stored)\n'
                      '   tracks that start or finish there: 1; tracks that pass within 150 m of it at any point: 2 (of 9)\n', out)
        self.assertNotIn('8. ', out)
        for text in (typed, typed.split(',')[0], typed.split('.')[1][:4], 'pair-a', 'pair-b', 'AUTHOR ONLY'):
            self.assertNotIn(text, out)
        at_finish = '%.6f,%.6f' % (LAT0 + 0.2 + 500 * M_LAT, LON0)               # where pair-a ends; pair-b's line passes through
        with mock.patch.object(pa.getpass, 'getpass', return_value=at_finish):
            self.assertIn('   tracks that start or finish there: 1; tracks that pass within 100 m of it at any point: 2 (of 9)\n',
                          self.run_audit('--near', '--radius', '100'))
        with mock.patch.object(pa.getpass, 'getpass', return_value=typed.replace(',', ' ')):   # a space works as the comma does
            listed = self.run_audit('--near', '--list', '--radius', '40', isatty=True)
        self.assertIn('   tracks that start or finish there: 0; tracks that pass within 40 m of it at any point: 0 (of 9)\n', listed)
        with mock.patch.object(pa.getpass, 'getpass', return_value=' %s , %s ' % (LAT0, LON0)):   # on the shared spot; planned route left out
            listed = self.run_audit('--near', '--list', isatty=True)
        self.assertIn('   tracks that start or finish there: 5; tracks that pass within 150 m of it at any point: 5 (of 9)\n'
                      '      AUTHOR ONLY: alpha-loop-0, alpha-loop-1, alpha-loop-2, alpha-loop-3, alpha-loop-4\n', listed)
        self.assertNotIn('someday-goal', listed.split('NEAR THE POINT')[1])
        for bad in ('somewhere secret', '', '95, 10', '10, 190', '10', '10, 10, 10', '10N 10E', 'nan, 10'):
            with mock.patch.object(pa.getpass, 'getpass', return_value=bad):
                err = self.usage_error('--near')
            self.assertIn('--near needs "latitude, longitude" in decimal degrees', err)
            if bad:
                self.assertNotIn(bad, err)
        with mock.patch.object(pa.getpass, 'getpass', side_effect=AssertionError('asked without --near')):
            self.assertNotIn('NEAR THE POINT', self.run_audit())

    def test_a_built_site_is_compared_with_its_sources(self):
        self.build()
        self.days('long-traverse', 'multi-day', [(LAT0 + 0.9 + i * 500 * M_LAT, utc(2026, 7, i + 1, 15)) for i in range(2)])
        write(os.path.join(self.trips, 'long-traverse', 'track.gpx'), track(LAT0 + 0.9, LON0, utc(2026, 7, 1, 15)))
        site = os.path.join(self.tmp, 'site')

        def source(slug, name='track.gpx'):
            with open(os.path.join(self.trips, slug, name), 'rb') as fh:
                return fh.read()
        write(os.path.join(site, 'trips', 'alpha-loop-0', 'alpha-loop-0.gpx'), source('alpha-loop-0'))
        write(os.path.join(site, 'trips', 'alpha-loop-1', 'alpha-loop-1.gpx'), source('alpha-loop-1') + b'\n')
        os.makedirs(os.path.join(site, 'trips', 'alpha-loop-2'))
        os.symlink(os.path.join(self.trips, 'alpha-loop-2', 'track.gpx'), os.path.join(site, 'trips', 'alpha-loop-2', 'alpha-loop-2.gpx'))
        write(os.path.join(site, 'trips', 'long-traverse', 'gpx', 'long-traverse-day-01.gpx'), source('long-traverse', 'days/01.gpx'))
        # the combined download sits at the trip's own address: it is not a copy of track.gpx and is not compared with it
        write(os.path.join(site, 'trips', 'long-traverse', 'long-traverse.gpx'), b'<gpx>both days</gpx>')
        # two long decimals side by side, at a spot where no track of the tree starts or ends: look-alikes
        write(os.path.join(site, 'index.html'), '<p data-ll="%.5f, %.5f">x</p>' % (LAT0 + 0.12345, LON0 + 0.54321))
        write(os.path.join(site, 'assets', 'site.js'), 'var a = [%.4f,-%.4f];' % (LAT0 + 0.1234, LON0 + 0.4321))
        write(os.path.join(site, 'about', 'index.html'), '<p>12.5, 20.25 and 3.14159 are not a pair; local time is %s</p>' % ZONE)
        write(os.path.join(site, 'trips', 'search.json'), '[{"s": "x", "id": %d}]' % STRAVA_ID)
        write(os.path.join(site, 'feed.xml'), '<rss><item>%d0</item></rss>' % STRAVA_ID)          # the id with a digit more is another number
        write(os.path.join(site, 'assets', 'site.css'), 'a{color:red}')
        write(os.path.join(site, 'robots.txt'), 'User-agent: *')
        write(os.path.join(site, 'assets', 'favicon.svg'), '<svg/>')
        # where pair-a ends, in three of the forms the first version of this check could not see; then where the draft starts
        end = points(LAT0 + 0.2, LON0, utc(2026, 8, 1, 15), step_m=100.0)[-1]
        write(os.path.join(site, 'map', 'index.html'), '<a data-lat="%.5f" data-lon="%.5f">x</a>' % (end[0], end[1]))
        write(os.path.join(site, 'map', 'line.json'), '{"coordinates":[[%.6f,%.6f]]}' % (end[1], end[0]))
        write(os.path.join(site, 'ski', 'index.html'), '<p>%.3f N then %.3f E</p>' % (end[0], end[1]))
        write(os.path.join(site, 'hike', 'index.html'), '<p>%.4f %.4f</p>' % (LAT0 + 0.7, LON0))  # a draft's track is looked for too
        write(os.path.join(site, 'half', 'index.html'), '<p>%.5f and no longitude</p>' % end[0])
        # the proportions of a photo row, as core.py writes them
        write(os.path.join(site, 'trips', 'alpha-loop-0', 'index.html'), '<div class="jrow" style="--n:2;--sum:2.8333;--ar:1.5000"></div>')
        write(os.path.join(site, 'trips', 'alpha-loop-0', 'photos', '01.webp'), PLAIN)
        write(os.path.join(site, 'trips', 'alpha-loop-0', 'photos', '02.webp'), TAGGED)
        write(os.path.join(site, '.nojekyll'), '')
        write(os.path.join(site, 'CNAME'), 'example.test')
        out = self.run_audit('--site', site)
        self.assertIn('GPX files: 13 = 12 recorded tracks + 1 planned route;', out)
        self.assertIn('9 single-day reports; 2 days of 1 multi-day trip; 0 days of 0 journals; 1 in another arrangement; 10 reports in all', out)
        self.assertIn(
            '7. THE BUILT SITE in the folder given\n'
            '   GPX copies: equal to the source byte for byte: 2; different: 1; a symlink to the source (a --link build: nothing '
            'to compare): 1; not in the folder: 8 (in a draft: 1)\n'
            '   text files (14: html, svg, json, xml, js, css, txt):\n'
            # map/index.html, map/line.json, ski/index.html and hike/index.html; 13 GPX files, two ends each
            '     holding the latitude and the longitude of the first or the last point of one GPX file of content/trips, each '
            'written with 3 or more decimals (rounded or cut short, in either order, whatever stands between them; 26 points looked '
            'for): 4\n'
            # index.html, site.js, map/index.html, map/line.json and hike/index.html; then the page of photo rows
            '     holding two numbers of 4 or more decimals, no more than 40 characters apart, that could be a latitude and a '
            'longitude (look-alikes, not known positions): 5; the same, but only as values of CSS custom properties (--name: number, '
            'which is how the site writes the proportions of a photo row): 1\n'
            '     with a strava_id from the front matter: 1; with a timezone name from the front matter: 1\n'
            '     not looked for: a position in another notation (degrees and minutes, whole numbers, an encoded line) or with fewer '
            'decimals, and what an image shows\n'
            '   not read: text or image files whose name, or a folder\'s above them, looks like an iCloud conflict copy (a trip\'s '
            'photos are read whatever their name): 0; files that are neither GPX, text nor image: 2\n'
            '   images:\n     2 files: 2 WebP\n     with EXIF: 1; with XMP: 0;', out)
        # counts only: none of the numbers found in those files is in the report
        self.assertIsNone(COORDINATE.search(out), 'a coordinate-like number in the --site report')
        for number in ('%.5f' % end[0], '%.3f' % end[0], '2.8333', '1.5000', str(STRAVA_ID), ZONE):
            self.assertNotIn(number, out)
        self.assertIn('--site: the folder given does not exist', self.usage_error('--site', os.path.join(self.tmp, 'nowhere')))

    def test_the_defaults_are_the_checkouts_own_folders(self):
        self.build()
        write(os.path.join(self.rendered, 'trips', 'alpha-loop-0', 'meta.json'), '{"start": [1, 2], "end": [3, 4]}')
        out = io.StringIO()
        with mock.patch.object(pa.content, 'TRIPS_DIR', self.trips), mock.patch.object(pa.content, 'RENDERED', self.rendered):
            self.assertEqual(pa.main([], out=out, isatty=False), 0)
        self.assertIn('GPX files: 10 = 9 recorded tracks + 1 planned route;', out.getvalue())
        self.assertIn('meta.json: 1 file;', out.getvalue())
        err = io.StringIO()
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stderr(err):
            pa.main(['--content', os.path.join(self.tmp, 'nowhere')], out=io.StringIO())
        self.assertEqual(cm.exception.code, 2)
        self.assertIn('no trips/ folder to read', err.getvalue())
        self.assertNotIn(self.tmp, err.getvalue())

    def test_help_explains_the_two_modes(self):
        out = io.StringIO()
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(out):
            pa.main(['--help'])
        self.assertEqual(cm.exception.code, 0)
        text = out.getvalue()
        for flag in ('--radius', '--min-cluster', '--list', '--list-anyway', '--near', '--site', 'default 150', 'default 3'):
            self.assertIn(flag, text)
        self.assertIn('Read-only and offline', text)


class NotPartOfTheSite(unittest.TestCase):

    def test_nothing_in_the_build_or_ci_runs_it(self):
        runs = re.compile(r'^\s*(?:import|from)\s+privacy_audit\b|import_module\([^)\n]*privacy_audit|privacy_audit\.(?:main|audit)\(|'
                          r'privacy_audit\.py', re.M)
        tools = os.path.join(ROOT, 'tools')
        for dp, _dn, fn in os.walk(tools):
            for f in fn:
                p = os.path.join(dp, f)
                if not f.endswith('.py') or os.path.samefile(p, pa.__file__) or pa.conflict_copy(f):
                    continue
                with open(p, encoding='utf-8') as fh:
                    self.assertIsNone(runs.search(fh.read()), '%s runs or imports the privacy audit' % os.path.relpath(p, ROOT))
        flows = os.path.join(ROOT, '.github', 'workflows')
        for f in (sorted(os.listdir(flows)) if os.path.isdir(flows) else []):
            with open(os.path.join(flows, f), encoding='utf-8') as fh:
                self.assertNotIn('privacy_audit', fh.read(), 'the workflow %s mentions the privacy audit: a CI log is public' % f)

    def test_the_tool_and_the_notes_hold_no_position(self):
        """The tool and docs/PRIVACY_NOTES.md are public: nothing in them may look like a position (a number with three
        or more decimals), and the notes may not hold a line of the author's listing, nor what the default report no
        longer prints because it is one track's own: a clock time to the minute, an earliest or a latest start. (This
        file's own numbers are the invented spot at latitude 10, longitude 10.)"""
        notes = os.path.join(ROOT, 'docs', 'PRIVACY_NOTES.md')
        for p in (pa.__file__, notes):
            if not os.path.exists(p):
                continue                                                         # a checkout without the notes
            with open(p, encoding='utf-8') as fh:
                text = fh.read()
            hit = COORDINATE.search(text)
            self.assertIsNone(hit, '%s holds %r' % (os.path.relpath(p, ROOT), hit.group(0) if hit else ''))
            if p == notes:
                self.assertIsNone(re.search(r'(?m)^\s*(?:place \d+:|near -?\d)', text), 'a line of --list in the notes')
                self.assertNotIn('AUTHOR ONLY:', text)
                minutes = re.findall(r'\b(?:[01]\d|2[0-4]):([0-5]\d)\b', text)
                self.assertEqual([m for m in minutes if m not in ('00', '15', '30', '45')], [], 'a clock time to the minute in the notes')
                self.assertIsNone(re.search(r'(?i)\b(?:earliest|latest)\b[^.\n]*\d\d:\d\d', text), 'an earliest or latest start in the notes')
                self.assertIsNone(re.search(r'(?i)\b(?:[12]|one|two) by (?:10|ten) or more\b|\bby (?:10|ten) or more\D{0,12}\b[12]\b', text),
                                  'a count of one or two places in the notes')


if __name__ == '__main__':
    unittest.main()
