"""Phase 6: tools/add_trip.py driven end to end through main(argv), pinned to the Phase 6 contract (the add_trip section).

Every run writes into a temp dir: add_trip.TRIPS is patched to <tmp>/trips for the whole of each test, and a listing of
the real content/trips/ is compared before and after as a guard. The inputs are synthetic and live in <tmp>/src: a
20-point GPX (a zigzag north from 38.9 N 120.1 W, open water, so nothing is a real route) stamped a minute apart from the
fixture clock 2026-07-04 15:00 UTC (08:00 in Los Angeles, the zone guess_tz gives there); the hand-built three-record FIT
of tests/test_fit_reader.py (build_fit and POINTS are imported from that module, so both files decode the same bytes);
zips of them; and Strava exports written with the CSV helpers of tests/test_strava_export.py (two Distance columns, an
Elapsed Time pair, a Media list of .jpg files). Existing trips are helpers.make_trip fixtures.

Nothing is drawn or converted: photolib.web_copies is replaced by a stub that writes three placeholder files
(<base>.webp, .sm.webp, .th.webp) and answers ('webp', 1600, 1200), the way tests/test_thumbs.py stubs thumb_copy, and the
photo inputs are .jpg (anything else would call sips). subprocess.run is replaced by a recorder; --no-render is passed
everywhere except the one test that checks the two render.py commands, and every other test asserts nothing was run.
"""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import add_trip  # noqa: E402  (tools/add_trip.py: tools/ is on sys.path)
import checks  # noqa: E402
import frontmatter  # noqa: E402
import photos as photolib  # noqa: E402

import gpx_fixtures as gf  # noqa: E402
import helpers  # noqa: E402
from helpers import photo  # noqa: E402
import test_fit_reader as fitfix  # noqa: E402  (the hand-built FIT: build_fit, POINTS)
import test_strava_export as sx  # noqa: E402  (the synthetic activities.csv: HEADER, row, write_export)

GPX_NS = '{http://www.topografix.com/GPX/1/1}'
TITLE = 'Synthetic Ridge Traverse'
SLUG = 'synthetic-ridge-traverse'
PLACEHOLDER = '<!-- Write the trip report here (Markdown). -->'
MOVE = ('Move the folder out of content/trips/ first (git keeps the old one: git checkout -- content/trips/%s restores it).'
        % SLUG)

# 20 points a minute apart, zigzagging 35 m east and back so the simplifier keeps them, with ups and downs in elevation
ELES = [2000, 2006, 2011, 2009, 2017, 2024, 2030, 2028, 2035, 2041, 2047, 2052, 2050, 2058, 2063, 2070, 2068, 2075, 2081, 2088]
PTS = [(round(38.900 + i * 0.001, 6), -120.1004 if i % 2 else -120.1, ELES[i], gf.iso(i)) for i in range(20)]
GPX = gf.gpx(gf.trk([PTS], 'Synthetic recording'))

# the day the fixture clock falls on, and its start, in the zones the tests use
DAY = '2026-07-04'
START_LA = '08:00'         # America/Los_Angeles (guessed for 38.9 N 120.1 W), PDT
START_CHICAGO = '10:00'    # America/Chicago, CDT

WRITE_UP = 'An invented day on a synthetic ridge, written only for this test.'


def read(path, mode='r'):
    with open(path, mode, **({} if 'b' in mode else {'encoding': 'utf-8'})) as fh:
        return fh.read()


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb' if isinstance(data, bytes) else 'w', **({} if isinstance(data, bytes) else {'encoding': 'utf-8'})) as fh:
        fh.write(data)
    return path


def tree(root):
    """Every file under root as {relative path: bytes}, and every folder as {relative path + '/': None}."""
    out = {}
    for base, dirs, files in os.walk(root):
        for d in dirs:
            out[os.path.relpath(os.path.join(base, d), root) + '/'] = None
        for name in files:
            path = os.path.join(base, name)
            out[os.path.relpath(path, root)] = read(path, 'rb')
    return out


def front(path):
    """(meta, body) of a written index.md or day file."""
    return frontmatter.split(read(path))


class AddTripFixture(unittest.TestCase):

    def setUp(self):
        self.real_trips = os.path.join(ROOT, 'content', 'trips')
        self.real_listing = sorted(os.listdir(self.real_trips)) if os.path.isdir(self.real_trips) else []
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        self.trips = os.path.join(self.tmp, 'trips')     # stands in for content/trips/
        self.src = os.path.join(self.tmp, 'src')         # the recordings, photos and exports given to the tool
        os.makedirs(self.trips)
        os.makedirs(self.src)
        self.copies = []          # (src, dst_base) of every web_copies call
        self.runs = []            # the argv of every subprocess.run call
        self.allow_runs = False
        for target, name, new in ((add_trip, 'TRIPS', self.trips),
                                  (add_trip.photolib, 'web_copies', self.fake_web_copies),
                                  (add_trip.subprocess, 'run', self.fake_run)):
            p = mock.patch.object(target, name, new)
            p.start()
            self.addCleanup(p.stop)
        # add_trip.py works on the modules patched above, not on copies of them
        self.assertIs(add_trip.photolib, photolib)
        self.assertIs(add_trip.subprocess, subprocess)

    def tearDown(self):
        if os.path.isdir(self.real_trips):
            self.assertEqual(sorted(os.listdir(self.real_trips)), self.real_listing,
                             'add_trip.py wrote into the real content/trips/: remove the new entries by hand')
        if not self.allow_runs:
            self.assertEqual(self.runs, [], 'a command was run (render.py or sips) where none should be')
        outside = [dst for _src, dst in self.copies if not dst.startswith(self.trips + os.sep)]
        self.assertEqual(outside, [], 'a photo copy was written outside the temp trips folder')

    # ------------------------------------------------------------ stubs

    def fake_web_copies(self, src, dst_base, *args, **kw):
        """photolib.web_copies without sips or cwebp: note the call, write the three copies as placeholders."""
        self.copies.append((src, dst_base))
        os.makedirs(os.path.dirname(dst_base), exist_ok=True)
        for suffix in ('.webp', '.sm.webp', '.th.webp'):
            with open(dst_base + suffix, 'wb') as fh:
                fh.write(b'placeholder')
        return 'webp', 1600, 1200

    def fake_run(self, args, *a, **kw):
        self.runs.append([str(x) for x in args])
        return subprocess.CompletedProcess(args, 0)

    # ------------------------------------------------------------ running

    def run_main(self, *argv):
        """(exit status, stdout, stderr) of add_trip.main(argv). A SystemExit fails the test: use usage_error for those."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = add_trip.main([str(a) for a in argv])
            except SystemExit as ex:
                code = ('SystemExit', ex.code)
        if isinstance(code, tuple):
            self.fail('main(%r) raised SystemExit(%r): %s' % (argv, code[1], err.getvalue()))
        return code, out.getvalue(), err.getvalue()

    def ok(self, *argv):
        code, out, err = self.run_main(*argv)
        self.assertEqual(code, 0, 'exit %r; stderr: %s' % (code, err))
        return out

    def refused(self, *argv):
        """stderr of a run that returns exit status 1."""
        code, out, err = self.run_main(*argv)
        self.assertEqual(code, 1, 'exit %r; stdout: %s; stderr: %s' % (code, out, err))
        return err

    def usage_error(self, *argv):
        """stderr of a run that stops with argparse's SystemExit(2)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                add_trip.main([str(a) for a in argv])
        self.assertEqual(cm.exception.code, 2, err.getvalue())
        return err.getvalue()

    # ------------------------------------------------------------ inputs

    def gpx_file(self, name='Synthetic_Recording.gpx', text=GPX):
        return write(os.path.join(self.src, name), text)

    def fit_file(self, name='Synthetic_Fit_Track.fit'):
        return write(os.path.join(self.src, name), fitfix.build_fit(fitfix.POINTS))

    def jpgs(self, *names, **kw):
        """Empty .jpg files in a folder of src (the stub never reads them); returns the folder."""
        folder = os.path.join(self.src, kw.get('folder', 'shots'))
        for n in names:
            write(os.path.join(folder, n), b'')
        return folder

    def import_gpx(self, *extra):
        """The plain import every other test starts from: the GPX, TITLE, hike, --no-render."""
        return self.ok(self.gpx_file(), '--title', TITLE, '--activity', 'hike', '--no-render', *extra)

    def path(self, *parts):
        return os.path.join(self.trips, *parts)

    def steps(self, out):
        """The numbered lines after 'Next steps:', checked to run 1, 2, 3 ... with nothing after them."""
        lines = out.splitlines()
        self.assertIn('Next steps:', lines)
        rest = lines[lines.index('Next steps:') + 1:]
        got = []
        for line in rest:
            m = re.match(r'^  (\d+)\. (\S.*)$', line)
            self.assertIsNotNone(m, 'not a numbered step: %r' % line)
            got.append((int(m.group(1)), m.group(2)))
        self.assertEqual([n for n, _ in got], list(range(1, len(got) + 1)))
        self.assertGreater(len(got), 2)
        return [s for _, s in got]


# ---------------------------------------------------------------- a new trip


class NewTripTests(AddTripFixture):

    def test_a_gpx_import_writes_the_trip_folder_with_index_md_and_track_gpx(self):
        out = self.import_gpx()
        self.assertTrue(os.path.isfile(self.path(SLUG, 'index.md')))
        self.assertTrue(os.path.isfile(self.path(SLUG, 'track.gpx')))
        self.assertEqual(sorted(os.listdir(self.trips)), [SLUG])
        meta, body = front(self.path(SLUG, 'index.md'))
        self.assertEqual((meta['title'], meta['activity'], meta['date'], meta['start_time'], meta['timezone']),
                         (TITLE, 'hike', DAY, START_LA, 'America/Los_Angeles'))
        self.assertEqual(meta['route_shape'], 'point-to-point')
        self.assertEqual(body.strip(), PLACEHOLDER)
        self.assertIn('created content/trips/%s/ (' % SLUG, out)
        self.assertIn('maps not drawn: python3 tools/render.py %s' % SLUG, out.splitlines())

    def test_the_stats_come_from_the_track(self):
        self.import_gpx()
        stats = front(self.path(SLUG, 'index.md'))[0]['stats']
        gain, loss = gf.ref_gain_loss(ELES)
        self.assertEqual((stats['gain_m'], stats['loss_m'], stats['high_m'], stats['low_m']), (gain, loss, max(ELES), min(ELES)))
        self.assertAlmostEqual(stats['distance_km'], gf.poly_km(PTS), delta=0.011)
        self.assertEqual(stats['elapsed'], '0:19')
        self.assertTrue(set(stats) <= set(checks.STATS_KEYS), stats)

    def test_every_index_md_key_is_one_the_validator_knows(self):
        shots = self.jpgs('a.jpg', 'b.jpg')
        self.ok(self.gpx_file(), '--title', TITLE, '--activity', 'other', '--subtype', 'SUP', '--place', 'Invented Saddle',
                '--region', 'Invented Coast', '--party', 'A friend', '--draft', '--photos', shots, '--no-render')
        meta, _body = front(self.path(SLUG, 'index.md'))
        self.assertEqual(set(meta), {'title', 'activity', 'subtype', 'date', 'start_time', 'timezone', 'place', 'region',
                                     'party', 'route_shape', 'stats', 'draft', 'photos'})
        self.assertTrue(set(meta) <= set(checks.INDEX_KEYS), set(meta) - set(checks.INDEX_KEYS))
        self.assertEqual((meta['subtype'], meta['place'], meta['region'], meta['party']),
                         ('SUP', 'Invented Saddle', 'Invented Coast', 'A friend'))
        for p in meta['photos']:
            self.assertTrue(set(p) <= set(checks.PHOTO_KEYS), p)

    def test_without_the_optional_flags_only_the_import_keys_are_written(self):
        self.import_gpx()
        meta, _body = front(self.path(SLUG, 'index.md'))
        self.assertEqual(set(meta), {'title', 'activity', 'date', 'start_time', 'timezone', 'route_shape', 'stats'})

    def test_the_track_gpx_is_well_formed_gpx_1_1_with_a_time_per_point(self):
        out = self.import_gpx()
        root = ET.parse(self.path(SLUG, 'track.gpx')).getroot()
        self.assertEqual((root.tag, root.get('version')), (GPX_NS + 'gpx', '1.1'))
        pts = list(root.iter(GPX_NS + 'trkpt'))
        kept = int(re.search(r'\((\d+) points kept of 20, 0 photos\)', out).group(1))
        self.assertEqual(len(pts), kept)
        self.assertGreater(kept, 2)
        self.assertEqual([p.find(GPX_NS + 'time') is not None for p in pts], [True] * kept)
        self.assertEqual([p.find(GPX_NS + 'ele') is not None for p in pts], [True] * kept)
        self.assertEqual(pts[0].find(GPX_NS + 'time').text, gf.iso(0))
        self.assertEqual(pts[-1].find(GPX_NS + 'time').text, gf.iso(19))
        self.assertEqual((pts[0].get('lat'), pts[0].get('lon')), ('38.900000', '-120.100000'))

    def test_strip_times_leaves_every_time_out_of_track_gpx(self):
        self.import_gpx('--strip-times')
        text = read(self.path(SLUG, 'track.gpx'))
        ET.fromstring(text.encode('utf-8'))
        self.assertNotIn('<time>', text)
        self.assertGreater(text.count('<trkpt '), 2)

    def test_draft_writes_draft_true_and_the_publish_step_stages_the_content_folder_alone(self):
        out = self.import_gpx('--draft')
        self.assertIs(front(self.path(SLUG, 'index.md'))[0]['draft'], True)
        steps = self.steps(out)
        publish = [s for s in steps if s.startswith('Publish')]
        self.assertEqual(len(publish), 1, steps)
        self.assertIn('git add "content/trips/%s" alone' % SLUG, publish[0])
        self.assertNotIn('rendered/trips', publish[0])
        self.assertFalse(any(s.startswith('Draw the maps') for s in steps), steps)

    def test_a_published_import_stages_its_rendered_folder_too(self):
        steps = self.steps(self.import_gpx())
        publish = [s for s in steps if s.startswith('Publish')][0]
        self.assertIn('git add "content/trips/%s" "rendered/trips/%s" rendered/site' % (SLUG, SLUG), publish)
        self.assertIn('Draw the maps (internet needed): python3 tools/render.py %s' % SLUG, steps)
        self.assertNotIn('draft', front(self.path(SLUG, 'index.md'))[0])

    def test_the_checklist_is_numbered_and_counts_the_empty_alt_lines(self):
        shots = self.jpgs('b.jpg', 'a.jpg', 'notes.txt')
        out = self.import_gpx('--photos', shots)
        steps = self.steps(out)
        self.assertIn('Describe the photos: 2 alt: lines are empty', ' '.join(steps))
        self.assertIn('Preview: python3 tools/build.py --serve --open %s' % SLUG, steps)
        self.assertTrue(steps[0].startswith('Edit content/trips/%s/index.md: ' % SLUG), steps[0])
        # the photos, in name order, as the stub's copies with empty alt lines
        meta = front(self.path(SLUG, 'index.md'))[0]
        self.assertEqual(meta['photos'], [{'file': 'photos/01.webp', 'w': 1600, 'h': 1200, 'alt': ''},
                                          {'file': 'photos/02.webp', 'w': 1600, 'h': 1200, 'alt': ''}])
        self.assertEqual([os.path.basename(s) for s, _d in self.copies], ['a.jpg', 'b.jpg'])
        self.assertEqual(sorted(os.listdir(self.path(SLUG, 'photos'))),
                         ['01.sm.webp', '01.th.webp', '01.webp', '02.sm.webp', '02.th.webp', '02.webp'])
        self.assertIn('created content/trips/%s/ (' % SLUG, out)
        self.assertIn(', 2 photos)', out)

    def test_one_photo_says_line_is(self):
        steps = self.steps(self.import_gpx('--photos', os.path.join(self.jpgs('a.jpg'), 'a.jpg')))
        self.assertIn('Describe the photos: 1 alt: line is empty', ' '.join(steps))

    def test_without_photos_there_is_no_describe_step(self):
        steps = self.steps(self.import_gpx())
        self.assertFalse(any('alt:' in s and s.startswith('Describe') for s in steps), steps)
        self.assertIn('Preview: python3 tools/build.py --serve --open %s' % SLUG, steps)

    def test_the_timezone_line_says_guessed(self):
        out = self.import_gpx()
        self.assertIn('timezone America/Los_Angeles, guessed; --timezone to change', out.splitlines())

    def test_the_timezone_line_says_from_timezone_and_the_start_follows_the_zone(self):
        out = self.import_gpx('--timezone', 'America/Chicago')
        self.assertIn('timezone America/Chicago, from --timezone', out.splitlines())
        meta = front(self.path(SLUG, 'index.md'))[0]
        self.assertEqual((meta['timezone'], meta['date'], meta['start_time']), ('America/Chicago', DAY, START_CHICAGO))

    def test_a_timezone_that_is_no_zone_name_is_a_usage_error_and_nothing_is_written(self):
        err = self.usage_error(self.gpx_file(), '--title', TITLE, '--activity', 'hike', '--timezone', 'Mars/Olympus',
                               '--no-render')
        self.assertIn('--timezone Mars/Olympus: not a time zone name', err)
        self.assertEqual(os.listdir(self.trips), [])

    def test_subtype_takes_only_the_sites_sub_types(self):
        err = self.usage_error(self.gpx_file(), '--title', TITLE, '--activity', 'other', '--subtype', 'Canoe', '--no-render')
        self.assertIn('invalid choice', err)
        self.assertIn('Canoe', err)
        self.assertEqual(os.listdir(self.trips), [])
        for sub in ('SUP', 'Rafting', 'Kayaking', 'Mountaineering'):
            with self.subTest(subtype=sub):
                slug = 'synthetic-' + sub.lower()
                self.ok(self.gpx_file(), '--title', TITLE, '--slug', slug, '--activity', 'other', '--subtype', sub, '--no-render')
                self.assertEqual(front(self.path(slug, 'index.md'))[0]['subtype'], sub)

    def test_a_fit_file_imports_end_to_end(self):
        out = self.ok(self.fit_file(), '--activity', 'ski', '--no-render')
        slug = 'synthetic-fit-track'           # the title comes from the file name
        meta, body = front(self.path(slug, 'index.md'))
        self.assertEqual((meta['title'], meta['activity'], meta['date'], meta['start_time'], meta['timezone']),
                         ('Synthetic Fit Track', 'ski', DAY, START_LA, 'America/Los_Angeles'))
        self.assertEqual(body.strip(), PLACEHOLDER)
        self.assertRegex(out, r'created content/trips/synthetic-fit-track/ \(\d+ points kept of 3, 0 photos\)')
        root = ET.parse(self.path(slug, 'track.gpx')).getroot()
        first = next(root.iter(GPX_NS + 'trkpt'))
        self.assertEqual((first.get('lat'), first.get('lon')), ('38.900000', '-120.100000'))
        self.assertEqual(first.find(GPX_NS + 'ele').text, '2000.0')
        self.assertEqual(first.find(GPX_NS + 'time').text, gf.iso(0))
        trk_type = root.find(GPX_NS + 'trk').find(GPX_NS + 'type')
        self.assertEqual(trk_type.text, 'ski')

    def test_a_zip_holding_the_gpx_imports_end_to_end(self):
        zpath = os.path.join(self.src, 'export-original.zip')
        with zipfile.ZipFile(zpath, 'w') as zf:
            zf.writestr('Synthetic_Recording.gpx', GPX)
            zf.writestr('__MACOSX/._Synthetic_Recording.gpx', b'resource fork')
        out = self.ok(zpath, '--title', TITLE, '--activity', 'hike', '--no-render')
        meta = front(self.path(SLUG, 'index.md'))[0]
        self.assertEqual((meta['date'], meta['start_time'], meta['timezone']), (DAY, START_LA, 'America/Los_Angeles'))
        self.assertIn('points kept of 20', out)
        ET.parse(self.path(SLUG, 'track.gpx'))
        # nothing was unpacked beside the zip
        self.assertEqual(sorted(os.listdir(self.src)), ['export-original.zip'])

    def test_a_zip_with_two_track_files_is_a_usage_error_naming_both(self):
        zpath = os.path.join(self.src, 'two.zip')
        with zipfile.ZipFile(zpath, 'w') as zf:
            zf.writestr('a.fit', fitfix.build_fit(fitfix.POINTS))
            zf.writestr('b.gpx', GPX)
        err = self.usage_error(zpath, '--title', TITLE, '--activity', 'hike', '--no-render')
        self.assertIn('the .zip holds 2 track files (a.fit, b.gpx)', err)
        self.assertEqual(os.listdir(self.trips), [])

    def test_without_no_render_render_py_runs_for_the_slug_then_status(self):
        self.allow_runs = True
        self.assertFalse(os.path.lexists(os.path.join(ROOT, 'rendered', 'trips', SLUG)), 'fixture slug names a real render')
        out = self.ok(self.gpx_file(), '--title', TITLE, '--activity', 'hike')
        render = os.path.join(add_trip.ROOT, 'tools', 'render.py')
        self.assertEqual(self.runs, [[sys.executable, render, SLUG], [sys.executable, render, '--status', SLUG]])
        self.assertNotIn('maps not drawn', out)
        # the recorder answers 0 to both commands, and their exit statuses are what decides: the maps count as drawn
        # (ReviewFixTests: a render or a status that answers 1 keeps the step)
        self.assertEqual([s for s in self.steps(out) if s.startswith('Draw the maps')], [])


# ---------------------------------------------------------------- an existing folder, --force


class ExistingFolderTests(AddTripFixture):

    def force(self, *extra):
        """A --force import over SLUG with one photo given; returns its stderr after checking exit status 1."""
        shots = self.jpgs('a.jpg')
        return self.refused(self.gpx_file(), '--title', TITLE, '--activity', 'hike', '--force', '--no-render',
                            '--photos', shots, *extra)

    def assert_untouched(self, before):
        self.assertEqual(tree(self.trips), before, 'the existing folder changed')
        self.assertEqual(self.copies, [], 'a photo was written')

    def test_an_existing_folder_without_force_is_refused_and_left_alone(self):
        self.import_gpx()
        before = tree(self.trips)
        err = self.refused(self.gpx_file(), '--title', TITLE, '--activity', 'ski', '--no-render')
        self.assertEqual(err, '%s already exists (use --slug or --force)\n' % self.path(SLUG))
        self.assert_untouched(before)

    def test_force_refuses_a_written_up_trip_with_alt_texts_and_writes_nothing(self):
        helpers.make_trip(self.trips, SLUG, title=TITLE, body=WRITE_UP, track=True,
                          photos=[photo('photos/01.webp', alt='A synthetic skier on an invented ridge.'),
                                  photo('photos/02.webp', alt='An invented cairn.')])
        index_before = read(self.path(SLUG, 'index.md'), 'rb')
        before = tree(self.trips)
        err = self.force()
        self.assertEqual(err.strip(), 'content/trips/%s/index.md has a write-up and 2 photo descriptions; --force would '
                                      'erase them. %s' % (SLUG, MOVE))
        self.assertEqual(read(self.path(SLUG, 'index.md'), 'rb'), index_before)
        self.assert_untouched(before)

    def test_force_refuses_a_write_up_alone_saying_it(self):
        helpers.make_trip(self.trips, SLUG, title=TITLE, body=WRITE_UP, photos=[photo('photos/01.webp', alt='')])
        before = tree(self.trips)
        err = self.force()
        self.assertEqual(err.strip(), 'content/trips/%s/index.md has a write-up; --force would erase it. %s' % (SLUG, MOVE))
        self.assert_untouched(before)

    def test_force_refuses_one_photo_description(self):
        helpers.make_trip(self.trips, SLUG, title=TITLE, body=PLACEHOLDER,
                          photos=[photo('photos/01.webp', alt='An invented cairn.'), photo('photos/02.webp', alt='')])
        before = tree(self.trips)
        err = self.force()
        self.assertEqual(err.strip(), 'content/trips/%s/index.md has 1 photo description; --force would erase it. %s'
                                      % (SLUG, MOVE))
        self.assert_untouched(before)

    def test_force_refuses_an_index_md_with_a_line_an_import_never_writes(self):
        kept = {'beta': [{'label': 'Grade', 'value': 'Easy'}], 'map': {'peaks': ['Invented Peak']},
                'cover_photo': 'photos/01.webp', 'cover_focal_x': 0.4, 'cover_focal_y': 0.6,
                'card_summary': 'A synthetic summary.', 'featured': True, 'search_aliases': ['invented'],
                'published_at': '2026-07-05', 'updated_at': '2026-07-06', 'kind': 'multi-day', 'end_date': '2026-07-05',
                'conditions': 'Firm synthetic snow.'}
        for key, value in kept.items():
            with self.subTest(key=key):
                helpers.make_trip(self.trips, SLUG, title=TITLE, body=PLACEHOLDER,
                                  photos=[photo('photos/01.webp', alt='')], **{key: value})
                before = tree(self.trips)
                err = self.force()
                self.assertEqual(err.strip(), 'content/trips/%s/index.md has the %s line; --force would erase it. %s'
                                              % (SLUG, key, MOVE))
                self.assert_untouched(before)
                os.remove(self.path(SLUG, 'index.md'))

    def test_force_names_two_kept_lines_and_says_them(self):
        helpers.make_trip(self.trips, SLUG, title=TITLE, body=PLACEHOLDER, cover_photo='photos/01.webp',
                          beta=[{'label': 'Grade', 'value': 'Easy'}])
        before = tree(self.trips)
        err = self.force()
        self.assertEqual(err.strip(), 'content/trips/%s/index.md has the beta and cover_photo lines; --force would erase '
                                      'them. %s' % (SLUG, MOVE))
        self.assert_untouched(before)

    def test_force_refuses_a_folder_with_day_files(self):
        helpers.make_trip(self.trips, SLUG, title=TITLE, body=PLACEHOLDER, days=[{'title': 'Day one', 'date': DAY}])
        before = tree(self.trips)
        err = self.force()
        self.assertEqual(err.strip(), 'content/trips/%s/ holds day files (days/); --force would erase them. %s' % (SLUG, MOVE))
        self.assert_untouched(before)

    def test_force_names_a_write_up_and_day_files_together(self):
        helpers.make_trip(self.trips, SLUG, title=TITLE, body=WRITE_UP, days=[{'title': 'Day one', 'date': DAY}])
        before = tree(self.trips)
        err = self.force()
        self.assertEqual(err.strip(), 'content/trips/%s/index.md has a write-up and the folder holds day files (days/); '
                                      '--force would erase them. %s' % (SLUG, MOVE))
        self.assert_untouched(before)

    def test_force_refuses_a_folder_with_a_goal_json(self):
        helpers.make_trip(self.trips, SLUG, title=TITLE, body=PLACEHOLDER)
        write(self.path(SLUG, 'goal.json'), json.dumps({'title': 'Invented goal'}))
        before = tree(self.trips)
        err = self.force()
        self.assertEqual(err.strip(), 'content/trips/%s/ holds a goal.json (a tick-list goal); --force would erase it. %s'
                                      % (SLUG, MOVE))
        self.assert_untouched(before)

    def test_force_refuses_an_index_md_it_cannot_read(self):
        write(self.path(SLUG, 'index.md'), '---\ntitle: %s\nstats:\n\tgain_m: 30\n---\n\n%s\n' % (TITLE, PLACEHOLDER))
        before = tree(self.trips)
        err = self.force()
        self.assertTrue(err.startswith('content/trips/%s/index.md cannot be read (' % SLUG), err)
        self.assertIn('so --force cannot tell what it would erase. %s' % MOVE, err)
        self.assert_untouched(before)

    def test_force_over_an_untouched_import_overwrites_it(self):
        self.import_gpx()
        out = self.ok(self.gpx_file(), '--title', TITLE, '--activity', 'hike', '--place', 'Invented Saddle', '--force',
                      '--no-render')
        self.assertIn('--force: content/trips/%s/ is an untouched import; overwriting index.md and track.gpx' % SLUG, out)
        meta, body = front(self.path(SLUG, 'index.md'))
        self.assertEqual(meta['place'], 'Invented Saddle')
        self.assertEqual(body.strip(), PLACEHOLDER)

    def test_force_over_an_untouched_import_with_empty_alt_lines_overwrites_its_photos(self):
        self.import_gpx('--photos', self.jpgs('a.jpg', 'b.jpg'))
        out = self.ok(self.gpx_file(), '--title', TITLE, '--activity', 'hike', '--force', '--no-render',
                      '--photos', self.jpgs('c.jpg', 'd.jpg', folder='more'))
        self.assertIn('--force: content/trips/%s/ is an untouched import; overwriting index.md, track.gpx, photos/01' % SLUG,
                      out)
        self.assertEqual(len(front(self.path(SLUG, 'index.md'))[0]['photos']), 2)
        self.assertEqual([os.path.basename(s) for s, _d in self.copies], ['a.jpg', 'b.jpg', 'c.jpg', 'd.jpg'])


# ---------------------------------------------------------------- --region


class RegionTests(AddTripFixture):

    def setUp(self):
        AddTripFixture.setUp(self)
        helpers.make_trip(self.trips, 'synthetic-a', region='Synthetic Highlands')
        helpers.make_trip(self.trips, 'synthetic-b', region='Synthetic Highlands')
        helpers.make_trip(self.trips, 'synthetic-c', region='SYNTHETIC HIGHLANDS')
        helpers.make_trip(self.trips, 'synthetic-d', region='Invented Coast')
        helpers.make_trip(self.trips, 'synthetic-e')

    def test_a_second_spelling_of_an_existing_region_is_a_usage_error_naming_the_spelling_in_use(self):
        before = tree(self.trips)
        err = self.usage_error(self.gpx_file(), '--title', TITLE, '--activity', 'hike', '--region', 'synthetic highlands',
                               '--no-render')
        self.assertIn('region "synthetic highlands" is written "Synthetic Highlands" on 2 trips; use that spelling', err)
        self.assertEqual(tree(self.trips), before)

    def test_one_trip_is_said_in_the_singular(self):
        err = self.usage_error(self.gpx_file(), '--title', TITLE, '--activity', 'hike', '--region', 'invented  coast',
                               '--no-render')
        self.assertIn('region "invented  coast" is written "Invented Coast" on 1 trip; use that spelling', err)

    def test_a_spelling_some_trip_uses_is_accepted_without_a_new_region_line(self):
        out = self.ok(self.gpx_file(), '--title', TITLE, '--activity', 'hike', '--region', 'SYNTHETIC HIGHLANDS', '--no-render')
        self.assertNotIn('new region', out)
        self.assertEqual(front(self.path(SLUG, 'index.md'))[0]['region'], 'SYNTHETIC HIGHLANDS')

    def test_a_new_region_is_said_with_the_existing_ones_most_used_first(self):
        out = self.ok(self.gpx_file(), '--title', TITLE, '--activity', 'hike', '--region', 'Quiet Basin', '--no-render')
        self.assertIn('new region: Quiet Basin (existing: Synthetic Highlands, Invented Coast, SYNTHETIC HIGHLANDS)',
                      out.splitlines())
        self.assertEqual(front(self.path(SLUG, 'index.md'))[0]['region'], 'Quiet Basin')

    def test_the_region_is_not_checked_with_day_of(self):
        helpers.make_trip(self.trips, 'synthetic-hut-traverse', kind='multi-day', region='Synthetic Highlands',
                          days=[{'title': 'Day one', 'date': '2026-07-03'}])
        out = self.ok(self.gpx_file(), '--day-of', 'synthetic-hut-traverse', '--region', 'synthetic highlands', '--no-render')
        self.assertIn('added day 2 to synthetic-hut-traverse', out)
        self.assertNotIn('new region', out)


class FirstRegionTests(AddTripFixture):

    def test_a_new_region_with_no_trips_says_none_exist(self):
        out = self.ok(self.gpx_file(), '--title', TITLE, '--activity', 'hike', '--region', 'Quiet Basin', '--no-render')
        self.assertIn('new region: Quiet Basin (existing: none)', out.splitlines())


# ---------------------------------------------------------------- --day-of


class DayOfTests(AddTripFixture):

    PARENT = 'synthetic-hut-traverse'

    def parent(self, days=1, labelled=True, **meta):
        """A multi-day trip folder with `days` day files (dated from 2026-07-02); meta overrides (None drops a key)."""
        m = dict(title='Synthetic Hut Traverse', kind='multi-day', date='2026-07-02', end_date='2026-07-03')
        m.update(meta)
        ds = []
        for i in range(days):
            d = {'title': 'Invented day %d' % (i + 1), 'date': '2026-07-%02d' % (i + 2)}
            if not labelled:
                d['day'] = ''
            ds.append(d)
        return helpers.make_trip(self.trips, self.PARENT, days=ds, **m)

    def add_day(self, *extra):
        return self.ok(self.gpx_file(), '--day-of', self.PARENT, '--title', 'Invented crossing', '--no-render', *extra)

    def test_the_new_day_is_numbered_after_the_existing_day_files(self):
        folder = self.parent(days=2)
        out = self.add_day()
        self.assertIn('added day 3 to %s (0 photos, 0 existing)' % self.PARENT, out.splitlines())
        self.assertTrue(os.path.isfile(os.path.join(folder, 'days', '03.md')))
        ET.parse(os.path.join(folder, 'days', '03.gpx'))
        meta, body = front(os.path.join(folder, 'days', '03.md'))
        self.assertEqual((meta['title'], meta['date'], meta['start_time']), ('Invented crossing', DAY, START_LA))
        self.assertIn('gain_m', meta['stats'])
        self.assertTrue(set(meta) <= set(checks.DAY_KEYS), meta)
        self.assertEqual(body, '')
        self.assertTrue(self.steps(out)[0].startswith('Edit content/trips/%s/days/03.md: ' % self.PARENT))

    def test_the_first_day_of_a_trip_without_day_files_is_01(self):
        folder = self.parent(days=0)
        out = self.add_day()
        self.assertIn('added day 1 to %s (0 photos, 0 existing)' % self.PARENT, out.splitlines())
        self.assertEqual(sorted(os.listdir(os.path.join(folder, 'days'))), ['01.gpx', '01.md'])

    def test_the_notes_name_a_missing_kind_line_and_the_day_labels(self):
        self.parent(days=1, kind=None)
        out = self.add_day()
        notes = [l for l in out.splitlines() if l.startswith('note: ')]
        self.assertEqual(notes, [
            'note: index.md has no `kind: multi-day` line; a trip with day files needs it (and `end_date:` for its last day)',
            'note: the other days carry a `day:` label; add one to days/02.md that no other day has'])

    def test_no_note_for_a_multi_day_trip_whose_days_carry_no_label(self):
        self.parent(days=2, labelled=False)
        out = self.add_day()
        self.assertEqual([l for l in out.splitlines() if l.startswith('note: ')], [])

    def test_the_existing_day_photo_count_counts_full_size_webp_and_jpg_files_only(self):
        folder = self.parent(days=1)
        for name in ('d01-01.webp', 'd01-01.sm.webp', 'd01-01.th.webp', 'd01-02.webp', 'd01-02.sm.webp', 'd01-02.th.webp',
                     'd01-03.jpg', 'd01-03.sm.jpg', 'd01-03.th.jpg', '01.webp', 'cover.webp'):
            write(os.path.join(folder, 'photos', name), b'x')
        out = self.add_day('--photos', self.jpgs('a.jpg'))
        self.assertIn('added day 2 to %s (1 photos, 3 existing)' % self.PARENT, out.splitlines())
        meta = front(os.path.join(folder, 'days', '02.md'))[0]
        self.assertEqual(meta['photos'], [{'file': 'photos/d02-01.webp', 'w': 1600, 'h': 1200, 'alt': ''}])
        self.assertTrue(os.path.isfile(os.path.join(folder, 'photos', 'd02-01.webp')))
        self.assertIn('Describe the photos: 1 alt: line is empty', ' '.join(self.steps(out)))

    def test_an_earlier_end_date_is_moved_to_the_new_days_date(self):
        folder = self.parent(days=1, end_date='2026-07-03')
        before = read(os.path.join(folder, 'index.md')).split('\n')
        out = self.add_day()
        self.assertIn('end_date 2026-07-03 -> %s (index.md)' % DAY, out.splitlines())
        after = read(os.path.join(folder, 'index.md')).split('\n')
        self.assertEqual(len(after), len(before))
        changed = [(b, a) for b, a in zip(before, after) if b != a]
        self.assertEqual(changed, [('end_date: 2026-07-03', 'end_date: %s' % DAY)])

    def test_an_end_date_on_or_after_the_new_day_is_left_alone(self):
        for end in (DAY, '2026-07-09'):
            with self.subTest(end_date=end):
                folder = self.parent(days=1, end_date=end)
                before = read(os.path.join(folder, 'index.md'), 'rb')
                out = self.add_day()
                self.assertEqual(read(os.path.join(folder, 'index.md'), 'rb'), before)
                self.assertNotIn('end_date', out)
                for f in ('02.md', '02.gpx'):
                    os.remove(os.path.join(folder, 'days', f))

    def test_no_end_date_line_is_written_when_index_md_has_none(self):
        folder = self.parent(days=1, end_date=None)
        before = read(os.path.join(folder, 'index.md'), 'rb')
        self.assertNotIn(b'end_date', before)
        out = self.add_day()
        self.assertEqual(read(os.path.join(folder, 'index.md'), 'rb'), before)
        self.assertNotIn('end_date ', out)

    def test_an_index_md_that_does_not_round_trip_is_not_rewritten(self):
        folder = os.path.join(self.trips, self.PARENT)
        text = ('---\ntitle: Synthetic Hut Traverse\nactivity: hike\nkind: multi-day\n# the last day is still to come\n'
                'date: 2026-07-02\nend_date: 2026-07-03\n---\n\n\n')
        write(os.path.join(folder, 'index.md'), text)
        out = self.add_day()
        self.assertEqual(read(os.path.join(folder, 'index.md')), text)
        notes = [l for l in out.splitlines() if l.startswith('note: ')]
        self.assertEqual(len(notes), 1, out)
        self.assertTrue(notes[0].startswith('note: end_date in index.md is 2026-07-03, before this day (%s), and was not '
                                            'changed: ' % DAY), notes[0])
        self.assertIn('edit it by hand', notes[0])
        self.assertNotIn('end_date 2026-07-03 ->', out)


# ---------------------------------------------------------------- --retime


class RetimeTests(AddTripFixture):

    def index(self, slug=SLUG):
        return self.path(slug, 'index.md')

    def changed_lines(self, before, after):
        """{key: (old line, new line)} of the front-matter lines that differ; the files must have as many lines."""
        b, a = before.split('\n'), after.split('\n')
        self.assertEqual(len(a), len(b))
        return {x.split(':')[0]: (x, y) for x, y in zip(b, a) if x != y}

    def test_a_new_zone_rewrites_timezone_and_start_time_and_keeps_the_rest_byte_for_byte(self):
        self.import_gpx()
        before = read(self.index())
        out = self.ok('--retime', SLUG, '--timezone', 'America/Chicago')
        lines = out.splitlines()
        self.assertIn('timezone   America/Los_Angeles -> America/Chicago', lines)
        self.assertIn('date       %s -> %s (unchanged)' % (DAY, DAY), lines)
        self.assertIn('start_time %s -> %s' % (START_LA, START_CHICAGO), lines)
        after = read(self.index())
        self.assertEqual(sorted(self.changed_lines(before, after)), ['start_time', 'timezone'])
        meta = frontmatter.split(after)[0]
        self.assertEqual((meta['timezone'], meta['date'], meta['start_time']), ('America/Chicago', DAY, START_CHICAGO))
        self.assertEqual(self.runs, [])

    def test_a_zone_past_midnight_moves_the_date_too(self):
        self.import_gpx()
        before = read(self.index())
        out = self.ok('--retime', SLUG, '--timezone', 'Asia/Tokyo')
        self.assertIn('date       %s -> 2026-07-05' % DAY, out.splitlines())
        self.assertIn('start_time %s -> 00:00' % START_LA, out.splitlines())
        self.assertEqual(sorted(self.changed_lines(before, read(self.index()))), ['date', 'start_time', 'timezone'])

    def test_without_timezone_the_zone_in_index_md_is_used(self):
        self.import_gpx('--timezone', 'America/Denver')
        before = read(self.index(), 'rb')
        out = self.ok('--retime', SLUG)
        self.assertIn('timezone   America/Denver -> America/Denver (unchanged)', out.splitlines())
        self.assertIn('start_time 09:00 -> 09:00 (unchanged)', out.splitlines())
        self.assertEqual(read(self.index(), 'rb'), before)

    def test_without_any_zone_the_zone_is_guessed(self):
        self.import_gpx('--timezone', 'America/Chicago')
        meta, body = front(self.index())
        del meta['timezone']
        write(self.index(), frontmatter.render(meta, body))
        out = self.ok('--retime', SLUG)
        self.assertIn('timezone   (none) -> America/Los_Angeles', out.splitlines())
        self.assertIn('start_time %s -> %s' % (START_CHICAGO, START_LA), out.splitlines())
        self.assertEqual(front(self.index())[0]['timezone'], 'America/Los_Angeles')

    def test_a_folder_with_day_files_is_refused(self):
        helpers.make_trip(self.trips, SLUG, title=TITLE, track=True, days=[{'title': 'Day one', 'date': DAY}])
        before = tree(self.trips)
        err = self.refused('--retime', SLUG, '--timezone', 'America/Chicago')
        self.assertIn('content/trips/%s has day files' % SLUG, err)
        self.assertEqual(tree(self.trips), before)

    def test_a_folder_without_track_gpx_is_refused(self):
        helpers.make_trip(self.trips, SLUG, title=TITLE, timezone='America/Los_Angeles')
        before = tree(self.trips)
        err = self.refused('--retime', SLUG)
        self.assertIn('content/trips/%s has no track.gpx' % SLUG, err)
        self.assertEqual(tree(self.trips), before)

    def test_a_gpx_without_timestamps_is_refused(self):
        self.import_gpx('--strip-times')
        before = tree(self.trips)
        err = self.refused('--retime', SLUG, '--timezone', 'America/Chicago')
        self.assertIn('content/trips/%s/track.gpx has no timestamps' % SLUG, err)
        self.assertEqual(tree(self.trips), before)

    def test_an_index_md_that_does_not_round_trip_is_refused(self):
        self.import_gpx()
        text = read(self.index()).replace('---\n', '---\n# a note the author left\n', 1)
        write(self.index(), text)
        err = self.refused('--retime', SLUG, '--timezone', 'America/Chicago')
        self.assertIn('edit it by hand', err)
        self.assertEqual(read(self.index()), text)

    def test_an_index_md_timezone_that_is_no_zone_name_is_refused(self):
        self.import_gpx()
        text = read(self.index()).replace('timezone: America/Los_Angeles', 'timezone: Mars/Olympus')
        self.assertIn('Mars/Olympus', text)
        write(self.index(), text)
        err = self.refused('--retime', SLUG)
        self.assertIn('content/trips/%s/index.md says timezone: Mars/Olympus, which is not a time zone name' % SLUG, err)
        self.assertEqual(read(self.index()), text)

    def test_a_trip_without_index_md_is_a_usage_error(self):
        err = self.usage_error('--retime', 'synthetic-nothing-here')
        self.assertIn('--retime synthetic-nothing-here: no content/trips/synthetic-nothing-here/index.md', err)

    def test_a_timezone_that_is_no_zone_name_is_a_usage_error(self):
        self.import_gpx()
        before = tree(self.trips)
        err = self.usage_error('--retime', SLUG, '--timezone', 'Mars/Olympus')
        self.assertIn('not a time zone name', err)
        self.assertEqual(tree(self.trips), before)


# ---------------------------------------------------------------- Strava


class StravaFixture(AddTripFixture):

    def export(self, rows, name='strava-export'):
        """A synthetic Strava export folder: activities.csv, activities/101.gpx (the GPX) and two media .jpg files."""
        folder = os.path.join(self.src, name)
        write(os.path.join(folder, 'activities', '101.gpx'), GPX)
        write(os.path.join(folder, 'media', 'aa.jpg'), b'')
        write(os.path.join(folder, 'media', 'bb.jpg'), b'')
        sx.write_export(folder, sx.HEADER, rows)
        return folder


class StravaImportTests(StravaFixture):

    def test_an_import_takes_title_stats_body_photos_and_activity_from_the_export(self):
        folder = self.export([
            sx.row(101, 'Jul 4, 2026, 3:00:00 PM', '  Synthetic Morning Loop  ', kind='Hike',
                   desc='Started in the invented cold.\nFinished in the synthetic sun.', filename='activities/101.gpx',
                   media='media/aa.jpg|media/bb.jpg'),
            sx.row(102, 'Jun 1, 2026, 7:30:00 AM', 'Another Synthetic Ride', kind='Ride'),
        ])
        out = self.ok('--strava-export', folder, '--strava-id', '101', '--no-render')
        slug = 'synthetic-morning-loop'
        meta, body = front(self.path(slug, 'index.md'))
        self.assertEqual((meta['title'], meta['activity'], meta['date'], meta['start_time']),
                         ('Synthetic Morning Loop', 'hike', DAY, START_LA))
        self.assertNotIn('subtype', meta)
        # the CSV's numbers: metres from the second Distance column, the second Elapsed Time, rounded elevations
        self.assertEqual(meta['stats'], {'distance_km': 12.35, 'moving': '2:00', 'elapsed': '2:35', 'gain_m': 812,
                                         'loss_m': 800, 'high_m': 2700, 'low_m': 1900})
        self.assertEqual(body.strip(), 'Started in the invented cold.\n\nFinished in the synthetic sun.')
        self.assertEqual([p['file'] for p in meta['photos']], ['photos/01.webp', 'photos/02.webp'])
        self.assertEqual([s for s, _d in self.copies], [os.path.join(folder, 'media', 'aa.jpg'),
                                                        os.path.join(folder, 'media', 'bb.jpg')])
        self.assertTrue(set(meta) <= set(checks.INDEX_KEYS), meta)
        steps = self.steps(out)
        self.assertTrue(steps[0].startswith('Edit content/trips/%s/index.md: ' % slug), steps[0])
        self.assertIn('Strava description', steps[0])
        self.assertIn('Describe the photos: 2 alt: lines are empty', ' '.join(steps))

    def test_a_strava_type_whose_sub_type_the_site_lacks_is_a_usage_error(self):
        for kind, sub in (('Canoeing', 'Canoeing'), ('Swim', 'Swimming'), ('Workout', 'Workout')):
            with self.subTest(type=kind):
                folder = self.export([sx.row(101, 'Jul 4, 2026, 3:00:00 PM', 'Synthetic Paddle', kind=kind,
                                             filename='activities/101.gpx')], name='export-' + kind)
                err = self.usage_error('--strava-export', folder, '--strava-id', '101', '--no-render')
                self.assertIn('the Strava type "%s" gives the sub-type "%s", which the site does not have' % (kind, sub), err)
                self.assertEqual(os.listdir(self.trips), [])

    def test_activity_given_by_hand_overrides_the_strava_type(self):
        folder = self.export([sx.row(101, 'Jul 4, 2026, 3:00:00 PM', 'Synthetic Paddle', kind='Canoeing',
                                     filename='activities/101.gpx')])
        self.ok('--strava-export', folder, '--strava-id', '101', '--activity', 'hike', '--no-render')
        meta = front(self.path('synthetic-paddle', 'index.md'))[0]
        self.assertEqual(meta['activity'], 'hike')
        self.assertNotIn('subtype', meta)

    def test_a_strava_type_that_maps_to_a_site_sub_type_is_accepted(self):
        folder = self.export([sx.row(101, 'Jul 4, 2026, 3:00:00 PM', 'Synthetic Paddle', kind='Stand Up Paddling',
                                     filename='activities/101.gpx')])
        self.ok('--strava-export', folder, '--strava-id', '101', '--no-render')
        meta = front(self.path('synthetic-paddle', 'index.md'))[0]
        self.assertEqual((meta['activity'], meta['subtype']), ('other', 'SUP'))


class StravaListTests(StravaFixture):

    def setUp(self):
        StravaFixture.setUp(self)
        self.folder = self.export([
            sx.row(101, 'Jul 4, 2026, 3:00:00 PM', 'Synthetic Morning Loop', kind='Hike', media='media/aa.jpg'),
            sx.row(102, 'Jun 1, 2026, 7:30:00 AM', 'Known Synthetic Ride', kind='Ride'),
            sx.row(103, 'Aug 2, 2026, 6:15:00 AM', 'Invented Summit Hike', kind='Hike'),
            sx.row(104, 'May 5, 2026, 9:00:00 AM', 'Known Synthetic Walk', kind='Walk'),
            sx.row(105, 'Mar 3, 2026, 10:00:00 AM', 'Invented Gravel Ride', kind='Ride'),
            sx.row(106, 'Jan 9, 2025, 9:05:07 AM', 'Old Synthetic Hike', kind='Hike'),
        ])
        # 102 is on a trip's index.md (an int), 104 on a day file (a string)
        helpers.make_trip(self.trips, 'synthetic-known-ride', strava_id=102)
        helpers.make_trip(self.trips, 'synthetic-known-days', kind='multi-day',
                          days=[{'title': 'Invented day', 'date': '2026-05-05', 'strava_id': '104'}])
        self.before = tree(self.trips)
        self.export_before = tree(self.folder)

    def tearDown(self):
        self.assertEqual(tree(self.trips), self.before, '--list wrote into the trips folder')
        self.assertEqual(tree(self.folder), self.export_before, '--list changed the export')
        self.assertEqual(self.copies, [])
        StravaFixture.tearDown(self)

    def listed(self, *extra):
        """(ids in the order printed, the lines) of a --list run; each activity line starts with its ISO date."""
        out = self.ok('--strava-export', self.folder, '--list', *extra)
        lines = out.splitlines()
        rows = [l for l in lines if re.match(r'^\d{4}-\d{2}-\d{2}  ', l)]
        return [l.split()[1] for l in rows], lines

    def test_the_activities_on_no_trip_or_day_are_listed_newest_first(self):
        ids, lines = self.listed()
        self.assertEqual(ids, ['103', '101', '105', '106'])
        self.assertIn('4 activities not on the site (of 6 in the export)', lines)
        first = [l for l in lines if l.startswith('2026-08-02  103')]
        self.assertEqual(len(first), 1)
        self.assertIn('Invented Summit Hike', first[0])
        self.assertIn('photos', [l for l in lines if ' 101 ' in l][0])

    def test_type_filters_by_strava_type_ignoring_case(self):
        ids, lines = self.listed('--type', 'Hike')
        self.assertEqual(ids, ['103', '101', '106'])
        self.assertIn('3 activities not on the site with these filters (of 6 in the export)', lines)
        ids, _lines = self.listed('--type', 'hike,RIDE')
        self.assertEqual(ids, ['103', '101', '105', '106'])

    def test_since_keeps_the_activities_on_or_after_the_day(self):
        ids, _lines = self.listed('--since', '2026-03-03')
        self.assertEqual(ids, ['103', '101', '105'])
        ids, lines = self.listed('--type', 'Ride', '--since', '2026-01-01')
        self.assertEqual(ids, ['105'])
        self.assertIn('1 activity not on the site with these filters (of 6 in the export)', lines)

    def test_list_usage_errors(self):
        self.assertIn('--list needs --strava-export', self.usage_error('--list'))
        self.assertIn('--since 03/03/2026: write the date as YYYY-MM-DD',
                      self.usage_error('--strava-export', self.folder, '--list', '--since', '03/03/2026'))
        self.assertIn('--strava-id is required with --strava-export', self.usage_error('--strava-export', self.folder))
        empty = os.path.join(self.src, 'not-an-export')
        os.makedirs(empty)
        self.assertIn('no activities.csv in that folder', self.usage_error('--strava-export', empty, '--list'))


# ---------------------------------------------------------------- after the review of the phase

class ReviewFixTests(StravaFixture):
    """What a review of the phase found: a folder of zones taken for a zone, damaged track files ending in a traceback,
    a failed render that the checklist took for a drawn one, and a Strava day refused for a sub-type a day never has."""

    def test_a_folder_of_zones_is_not_a_time_zone(self):
        # Python 3.9 with the Mac's zone files raises IsADirectoryError for 'America'; 3.12 raises a KeyError
        for zone in ('America', 'Europe', 'Nowhere/Invented'):
            with self.subTest(zone=zone):
                err = self.usage_error(self.gpx_file(), '--title', TITLE, '--activity', 'hike', '--no-render', '--timezone', zone)
                self.assertIn('--timezone %s: not a time zone name' % zone, err)
                self.assertNotIn('Traceback', err)
        self.assertEqual(os.listdir(self.trips), [])

    def test_a_damaged_track_is_one_line_not_a_traceback(self):
        zpath = os.path.join(self.src, 'damaged.zip')
        with zipfile.ZipFile(zpath, 'w') as zf:
            zf.writestr('recording.gpx', '<gpx><trk><trkseg><trkpt lat="1" lon="2"></trk>')      # not well-formed
        folder = os.path.join(self.src, 'a-folder.fit')
        os.makedirs(folder)
        gz = write(os.path.join(self.src, 'broken.fit.gz'), b'\x1f\x8bnot really gzip at all')
        for path in (zpath, folder, gz):
            with self.subTest(path=os.path.basename(path)):
                err = self.usage_error(path, '--title', TITLE, '--activity', 'hike', '--no-render')
                self.assertIn('cannot be read as a track', err)
                self.assertNotIn('Traceback', err)
        self.assertEqual(os.listdir(self.trips), [])

    def run_codes(self, render, status):
        """subprocess.run answering render.py SLUG with `render` and render.py --status with `status`."""
        self.allow_runs = True

        def run(args, *a, **kw):
            self.runs.append([str(x) for x in args])
            return subprocess.CompletedProcess(args, status if '--status' in args else render)
        p = mock.patch.object(add_trip.subprocess, 'run', run)
        p.start()
        self.addCleanup(p.stop)

    def test_a_failed_render_keeps_the_draw_step_in_the_checklist(self):
        for render, status, drawn in ((0, 0, True), (1, 1, False), (0, 1, False)):
            with self.subTest(render=render, status=status):
                self.run_codes(render, status)
                slug = 'synthetic-trip-%d-%d' % (render, status)
                out = self.ok(self.gpx_file(), '--title', TITLE, '--slug', slug, '--activity', 'hike')
                draw = [s for s in self.steps(out) if s.startswith('Draw the maps')]
                self.assertEqual(draw, [] if drawn else ['Draw the maps (internet needed): python3 tools/render.py %s' % slug])

    def test_a_strava_day_whose_type_has_no_site_sub_type_is_accepted(self):
        # a day file carries no activity and no sub-type: the Strava type does not matter for --day-of
        helpers.make_trip(self.trips, 'synthetic-tour', kind='multi-day', activity='other', subtype='Kayaking',
                          days=[{'title': 'Synthetic first day', 'date': '2026-07-03'}])
        folder = self.export([sx.row(101, 'Jul 4, 2026, 3:00:00 PM', 'Synthetic Paddle', kind='Canoeing',
                                     filename='activities/101.gpx')])
        out = self.ok('--strava-export', folder, '--strava-id', '101', '--day-of', 'synthetic-tour', '--no-render')
        self.assertIn('added day 2 to synthetic-tour', out)
        meta = front(self.path('synthetic-tour', 'days', '02.md'))[0]
        self.assertNotIn('activity', meta)
        self.assertNotIn('subtype', meta)


if __name__ == '__main__':
    unittest.main()
