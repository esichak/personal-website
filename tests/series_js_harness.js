#!/usr/bin/env node
'use strict';
/* Phase 3: unit tests for the pure helpers of assets/js/pages/series.js (hashTarget, startFiltered, revealId,
   landAfterLoad): which entry a URL hash names, whether the journal's "write-ups only" reader mode may start on without
   hiding that entry, which hidden entry a followed link must reveal, and whether the page scrolls to the hash again once
   the filter has shortened it (only on a fresh visit, never on a reload or Back / Forward). Given a page model, also
   checks of the script's listeners (the "dom:" checks at the end of this file).
   Review gate: an address that names an id inside a hidden day or month (a day's number and title, a month's heading)
   reveals that day or month too; the helpers are as they were, the page hands them a longer list, with each id in it
   once (round 3).
   Phase 11: a fifth helper, openedDay (the entry a pressed in-page link names, for 'Continue reading', features-08), and
   "dom:" checks of the month nav under the filter (a month without write-ups stays a link, marked is-empty and named
   ', no write-ups', a11y-07) and of 'Continue reading' (kept in localStorage per journal, offered on a later visit).

   Run by tests/test_series_js.py (skipped when node is missing); by hand:
   `node tests/series_js_harness.js [series.js [page-model.json [fault]]]`.
   - series.js: another module with the same exports (used to prove the harness fails a wrong one).
   - page-model.json: a journal page as tests/test_series_js.py describes it (page_model); with it the whole script is
     run against a stand-in for the browser and the "dom:" checks are added.
   - fault: one thing that stand-in then fails to do (deliver an event, keep the session store, report the navigation
     type, keep anything in localStorage), to prove the "dom:" checks notice.
     Or 'gap:<name>': also the check of that name, a case the page does not handle as said yet (GAPS, at the end:
     none at present, so any name is refused).
   Every failed assertion throws, so the process exits non-zero. The ids are shaped like the page's own: a day article is
   day-<label> with a decimal label's dot as a dash (day-5-2), a month section is month-YYYY-MM, and the hidden list is what
   the filter hides (track-only days and months without a write-up). */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const MODULE = path.resolve(process.argv[2] || path.join(__dirname, '..', 'assets', 'js', 'pages', 'series.js'));

assert.strictEqual(typeof document, 'undefined', 'the harness runs without a DOM');
assert.strictEqual(typeof window, 'undefined', 'the harness runs without a window');
assert.ok(fs.existsSync(MODULE), 'missing ' + MODULE);
const SER = require(MODULE);   // must export before touching the DOM (there is none here)

let checks = 0;
function check(label, fn) {
  try {
    fn();
    checks++;
  } catch (e) {
    console.error('FAIL ' + label);
    throw e;
  }
}
const eq = assert.strictEqual;
const deq = assert.deepStrictEqual;

// ---------------------------------------------------------------- exports

check('exports', () => {
  eq(typeof SER, 'object');
  for (const name of ['hashTarget', 'startFiltered', 'revealId', 'landAfterLoad', 'openedDay']) {
    eq(typeof SER[name], 'function', 'series.js does not export ' + name);
  }
});

// ---------------------------------------------------------------- hashTarget(hash) -> {kind, id}

const target = (hash) => {
  const t = SER.hashTarget(hash);
  assert.ok(t && typeof t === 'object', 'hashTarget(' + JSON.stringify(hash) + ') is not an object');
  return t;
};

check('hashTarget #day-5-2 (a decimal day label)', () => {
  eq(target('#day-5-2').kind, 'day');
  eq(target('#day-5-2').id, 'day-5-2');
});
check('hashTarget #day-12', () => {
  eq(target('#day-12').kind, 'day');
  eq(target('#day-12').id, 'day-12');
});
check('hashTarget #month-2024-06', () => {
  eq(target('#month-2024-06').kind, 'month');
  eq(target('#month-2024-06').id, 'month-2024-06');
});
check('hashTarget #days is the day log, not a day', () => {
  eq(target('#days').kind, 'other');
  eq(target('#days').id, 'days');
});
check('hashTarget #title', () => {
  eq(target('#title').kind, 'other');
  eq(target('#title').id, 'title');
});
check('hashTarget of no hash', () => {
  eq(target('').kind, null);
  assert.ok(!target('').id, 'no hash names no element');
});
check('hashTarget decodes a percent-encoded hash', () => {
  eq(target('#day%2D5%2D2').kind, 'day');
  eq(target('#day%2D5%2D2').id, 'day-5-2');
  eq(target('#month%2D2024%2D06').kind, 'month');
  eq(target('#month%2D2024%2D06').id, 'month-2024-06');
});
check('hashTarget survives a malformed escape', () => {
  // the page calls this on load and on every hashchange: a hand-typed '%' must not throw there
  assert.doesNotThrow(() => SER.hashTarget('#day-%'));
  assert.doesNotThrow(() => SER.hashTarget('#%E0%A4%A'));
});
check('hashTarget returns kind and id', () => {
  for (const hash of ['#day-5-2', '#month-2024-06', '#days', '']) {
    deq(Object.keys(target(hash)).sort(), ['id', 'kind'], 'hashTarget(' + JSON.stringify(hash) + ')');
  }
});

// ---------------------------------------------------------------- startFiltered(defaultOn, hash, hiddenIds)

// track-only days and a month without a write-up; day-2, day-5-2 and month-2024-04 stay visible under the filter
const HIDDEN = ['day-1', 'day-3', 'day-6', 'month-2024-06'];
const on = (hash, hidden) => SER.startFiltered(true, hash, hidden || HIDDEN);

check('startFiltered default on, no hash', () => {
  eq(on(''), true);
});
check('startFiltered default on, a hash naming a hidden day', () => {
  eq(on('#day-1'), false);
  eq(on('#day-6'), false);
});
check('startFiltered default on, a hash naming a hidden month', () => {
  eq(on('#month-2024-06'), false);
});
check('startFiltered default on, a hash naming a visible entry', () => {
  eq(on('#day-2'), true);
  eq(on('#day-5-2'), true);
  eq(on('#month-2024-04'), true);
});
check('startFiltered default on, a hash naming another part of the page', () => {
  eq(on('#days'), true);
  eq(on('#title'), true);
  eq(on('#highlights'), true);
});
check('startFiltered matches whole ids only', () => {
  eq(on('#day-12', ['day-1']), true);     // day-12 is not day-1
  eq(on('#day-5', ['day-5-2']), true);    // nor is day-5 the hidden day-5-2
  eq(on('#day-5-2', ['day-5']), true);
  eq(on('#day-5-2', ['day-5-2']), false);
});
check('startFiltered decodes a percent-encoded hash', () => {
  eq(on('#day%2D1'), false);
  eq(on('#day%2D2'), true);
});
check('startFiltered with nothing hidden', () => {
  eq(on('#day-1', []), true);
  eq(on('', []), true);
});
check('startFiltered default off, whatever the hash', () => {
  for (const hash of ['', '#day-1', '#day-2', '#day-5-2', '#month-2024-06', '#days']) {
    eq(SER.startFiltered(false, hash, HIDDEN), false, 'default off with ' + JSON.stringify(hash));
  }
  eq(SER.startFiltered(false, '', []), false);
});
check('startFiltered leaves the hidden list alone', () => {
  const hidden = HIDDEN.slice();
  on('#day-1', hidden);
  on('#day-2', hidden);
  deq(hidden, HIDDEN);
});

// ---------------------------------------------------------------- revealId(filtered, hash, hiddenIds) -> id | ''

// what a followed link must reveal: the hidden day or month the hash names while the filter is on, else nothing
const reveal = (hash, hidden) => SER.revealId(true, hash, hidden || HIDDEN);

check('revealId filtered, a hash naming a hidden day', () => {
  eq(reveal('#day-1'), 'day-1');
  eq(reveal('#day-3'), 'day-3');
  eq(reveal('#day-6'), 'day-6');
});
check('revealId filtered, a hash naming a hidden month', () => {
  eq(reveal('#month-2024-06'), 'month-2024-06');
});
check('revealId filtered, a hash naming a visible entry', () => {
  eq(reveal('#day-2'), '');
  eq(reveal('#day-5-2'), '');
  eq(reveal('#month-2024-04'), '');
});
check('revealId filtered, a hash naming another part of the page', () => {
  eq(reveal('#days'), '');
  eq(reveal('#title'), '');
  eq(reveal('#highlights'), '');
});
check('revealId filtered, no hash', () => {
  eq(reveal(''), '');
  eq(reveal('#'), '');
});
check('revealId not filtered, whatever the hash', () => {
  // nothing is hidden while the filter is off, so there is nothing to reveal (and nothing to announce)
  for (const hash of ['', '#day-1', '#day-6', '#month-2024-06', '#day-2', '#day-5-2', '#days']) {
    eq(SER.revealId(false, hash, HIDDEN), '', 'not filtered with ' + JSON.stringify(hash));
  }
});
check('revealId matches whole ids only', () => {
  eq(reveal('#day-12', ['day-1']), '');       // day-12 is not the hidden day-1
  eq(reveal('#day-5', ['day-5-2']), '');      // nor is day-5 the hidden day-5-2
  eq(reveal('#day-5-2', ['day-5']), '');
  eq(reveal('#day-5-2', ['day-5-2']), 'day-5-2');
});
check('revealId decodes a percent-encoded hash', () => {
  eq(reveal('#day%2D1'), 'day-1');
  eq(reveal('#month%2D2024%2D06'), 'month-2024-06');
  eq(reveal('#day%2D2'), '');
});
check('revealId with nothing hidden', () => {
  eq(reveal('#day-1', []), '');
  eq(reveal('', []), '');
});
check('revealId returns the id as a string, or the empty string', () => {
  for (const filtered of [true, false]) {
    for (const hash of ['', '#day-1', '#day-2', '#month-2024-06', '#days']) {
      eq(typeof SER.revealId(filtered, hash, HIDDEN), 'string', JSON.stringify([filtered, hash]));
    }
  }
});
check('revealId survives a malformed escape', () => {
  // the page calls this on every hashchange and on clicks: a hand-typed '%' must not throw there
  assert.doesNotThrow(() => reveal('#day-%'));
  assert.doesNotThrow(() => reveal('#%E0%A4%A'));
});
check('revealId leaves the hidden list alone', () => {
  const hidden = HIDDEN.slice();
  reveal('#day-1', hidden);
  reveal('#day-2', hidden);
  SER.revealId(false, '#day-1', hidden);
  deq(hidden, HIDDEN);
});
check('revealId agrees with startFiltered about what is hidden', () => {
  // a hash that keeps the filter from starting on is exactly a hash that a later link must reveal
  for (const hash of ['', '#day-1', '#day-2', '#day-3', '#day-5-2', '#day-6', '#day-12', '#month-2024-04', '#month-2024-06', '#days']) {
    eq(reveal(hash) !== '', on(hash) === false, 'hash ' + JSON.stringify(hash));
  }
});

// ---------------------------------------------------------------- landAfterLoad(filtered, hash, navType) -> boolean

// navType is PerformanceNavigationTiming.type: 'navigate' for a link or a typed address; '' or undefined when the
// browser does not say. On 'reload', 'back_forward' and 'prerender' the browser restores the reader's own position.
const FRESH = ['navigate', '', undefined];
const RESTORED = ['reload', 'back_forward', 'prerender'];
const ENTRIES = ['#day-1', '#day-2', '#day-5-2', '#day-12', '#month-2024-04', '#month-2024-06'];
const ELSEWHERE = ['', '#', '#days', '#title', '#highlights', '#map', '#stats'];

check('landAfterLoad filtered, a day or month hash, a fresh visit', () => {
  for (const hash of ENTRIES) {
    for (const nav of FRESH) {
      eq(SER.landAfterLoad(true, hash, nav), true, JSON.stringify([hash, nav]));
    }
  }
});
check('landAfterLoad filtered, a day or month hash, navType left out', () => {
  eq(SER.landAfterLoad(true, '#day-5-2'), true);
  eq(SER.landAfterLoad(true, '#month-2024-06'), true);
});
check('landAfterLoad never on reload', () => {
  for (const hash of ENTRIES) {
    eq(SER.landAfterLoad(true, hash, 'reload'), false, hash);
  }
});
check('landAfterLoad never on back_forward', () => {
  for (const hash of ENTRIES) {
    eq(SER.landAfterLoad(true, hash, 'back_forward'), false, hash);
  }
});
check('landAfterLoad never on prerender', () => {
  for (const hash of ENTRIES) {
    eq(SER.landAfterLoad(true, hash, 'prerender'), false, hash);
  }
});
check('landAfterLoad filtered, a hash naming something other than a day or month', () => {
  for (const hash of ELSEWHERE) {
    for (const nav of FRESH.concat(RESTORED)) {
      eq(SER.landAfterLoad(true, hash, nav), false, JSON.stringify([hash, nav]));
    }
  }
});
check('landAfterLoad not filtered, whatever the hash and the navigation', () => {
  // the list was not shortened, so the browser's own jump to the hash already landed
  for (const hash of ENTRIES.concat(ELSEWHERE)) {
    for (const nav of FRESH.concat(RESTORED)) {
      eq(SER.landAfterLoad(false, hash, nav), false, JSON.stringify([hash, nav]));
    }
  }
  eq(SER.landAfterLoad(false, '#day-5-2'), false);
});
check('landAfterLoad decodes a percent-encoded hash', () => {
  eq(SER.landAfterLoad(true, '#day%2D5%2D2', 'navigate'), true);
  eq(SER.landAfterLoad(true, '#month%2D2024%2D06', 'navigate'), true);
  eq(SER.landAfterLoad(true, '#day%2D5%2D2', 'reload'), false);
});
check('landAfterLoad returns a boolean', () => {
  for (const filtered of [true, false]) {
    for (const hash of ['', '#day-1', '#month-2024-06', '#days']) {
      for (const nav of FRESH.concat(RESTORED)) {
        eq(typeof SER.landAfterLoad(filtered, hash, nav), 'boolean', JSON.stringify([filtered, hash, nav]));
      }
    }
  }
});
check('landAfterLoad survives a malformed escape', () => {
  assert.doesNotThrow(() => SER.landAfterLoad(true, '#day-%', 'navigate'));
  assert.doesNotThrow(() => SER.landAfterLoad(true, '#%E0%A4%A', 'reload'));
});

// ---------------------------------------------------------------- openedDay(href, firstDayOf) -> id | ''

// features-08, 'Continue reading': the entry a pressed in-page link names. A link to a day names that day; a link to a
// month names the day firstDayOf(monthId) picks in it (on the page: the first day the reader can see there, else its
// first); anything else names nothing. firstDayOf here answers from a table and notes every month it was asked about.
const FIRST = { 'month-2024-04': 'day-2', 'month-2024-06': 'day-40' };
const asked = [];
const firstDay = (monthId) => { asked.push(monthId); return FIRST[monthId] || ''; };
const opened = (href) => SER.openedDay(href, firstDay);

check('openedDay a link to a day names that day', () => {
  asked.length = 0;
  eq(opened('#day-2'), 'day-2');
  eq(opened('#day-5-2'), 'day-5-2');
  eq(opened('#day-12'), 'day-12');
  eq(opened('#day-40'), 'day-40');
  deq(asked, [], 'a link to a day does not ask for a month\'s first day');
});
check('openedDay a link to a month names the day firstDayOf gives for it', () => {
  asked.length = 0;
  eq(opened('#month-2024-04'), 'day-2');
  eq(opened('#month-2024-06'), 'day-40');
  deq(asked, ['month-2024-04', 'month-2024-06'], 'firstDayOf is asked once per month link, with the month\'s id');
});
check('openedDay a month in which firstDayOf finds no day names nothing', () => {
  eq(opened('#month-2024-05'), '');
  for (const none of [undefined, null, '']) {
    eq(SER.openedDay('#month-2024-04', () => none), '', 'firstDayOf answered ' + JSON.stringify(none));
  }
});
check('openedDay a link to another part of the page names nothing', () => {
  asked.length = 0;
  for (const href of ['#days', '#title', '#map', '#highlights', '#stats', '#', '']) {
    eq(opened(href), '', JSON.stringify(href));
  }
  deq(asked, []);
});
check('openedDay a link that is not a bare fragment names nothing', () => {
  // only '#…': a link to another page (another journal's day among them) or a relative path is not an entry of this page
  asked.length = 0;
  for (const href of ['day-2', 'month-2024-04', './#day-2', '../other-journal/#day-2', '/trips/x/#month-2024-04',
                      'https://example.com/#day-2', '?q=1#day-2']) {
    eq(opened(href), '', href);
  }
  eq(SER.openedDay(null, firstDay), '');
  eq(SER.openedDay(undefined, firstDay), '');
  deq(asked, []);
});
check('openedDay decodes a percent-encoded hash', () => {
  asked.length = 0;
  eq(opened('#day%2D5%2D2'), 'day-5-2');
  eq(opened('#month%2D2024%2D06'), 'day-40');
  deq(asked, ['month-2024-06']);
});
check('openedDay agrees with hashTarget about what a day and a month are', () => {
  // the page keeps only an id that is a day article (series.js keep()); the helper names what the link names
  for (const href of ['#day-5-2', '#day-2-t', '#days', '#month-2024-04', '#title', '']) {
    const kind = SER.hashTarget(href).kind;
    eq(SER.openedDay(href, (m) => 'first of ' + m),
       kind === 'day' ? SER.hashTarget(href).id : kind === 'month' ? 'first of ' + SER.hashTarget(href).id : '', href);
  }
});
check('openedDay returns a string', () => {
  for (const href of ['#day-2', '#month-2024-04', '#month-2024-05', '#days', '', 'other/#day-2', null, undefined]) {
    eq(typeof SER.openedDay(href, () => undefined), 'string', JSON.stringify(href));
    eq(typeof opened(href), 'string', JSON.stringify(href));
  }
});
check('openedDay survives a malformed escape', () => {
  // the page calls this on every press of an in-page link
  assert.doesNotThrow(() => opened('#day-%'));
  assert.doesNotThrow(() => opened('#month-%E0%A4%A'));
});

// ---------------------------------------------------------------- ids inside a hidden day or month (review gate)

// The page now lists, with each hidden day and month, every id inside it: a day's number (day-1-n) and title (day-1-t),
// a month's heading (month-2024-06-h). The helpers are unchanged: they look an id up in the list they are handed, whole.
const INSIDE = ['day-1', 'day-1-n', 'day-1-t', 'day-6', 'day-6-n', 'day-6-t', 'month-2024-06', 'month-2024-06-h'];
check('inner ids: in the list, an id inside a hidden day or month is one the filter hides', () => {
  for (const id of ['day-1-t', 'day-1-n', 'day-6-t', 'month-2024-06-h']) {
    eq(SER.startFiltered(true, '#' + id, INSIDE), false, id);
    eq(SER.revealId(true, '#' + id, INSIDE), id, id);
    eq(SER.revealId(false, '#' + id, INSIDE), '', id + ', not filtered');
    eq(SER.startFiltered(false, '#' + id, INSIDE), false, id + ', default off');
  }
});
check('inner ids: the same ids of a written day or month are not in it, and keep the filter', () => {
  for (const id of ['day-2-t', 'day-2-n', 'day-5-2-t', 'month-2024-04-h']) {
    eq(SER.startFiltered(true, '#' + id, INSIDE), true, id);
    eq(SER.revealId(true, '#' + id, INSIDE), '', id);
  }
});
check('inner ids: the helpers do not work them out from the day or month they are in', () => {
  // only the list decides: handed the days and months alone, as before the change, an inner id is not hidden
  for (const id of ['day-1-t', 'day-1-n', 'month-2024-06-h']) {
    eq(SER.startFiltered(true, '#' + id, HIDDEN), true, id);
    eq(SER.revealId(true, '#' + id, HIDDEN), '', id);
  }
  eq(SER.startFiltered(true, '#day-1-title', INSIDE), true);      // whole ids, here too
  eq(SER.revealId(true, '#day-1-', INSIDE), '');
});
check('inner ids: an id listed twice changes no answer', () => {
  const twice = INSIDE.concat(INSIDE);
  for (const id of ['day-1', 'day-1-t', 'month-2024-06-h', 'day-2', 'day-2-t', 'days']) {
    eq(SER.startFiltered(true, '#' + id, twice), SER.startFiltered(true, '#' + id, INSIDE), id);
    eq(SER.revealId(true, '#' + id, twice), SER.revealId(true, '#' + id, INSIDE), id);
  }
});
check('inner ids: hashTarget and landAfterLoad take them for a day or a month', () => {
  // so a fresh visit to a written day's title is landed on again once the filter has shortened the page
  deq(SER.hashTarget('#day-2-t'), { kind: 'day', id: 'day-2-t' });
  deq(SER.hashTarget('#month-2024-04-h'), { kind: 'month', id: 'month-2024-04-h' });
  eq(SER.landAfterLoad(true, '#day-2-t', 'navigate'), true);
  eq(SER.landAfterLoad(true, '#month-2024-04-h', 'navigate'), true);
  eq(SER.landAfterLoad(true, '#day-2-t', 'reload'), false);
  eq(SER.landAfterLoad(false, '#day-1-t', 'navigate'), false);
});
// last of the pure checks, so that a helper with a wrong answer is reported at its own check first
check('signatures: the five helpers, with the arguments they take', () => {
  deq(Object.keys(SER).sort(), ['hashTarget', 'landAfterLoad', 'openedDay', 'revealId', 'startFiltered']);
  deq([SER.hashTarget.length, SER.startFiltered.length, SER.revealId.length, SER.landAfterLoad.length, SER.openedDay.length],
      [1, 3, 3, 3, 2],
      'hashTarget(hash), startFiltered(defaultOn, hash, hiddenIds), revealId(filtered, hash, hiddenIds), landAfterLoad(filtered, hash, navType), openedDay(href, firstDayOf)');
});

// ---------------------------------------------------------------- the listeners, on a stand-in for the browser

/* What the pure helpers cannot show: that the page code calls them at the right moments (contract sections 5 and 9, and
   the "Behaviour" line of 10.6). tests/test_series_js.py passes a JSON model of a journal page that
   sitegen.pages.series generated: its elements (tag, id, classes, attributes, parent), the elements matched by each
   selector the script uses, the elements series.css takes out of the page while the filter is on, and the few elements
   pressed or read below. load() runs the whole script against just enough of window, document and Element for what
   series.js calls, with a session store, a local store and a navigation type, and returns the reader's actions: a press
   on an element, a change of the toggle, a new hash. A call the stand-in lacks throws and fails the run: add it to
   load(). Selectors are answered from the model, so the script may spell them as it likes. Without the model these
   checks are skipped.
   Phase 11: the script now makes an element of its own (the ', no write-ups' note in a month link, a11y-07), which the
   model cannot list. document.createElement, appendChild and removeChild make and move such elements; a selector is
   tried on them through its parsed form (MODEL.parsed, from tests/test_series_js.py parse_selector), so a link's
   querySelector finds the note it was given. Every element's textContent is the page's (MODEL elements' text), with the
   text of the elements the script appended after it.

   FAULT breaks the stand-in on purpose, as a script with that part gutted would behave: 'hashchange', 'click' or
   'change' (the event reaches no listener), 'store' (the session store keeps nothing), 'navigation' (every load is
   reported as a fresh visit), 'local' (localStorage throws on every call, as in a private window: it keeps nothing).
   Each must make a check below fail; tests/test_series_js.py runs them all. */
const MODEL = process.argv[3] ? JSON.parse(fs.readFileSync(path.resolve(process.argv[3]), 'utf8')) : null;
const SOURCE = MODEL ? fs.readFileSync(MODULE, 'utf8') : '';
const GAP = /^gap:/.test(process.argv[4] || '') ? process.argv[4].slice(4) : '';
const FAULT = GAP ? '' : process.argv[4] || '';
assert.ok(['', 'hashchange', 'click', 'change', 'store', 'navigation', 'local'].indexOf(FAULT) !== -1, 'unknown fault: ' + FAULT);
// Run in the page's own realm before the script: the lists the script then searches with indexOf. series.js keeps one,
// the ids the filter hides, and searches it whenever an address names an id (startFiltered, revealId).
const SPY = '(function () { var real = Array.prototype.indexOf, lists = [];'
  + ' Array.prototype.indexOf = function () { var i = 0; while (i < lists.length && lists[i] !== this) i++;'
  + ' if (i === lists.length) lists.push(this); return real.apply(this, arguments); }; return lists; })()';

// A selector as tests/test_series_js.py parse_selector writes it (MODEL.parsed): a list of chains, each a list of
// [combinator, tests] from left to right; a test is ['tag', name], ['id', v], ['class', v], ['attr', name, op, value] or
// ['not', tests]. Tried on the elements the script made itself, which the model's answers cannot list; the same rules
// as that file's matcher (_attr_ok, node_matches, chain_matches).
function attrOk(have, op, value) {
  if (have === null) return false;
  if (op === null) return true;
  if (op === '=') return have === value;
  if (op === '^=') return !!value && have.indexOf(value) === 0;
  if (op === '$=') return !!value && have.slice(-value.length) === value;
  if (op === '*=') return !!value && have.indexOf(value) !== -1;
  if (op === '~=') return have.split(/\s+/).indexOf(value) !== -1;
  return have === value || have.indexOf(value + '-') === 0;        // |=
}
function passes(el, tests) {
  return tests.every((t) => {
    if (t[0] === 'tag') return t[1] === '*' || el.tagName.toLowerCase() === t[1];
    if (t[0] === 'id') return el.id === t[1];
    if (t[0] === 'class') return el.classList.contains(t[1]);
    if (t[0] === 'attr') return attrOk(el.getAttribute(t[1]), t[2], t[3]);
    return !passes(el, t[1]);                                      // not
  });
}
function chainFits(el, chain) {
  const last = chain[chain.length - 1];
  if (!passes(el, last[1])) return false;
  if (chain.length === 1) return true;
  for (let up = el.parentElement; up; up = up.parentElement) {
    if (chainFits(up, chain.slice(0, -1))) return true;
    if (last[0] === '>') return false;
  }
  return false;
}

function load(opts) {
  opts = opts || {};
  const store = opts.store || {};
  const local = opts.local || {};          // localStorage: kept across again() as well, in a store of its own
  const frames = [];
  const scrolled = [];
  const heard = { window: {}, document: {} };
  const listen = (bag) => (type, fn) => { (bag[type] = bag[type] || []).push(fn); };
  const emit = (bag, type, ev) => (type === FAULT ? [] : bag[type] || []).slice().forEach((fn) => fn(ev));
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const els = [];
  const made = [];                         // the elements the script made (document.createElement), in order
  const appended = new Map();              // element -> the elements the script appended to it, in order
  const adopt = new Map();                 // element the script made -> sets its parent
  // in the document: an element of the page, or one the script made that hangs under one
  const attached = (el) => {
    let top = el;
    while (top.parentElement) top = top.parentElement;
    return top.index >= 0;
  };
  const matching = (sel) => {
    if (!own(MODEL.selectors, sel)) throw new Error('the page model has no answer for the selector ' + sel);
    if (!own(MODEL.parsed, sel)) throw new Error('the page model has no parsed form of the selector ' + sel);
    const mine = made.filter((e) => attached(e) && MODEL.parsed[sel].some((chain) => chainFits(e, chain)));
    return MODEL.selectors[sel].map((i) => els[i]).concat(mine);
  };
  // rendered: not under [hidden], and not one of the entries the stylesheet drops while the day log has the filter class
  const shown = (el) => {
    const filtering = els[MODEL.handles.log].classList.contains(MODEL.filterClass);
    for (let e = el; e; e = e.parentElement) {
      if (e.hidden || (filtering && MODEL.filteredOut.indexOf(e.index) !== -1)) return false;
    }
    return true;
  };
  // one element: of the page (spec: its model entry, index: its place in the model) or made by the script (index -1)
  const make = (spec, index) => {
    const classes = new Set(spec.classes);
    const attrs = Object.assign({}, spec.attrs);
    const dataset = {};
    Object.keys(attrs).filter((k) => k.indexOf('data-') === 0).forEach((k) => {
      dataset[k.slice(5).replace(/-([a-z])/g, (m, c) => c.toUpperCase())] = attrs[k];
    });
    const bag = {};
    const kids = [];
    let text = spec.text || '';
    let up = null;
    const el = {
      index: index, tagName: spec.tag.toUpperCase(), id: spec.id, dataset: dataset,
      hidden: own(attrs, 'hidden'), checked: own(attrs, 'checked'), heard: bag,
      classList: {
        contains: (c) => classes.has(c),
        add: (c) => { classes.add(c); },
        remove: (c) => { classes.delete(c); },
        toggle: (c, force) => {
          const want = force === undefined ? !classes.has(c) : !!force;
          if (want) classes.add(c); else classes.delete(c);
          return want;
        },
      },
      getAttribute: (n) => (own(attrs, n) ? attrs[n] : null),
      hasAttribute: (n) => own(attrs, n),
      setAttribute: (n, v) => { attrs[n] = String(v); },
      removeAttribute: (n) => { delete attrs[n]; },
      contains: (other) => {
        for (let e = other; e; e = e.parentElement) if (e === el) return true;
        return false;
      },
      querySelectorAll: (sel) => matching(sel).filter((e) => e !== el && el.contains(e)),
      querySelector: (sel) => el.querySelectorAll(sel)[0] || null,
      matches: (sel) => matching(sel).indexOf(el) !== -1,
      closest: (sel) => {
        const hits = matching(sel);
        for (let e = el; e; e = e.parentElement) if (hits.indexOf(e) !== -1) return e;
        return null;
      },
      // only an element the script made can be moved: the page's own stay where the model has them
      appendChild: (child) => {
        assert.ok(made.indexOf(child) !== -1, 'the stand-in appends only elements the script made');
        if (child.parentElement) child.parentElement.removeChild(child);
        adopt.get(child)(el);
        kids.push(child);
        return child;
      },
      removeChild: (child) => {
        const i = kids.indexOf(child);
        if (i === -1) throw new Error('NotFoundError: removeChild() of an element that is not a child of this one');
        kids.splice(i, 1);
        adopt.get(child)(null);
        return child;
      },
      addEventListener: listen(bag),
      getBoundingClientRect: () => ({ top: 0, right: 0, bottom: 0, left: 0, width: 0, height: 0 }),
      scrollIntoView: () => { scrolled.push(el.id); win.scrollY = 1000 + 10 * index; },   // each element at its own height
    };
    Object.defineProperty(el, 'parentElement', { get: () => (index < 0 ? up : spec.parent < 0 ? null : els[spec.parent]) });
    Object.defineProperty(el, 'offsetParent', { get: () => (shown(el) ? el.parentElement || el : null) });
    // the page's text of the element (its children's included), then the text of what the script appended to it;
    // setting it replaces both, as in a browser
    Object.defineProperty(el, 'textContent', {
      get: () => text + kids.map((k) => k.textContent).join(''),
      set: (v) => { text = String(v); kids.splice(0).forEach((k) => adopt.get(k)(null)); },
    });
    Object.defineProperty(el, 'className', {
      get: () => Array.from(classes).join(' '),
      set: (v) => {
        classes.clear();
        String(v).split(/\s+/).filter(Boolean).forEach((c) => classes.add(c));
        attrs['class'] = String(v);
      },
    });
    appended.set(el, kids);
    adopt.set(el, (parent) => { up = parent; });
    return el;
  };
  MODEL.elements.forEach((spec, index) => { els.push(make(spec, index)); });
  // localStorage, per origin and kept across visits. In a private window (opts.private, or FAULT 'local') every call
  // throws, as Safari's once did; with opts.private 'access' even reading window.localStorage throws, as it does where
  // the reader blocks site data
  const priv = FAULT === 'local' ? 'calls' : opts.private || '';
  const refuse = () => { throw new Error('QuotaExceededError: the stand-in\'s localStorage refuses (a private window)'); };
  const localStorage = {
    getItem: (k) => (priv ? refuse() : own(local, k) ? local[k] : null),
    setItem: (k, v) => { if (priv) refuse(); local[k] = String(v); },
    removeItem: (k) => { if (priv) refuse(); delete local[k]; },
  };
  const win = {
    scrollY: 0,
    location: { hash: opts.hash || '', pathname: opts.pathname || MODEL.pathname },
    sessionStorage: {
      getItem: (k) => (own(store, k) ? store[k] : null),
      setItem: (k, v) => { if (FAULT !== 'store') store[k] = String(v); },
    },
    // PerformanceNavigationTiming.type; an older browser has no entry at all
    performance: {
      getEntriesByType: (t) => {
        if (t !== 'navigation' || (opts.navType === undefined && FAULT !== 'navigation')) return [];
        return [{ type: FAULT === 'navigation' ? 'navigate' : opts.navType }];
      },
    },
    addEventListener: listen(heard.window),
    requestAnimationFrame: (fn) => frames.push(fn),
  };
  Object.defineProperty(win, 'localStorage', { get: () => (priv === 'access' ? refuse() : localStorage) });
  const doc = {
    readyState: opts.loading ? 'loading' : 'complete',     // loading: the script runs before the window's load event
    // opts.drop: ids the page is taken not to have (a journal whose days are all written, or none, has no toggle)
    getElementById: (id) => ((opts.drop || []).indexOf(id) !== -1 ? null : els.concat(made.filter(attached)).find((e) => e.id === id) || null),
    querySelectorAll: (sel) => matching(sel),
    querySelector: (sel) => matching(sel)[0] || null,
    addEventListener: listen(heard.document),
    // an element of the script's own (a month link's ', no write-ups' note): in the document once appended to it
    createElement: (tag) => {
      const el = make({ tag: String(tag).toLowerCase(), id: '', classes: [], attrs: {}, parent: -1 }, -1);
      made.push(el);
      return el;
    },
  };
  const flush = () => { while (frames.length) frames.shift()(); };
  const h = {};
  Object.keys(MODEL.handles).forEach((k) => { h[k] = els[MODEL.handles[k]]; });

  const context = vm.createContext({ window: win, document: doc });
  const searched = vm.runInContext(SPY, context);
  vm.runInContext(SOURCE, context, { filename: MODULE });
  flush();

  return {
    h: h,
    scrolled: scrolled,
    stored: () => Object.keys(store),
    // localStorage as it stands (a copy): what 'Continue reading' kept, by key
    kept: () => Object.assign({}, local),
    // the elements the script appended to this one, in order (a copy)
    appended: (el) => appended.get(el).slice(),
    // the links of the month nav, in page order
    monthLinks: () => els.filter((e) => e.tagName === 'A' && h.mnav.contains(e)),
    hash: () => win.location.hash,
    scrollY: () => win.scrollY,
    said: () => h.live.textContent,
    // on the page: the element with this id is rendered (not under [hidden], not dropped by the filter's stylesheet rule)
    rendered: (id) => {
      const el = doc.getElementById(id);
      assert.ok(el, 'the page has no element with the id ' + id);
      return el.offsetParent !== null;
    },
    // the ids the script takes for hidden: the one list it searches, as it stands now (a copy)
    hidden: () => {
      eq(searched.length, 1, 'the script searched ' + searched.length + ' lists; this check expects the one list of hidden ids');
      return Array.from(searched[0]);
    },
    // true while only the written entries show; the checkbox and the class the stylesheet keys on must agree
    filtered: () => {
      eq(h.log.classList.contains(MODEL.filterClass), h.box.checked, 'the toggle and .' + MODEL.filterClass + ' disagree');
      return h.box.checked;
    },
    // a press on an element: the click listeners up the tree, then what a browser does with an in-page link. A link to
    // the fragment the address already ends with changes nothing, so no hashchange follows
    press: (el) => {
      const ev = { type: 'click', target: el, defaultPrevented: false, preventDefault: () => { ev.defaultPrevented = true; } };
      for (let e = el; e; e = e.parentElement) emit(e.heard, 'click', ev);
      emit(heard.document, 'click', ev);
      emit(heard.window, 'click', ev);
      let a = el;
      while (a && !(a.tagName === 'A' && (a.getAttribute('href') || '').charAt(0) === '#')) a = a.parentElement;
      if (a && !ev.defaultPrevented && a.getAttribute('href') !== win.location.hash) {
        win.location.hash = a.getAttribute('href');
        emit(heard.window, 'hashchange', { type: 'hashchange' });
      }
      flush();
    },
    // the reader ticks or clears 'Show days with write-ups only'
    toggle: (on) => {
      h.box.checked = on;
      const ev = { type: 'change', target: h.box };
      for (let e = h.box; e; e = e.parentElement) emit(e.heard, 'change', ev);
      emit(heard.document, 'change', ev);
      flush();
    },
    // the fragment changes without a press: an edited address, Back or Forward within the page
    go: (hash) => {
      win.location.hash = hash;
      emit(heard.window, 'hashchange', { type: 'hashchange' });
      flush();
    },
    // the reader scrolls on by so many pixels
    scroll: (by) => {
      win.scrollY += by;
      emit(heard.window, 'scroll', { type: 'scroll' });
      flush();
    },
    // the photos and fonts are in: the window's load event, for a page opened with { loading: true }
    loaded: () => {
      doc.readyState = 'complete';
      emit(heard.window, 'load', { type: 'load' });
      flush();
    },
    // a page loaded later in the same browser session (a reload, another visit, another journal): the session store
    // and localStorage are kept
    again: (next) => load(Object.assign({ store: store, local: local }, next)),
  };
}

if (MODEL) {
  const ID = MODEL.ids;            // hiddenDay, hiddenMonth: what the filter hides; shownDay: a written entry
  const ALL = 'Showing all ' + MODEL.total + ' days';

  check('dom: the model is the page the script expects', () => {
    for (const k of ['log', 'box', 'live', 'wrapper', 'browse', 'dayLink', 'monthLink', 'shownLink',
                     'mnav', 'monthNav', 'emptyMonthNav', 'nextLink', 'prevLink', 'cont']) {
      assert.ok(MODEL.handles[k] >= 0, 'the page model has no ' + k);
    }
    const page = load();
    eq(page.h.dayLink.getAttribute('href'), '#' + ID.hiddenDay);
    eq(page.h.monthLink.getAttribute('href'), '#' + ID.hiddenMonth);
    eq(page.h.shownLink.getAttribute('href'), '#' + ID.shownDay);
    eq(page.h.browse.getAttribute('href'), '#days');
    // Phase 11: the month nav's links to a month with write-ups whose first day the filter hides, and to the month
    // without write-ups; the written entries' Next and Previous links; 'Continue reading' as the page writes it
    eq(page.h.monthNav.getAttribute('href'), '#' + ID.shownMonth);
    eq(page.h.emptyMonthNav.getAttribute('href'), '#' + ID.hiddenMonth);
    eq(page.h.emptyMonthNav.dataset.wu, '0');
    assert.ok(page.h.monthNav.dataset.wu !== '0', 'the month with write-ups is marked as one without');
    assert.ok(page.h.mnav.contains(page.h.monthNav) && page.h.mnav.contains(page.h.emptyMonthNav));
    assert.ok(page.monthLinks().length >= 2);
    deq(ID.shownMonthDays.slice(0, 2), [ID.hiddenDay, ID.shownDay], 'the month\'s first day is not one the filter hides');
    assert.ok(ID.hiddenMonthDays.length >= 1);
    eq(page.h.nextLink.getAttribute('href'), '#' + ID.nextShownDay);
    eq(page.h.prevLink.getAttribute('href'), '#' + ID.shownDay);
    const cont = MODEL.elements[MODEL.handles.cont];
    deq([Object.prototype.hasOwnProperty.call(cont.attrs, 'hidden'), cont.text, cont.attrs.href], [true, '', '#days']);
    deq(Object.keys(ID.continued).sort(), MODEL.elements.filter((e) => e.classes.indexOf('ser-day') !== -1).map((e) => e.id).sort(),
        'the model names the link\'s text for each day article of the page');
  });

  // ---- on load (contract 5, Reader mode)

  check('dom: a first visit shows the written entries only', () => {
    const page = load();
    eq(page.filtered(), true);
    eq(page.h.wrapper.hidden, false, 'the toggle stays hidden');
    eq(page.said(), '', 'nothing changed for the reader, so nothing is announced');
    deq(page.scrolled, []);
    eq(page.again().filtered(), true, 'the default is not a remembered choice');
  });
  check('dom: a visit to a hidden day starts with every day, and says nothing', () => {
    // contract 11.2: nothing is announced on load (a live region filled while the page loads is not reliably spoken;
    // the unchecked toggle states the mode)
    const page = load({ hash: '#' + ID.hiddenDay, navType: 'navigate' });
    eq(page.filtered(), false);
    eq(page.said(), '', 'a load that starts on every day announces nothing');
    eq(page.again().filtered(), true, 'a link that showed a hidden day is not a choice');
  });
  check('dom: a visit to a hidden month starts with every day, and says nothing', () => {
    const page = load({ hash: '#' + ID.hiddenMonth, navType: 'navigate' });
    eq(page.filtered(), false);
    eq(page.said(), '', 'a load that starts on every day announces nothing');
  });
  check('dom: a visit to a written entry keeps the filter and lands on the entry', () => {
    for (const navType of ['navigate', '', undefined]) {
      const page = load({ hash: '#' + ID.shownDay, navType: navType });
      eq(page.filtered(), true, JSON.stringify(navType));
      assert.ok(page.scrolled.length >= 1, 'no scroll to the entry with navType ' + JSON.stringify(navType));
      deq(Array.from(new Set(page.scrolled)), [ID.shownDay]);
    }
  });
  check('dom: a visit to a month with write-ups keeps the filter and lands on the month', () => {
    const page = load({ hash: '#' + ID.shownMonth, navType: 'navigate' });
    eq(page.filtered(), true);
    deq(Array.from(new Set(page.scrolled)), [ID.shownMonth]);
  });
  check('dom: a visit to another part of the page does not scroll', () => {
    for (const hash of ['#days', '#title', '']) {
      const page = load({ hash: hash, navType: 'navigate' });
      eq(page.filtered(), true, hash);
      deq(page.scrolled, [], hash);
    }
  });

  // ---- contract 10.6: no re-scroll to the hash on reload or Back / Forward

  check('dom: a reload does not scroll back to the hash', () => {
    const page = load({ hash: '#' + ID.shownDay, navType: 'reload' });
    eq(page.filtered(), true);
    deq(page.scrolled, [], 'the browser restores the reader\'s place; the script must not move it');
  });
  check('dom: Back or Forward does not scroll back to the hash', () => {
    deq(load({ hash: '#' + ID.shownDay, navType: 'back_forward' }).scrolled, []);
    deq(load({ hash: '#' + ID.shownMonth, navType: 'back_forward' }).scrolled, []);
  });
  check('dom: a prerendered page does not scroll to the hash', () => {
    deq(load({ hash: '#' + ID.shownDay, navType: 'prerender' }).scrolled, []);
  });

  check('dom: a reload of a page that is still loading never scrolls to the hash', () => {
    for (const navType of ['reload', 'back_forward', 'prerender']) {
      const page = load({ hash: '#' + ID.shownDay, navType: navType, loading: true });
      deq(page.scrolled, [], navType);
      page.loaded();
      deq(page.scrolled, [], navType + ', after the load event');
    }
  });

  // ---- a fresh visit while the page is still loading (contract 9: the entry named in the hash is in view again)

  check('dom: a visit that is still loading lands on the entry, and again once loaded', () => {
    // the photos and fonts that arrive before the load event move the entry: the second landing puts it back in view
    const page = load({ hash: '#' + ID.shownDay, navType: 'navigate', loading: true });
    deq(page.scrolled, [ID.shownDay]);
    page.loaded();
    deq(page.scrolled, [ID.shownDay, ID.shownDay]);
  });
  check('dom: the load event does not pull back a reader who has scrolled on', () => {
    // series.js lands a second time on load only while the reader is still where the first landing left them
    const page = load({ hash: '#' + ID.shownDay, navType: 'navigate', loading: true });
    deq(page.scrolled, [ID.shownDay]);
    page.scroll(800);
    const at = page.scrollY();
    page.loaded();
    deq(page.scrolled, [ID.shownDay], 'the reader was thrown back to the entry');
    eq(page.scrollY(), at);
  });

  // ---- a link followed after the load (contract 5: hashchange; 10.6: the same fragment again)

  check('dom: a hash change to a hidden day turns the filter off, says so and goes there', () => {
    const page = load();
    page.go('#' + ID.hiddenDay);
    eq(page.filtered(), false);
    eq(page.said(), ALL);
    deq(page.scrolled, [ID.hiddenDay]);
    eq(page.again().filtered(), true, 'a link that showed a hidden day is not a choice');
  });
  check('dom: a pressed link to a hidden day or month reveals it', () => {
    let page = load();
    page.press(page.h.dayLink);
    eq(page.hash(), '#' + ID.hiddenDay);
    eq(page.filtered(), false);
    eq(page.said(), ALL);
    deq(page.scrolled, [ID.hiddenDay]);
    page = load();
    page.press(page.h.monthLink);
    eq(page.filtered(), false);
    deq(page.scrolled, [ID.hiddenMonth]);
  });
  check('dom: a link to a written entry leaves the filter on', () => {
    const page = load();
    page.press(page.h.shownLink);
    eq(page.hash(), '#' + ID.shownDay);
    eq(page.filtered(), true);
    eq(page.said(), '', 'nothing was hidden, so nothing is announced');
  });
  check('dom: the same link pressed again reveals a hidden day', () => {
    // the address already ends with the fragment, so no hashchange fires: the click itself must reveal the target
    const page = load({ hash: '#' + ID.hiddenDay, navType: 'navigate' });
    page.toggle(true);
    eq(page.filtered(), true);
    page.press(page.h.dayLink);
    eq(page.hash(), '#' + ID.hiddenDay);
    eq(page.filtered(), false, 'the link did nothing: its target stays hidden');
    eq(page.said(), ALL);
    deq(page.scrolled, [ID.hiddenDay]);
  });
  check('dom: the same link pressed again reveals a hidden month', () => {
    const page = load({ hash: '#' + ID.hiddenMonth, navType: 'navigate' });
    page.toggle(true);
    page.press(page.h.monthLink);
    eq(page.filtered(), false, 'the link did nothing: its target stays hidden');
    eq(page.said(), ALL);
    deq(page.scrolled, [ID.hiddenMonth]);
  });
  check('dom: the same link pressed again changes nothing when its target is showing', () => {
    const page = load({ hash: '#' + ID.shownDay, navType: 'reload' });
    page.press(page.h.shownLink);
    eq(page.filtered(), true);
    eq(page.said(), '');
  });

  // ---- the reader's own choice (contract 9: kept for the session; 10.6: 'Browse all recordings' always is one)

  check('dom: the toggle shows every day, says so, and the choice survives a reload', () => {
    const page = load();
    page.toggle(false);
    eq(page.filtered(), false);
    eq(page.said(), ALL);
    const reloaded = page.again({ navType: 'reload' });
    eq(reloaded.filtered(), false);
    eq(reloaded.said(), '', 'a reload that keeps every day showing announces nothing');
    const back = page.again();
    back.toggle(true);
    eq(back.filtered(), true);
    assert.ok(back.said() && back.said() !== ALL, 'turning the filter on is announced too');
    eq(back.again({ navType: 'reload' }).filtered(), true);
  });
  check('dom: the choice is kept under this journal\'s own address', () => {
    // contract 9: sessionStorage key 'ser-only:' + pathname, so one journal's choice is not another's
    const page = load();
    deq(page.stored(), [], 'a load alone stores nothing');
    page.toggle(false);
    deq(page.stored(), ['ser-only:' + MODEL.pathname]);
    eq(page.again().filtered(), false);
    eq(page.again({ pathname: MODEL.pathname.replace(/[^/]+\/$/, 'another-journal/') }).filtered(), true);
  });
  check('dom: a remembered "write-ups only" still gives way to a link to a hidden entry', () => {
    const page = load({ hash: '#' + ID.hiddenMonth });
    page.toggle(true);
    eq(page.again({ hash: '#' + ID.hiddenDay }).filtered(), false);
    eq(page.again().filtered(), true);
  });
  check('dom: Browse all recordings shows every day, says so, and is remembered', () => {
    const page = load();
    page.press(page.h.browse);
    eq(page.hash(), '#days');
    eq(page.filtered(), false);
    eq(page.said(), ALL);
    eq(page.again({ hash: '#days', navType: 'reload' }).filtered(), false);
    eq(page.again().filtered(), false);
  });
  check('dom: Browse all recordings is remembered when a link had already shown every day', () => {
    // the filter is off because of the link, which is not a choice; the press is one and must hold after a reload
    const page = load({ hash: '#' + ID.hiddenDay, navType: 'navigate' });
    eq(page.filtered(), false);
    page.press(page.h.browse);
    eq(page.filtered(), false);
    eq(page.again({ hash: '#days', navType: 'reload' }).filtered(), false, 'the press was forgotten');
  });
  check('dom: Browse all recordings replaces an earlier "write-ups only"', () => {
    const page = load({ hash: '#' + ID.hiddenMonth });
    page.toggle(true);                       // a choice: write-ups only
    page.go('#' + ID.hiddenDay);             // a link shows every day again, which is not a choice
    eq(page.filtered(), false);
    page.press(page.h.browse);               // the last word: every recording
    eq(page.again({ hash: '#days', navType: 'reload' }).filtered(), false, 'the older choice came back');
  });

  // ---- review gate: an address that names an id inside a hidden day or month (its number, its title, a month's heading)

  // ID.inHiddenDay: the number and the title of the hidden day; ID.inHiddenMonth: the heading of the hidden month and the
  // title of a hidden day in it; ID.inShown: the same ids of a written day and of a month with write-ups
  const IN_HIDDEN = ID.inHiddenDay.concat(ID.inHiddenMonth);

  check('dom: the model names ids inside hidden and written entries', () => {
    eq(ID.inHiddenDay.length, 2);
    assert.ok(ID.inHiddenMonth.length >= 2 && ID.inShown.length >= 3);
    const page = load();
    eq(page.filtered(), true);
    // while the filter is on, the first are not on the page and the others are: what an address to them lands on
    for (const id of IN_HIDDEN) eq(page.rendered(id), false, id);
    for (const id of ID.inShown) eq(page.rendered(id), true, id);
    page.toggle(false);
    for (const id of IN_HIDDEN.concat(ID.inShown)) eq(page.rendered(id), true, id + ', every day showing');
  });
  check('dom: a visit to the number or the title of a hidden day starts with every day, on that element', () => {
    for (const id of ID.inHiddenDay) {
      for (const navType of ['navigate', '', undefined, 'reload', 'back_forward']) {
        const page = load({ hash: '#' + id, navType: navType });
        eq(page.filtered(), false, id + ' ' + JSON.stringify(navType));
        eq(page.rendered(id), true, 'the address names an element that is not on the page: ' + id);
        eq(page.said(), '', 'a load that starts on every day announces nothing');
        deq(page.scrolled, [], 'nothing was shortened: the browser\'s own jump to the fragment stands');
      }
      eq(load({ hash: '#' + id }).again().filtered(), true, 'a link that showed a hidden day is not a choice');
    }
  });
  check('dom: a visit to the heading of a hidden month, or to a day inside it, starts with every day', () => {
    for (const id of ID.inHiddenMonth) {
      const page = load({ hash: '#' + id, navType: 'navigate' });
      eq(page.filtered(), false, id);
      eq(page.rendered(id), true, 'the address names an element that is not on the page: ' + id);
      eq(page.said(), '');
      deq(page.scrolled, []);
    }
  });
  check('dom: a remembered "write-ups only" gives way to an address inside a hidden day', () => {
    const page = load();
    page.toggle(false);
    page.toggle(true);                       // a choice: write-ups only
    for (const id of IN_HIDDEN) eq(page.again({ hash: '#' + id }).filtered(), false, id);
    eq(page.again().filtered(), true);
  });
  check('dom: a visit to the same ids of a written day or month keeps the filter and lands on the element', () => {
    for (const id of ID.inShown) {
      const page = load({ hash: '#' + id, navType: 'navigate' });
      eq(page.filtered(), true, id);
      eq(page.rendered(id), true, id);
      eq(page.said(), '');
      deq(Array.from(new Set(page.scrolled)), [id]);
      deq(load({ hash: '#' + id, navType: 'reload' }).scrolled, [], id + ', on a reload');
    }
  });
  check('dom: a hash change to an id inside a hidden day or month reveals it, says so and goes there', () => {
    for (const id of IN_HIDDEN) {
      const page = load();
      eq(page.rendered(id), false, id);
      page.go('#' + id);
      eq(page.filtered(), false, id);
      eq(page.said(), ALL, id);
      deq(page.scrolled, [id]);
      eq(page.rendered(id), true, id);
      eq(page.again().filtered(), true, 'a link that showed a hidden day is not a choice');
    }
  });
  check('dom: a hash change to the same ids of a written day or month leaves the filter on and says nothing', () => {
    for (const id of ID.inShown) {
      const page = load();
      page.go('#' + id);
      eq(page.filtered(), true, id);
      eq(page.said(), '', 'nothing was hidden, so nothing is announced');
      deq(page.scrolled, []);
    }
  });
  check('dom: after the reader turns the filter on again, the same address reveals the day once more', () => {
    const id = ID.inHiddenDay[1];
    const page = load({ hash: '#' + id, navType: 'navigate' });
    page.toggle(true);
    eq(page.rendered(id), false);
    page.go('#' + ID.shownDay);
    eq(page.filtered(), true);
    page.go('#' + id);
    eq(page.filtered(), false);
    eq(page.said(), ALL);
    deq(page.scrolled.slice(-1), [id]);
  });
  // The list itself: a load with a fragment makes the script search it whatever the collecting code looks like.
  const collected = () => load({ hash: '#' + ID.shownDay, navType: 'navigate' }).hidden();
  check('dom: the ids the script takes for hidden are the hidden days and months and every id inside them', () => {
    // MODEL.hiddenIds: what series.css takes out of the page while the filter is on, by id (tests/test_series_js.py)
    deq(Array.from(new Set(collected())).sort(), MODEL.hiddenIds.slice().sort());
    for (const id of IN_HIDDEN.concat([ID.hiddenDay, ID.hiddenMonth])) assert.ok(MODEL.hiddenIds.indexOf(id) !== -1, id);
    for (const id of ID.inShown.concat([ID.shownDay, ID.shownMonth, 'days', 'ser-only', 'ser-live'])) eq(MODEL.hiddenIds.indexOf(id), -1, id);
  });
  check('dom: an id inside a hidden day of a hidden month is collected once', () => {
    // MODEL.hiddenInside: the ids inside a hidden day or month that are not such a day or month themselves. The number
    // and the title of a hidden day in a hidden month are met twice: inside the month, and inside the day
    const list = collected();
    assert.ok(MODEL.hiddenInside.length >= 6, 'the model names too few ids inside hidden entries');
    for (const id of MODEL.hiddenInside) eq(list.filter((x) => x === id).length, 1, id);
    for (const id of ID.inHiddenMonth) assert.ok(MODEL.hiddenInside.indexOf(id) !== -1, id + ' is not among them');
  });
  check('dom: every id the filter hides is listed once, a hidden day inside a hidden month too', () => {
    // such a day is met twice as well: as an id inside its month, and as a hidden day in its own right
    const list = collected();
    deq(list.filter((id, i) => list.indexOf(id) !== i), [], 'ids listed more than once');
    eq(list.length, MODEL.hiddenIds.length);
    // the model has such a day: the one whose title is among the ids inside the hidden month
    const days = ID.inHiddenMonth.filter((id) => /^day-.+-t$/.test(id)).map((id) => id.replace(/-t$/, ''));
    assert.ok(days.length >= 1, 'the model names no hidden day inside the hidden month');
    for (const id of days) {
      assert.ok(MODEL.hiddenIds.indexOf(id) !== -1, id + ' is not hidden');
      eq(list.filter((x) => x === id).length, 1, id);
    }
  });

  // ---- Phase 11, a11y-07: under the filter a month without write-ups stays a link in the month nav, lighter and named
  // so; a press on it reveals the month through the hashchange (the old aria-disabled / tabindex="-1" made it a dead
  // stop for keyboard and screen-reader users)

  const EMPTY = ', no write-ups';
  // what the script appended to a month link, as the reader's tools meet it: [tag, classes, text]
  const notes = (page, a) => page.appended(a).map((k) => [k.tagName, k.className, k.textContent]);
  const pageText = (handle) => MODEL.elements[MODEL.handles[handle]].text;    // a link's own words on the page

  check('dom: no month-nav link carries aria-disabled or tabindex, under the filter or without it', () => {
    const page = load();
    eq(page.filtered(), true);
    const bare = (when) => {
      for (const a of page.monthLinks()) {
        eq(a.getAttribute('aria-disabled'), null, a.getAttribute('href') + ' carries aria-disabled ' + when);
        eq(a.hasAttribute('tabindex'), false, a.getAttribute('href') + ' carries tabindex ' + when);
      }
    };
    bare('in the default (filtered) view');
    page.toggle(false);
    bare('with every day showing');
    page.toggle(true);
    bare('with the filter on again');
    page.press(page.h.emptyMonthNav);
    bare('after a press revealed the month');
    const all = load({ hash: '#' + ID.hiddenDay, navType: 'navigate' });
    eq(all.filtered(), false);
    for (const a of all.monthLinks()) {
      eq(a.getAttribute('aria-disabled'), null, a.getAttribute('href'));
      eq(a.hasAttribute('tabindex'), false, a.getAttribute('href'));
    }
  });
  check('dom: under the filter a month without write-ups carries is-empty and the words ", no write-ups"', () => {
    const page = load();
    eq(page.filtered(), true);
    for (const a of page.monthLinks()) {
      const empty = a.dataset.wu === '0';
      eq(a.classList.contains('is-empty'), empty, a.getAttribute('href'));
      deq(notes(page, a), empty ? [['SPAN', 'sr ser-mn-none', EMPTY]] : [], a.getAttribute('href'));
    }
    deq(page.monthLinks().filter((a) => a.classList.contains('is-empty')).map((a) => a.getAttribute('href')), ['#' + ID.hiddenMonth]);
    // what a screen reader hears: the month's own words, then the note (visually hidden: .sr)
    eq(page.h.emptyMonthNav.textContent, pageText('emptyMonthNav') + EMPTY);
    eq(page.h.monthNav.textContent, pageText('monthNav'));
    // the note hangs in the link, where the script's own lookup finds it again
    const note = page.appended(page.h.emptyMonthNav)[0];
    eq(note.parentElement, page.h.emptyMonthNav);
    eq(page.h.emptyMonthNav.querySelector('.ser-mn-none'), note);
    eq(page.h.monthNav.querySelector('.ser-mn-none'), null);
  });
  check('dom: is-empty and ", no write-ups" go when the filter is turned off, and come back once when it is on again', () => {
    const page = load();
    const june = page.h.emptyMonthNav;
    page.toggle(false);
    eq(page.filtered(), false);
    for (const a of page.monthLinks()) {
      eq(a.classList.contains('is-empty'), false, a.getAttribute('href'));
      deq(notes(page, a), [], a.getAttribute('href') + ' keeps its note with every day showing');
    }
    eq(june.querySelector('.ser-mn-none'), null);
    eq(june.textContent, pageText('emptyMonthNav'));
    page.toggle(true);
    eq(june.classList.contains('is-empty'), true);
    deq(notes(page, june), [['SPAN', 'sr ser-mn-none', EMPTY]]);
    page.toggle(true);                       // the box changed again with the filter on: apply() runs once more
    deq(notes(page, june), [['SPAN', 'sr ser-mn-none', EMPTY]], 'the note is added on every pass');
    eq(june.textContent, pageText('emptyMonthNav') + EMPTY);
    // a visit that starts with every day showing has neither
    const all = load({ hash: '#' + ID.hiddenMonth, navType: 'navigate' });
    eq(all.filtered(), false);
    for (const a of all.monthLinks()) {
      eq(a.classList.contains('is-empty'), false, a.getAttribute('href'));
      deq(notes(all, a), [], a.getAttribute('href'));
    }
  });
  check('dom: pressing the month-nav link of a month without write-ups reveals it and says "Showing all N days"', () => {
    const page = load();
    eq(page.rendered(ID.hiddenMonth), false);
    page.press(page.h.emptyMonthNav);
    eq(page.hash(), '#' + ID.hiddenMonth);
    eq(page.filtered(), false);
    eq(page.said(), ALL);
    deq(page.scrolled, [ID.hiddenMonth]);
    eq(page.rendered(ID.hiddenMonth), true);
    eq(page.h.emptyMonthNav.classList.contains('is-empty'), false);
    deq(notes(page, page.h.emptyMonthNav), []);
    eq(page.again().filtered(), true, 'a link that showed a hidden month is not a choice');
    // pressed again once the reader has put the filter back: the same fragment fires no hashchange, the click reveals it
    page.toggle(true);
    eq(page.h.emptyMonthNav.classList.contains('is-empty'), true);
    page.press(page.h.emptyMonthNav);
    eq(page.filtered(), false, 'the second press did nothing: the month stays hidden');
    eq(page.said(), ALL);
    deq(page.scrolled, [ID.hiddenMonth, ID.hiddenMonth]);
  });

  // ---- Phase 11, features-08: 'Continue reading', the last entry this browser opened on this journal

  // localStorage key 'ser-last:' + pathname; ID.continued: {day id: the link's text when that day is the one kept}
  const LAST = 'ser-last:' + MODEL.pathname;
  const lastOf = (id) => { const o = {}; o[LAST] = id; return o; };
  // the link as the reader meets it: [hidden, text, href]; NONE: as the page writes it, hidden, empty, to the day log
  const offer = (page) => [page.h.cont.hidden, page.h.cont.textContent, page.h.cont.getAttribute('href')];
  const NONE = [true, '', '#days'];
  const offered = (id) => [false, ID.continued[id], '#' + id];

  check('dom: Continue reading stays hidden and empty without a stored entry', () => {
    for (const hash of ['', '#days', '#title', '#' + ID.shownMonth, '#' + ID.hiddenMonth]) {
      const page = load({ hash: hash, navType: 'navigate' });
      deq(offer(page), NONE, JSON.stringify(hash));
      deq(page.kept(), {}, 'a load at ' + JSON.stringify(hash) + ' stores nothing');
      deq(offer(page.again()), NONE, JSON.stringify(hash) + ', on a later visit');
    }
  });
  check('dom: pressing a link to a day keeps that day under this journal\'s address', () => {
    const page = load();
    page.press(page.h.shownLink);            // the title action 'Read the first written entry'
    deq(page.kept(), lastOf(ID.shownDay));
    page.press(page.h.dayLink);              // a highlight, to a day the filter hides
    deq(page.kept(), lastOf(ID.hiddenDay));
    eq(page.filtered(), false, 'keeping the day got in the way of revealing it');
    eq(page.said(), ALL);
    deq(page.stored(), [], 'the entry goes to localStorage, not to the session store');
  });
  check('dom: pressing a month-nav link keeps the first day the reader can see in that month', () => {
    let page = load();
    eq(page.filtered(), true);
    page.press(page.h.monthNav);             // under the filter the month's first day is hidden: its first written one
    deq(page.kept(), lastOf(ID.shownDay));
    page = load();
    page.toggle(false);
    page.press(page.h.monthNav);             // with every day showing: the month's first day
    deq(page.kept(), lastOf(ID.shownMonthDays[0]));
    page = load();
    page.press(page.h.emptyMonthNav);        // a month without write-ups shows no day under the filter: its first
    deq(page.kept(), lastOf(ID.hiddenMonthDays[0]));
    eq(page.filtered(), false);
    page = load();
    page.press(page.h.monthLink);            // the overview's month index is a month link too
    deq(page.kept(), lastOf(ID.hiddenMonthDays[0]));
  });
  check('dom: pressing a written entry\'s Next or Previous link keeps the entry it leads to', () => {
    const page = load();
    page.press(page.h.nextLink);
    deq(page.kept(), lastOf(ID.nextShownDay));
    page.press(page.h.prevLink);
    deq(page.kept(), lastOf(ID.shownDay));
  });
  check('dom: a link to another part of the page keeps nothing, and leaves the entry kept', () => {
    const page = load();
    page.press(page.h.browse);               // '#days'
    deq(page.kept(), {});
    page.press(page.h.nextLink);
    page.press(page.h.browse);
    deq(page.kept(), lastOf(ID.nextShownDay));
  });
  check('dom: arriving at a day keeps it; arriving anywhere else keeps nothing', () => {
    for (const id of [ID.shownDay, ID.nextShownDay, ID.hiddenDay]) {
      for (const navType of ['navigate', 'reload', undefined]) {
        deq(load({ hash: '#' + id, navType: navType }).kept(), lastOf(id), id + ' ' + JSON.stringify(navType));
      }
    }
    deq(load({ hash: '#' + ID.nextShownDay.replace(/-/g, '%2D'), navType: 'navigate' }).kept(), lastOf(ID.nextShownDay));
    // only a day article is kept: not the number or the title inside one, a month, the day log or an id the page lacks
    for (const hash of ['#' + ID.inShown[0], '#' + ID.inShown[1], '#' + ID.shownMonth, '#days', '#day-99']) {
      deq(load({ hash: hash, navType: 'navigate' }).kept(), {}, hash);
    }
  });
  check('dom: on a later visit Continue reading offers the entry kept, by its day and title, linked to it', () => {
    const page = load();
    page.press(page.h.nextLink);
    deq(offer(page), NONE, 'offered on the next visit, not on this one');
    const later = page.again();
    deq(offer(later), offered(ID.nextShownDay));
    eq(later.filtered(), true);
    // every day of the journal as the link names it: 'Day N · title'; a day without a title by its number alone
    for (const id of Object.keys(ID.continued)) {
      deq(offer(load({ local: lastOf(id) })), offered(id), id);
    }
    // the link pressed: to a day the filter hides, it reveals the day like any link to one, and keeps it again
    const back = load({ local: lastOf(ID.hiddenDay) });
    back.press(back.h.cont);
    eq(back.hash(), '#' + ID.hiddenDay);
    eq(back.filtered(), false);
    eq(back.said(), ALL);
    deq(back.scrolled, [ID.hiddenDay]);
    deq(back.kept(), lastOf(ID.hiddenDay));
  });
  check('dom: pressing Continue reading keeps the entry it opens', () => {
    // following the offer is reading that entry: after another entry was opened since the page loaded, the press on
    // the (older) offer makes it the one kept again, so the next visit offers where the reader went last
    const page = load({ local: lastOf(ID.hiddenDay) });
    deq(offer(page), offered(ID.hiddenDay));
    page.press(page.h.nextLink);
    deq(page.kept(), lastOf(ID.nextShownDay));
    page.press(page.h.cont);
    eq(page.hash(), '#' + ID.hiddenDay);
    eq(page.filtered(), false, 'the offer to a hidden day did not reveal it');
    deq(page.kept(), lastOf(ID.hiddenDay), 'the press on Continue reading was not kept');
  });
  check('dom: Continue reading works on a journal without the filter toggle', () => {
    // a journal whose days are all written (or none) has no #ser-only: the script stops before the filter, after
    // 'Continue reading' is set up
    const page = load({ drop: ['ser-only'], local: lastOf(ID.nextShownDay) });
    deq(offer(page), offered(ID.nextShownDay));
    page.press(page.h.prevLink);
    deq(page.kept(), lastOf(ID.shownDay));
    deq(load({ drop: ['ser-only'], hash: '#' + ID.hiddenDay, navType: 'navigate' }).kept(), lastOf(ID.hiddenDay));
  });
  check('dom: Continue reading is kept per journal', () => {
    const page = load();
    page.press(page.h.nextLink);
    deq(Object.keys(page.kept()), [LAST]);
    deq(offer(page.again({ pathname: MODEL.pathname.replace(/[^/]+\/$/, 'another-journal/') })), NONE);
    deq(offer(page.again()), offered(ID.nextShownDay));
  });
  check('dom: Continue reading is not offered for the entry the address already names', () => {
    const id = ID.nextShownDay;
    for (const hash of ['#' + id, '#' + id.replace(/-/g, '%2D')]) {
      const page = load({ local: lastOf(id), hash: hash, navType: 'navigate' });
      deq(offer(page), NONE, hash);
      deq(page.kept(), lastOf(id), hash);
    }
    // another entry in the address: the one kept is offered, and the one arrived at is kept for next time
    const page = load({ local: lastOf(id), hash: '#' + ID.shownDay, navType: 'navigate' });
    deq(offer(page), offered(id));
    deq(page.kept(), lastOf(ID.shownDay));
  });
  check('dom: a stored id that is not a day article of this page offers nothing', () => {
    for (const id of ['day-99', ID.inShown[1], ID.shownMonth, 'days', 'ser-only', '']) {
      const page = load({ local: lastOf(id) });
      deq(offer(page), NONE, JSON.stringify(id));
      eq(page.filtered(), true, JSON.stringify(id));
    }
  });
  check('dom: where localStorage throws (a private window) the page still works and offers nothing', () => {
    // 'calls': each getItem / setItem throws; 'access': reading window.localStorage itself throws. The store holds an
    // entry the browser will not hand over
    for (const mode of ['calls', 'access']) {
      let page = null;
      assert.doesNotThrow(() => { page = load({ private: mode, local: lastOf(ID.nextShownDay) }); }, mode);
      deq(offer(page), NONE, mode);
      eq(page.filtered(), true, mode);
      eq(page.h.wrapper.hidden, false, mode);
      eq(page.h.emptyMonthNav.classList.contains('is-empty'), true, mode);
      assert.doesNotThrow(() => page.press(page.h.shownLink), mode);
      assert.doesNotThrow(() => page.press(page.h.monthNav), mode);
      page.press(page.h.dayLink);
      eq(page.filtered(), false, mode + ': the link to a hidden day did not reveal it');
      eq(page.said(), ALL, mode);
      page.toggle(true);
      eq(page.filtered(), true, mode);
      deq(page.kept(), lastOf(ID.nextShownDay), mode + ': the store was written');
      // arriving at a day: nothing kept, and still landed on
      const at = load({ private: mode, hash: '#' + ID.shownDay, navType: 'navigate' });
      deq(at.kept(), {}, mode);
      deq(Array.from(new Set(at.scrolled)), [ID.shownDay], mode);
      deq(offer(at.again({ private: mode })), NONE, mode);
    }
  });

  // GAPS: a case in which the page does not do what is said of it. Run only when asked for ('gap:<name>', after every
  // check above) by a test of tests/test_series_js.py that is marked as an expected failure; when the page is put
  // right, the case becomes a check above. None at present: the one of round 2 (an id listed twice) is the check
  // 'every id the filter hides is listed once' above.
  const GAPS = {};
  if (process.argv[4] && /^gap:/.test(process.argv[4])) {
    assert.ok(Object.prototype.hasOwnProperty.call(GAPS, GAP), 'unknown gap: ' + GAP);
    check('gap: ' + GAP, GAPS[GAP]);
  }
}

console.log('series_js_harness: ' + checks + ' checks passed');
