#!/usr/bin/env node
'use strict';
/* Unit tests for the pure functions of assets/js/pages/trips.js. Phase 2: norm, tokens, parseState, match, score,
   snippet, chipLabel. Phase 3: the journal-day search (dayHits, dayMeta, dayHref, dayText) and the wording decisions of
   the status line and the "Journal days" list (countText, daysCount, daysHead, daysListed, daysMoreText, failText).
   Phase 4: facetOk, the filter predicate the page hides and counts its cards with; adoptForm and ownSort, what the page
   takes over from a form the visitor used before the script arrived; stillFailed and mayLoad, when a search index that
   did not load is asked for again. Review gate: historyStep, what a change of view does to the browser's history, and
   clearedSort, the sort Clear all leaves; and, given a page model, the page part of trips.js itself, run whole against
   a stand-in for the browser (the "page:" checks at the end of this file). Round 3 of the gate: the page keeps what a
   history entry stands for and what it carries now in its own spelling, settles the entry on every deliberate change,
   on a year link and on Back, and never leaves Best match as the sort of no search (the scenario checks from
   "round 3" on). Round 4: Back or Forward onto an entry that carried Best match without a search (the visitor picked
   it in the Sort menu while the box was empty) rewrites that entry's address, its fragment kept, so the menu and the
   address agree; an entry whose sort needs no correction is not written to (the scenario checks from "round 4" on,
   which also read the order of the list). Round 6: historyStep is defined in assets/js/pages/explore.js, where the
   tick list takes it from too; trips.js takes it from there and still exports it, so the checks of it here stay as
   they were and one more says that TRX.historyStep is that very function (tests/ticklist_js_harness.js holds the
   rule's truth table against explore.js itself). The stand-in for the browser is tests/page_standin.js, shared with
   that harness.

   Run by tests/test_trips_js.py (skipped when node is missing); by hand:
   `node tests/trips_js_harness.js [trips.js [page-model.json [gap:<name>]]]`.
   - trips.js: another module with the same exports (used to prove the harness fails a wrong one).
   - page-model.json: a Trips page as tests/test_trips_js.py describes it (page_model); with it the whole script is
     run and the "page:" checks are added.
   - gap:<name>: also the check of that name, a case the page does not handle yet (GAPS: none at present, so any
     name is refused).
   Every failed assertion throws, so the process exits non-zero. norm() is checked against tests/norm_cases.json, the
   table tests/test_search.py holds search.normalize to, so the two sides of the search stay in step. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const standin = require('./page_standin.js');

const MODULE = path.resolve(process.argv[2] || path.join(__dirname, '..', 'assets', 'js', 'pages', 'trips.js'));
const CASES = path.join(__dirname, 'norm_cases.json');
// explore.js as the module itself asks for it under node: the file beside it (the site's own when the module is a
// wrapper kept somewhere else)
const BESIDE = path.join(path.dirname(MODULE), 'explore.js');
const EXPLORE_JS = fs.existsSync(BESIDE) ? BESIDE : path.join(__dirname, '..', 'assets', 'js', 'pages', 'explore.js');

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
  // synthetic text: no fixture quotes a real write-up
  const raw = 'Walked the synthetic ridge end to end in the fog. Overall a very solid outing with a test partner for the first time.';
  eq(TRX.snippet(raw, ['solid'], 3), '… Overall a very solid outing with a …');
  eq(TRX.snippet(raw, ['walked'], 2), 'Walked the synthetic …');
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
// ---------------------------------------------------------------- what a change of view does to the history (historyStep)

// historyStep(kind, entry, now, next, recent) -> { push, restore }. kind: 'type' (the pause after typing, and the write
// on load), 'pick' (a filter, the sort, the view, Clear all, a chip removed) or 'submit' (Enter in the search box).
// entry: the address this history entry stood for when the visitor settled on it; now: its address at this moment
// (typing rewrites it); next: the address of the new view; recent: an entry was made a moment ago.
const HOME = '/trips/', TYPED = '/trips/?q=tallac&sort=relevance', MORE = '/trips/?q=tallac+lake&sort=relevance';
const hstep = (kind, entry, now, next, recent) => {
  const s = TRX.historyStep(kind, entry, now, next, recent);
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

check('exports: the history helpers', () => {
  eq(typeof TRX.historyStep, 'function', 'TRX.historyStep is not a function');
  eq(typeof TRX.clearedSort, 'function', 'TRX.clearedSort is not a function');
  eq(TRX.historyStep.length, 5, 'historyStep(kind, entry, now, next, recent)');
  eq(TRX.clearedSort.length, 2, 'clearedSort(sort, userSort)');
  // round 6: the rule is explore.js's, shared with the tick list; trips.js hands on that very function, not a copy
  assert.strictEqual(TRX.historyStep, require(EXPLORE_JS).historyStep, 'TRX.historyStep is not Explore.historyStep itself');
});
check('historyStep: typing never adds an entry', () => {
  for (const name of Object.keys(SHAPES)) for (const recent of [false, true]) {
    deq(hstep('type', ...SHAPES[name], recent), [false, false], name + (recent ? ', an entry just made' : ''));
  }
});
check('historyStep: a pick adds one entry, unless one was made a moment ago', () => {
  for (const name of Object.keys(SHAPES)) {
    deq(hstep('pick', ...SHAPES[name], false), [true, false], name);       // also back to the view the entry stood for (Clear all)
    deq(hstep('pick', ...SHAPES[name], true), [false, false], name + ', an entry just made');
  }
});
check('historyStep: a submitted search adds an entry exactly when the view differs from the one the entry stood for', () => {
  for (const name of Object.keys(SHAPES)) {
    const [entry, now, next] = SHAPES[name];
    eq(hstep('submit', entry, now, next, false)[0], next !== entry, name);
  }
  eq(hstep('submit', HOME, HOME, TYPED, false)[0], true);       // Enter before the typing pause was over
  eq(hstep('submit', HOME, TYPED, TYPED, false)[0], true);      // Enter after it: the address already holds the words
  eq(hstep('submit', HOME, TYPED, MORE, false)[0], true);
});
check('historyStep: the entry is restored first exactly when typing had rewritten it', () => {
  for (const name of Object.keys(SHAPES)) {
    const [entry, now, next] = SHAPES[name];
    eq(hstep('submit', entry, now, next, false)[1], next !== entry && now !== entry, name);
  }
  deq(hstep('submit', HOME, TYPED, TYPED, false), [true, true]);
  deq(hstep('submit', HOME, TYPED, MORE, false), [true, true]);
  deq(hstep('submit', HOME, HOME, TYPED, false), [true, false]);          // nothing was rewritten: nothing to put back
  deq(hstep('submit', TYPED, MORE, MORE, false), [true, true]);           // a second search, typed over the first
  deq(hstep('submit', TYPED, TYPED, MORE, false), [true, false]);
});
check('historyStep: Enter again on the same view adds nothing', () => {
  deq(hstep('submit', HOME, HOME, HOME, false), [false, false]);          // an empty box, nothing typed
  deq(hstep('submit', TYPED, TYPED, TYPED, false), [false, false]);       // the search just submitted, Enter once more
  deq(hstep('submit', HOME, TYPED, HOME, false), [false, false]);         // typed, emptied again, Enter: the view the entry stood for
  for (const name of Object.keys(SHAPES)) deq(hstep('submit', ...SHAPES[name], true), [false, false], name + ', an entry just made');
});
check('historyStep: the entry is never restored without a new one being made', () => {
  for (const kind of KINDS) for (const name of Object.keys(SHAPES)) for (const recent of [false, true]) {
    const [push, restore] = hstep(kind, ...SHAPES[name], recent);
    assert.ok(push || !restore, [kind, name, recent].join(' / '));
    if (kind !== 'submit') eq(restore, false, [kind, name, recent].join(' / '));
  }
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
check('historyStep: addresses are compared whole', () => {
  deq(hstep('submit', '/trips/?q=talla', '/trips/?q=talla', '/trips/?q=tallac', false), [true, false]);
  deq(hstep('submit', '/trips/?q=tallac', '/trips/?q=tallac', '/trips/?q=tallac&view=list', false), [true, false]);
  deq(hstep('submit', '/trips/', '/trips/?q=a', '/trips/?q=a', false), [true, true]);
  deq(hstep('submit', '/trips/?q=a', '/trips/?q=a', '/trips/?q=a', false), [false, false]);
});
// The page's write(), on a history that is a list of addresses (what Back steps through). `entry` is what the current
// entry stood for when the visitor settled on it: a new entry, the load and Back set it. ms: the time of the write, for
// the 'an entry was made a moment ago' rule (600 ms, as the page has it).
function tab(start) {
  const t = { stack: [start], at: 0, entry: start, pushed: -Infinity, left: false };
  t.write = (kind, next, ms) => {
    const s = TRX.historyStep(kind, t.entry, t.stack[t.at], next, ms - t.pushed < 600);
    if (s.restore) t.stack[t.at] = t.entry;
    if (s.push) { t.stack.splice(t.at + 1, t.stack.length, next); t.at++; t.pushed = ms; t.entry = next; } else t.stack[t.at] = next;
    return t.stack.slice();
  };
  t.back = () => {
    if (t.at === 0) { t.left = true; return null; }      // nothing before the page's first entry: the visitor leaves it
    t.at--;
    t.entry = t.stack[t.at];
    return t.stack[t.at];
  };
  return t;
}
const FILTERED = '/trips/?q=tallac&activity=ski&sort=relevance';
check('historyStep: type, pause, Enter, Back returns to the list before the search', () => {
  const t = tab(HOME);
  deq(t.write('type', TYPED, 1000), [TYPED]);              // the pause wrote the words into the entry's address
  deq(t.write('submit', TYPED, 3000), [HOME, TYPED]);      // Enter: the entry is put back, and the search is a new one
  eq(t.back(), HOME);
  eq(t.left, false, 'Back left the page');
});
check('historyStep: type, Enter at once, Back returns to the list before the search', () => {
  const t = tab(HOME);
  deq(t.write('submit', TYPED, 1000), [HOME, TYPED]);      // the typing timer never fired
  eq(t.back(), HOME);
  eq(t.left, false);
});
check('historyStep: type, pause, pick a filter, Back returns to the typed search', () => {
  const t = tab(HOME);
  deq(t.write('type', TYPED, 1000), [TYPED]);
  deq(t.write('pick', FILTERED, 3000), [TYPED, FILTERED]);
  eq(t.back(), TYPED);
  eq(t.left, false);
});
check('historyStep: Enter twice makes one entry', () => {
  const t = tab(HOME);
  t.write('type', TYPED, 1000);
  deq(t.write('submit', TYPED, 3000), [HOME, TYPED]);
  deq(t.write('submit', TYPED, 5000), [HOME, TYPED]);      // long after: not the 'moment ago' rule, the same view
  deq(t.write('submit', TYPED, 5100), [HOME, TYPED]);
  eq(t.back(), HOME);
  eq(t.back(), null);
  eq(t.left, true);
});
check('historyStep: a second search typed over the first is one more entry, and Back goes through both', () => {
  const t = tab(HOME);
  t.write('submit', TYPED, 1000);
  deq(t.write('type', MORE, 3000), [HOME, MORE]);          // typing rewrites the entry of the first search
  deq(t.write('submit', MORE, 5000), [HOME, TYPED, MORE]);
  eq(t.back(), TYPED);
  eq(t.back(), HOME);
});
check('historyStep: typing alone, however long, leaves one entry', () => {
  const t = tab(HOME);
  let ms = 1000;
  for (const q of ['t', 'ta', 'tal', 'tall', 'talla', 'tallac']) deq(t.write('type', '/trips/?q=' + q + '&sort=relevance', ms += 1000).length, 1, q);
  eq(t.back(), null);                                       // as before: typing alone is not a step to come back to
  eq(t.left, true);
});
check('historyStep: several picks within a moment make one entry, later ones one each', () => {
  const t = tab(HOME);
  t.write('pick', '/trips/?activity=ski', 1000);
  t.write('pick', '/trips/?activity=climb', 1200);          // arrow keys through the activity chips
  deq(t.write('pick', '/trips/?activity=hike', 1400), [HOME, '/trips/?activity=hike']);
  deq(t.write('pick', '/trips/?activity=hike&view=list', 3000), [HOME, '/trips/?activity=hike', '/trips/?activity=hike&view=list']);
});

// ---------------------------------------------------------------- the sort Clear all leaves (clearedSort)

check('clearedSort: the visitor\'s own sort stays, and stays their choice', () => {
  deq(TRX.clearedSort('oldest', true), ['oldest', true]);
  deq(TRX.clearedSort('newest', true), ['newest', true]);       // Newest first, chosen in the menu, is a choice too
});
check('clearedSort: Best match never stays, chosen or not', () => {
  deq(TRX.clearedSort('relevance', true), ['newest', false]);
  deq(TRX.clearedSort('relevance', false), ['newest', false]);
  eq(TRX.clearedSort('relevance', true)[0], TRX.DEFAULTS.sort);
});
check('clearedSort: an automatic sort resets', () => {
  for (const sort of ['newest', 'oldest', 'relevance']) deq(TRX.clearedSort(sort, false), [TRX.DEFAULTS.sort, false], sort);
  for (const own of [0, '', null, undefined]) deq(TRX.clearedSort('oldest', own), ['newest', false], JSON.stringify(own));
});
check('clearedSort returns a new [sort, still the visitor\'s] pair each time', () => {
  for (const sort of ['newest', 'oldest', 'relevance']) for (const own of [true, false]) {
    const out = TRX.clearedSort(sort, own);
    assert.ok(Array.isArray(out));
    eq(out.length, 2);
    eq(typeof out[0], 'string');
    eq(typeof out[1], 'boolean');
    assert.notStrictEqual(out, TRX.clearedSort(sort, own));
    eq(out[1], own && sort !== 'relevance', sort + ' / ' + own);
    assert.notStrictEqual(out[0], 'relevance', 'Best match is left as the sort of no search');
  }
});

// ---------------------------------------------------------------- the page part, on a stand-in for the browser

/* What the pure helpers cannot show: that the page's own lines hand them the right things at the right moments.
   tests/test_trips_js.py passes a model of a Trips page that sitegen.pages.trips generated from a synthetic site
   (page_model): the page's address, its <body> as a tree of elements and text, and its search index. load() opens it
   in the stand-in for the browser of tests/page_standin.js (shared with tests/ticklist_js_harness.js; its header says
   what it models: a history that is a list of addresses spelled as the URL Standard spells them, a location, timers
   and a clock, popstate and hashchange as browsers send them, a history that can refuse writes), which runs explore.js
   and then the whole of trips.js against it (the order the bundle has them). To what every visitor does there (the
   pause, Back, Forward) load() adds the Trips page's own: typing, Enter, a filter, Clear all, a year link (a link of
   the page to one of its own fragments), and what is read back of the page. order() is the list as it is read, top to
   bottom.

   Without the model these checks are skipped. With 'gap:<name>' as a third argument the check of that name is run
   after them: a case in which the page does not yet do what its history rule says (GAPS, at the end of this file;
   it is empty at present). */
const MODEL = process.argv[3] ? JSON.parse(fs.readFileSync(path.resolve(process.argv[3]), 'utf8')) : null;
const ONLY = process.argv[4] || '';
const SOURCE = MODEL ? fs.readFileSync(MODULE, 'utf8') : '';
const EXPLORE = MODEL ? fs.readFileSync(EXPLORE_JS, 'utf8') : '';

function load(opts) {
  const tab = standin.open(MODEL, [['explore.js', EXPLORE], [MODULE, SOURCE]], opts);
  const body = tab.body, byId = tab.byId, one = tab.one, press = tab.press, fire = tab.fire;
  const form = byId('search'), q = byId('trx-q');
  const page = Object.assign(tab.visitor, {
    // ---- what the visitor does on the Trips page
    type: (text) => { q.value = text; fire(q, 'input'); },                        // the keys; the typing pause has not passed yet
    enter: () => { eq(fire(form, 'submit').defaultPrevented, true, 'Enter sent the form to the server'); },
    activity: (value) => { press(one(form, '.trx-acts [data-filter="' + value + '"]', 'the activity ' + value)); },
    view: (value) => { press(one(form, '.trx-view [data-view="' + value + '"]', 'the view ' + value)); },
    choose: (name, value) => {
      const sel = one(form, 'select[name="' + name + '"]', 'the ' + name + ' menu');
      assert.ok(sel.options.some((o) => o.value === value), 'the ' + name + ' menu has no option ' + value);
      sel.value = value;
      fire(sel, 'change');
    },
    writeup: (on) => { const box = one(form, 'input[name="writeup"]', 'the write-up box'); box.checked = on; fire(box, 'change'); },
    clearAll: () => { const b = byId('trx-clear'); eq(b.hidden, false, 'Clear all is not on screen'); press(b); },
    clearFilters: () => {                                 // the button of the 'No trips match' message
      eq(byId('trx-none').hidden, false, 'the empty state is not on screen');
      press(one(byId('trx-none'), '[data-clear]', 'the Clear filters button'));
    },
    removeChip: (label) => {
      const hits = byId('trx-chips').querySelectorAll('button').filter((b) => b.textContent === label);
      eq(hits.length, 1, 'the chips are ' + JSON.stringify(page.chips()));
      press(hits[0]);
    },
    // a year of the browse row ('2025'): the link to that year's heading, which must be on the page
    year: (value) => {
      assert.ok(byId('y-' + value), 'the page has no heading for the year ' + value);
      tab.follow(one(body, '.trx-browse [href="#y-' + value + '"]', 'the link to the year ' + value));
    },
    // ---- what the visitor sees of the page
    box: () => q.value,
    sort: () => one(form, 'select[name="sort"]', 'the sort menu').value,
    chosen: () => one(form, '.trx-acts [aria-checked="true"]', 'the checked activity').dataset.filter,
    chips: () => byId('trx-chips').querySelectorAll('button').map((b) => b.textContent),
    shown: () => byId('trx-results').querySelectorAll('.tcard').filter((c) => !c.hidden).map((c) => c.dataset.slug).sort(),
    // the reports on screen in the order they are listed, top to bottom: a card counts when neither it nor a list or a
    // section around it is hidden (the year groups, or the one list of 'Oldest first' and 'Best match first')
    order: () => {
      const results = byId('trx-results');
      const onScreen = (el) => { for (let p = el; p && p !== results; p = p.parentNode) if (p.hidden) return false; return true; };
      return results.querySelectorAll('.tcard').filter(onScreen).map((c) => c.dataset.slug);
    },
  });
  return page;
}

if (MODEL) {
  const SEARCHED = '?q=ridge&sort=relevance';        // the address of a search for 'ridge', best match first
  const ALL = MODEL.slugs.slice().sort(), RIDGE = MODEL.found.ridge.slice().sort();
  // the visitor has typed a search, waited and pressed Enter: the page's first entry and the search's
  const searched = (opts) => {
    const page = load(opts);
    page.type('ridge');
    page.pause();
    page.enter();
    deq(page.stack(), ['', SEARCHED]);
    page.pause();
    return page;
  };
  const YEAR = '#y-' + MODEL.year;                     // the fragment of a year link of the browse row
  // the history as the Back button has it: every entry of the page, the one the visitor is on, and its address
  const where = (page) => [page.stack(), page.at(), page.address()];
  // Type a search (no Enter), follow a year link, Enter, then Back three times. opts: the browser (load)
  const typedThenYear = (opts) => {
    const there = SEARCHED + YEAR;
    const page = load(opts);
    page.type('ridge');
    page.pause();
    deq(where(page), [[SEARCHED], 0, SEARCHED]);            // typing rewrote the page's one entry
    page.year(MODEL.year);
    deq(where(page), [[SEARCHED, there], 1, there]);        // the browser's own entry, for the view on screen
    deq([page.box(), page.shown(), page.pushes()], ['ridge', RIDGE, 0]);
    page.pause();
    page.enter();
    // the search is the view this entry stands for: Enter adds no entry and turns none into another view (the fragment
    // goes, as on every write after the load)
    deq(where(page), [[SEARCHED, SEARCHED], 1, SEARCHED], 'the entry the year link made did not keep the typed search');
    deq([page.pushes(), page.calls().slice(-1)], [0, ['replace ' + SEARCHED]]);
    page.back();
    deq(where(page), [[SEARCHED, SEARCHED], 0, SEARCHED]);
    deq([page.box(), page.sort(), page.shown(), page.left()], ['ridge', 'relevance', RIDGE, false]);
    page.back();                                            // the list before the typing was never an entry of its own
    deq([where(page), page.left()], [[[SEARCHED, SEARCHED], 0, SEARCHED], true]);
    page.back();
    deq([where(page), page.left()], [[[SEARCHED, SEARCHED], 0, SEARCHED], true]);
    // the same with an apostrophe in the words: the entry is settled on the page's spelling of them, not the browser's
    const quoted = '?q=lover%27s&sort=relevance';
    const other = load(opts);
    other.type("lover's");
    other.pause();
    other.year(MODEL.year);
    deq(where(other), [[quoted, quoted + YEAR], 1, quoted + YEAR]);
    other.pause();
    other.enter();
    deq(where(other), [[quoted, quoted], 1, quoted]);
    eq(other.pushes(), 0);
    // typed but not yet written when the link is followed: the link's entry stands for the list that was on screen, and
    // the search submitted there is a new view
    const quick = load(opts);
    quick.type('ridge');
    quick.year(MODEL.year);
    deq(where(quick), [['', YEAR], 1, YEAR]);
    quick.pause();
    deq(where(quick), [['', SEARCHED], 1, SEARCHED]);
    quick.enter();
    deq(where(quick), [['', '', SEARCHED], 2, SEARCHED]);
    quick.back();
    deq(where(quick), [['', '', SEARCHED], 1, '']);
    deq([quick.box(), quick.shown(), quick.left()], ['', ALL, false]);
  };
  // ---- round 4. The order of the list: the page lists its reports newest first (MODEL.slugs, as it was generated);
  // Oldest first is that order turned round, the fixture's dates being all different; Best match first is by
  // TRX.score, the newer report first among equals (the page's own rule, with the score the checks above hold).
  const CARDS = [];                                    // the attributes of every card of the page, in page order
  (function walk(node) {
    if (typeof node === 'string') return;
    if ((' ' + (node.attrs.class || '') + ' ').indexOf(' tcard ') !== -1) CARDS.push(node.attrs);
    node.children.forEach(walk);
  })(MODEL.body);
  const NEWEST = MODEL.slugs.slice(), OLDEST = MODEL.slugs.slice().reverse();
  const INDEX = MODEL.indexes['search.json'];
  const finds = (q) => NEWEST.filter((slug) => INDEX.some((e) => e.s === slug && TRX.match(e, TRX.tokens(q))));
  const bestFirst = (q) => {
    const points = {};
    INDEX.forEach((e) => { points[e.s] = TRX.score(e, TRX.tokens(q)); });
    return finds(q).sort((a, b) => points[b] - points[a] || NEWEST.indexOf(a) - NEWEST.indexOf(b));
  };
  const SKI = CARDS.filter((c) => c['data-act'] === 'ski').map((c) => c['data-slug']);       // the Ski filter, newest first
  const RIDGE_BEST = bestFirst('ridge');
  const WORD = 'synthetic';                            // a search the three sorts list in three different orders
  // BEST: the address Best match gets when it is picked in the Sort menu while the search box is empty; SKIING_BEST:
  // an activity picked after it; SKIING: the same view at the address it has once the sort is put right
  const BEST = '?sort=relevance', SKIING = '?activity=ski', SKIING_BEST = '?activity=ski&sort=relevance';
  // what a step can change that the visitor sees of the history and of the order: every entry of the page, the one the
  // visitor is on, its address, the Sort menu, and the reports in the order they are listed
  const seen = (page) => [page.stack(), page.at(), page.address(), page.sort(), page.order()];
  // the visitor picked Best match with an empty box, then (the moment over) an activity, and came Back: the entry of
  // the pick has been rewritten to the plain address
  const rewritten = (opts) => {
    const page = load(opts);
    page.pause();
    page.choose('sort', 'relevance');
    deq(seen(page), [['', BEST], 1, BEST, 'relevance', NEWEST]);
    page.pause();
    page.activity('ski');
    deq(seen(page), [['', BEST, SKIING_BEST], 2, SKIING_BEST, 'relevance', SKI]);
    page.pause();
    page.back();
    deq(seen(page), [['', '', SKIING_BEST], 1, '', 'newest', NEWEST]);
    page.pause();
    return page;
  };
  const pageChecks = {
    'the model is the page the script expects': () => {
      const page = load();
      deq(page.shown(), ALL);
      assert.ok(RIDGE.length > 0 && RIDGE.length < ALL.length, 'the fixture search must find some reports and not all');
      eq(page.box(), '');
      eq(page.sort(), 'newest');
      eq(page.chosen(), 'all');
      deq(page.chips(), []);
      // what the round-3 checks press: three activities besides All, and a link of the browse row to a year
      eq(MODEL.activities[0], 'all');
      assert.ok(MODEL.activities.length >= 4, 'the fixture needs three activities besides All');
      page.year(MODEL.year);
      deq([page.stack(), page.at(), page.pushes()], [['', '#y-' + MODEL.year], 1, 0]);
      page.year(MODEL.year);                                // the address already ends with it: no second entry
      deq([page.stack(), page.at()], [['', '#y-' + MODEL.year], 1]);
      page.back();
      deq([page.stack(), page.at(), page.address(), page.left()], [['', '#y-' + MODEL.year], 0, '', false]);
    },
    'the load rewrites its own entry and adds none': () => {
      const page = load();
      deq(page.stack(), ['']);
      deq(page.calls(), ['replace ']);
      eq(page.left(), false);
      // an address with a view in it, spelled its own way, becomes the canonical one, in the same entry
      const shared = load({ search: '?view=list&utm=x&activity=ski' });
      deq(shared.stack(), ['?activity=ski&view=list']);
      deq(shared.calls(), ['replace ?activity=ski&view=list']);
      eq(shared.chosen(), 'ski');
      // and that canonical address is what the entry stands for from then on: Enter on it is no change of view
      shared.pause();
      shared.enter();
      deq([shared.stack(), shared.pushes()], [['?activity=ski&view=list'], 0], 'the entry still stood for the address as it was typed');
      // the fragment is kept on that first write (the header's Search link, a year link)
      deq(load({ hash: '#y-2025' }).stack(), ['#y-2025']);
      deq(load({ search: '?activity=ski', hash: '#search' }).stack(), ['?activity=ski#search']);
    },
    'typing rewrites the entry after the pause, and never adds one': () => {
      const page = load();
      page.type('ri');
      deq(page.stack(), [''], 'the address changed before the typing pause was over');
      page.pause(100);
      deq(page.stack(), ['']);
      page.type('ridge');                                   // typed on within the pause: one write, for the whole word
      page.pause(149);
      deq(page.stack(), ['']);
      page.pause(1);
      deq(page.stack(), [SEARCHED]);
      deq(page.shown(), RIDGE);
      for (const text of ['ridge w', 'ridge wa', 'ridge', 'r', '']) {
        page.type(text);
        page.pause();
        eq(page.stack().length, 1, JSON.stringify(text));
      }
      deq(page.stack(), ['']);
      eq(page.pushes(), 0);
      page.back();
      eq(page.left(), true, 'typing alone made a step to come back to');
    },
    'load, type, pause, Enter, Back': () => {
      const page = load();
      deq([page.stack(), page.at(), page.address()], [[''], 0, '']);
      page.type('ridge');
      deq([page.stack(), page.at(), page.address()], [[''], 0, '']);
      page.pause();
      deq([page.stack(), page.at(), page.address()], [[SEARCHED], 0, SEARCHED]);        // the pause wrote the words into the entry
      page.enter();
      deq([page.stack(), page.at(), page.address()], [['', SEARCHED], 1, SEARCHED]);    // the entry is put back; the search is a new one
      deq(page.calls().slice(-2), ['replace ', 'push ' + SEARCHED], 'the entry is restored before the new one is made');
      deq(page.shown(), RIDGE);
      page.back();
      eq(page.left(), false, 'Back left the Trips page instead of returning to the list before the search');
      deq([page.stack(), page.at(), page.address()], [['', SEARCHED], 0, '']);
      deq([page.box(), page.sort(), page.shown()], ['', 'newest', ALL]);
      page.forward();
      deq([page.stack(), page.at(), page.address()], [['', SEARCHED], 1, SEARCHED]);
      deq([page.box(), page.sort(), page.shown()], ['ridge', 'relevance', RIDGE]);
    },
    'load, type, Enter at once, Back': () => {
      const page = load();
      page.type('ridge');
      page.enter();                                         // before the typing pause is over
      deq([page.stack(), page.at(), page.address()], [['', SEARCHED], 1, SEARCHED]);
      deq(page.calls(), ['replace ', 'push ' + SEARCHED]);  // nothing to put back: the entry was never rewritten
      page.pause();                                         // the typing timer was cancelled: no late write
      deq(page.calls(), ['replace ', 'push ' + SEARCHED]);
      page.back();
      eq(page.left(), false);
      deq([page.stack(), page.at(), page.address()], [['', SEARCHED], 0, '']);
      deq([page.box(), page.shown()], ['', ALL]);
    },
    'load, type, pause, pick a filter, Back': () => {
      const page = load();
      page.type('ridge');
      page.pause();
      deq([page.stack(), page.at(), page.address()], [[SEARCHED], 0, SEARCHED]);
      page.activity('ski');
      const filtered = '?q=ridge&activity=ski&sort=relevance';
      deq([page.stack(), page.at(), page.address()], [[SEARCHED, filtered], 1, filtered]);   // a pick makes an entry, as before
      deq(page.calls().slice(-1), ['push ' + filtered]);
      page.back();
      eq(page.left(), false);
      deq([page.stack(), page.at(), page.address()], [[SEARCHED, filtered], 0, SEARCHED]);
      deq([page.box(), page.chosen(), page.shown()], ['ridge', 'all', RIDGE]);
    },
    'after typing, every control and Clear all make their entry on top of the typed one': () => {
      // [what is pressed, the address it gives]; the typed search stays the entry below it, as before the fix
      const controls = [
        [(page) => page.activity('ski'), '?q=ridge&activity=ski&sort=relevance'],
        [(page) => page.choose('region', MODEL.region), '?q=ridge&region=' + MODEL.region + '&sort=relevance'],
        [(page) => page.choose('year', MODEL.year), '?q=ridge&year=' + MODEL.year + '&sort=relevance'],
        [(page) => page.choose('format', 'trip'), '?q=ridge&format=trip&sort=relevance'],
        [(page) => page.choose('sort', 'oldest'), '?q=ridge&sort=oldest'],
        [(page) => page.writeup(true), '?q=ridge&writeup=1&sort=relevance'],
        [(page) => page.view('list'), '?q=ridge&sort=relevance&view=list'],
        [(page) => page.clearAll(), ''],
        [(page) => page.removeChip('Search: ridge'), ''],
      ];
      for (const [act, address] of controls) {
        const page = load();
        page.type('ridge');
        page.pause();
        act(page);
        deq([page.stack(), page.at(), page.address()], [[SEARCHED, address], 1, address], address || 'cleared');
        deq(page.calls().slice(-1), ['push ' + address]);
        deq(page.calls().filter((c) => c === 'replace '), ['replace '], 'the typed entry was put back: ' + (address || 'cleared'));
        page.back();
        deq([page.address(), page.box(), page.left()], [SEARCHED, 'ridge', false], address || 'cleared');
      }
      // the empty state's own button is Clear all too
      const page = load();
      page.type('zzzz');
      page.pause();
      deq([page.stack(), page.shown()], [['?q=zzzz&sort=relevance'], []]);
      page.clearFilters();
      deq([page.stack(), page.at(), page.box(), page.shown()], [['?q=zzzz&sort=relevance', ''], 1, '', ALL]);
    },
    'Enter twice': () => {
      const page = load();
      page.type('ridge');
      page.pause();
      page.enter();
      deq([page.stack(), page.at()], [['', SEARCHED], 1]);
      page.enter();                                         // at once
      deq([page.stack(), page.at()], [['', SEARCHED], 1]);
      page.pause();
      page.enter();                                         // and long after: the same view, so no entry
      page.pause();
      page.enter();
      deq([page.stack(), page.at(), page.address()], [['', SEARCHED], 1, SEARCHED]);
      eq(page.pushes(), 1);
      page.back();
      deq([page.at(), page.address(), page.left()], [0, '', false]);
      page.back();
      eq(page.left(), true);
      // Enter in a box nothing was typed in changes nothing either
      const idle = load();
      idle.pause();
      idle.enter();
      idle.pause();
      idle.enter();
      deq([idle.stack(), idle.pushes()], [[''], 0]);
    },
    'a second search typed over the first is one more entry': () => {
      const page = searched();
      const more = '?q=ridge+walk&sort=relevance';
      page.type('ridge walk');
      page.pause();
      deq([page.stack(), page.at()], [['', more], 1]);      // typing rewrites the entry of the first search
      page.enter();
      deq([page.stack(), page.at()], [['', SEARCHED, more], 2]);
      page.back();
      deq([page.address(), page.box()], [SEARCHED, 'ridge']);
      page.back();
      deq([page.address(), page.box(), page.left()], ['', '', false]);
    },
    'typed and emptied again, Enter adds nothing': () => {
      const page = load();
      page.type('ridge');
      page.pause();
      page.type('');
      page.enter();                                         // the view the entry stood for: no entry, and the address says so again
      deq([page.stack(), page.pushes()], [[''], 0]);
    },
    'Back to an entry, then a search from there': () => {
      const page = searched();
      page.back();
      deq([page.at(), page.address()], [0, '']);
      page.enter();                                         // the entry the visitor came back to stands for what it shows
      deq([page.stack(), page.at()], [['', SEARCHED], 0]);
      page.type('loop');
      page.pause();
      page.enter();
      const loop = '?q=loop&sort=relevance';
      deq([page.stack(), page.at(), page.address()], [['', loop], 1, loop]);     // the entries Forward led to are gone
      page.back();
      deq([page.address(), page.box(), page.left()], ['', '', false]);
      // and forward to the search again: Enter there adds nothing, a new search is one entry after it
      const again = searched();
      again.back();
      again.forward();
      again.pause();
      again.enter();
      deq([again.stack(), again.at()], [['', SEARCHED], 1]);
      again.type('loop');
      again.pause();
      again.enter();
      deq([again.stack(), again.at()], [['', SEARCHED, loop], 2]);
    },
    'a filter, the sort, the view and the write-up box each add an entry': () => {
      const page = load();
      const want = [''];
      const steps = [
        [() => page.activity('ski'), '?activity=ski'],
        [() => page.choose('year', MODEL.year), '?activity=ski&year=' + MODEL.year],
        [() => page.choose('sort', 'oldest'), '?activity=ski&year=' + MODEL.year + '&sort=oldest'],
        [() => page.view('list'), '?activity=ski&year=' + MODEL.year + '&sort=oldest&view=list'],
        [() => page.writeup(true), '?activity=ski&year=' + MODEL.year + '&writeup=1&sort=oldest&view=list'],
        [() => page.clearAll(), '?sort=oldest&view=list'],          // Clear all: the filters go, the visitor's own sort and the view stay
      ];
      for (const [act, address] of steps) {
        page.pause();
        act();
        want.push(address);
        deq([page.stack(), page.at()], [want, want.length - 1], address);
      }
      eq(page.pushes(), steps.length);
      // the same choice pressed again is not a change of view
      page.pause();
      page.view('list');
      eq(page.pushes(), steps.length);
    },
    'picks within a moment make one entry': () => {
      const page = load();
      page.pause();
      page.activity('ski');                                 // arrow keys through the activity chips: a press per step
      page.pause(100);
      page.activity('hike');
      page.pause(100);
      page.activity('ski');
      deq([page.stack(), page.at(), page.chosen()], [['', '?activity=ski'], 1, 'ski']);
      page.pause(700);
      page.activity('hike');
      deq([page.stack(), page.at()], [['', '?activity=ski', '?activity=hike'], 2]);
      // the moment is 600 ms, counted from the entry that was made: at 599 the next pick still rewrites it, at 600 it
      // makes its own
      page.pause(599);
      page.view('list');
      deq(page.stack(), ['', '?activity=ski', '?activity=hike&view=list']);
      page.pause(1);
      page.view('cards');
      deq(page.stack(), ['', '?activity=ski', '?activity=hike&view=list', '?activity=hike']);
    },
    'Clear all after a search leaves Newest first, never Best match': () => {
      // the automatic sort of a search
      let page = searched();
      eq(page.sort(), 'relevance');
      page.clearAll();
      deq([page.stack(), page.at(), page.sort(), page.box(), page.shown()], [['', SEARCHED, ''], 2, 'newest', '', ALL]);
      // Best match that counts as the visitor's own: chosen in the menu, or come back to with Back
      page = load();
      page.pause();
      page.choose('sort', 'relevance');
      page.type('ridge');
      page.pause();
      page.enter();
      page.pause();
      page.clearAll();
      deq([page.address(), page.sort()], ['', 'newest'], 'Best match was left as the sort of no search');
      page = load({ search: SEARCHED });
      page.pause();
      page.clearAll();
      deq([page.stack(), page.sort()], [[SEARCHED, ''], 'newest']);
      // once reset it is automatic again: the next search is best match first, and emptying the box goes back to newest
      page.type('loop');
      page.pause();
      deq([page.address(), page.sort()], ['?q=loop&sort=relevance', 'relevance']);
      page.type('');
      page.pause();
      deq([page.address(), page.sort()], ['', 'newest']);
    },
    'Clear all keeps a sort the visitor chose': () => {
      const page = load();
      page.pause();
      page.choose('sort', 'oldest');
      page.type('ridge');
      page.pause();
      page.enter();
      page.pause();
      eq(page.address(), '?q=ridge&sort=oldest');
      page.clearAll();
      deq([page.address(), page.sort()], ['?sort=oldest', 'oldest']);
      page.type('loop');                                    // and it is still theirs: a new search does not take it over
      page.pause();
      deq([page.address(), page.sort()], ['?q=loop&sort=oldest', 'oldest']);
    },
    'removing the search chip clears the sort as Clear all does, and adds an entry': () => {
      let page = load({ search: '?q=ridge&activity=ski&sort=relevance' });
      page.pause();
      deq(page.chips(), ['Search: ridge', MODEL.skiLabel]);
      page.removeChip('Search: ridge');
      deq([page.stack(), page.sort(), page.box(), page.chosen()], [['?q=ridge&activity=ski&sort=relevance', '?activity=ski'], 'newest', '', 'ski']);
      page.type('loop');                                    // the sort is automatic again: the next search is best match first
      page.pause();
      deq([page.address(), page.sort()], ['?q=loop&activity=ski&sort=relevance', 'relevance']);
      // another chip leaves the search and its order alone
      page = load({ search: '?q=ridge&activity=ski&sort=relevance' });
      page.pause();
      page.removeChip(MODEL.skiLabel);
      deq([page.stack(), page.sort(), page.box()], [['?q=ridge&activity=ski&sort=relevance', SEARCHED], 'relevance', 'ridge']);
      // a chosen sort stays when the search chip goes
      page = load({ search: '?q=ridge&sort=oldest' });
      page.pause();
      page.removeChip('Search: ridge');
      deq([page.address(), page.sort()], ['?sort=oldest', 'oldest']);
    },
    // ---- round 3 of the gate. The page keeps what an entry stands for, and what it carries now, in its own spelling;
    // every deliberate change, a year link and Back settle the entry; Best match is never the sort of no search. The
    // first two checks are the cases round 2 kept as known gaps, as they were written then. In the others where(page)
    // is read after every step that can write to the history: every entry, the one the visitor is on, and its address.
    'Enter again on a search with an apostrophe adds no entry': () => {
      // the browser spells the apostrophe %27 where the page writes "'": two spellings of one view
      const page = load();
      page.type("lover's");
      page.pause();
      page.enter();
      const address = '?q=lover%27s&sort=relevance';
      deq([page.stack(), page.at()], [['', address], 1]);
      page.pause();
      page.enter();
      deq([page.stack(), page.at()], [['', address], 1], 'Enter on the same view added an entry');
    },
    'a search after picks made within a moment goes back to the last of them': () => {
      // picks within a moment of an entry rewrite it (arrow keys through the activity chips), and the last of them is
      // what the entry stands for: a search submitted afterwards puts that one back, not the first
      const page = load();
      page.pause();
      page.activity('ski');
      page.pause(100);
      page.activity('hike');                                // within the moment: the same entry, now for hiking
      deq(page.stack(), ['', '?activity=hike']);
      page.pause();
      page.type('ridge');
      page.pause();
      page.enter();
      const address = '?q=ridge&activity=hike&sort=relevance';
      deq([page.stack(), page.at()], [['', '?activity=hike', address], 2], 'Back would not return to the view from before the search');
      page.back();
      deq([page.address(), page.chosen()], ['?activity=hike', 'hike']);
    },
    'a search with an apostrophe, a space, + & % # or an accent: type, pause, Enter three times is one new entry': () => {
      // [the words typed, the address bar's spelling of them]. The page writes them its own way (encodeURIComponent, a
      // space as +); of these characters the browser respells the straight apostrophe alone
      const SPELLED = [
        ["lover's", 'lover%27s'], ['l’ete', 'l%E2%80%99ete'], ['ridge walk', 'ridge+walk'], ['a+b', 'a%2Bb'], ['r&r', 'r%26r'],
        ['50% off', '50%25+off'], ['#1 ridge', '%231+ridge'], ['crête', 'cr%C3%AAte'],
        ["lover's l’été a+b & 50% #1 crête", 'lover%27s+l%E2%80%99%C3%A9t%C3%A9+a%2Bb+%26+50%25+%231+cr%C3%AAte'],
      ];
      for (const [typed, spelled] of SPELLED) {
        const address = '?q=' + spelled + '&sort=relevance';
        const page = load();
        deq(where(page), [[''], 0, ''], typed);
        page.type(typed);
        deq(where(page), [[''], 0, ''], typed);
        page.pause();
        deq(where(page), [[address], 0, address], typed);             // the pause wrote the words into the entry
        page.enter();
        deq(where(page), [['', address], 1, address], typed);         // one new entry, the list before the search under it
        page.enter();                                                 // at once
        deq(where(page), [['', address], 1, address], typed);
        page.pause();
        page.enter();                                                 // and long after, when no entry was 'made a moment ago'
        deq(where(page), [['', address], 1, address], 'Enter on the same view added an entry: ' + typed);
        eq(page.pushes(), 1, typed);
        page.back();
        deq(where(page), [['', address], 0, ''], typed);
        deq([page.box(), page.sort(), page.shown(), page.left()], ['', 'newest', ALL, false], typed);
        // Forward: the words are in the box as they were typed, and the entry stands for them
        page.forward();
        deq(where(page), [['', address], 1, address], typed);
        deq([page.box(), page.sort()], [typed, 'relevance']);
        page.pause();
        page.enter();
        deq(where(page), [['', address], 1, address], 'Enter after Forward added an entry: ' + typed);
        eq(page.pushes(), 1, typed);
        // a second search, Enter before the typing pause is over: nothing had been rewritten, so nothing is put back
        const calls = page.calls().length;
        const longer = '?q=' + spelled + '+x&sort=relevance';
        page.type(typed + ' x');
        deq(where(page), [['', address], 1, address], typed);
        page.enter();
        deq(where(page), [['', address, longer], 2, longer], typed);
        deq(page.calls().slice(calls), ['push ' + longer], typed);
        // and the address opened directly (a shared link, a reload) is the view its entry stands for
        const opened = load({ search: address });
        deq(where(opened), [[address], 0, address], typed);
        opened.pause();
        opened.enter();
        deq(where(opened), [[address], 0, address], 'Enter on the address as it was opened added an entry: ' + typed);
        deq([opened.box(), opened.pushes()], [typed, 0], typed);
      }
    },
    'arrow keys through three activities, then a search: Back shows the last activity, the next Back the plain list': () => {
      const [first, second, third] = MODEL.activities.filter((a) => a !== 'all');
      assert.ok(third, 'the fixture needs three activities besides All');
      const last = '?activity=' + third, found = '?q=ridge&activity=' + third + '&sort=relevance';
      const page = load();
      page.pause();
      page.activity(first);                                 // a press per arrow key: selection follows focus
      deq(where(page), [['', '?activity=' + first], 1, '?activity=' + first]);
      page.pause(100);
      page.activity(second);                                // within the moment: the entry just made is rewritten
      deq(where(page), [['', '?activity=' + second], 1, '?activity=' + second]);
      page.pause(100);
      page.activity(third);
      deq(where(page), [['', last], 1, last]);
      eq(page.pushes(), 1);
      page.pause();
      page.type('ridge');
      deq(where(page), [['', last], 1, last]);
      page.pause();
      deq(where(page), [['', found], 1, found]);            // typing rewrites the entry of the last activity
      page.enter();
      deq(where(page), [['', last, found], 2, found]);
      deq(page.calls().slice(-2), ['replace ' + last, 'push ' + found], 'the entry was put back to an activity the visitor only passed through');
      page.back();
      deq(where(page), [['', last, found], 1, last]);
      deq([page.chosen(), page.box(), page.left()], [third, '', false]);
      page.back();
      deq(where(page), [['', last, found], 0, '']);
      deq([page.chosen(), page.box(), page.shown(), page.left()], ['all', '', ALL, false]);
    },
    'a filter picked within a moment of a submitted search is part of what its entry stands for': () => {
      const skiing = '?q=ridge&activity=ski&sort=relevance', tour = '?q=tour&activity=ski&sort=relevance';
      const page = load();
      page.type('ridge');
      page.enter();
      deq(where(page), [['', SEARCHED], 1, SEARCHED]);
      page.pause(100);
      page.activity('ski');                                 // within the moment: the search's entry is rewritten
      deq(where(page), [['', skiing], 1, skiing]);
      page.pause();
      page.type('tour');
      page.pause();
      deq(where(page), [['', tour], 1, tour]);
      page.enter();
      deq(where(page), [['', skiing, tour], 2, tour]);
      page.back();
      deq(where(page), [['', skiing, tour], 1, skiing]);
      deq([page.box(), page.chosen()], ['ridge', 'ski'], 'Back lost the filter the visitor had chosen');
      page.back();
      deq(where(page), [['', skiing, tour], 0, '']);
    },
    'a search submitted within a moment of a filter rewrites the filter\'s entry, and is what it stands for': () => {
      const skiing = '?q=ridge&activity=ski&sort=relevance', tour = '?q=tour&activity=ski&sort=relevance';
      const page = load();
      page.pause();
      page.activity('ski');
      deq(where(page), [['', '?activity=ski'], 1, '?activity=ski']);
      page.pause(100);
      page.type('ridge');
      page.enter();                                         // Enter within the moment: no second entry
      deq(where(page), [['', skiing], 1, skiing]);
      eq(page.pushes(), 1);
      page.pause();
      page.type('tour');
      page.pause();
      page.enter();
      deq(where(page), [['', skiing, tour], 2, tour]);
      page.back();
      deq(where(page), [['', skiing, tour], 1, skiing]);
      deq([page.box(), page.chosen()], ['ridge', 'ski']);
    },
    'a box emptied by hand leaves Newest first, and no sort in the address': () => {
      const loop = '?q=loop&sort=relevance';
      // typed, then emptied: the automatic Best match goes with the words
      let page = load();
      page.type('ridge');
      page.pause();
      deq(where(page), [[SEARCHED], 0, SEARCHED]);
      eq(page.sort(), 'relevance');
      page.type('');
      deq(where(page), [[SEARCHED], 0, SEARCHED]);
      page.pause();
      deq(where(page), [[''], 0, '']);
      deq([page.sort(), page.box(), page.shown()], ['newest', '', ALL]);
      // a search opened directly: its Best match counts as the visitor's (it is in the address), and goes all the same
      page = load({ search: SEARCHED });
      deq(where(page), [[SEARCHED], 0, SEARCHED]);
      deq([page.sort(), page.box()], ['relevance', 'ridge']);
      page.pause();
      page.type('');
      page.pause();
      deq(where(page), [[''], 0, '']);
      deq([page.sort(), page.shown()], ['newest', ALL], 'Best match was left as the sort of no search');
      page.type('loop');                                    // and the sort is automatic again
      page.pause();
      deq(where(page), [[loop], 0, loop]);
      page.type('');
      page.pause();
      deq(where(page), [[''], 0, '']);
      eq(page.sort(), 'newest');
      // Back onto a submitted search, and the box emptied there
      page = searched();
      page.type('loop');
      page.pause();
      page.enter();
      deq(where(page), [['', SEARCHED, loop], 2, loop]);
      page.pause();
      page.back();
      deq(where(page), [['', SEARCHED, loop], 1, SEARCHED]);
      deq([page.sort(), page.box()], ['relevance', 'ridge']);
      page.pause();
      page.type('');
      page.pause();
      deq(where(page), [['', '', loop], 1, '']);            // typing rewrites the entry the visitor is on
      deq([page.sort(), page.shown()], ['newest', ALL], 'Best match was left as the sort of no search');
      // emptied and Enter at once: from a search to the plain list is a change of view, in Newest first
      page = load({ search: SEARCHED });
      page.pause();
      page.type('');
      page.enter();
      deq(where(page), [[SEARCHED, ''], 1, '']);
      deq([page.sort(), page.shown()], ['newest', ALL]);
      page.back();
      deq(where(page), [[SEARCHED, ''], 0, SEARCHED]);
      deq([page.sort(), page.box()], ['relevance', 'ridge']);
    },
    'an address with Best match and no search opens as the plain list, with a clean address': () => {
      const page = load({ search: '?sort=relevance' });
      deq(where(page), [[''], 0, '']);
      deq(page.calls(), ['replace ']);
      deq([page.sort(), page.box(), page.shown()], ['newest', '', ALL]);
      page.pause();
      page.enter();                                         // the plain list is what the entry stands for
      deq(where(page), [[''], 0, '']);
      eq(page.pushes(), 0);
      page.type('ridge');                                   // and the sort is automatic: a search is best match first
      page.pause();
      deq(where(page), [[SEARCHED], 0, SEARCHED]);
      page.type('');
      page.pause();
      deq(where(page), [[''], 0, '']);
      // a filter and a fragment beside it stay; words that search nothing are no search
      const more = load({ search: '?activity=ski&sort=relevance', hash: YEAR });
      deq(where(more), [['?activity=ski' + YEAR], 0, '?activity=ski' + YEAR]);
      deq([more.sort(), more.chosen()], ['newest', 'ski']);
      const none = load({ search: '?q=!!!&sort=relevance' });
      deq(where(none), [['?q=!!!'], 0, '?q=!!!']);
      deq([none.sort(), none.shown()], ['newest', ALL]);
    },
    'an address with Oldest first and no search keeps Oldest first': () => {
      const page = load({ search: '?sort=oldest' });
      deq(where(page), [['?sort=oldest'], 0, '?sort=oldest']);
      deq([page.sort(), page.shown()], ['oldest', ALL]);
      page.pause();
      page.enter();
      deq(where(page), [['?sort=oldest'], 0, '?sort=oldest']);
      eq(page.pushes(), 0);
      page.type('ridge');                                   // it is the visitor's own: a search keeps it,
      page.pause();
      deq(where(page), [['?q=ridge&sort=oldest'], 0, '?q=ridge&sort=oldest']);
      page.type('');                                        // and so does emptying the box by hand
      page.pause();
      deq(where(page), [['?sort=oldest'], 0, '?sort=oldest']);
      eq(page.sort(), 'oldest');
    },
    'a shared search without a sort opens, and comes back, in the order it was shared': () => {
      // the sort is looked at on load and on Back only when there is no search: this one is not turned to Best match
      const shared = '?q=ridge', skiing = '?q=ridge&activity=ski';
      const page = load({ search: shared });
      deq(where(page), [[shared], 0, shared]);
      deq([page.sort(), page.box(), page.shown()], ['newest', 'ridge', RIDGE]);
      page.pause();
      page.activity('ski');
      deq(where(page), [[shared, skiing], 1, skiing]);
      page.pause();
      page.back();
      deq(where(page), [[shared, skiing], 0, shared]);
      deq([page.sort(), page.chosen(), page.shown()], ['newest', 'all', RIDGE]);
      page.pause();
      page.enter();                                         // submitted, it is a search like any other: best match first
      deq(where(page), [[shared, SEARCHED], 1, SEARCHED]);
      eq(page.sort(), 'relevance');
    },
    'Back onto an address with Best match and no search shows the plain list, Newest first, at a clean address': () => {
      // the one way the page itself still writes such an address: Best match chosen in the menu while the box is empty
      // (the visitor's own pick, written as chosen)
      const best = '?sort=relevance', skiing = '?activity=ski&sort=relevance';
      const page = load();
      page.pause();
      page.choose('sort', 'relevance');
      deq(where(page), [['', best], 1, best]);
      page.pause();
      page.activity('ski');
      deq(where(page), [['', best, skiing], 2, skiing]);
      page.pause();
      const calls = page.calls().length;
      page.back();
      // round 4: Back rewrites the entry it lands on, as a load of that address is rewritten (round 3 left it saying
      // sort=relevance under a menu that read Newest first). One replaceState, no new entry
      deq(where(page), [['', '', skiing], 1, ''], 'the address still says Best match');
      deq([page.calls().slice(calls), page.pushes()], [['replace '], 2]);
      deq([page.sort(), page.chosen(), page.box(), page.shown()], ['newest', 'all', '', ALL], 'Best match came back as the sort of no search');
      // the entry stands for the plain list it shows: Enter in the empty box adds nothing and changes nothing
      page.pause();
      page.enter();
      deq(where(page), [['', '', skiing], 1, '']);
      eq(page.pushes(), 2);
      page.type('ridge');                                   // and the sort is automatic again
      page.pause();
      deq(where(page), [['', SEARCHED, skiing], 1, SEARCHED]);
      page.type('');
      page.pause();
      deq(where(page), [['', '', skiing], 1, '']);
      eq(page.sort(), 'newest');
    },
    'type, a year link, Enter: the entry the year link made keeps the typed search': () => { typedThenYear({}); },
    'the same in a browser that sends no popstate for a fragment: the hashchange alone settles the entry': () => {
      typedThenYear({ fragmentPopstate: false });
    },
    'a submitted search, then a year link: Back returns to the search, the next Back to the list': () => {
      const there = SEARCHED + YEAR, loop = '?q=loop&sort=relevance';
      const page = searched();
      page.year(MODEL.year);
      deq(where(page), [['', SEARCHED, there], 2, there]);
      eq(page.pushes(), 1);
      page.pause();
      page.back();
      deq(where(page), [['', SEARCHED, there], 1, SEARCHED]);
      deq([page.box(), page.shown()], ['ridge', RIDGE]);
      page.back();
      deq(where(page), [['', SEARCHED, there], 0, '']);
      deq([page.box(), page.shown(), page.left()], ['', ALL, false]);
      // forward again to the entry the year link made: a new search from there goes on top of the search it stands for
      page.forward();
      page.forward();
      deq(where(page), [['', SEARCHED, there], 2, there]);
      deq([page.box(), page.sort()], ['ridge', 'relevance']);
      page.type('loop');
      page.pause();
      deq(where(page), [['', SEARCHED, loop], 2, loop]);
      page.enter();
      deq(where(page), [['', SEARCHED, SEARCHED, loop], 3, loop]);
      page.back();
      deq(where(page), [['', SEARCHED, SEARCHED, loop], 2, SEARCHED]);
      deq([page.box(), page.shown()], ['ridge', RIDGE]);
    },
    'Forward onto a search, after the same words were typed into the entry before it: Enter adds nothing': () => {
      // two entries with one address: arriving on the second is no change of view (a popstate, and no hashchange), yet
      // it is the entry the visitor is on now, and it stands for the search. With an apostrophe too: the entry is
      // settled on the page's spelling of the words
      for (const [typed, address] of [['ridge', SEARCHED], ["lover's", '?q=lover%27s&sort=relevance']]) {
        const page = load();
        page.type(typed);
        page.pause();
        page.enter();
        deq(where(page), [['', address], 1, address], typed);
        page.pause();
        page.back();
        deq(where(page), [['', address], 0, ''], typed);
        page.type(typed);
        page.pause();
        deq(where(page), [[address, address], 0, address], typed);     // typing rewrites the entry of the plain list
        page.forward();
        deq(where(page), [[address, address], 1, address], typed);
        deq([page.box(), page.sort()], [typed, 'relevance']);
        page.pause();
        page.enter();
        deq(where(page), [[address, address], 1, address], 'the entry of the search was rewritten or another added: ' + typed);
        eq(page.pushes(), 1, typed);
      }
    },
    'type, pause, Enter, Back, Forward, Enter adds no entry': () => {
      const loop = '?q=loop&sort=relevance';
      const page = load();
      page.type('ridge');
      page.pause();
      deq(where(page), [[SEARCHED], 0, SEARCHED]);
      page.enter();
      deq(where(page), [['', SEARCHED], 1, SEARCHED]);
      page.pause();
      page.back();
      deq(where(page), [['', SEARCHED], 0, '']);
      deq([page.box(), page.shown()], ['', ALL]);
      page.pause();
      page.forward();
      deq(where(page), [['', SEARCHED], 1, SEARCHED]);
      deq([page.box(), page.sort(), page.shown()], ['ridge', 'relevance', RIDGE]);
      page.pause();
      let calls = page.calls().length;
      page.enter();
      deq(where(page), [['', SEARCHED], 1, SEARCHED]);
      deq([page.pushes(), page.calls().slice(calls)], [1, ['replace ' + SEARCHED]]);
      // Back once more, and another search with Enter before the typing pause is over: one entry made, and nothing put
      // back, because the entry the visitor came back to carries the address it stands for
      page.back();
      deq(where(page), [['', SEARCHED], 0, '']);
      calls = page.calls().length;
      page.type('loop');
      page.enter();
      deq(where(page), [['', loop], 1, loop]);
      deq(page.calls().slice(calls), ['push ' + loop]);
    },
    'type, pause, a filter, Back: the typed search without the filter': () => {
      const there = '?q=ridge&region=' + MODEL.region + '&sort=relevance';
      const page = load();
      page.type('ridge');
      page.pause();
      deq(where(page), [[SEARCHED], 0, SEARCHED]);
      page.choose('region', MODEL.region);
      deq(where(page), [[SEARCHED, there], 1, there]);     // typing is kept when a pick follows: nothing is put back
      deq(page.calls(), ['replace ', 'replace ' + SEARCHED, 'push ' + there]);
      page.pause();
      page.enter();                                         // the pick is what its entry stands for
      deq(where(page), [[SEARCHED, there], 1, there]);
      page.back();
      deq(where(page), [[SEARCHED, there], 0, SEARCHED]);
      deq([page.box(), page.chips(), page.shown(), page.left()], ['ridge', ['Search: ridge'], RIDGE, false]);
      page.pause();
      page.enter();                                         // come back to, the typed search is what its entry stands for
      deq(where(page), [[SEARCHED, there], 0, SEARCHED]);
      eq(page.pushes(), 1);
      page.back();
      eq(page.left(), true);                                // the list before the typing was never an entry of its own
    },
    'a submitted search, then a filter, then Back, Back': () => {
      const skiing = '?q=ridge&activity=ski&sort=relevance';
      const page = searched();
      deq(where(page), [['', SEARCHED], 1, SEARCHED]);
      page.activity('ski');
      deq(where(page), [['', SEARCHED, skiing], 2, skiing]);
      deq(page.calls().slice(-1), ['push ' + skiing]);
      page.pause();
      page.back();
      deq(where(page), [['', SEARCHED, skiing], 1, SEARCHED]);
      deq([page.box(), page.chosen(), page.shown()], ['ridge', 'all', RIDGE]);
      page.back();
      deq(where(page), [['', SEARCHED, skiing], 0, '']);
      deq([page.box(), page.chosen(), page.sort(), page.shown(), page.left()], ['', 'all', 'newest', ALL, false]);
      page.forward();
      page.forward();
      deq(where(page), [['', SEARCHED, skiing], 2, skiing]);
      deq([page.box(), page.chosen()], ['ridge', 'ski']);
      eq(page.pushes(), 2);
    },
    'Enter in an empty box on a fresh page adds no entry': () => {
      const page = load();
      deq(where(page), [[''], 0, '']);
      page.enter();                                         // at once, before anything else is done
      deq(where(page), [[''], 0, '']);
      page.pause();
      page.enter();
      deq(where(page), [[''], 0, '']);
      deq(page.calls(), ['replace ', 'replace ', 'replace ']);
      page.back();
      eq(page.left(), true);
      // nor on a page opened with a filter in its address, or by the header's Search link (whose fragment goes with the
      // first thing the visitor does)
      const filtered = load({ search: '?activity=ski' });
      filtered.enter();
      deq(where(filtered), [['?activity=ski'], 0, '?activity=ski']);
      eq(filtered.pushes(), 0);
      const linked = load({ hash: '#search' });
      deq(where(linked), [['#search'], 0, '#search']);
      linked.enter();
      deq(where(linked), [[''], 0, '']);
      eq(linked.pushes(), 0);
    },
    'two different searches submitted in a row are two entries, and Back, Back walks them': () => {
      const loop = '?q=loop&sort=relevance';
      const page = load();
      page.type('ridge');
      page.pause();
      page.enter();
      deq(where(page), [['', SEARCHED], 1, SEARCHED]);
      page.pause();
      page.type('loop');
      deq(where(page), [['', SEARCHED], 1, SEARCHED]);
      page.pause();
      deq(where(page), [['', loop], 1, loop]);             // typing rewrites the entry of the first search,
      page.enter();
      deq(where(page), [['', SEARCHED, loop], 2, loop]);   // and Enter puts it back under the second search's own
      deq(page.calls().slice(-2), ['replace ' + SEARCHED, 'push ' + loop]);
      eq(page.pushes(), 2);
      page.back();
      deq(where(page), [['', SEARCHED, loop], 1, SEARCHED]);
      deq([page.box(), page.shown()], ['ridge', RIDGE]);
      page.back();
      deq(where(page), [['', SEARCHED, loop], 0, '']);
      deq([page.box(), page.shown(), page.left()], ['', ALL, false]);
      page.back();
      eq(page.left(), true);
      // each Enter before its typing pause is over: the same two entries, and nothing to put back
      const quick = load();
      quick.type('ridge');
      quick.enter();
      deq(where(quick), [['', SEARCHED], 1, SEARCHED]);
      quick.pause();
      quick.type('loop');
      quick.enter();
      deq(where(quick), [['', SEARCHED, loop], 2, loop]);
      deq(quick.calls(), ['replace ', 'push ' + SEARCHED, 'push ' + loop]);
    },
    // ---- round 4 of the gate. Best match can be picked in the Sort menu while the search box is empty: the pick makes
    // its entry (trips/?sort=relevance) and the menu reads Best match until the visitor leaves it. Back or Forward
    // onto such an entry puts the sort right, as in round 3, and now rewrites the entry's address as well (its
    // fragment kept), as a load of that address is rewritten; an entry whose sort needs no correction is not written
    // to. In these checks seen(page) is read after every step: every entry, the one the visitor is on, its address,
    // the Sort menu and the reports in the order they are listed.
    'Best match picked with an empty box: Back and Forward onto its entry rewrite the address, and the menu agrees': () => {
      // the fixture: the cards are the model's reports, newest first, no two on one date; some are skiing, not all
      deq(CARDS.map((c) => c['data-slug']), NEWEST);
      CARDS.forEach((c, i) => { assert.ok(i === 0 || c['data-date'] < CARDS[i - 1]['data-date'], 'the fixture is not newest first: ' + c['data-slug']); });
      assert.ok(SKI.length > 1 && SKI.length < NEWEST.length, 'the fixture needs skiing reports and others');
      const page = load();
      deq(seen(page), [[''], 0, '', 'newest', NEWEST]);
      deq(page.order().slice().sort(), page.shown());       // the two read the same cards
      page.pause();
      page.choose('sort', 'relevance');
      // one entry; the menu reads Best match; nothing is searched, so the list stays newest first
      deq(seen(page), [['', BEST], 1, BEST, 'relevance', NEWEST]);
      deq(page.calls(), ['replace ', 'push ' + BEST]);
      page.pause();                                         // the moment is over: the next pick is an entry of its own
      page.activity('ski');
      deq(seen(page), [['', BEST, SKIING_BEST], 2, SKIING_BEST, 'relevance', SKI]);
      let calls = page.calls().length;
      page.back();
      // the entry's address is the plain one now, in the same entry: as many entries as before the Back, none added
      deq(seen(page), [['', '', SKIING_BEST], 1, '', 'newest', NEWEST], 'the menu and the address of the entry do not agree');
      deq([page.calls().slice(calls), page.pushes()], [['replace '], 2]);
      deq([page.chosen(), page.box(), page.chips(), page.left()], ['all', '', [], false]);
      page.back();                                          // the list the page opened on
      deq(seen(page), [['', '', SKIING_BEST], 0, '', 'newest', NEWEST]);
      deq([page.calls().slice(calls), page.left()], [['replace '], false]);
      page.forward();                                       // the rewritten entry needs no correction any more
      deq(seen(page), [['', '', SKIING_BEST], 1, '', 'newest', NEWEST]);
      deq(page.calls().slice(calls), ['replace ']);
      page.forward();                                       // the activity's entry carried Best match too: it loses it when landed on
      deq(seen(page), [['', '', SKIING], 2, SKIING, 'newest', SKI], 'the menu and the address of the entry do not agree');
      deq([page.calls().slice(calls), page.chosen()], [['replace ', 'replace ' + SKIING], 'ski']);
      // every entry now says what it shows: walking them again writes nothing
      calls = page.calls().length;
      page.back();
      deq(seen(page), [['', '', SKIING], 1, '', 'newest', NEWEST]);
      eq(page.chosen(), 'all');
      page.back();
      deq(seen(page), [['', '', SKIING], 0, '', 'newest', NEWEST]);
      page.forward();
      deq(seen(page), [['', '', SKIING], 1, '', 'newest', NEWEST]);
      page.forward();
      deq(seen(page), [['', '', SKIING], 2, SKIING, 'newest', SKI]);
      deq([page.calls().length, page.pushes(), page.chosen(), page.left()], [calls, 2, 'ski', false]);
      // the shortest way onto such an entry: the pick, Back to the list the page opened on, Forward
      const short = load();
      short.pause();
      short.choose('sort', 'relevance');
      deq(seen(short), [['', BEST], 1, BEST, 'relevance', NEWEST]);
      short.pause();
      short.back();                                         // the visitor leaves the entry: the menu reads Newest first again,
      deq(seen(short), [['', BEST], 0, '', 'newest', NEWEST]);
      deq(short.calls(), ['replace ', 'push ' + BEST]);     // and nothing is written (the entry left behind is not the one landed on)
      short.forward();
      deq(seen(short), [['', ''], 1, '', 'newest', NEWEST], 'Forward onto the entry left its address saying Best match');
      deq(short.calls(), ['replace ', 'push ' + BEST, 'replace ']);
      short.back();
      deq(seen(short), [['', ''], 0, '', 'newest', NEWEST]);
      short.forward();
      deq(seen(short), [['', ''], 1, '', 'newest', NEWEST]);
      deq([short.calls().length, short.replaces(), short.pushes()], [3, 2, 1]);
      // words that search nothing are no search: Best match picked beside them is put right, and rewritten, the same way
      const none = load();
      none.type('!!!');
      none.pause();
      deq(seen(none), [['?q=!!!'], 0, '?q=!!!', 'newest', NEWEST]);
      none.choose('sort', 'relevance');
      deq(seen(none), [['?q=!!!', '?q=!!!&sort=relevance'], 1, '?q=!!!&sort=relevance', 'relevance', NEWEST]);
      none.pause();
      none.activity('ski');
      deq(seen(none), [['?q=!!!', '?q=!!!&sort=relevance', '?q=!!!&activity=ski&sort=relevance'], 2, '?q=!!!&activity=ski&sort=relevance', 'relevance', SKI]);
      none.pause();
      none.back();
      deq(seen(none), [['?q=!!!', '?q=!!!', '?q=!!!&activity=ski&sort=relevance'], 1, '?q=!!!', 'newest', NEWEST]);
      deq([none.box(), none.calls().slice(-1)], ['!!!', ['replace ?q=!!!']]);
    },
    'the rewrite keeps the fragment of the entry it lands on, and takes no other': () => {
      // a year link followed after the pick is the browser's own entry: the same address with the fragment. Also in a
      // browser that sends no popstate when only the fragment changes
      for (const opts of [{}, { fragmentPopstate: false }]) {
        const name = JSON.stringify(opts);
        const page = load(opts);
        page.pause();
        page.choose('sort', 'relevance');
        deq(seen(page), [['', BEST], 1, BEST, 'relevance', NEWEST], name);
        page.pause();
        page.year(MODEL.year);
        deq(seen(page), [['', BEST, BEST + YEAR], 2, BEST + YEAR, 'relevance', NEWEST], name);
        // between the two entries of this one view nothing is read again or written: the menu still reads Best match
        page.back();
        deq(seen(page), [['', BEST, BEST + YEAR], 1, BEST, 'relevance', NEWEST], name);
        page.forward();
        deq(seen(page), [['', BEST, BEST + YEAR], 2, BEST + YEAR, 'relevance', NEWEST], name);
        deq(page.calls(), ['replace ', 'push ' + BEST], name);
        page.pause();
        page.activity('ski');
        deq(seen(page), [['', BEST, BEST + YEAR, SKIING_BEST], 3, SKIING_BEST, 'relevance', SKI], name);
        const calls = page.calls().length;
        page.back();
        deq(seen(page), [['', BEST, YEAR, SKIING_BEST], 2, YEAR, 'newest', NEWEST], 'the rewrite did not keep the fragment: ' + name);
        deq(page.calls().slice(calls), ['replace ' + YEAR], name);
        page.back();                                        // the pick's own entry still says Best match: rewritten in its turn, with no fragment
        deq(seen(page), [['', '', YEAR, SKIING_BEST], 1, '', 'newest', NEWEST], 'the entry under the rewritten one kept Best match: ' + name);
        deq(page.calls().slice(calls), ['replace ' + YEAR, 'replace '], name);
        page.forward();                                     // the same query string: a jump to a fragment
        deq(seen(page), [['', '', YEAR, SKIING_BEST], 2, YEAR, 'newest', NEWEST], name);
        page.forward();
        deq(seen(page), [['', '', YEAR, SKIING], 3, SKIING, 'newest', SKI], name);
        deq([page.calls().slice(calls), page.pushes()], [['replace ' + YEAR, 'replace ', 'replace ' + SKIING], 2], name);
      }
      // the fragment is the entry's own, not the one the page opened with (the header's Search link): here the entry has none
      const linked = load({ hash: '#search' });
      deq(seen(linked), [['#search'], 0, '#search', 'newest', NEWEST]);
      linked.pause();
      linked.choose('sort', 'relevance');
      deq(seen(linked), [['#search', BEST], 1, BEST, 'relevance', NEWEST]);
      linked.pause();
      linked.activity('ski');
      deq(seen(linked), [['#search', BEST, SKIING_BEST], 2, SKIING_BEST, 'relevance', SKI]);
      linked.pause();
      linked.back();
      deq(seen(linked), [['#search', '', SKIING_BEST], 1, '', 'newest', NEWEST], 'the rewrite took the fragment the page opened with');
      linked.back();
      deq(seen(linked), [['#search', '', SKIING_BEST], 0, '#search', 'newest', NEWEST]);
      // and the other way round: opened plain, the entry has a fragment (above); opened with one, the entry has another
      const other = load({ hash: '#search' });
      other.pause();
      other.choose('sort', 'relevance');
      deq(seen(other), [['#search', BEST], 1, BEST, 'relevance', NEWEST]);
      other.pause();
      other.year(MODEL.year);
      deq(seen(other), [['#search', BEST, BEST + YEAR], 2, BEST + YEAR, 'relevance', NEWEST]);
      other.pause();
      other.activity('ski');
      deq(seen(other), [['#search', BEST, BEST + YEAR, SKIING_BEST], 3, SKIING_BEST, 'relevance', SKI]);
      other.pause();
      other.back();
      deq(seen(other), [['#search', BEST, YEAR, SKIING_BEST], 2, YEAR, 'newest', NEWEST]);
    },
    'Back and Forward onto an entry whose sort needs no correction rewrite nothing': () => {
      // WORD is found in several reports, and the three sorts list them in three orders: the order tells the sort
      const found = finds(WORD), best = bestFirst(WORD), oldest = OLDEST.filter((s) => found.indexOf(s) !== -1);
      assert.ok(found.length > 2, 'the fixture search must find several reports');
      assert.notDeepStrictEqual(best, found, 'the fixture search must not be best match first in the newest order');
      assert.notDeepStrictEqual(best, oldest, 'the fixture search must not be best match first in the oldest order');
      const typed = '?q=' + WORD, byBest = typed + '&sort=relevance', byOldest = typed + '&sort=oldest';
      // A step: [what the visitor does, what that does to the history, then the address, the Sort menu and the list].
      // 'push': a new entry. 'type': the entry the visitor is on is rewritten. 'enter': that entry is put back to the
      // address it stood for, and a new one is made
      const pickOldest = [(page) => page.choose('sort', 'oldest'), 'push', '?sort=oldest', 'oldest', OLDEST];
      const type = (address, sort, order) => [(page) => { page.type(WORD); page.pause(); }, 'type', address, sort, order];
      const enter = (address, sort, order) => [(page) => page.enter(), 'enter', address, sort, order];
      // [the entry, how the page is opened, what it opens on (address, Sort menu, list), the steps to the entry]
      const entries = [
        ['the plain list', {}, ['', 'newest', NEWEST], []],
        ['Oldest first and no search', {}, ['', 'newest', NEWEST], [pickOldest]],
        ['a submitted search, best match first', {}, ['', 'newest', NEWEST],
          [type(byBest, 'relevance', best), enter(byBest, 'relevance', best)]],
        ['a search with a chosen Oldest first', {}, ['', 'newest', NEWEST],
          [pickOldest, type(byOldest, 'oldest', oldest), enter(byOldest, 'oldest', oldest)]],
        ['a search with Best match chosen in the menu', {}, ['', 'newest', NEWEST],
          [pickOldest, type(byOldest, 'oldest', oldest), enter(byOldest, 'oldest', oldest),
            [(page) => page.choose('sort', 'relevance'), 'push', byBest, 'relevance', best]]],
        ['a shared search without a sort', { search: typed }, [typed, 'newest', found], []],
        ['a shared search, oldest first, at a year', { search: byOldest, hash: YEAR }, [byOldest + YEAR, 'oldest', oldest], []],
        ['a filter and no sort', {}, ['', 'newest', NEWEST], [[(page) => page.activity('ski'), 'push', SKIING, 'newest', SKI]]],
      ];
      for (const [name, opts, opened, steps] of entries) {
        const page = load(opts);
        let [address, sort, order] = opened, stack = [address], at = 0, stood = address;
        deq(seen(page), [stack, at, address, sort, order], name);
        for (const [act, kind, toAddress, toSort, toOrder] of steps) {
          page.pause();
          act(page);
          if (kind === 'type') stack[at] = toAddress;
          else {
            if (kind === 'enter') stack[at] = stood;
            stack = stack.slice(0, at + 1).concat([toAddress]);
            at++;
            stood = toAddress;
          }
          [address, sort, order] = [toAddress, toSort, toOrder];
          deq(seen(page), [stack, at, address, sort, order], name + ', after ' + kind + ' ' + toAddress);
        }
        // another view on top of it: the list view (the last key of an address, no change to the order; a pick drops
        // the fragment from the new entry and leaves the old one as it is)
        const bare = address.split('#')[0], listed = bare + (bare ? '&' : '?') + 'view=list';
        stack = stack.concat([listed]);
        page.pause();
        page.view('list');
        deq(seen(page), [stack, at + 1, listed, sort, order], name);
        page.pause();
        const calls = page.calls(), replaces = page.replaces();
        page.back();
        deq(seen(page), [stack, at, address, sort, order], name);
        deq([page.calls(), page.replaces(), page.left()], [calls, replaces, false], 'Back wrote to the history: ' + name);
        page.forward();
        deq(seen(page), [stack, at + 1, listed, sort, order], name);
        deq([page.calls(), page.replaces()], [calls, replaces], 'Forward wrote to the history: ' + name);
        page.back();
        deq(seen(page), [stack, at, address, sort, order], name);
        deq([page.calls(), page.replaces(), page.pushes()], [calls, replaces, calls.length - replaces], name);
      }
    },
    'after the rewrite, a search typed and submitted from that entry: Back lands on the plain list once': () => {
      // quick: Enter before the typing pause is over
      for (const quick of [false, true]) {
        const name = quick ? 'Enter at once' : 'Enter after the pause';
        const page = rewritten();
        page.type('ridge');
        deq(seen(page), [['', '', SKIING_BEST], 1, '', 'newest', NEWEST], name);
        if (!quick) {
          page.pause();                                     // typing rewrites the entry the visitor is on
          deq(seen(page), [['', SEARCHED, SKIING_BEST], 1, SEARCHED, 'relevance', RIDGE_BEST], name);
        }
        let calls = page.calls().length;
        page.enter();
        // the search is one new entry on top of the plain list. What the typing wrote is put back to the plain address
        // the entry stands for since the rewrite, not to the sort=relevance it carried before; the entry Forward led
        // to is gone
        deq(seen(page), [['', '', SEARCHED], 2, SEARCHED, 'relevance', RIDGE_BEST], name);
        deq(page.calls().slice(calls), quick ? ['push ' + SEARCHED] : ['replace ', 'push ' + SEARCHED], name);
        page.pause();
        calls = page.calls().length;
        page.back();
        deq(seen(page), [['', '', SEARCHED], 1, '', 'newest', NEWEST], 'Back did not land on the plain list: ' + name);
        deq([page.box(), page.chips(), page.chosen(), page.left()], ['', [], 'all', false], name);
        page.forward();
        deq(seen(page), [['', '', SEARCHED], 2, SEARCHED, 'relevance', RIDGE_BEST], name);
        page.back();
        deq(seen(page), [['', '', SEARCHED], 1, '', 'newest', NEWEST], name);
        page.back();                                        // under it, the entry the page opened on
        deq(seen(page), [['', '', SEARCHED], 0, '', 'newest', NEWEST], name);
        deq([page.calls().length, page.pushes(), page.left()], [calls, 3, false], 'coming back wrote to the history: ' + name);
        page.back();
        eq(page.left(), true, name);
      }
    },
    'after the rewrite, a jump to a fragment and back does not read the address again': () => {
      // After the rewrite the page holds the query string the entry has now: a popstate that carries the same one is a
      // jump to or from a fragment, not a change of view. Words typed and not yet written are the one thing on screen
      // an address does not hold, so reading the address again would empty the box
      const page = rewritten();
      page.type('ridge');                                   // the typing pause is not over
      deq(seen(page), [['', '', SKIING_BEST], 1, '', 'newest', NEWEST]);
      let calls = page.calls().length;
      page.year(MODEL.year);
      deq(seen(page), [['', '', YEAR], 2, YEAR, 'newest', NEWEST]);
      eq(page.box(), 'ridge', 'the address was read again on the way to the fragment');
      page.back();
      deq(seen(page), [['', '', YEAR], 1, '', 'newest', NEWEST]);
      eq(page.box(), 'ridge', 'the address was read again on the way back');
      deq(page.calls().slice(calls), []);
      page.pause();                                         // the pause is over: the words go into the entry the visitor is on
      deq(seen(page), [['', SEARCHED, YEAR], 1, SEARCHED, 'relevance', RIDGE_BEST]);
      deq([page.calls().slice(calls), page.box()], [['replace ' + SEARCHED], 'ridge']);
      // the same on an entry rewritten with a filter in it: Forward onto the activity's entry
      const skiingRidge = '?q=ridge&activity=ski&sort=relevance';
      const other = rewritten();
      other.forward();
      deq(seen(other), [['', '', SKIING], 2, SKIING, 'newest', SKI]);
      other.pause();
      other.type('ridge');
      deq(seen(other), [['', '', SKIING], 2, SKIING, 'newest', SKI]);
      calls = other.calls().length;
      other.year(MODEL.year);
      deq(seen(other), [['', '', SKIING, SKIING + YEAR], 3, SKIING + YEAR, 'newest', SKI]);
      eq(other.box(), 'ridge', 'the address was read again on the way to the fragment');
      other.back();
      deq(seen(other), [['', '', SKIING, SKIING + YEAR], 2, SKIING, 'newest', SKI]);
      deq([other.box(), other.chosen(), other.calls().slice(calls)], ['ridge', 'ski', []]);
      other.pause();
      deq(seen(other), [['', '', skiingRidge, SKIING + YEAR], 2, skiingRidge, 'relevance', RIDGE_BEST.filter((s) => SKI.indexOf(s) !== -1)]);
    },
    'a rewrite the browser refuses leaves the entry as it is, and the view is put on screen all the same': () => {
      // history.replaceState can throw (a page opened from a file is one case). The handler keeps what was: the entry
      // keeps its address, and the plain list still comes on screen, Newest first
      const page = load();
      page.pause();
      page.choose('sort', 'relevance');
      deq(seen(page), [['', BEST], 1, BEST, 'relevance', NEWEST]);
      page.pause();
      page.activity('ski');
      deq(seen(page), [['', BEST, SKIING_BEST], 2, SKIING_BEST, 'relevance', SKI]);
      page.pause();
      const calls = page.calls();
      page.refuse(true);
      page.back();
      deq(seen(page), [['', BEST, SKIING_BEST], 1, BEST, 'newest', NEWEST], 'the view was not put on screen');
      deq([page.chosen(), page.box(), page.chips(), page.calls(), page.left()], ['all', '', [], calls, false]);
      // once the browser takes writes again the page is where it should be. The entry stands for the plain list, so
      // Enter in the empty box is no new view, and that write gives the entry its plain address
      page.refuse(false);
      page.pause();
      page.enter();
      deq(seen(page), [['', '', SKIING_BEST], 1, '', 'newest', NEWEST]);
      deq([page.calls().slice(calls.length), page.pushes()], [['replace '], 2]);
      page.forward();                                       // and the next landing is rewritten as usual
      deq(seen(page), [['', '', SKIING], 2, SKIING, 'newest', SKI]);
      deq(page.calls().slice(calls.length), ['replace ', 'replace ' + SKIING]);
      // refused on the way Forward as well: the view comes on screen, the address stays
      const other = rewritten();
      other.refuse(true);
      other.forward();
      deq(seen(other), [['', '', SKIING_BEST], 2, SKIING_BEST, 'newest', SKI], 'the view was not put on screen');
      eq(other.chosen(), 'ski');
    },
  };
  // GAPS: cases in which the page does not do what the rule above says. Each is run only when asked for, as
  // 'gap:<name>' and after every check above, by a test of tests/test_trips_js.py that is marked as an expected
  // failure; when the page is put right, that test says so and the case becomes a check above. None at present: the
  // two of round 2 (an apostrophe in the search, picks made within a moment) are the first two checks of round 3.
  const GAPS = {};
  const gap = ONLY.replace(/^gap:/, '');
  assert.ok(!ONLY || (ONLY.indexOf('gap:') === 0 && Object.prototype.hasOwnProperty.call(GAPS, gap)), 'unknown argument: ' + ONLY);
  Object.keys(pageChecks).forEach((label) => check('page: ' + label, pageChecks[label]));
  if (ONLY) check('gap: ' + gap, GAPS[gap]);
}

console.log('trips_js_harness: ' + checks + ' checks passed');
