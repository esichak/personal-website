/* Multi-day reports: scrollspy for the sticky day nav. The chapter crossing a 1px line just under the header and
   the nav gets aria-current="location"; above Day 1 it is Overview. On phones the chip row scrolls the current
   chip into view. */
(function () {
  'use strict';
  var nav = document.querySelector('.mul-dnav');
  if (!nav || !('IntersectionObserver' in window)) return;
  var scroller = nav.querySelector('.mul-dn-in');
  var links = Array.prototype.slice.call(nav.querySelectorAll('a[data-day]'));
  var chapters = Array.prototype.slice.call(document.querySelectorAll('.mul-day[data-day]'));
  if (!chapters.length) return;
  var header = document.querySelector('.site-h');
  var current = null;
  var io = null;

  function lineY() {
    return (header ? header.getBoundingClientRect().height : 0) + nav.getBoundingClientRect().height + 24;
  }

  function reveal(a) {
    if (!scroller || scroller.scrollWidth <= scroller.clientWidth + 1) return;
    var left = a.offsetLeft - (scroller.clientWidth - a.offsetWidth) / 2;
    var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    scroller.scrollTo({ left: Math.max(0, left), behavior: reduce ? 'auto' : 'smooth' });
  }

  function set(key) {
    if (key === current) return;
    current = key;
    links.forEach(function (a) {
      if (a.dataset.day === key) { a.setAttribute('aria-current', 'location'); reveal(a); }
      else a.removeAttribute('aria-current');
    });
  }

  function fallback() {
    var y = lineY();
    if (chapters[0].getBoundingClientRect().top > y) { set('overview'); return; }
    var last = chapters[chapters.length - 1];
    if (last.getBoundingClientRect().bottom <= y) set(last.dataset.day);
  }

  function observe() {
    if (io) io.disconnect();
    var y = Math.round(lineY());
    var below = Math.max(0, window.innerHeight - y - 1);
    io = new IntersectionObserver(function (entries) {
      var hit = null;
      entries.forEach(function (e) { if (e.isIntersecting) hit = e.target; });
      if (hit) set(hit.dataset.day); else fallback();
    }, { rootMargin: (-y) + 'px 0px ' + (-below) + 'px 0px' });
    chapters.forEach(function (c) { io.observe(c); });
  }

  observe();
  var t = null;
  window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(observe, 150); });
})();
