"""tools/smoke.py (Phase 8) without a browser: no Chrome is a notice and exit 0, what it reads in a dumped page, and
how a console error or a page whose scripts did not run fails a case. Chrome is a recorded stand-in (subprocess.run
replaced); the site is a tiny folder served for real on a free local port. The real run is by hand and in CI."""
import contextlib
import importlib
import io
import os
import tempfile
import unittest
from unittest import mock

import helpers  # noqa: F401  (puts tools/ on sys.path)

smoke = importlib.import_module('smoke')

GOOD = {
    'trips/?q=tallac&activity=hike': '<p id="trx-count" class="t-mono-s">3 OF 167 REPORTS</p>',
    'map/#region-oregon': '<button role="tab" aria-controls="region-oregon" aria-selected="true">Oregon</button>',
    'ski/#season-2022-23': '<a href="#season-2022-23" data-filter="2022-23" aria-checked="true">2022–23</a>',
    'trips/matterhorn-peak-west-couloir/': '<dialog class="lb" aria-label="Photo viewer"></dialog>',
    'trips/pacific-crest-trail-2024/': '<div class="ser-log is-wu" id="log"></div>',
}


class Done(object):
    def __init__(self, stdout, stderr=''):
        self.stdout, self.stderr, self.returncode = stdout, stderr, 0


class SmokeTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.site = tmp.name
        with open(os.path.join(self.site, 'index.html'), 'w') as fh:
            fh.write('<!doctype html>')
        self.urls = []

    def chrome(self, pages, stderr=''):
        def run(cmd, **kw):
            url = cmd[-1]
            self.urls.append(url)
            self.assertIn('--dump-dom', cmd)
            self.assertIn('--headless=new', cmd)
            path = url.split(smoke.PREFIX + '/', 1)[1]
            return Done('<html><body>%s<div id="units-live" class="sr"></div></body></html>' % pages.get(path, ''), stderr)
        return run

    def run_smoke(self, run, which=lambda n: '/opt/chrome' if n == 'google-chrome' else None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = smoke.main([self.site], which=which, run=run)
        return code, out.getvalue()

    def test_no_chrome_is_a_notice_and_not_a_failure(self):
        with mock.patch.object(smoke, 'MAC_CHROME', '/nowhere/chrome'):
            code, out = self.run_smoke(self.chrome(GOOD), which=lambda n: None)
        self.assertEqual(code, 0)
        self.assertIn('Chrome is not installed', out)
        self.assertEqual(self.urls, [])

    def test_every_case_passes_on_pages_that_did_their_work(self):
        code, out = self.run_smoke(self.chrome(GOOD))
        self.assertEqual(code, 0, out)
        self.assertIn('smoke: all 5 pages OK', out)
        self.assertEqual(len(self.urls), len(smoke.CASES))
        self.assertTrue(all('/personal-website/' in u and u.startswith('http://127.0.0.1:') for u in self.urls))

    def test_a_page_whose_script_did_nothing_fails(self):
        pages = dict(GOOD, **{'map/#region-oregon': '<button role="tab" aria-controls="region-oregon" aria-selected="false">'})
        code, out = self.run_smoke(self.chrome(pages))
        self.assertEqual(code, 1)
        self.assertIn('not seen: the Oregon tab is selected', out)
        self.assertIn('1 of 5 pages failed', out)

    def test_a_console_error_fails_the_page(self):
        log = '[1:2:1024/1.0:INFO:CONSOLE:2070] "Uncaught SyntaxError: Unexpected token \';\'", source: x (2070)\n'
        code, out = self.run_smoke(self.chrome(GOOD, stderr=log))
        self.assertEqual(code, 1)
        self.assertIn('Uncaught SyntaxError', out)

    def test_console_lines_and_start_tags(self):
        log = ('[x:INFO:CONSOLE(12)] "Uncaught TypeError: a is null", source: y\n'
               '[x:INFO:CONSOLE:3] "a plain log line", source: y\n'
               '[x:WARNING:something else] Error in some other component\n')
        self.assertEqual(len(smoke.console_errors(log)), 1)
        self.assertEqual(smoke.start_tag('<p><a href="#x" aria-checked="true">X</a></p>', 'href="#x"'),
                         '<a href="#x" aria-checked="true">')
        self.assertEqual(smoke.start_tag('<p>', 'href="#x"'), '')

    def test_no_built_site_is_said(self):
        os.remove(os.path.join(self.site, 'index.html'))
        code, out = self.run_smoke(self.chrome(GOOD))
        self.assertEqual(code, 1)
        self.assertIn('no built site', out)


if __name__ == '__main__':
    unittest.main()
