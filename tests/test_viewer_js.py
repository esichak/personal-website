"""Phase 11: the photo viewer and the copy-link control of assets/js/base.js, run under node through
tests/viewer_js_harness.js against the stand-in for the browser (tests/page_standin.js). Skipped when node is not
installed: node is a dev-only convenience, the production build never runs it.

What the harness plays (its header says how far the stand-in goes), on a page assembled here from markup the site
generator writes (page_model):

- resilience-10: opening the viewer adds one history entry ({lb: true}, the page's own address); Back (popstate) closes
  it and goes back no further; the Close button, Escape (the dialog's cancel and close) and a tap outside take the entry
  back off with history.back(), once, and never over-pop: not after Back closed the viewer, not when pushState was
  refused. A photo that does not load says 'This photo could not be loaded', marks the dialog lb--error and shows the
  file link ('Open the file', the photo's href); moving to another photo takes all three back.
- a11y-14: opening says 'Photo 1 of N. <alt>' in #lb-live once the dialog is up; moving says the photo moved to.
- gap1-07: a second finger is no swipe, pointercancel ends one, a primary swipe of more than 40 px still moves, a tap
  outside still closes.
- the journal's capped srcset (.th and .sm) gets the file at the thumbnail's width in the viewer; a full set is passed as
  it is.
- phone-06: under (hover: none) with navigator.share each control reads its data-share ('Share this page' on the report's
  share row) and a press calls navigator.share inside the click, after navigator.canShare when there is one, with the
  clipboard path as the fallback (not after AbortError); with (hover: hover), without navigator.share or without
  matchMedia nothing is relabelled and the desktop copy-link path is as it was: 'Link copied' for 4 s, or the field to
  copy by hand.

The harness is also run against copies of base.js that are wrong in one way each (WRONG: one line changed), and has to
fail each of them at the check that names the behaviour. A copy is made by changing a line the script has today; when
the script is rewritten so that the line is gone, LineTests fails and says which entry to write again, with or without
node.

By hand: `python3 tests/test_viewer_js.py --model` prints the page the harness plays on (the harness asks for it this
way when it is run without one).
"""
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
TESTS = os.path.join(ROOT, 'tests')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
from sitegen import core  # noqa: E402

from helpers import Doc  # noqa: E402
from js_fixtures import tree  # noqa: E402

HARNESS = os.path.join(TESTS, 'viewer_js_harness.js')
BASE_JS = os.path.join(ROOT, 'assets', 'js', 'base.js')

PAGE = 'trips/syn-viewer-journal/'
TITLE = 'Synthetic Viewer Journal · %s' % core.SITE_NAME


def _photo(stem, w, h, alt, caption=None):
    """A photo as content.py hands it to the pages: the file, its .sm and .th copies, its size, alt text, caption."""
    p = {'file': 'photos/%s.webp' % stem, 'sm': 'photos/%s.sm.webp' % stem, 'th': 'photos/%s.th.webp' % stem,
         'w': w, 'h': h, 'alt': alt}
    if caption:
        p['caption'] = caption
    return p


def page_model():
    """The page tests/viewer_js_harness.js plays on: the address it is served at, its title, its <body> as a tree.
    Every part is the generator's own markup for a synthetic trip: a written journal day's photos (series.day_photos:
    the capped .th/.sm set, full=False) with the entry's copy control as series.written_nav writes it, a track-only day's
    contact sheet (series.thumbs: no width-described set), a report's photo rows (core.photo_rows: the full set) in a
    section that carries data-lb-group as the report's does, the title block's copy control (core.copy_link(url)), the
    report's phone share row (core.copy_link(url, 'Copy link to this page', cls='alink')) and the viewer
    (core.lightbox()). The wrapping elements are written here; no page of the site has all of these at once."""
    series = importlib.import_module('sitegen.pages.series')
    here = PAGE
    t = {'url': PAGE, 'dir': os.path.join(TESTS, 'no-such-folder')}     # no .th copy on disk: the sheet takes the .sm
    day3 = {'id': '003', 'label': '3', 'body_md': 'A written day.', 'photos': [
        _photo('d003-01', 1600, 1200, 'Tents by a synthetic lake', 'Camp at the synthetic lake'),
        _photo('d003-02', 1200, 1600, 'A synthetic pass'),
        _photo('d003-03', 1200, 1600, 'Snow on a synthetic ridge')]}
    day4 = {'id': '004', 'label': '4', 'body_md': '', 'photos': [
        _photo('d004-01', 1600, 1200, 'A synthetic meadow'),
        _photo('d004-02', 1600, 1200, 'A synthetic creek')]}
    report = [_photo('r-01', 1600, 1067, 'A synthetic summit'), _photo('r-02', 1200, 1600, 'A synthetic couloir', 'Looking down')]
    url = core.SITE_URL + PAGE
    body = ('<body class="p-series"><main id="main">'
            '<header class="ser-head"><h1>Synthetic Viewer Journal</h1><div class="ser-acts">%s</div></header>'
            '<article class="ser-day" id="day-3"><h2>Day 3</h2>%s<div class="ser-wnav">%s</div></article>'
            '<article class="ser-day" id="day-4"><h2>Day 4</h2>%s</article>'
            '<section class="rep-photos wrap sec" id="photos" data-lb-group="photos"><h2>Photos</h2>%s</section>'
            '<div class="wrap rep-share">%s</div>'
            '</main>%s</body>'
            % (core.copy_link(url),
               series.day_photos(t, day3, here),
               core.copy_link(url + '#day-3', 'Copy link to this entry', cls='alink', of='Day 3', share='Share this entry'),
               series.thumbs(t, day4, here),
               core.photo_rows(t, here, report),
               core.copy_link(url, 'Copy link to this page', cls='alink'),
               core.lightbox()))
    doc = Doc(body)
    return {'pathname': '/personal-website/' + PAGE, 'title': TITLE, 'body': tree(doc.find('body'))}


PUSH = r"try \{ history\.pushState\(\{ lb: true \}, ''\); pushed = true; \} catch \(err\) \{ pushed = false; /\* file:// or a sandbox \*/ \}"
POP = r"if \(lb\.open\) \{ popping = true; lb\.close\(\); \}"
BACK = r"if \(pushed && !popping && history\.state && history\.state\.lb\) \{"
FILE_ON = r"if \(lbFile\) \{ lbFile\.href = group\[at\]\.getAttribute\('href'\); lbFile\.hidden = false; \}"
FILE_OFF = r"if \(lbFile\) \{ lbFile\.hidden = true; lbFile\.removeAttribute\('href'\); \}"
SWIPE = r"if \(Math\.abs\(dx\) > 40\) \{"
TAP = r"if \(e\.target === lb && !swiped\) lb\.close\(\);"
APPEND = r"if \(fw && ss\.indexOf\(a\.getAttribute\('href'\) \+ ' '\) === -1\) ss \+= ', ' \+ a\.getAttribute\('href'\) \+ ' ' \+ fw \+ 'w';"
SHEET = r"try \{ canSheet = !!\(navigator\.share && window\.matchMedia && window\.matchMedia\('\(hover: none\)'\)\.matches\); \}"
RELABEL = r"if \(l\) l\.textContent = b\.getAttribute\('data-share'\);"
IS_SHARE = r"if \(b\.classList\.contains\('is-share'\)\) \{"
DATA = r"var data = \{ title: document\.title, url: url \}, ok = false;"
SHARE = (r"navigator\.share\(data\)\.then\(null, function \(err\) \{ if \(!err \|\| err\.name !== 'AbortError'\) "
         r"copyPath\(b, box, url, msg\); \}\);")
# (what is wrong, the line as a pattern, how often the script has it, which of them is changed, what it becomes, the
#  label the harness's failing check starts with)
WRONG = (
    ('never pushes an entry', PUSH, 1, 0, 'pushed = false;', 'pushState on open'),
    ('pushes an entry without its state', PUSH, 1, 0, "try { history.pushState(null, ''); pushed = true; } catch (err) { pushed = false; }",
     'pushState on open'),
    ('pushes an entry with an address of its own', PUSH, 1, 0,
     "try { history.pushState({ lb: true }, '', '#photo'); pushed = true; } catch (err) { pushed = false; }", 'pushState on open'),
    ('lets a refused pushState throw', PUSH, 1, 0, "history.pushState({ lb: true }, ''); pushed = true;", 'no over-popping'),
    ('stays open on Back', POP, 1, 0, '', 'popstate closing'),
    ('goes back on every close, after Back too', BACK, 1, 0, 'if (true) {', 'popstate closing'),
    ("trusts the entry's state alone", BACK, 1, 0, 'if (history.state && history.state.lb) {', 'popstate closing'),
    ('never goes back on close', BACK, 1, 0, 'if (false) {', 'close button'),
    ('never marks the error', r"lb\.classList\.add\('lb--error'\);", 1, 0, '', 'error state'),
    ('keeps the error mark on the next photo', r"lb\.classList\.remove\('lb--error'\);", 1, 0, '', 'error state'),
    ('does not say the photo failed', r"lbCap\.textContent = 'This photo could not be loaded';", 1, 0, '', 'error state'),
    ('offers no file', FILE_ON, 1, 0, '', 'error state'),
    ('offers the file without its address', FILE_ON, 1, 0, 'if (lbFile) { lbFile.hidden = false; }', 'error state'),
    ("offers the first photo's file", FILE_ON, 1, 0, "if (lbFile) { lbFile.href = group[0].getAttribute('href'); lbFile.hidden = false; }",
     'error state'),
    ('keeps the file link on the next photo', FILE_OFF, 1, 0, '', 'error state'),
    ('reacts to an error while closed', r"if \(!lb\.open \|\| !group\[at\]\) return;", 1, 0, 'if (!group[at]) return;', 'error state'),
    ('announces nothing on open', r"lbClose\.focus\(\);\n      say\(\);", 1, 0, 'lbClose.focus();', 'announce'),
    ('announces before the viewer is up', r"show\(group\.indexOf\(a\)\);", 1, 0, 'show(group.indexOf(a), true);', 'announce'),
    ('announces without the alt text', r"'\. ' \+ lbImg\.alt;", 1, 0, "'.';", 'announce'),
    ('counts the photos from 0', r"'Photo ' \+ \(at \+ 1\) \+ ' of ' \+ group\.length \+ '\. '", 1, 0,
     "'Photo ' + at + ' of ' + group.length + '. '", 'announce'),
    ('keeps a leftover viewer entry', r"try \{ if \(history\.state && history\.state\.lb\) history\.replaceState\(null, ''\); \} catch \(err\) \{ /\* sandboxed \*/ \}",
     1, 0, '', 'history'),
    ('does not announce the failure', r"if \(lbLive\) lbLive\.textContent = 'Photo ' \+ \(at \+ 1\) \+ ' of ' \+ group\.length \+ ' could not be loaded';",
     1, 0, '', 'error state'),
    ('swipes with any pointer', r"if \(!e\.isPrimary\) return; sx = e\.clientX;", 1, 0, 'sx = e.clientX;', 'pointers'),
    ('ends a swipe with any pointer', r"if \(!e\.isPrimary \|\| sx === null\) return;", 1, 0, 'if (sx === null) return;', 'pointers'),
    ('keeps a cancelled swipe', r"lb\.addEventListener\('pointercancel', function \(\) \{ sx = null; \}\);", 1, 0, '', 'pointers'),
    ('never swipes', SWIPE, 1, 0, 'if (false) {', 'pointers'),
    ('takes 40 px for a swipe', SWIPE, 1, 0, 'if (Math.abs(dx) >= 40) {', 'pointers'),
    ('closes on the click after a swipe', TAP, 1, 0, 'if (e.target === lb) lb.close();', 'pointers'),
    ('never closes on a tap outside', TAP, 1, 0, 'if (false) lb.close();', 'tap outside'),
    ('appends the file to every set', APPEND, 1, 0, "if (fw) ss += ', ' + a.getAttribute('href') + ' ' + fw + 'w';", 'srcset'),
    ('never gives the file back', APPEND, 1, 0, '', 'srcset'),
    ('gives the file back at the landscape width', APPEND, 1, 0,
     "if (fw && ss.indexOf(a.getAttribute('href') + ' ') === -1) ss += ', ' + a.getAttribute('href') + ' 1600w';", 'srcset'),
    ("writes the set into the thumbnail", r"lbImg\.setAttribute\('srcset', ss\);", 1, 0,
     "lbImg.setAttribute('srcset', ss); th.setAttribute('srcset', ss);", 'srcset'),
    ('relabels on any device with a share sheet', SHEET, 1, 0, 'try { canSheet = !!navigator.share; }', 'desktop copy'),
    ('relabels any touch screen, share sheet or not', SHEET, 1, 0,
     "try { canSheet = !!(window.matchMedia && window.matchMedia('(hover: none)').matches); }", 'desktop copy'),
    ('relabels nothing', RELABEL, 1, 0, '', 'share'),
    ("relabels with words of its own", RELABEL, 1, 0, "if (l) l.textContent = 'Share';", 'share'),
    ('never opens the sheet', IS_SHARE, 1, 0, 'if (false) {', 'share'),
    ('opens the sheet on a desktop that has navigator.share', IS_SHARE, 1, 0, 'if (navigator.share) {', 'desktop copy'),
    ("shares the page's path, not the control's URL", DATA, 1, 0,
     'var data = { title: document.title, url: window.location.pathname }, ok = false;', 'share'),
    ('shares without a title', DATA, 1, 0, 'var data = { url: url }, ok = false;', 'share'),
    ('ignores canShare', r"try \{ ok = !navigator\.canShare \|\| navigator\.canShare\(data\); \}", 1, 0, 'try { ok = true; }', 'share'),
    ('shares after the press, not inside it', SHARE, 1, 0,
     "window.setTimeout(function () { navigator.share(data).then(null, function (err) {"
     " if (!err || err.name !== 'AbortError') copyPath(b, box, url, msg); }); }, 0);", 'share'),
    ('copies after a dismissed sheet', SHARE, 1, 0, 'navigator.share(data).then(null, function () { copyPath(b, box, url, msg); });', 'share'),
    ('stops after a refused sheet', SHARE, 1, 0, 'navigator.share(data).then(null, function () {});', 'share'),
    ('falls back only after an error that has a name', SHARE, 1, 0,
     "navigator.share(data).then(null, function (err) { if (err && err.name !== 'AbortError') copyPath(b, box, url, msg); });", 'share'),
    ('loses the press when the sheet throws', r"\} catch \(err\) \{ copyPath\(b, box, url, msg\); \}", 1, 0,
     '} catch (err) { /* nothing */ }', 'share'),
    ('copies as well as sharing', r"(?<=copyPath\(b, box, url, msg\); \}\n)        return;\n", 1, 0, '', 'share'),
    # the share sheet's fallback is the same clipboard path, and its checks come first
    ('says Link copied for ever', r"msg\._t = window\.setTimeout\(function \(\) \{ msg\.textContent = ''; \}, 4000\);", 1, 0, '',
     'share'),
    ('says Link copied when the clipboard refused', r"navigator\.clipboard\.writeText\(url\)\.then\(done, byHand\);", 1, 0,
     'navigator.clipboard.writeText(url).then(done, done);', 'desktop copy'),
)


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def wrong_copy(src, pattern, which, becomes):
    """The script with the `which`-th line that matches the pattern replaced."""
    hits = list(re.finditer(pattern, src))
    m = hits[which]
    return src[:m.start()] + becomes + src[m.end():]


class LineTests(unittest.TestCase):
    """The lines the wrong copies are made from are in the script as written here. Needs no node."""

    def test_the_script_has_the_lines_the_wrong_copies_change(self):
        src = read(BASE_JS)
        for what, pattern, count, which, becomes, _label in WRONG:
            with self.subTest(wrong=what):
                self.assertEqual(len(re.findall(pattern, src)), count,
                                 'base.js no longer has the line /%s/ %d time(s): write this entry of WRONG again for the script as it is now'
                                 % (pattern, count))
                self.assertLess(which, count)
                self.assertNotEqual(wrong_copy(src, pattern, which, becomes), src)

    def test_every_entry_is_wrong_in_its_own_way(self):
        src = read(BASE_JS)
        copies = [wrong_copy(src, pattern, which, becomes) for _w, pattern, _c, which, becomes, _l in WRONG]
        self.assertEqual(len(set(copies)), len(WRONG))
        self.assertEqual(len({what for what, *_rest in WRONG}), len(WRONG))


class ModelTests(unittest.TestCase):
    """The page is the generator's markup. Needs no node."""

    @classmethod
    def setUpClass(cls):
        cls.model = page_model()
        cls.html = json.dumps(cls.model['body'])

    @staticmethod
    def walk(node):
        for c in node['children']:
            if isinstance(c, dict):
                yield c
                for d in ModelTests.walk(c):
                    yield d

    def find(self, tag, cls_):
        return [n for n in self.walk(self.model['body']) if n['tag'] == tag and cls_ in (n['attrs'].get('class') or '').split()]

    def test_the_viewer_and_the_copy_controls_are_the_generators(self):
        lb = self.find('dialog', 'lb')
        self.assertEqual(len(lb), 1)
        self.assertEqual(lb[0], tree(Doc(core.lightbox()).find('dialog')))
        buttons = self.find('button', 'copy-btn')
        self.assertEqual([(b['attrs']['data-share'], b['attrs']['data-copy']) for b in buttons], [
            ('Share', core.SITE_URL + PAGE),
            ('Share this entry', core.SITE_URL + PAGE + '#day-3'),
            ('Share this page', core.SITE_URL + PAGE)])

    def test_the_photo_sets_are_the_ones_the_harness_names(self):
        # the journal's set stops at the .sm copy; the report's holds the file; the sheet's thumbnails have none
        kinds = []
        for a in self.find('a', 'jph') + self.find('a', 'ser-ph'):
            href = a['attrs']['href']
            img = [n for n in self.walk(a) if n['tag'] == 'img']
            self.assertEqual(len(img), 1, href)
            ss = img[0]['attrs'].get('srcset')
            if '/d003-' in href:
                kinds.append('capped')
                self.assertRegex(ss, r'\.th\.webp \d+w, \S+\.sm\.webp \d+w$')
                self.assertNotIn(href + ' ', ss)
            elif '/r-' in href:
                kinds.append('full')
                self.assertIn(href + ' ', ss)
            else:
                kinds.append('none')
                self.assertIsNone(ss)
        self.assertEqual(sorted(kinds), ['capped'] * 3 + ['full'] * 2 + ['none'] * 2)


class ViewerJsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.model_path = os.path.join(cls.tmp.name, 'page.json')
        with open(cls.model_path, 'w', encoding='utf-8') as fh:
            json.dump(page_model(), fh)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.node = shutil.which('node')
        if self.node is None:
            self.skipTest('node is not installed')

    def run_node(self, *args):
        env = dict(os.environ, PYTHON=sys.executable)        # a harness run without a page asks this interpreter for one
        return subprocess.run([self.node] + list(args), cwd=TESTS, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=120, env=env)

    def test_harness_is_valid_javascript(self):
        r = self.run_node('--check', HARNESS)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_the_script_does_what_the_harness_plays(self):
        r = self.run_node(HARNESS, BASE_JS, self.model_path)
        self.assertEqual(r.returncode, 0, 'node %s failed:\n%s\n%s' % (os.path.basename(HARNESS), r.stdout, r.stderr))
        self.assertRegex(r.stdout, r'^\d+ checks passed\n$')
        self.assertNotIn('FAIL', r.stderr)
        # ... and the same by hand, when the harness asks for the page itself
        again = self.run_node(HARNESS)
        self.assertEqual((again.returncode, again.stdout), (0, r.stdout), again.stderr[-2000:])

    def test_harness_rejects_a_script_that_is_wrong_in_one_line(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        src = read(BASE_JS)
        for n, (what, pattern, _count, which, becomes, label) in enumerate(WRONG):
            with self.subTest(wrong=what):
                copy = os.path.join(tmp.name, 'base_%d.js' % n)
                with open(copy, 'w', encoding='utf-8') as fh:
                    fh.write(wrong_copy(src, pattern, which, becomes))
                r = self.run_node(HARNESS, copy, self.model_path)
                self.assertNotEqual(r.returncode, 0, 'the harness passed a base.js that %s' % what)
                # the check that names the behaviour is the first to fail (a copy that is no longer JavaScript would
                # fail the fixture before any other check)
                self.assertTrue(r.stderr.startswith('FAIL ' + label), r.stderr[:400])
                self.assertNotIn('checks passed', r.stdout)

    def test_harness_rejects_a_script_that_wires_nothing(self):
        # an empty script opens nothing and so closes nothing and goes back nowhere: every 'goes no further' check would
        # pass on it, so the fixture first opens the viewer and copies a link
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        empty = os.path.join(tmp.name, 'empty.js')
        with open(empty, 'w', encoding='utf-8') as fh:
            fh.write("(function () { 'use strict'; })();\n")
        r = self.run_node(HARNESS, empty, self.model_path)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(r.stderr.startswith('FAIL fixture'), r.stderr[:400])

    def test_harness_rejects_a_script_that_throws(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        broken = os.path.join(tmp.name, 'broken.js')
        src = read(BASE_JS)
        self.assertEqual(src.count("var group = [], at = 0, opener = null;"), 1)
        with open(broken, 'w', encoding='utf-8') as fh:
            fh.write(src.replace("var group = [], at = 0, opener = null;", "var group = [], at = 0, opener = null; null.x;", 1))
        r = self.run_node(HARNESS, broken, self.model_path)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(r.stderr.startswith('FAIL fixture: base.js runs'), r.stderr[:400])


if __name__ == '__main__':
    if sys.argv[1:] == ['--model']:
        json.dump(page_model(), sys.stdout)
    else:
        unittest.main()
