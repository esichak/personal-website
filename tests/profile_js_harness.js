#!/usr/bin/env node
'use strict';
/* maps-04: the readout on the elevation profile of a single-day report, as assets/js/pages/profile.js draws it. The
   script is run as it is against the stand-in for the browser (tests/page_standin.js), on pages written by hand after
   the markup core.chart_block generates (the .chart's data-pf and data-pf-km, each .cv's data-w and data-pad), and a
   reader's pointer, finger and keys are played on it:

     fixture        each .cv of a chart with data-pf gets one crosshair (span.pf-x) and one label (span.pf-l), hidden,
                    aria-hidden="true", never focusable, and a pointermove listener; a chart without data-pf gets none
     labels         '7.2 MI · 11,650 FT', '11.6 KM · 3,551 M' (html.km, read at every move), separators, below zero
     mapping        the pointer to a sample: x = (clientX - left) * w / width, f = (x - pad) / (w - pad), the sample at
                    round(f * N) and the distance f * km, on each rendered width and on a rect scaled from its viewBox;
                    the crosshair under the pointer
     nearest sample round(f * N), not the sample below
     clamped ends   left of the axis (in the padding, or off the chart) the first sample at 0.0, the crosshair on the
                    axis; at or past the right edge the last sample at the whole distance, the crosshair inside the .cv
     label clamp    the label is centred on the crosshair and kept inside the .cv, at both ends and over a sweep
     touch          a finger (pointerType touch) or a pen updates the readout as a mouse does
     hide           pointerleave and pointercancel of the .cv, and Escape anywhere, hide both; other keys do not
     no width       a .cv with no width (not displayed) shows nothing and does not throw
     malformed      data-pf that is not JSON, not an array, empty or not all numbers, a missing or bad data-pf-km, a
                    .cv whose padding is not inside its width: no readout there, nothing thrown, the rest still works
     no data-pf     a page without a .chart[data-pf]: nothing created, nothing listened to

   Run by tests/test_profile_js.py (skipped when node is missing); by hand:
     node tests/profile_js_harness.js [profile.js]
   The optional argument points at another copy of the script (used to prove the harness fails a wrong one). Every
   failed check prints 'FAIL <label>' on stderr and throws, so the process exits non-zero; a run without one ends with
   '<N> checks passed' on stdout.

   page_standin.js is left as it is. What this page needs beyond it is added from here, by a first script run in the
   same window (extras, below): the document element and a node above it that stands for the document (its
   querySelectorAll and its listeners), getBoundingClientRect (the rect a check gives an element with place()), style,
   and offsetWidth for the label: 0 while it or anything around it is hidden, else its characters at 7.44 px (Geist Mono
   12 px, 0.6 em plus 0.02 em of letter spacing) and 4 px of padding each side. Layout is not modelled otherwise. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const standin = require('./page_standin.js');

const PROFILE = path.resolve(process.argv[2] || path.join(__dirname, '..', 'assets', 'js', 'pages', 'profile.js'));
assert.ok(fs.existsSync(PROFILE), 'missing ' + PROFILE);
const SOURCE = fs.readFileSync(PROFILE, 'utf8');

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

// ---------------------------------------------------------------- the stand-in, and what this page adds to it

const CHAR = 7.44, PADX = 8;
const labelWidth = (text) => text.length * CHAR + PADX;

// run inside the window, before profile.js (see the header)
function extras(CHAR, PADX) {
  'use strict';
  var body = document.body;
  var proto = Object.getPrototypeOf(body);
  if (!Object.prototype.hasOwnProperty.call(proto, 'getBoundingClientRect')) {
    proto.getBoundingClientRect = function () {
      var r = this.rect || { left: 0, width: 0 };
      return { left: r.left, right: r.left + r.width, width: r.width, top: 0, bottom: 120, height: 120, x: r.left, y: 0 };
    };
    Object.defineProperty(proto, 'offsetWidth', {
      get: function () {
        for (var p = this; p; p = p.parentNode) if (p.hidden) return 0;
        return this.textContent.length * CHAR + PADX;
      },
    });
    Object.defineProperty(proto, 'style', { get: function () { return this.css || (this.css = {}); } });
  }
  var doc = document.createElement('x-document'), html = document.createElement('html');
  doc.appendChild(html);
  html.appendChild(body);
  document.documentElement = html;
  document.querySelectorAll = function (sel) { return doc.querySelectorAll(sel); };
  document.querySelector = function (sel) { return doc.querySelector(sel); };
  document.addEventListener = function (type, fn) { doc.addEventListener(type, fn); };
}
const EXTRAS = '(' + extras.toString() + ')(' + CHAR + ', ' + PADX + ');\n';

function open(children) {
  const model = { pathname: '/trips/syn-pf/', body: { tag: 'body', attrs: { class: 'p-report' }, children: children }, indexes: {} };
  return standin.open(model, [['standin-extras.js', EXTRAS], [path.basename(PROFILE), SOURCE]]);
}
const docOf = (tab) => tab.body.parentNode.parentNode;
const units = (tab, km) => { tab.body.parentNode.classList.toggle('km', km); };
const place = (el, left, width) => { el.rect = { left: left, width: width }; };

// one event on an element's own listeners, with what a pointer or a key event carries
function send(el, type, props) {
  const e = Object.assign({ type: type, target: el, defaultPrevented: false, preventDefault() { e.defaultPrevented = true; } }, props);
  (el.listeners[type] || []).slice().forEach((fn) => fn.call(el, e));
  return e;
}
const move = (cv, clientX, pointerType) => send(cv, 'pointermove', { clientX: clientX, clientY: 60, pointerType: pointerType || 'mouse',
                                                                     isPrimary: true, target: cv.firstChild });
const leave = (cv) => send(cv, 'pointerleave', { pointerType: 'mouse', target: cv });
const cancel = (cv) => send(cv, 'pointercancel', { pointerType: 'touch', target: cv });
const key = (tab, k) => send(docOf(tab), 'keydown', { key: k, target: tab.body });

function all(scope, sel) { return scope.querySelectorAll(sel); }
function only(scope, sel) {
  const hits = all(scope, sel);
  eq(hits.length, 1, hits.length + ' elements for ' + sel);
  return hits[0];
}
// the readout of a .cv as the reader sees it
function seen(cv) {
  const x = only(cv, '.pf-x'), l = only(cv, '.pf-l');
  return { on: !x.hidden && !l.hidden, off: x.hidden && l.hidden, text: l.textContent, x: x.style.left, l: l.style.left };
}
const listened = (el) => Object.keys(el.listeners).filter((k) => el.listeners[k].length);

// the label the spec asks for, written here without the script's own helpers
const sep = (n) => Math.round(n).toLocaleString('en-US');
function want(m, d, km) {
  return km ? d.toFixed(1) + ' KM · ' + sep(m) + ' M' : (d / 1.609344).toFixed(1) + ' MI · ' + sep(m * 3.28084) + ' FT';
}
const dims = (cv) => ({ w: Number(cv.getAttribute('data-w')), pad: Number(cv.getAttribute('data-pad')) });
// the clientX of the point t samples along the axis (t / N of the track), on the rect the .cv has now
function clientAt(cv, t, n) {
  const d = dims(cv);
  return cv.rect.left + (d.pad + t / n * (d.w - d.pad)) * cv.rect.width / d.w;
}

// ---------------------------------------------------------------- the pages

const N = 150;
const ELE = Array.from({ length: N + 1 }, (_v, i) => 2000 + 10 * i);    // 2,000 m to 3,500 m, every sample its own value
const KM = 20.6;
const svg = (w, h) => ({ tag: 'svg', attrs: { viewBox: '0 0 ' + w + ' ' + h, role: 'img', 'aria-label': 'Elevation profile' }, children: [] });
const cv = (size, w, pad, h) => ({ tag: 'div', attrs: { class: 'cv cv--' + size, 'data-w': String(w), 'data-pad': String(pad),
                                                        style: 'aspect-ratio:' + w + '/' + h }, children: [svg(w, h)] });
function chart(id, pf, km, cvs) {
  const attrs = { class: 'chart', id: id };
  if (pf !== undefined) attrs['data-pf'] = pf;
  if (km !== undefined) attrs['data-pf-km'] = km;
  return { tag: 'div', attrs: attrs, children: cvs };
}
const THREE = () => [cv('wide', 1248, 72, 162), cv('col', 718, 72, 132), cv('phone', 358, 0, 122)];
// a speed chart: no data-pf, and no data-w or data-pad on its .cv
const SPEED = { tag: 'div', attrs: { class: 'chart', id: 'speed' }, children: [
  { tag: 'div', attrs: { class: 'cv cv--col', style: 'aspect-ratio:718/132' }, children: [svg(718, 132)] }] };

const MAIN = [
  { tag: 'section', attrs: { class: 'rep-prof', id: 'profile' }, children: [
    { tag: 'h2', attrs: { class: 'rep-h' }, children: ['Elevation'] },
    { tag: 'p', attrs: { class: 't-mono-s' }, children: ['GAIN 4,920 FT · HIGH 11,483 FT'] },
    chart('trip', JSON.stringify(ELE), String(KM), THREE()),
  ] },
  chart('spec', '[2169,3551,2400]', '23.2', [cv('phone', 358, 0, 122)]),      // N = 2: read from the array's length
  chart('low', '[-86,950]', '0.5', [cv('phone', 358, 0, 122)]),
  SPEED,
];
const BAD_CHARTS = [
  chart('notjson', '[2000,2010', '1', THREE()),
  chart('object', '{"0":2000,"1":2010,"length":2}', '1', THREE()),
  chart('string', '"2000,2010"', '1', THREE()),
  chart('empty', '[]', '1', THREE()),
  chart('strings', '[2000,"2010"]', '1', THREE()),
  chart('nulls', '[2000,null]', '1', THREE()),
  chart('nokm', '[2000,2010]', undefined, THREE()),
  chart('badkm', '[2000,2010]', 'far', THREE()),
];
const BAD = BAD_CHARTS.concat([
  chart('trip', JSON.stringify(ELE), String(KM), THREE().concat([cv('odd', 72, 72, 120), cv('neg', 358, -4, 120)])),
]);
const NONE = [{ tag: 'section', attrs: { class: 'rep-prof' }, children: [SPEED] }];
const EMPTY = [{ tag: 'p', attrs: {}, children: ['A page without a chart.'] }];

// ---------------------------------------------------------------- fixture

let tab, trip, wide, col, phone, spec, low;
check('fixture: the script runs on a report page', () => {
  tab = open(MAIN);
  trip = tab.byId('trip');
  [wide, col, phone] = ['wide', 'col', 'phone'].map((s) => only(trip, '.cv--' + s));
  spec = only(tab.byId('spec'), '.cv');
  low = only(tab.byId('low'), '.cv');
});
check('fixture: each .cv of a chart with data-pf gets a hidden crosshair and label of its own', () => {
  for (const c of [wide, col, phone, spec, low]) {
    const x = only(c, '.pf-x'), l = only(c, '.pf-l');
    for (const el of [x, l]) {
      eq(el.tagName, 'SPAN');
      eq(el.parentNode, c);
      eq(el.getAttribute('aria-hidden'), 'true');
      eq(el.hidden, true);
      eq(el.hasAttribute('tabindex'), false);
      eq(el.hasAttribute('role'), false);
      eq(el.textContent, '');
    }
    eq(all(c, 'span').length, 2);
    ok(listened(c).indexOf('pointermove') !== -1, 'no pointermove listener on the .cv');
  }
});
check('fixture: a chart without data-pf is left alone', () => {
  const s = tab.byId('speed');
  eq(all(s, 'span').length, 0);
  for (const el of [s].concat(s.descendants())) eq(listened(el).length, 0);
});

// ---------------------------------------------------------------- labels

check('labels: miles and feet, with a separator', () => {
  place(spec, 0, 358);
  units(tab, false);
  move(spec, 179);
  ok(seen(spec).on, 'the readout does not show');
  eq(seen(spec).text, '7.2 MI · 11,650 FT');
});
check('labels: km and metres under html.km, read at every move', () => {
  units(tab, true);
  move(spec, 179);
  eq(seen(spec).text, '11.6 KM · 3,551 M');
  units(tab, false);
  move(spec, 179);
  eq(seen(spec).text, '7.2 MI · 11,650 FT');
});
check('labels: both ends of a chart of three samples', () => {
  units(tab, false);
  move(spec, 0);
  eq(seen(spec).text, '0.0 MI · 7,116 FT');
  move(spec, 358);
  eq(seen(spec).text, '14.4 MI · 7,874 FT');
  units(tab, true);
  move(spec, 358);
  eq(seen(spec).text, '23.2 KM · 2,400 M');
  move(spec, 0);
  eq(seen(spec).text, '0.0 KM · 2,169 M');
});
check('labels: no separator under a thousand, and below sea level', () => {
  place(low, 0, 358);
  units(tab, true);
  move(low, 0);
  eq(seen(low).text, '0.0 KM · -86 M');
  move(low, 358);
  eq(seen(low).text, '0.5 KM · 950 M');
  units(tab, false);
  move(low, 0);
  eq(seen(low).text, '0.0 MI · -282 FT');
  move(low, 358);
  eq(seen(low).text, '0.3 MI · 3,117 FT');
});

// ---------------------------------------------------------------- mapping

check('mapping: the wide chart at half its viewBox width', () => {
  // 30.2 samples along the axis: the pointer is 154.384 px into a .cv of 624 px drawn from a viewBox of 1248 with 72 of
  // padding; sample 30 (2,300 m) at 4.1 km of 20.6
  place(wide, 100, 624);
  units(tab, true);
  move(wide, 254.384);
  eq(seen(wide).text, '4.1 KM · 2,300 M');
  eq(seen(wide).x, '154px');
  units(tab, false);
  move(wide, 254.384);
  eq(seen(wide).text, '2.6 MI · 7,546 FT');
});
for (const [what, size, left, width, t] of [
  ['wide at 624 px', 'wide', 100, 624, 100.3], ['wide at 1248 px', 'wide', 0, 1248, 61.1], ['wide at 936 px', 'wide', 8, 936, 12.2],
  ['col at 359 px', 'col', 20, 359, 100.3], ['col at 718 px', 'col', 20, 718, 5.1],
  ['phone at 358 px', 'phone', 16, 358, 45.1], ['phone at 179 px', 'phone', 16, 179, 140.2]]) {
  check('mapping: ' + what, () => {
    const c = { wide: wide, col: col, phone: phone }[size];
    place(c, left, width);
    const cx = clientAt(c, t, N);
    const i = Math.floor(t);                  // t is never in the upper half of a step here: no rounding question
    for (const km of [true, false]) {
      units(tab, km);
      move(c, cx);
      eq(seen(c).text, want(ELE[i], t / N * KM, km));
      eq(seen(c).x, Math.floor(cx - left) + 'px');
    }
  });
}

// ---------------------------------------------------------------- nearest sample

check('nearest sample: round(f * N), not the sample below', () => {
  place(wide, 100, 624);
  units(tab, true);
  for (const [t, i] of [[74.4, 74], [74.6, 75], [0.4, 0], [0.6, 1], [12.49, 12], [12.51, 13], [149.4, 149], [149.6, 150]]) {
    move(wide, clientAt(wide, t, N));
    eq(seen(wide).text, want(ELE[i], t / N * KM, true), 't = ' + t);
  }
});
check('nearest sample: N comes from the length of data-pf', () => {
  place(spec, 0, 358);
  units(tab, true);
  move(spec, clientAt(spec, 0.6, 2));
  eq(seen(spec).text, '7.0 KM · 3,551 M');
  move(spec, clientAt(spec, 1.4, 2));
  eq(seen(spec).text, '16.2 KM · 3,551 M');
  move(spec, clientAt(spec, 1.6, 2));
  eq(seen(spec).text, '18.6 KM · 2,400 M');
});

// ---------------------------------------------------------------- clamped ends

check('clamped ends: left of the axis, the first sample at 0.0 and the crosshair on the axis', () => {
  place(wide, 100, 624);
  for (const cx of [100, 120, 135.9, 60, -500]) {
    units(tab, true);
    move(wide, cx);
    eq(seen(wide).text, '0.0 KM · 2,000 M', 'clientX ' + cx);
    eq(seen(wide).x, '36px', 'clientX ' + cx);           // 72 of 1248 at half size
    units(tab, false);
    move(wide, cx);
    eq(seen(wide).text, '0.0 MI · 6,562 FT', 'clientX ' + cx);
  }
  place(col, 20, 359);
  move(col, 20);
  eq(seen(col).x, '36px');
  place(phone, 16, 358);
  units(tab, true);
  for (const cx of [16, 10]) {
    move(phone, cx);
    eq(seen(phone).text, '0.0 KM · 2,000 M');
    eq(seen(phone).x, '0px');
  }
});
check('clamped ends: at or past the right edge, the last sample at the whole distance, the crosshair inside', () => {
  place(wide, 100, 624);
  for (const cx of [724, 760, 2000]) {
    units(tab, true);
    move(wide, cx);
    eq(seen(wide).text, '20.6 KM · 3,500 M', 'clientX ' + cx);
    eq(seen(wide).x, '623px', 'clientX ' + cx);
    units(tab, false);
    move(wide, cx);
    eq(seen(wide).text, '12.8 MI · 11,483 FT', 'clientX ' + cx);
  }
  place(col, 20, 359);
  move(col, 379);
  eq(seen(col).x, '358px');
  place(phone, 16, 358);
  move(phone, 374);
  eq(seen(phone).x, '357px');
});

// ---------------------------------------------------------------- label clamp

check('label clamp: held at the left edge of the .cv', () => {
  place(wide, 100, 624);
  units(tab, true);
  move(wide, 100);                                      // centred on 36 px, the label would start left of the chart
  eq(seen(wide).l, '0px');
  place(phone, 16, 358);
  move(phone, 16);
  eq(seen(phone).l, '0px');
});
check('label clamp: held at the right edge of the .cv', () => {
  place(wide, 100, 624);
  units(tab, true);
  move(wide, 724);
  eq(seen(wide).l, Math.floor(624 - labelWidth('20.6 KM · 3,500 M')) + 'px');      // 489px
  units(tab, false);
  move(wide, 724);
  eq(seen(wide).l, Math.floor(624 - labelWidth('12.8 MI · 11,483 FT')) + 'px');    // 482px
});
check('label clamp: centred on the crosshair where there is room', () => {
  place(wide, 100, 624);
  units(tab, true);
  move(wide, 254.384);
  eq(seen(wide).l, Math.round(154.384 - labelWidth('4.1 KM · 2,300 M') / 2) + 'px');   // 91px
});
check('label clamp: a label wider than its chart starts at the left edge', () => {
  place(phone, 16, 100);
  units(tab, false);
  move(phone, 66);
  eq(seen(phone).l, '0px');
});
check('label clamp: a sweep over every width, both units, always inside the .cv', () => {
  for (const [c, left, width] of [[wide, 100, 624], [col, 20, 359], [phone, 16, 358]]) {
    place(c, left, width);
    for (const km of [true, false]) {
      units(tab, km);
      for (let cx = left - 40; cx <= left + width + 40; cx += 7) {
        move(c, cx);
        const s = seen(c), lw = labelWidth(s.text), L = parseFloat(s.l), X = parseFloat(s.x);
        const at = c.getAttribute('class') + ' clientX ' + cx + ': ' + JSON.stringify(s);
        ok(s.on, at);
        ok(L >= 0 && L + lw <= width, at);
        ok(X >= 0 && X <= width - 1, at);
        if (X - lw / 2 >= 1 && X + lw / 2 <= width - 1) ok(Math.abs(L + lw / 2 - X) < 1.5, 'not centred: ' + at);
      }
    }
  }
});

// ---------------------------------------------------------------- touch

check('touch: a finger and a pen update the readout as the mouse does', () => {
  place(wide, 100, 624);
  units(tab, false);
  move(wide, 254.384);
  const mouse = seen(wide);
  for (const type of ['touch', 'pen']) {
    move(wide, 400);                                    // somewhere else first, then away (the hide checks own leaving)
    leave(wide);
    move(wide, 254.384, type);
    ok(seen(wide).on, type + ': the readout does not show');
    eq(JSON.stringify(seen(wide)), JSON.stringify(mouse), type);
  }
});
check('touch: a finger moved sideways along the phone chart', () => {
  place(phone, 16, 358);
  units(tab, true);
  leave(phone);
  for (const t of [10.2, 50.2, 90.2, 130.2]) {
    const cx = clientAt(phone, t, N);
    move(phone, cx, 'touch');
    eq(seen(phone).text, want(ELE[Math.floor(t)], t / N * KM, true));
    eq(seen(phone).x, Math.floor(cx - 16) + 'px');
  }
});

// ---------------------------------------------------------------- hide

check('hide: pointerleave of the .cv hides both', () => {
  place(wide, 100, 624);
  move(wide, 254.384);
  ok(seen(wide).on);
  leave(wide);
  ok(seen(wide).off);
  move(wide, 254.384);
  ok(seen(wide).on, 'a move after leaving shows the readout again');
});
check('hide: pointercancel of the .cv hides both', () => {
  place(phone, 16, 358);
  move(phone, 100, 'touch');
  ok(seen(phone).on);
  cancel(phone);
  ok(seen(phone).off);
});
check('hide: leaving one .cv leaves the readout of another', () => {
  place(wide, 100, 624);
  move(wide, 254.384);
  leave(col);
  leave(tab.byId('speed').firstChild);
  ok(seen(wide).on);
});
check('hide: other keys leave the readout', () => {
  place(wide, 100, 624);
  place(spec, 0, 358);
  move(wide, 254.384);
  move(spec, 179);
  for (const k of ['Enter', 'Tab', 'ArrowLeft', 'Esc', 'e']) {
    key(tab, k);
    ok(seen(wide).on && seen(spec).on, k);
  }
});
check('hide: Escape hides every readout of the page', () => {
  place(wide, 100, 624);
  place(spec, 0, 358);
  move(wide, 254.384);
  move(spec, 179);
  key(tab, 'Escape');
  ok(seen(wide).off, 'the wide chart still shows its readout');
  ok(seen(spec).off, 'the second chart still shows its readout');
  move(wide, 254.384);
  ok(seen(wide).on, 'a move after Escape shows the readout again');
  key(tab, 'Escape');
});

// ---------------------------------------------------------------- no width

check('no width: a .cv that is not displayed shows nothing', () => {
  leave(col);
  const before = seen(col).text;
  place(col, 0, 0);
  move(col, 10);
  ok(seen(col).off);
  eq(seen(col).text, before);                          // not even written
});

// ---------------------------------------------------------------- malformed

check('malformed: a bad data-pf or data-pf-km throws nothing and gives its chart no readout', () => {
  const bad = open(BAD);
  for (const c of BAD_CHARTS) {
    const el = bad.byId(c.attrs.id);
    eq(all(el, 'span').length, 0, c.attrs.id);
    for (const d of el.descendants()) eq(listened(d).length, 0, c.attrs.id);
  }
  // the good chart on the same page still has its readout, and its .cv whose padding is not inside its width none
  const t = bad.byId('trip');
  for (const s of ['odd', 'neg']) eq(all(only(t, '.cv--' + s), 'span').length, 0, s);
  const w = only(t, '.cv--wide');
  place(w, 100, 624);
  move(w, 254.384);
  ok(seen(w).on);
  eq(seen(w).text, '2.6 MI · 7,546 FT');
  ok(listened(docOf(bad)).indexOf('keydown') !== -1);
  key(bad, 'Escape');
  ok(seen(w).off);
});
check('malformed: a page whose every chart is malformed listens to nothing', () => {
  const bad = open(BAD_CHARTS);
  eq(all(bad.body, 'span').length, 0);
  eq(listened(docOf(bad)).length, 0);
});

// ---------------------------------------------------------------- no data-pf

check('no data-pf: nothing created, nothing listened to', () => {
  for (const children of [NONE, EMPTY]) {
    const t = open(children);
    eq(all(t.body, '.pf-x').length + all(t.body, '.pf-l').length + all(t.body, 'span').length, 0);
    for (const el of [docOf(t), t.body.parentNode, t.body].concat(t.body.descendants())) eq(listened(el).length, 0);
  }
});

console.log(checks + ' checks passed');
