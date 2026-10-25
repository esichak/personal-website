"""Phase 4: tools/validate.py, the command line over tools/lib/checks.py, driven in-process through main(argv).

Every run names a temp folder with --content (two small valid reports, a home.json, a rendered/ folder beside it) and
a fixed --today, so nothing depends on the clock and the real content/ is never read; the one test of the defaults
replaces checks.survey and only looks at what it was called with. The built-site checks behind --site belong to
tools/sitegen/sitecheck.py and have their own tests: here a stand-in module takes their place, so this file pins only
what the command does with their answer. Three runs go through a real `python3 tools/validate.py` process, for the exit
status as a shell sees it. validate is imported in setUp so a missing module fails each test clearly.
"""
import contextlib
import datetime
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import checks  # noqa: E402
import content  # noqa: E402

import gpx_fixtures as gf  # noqa: E402
import helpers  # noqa: E402

TODAY = '2026-10-10'
DAY = datetime.date(2026, 10, 10)
CLEAN = 'content: 0 errors, 0 warnings, 4 notes (2 trips, 0 photos, 2 GPX files)'
NO_HOME = ('WARNING content/home.json: the file is missing, so the home page falls back to the newest featured report; create it '
           'to choose the featured trips (see docs/CONTENT_GUIDE.md)')
NOTES = ['NOTE content/trips/quiet-lap/index.md: no photos', 'NOTE content/trips/quiet-lap/index.md: no place',
         'NOTE content/trips/quiet-lap/index.md: no write-up', 'NOTE content/trips/ridge-walk/index.md: no photos']
BAD_TITLE = 'ERROR content/trips/quiet-lap/index.md: title must be text, got 7'
BAD_PLACE = 'ERROR content/trips/ridge-walk/index.md: place must be text, got 9000'
BAD_HOME = "ERROR content/home.json: unknown slug 'nope' in featured_slugs (no content/trips/nope/index.md)"


def load_cli(tc):
    """tools/validate.py as a module, or a clear failure of the calling test when it is missing."""
    try:
        return importlib.import_module('validate')
    except ImportError as ex:
        tc.fail('tools/validate.py is not importable: %s' % ex)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


class CliFixture(unittest.TestCase):

    def setUp(self):
        self.cli = load_cli(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.content = os.path.join(self.root, 'content')
        self.trips = os.path.join(self.content, 'trips')
        self.home = os.path.join(self.content, 'home.json')
        self.rendered = os.path.join(self.root, 'rendered')
        os.makedirs(self.trips)
        helpers.make_trip(self.trips, 'ridge-walk', title='Ridge Walk', activity='hike', date='2026-06-01', place='Desolation',
                          region='Lake Tahoe', body='Along the ridge and back.')
        helpers.make_trip(self.trips, 'quiet-lap', title='Quiet Lap', activity='ski', date='2026-02-02', region='Lake Tahoe')
        for slug in ('ridge-walk', 'quiet-lap'):
            write(os.path.join(self.trips, slug, 'track.gpx'), gf.SINGLE)
            write(os.path.join(self.rendered, 'trips', slug, 'meta.json'), '{}')
        write(os.path.join(self.rendered, 'site', 'meta.json'), json.dumps({'all_regions': ['Lake Tahoe']}))
        write(self.home, json.dumps({'featured_slugs': ['ridge-walk']}))

    def index(self, slug):
        return os.path.join(self.trips, slug, 'index.md')

    def sub(self, slug, old, new):
        text = read(self.index(slug))
        assert old in text, (old, text)
        write(self.index(slug), text.replace(old, new, 1))

    def break_three(self):
        """An error in each trip and in the manifest."""
        self.sub('quiet-lap', 'title: Quiet Lap', 'title: 7')
        self.sub('ridge-walk', 'place: Desolation', 'place: 9000')
        write(self.home, json.dumps({'featured_slugs': ['nope']}))

    def main(self, *args, today=TODAY, content_dir=True):
        """(exit status, stdout, stderr) of validate.main for these options, on the temp content and the fixed day."""
        argv = list(args)
        if content_dir:
            argv = ['--content', self.content] + argv
        if today:
            argv = ['--today', today] + argv
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = self.cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def lines(self, *args, **kw):
        code, out, err = self.main(*args, **kw)
        self.assertEqual(err, '')
        self.assertTrue(out.endswith('\n'))
        return code, out[:-1].split('\n')


class OutputAndExitTests(CliFixture):

    def test_clean_content_prints_the_summary_and_exits_0(self):
        self.assertEqual(self.main(), (0, CLEAN + '\n', ''))

    def test_a_warning_is_printed_and_still_exits_0(self):
        os.remove(self.home)
        self.assertEqual(self.lines(), (0, [NO_HOME, 'content: 0 errors, 1 warnings, 4 notes (2 trips, 0 photos, 2 GPX files)']))

    def test_strict_fails_on_a_warning_and_only_on_one(self):
        self.assertEqual(self.main('--strict')[0], 0)
        os.remove(self.home)
        code, lines = self.lines('--strict')
        self.assertEqual(code, 1)
        self.assertEqual(lines[0], NO_HOME)        # the same output: only the status differs

    def test_notes_alone_never_fail_even_under_strict(self):
        code, lines = self.lines('--strict', '-v')
        self.assertEqual(code, 0)
        self.assertEqual(lines, NOTES + [CLEAN])

    def test_errors_are_one_line_each_in_file_order_then_the_summary_and_exit_1(self):
        self.break_three()
        code, lines = self.lines()
        self.assertEqual(code, 1)
        self.assertEqual(lines, [BAD_HOME, BAD_TITLE, BAD_PLACE, 'content: 3 errors, 0 warnings, 0 notes (2 trips, 0 photos, 2 GPX files)'])
        self.assertNotIn('Traceback', '\n'.join(lines))

    def test_an_error_and_a_warning_in_one_file_print_error_first(self):
        # by text alone 'route_shape ...' would come before 'title ...'
        self.sub('quiet-lap', 'title: Quiet Lap', 'title: 7\nroute_shape: lollipop')
        code, lines = self.lines()
        self.assertEqual(code, 1)
        self.assertEqual(lines[:2], [BAD_TITLE, "WARNING content/trips/quiet-lap/index.md: route_shape 'lollipop' is not one of loop, "
                                                'out-and-back, point-to-point; it is shown as written'])

    def test_quiet_prints_errors_and_the_summary_only(self):
        self.sub('quiet-lap', 'title: Quiet Lap', 'title: 7')
        os.remove(self.home)
        for flag in ('-q', '--quiet'):
            with self.subTest(flag=flag):
                self.assertEqual(self.lines(flag), (1, [BAD_TITLE, 'content: 1 errors, 1 warnings, 1 notes (2 trips, 0 photos, 2 GPX files)']))
        self.assertIn(NO_HOME, self.lines()[1])

    def test_quiet_on_content_with_only_a_warning_is_just_the_summary(self):
        os.remove(self.home)
        self.assertEqual(self.lines('-q'), (0, ['content: 0 errors, 1 warnings, 4 notes (2 trips, 0 photos, 2 GPX files)']))
        self.assertEqual(self.main('-q', '--strict')[0], 1)     # what is printed does not decide the status

    def test_verbose_lists_the_notes_too(self):
        os.remove(self.home)
        for flag in ('-v', '--verbose'):
            with self.subTest(flag=flag):
                code, lines = self.lines(flag)
                self.assertEqual(code, 0)
                # sorted by file; within a file errors, then warnings, then notes
                self.assertEqual(lines, [NO_HOME] + NOTES + ['content: 0 errors, 1 warnings, 4 notes (2 trips, 0 photos, 2 GPX files)'])
        self.assertEqual([ln for ln in self.lines()[1] if ln.startswith('NOTE')], [])

    def test_the_report_goes_to_stdout_and_nothing_to_stderr(self):
        self.break_three()
        code, out, err = self.main('-v')
        self.assertEqual((code, err), (1, ''))
        self.assertEqual(out.count('\n'), 4)

    def test_the_lines_are_checks_line_and_checks_summary(self):
        self.break_three()
        found, counts = checks.survey(self.trips, self.home, self.rendered, DAY)
        self.assertEqual(self.lines('-v')[1], [checks.line(f) for f in found] + [checks.summary(found, counts)])


class JsonTests(CliFixture):

    def test_json_is_every_finding_and_nothing_else(self):
        os.remove(self.home)
        self.sub('quiet-lap', 'title: Quiet Lap', 'title: 7')
        code, out, err = self.main('--json')
        self.assertEqual((code, err), (1, ''))
        data = json.loads(out)
        self.assertEqual(data, checks.run(self.trips, self.home, self.rendered, DAY))
        self.assertEqual(sorted({f['level'] for f in data}), ['error', 'note', 'warning'])
        for f in data:
            self.assertEqual(sorted(f), ['file', 'level', 'text'])
        self.assertNotIn('content: ', out.split(']')[-1])       # no summary line after the list

    def test_json_keeps_non_ascii_text_readable(self):
        self.sub('quiet-lap', 'title: Quiet Lap', 'title: Quiet Lap\nplace: [Tête Blanche]')
        code, out, err = self.main('--json')
        self.assertEqual(code, 1)
        self.assertIn('Tête Blanche', out)
        self.assertEqual(json.loads(out)[0]['text'], "content/trips/quiet-lap/index.md: place must be text, got ['Tête Blanche']")

    def test_json_exit_status_follows_the_same_rules(self):
        self.assertEqual(self.main('--json')[0], 0)
        self.assertEqual(self.main('--json', '--strict')[0], 0)
        os.remove(self.home)
        self.assertEqual(self.main('--json')[0], 0)
        self.assertEqual(self.main('--json', '--strict')[0], 1)

    def test_json_lists_notes_whatever_q_or_v_says(self):
        for flags in ((), ('-q',), ('-v',)):
            with self.subTest(flags=flags):
                data = json.loads(self.main('--json', *flags)[1])
                self.assertEqual([checks.line(f) for f in data], NOTES)


class OptionTests(CliFixture):

    def test_today_sets_the_day_dates_are_judged_against(self):
        code, lines = self.lines(today='2026-03-01')
        self.assertEqual(code, 0)
        self.assertEqual(lines[0], 'WARNING content/trips/ridge-walk/index.md: date 2026-06-01 is in the future (today is 2026-03-01)')
        self.assertEqual(self.lines(today='2026-05-31')[1], [CLEAN])        # the day before: tomorrow is not the future yet

    def test_a_today_that_is_not_a_date_is_a_usage_error(self):
        for value in ('tomorrow', '2026-13-45', '20261010', '2026-W41-6', '2026-10-1', ''):
            with self.subTest(value=value):
                code, out, err = self.main('--today', value, today=None)
                self.assertEqual((code, out), (2, ''))
                self.assertIn('is not a date written YYYY-MM-DD', err)

    def test_without_today_the_clock_is_left_to_checks(self):
        with mock.patch.object(checks, 'survey', return_value=([], {'trips': 0, 'photos': 0, 'gpx': 0})) as survey:
            code, out, err = self.main(today=None)
        survey.assert_called_once_with(self.trips, self.home, self.rendered, None)
        self.assertEqual((code, out, err), (0, 'content: 0 errors, 0 warnings, 0 notes (0 trips, 0 photos, 0 GPX files)\n', ''))

    def test_without_content_the_checkout_s_own_folders_are_left_to_checks(self):
        # the real content/ is never read here: survey is replaced, and only its arguments are looked at
        with mock.patch.object(checks, 'survey', return_value=([], {'trips': 0, 'photos': 0, 'gpx': 0})) as survey:
            code, out, err = self.main(content_dir=False)
        survey.assert_called_once_with(None, None, None, DAY)
        self.assertEqual(code, 0)

    def test_content_names_trips_home_json_and_the_rendered_folder_beside_it(self):
        os.remove(os.path.join(self.rendered, 'trips', 'ridge-walk', 'meta.json'))
        code, lines = self.lines()
        self.assertEqual(lines[0], 'WARNING content/trips/ridge-walk/index.md: no rendered map (rendered/trips/ridge-walk/meta.json is '
                                   'missing); run python3 tools/render.py ridge-walk (until then the page shows "Map not rendered yet")')
        shutil.rmtree(self.rendered)                      # a content folder on its own: nothing is said about renders
        self.assertEqual(self.lines()[1], [CLEAN])

    def test_content_may_be_given_relative_or_with_a_trailing_slash(self):
        self.assertEqual(self.main('--content', self.content + os.sep, content_dir=False)[:2], (0, CLEAN + '\n'))
        here = os.getcwd()
        os.chdir(self.root)
        try:
            self.assertEqual(self.main('--content', 'content', content_dir=False)[:2], (0, CLEAN + '\n'))
        finally:
            os.chdir(here)

    def test_a_content_folder_without_trips_is_a_usage_error(self):
        empty = os.path.join(self.root, 'empty')
        os.makedirs(empty)
        for folder in (empty, os.path.join(self.root, 'nowhere'), self.trips):
            with self.subTest(folder=folder):
                code, out, err = self.main('--content', folder, content_dir=False)
                self.assertEqual((code, out), (2, ''))
                self.assertEqual(err, 'ERROR --content %s: there is no trips/ folder in it\n' % folder)

    def test_q_and_v_together_are_a_usage_error(self):
        code, out, err = self.main('-q', '-v')
        self.assertEqual((code, out), (2, ''))
        self.assertIn('not allowed with', err)

    def test_an_unknown_option_and_a_stray_argument_are_usage_errors(self):
        for args in (('--fix',), ('content',), ('--content',)):
            with self.subTest(args=args):
                code, out, err = self.main(*args, content_dir=False)
                self.assertEqual((code, out), (2, ''))
                self.assertIn('usage: validate.py', err)

    def test_help_exits_0_and_names_every_option_and_the_exit_statuses(self):
        code, out, err = self.main('--help', today=None, content_dir=False)
        self.assertEqual((code, err), (0, ''))
        for word in ('--content', '--site', '--strict', '--json', '-q', '-v', '--today', 'Exit status'):
            self.assertIn(word, out)

    def test_main_returns_the_status_and_never_exits_by_itself(self):
        for args, status in (((), 0), (('--fix',), 2), (('--help',), 0)):
            with self.subTest(args=args):
                self.assertIs(type(self.main(*args)[0]), int)
                self.assertEqual(self.main(*args)[0], status)

    def test_nothing_is_written_to_the_content(self):
        def snapshot():
            out = {}
            for folder, _dirs, files in os.walk(self.root):
                for n in files:
                    p = os.path.join(folder, n)
                    out[p] = (os.path.getsize(p), os.stat(p).st_mtime_ns)
            return out
        self.break_three()
        before = snapshot()
        for args in ((), ('-v',), ('--json',), ('--strict',)):
            self.main(*args)
        self.assertEqual(snapshot(), before)


class SiteTests(CliFixture):
    """--site DIR: the command's side of the built-site checks (their rules are tested with sitecheck itself)."""

    def setUp(self):
        CliFixture.setUp(self)
        self.site = os.path.join(self.root, '_site')
        os.makedirs(self.site)
        self.calls = []

    def stand_in(self, problems):
        def check(out_dir, content_trips_dir=None):
            self.calls.append((out_dir, content_trips_dir))
            return list(problems)
        mod = types.ModuleType('sitegen.sitecheck')
        mod.check = check
        return mock.patch.dict(sys.modules, {'sitegen.sitecheck': mod})

    def test_site_problems_print_as_errors_after_the_content_lines_and_fail_the_run(self):
        os.remove(self.home)
        with self.stand_in(['BROKEN trips/x/index.html -> y.gpx', 'META 404.html: no noindex']):
            code, lines = self.lines('--site', self.site)
        self.assertEqual(code, 1)
        self.assertEqual(lines, [NO_HOME, 'ERROR BROKEN trips/x/index.html -> y.gpx', 'ERROR META 404.html: no noindex',
                                 'content: 0 errors, 1 warnings, 4 notes (2 trips, 0 photos, 2 GPX files)', 'site: 2 problems'])
        self.assertEqual(self.calls, [(self.site, self.trips)])

    def test_a_site_without_problems_says_so_and_exits_0(self):
        with self.stand_in([]):
            self.assertEqual(self.lines('--site', self.site), (0, [CLEAN, 'site: 0 problems']))

    def test_site_problems_are_printed_under_quiet_as_well(self):
        with self.stand_in(['SITEMAP lists trips/gone/']):
            self.assertEqual(self.lines('--site', self.site, '-q'), (1, ['ERROR SITEMAP lists trips/gone/', CLEAN, 'site: 1 problems']))

    def test_the_site_folder_is_handed_over_as_an_absolute_path(self):
        here = os.getcwd()
        os.chdir(self.root)
        try:
            with self.stand_in([]):
                self.main('--site', '_site')
        finally:
            os.chdir(here)
        self.assertEqual([os.path.realpath(c[0]) for c in self.calls], [os.path.realpath(self.site)])
        self.assertTrue(os.path.isabs(self.calls[0][0]))

    def test_without_content_the_site_is_checked_against_the_checkout_s_trips(self):
        with self.stand_in([]), mock.patch.object(checks, 'survey', return_value=([], {})):
            self.main('--site', self.site, content_dir=False)
        self.assertEqual(self.calls, [(self.site, content.TRIPS_DIR)])

    def test_json_carries_site_problems_as_errors_without_a_file(self):
        with self.stand_in(['FEED item 3 links trips/gone/']):
            code, out, err = self.main('--site', self.site, '--json')
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data[-1], {'level': 'error', 'file': '', 'text': 'FEED item 3 links trips/gone/'})
        self.assertEqual([checks.line(f) for f in data[:-1]], NOTES)

    def test_a_site_folder_that_is_not_there_is_a_usage_error(self):
        with self.stand_in(['never asked']):
            code, out, err = self.main('--site', os.path.join(self.root, 'nowhere'))
        self.assertEqual((code, out), (2, ''))
        self.assertEqual(err, 'ERROR --site %s: no such folder (build the site first: python3 tools/build.py)\n'
                         % os.path.join(self.root, 'nowhere'))
        self.assertEqual(self.calls, [])

    def test_without_the_sitecheck_module_one_line_says_so_and_the_status_is_2(self):
        real = importlib.import_module

        def no_sitecheck(name, *a, **k):
            if name == 'sitegen.sitecheck':
                raise ModuleNotFoundError("No module named 'sitegen.sitecheck'", name=name)
            return real(name, *a, **k)
        self.break_three()
        with mock.patch.object(self.cli.importlib, 'import_module', no_sitecheck):
            code, out, err = self.main('--site', self.site)
        self.assertEqual((code, out), (2, ''))          # not even the content findings: the request could not be met
        self.assertEqual(err, "ERROR --site: the built-site checks are unavailable (tools/sitegen/sitecheck.py: No module named "
                              "'sitegen.sitecheck')\n")

    def test_a_sitecheck_module_without_check_is_unavailable_too(self):
        with mock.patch.dict(sys.modules, {'sitegen.sitecheck': types.ModuleType('sitegen.sitecheck')}):
            code, out, err = self.main('--site', self.site)
        self.assertEqual((code, out), (2, ''))
        self.assertEqual(err, 'ERROR --site: the built-site checks are unavailable (tools/sitegen/sitecheck.py has no check())\n')

    def test_sitecheck_is_not_imported_unless_asked_for(self):
        def refuse(name, *a, **k):
            raise AssertionError('imported %s without --site' % name)
        with mock.patch.object(self.cli.importlib, 'import_module', refuse):
            self.assertEqual(self.main()[0], 0)


class ProcessTests(CliFixture):
    """The command as a shell runs it."""

    def run_cli(self, *args):
        cmd = [sys.executable, '-W', 'error', os.path.join(ROOT, 'tools', 'validate.py'), '--content', self.content, '--today', TODAY]
        p = subprocess.run(cmd + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, cwd=self.root)
        return p.returncode, p.stdout, p.stderr

    def test_exit_0_with_the_summary(self):
        self.assertEqual(self.run_cli(), (0, CLEAN + '\n', ''))

    def test_exit_1_with_error_lines_and_no_traceback(self):
        self.break_three()
        code, out, err = self.run_cli()
        self.assertEqual((code, err), (1, ''))
        self.assertEqual(out.split('\n')[:3], [BAD_HOME, BAD_TITLE, BAD_PLACE])
        self.assertNotIn('Traceback', out + err)

    def test_exit_2_on_a_usage_error(self):
        code, out, err = self.run_cli('--fix')
        self.assertEqual((code, out), (2, ''))
        self.assertIn('usage: validate.py', err)


if __name__ == '__main__':
    unittest.main()
