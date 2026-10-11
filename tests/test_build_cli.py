"""tools/build.py as a command: main(argv), the content checks that run before the output folder is touched, the
wrapper around the built-site checks, and the one write a --link build must never make.

No test here builds the real site. build.build, checks.run and sitecheck.check are replaced by stand-ins where a test
is about what main() does with their answers; the --link test works on a trip folder in a temp dir.
"""
import contextlib
import importlib
import io
import os
import sys
import tempfile
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


if __name__ == '__main__':
    unittest.main()
