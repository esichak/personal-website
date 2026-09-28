/* Site behaviour: units toggle, phone menu, list ↔ map highlighting, current-section markers, full-screen map. No dependencies. */
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
  // while the menu is open, everything behind it is inert (focus and the reading cursor stay in the menu)
  function setInert(on) {
    ['#main', '.site-f', '.skip', '.bbar'].forEach(function (sel) {
      var el = document.querySelector(sel);
      if (!el) return;
      if (on) el.setAttribute('inert', ''); else el.removeAttribute('inert');
      el.inert = on;
    });
  }
  function closeMenu(focusBtn) {
    if (!menu || menu.hidden) return;
    menu.hidden = true;
    btn.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('menu-open');
    setInert(false);
    if (focusBtn) btn.focus();
  }
  if (btn && menu) {
    btn.addEventListener('click', function () {
      if (!menu.hidden) { closeMenu(false); return; }
      menu.hidden = false;
      btn.setAttribute('aria-expanded', 'true');
      document.body.classList.add('menu-open');
      setInert(true);
      var f = menu.querySelector('a'); if (f) f.focus();
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenu(true); });
    window.addEventListener('resize', function () { if (window.innerWidth >= 1280) closeMenu(false); });
  }

  // ------------------------------------------------------------ list rows ↔ map tracks, pins and clusters
  function highlight(map, keys) {
    if (!map) return;
    keys = keys || [];
    var has = function (k) { return keys.indexOf(k) !== -1; };
    map.classList.toggle('is-hl', keys.length > 0);
    map.querySelectorAll('.mk-cat[data-key], .mk-pin[data-key]').forEach(function (g) { g.classList.toggle('hl', has(g.dataset.key)); });
    map.querySelectorAll('.mk-cluster').forEach(function (c) {
      c.classList.toggle('hl', (c.dataset.keys || '').split(' ').some(has));
    });
  }
  function rowsFor(map) {
    return map && map.id ? document.querySelectorAll('[data-map-target="' + map.id + '"] [data-key]') : [];
  }
  function markRows(map, keys) {
    rowsFor(map).forEach(function (r) { r.classList.toggle('is-map-hl', !!keys && keys.indexOf(r.dataset.key) !== -1); });
  }
  document.querySelectorAll('[data-map-target]').forEach(function (list) {
    var map = document.getElementById(list.dataset.mapTarget);
    list.querySelectorAll('[data-key]').forEach(function (row) {
      var on = function () { highlight(map, [row.dataset.key]); };
      var off = function () { highlight(map, null); };
      row.addEventListener('mouseenter', on);
      row.addEventListener('mouseleave', off);
      row.addEventListener('focusin', on);
      row.addEventListener('focusout', off);
    });
  });
  document.querySelectorAll('.mk-pin[data-key], .mk-cluster').forEach(function (el) {
    var map = el.closest('.map[id]') || el.closest('.map');
    if (!map) return;
    var keys = el.classList.contains('mk-cluster') ? (el.dataset.keys || '').split(' ').filter(Boolean) : [el.dataset.key];
    var on = function () { highlight(map, keys); markRows(map, keys); };
    var off = function () { highlight(map, null); markRows(map, null); };
    el.addEventListener('mouseenter', on);
    el.addEventListener('mouseleave', off);
    el.addEventListener('focusin', on);
    el.addEventListener('focusout', off);
    if (el.classList.contains('mk-cluster') && rowsFor(map).length) {
      el.classList.add('is-linked');
      el.addEventListener('click', function () {
        var row = Array.prototype.find.call(rowsFor(map), function (r) { return keys.indexOf(r.dataset.key) !== -1; });
        if (!row) return;
        row.scrollIntoView({ block: 'center' });
        var a = row.matches('a') ? row : row.querySelector('a');
        if (a) a.focus({ preventScroll: true });
      });
    }
  });

  // ------------------------------------------------------------ current section in the report rail / phone bottom bar
  var navLinks = document.querySelectorAll('.rail-toc a[href^="#"], .bbar a[href^="#"]');
  if (navLinks.length && 'IntersectionObserver' in window) {
    var byId = {};
    navLinks.forEach(function (a) {
      var id = decodeURIComponent(a.getAttribute('href').slice(1));
      if (id && document.getElementById(id)) (byId[id] = byId[id] || []).push(a);
    });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        (byId[e.target.id] || []).forEach(function (a) {
          var nav = a.closest('.rail-toc, .bbar');
          nav.querySelectorAll('a[aria-current="location"]').forEach(function (x) { x.removeAttribute('aria-current'); });
          a.setAttribute('aria-current', 'location');
        });
      });
    }, { rootMargin: '-40% 0px -55% 0px' });
    Object.keys(byId).forEach(function (id) { io.observe(document.getElementById(id)); });
  }

  // ------------------------------------------------------------ full-screen map page: start centred on the track
  var fm = document.querySelector('.fs-map');
  if (fm) fm.scrollLeft = (fm.scrollWidth - fm.clientWidth) / 2;
})();
