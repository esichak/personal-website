#!/usr/bin/env node
'use strict';
/* Phase 2: unit tests for the pure functions of assets/js/pages/trips.js (norm, tokens, parseState, match, score).

   Run by tests/test_trips_js.py (skipped when node is missing); by hand: `node tests/trips_js_harness.js [trips.js]`.
   The optional argument points at another module with the same exports (used to prove the harness fails a wrong one).
   Every failed assertion throws, so the process exits non-zero. norm() is checked against tests/norm_cases.json, the
   table tests/test_search.py holds search.normalize to, so the two sides of the search stay in step. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const MODULE = path.resolve(process.argv[2] || path.join(__dirname, '..', 'assets', 'js', 'pages', 'trips.js'));
const CASES = path.join(__dirname, 'norm_cases.json');

assert.strictEqual(typeof document, 'undefined', 'the harness runs without a DOM');
assert.ok(fs.existsSync(MODULE), 'missing ' + MODULE);
const TRX = require(MODULE);   // must export TRX before touching the DOM (there is none here)

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
  eq(typeof TRX, 'object');
  for (const name of ['norm', 'tokens', 'parseState', 'match', 'score', 'chipLabel']) {
    eq(typeof TRX[name], 'function', 'TRX.' + name + ' is not a function');
  }
});

// ---------------------------------------------------------------- norm (parity with search.normalize)

const cases = JSON.parse(fs.readFileSync(CASES, 'utf8'));
assert.ok(Array.isArray(cases) && cases.length > 0, 'norm_cases.json is empty');
for (const [input, want] of cases) {
  check('norm ' + JSON.stringify(input), () => eq(TRX.norm(input), want));
}
check('norm contract examples', () => {
  eq(TRX.norm("Lover's Leap: Corrugation Corner"), 'lover s leap corrugation corner');
  eq(TRX.norm('Chamonix – Zermatt'), 'chamonix zermatt');
  eq(TRX.norm(''), '');
});
check('norm is idempotent and yields single-spaced lower-case ASCII words', () => {
  for (const [input] of cases) {
    const out = TRX.norm(input);
    eq(TRX.norm(out), out);
    assert.ok(/^$|^[a-z0-9]+( [a-z0-9]+)*$/.test(out), JSON.stringify(out));
  }
});

// ---------------------------------------------------------------- tokens

check('tokens', () => {
  deq(TRX.tokens("Lover's  Leap: Corrugation"), ['lover', 's', 'leap', 'corrugation']);
  deq(TRX.tokens('Matterhorn'), ['matterhorn']);
  deq(TRX.tokens('  Vallée   Blanche '), ['vallee', 'blanche']);
  deq(TRX.tokens(''), []);
  deq(TRX.tokens('  !!  --- '), []);
});

// ---------------------------------------------------------------- parseState

const ALLOWED = {
  activity: ['all', 'ski', 'climb', 'hike'],
  region: ['', 'eastern-sierra', 'alps', 'pacific-crest-trail'],
  year: ['', '2026', '2025', '2024'],
  format: ['', 'trip', 'multi-day', 'series'],
  sort: ['newest', 'oldest', 'relevance'],
  view: ['cards', 'list'],
};
const DEFAULTS = { q: '', activity: 'all', region: '', year: '', format: '', writeup: false, sort: 'newest', view: 'cards' };
const st = (s) => TRX.parseState(s, ALLOWED);
const withDefaults = (o) => Object.assign({}, DEFAULTS, o);

check('parseState defaults', () => {
  deq(st(''), DEFAULTS);
  deq(st('?'), DEFAULTS);
});
check('parseState reads every key, with or without the leading ?', () => {
  const want = { q: 'matterhorn', activity: 'ski', region: 'eastern-sierra', year: '2025', format: 'trip', writeup: true, sort: 'oldest', view: 'list' };
  const qs = 'q=matterhorn&activity=ski&region=eastern-sierra&year=2025&format=trip&writeup=1&sort=oldest&view=list';
  deq(st('?' + qs), want);
  deq(st(qs), want);
});
check('parseState contract example', () => deq(st('?q=matterhorn&activity=ski'), withDefaults({ q: 'matterhorn', activity: 'ski' })));
check('parseState ignores unknown keys', () => deq(st('?foo=bar&utm_source=x&page=2&q=dana'), withDefaults({ q: 'dana' })));
check('parseState resets values outside allowed', () => {
  deq(st('?activity=swim&region=mars&year=1999&format=weird&sort=random&view=table'), DEFAULTS);
  deq(st('?activity=SKI'), DEFAULTS);   // exact values only
});
check('parseState keeps valid values beside invalid ones', () => deq(st('?activity=ski&region=mars&year=2024'), withDefaults({ activity: 'ski', year: '2024' })));
check('parseState writeup is true only for writeup=1', () => {
  eq(st('?writeup=1').writeup, true);
  for (const v of ['0', 'true', 'yes', '', '2', 'on']) eq(st('?writeup=' + v).writeup, false, 'writeup=' + v);
  eq(st('?q=a').writeup, false);
});
check('parseState decodes the query text as a form-encoded value', () => {
  eq(st('?q=lover%27s%20leap').q, "lover's leap");
  eq(st('?q=half+dome').q, 'half dome');
  eq(st('?q=vall%C3%A9e').q, 'vallée');
  eq(st('?q=').q, '');
});
check('parseState returns exactly the eight state keys', () => {
  deq(Object.keys(st('?q=a&zzz=1')).sort(), Object.keys(DEFAULTS).sort());
  deq(Object.keys(st('')).sort(), Object.keys(DEFAULTS).sort());
});

// ---------------------------------------------------------------- match / score

const ENTRY = {
  s: 'matterhorn-peak-west-couloir',
  t: 'matterhorn peak west couloir',
  p: 'sawtooth ridge eastern sierra',
  k: 'matterhorn peak sawtooth',
  x: 'skinned up from twin lakes before dawn and skied the couloir on firm snow',
  n: 'Skinned up from Twin Lakes before dawn…',
};
const OTHER = { s: 'slugonly', t: 'basin loop', p: 'eastern sierra', k: '', x: 'a loop over three summits', n: 'zzzsnippet only' };

check('match', () => {
  eq(TRX.match(ENTRY, ['matterhorn']), true);
  eq(TRX.match(ENTRY, ['matter']), true);                  // substring, not whole word
  eq(TRX.match(ENTRY, ['matterhorn', 'sierra']), true);    // tokens may hit different fields
  eq(TRX.match(ENTRY, ['dawn']), true);                    // body text
  eq(TRX.match(ENTRY, ['sawtooth']), true);                // place / keywords
  eq(TRX.match(ENTRY, ['matterhorn', 'zermatt']), false);  // every token must hit
  eq(TRX.match(ENTRY, ['zermatt']), false);
  eq(TRX.match(ENTRY, []), true);                          // no tokens: nothing is filtered out
  eq(TRX.match(OTHER, ['slugonly']), false);               // the slug is not searched
  eq(TRX.match(OTHER, ['zzzsnippet']), false);             // nor the snippet
  eq(TRX.match(OTHER, ['summits', 'basin']), true);
});
check('score', () => {
  eq(TRX.score(ENTRY, ['matterhorn']), 5);   // title 3 + keywords 2 (not in the body)
  eq(TRX.score(ENTRY, ['couloir']), 4);      // title 3 + body 1
  eq(TRX.score(ENTRY, ['sierra']), 2);       // place
  eq(TRX.score(ENTRY, ['sawtooth']), 2);     // in place and in keywords: 2 once, not 4
  eq(TRX.score(ENTRY, ['dawn']), 1);         // body only
  eq(TRX.score(ENTRY, ['zermatt']), 0);
  eq(TRX.score(ENTRY, ['matterhorn', 'dawn']), 6);
  eq(TRX.score(ENTRY, []), 0);
  assert.ok(TRX.score(ENTRY, ['matterhorn']) > TRX.score(OTHER, ['matterhorn']));
});
check('match and score agree for single tokens', () => {
  for (const tok of ['matterhorn', 'sierra', 'dawn', 'zermatt', 'loop', 'summits', 'slugonly', 'zzzsnippet']) {
    for (const e of [ENTRY, OTHER]) {
      eq(TRX.match(e, [tok]), TRX.score(e, [tok]) > 0, tok + ' on ' + e.s);
    }
  }
});


check('snippet shows the words around the first hit, with ellipses only where text was cut', () => {
  const raw = 'Skied the couloir lookers left in the first pic. Overall super solid day getting out with Adam for the first time.';
  eq(TRX.snippet(raw, ['solid'], 3), '… pic. Overall super solid day getting out …');
  eq(TRX.snippet(raw, ['skied'], 2), 'Skied the couloir …');
  eq(TRX.snippet(raw, ['zermatt'], 3), '');
  eq(TRX.snippet('Lover’s Leap again', ['lover'], 2), 'Lover’s Leap again');
  eq(TRX.snippet('', ['x']), '');
});
check('chipLabel names each filter for the chips', () => {
  const names = { activity: { ski: 'Backcountry Ski' }, region: { 'lake-tahoe': 'Lake Tahoe' }, format: { 'multi-day': 'Multi-day' } };
  eq(TRX.chipLabel('q', 'dana', names), 'Search: dana');
  eq(TRX.chipLabel('activity', 'ski', names), 'Backcountry Ski');
  eq(TRX.chipLabel('region', 'lake-tahoe', names), 'Region: Lake Tahoe');
  eq(TRX.chipLabel('region', 'nowhere', names), 'Region: nowhere');
  eq(TRX.chipLabel('year', '2026', names), 'Year: 2026');
  eq(TRX.chipLabel('format', 'multi-day', names), 'Format: Multi-day');
  eq(TRX.chipLabel('writeup', true, names), 'Has a write-up');
});
console.log('trips_js_harness: ' + checks + ' checks passed');
