"""Phase 2T: the pure functions of assets/js/pages/explore.js (norm, tokens, parseState, serialize, chipLabel) and
assets/js/pages/ticklist.js (state keys and defaults, the scope predicate, the sort comparators, chipLabel), run under node
through tests/ticklist_js_harness.js. Skipped when node is not installed: node is a dev-only convenience, the production
build never runs it. Also checks, by reading the sources, that both files export for node before touching the DOM and that
no untrusted text can reach innerHTML.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
TESTS = os.path.join(ROOT, 'tests')
HARNESS = os.path.join(TESTS, 'ticklist_js_harness.js')
EXPLORE_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'explore.js')
TICKLIST_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'ticklist.js')

# an explore module with the right exports but wrong answers: the harness must reject it
BAD_EXPLORE = ("module.exports = {norm: function (s) { return s; }, tokens: function () { return []; },"
               " parseState: function () { return {}; }, serialize: function () { return ''; }, chipLabel: function () { return ''; }};\n")


def source(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


class TickListJsTests(unittest.TestCase):

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

    def test_harness_rejects_an_explore_module_with_wrong_answers(self):
        self.assertTrue(os.path.exists(TICKLIST_JS), 'assets/js/pages/ticklist.js is missing')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        stub = os.path.join(tmp.name, 'explore.js')
        with open(stub, 'w', encoding='utf-8') as fh:
            fh.write(BAD_EXPLORE)
        r = self.run_node(HARNESS, stub, TICKLIST_JS)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('FAIL norm', r.stderr)
        self.assertNotIn('checks passed', r.stdout)

    def test_modules_export_for_node_before_touching_the_dom(self):
        for path, name in ((EXPLORE_JS, 'explore.js'), (TICKLIST_JS, 'ticklist.js')):
            with self.subTest(file=name):
                self.assertTrue(os.path.exists(path), 'assets/js/pages/%s is missing' % name)
                src = source(path)
                self.assertIn('module.exports', src)
                dom = re.search(r'\bdocument\.', src)
                if dom:
                    self.assertLess(src.index('module.exports'), dom.start(), '%s touches the DOM before exporting' % name)
        self.assertIn('window.Explore', source(EXPLORE_JS))

    def test_no_untrusted_text_reaches_inner_html(self):
        for path in (EXPLORE_JS, TICKLIST_JS):
            src = source(path)
            self.assertNotRegex(src, r'\.(outerHTML|insertAdjacentHTML)\b|document\.write\b', os.path.basename(path))
            for m in re.finditer(r'\.innerHTML\s*(\+?=)\s*([^;\n]*)', src):
                self.assertEqual(m.group(1), '=', m.group(0))
                self.assertIn(m.group(2).strip(), ("''", '""'), m.group(0))

    def test_pure_functions_match_the_contract(self):
        self.assertTrue(os.path.exists(EXPLORE_JS), 'assets/js/pages/explore.js is missing')
        self.assertTrue(os.path.exists(TICKLIST_JS), 'assets/js/pages/ticklist.js is missing')
        r = self.run_node(HARNESS)
        self.assertEqual(r.returncode, 0, 'node %s failed:\n%s\n%s' % (os.path.basename(HARNESS), r.stdout, r.stderr))
        self.assertIn('checks passed', r.stdout)


if __name__ == '__main__':
    unittest.main()
