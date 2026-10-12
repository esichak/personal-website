"""Phase 2T: the pure functions of assets/js/pages/explore.js (norm, tokens, parseState, serialize, chipLabel) and
assets/js/pages/ticklist.js (state keys and defaults, the scope predicate, the sort comparators, chipLabel), run under node
through tests/ticklist_js_harness.js. Skipped when node is not installed: node is a dev-only convenience, the production
build never runs it. Also checks, by reading the sources, that both files export for node before touching the DOM and that
no untrusted text can reach innerHTML. Phase 4 adds goalShown, the predicate a goal card is shown by: the harness is
also run against the real module with one filter switched off at a time, and must fail. It also adds adoptForm (what
the page takes over from a form the visitor used before the script arrived): the harness is run against the real
module with adoptForm wrong in one way at a time, and the page's own lines that call it are read from the source.

Round 6 of the review gate: the Tick list follows the Trips page's rule for history entries. The rule itself,
historyStep(kind, entry, now, next, recent), is defined in explore.js and shared by the two pages; this harness holds
its truth table against explore.js, and is run against explore.js with historyStep wrong in one way at a time
(js_fixtures.WRONG_HISTORY_STEPS, the modules tests/test_trips_js.py puts beside a copy of trips.js). The page part of
ticklist.js keeps two addresses, both built by address() in the page's own spelling and never read back from
location: entryUrl, what this history entry stood for when the visitor last settled on it, and nowUrl, what it carries
at this moment. write(kind, keepHash, settle) asks X.historyStep with them and the next address, puts the entry back
before it adds one, and settles the entry on every change but typing; Enter is 'submit', the typing pause 'type',
every filter, the scope, the sort, the view, a chip's remove button and Clear all 'pick', the load 'type' with the
fragment kept and the entry settled; Back and Forward (popstate) read the address again and set both addresses from
it; a jump to a fragment (hashchange) settles the entry on the view on screen. Three kinds of test, as for trips.js:
the lines themselves, read from the source (TickListPageSourceTests); the whole of ticklist.js run by the harness
against a stand-in for the browser (tests/page_standin.js, shared with tests/trips_js_harness.js) on a Tick list page
that sitegen.pages.ticklist generated from a synthetic site (page_model), with a visitor's typing, Enter, filters, a
jump to a fragment, Back and Forward played on it and the history list, the position, the address, the box and the
controls read after every step (SCENARIOS, the sequences (a) to (m) the gate asked for); and that harness run against
the page with each of those lines changed in one way (BROKEN_PAGES), which it has to reject at a "page:" check. The
stand-in is not a browser: it spells addresses as the URL Standard does and keeps a list of entries, and models neither
layout nor focus nor the back/forward cache.
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

HARNESS = os.path.join(TESTS, 'ticklist_js_harness.js')
STANDIN = os.path.join(TESTS, 'page_standin.js')           # the stand-in for the browser, shared with the trips harness
EXPLORE_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'explore.js')
TICKLIST_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'ticklist.js')

# an explore module with the right exports but wrong answers: the harness must reject it
BAD_EXPLORE = ("module.exports = {norm: function (s) { return s; }, tokens: function () { return []; },"
               " parseState: function () { return {}; }, serialize: function () { return ''; }, chipLabel: function () { return ''; },"
               " historyStep: function () { return {}; }};\n")


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

    def test_harness_rejects_a_wrong_history_rule(self):
        # round 6: explore.js with its historyStep wrong in one way each (the modules tests/test_trips_js.py puts beside
        # a copy of trips.js): the truth table this harness holds against explore.js must notice every one of them
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.assertGreaterEqual(len(js_fixtures.WRONG_HISTORY_STEPS), 11)
        for n, (what, body) in enumerate(js_fixtures.WRONG_HISTORY_STEPS):
            with self.subTest(wrong=what):
                folder = os.path.join(tmp.name, 'wrong_%d' % n)
                os.mkdir(folder)
                r = self.run_node(HARNESS, js_fixtures.wrong_explore(folder, body), TICKLIST_JS)
                self.assertNotEqual(r.returncode, 0, 'the harness passed a historyStep that %s' % what)
                self.assertIn('FAIL historyStep', r.stderr)
                self.assertEqual(len(re.findall(r'(?m)^FAIL ', r.stderr)), 1)
                self.assertNotIn('checks passed', r.stdout)
        # the same module around the right function passes: it is the answers that are rejected
        folder = os.path.join(tmp.name, 'right')
        os.mkdir(folder)
        r = self.run_node(HARNESS, js_fixtures.wrong_explore(folder, js_fixtures.RIGHT_HISTORY_STEP), TICKLIST_JS)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('checks passed', r.stdout)

    def test_the_history_rule_is_held_to_its_whole_truth_table_here(self):
        # the rule is tested where it is defined: through Explore.historyStep, every kind against every way the three
        # addresses can relate, with and without an entry made a moment ago
        harness = source(HARNESS)
        rule = harness[harness.index("check('historyStep is a function of five arguments'"):harness.index('// ---------------------------------------------------------------- the page part')]
        self.assertNotIn('TKL.historyStep', harness)
        self.assertGreaterEqual(len(re.findall(r'\bX\.historyStep\(', rule)), 3)
        self.assertIn("const KINDS = ['type', 'pick', 'submit'];", harness)
        self.assertEqual(len(re.findall(r"(?m)^  '[^'\n]+': \[(?:HOME|TYPED|MORE), (?:HOME|TYPED|MORE), (?:HOME|TYPED|MORE)\],$", harness)), 5)
        table = re.search(r"const table = \{\n    type: (\[.*\]),\n    pick: (\[.*\]),\n    submit: (\[.*\]),\n  \};", rule)
        self.assertIsNotNone(table, 'the truth table of historyStep is gone from the harness')
        rows = [json.loads(row) for row in table.groups()]
        self.assertEqual(rows, [[[False, False]] * 5, [[True, False]] * 5,
                                [[False, False], [True, False], [False, False], [True, True], [True, True]]])
        self.assertIn("deq(hstep(kind, ...SHAPES[name], true), [false, false], kind + ': ' + name + ', an entry just made');", rule)
        self.assertGreaterEqual(len(re.findall(r"(?m)^check\('historyStep", harness)), 5)
        # it is the table tests/trips_js_harness.js holds TRX.historyStep to (the same function): the same five ways
        # the addresses relate, in the same order, and the same answers
        trips = source(os.path.join(TESTS, 'trips_js_harness.js'))
        shapes = r"(?m)^  '([^'\n]+)': \[(HOME|TYPED|MORE), (HOME|TYPED|MORE), (HOME|TYPED|MORE)\],$"
        self.assertEqual(re.findall(shapes, harness), re.findall(shapes, trips))
        theirs = re.search(table.re.pattern, trips)
        self.assertIsNotNone(theirs, 'the truth table of historyStep is gone from the trips harness')
        self.assertEqual([json.loads(row) for row in theirs.groups()], rows)

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
    text; that the page has no index to fetch, so nothing of trips.js's retry rule applies to it; and, since round 6 of
    the gate, the lines that keep the history: the two addresses, write(), what kind each change of view is, popstate
    and hashchange. Nothing here needs node."""

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
        self.assertLess(start.start(), page.index("apply('type', true, true)"))       # the load: the first write of the page
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

    # ------------------------------------------------------------ the history (round 6: the rule of trips.js)

    def code(self):
        """The page part without its // comments (several of them name write() and the addresses)."""
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
    FIRST = 'if (entryUrl === null) entryUrl = nowUrl = next;'
    ASK = 'var step = X.historyStep(kind, entryUrl, nowUrl, next, Date.now() - lastPush < 600);'
    RESTORE = "if (step.restore) history.replaceState(null, '', entryUrl);"
    WRITTEN = "history[step.push ? 'pushState' : 'replaceState'](null, '', next + (keepHash ? location.hash : ''));"
    TIMED = 'if (step.push) lastPush = Date.now();'
    NOW = 'nowUrl = next;'
    SETTLE = "if (step.push || settle || kind !== 'type') entryUrl = next;"
    LOAD = "apply('type', true, true);"
    POP = "window.addEventListener('popstate', function () {"
    HASHCHANGE = "window.addEventListener('hashchange', function () {"

    def test_write_asks_the_shared_rule_and_puts_the_entry_back_before_it_adds_one(self):
        code = self.code()
        lines = self.lines_of(self.WRITE)
        body = self.body_of(self.WRITE)
        # the whole of write(), line by line. The new address is address()'s (a state that cannot be written, a lone
        # surrogate, is left alone); the first write says what the entry stands for; the step is the shared rule's
        # answer; then, in one try, the entry is put back, the address written, a new entry timed, and the two
        # addresses the page keeps brought up to date
        self.assertEqual(lines, ['var next;', 'try { next = address(); } catch (e) { return; }', self.FIRST, self.ASK,
                                 'try {', self.RESTORE, self.WRITTEN, self.TIMED, self.NOW, self.SETTLE,
                                 '} catch (e) { /* file:// */ }'])
        # the step is X.historyStep's answer for: the kind, what the entry stood for, the address it carries at this
        # moment, the new address, and whether an entry was made within the last 600 ms. Asked once, here; the rule
        # is explore.js's, and ticklist.js has no copy of it under any name
        src = self.pure + self.page
        self.assertEqual(len(re.findall(r'\bhistoryStep\b', re.sub(r'(?m)(^|\s)//.*$', r'\1', src))), 1)
        self.assertEqual(len(re.findall(r'\bX\.historyStep\(', body)), 1)
        self.assertNotRegex(src, r'\bfunction\s+historyStep\b|\bhistoryStep\s*[=:]')
        self.assertEqual(re.findall(r'(?m)^  var X = (.*?);', src),
                         ["(typeof module === 'object' && module && module.exports) ? require('./explore.js') : window.Explore"])
        self.assertEqual(re.findall(r'\bX\.historyStep\(([^()]*)\(\)([^()]*)\)', body), [('kind, entryUrl, nowUrl, next, Date.now', ' - lastPush < 600')])
        # the entry is put back to what it stood for, before the write (the new address, in WRITTEN, is the one the
        # step was asked about)
        self.assertLess(lines.index(self.ASK), lines.index(self.RESTORE))
        self.assertEqual(lines.index(self.WRITTEN), lines.index(self.RESTORE) + 1)
        self.assertEqual(re.findall(r"history\.replaceState\(null, '', (\w+)\)", body), ['entryUrl'])
        # these are the only two history calls of the page, and write()'s is its one pushState: an entry is made here
        # and nowhere else. Nothing else is written to the address
        self.assertEqual(len(re.findall(r'\bhistory\s*[.\[]', body)), 2)
        self.assertEqual(len(re.findall(r'\bhistory\b', code)), 2)
        self.assertEqual(len(re.findall(r'\b(?:pushState|replaceState)\b', code)), 3)
        self.assertEqual(len(re.findall(r'\bpushState\b', code)), 1)
        self.assertNotRegex(code, r'\blocation\s*(?:\.\s*(?:href|search|hash|pathname)\s*)?=(?!=)|\blocation\s*\.\s*(?:assign|replace)\s*\(')
        # a new entry is timed, for the 'made a moment ago' rule
        self.assertEqual(len(re.findall(r'\blastPush\s*=(?!=)', code)), 2)        # that line and its declaration (0)
        self.assertRegex(code, r'(?m)^  var timer = null, lastPush = 0;$')
        self.assertEqual(len(re.findall(r'\bDate\.now\(\)', code)), 2)

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
                                 (['entryUrl', 'nowUrl'], 'address()'),                   # popstate
                                 (['entryUrl'], 'nowUrl')])                               # hashchange
        self.assertRegex(code, r'(?m)^  var entryUrl = null, nowUrl = null;$')
        self.assertEqual((len(re.findall(r'\bentryUrl\s*=(?!=)', code)), len(re.findall(r'\bnowUrl\s*=(?!=)', code))), (5, 4))
        self.assertEqual(re.findall(r'\bnext\s*=(?!=)\s*([^;]+);', self.body_of(self.WRITE)), ['address()'])
        # what the page does read from location: the fragment (at load, on the load's write, for the Search link of
        # the header), the pathname (address()) and the query string, for the state alone: on load and on Back
        self.assertEqual(sorted(set(re.findall(r'\blocation\s*\.\s*(\w+)', code))), ['hash', 'pathname', 'search'])
        self.assertEqual(len(re.findall(r'\blocation\.search\b', code)), 2)
        self.assertEqual(len(re.findall(r'\bparseState\(location\.search, allowed\)', code)), 2)
        self.assertEqual(len(re.findall(r'\blocation\.hash\b', code)), 3)
        self.assertEqual(len(re.findall(r'\blocation\b', code)), 6)

    def test_write_settles_the_entry_on_every_change_but_typing(self):
        code = self.code()
        lines = self.lines_of(self.WRITE)
        body = self.body_of(self.WRITE)
        for line in (self.FIRST, self.NOW, self.SETTLE):
            self.assertEqual(lines.count(line), 1, line)
        # the first write sets both from the view the page opened on, before the step is asked for
        self.assertLess(lines.index(self.FIRST), lines.index(self.ASK))
        # then, once the address is written: on every write the address the entry carries now (a line of its own, under
        # no condition); and on a push, on the load (settle) and for every kind but 'type', what the entry stands for
        written = lines.index(self.WRITTEN)
        self.assertLess(written, lines.index(self.NOW))
        self.assertLess(lines.index(self.NOW), lines.index(self.SETTLE))
        parts = re.fullmatch(r'if \((.*)\) entryUrl = next;', self.SETTLE)
        self.assertEqual(parts.group(1).split(' || '), ['step.push', 'settle', "kind !== 'type'"])
        # both in the try of the write itself, to its end: a write the browser refuses (file://) changes neither
        self.assertEqual(lines[written - 2:written], ['try {', self.RESTORE])
        self.assertEqual(lines[lines.index(self.SETTLE) + 1:], ['} catch (e) { /* file:// */ }'])
        self.assertEqual((lines.count('try {'), len(re.findall(r'\bcatch\b', body))), (1, 2))
        # and nothing else in write() gives either a value
        self.assertEqual((len(re.findall(r'\bentryUrl\s*=(?!=)', body)), len(re.findall(r'\bnowUrl\s*=(?!=)', body))), (2, 2))
        # settle is the load's alone: the one call that passes it (and the one that keeps the fragment)
        self.assertEqual(re.findall(r'(?<![\w.])apply\(([^()]*,[^()]*)\)', code), ['kind, keepHash, settle', "'type', true, true"])
        self.assertEqual(re.findall(r'(?<![\w.])write\(([^()]*)\)', code), ['kind, keepHash, settle', 'kind, keepHash, settle'])
        # apply() puts the view on screen and then writes: a write that is refused has stopped nothing
        self.assertEqual(code.count('  function apply(kind, keepHash, settle) { setControls(); render(); write(kind, keepHash, settle); }\n'), 1)

    def test_every_change_of_view_says_what_kind_it_is(self):
        code = self.code()
        calls = re.findall(r'(?<![\w.])apply\(([^()]*)\)', code)
        self.assertEqual(calls.count('kind, keepHash, settle'), 1)                     # the definition
        calls.remove('kind, keepHash, settle')
        self.assertEqual(sorted(calls), sorted(["'pick'"] * 7 + ["'submit'", "'type'", "'type', true, true"]))
        # no call says true or false any more (the old apply(push, keepHash)), and Enter no longer asks whether the
        # words changed: the rule decides
        self.assertNotRegex(code, r'(?<![\w.])(?:apply|write)\(\s*(?:true|false|changed|push)\b')
        self.assertNotRegex(code, r'\bchanged\b')
        # each handler, whole: Enter in the search box (which also stops the form and the typing timer); the typing
        # timer; a pick: the activity, the scope, the view, the five menus (the sort among them), the route switch
        for line in ("form.addEventListener('submit', function (e) { e.preventDefault(); clearTimeout(timer); state.q = q.value; apply('submit'); });",
                     "q.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { state.q = q.value; apply('type'); }, 150); });",
                     "actBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.activity === b.dataset.filter) return; "
                     "state.activity = b.dataset.filter; apply('pick'); }); });",
                     "scopeBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.scope === b.dataset.scope) return; "
                     "state.scope = b.dataset.scope; apply('pick'); }); });",
                     "viewBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.view === b.dataset.view) return; "
                     "state.view = b.dataset.view; apply('pick'); }); });",
                     "['region', 'status', 'priority', 'month', 'sort'].forEach(function (k) { if (sel[k]) sel[k].addEventListener('change', function () { "
                     "state[k] = sel[k].value; apply('pick'); }); });",
                     "if (gpxBtn) gpxBtn.addEventListener('click', function () { state.gpx = !state.gpx; apply('pick'); });",
                     # Clear all (its button, and the empty state's 'Clear filters') and a chip's remove button
                     "function clearAll() { state.q = ''; FACETS.forEach(function (k) { state[k] = DEFAULTS[k]; }); apply('pick'); q.focus(); }",
                     "clearBtn.addEventListener('click', clearAll);",
                     "Array.prototype.forEach.call(noneEl.querySelectorAll('[data-clear]'), function (b) { b.addEventListener('click', clearAll); });",
                     "b.addEventListener('click', function () { state[key] = DEFAULTS[key]; apply('pick'); q.focus(); });"):
            with self.subTest(handler=line[:44]):
                self.assertEqual(code.count('  ' + line + '\n'), 1)
        # the load: 'type', the fragment kept, the entry settled; the page's last write-making statement, after every
        # listener is in place
        self.assertRegex(code, r"(?m)^  apply\('type', true, true\);$")
        at = code.index('\n  ' + self.LOAD + '\n')
        for listener in ("form.addEventListener('submit'", "q.addEventListener('input'", self.POP, self.HASHCHANGE):
            self.assertLess(code.index(listener), at, listener)
        self.assertNotRegex(code[at + len(self.LOAD) + 4:], r'\b(?:apply|write|history)\b')

    def test_back_forward_and_a_jump_to_a_fragment_settle_the_entry(self):
        code = self.code()
        # popstate: the state is read from the address again (also when only the fragment changed, as before round 6),
        # both addresses are that view's, as address() builds them, and the view is put on screen
        pop = self.lines_of(self.POP)
        self.assertEqual(pop, ['state = parseState(location.search, allowed);',
                               'try { entryUrl = nowUrl = address(); } catch (e) { /* keep what was */ }',
                               'setControls();', 'render();'])
        # coming back goes through neither write() nor apply(): no step is asked for, no entry is made, nothing is
        # written to the history
        self.assertNotRegex(' '.join(pop), r'\b(?:write|apply|historyStep|pushState|replaceState|history)\b')
        # hashchange: a jump to a fragment made a new entry for the view on screen
        self.assertEqual(self.lines_of(self.HASHCHANGE), ['entryUrl = nowUrl;', "if (location.hash === '#search') focusSearch();"])
        # one listener each
        for event in ('popstate', 'hashchange'):
            self.assertEqual(code.count("window.addEventListener('%s'" % event), 1)
        # the Tick list has no sort that follows the search, so nothing of that part of trips.js is here: no sort to
        # put right, no address to rewrite on the way back, no query string kept to tell a jump from a change of view
        self.assertNotRegex(self.pure + self.page, r'\b(?:sortForSearch|clearedSort|userSort|lastSearch|ownSort|arrived)\b')


# ---------------------------------------------------------------- the page part of ticklist.js, on a generated Tick list page

PREFIX = 'syng-'                  # every fixture slug starts with it; no real trip's slug does
# (slug, front matter, the goal's sidecar on top of goals.defaults()): three activities (the arrow keys of the activity
# chips pass through them), two regions and a goal without one, four statuses, three priorities, target months, goals
# with and without a route file; one completed (by a logged outing) and one archived, which the default scope leaves
# out. 'ridge' is in three titles, one of them the archived goal's
SITE = (
    ('syng-ridge-traverse', dict(title='Synthetic Ridge Traverse', activity='hike', region='Synthetic Range', track=True,
                                 body='Synthetic notes about a traverse.'),
     dict(status='idea', priority='high', added_at='2026-03-01', target_months=[7, 8], why='A synthetic reason.')),
    ('syng-ridge-couloir', dict(title='Synthetic Ridge Couloir', activity='ski', region='Synthetic Range', track=True),
     dict(status='shortlisted', priority='high', added_at='2026-05-01', target_months=[4])),
    ('syng-bowl', dict(title='Synthetic Bowl', activity='ski', region='Synthetic Coast'),
     dict(status='researching', priority='normal', added_at='2026-02-01', target_months=[1, 2])),
    ('syng-tower', dict(title='Synthetic Tower', activity='climb', region='Synthetic Coast'),
     dict(status='idea', priority='normal', added_at='2026-01-15', target_months=[9])),
    ('syng-slab', dict(title='Synthetic Slab', activity='climb', region='Synthetic Range', track=True),
     dict(status='shortlisted', priority='someday', added_at='2025-12-01')),
    ('syng-loop', dict(title='Synthetic Loop', activity='hike', track=True),
     dict(status='idea', priority='someday')),
    ('syng-summit', dict(title='Synthetic Summit', activity='hike', region='Synthetic Coast'),
     dict(status='completed', priority='high', added_at='2025-06-01',
          outings=[{'outcome': 'completed', 'date': '2026-08-30', 'report_slug': None, 'note': ''}])),
    ('syng-old-ridge', dict(title='Synthetic Old Ridge Plan', activity='ski', region='Synthetic Range'),
     dict(status='researching', priority='normal', archived=True, added_at='2024-02-02')),
)


def page_model():
    """The Tick list page of the synthetic site as tests/ticklist_js_harness.js needs it for its "page:" checks: the
    address the page is served at, its <body> as a tree, and what the checks press and expect, all read from the page
    sitegen.pages.ticklist wrote: the goals listed, the ones whose searchable text holds 'ridge', the activity chips,
    the scopes and the views in page order, the values each menu offers, the labels the chips are named with, and the
    page's link to one of its own fragments (the skip link). The site dict is tools/build.py's own (site_of), as in
    tests/test_ticklist_page.py. core is left as it was."""
    try:
        ticklist = importlib.import_module('sitegen.pages.ticklist')
        goals = importlib.import_module('goals')
        build = importlib.import_module('build')
    except ImportError as ex:
        raise AssertionError('the tick list page cannot be generated: %s' % ex)
    saved = helpers.snapshot(core)
    meta = {'hash': '', 'maps': {}, 'regions': [], 'all_regions': sorted({m['region'] for _slug, m, _goal in SITE if m.get('region')})}
    try:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(core, '_SITE_META', [meta]):
            for slug, front, goal in SITE:
                assert slug.startswith(PREFIX), slug
                folder = helpers.make_trip(tmp, slug, kind='planned', **front)
                with open(os.path.join(folder, 'goal.json'), 'w', encoding='utf-8') as fh:
                    json.dump(dict(goals.defaults(), **goal), fh)
            site = build.site_of(helpers.load_dir(tmp))
            core.register_site(site)
            pages = {p.url: p.html for p in ticklist.build(site)}
    finally:
        helpers.restore(saved)
    doc = Doc(pages['tick-list/'])
    form = doc.by_id('search')
    radios = form.find_all('button', attrs={'role': 'radio'})
    cards = doc.by_id('tkl-results').find_all('li', cls='gcard')
    menus = {sel['name']: [(o['value'], o.text()) for o in sel.find_all('option')] for sel in form.find_all('select')}
    labels = {b['data-filter']: b.find('span', cls='fchip-l').text() for b in radios if b['data-filter'] is not None}
    links = sorted({a['href'] for a in doc.find('body').find_all('a') if (a['href'] or '').startswith('#')})
    return {
        'pathname': '/personal-website/tick-list/',
        'body': tree(doc.find('body')),
        'indexes': {},                                    # the tick list fetches nothing
        'slugs': [li['data-slug'] for li in cards],
        'found': {'ridge': [li['data-slug'] for li in cards if 'ridge' in li['data-text']]},
        'activities': [b['data-filter'] for b in radios if b['data-filter'] is not None],
        'scopes': [b['data-scope'] for b in radios if b['data-scope'] is not None],
        'views': [b['data-view'] for b in radios if b['data-view'] is not None],
        'menus': {name: [value for value, _label in options] for name, options in menus.items()},
        'labels': {'activity': labels, 'region': dict(menus['region']), 'status': dict(menus['status']),
                   'priority': dict(menus['priority']), 'month': dict(menus['month'])},
        'fragments': links,
    }


# The "page:" checks of the harness after the one of the model itself, by the sequence of round 6 of the gate each one
# plays, (a) to (m), in the harness's order
MODEL_CHECK = 'the model is the page the script expects'
SCENARIOS = (
    ('a', ('the load rewrites its own entry and adds none, and keeps a fragment',)),
    ('b', ('type, pause, Enter, Back: one new entry, and Back shows the list from before the search',
           'typing alone rewrites the entry after each pause, and never adds one')),
    ('c', ('type and Enter at once, Back',)),
    ('d', ('a search with an apostrophe, a curly one, a space, + & % # or an accent: type, pause, Enter three times is one new entry',)),
    ('e', ('arrow keys through three activities, then a search: Back shows the last activity, the next Back the list the page opened on',
           'arrow keys through three scopes, then a search: Back shows the last scope, the next Back the list the page opened on',
           'picks within a moment make one entry, later ones one each',
           'a filter picked within a moment of a submitted search is part of what its entry stands for',
           "a search submitted within a moment of a filter rewrites the filter's entry, and is what it stands for")),
    ('f', ('type, pause, pick a filter, Back: the typed search without the filter',)),
    ('g', ('a submitted search, then a filter, then Back, Back',)),
    ('h', ('Enter in an empty box on a fresh page adds no entry',)),
    ('i', ('two different searches submitted in a row are two entries, and Back, Back walks them',)),
    ('j', ('each kind of control makes one entry: an activity, the scope, a menu, the route switch, the view, a chip removed, Clear all',)),
    ('k', ('Back onto an entry, then a search from there, Back',)),
    ('l', ('type, a jump to a fragment, Enter: the entry the jump made keeps the typed search',
           'the same in a browser that sends no popstate for a fragment: the hashchange alone settles the entry')),
    ('m', ('a browser that refuses every write to the history (a page opened from a file): each view is put on screen all the same',)),
)
LABELS = [label for _letter, labels in SCENARIOS for label in labels]

# The page part of ticklist.js with its history handling changed in one way: (what the change does, the text as it is,
# the text instead), or (what the change does, (text, instead), (text, instead), ...) for lines changed together. Each
# is still valid JavaScript with the same pure helpers; only the "page:" checks can tell.
_SUBMIT = "state.q = q.value; apply('submit'); });"
_TYPING = "state.q = q.value; apply('type'); }, 150); });"
_ACTIVITY = "state.activity = b.dataset.filter; apply('pick'); }); });"
_SCOPE = "state.scope = b.dataset.scope; apply('pick'); }); });"
_VIEW = "state.view = b.dataset.view; apply('pick'); }); });"
_MENU = "state[k] = sel[k].value; apply('pick'); }); });"
_ROUTE = "state.gpx = !state.gpx; apply('pick'); });"
_CHIP = "state[key] = DEFAULTS[key]; apply('pick'); q.focus(); });"
_CLEAR = "FACETS.forEach(function (k) { state[k] = DEFAULTS[k]; }); apply('pick'); q.focus(); }"
_LOAD = "  apply('type', true, true);\n"
_ASK = 'X.historyStep(kind, entryUrl, nowUrl, next,'
_RECENT = 'next, Date.now() - lastPush < 600);'
_TRY = '    try {\n      if (step.restore)'
_RESTORE = "      if (step.restore) history.replaceState(null, '', entryUrl);\n"
_WRITE = "      history[step.push ? 'pushState' : 'replaceState'](null, '', next + (keepHash ? location.hash : ''));\n"
_TIMED = '      if (step.push) lastPush = Date.now();\n'
_NOW = '      nowUrl = next;\n'
_SETTLE = "if (step.push || settle || kind !== 'type') entryUrl = next;"
_CATCH = '    } catch (e) { /* file:// */ }\n'
_FIRST = 'if (entryUrl === null) entryUrl = nowUrl = next;'
_ADDRESS = "return location.pathname + (qs ? '?' + qs : '');"
_POP_READ = '    state = parseState(location.search, allowed);\n    try {'
_POP = 'try { entryUrl = nowUrl = address(); } catch (e) { /* keep what was */ }'
_HASH_REST = "    if (location.hash === '#search') focusSearch();"
_HASH = ('    entryUrl = nowUrl;   // a jump to a fragment made a new entry for the view on screen: that view is what it stands for\n'
         + _HASH_REST)
_FROM_LOCATION = 'location.pathname + location.search'


def _kinds(what, line):
    """Three entries for a control that is a pick: written as typing is, written as Enter is, not put on screen at all."""
    return ((what + ' is written as typing is', line, line.replace("apply('pick')", "apply('type')")),
            (what + ' is written as Enter is', line, line.replace("apply('pick')", "apply('submit')")),
            (what + ' changes the state and puts nothing on screen', line, line.replace(" apply('pick');", '')))


BROKEN_PAGES = (
    # ---- what kind each change is: Enter, the typing pause, every control, the load
    ('Enter is written as typing is', _SUBMIT, _SUBMIT.replace("'submit'", "'type'")),
    ('Enter is written as a pick is', _SUBMIT, _SUBMIT.replace("'submit'", "'pick'")),
    ('Enter reads the box and puts nothing on screen', _SUBMIT, _SUBMIT.replace(" apply('submit');", '')),
    ('typing adds an entry', _TYPING, _TYPING.replace("'type'", "'pick'")),
    ('typing is written as Enter is', _TYPING, _TYPING.replace("'type'", "'submit'")),
    ('typing reads the box and puts nothing on screen', _TYPING, _TYPING.replace(" apply('type');", '')),
) + _kinds('an activity', _ACTIVITY) + _kinds('the scope', _SCOPE) + _kinds('the view', _VIEW) + _kinds('a menu', _MENU) + _kinds(
    'the route switch', _ROUTE) + _kinds("a chip's remove button", _CHIP) + _kinds('Clear all', _CLEAR) + (
    ('the load makes an entry', _LOAD, "  apply('pick', true, true);\n"),
    ('the load drops the fragment', _LOAD, "  apply('type', false, true);\n"),
    ('nothing says what the entry stands for when the page opens', (_FIRST, 'void 0;'), (_LOAD, "  apply('type', true);\n")),
    # ---- write(): the step, the entry put back, the new one
    ('the entry is never put back', _RESTORE, ''),
    ('the entry is put back after the new one is made', _RESTORE + _WRITE, _WRITE + _RESTORE),
    ('the entry is put back to the address typing gave it',
     "if (step.restore) history.replaceState(null, '', entryUrl);", "if (step.restore) history.replaceState(null, '', next);"),
    ('the entry is put back to the address it carries, not the one it stood for',
     "if (step.restore) history.replaceState(null, '', entryUrl);", "if (step.restore) history.replaceState(null, '', nowUrl);"),
    ('the step is asked with the two addresses the wrong way round', _ASK, 'X.historyStep(kind, nowUrl, entryUrl, next,'),
    ('the step is taken from the address of the moment, not from the entry', _ASK, 'X.historyStep(kind, nowUrl, nowUrl, next,'),
    ('the step is taken from the entry, not from the address of the moment', _ASK, 'X.historyStep(kind, entryUrl, entryUrl, next,'),
    ('the step is taken from the address of the moment as the browser spells it',
     _ASK, 'X.historyStep(kind, entryUrl, %s, next,' % _FROM_LOCATION),
    ('the step is taken from the address the browser has, not from what the entry stood for',
     _ASK, 'X.historyStep(kind, %s, nowUrl, next,' % _FROM_LOCATION),
    ('an entry made a moment ago is forgotten', _RECENT, 'next, false);'),
    ('a new entry is not timed', _TIMED, ''),
    ('the moment ends a millisecond early', _RECENT, 'next, Date.now() - lastPush < 599);'),
    ('the moment lasts a millisecond longer', _RECENT, 'next, Date.now() - lastPush <= 600);'),
    # ---- write(): the address the entry carries now
    ('the address the entry carries is not kept up', _NOW, ''),
    ('the address the entry carries is kept up on a new entry only', _NOW, '      if (step.push) nowUrl = next;\n'),
    ('the address the entry carries is kept up by typing only', _NOW, "      if (kind === 'type') nowUrl = next;\n"),
    ('the address the entry carries is read back from the browser', _NOW, '      nowUrl = %s;\n' % _FROM_LOCATION),
    ('the address the entry carries is kept up by a write the browser refused', (_NOW, ''), (_CATCH, _CATCH + '    nowUrl = next;\n')),
    # ---- write(): what the entry stands for
    ('what the entry stands for is read back from the browser',
     _SETTLE, "if (step.push || settle || kind !== 'type') entryUrl = %s;" % _FROM_LOCATION),
    ('a change that rewrites the entry made a moment ago does not become what it stands for',
     _SETTLE, 'if (step.push || settle) entryUrl = next;'),
    ('a pick that rewrites the entry made a moment ago does not become what it stands for',
     _SETTLE, "if (step.push || settle || kind === 'submit') entryUrl = next;"),
    ('a search that rewrites the entry made a moment ago does not become what it stands for',
     _SETTLE, "if (step.push || settle || kind === 'pick') entryUrl = next;"),
    ('every write becomes what the entry stands for, typing too', _SETTLE, 'entryUrl = next;'),
    ('only the load becomes what the entry stands for', _SETTLE, 'if (settle) entryUrl = next;'),
    ('no write becomes what the entry stands for', _SETTLE, 'void 0;'),
    # ---- address()
    ('the address is read back from the browser where it is built', _ADDRESS, 'return %s;' % _FROM_LOCATION),
    ('the address is built without the page it is on', _ADDRESS, "return (qs ? '?' + qs : '');"),
    # ---- Back and Forward (popstate)
    ('Back says nothing about the entry it lands on', _POP, 'try { address(); } catch (e) { /* keep what was */ }'),
    ('Back sets what the entry stands for and not what it carries', _POP, 'try { entryUrl = address(); } catch (e) { /* keep what was */ }'),
    ('Back sets what the entry carries and not what it stands for', _POP, 'try { nowUrl = address(); } catch (e) { /* keep what was */ }'),
    ("Back takes the browser's spelling of the address",
     _POP, 'try { entryUrl = nowUrl = %s; } catch (e) { /* keep what was */ }' % _FROM_LOCATION),
    ('Back takes the address of the view it left, before the state is read again',
     (_POP_READ, '    try {'), (_POP, _POP + '\n    state = parseState(location.search, allowed);')),
    # ---- a jump to a fragment (hashchange)
    ('the hashchange does not settle the entry', _HASH, _HASH_REST),
    ('the hashchange settles the wrong way round', _HASH, '    nowUrl = entryUrl;\n' + _HASH_REST),
    ("the hashchange takes the browser's spelling of the address", _HASH, '    entryUrl = %s;\n' % _FROM_LOCATION + _HASH_REST),
    # ---- a browser that refuses the write (a page opened from a file)
    ('a write the browser refuses stops the script (no try around it)', (_TRY, '    {\n      if (step.restore)'), (_CATCH, '    }\n')),
)


def changes(entry):
    """(what the change does, [(text, instead), ...]) of a BROKEN_PAGES entry."""
    return entry[0], ([entry[1:]] if isinstance(entry[1], str) else list(entry[1:]))


# what a visitor does in a "page:" check, as the harness writes it: a call of the page's own (page.type('ridge')), a
# press handed in from a table (press(page), press()) or picked by name (page[key](first)); not the same call where a
# table only names it (`(page) => page.activity(FIRST)`), and not refuse(), which is the browser's doing
_STEP = re.compile(r'(?<!=> )\b(?:\w+\.(?:type|pause|enter|back|forward|activity|scope|view|choose|route|clearAll|clearFilters|removeChip|jump)'
                   r'|\w+\[key\]|press)\(')
_OPENED = re.compile(r'(?<![\w.])load\(')
_READ = re.compile(r'\bseen\(\w+\)')


class TickListPageScenarioTests(unittest.TestCase):
    """The page part of ticklist.js, run whole by the harness on a generated Tick list page: its "page:" checks play the
    load, typing, the pause, Enter, every control, Clear all, a jump to a fragment, Back and Forward, and read the
    history list, the position, the address, the box and the controls after every step."""

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

    def run_node(self, *args):
        return subprocess.run([self.node] + list(args), cwd=TESTS, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=60)

    def run_page(self, module=TICKLIST_JS, *more):
        return self.run_node(HARNESS, EXPLORE_JS, module, self.model_path, *more)

    def passed(self, r):
        m = re.search(r'ticklist_js_harness: (\d+) checks passed', r.stdout)
        self.assertIsNotNone(m, 'no "N checks passed" line:\n%s\n%s' % (r.stdout, r.stderr))
        return int(m.group(1))

    def page_checks(self):
        """(the harness's text, [(label, body), ...] of its "page:" checks, in the order of the table)."""
        harness = source(HARNESS)
        table = harness[harness.index('  const pageChecks = {'):harness.index('  const GAPS = {')]
        heads = list(re.finditer(r"(?m)^    '((?:[^'\\\n]|\\.)*)': \(\) => ", table))
        ends = [m.start() for m in heads[1:]] + [len(table)]
        return harness, [(m.group(1).replace("\\'", "'"), table[m.end():end]) for m, end in zip(heads, ends)]

    def test_the_model_is_a_generated_tick_list_page(self):
        # the fixture: eight goals, of which the default scope lists six and a search for 'ridge' finds three (one of
        # them archived); every control the scenarios press is there
        model = self.model
        self.assertEqual(sorted(model['slugs']), sorted(slug for slug, _front, _goal in SITE))
        self.assertEqual(sorted(model['found']['ridge']), ['syng-old-ridge', 'syng-ridge-couloir', 'syng-ridge-traverse'])
        self.assertEqual((model['body']['tag'], model['body']['attrs'].get('class')), ('body', 'p-ticklist'))
        self.assertEqual(model['pathname'], '/personal-website/tick-list/')
        # three activities besides All, in the order of the chips (the arrow keys go through them); the five scopes;
        # the two views; a value in every menu, with the label its chip is named with
        self.assertEqual(model['activities'], ['all', 'ski', 'climb', 'hike'])
        self.assertEqual(model['labels']['activity']['ski'], core.ACT['ski'][0])
        self.assertEqual(model['scopes'], ['active', 'shortlisted', 'completed', 'archived', 'all'])
        self.assertEqual(model['views'], ['cards', 'list'])
        self.assertEqual(sorted(model['menus']), ['month', 'priority', 'region', 'sort', 'status'])
        self.assertEqual(model['menus']['region'], ['', 'synthetic-coast', 'synthetic-range'])
        self.assertEqual(model['menus']['status'], ['', 'idea', 'researching', 'shortlisted', 'completed'])
        self.assertEqual(model['menus']['priority'], ['', 'high', 'normal', 'someday'])
        self.assertEqual(model['menus']['month'], ['', '1', '2', '4', '7', '8', '9'])
        self.assertEqual(model['menus']['sort'], ['priority', 'added', 'name'])
        for name in ('region', 'status', 'priority', 'month'):
            self.assertEqual(sorted(model['labels'][name]), sorted(model['menus'][name]), name)
        # the page's one link to a fragment of itself is the skip link, and its target is on the page
        self.assertEqual(model['fragments'], ['#main'])
        html = json.dumps(model['body'])
        self.assertEqual(html.count('"href": "#main"'), 1)
        self.assertEqual(html.count('"id": "main"'), 1)
        # the form the script drives, as the generator writes it since round 5
        self.assertEqual(html.count('"id": "search"'), 1)
        self.assertIn('"autocomplete": "off"', html)
        for slug in model['slugs']:
            self.assertTrue(slug.startswith(PREFIX), slug)
            for folder in ('rendered', 'content'):
                self.assertFalse(os.path.lexists(os.path.join(ROOT, folder, 'trips', slug)), 'fixture slug %r names a real trip' % slug)
        self.assertEqual(core._REGION_PAGES, {})                 # page_model put core back

    def test_the_history_scenarios_play_out_on_a_generated_page(self):
        # the sequences (a) to (m): the harness asserts the history list, the position, the address, the box and the
        # controls at each step. Every "page:" check ran: the count is the pure checks' plus one per label
        r = self.run_page()
        self.assertEqual(r.returncode, 0, 'the "page:" checks failed:\n%s\n%s' % (r.stdout, r.stderr))
        pure = self.run_node(HARNESS)
        self.assertEqual(self.passed(r) - self.passed(pure), 1 + len(LABELS), 'the "page:" checks did not all run')
        # '' stands for the site's own module, so the model can be given without naming the two scripts
        self.assertEqual(self.passed(self.run_node(HARNESS, '', '', self.model_path)), self.passed(r))

    def test_the_sequences_of_round_6_are_checks_of_the_harness(self):
        # each sequence the gate asked for, (a) to (m), is one or more checks of the table every run with a page model
        # goes through, named for what it shows; none is behind an argument
        harness, checks = self.page_checks()
        labels = [label for label, _body in checks]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(labels, [MODEL_CHECK] + LABELS)
        self.assertEqual([letter for letter, _labels in SCENARIOS], list('abcdefghijklm'))
        self.assertEqual(len(LABELS), len(set(LABELS)))
        for letter, sequence in SCENARIOS:
            self.assertGreaterEqual(len(sequence), 1, letter)
        self.assertIn("Object.keys(pageChecks).forEach((label) => check('page: ' + label, pageChecks[label]));", harness)
        # each group of checks is marked with its letter in the harness, in order
        self.assertEqual(re.findall(r'(?m)^    // ---- \(([a-m])\)$', harness), list('abcdefghijklm'))

    def test_every_step_of_a_sequence_is_followed_by_a_reading_of_the_page(self):
        # after everything a visitor does, and after every page opened, the check reads all five: every entry of the
        # page, the one the visitor is on, its address, the box and the controls (seen), before the next step
        harness, checks = self.page_checks()
        self.assertIn('const seen = (page) => [page.stack(), page.at(), page.address(), page.box(), page.controls()];', harness)
        self.assertEqual(len(re.findall(r'(?m)^  const seen = ', harness)), 1)
        # the controls are every one the form has: the two radio groups, the four filter menus, the switch, the sort, the view
        controls = re.search(r'(?m)^    controls: \(\) => \(\{\n(.*?)\n    \}\),$', harness, re.S)
        self.assertIsNotNone(controls)
        self.assertEqual(re.findall(r'(?<![\w.\'"])(\w+): ', controls.group(1)),
                         ['activity', 'region', 'status', 'priority', 'month', 'gpx', 'scope', 'sort', 'view'])
        # the helpers the checks share (a search submitted, arrow keys, a jump to a fragment) are held to the same
        played = harness[harness.index('  const searched = '):harness.index('  const GAPS = {')]
        steps = sorted([m.start() for m in _STEP.finditer(played)] + [m.start() for m in _OPENED.finditer(played)])
        reads = [m.start() for m in _READ.finditer(played)]
        self.assertGreater(len(steps), 200)                     # the steps were found: about 230 of them
        unread = [played[at:at + 40].split('\n')[0] for at, nxt in zip(steps, steps[1:] + [len(played)])
                  if not any(at < r < nxt for r in reads)]
        self.assertEqual(unread, [], 'a step of a visitor without a reading of the page after it')
        # and every check plays something: it opens a page (itself, or through a helper) and takes steps on it
        for label, body in checks:
            with self.subTest(check=label):
                self.assertRegex(body, r'\b(?:load|searched|arrows|typedThenJump)\(')
                self.assertRegex(body, r'\bseen\(|\b(?:arrows|typedThenJump)\(')
        # what Back off the page's first entry is told by, and what a refused browser is
        self.assertIn('\n      left: () => hist.left,\n', source(STANDIN))
        self.assertIn(', refused: !!opts.refused };\n', source(STANDIN))

    def test_the_scenarios_notice_a_page_that_breaks_the_history_rule(self):
        # the harness itself: the real script with its history handling changed in one way fails a "page:" check, and
        # none of the checks of the pure helpers (which are untouched)
        src = source(TICKLIST_JS)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        shutil.copy(EXPLORE_JS, os.path.join(tmp.name, 'explore.js'))        # ticklist.js asks for it beside itself under node
        self.assertEqual(len(set(changes(entry)[0] for entry in BROKEN_PAGES)), len(BROKEN_PAGES))
        self.assertGreaterEqual(len(BROKEN_PAGES), 60)
        for n, entry in enumerate(BROKEN_PAGES):
            what, pairs = changes(entry)
            with self.subTest(broken=what):
                broken = src
                for old, new in pairs:
                    self.assertEqual(src.count(old), 1, 'assets/js/pages/ticklist.js no longer has this line once: %r' % old)
                    self.assertNotEqual(old, new)
                    broken = broken.replace(old, new)
                path = os.path.join(tmp.name, 'ticklist_%d.js' % n)
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(broken)
                self.assertEqual(self.run_node('--check', path).returncode, 0)
                r = self.run_page(path)
                self.assertNotEqual(r.returncode, 0, 'the harness passed a page where %s' % what)
                self.assertIn('FAIL page: ', r.stderr)
                self.assertEqual(len(re.findall(r'(?m)^FAIL ', r.stderr)), 1)
                self.assertNotIn('checks passed', r.stdout)
        # and the unchanged copy passes from there too
        path = os.path.join(tmp.name, 'ticklist.js')
        shutil.copy(TICKLIST_JS, path)
        self.assertEqual(self.run_page(path).returncode, 0)

    def test_no_case_is_left_as_a_known_gap(self):
        # the page does what the rule says in every sequence played: the harness knows no gap by any name, and refuses
        # the argument (a case the page did not handle would be kept there, as round 2 kept two for trips.js, and run
        # by a test marked as an expected failure)
        for name in ('apostrophe', 'moment', 'no-such-case'):
            with self.subTest(gap=name):
                r = self.run_page(TICKLIST_JS, 'gap:' + name)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn('unknown argument: gap:' + name, r.stderr)
                self.assertEqual(re.findall(r'(?m)^FAIL ', r.stderr), [])            # refused, not failed at a check
                self.assertNotIn('checks passed', r.stdout)
        self.assertRegex(source(HARNESS), r'(?m)^  const GAPS = \{\};$')

    def test_the_stand_in_for_the_browser_is_the_shared_one(self):
        # the document, the history, the location, the timers and the clock the page is run against are
        # tests/page_standin.js, the file tests/trips_js_harness.js uses: neither harness keeps a copy of any of it,
        # so the two cannot come to model two different browsers
        harness, standin = source(HARNESS), source(STANDIN)
        self.assertEqual(harness.count("const standin = require('./page_standin.js');"), 1)
        self.assertEqual(len(re.findall(r'\bstandin\.open\(', harness)), 1)
        self.assertIn('const tab = standin.open(MODEL, SOURCES, opts);', harness)
        # explore.js first, then ticklist.js: the order the bundle has them, and the two files the harness was given
        self.assertIn("const SOURCES = MODEL ? [[EXPLORE, fs.readFileSync(EXPLORE, 'utf8')], [TICKLIST, fs.readFileSync(TICKLIST, 'utf8')]] : [];", harness)
        for own in (r'\bclass\s+\w+', r"require\('vm'\)", r'\bvm\.', r'\bpushState:', r'\breplaceState:', r'\bnew URL\(', r'\bsetTimeout:'):
            with self.subTest(own=own):
                self.assertNotRegex(harness, own)
                self.assertRegex(standin, own)
        with open(os.path.join(TESTS, 'trips_js_harness.js'), encoding='utf-8') as fh:
            self.assertEqual(fh.read().count("const standin = require('./page_standin.js');"), 1)
        # the one selector the Tick list needs beyond the Trips page's: the activity group is the .trx-acts that is not
        # the scope's
        self.assertIn(r'|:not\(([^()\s]+)\))/;', standin)
        self.assertIn(".trx-acts:not(.tkl-scope) [role=\"radio\"]", source(TICKLIST_JS))
        # not a test module, and not a harness: discovery loads test_*.py, and the file runs nothing by itself
        self.assertFalse(os.path.basename(STANDIN).startswith('test_'))
        self.assertNotRegex(standin, r'\bcheck\(|console\.log\(|process\.argv')
        self.assertEqual(self.run_node('--check', STANDIN).returncode, 0)
        r = self.run_node(STANDIN)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, '', ''))


if __name__ == '__main__':
    unittest.main()
