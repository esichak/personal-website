/* Series log: month scrollspy for the sticky month nav, and the "Show days with write-ups only" filter.
   Without JS every day shows and the month links are plain anchors. */
(function () {
  'use strict';
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

  // ------------------------------------------------------------ filter: days with write-ups only (default: all days)
  var box = document.getElementById('ser-only');
  var live = document.getElementById('ser-live');
  if (!box) return;
  box.closest('.ser-only').hidden = false;
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
  box.addEventListener('change', function () { apply(true); });
  if (box.checked) apply(false); // restored by the browser on back/forward
})();
