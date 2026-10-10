/* Tick list (/tick-list/): search and filters over the goal cards' data attributes (no index to fetch), a scope (active /
   shortlisted / completed / archived / all), priority / newest / name order, cards or list, and the state in the URL as
   on trips/. Pure parts (TKL) are exported for the Node test (tests/ticklist_js_harness.js); explore.js supplies the
   shared helpers. Without JavaScript the page is the full list by region. */
(function () {
  'use strict';
  var X = (typeof module === 'object' && module && module.exports) ? require('./explore.js') : window.Explore;
  var DEFAULTS = { q: '', activity: 'all', region: '', status: '', priority: '', month: '', gpx: false, scope: 'active', sort: 'priority', view: 'cards' };
  var KEYS = ['q', 'activity', 'region', 'status', 'priority', 'month', 'gpx', 'scope', 'sort', 'view'];
  var FACETS = ['activity', 'region', 'status', 'priority', 'month', 'gpx'];
  var LABELS = { region: 'Region: ', status: 'Status: ', priority: 'Priority: ', month: 'Month: ', gpx: 'Has a route' };
  var RANK = { high: 0, normal: 1, someday: 2 };
  function parseState(search, allowed) { return X.parseState(search, allowed, DEFAULTS, KEYS); }
  function serialize(st) { return X.serialize(st, DEFAULTS, KEYS); }
  function chipLabel(key, value, names) { return X.chipLabel(key, value, names, LABELS); }
  // d: the card's facets {status, archived ('1'|'0')}; the scope is the tick list's main split
  function inScope(d, scope) {
    var archived = d.archived === '1';
    if (scope === 'all') return true;
    if (scope === 'archived') return archived;
    if (scope === 'completed') return d.status === 'completed';
    if (scope === 'shortlisted') return d.status === 'shortlisted' && !archived;
    return !archived && d.status !== 'completed';   // active
  }
  // records: {priority, added ('' when unknown), slug, title}
  function compare(sort) {
    if (sort === 'name') return function (a, b) { return a.title.localeCompare(b.title) || (a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : 0); };
    var byAdded = function (a, b) {
      if (a.added && b.added && a.added !== b.added) return a.added > b.added ? -1 : 1;   // newest first
      if (a.added && !b.added) return -1;
      if (!a.added && b.added) return 1;
      return a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : 0;
    };
    if (sort === 'added') return byAdded;
    return function (a, b) { return (RANK[a.priority] - RANK[b.priority]) || byAdded(a, b); };   // priority
  }
  function matches(text, toks) { return toks.every(function (t) { return text.indexOf(t) !== -1; }); }
  var TKL = { parseState: parseState, serialize: serialize, chipLabel: chipLabel, inScope: inScope, compare: compare, matches: matches, DEFAULTS: DEFAULTS, KEYS: KEYS, FACETS: FACETS };
  if (typeof module === 'object' && module && module.exports) { module.exports = TKL; return; }
  if (typeof document === 'undefined' || !document.body.classList.contains('p-ticklist')) return;

  // ------------------------------------------------------------ the page
  var form = document.getElementById('search'), q = document.getElementById('tkl-q');
  var results = document.getElementById('tkl-results'), sortedUl = document.getElementById('tkl-sorted');
  var sortedSec = document.getElementById('tkl-sorted-sec'), sortedH = document.getElementById('tkl-sorted-h');
  var countEl = document.getElementById('tkl-count'), chipsEl = document.getElementById('tkl-chips');
  var clearBtn = document.getElementById('tkl-clear'), noneEl = document.getElementById('tkl-none');
  if (!form || !q || !results || !sortedUl || !sortedSec || !countEl || !chipsEl || !clearBtn || !noneEl) return;
  var actBtns = Array.prototype.slice.call(form.querySelectorAll('.trx-acts:not(.tkl-scope) [role="radio"]'));
  var scopeBtns = Array.prototype.slice.call(form.querySelectorAll('.tkl-scope [role="radio"]'));
  var viewBtns = Array.prototype.slice.call(form.querySelectorAll('.trx-view [role="radio"]'));
  var sel = { region: form.querySelector('select[name="region"]'), status: form.querySelector('select[name="status"]'),
    priority: form.querySelector('select[name="priority"]'), month: form.querySelector('select[name="month"]'), sort: form.querySelector('select[name="sort"]') };
  var gpxBtn = form.querySelector('[data-toggle="gpx"]');   // a switch button, not a checkbox: nothing on the page persists
  var groups = Array.prototype.slice.call(results.querySelectorAll('.tkl-region'));
  var cards = Array.prototype.slice.call(results.querySelectorAll('.gcard'));
  var origin = cards.map(function (c) { return c.parentNode; });
  var total = cards.length;
  function optionValues(s) { return s ? Array.prototype.map.call(s.options, function (o) { return o.value; }) : []; }
  function optionNames(s) { var m = {}; if (s) Array.prototype.forEach.call(s.options, function (o) { m[o.value] = o.textContent; }); return m; }
  var allowed = { activity: actBtns.map(function (b) { return b.dataset.filter; }), region: optionValues(sel.region), status: optionValues(sel.status),
    priority: optionValues(sel.priority), month: optionValues(sel.month), scope: scopeBtns.map(function (b) { return b.dataset.scope; }),
    sort: optionValues(sel.sort), view: viewBtns.map(function (b) { return b.dataset.view; }) };
  var names = { activity: {}, region: optionNames(sel.region), status: optionNames(sel.status), priority: optionNames(sel.priority), month: optionNames(sel.month) };
  actBtns.forEach(function (b) { names.activity[b.dataset.filter] = b.querySelector('.fchip-l').textContent; });
  var hash = location.hash;
  var state = parseState(location.search, allowed);
  var timer = null, lastPush = 0;

  function anyFilter() { return X.tokens(state.q).length > 0 || FACETS.some(function (k) { return state[k] !== DEFAULTS[k]; }); }
  function setControls() {
    if (q.value !== state.q) q.value = state.q;
    var radio = function (btns, attr, value) { btns.forEach(function (b) { var on = b.dataset[attr] === value; b.setAttribute('aria-checked', String(on)); b.tabIndex = on ? 0 : -1; }); };
    radio(actBtns, 'filter', state.activity);
    radio(scopeBtns, 'scope', state.scope);
    radio(viewBtns, 'view', state.view);
    ['region', 'status', 'priority', 'month', 'sort'].forEach(function (k) { if (sel[k]) sel[k].value = state[k]; });
    if (gpxBtn) gpxBtn.setAttribute('aria-checked', String(state.gpx));
    results.classList.toggle('trx--list', state.view === 'list');
  }
  function chip(key, label) {
    var li = document.createElement('li'), b = document.createElement('button');
    b.type = 'button'; b.className = 'trx-chip';
    b.setAttribute('aria-label', 'Remove filter: ' + label);
    b.appendChild(document.createTextNode(label));
    var x = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    x.setAttribute('class', 'ic'); x.setAttribute('viewBox', '0 0 24 24'); x.setAttribute('aria-hidden', 'true');
    var p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', 'M5.5 5.5l13 13M18.5 5.5l-13 13'); p.setAttribute('fill', 'none'); p.setAttribute('stroke', 'currentColor'); p.setAttribute('stroke-width', '1.75');
    x.appendChild(p); b.appendChild(x);
    b.addEventListener('click', function () { state[key] = DEFAULTS[key]; apply(true); q.focus(); });
    li.appendChild(b);
    return li;
  }
  function render() {
    var toks = X.tokens(state.q);
    var shown = [];
    cards.forEach(function (c, i) {
      var d = c.dataset, on = inScope(d, state.scope);
      if (on && state.activity !== 'all' && d.act !== state.activity) on = false;
      if (on && state.region && d.region !== state.region) on = false;
      if (on && state.status && d.status !== state.status) on = false;
      if (on && state.priority && d.priority !== state.priority) on = false;
      if (on && state.month && (' ' + (d.months || '') + ' ').indexOf(' ' + state.month + ' ') === -1) on = false;
      if (on && state.gpx && d.gpx !== '1') on = false;
      if (on && toks.length && !matches(d.text || '', toks)) on = false;
      c.hidden = !on;
      if (on) shown.push({ el: c, i: i, priority: d.priority, added: d.added || '', slug: d.slug, title: (c.querySelector('.gcard-t') || c).textContent.trim() });
    });
    if (state.sort === DEFAULTS.sort) {
      cards.forEach(function (c, i) { if (c.parentNode !== origin[i]) origin[i].appendChild(c); });
      sortedSec.hidden = true;
      groups.forEach(function (g) {
        var vis = Array.prototype.filter.call(g.querySelectorAll('.gcard'), function (c) { return !c.hidden; }).length;
        g.hidden = vis === 0;
        var n = g.querySelector('.trx-yr-n');
        if (n) n.textContent = vis + (vis === 1 ? ' GOAL' : ' GOALS');
      });
    } else {
      shown.sort(compare(state.sort));
      shown.forEach(function (x) { sortedUl.appendChild(x.el); });
      groups.forEach(function (g) { g.hidden = true; });
      if (sortedH) sortedH.textContent = state.sort === 'added' ? 'Newest added first' : 'By name';
      sortedSec.hidden = false;
    }
    var k = shown.length;
    var text = (anyFilter() || state.scope !== 'all') ? k + ' OF ' + total + ' GOALS' : total + ' GOALS';
    if (countEl.textContent !== text) countEl.textContent = text;
    while (chipsEl.firstChild) chipsEl.removeChild(chipsEl.firstChild);
    ['q'].concat(FACETS).forEach(function (key) {
      var v = state[key];
      if (key === 'gpx' ? !v : (v === DEFAULTS[key] || !v)) return;
      chipsEl.appendChild(chip(key, chipLabel(key, v, names)));
    });
    clearBtn.hidden = !anyFilter();
    noneEl.hidden = k > 0;
  }
  function write(push, keepHash) {
    var qs;
    try { qs = serialize(state); } catch (e) { return; }
    var url = location.pathname + (qs ? '?' + qs : '') + (keepHash ? location.hash : '');
    if (push && Date.now() - lastPush < 600) push = false;
    try { history[push ? 'pushState' : 'replaceState'](null, '', url); if (push) lastPush = Date.now(); } catch (e) { /* file:// */ }
  }
  function apply(push, keepHash) { setControls(); render(); write(push, keepHash); }
  function clearAll() { state.q = ''; FACETS.forEach(function (k) { state[k] = DEFAULTS[k]; }); apply(true); q.focus(); }
  function focusSearch() { q.focus(); form.scrollIntoView({ block: 'start' }); }

  form.hidden = false;
  form.addEventListener('submit', function (e) { e.preventDefault(); clearTimeout(timer); var changed = state.q !== q.value; state.q = q.value; apply(changed); });
  q.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { state.q = q.value; apply(false); }, 150); });
  actBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.activity === b.dataset.filter) return; state.activity = b.dataset.filter; apply(true); }); });
  scopeBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.scope === b.dataset.scope) return; state.scope = b.dataset.scope; apply(true); }); });
  viewBtns.forEach(function (b) { b.addEventListener('click', function () { if (state.view === b.dataset.view) return; state.view = b.dataset.view; apply(true); }); });
  ['region', 'status', 'priority', 'month', 'sort'].forEach(function (k) { if (sel[k]) sel[k].addEventListener('change', function () { state[k] = sel[k].value; apply(true); }); });
  if (gpxBtn) gpxBtn.addEventListener('click', function () { state.gpx = !state.gpx; apply(true); });
  clearBtn.addEventListener('click', clearAll);
  Array.prototype.forEach.call(noneEl.querySelectorAll('[data-clear]'), function (b) { b.addEventListener('click', clearAll); });
  window.addEventListener('popstate', function () { state = parseState(location.search, allowed); setControls(); render(); });
  window.addEventListener('hashchange', function () { if (location.hash === '#search') focusSearch(); });
  apply(false, true);
  if (hash === '#search') {
    focusSearch();
    if (document.readyState !== 'complete') window.addEventListener('load', function () { setTimeout(focusSearch, 0); }, { once: true });
  }
})();
