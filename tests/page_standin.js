'use strict';
/* A stand-in for the browser, shared by tests/trips_js_harness.js, tests/ticklist_js_harness.js,
   tests/profile_js_harness.js and tests/viewer_js_harness.js. Neither a test nor a harness: it checks nothing by itself,
   and unittest never collects it (it is not Python, and its name does not start with test_). There is one copy, so that
   the harnesses cannot come to disagree about what a browser does.

   open(model, scripts, opts) builds just enough of a document from a page that the site generator wrote, runs the
   page's scripts against it and returns the tab the page is open in.
   - model: { pathname, body, indexes }. pathname is the address the page is served at; body its <body> as a tree of
     { tag, attrs, children } and text; indexes the files a fetch may ask for, { 'search.json': [...] } (none: {}).
   - scripts: [[file name, source], ...], run in this order in one window (explore.js, then the page's own script: the
     order the bundle has them).
   - opts: { search, hash } the query string and the fragment the page is opened with; navType the type of the
     navigation entry ('navigate' unless said; 'back_forward'); fragmentPopstate: false a browser that sends no
     popstate when only the fragment changes; refused: true a browser that refuses every write to the history from the
     start (a page opened from a file); state: the history state the page's entry already holds (a reload of an entry
     the page pushed; null unless said).

   history and location are a list of addresses and a position in it. An address is spelled as the URL Standard spells
   it (Node's own URL class, the parser browsers implement), so location.search reads back an apostrophe as %27 where
   the page wrote "'". Back from the first entry leaves the page (left()). A link of the page to one of its own
   fragments (follow) makes the browser's own entry: the same address with the fragment. Whenever the visitor arrives
   on another entry of the page the stand-in sends popstate, also when only the fragment differs, and then hashchange
   when the fragment differs, as browsers do (Chrome 155, at the gate: a press on a year link of the Trips page sent
   popstate, then hashchange). fragmentPopstate: false is a browser that sends no popstate when only the fragment
   changes, as some older ones did not: the hashchange is then all the page hears. Time is a counter the checks move:
   setTimeout, clearTimeout and Date.now follow it. fetch answers at once with the model's index. Every pushState and
   replaceState is kept (calls(), and counted: pushes(), replaces()), so a check can say that a step wrote nothing.
   refuse(true) is a browser that throws on both from then on, as one does for a page opened from a file, until
   refuse(false). Each entry keeps the state pushState or replaceState gave it (history.state; null for the first entry
   and for one a fragment link made), a copy, as a browser keeps a structured clone. history.back() and forward() are
   the page's own traversals: kept in order (traversals()) and, as in a browser, not made at once but as a task of their
   own, the next time the clock moves (pause(0) is enough); popstate comes then. Selectors: a tag, classes, #id, [attr],
   [attr="value"] and :not(...) of those, joined by spaces (descendants), and lists of those (commas), for
   querySelectorAll, querySelector, matches and closest. A selector or a call the stand-in lacks throws and fails the
   run: add it here. Layout, focus and scrolling are not modelled; this is not a browser.

   The tab: body, byId(id), one(scope, selector, what) (the one element a selector finds, or the run fails),
   press(element) (a click), fire(element, type) (any other event of an element, returned), follow(link), and visitor:
   what the visitor of any page does (pause, back, forward, refuse) and sees of the history (stack, at, address, left,
   calls, pushes, replaces, state, traversals, fetched). A harness adds the page's own controls to visitor. */
const assert = require('assert');
const vm = require('vm');

const eq = assert.strictEqual;
const ORIGIN = 'https://example.test';

const PART = /^(?:\.([\w-]+)|#([\w-]+)|\[([\w-]+)(?:=(?:"([^"]*)"|'([^']*)'))?\]|:not\(([^()\s]+)\))/;
function compound(text, whole) {
  const head = /^([a-zA-Z][\w-]*)?/.exec(text);
  const tests = head[1] ? [(el) => el.tagName === head[1].toUpperCase()] : [];
  let rest = text.slice(head[0].length);
  while (rest) {
    const m = PART.exec(rest);
    if (!m) throw new Error('the stand-in cannot read the selector ' + JSON.stringify(whole));
    const value = m[4] !== undefined ? m[4] : m[5];
    if (m[1]) tests.push((el) => el.classList.contains(m[1]));
    else if (m[2]) tests.push((el) => el.id === m[2]);
    else if (m[6]) { const not = compound(m[6], whole); tests.push((el) => !not(el)); }
    else tests.push((el) => el.hasAttribute(m[3]) && (value === undefined || el.getAttribute(m[3]) === value));
    rest = rest.slice(m[0].length);
  }
  if (!tests.length) throw new Error('the stand-in cannot read the selector ' + JSON.stringify(whole));
  return (el) => tests.every((t) => t(el));
}
// a selector list: its selectors are the parts between the commas that are neither in a quoted value nor in :not(...)
function list(sel) {
  const out = [];
  let quote = '', depth = 0, from = 0;
  for (let i = 0; i < sel.length; i++) {
    const c = sel.charAt(i);
    if (quote) { if (c === quote) quote = ''; } else if (c === '"' || c === "'") quote = c;
    else if (c === '(') depth++;
    else if (c === ')') depth--;
    else if (c === ',' && !depth) { out.push(sel.slice(from, i)); from = i + 1; }
  }
  return out.concat([sel.slice(from)]);
}
function matcher(sel) {
  const chains = list(String(sel)).map((one) => one.trim().split(/\s+/).map((part) => compound(part, sel)));
  const one = (chain, el) => {
    if (!chain[chain.length - 1](el)) return false;
    let i = chain.length - 2;
    for (let p = el.parentNode; p && i >= 0; p = p.parentNode) if (chain[i](p)) i--;
    return i < 0;
  };
  return (el) => chains.some((chain) => one(chain, el));
}

class Text {
  constructor(text) { this.text = String(text); this.parentNode = null; }
  get textContent() { return this.text; }
}
class El {
  constructor(tag, attrs) {
    this.tagName = String(tag).toUpperCase();
    this.attrs = Object.assign({}, attrs);
    this.childNodes = [];
    this.parentNode = null;
    this.listeners = {};
    this.tabIndex = this.attrs.tabindex === undefined ? -1 : Number(this.attrs.tabindex);
    this.checked = 'checked' in this.attrs;
    this.held = null;                         // what an <input> holds, or the <select> option chosen, once set
    const self = this;
    const names = () => (self.attrs.class || '').split(/\s+/).filter(Boolean);
    this.classList = {
      contains: (k) => names().indexOf(k) !== -1,
      add: (k) => { self.classList.toggle(k, true); },
      remove: (k) => { self.classList.toggle(k, false); },
      toggle: (k, force) => {
        const on = force === undefined ? names().indexOf(k) === -1 : !!force;
        self.attrs.class = names().filter((x) => x !== k).concat(on ? [k] : []).join(' ');
        return on;
      },
    };
    // el.dataset.filter is the attribute data-filter; an attribute the element lacks reads undefined
    this.dataset = new Proxy({}, { get: (_t, prop) => (typeof prop === 'string' ? self.attrs['data-' + prop.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase())] : undefined) });
  }
  get id() { return this.attrs.id || ''; }
  set id(v) { this.attrs.id = String(v); }
  get className() { return this.attrs.class || ''; }
  set className(v) { this.attrs.class = String(v); }
  get type() { return this.attrs.type || ''; }
  set type(v) { this.attrs.type = String(v); }
  get hidden() { return 'hidden' in this.attrs; }
  set hidden(v) { if (v) this.attrs.hidden = ''; else delete this.attrs.hidden; }
  get firstChild() { return this.childNodes[0] || null; }
  get textContent() { return this.childNodes.map((c) => c.textContent).join(''); }
  set textContent(v) {
    this.childNodes.forEach((c) => { c.parentNode = null; });
    this.childNodes = [];
    if (String(v) !== '') this.appendChild(new Text(v));
  }
  get options() { return this.descendants().filter((d) => d.tagName === 'OPTION'); }
  // an <option> without a value attribute has its text for a value; a <select> starts on its first option and takes
  // only a value one of its options has (anything else leaves it on none: '')
  get value() {
    if (this.tagName === 'OPTION') return this.attrs.value !== undefined ? this.attrs.value : this.textContent;
    if (this.tagName === 'SELECT') return this.held !== null ? this.held : (this.options[0] ? this.options[0].value : '');
    return this.held !== null ? this.held : (this.attrs.value || '');
  }
  set value(v) {
    v = String(v);
    this.held = this.tagName === 'SELECT' && !this.options.some((o) => o.value === v) ? '' : v;
  }
  appendChild(child) {
    if (child.parentNode) child.parentNode.removeChild(child);     // a node is in one place: appending moves it
    child.parentNode = this;
    this.childNodes.push(child);
    return child;
  }
  insertBefore(child, ref) {
    if (ref == null) return this.appendChild(child);
    if (this.childNodes.indexOf(ref) < 0) throw new Error('insertBefore: the reference is not a child of this element');
    if (child.parentNode) child.parentNode.removeChild(child);
    child.parentNode = this;
    this.childNodes.splice(this.childNodes.indexOf(ref), 0, child);
    return child;
  }
  removeChild(child) {
    const i = this.childNodes.indexOf(child);
    if (i < 0) throw new Error('removeChild: not a child of this element');
    this.childNodes.splice(i, 1);
    child.parentNode = null;
    return child;
  }
  hasAttribute(name) { return name in this.attrs; }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  removeAttribute(name) { delete this.attrs[name]; }
  descendants() {
    const out = [];
    this.childNodes.forEach((c) => { if (c instanceof El) { out.push(c); c.descendants().forEach((d) => out.push(d)); } });
    return out;
  }
  contains(other) { for (let p = other; p; p = p.parentNode) if (p === this) return true; return false; }
  querySelectorAll(sel) { return this.descendants().filter(matcher(sel)); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  matches(sel) { return matcher(sel)(this); }
  closest(sel) {
    const test = matcher(sel);
    for (let p = this; p instanceof El; p = p.parentNode) if (test(p)) return p;
    return null;
  }
  addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); }
  focus() {}
  scrollIntoView() {}
}
function grow(node) {
  if (typeof node === 'string') return new Text(node);
  const el = new El(node.tag, node.attrs);
  node.children.forEach((c) => el.appendChild(grow(c)));
  return el;
}
// a promise that has already settled, and settles what follows it at once: no check has to wait for a tick
function settled(ok, value) {
  return {
    then(onOk, onFail) {
      const fn = ok ? onOk : onFail;
      if (!fn) return settled(ok, value);
      try { return settled(true, fn(value)); } catch (e) { return settled(false, e); }
    },
  };
}

function open(model, scripts, opts) {
  opts = opts || {};
  const body = grow(model.body);
  const everything = () => [body].concat(body.descendants());
  const byId = (id) => everything().filter((e) => e.id === id)[0] || null;
  // ---- time
  let clock = 1000000, timers = [], ids = 0;
  const wait = (ms) => {
    const until = clock + ms;
    for (;;) {
      const due = timers.filter((t) => t.at <= until).sort((a, b) => a.at - b.at || a.id - b.id)[0];
      if (!due) break;
      timers = timers.filter((t) => t !== due);
      clock = Math.max(clock, due.at);
      due.fn();
    }
    clock = until;
  };
  // ---- history and location
  const spell = (url, base) => { const u = new URL(url, ORIGIN + base); return u.pathname + u.search + u.hash; };
  const hist = { entries: [spell(model.pathname + (opts.search || '') + (opts.hash || ''), '/')], at: 0, calls: [], left: false, refused: !!opts.refused };
  const refusal = () => { if (hist.refused) throw new Error('SecurityError: the history cannot be written'); };
  // each entry's state (history.state), a copy as a browser keeps one; the page's own back() and forward() calls
  hist.states = [opts.state === undefined ? null : JSON.parse(JSON.stringify(opts.state))];
  hist.traversals = [];
  const keep = (s) => (typeof structuredClone === 'function' ? structuredClone(s) : JSON.parse(JSON.stringify(s === undefined ? null : s)));
  const here = () => hist.entries[hist.at];
  const loc = {};
  ['pathname', 'search', 'hash'].forEach((k) => Object.defineProperty(loc, k, { get: () => new URL(here(), ORIGIN)[k], enumerable: true }));
  const short = (url) => { eq(url.indexOf(model.pathname), 0, 'the address left the page: ' + url); return url.slice(model.pathname.length); };
  const heard = {};
  const fire = (bag, target, type) => {
    const ev = { type: type, target: target, defaultPrevented: false, preventDefault() { ev.defaultPrevented = true; } };
    (bag[type] || []).slice().forEach((fn) => fn.call(target, ev));
    return ev;
  };
  // the visitor is on another entry of the page than a moment ago (it was at `from`): popstate, then hashchange when
  // the fragment differs. opts.fragmentPopstate === false: no popstate when the fragment is all that differs
  const arrived = (from) => {
    const to = new URL(here(), ORIGIN);
    const fragmentOnly = to.pathname === from.pathname && to.search === from.search && to.hash !== from.hash;
    if (!(fragmentOnly && opts.fragmentPopstate === false)) fire(heard, sandbox, 'popstate');
    if (to.hash !== from.hash) fire(heard, sandbox, 'hashchange');
  };
  const step = (by) => {
    if (hist.at + by < 0) { hist.left = true; return; }                 // nothing before the page's first entry
    if (hist.at + by >= hist.entries.length) return;
    const from = new URL(here(), ORIGIN);
    hist.at += by;
    arrived(from);
  };
  // a press on a link of the page to one of its own fragments. Unless a listener stops it or the address already ends
  // with that fragment, the browser makes a new entry: the same address with the fragment (no call of the page's)
  const follow = (a) => {
    const href = a.getAttribute('href') || '';
    eq(href.charAt(0), '#', 'the stand-in follows links to a fragment of the page only: ' + href);
    if (fire(a.listeners, a, 'click').defaultPrevented) return;
    const from = new URL(here(), ORIGIN);
    if (from.hash === href) return;
    hist.entries.splice(hist.at + 1, hist.entries.length, from.pathname + from.search + href);
    hist.states.splice(hist.at + 1, hist.states.length, null);
    hist.at++;
    arrived(from);
  };
  const fetched = [];
  const indexes = model.indexes || {};
  const sandbox = {
    document: {
      body: body, readyState: 'complete', getElementById: byId,
      createElement: (tag) => new El(tag, {}), createElementNS: (_ns, tag) => new El(tag, {}), createTextNode: (text) => new Text(text),
    },
    location: loc,
    history: {
      // without a URL (null, or none given) the entry keeps the address the page has
      pushState: (s, _t, url) => {
        refusal();
        const kept = keep(s);
        url = url == null ? here() : spell(url, here());
        hist.entries.splice(hist.at + 1, hist.entries.length, url);    // a new entry drops the ones Forward led to
        hist.states.splice(hist.at + 1, hist.states.length, kept);
        hist.at++;
        hist.calls.push('push ' + short(url));
      },
      replaceState: (s, _t, url) => {
        refusal();
        const kept = keep(s);
        url = url == null ? here() : spell(url, here());
        hist.entries[hist.at] = url;
        hist.states[hist.at] = kept;
        hist.calls.push('replace ' + short(url));
      },
      get state() { return hist.states[hist.at]; },
      // a traversal the page asks for is made in a task of its own, the next time the clock moves (pause(0) is enough)
      back: () => { hist.traversals.push('back'); timers.push({ id: ++ids, at: clock, fn: () => step(-1) }); },
      forward: () => { hist.traversals.push('forward'); timers.push({ id: ++ids, at: clock, fn: () => step(1) }); },
    },
    performance: { getEntriesByType: (t) => (t === 'navigation' ? [{ type: opts.navType || 'navigate' }] : []) },
    setTimeout: (fn, ms) => { timers.push({ id: ++ids, at: clock + (ms || 0), fn: fn }); return ids; },
    clearTimeout: (id) => { timers = timers.filter((t) => t.id !== id); },
    Date: { now: () => clock },
    fetch: (url) => {
      fetched.push(url);
      if (!(url in indexes)) return settled(false, new Error('no such file: ' + url));
      return settled(true, { ok: true, json: () => JSON.parse(JSON.stringify(indexes[url])) });
    },
    addEventListener: (type, fn) => { (heard[type] = heard[type] || []).push(fn); },
    console: console,
  };
  sandbox.window = sandbox;
  const context = vm.createContext(sandbox);
  scripts.forEach(([name, source]) => vm.runInContext(source, context, { filename: name }));

  const one = (scope, sel, what) => {
    const hits = scope.querySelectorAll(sel);
    eq(hits.length, 1, 'the page has ' + hits.length + ' elements for ' + what + ' (' + sel + ')');
    return hits[0];
  };
  return {
    body: body,
    byId: byId,
    one: one,
    press: (el) => { fire(el.listeners, el, 'click'); },
    fire: (el, type) => fire(el.listeners, el, type),
    follow: follow,
    visitor: {
      // ---- what the visitor of any page does
      pause: (ms) => { wait(ms === undefined ? 2000 : ms); },                       // time passes (two seconds unless said)
      back: () => { step(-1); },
      forward: () => { step(1); },
      refuse: (on) => { hist.refused = !!on; },           // the browser throws on pushState and replaceState while this is on
      // ---- what the visitor sees of the history
      stack: () => hist.entries.map(short),                 // every entry of the page, '' for its plain address
      at: () => hist.at,
      address: () => short(here()),
      left: () => hist.left,
      calls: () => hist.calls.slice(),                      // every pushState / replaceState so far: 'push ?q=…', 'replace '
      pushes: () => hist.calls.filter((c) => c.indexOf('push ') === 0).length,
      replaces: () => hist.calls.filter((c) => c.indexOf('replace ') === 0).length,   // the replaceState calls alone
      state: () => hist.states[hist.at],                    // the state of the entry the visitor is on
      traversals: () => hist.traversals.slice(),            // the page's own history.back() and forward() calls, in order
      fetched: () => fetched.slice(),
    },
  };
}

module.exports = { open: open };
