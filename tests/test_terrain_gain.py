"""Terrain gain for tick-list goals whose GPX has no elevation, or only some (2026-10-26).

A goal's index.md stats stay the numbers measured from its own file (gpxroute.measure: no elevation, no gain). Where
the file has no elevation, or only some, tools/render.py estimates the gain, loss, high and low of the ground under the
line from AWS Terrain Tiles (gpxroute.measure_terrain, render.terrain_block) and writes them to
rendered/trips/<slug>/meta.json under 'terrain'; the card (core.goal_stats_line) and the goal page (report.goal_strip)
show them where the file has none, each marked '(terrain)', and the strip note says they come from terrain data.

What is pinned, with synthetic lines (tests/gpx_fixtures.py) and a synthetic terrain: no tile is read from disk or
fetched, geo.get_tile is replaced by a function of the tile's position (a slope that rises to the north, which the
bilinear sampling reproduces exactly), as tests/test_render_goals.py replaces the drawing and OpenStreetMap functions.
- gpxroute.along and measure_terrain: the sample spacing, the 3 m hysteresis, each segment measured on its own;
- renderkey.file_elevation, wants_terrain and terrain_reason;
- render.terrain_block at gpxroute.TERRAIN_ZOOM, render_single writing it for a goal without elevation (and not for one
  with full elevation or a report), render_trip adding it alone to a render made before it with every map left as it
  was, pending_reason and --status naming it without fetching anything;
- core.goal_heights, goal_stats_line and report.goal_strip: the file first, the terrain marked, the note;
- checks: the warning for a published goal whose meta.json lacks its estimate.
"""
import array
import importlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import geo  # noqa: E402
import gpxroute  # noqa: E402
import renderkey  # noqa: E402
from sitegen import core  # noqa: E402

import gpx_fixtures as gf  # noqa: E402
import helpers  # noqa: E402
from helpers import Doc  # noqa: E402
import test_checks_site_maps as site_maps  # noqa: E402  (its fixture, subclassed below; its tests stay in its module)
import test_render_goals as render_goals  # noqa: E402

Z = gpxroute.TERRAIN_ZOOM
SLOPE = 0.5     # metres of synthetic terrain per pixel row at TERRAIN_ZOOM, rising to the north
BASE = 2000.0


def pixel_row(lat, lon):
    """The row DEM.sample reads a point at: the tile pixel grid's y, less the half pixel it centres on."""
    return geo.tile_xy(lat, lon, Z)[1] * 256 - 0.5


Y0 = pixel_row(gf.SEG_NO_ELE[0][0], gf.SEG_NO_ELE[0][1])


def terrain_at(lat, lon):
    """The synthetic ground's height: BASE at the fixtures' first point, SLOPE more for every pixel row to the north."""
    return BASE + SLOPE * (Y0 - pixel_row(lat, lon))


class SyntheticTiles(object):
    """A stand-in for geo.get_tile: a tile of the synthetic terrain, built from its position alone; every call recorded."""

    def __init__(self):
        self.calls = []
        self.tiles = {}

    def __call__(self, z, x, y):
        self.calls.append((z, x, y))
        if (z, x, y) not in self.tiles:
            t = array.array('d', [0.0]) * 65536
            for py in range(256):
                v = BASE + SLOPE * (Y0 - (y * 256 + py))
                for px in range(256):
                    t[py * 256 + px] = v
            self.tiles[(z, x, y)] = t
        return self.tiles[(z, x, y)]


def by_lat(table):
    """A sample function for measure_terrain: the height given for each latitude in table (vertices only)."""
    return lambda lat, lon: table[round(lat, 6)]


EVERY_VERTEX = 1e9   # a step longer than any edge: along() returns the points of the segment and nothing between


# ---------------------------------------------------------------- gpxroute

class AlongTests(unittest.TestCase):

    def test_every_point_is_kept_and_no_two_samples_are_farther_apart_than_the_step(self):
        seg = gf.SEG_NO_ELE                                 # 12 points about 111 m apart
        pts = gpxroute.along(seg, 20.0)
        for p in seg:
            self.assertIn((p[0], p[1]), pts)
        gaps = [geo.hav(a, b) for a, b in zip(pts, pts[1:])]
        self.assertLessEqual(max(gaps), 20.0 + 1e-6)
        self.assertGreater(min(gaps), 15.0)                 # evenly spaced: 111 m in six steps of about 18.5 m
        self.assertEqual(len(pts), 1 + sum(int(math.ceil(geo.hav(a, b) / 20.0)) for a, b in zip(seg, seg[1:])))

    def test_points_closer_than_the_step_are_sampled_as_they_are(self):
        seg = gf.line(38.9, -120.1, 5, dlat=0.0001)        # about 11 m apart
        self.assertEqual(gpxroute.along(seg, 20.0), [(p[0], p[1]) for p in seg])
        self.assertEqual(gpxroute.along(gf.SEG_NO_ELE, EVERY_VERTEX), [(p[0], p[1]) for p in gf.SEG_NO_ELE])

    def test_the_default_step_is_the_terrain_step(self):
        self.assertEqual(gpxroute.along(gf.SEG_NO_ELE), gpxroute.along(gf.SEG_NO_ELE, gpxroute.TERRAIN_STEP_M))


class MeasureTerrainTests(unittest.TestCase):

    def test_gain_loss_high_and_low_with_the_3_m_hysteresis(self):
        seg = gf.line(38.9, -120.1, 8)
        heights = [2000, 2002, 2000, 2002, 2010, 2008, 2001, 2001]   # wiggles under 3 m are not counted
        got = gpxroute.measure_terrain([seg], by_lat({round(p[0], 6): h for p, h in zip(seg, heights)}), EVERY_VERTEX)
        self.assertEqual(got, {'gain_m': 10, 'loss_m': 9, 'high_m': 2010, 'low_m': 2000, 'samples': 8})

    def test_each_segment_is_measured_on_its_own_and_the_gap_is_never_bridged(self):
        # 10,000 m a degree of latitude: 10 m between two points of a segment, 160 m and 260 m across the two gaps
        got = gpxroute.measure_terrain(gf.SEGS_M, lambda lat, lon: lat * 10000.0, EVERY_VERTEX)
        self.assertEqual((got['gain_m'], got['loss_m']), (40 + 40 + 30, 0))
        joined = gpxroute.measure_terrain([[p for s in gf.SEGS_M for p in s]], lambda lat, lon: lat * 10000.0, EVERY_VERTEX)
        self.assertEqual(joined['gain_m'], 110 + 160 + 260)     # what bridging would have counted
        self.assertEqual((got['high_m'], got['low_m']), (int(round(38.953 * 10000)), int(round(38.900 * 10000))))

    def test_the_elevations_in_the_file_are_not_read(self):
        a = gpxroute.measure_terrain([gf.SEG_PARTIAL], terrain_at)
        b = gpxroute.measure_terrain([gf.SEG_NO_ELE], terrain_at)
        self.assertEqual(a, b)

    def test_single_points_and_empty_segments_give_nothing(self):
        self.assertIsNone(gpxroute.measure_terrain([], terrain_at))
        self.assertIsNone(gpxroute.measure_terrain([[], gf.SEG_NO_ELE[:1]], terrain_at))
        one = gpxroute.measure_terrain([gf.SEG_NO_ELE[:1], gf.SEG_NO_ELE], terrain_at)
        self.assertEqual(one, gpxroute.measure_terrain([gf.SEG_NO_ELE], terrain_at))

    def test_measure_of_the_file_is_unchanged(self):
        # measure() shares the hysteresis now (gpxroute._climb): the same numbers as before for the fixtures with elevation
        self.assertEqual((gpxroute.measure([gf.SEG_A])['gain_m'], gpxroute.measure([gf.SEG_A])['loss_m']), (57, 7))
        self.assertEqual(gpxroute.measure(gf.SEGS_J)['gain_m'], 40)
        self.assertIsNone(gpxroute.measure([gf.SEG_NO_ELE])['gain_m'])


# ---------------------------------------------------------------- renderkey

class WantsTerrainTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name

    def trip(self, slug, gpx_text=None, **meta):
        meta.setdefault('activity', 'hike')
        folder = helpers.make_trip(self.dir, slug, track=gpx_text is not None, **meta)
        if gpx_text is not None:
            with open(os.path.join(folder, 'track.gpx'), 'w', encoding='utf-8') as fh:
                fh.write(gpx_text)
        return content.load_trip(folder)

    def test_how_much_elevation_a_goals_file_has(self):
        cases = [(self.trip('none', gf.NO_ELE, kind='planned'), 'none', True),
                 (self.trip('partial', gf.PARTIAL_ELE, kind='planned'), 'partial', True),
                 (self.trip('full', gf.SINGLE, kind='planned'), 'full', False),
                 (self.trip('route', gf.ROUTE_ONLY, kind='planned'), 'full', False),
                 (self.trip('idea', None, kind='planned'), None, False),
                 (self.trip('report', gf.NO_ELE, date='2026-08-01'), None, False),
                 (self.trip('broken', gf.NOT_XML, kind='planned'), None, False)]
        for t, elevation, wants in cases:
            with self.subTest(slug=t['slug']):
                self.assertEqual(renderkey.file_elevation(t), elevation)
                self.assertIs(renderkey.wants_terrain(t), wants)

    def test_terrain_reason(self):
        none = self.trip('none', gf.NO_ELE, kind='planned')
        partial = self.trip('partial', gf.PARTIAL_ELE, kind='planned')
        full = self.trip('full', gf.SINGLE, kind='planned')
        self.assertEqual(renderkey.terrain_reason(none, {'maps': {}}), 'no terrain estimate of the gain yet (the file has no elevation)')
        self.assertEqual(renderkey.terrain_reason(partial, {'maps': {}}),
                         'no terrain estimate of the gain yet (the file has elevation for only part of the line)')
        current = {'terrain': {'method': gpxroute.TERRAIN_METHOD, 'gain_m': 1}}
        self.assertIsNone(renderkey.terrain_reason(none, current))
        self.assertEqual(renderkey.terrain_reason(none, {'terrain': {'method': 'ticklist-terrain-0'}}),
                         'terrain estimate made by an older method (ticklist-terrain-0, now %s)' % gpxroute.TERRAIN_METHOD)
        self.assertIsNone(renderkey.terrain_reason(full, {'maps': {}}))
        self.assertIsNone(renderkey.terrain_reason(full, {'terrain': {'method': 'ticklist-terrain-0'}}))

    def test_the_hash_of_a_render_does_not_change(self):
        # the estimate is added to a render, never a reason to draw its maps again
        t = self.trip('none', gf.NO_ELE, kind='planned')
        self.assertNotIn('terrain', renderkey.input_fields(t))
        self.assertEqual(sorted(renderkey.input_parts(t)), ['fields', 'files', 'version'])


# ---------------------------------------------------------------- render.py

class RenderTerrainFixture(render_goals.RenderGoalsFixture):
    """render_goals' fixture (render.OUT in a temp dir, render_map / fetch_osm / optimize_images stubbed) with the tile,
    glyph and chart drawings stubbed too, and geo.get_tile replaced by the synthetic terrain."""

    def setUp(self):
        super().setUp()
        for name in ('render_tile', 'render_glyph', 'render_profile', 'render_sparkline', 'render_speed_chart'):
            p = mock.patch.object(self.render, name, side_effect=lambda *a, **k: {})
            p.start()
            self.addCleanup(p.stop)
        self.tiles = SyntheticTiles()
        p = mock.patch.object(geo, 'get_tile', self.tiles)
        p.start()
        self.addCleanup(p.stop)

    def meta(self, t):
        with open(os.path.join(t['rendered'], 'meta.json'), encoding='utf-8') as fh:
            return json.load(fh)


class RenderTerrainTests(RenderTerrainFixture):

    def test_the_block_holds_the_estimate_and_what_made_it(self):
        goal = self.trip('flat-file', gf.NO_ELE, kind='planned')
        block = self.render.terrain_block(goal)
        rise = terrain_at(*gf.SEG_NO_ELE[-1][:2]) - BASE
        self.assertGreater(rise, 20)                                   # the line climbs to the north
        self.assertLessEqual(rise - 3, block['gain_m'])                # the hysteresis may leave under 3 m uncounted
        self.assertLessEqual(block['gain_m'], round(rise))
        self.assertEqual((block['loss_m'], block['low_m'], block['high_m']), (0, int(BASE), int(round(BASE + rise))))
        self.assertEqual({k: block[k] for k in ('method', 'source', 'zoom', 'step_m', 'file_elevation')},
                         {'method': gpxroute.TERRAIN_METHOD, 'source': 'AWS Terrain Tiles', 'zoom': Z,
                          'step_m': gpxroute.TERRAIN_STEP_M, 'file_elevation': 'none'})
        self.assertEqual(block['samples'], len(gpxroute.along(gf.SEG_NO_ELE)))
        self.assertTrue(self.tiles.calls)
        self.assertEqual({c[0] for c in self.tiles.calls}, {Z})       # read at the terrain zoom alone

    def test_no_block_for_a_goal_with_full_elevation_or_a_report(self):
        self.assertIsNone(self.render.terrain_block(self.trip('ele-file', gf.SINGLE, kind='planned')))
        self.assertIsNone(self.render.terrain_block(self.trip('walked', gf.NO_ELE, date='2026-08-01')))
        self.assertEqual(self.tiles.calls, [])

    def test_a_goal_render_writes_it_and_a_goal_with_full_elevation_gets_none(self):
        none = self.trip('flat-file', gf.NO_ELE, kind='planned')
        partial = self.trip('half-file', gf.PARTIAL_ELE, kind='planned')
        full = self.trip('ele-file', gf.SINGLE, kind='planned')
        for t in (none, partial, full):
            self.assertIs(self.render.render_trip(t), True)
        self.assertEqual(self.meta(none)['terrain']['file_elevation'], 'none')
        self.assertEqual(self.meta(partial)['terrain']['file_elevation'], 'partial')
        self.assertEqual(self.meta(partial)['terrain']['gain_m'], self.meta(none)['terrain']['gain_m'])   # the same line
        self.assertNotIn('terrain', self.meta(full))
        for t in (none, partial, full):
            self.assertIsNone(self.render.pending_reason(t))
            self.assertIs(self.render.render_trip(t), False)          # nothing left to do

    def test_a_render_made_before_gets_the_estimate_alone(self):
        goal = self.trip('flat-file', gf.NO_ELE, kind='planned')
        self.render.render_trip(goal)
        meta = self.meta(goal)
        old = dict(meta)
        del old['terrain']
        with open(os.path.join(goal['rendered'], 'meta.json'), 'w') as fh:
            json.dump(old, fh)
        self.assertEqual(self.render.pending_reason(goal), 'no terrain estimate of the gain yet (the file has no elevation)')
        self.assertEqual(self.render.pending_trips([goal]), [goal])
        del self.maps[:]
        with mock.patch.object(self.render, 'render_single', side_effect=AssertionError('the maps were drawn again')):
            self.assertIs(self.render.render_trip(goal), True)
        self.assertEqual(self.maps, [])
        again = self.meta(goal)
        self.assertEqual({k: v for k, v in again.items() if k != 'terrain'}, old)       # every other key as it was
        self.assertEqual({k: v for k, v in again['terrain'].items() if k != 'date'},
                         {k: v for k, v in meta['terrain'].items() if k != 'date'})
        self.assertEqual(os.listdir(goal['rendered']), ['meta.json'])                  # no temp file left beside it
        self.assertIn('terrain  flat-file', self.printed.getvalue())
        self.assertIsNone(self.render.pending_reason(goal))
        self.assertIs(self.render.render_trip(goal), False)

    def test_an_estimate_by_an_older_method_is_made_again(self):
        goal = self.trip('flat-file', gf.NO_ELE, kind='planned')
        self.render.render_trip(goal)
        meta = self.meta(goal)
        meta['terrain'] = dict(meta['terrain'], method='ticklist-terrain-0', gain_m=1)
        with open(os.path.join(goal['rendered'], 'meta.json'), 'w') as fh:
            json.dump(meta, fh)
        self.assertIn('older method', self.render.pending_reason(goal))
        self.assertIs(self.render.render_trip(goal), True)
        self.assertEqual(self.meta(goal)['terrain']['method'], gpxroute.TERRAIN_METHOD)
        self.assertGreater(self.meta(goal)['terrain']['gain_m'], 1)

    def test_status_names_it_and_fetches_nothing(self):
        goal = self.trip('flat-file', gf.NO_ELE, kind='planned')
        self.render.render_trip(goal)
        meta = self.meta(goal)
        del meta['terrain']
        with open(os.path.join(goal['rendered'], 'meta.json'), 'w') as fh:
            json.dump(meta, fh)
        said = []
        with mock.patch.object(self.render.content, 'load_all', return_value=[goal]), \
                mock.patch.object(geo, 'get_tile', side_effect=AssertionError('--status read a tile')), \
                mock.patch.object(self.render, 'site_maps_stale', return_value=None):
            self.assertEqual(self.render.status(['flat-file'], say=said.append), 1)
        self.assertEqual(said[0], '%-44s %s' % ('flat-file', 'no terrain estimate of the gain yet (the file has no elevation)'))

    def test_a_failed_tile_leaves_meta_json_as_it_was(self):
        goal = self.trip('flat-file', gf.NO_ELE, kind='planned')
        self.render.render_trip(goal)
        meta = self.meta(goal)
        del meta['terrain']
        with open(os.path.join(goal['rendered'], 'meta.json'), 'w') as fh:
            json.dump(meta, fh)
        with mock.patch.object(geo, 'get_tile', side_effect=RuntimeError('tile fetch failed')):
            with self.assertRaises(RuntimeError):
                self.render.render_trip(goal)
        self.assertEqual(self.meta(goal), meta)
        self.assertEqual(os.listdir(goal['rendered']), ['meta.json'])


# ---------------------------------------------------------------- the card and the goal page

TERRAIN = {'gain_m': 2716, 'loss_m': 2417, 'high_m': 3041, 'low_m': 1800, 'samples': 1741, 'method': gpxroute.TERRAIN_METHOD,
           'source': 'AWS Terrain Tiles', 'zoom': 13, 'step_m': 20.0, 'file_elevation': 'none', 'date': '2026-10-26'}


class GoalDisplayTests(unittest.TestCase):

    def setUp(self):
        self.report = importlib.import_module('sitegen.pages.report')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.goals = importlib.import_module('goals')

    def goal(self, slug, gpx_text=gf.NO_ELE, terrain=TERRAIN, **meta):
        """A goal loaded from a temp folder, its rendered/trips/<slug>/meta.json holding `terrain` (none when None)."""
        meta.setdefault('activity', 'hike')
        meta.setdefault('kind', 'planned')
        meta.setdefault('stats', {'distance_km': 27.94})
        folder = helpers.make_trip(os.path.join(self.dir, 'trips'), slug, track=True, **meta)
        with open(os.path.join(folder, 'track.gpx'), 'w', encoding='utf-8') as fh:
            fh.write(gpx_text)
        t = content.load_trip(folder)
        t['rendered'] = os.path.join(self.dir, 'rendered', slug)
        os.makedirs(t['rendered'])
        rmeta = {'hash': 'x', 'maps': {}, 'charts': {}}
        if terrain is not None:
            rmeta['terrain'] = terrain
        with open(os.path.join(t['rendered'], 'meta.json'), 'w') as fh:
            json.dump(rmeta, fh)
        return t

    def card_text(self, t):
        return helpers.plain_text(helpers.seen_text(Doc(core.goal_stats_line(t)).find(cls='ml')))

    def strip(self, t):
        doc = Doc(self.report.goal_strip(t))
        return [d.text() for d in doc.find('dl', cls='strip').find_all('dt')], doc.find('dl', cls='strip').text(), doc.find(cls='strip-note').text()

    def test_a_goal_without_elevation_shows_the_terrain_marked(self):
        t = self.goal('crest-line')
        self.assertEqual(core.goal_heights(t), {'gain': (2716, True), 'loss': (2417, True), 'high': (3041, True)})
        text = self.card_text(t)
        self.assertIn('≈ 17.4 MI', text)
        self.assertIn('≈ 8,911 FT GAIN (TERRAIN)', text)
        self.assertIn('≈ 2,716 M GAIN (TERRAIN)', text)            # the km side through core.U
        self.assertIn('≈ 9,977 FT HIGH POINT (TERRAIN)', text)
        self.assertNotIn('LOSS', text)                             # the card never shows a loss
        labels, values, note = self.strip(t)
        self.assertEqual(labels, ['Distance', 'Gain (terrain)', 'Loss (terrain)', 'High point (terrain)'])
        self.assertIn('8,911', values)
        self.assertIn('7,930', values)
        self.assertEqual(note, 'Approximate values from the planned route file. The file has no elevation, so the gain, loss '
                               'and high point are estimated from terrain data (AWS Terrain Tiles) under the line, not '
                               'measured from the file. The high point is the highest ground under the line, not a surveyed '
                               'summit.')

    def test_a_terrain_item_may_wrap_before_the_mark_alone(self):
        html = core.goal_stats_line(self.goal('crest-line'))
        self.assertEqual(['mi-w' in i.classes for i in Doc(html).find_all(cls='mi')], [False, True, True])
        # the only breakable spaces on the line (the separators' ', ' aside): one before each '(TERRAIN)', in miles and km
        text = re.sub(r'<[^>]+>', '', html.replace('<span class="sr">, </span>', ''))
        self.assertEqual((text.count(' '), text.count(' (TERRAIN)')), (4, 4))

    def test_a_goal_imported_without_elevation_names_its_source_and_the_terrain(self):
        t = self.goal('crest-line')
        route = {'source_sha256': '0' * 64, 'method': 'ticklist-gpx-1', 'selected': {'type': 'trk', 'index': 0, 'name': None},
                 'alternatives': 1, 'segments': 1, 'points': 12, 'elevation': 'none', 'times': True, 'waypoints': 0}
        t = dict(t, goal=dict(t['goal'], route=route, route_source=dict(t['goal']['route_source'], kind='author-drawn'),
                              route_scope='full-intended-route'))
        note = self.strip(t)[2]
        self.assertTrue(note.startswith('Approximate, measured from the planned route ('), note)
        self.assertIn('The file has no elevation, so the gain, loss and high point are estimated from terrain data', note)
        self.assertNotIn('no gain is shown', note)

    def test_partial_elevation_keeps_the_files_high_point(self):
        t = self.goal('half-line', gf.PARTIAL_ELE, terrain=dict(TERRAIN, file_elevation='partial'),
                      stats={'distance_km': 27.94, 'high_m': 2900, 'low_m': 1900})
        self.assertEqual(core.goal_heights(t), {'gain': (2716, True), 'loss': (2417, True), 'high': (2900, False)})
        text = self.card_text(t)
        self.assertIn('≈ 8,911 FT GAIN (TERRAIN)', text)
        self.assertIn('≈ 9,514 FT HIGH POINT', text)
        self.assertNotIn('HIGH POINT (TERRAIN)', text)
        labels, _values, note = self.strip(t)
        self.assertEqual(labels, ['Distance', 'Gain (terrain)', 'Loss (terrain)', 'High point'])
        self.assertIn('Elevation covers only part of the route, so the gain and loss are estimated from terrain data', note)
        self.assertIn('The high point is the highest point in the file', note)

    def test_the_files_own_numbers_win(self):
        # a goal with full elevation has no estimate; were one left in meta.json, the file's numbers are still the ones shown
        t = self.goal('ele-line', gf.SINGLE, stats={'distance_km': 12.0, 'gain_m': 640, 'loss_m': 610, 'high_m': 3200})
        self.assertEqual(core.goal_heights(t), {'gain': (640, False), 'loss': (610, False), 'high': (3200, False)})
        self.assertNotIn('TERRAIN', self.card_text(t))
        labels, _values, note = self.strip(t)
        self.assertEqual(labels, ['Distance', 'Gain', 'Loss', 'High point'])
        self.assertNotIn('terrain', note)

    def test_without_an_estimate_nothing_changes(self):
        t = self.goal('crest-line', terrain=None)
        self.assertEqual(core.goal_heights(t), {})
        self.assertEqual(self.card_text(t), '≈ 17.4 MI≈ 27.9 KM')    # the miles and the km sides of core.U, nothing else
        self.assertEqual(self.strip(t)[0], ['Distance'])
        self.assertEqual(self.strip(t)[2], 'Approximate values from the planned route file.')
        for bad in ({'gain_m': '2716', 'loss_m': 1, 'high_m': 1}, {'gain_m': 1, 'high_m': 1}, ['gain_m'], 'none'):
            with self.subTest(terrain=bad):
                shutil.rmtree(os.path.join(self.dir, 'trips', 'bad-line'), ignore_errors=True)
                shutil.rmtree(os.path.join(self.dir, 'rendered', 'bad-line'), ignore_errors=True)
                self.assertEqual(core.goal_heights(self.goal('bad-line', terrain=bad)), {})

    def test_a_report_never_shows_one(self):
        t = self.goal('walked-line', kind='trip', date='2026-08-01')
        self.assertIsNone(core.goal_terrain(t))


# ---------------------------------------------------------------- the content checks

ESTIMATE = ('content/trips/%s/index.md: no terrain estimate of the gain yet (the file has no elevation); run python3 '
            'tools/render.py %s (it writes the estimate into meta.json and leaves the maps as they are)')


class TerrainCheckTests(site_maps.RenderHashFixture):
    """A published goal whose maps are up to date (its meta.json carries the hash of the goal as it is) and whose GPX
    has no elevation: warned while meta.json has no estimate. Only the terrain lines of a run are compared here; a goal
    in the fixture's region brings the other goal and site-map lines with it."""

    def found(self):
        got = checks_run(self)
        return [text for _f, text in got if 'terrain' in text]

    def test_a_goal_without_its_estimate_is_warned_once(self):
        self.trip('syn-goal', gpx=gf.NO_ELE, kind='planned')
        self.drawn('syn-goal')
        self.assertEqual(self.found(), [ESTIMATE % ('syn-goal', 'syn-goal')])

    def test_with_its_estimate_or_with_elevation_in_the_file_nothing_is_said(self):
        self.trip('syn-goal', gpx=gf.NO_ELE, kind='planned')
        self.drawn('syn-goal', terrain=dict(TERRAIN))
        self.trip('syn-ele-goal', gpx=gf.SINGLE, kind='planned')
        self.drawn('syn-ele-goal')
        self.assertEqual(self.found(), [])

    def test_a_stale_render_is_named_first_and_an_offloaded_track_is_not_read(self):
        self.trip('syn-goal', gpx=gf.NO_ELE, kind='planned')
        self.drawn('syn-goal', hash='0' * 40)               # the maps themselves are stale: that line, not this one
        self.assertEqual(self.found(), [])
        self.drawn('syn-goal')
        with mock.patch.object(site_maps.checks, '_offloaded', return_value=True):
            self.assertEqual(self.found(), [])


def checks_run(tc):
    got = site_maps.checks.run(tc.trips, tc.home, tc.rendered, site_maps.TODAY)
    tc.assertEqual([f['text'] for f in site_maps.checks.errors(got)], [])
    return [(f['file'], f['text']) for f in site_maps.checks.warnings(got)]


if __name__ == '__main__':
    unittest.main()
