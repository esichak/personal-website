#!/usr/bin/env node
'use strict';
/* Phase 2T: unit tests for the pure functions behind the tick list page: assets/js/pages/explore.js (the shared helpers
   norm, tokens, parseState, serialize, chipLabel) and assets/js/pages/ticklist.js (its state keys and defaults, the scope
   predicate, the sort comparators, chipLabel). Phase 4: goalShown, the predicate the page hides and counts its goal
   cards with (the scope, every filter, the search tokens), and adoptForm, what the page takes over from a form the
   visitor used before the script arrived.

   Round 6 of the review gate: Explore.historyStep, the rule for history entries that trips.js and ticklist.js both
   take from explore.js (its truth table is held here, where the rule is defined; tests/trips_js_harness.js keeps its
   own checks of the same function through TRX.historyStep). And, given a page model, the page part of ticklist.js
   itself: the whole script run against a stand-in for the browser (tests/page_standin.js, shared with the trips
   harness) on a Tick list page that sitegen.pages.ticklist generated from a synthetic site, with a visitor's typing,
   Enter, filters, a link to a fragment, Back and Forward played on it and the history read after every step (the
   "page:" checks at the end of this file).

   Run by tests/test_ticklist_js.py (skipped when node is missing); by hand:
     node tests/ticklist_js_harness.js [explore.js [ticklist.js [page-model.json [gap:<name>]]]]
   - explore.js, ticklist.js: other modules with the same exports (used to prove the harness fails a wrong one); '' for
     the site's own.
   - page-model.json: a Tick list page as tests/test_ticklist_js.py describes it (page_model); with it the two scripts
     are run whole and the "page:" checks are added.
   - gap:<name>: also the check of that name, a case the page does not handle yet (GAPS: none at present, so any name
     is refused).
   Every failed assertion throws, so the process exits non-zero. norm() is held to tests/norm_cases.json, the table
   tests/test_search.py checks search.normalize against. Card records are shaped like the cards' data attributes
   (li.dataset: strings, archived '1' | '0'), which is all the page's filtering reads. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const standin = require('./page_standin.js');

const PAGES = path.join(__dirname, '..', 'assets', 'js', 'pages');
const EXPLORE = path.resolve(process.argv[2] || path.join(PAGES, 'explore.js'));
const TICKLIST = path.resolve(process.argv[3] || path.join(PAGES, 'ticklist.js'));
const CASES = path.join(__dirname, 'norm_cases.json');

assert.strictEqual(typeof document, 'undefined', 'the harness runs without a DOM');
assert.ok(fs.existsSync(EXPLORE), 'missing ' + EXPLORE);
assert.ok(fs.existsSync(TICKLIST), 'missing ' + TICKLIST);
const X = require(EXPLORE);     // must export before touching the DOM (there is none here)
const TKL = require(TICKLIST);

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
function pick(obj, names, what) {
  for (const n of names) if (obj && typeof obj[n] !== 'undefined') return obj[n];
  throw new Error('ticklist.js exports none of ' + names.join(' / ') + ' (' + what + ')');
}

// ---------------------------------------------------------------- exports

check('explore exports', () => {
  eq(typeof X, 'object');
  for (const name of ['norm', 'tokens', 'parseState', 'serialize', 'chipLabel', 'historyStep']) {
    eq(typeof X[name], 'function', 'Explore.' + name + ' is not a function');
  }
});
check('ticklist exports', () => {
  eq(typeof TKL, 'object');
  eq(typeof TKL.parseState, 'function', 'TKL.parseState');
  eq(typeof TKL.chipLabel, 'function', 'TKL.chipLabel');
  eq(typeof pick(TKL, ['inScope', 'scope', 'matchesScope', 'scopeMatch'], 'the scope predicate'), 'function');
  eq(typeof pick(TKL, ['compare', 'comparator', 'comparators', 'SORTS'], 'the sort comparators'), 'function', 'compare(sort) must be a function');
});

// ---------------------------------------------------------------- norm / tokens (parity with search.normalize)

const cases = JSON.parse(fs.readFileSync(CASES, 'utf8'));
assert.ok(Array.isArray(cases) && cases.length > 0, 'norm_cases.json is empty');
for (const [input, want] of cases) {
  check('norm ' + JSON.stringify(input), () => eq(X.norm(input), want));
}
check('norm contract examples', () => {
  eq(X.norm("Lover's Leap: Corrugation Corner"), 'lover s leap corrugation corner');
  eq(X.norm("Aiguille d'Example – Vallée"), 'aiguille d example vallee');
  eq(X.norm(''), '');
});
check('tokens', () => {
  deq(X.tokens('  Ridge   Idea '), ['ridge', 'idea']);
  deq(X.tokens(''), []);
  deq(X.tokens(' --- '), []);
});

// ---------------------------------------------------------------- state keys and defaults

const KEYS = ['q', 'activity', 'region', 'status', 'priority', 'month', 'gpx', 'scope', 'sort', 'view'];
const DEFAULTS = { q: '', activity: 'all', region: '', status: '', priority: '', month: '', gpx: false, scope: 'active', sort: 'priority', view: 'cards' };
const ALLOWED = {
  activity: ['all', 'ski', 'climb', 'hike', 'mtb'],
  region: ['', 'alps', 'boise', 'eastern-sierra', 'lake-tahoe'],
  status: ['', 'idea', 'researching', 'shortlisted', 'attempted', 'completed'],
  priority: ['', 'high', 'normal', 'someday'],
  month: ['', '4', '5', '6', '7'],
  scope: ['all', 'active', 'shortlisted', 'completed', 'archived'],
  sort: ['priority', 'added', 'name'],
  view: ['cards', 'list'],
};
const withDefaults = (o) => Object.assign({}, DEFAULTS, o);

check('ticklist KEYS and DEFAULTS', () => {
  deq(pick(TKL, ['KEYS', 'keys'], 'the state keys'), KEYS);
  deq(pick(TKL, ['DEFAULTS', 'defaults'], 'the state defaults'), DEFAULTS);
});

// ---------------------------------------------------------------- Explore.parseState / serialize with the ticklist state

const st = (s) => X.parseState(s, ALLOWED, DEFAULTS, KEYS);
const tst = (s) => TKL.parseState(s, ALLOWED);

check('parseState defaults', () => {
  deq(st(''), DEFAULTS);
  deq(st('?'), DEFAULTS);
  deq(tst(''), DEFAULTS);
  deq(st(undefined), DEFAULTS);
});
check('parseState reads every key, with or without the leading ?', () => {
  const want = { q: 'ridge', activity: 'hike', region: 'eastern-sierra', status: 'shortlisted', priority: 'high', month: '6', gpx: true, scope: 'all', sort: 'name', view: 'list' };
  const qs = 'q=ridge&activity=hike&region=eastern-sierra&status=shortlisted&priority=high&month=6&gpx=1&scope=all&sort=name&view=list';
  deq(st('?' + qs), want);
  deq(st(qs), want);
  deq(tst('?' + qs), want);
});
check('parseState contract example url', () => {
  deq(st('?activity=hike&region=eastern-sierra&status=shortlisted&priority=high'),
      withDefaults({ activity: 'hike', region: 'eastern-sierra', status: 'shortlisted', priority: 'high' }));
});
check('parseState ignores unknown keys', () => {
  deq(st('?foo=bar&utm_source=x&year=2026&writeup=1&q=dana'), withDefaults({ q: 'dana' }));
});
check('parseState resets values outside allowed', () => {
  deq(st('?activity=swim&region=mars&status=done&priority=urgent&month=13&scope=mine&sort=random&view=table'), DEFAULTS);
  deq(st('?status=SHORTLISTED'), DEFAULTS);   // exact values only
});
check('parseState keeps valid values beside invalid ones', () => {
  deq(st('?activity=ski&region=mars&status=idea'), withDefaults({ activity: 'ski', status: 'idea' }));
});
check('parseState gpx is true only for gpx=1', () => {
  eq(st('?gpx=1').gpx, true);
  for (const v of ['0', 'true', 'yes', '', '2', 'on']) eq(st('?gpx=' + v).gpx, false, 'gpx=' + v);
  eq(st('?q=a').gpx, false);
});
check('parseState decodes the query text as a form-encoded value', () => {
  eq(st('?q=aiguille%20d%27example').q, "aiguille d'example");
  eq(st('?q=short+couloir').q, 'short couloir');
  eq(st('?q=vall%C3%A9e').q, 'vallée');
  eq(st('?q=').q, '');
});
check('parseState returns exactly the ten state keys', () => {
  deq(Object.keys(st('?q=a&zzz=1')).sort(), KEYS.slice().sort());
  deq(Object.keys(tst('')).sort(), KEYS.slice().sort());
});

const ser = (o) => String(X.serialize(withDefaults(o), DEFAULTS, KEYS)).replace(/^\?/, '');
check('serialize writes only non-default keys in key order', () => {
  eq(ser({}), '');
  eq(ser({ status: 'shortlisted', q: 'dana' }), 'q=dana&status=shortlisted');
  eq(ser({ gpx: true }), 'gpx=1');
  eq(ser({ gpx: false }), '');
  eq(ser({ scope: 'active', sort: 'priority', view: 'cards' }), '');
  eq(ser({ view: 'list', scope: 'all', activity: 'ski' }), 'activity=ski&scope=all&view=list');
  eq(ser({ month: '6', priority: 'high' }), 'priority=high&month=6');
});
check('serialize round-trips through parseState', () => {
  const states = [
    { q: "aiguille d'example", activity: 'climb', scope: 'all' },
    { q: 'short couloir', status: 'shortlisted', priority: 'high', month: '4', gpx: true, sort: 'name', view: 'list' },
    { region: 'lake-tahoe', scope: 'archived' },
  ];
  for (const s of states) deq(st('?' + ser(s)), withDefaults(s));
  if (typeof TKL.serialize === 'function') {
    for (const s of states) deq(tst('?' + String(TKL.serialize(withDefaults(s))).replace(/^\?/, '')), withDefaults(s));
  }
});

// ---------------------------------------------------------------- the scope predicate

const inScope = pick(TKL, ['inScope', 'scope', 'matchesScope', 'scopeMatch'], 'the scope predicate');
const CARDS = {
  idea: { status: 'idea', archived: '0' },
  short: { status: 'shortlisted', archived: '0' },
  shortArchived: { status: 'shortlisted', archived: '1' },
  attempted: { status: 'attempted', archived: '0' },
  done: { status: 'completed', archived: '0' },
  doneArchived: { status: 'completed', archived: '1' },
  researchingArchived: { status: 'researching', archived: '1' },
};
const TRUTH = {
  all: ['idea', 'short', 'shortArchived', 'attempted', 'done', 'doneArchived', 'researchingArchived'],
  active: ['idea', 'short', 'attempted'],
  shortlisted: ['short'],
  completed: ['done', 'doneArchived'],
  archived: ['shortArchived', 'doneArchived', 'researchingArchived'],
};
for (const scope of Object.keys(TRUTH)) {
  check('scope ' + scope, () => {
    const got = Object.keys(CARDS).filter((k) => !!inScope(CARDS[k], scope));
    deq(got, TRUTH[scope]);
  });
}

// ---------------------------------------------------------------- the sort comparators

const compareOf = (sort) => {
  if (typeof TKL.compare === 'function') return TKL.compare(sort);
  if (typeof TKL.comparator === 'function') return TKL.comparator(sort);
  const table = TKL.comparators || TKL.SORTS;
  return table[sort];
};
const R = {
  a: { slug: 'a-high-old', title: 'Delta', priority: 'high', added: '2025-01-01' },
  b: { slug: 'b-high-new', title: 'Charlie', priority: 'high', added: '2026-06-01' },
  c: { slug: 'c-high-nodate', title: 'Bravo', priority: 'high', added: '' },
  d: { slug: 'd-normal-new', title: 'Echo', priority: 'normal', added: '2026-07-01' },
  e: { slug: 'e-normal-same', title: 'Alpha', priority: 'normal', added: '2026-05-01' },
  f: { slug: 'f-normal-same', title: 'Foxtrot', priority: 'normal', added: '2026-05-01' },
  g: { slug: 'g-someday-new', title: 'Golf', priority: 'someday', added: '2026-09-01' },
  h: { slug: 'h-normal-nodate', title: 'Hotel', priority: 'normal', added: '' },
};
const shuffled = () => ['g', 'e', 'h', 'c', 'a', 'f', 'd', 'b'].map((k) => R[k]);
const sortedSlugs = (sort) => shuffled().sort(compareOf(sort)).map((r) => r.slug);

check('sort priority: high > normal > someday, newest added first, missing dates last, then slug', () => {
  deq(sortedSlugs('priority'), ['b-high-new', 'a-high-old', 'c-high-nodate', 'd-normal-new', 'e-normal-same', 'f-normal-same', 'h-normal-nodate', 'g-someday-new']);
});
check('sort added: newest first, missing dates last, then slug', () => {
  deq(sortedSlugs('added'), ['g-someday-new', 'd-normal-new', 'b-high-new', 'e-normal-same', 'f-normal-same', 'a-high-old', 'c-high-nodate', 'h-normal-nodate']);
});
check('sort name: title A-Z', () => {
  deq(sortedSlugs('name'), ['e-normal-same', 'c-high-nodate', 'b-high-new', 'a-high-old', 'd-normal-new', 'f-normal-same', 'g-someday-new', 'h-normal-nodate']);
});
check('comparators give every pair of distinct records one definite order', () => {
  for (const sort of ['priority', 'added', 'name']) {
    const cmp = compareOf(sort);
    const recs = shuffled();
    for (const x of recs) for (const y of recs) {
      if (x === y) continue;
      const xy = cmp(x, y), yx = cmp(y, x);
      assert.ok(xy !== 0 && Math.sign(xy) === -Math.sign(yx), sort + ' ' + x.slug + ' vs ' + y.slug);
    }
  }
});

// ---------------------------------------------------------------- chipLabel

const NAMES = {
  activity: { ski: 'Backcountry Ski', hike: 'Hiking' },
  region: { 'lake-tahoe': 'Lake Tahoe' },
  status: { shortlisted: 'Shortlisted' },
  priority: { high: 'High priority' },
  month: { '6': 'June' },
  gpx: { '1': 'Has a route (GPX)', 'true': 'Has a route (GPX)' },
};
check('chipLabel names each filter for the chips', () => {
  eq(TKL.chipLabel('q', 'dana', NAMES), 'Search: dana');
  eq(TKL.chipLabel('activity', 'ski', NAMES), 'Backcountry Ski');
  eq(TKL.chipLabel('region', 'lake-tahoe', NAMES), 'Region: Lake Tahoe');
  eq(TKL.chipLabel('region', 'nowhere', NAMES), 'Region: nowhere');
  eq(TKL.chipLabel('status', 'shortlisted', NAMES), 'Status: Shortlisted');
  eq(TKL.chipLabel('priority', 'high', NAMES), 'Priority: High priority');
  eq(TKL.chipLabel('month', '6', NAMES), 'Month: June');
  assert.ok(String(TKL.chipLabel('gpx', true, NAMES)).indexOf('Has a route') === 0, 'gpx chip');
});
check('matches: every token has to appear somewhere in the text', () => {
  const m = TKL.matches;
  eq(m('short couloir synthetic bowl eastern sierra', ['coul']), true);
  eq(m('short couloir synthetic bowl', ['couloir', 'bowl']), true);
  eq(m('short couloir synthetic bowl', ['couloir', 'ridge']), false);   // all of them, not any of them
  eq(m('anything', []), true);
  eq(m('', ['x']), false);
});
check('Explore.chipLabel keeps the trips page labels', () => {
  const names = { activity: { ski: 'Backcountry Ski' }, region: { 'lake-tahoe': 'Lake Tahoe' } };
  eq(X.chipLabel('q', 'dana', names), 'Search: dana');
  eq(X.chipLabel('activity', 'ski', names), 'Backcountry Ski');
});

// ---------------------------------------------------------------- goalShown (the scope, then every filter, then the search)

// Each goal card as the page reads it: li.dataset of core.goal_card (data-slug, data-act, data-region, data-status,
// data-priority, data-months, data-gpx, data-archived, data-added, data-text), every value a string. data-months is the
// target months as numbers with spaces between ('1 2 12', '' for none); data-text is the normalised searchable text.
// The last card has no facet attribute at all.
const GOALS = [
  { slug: 'syn-ridge', act: 'hike', region: 'eastern-sierra', status: 'idea', priority: 'high', months: '7 8 9', gpx: '1', archived: '0', added: '2026-01-01', text: 'synthetic ridge traverse eastern sierra scramble' },
  { slug: 'syn-couloir', act: 'ski', region: 'eastern-sierra', status: 'shortlisted', priority: 'high', months: '3 4', gpx: '1', archived: '0', added: '', text: 'synthetic couloir eastern sierra steep' },
  { slug: 'syn-bowl', act: 'ski', region: 'lake-tahoe', status: 'researching', priority: 'normal', months: '1 2 12', gpx: '0', archived: '0', added: '2026-02-01', text: 'synthetic bowl lake tahoe' },
  { slug: 'syn-tower', act: 'climb', region: 'lake-tahoe', status: 'attempted', priority: 'normal', months: '11', gpx: '0', archived: '0', added: '2026-03-01', text: 'synthetic tower lake tahoe trad' },
  { slug: 'syn-loop', act: 'mtb', region: '', status: 'idea', priority: 'someday', months: '', gpx: '1', archived: '0', added: '', text: 'synthetic loop' },
  { slug: 'syn-summit', act: 'hike', region: 'alps', status: 'completed', priority: 'high', months: '7', gpx: '1', archived: '0', added: '2025-01-01', text: 'synthetic summit alps' },
  { slug: 'syn-old', act: 'ski', region: 'alps', status: 'shortlisted', priority: 'someday', months: '4', gpx: '0', archived: '1', added: '2024-01-01', text: 'synthetic old plan alps' },
  { slug: 'syn-done-old', act: 'hike', region: 'lake-tahoe', status: 'completed', priority: 'normal', months: '10', gpx: '1', archived: '1', added: '2023-01-01', text: 'synthetic finished lake tahoe' },
  { slug: 'syn-bare' },
];
const ALL_GOALS = GOALS.map((g) => g.slug);
const ACTIVE_GOALS = ['syn-ridge', 'syn-couloir', 'syn-bowl', 'syn-tower', 'syn-loop', 'syn-bare'];
// the values the page's controls offer for these cards
const GALLOWED = Object.assign({}, ALLOWED, { month: ['', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'] });
const gst = (s) => TKL.parseState(s, GALLOWED);
// the goals a state shows, by slug and in page order; `o` overrides the defaults, `q` is the search box
const goalsShown = (o, q) => GOALS.filter((g) => TKL.goalShown(g, withDefaults(o), X.tokens(q || ''))).map((g) => g.slug);
// every filter is tried with the scope 'all' (the filter alone) and with the page's default scope, 'active'
const everywhere = (o, q) => goalsShown(Object.assign({ scope: 'all' }, o), q);

check('goalShown is exported and answers true or false', () => {
  eq(typeof TKL.goalShown, 'function', 'TKL.goalShown is not a function');
  eq(TKL.goalShown(GOALS[0], DEFAULTS, []), true);
  eq(TKL.goalShown(GOALS[0], withDefaults({ activity: 'ski' }), []), false);
});
check('goalShown: the scope comes first', () => {
  deq(goalsShown({}), ACTIVE_GOALS);                         // the default: active
  deq(goalsShown({ scope: 'active' }), ACTIVE_GOALS);
  deq(goalsShown({ scope: 'shortlisted' }), ['syn-couloir']);
  deq(goalsShown({ scope: 'completed' }), ['syn-summit', 'syn-done-old']);
  deq(goalsShown({ scope: 'archived' }), ['syn-old', 'syn-done-old']);
  deq(goalsShown({ scope: 'all' }), ALL_GOALS);
  // with no filter and no search it is the scope predicate, card for card
  for (const scope of ALLOWED.scope) {
    deq(goalsShown({ scope: scope }), GOALS.filter((g) => !!inScope(g, scope)).map((g) => g.slug), scope);
  }
  // a card outside the scope stays hidden whatever else it matches
  deq(goalsShown({ scope: 'active', status: 'completed' }), []);
  deq(goalsShown({ scope: 'all', status: 'completed' }), ['syn-summit', 'syn-done-old']);
  deq(goalsShown({ scope: 'archived', status: 'completed' }), ['syn-done-old']);
  deq(goalsShown({ scope: 'shortlisted', status: 'shortlisted' }), ['syn-couloir']);    // the archived shortlisted goal is not in it
  deq(goalsShown({ scope: 'archived', status: 'shortlisted' }), ['syn-old']);
  deq(goalsShown({ scope: 'completed' }, 'alps'), ['syn-summit']);
  deq(goalsShown({ scope: 'active' }, 'alps'), []);
});
check('goalShown: the activity filter alone', () => {
  deq(everywhere({ activity: 'ski' }), ['syn-couloir', 'syn-bowl', 'syn-old']);
  deq(everywhere({ activity: 'hike' }), ['syn-ridge', 'syn-summit', 'syn-done-old']);
  deq(everywhere({ activity: 'climb' }), ['syn-tower']);
  deq(everywhere({ activity: 'mtb' }), ['syn-loop']);
  deq(everywhere({ activity: 'other' }), []);
  deq(goalsShown({ activity: 'ski' }), ['syn-couloir', 'syn-bowl']);
  deq(goalsShown({ activity: 'hike' }), ['syn-ridge']);
});
check('goalShown: the region filter alone', () => {
  deq(everywhere({ region: 'eastern-sierra' }), ['syn-ridge', 'syn-couloir']);
  deq(everywhere({ region: 'lake-tahoe' }), ['syn-bowl', 'syn-tower', 'syn-done-old']);
  deq(everywhere({ region: 'alps' }), ['syn-summit', 'syn-old']);
  deq(everywhere({ region: 'boise' }), []);
  deq(goalsShown({ region: 'lake-tahoe' }), ['syn-bowl', 'syn-tower']);
  deq(goalsShown({ region: 'alps' }), []);
});
check('goalShown: the status filter alone', () => {
  deq(everywhere({ status: 'idea' }), ['syn-ridge', 'syn-loop']);
  deq(everywhere({ status: 'researching' }), ['syn-bowl']);
  deq(everywhere({ status: 'shortlisted' }), ['syn-couloir', 'syn-old']);
  deq(everywhere({ status: 'attempted' }), ['syn-tower']);
  deq(everywhere({ status: 'completed' }), ['syn-summit', 'syn-done-old']);
  deq(goalsShown({ status: 'shortlisted' }), ['syn-couloir']);
});
check('goalShown: the priority filter alone', () => {
  deq(everywhere({ priority: 'high' }), ['syn-ridge', 'syn-couloir', 'syn-summit']);
  deq(everywhere({ priority: 'normal' }), ['syn-bowl', 'syn-tower', 'syn-done-old']);
  deq(everywhere({ priority: 'someday' }), ['syn-loop', 'syn-old']);
  deq(goalsShown({ priority: 'high' }), ['syn-ridge', 'syn-couloir']);
  deq(goalsShown({ priority: 'normal' }), ['syn-bowl', 'syn-tower']);
  deq(goalsShown({ priority: 'someday' }), ['syn-loop']);
});
check('goalShown: the month filter matches whole month numbers', () => {
  deq(everywhere({ month: '1' }), ['syn-bowl']);             // January: not the 11 of 'syn-tower', the 10 of 'syn-done-old' or the 12
  deq(everywhere({ month: '2' }), ['syn-bowl']);             // February: not the 12 on its own
  deq(everywhere({ month: '12' }), ['syn-bowl']);
  deq(everywhere({ month: '11' }), ['syn-tower']);
  deq(everywhere({ month: '10' }), ['syn-done-old']);
  deq(everywhere({ month: '4' }), ['syn-couloir', 'syn-old']);
  deq(everywhere({ month: '7' }), ['syn-ridge', 'syn-summit']);
  deq(everywhere({ month: '9' }), ['syn-ridge']);            // the last month of a list
  deq(everywhere({ month: '3' }), ['syn-couloir']);          // and the first
  deq(everywhere({ month: '5' }), []);
  deq(everywhere({ month: '0' }), []);                       // inside '10', and no month
  const months = (list, m) => TKL.goalShown({ months: list }, withDefaults({ scope: 'all', month: m }), []);
  eq(months('11', '1'), false);
  eq(months('11 12', '1'), false);
  eq(months('11 12', '2'), false);
  eq(months('1 11', '1'), true);
  eq(months('1 11', '11'), true);
  eq(months('10 11 12', '1'), false);
  eq(months('10 11 12', '0'), false);
  eq(months('1', '1'), true);
  eq(months('12', '12'), true);
  eq(months('12', '1'), false);
  eq(months('', '1'), false);
  eq(months(undefined, '1'), false);
  eq(months('', ''), true);                                  // no month chosen: every goal, with target months or without
  eq(months(undefined, ''), true);
});
check('goalShown: "Has a route (GPX)" alone', () => {
  deq(everywhere({ gpx: true }), ['syn-ridge', 'syn-couloir', 'syn-loop', 'syn-summit', 'syn-done-old']);
  deq(goalsShown({ gpx: true }), ['syn-ridge', 'syn-couloir', 'syn-loop']);
  deq(everywhere({ gpx: false }), ALL_GOALS);
  for (const v of ['0', '', 'true', undefined]) {
    eq(TKL.goalShown({ gpx: v }, withDefaults({ scope: 'all', gpx: true }), []), false, 'gpx=' + JSON.stringify(v));
    eq(TKL.goalShown({ gpx: v }, withDefaults({ scope: 'all' }), []), true, 'gpx=' + JSON.stringify(v) + ', filter off');
  }
});
check('goalShown: every search token has to be in the card\'s text', () => {
  deq(everywhere({}, 'synthetic'), ALL_GOALS.slice(0, 8));    // every card with a text; the bare one has none
  deq(everywhere({}, 'Lake Tahoe'), ['syn-bowl', 'syn-tower', 'syn-done-old']);
  deq(everywhere({}, 'tahoe trad'), ['syn-tower']);
  deq(everywhere({}, 'ridge alps'), []);                      // each word is in some card, no card has both
  deq(everywhere({}, 'coul'), ['syn-couloir']);               // substring, as on the trips page
  deq(everywhere({}, 'zermatt'), []);
  deq(everywhere({}, ''), ALL_GOALS);
  deq(everywhere({}, '  !! -- '), ALL_GOALS);                 // a query of punctuation has no tokens
  deq(goalsShown({}, 'sierra'), ['syn-ridge', 'syn-couloir']);
  // the tokens are the third argument; the state's q is not read
  deq(GOALS.filter((g) => TKL.goalShown(g, withDefaults({ scope: 'all', q: 'zermatt' }), [])).length, 9);
  deq(GOALS.filter((g) => TKL.goalShown(g, withDefaults({ scope: 'all', q: '' }), ['zermatt'])).length, 0);
  // no token list at all is no search
  eq(TKL.goalShown(GOALS[0], DEFAULTS), true);
  eq(TKL.goalShown(GOALS[0], DEFAULTS, null), true);
  // the slug and the other attributes are not searched
  deq(everywhere({}, 'syn'), ALL_GOALS.slice(0, 8));          // only as the start of 'synthetic' in the text
  deq(everywhere({}, 'shortlisted'), []);
  deq(everywhere({}, 'done'), []);
});
check('goalShown: a filter and a search together', () => {
  deq(everywhere({ activity: 'ski' }, 'alps'), ['syn-old']);
  deq(everywhere({ priority: 'high' }, 'sierra'), ['syn-ridge', 'syn-couloir']);
  deq(everywhere({ priority: 'high', activity: 'ski' }, 'sierra'), ['syn-couloir']);
  deq(everywhere({ region: 'lake-tahoe', gpx: true }), ['syn-done-old']);
  deq(everywhere({ region: 'lake-tahoe', priority: 'high' }), []);          // each alone finds cards, together none
  deq(everywhere({ status: 'idea', gpx: true }), ['syn-ridge', 'syn-loop']);
  deq(everywhere({ status: 'idea', month: '8' }), ['syn-ridge']);
  deq(everywhere({ activity: 'hike', month: '7' }), ['syn-ridge', 'syn-summit']);
  deq(goalsShown({ activity: 'hike', month: '7' }), ['syn-ridge']);
});
check('goalShown: every filter together, and each one still decides', () => {
  const all = { scope: 'all', activity: 'ski', region: 'eastern-sierra', status: 'shortlisted', priority: 'high', month: '3', gpx: true };
  deq(goalsShown(all, 'steep couloir'), ['syn-couloir']);
  deq(goalsShown(all), ['syn-couloir']);
  // the one card that passes all the other filters must stay hidden by the last, whichever it is
  const others = { scope: 'archived', activity: 'hike', region: 'alps', status: 'idea', priority: 'normal', month: '5' };
  for (const key of Object.keys(others)) {
    deq(goalsShown(Object.assign({}, all, { [key]: others[key] }), 'steep'), [], 'with another ' + key);
  }
  deq(goalsShown(all, 'steep ridge'), []);
  const card = GOALS[1], state = withDefaults(all);
  const changed = { act: 'hike', region: 'alps', status: 'idea', priority: 'normal', months: '5 6', gpx: '0', text: 'synthetic couloir' };
  for (const key of Object.keys(changed)) {
    eq(TKL.goalShown(Object.assign({}, card, { [key]: changed[key] }), state, ['steep']), false, 'a card that differs only in data-' + key);
  }
  eq(TKL.goalShown(Object.assign({}, card, { archived: '1' }), withDefaults(Object.assign({}, all, { scope: 'active' })), ['steep']), false);
  eq(TKL.goalShown(card, state, ['steep']), true);
});
check('goalShown: an empty data attribute matches no value of its filter', () => {
  const loop = GOALS[4];
  deq([loop.region, loop.months], ['', '']);
  for (const region of ALLOWED.region.filter(Boolean)) eq(TKL.goalShown(loop, withDefaults({ region: region }), []), false, region);
  for (const month of GALLOWED.month.filter(Boolean)) eq(TKL.goalShown(loop, withDefaults({ month: month }), []), false, month);
  eq(TKL.goalShown(loop, withDefaults({ activity: 'mtb', status: 'idea', priority: 'someday', gpx: true }), ['loop']), true);
});
check('goalShown: a card without data attributes is an active goal that no filter and no search finds', () => {
  const bare = GOALS[8];
  deq(Object.keys(bare), ['slug']);
  eq(TKL.goalShown(bare, DEFAULTS, []), true);
  eq(TKL.goalShown(bare, withDefaults({ scope: 'all' }), []), true);
  for (const scope of ['shortlisted', 'completed', 'archived']) eq(TKL.goalShown(bare, withDefaults({ scope: scope }), []), false, scope);
  for (const o of [{ activity: 'ski' }, { region: 'alps' }, { status: 'idea' }, { priority: 'high' }, { month: '1' }, { gpx: true }]) {
    eq(TKL.goalShown(bare, withDefaults(Object.assign({ scope: 'all' }, o)), []), false, JSON.stringify(o));
  }
  eq(TKL.goalShown(bare, withDefaults({ scope: 'all' }), ['bare']), false);
  eq(TKL.goalShown({}, DEFAULTS, []), true);
});
check('goalShown: the order and the view are not filters', () => {
  deq(goalsShown({ sort: 'name', view: 'list' }), ACTIVE_GOALS);
  deq(goalsShown({ sort: 'added' }), ACTIVE_GOALS);
});
check('goalShown: how many goals a state shows', () => {
  const table = [
    ['', '', 6],
    ['?scope=all', '', 9],
    ['?scope=shortlisted', '', 1],
    ['?scope=completed', '', 2],
    ['?scope=archived', '', 2],
    ['?activity=ski', '', 2],
    ['?activity=ski&scope=all', '', 3],
    ['?priority=high', '', 2],
    ['?priority=high&scope=all', '', 3],
    ['?priority=someday&scope=archived', '', 1],
    ['?region=lake-tahoe&scope=all', '', 3],
    ['?status=idea', '', 2],
    ['?month=1&scope=all', '', 1],
    ['?month=11&scope=all', '', 1],
    ['?month=7&scope=all', '', 2],
    ['?gpx=1', '', 3],
    ['?gpx=1&scope=all', '', 5],
    ['?scope=all', 'lake tahoe', 3],
    ['', 'lake tahoe', 2],
    ['?activity=ski&region=eastern-sierra&status=shortlisted&priority=high&month=3&gpx=1', 'steep', 1],
    ['?activity=ski&region=eastern-sierra&status=shortlisted&priority=high&month=5&gpx=1', 'steep', 0],
    ['?priority=urgent&month=13', '', 6],     // values no control offers are reset by parseState, so nothing is filtered
  ];
  for (const [search, q, want] of table) {
    eq(GOALS.filter((g) => TKL.goalShown(g, gst(search), X.tokens(q))).length, want, (search || '(no query)') + ' ' + q);
  }
});
check('goalShown leaves the card, the state and the tokens as it found them', () => {
  const state = withDefaults({ scope: 'all', activity: 'ski', month: '4', gpx: true }), toks = ['synthetic', 'alps'];
  const before = [JSON.stringify(GOALS), JSON.stringify(state)];
  GOALS.forEach((g) => TKL.goalShown(g, state, toks));
  deq([JSON.stringify(GOALS), JSON.stringify(state)], before);
  deq(toks, ['synthetic', 'alps']);
});

// ---------------------------------------------------------------- the form as the script finds it (adoptForm)

// The form is revealed at first paint and the script is deferred, so the visitor may have used it first. An untouched
// form: an empty box and every select on its first option. The scope, the activity, the route switch and the view are
// buttons, which hold nothing until the script is there.
const UNTOUCHED = { q: '', region: '', status: '', priority: '', month: '', sort: 'priority' };
const formWith = (o) => Object.assign({}, UNTOUCHED, o);
const adopt = (search, form, traversal) => TKL.adoptForm(gst(search), form, traversal);

check('adoptForm is exported', () => eq(typeof TKL.adoptForm, 'function', 'TKL.adoptForm is not a function'));
check('adoptForm: an untouched form adopts nothing', () => {
  deq(adopt('', UNTOUCHED), DEFAULTS);
  deq(adopt('', {}), DEFAULTS);
  deq(adopt('', undefined), DEFAULTS);
  deq(adopt('', null), DEFAULTS);
  for (const search of ['?q=ridge', '?scope=all&view=list', '?activity=ski&region=alps&status=idea&priority=high&month=4&gpx=1&scope=all&sort=name&view=list']) {
    deq(adopt(search, UNTOUCHED), gst(search), search);
    deq(adopt(search, UNTOUCHED, true), gst(search), search + ' after Back');
  }
});
check('adoptForm: with no state in the URL, each select that is off its default and the typed text are taken over', () => {
  deq(adopt('', formWith({ region: 'lake-tahoe' })), withDefaults({ region: 'lake-tahoe' }));
  deq(adopt('', formWith({ status: 'shortlisted' })), withDefaults({ status: 'shortlisted' }));
  deq(adopt('', formWith({ priority: 'high' })), withDefaults({ priority: 'high' }));
  deq(adopt('', formWith({ month: '7' })), withDefaults({ month: '7' }));
  deq(adopt('', formWith({ sort: 'name' })), withDefaults({ sort: 'name' }));
  deq(adopt('', formWith({ q: 'ridge' })), withDefaults({ q: 'ridge' }));            // no best-match order here: the sort stays
  deq(adopt('', formWith({ q: 'ridge', region: 'lake-tahoe', status: 'idea', priority: 'someday', month: '4', sort: 'added' })),
      withDefaults({ q: 'ridge', region: 'lake-tahoe', status: 'idea', priority: 'someday', month: '4', sort: 'added' }));
});
check('adoptForm: what is taken over filters and is written to the URL as a choice made later would be', () => {
  const state = adopt('', formWith({ region: 'lake-tahoe', sort: 'name' }));
  deq(GOALS.filter((g) => TKL.goalShown(g, state, [])).map((g) => g.slug), GOALS.filter((g) => TKL.goalShown(g, withDefaults({ region: 'lake-tahoe' }), [])).map((g) => g.slug));
  assert.ok(GOALS.filter((g) => TKL.goalShown(g, state, [])).length < ACTIVE_GOALS.length);
  eq(TKL.serialize(state), 'region=lake-tahoe&sort=name');
  eq(TKL.serialize(adopt('', UNTOUCHED)), '');
});
check('adoptForm: a URL with state wins over the form, key by key', () => {
  deq(adopt('?region=alps', formWith({ region: 'lake-tahoe' })), withDefaults({ region: 'alps' }));
  deq(adopt('?status=idea', formWith({ status: 'completed' })), withDefaults({ status: 'idea' }));
  deq(adopt('?priority=high', formWith({ priority: 'someday' })), withDefaults({ priority: 'high' }));
  deq(adopt('?month=4', formWith({ month: '7' })), withDefaults({ month: '4' }));
  deq(adopt('?sort=name', formWith({ sort: 'added' })), withDefaults({ sort: 'name' }));
  deq(adopt('?q=ridge', formWith({ q: 'tower' })), withDefaults({ q: 'ridge' }));
  const full = '?q=ridge&activity=hike&region=alps&status=idea&priority=high&month=4&gpx=1&scope=all&sort=name&view=list';
  deq(adopt(full, formWith({ q: 'tower', region: 'lake-tahoe', status: 'completed', priority: 'someday', month: '7', sort: 'added' })), gst(full));
});
check('adoptForm: a key the URL leaves alone is still taken from the form', () => {
  deq(adopt('?region=alps', formWith({ region: 'lake-tahoe', status: 'idea', q: 'ridge' })), withDefaults({ region: 'alps', status: 'idea', q: 'ridge' }));
  deq(adopt('?scope=all&gpx=1', formWith({ month: '6' })), withDefaults({ scope: 'all', gpx: true, month: '6' }));
});
check('adoptForm: after Back or Forward only the typed text is taken', () => {
  const form = formWith({ q: 'ridge', region: 'lake-tahoe', status: 'idea', priority: 'high', month: '4', sort: 'name' });
  deq(adopt('', form, true), withDefaults({ q: 'ridge' }));
  deq(adopt('', formWith({ region: 'lake-tahoe', sort: 'name' }), true), DEFAULTS);
  deq(adopt('?status=idea', form, true), withDefaults({ status: 'idea', q: 'ridge' }));
  deq(adopt('', form, false), withDefaults({ q: 'ridge', region: 'lake-tahoe', status: 'idea', priority: 'high', month: '4', sort: 'name' }));
  deq(adopt('', form), adopt('', form, false));
});
check('adoptForm: the buttons (activity, route, scope, view) are never read from the form', () => {
  deq(adopt('', formWith({ activity: 'ski', gpx: true, scope: 'all', view: 'list' })), DEFAULTS);
});
check('adoptForm returns a new state of the ten keys and changes neither argument', () => {
  const state = gst('?activity=ski'), form = formWith({ q: 'ridge', region: 'lake-tahoe', extra: 'x' });
  const before = [JSON.stringify(state), JSON.stringify(form)];
  const out = TKL.adoptForm(state, form);
  assert.notStrictEqual(out, state);
  deq([JSON.stringify(state), JSON.stringify(form)], before);
  deq(Object.keys(out).sort(), KEYS.slice().sort());
  assert.notStrictEqual(TKL.adoptForm(state, UNTOUCHED), state);
});

// ---------------------------------------------------------------- what a change of view does to the history (Explore.historyStep)

// historyStep(kind, entry, now, next, recent) -> { push, restore }: the rule trips.js and ticklist.js share, held here
// against explore.js itself. kind: 'type' (the pause after typing, and the write on load), 'pick' (a filter, the
// scope, the sort, the view, a chip removed, Clear all) or 'submit' (Enter in the search box). entry: the address this
// history entry stood for when the visitor settled on it; now: its address at this moment (typing rewrites it); next:
// the address of the new view; recent: an entry was made a moment ago.
const HOME = '/tick-list/', TYPED = '/tick-list/?q=ridge', MORE = '/tick-list/?q=ridge+walk';
const hstep = (kind, entry, now, next, recent) => {
  const s = X.historyStep(kind, entry, now, next, recent);
  deq(Object.keys(s).sort(), ['push', 'restore'], 'historyStep returns { push, restore }');
  eq(typeof s.push, 'boolean');
  eq(typeof s.restore, 'boolean');
  return [s.push, s.restore];
};
// every way the three addresses can relate: [entry, now, next]
const SHAPES = {
  'nothing has changed': [HOME, HOME, HOME],
  'a new view, the entry still as it stood': [HOME, HOME, TYPED],
  'typing rewrote the entry and the view is the old one again': [HOME, TYPED, HOME],
  'typing already wrote the new view into the entry': [HOME, TYPED, TYPED],
  'typing rewrote the entry and the new view is yet another': [HOME, TYPED, MORE],
};
const KINDS = ['type', 'pick', 'submit'];

check('historyStep is a function of five arguments', () => {
  eq(typeof X.historyStep, 'function', 'Explore.historyStep is not a function');
  eq(X.historyStep.length, 5, 'historyStep(kind, entry, now, next, recent)');
});
check('historyStep: every combination of kind, addresses and a recent entry', () => {
  // [push, restore] with no entry just made; with one, every answer is [false, false]
  const table = {
    type: [[false, false], [false, false], [false, false], [false, false], [false, false]],
    pick: [[true, false], [true, false], [true, false], [true, false], [true, false]],
    submit: [[false, false], [true, false], [false, false], [true, true], [true, true]],
  };
  const names = Object.keys(SHAPES);
  eq(names.length, 5);
  for (const kind of KINDS) names.forEach((name, i) => {
    deq(hstep(kind, ...SHAPES[name], false), table[kind][i], kind + ': ' + name);
    deq(hstep(kind, ...SHAPES[name], true), [false, false], kind + ': ' + name + ', an entry just made');
  });
});
check('historyStep: the table, said as the rule', () => {
  for (const name of Object.keys(SHAPES)) for (const recent of [false, true]) {
    const [entry, now, next] = SHAPES[name], what = name + (recent ? ', an entry just made' : '');
    // typing never adds an entry; a pick adds one unless one was just made, and puts nothing back
    deq(hstep('type', entry, now, next, recent), [false, false], what);
    deq(hstep('pick', entry, now, next, recent), [!recent, false], what);
    // a submitted search adds one whenever the view differs from the one the entry stood for, and the entry is put
    // back first exactly when typing had rewritten it
    deq(hstep('submit', entry, now, next, recent), [!recent && next !== entry, !recent && next !== entry && now !== entry], what);
  }
  // the entry is never put back without a new one being made
  for (const kind of KINDS) for (const name of Object.keys(SHAPES)) for (const recent of [false, true]) {
    const [push, restore] = hstep(kind, ...SHAPES[name], recent);
    assert.ok(push || !restore, [kind, name, recent].join(' / '));
  }
});
check('historyStep: a second search typed over the first, and Enter again', () => {
  deq(hstep('submit', TYPED, MORE, MORE, false), [true, true]);           // typed over the first search, the pause, Enter
  deq(hstep('submit', TYPED, TYPED, MORE, false), [true, false]);         // Enter before the pause: nothing to put back
  deq(hstep('submit', TYPED, TYPED, TYPED, false), [false, false]);       // the search just submitted, Enter once more
});
check('historyStep: addresses are compared whole, and as they are given', () => {
  deq(hstep('submit', '/tick-list/?q=ridg', '/tick-list/?q=ridg', '/tick-list/?q=ridge', false), [true, false]);
  deq(hstep('submit', '/tick-list/?q=ridge', '/tick-list/?q=ridge', '/tick-list/?q=ridge&view=list', false), [true, false]);
  deq(hstep('submit', '/tick-list/', '/tick-list/?q=a', '/tick-list/?q=a', false), [true, true]);
  // two spellings of one view are two addresses to it: the caller keeps to one spelling (the page's own)
  deq(hstep('submit', "/tick-list/?q=lover's", "/tick-list/?q=lover's", '/tick-list/?q=lover%27s', false), [true, false]);
});
check('historyStep returns a new answer each time and keeps nothing between calls', () => {
  const a = X.historyStep('submit', HOME, TYPED, TYPED, false), b = X.historyStep('submit', HOME, TYPED, TYPED, false);
  deq(a, b);
  assert.notStrictEqual(a, b);
  a.push = false;
  a.restore = false;
  deq(X.historyStep('submit', HOME, TYPED, TYPED, false), { push: true, restore: true });
  // the order of the questions does not matter: a pick asked in between changes no later answer
  X.historyStep('pick', HOME, HOME, TYPED, false);
  deq(X.historyStep('type', HOME, HOME, TYPED, false), { push: false, restore: false });
  deq(X.historyStep('submit', HOME, HOME, HOME, false), { push: false, restore: false });
});

// ---------------------------------------------------------------- the page part, on a stand-in for the browser

/* What the pure helpers cannot show: that the page's own lines hand them the right things at the right moments.
   tests/test_ticklist_js.py passes a model of a Tick list page that sitegen.pages.ticklist generated from a synthetic
   site (page_model): the page's address, its <body> as a tree of elements and text, and what the checks press and
   expect, all read from that page. load() opens it in the stand-in for the browser of tests/page_standin.js (its
   header says what it models), which runs explore.js and then the whole of ticklist.js against it (the order the
   bundle has them). To what every visitor does there (the pause, Back, Forward) load() adds the Tick list's own:
   typing, Enter, an activity, the scope, a menu, the route switch, the view, a chip's remove button, Clear all, and
   the page's one link to a fragment of itself (the skip link); and what is read back of the page: the box, the
   controls, the chips, the goals listed.

   The rule the checks hold the page to is the Trips page's (docs/personal-website-improvement-plan.md, 8.4): typing
   rewrites the address of the entry the visitor is on, a deliberate change (Enter, a filter, the scope, the sort, the
   view, a chip removed, Clear all) makes one entry, and Back returns to the view from before it. The Tick list has no
   sort that follows the search, so nothing of the Trips page's handling of Best match is played here.

   Without the model these checks are skipped. With 'gap:<name>' as a fourth argument the check of that name is run
   after them: a case in which the page does not yet do what the rule says (GAPS, at the end of this file; it is
   empty at present). */
const MODEL = process.argv[4] ? JSON.parse(fs.readFileSync(path.resolve(process.argv[4]), 'utf8')) : null;
const ONLY = process.argv[5] || '';
const SOURCES = MODEL ? [[EXPLORE, fs.readFileSync(EXPLORE, 'utf8')], [TICKLIST, fs.readFileSync(TICKLIST, 'utf8')]] : [];

function load(opts) {
  const tab = standin.open(MODEL, SOURCES, opts);
  const body = tab.body, byId = tab.byId, one = tab.one, press = tab.press, fire = tab.fire;
  const form = byId('search'), q = byId('tkl-q');
  const menu = (name) => one(form, 'select[name="' + name + '"]', 'the ' + name + ' menu');
  const checked = (sel, what) => one(form, sel + ' [aria-checked="true"]', 'the checked ' + what).dataset;
  const page = Object.assign(tab.visitor, {
    // ---- what the visitor does on the Tick list
    type: (text) => { q.value = text; fire(q, 'input'); },                        // the keys; the typing pause has not passed yet
    enter: () => { eq(fire(form, 'submit').defaultPrevented, true, 'Enter sent the form to the server'); },
    activity: (value) => { press(one(form, '.trx-acts:not(.tkl-scope) [data-filter="' + value + '"]', 'the activity ' + value)); },
    scope: (value) => { press(one(form, '.tkl-scope [data-scope="' + value + '"]', 'the scope ' + value)); },
    view: (value) => { press(one(form, '.trx-view [data-view="' + value + '"]', 'the view ' + value)); },
    choose: (name, value) => {
      const sel = menu(name);
      assert.ok(sel.options.some((o) => o.value === value), 'the ' + name + ' menu has no option ' + value);
      sel.value = value;
      fire(sel, 'change');
    },
    route: () => { press(one(form, '[data-toggle="gpx"]', 'the "Has a route" switch')); },
    clearAll: () => { const b = byId('tkl-clear'); eq(b.hidden, false, 'Clear all is not on screen'); press(b); },
    clearFilters: () => {                                 // the button of the 'No goals match' message
      eq(byId('tkl-none').hidden, false, 'the empty state is not on screen');
      const b = one(byId('tkl-none'), '[data-clear]', 'the Clear filters button');
      eq(b.hidden, false, 'the Clear filters button is not on screen');
      press(b);
    },
    removeChip: (label) => {
      const hits = byId('tkl-chips').querySelectorAll('button').filter((b) => b.textContent === label);
      eq(hits.length, 1, 'the chips are ' + JSON.stringify(page.chips()));
      press(hits[0]);
    },
    // the page's link to one of its own fragments ('#main', the skip link): its target must be on the page
    jump: (fragment) => {
      assert.ok(byId(fragment.slice(1)), 'the page has no element for ' + fragment);
      tab.follow(one(body, 'a[href="' + fragment + '"]', 'the link to ' + fragment));
    },
    // ---- what the visitor sees of the page
    box: () => q.value,
    // every control but the box, as it reads: the two radio groups and the view by their checked button, the menus by
    // their value, the switch by its state
    controls: () => ({
      activity: checked('.trx-acts:not(.tkl-scope)', 'activity').filter, region: menu('region').value, status: menu('status').value,
      priority: menu('priority').value, month: menu('month').value,
      gpx: one(form, '[data-toggle="gpx"]', 'the "Has a route" switch').getAttribute('aria-checked') === 'true',
      scope: checked('.tkl-scope', 'scope').scope, sort: menu('sort').value, view: checked('.trx-view', 'view').view,
    }),
    chips: () => byId('tkl-chips').querySelectorAll('button').map((b) => b.textContent),
    shown: () => byId('tkl-results').querySelectorAll('.gcard').filter((c) => !c.hidden).map((c) => c.dataset.slug).sort(),
    count: () => byId('tkl-count').textContent,
  });
  return page;
}

if (MODEL) {
  // ---- the fixture, read from the model: the attributes of every goal card in page order, and the list a view shows,
  // worked out here from those attributes (not by TKL.goalShown, which the checks above hold on records of their own)
  const CARDS = [];
  (function walk(node) {
    if (typeof node === 'string') return;
    if ((' ' + (node.attrs.class || '') + ' ').indexOf(' gcard ') !== -1) CARDS.push(node.attrs);
    node.children.forEach(walk);
  })(MODEL.body);
  const PLAIN = { activity: 'all', region: '', status: '', priority: '', month: '', gpx: false, scope: 'active', sort: 'priority', view: 'cards' };
  const set = (o) => Object.assign({}, PLAIN, o);          // the controls of a view: what differs from the plain one
  const scoped = (c, scope) => {
    const archived = c['data-archived'] === '1', done = c['data-status'] === 'completed';
    if (scope === 'all') return true;
    if (scope === 'archived') return archived;
    if (scope === 'completed') return done;
    if (scope === 'shortlisted') return c['data-status'] === 'shortlisted' && !archived;
    return !archived && !done;
  };
  // the goals a view lists, by slug and sorted as shown() reads them: o as for set(), words the search
  const listed = (o, words) => {
    const v = set(o), toks = String(words || '').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
    return CARDS.filter((c) => scoped(c, v.scope)
      && (v.activity === 'all' || c['data-act'] === v.activity)
      && (!v.region || c['data-region'] === v.region) && (!v.status || c['data-status'] === v.status)
      && (!v.priority || c['data-priority'] === v.priority) && (!v.month || c['data-months'].split(' ').indexOf(v.month) !== -1)
      && (!v.gpx || c['data-gpx'] === '1') && toks.every((t) => c['data-text'].indexOf(t) !== -1)).map((c) => c['data-slug']).sort();
  };
  const ACTIVE = listed({}), RIDGE = listed({}, 'ridge'), LOOP_FOUND = listed({}, 'loop');
  const Q = '?q=ridge', LOOP = '?q=loop';             // the addresses of the two searches the checks type
  const LINK = MODEL.fragments[0];                     // the fragment of the page's link to itself
  const [FIRST, SECOND, THIRD] = MODEL.activities.filter((a) => a !== 'all');
  const REGION = MODEL.menus.region.filter(Boolean).slice(-1)[0], STATUS = MODEL.menus.status.filter(Boolean)[0];
  const PRIORITY = MODEL.menus.priority.filter(Boolean)[0], MONTH = MODEL.menus.month.filter(Boolean)[0];
  // What a step can change that the visitor sees: every entry of the page, the one the visitor is on, its address, the
  // box and the controls. Read after every step of every check below (tests/test_ticklist_js.py holds the checks to it)
  const seen = (page) => [page.stack(), page.at(), page.address(), page.box(), page.controls()];
  // the visitor has typed a search, waited and pressed Enter, and the moment after it is over: the page's first entry
  // and the search's
  const searched = (opts) => {
    const page = load(opts);
    deq(seen(page), [[''], 0, '', '', PLAIN]);
    page.type('ridge');
    deq(seen(page), [[''], 0, '', 'ridge', PLAIN]);
    page.pause();
    deq(seen(page), [[Q], 0, Q, 'ridge', PLAIN]);
    page.enter();
    deq(seen(page), [['', Q], 1, Q, 'ridge', PLAIN]);
    page.pause();
    deq(seen(page), [['', Q], 1, Q, 'ridge', PLAIN]);
    return page;
  };
  // every kind of control, as [its name, the press, what it changes of the plain view (set), the address of that view
  // beside a search for 'ridge', the box afterwards]: an activity, the scope, each menu, the route switch, the view,
  // the search chip's remove button, Clear all
  const CONTROLS = [
    ['an activity', (page) => page.activity(FIRST), { activity: FIRST }, Q + '&activity=' + FIRST, 'ridge'],
    ['the scope', (page) => page.scope('all'), { scope: 'all' }, Q + '&scope=all', 'ridge'],
    ['the region menu', (page) => page.choose('region', REGION), { region: REGION }, Q + '&region=' + REGION, 'ridge'],
    ['the status menu', (page) => page.choose('status', STATUS), { status: STATUS }, Q + '&status=' + STATUS, 'ridge'],
    ['the priority menu', (page) => page.choose('priority', PRIORITY), { priority: PRIORITY }, Q + '&priority=' + PRIORITY, 'ridge'],
    ['the month menu', (page) => page.choose('month', MONTH), { month: MONTH }, Q + '&month=' + MONTH, 'ridge'],
    ['the sort menu', (page) => page.choose('sort', 'name'), { sort: 'name' }, Q + '&sort=name', 'ridge'],
    ['the route switch', (page) => page.route(), { gpx: true }, Q + '&gpx=1', 'ridge'],
    ['the view', (page) => page.view('list'), { view: 'list' }, Q + '&view=list', 'ridge'],
    ['the remove button of the search chip', (page) => page.removeChip('Search: ridge'), {}, '', ''],
    ['Clear all', (page) => page.clearAll(), {}, '', ''],
  ];
  // Arrow keys through a radio group: a press per key (selection follows focus), three of them within the moment, then
  // a submitted search. key: 'activity' or 'scope'; values: the three passed through, in the order of the page
  const arrows = (key, values) => {
    const [first, second, third] = values;
    assert.ok(third, 'the fixture needs three more values of ' + key);
    const at = (value) => '?' + key + '=' + value, on = (value) => ({ [key]: value });
    const last = at(third), found = Q + '&' + key + '=' + third;
    const page = load();
    deq(seen(page), [[''], 0, '', '', PLAIN]);
    page.pause();
    deq(seen(page), [[''], 0, '', '', PLAIN]);
    page[key](first);
    deq(seen(page), [['', at(first)], 1, at(first), '', set(on(first))]);
    page.pause(100);
    deq(seen(page), [['', at(first)], 1, at(first), '', set(on(first))]);
    page[key](second);                                    // within the moment: the entry just made is rewritten
    deq(seen(page), [['', at(second)], 1, at(second), '', set(on(second))]);
    page.pause(100);
    deq(seen(page), [['', at(second)], 1, at(second), '', set(on(second))]);
    page[key](third);
    deq(seen(page), [['', last], 1, last, '', set(on(third))]);
    eq(page.pushes(), 1, key);
    page.pause();
    deq(seen(page), [['', last], 1, last, '', set(on(third))]);
    page.type('ridge');
    deq(seen(page), [['', last], 1, last, 'ridge', set(on(third))]);
    page.pause();
    deq(seen(page), [['', found], 1, found, 'ridge', set(on(third))]);      // typing rewrites the entry of the last of them
    page.enter();
    deq(seen(page), [['', last, found], 2, found, 'ridge', set(on(third))]);
    deq(page.calls().slice(-2), ['replace ' + last, 'push ' + found], 'the entry was put back to a ' + key + ' the visitor only passed through');
    deq(page.shown(), listed(on(third), 'ridge'));
    page.back();
    deq(seen(page), [['', last, found], 1, last, '', set(on(third))], 'Back did not show the last ' + key);
    deq([page.shown(), page.left()], [listed(on(third)), false]);
    page.back();
    deq(seen(page), [['', last, found], 0, '', '', PLAIN], 'the next Back did not show the list the page opened on');
    deq([page.shown(), page.left()], [ACTIVE, false]);
  };
  // Type a search (no Enter), jump to a fragment of the page, Enter, then Back. opts: the browser (page_standin.js)
  const typedThenJump = (opts) => {
    const name = JSON.stringify(opts), there = Q + LINK;
    const page = load(opts);
    deq(seen(page), [[''], 0, '', '', PLAIN], name);
    page.type('ridge');
    deq(seen(page), [[''], 0, '', 'ridge', PLAIN], name);
    page.pause();
    deq(seen(page), [[Q], 0, Q, 'ridge', PLAIN], name);              // typing rewrote the page's one entry
    page.jump(LINK);
    deq(seen(page), [[Q, there], 1, there, 'ridge', PLAIN], name);   // the browser's own entry, for the view on screen
    deq([page.shown(), page.pushes()], [RIDGE, 0], name);
    page.pause();
    deq(seen(page), [[Q, there], 1, there, 'ridge', PLAIN], name);
    page.enter();
    // the search is the view this entry stands for: Enter adds no entry and turns none into another view (the fragment
    // goes, as on every write after the load)
    deq(seen(page), [[Q, Q], 1, Q, 'ridge', PLAIN], 'the entry the jump made was rewritten into another view, or another added: ' + name);
    deq([page.pushes(), page.calls().slice(-1), page.shown()], [0, ['replace ' + Q], RIDGE], name);
    page.back();
    deq(seen(page), [[Q, Q], 0, Q, 'ridge', PLAIN], name);
    deq([page.shown(), page.left()], [RIDGE, false], name);
    page.back();                                            // the list before the typing was never an entry of its own
    deq([seen(page), page.left()], [[[Q, Q], 0, Q, 'ridge', PLAIN], true], name);
    // the same with an apostrophe in the words: the entry is settled on the page's spelling of them, not the browser's
    const quoted = '?q=lover%27s';
    const other = load(opts);
    deq(seen(other), [[''], 0, '', '', PLAIN], name);
    other.type("lover's");
    deq(seen(other), [[''], 0, '', "lover's", PLAIN], name);
    other.pause();
    deq(seen(other), [[quoted], 0, quoted, "lover's", PLAIN], name);
    other.jump(LINK);
    deq(seen(other), [[quoted, quoted + LINK], 1, quoted + LINK, "lover's", PLAIN], name);
    other.pause();
    deq(seen(other), [[quoted, quoted + LINK], 1, quoted + LINK, "lover's", PLAIN], name);
    other.enter();
    deq(seen(other), [[quoted, quoted], 1, quoted, "lover's", PLAIN], name);
    eq(other.pushes(), 0, name);
    // a submitted search, then the jump: Back returns to the search, the next Back to the list; and a new search from
    // the entry the jump made goes on top of the search it stands for
    const sub = searched(opts);
    sub.jump(LINK);
    deq(seen(sub), [['', Q, there], 2, there, 'ridge', PLAIN], name);
    eq(sub.pushes(), 1, name);
    sub.pause();
    deq(seen(sub), [['', Q, there], 2, there, 'ridge', PLAIN], name);
    sub.back();
    deq(seen(sub), [['', Q, there], 1, Q, 'ridge', PLAIN], name);
    deq(sub.shown(), RIDGE, name);
    sub.back();
    deq(seen(sub), [['', Q, there], 0, '', '', PLAIN], name);
    deq([sub.shown(), sub.left()], [ACTIVE, false], name);
    sub.forward();
    deq(seen(sub), [['', Q, there], 1, Q, 'ridge', PLAIN], name);
    sub.forward();
    deq(seen(sub), [['', Q, there], 2, there, 'ridge', PLAIN], name);
    sub.type('loop');
    deq(seen(sub), [['', Q, there], 2, there, 'loop', PLAIN], name);
    sub.pause();
    deq(seen(sub), [['', Q, LOOP], 2, LOOP, 'loop', PLAIN], name);
    sub.enter();
    deq(seen(sub), [['', Q, Q, LOOP], 3, LOOP, 'loop', PLAIN], 'the entry the jump made did not go back to the search it stood for: ' + name);
    sub.back();
    deq(seen(sub), [['', Q, Q, LOOP], 2, Q, 'ridge', PLAIN], name);
    deq(sub.shown(), RIDGE, name);
  };
  const pageChecks = {
    'the model is the page the script expects': () => {
      const page = load();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      deq([page.shown(), page.chips(), page.count()], [ACTIVE, [], ACTIVE.length + ' OF ' + CARDS.length + ' GOALS']);
      // the fixture: goals the default scope leaves out, a search that finds some goals and not all, and it finds one
      // more among the archived; the list worked out here agrees with what the generator's data-text says
      deq(CARDS.map((c) => c['data-slug']), MODEL.slugs);
      assert.ok(ACTIVE.length > 2 && ACTIVE.length < CARDS.length, 'the fixture needs goals the default scope leaves out');
      assert.ok(RIDGE.length > 0 && RIDGE.length < ACTIVE.length, 'the fixture search must find some goals and not all');
      deq(listed({ scope: 'all' }, 'ridge'), MODEL.found.ridge.slice().sort());
      assert.ok(listed({ scope: 'all' }, 'ridge').length > RIDGE.length, 'the fixture search must find a goal outside the default scope');
      deq([LOOP_FOUND.length, listed({}, 'zzzz')], [1, []]);
      // what the checks press: three activities besides All, the five scopes, two views, a value in every menu, and a
      // link of the page to one of its own fragments
      eq(MODEL.activities[0], 'all');
      assert.ok(MODEL.activities.length >= 4, 'the fixture needs three activities besides All');
      deq(MODEL.scopes, ['active', 'shortlisted', 'completed', 'archived', 'all']);
      deq(MODEL.views, ['cards', 'list']);
      for (const value of [REGION, STATUS, PRIORITY, MONTH]) assert.ok(value, 'a menu of the fixture offers nothing');
      deq(MODEL.menus.sort, ['priority', 'added', 'name']);
      eq(MODEL.fragments.length, 1, 'the checks follow the page\'s one link to itself: ' + JSON.stringify(MODEL.fragments));
      // every filter the checks pick narrows the list and leaves something; the scope 'all' widens it; the sort and
      // the view change no goal
      for (const [name, _press, o] of CONTROLS) {
        const n = listed(o).length;
        if (o.scope) assert.ok(n > ACTIVE.length, name);
        else if (o.sort || o.view || !Object.keys(o).length) eq(n, ACTIVE.length, name);
        else assert.ok(n > 0 && n < ACTIVE.length, 'the fixture needs some goals, not all, for ' + name);
      }
      page.jump(LINK);
      deq(seen(page), [['', LINK], 1, LINK, '', PLAIN]);
      eq(page.pushes(), 0);
      page.jump(LINK);                                      // the address already ends with it: no second entry
      deq(seen(page), [['', LINK], 1, LINK, '', PLAIN]);
      page.back();
      deq([seen(page), page.left()], [[['', LINK], 0, '', '', PLAIN], false]);
    },
    // ---- (a)
    'the load rewrites its own entry and adds none, and keeps a fragment': () => {
      const page = load();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      deq([page.calls(), page.left()], [['replace '], false]);
      // an address with a view in it, spelled its own way, becomes the canonical one, in the same entry
      const shared = load({ search: '?view=list&utm=x&q=ridge&activity=' + FIRST });
      const canonical = Q + '&activity=' + FIRST + '&view=list';
      deq(seen(shared), [[canonical], 0, canonical, 'ridge', set({ activity: FIRST, view: 'list' })]);
      deq([shared.calls(), shared.shown()], [['replace ' + canonical], listed({ activity: FIRST }, 'ridge')]);
      // and that canonical address is what the entry stands for from then on: Enter on it is no change of view
      shared.pause();
      deq(seen(shared), [[canonical], 0, canonical, 'ridge', set({ activity: FIRST, view: 'list' })]);
      shared.enter();
      deq(seen(shared), [[canonical], 0, canonical, 'ridge', set({ activity: FIRST, view: 'list' })], 'the entry still stood for the address as it was typed');
      eq(shared.pushes(), 0);
      // the fragment is kept on that first write (a link to a place on the page, the header's Search link of trips/)
      const linked = load({ hash: LINK });
      deq(seen(linked), [[LINK], 0, LINK, '', PLAIN]);
      deq(linked.calls(), ['replace ' + LINK]);
      const both = load({ search: '?scope=all&q=ridge', hash: '#search' });
      deq(seen(both), [[Q + '&scope=all#search'], 0, Q + '&scope=all#search', 'ridge', set({ scope: 'all' })]);
      deq([both.calls(), both.shown()], [['replace ' + Q + '&scope=all#search'], listed({ scope: 'all' }, 'ridge')]);
      // and it goes with the first thing the visitor does, in the same entry
      linked.enter();
      deq(seen(linked), [[''], 0, '', '', PLAIN]);
      deq(linked.calls(), ['replace ' + LINK, 'replace ']);
      // a page loaded again on the way Back (from a goal's page, say): the view is the address's, in its one entry,
      // and that is what the entry stands for
      const back = load({ search: canonical, navType: 'back_forward' });
      deq(seen(back), [[canonical], 0, canonical, 'ridge', set({ activity: FIRST, view: 'list' })]);
      deq([back.calls(), back.shown()], [['replace ' + canonical], listed({ activity: FIRST }, 'ridge')]);
      back.enter();
      deq(seen(back), [[canonical], 0, canonical, 'ridge', set({ activity: FIRST, view: 'list' })]);
      eq(back.pushes(), 0);
    },
    // ---- (b)
    'type, pause, Enter, Back: one new entry, and Back shows the list from before the search': () => {
      const page = load();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      page.type('rid');
      deq(seen(page), [[''], 0, '', 'rid', PLAIN], 'the address changed before the typing pause was over');
      page.pause(100);
      deq(seen(page), [[''], 0, '', 'rid', PLAIN]);
      page.type('ridge');                                   // typed on within the pause: one write, for the whole word
      deq(seen(page), [[''], 0, '', 'ridge', PLAIN]);
      page.pause(149);
      deq(seen(page), [[''], 0, '', 'ridge', PLAIN]);
      deq(page.shown(), ACTIVE);
      page.pause(1);
      deq(seen(page), [[Q], 0, Q, 'ridge', PLAIN]);        // the pause wrote the words into the entry
      deq([page.shown(), page.chips(), page.calls()], [RIDGE, ['Search: ridge'], ['replace ', 'replace ' + Q]]);
      page.pause();
      deq(seen(page), [[Q], 0, Q, 'ridge', PLAIN]);
      page.enter();
      deq(seen(page), [['', Q], 1, Q, 'ridge', PLAIN]);    // the entry is put back; the search is a new one
      deq(page.calls().slice(-2), ['replace ', 'push ' + Q], 'the entry is restored before the new one is made');
      deq([page.shown(), page.pushes()], [RIDGE, 1]);
      page.back();
      deq(seen(page), [['', Q], 0, '', '', PLAIN], 'Back did not return to the list before the search');
      deq([page.shown(), page.chips(), page.left()], [ACTIVE, [], false]);
      page.forward();
      deq(seen(page), [['', Q], 1, Q, 'ridge', PLAIN]);
      deq([page.shown(), page.chips()], [RIDGE, ['Search: ridge']]);
      page.enter();                                         // Enter again, at once
      deq(seen(page), [['', Q], 1, Q, 'ridge', PLAIN]);
      page.pause();
      deq(seen(page), [['', Q], 1, Q, 'ridge', PLAIN]);
      const calls = page.calls().length;
      page.enter();                                         // and long after, when no entry was 'made a moment ago'
      deq(seen(page), [['', Q], 1, Q, 'ridge', PLAIN], 'Enter on the same view added an entry');
      deq([page.pushes(), page.calls().slice(calls)], [1, ['replace ' + Q]]);
      page.back();
      deq(seen(page), [['', Q], 0, '', '', PLAIN]);
      page.back();
      deq([seen(page), page.left()], [[['', Q], 0, '', '', PLAIN], true]);
    },
    'typing alone rewrites the entry after each pause, and never adds one': () => {
      const page = load();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      let before = '';
      for (const text of ['ridge', 'ridge t', 'ridge tr', 'ridge', 'r', '']) {
        page.type(text);
        deq(seen(page), [[before], 0, before, text, PLAIN], JSON.stringify(text));       // not before the pause is over
        page.pause();
        const address = text ? '?q=' + text.replace(/ /g, '+') : '';
        deq(seen(page), [[address], 0, address, text, PLAIN], JSON.stringify(text));
        before = address;
      }
      deq([page.pushes(), page.shown()], [0, ACTIVE]);
      page.back();
      deq([seen(page), page.left()], [[[''], 0, '', '', PLAIN], true], 'typing alone made a step to come back to');
    },
    // ---- (c)
    'type and Enter at once, Back': () => {
      const page = load();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      page.type('ridge');
      deq(seen(page), [[''], 0, '', 'ridge', PLAIN]);
      page.enter();                                         // before the typing pause is over
      deq(seen(page), [['', Q], 1, Q, 'ridge', PLAIN]);
      deq([page.calls(), page.shown()], [['replace ', 'push ' + Q], RIDGE]);     // nothing to put back: the entry was never rewritten
      page.pause();                                         // the typing timer was cancelled: no late write
      deq(seen(page), [['', Q], 1, Q, 'ridge', PLAIN]);
      deq(page.calls(), ['replace ', 'push ' + Q]);
      page.back();
      deq(seen(page), [['', Q], 0, '', '', PLAIN]);
      deq([page.shown(), page.left()], [ACTIVE, false]);
      page.back();
      deq([seen(page), page.left()], [[['', Q], 0, '', '', PLAIN], true]);
    },
    // ---- (d)
    'a search with an apostrophe, a curly one, a space, + & % # or an accent: type, pause, Enter three times is one new entry': () => {
      // [the words typed, the address bar's spelling of them]. The page writes them its own way (encodeURIComponent, a
      // space as +); of these characters the browser respells the straight apostrophe alone
      const SPELLED = [
        ["lover's", 'lover%27s'], ['l’ete', 'l%E2%80%99ete'], ['ridge walk', 'ridge+walk'], ['a+b', 'a%2Bb'], ['r&r', 'r%26r'],
        ['50% off', '50%25+off'], ['#1 ridge', '%231+ridge'], ['crête', 'cr%C3%AAte'],
        ["lover's l’été a+b & 50% #1 crête", 'lover%27s+l%E2%80%99%C3%A9t%C3%A9+a%2Bb+%26+50%25+%231+cr%C3%AAte'],
      ];
      for (const [typed, spelled] of SPELLED) {
        const address = '?q=' + spelled;
        const page = load();
        deq(seen(page), [[''], 0, '', '', PLAIN], typed);
        page.type(typed);
        deq(seen(page), [[''], 0, '', typed, PLAIN], typed);
        page.pause();
        deq(seen(page), [[address], 0, address, typed, PLAIN], typed);         // the pause wrote the words into the entry
        page.enter();
        deq(seen(page), [['', address], 1, address, typed, PLAIN], typed);     // one new entry, the list before the search under it
        page.enter();                                                           // at once
        deq(seen(page), [['', address], 1, address, typed, PLAIN], typed);
        page.pause();
        deq(seen(page), [['', address], 1, address, typed, PLAIN], typed);
        page.enter();                                                           // and long after, when no entry was 'made a moment ago'
        deq(seen(page), [['', address], 1, address, typed, PLAIN], 'Enter on the same view added an entry: ' + typed);
        eq(page.pushes(), 1, typed);
        page.back();
        deq(seen(page), [['', address], 0, '', '', PLAIN], typed);
        deq([page.shown(), page.left()], [ACTIVE, false], typed);
        // Forward: the words are in the box as they were typed, and the entry stands for them
        page.forward();
        deq(seen(page), [['', address], 1, address, typed, PLAIN], typed);
        page.pause();
        deq(seen(page), [['', address], 1, address, typed, PLAIN], typed);
        page.enter();
        deq(seen(page), [['', address], 1, address, typed, PLAIN], 'Enter after Forward added an entry: ' + typed);
        eq(page.pushes(), 1, typed);
        // a second search, Enter before the typing pause is over: nothing had been rewritten, so nothing is put back
        const calls = page.calls().length, longer = address + '+x';
        page.type(typed + ' x');
        deq(seen(page), [['', address], 1, address, typed + ' x', PLAIN], typed);
        page.enter();
        deq(seen(page), [['', address, longer], 2, longer, typed + ' x', PLAIN], typed);
        deq(page.calls().slice(calls), ['push ' + longer], typed);
        // and the address opened directly (a shared link, a reload) is the view its entry stands for
        const opened = load({ search: address });
        deq(seen(opened), [[address], 0, address, typed, PLAIN], typed);
        opened.pause();
        deq(seen(opened), [[address], 0, address, typed, PLAIN], typed);
        opened.enter();
        deq(seen(opened), [[address], 0, address, typed, PLAIN], 'Enter on the address as it was opened added an entry: ' + typed);
        eq(opened.pushes(), 0, typed);
      }
    },
    // ---- (e)
    'arrow keys through three activities, then a search: Back shows the last activity, the next Back the list the page opened on': () => {
      arrows('activity', [FIRST, SECOND, THIRD]);
    },
    'arrow keys through three scopes, then a search: Back shows the last scope, the next Back the list the page opened on': () => {
      arrows('scope', MODEL.scopes.filter((s) => s !== 'active').slice(0, 3));
    },
    'picks within a moment make one entry, later ones one each': () => {
      const one = '?activity=' + FIRST, two = '?activity=' + SECOND;
      const page = load();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      page.pause();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      page.activity(FIRST);
      deq(seen(page), [['', one], 1, one, '', set({ activity: FIRST })]);
      page.pause(700);
      deq(seen(page), [['', one], 1, one, '', set({ activity: FIRST })]);
      page.activity(SECOND);
      deq(seen(page), [['', one, two], 2, two, '', set({ activity: SECOND })]);
      // the moment is 600 ms, counted from the entry that was made: at 599 the next pick still rewrites it, at 600 it
      // makes its own
      page.pause(599);
      deq(seen(page), [['', one, two], 2, two, '', set({ activity: SECOND })]);
      page.view('list');
      deq(seen(page), [['', one, two + '&view=list'], 2, two + '&view=list', '', set({ activity: SECOND, view: 'list' })]);
      page.pause(1);
      deq(seen(page), [['', one, two + '&view=list'], 2, two + '&view=list', '', set({ activity: SECOND, view: 'list' })]);
      page.view('cards');
      deq(seen(page), [['', one, two + '&view=list', two], 3, two, '', set({ activity: SECOND })]);
      eq(page.pushes(), 3);
    },
    'a filter picked within a moment of a submitted search is part of what its entry stands for': () => {
      const filtered = Q + '&activity=' + FIRST, loop = LOOP + '&activity=' + FIRST;
      const page = load();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      page.type('ridge');
      deq(seen(page), [[''], 0, '', 'ridge', PLAIN]);
      page.enter();
      deq(seen(page), [['', Q], 1, Q, 'ridge', PLAIN]);
      page.pause(100);
      deq(seen(page), [['', Q], 1, Q, 'ridge', PLAIN]);
      page.activity(FIRST);                                 // within the moment: the search's entry is rewritten
      deq(seen(page), [['', filtered], 1, filtered, 'ridge', set({ activity: FIRST })]);
      page.pause();
      deq(seen(page), [['', filtered], 1, filtered, 'ridge', set({ activity: FIRST })]);
      page.type('loop');
      deq(seen(page), [['', filtered], 1, filtered, 'loop', set({ activity: FIRST })]);
      page.pause();
      deq(seen(page), [['', loop], 1, loop, 'loop', set({ activity: FIRST })]);
      page.enter();
      deq(seen(page), [['', filtered, loop], 2, loop, 'loop', set({ activity: FIRST })]);
      page.back();
      deq(seen(page), [['', filtered, loop], 1, filtered, 'ridge', set({ activity: FIRST })], 'Back lost the filter the visitor had chosen');
      deq(page.shown(), listed({ activity: FIRST }, 'ridge'));
      page.back();
      deq(seen(page), [['', filtered, loop], 0, '', '', PLAIN]);
    },
    'a search submitted within a moment of a filter rewrites the filter\'s entry, and is what it stands for': () => {
      const filtered = Q + '&activity=' + FIRST, loop = LOOP + '&activity=' + FIRST;
      const page = load();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      page.pause();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      page.activity(FIRST);
      deq(seen(page), [['', '?activity=' + FIRST], 1, '?activity=' + FIRST, '', set({ activity: FIRST })]);
      page.pause(100);
      deq(seen(page), [['', '?activity=' + FIRST], 1, '?activity=' + FIRST, '', set({ activity: FIRST })]);
      page.type('ridge');
      deq(seen(page), [['', '?activity=' + FIRST], 1, '?activity=' + FIRST, 'ridge', set({ activity: FIRST })]);
      page.enter();                                         // Enter within the moment: no second entry
      deq(seen(page), [['', filtered], 1, filtered, 'ridge', set({ activity: FIRST })]);
      eq(page.pushes(), 1);
      page.pause();
      deq(seen(page), [['', filtered], 1, filtered, 'ridge', set({ activity: FIRST })]);
      page.type('loop');
      deq(seen(page), [['', filtered], 1, filtered, 'loop', set({ activity: FIRST })]);
      page.pause();
      deq(seen(page), [['', loop], 1, loop, 'loop', set({ activity: FIRST })]);
      page.enter();
      deq(seen(page), [['', filtered, loop], 2, loop, 'loop', set({ activity: FIRST })]);
      page.back();
      deq(seen(page), [['', filtered, loop], 1, filtered, 'ridge', set({ activity: FIRST })], 'Back did not return to the search the entry stood for');
      deq(page.shown(), listed({ activity: FIRST }, 'ridge'));
    },
    // ---- (f)
    'type, pause, pick a filter, Back: the typed search without the filter': () => {
      for (const [name, press, o, address, box] of CONTROLS) {
        const page = load();
        deq(seen(page), [[''], 0, '', '', PLAIN], name);
        page.type('ridge');
        deq(seen(page), [[''], 0, '', 'ridge', PLAIN], name);
        page.pause();
        deq(seen(page), [[Q], 0, Q, 'ridge', PLAIN], name);
        press(page);
        deq(seen(page), [[Q, address], 1, address, box, set(o)], name);     // typing is kept when a pick follows: nothing is put back
        deq(page.calls(), ['replace ', 'replace ' + Q, 'push ' + address], name);
        deq(page.shown(), listed(o, box), name);
        page.pause();
        deq(seen(page), [[Q, address], 1, address, box, set(o)], name);
        page.enter();                                         // the pick is what its entry stands for
        deq(seen(page), [[Q, address], 1, address, box, set(o)], name);
        page.back();
        deq(seen(page), [[Q, address], 0, Q, 'ridge', PLAIN], 'Back did not show the typed search without the filter: ' + name);
        deq([page.shown(), page.chips(), page.left()], [RIDGE, ['Search: ridge'], false], name);
        page.pause();
        deq(seen(page), [[Q, address], 0, Q, 'ridge', PLAIN], name);
        page.enter();                                         // come back to, the typed search is what its entry stands for
        deq(seen(page), [[Q, address], 0, Q, 'ridge', PLAIN], name);
        eq(page.pushes(), 1, name);
        page.back();                                          // the list before the typing was never an entry of its own
        deq([seen(page), page.left()], [[[Q, address], 0, Q, 'ridge', PLAIN], true], name);
      }
      // the empty state's own button is Clear all too
      const page = load();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      page.type('zzzz');
      deq(seen(page), [[''], 0, '', 'zzzz', PLAIN]);
      page.pause();
      deq(seen(page), [['?q=zzzz'], 0, '?q=zzzz', 'zzzz', PLAIN]);
      deq(page.shown(), []);
      page.clearFilters();
      deq(seen(page), [['?q=zzzz', ''], 1, '', '', PLAIN]);
      deq(page.shown(), ACTIVE);
      page.back();
      deq(seen(page), [['?q=zzzz', ''], 0, '?q=zzzz', 'zzzz', PLAIN]);
    },
    // ---- (g)
    'a submitted search, then a filter, then Back, Back': () => {
      const filtered = Q + '&activity=' + FIRST;
      const page = searched();
      page.activity(FIRST);
      deq(seen(page), [['', Q, filtered], 2, filtered, 'ridge', set({ activity: FIRST })]);
      deq([page.calls().slice(-1), page.shown()], [['push ' + filtered], listed({ activity: FIRST }, 'ridge')]);
      page.pause();
      deq(seen(page), [['', Q, filtered], 2, filtered, 'ridge', set({ activity: FIRST })]);
      page.back();
      deq(seen(page), [['', Q, filtered], 1, Q, 'ridge', PLAIN]);
      deq(page.shown(), RIDGE);
      page.back();
      deq(seen(page), [['', Q, filtered], 0, '', '', PLAIN]);
      deq([page.shown(), page.left()], [ACTIVE, false]);
      page.forward();
      deq(seen(page), [['', Q, filtered], 1, Q, 'ridge', PLAIN]);
      page.forward();
      deq(seen(page), [['', Q, filtered], 2, filtered, 'ridge', set({ activity: FIRST })]);
      deq([page.shown(), page.pushes()], [listed({ activity: FIRST }, 'ridge'), 2]);
    },
    // ---- (h)
    'Enter in an empty box on a fresh page adds no entry': () => {
      const page = load();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      page.enter();                                         // at once, before anything else is done
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      page.pause();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      page.enter();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      deq(page.calls(), ['replace ', 'replace ', 'replace ']);
      page.back();
      deq([seen(page), page.left()], [[[''], 0, '', '', PLAIN], true]);
      // nor on a page opened with a filter in its address, or with a fragment (which goes with the first thing the
      // visitor does)
      const there = '?activity=' + FIRST + '&scope=all';
      const filtered = load({ search: there });
      deq(seen(filtered), [[there], 0, there, '', set({ activity: FIRST, scope: 'all' })]);
      filtered.enter();
      deq(seen(filtered), [[there], 0, there, '', set({ activity: FIRST, scope: 'all' })]);
      eq(filtered.pushes(), 0);
      const linked = load({ hash: '#search' });
      deq(seen(linked), [['#search'], 0, '#search', '', PLAIN]);
      linked.enter();
      deq(seen(linked), [[''], 0, '', '', PLAIN]);
      eq(linked.pushes(), 0);
      // typed and emptied again: the view the entry stood for, so no entry, and the address says so again
      const emptied = load();
      deq(seen(emptied), [[''], 0, '', '', PLAIN]);
      emptied.type('ridge');
      deq(seen(emptied), [[''], 0, '', 'ridge', PLAIN]);
      emptied.pause();
      deq(seen(emptied), [[Q], 0, Q, 'ridge', PLAIN]);
      emptied.type('');
      deq(seen(emptied), [[Q], 0, Q, '', PLAIN]);
      emptied.enter();
      deq(seen(emptied), [[''], 0, '', '', PLAIN]);
      deq([emptied.pushes(), emptied.shown()], [0, ACTIVE]);
    },
    // ---- (i)
    'two different searches submitted in a row are two entries, and Back, Back walks them': () => {
      const page = searched();
      page.type('loop');
      deq(seen(page), [['', Q], 1, Q, 'loop', PLAIN]);
      page.pause();
      deq(seen(page), [['', LOOP], 1, LOOP, 'loop', PLAIN]);            // typing rewrites the entry of the first search,
      page.enter();
      deq(seen(page), [['', Q, LOOP], 2, LOOP, 'loop', PLAIN]);         // and Enter puts it back under the second search's own
      deq(page.calls().slice(-2), ['replace ' + Q, 'push ' + LOOP]);
      deq([page.pushes(), page.shown()], [2, LOOP_FOUND]);
      page.back();
      deq(seen(page), [['', Q, LOOP], 1, Q, 'ridge', PLAIN]);
      deq(page.shown(), RIDGE);
      page.back();
      deq(seen(page), [['', Q, LOOP], 0, '', '', PLAIN]);
      deq([page.shown(), page.left()], [ACTIVE, false]);
      page.back();
      deq([seen(page), page.left()], [[['', Q, LOOP], 0, '', '', PLAIN], true]);
      // each Enter before its typing pause is over: the same two entries, and nothing to put back
      const quick = load();
      deq(seen(quick), [[''], 0, '', '', PLAIN]);
      quick.type('ridge');
      deq(seen(quick), [[''], 0, '', 'ridge', PLAIN]);
      quick.enter();
      deq(seen(quick), [['', Q], 1, Q, 'ridge', PLAIN]);
      quick.pause();
      deq(seen(quick), [['', Q], 1, Q, 'ridge', PLAIN]);
      quick.type('loop');
      deq(seen(quick), [['', Q], 1, Q, 'loop', PLAIN]);
      quick.enter();
      deq(seen(quick), [['', Q, LOOP], 2, LOOP, 'loop', PLAIN]);
      deq(quick.calls(), ['replace ', 'push ' + Q, 'push ' + LOOP]);
    },
    // ---- (j)
    'each kind of control makes one entry: an activity, the scope, a menu, the route switch, the view, a chip removed, Clear all': () => {
      const page = load();
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      const want = [''];
      const region = 'Region: ' + MODEL.labels.region[REGION];
      // [the press, the address it gives, the controls then]: each on top of the ones before it
      const steps = [
        [() => page.activity(FIRST), '?activity=' + FIRST, { activity: FIRST }],
        [() => page.scope('all'), '?activity=' + FIRST + '&scope=all', { activity: FIRST, scope: 'all' }],
        [() => page.choose('region', REGION), '?activity=' + FIRST + '&region=' + REGION + '&scope=all', { activity: FIRST, region: REGION, scope: 'all' }],
        [() => page.route(), '?activity=' + FIRST + '&region=' + REGION + '&gpx=1&scope=all', { activity: FIRST, region: REGION, gpx: true, scope: 'all' }],
        [() => page.view('list'), '?activity=' + FIRST + '&region=' + REGION + '&gpx=1&scope=all&view=list',
          { activity: FIRST, region: REGION, gpx: true, scope: 'all', view: 'list' }],
        [() => page.removeChip(region), '?activity=' + FIRST + '&gpx=1&scope=all&view=list', { activity: FIRST, gpx: true, scope: 'all', view: 'list' }],
        [() => page.choose('sort', 'added'), '?activity=' + FIRST + '&gpx=1&scope=all&sort=added&view=list',
          { activity: FIRST, gpx: true, scope: 'all', sort: 'added', view: 'list' }],
        // Clear all: the filters go; the scope, the sort and the view are not filters and stay
        [() => page.clearAll(), '?scope=all&sort=added&view=list', { scope: 'all', sort: 'added', view: 'list' }],
        [() => page.route(), '?gpx=1&scope=all&sort=added&view=list', { gpx: true, scope: 'all', sort: 'added', view: 'list' }],
        [() => page.route(), '?scope=all&sort=added&view=list', { scope: 'all', sort: 'added', view: 'list' }],     // the switch, off again
      ];
      let before = {};
      for (const [press, address, o] of steps) {
        page.pause();
        deq(seen(page), [want, want.length - 1, want[want.length - 1], '', set(before)], address);
        press();
        want.push(address);
        deq(seen(page), [want, want.length - 1, address, '', set(o)], address);
        deq([page.shown(), page.calls().slice(-1)], [listed(o), ['push ' + address]], address);
        before = o;
      }
      eq(page.pushes(), steps.length);
      // the same choice pressed again is not a change of view
      page.pause();
      deq(seen(page), [want, want.length - 1, want[want.length - 1], '', set({ scope: 'all', sort: 'added', view: 'list' })]);
      page.view('list');
      deq(seen(page), [want, want.length - 1, want[want.length - 1], '', set({ scope: 'all', sort: 'added', view: 'list' })]);
      page.scope('all');
      deq(seen(page), [want, want.length - 1, want[want.length - 1], '', set({ scope: 'all', sort: 'added', view: 'list' })]);
      page.activity('all');
      deq(seen(page), [want, want.length - 1, want[want.length - 1], '', set({ scope: 'all', sort: 'added', view: 'list' })]);
      eq(page.pushes(), steps.length);
      // each menu by itself, and each chip's remove button: one entry each, on a page of its own
      const menus = [['region', REGION, 'Region: '], ['status', STATUS, 'Status: '], ['priority', PRIORITY, 'Priority: '], ['month', MONTH, 'Month: ']];
      for (const [name, value, prefix] of menus) {
        const there = '?' + name + '=' + value, chip = prefix + MODEL.labels[name][value];
        const other = load();
        deq(seen(other), [[''], 0, '', '', PLAIN], name);
        other.pause();
        deq(seen(other), [[''], 0, '', '', PLAIN], name);
        other.choose(name, value);
        deq(seen(other), [['', there], 1, there, '', set({ [name]: value })], name);
        deq([other.shown(), other.chips(), other.pushes()], [listed({ [name]: value }), [chip], 1], name);
        other.pause();
        deq(seen(other), [['', there], 1, there, '', set({ [name]: value })], name);
        other.removeChip(chip);
        deq(seen(other), [['', there, ''], 2, '', '', PLAIN], name);
        deq([other.shown(), other.chips(), other.pushes()], [ACTIVE, [], 2], name);
        other.back();
        deq(seen(other), [['', there, ''], 1, there, '', set({ [name]: value })], name);
      }
    },
    // ---- (k)
    'Back onto an entry, then a search from there, Back': () => {
      const page = searched();
      page.back();
      deq(seen(page), [['', Q], 0, '', '', PLAIN]);
      page.enter();                                         // the entry the visitor came back to stands for what it shows
      deq(seen(page), [['', Q], 0, '', '', PLAIN], 'Enter on the entry come back to made another, or rewrote it');
      eq(page.pushes(), 1);
      page.type('loop');
      deq(seen(page), [['', Q], 0, '', 'loop', PLAIN]);
      page.pause();
      deq(seen(page), [[LOOP, Q], 0, LOOP, 'loop', PLAIN]);            // typing rewrites the entry the visitor is on
      page.enter();
      deq(seen(page), [['', LOOP], 1, LOOP, 'loop', PLAIN]);           // the entries Forward led to are gone
      deq(page.calls().slice(-2), ['replace ', 'push ' + LOOP]);
      page.back();
      deq(seen(page), [['', LOOP], 0, '', '', PLAIN]);
      deq([page.shown(), page.left()], [ACTIVE, false]);
      // Enter before the typing pause is over, straight after the Back: one entry made and nothing put back, because
      // the entry the visitor came back to carries the address it stands for
      const quick = searched();
      quick.back();
      deq(seen(quick), [['', Q], 0, '', '', PLAIN]);
      const calls = quick.calls().length;
      quick.type('loop');
      deq(seen(quick), [['', Q], 0, '', 'loop', PLAIN]);
      quick.enter();
      deq(seen(quick), [['', LOOP], 1, LOOP, 'loop', PLAIN]);
      deq(quick.calls().slice(calls), ['push ' + LOOP], 'the entry come back to was written to before the new one was made');
      // and forward to the search again: Enter there adds nothing, a new search is one entry after it
      const again = searched();
      again.back();
      deq(seen(again), [['', Q], 0, '', '', PLAIN]);
      again.forward();
      deq(seen(again), [['', Q], 1, Q, 'ridge', PLAIN]);
      again.pause();
      deq(seen(again), [['', Q], 1, Q, 'ridge', PLAIN]);
      again.enter();
      deq(seen(again), [['', Q], 1, Q, 'ridge', PLAIN]);
      eq(again.pushes(), 1);
      again.type('loop');
      deq(seen(again), [['', Q], 1, Q, 'loop', PLAIN]);
      again.pause();
      deq(seen(again), [['', LOOP], 1, LOOP, 'loop', PLAIN]);
      again.enter();
      deq(seen(again), [['', Q, LOOP], 2, LOOP, 'loop', PLAIN]);
      again.back();
      deq(seen(again), [['', Q, LOOP], 1, Q, 'ridge', PLAIN]);
      deq(again.shown(), RIDGE);
      // Forward onto a search, after the same words were typed into the entry before it: two entries with one address,
      // and the one the visitor is on stands for the search. With an apostrophe too
      for (const [typed, address] of [['ridge', Q], ["lover's", '?q=lover%27s']]) {
        const twice = load();
        deq(seen(twice), [[''], 0, '', '', PLAIN], typed);
        twice.type(typed);
        deq(seen(twice), [[''], 0, '', typed, PLAIN], typed);
        twice.enter();
        deq(seen(twice), [['', address], 1, address, typed, PLAIN], typed);
        twice.pause();
        deq(seen(twice), [['', address], 1, address, typed, PLAIN], typed);
        twice.back();
        deq(seen(twice), [['', address], 0, '', '', PLAIN], typed);
        twice.type(typed);
        deq(seen(twice), [['', address], 0, '', typed, PLAIN], typed);
        twice.pause();
        deq(seen(twice), [[address, address], 0, address, typed, PLAIN], typed);     // typing rewrites the entry of the plain list
        twice.forward();
        deq(seen(twice), [[address, address], 1, address, typed, PLAIN], typed);
        twice.pause();
        deq(seen(twice), [[address, address], 1, address, typed, PLAIN], typed);
        twice.enter();
        deq(seen(twice), [[address, address], 1, address, typed, PLAIN], 'the entry of the search was rewritten or another added: ' + typed);
        eq(twice.pushes(), 1, typed);
      }
    },
    // ---- (l)
    'type, a jump to a fragment, Enter: the entry the jump made keeps the typed search': () => { typedThenJump({}); },
    'the same in a browser that sends no popstate for a fragment: the hashchange alone settles the entry': () => {
      typedThenJump({ fragmentPopstate: false });
      // typed but not yet written when the link is followed: the link's entry stands for the list that was on screen,
      // and the search submitted there is a new view. (Only in this browser: the Tick list reads the address again on
      // every popstate, one for a fragment too, and the words not yet written are then not in it.)
      const quick = load({ fragmentPopstate: false });
      deq(seen(quick), [[''], 0, '', '', PLAIN]);
      quick.type('ridge');
      deq(seen(quick), [[''], 0, '', 'ridge', PLAIN]);
      quick.jump(LINK);
      deq(seen(quick), [['', LINK], 1, LINK, 'ridge', PLAIN]);
      quick.pause();
      deq(seen(quick), [['', Q], 1, Q, 'ridge', PLAIN]);
      quick.enter();
      deq(seen(quick), [['', '', Q], 2, Q, 'ridge', PLAIN]);
      quick.back();
      deq(seen(quick), [['', '', Q], 1, '', '', PLAIN]);
      deq([quick.shown(), quick.left()], [ACTIVE, false]);
    },
    // ---- (m)
    'a browser that refuses every write to the history (a page opened from a file): each view is put on screen all the same': () => {
      const page = load({ refused: true });
      deq(seen(page), [[''], 0, '', '', PLAIN]);
      deq([page.shown(), page.count()], [ACTIVE, ACTIVE.length + ' OF ' + CARDS.length + ' GOALS']);
      page.type('ridge');
      deq(seen(page), [[''], 0, '', 'ridge', PLAIN]);
      page.pause();
      deq(seen(page), [[''], 0, '', 'ridge', PLAIN]);
      deq([page.shown(), page.chips()], [RIDGE, ['Search: ridge']], 'the typed search was not put on screen');
      page.enter();
      deq(seen(page), [[''], 0, '', 'ridge', PLAIN]);
      deq(page.shown(), RIDGE);
      const o = {};
      for (const [name, press, change] of CONTROLS.slice(0, 9)) {       // every control that adds to the view
        page.pause();
        deq(seen(page), [[''], 0, '', 'ridge', set(o)], name);
        press(page);
        Object.assign(o, change);
        deq(seen(page), [[''], 0, '', 'ridge', set(o)], 'the pick was not put on screen: ' + name);
        deq(page.shown(), listed(o, 'ridge'), name);
      }
      page.pause();
      deq(seen(page), [[''], 0, '', 'ridge', set(o)]);
      page.clearAll();
      deq(seen(page), [[''], 0, '', '', set({ scope: 'all', sort: 'name', view: 'list' })]);
      deq([page.shown(), page.chips()], [listed({ scope: 'all' }), []]);
      deq([page.calls(), page.pushes(), page.left()], [[], 0, false]);
      page.back();                                          // there is one entry: Back leaves the page
      deq([seen(page), page.left()], [[[''], 0, '', '', set({ scope: 'all', sort: 'name', view: 'list' })], true]);
      // A browser that refuses from some moment on (the stand-in's refuse(true)): the entries stay as they are and the
      // page goes on. A refused write changes neither address the page keeps, so once writes are taken again the page
      // is where it should be: the search before is put under the new one, and nothing else is written
      const later = searched();
      later.refuse(true);
      later.type('loop');
      deq(seen(later), [['', Q], 1, Q, 'loop', PLAIN]);
      later.pause();
      deq(seen(later), [['', Q], 1, Q, 'loop', PLAIN]);
      deq(later.shown(), LOOP_FOUND, 'the typed search was not put on screen');
      later.enter();
      deq(seen(later), [['', Q], 1, Q, 'loop', PLAIN]);
      later.pause();
      deq(seen(later), [['', Q], 1, Q, 'loop', PLAIN]);
      const calls = later.calls().length;
      later.refuse(false);
      later.enter();
      deq(seen(later), [['', Q, LOOP], 2, LOOP, 'loop', PLAIN]);
      deq(later.calls().slice(calls), ['push ' + LOOP], 'a refused write was taken for one that happened');
      later.back();
      deq(seen(later), [['', Q, LOOP], 1, Q, 'ridge', PLAIN]);
      deq(later.shown(), RIDGE);
    },
  };
  // GAPS: cases in which the page does not do what the rule above says. Each would be run only when asked for, as
  // 'gap:<name>' and after every check above, by a test of tests/test_ticklist_js.py marked as an expected failure;
  // when the page is put right, that test says so and the case becomes a check above. None at present.
  const GAPS = {};
  const gap = ONLY.replace(/^gap:/, '');
  assert.ok(!ONLY || (ONLY.indexOf('gap:') === 0 && Object.prototype.hasOwnProperty.call(GAPS, gap)), 'unknown argument: ' + ONLY);
  Object.keys(pageChecks).forEach((label) => check('page: ' + label, pageChecks[label]));
  if (ONLY) check('gap: ' + gap, GAPS[gap]);
}

console.log('ticklist_js_harness: ' + checks + ' checks passed');
