"""tools/reflow.py without a browser: no Chrome is a notice and exit 0, the page of frames the server answers beside
the site, how a page that scrolls sideways, a page that is not in the build and a frame that was never measured (or
measured in other units or script state than --km and --no-js ask for) fail, and which pages --all and --page check.
Chrome is a stand-in (subprocess.run replaced) that fetches the page of frames from the real server, on a free local
port, and answers with what the test says each frame measured. The measuring script runs in Chrome only in
ChromeTests, by hand (REFLOW_TESTS=1); otherwise node checks that it parses."""
import contextlib
import html
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import urllib.error
import urllib.request
from unittest import mock

import helpers  # noqa: F401  (puts tools/ on sys.path)

reflow = importlib.import_module('reflow')
smoke = importlib.import_module('smoke')

PAGES = ['', 'trips/', 'trips/some-report/', '404.html']


class Done(object):
    def __init__(self, stdout, stderr=''):
        self.stdout, self.stderr, self.returncode = stdout, stderr, 0


def fits(w, km=False, js=True):
    return {'scrollWidth': w, 'clientWidth': w, 'over': [], 'more': 0, 'km': km, 'js': js}


class ReflowTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.site = tmp.name
        for p in ('index.html', 'trips/index.html', 'trips/some-report/index.html', '404.html', 'assets/maps/index.html'):
            os.makedirs(os.path.dirname(os.path.join(self.site, p)), exist_ok=True)
            with open(os.path.join(self.site, p), 'w') as fh:
                fh.write('<!doctype html><title>%s</title>' % p)
        self.runs = []

    def chrome(self, measured=None, answer=True):
        """A stand-in for Chrome: it fetches the page of frames it is given, keeps its frames, and dumps the page with
        what measured[(path, width)] says (fits when not given; None leaves the frame out)."""
        measured = measured or {}

        def run(cmd, **kw):
            url = cmd[-1]
            with urllib.request.urlopen(url) as r:
                page = r.read().decode('utf-8')
            frames = json.loads(re.search(r'var FRAMES = (\[.*?\]), SETTLE', page).group(1))
            units, scripts = re.search(r'UNITS = "(\w+)", SCRIPTS = (true|false);', page).groups()
            self.runs.append({'cmd': cmd, 'url': url, 'page': page, 'frames': frames, 'timeout': kw.get('timeout'),
                              'units': units, 'scripts': scripts == 'true'})
            out = {}
            for f in frames:
                path = f['src'][len(smoke.PREFIX) + 1:]
                got = measured.get((path, f['w']), fits(f['w'], units == 'km', scripts == 'true'))
                if got is not None:
                    out[f['k']] = got
            pre = html.escape(json.dumps(out)) if answer else ''
            return Done('<html><head></head><body><pre id="reflow-out">%s</pre><iframe></iframe></body></html>' % pre)
        return run

    def run_reflow(self, run, args=(), which=lambda n: '/opt/chrome' if n == 'google-chrome' else None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(reflow, 'PAGES', [(p, p) for p in PAGES]):
            code = reflow.main([self.site] + list(args), which=which, run=run)
        return code, out.getvalue()

    def test_no_chrome_is_a_notice_and_not_a_failure(self):
        with mock.patch.object(smoke, 'MAC_CHROME', '/nowhere/chrome'):
            code, out = self.run_reflow(self.chrome(), which=lambda n: None)
        self.assertEqual(code, 0)
        self.assertIn('Chrome is not installed', out)
        self.assertEqual(self.runs, [])

    def test_no_built_site_is_said(self):
        os.remove(os.path.join(self.site, 'index.html'))
        code, out = self.run_reflow(self.chrome())
        self.assertEqual(code, 1)
        self.assertIn('no built site', out)
        self.assertEqual(self.runs, [])

    def test_every_page_fits_at_both_widths(self):
        code, out = self.run_reflow(self.chrome())
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines(), ['OK    /', 'OK    trips/', 'OK    trips/some-report/', 'OK    404.html',
                                            'reflow: all 4 pages fit at 320 and 375 px'])
        (one,) = self.runs
        # each page in a frame of each width, under the prefix, its height a phone's
        self.assertEqual([(f['src'], f['w'], f['h']) for f in one['frames']],
                         [('/personal-website/%s' % p, w, h) for p in PAGES for w, h in ((320, 568), (375, 667))])
        self.assertEqual(len({f['k'] for f in one['frames']}), 8)

    def test_the_page_of_frames_is_served_beside_the_site_from_the_same_origin(self):
        self.run_reflow(self.chrome())
        (one,) = self.runs
        self.assertRegex(one['url'], r'^http://127\.0\.0\.1:\d+/__reflow__/\d+\.html$')
        self.assertIn('<pre id="reflow-out"></pre>', one['page'])
        self.assertIn(reflow.MEASURE, one['page'])
        self.assertIn('iframe { position: absolute; top: 0; left: 0;', one['page'])    # every frame in the window
        # the site itself is still served under the prefix only
        httpd = smoke.serve(self.site, reflow.Handler)
        httpd.frames = {'/__reflow__/0.html': 'frames'}
        try:
            base = 'http://127.0.0.1:%d' % httpd.server_address[1]
            with urllib.request.urlopen(base + '/personal-website/trips/') as r:
                self.assertIn('trips/index.html', r.read().decode('utf-8'))
            with urllib.request.urlopen(base + '/__reflow__/0.html') as r:
                self.assertEqual((r.read(), r.headers['Content-Type']), (b'frames', 'text/html; charset=utf-8'))
            for path in ('/trips/', '/__reflow__/1.html'):
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    urllib.request.urlopen(base + path)
                self.assertEqual(cm.exception.code, 404)
                cm.exception.close()
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_chrome_is_headless_with_its_scrollbars_hidden_and_a_window_wider_than_its_least(self):
        self.run_reflow(self.chrome())
        cmd = self.runs[0]['cmd']
        for flag in ('--headless=new', '--hide-scrollbars', '--dump-dom', '--virtual-time-budget=%d' % reflow.BUDGET):
            self.assertIn(flag, cmd)
        size = [c for c in cmd if c.startswith('--window-size=')]
        self.assertEqual(len(size), 1)
        self.assertGreaterEqual(int(size[0].split('=')[1].split(',')[0]), 500)   # Chrome draws nothing under its least window
        self.assertEqual(self.runs[0]['timeout'], reflow.TIMEOUT)

    def test_a_page_that_scrolls_sideways_fails_and_names_what_sticks_out(self):
        over = {'scrollWidth': 343, 'clientWidth': 320, 'more': 2, 'over': [
            {'name': 'span.mi', 'what': '', 'right': 343, 'width': 210, 'text': 'SAT, JAN 17, 2026', 'ctx': 'span.ml < header.rep-head'},
            {'name': 'p.x', 'what': 'text', 'right': 330, 'width': 300, 'text': 'Unbreakable', 'ctx': ''},
            {'name': 'a.crumb', 'what': '::before', 'right': 324, 'width': 40, 'text': 'Reports', 'ctx': 'nav.crumbs'}]}
        code, out = self.run_reflow(self.chrome({('trips/some-report/', 320): over}))
        self.assertEqual(code, 1)
        self.assertIn('FAIL  trips/some-report/\n'
                      '      320 px: 23 px too wide: scrollWidth 343\n'
                      '          span.mi  right 343 (210 wide)  "SAT, JAN 17, 2026"  in span.ml < header.rep-head\n'
                      '          p.x (its text)  right 330 (300 wide)  "Unbreakable"\n'
                      '          a.crumb::before  right 324  "Reports"  in nav.crumbs\n'
                      '          ... and 2 more\n'
                      'OK    404.html', out)
        self.assertIn('reflow: 1 of 4 pages scroll sideways or were not measured at 320 and 375 px', out)

    def test_an_overflow_with_nothing_found_past_the_edge_still_fails(self):
        code, out = self.run_reflow(self.chrome({('', 375): {'scrollWidth': 376, 'clientWidth': 375, 'over': [], 'more': 0}}))
        self.assertEqual(code, 1)
        self.assertIn('FAIL  /\n      375 px: 1 px too wide: scrollWidth 376\n          no element found past the edge', out)

    def test_a_frame_never_measured_or_measured_with_a_scrollbar_fails(self):
        code, out = self.run_reflow(self.chrome({('trips/', 320): None, ('trips/', 375): {'error': 'TypeError: x'},
                                                 ('404.html', 320): {'scrollWidth': 305, 'clientWidth': 305}}))
        self.assertEqual(code, 1)
        self.assertIn('FAIL  trips/\n      320 px: not measured: the page did not finish loading in Chrome\n'
                      '      375 px: not measured: TypeError: x', out)
        self.assertIn('FAIL  404.html\n      320 px: not measured: the page is 305 px wide in a 320 px frame (a scrollbar?)', out)
        self.assertIn('2 of 4 pages', out)

    def test_nothing_written_by_the_page_of_frames_fails_every_page(self):
        code, out = self.run_reflow(self.chrome(answer=False))
        self.assertEqual(code, 1)
        self.assertEqual(out.count('not measured: the page did not finish loading in Chrome'), 8)

    def test_chrome_running_out_of_time_fails_its_pages(self):
        def run(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, kw.get('timeout'))
        code, out = self.run_reflow(run)
        self.assertEqual(code, 1)
        self.assertIn('4 of 4 pages', out)

    def test_a_page_missing_from_the_build_fails_without_a_frame(self):
        shutil.rmtree(os.path.join(self.site, 'trips', 'some-report'))
        code, out = self.run_reflow(self.chrome())
        self.assertEqual(code, 1)
        self.assertIn('FAIL  trips/some-report/\n      not in the build (trips/some-report/index.html)', out)
        self.assertNotIn('/personal-website/trips/some-report/', [f['src'] for f in self.runs[0]['frames']])

    def test_all_checks_every_page_of_the_build_in_batches(self):
        for i in range(reflow.BATCH):
            helpers.touch(os.path.join(self.site, 'trips', 'r%d' % i, 'index.html'))
        self.assertEqual(reflow.all_pages(self.site),
                         ['', 'trips/'] + ['trips/r%d/' % i for i in range(reflow.BATCH)] + ['trips/some-report/', '404.html'])
        code, out = self.run_reflow(self.chrome(), ['--all'])
        self.assertEqual(code, 0, out)
        self.assertIn('reflow: all %d pages fit' % (reflow.BATCH + 4), out)
        self.assertEqual([len(r['frames']) for r in self.runs], [2 * reflow.BATCH, 8])
        self.assertEqual(len({r['url'] for r in self.runs}), 2)                  # a page of frames for each run
        self.assertNotIn('assets/', out)

    def test_page_and_width_choose_what_is_checked(self):
        code, out = self.run_reflow(self.chrome(), ['--page', '/', '--page', 'trips', '--page', 'trips/?view=list',
                                                    '--width', '300'])
        self.assertEqual(code, 0, out)
        self.assertEqual([(f['src'], f['w']) for f in self.runs[0]['frames']],
                         [('/personal-website/', 300), ('/personal-website/trips/', 300),
                          ('/personal-website/trips/?view=list', 300)])
        self.assertIn('reflow: all 3 pages fit at 300 px', out)

    def test_km_and_no_js_set_up_the_frames_and_are_said(self):
        code, out = self.run_reflow(self.chrome())
        self.assertEqual((self.runs[0]['units'], self.runs[0]['scripts']), ('mi', True))   # stated, never left to the profile
        code, out = self.run_reflow(self.chrome(), ['--km', '--no-js'])
        self.assertEqual(code, 0, out)
        self.assertEqual((self.runs[1]['units'], self.runs[1]['scripts']), ('km', False))
        self.assertIn("localStorage.setItem('units', UNITS)", self.runs[1]['page'])
        self.assertIn("if (!SCRIPTS) el.setAttribute('sandbox', 'allow-same-origin');", self.runs[1]['page'])
        self.assertIn('reflow: all 4 pages fit at 320 and 375 px in km without scripts', out)

    def test_a_frame_in_the_wrong_units_or_whose_scripts_did_not_run_was_not_measured(self):
        code, out = self.run_reflow(self.chrome({('', 320): fits(320, km=True), ('trips/', 375): fits(375, js=False)}))
        self.assertEqual(code, 1)
        self.assertIn('FAIL  /\n      320 px: not measured: the page is in kilometers', out)
        self.assertIn('FAIL  trips/\n      375 px: not measured: its scripts did not run (the js class on <html>)', out)
        code, out = self.run_reflow(self.chrome({('404.html', 320): fits(320, km=False, js=True)}), ['--km', '--no-js'])
        self.assertIn('FAIL  404.html\n      320 px: not measured: the page is in miles', out)
        code, out = self.run_reflow(self.chrome({('404.html', 375): fits(375, km=True, js=True)}), ['--km', '--no-js'])
        self.assertIn('FAIL  404.html\n      375 px: not measured: its scripts ran (the js class on <html>)', out)

    def test_paths_and_files(self):
        for given, path in (('/', ''), ('index.html', ''), ('about', 'about/'), ('/about/', 'about/'),
                            ('trips/x/index.html', 'trips/x/'), ('trips?view=list', 'trips/?view=list'),
                            ('map/#region-x', 'map/#region-x'), ('404.html', '404.html')):
            self.assertEqual(reflow.norm(given), path, given)
        self.assertEqual(reflow.page_file('/s', ''), os.path.join('/s', 'index.html'))
        self.assertEqual(reflow.page_file('/s', 'trips/?view=list'), os.path.join('/s', 'trips', 'index.html'))
        self.assertEqual(reflow.page_file('/s', '404.html'), os.path.join('/s', '404.html'))

    def test_results_are_read_from_the_dumped_page(self):
        got = {'0@320': {'scrollWidth': 320, 'clientWidth': 320, 'over': [{'text': 'A & B <c>  "d"'}]}}
        dom = '<body><pre id="reflow-out">%s</pre></body>' % html.escape(json.dumps(got)).replace(' ', '&nbsp;')
        self.assertEqual(reflow.results(dom), got)
        for junk in ('', '<pre id="reflow-out"></pre>', '<pre id="reflow-out">{not json</pre>', '<pre id="reflow-out">[1]</pre>'):
            self.assertEqual(reflow.results(junk), {})

    def test_a_path_cannot_close_the_script_of_the_page_of_frames(self):
        page = reflow.frames_page([{'k': '0@320', 'src': '/personal-website/</script><b>', 'w': 320, 'h': 568}])
        self.assertEqual(page.count('</script>'), 1)
        self.assertTrue(page.endswith('</script>'))

    @unittest.skipUnless(shutil.which('node'), 'node is not installed')
    def test_the_measuring_script_parses(self):
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as fh:
            fh.write(re.search(r'<script>(.*)</script>', reflow.frames_page([]), re.S).group(1))
        self.addCleanup(os.remove, fh.name)
        r = subprocess.run(['node', '--check', fh.name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        self.assertEqual(r.returncode, 0, r.stdout)


HEAD = ('<!doctype html><html lang="en" class="js"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<style>body { margin: 0; font: 16px/24px sans-serif; } .wrap { padding: 0 16px; } .sr { position: absolute !important;'
        ' width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }</style><body><div class="wrap">')
# a page each: what it holds, and what the report must name (None: the page fits)
FAULTS = {
    'fits': ('<p>Short words.</p>', None),
    'nowrap': ('<p class="ml"><span class="mi" style="white-space: nowrap">SATURDAY, JANUARY 17, 2026 · AT THE TRAILHEAD</span></p>',
               'span.mi  right '),
    'word': ('<p class="long">Pneumonoultramicroscopicsilicovolcanoconiosis</p>', 'p.long (its text)  right '),
    'hidden': ('<div class="box" style="overflow-x: auto"><table><tr><td style="white-space: nowrap">A cell longer than the'
               ' phone is wide, in its own scroll box<span class="sr">, hidden words</span></td></tr></table></div>',
               'span.sr  right '),
    'hit': ('<style>.hit::before { content: ""; position: absolute; inset: 0 -20px; }</style>'
            '<p style="text-align: right"><a class="hit" href="#" style="position: relative">X</a></p>', 'a.hit::before  right '),
    # neither a fixed box nor a table that scrolls in a box of its own widens the page
    'decoys': ('<div style="position: fixed; left: 300px; top: 0; width: 200px">fixed</div><div style="overflow-x: auto"><table>'
               '<tr><td style="white-space: nowrap">A table that scrolls in its own box and leaves the page alone</td></tr>'
               '</table></div>', None),
}


@unittest.skipUnless(os.environ.get('REFLOW_TESTS') == '1', 'by hand: REFLOW_TESTS=1, with Chrome installed')
class ChromeTests(unittest.TestCase):
    """The measuring script in Chrome itself, on a page of each kind of fault and on decoys that must not count."""

    def test_each_fault_is_found_and_named_and_the_decoys_pass(self):
        if not smoke.find_chrome():
            self.skipTest('Chrome is not installed')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name, (body, _want) in dict(FAULTS, **{'': ('', None)}).items():
            os.makedirs(os.path.join(tmp.name, name), exist_ok=True)
            with open(os.path.join(tmp.name, name, 'index.html'), 'w', encoding='utf-8') as fh:
                fh.write(HEAD + body + '</div>')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = reflow.main([tmp.name] + ['--page=%s/' % name for name in FAULTS] + ['--width=320'])
        report = out.getvalue()
        self.assertEqual(code, 1, report)
        blocks = dict((b.split('\n')[0].split()[1].rstrip('/'), b) for b in re.split(r'\n(?=OK|FAIL)', report.split('\nreflow:')[0]))
        for name, (_body, want) in FAULTS.items():
            if want is None:
                self.assertTrue(blocks[name].startswith('OK'), blocks[name])
            else:
                self.assertTrue(blocks[name].startswith('FAIL  %s/\n      320 px: ' % name), blocks[name])
                self.assertIn('\n          ' + want, blocks[name])
        self.assertIn('reflow: 4 of 6 pages scroll sideways', report)


if __name__ == '__main__':
    unittest.main()
