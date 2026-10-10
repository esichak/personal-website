"""Phase 2T: tools/lib/gpxroute.py, the safe GPX inspection behind tools/ticklist.py and the planned-route renderer
(inspect, candidates, select, measure, as_tracks).

Every fixture is a synthetic GPX string from tests/gpx_fixtures.py written to a temp file: a single track, a track in three
segments with gaps between them, a route-only file, two tracks and a route (alternatives), a waypoint-only file, no / partial
elevation, no timestamps, a 5-point sparse file, a DOCTYPE and an ENTITY file, out-of-range and non-finite coordinates, a
non-gpx root and a non-numeric elevation. Measurements are checked against the fixture module's own haversine sums and
hysteresis, never against the module under test. gpxroute is imported in setUp so a missing module fails each test with a
clear message instead of breaking discovery. Nothing under content/ or rendered/ is read or written.
"""
import hashlib
import importlib
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import fit_reader  # noqa: E402
import tracks  # noqa: E402

import gpx_fixtures as gf  # noqa: E402


def load_gpxroute(tc):
    """tools/lib/gpxroute.py, or a clear failure of the calling test when it is missing."""
    try:
        return importlib.import_module('gpxroute')
    except ImportError as ex:
        tc.fail('tools/lib/gpxroute.py is not importable: %s' % ex)


def expected_point(p):
    """A fixture point (lat, lon, ele, iso) as inspect() should return it: floats, elevation float or None, unix time or None."""
    lat, lon, ele, when = p
    minutes = int((gf.datetime.strptime(when, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=gf.timezone.utc) - gf.T0).total_seconds() // 60) if when else None
    return (float(lat), float(lon), None if ele is None else float(ele), None if when is None else gf.ts(minutes))


class GpxFixture(unittest.TestCase):

    def setUp(self):
        self.gpx = load_gpxroute(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        return path

    def inspect(self, name, text):
        return self.gpx.inspect(self.write(name, text))

    def assertDistance(self, got, want_km):
        """Two decimals, with room for a different Earth radius (0.2 %) and the rounding."""
        self.assertAlmostEqual(got, round(want_km, 2), delta=max(0.02, want_km * 0.002))

    def assertPoints(self, got, fixture):
        self.assertEqual(len(got), len(fixture))
        for g, f in zip(got, fixture):
            e = expected_point(f)
            self.assertEqual(len(g), 4, g)
            self.assertAlmostEqual(g[0], e[0], places=6)
            self.assertAlmostEqual(g[1], e[1], places=6)
            if e[2] is None:
                self.assertIsNone(g[2])
            else:
                self.assertAlmostEqual(g[2], e[2], places=3)
            if e[3] is None:
                self.assertIsNone(g[3])
            else:
                self.assertAlmostEqual(g[3], e[3], places=3)


# ---------------------------------------------------------------- errors and constants

class ErrorAndConstantTests(GpxFixture):

    def test_error_classes(self):
        self.assertTrue(issubclass(self.gpx.GpxError, ValueError))
        self.assertTrue(issubclass(self.gpx.SelectionNeeded, self.gpx.GpxError))
        self.assertTrue(issubclass(self.gpx.NoRoute, self.gpx.GpxError))

    def test_limits(self):
        self.assertEqual(self.gpx.MAX_BYTES, 30_000_000)
        self.assertEqual(self.gpx.MAX_POINTS, 500_000)


# ---------------------------------------------------------------- inspect

class InspectTests(GpxFixture):

    def test_single_track_shape(self):
        path = self.write('single.gpx', gf.SINGLE)
        info = self.gpx.inspect(path)
        self.assertEqual(set(info), {'tracks', 'routes', 'waypoints', 'bytes', 'sha256', 'contains'})   # contains: what else the file carries
        self.assertEqual(len(info['tracks']), 1)
        self.assertEqual(set(info['tracks'][0]), {'name', 'segments'})
        self.assertEqual(info['tracks'][0]['name'], 'Synthetic ridge')
        self.assertEqual(len(info['tracks'][0]['segments']), 1)
        self.assertEqual(len(info['tracks'][0]['segments'][0]), 12)
        self.assertEqual(info['routes'], [])
        self.assertEqual(info['waypoints'], 0)
        with open(path, 'rb') as fh:
            raw = fh.read()
        self.assertEqual(info['bytes'], len(raw))
        self.assertEqual(info['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(info['sha256']), 64)

    def test_points_are_lat_lon_ele_time_tuples(self):
        info = self.inspect('single.gpx', gf.SINGLE)
        self.assertPoints(info['tracks'][0]['segments'][0], gf.SEG_A)
        first = info['tracks'][0]['segments'][0][0]
        self.assertAlmostEqual(first[3], gf.ts(0), places=3)   # 2026-07-04T15:00:00Z as a unix time

    def test_times_parse_like_fit_reader(self):
        path = self.write('single.gpx', gf.SINGLE)
        info = self.gpx.inspect(path)
        theirs = fit_reader.read_gpx(path)
        mine = info['tracks'][0]['segments'][0]
        self.assertEqual(len(mine), len(theirs))
        for a, b in zip(mine, theirs):
            self.assertAlmostEqual(a[3], b[3], places=3)

    def test_unnamed_track_has_name_none(self):
        info = self.inspect('unnamed.gpx', gf.UNNAMED)
        self.assertIsNone(info['tracks'][0]['name'])

    def test_three_segments_stay_three_segments(self):
        info = self.inspect('multi.gpx', gf.MULTISEG)
        segs = info['tracks'][0]['segments']
        self.assertEqual([len(s) for s in segs], [5, 5, 4])
        for got, want in zip(segs, gf.SEGS_M):
            self.assertPoints(got, want)

    def test_empty_segments_are_dropped(self):
        info = self.inspect('empty-seg.gpx', gf.EMPTY_SEG)
        self.assertEqual(len(info['tracks'][0]['segments']), 1)
        self.assertPoints(info['tracks'][0]['segments'][0], gf.SEG_A)
        info = self.inspect('empty-trk.gpx', gf.EMPTY_TRACK_AND_ROUTE)
        self.assertEqual(info['tracks'][0]['segments'], [])
        self.assertEqual(len(info['routes']), 1)

    def test_route_only_file(self):
        info = self.inspect('route.gpx', gf.ROUTE_ONLY)
        self.assertEqual(info['tracks'], [])
        self.assertEqual(len(info['routes']), 1)
        self.assertEqual(set(info['routes'][0]), {'name', 'points'})
        self.assertEqual(info['routes'][0]['name'], 'Ridge route')
        self.assertPoints(info['routes'][0]['points'], gf.RTE_PTS)
        self.assertEqual(info['waypoints'], 0)

    def test_two_tracks_and_a_route_in_file_order(self):
        info = self.inspect('alts.gpx', gf.ALTERNATIVES)
        self.assertEqual([t['name'] for t in info['tracks']], ['North approach', 'South approach'])
        self.assertEqual([len(s) for s in info['tracks'][1]['segments']], [4, 3])
        self.assertEqual([r['name'] for r in info['routes']], ['Descent'])
        self.assertEqual(len(info['routes'][0]['points']), 5)

    def test_waypoint_only_file(self):
        info = self.inspect('wpts.gpx', gf.WAYPOINT_ONLY)
        self.assertEqual(info['tracks'], [])
        self.assertEqual(info['routes'], [])
        self.assertEqual(info['waypoints'], 3)

    def test_waypoints_are_counted_beside_a_track(self):
        info = self.inspect('trk-wpts.gpx', gf.TRACK_PLUS_WPTS)
        self.assertEqual(info['waypoints'], 2)
        self.assertEqual(len(info['tracks']), 1)
        self.assertPoints(info['tracks'][0]['segments'][0], gf.SEG_A)

    def test_no_elevation_gives_none_elevations(self):
        info = self.inspect('noele.gpx', gf.NO_ELE)
        pts = info['tracks'][0]['segments'][0]
        self.assertEqual(len(pts), 12)
        self.assertTrue(all(p[2] is None for p in pts))
        self.assertTrue(all(p[3] is not None for p in pts))

    def test_partial_elevation_keeps_the_gaps(self):
        info = self.inspect('partial.gpx', gf.PARTIAL_ELE)
        pts = info['tracks'][0]['segments'][0]
        self.assertEqual([p[2] is None for p in pts], [e is None for e in gf.ELES_PARTIAL])

    def test_every_iso_zone_form_counts_as_a_timestamp(self):
        # a recording made west of Greenwich writes -07:00; the file has times whatever the zone looks like
        for i, stamp in enumerate(('2026-07-04T08:00:00-07:00', '2026-07-04T08:00:00-0700', '2026-07-04T17:00:00+02:00',
                                   '2026-07-04T15:00:00Z', '2026-07-04T15:00:00.250Z', '2026-07-04T15:00:00')):
            with self.subTest(stamp):
                pts = [(38.9 + 0.001 * k, -120.1, 2000 + k, stamp) for k in range(3)]
                info = self.inspect('zone%d.gpx' % i, gf.gpx(gf.trk([pts])))
                got = [p[3] for p in info['tracks'][0]['segments'][0]]
                self.assertEqual(got, [gf.ts(0)] * 3)             # all six are 15:00 UTC on the fixture day
                self.assertIs(info['contains']['times'], True)
                self.assertIs(self.gpx.measure(info['tracks'][0]['segments'])['times'], True)

    def test_an_unreadable_time_is_still_reported_as_carried(self):
        pts = [(38.9 + 0.001 * k, -120.1, 2000 + k, 'yesterday afternoon') for k in range(3)]
        info = self.inspect('odd.gpx', gf.gpx(gf.trk([pts])))
        self.assertEqual([p[3] for p in info['tracks'][0]['segments'][0]], [None] * 3)
        self.assertIs(info['contains']['times'], True)       # the bytes hold <time> text, so the privacy note says so

    def test_no_timestamps_give_none_times(self):
        info = self.inspect('notime.gpx', gf.NO_TIME)
        pts = info['tracks'][0]['segments'][0]
        self.assertTrue(all(p[3] is None for p in pts))
        self.assertTrue(all(p[2] is not None for p in pts))

    def test_accepts_a_gpx_root_without_a_namespace(self):
        info = self.inspect('nons.gpx', gf.SINGLE_NO_NS)
        self.assertPoints(info['tracks'][0]['segments'][0], gf.SEG_A)

    def test_rejects_a_doctype_before_parsing(self):
        with self.assertRaises(self.gpx.GpxError):
            self.inspect('doctype.gpx', gf.DOCTYPE)

    def test_rejects_an_entity_declaration_anywhere_in_the_bytes(self):
        with self.assertRaises(self.gpx.GpxError):
            self.inspect('entity.gpx', gf.ENTITY_IN_COMMENT)   # well-formed XML, the declaration is inside a comment

    def test_rejects_browser_runnable_content_the_byte_scan_cannot_see(self):
        # a goal GPX is served from the site's own origin as XML, so what a browser's parser sees is what matters
        for name, text, word in (('svgns.gpx', gf.SVG_NS_CHARREF, 'svg'), ('pscript.gpx', gf.PREFIXED_SCRIPT, 'script'),
                                 ('jsref.gpx', gf.JS_HREF_CHARREF, 'javascript'), ('jssplit.gpx', gf.JS_HREF_SPLIT, 'javascript'),
                                 ('data.gpx', gf.DATA_HREF, 'data'), ('onload.gpx', gf.EVENT_ATTR, 'onload'),
                                 ('pi.gpx', gf.PI_INSIDE, 'processing instruction'), ('enc.gpx', gf.DECLARED_OTHER_ENCODING, 'utf-8')):
            with self.subTest(name):
                with self.assertRaises(self.gpx.GpxError) as cm:
                    self.inspect(name, text)
                self.assertIn(word, str(cm.exception).lower())

    def test_accepts_extensions_schema_attributes_and_cdata_from_real_tools(self):
        for name, text in (('garmin.gpx', gf.GARMIN_EXTENSIONS), ('xsi.gpx', gf.XSI_SCHEMA), ('cdata.gpx', gf.CDATA_DESC)):
            with self.subTest(name):
                info = self.inspect(name, text)
                self.assertEqual(len(info['tracks']), 1)

    def test_extracted_element_reproduces_the_chosen_track_whatever_the_root_tag_looks_like(self):
        for name, text in (('gt.gpx', gf.ROOT_GT_IN_ATTR), ('comment.gpx', gf.ROOT_AFTER_COMMENT),
                           ('prefixed.gpx', gf.ROOT_PREFIXED), ('nodecl.gpx', gf.ROOT_NO_DECL)):
            path = self.write(name, text)
            info = self.gpx.inspect(path)
            for choice in ('trk:0', 'trk:1'):
                with self.subTest(name=name, choice=choice):
                    cand = self.gpx.select(info, choice)
                    out = self.gpx.extract_bytes(path, cand)
                    # the published document passes the same inspection as a whole and holds exactly the chosen geometry
                    got = self.gpx.candidates(self.gpx.inspect_bytes(out, name))
                    self.assertEqual(len(got), 1)
                    self.assertEqual(got[0]['segments'], cand['segments'])
                    self.assertTrue(out.startswith(b'<?xml'))

    def test_a_utf8_byte_order_mark_is_accepted_and_an_extract_stays_well_formed(self):
        for name, text in (('bom-decl.gpx', gf.ROOT_GT_IN_ATTR), ('bom-nodecl.gpx', gf.ROOT_NO_DECL)):
            path = os.path.join(self.tmp, name)
            with open(path, 'wb') as fh:
                fh.write(gf.BOM + text.encode('utf-8'))
            info = self.gpx.inspect(path)
            self.assertEqual(len(info['tracks']), 2)
            for choice in ('trk:0', 'trk:1'):
                with self.subTest(name=name, choice=choice):
                    cand = self.gpx.select(info, choice)
                    out = self.gpx.extract_bytes(path, cand)
                    self.assertTrue(out.startswith(b'<?xml'), out[:20])
                    self.assertEqual(out.count(b'<?xml'), 1)
                    got = self.gpx.candidates(self.gpx.inspect_bytes(out, name))
                    self.assertEqual([c['segments'] for c in got], [cand['segments']])

    def test_printable_keeps_file_text_on_one_line_escaped_bounded_and_quoted(self):
        p = self.gpx.printable
        self.assertEqual(p('North approach'), '"North approach"')
        self.assertEqual(p('a\nb\tc'), '"a b c"')
        self.assertEqual(p('say "hi" \\ there'), '"say \\"hi\\" \\\\ there"')
        got = p('x\x1b[31mred\x07\u202e\u200b\u2028end')
        for ch in ('\x1b', '\x07', '\u202e', '\u200b', '\u2028'):
            self.assertNotIn(ch, got)
        self.assertIn('\\u001b', got)
        self.assertIn('\\u202e', got)
        long = p('y' * 500, 40)
        self.assertEqual(len(long), 42)                      # 40 characters and the two quotes
        self.assertTrue(long.endswith('…"'))
        self.assertEqual(self.gpx.printable_name('sat'), 'sat')
        self.assertNotIn('\u200d', self.gpx.printable_name('a\u200db'))

    def test_contents_files_every_element_and_attribute_somewhere(self):
        c = self.inspect('hostile.gpx', gf.HOSTILE)['contains']
        self.assertEqual(c['other'], ['bar', 'trk'])         # an unknown element, and a track hidden inside a waypoint
        self.assertEqual(c['attributes'], ['k'])
        self.assertEqual(c['point_fields'], ['sat'])
        self.assertEqual(c['point_names'], 1)
        self.assertIs(c['text'], True)
        self.assertEqual(c['waypoint_names'], [])
        self.assertEqual(len(c['names']), 1)                 # the forged name, as text: escaping is the printer's job
        self.assertIn('\n', c['names'][0])
        plain = self.inspect('single.gpx', gf.SINGLE)['contains']
        self.assertEqual((plain['other'], plain['attributes'], plain['point_fields'], plain['point_names'], plain['text']),
                         ([], [], [], 0, False))
        self.assertEqual(plain['creator'], 'synthetic fixture')
        self.assertEqual(self.inspect('xsi.gpx', gf.XSI_SCHEMA)['contains']['attributes'], ['schemaLocation'])
        personal = self.inspect('personal.gpx', gf.PERSONAL)['contains']
        self.assertEqual(personal['metadata'], ['author', 'name'])
        self.assertEqual((personal['links'], personal['descriptions'], personal['extensions'], personal['comments']), (1, 1, True, True))

    def test_describe_escapes_a_candidates_name(self):
        info = self.inspect('hostile.gpx', gf.HOSTILE)
        text = self.gpx.describe(self.gpx.candidates(info)[0])
        self.assertNotIn('\n', text)
        self.assertNotIn('\u202e', text)
        self.assertTrue(text.startswith('trk:0 "ok'))

    def test_rejects_malformed_xml(self):
        with self.assertRaises(self.gpx.GpxError):
            self.inspect('broken.gpx', gf.NOT_XML)

    def test_rejects_a_root_that_is_not_gpx(self):
        with self.assertRaises(self.gpx.GpxError) as cm:
            self.inspect('route.kml', gf.NON_GPX_ROOT)
        self.assertIn('gpx', str(cm.exception).lower())

    def test_rejects_coordinates_out_of_range(self):
        for name, text in (('lat.gpx', gf.LAT_OUT), ('lon.gpx', gf.LON_OUT)):
            with self.subTest(file=name):
                with self.assertRaises(self.gpx.GpxError):
                    self.inspect(name, text)

    def test_rejects_a_missing_or_non_finite_coordinate(self):
        for name, text in (('nolat.gpx', gf.MISSING_LAT), ('nan.gpx', gf.NAN_LAT), ('inf.gpx', gf.INF_LON)):
            with self.subTest(file=name):
                with self.assertRaises(self.gpx.GpxError):
                    self.inspect(name, text)

    def test_rejects_a_non_numeric_or_non_finite_elevation(self):
        for name, text in (('ele.gpx', gf.BAD_ELE), ('infele.gpx', gf.INF_ELE)):
            with self.subTest(file=name):
                with self.assertRaises(self.gpx.GpxError):
                    self.inspect(name, text)

    def test_rejects_a_file_over_max_bytes(self):
        path = self.write('single.gpx', gf.SINGLE)
        with mock.patch.object(self.gpx, 'MAX_BYTES', 200):
            with self.assertRaises(self.gpx.GpxError):
                self.gpx.inspect(path)
        self.gpx.inspect(path)   # the real limit admits it

    def test_rejects_more_than_max_points(self):
        path = self.write('single.gpx', gf.SINGLE)
        with mock.patch.object(self.gpx, 'MAX_POINTS', 11):
            with self.assertRaises(self.gpx.GpxError):
                self.gpx.inspect(path)
        with mock.patch.object(self.gpx, 'MAX_POINTS', 12):
            self.gpx.inspect(path)

    def test_errors_are_value_errors(self):
        with self.assertRaises(ValueError):
            self.inspect('doctype.gpx', gf.DOCTYPE)


# ---------------------------------------------------------------- candidates

class CandidateTests(GpxFixture):

    def test_single_track_is_one_candidate(self):
        c = self.gpx.candidates(self.inspect('single.gpx', gf.SINGLE))
        self.assertEqual(len(c), 1)
        self.assertEqual((c[0]['type'], c[0]['index'], c[0]['name'], c[0]['points']), ('trk', 0, 'Synthetic ridge', 12))
        self.assertEqual(len(c[0]['segments']), 1)
        self.assertPoints(c[0]['segments'][0], gf.SEG_A)

    def test_tracks_first_then_routes_with_per_type_indices(self):
        c = self.gpx.candidates(self.inspect('alts.gpx', gf.ALTERNATIVES))
        self.assertEqual([(x['type'], x['index'], x['name'], x['points']) for x in c],
                         [('trk', 0, 'North approach', 6), ('trk', 1, 'South approach', 7), ('rte', 0, 'Descent', 5)])
        self.assertEqual([len(s) for s in c[1]['segments']], [4, 3])
        self.assertEqual(len(c[2]['segments']), 1)   # a route is one segment
        self.assertPoints(c[2]['segments'][0], gf.RTE_D)

    def test_a_track_without_points_is_not_a_candidate(self):
        c = self.gpx.candidates(self.inspect('empty-trk.gpx', gf.EMPTY_TRACK_AND_ROUTE))
        self.assertEqual([(x['type'], x['index']) for x in c], [('rte', 0)])

    def test_waypoint_only_has_no_candidates(self):
        self.assertEqual(self.gpx.candidates(self.inspect('wpts.gpx', gf.WAYPOINT_ONLY)), [])


# ---------------------------------------------------------------- select

class SelectTests(GpxFixture):

    def test_single_candidate_needs_no_choice(self):
        info = self.inspect('single.gpx', gf.SINGLE)
        self.assertEqual(self.gpx.select(info)['points'], 12)
        self.assertEqual(self.gpx.select(info, None)['name'], 'Synthetic ridge')
        self.assertEqual(self.gpx.select(info, 'trk:0')['name'], 'Synthetic ridge')

    def test_the_only_route_beside_an_empty_track_is_selected_alone(self):
        c = self.gpx.select(self.inspect('empty-trk.gpx', gf.EMPTY_TRACK_AND_ROUTE))
        self.assertEqual((c['type'], c['index']), ('rte', 0))

    def test_several_candidates_without_a_choice_raise_selection_needed_listing_them(self):
        info = self.inspect('alts.gpx', gf.ALTERNATIVES)
        with self.assertRaises(self.gpx.SelectionNeeded) as cm:
            self.gpx.select(info)
        msg = str(cm.exception)
        for want in ('trk:0', 'trk:1', 'rte:0', 'North approach', 'South approach', 'Descent', '6', '7', '5'):
            self.assertIn(want, msg)
        self.assertIsInstance(cm.exception, ValueError)

    def test_choice_picks_a_track_or_a_route(self):
        info = self.inspect('alts.gpx', gf.ALTERNATIVES)
        south = self.gpx.select(info, 'trk:1')
        self.assertEqual((south['type'], south['index'], south['name'], south['points']), ('trk', 1, 'South approach', 7))
        self.assertEqual(len(south['segments']), 2)
        descent = self.gpx.select(info, 'rte:0')
        self.assertEqual((descent['type'], descent['index'], descent['name']), ('rte', 0, 'Descent'))
        self.assertPoints(descent['segments'][0], gf.RTE_D)

    def test_a_choice_not_in_the_file_raises_selection_needed(self):
        info = self.inspect('alts.gpx', gf.ALTERNATIVES)
        for choice in ('trk:2', 'rte:1', 'trk:99'):
            with self.subTest(choice=choice):
                with self.assertRaises(self.gpx.SelectionNeeded) as cm:
                    self.gpx.select(info, choice)
                self.assertIn('trk:0', str(cm.exception))

    def test_a_malformed_choice_is_a_gpx_error(self):
        info = self.inspect('alts.gpx', gf.ALTERNATIVES)
        for choice in ('foo', 'trk', 'trk:x', '0', 'wpt:0'):
            with self.subTest(choice=choice):
                with self.assertRaises(self.gpx.GpxError):
                    self.gpx.select(info, choice)

    def test_no_candidate_raises_no_route(self):
        with self.assertRaises(self.gpx.NoRoute):
            self.gpx.select(self.inspect('wpts.gpx', gf.WAYPOINT_ONLY))
        with self.assertRaises(self.gpx.NoRoute):
            self.gpx.select(self.inspect('wpts.gpx', gf.WAYPOINT_ONLY), 'trk:0')
        empty = self.inspect('empty.gpx', gf.gpx(gf.trk([[]], 'Nothing')))
        with self.assertRaises(self.gpx.NoRoute):
            self.gpx.select(empty)


# ---------------------------------------------------------------- measure

class MeasureTests(GpxFixture):

    def measure(self, name, text, choice=None):
        return self.gpx.measure(self.gpx.select(self.inspect(name, text), choice)['segments'])

    def test_reference_hysteresis_agrees_with_tracks_compute_stats(self):
        """The fixture module's own gain/loss (what the measure tests compare against) matches the existing helper."""
        self.assertEqual(gf.ref_gain_loss(gf.ELES_A), (57, 7))
        pts = [(p[0], p[1], p[2], None) for p in gf.SEG_A]
        st = tracks.compute_stats(pts)
        self.assertEqual((st['gain_m'], st['loss_m']), (57, 7))
        self.assertDistance(st['distance_km'], gf.poly_km(gf.SEG_A))

    def test_result_keys(self):
        m = self.measure('single.gpx', gf.SINGLE)
        self.assertEqual(set(m), {'distance_km', 'gain_m', 'loss_m', 'high_m', 'low_m', 'elevation', 'times', 'points', 'segments', 'sparse'})

    def test_single_track_against_haversine_and_hysteresis(self):
        m = self.measure('single.gpx', gf.SINGLE)
        self.assertDistance(m['distance_km'], gf.poly_km(gf.SEG_A))
        self.assertEqual((m['gain_m'], m['loss_m']), gf.ref_gain_loss(gf.ELES_A))
        self.assertIsInstance(m['gain_m'], int)
        self.assertIsInstance(m['loss_m'], int)
        self.assertEqual((m['high_m'], m['low_m']), (2050, 2000))
        self.assertEqual(m['elevation'], 'full')
        self.assertTrue(m['times'])
        self.assertEqual((m['points'], m['segments']), (12, 1))
        self.assertFalse(m['sparse'])

    def test_sparse_means_fewer_than_ten_points(self):
        self.assertIs(self.measure('nine.gpx', gf.NINE)['sparse'], True)
        self.assertIs(self.measure('ten.gpx', gf.TEN)['sparse'], False)
        self.assertEqual((self.measure('nine.gpx', gf.NINE)['points'], self.measure('ten.gpx', gf.TEN)['points']), (9, 10))

    def test_gain_is_measured_per_segment_never_across_a_gap(self):
        m = self.measure('jump.gpx', gf.JUMP)
        per_segment = [gf.ref_gain_loss([p[2] for p in seg]) for seg in gf.SEGS_J]
        self.assertEqual((m['gain_m'], m['loss_m']), (sum(g for g, _l in per_segment), sum(l for _g, l in per_segment)))
        self.assertEqual(m['gain_m'], 40)
        joined = gf.ref_gain_loss([p[2] for seg in gf.SEGS_J for p in seg])
        self.assertEqual(joined[0], 55)                      # what bridging the gap would have claimed
        self.assertNotEqual(m['gain_m'], joined[0])
        self.assertEqual(m['segments'], 2)

    def test_distance_has_two_decimals(self):
        m = self.measure('single.gpx', gf.SINGLE)
        self.assertEqual(m['distance_km'], round(m['distance_km'], 2))
        self.assertIsInstance(m['distance_km'], float)

    def test_three_segments_sum_their_own_lengths_and_bridge_nothing(self):
        m = self.measure('multi.gpx', gf.MULTISEG)
        own = sum(gf.poly_km(s) for s in gf.SEGS_M)
        joined = gf.poly_km([p for s in gf.SEGS_M for p in s])
        self.assertGreater(joined, own * 3)   # the gaps are several kilometres: bridging them would be obvious
        self.assertDistance(m['distance_km'], own)
        self.assertLess(m['distance_km'], joined / 2)
        self.assertEqual((m['gain_m'], m['loss_m']), (35, 20))
        self.assertEqual((m['high_m'], m['low_m']), (2020, 2000))
        self.assertEqual((m['points'], m['segments']), (14, 3))
        self.assertEqual(m['elevation'], 'full')
        self.assertFalse(m['sparse'])

    def test_route_only(self):
        m = self.measure('route.gpx', gf.ROUTE_ONLY)
        self.assertDistance(m['distance_km'], gf.poly_km(gf.RTE_PTS))
        self.assertEqual((m['gain_m'], m['loss_m']), (100, 0))
        self.assertEqual((m['high_m'], m['low_m']), (2600, 2500))
        self.assertFalse(m['times'])
        self.assertEqual((m['points'], m['segments']), (11, 1))

    def test_no_elevation_means_no_gain_and_no_heights(self):
        m = self.measure('noele.gpx', gf.NO_ELE)
        self.assertDistance(m['distance_km'], gf.poly_km(gf.SEG_NO_ELE))
        for k in ('gain_m', 'loss_m', 'high_m', 'low_m'):
            self.assertIsNone(m[k], k)
        self.assertEqual(m['elevation'], 'none')
        self.assertTrue(m['times'])

    def test_partial_elevation_means_no_gain_but_known_heights(self):
        m = self.measure('partial.gpx', gf.PARTIAL_ELE)
        self.assertIsNone(m['gain_m'])
        self.assertIsNone(m['loss_m'])
        self.assertEqual((m['high_m'], m['low_m']), (2050, 2000))
        self.assertEqual(m['elevation'], 'partial')
        self.assertEqual(m['points'], 12)

    def test_no_timestamps(self):
        m = self.measure('notime.gpx', gf.NO_TIME)
        self.assertFalse(m['times'])
        self.assertEqual(m['elevation'], 'full')
        self.assertEqual((m['gain_m'], m['loss_m']), gf.ref_gain_loss(gf.ELES_A))

    def test_sparse_flag_for_fewer_than_ten_points(self):
        m = self.measure('sparse.gpx', gf.SPARSE)
        self.assertTrue(m['sparse'])
        self.assertEqual(m['points'], 5)
        self.assertDistance(m['distance_km'], gf.poly_km(gf.SEG_SPARSE))
        self.assertEqual((m['gain_m'], m['loss_m']), (40, 0))
        self.assertFalse(self.measure('single.gpx', gf.SINGLE)['sparse'])

    def test_alternative_measured_alone(self):
        m = self.measure('alts.gpx', gf.ALTERNATIVES, 'trk:1')
        self.assertDistance(m['distance_km'], gf.poly_km(gf.TRK_S1) + gf.poly_km(gf.TRK_S2))
        self.assertEqual((m['points'], m['segments']), (7, 2))
        self.assertEqual((m['gain_m'], m['loss_m']), (30, 0))


# ---------------------------------------------------------------- as_tracks

class AsTracksTests(GpxFixture):

    def setUp(self):
        super().setUp()
        import mapkit
        self.mapkit = mapkit

    def raw(self, tr):
        return [(p[0], p[1], p[2], p[3]) for p in tr.raw]

    def test_one_track_per_segment_in_order(self):
        trs = self.gpx.as_tracks(self.write('multi.gpx', gf.MULTISEG), 'multi', 'HIK')
        self.assertEqual(len(trs), 3)
        for tr, seg in zip(trs, gf.SEGS_M):
            self.assertIsInstance(tr, self.mapkit.Track)
            self.assertEqual((tr.key, tr.cat), ('multi', 'HIK'))
            self.assertPoints(self.raw(tr), seg)
            self.assertDistance(tr.total / 1000.0, gf.poly_km(seg))

    def test_a_route_is_one_track(self):
        trs = self.gpx.as_tracks(self.write('route.gpx', gf.ROUTE_ONLY), 'r', 'SKI')
        self.assertEqual(len(trs), 1)
        self.assertPoints(self.raw(trs[0]), gf.RTE_PTS)

    def test_a_single_track_file(self):
        trs = self.gpx.as_tracks(self.write('single.gpx', gf.SINGLE), 's', 'HIK')
        self.assertEqual(len(trs), 1)
        self.assertPoints(self.raw(trs[0]), gf.SEG_A)

    def test_never_joins_segments_across_candidates(self):
        """Whatever is drawn for a file with several candidates, each Track is exactly one of the file's segments."""
        segments = [gf.TRK_N, gf.TRK_S1, gf.TRK_S2, gf.RTE_D]
        trs = self.gpx.as_tracks(self.write('alts.gpx', gf.ALTERNATIVES), 'a', 'HIK')
        self.assertTrue(trs)
        for tr in trs:
            got = self.raw(tr)
            match = [seg for seg in segments if len(seg) == len(got) and all(abs(a[0] - float(b[0])) < 1e-6 and abs(a[1] - float(b[1])) < 1e-6 for a, b in zip(got, seg))]
            self.assertEqual(len(match), 1, 'a drawn Track is not one of the file\'s segments: %r' % (got[:2],))

    def test_waypoint_only_draws_nothing(self):
        try:
            trs = self.gpx.as_tracks(self.write('wpts.gpx', gf.WAYPOINT_ONLY), 'w', 'HIK')
        except self.gpx.NoRoute:
            return
        self.assertEqual(trs, [])

    def test_unsafe_files_are_refused(self):
        with self.assertRaises(self.gpx.GpxError):
            self.gpx.as_tracks(self.write('doctype.gpx', gf.DOCTYPE), 'd', 'HIK')


if __name__ == '__main__':
    unittest.main()
