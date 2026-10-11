#!/usr/bin/env node
'use strict';
/* Phase 2T: unit tests for the pure functions behind the tick list page: assets/js/pages/explore.js (the shared helpers
   norm, tokens, parseState, serialize, chipLabel) and assets/js/pages/ticklist.js (its state keys and defaults, the scope
   predicate, the sort comparators, chipLabel). Phase 4: goalShown, the predicate the page hides and counts its goal
   cards with (the scope, every filter, the search tokens), and adoptForm, what the page takes over from a form the
   visitor used before the script arrived.

   Run by tests/test_ticklist_js.py (skipped when node is missing); by hand:
     node tests/ticklist_js_harness.js [explore.js] [ticklist.js]
   The optional arguments point at other modules with the same exports (used to prove the harness fails a wrong one).
   Every failed assertion throws, so the process exits non-zero. norm() is held to tests/norm_cases.json, the table
   tests/test_search.py checks search.normalize against. Card records are shaped like the cards' data attributes
   (li.dataset: strings, archived '1' | '0'), which is all the page's filtering reads. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

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
  for (const name of ['norm', 'tokens', 'parseState', 'serialize', 'chipLabel']) {
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

console.log('ticklist_js_harness: ' + checks + ' checks passed');
