#!/usr/bin/env node
'use strict';
/* Unit tests for the pure functions of assets/js/pages/trips.js. Phase 2: norm, tokens, parseState, match, score,
   snippet, chipLabel. Phase 3: the journal-day search (dayHits, dayMeta, dayHref, dayText) and the wording decisions of
   the status line and the "Journal days" list (countText, daysCount, daysHead, daysListed, daysMoreText, failText).
   Phase 4: facetOk, the filter predicate the page hides and counts its cards with; adoptForm and ownSort, what the page
   takes over from a form the visitor used before the script arrived; stillFailed and mayLoad, when a search index that
   did not load is asked for again.

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
// ---------------------------------------------------------------- journal days (trips/journal.json)

check('exports: the journal-day helpers', () => {
  for (const name of ['dayHits', 'dayMeta', 'dayHref', 'dayText', 'countText', 'daysCount', 'daysHead', 'daysListed', 'daysMoreText', 'dayShown', 'pending',
    'failText', 'noteText']) {
    eq(typeof TRX[name], 'function', 'TRX.' + name + ' is not a function');
  }
  for (const name of ['DAYS_SHOWN', 'FAIL', 'FAIL_REPORTS', 'LOADING']) assert.ok(name in TRX, 'TRX.' + name + ' is missing');
});

// One entry as tools/sitegen/search.py day_entry writes it, without its 'q' (the journal's title and aliases, added to the
// QDAYS fixtures further down): 't' and 'x' are the day's own title and write-up, 'p' is its name ('day 2 5'), and 'j' is
// the journal's title for display. The fixtures are plain ASCII, so lower-casing and
// single spaces are the whole normalisation (no need to lean on TRX.norm here).
const words = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
function day(label, title, text, more) {
  return Object.assign({ s: 'long-walk', a: 'day-' + label.replace(/[^A-Za-z0-9]+/g, '-'), n: label, j: 'Long Walk 2023', h: title, w: '',
    t: words(title), p: words('day ' + label), k: '', x: words(text), r: text }, more);
}
const DAYS = [
  day('1', 'Trailhead', 'Synthetic entry one about a creek ford.', { w: 'Jun 1, 2023' }),
  day('2', 'Ridge', '', { w: 'Jun 2, 2023' }),                                       // a title and a track, no write-up
  day('2.5', 'Creek Town', 'Synthetic entry two: a zero day in town.', { w: 'Jun 3, 2023' }),
  day('4', '', 'Synthetic entry three with no title and one creek.'),               // untitled, undated
];
const [DAY_1, DAY_2, DAY_2_5, DAY_4] = DAYS;
// the day anchors a query finds, in the order they would be listed
const found = (days, q) => TRX.dayHits(days, TRX.tokens(q)).map((e) => e.a);

check('the fixture entries have the shape of the journal index, less its q field', () => {
  deq(DAY_2_5, { s: 'long-walk', a: 'day-2-5', n: '2.5', j: 'Long Walk 2023', h: 'Creek Town', w: 'Jun 3, 2023', t: 'creek town', p: 'day 2 5', k: '',
    x: 'synthetic entry two a zero day in town', r: 'Synthetic entry two: a zero day in town.' });
  deq([DAY_1.p, DAY_2.p, DAY_4.p], ['day 1', 'day 2', 'day 4']);
  deq([DAY_2.x, DAY_2.r, DAY_4.t, DAY_4.h], ['', '', '', '']);
});

check('dayHits: nothing without tokens, nothing without an index', () => {
  deq(TRX.dayHits(DAYS, []), []);
  deq(found(DAYS, ''), []);
  deq(found(DAYS, '  !! -- '), []);      // a query of punctuation has no tokens
  deq(TRX.dayHits(null, ['creek']), []);
  deq(TRX.dayHits(undefined, ['creek']), []);
  deq(TRX.dayHits([], ['creek']), []);
});
check('dayHits: every token must be in the day\'s own title or write-up', () => {
  deq(TRX.dayHits(DAYS, ['ford']), [DAY_1]);            // the entries themselves come back
  deq(found(DAYS, 'creek ford'), ['day-1']);
  deq(found(DAYS, 'zero ford'), []);                    // each word is in some day, no day has both
  deq(found(DAYS, 'town zero'), ['day-2-5']);           // one token in the title, the other in the write-up
  deq(found(DAYS, 'for'), ['day-1']);                   // substring, as for trips
  deq(found(DAYS, 'zermatt'), []);
});
check('dayHits: title hits outrank write-up hits, and ties keep index order', () => {
  deq(found(DAYS, 'creek'), ['day-2-5', 'day-1', 'day-4']);   // title (3) above the two write-up hits (1 each, in index order)
  const rank = [
    day('1', '', 'Forded the creek.'),                    // write-up: 1
    day('2', 'Creek Town', ''),                           // title: 3
    day('3', 'Creek Camp', 'Slept beside the creek.'),    // title and write-up: 4
    day('4', '', 'Another creek crossing.'),              // write-up: 1
    day('5', 'Creekside', ''),                            // title: 3
  ];
  deq(found(rank, 'creek'), ['day-3', 'day-2', 'day-5', 'day-1', 'day-4']);
  deq(found(rank.slice().reverse(), 'creek'), ['day-3', 'day-5', 'day-2', 'day-4', 'day-1']);   // ties follow the index, not the labels
  deq(found(rank, 'creek camp'), ['day-3']);
});
check('dayHits leaves the index as it found it', () => {
  const before = JSON.stringify(DAYS);
  const toks = ['creek', 'town'];
  TRX.dayHits(DAYS, toks);
  eq(JSON.stringify(DAYS), before);
  deq(toks, ['creek', 'town']);
  deq(DAYS.map((e) => e.a), ['day-1', 'day-2', 'day-2-5', 'day-4']);
});
check('dayHits: the journal\'s own name finds no day', () => {
  for (const q of ['long walk', 'Long Walk 2023', 'long', 'walk', '2023', 'long-walk']) deq(found(DAYS, q), [], q);
  deq(found(DAYS, 'long walk creek'), []);              // 'creek' is in three days; the journal's name is in none
  // unless the day's own words hold it
  const own = DAYS.concat([day('7', 'Camp', 'Synthetic end of the long walk.')]);
  deq(found(own, 'long walk'), ['day-7']);
  deq(found(own, 'Long Walk 2023'), []);
});
// 'q' is the journal's title and aliases (search.py day_entry). Its words never find a day by themselves, but they may
// come along, as whole words, with something of the day's own: its name, or a word of its title or write-up that is not
// also a word of the journal's name.
const QDAYS = DAYS.concat([day('5', '', '', { w: 'Jun 5, 2023' })]).map((e) => Object.assign({}, e, { q: 'long walk 2023 lw' }));
check('dayHits: the journal\'s name or alias alone finds no day, with q in the index too', () => {
  for (const q of ['long walk', 'Long Walk 2023', 'long', 'walk', '2023', 'lw', 'LW long walk', 'long-walk 2023 lw']) deq(found(QDAYS, q), [], q);
});
check('dayHits: the journal\'s name may come along with the day\'s own words', () => {
  deq(found(QDAYS, 'long walk creek'), ['day-2-5', 'day-1', 'day-4']);   // the title hit first, then the write-ups in order
  deq(found(QDAYS, 'creek'), ['day-2-5', 'day-1', 'day-4']);             // the same days, the same order: riding words score nothing
  deq(found(QDAYS, 'lw ridge'), ['day-2']);
  deq(found(QDAYS, 'ridge lw'), ['day-2']);
  deq(found(QDAYS, 'lw zero'), ['day-2-5']);
});
check('dayHits: the journal\'s name may come along with the day\'s name, as a result row prints it', () => {
  deq(found(QDAYS, 'lw day 2'), ['day-2']);
  deq(found(QDAYS, 'Long Walk 2023 · Day 2.5'), ['day-2-5']);
  deq(found(QDAYS, 'Long Walk 2023 · Day 1 · Jun 1, 2023'), []);          // the date is not searched: 'jun' is nobody's word
  deq(found(QDAYS, 'long walk day 4'), ['day-4']);
});
check('dayHits: only whole words of the journal\'s name ride along', () => {
  deq(found(QDAYS, 'creek 2'), []);            // '2' is inside '2023' but is not a word of it
  deq(found(QDAYS, 'creek 20'), []);
  deq(found(QDAYS, 'creek wal'), []);
  deq(found(QDAYS, 'creek walk'), ['day-2-5', 'day-1', 'day-4']);
});
check('dayHits: a word the day shares with its journal\'s name is not something of the day\'s own', () => {
  const own = QDAYS.concat([Object.assign(day('7', 'Camp', 'Synthetic end of the long walk.'), { q: 'long walk 2023 lw' })]);
  deq(found(own, 'long walk'), ['day-7']);          // both words are in the write-up: found by its own text
  deq(found(own, 'long walk 2023'), []);            // '2023' is only the journal's, and nothing else is the day's alone
  deq(found(own, 'long walk 2023 camp'), ['day-7']);
  deq(found(own, 'lw walk'), []);
});
check('dayHits: a day without a title or a write-up is found by its name and by nothing else', () => {
  deq(found(QDAYS, 'day 5'), ['day-5']);
  deq(found(QDAYS, 'lw day 5'), ['day-5']);
  deq(found(QDAYS, '5'), []);
  deq(found(QDAYS, 'day'), ['day-2-5']);            // 'zero day' in a write-up; the bare day has no words to hold it
  deq(TRX.dayText(QDAYS[4], TRX.tokens('day 5')), '');
});
check('dayHits: the day\'s name typed twice still names the day', () => {
  deq(found(QDAYS, 'day 5 day 5'), ['day-5']);
  deq(found(QDAYS, 'day 2 day 2'), ['day-2']);
  deq(found(QDAYS, 'day 2.5 lw day 2.5'), ['day-2-5']);
  deq(found(QDAYS, 'day 1 creek day 1'), ['day-1']);                     // and the word between the two is still the day's own
  deq(found(QDAYS, 'day 1 ridge day 1'), []);                            // or the day is not found: 'ridge' is Day 2's word
  // typed twice it finds what it finds typed once
  for (const q of ['day 1', 'day 2', 'day 2.5', 'day 4', 'day 5']) deq(found(QDAYS, q + ' ' + q), found(QDAYS, q), q);
});
check('dayHits: without q in an entry nothing rides along', () => {
  deq(found(DAYS, 'long walk creek'), []);
  deq(found(DAYS, 'lw ridge'), []);
});

check('dayHits: the day\'s name is given whole or not at all', () => {
  deq(found(DAYS, 'day 4'), ['day-4']);
  deq(found(DAYS, 'Day 4'), ['day-4']);
  deq(found(DAYS, 'day'), ['day-2-5']);                 // only the day whose write-up says 'day', not every day
  deq(found(DAYS, '4'), []);                            // a label alone names nothing
  deq(found(DAYS, 'da 4'), []);                         // the name is compared token by token, not by substring
  deq(found(DAYS, 'day 1'), ['day-1']);
  deq(found(DAYS, 'day 3'), []);                        // no such day
  deq(found(DAYS, 'day 2.5'), ['day-2-5']);             // Day 2 is named too, but '5' is in none of its words
});
check('dayHits: a titled day without a write-up is found by its title or its name', () => {
  deq(found(DAYS, 'ridge'), ['day-2']);
  deq(found(DAYS, 'day 2'), ['day-2']);
  deq(found(DAYS, 'day 2 ridge'), ['day-2']);
  deq(TRX.dayHits(DAYS, ['ridge']), [DAY_2]);
});
check('dayHits: a query that names a day lists it first, whatever the other days\' words score', () => {
  const walk = [
    day('1', 'Two day plan', 'Day 1 of 2 on the synthetic ridge, 12 miles.'),   // 'day' and '2' in its own words: 3 + 1 + 1
    day('2', 'Ridge', ''),                                                       // named by 'day 2'; no write-up at all
    day('12', '', 'A rest day after 20 miles.'),                                 // 'day' and '2' in the write-up: 1 + 1
    day('2.5', 'Half day', 'A 2 mile stroll into town.'),                        // 'day' in the title, '2' in the write-up: 3 + 1
    day('20', 'Pass', 'Snow on the synthetic pass.'),                            // 'day 20' is another name; no 'day' in its words
  ];
  deq(found(walk, 'day 2'), ['day-2', 'day-1', 'day-2-5', 'day-12']);
  deq(found(walk, 'day 20'), ['day-20', 'day-12']);       // Day 12 holds both words and comes first in the index: still second
  deq(found(walk, 'day 12'), ['day-12', 'day-1']);
  deq(found(walk, 'day 2 ridge'), ['day-2', 'day-1']);    // the leftover word is in Day 2's title; Day 1 has all three in its text
  deq(found(walk, 'ridge day 2'), ['day-2', 'day-1']);    // the name may come anywhere in the query
  // however many of the query's words another day holds, in its title and in its write-up
  const busy = [
    day('9', 'Day 2 creek camp lake pass', 'Day 2 creek camp lake pass.'),   // all six tokens, twice over
    day('2', '', 'Creek, camp, lake, pass.'),                                 // named; the four other words once each
  ];
  deq(found(busy, 'day 2 creek camp lake pass'), ['day-2', 'day-9']);
});
check('dayHits: a named day must still hold every other token in its own words', () => {
  const walk = [day('1', 'Two day plan', 'Day 1 of 2 on the synthetic ridge.'), day('2', 'Ridge', ''), day('20', 'Pass', 'Snow on the synthetic pass.')];
  deq(found(walk, 'day 2 pass'), []);                     // Day 2 is named, but 'pass' is another day's word
  deq(found(walk, 'day 2 synthetic'), ['day-1']);         // Day 2 drops out; Day 1 has the three words in its text
  deq(found(walk, 'day 20 pass'), ['day-20']);
  deq(found(walk, 'day 20 snow pass'), ['day-20']);
  deq(found(walk, 'day 20 ridge'), []);
});
check('dayHits: "day 5.2" ranks Day 5.2 above Day 5', () => {
  const fives = [
    day('5', 'Lake', 'Walked 12 miles to the synthetic lake.'),    // named by 'day 5'; the '2' left over is in '12'
    day('5.2', '', 'Synthetic afternoon stroll.'),                 // named whole by 'day 5 2'
    day('2', '', 'Synthetic day 2 of 5.'),                         // not named ('5' sits between), but holds all three tokens
    day('52', 'Pass', 'Synthetic pass.'),                          // 'day 52' is one number, not 5 and 2
  ];
  deq(TRX.tokens('day 5.2'), ['day', '5', '2']);
  deq(found(fives, 'day 5.2'), ['day-5-2', 'day-5', 'day-2']);
  deq(found(fives, 'day 5'), ['day-5', 'day-2']);                  // 'day 5' does not name Day 5.2
  deq(found(fives, 'day 52'), ['day-52']);
  // a Day 5 with no '2' anywhere in its words is not listed for 'day 5.2' at all
  const dry = fives.map((e) => (e.a === 'day-5' ? day('5', 'Lake', 'Walked to the synthetic lake.') : e));
  deq(found(dry, 'day 5.2'), ['day-5-2', 'day-2']);
  // the name must be a consecutive run of the query
  deq(found(fives, 'day 5 lake'), ['day-5']);
  deq(found(fives, 'lake day 5'), ['day-5']);
  deq(found(fives, 'day lake 5'), []);
});
check('dayHits: among named days, title hits outrank write-up hits and ties keep index order', () => {
  const two = [
    day('5', 'Meadow', 'Camped by a lake.'),
    day('5', 'Lake camp', 'Synthetic words.', { s: 'short-walk', j: 'Short Walk 2022' }),
  ];
  const slugs = (q) => TRX.dayHits(two, TRX.tokens(q)).map((e) => e.s);
  deq(slugs('day 5'), ['long-walk', 'short-walk']);       // both named: index order
  deq(slugs('day 5 lake'), ['short-walk', 'long-walk']);  // 'lake' in a title (3) above 'lake' in a write-up (1)
  deq(slugs('day 5 camp'), ['short-walk', 'long-walk']);  // 'camp' in a title above 'camped' in a write-up
  deq(slugs('day 5 meadow'), ['long-walk']);
});

check('dayMeta names the journal, the day as labelled and the date, leaving out what is unknown', () => {
  eq(TRX.dayMeta(DAY_1), 'Long Walk 2023 · Day 1 · Jun 1, 2023');
  eq(TRX.dayMeta(DAY_2_5), 'Long Walk 2023 · Day 2.5 · Jun 3, 2023');
  eq(TRX.dayMeta(DAY_4), 'Long Walk 2023 · Day 4');
});
check('dayHref points at the day on its journal page, relative to trips/', () => {
  eq(TRX.dayHref(DAY_2_5), 'long-walk/#day-2-5');
  eq(TRX.dayHref({ s: 'a b/c', a: 'day-1"x' }), 'a%20b%2Fc/#day-1%22x');   // an index value can never break out of the href
});
check('dayText shows the words around the hit, or the opening when the hit is in the title or the day\'s name', () => {
  eq(TRX.dayText(DAY_1, ['ford']), 'Synthetic entry one about a creek ford.');
  eq(TRX.dayText(DAY_2_5, ['town']), 'Synthetic entry two: a zero day in town.');
  eq(TRX.dayText(DAY_1, ['trailhead']), 'Synthetic entry one about a creek ford.');   // a title hit
  eq(TRX.dayText(DAY_1, ['day', '1']), 'Synthetic entry one about a creek ford.');    // the day was named
  const long = { r: Array.from({ length: 60 }, (_, i) => 'w' + i).join(' ') };
  eq(TRX.dayText(long, ['zzz']).split(' ').length, 25);                    // 24 words and the ellipsis
  assert.ok(TRX.dayText(long, ['zzz']).endsWith(' …'));
  eq(TRX.dayText({ r: '' }, ['x']), '');
});
check('dayText is empty for a titled day without a write-up, however it was found', () => {
  eq(TRX.dayText(DAY_2, ['ridge']), '');
  eq(TRX.dayText(DAY_2, ['day', '2']), '');
  eq(TRX.dayText({}, ['ridge']), '');
});

// ---------------------------------------------------------------- the status line and the journal-day list

check('countText: the total, or how many of it while a search or a filter narrows the list', () => {
  eq(TRX.countText(167, 167, false), '167 REPORTS');
  eq(TRX.countText(3, 167, true), '3 OF 167 REPORTS');
  eq(TRX.countText(0, 167, true), '0 OF 167 REPORTS');
  eq(TRX.countText(167, 167, true), '167 OF 167 REPORTS');   // a filter that happens to keep everything is still a filter
});
check('countText: one report is a REPORT, as the page prints it before the script runs', () => {
  eq(TRX.countText(1, 1, false), '1 REPORT');
  eq(TRX.countText(0, 1, true), '0 OF 1 REPORT');
  eq(TRX.countText(1, 1, true), '1 OF 1 REPORT');
  eq(TRX.countText(1, 2, true), '1 OF 2 REPORTS');     // the noun follows the total, as in '3 OF 167 REPORTS'
  eq(TRX.countText(0, 0, false), '0 REPORTS');
});
check('daysCount: the status line\'s journal-day count, empty for none', () => {
  eq(TRX.daysCount(0), '');
  eq(TRX.daysCount(1), '1 JOURNAL DAY');
  eq(TRX.daysCount(2), '2 JOURNAL DAYS');
  eq(TRX.daysCount(32), '32 JOURNAL DAYS');
});
check('daysHead: the count beside the Journal days heading', () => {
  eq(TRX.daysHead(1), '1 DAY');
  eq(TRX.daysHead(2), '2 DAYS');
  eq(TRX.daysHead(11), '11 DAYS');
});
const rows = (n) => Array.from({ length: n }, (_, i) => day(String(i + 1), 'Stage ' + (i + 1), ''));
check('DAYS_SHOWN is five', () => eq(TRX.DAYS_SHOWN, 5));
check('daysListed: the first five, or all of them once asked', () => {
  const seven = rows(7);
  deq(TRX.daysListed(seven, false), seven.slice(0, 5));
  deq(TRX.daysListed(seven, true), seven);
  deq(TRX.daysListed(seven, false).map((e) => e.n), ['1', '2', '3', '4', '5']);
  for (const n of [0, 1, 4, 5]) {
    eq(TRX.daysListed(rows(n), false).length, n, 'short list of ' + n);
    eq(TRX.daysListed(rows(n), true).length, n, 'short list of ' + n + ', all');
  }
  eq(TRX.daysListed(rows(6), false).length, 5);
  eq(TRX.daysListed(rows(6), true).length, 6);
});
check('daysListed returns a copy and leaves the list alone', () => {
  for (const n of [3, 5, 7]) {
    for (const all of [false, true]) {
      const list = rows(n), before = list.slice();
      const out = TRX.daysListed(list, all);
      assert.notStrictEqual(out, list, 'n=' + n + ' all=' + all + ': the list itself came back');
      out.push('x');
      out.reverse();
      deq(list, before, 'n=' + n + ' all=' + all + ': the list was changed');
      eq(list.length, n);
    }
  }
});
check('daysMoreText: no button until a sixth day, then show all / show fewer', () => {
  for (const n of [0, 1, 4, 5]) {
    eq(TRX.daysMoreText(n, false), '', 'n=' + n);
    eq(TRX.daysMoreText(n, true), '', 'n=' + n + ', all');
  }
  eq(TRX.daysMoreText(6, false), 'Show all 6 journal days');
  eq(TRX.daysMoreText(6, true), 'Show fewer journal days');
  eq(TRX.daysMoreText(32, false), 'Show all 32 journal days');
  eq(TRX.daysMoreText(32, true), 'Show fewer journal days');
});
check('the button shows exactly when the short list holds days back', () => {
  for (let n = 0; n <= 12; n++) {
    const held = n - TRX.daysListed(rows(n), false).length;
    eq(held, Math.max(0, n - TRX.DAYS_SHOWN), 'n=' + n);
    eq(TRX.daysMoreText(n, false) !== '', held > 0, 'n=' + n);
    eq(TRX.daysMoreText(n, true) !== '', held > 0, 'n=' + n + ', all');
  }
});
check('dayShown: a day follows its journal\'s card, and "Has a write-up" asks it of the day itself', () => {
  const written = DAY_1, titled = DAY_2;          // Day 2 has a title and a track, no write-up
  assert.ok(written.x && !titled.x);
  eq(TRX.dayShown(written, true, false), true);
  eq(TRX.dayShown(titled, true, false), true);
  eq(TRX.dayShown(written, true, true), true);
  eq(TRX.dayShown(titled, true, true), false);    // its journal has write-ups; this day does not
  for (const writeup of [false, true]) for (const e of [written, titled]) eq(TRX.dayShown(e, false, writeup), false);   // the card is filtered out, or absent
  eq(TRX.dayShown(written, undefined, false), false);
  eq(TRX.dayShown({ s: 'x' }, true, true), false);
  eq(TRX.dayShown({ s: 'x' }, true, false), true);
});
check('pending: a search waits for both indexes before the count is rewritten or the empty state shown', () => {
  const states = ['none', 'idle', 'loading', 'ready', 'failed'];
  for (const trips of states) for (const days of states) {
    eq(TRX.pending(false, trips, days), false, 'not searching: ' + trips + ' / ' + days);
    eq(TRX.pending(true, trips, days), trips === 'loading' || days === 'loading', trips + ' / ' + days);
  }
  eq(TRX.pending(1, 'ready', 'loading'), true);     // a truthy count of tokens will do
  eq(TRX.pending(0, 'loading', 'loading'), false);
});
check('noteText: what failed, else that the search is still loading, else nothing', () => {
  const states = ['none', 'idle', 'loading', 'ready', 'failed'];
  eq(typeof TRX.LOADING, 'string');
  assert.ok(TRX.LOADING.trim().length > 0);
  for (const trips of states) for (const days of states) for (const searching of [false, true]) {
    const want = trips === 'failed' ? TRX.failText(searching, true, days === 'ready')
      : (TRX.pending(searching, trips, days) ? TRX.LOADING : '');
    eq(TRX.noteText(searching, trips, days), want, [searching, trips, days].join(' / '));
  }
  // the cases a reader meets
  eq(TRX.noteText(true, 'loading', 'loading'), TRX.LOADING);
  eq(TRX.noteText(true, 'ready', 'loading'), TRX.LOADING);     // the count waits for the journal days, so the note stays up
  eq(TRX.noteText(true, 'ready', 'ready'), '');
  eq(TRX.noteText(true, 'ready', 'failed'), '');               // a journal index that failed costs only the day results
  eq(TRX.noteText(true, 'failed', 'ready'), TRX.FAIL_REPORTS);
  eq(TRX.noteText(true, 'failed', 'loading'), TRX.FAIL);
  eq(TRX.noteText(false, 'loading', 'ready'), '');             // the box was cleared while the index was loading
  eq(TRX.noteText(false, 'failed', 'failed'), '');
});
check('FAIL and FAIL_REPORTS are two different messages', () => {
  for (const name of ['FAIL', 'FAIL_REPORTS']) {
    eq(typeof TRX[name], 'string', name);
    assert.ok(TRX[name].trim().length > 0, name + ' is empty');
  }
  assert.notStrictEqual(TRX.FAIL, TRX.FAIL_REPORTS);
});
check('failText: silent unless a search is on and the trip index failed; then it says whether journal days still work', () => {
  // searching, the trip index failed, the journal index is ready -> the message
  const table = [
    [false, false, false, ''],
    [false, false, true, ''],
    [false, true, false, ''],                 // the index failed on an earlier query, the box is empty now
    [false, true, true, ''],
    [true, false, false, ''],                 // the trip index is fine (or still loading)
    [true, false, true, ''],
    [true, true, false, TRX.FAIL],            // nothing can be searched
    [true, true, true, TRX.FAIL_REPORTS],     // journal days are still being found: do not say search is off
  ];
  for (const [searching, tripsFailed, daysReady, want] of table) {
    eq(TRX.failText(searching, tripsFailed, daysReady), want, JSON.stringify([searching, tripsFailed, daysReady]));
  }
});
// ---------------------------------------------------------------- facetOk (the filters: activity, region, year, format, write-up)

// Each card as the page reads it: li.dataset of core.trip_card (data-slug, data-act, data-kind, data-region, data-year,
// data-writeup, data-date), every value a string. A trip without a region or without a date carries '' there; the last
// card has no facet attribute at all (an attribute the page stopped writing must never crash the filter).
const FCARDS = [
  { slug: 'syn-couloir', act: 'ski', kind: 'trip', region: 'eastern-sierra', year: '2026', writeup: '1', date: '2026-01-17' },
  { slug: 'syn-lap', act: 'ski', kind: 'trip', region: 'lake-tahoe', year: '2026', writeup: '0', date: '2026-02-02' },
  { slug: 'syn-traverse', act: 'ski', kind: 'multi-day', region: 'alps', year: '2025', writeup: '1', date: '2025-04-10' },
  { slug: 'syn-loop', act: 'hike', kind: 'trip', region: 'eastern-sierra', year: '2025', writeup: '1', date: '2025-08-10' },
  { slug: 'syn-journal', act: 'hike', kind: 'series', region: 'pacific-crest-trail', year: '2024', writeup: '1', date: '2024-04-22' },
  { slug: 'syn-crag', act: 'climb', kind: 'trip', region: 'lake-tahoe', year: '2024', writeup: '0', date: '2024-06-01' },
  { slug: 'syn-ride', act: 'mtb', kind: 'trip', region: '', year: '2025', writeup: '0', date: '2025-07-04' },
  { slug: 'syn-undated', act: 'hike', kind: 'trip', region: 'lake-tahoe', year: '', writeup: '0', date: '' },
  { slug: 'syn-bare' },
];
const ALL_FCARDS = FCARDS.map((c) => c.slug);
// the values the page's controls offer for these cards (parseState resets anything else to the default)
const FALLOWED = Object.assign({}, ALLOWED, {
  activity: ['all', 'ski', 'climb', 'hike', 'mtb'],
  region: ['', 'alps', 'eastern-sierra', 'lake-tahoe', 'pacific-crest-trail'],
});
const fst = (s) => TRX.parseState(s, FALLOWED);
// the cards a state shows, by slug and in page order: what render() leaves un-hidden when no search is on
const facetShown = (o) => FCARDS.filter((c) => TRX.facetOk(c, withDefaults(o))).map((c) => c.slug);

check('facetOk is exported and answers true or false', () => {
  eq(typeof TRX.facetOk, 'function', 'TRX.facetOk is not a function');
  eq(TRX.facetOk(FCARDS[0], DEFAULTS), true);
  eq(TRX.facetOk(FCARDS[0], withDefaults({ activity: 'hike' })), false);
});
check('facetOk: the default state shows every card', () => {
  deq(facetShown({}), ALL_FCARDS);
  deq(FCARDS.filter((c) => TRX.facetOk(c, DEFAULTS)).length, 9);
  deq(FCARDS.filter((c) => TRX.facetOk(c, TRX.DEFAULTS)).length, 9);      // the page's own defaults
  deq(FCARDS.filter((c) => TRX.facetOk(c, fst(''))).length, 9);           // and a URL without a query
  eq(TRX.facetOk({}, DEFAULTS), true);
});
check('facetOk: the activity filter alone', () => {
  deq(facetShown({ activity: 'ski' }), ['syn-couloir', 'syn-lap', 'syn-traverse']);
  deq(facetShown({ activity: 'hike' }), ['syn-loop', 'syn-journal', 'syn-undated']);
  deq(facetShown({ activity: 'climb' }), ['syn-crag']);
  deq(facetShown({ activity: 'mtb' }), ['syn-ride']);
  deq(facetShown({ activity: 'other' }), []);
  deq(facetShown({ activity: 'all' }), ALL_FCARDS);
});
check('facetOk: the region filter alone', () => {
  deq(facetShown({ region: 'eastern-sierra' }), ['syn-couloir', 'syn-loop']);
  deq(facetShown({ region: 'lake-tahoe' }), ['syn-lap', 'syn-crag', 'syn-undated']);
  deq(facetShown({ region: 'alps' }), ['syn-traverse']);
  deq(facetShown({ region: 'pacific-crest-trail' }), ['syn-journal']);
  deq(facetShown({ region: 'utah' }), []);
  deq(facetShown({ region: '' }), ALL_FCARDS);
});
check('facetOk: the year filter alone', () => {
  deq(facetShown({ year: '2026' }), ['syn-couloir', 'syn-lap']);
  deq(facetShown({ year: '2025' }), ['syn-traverse', 'syn-loop', 'syn-ride']);
  deq(facetShown({ year: '2024' }), ['syn-journal', 'syn-crag']);
  deq(facetShown({ year: '1999' }), []);
  deq(facetShown({ year: '' }), ALL_FCARDS);
});
check('facetOk: the format filter alone reads the card\'s kind', () => {
  deq(facetShown({ format: 'trip' }), ['syn-couloir', 'syn-lap', 'syn-loop', 'syn-crag', 'syn-ride', 'syn-undated']);
  deq(facetShown({ format: 'multi-day' }), ['syn-traverse']);
  deq(facetShown({ format: 'series' }), ['syn-journal']);
  deq(facetShown({ format: 'planned' }), []);
  deq(facetShown({ format: '' }), ALL_FCARDS);
});
check('facetOk: "Has a write-up" alone', () => {
  deq(facetShown({ writeup: true }), ['syn-couloir', 'syn-traverse', 'syn-loop', 'syn-journal']);
  deq(facetShown({ writeup: false }), ALL_FCARDS);
  // only the page's own '1' says a card has one
  for (const v of ['0', '', 'true', 'yes', undefined]) {
    eq(TRX.facetOk({ act: 'ski', writeup: v }, withDefaults({ writeup: true })), false, 'writeup=' + JSON.stringify(v));
    eq(TRX.facetOk({ act: 'ski', writeup: v }, DEFAULTS), true, 'writeup=' + JSON.stringify(v) + ', filter off');
  }
  eq(TRX.facetOk({ act: 'ski', writeup: '1' }, withDefaults({ writeup: true })), true);
});
check('facetOk: two filters at once keep only the cards that pass both', () => {
  deq(facetShown({ activity: 'ski', year: '2026' }), ['syn-couloir', 'syn-lap']);
  deq(facetShown({ activity: 'ski', region: 'lake-tahoe' }), ['syn-lap']);
  deq(facetShown({ activity: 'hike', region: 'eastern-sierra' }), ['syn-loop']);
  deq(facetShown({ region: 'lake-tahoe', year: '2024' }), ['syn-crag']);
  deq(facetShown({ region: 'lake-tahoe', writeup: true }), []);                  // each alone finds cards, together none
  deq(facetShown({ region: 'eastern-sierra', writeup: true }), ['syn-couloir', 'syn-loop']);
  deq(facetShown({ format: 'trip', year: '2025' }), ['syn-loop', 'syn-ride']);
  deq(facetShown({ format: 'series', activity: 'ski' }), []);
  deq(facetShown({ year: '2025', writeup: true }), ['syn-traverse', 'syn-loop']);
  deq(facetShown({ activity: 'hike', writeup: true, format: 'trip' }), ['syn-loop']);
});
check('facetOk: all five filters together, and each one still decides', () => {
  const all = { activity: 'ski', region: 'eastern-sierra', year: '2026', format: 'trip', writeup: true };
  deq(facetShown(all), ['syn-couloir']);
  // the one card that passes four of the five filters must stay hidden by the fifth, whichever it is
  const others = { activity: 'hike', region: 'alps', year: '2025', format: 'multi-day' };
  for (const key of Object.keys(others)) {
    deq(facetShown(Object.assign({}, all, { [key]: others[key] })), [], 'with another ' + key);
  }
  const card = FCARDS[0];
  for (const key of ['act', 'region', 'year', 'kind', 'writeup']) {
    const off = Object.assign({}, card, { [key]: key === 'writeup' ? '0' : 'something-else' });
    eq(TRX.facetOk(off, withDefaults(all)), false, 'a card that differs only in data-' + key);
  }
  eq(TRX.facetOk(card, withDefaults(all)), true);
  // dropping one filter at a time only ever lets cards in
  for (const key of Object.keys(all)) {
    const fewer = Object.assign({}, all, { [key]: DEFAULTS[key] });
    assert.ok(facetShown(fewer).indexOf('syn-couloir') !== -1, 'without ' + key);
  }
});
check('facetOk: an empty data attribute matches no value of its filter', () => {
  const ride = FCARDS[6], undated = FCARDS[7];
  eq(ride.region, '');
  eq(undated.year, '');
  for (const region of FALLOWED.region.filter(Boolean)) eq(TRX.facetOk(ride, withDefaults({ region: region })), false, region);
  for (const year of FALLOWED.year.filter(Boolean)) eq(TRX.facetOk(undated, withDefaults({ year: year })), false, year);
  // the other filters still see the card
  eq(TRX.facetOk(ride, withDefaults({ activity: 'mtb', year: '2025', format: 'trip' })), true);
  eq(TRX.facetOk(undated, withDefaults({ activity: 'hike', region: 'lake-tahoe', format: 'trip' })), true);
});
check('facetOk: a card without data attributes passes only when no filter is set', () => {
  const bare = FCARDS[8];
  deq(Object.keys(bare), ['slug']);
  eq(TRX.facetOk(bare, DEFAULTS), true);
  for (const o of [{ activity: 'ski' }, { region: 'alps' }, { year: '2026' }, { format: 'trip' }, { writeup: true }]) {
    eq(TRX.facetOk(bare, withDefaults(o)), false, JSON.stringify(o));
  }
});
check('facetOk: a value is compared whole', () => {
  deq(facetShown({ region: 'lake' }), []);
  deq(facetShown({ region: 'sierra' }), []);
  deq(facetShown({ year: '202' }), []);
  deq(facetShown({ activity: 'sk' }), []);
  deq(facetShown({ format: 'multi' }), []);
});
check('facetOk: the search text, the order and the view are not filters', () => {
  deq(facetShown({ q: 'zermatt' }), ALL_FCARDS);            // the text is matched against the index, separately
  deq(facetShown({ sort: 'oldest' }), ALL_FCARDS);
  deq(facetShown({ sort: 'relevance', view: 'list' }), ALL_FCARDS);
  deq(facetShown({ q: 'zermatt', sort: 'oldest', view: 'list', region: 'alps' }), ['syn-traverse']);
});
check('facetOk: how many cards a state shows', () => {
  const table = [
    ['', 9],
    ['?activity=ski', 3],
    ['?activity=hike', 3],
    ['?region=lake-tahoe', 3],
    ['?region=eastern-sierra', 2],
    ['?year=2025', 3],
    ['?format=trip', 6],
    ['?writeup=1', 4],
    ['?activity=ski&region=lake-tahoe', 1],
    ['?activity=ski&writeup=1', 2],
    ['?region=alps&writeup=1', 1],
    ['?year=2024&format=series', 1],
    ['?activity=climb&writeup=1', 0],
    ['?activity=ski&region=eastern-sierra&year=2026&format=trip&writeup=1', 1],
    ['?q=couloir&sort=oldest&view=list', 9],
    ['?region=mars&year=1999', 9],            // values no control offers are reset by parseState, so nothing is filtered
  ];
  for (const [search, want] of table) {
    eq(FCARDS.filter((c) => TRX.facetOk(c, fst(search))).length, want, search || '(no query)');
  }
});
check('facetOk leaves the card and the state as it found them', () => {
  const state = withDefaults({ activity: 'ski', region: 'alps', writeup: true });
  const before = [JSON.stringify(FCARDS), JSON.stringify(state)];
  FCARDS.forEach((c) => TRX.facetOk(c, state));
  deq([JSON.stringify(FCARDS), JSON.stringify(state)], before);
});
check('facetOk and dayShown: a journal day follows its journal\'s card', () => {
  const journal = FCARDS[4], written = { s: 'syn-journal', x: 'synthetic words' }, bare = { s: 'syn-journal', x: '' };
  const shown = (e, o) => TRX.dayShown(e, TRX.facetOk(journal, withDefaults(o)), withDefaults(o).writeup);
  eq(shown(written, {}), true);
  eq(shown(written, { region: 'pacific-crest-trail', format: 'series', year: '2024' }), true);
  eq(shown(written, { region: 'alps' }), false);        // the journal's card is filtered out, and its days with it
  eq(shown(written, { activity: 'ski' }), false);
  eq(shown(bare, { writeup: true }), false);            // the card passes; this day has no write-up
  eq(shown(written, { writeup: true }), true);
});

// ---------------------------------------------------------------- the form as the script finds it (adoptForm, ownSort)

// The form is revealed at first paint and the script is deferred, so the visitor may have used it first. An untouched
// form: an empty box, every select on its first option, the write-up box unticked.
const UNTOUCHED = { q: '', region: '', year: '', format: '', sort: 'newest', writeup: false };
const formWith = (o) => Object.assign({}, UNTOUCHED, o);
const adopt = (search, form, traversal) => TRX.adoptForm(fst(search), form, traversal);

check('adoptForm and ownSort are exported', () => {
  eq(typeof TRX.adoptForm, 'function', 'TRX.adoptForm is not a function');
  eq(typeof TRX.ownSort, 'function', 'TRX.ownSort is not a function');
});
check('adoptForm: an untouched form adopts nothing', () => {
  deq(adopt('', UNTOUCHED), DEFAULTS);
  deq(adopt('', {}), DEFAULTS);                 // a page without the controls
  deq(adopt('', undefined), DEFAULTS);
  deq(adopt('', null), DEFAULTS);
  for (const search of ['?q=tallac', '?view=list', '?activity=ski&region=alps&year=2025&format=multi-day&writeup=1&sort=oldest&view=list']) {
    deq(adopt(search, UNTOUCHED), fst(search), search);
    deq(adopt(search, UNTOUCHED, true), fst(search), search + ' after Back');
  }
});
check('adoptForm: with no state in the URL, each select that is off its default is taken over', () => {
  deq(adopt('', formWith({ region: 'lake-tahoe' })), withDefaults({ region: 'lake-tahoe' }));
  deq(adopt('', formWith({ year: '2025' })), withDefaults({ year: '2025' }));
  deq(adopt('', formWith({ format: 'series' })), withDefaults({ format: 'series' }));
  deq(adopt('', formWith({ sort: 'oldest' })), withDefaults({ sort: 'oldest' }));
  deq(adopt('', formWith({ sort: 'relevance' })), withDefaults({ sort: 'relevance' }));
});
check('adoptForm: the ticked write-up box is taken over', () => {
  deq(adopt('', formWith({ writeup: true })), withDefaults({ writeup: true }));
  deq(adopt('', { writeup: true }), withDefaults({ writeup: true }));
  // only the checkbox's own true: the page passes chk.checked, nothing else ticks the filter
  for (const v of ['1', 'on', 'true', 1, 'false', null, undefined]) eq(adopt('', formWith({ writeup: v })).writeup, false, JSON.stringify(v));
});
check('adoptForm: several choices at once, the reported case among them', () => {
  deq(adopt('', formWith({ region: 'lake-tahoe', writeup: true })), withDefaults({ region: 'lake-tahoe', writeup: true }));
  deq(adopt('', formWith({ region: 'lake-tahoe', year: '2025', format: 'trip', writeup: true, sort: 'oldest' })),
      withDefaults({ region: 'lake-tahoe', year: '2025', format: 'trip', writeup: true, sort: 'oldest' }));
});
check('adoptForm: what is taken over filters and is written to the URL as a choice made later would be', () => {
  const state = adopt('', formWith({ region: 'lake-tahoe', year: '2024' }));
  deq(FCARDS.filter((c) => TRX.facetOk(c, state)).map((c) => c.slug), ['syn-crag']);
  eq(TRX.serialize(state), 'region=lake-tahoe&year=2024');
  eq(TRX.serialize(adopt('', formWith({ writeup: true, sort: 'oldest' }))), 'writeup=1&sort=oldest');
  eq(TRX.serialize(adopt('', UNTOUCHED)), '');
});
check('adoptForm: typed text is the search, best match first unless a sort was chosen', () => {
  deq(adopt('', formWith({ q: 'tallac' })), withDefaults({ q: 'tallac', sort: 'relevance' }));
  deq(adopt('', formWith({ q: 'tallac', sort: 'oldest' })), withDefaults({ q: 'tallac', sort: 'oldest' }));     // the visitor's own sort stays
  deq(adopt('', formWith({ q: 'tallac', sort: 'relevance' })), withDefaults({ q: 'tallac', sort: 'relevance' }));
  deq(adopt('?sort=oldest', formWith({ q: 'tallac' })), withDefaults({ q: 'tallac', sort: 'oldest' }));       // so does a sort in the URL
  deq(adopt('?activity=ski&view=list', formWith({ q: 'tallac' })), withDefaults({ activity: 'ski', view: 'list', q: 'tallac', sort: 'relevance' }));
  deq(adopt('', formWith({ q: '  !! ' })), withDefaults({ q: '  !! ' }));    // text that searches nothing is kept in the box and changes no order
  deq(adopt('', formWith({ q: 'tallac', region: 'lake-tahoe' })), withDefaults({ q: 'tallac', region: 'lake-tahoe', sort: 'relevance' }));
});
check('adoptForm: a URL with state wins over the form, key by key', () => {
  deq(adopt('?region=alps', formWith({ region: 'lake-tahoe' })), withDefaults({ region: 'alps' }));
  deq(adopt('?year=2026', formWith({ year: '2024' })), withDefaults({ year: '2026' }));
  deq(adopt('?format=series', formWith({ format: 'trip' })), withDefaults({ format: 'series' }));
  deq(adopt('?sort=oldest', formWith({ sort: 'relevance' })), withDefaults({ sort: 'oldest' }));
  deq(adopt('?writeup=1', formWith({ writeup: false })), withDefaults({ writeup: true }));
  deq(adopt('?q=whitney', formWith({ q: 'tallac' })), withDefaults({ q: 'whitney' }));     // and the URL's search keeps the URL's order
  const full = '?q=whitney&activity=hike&region=alps&year=2026&format=series&writeup=1&sort=oldest&view=list';
  deq(adopt(full, formWith({ q: 'tallac', region: 'lake-tahoe', year: '2024', format: 'trip', sort: 'relevance' })), fst(full));
});
check('adoptForm: a key the URL leaves alone is still taken from the form', () => {
  deq(adopt('?region=alps', formWith({ region: 'lake-tahoe', year: '2025', writeup: true })), withDefaults({ region: 'alps', year: '2025', writeup: true }));
  deq(adopt('?activity=ski&view=list', formWith({ format: 'trip' })), withDefaults({ activity: 'ski', view: 'list', format: 'trip' }));
  deq(adopt('?q=whitney', formWith({ q: 'tallac', sort: 'oldest' })), withDefaults({ q: 'whitney', sort: 'oldest' }));
});
check('adoptForm: after Back or Forward only the typed text is taken', () => {
  // the browser puts the selects and the box back to what it remembers, which need not be what the address says
  const form = formWith({ q: 'tallac', region: 'lake-tahoe', year: '2025', format: 'trip', writeup: true, sort: 'oldest' });
  deq(adopt('', form, true), withDefaults({ q: 'tallac', sort: 'relevance' }));
  deq(adopt('', formWith({ region: 'lake-tahoe', writeup: true }), true), DEFAULTS);
  deq(adopt('', formWith({ sort: 'oldest' }), true), DEFAULTS);
  deq(adopt('?region=alps', form, true), withDefaults({ region: 'alps', q: 'tallac', sort: 'relevance' }));
  deq(adopt('', form, false), withDefaults({ q: 'tallac', region: 'lake-tahoe', year: '2025', format: 'trip', writeup: true, sort: 'oldest' }));
  deq(adopt('', form), adopt('', form, false));         // not said: a first visit
});
check('adoptForm: the activity and the view have no control that holds a value, and are never read from the form', () => {
  deq(adopt('', formWith({ activity: 'ski', view: 'list' })), DEFAULTS);
  deq(adopt('?activity=hike', formWith({ activity: 'ski', view: 'list' })), withDefaults({ activity: 'hike' }));
});
check('adoptForm returns a new state of the eight keys and changes neither argument', () => {
  const state = fst('?activity=ski'), form = formWith({ q: 'tallac', region: 'lake-tahoe', writeup: true, extra: 'x' });
  const before = [JSON.stringify(state), JSON.stringify(form)];
  const out = TRX.adoptForm(state, form);
  assert.notStrictEqual(out, state);
  deq([JSON.stringify(state), JSON.stringify(form)], before);
  deq(Object.keys(out).sort(), Object.keys(DEFAULTS).sort());
  assert.notStrictEqual(TRX.adoptForm(state, UNTOUCHED), state);      // also when nothing is taken over
  for (const k of ['region', 'year', 'format', 'sort', 'q']) eq(typeof TRX.adoptForm(state, formWith({ region: 'alps' }))[k], 'string', k);
});
check('adoptForm: ownSort says whether the sort is the visitor\'s own', () => {
  eq(TRX.ownSort(fst(''), UNTOUCHED), false);
  eq(TRX.ownSort(fst(''), undefined), false);
  eq(TRX.ownSort(fst(''), {}), false);
  eq(TRX.ownSort(fst('?sort=oldest'), UNTOUCHED), true);                      // chosen or shared: in the URL
  eq(TRX.ownSort(fst('?sort=relevance'), UNTOUCHED), true);
  eq(TRX.ownSort(fst(''), formWith({ sort: 'oldest' })), true);              // chosen in the form before the script arrived
  eq(TRX.ownSort(fst(''), formWith({ sort: 'relevance' })), true);
  eq(TRX.ownSort(fst(''), formWith({ sort: 'oldest' }), true), false);       // after Back the select is the browser's doing
  eq(TRX.ownSort(fst('?sort=oldest'), formWith({ sort: 'oldest' }), true), true);
  eq(TRX.ownSort(fst(''), formWith({ q: 'tallac' })), false);                // best match for typed text is not a choice
  eq(TRX.ownSort(fst('?q=tallac'), formWith({ region: 'alps', writeup: true })), false);
});

// ---------------------------------------------------------------- a search index that did not load (stillFailed, mayLoad)

check('retry: stillFailed and mayLoad are exported', () => {
  eq(typeof TRX.stillFailed, 'function', 'TRX.stillFailed is not a function');
  eq(typeof TRX.mayLoad, 'function', 'TRX.mayLoad is not a function');
});
check('retry: a first search fetches; no words, a request under way or an index already here never do', () => {
  eq(TRX.mayLoad('idle', null, 'tallac'), true);
  for (const q of ['', '   ', ' !! ']) for (const s of ['idle', 'failed']) eq(TRX.mayLoad(s, null, q), false, s + ' ' + JSON.stringify(q));
  for (const s of ['loading', 'ready', 'none']) {
    eq(TRX.mayLoad(s, null, 'tallac'), false, s);
    eq(TRX.mayLoad(s, 'whitney', 'tallac'), false, s + ', after another query failed');
  }
});
check('retry: after a failure the same query does not ask again, any other one does', () => {
  eq(TRX.mayLoad('failed', 'tallac', 'tallac'), false);
  eq(TRX.mayLoad('failed', 'tallac', 'whitney'), true);
  eq(TRX.mayLoad('failed', 'tallac', 'tallac '), true);      // the box is compared as typed
  eq(TRX.mayLoad('failed', 'tallac', ''), false);            // nothing to search for
  eq(TRX.mayLoad('failed', null, 'tallac'), true);           // forgotten: the box was cleared or changed since
  eq(TRX.mayLoad('failed', '', 'tallac'), true);             // it failed after the box had been emptied
});
check('retry: stillFailed keeps the failed query only while the box still holds it', () => {
  eq(TRX.stillFailed('tallac', 'tallac'), 'tallac');
  eq(TRX.stillFailed('tallac', ''), null);
  eq(TRX.stillFailed('tallac', 'talla'), null);
  eq(TRX.stillFailed('tallac', 'tallac '), null);
  eq(TRX.stillFailed(null, 'tallac'), null);
  eq(TRX.stillFailed(null, ''), null);
});
// The page's ask(), which runs on every apply() (typing, a filter, a view switch, Back): forget the failed query when the
// box no longer holds it, then fetch if the search may. `online` decides how the request ends.
function visit() {
  const v = { state: 'idle', failedFor: null, requests: 0, online: false };
  v.ask = (q) => {
    v.failedFor = TRX.stillFailed(v.failedFor, q);
    if (TRX.mayLoad(v.state, v.failedFor, q)) {
      v.requests++;
      if (v.online) v.state = 'ready'; else { v.state = 'failed'; v.failedFor = q; }
    }
    return v.requests;
  };
  return v;
}
check('retry: the same words typed again after the box was cleared ask again', () => {
  const v = visit();
  eq(v.ask('tallac'), 1);            // offline: the request fails
  eq(v.ask(''), 1);                  // the box cleared
  v.online = true;
  eq(v.ask('tallac'), 2);            // the same word: asked again, and answered
  eq(v.state, 'ready');
  eq(v.ask('tallac'), 2);
  eq(v.ask('whitney'), 2);           // the index is here: never again
});
check('retry: the same words typed again after the box held something else ask again', () => {
  const v = visit();
  eq(v.ask('tallac'), 1);
  eq(v.ask('tallac x'), 2);          // a changed query has always retried
  eq(v.ask('tallac'), 3);            // and so does the first one, typed again
});
check('retry: no request while the failed query is still the one in the box', () => {
  const v = visit();
  eq(v.ask('tallac'), 1);
  for (let i = 0; i < 25; i++) eq(v.ask('tallac'), 1, 'apply() number ' + (i + 2));   // filters, view switches, re-renders
  // typing on while offline: one request per changed query, none for a repeat
  const w = visit();
  for (const q of ['t', 'ta', 'ta', 'tal', 'tal', 'tal', 'tall']) w.ask(q);
  eq(w.requests, 4);
});
console.log('trips_js_harness: ' + checks + ' checks passed');
