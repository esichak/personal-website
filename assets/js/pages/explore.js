/* Shared helpers for the filterable lists (trips/ and tick-list/): text normalisation that mirrors
   tools/sitegen/search.py, the query-string state (parseState / serialize), matching and scoring over an index entry, a
   snippet around a hit, chip labels, and the rule for history entries (historyStep). Pure functions: no DOM. In the bundle they are window.Explore; under Node
   (tests/trips_js_harness.js, tests/ticklist_js_harness.js) the file is a module. */
(function () {
  'use strict';
  // mirrors tools/sitegen/search.py normalize() exactly: NFKD, the U+0300–036F combining marks dropped, lower-case,
  // apostrophes (' ’ ‘) dropped so a word keeps its letters together (lover's -> lovers), except after a one-letter word
  // elided onto the next (d'argentiere -> d argentiere), then anything but a–z / 0–9 is a space
  function norm(s) {
    s = String(s == null ? '' : s).normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();
    s = s.replace(/\b([a-z])['\u2019\u2018](?=[a-z])/g, '$1 ').replace(/['\u2019\u2018]/g, '');
    return s.replace(/[^a-z0-9]+/g, ' ').trim();
  }
  function tokens(q) { return norm(q).split(' ').filter(Boolean); }
  // a typed word is found where a word of the field starts with it ('tal' in 'tallac', 'ice' not in 'practice'): field
  // and token are normalised, so words are separated by single spaces
  function has(field, tok) { return (' ' + (field || '')).indexOf(' ' + tok) !== -1; }
  function decode(s) { try { return decodeURIComponent(s.replace(/\+/g, ' ')); } catch (e) { return null; } }
  // ?q=…&activity=… -> a state over `keys` with `defaults`; unknown keys are ignored, values outside `allowed` fall back to
  // the default; a boolean default reads '1' as true; q is free text (up to 200 code points)
  function parseState(search, allowed, defaults, keys) {
    var st = {};
    keys.forEach(function (k) { st[k] = defaults[k]; });
    var s = String(search || '');
    if (s.charAt(0) === '?') s = s.slice(1);
    s.split('&').forEach(function (pair) {
      if (!pair) return;
      var i = pair.indexOf('='), k = decode(i < 0 ? pair : pair.slice(0, i)), v = decode(i < 0 ? '' : pair.slice(i + 1));
      if (k === null || v === null || keys.indexOf(k) === -1) return;
      if (k === 'q') st.q = Array.from(v).slice(0, 200).join('');
      else if (typeof defaults[k] === 'boolean') st[k] = v === '1';
      else if (allowed && allowed[k] && allowed[k].indexOf(v) !== -1) st[k] = v;
    });
    return st;
  }
  // the canonical query string: only non-default keys, in `keys` order ('' for the default state)
  function serialize(st, defaults, keys) {
    var out = [];
    keys.forEach(function (k) {
      var v = st[k];
      if (typeof defaults[k] === 'boolean') { if (v) out.push(encodeURIComponent(k) + '=1'); return; }
      if (v === defaults[k] || v === '' || v == null) return;
      out.push(encodeURIComponent(k) + '=' + encodeURIComponent(v).replace(/%20/g, '+'));
    });
    return out.join('&');
  }
  function fields(e) { return (e.t || '') + ' ' + (e.p || '') + ' ' + (e.k || '') + ' ' + (e.x || ''); }
  function match(e, toks) {
    var all = fields(e);
    return toks.every(function (t) { return has(all, t); });
  }
  function score(e, toks) {
    var n = 0;
    toks.forEach(function (t) {
      if (has(e.t, t)) n += 3;
      if (has(e.p, t) || has(e.k, t)) n += 2;
      if (has(e.x, t)) n += 1;
    });
    return n;
  }
  // a few words of plain text around the first token hit (words compared in normalised form)
  function snippet(raw, toks, span) {
    var words = String(raw || '').split(/\s+/).filter(Boolean);
    span = span || 9;
    for (var i = 0; i < words.length; i++) {
      var w = norm(words[i]);
      for (var j = 0; j < toks.length; j++) {
        if (has(w, toks[j])) {
          var a = Math.max(0, i - span), b = Math.min(words.length, i + span + 1);
          return (a > 0 ? '… ' : '') + words.slice(a, b).join(' ') + (b < words.length ? ' …' : '');
        }
      }
    }
    return '';
  }
  // the text of a filter chip: names maps a facet's values to labels; labels maps a facet to its prefix ('Region: ') or,
  // for a boolean facet, to its whole label
  function chipLabel(key, value, names, labels) {
    var n = (names && names[key] && names[key][value]) || value;
    if (key === 'q') return 'Search: ' + value;
    var l = labels && labels[key];
    if (typeof value === 'boolean') return l || key;
    return (l || '') + n;
  }
  // how many of `keys` the state has off their default (the count on the phones' Filters button)
  function moreCount(st, defaults, keys) {
    return keys.filter(function (k) { return typeof defaults[k] === 'boolean' ? !!st[k] : st[k] !== defaults[k] && st[k] !== ''; }).length;
  }
  // When a search and filters together find nothing, the nearest views that do: the search without the filters, and
  // the filters without the search. noFacets / noQuery: how many items each would show (live counts, never an
  // estimate). Returns [{ kind: 'facets' | 'query', text }], each only when its count is above 0, and nothing without
  // both a search and a filter (Clear filters is then the one way on). names / labels: as for chipLabel; defaults /
  // facets: the page's state defaults and filter keys; noun: 'report' or 'goal'; days: the journal days the search
  // finds without the filters (the Trips page; counted in the first offer).
  function relaxOffers(st, noFacets, noQuery, names, labels, defaults, facets, noun, days) {
    var on = facets.filter(function (k) { return typeof defaults[k] === 'boolean' ? !!st[k] : st[k] !== defaults[k] && st[k] !== ''; });
    var out = [], q = String(st.q || '').trim();
    if (!tokens(st.q).length || !on.length) return out;
    var onlyAct = on.length === 1 && on[0] === 'activity';
    var many = function (k, before) { return k + ' ' + (before || '') + noun + (k === 1 ? '' : 's'); };
    var dayN = days > 0 ? days : 0, total = noFacets + dayN;
    if (total > 0) {
      var where = onlyAct ? 'in all activities' : on.length === 1 ? 'without ' + chipLabel(on[0], st[on[0]], names, labels) : 'without the filters';
      var what = (noFacets ? many(noFacets) : '') + (dayN ? (noFacets ? ' and ' : '') + dayN + ' journal day' + (dayN === 1 ? '' : 's') : '');
      out.push({ kind: 'facets', text: what + (total === 1 ? ' matches ' : ' match ') + '\u2018' + q + '\u2019 ' + where });
    }
    if (noQuery > 0) {
      var act = onlyAct ? String((names && names.activity && names.activity[st.activity]) || st.activity).toLowerCase() + ' ' : '';
      out.push({ kind: 'query', text: many(noQuery, act) + (onlyAct ? '' : ' with these filters,') + ' without the search' });
    }
    return out;
  }
  // What a change of view does to the browser's history. Typing rewrites the address of the current entry (no entry per
  // keystroke); a deliberate change makes one new entry. kind: 'type' (the pause after typing, or the first write on
  // load), 'pick' (a filter, the sort, the view, Clear all) or 'submit' (Enter in the search box). entry is the address
  // this history entry stood for when the visitor last settled on it, now its address at this moment, next the address
  // of the new view; recent: an entry was made a moment ago (arrow keys through a radio group make one, not one per
  // step). Returns { push, restore }. A pick always adds an entry. A submitted search adds one whenever the view differs
  // from the one the entry stood for, also when the pause has already written the typed words into the address; the
  // entry is then put back to what it stood for (restore) before the new one is made, so that Back returns to the view
  // from before the search and not to a second copy of its result.
  function historyStep(kind, entry, now, next, recent) {
    if (recent || kind === 'type') return { push: false, restore: false };
    if (kind === 'pick') return { push: true, restore: false };
    var push = next !== entry;
    return { push: push, restore: push && now !== entry };
  }
  var Explore = { norm: norm, tokens: tokens, has: has, parseState: parseState, serialize: serialize, match: match, score: score, snippet: snippet, chipLabel: chipLabel,
    relaxOffers: relaxOffers, moreCount: moreCount, historyStep: historyStep };
  if (typeof module === 'object' && module && module.exports) module.exports = Explore;
  else if (typeof window !== 'undefined') window.Explore = Explore;
})();
