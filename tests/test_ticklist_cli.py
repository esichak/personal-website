"""Phase 2T: tools/ticklist.py, the local tick-list CLI (add, update, log-outing, review-packet, export), driven in-process
through main(argv).

The content root is redirected: every module constant of tools/ticklist.py that equals content.TRIPS_DIR, and
content.TRIPS_DIR itself, are patched to a temp dir, so each run writes there and the real content/trips/ is never touched
(a listing of it is compared before and after every test as a guard). subprocess is patched so tools/render.py is never run
(--no-render is passed everywhere but the one test that checks the render call and its failure path), and every test
asserts no render was invoked. GPX inputs are the synthetic strings of tests/gpx_fixtures.py written to a second temp dir, so
"the local path" is a real, distinctive string that must not appear in any written file. Published trips the outing tests
link to are helpers.make_trip fixtures. ticklist is imported in setUp so a missing module fails each test clearly.
"""
import contextlib
import hashlib
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import frontmatter  # noqa: E402

import gpx_fixtures as gf  # noqa: E402
import helpers  # noqa: E402

TITLE = 'Synthetic Ridge Traverse'
SLUG = 'synthetic-ridge-traverse'
TODAY = '2026-10-09'   # what ticklist.today() answers in these tests (patched in CliFixture.setUp)


def load_cli(tc):
    """tools/ticklist.py as a module, or a clear failure of the calling test when it is missing."""
    try:
        return importlib.import_module('ticklist')
    except ImportError as ex:
        tc.fail('tools/ticklist.py is not importable: %s' % ex)


def load_lib(tc, name):
    try:
        return importlib.import_module(name)
    except ImportError as ex:
        tc.fail('tools/lib/%s.py is not importable: %s' % (name, ex))


def read(path, mode='r'):
    with open(path, mode if mode == 'rb' else 'r', **({} if mode == 'rb' else {'encoding': 'utf-8'})) as fh:
        return fh.read()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class CliFixture(unittest.TestCase):

    def setUp(self):
        self.cli = load_cli(self)
        self.gpxroute = load_lib(self, 'gpxroute')
        self.goals = load_lib(self, 'goals')
        self.real_trips = content.TRIPS_DIR
        self.real_listing = sorted(os.listdir(self.real_trips)) if os.path.isdir(self.real_trips) else []
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.trips = os.path.join(tmp.name, 'trips')     # stands in for content/trips/
        self.src = os.path.join(tmp.name, 'gpx-src')     # where "the local GPX" lives: a path that must never be written
        os.makedirs(self.trips)
        os.makedirs(self.src)
        self.patch_content_root()
        self.patch_subprocess()
        # a fixed day, so nothing here depends on the clock (or on midnight passing between the command and the assertion)
        p = mock.patch.object(self.cli, 'today', return_value=TODAY)
        p.start()
        self.addCleanup(p.stop)
        self.modules_before = set(sys.modules)

    def tearDown(self):
        if os.path.isdir(self.real_trips):
            now = sorted(os.listdir(self.real_trips))
            self.assertEqual(now, self.real_listing, 'the CLI wrote into the real content/trips/: remove the new entries by hand')

    # ---- patches

    def patch_content_root(self):
        real = os.path.normpath(content.TRIPS_DIR)
        names = [n for n in dir(self.cli) if not n.startswith('__') and isinstance(getattr(self.cli, n), str)
                 and os.path.normpath(getattr(self.cli, n)) == real]
        src = read(self.cli.__file__)
        if not names and 'TRIPS_DIR' not in src:
            self.fail('tools/ticklist.py has no module constant equal to content.TRIPS_DIR and never reads content.TRIPS_DIR: '
                      'the tests cannot redirect it away from the real content/trips/')
        for n in names:
            p = mock.patch.object(self.cli, n, self.trips)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(content, 'TRIPS_DIR', self.trips)
        p.start()
        self.addCleanup(p.stop)

    def patch_subprocess(self):
        self.calls = []
        self.render_rc = 0

        def fake_run(args, *a, **k):
            self.calls.append([str(x) for x in args])
            return subprocess.CompletedProcess(args, self.render_rc)

        def fake_check(args, *a, **k):
            self.calls.append([str(x) for x in args])
            if self.render_rc:
                raise subprocess.CalledProcessError(self.render_rc, args)
            return 0

        for name, fn in (('run', fake_run), ('call', fake_run), ('check_call', fake_check), ('check_output', fake_check), ('Popen', fake_run)):
            p = mock.patch.object(subprocess, name, fn)
            p.start()
            self.addCleanup(p.stop)

    # ---- running

    def run_cli(self, *argv):
        """(exit code, stdout, stderr) of main(argv). A SystemExit (argparse) counts by its code."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = self.cli.main([str(a) for a in argv])
            except SystemExit as ex:
                code = ex.code
        return (0 if code is None else code), out.getvalue(), err.getvalue()

    def ok(self, *argv):
        code, out, err = self.run_cli(*argv)
        self.assertEqual(code, 0, 'argv %r failed (%s):\n%s%s' % (argv, code, out, err))
        return out

    def fails(self, *argv):
        code, out, err = self.run_cli(*argv)
        self.assertNotEqual(code, 0, 'argv %r unexpectedly succeeded:\n%s' % (argv, out))
        return out + err

    def add(self, *extra, title=TITLE, activity='hike', render=False):
        argv = ['add', '--title', title, '--activity', activity] + ([] if render else ['--no-render']) + list(extra)
        return self.ok(*argv)

    # ---- fixtures and readers

    def gpx(self, name, text):
        path = os.path.join(self.src, name)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        return path

    def folder(self, slug=SLUG):
        return os.path.join(self.trips, slug)

    def index(self, slug=SLUG):
        return frontmatter.split(read(os.path.join(self.folder(slug), 'index.md')))

    def goal(self, slug=SLUG):
        return json.loads(read(os.path.join(self.folder(slug), 'goal.json')))

    def track(self, slug=SLUG):
        return read(os.path.join(self.folder(slug), 'track.gpx'), 'rb')

    def files(self, slug=SLUG):
        return sorted(os.listdir(self.folder(slug)))

    def load(self, slug=SLUG):
        return content.load_trip(self.folder(slug))

    def report(self, slug='real-report', **meta):
        meta.setdefault('activity', 'hike')
        meta.setdefault('date', '2026-08-30')
        meta.setdefault('title', 'A Real Synthetic Report')
        return helpers.make_trip(self.trips, slug, track=True, body='Walked it in a day.', **meta)

    def assertNoRender(self):
        self.assertEqual([c for c in self.calls if any('render' in x for x in c)], [], 'render.py was invoked')

    def assertNoLocalPath(self, slug=SLUG):
        """Neither the source folder nor the source file path appears in any written file."""
        for name in self.files(slug):
            data = read(os.path.join(self.folder(slug), name), 'rb')
            self.assertNotIn(self.src.encode(), data, name)
            self.assertNotIn(b'gpx-src', data, name)


# ---------------------------------------------------------------- add

class AddReportTests(CliFixture):
    """What the import report tells the author before anything is approved."""

    def test_a_sparse_file_is_called_a_rough_line(self):
        out = self.add('--gpx', self.gpx('sparse.gpx', gf.SPARSE), '--dry-run')
        self.assertIn('sparse', out.lower())
        out = self.add('--gpx', self.gpx('single.gpx', gf.SINGLE), '--dry-run')
        self.assertNotIn('sparse', out.lower())

    def test_publishing_one_element_says_what_is_left_behind(self):
        out = self.add('--gpx', self.gpx('alts.gpx', gf.ALTERNATIVES), '--select', 'trk:1', '--publish-track')
        self.assertIn('chosen element', out)
        self.assertIn('not copied', out)
        self.assertIn('waypoint', out)
        whole = self.add('--gpx', self.gpx('single.gpx', gf.SINGLE), '--publish-track', '--slug', 'whole-file-goal', title='Whole File Goal')
        self.assertIn('whole file', whole)
        self.assertNotIn('not copied', whole)

    def test_duplicate_check_also_covers_a_planned_route_without_a_goal_json(self):
        # a route saved before the tick list has no recorded checksum: its file is compared as it is
        legacy = helpers.make_trip(self.trips, 'legacy-route', title='Legacy Route', activity='hike', kind='planned', track=True)
        with open(os.path.join(legacy, 'track.gpx'), 'w', encoding='utf-8') as fh:
            fh.write(gf.SINGLE)
        src = self.gpx('same.gpx', gf.SINGLE)
        msg = self.fails('add', '--title', TITLE, '--activity', 'hike', '--no-render', '--gpx', src, '--publish-track')
        self.assertIn('legacy-route', msg)
        self.assertFalse(os.path.exists(self.folder()))
        # a report's recording with the same bytes is not a goal route: no duplicate
        rep = self.report('walked-it')
        with open(os.path.join(rep, 'track.gpx'), 'w', encoding='utf-8') as fh:
            fh.write(gf.ROUTE_ONLY)
        self.add('--gpx', self.gpx('route.gpx', gf.ROUTE_ONLY), '--publish-track')
        # without --publish-track nothing is published, so there is nothing to compare: the idea is saved
        self.ok('add', '--title', 'Looked At Only', '--activity', 'hike', '--no-render', '--gpx', src)
        self.assertEqual(self.files('looked-at-only'), ['goal.json', 'index.md'])

    def test_a_title_that_gives_no_folder_name_asks_for_a_slug(self):
        msg = self.fails('add', '--title', '!!!', '--activity', 'hike', '--no-render')
        self.assertIn('--slug', msg)
        self.assertEqual(os.listdir(self.trips), [])
        self.ok('add', '--title', '!!!', '--activity', 'hike', '--no-render', '--slug', 'named-by-hand')
        self.assertEqual(os.listdir(self.trips), ['named-by-hand'])

    def test_a_route_source_that_is_not_an_object_gets_a_message_not_a_traceback(self):
        self.add()
        p = os.path.join(self.folder(), 'goal.json')
        g = self.goal()
        g['route_source'] = None
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(g, fh)
        before = read(p, 'rb')
        msg = self.fails('update', SLUG, '--source-kind', 'planner-export')
        self.assertIn('route_source', msg)
        self.assertNotIn('Traceback', msg)
        self.assertEqual(read(p, 'rb'), before)


class AddTests(CliFixture):

    def test_metadata_only_creates_a_draft_planned_trip_with_a_sidecar(self):
        out = self.add()
        self.assertEqual(self.files(), ['goal.json', 'index.md'])
        meta, body = self.index()
        self.assertEqual(meta['title'], TITLE)
        self.assertEqual(meta['activity'], 'hike')
        self.assertEqual(meta['kind'], 'planned')
        self.assertIs(meta['draft'], True)
        self.assertNotIn('date', meta)
        self.assertNotIn('stats', meta)
        self.assertEqual(body.strip(), '')
        g = self.goal()
        d = self.goals.defaults()
        self.assertEqual((g['status'], g['priority'], g['archived']), ('idea', 'normal', False))
        self.assertEqual(g['added_at'], TODAY)
        self.assertIsNone(g['route'])
        self.assertFalse(g['route_source']['public_copy_approved'])
        for k in ('tags', 'why', 'target_months', 'target_year', 'time_commitment', 'season_notes', 'difficulty', 'route_scope',
                  'references', 'field_evidence', 'checklist', 'outings'):
            self.assertEqual(g[k], d[k], k)
        self.assertNotIn('legacy', g)
        t = self.load()
        self.assertIs(t['goal']['legacy'], False)
        self.assertIn(SLUG, out)
        self.assertNoRender()

    def test_report_names_the_files_and_the_publish_step(self):
        out = self.add()
        self.assertIn('index.md', out)
        self.assertIn('goal.json', out)
        self.assertIn('draft: true', out)
        self.assertIn('git add', out)

    def test_place_region_subtype_and_notes_go_into_index_md(self):
        self.add('--place', 'Synthetic Bowl', '--region', 'Nowhere Range', '--subtype', 'Mountaineering', '--notes', 'Start before dawn.\n\nCheck the creek.',
                 activity='other')
        meta, body = self.index()
        self.assertEqual((meta['place'], meta['region'], meta['subtype']), ('Synthetic Bowl', 'Nowhere Range', 'Mountaineering'))
        self.assertIn('Start before dawn.', body)
        self.assertIn('Check the creek.', body)
        t = self.load()
        self.assertEqual(t['body_md'], 'Start before dawn.\n\nCheck the creek.')

    def test_intent_options_reach_goal_json(self):
        self.add('--priority', 'high', '--status', 'shortlisted', '--tags', 'ridge, scramble', '--why', 'Long ridge.', '--months', '7,6',
                 '--year', '2027', '--commitment', 'full-day', '--scope', 'approach-only', '--source-kind', 'planner-export',
                 '--source-url', 'https://example.test/plan', '--source-label', 'Planner')
        g = self.goal()
        self.assertEqual((g['priority'], g['status']), ('high', 'shortlisted'))
        self.assertEqual(g['tags'], ['ridge', 'scramble'])
        self.assertEqual(g['why'], 'Long ridge.')
        self.assertEqual(sorted(g['target_months']), [6, 7])
        self.assertEqual(g['target_year'], 2027)
        self.assertEqual((g['time_commitment'], g['route_scope']), ('full-day', 'approach-only'))
        self.assertEqual((g['route_source']['kind'], g['route_source']['url'], g['route_source']['label']),
                         ('planner-export', 'https://example.test/plan', 'Planner'))
        self.assertIs(self.load()['goal']['legacy'], False)

    def test_custom_slug(self):
        self.add('--slug', 'my-ridge')
        self.assertTrue(os.path.isdir(self.folder('my-ridge')))
        self.assertFalse(os.path.exists(self.folder()))

    def test_publish_track_copies_the_bytes_exactly(self):
        path = self.gpx('single.gpx', gf.SINGLE)
        src = read(path, 'rb')
        self.add('--gpx', path, '--publish-track')
        self.assertEqual(self.files(), ['goal.json', 'index.md', 'track.gpx'])
        self.assertEqual(self.track(), src)
        self.assertEqual(sha256(self.track()), sha256(src))
        self.assertEqual(self.goal()['route']['source_sha256'], sha256(src))
        self.assertNoRender()

    def test_publish_track_writes_stats_and_a_route_block(self):
        path = self.gpx('single.gpx', gf.SINGLE)
        self.add('--gpx', path, '--publish-track')
        info = self.gpxroute.inspect(path)
        m = self.gpxroute.measure(self.gpxroute.select(info)['segments'])
        meta, _ = self.index()
        st = meta['stats']
        self.assertEqual(st['distance_km'], m['distance_km'])
        self.assertEqual((st['gain_m'], st['loss_m']), (m['gain_m'], m['loss_m']))
        self.assertEqual((st['high_m'], st['low_m']), (m['high_m'], m['low_m']))
        self.assertNotIn('moving', st)
        self.assertNotIn('elapsed', st)
        self.assertNotIn('date', meta)   # the recorder's timestamps are never a trip date
        g = self.goal()
        r = g['route']
        self.assertEqual(r['source_sha256'], info['sha256'])
        self.assertEqual(r['method'], 'ticklist-gpx-1')
        self.assertEqual(r['selected'], {'type': 'trk', 'index': 0, 'name': 'Synthetic ridge'})
        self.assertEqual(r['alternatives'], 1)
        self.assertEqual((r['segments'], r['points']), (1, 12))
        self.assertEqual((r['elevation'], r['times'], r['waypoints']), ('full', True, 0))
        self.assertTrue(g['route_source']['public_copy_approved'])
        t = self.load()   # the sidecar validates against the written track
        self.assertEqual(t['goal']['route']['source_sha256'], info['sha256'])
        self.assertEqual(t['stats']['distance_km'], m['distance_km'])

    def test_no_local_path_in_any_written_file(self):
        path = self.gpx('single.gpx', gf.SINGLE)
        self.add('--gpx', path, '--publish-track')
        self.assertNoLocalPath()
        self.add('--gpx', self.gpx('other.gpx', gf.ROUTE_ONLY), title='Metadata Only Idea')
        self.assertNoLocalPath('metadata-only-idea')

    def test_without_publish_track_nothing_from_the_file_is_written(self):
        path = self.gpx('single.gpx', gf.SINGLE)
        out = self.add('--gpx', path)
        self.assertEqual(self.files(), ['goal.json', 'index.md'])
        meta, _ = self.index()
        self.assertNotIn('stats', meta)
        g = self.goal()
        self.assertIsNone(g['route'])
        self.assertFalse(g['route_source']['public_copy_approved'])
        m = self.gpxroute.measure(self.gpxroute.select(self.gpxroute.inspect(path))['segments'])
        self.assertIn('%.2f' % m['distance_km'], out)   # the report shows the author the measurements
        self.assertIn('approx', out.lower())
        self.assertIn('publish-track', out)
        self.assertNoLocalPath()

    def test_no_elevation_file_publishes_no_gain(self):
        self.add('--gpx', self.gpx('noele.gpx', gf.NO_ELE), '--publish-track')
        meta, _ = self.index()
        self.assertIn('distance_km', meta['stats'])
        for k in ('gain_m', 'loss_m', 'high_m', 'low_m'):
            self.assertNotIn(k, meta['stats'])
        self.assertEqual(self.goal()['route']['elevation'], 'none')
        self.assertIsNone(self.load()['stats']['gain_m'])

    def test_partial_elevation_file_publishes_heights_but_no_gain(self):
        self.add('--gpx', self.gpx('partial.gpx', gf.PARTIAL_ELE), '--publish-track')
        st = self.index()[0]['stats']
        self.assertNotIn('gain_m', st)
        self.assertNotIn('loss_m', st)
        self.assertEqual((st['high_m'], st['low_m']), (2050, 2000))
        self.assertEqual(self.goal()['route']['elevation'], 'partial')

    def test_no_timestamps_file(self):
        self.add('--gpx', self.gpx('notime.gpx', gf.NO_TIME), '--publish-track')
        self.assertIs(self.goal()['route']['times'], False)

    def test_route_only_file_publishes_the_route(self):
        self.add('--gpx', self.gpx('route.gpx', gf.ROUTE_ONLY), '--publish-track')
        r = self.goal()['route']
        self.assertEqual(r['selected'], {'type': 'rte', 'index': 0, 'name': 'Ridge route'})
        self.assertEqual((r['segments'], r['points']), (1, 11))
        self.assertEqual(self.track(), read(os.path.join(self.src, 'route.gpx'), 'rb'))

    def test_multisegment_track_keeps_its_segments_and_sums_distance(self):
        self.add('--gpx', self.gpx('multi.gpx', gf.MULTISEG), '--publish-track')
        r = self.goal()['route']
        self.assertEqual((r['segments'], r['points']), (3, 14))
        st = self.index()[0]['stats']
        own = sum(gf.poly_km(s) for s in gf.SEGS_M)
        self.assertAlmostEqual(st['distance_km'], own, delta=0.02)
        self.assertEqual((st['gain_m'], st['loss_m']), (35, 20))

    def test_alternatives_require_select(self):
        path = self.gpx('alts.gpx', gf.ALTERNATIVES)
        msg = self.fails('add', '--title', TITLE, '--activity', 'hike', '--no-render', '--gpx', path, '--publish-track')
        self.assertFalse(os.path.exists(self.folder()))
        for want in ('trk:0', 'trk:1', 'rte:0', 'select'):
            self.assertIn(want, msg)
        self.assertNoRender()

    def test_select_a_route_publishes_only_that_route(self):
        path = self.gpx('alts.gpx', gf.ALTERNATIVES)
        self.add('--gpx', path, '--select', 'rte:0', '--publish-track')
        published = self.gpxroute.inspect(os.path.join(self.folder(), 'track.gpx'))
        self.assertEqual(published['tracks'], [])
        self.assertEqual(len(published['routes']), 1)
        self.assertEqual(published['routes'][0]['name'], 'Descent')
        src = self.gpxroute.inspect(path)
        self.assertEqual(published['routes'][0]['points'], src['routes'][0]['points'])   # points, elevations, times unchanged
        g = self.goal()
        self.assertEqual(g['route']['selected'], {'type': 'rte', 'index': 0, 'name': 'Descent'})
        self.assertEqual(g['route']['alternatives'], 3)
        self.assertEqual(g['route']['source_sha256'], sha256(self.track()))
        self.assertNotEqual(g['route']['source_sha256'], src['sha256'])
        self.assertEqual(self.load()['goal']['route']['points'], 5)

    def test_select_a_track_keeps_its_segments(self):
        path = self.gpx('alts.gpx', gf.ALTERNATIVES)
        self.add('--gpx', path, '--select', 'trk:1', '--publish-track')
        published = self.gpxroute.inspect(os.path.join(self.folder(), 'track.gpx'))
        self.assertEqual(len(published['tracks']), 1)
        self.assertEqual(published['routes'], [])
        self.assertEqual(published['tracks'][0]['name'], 'South approach')
        src = self.gpxroute.inspect(path)
        self.assertEqual(published['tracks'][0]['segments'], src['tracks'][1]['segments'])
        r = self.goal()['route']
        self.assertEqual(r['selected'], {'type': 'trk', 'index': 1, 'name': 'South approach'})
        self.assertEqual((r['segments'], r['points']), (2, 7))

    def test_select_not_in_the_file_is_refused(self):
        path = self.gpx('alts.gpx', gf.ALTERNATIVES)
        self.fails('add', '--title', TITLE, '--activity', 'hike', '--no-render', '--gpx', path, '--select', 'rte:4', '--publish-track')
        self.assertFalse(os.path.exists(self.folder()))

    def test_waypoint_only_file_becomes_a_metadata_only_goal(self):
        path = self.gpx('wpts.gpx', gf.WAYPOINT_ONLY)
        out = self.add('--gpx', path, '--publish-track')
        self.assertEqual(self.files(), ['goal.json', 'index.md'])
        self.assertNotIn('stats', self.index()[0])
        g = self.goal()
        self.assertIsNone(g['route'])
        self.assertFalse(g['route_source']['public_copy_approved'])
        self.assertIn('waypoint', out.lower())
        self.assertNoLocalPath()

    def test_duplicate_checksum_stops_without_allow_duplicate(self):
        path = self.gpx('single.gpx', gf.SINGLE)
        self.add('--gpx', path, '--publish-track')
        msg = self.fails('add', '--title', 'Same Line Again', '--activity', 'ski', '--no-render', '--gpx', path, '--publish-track')
        self.assertFalse(os.path.exists(self.folder('same-line-again')))
        self.assertIn('duplicate', msg.lower())
        self.assertIn(SLUG, msg)
        self.add('--gpx', path, '--publish-track', '--allow-duplicate', title='Same Line Again', activity='ski')
        self.assertEqual(self.track('same-line-again'), self.track())

    def test_dry_run_writes_nothing(self):
        path = self.gpx('single.gpx', gf.SINGLE)
        out = self.add('--gpx', path, '--publish-track', '--dry-run')
        self.assertEqual(os.listdir(self.trips), [])
        self.assertIn('dry', out.lower())
        self.assertIn(SLUG, out)
        out = self.add('--dry-run', title='Just An Idea')
        self.assertEqual(os.listdir(self.trips), [])
        self.assertNoRender()

    def test_existing_slug_is_refused_and_suggests_slug(self):
        self.add('--notes', 'first')
        before = read(os.path.join(self.folder(), 'index.md'), 'rb')
        msg = self.fails('add', '--title', TITLE, '--activity', 'ski', '--no-render', '--notes', 'second')
        self.assertIn('--slug', msg)
        self.assertEqual(read(os.path.join(self.folder(), 'index.md'), 'rb'), before)
        self.assertEqual(self.files(), ['goal.json', 'index.md'])

    def test_slug_traversal_and_bad_slugs_are_rejected(self):
        parent = os.path.dirname(self.trips)
        before = sorted(os.listdir(parent))
        for bad in ('../evil', 'a/b', '/abs', '..', 'Bad Slug', 'ridge.', ''):
            with self.subTest(slug=bad):
                self.fails('add', '--title', TITLE, '--activity', 'hike', '--no-render', '--slug', bad)
        self.assertEqual(os.listdir(self.trips), [])
        self.assertEqual(sorted(os.listdir(parent)), before)
        self.assertFalse(os.path.exists(os.path.join(parent, 'evil')))

    def test_unsafe_or_missing_gpx_is_refused(self):
        for name, text in (('doctype.gpx', gf.DOCTYPE), ('entity.gpx', gf.ENTITY_IN_COMMENT), ('kml.gpx', gf.NON_GPX_ROOT),
                           ('lat.gpx', gf.LAT_OUT), ('broken.gpx', gf.NOT_XML)):
            with self.subTest(file=name):
                self.fails('add', '--title', TITLE, '--activity', 'hike', '--no-render', '--gpx', self.gpx(name, text), '--publish-track')
        self.fails('add', '--title', TITLE, '--activity', 'hike', '--no-render', '--gpx', os.path.join(self.src, 'nope.gpx'))
        self.assertEqual(os.listdir(self.trips), [])

    def test_unknown_activity_is_refused(self):
        self.fails('add', '--title', TITLE, '--activity', 'swim', '--no-render')
        self.assertEqual(os.listdir(self.trips), [])

    def test_render_runs_after_publishing_and_a_failure_is_only_a_warning(self):
        self.render_rc = 1
        path = self.gpx('single.gpx', gf.SINGLE)
        out = self.add('--gpx', path, '--publish-track', render=True)
        renders = [c for c in self.calls if any(x.endswith('render.py') for x in c)]
        self.assertEqual(len(renders), 1, self.calls)
        self.assertIn(SLUG, renders[0])
        self.assertNotIn('add_trip.py', ' '.join(renders[0]))
        self.assertIn('render', out.lower())
        t = self.load()   # the goal stays valid
        self.assertEqual(t['goal']['route']['source_sha256'], sha256(self.track()))

    def test_render_is_not_run_for_a_metadata_only_goal_even_without_no_render(self):
        self.add(render=True)
        self.assertNoRender()

    def test_never_calls_add_trip(self):
        self.add('--gpx', self.gpx('single.gpx', gf.SINGLE), '--publish-track', render=True)
        self.assertFalse(any('add_trip' in ' '.join(c) for c in self.calls))
        self.assertNotIn('add_trip', set(sys.modules) - self.modules_before)


# ---------------------------------------------------------------- update

class UpdateTests(CliFixture):

    def setUp(self):
        super().setUp()
        self.add()
        self.index_before = read(os.path.join(self.folder(), 'index.md'), 'rb')

    def assertIndexUnchanged(self):
        self.assertEqual(read(os.path.join(self.folder(), 'index.md'), 'rb'), self.index_before)

    def test_status_and_priority(self):
        self.ok('update', SLUG, '--status', 'shortlisted', '--priority', 'high')
        g = self.goal()
        self.assertEqual((g['status'], g['priority']), ('shortlisted', 'high'))
        self.assertEqual(g['added_at'], TODAY)   # the rest is untouched
        self.assertIndexUnchanged()
        self.assertIs(self.load()['goal']['legacy'], False)

    def test_archive_and_unarchive(self):
        self.ok('update', SLUG, '--archived', 'true')
        self.assertTrue(self.goal()['archived'])
        self.ok('update', SLUG, '--archived', 'false')
        self.assertFalse(self.goal()['archived'])

    def test_intent_fields(self):
        self.ok('update', SLUG, '--tags', 'couloir,ski', '--why', 'Steep and short.', '--months', '4,5', '--year', '2028',
                '--commitment', 'half-day', '--scope', 'partial', '--source-kind', 'third-party-recording',
                '--source-url', 'https://example.test/rec', '--source-label', 'A recording', '--checked-at', '2026-09-01')
        g = self.goal()
        self.assertEqual(g['tags'], ['couloir', 'ski'])
        self.assertEqual(g['why'], 'Steep and short.')
        self.assertEqual(sorted(g['target_months']), [4, 5])
        self.assertEqual(g['target_year'], 2028)
        self.assertEqual((g['time_commitment'], g['route_scope']), ('half-day', 'partial'))
        self.assertEqual(g['route_source']['kind'], 'third-party-recording')
        self.assertEqual(g['route_source']['url'], 'https://example.test/rec')
        self.assertEqual(g['route_source']['label'], 'A recording')
        self.assertEqual(g['route_source']['checked_at'], '2026-09-01')

    def test_checklist_add_check_uncheck(self):
        self.ok('update', SLUG, '--add-check', 'Does the file include the descent?')
        cl = self.goal()['checklist']
        self.assertEqual(len(cl), 1)
        self.assertEqual(cl[0]['text'], 'Does the file include the descent?')
        self.assertIs(cl[0]['done'], False)
        cid = cl[0]['id']
        self.assertTrue(cid)
        self.ok('update', SLUG, '--check', cid)
        self.assertIs(self.goal()['checklist'][0]['done'], True)
        self.ok('update', SLUG, '--uncheck', cid)
        self.assertIs(self.goal()['checklist'][0]['done'], False)
        self.fails('update', SLUG, '--check', 'no-such-item')

    def test_add_reference(self):
        self.ok('update', SLUG, '--add-reference', 'guide-1|Synthetic guidebook|https://example.test/guide', '--reference-checked-at', '2026-09-02')
        refs = self.goal()['references']
        self.assertEqual(len(refs), 1)
        self.assertEqual((refs[0]['id'], refs[0]['label'], refs[0]['url']), ('guide-1', 'Synthetic guidebook', 'https://example.test/guide'))
        self.assertEqual(refs[0]['checked_at'], '2026-09-02')
        self.fails('update', SLUG, '--add-reference', 'guide-1|Again|https://example.test/again')   # duplicate id
        self.fails('update', SLUG, '--add-reference', 'guide-2|Bad scheme|ftp://example.test/x')
        self.assertEqual(len(self.goal()['references']), 1)

    def test_a_reference_date_and_the_route_source_date_never_overwrite_each_other(self):
        self.ok('update', SLUG, '--source-kind', 'planner-export', '--source-url', 'https://example.test/plan', '--checked-at', '2026-01-01')
        self.assertEqual(self.goal()['route_source']['checked_at'], '2026-01-01')
        # adding a reference, dated or not, leaves the route source's date alone
        self.ok('update', SLUG, '--add-reference', 'guide-1|Synthetic guidebook|https://example.test/guide', '--reference-checked-at', '2026-09-02')
        self.ok('update', SLUG, '--add-reference', 'guide-2|Second guide|https://example.test/guide2')
        g = self.goal()
        self.assertEqual(g['route_source']['checked_at'], '2026-01-01')
        self.assertEqual([r['checked_at'] for r in g['references']], ['2026-09-02', TODAY])     # undated: the day it was added
        # and the route source's date, given with a reference in one command, stamps only the route source
        self.ok('update', SLUG, '--checked-at', '2026-03-03', '--add-reference', 'guide-3|Third guide|https://example.test/guide3')
        g = self.goal()
        self.assertEqual(g['route_source']['checked_at'], '2026-03-03')
        self.assertEqual(g['references'][2]['checked_at'], TODAY)
        # repeatable in one command, all with the one reference date
        self.ok('update', SLUG, '--add-reference', 'a-1|A|https://example.test/a', '--add-reference', 'b-1|B|https://example.test/b',
                '--reference-checked-at', '2026-04-04')
        self.assertEqual([r['checked_at'] for r in self.goal()['references'][3:]], ['2026-04-04', '2026-04-04'])
        self.fails('update', SLUG, '--reference-checked-at', '2026-05-05')                        # nothing to date
        self.fails('update', SLUG, '--add-reference', 'c-1|C|https://example.test/c', '--reference-checked-at', 'last week')
        self.assertEqual(len(self.goal()['references']), 5)

    def test_status_completed_without_an_outing_is_rejected(self):
        before = read(os.path.join(self.folder(), 'goal.json'), 'rb')
        msg = self.fails('update', SLUG, '--status', 'completed')
        self.assertIn('log-outing', msg)
        self.assertEqual(read(os.path.join(self.folder(), 'goal.json'), 'rb'), before)

    def test_status_attempted_without_an_outing_is_rejected(self):
        before = read(os.path.join(self.folder(), 'goal.json'), 'rb')
        self.fails('update', SLUG, '--status', 'attempted')
        self.assertEqual(read(os.path.join(self.folder(), 'goal.json'), 'rb'), before)

    def test_invalid_values_leave_the_file_unchanged(self):
        before = read(os.path.join(self.folder(), 'goal.json'), 'rb')
        self.fails('update', SLUG, '--priority', 'urgent')
        self.fails('update', SLUG, '--months', '13')
        self.fails('update', SLUG, '--source-url', 'javascript:alert(1)')
        self.fails('update', SLUG, '--source-kind', 'author-drawn')   # needs an approximation note
        self.assertEqual(read(os.path.join(self.folder(), 'goal.json'), 'rb'), before)
        self.ok('update', SLUG, '--source-kind', 'author-drawn', '--approximation-note', 'A sketch, not a recording.')
        self.assertEqual(self.goal()['route_source']['approximation_note'], 'A sketch, not a recording.')

    def test_unknown_slug_and_non_planned_trip_are_refused(self):
        self.fails('update', 'no-such-goal', '--status', 'shortlisted')
        self.report()
        self.fails('update', 'real-report', '--status', 'shortlisted')
        self.assertFalse(os.path.exists(os.path.join(self.folder('real-report'), 'goal.json')))
        self.fails('update', '../evil', '--status', 'shortlisted')

    def test_dry_run_writes_nothing(self):
        before = read(os.path.join(self.folder(), 'goal.json'), 'rb')
        out = self.ok('update', SLUG, '--status', 'shortlisted', '--dry-run')
        self.assertEqual(read(os.path.join(self.folder(), 'goal.json'), 'rb'), before)
        self.assertIn('goal.json', out)

    def test_legacy_goal_gets_a_sidecar_on_first_update(self):
        helpers.make_trip(self.trips, 'legacy-ridge', title='Legacy Ridge', activity='ski', kind='planned', track=True)
        self.ok('update', 'legacy-ridge', '--priority', 'someday')
        g = self.goal('legacy-ridge')
        self.assertEqual((g['status'], g['priority']), ('idea', 'someday'))
        self.assertIs(self.load('legacy-ridge')['goal']['legacy'], False)
        self.assertEqual(read(os.path.join(self.folder('legacy-ridge'), 'track.gpx'), 'rb'), b'')   # the GPX is untouched


# ---------------------------------------------------------------- log-outing

class LogOutingTests(CliFixture):

    def setUp(self):
        super().setUp()
        self.add('--gpx', self.gpx('single.gpx', gf.SINGLE), '--publish-track')
        self.report()
        # the report's recording holds real bytes (a different route than the goal's), so a command that copied the planned
        # track over it, or rewrote it, changes its checksum
        with open(os.path.join(self.folder('real-report'), 'track.gpx'), 'w', encoding='utf-8') as fh:
            fh.write(gf.ROUTE_ONLY)
        self.track_before = self.track()
        self.report_before = read(os.path.join(self.folder('real-report'), 'index.md'), 'rb')
        self.hashes_before = self.folder_hashes(skip=(os.path.join(SLUG, 'goal.json'),))

    def folder_hashes(self, skip=()):
        """{relative path: sha256} of every file under the stand-in content/trips/, but the paths in skip."""
        out = {}
        for base, _dirs, names in os.walk(self.trips):
            for n in names:
                rel = os.path.relpath(os.path.join(base, n), self.trips)
                if rel not in skip:
                    out[rel] = hashlib.sha256(read(os.path.join(base, n), 'rb')).hexdigest()
        return out

    def assertUntouched(self):
        self.assertEqual(self.track(), self.track_before)
        self.assertEqual(read(os.path.join(self.folder('real-report'), 'index.md'), 'rb'), self.report_before)
        self.assertEqual(sorted(os.listdir(self.folder('real-report'))), ['index.md', 'track.gpx'])
        # nothing but the goal's own goal.json changed anywhere: the report's recording keeps its checksum
        self.assertEqual(self.folder_hashes(skip=(os.path.join(SLUG, 'goal.json'),)), self.hashes_before)
        self.assertNotEqual(read(os.path.join(self.folder('real-report'), 'track.gpx'), 'rb'), self.track_before)

    def test_attempted_then_completed(self):
        self.ok('log-outing', SLUG, '--outcome', 'attempted', '--date', '2026-07-12', '--note', 'Turned around at the notch.')
        g = self.goal()
        self.assertEqual(g['status'], 'attempted')
        self.assertEqual(len(g['outings']), 1)
        self.assertEqual((g['outings'][0]['outcome'], g['outings'][0]['date'], g['outings'][0]['report_slug']), ('attempted', '2026-07-12', None))
        self.assertEqual(g['outings'][0]['note'], 'Turned around at the notch.')
        self.ok('log-outing', SLUG, '--outcome', 'completed', '--date', '2026-08-30', '--report-slug', 'real-report')
        g = self.goal()
        self.assertEqual(g['status'], 'completed')
        self.assertEqual([o['outcome'] for o in g['outings']], ['attempted', 'completed'])
        self.assertEqual(g['outings'][1]['report_slug'], 'real-report')
        self.assertUntouched()
        t = self.load()
        self.assertEqual(t['kind'], 'planned')   # the goal stays a goal
        self.assertEqual(t['goal']['status'], 'completed')
        self.assertNoRender()

    def test_completed_without_date_or_report(self):
        out = self.ok('log-outing', SLUG, '--outcome', 'completed')
        g = self.goal()
        self.assertEqual(g['status'], 'completed')
        self.assertEqual(g['outings'], [{'outcome': 'completed', 'date': None, 'report_slug': None, 'note': ''}])
        self.assertIn('date', out.lower())
        self.assertIs(self.load()['goal']['legacy'], False)

    def test_report_slug_must_be_a_published_non_planned_trip(self):
        helpers.make_trip(self.trips, 'other-goal', title='Other Goal', activity='hike', kind='planned', track=True)
        helpers.make_trip(self.trips, 'secret-draft', title='Secret Draft', activity='hike', date='2026-08-01', draft=True, track=True)
        before = read(os.path.join(self.folder(), 'goal.json'), 'rb')
        for bad in ('other-goal', 'secret-draft', 'no-such-report', '../real-report'):
            with self.subTest(report=bad):
                self.fails('log-outing', SLUG, '--outcome', 'completed', '--report-slug', bad)
        self.assertEqual(read(os.path.join(self.folder(), 'goal.json'), 'rb'), before)

    def test_an_attempt_after_completion_keeps_the_goal_completed(self):
        self.ok('log-outing', SLUG, '--outcome', 'completed', '--report-slug', 'real-report')
        self.ok('log-outing', SLUG, '--outcome', 'attempted', '--date', '2026-09-20')
        g = self.goal()
        self.assertEqual(g['status'], 'completed')
        self.assertEqual([o['outcome'] for o in g['outings']], ['completed', 'attempted'])
        self.assertUntouched()

    def test_reopening_a_completed_goal_keeps_its_outings(self):
        self.ok('log-outing', SLUG, '--outcome', 'attempted', '--date', '2026-07-12')
        self.ok('log-outing', SLUG, '--outcome', 'completed', '--date', '2026-08-30', '--report-slug', 'real-report')
        refused = self.fails('update', SLUG, '--status', 'researching')            # a plain flip is still refused...
        self.assertIn('--reopen', refused)                                          # ...and says how to reopen
        self.assertEqual(self.goal()['status'], 'completed')
        self.fails('update', SLUG, '--reopen')                                      # needs the status to go back to
        self.fails('update', SLUG, '--reopen', '--status', 'completed')
        self.assertEqual(len(self.goal()['outings']), 2)
        out = self.ok('update', SLUG, '--reopen', '--status', 'shortlisted', '--reopen-note', 'Back for the north side.')
        g = self.goal()
        self.assertEqual(g['status'], 'shortlisted')
        self.assertEqual([o['outcome'] for o in g['outings']], ['attempted', 'completed', 'reopened'])
        self.assertEqual(g['outings'][1], {'outcome': 'completed', 'date': '2026-08-30', 'report_slug': 'real-report', 'note': ''})
        self.assertEqual(g['outings'][2]['note'], 'Back for the north side.')
        self.assertIsNone(g['outings'][2]['report_slug'])
        self.assertEqual(g['outings'][2]['date'], TODAY)
        self.assertIn('reopened', out.lower())
        self.assertIs(self.goals.is_active(self.load()['goal']), True)
        self.assertUntouched()
        # a second completion closes it again, with the whole history kept
        self.ok('log-outing', SLUG, '--outcome', 'completed')
        g = self.goal()
        self.assertEqual(g['status'], 'completed')
        self.assertEqual([o['outcome'] for o in g['outings']], ['attempted', 'completed', 'reopened', 'completed'])

    def test_reopen_is_only_for_a_completed_goal_and_dry_run_writes_nothing(self):
        before = read(os.path.join(self.folder(), 'goal.json'), 'rb')
        self.fails('update', SLUG, '--reopen', '--status', 'researching')           # not completed yet
        self.fails('update', SLUG, '--reopen-note', 'no reopen given')
        self.assertEqual(read(os.path.join(self.folder(), 'goal.json'), 'rb'), before)
        self.ok('log-outing', SLUG, '--outcome', 'completed')
        done = read(os.path.join(self.folder(), 'goal.json'), 'rb')
        self.ok('update', SLUG, '--reopen', '--status', 'idea', '--dry-run')
        self.assertEqual(read(os.path.join(self.folder(), 'goal.json'), 'rb'), done)

    def test_bad_date_or_outcome_is_refused(self):
        before = read(os.path.join(self.folder(), 'goal.json'), 'rb')
        self.fails('log-outing', SLUG, '--outcome', 'completed', '--date', 'last summer')
        self.fails('log-outing', SLUG, '--outcome', 'summited')
        self.fails('log-outing', 'real-report', '--outcome', 'completed')   # a report is not a goal
        self.assertEqual(read(os.path.join(self.folder(), 'goal.json'), 'rb'), before)

    def test_dry_run_writes_nothing(self):
        before = read(os.path.join(self.folder(), 'goal.json'), 'rb')
        self.ok('log-outing', SLUG, '--outcome', 'attempted', '--dry-run')
        self.assertEqual(read(os.path.join(self.folder(), 'goal.json'), 'rb'), before)


# ---------------------------------------------------------------- review-packet and export

class ReviewPacketTests(CliFixture):

    def setUp(self):
        super().setUp()
        self.add('--gpx', self.gpx('single.gpx', gf.SINGLE), '--publish-track', '--why', 'A ridge I keep seeing.',
                 '--notes', 'Check the creek crossing.')
        self.ok('update', SLUG, '--add-reference', 'guide-1|Synthetic guidebook|https://example.test/guide')

    def test_refuses_a_path_inside_the_repository(self):
        # a stand-in checkout, so a regression of the guard writes into the temp folder and never into the real repository
        fake_root = os.path.join(self.src, 'checkout')
        os.makedirs(os.path.join(fake_root, 'docs'))
        with mock.patch.object(self.cli, 'ROOT', fake_root):
            inside = os.path.join(fake_root, 'docs', 'packet.md')
            msg = self.fails('review-packet', SLUG, '--out', inside)
            self.assertFalse(os.path.exists(inside))
            self.assertIn('outside', msg.lower())
            nested = os.path.join(fake_root, '_site', 'x', 'packet.md')
            self.fails('review-packet', SLUG, '--out', nested)
            self.assertFalse(os.path.exists(os.path.dirname(nested)))
            self.fails('review-packet', SLUG, '--out', fake_root)
            # through a symbolic link that leads into the checkout
            link = os.path.join(self.src, 'looks-outside')
            try:
                os.symlink(os.path.join(fake_root, 'docs'), link)
            except (OSError, NotImplementedError):
                return
            msg = self.fails('review-packet', SLUG, '--out', os.path.join(link, 'packet.md'))
            self.assertIn('outside', msg.lower())
            self.assertEqual(os.listdir(os.path.join(fake_root, 'docs')), [])

    def test_writes_a_packet_outside(self):
        out = os.path.join(self.src, 'packets', 'goal-review.md')
        self.ok('review-packet', SLUG, '--out', out)
        text = read(out)
        self.assertIn(TITLE, text)
        self.assertIn(SLUG, text)
        self.assertIn('https://example.test/guide', text)
        self.assertIn('A ridge I keep seeing.', text)
        self.assertIn('Check the creek crossing.', text)
        for key in ('proposed_value', 'source_ids', 'checked_at', 'qualification'):
            self.assertIn(key, text)
        self.assertIn('Add or enrich this future goal', text)   # the enrichment prompt, verbatim from the guide
        low = text.lower()
        self.assertIn('missing', low)
        self.assertIn('approx', low)
        self.assertNotIn(self.src, text.replace(out, ''))   # the local GPX path never reaches the packet
        self.assertNoRender()

    def test_dry_run_writes_nothing(self):
        out = os.path.join(self.src, 'dry.md')
        self.ok('review-packet', SLUG, '--out', out, '--dry-run')
        self.assertFalse(os.path.exists(out))


class ExportTests(CliFixture):

    def undraft(self, slug):
        p = os.path.join(self.folder(slug), 'index.md')
        meta, body = frontmatter.split(read(p))
        meta.pop('draft', None)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(frontmatter.render(meta, body))

    def setUp(self):
        super().setUp()
        self.gpx_path = self.gpx('single.gpx', gf.SINGLE)
        self.add('--gpx', self.gpx_path, '--publish-track', '--region', 'Nowhere Range', '--why', 'Long ridge.', '--tags', 'ridge',
                 '--months', '6,7', '--year', '2027', '--commitment', 'full-day', '--scope', 'approach-only',
                 '--source-kind', 'third-party-recording', '--source-url', 'https://example.test/rec', '--source-label', 'A recording')
        self.ok('update', SLUG, '--add-reference', 'guide-1|Synthetic guidebook|https://example.test/guide')
        self.report()
        self.ok('log-outing', SLUG, '--outcome', 'completed', '--date', '2026-08-30', '--report-slug', 'real-report')
        # proposed, unreviewed evidence for a field that needs no approval: must never be exported
        p = os.path.join(self.folder(), 'goal.json')
        g = json.loads(read(p))
        g['field_evidence'] = {'region': {'source_ids': ['guide-1'], 'status': 'proposed'}}
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(g, fh)
        self.undraft(SLUG)
        self.add(title='Still A Draft')   # stays draft: true

    def export(self, *extra):
        out = os.path.join(self.src, 'export', 'tick-list.json')
        self.ok('export', '--out', out, *extra)
        return read(out)

    def test_lists_the_public_fields_of_non_draft_goals_only(self):
        text = self.export()
        data = json.loads(text)
        self.assertEqual([r['slug'] for r in data], [SLUG])
        self.assertNotIn('still-a-draft', text)
        r = data[0]
        self.assertEqual(r['url'], 'trips/%s/' % SLUG)
        self.assertEqual((r['title'], r['activity'], r['region']), (TITLE, 'hike', 'Nowhere Range'))
        self.assertEqual((r['status'], r['priority'], r['archived']), ('completed', 'normal', False))
        self.assertEqual((r['tags'], r['why']), (['ridge'], 'Long ridge.'))
        self.assertEqual((sorted(r['target_months']), r['target_year']), ([6, 7], 2027))
        self.assertEqual((r['time_commitment'], r['route_scope']), ('full-day', 'approach-only'))
        for k in ('kind', 'label', 'url', 'checked_at'):
            self.assertIn(k, r['route_source'])
        self.assertEqual(r['route_source']['kind'], 'third-party-recording')
        self.assertNotIn('public_copy_approved', r['route_source'])
        self.assertEqual(r['references'][0]['url'], 'https://example.test/guide')
        self.assertEqual(len(r['outings']), 1)
        self.assertIn('trips/real-report/', text)   # the outing's report as a url
        self.assertIn('distance_km', text)

    def test_excludes_local_paths_and_proposed_evidence(self):
        text = self.export()
        self.assertNotIn(self.src, text)
        self.assertNotIn('gpx-src', text)
        self.assertNotIn(self.trips, text)
        self.assertNotIn(ROOT, text)
        self.assertNotIn('proposed', text)
        self.assertNotIn('field_evidence', text)
        self.assertNotIn('source_sha256', text)

    def test_stdout_without_out(self):
        code, out, err = self.run_cli('export')
        self.assertEqual(code, 0, err)
        data = json.loads(out)
        self.assertEqual([r['slug'] for r in data], [SLUG])

    def test_dry_run_writes_nothing(self):
        out = os.path.join(self.src, 'dry.json')
        self.ok('export', '--out', out, '--dry-run')
        self.assertFalse(os.path.exists(out))
        self.assertNoRender()


if __name__ == '__main__':
    unittest.main()
