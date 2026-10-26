#!/usr/bin/env python3
"""Sideways scrolling at phone widths, in headless Chrome: python3 tools/reflow.py [SITE] [--all | --page PATH ...]

It serves SITE (the build, default _site/) under /personal-website/ as tools/smoke.py does, opens PAGES (one of each
kind of page, and the two explorers' list views) at 320 and 375 px wide, and fails a page that a reader could scroll
sideways at either width: its document.documentElement.scrollWidth is larger than its clientWidth. For each such page
it names the outermost elements past the right edge that no box clips: an element, the text in it, or its ::before /
::after (a 44 px hit area). --all checks every page of the build (about 370, two minutes) as it loads; --page PATH, the
pages named; --width, other widths; --km, the pages in kilometers; --no-js, the pages without their scripts.

Chrome draws nothing narrower than its smallest window (a --window-size of 390 px gave a blank page), so each page
is loaded in a same-origin <iframe> of the phone's width inside a page of frames that the server answers outside the
prefix, and Chrome's --dump-dom prints what that page measured. --hide-scrollbars keeps a 15 px scrollbar from
narrowing the frames. Chrome only and opt-in: without Chrome it exits 0 with a notice, and CI does not run it. PAGES
name today's content: when that content changes, change PAGES.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys

import smoke

ROOT = smoke.ROOT
WIDTHS = (320, 375)
HEIGHTS = {320: 568, 375: 667}   # the frames' heights: an iPhone SE (1st) and an iPhone 8; only svh-sized boxes read them
BATCH = 8                        # pages per Chrome run, each at every width
BUDGET = 10000                   # --virtual-time-budget (ms): every frame has loaded and been measured well before
SETTLE = 300                     # ms after a frame's load and fonts before it is measured, for its page scripts
SHOWN = 8                        # elements named per page and width
FRAMES = '/__reflow__/'          # the pages of frames, outside the prefix: same origin, so they can read the frames
TIMEOUT = 180

# (path under the site, what it is)
PAGES = [
    ('', 'home'),
    ('trips/', 'the Trips explorer'),
    ('trips/?view=list', 'the explorer as a list'),
    ('hiking/', 'an activity section'),
    ('ski/', 'the ski section, with its seasons'),
    ('trips/matterhorn-peak-west-couloir/', 'a single-day report with photos'),
    ('trips/matterhorn-peak-west-couloir/map/', "a report's full-screen map"),
    ('trips/chamonix-zermatt-haute-route/', 'a multi-day report'),
    ('trips/pacific-crest-trail-2024/', 'the PCT journal'),
    ('map/', 'the map page and its archive table'),
    ('map/eastern-sierra/', "a region's full-screen map"),
    ('regions/eastern-sierra/', 'a region page'),
    ('tick-list/', 'the tick list'),
    ('tick-list/?view=list', 'the tick list as a list'),
    ('trips/crystal-range-to-bayview/', 'a goal page'),
    ('about/', 'About'),
    ('404.html', 'the 404 page'),
]

# Runs in the page of frames: FRAMES, SETTLE, SHOWN, UNITS and SCRIPTS are set before it (frames_page). Each frame is
# measured once its page has loaded, its fonts are in and its scripts have had SETTLE ms; every result is written into
# #reflow-out at once, so a frame that never loads leaves the others' results.
MEASURE = r'''
(function () {
  'use strict';
  var out = {}, pre = document.getElementById('reflow-out');
  function put(k, r) { out[k] = r; pre.textContent = JSON.stringify(out); }
  try { localStorage.setItem('units', UNITS); } catch (e) { /* the frames share it: they start in UNITS */ }
  FRAMES.forEach(function (f) {
    var el = document.createElement('iframe');
    el.width = f.w;
    el.height = f.h;
    if (!SCRIPTS) el.setAttribute('sandbox', 'allow-same-origin');   // readable from here, its scripts off
    el.addEventListener('load', function () {
      var doc = el.contentDocument;
      if (!doc) { put(f.k, {error: 'the frame cannot be read from the page of frames'}); return; }
      (doc.fonts ? doc.fonts.ready : Promise.resolve()).then(function () {
        setTimeout(function () {
          try { put(f.k, measure(el.contentWindow)); } catch (e) { put(f.k, {error: String(e)}); }
        }, SETTLE);
      });
    });
    el.src = f.src;
    document.body.appendChild(el);
  });

  function measure(win) {
    var doc = win.document, root = doc.documentElement, vw = root.clientWidth, sx = win.scrollX;
    var res = {scrollWidth: root.scrollWidth, clientWidth: vw, over: [], more: 0,
               km: root.classList.contains('km'), js: root.classList.contains('js')};
    if (res.scrollWidth <= vw) return res;
    var VIEWPORT = {};
    function cs(el, pseudo) { return win.getComputedStyle(el, pseudo || null); }
    // an element's overflow clips every box whose chain of containing blocks passes through it (CSS 2.1, 11.1.1);
    // body's and html's go to the viewport, which is what scrolls
    function clips(el) {
      if (el === root || el === doc.body) return false;
      var s = cs(el);
      return s.display !== 'contents' && (s.overflowX !== 'visible' || /paint|strict|content/.test(s.contain));
    }
    // a transform, filter, perspective or containment makes an element the containing block of fixed boxes too
    function holdsFixed(s) {
      return s.transform !== 'none' || s.perspective !== 'none' || s.filter !== 'none' ||
        /paint|layout|strict|content/.test(s.contain) || /transform|perspective|filter/.test(s.willChange) ||
        (s.containerType || 'normal') !== 'normal';
    }
    // the containing block of a box placed with pos in from: null for the page's own, VIEWPORT for a fixed box's.
    // An absolute box skips the unpositioned boxes between, so their overflow does not clip it: a .sr span in an
    // unpositioned scroll box widens the page
    function cbOf(from, pos) {
      if (pos !== 'absolute' && pos !== 'fixed') return from;
      for (var a = from; a; a = a.parentElement) {
        var s = cs(a);
        if (s.display !== 'contents' && ((pos === 'absolute' && s.position !== 'static') || holdsFixed(s))) return a;
      }
      return pos === 'fixed' ? VIEWPORT : null;
    }
    // does a box whose containing block is cb add to the page's scrollable overflow? Not when a box on the way clips
    // it, nor inside a box fixed to the viewport
    function reaches(cb) {
      for (var x = cb; x; x = cbOf(x.parentElement, cs(x).position)) {
        if (x === VIEWPORT || clips(x)) return false;
      }
      return true;
    }
    var seen = new Map(), hits = [];
    function hit(el, right, what) {
      var h = seen.get(el);
      if (h) { h.right = Math.max(h.right, right); return; }
      h = {el: el, right: right, what: what};
      seen.set(el, h);
      hits.push(h);
    }
    var els = [doc.body].concat(Array.prototype.slice.call(doc.body.querySelectorAll('*')));
    els.forEach(function (el) {
      var r = el.getBoundingClientRect();
      if ((r.width || r.height) && r.right + sx > vw + 0.5 && reaches(cbOf(el.parentElement, cs(el).position))) {
        hit(el, r.right + sx, '');
      }
    });
    var walk = doc.createTreeWalker(doc.body, win.NodeFilter.SHOW_TEXT), range = doc.createRange(), t;
    while ((t = walk.nextNode())) {
      if (!/\S/.test(t.data)) continue;
      range.selectNodeContents(t);
      var tr = range.getBoundingClientRect();
      if ((tr.width || tr.height) && tr.right + sx > vw + 0.5 && reaches(t.parentElement)) hit(t.parentElement, tr.right + sx, 'text');
    }
    els.forEach(function (el) {
      ['::before', '::after'].forEach(function (p) {
        var s = cs(el, p);
        if (s.content === 'none' || s.content === 'normal' || s.display === 'none') return;
        if (s.position !== 'absolute' && s.position !== 'fixed') return;
        var cb = cbOf(el, s.position);
        if (cb === VIEWPORT || isNaN(parseFloat(s.right))) return;
        var edge = cb ? cb.getBoundingClientRect().right - parseFloat(cs(cb).borderRightWidth) + sx : vw;
        var right = edge - parseFloat(s.right) - (parseFloat(s.marginRight) || 0);
        if (right > vw + 0.5 && reaches(cb)) hit(el, right, p);
      });
    });
    // the outermost: no element around it that is past the edge reaches as far
    var shown = hits.filter(function (h) {
      for (var a = h.el.parentElement; a; a = a.parentElement) {
        var o = seen.get(a);
        if (o && o.right >= h.right - 0.5) return false;
      }
      return true;
    });
    shown.sort(function (a, b) { return a.el.compareDocumentPosition(b.el) & 4 ? -1 : 1; });
    res.more = Math.max(0, shown.length - SHOWN);
    res.over = shown.slice(0, SHOWN).map(function (h) {
      return {name: name(h.el), what: h.what, right: Math.round(h.right), width: Math.round(h.el.getBoundingClientRect().width),
              text: (h.el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 50), ctx: context(h.el)};
    });
    return res;

    function name(el) {
      var c = (el.getAttribute('class') || '').trim();
      return el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (c ? '.' + c.split(/\s+/).join('.') : '');
    }
    function context(el) {
      var names = [];
      for (var a = el.parentElement; a && a !== doc.body && names.length < 3; a = a.parentElement) {
        if (a.id || (a.getAttribute('class') || '').trim()) names.push(name(a));
      }
      return names.join(' < ');
    }
  }
})();
'''


class Handler(smoke.Handler):
    """smoke.py's server, which also answers the pages of frames this run made (server.frames), outside the prefix."""

    def do_GET(self):
        page = getattr(self.server, 'frames', {}).get(self.path)
        if page is None:
            return super().do_GET()
        data = page.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def frames_page(frames, units='mi', scripts=True):
    """The page of frames for [{'k': key, 'src': path, 'w': width, 'h': height}]: MEASURE writes what it measured into
    <pre id="reflow-out"> as JSON, {key: result}. The frames' pages start in units ('mi' or 'km', the choice base.js
    stores) and, with scripts=False, run no script (the no-script header, the pages as a failed site.js leaves them)."""
    return ('<!doctype html><meta charset="utf-8"><title>reflow</title>'
            '<style>iframe { position: absolute; top: 0; left: 0; border: 0; }</style>'
            '<pre id="reflow-out"></pre><script>var FRAMES = %s, SETTLE = %d, SHOWN = %d, UNITS = %s, SCRIPTS = %s;%s</script>'
            % (json.dumps(frames).replace('<', '\\u003c'), SETTLE, SHOWN, json.dumps(units), json.dumps(bool(scripts)),
               MEASURE))


_OUT = re.compile(r'<pre id="reflow-out">(.*?)</pre>', re.S)


def results(dom):
    """{key: result} from Chrome's dumped page of frames ({} when it wrote nothing)."""
    m = _OUT.search(dom or '')
    try:
        found = json.loads(html.unescape(m.group(1))) if m and m.group(1).strip() else {}
    except ValueError:
        return {}
    return found if isinstance(found, dict) else {}


def norm(path):
    """A page as a path under the site: '/' and 'index.html' are the home page, 'about' is 'about/'."""
    path = path.lstrip('/')
    base = re.split(r'[?#]', path, 1)[0]
    if base == 'index.html' or base.endswith('/index.html'):
        path = path[:len(base) - len('index.html')] + path[len(base):]
    elif base and not base.endswith('/') and not os.path.splitext(base)[1]:
        path = base + '/' + path[len(base):]
    return path


def page_file(site, path):
    """The file a page path is served from."""
    base = re.split(r'[?#]', path, 1)[0]
    return os.path.join(site, *(base + 'index.html' if base == '' or base.endswith('/') else base).split('/'))


def all_pages(site):
    """Every page of the build, as paths: each folder with an index.html, then 404.html (assets/ left out)."""
    out = []
    for d, dirs, files in os.walk(site):
        rel = os.path.relpath(d, site).replace(os.sep, '/')
        dirs[:] = sorted(x for x in dirs if not (rel == '.' and x == 'assets'))
        if 'index.html' in files:
            out.append('' if rel == '.' else rel + '/')
    if os.path.isfile(os.path.join(site, '404.html')):
        out.append('404.html')
    return out


def chrome_cmd(chrome, url):
    cmd = [chrome, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
           '--hide-scrollbars', '--window-size=1400,1000', '--virtual-time-budget=%d' % BUDGET, '--dump-dom', url]
    if sys.platform.startswith('linux'):
        cmd.insert(1, '--no-sandbox')       # the runner's Chrome cannot make its sandbox
    return cmd


def measure(chrome, httpd, base, batch, widths, run=subprocess.run, units='mi', scripts=True):
    """{(page, width): result or None} for one batch of pages, in one Chrome run."""
    name = '%s%d.html' % (FRAMES, len(httpd.frames))
    keys = [(p, w, '%d@%d' % (i, w)) for i, p in enumerate(batch) for w in widths]
    httpd.frames[name] = frames_page([{'k': k, 'src': '%s/%s' % (smoke.PREFIX, p), 'w': w, 'h': HEIGHTS.get(w, 667)}
                                      for p, w, k in keys], units, scripts)
    try:
        r = run(chrome_cmd(chrome, base + name), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True, timeout=TIMEOUT)
        found = results(r.stdout)
    except subprocess.TimeoutExpired:
        found = {}
    return {(p, w): found.get(k) for p, w, k in keys}


def describe(o):
    """One element past the edge: 'span.mi  right 361 (241 wide)  "SAT, JAN 17, 2026"  in span.ml < header.rep-head'."""
    what = {'': '', 'text': ' (its text)'}.get(o.get('what', ''), o.get('what', ''))
    size = ' (%d wide)' % o['width'] if o.get('what', '') in ('', 'text') else ''
    return '%s%s  right %d%s  "%s"%s' % (o['name'], what, o['right'], size, o.get('text', ''),
                                          '  in ' + o['ctx'] if o.get('ctx') else '')


def verdict(r, width, units='mi', scripts=True):
    """[] when the page fits at width, else the lines that say why (r: what the page of frames measured, or None). A
    page in other units, or whose scripts did (not) run, was not measured as asked: <html> carries km and js
    (core.PREPAINT; site.js's onerror takes both off)."""
    if r is None:
        return ['not measured: the page did not finish loading in Chrome']
    if r.get('error'):
        return ['not measured: %s' % r['error']]
    sw, cw = r['scrollWidth'], r['clientWidth']
    if cw != width:
        return ['not measured: the page is %d px wide in a %d px frame (a scrollbar?)' % (cw, width)]
    if r.get('km', False) != (units == 'km'):
        return ['not measured: the page is in %s' % ('kilometers' if r.get('km') else 'miles')]
    if r.get('js', True) != scripts:
        return ['not measured: its scripts %s (the js class on <html>)' % ('ran' if r.get('js') else 'did not run')]
    if sw <= cw:
        return []
    lines = ['%d px too wide: scrollWidth %d' % (sw - cw, sw)]
    lines += ['  ' + describe(o) for o in r.get('over') or []]
    if r.get('more'):
        lines.append('  ... and %d more' % r['more'])
    if not r.get('over'):
        lines.append('  no element found past the edge')
    return lines


def main(argv=None, which=shutil.which, run=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('site', nargs='?', default=os.path.join(ROOT, '_site'), help='the built site (default _site/)')
    which_pages = ap.add_mutually_exclusive_group()
    which_pages.add_argument('--all', action='store_true', help='every page of the build, not only PAGES')
    which_pages.add_argument('--page', action='append', metavar='PATH',
                             help='a page to check, as its path under the site (/, trips/, 404.html); repeatable')
    ap.add_argument('--width', action='append', type=int, metavar='PX',
                    help='a width to check at, in CSS pixels (default 320 and 375); repeatable')
    ap.add_argument('--km', action='store_true', help='the pages in kilometers and meters (the stored MI | KM choice)')
    ap.add_argument('--no-js', action='store_true', help='the pages without their scripts')
    a = ap.parse_args(argv)
    chrome = smoke.find_chrome(which)
    if not chrome:
        print('reflow: Chrome is not installed here; nothing was checked')
        return 0
    if not os.path.isfile(os.path.join(a.site, 'index.html')):
        print('reflow: no built site in %s (python3 tools/build.py first)' % a.site)
        return 1
    site = os.path.abspath(a.site)
    pages = all_pages(site) if a.all else [norm(p) for p in a.page] if a.page else [p for p, _w in PAGES]
    widths = a.width or list(WIDTHS)
    todo = [p for p in pages if os.path.isfile(page_file(site, p))]
    found = {}
    httpd = smoke.serve(site, Handler)
    httpd.frames = {}
    base = 'http://127.0.0.1:%d' % httpd.server_address[1]
    try:
        for i in range(0, len(todo), BATCH):
            found.update(measure(chrome, httpd, base, todo[i:i + BATCH], widths, run, 'km' if a.km else 'mi', not a.no_js))
    finally:
        httpd.shutdown()
        httpd.server_close()
    failed = 0
    for p in pages:
        if p not in todo:
            problems = ['not in the build (%s)' % os.path.relpath(page_file(site, p), site)]
        else:
            problems = []
            for w in widths:
                why = verdict(found.get((p, w)), w, 'km' if a.km else 'mi', not a.no_js)
                if why:
                    problems += ['%d px: %s' % (w, why[0])] + ['  ' + ln for ln in why[1:]]
        failed += bool(problems)
        print('%-5s %s%s' % ('FAIL' if problems else 'OK', p or '/', ''.join('\n      ' + ln for ln in problems)))
    at = ' and '.join('%d' % w for w in widths) + ' px' + (' in km' if a.km else '') + (' without scripts' if a.no_js else '')
    print('reflow: %s' % ('%d of %d pages scroll sideways or were not measured at %s' % (failed, len(pages), at) if failed
                          else 'all %d pages fit at %s' % (len(pages), at)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
