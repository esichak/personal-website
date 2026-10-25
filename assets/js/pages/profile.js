/* Single-day reports: a readout on the elevation profile (maps-04). A pointer on the chart (a mouse, a pen, or a finger
   moved sideways: report.css lets a finger still scroll the page vertically) draws a 1px crosshair and a Mono-S label
   above it with the distance and the elevation there, '7.2 MI · 11,650 FT', or '11.6 KM · 3,551 M' while the units
   switch has html.km (read at each move). core.chart_block writes the data: the .chart's data-pf holds the elevations in
   metres at the evenly spaced fractions 0, 1/N ... 1 of the track and data-pf-km the trip's distance; each .cv (one
   rendered width, one shown at a time) its viewBox width and the padding left of the profile's x axis (data-w,
   data-pad). The readout is a visual extra, hidden from assistive technology and never focusable: the mile table under
   the chart is the alternative. It goes when the pointer leaves or is cancelled, and on Escape. Without JavaScript or
   without data-pf nothing changes; a data-pf that is not an array of numbers leaves its chart without a readout. */
(function () {
  'use strict';
  var charts = document.querySelectorAll('.chart[data-pf]');
  if (!charts.length) return;
  var hides = [];

  // 11650 -> '11,650'
  function sep(n) {
    var s = String(Math.abs(n)), out = '';
    while (s.length > 3) { out = ',' + s.slice(-3) + out; s = s.slice(0, -3); }
    return (n < 0 ? '-' : '') + s + out;
  }
  // metres and km -> the label in the units the switch shows now
  function label(m, d) {
    if (document.documentElement.classList.contains('km')) return d.toFixed(1) + ' KM · ' + sep(Math.round(m)) + ' M';
    return (d / 1.609344).toFixed(1) + ' MI · ' + sep(Math.round(m * 3.28084)) + ' FT';
  }
  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  Array.prototype.forEach.call(charts, function (chart) {
    var pf = null, total = Number(chart.dataset.pfKm);
    try { pf = JSON.parse(chart.dataset.pf); } catch (e) { /* not JSON: no readout */ }
    if (!Array.isArray(pf) || !pf.length || !pf.every(isNum) || !(total >= 0)) return;
    var n = pf.length - 1;
    Array.prototype.forEach.call(chart.querySelectorAll('.cv'), function (cv) {
      var w = Number(cv.dataset.w), pad = Number(cv.dataset.pad);
      if (!(pad >= 0 && w > pad)) return;
      var x = document.createElement('span'), l = document.createElement('span');
      x.className = 'pf-x';
      l.className = 'pf-l';
      [x, l].forEach(function (el) { el.setAttribute('aria-hidden', 'true'); el.hidden = true; cv.appendChild(el); });
      function hide() { x.hidden = l.hidden = true; }
      cv.addEventListener('pointermove', function (e) {
        var r = cv.getBoundingClientRect();
        if (!(r.width > 0)) return;
        // the pointer in viewBox units, then as a fraction of the profile's axis (pad to w), held at both ends
        var f = Math.min(1, Math.max(0, ((e.clientX - r.left) * w / r.width - pad) / (w - pad)));
        var px = (pad + f * (w - pad)) * r.width / w;          // that point in CSS px from the left of the .cv
        l.textContent = label(pf[Math.round(f * n)], f * total);
        x.hidden = l.hidden = false;
        x.style.left = Math.max(0, Math.min(r.width - 1, Math.floor(px))) + 'px';
        // centred on the crosshair, kept inside the .cv; measured once it shows
        var lw = l.offsetWidth;
        l.style.left = Math.max(0, Math.min(Math.floor(r.width - lw), Math.round(px - lw / 2))) + 'px';
      });
      cv.addEventListener('pointerleave', hide);
      cv.addEventListener('pointercancel', hide);
      hides.push(hide);
    });
  });
  if (hides.length) {
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') hides.forEach(function (h) { h(); });
    });
  }
})();
