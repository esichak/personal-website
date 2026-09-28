/* Section index pages: filter bands (Ski seasons, Other sub-types, MTB / Hiking years) and the ski region tablist.
   No dependencies; base.js supplies the radio-group keys (arrows, Home / End, Space / Enter). */
(function () {
  'use strict';
  if (!document.body.classList.contains('p-section')) return;

  // ------------------------------------------------------------ filter bands: links that jump without JS, a radio group with it
  document.querySelectorAll('[data-filter-nav]').forEach(function (nav) {
    var scope = document.getElementById(nav.dataset.filterNav) || document.body;
    var links = Array.prototype.slice.call(nav.querySelectorAll('a[data-filter]'));
    var live = nav.parentNode.querySelector('[data-filter-live]');
    var items = scope.querySelectorAll('[data-f]');

    // one radio per segment (the nav's aria-label names the group); a sub-type with no reports stays, disabled
    nav.setAttribute('role', 'radiogroup');
    nav.querySelectorAll('.sec-seg-a').forEach(function (a) {
      a.setAttribute('role', 'radio');
      a.removeAttribute('aria-current');
      if (!a.dataset.filter) {
        a.setAttribute('aria-disabled', 'true');
        a.setAttribute('aria-checked', 'false');
        a.tabIndex = -1;
      }
    });

    function visible(el) { return !el.classList.contains('is-off') && !el.closest('.is-off'); }

    function apply(key, announce) {
      links.forEach(function (a) {
        var on = a.dataset.filter === key;
        a.setAttribute('aria-checked', String(on));
        a.tabIndex = on ? 0 : -1;
      });
      items.forEach(function (el) {
        var keys = (el.dataset.f || '').split(' ');
        el.classList.toggle('is-off', !(key === 'all' || keys.indexOf(key) !== -1));
      });
      // a list section whose rows are all filtered out disappears too (a section with its own key, like the Planned
      // block, was set above)
      scope.querySelectorAll('.sec-more:not([data-f])').forEach(function (sec) {
        var rows = sec.querySelectorAll('.trow');
        var vis = Array.prototype.filter.call(rows, function (r) { return !r.classList.contains('is-off') && !r.closest('.sec-season.is-off'); }).length;
        sec.classList.toggle('is-off', rows.length > 0 && vis === 0);
      });
      if (!announce || !live) return;
      // published reports shown: rows (planned routes aside), the featured trip and the series
      var shown = 0;
      scope.querySelectorAll('.trow').forEach(function (r) {
        if (visible(r) && !r.closest('[data-f="planned"]')) shown++;
      });
      scope.querySelectorAll('#featured, #series').forEach(function (b) { if (visible(b)) shown++; });
      live.textContent = shown === 1 ? '1 report shown' : shown + ' reports shown';
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

    // deep link: /ski/#season-2024-25 or /mountain-biking/#year-2022 opens with that filter applied (only a link to a
    // group does: #featured is shared by several segments on Other)
    var key = 'all';
    var target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (target && target.classList.contains('sec-season')) {
      links.forEach(function (a) {
        if (a.getAttribute('href') === location.hash && a.dataset.filter !== 'all') key = a.dataset.filter;
      });
    }
    apply(key, false);
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
