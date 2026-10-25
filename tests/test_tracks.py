"""tools/lib/tracks.py (Phase 6): the time zone guessed from a track's first point, the local start time in a zone, and
a track read out of a .zip without unpacking it.

guess_tz is a list of boxes, not borders, checked in order: Zurich, then Arizona (it keeps no summer time, so its box
comes before the Los Angeles and Denver boxes it overlaps), Los Angeles, Denver, Chicago, New York, and 'UTC' where no
box applies. Each box is pinned with an invented point inside it, and the edges with points either side of them.
local_start reads gpx_fixtures.SINGLE (recorded from 2026-07-04 15:00 UTC) in two zones.

tracks.read takes a .zip (Garmin Connect's 'Export Original' download) holding exactly one .fit, .fit.gz or .gpx file
and reads it from memory: tracks.zip_member picks the member, fit_reader.read_track_bytes parses it. The zips are
written in a temp dir with zipfile; the FIT file is a tiny one built here with struct (a 14-byte header, one definition
of the record message, a data message per point, a 2-byte CRC that is not checked), gzipped for the .fit.gz member.
Every point is invented (beside 38.9N 120.1W, open water, as in gpx_fixtures). Nothing touches content/ or the network.
"""
import gzip
import os
import struct
import tempfile
import unittest
import zipfile
from unittest import mock

import helpers  # noqa: F401  (puts tools/lib on sys.path)
import gpx_fixtures as gf
import fit_reader
import tracks

FIT_EPOCH = 631065600            # 1989-12-31 00:00 UTC in unix seconds
INVALID_LAT = 0x7FFFFFFF         # a sint32 the FIT profile reads as "no value"

# (lat, lon, ele, unix ts) of the FIT fixture; the third point has no position (an invalid latitude): it is dropped
FIT_POINTS = [(38.9, -120.1, 2000, int(gf.ts(0))), (38.901, -120.1, 2005, int(gf.ts(1))), (None, -120.1, 2008, int(gf.ts(2))),
              (38.902, -120.1, 2010, int(gf.ts(3)))]


def semicircles(deg):
    return int(round(deg * 2 ** 31 / 180.0))


def fit_file(points):
    """A FIT file as bytes: a 14-byte header (its size, protocol and profile versions, the data size little-endian,
    '.FIT', a header CRC of 0), one definition message for local message 0 = global message 20 (record) with the fields
    253 timestamp (uint32), 0 lat and 1 lon (sint32 semicircles) and 2 altitude (uint16, (alt + 500) * 5), one data
    message per point, then the file's 2-byte CRC (0: the reader does not check it). lat None writes the invalid value."""
    fields = [(253, 4, 0x86), (0, 4, 0x85), (1, 4, 0x85), (2, 2, 0x84)]
    data = bytes([0x40, 0, 0]) + struct.pack('<HB', 20, len(fields)) + b''.join(struct.pack('<BBB', *f) for f in fields)
    for lat, lon, ele, ts in points:
        data += bytes([0x00]) + struct.pack('<IiiH', ts - FIT_EPOCH, INVALID_LAT if lat is None else semicircles(lat),
                                            semicircles(lon), int(round((ele + 500) * 5)))
    header = struct.pack('<BBHI4sH', 14, 0x20, 2132, len(data), b'.FIT', 0)
    return header + data + b'\x00\x00'


FIT = fit_file(FIT_POINTS)
GPX = gf.SINGLE.encode('utf-8')


def write_zip(path, members):
    """A .zip at path holding members [(name, bytes)], in that order; a name ending in '/' is a folder entry."""
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, data in members:
            zf.writestr(name, data)
    return path


def in_la_box(lat, lon):
    return lon < -114.5 and lat > 32


def in_denver_box(lat, lon):
    return -114.5 <= lon < -102 and lat > 31


class GuessTzTests(unittest.TestCase):

    def test_an_invented_point_inside_each_box(self):
        table = [((46.5, 9.5), 'Europe/Zurich'),
                 ((34.5, -111.5), 'America/Phoenix'),
                 ((39.5, -121.5), 'America/Los_Angeles'),
                 ((40.5, -106.5), 'America/Denver'),
                 ((38.5, -93.5), 'America/Chicago'),
                 ((41.5, -76.5), 'America/New_York')]
        for (lat, lon), zone in table:
            with self.subTest(zone=zone):
                self.assertEqual(tracks.guess_tz(lat, lon), zone)

    def test_arizona_comes_before_los_angeles_and_denver(self):
        # each point is inside the Arizona box and inside the other box as well: Arizona's is checked first
        for (lat, lon), other in (((34.0, -114.6), in_la_box), ((35.0, -110.0), in_denver_box), ((31.5, -113.0), in_denver_box)):
            with self.subTest(point=(lat, lon)):
                self.assertTrue(other(lat, lon))
                self.assertEqual(tracks.guess_tz(lat, lon), 'America/Phoenix')

    def test_the_arizona_box_edges(self):
        # 31.3 <= lat <= 37 and -114.8 <= lon <= -109, edges included
        for lat, lon in ((31.3, -112.0), (37.0, -112.0), (34.0, -114.8), (34.0, -109.0)):
            self.assertEqual(tracks.guess_tz(lat, lon), 'America/Phoenix', (lat, lon))
        self.assertEqual(tracks.guess_tz(37.01, -112.0), 'America/Denver')
        self.assertEqual(tracks.guess_tz(31.29, -112.0), 'America/Denver')
        self.assertEqual(tracks.guess_tz(34.0, -108.99), 'America/Denver')
        self.assertEqual(tracks.guess_tz(34.0, -114.81), 'America/Los_Angeles')

    def test_the_edges_between_the_mainland_zones(self):
        for (lat, lon), zone in (((40.0, -114.51), 'America/Los_Angeles'), ((40.0, -114.5), 'America/Denver'),
                                 ((40.0, -102.01), 'America/Denver'), ((40.0, -102.0), 'America/Chicago'),
                                 ((40.0, -85.01), 'America/Chicago'), ((40.0, -85.0), 'America/New_York'),
                                 ((40.0, -66.01), 'America/New_York')):
            with self.subTest(point=(lat, lon)):
                self.assertEqual(tracks.guess_tz(lat, lon), zone)

    def test_where_no_box_applies_it_is_utc(self):
        # east of every box; past New York's east edge; south of the American boxes; south of Zurich's
        for lat, lon in ((40.0, 60.0), (40.0, -66.0), (20.0, -100.0), (10.0, 10.0), (-33.5, 150.5)):
            with self.subTest(point=(lat, lon)):
                self.assertEqual(tracks.guess_tz(lat, lon), 'UTC')


class LocalStartTests(unittest.TestCase):
    """local_start(points, zone): the first timestamp as a datetime in the zone, and the zone (guessed when not given)."""

    def setUp(self):
        self.pts = fit_reader.read_gpx_bytes(GPX)

    def test_the_fixture_starts_at_15_00_utc(self):
        self.assertEqual(self.pts[0][3], gf.ts(0))
        self.assertEqual(gf.iso(0), '2026-07-04T15:00:00Z')

    def test_the_date_and_clock_are_the_zones(self):
        for zone, want in (('America/Los_Angeles', '2026-07-04 08:00'), ('Asia/Tokyo', '2026-07-05 00:00')):
            with self.subTest(zone=zone):
                when, tz = tracks.local_start(self.pts, zone)
                self.assertEqual(tz, zone)
                self.assertEqual(when.strftime('%Y-%m-%d %H:%M'), want)
                self.assertEqual(when.timestamp(), gf.ts(0))

    def test_without_a_zone_the_first_point_picks_one(self):
        when, tz = tracks.local_start(self.pts)
        self.assertEqual(tz, tracks.guess_tz(38.9, -120.1))
        self.assertEqual(tz, 'America/Los_Angeles')
        self.assertEqual(when.strftime('%Y-%m-%d %H:%M'), '2026-07-04 08:00')

    def test_a_track_without_timestamps_has_no_start(self):
        pts = fit_reader.read_gpx_bytes(gf.NO_TIME.encode('utf-8'))
        self.assertEqual(tracks.local_start(pts, 'Asia/Tokyo'), (None, 'Asia/Tokyo'))


class ZipTests(unittest.TestCase):
    """tracks.read and tracks.zip_member on zips written in a temp dir."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)

    def zip(self, members, name='export.zip'):
        return write_zip(os.path.join(self.tmp, name), members)

    def assertFitPoints(self, pts):
        """The FIT fixture's points with a position, decoded: semicircles to about a centimetre, the rest exactly."""
        want = [p for p in FIT_POINTS if p[0] is not None]
        self.assertEqual(len(pts), len(want))
        for got, (lat, lon, ele, ts) in zip(pts, want):
            self.assertAlmostEqual(got[0], lat, places=6)
            self.assertAlmostEqual(got[1], lon, places=6)
            self.assertEqual((got[2], got[3]), (float(ele), ts))

    def test_the_fit_fixture_reads_as_a_fit_file(self):
        # the hand-built bytes are a FIT file fit_reader reads, before any zip is involved
        path = os.path.join(self.tmp, 'synthetic.fit')
        with open(path, 'wb') as fh:
            fh.write(FIT)
        self.assertFitPoints(tracks.read(path))
        self.assertEqual(len(fit_reader.read_fit_bytes(FIT)), 3)     # the point without a position is not one

    def test_one_gpx_member_is_read_from_memory(self):
        path = self.zip([('Synthetic ridge.gpx', GPX)])
        self.assertEqual(tracks.zip_member(path), ('Synthetic ridge.gpx', GPX))
        pts = tracks.read(path)
        want = [(lat, lon, float(ele), gf.ts(i)) for i, (lat, lon, ele, _when) in enumerate(gf.SEG_A)]
        self.assertEqual(pts, want)
        # the same points as the file itself
        plain = os.path.join(self.tmp, 'synthetic.gpx')
        with open(plain, 'wb') as fh:
            fh.write(GPX)
        self.assertEqual(tracks.read(plain), pts)

    def test_one_fit_gz_member(self):
        packed = gzip.compress(FIT)
        path = self.zip([('activity_1234.fit.gz', packed)])
        self.assertEqual(tracks.zip_member(path), ('activity_1234.fit.gz', packed))
        self.assertFitPoints(tracks.read(path))

    def test_one_fit_member_and_names_in_capitals(self):
        self.assertFitPoints(tracks.read(self.zip([('ACTIVITY.FIT', FIT)], 'a.zip')))
        self.assertFitPoints(tracks.read(self.zip([('ACTIVITY.FIT.GZ', gzip.compress(FIT))], 'b.zip')))
        self.assertEqual(len(tracks.read(self.zip([('Synthetic.GPX', GPX)], 'c.zip'))), len(gf.SEG_A))
        self.assertEqual(len(tracks.read(self.zip([('Synthetic.gpx', GPX)], 'D.ZIP'))), len(gf.SEG_A))

    def test_a_member_inside_a_folder_of_the_zip(self):
        path = self.zip([('export/', b''), ('export/2026/', b''), ('export/2026/Synthetic ridge.gpx', GPX)])
        self.assertEqual(tracks.zip_member(path), ('export/2026/Synthetic ridge.gpx', GPX))
        self.assertEqual(len(tracks.read(path)), len(gf.SEG_A))

    def test_macosx_members_dot_files_folders_and_other_files_are_ignored(self):
        path = self.zip([('__MACOSX/', b''), ('__MACOSX/._Synthetic.gpx', b'resource fork'), ('__MACOSX/Synthetic.gpx', GPX),
                         ('.Synthetic.gpx', GPX), ('export/.hidden.fit', FIT), ('notes.gpx/', b''), ('readme.txt', b'synthetic'),
                         ('route.tcx', b'<x/>'), ('Synthetic.gpx', GPX)])
        self.assertEqual(tracks.zip_member(path), ('Synthetic.gpx', GPX))
        self.assertEqual(len(tracks.read(path)), len(gf.SEG_A))

    def test_two_track_members_are_refused_by_name(self):
        path = self.zip([('a.fit', FIT), ('readme.txt', b'synthetic'), ('b.gpx', GPX)])
        for read in (tracks.zip_member, tracks.read):
            with self.subTest(read=read.__name__):
                with self.assertRaises(ValueError) as cm:
                    read(path)
                self.assertEqual(str(cm.exception), 'the .zip holds 2 track files (a.fit, b.gpx); unzip it and give the one you mean')
        path = self.zip([('day/one.fit.gz', gzip.compress(FIT)), ('day/two.FIT', FIT), ('three.gpx', GPX)], 'three.zip')
        with self.assertRaises(ValueError) as cm:
            tracks.zip_member(path)
        self.assertEqual(str(cm.exception),
                         'the .zip holds 3 track files (day/one.fit.gz, day/two.FIT, three.gpx); unzip it and give the one you mean')

    def test_no_track_member_is_refused(self):
        for name, members in (('empty.zip', []), ('other.zip', [('readme.txt', b'synthetic'), ('route.tcx', b'<x/>')]),
                              ('hidden.zip', [('__MACOSX/Synthetic.gpx', GPX), ('.Synthetic.fit', FIT), ('folder.gpx/', b'')])):
            with self.subTest(name=name):
                path = self.zip(members, name)
                for read in (tracks.zip_member, tracks.read):
                    with self.assertRaises(ValueError) as cm:
                        read(path)
                    self.assertEqual(str(cm.exception), 'the .zip holds no .fit, .fit.gz or .gpx file')

    def test_a_member_larger_than_zip_max_is_refused(self):
        path = self.zip([('Synthetic ridge.gpx', GPX)])
        with mock.patch.object(tracks, 'ZIP_MAX', len(GPX) - 1):
            for read in (tracks.zip_member, tracks.read):
                with self.assertRaises(ValueError) as cm:
                    read(path)
                self.assertIn('Synthetic ridge.gpx', str(cm.exception))
        with mock.patch.object(tracks, 'ZIP_MAX', len(GPX)):           # exactly the limit is still a recording
            self.assertEqual(tracks.zip_member(path), ('Synthetic ridge.gpx', GPX))

    def test_the_limit_is_fifty_megabytes(self):
        self.assertEqual(tracks.ZIP_MAX, 50 * 1024 * 1024)

    def test_a_file_that_is_not_a_zip(self):
        for name, data in (('fake.zip', b'not a zip archive at all, only some synthetic text'), ('empty.zip', b''), ('gpx.zip', GPX)):
            with self.subTest(name=name):
                path = os.path.join(self.tmp, name)
                with open(path, 'wb') as fh:
                    fh.write(data)
                for read in (tracks.zip_member, tracks.read):
                    with self.assertRaises(zipfile.BadZipFile):
                        read(path)

    def test_a_gpx_member_with_a_doctype_is_refused(self):
        path = self.zip([('Synthetic.gpx', gf.DOCTYPE.encode('utf-8'))])
        with self.assertRaises(ValueError):
            tracks.read(path)
        # as tools/lib/gpxroute.py refuses it: an entity declaration anywhere in the bytes, a comment included
        path = self.zip([('Synthetic.gpx', gf.ENTITY_IN_COMMENT.encode('utf-8'))], 'entity.zip')
        with self.assertRaises(ValueError):
            tracks.read(path)
        # a plain comment is fine
        path = self.zip([('Synthetic.gpx', gf.gpx(gf.trk([gf.SEG_A]), '<!-- a synthetic note -->').encode('utf-8'))], 'comment.zip')
        self.assertEqual(len(tracks.read(path)), len(gf.SEG_A))

    def test_nothing_is_extracted(self):
        # read from inside the folder that holds the zip, with a member whose name climbs out of it: afterwards the
        # folder holds the zip alone and nothing was written beside it
        box = os.path.join(self.tmp, 'box')
        os.makedirs(box)
        for name, members in (('gpx.zip', [('export/Synthetic.gpx', GPX)]), ('fit.zip', [('activity.fit.gz', gzip.compress(FIT))]),
                              ('climb.zip', [('../outside.gpx', GPX)])):
            path = write_zip(os.path.join(box, name), members)
            here = os.getcwd()
            os.chdir(box)
            try:
                self.assertTrue(tracks.read(path))
            finally:
                os.chdir(here)
            self.assertEqual(os.listdir(box), [name], name)
            self.assertEqual(os.listdir(self.tmp), ['box'], name)
            os.remove(path)


if __name__ == '__main__':
    unittest.main()
