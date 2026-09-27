/* Site behaviour: units toggle, phone menu, list ↔ map highlighting. No dependencies. */
(function () {
  'use strict';
  var root = document.documentElement;

  // ------------------------------------------------------------ units (MI | KM), remembered per browser
  function setUnits(u, announce) {
    root.classList.toggle('km', u === 'km');
    try { localStorage.setItem('units', u); } catch (e) { /* private mode */ }
    document.querySelectorAll('.units button').forEach(function (b) {
      b.setAttribute('aria-checked', String(b.dataset.units === u));
    });
    if (announce) {
      var live = document.getElementById('units-live');
      if (live) live.textContent = u === 'km' ? 'Showing kilometres and metres' : 'Showing miles and feet';
    }
  }
  setUnits(root.classList.contains('km') ? 'km' : 'mi', false);
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.units button');
    if (b) setUnits(b.dataset.units, true);
  });
  document.addEventListener('keydown', function (e) {
    var b = e.target.closest && e.target.closest('.units button');
    if (!b || (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight')) return;
    e.preventDefault();
    var next = b.dataset.units === 'mi' ? 'km' : 'mi';
    setUnits(next, true);
    var t = b.parentNode.querySelector('[data-units="' + next + '"]');
    if (t) t.focus();
  });
  var live = document.createElement('p');
  live.id = 'units-live'; live.className = 'sr'; live.setAttribute('aria-live', 'polite');
  document.body.appendChild(live);

  // ------------------------------------------------------------ phone / tablet menu
  var btn = document.querySelector('.menu-btn');
  var menu = document.getElementById('menu');
  function closeMenu(focusBtn) {
    if (!menu || menu.hidden) return;
    menu.hidden = true;
    btn.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('menu-open');
    if (focusBtn) btn.focus();
  }
  if (btn && menu) {
    btn.addEventListener('click', function () {
      var open = menu.hidden;
      menu.hidden = !open;
      btn.setAttribute('aria-expanded', String(open));
      document.body.classList.toggle('menu-open', open);
      if (open) { var f = menu.querySelector('a'); if (f) f.focus(); }
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenu(true); });
    window.addEventListener('resize', function () { if (window.innerWidth >= 1280) closeMenu(false); });
  }

  // ------------------------------------------------------------ list rows / pins highlight their track
  function highlight(map, key) {
    if (!map) return;
    map.classList.toggle('is-hl', !!key);
    map.querySelectorAll('.mk-cat').forEach(function (g) { g.classList.toggle('hl', g.dataset.key === key); });
  }
  document.querySelectorAll('[data-map-target]').forEach(function (list) {
    var map = document.getElementById(list.dataset.mapTarget);
    list.querySelectorAll('[data-key]').forEach(function (row) {
      row.addEventListener('mouseenter', function () { highlight(map, row.dataset.key); });
      row.addEventListener('mouseleave', function () { highlight(map, null); });
      row.addEventListener('focusin', function () { highlight(map, row.dataset.key); });
      row.addEventListener('focusout', function () { highlight(map, null); });
    });
  });
  document.querySelectorAll('.map').forEach(function (map) {
    map.querySelectorAll('.mk-pin').forEach(function (pin) {
      pin.addEventListener('mouseenter', function () { highlight(map, pin.dataset.key); });
      pin.addEventListener('mouseleave', function () { highlight(map, null); });
    });
  });
})();
