/* Section index pages: filter band (seasons / sub-types) and the ski region tablist. No dependencies. */
(function () {
  'use strict';
  if (!document.body.classList.contains('p-section')) return;

  // ------------------------------------------------------------ filter band: links that jump without JS, filter with it
  document.querySelectorAll('[data-filter-nav]').forEach(function (nav) {
    var scope = document.getElementById(nav.dataset.filterNav) || document.body;
    var links = nav.querySelectorAll('a[data-filter]');
    var live = nav.parentNode.querySelector('[data-filter-live]');
    var items = scope.querySelectorAll('[data-f]');

    function apply(key, announce) {
      var shown = 0;
      links.forEach(function (a) {
        if (a.dataset.filter === key) a.setAttribute('aria-current', 'true');
        else a.removeAttribute('aria-current');
      });
      items.forEach(function (el) {
        var keys = (el.dataset.f || '').split(' ');
        var on = key === 'all' || keys.indexOf(key) !== -1;
        el.classList.toggle('is-off', !on);
      });
      // a list section whose rows are all filtered out disappears too
      scope.querySelectorAll('.sec-more').forEach(function (sec) {
        var rows = sec.querySelectorAll('.trow');
        var vis = Array.prototype.filter.call(rows, function (r) { return !r.classList.contains('is-off'); }).length;
        sec.classList.toggle('is-off', rows.length > 0 && vis === 0);
      });
      scope.querySelectorAll('.trow').forEach(function (r) {
        if (!r.classList.contains('is-off') && !r.closest('.is-off')) shown++;
      });
      if (scope.querySelector('#featured') && !scope.querySelector('#featured').classList.contains('is-off')) shown++;
      if (announce && live) live.textContent = shown === 1 ? '1 report shown' : shown + ' reports shown';
    }

    nav.addEventListener('click', function (e) {
      var a = e.target.closest('a[data-filter]');
      if (!a) return;
      e.preventDefault();
      apply(a.dataset.filter, true);
      try {
        var h = a.dataset.filter === 'all' ? location.pathname + location.search : a.getAttribute('href');
        history.replaceState(null, '', h);
      } catch (err) { /* file:// */ }
    });

    // deep link: /ski/#season-2024-25 opens with that filter applied
    if (location.hash) {
      links.forEach(function (a) {
        if (a.getAttribute('href') === location.hash && a.dataset.filter !== 'all') apply(a.dataset.filter, false);
      });
    }
  });

  // ------------------------------------------------------------ ski region tablist
  var tablist = document.querySelector('.sec-tabs[role="tablist"]');
  if (!tablist) return;
  var tabs = Array.prototype.slice.call(tablist.querySelectorAll('[role="tab"]'));

  function select(tab, focus) {
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      var p = document.getElementById(t.getAttribute('aria-controls'));
      if (p) p.hidden = !on;
    });
    if (focus) tab.focus();
  }
  tablist.addEventListener('click', function (e) {
    var t = e.target.closest('[role="tab"]');
    if (t) select(t, false);
  });
  tablist.addEventListener('keydown', function (e) {
    var i = tabs.indexOf(document.activeElement);
    if (i < 0) return;
    var j = null;
    if (e.key === 'ArrowRight') j = (i + 1) % tabs.length;
    else if (e.key === 'ArrowLeft') j = (i - 1 + tabs.length) % tabs.length;
    else if (e.key === 'Home') j = 0;
    else if (e.key === 'End') j = tabs.length - 1;
    if (j === null) return;
    e.preventDefault();
    select(tabs[j], true);
  });

  // the map follows the list: resting on a report from another region switches the panel to it
  var list = document.querySelector('.sec-list[data-map-target]');
  var maps = document.getElementById(list ? list.dataset.mapTarget : '');
  if (!list || !maps) return;
  var timer = null;
  function tabFor(key) {
    var track = maps.querySelector('.mk-cat[data-key="' + key + '"]');
    var panel = track && track.closest('[role="tabpanel"]');
    return panel ? document.getElementById(panel.getAttribute('aria-labelledby')) : null;
  }
  function follow(row) {
    clearTimeout(timer);
    timer = setTimeout(function () {
      var t = tabFor(row.dataset.key);
      if (t && t.getAttribute('aria-selected') !== 'true') select(t, false);
    }, 220);
  }
  list.querySelectorAll('.trow[data-key]').forEach(function (row) {
    row.addEventListener('mouseenter', function () { follow(row); });
    row.addEventListener('focusin', function () { follow(row); });
    row.addEventListener('mouseleave', function () { clearTimeout(timer); });
  });
})();
