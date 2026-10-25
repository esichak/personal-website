"""Phase 6: tools/lib/fit_reader.py, the stdlib FIT and GPX decoder behind tools/add_trip.py and tracks.read.

A FIT file is built here byte by byte with struct (build_fit): a 14-byte header (or 12), one definition message for the
record message (global 20) with the fields 253 timestamp, 0 latitude, 1 longitude and 78 enhanced altitude (or 2
altitude, or both, or none), one data message per point, and the 2-byte file CRC. The values are the ones the FIT
profile defines: seconds since 1989-12-31 00:00 UTC, semicircles (degrees * 2**31 / 180), altitude as (m + 500) * 5. The
points are invented (open water near 38.9 N 120.1 W, the spot tests/gpx_fixtures.py uses) and every expectation is
worked out from the numbers given to build_fit, never from the module under test. GPX inputs are the synthetic strings of
tests/gpx_fixtures.py. Files go to a temp dir only.

build_fit and the three-record POINTS are imported by tests/test_add_trip.py (tests/ is on sys.path under discovery), so
the FIT that add_trip.py imports end to end is the same one these tests decode.
"""
import gzip
import os
import struct
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import fit_reader  # noqa: E402

import gpx_fixtures as gf  # noqa: E402

FIT_EPOCH_UNIX = 631065600        # 1989-12-31T00:00:00Z: FIT timestamps count from here
INVALID_SINT32 = 0x7FFFFFFF       # the FIT "no value" of a sint32 field (latitude, longitude)
INVALID_UINT32 = 0xFFFFFFFF
INVALID_UINT16 = 0xFFFF

# three invented fixes a minute apart, about 550 m apart (so a route of them is point-to-point), with elevations that
# are exact in the (m + 500) * 5 encoding: (lat, lon, ele_m, unix_ts)
POINTS = [
    (38.900, -120.100, 2000.0, int(gf.ts(0))),
    (38.905, -120.100, 2010.4, int(gf.ts(1))),
    (38.910, -120.100, 2020.0, int(gf.ts(2))),
]

# the FIT CRC-16 (the profile's nibble table); the reader does not check it, the files are written with a right one anyway
_CRC_TABLE = (0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
              0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400)


def fit_crc(data, crc=0):
    for byte in bytearray(data):
        tmp = _CRC_TABLE[crc & 0xF]
        crc = ((crc >> 4) & 0x0FFF) ^ tmp ^ _CRC_TABLE[byte & 0xF]
        tmp = _CRC_TABLE[crc & 0xF]
        crc = ((crc >> 4) & 0x0FFF) ^ tmp ^ _CRC_TABLE[(byte >> 4) & 0xF]
    return crc


def semicircles(deg):
    return int(round(deg * 2 ** 31 / 180.0))


def build_fit(points, altitude='enhanced', header_size=14, big_endian=False, enhanced=None, plain=None):
    """The bytes of a FIT activity file holding `points` [(lat, lon, ele_m or None, unix_ts)] as record messages.

    altitude: 'enhanced' (field 78, uint32), 'plain' (field 2, uint16), 'both' (2 then 78) or None (no altitude field).
    A lat or lon of None is written as the invalid sint32 0x7FFFFFFF, an ele of None as the field's invalid value.
    enhanced / plain: per-point elevations for the two fields when altitude='both' (default: the point's own).
    header_size: 14 (with a header CRC) or 12. big_endian: architecture byte 1 in the definition message."""
    e = '>' if big_endian else '<'
    fields = [(253, 4, 0x86), (0, 4, 0x85), (1, 4, 0x85)]
    if altitude in ('plain', 'both'):
        fields.append((2, 2, 0x84))
    if altitude in ('enhanced', 'both'):
        fields.append((78, 4, 0x86))
    local = 0
    # definition: header byte, reserved, architecture, global message number (in the definition's byte order), field count
    body = bytes([0x40 | local, 0, 1 if big_endian else 0]) + struct.pack(e + 'H', 20) + bytes([len(fields)])
    for num, size, base in fields:
        body += bytes([num, size, base])
    for i, (lat, lon, ele, ts) in enumerate(points):
        rec = bytes([local])
        rec += struct.pack(e + 'I', ts - FIT_EPOCH_UNIX)
        rec += struct.pack(e + 'i', INVALID_SINT32 if lat is None else semicircles(lat))
        rec += struct.pack(e + 'i', INVALID_SINT32 if lon is None else semicircles(lon))
        if altitude in ('plain', 'both'):
            v = plain[i] if plain is not None else ele
            rec += struct.pack(e + 'H', INVALID_UINT16 if v is None else int(round((v + 500) * 5)))
        if altitude in ('enhanced', 'both'):
            v = enhanced[i] if enhanced is not None else ele
            rec += struct.pack(e + 'I', INVALID_UINT32 if v is None else int(round((v + 500) * 5)))
        body += rec
    head = struct.pack('<BBHI4s', header_size, 0x20, 2132, len(body), b'.FIT')
    if header_size == 14:
        head += struct.pack('<H', fit_crc(head))
    data = head + body
    return data + struct.pack('<H', fit_crc(data))


def write(path, data):
    with open(path, 'wb') as fh:
        fh.write(data)
    return path


class FitDecodeTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.fit = build_fit(POINTS)

    def assert_points(self, got, want):
        """got from the reader against (lat, lon, ele, ts) as given to build_fit: lat/lon to 1e-6 degrees (a semicircle
        is 8e-8 degrees), elevation and time exactly."""
        self.assertEqual(len(got), len(want), got)
        for g, w in zip(got, want):
            self.assertAlmostEqual(g[0], w[0], places=6)
            self.assertAlmostEqual(g[1], w[1], places=6)
            if w[2] is None:
                self.assertIsNone(g[2])
            else:
                self.assertAlmostEqual(g[2], w[2], places=6)
            self.assertEqual(g[3], w[3])

    def test_the_hand_built_file_decodes_to_its_three_points(self):
        self.assert_points(fit_reader.read_fit_bytes(self.fit), POINTS)

    def test_the_file_is_what_build_fit_says_it_is(self):
        # a guard on the fixture itself: header size, data size, the .FIT signature, and the record definition
        self.assertEqual(self.fit[0], 14)
        self.assertEqual(self.fit[8:12], b'.FIT')
        self.assertEqual(struct.unpack_from('<I', self.fit, 4)[0], len(self.fit) - 14 - 2)
        self.assertEqual(self.fit[14], 0x40)
        self.assertEqual(struct.unpack_from('<H', self.fit, 17)[0], 20)
        self.assertEqual(self.fit[19], 4)
        self.assertEqual(list(self.fit[20:32]), [253, 4, 0x86, 0, 4, 0x85, 1, 4, 0x85, 78, 4, 0x86])
        self.assertEqual(fit_crc(self.fit[:-2]), struct.unpack('<H', self.fit[-2:])[0])

    def test_read_fit_on_a_path_is_read_fit_bytes_on_its_bytes(self):
        path = write(os.path.join(self.tmp, 'ride.fit'), self.fit)
        self.assertEqual(fit_reader.read_fit(path), fit_reader.read_fit_bytes(self.fit))
        self.assert_points(fit_reader.read_fit(path), POINTS)

    def test_a_fit_gz_file_is_unzipped_first(self):
        packed = gzip.compress(self.fit)
        path = write(os.path.join(self.tmp, 'ride.fit.gz'), packed)
        self.assert_points(fit_reader.read_fit(path), POINTS)
        self.assert_points(fit_reader.read_fit_bytes(packed, gz=True), POINTS)
        self.assertEqual(fit_reader.read_fit(path), fit_reader.read_fit_bytes(self.fit))

    def test_a_gz_name_in_capitals_is_unzipped_too(self):
        # Garmin and some file managers write RIDE.FIT.GZ: read_fit unzips by the name in any case, as read_track_bytes does
        path = write(os.path.join(self.tmp, 'RIDE.FIT.GZ'), gzip.compress(self.fit))
        self.assert_points(fit_reader.read_fit(path), POINTS)

    def test_a_12_byte_header_reads_the_same(self):
        short = build_fit(POINTS, header_size=12)
        self.assertEqual(short[0], 12)
        self.assertEqual(len(short), len(self.fit) - 2)
        self.assert_points(fit_reader.read_fit_bytes(short), POINTS)

    def test_a_big_endian_definition_reads_the_same(self):
        self.assert_points(fit_reader.read_fit_bytes(build_fit(POINTS, big_endian=True)), POINTS)

    def test_the_file_crc_is_not_checked(self):
        broken = self.fit[:-2] + b'\x00\x00'
        self.assert_points(fit_reader.read_fit_bytes(broken), POINTS)

    def test_a_point_with_the_invalid_latitude_is_skipped(self):
        pts = [POINTS[0], (None, -120.1, 2005.0, POINTS[1][3]), POINTS[2]]
        self.assert_points(fit_reader.read_fit_bytes(build_fit(pts)), [POINTS[0], POINTS[2]])

    def test_a_point_with_the_invalid_longitude_is_skipped(self):
        pts = [POINTS[0], POINTS[1], (38.91, None, 2020.0, POINTS[2][3])]
        self.assert_points(fit_reader.read_fit_bytes(build_fit(pts)), POINTS[:2])

    def test_the_altitude_field_is_read_when_there_is_no_enhanced_altitude(self):
        got = fit_reader.read_fit_bytes(build_fit(POINTS, altitude='plain'))
        self.assert_points(got, POINTS)

    def test_enhanced_altitude_wins_over_altitude_when_both_are_recorded(self):
        enh = [1500.0, 1510.2, 1520.0]
        plain = [900.0, 910.0, 920.0]
        got = fit_reader.read_fit_bytes(build_fit(POINTS, altitude='both', enhanced=enh, plain=plain))
        self.assertEqual([g[2] for g in got], enh)

    def test_an_invalid_enhanced_altitude_falls_back_to_altitude(self):
        got = fit_reader.read_fit_bytes(build_fit(POINTS, altitude='both', enhanced=[None, None, None],
                                                  plain=[900.0, 910.0, 920.0]))
        self.assertEqual([g[2] for g in got], [900.0, 910.0, 920.0])

    def test_no_altitude_field_gives_no_elevation(self):
        got = fit_reader.read_fit_bytes(build_fit(POINTS, altitude=None))
        self.assertEqual([g[2] for g in got], [None, None, None])
        self.assertEqual([g[3] for g in got], [p[3] for p in POINTS])

    def test_a_fit_timestamp_counts_seconds_from_the_last_day_of_1989(self):
        self.assertEqual(fit_reader.FIT_EPOCH, FIT_EPOCH_UNIX)
        self.assertEqual(datetime.fromtimestamp(FIT_EPOCH_UNIX, timezone.utc), datetime(1989, 12, 31, tzinfo=timezone.utc))
        # a record stamped 0 is that instant; the fixture's first record is the fixture clock's 15:00 UTC
        zero = build_fit([(38.9, -120.1, 2000.0, FIT_EPOCH_UNIX)])
        self.assertEqual(fit_reader.read_fit_bytes(zero)[0][3], FIT_EPOCH_UNIX)
        first = fit_reader.read_fit_bytes(self.fit)[0][3]
        self.assertEqual(datetime.fromtimestamp(first, timezone.utc), datetime(2026, 7, 4, 15, 0, tzinfo=timezone.utc))
        # and the raw field is unix - 631065600
        self.assertEqual(struct.unpack_from('<I', self.fit, 33)[0], POINTS[0][3] - FIT_EPOCH_UNIX)

    def test_bytes_that_are_not_a_fit_file_give_no_points(self):
        self.assertEqual(fit_reader.read_fit_bytes(b'not a fit file at all'), [])


class TrackDispatchTests(unittest.TestCase):
    """read_track(path) and read_track_bytes(name, data): .gpx by name, in any case, else FIT (.gz unzipped)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.fit = build_fit(POINTS)
        self.gpx = gf.SINGLE.encode('utf-8')
        self.gpx_points = fit_reader.read_gpx_bytes(self.gpx)
        self.fit_points = fit_reader.read_fit_bytes(self.fit)
        self.assertEqual(len(self.gpx_points), 12)
        self.assertEqual(len(self.fit_points), 3)

    def test_read_track_reads_a_gpx_path_by_its_name_in_any_case(self):
        for name in ('walk.gpx', 'WALK.GPX', 'Walk.Gpx'):
            with self.subTest(name=name):
                path = write(os.path.join(self.tmp, name), self.gpx)
                self.assertEqual(fit_reader.read_track(path), self.gpx_points)

    def test_read_track_reads_any_other_path_as_fit(self):
        for name in ('ride.fit', 'RIDE.FIT', 'ride.bin'):
            with self.subTest(name=name):
                path = write(os.path.join(self.tmp, name), self.fit)
                self.assertEqual(fit_reader.read_track(path), self.fit_points)
        path = write(os.path.join(self.tmp, 'ride.fit.gz'), gzip.compress(self.fit))
        self.assertEqual(fit_reader.read_track(path), self.fit_points)

    def test_read_track_bytes_reads_gpx_by_name_in_any_case(self):
        for name in ('walk.gpx', 'WALK.GPX', 'folder/Walk.GpX'):
            with self.subTest(name=name):
                self.assertEqual(fit_reader.read_track_bytes(name, self.gpx), self.gpx_points)

    def test_read_track_bytes_reads_fit_and_unzips_a_gz_name_in_any_case(self):
        self.assertEqual(fit_reader.read_track_bytes('ride.fit', self.fit), self.fit_points)
        self.assertEqual(fit_reader.read_track_bytes('RIDE.FIT', self.fit), self.fit_points)
        packed = gzip.compress(self.fit)
        self.assertEqual(fit_reader.read_track_bytes('ride.fit.gz', packed), self.fit_points)
        self.assertEqual(fit_reader.read_track_bytes('RIDE.FIT.GZ', packed), self.fit_points)

    def test_gpx_bytes_by_a_fit_name_are_not_read_as_gpx(self):
        # the name decides, not the bytes: GPX text under a .fit name has no FIT header, so no points
        self.assertEqual(fit_reader.read_track_bytes('walk.fit', self.gpx), [])


class GpxBytesTests(unittest.TestCase):

    def expected(self, seg):
        return [(float(lat), float(lon), None if ele is None else float(ele),
                 None if when is None else datetime.strptime(when, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp())
                for lat, lon, ele, when in seg]

    def test_a_small_gpx_gives_its_points_with_elevation_and_unix_time(self):
        got = fit_reader.read_gpx_bytes(gf.SINGLE.encode('utf-8'))
        self.assertEqual(got, self.expected(gf.SEG_A))
        self.assertEqual(got[0][3], gf.ts(0))
        self.assertEqual(got[-1][3], gf.ts(11))

    def test_a_gpx_without_the_namespace_reads_the_same(self):
        self.assertEqual(fit_reader.read_gpx_bytes(gf.SINGLE_NO_NS.encode('utf-8')), self.expected(gf.SEG_A))

    def test_a_gpx_without_times_gives_none_for_each_time(self):
        got = fit_reader.read_gpx_bytes(gf.NO_TIME.encode('utf-8'))
        self.assertEqual([p[3] for p in got], [None] * 12)

    def test_fractional_seconds_and_offsets_give_the_same_instant_on_any_machine(self):
        # '18:40:00.000Z' once lost its offset with its fraction and was read in the build machine's zone; the same
        # instant written five ways, under two TZ settings, is one timestamp (time.tzset: not on Windows, nor needed)
        whens = ('2026-01-17T18:40:00Z', '2026-01-17T18:40:00.000Z', '2026-01-17T10:40:00.5-08:00',
                 '2026-01-17T19:40:00.123456+01:00', '2026-01-17T18:40:00')
        gpx = (gf.HEAD + '<trk><trkseg>' + ''.join('<trkpt lat="38.9" lon="-120.1"><ele>1900</ele><time>%s</time></trkpt>' % w
                                                   for w in whens) + '</trkseg></trk>\n</gpx>\n')
        want = datetime(2026, 1, 17, 18, 40, tzinfo=timezone.utc).timestamp()
        import time
        if not hasattr(time, 'tzset'):
            self.skipTest('no time.tzset')
        old = os.environ.get('TZ')
        try:
            for tz in ('UTC', 'America/New_York', 'Asia/Tokyo'):
                os.environ['TZ'] = tz
                time.tzset()
                with self.subTest(tz=tz):
                    self.assertEqual([p[3] for p in fit_reader.read_gpx_bytes(gpx.encode('utf-8'))], [want] * len(whens))
        finally:
            if old is None:
                os.environ.pop('TZ', None)
            else:
                os.environ['TZ'] = old
            time.tzset()

    def test_a_time_that_is_not_iso_8601_gives_none(self):
        gpx = gf.HEAD + '<trk><trkseg><trkpt lat="38.9" lon="-120.1"><ele>1900</ele><time>yesterday</time></trkpt></trkseg></trk>\n</gpx>\n'
        self.assertEqual(fit_reader.read_gpx_bytes(gpx.encode('utf-8'))[0][3], None)

    def test_read_gpx_bytes_is_read_gpx_on_the_same_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(os.path.join(tmp, 'walk.gpx'), gf.SINGLE.encode('utf-8'))
            self.assertEqual(fit_reader.read_gpx(path), fit_reader.read_gpx_bytes(gf.SINGLE.encode('utf-8')))

    def test_a_doctype_declaration_is_refused_before_parsing(self):
        with self.assertRaises(ValueError) as cm:
            fit_reader.read_gpx_bytes(gf.DOCTYPE.encode('utf-8'))
        self.assertIn('DOCTYPE', str(cm.exception))

    def test_a_gpx_that_is_not_utf8_is_refused_before_parsing(self):
        # the declaration check reads UTF-8: in UTF-16 an ENTITY would slip past it to the parser
        entity = gf.HEAD + '<!ENTITY e "39.5">\n' + gf.trk([gf.SEG_A]) + '\n</gpx>\n'
        for data in (entity.encode('utf-16'), entity.encode('utf-16-be'), gf.SINGLE.encode('utf-8').replace(b'<trk>', b'<trk>\xff\xfe'),
                     gf.SINGLE.encode('utf-8') + b'\x00'):
            with self.subTest(data=data[:12]):
                with self.assertRaises(ValueError) as cm:
                    fit_reader.read_gpx_bytes(data)
                self.assertIn('not UTF-8', str(cm.exception))

    def test_a_gz_member_that_unpacks_without_end_is_refused(self):
        with mock.patch.object(fit_reader, 'GZ_MAX', 1000):
            with self.assertRaises(ValueError) as cm:
                fit_reader.read_fit_bytes(gzip.compress(b'\x00' * 5000), gz=True)
            self.assertIn('unpacks to more than', str(cm.exception))
            self.assertEqual(fit_reader.read_fit_bytes(gzip.compress(b'\x00' * 900), gz=True), [])

    def test_an_entity_declaration_is_refused(self):
        data = (gf.HEAD + '<!ENTITY boom "x">\n' + gf.trk([gf.SEG_A]) + '\n</gpx>\n').encode('utf-8')
        # a ValueError (not the parser's ParseError, which is a SyntaxError): the bytes were refused, not parsed
        with self.assertRaises(ValueError):
            fit_reader.read_gpx_bytes(data)

    def test_a_comment_and_a_cdata_section_are_accepted(self):
        commented = gf.gpx('<!-- exported by a synthetic tool -->', gf.trk([gf.SEG_A]))
        self.assertEqual(fit_reader.read_gpx_bytes(commented.encode('utf-8')), self.expected(gf.SEG_A))
        self.assertEqual(fit_reader.read_gpx_bytes(gf.CDATA_DESC.encode('utf-8')), self.expected(gf.SEG_A))


if __name__ == '__main__':
    unittest.main()
