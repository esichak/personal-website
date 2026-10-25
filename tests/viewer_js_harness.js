#!/usr/bin/env node
'use strict';
/* Phase 11: the photo viewer and the copy-link control of assets/js/base.js. The script is run as it is against the
   stand-in for the browser (tests/page_standin.js), on a page assembled from markup the site generator writes
   (tests/test_viewer_js.py, page_model: a journal day's photos from series.day_photos, a contact sheet from
   series.thumbs, a report's full-size photo rows from core.photo_rows, the three copy controls core.copy_link writes and
   core.lightbox()), and a reader's presses, keys, fingers and Back are played on it:

     fixture            base.js runs; a press on a photo opens the viewer; a press on a copy control copies
     pushState on open  opening adds one history entry at the page's own address holding {lb: true}; moving within the
                        viewer writes nothing more; a press with a modifier key opens the file and writes nothing
     popstate closing   Back (popstate) closes the viewer and goes back no further; so does a second Back after Back,
                        Forward and another photo (Forward lands on the viewer's old entry, which holds {lb: true})
     close button       closing takes the viewer's entry back off with history.back(), once
     Escape             the dialog's own cancel and close: back once, never over-popping (a second Escape, an Escape
                        after Back closed the viewer)
     tap outside        a tap on the backdrop closes and goes back once; a tap on the photo or the bar does not close
     no over-popping    a browser that refuses pushState still opens the viewer, and closing goes nowhere; refused
                        while on the viewer's old entry, closing stays on it
     error state        an error of the photo while open: 'This photo could not be loaded' in the caption, the dialog
                        marked lb--error, the file link (.lb-file, 'Open the file') shown with the photo's href; moving
                        to another photo takes all three back; an error while closed changes nothing
     announce           opening says 'Photo N of M. <alt>' in #lb-live once the dialog is up (#lb-live was empty
                        when showModal ran); moving says the photo moved to; each group counts its own photos
     pointers           a primary swipe of more than 40 px changes the photo (exactly 40 does not); a second finger
                        is ignored; pointercancel ends the swipe; a swipe that ends on the backdrop does not close; a
                        tap outside after it does
     srcset             a capped set (.th and .sm: the journal's) gets ', <href> <width>w' appended, the width the
                        thumbnail's own; a full set (holding the href) is passed as it is; never twice; the thumbnail
                        keeps its own set; a thumbnail without a width-described set opens the file alone
     share              (hover: none) and navigator.share: every control reads its data-share ('Share this page' on the
                        report's share row) and has is-share; a press calls navigator.share({title, url}) inside the
                        click, after navigator.canShare when the browser has it; a dismissed sheet (AbortError) does
                        nothing; a refused sheet, a rejection without a reason, one that throws at once or canShare
                        false or throwing: the clipboard path
     desktop copy       (hover: hover), or no navigator.share, or no matchMedia: nothing relabelled, a press never asks
                        for the sheet; 'Link copied' under the control for 4 s, or the field to copy by hand when the
                        clipboard refuses or is missing (a second press or Escape closes it)

   Run by tests/test_viewer_js.py (skipped when node is missing); by hand:
     node tests/viewer_js_harness.js [base.js] [page.json]
   The optional arguments point at another copy of the script (used to prove the harness fails a wrong one) and at the
   page the runner wrote; without the second, the page is asked of `python3 tests/test_viewer_js.py --model` ($PYTHON
   names another interpreter). Every failed check prints 'FAIL <label>' on stderr and throws, so the process exits
   non-zero; a run without one ends with '<N> checks passed' on stdout.

   page_standin.js gives the document tree, selectors (lists too), the history (each entry's state, the page's own
   back() as a task of its own), timers and the clock. What this page needs beyond it is added from here, by a first
   script run in the same window (extras, below):
   - a document above <html> above <body>: querySelector(All), addEventListener, activeElement, title. Events are sent
     to the target and then, for those that bubble, to each node above it up to the document; a listener that throws
     fails the check (a browser would report it and go on). Nothing reaches window but what the stand-in sends there
     (popstate). Focus: focus() moves activeElement unless the element or something around it is hidden or it is not
     in the page; blur() hands it to <body>; no focus events are sent.
   - <dialog>: open (the attribute), showModal() (nothing when already open as a modal, InvalidStateError when open
     otherwise), close() (the attribute off now, the close event in a task of its own, as the HTML standard has it), and
     a close request (Escape): keydown at the focused element, then, unless prevented, cancel at the open modal dialog
     and, unless cancelled, close(). The dialog's own focusing steps and the top layer are not modelled.
   - src, alt and href read and write their attributes; style is a bag of properties; layout is a box of zeros.
   - navigator.share and canShare, navigator.clipboard.writeText and matchMedia('(hover: none)'), as each tab is
     opened with (cfg). What they are asked is kept on the document node, with whether it came inside a click. Their
     promises settle in a task of their own, the next time the clock moves (pause(0)), as a share sheet or the
     clipboard answers after the press has been handled. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const childProcess = require('child_process');
const standin = require('./page_standin.js');

const BASE = path.resolve(process.argv[2] || path.join(__dirname, '..', 'assets', 'js', 'base.js'));
assert.ok(fs.existsSync(BASE), 'missing ' + BASE);
const SOURCE = fs.readFileSync(BASE, 'utf8');
const MODEL = JSON.parse(process.argv[3] ? fs.readFileSync(process.argv[3], 'utf8')
  : childProcess.execFileSync(process.env.PYTHON || 'python3', [path.join(__dirname, 'test_viewer_js.py'), '--model'], { encoding: 'utf8' }));

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
const ok = assert.ok;
// objects made inside the window have its prototypes: compared as JSON
const plain = (x) => (x === undefined ? undefined : JSON.parse(JSON.stringify(x)));
const deq = (actual, expected, msg) => assert.deepStrictEqual(plain(actual), plain(expected), msg);

// ---------------------------------------------------------------- the stand-in, and what this page adds to it

// run inside the window, before base.js (see the header)
function extras(cfg) {
  'use strict';
  var body = document.body;
  var proto = Object.getPrototypeOf(body);
  // the document node an element is in, or null when it is not in the page
  var docOf = function (el) {
    var p = el;
    while (p && p.parentNode) p = p.parentNode;
    return p && p.page ? p : null;
  };
  if (!Object.prototype.hasOwnProperty.call(proto, 'blur')) {     // once: every tab's elements share the class
    ['src', 'alt', 'href'].forEach(function (name) {
      Object.defineProperty(proto, name, {
        get: function () { return this.getAttribute(name) || ''; },
        set: function (v) { this.setAttribute(name, v); },
        configurable: true,
      });
    });
    proto.focus = function () {
      var d = docOf(this);
      if (!d) return;
      for (var p = this; p; p = p.parentNode) if (p.hidden) return;
      d.page.activeElement = this;
    };
    proto.blur = function () {
      var d = docOf(this);
      if (d && d.page.activeElement === this) d.page.activeElement = d.page.body;
    };
    proto.select = function () {};
    proto.getBoundingClientRect = function () { return { left: 0, right: 0, top: 0, bottom: 0, width: 0, height: 0, x: 0, y: 0 }; };
    Object.defineProperty(proto, 'offsetWidth', { get: function () { return 0; }, configurable: true });
    Object.defineProperty(proto, 'style', { get: function () { return this.css || (this.css = {}); }, configurable: true });
  }
  var doc = document.createElement('x-document'), html = document.createElement('html');
  doc.appendChild(html);
  html.appendChild(body);
  html.clientWidth = 390;
  doc.page = document;
  doc.cfg = cfg;
  doc.dispatching = '';
  doc.shares = []; doc.canShares = []; doc.clips = []; doc.shown = [];
  document.documentElement = html;
  document.title = cfg.title;
  document.activeElement = body;
  document.querySelectorAll = function (sel) { return doc.querySelectorAll(sel); };
  document.querySelector = function (sel) { return doc.querySelector(sel); };
  document.addEventListener = function (type, fn) { doc.addEventListener(type, fn); };

  var STILL = { close: true, cancel: true, error: true, load: true };   // events that do not bubble
  doc.dispatch = function (target, type, init) {
    var ev = { type: type, target: target, bubbles: !STILL[type], cancelable: type !== 'close' && type !== 'error',
               defaultPrevented: false, button: 0, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false };
    Object.keys(init || {}).forEach(function (k) { ev[k] = init[k]; });
    var stopped = false;
    ev.preventDefault = function () { if (ev.cancelable) ev.defaultPrevented = true; };
    ev.stopPropagation = function () { stopped = true; };
    var route = [target];
    if (ev.bubbles) for (var p = target.parentNode; p; p = p.parentNode) route.push(p);
    var was = doc.dispatching;
    doc.dispatching = type;
    try {
      for (var i = 0; i < route.length && !stopped; i++) {
        ev.currentTarget = route[i];
        (route[i].listeners[type] || []).slice().forEach(function (fn) { fn.call(route[i], ev); });
      }
    } finally {
      doc.dispatching = was;
    }
    return ev;
  };

  Array.prototype.forEach.call(body.querySelectorAll('dialog'), function (dlg) {
    dlg.modalFlag = false;
    Object.defineProperty(dlg, 'open', { get: function () { return dlg.hasAttribute('open'); } });
    dlg.showModal = function () {
      if (dlg.hasAttribute('open') && dlg.modalFlag) return;
      if (dlg.hasAttribute('open')) throw new Error('InvalidStateError: the dialog is open, and not as a modal');
      dlg.setAttribute('open', '');
      dlg.modalFlag = true;
      var live = dlg.querySelector('#lb-live');
      doc.shown.push(live ? live.textContent : null);              // what #lb-live said as the dialog came up
    };
    dlg.close = function () {
      if (!dlg.hasAttribute('open')) return;
      dlg.removeAttribute('open');
      dlg.modalFlag = false;
      window.setTimeout(function () { doc.dispatch(dlg, 'close'); }, 0);
    };
  });
  doc.escape = function () {
    var kd = doc.dispatch(document.activeElement || body, 'keydown', { key: 'Escape' });
    if (kd.defaultPrevented) return;
    Array.prototype.forEach.call(doc.querySelectorAll('dialog[open]'), function (dlg) {
      if (!dlg.modalFlag) return;
      if (!doc.dispatch(dlg, 'cancel').defaultPrevented) dlg.close();
    });
  };

  // a promise, settled by settle(); then() hands on what its callback returns. A callback that throws fails the run (a
  // browser would report an unhandled rejection)
  var Later = function () { this.state = null; this.value = undefined; this.subs = []; };
  Later.prototype.settle = function (state, value) {
    if (this.state) return;
    this.state = state;
    this.value = value;
    this.subs.splice(0).forEach(function (run) { run(); });
  };
  Later.prototype.then = function (onOk, onFail) {
    var self = this, next = new Later();
    var run = function () {
      var fn = self.state === 'ok' ? onOk : onFail;
      if (typeof fn !== 'function') next.settle(self.state, self.value);
      else next.settle('ok', fn(self.value));
    };
    if (self.state) run(); else self.subs.push(run);
    return next;
  };
  // the answer of a share sheet or of the clipboard: in a task of its own, the next time the clock moves
  var answer = function (fine, value) {
    var p = new Later();
    window.setTimeout(function () { p.settle(fine ? 'ok' : 'fail', value); }, 0);
    return p;
  };
  var named = function (name, message) { var e = new Error(message); e.name = name; return e; };
  var inClick = function () { return doc.dispatching === 'click'; };
  var nav = {};
  if (cfg.share) {
    nav.share = function (data) {
      doc.shares.push({ keys: Object.keys(data).sort().join(' '), title: data.title, url: data.url, inClick: inClick() });
      var how = doc.cfg.shareAnswer;
      if (how === 'throw') throw new TypeError('share() refused at once');
      if (how === 'ok') return answer(true);
      return answer(false, { abort: named('AbortError', 'Share canceled'), refused: named('NotAllowedError', 'Permission denied'),
                             type: new TypeError('Not shareable'), nothing: undefined }[how]);
    };
  }
  Object.defineProperty(nav, 'canShare', {
    get: function () {
      var c = doc.cfg.canShare;
      if (c === undefined) return undefined;
      return function (data) {
        doc.canShares.push({ keys: Object.keys(data).sort().join(' '), url: data.url });
        if (c === 'throw') throw new TypeError('canShare() threw');
        return c;
      };
    },
  });
  Object.defineProperty(nav, 'clipboard', {
    get: function () {
      var c = doc.cfg.clipboard;
      if (c === 'none') return undefined;
      return {
        writeText: function (text) {
          doc.clips.push({ text: text, inClick: inClick() });
          return c === 'ok' ? answer(true) : answer(false, named('NotAllowedError', 'Write permission denied'));
        },
      };
    },
  });
  window.navigator = nav;
  if (cfg.media) {
    window.matchMedia = function (q) {
      return { media: q, matches: (q === '(hover: none)' && cfg.hover === 'none') || (q === '(hover: hover)' && cfg.hover === 'hover') };
    };
  }
}

// how a tab is opened: a desktop that has navigator.share (as Safari and Edge do), a phone with a share sheet, ...
const DESKTOP = { hover: 'hover', share: true, clipboard: 'ok', media: true };
const PLAIN = { hover: 'hover', share: false, clipboard: 'ok', media: true };
const PHONE = { hover: 'none', share: true, clipboard: 'ok', media: true, shareAnswer: 'ok' };

function open(cfg, opts) {
  const all = Object.assign({ title: MODEL.title, shareAnswer: 'ok' }, cfg);
  const EXTRAS = '(' + extras.toString() + ')(' + JSON.stringify(all) + ');\n';
  const model = { pathname: MODEL.pathname, body: MODEL.body, indexes: {} };
  return standin.open(model, [['viewer-extras.js', EXTRAS], [path.basename(BASE), SOURCE]], opts);
}
const docOf = (tab) => tab.body.parentNode.parentNode;
const send = (tab, el, type, init) => docOf(tab).dispatch(el, type, init);
const active = (tab) => docOf(tab).page.activeElement;
const settle = (tab) => tab.visitor.pause(0);                      // the tasks that are due now: close, back, answers

// the parts of the page
function parts(tab) {
  const lb = tab.one(tab.body, 'dialog.lb', 'the viewer');
  return {
    lb: lb,
    img: tab.one(lb, '.lb-img', 'the photo'),
    bar: tab.one(lb, '.lb-bar', 'the bar'),
    n: tab.one(lb, '.lb-n', 'the counter'),
    cap: tab.one(lb, '.lb-cap', 'the caption'),
    file: tab.one(lb, 'a.lb-file', 'the file link'),
    prev: tab.one(lb, '.lb-prev', 'the Previous button'),
    next: tab.one(lb, '.lb-next', 'the Next button'),
    close: tab.one(lb, '.lb-close', 'the Close button'),
    live: tab.one(lb, '#lb-live', 'the live region'),
    J: tab.body.querySelectorAll('#day-3 a.jph'),                  // a journal day's photos: the capped set
    S: tab.body.querySelectorAll('#day-4 a.ser-ph'),               // a contact sheet: no width-described set
    R: tab.body.querySelectorAll('#photos a.jph'),                 // a report's photo rows: the full set
    title: tab.one(tab.body, '.ser-acts .copy-btn', 'the title block copy control'),
    entry: tab.one(tab.body, '#day-3 .copy-btn', 'the entry copy control'),
    page: tab.one(tab.body, '.rep-share .copy-btn', 'the share row copy control'),
  };
}
const thumb = (a) => a.querySelector('img');
const alt = (a) => thumb(a).getAttribute('alt');

// a reader's hands
const pressPhoto = (tab, a, mods) => send(tab, thumb(a), 'click', mods);       // the image inside the link is what is hit
const press = (tab, el) => send(tab, el.querySelector('svg') || el, 'click');  // an icon button: its glyph is what is hit
const key = (tab, k) => send(tab, active(tab) || tab.body, 'keydown', { key: k });
const escape = (tab) => docOf(tab).escape();
const pointer = (tab, type, target, x, primary) => send(tab, target, type, { clientX: x, clientY: 300, isPrimary: primary !== false,
                                                                             pointerId: primary !== false ? 1 : 2, pointerType: 'touch' });
// a primary pointer down at x0, up at x1 on the same element, and the click that follows
function swipe(tab, target, x0, x1) {
  pointer(tab, 'pointerdown', target, x0);
  pointer(tab, 'pointerup', target, x1);
  send(tab, target, 'click');
}
const tapOutside = (tab, v) => swipe(tab, v.lb, 200, 200);

// what the reader sees of the viewer
function seen(v) {
  return { open: v.lb.open, n: v.n.textContent, cap: v.cap.textContent, live: v.live.textContent,
           src: v.img.getAttribute('src'), srcset: v.img.getAttribute('srcset'), sizes: v.img.getAttribute('sizes'),
           file: v.file.hidden ? null : v.file.getAttribute('href'), error: v.lb.classList.contains('lb--error') };
}
// the history as the visitor has it: entries, position, the page's own back() calls, left the page
const hist = (tab) => ({ stack: tab.visitor.stack(), at: tab.visitor.at(), backs: tab.visitor.traversals(), left: tab.visitor.left() });
const label = (b) => b.querySelector('.copy-l').textContent;
const msg = (b) => b.parentNode.querySelector('.copy-msg').textContent;
const field = (b) => b.parentNode.querySelector('.copy-pop');

// ---------------------------------------------------------------- fixture

let tab, v;
check('fixture: base.js runs on a page of generated parts', () => {
  tab = open(PLAIN);
  v = parts(tab);
  eq(v.J.length, 3);
  eq(v.S.length, 2);
  eq(v.R.length, 2);
});
check('fixture: the viewer is the markup core.lightbox() writes, closed', () => {
  eq(v.lb.getAttribute('aria-label'), 'Photo viewer');
  eq(v.lb.getAttribute('aria-describedby'), 'lb-live');
  eq(v.lb.open, false);
  eq(v.file.hidden, true);
  eq(v.file.hasAttribute('href'), false);
  eq(v.file.textContent, 'Open the file');
  eq(v.live.getAttribute('aria-live'), 'polite');
});
check('fixture: a press on a photo opens the viewer', () => {
  const ev = pressPhoto(tab, v.J[0]);
  ok(v.lb.open, 'the viewer did not open');
  ok(ev.defaultPrevented, 'the link was followed as well');
  eq(seen(v).n, 'PHOTO 1 / 3');
  press(tab, v.close);
  settle(tab);
  eq(v.lb.open, false);
});
check('fixture: a press on a copy control copies its URL', () => {
  const t = open(PLAIN), p = parts(t);
  press(t, p.page);
  deq(docOf(t).clips, [{ text: p.page.getAttribute('data-copy'), inClick: true }]);
});

// ---------------------------------------------------------------- pushState on open

check('pushState on open: one entry at the address the page has, holding {lb: true}', () => {
  const t = open(PLAIN), p = parts(t);
  deq(hist(t), { stack: [''], at: 0, backs: [], left: false });
  eq(t.visitor.state(), null);
  pressPhoto(t, p.J[0]);
  ok(p.lb.open);
  deq(t.visitor.calls(), ['push ']);
  deq(hist(t), { stack: ['', ''], at: 1, backs: [], left: false });
  deq(t.visitor.state(), { lb: true });
});
check('pushState on open: moving within the viewer writes nothing more', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[1]);
  press(t, p.next);
  press(t, p.prev);
  key(t, 'ArrowLeft');
  key(t, 'ArrowRight');
  key(t, 'ArrowRight');
  t.visitor.pause();
  ok(p.lb.open);
  eq(seen(p).n, 'PHOTO 3 / 3');
  deq(t.visitor.calls(), ['push ']);
  deq(hist(t), { stack: ['', ''], at: 1, backs: [], left: false });
});
check('pushState on open: a press with a modifier key opens the file and writes nothing', () => {
  const t = open(PLAIN), p = parts(t);
  for (const mods of [{ metaKey: true }, { ctrlKey: true }, { shiftKey: true }, { altKey: true }]) {
    const ev = pressPhoto(t, p.J[0], mods);
    eq(ev.defaultPrevented, false, JSON.stringify(mods));
    eq(p.lb.open, false, JSON.stringify(mods));
  }
  deq(t.visitor.calls(), []);
});

// ---------------------------------------------------------------- popstate closing

check('popstate closing: Back closes the viewer and goes back no further', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[0]);
  t.visitor.back();
  eq(p.lb.open, false, 'Back left the viewer open');
  settle(t);
  t.visitor.pause();
  deq(hist(t), { stack: ['', ''], at: 0, backs: [], left: false });
  eq(active(t), p.J[0], 'the focus did not go back to the photo');
});
check('popstate closing: Back, Forward, another photo and Back again: back on the old entry, no further', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[1]);
  t.visitor.back();
  settle(t);
  t.visitor.forward();                                       // onto the viewer's old entry: {lb: true}, the viewer closed
  settle(t);
  eq(p.lb.open, false, 'Forward opened the viewer');
  deq(t.visitor.state(), { lb: true });
  pressPhoto(t, p.J[2]);
  deq(hist(t), { stack: ['', '', ''], at: 2, backs: [], left: false });
  t.visitor.back();
  eq(p.lb.open, false);
  settle(t);
  t.visitor.pause();
  deq(hist(t), { stack: ['', '', ''], at: 1, backs: [], left: false });
});
check('popstate closing: Back and Forward while the viewer is closed open nothing and go nowhere', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[0]);
  t.visitor.back();
  settle(t);
  for (const go of ['forward', 'back', 'forward', 'back']) {
    t.visitor[go]();
    settle(t);
    eq(p.lb.open, false, go);
  }
  deq(hist(t), { stack: ['', ''], at: 0, backs: [], left: false });
});

// ---------------------------------------------------------------- close button

check('close button: closing takes the viewer\'s entry back off, once', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[0]);
  press(t, p.close);
  eq(p.lb.open, false);
  settle(t);
  deq(hist(t), { stack: ['', ''], at: 0, backs: ['back'], left: false });
  eq(t.visitor.state(), null);
  eq(active(t), p.J[0], 'the focus did not go back to the photo');
  t.visitor.pause();
  deq(hist(t), { stack: ['', ''], at: 0, backs: ['back'], left: false });
  eq(p.lb.open, false, 'the Back that took the entry off opened the viewer again');
});
check('close button: three times over, one entry at a time', () => {
  const t = open(PLAIN), p = parts(t);
  for (let i = 0; i < 3; i++) {
    pressPhoto(t, p.R[i % 2]);
    deq(hist(t).at, 1);
    press(t, p.close);
    settle(t);
    deq(hist(t), { stack: ['', ''], at: 0, backs: Array(i + 1).fill('back'), left: false });
  }
  deq(t.visitor.calls(), ['push ', 'push ', 'push ']);
});

// ---------------------------------------------------------------- Escape

check('Escape: closes the viewer and goes back once', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[1]);
  escape(t);
  eq(p.lb.open, false);
  settle(t);
  deq(hist(t), { stack: ['', ''], at: 0, backs: ['back'], left: false });
  eq(active(t), p.J[1]);
});
check('Escape: not over-popping: a second Escape once the viewer is closed goes nowhere', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[0]);
  escape(t);
  settle(t);
  escape(t);
  settle(t);
  t.visitor.pause();
  deq(hist(t), { stack: ['', ''], at: 0, backs: ['back'], left: false });
});
check('Escape: not over-popping: two Escapes before the viewer has closed are one Back', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[0]);
  escape(t);
  escape(t);
  settle(t);
  deq(hist(t), { stack: ['', ''], at: 0, backs: ['back'], left: false });
});
check('Escape: not over-popping: after Back closed the viewer, Escape goes nowhere', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[0]);
  t.visitor.back();
  settle(t);
  escape(t);
  settle(t);
  deq(hist(t), { stack: ['', ''], at: 0, backs: [], left: false });
});

// ---------------------------------------------------------------- tap outside

check('tap outside: a tap on the backdrop closes the viewer and goes back once', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[0]);
  tapOutside(t, p);
  eq(p.lb.open, false, 'a tap outside the photo left the viewer open');
  settle(t);
  deq(hist(t), { stack: ['', ''], at: 0, backs: ['back'], left: false });
});
check('tap outside: a tap on the photo or on the bar leaves the viewer open', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[0]);
  swipe(t, p.img, 200, 200);
  swipe(t, p.bar, 200, 200);
  send(t, p.n, 'click');
  settle(t);
  ok(p.lb.open);
  deq(hist(t), { stack: ['', ''], at: 1, backs: [], left: false });
});

// ---------------------------------------------------------------- no over-popping

check('no over-popping: a browser that refuses pushState still opens the viewer, and closing goes nowhere', () => {
  const t = open(PLAIN, { refused: true }), p = parts(t);
  for (const how of ['close button', 'Escape', 'tap outside']) {
    pressPhoto(t, p.J[0]);
    ok(p.lb.open, how + ': the viewer did not open');
    deq(t.visitor.calls(), [], how);
    if (how === 'close button') press(t, p.close);
    else if (how === 'Escape') escape(t);
    else tapOutside(t, p);
    eq(p.lb.open, false, how);
    settle(t);
    deq(hist(t), { stack: [''], at: 0, backs: [], left: false }, how);
  }
});
check('no over-popping: refused on the viewer\'s old entry (Back, Forward), closing stays on it', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[0]);
  t.visitor.back();
  settle(t);
  t.visitor.forward();
  settle(t);
  t.visitor.refuse(true);
  pressPhoto(t, p.J[1]);
  ok(p.lb.open);
  press(t, p.close);
  settle(t);
  deq(hist(t), { stack: ['', ''], at: 1, backs: [], left: false });
});

// ---------------------------------------------------------------- error state

const UNLOADED = 'This photo could not be loaded';
let et, ev;
check('error state: a photo that does not load says so and offers its file', () => {
  et = open(PLAIN);
  ev = parts(et);
  pressPhoto(et, ev.J[0]);
  eq(seen(ev).file, null);
  eq(seen(ev).error, false);
  send(et, ev.img, 'error');
  const s = seen(ev);
  ok(s.open);
  eq(s.cap, UNLOADED);
  eq(s.file, ev.J[0].getAttribute('href'), 'the file link is not shown with the photo\'s href');
  eq(ev.file.textContent, 'Open the file');
  eq(s.error, true, 'the dialog is not marked lb--error');
  eq(s.n, 'PHOTO 1 / 3');
  // the caption is no live region: the failure is said where the photo was announced
  eq(s.live, 'Photo 1 of 3 could not be loaded');
});
check('error state: moving to another photo takes the message, the mark and the file link back', () => {
  press(et, ev.next);
  let s = seen(ev);
  eq(s.file, null, 'the file link stayed');
  eq(ev.file.hasAttribute('href'), false);
  eq(s.error, false, 'lb--error stayed');
  eq(s.cap, '');                                            // the second photo has no caption
  send(et, ev.img, 'error');
  eq(seen(ev).file, ev.J[1].getAttribute('href'), 'the file link is not the second photo\'s');
  eq(seen(ev).error, true);
  key(et, 'ArrowLeft');
  s = seen(ev);
  eq(s.file, null);
  eq(s.error, false);
  eq(s.cap, ev.J[0].getAttribute('data-cap'));
  ok(s.cap, 'the first photo has a caption');
});
check('error state: an error while the viewer is closed changes nothing', () => {
  press(et, ev.close);
  settle(et);
  const before = seen(ev);
  send(et, ev.img, 'error');
  deq(seen(ev), before);
  eq(seen(ev).file, null);
  eq(seen(ev).error, false);
});
check('error state: reopening after an error starts clean', () => {
  pressPhoto(et, ev.J[2]);
  send(et, ev.img, 'error');
  eq(seen(ev).cap, UNLOADED);
  escape(et);
  settle(et);
  pressPhoto(et, ev.J[0]);
  const s = seen(ev);
  eq(s.file, null);
  eq(s.error, false);
  eq(s.cap, ev.J[0].getAttribute('data-cap'));
});

check('history: a page loaded on a leftover viewer entry forgets its mark', () => {
  // a reload while the viewer was open: the entry still says {lb: true}; the next open must not stack a second one
  const t = open(PLAIN, { state: { lb: true } });
  eq(t.visitor.state(), null, 'the leftover mark was kept');
  const v = parts(t);
  pressPhoto(t, v.J[0]);
  deq(t.visitor.state(), { lb: true });
  press(t, v.close);
  settle(t);
  eq(t.visitor.state(), null);
  eq(t.visitor.at(), 0, 'one close did not take the viewer\'s entry back off');
});

// ---------------------------------------------------------------- announce

check('announce: opening says Photo 1 of 3 and the alt text, once the viewer is up', () => {
  const t = open(PLAIN), p = parts(t);
  ok(alt(p.J[0]), 'the first photo has alt text');
  pressPhoto(t, p.J[0]);
  eq(seen(p).live, 'Photo 1 of 3. ' + alt(p.J[0]));
  deq(docOf(t).shown, [''], '#lb-live was not empty when showModal ran');
});
check('announce: opening another photo says its own place in the group', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[2]);
  eq(seen(p).live, 'Photo 3 of 3. ' + alt(p.J[2]));
  press(t, p.close);
  settle(t);
  pressPhoto(t, p.J[1]);
  eq(seen(p).live, 'Photo 2 of 3. ' + alt(p.J[1]));
  deq(docOf(t).shown, ['', '']);
});
check('announce: moving says the photo moved to', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[0]);
  press(t, p.next);
  eq(seen(p).live, 'Photo 2 of 3. ' + alt(p.J[1]));
  key(t, 'ArrowRight');
  eq(seen(p).live, 'Photo 3 of 3. ' + alt(p.J[2]));
  press(t, p.prev);
  eq(seen(p).live, 'Photo 2 of 3. ' + alt(p.J[1]));
  key(t, 'ArrowLeft');
  eq(seen(p).live, 'Photo 1 of 3. ' + alt(p.J[0]));
});
check('announce: each group counts its own photos', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.R[1]);
  eq(seen(p).live, 'Photo 2 of 2. ' + alt(p.R[1]));
  eq(seen(p).n, 'PHOTO 2 / 2');
  press(t, p.close);
  settle(t);
  pressPhoto(t, p.S[0]);
  eq(seen(p).live, 'Photo 1 of 2. ' + alt(p.S[0]));
});

// ---------------------------------------------------------------- pointers

let pt, pv;
check('pointers: a primary swipe of more than 40 px sideways changes the photo', () => {
  pt = open(PLAIN);
  pv = parts(pt);
  pressPhoto(pt, pv.J[0]);
  swipe(pt, pv.img, 300, 240);
  eq(seen(pv).n, 'PHOTO 2 / 3', 'a swipe to the left did not move on');
  eq(seen(pv).live, 'Photo 2 of 3. ' + alt(pv.J[1]));
  swipe(pt, pv.img, 200, 260);
  eq(seen(pv).n, 'PHOTO 1 / 3', 'a swipe to the right did not move back');
  swipe(pt, pv.img, 300, 260);
  eq(seen(pv).n, 'PHOTO 1 / 3', 'a move of exactly 40 px is a swipe');
  swipe(pt, pv.img, 300, 341);
  eq(seen(pv).n, 'PHOTO 1 / 3', 'a swipe to the right moved before the first photo');
  ok(pv.lb.open);
});
check('pointers: a second finger is ignored (a pinch)', () => {
  swipe(pt, pv.img, 300, 200);
  eq(seen(pv).n, 'PHOTO 2 / 3');
  pointer(pt, 'pointerdown', pv.img, 300);
  pointer(pt, 'pointerdown', pv.img, 500, false);
  pointer(pt, 'pointerup', pv.img, 650, false);
  pointer(pt, 'pointerup', pv.img, 290);
  eq(seen(pv).n, 'PHOTO 2 / 3', 'the second finger moved the photo');
  pointer(pt, 'pointerdown', pv.img, 300);
  pointer(pt, 'pointerdown', pv.img, 100, false);
  pointer(pt, 'pointerup', pv.img, 120, false);
  pointer(pt, 'pointerup', pv.img, 230);
  eq(seen(pv).n, 'PHOTO 3 / 3', 'the first finger\'s swipe was lost to the second');
  ok(pv.lb.open);
});
check('pointers: pointercancel ends the swipe', () => {
  pointer(pt, 'pointerdown', pv.img, 300);
  send(pt, pv.img, 'pointercancel', { isPrimary: true, pointerId: 1, pointerType: 'touch' });
  pointer(pt, 'pointerup', pv.img, 400);
  eq(seen(pv).n, 'PHOTO 3 / 3', 'a cancelled pointer swiped');
});
check('pointers: a swipe that ends on the backdrop does not close; a tap outside after it does', () => {
  swipe(pt, pv.lb, 300, 400);
  ok(pv.lb.open, 'the click after a swipe closed the viewer');
  eq(seen(pv).n, 'PHOTO 2 / 3');
  deq(hist(pt).backs, []);
  tapOutside(pt, pv);
  eq(pv.lb.open, false);
  settle(pt);
  deq(hist(pt), { stack: ['', ''], at: 0, backs: ['back'], left: false });
});

// ---------------------------------------------------------------- srcset

const files = (ss) => (ss || '').split(',').map((c) => c.trim().split(/\s+/)[0]);
check('srcset: a capped set (.th and .sm) gets the file appended at the thumbnail\'s width', () => {
  const t = open(PLAIN), p = parts(t);
  const a = p.J[0], th = thumb(a), own = th.getAttribute('srcset'), href = a.getAttribute('href');
  ok(/\.th\.webp \d+w, .*\.sm\.webp \d+w$/.test(own), 'not a capped set: ' + own);
  eq(own.indexOf(href + ' '), -1);
  pressPhoto(t, a);
  const s = seen(p);
  eq(s.srcset, own + ', ' + href + ' ' + th.getAttribute('width') + 'w');
  ok(/ 1600w$/.test(s.srcset), s.srcset);
  eq(s.sizes, '100vw');
  eq(s.src, href);
  eq(th.getAttribute('srcset'), own, 'the thumbnail\'s own set changed');
});
check('srcset: a portrait of the capped set gets its own width', () => {
  const t = open(PLAIN), p = parts(t);
  const a = p.J[1], th = thumb(a), href = a.getAttribute('href');
  pressPhoto(t, p.J[0]);
  press(t, p.next);
  eq(seen(p).srcset, th.getAttribute('srcset') + ', ' + href + ' 1200w');
  eq(th.getAttribute('width'), '1200');
});
check('srcset: back on a capped photo, the file is in the set once', () => {
  const t = open(PLAIN), p = parts(t);
  const a = p.J[0], own = thumb(a).getAttribute('srcset'), href = a.getAttribute('href');
  for (let i = 0; i < 3; i++) {
    pressPhoto(t, a);
    press(t, p.next);
    press(t, p.prev);
    eq(files(seen(p).srcset).filter((f) => f === href).length, 1, seen(p).srcset);
    eq(seen(p).srcset, own + ', ' + href + ' 1600w');
    eq(thumb(a).getAttribute('srcset'), own);
    press(t, p.close);
    settle(t);
  }
});
check('srcset: a full set, which holds the file already, is passed as it is', () => {
  const t = open(PLAIN), p = parts(t);
  for (const a of p.R) {
    const own = thumb(a).getAttribute('srcset');
    ok(own.indexOf(a.getAttribute('href') + ' ') !== -1, 'not a full set: ' + own);
    pressPhoto(t, a);
    eq(seen(p).srcset, own);
    eq(seen(p).sizes, '100vw');
    eq(seen(p).src, a.getAttribute('href'));
    press(t, p.close);
    settle(t);
  }
});
check('srcset: a thumbnail without a width-described set opens the file alone', () => {
  const t = open(PLAIN), p = parts(t);
  pressPhoto(t, p.J[0]);
  press(t, p.close);
  settle(t);
  const a = p.S[0];
  eq(thumb(a).hasAttribute('srcset'), false);
  pressPhoto(t, a);
  eq(seen(p).srcset, null);
  eq(seen(p).sizes, null);
  eq(seen(p).src, a.getAttribute('href'));
});

// ---------------------------------------------------------------- share

check('share: under (hover: none) with navigator.share every control reads its data-share', () => {
  const t = open(PHONE), p = parts(t);
  eq(label(p.page), 'Share this page');                     // the report's share row: core.copy_link(url, 'Copy link to this page')
  eq(p.page.getAttribute('data-share'), 'Share this page');
  for (const b of [p.title, p.entry, p.page]) {
    eq(label(b), b.getAttribute('data-share'));
    ok(b.classList.contains('is-share'), 'no is-share on ' + b.getAttribute('data-share'));
  }
  eq(p.entry.textContent, p.entry.getAttribute('data-share') + ', Day 3');   // what the entry is still says who it is
});
check('share: a press calls navigator.share inside the click, with the page\'s title and the control\'s URL', () => {
  const t = open(PHONE), p = parts(t), d = docOf(t);
  press(t, p.page);
  deq(d.shares, [{ keys: 'title url', title: MODEL.title, url: p.page.getAttribute('data-copy'), inClick: true }]);
  deq(d.clips, []);
  settle(t);
  t.visitor.pause();
  deq(d.clips, [], 'a shared page was copied as well');
  eq(msg(p.page), '');
  eq(field(p.page), null);
  press(t, p.entry);
  eq(d.shares.length, 2);
  deq(d.shares[1], { keys: 'title url', title: MODEL.title, url: p.entry.getAttribute('data-copy'), inClick: true });
});
check('share: navigator.canShare is asked first when the browser has it', () => {
  const t = open(Object.assign({}, PHONE, { canShare: true })), p = parts(t), d = docOf(t);
  const url = p.page.getAttribute('data-copy');
  press(t, p.page);
  deq(d.canShares, [{ keys: 'title url', url: url }]);
  eq(d.shares.length, 1);
  settle(t);
  deq(d.clips, []);
  d.cfg.canShare = false;                                  // a sheet that would refuse this data: the clipboard instead
  press(t, p.page);
  eq(d.shares.length, 1, 'shared what canShare refused');
  deq(d.clips, [{ text: url, inClick: true }]);
  settle(t);
  eq(msg(p.page), 'Link copied');
  t.visitor.pause(4000);
  d.cfg.canShare = 'throw';
  press(t, p.page);
  eq(d.shares.length, 1);
  eq(d.clips.length, 2);
  settle(t);
  eq(msg(p.page), 'Link copied');
});
check('share: a dismissed sheet (AbortError) does nothing more', () => {
  const t = open(Object.assign({}, PHONE, { shareAnswer: 'abort' })), p = parts(t), d = docOf(t);
  press(t, p.page);
  settle(t);
  t.visitor.pause();
  eq(d.shares.length, 1);
  deq(d.clips, [], 'a dismissed sheet was followed by the clipboard');
  eq(msg(p.page), '');
  eq(field(p.page), null);
});
check('share: a refused sheet falls back to the clipboard', () => {
  for (const how of ['refused', 'type', 'nothing']) {
    const t = open(Object.assign({}, PHONE, { shareAnswer: how })), p = parts(t), d = docOf(t);
    const url = p.page.getAttribute('data-copy');
    press(t, p.page);
    eq(d.shares.length, 1, how);
    deq(d.clips, [], how + ': the clipboard before the sheet answered');
    settle(t);
    deq(d.clips, [{ text: url, inClick: false }], how);
    eq(msg(p.page), 'Link copied', how);
    t.visitor.pause(4000);
    eq(msg(p.page), '', how);
  }
});
check('share: a sheet that throws at once falls back to the clipboard inside the press', () => {
  const t = open(Object.assign({}, PHONE, { shareAnswer: 'throw' })), p = parts(t), d = docOf(t);
  press(t, p.page);
  eq(d.shares.length, 1);
  deq(d.clips, [{ text: p.page.getAttribute('data-copy'), inClick: true }]);
  settle(t);
  eq(msg(p.page), 'Link copied');
});
check('share: the fallback without a clipboard is the field to copy by hand', () => {
  const t = open(Object.assign({}, PHONE, { shareAnswer: 'refused', clipboard: 'none' })), p = parts(t), d = docOf(t);
  press(t, p.page);
  eq(field(p.page), null);
  settle(t);
  const f = field(p.page);
  ok(f, 'no field to copy by hand');
  const inp = f.querySelector('input.copy-url');
  eq(inp.value, p.page.getAttribute('data-copy'));
  eq(inp.getAttribute('aria-label'), 'Link to copy');
  eq(active(t), inp);
  eq(msg(p.page), '');
  deq(d.clips, []);
});

// ---------------------------------------------------------------- desktop copy

const LABELS = (p) => [label(p.title), label(p.entry), label(p.page)];
function copiesAsBefore(cfg, what) {
  const t = open(cfg), p = parts(t), d = docOf(t);
  deq(LABELS(p), ['Copy link', 'Copy link to this entry', 'Copy link to this page'], what + ': relabelled');
  for (const b of [p.title, p.entry, p.page]) eq(b.classList.contains('is-share'), false, what);
  const url = p.title.getAttribute('data-copy');
  press(t, p.title);
  deq(d.shares, [], what + ': asked for the share sheet');
  deq(d.clips, [{ text: url, inClick: true }], what);
  eq(msg(p.title), '', what);
  settle(t);
  eq(msg(p.title), 'Link copied', what);
  eq(msg(p.page), '', what);
  t.visitor.pause(3999);
  eq(msg(p.title), 'Link copied', what + ': gone before 4 s');
  t.visitor.pause(1);
  eq(msg(p.title), '', what + ': still there after 4 s');
  eq(field(p.title), null, what);
  return t;
}
check('desktop copy: (hover: hover) relabels nothing, even with navigator.share, and copies as before', () => {
  copiesAsBefore(DESKTOP, '(hover: hover)');
});
check('desktop copy: a touch screen without navigator.share keeps Copy link and copies as before', () => {
  copiesAsBefore(Object.assign({}, PHONE, { share: false }), 'no navigator.share');
});
check('desktop copy: a browser without matchMedia keeps Copy link and copies as before', () => {
  copiesAsBefore(Object.assign({}, PHONE, { media: false }), 'no matchMedia');
});
check('desktop copy: a clipboard that refuses gives the field to copy by hand; a second press closes it', () => {
  const t = open(Object.assign({}, DESKTOP, { clipboard: 'refused' })), p = parts(t), d = docOf(t);
  press(t, p.entry);
  settle(t);
  deq(d.shares, []);
  const f = field(p.entry);
  ok(f, 'no field to copy by hand');
  const inp = f.querySelector('input.copy-url');
  eq(inp.value, p.entry.getAttribute('data-copy'));
  eq(inp.readOnly, true);
  eq(inp.getAttribute('aria-label'), 'Link to copy');
  eq(active(t), inp);
  eq(msg(p.entry), '');
  press(t, p.entry);
  eq(field(p.entry), null, 'a second press left the field');
  eq(d.clips.length, 1, 'a second press copied again');
});
check('desktop copy: without a clipboard the field comes inside the press; Escape closes it', () => {
  const t = open(Object.assign({}, DESKTOP, { clipboard: 'none' })), p = parts(t);
  press(t, p.page);
  const f = field(p.page);
  ok(f, 'no field to copy by hand');
  eq(active(t), f.querySelector('input.copy-url'));
  key(t, 'Escape');
  eq(field(p.page), null);
  eq(active(t), p.page, 'the focus did not go back to the control');
});

console.log(checks + ' checks passed');
