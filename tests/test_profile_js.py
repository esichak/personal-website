"""maps-04: the readout on the elevation profile of a single-day report, as assets/js/pages/profile.js draws it, run
under node through tests/profile_js_harness.js against the stand-in for the browser (tests/page_standin.js). Skipped when
node is not installed: node is a dev-only convenience, the production build never runs it.

What the harness plays (its header says how far the stand-in goes): a pointer on a .cv of a .chart[data-pf] picks the
sample nearest to it on the profile's axis (data-w, data-pad; both ends held) and shows a 1px crosshair and a label,
'7.2 MI · 11,650 FT' or '11.6 KM · 3,551 M' under html.km, kept inside the .cv; a finger or a pen does the same;
pointerleave, pointercancel and Escape hide it; a malformed data-pf throws nothing and leaves its chart without a
readout; a page without data-pf gets nothing.

The harness is also run against copies of the script that are wrong in one way each (WRONG: one line changed), and has
to fail each of them at the check that names the behaviour. A copy is made by changing a line the script has today;
when the script is rewritten so that the line is gone, LineTests fails and says which entry to write again, with or
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
HARNESS = os.path.join(TESTS, 'profile_js_harness.js')
PROFILE_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'profile.js')

FRACTION = r"var f = Math\.min\(1, Math\.max\(0, \(\(e\.clientX - r\.left\) \* w / r\.width - pad\) / \(w - pad\)\)\);"
SAMPLE = r"pf\[Math\.round\(f \* n\)\]"
UNITS = r"if \(document\.documentElement\.classList\.contains\('km'\)\) "
SEP = r"return \(n < 0 \? '-' : ''\) \+ s \+ out;"
CROSS = r"x\.style\.left = Math\.max\(0, Math\.min\(r\.width - 1, Math\.floor\(px\)\)\) \+ 'px';"
LABEL = r"l\.style\.left = Math\.max\(0, Math\.min\(Math\.floor\(r\.width - lw\), Math\.round\(px - lw / 2\)\)\) \+ 'px';"
SHOW = r"x\.hidden = l\.hidden = false;"
RECT = r"var r = cv\.getBoundingClientRect\(\);"
ESCAPE = r"if \(e\.key === 'Escape'\) "
PARSE = r"try \{ pf = JSON\.parse\(chart\.dataset\.pf\); \} catch \(e\) \{ /\* not JSON: no readout \*/ \}"
VALID = r"if \(!Array\.isArray\(pf\) \|\| !pf\.length \|\| !pf\.every\(isNum\) \|\| !\(total >= 0\)\) return;"
# (what is wrong, the line as a pattern, how often the script has it, which of them is changed, what it becomes, the
#  label the harness's failing check starts with)
WRONG = (
    ('never shows the readout', SHOW, 1, 0, '', 'labels'),
    ('ignores the units switch', UNITS, 1, 0, 'if (false) ', 'labels'),
    ('shows km and metres whatever the switch says', UNITS, 1, 0, '', 'labels'),
    ('writes no thousands separators', SEP, 1, 0, 'return String(n);', 'labels'),
    ('gives metres for feet', r"sep\(Math\.round\(m \* 3\.28084\)\)", 1, 0, 'sep(Math.round(m))', 'labels'),
    ('ignores the padding left of the axis', FRACTION, 1, 0,
     'var f = Math.min(1, Math.max(0, ((e.clientX - r.left) * w / r.width) / w));', 'mapping'),
    ('ignores the rect being scaled from the viewBox', FRACTION, 1, 0,
     'var f = Math.min(1, Math.max(0, ((e.clientX - r.left) - pad) / (w - pad)));', 'mapping'),
    ('draws the crosshair at the pointer outside the axis too', CROSS, 1, 0, "x.style.left = Math.floor(e.clientX - r.left) + 'px';",
     'clamped ends'),
    ('takes the sample below, not the nearest', SAMPLE, 1, 0, 'pf[Math.floor(f * n)]', 'nearest sample'),
    ('takes N + 1 for the number of steps', r"var n = pf\.length - 1;", 1, 0, 'var n = pf.length;', 'labels'),
    ('does not hold the ends', FRACTION, 1, 0, 'var f = ((e.clientX - r.left) * w / r.width - pad) / (w - pad);', 'clamped ends'),
    ('lets the label run out of the chart', LABEL, 1, 0, "l.style.left = Math.round(px - lw / 2) + 'px';", 'label clamp'),
    ('starts the label at the crosshair', LABEL, 1, 0, "l.style.left = Math.max(0, Math.min(Math.floor(r.width - lw), Math.round(px))) + 'px';",
     'label clamp'),
    ('ignores a finger', RECT, 1, 0, "if (e.pointerType === 'touch') return; var r = cv.getBoundingClientRect();", 'touch'),
    ('stays when the pointer leaves', r"cv\.addEventListener\('pointerleave', hide\);", 1, 0, '', 'hide'),
    ('stays when the browser cancels the pointer', r"cv\.addEventListener\('pointercancel', hide\);", 1, 0, '', 'hide'),
    ('hides on any key', ESCAPE, 1, 0, '', 'hide'),
    ('stays on Escape', ESCAPE, 1, 0, "if (e.key === 'Esc') ", 'hide'),
    ('reads a chart that is not displayed', r"if \(!\(r\.width > 0\)\) return;", 1, 0, '', 'no width'),
    ('throws on data-pf that is not JSON', PARSE, 1, 0, 'pf = JSON.parse(chart.dataset.pf);', 'malformed'),
    ('takes any JSON for an array', VALID, 1, 0, 'if (!pf || !pf.length || !pf.every(isNum) || !(total >= 0)) return;', 'malformed'),
    ('takes elevations that are not numbers', VALID, 1, 0, 'if (!Array.isArray(pf) || !pf.length || !(total >= 0)) return;', 'malformed'),
    ('listens for Escape on a page without a readout', r"if \(hides\.length\) \{", 1, 0, 'if (true) {', 'malformed'),
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
        src = read(PROFILE_JS)
        for what, pattern, count, which, becomes, _label in WRONG:
            with self.subTest(wrong=what):
                self.assertEqual(len(re.findall(pattern, src)), count,
                                 'profile.js no longer has the line /%s/ %d time(s): write this entry of WRONG again for the script as it is now'
                                 % (pattern, count))
                self.assertLess(which, count)
                self.assertNotEqual(wrong_copy(src, pattern, which, becomes), src)

    def test_every_entry_is_wrong_in_its_own_way(self):
        src = read(PROFILE_JS)
        copies = [wrong_copy(src, pattern, which, becomes) for _w, pattern, _c, which, becomes, _l in WRONG]
        self.assertEqual(len(set(copies)), len(WRONG))
        self.assertEqual(len({what for what, *_rest in WRONG}), len(WRONG))


class ProfileJsTests(unittest.TestCase):

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

    def test_the_script_does_what_the_harness_plays(self):
        r = self.run_node(HARNESS)
        self.assertEqual(r.returncode, 0, 'node %s failed:\n%s\n%s' % (os.path.basename(HARNESS), r.stdout, r.stderr))
        self.assertRegex(r.stdout, r'^\d+ checks passed\n$')
        self.assertNotIn('FAIL', r.stderr)
        # ... and the same when the path is given, as the wrong copies are
        again = self.run_node(HARNESS, PROFILE_JS)
        self.assertEqual((again.returncode, again.stdout), (0, r.stdout))

    def test_harness_rejects_a_script_that_is_wrong_in_one_line(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        src = read(PROFILE_JS)
        for n, (what, pattern, _count, which, becomes, label) in enumerate(WRONG):
            with self.subTest(wrong=what):
                copy = os.path.join(tmp.name, 'profile_%d.js' % n)
                with open(copy, 'w', encoding='utf-8') as fh:
                    fh.write(wrong_copy(src, pattern, which, becomes))
                r = self.run_node(HARNESS, copy)
                self.assertNotEqual(r.returncode, 0, 'the harness passed a profile.js that %s' % what)
                # the check that names the behaviour is the first to fail (a copy that is no longer JavaScript would
                # fail the fixture before any other check)
                self.assertTrue(r.stderr.startswith('FAIL ' + label), r.stderr[:400])
                self.assertNotIn('checks passed', r.stdout)

    def test_harness_rejects_a_script_that_wires_nothing(self):
        # an empty script shows nothing and so hides everything: every 'hidden' and 'left alone' check would pass on it,
        # so the harness first looks for the readout and the listeners on each .cv
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        empty = os.path.join(tmp.name, 'empty.js')
        with open(empty, 'w', encoding='utf-8') as fh:
            fh.write("(function () { 'use strict'; })();\n")
        r = self.run_node(HARNESS, empty)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(r.stderr.startswith('FAIL fixture'), r.stderr[:400])

    def test_harness_rejects_a_script_that_throws(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        broken = os.path.join(tmp.name, 'broken.js')
        with open(broken, 'w', encoding='utf-8') as fh:
            fh.write(read(PROFILE_JS).replace("var hides = [];", "var hides = []; null.x;", 1))
        r = self.run_node(HARNESS, broken)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(r.stderr.startswith('FAIL fixture: the script runs'), r.stderr[:400])


if __name__ == '__main__':
    unittest.main()
