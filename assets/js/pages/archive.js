/* Map & archive: region tabs (ARIA tabs, automatic activation) and activity filters for the report table.
   Without JS every region panel renders stacked and the table shows everything.
   A region page (/regions/<slug>/, body.p-region) is one panel and the same table for one region: it has no tab row,
   so the tab code finds nothing there; 'Show all' and the filter run as here. */
(function () {
  'use strict';
  var page = document.body.classList;
  if (!page.contains('p-archive') && !page.contains('p-region')) return;

  // ------------------------------------------------------------ region tabs
  // The row is a .tabs-x: base.js scrolls the selected tab into the row after a click or key press (and once at start).
  var list = document.querySelector('.arc-tabs[role="tablist"]');
  var sec = document.querySelector('.arc-map');
  var h = (location.hash || '').slice(1);
  try { h = decodeURIComponent(h); } catch (e) { /* keep it as typed */ }
  var target = h ? document.getElementById(h) : null;
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
    };
    panels.forEach(function (p, j) {
      if (!p) return;
      p.setAttribute('role', 'tabpanel');
      p.setAttribute('aria-labelledby', tabs[j].id);
      // no tabindex: every panel starts with focusable pins/rows, and a focusable panel would take focus (and a ring) on #region- links
    });
    list.hidden = false;
    sec.classList.add('arc-js');
    // a #region-<slug> link opens that region's tab; a link to anything inside a panel opens the panel that holds it
    var start = 0, hit = false;
    panels.forEach(function (p, j) {
      if (p && target && p.contains(target)) { start = j; hit = p === target; }
    });
    select(start, false);
    // a region tab's panel: show the tab row above it, not just the panel the browser jumped to
    if (hit) target = list.parentNode;
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
  // Any other hash target (#region-utah in "Not on a region map", #other-places, #yr-2024, #all-reports) moved up when the
  // other panels were hidden: scroll it back into view now, and again after load (when the browser makes its own jump).
  if (target) {
    var toTarget = function () { target.scrollIntoView({ block: 'start' }); };
    requestAnimationFrame(toTarget);
    window.addEventListener('load', function () { setTimeout(toTarget, 0); }, { once: true });
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
      // closing a long list shortens the page above the reader: keep the button they pressed, which has focus, in view
      else b.scrollIntoView({ block: 'nearest' });
    });
  });
  // a link to one report's row (a report's 'See on the <Region> map', #arc-row-<slug>): a folded row is opened as a
  // cluster marker's click opens it (base.js), then centred, and its link focused, so base.js's focusin marks the trip
  // on the map and the row while focus stays (gap4-01, gap4-02)
  var row = target && target.classList && target.classList.contains('arc-row') ? target : null;
  if (row) {
    var land = function () {
      var ol2 = row.closest('ol');
      var btn = ol2 && ol2.classList.contains('arc-collapsed') && row.classList.contains('arc-more')
        ? document.querySelector('.arc-all-btn[aria-controls="' + ol2.id + '"]') : null;
      if (btn) btn.click();
      row.scrollIntoView({ block: 'center' });
      var a = row.querySelector('a');
      if (a) a.focus({ preventScroll: true });
    };
    requestAnimationFrame(land);
    window.addEventListener('load', function () { setTimeout(function () { row.scrollIntoView({ block: 'center' }); }, 0); }, { once: true });
  }

  // ------------------------------------------------------------ the region map's legend as an activity filter (maps-07)
  // Each activity of the legend becomes a toggle: pressed, the map dims every track, pin, journal line and cluster of
  // another activity (.is-out, archive.css; the markers carry data-act / data-acts from archive.inject_acts) and the
  // list beside it sets those rows aside (.is-actoff); the panel's live region says 'N of M reports'. While an activity
  // is chosen the list is not folded (its rows may all be behind 'Show all N'), and 'Show all N' waits; the fold comes
  // back as it was when the filter ends. One activity at a time; a second press, or another activity, changes it.
  // Without JavaScript the legend stays a list.
  document.querySelectorAll('.arc-panel').forEach(function (panel) {
    var map = panel.querySelector('.map[id]');
    var lis = Array.prototype.slice.call(panel.querySelectorAll('.arc-legend li[data-act]'));
    var live = panel.querySelector('.arc-plive');
    if (!map || lis.length < 2) return;
    var rows = Array.prototype.slice.call(panel.querySelectorAll('.arc-rows > li[data-key]'));
    var reports = rows.filter(function (r) { return r.dataset.kind && r.dataset.kind !== 'planned'; });
    var ol = panel.querySelector('ol.arc-rows[id]');
    var all = ol && document.querySelector('.arc-all-btn[aria-controls="' + ol.id + '"]');
    var foldWas = null;      // the list's fold when the filter began (null: no filter on)
    lis[0].parentNode.classList.add('arc-lg-ul');
    var buttons = lis.map(function (li) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'arc-lg-b';
      b.setAttribute('aria-pressed', 'false');
      while (li.firstChild) b.appendChild(li.firstChild);
      li.appendChild(b);
      b.addEventListener('click', function () { setAct(b.getAttribute('aria-pressed') === 'true' ? null : li.dataset.act); });
      return b;
    });
    function setAct(act) {
      lis.forEach(function (li, i) { buttons[i].setAttribute('aria-pressed', String(li.dataset.act === act)); });
      if (act) map.setAttribute('data-filter', act); else map.removeAttribute('data-filter');
      map.querySelectorAll('[data-act]').forEach(function (m) { m.classList.toggle('is-out', !!act && m.dataset.act !== act); });
      map.querySelectorAll('.mk-cluster').forEach(function (c) {
        c.classList.toggle('is-out', !!act && (c.dataset.acts || '').split(' ').indexOf(act) === -1);
      });
      rows.forEach(function (r) {
        var a = r.querySelector('[data-act]');
        r.classList.toggle('is-actoff', !!act && !!a && a.dataset.act !== act);
      });
      if (all) {
        if (act && foldWas === null) { foldWas = ol.classList.contains('arc-collapsed'); ol.classList.remove('arc-collapsed'); all.hidden = true; }
        else if (!act && foldWas !== null) { ol.classList.toggle('arc-collapsed', foldWas); all.hidden = false; foldWas = null; }
      }
      if (live) {
        var n = reports.filter(function (r) { return !r.classList.contains('is-actoff'); }).length;
        live.textContent = act ? n + ' of ' + reports.length + ' reports' : 'All ' + reports.length + ' reports';
      }
    }
  });

  // ------------------------------------------------------------ phones: every year of 'All reports' after the first folded
  // behind 'Show N reports' (phone-03), the region list's own idiom: a button under the year's head with aria-expanded and
  // aria-controls on its list, .arc-collapsed on the list. A year link, the activity filter (which recounts the years) and
  // an address inside a year unfold it; from 760 px nothing is folded, and without JavaScript nothing is.
  var narrow = window.matchMedia ? window.matchMedia('(max-width: 759.98px)') : null;
  var folds = [];
  var unfold = function (f) {
    if (!f.list.classList.contains('arc-collapsed')) return;
    f.list.classList.remove('arc-collapsed');
    f.btn.setAttribute('aria-expanded', 'true');
    f.btn.firstChild.nodeValue = 'Show fewer';
  };
  // 'Show 32 reports'; the Planned group holds planned routes, which are not reports
  var label = function (f) {
    var n = Array.prototype.filter.call(f.list.children, function (li) { return !li.hidden; }).length;
    var planned = f.group.dataset.group === 'yr-planned';
    return 'Show ' + n + (planned ? (n === 1 ? ' planned route' : ' planned routes') : (n === 1 ? ' report' : ' reports'));
  };
  if (narrow && narrow.matches) {
    Array.prototype.slice.call(document.querySelectorAll('.arc-yr')).slice(1).forEach(function (g) {
      var list = g.querySelector('ol.arc-rows2[id]'), head = g.querySelector('.arc-yr-h');
      if (!list || !head) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'alink arc-yr-btn';
      btn.setAttribute('aria-expanded', 'false');
      btn.setAttribute('aria-controls', list.id);
      var f = { list: list, btn: btn, group: g };
      btn.appendChild(document.createTextNode(label(f)));
      list.classList.add('arc-collapsed');
      head.insertAdjacentElement('afterend', btn);
      btn.addEventListener('click', function () {
        if (list.classList.contains('arc-collapsed')) { unfold(f); return; }
        list.classList.add('arc-collapsed');
        btn.setAttribute('aria-expanded', 'false');
        btn.firstChild.nodeValue = label(f);
        btn.scrollIntoView({ block: 'nearest' });
      });
      folds.push(f);
    });
    // a year link of the index, or an address inside a year: that year opens
    var openFor = function (id) {
      var el = id && document.getElementById(id);
      folds.forEach(function (f) { if (el && f.group.contains(el)) unfold(f); });
    };
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('.arc-years a[href^="#"]');
      if (a) openFor(a.getAttribute('href').slice(1));
    });
    window.addEventListener('hashchange', function () { openFor(decodeURIComponent(location.hash.slice(1))); });
    if (target) openFor(target.id);
    // a tablet turned from under 760 px to wider: nothing is folded there, so every year opens and its button goes
    var widen = function (e) { folds.forEach(function (f) { if (!e.matches) unfold(f); f.btn.hidden = !e.matches; }); };
    if (narrow.addEventListener) narrow.addEventListener('change', widen);
    else if (narrow.addListener) narrow.addListener(widen);
  }

  // ------------------------------------------------------------ activity filters
  var bar = document.querySelector('.arc-filt');
  if (!bar) return;
  var chips = Array.prototype.slice.call(bar.querySelectorAll('.fchip'));
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
  var years = Array.prototype.slice.call(document.querySelectorAll('.arc-years li[data-group]'));
  function countN(k) {
    return '<span class="sr">, </span>' + k + '<span class="sr"> ' + (k === 1 ? 'report' : 'reports') + '</span>';
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
      var pub = vis.filter(function (r) { return r.dataset.kind !== 'planned'; }).length;
      shown += pub;
      // the year index follows: a year with no rows in this activity drops out, the others count its published rows
      years.forEach(function (y) {
        if (y.dataset.group !== g.dataset.group) return;
        y.hidden = g.hidden;
        var n = y.querySelector('.arc-years-n');
        if (n) n.innerHTML = countN(pub);
      });
    });
    chips.forEach(function (c) {
      var on = c.dataset.filter === f;
      c.setAttribute('aria-checked', String(on));
      c.tabIndex = on ? 0 : -1;  // one tab stop (base.js moves it with the arrow keys)
    });
    if (live) {
      var chip = chips.filter(function (c) { return c.dataset.filter === f; })[0];
      var word = f === 'all' ? '' : ' ' + chip.querySelector('.fchip-l').textContent.toLowerCase();
      live.textContent = 'Showing ' + shown + word + (shown === 1 ? ' report' : ' reports');
    }
  }
  bar.hidden = false;
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      if (c.getAttribute('aria-checked') === 'true') return;
      apply(c.dataset.filter);
      // a filtered list is short: the folded years open, and a button's count follows what is left
      folds.forEach(unfold);
    });
  });
})();
