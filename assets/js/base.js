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
    window.addEventListener('resize', function () { if (window.innerWidth >= 1140) closeMenu(false); });
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
        if (row.offsetParent === null) {
          // the row sits in a collapsed list ("Show all N"): open it first
          var ol = row.closest('ol[id]');
          var more = ol && document.querySelector('[aria-controls="' + ol.id + '"][aria-expanded="false"]');
          if (more) more.click();
        }
        row.scrollIntoView({ block: 'center' });
        var a = row.matches('a') ? row : row.querySelector('a');
        if (a) a.focus({ preventScroll: true });
      });
    }
  });

  // ------------------------------------------------------------ current section in the report rail / phone bottom bar
  // Per nav, the current section is the last of its targets whose top has passed 35% of the viewport (at the very bottom
  // of the page, the last one on screen). Targets are containers (the whole Beta block, the whole write-up), so each stays
  // current for its full height, and a nav without a Photos link keeps 'Report' through the photos. A rAF-throttled
  // scroll handler never skips a section on a fast scroll or a jump.
  var idOf = function (a) { return decodeURIComponent(a.getAttribute('href').slice(1)); };
  var spies = [];
  document.querySelectorAll('.rail-toc, .bbar').forEach(function (nav) {
    var links = Array.prototype.slice.call(nav.querySelectorAll('a[href^="#"]'));
    var targets = [];
    links.forEach(function (a) {
      var el = idOf(a) && document.getElementById(idOf(a));
      if (el && targets.indexOf(el) === -1) targets.push(el);
    });
    targets.sort(function (a, b) { return a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1; });
    if (targets.length) spies.push({ links: links, targets: targets });
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
    window.addEventListener('hashchange', request);
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('.rail-toc a[href^="#"], .bbar a[href^="#"]');
      if (!a) return;
      spies.forEach(function (spy) { if (spy.links.indexOf(a) !== -1) markCurrent(spy, idOf(a)); });
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
    var group = [], at = 0, opener = null;
    var LINKS = 'a.jph, a.mul-ph, a.ser-ph';
    // announce: moving within the open viewer (keys, buttons, swipes) says 'Photo N of M. <alt>'; the first open does not
    var show = function (i, announce) {
      at = Math.max(0, Math.min(group.length - 1, i));
      var a = group[at], th = a.querySelector('img');
      var ss = th && th.getAttribute('srcset');
      lbImg.removeAttribute('srcset');
      lbImg.removeAttribute('sizes');
      // width descriptors (800/1600 copies) let a phone take the small file; density-only thumbnail sets would pick a
      // thumbnail, so those open the full file (the href)
      if (ss && /\s\d+w\s*(,|$)/.test(ss)) { lbImg.setAttribute('sizes', '100vw'); lbImg.setAttribute('srcset', ss); }
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
      if (lbLive) lbLive.textContent = announce ? 'Photo ' + (at + 1) + ' of ' + group.length + '. ' + lbImg.alt : '';
    };
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest(LINKS);
      if (!a || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      var box = a.closest('.jrows, .mul-photos, .ser-phs, .rep-aside-ph');
      group = box ? Array.prototype.slice.call(box.querySelectorAll(LINKS)) : [a];
      if (group.indexOf(a) === -1) group = [a];
      e.preventDefault();
      opener = a;
      show(group.indexOf(a));
      lb.showModal();
      lbClose.focus();
    });
    lbPrev.addEventListener('click', function () { show(at - 1, true); });
    lbNext.addEventListener('click', function () { show(at + 1, true); });
    lbClose.addEventListener('click', function () { lb.close(); });
    lb.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft' && at > 0) { e.preventDefault(); show(at - 1, true); }
      if (e.key === 'ArrowRight' && at < group.length - 1) { e.preventDefault(); show(at + 1, true); }
    });
    var sx = null, swiped = false;
    lb.addEventListener('pointerdown', function (e) { sx = e.clientX; swiped = false; });
    lb.addEventListener('pointerup', function (e) {
      if (sx === null) return;
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
    });
  }

  // ------------------------------------------------------------ full-screen map page: open on the route, not the image
  // centre. A route that fits the screen is centred; a wider one opens on its start (kept in view, as much of the route as
  // fits beside it). A map wider than the screen shows 'Drag to pan'.
  var fm = document.querySelector('.fs-map');
  if (fm) {
    var svg = fm.querySelector('.mv svg'), mapEl = fm.querySelector('.map');
    var vb = svg && svg.viewBox && svg.viewBox.baseVal;
    var bb = null, start = null;
    fm.querySelectorAll('.mk-trk').forEach(function (p) {
      try {
        var b = p.getBBox();
        if (!b.width && !b.height) return;
        if (!start && p.getPointAtLength) start = p.getPointAtLength(0);
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
  }
})();
