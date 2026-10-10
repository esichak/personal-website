#!/usr/bin/env node
'use strict';
/* Phase 3: unit tests for the pure helpers of assets/js/pages/series.js (hashTarget, startFiltered, revealId,
   landAfterLoad): which entry a URL hash names, whether the journal's "write-ups only" reader mode may start on without
   hiding that entry, which hidden entry a followed link must reveal, and whether the page scrolls to the hash again once
   the filter has shortened it (only on a fresh visit, never on a reload or Back / Forward). Given a page model, also
   checks of the script's listeners (the "dom:" checks at the end of this file).

   Run by tests/test_series_js.py (skipped when node is missing); by hand:
   `node tests/series_js_harness.js [series.js [page-model.json [fault]]]`.
   - series.js: another module with the same exports (used to prove the harness fails a wrong one).
   - page-model.json: a journal page as tests/test_series_js.py describes it (page_model); with it the whole script is
     run against a stand-in for the browser and the "dom:" checks are added.
   - fault: one thing that stand-in then fails to do (deliver an event, keep the session store, report the navigation
     type), to prove the "dom:" checks notice.
   Every failed assertion throws, so the process exits non-zero. The ids are shaped like the page's own: a day article is
   day-<label> with a decimal label's dot as a dash (day-5-2), a month section is month-YYYY-MM, and the hidden list is what
   the filter hides (track-only days and months without a write-up). */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const MODULE = path.resolve(process.argv[2] || path.join(__dirname, '..', 'assets', 'js', 'pages', 'series.js'));

assert.strictEqual(typeof document, 'undefined', 'the harness runs without a DOM');
assert.strictEqual(typeof window, 'undefined', 'the harness runs without a window');
assert.ok(fs.existsSync(MODULE), 'missing ' + MODULE);
const SER = require(MODULE);   // must export before touching the DOM (there is none here)

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
  eq(typeof SER, 'object');
  for (const name of ['hashTarget', 'startFiltered', 'revealId', 'landAfterLoad']) {
    eq(typeof SER[name], 'function', 'series.js does not export ' + name);
  }
});

// ---------------------------------------------------------------- hashTarget(hash) -> {kind, id}

const target = (hash) => {
  const t = SER.hashTarget(hash);
  assert.ok(t && typeof t === 'object', 'hashTarget(' + JSON.stringify(hash) + ') is not an object');
  return t;
};

check('hashTarget #day-5-2 (a decimal day label)', () => {
  eq(target('#day-5-2').kind, 'day');
  eq(target('#day-5-2').id, 'day-5-2');
});
check('hashTarget #day-12', () => {
  eq(target('#day-12').kind, 'day');
  eq(target('#day-12').id, 'day-12');
});
check('hashTarget #month-2024-06', () => {
  eq(target('#month-2024-06').kind, 'month');
  eq(target('#month-2024-06').id, 'month-2024-06');
});
check('hashTarget #days is the day log, not a day', () => {
  eq(target('#days').kind, 'other');
  eq(target('#days').id, 'days');
});
check('hashTarget #title', () => {
  eq(target('#title').kind, 'other');
  eq(target('#title').id, 'title');
});
check('hashTarget of no hash', () => {
  eq(target('').kind, null);
  assert.ok(!target('').id, 'no hash names no element');
});
check('hashTarget decodes a percent-encoded hash', () => {
  eq(target('#day%2D5%2D2').kind, 'day');
  eq(target('#day%2D5%2D2').id, 'day-5-2');
  eq(target('#month%2D2024%2D06').kind, 'month');
  eq(target('#month%2D2024%2D06').id, 'month-2024-06');
});
check('hashTarget survives a malformed escape', () => {
  // the page calls this on load and on every hashchange: a hand-typed '%' must not throw there
  assert.doesNotThrow(() => SER.hashTarget('#day-%'));
  assert.doesNotThrow(() => SER.hashTarget('#%E0%A4%A'));
});
check('hashTarget returns kind and id', () => {
  for (const hash of ['#day-5-2', '#month-2024-06', '#days', '']) {
    deq(Object.keys(target(hash)).sort(), ['id', 'kind'], 'hashTarget(' + JSON.stringify(hash) + ')');
  }
});

// ---------------------------------------------------------------- startFiltered(defaultOn, hash, hiddenIds)

// track-only days and a month without a write-up; day-2, day-5-2 and month-2024-04 stay visible under the filter
const HIDDEN = ['day-1', 'day-3', 'day-6', 'month-2024-06'];
const on = (hash, hidden) => SER.startFiltered(true, hash, hidden || HIDDEN);

check('startFiltered default on, no hash', () => {
  eq(on(''), true);
});
check('startFiltered default on, a hash naming a hidden day', () => {
  eq(on('#day-1'), false);
  eq(on('#day-6'), false);
});
check('startFiltered default on, a hash naming a hidden month', () => {
  eq(on('#month-2024-06'), false);
});
check('startFiltered default on, a hash naming a visible entry', () => {
  eq(on('#day-2'), true);
  eq(on('#day-5-2'), true);
  eq(on('#month-2024-04'), true);
});
check('startFiltered default on, a hash naming another part of the page', () => {
  eq(on('#days'), true);
  eq(on('#title'), true);
  eq(on('#highlights'), true);
});
check('startFiltered matches whole ids only', () => {
  eq(on('#day-12', ['day-1']), true);     // day-12 is not day-1
  eq(on('#day-5', ['day-5-2']), true);    // nor is day-5 the hidden day-5-2
  eq(on('#day-5-2', ['day-5']), true);
  eq(on('#day-5-2', ['day-5-2']), false);
});
check('startFiltered decodes a percent-encoded hash', () => {
  eq(on('#day%2D1'), false);
  eq(on('#day%2D2'), true);
});
check('startFiltered with nothing hidden', () => {
  eq(on('#day-1', []), true);
  eq(on('', []), true);
});
check('startFiltered default off, whatever the hash', () => {
  for (const hash of ['', '#day-1', '#day-2', '#day-5-2', '#month-2024-06', '#days']) {
    eq(SER.startFiltered(false, hash, HIDDEN), false, 'default off with ' + JSON.stringify(hash));
  }
  eq(SER.startFiltered(false, '', []), false);
});
check('startFiltered leaves the hidden list alone', () => {
  const hidden = HIDDEN.slice();
  on('#day-1', hidden);
  on('#day-2', hidden);
  deq(hidden, HIDDEN);
});

// ---------------------------------------------------------------- revealId(filtered, hash, hiddenIds) -> id | ''

// what a followed link must reveal: the hidden day or month the hash names while the filter is on, else nothing
const reveal = (hash, hidden) => SER.revealId(true, hash, hidden || HIDDEN);

check('revealId filtered, a hash naming a hidden day', () => {
  eq(reveal('#day-1'), 'day-1');
  eq(reveal('#day-3'), 'day-3');
  eq(reveal('#day-6'), 'day-6');
});
check('revealId filtered, a hash naming a hidden month', () => {
  eq(reveal('#month-2024-06'), 'month-2024-06');
});
check('revealId filtered, a hash naming a visible entry', () => {
  eq(reveal('#day-2'), '');
  eq(reveal('#day-5-2'), '');
  eq(reveal('#month-2024-04'), '');
});
check('revealId filtered, a hash naming another part of the page', () => {
  eq(reveal('#days'), '');
  eq(reveal('#title'), '');
  eq(reveal('#highlights'), '');
});
check('revealId filtered, no hash', () => {
  eq(reveal(''), '');
  eq(reveal('#'), '');
});
check('revealId not filtered, whatever the hash', () => {
  // nothing is hidden while the filter is off, so there is nothing to reveal (and nothing to announce)
  for (const hash of ['', '#day-1', '#day-6', '#month-2024-06', '#day-2', '#day-5-2', '#days']) {
    eq(SER.revealId(false, hash, HIDDEN), '', 'not filtered with ' + JSON.stringify(hash));
  }
});
check('revealId matches whole ids only', () => {
  eq(reveal('#day-12', ['day-1']), '');       // day-12 is not the hidden day-1
  eq(reveal('#day-5', ['day-5-2']), '');      // nor is day-5 the hidden day-5-2
  eq(reveal('#day-5-2', ['day-5']), '');
  eq(reveal('#day-5-2', ['day-5-2']), 'day-5-2');
});
check('revealId decodes a percent-encoded hash', () => {
  eq(reveal('#day%2D1'), 'day-1');
  eq(reveal('#month%2D2024%2D06'), 'month-2024-06');
  eq(reveal('#day%2D2'), '');
});
check('revealId with nothing hidden', () => {
  eq(reveal('#day-1', []), '');
  eq(reveal('', []), '');
});
check('revealId returns the id as a string, or the empty string', () => {
  for (const filtered of [true, false]) {
    for (const hash of ['', '#day-1', '#day-2', '#month-2024-06', '#days']) {
      eq(typeof SER.revealId(filtered, hash, HIDDEN), 'string', JSON.stringify([filtered, hash]));
    }
  }
});
check('revealId survives a malformed escape', () => {
  // the page calls this on every hashchange and on clicks: a hand-typed '%' must not throw there
  assert.doesNotThrow(() => reveal('#day-%'));
  assert.doesNotThrow(() => reveal('#%E0%A4%A'));
});
check('revealId leaves the hidden list alone', () => {
  const hidden = HIDDEN.slice();
  reveal('#day-1', hidden);
  reveal('#day-2', hidden);
  SER.revealId(false, '#day-1', hidden);
  deq(hidden, HIDDEN);
});
check('revealId agrees with startFiltered about what is hidden', () => {
  // a hash that keeps the filter from starting on is exactly a hash that a later link must reveal
  for (const hash of ['', '#day-1', '#day-2', '#day-3', '#day-5-2', '#day-6', '#day-12', '#month-2024-04', '#month-2024-06', '#days']) {
    eq(reveal(hash) !== '', on(hash) === false, 'hash ' + JSON.stringify(hash));
  }
});

// ---------------------------------------------------------------- landAfterLoad(filtered, hash, navType) -> boolean

// navType is PerformanceNavigationTiming.type: 'navigate' for a link or a typed address; '' or undefined when the
// browser does not say. On 'reload', 'back_forward' and 'prerender' the browser restores the reader's own position.
const FRESH = ['navigate', '', undefined];
const RESTORED = ['reload', 'back_forward', 'prerender'];
const ENTRIES = ['#day-1', '#day-2', '#day-5-2', '#day-12', '#month-2024-04', '#month-2024-06'];
const ELSEWHERE = ['', '#', '#days', '#title', '#highlights', '#map', '#stats'];

check('landAfterLoad filtered, a day or month hash, a fresh visit', () => {
  for (const hash of ENTRIES) {
    for (const nav of FRESH) {
      eq(SER.landAfterLoad(true, hash, nav), true, JSON.stringify([hash, nav]));
    }
  }
});
check('landAfterLoad filtered, a day or month hash, navType left out', () => {
  eq(SER.landAfterLoad(true, '#day-5-2'), true);
  eq(SER.landAfterLoad(true, '#month-2024-06'), true);
});
check('landAfterLoad never on reload', () => {
  for (const hash of ENTRIES) {
    eq(SER.landAfterLoad(true, hash, 'reload'), false, hash);
  }
});
check('landAfterLoad never on back_forward', () => {
  for (const hash of ENTRIES) {
    eq(SER.landAfterLoad(true, hash, 'back_forward'), false, hash);
  }
});
check('landAfterLoad never on prerender', () => {
  for (const hash of ENTRIES) {
    eq(SER.landAfterLoad(true, hash, 'prerender'), false, hash);
  }
});
check('landAfterLoad filtered, a hash naming something other than a day or month', () => {
  for (const hash of ELSEWHERE) {
    for (const nav of FRESH.concat(RESTORED)) {
      eq(SER.landAfterLoad(true, hash, nav), false, JSON.stringify([hash, nav]));
    }
  }
});
check('landAfterLoad not filtered, whatever the hash and the navigation', () => {
  // the list was not shortened, so the browser's own jump to the hash already landed
  for (const hash of ENTRIES.concat(ELSEWHERE)) {
    for (const nav of FRESH.concat(RESTORED)) {
      eq(SER.landAfterLoad(false, hash, nav), false, JSON.stringify([hash, nav]));
    }
  }
  eq(SER.landAfterLoad(false, '#day-5-2'), false);
});
check('landAfterLoad decodes a percent-encoded hash', () => {
  eq(SER.landAfterLoad(true, '#day%2D5%2D2', 'navigate'), true);
  eq(SER.landAfterLoad(true, '#month%2D2024%2D06', 'navigate'), true);
  eq(SER.landAfterLoad(true, '#day%2D5%2D2', 'reload'), false);
});
check('landAfterLoad returns a boolean', () => {
  for (const filtered of [true, false]) {
    for (const hash of ['', '#day-1', '#month-2024-06', '#days']) {
      for (const nav of FRESH.concat(RESTORED)) {
        eq(typeof SER.landAfterLoad(filtered, hash, nav), 'boolean', JSON.stringify([filtered, hash, nav]));
      }
    }
  }
});
check('landAfterLoad survives a malformed escape', () => {
  assert.doesNotThrow(() => SER.landAfterLoad(true, '#day-%', 'navigate'));
  assert.doesNotThrow(() => SER.landAfterLoad(true, '#%E0%A4%A', 'reload'));
});

// ---------------------------------------------------------------- the listeners, on a stand-in for the browser

/* What the pure helpers cannot show: that the page code calls them at the right moments (contract sections 5 and 9, and
   the "Behaviour" line of 10.6). tests/test_series_js.py passes a JSON model of a journal page that
   sitegen.pages.series generated: its elements (tag, id, classes, attributes, parent), the elements matched by each
   selector the script uses, the elements series.css takes out of the page while the filter is on, and the few elements
   pressed or read below. load() runs the whole script against just enough of window, document and Element for what
   series.js calls, with a session store and a navigation type, and returns the reader's actions: a press on an element,
   a change of the toggle, a new hash. A call the stand-in lacks throws and fails the run: add it to load(). Selectors
   are answered from the model, so the script may spell them as it likes. Without the model these checks are skipped.

   FAULT breaks the stand-in on purpose, as a script with that part gutted would behave: 'hashchange', 'click' or
   'change' (the event reaches no listener), 'store' (the session store keeps nothing), 'navigation' (every load is
   reported as a fresh visit). Each must make a check below fail; tests/test_series_js.py runs them all. */
const MODEL = process.argv[3] ? JSON.parse(fs.readFileSync(path.resolve(process.argv[3]), 'utf8')) : null;
const SOURCE = MODEL ? fs.readFileSync(MODULE, 'utf8') : '';
const FAULT = process.argv[4] || '';
assert.ok(['', 'hashchange', 'click', 'change', 'store', 'navigation'].indexOf(FAULT) !== -1, 'unknown fault: ' + FAULT);

function load(opts) {
  opts = opts || {};
  const store = opts.store || {};
  const frames = [];
  const scrolled = [];
  const heard = { window: {}, document: {} };
  const listen = (bag) => (type, fn) => { (bag[type] = bag[type] || []).push(fn); };
  const emit = (bag, type, ev) => (type === FAULT ? [] : bag[type] || []).slice().forEach((fn) => fn(ev));
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const els = [];
  const matching = (sel) => {
    if (!own(MODEL.selectors, sel)) throw new Error('the page model has no answer for the selector ' + sel);
    return MODEL.selectors[sel].map((i) => els[i]);
  };
  // rendered: not under [hidden], and not one of the entries the stylesheet drops while the day log has the filter class
  const shown = (el) => {
    const filtering = els[MODEL.handles.log].classList.contains(MODEL.filterClass);
    for (let e = el; e; e = e.parentElement) {
      if (e.hidden || (filtering && MODEL.filteredOut.indexOf(e.index) !== -1)) return false;
    }
    return true;
  };
  MODEL.elements.forEach((spec, index) => {
    const classes = new Set(spec.classes);
    const attrs = Object.assign({}, spec.attrs);
    const dataset = {};
    Object.keys(attrs).filter((k) => k.indexOf('data-') === 0).forEach((k) => {
      dataset[k.slice(5).replace(/-([a-z])/g, (m, c) => c.toUpperCase())] = attrs[k];
    });
    const bag = {};
    const el = {
      index: index, tagName: spec.tag.toUpperCase(), id: spec.id, dataset: dataset, textContent: '',
      hidden: own(attrs, 'hidden'), checked: own(attrs, 'checked'), heard: bag,
      classList: {
        contains: (c) => classes.has(c),
        add: (c) => { classes.add(c); },
        remove: (c) => { classes.delete(c); },
        toggle: (c, force) => {
          const want = force === undefined ? !classes.has(c) : !!force;
          if (want) classes.add(c); else classes.delete(c);
          return want;
        },
      },
      getAttribute: (n) => (own(attrs, n) ? attrs[n] : null),
      hasAttribute: (n) => own(attrs, n),
      setAttribute: (n, v) => { attrs[n] = String(v); },
      removeAttribute: (n) => { delete attrs[n]; },
      contains: (other) => {
        for (let e = other; e; e = e.parentElement) if (e === el) return true;
        return false;
      },
      querySelectorAll: (sel) => matching(sel).filter((e) => e !== el && el.contains(e)),
      querySelector: (sel) => el.querySelectorAll(sel)[0] || null,
      matches: (sel) => matching(sel).indexOf(el) !== -1,
      closest: (sel) => {
        const hits = matching(sel);
        for (let e = el; e; e = e.parentElement) if (hits.indexOf(e) !== -1) return e;
        return null;
      },
      addEventListener: listen(bag),
      getBoundingClientRect: () => ({ top: 0, right: 0, bottom: 0, left: 0, width: 0, height: 0 }),
      scrollIntoView: () => { scrolled.push(el.id); win.scrollY = 1000 + 10 * index; },   // each element at its own height
    };
    Object.defineProperty(el, 'parentElement', { get: () => (spec.parent < 0 ? null : els[spec.parent]) });
    Object.defineProperty(el, 'offsetParent', { get: () => (shown(el) ? el.parentElement || el : null) });
    els.push(el);
  });
  const win = {
    scrollY: 0,
    location: { hash: opts.hash || '', pathname: opts.pathname || MODEL.pathname },
    sessionStorage: {
      getItem: (k) => (own(store, k) ? store[k] : null),
      setItem: (k, v) => { if (FAULT !== 'store') store[k] = String(v); },
    },
    // PerformanceNavigationTiming.type; an older browser has no entry at all
    performance: {
      getEntriesByType: (t) => {
        if (t !== 'navigation' || (opts.navType === undefined && FAULT !== 'navigation')) return [];
        return [{ type: FAULT === 'navigation' ? 'navigate' : opts.navType }];
      },
    },
    addEventListener: listen(heard.window),
    requestAnimationFrame: (fn) => frames.push(fn),
  };
  const doc = {
    readyState: opts.loading ? 'loading' : 'complete',     // loading: the script runs before the window's load event
    getElementById: (id) => els.find((e) => e.id === id) || null,
    querySelectorAll: (sel) => matching(sel),
    querySelector: (sel) => matching(sel)[0] || null,
    addEventListener: listen(heard.document),
  };
  const flush = () => { while (frames.length) frames.shift()(); };
  const h = {};
  Object.keys(MODEL.handles).forEach((k) => { h[k] = els[MODEL.handles[k]]; });

  vm.runInNewContext(SOURCE, { window: win, document: doc }, { filename: MODULE });
  flush();

  return {
    h: h,
    scrolled: scrolled,
    stored: () => Object.keys(store),
    hash: () => win.location.hash,
    scrollY: () => win.scrollY,
    said: () => h.live.textContent,
    // true while only the written entries show; the checkbox and the class the stylesheet keys on must agree
    filtered: () => {
      eq(h.log.classList.contains(MODEL.filterClass), h.box.checked, 'the toggle and .' + MODEL.filterClass + ' disagree');
      return h.box.checked;
    },
    // a press on an element: the click listeners up the tree, then what a browser does with an in-page link. A link to
    // the fragment the address already ends with changes nothing, so no hashchange follows
    press: (el) => {
      const ev = { type: 'click', target: el, defaultPrevented: false, preventDefault: () => { ev.defaultPrevented = true; } };
      for (let e = el; e; e = e.parentElement) emit(e.heard, 'click', ev);
      emit(heard.document, 'click', ev);
      emit(heard.window, 'click', ev);
      let a = el;
      while (a && !(a.tagName === 'A' && (a.getAttribute('href') || '').charAt(0) === '#')) a = a.parentElement;
      if (a && !ev.defaultPrevented && a.getAttribute('href') !== win.location.hash) {
        win.location.hash = a.getAttribute('href');
        emit(heard.window, 'hashchange', { type: 'hashchange' });
      }
      flush();
    },
    // the reader ticks or clears 'Show days with write-ups only'
    toggle: (on) => {
      h.box.checked = on;
      const ev = { type: 'change', target: h.box };
      for (let e = h.box; e; e = e.parentElement) emit(e.heard, 'change', ev);
      emit(heard.document, 'change', ev);
      flush();
    },
    // the fragment changes without a press: an edited address, Back or Forward within the page
    go: (hash) => {
      win.location.hash = hash;
      emit(heard.window, 'hashchange', { type: 'hashchange' });
      flush();
    },
    // the reader scrolls on by so many pixels
    scroll: (by) => {
      win.scrollY += by;
      emit(heard.window, 'scroll', { type: 'scroll' });
      flush();
    },
    // the photos and fonts are in: the window's load event, for a page opened with { loading: true }
    loaded: () => {
      doc.readyState = 'complete';
      emit(heard.window, 'load', { type: 'load' });
      flush();
    },
    // a page loaded later in the same browser session (a reload, another visit, another journal): the store is kept
    again: (next) => load(Object.assign({ store: store }, next)),
  };
}

if (MODEL) {
  const ID = MODEL.ids;            // hiddenDay, hiddenMonth: what the filter hides; shownDay: a written entry
  const ALL = 'Showing all ' + MODEL.total + ' days';

  check('dom: the model is the page the script expects', () => {
    for (const k of ['log', 'box', 'live', 'wrapper', 'browse', 'dayLink', 'monthLink', 'shownLink']) {
      assert.ok(MODEL.handles[k] >= 0, 'the page model has no ' + k);
    }
    const page = load();
    eq(page.h.dayLink.getAttribute('href'), '#' + ID.hiddenDay);
    eq(page.h.monthLink.getAttribute('href'), '#' + ID.hiddenMonth);
    eq(page.h.shownLink.getAttribute('href'), '#' + ID.shownDay);
    eq(page.h.browse.getAttribute('href'), '#days');
  });

  // ---- on load (contract 5, Reader mode)

  check('dom: a first visit shows the written entries only', () => {
    const page = load();
    eq(page.filtered(), true);
    eq(page.h.wrapper.hidden, false, 'the toggle stays hidden');
    eq(page.said(), '', 'nothing changed for the reader, so nothing is announced');
    deq(page.scrolled, []);
    eq(page.again().filtered(), true, 'the default is not a remembered choice');
  });
  check('dom: a visit to a hidden day starts with every day, and says nothing', () => {
    // contract 11.2: nothing is announced on load (a live region filled while the page loads is not reliably spoken;
    // the unchecked toggle states the mode)
    const page = load({ hash: '#' + ID.hiddenDay, navType: 'navigate' });
    eq(page.filtered(), false);
    eq(page.said(), '', 'a load that starts on every day announces nothing');
    eq(page.again().filtered(), true, 'a link that showed a hidden day is not a choice');
  });
  check('dom: a visit to a hidden month starts with every day, and says nothing', () => {
    const page = load({ hash: '#' + ID.hiddenMonth, navType: 'navigate' });
    eq(page.filtered(), false);
    eq(page.said(), '', 'a load that starts on every day announces nothing');
  });
  check('dom: a visit to a written entry keeps the filter and lands on the entry', () => {
    for (const navType of ['navigate', '', undefined]) {
      const page = load({ hash: '#' + ID.shownDay, navType: navType });
      eq(page.filtered(), true, JSON.stringify(navType));
      assert.ok(page.scrolled.length >= 1, 'no scroll to the entry with navType ' + JSON.stringify(navType));
      deq(Array.from(new Set(page.scrolled)), [ID.shownDay]);
    }
  });
  check('dom: a visit to a month with write-ups keeps the filter and lands on the month', () => {
    const page = load({ hash: '#' + ID.shownMonth, navType: 'navigate' });
    eq(page.filtered(), true);
    deq(Array.from(new Set(page.scrolled)), [ID.shownMonth]);
  });
  check('dom: a visit to another part of the page does not scroll', () => {
    for (const hash of ['#days', '#title', '']) {
      const page = load({ hash: hash, navType: 'navigate' });
      eq(page.filtered(), true, hash);
      deq(page.scrolled, [], hash);
    }
  });

  // ---- contract 10.6: no re-scroll to the hash on reload or Back / Forward

  check('dom: a reload does not scroll back to the hash', () => {
    const page = load({ hash: '#' + ID.shownDay, navType: 'reload' });
    eq(page.filtered(), true);
    deq(page.scrolled, [], 'the browser restores the reader\'s place; the script must not move it');
  });
  check('dom: Back or Forward does not scroll back to the hash', () => {
    deq(load({ hash: '#' + ID.shownDay, navType: 'back_forward' }).scrolled, []);
    deq(load({ hash: '#' + ID.shownMonth, navType: 'back_forward' }).scrolled, []);
  });
  check('dom: a prerendered page does not scroll to the hash', () => {
    deq(load({ hash: '#' + ID.shownDay, navType: 'prerender' }).scrolled, []);
  });

  check('dom: a reload of a page that is still loading never scrolls to the hash', () => {
    for (const navType of ['reload', 'back_forward', 'prerender']) {
      const page = load({ hash: '#' + ID.shownDay, navType: navType, loading: true });
      deq(page.scrolled, [], navType);
      page.loaded();
      deq(page.scrolled, [], navType + ', after the load event');
    }
  });

  // ---- a fresh visit while the page is still loading (contract 9: the entry named in the hash is in view again)

  check('dom: a visit that is still loading lands on the entry, and again once loaded', () => {
    // the photos and fonts that arrive before the load event move the entry: the second landing puts it back in view
    const page = load({ hash: '#' + ID.shownDay, navType: 'navigate', loading: true });
    deq(page.scrolled, [ID.shownDay]);
    page.loaded();
    deq(page.scrolled, [ID.shownDay, ID.shownDay]);
  });
  check('dom: the load event does not pull back a reader who has scrolled on', () => {
    // series.js lands a second time on load only while the reader is still where the first landing left them
    const page = load({ hash: '#' + ID.shownDay, navType: 'navigate', loading: true });
    deq(page.scrolled, [ID.shownDay]);
    page.scroll(800);
    const at = page.scrollY();
    page.loaded();
    deq(page.scrolled, [ID.shownDay], 'the reader was thrown back to the entry');
    eq(page.scrollY(), at);
  });

  // ---- a link followed after the load (contract 5: hashchange; 10.6: the same fragment again)

  check('dom: a hash change to a hidden day turns the filter off, says so and goes there', () => {
    const page = load();
    page.go('#' + ID.hiddenDay);
    eq(page.filtered(), false);
    eq(page.said(), ALL);
    deq(page.scrolled, [ID.hiddenDay]);
    eq(page.again().filtered(), true, 'a link that showed a hidden day is not a choice');
  });
  check('dom: a pressed link to a hidden day or month reveals it', () => {
    let page = load();
    page.press(page.h.dayLink);
    eq(page.hash(), '#' + ID.hiddenDay);
    eq(page.filtered(), false);
    eq(page.said(), ALL);
    deq(page.scrolled, [ID.hiddenDay]);
    page = load();
    page.press(page.h.monthLink);
    eq(page.filtered(), false);
    deq(page.scrolled, [ID.hiddenMonth]);
  });
  check('dom: a link to a written entry leaves the filter on', () => {
    const page = load();
    page.press(page.h.shownLink);
    eq(page.hash(), '#' + ID.shownDay);
    eq(page.filtered(), true);
    eq(page.said(), '', 'nothing was hidden, so nothing is announced');
  });
  check('dom: the same link pressed again reveals a hidden day', () => {
    // the address already ends with the fragment, so no hashchange fires: the click itself must reveal the target
    const page = load({ hash: '#' + ID.hiddenDay, navType: 'navigate' });
    page.toggle(true);
    eq(page.filtered(), true);
    page.press(page.h.dayLink);
    eq(page.hash(), '#' + ID.hiddenDay);
    eq(page.filtered(), false, 'the link did nothing: its target stays hidden');
    eq(page.said(), ALL);
    deq(page.scrolled, [ID.hiddenDay]);
  });
  check('dom: the same link pressed again reveals a hidden month', () => {
    const page = load({ hash: '#' + ID.hiddenMonth, navType: 'navigate' });
    page.toggle(true);
    page.press(page.h.monthLink);
    eq(page.filtered(), false, 'the link did nothing: its target stays hidden');
    eq(page.said(), ALL);
    deq(page.scrolled, [ID.hiddenMonth]);
  });
  check('dom: the same link pressed again changes nothing when its target is showing', () => {
    const page = load({ hash: '#' + ID.shownDay, navType: 'reload' });
    page.press(page.h.shownLink);
    eq(page.filtered(), true);
    eq(page.said(), '');
  });

  // ---- the reader's own choice (contract 9: kept for the session; 10.6: 'Browse all recordings' always is one)

  check('dom: the toggle shows every day, says so, and the choice survives a reload', () => {
    const page = load();
    page.toggle(false);
    eq(page.filtered(), false);
    eq(page.said(), ALL);
    const reloaded = page.again({ navType: 'reload' });
    eq(reloaded.filtered(), false);
    eq(reloaded.said(), '', 'a reload that keeps every day showing announces nothing');
    const back = page.again();
    back.toggle(true);
    eq(back.filtered(), true);
    assert.ok(back.said() && back.said() !== ALL, 'turning the filter on is announced too');
    eq(back.again({ navType: 'reload' }).filtered(), true);
  });
  check('dom: the choice is kept under this journal\'s own address', () => {
    // contract 9: sessionStorage key 'ser-only:' + pathname, so one journal's choice is not another's
    const page = load();
    deq(page.stored(), [], 'a load alone stores nothing');
    page.toggle(false);
    deq(page.stored(), ['ser-only:' + MODEL.pathname]);
    eq(page.again().filtered(), false);
    eq(page.again({ pathname: MODEL.pathname.replace(/[^/]+\/$/, 'another-journal/') }).filtered(), true);
  });
  check('dom: a remembered "write-ups only" still gives way to a link to a hidden entry', () => {
    const page = load({ hash: '#' + ID.hiddenMonth });
    page.toggle(true);
    eq(page.again({ hash: '#' + ID.hiddenDay }).filtered(), false);
    eq(page.again().filtered(), true);
  });
  check('dom: Browse all recordings shows every day, says so, and is remembered', () => {
    const page = load();
    page.press(page.h.browse);
    eq(page.hash(), '#days');
    eq(page.filtered(), false);
    eq(page.said(), ALL);
    eq(page.again({ hash: '#days', navType: 'reload' }).filtered(), false);
    eq(page.again().filtered(), false);
  });
  check('dom: Browse all recordings is remembered when a link had already shown every day', () => {
    // the filter is off because of the link, which is not a choice; the press is one and must hold after a reload
    const page = load({ hash: '#' + ID.hiddenDay, navType: 'navigate' });
    eq(page.filtered(), false);
    page.press(page.h.browse);
    eq(page.filtered(), false);
    eq(page.again({ hash: '#days', navType: 'reload' }).filtered(), false, 'the press was forgotten');
  });
  check('dom: Browse all recordings replaces an earlier "write-ups only"', () => {
    const page = load({ hash: '#' + ID.hiddenMonth });
    page.toggle(true);                       // a choice: write-ups only
    page.go('#' + ID.hiddenDay);             // a link shows every day again, which is not a choice
    eq(page.filtered(), false);
    page.press(page.h.browse);               // the last word: every recording
    eq(page.again({ hash: '#days', navType: 'reload' }).filtered(), false, 'the older choice came back');
  });
}

console.log('series_js_harness: ' + checks + ' checks passed');
