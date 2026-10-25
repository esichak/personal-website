/* 404 page: it carries <base href="/personal-website/">, so a fragment-only link such as the skip link would
   resolve to the home page. Keep those links on this page. An address of the form /trips/<slug>/ (an old or mistyped
   link to a report) puts the slug's words into the search box (less its one- and two-digit numbers) and asks 'Looking
   for "<words>"?'; the words come from the address only, never from a guess at a trip, and are set as text, never as
   HTML. */
(function () {
  'use strict';
  if (!document.body.classList.contains('p-404')) return;
  var m = /\/trips\/([^\/?#]+)/.exec(location.pathname), box = document.getElementById('nf-q'), ask = document.getElementById('nf-ask');
  if (m && box && ask) {
    var words = '';
    try { words = decodeURIComponent(m[1]); } catch (e) { words = ''; }
    // a number of one or two digits (the month and day of a dated address, tallac-2026-09-24) is no date word of the index,
    // and every word typed must be found: it is left out, the year kept
    words = words.replace(/[-_+]+/g, ' ').split(/\s+/).filter(function (w) { return w && !/^\d{1,2}$/.test(w); }).join(' ');
    words = Array.from(words).slice(0, 200).join('');
    if (words) {
      box.value = words;
      ask.textContent = 'Looking for \u201c' + words + '\u201d?';
      ask.hidden = false;
    }
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href^="#"]');
    if (!a) return;
    var el = document.getElementById(a.getAttribute('href').slice(1));
    if (!el) return;
    e.preventDefault();
    if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1');
    el.focus({ preventScroll: true });
    el.scrollIntoView();
  });
})();
