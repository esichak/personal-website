/* Shared helpers for the filterable lists (trips/ and tick-list/): text normalisation that mirrors
   tools/sitegen/search.py, the query-string state (parseState / serialize), matching and scoring over an index entry, a
   snippet around a hit, and chip labels. Pure functions: no DOM. In the bundle they are window.Explore; under Node
   (tests/trips_js_harness.js, tests/ticklist_js_harness.js) the file is a module. */
(function () {
  'use strict';
  // mirrors tools/sitegen/search.py normalize() exactly: NFKD, the U+0300–036F combining marks dropped, lower-case,
  // anything but a–z / 0–9 is a space
  function norm(s) {
    s = String(s == null ? '' : s).normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();
    return s.replace(/[^a-z0-9]+/g, ' ').trim();
  }
  function tokens(q) { return norm(q).split(' ').filter(Boolean); }
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
    return toks.every(function (t) { return all.indexOf(t) !== -1; });
  }
  function score(e, toks) {
    var n = 0;
    toks.forEach(function (t) {
      if ((e.t || '').indexOf(t) !== -1) n += 3;
      if ((e.p || '').indexOf(t) !== -1 || (e.k || '').indexOf(t) !== -1) n += 2;
      if ((e.x || '').indexOf(t) !== -1) n += 1;
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
        if (w.indexOf(toks[j]) !== -1) {
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
  var Explore = { norm: norm, tokens: tokens, parseState: parseState, serialize: serialize, match: match, score: score, snippet: snippet, chipLabel: chipLabel };
  if (typeof module === 'object' && module && module.exports) module.exports = Explore;
  else if (typeof window !== 'undefined') window.Explore = Explore;
})();
