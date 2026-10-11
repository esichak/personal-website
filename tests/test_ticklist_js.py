"""Phase 2T: the pure functions of assets/js/pages/explore.js (norm, tokens, parseState, serialize, chipLabel) and
assets/js/pages/ticklist.js (state keys and defaults, the scope predicate, the sort comparators, chipLabel), run under node
through tests/ticklist_js_harness.js. Skipped when node is not installed: node is a dev-only convenience, the production
build never runs it. Also checks, by reading the sources, that both files export for node before touching the DOM and that
no untrusted text can reach innerHTML. Phase 4 adds goalShown, the predicate a goal card is shown by: the harness is
also run against the real module with one filter switched off at a time, and must fail. It also adds adoptForm (what
the page takes over from a form the visitor used before the script arrived): the harness is run against the real
module with adoptForm wrong in one way at a time, and the page's own lines that call it are read from the source.
"""
import json
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


# the real ticklist module with its predicate wrapped: one key of the state is put back to its unset value before
# asking ('scope': every goal is in scope), or the search tokens are dropped
IGNORING = ("var real = require(%(module)s);\n"
            "var patch = {}; patch[%(key)s] = %(unset)s;\n"
            "module.exports = Object.assign({}, real, { goalShown: function (d, st, toks) {"
            " return real.goalShown(d, Object.assign({}, st, patch), %(toks)s); } });\n")


# the real ticklist module with adoptForm replaced by a version that is wrong in one way
WRONG_ADOPT = ("var real = require(%(module)s);\n"
               "module.exports = Object.assign({}, real, { adoptForm: %(body)s });\n")
WRONG_ADOPTS = (
    ('adopts nothing', 'function (st) { return Object.assign({}, st); }'),
    ('adopts only the typed text, as before', 'function (st, form) { return real.adoptForm(st, form, true); }'),
    ('lets the form win over the URL',
     "function (st, form, t) { var out = real.adoptForm(st, form, t);"
     " ['region', 'status', 'priority', 'month', 'sort'].forEach(function (k) { if (form && form[k] && form[k] !== real.DEFAULTS[k]) out[k] = form[k]; });"
     " return out; }"),
    ('takes the selects after Back or Forward too', 'function (st, form) { return real.adoptForm(st, form, false); }'),
    ('takes nothing unless the URL is empty',
     'function (st, form, t) { return real.serialize(st) ? Object.assign({}, st) : real.adoptForm(st, form, t); }'),
    ('lets typed text replace the query in the URL',
     'function (st, form, t) { var out = real.adoptForm(st, form, t); if (form && form.q) out.q = form.q; return out; }'),
    ('reads the buttons from the form',
     "function (st, form, t) { var out = real.adoptForm(st, form, t); if (form && form.scope) out.scope = form.scope; return out; }"),
    ('changes the state it is given', 'function (st, form, t) { return Object.assign(st, real.adoptForm(st, form, t)); }'),
)


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

    def test_harness_rejects_a_goal_filter_that_ignores_one_filter(self):
        # the real module, with goalShown answering as if one filter were never set (or the scope were 'all', or
        # nothing were typed in the search box): whichever is dropped, the harness must notice
        self.assertTrue(os.path.exists(TICKLIST_JS), 'assets/js/pages/ticklist.js is missing')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cases = [(key, unset, 'toks') for key, unset in (('scope', 'all'), ('activity', 'all'), ('region', ''), ('status', ''),
                                                          ('priority', ''), ('month', ''), ('gpx', False))]
        cases.append(('q', '', '[]'))        # the search: the state is left alone, the tokens are dropped
        for key, unset, toks in cases:
            with self.subTest(ignored='the search tokens' if toks == '[]' else key):
                stub = os.path.join(tmp.name, 'no_%s.js' % key)
                with open(stub, 'w', encoding='utf-8') as fh:
                    fh.write(IGNORING % {'module': json.dumps(TICKLIST_JS), 'key': json.dumps(key), 'unset': json.dumps(unset), 'toks': toks})
                r = self.run_node(HARNESS, EXPLORE_JS, stub)
                self.assertNotEqual(r.returncode, 0, 'the harness passed a goalShown that ignores %s' % key)
                self.assertIn('FAIL goalShown', r.stderr)
                self.assertNotIn('checks passed', r.stdout)

    def test_harness_rejects_wrong_answers_about_the_form(self):
        self.assertTrue(os.path.exists(TICKLIST_JS), 'assets/js/pages/ticklist.js is missing')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for n, (what, body) in enumerate(WRONG_ADOPTS):
            with self.subTest(wrong=what):
                stub = os.path.join(tmp.name, 'wrong_%d.js' % n)
                with open(stub, 'w', encoding='utf-8') as fh:
                    fh.write(WRONG_ADOPT % {'module': json.dumps(TICKLIST_JS), 'body': body})
                r = self.run_node(HARNESS, EXPLORE_JS, stub)
                self.assertNotEqual(r.returncode, 0, 'the harness passed an adoptForm that %s' % what)
                self.assertIn('FAIL adoptForm', r.stderr)
                self.assertNotIn('checks passed', r.stdout)


class TickListPageSourceTests(unittest.TestCase):
    """The lines of the page part of ticklist.js (after the Node export) that hand the first state to adoptForm, read as
    text; and that the page has no index to fetch, so nothing of trips.js's retry rule applies to it."""

    def setUp(self):
        src = source(TICKLIST_JS)
        marker = 'module.exports = TKL; return;'
        self.assertEqual(src.count(marker), 1)
        self.pure, self.page = src.split(marker)

    def test_the_page_starts_from_what_the_form_already_holds(self):
        page = self.page
        self.assertRegex(self.pure, r'function adoptForm\(')
        self.assertRegex(self.pure, r'\badoptForm: adoptForm\b')
        self.assertRegex(self.pure, r"SELECTS\s*=\s*\['region', 'status', 'priority', 'month', 'sort'\]")
        start = re.search(r'(?:var|let|const)\s+state\s*=\s*adoptForm\(\s*parseState\(\s*location\.search\s*,\s*allowed\s*\)\s*,\s*found\s*,\s*traversal\s*\)', page)
        self.assertIsNotNone(start, 'the page does not start from adoptForm(parseState(location.search, allowed), found, traversal)')
        self.assertLess(start.start(), page.index('apply(false, true)'))
        found = re.search(r'(?:var|let|const)\s+found\s*=\s*\{([^}]*)\}', page)
        self.assertIsNotNone(found)
        self.assertRegex(found.group(1), r'\bq:\s*q\.value\b')
        self.assertRegex(page, r'SELECTS\.forEach\(function \((\w+)\) \{ if \(sel\[\1\]\) found\[\1\] = sel\[\1\]\.value; \}\)')
        self.assertLess(found.start(), start.start())
        self.assertLess(found.start(), page.index('function setControls'))
        self.assertRegex(page, r"traversal\s*=\s*nav\s*\?\s*nav\.type\s*===\s*'back_forward'")
        self.assertRegex(page, r"performance\.getEntriesByType\(\s*'navigation'\s*\)\[0\]")
        self.assertNotIn('if (!state.q && q.value)', page)       # the text-only take-over this replaces

    def test_the_tick_list_fetches_nothing(self):
        src = self.pure + self.page
        self.assertNotRegex(src, r'\bfetch\s*\(|XMLHttpRequest|\.json\b')


if __name__ == '__main__':
    unittest.main()
