/* Trips explorer (/trips/): text search over the build-time index (trips/search.json), combined filters (activity,
   region, year, format, has a write-up), newest / oldest / best-match order, cards or list, and the whole state in the
   URL (?q=…&activity=…) so a filtered view can be shared and Back / Forward restore it. Without JavaScript the page is
   the full list by year with the browse links; the form stays hidden. The pure parts come from explore.js (shared with
   tick-list/) and are re-exported as TRX for the Node unit test (tests/trips_js_harness.js). */
(function () {
  'use strict';
  var X = (typeof module === 'object' && module && module.exports) ? require('./explore.js') : window.Explore;  // the shared helpers
  var DEFAULTS = { q: '', activity: 'all', region: '', year: '', format: '', writeup: false, sort: 'newest', view: 'cards' };
  var KEYS = ['q', 'activity', 'region', 'year', 'format', 'writeup', 'sort', 'view'];
  var LABELS = { region: 'Region: ', year: 'Year: ', format: 'Format: ', writeup: 'Has a write-up' };
  var norm = X.norm, tokens = X.tokens, match = X.match, score = X.score, snippet = X.snippet;
  function parseState(search, allowed) { return X.parseState(search, allowed, DEFAULTS, KEYS); }
  function serialize(st) { return X.serialize(st, DEFAULTS, KEYS); }
  function chipLabel(key, value, names) { return X.chipLabel(key, value, names, LABELS); }
  var TRX = { norm: norm, tokens: tokens, parseState: parseState, serialize: serialize, match: match, score: score, snippet: snippet, chipLabel: chipLabel, DEFAULTS: DEFAULTS };
  if (typeof module === 'object' && module && module.exports) { module.exports = TRX; return; }
  if (typeof document === 'undefined' || !document.body.classList.contains('p-trips')) return;

  // ------------------------------------------------------------ the page
  var FACETS = ['activity', 'region', 'year', 'format', 'writeup'];  // the filters (q is the search; sort / view are not filters)
  var form = document.getElementById('search'), q = document.getElementById('trx-q');
  var results = document.getElementById('trx-results'), sortedUl = document.getElementById('trx-sorted');
  var sortedSec = document.getElementById('trx-sorted-sec'), sortedH = document.getElementById('trx-sorted-h');
  var countEl = document.getElementById('trx-count'), chipsEl = document.getElementById('trx-chips');
  var clearBtn = document.getElementById('trx-clear'), msgEl = document.getElementById('trx-msg'), noneEl = document.getElementById('trx-none');
  if (!form || !q || !results || !sortedUl || !countEl || !chipsEl || !clearBtn || !msgEl || !noneEl) return;
  var actBtns = Array.prototype.slice.call(form.querySelectorAll('.trx-acts [role="radio"]'));
  var viewBtns = Array.prototype.slice.call(form.querySelectorAll('.trx-view [role="radio"]'));
  var sel = { region: form.querySelector('select[name="region"]'), year: form.querySelector('select[name="year"]'),
    format: form.querySelector('select[name="format"]'), sort: form.querySelector('select[name="sort"]') };
  var chk = form.querySelector('input[name="writeup"]');
  var groups = Array.prototype.slice.call(results.querySelectorAll('.trx-yr'));
  var cards = Array.prototype.slice.call(results.querySelectorAll('.tcard'));
  var origin = cards.map(function (c) { return c.parentNode; });   // each card's year list, for the newest order
  var total = cards.length;
  function optionValues(s) { return s ? Array.prototype.map.call(s.options, function (o) { return o.value; }) : []; }
  function optionNames(s) { var m = {}; if (s) Array.prototype.forEach.call(s.options, function (o) { m[o.value] = o.textContent; }); return m; }
  var allowed = { activity: actBtns.map(function (b) { return b.dataset.filter; }), region: optionValues(sel.region), year: optionValues(sel.year),
    format: optionValues(sel.format), sort: optionValues(sel.sort), view: viewBtns.map(function (b) { return b.dataset.view; }) };
  var names = { activity: {}, region: optionNames(sel.region), year: optionNames(sel.year), format: optionNames(sel.format) };
  actBtns.forEach(function (b) { names.activity[b.dataset.filter] = b.querySelector('.fchip-l').textContent; });
  var hash = location.hash;                       // read before the first write() canonicalises the URL
  var state = parseState(location.search, allowed);
  var userSort = state.sort !== DEFAULTS.sort;    // a sort the visitor chose (or shared) is kept; otherwise a query means best match
  var index = null, indexState = 'idle', failedFor = null;   // idle | loading | ready | failed (failedFor: the query that failed)
  var excerpts = {};                              // slug -> the card's own excerpt text, restored when a snippet goes
  var timer = null, lastPush = 0;
  var FAIL = 'Search isn’t available right now (the search index didn’t load). The filters still work.';

  function message(text) { if (msgEl.textContent !== (text || '')) msgEl.textContent = text || ''; msgEl.hidden = !text; }
  function loadIndex(done) {
    indexState = 'loading';
    message('Loading search…');
    var ok = function (data) { index = data; indexState = 'ready'; done(); };
    var fail = function () { indexState = 'failed'; failedFor = state.q; done(); };
    if (typeof fetch !== 'function') { fail(); return; }
    fetch('search.json', { credentials: 'same-origin' }).then(function (r) {
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    }).then(ok, fail);
  }
  function searching() { return tokens(state.q).length > 0; }
  function anyFilter() {
    // the query counts as a filter only once the index has answered it (while it loads or after it failed nothing is hidden)
    return (searching() && indexState === 'ready') || FACETS.some(function (k) { return state[k] !== DEFAULTS[k]; });
  }
  function setControls() {
    if (q.value !== state.q) q.value = state.q;
    actBtns.forEach(function (b) { var on = b.dataset.filter === state.activity; b.setAttribute('aria-checked', String(on)); b.tabIndex = on ? 0 : -1; });
    ['region', 'year', 'format', 'sort'].forEach(function (k) { if (sel[k]) sel[k].value = state[k]; });
    if (chk) chk.checked = state.writeup;
    viewBtns.forEach(function (b) { var on = b.dataset.view === state.view; b.setAttribute('aria-checked', String(on)); b.tabIndex = on ? 0 : -1; });
    results.classList.toggle('trx--list', state.view === 'list');
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
      if (key === 'q' && !userSort) state.sort = DEFAULTS.sort;
      apply(true);
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
    if (indexState === 'failed') message(toks.length ? FAIL : '');
    else if (indexState === 'loading' && !toks.length) message('');
    else if (indexState === 'ready') message('');
    var hits = {};
    if (useQ) index.forEach(function (e) { if (match(e, toks)) hits[e.s] = e; });
    var shown = [];
    cards.forEach(function (c, i) {
      var d = c.dataset, on = true;
      if (state.activity !== 'all' && d.act !== state.activity) on = false;
      if (on && state.region && d.region !== state.region) on = false;
      if (on && state.year && d.year !== state.year) on = false;
      if (on && state.format && d.kind !== state.format) on = false;
      if (on && state.writeup && d.writeup !== '1') on = false;
      if (on && useQ && !hits[d.slug]) on = false;
      c.hidden = !on;
      var e = on && useQ ? hits[d.slug] : null;
      // a hit only in the write-up shows the words around it; everything else keeps the card's own excerpt
      var bodyOnly = e && toks.every(function (t) { return (e.t + ' ' + e.p + ' ' + e.k).indexOf(t) === -1; });
      setExcerpt(c, bodyOnly ? (snippet(e.r, toks) || null) : null);
      if (on) shown.push({ el: c, i: i, score: e ? score(e, toks) : 0, date: d.date || '' });
    });
    var sort = state.sort;
    if (sort === 'relevance' && !useQ) sort = 'newest';
    if (sort === 'newest') {
      cards.forEach(function (c, i) { if (c.parentNode !== origin[i]) origin[i].appendChild(c); });
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
        : function (a, b) { return b.score - a.score || (a.date > b.date ? -1 : a.date < b.date ? 1 : a.i - b.i); });
      shown.forEach(function (x) { sortedUl.appendChild(x.el); });
      groups.forEach(function (g) { g.hidden = true; });
      if (sortedH) sortedH.textContent = sort === 'oldest' ? 'Oldest first' : 'Best match first';
      if (sortedSec) sortedSec.hidden = false; else sortedUl.hidden = false;
    }
    var k = shown.length;
    var countText = anyFilter() ? k + ' OF ' + total + ' REPORTS' : total + ' REPORTS';
    if (countEl.textContent !== countText) countEl.textContent = countText;
    while (chipsEl.firstChild) chipsEl.removeChild(chipsEl.firstChild);
    ['q'].concat(FACETS).forEach(function (key) {
      var v = state[key];
      if (key === 'writeup' ? !v : (v === DEFAULTS[key] || !v)) return;
      chipsEl.appendChild(chip(key, chipLabel(key, v, names)));
    });
    clearBtn.hidden = !(searching() || anyFilter());
    noneEl.hidden = k > 0;
  }
  // the canonical URL for the state; the fragment is kept on the first (load-time) write and dropped once the visitor acts
  function write(push, keepHash) {
    var qs;
    try { qs = serialize(state); } catch (e) { return; }
    var url = location.pathname + (qs ? '?' + qs : '') + (keepHash ? location.hash : '');
    if (push && Date.now() - lastPush < 600) push = false;   // arrow keys through a radio group make one history entry, not one per step
    try {
      history[push ? 'pushState' : 'replaceState'](null, '', url);
      if (push) lastPush = Date.now();
    } catch (e) { /* file:// */ }
  }
  function apply(push, keepHash) {
    setControls();
    if (searching() && (indexState === 'idle' || (indexState === 'failed' && state.q !== failedFor))) loadIndex(render);
    render();
    write(push, keepHash);
  }
  function clearAll() {
    state.q = DEFAULTS.q;
    FACETS.forEach(function (k) { state[k] = DEFAULTS[k]; });
    if (!userSort) state.sort = DEFAULTS.sort;
    apply(true);
    q.focus();
  }
  function focusSearch() { q.focus(); form.scrollIntoView({ block: 'start' }); }

  form.hidden = false;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    clearTimeout(timer);
    var changed = state.q !== q.value;
    state.q = q.value;
    if (!userSort) state.sort = searching() ? 'relevance' : 'newest';
    apply(changed);
  });
  q.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      state.q = q.value;
      if (!userSort) state.sort = searching() ? 'relevance' : 'newest';
      apply(false);
    }, 150);
  });
  actBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.activity === b.dataset.filter) return; state.activity = b.dataset.filter; apply(true); }); });
  viewBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.view === b.dataset.view) return; state.view = b.dataset.view; apply(true); }); });
  ['region', 'year', 'format'].forEach(function (k) { if (sel[k]) sel[k].addEventListener('change', function () { state[k] = sel[k].value; apply(true); }); });
  // any choice in the sort menu, Newest first included, is the visitor's and stays while they type
  if (sel.sort) sel.sort.addEventListener('change', function () { state.sort = sel.sort.value; userSort = true; apply(true); });
  if (chk) chk.addEventListener('change', function () { state.writeup = chk.checked; apply(true); });
  clearBtn.addEventListener('click', clearAll);
  Array.prototype.forEach.call(noneEl.querySelectorAll('[data-clear]'), function (b) { b.addEventListener('click', clearAll); });
  window.addEventListener('popstate', function () {
    state = parseState(location.search, allowed);
    userSort = state.sort !== DEFAULTS.sort;
    setControls();
    if (searching() && (indexState === 'idle' || (indexState === 'failed' && state.q !== failedFor))) loadIndex(render);
    render();
  });
  // the header's Search link is trips/#search: focus the box after the first render (a same-page click too)
  window.addEventListener('hashchange', function () { if (location.hash === '#search') focusSearch(); });
  apply(false, true);
  if (hash === '#search') {
    focusSearch();
    // the browser's own jump to the fragment runs after deferred scripts and moves focus off the box again: refocus after load
    if (document.readyState !== 'complete') window.addEventListener('load', function () { setTimeout(focusSearch, 0); }, { once: true });
  }
})();
