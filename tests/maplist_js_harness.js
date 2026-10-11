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
     both        a press on a cluster marker whose rows are hidden opens the list (base.js presses the button) and
                 focuses the row; the button is not scrolled to.

   Run by tests/test_maplist_js.py (skipped when node is missing); by hand:
     node tests/maplist_js_harness.js [base.js] [archive.js]
   The optional arguments point at other copies of the two scripts (used to prove the harness fails a wrong one). Every
   failed check prints 'FAIL <label>' on stderr and throws, so the process exits non-zero; a run without one ends with
   '<N> checks passed' on stdout.

   The stand-in is not a browser. It is a tree of elements with attributes, classList, dataset, listeners and a small
   selector matcher: a tag, classes, #id, [attr] and [attr="value"], joined by spaces (descendants) and commas. A
   selector it cannot read matches nothing, which is what the parts of base.js that have nothing to do on this page get
   (the units switch, the menu, the photo viewer). Rows are hidden as archive.css hides them: .arc-rows.arc-collapsed
   .arc-more. Layout, real focus and real scrolling are not modelled: focus() and scrollIntoView() are only recorded.
   The page below is written by hand after the markup archive.region_panel generates and tools/lib/mapkit.py draws
   (tests/test_region_page.py holds the generated page to those hooks: data-map-target, data-key, data-keys). */
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
  const part = /^(?:\.([\w-]+)|#([\w-]+)|\[([\w-]+)(?:=(?:"([^"]*)"|'([^']*)'))?\])/;
  while (rest) {
    const m = part.exec(rest);
    if (!m) return null;                       // not read: the selector then matches nothing
    if (m[1]) out.classes.push(m[1]);
    else if (m[2]) out.attrs.push(['id', m[2]]);
    else out.attrs.push([m[3], m[4] !== undefined ? m[4] : m[5]]);
    rest = rest.slice(m[0].length);
  }
  return out;
}
function parseSelector(sel) {
  // -> one chain of compounds per comma part; a chain with a part that is not read is dropped
  return String(sel).split(',').map((s) => s.trim().split(/\s+/).map(parseCompound)).filter((chain) => chain.every(Boolean));
}
function hasCompound(el, c) {
  if (c.tag && el.tagName !== c.tag) return false;
  if (!c.classes.every((k) => el.classList.contains(k))) return false;
  return c.attrs.every(([name, value]) => el.hasAttribute(name) && (value === undefined || el.getAttribute(name) === value));
}
function hasChain(el, chain) {
  if (!hasCompound(el, chain[chain.length - 1])) return false;
  let i = chain.length - 2;
  for (let p = el.parentNode; p && i >= 0; p = p.parentNode) if (hasCompound(p, chain[i])) i--;
  return i < 0;
}

class Text {
  constructor(value) { this.nodeValue = value; this.parentNode = null; }
}

// an element in a few words, for the checks and for a failed assertion (which would otherwise print the whole page)
function who(el) {
  if (!el) return 'nothing';
  if (el.tagName === 'LI') return 'row ' + el.getAttribute('data-key');
  if (el.tagName === 'A' && el.parentNode && el.parentNode.tagName === 'LI') return 'the link of ' + who(el.parentNode);
  if (el.tagName === 'BUTTON') return 'the button of ' + el.getAttribute('aria-controls');
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
  // null for an element that is not rendered, as in a browser: hidden itself, inside something hidden, or a row beyond
  // the first eight of a collapsed list (archive.css: .arc-rows.arc-collapsed .arc-more { display: none; })
  get offsetParent() {
    for (let p = this; p; p = p.parentNode) {
      if (p.hidden) return null;
      if (p.classList.contains('arc-more') && p.parentNode && p.parentNode.classList.contains('arc-collapsed')) return null;
    }
    return this.page.body;
  }
  appendChild(child) { child.parentNode = this; this.childNodes.push(child); return child; }
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
  focus(options) { this.page.activeElement = this; this.page.log.push({ did: 'focus', el: this, how: options }); }
  scrollIntoView(options) { this.page.log.push({ did: 'scroll', el: this, how: options }); }
  click() { this.page.send(this, 'click', true); }
}

class Page {
  constructor(bodyClass) {
    this.log = [];                 // every focus() and scrollIntoView() a script called, in order
    this.listeners = {};           // the document's own
    this.activeElement = null;
    this.body = this.el('body', { class: bodyClass });
    this.documentElement = this.el('html', {}, [this.body]);
  }
  [util.inspect.custom]() { return '<the page>'; }
  el(tag, attrs, children) { return new El(this, tag, attrs, children); }
  createElement(tag) { return this.el(tag); }
  addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); }
  querySelectorAll(sel) { return this.documentElement.querySelectorAll(sel); }
  querySelector(sel) { return this.documentElement.querySelector(sel); }
  getElementById(id) { return this.documentElement.descendants().filter((d) => d.attrs.id === id)[0] || null; }
  // one event: the element's own listeners, then (for an event that bubbles) the document's
  send(el, type, bubbles) {
    const e = { type: type, target: el, button: 0, preventDefault() {} };
    (el.listeners[type] || []).slice().forEach((fn) => fn.call(el, e));
    if (bubbles) (this.listeners[type] || []).slice().forEach((fn) => fn.call(this, e));
  }
  run(file) {
    if (!this.context) {
      const noop = () => {};
      const sandbox = {
        document: this, location: { hash: '', search: '', href: 'https://example.test/regions/synthetic-range/' },
        navigator: {}, history: { replaceState: noop }, localStorage: { getItem: () => null, setItem: noop },
        requestAnimationFrame: (fn) => { fn(); }, setTimeout: (fn) => { fn(); }, clearTimeout: noop,
        addEventListener: noop, innerWidth: 1280, innerHeight: 800, scrollY: 0, console: console,
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
   since the map was drawn: the map draws none of the four. */
const DRAWN = ['t1', 't2', 't3', 't4', 't8', 't9', 'g1'];
const NOT_DRAWN = ['n1', 'j1', 'n2', 't5'];
const ROWS = ['t1', 'n1', 't2', 't3', 't4', 'j1', 'n2', 't5', 't8', 't9', 'g1'];

function panel(page, slug, rows) {
  const el = (tag, attrs, children) => page.el(tag, attrs, children);
  const marks = [
    el('g', { class: 'mk-cat', 'data-key': 't1' }), el('g', { class: 'mk-cat', 'data-key': 't2' }),
    el('g', { class: 'mk-cat mk-planned', 'data-key': 'g1' }),
    el('a', { class: 'mk-pin', href: '../../trips/t1/', 'data-key': 't1' }),
    el('a', { class: 'mk-pin', href: '../../trips/t4/', 'data-key': 't4' }),
    el('g', { class: 'mk-cluster', 'aria-hidden': 'true', 'data-keys': 't2 t3' }),
    el('g', { class: 'mk-cluster', 'aria-hidden': 'true', 'data-keys': 't8 t9' }),
  ];
  const map = el('div', { id: 'arc-map-' + slug, class: 'map arc-mapv' }, [el('div', { class: 'mv mv--desktop' }, [el('svg', {}, marks)])]);
  const items = rows.map((key, i) => el('li', { class: 'arc-row' + (i >= 8 && rows.length > 9 ? ' arc-more' : ''), 'data-key': key },
    [el('a', { href: '../../trips/' + key + '/', 'data-act': 'hike' })]));
  const list = el('ol', { class: 'arc-rows', id: 'arc-rows-' + slug, 'aria-labelledby': 'arc-in-' + slug, 'data-map-target': 'arc-map-' + slug },
    items);
  const label = 'Show all ' + (rows.length - 1);
  const press = { type: 'button', class: 'alink arc-all-btn', 'aria-expanded': 'false', 'aria-controls': 'arc-rows-' + slug, hidden: '' };
  const button = rows.length > 9 ? el('button', press, [label, el('svg', { class: 'ic' })]) : null;
  const box = el('div', { class: 'arc-panel', id: slug === 'x' ? 'map' : 'region-' + slug },
    [map, el('div', { class: 'arc-inreg' }, [list].concat(button ? [button] : []))]);
  page.body.appendChild(box);
  return { map: map, marks: marks, list: list, rows: items, button: button, label: label };
}

function build(bodyClass, scripts) {
  const page = new Page(bodyClass);
  const main = panel(page, 'x', ROWS);
  const other = panel(page, 'y', ['t1', 't2', 'n1']);          // a second panel, as the Map page has: its map stays out of it
  (scripts || [BASE, ARCHIVE]).forEach((file) => page.run(file));
  return { page: page, main: main, other: other };
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
  deq(Object.keys(t.main.button.listeners), []);
  deq(done(t.page), []);
});

// ---------------------------------------------------------------- the two together: a cluster marker whose rows are hidden

check('both: a press on a cluster marker of hidden rows opens the list and focuses the row, without scrolling to the button', () => {
  const t = build('p-region');
  const p = t.main;
  const marker = mark(p, 'mk-cluster', 't8 t9');
  eq(marker.classList.contains('is-linked'), true);
  eq(who(row(p, 't8').offsetParent), 'nothing');
  marker.click();
  eq(p.list.classList.contains('arc-collapsed'), false);
  eq(p.button.getAttribute('aria-expanded'), 'true');
  // archive.js opens the list and focuses its first new row; base.js then centres the marker's row and focuses its
  // link without another scroll. The button is not scrolled to: the list opened
  deq(done(t.page), ['focus: the link of row t8', 'scroll: row t8 {"block":"center"}', 'focus: the link of row t8 {"preventScroll":true}']);
  eq(who(t.page.activeElement), 'the link of row t8');
  // a marker whose first row is in view opens nothing
  const again = build('p-region');
  mark(again.main, 'mk-cluster', 't2 t3').click();
  eq(again.main.list.classList.contains('arc-collapsed'), true);
  deq(done(again.page), ['scroll: row t2 {"block":"center"}', 'focus: the link of row t2 {"preventScroll":true}']);
});

console.log(checks + ' checks passed');
