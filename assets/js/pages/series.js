/* Series log: month scrollspy for the sticky month nav, the "Show days with write-ups only" filter (on by default as the
   reader mode; a link to a hidden day or month turns it off), and the written-entry navigation. The decisions (what a
   hash names, whether the filter starts on, whether a link must reveal its target, whether to re-scroll after loading)
   are pure helpers, exported for the Node tests. Without JS every day shows and the month links are plain anchors. */
(function (root) {
  'use strict';

  // '#day-5-2' -> {kind: 'day', id: 'day-5-2'}; '#month-2024-06' -> month; '#days' -> other; '' -> {kind: null, id: ''}
  function hashTarget(hash) {
    var id = String(hash || '').replace(/^#/, '');
    try { id = decodeURIComponent(id); } catch (e) { /* keep as typed */ }
    if (!id) return { kind: null, id: '' };
    if (id.indexOf('day-') === 0) return { kind: 'day', id: id };
    if (id.indexOf('month-') === 0) return { kind: 'month', id: id };
    return { kind: 'other', id: id };
  }

  // the filter starts on when it is the default and the URL hash does not point at something it would hide
  function startFiltered(defaultOn, hash, hiddenIds) {
    if (!defaultOn) return false;
    var t = hashTarget(hash);
    return !(t.id && hiddenIds.indexOf(t.id) !== -1);
  }

  // the id a link must reveal: the hash names a day or month the filter is hiding right now ('' when nothing is hidden)
  function revealId(filtered, hash, hiddenIds) {
    var t = hashTarget(hash);
    return filtered && t.id && hiddenIds.indexOf(t.id) !== -1 ? t.id : '';
  }

  // after the filter has shortened the page, scroll to the day or month the URL names: only when the page was opened by
  // a link or a typed address. On a reload or Back / Forward the browser puts the reader back where they were reading,
  // and a second scroll would throw them to the hash instead. navType is PerformanceNavigationTiming.type ('' if unknown).
  function landAfterLoad(filtered, hash, navType) {
    var k = hashTarget(hash).kind;
    return !!filtered && (k === 'day' || k === 'month') && (!navType || navType === 'navigate');
  }

  var api = { hashTarget: hashTarget, startFiltered: startFiltered, revealId: revealId, landAfterLoad: landAfterLoad };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.SeriesLog = api;
  if (typeof document === 'undefined') return;

  var log = document.querySelector('.ser-log');
  if (!log) return;
  var nav = log.querySelector('.ser-mnav');
  var links = nav ? Array.prototype.slice.call(nav.querySelectorAll('a[href^="#"]')) : [];
  var months = links.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });

  // ------------------------------------------------------------ scrollspy: the month in view gets aria-current="location"
  var ticking = false;
  function spy() {
    ticking = false;
    if (!nav) return;
    var line = nav.getBoundingClientRect().bottom + 48;
    var cur = -1;
    months.forEach(function (m, i) {
      if (m && m.offsetParent !== null && m.getBoundingClientRect().top <= line) cur = i;
    });
    var last = months[months.length - 1];
    if (cur >= 0 && last && last.getBoundingClientRect().bottom < nav.getBoundingClientRect().bottom) cur = -1;
    links.forEach(function (a, i) {
      if (i === cur) a.setAttribute('aria-current', 'location');
      else a.removeAttribute('aria-current');
    });
  }
  function onScroll() {
    if (!ticking) { ticking = true; window.requestAnimationFrame(spy); }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  spy();

  // ------------------------------------------------------------ filter: days with write-ups only
  var box = document.getElementById('ser-only');
  var live = document.getElementById('ser-live');
  if (!box) return;
  box.closest('.ser-only').hidden = false;
  // what the filter hides: track-only days and months without a write-up (series.css .is-wu), and with each of them
  // every id inside it (a day's number and title, a month's heading): those were link targets while the filter started
  // switched off (the public site before Phase 3), so an address that names one reveals its day or month as well
  var hidden = [];
  Array.prototype.forEach.call(log.querySelectorAll('.ser-day:not(.has-wu), .ser-month:not(.has-wu)'), function (el) {
    if (el.id && hidden.indexOf(el.id) === -1) hidden.push(el.id);   // a hidden day is also an id inside its hidden month
    Array.prototype.forEach.call(el.querySelectorAll('[id]'), function (c) { if (hidden.indexOf(c.id) === -1) hidden.push(c.id); });
  });
  function apply(announce) {
    var on = box.checked;
    log.classList.toggle('is-wu', on);
    links.forEach(function (a) {
      var off = on && a.dataset.wu === '0';
      if (off) { a.setAttribute('aria-disabled', 'true'); a.setAttribute('tabindex', '-1'); }
      else { a.removeAttribute('aria-disabled'); a.removeAttribute('tabindex'); }
    });
    if (announce && live) {
      live.textContent = on ? 'Showing the ' + box.dataset.wu + ' days with write-ups'
                            : 'Showing all ' + box.dataset.total + ' days';
    }
    spy();
  }
  // a direct link to a hidden day or month must land on it: turn the filter off, say so, and scroll there
  function reveal() {
    var id = revealId(box.checked, window.location.hash, hidden);
    if (!id) return;
    box.checked = false;
    apply(true);
    var el = document.getElementById(id);
    if (el) window.requestAnimationFrame(function () { el.scrollIntoView(); });
  }
  // the reader's own choice (the toggle, or 'Browse all recordings') lasts for the browser session, so a reload or Back
  // returns to the list as they left it; a link that merely revealed a hidden day is not a choice and is not kept
  var KEY = 'ser-only:' + window.location.pathname;
  function remembered() { try { return window.sessionStorage.getItem(KEY); } catch (e) { return null; } }
  function remember() { try { window.sessionStorage.setItem(KEY, box.checked ? '1' : '0'); } catch (e) { /* private mode */ } }
  box.addEventListener('change', function () { remember(); apply(true); });
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('[data-ser-all]');
    if (a) {
      // a choice even when a link has already revealed every day: it must still hold after a reload
      var was = box.checked;
      box.checked = false;
      remember();
      if (was) apply(true);
      return;
    }
    // a link to the fragment the URL already ends with fires no hashchange, so reveal its target here
    var h = e.target.closest && e.target.closest('a[href^="#"]');
    if (h && h.getAttribute('href') === window.location.hash) reveal();
  });
  window.addEventListener('hashchange', reveal);
  // the reader mode: written entries first (data-default), unless the reader chose otherwise this session or the URL
  // points at an entry the filter would hide
  var pref = remembered();
  box.checked = startFiltered(pref === null ? box.dataset.default === 'wu' : pref === '1', window.location.hash, hidden);
  apply(false);
  // a link to a day or a month (a shared entry, a journal-day search hit): the browser may have jumped to it before the
  // filter shortened the page, so land on it again once the list has its final length
  var landedY = null;
  function land() {
    var t = hashTarget(window.location.hash);
    var el = t.id && document.getElementById(t.id);
    if (el && log.contains(el) && el.offsetParent !== null) el.scrollIntoView();
    landedY = window.scrollY;
  }
  var navType = '';
  try { navType = (window.performance.getEntriesByType('navigation')[0] || {}).type || ''; } catch (e) { /* older browsers: treat as a fresh visit */ }
  if (landAfterLoad(box.checked, window.location.hash, navType)) {
    window.requestAnimationFrame(land);
    // once more when the photo and the fonts are in, unless the reader has scrolled on since the first landing
    if (document.readyState !== 'complete') {
      window.addEventListener('load', function () { if (landedY === null || Math.abs(window.scrollY - landedY) < 2) land(); }, { once: true });
    }
  }
})(typeof window !== 'undefined' ? window : this);
