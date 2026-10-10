"""Phase 2: the pure functions of assets/js/pages/trips.js (norm, tokens, parseState, match, score), run under node
through tests/trips_js_harness.js. Skipped when node is not installed: node is a dev-only convenience, the production
build never runs it. norm() is held to tests/norm_cases.json, the same table test_search.py checks search.normalize
against, so a drift between the Python index and the page's query handling fails here.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
TESTS = os.path.join(ROOT, 'tests')
HARNESS = os.path.join(TESTS, 'trips_js_harness.js')
TRIPS_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'trips.js')

# a module with the right exports but wrong answers: the harness must reject it
BAD_STUB = ("module.exports = {norm: function (s) { return s; }, tokens: function () { return []; },"
            " parseState: function () { return {}; }, match: function () { return true; },"
            " score: function () { return 0; }, chipLabel: function () { return ''; }};\n")


class TripsJsTests(unittest.TestCase):

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

    def test_harness_rejects_a_module_with_wrong_answers(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        stub = os.path.join(tmp.name, 'stub.js')
        with open(stub, 'w', encoding='utf-8') as fh:
            fh.write(BAD_STUB)
        r = self.run_node(HARNESS, stub)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('FAIL norm', r.stderr)
        self.assertNotIn('checks passed', r.stdout)

    def test_trips_js_exports_for_node_before_touching_the_dom(self):
        self.assertTrue(os.path.exists(TRIPS_JS), 'assets/js/pages/trips.js is missing')
        with open(TRIPS_JS, encoding='utf-8') as fh:
            src = fh.read()
        self.assertIn('module.exports', src)
        self.assertIn('p-trips', src)
        self.assertLess(src.index('module.exports'), src.index('p-trips'))
        # the query and the index never reach innerHTML: only clearing an element with '' is tolerated
        self.assertNotRegex(src, r'\.(outerHTML|insertAdjacentHTML)\b|document\.write\b')
        for m in re.finditer(r'\.innerHTML\s*(\+?=)\s*([^;\n]*)', src):
            self.assertEqual(m.group(1), '=', m.group(0))
            self.assertIn(m.group(2).strip(), ("''", '""'), m.group(0))

    def test_pure_functions_match_the_contract(self):
        self.assertTrue(os.path.exists(TRIPS_JS), 'assets/js/pages/trips.js is missing')
        r = self.run_node(HARNESS)
        self.assertEqual(r.returncode, 0, 'node %s failed:\n%s\n%s' % (os.path.basename(HARNESS), r.stdout, r.stderr))
        self.assertIn('checks passed', r.stdout)


if __name__ == '__main__':
    unittest.main()
