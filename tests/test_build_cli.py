"""tools/build.py as a command: main(argv), the content checks that run before the output folder is touched, the
wrapper around the built-site checks, and the one write a --link build must never make.

No test here builds the real site. build.build, checks.run and sitecheck.check are replaced by stand-ins where a test
is about what main() does with their answers; the --link test works on a trip folder in a temp dir.

Phase 6 (the author's preview) adds, at the end: --serve links the build unless --copy is given, the usage errors of
--link with --copy and of --open / --watch without --serve, and what main() hands build.serve; serve() itself with a
stand-in server class whose serve_forever is Ctrl+C at once (nothing listens), --open's address and its fall-back to
the home page; --watch's view of a temp tree laid out like the checkout (watch_state, changed), the child build it runs
(rebuild, with subprocess.run replaced) and its loop (watch, stopped by a threading.Event); and that CI still builds
with a plain `python3 tools/build.py --check`.
"""
import contextlib
import importlib
import inspect
import io
import os
import re
import sys
import tempfile
import threading
import unittest
from unittest import mock

import helpers
import content
from sitegen import curation

build = importlib.import_module('build')
checks = importlib.import_module('checks')
sitecheck = importlib.import_module('sitegen.sitecheck')

tearDownModule = helpers.no_region_pages_left      # this module runs build.build(): no region page may stay registered after it


def finding(level, n):
    return {'level': level, 'file': 'content/trips/t%02d/index.md' % n, 'text': 'content/trips/t%02d/index.md: thing %d' % (n, n)}


class Run(object):
    """One main() call with stand-ins: what it returned or exited with, what it printed, and what it called."""

    def __init__(self, argv, findings=(), problems=(), raises=None, out_dir=None):
        self.built = []
        self.checked = []
        self.stdout, self.stderr = io.StringIO(), io.StringIO()
        self.code = None
        self.exit = None

        def fake_build(verbose=True, only=None):
            self.built.append(only)
            self.out_seen = build.OUT
            self.link_seen = build.LINK
            if raises:
                raise raises
            return []

        def fake_check(out_dir, trips_dir=None, *a, **kw):
            self.checked.append((out_dir, trips_dir))
            return list(problems)

        with mock.patch.object(build, 'build', fake_build), mock.patch.object(checks, 'run', lambda *a, **kw: list(findings)), \
                mock.patch.object(sitecheck, 'check', fake_check), mock.patch.object(build, 'OUT', out_dir or build.OUT), \
                mock.patch.object(build, 'LINK', False), \
                contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr):
            try:
                self.code = build.main(argv)
            except SystemExit as ex:
                self.exit = ex.code
        self.out, self.err = self.stdout.getvalue(), self.stderr.getvalue()


class MainTests(unittest.TestCase):
    def test_a_clean_build_returns_0_and_builds_every_module(self):
        r = Run([])
        self.assertEqual((r.code, r.exit), (0, None))
        self.assertEqual(r.built, [None])
        self.assertEqual(r.checked, [])
        self.assertEqual((r.out, r.err), ('', ''))

    def test_check_runs_the_site_checks_on_the_output_folder_and_the_content_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Run(['--check', '--out', tmp], out_dir=tmp)
            self.assertEqual(r.code, 0)
            self.assertEqual(r.checked, [(os.path.abspath(tmp), content.TRIPS_DIR)])
            self.assertEqual(r.out, 'link check: OK\n')

    def test_problems_from_the_site_checks_fail_the_command(self):
        r = Run(['--check'], problems=['BROKEN a/index.html -> b.webp', 'META 404.html: the 404 page is not noindex'])
        self.assertEqual(r.code, 1)
        self.assertEqual(r.out, 'BROKEN a/index.html -> b.webp\nMETA 404.html: the 404 page is not noindex\nlink check: 2 problems\n')

    def test_only_the_first_problems_print_and_the_summary_counts_all(self):
        problems = ['BROKEN p%03d/index.html -> x.webp' % i for i in range(build.CHECK_LINES + 3)]
        r = Run(['--check'], problems=problems)
        lines = r.out.splitlines()
        self.assertEqual(lines[:build.CHECK_LINES], problems[:build.CHECK_LINES])
        self.assertEqual(lines[build.CHECK_LINES:], ['... 3 more', 'link check: %d problems' % len(problems)])
        self.assertEqual(r.code, 1)

    def test_exactly_the_cap_prints_no_more_line(self):
        problems = ['BROKEN p%03d/index.html -> x.webp' % i for i in range(build.CHECK_LINES)]
        r = Run(['--check'], problems=problems)
        self.assertEqual(r.out.splitlines(), problems + ['link check: %d problems' % len(problems)])

    def test_a_content_error_raised_by_the_build_is_one_line_and_exit_1(self):
        for ex in (content.ContentError('content/trips/x/index.md: cover_photo is not one of its photos'),
                   curation.CurationError('content/home.json: featured_slugs has no trip "x"')):
            with self.subTest(ex=type(ex).__name__):
                r = Run(['--check'], raises=ex)
                self.assertEqual(r.code, 1)
                self.assertEqual(r.err, 'ERROR %s\n' % ex)
                self.assertEqual(r.checked, [])

    def test_another_exception_is_not_swallowed(self):
        with self.assertRaises(ZeroDivisionError):
            Run([], raises=ZeroDivisionError('boom'))

    def test_out_and_link_reach_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Run(['--out', os.path.join(tmp, 'site'), '--link'])
            self.assertEqual(r.out_seen, os.path.abspath(os.path.join(tmp, 'site')))
            self.assertIs(r.link_seen, True)

    def test_without_arguments_main_reads_the_command_line(self):
        with mock.patch.object(sys, 'argv', ['build.py', '--only', 'home']):
            r = Run(None)
        self.assertEqual(r.built, [{'home'}])


class OnlyTests(unittest.TestCase):
    def test_module_names_are_split_and_trimmed(self):
        self.assertEqual(Run(['--only', 'report, home ,']).built, [{'report', 'home'}])

    def test_every_page_module_is_accepted(self):
        self.assertEqual(Run(['--only', ','.join(build.PAGE_MODULES)]).built, [set(build.PAGE_MODULES)])

    def test_region_is_a_page_module_and_builds_alone(self):
        # contract-phase5.md section 3: 'region' is in build.PAGE_MODULES, after 'archive', so `--only region` is a build
        self.assertEqual(build.PAGE_MODULES[build.PAGE_MODULES.index('archive') + 1], 'region')
        r = Run(['--only', 'region'])
        self.assertEqual((r.code, r.exit, r.built), (0, None, [{'region'}]))
        self.assertEqual(Run(['--only', 'archive,region']).built, [{'archive', 'region'}])
        # the name is the module's, not the folder's
        self.assertEqual(Run(['--only', 'regions']).exit, 2)

    def test_an_unknown_module_is_a_usage_error_that_names_it_and_builds_nothing(self):
        r = Run(['--only', 'report,reprot,hom'])
        self.assertEqual((r.code, r.exit), (None, 2))
        self.assertEqual(r.built, [])
        self.assertIn('--only takes page modules (%s), got hom, reprot' % ', '.join(build.PAGE_MODULES), r.err)

    def test_an_empty_list_is_a_usage_error(self):
        for value in ('', ' , '):
            with self.subTest(value=value):
                r = Run(['--only', value])
                self.assertEqual(r.exit, 2)
                self.assertEqual(r.built, [])
                self.assertIn('got none', r.err)


class ContentChecksTests(unittest.TestCase):
    def test_errors_go_to_stderr_one_line_each_and_nothing_is_built(self):
        with tempfile.TemporaryDirectory() as tmp:
            keep = os.path.join(tmp, 'kept.txt')     # an earlier build's file: still there if the checks stop this run
            open(keep, 'w').close()
            open(os.path.join(tmp, build.BUILD_MARK), 'w').close()
            found = [finding('error', 1), finding('warning', 2), finding('error', 3), finding('note', 4)]
            r = Run(['--check', '--out', tmp], findings=found, out_dir=tmp)
            self.assertEqual(r.code, 1)
            self.assertEqual(r.err, 'ERROR content/trips/t01/index.md: thing 1\nERROR content/trips/t03/index.md: thing 3\n')
            self.assertEqual(r.out, '')
            self.assertEqual((r.built, r.checked), ([], []))
            self.assertTrue(os.path.exists(keep), 'the output folder was touched before the content was checked')

    def test_every_error_prints_however_many_there_are(self):
        found = [finding('error', n) for n in range(build.WARNING_LINES + 15)]
        r = Run([], findings=found)
        self.assertEqual(r.err.count('\n'), len(found))

    def test_warnings_print_and_the_build_goes_on(self):
        found = [finding('warning', 1), finding('note', 2), finding('warning', 3)]
        r = Run([], findings=found)
        self.assertEqual(r.code, 0)
        self.assertEqual(r.out, 'WARNING content/trips/t01/index.md: thing 1\nWARNING content/trips/t03/index.md: thing 3\n')
        self.assertEqual(r.err, '')
        self.assertEqual(r.built, [None])

    def test_past_the_cap_the_rest_are_counted_with_a_pointer_to_the_validator(self):
        found = [finding('warning', n) for n in range(build.WARNING_LINES + 4)]
        lines = Run([], findings=found).out.splitlines()
        self.assertEqual(len(lines), build.WARNING_LINES + 1)
        self.assertEqual(lines[-1], '... 4 more; python3 tools/validate.py lists them')

    def test_exactly_the_cap_prints_no_pointer(self):
        found = [finding('warning', n) for n in range(build.WARNING_LINES)]
        lines = Run([], findings=found).out.splitlines()
        self.assertEqual(len(lines), build.WARNING_LINES)
        self.assertTrue(all(ln.startswith('WARNING ') for ln in lines))

    def test_notes_never_print(self):
        r = Run([], findings=[finding('note', 1)])
        self.assertEqual((r.code, r.out, r.err), (0, '', ''))

    def test_the_lines_are_the_validators_own(self):
        f = finding('warning', 7)
        self.assertEqual(Run([], findings=[f]).out, checks.line(f) + '\n')

    def test_the_checks_run_before_the_build_is_called(self):
        order = []
        with mock.patch.object(checks, 'run', lambda *a, **kw: order.append('checks') or []), \
                mock.patch.object(build, 'build', lambda verbose=True, only=None: order.append('build') or []), \
                mock.patch.object(build, 'OUT', build.OUT), mock.patch.object(build, 'LINK', False):
            self.assertEqual(build.main([]), 0)
        self.assertEqual(order, ['checks', 'build'])


DAY = ('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1">\n'
       '<trk><name>%s</name><trkseg><trkpt lat="10.0%d" lon="10.0"><ele>1</ele></trkpt>'
       '<trkpt lat="10.0%d" lon="10.01"><ele>2</ele></trkpt></trkseg></trk>\n</gpx>\n')
OWN = DAY % ('The whole tour', 7, 8)


class LinkedCombinedFileTests(unittest.TestCase):
    """A multi-day trip that has its own track.gpx as well as day tracks. A --link build links <slug>.gpx to that file
    and then writes the combined file under the same name: it must replace the link, never write through it."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        self.trips = os.path.join(self.tmp, 'content', 'trips')
        self.out = os.path.join(self.tmp, 'site')
        folder = helpers.make_trip(self.trips, 'tour', title='Tour', kind='multi-day', date='2025-04-01',
                                   days=[{'date': '2025-04-01'}, {'date': '2025-04-02'}])
        self.own = os.path.join(folder, 'track.gpx')
        for path, text in ((self.own, OWN), (os.path.join(folder, 'days', '01.gpx'), DAY % ('Day 1', 1, 2)),
                           (os.path.join(folder, 'days', '02.gpx'), DAY % ('Day 2', 3, 4))):
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(text)
        with mock.patch.object(content, 'RENDERED', os.path.join(self.tmp, 'rendered')):
            self.trip = content.load_trip(folder)

    def assets(self, link):
        with mock.patch.object(build, 'OUT', self.out), mock.patch.object(build, 'LINK', link):
            build.copy_trip_assets(self.trip)
        return os.path.join(self.out, 'trips', 'tour', 'tour.gpx')

    def test_the_fixture_has_both_kinds_of_track(self):
        self.assertEqual(self.trip['track'], self.own)
        self.assertEqual([bool(d['track']) for d in self.trip['days']], [True, True])

    def test_a_link_build_leaves_the_content_file_alone(self):
        combined = self.assets(link=True)
        with open(self.own, encoding='utf-8') as fh:
            self.assertEqual(fh.read(), OWN)
        self.assertFalse(os.path.islink(combined))
        with open(combined, encoding='utf-8') as fh:
            text = fh.read()
        self.assertEqual(text.count('<trk>'), 2)
        self.assertLess(text.index('<name>Day 1</name>'), text.index('<name>Day 2</name>'))
        self.assertNotIn('The whole tour', text)

    def test_a_link_build_twice_over_is_the_same(self):
        self.assets(link=True)
        combined = self.assets(link=True)
        with open(self.own, encoding='utf-8') as fh:
            self.assertEqual(fh.read(), OWN)
        self.assertFalse(os.path.islink(combined))

    def test_a_copy_build_writes_the_same_combined_file(self):
        with open(self.assets(link=True), encoding='utf-8') as fh:
            linked = fh.read()
        other = os.path.join(self.tmp, 'site2')
        with mock.patch.object(build, 'OUT', other), mock.patch.object(build, 'LINK', False):
            build.copy_trip_assets(self.trip)
        with open(os.path.join(other, 'trips', 'tour', 'tour.gpx'), encoding='utf-8') as fh:
            self.assertEqual(fh.read(), linked)

    def test_the_day_files_are_still_links_to_the_content(self):
        self.assets(link=True)
        day = os.path.join(self.out, 'trips', 'tour', 'gpx', 'tour-day-01.gpx')
        self.assertTrue(os.path.islink(day))
        self.assertEqual(os.path.realpath(day), os.path.realpath(os.path.join(self.trips, 'tour', 'days', '01.gpx')))


class LineEndingTests(unittest.TestCase):
    """A day file with Windows line endings (some GPS tools write them). Its track goes into the combined file byte for
    byte, so the site check, which compares the bytes, passes a build of it."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        self.trips = os.path.join(self.tmp, 'content', 'trips')
        self.out = os.path.join(self.tmp, 'site')
        folder = helpers.make_trip(self.trips, 'tour', title='Tour', kind='multi-day', date='2025-04-01',
                                   days=[{'date': '2025-04-01'}, {'date': '2025-04-02'}])
        self.crlf = (DAY % ('Day 1', 1, 2)).replace('\n', '\r\n').replace('</trkpt><trkpt', '</trkpt>\r\n<trkpt')
        self.lf = DAY % ('Day 2', 3, 4)
        for name, text in (('01.gpx', self.crlf), ('02.gpx', self.lf)):
            with open(os.path.join(folder, 'days', name), 'w', encoding='utf-8', newline='') as fh:
                fh.write(text)
        with mock.patch.object(content, 'RENDERED', os.path.join(self.tmp, 'rendered')):
            self.trip = content.load_trip(folder)

    def built(self, link=False):
        with mock.patch.object(build, 'OUT', self.out), mock.patch.object(build, 'LINK', link):
            build.copy_trip_assets(self.trip)
        with open(os.path.join(self.out, 'trips', 'tour', 'tour.gpx'), 'rb') as fh:
            return fh.read()

    def test_the_fixture_has_both_kinds_of_line_ending(self):
        self.assertIn('\r\n<trkpt', self.crlf)
        self.assertNotIn('\r', self.lf)

    def test_each_days_track_is_in_the_combined_file_byte_for_byte(self):
        data = self.built()
        for text in (self.crlf, self.lf):
            block = text[text.index('<trk>'):text.index('</trk>') + len('</trk>')].encode('utf-8')
            self.assertIn(block, data)
        self.assertEqual(data.count(b'\r\n'), self.crlf[self.crlf.index('<trk>'):self.crlf.index('</trk>')].count('\r\n'))

    def test_the_site_check_passes_the_build(self):
        for link in (False, True):
            with self.subTest(link=link):
                self.built(link)
                self.assertEqual(sitecheck.gpx(sitecheck.read(self.out), self.trips), [])


class GpxRootTagTests(unittest.TestCase):
    """build.gpx_root_tag: the <gpx ...> start tag of a day file, where the combined download's root gets its
    xmlns:prefix declarations from. Found by position, so an odd file costs no more than its length."""

    def test_the_tag_is_read_whole(self):
        tag = build.gpx_root_tag
        self.assertEqual(tag('<?xml version="1.0"?>\n<gpx version="1.1" xmlns:ns3="urn:x">\n<trk></trk></gpx>'), '<gpx version="1.1" xmlns:ns3="urn:x">')
        self.assertEqual(tag("<gpx xmlns:a='urn:a'\n     xmlns:b=\"urn:b\">\n<trk>"), "<gpx xmlns:a='urn:a'\n     xmlns:b=\"urn:b\">")
        self.assertEqual(tag('<gpx><trk>'), '<gpx>')

    def test_a_greater_than_sign_inside_a_quoted_value_does_not_end_it(self):
        text = '<gpx version="1.1" creator="Device > v2" xmlns:ns3="urn:x"><trk>'
        self.assertEqual(build.gpx_root_tag(text), text[:-len('<trk>')])
        text = "<gpx creator='a > b' xmlns:q='urn:q'><trk>"
        self.assertEqual(build.gpx_root_tag(text), text[:-len('<trk>')])

    def test_a_tag_named_in_a_comment_is_not_the_root(self):
        self.assertEqual(build.gpx_root_tag('<!-- exported by <gpx tool> -->\n<gpx xmlns:a="urn:a">\n<trk>'), '<gpx xmlns:a="urn:a">')
        self.assertEqual(build.gpx_root_tag('<!-- a --><!-- <gpx xmlns:no="urn:no"> -->\n<gpx xmlns:yes="urn:yes"><trk>'), '<gpx xmlns:yes="urn:yes">')

    def test_no_tag_before_the_first_track_is_no_tag(self):
        for text in ('', '<trk></trk>', 'no root <trk>', '<gpx xmlns:a="u"', '<gpx a="unclosed <trk>', '<metadata/><trk><gpx xmlns:late="u">'):
            self.assertEqual(build.gpx_root_tag(text), '', text)

    def test_a_long_odd_file_is_read_in_one_pass(self):
        # each of these took seconds to minutes with one pattern searched from every '<gpx' or '<!--'
        import time
        for text in ('<gpx ' * 100000 + '<trk>', '<!-- ' * 100000 + '<gpx><trk>', '<gpx a="' + 'x' * 500000 + '<trk>'):
            started = time.time()
            build.gpx_root_tag(text)
            self.assertLess(time.time() - started, 2.0, text[:12])

    def test_the_combined_file_declares_a_prefix_from_such_a_tag(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = os.path.realpath(tmp.name)
        trips, out = os.path.join(root, 'content', 'trips'), os.path.join(root, 'site')
        folder = helpers.make_trip(trips, 'tour', title='Tour', kind='multi-day', date='2025-04-01', days=[{'date': '2025-04-01'}])
        day = ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- made by <gpx maker> -->\n'
               '<gpx version="1.1" creator="Maker > 2" xmlns="http://www.topografix.com/GPX/1/1" xmlns:ns3="urn:ext">\n'
               '<trk><name>Day 1</name><trkseg><trkpt lat="10.01" lon="10.0"><extensions><ns3:hr>120</ns3:hr></extensions></trkpt>'
               '<trkpt lat="10.02" lon="10.0"/></trkseg></trk>\n</gpx>\n')
        with open(os.path.join(folder, 'days', '01.gpx'), 'w', encoding='utf-8') as fh:
            fh.write(day)
        with mock.patch.object(content, 'RENDERED', os.path.join(root, 'rendered')):
            trip = content.load_trip(folder)
        with mock.patch.object(build, 'OUT', out), mock.patch.object(build, 'LINK', False):
            build.copy_trip_assets(trip)
        with open(os.path.join(out, 'trips', 'tour', 'tour.gpx'), encoding='utf-8') as fh:
            text = fh.read()
        self.assertEqual(text.count('xmlns:ns3="urn:ext"'), 1)
        import xml.etree.ElementTree as ET
        ET.fromstring(text.encode('utf-8'))
        self.assertEqual(sitecheck.gpx(sitecheck.read(out), trips), [])


class OutputFolderGuardTests(unittest.TestCase):
    """A build empties its output folder before it writes. --out is refused, before anything is read or removed, when
    that would delete something that is not an earlier build."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)

    def refused(self, out):
        r = Run(['--out', out])
        self.assertEqual((r.code, r.exit), (None, 2), out)
        self.assertEqual(r.built, [])
        self.assertIn('a build empties its output folder first, and ', r.err)
        return r.err

    def test_a_new_folder_an_empty_folder_and_an_earlier_build_are_fine(self):
        self.assertIsNone(build.unsafe_out(os.path.join(self.tmp, 'new', 'deeper')))
        self.assertIsNone(build.unsafe_out(self.tmp))
        with open(os.path.join(self.tmp, 'index.html'), 'w') as fh:
            fh.write('x')
        open(os.path.join(self.tmp, build.BUILD_MARK), 'w').close()
        self.assertIsNone(build.unsafe_out(self.tmp))
        self.assertEqual(Run(['--out', self.tmp]).code, 0)

    def test_a_folder_with_other_things_in_it_is_refused_and_keeps_them(self):
        mine = os.path.join(self.tmp, 'notes.txt')
        with open(mine, 'w') as fh:
            fh.write('mine')
        self.assertIn('it is not empty and is not an earlier build (it has no .nojekyll file)', self.refused(self.tmp))
        self.assertTrue(os.path.exists(mine))

    def test_a_file_is_refused(self):
        path = os.path.join(self.tmp, 'a-file')
        open(path, 'w').close()
        self.assertIn('it is a file', self.refused(path))

    def test_the_checkout_and_the_folders_above_it_are_refused(self):
        for out in (build.ROOT, os.path.dirname(build.ROOT), os.path.join(build.ROOT, '.'), os.sep):
            with self.subTest(out=out):
                self.assertEqual(build.unsafe_out(out), 'it is, or holds, this checkout')
        self.assertIn('it is, or holds, this checkout', self.refused(build.ROOT))

    def test_the_source_folders_are_refused_at_any_depth(self):
        for name in ('content', 'rendered', 'assets', 'tools', 'tests', 'docs', '.git', '.github'):
            for out in (os.path.join(build.ROOT, name), os.path.join(build.ROOT, name, 'new-folder', 'deeper')):
                with self.subTest(out=out):
                    self.assertEqual(build.unsafe_out(out), 'it is inside %s/ of this checkout' % name)
        self.assertIn('it is inside content/ of this checkout', self.refused(os.path.join(build.ROOT, 'content', 'trips')))

    def test_a_link_to_the_checkout_is_seen_through(self):
        link = os.path.join(self.tmp, 'link')
        os.symlink(build.ROOT, link)
        self.assertEqual(build.unsafe_out(link), 'it is, or holds, this checkout')
        self.assertEqual(build.unsafe_out(os.path.join(link, 'content')), 'it is inside content/ of this checkout')

    def test_a_source_folder_that_is_a_link_out_of_the_checkout_is_still_a_source_folder(self):
        # a checkout whose content/ is a link to another disk: a build into it, at any depth, is refused all the same
        root, elsewhere = os.path.join(self.tmp, 'checkout'), os.path.join(self.tmp, 'elsewhere')
        os.makedirs(root)
        os.makedirs(os.path.join(elsewhere, 'trips'))
        os.symlink(elsewhere, os.path.join(root, 'content'))
        with mock.patch.object(build, 'ROOT', root):
            for out in (os.path.join(root, 'content'), os.path.join(root, 'content', 'new-folder', 'deeper'),
                        os.path.join(elsewhere, 'trips'), os.path.join(elsewhere, 'new-folder')):
                self.assertEqual(build.unsafe_out(out), 'it is inside content/ of this checkout', out)
            # a folder beside the link's target is not in it
            self.assertIsNone(build.unsafe_out(os.path.join(self.tmp, 'elsewhere-2', 'site')))
            self.assertIsNone(build.unsafe_out(os.path.join(root, '_site')))

    def test_other_folders_of_the_checkout_are_allowed(self):
        # _site, .cache/<name> and a scratch folder in the checkout are where builds go
        for out in (os.path.join(build.ROOT, '_site-not-there'), os.path.join(build.ROOT, '.cache', 'not-there', 'site')):
            self.assertIsNone(build.unsafe_out(out), out)

    def test_the_mark_is_written_first_so_a_build_that_stops_half_way_can_be_built_over(self):
        seen = []

        def boom(site):
            seen.append(os.path.exists(os.path.join(build.OUT, build.BUILD_MARK)))
            raise content.ContentError('content/trips/x/index.md: stop here')

        out = os.path.join(self.tmp, 'site')
        module = type('M', (), {'build': staticmethod(boom)})
        # (build() hands core.register_site the site and the site meta since Phase 5; both are stand-ins here, so the
        # checkout's own rendered/site/meta.json is not read)
        with mock.patch.object(build, 'OUT', out), mock.patch.object(build, 'LINK', False), \
                mock.patch.object(build, 'PAGE_MODULES', ['home']), mock.patch.object(build.importlib, 'import_module', lambda name: module), \
                mock.patch.object(build.content, 'load_all', lambda *a, **k: []), mock.patch.object(build, 'site_of', lambda trips: {'trips': [], 'published': []}), \
                mock.patch.object(build.curation, 'featured_for', lambda site: []), \
                mock.patch.object(build.core, 'read_site_meta', lambda: {'maps': {}, 'regions': []}), \
                mock.patch.object(build.core, 'register_site', lambda site, meta=None: None):
            with self.assertRaises(content.ContentError):
                build.build(verbose=False)
        self.assertEqual(seen, [True])
        self.assertIsNone(build.unsafe_out(out))

    def test_build_registers_the_site_with_the_site_meta_as_it_is_on_disk(self):
        # contract-phase5.md section 1 (REVISED in round 2): build.build() passes core.read_site_meta() to
        # core.register_site, which is what gives the regions their pages; a site registered without it has none
        calls, order = [], []
        meta = {'maps': {'region-synthetic-desktop': {}}, 'regions': ['Synthetic'], 'marker': object()}
        site = {'trips': [], 'published': []}

        def read():
            order.append('read')
            return meta

        def register(*args, **kwargs):
            order.append('register')
            calls.append((args, kwargs))

        def pages(site_):
            # the first page module: the build stops here, before it writes a page or copies a file of rendered/
            order.append('pages')
            raise content.ContentError('content/trips/x/index.md: stop here')

        out = os.path.join(self.tmp, 'site')
        module = type('M', (), {'build': staticmethod(pages)})
        with mock.patch.object(build, 'OUT', out), mock.patch.object(build, 'LINK', False), \
                mock.patch.object(build, 'PAGE_MODULES', ['home']), mock.patch.object(build.importlib, 'import_module', lambda name: module), \
                mock.patch.object(build.content, 'load_all', lambda *a, **k: []), mock.patch.object(build, 'site_of', lambda trips: site), \
                mock.patch.object(build.curation, 'featured_for', lambda site_: []), \
                mock.patch.object(build.core, 'read_site_meta', read), mock.patch.object(build.core, 'register_site', register), \
                mock.patch.object(build.core, 'site_meta', lambda: self.fail('build() asked for the cached copy of the site meta')):
            with self.assertRaises(content.ContentError):
                build.build(verbose=False)
        self.assertEqual(len(calls), 1)
        (args, kwargs), = calls
        handed = list(args) + [kwargs[k] for k in sorted(kwargs)]
        self.assertEqual(len(handed), 2)
        self.assertIs(handed[0], site)
        self.assertIs(handed[1], meta)                                   # the object read_site_meta returned, not a default
        self.assertEqual(sorted(kwargs), [k for k in ('meta',) if k in kwargs])
        self.assertEqual(order, ['read', 'register', 'pages'])           # read once, and registered before any page is built


# ---------------------------------------------------------------- Phase 6: --serve, --open, --watch

class Recorder(object):
    """A stand-in for one of build.py's functions: each call is kept as {parameter: value}, bound to the real function's
    signature with its defaults filled in, so a test does not depend on whether a value is passed by position or by
    name. answer: what the call returns; then: run after each call with the bound arguments (to stop a loop)."""

    def __init__(self, real, answer=None, then=None):
        self.sig = inspect.signature(real)
        self.calls = []
        self.answer = answer
        self.then = then

    def __call__(self, *args, **kwargs):
        bound = self.sig.bind(*args, **kwargs)
        bound.apply_defaults()
        self.calls.append(dict(bound.arguments))
        if self.then:
            self.then(self.calls[-1])
        return self.answer


def run_serving(argv, answer=0, **kw):
    """Run(argv) with build.serve replaced by a Recorder (nothing listens): (the Run, the serve calls)."""
    serve = Recorder(build.serve, answer)
    with mock.patch.object(build, 'serve', serve):
        r = Run(argv, **kw)
    return r, serve.calls


class ServeOptionTests(unittest.TestCase):
    """main() with --serve and the options that go with it. A preview links photos, maps and GPX into the output folder
    (LINK True) unless --copy is given; CI's plain build copies as before. --link with --copy, and --open or --watch
    without --serve, are usage errors that build nothing. build.serve gets the port, the --open value ('' for a bare
    --open, the slug, None without it) and the watch argument (None without --watch, else the LINK value), and main()
    returns what serve returns."""

    def test_serve_links_the_build(self):
        r, calls = run_serving(['--serve'])
        self.assertEqual((r.code, r.exit, r.built), (0, None, [None]))
        self.assertIs(r.link_seen, True)
        self.assertEqual(len(calls), 1)

    def test_serve_with_copy_copies(self):
        r, calls = run_serving(['--serve', '--copy'])
        self.assertEqual((r.code, r.exit, r.built), (0, None, [None]))
        self.assertIs(r.link_seen, False)
        self.assertEqual(len(calls), 1)

    def test_a_build_that_is_not_served_copies_as_before_and_serves_nothing(self):
        for argv in ([], ['--check']):
            with self.subTest(argv=argv):
                r, calls = run_serving(argv)
                self.assertEqual((r.code, r.exit), (0, None))
                self.assertIs(r.link_seen, False)
                self.assertEqual(calls, [])
        r, calls = run_serving(['--link'])
        self.assertIs(r.link_seen, True)
        self.assertEqual(calls, [])

    def test_link_and_copy_together_are_a_usage_error(self):
        for argv in (['--link', '--copy'], ['--serve', '--link', '--copy'], ['--copy', '--link', '--serve', '--watch']):
            with self.subTest(argv=argv):
                r, calls = run_serving(argv)
                self.assertEqual((r.code, r.exit), (None, 2))
                self.assertEqual((r.built, calls), ([], []))

    def test_open_and_watch_without_serve_are_a_usage_error(self):
        for argv in (['--open'], ['--open', 'syn-preview'], ['--watch'], ['--open', '--watch'], ['--check', '--watch'],
                     ['--link', '--open', 'syn-preview']):
            with self.subTest(argv=argv):
                r, calls = run_serving(argv)
                self.assertEqual((r.code, r.exit), (None, 2))
                self.assertEqual((r.built, calls), ([], []))

    def test_serve_gets_the_port_the_open_value_and_the_watch_argument(self):
        # (argv, port, open_slug, watch_link, only)
        cases = [(['--serve'], 8000, None, None, None),
                 (['--serve', '--open'], 8000, '', None, None),
                 (['--serve', '--open', 'syn-preview'], 8000, 'syn-preview', None, None),
                 (['--serve', '--watch'], 8000, None, True, None),
                 (['--serve', '--copy', '--watch'], 8000, None, False, None),
                 (['--serve', '--open', '--watch', '--port', '8123'], 8123, '', True, None),
                 (['--serve', '--link', '--watch', '--open', 'syn-preview'], 8000, 'syn-preview', True, None),
                 (['--serve', '--only', 'report,home', '--watch'], 8000, None, True, {'report', 'home'})]
        for argv, port, open_slug, watch_link, only in cases:
            with self.subTest(argv=argv):
                r, calls = run_serving(argv)
                self.assertEqual((r.code, r.exit, r.built), (0, None, [only]))
                self.assertEqual(len(calls), 1)
                c = calls[0]
                self.assertEqual((c['port'], c['open_slug'], c['watch_link'], c['only']), (port, open_slug, watch_link, only))
                self.assertIsNone(c['server_class'])          # the real server: the stand-in is the tests' alone
                if watch_link is not None:
                    self.assertIs(c['watch_link'], r.link_seen)

    def test_main_returns_what_serve_returns(self):
        for answer in (0, 1, 7):
            with self.subTest(answer=answer):
                self.assertEqual(run_serving(['--serve'], answer=answer)[0].code, answer)

    def test_a_content_error_in_the_build_serves_nothing(self):
        r, calls = run_serving(['--serve', '--watch'], raises=content.ContentError('content/trips/x/index.md: stop here'))
        self.assertEqual((r.code, calls), (1, []))
        self.assertEqual(r.err, 'ERROR content/trips/x/index.md: stop here\n')


def server_class(made, events=None):
    """A server class for build.serve: it remembers how it was made (address, handler), and its serve_forever is Ctrl+C
    at once, so serve() returns without anything listening. events: a list each step is appended to, in order."""
    events = [] if events is None else events

    class Server(object):
        def __init__(self, address, handler):
            self.address, self.handler, self.served, self.closed = address, handler, 0, 0
            made.append(self)
            events.append('made')

        def serve_forever(self):
            self.served += 1
            events.append('serve_forever')
            raise KeyboardInterrupt

        def server_close(self):
            self.closed += 1
            events.append('server_close')

    return Server


class ServeTests(unittest.TestCase):
    """build.serve with a stand-in server class and build.open_in_browser recorded: Ctrl+C ends it quietly, --open opens
    the home page or the trip's page, and a slug that has no page in the build opens the home page and says so."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = os.path.realpath(tmp.name)
        helpers.touch(os.path.join(self.out, 'index.html'))
        helpers.touch(os.path.join(self.out, 'trips', 'syn-preview', 'index.html'))
        os.makedirs(os.path.join(self.out, 'trips', 'syn-half'))     # a folder of the build without its page

    def serve(self, *args, **kwargs):
        """build.serve(*args, **kwargs) with OUT the temp build, the stand-in server class and the browser recorded:
        (answer, stdout, stderr, servers made, addresses opened, events in order)."""
        made, events = [], []
        opened = Recorder(build.open_in_browser, then=lambda call: events.append('open'))
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(build, 'OUT', self.out), mock.patch.object(build, 'open_in_browser', opened), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            answer = build.serve(*args, server_class=server_class(made, events), **kwargs)
        return answer, stdout.getvalue(), stderr.getvalue(), made, [c['url'] for c in opened.calls], events

    def test_ctrl_c_stops_it_quietly_closes_the_server_and_returns_0(self):
        answer, out, err, made, opened, events = self.serve(8123)
        self.assertEqual(answer, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], 'serving http://localhost:8123  (Ctrl+C to stop)')
        self.assertEqual(lines[-1], 'stopped')
        self.assertEqual(err, '')
        self.assertNotIn('Traceback', out)
        self.assertNotIn('KeyboardInterrupt', out)
        self.assertEqual(len(made), 1)
        self.assertEqual((made[0].served, made[0].closed), (1, 1))
        self.assertEqual(events, ['made', 'serve_forever', 'server_close'])
        self.assertEqual(opened, [])

    def test_it_listens_on_this_computer_alone_on_the_port_given(self):
        for port in (8000, 8123):
            with self.subTest(port=port):
                made = self.serve(port)[3]
                self.assertEqual(made[0].address, ('127.0.0.1', port))

    def test_page_url(self):
        self.assertEqual(build.page_url(8000, ''), 'http://localhost:8000/')
        self.assertEqual(build.page_url(8000, 'syn-preview'), 'http://localhost:8000/trips/syn-preview/')
        self.assertEqual(build.page_url(8123, ''), 'http://localhost:8123/')
        self.assertEqual(build.page_url(8123, 'syn-preview'), 'http://localhost:8123/trips/syn-preview/')

    def test_a_bare_open_opens_the_home_page(self):
        answer, out, err, made, opened, events = self.serve(8000, '')
        self.assertEqual((answer, opened), (0, ['http://localhost:8000/']))
        self.assertNotIn('no page', out)

    def test_open_with_a_slug_opens_its_page_once_the_server_is_made(self):
        answer, out, err, made, opened, events = self.serve(8123, 'syn-preview')
        self.assertEqual((answer, opened), (0, ['http://localhost:8123/trips/syn-preview/']))
        self.assertEqual(events, ['made', 'open', 'serve_forever', 'server_close'])
        self.assertNotIn('no page', out)

    def test_a_slug_without_a_page_in_the_build_opens_the_home_page_and_says_so(self):
        for slug in ('syn-missing', 'syn-half'):
            with self.subTest(slug=slug):
                answer, out, err, made, opened, events = self.serve(8000, slug)
                self.assertEqual((answer, opened), (0, ['http://localhost:8000/']))
                said = [ln.strip() for ln in out.splitlines() if 'no page' in ln]
                self.assertEqual(len(said), 1, out)
                self.assertTrue(said[0].startswith('no page trips/%s/ in this build' % slug), said[0])

    def test_without_open_no_browser_is_opened(self):
        self.assertEqual(self.serve(8000, None)[4], [])
        self.assertEqual(self.serve(8000)[4], [])

    def test_watch_starts_the_watcher_with_the_link_value_and_the_modules(self):
        for link in (True, False):
            with self.subTest(link=link):
                started = threading.Event()
                watch = Recorder(build.watch, then=lambda call: started.set())
                with mock.patch.object(build, 'watch', watch):
                    answer = self.serve(8000, watch_link=link, only={'report'})[0]
                    self.assertTrue(started.wait(5), 'serve() with watch_link did not start build.watch')
                self.assertEqual(answer, 0)
                self.assertEqual(len(watch.calls), 1)
                self.assertIs(watch.calls[0]['link'], link)
                self.assertEqual(watch.calls[0]['only'], {'report'})

    def test_without_watch_nothing_watches(self):
        started = threading.Event()
        watch = Recorder(build.watch, then=lambda call: started.set())
        with mock.patch.object(build, 'watch', watch):
            self.assertEqual(self.serve(8000, watch_link=None)[0], 0)
            self.assertFalse(started.wait(0.3))
        self.assertEqual(watch.calls, [])


def checkout_tree(root):
    """A temp tree laid out like the checkout, every file a few bytes (each its own size), and the paths --watch looks
    at: a trip's index.md, its photos/ folder (one entry for the folder, not its files), a stylesheet, a helper and the
    site maps' meta. Left out: iCloud conflict copies (a file 'base 2.css', 'index 2.md', a folder 'x 2'), dot-files and
    dot-folders, and a trip's own renders under rendered/trips/."""
    files = ['content/trips/x/index.md', 'content/trips/x/photos/01.webp', 'content/trips/x/photos/01.sm.webp',
             'content/trips/x/index 2.md', 'content/trips/x 2/index.md', 'content/trips/x/.notes.md', 'content/.DS_Store',
             'content/.hidden/trips.md', 'assets/css/base.css', 'assets/css/base 2.css', 'tools/lib/a.py', 'tools/lib/.a.py.swp',
             'rendered/site/meta.json', 'rendered/site/meta 3.json', 'rendered/trips/x/meta.json']
    for i, name in enumerate(files):
        path = os.path.join(root, *name.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('x' * (i + 1))
    watched = ['content/trips/x/index.md', 'content/trips/x/photos', 'assets/css/base.css', 'tools/lib/a.py', 'rendered/site/meta.json']
    return [os.path.join(root, *name.split('/')) for name in watched]


class WatchStateTests(unittest.TestCase):
    """build.watch_state and build.changed on a temp tree (checkout_tree)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.realpath(tmp.name)
        self.watched = checkout_tree(self.root)
        self.index, self.photos, self.css, self.helper, self.site_meta = self.watched

    def p(self, name):
        return os.path.join(self.root, *name.split('/'))

    def test_exactly_the_sources_are_looked_at(self):
        self.assertEqual(sorted(build.watch_state(self.root)), sorted(self.watched))

    def test_a_file_is_its_mtime_and_size(self):
        state = build.watch_state(self.root)
        for path in (self.index, self.css, self.helper, self.site_meta):
            st = os.stat(path)
            self.assertEqual(state[path], (st.st_mtime_ns, st.st_size), path)

    def test_the_photos_folder_is_one_entry_its_own_mtime_and_size_0(self):
        state = build.watch_state(self.root)
        self.assertEqual(state[self.photos], (os.stat(self.photos).st_mtime_ns, 0))
        self.assertEqual([p for p in state if p.startswith(self.photos + os.sep)], [])

    def test_conflict_copies_dot_files_and_a_trips_renders_are_absent(self):
        state = build.watch_state(self.root)
        for name in ('content/trips/x/index 2.md', 'content/trips/x 2/index.md', 'assets/css/base 2.css', 'rendered/site/meta 3.json',
                     'content/trips/x/.notes.md', 'content/.DS_Store', 'content/.hidden/trips.md', 'tools/lib/.a.py.swp',
                     'rendered/trips/x/meta.json', 'content/trips/x/photos/01.webp', 'content/trips/x/photos/01.sm.webp'):
            self.assertNotIn(self.p(name), state)
        self.assertEqual([p for p in state if os.sep + 'x 2' + os.sep in p or os.sep + 'rendered' + os.sep + 'trips' in p], [])

    def test_bytecode_is_no_change(self):
        # the child build of a rebuild writes __pycache__/*.pyc under tools/: watched, that would rebuild for ever
        cache = self.p('tools/lib/__pycache__')
        os.makedirs(cache)
        with open(os.path.join(cache, 'a.cpython-39.pyc'), 'wb') as fh:
            fh.write(b'bytecode')
        with open(self.p('tools/lib/b.pyc'), 'wb') as fh:
            fh.write(b'bytecode')
        self.assertEqual(sorted(build.watch_state(self.root)), sorted(self.watched))

    def test_a_photo_written_over_in_place_is_not_a_change(self):
        # its file is not looked at, and writing it does not touch the folder's own entry
        before = build.watch_state(self.root)
        with open(self.p('content/trips/x/photos/01.webp'), 'w', encoding='utf-8') as fh:
            fh.write('a different photo, much longer than the first')
        self.assertEqual(build.changed(before, build.watch_state(self.root)), [])

    def test_without_a_root_it_looks_at_the_checkout(self):
        with mock.patch.object(build, 'ROOT', self.root):
            self.assertEqual(build.watch_state(), build.watch_state(self.root))

    def test_changed_on_an_edit(self):
        before = build.watch_state(self.root)
        with open(self.index, 'a', encoding='utf-8') as fh:
            fh.write(' and more')
        self.assertEqual(build.changed(before, build.watch_state(self.root)), [self.index])
        # the same size, another time: still a change
        before = build.watch_state(self.root)
        st = os.stat(self.css)
        os.utime(self.css, ns=(st.st_atime_ns, st.st_mtime_ns + 5 * 10 ** 9))
        self.assertEqual(build.changed(before, build.watch_state(self.root)), [self.css])

    def test_changed_on_an_addition_and_a_removal(self):
        before = build.watch_state(self.root)
        added = self.p('content/trips/y/index.md')
        helpers.touch(added)
        self.assertEqual(build.changed(before, build.watch_state(self.root)), [added])
        before = build.watch_state(self.root)
        os.remove(self.helper)
        self.assertEqual(build.changed(before, build.watch_state(self.root)), [self.helper])

    def test_changed_is_sorted_and_counts_new_gone_and_different(self):
        self.assertEqual(build.changed({}, {}), [])
        state = build.watch_state(self.root)
        self.assertEqual(build.changed(state, dict(state)), [])
        self.assertEqual(build.changed({'c': (1, 1), 'a': (1, 1), 'b': (1, 1)}, {'b': (2, 1), 'd': (1, 1), 'a': (1, 1)}), ['b', 'c', 'd'])
        self.assertEqual(build.changed({'a': (1, 1)}, {'a': (1, 2)}), ['a'])


class Completed(object):
    """What subprocess.run returns, as far as rebuild() reads it."""

    def __init__(self, returncode, stdout='', stderr=''):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


BUILD_PY = os.path.join(build.ROOT, 'tools', 'build.py')


class RebuildTests(unittest.TestCase):
    """build.rebuild: one build in a child process (subprocess.run replaced; rebuild imports subprocess when it runs, so
    subprocess.run itself is patched). The command line, and the one line printed on success or the ERROR lines and a
    'not rebuilt' line on failure."""

    def rebuild(self, answer, *args, **kwargs):
        """(rebuild's answer, what it printed, the subprocess.run calls as (args, kwargs)), with OUT a path of the test's."""
        calls = []

        def run(*a, **kw):
            calls.append((a, kw))
            return answer

        out = io.StringIO()
        self.out_dir = os.path.join(tempfile.gettempdir(), 'syn-not-written', '_site')
        with mock.patch('subprocess.run', run), mock.patch.object(build, 'OUT', self.out_dir), contextlib.redirect_stdout(out):
            ok = build.rebuild(*args, **kwargs)
        return ok, out.getvalue(), calls

    def test_the_command_line(self):
        ok, out, calls = self.rebuild(Completed(0), False)
        self.assertEqual(len(calls), 1)
        (args, kwargs), = calls
        self.assertEqual(args, ([sys.executable, BUILD_PY, '--out', self.out_dir],))
        self.assertEqual(kwargs, {'capture_output': True, 'text': True})

    def test_link_and_only_are_passed_on(self):
        ok, out, calls = self.rebuild(Completed(0), True, 'content/trips/x/index.md changed', {'report', 'home'})
        cmd = calls[0][0][0]
        self.assertEqual(cmd[:5], [sys.executable, BUILD_PY, '--out', self.out_dir, '--link'])
        self.assertEqual(cmd[5], '--only')
        self.assertEqual(sorted(cmd[6].split(',')), ['home', 'report'])
        self.assertEqual(len(cmd), 7)
        ok, out, calls = self.rebuild(Completed(0), False, 'x', {'report'})
        self.assertEqual(calls[0][0][0], [sys.executable, BUILD_PY, '--out', self.out_dir, '--only', 'report'])
        ok, out, calls = self.rebuild(Completed(0), True, 'x')
        self.assertEqual(calls[0][0][0], [sys.executable, BUILD_PY, '--out', self.out_dir, '--link'])

    def test_a_build_that_goes_through_prints_one_line_and_returns_true(self):
        ok, out, calls = self.rebuild(Completed(0, stdout='built 9 pages, 3 trips in 1.0s -> _site\n'), True,
                                      'content/trips/x/index.md changed (and 2 more)')
        self.assertIs(ok, True)
        self.assertRegex(out, r'\Arebuilt in \d+\.\ds: content/trips/x/index\.md changed \(and 2 more\)\n\Z')

    def test_a_content_error_prints_its_error_lines_and_not_rebuilt(self):
        err = ('WARNING content/trips/y/index.md: a warning\nERROR content/trips/x/index.md: date must be a date\n'
               'ERROR content/trips/z/index.md: cover_photo is not one of its photos\n')
        ok, out, calls = self.rebuild(Completed(1, stderr=err), True, 'content/trips/x/index.md changed')
        self.assertIs(ok, False)
        lines = out.splitlines()
        self.assertEqual(lines[:-1], ['ERROR content/trips/x/index.md: date must be a date',
                                      'ERROR content/trips/z/index.md: cover_photo is not one of its photos'])
        self.assertTrue(lines[-1].startswith('not rebuilt'), lines[-1])
        self.assertIn('; still serving', lines[-1])
        self.assertNotIn('rebuilt in', out)

    def test_another_failure_prints_the_last_five_lines_of_its_output(self):
        err = ''.join('line %d of a traceback\n' % i for i in range(1, 9))
        ok, out, calls = self.rebuild(Completed(1, stderr=err), False, 'tools/lib/a.py changed')
        self.assertIs(ok, False)
        lines = out.splitlines()
        self.assertEqual(lines[:-1], ['line %d of a traceback' % i for i in range(4, 9)])
        self.assertTrue(lines[-1].startswith('not rebuilt'), lines[-1])
        self.assertIn('; still serving', lines[-1])


class WatchTests(unittest.TestCase):
    """build.watch: look every `every` seconds until the threading.Event `stop` is set; a change rebuilds once, with the
    first changed path (relative to ROOT) and how many more changed. ROOT is the temp tree, rebuild a Recorder."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.realpath(tmp.name)
        self.index, self.photos, self.css, self.helper, self.site_meta = checkout_tree(self.root)
        self.stop = threading.Event()
        guard = threading.Timer(10, self.stop.set)    # a loop that never stops on its own ends here, and the test fails
        guard.start()
        self.addCleanup(guard.cancel)

    def watch(self, *args, **kwargs):
        rebuild = Recorder(build.rebuild, answer=True, then=lambda call: self.stop.set())
        with mock.patch.object(build, 'ROOT', self.root), mock.patch.object(build, 'rebuild', rebuild):
            build.watch(*args, stop=self.stop, **kwargs)
        return rebuild.calls

    def test_a_change_rebuilds_once_naming_the_first_path_and_the_count(self):
        now = build.watch_state(self.root)
        state = dict(now)
        state[self.index] = (0, 0)                                        # different
        del state[self.helper]                                            # new
        gone = os.path.join(self.root, 'content', 'trips', 'gone.md')
        state[gone] = (1, 1)                                              # gone
        calls = self.watch(True, every=0, state=state, only={'report'})
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0]['link'], calls[0]['why'], calls[0]['only']),
                         (True, '%s changed (and 2 more)' % os.path.join('content', 'trips', 'gone.md'), {'report'}))

    def test_one_change_is_named_alone(self):
        state = dict(build.watch_state(self.root))
        del state[self.css]
        calls = self.watch(False, every=0, state=state)
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0]['link'], calls[0]['why'], calls[0]['only']),
                         (False, '%s changed' % os.path.join('assets', 'css', 'base.css'), None))

    def test_nothing_changed_nothing_rebuilt(self):
        looks = []

        def sleep(seconds):
            looks.append(seconds)
            if len(looks) == 3:
                self.stop.set()

        with mock.patch.object(build.time, 'sleep', sleep):
            calls = self.watch(True, every=0.25, state=build.watch_state(self.root))
        self.assertEqual(calls, [])
        self.assertEqual(looks, [0.25, 0.25, 0.25])

    def test_a_save_made_during_a_rebuild_is_built_at_the_next_look(self):
        # the look from before the rebuild stays the baseline: a file saved while the child was building differs from it
        looks = [build.watch_state(self.root)]
        edited = dict(looks[0])
        edited[self.index] = (1, 1)                         # the save that starts the first rebuild
        during = dict(edited)
        during[self.css] = (2, 2)                           # saved while the first rebuild ran
        answers = iter([edited, during, during])
        calls = []

        def rebuild(link, why='', only=None):
            calls.append(why)
            if len(calls) == 2:
                self.stop.set()
            return True
        with mock.patch.object(build, 'ROOT', self.root), mock.patch.object(build, 'rebuild', rebuild), \
                mock.patch.object(build, 'watch_state', lambda root=None: next(answers)):
            build.watch(True, every=0, stop=self.stop, state=looks[0])
        self.assertEqual(calls, ['%s changed' % os.path.join('content', 'trips', 'x', 'index.md'),
                                 '%s changed' % os.path.join('assets', 'css', 'base.css')])

    def test_a_stop_already_set_looks_no_more(self):
        self.stop.set()
        self.assertEqual(self.watch(True, every=0, state={}), [])


class WorkflowTests(unittest.TestCase):
    """The preview is the author's alone: CI's build step is still a plain `python3 tools/build.py --check`, which copies
    photos, maps and GPX into the published folder (no --link, no --serve)."""

    def test_ci_builds_with_a_plain_check(self):
        with open(os.path.join(build.ROOT, '.github', 'workflows', 'pages.yml'), encoding='utf-8') as fh:
            text = fh.read()
        steps = [ln.strip() for ln in text.splitlines() if 'tools/build.py' in ln and not ln.strip().startswith('#')]
        self.assertEqual(steps, ['run: python3 tools/build.py --check'])
        for flag in ('--link', '--serve', '--watch', '--open'):
            self.assertIsNone(re.search(r'build\.py.*%s' % flag, text), flag)


if __name__ == '__main__':
    unittest.main()
