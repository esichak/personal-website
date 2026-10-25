#!/usr/bin/env python3
"""A smoke test of the built site in headless Chrome: python3 tools/smoke.py [SITE]   (SITE: the build, default _site/)

It serves SITE under /personal-website/ as GitHub Pages does, opens a few pages in Chrome (google-chrome --headless=new
--dump-dom) and reads the page as the scripts left it: every page must carry the live region base.js adds (so the
bundle parsed and ran), and each case its own sign that its page script did its work (CASES). Any console error
Chrome logs ('Uncaught ...' on a CONSOLE line of its log) fails the case. It exits 0 with a notice when Chrome is not
installed, and CI runs it as a job of its own that never blocks the deploy (.github/workflows/pages.yml).

Chrome only: Safari, Firefox, a real phone and screen readers are not covered by this, or by anything else that runs
on its own. The cases name today's content (a region, a ski season, a report with photos): when that content changes,
change CASES.
"""
import argparse
import functools
import http.server
import os
import re
import shutil
import subprocess
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFIX = '/personal-website'
BASE_JS = 'id="units-live"'          # the live region base.js adds on every page: the bundle parsed and ran
MAC_CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
TIMEOUT = 60

# (path under the site, what it shows, a test of the dumped DOM)
CASES = [
    ('trips/?q=tallac&activity=hike', 'the explorer counted a search',
     lambda dom: re.search(r'id="trx-count"[^>]*>\s*\d+ OF \d+ REPORTS', dom) is not None),
    ('map/#region-oregon', 'the Oregon tab is selected',
     lambda dom: 'aria-selected="true"' in start_tag(dom, 'aria-controls="region-oregon"')),
    ('ski/#season-2022-23', 'the 2022-23 season filter is on',
     lambda dom: 'aria-checked="true"' in start_tag(dom, 'href="#season-2022-23"')),
    ('trips/matterhorn-peak-west-couloir/', 'the photo viewer is there',
     lambda dom: '<dialog class="lb"' in dom),
    ('trips/pacific-crest-trail-2024/', 'the journal opened with its written days',
     lambda dom: re.search(r'class="[^"]*\bser-log\b[^"]*\bis-wu\b', dom) is not None),
]


def start_tag(dom, attr):
    """The start tag that holds attr ('' when none does)."""
    i = dom.find(attr)
    if i < 0:
        return ''
    j = dom.rfind('<', 0, i)
    k = dom.find('>', i)
    return dom[j:k + 1] if j >= 0 and k >= 0 else ''


def find_chrome(which=shutil.which):
    for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'):
        found = which(name)
        if found:
            return found
    return MAC_CHROME if os.path.exists(MAC_CHROME) else None


class Handler(http.server.SimpleHTTPRequestHandler):
    """The site under /personal-website/, the way GitHub Pages serves it; anything else is a 404."""

    def translate_path(self, path):
        if path == PREFIX or path.startswith(PREFIX + '/'):
            path = path[len(PREFIX):] or '/'
        else:
            path = '/__not_under_the_prefix__' + path
        return super().translate_path(path)

    def log_message(self, *args):
        pass


def serve(site):
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=site))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


_CONSOLE = re.compile(r'CONSOLE[(:]')   # 'INFO:CONSOLE:2070] "Uncaught SyntaxError: ..."' (Chrome 155), 'CONSOLE(12)' in older ones


def console_errors(log):
    return [ln.strip() for ln in log.splitlines() if _CONSOLE.search(ln) and ('Uncaught' in ln or 'Error' in ln)]


def dump(chrome, url, run=subprocess.run):
    """(dumped DOM, console error lines) of one page."""
    cmd = [chrome, '--headless=new', '--disable-gpu', '--no-first-run', '--virtual-time-budget=4000',
           '--enable-logging=stderr', '--v=0', '--dump-dom', url]
    if sys.platform.startswith('linux'):
        cmd.insert(1, '--no-sandbox')       # the runner's Chrome cannot make its sandbox
    r = run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=TIMEOUT)
    return r.stdout or '', console_errors(r.stderr or '')


def main(argv=None, which=shutil.which, run=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('site', nargs='?', default=os.path.join(ROOT, '_site'), help='the built site (default _site/)')
    a = ap.parse_args(argv)
    chrome = find_chrome(which)
    if not chrome:
        print('smoke: Chrome is not installed here; nothing was tested')
        return 0
    if not os.path.isfile(os.path.join(a.site, 'index.html')):
        print('smoke: no built site in %s (python3 tools/build.py first)' % a.site)
        return 1
    httpd = serve(os.path.abspath(a.site))
    base = 'http://127.0.0.1:%d%s/' % (httpd.server_address[1], PREFIX)
    failed = 0
    try:
        for path, what, test in CASES:
            try:
                dom, errors = dump(chrome, base + path, run)
            except subprocess.TimeoutExpired:
                dom, errors = '', ['Chrome did not finish in %d s' % TIMEOUT]
            problems = []
            if BASE_JS not in dom:
                problems.append('base.js did not run (no %s)' % BASE_JS)
            if not test(dom):
                problems.append('not seen: %s' % what)
            problems += errors
            failed += bool(problems)
            print('%-5s %s%s' % ('FAIL' if problems else 'OK', path, ''.join('\n      ' + p for p in problems)))
    finally:
        httpd.shutdown()
        httpd.server_close()
    print('smoke: %s' % ('%d of %d pages failed' % (failed, len(CASES)) if failed else 'all %d pages OK' % len(CASES)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
