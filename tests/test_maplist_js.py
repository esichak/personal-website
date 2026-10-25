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

Phase 12 (maps on pages) adds, on the same stand-in: a cluster marker of a map with list rows is a named toggle button
and one of a map without rows (home) stays aria-hidden with no focus listeners (rule D4 revised); a press selects the
marker's rows, sets the rest aside and says 'N reports start here · Show all' (N counts reports, never the planned
route), and a second press, Escape or Show all clears it (qa-02); an address naming a folded row opens the list, centres
the row and focuses its link (gap4-01/02); the legend filters the rows and dims the other activities' markers, its discs
moved into the buttons (maps-07); under a matchMedia stub, a first tap on a pin picks it out, a second opens it, a tap on
the map clears, and a map without rows is left alone (gap1-03), and the years of 'All reports' fold on a phone
(phone-03); a region's full-screen map is centred on both axes (qa-06). The CSS halo of a focused journal line needs no
script and is read from base.css by tests/test_a11y_static.py. The phase's review added: the legend filter opens a folded
list and gives the fold back; the Ski panel's clusters keep their plain click; the list's own Show all / Show fewer
ends a selection; Escape from the count line's button puts the focus on the marker; a cluster of planned routes says
so; a pick ends with a tap outside the map or Escape; a phone turned past 760 px opens its years.

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
    # Phase 12: a cluster's selection (qa-02) and rule D4 revised
    ('a cluster marker names the planned route among its reports', 'base',
     r"var n = matched\.filter\(function \(r\) \{ return r\.dataset\.kind !== 'planned'; \}\)\.length;", 1, 0,
     'var n = matched.length;', 'cluster press'),
    ('the count line counts the planned route among the reports', 'base',
     r"var n = rows\.filter\(function \(r\) \{ return r\.dataset\.kind !== 'planned'; \}\)\.length;", 1, 0, 'var n = rows.length;', 'cluster press'),
    ('a cluster marker of a map without rows (home) is named and focusable', 'base',
     r"var linked = el\.classList\.contains\('mk-cluster'\) && panelList\(map\) && matched\.length;", 1, 0,
     "var linked = el.classList.contains('mk-cluster');", 'clusters'),
    ('a named cluster marker stays aria-hidden', 'base', r"el\.removeAttribute\('aria-hidden'\);", 1, 0, '', 'clusters'),
    ('a selection does not set the other rows aside', 'base',
     r"rowsFor\(map\)\.forEach\(function \(r\) \{ r\.classList\.toggle\('is-off', rows\.indexOf\(r\) === -1\); \}\);", 1, 0, '', 'both'),
    ('leaving a row clears the map instead of going back to the selection', 'base',
     r"var off = function \(\) \{ highlight\(map, \(map && map\._sel\) \|\| null\); \};", 1, 0,
     'var off = function () { highlight(map, null); };', 'cluster press'),
    ('leaving a pin clears the map instead of going back to the selection', 'base',
     r"var off = function \(\) \{ highlight\(map, map\._sel \|\| null\); markRows\(map, map\._sel \|\| null\); \};", 1, 0,
     'var off = function () { highlight(map, null); markRows(map, null); };', 'cluster press'),
    ('Escape does not clear a selection', 'base', r"if \(e\.key !== 'Escape'\) return;", 1, 0, "if (e.key !== 'Esc') return;", 'cluster press'),
    ('clearing a selection leaves its count line', 'base', r"if \(c && map\._count !== undefined\) c\.innerHTML = map\._count;", 1, 0, '',
     'cluster press'),
    # gap1-03: a tap on a touch screen
    ('a second tap on a pin is taken as well, so it never opens', 'base', r"if \(map\._tap === el\) return;", 1, 0, '', 'touch'),
    ('a tap on a pin of a map without rows is taken', 'base',
     r"\} else if \(touch && !el\.classList\.contains\('mk-cluster'\) && rowsFor\(map\)\.length\) \{", 1, 0,
     "} else if (touch && !el.classList.contains('mk-cluster')) {", 'touch'),
    # qa-06: a region's full-screen map
    ('a region\'s full-screen map is centred across only', 'base', r"fm\.scrollTop = \(fm\.scrollHeight - fm\.clientHeight\) / 2;", 1, 0, '',
     'full screen'),
    # gap4-01/02: an address naming a row
    ('an address naming a folded row does not open the list', 'archive', r"if \(btn\) btn\.click\(\);", 1, 0, '', 'landing'),
    ('an address naming a row scrolls again when its link is focused', 'archive', r"if \(a\) a\.focus\(\{ preventScroll: true \}\);", 1, 0,
     'if (a) a.focus();', 'landing'),
    # maps-07: the legend as a filter
    ('the legend counts the planned route and the journal as reports', 'archive',
     r"var reports = rows\.filter\(function \(r\) \{ return r\.dataset\.kind && r\.dataset\.kind !== 'planned'; \}\);", 1, 0,
     'var reports = rows;', 'legend'),
    ('the legend never dims a cluster marker', 'archive',
     r"c\.classList\.toggle\('is-out', !!act && \(c\.dataset\.acts \|\| ''\)\.split\(' '\)\.indexOf\(act\) === -1\);", 1, 0, '', 'legend'),
    ('the legend\'s buttons draw their words again and drop the discs', 'archive', r"while \(li\.firstChild\) b\.appendChild\(li\.firstChild\);", 1, 0,
     'b.appendChild(document.createTextNode(li.textContent));', 'legend'),
    # phone-03: the years folded on a phone
    ('the first year is folded too', 'archive', r"\.slice\(1\)\.forEach", 1, 0, '.forEach', 'year folds'),
    ('the activity filter leaves the years folded', 'archive', r"folds\.forEach\(unfold\);", 1, 0, '', 'year folds'),
    ('an address inside a year does not unfold it', 'archive', r"if \(target\) openFor\(target\.id\);", 1, 0, '', 'year folds'),
    # the phase's review
    ('the legend filter leaves the list folded', 'archive', r"ol\.classList\.remove\('arc-collapsed'\); all\.hidden = true;", 1, 0, '',
     'legend, review fix 1'),
    ('the legend filter leaves the list open when it ends', 'archive', r"ol\.classList\.toggle\('arc-collapsed', foldWas\);", 1, 0, '',
     'legend, review fix 1'),
    ('a cluster of the Ski panel is a selection button', 'base', r"panelList\(map\) && matched\.length;", 1, 0,
     'rowsFor(map).length && matched.length;', 'clusters, review fix 2'),
    ('a cluster of the Ski panel does nothing on a click', 'base', r"el\.addEventListener\('click', function \(\) \{ openRow\(matched\[0\], true\); \}\);", 1, 0, '',
     'clusters, review fix 2'),
    ('the list\'s own Show fewer keeps a selection', 'base', r"if \(map\._sel && !opening\) unselect\(map\);", 1, 0, '',
     'cluster press, review fix 5'),
    ('base.js\'s own press of Show all ends the selection it opens', 'base', r"if \(map\._sel && !opening\) unselect\(map\);", 1, 0,
     'if (map._sel) unselect(map);', 'both'),
    ('Escape leaves the focus on the body', 'base', r"if \(back\) back\.focus\(\{ preventScroll: true \}\);", 1, 0, '',
     'cluster press, review fix 6'),
    ('a cluster of planned routes says 0 reports', 'base', r"\(n \|\| rows\.length\)", 1, 0, 'n', 'cluster press, review: a cluster of planned'),
    ('a tap outside the map keeps the pick', 'base', r"if \(map\.contains\(e\.target\) && e\.target\.closest", 1, 0,
     'if (!map.contains(e.target) || e.target.closest', 'touch, review'),
    ('a tablet turned wider keeps its folds', 'archive', r"if \(!e\.matches\) unfold\(f\); ", 1, 0, '', 'year folds, review'),
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
