"""Phase 2: the pure functions of assets/js/pages/trips.js (norm, tokens, parseState, match, score), run under node
through tests/trips_js_harness.js. Skipped when node is not installed: node is a dev-only convenience, the production
build never runs it. norm() is held to tests/norm_cases.json, the same table test_search.py checks search.normalize
against, so a drift between the Python index and the page's query handling fails here. Phase 4 adds facetOk, the
filter predicate: the harness is also run against the real module with one filter switched off at a time, and must fail.
It also adds adoptForm / ownSort (what the page takes over from a form the visitor used before the script arrived) and
stillFailed / mayLoad (when an index that did not load is asked for again): the harness is run against the real module
with each of them answering wrongly in one way, and the page's own lines that call them are read from the source.
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
HARNESS = os.path.join(TESTS, 'trips_js_harness.js')
TRIPS_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'trips.js')

# a module with the right exports but wrong answers: the harness must reject it
BAD_STUB = ("module.exports = {norm: function (s) { return s; }, tokens: function () { return []; },"
            " parseState: function () { return {}; }, match: function () { return true; },"
            " score: function () { return 0; }, chipLabel: function () { return ''; }};\n")


# the real module with its filter predicate wrapped: one key of the state is put back to its unset value before asking
IGNORING = ("var real = require(%(module)s);\n"
            "var patch = {}; patch[%(key)s] = %(unset)s;\n"
            "module.exports = Object.assign({}, real, { facetOk: function (d, st) {"
            " return real.facetOk(d, Object.assign({}, st, patch)); } });\n")


# the real module with one export replaced by a version that is wrong in one way
WRONG = ("var real = require(%(module)s);\n"
         "module.exports = Object.assign({}, real, { %(name)s: %(body)s });\n")
# (what is wrong, the export, its wrong version, the label the harness's failing check starts with)
WRONG_EXPORTS = (
    ('adopts nothing', 'adoptForm', 'function (st) { return Object.assign({}, st); }', 'adoptForm'),
    ('adopts only the typed text, as before', 'adoptForm',
     'function (st, form) { return real.adoptForm(st, form, true); }', 'adoptForm'),
    ('lets the form win over the URL', 'adoptForm',
     "function (st, form, t) { var out = real.adoptForm(st, form, t);"
     " ['region', 'year', 'format', 'sort'].forEach(function (k) { if (form && form[k] && form[k] !== real.DEFAULTS[k]) out[k] = form[k]; });"
     " return out; }", 'adoptForm'),
    ('takes the selects after Back or Forward too', 'adoptForm',
     'function (st, form) { return real.adoptForm(st, form, false); }', 'adoptForm'),
    ('takes nothing unless the URL is empty', 'adoptForm',
     'function (st, form, t) { return real.serialize(st) ? Object.assign({}, st) : real.adoptForm(st, form, t); }', 'adoptForm'),
    ('never sorts typed text by best match', 'adoptForm',
     "function (st, form, t) { var out = real.adoptForm(st, form, t);"
     " if (!real.ownSort(st, form, t)) out.sort = st.sort; return out; }", 'adoptForm'),
    ('sorts typed text by best match over a chosen sort', 'adoptForm',
     "function (st, form, t) { var out = real.adoptForm(st, form, t);"
     " if (out.q !== st.q && real.tokens(out.q).length) out.sort = 'relevance'; return out; }", 'adoptForm'),
    ('ticks the write-up filter for any value', 'adoptForm',
     'function (st, form, t) { var out = real.adoptForm(st, form, t); if (!t && form && form.writeup) out.writeup = true; return out; }',
     'adoptForm'),
    ('changes the state it is given', 'adoptForm',
     'function (st, form, t) { return Object.assign(st, real.adoptForm(st, form, t)); }', 'adoptForm'),
    ('calls the default sort a chosen one', 'ownSort', 'function () { return true; }', 'adoptForm'),
    ('forgets that a sort was chosen in the form', 'ownSort',
     'function (st) { return st.sort !== real.DEFAULTS.sort; }', 'adoptForm'),
    ('never forgets the query that failed', 'stillFailed', 'function (failedFor) { return failedFor; }', 'retry'),
    ('forgets the query that failed at once', 'stillFailed', 'function () { return null; }', 'retry'),
    ('asks again on every render after a failure', 'mayLoad',
     "function (state, failedFor, q) { return real.tokens(q).length > 0 && (state === 'idle' || state === 'failed'); }", 'retry'),
    ('never asks again after a failure', 'mayLoad',
     "function (state, failedFor, q) { return real.tokens(q).length > 0 && state === 'idle'; }", 'retry'),
    ('fetches for an empty box', 'mayLoad',
     "function (state, failedFor, q) { return state === 'idle' || (state === 'failed' && q !== failedFor); }", 'retry'),
)


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

    def test_harness_rejects_a_facet_filter_that_ignores_one_filter(self):
        # the real module, with facetOk answering as if one filter were never set (contract-phase4.md section 10 exports
        # it so that this can be tested): whichever filter is dropped, the harness must notice
        self.assertTrue(os.path.exists(TRIPS_JS), 'assets/js/pages/trips.js is missing')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for key, unset in (('activity', 'all'), ('region', ''), ('year', ''), ('format', ''), ('writeup', False)):
            with self.subTest(ignored=key):
                stub = os.path.join(tmp.name, 'no_%s.js' % key)
                with open(stub, 'w', encoding='utf-8') as fh:
                    fh.write(IGNORING % {'module': json.dumps(TRIPS_JS), 'key': json.dumps(key), 'unset': json.dumps(unset)})
                r = self.run_node(HARNESS, stub)
                self.assertNotEqual(r.returncode, 0, 'the harness passed a facetOk that ignores the %s filter' % key)
                self.assertIn('FAIL facetOk', r.stderr)
                self.assertNotIn('checks passed', r.stdout)

    def test_harness_rejects_wrong_answers_about_the_form_and_about_retrying(self):
        # the real module with adoptForm, ownSort, stillFailed or mayLoad wrong in one way each
        self.assertTrue(os.path.exists(TRIPS_JS), 'assets/js/pages/trips.js is missing')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for n, (what, name, body, label) in enumerate(WRONG_EXPORTS):
            with self.subTest(wrong=what):
                stub = os.path.join(tmp.name, 'wrong_%d.js' % n)
                with open(stub, 'w', encoding='utf-8') as fh:
                    fh.write(WRONG % {'module': json.dumps(TRIPS_JS), 'name': name, 'body': body})
                r = self.run_node(HARNESS, stub)
                self.assertNotEqual(r.returncode, 0, 'the harness passed a %s that %s' % (name, what))
                self.assertIn('FAIL ' + label, r.stderr)
                self.assertNotIn('checks passed', r.stdout)


class TripsPageSourceTests(unittest.TestCase):
    """The few lines of the page part of trips.js (after the Node export) that hand the decisions to the pure helpers the
    harness tests. Read as text: nothing here needs node."""

    def setUp(self):
        with open(TRIPS_JS, encoding='utf-8') as fh:
            src = fh.read()
        marker = 'module.exports = TRX; return;'
        self.assertEqual(src.count(marker), 1)
        self.pure, self.page = src.split(marker)

    def test_the_helpers_are_defined_before_the_export_and_touch_no_page(self):
        for name in ('adoptForm', 'ownSort', 'stillFailed', 'mayLoad'):
            with self.subTest(helper=name):
                self.assertRegex(self.pure, r'function %s\(' % name)
                self.assertRegex(self.pure, r'\b%s: %s\b' % (name, name))       # in TRX
        # nothing before the export reads the page: the one global is the shared helpers' own (window.Explore)
        self.assertEqual(re.findall(r'\b(?:document|window|location|performance|history|navigator)\.\w+', self.pure), ['window.Explore'])

    def test_the_page_starts_from_what_the_form_already_holds(self):
        page = self.page
        first_apply = page.index('apply(false, true)')
        start = re.search(r'(?:var|let|const)\s+state\s*=\s*adoptForm\(\s*fromUrl\s*,\s*found\s*,\s*traversal\s*\)', page)
        self.assertIsNotNone(start, 'the page does not start from adoptForm(fromUrl, found, traversal)')
        self.assertLess(start.start(), first_apply)
        self.assertRegex(page, r'(?:var|let|const)\s+fromUrl\s*=\s*parseState\(\s*location\.search\s*,\s*allowed\s*\)')
        self.assertRegex(page, r'(?:var|let|const)\s+userSort\s*=\s*ownSort\(\s*fromUrl\s*,\s*found\s*,\s*traversal\s*\)')
        # found: the text, the write-up box and every select, read before anything is written to a control
        found = re.search(r'(?:var|let|const)\s+found\s*=\s*\{([^}]*)\}', page)
        self.assertIsNotNone(found)
        self.assertRegex(found.group(1), r'\bq:\s*q\.value\b')
        self.assertRegex(found.group(1), r'\bwriteup:[^,]*\bchk\.checked\b')
        self.assertRegex(page, r'SELECTS\.forEach\(function \((\w+)\) \{ if \(sel\[\1\]\) found\[\1\] = sel\[\1\]\.value; \}\)')
        self.assertRegex(self.pure, r"SELECTS\s*=\s*\['region', 'year', 'format', 'sort'\]")
        self.assertLess(found.start(), start.start())
        self.assertLess(found.start(), page.index('function setControls'))
        self.assertEqual(len(re.findall(r'\bsetControls\(\)', page[:found.start()])), 0)
        # Back / Forward is told apart by the navigation entry, and a browser without one counts as a first visit
        self.assertRegex(page, r"traversal\s*=\s*nav\s*\?\s*nav\.type\s*===\s*'back_forward'")
        self.assertRegex(page, r"performance\.getEntriesByType\(\s*'navigation'\s*\)\[0\]")
        # the text-only take-over this replaces is gone
        self.assertNotIn('if (!state.q && q.value)', page)

    def test_every_search_goes_through_the_retry_rule(self):
        page = self.page
        ask = re.search(r'function ask\(\) \{(.*?)\n  \}', page, re.S)
        self.assertIsNotNone(ask, 'the page has no ask()')
        body = ask.group(1)
        lines = [ln.strip() for ln in body.strip().splitlines()]
        self.assertEqual(lines, ['failedFor = stillFailed(failedFor, state.q);',
                                 'daysFailedFor = stillFailed(daysFailedFor, state.q);',
                                 'if (mayLoad(indexState, failedFor, state.q)) loadIndex(render);',
                                 'if (mayLoad(daysState, daysFailedFor, state.q)) loadDays(render);'])
        # the two places a view is put on screen call it, and nothing fetches past it
        self.assertEqual(len(re.findall(r'\bask\(\);', page)), 2)
        self.assertEqual(len(re.findall(r'\bloadIndex\(render\)', page)), 1)
        self.assertEqual(len(re.findall(r'\bloadDays\(render\)', page)), 1)
        self.assertNotRegex(page, r'state\.q\s*!==\s*(failedFor|daysFailedFor)')
        # a box emptied and filled again inside the typing pause still counts as changed: noted on the input event itself
        handler = re.search(r"q\.addEventListener\('input', function \(\) \{(.*?)timer = setTimeout", page, re.S)
        self.assertIsNotNone(handler)
        self.assertIn('failedFor = stillFailed(failedFor, q.value);', handler.group(1))
        self.assertIn('daysFailedFor = stillFailed(daysFailedFor, q.value);', handler.group(1))
        # and a failure remembers the query that was in the box
        self.assertRegex(page, r"indexState = 'failed'; failedFor = state\.q;")
        self.assertRegex(page, r"daysState = 'failed'; daysFailedFor = state\.q;")


if __name__ == '__main__':
    unittest.main()
