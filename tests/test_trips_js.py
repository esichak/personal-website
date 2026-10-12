"""Phase 2: the pure functions of assets/js/pages/trips.js (norm, tokens, parseState, match, score), run under node
through tests/trips_js_harness.js. Skipped when node is not installed: node is a dev-only convenience, the production
build never runs it. norm() is held to tests/norm_cases.json, the same table test_search.py checks search.normalize
against, so a drift between the Python index and the page's query handling fails here. Phase 4 adds facetOk, the
filter predicate: the harness is also run against the real module with one filter switched off at a time, and must fail.
It also adds adoptForm / ownSort (what the page takes over from a form the visitor used before the script arrived) and
stillFailed / mayLoad (when an index that did not load is asked for again): the harness is run against the real module
with each of them answering wrongly in one way, and the page's own lines that call them are read from the source.

Review gate (fix C): historyStep (what a change of view does to the browser's history: typing rewrites the entry, a
pick adds one, a submitted search adds one whenever the view differs from the one the entry stood for) and clearedSort
(the sort Clear all leaves). Three kinds of test, as above: the harness on the pure helpers, and on each of them
answering wrongly in one way; the page's own lines, read from the source; and the page part of trips.js itself, run
whole by the harness against a stand-in for the browser built from a Trips page that sitegen.pages.trips generated
from a synthetic site (page_model), on which a visitor's typing, Enter, filters and Back are played and the history
is read after each step. The stand-in is not a browser: it spells addresses as the URL Standard does and keeps a
list of entries, and models neither layout nor focus nor the back/forward cache.

Round 3 of the gate (fix C corrected). The page keeps two addresses, both built by address() in its own spelling and
never read back from location: entryUrl, what this history entry stood for when the visitor last settled on it, and
nowUrl, what it carries at this moment. write() asks historyStep with them and the next address, puts the entry back
before it adds one, and settles the entry on every change but typing; a year link (hashchange), Back and Forward
(popstate) settle it too. sortForSearch() keeps Best match from being the sort of no search, from the submit handler,
the typing timer, the load and popstate. The source tests pin those lines; the harness's "page:" checks from "round 3"
on play the sequences; BROKEN_PAGES is the page with each of those lines changed in one way. The two cases round 2
kept as expected failures (an apostrophe in the search, picks made within a moment) are regular checks: no known gap
is left (FORMER_GAPS).

Round 4 of the gate (one change in the popstate handler). Best match can be picked in the Sort menu while the search
box is empty; its entry then carries sort=relevance without a search. Round 3's popstate put the sort right in the page
(the menu read Newest first again) and left the entry's address saying sort=relevance. Now the handler remembers the
sort the address arrived with before sortForSearch, builds entryUrl and nowUrl from address() as before, and, only when
the sort was corrected, rewrites the entry with history.replaceState(null, '', nowUrl + location.hash) and reads
lastSearch again from location: the load already rewrote such an address, Back and Forward now do too. An entry whose
sort needs no correction is not written to. The source tests pin those lines and the page's counts of history and
location.search uses; the harness's "page:" checks from "round 4" on (ROUND_4) play the sequences and read, after every
step, the entries, the position, the address, the Sort menu and the order of the list; BROKEN_PAGES has the handler
with each of its lines changed in one way. The last of those checks is a browser that refuses the rewrite (the stand-in's
refuse(true): replaceState throws, as for a page opened from a file): the try keeps the page going, and the view still
comes on screen.

Round 6 of the gate. historyStep is defined in assets/js/pages/explore.js, where the Tick list page takes it from as
well; trips.js has `var historyStep = X.historyStep;` in its place and still exports it as TRX.historyStep. The source
tests say so of both files (one definition, before explore.js's export, that touches no page; no second copy in
trips.js), and the harness says that TRX.historyStep is that very function. The modules with a wrong historyStep
(js_fixtures.WRONG_HISTORY_STEPS) break it where it lives: each is the real explore.js with its historyStep replaced,
with a copy of trips.js beside it that takes the rule from there. The stand-in for the browser moved to
tests/page_standin.js, which tests/ticklist_js_harness.js uses too (tests/test_ticklist_js.py plays the same history
sequences on a generated Tick list page).
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
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
TESTS = os.path.join(ROOT, 'tests')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc  # noqa: E402
import js_fixtures  # noqa: E402
from js_fixtures import tree  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

HARNESS = os.path.join(TESTS, 'trips_js_harness.js')
STANDIN = os.path.join(TESTS, 'page_standin.js')           # the stand-in for the browser, shared with the tick list harness
TRIPS_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'trips.js')
EXPLORE_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'explore.js')

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
    # clearedSort(sort, userSort), wrong in one way each. historyStep, which stood here until round 6, is explore.js's:
    # js_fixtures.WRONG_HISTORY_STEPS, and test_harness_rejects_a_wrong_history_rule_broken_where_it_is_defined below
    ('keeps Best match as a chosen sort', 'clearedSort',
     'function (sort, own) { return own ? [sort, true] : [real.DEFAULTS.sort, false]; }', 'clearedSort'),
    ('resets a sort the visitor chose', 'clearedSort', 'function (sort, own) { return [real.DEFAULTS.sort, false]; }', 'clearedSort'),
    ('keeps an automatic sort', 'clearedSort',
     "function (sort, own) { return sort !== 'relevance' ? [sort, !!own] : [real.DEFAULTS.sort, false]; }", 'clearedSort'),
    ('forgets that the kept sort was chosen', 'clearedSort',
     'function (sort, own) { return [real.clearedSort(sort, own)[0], false]; }', 'clearedSort'),
    ('calls the default it resets to a chosen sort', 'clearedSort',
     'function (sort, own) { return [real.clearedSort(sort, own)[0], true]; }', 'clearedSort'),
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
        # the real module with adoptForm, ownSort, stillFailed, mayLoad or clearedSort wrong in one way each
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

    def beside(self, tmp, name, explore_body=None, change=None):
        """A folder <tmp>/<name>/ with a copy of trips.js (its text changed by `change`, when given) and, beside it, the
        explore.js it asks for: the site's own, or the real module with its historyStep replaced by `explore_body`.
        Returns the path of the copy of trips.js."""
        folder = os.path.join(tmp, name)
        os.mkdir(folder)
        if explore_body is None:
            shutil.copy(EXPLORE_JS, os.path.join(folder, 'explore.js'))
        else:
            js_fixtures.wrong_explore(folder, explore_body)
        with open(TRIPS_JS, encoding='utf-8') as fh:
            src = fh.read()
        path = os.path.join(folder, 'trips.js')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(change(src) if change else src)
        return path

    def test_harness_rejects_a_wrong_history_rule_broken_where_it_is_defined(self):
        # round 6: historyStep is explore.js's. Each wrong version replaces it there; the copy of trips.js beside it
        # is unchanged and takes it through X.historyStep, so TRX.historyStep is the wrong function and the harness's
        # checks of the rule must notice
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.assertEqual(len(set(what for what, _body in js_fixtures.WRONG_HISTORY_STEPS)), len(js_fixtures.WRONG_HISTORY_STEPS))
        for n, (what, body) in enumerate(js_fixtures.WRONG_HISTORY_STEPS):
            with self.subTest(wrong=what):
                r = self.run_node(HARNESS, self.beside(tmp.name, 'wrong_%d' % n, body))
                self.assertNotEqual(r.returncode, 0, 'the harness passed a historyStep that %s' % what)
                self.assertIn('FAIL historyStep', r.stderr)
                self.assertEqual(len(re.findall(r'(?m)^FAIL ', r.stderr)), 1)
                self.assertNotIn('checks passed', r.stdout)
        # a module made the same way around the right function passes: it is the answers that are rejected, not the wrapper
        r = self.run_node(HARNESS, self.beside(tmp.name, 'right', js_fixtures.RIGHT_HISTORY_STEP))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('checks passed', r.stdout)

    def test_harness_rejects_a_trips_js_with_a_history_rule_of_its_own(self):
        # round 6: TRX.historyStep is Explore.historyStep itself. A copy of trips.js that defines the rule again fails
        # the harness even when its copy answers rightly: two copies are what the move to explore.js did away with
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        taken = '  var historyStep = X.historyStep;'
        copies = (('a function that hands every question on to explore.js',
                   '  function historyStep(kind, entry, now, next, recent) { return X.historyStep(kind, entry, now, next, recent); }'),
                  ('the rule written out again',
                   "  function historyStep(kind, entry, now, next, recent) {\n"
                   "    if (recent || kind === 'type') return { push: false, restore: false };\n"
                   "    if (kind === 'pick') return { push: true, restore: false };\n"
                   "    var push = next !== entry;\n"
                   "    return { push: push, restore: push && now !== entry };\n"
                   "  }"))

        def with_copy(text):
            def change(src):
                self.assertEqual(src.count(taken), 1, 'assets/js/pages/trips.js no longer has this line once: %r' % taken)
                return src.replace(taken, text)
            return change

        for n, (what, text) in enumerate(copies):
            with self.subTest(copy=what):
                path = self.beside(tmp.name, 'copy_%d' % n, change=with_copy(text))
                self.assertEqual(self.run_node('--check', path).returncode, 0)
                r = self.run_node(HARNESS, path)
                self.assertNotEqual(r.returncode, 0, 'the harness passed a trips.js with %s' % what)
                self.assertIn('FAIL exports: the history helpers', r.stderr)
                self.assertIn('TRX.historyStep is not Explore.historyStep itself', r.stderr)
                self.assertEqual(len(re.findall(r'(?m)^FAIL ', r.stderr)), 1)
                self.assertNotIn('checks passed', r.stdout)
        # the unchanged pair, from a folder of its own, passes
        r = self.run_node(HARNESS, self.beside(tmp.name, 'unchanged'))
        self.assertEqual(r.returncode, 0, r.stderr)


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
        for name in ('adoptForm', 'ownSort', 'stillFailed', 'mayLoad', 'clearedSort'):
            with self.subTest(helper=name):
                self.assertRegex(self.pure, r'function %s\(' % name)
                self.assertRegex(self.pure, r'\b%s: %s\b' % (name, name))       # in TRX
        # nothing before the export reads the page: the one global is the shared helpers' own (window.Explore)
        self.assertEqual(re.findall(r'\b(?:document|window|location|performance|history|navigator)\.\w+', self.pure), ['window.Explore'])

    def test_history_step_is_defined_once_in_explore_js_and_trips_js_hands_it_on(self):
        # round 6: the rule for history entries is shared with the tick list, so it lives in explore.js
        with open(EXPLORE_JS, encoding='utf-8') as fh:
            explore = fh.read()
        code = re.sub(r'(?m)(^|\s)//.*$', r'\1', re.sub(r'(?s)/\*.*?\*/', '', explore))     # explore.js without its comments
        # ---- explore.js: one definition, of five parameters, and nothing gives the name another value
        self.assertEqual(re.findall(r'\bfunction historyStep\(([^)]*)\)', code), ['kind, entry, now, next, recent'])
        self.assertEqual(len(re.findall(r'\bfunction\s+historyStep\b', code)), 1)
        self.assertEqual(re.findall(r'\bhistoryStep\s*=(?!=)', code), [])
        # before the file's export, and in it: the Explore object, then the two ways it is handed out
        defined = code.index('function historyStep(')
        exported = re.search(r'(?m)^  var Explore = \{(.*?)\};$', code, re.S)
        self.assertIsNotNone(exported, 'explore.js has no `var Explore = {...};`')
        self.assertEqual(len(re.findall(r'\bhistoryStep: historyStep\b', exported.group(1))), 1)
        self.assertEqual(len(re.findall(r'\bhistoryStep\b', code)), 3)             # the definition and the export's key and value
        self.assertLess(defined, exported.start())
        self.assertLess(exported.end(), code.index('module.exports = Explore;'))
        self.assertLess(exported.end(), code.index('window.Explore = Explore;'))
        # it touches no page: its body names neither the document, the window, the location nor the history (nor a
        # clock: whether an entry was made a moment ago is the caller's to say), and the whole file reads none of
        # them; the one global it writes is its own export
        body = re.search(r'function historyStep\(kind, entry, now, next, recent\) \{(.*?)\n  \}', code, re.S)
        self.assertIsNotNone(body)
        self.assertEqual(re.findall(r'\b(?:document|window|location|history|performance|navigator|Date|setTimeout)\b', body.group(1)), [])
        self.assertEqual(sorted(set(re.findall(r'[A-Za-z_$][\w$]*', re.sub(r"'[^']*'", '', body.group(1))))),
                         ['entry', 'false', 'if', 'kind', 'next', 'now', 'push', 'recent', 'restore', 'return', 'true', 'var'])
        self.assertEqual(re.findall(r'\b(?:document|window|location|performance|history|navigator)\.\w+', code), ['window.Explore'])
        self.assertEqual(re.findall(r'\b(?:document|location|performance|history|navigator)\b', code), [])
        # ---- trips.js: no definition of its own, anywhere; the name is given one value, explore.js's function, before
        # the export, and TRX hands that on
        with open(TRIPS_JS, encoding='utf-8') as fh:
            src = fh.read()
        self.assertNotRegex(src, r'\bfunction\s+historyStep\b')
        self.assertEqual(re.findall(r'\bhistoryStep\s*=(?!=)\s*([^;]+);', src), ['X.historyStep'])
        self.assertEqual(self.pure.count('  var historyStep = X.historyStep;'), 1)
        self.assertEqual(len(re.findall(r'\bX\.historyStep\b', src)), 1)
        self.assertEqual(len(re.findall(r'\bhistoryStep: historyStep\b', self.pure)), 1)        # in TRX
        self.assertEqual(len(re.findall(r'\bhistoryStep:', src)), 1)
        self.assertLess(self.pure.index('var historyStep = X.historyStep;'), self.pure.index('var TRX = {'))
        # X is explore.js: the file beside it under node, window.Explore in the bundle
        self.assertEqual(re.findall(r'(?m)^  var X = (.*?);', src),
                         ["(typeof module === 'object' && module && module.exports) ? require('./explore.js') : window.Explore"])
        self.assertEqual(re.findall(r'\bX\s*=(?!=)', src), ['X ='])
        # the page part asks it once, in write() (test_write_puts_the_entry_back_before_it_adds_one), under that name
        self.assertEqual(len(re.findall(r'\bhistoryStep\b', self.code())), 1)

    def test_the_page_starts_from_what_the_form_already_holds(self):
        page = self.page
        first_apply = page.index("apply('type', true, true)")      # the load: the first write of the page
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

    # ------------------------------------------------------------ the history (historyStep, clearedSort)

    def code(self):
        """The page part without its // comments (several of them name write() and apply())."""
        return re.sub(r'(?m)(^|\s)//.*$', r'\1', self.page)

    def body_of(self, opening):
        """The body of the page-level function or listener that starts with this text, up to its closing line."""
        code = self.code()
        self.assertEqual(code.count(opening), 1, 'the page does not have %r once' % opening)
        rest = code[code.index(opening) + len(opening):]
        end = re.search(r'\n  \}', rest)
        self.assertIsNotNone(end, opening)
        return rest[:end.start()]

    def lines_of(self, opening):
        """body_of(opening), line by line, without indentation or blank lines."""
        return [ln.strip() for ln in self.body_of(opening).splitlines() if ln.strip()]

    WRITE = 'function write(kind, keepHash, settle) {'
    ASK = 'var step = historyStep(kind, entryUrl, nowUrl, next, Date.now() - lastPush < 600);'
    RESTORE = "if (step.restore) history.replaceState(null, '', entryUrl);"
    WRITTEN = "history[step.push ? 'pushState' : 'replaceState'](null, '', next + (keepHash ? location.hash : ''));"

    def test_write_puts_the_entry_back_before_it_adds_one(self):
        lines = self.lines_of(self.WRITE)
        body = self.body_of(self.WRITE)
        # the new address is address()'s; a state that cannot be written (a lone surrogate) is left alone
        self.assertEqual(lines[:2], ['var next;', 'try { next = address(); } catch (e) { return; }'])
        # the step is historyStep's answer for: the kind, what the entry stood for, the address it carries at this
        # moment, the new address, and whether an entry was made within the last 600 ms
        for line in (self.ASK, self.RESTORE, self.WRITTEN):
            self.assertEqual(lines.count(line), 1, line)
        self.assertEqual(len(re.findall(r'\bhistoryStep\(', self.code())), 1)
        self.assertLess(lines.index(self.ASK), lines.index(self.RESTORE))
        self.assertLess(lines.index(self.RESTORE), lines.index(self.WRITTEN))
        # the entry is put back to what it stood for (the new address, in WRITTEN, is the one the step was asked about)
        self.assertEqual(re.findall(r"history\.replaceState\(null, '', (\w+)\)", body), ['entryUrl'])
        # these are the only two history calls of write(). The page has one more, since round 4: popstate rewrites an
        # entry whose sort it has put right (test_back_and_forward_rewrite_an_entry_only_when_its_sort_was_put_right).
        # write()'s is the one pushState of the page: an entry is made here and nowhere else. Nothing else is written
        # to the address
        self.assertEqual(len(re.findall(r'\bhistory\s*[.\[]', body)), 2)
        self.assertEqual(len(re.findall(r'\b(?:pushState|replaceState)\b', body)), 3)
        self.assertEqual(len(re.findall(r'\bhistory\s*[.\[]', self.code())), 3)
        self.assertEqual(len(re.findall(r'\b(?:pushState|replaceState)\b', self.code())), 4)
        self.assertEqual(len(re.findall(r'\bpushState\b', self.code())), 1)
        self.assertEqual(len(re.findall(r'\bpushState\b', body)), 1)
        self.assertNotRegex(self.code(), r'\blocation\s*(?:\.\s*(?:href|search|hash|pathname)\s*)?=(?!=)|\blocation\s*\.\s*(?:assign|replace)\s*\(')
        # a new entry is timed, for the 'made a moment ago' rule
        self.assertIn('if (step.push) lastPush = Date.now();', body)
        self.assertEqual(len(re.findall(r'\blastPush\s*=(?!=)', self.code())), 2)        # that line and its declaration (0)

    def test_the_two_addresses_are_built_by_address_and_never_read_from_location(self):
        code = self.code()
        # address(): the pathname and the state as the page serializes it. The one place the pathname is read
        self.assertEqual(self.lines_of('function address() {'),
                         ['var qs = serialize(state);', "return location.pathname + (qs ? '?' + qs : '');"])
        self.assertEqual(len(re.findall(r'\blocation\s*\.\s*pathname\b', code)), 1)
        self.assertEqual(len(re.findall(r'(?<![\w.])address\(\)', code)), 3)            # its definition, write() and popstate
        # entryUrl and nowUrl: every value either is ever given, in the order of the source. Each is null, the address
        # write() built (next), the other of the two, or address() itself; none mentions location
        given = [(re.findall(r'entryUrl|nowUrl', m.group(1)), m.group(2).strip())
                 for m in re.finditer(r'((?:\b(?:entryUrl|nowUrl)\s*=(?!=)\s*)+)([^;,]+)[;,]', code)]
        self.assertEqual(given, [(['entryUrl'], 'null'), (['nowUrl'], 'null'),           # declared empty
                                 (['entryUrl', 'nowUrl'], 'next'),                        # write(): the first write
                                 (['nowUrl'], 'next'),                                    # write(): every write
                                 (['entryUrl'], 'next'),                                  # write(): a deliberate change
                                 (['entryUrl'], 'nowUrl'),                                # popstate, the same view
                                 (['entryUrl', 'nowUrl'], 'address()'),                   # popstate onto another view
                                 (['entryUrl'], 'nowUrl')])                               # hashchange
        self.assertRegex(code, r'(?m)^  var entryUrl = null, nowUrl = null;$')
        self.assertEqual(re.findall(r'\bnext\s*=(?!=)\s*([^;]+);', self.body_of(self.WRITE)), ['address()'])
        # what the page does read from location: the fragment; and the query string, for the state (on load and on
        # Back) and to tell a jump to a fragment from a change of view (lastSearch, in the browser's spelling on both
        # sides of the comparison). lastSearch is read from location in four places: where it is declared, after
        # write()'s write, on a popstate onto another view, and again once popstate has rewritten that entry (round 4)
        self.assertEqual(sorted(set(re.findall(r'\blocation\s*\.\s*(\w+)', code))), ['hash', 'pathname', 'search'])
        self.assertEqual(len(re.findall(r'\blocation\.search\b', code)), 7)
        self.assertEqual(len(re.findall(r'\bparseState\(location\.search, allowed\)', code)), 2)
        self.assertEqual(len(re.findall(r'\blastSearch = location\.search;', code)), 4)
        self.assertEqual(len(re.findall(r'\blastSearch\s*=(?!=)', code)), 4)                 # and it is given no other value
        self.assertEqual(len(re.findall(r'\blocation\.search === lastSearch\b', code)), 1)
        self.assertEqual(len(re.findall(r'\blastSearch\b', code)), 5)

    def test_write_settles_the_entry_on_every_change_but_typing(self):
        code = self.code()
        lines = self.lines_of(self.WRITE)
        body = self.body_of(self.WRITE)
        first = 'if (entryUrl === null) entryUrl = nowUrl = next;'
        now = 'nowUrl = next;'
        settle = "if (step.push || settle || kind !== 'type') entryUrl = next;"
        for line in (first, now, settle):
            self.assertEqual(lines.count(line), 1, line)
        # the first write sets both from the view the page opened on, before the step is asked for
        self.assertLess(lines.index(first), lines.index(self.ASK))
        # then, once the address is written: on every write the address the entry carries now (a line of its own, under
        # no condition); and on a push, on the load (settle) and for every kind but 'type', what the entry stands for
        written = lines.index(self.WRITTEN)
        self.assertLess(written, lines.index(now))
        self.assertLess(lines.index(now), lines.index(settle))
        # both in the try of the write itself, to its end: a write the browser refuses (file://) changes neither
        self.assertEqual(lines[written - 2:written], ['try {', self.RESTORE])
        self.assertEqual(lines[lines.index(settle) + 1:], ['} catch (e) { /* file:// */ }'])
        # and nothing else in write() gives either a value
        self.assertEqual((len(re.findall(r'\bentryUrl\s*=(?!=)', body)), len(re.findall(r'\bnowUrl\s*=(?!=)', body))), (2, 2))
        # settle is the load's alone: the one call that passes it (and the one that keeps the fragment)
        self.assertEqual(re.findall(r'(?<![\w.])apply\(([^()]*,[^()]*)\)', code), ['kind, keepHash, settle', "'type', true, true"])
        self.assertEqual(re.findall(r'(?<![\w.])write\(([^()]*)\)', code), ['kind, keepHash, settle', 'kind, keepHash, settle'])
        self.assertIn('write(kind, keepHash, settle);', self.body_of('function apply(kind, keepHash, settle) {'))

    POP = "window.addEventListener('popstate', function () {"
    POP_SAME = 'if (location.search === lastSearch) { entryUrl = nowUrl; return; }'
    POP_READ = 'state = parseState(location.search, allowed);'
    ARRIVED = 'var arrived = state.sort;'
    POP_SORT = 'if (!searching()) sortForSearch();'
    POP_VIEW = 'entryUrl = nowUrl = address();'
    REWRITE = "if (state.sort !== arrived) { history.replaceState(null, '', nowUrl + location.hash); lastSearch = location.search; }"
    POP_TRY = ('try {', '} catch (e) { /* keep what was */ }')

    def test_back_forward_and_a_year_link_settle_the_entry(self):
        # popstate. The same query string as the view on screen (a jump back to or from a fragment, or another entry
        # with this address): the entry the visitor is on now stands for that view, and nothing is read again. Another
        # view: the state is read from the address, and both addresses are that view's, built once the sort is settled.
        # Round 4: the sort the address arrived with is remembered, and the entry is rewritten when it was corrected
        pop = self.lines_of(self.POP)
        self.assertEqual(pop, [self.POP_SAME,
                               'lastSearch = location.search;',
                               self.POP_READ,
                               'userSort = state.sort !== DEFAULTS.sort;',
                               self.ARRIVED,
                               self.POP_SORT,
                               self.POP_TRY[0],
                               self.POP_VIEW,
                               self.REWRITE,
                               self.POP_TRY[1],
                               'setControls();', 'ask();', 'render();'])
        # coming back goes through neither write() nor apply(): no step is asked for and no entry is made
        self.assertNotRegex(' '.join(pop), r'\b(?:write|apply|historyStep|pushState)\b')
        # and a popstate for the view on screen (the first line) returns before anything is read or written
        self.assertNotRegex(pop[0], r'\b(?:history|parseState|address)\b')
        # hashchange: a year link made a new entry for the view on screen
        self.assertEqual(self.lines_of("window.addEventListener('hashchange', function () {"),
                         ['entryUrl = nowUrl;', "if (location.hash === '#search') focusSearch();"])
        # one listener each, both in place before the load's write
        code = self.code()
        for event in ('popstate', 'hashchange'):
            self.assertEqual(code.count("window.addEventListener('%s'" % event), 1)
            self.assertLess(code.index("window.addEventListener('%s'" % event), code.index("apply('type', true, true);"))

    def test_back_and_forward_rewrite_an_entry_only_when_its_sort_was_put_right(self):
        # Round 4. An entry may carry Best match without a search (the visitor picked it in the menu with an empty box).
        # Landing on it, popstate puts the sort right and then rewrites the entry's address, as the load rewrites such
        # an address, so the menu and the address agree. Every other entry is left as it is
        code = self.code()
        pop = self.lines_of(self.POP)
        # the sort the address arrived with: remembered once the state has been read from the address, and on the line
        # before sortForSearch can change it. Remembered once and compared once; nothing else gives it a value
        self.assertEqual(code.count(self.ARRIVED), 1)
        self.assertEqual(len(re.findall(r'\barrived\b', code)), 2)
        self.assertEqual(len(re.findall(r'\barrived\s*=(?!=)', code)), 1)
        self.assertLess(pop.index(self.POP_READ), pop.index(self.ARRIVED))
        self.assertLess(pop.index('userSort = state.sort !== DEFAULTS.sort;'), pop.index(self.ARRIVED))
        self.assertEqual(pop.index(self.POP_SORT), pop.index(self.ARRIVED) + 1)
        # one try, after the sort is settled; in it, in this order: entryUrl and nowUrl from address(), then the rewrite
        start, end = pop.index(self.POP_TRY[0]), pop.index(self.POP_TRY[1])
        self.assertEqual((pop.count(self.POP_TRY[0]), pop.count(self.POP_TRY[1])), (1, 1))
        self.assertLess(pop.index(self.POP_SORT), start)
        self.assertEqual(pop[start + 1:end], [self.POP_VIEW, self.REWRITE])
        self.assertEqual(pop[end + 1:], ['setControls();', 'ask();', 'render();'])        # the controls follow the corrected state
        # the rewrite, part by part: only when the sort was corrected; replaceState (the same entry); the address the
        # page has just built, with the fragment the entry has; then the query string on screen, read again from
        # location (the browser's spelling, as after write()'s write), so that a later jump to a fragment of this
        # entry is not taken for a change of view
        parts = re.fullmatch(r'if \((.*?)\) \{ (.*?); (.*?); \}', pop[start + 2])
        self.assertIsNotNone(parts, pop[start + 2])
        self.assertEqual(parts.groups(), ('state.sort !== arrived', "history.replaceState(null, '', nowUrl + location.hash)",
                                          'lastSearch = location.search'))
        # this is popstate's one use of history, and the one place the page writes nowUrl with the entry's fragment
        self.assertEqual(len(re.findall(r'\bhistory\b', ' '.join(pop))), 1)
        self.assertEqual(code.count('nowUrl + location.hash'), 1)
        self.assertEqual(len(re.findall(r'\bstate\.sort !== arrived\b', code)), 1)
        # the page's history calls by name: write() puts the entry back, popstate rewrites it (write()'s other call
        # chooses between pushState and replaceState)
        self.assertEqual(re.findall(r"\bhistory\.(\w+)\(null, '', ([^;]+)\);", code),
                         [('replaceState', 'entryUrl'), ('replaceState', 'nowUrl + location.hash')])
        self.assertEqual(len(re.findall(r'\bhistory\s*[.\[]', code)), 3)
        self.assertEqual(len(re.findall(r'\b(?:pushState|replaceState)\b', code)), 4)
        # the fragment is read in four places: at load (hash), on the load's write (keepHash), for this rewrite, and
        # for the header's Search link (hashchange)
        self.assertEqual(len(re.findall(r'\blocation\.hash\b', code)), 4)
        self.assertEqual(len(re.findall(r'\blocation\.search\b', code)), 7)
        # the load makes the same correction before its own write, which keeps the fragment too
        self.assertRegex(code, r"(?m)^  if \(!searching\(\)\) sortForSearch\(\);\s*\n  apply\('type', true, true\);$")

    def test_the_sort_follows_the_search_box_through_sort_for_search(self):
        code = self.code()
        # with words: best match, unless the visitor chose a sort. Without: whatever clearedSort leaves (never Best match)
        self.assertEqual(self.lines_of('function sortForSearch() {'),
                         ["if (searching()) { if (!userSort) state.sort = 'relevance'; return; }",
                          'var kept = clearedSort(state.sort, userSort);', 'state.sort = kept[0];', 'userSort = kept[1];'])
        # called in four places, and nowhere else
        self.assertEqual(len(re.findall(r'(?<![\w.])sortForSearch\(\)', code)), 5)      # its definition and the four
        # Enter: once the box is read, before the view is put on screen
        submit = self.lines_of("form.addEventListener('submit', function (e) {")
        self.assertEqual(submit[-3:], ['state.q = q.value;', 'sortForSearch();', "apply('submit');"])
        # the typing timer, the same way
        typing = self.body_of("q.addEventListener('input', function () {")
        self.assertRegex(typing, r"timer = setTimeout\(function \(\) \{\s*state\.q = q\.value;\s*sortForSearch\(\);\s*apply\('type'\);\s*\}, 150\);")
        # the load, and Back or Forward onto another view: only when there is no search (a shared ?q=... keeps its order)
        self.assertEqual(code.count('if (!searching()) sortForSearch();'), 2)
        self.assertRegex(code, r"(?m)^  if \(!searching\(\)\) sortForSearch\(\);\s*\n  apply\('type', true, true\);$")
        pop = self.lines_of("window.addEventListener('popstate', function () {")
        self.assertEqual(pop.count('if (!searching()) sortForSearch();'), 1)
        # the rule the two handlers had inline is gone
        self.assertNotIn("searching() ? 'relevance' : 'newest'", code)

    def test_every_change_of_view_says_what_kind_it_is(self):
        code = self.code()
        calls = re.findall(r'(?<![\w.])apply\(([^()]*)\)', code)
        self.assertEqual(calls.count('kind, keepHash, settle'), 1)                     # the definition
        calls.remove('kind, keepHash, settle')
        self.assertEqual(sorted(calls), sorted(["'pick'"] * 7 + ["'submit'", "'type'", "'type', true, true"]))
        # no call says true or false any more (the old apply(push, keepHash))
        self.assertNotRegex(code, r'(?<![\w.])(?:apply|write)\(\s*(?:true|false|changed|push)\b')
        # Enter in the search box: the form's submit handler, which also stops the form and the typing timer
        submit = self.body_of("form.addEventListener('submit', function (e) {")
        self.assertEqual(re.findall(r'apply\(([^()]*)\)', submit), ["'submit'"])
        self.assertIn('e.preventDefault();', submit)
        self.assertIn('clearTimeout(timer);', submit)
        self.assertNotIn('changed', submit)
        # typing: the timer of the input handler
        typing = self.body_of("q.addEventListener('input', function () {")
        self.assertEqual(re.findall(r'apply\(([^()]*)\)', typing), ["'type'"])
        self.assertRegex(typing, r"timer = setTimeout\(function \(\) \{[^}]*apply\('type'\);\s*\}, 150\);")
        # the load: the page's first write, after every listener is in place
        self.assertRegex(code, r"(?m)^  apply\('type', true, true\);$")
        self.assertLess(code.index("window.addEventListener('popstate'"), code.index("apply('type', true, true);"))
        # a pick: every filter control, Clear all and a chip's remove button
        for control in ("actBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.activity === b.dataset.filter) return; "
                        "state.activity = b.dataset.filter; apply('pick'); }); });",
                        "viewBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.view === b.dataset.view) return; "
                        "state.view = b.dataset.view; apply('pick'); }); });",
                        "['region', 'year', 'format'].forEach(function (k) { if (sel[k]) sel[k].addEventListener('change', function () { "
                        "state[k] = sel[k].value; apply('pick'); }); });",
                        "if (sel.sort) sel.sort.addEventListener('change', function () { state.sort = sel.sort.value; userSort = true; apply('pick'); });",
                        "if (chk) chk.addEventListener('change', function () { state.writeup = chk.checked; apply('pick'); });"):
            with self.subTest(control=control[:40]):
                self.assertEqual(code.count(control), 1)
        clear = self.body_of('function clearAll() {')
        self.assertEqual(re.findall(r'apply\(([^()]*)\)', clear), ["'pick'"])
        self.assertEqual(code.count("clearBtn.addEventListener('click', clearAll);"), 1)
        self.assertEqual(code.count("b.addEventListener('click', clearAll);"), 1)      # the empty state's 'Clear filters'
        chip = self.body_of("    b.addEventListener('click', function () {")
        self.assertEqual(re.findall(r'apply\(([^()]*)\)', chip), ["'pick'"])
        self.assertIn('state[key] = DEFAULTS[key];', chip)

    def test_clear_all_and_the_search_chip_hand_the_sort_to_cleared_sort(self):
        code = self.code()
        clear = self.body_of('function clearAll() {')
        lines = [ln.strip() for ln in clear.strip().splitlines()]
        self.assertEqual(lines, ['state.q = DEFAULTS.q;', 'FACETS.forEach(function (k) { state[k] = DEFAULTS[k]; });',
                                 'var kept = clearedSort(state.sort, userSort);', 'state.sort = kept[0];', 'userSort = kept[1];',
                                 "apply('pick');", 'q.focus();'])
        chip = self.body_of("    b.addEventListener('click', function () {")
        self.assertIn("if (key === 'q') { var kept = clearedSort(state.sort, userSort); state.sort = kept[0]; userSort = kept[1]; }", chip)
        # clearedSort decides in three places: Clear all, the search chip, and sortForSearch (round 3)
        self.assertEqual(len(re.findall(r'\bclearedSort\(', code)), 3)
        self.assertEqual(len(re.findall(r'\bvar kept = clearedSort\(state\.sort, userSort\);', code)), 3)
        self.assertIn('var kept = clearedSort(state.sort, userSort);', self.body_of('function sortForSearch() {'))
        # the rule these two lines had before is gone: a chosen Best match stayed as the sort of no search
        self.assertNotIn('if (!userSort) state.sort = DEFAULTS.sort', code)
        self.assertNotRegex(code, r"key === 'q' && !userSort")


# ---------------------------------------------------------------- the page part of trips.js, on a generated Trips page

PREFIX = 'synx-'                  # every fixture slug starts with it; no real trip's slug does
# (slug, front matter): three activities (the arrow keys of the activity chips pass through them), two regions, three
# years, a multi-day trip; 'ridge' is in two titles
SITE = (
    ('synx-ridge-tour', dict(title='Synthetic Ridge Tour', activity='ski', date='2026-01-17', region='Synthetic Range',
                             body='Synthetic words about a tour.', track=True)),
    ('synx-ridge-walk', dict(title='Synthetic Ridge Walk', activity='hike', date='2025-08-10', region='Synthetic Range')),
    ('synx-loop', dict(title='Synthetic Loop', activity='hike', date='2025-06-01', region='Synthetic Coast', body='A synthetic loop.')),
    ('synx-slab', dict(title='Synthetic Slab', activity='climb', date='2025-05-03', region='Synthetic Range')),
    ('synx-bowl', dict(title='Synthetic Bowl', activity='ski', date='2024-03-02', region='Synthetic Coast', track=True)),
    ('synx-hut-days', dict(title='Synthetic Hut Days', activity='ski', kind='multi-day', date='2024-02-01', end_date='2024-02-02',
                           region='Synthetic Range', days=[{'title': 'In'}, {'title': 'Out'}])),
)


def page_model():
    """The Trips page of the synthetic site as tests/trips_js_harness.js needs it for its "page:" checks: the address the
    page is served at, its <body> as a tree, the search index trips.js fetches, and what the checks press and expect
    (the reports listed, the ones a search for 'ridge' finds, a year and a region of the menus, the activity chips in
    page order, the Ski chip's label).
    Everything comes from the page and the index sitegen.pages.trips wrote; nothing is assumed. core is left as it was."""
    try:
        trips = importlib.import_module('sitegen.pages.trips')
    except ImportError as ex:
        raise AssertionError('tools/sitegen/pages/trips.py is not importable: %s' % ex)
    saved = helpers.snapshot(core)
    meta = {'hash': '', 'maps': {}, 'regions': [], 'all_regions': sorted({m['region'] for _slug, m in SITE})}
    try:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(core, '_SITE_META', [meta]):
            for slug, front in SITE:
                assert slug.startswith(PREFIX), slug
                helpers.make_trip(tmp, slug, **front)
            site = helpers.make_site(helpers.load_dir(tmp))
            pages = {p.url: p.html for p in trips.build(site)}
    finally:
        helpers.restore(saved)
    doc = Doc(pages['trips/'])
    index = json.loads(pages['trips/search.json'])
    form = doc.by_id('search')
    ski = [b for b in form.find_all('button', attrs={'role': 'radio'}) if b['data-filter'] == 'ski']
    years = [o['value'] for o in form.find('select', attrs={'name': 'year'}).find_all('option') if o['value']]
    return {
        'pathname': '/personal-website/trips/',
        'body': tree(doc.find('body')),
        'indexes': {'search.json': index},
        'slugs': [li['data-slug'] for li in doc.by_id('trx-results').find_all('li', cls='tcard')],
        'found': {'ridge': [e['s'] for e in index if 'ridge' in ' '.join(e.get(k, '') for k in 'tpkx')]},
        'year': years[-1],
        'region': [o['value'] for o in form.find('select', attrs={'name': 'region'}).find_all('option') if o['value']][0],
        'activities': [b['data-filter'] for b in form.find('div', cls='trx-acts').find_all('button', attrs={'role': 'radio'})],
        'skiLabel': ski[0].find('span', cls='fchip-l').text() if ski else '',
    }


# The page part of trips.js with its history handling changed in one way: (what the change does, the text as it is, the
# text instead), or (what the change does, (text, instead), (text, instead), ...) for lines changed together. Each is
# still valid JavaScript with the same pure helpers; only the "page:" checks can tell.
_ASK = 'historyStep(kind, entryUrl, nowUrl, next,'
_RESTORE = "      if (step.restore) history.replaceState(null, '', entryUrl);\n"
_WRITE = "      history[step.push ? 'pushState' : 'replaceState'](null, '', next + (keepHash ? location.hash : ''));\n"
_NOW = '      nowUrl = next;\n'
_SETTLE = "if (step.push || settle || kind !== 'type') entryUrl = next;"
_FIRST = 'if (entryUrl === null) entryUrl = nowUrl = next;'
_LOAD = "  apply('type', true, true);\n"
_POP_SAME = 'if (location.search === lastSearch) { entryUrl = nowUrl; return; }'
_POP_READ = '    state = parseState(location.search, allowed);\n'
_POP_ARRIVED = '    var arrived = state.sort;\n'
_POP_SORT = '    if (!searching()) sortForSearch();                // an address with sort=relevance and no search\n'
_POP_VIEW = 'entryUrl = nowUrl = address();'
_POP_IF = 'if (state.sort !== arrived) {'
_POP_REPLACE = "history.replaceState(null, '', nowUrl + location.hash);"
_POP_AGAIN = ' lastSearch = location.search; }'
_POP_TRY = '    try {\n      entryUrl'
_POP_END = '    } catch (e) { /* keep what was */ }\n'
_HASH_REST = "    if (location.hash === '#search') focusSearch();"
_HASH = '    entryUrl = nowUrl;\n' + _HASH_REST
_ON_LOAD = '\n  if (!searching()) sortForSearch();'            # two spaces: the load's; four: popstate's
_ON_POP = '\n    if (!searching()) sortForSearch();'
_SEARCHING = "if (searching()) { if (!userSort) state.sort = 'relevance'; return; }"
_SORT_TAIL = '    var kept = clearedSort(state.sort, userSort);\n    state.sort = kept[0];\n    userSort = kept[1];\n  }'
_FROM_LOCATION = 'location.pathname + location.search'
BROKEN_PAGES = (
    # ---- what kind each change is
    ('typing adds an entry',
     "      apply('type');\n    }, 150);", "      apply('pick');\n    }, 150);"),
    ('Enter is written as typing is',
     "    apply('submit');\n  });", "    apply('type');\n  });"),
    ('Enter is written as a pick is',
     "    apply('submit');\n  });", "    apply('pick');\n  });"),
    ('a filter is written as typing is',
     "state.activity = b.dataset.filter; apply('pick');", "state.activity = b.dataset.filter; apply('type');"),
    # ---- write(): the step, the entry put back, the new one
    ('the entry is never put back', _RESTORE, ''),
    ('the entry is put back after the new one is made', _RESTORE + _WRITE, _WRITE + _RESTORE),
    ('the entry is put back to the address typing gave it',
     "if (step.restore) history.replaceState(null, '', entryUrl);", "if (step.restore) history.replaceState(null, '', next);"),
    ('the entry is put back to the address it carries, not the one it stood for',
     "if (step.restore) history.replaceState(null, '', entryUrl);", "if (step.restore) history.replaceState(null, '', nowUrl);"),
    ('the step is taken from the address of the moment, not from the entry', _ASK, 'historyStep(kind, nowUrl, nowUrl, next,'),
    ('the step is taken from the entry, not from the address of the moment', _ASK, 'historyStep(kind, entryUrl, entryUrl, next,'),
    ('the step is taken from the address of the moment as the browser spells it, as in round 2',
     _ASK, 'historyStep(kind, entryUrl, %s, next,' % _FROM_LOCATION),
    ('an entry made a moment ago is forgotten',
     'next, Date.now() - lastPush < 600);', 'next, false);'),
    # ---- round 3, write(): the address the entry carries now
    ('the address the entry carries is not kept up', _NOW, ''),
    ('the address the entry carries is kept up on a new entry only', _NOW, '      if (step.push) nowUrl = next;\n'),
    ('the address the entry carries is kept up by typing only', _NOW, "      if (kind === 'type') nowUrl = next;\n"),
    ('the address the entry carries is read back from the browser', _NOW, '      nowUrl = %s;\n' % _FROM_LOCATION),
    # ---- round 3, write(): what the entry stands for
    ('what the entry stands for is read back from the browser, as in round 2',
     _SETTLE, "if (step.push || settle || kind !== 'type') entryUrl = %s;" % _FROM_LOCATION),
    ('a change that rewrites the entry made a moment ago does not become what it stands for, as in round 2',
     _SETTLE, 'if (step.push || settle) entryUrl = next;'),
    ('a pick that rewrites the entry made a moment ago does not become what it stands for',
     _SETTLE, "if (step.push || settle || kind === 'submit') entryUrl = next;"),
    ('a search that rewrites the entry made a moment ago does not become what it stands for',
     _SETTLE, "if (step.push || settle || kind === 'pick') entryUrl = next;"),
    ('every write becomes what the entry stands for, typing too', _SETTLE, 'entryUrl = next;'),
    ('only the load becomes what the entry stands for', _SETTLE, 'if (settle) entryUrl = next;'),
    ('no write becomes what the entry stands for', _SETTLE, 'void 0;'),
    ('nothing says what the entry stands for when the page opens', (_FIRST, 'void 0;'), (_LOAD, "  apply('type', true);\n")),
    ('the address is read back from the browser where it is built',
     "return location.pathname + (qs ? '?' + qs : '');", 'return %s;' % _FROM_LOCATION),
    # ---- round 3: Back and Forward (popstate)
    ('Back onto another view says nothing about its entry', _POP_VIEW, 'address();'),
    ('Back onto another view sets what the entry stands for and not what it carries', _POP_VIEW, 'entryUrl = address();'),
    ('Back onto another view sets what the entry carries and not what it stands for', _POP_VIEW, 'nowUrl = address();'),
    ("Back onto another view takes the browser's spelling of the address", _POP_VIEW, 'entryUrl = nowUrl = %s;' % _FROM_LOCATION),
    ('Back onto another view takes the address before the sort is settled', (_POP_SORT, ''), (_POP_END, _POP_END + _POP_SORT)),
    ('a popstate for the view on screen does not settle the entry', _POP_SAME, 'if (location.search === lastSearch) { return; }'),
    ('a popstate for the view on screen settles the wrong way round',
     _POP_SAME, 'if (location.search === lastSearch) { nowUrl = entryUrl; return; }'),
    ("a popstate for the view on screen takes the browser's spelling of the address",
     _POP_SAME, 'if (location.search === lastSearch) { entryUrl = %s; return; }' % _FROM_LOCATION),
    ('a popstate for the view on screen reads the address again',
     _POP_SAME, 'if (location.search === lastSearch) { entryUrl = nowUrl; }'),
    # ---- round 4: Back or Forward onto an entry whose sort is put right rewrites its address (popstate)
    ('the sort the address arrived with is taken after it is put right', _POP_ARRIVED + _POP_SORT, _POP_SORT + _POP_ARRIVED),
    ('the sort the address arrived with is the one that was on screen', (_POP_ARRIVED, ''), (_POP_READ, _POP_ARRIVED + _POP_READ)),
    ('the entry is rewritten when its sort was not put right, and not when it was', _POP_IF, 'if (state.sort === arrived) {'),
    ('every Back and Forward onto another view rewrites the entry', _POP_IF, 'if (true) {'),
    ('no Back or Forward rewrites the entry, as in round 3', _POP_IF, 'if (false) {'),
    ('the entry is rewritten whenever there is no search', _POP_IF, 'if (!searching()) {'),
    ('the entry is rewritten whenever it arrived with Best match, search or not', _POP_IF, "if (arrived === 'relevance') {"),
    ('the entry is rewritten whenever it arrived with a sort', _POP_IF, 'if (arrived !== DEFAULTS.sort) {'),
    ('the rewrite drops the fragment of the entry', _POP_REPLACE, "history.replaceState(null, '', nowUrl);"),
    ('the rewrite takes the fragment the page opened with', _POP_REPLACE, "history.replaceState(null, '', nowUrl + hash);"),
    ('the rewrite writes the address the entry arrived with',
     _POP_REPLACE, "history.replaceState(null, '', %s + location.hash);" % _FROM_LOCATION),
    ('the rewrite writes the query string the entry arrived with',
     _POP_REPLACE, "history.replaceState(null, '', location.search + location.hash);"),
    ('the rewrite makes a new entry', _POP_REPLACE, "history.pushState(null, '', nowUrl + location.hash);"),
    ('the query string on screen is not read again after the rewrite', _POP_REPLACE + _POP_AGAIN, _POP_REPLACE + ' }'),
    ('the query string on screen is read again before the rewrite, not after it',
     _POP_REPLACE + _POP_AGAIN, 'lastSearch = location.search; ' + _POP_REPLACE + ' }'),
    ('after the rewrite the page keeps the address of the view where it kept its query string',
     _POP_REPLACE + _POP_AGAIN, _POP_REPLACE + ' lastSearch = nowUrl; }'),
    ('the entry is rewritten before the page has built the address of the view',
     (_POP_VIEW, 'void 0;'), (_POP_END, '      entryUrl = nowUrl = address();\n' + _POP_END)),
    ('the entry is rewritten, and still stands for the address it arrived with',
     (_POP_SORT, ''), (_POP_IF, 'if (!searching()) sortForSearch();\n      ' + _POP_IF),
     (_POP_REPLACE, "history.replaceState(null, '', address() + location.hash);")),
    ('a rewrite the browser refuses stops the view from being put on screen (no try around it)',
     (_POP_TRY, '    {\n      entryUrl'), (_POP_END, '    }\n')),
    # ---- round 3: a year link (hashchange)
    ('the hashchange does not settle the entry', _HASH, _HASH_REST),
    ('the hashchange settles the wrong way round', _HASH, '    nowUrl = entryUrl;\n' + _HASH_REST),
    ("the hashchange takes the browser's spelling of the address", _HASH, '    entryUrl = %s;\n' % _FROM_LOCATION + _HASH_REST),
    ('neither the hashchange nor the popstate of a year link settles the entry, as in round 2',
     (_HASH, _HASH_REST), (_POP_SAME, 'if (location.search === lastSearch) { return; }')),
    # ---- round 3: the sort that goes with the search box (sortForSearch)
    ('Enter does not look at the sort',
     "    state.q = q.value;\n    sortForSearch();\n    apply('submit');", "    state.q = q.value;\n    apply('submit');"),
    ('typing does not look at the sort',
     "      state.q = q.value;\n      sortForSearch();\n      apply('type');", "      state.q = q.value;\n      apply('type');"),
    ('the load does not look at the sort', _ON_LOAD, '\n  void 0;'),
    ('the load looks at the sort of a search too', _ON_LOAD, '\n  sortForSearch();'),
    ('the load looks at the sort only when there is a search', _ON_LOAD, '\n  if (searching()) sortForSearch();'),
    ('Back does not look at the sort', _ON_POP, '\n    void 0;'),
    ('Back looks at the sort of a search too', _ON_POP, '\n    sortForSearch();'),
    ('Back looks at the sort only when there is a search', _ON_POP, '\n    if (searching()) sortForSearch();'),
    ('a box emptied by hand keeps a Best match that counts as chosen, as in round 2',
     _SORT_TAIL, '    if (!userSort) state.sort = DEFAULTS.sort;\n  }'),
    ('a box emptied by hand keeps the sort it had',
     _SORT_TAIL, '    var kept = [state.sort, userSort];\n    state.sort = kept[0];\n    userSort = kept[1];\n  }'),
    ('the sort put right for an empty box still counts as chosen',
     _SORT_TAIL, '    var kept = clearedSort(state.sort, userSort);\n    state.sort = kept[0];\n  }'),
    ('a search takes over a sort the visitor chose', _SEARCHING, "if (searching()) { state.sort = 'relevance'; return; }"),
    ('a search is not turned to best match', _SEARCHING, 'if (searching()) { return; }'),
    ('a search is turned to best match and then to what an empty box gets',
     _SEARCHING, "if (searching()) { if (!userSort) state.sort = 'relevance'; }"),
    # ---- Clear all and the search chip
    ('Clear all keeps Best match, as before',
     "    FACETS.forEach(function (k) { state[k] = DEFAULTS[k]; });\n    var kept = clearedSort(state.sort, userSort);\n"
     "    state.sort = kept[0];\n    userSort = kept[1];\n",
     "    FACETS.forEach(function (k) { state[k] = DEFAULTS[k]; });\n    if (!userSort) state.sort = DEFAULTS.sort;\n"),
    ('Clear all resets the sort and still calls it chosen',
     "    state.sort = kept[0];\n    userSort = kept[1];\n    apply('pick');", "    state.sort = kept[0];\n    apply('pick');"),
    ('the search chip keeps Best match, as before',
     "if (key === 'q') { var kept = clearedSort(state.sort, userSort); state.sort = kept[0]; userSort = kept[1]; }",
     "if (key === 'q' && !userSort) state.sort = DEFAULTS.sort;"),
    ('any chip resets the sort',
     "if (key === 'q') { var kept = clearedSort(state.sort, userSort);", "if (key) { var kept = clearedSort(state.sort, userSort);"),
)
# the cases the harness kept as known gaps in round 2 ('gap:<name>'); each is a regular check now, and no name is left
FORMER_GAPS = ('apostrophe', 'moment')
# the "page:" checks that play the sequences of round 3, by what each one shows (the label in the harness)
ROUND_3 = (
    'Enter again on a search with an apostrophe adds no entry',
    'a search after picks made within a moment goes back to the last of them',
    'a search with an apostrophe, a space, + & % # or an accent: type, pause, Enter three times is one new entry',
    'arrow keys through three activities, then a search: Back shows the last activity, the next Back the plain list',
    'a filter picked within a moment of a submitted search is part of what its entry stands for',
    "a search submitted within a moment of a filter rewrites the filter's entry, and is what it stands for",
    'a box emptied by hand leaves Newest first, and no sort in the address',
    'an address with Best match and no search opens as the plain list, with a clean address',
    'an address with Oldest first and no search keeps Oldest first',
    'a shared search without a sort opens, and comes back, in the order it was shared',
    'Back onto an address with Best match and no search shows the plain list, Newest first, at a clean address',
    'type, a year link, Enter: the entry the year link made keeps the typed search',
    'the same in a browser that sends no popstate for a fragment: the hashchange alone settles the entry',
    'a submitted search, then a year link: Back returns to the search, the next Back to the list',
    'Forward onto a search, after the same words were typed into the entry before it: Enter adds nothing',
    'type, pause, Enter, Back, Forward, Enter adds no entry',
    'type, pause, a filter, Back: the typed search without the filter',
    'a submitted search, then a filter, then Back, Back',
    'Enter in an empty box on a fresh page adds no entry',
    'two different searches submitted in a row are two entries, and Back, Back walks them',
)
# the "page:" checks of round 4, after those: Back and Forward onto an entry that carried Best match without a search
ROUND_4 = (
    'Best match picked with an empty box: Back and Forward onto its entry rewrite the address, and the menu agrees',
    'the rewrite keeps the fragment of the entry it lands on, and takes no other',
    'Back and Forward onto an entry whose sort needs no correction rewrite nothing',
    'after the rewrite, a search typed and submitted from that entry: Back lands on the plain list once',
    'after the rewrite, a jump to a fragment and back does not read the address again',
    'a rewrite the browser refuses leaves the entry as it is, and the view is put on screen all the same',
)


def changes(entry):
    """(what the change does, [(text, instead), ...]) of a BROKEN_PAGES entry."""
    return entry[0], ([entry[1:]] if isinstance(entry[1], str) else list(entry[1:]))


class TripsPageScenarioTests(unittest.TestCase):
    """The page part of trips.js, run whole by the harness on a generated Trips page: its "page:" checks play load, type,
    the pause, Enter, a filter, Clear all, a year link, Back and Forward, and read the history and the address after
    each step."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.model = page_model()
        cls.model_path = os.path.join(cls.tmp.name, 'page.json')
        with open(cls.model_path, 'w', encoding='utf-8') as fh:
            json.dump(cls.model, fh)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.node = shutil.which('node')
        if self.node is None:
            self.skipTest('node is not installed')

    def run_page(self, module=TRIPS_JS, *more):
        return subprocess.run([self.node, HARNESS, module, self.model_path] + list(more), cwd=TESTS, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, timeout=60)

    def passed(self, r):
        m = re.search(r'trips_js_harness: (\d+) checks passed', r.stdout)
        self.assertIsNotNone(m, 'no "N checks passed" line:\n%s\n%s' % (r.stdout, r.stderr))
        return int(m.group(1))

    def test_the_model_is_a_generated_trips_page(self):
        # the fixture: six reports, of which a search for 'ridge' finds two; every control the scenarios press is there
        model = self.model
        self.assertEqual(sorted(model['slugs']), sorted(slug for slug, _front in SITE))
        self.assertEqual(sorted(model['found']['ridge']), ['synx-ridge-tour', 'synx-ridge-walk'])
        self.assertEqual((model['year'], model['region'], model['skiLabel']), ('2024', 'synthetic-range', core.ACT['ski'][0]))
        self.assertEqual((model['body']['tag'], model['body']['attrs'].get('class')), ('body', 'p-trips'))
        # three activities besides All, in the order of the chips (the arrow keys of round 3 go through them), and a
        # link of the browse row to each year, with the heading it names
        self.assertEqual(model['activities'], ['all', 'ski', 'climb', 'hike'])
        html = json.dumps(model['body'])
        for year in ('2026', '2025', '2024'):
            self.assertEqual(html.count('"href": "#y-%s"' % year), 1)
            self.assertEqual(html.count('"id": "y-%s"' % year), 1)
        for slug in model['slugs']:
            self.assertFalse(os.path.lexists(os.path.join(ROOT, 'rendered', 'trips', slug)), 'fixture slug %r names a real trip' % slug)
        self.assertEqual(core._REGION_PAGES, {})                 # page_model put core back

    def test_the_history_scenarios_play_out_on_a_generated_page(self):
        # fix C: load, type (pause), Enter, Back; load, type, Enter at once, Back; load, type, a filter, Back; Enter
        # twice; what Clear all leaves as the sort; and the sequences of round 3 (ROUND_3) and round 4 (ROUND_4). The
        # harness asserts the history and the address at each step
        r = self.run_page()
        self.assertEqual(r.returncode, 0, 'the "page:" checks failed:\n%s\n%s' % (r.stdout, r.stderr))
        pure = subprocess.run([self.node, HARNESS], cwd=TESTS, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=60)
        self.assertEqual(self.passed(r) - self.passed(pure), 16 + len(ROUND_3) + len(ROUND_4), 'the "page:" checks did not all run')

    def page_checks(self):
        """(the harness's text, [(label, body), ...] of its "page:" checks, in the order of the table)."""
        with open(HARNESS, encoding='utf-8') as fh:
            harness = fh.read()
        table = harness[harness.index('  const pageChecks = {'):harness.index('  const GAPS = {')]
        heads = list(re.finditer(r"(?m)^    '((?:[^'\\\n]|\\.)*)': \(\) => ", table))
        ends = [m.start() for m in heads[1:]] + [len(table)]
        return harness, [(m.group(1).replace("\\'", "'"), table[m.end():end]) for m, end in zip(heads, ends)]

    def test_the_round_3_sequences_are_checks_of_the_harness(self):
        # each sequence the gate asked for is a check of its own, named for what it shows, in the table every run with a
        # page model goes through (the run itself is the test above)
        harness, checks = self.page_checks()
        labels = [label for label, _body in checks]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(labels[16:16 + len(ROUND_3)], list(ROUND_3))
        self.assertEqual(len(labels), 16 + len(ROUND_3) + len(ROUND_4))
        # and all of them are run: none is behind an argument
        self.assertIn("Object.keys(pageChecks).forEach((label) => check('page: ' + label, pageChecks[label]));", harness)

    def test_the_round_4_sequences_are_checks_of_the_harness(self):
        # the sequences of round 4 are the last checks of the table, each named for what it shows
        harness, checks = self.page_checks()
        self.assertEqual([label for label, _body in checks][-len(ROUND_4):], list(ROUND_4))
        # what each of them reads after a step: every entry, the position, the address, the Sort menu, the list's order
        self.assertIn('const seen = (page) => [page.stack(), page.at(), page.address(), page.sort(), page.order()];', harness)
        self.assertEqual(len(re.findall(r'(?m)^  const seen = ', harness)), 1)
        # the stand-in counts the replaceState calls and can refuse writes (tests/page_standin.js since round 6), and
        # the harness reads the order of the list (none of the three existed before round 4)
        with open(STANDIN, encoding='utf-8') as fh:
            standin = fh.read()
        self.assertRegex(standin, r"(?m)^      replaces: \(\) => hist\.calls\.filter\(\(c\) => c\.indexOf\('replace '\) === 0\)\.length,")
        self.assertRegex(harness, r'(?m)^    order: \(\) => \{$')
        self.assertRegex(standin, r'(?m)^      refuse: \(on\) => \{ hist\.refused = !!on; \},')
        self.assertEqual(len(re.findall(r'(?m)^        refusal\(\);$', standin)), 2)             # pushState and replaceState both throw
        for label, body in checks[-len(ROUND_4):]:
            with self.subTest(check=label):
                # every Back and Forward is followed, before the next one, by a reading of all five; or, for a Back off
                # the page's first entry, by the page having been left
                moves = [m.start() for m in re.finditer(r'\b\w+\.(?:back|forward)\(\);', body)]
                self.assertGreaterEqual(len(moves), 2)
                read = [m.start() for m in re.finditer(r'\bdeq\(seen\(\w+\), |\beq\(\w+\.left\(\), true\b', body)]
                unread = [body[at:at + 20] for at, nxt in zip(moves, moves[1:] + [len(body)]) if not any(at < r < nxt for r in read)]
                self.assertEqual(unread, [], 'Back or Forward without a reading of the page after it')
        # the check that says a landing wrote nothing compares every call and the count of replaceState calls
        nothing = dict(checks)[ROUND_4[2]]
        self.assertIn("deq([page.calls(), page.replaces(), page.left()], [calls, replaces, false], 'Back wrote to the history: ' + name);", nothing)
        self.assertIn("deq([page.calls(), page.replaces()], [calls, replaces], 'Forward wrote to the history: ' + name);", nothing)

    def test_the_scenarios_notice_a_page_that_breaks_the_history_rule(self):
        # the harness itself: the real script with its history handling changed in one way fails a "page:" check, and
        # none of the checks of the pure helpers (which are untouched)
        with open(TRIPS_JS, encoding='utf-8') as fh:
            src = fh.read()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        shutil.copy(EXPLORE_JS, os.path.join(tmp.name, 'explore.js'))        # trips.js asks for it beside itself under node
        self.assertEqual(len(set(changes(entry)[0] for entry in BROKEN_PAGES)), len(BROKEN_PAGES))
        for n, entry in enumerate(BROKEN_PAGES):
            what, pairs = changes(entry)
            with self.subTest(broken=what):
                broken = src
                for old, new in pairs:
                    self.assertEqual(src.count(old), 1, 'assets/js/pages/trips.js no longer has this line once: %r' % old)
                    broken = broken.replace(old, new)
                path = os.path.join(tmp.name, 'trips_%d.js' % n)
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(broken)
                self.assertEqual(self.run_node_check(path), 0)
                r = self.run_page(path)
                self.assertNotEqual(r.returncode, 0, 'the harness passed a page where %s' % what)
                self.assertIn('FAIL page: ', r.stderr)
                self.assertEqual(len(re.findall(r'(?m)^FAIL ', r.stderr)), 1)
                self.assertNotIn('checks passed', r.stdout)
        # and the unchanged copy passes from there too
        path = os.path.join(tmp.name, 'trips.js')
        shutil.copy(TRIPS_JS, path)
        self.assertEqual(self.run_page(path).returncode, 0)

    def run_node_check(self, path):
        return subprocess.run([self.node, '--check', path], cwd=TESTS, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=60).returncode

    def test_the_stand_in_for_the_browser_is_the_shared_one(self):
        # round 6: the document, the history, the location, the timers and the clock the page is run against are
        # tests/page_standin.js, which the tick list harness uses too; this harness keeps no copy of any of it
        with open(HARNESS, encoding='utf-8') as fh:
            harness = fh.read()
        with open(STANDIN, encoding='utf-8') as fh:
            standin = fh.read()
        self.assertEqual(harness.count("const standin = require('./page_standin.js');"), 1)
        self.assertEqual(len(re.findall(r'\bstandin\.open\(', harness)), 1)
        self.assertIn("const tab = standin.open(MODEL, [['explore.js', EXPLORE], [MODULE, SOURCE]], opts);", harness)
        for own in (r'\bclass\s+\w+', r"require\('vm'\)", r'\bvm\.', r'\bpushState:', r'\breplaceState:', r'\bnew URL\(', r'\bsetTimeout:'):
            with self.subTest(own=own):
                self.assertNotRegex(harness, own)
                self.assertRegex(standin, own)
        self.assertTrue(standin.endswith('\nmodule.exports = { open: open };\n'))       # all it hands out
        # the page is given explore.js as the module itself asks for it under node: the file beside it
        self.assertIn("const EXPLORE = MODEL ? fs.readFileSync(EXPLORE_JS, 'utf8') : '';", harness)
        self.assertRegex(harness, r"(?m)^const BESIDE = path\.join\(path\.dirname\(MODULE\), 'explore\.js'\);$")
        self.assertEqual(self.run_node_check(STANDIN), 0)

    def test_no_case_is_left_as_a_known_gap(self):
        # round 2 kept two cases the page did not handle as expected failures ('gap:apostrophe', 'gap:moment'). Both are
        # regular checks now (the first two of ROUND_3), so the harness knows no gap by those names, nor by any other,
        # and refuses the argument
        for name in FORMER_GAPS + ('no-such-case',):
            with self.subTest(gap=name):
                r = self.run_page(TRIPS_JS, 'gap:' + name)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn('unknown argument: gap:' + name, r.stderr)
                self.assertEqual(re.findall(r'(?m)^FAIL ', r.stderr), [])            # refused, not failed at a check
                self.assertNotIn('checks passed', r.stdout)
        with open(HARNESS, encoding='utf-8') as fh:
            self.assertRegex(fh.read(), r'(?m)^  const GAPS = \{\};$')


if __name__ == '__main__':
    unittest.main()
