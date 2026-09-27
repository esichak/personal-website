/* 404 page: it carries <base href="/personal-website/">, so a fragment-only link such as the skip link would
   resolve to the home page. Keep those links on this page. */
(function () {
  'use strict';
  if (!document.body.classList.contains('p-404')) return;
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
