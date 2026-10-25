"""The script bundle parses (Phase 8, resilience-08). build.js_bundle() joins base.js and every page script into one
assets/site.js, so one syntax error anywhere stops the menu, the units switch, the photo viewer and every page script
at once. node --check parses the bundle as the build writes it, and each page script on its own (multiday.js and
notfound.js are in no other test). Skipped when node is not installed; the build itself never runs node."""
import glob
import importlib
import os
import shutil
import subprocess
import tempfile
import unittest

import helpers  # noqa: F401  (puts tools/ on sys.path)

build = importlib.import_module('build')
PAGES = os.path.join(build.ROOT, 'assets', 'js', 'pages')


class BundleParseTests(unittest.TestCase):

    def setUp(self):
        self.node = shutil.which('node')
        if self.node is None:
            self.skipTest('node is not installed')

    def check(self, path):
        return subprocess.run([self.node, '--check', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=60)

    def test_the_bundle_as_the_build_writes_it_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'site.js')
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(build.js_bundle())
            r = self.check(path)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_every_page_script_parses_on_its_own(self):
        scripts = [p for p in sorted(glob.glob(os.path.join(PAGES, '*.js'))) if not build.conflict_copy(p)]
        self.assertGreaterEqual(len(scripts), 8)          # explore.js and the seven page scripts
        for p in [os.path.join(build.ROOT, 'assets', 'js', 'base.js')] + scripts:
            with self.subTest(script=os.path.basename(p)):
                r = self.check(p)
                self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_syntax_error_is_caught(self):
        # the check is not vacuous: the same bundle with one broken line fails it
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'site.js')
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(build.js_bundle() + '\n(function () { var x = ;\n')
            r = self.check(path)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('SyntaxError', r.stderr)


if __name__ == '__main__':
    unittest.main()
