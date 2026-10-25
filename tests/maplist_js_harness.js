#!/usr/bin/env node
'use strict';
/* Phase 5, round 3: the list beside a region map, as assets/js/base.js and assets/js/pages/archive.js drive it on the Map
   page and on a region page. Both scripts are run as they are, in the order the bundle has them, against a stand-in
   for the page, and a reader's pointer, focus and presses are played on it:

     highlight   base.js: pointing at (or focusing) a list row picks out its track, pin or cluster marker on the map and
                 dims the rest (the class is-hl on the map). A row whose trip the map does not draw (a region page lists
                 a report without a track, a journal, a report newer than the last render) leaves the map as it is.
     show all    archive.js: 'Show all N' opens the list and focuses the first row that came into view; 'Show fewer'
                 closes it and scrolls the button, which keeps the focus, into view (block: 'nearest'), and only then.
     both        a press on a cluster marker whose rows are hidden opens the list (base.js presses the button); the
                 button is not scrolled to.

   Phase 12 (maps on pages):

     clusters    rule D4 revised (tests/test_a11y_static.py): a cluster marker of a map with list rows is a named
                 toggle (aria-hidden removed; role=button, tabindex 0, aria-pressed, 'N reports start here', N counting
                 reports and never the planned route) with focus listeners; one of a map without rows (home) stays an
                 aria-hidden pointer target with none.
     press       qa-02: a press (click, Enter, Space) selects the cluster's rows (is-map-hl), sets the panel's other rows
                 aside (.is-off) and says 'N REPORTS START HERE · Show all' in the count line; a second press, Escape
                 or Show all clears and restores the line; a hover elsewhere returns to the selection.
     landing     gap4-01/02: an address naming a row (#arc-row-<slug>) opens a folded list, centres the row and focuses
                 its link (the cluster click's open, scroll, focus).
     legend      maps-07: each activity of the legend becomes a toggle that filters the rows (.is-actoff), dims the
                 markers of the other activities (.is-out) and says 'N of M reports'; its disc moves into the button.
     touch       gap1-03, under a matchMedia stub that answers '(hover: none)': the first tap on a pin or a line picks it
                 out and opens its row, a second tap follows the link, a tap on the map's paper clears; a map without
                 rows, and every map without (hover: none), is left alone.
     year folds  phone-03, under a stub that answers '(max-width: 759.98px)': every year of 'All reports' after the
                 first is folded behind 'Show N reports'; a year link, an address inside a year and the activity filter
                 unfold it.
     full screen qa-06: a region's full-screen map (.fs-map[data-fs="region"]) is centred on both axes and skips the
                 route logic.

   The CSS halo of a focused journal line (.mk-line:focus-visible .mk-hit) needs no script: tests/test_a11y_static.py
   reads it from base.css.

   Run by tests/test_maplist_js.py (skipped when node is missing); by hand:
     node tests/maplist_js_harness.js [base.js] [archive.js]
   The optional arguments point at other copies of the two scripts (used to prove the harness fails a wrong one). Every
   failed check prints 'FAIL <label>' on stderr and throws, so the process exits non-zero; a run without one ends with
   '<N> checks passed' on stdout.

   The stand-in is not a browser. It is a tree of elements with attributes, classList, dataset, listeners and a small
   selector matcher: a tag, classes, #id, [attr], [attr="value"] and [attr^="value"], joined by spaces (descendants),
   '>' (children) and commas. A selector it cannot read matches nothing, which is what the parts of base.js that have
   nothing to do on this page get (the units switch, the menu, the photo viewer). Events bubble from the target through
   its ancestors to the document, and preventDefault() is recorded. innerHTML is read and written through a small parser
   (tags, quoted attributes, text, &amp; &lt; &gt; &quot; &#39; &nbsp;). Rows are hidden as archive.css hides them:
   .arc-rows.arc-collapsed .arc-more, .arc-rows > li.is-off and .is-actoff, .arc-rows2.arc-collapsed. focus() on an
   element that is not rendered does nothing, as in a browser (it is logged as such); otherwise it moves
   document.activeElement and sends focusout and focusin, which bubble. Layout and real scrolling are not modelled:
   scrollIntoView() is only recorded. window.matchMedia answers false unless a check names the query.
   The page below is written by hand after the markup archive.region_panel (with archive.region_row, journal_row,
   legend and inject_acts) and archive.archive_section generate and tools/lib/mapkit.py draws (tests/test_region_page.py
   holds the generated page to those hooks: data-map-target, data-key, data-keys, data-kind, data-act, data-acts). */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const util = require('util');
const vm = require('vm');

const JS = path.join(__dirname, '..', 'assets', 'js');
const BASE = path.resolve(process.argv[2] || path.join(JS, 'base.js'));
const ARCHIVE = path.resolve(process.argv[3] || path.join(JS, 'pages', 'archive.js'));
assert.ok(fs.existsSync(BASE), 'missing ' + BASE);
assert.ok(fs.existsSync(ARCHIVE), 'missing ' + ARCHIVE);

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

// ---------------------------------------------------------------- the stand-in page

function parseCompound(text) {
  const head = /^([a-zA-Z][\w-]*|\*)?/.exec(text);
  const out = { tag: head[1] && head[1] !== '*' ? head[1].toUpperCase() : null, classes: [], attrs: [] };
  let rest = text.slice(head[0].length);
  const part = /^(?:\.([\w-]+)|#([\w-]+)|\[([\w-]+)(?:(\^?=)(?:"([^"]*)"|'([^']*)'))?\])/;
  while (rest) {
    const m = part.exec(rest);
    if (!m) return null;                       // not read: the selector then matches nothing
    if (m[1]) out.classes.push(m[1]);
    else if (m[2]) out.attrs.push(['id', m[2], '=']);
    else out.attrs.push([m[3], m[5] !== undefined ? m[5] : m[6], m[4]]);
    rest = rest.slice(m[0].length);
  }
  return out;
}
function parseSelector(sel) {
  // -> one chain of compounds per comma part, each compound with the combinator that joins it to the one before (' ' or
  // '>'); a chain with a part that is not read is dropped
  return String(sel).split(',').map((s) => {
    const chain = [];
    let comb = ' ';
    for (const tok of s.trim().replace(/\s*>\s*/g, ' > ').split(/\s+/)) {
      if (tok === '>') { comb = '>'; continue; }
      const c = parseCompound(tok);
      if (!c) return null;
      c.comb = comb;
      comb = ' ';
      chain.push(c);
    }
    return chain.length ? chain : null;
  }).filter(Boolean);
}
function hasCompound(el, c) {
  if (c.tag && el.tagName !== c.tag) return false;
  if (!c.classes.every((k) => el.classList.contains(k))) return false;
  return c.attrs.every(([name, value, op]) => el.hasAttribute(name)
    && (value === undefined || (op === '^=' ? el.getAttribute(name).startsWith(value) : el.getAttribute(name) === value)));
}
function hasChain(el, chain, i) {
  if (i === undefined) i = chain.length - 1;
  if (!hasCompound(el, chain[i])) return false;
  if (i === 0) return true;
  if (chain[i].comb === '>') return !!el.parentNode && hasChain(el.parentNode, chain, i - 1);
  for (let p = el.parentNode; p; p = p.parentNode) if (hasChain(p, chain, i - 1)) return true;
  return false;
}

class Text {
  constructor(value) { this.nodeValue = String(value); this.parentNode = null; }
  get textContent() { return this.nodeValue; }
}
function detach(node) {
  if (!node.parentNode) return;
  const sib = node.parentNode.childNodes;
  const i = sib.indexOf(node);
  if (i !== -1) sib.splice(i, 1);
  node.parentNode = null;
}

// innerHTML, both ways: what the scripts write (the count line, the year counts) is read back into elements
const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', '#39': "'", nbsp: '\u00a0' };
const decode = (s) => s.replace(/&(amp|lt|gt|quot|#39|nbsp);/g, (_m, k) => ENTITIES[k]);
const VOID = ['img', 'br', 'input', 'hr', 'source', 'meta', 'link'];
function parseInto(parent, html) {
  const stack = [parent];
  const tok = /<\/([a-zA-Z][\w-]*)\s*>|<([a-zA-Z][\w-]*)((?:\s+[^\s=>/]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?)*)\s*(\/?)>|([^<]+)/g;
  let m;
  while ((m = tok.exec(html))) {
    const top = stack[stack.length - 1];
    if (m[1]) {
      const name = m[1].toUpperCase();
      let i = stack.length - 1;
      while (i > 0 && stack[i].tagName !== name) i--;
      assert.ok(i > 0, 'a stray </' + m[1] + '> in ' + html.slice(0, 120));
      stack.length = i;
    } else if (m[2]) {
      const attrs = {};
      const at = /([^\s=>/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
      let a;
      while ((a = at.exec(m[3]))) attrs[a[1]] = decode([a[2], a[3], a[4], ''].filter((v) => v !== undefined)[0]);
      const el = parent.page.el(m[2], attrs);
      top.appendChild(el);
      if (!m[4] && VOID.indexOf(m[2].toLowerCase()) === -1) stack.push(el);
    } else {
      top.appendChild(new Text(decode(m[5])));
    }
  }
  assert.strictEqual(stack.length, 1, 'an unclosed <' + stack[stack.length - 1].tagName + '> in ' + html.slice(0, 120));
}
const escText = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
function serialize(node) {
  if (node instanceof Text) return escText(node.nodeValue);
  const tag = node.tagName.toLowerCase();
  const attrs = Object.keys(node.attrs).map((k) => ' ' + k + '="' + escText(node.attrs[k]).replace(/"/g, '&quot;') + '"').join('');
  return '<' + tag + attrs + '>' + (VOID.indexOf(tag) !== -1 ? '' : node.childNodes.map(serialize).join('') + '</' + tag + '>');
}

// an element in a few words, for the checks and for a failed assertion (which would otherwise print the whole page)
function who(el) {
  if (!el) return 'nothing';
  if (el.tagName === 'LI' && el.hasAttribute('data-key')) return 'row ' + el.getAttribute('data-key');
  if (el.tagName === 'A' && el.parentNode && el.parentNode.tagName === 'LI' && el.parentNode.hasAttribute('data-key')) {
    return 'the link of ' + who(el.parentNode);
  }
  if (el.classList.contains('mk-cluster')) return 'cluster ' + el.getAttribute('data-keys');
  if (el.classList.contains('mk-pin')) return 'pin ' + el.getAttribute('data-key');
  if (el.classList.contains('mk-line')) return 'line ' + el.getAttribute('data-key');
  if (el.tagName === 'BUTTON' && el.hasAttribute('aria-controls')) return 'the button of ' + el.getAttribute('aria-controls');
  return el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className ? '.' + el.className.split(' ').join('.') : '');
}

class El {
  constructor(page, tag, attrs, children) {
    this.page = page;
    this.tagName = tag.toUpperCase();
    this.attrs = Object.assign({}, attrs || {});
    this.childNodes = [];
    this.parentNode = null;
    this.listeners = {};
    this.tabIndex = -1;
    const self = this;
    const names = () => (self.attrs.class || '').split(/\s+/).filter(Boolean);
    const put = (list) => { self.attrs.class = list.join(' '); };
    this.classList = {
      contains: (k) => names().indexOf(k) !== -1,
      add: (k) => { if (names().indexOf(k) === -1) put(names().concat([k])); },
      remove: (k) => { put(names().filter((x) => x !== k)); },
      toggle: (k, force) => {
        const on = force === undefined ? names().indexOf(k) === -1 : !!force;
        if (on) self.classList.add(k); else self.classList.remove(k);
        return on;
      },
    };
    // el.dataset.mapTarget is the attribute data-map-target
    const dataName = (prop) => 'data-' + prop.replace(/[A-Z]/g, (ch) => '-' + ch.toLowerCase());
    this.dataset = new Proxy({}, { get: (_t, prop) => (typeof prop === 'string' ? self.attrs[dataName(prop)] : undefined) });
    (children || []).forEach((c) => this.appendChild(typeof c === 'string' ? new Text(c) : c));
  }
  [util.inspect.custom]() { return '<' + who(this) + '>'; }
  get id() { return this.attrs.id || ''; }
  set id(v) { this.attrs.id = String(v); }
  get className() { return this.attrs.class || ''; }
  set className(v) { this.attrs.class = String(v); }
  get hidden() { return 'hidden' in this.attrs; }
  set hidden(v) { if (v) this.attrs.hidden = ''; else delete this.attrs.hidden; }
  get firstChild() { return this.childNodes[0] || null; }
  get children() { return this.childNodes.filter((c) => c instanceof El); }
  get nextElementSibling() {
    if (!this.parentNode) return null;
    const sib = this.parentNode.children;
    return sib[sib.indexOf(this) + 1] || null;
  }
  get innerHTML() { return this.childNodes.map(serialize).join(''); }
  set innerHTML(html) { this.childNodes.slice().forEach(detach); parseInto(this, String(html)); }
  get textContent() { return this.childNodes.map((c) => c.textContent).join(''); }
  set textContent(v) { this.childNodes.slice().forEach(detach); if (String(v)) this.appendChild(new Text(v)); }
  // null for an element that is not rendered, as in a browser: hidden itself, inside something hidden, a row beyond the
  // first eight of a collapsed list, a row set aside, or a folded year (archive.css: .arc-rows.arc-collapsed .arc-more,
  // .arc-rows > li.is-off, .arc-rows > li.is-actoff, .arc-rows2.arc-collapsed { display: none; })
  get offsetParent() {
    for (let p = this; p; p = p.parentNode) {
      if (p.hidden) return null;
      const up = p.parentNode;
      if (up && up.classList.contains('arc-rows')) {
        if (p.classList.contains('arc-more') && up.classList.contains('arc-collapsed')) return null;
        if (p.tagName === 'LI' && (p.classList.contains('is-off') || p.classList.contains('is-actoff'))) return null;
      }
      if (p.classList.contains('arc-rows2') && p.classList.contains('arc-collapsed')) return null;
    }
    return this.page.body;
  }
  appendChild(child) { detach(child); child.parentNode = this; this.childNodes.push(child); return child; }
  removeChild(child) { detach(child); return child; }
  insertAdjacentElement(where, el) {
    if (where === 'beforeend') return this.appendChild(el);
    assert.strictEqual(where, 'afterend', 'insertAdjacentElement(' + where + ') is not modelled');
    detach(el);
    const sib = this.parentNode.childNodes;
    sib.splice(sib.indexOf(this) + 1, 0, el);
    el.parentNode = this.parentNode;
    return el;
  }
  hasAttribute(name) { return name in this.attrs; }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  removeAttribute(name) { delete this.attrs[name]; }
  contains(other) { for (let p = other; p; p = p.parentNode) if (p === this) return true; return false; }
  descendants() {
    const out = [];
    this.children.forEach((c) => { out.push(c); c.descendants().forEach((d) => out.push(d)); });
    return out;
  }
  matches(sel) { return parseSelector(sel).some((chain) => hasChain(this, chain)); }
  closest(sel) { for (let p = this; p; p = p.parentNode) if (p.matches(sel)) return p; return null; }
  querySelectorAll(sel) {
    const chains = parseSelector(sel);
    return this.descendants().filter((d) => chains.some((chain) => hasChain(d, chain)));
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); }
  // a browser focuses nothing that is not rendered; otherwise the focus moves and focusout / focusin bubble
  focus(options) {
    const page = this.page;
    if (this.offsetParent === null) { page.log.push({ did: 'focus refused (not rendered)', el: this, how: options }); return; }
    page.log.push({ did: 'focus', el: this, how: options });
    const was = page.activeElement;
    if (was === this) return;
    page.activeElement = this;
    if (was) page.send(was, 'focusout', true, { relatedTarget: this });
    page.send(this, 'focusin', true, { relatedTarget: was });
  }
  blur() { if (this.page.activeElement === this) { this.page.activeElement = null; this.page.send(this, 'focusout', true); } }
  scrollIntoView(options) { this.page.log.push({ did: 'scroll', el: this, how: options }); }
  click() { return this.page.send(this, 'click', true); }
}

class Page {
  // opts: media, the queries window.matchMedia answers true ({ '(hover: none)': true }); hash, the address's fragment
  constructor(bodyClass, opts) {
    opts = opts || {};
    this.log = [];                 // every focus() and scrollIntoView() a script called, in order
    this.listeners = {};           // the document's own
    this.windowListeners = {};
    this.media = opts.media || {};
    this.asked = [];               // every query a script handed to matchMedia
    this.mqls = {};                // the change listeners a script put on each query (turn() fires them)
    this.hash = opts.hash || '';
    this.activeElement = null;
    this.body = this.el('body', { class: bodyClass });
    this.documentElement = this.el('html', {}, [this.body]);
  }
  [util.inspect.custom]() { return '<the page>'; }
  el(tag, attrs, children) { return new El(this, tag, attrs, children); }
  createElement(tag) { return this.el(tag); }
  createTextNode(value) { return new Text(value); }
  addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); }
  querySelectorAll(sel) { return this.documentElement.querySelectorAll(sel); }
  querySelector(sel) { return this.documentElement.querySelector(sel); }
  getElementById(id) { return this.documentElement.descendants().filter((d) => d.attrs.id === id)[0] || null; }
  // one event: the target's own listeners, then (for an event that bubbles) its ancestors' and the document's. Returns
  // the event, so a check can ask whether a script prevented the default (a link followed, a key's own action)
  send(el, type, bubbles, extra) {
    const e = Object.assign({
      type: type, target: el, button: 0, defaultPrevented: false, stopped: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { this.stopped = true; },
    }, extra || {});
    const path = [el];
    if (bubbles) for (let p = el.parentNode; p; p = p.parentNode) path.push(p);
    for (const node of path) {
      e.currentTarget = node;
      (node.listeners[type] || []).slice().forEach((fn) => fn.call(node, e));
      if (e.stopped) return e;
    }
    if (bubbles) (this.listeners[type] || []).slice().forEach((fn) => fn.call(this, e));
    return e;
  }
  key(el, key) { return this.send(el, 'keydown', true, { key: key }); }
  // a query's answer changes (a tablet turned): its change listeners hear it
  turn(q, matches) { this.media[q] = matches; (this.mqls[q] || []).slice().forEach((fn) => fn({ matches: matches, media: q })); }
  // the window's listeners for one event ('load', 'hashchange'), as the browser would fire them
  fire(type) { (this.windowListeners[type] || []).slice().forEach((fn) => fn.call(this.context, { type: type })); }
  run(file) {
    if (!this.context) {
      const noop = () => {};
      const page = this;
      const sandbox = {
        document: this, location: { hash: this.hash, search: '', pathname: '/regions/synthetic-range/', href: 'https://example.test/regions/synthetic-range/' + this.hash },
        navigator: {}, history: { replaceState: noop }, localStorage: { getItem: () => null, setItem: noop },
        sessionStorage: { getItem: () => null, setItem: noop },
        requestAnimationFrame: (fn) => { fn(); }, setTimeout: (fn) => { fn(); }, clearTimeout: noop,
        addEventListener: (type, fn) => { (page.windowListeners[type] = page.windowListeners[type] || []).push(fn); },
        matchMedia: (q) => {
          page.asked.push(q);
          const keep = (fn) => { (page.mqls[q] = page.mqls[q] || []).push(fn); };
          return { matches: page.media[q] === true, media: q, addListener: keep, addEventListener: (_type, fn) => keep(fn) };
        },
        innerWidth: 1280, innerHeight: 800, scrollY: 0, console: console,
        Node: { DOCUMENT_POSITION_FOLLOWING: 4 },
      };
      sandbox.window = sandbox;
      this.context = vm.createContext(sandbox);
    }
    vm.runInContext(fs.readFileSync(file, 'utf8'), this.context, { filename: file });
  }
}

/* One panel as archive.region_panel writes it: a map and, beside it, the list that names the map (data-map-target).

   The map draws: the tracks of t1 and t2 and the planned line of g1 (.mk-cat[data-key]), pins for t1 and t4, and two
   cluster markers, one for t2 + t3 and one for t8 + t9.
   The list holds eleven rows, newest first, the goal last: t1, n1, t2, t3, t4, j1, n2, t5, and then, beyond the first
   eight (li.arc-more), t8, t9 and g1. n1 and n2 are reports without a track, j1 is a journal and t5 a report added
   since the map was drawn: the map draws none of the four.

   Phase 12: every row carries data-kind (archive.region_row: 'trip', 'planned' for g1; a journal row none) and its id,
   arc-row-<slug>, in the list of its own region; every marker carries its activity (inject_acts: data-act on tracks
   and pins, data-acts on a cluster); the panel has its count line (.arc-count), its live region (.arc-plive) and the
   legend under the map (archive.legend: li[data-act] with a .disc and the word). Hikes: t1 n1 t3 j1 t5 g1; skis: t2 t4
   n2 t8 t9. The second panel's legend names one activity. */
const DRAWN = ['t1', 't2', 't3', 't4', 't8', 't9', 'g1'];
const NOT_DRAWN = ['n1', 'j1', 'n2', 't5'];
const ROWS = ['t1', 'n1', 't2', 't3', 't4', 'j1', 'n2', 't5', 't8', 't9', 'g1'];
const ACT = { t1: 'hike', n1: 'hike', t2: 'ski', t3: 'hike', t4: 'ski', j1: 'hike', n2: 'ski', t5: 'hike', t8: 'ski', t9: 'ski', g1: 'hike' };
const actOf = (key) => ACT[key.split(':')[0]];
const rowKind = (key) => (key === 'g1' ? 'planned' : key[0] === 'j' ? null : 'trip');
const WORD = { hike: 'Hike', ski: 'Ski' };

// archive.legend: one li[data-act] per activity the map draws, then the map's symbols
function legendHtml(acts) {
  return '<div class="arc-legend keyrow--d"><p class="t-label">Legend</p><div class="arc-legend-c"><ul aria-label="Activities">'
    + acts.map((a) => '<li data-act="' + a + '"><span class="disc" style="width:16px;height:16px;background:#3A6B47" aria-hidden="true">'
      + '<svg class="ic" width="9" height="9" aria-hidden="true"></svg></span><span>' + WORD[a] + '</span></li>').join('')
    + '</ul><ul aria-label="Map symbols"><li><svg width="28" height="12" viewBox="0 0 28 12" aria-hidden="true"></svg><span>Planned route</span></li>'
    + '<li><svg width="28" height="20" viewBox="0 0 28 20" aria-hidden="true"></svg><span>Several reports start here</span></li></ul></div></div>';
}
// archive.count_line(ts, 'ml--end'): reports, then '+ N PLANNED ROUTE' (a journal row is in neither)
function countHtml(keys) {
  const pub = keys.filter((k) => rowKind(k) === 'trip').length;
  const pl = keys.filter((k) => rowKind(k) === 'planned').length;
  const items = [pub + '\u00a0' + (pub === 1 ? 'REPORT' : 'REPORTS')].concat(pl ? ['+ ' + pl + '\u00a0PLANNED\u00a0ROUTE' + (pl === 1 ? '' : 'S')] : []);
  return '<span class="ml ml--end">' + items.map((x, i) => '<span class="mi">' + (i ? '<span class="sr">, </span>' : '') + x + '</span>').join('') + '</span>';
}
function frag(page, html) {
  const box = page.el('template');
  parseInto(box, html);
  return box.childNodes.slice();
}

function panel(page, slug, rows, extra, acts) {
  const el = (tag, attrs, children) => page.el(tag, attrs, children);
  let marks = [
    el('g', { class: 'mk-cat', 'data-key': 't1', 'data-act': 'hike' }), el('g', { class: 'mk-cat', 'data-key': 't2', 'data-act': 'ski' }),
    el('g', { class: 'mk-cat mk-planned', 'data-key': 'g1', 'data-act': 'hike' }),
    el('a', { class: 'mk-pin', href: '../../trips/t1/', 'data-key': 't1', 'data-act': 'hike' }),
    el('a', { class: 'mk-pin', href: '../../trips/t4/', 'data-key': 't4', 'data-act': 'ski' }),
    el('g', { class: 'mk-cluster', 'aria-hidden': 'true', 'data-keys': 't2 t3', 'data-acts': 'hike ski' }),
    el('g', { class: 'mk-cluster', 'aria-hidden': 'true', 'data-keys': 't8 t9', 'data-acts': 'ski' }),
  ];
  if (extra) marks = marks.concat(extra(el));          // what one check adds to the map (a journal part's lines)
  const map = el('div', { id: 'arc-map-' + slug, class: 'map arc-mapv' }, [el('div', { class: 'mv mv--desktop' }, [el('svg', {}, marks)])]);
  const items = rows.map((key, i) => {
    const kind = rowKind(key);
    const attrs = { class: 'arc-row' + (kind ? '' : ' arc-row--journal') + (i >= 8 && rows.length > 9 ? ' arc-more' : ''), 'data-key': key };
    // the row's id only in its own region's list (the second panel lists t1 and t2 of the first one's region)
    if (slug !== 'y') attrs.id = kind ? 'arc-row-' + key : 'arc-row-' + slug + '-' + key.replace(':', '-');
    if (kind) attrs['data-kind'] = kind;
    return el('li', attrs, [el('a', { href: '../../trips/' + key.split(':')[0] + '/', 'data-act': actOf(key) })]);
  });
  const list = el('ol', { class: 'arc-rows', id: 'arc-rows-' + slug, 'aria-labelledby': 'arc-in-' + slug, 'data-map-target': 'arc-map-' + slug },
    items);
  const label = 'Show all ' + (rows.length - 1);
  const press = { type: 'button', class: 'alink arc-all-btn', 'aria-expanded': 'false', 'aria-controls': 'arc-rows-' + slug, hidden: '' };
  const button = rows.length > 9 ? el('button', press, [label, el('svg', { class: 'ic' })]) : null;
  const count = el('span', { class: 't-mono-s arc-count', id: 'arc-count-' + slug }, frag(page, countHtml(rows)));
  const live = el('p', { class: 'sr arc-plive', 'aria-live': 'polite' });
  const legend = frag(page, legendHtml(acts || (slug === 'y' ? ['hike'] : ['hike', 'ski'])))[0];
  const box = el('div', { class: 'arc-panel', id: slug === 'x' ? 'map' : 'region-' + slug }, [
    el('div', { class: 'arc-grid' }, [
      el('div', { class: 'arc-mapcol' }, [map, el('div', { class: 'arc-cap' }, ['North up']), legend]),
      el('div', { class: 'arc-side' }, [el('div', { class: 'arc-inreg' }, [
        el('div', { class: 'arc-inreg-h' }, [el('h3', { class: 't-label', id: 'arc-in-' + slug }, ['In this region']), count]),
        live, list].concat(button ? [button] : []))]),
    ]),
  ]);
  page.body.appendChild(box);
  return {
    map: map, marks: marks, list: list, rows: items, button: button, label: label, count: count, live: live, legend: legend,
    lis: legend.querySelectorAll('li[data-act]'), discs: legend.querySelectorAll('.disc'),
  };
}

// opts: scripts (the files to run, base.js then archive.js), media and hash (for the Page), extra (for the first panel)
function build(bodyClass, opts) {
  opts = opts || {};
  const page = new Page(bodyClass, opts);
  const main = panel(page, 'x', ROWS, opts.extra);
  const other = panel(page, 'y', ['t1', 't2', 'n1']);          // a second panel, as the Map page has: its map stays out of it
  (opts.scripts || [BASE, ARCHIVE]).forEach((file) => page.run(file));
  return { page: page, main: main, other: other };
}

// a home page region map (home.py: core.map_block without an id, and no list beside it): the same markers
function homeMap(page) {
  const el = (tag, attrs, children) => page.el(tag, attrs, children);
  const marks = [
    el('g', { class: 'mk-cat', 'data-key': 't1' }),
    el('a', { class: 'mk-pin', href: 'trips/t1/', 'data-key': 't1' }), el('a', { class: 'mk-pin', href: 'trips/t4/', 'data-key': 't4' }),
    el('g', { class: 'mk-cluster', 'aria-hidden': 'true', 'data-keys': 't2 t3' }),
    el('g', { class: 'mk-cluster', 'aria-hidden': 'true', 'data-keys': 't8 t9' }),
  ];
  const map = el('div', { class: 'map' }, [el('div', { class: 'mv mv--desktop' }, [el('svg', {}, marks)])]);
  page.body.appendChild(el('div', { class: 'hom-reg' }, [map]));
  return { map: map, marks: marks, rows: [] };
}

const keysOf = (m) => m.getAttribute('data-key') || m.getAttribute('data-keys');
const kindOf = (m) => (m.classList.contains('mk-cluster') ? 'cluster' : m.classList.contains('mk-pin') ? 'pin' : 'track');
function state(p) {
  // what the map shows: is it dimmed, which marks are picked out, and which rows of the list are marked from the map
  return {
    dimmed: p.map.classList.contains('is-hl'),
    picked: p.marks.filter((m) => m.classList.contains('hl')).map((m) => kindOf(m) + ':' + keysOf(m)),
    rows: p.rows.filter((r) => r.classList.contains('is-map-hl')).map((r) => r.getAttribute('data-key')),
  };
}
const CLEAR = { dimmed: false, picked: [], rows: [] };
const row = (p, key) => p.rows.filter((r) => r.getAttribute('data-key') === key)[0];
const mark = (p, cls, key) => p.marks.filter((m) => m.classList.contains(cls) && keysOf(m) === key)[0];
const withClass = (list, cls) => list.filter((x) => x.classList.contains(cls));
const keysWith = (p, cls) => withClass(p.rows, cls).map((r) => r.getAttribute('data-key'));
const marksWith = (p, cls) => withClass(p.marks, cls).map((m) => kindOf(m) + ':' + keysOf(m));

// ---------------------------------------------------------------- highlight: base.js

check('fixture: the list has rows the map draws and rows it does not', () => {
  const p = build('p-region').main;
  deq(ROWS.filter((k) => DRAWN.indexOf(k) === -1), NOT_DRAWN);
  eq(p.rows.length, 11);
  eq(p.map.querySelectorAll('.mk-cat[data-key], .mk-pin[data-key]').length, 5);
  eq(p.map.querySelectorAll('.mk-cluster').length, 2);
  deq(state(p), CLEAR);
  // the rows are wired at all: without listeners every check below would pass on a map nobody touches
  p.rows.forEach((r) => ['mouseenter', 'mouseleave', 'focusin', 'focusout'].forEach((type) => {
    eq((r.listeners[type] || []).length, 1, type + ' on the row of ' + r.getAttribute('data-key'));
  }));
});

check('highlight drawn: a row of a trip the map draws picks it out and dims the rest', () => {
  const t = build('p-region');
  const p = t.main;
  const want = {
    t1: ['track:t1', 'pin:t1'],            // a track and its pin
    t4: ['pin:t4'],                        // a pin alone
    g1: ['track:g1'],                      // the planned line of a goal
    t2: ['track:t2', 'cluster:t2 t3'],     // a track whose pin is merged into a cluster marker
    t3: ['cluster:t2 t3'],                 // a cluster marker alone
    t9: ['cluster:t8 t9'],
  };
  Object.keys(want).forEach((key) => {
    ['mouseenter', 'focusin'].forEach((type, i) => {
      t.page.send(row(p, key), type);
      deq(state(p), { dimmed: true, picked: want[key], rows: [] }, type + ' on the row of ' + key);
      t.page.send(row(p, key), ['mouseleave', 'focusout'][i]);
      deq(state(p), CLEAR, 'after leaving the row of ' + key);
    });
  });
  deq(state(t.other), CLEAR);              // the other panel's map was never touched
});

check('highlight not drawn: a row of a trip the map does not draw leaves the map as it is', () => {
  const t = build('p-region');
  const p = t.main;
  NOT_DRAWN.forEach((key) => {
    ['mouseenter', 'focusin'].forEach((type, i) => {
      t.page.send(row(p, key), type);
      deq(state(p), CLEAR, type + ' on the row of ' + key + ': the map draws nothing of it, and is dimmed or marked all the same');
      t.page.send(row(p, key), ['mouseleave', 'focusout'][i]);
      deq(state(p), CLEAR);
    });
  });
});

check('highlight moves: from a drawn row straight to one that is not, the map is let go of', () => {
  const t = build('p-region');
  const p = t.main;
  // the pointer can enter the next row before the browser reports leaving the last one: nothing may be left behind
  t.page.send(row(p, 't1'), 'mouseenter');
  eq(state(p).dimmed, true);
  t.page.send(row(p, 'n1'), 'mouseenter');
  deq(state(p), CLEAR);
  t.page.send(row(p, 't3'), 'mouseenter');
  deq(state(p), { dimmed: true, picked: ['cluster:t2 t3'], rows: [] });
  t.page.send(row(p, 't4'), 'mouseenter');
  deq(state(p), { dimmed: true, picked: ['pin:t4'], rows: [] });
  t.page.send(row(p, 't4'), 'mouseleave');
  deq(state(p), CLEAR);
});

check('highlight markers: a pin and a cluster marker still pick out their tracks and mark their rows', () => {
  const t = build('p-region');
  const p = t.main;
  t.page.send(mark(p, 'mk-pin', 't1'), 'mouseenter');
  deq(state(p), { dimmed: true, picked: ['track:t1', 'pin:t1'], rows: ['t1'] });
  t.page.send(mark(p, 'mk-pin', 't1'), 'mouseleave');
  deq(state(p), CLEAR);
  t.page.send(mark(p, 'mk-pin', 't4'), 'focusin');
  deq(state(p), { dimmed: true, picked: ['pin:t4'], rows: ['t4'] });
  t.page.send(mark(p, 'mk-pin', 't4'), 'focusout');
  deq(state(p), CLEAR);
  t.page.send(mark(p, 'mk-cluster', 't2 t3'), 'mouseenter');
  deq(state(p), { dimmed: true, picked: ['track:t2', 'cluster:t2 t3'], rows: ['t2', 't3'] });
  t.page.send(mark(p, 'mk-cluster', 't2 t3'), 'mouseleave');
  deq(state(p), CLEAR);
  deq(state(t.other), CLEAR);
  // the second panel has its own list and map: its rows reach its map alone
  t.page.send(row(t.other, 't1'), 'mouseenter');
  deq(state(t.other), { dimmed: true, picked: ['track:t1', 'pin:t1'], rows: [] });
  deq(state(p), CLEAR);
  t.page.send(row(t.other, 'n1'), 'mouseenter');
  deq(state(t.other), CLEAR);
});

// a journal part on a region map: one line per day under the part's key, no pin, and one link over the lines (a.mk-line,
// mapkit.line_links); its row in the list carries the same key
const LOOP = 'j1:loop';
const CREST = 'j1:crest';
const journalLines = (el) => [
  el('g', { class: 'mk-cat', 'data-key': LOOP, 'data-act': 'hike' }), el('g', { class: 'mk-cat', 'data-key': LOOP, 'data-act': 'hike' }),
  el('g', { class: 'mk-cat', 'data-key': CREST, 'data-act': 'hike' }),
  el('a', { class: 'mk-line', href: '../../trips/j1/#day-4', 'data-key': LOOP, 'data-act': 'hike' }),
  el('a', { class: 'mk-line', href: '../../trips/j1/#day-1', 'data-key': CREST, 'data-act': 'hike' }),
];

check('highlight lines: a line that is a link picks out its lines and marks its row, as a pin does', () => {
  const page = new Page('p-region');
  const p = panel(page, 'x', ['t1', 't2', LOOP, CREST], journalLines);
  [BASE, ARCHIVE].forEach((file) => page.run(file));
  const loop = mark(p, 'mk-line', LOOP);
  ['mouseenter', 'mouseleave', 'focusin', 'focusout'].forEach((type) => {
    eq((loop.listeners[type] || []).length, 1, type + ' on the line link');       // a link: the keyboard reaches it too
  });
  deq(state(p), CLEAR);
  [['mouseenter', 'mouseleave'], ['focusin', 'focusout']].forEach((pair) => {
    page.send(loop, pair[0]);
    deq(state(p), { dimmed: true, picked: ['track:' + LOOP, 'track:' + LOOP], rows: [LOOP] }, pair[0] + ' on the line link');
    page.send(loop, pair[1]);
    deq(state(p), CLEAR, pair[1] + ' on the line link');
  });
  // the other part's link picks out the other part alone
  page.send(mark(p, 'mk-line', CREST), 'mouseenter');
  deq(state(p), { dimmed: true, picked: ['track:' + CREST], rows: [CREST] });
  page.send(mark(p, 'mk-line', CREST), 'mouseleave');
  // and the part's row picks out its lines, as any row of a drawn trip does
  page.send(row(p, LOOP), 'mouseenter');
  deq(state(p), { dimmed: true, picked: ['track:' + LOOP, 'track:' + LOOP], rows: [] });
  page.send(row(p, LOOP), 'mouseleave');
  deq(state(p), CLEAR);
});

// ---------------------------------------------------------------- 'Show all' / 'Show fewer': archive.js

const shown = (p) => p.rows.filter((r) => r.offsetParent !== null).length;
// what the scripts focused and scrolled to, in order: 'focus: the link of row t8', 'scroll: row t8 {"block":"center"}'
const done = (page) => page.log.map((x) => x.did + ': ' + who(x.el) + (x.how === undefined ? '' : ' ' + JSON.stringify(x.how)));
const BUTTON = 'the button of arc-rows-x';

['p-region', 'p-archive'].forEach((bodyClass) => {
  check('show all (' + bodyClass + '): as the script leaves the page, the list is short and the button is there', () => {
    const t = build(bodyClass);
    const p = t.main;
    eq(p.list.classList.contains('arc-collapsed'), true);
    eq(shown(p), 8);
    eq(p.button.hidden, false);
    eq(p.button.getAttribute('aria-expanded'), 'false');
    eq(p.button.firstChild.nodeValue, 'Show all 10');
    eq(who(t.other.button), 'nothing');                        // a list of three has none
    eq(t.other.list.classList.contains('arc-collapsed'), false);
    deq(done(t.page), []);                                     // nothing was focused or scrolled to on the way
  });

  check('show all (' + bodyClass + '): opening focuses the first row that came into view and scrolls to nothing', () => {
    const t = build(bodyClass);
    const p = t.main;
    p.button.click();
    eq(p.list.classList.contains('arc-collapsed'), false);
    eq(shown(p), 11);
    eq(p.button.getAttribute('aria-expanded'), 'true');
    eq(p.button.firstChild.nodeValue, 'Show fewer');
    // the ninth row is the first of the three that were hidden; nothing is scrolled to
    deq(done(t.page), ['focus: the link of row t8']);
  });

  check('show fewer (' + bodyClass + '): closing scrolls the button into view and moves no focus', () => {
    const t = build(bodyClass);
    const p = t.main;
    p.button.click();
    t.page.log.length = 0;
    t.page.activeElement = p.button;                           // a press leaves the focus on the button
    p.button.click();
    eq(p.list.classList.contains('arc-collapsed'), true);
    eq(shown(p), 8);
    eq(p.button.getAttribute('aria-expanded'), 'false');
    eq(p.button.firstChild.nodeValue, 'Show all 10');
    // the button that was pressed, by the least movement (none when it is in view); and the focus stays on it
    deq(done(t.page), ['scroll: ' + BUTTON + ' {"block":"nearest"}']);
    eq(who(t.page.activeElement), BUTTON);
    // and round again: each opening focuses, each closing scrolls, never both
    p.button.click();
    p.button.click();
    const scrolled = 'scroll: ' + BUTTON + ' {"block":"nearest"}';
    deq(done(t.page), [scrolled, 'focus: the link of row t8', scrolled]);
  });
});

check('show all: on a page that is neither the Map page nor a region page the script does nothing', () => {
  const t = build('p-home');
  eq(t.main.list.classList.contains('arc-collapsed'), false);
  eq(t.main.button.hidden, true);
  // archive.js wires nothing; base.js's one listener ends a cluster's selection, so with none it does nothing either
  deq((t.main.button.listeners.click || []).length, 1);
  t.main.button.click();
  deq([t.main.list.classList.contains('arc-collapsed'), t.main.button.getAttribute('aria-expanded')], [false, 'false']);
  deq(done(t.page), []);
});

// ---------------------------------------------------------------- the two together: a cluster marker whose rows are hidden

const visible = (p) => p.rows.filter((r) => r.offsetParent !== null).map((r) => r.getAttribute('data-key'));

check('both: a press on a cluster marker of hidden rows opens the list, without scrolling to the button', () => {
  const t = build('p-region');
  const p = t.main;
  const marker = mark(p, 'mk-cluster', 't8 t9');
  eq(marker.classList.contains('is-linked'), true);
  eq(who(row(p, 't8').offsetParent), 'nothing');
  marker.click();
  eq(p.list.classList.contains('arc-collapsed'), false);
  eq(p.button.getAttribute('aria-expanded'), 'true');
  // the marker's two rows are on view, and nothing else of the list: the selection sets the rest aside (qa-02)
  deq(visible(p), ['t8', 't9']);
  // base.js presses the button (archive.js opens the list), then centres the marker's first row. The button is not
  // scrolled to: the list opened
  const log = done(t.page);
  eq(log[log.length - 1], 'scroll: row t8 {"block":"center"}');
  deq(log.filter((x) => x.indexOf(BUTTON) !== -1), []);
  // a marker whose first row is in view opens nothing, centres the row and moves no focus (a toggle keeps it)
  const again = build('p-region');
  mark(again.main, 'mk-cluster', 't2 t3').click();
  eq(again.main.list.classList.contains('arc-collapsed'), true);
  deq(done(again.page), ['scroll: row t2 {"block":"center"}']);
  eq(who(again.page.activeElement), 'nothing');
});

// ---------------------------------------------------------------- Phase 12, rule D4 revised: which cluster markers are buttons

const MARKER_EVENTS = ['mouseenter', 'mouseleave', 'focusin', 'focusout', 'click', 'keydown'];
const wired = (el) => MARKER_EVENTS.filter((type) => (el.listeners[type] || []).length).join(' ');
const aria = (el) => ['aria-hidden', 'role', 'tabindex', 'aria-pressed', 'aria-label'].map((a) => a + '=' + el.getAttribute(a)).join(' ');
const TOUCH = { '(hover: none)': true };
const NARROW = { '(max-width: 759.98px)': true };

check('clusters (D4 revised): on a map with list rows a cluster marker is a named toggle button with focus listeners', () => {
  const t = build('p-region');
  ['t2 t3', 't8 t9'].forEach((keys) => {
    const c = mark(t.main, 'mk-cluster', keys);
    // drawn aria-hidden (mapkit); the script takes that off and names it, since it now has focus listeners
    eq(aria(c), 'aria-hidden=null role=button tabindex=0 aria-pressed=false aria-label=2 reports start here', 'cluster ' + keys);
    eq(c.classList.contains('is-linked'), true);
    eq(wired(c), MARKER_EVENTS.join(' '), 'cluster ' + keys);
    MARKER_EVENTS.forEach((type) => eq(c.listeners[type].length, 1, type + ' on cluster ' + keys));
  });
  // the second panel's list holds one of the marker's two reports
  eq(mark(t.other, 'mk-cluster', 't2 t3').getAttribute('aria-label'), '1 report starts here');
  // a pin is a link: hover and focus, and no click of the script's without (hover: none)
  withClass(t.main.marks, 'mk-pin').forEach((pin) => {
    eq(wired(pin), 'mouseenter mouseleave focusin focusout', who(pin));
    eq(pin.hasAttribute('role') || pin.hasAttribute('tabindex'), false, who(pin));
  });
});

check('clusters (D4 revised): on a map without list rows (home) a cluster marker stays aria-hidden, unnamed and out of the Tab order', () => {
  [{}, TOUCH].forEach((media) => {
    const page = new Page('p-home', { media: media });
    const home = homeMap(page);
    [BASE, ARCHIVE].forEach((file) => page.run(file));
    const how = Object.keys(media).join('') || 'no media query';
    withClass(home.marks, 'mk-cluster').forEach((c) => {
      eq(aria(c), 'aria-hidden=true role=null tabindex=null aria-pressed=null aria-label=null', who(c) + ', ' + how);
      eq(c.classList.contains('is-linked'), false);
      // a pointer target only: Chrome makes an SVG <g> with a focus listener a Tab stop
      eq(wired(c), 'mouseenter mouseleave', who(c) + ', ' + how);
      page.send(c, 'click', true);
      eq(c.hasAttribute('aria-pressed'), false);
    });
    // a pin is a link with hover and focus listeners (what a tap does under (hover: none) is the touch checks')
    withClass(home.marks, 'mk-pin').forEach((pin) => {
      deq(['mouseenter', 'mouseleave', 'focusin', 'focusout'].map((type) => (pin.listeners[type] || []).length), [1, 1, 1, 1], who(pin) + ', ' + how);
    });
    deq(state(home), CLEAR);
  });
});

// ---------------------------------------------------------------- qa-02: a cluster's selection

// the words of a line, whatever spaces (no-break or not) the script put between them
const words = (el) => el.textContent.replace(/\s+/g, ' ');
const selText = (n) => n + (n === 1 ? ' REPORT STARTS' : ' REPORTS START') + ' HERE, Show all';

check('cluster press: a press selects the marker\'s rows, sets the rest of the list aside and says N reports start here · Show all', () => {
  const t = build('p-region');
  const p = t.main;
  const before = p.count.innerHTML;
  eq(before, countHtml(ROWS));
  eq(p.count.textContent, '9\u00a0REPORTS, + 1\u00a0PLANNED\u00a0ROUTE');
  const c = mark(p, 'mk-cluster', 't2 t3');
  c.click();
  eq(c.getAttribute('aria-pressed'), 'true');
  deq(state(p), { dimmed: true, picked: ['track:t2', 'cluster:t2 t3'], rows: ['t2', 't3'] });
  deq(keysWith(p, 'is-off'), ['t1', 'n1', 't4', 'j1', 'n2', 't5', 't8', 't9', 'g1']);
  deq(visible(p), ['t2', 't3']);
  // the count line: two items of one .ml line (CSS draws the dot), the second a button that clears
  eq(words(p.count), selText(2));
  deq(p.count.querySelectorAll('.ml .mi').length, 2);
  const clear = p.count.querySelector('.mi button.arc-sel-clear');
  deq([clear.getAttribute('type'), clear.textContent], ['button', 'Show all']);
  // both rows are among the first eight: the list stays folded; the first row is centred and the focus stays put
  eq(p.list.classList.contains('arc-collapsed'), true);
  deq(done(t.page), ['scroll: row t2 {"block":"center"}']);
  // the other panel is not touched
  deq(keysWith(t.other, 'is-off'), []);
  deq(state(t.other), CLEAR);
  eq(t.other.count.innerHTML, countHtml(['t1', 't2', 'n1']));
});

check('cluster press: a pointer or the focus on another pin or row returns to the selection when it leaves, not to a clear map', () => {
  const t = build('p-region');
  const p = t.main;
  const c = mark(p, 'mk-cluster', 't2 t3');
  c.click();
  const sel = state(p);
  [['mouseenter', 'mouseleave'], ['focusin', 'focusout']].forEach((pair) => {
    const pin = mark(p, 'mk-pin', 't1');
    t.page.send(pin, pair[0]);
    deq(state(p), { dimmed: true, picked: ['track:t1', 'pin:t1'], rows: ['t1'] }, pair[0] + ' on pin t1');
    t.page.send(pin, pair[1]);
    deq(state(p), sel, pair[1] + ' on pin t1: the selection is gone');
    t.page.send(row(p, 't3'), pair[0]);
    deq(state(p), { dimmed: true, picked: ['cluster:t2 t3'], rows: ['t2', 't3'] }, pair[0] + ' on row t3');
    t.page.send(row(p, 't3'), pair[1]);
    deq(state(p), sel, pair[1] + ' on row t3: the selection is gone');
    t.page.send(c, pair[0]);
    t.page.send(c, pair[1]);
    deq(state(p), sel, pair[1] + ' on the selected marker');
  });
  eq(c.getAttribute('aria-pressed'), 'true');
  deq(keysWith(p, 'is-off').length, 9);
});

check('cluster press: a second press, Escape or Show all clears and gives the count line back; Enter and Space press it too', () => {
  const t = build('p-region');
  const p = t.main;
  const before = p.count.innerHTML;
  const c = mark(p, 'mk-cluster', 't2 t3');
  const cleared = (how, map) => {
    eq(c.getAttribute('aria-pressed'), 'false', how);
    deq(keysWith(p, 'is-off'), [], how);
    eq(p.count.innerHTML, before, how);
    deq(state(p), map || CLEAR, how);
  };
  c.click();
  c.click();
  cleared('a second press');
  let e = t.page.key(c, 'Enter');
  deq([e.defaultPrevented, c.getAttribute('aria-pressed')], [true, 'true'], 'Enter');
  e = t.page.key(c, ' ');
  eq(e.defaultPrevented, true, 'Space scrolled the page');
  cleared('Space');
  e = t.page.key(c, 'Tab');
  deq([e.defaultPrevented, c.getAttribute('aria-pressed')], [false, 'false'], 'Tab');
  c.click();
  t.page.key(t.page.body, 'Escape');
  cleared('Escape');
  // Show all: the button it was pressed on is gone, so the focus goes back to the marker (which then marks its rows,
  // as a focused marker does, without selecting them)
  c.click();
  t.page.log.length = 0;
  p.count.querySelector('.arc-sel-clear').click();
  cleared('Show all', { dimmed: true, picked: ['track:t2', 'cluster:t2 t3'], rows: ['t2', 't3'] });
  deq(done(t.page), ['focus: cluster t2 t3']);
  t.page.send(c, 'focusout', true);
  deq(state(p), CLEAR);
  // a press on another marker moves the selection; Escape then gives back the line as it was before either
  c.click();
  const d = mark(p, 'mk-cluster', 't8 t9');
  d.click();
  deq([c.getAttribute('aria-pressed'), d.getAttribute('aria-pressed')], ['false', 'true']);
  deq(state(p).rows, ['t8', 't9']);
  deq(keysWith(p, 'is-off'), ['t1', 'n1', 't2', 't3', 't4', 'j1', 'n2', 't5', 'g1']);
  eq(words(p.count), selText(2));
  t.page.key(t.page.body, 'Escape');
  deq([d.getAttribute('aria-pressed'), p.count.innerHTML, keysWith(p, 'is-off').length], ['false', before, 0]);
});

check('cluster press: N counts the reports among the marker\'s rows, never the planned route', () => {
  // a marker over a report and the planned route of a goal (a cluster's keys can hold both); the route's row is folded
  const t = build('p-region', { extra: (el) => [el('g', { class: 'mk-cluster', 'aria-hidden': 'true', 'data-keys': 't5 g1', 'data-acts': 'hike' })] });
  const p = t.main;
  const c = mark(p, 'mk-cluster', 't5 g1');
  eq(c.getAttribute('aria-label'), '1 report starts here');
  c.click();
  eq(words(p.count), selText(1));
  deq(state(p), { dimmed: true, picked: ['track:g1', 'cluster:t5 g1'], rows: ['t5', 'g1'] });
  // the folded row is brought on view: the list opens
  eq(p.button.getAttribute('aria-expanded'), 'true');
  deq(visible(p), ['t5', 'g1']);
});

// ---------------------------------------------------------------- gap4-01/02: an address naming one row

['p-region', 'p-archive'].forEach((bodyClass) => {
  check('landing (' + bodyClass + '): an address naming a folded row opens the list, centres the row and focuses its link', () => {
    const t = build(bodyClass, { hash: '#arc-row-t9' });
    const p = t.main;
    eq(p.button.getAttribute('aria-expanded'), 'true');
    eq(p.button.firstChild.nodeValue, 'Show fewer');
    // as a cluster press opens a folded row: the list's own button, then the row centred and its link focused without
    // another scroll; the button is not scrolled to
    const log = done(t.page);
    deq(log.slice(-2), ['scroll: row t9 {"block":"center"}', 'focus: the link of row t9 {"preventScroll":true}']);
    deq(log.filter((x) => x.indexOf(BUTTON) !== -1), []);
    eq(who(t.page.activeElement), 'the link of row t9');
    // the focus in the row marks its trip on the map (base.js, focusin), while it stays
    deq(state(p), { dimmed: true, picked: ['cluster:t8 t9'], rows: [] });
    // after load (the browser's own jump to the fragment) the row ends centred again
    t.page.log.length = 0;
    t.page.fire('load');
    eq(done(t.page).pop(), 'scroll: row t9 {"block":"center"}');
    eq(who(t.page.activeElement), 'the link of row t9');
  });
});

check('landing: a row on view is centred and focused without opening the list; an address that is not a row focuses nothing', () => {
  const t = build('p-region', { hash: '#arc-row-t3' });
  eq(t.main.list.classList.contains('arc-collapsed'), true);
  deq(done(t.page).slice(-2), ['scroll: row t3 {"block":"center"}', 'focus: the link of row t3 {"preventScroll":true}']);
  deq(state(t.main), { dimmed: true, picked: ['cluster:t2 t3'], rows: [] });
  ['#map', '#arc-in-x', '#region-y', '#nothing-here'].forEach((hash) => {
    const u = build('p-region', { hash: hash });
    eq(u.main.list.classList.contains('arc-collapsed'), true, hash);
    deq(done(u.page).filter((x) => x.indexOf('focus') === 0), [], hash);
    eq(who(u.page.activeElement), 'nothing', hash);
  });
});

// ---------------------------------------------------------------- maps-07: the legend as an activity filter

const legendButton = (p, act) => p.lis.filter((li) => li.getAttribute('data-act') === act)[0].children[0];

check('legend: each activity becomes a toggle button that holds its disc and its word; a legend of one activity stays a list', () => {
  const t = build('p-region');
  const p = t.main;
  p.lis.forEach((li, i) => {
    eq(li.children.length, 1);
    const b = li.children[0];
    deq([b.tagName, b.type, b.className, b.getAttribute('aria-pressed')], ['BUTTON', 'button', 'arc-lg-b', 'false']);
    // the disc is moved into the button, not drawn again: it keeps its colour, and archive.css keeps it under forced
    // colours (.arc-legend .disc { forced-color-adjust: none; }, read by tests/test_a11y_static.py)
    eq(b.children[0] === p.discs[i], true, 'the disc of ' + li.getAttribute('data-act') + ' is not the one the legend drew');
    eq(p.discs[i].matches('.arc-legend .disc'), true);
    eq(p.discs[i].getAttribute('style'), 'width:16px;height:16px;background:#3A6B47');
    eq(b.textContent, WORD[li.getAttribute('data-act')]);
  });
  eq(p.legend.querySelectorAll('button').length, 2);           // the map's symbols are not activities
  deq([p.live.textContent, p.map.hasAttribute('data-filter')], ['', false]);
  eq(t.other.legend.querySelectorAll('button').length, 0);
  eq(t.other.lis[0].children[0] === t.other.discs[0], true);
});

check('legend: an activity pressed filters the list and dims the markers of the others; pressed again, it clears', () => {
  const t = build('p-region');
  const p = t.main;
  const pressed = () => p.lis.map((li) => li.children[0].getAttribute('aria-pressed')).join(' ');
  legendButton(p, 'ski').click();
  deq([p.map.getAttribute('data-filter'), pressed()], ['ski', 'false true']);
  // every track and pin of another activity, and a cluster with no ski among its reports (none here: t2 is one)
  deq(marksWith(p, 'is-out'), ['track:t1', 'track:g1', 'pin:t1']);
  deq(keysWith(p, 'is-actoff'), ['t1', 'n1', 't3', 'j1', 't5', 'g1']);
  eq(p.live.textContent, '5 of 9 reports');                    // reports only: neither the journal nor the planned route
  legendButton(p, 'hike').click();                             // one activity at a time
  deq([p.map.getAttribute('data-filter'), pressed()], ['hike', 'true false']);
  deq(marksWith(p, 'is-out'), ['track:t2', 'pin:t4', 'cluster:t8 t9']);
  deq(keysWith(p, 'is-actoff'), ['t2', 't4', 'n2', 't8', 't9']);
  eq(p.live.textContent, '4 of 9 reports');
  legendButton(p, 'hike').click();
  deq([p.map.hasAttribute('data-filter'), pressed()], [false, 'false false']);
  deq([marksWith(p, 'is-out'), keysWith(p, 'is-actoff')], [[], []]);
  eq(p.live.textContent, 'All 9 reports');
  // the other panel's map and list are its own
  deq([marksWith(t.other, 'is-out'), keysWith(t.other, 'is-actoff'), t.other.live.textContent], [[], [], '']);
});

// ---------------------------------------------------------------- gap1-03: a touch screen has no hover

check('touch: without (hover: none) a tap on a pin is not taken: it follows the link, and the map has no tap of its own', () => {
  const t = build('p-region');
  eq(t.page.asked.indexOf('(hover: none)') !== -1, true);
  const pin = mark(t.main, 'mk-pin', 't1');
  deq([(pin.listeners.click || []).length, (t.main.map.listeners.click || []).length], [0, 0]);
  eq(t.page.send(pin, 'click', true).defaultPrevented, false);
  eq(pin.classList.contains('is-sel'), false);
  deq(state(t.main), CLEAR);
});

check('touch: with (hover: none) a first tap picks a pin out and opens its row, a second tap follows the link, a tap on the map clears', () => {
  const t = build('p-region', { media: TOUCH });
  const p = t.main;
  const t4 = mark(p, 'mk-pin', 't4');
  const t1 = mark(p, 'mk-pin', 't1');
  const paper = p.map.querySelector('svg');
  eq(t.page.send(t4, 'click', true).defaultPrevented, true, 'the first tap followed the link');
  eq(t4.classList.contains('is-sel'), true);
  deq(state(p), { dimmed: true, picked: ['pin:t4'], rows: ['t4'] });
  // the row names the trip: centred, and its link focused
  deq(done(t.page), ['scroll: row t4 {"block":"center"}', 'focus: the link of row t4 {"preventScroll":true}']);
  eq(t.page.send(t4, 'click', true).defaultPrevented, false, 'the second tap on the same pin did not follow the link');
  // a first tap on another pin moves the pick
  eq(t.page.send(t1, 'click', true).defaultPrevented, true);
  deq([t4.classList.contains('is-sel'), t1.classList.contains('is-sel')], [false, true]);
  deq(state(p), { dimmed: true, picked: ['track:t1', 'pin:t1'], rows: ['t1'] });
  // a tap on the map's paper clears it, and the next tap on the pin is a first tap again
  t.page.send(paper, 'click', true);
  eq(t1.classList.contains('is-sel'), false);
  deq(state(p), CLEAR);
  t.page.send(paper, 'click', true);
  deq(state(p), CLEAR);
  eq(t.page.send(t1, 'click', true).defaultPrevented, true);
  t.page.send(paper, 'click', true);
  // a cluster marker is pressed as without touch, and the paper's tap leaves its selection
  const c = mark(p, 'mk-cluster', 't2 t3');
  c.click();
  t.page.send(paper, 'click', true);
  deq([c.getAttribute('aria-pressed'), state(p).rows], ['true', ['t2', 't3']]);
  deq(state(t.other), CLEAR);
});

check('touch: with (hover: none) a line that is a link is tapped as a pin is', () => {
  const page = new Page('p-region', { media: TOUCH });
  const p = panel(page, 'x', ['t1', 't2', LOOP, CREST], journalLines);
  [BASE, ARCHIVE].forEach((file) => page.run(file));
  const loop = mark(p, 'mk-line', LOOP);
  eq(page.send(loop, 'click', true).defaultPrevented, true);
  eq(loop.classList.contains('is-sel'), true);
  deq(state(p), { dimmed: true, picked: ['track:' + LOOP, 'track:' + LOOP], rows: [LOOP] });
  eq(who(page.activeElement), 'the link of row ' + LOOP);
  eq(page.send(loop, 'click', true).defaultPrevented, false);
  page.send(p.map.querySelector('svg'), 'click', true);
  deq([loop.classList.contains('is-sel'), state(p)], [false, CLEAR]);
});

check('touch, Phase 13C walk: a first tap on a pin whose row is folded opens the list and keeps the pick; a second tap follows the link', () => {
  const page = new Page('p-region', { media: TOUCH });
  const p = panel(page, 'x', ROWS, (el) => [el('a', { class: 'mk-pin', href: '../../trips/t9/', 'data-key': 't9', 'data-act': 'ski' })]);
  [BASE, ARCHIVE].forEach((file) => page.run(file));
  const t9 = mark(p, 'mk-pin', 't9');
  eq(row(p, 't9').offsetParent, null, 'row t9 starts folded');
  eq(page.send(t9, 'click', true).defaultPrevented, true);
  // the press of 'Show all 10' that opened the list (a click on the page, outside the map) did not end the pick
  deq([p.button.getAttribute('aria-expanded'), t9.classList.contains('is-sel')], ['true', true]);
  eq(who(page.activeElement), 'the link of row t9');
  eq(page.send(t9, 'click', true).defaultPrevented, false, 'the second tap on the pin did not follow the link');
});

check('touch: with (hover: none) a map without list rows (home) is left alone', () => {
  const page = new Page('p-home', { media: TOUCH });
  const home = homeMap(page);
  [BASE, ARCHIVE].forEach((file) => page.run(file));
  eq(page.asked.indexOf('(hover: none)') !== -1, true);
  withClass(home.marks, 'mk-pin').forEach((pin) => {
    eq((pin.listeners.click || []).length, 0, who(pin));
    eq(page.send(pin, 'click', true).defaultPrevented, false, who(pin));
    eq(pin.classList.contains('is-sel'), false, who(pin));
  });
  page.send(home.map.querySelector('svg'), 'click', true);
  deq(state(home), CLEAR);
  deq(done(page), []);
});

// ---------------------------------------------------------------- phone-03: the years of 'All reports' folded on a phone

const YEARS = [
  ['2026', [['t1', 'hike', 'trip'], ['t2', 'ski', 'trip'], ['t3', 'hike', 'trip']]],
  ['2025', [['t4', 'ski', 'trip'], ['n1', 'hike', 'trip']]],
  ['2024', [['t8', 'ski', 'trip']]],
  ['Planned', [['g1', 'hike', 'planned']]],
];
// archive.archive_section: the filter, the year index, then one .arc-yr per year of core.table_row links
function allReports(page) {
  const gid = (y) => 'yr-' + y.toLowerCase();
  const n = (k) => '<span class="sr">, </span>' + k + '<span class="sr"> ' + (k === 1 ? 'report' : 'reports') + '</span>';
  const count = (rows) => {
    const pub = rows.filter((r) => r[2] !== 'planned').length;
    return '<span class="ml ml--end"><span class="mi">' + (pub ? pub + '\u00a0' + (pub === 1 ? 'REPORT' : 'REPORTS')
      : (rows.length + '\u00a0PLANNED\u00a0ROUTE' + (rows.length === 1 ? '' : 'S'))) + '</span></span>';
  };
  const chips = '<button type="button" class="fchip" role="radio" data-filter="all" aria-checked="true" tabindex="0"><span class="fchip-l">All</span></button>'
    + ['hike', 'ski'].map((a) => '<button type="button" class="fchip" role="radio" data-filter="' + a + '" aria-checked="false" tabindex="-1">'
      + '<span class="chip-sw" aria-hidden="true"></span><span class="fchip-l">' + WORD[a] + '</span><span class="fchip-n">' + n(2) + '</span></button>').join('');
  const index = YEARS.map(([y, rows]) => '<li data-group="' + gid(y) + '"><a href="#' + gid(y) + '">' + y
    + (y === 'Planned' ? '' : '<span class="arc-years-n">' + n(rows.length) + '</span>') + '</a></li>').join('');
  const groups = YEARS.map(([y, rows]) => '<div class="arc-yr" data-group="' + gid(y) + '"><div class="arc-yr-h"><h3 class="t-label" id="' + gid(y) + '">' + y
    + '</h3><span class="t-mono-s arc-yr-n">' + count(rows) + '</span></div><ol class="arc-rows2" id="' + gid(y) + '-rows" aria-labelledby="' + gid(y) + '">'
    + rows.map(([key, act, kind]) => '<li><a class="rtab-r" href="../../trips/' + key + '/" data-key="' + key + '" data-act="' + act + '" data-kind="' + kind + '">'
      + '<span class="rtab-title"><span class="rtab-tt">' + key + '</span></span></a></li>').join('') + '</ol></div>').join('');
  frag(page, '<section class="arc-all wrap sec" id="all-reports" aria-labelledby="all-reports-h"><div class="shead"><h2 class="shead-t" id="all-reports-h">All reports</h2></div>'
    + '<div class="arc-filt" role="radiogroup" aria-label="Filter by activity" hidden>' + chips + '</div>'
    + '<nav class="arc-years" aria-label="Jump to year"><ul>' + index + '</ul></nav><p class="sr" id="arc-live" aria-live="polite"></p>'
    + '<div class="rtab arc-table"><div aria-hidden="true"></div>' + groups + '</div></section>').forEach((node) => page.body.appendChild(node));
  return page.querySelectorAll('.arc-yr').map((g) => ({ group: g, head: g.querySelector('.arc-yr-h'), list: g.querySelector('ol') }));
}
function buildAll(opts) {
  const page = new Page('p-archive', opts);
  const groups = allReports(page);
  [BASE, ARCHIVE].forEach((file) => page.run(file));
  return { page: page, groups: groups };
}
const yearButton = (g) => g.group.querySelector('.arc-yr-btn');
const folded = (t) => t.groups.map((g) => g.list.classList.contains('arc-collapsed'));

check('year folds: on a phone every year after the first is folded behind a Show N reports button under its head', () => {
  const t = buildAll({ media: NARROW });
  eq(t.page.asked.indexOf('(max-width: 759.98px)') !== -1, true);
  eq(who(yearButton(t.groups[0])), 'nothing');
  eq(t.groups[0].head.nextElementSibling === t.groups[0].list, true);
  deq(folded(t), [false, true, true, true]);
  deq(t.groups.slice(1, 3).map((g) => {
    const b = yearButton(g);
    return [g.head.nextElementSibling === b, b.className, b.type, b.getAttribute('aria-expanded'), b.getAttribute('aria-controls'), b.textContent];
  }), [[true, 'alink arc-yr-btn', 'button', 'false', 'yr-2025-rows', 'Show 2 reports'],
    [true, 'alink arc-yr-btn', 'button', 'false', 'yr-2024-rows', 'Show 1 report']]);
  eq(yearButton(t.groups[3]).getAttribute('aria-controls'), 'yr-planned-rows');
  eq(t.page.querySelectorAll('.arc-rows2 a').filter((a) => a.offsetParent !== null).length, 3);
  deq(done(t.page), []);
});

check('year folds: the button folds and unfolds its year; a year link, an address inside a year and the activity filter unfold', () => {
  let t = buildAll({ media: NARROW });
  const g = t.groups[1];
  const b = yearButton(g);
  b.click();
  deq([b.getAttribute('aria-expanded'), b.textContent, g.list.classList.contains('arc-collapsed')], ['true', 'Show fewer', false]);
  deq(done(t.page), []);
  b.click();
  deq([b.getAttribute('aria-expanded'), b.textContent, g.list.classList.contains('arc-collapsed')], ['false', 'Show 2 reports', true]);
  deq(done(t.page), ['scroll: the button of yr-2025-rows {"block":"nearest"}']);
  // a link of the year index opens its year alone
  t.page.querySelector('.arc-years a[href="#yr-2024"]').click();
  deq(folded(t), [false, true, false, true]);
  eq(yearButton(t.groups[2]).getAttribute('aria-expanded'), 'true');
  // Back or Forward to an address inside a year
  t.page.context.location.hash = '#yr-2025';
  t.page.fire('hashchange');
  deq(folded(t), [false, false, false, true]);
  // an address inside a year when the page opens
  t = buildAll({ media: NARROW, hash: '#yr-2024' });
  deq(folded(t), [false, true, false, true]);
  // the activity filter opens every year; a year folded again counts what the filter left
  t = buildAll({ media: NARROW });
  t.page.querySelector('.fchip[data-filter="ski"]').click();
  deq(folded(t), [false, false, false, false]);
  yearButton(t.groups[1]).click();
  eq(yearButton(t.groups[1]).textContent, 'Show 1 report');
});

check('year folds: without (max-width: 759.98px) nothing is folded', () => {
  const t = buildAll({});
  deq([t.page.querySelectorAll('.arc-yr-btn').length, t.page.querySelectorAll('.arc-collapsed').length], [0, 0]);
});

// ---------------------------------------------------------------- qa-06: a region's full-screen map

function fullScreen(attrs, size) {
  const page = new Page('p-fs');
  let boxes = 0;
  const trk = page.el('path', { class: 'mk-trk', d: 'M0 0L10 10' });
  trk.getBBox = () => { boxes++; return { x: 100, y: 100, width: 50, height: 50 }; };
  const fm = page.el('div', Object.assign({ class: 'fs-map' }, attrs),
    [page.el('div', { class: 'map map--fscol' }, [page.el('div', { class: 'mv mv--fs' }, [page.el('svg', {}, [trk])])])]);
  Object.assign(fm, { scrollLeft: 0, scrollTop: 0 }, size);
  page.body.appendChild(fm);
  [BASE, ARCHIVE].forEach((file) => page.run(file));
  return { page: page, fm: fm, boxes: () => boxes };
}

check('full screen: a region\'s map is centred on both axes and the route logic is skipped', () => {
  const big = { scrollWidth: 1077, clientWidth: 390, scrollHeight: 930, clientHeight: 700 };
  let f = fullScreen({ 'data-fs': 'region' }, big);
  deq([f.fm.scrollLeft, f.fm.scrollTop, f.boxes()], [343.5, 115, 0]);
  deq([f.page.body.classList.contains('is-pannable'), f.page.body.classList.contains('is-fit')], [true, false]);
  f = fullScreen({ 'data-fs': 'region' }, { scrollWidth: 390, clientWidth: 390, scrollHeight: 700, clientHeight: 700 });
  deq([f.fm.scrollLeft, f.fm.scrollTop, f.page.body.classList.contains('is-fit')], [0, 0, true]);
  // a report's full-screen map still reads its route (here without a viewBox to scale by, so it is centred across only)
  f = fullScreen({}, big);
  deq([f.boxes() > 0, f.fm.scrollLeft, f.fm.scrollTop], [true, 343.5, 0]);
});

// ---------------------------------------------------------------- Phase 12: script bugs this harness found, now fixed

check('cluster press, review fix 1: a press on a cluster marker of folded rows keeps the focus on the marker, as a press on one in view does', () => {
  const t = build('p-region');
  const c = mark(t.main, 'mk-cluster', 't8 t9');
  c.focus();
  t.page.key(c, 'Enter');
  eq(c.getAttribute('aria-pressed'), 'true');
  // archive.js's 'Show all' handler focuses the first row it reveals (t8's link), so a second Enter follows that link
  eq(who(t.page.activeElement), 'cluster t8 t9');
});

check('cluster press, review fix 2a: on a touch screen, a first tap on a pin while a cluster is selected shows the pin\'s row and leaves the list\'s button alone', () => {
  const t = build('p-region', { media: TOUCH });
  const p = t.main;
  mark(p, 'mk-cluster', 't2 t3').click();
  t.page.log.length = 0;
  t.page.send(mark(p, 'mk-pin', 't1'), 'click', true);
  // openRow() takes row t1, set aside by the selection (.is-off), for a folded row: it presses 'Show all 10', and the
  // row it was meant to show stays hidden, its link's focus refused
  eq(p.button.getAttribute('aria-expanded'), 'false', done(t.page).join(' | '));
  eq(row(p, 't1').offsetParent !== null, true, 'row t1 is still hidden');
});

check('cluster press, review fix 2b: a cluster press under the legend filter opens no folded list when its rows are among the first eight', () => {
  const t = build('p-region');
  const p = t.main;
  legendButton(p, 'ski').click();
  mark(p, 'mk-cluster', 't2 t3').click();          // t2 ski, t3 hike: t3 is .is-actoff, and taken for folded
  eq(p.button.getAttribute('aria-expanded'), 'false', done(t.page).join(' | '));
});

check('cluster press, review fix 3: a cluster marker none of whose keys is in the list is not a button that names 0 reports and does nothing', () => {
  const t = build('p-region');
  const c = mark(t.other, 'mk-cluster', 't8 t9');   // the second panel lists t1, t2, n1
  c.click();
  eq(aria(c), 'aria-hidden=true role=null tabindex=null aria-pressed=null aria-label=null');
});

check('cluster press, review fix 4: the Planned year\'s fold button does not call a planned route a report', () => {
  const t = buildAll({ media: NARROW });
  eq(yearButton(t.groups[3]).textContent.indexOf('report'), -1, yearButton(t.groups[3]).textContent);
});

// ---------------------------------------------------------------- Phase 12: what the phase's review found, now fixed

check('legend, review fix 1: an activity chosen opens a folded list, so its rows behind Show all show; the fold comes back after', () => {
  const t = build('p-region');
  const p = t.main;
  legendButton(p, 'ski').click();
  // t8 and t9, both ski, are beyond the first eight: they are on view, and 'Show all 10' waits while the filter is on
  deq(visible(p), ['t2', 't4', 'n2', 't8', 't9']);
  deq([p.list.classList.contains('arc-collapsed'), p.button.hidden], [false, true]);
  legendButton(p, 'hike').click();                             // another activity: still open
  deq(visible(p), ['t1', 'n1', 't3', 'j1', 't5', 'g1']);
  legendButton(p, 'hike').click();
  deq([p.list.classList.contains('arc-collapsed'), p.button.hidden, p.button.getAttribute('aria-expanded'), p.button.firstChild.nodeValue],
      [true, false, 'false', 'Show all 10']);
  eq(shown(p), 8);
  // a list the reader had opened is open again after the filter
  p.button.click();
  legendButton(p, 'ski').click();
  legendButton(p, 'ski').click();
  deq([p.list.classList.contains('arc-collapsed'), p.button.hidden, p.button.firstChild.nodeValue], [false, false, 'Show fewer']);
  deq(done(t.page).filter((x) => x.indexOf('focus') === 0), ['focus: the link of row t8']);   // the reader's own press only
});

// the Ski page's panel (section.ski_panel): one map, #ski-map, and the list beside it is no region list
function skiPage(media) {
  const page = new Page('p-section', { media: media });
  const el = (tag, attrs, children) => page.el(tag, attrs, children);
  const marks = [
    el('a', { class: 'mk-pin', href: '../trips/t4/', 'data-key': 't4' }),
    el('g', { class: 'mk-cluster', 'aria-hidden': 'true', 'data-keys': 't2 t3' }),
  ];
  const map = el('div', { class: 'map sec-maps', id: 'ski-map' }, [el('div', { class: 'sec-rp' }, [el('svg', {}, marks)])]);
  const rows = ['t1', 't2', 't3', 't4'].map((k) => el('div', { class: 'trow', 'data-key': k }, [el('a', { class: 'trow-a', href: '../trips/' + k + '/' })]));
  page.body.appendChild(el('aside', { class: 'sec-panel' }, [map]));
  page.body.appendChild(el('div', { class: 'sec-list', 'data-map-target': 'ski-map' }, rows));
  page.run(BASE);
  return { page: page, map: map, marks: marks, rows: rows };
}

check('clusters, review fix 2: on the Ski panel a cluster marker keeps its click to the first row it names and stays an unnamed pointer target', () => {
  const k = skiPage();
  const c = k.marks[1];
  eq(aria(c), 'aria-hidden=true role=null tabindex=null aria-pressed=null aria-label=null');
  eq(wired(c), 'mouseenter mouseleave click');
  c.click();
  deq(done(k.page), ['scroll: div.trow {"block":"center"}', 'focus: a.trow-a {"preventScroll":true}']);
  eq(k.page.activeElement.parentNode, k.rows[1]);
  deq(k.rows.filter((r) => r.classList.contains('is-off')), []);
  eq(c.hasAttribute('aria-pressed'), false);
  k.page.key(k.page.body, 'Escape');                          // nothing to clear
  deq(k.rows.filter((r) => r.classList.contains('is-off')), []);
});

check('cluster press, review fix 5: the list\'s own Show fewer or Show all ends a selection first, then folds or opens the list', () => {
  const t = build('p-region');
  const p = t.main;
  const before = p.count.innerHTML;
  p.button.click();                                            // the reader opens the list, then picks the t8 t9 marker
  const c = mark(p, 'mk-cluster', 't8 t9');
  c.click();
  deq(visible(p), ['t8', 't9']);
  p.button.click();                                            // 'Show fewer'
  deq([c.getAttribute('aria-pressed'), keysWith(p, 'is-off'), p.count.innerHTML], ['false', [], before]);
  deq([p.list.classList.contains('arc-collapsed'), shown(p)], [true, 8]);
  // a selection on a folded list (its rows among the first eight), then 'Show all 10'
  const d = mark(p, 'mk-cluster', 't2 t3');
  d.click();
  eq(p.list.classList.contains('arc-collapsed'), true);
  p.button.click();
  deq([d.getAttribute('aria-pressed'), keysWith(p, 'is-off'), p.count.innerHTML, shown(p)], ['false', [], before, 11]);
  // the press base.js makes itself, to show a selection's folded rows, keeps the selection
  p.button.click();
  c.click();
  deq([c.getAttribute('aria-pressed'), visible(p)], ['true', ['t8', 't9']]);
});

check('cluster press, review fix 6: Escape on the count line\'s Show all puts the focus back on the marker', () => {
  const t = build('p-region');
  const p = t.main;
  const c = mark(p, 'mk-cluster', 't2 t3');
  c.click();
  p.count.querySelector('.arc-sel-clear').focus();
  t.page.key(t.page.activeElement, 'Escape');
  deq([c.getAttribute('aria-pressed'), who(t.page.activeElement)], ['false', 'cluster t2 t3']);
  // Escape with the focus elsewhere leaves it there
  c.click();
  row(p, 't2').querySelector('a').focus();
  t.page.key(t.page.activeElement, 'Escape');
  eq(who(t.page.activeElement), 'the link of row t2');
});

check('cluster press, review: a cluster of planned routes alone says so in the count line, not 0 reports', () => {
  const t = build('p-region', { extra: (el) => [el('g', { class: 'mk-cluster', 'aria-hidden': 'true', 'data-keys': 'g1', 'data-acts': 'hike' })] });
  const c = mark(t.main, 'mk-cluster', 'g1');
  eq(c.getAttribute('aria-label'), 'A planned route starts here');
  c.click();
  eq(words(t.main.count), '1 PLANNED ROUTE STARTS HERE, Show all');
});

check('touch, review: a pick ends with a tap outside the map and with Escape; a picked pin is marked is-sel', () => {
  const t = build('p-region', { media: TOUCH });
  const p = t.main;
  const t4 = mark(p, 'mk-pin', 't4');
  t.page.send(t4, 'click', true);
  eq(t4.classList.contains('is-sel'), true);
  t.page.send(t.page.body, 'click', true);                     // somewhere else on the page
  deq([t4.classList.contains('is-sel'), state(p)], [false, CLEAR]);
  eq(t.page.send(t4, 'click', true).defaultPrevented, true, 'the next tap on the pin was not a first tap');
  t.page.key(t.page.body, 'Escape');
  deq([t4.classList.contains('is-sel'), state(p)], [false, CLEAR]);
  eq(t.page.send(t4, 'click', true).defaultPrevented, true);
});

check('year folds, review: a phone turned past 760 px opens every year and drops the buttons; turned back, the buttons return', () => {
  const t = buildAll({ media: NARROW });
  deq(folded(t), [false, true, true, true]);
  t.page.turn('(max-width: 759.98px)', false);
  deq(folded(t), [false, false, false, false]);
  deq(t.groups.slice(1).map((g) => yearButton(g).hidden), [true, true, true]);
  t.page.turn('(max-width: 759.98px)', true);
  deq(t.groups.slice(1).map((g) => [yearButton(g).hidden, yearButton(g).firstChild.nodeValue]),
      [[false, 'Show fewer'], [false, 'Show fewer'], [false, 'Show fewer']]);
});

console.log(checks + ' checks passed');
