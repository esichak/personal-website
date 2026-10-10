#!/usr/bin/env node
'use strict';
/* Phase 2T: unit tests for the pure functions behind the tick list page: assets/js/pages/explore.js (the shared helpers
   norm, tokens, parseState, serialize, chipLabel) and assets/js/pages/ticklist.js (its state keys and defaults, the scope
   predicate, the sort comparators, chipLabel).

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
check('Explore.chipLabel keeps the trips page labels', () => {
  const names = { activity: { ski: 'Backcountry Ski' }, region: { 'lake-tahoe': 'Lake Tahoe' } };
  eq(X.chipLabel('q', 'dana', names), 'Search: dana');
  eq(X.chipLabel('activity', 'ski', names), 'Backcountry Ski');
});

console.log('ticklist_js_harness: ' + checks + ' checks passed');
