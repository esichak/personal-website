/* Trips explorer (/trips/): text search over the build-time index (trips/search.json), combined filters (activity,
   region, year, month, format, has a write-up, has photos), newest / oldest / best-match / longest / most-gain order,
   cards or list, and the whole state in the
   URL (?q=…&activity=…) so a filtered view can be shared and Back / Forward restore it. A search also looks through the
   days of a journal (trips/journal.json) and lists the days it finds under "Journal days", after the reports: each is
   named by its journal, day and date and links to that day on the journal's own page.
   Without JavaScript the page is the full list by year with the browse links; the form stays hidden. The pure parts
   (explore.js, shared with tick-list/, and the journal-day decisions below) are exported as TRX for the Node unit test
   (tests/trips_js_harness.js). */
(function () {
  'use strict';
  var X = (typeof module === 'object' && module && module.exports) ? require('./explore.js') : window.Explore;  // the shared helpers
  var DEFAULTS = { q: '', activity: 'all', region: '', year: '', month: '', format: '', writeup: false, photos: false, sort: 'newest', view: 'cards' };
  var KEYS = ['q', 'activity', 'region', 'year', 'month', 'format', 'writeup', 'photos', 'sort', 'view'];
  var LABELS = { region: 'Region: ', year: 'Year: ', month: 'Month: ', format: 'Format: ', writeup: 'Has a write-up', photos: 'Has photos' };
  var norm = X.norm, tokens = X.tokens, has = X.has, match = X.match, score = X.score, snippet = X.snippet;
  function parseState(search, allowed) { return X.parseState(search, allowed, DEFAULTS, KEYS); }
  function serialize(st) { return X.serialize(st, DEFAULTS, KEYS); }
  function chipLabel(key, value, names) { return X.chipLabel(key, value, names, LABELS); }
  // The journal days (the entries of trips/journal.json) a query finds. A day is found by its own words: every token
  // starts a word of its title, its write-up or its date (e.d, 'june 30': the month and the day, never the year). A
  // query may also name the day ('day 31', 'day 5.2': the word day, then exactly its label), which is the only way to
  // find a day that has no words. The journal's own name and aliases (e.q, which hold its year) find the journal, among
  // the reports, not its days: alone they match nothing here, or every day would be listed. They may come along, as
  // whole words, with something of the day's own ('pct whitney', 'june 2024', 'pacific crest trail day 48'). Order: a
  // day the query names (the longer label first, so 'day 5.2' puts Day 5.2 above Day 5), then title hits above write-up
  // and date hits, then journal order.
  function dayHits(days, toks) {
    if (!toks.length) return [];
    var out = [];
    (days || []).forEach(function (e, i) {
      var title = e.t || '', text = e.x || '', date = e.d || '';
      var name = (e.p || '').split(' ').filter(Boolean);   // ['day', '31'], ['day', '5', '2']
      var rest = toks.slice(), named = 0;
      for (var k = 0; name.length > 1 && k + name.length <= rest.length;) {   // every run of the name, should it be typed twice
        var run = true;
        for (var j = 0; j < name.length; j++) if (rest[k + j] !== name[j]) { run = false; break; }
        if (run) { named = name.length; rest.splice(k, name.length); } else k++;
      }
      var journal = ' ' + (e.q || '') + ' ';
      var n = named * 100, own = named > 0, rode = false;
      for (var r = 0; r < rest.length; r++) {
        var inTitle = has(title, rest[r]), inText = has(text, rest[r]), inDate = has(date, rest[r]);
        var inJournal = journal.indexOf(' ' + rest[r] + ' ') !== -1;
        if (!inTitle && !inText && !inDate) { if (!inJournal) return; rode = true; }
        else if (!inJournal) own = true;
        n += (inTitle ? 3 : 0) + (inText ? 1 : 0) + (inDate ? 1 : 0);
      }
      if (rode && !own) return;   // nothing of the day's own beside the journal's name
      out.push({ e: e, i: i, score: n });
    });
    out.sort(function (a, b) { return b.score - a.score || a.i - b.i; });
    return out.map(function (x) { return x.e; });
  }
  // 'Pacific Crest Trail 2024 · Day 31 · May 22, 2024': whose day this is (the page shows it in caps)
  function dayMeta(e) { return [e.j, 'Day ' + e.n, e.w].filter(Boolean).join(' · '); }
  // the day on its journal's page, relative to trips/: '<slug>/#day-31'
  function dayHref(e) { return encodeURIComponent(e.s) + '/#' + encodeURIComponent(e.a); }
  // the words around the hit, or the day's opening when the hit is in its title or its name ('' for a day without a write-up)
  function dayText(e, toks) {
    var s = snippet(e.r, toks, 14);
    if (s) return s;
    var words = String(e.r || '').split(/\s+/).filter(Boolean);
    return words.slice(0, 24).join(' ') + (words.length > 24 ? ' …' : '');
  }
  // the status line: 'N REPORTS', or 'K OF N REPORTS' while a search or a filter narrows the list
  function countText(k, total, narrowed) { return (narrowed ? k + ' OF ' + total : total) + (total === 1 ? ' REPORT' : ' REPORTS'); }
  // 'N JOURNAL DAYS' for the status line and '' for none; 'N DAYS' beside the section's heading
  function daysCount(n) { return n ? n + (n === 1 ? ' JOURNAL DAY' : ' JOURNAL DAYS') : ''; }
  function daysHead(n) { return n + (n === 1 ? ' DAY' : ' DAYS'); }
  // the journal days listed: the first DAYS_SHOWN until the reader asks for all of them
  var DAYS_SHOWN = 5;
  function daysListed(list, all) { return all ? list.slice() : list.slice(0, DAYS_SHOWN); }
  // the button under the list: none when everything already shows
  function daysMoreText(n, all) { return n <= DAYS_SHOWN ? '' : all ? 'Show fewer journal days' : 'Show all ' + n + ' journal days'; }
  // a card's facets (its data attributes: act, region, year, month, kind, writeup, photos) against the filters of a
  // state; the search text is matched separately. A journal day is filtered as its journal's card is.
  function facetOk(d, st) {
    if (st.activity !== 'all' && d.act !== st.activity) return false;
    if (st.region && d.region !== st.region) return false;
    if (st.year && d.year !== st.year) return false;
    if (st.month && (' ' + (d.month || '') + ' ').indexOf(' ' + st.month + ' ') === -1) return false;   // every month it spans
    if (st.format && d.kind !== st.format) return false;
    if (st.writeup && d.writeup !== '1') return false;
    if (st.photos && (!d.photos || d.photos === '0')) return false;
    return true;
  }
  // Longest first / Most gain: the cards' data-km / data-gain, largest first; a card without the value after every
  // card that has one (in the order the list had). items: [{ value: '' | number text, i }]. Never a value of its own.
  function byValue(a, b) {
    var x = a.value === '' ? null : Number(a.value), y = b.value === '' ? null : Number(b.value);
    if (x === null || y === null) return (x === null) - (y === null) || a.i - b.i;
    return y - x || a.i - b.i;
  }
  // the line beside the heading of those two orders: how multi-day trips are counted, and how many cards have no value
  function sortedMeta(sort, missing, totals) {
    if (sort !== 'longest' && sort !== 'gain') return '';
    var bits = [];
    if (totals) bits.push('MULTI-DAY AND SERIES BY THEIR TOTALS');
    if (missing) bits.push(missing + ' WITHOUT A ' + (sort === 'longest' ? 'DISTANCE' : 'GAIN') + ', LISTED LAST');
    return bits.join(' \u00b7 ');
  }
  var SORTED_HEAD = { oldest: 'Oldest first', relevance: 'Best match first', longest: 'Longest first', gain: 'Most gain first' };
  // whether a found day is listed: its journal's card passes the filters (cardOk; false when the journal has no card),
  // and with 'Has a write-up' on the day itself has one. A titled track-only day has none, whatever its journal has.
  function dayShown(e, cardOk, writeup) { return !!cardOk && (!writeup || !!(e && e.x)); }
  // Month and Has photos ask the day itself too: its own date's month (from d, 'june 5') and its own photos (f). The
  // journal's card passes Month when the journal spans that month, so without this every day would follow it
  var MONTH_WORDS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];
  function dayMonth(e) { var i = MONTH_WORDS.indexOf(String((e && e.d) || '').split(' ')[0]); return i < 0 ? '' : (i < 9 ? '0' : '') + (i + 1); }
  function dayFacets(e, st) { return (!st.month || dayMonth(e) === st.month) && (!st.photos || !!(e && e.f)); }
  // a first search fetches two indexes: until both have answered, the count is not rewritten and the empty state is not
  // shown, so 'No trips match' never flashes before the journal days arrive and the status line is spoken once
  function pending(searching, tripsState, daysState) { return !!searching && (tripsState === 'loading' || daysState === 'loading'); }
  // what to say when an index did not load: nothing without a query; the journal days still work when only theirs loaded
  var FAIL = 'Search isn’t available right now (the search index didn’t load). The filters still work.';
  var FAIL_REPORTS = 'Report search isn’t available right now (its index didn’t load). Journal days and the filters still work.';
  function failText(searching, tripsFailed, daysReady) { return !searching || !tripsFailed ? '' : daysReady ? FAIL_REPORTS : FAIL; }
  // the one note under the search box: what failed, else that the search is still loading, else nothing
  var LOADING = 'Loading search…';
  function noteText(searching, tripsState, daysState) {
    if (tripsState === 'failed') return failText(searching, true, daysState === 'ready');
    return pending(searching, tripsState, daysState) ? LOADING : '';
  }
  // The form is on screen before this script arrives (core.reveal shows it at first paint), so the visitor may have used
  // it by then. adoptForm(st, form, traversal) is the state the page starts from. st is the URL's state (parseState);
  // form is what the controls hold as the script finds them, { q, region, year, format, sort, writeup } (a control the
  // page lacks is left out). A key the URL sets keeps the URL's value, so a shared address still opens as it was
  // shared, and the control is put back to it. A key the URL leaves alone takes its control's value when that is off
  // the default: a select, the ticked write-up box, the text typed. traversal: the page was reached by Back / Forward,
  // when a browser may put the selects and the box back to what it remembers, which need not be what this address
  // says; they are then not taken. (The form is autocomplete="off" so that browsers leave the controls alone: Chrome
  // refills them after this script has run.) The text is taken either way: the browser never fills the box.
  // ownSort: the sort is one the visitor chose, in the address or in the form. Without one, typed text means best match
  // first, as it does when typed after the script has arrived.
  var SELECTS = ['region', 'year', 'month', 'format', 'sort'];
  function ownSort(st, form, traversal) {
    return st.sort !== DEFAULTS.sort || (!traversal && !!form && !!form.sort && form.sort !== DEFAULTS.sort);
  }
  function adoptForm(st, form, traversal) {
    var out = {};
    KEYS.forEach(function (k) { out[k] = st[k]; });
    form = form || {};
    if (!traversal) {
      SELECTS.forEach(function (k) { if (out[k] === DEFAULTS[k] && form[k] && form[k] !== DEFAULTS[k]) out[k] = String(form[k]); });
      if (form.writeup === true) out.writeup = true;
      if (form.photos === true) out.photos = true;
    }
    if (!out.q && form.q) {
      out.q = String(form.q);
      if (!ownSort(st, form, traversal) && tokens(out.q).length) out.sort = 'relevance';
    }
    return out;
  }
  // An index that did not load is asked for again when the search changes, never on every later render (a filter, a
  // view switch): failedFor is the query that was in the box when the request failed. stillFailed(failedFor, q) is what
  // to remember once the box holds q: the same query, while it is still that one, or null as soon as the box has been
  // cleared or changed, so that the same words typed again ask again. mayLoad(indexState, failedFor, q): whether a
  // search for q fetches now (never while a request is out, never once the index is here).
  function stillFailed(failedFor, q) { return failedFor === q ? failedFor : null; }
  function mayLoad(indexState, failedFor, q) {
    return tokens(q).length > 0 && (indexState === 'idle' || (indexState === 'failed' && q !== failedFor));
  }
  var historyStep = X.historyStep;   // what a change of view does to the browser's history: explore.js, shared with the tick list
  // The sort Clear all leaves: the visitor's own choice stays, except Best match, which orders by a search that is no
  // longer there. Returns [sort, whether it still counts as the visitor's choice].
  function clearedSort(sort, userSort) {
    return (userSort && sort !== 'relevance') ? [sort, true] : [DEFAULTS.sort, false];
  }
  var FACETS = ['activity', 'region', 'year', 'month', 'format', 'writeup', 'photos'];  // the filters (q is the search; sort / view are not)
  var MORE = ['region', 'year', 'month', 'format', 'writeup', 'photos'];   // the filters behind the phones' Filters button
  // the nearest views when a search and filters find nothing (explore.js relaxOffers), in reports; days: the journal
  // days the search finds without the filters
  function relaxOffers(st, noFacets, noQuery, names, days) { return X.relaxOffers(st, noFacets, noQuery, names, LABELS, DEFAULTS, FACETS, 'report', days); }
  var TRX = { norm: norm, tokens: tokens, has: has, parseState: parseState, serialize: serialize, match: match, score: score, snippet: snippet, chipLabel: chipLabel, DEFAULTS: DEFAULTS,
    adoptForm: adoptForm, ownSort: ownSort, stillFailed: stillFailed, mayLoad: mayLoad, historyStep: historyStep, clearedSort: clearedSort,
    FACETS: FACETS, MORE: MORE, relaxOffers: relaxOffers, dayMonth: dayMonth, dayFacets: dayFacets, byValue: byValue, sortedMeta: sortedMeta, SORTED_HEAD: SORTED_HEAD,
    dayHits: dayHits, dayMeta: dayMeta, dayHref: dayHref, dayText: dayText, countText: countText, daysCount: daysCount, daysHead: daysHead,
    DAYS_SHOWN: DAYS_SHOWN, daysListed: daysListed, daysMoreText: daysMoreText, facetOk: facetOk, dayShown: dayShown, pending: pending, failText: failText, noteText: noteText,
    FAIL: FAIL, FAIL_REPORTS: FAIL_REPORTS, LOADING: LOADING };
  if (typeof module === 'object' && module && module.exports) { module.exports = TRX; return; }
  if (typeof document === 'undefined' || !document.body.classList.contains('p-trips')) return;

  // ------------------------------------------------------------ the page
  var form = document.getElementById('search'), q = document.getElementById('trx-q');
  var results = document.getElementById('trx-results'), sortedUl = document.getElementById('trx-sorted');
  var sortedSec = document.getElementById('trx-sorted-sec'), sortedH = document.getElementById('trx-sorted-h'), sortedM = document.getElementById('trx-sorted-m');
  var countEl = document.getElementById('trx-count'), chipsEl = document.getElementById('trx-chips');
  var clearBtn = document.getElementById('trx-clear'), msgEl = document.getElementById('trx-msg'), noneEl = document.getElementById('trx-none');
  if (!form || !q || !results || !sortedUl || !countEl || !chipsEl || !clearBtn || !msgEl || !noneEl) return;
  var actBtns = Array.prototype.slice.call(form.querySelectorAll('.trx-acts [role="radio"]'));
  var viewBtns = Array.prototype.slice.call(form.querySelectorAll('.trx-view [role="radio"]'));
  var sel = { region: form.querySelector('select[name="region"]'), year: form.querySelector('select[name="year"]'),
    month: form.querySelector('select[name="month"]'), format: form.querySelector('select[name="format"]'), sort: form.querySelector('select[name="sort"]') };
  var chk = form.querySelector('input[name="writeup"]'), pchk = form.querySelector('input[name="photos"]');
  var moreN = form.querySelector('.trx-more-n');
  var groups = Array.prototype.slice.call(results.querySelectorAll('.trx-yr'));
  var cards = Array.prototype.slice.call(results.querySelectorAll('.tcard'));
  var origin = cards.map(function (c) { return c.parentNode; });   // each card's year list, for the newest order
  var total = cards.length;
  function optionValues(s) { return s ? Array.prototype.map.call(s.options, function (o) { return o.value; }) : []; }
  function optionNames(s) { var m = {}; if (s) Array.prototype.forEach.call(s.options, function (o) { m[o.value] = o.textContent; }); return m; }
  var allowed = { activity: actBtns.map(function (b) { return b.dataset.filter; }), region: optionValues(sel.region), year: optionValues(sel.year),
    month: optionValues(sel.month), format: optionValues(sel.format), sort: optionValues(sel.sort), view: viewBtns.map(function (b) { return b.dataset.view; }) };
  var names = { activity: {}, region: optionNames(sel.region), year: optionNames(sel.year), month: optionNames(sel.month), format: optionNames(sel.format) };
  actBtns.forEach(function (b) { names.activity[b.dataset.filter] = b.querySelector('.fchip-l').textContent; });
  var hash = location.hash;                       // read before the first write() canonicalises the URL
  // the form is on screen before this script arrives (core.reveal): what the visitor typed or chose in it meanwhile is
  // taken over (adoptForm), unless the address says otherwise
  var found = { q: q.value, writeup: !!(chk && chk.checked), photos: !!(pchk && pchk.checked) };
  SELECTS.forEach(function (k) { if (sel[k]) found[k] = sel[k].value; });
  var traversal = false;                          // reached by Back / Forward: the browser may have filled the form itself
  try {
    var nav = performance.getEntriesByType('navigation')[0];
    traversal = nav ? nav.type === 'back_forward' : performance.navigation.type === 2;
  } catch (e) { /* no Performance API: a first visit */ }
  var fromUrl = parseState(location.search, allowed);
  var userSort = ownSort(fromUrl, found, traversal);   // a sort the visitor chose (or shared) is kept; otherwise a query means best match
  var state = adoptForm(fromUrl, found, traversal);
  var index = null, indexState = 'idle', failedFor = null;   // idle | loading | ready | failed (failedFor: see stillFailed)
  var excerpts = {};                              // slug -> the card's own excerpt text, restored when a snippet goes
  var timer = null, lastPush = 0;
  // journal days: listed only while searching; the section is absent when no journal has a day to search
  var daysSec = document.getElementById('trx-days'), daysList = document.getElementById('trx-days-l');
  var daysN = document.getElementById('trx-days-n'), daysMore = document.getElementById('trx-days-more');
  if (!daysList || !daysN || !daysMore) daysSec = null;
  var days = null, daysState = daysSec ? 'idle' : 'none';   // none | idle | loading | ready | failed
  var daysAll = false, daysAllFor = null;         // 'Show all' belongs to one query: any other starts from the short list
  var daysFailedFor = null;                       // the query the journal index failed on (stillFailed, as failedFor)
  var lastSearch = location.search;              // the query string of the view on screen (write() and popstate keep it)
  // History (historyStep): entryUrl is the address this history entry stood for when the visitor last settled on it,
  // nowUrl the address it carries at this moment (typing rewrites it). Both are kept in the page's own spelling, as
  // address() builds them, and never read back from location: the browser spells an apostrophe as %27, and a search for
  // lover's would then look like a new view at every Enter.
  var entryUrl = null, nowUrl = null;
  var bySlug = {};
  cards.forEach(function (c) { bySlug[c.dataset.slug] = c; });

  function message(text) { if (msgEl.textContent !== (text || '')) msgEl.textContent = text || ''; msgEl.hidden = !text; }
  // quiet: fetched ahead of a search (warm), so nothing is said: nothing has been asked yet
  function loadIndex(done, quiet) {
    indexState = 'loading';
    if (!quiet) message(LOADING);
    var ok = function (data) { index = data; indexState = 'ready'; done(); };
    var fail = function () { indexState = 'failed'; failedFor = state.q; done(); };
    if (typeof fetch !== 'function') { fail(); return; }
    fetch('search.json', { credentials: 'same-origin' }).then(function (r) {
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    }).then(ok, fail);
  }
  // a journal index that does not load costs only the day results: the trip search and the filters carry on
  // The status line waits for this index (pending), so the wait is bounded: after DAYS_WAIT ms the request is given up
  // as failed and the reports' count is shown without the journal days.
  var DAYS_WAIT = 8000;
  function loadDays(done) {
    daysState = 'loading';
    var settled = false, timer = null;
    var fail = function () { if (settled) return; settled = true; clearTimeout(timer); daysState = 'failed'; daysFailedFor = state.q; done(); };
    var ok = function (data) { if (settled) return; settled = true; clearTimeout(timer); days = data; daysState = 'ready'; done(); };
    if (typeof fetch !== 'function') { fail(); return; }
    var opts = { credentials: 'same-origin' }, ctl = typeof AbortController === 'function' ? new AbortController() : null;
    if (ctl) opts.signal = ctl.signal;
    timer = setTimeout(function () { if (ctl) ctl.abort(); fail(); }, DAYS_WAIT);
    fetch(daysSec.getAttribute('data-index') || 'journal.json', opts).then(function (r) {
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    }).then(ok, fail);
  }
  function renderDays(list, toks) {
    if (!daysSec) return;
    if (daysAllFor !== state.q) { daysAll = false; daysAllFor = state.q; }
    while (daysList.firstChild) daysList.removeChild(daysList.firstChild);
    daysListed(list, daysAll).forEach(function (e) {
      var li = document.createElement('li'), a = document.createElement('a');
      var m = document.createElement('span'), t = document.createElement('span');
      li.className = 'trx-day';
      a.className = 'trx-day-a';
      a.setAttribute('href', dayHref(e));
      m.className = 't-mono-s trx-day-m';
      m.textContent = dayMeta(e);
      t.className = 'trx-day-t';
      t.textContent = e.h || ('Day ' + e.n);
      a.appendChild(m); a.appendChild(t); li.appendChild(a);
      var text = dayText(e, toks);
      if (text) {
        var p = document.createElement('p');
        p.className = 't-excerpt trx-day-x';
        p.textContent = text;
        li.appendChild(p);
      }
      daysList.appendChild(li);
    });
    daysSec.hidden = list.length === 0;
    daysN.textContent = daysHead(list.length);
    var more = daysMoreText(list.length, daysAll);
    daysMore.hidden = !more;
    daysMore.textContent = more;
    daysMore.setAttribute('aria-expanded', String(daysAll));
  }
  function searching() { return tokens(state.q).length > 0; }
  // the sort that goes with the search box as it is now: best match while it holds words, unless the visitor chose a
  // sort; without words, never best match (clearedSort), however the box was emptied or the address arrived
  function sortForSearch() {
    if (searching()) { if (!userSort) state.sort = 'relevance'; return; }
    var kept = clearedSort(state.sort, userSort);
    state.sort = kept[0];
    userSort = kept[1];
  }
  function anyFilter() {
    // the query counts as a filter only once the index has answered it (while it loads or after it failed nothing is hidden)
    return (searching() && indexState === 'ready') || FACETS.some(function (k) { return state[k] !== DEFAULTS[k]; });
  }
  function setControls() {
    if (q.value !== state.q) q.value = state.q;
    actBtns.forEach(function (b) { var on = b.dataset.filter === state.activity; b.setAttribute('aria-checked', String(on)); b.tabIndex = on ? 0 : -1; });
    ['region', 'year', 'month', 'format', 'sort'].forEach(function (k) { if (sel[k]) sel[k].value = state[k]; });
    if (chk) chk.checked = state.writeup;
    if (pchk) pchk.checked = state.photos;
    viewBtns.forEach(function (b) { var on = b.dataset.view === state.view; b.setAttribute('aria-checked', String(on)); b.tabIndex = on ? 0 : -1; });
    results.classList.toggle('trx--list', state.view === 'list');
    listImages(state.view === 'list');
  }
  // the list view's thumbnail is at most 200 px wide: its images take the candidates and the slot core.cover_img wrote
  // for it (data-srcset-list, data-sizes-list) and give back the card's own on the way back to the cards
  var listed = false;
  function listImages(on) {
    if (on === listed) return;
    listed = on;
    Array.prototype.forEach.call(results.querySelectorAll('img[data-srcset-list]'), function (img) {
      if (on) {
        if (!img.hasAttribute('data-srcset-card')) { img.setAttribute('data-srcset-card', img.getAttribute('srcset') || ''); img.setAttribute('data-sizes-card', img.getAttribute('sizes') || ''); }
        img.setAttribute('sizes', img.getAttribute('data-sizes-list'));
        img.setAttribute('srcset', img.getAttribute('data-srcset-list'));
      } else if (img.hasAttribute('data-srcset-card')) {
        img.setAttribute('sizes', img.getAttribute('data-sizes-card'));
        img.setAttribute('srcset', img.getAttribute('data-srcset-card'));
      }
    });
  }
  function chip(key, label) {
    var li = document.createElement('li'), b = document.createElement('button');
    b.type = 'button';
    b.className = 'trx-chip';
    b.setAttribute('aria-label', 'Remove filter: ' + label);
    b.appendChild(document.createTextNode(label));
    var x = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    x.setAttribute('class', 'ic'); x.setAttribute('viewBox', '0 0 24 24'); x.setAttribute('aria-hidden', 'true');
    var p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', 'M5.5 5.5l13 13M18.5 5.5l-13 13'); p.setAttribute('fill', 'none'); p.setAttribute('stroke', 'currentColor'); p.setAttribute('stroke-width', '1.75');
    x.appendChild(p); b.appendChild(x);
    b.addEventListener('click', function () {
      state[key] = DEFAULTS[key];
      if (key === 'q') { var kept = clearedSort(state.sort, userSort); state.sort = kept[0]; userSort = kept[1]; }
      apply('pick');
      q.focus();
    });
    li.appendChild(b);
    return li;
  }
  // a snippet replaces the card's excerpt (and hides its DAY N label, which belongs to the excerpt, not the hit)
  function setExcerpt(card, text) {
    var ex = card.querySelector('.tcard-ex'), lab = card.querySelector('.tcard-exl');
    if (!ex) return;
    var slug = card.dataset.slug;
    if (!(slug in excerpts)) excerpts[slug] = ex.textContent;
    var want = text == null ? excerpts[slug] : text;
    if (ex.textContent !== want) ex.textContent = want;
    if (lab) lab.hidden = text != null;
  }
  function render() {
    var toks = tokens(state.q);
    var useQ = toks.length > 0 && indexState === 'ready';
    // while a search waits for either index the count below is not rewritten, so the note says why
    var wait = pending(toks.length > 0, indexState, daysState);
    message(noteText(toks.length > 0, indexState, daysState));
    var hits = {};
    if (useQ) index.forEach(function (e) { if (match(e, toks)) hits[e.s] = e; });
    var shown = [];
    cards.forEach(function (c, i) {
      var d = c.dataset, on = facetOk(d, state);
      if (on && useQ && !hits[d.slug]) on = false;
      c.hidden = !on;
      var e = on && useQ ? hits[d.slug] : null;
      // a hit only in the write-up shows the words around it; everything else keeps the card's own excerpt
      var bodyOnly = e && toks.every(function (t) { return !has(e.t + ' ' + e.p + ' ' + e.k, t); });
      setExcerpt(c, bodyOnly ? (snippet(e.r, toks) || null) : null);
      if (on) shown.push({ el: c, i: i, score: e ? score(e, toks) : 0, date: d.date || '', kind: d.kind,
        value: state.sort === 'longest' ? (d.km || '') : state.sort === 'gain' ? (d.gain || '') : '' });
    });
    var sort = state.sort;
    if (sort === 'relevance' && !useQ) sort = 'newest';
    if (sortedM && sort === 'newest' && sortedM.textContent) sortedM.textContent = '';
    if (sort === 'newest') {
      // back from another sort: every card returns in page order (re-appending only the moved ones would leave them after
      // the cards a filter had kept in place). Nothing moves when nothing is out of place.
      if (cards.some(function (c, i) { return c.parentNode !== origin[i]; })) cards.forEach(function (c, i) { origin[i].appendChild(c); });
      if (sortedSec) sortedSec.hidden = true; else sortedUl.hidden = true;
      groups.forEach(function (g) {
        var vis = Array.prototype.filter.call(g.querySelectorAll('.tcard'), function (c) { return !c.hidden; }).length;
        g.hidden = vis === 0;
        var n = g.querySelector('.trx-yr-n');
        if (n) n.textContent = vis + (vis === 1 ? ' REPORT' : ' REPORTS');
      });
    } else {
      shown.sort(sort === 'oldest'
        ? function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : b.i - a.i; }
        : (sort === 'longest' || sort === 'gain') ? byValue
          : function (a, b) { return b.score - a.score || (a.date > b.date ? -1 : a.date < b.date ? 1 : a.i - b.i); });
      shown.forEach(function (x) { sortedUl.appendChild(x.el); });
      groups.forEach(function (g) { g.hidden = true; });
      if (sortedH) sortedH.textContent = SORTED_HEAD[sort] || 'Results';
      if (sortedM) {
        var meta = sortedMeta(sort, shown.filter(function (x) { return x.value === ''; }).length, shown.some(function (x) { return x.kind !== 'trip'; }));
        if (sortedM.textContent !== meta) sortedM.textContent = meta;
      }
      // no report matches: no empty 'Best match first' head above nothing (journal days may still be listed)
      if (sortedSec) sortedSec.hidden = shown.length === 0; else sortedUl.hidden = shown.length === 0;
    }
    var k = shown.length;
    // the journal days the query finds, filtered like their journal's own card
    var dayList = [];
    if (toks.length && daysState === 'ready') {
      dayList = dayHits(days, toks).filter(function (e) { var c = bySlug[e.s]; return dayShown(e, !!c && facetOk(c.dataset, state), state.writeup) && dayFacets(e, state); });
    }
    renderDays(dayList, toks);
    // the count, then the journal days as a link to their list under the reports (rewritten only when it changes, so
    // the live region speaks once per result)
    var reportsText = countText(k, total, anyFilter()), jdText = daysCount(dayList.length);
    if (!wait && countEl.textContent !== reportsText + (jdText ? ' · ' + jdText : '')) {
      countEl.textContent = reportsText;
      if (jdText) {
        var jump = document.createElement('a');
        jump.setAttribute('href', '#trx-days');
        jump.textContent = jdText;
        jump.addEventListener('click', toDays);
        countEl.appendChild(document.createTextNode(' · '));
        countEl.appendChild(jump);
      }
    }
    while (chipsEl.firstChild) chipsEl.removeChild(chipsEl.firstChild);
    ['q'].concat(FACETS).forEach(function (key) {
      var v = state[key];
      if (key === 'writeup' ? !v : (v === DEFAULTS[key] || !v)) return;
      if (key === 'q' && !tokens(v).length) return;   // '!!!' or spaces search nothing, so they are not a filter
      chipsEl.appendChild(chip(key, chipLabel(key, v, names)));
    });
    clearBtn.hidden = !(searching() || anyFilter());
    noneEl.hidden = wait || k > 0 || dayList.length > 0;
    if (moreN) { var nMore = X.moreCount(state, DEFAULTS, MORE), tMore = nMore ? ' \u00b7 ' + nMore : ''; if (moreN.textContent !== tMore) moreN.textContent = tMore; }
    // nothing found: the search without the filters and the filters without the search, counted over the same cards
    var offers = [];
    if (!noneEl.hidden && useQ) {
      var bare = {};
      FACETS.forEach(function (key) { bare[key] = DEFAULTS[key]; });
      var noFacets = cards.filter(function (c) { return !!hits[c.dataset.slug] && facetOk(c.dataset, Object.assign({}, state, bare)); }).length;
      var noQuery = cards.filter(function (c) { return facetOk(c.dataset, state); }).length;
      var noFacetDays = toks.length && daysState === 'ready' ? dayHits(days, toks).filter(function (e) { return !!bySlug[e.s]; }).length : 0;
      offers = relaxOffers(state, noFacets, noQuery, names, noFacetDays);
    }
    showOffers(offers);
  }
  // the buttons of the empty state that apply a nearest view (relaxOffers); built as text, never HTML
  var offersEl = null;
  function showOffers(offers) {
    if (!offers.length && !offersEl) return;
    if (!offersEl) {
      offersEl = document.createElement('div');
      offersEl.className = 'trx-relax';
      noneEl.insertBefore(offersEl, noneEl.querySelector('[data-clear]'));
    }
    while (offersEl.firstChild) offersEl.removeChild(offersEl.firstChild);
    offers.forEach(function (o) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'btn trx-relax-b';
      b.textContent = o.text;
      b.addEventListener('click', takeOffer.bind(null, o.kind));
      offersEl.appendChild(b);
    });
    offersEl.hidden = !offers.length;
  }
  // 'facets': every filter back to its default, the search kept; 'query': the search emptied (and its automatic sort
  // with it, as the search chip does), the filters kept
  function takeOffer(kind) {
    if (kind === 'facets') FACETS.forEach(function (key) { state[key] = DEFAULTS[key]; });
    else { state.q = DEFAULTS.q; var kept = clearedSort(state.sort, userSort); state.sort = kept[0]; userSort = kept[1]; }
    apply('pick');
    q.focus();
  }
  // the status line's link to the journal days: scrolled to and focused by script. As a fragment in the address it would
  // not survive a reload or a share, because the list is filled only after its index has loaded.
  function toDays(e) {
    if (!daysSec || daysSec.hidden) return;
    e.preventDefault();
    daysSec.scrollIntoView();
    var h = document.getElementById('trx-days-h');
    if (h) h.focus({ preventScroll: true });
  }
  // the canonical URL for the state, without a fragment
  function address() {
    var qs = serialize(state);
    return location.pathname + (qs ? '?' + qs : '');
  }
  // the fragment is kept on the first (load-time) write and dropped once the visitor acts. kind: 'type', 'pick' or
  // 'submit' (historyStep); settle: this write is what the entry now stands for (load)
  function write(kind, keepHash, settle) {
    var next;
    try { next = address(); } catch (e) { return; }
    if (entryUrl === null) entryUrl = nowUrl = next;   // the first write: the entry stands for the view the page opened on
    var step = historyStep(kind, entryUrl, nowUrl, next, Date.now() - lastPush < 600);
    try {
      if (step.restore) history.replaceState(null, '', entryUrl);
      history[step.push ? 'pushState' : 'replaceState'](null, '', next + (keepHash ? location.hash : ''));
      if (step.push) lastPush = Date.now();
      lastSearch = location.search;   // the browser's own spelling: it writes an apostrophe as %27
      nowUrl = next;
      // every deliberate change is what the entry now stands for, also a pick that rewrote the entry made a moment ago
      // (arrow keys through the activities); only typing leaves it standing for the view from before
      if (step.push || settle || kind !== 'type') entryUrl = next;
    } catch (e) { /* file:// */ }
  }
  // fetch what the search on screen needs: each index once, and again after a failure only when the query has changed
  function ask() {
    failedFor = stillFailed(failedFor, state.q);
    daysFailedFor = stillFailed(daysFailedFor, state.q);
    if (mayLoad(indexState, failedFor, state.q)) loadIndex(render);
    if (mayLoad(daysState, daysFailedFor, state.q)) loadDays(render);
  }
  // the indexes are fetched as soon as the visitor turns to the search (the box takes the focus, the form a press), so
  // the first results do not wait for two requests after the typing has begun. Each index once (the states guard it);
  // a failure is remembered as for a search (failedFor) and asked again with the next search words. Nothing is said.
  function warm() {
    if (indexState === 'idle') loadIndex(render, true);
    if (daysState === 'idle') loadDays(render);
  }
  function apply(kind, keepHash, settle) {
    setControls();
    ask();
    render();
    write(kind, keepHash, settle);
  }
  function clearAll() {
    state.q = DEFAULTS.q;
    FACETS.forEach(function (k) { state[k] = DEFAULTS[k]; });
    var kept = clearedSort(state.sort, userSort);
    state.sort = kept[0];
    userSort = kept[1];
    apply('pick');
    q.focus();
  }
  function focusSearch() { q.focus(); form.scrollIntoView({ block: 'start' }); }

  form.hidden = false;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    clearTimeout(timer);
    state.q = q.value;
    sortForSearch();
    apply('submit');
  });
  q.addEventListener('focus', warm);
  form.addEventListener('pointerdown', warm, { passive: true });
  form.addEventListener('touchstart', warm, { passive: true });
  q.addEventListener('input', function () {
    clearTimeout(timer);
    // noted at once, not after the pause below: a box emptied and filled again within it has still been changed
    failedFor = stillFailed(failedFor, q.value);
    daysFailedFor = stillFailed(daysFailedFor, q.value);
    timer = setTimeout(function () {
      state.q = q.value;
      sortForSearch();
      apply('type');
    }, 150);
  });
  if (daysSec) daysMore.addEventListener('click', function () { daysAll = !daysAll; render(); });
  actBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.activity === b.dataset.filter) return; state.activity = b.dataset.filter; apply('pick'); }); });
  viewBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.view === b.dataset.view) return; state.view = b.dataset.view; apply('pick'); }); });
  ['region', 'year', 'month', 'format'].forEach(function (k) { if (sel[k]) sel[k].addEventListener('change', function () { state[k] = sel[k].value; apply('pick'); }); });
  // any choice in the sort menu, Newest first included, is the visitor's and stays while they type
  if (sel.sort) sel.sort.addEventListener('change', function () { state.sort = sel.sort.value; userSort = true; apply('pick'); });
  if (chk) chk.addEventListener('change', function () { state.writeup = chk.checked; apply('pick'); });
  if (pchk) pchk.addEventListener('change', function () { state.photos = pchk.checked; apply('pick'); });
  clearBtn.addEventListener('click', clearAll);
  Array.prototype.forEach.call(noneEl.querySelectorAll('[data-clear]'), function (b) { b.addEventListener('click', clearAll); });
  window.addEventListener('popstate', function () {
    // a jump back to or from a fragment (a year link) is not a change of view: re-reading the URL would take the
    // automatic sort it carries for the visitor's own choice. The entry the visitor is on now stands for that view
    if (location.search === lastSearch) { entryUrl = nowUrl; return; }
    lastSearch = location.search;
    state = parseState(location.search, allowed);
    userSort = state.sort !== DEFAULTS.sort;
    var arrived = state.sort;
    if (!searching()) sortForSearch();                // an address with sort=relevance and no search
    try {
      entryUrl = nowUrl = address();                  // the entry stands for what it shows
      // and its address says so: an entry that carried Best match without a search (the visitor picked it from the menu
      // with an empty box) is rewritten, as the load rewrites such an address, so the menu and the address agree
      if (state.sort !== arrived) { history.replaceState(null, '', nowUrl + location.hash); lastSearch = location.search; }
    } catch (e) { /* keep what was */ }
    setControls();
    ask();
    render();
  });
  // the header's Search link is trips/#search: focus the box after the first render (a same-page click too)
  window.addEventListener('hashchange', function () {
    // a year link made a new entry for the view on screen: that view is what the entry stands for
    entryUrl = nowUrl;
    if (location.hash === '#search') focusSearch();
  });
  if (!searching()) sortForSearch();   // an address that arrives with sort=relevance and no search
  apply('type', true, true);
  if (hash === '#search') {
    focusSearch();
    // the browser's own jump to the fragment runs after deferred scripts and moves focus off the box again: refocus after load
    if (document.readyState !== 'complete') window.addEventListener('load', function () { setTimeout(focusSearch, 0); }, { once: true });
  }
})();
