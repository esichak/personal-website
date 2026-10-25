/* Site behaviour: units toggle, radio groups, scrollable tab rows, phone menu, list ↔ map highlighting, current-section
   markers, phone app bar, photo viewer, full-screen map. No dependencies. */
(function () {
  'use strict';
  var root = document.documentElement;

  // ------------------------------------------------------------ units (MI | KM), remembered per browser
  function setUnits(u, announce) {
    root.classList.toggle('km', u === 'km');
    try { localStorage.setItem('units', u); } catch (e) { /* private mode */ }
    document.querySelectorAll('.units button').forEach(function (b) {
      b.setAttribute('aria-checked', String(b.dataset.units === u));
      b.tabIndex = b.dataset.units === u ? 0 : -1;  // one tab stop; arrow keys move within the radio group
    });
    if (announce) {
      var live = document.getElementById('units-live');
      if (live) live.textContent = u === 'km' ? 'Showing kilometers and meters' : 'Showing miles and feet';
    }
  }
  setUnits(root.classList.contains('km') ? 'km' : 'mi', false);
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.units button');
    if (b) setUnits(b.dataset.units, true);
  });
  var live = document.createElement('p');
  live.id = 'units-live'; live.className = 'sr'; live.setAttribute('aria-live', 'polite');
  document.body.appendChild(live);

  // ------------------------------------------------------------ radio groups (units, filter bands, activity chips)
  // One tab stop per [role=radiogroup] (roving tabindex on the checked radio). Arrow keys (wrapping), Home and End move
  // focus and select (el.click(), so each page's own click handler applies the choice); Space / Enter select. Disabled
  // radios (aria-disabled="true") are skipped.
  var RADIO = '[role="radio"]:not([aria-disabled="true"])';
  var radios = function (g) {
    return Array.prototype.filter.call(g.querySelectorAll(RADIO), function (r) {
      return !r.hidden && r.closest('[role="radiogroup"]') === g;
    });
  };
  var syncRadios = function (g) {
    var rs = radios(g);
    if (!rs.length) return;
    var on = rs.filter(function (r) { return r.getAttribute('aria-checked') === 'true'; })[0] || rs[0];
    g.querySelectorAll('[role="radio"]').forEach(function (r) { r.tabIndex = r === on ? 0 : -1; });
  };
  document.querySelectorAll('[role="radiogroup"]').forEach(syncRadios);
  document.addEventListener('click', function (e) {
    var g = e.target.closest && e.target.closest('[role="radiogroup"]');
    if (g) window.requestAnimationFrame(function () { syncRadios(g); });
  });
  document.addEventListener('keydown', function (e) {
    var r = e.target.closest && e.target.closest('[role="radio"]');
    var g = r && r.closest('[role="radiogroup"]');
    if (!g || e.altKey || e.ctrlKey || e.metaKey) return;
    var k = e.key;
    if (k === ' ' || k === 'Enter') {
      if (r.tagName === 'BUTTON' || (k === 'Enter' && r.tagName === 'A')) return;  // the browser activates these itself
      e.preventDefault();
      r.click();
      return;
    }
    var rs = radios(g), i = rs.indexOf(r), j = null;
    if (!rs.length) return;
    if (k === 'ArrowRight' || k === 'ArrowDown') j = (i + 1) % rs.length;
    else if (k === 'ArrowLeft' || k === 'ArrowUp') j = (i - 1 + rs.length) % rs.length;
    else if (k === 'Home') j = 0;
    else if (k === 'End') j = rs.length - 1;
    if (j === null) return;
    e.preventDefault();
    rs[j].focus();
    rs[j].click();
  });

  // ------------------------------------------------------------ scrollable tab rows (.tabs-x > [role=tablist])
  // The row scrolls sideways instead of widening the page: .is-scroll when it overflows, .is-end at the right end (the fade
  // hides), and after a click or a key press the selected tab is scrolled into the row (never the page: no scrollIntoView).
  document.querySelectorAll('.tabs-x').forEach(function (box) {
    var tl = box.querySelector('[role="tablist"]');
    if (!tl) return;
    var upd = function () {
      box.classList.toggle('is-scroll', tl.scrollWidth > tl.clientWidth + 1);
      box.classList.toggle('is-end', tl.scrollLeft + tl.clientWidth >= tl.scrollWidth - 1);
    };
    var reveal = function () {
      window.requestAnimationFrame(function () {
        var tab = tl.querySelector('[aria-selected="true"]');
        if (!tab || tl.scrollWidth <= tl.clientWidth + 1) { upd(); return; }
        var l = tab.getBoundingClientRect().left - tl.getBoundingClientRect().left + tl.scrollLeft, r = l + tab.offsetWidth;
        if (l < tl.scrollLeft) tl.scrollLeft = l - 16;
        else if (r > tl.scrollLeft + tl.clientWidth) tl.scrollLeft = r - tl.clientWidth + 32;
        upd();
      });
    };
    if ('ResizeObserver' in window) new ResizeObserver(upd).observe(tl);
    tl.addEventListener('scroll', upd, { passive: true });
    tl.addEventListener('click', reveal);
    tl.addEventListener('keydown', reveal);
    upd();
    reveal();
  });

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
    // a link in the menu closes it: a same-page target (trips/#search on the Trips page) would otherwise leave it open
    menu.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('a[href]')) closeMenu(false); });
    window.addEventListener('resize', function () { if (window.innerWidth >= 1140) closeMenu(false); });
  }

  // ------------------------------------------------------------ list rows ↔ map tracks, pins and clusters
  function highlight(map, keys) {
    if (!map) return;
    keys = keys || [];
    var has = function (k) { return keys.indexOf(k) !== -1; };
    var hit = false;
    map.querySelectorAll('.mk-cat[data-key], .mk-pin[data-key]').forEach(function (g) {
      var on = has(g.dataset.key);
      g.classList.toggle('hl', on);
      hit = hit || on;
    });
    map.querySelectorAll('.mk-cluster').forEach(function (c) {
      var on = (c.dataset.keys || '').split(' ').some(has);
      c.classList.toggle('hl', on);
      hit = hit || on;
    });
    // the map dims everything else only when it has something to pick out: a list row whose trip this map does not
    // draw (a report without a track on a region page) leaves it as it is
    map.classList.toggle('is-hl', hit);
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
      var off = function () { highlight(map, (map && map._sel) || null); };   // back to a cluster's selection, if any
      row.addEventListener('mouseenter', on);
      row.addEventListener('mouseleave', off);
      row.addEventListener('focusin', on);
      row.addEventListener('focusout', off);
    });
  });
  // the row a key resolves to, brought into view: a folded list ("Show all N") is opened first, as its button would
  // folded: behind a list's 'Show all N' (archive.js .arc-collapsed), not set aside by a selection or the legend
  function folded(row) {
    var ol = row.closest('ol[id]');
    return !!ol && row.classList.contains('arc-more') && ol.classList.contains('arc-collapsed');
  }
  var opening = false;     // a press of a list's 'Show all' made here, not by the reader (it keeps a selection)
  function openRow(row, focus) {
    if (folded(row)) {
      var ol = row.closest('ol[id]');
      var more = document.querySelector('[aria-controls="' + ol.id + '"][aria-expanded="false"]');
      opening = true;
      try { if (more) more.click(); } finally { opening = false; }
    }
    if (row.offsetParent === null) return;      // set aside (.is-off, .is-actoff): nothing to show
    row.scrollIntoView({ block: 'center' });
    var a = row.matches('a') ? row : row.querySelector('a');
    if (a && focus) a.focus({ preventScroll: true });
  }
  // a cluster's selection (qa-02): its rows stay marked, the panel's other rows are set aside (.is-off, archive.css),
  // and the count line says 'N reports start here · Show all' (N counts report rows, never a planned route among the
  // keys). map._sel holds the keys, so a hover elsewhere returns to them instead of clearing. Only a region list
  // (map/, the region pages: ol.arc-rows) has a selection; the Ski panel's list keeps the plain cluster click.
  function panelList(map) {
    return map && map.id ? document.querySelector('ol.arc-rows[data-map-target="' + map.id + '"]') : null;
  }
  var countOf = function (map) {
    var list = document.querySelector('[data-map-target="' + map.id + '"]');
    var box = list && list.closest('.arc-inreg');
    return box ? box.querySelector('.arc-count') : null;
  };
  function unselect(map) {
    if (!map._sel) return;
    map._sel = null;
    if (map._selEl) { map._selEl.setAttribute('aria-pressed', 'false'); map._selEl = null; }
    rowsFor(map).forEach(function (r) { r.classList.remove('is-off'); });
    var c = countOf(map);
    if (c && map._count !== undefined) c.innerHTML = map._count;
    highlight(map, null);
    markRows(map, null);
  }
  function select(map, el, keys) {
    var rows = Array.prototype.filter.call(rowsFor(map), function (r) { return keys.indexOf(r.dataset.key) !== -1; });
    if (!rows.length) return;
    if (map._sel) unselect(map);
    map._sel = keys;
    map._selEl = el;
    el.setAttribute('aria-pressed', 'true');
    rowsFor(map).forEach(function (r) { r.classList.toggle('is-off', rows.indexOf(r) === -1); });
    highlight(map, keys);
    markRows(map, keys);
    var n = rows.filter(function (r) { return r.dataset.kind !== 'planned'; }).length;
    // a cluster of planned routes alone names them, not '0 reports'
    var what = n ? (n === 1 ? 'REPORT\u00a0STARTS' : 'REPORTS\u00a0START')
      : (rows.length === 1 ? 'PLANNED\u00a0ROUTE\u00a0STARTS' : 'PLANNED\u00a0ROUTES\u00a0START');
    var c = countOf(map);
    if (c) {
      if (map._count === undefined) map._count = c.innerHTML;
      c.innerHTML = '<span class="ml ml--end"><span class="mi">' + (n || rows.length) + '\u00a0' + what + '\u00a0HERE</span>'
        + '<span class="mi"><span class="sr">, </span><button type="button" class="arc-sel-clear">Show all</button></span></span>';
      c.querySelector('.arc-sel-clear').addEventListener('click', function () { unselect(map); el.focus(); });
    }
    // every selected row on view: a list folded behind 'Show all N' is opened when any of them is behind it; its button
    // focuses the first row it reveals, so the focus is put back on the cluster, where Enter clears the selection
    var behind = rows.filter(folded)[0];
    var had = document.activeElement;
    if (behind) openRow(behind, false);
    if (document.activeElement !== had && el.focus) el.focus({ preventScroll: true });
    openRow(rows[0], false);
  }
  var touch = false;
  try { touch = !!(window.matchMedia && window.matchMedia('(hover: none)').matches); } catch (err) { touch = false; }
  // a line that is a link (a.mk-line: a journal's days on a region map, which have no pin) is treated as a pin is
  document.querySelectorAll('.mk-pin[data-key], .mk-cluster, .mk-line[data-key]').forEach(function (el) {
    var map = el.closest('.map[id]') || el.closest('.map');
    if (!map) return;
    var keys = el.classList.contains('mk-cluster') ? (el.dataset.keys || '').split(' ').filter(Boolean) : [el.dataset.key];
    var on = function () { highlight(map, keys); markRows(map, keys); };
    var off = function () { highlight(map, map._sel || null); markRows(map, map._sel || null); };
    el.addEventListener('mouseenter', on);
    el.addEventListener('mouseleave', off);
    // focus listeners on the pins, and on the clusters that are linked to a list (below: those get a role and a name).
    // An unnamed cluster stays an aria-hidden pointer target: Chrome makes an SVG <g> that has a focus listener a Tab
    // stop, which put 14 dead stops on the home page (rule D4, tests/test_a11y_static.py).
    var matched = el.classList.contains('mk-cluster') ? Array.prototype.filter.call(rowsFor(map), function (r) {
      return keys.indexOf(r.dataset.key) !== -1;
    }) : [];
    // a cluster is linked only when a region list rows at least one of its keys (a map drawn with a trip no list shows)
    var linked = el.classList.contains('mk-cluster') && panelList(map) && matched.length;
    if (!el.classList.contains('mk-cluster') || linked) {
      el.addEventListener('focusin', on);
      el.addEventListener('focusout', off);
    }
    if (linked) {
      el.classList.add('is-linked');
      var n = matched.filter(function (r) { return r.dataset.kind !== 'planned'; }).length;
      el.removeAttribute('aria-hidden');
      el.setAttribute('role', 'button');
      el.setAttribute('tabindex', '0');
      el.setAttribute('aria-pressed', 'false');
      el.setAttribute('aria-label', n ? n + (n === 1 ? ' report starts here' : ' reports start here')
        : (matched.length === 1 ? 'A planned route starts here' : matched.length + ' planned routes start here'));
      var press = function () { if (map._sel && map._selEl === el) unselect(map); else select(map, el, keys); };
      el.addEventListener('click', press);
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); press(); }
      });
    } else if (el.classList.contains('mk-cluster') && matched.length) {
      // a list that is no region list (the Ski panel): a click brings the first row the cluster names into view and
      // focuses its link, as before Phase 12; the cluster stays an unnamed pointer target (rule D4)
      el.classList.add('is-linked');
      el.addEventListener('click', function () { openRow(matched[0], true); });
    } else if (touch && !el.classList.contains('mk-cluster') && rowsFor(map).length) {
      // a touch screen has no hover (gap1-03): the first tap on a pin or a line picks it out and opens its row, which
      // names the trip; a second tap on the same one follows the link; a tap on the map's paper clears the pick
      el.addEventListener('click', function (e) {
        if (map._tap === el) return;
        e.preventDefault();
        if (map._tap) map._tap.classList.remove('is-sel');
        map._tap = el;
        el.classList.add('is-sel');
        highlight(map, keys);
        markRows(map, keys);
        var row = Array.prototype.find.call(rowsFor(map), function (r) { return keys.indexOf(r.dataset.key) !== -1; });
        if (row && row.classList.contains('is-off')) { unselect(map); highlight(map, keys); markRows(map, keys); }
        if (row) openRow(row, true);
      });
    }
  });
  // a pick ends with a tap on the map's paper, or on anything outside the map (the next tap on its pin is a first tap)
  function untap(map) {
    if (!map._tap) return;
    map._tap.classList.remove('is-sel');
    map._tap = null;
    highlight(map, map._sel || null);
    markRows(map, map._sel || null);
  }
  if (touch) {
    document.addEventListener('click', function (e) {
      document.querySelectorAll('.map[id]').forEach(function (map) {
        if (!map._tap) return;
        if (map.contains(e.target) && e.target.closest && e.target.closest('.mk-pin, .mk-line, .mk-cluster')) return;
        untap(map);
      });
    });
  }
  // a list's own 'Show all N' / 'Show fewer', pressed by the reader, ends a selection first (the rows come back, then
  // the list folds or opens as asked)
  document.querySelectorAll('ol.arc-rows[data-map-target][id]').forEach(function (ol) {
    var map = document.getElementById(ol.dataset.mapTarget);
    var btn = document.querySelector('.arc-all-btn[aria-controls="' + ol.id + '"]');
    if (map && btn) btn.addEventListener('click', function () { if (map._sel && !opening) unselect(map); });
  });
  // Escape ends a selection and a pick; the focus, when it was on the count line's 'Show all' (which the restored count
  // line removes), goes back to the cluster
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    document.querySelectorAll('.map[id]').forEach(function (map) {
      untap(map);
      if (!map._sel) return;
      var c = countOf(map), back = c && c.contains(document.activeElement) ? map._selEl : null;
      unselect(map);
      if (back) back.focus({ preventScroll: true });
    });
  });

  // ------------------------------------------------------------ current section in the phone bottom bar
  // The current section is the last of the bar's targets whose top has passed 35% of the viewport (at the very bottom of
  // the page, the last one on screen). Targets are containers (the whole Beta block, the whole write-up), so each stays
  // current for its full height, and a bar without a Photos link keeps 'Report' through the photos. A rAF-throttled scroll
  // handler never skips a section on a fast scroll or a jump. A link the reader pressed stays current while its section
  // sits where the jump put it (a short section would otherwise hand the marker to the next one as soon as the jump
  // lands); once the page has moved from there, by any means, the marker follows the scroll again. The story layout's
  // section row (.rep-toc) is not marked: it scrolls away with the header, so it is only on screen above every section
  // it lists.
  var idOf = function (a) { return decodeURIComponent(a.getAttribute('href').slice(1)); };
  var spies = [];
  document.querySelectorAll('.bbar').forEach(function (nav) {
    var links = Array.prototype.slice.call(nav.querySelectorAll('a[href^="#"]'));
    var targets = [];
    links.forEach(function (a) {
      var el = idOf(a) && document.getElementById(idOf(a));
      if (el && targets.indexOf(el) === -1) targets.push(el);
    });
    targets.sort(function (a, b) { return a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1; });
    if (targets.length) spies.push({ links: links, targets: targets, pinned: null, pinTop: null });
  });
  var markCurrent = function (spy, id) {
    spy.links.forEach(function (a) { if (idOf(a) === id) a.setAttribute('aria-current', 'location'); else a.removeAttribute('aria-current'); });
  };
  if (spies.length) {
    var ticking = false;
    var update = function () {
      ticking = false;
      var lim = window.innerHeight * 0.35;
      var atEnd = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
      spies.forEach(function (spy) {
        if (spy.pinned) {
          var pel = document.getElementById(spy.pinned), ptop = pel ? pel.getBoundingClientRect().top : null;
          if (ptop === null) spy.pinned = null;
          else if (spy.pinTop === null) spy.pinTop = ptop;                  // where the jump put the section
          else if (Math.abs(ptop - spy.pinTop) > 8) spy.pinned = null;    // the page has moved on since
          if (spy.pinned) { markCurrent(spy, spy.pinned); return; }
        }
        var cur = spy.targets[0];
        spy.targets.forEach(function (el) {
          var top = el.getBoundingClientRect().top;
          if (top <= lim || (atEnd && top < window.innerHeight)) cur = el;
        });
        markCurrent(spy, cur.id);
      });
    };
    var request = function () { if (!ticking) { ticking = true; window.requestAnimationFrame(update); } };
    window.addEventListener('scroll', request, { passive: true });
    window.addEventListener('resize', request);
    // Back or Forward to another fragment moves the page without any of the inputs below
    window.addEventListener('hashchange', function () {
      var id = '';
      try { id = decodeURIComponent(window.location.hash.slice(1)); } catch (e) { /* a malformed escape names nothing */ }
      spies.forEach(function (spy) { if (spy.pinned !== id) spy.pinned = null; });
      request();
    });
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('.bbar a[href^="#"]');
      if (!a) return;
      spies.forEach(function (spy) {
        if (spy.links.indexOf(a) === -1 || !document.getElementById(idOf(a))) return;
        spy.pinned = idOf(a);
        spy.pinTop = null;   // read by the first update after the jump has landed
        markCurrent(spy, spy.pinned);
      });
      // the jump is made in this same task and the frame comes after it, so the landing spot is recorded after every
      // press, also when nothing moved (a second press of the link of the section already in place)
      request();
    });
    update();
  }

  // ------------------------------------------------------------ phone app bar: glyph + title once the H1 is under the header
  var h1 = document.getElementById('title');
  if (h1 && document.querySelector('.ab-trip') && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        document.body.classList.toggle('past-title', !e.isIntersecting && e.boundingClientRect.top < 52);
      });
    }, { rootMargin: '-52px 0px 0px 0px' }).observe(h1);
  }

  // ------------------------------------------------------------ photo viewer: photo links open in-page (their hrefs stay the
  // full .webp, so without JS, or with a modified click, they still open the file)
  var lb = document.querySelector('dialog.lb');
  if (lb && typeof lb.showModal === 'function') {
    var lbImg = lb.querySelector('.lb-img'), lbN = lb.querySelector('.lb-n'), lbCap = lb.querySelector('.lb-cap');
    var lbPrev = lb.querySelector('.lb-prev'), lbNext = lb.querySelector('.lb-next'), lbClose = lb.querySelector('.lb-close');
    var lbLive = document.getElementById('lb-live');
    var lbFile = lb.querySelector('.lb-file');
    var group = [], at = 0, opener = null;
    var LINKS = 'a.jph, a.mul-ph, a.ser-ph';
    // the viewer is a history entry while it is open, so a phone's Back gesture closes it instead of leaving the page:
    // pushed while our entry is on top; popping while a popstate is closing it (that close must not go back again)
    var pushed = false, popping = false;
    // a page reloaded (or come back to without the back-forward cache) while the viewer was open starts closed but on the
    // viewer's entry: forget its mark, so the next open does not stack a second entry for one Back to undo
    try { if (history.state && history.state.lb) history.replaceState(null, ''); } catch (err) { /* sandboxed */ }
    var say = function () {
      if (lbLive) lbLive.textContent = 'Photo ' + (at + 1) + ' of ' + group.length + '. ' + lbImg.alt;
    };
    // announce: moving within the open viewer (keys, buttons, swipes) says 'Photo N of M. <alt>'; the open says it too,
    // once the dialog is up (the click handler below)
    var show = function (i, announce) {
      at = Math.max(0, Math.min(group.length - 1, i));
      var a = group[at], th = a.querySelector('img');
      lb.classList.remove('lb--error');
      if (lbFile) { lbFile.hidden = true; lbFile.removeAttribute('href'); }
      var ss = th && th.getAttribute('srcset');
      lbImg.removeAttribute('srcset');
      lbImg.removeAttribute('sizes');
      // width descriptors (800/1600 copies) let a phone take the small file; density-only thumbnail sets would pick a
      // thumbnail, so those open the full file (the href)
      if (ss && /\s\d+w\s*(,|$)/.test(ss)) {
        // a set that stops at the .sm copy (the journal's photos, core.photo full=False) gets the file back for the viewer:
        // the thumbnail's width attribute is the file's own width
        var fw = th.getAttribute('width');
        if (fw && ss.indexOf(a.getAttribute('href') + ' ') === -1) ss += ', ' + a.getAttribute('href') + ' ' + fw + 'w';
        lbImg.setAttribute('sizes', '100vw');
        lbImg.setAttribute('srcset', ss);
      }
      // the thumbnail's size attributes give the viewer its shape before the file arrives, so the bar never jumps
      lbImg.style.aspectRatio = (th && th.getAttribute('width') && th.getAttribute('height'))
        ? th.getAttribute('width') + ' / ' + th.getAttribute('height') : '';
      lbImg.src = a.getAttribute('href');
      lbImg.alt = th ? th.alt : '';
      lbN.textContent = 'PHOTO ' + (at + 1) + ' / ' + group.length;
      lbCap.textContent = a.getAttribute('data-cap') || '';  // the caption only, never the alt text
      lbPrev.hidden = at === 0;
      lbNext.hidden = at === group.length - 1;
      if (document.activeElement && document.activeElement.hidden) lbClose.focus();
      if (announce) say(); else if (lbLive) lbLive.textContent = '';
    };
    // a photo that does not load says so, and offers its file (the full-size href) to open instead
    lbImg.addEventListener('error', function () {
      if (!lb.open || !group[at]) return;
      lb.classList.add('lb--error');      // base.css hides the broken image (its glyph and alt text) but keeps its box
      lbCap.textContent = 'This photo could not be loaded';
      if (lbFile) { lbFile.href = group[at].getAttribute('href'); lbFile.hidden = false; }
      // the caption is no live region: say it where the photo was announced
      if (lbLive) lbLive.textContent = 'Photo ' + (at + 1) + ' of ' + group.length + ' could not be loaded';
    });
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest(LINKS);
      if (!a || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      // a lead photo and its Photos grid share data-lb-group, so the viewer counts every photo of the trip once
      var gk = a.closest('[data-lb-group]');
      if (gk) {
        var key = gk.getAttribute('data-lb-group').replace(/"/g, '');
        group = Array.prototype.slice.call(document.querySelectorAll('[data-lb-group="' + key + '"] a.jph, a.jph[data-lb-group="' + key + '"]'));
      } else {
        var box = a.closest('.jrows, .mul-photos, .ser-phs, .rep-aside-ph');
        group = box ? Array.prototype.slice.call(box.querySelectorAll(LINKS)) : [a];
      }
      if (group.indexOf(a) === -1) group = [a];
      e.preventDefault();
      opener = a;
      show(group.indexOf(a));
      lb.showModal();
      lbClose.focus();
      say();
      try { history.pushState({ lb: true }, ''); pushed = true; } catch (err) { pushed = false; /* file:// or a sandbox */ }
    });
    window.addEventListener('popstate', function () {
      pushed = false;
      if (lb.open) { popping = true; lb.close(); }
    });
    lbPrev.addEventListener('click', function () { show(at - 1, true); });
    lbNext.addEventListener('click', function () { show(at + 1, true); });
    lbClose.addEventListener('click', function () { lb.close(); });
    lb.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft' && at > 0) { e.preventDefault(); show(at - 1, true); }
      if (e.key === 'ArrowRight' && at < group.length - 1) { e.preventDefault(); show(at + 1, true); }
    });
    // a swipe: one finger (or the mouse) moved 40 px sideways. base.css gives the dialog touch-action: pinch-zoom, so a
    // drag reaches here instead of scrolling the page; a second finger is a pinch, and a cancelled pointer is no swipe
    var sx = null, swiped = false;
    lb.addEventListener('pointerdown', function (e) { if (!e.isPrimary) return; sx = e.clientX; swiped = false; });
    lb.addEventListener('pointercancel', function () { sx = null; });
    lb.addEventListener('pointerup', function (e) {
      if (!e.isPrimary || sx === null) return;
      var dx = e.clientX - sx;
      sx = null;
      if (Math.abs(dx) > 40) {
        swiped = true;
        if (dx < 0 && at < group.length - 1) show(at + 1, true);
        if (dx > 0 && at > 0) show(at - 1, true);
      }
    });
    lbImg.addEventListener('dragstart', function (e) { e.preventDefault(); });
    lb.addEventListener('click', function (e) { if (e.target === lb && !swiped) lb.close(); });  // tap outside the photo
    lb.addEventListener('close', function () {
      if (opener) opener.focus({ preventScroll: true });
      opener = null;
      // closed by the button, Escape or a tap outside: take the viewer's history entry back off (a Back gesture already did)
      if (pushed && !popping && history.state && history.state.lb) {
        pushed = false;
        try { history.back(); } catch (err) { /* nothing to undo */ }
      }
      popping = false;
    });
  }

  // ------------------------------------------------------------ copy link (core.copy_link): the clipboard when the page
  // may use it ('Link copied' under the button for 4 s), else the URL in a selected read-only field to copy by hand. Both
  // hang under the button out of the flow (report.css), so nothing on the page moves; a button at the very bottom of the
  // screen (or just above the phone bottom bar) has them scrolled into view. The field is kept inside the page gutters
  // wherever its button sits, and closes on Escape, on a second press of the button, or on a press elsewhere.
  // closeCopy may be called twice, or from a listener that runs while it is at work, and then does nothing more. Taking
  // the focused field out of the page makes Chromium send focusout from inside removeChild, and a listener that removed
  // the field there made that call throw: so the field gives up the focus first, and one that has already left the page
  // is not removed again.
  var closeCopy = function (keep) {
    Array.prototype.forEach.call(document.querySelectorAll('.copy-pop'), function (p) {
      if (p === keep) return;
      if (p.contains(document.activeElement)) document.activeElement.blur();
      if (p.parentNode) p.parentNode.removeChild(p);
    });
  };
  // the field also closes when the keyboard moves on and on Escape from anywhere. Moving on is focus going to something
  // outside the control (relatedTarget): a focusout without one is the window losing focus, the field being taken out,
  // or a press on something that takes no focus, and the click listener below sees to a press.
  document.addEventListener('focusout', function (e) {
    var box = e.target.closest && e.target.closest('.copy');
    if (box && box.querySelector('.copy-pop') && e.relatedTarget && !box.contains(e.relatedTarget)) closeCopy();
  });
  document.addEventListener('keydown', function (e) {
    if ((e.key === 'Escape' || e.key === 'Esc') && document.querySelector('.copy-pop')) closeCopy();
  });
  // a touch screen with a share sheet (phone-06): the control becomes 'Share this page' (its data-share) with the share
  // icon, and a press opens the sheet; desktops keep 'Copy link' (their browsers may have navigator.share too)
  var canSheet = false;
  try { canSheet = !!(navigator.share && window.matchMedia && window.matchMedia('(hover: none)').matches); } catch (err) { canSheet = false; }
  if (canSheet) {
    Array.prototype.forEach.call(document.querySelectorAll('.copy-btn[data-share]'), function (b) {
      var l = b.querySelector('.copy-l');
      if (l) l.textContent = b.getAttribute('data-share');
      b.classList.add('is-share');
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.copy-btn');
    if (!b) { closeCopy(e.target.closest && e.target.closest('.copy-pop')); return; }
    var box = b.parentNode, url = b.getAttribute('data-copy') || window.location.href;
    var msg = box.querySelector('.copy-msg');
    if (box.querySelector('.copy-pop')) { closeCopy(); return; }
    closeCopy();
    // the share sheet, inside the press (it needs the gesture); the clipboard below when the sheet is refused, unless the
    // reader dismissed it (AbortError)
    if (b.classList.contains('is-share')) {
      var data = { title: document.title, url: url }, ok = false;
      try { ok = !navigator.canShare || navigator.canShare(data); } catch (err) { ok = false; }
      if (ok) {
        try {
          navigator.share(data).then(null, function (err) { if (!err || err.name !== 'AbortError') copyPath(b, box, url, msg); });
        } catch (err) { copyPath(b, box, url, msg); }
        return;
      }
    }
    copyPath(b, box, url, msg);
  });
  function copyPath(b, box, url, msg) {
    var byHand = function () {
      if (msg) msg.textContent = '';
      var pop = document.createElement('span'), inp = document.createElement('input');
      pop.className = 'copy-pop';
      inp.type = 'text'; inp.readOnly = true; inp.className = 'copy-url'; inp.value = url;
      inp.setAttribute('aria-label', 'Link to copy');
      inp.addEventListener('keydown', function (ev) {
        if (ev.key !== 'Escape' && ev.key !== 'Esc') return;
        b.focus();      // first: the field is then closed without the focus in it, and focus never rests on <body>
        closeCopy();
      });
      pop.appendChild(inp);
      box.appendChild(pop);
      var r = box.getBoundingClientRect(), vw = document.documentElement.clientWidth;
      pop.style.left = Math.round(Math.max(16 - r.left, Math.min(0, vw - 16 - r.left - pop.offsetWidth))) + 'px';
      if (pop.scrollIntoView) pop.scrollIntoView({ block: 'nearest', inline: 'nearest' });   // honours html's scroll-padding
      inp.focus({ preventScroll: true }); inp.select();
      inp.scrollLeft = 0;   // show the start of the address (https://…), not its tail
    };
    var done = function () {
      if (!msg) return;
      msg.textContent = 'Link copied';
      if (msg.scrollIntoView) msg.scrollIntoView({ block: 'nearest', inline: 'nearest' });
      window.clearTimeout(msg._t);
      msg._t = window.setTimeout(function () { msg.textContent = ''; }, 4000);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, byHand);
    else byHand();
  }

  // ------------------------------------------------------------ phones: the explorer's and the tick list's secondary
  // filters behind one Filters button (trips.py more_button; trips.css hides them below 760 px until it is pressed). The
  // form's is-more class opens them; open or closed is remembered for the session, per page. The count in the button is
  // the page script's (trips.js, ticklist.js)
  var moreBtn = document.querySelector('.trx-more-btn');
  if (moreBtn) {
    var moreForm = moreBtn.closest('form'), moreKey = 'trx-more:' + location.pathname;
    var setMore = function (on) { moreBtn.setAttribute('aria-expanded', String(on)); if (moreForm) moreForm.classList.toggle('is-more', on); };
    var moreWas = null;
    try { moreWas = sessionStorage.getItem(moreKey); } catch (err) { /* storage refused: closed */ }
    setMore(moreWas === '1');
    moreBtn.addEventListener('click', function () {
      var on = moreBtn.getAttribute('aria-expanded') !== 'true';
      setMore(on);
      try { sessionStorage.setItem(moreKey, on ? '1' : '0'); } catch (err) { /* storage refused */ }
    });
  }

  // ------------------------------------------------------------ full-screen map page: open on the route, not the image
  // centre. The address already names #route-start (core.fullscreen_link), so the browser has opened the map on the
  // route's start before this runs; here a route that fits the screen is centred and a wider one keeps its start in view
  // with as much of the route as fits beside it. The start is the one core.route_start marks: the first route path that
  // is not a faded one, the dashed ascent on a ski map. 'Drag to pan' shows until the map turns out to fit the screen.
  var fm = document.querySelector('.fs-map');
  if (fm && fm.getAttribute('data-fs') === 'region') {
    // a region's map (archive.region_fullscreen): many routes, a planned one among them, so the whole map is centred
    fm.scrollLeft = (fm.scrollWidth - fm.clientWidth) / 2;
    fm.scrollTop = (fm.scrollHeight - fm.clientHeight) / 2;
    if (fm.scrollWidth > fm.clientWidth + 1) document.body.classList.add('is-pannable');
    else document.body.classList.add('is-fit');
  } else if (fm) {
    var svg = fm.querySelector('.mv svg'), mapEl = fm.querySelector('.map');
    var vb = svg && svg.viewBox && svg.viewBox.baseVal;
    var bb = null, start = null;
    var trks = Array.prototype.filter.call(fm.querySelectorAll('.mk-trk'), function (p) {
      return !/stroke-opacity/.test(p.getAttribute('style') || '');
    });
    var first = trks.filter(function (p) { return /stroke-dasharray/.test(p.getAttribute('style') || ''); })[0] || trks[0];
    // mapkit's start disc sits on the recording's first point; the paths are the fallback (as core.route_start reads them)
    var disc = Array.prototype.filter.call(fm.querySelectorAll('circle'), function (c) {
      var st = c.getAttribute('style') || '';
      return /fill: #16171A; stroke: #FFFFFF/.test(st) && /^[57]$/.test(c.getAttribute('r') || '');
    })[0];
    if (trks.length && disc) {
      start = { x: parseFloat(disc.getAttribute('cx')), y: parseFloat(disc.getAttribute('cy')) };
    } else {
      try { if (first && first.getPointAtLength) start = first.getPointAtLength(0); } catch (err) { start = null; }
    }
    trks.forEach(function (p) {
      try {
        var b = p.getBBox();
        if (!b.width && !b.height) return;
        bb = bb ? { x0: Math.min(bb.x0, b.x), y0: Math.min(bb.y0, b.y), x1: Math.max(bb.x1, b.x + b.width), y1: Math.max(bb.y1, b.y + b.height) }
          : { x0: b.x, y0: b.y, x1: b.x + b.width, y1: b.y + b.height };
      } catch (err) { /* not rendered */ }
    });
    // one axis: centre the route when it fits, else keep the start in view and show as much of the route as fits
    var fit = function (a0, a1, s, size) {
      if ((a1 - a0) <= size - 32) return (a0 + a1) / 2 - size / 2;
      var lo = a0 - 24, hi = a1 + 24 - size;
      return s === null ? lo : Math.max(lo, Math.min(s - size / 2, hi));
    };
    if (bb && vb && vb.width && mapEl) {
      var k = mapEl.getBoundingClientRect().width / vb.width;
      fm.scrollLeft = fit(bb.x0 * k, bb.x1 * k, start ? start.x * k : null, fm.clientWidth);
      fm.scrollTop = fit(bb.y0 * k, bb.y1 * k, start ? start.y * k : null, fm.clientHeight);
    } else {
      fm.scrollLeft = (fm.scrollWidth - fm.clientWidth) / 2;
    }
    if (fm.scrollWidth > fm.clientWidth + 1) document.body.classList.add('is-pannable');
    else document.body.classList.add('is-fit');
  }
})();
