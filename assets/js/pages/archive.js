/* Map & archive: region tabs (ARIA tabs, automatic activation) and activity filters for the report table.
   Without JS every region panel renders stacked and the table shows everything. */
(function () {
  'use strict';
  if (!document.body.classList.contains('p-archive')) return;

  // ------------------------------------------------------------ region tabs
  var list = document.querySelector('.arc-tabs[role="tablist"]');
  var sec = document.querySelector('.arc-map');
  if (list && sec) {
    var tabs = Array.prototype.slice.call(list.querySelectorAll('[role="tab"]'));
    var panels = tabs.map(function (t) { return document.getElementById(t.getAttribute('aria-controls')); });
    var select = function (i, focus) {
      tabs.forEach(function (t, j) {
        var on = i === j;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        if (panels[j]) panels[j].hidden = !on;
      });
      if (focus) tabs[i].focus();
      var t = tabs[i];
      var l = t.offsetLeft - list.offsetLeft, r = l + t.offsetWidth;
      if (l < list.scrollLeft || r > list.scrollLeft + list.clientWidth) list.scrollLeft = Math.max(0, l - 16);
    };
    panels.forEach(function (p, j) {
      if (!p) return;
      p.setAttribute('role', 'tabpanel');
      p.setAttribute('aria-labelledby', tabs[j].id);
      // no tabindex: every panel starts with focusable pins/rows, and a focusable panel would take focus (and a ring) on #region- links
    });
    list.hidden = false;
    sec.classList.add('arc-js');
    var start = 0, hit = false;
    var h = (location.hash || '').slice(1);
    tabs.forEach(function (t, j) { if (t.getAttribute('aria-controls') === h) { start = j; hit = true; } });
    select(start, false);
    if (hit) {
      // show the tab row, not just the panel the browser jumped to (again after load, when the native jump happens)
      var w = list.parentNode;
      var toTabs = function () { w.scrollIntoView({ block: 'start' }); };
      requestAnimationFrame(toTabs);
      window.addEventListener('load', function () { setTimeout(toTabs, 0); }, { once: true });
    }
    tabs.forEach(function (t, j) {
      t.addEventListener('click', function () {
        select(j, false);
        try { history.replaceState(null, '', '#' + t.getAttribute('aria-controls')); } catch (e) { /* file:// */ }
      });
      t.addEventListener('keydown', function (e) {
        var k = e.key, n = tabs.length, to = null;
        if (k === 'ArrowRight') to = (j + 1) % n;
        else if (k === 'ArrowLeft') to = (j - 1 + n) % n;
        else if (k === 'Home') to = 0;
        else if (k === 'End') to = n - 1;
        if (to === null) return;
        e.preventDefault();
        select(to, true);
      });
    });
  }

  // ------------------------------------------------------------ "In this region": newest rows first, then "Show all N"
  document.querySelectorAll('.arc-all-btn').forEach(function (b) {
    var ol = document.getElementById(b.getAttribute('aria-controls'));
    if (!ol) return;
    var more = b.firstChild.nodeValue;
    ol.classList.add('arc-collapsed');
    b.hidden = false;
    b.addEventListener('click', function () {
      var open = ol.classList.toggle('arc-collapsed') === false;
      b.setAttribute('aria-expanded', String(open));
      b.firstChild.nodeValue = open ? 'Show fewer' : more;
      if (open) { var f = ol.querySelector('.arc-more a'); if (f) f.focus(); }
    });
  });

  // ------------------------------------------------------------ activity filters
  var bar = document.querySelector('.arc-filt');
  if (!bar) return;
  var chips = Array.prototype.slice.call(bar.querySelectorAll('.arc-chip'));
  var groups = Array.prototype.slice.call(document.querySelectorAll('.arc-yr'));
  var live = document.getElementById('arc-live');
  function plural(k, w, pl) { return k + ' ' + (k === 1 ? w : (pl || w + 'S')); }
  var NB = function (x) { return x.replace(/ /g, '\u00a0'); };
  // mirrors archive.py count_line() (core.count_items in a core.meta_items line): '3 REPORTS · INCL. 2 MULTI-DAY, 1 SERIES'
  // · '+ 1 PLANNED ROUTE'; a group of planned routes only reads '1 PLANNED ROUTE'. CSS draws the dots (.ml).
  function countLine(rows) {
    var pub = rows.filter(function (r) { return r.dataset.kind !== 'planned'; });
    var pl = rows.length - pub.length;
    var items = [];
    if (pub.length) {
      items.push(plural(pub.length, 'REPORT'));
      var md = pub.filter(function (r) { return r.dataset.kind === 'multi-day'; }).length;
      var se = pub.filter(function (r) { return r.dataset.kind === 'series'; }).length;
      var sub = [];
      if (md) sub.push(md + ' MULTI-DAY');
      if (se) sub.push(se + ' SERIES');
      if (sub.length) items.push('INCL. ' + sub.join(', '));
      if (pl) items.push('+ ' + plural(pl, 'PLANNED ROUTE'));
    } else if (pl) {
      items.push(plural(pl, 'PLANNED ROUTE'));
    }
    if (!items.length) return '';
    return '<span class="ml ml--end">' + items.map(function (x, i) {
      return '<span class="mi">' + (i ? '<span class="sr">, </span>' : '') + NB(x) + '</span>';
    }).join('') + '</span>';
  }
  function apply(f) {
    var shown = 0;
    groups.forEach(function (g) {
      // rows are core.table_row links (li > a.rtab-r[data-act]); hide the whole list item
      var rows = Array.prototype.slice.call(g.querySelectorAll('[data-act]'));
      var vis = rows.filter(function (r) {
        var on = f === 'all' || r.dataset.act === f;
        (r.closest('li') || r).hidden = !on;
        return on;
      });
      g.hidden = vis.length === 0;
      var c = g.querySelector('.arc-yr-n');
      if (c) c.innerHTML = countLine(vis);
      shown += vis.filter(function (r) { return r.dataset.kind !== 'planned'; }).length;
    });
    chips.forEach(function (c) { c.setAttribute('aria-pressed', String(c.dataset.filter === f)); });
    if (live) {
      var chip = chips.filter(function (c) { return c.dataset.filter === f; })[0];
      var word = f === 'all' ? '' : ' ' + chip.querySelector('.arc-chip-l').textContent.toLowerCase();
      live.textContent = 'Showing ' + shown + word + (shown === 1 ? ' report' : ' reports');
    }
  }
  bar.hidden = false;
  chips.forEach(function (c) { c.addEventListener('click', function () { apply(c.dataset.filter); }); });
})();
