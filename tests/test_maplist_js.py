"""Phase 5, round 3: the list beside a region map, as assets/js/base.js and assets/js/pages/archive.js drive it on the Map
page and on a region page, run under node through tests/maplist_js_harness.js against a stand-in for the page. Skipped
when node is not installed: node is a dev-only convenience, the production build never runs it. The same two changes
are also read from the sources without node (tests/test_a11y_static.py, MapListScriptTests).

What the harness plays (its header says how far a stand-in can go):

- base.js, highlight(): pointing at or focusing a list row picks out the trip's track, pin or cluster marker and dims the
  rest of the map. A region page lists what the content says, so its list has rows the map does not draw (a report
  without a track, a journal, a report newer than the last render): such a row now leaves the map as it is. Before, any
  key at all dimmed the whole map and picked out nothing.
- archive.js, the 'Show all N' button: closing the list ('Show fewer') scrolls the button, which keeps the focus, into
  view with block: 'nearest'; opening still focuses the first row that came into view and scrolls to nothing.

The harness is also run against copies of the two scripts that are wrong in one way each (WRONG: one line changed), and
has to fail each of them at the check that names the behaviour. A copy is made by changing a line the script has today;
when a script is rewritten so that the line is gone, LineTests fails and says which entry to write again, with or
without node.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
TESTS = os.path.join(ROOT, 'tests')
HARNESS = os.path.join(TESTS, 'maplist_js_harness.js')
BASE_JS = os.path.join(ROOT, 'assets', 'js', 'base.js')
ARCHIVE_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'archive.js')

DIM = r"map\.classList\.toggle\('is-hl', hit\);"
RAISE = r'hit = hit \|\| on;'
SCROLL = r"else b\.scrollIntoView\(\{ block: 'nearest' \}\);"
FOCUS = r"if \(f\) f\.focus\(\);"
# (what is wrong, the script, the line as a pattern, how often the script has it, which of them is changed, what it
#  becomes, the label the harness's failing check starts with)
WRONG = (
    ('dims the map as soon as there is a key, as before round 3', 'base', DIM, 1, 0,
     "map.classList.toggle('is-hl', keys.length > 0);", 'highlight not drawn'),
    ('dims the map whatever the keys are', 'base', DIM, 1, 0, "map.classList.toggle('is-hl', true);", 'highlight drawn'),
    ('never dims the map', 'base', DIM, 1, 0, "map.classList.toggle('is-hl', false);", 'highlight drawn'),
    ('dims the map and never lets go of it', 'base', DIM, 1, 0, "if (hit) map.classList.add('is-hl');", 'highlight drawn'),
    ('dims the map when nothing matched and not when something did', 'base', DIM, 1, 0, "map.classList.toggle('is-hl', !hit);", 'highlight drawn'),
    ('a track or a pin that matched does not count', 'base', RAISE, 2, 0, '', 'highlight drawn'),
    ('a cluster marker that matched does not count', 'base', RAISE, 2, 1, '', 'highlight drawn'),
    ('every track and pin counts, matched or not', 'base', RAISE, 2, 0, 'hit = true;', 'highlight drawn'),
    ('does not scroll when the list closes, as before round 3', 'archive', SCROLL, 1, 0, '', 'show fewer'),
    ('scrolls on every press', 'archive', SCROLL, 1, 0, "b.scrollIntoView({ block: 'nearest' });", 'show all'),
    ('scrolls when the list opens and not when it closes', 'archive', SCROLL, 1, 0,
     "if (open) b.scrollIntoView({ block: 'nearest' });", 'show all'),
    ('scrolls the button to the top of the window', 'archive', SCROLL, 1, 0, "else b.scrollIntoView({ block: 'start' });", 'show fewer'),
    ('scrolls the button with the browser\'s default, to the top', 'archive', SCROLL, 1, 0, 'else b.scrollIntoView();', 'show fewer'),
    ('scrolls to the list, not to the button', 'archive', SCROLL, 1, 0, "else ol.scrollIntoView({ block: 'nearest' });", 'show fewer'),
    ('takes the focus off the button when the list closes', 'archive', SCROLL, 1, 0,
     "else { b.scrollIntoView({ block: 'nearest' }); ol.querySelector('.arc-row a').focus(); }", 'show fewer'),
    ('focuses nothing when the list opens', 'archive', FOCUS, 1, 0, '', 'show all'),
    ('focuses the first row of the list, not the first new one', 'archive', r"ol\.querySelector\('\.arc-more a'\)", 1, 0,
     "ol.querySelector('.arc-row a')", 'show all'),
)
PATHS = {'base': BASE_JS, 'archive': ARCHIVE_JS}


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def wrong_copy(src, pattern, which, becomes):
    """The script with the `which`-th line that matches the pattern replaced."""
    hits = list(re.finditer(pattern, src))
    m = hits[which]
    return src[:m.start()] + becomes + src[m.end():]


class LineTests(unittest.TestCase):
    """The lines the wrong copies are made from are in the scripts as written here. Needs no node."""

    def test_each_script_has_the_lines_the_wrong_copies_change(self):
        for what, script, pattern, count, which, becomes, _label in WRONG:
            with self.subTest(wrong=what):
                src = read(PATHS[script])
                self.assertEqual(len(re.findall(pattern, src)), count,
                                 '%s no longer has the line /%s/ %d time(s): write this entry of WRONG again for the script as it is now'
                                 % (os.path.basename(PATHS[script]), pattern, count))
                self.assertLess(which, count)
                self.assertNotEqual(wrong_copy(src, pattern, which, becomes), src)

    def test_every_entry_is_wrong_in_its_own_way(self):
        copies = [(script, wrong_copy(read(PATHS[script]), pattern, which, becomes)) for _w, script, pattern, _c, which, becomes, _l in WRONG]
        self.assertEqual(len(set(copies)), len(WRONG))
        self.assertEqual(len({what for what, *_rest in WRONG}), len(WRONG))


class MapListJsTests(unittest.TestCase):

    def setUp(self):
        self.node = shutil.which('node')
        if self.node is None:
            self.skipTest('node is not installed')

    def run_node(self, *args):
        return subprocess.run([self.node] + list(args), cwd=TESTS, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=60)

    def test_harness_is_valid_javascript(self):
        r = self.run_node('--check', HARNESS)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_the_two_scripts_do_what_the_harness_plays(self):
        r = self.run_node(HARNESS)
        self.assertEqual(r.returncode, 0, 'node %s failed:\n%s\n%s' % (os.path.basename(HARNESS), r.stdout, r.stderr))
        self.assertRegex(r.stdout, r'^\d+ checks passed\n$')
        self.assertNotIn('FAIL', r.stderr)
        # ... and the same when the paths are given, as the wrong copies are
        again = self.run_node(HARNESS, BASE_JS, ARCHIVE_JS)
        self.assertEqual((again.returncode, again.stdout), (0, r.stdout))

    def test_harness_rejects_a_script_that_is_wrong_in_one_line(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for n, (what, script, pattern, _count, which, becomes, label) in enumerate(WRONG):
            with self.subTest(wrong=what):
                copy = os.path.join(tmp.name, '%s_%d.js' % (script, n))
                with open(copy, 'w', encoding='utf-8') as fh:
                    fh.write(wrong_copy(read(PATHS[script]), pattern, which, becomes))
                args = (copy, ARCHIVE_JS) if script == 'base' else (BASE_JS, copy)
                r = self.run_node(HARNESS, *args)
                self.assertNotEqual(r.returncode, 0, 'the harness passed a %s.js that %s' % (script, what))
                # the check that names the behaviour is the first to fail (a copy that is no longer JavaScript would
                # stop node before any check, with the file's name first)
                self.assertTrue(r.stderr.startswith('FAIL ' + label), r.stderr[:400])
                self.assertNotIn('checks passed', r.stdout)

    def test_harness_rejects_scripts_that_wire_nothing(self):
        # an empty base.js highlights nothing and dims nothing: every 'leaves the map as it is' check would pass on it,
        # so the harness first looks for the listeners on the rows
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        empty = os.path.join(tmp.name, 'empty.js')
        with open(empty, 'w', encoding='utf-8') as fh:
            fh.write("(function () { 'use strict'; })();\n")
        r = self.run_node(HARNESS, empty, ARCHIVE_JS)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(r.stderr.startswith('FAIL fixture'), r.stderr[:400])
        r = self.run_node(HARNESS, BASE_JS, empty)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(r.stderr.startswith('FAIL show all'), r.stderr[:400])


if __name__ == '__main__':
    unittest.main()
