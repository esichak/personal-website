"""Phase 2T review: tools/render.py and tick-list goals.

render.py is never run here (it needs the internet and rewrites committed assets). Its helpers are called with synthetic
trips in a temp folder, and everything that draws or fetches (render_map, fetch_osm, render_single, optimize_images) is
replaced by a stub, with render.OUT pointed at the temp folder. What is pinned: a goal without a GPX is skipped instead of
crashing a full run, a route-only (rte/rtept) goal has a start and a line on its region map, and a goal with several
segments is drawn as several lines, never joined across the gaps.

Phase 6 adds, with the same stubs: render_trip and render_site draw into a '<folder>.tmp-<pid>' folder and swap it in only
when the drawing finished, so a render that raises (or that Ctrl+C stops) leaves the last good maps byte for byte and no
temp or '.old' folder; main(argv) reports a failed trip, draws the others and ends with exit status 1 (content.load_all
is patched to load the temp folder); `render.py --status` (status, pending_reason, pending_trips, site_maps_stale) says
what a run would draw and why while every fetch and drawing function is patched to fail the test if called; and the
input hashes now in lib/renderkey.py are the very functions render.py uses, computed as render.py always computed them.
"""
import contextlib
import hashlib
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
import renderkey  # noqa: E402

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


class ReportWithoutTrackTests(RenderGoalsFixture):
    """A report whose track.gpx is gone (or that never had one), and a multi-day trip with no day track. The site shows no
    render for it (sitegen.core.has_track), so the renderer draws none: it must not crash on it, and above all it must
    not empty rendered/site/ and then stop, which is what reading a missing track did."""

    def tour(self, slug, tracks, **meta):
        meta.setdefault('region', REGION)
        folder = helpers.make_trip(self.trips_dir, slug, kind='multi-day', date='2026-08-01', activity='ski',
                                   days=[{'date': '2026-08-%02d' % (i + 1), 'track': False} for i in range(len(tracks))], **meta)
        for i, has in enumerate(tracks):
            if has:
                with open(os.path.join(folder, 'days', '%02d.gpx' % (i + 1)), 'w', encoding='utf-8') as fh:
                    fh.write(gf.SINGLE)
        t = content.load_trip(folder)
        t['rendered'] = os.path.join(self.out, 'trips', slug)
        return t

    def test_no_track_by_shape(self):
        no_track = self.render.no_track
        self.assertIs(no_track(self.trip('words-only', None, date='2026-08-02')), True)
        self.assertIs(no_track(self.recorded('walked-it', 1)), False)
        self.assertIs(no_track(self.tour('tour-none', (False, False))), True)
        self.assertIs(no_track(self.tour('tour-some', (False, True))), False)
        # a goal is never this case: an idea is no_route, and a goal with a route has a track
        self.assertIs(no_track(self.trip('idea-only', None, kind='planned')), False)
        self.assertIs(no_track(self.trip('route-goal', gf.ROUTE_ONLY, kind='planned')), False)

    def test_it_is_skipped_and_never_reaches_the_drawing_code(self):
        for t in (self.trip('words-only', None, date='2026-08-02'), self.tour('tour-none', (False, False))):
            with self.subTest(slug=t['slug']):
                with mock.patch.object(self.render, 'render_single', side_effect=AssertionError('drawn')), \
                        mock.patch.object(self.render, 'render_multi', side_effect=AssertionError('drawn')), \
                        mock.patch.object(self.render, 'load_track', side_effect=AssertionError('a missing track was read')):
                    self.assertIs(self.render.render_trip(t), False)
                    self.assertIs(self.render.render_trip(t, force=True), False)
                self.assertFalse(os.path.exists(t['rendered']))

    def test_a_render_left_from_when_it_had_a_track_is_removed(self):
        t = self.trip('words-only', None, date='2026-08-02')
        os.makedirs(t['rendered'])
        with open(os.path.join(t['rendered'], 'meta.json'), 'w') as fh:
            json.dump({'maps': {'map-col': {}}, 'charts': {'profile-wide': {}}}, fh)
        self.assertIs(self.render.render_trip(t), False)
        self.assertFalse(os.path.exists(t['rendered']))
        self.assertIn('removed render of words-only (the report has no track now)', self.printed.getvalue())

    def test_a_report_with_a_track_is_still_rendered(self):
        t = self.recorded('walked-it', 1)
        seen = []
        with mock.patch.object(self.render, 'render_single', side_effect=lambda trip, meta: seen.append(trip['slug'])):
            self.assertIs(self.render.render_trip(t, force=True), True)
        self.assertEqual(seen, ['walked-it'])

    def test_the_region_maps_leave_it_out_and_the_run_finishes(self):
        trips = [self.recorded('walk-%d' % i, i) for i in (1, 2, 3)] + [self.trip('words-only', None, date='2026-08-09'),
                                                                        self.tour('tour-none', (False, False))]
        os.makedirs(os.path.join(self.out, 'site'))
        with open(os.path.join(self.out, 'site', 'meta.json'), 'w') as fh:
            json.dump({'hash': 'stale', 'maps': {}}, fh)
        self.assertIs(self.render.render_site(trips, force=True), True)     # no TypeError from a track that is not there
        with open(os.path.join(self.out, 'site', 'meta.json')) as fh:
            meta = json.load(fh)
        slug = content.slugify(REGION)
        self.assertEqual(sorted(meta['maps']), ['region-%s-desktop' % slug, 'region-%s-phone' % slug])
        for m in meta['maps'].values():
            self.assertEqual(sorted(m['trips']), ['walk-1', 'walk-2', 'walk-3'])
        for spec in self.maps:
            self.assertEqual(sorted(p['key'] for p in spec['pins']), ['walk-1', 'walk-2', 'walk-3'])
            self.assertEqual({tr['key'] for tr in spec['tracks']}, {'walk-1', 'walk-2', 'walk-3'})

    def test_it_does_not_count_towards_a_regions_map_but_its_region_is_still_listed(self):
        trips = [self.recorded('walk-1', 1), self.recorded('walk-2', 2), self.trip('words-only', None, date='2026-08-09'),
                 self.trip('far-words', None, date='2026-08-10', region='Elsewhere')]
        self.assertIs(self.render.render_site(trips, force=True), True)
        with open(os.path.join(self.out, 'site', 'meta.json')) as fh:
            meta = json.load(fh)
        self.assertEqual(meta['maps'], {})                       # two drawable reports are not enough for a region map
        self.assertEqual(meta['regions'], [])
        self.assertEqual(meta['all_regions'], ['Elsewhere', REGION])
        self.assertEqual(self.maps, [])

    def test_the_site_maps_of_trips_that_all_have_tracks_are_what_they_were(self):
        trips = [self.recorded('walk-%d' % i, i) for i in (1, 2, 3)]
        self.assertIs(self.render.render_site(trips, force=True), True)
        with open(os.path.join(self.out, 'site', 'meta.json')) as fh:
            first = json.load(fh)
        self.assertIs(self.render.render_site(trips), False)     # same inputs, same hash: nothing is redrawn
        self.assertEqual(sorted(first['maps'][next(iter(first['maps']))]['trips']), ['walk-1', 'walk-2', 'walk-3'])


# ---------------------------------------------------------------- Phase 6: the temp-folder swap, main(), --status, renderkey

def tree(folder):
    """{path relative to folder: bytes} of every file under it."""
    out = {}
    for base, _dirs, files in os.walk(folder):
        for name in files:
            path = os.path.join(base, name)
            with open(path, 'rb') as fh:
                out[os.path.relpath(path, folder)] = fh.read()
    return out


def write_tree(folder, files):
    for rel, data in files.items():
        path = os.path.join(folder, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as fh:
            fh.write(data)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def leftovers(folder):
    """What a swap that went wrong leaves beside the folder: '<name>.tmp-<pid>' and '<name>.old'."""
    parent = os.path.dirname(folder)
    return sorted(n for n in (os.listdir(parent) if os.path.isdir(parent) else []) if '.tmp-' in n or n.endswith('.old'))


# a render folder as an earlier run left it (the bytes stand in for real maps; only that they survive is asserted)
OLD_RENDER = {'meta.json': b'{"hash": "drawn-from-older-inputs", "maps": {"map-wide": {"w": 1440, "h": 640}}}',
              'map-wide.webp': b'RIFF\x00\x00\x00\x00old map bytes',
              os.path.join('days', '01-g64.svg'): b'<svg xmlns="http://www.w3.org/2000/svg"/>'}
OLD_SITE = {'meta.json': b'{"hash": "older", "maps": {}, "regions": [], "all_regions": []}',
            'region-synthetic-range-desktop.webp': b'RIFF\x00\x00\x00\x00old region map'}
GENERIC = 'track, title, activity, kind, map: or stats changed'
NO_OSM = 'OSM missing last time (drawn with terrain only)'


class SwapTests(RenderGoalsFixture):
    """render_trip and render_site draw into a temp folder beside the old one and swap it in only once the drawing has
    finished: a render that fails half-way, by an exception or by Ctrl+C (a BaseException), leaves the last good maps."""

    def failing_render(self, error):
        """A trip with an earlier render, drawn by a render_single that writes a file and then raises `error`."""
        t = self.recorded('walked-it', 1)
        final = t['rendered']
        write_tree(final, OLD_RENDER)
        seen = []

        def draw(trip, meta):
            seen.append((trip['rendered'], os.path.isdir(trip['rendered'])))
            with open(os.path.join(trip['rendered'], 'map-wide.webp'), 'wb') as fh:
                fh.write(b'half of a new map')
            raise error
        with mock.patch.object(self.render, 'render_single', side_effect=draw):
            with self.assertRaises(type(error)):
                self.render.render_trip(t)
        return t, final, seen

    def assert_last_good_render_kept(self, t, final, seen):
        self.assertEqual(seen, [('%s.tmp-%d' % (final, os.getpid()), True)])    # it drew into the temp folder
        self.assertEqual(t['rendered'], final)                                   # and the trip points back at its own
        self.assertEqual(tree(final), OLD_RENDER)                                # the old files, byte for byte
        self.assertEqual(leftovers(final), [])                                   # no temp folder, no .old folder

    def test_a_render_that_raises_keeps_the_last_good_maps_and_leaves_no_temp_folder(self):
        self.assert_last_good_render_kept(*self.failing_render(RuntimeError('tile fetch failed')))

    def test_a_render_stopped_by_ctrl_c_keeps_the_last_good_maps_and_leaves_no_temp_folder(self):
        self.assert_last_good_render_kept(*self.failing_render(KeyboardInterrupt()))

    def test_a_first_render_that_fails_leaves_no_folder_at_all(self):
        t = self.recorded('walked-it', 1)
        with mock.patch.object(self.render, 'render_single', side_effect=RuntimeError('no tiles')):
            with self.assertRaises(RuntimeError):
                self.render.render_trip(t)
        self.assertFalse(os.path.exists(t['rendered']))
        self.assertEqual(leftovers(t['rendered']), [])

    def test_a_finished_render_takes_the_place_of_the_old_folder_and_records_its_inputs(self):
        t = self.recorded('walked-it', 1)
        final = t['rendered']
        write_tree(final, dict(OLD_RENDER, **{'map-gone.webp': b'a map this render no longer draws'}))

        def draw(trip, meta):
            with open(os.path.join(trip['rendered'], 'map-wide.webp'), 'wb') as fh:
                fh.write(b'new map bytes')
            write_text(os.path.join(trip['rendered'], 'map-wide.meta.json'), '{}')   # mapkit's side file: removed
        with mock.patch.object(self.render, 'render_single', side_effect=draw):
            self.assertIs(self.render.render_trip(t), True)
        self.assertEqual(t['rendered'], final)
        got = tree(final)
        self.assertEqual(sorted(got), ['map-wide.webp', 'meta.json'])           # nothing of the old folder is left
        self.assertEqual(got['map-wide.webp'], b'new map bytes')
        meta = json.loads(got['meta.json'].decode('utf-8'))
        self.assertEqual(meta['hash'], self.render.trip_inputs(t))
        self.assertEqual(meta['inputs'], renderkey.input_parts(t))
        self.assertEqual(sorted(meta['inputs']), ['fields', 'files', 'version'])
        self.assertEqual(meta['inputs']['version'], renderkey.VERSION)
        self.assertEqual(leftovers(final), [])
        self.assertIsNone(self.render.pending_reason(t))                         # read back by --status: up to date

    def failing_site_render(self, error):
        trips = [self.recorded('walk-%d' % i, i) for i in (1, 2, 3)]            # three trips: a region map to draw
        site = os.path.join(self.out, 'site')
        write_tree(site, OLD_SITE)
        with mock.patch.object(self.render, 'render_map', side_effect=error):
            with self.assertRaises(type(error)):
                self.render.render_site(trips, force=True)
        self.assertEqual(tree(site), OLD_SITE)
        self.assertEqual(sorted(os.listdir(self.out)), ['site'])               # no site.tmp-<pid>, no site.old

    def test_a_site_render_that_raises_keeps_rendered_site(self):
        self.failing_site_render(RuntimeError('overview failed'))

    def test_a_site_render_stopped_by_ctrl_c_keeps_rendered_site(self):
        self.failing_site_render(KeyboardInterrupt())

    def test_render_site_draws_into_a_temp_folder_and_swaps_it_in(self):
        trips = [self.recorded('walk-%d' % i, i) for i in (1, 2, 3)]
        site = os.path.join(self.out, 'site')
        write_tree(site, OLD_SITE)
        with mock.patch.object(self.render, 'draw_site', wraps=self.render.draw_site) as drawn:
            self.assertIs(self.render.render_site(trips, force=True), True)
        self.assertEqual(drawn.call_args[0][0], os.path.join(self.out, 'site.tmp-%d' % os.getpid()))
        self.assertEqual(sorted(tree(site)), ['meta.json'])                     # the stubs draw no files; the old map is gone
        with open(os.path.join(site, 'meta.json'), encoding='utf-8') as fh:
            self.assertEqual(json.load(fh)['hash'], renderkey.site_hash(renderkey.site_jobs(trips)[0]))
        self.assertEqual(sorted(os.listdir(self.out)), ['site'])


class RunFixture(RenderGoalsFixture):
    """main() and status() read the trips through content.load_all: here it loads the temp folder (drafts only when asked,
    by folder and then newest first, as content.load_all does), with every render folder under the temp rendered/."""

    def setUp(self):
        super().setUp()
        p = mock.patch.object(self.render.content, 'load_all', side_effect=self.loaded)
        self.load_all = p.start()
        self.addCleanup(p.stop)

    def loaded(self, include_drafts=False):
        trips = helpers.load_dir(self.trips_dir, include_drafts)
        for t in trips:
            t['rendered'] = os.path.join(self.out, 'trips', t['slug'])
        return trips

    def meta_file(self, slug):
        return os.path.join(self.out, 'trips', slug, 'meta.json')

    def draw(self, t):
        """rendered/trips/<slug>/ as a run leaves it, with the drawing stubbed."""
        with mock.patch.object(self.render, 'render_single', side_effect=lambda trip, meta: None):
            self.assertIs(self.render.render_trip(t, force=True), True)

    def draw_site(self, hash_=None):
        """rendered/site/meta.json holding `hash_`, by default the hash of the site maps of the trips as they are now."""
        if hash_ is None:
            hash_ = renderkey.site_hash(renderkey.site_jobs(self.loaded())[0])
        write_text(os.path.join(self.out, 'site', 'meta.json'), json.dumps({'hash': hash_, 'maps': {}}))

    def edit_meta(self, slug, **changes):
        with open(self.meta_file(slug), encoding='utf-8') as fh:
            meta = json.load(fh)
        for k, v in changes.items():
            if v is KeyError:
                del meta[k]
            else:
                meta[k] = v
        write_text(self.meta_file(slug), json.dumps(meta))


class MainTests(RunFixture):
    """main(argv): a trip whose render raises is reported, keeps its last good maps, and the run goes on with the others
    and ends with exit status 1; a clean run ends with 0."""

    def setUp(self):
        super().setUp()
        p = mock.patch.object(self.render, 'prefetch_osm', side_effect=lambda trips: None)
        p.start()
        self.addCleanup(p.stop)
        # newest first: the failing trip is drawn before the other one
        self.bad = self.recorded('bad-walk', 2)
        self.good = self.recorded('good-walk', 1)
        self.drawn = []

    def draw_or_fail(self, trip, meta):
        self.drawn.append(trip['slug'])
        if trip['slug'] == 'bad-walk':
            raise RuntimeError('tile fetch failed')
        with open(os.path.join(trip['rendered'], 'map-wide.webp'), 'wb') as fh:
            fh.write(b'new map bytes')

    def just_draw(self, trip, meta):
        self.drawn.append(trip['slug'])

    def run_main(self, draw, *argv):
        with mock.patch.object(self.render, 'render_single', side_effect=draw):
            return self.render.main(list(argv))

    def lines(self):
        return self.printed.getvalue().splitlines()

    def failed_lines(self):
        return [line for line in self.lines() if 'failed, their last good maps kept' in line]

    def test_a_failed_trip_is_reported_the_others_are_drawn_and_the_exit_status_is_1(self):
        old = os.path.join(self.out, 'trips', 'bad-walk')
        write_tree(old, OLD_RENDER)
        self.assertEqual(self.run_main(self.draw_or_fail), 1)
        self.assertIn('! bad-walk: tile fetch failed', self.lines())
        self.assertEqual(self.drawn, ['bad-walk', 'good-walk'])                 # the run went on after the failure
        self.assertEqual(tree(old), OLD_RENDER)                                 # its last good maps are kept
        self.assertEqual(leftovers(old), [])
        good = tree(os.path.join(self.out, 'trips', 'good-walk'))
        self.assertEqual(good['map-wide.webp'], b'new map bytes')
        self.assertEqual(json.loads(good['meta.json'].decode('utf-8'))['hash'], self.render.trip_inputs(self.good))
        failed = self.failed_lines()
        self.assertEqual(len(failed), 1, self.lines())
        self.assertTrue(failed[0].startswith('1 failed, their last good maps kept: bad-walk.'), failed[0])
        self.assertIn(mock.call(), self.load_all.call_args_list)
        self.assertIn(mock.call(include_drafts=True), self.load_all.call_args_list)

    def test_a_clean_run_returns_0_and_a_second_run_draws_nothing(self):
        self.assertEqual(self.run_main(self.just_draw), 0)
        self.assertEqual(self.drawn, ['bad-walk', 'good-walk'])
        self.assertEqual([line for line in self.lines() if line.startswith('!')], [])
        self.assertEqual(self.failed_lines(), [])
        for slug in ('bad-walk', 'good-walk'):
            self.assertTrue(os.path.exists(self.meta_file(slug)))
        self.drawn[:] = []
        self.assertEqual(self.run_main(self.just_draw), 0)
        self.assertEqual(self.drawn, [])                                        # same inputs: nothing drawn again

    def test_a_failed_site_render_is_reported_keeps_rendered_site_and_the_exit_status_is_1(self):
        self.recorded('third-walk', 3)                                           # three trips: render_site draws a region map
        site = os.path.join(self.out, 'site')
        write_tree(site, OLD_SITE)
        with mock.patch.object(self.render, 'render_map', side_effect=RuntimeError('overview failed')):
            self.assertEqual(self.run_main(self.just_draw), 1)
        self.assertIn('! site maps: overview failed', self.lines())
        self.assertEqual(sorted(self.drawn), ['bad-walk', 'good-walk', 'third-walk'])
        self.assertEqual(tree(site), OLD_SITE)
        self.assertEqual(leftovers(site), [])
        failed = self.failed_lines()
        self.assertEqual(len(failed), 1, self.lines())
        self.assertTrue(failed[0].startswith('1 failed, their last good maps kept: site maps.'), failed[0])


class StrayEntryTests(MainTests):
    """After the review of the phase: rendered/trips/ can hold things that are no trip's render: a Finder .DS_Store, and
    the <slug>.tmp-<pid> or <slug>.old folder of another render at work. Neither main's clean-up nor --status takes them
    for a trip that is gone; and a meta.json that does not parse is drawn again instead of failing every run."""

    def strays(self):
        tdir = os.path.join(self.out, 'trips')
        os.makedirs(tdir, exist_ok=True)
        write_text(os.path.join(tdir, '.DS_Store'), 'finder')
        for name in ('other-walk.tmp-4242', 'other-walk.old'):     # a trip this run does not draw (its own swap would replace them)
            write_text(os.path.join(tdir, name, 'map-wide.webp'), 'another run at work')
        return tdir

    def test_render_folders_are_the_trip_folders_alone(self):
        tdir = self.strays()
        write_text(os.path.join(tdir, 'gone-walk', 'meta.json'), '{}')
        self.assertEqual(self.render.render_folders(tdir), ['gone-walk'])
        self.assertEqual(self.render.render_folders(os.path.join(self.out, 'nothing-here')), [])

    def test_main_leaves_strays_alone_and_removes_a_gone_trips_render(self):
        tdir = self.strays()
        write_text(os.path.join(tdir, 'gone-walk', 'meta.json'), '{}')
        self.assertEqual(self.run_main(self.just_draw), 0)                   # no NotADirectoryError from .DS_Store
        self.assertEqual(sorted(os.listdir(tdir)), ['.DS_Store', 'bad-walk', 'good-walk', 'other-walk.old', 'other-walk.tmp-4242'])
        self.assertIn('removed stale render gone-walk', self.lines())

    def test_status_does_not_count_strays_as_gone_trips(self):
        self.assertEqual(self.run_main(self.just_draw), 0)
        self.strays()
        said = []
        with mock.patch.object(self.render, 'site_maps_stale', side_effect=lambda trips, force=False: None):
            self.assertEqual(self.render.status(say=said.append), 0)
        self.assertEqual([' '.join(x.split()) for x in said], ['trips: all 2 up to date', 'site maps: up to date'])

    def test_a_meta_json_that_does_not_parse_is_drawn_again(self):
        self.assertEqual(self.run_main(self.just_draw), 0)
        write_text(self.meta_file('good-walk'), '{"hash": "cut sho')
        self.assertIsNone(self.render.stored_hash(self.meta_file('good-walk')))
        self.drawn[:] = []
        self.assertEqual(self.run_main(self.just_draw), 0)
        self.assertEqual(self.drawn, ['good-walk'])
        with open(self.meta_file('good-walk'), encoding='utf-8') as fh:
            self.assertEqual(json.load(fh)['hash'], self.render.trip_inputs(self.good))


class StatusTests(RunFixture):
    """`render.py --status`: what a run would draw and why, read from content and rendered/ alone. Three walks in one
    region (so there is a region map) are drawn and the site maps hashed in setUp; each test changes one thing. Every
    status() call runs with the fetching and drawing functions patched to fail the test if called."""

    def setUp(self):
        super().setUp()
        for i in (1, 2, 3):
            self.draw(self.recorded('walk-%d' % i, i))
        self.draw_site()

    def status(self, *slugs, **kw):
        """(exit status, lines said) of render.status(slugs), with the slug padding collapsed to one space."""
        said = []
        refuse = [(self.render.geo, 'overpass'), (self.render.geo, 'get_tile'), (self.render.geo, 'osm_layers'),
                  (self.render.geo.subprocess, 'run'), (self.render, 'fetch_osm'), (self.render, 'prefetch_osm'),
                  (self.render, 'render_map'), (self.render, 'render_single'), (self.render, 'render_multi'),
                  (self.render, 'render_series'), (self.render, 'draw_site'), (self.render, 'render_trip')]
        with contextlib.ExitStack() as guards:
            for owner, name in refuse:
                guards.enter_context(mock.patch.object(owner, name, side_effect=AssertionError('--status called %s' % name)))
            code = self.render.status(slugs, say=said.append, **kw)
        return code, [' '.join(line.split()) for line in said]

    def named(self, slug):
        return next(t for t in self.loaded(True) if t['slug'] == slug)

    def reason(self, slug, force=False):
        return self.render.pending_reason(self.named(slug), force)

    def test_nothing_changed_nothing_to_draw_and_exit_status_0(self):
        self.load_all.reset_mock()
        self.assertEqual(self.status(), (0, ['trips: all 3 up to date', 'site maps: up to date']))
        self.assertEqual(self.load_all.call_args_list, [mock.call(include_drafts=True)])
        trips = self.loaded()
        self.assertEqual([self.render.pending_reason(t) for t in trips], [None, None, None])
        self.assertEqual(self.render.pending_trips(trips), [])
        self.assertIsNone(self.render.site_maps_stale(trips))

    def test_a_changed_track_is_named_when_meta_json_has_the_inputs_of_the_last_render(self):
        write_text(os.path.join(self.trips_dir, 'walk-2', 'track.gpx'), gf.gpx(gf.trk([gf.SEG_M1])))
        self.assertEqual(self.reason('walk-2'), 'track changed')
        self.assertEqual(self.status(), (1, ['walk-2 track changed', 'site maps: stale (a trip on a region or ski map changed)']))
        self.assertEqual([t['slug'] for t in self.render.pending_trips(self.loaded())], ['walk-2'])

    def test_a_changed_track_gets_the_generic_reason_when_meta_json_has_no_inputs(self):
        self.edit_meta('walk-2', inputs=KeyError)            # a render from before meta.json carried its inputs
        write_text(os.path.join(self.trips_dir, 'walk-2', 'track.gpx'), gf.gpx(gf.trk([gf.SEG_M1])))
        self.assertEqual(self.reason('walk-2'), GENERIC)
        code, lines = self.status()
        self.assertEqual(code, 1)
        self.assertEqual(lines[0], 'walk-2 ' + GENERIC)

    def test_a_changed_title_or_stats_is_named(self):
        self.trip('walk-3', gf.SINGLE, date='2026-08-03', title='Renamed Synthetic Walk')
        self.assertEqual(self.reason('walk-3'), 'title/map/stats changed')
        self.assertEqual(self.status(), (1, ['walk-3 title/map/stats changed',
                                             'site maps: stale (a trip on a region or ski map changed)']))
        self.trip('walk-3', gf.SINGLE, date='2026-08-03', stats={'distance_km': 5.5})
        self.assertEqual(self.reason('walk-3'), 'title/map/stats changed')

    def test_a_new_renderer_and_several_changes_at_once_are_named(self):
        self.edit_meta('walk-1', hash='drawn-by-an-older-renderer', inputs=dict(renderkey.input_parts(self.named('walk-1')),
                                                                                version=renderkey.VERSION - 1))
        self.assertEqual(self.reason('walk-1'), 'renderer changed')
        self.trip('walk-3', gf.gpx(gf.trk([gf.SEG_M2])), date='2026-08-03', title='Renamed Synthetic Walk')
        self.assertEqual(self.reason('walk-3'), 'track changed, title/map/stats changed')

    def test_a_trip_never_drawn_is_new(self):
        self.recorded('walk-4', 4)
        self.assertEqual(self.reason('walk-4'), 'new: no maps drawn yet')
        self.assertEqual(self.status(), (1, ['walk-4 new: no maps drawn yet',
                                             'site maps: stale (a trip on a region or ski map changed)']))

    def test_a_render_that_lost_its_osm_data_is_drawn_again(self):
        self.edit_meta('walk-1', hash=None, osm_failed=True)
        self.assertEqual(self.reason('walk-1'), NO_OSM)
        self.assertEqual(self.status(), (1, ['walk-1 ' + NO_OSM, 'site maps: up to date']))
        self.draw(self.named('walk-1'))
        self.edit_meta('walk-1', osm_failed=True)              # the right hash, but marked as drawn without OSM
        self.assertEqual(self.reason('walk-1'), NO_OSM)

    def test_a_draft_is_listed_as_skipped_and_not_counted(self):
        self.trip('draft-walk', gf.SINGLE, date='2026-08-09', draft=True)
        self.assertEqual(self.status(), (0, ['draft-walk draft, skipped (render.py leaves drafts out)',
                                             'trips: all 3 up to date', 'site maps: up to date']))
        self.assertEqual(self.render.pending_trips(self.loaded()), [])

    def test_a_render_folder_without_a_trip_is_listed_unless_slugs_are_given(self):
        write_text(self.meta_file('gone-walk'), '{"hash": "x"}')
        self.assertEqual(self.status(), (1, ['rendered/trips/gone-walk no trip any more: its render is removed',
                                             'site maps: up to date']))
        code, lines = self.status('walk-1')
        self.assertEqual(code, 0)
        self.assertEqual([line for line in lines if 'gone-walk' in line], [])

    def test_stale_site_maps_are_named(self):
        for stored, why in (('0' * 40, 'a trip on a region or ski map changed'), (None, NO_OSM)):
            with self.subTest(stored=stored):
                write_text(os.path.join(self.out, 'site', 'meta.json'), json.dumps({'hash': stored, 'maps': {}}))
                self.assertEqual(self.render.site_maps_stale(self.loaded()), why)
                self.assertEqual(self.status(), (1, ['trips: all 3 up to date', 'site maps: stale (%s)' % why]))
        os.remove(os.path.join(self.out, 'site', 'meta.json'))
        self.assertEqual(self.render.site_maps_stale(self.loaded()), 'not drawn yet')
        self.assertEqual(self.status(), (1, ['trips: all 3 up to date', 'site maps: stale (not drawn yet)']))

    def test_render_site_writes_the_hash_site_maps_stale_compares(self):
        self.draw_site('0' * 40)
        trips = self.loaded()
        self.assertEqual(self.render.site_maps_stale(trips), 'a trip on a region or ski map changed')
        self.assertIs(self.render.render_site(trips), True)
        self.assertIsNone(self.render.site_maps_stale(self.loaded()))

    def test_force_makes_every_drawable_trip_and_the_site_maps_pending(self):
        trips = self.loaded()
        self.assertEqual([self.render.pending_reason(t, force=True) for t in trips], ['forced (--force)'] * 3)
        self.assertEqual(self.render.pending_trips(trips, force=True), trips)
        self.assertEqual(self.render.site_maps_stale(trips, force=True), 'forced (--force)')
        self.assertEqual(self.status(force=True), (1, ['walk-3 forced (--force)', 'walk-2 forced (--force)',
                                                       'walk-1 forced (--force)', 'site maps: stale (forced (--force))']))

    def test_only_the_slugs_asked_for_are_pending(self):
        self.recorded('walk-4', 4)
        self.recorded('walk-5', 5)
        trips = self.loaded()
        self.assertEqual([t['slug'] for t in self.render.pending_trips(trips)], ['walk-5', 'walk-4'])
        self.assertEqual([t['slug'] for t in self.render.pending_trips(trips, slugs=('walk-4', 'walk-1'))], ['walk-4'])

    def test_a_goal_without_a_route_or_a_report_without_a_track_is_pending_only_while_an_old_render_is_left(self):
        self.trip('idea-only', None, kind='planned')
        self.trip('words-only', None, date='2026-08-09')
        self.assertIsNone(self.reason('idea-only'))
        self.assertIsNone(self.reason('words-only'))
        self.assertEqual(self.status(), (0, ['trips: all 5 up to date', 'site maps: up to date']))
        for slug in ('idea-only', 'words-only'):
            write_text(self.meta_file(slug), '{"hash": "x"}')
        self.assertEqual(self.reason('idea-only'), 'the goal has no route now: its old render is removed')
        self.assertEqual(self.reason('words-only'), 'the report has no track now: its old render is removed')
        self.assertEqual(self.render.pending_trips(self.loaded()), [])        # render_trip only removes those folders
        code, lines = self.status()
        self.assertEqual(code, 1)
        self.assertIn('idea-only the goal has no route now: its old render is removed', lines)
        self.assertIn('words-only the report has no track now: its old render is removed', lines)


class RenderKeyTests(RenderGoalsFixture):
    """lib/renderkey.py holds the input hashes the content checks read without importing the renderer: render.py uses the
    very same functions, and they hash exactly what render.py always hashed, so moving them re-renders nothing."""

    def test_render_py_uses_renderkeys_functions_under_their_old_names(self):
        for name in ('VERSION', 'MIN_REGION_TRIPS', 'file_hash', 'trip_inputs', 'no_route', 'no_track', 'journal_parts'):
            with self.subTest(name=name):
                self.assertIs(getattr(self.render, name), getattr(renderkey, name))

    def test_trip_inputs_and_input_parts_hash_what_render_py_always_hashed(self):
        folder = helpers.make_trip(self.trips_dir, 'two-day-tour', kind='multi-day', date='2026-08-01', activity='ski',
                                   region=REGION, map={'peaks': ['Synthetic Dome']},
                                   days=[{'date': '2026-08-01', 'hut': 'Synthetic Hut', 'stats': {'distance_km': 9.0}},
                                         {'date': '2026-08-02', 'transfer_before': True}])
        for day in ('01', '02'):
            write_text(os.path.join(folder, 'days', day + '.gpx'), gf.SINGLE if day == '01' else gf.MULTISEG)
        for t in (self.recorded('walked-it', 1), content.load_trip(folder), self.trip('idea-only', None, kind='planned')):
            with self.subTest(slug=t['slug']):
                # the expression render.py's trip_inputs was before Phase 6, written out here
                keys = {k: t['meta'].get(k) for k in ('title', 'activity', 'kind', 'map', 'stats', 'route_shape')}
                keys['days'] = [(d['id'], d['hut'], d['transfer_before'], d['stats'], d['label']) for d in t['days']]
                files = hashlib.sha1()
                for p in [t['track']] + [d['track'] for d in t['days']]:
                    if p and os.path.exists(p):
                        with open(p, 'rb') as fh:
                            files.update(fh.read())
                fields = json.dumps(keys, sort_keys=True, default=str)
                self.assertEqual(renderkey.trip_inputs(t),
                                 hashlib.sha1((fields + files.hexdigest() + str(renderkey.VERSION)).encode()).hexdigest())
                self.assertEqual(renderkey.input_parts(t), {'fields': hashlib.sha1(fields.encode()).hexdigest(),
                                                            'files': files.hexdigest(), 'version': renderkey.VERSION})

    def test_goal_has_line_agrees_with_goal_lines(self):
        goals_ = [('single-goal', gf.SINGLE, True), ('route-goal', gf.ROUTE_ONLY, True), ('gappy-goal', gf.MULTISEG, True),
                  ('two-ways-goal', gf.ALTERNATIVES, True), ('waypoints-goal', gf.WAYPOINT_ONLY, False),
                  ('idea-only', None, False)]
        for slug, text, has_line in goals_:
            with self.subTest(slug=slug):
                t = self.trip(slug, text, kind='planned')
                self.assertIs(renderkey.goal_has_line(t), has_line)
                self.assertIs(bool(self.render.goal_lines(t)), has_line)


if __name__ == '__main__':
    unittest.main()
