"""Phase 2T review: tools/render.py and tick-list goals.

render.py is never run here (it needs the internet and rewrites committed assets). Its helpers are called with synthetic
trips in a temp folder, and everything that draws or fetches (render_map, fetch_osm, render_single, optimize_images) is
replaced by a stub, with render.OUT pointed at the temp folder. What is pinned: a goal without a GPX is skipped instead of
crashing a full run, a route-only (rte/rtept) goal has a start and a line on its region map, and a goal with several
segments is drawn as several lines, never joined across the gaps.
"""
import contextlib
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
import warnings
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402

import gpx_fixtures as gf  # noqa: E402
import helpers  # noqa: E402

REGION = 'Synthetic Range'


class RenderGoalsFixture(unittest.TestCase):

    def setUp(self):
        try:
            self.render = importlib.import_module('render')
        except Exception as ex:   # noqa: BLE001
            self.fail('tools/render.py could not be imported: %r' % ex)
        # render.py prints its progress and leaves files for the interpreter to close: neither is under test
        quiet = contextlib.ExitStack()
        self.addCleanup(quiet.close)
        quiet.enter_context(warnings.catch_warnings())
        warnings.simplefilter('ignore', ResourceWarning)
        self.printed = quiet.enter_context(contextlib.redirect_stdout(io.StringIO()))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.trips_dir = os.path.join(tmp.name, 'trips')
        self.out = os.path.join(tmp.name, 'rendered')
        os.makedirs(self.trips_dir)
        self.maps = []        # every spec handed to the stubbed render_map

        def fake_map(spec):
            self.maps.append(spec)
            return {'png': None, 'base': None}
        for name, fn in (('OUT', self.out), ('render_map', fake_map), ('fetch_osm', lambda *a, **k: {}),
                         ('optimize_images', lambda *a, **k: None)):
            p = mock.patch.object(self.render, name, fn)
            p.start()
            self.addCleanup(p.stop)

    def trip(self, slug, gpx_text=None, **meta):
        """A synthetic trip loaded like the build loads it, with its render folder inside the temp dir."""
        meta.setdefault('activity', 'hike')
        meta.setdefault('region', REGION)
        folder = helpers.make_trip(self.trips_dir, slug, track=gpx_text is not None, **meta)
        if gpx_text is not None:
            with open(os.path.join(folder, 'track.gpx'), 'w', encoding='utf-8') as fh:
                fh.write(gpx_text)
        t = content.load_trip(folder)
        t['rendered'] = os.path.join(self.out, 'trips', slug)
        return t

    def recorded(self, slug, day):
        return self.trip(slug, gf.SINGLE, date='2026-08-%02d' % day)


class GoalWithoutRouteTests(RenderGoalsFixture):

    def test_an_idea_is_skipped_and_never_reaches_the_drawing_code(self):
        idea = self.trip('idea-only', None, kind='planned')
        self.assertIsNone(idea['track'])
        self.assertIs(self.render.no_route(idea), True)
        with mock.patch.object(self.render, 'render_single', side_effect=AssertionError('an idea was drawn')):
            self.assertIs(self.render.render_trip(idea), False)
            self.assertIs(self.render.render_trip(idea, force=True), False)
        self.assertFalse(os.path.exists(idea['rendered']))     # nothing written, not even an empty folder

    def test_a_render_left_from_an_earlier_route_is_removed(self):
        idea = self.trip('idea-only', None, kind='planned')
        os.makedirs(idea['rendered'])
        with open(os.path.join(idea['rendered'], 'meta.json'), 'w') as fh:
            json.dump({'maps': {'map-col': {}}}, fh)
        self.assertIs(self.render.render_trip(idea), False)
        self.assertFalse(os.path.exists(idea['rendered']))

    def test_a_goal_with_a_route_and_a_report_are_not_no_route(self):
        self.assertIs(self.render.no_route(self.trip('route-goal', gf.ROUTE_ONLY, kind='planned')), False)
        self.assertIs(self.render.no_route(self.recorded('walked-it', 1)), False)
        # a report without a track is not this case: only a planned goal can be an idea
        self.assertIs(self.render.no_route(self.trip('no-track-report', None, date='2026-08-02')), False)

    def test_an_idea_has_no_line_start_or_tracks_for_a_region_map(self):
        idea = self.trip('idea-only', None, kind='planned')
        self.assertEqual(self.render.goal_lines(idea), [])
        self.assertIsNone(self.render.start_of(idea))
        self.assertEqual(self.render.site_tracks(idea), [])


class RegionMapGoalTests(RenderGoalsFixture):

    def test_a_route_only_goal_has_a_start_and_one_line(self):
        goal = self.trip('route-goal', gf.ROUTE_ONLY, kind='planned')
        lines = self.render.goal_lines(goal)
        self.assertEqual(len(lines), 1)
        self.assertEqual(len(lines[0]), len(gf.RTE_PTS))
        self.assertEqual(self.render.start_of(goal), (gf.RTE_PTS[0][0], gf.RTE_PTS[0][1]))
        trs = self.render.site_tracks(goal)
        self.assertEqual(len(trs), 1)
        self.assertEqual((trs[0]['style'], trs[0]['thin'], trs[0]['key']), ('planned', True, 'route-goal'))
        self.assertEqual(trs[0]['i1'], len(trs[0]['track'].raw) - 1)
        self.assertGreater(trs[0]['i1'], 0)

    def test_a_multi_segment_goal_is_drawn_as_separate_lines(self):
        goal = self.trip('gappy-goal', gf.MULTISEG, kind='planned')
        trs = self.render.site_tracks(goal)
        self.assertEqual(len(trs), len(gf.SEGS_M))
        for tr, seg in zip(trs, gf.SEGS_M):
            raw = tr['track'].raw
            self.assertEqual((raw[0][0], raw[0][1]), (seg[0][0], seg[0][1]))        # each line starts where its segment starts
            self.assertEqual((raw[-1][0], raw[-1][1]), (seg[-1][0], seg[-1][1]))    # and ends where it ends: no bridge
        self.assertEqual(self.render.start_of(goal), (gf.SEGS_M[0][0][0], gf.SEGS_M[0][0][1]))

    def test_a_recorded_trip_is_read_as_before(self):
        rep = self.recorded('walked-it', 1)
        self.assertEqual(self.render.start_of(rep), (gf.SEG_A[0][0], gf.SEG_A[0][1]))
        trs = self.render.site_tracks(rep)
        self.assertEqual(len(trs), 1)
        self.assertEqual((trs[0]['style'], trs[0]['thin']), ('cat', False))

    def test_render_site_draws_goals_with_a_line_and_leaves_ideas_out(self):
        trips = [self.recorded('walk-%d' % i, i) for i in (1, 2, 3)]
        trips += [self.trip('route-goal', gf.ROUTE_ONLY, kind='planned'), self.trip('gappy-goal', gf.MULTISEG, kind='planned'),
                  self.trip('idea-only', None, kind='planned')]
        self.assertIs(self.render.render_site(trips, force=True), True)     # no IndexError, no TypeError
        with open(os.path.join(self.out, 'site', 'meta.json')) as fh:
            meta = json.load(fh)
        self.assertEqual(meta['regions'], [REGION])
        self.assertEqual(meta['all_regions'], [REGION])
        slug = content.slugify(REGION)
        for name in ('region-%s-desktop' % slug, 'region-%s-phone' % slug):
            self.assertIn(name, meta['maps'])
            self.assertEqual(sorted(meta['maps'][name]['trips']), ['gappy-goal', 'route-goal', 'walk-1', 'walk-2', 'walk-3'])
        self.assertEqual(len(self.maps), 2)
        for spec in self.maps:
            pins = sorted(p['key'] for p in spec['pins'])
            self.assertEqual(pins, ['gappy-goal', 'route-goal', 'walk-1', 'walk-2', 'walk-3'])
            by_key = {}
            for tr in spec['tracks']:
                by_key.setdefault(tr['key'], []).append(tr)
            self.assertNotIn('idea-only', by_key)
            self.assertEqual(len(by_key['gappy-goal']), len(gf.SEGS_M))     # three lines, not one joined across the gaps
            self.assertEqual(len(by_key['route-goal']), 1)
            self.assertEqual(len(by_key['walk-1']), 1)
            self.assertTrue(all(tr['style'] == 'planned' for tr in by_key['gappy-goal'] + by_key['route-goal']))

    def test_completed_and_archived_goals_leave_the_region_maps(self):
        trips = [self.recorded('walk-%d' % i, i) for i in (1, 2, 3)]
        done = self.trip('done-goal', gf.ROUTE_ONLY, kind='planned')
        done['goal'] = dict(done['goal'], status='completed', outings=[{'outcome': 'completed', 'date': None, 'report_slug': None, 'note': ''}])
        shelved = self.trip('shelved-goal', gf.MULTISEG, kind='planned')
        shelved['goal'] = dict(shelved['goal'], archived=True)
        future = self.trip('future-goal', gf.SINGLE, kind='planned')
        self.assertIs(self.render.render_site(trips + [done, shelved, future], force=True), True)
        self.assertEqual(len(self.maps), 2)
        for spec in self.maps:
            keys = {tr['key'] for tr in spec['tracks']} | {p['key'] for p in spec['pins']}
            self.assertEqual(keys, {'walk-1', 'walk-2', 'walk-3', 'future-goal'})

    def test_a_region_with_only_an_idea_gets_no_map_and_no_crash(self):
        trips = [self.trip('idea-only', None, kind='planned', region='Elsewhere')]
        self.assertIs(self.render.render_site(trips, force=True), True)
        with open(os.path.join(self.out, 'site', 'meta.json')) as fh:
            meta = json.load(fh)
        self.assertEqual(meta['maps'], {})
        self.assertEqual(meta['all_regions'], [])
        self.assertEqual(self.maps, [])


if __name__ == '__main__':
    unittest.main()
