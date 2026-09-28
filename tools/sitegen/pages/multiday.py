"""Multi-day trip report (kind: multi-day) — /trips/<slug>/.

Title block, trip strip, full-bleed overview map, then one block that carries the sticky day nav: the stitched
elevation profile, the Overview (stage table) and one chapter per day file (#day-N). Ends with the site pager.
Shared pieces come from report.py (title block, pager) and core; everything page-specific is prefixed .mul-.
Rendered fragments are trimmed here before they are inlined (slim, thin_ticks, unclash_band): features outside each
map frame are clipped and colliding axis labels dropped, which cuts the Chamonix–Zermatt page from 4.2 MB to 1.7 MB
without changing what is drawn. These belong in render.py/mapkit once it clips at the source.
"""
import os
import re

import markdown

from sitegen import core
from sitegen.core import esc, U, U_sub, n, link, icon, FT
from sitegen.pages import report

GENERIC_TITLE = re.compile(r'^\s*day\s*\d+\s*$', re.I)


# ---------------------------------------------------------------- small helpers

def day_title(d):
    """The day's own title ('A → B'), or '' when the day file only says 'Day N' (or nothing)."""
    t = (d.get('title') or '').strip()
    return '' if (not t or GENERIC_TITLE.match(t)) else t


def route_ends(days):
    """'Argentière → Zermatt' from the first day's start and the last day's end, when both titles are 'A → B'."""
    a, b = day_title(days[0]), day_title(days[-1])
    if '→' in a and '→' in b:
        return '%s → %s' % (a.split('→')[0].strip(), b.split('→')[-1].strip())
    return ''


def gpx_href(t, d):
    return 'gpx/%s-day-%s.gpx' % (t['slug'], d['id']) if d.get('track') else ''


def hut_nights(t):
    return sum(1 for d in t['days'] if d.get('hut'))


def high_day(t):
    hi = t['stats'].get('high_m')
    if hi is None:
        return None
    return next((d for d in t['days'] if d['stats'].get('high_m') == hi), None)


def caps_dist(km):
    mi, k = core.dist_vals(km)
    return U(mi + ' MI', k + ' KM') if mi else ''


def caps_elev(m, suffix=''):
    return U('%s FT%s' % (n(m * FT), suffix), '%s M%s' % (n(m), suffix)) if m is not None else ''


def elev_cell(m):
    return U(n(m * FT), n(m)) if m is not None else '—'


def title_title(t):
    return core.title_html(t['title'])


def arrow_html(text):
    """Escaped 'A → B' that never starts a line with the arrow."""
    return esc(text).replace(' → ', '\u00a0→ ')


def days_meta(t, parts=False):
    bits = ['%d DAYS' % len(t['days'])]
    h = hut_nights(t)
    if h:
        bits.append('%d HUT NIGHT%s' % (h, '' if h == 1 else 'S'))
    return bits if parts else ' · '.join(bits)


def nb(bits):
    """Mono-S meta whose parts wrap only between one another ('6 DAYS ·' / '5 HUT NIGHTS')."""
    bits = [b for b in bits if b]
    return ' '.join('<span class="mul-nb">%s%s</span>' % (b, ' ·' if i < len(bits) - 1 else '') for i, b in enumerate(bits))


_DRAWN = {}
_GPS = re.compile(r'l\d+(?:\.\d+)? \d+(?:\.\d+)?h-\d+(?:\.\d+)?z" style="fill: \{\{route\}\}')


def drawn(t, name):
    """Which key symbols a rendered map fragment actually draws, so key rows decode exactly what is on the map."""
    k = (t['slug'], name)
    if k not in _DRAWN:
        p = core.rendered(t, name + '.svg.html')
        s = open(p, encoding='utf-8').read() if os.path.exists(p) else ''
        _DRAWN[k] = {
            'skin': 'stroke-dasharray: 5 3' in s, 'ghost': 'stroke-opacity: .35' in s,
            'day': 'fill: #B8300F' in s, 'hut': 'class="mk-day"' in s, 'hut_named': 'class="mk-hut"' in s,
            'transfer': '>TRANSFER<' in s, 'gps': ('class="mk-gps"' in s) or bool(_GPS.search(s)),
            'start': bool(re.search(r'<circle[^>]*r="[57]"[^>]*fill: #16171A', s)),
            'end': bool(re.search(r'<rect[^>]*width="1[04]"[^>]*fill: #16171A', s)),
            'mile': 'class="mk-num"' in s,
        }
    return _DRAWN[k]


def key_items(t, names, route_label=None):
    """Key-row items for the symbols drawn on any of the named map renders (in a fixed order)."""
    f = {}
    for nm in names:
        for key, v in drawn(t, nm).items():
            f[key] = f.get(key) or v
    items = []
    if f.get('skin'):
        items += ['skin', 'ski']
    else:
        items.append(('route', route_label) if route_label else 'route')
    if f.get('ghost'):
        items.append(('ghost', 'Other days'))
    if f.get('day'):
        items.append(('day', 'Day label'))
    if f.get('hut'):
        items.append('hut' if f.get('hut_named') else 'dayend')  # 'Hut (night)' / 'End of day'
    if f.get('transfer'):
        items.append('transfer')
    if f.get('start') and f.get('end'):
        items.append('start_end')
    elif f.get('start') or f.get('end'):
        items.append('start' if f.get('start') else 'end')
    if f.get('gps'):
        items.append('gps')
    if f.get('mile'):
        items.append('mile')
    return items


# ---------------------------------------------------------------- fragment weight (local until render.py clips)

_SVG_OPEN = re.compile(r'<svg\b[^>]*\bviewBox="0 0 ([\d.]+) ([\d.]+)"[^>]*>')
_MK_PATH = re.compile(r'<path class="(mk-[a-z]+)"( style="[^"]*")? d="([^"]*)"/>')
_RING_OK = re.compile(r'^[MLZ\d\s.\-]*$')
_CLIP_MARGIN = 6.0  # px outside the viewBox, so the clip edge (and water's .75 stroke) is never visible


def _clip_ring(pts, x0, y0, x1, y1):
    """Sutherland–Hodgman against an axis-aligned rectangle. Winding (and even-odd parity) of every point inside the
    rectangle is unchanged, so fills render identically inside it."""
    for axis, lim, keep_ge in ((0, x0, True), (0, x1, False), (1, y0, True), (1, y1, False)):
        if not pts:
            break
        out = []
        prev = pts[-1]
        pin = (prev[axis] >= lim) if keep_ge else (prev[axis] <= lim)
        for cur in pts:
            cin = (cur[axis] >= lim) if keep_ge else (cur[axis] <= lim)
            if cin != pin:
                t = (lim - prev[axis]) / (cur[axis] - prev[axis])
                ix = prev[0] + t * (cur[0] - prev[0])
                iy = prev[1] + t * (cur[1] - prev[1])
                out.append((lim, iy) if axis == 0 else (ix, lim))
            if cin:
                out.append(cur)
            prev, pin = cur, cin
        pts = out
    return pts


def _fmt(v):
    s = '%.1f' % v
    s = s[:-2] if s.endswith('.0') else s
    return '0' if s == '-0' else s


def _clip_d(d, w, h):
    if not _RING_OK.match(d):
        return d  # arcs/curves: leave untouched
    x0, y0, x1, y1 = -_CLIP_MARGIN, -_CLIP_MARGIN, w + _CLIP_MARGIN, h + _CLIP_MARGIN
    rings = []
    for chunk in d.split('M')[1:]:
        nums = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', chunk)]
        pts = list(zip(nums[0::2], nums[1::2]))
        if len(pts) < 3:
            continue
        if all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in pts):
            rings.append('M' + chunk.strip())
            continue
        c = _clip_ring(pts, x0, y0, x1, y1)
        dedup = []
        for p in c:
            q = (_fmt(p[0]), _fmt(p[1]))
            if not dedup or dedup[-1] != q:
                dedup.append(q)
        if len(dedup) > 1 and dedup[0] == dedup[-1]:
            dedup.pop()
        if len(dedup) < 3:
            continue
        area = sum(float(a[0]) * float(b[1]) - float(b[0]) * float(a[1]) for a, b in zip(dedup, dedup[1:] + dedup[:1]))
        if abs(area) < 1.0:
            continue
        rings.append('M' + 'L'.join('%s %s' % q for q in dedup) + 'Z')
    return ''.join(rings)


def _clip_seg(p, q, x0, y0, x1, y1):
    """Liang–Barsky: the part of segment p→q inside the rectangle, or None."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pp == 0:
            if qq < 0:
                return None
            continue
        r = qq / pp
        if pp < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return None
    a = p if t0 == 0 else (p[0] + t0 * dx, p[1] + t0 * dy)
    b = q if t1 == 1 else (p[0] + t1 * dx, p[1] + t1 * dy)
    return a, b, t0 == 0, t1 == 1


def _clip_line_d(d, w, h, margin=10.0):
    """Open polylines (rivers, the faint other-day tracks): keep only the pieces inside the frame (+ margin, so the
    new line ends and their round caps stay out of sight)."""
    if not _RING_OK.match(d):
        return d
    x0, y0, x1, y1 = -margin, -margin, w + margin, h + margin
    out = []
    for chunk in d.split('M')[1:]:
        nums = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', chunk)]
        pts = list(zip(nums[0::2], nums[1::2]))
        if 'Z' in chunk and pts:
            pts.append(pts[0])
        if len(pts) < 2:
            continue
        if all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in pts):
            out.append('M' + chunk.strip())
            continue
        cur = None
        for p, q in zip(pts, pts[1:]):
            c = _clip_seg(p, q, x0, y0, x1, y1)
            if not c:
                cur = None
                continue
            a, b, a_kept, b_kept = c
            if cur is None or not a_kept:
                cur = [a]
                out.append(cur)
            cur.append(b)
            if not b_kept:
                cur = None
    res = []
    for sub in out:
        if isinstance(sub, str):
            res.append(sub)
            continue
        q = []
        for p in sub:
            f = (_fmt(p[0]), _fmt(p[1]))
            if not q or q[-1] != f:
                q.append(f)
        if len(q) >= 2:
            res.append('M' + 'L'.join('%s %s' % f for f in q))
    return ''.join(res)


def _slim_path(pm, w, h):
    cls, style, d = pm.group(1), pm.group(2) or '', pm.group(3)
    if cls in ('mk-glacier', 'mk-water') and not style:
        nd = _clip_d(d, w, h)
    elif (cls == 'mk-river' and not style) or (cls == 'mk-trk' and 'stroke-opacity: .35' in style and 'dasharray' not in style):
        nd = _clip_line_d(d, w, h)  # solid strokes only: clipping would shift a dash pattern's phase
    else:
        return pm.group(0)
    return ('<path class="%s"%s d="%s"/>' % (cls, style, nd)) if nd else ''


def slim(fragment_html):
    """Clip glacier and lake fills, rivers and the faint other-day tracks to each map's viewBox. The rendered overlays
    carry whole features that run far outside the frame (about 3 MB on Chamonix–Zermatt); only what can show is kept,
    so the map looks the same."""
    out, pos = [], 0
    for m in _SVG_OPEN.finditer(fragment_html):
        if m.start() < pos:
            continue
        end = fragment_html.find('</svg>', m.end())
        if end < 0:
            break
        w, h = float(m.group(1)), float(m.group(2))

        out.append(fragment_html[pos:m.end()])
        out.append(_MK_PATH.sub(lambda pm, w=w, h=h: _slim_path(pm, w, h), fragment_html[m.end():end]))
        pos = end
    out.append(fragment_html[pos:])
    return ''.join(out)


def spark(t, here, d):
    """Both sparkline states; CSS shows the route-red one on the current nav item."""
    return ('<span class="mul-sp" aria-hidden="true"><span class="sp-n">%s</span><span class="sp-c">%s</span></span>'
            % (core.frag(core.rendered(t, 'spark-%s.svg.html' % d['id']), t['url']),
               core.frag(core.rendered(t, 'spark-%s-cur.svg.html' % d['id']), t['url'])))


# ---------------------------------------------------------------- trip strip

def strip(t):
    """Five cells as on the design: total distance, longest day, total gain, GPS max, moving (days · hut nights under it).
    Phones show the 2×2 of totals; the longest day is dropped there."""
    st = t['stats']
    cells = []
    mi, km = core.dist_vals(st.get('distance_km'))
    if mi:
        cells.append(('Total distance', U(mi, km, 'mi', 'km'), U_sub(mi, km, 'MI', 'KM'), ''))
    longest = max((d for d in t['days'] if d['stats'].get('distance_km') is not None),
                  key=lambda d: d['stats']['distance_km'], default=None)
    if longest and len(t['days']) > 1:
        lmi, lkm = core.dist_vals(longest['stats']['distance_km'])
        cells.append(('Longest day', U(lmi, lkm, 'mi', 'km'), nb([U_sub(lmi, lkm, 'MI', 'KM'), 'DAY %d' % longest['n']]), 'mul-sc-long'))
    if st.get('gain_m') is not None:
        g = st['gain_m']
        cells.append(('Total gain', U(n(g * FT), n(g), 'ft', 'm'), U_sub(n(g * FT), n(g), 'FT', 'M'), ''))
    if st.get('high_m') is not None:
        h = st['high_m']
        hd = high_day(t)
        sub = nb([U_sub(n(h * FT), n(h), 'FT', 'M'), ('DAY %d' % hd['n']) if hd else ''])
        cells.append(('GPS max', U(n(h * FT), n(h), 'ft', 'm'), sub, ''))
    if st.get('moving_s'):
        cells.append(('Moving', '%s<span class="unit">h:mm</span>' % core.hm(st['moving_s']), nb(days_meta(t, True)), ''))
    out = ''.join('<div class="strip-c%s"><dt class="t-label">%s</dt><dd class="t-data-xl strip-v">%s</dd>%s</div>'
                  % ((' ' + cls) if cls else '', lab, core.dx(val), ('<dd class="t-mono-s strip-s">%s</dd>' % sub) if sub else '')
                  for lab, val, sub, cls in cells)
    long_ = ' mul-strip--long' if any(c[3] for c in cells) else ''
    return '<dl class="strip mul-strip%s" style="--cells:%d" aria-label="Trip stats">%s</dl>' % (long_, len(cells), out)


def stats_note(cls=''):
    """The one stats footnote (under the strip; phones show the rep-note-ph copy under the overview map caption instead).
    Plural: a multi-day trip is one recording per day."""
    return ('<p class="strip-note%s">Stats from the Garmin recordings via Strava. '
            'GPS max is the highest point in the GPX files, not a surveyed summit height.</p>' % ((' ' + cls) if cls else ''))


# ---------------------------------------------------------------- overview map

OVERVIEW_VARIANTS = [('overview-wide', 'wide'), ('overview-col', 'col'), ('overview-phone', 'phone')]


def gpx_all(t):
    """The combined all-days GPX (one <trk> per day) that build.py writes beside the page."""
    return t['slug'] + '.gpx'


def overview_map(t, here, meta):
    maps = meta.get('maps', {})
    desk = key_items(t, ['overview-wide', 'overview-col'], 'Route by day')
    phone = key_items(t, ['overview-phone'])
    cls = 'map--report' + ('' if 'overview-wide' in maps else ' map--nowide')
    first = ['Track: Garmin, %s' % core.frange(t['date'], t['end_date']), 'full track, not trimmed · North up']
    cap = ('<div class="mapcap"><p class="mapcap-t"><span>%s</span><span class="mul-cap2">%s</span></p>'
           '<div class="mapcap-a"><a class="btn" href="%s" download>%sDownload all GPX</a></div></div>'
           % (nb(first), nb(['Terrain: AWS Terrain Tiles · Map data © OpenStreetMap contributors', 'Not for navigation']),
              gpx_all(t), icon('download', 18)))
    mp = slim(core.map_block(t, here, OVERVIEW_VARIANTS, t['url'] + 'map/', 'ov', eager=True, cls=cls))
    hd = high_day(t)
    if hd and hd['n'] != len(t['days']):
        # the renderer merges 'END' into a GPS-max label near a day's end; on the trip overview that reads as the
        # finish of the whole route, which it is not when the high point came before the last day
        mp = mp.replace('>END · GPS MAX ', '>GPS MAX ')
    return ('<section class="rep-map mul-map" id="map" aria-label="Route map, all days"><div class="bleed">%s</div>'
            '<div class="wrap">%s%s%s</div></section>'
            % (mp, core.key_rows(desk, phone), cap, stats_note('rep-note-ph')))


# ---------------------------------------------------------------- sticky day nav

def day_nav(t, here):
    days = t['days']
    items = ['<a class="mul-dn-i mul-dn-ov" href="#overview" data-day="overview" aria-current="location">'
             '<span class="mul-dn-top"><span class="mul-dn-d">D1–D%d</span></span>'
             '<span class="mul-dn-date">Overview</span><span class="mul-dn-dist">%s</span></a>'
             % (len(days), caps_dist(t['stats'].get('distance_km')))]
    for d in days:
        dd = d['date']
        items.append('<a class="mul-dn-i mul-dn-day" href="#day-%d" data-day="%d">'
                     '<span class="mul-dn-top"><span class="mul-dn-d">D%d</span>%s</span>'
                     '<span class="mul-dn-date"><span class="mul-dlong">%s</span><span class="mul-dshort">%s</span></span>'
                     '<span class="mul-dn-dist">%s</span></a>'
                     % (d['n'], d['n'], d['n'], spark(t, here, d),
                        core.fdate(dd, 'day') if dd else '', ('%s %d' % (dd.strftime('%b'), dd.day)) if dd else '',
                        caps_dist(d['stats'].get('distance_km'))))
    return '<nav class="mul-dnav" aria-label="Days"><div class="mul-dn-in">%s</div></nav>' % ''.join(items)


# ---------------------------------------------------------------- stitched profile

_BAND = re.compile(r'<text class="pf-ax" x="([\d.]+)" y="12" '
                   r'style="text-anchor: middle; fill: #[0-9A-F]{6}(; font-weight: 600)?">([^<]*)</text>')


def unclash_band(svg):
    """Drop a TRANSFER label in the day band when it would overlap a day label (narrow phone render); the dashed
    divider stays, and the transfer is named in the map key and the day chapter."""
    labs = [(float(m.group(1)), m.group(3), m) for m in _BAND.finditer(svg)]
    days = [(x, len(txt)) for x, txt, _ in labs if txt != 'TRANSFER']
    for x, txt, m in labs:
        if txt != 'TRANSFER':
            continue
        half = len(txt) * 6.7 / 2 + 3
        if any(abs(x - dx) < half + dl * 7.0 / 2 for dx, dl in days):
            svg = svg.replace(m.group(0), '', 1)
    return svg


_TICK = re.compile(r'<text class="pf-ax" x="([\d.]+)" y="([\d.]+)" style="text-anchor: (start|middle|end)">(\d+)( mi)?</text>')


def _thin_one(svg):
    labs = [m for m in _TICK.finditer(svg) if float(m.group(2)) > 20]
    if len(labs) < 3:
        return svg
    y = max(float(m.group(2)) for m in labs)
    labs = [m for m in labs if float(m.group(2)) == y]

    def span(m):
        x, w = float(m.group(1)), len(m.group(4) + (m.group(5) or '')) * 6.7
        return {'start': (x, x + w), 'middle': (x - w / 2, x + w / 2), 'end': (x - w, x)}[m.group(3)]
    for step in (1, 2, 4, 5, 10, 20, 25, 50, 100):
        keep = [m for m in labs if int(m.group(4)) % step == 0]
        if all(span(b)[0] - span(a)[1] >= 6 for a, b in zip(keep, keep[1:])):
            break
    drop = [m for m in labs if m not in keep]
    for m in drop:
        svg = svg.replace(m.group(0), '', 1)
    return svg


def thin_ticks(chart_html):
    """Drop distance tick labels that would touch their neighbours ('13' '14' on a 14-mile day in the 358px phone
    render) by labelling every 2nd/5th… mile instead; tick marks stay."""
    out, pos = [], 0
    while True:
        a = chart_html.find('<svg', pos)
        if a < 0:
            break
        b = chart_html.find('</svg>', a)
        if b < 0:
            break
        out.append(chart_html[pos:a])
        out.append(_thin_one(chart_html[a:b]))
        pos = b
    out.append(chart_html[pos:])
    return ''.join(out)


def per_variant(chart_html, sizes, fn):
    """Apply fn to each chart variant slice (<div class="cv cv--SIZE">…</div>) whose size is in sizes, one SVG at a time."""
    parts = re.split(r'(?=<div class="cv cv--)', chart_html)
    out = []
    for p in parts:
        m = re.match(r'<div class="cv cv--([a-z]+)"', p)
        out.append(fn(p) if (m and m.group(1) in sizes) else p)
    return ''.join(out)


PROFILE_VARIANTS = [('profile-wide', 'wide'), ('profile-col', 'col'), ('profile-phone', 'phone')]


def stitched_profile(t, here, meta):
    ch = meta.get('charts', {})
    p = ch.get('profile-wide') or ch.get('profile-col')
    if not p:
        return ''
    st = t['stats']
    hi = st.get('high_m') if st.get('high_m') is not None else p['gps_max_ft'] / FT
    lo = st.get('low_m') if st.get('low_m') is not None else p['min_ft'] / FT
    hd = high_day(t)
    bits = ['GPS MAX %s%s' % (caps_elev(hi), (' (DAY %d)' % hd['n']) if hd else ''), 'MIN %s' % caps_elev(lo)]
    vx = core.vx_line(ch, PROFILE_VARIANTS)
    if vx:
        bits.append(vx)
    # wide ≥1200, the 718 col render 560–1199, phone below: each has its own vertical exaggeration (vx_line matches it)
    chart = core.chart_block(t, here, PROFILE_VARIANTS, 'sp', cls='mul-stitch')
    chart = per_variant(chart, ('col', 'phone'), unclash_band)
    chart = thin_ticks(chart)
    return ('<section class="wrap mul-prof" aria-labelledby="prof-h"><div class="rep-prof-h"><h2 class="t-label" id="prof-h">Elevation</h2>'
            '<p class="t-mono-s">%s</p></div>%s</section>' % (nb(bits), chart))


# ---------------------------------------------------------------- overview: stage table + phone day index

def stage_table(t, here):
    days = t['days']
    has_route = any(day_title(d) for d in days)
    unit = lambda a, b: '<span class="u"><span class="u-mi">%s</span><span class="u-km">%s</span></span>' % (a, b)  # noqa: E731
    head = ['<th scope="col" class="c-day">Day</th>', '<th scope="col" class="c-date">Date</th>']
    if has_route:
        head.append('<th scope="col" class="c-route">From → To</th>')
    head += ['<th scope="col" class="num c-dist">Dist %s</th>' % unit('mi', 'km'),
             '<th scope="col" class="num c-gain">Gain %s</th>' % unit('ft', 'm'),
             '<th scope="col" class="num c-loss">Loss %s</th>' % unit('ft', 'm'),
             '<th scope="col" class="num c-high">GPS max %s</th>' % unit('ft', 'm'),
             '<th scope="col" class="num c-time">Moving h:mm</th>',
             '<th scope="col" class="c-gpx">GPX</th>']
    rows = []
    for d in days:
        st = d['stats']
        mi, km = core.dist_vals(st.get('distance_km'))
        date_caps = core.fdate(d['date'], 'day').upper() if d['date'] else ''
        xfer = ('<span class="mul-tag" title="Road transfer before this day">Transfer<span class="sr"> before this day</span></span>'
                if d.get('transfer_before') else '')
        cells = ['<th scope="row" class="c-day"><a href="#day-%d">D%d</a></th>' % (d['n'], d['n'])]
        if has_route:
            cells.append('<td class="c-date t-mono-s">%s</td>' % date_caps)
            title = day_title(d) or 'Day %d' % d['n']
            cells.append('<td class="c-route"><span class="mul-st-r"><a href="#day-%d">%s</a>%s</span>'
                         '<span class="mul-st-sub t-mono-s">%s</span></td>' % (d['n'], arrow_html(title), xfer, date_caps))
        else:
            cells.append('<td class="c-date c-date--link t-mono-s"><span class="mul-st-r"><a href="#day-%d">%s</a>%s</span></td>'
                         % (d['n'], date_caps, xfer))
        g = gpx_href(t, d)
        cells += ['<td class="num c-dist">%s</td>' % (U(mi, km) if mi else '—'),
                  '<td class="num c-gain">%s</td>' % elev_cell(st.get('gain_m')),
                  '<td class="num c-loss">%s</td>' % elev_cell(st.get('loss_m')),
                  '<td class="num c-high">%s</td>' % elev_cell(st.get('high_m')),
                  '<td class="num c-time">%s</td>' % (core.hm(st['moving_s']) if st.get('moving_s') else '—'),
                  '<td class="c-gpx">%s</td>' % (('<a class="mul-dl-btn" href="%s" download aria-label="Download Day %d GPX">%s</a>'
                                                  % (g, d['n'], icon('download', 20))) if g else '')]
        rows.append('<tr>%s</tr>' % ''.join(cells))
    st = t['stats']
    mi, km = core.dist_vals(st.get('distance_km'))
    foot = ['<th scope="row" class="c-day">Total</th>', '<td class="c-date"></td>']
    if has_route:
        foot.append('<td class="c-route">%s</td>' % arrow_html(route_ends(days)))
    foot += ['<td class="num c-dist">%s</td>' % (U(mi, km) if mi else '—'),
             '<td class="num c-gain">%s</td>' % elev_cell(st.get('gain_m')),
             '<td class="num c-loss">%s</td>' % elev_cell(st.get('loss_m')),
             '<td class="num c-high">%s</td>' % elev_cell(st.get('high_m')),
             '<td class="num c-time">%s</td>' % (core.hm(st['moving_s']) if st.get('moving_s') else '—'),
             '<td class="c-gpx"></td>']
    return ('<table class="mul-st%s" id="stages"><caption class="sr">Stages, one row per day, with a GPX download for each day</caption>'
            '<thead><tr>%s</tr></thead><tbody>%s</tbody><tfoot><tr>%s</tr></tfoot></table>'
            % ('' if has_route else ' mul-st--noroute', ''.join(head), ''.join(rows), ''.join(foot)))


def day_index(t, here):
    """Phone replacement for the stage table: one 72px row per day with its sparkline."""
    out = []
    for d in t['days']:
        st = d['stats']
        bits = []
        if st.get('distance_km') is not None:
            bits.append(caps_dist(st['distance_km']))
        if st.get('gain_m') is not None:
            bits.append(caps_elev(st['gain_m'], ' GAIN'))
        title = day_title(d)
        out.append('<li><a href="#day-%d"><span class="mul-di-b"><span class="mul-di-t"><span class="mul-di-d">D%d</span>'
                   '<span class="mul-di-date">%s</span></span>%s<span class="t-mono-s mul-di-m">%s</span></span>%s%s</a></li>'
                   % (d['n'], d['n'], core.fdate(d['date'], 'day') if d['date'] else 'Day %d' % d['n'],
                      ('<span class="mul-di-r">%s</span>' % arrow_html(title)) if title else '', ' · '.join(bits),
                      '<span class="mul-sp mul-sp--96" aria-hidden="true">%s</span>'
                      % core.frag(core.rendered(t, 'spark-%s.svg.html' % d['id']), here), icon('chevron-right', 20)))
    return '<ol class="mul-di" aria-label="Days">%s</ol>' % ''.join(out)


def overview(t, here):
    prose = ('<div class="prose t-body mul-ov-p">%s</div>' % markdown.to_html(t['body_md'])) if t['body_md'] else ''
    return ('<section class="wrap mul-ov" id="overview" aria-labelledby="overview-h">'
            '<div class="shead"><h2 class="shead-t" id="overview-h">Overview</h2><span class="shead-m t-mono-s">%s</span></div>'
            '%s%s%s</section>' % (days_meta(t), prose, stage_table(t, here), day_index(t, here)))


# ---------------------------------------------------------------- day chapters

def rail_stats(d):
    st = d['stats']
    rows = []
    mi, km = core.dist_vals(st.get('distance_km'))
    if mi:
        rows.append(('Distance', U(mi, km, 'mi', 'km'), U_sub(mi, km, 'MI', 'KM'), ''))
    for key, lab, cls in (('gain_m', 'Gain', ''), ('loss_m', 'Loss', 'mul-ds-loss'), ('high_m', 'GPS max', '')):
        v = st.get(key)
        if v is not None:
            rows.append((lab, U(n(v * FT), n(v), 'ft', 'm'), U_sub(n(v * FT), n(v), 'FT', 'M'), cls))
    if st.get('moving_s'):
        rows.append(('Moving', '%s<span class="unit">h:mm</span>' % core.hm(st['moving_s']),
                     ('START ' + core.ftime(d['start_time'])) if d.get('start_time') else '', ''))
    out, i = [], 0
    for lab, val, sub, cls in rows:
        if cls != 'mul-ds-loss':  # position in the phone 2×2 grid
            cls = (cls + ' ' if cls else '') + ('pc-r' if i % 2 else 'pc-l') + (' pc-t' if i < 2 else '')
            i += 1
        out.append('<div class="mul-ds-r %s"><dt class="t-label">%s</dt><dd><span class="mul-ds-v">%s</span>%s</dd></div>'
                   % (cls, lab, val, ('<span class="t-mono-s mul-ds-s">%s</span>' % sub) if sub else ''))
    return ''.join(out)


def day_map_keys(t, d):
    return core.key_rows(key_items(t, ['day-%s-col' % d['id']]), key_items(t, ['day-%s-phone' % d['id']]))


def day_profile(t, here, meta, d):
    ch = meta.get('charts', {})
    col, ph = 'day-%s-profile-col' % d['id'], 'day-%s-profile-phone' % d['id']
    if col not in ch and ph not in ch:
        return ''
    st = d['stats']
    bits = []
    if st.get('distance_km') is not None:
        bits.append(caps_dist(st['distance_km']))
    if st.get('gain_m') is not None:
        bits.append(U('+%s FT' % n(st['gain_m'] * FT), '+%s M' % n(st['gain_m'])))
    if st.get('loss_m') is not None:
        bits.append(U('−%s FT' % n(st['loss_m'] * FT), '−%s M' % n(st['loss_m'])))
    vx = core.vx_line(ch, [(col, 'col'), (ph, 'phone')])  # chart--nowide: the col value also shows >= 1200
    if vx:
        bits.append(vx)
    keys = core.key_row(['hatch', 'fill'], 'keyrow--inline') if t['activity'] == 'ski' else ''
    return ('<div class="mul-dp"><div class="mul-dp-h"><p class="t-label">Elevation · Day %d</p>%s<p class="t-mono-s mul-dp-m">%s</p></div>%s</div>'
            % (d['n'], keys, nb(bits),
               thin_ticks(core.chart_block(t, here, [(col, 'col'), (ph, 'phone')], 'd%s' % d['id'], cls='chart--nowide'))))


def photo_rows(t, here, d):
    """Photos in rows that fill the column at one height per row (heights clamped in CSS, so pairs of portraits crop a
    little rather than run 900px tall). A photo alone keeps its own shape."""
    ps = [p for p in d['photos'] if p.get('file')]
    if not ps:
        return ''
    ar = [(p['w'] / float(p['h'])) if p.get('w') and p.get('h') else 1.5 for p in ps]
    rows, cur, tot = [], [], 0.0
    for p, a in zip(ps, ar):
        cur.append((p, a))
        tot += a
        if tot >= 1.9:
            rows.append((cur, tot))
            cur, tot = [], 0.0
    if cur:
        if rows and len(cur) == 1 and cur[0][1] < 1 and len(rows[-1][0]) < 3:
            prev, ptot = rows.pop()
            rows.append((prev + cur, ptot + tot))
        else:
            rows.append((cur, tot))
    out = []
    k = 0
    total = len(ps)
    for items, tot in rows:
        figs = []
        for p, a in items:
            k += 1
            img = core.photo(t, p, here, sizes='(min-width: 1200px) 620px, (min-width: 760px) 60vw, 100vw', caption=False)
            lab = ('%s (full size)' % esc(p['alt'])) if p.get('alt') else 'Photo %d of %d from Day %d, full size' % (k, total, d['n'])
            figs.append('<a class="mul-ph" href="%s%s" style="--ar:%.4f;--fg:%d" aria-label="%s">%s</a>'
                        % (link(here, t['url']), p['file'], a, round(a * 1000), lab, img))
        cls = 'mul-prow'
        if len(items) == 1:
            cls += ' mul-prow--one'
        elif all(a < 1 for _, a in items) and len(items) == 2:
            cls += ' mul-prow--pp'
        out.append('<div class="%s" style="--n:%d;--sum:%.4f;--ar:%.4f">%s</div>'
                   % (cls, len(items), tot, items[0][1], ''.join(figs)))
        caps = [p['caption'] for p, _ in items if p.get('caption')]
        if caps:  # captions sit under their row (rows have a fixed height)
            out.append('<p class="t-small mul-pcap">%s</p>' % ' · '.join(esc(c) for c in caps))
    return '<div class="mul-photos">%s</div>' % ''.join(out)


def pager_cell(x, cls):
    """A day in the chapter pager: its title (or its date when the day file has no title) and a caps meta line."""
    title = day_title(x)
    bits = []
    if title and x['date']:
        bits.append(core.fdate(x['date'], 'day').upper())
    if x['stats'].get('distance_km') is not None:
        bits.append(caps_dist(x['stats']['distance_km']))
    if not title and x['stats'].get('gain_m') is not None:
        bits.append(caps_elev(x['stats']['gain_m'], ' GAIN'))
    name = arrow_html(title) if title else (core.fdate(x['date'], 'day') if x['date'] else 'Day %d' % x['n'])
    arrow = icon('arrow-left' if cls == 'prev' else 'arrow-right', 14)
    lab = ('%s<span>Day %d</span>' % (arrow, x['n'])) if cls == 'prev' else ('<span>Day %d</span>%s' % (x['n'], arrow))
    return ('<a class="%s" href="#day-%d"><span class="pager-t"><span class="t-label pager-l">%s</span>'
            '<span class="pager-n">%s</span><span class="t-mono-s">%s</span></span></a>' % (cls, x['n'], lab, name, ' · '.join(bits)))


def overview_cell(t, cls):
    """Pager cell back to the top of the trip (first day: left; last day: right)."""
    up = icon('arrow-left', 14, 'mul-up')
    lab = ('%s<span>Overview</span>' % up) if cls == 'prev' else ('<span>Overview</span>%s' % up)
    return ('<a class="%s" href="#overview"><span class="pager-t"><span class="t-label pager-l">%s</span>'
            '<span class="pager-n">%s</span><span class="t-mono-s">%s · %s</span></span></a>'
            % (cls, lab, title_title(t), '%d DAYS' % len(t['days']), caps_dist(t['stats'].get('distance_km'))))


def day_pager(t, here, d):
    days = t['days']
    i = d['n'] - 1
    cells = [overview_cell(t, 'prev') if i == 0 else pager_cell(days[i - 1], 'prev')]
    if i + 1 < len(days):
        cells.append(pager_cell(days[i + 1], 'next'))
    elif i > 0:
        cells.append(overview_cell(t, 'next'))
    # a plain div, not a labelled nav: one pager per day would add a landmark per chapter (the day nav already is one).
    # Phones show only the next cell, as one 'Day N →' button (multiday.css).
    return '<div class="pager mul-dpager">%s</div>' % ''.join(cells)


def chapter(t, here, meta, d):
    k = d['n']
    title = day_title(d)
    date_s = core.fdate(d['date'], 'day') if d['date'] else ''
    if title:
        label = 'Day %d%s' % (k, (' · ' + date_s) if date_s else '')
        h3 = '<span class="sr">Day %d: </span>%s' % (k, arrow_html(title))
    elif date_s:  # untitled day file: the date names the day, as in the day nav and pagers
        label = 'Day %d' % k
        h3 = '<span class="sr">Day %d: </span>%s' % (k, esc(date_s))
    else:
        label = ''
        h3 = 'Day %d' % k
    hut = ''
    if d.get('hut'):
        hut = ('<p class="mul-hut"><svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><rect width="20" height="20"/>'
               '<text x="10" y="10.5">%d</text></svg>'
               '<span class="mul-hut-t"><span class="t-label">Night %d</span> <span>%s</span></span></p>'
               % (k, k, esc(d['hut'])))
    g = gpx_href(t, d)
    gpx = ('<a class="btn mul-dgpx" href="%s" download>%sDay %d GPX</a>' % (g, icon('download', 18), k)) if g else ''
    rail = ('<div class="mul-rail"><div class="mul-rail-h"><span class="mul-num" aria-hidden="true">%d</span>'
            '<div class="mul-rail-t">%s<h3 class="mul-dtitle" id="day-%d-h">%s</h3></div></div>'
            '%s<dl class="mul-ds" aria-label="Day %d stats">%s</dl>%s</div>'
            % (k, ('<p class="t-label mul-dlabel">%s</p>' % label) if label else '', k, h3, hut, k, rail_stats(d), gpx))
    ns = 'd%s' % d['id']
    mp = slim(core.map_block(t, here, [('day-%s-col' % d['id'], 'col'), ('day-%s-phone' % d['id'], 'phone')], t['url'] + 'map/', ns,
                             cls='map--nowide mul-dmap'))
    cap = '<p class="mul-dcap">%s</p>' % nb(['North up · Terrain: AWS Terrain Tiles',
                                             'Map data © OpenStreetMap contributors · Not for navigation'])
    xfer = ('<p class="mul-xfer"><svg width="16" height="10" viewBox="0 0 16 10" aria-hidden="true">%s</svg>Road transfer before this day</p>'
            % core.KEY_SYMBOLS['transfer'][1]) if d.get('transfer_before') else ''
    prose = ('<div class="prose t-body mul-prose">%s</div>' % markdown.to_html(d['body_md'], heading_shift=3)) if d['body_md'] else ''
    # the transfer note comes first: it happened before the day, so it reads before the day's map
    main = ('<div class="mul-main">%s<div class="mul-dmap-w">%s%s%s</div>%s%s</div>'
            % (xfer, mp, day_map_keys(t, d), cap, day_profile(t, here, meta, d), prose))
    return ('<section class="mul-day" data-day="%d" aria-labelledby="day-%d-h"><div class="wrap mul-day-in" id="day-%d">%s%s%s%s</div></section>'
            % (k, k, k, rail, main, photo_rows(t, here, d), day_pager(t, here, d)))


# ---------------------------------------------------------------- page

def first_photo(t):
    for d in t['days']:
        if d['photos']:
            return t['url'] + d['photos'][0]['file']
    return (t['url'] + t['photos'][0]['file']) if t['photos'] else None


def bottom_bar(t):
    """Phone bottom bar (< 760; CSS and the current-section scrollspy are shared with single-day reports in report.css /
    base.js): Map · Days · Report (the first day with a write-up, when there is one) · GPX (all days)."""
    items = [('#map', 'map', 'Map', ''), ('#overview', 'list', 'Days', '')]
    rd = next((d for d in t['days'] if d['body_md']), None)
    if rd:
        items.append(('#day-%d' % rd['n'], 'report', 'Report', ''))
    items.append((gpx_all(t), 'download', 'GPX', ' download'))
    return ('<nav class="bbar" aria-label="Trip sections" style="--n:%d">%s</nav>'
            % (len(items), ''.join('<a href="%s"%s>%s<span>%s</span></a>' % (h, dl, icon(ic, 24), lab) for h, ic, lab, dl in items)))


def description(t, limit=160):
    """Meta description: the factual summary; 'Day N: <excerpt>' of the first written day only if it all fits in limit."""
    desc = core.summary(t)
    d = next((d for d in t['days'] if d['body_md']), None)
    if d:
        lead = ' Day %d: ' % d['n']
        room = limit - 1 - len(desc) - len(lead)
        if room >= 40:
            desc += lead + markdown.plain(d['body_md'], room)
    return desc


def page(t, site):
    here = t['url']
    meta = core.render_meta(t)
    actions = ('<a class="btn" href="#day-1">%sDay by day</a><a class="btn btn--ink" href="%s" download>%sDownload all GPX</a>'
               % (icon('list', 18), gpx_all(t), icon('download', 18)))
    body = [report.title_block(t, here, actions),
            '<div class="wrap rep-strip" id="stats">%s%s</div>' % (strip(t), stats_note()),
            overview_map(t, here, meta)]
    chapters = ''.join(chapter(t, here, meta, d) for d in t['days'])
    body.append('<div class="mul-body">%s%s%s<section class="mul-days" aria-labelledby="days-h">'
                 '<h2 class="sr" id="days-h">Day by day</h2>%s</section></div>'
                 % (day_nav(t, here), stitched_profile(t, here, meta), overview(t, here), chapters))
    body.append(report.pager(t, here, site))
    head = core.map_preloads(t, here, OVERVIEW_VARIANTS, t['url'] + 'map/', nowide='overview-wide' not in meta.get('maps', {}))
    return core.Page(here, core.document(here, t['title'], ''.join(body), description(t), active=t['activity'], image=first_photo(t),
                                         extra_head=head, body_cls='p-multiday', bottom=bottom_bar(t), og_type='article'),
                     t['title'])


def build(site):
    return [page(t, site) for t in site['trips'] if t['kind'] == 'multi-day' and t['days']]
