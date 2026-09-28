"""Map, profile and glyph renderers for the Datum mockups.

Maps = hillshade/band PNG (uploaded asset) + SVG overlay fragment (classes styled by MAP_CSS).
"""
import bisect
import json
import math
import os
import re
import zlib

import geo
from geo import FT, MI, Proj
from icons import icon_inner

SP = geo.SP
# output dirs; tools/render.py points these at rendered/<slug>/ before each call
FRAG = os.path.join(geo.ROOT, '.cache', 'frag')
MAPPNG = FRAG
os.makedirs(FRAG, exist_ok=True)
os.makedirs(MAPPNG, exist_ok=True)

CAT = {'SKI': '#4A8CCD', 'HIK': '#69883C', 'OTH': '#1C7D78', 'MTB': '#845011', 'CLM': '#70355E'}
ROUTE = '#D2381A'
DEFAULT_TRIM = False  # tracks are published in full; set True to cut 0.25 mi off each end on maps
ROUTE_INK = '#B8300F'
INK, INK2, INK3 = '#16171A', '#45474C', '#66686D'
MAPPAPER = '#EEECE6'

MONO = "'Geist Mono', ui-monospace, 'SF Mono', monospace"
SANS = "Archivo, 'Helvetica Neue', system-ui, sans-serif"
SERIF = "'Source Serif 4', Georgia, serif"

# Shared CSS for map/profile SVG internals (goes in each artboard's <helmet><style>)
MAP_CSS = """
.mk-min{fill:none;stroke:#CFCABD;stroke-width:.5}
.mk-idx{fill:none;stroke:#B3AD9F;stroke-width:.9}
.mk-cl{font:500 11px/1 %(mono)s;fill:#55524A;stroke:#EEECE6;stroke-width:3px;paint-order:stroke;stroke-linejoin:round}
.mk-water{fill:#D3DEE2;stroke:#9FB4BD;stroke-width:.75;fill-rule:evenodd}
.mk-glacier{fill:#E6ECEE;fill-opacity:.5;stroke:none;fill-rule:evenodd}
.mk-stream{fill:none;stroke:#9FB4BD;stroke-width:.6}
.mk-river{fill:none;stroke:#9FB4BD;stroke-width:1.2}
.mk-roadc{fill:none;stroke:#8C8A83;stroke-width:3.5;stroke-linecap:round;stroke-linejoin:round}
.mk-road{fill:none;stroke:#FFFFFF;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}
.mk-minorc{fill:none;stroke:#A6A298;stroke-width:2.2;stroke-linecap:round}
.mk-minor{fill:none;stroke:#FFFFFF;stroke-width:1.4;stroke-linecap:round}
.mk-trail{fill:none;stroke:#8F8A7E;stroke-width:.75;stroke-dasharray:3 2}
.mk-border{fill:none;stroke:#66686D;stroke-width:1;stroke-dasharray:8 3 2 3}
.mk-case{fill:none;stroke:#FFFFFF;stroke-linecap:round;stroke-linejoin:round}
.mk-trk{fill:none;stroke-linecap:round;stroke-linejoin:round}
.mk-skin{fill:none;stroke:#FFFFFF;stroke-width:1;stroke-dasharray:1 4;stroke-linecap:round}
.mk-ghost{fill:none;stroke:#66686D;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.mk-chev{fill:none;stroke:#FFFFFF;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
.mk-peak{font:600 12px/1 %(sans)s;letter-spacing:.12em;text-transform:uppercase;fill:#45474C;stroke:#EEECE6;stroke-width:3px;paint-order:stroke;stroke-linejoin:round}
.mk-place{font:500 12px/1 %(sans)s;fill:#45474C;stroke:#EEECE6;stroke-width:3px;paint-order:stroke;stroke-linejoin:round}
.mk-wl{font:italic 400 14px/1 %(serif)s;fill:#3F6272;stroke:#D3DEE2;stroke-width:3px;paint-order:stroke;stroke-linejoin:round}
.mk-wlw{font:italic 400 16px/1 %(serif)s;letter-spacing:.2em;fill:#3F6272}
.mk-rl{font:500 11px/1 %(mono)s;fill:#45474C;stroke:#EEECE6;stroke-width:3px;paint-order:stroke;stroke-linejoin:round}
.mk-lbl{font:500 11px/1 %(mono)s;fill:#66686D;stroke:#EEECE6;stroke-width:3px;paint-order:stroke;stroke-linejoin:round}
.mk-gps{font:500 11px/1 %(mono)s;letter-spacing:.02em;fill:#B8300F;stroke:#EEECE6;stroke-width:3.5px;paint-order:stroke;stroke-linejoin:round}
.mk-num{font:500 11px/1 %(mono)s;fill:#16171A;text-anchor:middle;dominant-baseline:central}
.mk-numw{font:500 12px/1 %(mono)s;fill:#F2F1EC;text-anchor:middle;dominant-baseline:central}
.mk-day{font:600 11px/1 %(mono)s;fill:#FFFFFF;text-anchor:middle;dominant-baseline:central}
.mk-hut{font:600 12px/1 %(sans)s;fill:#16171A;stroke:#EEECE6;stroke-width:3px;paint-order:stroke;stroke-linejoin:round}
.mk-tri{fill:#45474C}
.pf-grid{fill:none;stroke:#DEDBD2;stroke-width:1}
.pf-fill{fill:#E2DFD6}
.pf-ax{font:400 11px/1 %(mono)s;fill:#66686D}
.pf-axk{fill:none;stroke:#8C8A83;stroke-width:1}
.pf-line{fill:none;stroke-width:2;stroke-linejoin:round}
.pf-ghost{fill:none;stroke:#66686D;stroke-width:1.5;stroke-linejoin:round}
.pf-div{fill:none;stroke:#16171A;stroke-width:1}
.pf-g0{fill:#F2F1EC;stroke:#8C8A83;stroke-width:1}
.pf-g1{fill:#8C8A83}
.pf-g3{fill:#16171A}
.gl-case{fill:none;stroke:#FFFFFF;stroke-linecap:round;stroke-linejoin:round}
.gl-trk{fill:none;stroke-linecap:round;stroke-linejoin:round}
.mk-ph .mk-lbl,.mk-ph .mk-gps,.mk-ph .mk-num,.mk-ph .mk-rl,.mk-ph .mk-day,.mk-ph .mk-cl{font-size:12px}
.pf-ph .pf-ax{font-size:12.1px}
""" % {'mono': MONO, 'sans': SANS, 'serif': SERIF}


AX_HALO = 'stroke: #F2F1EC; stroke-width: 3px; paint-order: stroke; stroke-linejoin: round'  # phone y-axis labels over the plot


def _base_css():
    keep = ('.mk-min', '.mk-idx', '.mk-water', '.mk-glacier', '.mk-stream', '.mk-river', '.mk-roadc', '.mk-road', '.mk-minorc', '.mk-minor', '.mk-trail', '.mk-border')
    return ''.join(l.strip() for l in MAP_CSS.split('\n') if l.strip().startswith(keep) and '%(' not in l)


BASE_CSS = _base_css()

_ATTR_RE = re.compile(r'<(text|tspan|path|rect|circle|g)\b([^>]*?)(/?)>')


def fix_attrs(svg):
    """Move hyphenated presentation attrs (text-anchor, dominant-baseline) into style for React safety."""
    def rep(m):
        tag, attrs, sl = m.group(1), m.group(2), m.group(3)
        moved = []
        for a in ('text-anchor', 'dominant-baseline'):
            mm = re.search(r'\s%s="([^"]*)"' % a, attrs)
            if mm:
                moved.append('%s: %s' % (a, mm.group(1)))
                attrs = attrs[:mm.start()] + attrs[mm.end():]
        if not moved:
            return m.group(0)
        sm = re.search(r'\sstyle="([^"]*)"', attrs)
        if sm:
            st = sm.group(1).rstrip('; ')
            attrs = attrs[:sm.start()] + ' style="%s; %s"' % (st, '; '.join(moved)) + attrs[sm.end():]
        else:
            attrs += ' style="%s"' % '; '.join(moved)
        return '<%s%s%s>' % (tag, attrs, sl)
    return _ATTR_RE.sub(rep, svg)


def write_frag(name, svg):
    svg = fix_attrs(svg)
    with open(os.path.join(FRAG, name + '.svg.html'), 'w') as fh:
        fh.write(svg)
    return svg


def fmt_int(v):
    return '{:,}'.format(int(round(v)))


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            .replace('{{', '{ {'))


def D(pts, closed=False):
    """Path data as every mapkit writer emits it: relative ('M x y l dx dy …'), 0.1 px, no drift (geo.d_attr rel=True)."""
    return geo.d_attr(pts, closed, rel=True)


def u_span(mi_txt, km_txt):
    """Unit-switched text for the MI|KM toggle (base.css hides .u-mi / .u-km): two tspans inside one <text>."""
    return '<tspan class="u-mi">%s</tspan><tspan class="u-km">%s</tspan>' % (mi_txt, km_txt)


def km_label(km_len):
    """Scale-bar / axis wording for a metric length: under 1 km in metres ('250 m'), else km ('2 km')."""
    return ('%d m' % round(km_len * 1000)) if km_len < 1 else ('%g km' % km_len)


# ---------------------------------------------------------------- track processing
def smooth_ele(pts, cd, window=60.0):
    """Distance-window median then mean of elevations; returns list (None-safe)."""
    eles = [p[2] for p in pts]
    if all(e is None for e in eles):
        return eles
    last = next(e for e in eles if e is not None)
    filled = []
    for e in eles:
        if e is not None:
            last = e
        filled.append(last)
    n = len(pts)
    out = [0.0] * n
    j0 = j1 = 0
    for i in range(n):
        while cd[i] - cd[j0] > window / 2:
            j0 += 1
        while j1 + 1 < n and cd[j1 + 1] - cd[i] <= window / 2:
            j1 += 1
        seg = sorted(filled[j0:j1 + 1])
        out[i] = seg[len(seg) // 2]
    # light mean pass
    out2 = [0.0] * n
    j0 = j1 = 0
    s = 0.0
    for i in range(n):
        while cd[i] - cd[j0] > 20:
            j0 += 1
        while j1 + 1 < n and cd[j1 + 1] - cd[i] <= 20:
            j1 += 1
        out2[i] = sum(out[j0:j1 + 1]) / (j1 - j0 + 1)
    return out2


def turning_segments(cd, ele, hyst=25.0):
    """Split into monotone-ish segments using hysteresis; returns list of (i0, i1, 'up'|'down')."""
    n = len(ele)
    if n < 2:
        return []
    segs = []
    start = 0
    direction = None
    ext_i = 0
    for i in range(1, n):
        if direction in (None, 'up'):
            if ele[i] > ele[ext_i] or direction is None and ele[i] >= ele[ext_i]:
                if direction is None and ele[i] - ele[start] > hyst:
                    direction = 'up'
                if direction == 'up':
                    ext_i = i
                elif ele[i] > ele[ext_i]:
                    ext_i = i
            if direction is None and ele[start] - ele[i] > hyst:
                direction = 'down'
                ext_i = i
                continue
            if direction == 'up' and ele[ext_i] - ele[i] > hyst:
                segs.append((start, ext_i, 'up'))
                start = ext_i
                direction = 'down'
                ext_i = i
        elif direction == 'down':
            if ele[i] < ele[ext_i]:
                ext_i = i
            if ele[i] - ele[ext_i] > hyst:
                segs.append((start, ext_i, 'down'))
                start = ext_i
                direction = 'up'
                ext_i = i
    segs.append((start, n - 1, direction or 'up'))
    # merge tiny
    return [s for s in segs if s[1] > s[0]]


def decimate(pts, n_target=1200):
    if len(pts) <= n_target:
        return pts
    step = len(pts) / n_target
    idx = sorted(set([int(i * step) for i in range(n_target)] + [len(pts) - 1]))
    return [pts[i] for i in idx]


def trim(pts, cd, meters):
    total = cd[-1]
    i0 = next((i for i, d in enumerate(cd) if d >= meters), 0)
    i1 = max(i for i, d in enumerate(cd) if d <= total - meters) if total > 2 * meters else len(cd) - 1
    return i0, i1


def along(pts_xy, cd, target):
    """Point & heading at distance target along a polyline (xy with cumulative real distances)."""
    for i in range(1, len(cd)):
        if cd[i] >= target:
            t = (target - cd[i - 1]) / max(cd[i] - cd[i - 1], 1e-9)
            x = pts_xy[i - 1][0] + t * (pts_xy[i][0] - pts_xy[i - 1][0])
            y = pts_xy[i - 1][1] + t * (pts_xy[i][1] - pts_xy[i - 1][1])
            # heading over a short window
            j0 = max(0, i - 3)
            j1 = min(len(pts_xy) - 1, i + 3)
            ang = math.atan2(pts_xy[j1][1] - pts_xy[j0][1], pts_xy[j1][0] - pts_xy[j0][0])
            return x, y, ang
    return pts_xy[-1][0], pts_xy[-1][1], 0.0


class Track:
    def __init__(self, pts, key='', cat='SKI'):
        self.raw = [p for p in pts if p[0] is not None]
        self.key = key
        self.cat = cat
        self.cd = geo.cumdist(self.raw)
        self.total = self.cd[-1] if self.cd else 0
        self.ele = smooth_ele(self.raw, self.cd) if self.raw and any(p[2] is not None for p in self.raw) else None
        if self.ele:
            self.imax = max(range(len(self.ele)), key=lambda i: self.raw[i][2] if self.raw[i][2] is not None else -1e9)
        else:
            self.imax = None

    @property
    def gps_max_m(self):
        lab = getattr(self, 'label_max_m', None)
        if lab:
            return lab
        return self.raw[self.imax][2] if self.imax is not None else None


def is_out_and_back(tr, radius=80.0, frac=0.6):
    """True when the return leg (after the farthest point from the start) mostly retraces the outbound leg."""
    pts = tr.raw
    if len(pts) < 20:
        return False
    s0 = pts[0]
    far = max(range(len(pts)), key=lambda i_: geo.hav(s0, pts[i_]))
    first, second = pts[:far + 1:2], pts[far::3]
    if len(first) < 5 or len(second) < 5:
        return False
    kx = geo.M_PER_DEG_LON_EQ * math.cos(math.radians(s0[0]))
    ky = geo.M_PER_DEG_LAT
    grid = {}
    for p_ in first:
        grid.setdefault((int(p_[1] * kx // radius), int(p_[0] * ky // radius)), []).append((p_[1] * kx, p_[0] * ky))
    hit = 0
    for p_ in second:
        x_, y_ = p_[1] * kx, p_[0] * ky
        gx_, gy_ = int(x_ // radius), int(y_ // radius)
        if any((a_ - x_) ** 2 + (b_ - y_) ** 2 <= radius * radius
               for dx_ in (-1, 0, 1) for dy_ in (-1, 0, 1) for a_, b_ in grid.get((gx_ + dx_, gy_ + dy_), ())):
            hit += 1
    return hit / len(second) >= frac


# ---------------------------------------------------------------- map rendering
def offset_line(xy, d):
    """Offset a polyline by d px along its left normal (averaged direction)."""
    out = []
    n = len(xy)
    for i in range(n):
        a = xy[max(0, i - 1)]
        b = xy[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        out.append((xy[i][0] - dy / L * d, xy[i][1] + dx / L * d))
    return out


def label_box(x, y, w, h):
    return (x, y, x + w, y + h)


def overlaps(b, boxes, pad=3):
    for c in boxes:
        if not (b[2] + pad < c[0] or c[2] + pad < b[0] or b[3] + pad < c[1] or c[3] + pad < b[1]):
            return True
    return False


def text_w(s, px, spacing=0.0, mono=False):
    per = 0.6 if mono else (0.7 if s.isupper() else 0.58)
    return len(s) * px * per + max(0, len(s) - 1) * spacing * px


def render_hillshade(proj, name, scale, bands, exaggeration=1.0, zoom=None, ocean=False, flat=False):
    """Write palette PNG at scale× resolution. bands: 3 thresholds (m) for band tints."""
    W, H = int(round(proj.w * scale)), int(round(proj.h * scale))
    step = 1.0 / scale
    grid, nx, ny, x0, y0 = geo.dem_grid(proj, step, zoom=zoom, margin=0)
    grid = geo.blur(grid, 1)
    cell_m = proj.m_per_px * step
    band_cols = [(0xEE, 0xEC, 0xE6)] * 4 if flat else [(0xEE, 0xEC, 0xE6), (0xE7, 0xE4, 0xDC), (0xDF, 0xDB, 0xD0), (0xD8, 0xD3, 0xC7)]
    NS = 40
    palette = []
    for b in band_cols:
        for s in range(NS):
            t = s / (NS - 1)  # 0 = deep shadow, 1 = full light
            # shade factor: shadow darkens to 74%, light brightens by 5%
            f = 0.74 + 0.31 * t
            palette.append(tuple(max(0, min(255, int(round(c * f)))) for c in b))
    zen = math.radians(45)
    az = math.radians(315)
    palette.append((0xD3, 0xDE, 0xE2))
    water_i = len(palette) - 1
    idx = bytearray(W * H)
    for j in range(H):
        jj = min(max(j, 1), ny - 2)
        for i in range(W):
            ii = min(max(i, 1), nx - 2)
            dzdx = (grid[jj][ii + 1] - grid[jj][ii - 1]) / (2 * cell_m) * exaggeration
            dzdy = (grid[jj + 1][ii] - grid[jj - 1][ii]) / (2 * cell_m) * exaggeration
            slope = math.atan(math.hypot(dzdx, dzdy))
            aspect = math.atan2(dzdy, -dzdx)
            sh = math.cos(zen) * math.cos(slope) + math.sin(zen) * math.sin(slope) * math.cos(az - aspect)
            # normalise so flat ground ~ 0.8 light
            t = max(0.0, min(1.0, 0.8 + (sh - math.cos(zen)) * 1.1))
            e = grid[jj][ii]
            if e <= 0.5 and ocean:
                idx[j * W + i] = water_i
                continue
            b = 0 if e < bands[0] else (1 if e < bands[1] else (2 if e < bands[2] else 3))
            idx[j * W + i] = b * NS + int(round(t * (NS - 1)))
    p = os.path.join(MAPPNG, name + '.png')
    geo.png_write_palette(p, W, H, idx, palette)
    return p


def choose_interval(m_per_px, relief_m):
    ft_opts = [20, 40, 80, 100, 200, 400, 500, 1000, 2000]
    target_m = m_per_px * 6.0
    for f in ft_opts:
        if f / FT >= target_m:
            return f
    return ft_opts[-1]


def contours_svg(proj, interval_ft, index_every=5, step=2.0, zoom=None, labels=True, label_boxes=None,
                 avoid=None, grid_cache=None, min_len=18, eps=0.6, max_labels=3, minor_on=True):
    grid, nx, ny, x0, y0 = grid_cache or geo.dem_grid(proj, step, zoom=zoom, margin=step * 2)
    grid = geo.blur(grid, 1)
    lo = min(min(r) for r in grid)
    hi = max(max(r) for r in grid)
    iv = interval_ft / FT
    first = math.ceil(lo / iv)
    last = math.floor(hi / iv)
    minor, index, lbl = [], [], []
    boxes = label_boxes if label_boxes is not None else []
    cands = []
    for k in range(first, last + 1):
        lev = k * iv
        is_idx = (k * interval_ft) % (interval_ft * index_every) == 0
        if not is_idx and not minor_on:
            continue
        for line in geo.contour_lines(grid, lev, x0, y0, step):
            if geo.path_len(line) < min_len:
                continue
            s_ = geo.rdp(line, eps)
            d = D(s_)
            (index if is_idx else minor).append(d)
            if is_idx and labels and geo.path_len(s_) > 220:
                cands.append((geo.path_len(s_), k, s_))
    # label the longest index contours first, within the budget
    cands.sort(key=lambda c: -c[0])
    for L, k, s_ in cands:
        if len(lbl) >= max_labels:
            break
        for frac in (0.4, 0.6, 0.25, 0.75):
            acc = 0
            placed = False
            for i in range(1, len(s_)):
                seg = math.hypot(s_[i][0] - s_[i - 1][0], s_[i][1] - s_[i - 1][1])
                if acc + seg >= frac * L:
                    x = (s_[i][0] + s_[i - 1][0]) / 2
                    y = (s_[i][1] + s_[i - 1][1]) / 2
                    ang = math.degrees(math.atan2(s_[i][1] - s_[i - 1][1], s_[i][0] - s_[i - 1][0]))
                    if ang > 90:
                        ang -= 180
                    if ang < -90:
                        ang += 180
                    if abs(ang) > 45:
                        break
                    txt = fmt_int(k * interval_ft)
                    tw = text_w(txt, 11, mono=True) + 4
                    a = math.radians(ang)
                    bw = tw * abs(math.cos(a)) + 16 * abs(math.sin(a))
                    bh = tw * abs(math.sin(a)) + 16 * abs(math.cos(a))
                    b = (x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2)
                    if 30 < x < proj.w - 30 and 20 < y < proj.h - 20 and not overlaps(b, boxes, 10) and \
                            not (avoid and avoid(x, y, 26)):
                        boxes.append(b)
                        lbl.append('<text class="mk-cl" x="%.1f" y="%.1f" text-anchor="middle" dominant-baseline="central" '
                                   'transform="rotate(%.1f %.1f %.1f)">%s</text>' % (x, y, ang, x, y, txt))
                        placed = True
                    break
                acc += seg
            if placed:
                break
    out = []
    if minor:
        out.append('<path class="mk-min" d="%s"/>' % ''.join(minor))
    if index:
        out.append('<path class="mk-idx" d="%s"/>' % ''.join(index))
    return out, lbl, (lo, hi)


CLIP_MARGIN = 8


def clip_ring(pts, x0, y0, x1, y1):
    """Sutherland–Hodgman: clip a closed ring to a rectangle (fills only; clip edges fall outside the viewBox)."""
    def clip(poly, inside, cross):
        out = []
        for i, cur in enumerate(poly):
            prev = poly[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
        return out

    def xcut(xv):
        return lambda a, b: (xv, a[1] + (b[1] - a[1]) * (xv - a[0]) / ((b[0] - a[0]) or 1e-9))

    def ycut(yv):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yv - a[1]) / ((b[1] - a[1]) or 1e-9), yv)
    poly = list(pts)
    for inside, cross in ((lambda p: p[0] >= x0, xcut(x0)), (lambda p: p[0] <= x1, xcut(x1)),
                          (lambda p: p[1] >= y0, ycut(y0)), (lambda p: p[1] <= y1, ycut(y1))):
        if not poly:
            break
        poly = clip(poly, inside, cross)
    return poly


def clip_runs(xy, w, h, m=CLIP_MARGIN):
    """Split a polyline into the runs that lie inside the frame (plus one point either side)."""
    runs, cur = [], []
    for i, (x_, y_) in enumerate(xy):
        if -m <= x_ <= w + m and -m <= y_ <= h + m:
            if not cur and i > 0:
                cur.append(xy[i - 1])
            cur.append((x_, y_))
        elif cur:
            cur.append((x_, y_))
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) >= 2]


GAP_M = 2000.0  # consecutive fixes farther apart than this are a recording gap, drawn as a gap
TRAIL_NEAR_M = 2000.0  # OSM trails are drawn only this close to a track
BASE_GZ_KB_PHONE, BASE_GZ_KB = 40, 80  # base-layer budgets (gzipped): phone renders / desktop and wide renders
# peak-name spots around its triangle (dx, baseline dy, anchor): E, W, NE, NW, SE, SW, N, S
PEAK_SPOTS = ((8, 4, 'start'), (-8, 4, 'end'), (6, -8, 'start'), (-6, -8, 'end'), (6, 16, 'start'), (-6, 16, 'end'),
              (0, -9, 'middle'), (0, 18, 'middle'))


MIN_RUN_M = 60.0  # a piece left between two recording gaps that is shorter than this is noise, not a route: dropped


def gap_ranges(cd, n=None):
    """Index ranges [a, b) of a track split wherever consecutive fixes are more than GAP_M apart. When the track does
    split, pieces shorter than MIN_RUN_M are dropped (the longest piece always stays); pieces of < 2 points never draw."""
    n = len(cd) if n is None else min(n, len(cd))
    runs, a = [], 0
    for i in range(1, n):
        if cd[i] - cd[i - 1] > GAP_M:
            runs.append((a, i))
            a = i
    runs.append((a, n))
    runs = [(a_, b_) for a_, b_ in runs if b_ - a_ >= 2]
    if len(runs) > 1:
        def ln(r):
            return cd[r[1] - 1] - cd[r[0]]
        longest = max(runs, key=ln)
        runs = [r for r in runs if r is longest or ln(r) >= MIN_RUN_M]
    return runs


def gap_split(xy, cd):
    """Split a projected polyline into runs wherever the fixes behind it are more than GAP_M apart (cd: cumulative
    metres per point, same length as xy), so a lost signal or a skipped stretch stays a gap, not a straight line."""
    return [xy[a:b] for a, b in gap_ranges(cd, len(xy))]


TRACK_EPS = 0.4  # every track / casing run is simplified to at least this many output px before it is written


def runs_d(xy, cd, eps):
    return ''.join(D(geo.rdp(r, max(eps, TRACK_EPS))) for r in gap_split(xy, cd))


def poly_d(proj, rings, eps=0.4, min_area=0.0, frame=None):
    parts = []
    for r in rings:
        pts = [proj.xy(a, b) for a, b in r]
        if min_area and ring_area_px(pts) < min_area:
            continue
        if frame:
            fw, fh = frame
            xs = [p_[0] for p_ in pts]
            ys = [p_[1] for p_ in pts]
            if max(xs) < -CLIP_MARGIN or min(xs) > fw + CLIP_MARGIN or max(ys) < -CLIP_MARGIN or min(ys) > fh + CLIP_MARGIN:
                continue
            if min(xs) < -CLIP_MARGIN or max(xs) > fw + CLIP_MARGIN or min(ys) < -CLIP_MARGIN or max(ys) > fh + CLIP_MARGIN:
                pts = clip_ring(pts, -CLIP_MARGIN, -CLIP_MARGIN, fw + CLIP_MARGIN, fh + CLIP_MARGIN)
        pts = geo.rdp(pts, eps)
        if len(pts) >= 3:
            parts.append(D(pts, closed=True))
    return ''.join(parts)


def point_in_ring(pt, ring):
    x, y = pt
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-9) + x1:
            inside = not inside
    return inside


def ring_area_px(pts):
    a = 0
    for i in range(len(pts)):
        x1, y1 = pts[i - 1]
        x2, y2 = pts[i]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def track_avoid_fn(xy_list, markers):
    def avoid(x, y, r):
        for (px, py) in markers:
            if math.hypot(px - x, py - y) < r + 10:
                return True
        for xy in xy_list:
            for k in range(0, len(xy), 3):
                if abs(xy[k][0] - x) < r and abs(xy[k][1] - y) < r:
                    return True
        return False
    return avoid


def join_ways(ways):
    """Open OSM ways ([(lat, lon)…]) joined end to end wherever two share an endpoint (at a junction of three or more,
    any one continues the line). Same points, fewer subpaths."""
    ways = [list(w_) for w_ in ways if len(w_) >= 2]
    ends = {}
    for i, w_ in enumerate(ways):
        ends.setdefault(w_[0], []).append(i)
        ends.setdefault(w_[-1], []).append(i)
    used = [False] * len(ways)
    out = []

    def take(pt, cur_i):
        for j in ends.get(pt, ()):
            if not used[j] and j != cur_i:
                return j
        return None
    for i in range(len(ways)):
        if used[i]:
            continue
        used[i] = True
        line = list(ways[i])
        for forward in (True, False):
            while True:
                pt = line[-1] if forward else line[0]
                j = take(pt, None)
                if j is None:
                    break
                used[j] = True
                wj = ways[j] if ways[j][0] == pt else ways[j][::-1]  # oriented to start at the shared point
                if forward:
                    line += wj[1:]
                else:
                    line = wj[::-1][:-1] + line
        out.append(line)
    return out


LAST_OSM = {}


def render_map(spec):
    """spec keys: name, w, h, tracks:[{track, style, cat, i0,i1, pin, highlight, day}], bbox?, pad, detail,
    osm: detail level or None, legend, scale, north, graticule, miles, chevrons, startend, gpsmax, waypoints,
    skin, huts, png_scale, hillshade, peaks_max, day_labels, contour_labels, trim_m, pins, aria"""
    name = spec['name']
    w, h = spec['w'], spec['h']
    trks = spec['tracks']
    trim_m = spec.get('trim_m', 0.25 * MI)
    if spec.get('skin') and any(t.get('style', 'route') == 'route' and getattr(t['track'], 'cat', 'SKI') != 'SKI' for t in trks):
        # skin (ascent, dashed) / ski (descent, solid) styling means skis: a climb, hike or raft drawn this way is keyed
        # as SKIN / SKI on its page
        print('  ! %s: skin styling requested for a non-ski track (%s)' % (name, ', '.join(sorted({t['track'].cat for t in trks}))))
    # geometry per track
    all_pts = []
    for t in trks:
        tr = t['track']
        if 'i0' not in t:
            if t.get('trim', spec.get('trim', DEFAULT_TRIM)) and tr.total > 4 * trim_m:
                t['i0'], t['i1'] = trim(tr.raw, tr.cd, trim_m)
            else:
                t['i0'], t['i1'] = 0, len(tr.raw) - 1
        all_pts.append([(p[0], p[1]) for p in tr.raw[t['i0']:t['i1'] + 1]])
    if spec.get('pins'):
        all_pts.append([(pn['lat'], pn['lon']) for pn in spec['pins']])
    bbox = spec.get('bbox') or geo.bbox_of(all_pts)
    if spec.get('pad_bottom_px'):
        # extend the bbox southwards so the track clears the bottom band
        s0, w0, n0, e0 = bbox
        frac = spec['pad_bottom_px'] / float(h)
        bbox = (s0 - (n0 - s0) * frac / max(1e-6, 1 - frac), w0, n0, e0)
    proj = Proj(bbox, w, h, pad=spec.get('pad', 0.12))
    # ensure a minimum ground extent (for tiny tracks)
    min_m = spec.get('min_extent_m')
    if min_m and proj.m_per_px * min(w, h) < min_m:
        s, wv, n, e = bbox
        clat, clon = (s + n) / 2, (wv + e) / 2
        half_lat = min_m / 2 / geo.M_PER_DEG_LAT
        half_lon = min_m / 2 / (geo.M_PER_DEG_LON_EQ * math.cos(math.radians(clat)))
        proj = Proj((clat - half_lat, clon - half_lon, clat + half_lat, clon + half_lon), w, h, pad=0.0)
    meta = {'name': name, 'w': w, 'h': h, 'm_per_px': proj.m_per_px, 'bbox_frame': proj.bounds()}
    layers = {'base': [], 'water': [], 'contours': [], 'lines': [], 'track': [], 'markers': [], 'labels': [], 'pins': []}
    boxes = []  # label collision boxes
    tboxes = []  # text-label boxes only (peak names keep a wider berth from these, so each triangle sits by its own name)
    marker_pts = []
    # phone renders (390 wide, shown at ~360): small lettering is 12px, not 11 (the .mk-ph rules in MAP_CSS), pin hit r=24
    phone = spec.get('phone', name.endswith('-phone') or '-phone-' in name)
    fs_s = 12 if phone else 11
    EDGE = 12  # labels keep this far from the frame

    # project tracks (decimated) for drawing
    proj_tracks = []
    for t in trks:
        tr = t['track']
        seg = tr.raw[t['i0']:t['i1'] + 1]
        cds = tr.cd[t['i0']:t['i1'] + 1]
        xy = [proj.xy(p[0], p[1]) for p in seg]
        proj_tracks.append((t, xy, cds, seg))
    if spec.get('min_track_px'):
        # a day whose whole track fits in a few pixels and is not joined to the day before or after (a town walk, a
        # side trip) draws as a stray speck: leave it out. Short days on the line stay, or the line would break; the
        # first and last days stay, they carry the overall start and end markers.
        for k, (t, xy, cds, seg) in enumerate(proj_tracks):
            if 0 < k < len(proj_tracks) - 1 and xy:
                xs_, ys_ = [q[0] for q in xy], [q[1] for q in xy]
                if max(max(xs_) - min(xs_), max(ys_) - min(ys_)) >= spec['min_track_px']:
                    continue
                prev_end, next_start = proj_tracks[k - 1][1][-1], proj_tracks[k + 1][1][0]
                joined = min(math.hypot(xy[0][0] - prev_end[0], xy[0][1] - prev_end[1]),
                             math.hypot(xy[-1][0] - next_start[0], xy[-1][1] - next_start[1])) <= spec['min_track_px']
                if not joined:
                    t['_skip'] = True
    avoid = track_avoid_fn([pt[1] for pt in proj_tracks], marker_pts)

    # furniture reserved up front (the scale bar is placed after markers, see below)
    furn = []
    if spec.get('north', True):
        furn.append((w - 56, 12, w - 12, 64))
    if spec.get('legend'):
        furn.append((12, h - spec.get('legend_h', 210), 12 + 260, h - 10))
    if spec.get('reserve'):
        furn += spec['reserve']
    boxes += furn
    trk_pts = [p for pt in proj_tracks for p in pt[1][::2]]
    # every drawn track except faded other-day ghosts: labels may sit on a ghost, never on a route
    solid_pts = [p for pt in proj_tracks if pt[0].get('style', 'route') != 'ghost' for p in pt[1][::2]]

    def hits_track(b, pad=3, pts=None):
        for x_, y_ in (trk_pts if pts is None else pts):
            if b[0] - pad <= x_ <= b[2] + pad and b[1] - pad <= y_ <= b[3] + pad:
                return True
        return False

    dense_trk = []
    for pt in proj_tracks:
        runs_ = gap_split(pt[1], pt[2])
        if spec.get('skin') and pt[0].get('style', 'route') == 'route' and not spec.get('small_markers') and pt[0]['track'].ele \
                and is_out_and_back(pt[0]['track']):
            # skin / ski legs of an out-and-back are drawn 4 px either side of the track: labels keep clear of both
            runs_ = runs_ + [offset_line(r_, d_) for r_ in runs_ for d_ in (-4, 4)]
        for xy_ in runs_:
            for (xa, ya), (xb, yb) in zip(xy_, xy_[1:]):
                n_ = max(1, int(math.hypot(xb - xa, yb - ya) / 3))
                dense_trk.extend((xa + (xb - xa) * k / n_, ya + (yb - ya) * k / n_) for k in range(n_))
            if xy_:
                dense_trk.append(xy_[-1])
    DC = 32.0  # grid index over the densified track: a box test visits only the cells it covers
    dense_grid = {}
    for x_, y_ in dense_trk:
        dense_grid.setdefault((int(x_ // DC), int(y_ // DC)), []).append((x_, y_))

    def hits_track_dense(b, pad=3):
        x0_, y0_, x1_, y1_ = b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad
        for cx_ in range(int(x0_ // DC), int(x1_ // DC) + 1):
            for cy_ in range(int(y0_ // DC), int(y1_ // DC) + 1):
                for x_, y_ in dense_grid.get((cx_, cy_), ()):
                    if x0_ <= x_ <= x1_ and y0_ <= y_ <= y1_:
                        return True
        return False

    def in_frame(b, m=EDGE):
        return b[0] >= m and b[2] <= w - m and b[1] >= m and b[3] <= h - m

    def free(b, pad=2, track=True):
        """track: True = clear of every track, 'solid' = may overlap ghost tracks only, False = tracks ignored."""
        if overlaps(b, boxes, pad) or not in_frame(b):
            return False
        if track == 'solid':
            return not hits_track(b, 3, solid_pts)
        return not (track and hits_track(b))

    # hillshade png
    if spec.get('hillshade', True) and os.environ.get('REUSE_PNG') and os.path.exists(os.path.join(MAPPNG, name + '.png')):
        meta['png'] = name + '.png'
    elif spec.get('hillshade', True):
        lo_hi = spec.get('bands')
        if not lo_hi:
            # sample relief for band thresholds
            samp = []
            for j in range(0, h + 1, max(8, h // 30)):
                for i in range(0, w + 1, max(8, w // 40)):
                    samp.append((i, j))
            dem = geo.DEM(geo.pick_zoom(proj.latc, proj.m_per_px))
            vals = sorted(v for v in (dem.sample(*proj.ll(i, j)) for i, j in samp) if (v > 1 or not spec.get('ocean')))
            lo, hi = vals[int(len(vals) * 0.05)], vals[int(len(vals) * 0.98)]
            bands = [lo + (hi - lo) * f for f in (0.35, 0.6, 0.82)]
        else:
            bands = lo_hi
        render_hillshade(proj, name, spec.get('png_scale', 1.5), bands, exaggeration=spec.get('exaggeration', 1.0),
                         zoom=spec.get('hs_zoom'), ocean=spec.get('ocean', False), flat=spec.get('bands_off', False))
        meta['png'] = name + '.png'

    # OSM
    osm = spec.get('osm_data')
    if osm is None and spec.get('osm_from'):
        osm = LAST_OSM.get(spec['osm_from'])
    if osm is None and spec.get('osm'):
        b = proj.bounds(margin=30)
        try:
            osm = geo.osm_layers(b, spec['osm'])
        except Exception as ex:
            print('OSM failed for', name, ex)
            osm = None
    if osm:
        LAST_OSM[name] = osm
        peps = spec.get('poly_eps', 0.4)
        pmin = spec.get('min_water_px', 25)
        for outer, inner, tags in geo.osm_polys(osm, 'natural', 'glacier'):
            d = poly_d(proj, outer + inner, peps, pmin, frame=(w, h))
            if d:
                layers['water'].append('<path class="mk-glacier" d="%s"/>' % d)
        water_named = []
        for outer, inner, tags in geo.osm_polys(osm, 'natural', 'water'):
            rings_xy = [[proj.xy(a, b) for a, b in r] for r in outer]
            if not rings_xy or not any(geo.clip_poly_to_frame(r, w, h) for r in rings_xy):
                continue
            area = sum(ring_area_px(r) for r in rings_xy)
            if area < spec.get('min_water_px', 25):
                continue
            d = poly_d(proj, outer + inner, peps, pmin * 0.5, frame=(w, h))
            if d:
                layers['water'].append('<path class="mk-water" d="%s"/>' % d)
            if tags.get('name'):
                water_named.append((area, rings_xy, tags['name']))
        if spec.get('osm') == 'report':
            for pts, tags in geo.osm_lines(osm, lambda t: t.get('waterway') in ('river', 'stream')):
                cls = 'mk-river' if tags.get('waterway') == 'river' else 'mk-stream'
                d = ''.join(D(geo.rdp(r, 0.5)) for r in clip_runs([proj.xy(a, b) for a, b in pts], w, h))
                if d:
                    layers['water'].append('<path class="%s" d="%s"/>' % (cls, d))
        else:
            for pts, tags in geo.osm_lines(osm, lambda t: t.get('waterway') == 'river'):
                runs = [geo.rdp(r, max(0.7, peps)) for r in clip_runs([proj.xy(a, b) for a, b in pts], w, h)]
                runs = [r for r in runs if geo.path_len(r) > 30]
                if runs:
                    layers['water'].append('<path class="mk-river" d="%s"/>' % ''.join(D(r) for r in runs))
        # roads & trails
        road_lbls = []
        minors, majors, trails = [], [], []
        levels = spec.get('road_levels', ('motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'path', 'footway', 'track'))
        if phone:
            # phones: the main roads only (a street grid at 390 px is noise, and most of the base layer's weight)
            levels = tuple(l_ for l_ in levels if l_ in ('motorway', 'trunk', 'primary', 'path', 'footway', 'track'))
        reps = max(0.6, spec.get('poly_eps', 0.4))
        # trails are drawn only near the route (within TRAIL_NEAR_M): the rest of a trail network is weight, not context
        near_r = TRAIL_NEAR_M / proj.m_per_px
        near_cells = {}
        for pt_ in proj_tracks:
            for x_, y_ in pt_[1][::3]:
                near_cells.setdefault((int(x_ // near_r), int(y_ // near_r)), []).append((x_, y_))

        def near_track(x, y):
            cx_, cy_ = int(x // near_r), int(y // near_r)
            return any((a_ - x) ** 2 + (b_ - y) ** 2 <= near_r * near_r
                       for dx_ in (-1, 0, 1) for dy_ in (-1, 0, 1) for a_, b_ in near_cells.get((cx_ + dx_, cy_ + dy_), ()))
        groups_ = {'major': [], 'minor': [], 'trail': []}
        for pts, tags in geo.osm_lines(osm, lambda t: 'highway' in t):
            hw = tags['highway']
            if hw not in levels:
                continue
            is_trail = hw in ('path', 'footway', 'track')
            if is_trail and not spec.get('trails', True):
                continue
            grp = 'trail' if is_trail else ('major' if hw in ('motorway', 'trunk', 'primary', 'secondary') else
                                            ('minor' if hw in ('tertiary', 'unclassified') else None))
            if grp is None:
                continue
            groups_[grp].append(pts)
            ref = tags.get('ref') or ''
            if grp == 'major' and ref:
                runs = clip_runs([proj.xy(a_, b_) for a_, b_ in pts], w, h, 12)
                if runs:
                    road_lbls.append((geo.rdp(max(runs, key=len), reps), ref.replace(';', ' / ')))
        for grp, ways in groups_.items():
            is_trail = grp == 'trail'
            ds = []
            # OSM splits a road into many short ways: joined end to end first, each road is one subpath (fewer bytes, and
            # simplification runs over the whole line)
            for pts in join_ways(ways):
                raw_xy = [proj.xy(a_, b_) for a_, b_ in pts]
                runs, cur = [], []
                for x_, y_ in raw_xy:
                    if -12 <= x_ <= w + 12 and -12 <= y_ <= h + 12 and (not is_trail or near_track(x_, y_)):
                        cur.append((x_, y_))
                    else:
                        if cur:
                            cur.append((x_, y_))
                            runs.append(cur)
                        cur = []
                if cur:
                    runs.append(cur)
                runs = [geo.rdp(r, 0.5 if is_trail else reps) for r in runs if len(r) >= 2]
                ds += [D(r) for r in runs if geo.path_len(r) >= 1.5]  # a stub under 1.5 px only draws a blob
            {'major': majors, 'minor': minors, 'trail': trails}[grp].extend(ds)
        if trails:
            layers['lines'].append('<path class="mk-trail" d="%s"/>' % ''.join(trails))
        if minors:
            layers['lines'].append('<defs><path id="%s-rdm" d="%s"/></defs><use href="#%s-rdm" class="mk-minorc"/><use href="#%s-rdm" class="mk-minor"/>'
                                   % (name, ''.join(minors), name, name))
        if majors:
            layers['lines'].append('<defs><path id="%s-rdM" d="%s"/></defs><use href="#%s-rdM" class="mk-roadc"/><use href="#%s-rdM" class="mk-road"/>'
                                   % (name, ''.join(majors), name, name))
        meta['osm'] = True
    else:
        water_named, road_lbls = [], []

    # tracks
    total_mi = None
    small = spec.get('small_markers', False)
    # GPS-max points first so mile markers can keep clear of them
    gps_pts, gps_box0 = {}, {}
    for idx_t, (t, xy, cds, seg) in enumerate(proj_tracks):
        tr = t['track']
        if t.get('_skip'):
            continue
        if t.get('gpsmax', spec.get('gpsmax')) and t.get('style', 'route') == 'route' and tr.imax is not None:
            gps_pts[idx_t] = proj.xy(tr.raw[tr.imax][0], tr.raw[tr.imax][1])
            gx, gy = gps_pts[idx_t]
            gps_box0[idx_t] = (gx - 8, gy - 9, gx + 8, gy + 6)
            boxes.append(gps_box0[idx_t])
    # where the overall start disc / end square will be drawn (after the loop), for the GPS-max proximity test
    overall_ends = []
    if spec.get('overall_startend') and proj_tracks:
        overall_ends = [('START', proj_tracks[0][1][0], 0), ('END', proj_tracks[-1][1][-1], len(proj_tracks) - 1)]
    for idx_t, (t, xy, cds, seg) in enumerate(proj_tracks):
        if t.get('_skip'):
            continue
        style = t.get('style', 'route')
        eps_ = spec.get('track_eps', 0.35)
        d = runs_d(xy, cds, eps_)
        tr = t['track']
        oab = style == 'route' and is_out_and_back(tr)
        if style == 'route' and small and oab:
            far_i = max(range(len(xy)), key=lambda k: math.hypot(xy[k][0] - xy[0][0], xy[k][1] - xy[0][1]))
            out_leg = xy[:far_i + 1:max(1, (far_i + 1) // 400)]
            back = xy[far_i::max(1, (len(xy) - far_i) // 200)]
            dists = sorted(min(math.hypot(bx - ax, by - ay) for ax, ay in out_leg) for bx, by in back)
            if dists and dists[int(0.9 * (len(dists) - 1))] < 4:
                d = runs_d(xy[:far_i + 1], cds[:far_i + 1], spec.get('track_eps', 1.2))
        if style == 'route' and spec.get('skin') and tr.ele and not small:
            # skin (ascent) dashed thin, ski (descent) solid; out-and-back legs offset apart
            segs_ = turning_segments(tr.cd, tr.ele, 30)
            asc, desc = [], []
            for a, b, dirn in segs_:
                a2, b2 = max(a, t['i0']), min(b, t['i1'])
                if b2 - a2 < 2:
                    continue
                sub = [proj.xy(p_[0], p_[1]) for p_ in tr.raw[a2:b2 + 1]]
                for run in gap_split(sub, tr.cd[a2:b2 + 1]):
                    run = geo.rdp(run, 1.0 if oab else 0.5)
                    if oab:
                        run = offset_line(run, -4 if dirn == 'up' else 4)
                    (asc if dirn == 'up' else desc).append(D(run))
            wdt = t.get('width', 3)
            if desc:
                layers['track'].append('<path class="mk-case" style="stroke-width: %.1f" d="%s"/>' % (wdt + 4, ''.join(desc)))
            if asc:
                layers['track'].append('<path class="mk-case" style="stroke-width: 5" d="%s"/>' % ''.join(asc))
            if desc:
                layers['track'].append('<path class="mk-trk" style="stroke: {{route}}; stroke-width: %.1f" d="%s"/>' % (wdt, ''.join(desc)))
            if asc:
                layers['track'].append('<path class="mk-trk" style="stroke: {{route}}; stroke-width: 2; stroke-dasharray: 5 3; stroke-linecap: butt" d="%s"/>' % ''.join(asc))
        elif style == 'route':
            wdt = t.get('width', 3)
            layers['track'].append('<path class="mk-case" style="stroke-width: %.1f" d="%s"/>' % (wdt + (2 if small else 4), d))
            layers['track'].append('<path class="mk-trk" style="stroke: {{route}}; stroke-width: %.1f" d="%s"/>' % (wdt, d))
        elif style == 'ghost':
            gd = ''.join(D(r) for run in gap_split(xy, cds) for r in clip_runs(geo.rdp(run, max(eps_, TRACK_EPS)), w, h))
            if gd:
                layers['track'].insert(0, '<path class="mk-trk" style="stroke: {{route}}; stroke-opacity: .35; stroke-width: 2" d="%s"/>' % gd)
        elif style == 'cat':
            op = t.get('opacity', 1)
            wdt = t.get('width', 2.5)
            col = CAT[t.get('cat', 'SKI')]
            g_open = '<g class="mk-cat"%s style="opacity: %s">' % (' data-key="%s"' % esc(t['key']) if t.get('key') else '', op)
            tiny = spec.get('tiny_disc')
            if tiny and xy:
                xs_, ys_ = [q[0] for q in xy], [q[1] for q in xy]
                if math.hypot(max(xs_) - min(xs_), max(ys_) - min(ys_)) < 2.5 * tiny:
                    # a day that is a few pixels across (a crag, a lesson on one slope) reads as a spot, not a scribble
                    mx_, my_ = xy[len(xy) // 2]
                    layers['track'].append('%s<circle cx="%.1f" cy="%.1f" r="%g" style="fill: %s; stroke: #EEECE6; stroke-width: 1.5"/></g>'
                                           % (g_open, mx_, my_, tiny, col))
                    d = ''
            if not d:
                pass
            elif t.get('casing', True):
                # one geometry, drawn twice (casing + line) through <use>: the clone inherits each <use>'s class and style
                spec['_tk'] = spec.get('_tk', 0) + 1
                tid = 'tk-%d' % spec['_tk']
                layers['track'].append('%s<defs><path id="%s" d="%s"/></defs><use href="#%s" class="mk-case" style="stroke-width: %g"/>'
                                       '<use href="#%s" class="gl-trk" style="stroke: %s; stroke-width: %g"/></g>'
                                       % (g_open, tid, d, tid, wdt + 3, tid, col, wdt))
            else:
                layers['track'].append('%s<path class="gl-trk" style="stroke: %s; stroke-width: %g" d="%s"/></g>' % (g_open, col, wdt, d))
        elif style == 'planned':
            if t.get('thin'):
                # region / section maps: a light ink-3 dash that sits under the recorded tracks (KEY_SYMBOLS['planned_site'])
                cs_, ls_ = 'stroke-width: 3.5; stroke: #EEECE6', 'stroke: #66686D; stroke-width: 1.5; stroke-dasharray: 4 3; stroke-linecap: butt; stroke-linejoin: round'
            else:
                cs_, ls_ = 'stroke-width: 5.5; stroke: #EEECE6', 'stroke: #45474C; stroke-width: 2.5; stroke-dasharray: 8 5; stroke-linecap: butt; stroke-linejoin: round'
            if t.get('key'):
                # region / section maps: one geometry through <use> (the report's own map keeps <path class="mk-trk">)
                spec['_tk'] = spec.get('_tk', 0) + 1
                tid = 'tk-%d' % spec['_tk']
                pl = ('<defs><path id="%s" d="%s"/></defs><use href="#%s" class="mk-case" style="%s"/><use href="#%s" class="mk-trk" style="%s"/>'
                      % (tid, d, tid, cs_, tid, ls_))
            else:
                pl = '<path class="mk-case" style="%s" d="%s"/><path class="mk-trk" style="%s" d="%s"/>' % (cs_, d, ls_, d)
            if t.get('key'):
                pl = '<g class="mk-cat mk-planned" data-key="%s">%s</g>' % (esc(t['key']), pl)
            layers['track'].append(pl)
        # hut square first, so mile discs, the GPS-max triangle and every label already keep clear of it
        if t.get('hut_end'):
            ex, ey = xy[-1]
            hb = spec.setdefault('_hut_boxes', [])
            near = next((b_ for b_ in hb if math.hypot(b_['x'] - ex, b_['y'] - ey) < 22), None)
            if near:
                near['nums'].append(t['hut_end']['n'])
                txt = '·'.join(str(n_) for n_ in near['nums'])
                bw = text_w(txt, 11, mono=True) + 10
                near['hw'] = bw / 2
                layers['markers'][near['i']] = ('<rect x="%.1f" y="%.1f" width="%.1f" height="20" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 1.5; paint-order: stroke"/><text class="mk-day" x="%.1f" y="%.1f">%s</text>'
                                                % (near['x'] - bw / 2, near['y'] - 10, bw, near['x'], near['y'] + 0.5, txt))
                boxes.append((near['x'] - bw / 2 - 1, near['y'] - 11, near['x'] + bw / 2 + 1, near['y'] + 11))
            else:
                layers['markers'].append('<rect x="%.1f" y="%.1f" width="20" height="20" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 1.5; paint-order: stroke"/><text class="mk-day" x="%.1f" y="%.1f">%d</text>'
                                         % (ex - 10, ey - 10, ex, ey + 0.5, t['hut_end']['n']))
                hb.append({'x': ex, 'y': ey, 'nums': [t['hut_end']['n']], 'i': len(layers['markers']) - 1, 'hw': 10})
                boxes.append((ex - 11, ey - 11, ex + 11, ey + 11))
                marker_pts.append((ex, ey))
                if t['hut_end'].get('label'):
                    meta.setdefault('hut_labels', []).append((ex, ey, re.sub(r'\s+(CAS|CAF|SAC|CAI)$', '', t['hut_end']['label'])))
        # mile markers (outbound only on out-and-back tracks; clear of start/end and GPS max)
        if style == 'route' and spec.get('miles'):
            tot_mi = tr.total / MI
            total_mi = tot_mi
            every = 1 if tot_mi <= 15 else 2
            m = every
            limit = tr.total - 0.1 * MI
            if oab:
                far_i = max(range(len(tr.raw)), key=lambda k: geo.hav(tr.raw[0], tr.raw[k]))
                limit = tr.cd[far_i]
            meta['outbound_only'] = bool(oab)
            gpt = gps_pts.get(idx_t)
            placed_discs = []

            def blocked(x, y):
                if min(math.hypot(x - xy[0][0], y - xy[0][1]), math.hypot(x - xy[-1][0], y - xy[-1][1])) < 19:
                    return True
                if gpt and math.hypot(x - gpt[0], y - gpt[1]) < 22:
                    return True
                if any(math.hypot(x - a_, y - b_) < 22 for a_, b_ in placed_discs):
                    return True
                return overlaps((x - 10, y - 10, x + 10, y + 10), boxes, 1)

            def in_gap(tgt):
                # inside a recording gap (fixes > GAP_M apart): the map draws nothing there, so no disc either
                k_ = bisect.bisect_left(cds, tgt)
                return 0 < k_ < len(cds) and cds[k_] - cds[k_ - 1] > GAP_M
            while m * MI < limit:
                if cds[0] <= m * MI <= cds[-1] and in_gap(m * MI):
                    m += every  # the mile falls in a gap: try the next one
                    continue
                if cds[0] <= m * MI <= cds[-1]:
                    pos = None
                    for dm in (0, 0.05, -0.05, 0.1, -0.1, 0.15, -0.15, 0.2, -0.2, 0.25, -0.25):
                        tgt = (m + dm) * MI
                        if not (cds[0] <= tgt <= cds[-1]) or in_gap(tgt):
                            continue
                        x, y, ang = along(xy, cds, tgt)
                        if not blocked(x, y):
                            pos = (x, y)
                            break
                    if pos is None:
                        pos = along(xy, cds, m * MI)[:2]
                        # nowhere clear: still mark the mile unless the disc would sit on another marker (a lap of the
                        # same loop, the start/end pair, the GPS max), where it would hide both
                        px_, py_ = pos
                        if (gpt and math.hypot(px_ - gpt[0], py_ - gpt[1]) < 22) or \
                                any(math.hypot(px_ - a_, py_ - b_) < 21 for a_, b_ in placed_discs) or \
                                min(math.hypot(px_ - xy[0][0], py_ - xy[0][1]), math.hypot(px_ - xy[-1][0], py_ - xy[-1][1])) < 19:
                            m += every
                            continue
                    x, y = pos
                    placed_discs.append((x, y))
                    marker_pts.append((x, y))
                    layers['markers'].append('<g class="mk-mile"><circle cx="%.1f" cy="%.1f" r="10" style="fill: #FFFFFF; stroke: #16171A; stroke-width: 1"/>'
                                             '<text class="mk-num" x="%.1f" y="%.1f">%d</text></g>' % (x, y, x, y + 0.5, m))
                    boxes.append((x - 11, y - 11, x + 11, y + 11))
                m += every
        if style == 'route' and spec.get('chevrons') and not oab:
            m = 0.5
            while m * MI < tr.total:
                if cds[0] + 60 <= m * MI <= cds[-1] - 60:
                    x, y, ang = along(xy, cds, m * MI)
                    a = math.degrees(ang)
                    layers['track'].append('<path class="mk-chev" transform="translate(%.1f %.1f) rotate(%.1f)" d="M-2.5 -3.5L1.5 0L-2.5 3.5"/>' % (x, y, a))
                m += 1.0 if (tr.total / MI) <= 15 else 2.0
        ends_here = [(tag_, p_) for tag_, p_, k_ in overall_ends if k_ == idx_t]
        if spec.get('startend') and style in ('route', 'planned'):
            sx, sy = xy[0]
            ex, ey = xy[-1]
            if math.hypot(sx - ex, sy - ey) < 24:
                cx_, cy_ = (sx + ex) / 2, (sy + ey) / 2
                off_ = 6 if small else 8
                sx, sy, ex, ey = cx_ - off_, cy_, cx_ + off_, cy_
            if small:
                layers['markers'].append('<rect x="%.1f" y="%.1f" width="10" height="10" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 2; paint-order: stroke"/>' % (ex - 5, ey - 5))
                layers['markers'].append('<circle cx="%.1f" cy="%.1f" r="5" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 2; paint-order: stroke"/>' % (sx, sy))
            else:
                layers['markers'].append('<rect x="%.1f" y="%.1f" width="14" height="14" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 3; paint-order: stroke"/>' % (ex - 7, ey - 7))
                layers['markers'].append('<circle cx="%.1f" cy="%.1f" r="7" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 3; paint-order: stroke"/>' % (sx, sy))
            marker_pts += [(sx, sy), (ex, ey)]
            boxes += [(sx - 10, sy - 10, sx + 10, sy + 10), (ex - 10, ey - 10, ex + 10, ey + 10)]
            meta['start_xy'], meta['end_xy'] = (sx, sy), (ex, ey)
            ends_here = [('START', (sx, sy)), ('END', (ex, ey))]
        if idx_t in gps_pts:
            gx, gy = gps_pts[idx_t]
            at_start = None
            hut_near = next((b_ for b_ in spec.get('_hut_boxes', []) if math.hypot(b_['x'] - gx, b_['y'] - gy) < 22), None)
            near_end = [(math.hypot(gx - p_[0], gy - p_[1]), tag_, p_) for tag_, p_ in ends_here]
            near_end = sorted(z_ for z_ in near_end if z_[0] < 22)
            if hut_near or near_end:
                boxes.remove(gps_box0[idx_t])  # the triangle moves: free its first spot for day labels
            if hut_near:
                # the high point is at a hut: the triangle sits just right of the hut square, never under it
                gx, gy = hut_near['x'] + hut_near.get('hw', 10) + 10, hut_near['y']
            elif near_end:
                # beside the start disc / end square (right of the rightmost marker of a side-by-side pair)
                mx_ = max(p_[0] for _, p_ in ends_here if math.hypot(p_[0] - near_end[0][2][0], p_[1] - near_end[0][2][1]) < 30)
                gx, gy = mx_ + (11 if small else 13), near_end[0][2][1]
                if not (t.get('hut_end') or t.get('day_label')):
                    at_start = near_end[0][1]
            layers['markers'].append('<path d="M%.1f %.1fl6 10h-12z" style="fill: {{route}}; stroke: #FFFFFF; stroke-width: 1.5; paint-order: stroke"/>' % (gx, gy - 6))
            marker_pts.append((gx, gy))
            boxes.append((gx - 7, gy - 7, gx + 7, gy + 5))
            meta['gpsmax_xy'] = (gx, gy)
            summit = None
            if osm and not at_start:
                glat, glon = tr.raw[tr.imax][0], tr.raw[tr.imax][1]
                best_pk = best_prio = None
                prio_names = set(spec.get('priority_peaks') or [])
                for (plat, plon), ptags in geo.osm_nodes(osm, lambda t_: t_.get('natural') == 'peak' and t_.get('name')):
                    dd = geo.hav((glat, glon), (plat, plon))
                    if ptags['name'] in prio_names and dd < 400 and (best_prio is None or dd < best_prio[0]):
                        best_prio = (dd, ptags['name'])
                    if dd < 250 and (best_pk is None or dd < best_pk[0]):
                        best_pk = (dd, ptags['name'])
                best_pk = best_prio or best_pk
                if best_pk:
                    summit = best_pk[1]
            gl = spec.get('gps_label', True)

            def place_label(bw_, top_, bot_, cands_, optional=False):
                """Compass spots around the triangle first (N, NE, E, SE, S, SW, W, NW at 10 px, then 18, then 28), then the
                older hand-tuned spots (cands_), each clear of labels, markers and every track pixel (the box inflated by
                2 px against the densified track); then (unless optional: None) the spot clear of labels and markers that
                covers the least track; then just inside the frame and clear of reserved furniture.
                Offsets are (dx, dy, anchor), dy = baseline."""
                def box_(dx, dy, anchor):
                    bx = gx + dx if anchor == 'start' else (gx + dx - bw_ if anchor == 'end' else gx - bw_ / 2)
                    return (bx - 2, gy + dy - top_, bx + bw_ + 2, gy + dy + bot_)
                dy_c = -1 - (bot_ - top_) / 2.0  # baseline that centres the block on the triangle
                compass = []
                for d_ in (10, 18, 28):
                    k_ = 0.7 * d_
                    compass += [(0, -d_ - bot_, 'middle'), (k_, -k_ - bot_, 'start'), (d_, dy_c, 'start'), (k_, k_ + top_, 'start'),
                                (0, d_ + top_, 'middle'), (-k_, k_ + top_, 'end'), (-d_, dy_c, 'end'), (-k_, -k_ - bot_, 'end')]
                every_ = compass + list(cands_)
                for dx, dy, anchor in every_:
                    b = box_(dx, dy, anchor)
                    if not overlaps(b, boxes, 2) and in_frame(b) and not hits_track_dense((b[0], b[1] - 2, b[2], b[3] + 2), 0):
                        return dx, dy, anchor, b
                if optional:
                    return None
                best_ = None
                for k_, (dx, dy, anchor) in enumerate(every_):
                    b = box_(dx, dy, anchor)
                    if free(b, 2, track=False):
                        n_ = sum(1 for x_, y_ in dense_trk if b[0] - 2 <= x_ <= b[2] + 2 and b[1] - 2 <= y_ <= b[3] + 2)
                        if best_ is None or (n_, k_) < best_[0]:
                            best_ = ((n_, k_), (dx, dy, anchor, b))
                if best_:
                    return best_[1]
                for dx, dy, anchor in every_:
                    b = box_(dx, dy, anchor)
                    if in_frame(b) and not overlaps(b, furn, 2):
                        return dx, dy, anchor, b
                dx, dy, anchor = cands_[0]
                bx = min(max(gx + dx, EDGE + 2), w - EDGE - 2 - bw_)
                by = min(max(gy + dy, EDGE + top_), h - EDGE - bot_)
                return bx - gx, by - gy, 'start', (bx - 2, by - top_, bx + bw_ + 2, by + bot_)
            gmax_ft, gmax_m = fmt_int(tr.gps_max_m * FT), fmt_int(tr.gps_max_m)
            if gl and summit:
                l1 = summit.upper()
                if gl == 'name':
                    # phones: the summit name only (the value is in the strip right above the map)
                    bw_ = text_w(l1, 12, 0.12)
                    bot_ = 4
                else:
                    # the value line follows the MI|KM toggle; placed with the wider of the two
                    l2_mi, l2_km = 'GPS MAX %s FT' % gmax_ft, 'GPS MAX %s M' % gmax_m
                    bw_ = max(text_w(l1, 12, 0.12), text_w(l2_mi, fs_s, 0.02, True), text_w(l2_km, fs_s, 0.02, True))
                    bot_ = 18
                cands = [(12, -6, 'start'), (12, 8, 'start'), (-12, -6, 'end'), (-12, 8, 'end'), (0, -34 + (14 if gl == 'name' else 0), 'middle'),
                         (0, 20, 'middle'), (16, -20, 'start'), (-16, -20, 'end'), (16, 22, 'start'), (-16, 22, 'end'),
                         (0, -48 + (14 if gl == 'name' else 0), 'middle'), (0, 34, 'middle'), (28, -6, 'start'), (-28, -6, 'end'), (28, 14, 'start'), (-28, 14, 'end')]
                # phones name the summit only (no value): a context label, left off when every spot crosses the route
                placed_ = place_label(bw_, 10, bot_, cands, optional=(gl == 'name'))
                dx, dy, anchor, b = placed_ or (0, 0, 'start', None)
                lx = gx + dx if anchor == 'start' else (gx + dx - bw_ if anchor == 'end' else gx - bw_ / 2)
                if not placed_:
                    pass
                elif gl == 'name':
                    layers['labels'].append('<text class="mk-peak" x="%.1f" y="%.1f" style="fill: #16171A">%s</text>' % (lx, gy + dy, esc(l1)))
                else:
                    layers['labels'].append('<text class="mk-peak" x="%.1f" y="%.1f" style="fill: #16171A">%s</text><text class="mk-gps" x="%.1f" y="%.1f">%s</text>'
                                            % (lx, gy + dy, esc(l1), lx, gy + dy + 14, u_span(l2_mi, l2_km)))
                if b:
                    boxes.append(b)
                    tboxes.append(b)
                spec.setdefault('_prio_done', set()).add(summit)
            elif gl and gl != 'name':
                first = spec.get('gps_label_first')
                cands = [(12, 4, 'start'), (12, 18, 'start'), (-12, 4, 'end'), (12, -10, 'start'), (-12, 18, 'end'), (-12, -10, 'end'),
                         (0, -16, 'middle'), (0, 24, 'middle'), (24, 4, 'start'), (-24, 4, 'end'), (18, 30, 'start'), (-18, 30, 'end'),
                         (18, -22, 'start'), (-18, -22, 'end'), (0, -30, 'middle'), (0, 38, 'middle')]
                if first:
                    cands.insert(0, first)
                # at the start / end: 'START · GPS MAX …' where it fits clear of the route, else the shorter 'GPS MAX …'
                # (the disc / square beside the triangle already marks the start, and the key decodes it)
                placed_ = None
                for pre_ in ((('%s · ' % at_start),) if at_start else ()) + ('',):
                    txt_mi, txt_km = '%sGPS MAX %s FT' % (pre_, gmax_ft), '%sGPS MAX %s M' % (pre_, gmax_m)
                    tw = max(text_w(txt_mi, fs_s, 0.02, True), text_w(txt_km, fs_s, 0.02, True))
                    placed_ = place_label(tw, 9, 4, cands, optional=bool(pre_))
                    if placed_:
                        break
                dx, dy, anchor, b = placed_
                # anchored at the box edge (not the text's own anchor), so the shorter of the two unit texts stays in the box
                ax_ = b[0] + 2 if anchor == 'start' else (b[2] - 2 if anchor == 'end' else (b[0] + b[2]) / 2)
                layers['labels'].append('<text class="mk-gps" x="%.1f" y="%.1f" text-anchor="%s">%s</text>' % (ax_, gy + dy, anchor, u_span(txt_mi, txt_km)))
                boxes.append(b)
                tboxes.append(b)
        if t.get('pin'):
            sx, sy = xy[0]
            layers['markers'].append(pin_svg(sx, sy, t.get('cat', 'SKI'), t.get('pin_num')))
            marker_pts.append((sx, sy))
            boxes.append((sx - 12, sy - 12, sx + 12, sy + 12))

    if spec.get('overall_startend') and proj_tracks:
        sx, sy = proj_tracks[0][1][0]
        ex, ey = proj_tracks[-1][1][-1]
        if math.hypot(sx - ex, sy - ey) < 16:
            cx_, cy_ = (sx + ex) / 2, (sy + ey) / 2
            sx, sy, ex, ey = cx_ - 6, cy_, cx_ + 6, cy_
        hut_boxes = spec.get('_hut_boxes', [])

        def beside_hut(x, y, left_first):
            # a numbered end-of-day square already sits here: the disc / square goes beside it, never under it (the start
            # disc on its left, the end square on its right, where free: they read in order)
            hb_ = next((b_ for b_ in hut_boxes if abs(b_['x'] - x) < b_['hw'] + 7 and abs(b_['y'] - y) < 17), None)
            if not hb_:
                return x, y
            sides_ = ((-hb_['hw'] - 9, 0), (hb_['hw'] + 9, 0)) if left_first else ((hb_['hw'] + 9, 0), (-hb_['hw'] - 9, 0))
            for dx_, dy_ in sides_ + ((0, -19), (0, 19)):
                c_ = (hb_['x'] + dx_, hb_['y'] + dy_)
                if not overlaps((c_[0] - 6, c_[1] - 6, c_[0] + 6, c_[1] + 6), boxes, 1):
                    return c_
            return hb_['x'] + hb_['hw'] + 9, hb_['y']
        sx, sy = beside_hut(sx, sy, True)
        boxes.append((sx - 7, sy - 7, sx + 7, sy + 7))
        ex, ey = beside_hut(ex, ey, False)
        boxes.pop()
        layers['markers'].append('<rect x="%.1f" y="%.1f" width="10" height="10" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 2; paint-order: stroke"/>' % (ex - 5, ey - 5))
        layers['markers'].append('<circle cx="%.1f" cy="%.1f" r="5" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 2; paint-order: stroke"/>' % (sx, sy))
        boxes += [(sx - 8, sy - 8, sx + 8, sy + 8), (ex - 8, ey - 8, ex + 8, ey + 8)]
        marker_pts += [(sx, sy), (ex, ey)]
    # transfers (dashed connector between a day end and the next start)
    for a_i, b_i in spec.get('transfers', []):
        ax, ay = proj_tracks[a_i][1][-1]
        bx_, by_ = proj_tracks[b_i][1][0]
        layers['track'].append('<path d="M%.1f %.1fL%.1f %.1f" style="fill: none; stroke: #66686D; stroke-width: %s; stroke-dasharray: %s; stroke-linecap: butt"/>'
                               % (ax, ay, bx_, by_, spec.get('transfer_w', 1.5), spec.get('transfer_dash', '2 4')))
        if not spec.get('transfer_label', True):
            continue
        mx, my = (ax + bx_) / 2, (ay + by_) / 2
        tw = text_w('TRANSFER', fs_s, mono=True)
        for dy in (-8, 16, -20, 28):
            b = (mx - tw / 2 - 2, my + dy - 9, mx + tw / 2 + 2, my + dy + 3)
            if free(b, 2, track=False):
                layers['labels'].append('<text class="mk-lbl" x="%.1f" y="%.1f" text-anchor="middle">TRANSFER</text>' % (mx, my + dy))
                boxes.append(b)
                tboxes.append(b)
                break

    # waypoints
    for n, (lat, lon) in enumerate(spec.get('waypoints', []), 1):
        x, y = proj.xy(lat, lon)
        layers['markers'].append('<circle cx="%.1f" cy="%.1f" r="11" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 1.5; paint-order: stroke"/><text class="mk-numw" x="%.1f" y="%.1f">%d</text>' % (x, y, x, y + 0.5, n))
        marker_pts.append((x, y))
        boxes.append((x - 12, y - 12, x + 12, y + 12))
    # hut labels: only faded other-day ghosts may be overlapped; a hut that fits nowhere keeps its numbered square
    # (the day list names it)
    for ex, ey, lbl in meta.get('hut_labels', []):
        tw = text_w(lbl, 12)
        for dx, dy, anchor in ((14, 4, 'start'), (-14, 4, 'end'), (26, 4, 'start'), (-26, 4, 'end'), (0, -16, 'middle'), (0, 24, 'middle'),
                               (0, -30, 'middle'), (0, 30, 'middle'), (14, -12, 'start'), (-14, -12, 'end'), (14, 20, 'start'), (-14, 20, 'end'),
                               (0, 38, 'middle')):
            bx = ex + dx if anchor == 'start' else (ex + dx - tw if anchor == 'end' else ex - tw / 2)
            b = (bx, ey + dy - 10, bx + tw, ey + dy + 3)
            if free(b, 2, track='solid'):
                layers['labels'].append('<text class="mk-hut" x="%.1f" y="%.1f" text-anchor="%s">%s</text>' % (ex + dx, ey + dy, anchor, esc(lbl)))
                boxes.append(b)
                tboxes.append(b)
                break
    def place_towns():
        """Town rings + names (city/town/village; with places_allow, exactly those names, hamlets included)."""
        cand = []
        txy = [p for pt in proj_tracks for p in pt[1][::10]] + [tuple(c) for c in marker_pts]
        rank = {'city': 0, 'town': 1, 'village': 2}
        allow = spec.get('places_allow')
        for (lat, lon), tags in geo.osm_nodes(osm, lambda t: t.get('place') in (('city', 'town', 'village', 'hamlet') if allow else ('city', 'town', 'village')) and t.get('name')):
            if allow is not None and tags['name'] not in allow:
                continue
            x, y = proj.xy(lat, lon)
            dmin = min((math.hypot(x - a, y - b) for a, b in txy), default=0)
            try:
                pop = int(re.sub(r'[^\d]', '', str(tags.get('population') or '')) or 0)
            except ValueError:
                pop = 0
            if spec.get('places_by_rank'):
                # region maps: cities before towns before villages, the biggest first (it anchors the map), then nearest
                cand.append(((rank.get(tags.get('place'), 3), -pop), dmin, x, y, tags))
            else:
                cand.append((0, dmin, x, y, tags))
        cand.sort(key=lambda c: (c[0], c[1]))
        pin_xy = [proj.xy(pn['lat'], pn['lon']) for pn in spec.get('pins', [])]
        near_pins = spec.get('places_near_pins')

        def by_pins(x, y):
            return any(math.hypot(x - a_, y - b_) < near_pins for a_, b_ in pin_xy)
        anchor_i = None
        if near_pins:
            # the anchor: the biggest city / town in the frame (cities first, then by population) is labelled wherever it
            # is; every other place only near a pin
            anchor_i = next((k_ for k_, c_ in enumerate(cand) if c_[4].get('place') in ('city', 'town')
                             and 20 < c_[2] < w - 20 and 20 < c_[3] < h - 20), None)
        n_places = 0
        seen_pl = set()
        for k_c, (_, _, x, y, tags) in enumerate(cand):
            if n_places >= (99 if spec.get('places_allow') else spec.get('places_max', 8)):
                break
            is_anchor = k_c == anchor_i
            if near_pins and not is_anchor and not by_pins(x, y):
                continue
            if tags['name'] in seen_pl:
                continue
            seen_pl.add(tags['name'])
            txt = tags['name']
            tw = text_w(txt, 12)
            if not (EDGE < x < w - EDGE and EDGE < y < h - EDGE):
                continue
            if not allow and not (20 < x < w - 20 and 20 < y < h - 20):
                continue
            ring = (x - 5, y - 5, x + 5, y + 5)
            if overlaps(ring, boxes, 1):
                continue
            # right of the ring, then left of it, then above / below either side: the first spot clear of every track;
            # the route's named places (places_allow) and a region map's anchor town may instead take the free spot that
            # crosses the least track (on a halo); any other place is left off
            spots_ = []
            for dx, dy, anchor in ((8, 4, 'start'), (-8, 4, 'end'), (6, -9, 'start'), (6, 17, 'start'), (-6, -9, 'end'), (-6, 17, 'end')):
                bx = x + dx if anchor == 'start' else x + dx - tw
                b = (bx - 1, y + dy - 11, bx + tw + 1, y + dy + 3)
                if in_frame(b) and not overlaps(b, boxes, 3):
                    spots_.append((dx, dy, anchor, b))
            pick = next((sp_ for sp_ in spots_ if not hits_track_dense(sp_[3], 2)), None)
            if pick is None and (allow or is_anchor) and spots_:
                pick = min(spots_, key=lambda sp_: sum(1 for x_, y_ in dense_trk if sp_[3][0] - 2 <= x_ <= sp_[3][2] + 2
                                                        and sp_[3][1] - 2 <= y_ <= sp_[3][3] + 2))
            if pick is None:
                continue
            dx, dy, anchor, b = pick
            layers['labels'].append('<circle cx="%.1f" cy="%.1f" r="3.5" style="fill: #EEECE6; stroke: #45474C; stroke-width: 1.5"/><text class="mk-place" x="%.1f" y="%.1f"%s>%s</text>'
                                    % (x, y, x + dx, y + dy, ' text-anchor="end"' if anchor == 'end' else '', esc(txt)))
            boxes.append(b)
            boxes.append(ring)
            tboxes.append(b)
            n_places += 1

    # named towns (places_allow: the route's endpoints) outrank day labels, contour labels and context peaks
    if osm and spec.get('places', True) and spec.get('places_allow'):
        place_towns()

    # day labels: route-ink text beside the track, no boxes
    if spec.get('day_labels', True):
        for idx_t, (t, xy, cds, seg) in enumerate(proj_tracks):
            if not t.get('day_label'):
                continue
            lbl = 'D%d' % t['day_label']
            tw = text_w(lbl, 12, mono=True) + 2
            done = False
            for strict in (2, 1, 0):
                for frac in (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8):
                    mx, my, ang = along(xy, cds, cds[0] + (cds[-1] - cds[0]) * frac)
                    nx, ny = -math.sin(ang), math.cos(ang)
                    for side in (1, -1):
                        cx, cy = mx + side * nx * 14, my + side * ny * 14
                        b = (cx - tw / 2 - 2, cy - 8, cx + tw / 2 + 2, cy + 6)
                        if free(b, 6 if strict == 2 else 2, track=strict > 0):
                            layers['labels'].append('<text x="%.1f" y="%.1f" style="font: 600 12px/1 %s; fill: #B8300F; stroke: #EEECE6; stroke-width: 3px; paint-order: stroke; stroke-linejoin: round; text-anchor: middle; dominant-baseline: central">%s</text>' % (cx, cy, MONO, lbl))
                            boxes.append(b)
                            tboxes.append(b)
                            done = True
                            break
                    if done:
                        break
                if done:
                    break

    # scale bar: a compact bar in the freest corner, one per unit (the MI|KM toggle shows one); at most 25% of the width
    if spec.get('scale', True):
        mpp = proj.m_per_px
        cap_px = min(80 if w <= 400 else 120, SCALE_MAX_FRAC * w)
        mi_len = nice_len(cap_px * mpp, 'mi')[0]
        spec['_scale'] = None

        def sb_w(bar_px, lab):
            lw_ = text_w(lab, fs_s, mono=True)
            return bar_px + 6 + lw_ + 24 if bar_px < text_w('0', fs_s, mono=True) + 8 + lw_ else bar_px + 24
        for attempt in range(4):
            mi_px = mi_len * MI / mpp
            km_len = nice_len(mi_px * mpp, 'km')[0]  # the metric bar is never longer than the imperial one
            km_px = km_len * 1000.0 / mpp
            bw_ = max(sb_w(mi_px, '%g mi' % mi_len), sb_w(km_px, km_label(km_len)))
            bh_ = 30
            ix_ = 96 if w >= 1200 else (12 if w <= 400 else 16)
            iy_ = 12 if w <= 400 else 16
            corners = {'br': (w - ix_ - bw_ + 12, h - iy_ - bh_), 'bl': (ix_ - 12, h - iy_ - bh_), 'tl': (ix_ - 12, iy_), 'tr': (w - 70 - bw_, iy_)}
            order_c = [spec['scale_corner']] if spec.get('scale_corner') else ['br', 'bl', 'tl', 'tr']
            best = None
            for c in order_c:
                x0_, y0_ = corners[c]
                b = (x0_, y0_, x0_ + bw_, y0_ + bh_)
                n_hit = sum(1 for x_, y_ in trk_pts if b[0] - 16 <= x_ <= b[2] + 16 and b[1] - 16 <= y_ <= b[3] + 16)
                n_box = 1 if overlaps(b, boxes, 16) else 0
                score = n_box * 1000 + n_hit
                if best is None or score < best[0]:
                    best = (score, c, b)
            smaller = [c for c in NICE_LENS if c < mi_len]
            if best[0] == 0 or spec.get('scale_corner') or attempt == 3 or not smaller:
                spec['_scale'] = (best[1], best[2], mi_len, mi_px, km_len, km_px, fs_s)
                boxes.append(best[2])
                break
            mi_len = smaller[-1]  # step down to the next nice length
        spec['_scale_corner'] = spec['_scale'][0]

    # overall start / end dates beside the start disc and end square (series maps: 'APR 22' / 'SEP 21')
    if spec.get('overall_startend') and spec.get('overall_labels') and proj_tracks:
        for txt, (mx, my) in zip(spec['overall_labels'], (proj_tracks[0][1][0], proj_tracks[-1][1][-1])):
            if not txt:
                continue
            tw = text_w(txt, fs_s, mono=True)
            done_ = False
            for strict in (True, False):
                for dx, dy, anchor in ((14, 4, 'start'), (-14, 4, 'end'), (14, -8, 'start'), (-14, -8, 'end'), (14, 16, 'start'), (-14, 16, 'end'),
                                       (0, -14, 'middle'), (0, 24, 'middle')):
                    bx = mx + dx if anchor == 'start' else (mx + dx - tw if anchor == 'end' else mx - tw / 2)
                    b = (bx - 2, my + dy - 10, bx + tw + 2, my + dy + 3)
                    if free(b, 2, track=strict):
                        layers['labels'].append('<text class="mk-lbl" x="%.1f" y="%.1f" text-anchor="%s">%s</text>' % (mx + dx, my + dy, anchor, esc(txt)))
                        boxes.append(b)
                        tboxes.append(b)
                        done_ = True
                        break
                if done_:
                    break

    # clustered pins
    if spec.get('pins'):
        pts_px = []
        for pn in spec['pins']:
            x, y = proj.xy(pn['lat'], pn['lon'])
            pts_px.append([x, y, pn])
        clusters = []
        for x, y, pn in pts_px:
            for c in clusters:
                if math.hypot(c['x'] - x, c['y'] - y) < spec.get('cluster_px', 24):
                    c['items'].append(pn)
                    break
            else:
                clusters.append({'x': x, 'y': y, 'items': [pn]})
        key_xy = {pt[0]['track'].key: pt[1] for pt in proj_tracks if hasattr(pt[0]['track'], 'key')}
        hit_r = 24 if phone else 22  # a phone map is shown at ~0.92x: r=24 keeps the tap target >= 44px at 360
        for c in clusters:
            x, y = c['x'], c['y']
            if len(c['items']) == 1:
                pn = c['items'][0]
                txy_ = key_xy.get(pn.get('key'))
                if txy_:
                    xs_ = [q[0] for q in txy_]
                    ys_ = [q[1] for q in txy_]
                    if math.hypot(max(xs_) - min(xs_), max(ys_) - min(ys_)) < 24:
                        ox, oy = x - w / 2, y - h / 2
                        L = math.hypot(ox, oy) or 1
                        nx_, ny_ = x + ox / L * 18, y + oy / L * 18
                        layers['markers'].append('<path d="M%.1f %.1fL%.1f %.1f" style="stroke: #66686D; stroke-width: 1"/>' % (x, y, nx_, ny_))
                        x, y = nx_, ny_
                pin_ = pin_svg(x, y, pn['cat'], pn.get('num'))
                if pn.get('href'):
                    pin_ = ('<a class="mk-pin" href="%s" data-key="%s" aria-label="%s"><title>%s</title><circle class="mk-hit" cx="%.1f" cy="%.1f" r="%d" style="fill: transparent"/>%s</a>'
                            % (esc(pn['href']), esc(pn.get('key', '')), esc(pn.get('title', '')), esc(pn.get('title', '')), x, y, hit_r, pin_))
                layers['pins'].append(pin_)
            else:
                n = len(c['items'])
                cats_ = set(i_['cat'] for i_ in c['items'])
                ring = CAT[list(cats_)[0]] if len(cats_) == 1 else '#16171A'
                layers['pins'].append('<g class="mk-cluster" aria-hidden="true" data-keys="%s"><title>%s</title><circle class="mk-hit" cx="%.1f" cy="%.1f" r="%d" style="fill: transparent"/><circle cx="%.1f" cy="%.1f" r="11" style="fill: #F2F1EC; stroke: %s; stroke-width: 2"/><text x="%.1f" y="%.1f" style="font: 600 12px/1 %s; fill: #16171A; text-anchor: middle; dominant-baseline: central">%d</text></g>'
                                      % (esc(' '.join(i_.get('key', '') for i_ in c['items'])), esc('; '.join(i_.get('title', '') for i_ in c['items'])), x, y, hit_r, x, y, ring, x, y + 0.5, MONO, n))
            c['x'], c['y'] = x, y
            boxes.append((x - 12, y - 12, x + 12, y + 12))
            marker_pts.append((x, y))
        meta['clusters'] = [{'x': c['x'], 'y': c['y'], 'n': len(c['items']), 'keys': [i.get('key') for i in c['items']]} for c in clusters]

    # priority peaks (placed early so they win); a peak merged with the GPS-max label is already done
    done_prio = spec.setdefault('_prio_done', set())
    if osm and spec.get('priority_peaks'):
        for (lat, lon), tags in geo.osm_nodes(osm, lambda t: t.get('natural') == 'peak' and t.get('name') in spec['priority_peaks']):
            if tags['name'] in done_prio:
                continue
            x, y = proj.xy(lat, lon)
            if not (EDGE < x < w - EDGE and EDGE < y < h - EDGE):
                continue
            if overlaps((x - 5, y - 6, x + 5, y + 3), boxes, 1):
                continue  # its triangle would sit on a marker or another label
            txt = tags['name'].upper()
            tw = text_w(txt, 12, 0.12)
            ok = False
            trk_pad = 6 if spec.get('overview_labels') else 4
            for pad_ in ((4,) if spec.get('overview_labels') else (2, 1)):
                # beside the triangle first, so each triangle sits at the start or end of its own name; never on a track
                # (every track pixel, the box inflated by 4 px): a name that fits nowhere is left off
                for dx, dy, anchor in PEAK_SPOTS:
                    bx = x + dx if anchor == 'start' else (x + dx - tw if anchor == 'end' else x - tw / 2)
                    b = (bx - 1, y + dy - 10, bx + tw + 1, y + dy + 3)
                    if not overlaps(b, boxes, pad_) and not overlaps((b[0] - 12, b[1], b[2] + 12, b[3]), tboxes, pad_) and in_frame(b) and \
                            not hits_track_dense(b, trk_pad):
                        layers['labels'].append('<path class="mk-tri" d="M%.1f %.1fl3.5 6h-7z"/><text class="mk-peak" x="%.1f" y="%.1f" text-anchor="%s" style="fill: #16171A">%s</text>'
                                                % (x, y - 3.5, x + dx, y + dy, anchor, esc(txt)))
                        boxes.append(b)
                        tboxes.append(b)
                        boxes.append((x - 4, y - 4, x + 4, y + 3))
                        ok = True
                        break
                if ok:
                    break
            if ok:
                done_prio.add(tags['name'])
        # names that were not placed must not reappear as ranked peaks either
        for nm in spec['priority_peaks']:
            done_prio.add(nm)

    # contours
    if spec.get('contours', True):
        iv = spec.get('interval_ft') or choose_interval(proj.m_per_px * spec.get('contour_density', 1.0), 0)
        cstep = spec.get('contour_step', 2.0)
        cl, clbl, (lo, hi) = contours_svg(proj, iv, step=cstep, zoom=spec.get('ct_zoom'),
                                          labels=spec.get('contour_labels', True), label_boxes=boxes, avoid=avoid,
                                          min_len=spec.get('contour_min_len', 18), eps=spec.get('contour_eps', 0.6),
                                          max_labels=spec.get('contour_labels_max', 2 if w <= 718 else 3),
                                          minor_on=spec.get('minor_contours', True))
        layers['contours'] += cl
        layers['labels'] += clbl
        meta['interval_ft'] = iv
        meta['relief_m'] = (lo, hi)

    # OSM labels (after track so we avoid it)
    if osm:
        # peaks
        peaks = geo.osm_nodes(osm, lambda t: t.get('natural') == 'peak' and t.get('name'))
        ranked = []
        track_xy_all = [p for pt in proj_tracks for p in pt[1][::5]]
        for (lat, lon), tags in peaks:
            if tags['name'] in spec.get('_prio_done', ()):
                continue
            x, y = proj.xy(lat, lon)
            if not (20 < x < w - 20 and 20 < y < h - 20):
                continue
            dmin = min((math.hypot(x - a, y - b) for a, b in track_xy_all), default=1e9)
            try:
                ele = float(str(tags.get('ele', '0')).split()[0].replace(',', ''))
            except ValueError:
                ele = 0
            ranked.append((0 if dmin < 60 else 1, -ele, x, y, tags['name']))
        ranked.sort()
        n_ok = 0
        for _, _, x, y, nm in ranked:
            if n_ok >= spec.get('peaks_max', 8):
                break
            if len(nm) > 24:
                continue
            if overlaps((x - 5, y - 6, x + 5, y + 3), boxes, 2):
                continue
            txt = nm.upper()
            tw = text_w(txt, 12, 0.12)
            # context peaks: 8 spots around the triangle, never on a track (the box inflated by 4 px against every track
            # pixel); a name that fits nowhere is left off
            for dx, dy, anchor in PEAK_SPOTS:
                bx = x + dx if anchor == 'start' else (x + dx - tw if anchor == 'end' else x - tw / 2)
                b = (bx - 1, y + dy - 10, bx + tw + 1, y + dy + 3)
                if not overlaps(b, boxes, 8) and not overlaps((b[0] - 12, b[1], b[2] + 12, b[3]), tboxes, 8) and in_frame(b) and \
                        not hits_track_dense(b, 4):
                    layers['labels'].append('<path class="mk-tri" d="M%.1f %.1fl3.5 6h-7z"/><text class="mk-peak" x="%.1f" y="%.1f" text-anchor="%s">%s</text>'
                                            % (x, y - 3.5, x + dx, y + dy, anchor, esc(txt)))
                    boxes.append(b)
                    tboxes.append(b)
                    boxes.append((x - 4, y - 4, x + 4, y + 3))
                    n_ok += 1
                    break
        # places (named endpoints outrank context peaks: placed before them)
        if spec.get('places', True) and not spec.get('places_allow'):
            place_towns()
        # water labels
        water_named.sort(key=lambda z: -z[0])
        seen = set()
        manual = set(txt_ for _, _, txt_ in spec.get('extra_water_labels', []))
        for area, rings_xy, nm in water_named[:spec.get('water_labels', 6)]:
            if nm in seen or nm in manual:
                continue
            if ';' in nm or re.fullmatch(r'[A-Z]{0,3}\d+[A-Z]?\d*', nm) or not any(c_.islower() for c_ in nm):
                continue  # reference codes, not names ('A2W', 'A5;A7;A8;A8S', 'A18', all-caps codes)
            seen.add(nm)
            big = max(rings_xy, key=ring_area_px)
            cx = sum(p[0] for p in big) / len(big)
            cy = sum(p[1] for p in big) / len(big)
            # nudge into frame
            cx = min(max(cx, 60), w - 60)
            cy = min(max(cy, 30), h - 30)
            if spec.get('water_near_track') and not any(math.hypot(cx - a_, cy - b_) < spec['water_near_track'] + 40 for a_, b_ in trk_pts[::3]):
                continue
            cls = 'mk-wlw' if area > (w * h * 0.12) else 'mk-wl'
            tw = text_w(nm, 16 if cls == 'mk-wlw' else 14, 0.2 if cls == 'mk-wlw' else 0)
            if area <= 400:
                continue
            bx0 = min(p_[0] for p_ in big); bx1 = max(p_[0] for p_ in big)
            by0 = min(p_[1] for p_ in big); by1 = max(p_[1] for p_ in big)
            cands = [(cx, cy), (cx, by0 - 6), (cx, by1 + 16), (bx1 + 6 + tw / 2, cy + 4), (bx0 - 6 - tw / 2, cy + 4)]
            for ci_, (lx_, ly_) in enumerate(cands):
                b = (lx_ - tw / 2, ly_ - 10, lx_ + tw / 2, ly_ + 6)
                if ci_ == 0 and sum(point_in_ring((px_, ly_ - 3), big) for px_ in (b[0] + 2, lx_, b[2] - 2)) < 2:
                    continue  # a lake larger than the frame: its clamped centroid can land on shore
                if ci_ > 0 and (bx1 - bx0 > w * 0.6 or by1 - by0 > h * 0.6):
                    continue  # never label a frame-filling lake from outside it
                if in_frame(b) and not overlaps(b, boxes, 3) and not hits_track_dense(b, 6):
                    layers['labels'].append('<text class="%s" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (cls, lx_, ly_, esc(nm)))
                    boxes.append(b)
                    break
        # road refs (one per ref)
        done = set()
        for xy, ref in road_lbls:
            if ref in done or len(xy) < 2:
                continue
            L = geo.path_len(xy)
            if L < 120:
                continue
            mid = xy[len(xy) // 2]
            txt = ref
            tw = text_w(txt, fs_s, mono=True)
            b = (mid[0] - tw / 2 - 3, mid[1] - 8, mid[0] + tw / 2 + 3, mid[1] + 8)
            if in_frame(b) and not overlaps(b, boxes, 4) and not hits_track(b, 24):
                layers['labels'].append('<rect x="%.1f" y="%.1f" width="%.1f" height="16" style="fill: #FFFFFF; stroke: #8C8A83; stroke-width: 1"/><text class="mk-rl" x="%.1f" y="%.1f" text-anchor="middle" dominant-baseline="central" style="stroke-width: 0">%s</text>'
                                        % (b[0], b[1], b[2] - b[0], mid[0], mid[1] + 0.5, esc(txt)))
                boxes.append(b)
                done.add(ref)

    for (lx, ly, ltxt) in spec.get('extra_water_labels', []):
        layers['labels'].append('<text class="mk-wlw" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (lx, ly, esc(ltxt)))
    # graticule ticks
    fur = []
    if spec.get('graticule', True):
        s_, w_, n_, e_ = proj.bounds()
        span = n_ - s_
        cand = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5]
        stp = next(c for c in cand if span / c <= 5)
        v = math.ceil(s_ / stp) * stp
        while v < n_:
            _, y = proj.xy(v, proj.lon0)
            txt = '%.*f°%s' % (2 if stp < 0.1 else 1, abs(v), 'N' if v >= 0 else 'S')
            if 40 < y < h - 40 and not overlaps((0, y - 8, 12 + text_w(txt, 11, mono=True), y + 8), boxes, 4):
                fur.append('<path d="M0 %.1fh6" style="stroke: #16171A; stroke-width: 1"/><text class="mk-lbl" x="9" y="%.1f" dominant-baseline="central">%s</text>' % (y, y, txt))
            v += stp
        spanx = e_ - w_
        stpx = next(c for c in cand if spanx / c <= 7)
        v = math.ceil(w_ / stpx) * stpx
        while v < e_:
            x, _ = proj.xy(proj.latc, v)
            sb = spec.get('_scale')
            txt = '%.*f°%s' % (2 if stpx < 0.1 else 1, abs(v), 'E' if v >= 0 else 'W')
            twg = text_w(txt, 11, mono=True)
            if (290 if spec.get('legend') else 60) < x < w - 60 and not (sb and sb[1][0] - 40 < x < sb[1][2] + 40 and sb[1][3] > h - 60) \
                    and not overlaps((x - twg / 2, h - 20, x + twg / 2, h), boxes, 4):
                fur.append('<path d="M%.1f %dv-6" style="stroke: #16171A; stroke-width: 1"/><text class="mk-lbl" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (x, h, x, h - 10, txt))
            v += stpx
    if spec.get('north', True):
        nx_, ny_ = w - 34, 22
        fur.append('<g transform="translate(%d %d)"><path d="M0 0l7 24-7-5-7 5z" style="fill: #16171A; stroke: #EEECE6; stroke-width: 1.5; paint-order: stroke"/>'
                   '<text class="mk-lbl" x="0" y="38" text-anchor="middle" style="fill: #16171A; font-weight: 600">N</text></g>' % (nx_, ny_))
    if spec.get('scale', True) and spec.get('_scale'):
        fur.append(scale_bar_compact(*spec['_scale']))
    aria = spec.get('aria', '')
    static = ''.join(''.join(layers[k]) for k in ('water', 'contours', 'lines'))
    if spec.get('split_base', True) and static:
        base_svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d"><style>%s</style>%s</svg>\n'
                    % (w, h, w, h, BASE_CSS, static))
        with open(os.path.join(FRAG, name + '.base.svg'), 'w') as fh:
            fh.write(base_svg)
        meta['base'] = name + '.base.svg'
        gz_kb = len(zlib.compress(base_svg.encode('utf-8'), 9)) / 1024.0
        meta['base_gz_kb'] = round(gz_kb, 1)
        if gz_kb > (BASE_GZ_KB_PHONE if phone else BASE_GZ_KB):
            print('  ! %s.base.svg is %.0f KB gzipped (budget %d KB)' % (name, gz_kb, BASE_GZ_KB_PHONE if phone else BASE_GZ_KB))
        order = ['base', 'track', 'markers', 'labels']
    else:
        order = ['base', 'water', 'contours', 'lines', 'track', 'markers', 'labels']
    body = ''.join(''.join(layers[k]) for k in order) + ''.join(fur)
    ph_cls = ' class="mk-ph"' if phone else ''
    if layers['pins']:
        svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d"%s role="group" aria-label="%s" '
               'style="position: absolute; left: 0; top: 0; display: block; overflow: hidden"><g aria-hidden="true">%s</g>%s</svg>') % (w, h, w, h, ph_cls, esc(aria), body, ''.join(layers['pins']))
    else:
        svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d"%s role="img" aria-label="%s" '
               'style="position: absolute; left: 0; top: 0; display: block; overflow: hidden">%s</svg>') % (w, h, w, h, ph_cls, esc(aria), body)
    write_frag(name, svg)
    meta['bytes'] = len(svg)
    meta['total_mi'] = total_mi
    json.dump(meta, open(os.path.join(FRAG, name + '.meta.json'), 'w'), default=str)
    return meta


NICE_LENS = (0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 20, 50, 100, 200)
SCALE_MAX_FRAC = 0.25  # a scale bar never spans more than this share of the map width


def nice_len(max_m, units):
    """The largest nice length (NICE_LENS, in mi or km) that fits in max_m metres; the smallest one when none does."""
    unit_m = MI if units == 'mi' else 1000.0
    best = NICE_LENS[0]
    for c in NICE_LENS:
        if c * unit_m <= max_m:
            best = c
    return best, best * unit_m


def _scale_group(cls, x0, y0, bar_px, lab, fs, right=None):
    """One unit's bar: two blocks, '0' over its start and the length over its end (beside it when the bar is short).
    right: the x the group ends at (right-hand corners), else it starts at x0."""
    halo = 'stroke: #EEECE6; stroke-width: 3px; paint-order: stroke; stroke-linejoin: round; fill: #45474C'
    lw = text_w(lab, fs, mono=True)
    beside = bar_px < text_w('0', fs, mono=True) + 8 + lw
    if right is not None:
        x0 = right - (bar_px + 6 + lw if beside else bar_px)
    seg = bar_px / 2
    parts = ['<rect x="%.1f" y="%.1f" width="%.1f" height="5" style="fill: %s; stroke: #16171A; stroke-width: .75"/>'
             % (x0 + k * seg, y0, seg, '#16171A' if k == 0 else '#FFFFFF') for k in range(2)]
    parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" style="%s; text-anchor: start">0</text>' % (x0, y0 - 5, halo))
    if beside:
        parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" style="%s; text-anchor: start">%s</text>' % (x0 + bar_px + 6, y0 + 5, halo, lab))
    else:
        parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" style="%s; text-anchor: end">%s</text>' % (x0 + bar_px, y0 - 5, halo, lab))
    return '<g class="%s">%s</g>' % (cls, ''.join(parts))


def scale_bar_compact(corner, box, mi_len, mi_px, km_len, km_px, fs=11):
    """The map's scale bar in both units (<g class="u-mi"> / <g class="u-km">, one shown by the MI|KM toggle), each with
    its own nice length. Left-hand corners start at the box's inset; right-hand corners end there."""
    x0, y0 = box[0] + 12, box[1] + 22
    right = (box[2] - 12) if corner in ('br', 'tr') else None
    return (_scale_group('u-mi', x0, y0, mi_px, '%g mi' % mi_len, fs, right) +
            _scale_group('u-km', x0, y0, km_px, km_label(km_len), fs, right))


def scale_bar(proj, w, h, corner='br'):
    """Legacy full scale bar (mi blocks over km ticks); render_map uses scale_bar_compact."""
    max_px = min(180, SCALE_MAX_FRAC * w)
    mi_len, mi_m = nice_len(max_px * proj.m_per_px, 'mi')
    km_len, km_m = nice_len(max_px * proj.m_per_px, 'km')
    mi_px = mi_m / proj.m_per_px
    km_px = km_m / proj.m_per_px
    if corner in ('bl', 'tl'):
        x0 = 22
    elif corner == 'tr':
        x0 = w - 112 - max(mi_px, km_px)
    else:
        x0 = w - 52 - max(mi_px, km_px)
    y0 = h - 40 if corner in ('br', 'bl') else 36
    parts = ['<rect x="%.1f" y="%.1f" width="%.1f" height="44" style="fill: #EEECE6; fill-opacity: .88"/>' % (x0 - 10, y0 - 20, max(mi_px, km_px) + 54)]
    # mi bar: 4 alternating blocks
    for k in range(4):
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="6" style="fill: %s; stroke: #16171A; stroke-width: .75"/>'
                     % (x0 + k * mi_px / 4, y0, mi_px / 4, '#16171A' if k % 2 == 0 else '#FFFFFF'))

    def lab(v):
        return ('%g' % v)
    parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" text-anchor="middle" style="stroke-width: 0; fill: #45474C">0</text>' % (x0, y0 - 5))
    parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" text-anchor="middle" style="stroke-width: 0; fill: #45474C">%s</text>' % (x0 + mi_px / 2, y0 - 5, lab(mi_len / 2)))
    parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" text-anchor="start" style="stroke-width: 0; fill: #45474C">%s mi</text>' % (x0 + mi_px - 4, y0 - 5, lab(mi_len)))
    # km ticks below
    parts.append('<path d="M%.1f %.1fv5M%.1f %.1fv5M%.1f %.1fv5" style="stroke: #16171A; stroke-width: 1"/>' % (x0, y0 + 6, x0 + km_px / 2, y0 + 6, x0 + km_px, y0 + 6))
    parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" text-anchor="middle" style="stroke-width: 0; fill: #45474C">0</text>' % (x0, y0 + 21))
    parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" text-anchor="middle" style="stroke-width: 0; fill: #45474C">%s</text>' % (x0 + km_px / 2, y0 + 21, lab(km_len / 2)))
    parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" text-anchor="start" style="stroke-width: 0; fill: #45474C">%s</text>' % (x0 + km_px - 4, y0 + 21, km_label(km_len)))
    return ''.join(parts)


def pin_svg(x, y, cat, num=None):
    col = CAT[cat]
    if num is not None:
        return ('<circle cx="%.1f" cy="%.1f" r="10" style="fill: #FFFFFF"/><circle cx="%.1f" cy="%.1f" r="9" style="fill: #16171A"/>'
                '<text class="mk-numw" x="%.1f" y="%.1f" style="font-size: 11px">%s</text>') % (x, y, x, y, x, y + 0.5, num)
    inner = ('<g transform="translate(%.1f %.1f) scale(.4)" style="fill: none; stroke: #FFFFFF; stroke-width: 2.4; stroke-linecap: square">%s</g>'
             % (x - 4.8, y - 4.8, icon_inner(cat)))
    return ('<circle cx="%.1f" cy="%.1f" r="9" style="fill: #16171A"/><circle cx="%.1f" cy="%.1f" r="8.2" style="fill: #FFFFFF"/>'
            '<circle cx="%.1f" cy="%.1f" r="7" style="fill: %s"/>%s') % (x, y, x, y, x, y, col, inner)


# ---------------------------------------------------------------- profile
AXIS_STEPS = (0.01, 0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 20, 50, 100)
ELEV_STEPS_M = (25, 50, 100, 200, 250, 500, 1000, 2000, 4000)
RELIEF_FLOOR_FT = 250.0  # a profile never spans less than this (3 ft of noise must not draw as a mountain)


def axis_step(total, w):
    """Distance-tick spacing (in the axis unit: mi or km) for a profile w px wide: the finest step whose labels stay at
    least 56 px apart below one unit ('0.25' is wider than '3') and 36 px apart otherwise; every sub-unit track gets real
    fractional ticks ('0 · 0.25 · 0.5')."""
    plot_w = w - (0 if w < 500 else 72)
    for step in AXIS_STEPS:
        if plot_w / max(total / step, 1) >= (56 if step < 1 else 36):
            return step
    return AXIS_STEPS[-1]


def _seg_hits_box(x1, y1, x2, y2, b):
    """Liang–Barsky: does segment (x1, y1)-(x2, y2) touch box b = (x0, y0, x1, y1)?"""
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - b[0]), (dx, b[2] - x1), (-dy, y1 - b[1]), (dy, b[3] - y1)):
        if p == 0:
            if q < 0:
                return False
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return False
    return True


def _box_overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def render_profile(name, tracks, w, plot_h, opts):
    """Elevation profile with a left y-axis gutter. Fragment size stays w x H (H unchanged vs earlier renders).
    Phone renders (w < 500) have no gutter: the y-axis labels sit inside the plot on a paper halo, 12px lettering
    (.pf-ph), each placed where it crosses neither the line nor a marker (left edge, right edge, then under its grid
    line; dropped when all collide, never fewer than two), and the distance unit rides on the last tick.

    Both unit systems are drawn and the MI|KM toggle shows one: grid lines, elevation labels (ft | m) and distance ticks
    (mi | km) sit in <g class="u-mi"> / <g class="u-km"> groups. Distance tick labels carry class "pf-ax pf-xl".

    opts: transfers [(a, b)] (content road transfers: TRANSFER in the day band, dark divider), gaps [b] (day b starts
    somewhere else with no transfer: plain divider), both break the line; within a track the line and fill also break
    wherever consecutive fixes are more than GAP_M apart. A profile spans at least RELIEF_FLOOR_FT."""
    phone = w < 500
    pts = []  # (dist_m, ele_m, day)
    starts = set()  # indices where a new drawn run starts (a break before it)
    xfer_b = set(b_ for a_, b_ in opts.get('transfers', ()))  # day index that starts after a content transfer
    breaks = xfer_b | set(opts.get('gaps', ()))
    off = 0.0
    for di, tr in enumerate(tracks):
        base_i = len(pts)
        if di > 0 and di in breaks:
            starts.add(base_i)
        for k, (d, e) in enumerate(zip(tr.cd, tr.ele)):
            if k > 0 and d - tr.cd[k - 1] > GAP_M:
                starts.add(base_i + k)  # a recording gap inside the day: no line across it
            pts.append((off + d, e, di))
        off += tr.total
    total = off
    runs = []  # [a, b) index ranges drawn as one line
    a_ = 0
    for i in sorted(starts):
        if i > a_:
            runs.append((a_, i))
        a_ = i
    runs.append((a_, len(pts)))
    runs = [r for r in runs if r[1] - r[0] >= 2]
    eles = [p[1] for p in pts]
    lo, hi = min(eles), max(eles)
    lo_ft, hi_ft = lo * FT, hi * FT
    if hi_ft - lo_ft < RELIEF_FLOOR_FT:
        mid_ = (hi_ft + lo_ft) / 2
        lo_ft, hi_ft = mid_ - RELIEF_FLOOR_FT / 2, mid_ + RELIEF_FLOOR_FT / 2
    rng = max(hi_ft - lo_ft, 1)
    pad_l = 0 if phone else 72
    pw = w - pad_l
    top = 24 if opts.get('day_band') else (14 if phone else 8)  # phones: room for the top label above its grid line
    ph = plot_h
    y_lo = lo_ft - 0.06 * rng
    y_hi = hi_ft + 0.10 * rng
    max_lab = 3 if plot_h <= 96 else 5

    def X(d):
        return pad_l + d / total * pw

    def Y(e_m):
        return top + (y_hi - e_m * FT) / (y_hi - y_lo) * (ph - top)

    # ---- elevation label steps: ft (the round-2 rules) and m (the same spacing / count rules over ELEV_STEPS_M)
    def n_ticks(le, f):
        return int(math.floor(y_hi * f / le) - math.ceil(y_lo * f / le)) + 1

    def roomy(le, f):  # phone labels sit inside the plot: 20px apart
        return not phone or le / ((y_hi - y_lo) * f) * (ph - top) >= 20

    def n_labels(le, f):  # ticks that get a label (the grid line is at least 12px above the axis)
        return sum(1 for k in range(int(math.ceil(y_lo * f / le)), int(math.floor(y_hi * f / le)) + 1)
                   if plot_h - (top + (y_hi - k * le / f) / (y_hi - y_lo) * (plot_h - top)) >= 12)
    lab_ft = opts.get('label_every_ft') or (1000 if rng > 4000 else 500)
    while not ((n_ticks(lab_ft, 1) <= max_lab and roomy(lab_ft, 1)) or lab_ft >= 8000):
        lab_ft *= 2
    # a low-relief track (a crag approach, a flat day) still gets two elevation labels: step down to a finer interval
    for le in (1000, 500, 250, 200, 100, 50):
        if n_labels(lab_ft, 1) >= 2 or le >= lab_ft:
            continue
        if roomy(le, 1):
            lab_ft = le
    fm = 1 / FT  # ft -> m
    start_m = max([s_ for s_ in ELEV_STEPS_M if s_ <= lab_ft * fm * 1.05] or [ELEV_STEPS_M[0]])
    lab_m = start_m
    while not ((n_ticks(lab_m, fm) <= max_lab and roomy(lab_m, fm)) or lab_m >= ELEV_STEPS_M[-1]):
        lab_m = next(s_ for s_ in ELEV_STEPS_M if s_ > lab_m)
    for le in reversed(ELEV_STEPS_M):
        if n_labels(lab_m, fm) >= 2 or le >= lab_m:
            continue
        if roomy(le, fm):
            lab_m = le

    def elev_ticks(le, f):
        """[(value in the unit, y px)] top-down."""
        out_, v = [], math.floor(y_hi * f / le) * le
        while v >= y_lo * f - 0.1:
            out_.append((v, top + (y_hi - v / f) / (y_hi - y_lo) * (ph - top)))
            v -= le
        return out_

    step = max(1, len(pts) // (w * 2))
    out = []
    uid = name.replace('-', '_')
    out.append('<defs><pattern id="%s_hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
               '<rect width="5" height="5" style="fill: #E2DFD6"/><path d="M0 0V5" style="stroke: #66686D; stroke-width: 1"/></pattern></defs>' % uid)
    grid_i = len(out)
    out.append('')  # grid lines: filled in once the phone labels have settled each unit's step (below)

    # ---- fills (skin hatch / day tints / one fill), split at every break
    segs = []
    if opts.get('skin'):
        base_i = 0
        for tr in tracks:
            for a, b, dirn in turning_segments(tr.cd, tr.ele, 30):
                segs.append((base_i + a, base_i + b, dirn))
            base_i += len(tr.cd)
    else:
        segs = [(0, len(pts) - 1, 'down')]
    if opts.get('day_tints') and len(tracks) > 1:
        segs = []
        base_i = 0
        for di_, tr in enumerate(tracks):
            segs.append((base_i, base_i + len(tr.cd) - 1, 'tint%d' % (di_ % 2)))
            base_i += len(tr.cd)
    base_y = ph
    for a, b, dirn in segs:
        for ra, rb in runs:  # the part of this fill inside each drawn run
            a2, b2 = max(a, ra), min(b, rb - 1)
            if b2 <= a2:
                continue
            sub = pts[a2:b2 + 1:max(1, step)] + [pts[b2]]
            # simplify the top edge like the line (0.3px), so the fill carries no runs of coincident points
            poly = [(X(sub[0][0]), base_y)] + geo.rdp([(X(d), Y(e)) for d, e, _ in sub], 0.3) + [(X(sub[-1][0]), base_y)]
            fill = {'up': 'url(#%s_hatch)' % uid, 'tint0': '#E2DFD6', 'tint1': '#EAE7DF'}.get(dirn, '#E2DFD6')
            out.append('<path d="%s" style="fill: %s"/>' % (D(poly, closed=True), fill))

    # ---- the line, one subpath per run
    run_xy = []  # (day or None, [(x, y)…]) sampled, for drawing and for the label collision test
    sel = opts.get('selected')
    for ra, rb in runs:
        sub = pts[ra:rb:step] + [pts[rb - 1]]
        if sel is None:  # one continuous subpath per run, across day boundaries
            run_xy.append((None, [(X(d), Y(e)) for d, e, _ in sub]))
            continue
        by_day = {}
        for d, e, dd in sub:
            by_day.setdefault(dd, []).append((X(d), Y(e)))
        for dd, xy_ in sorted(by_day.items()):
            if len(xy_) > 1:
                run_xy.append((dd, xy_))
    if sel is None:
        out.append('<path class="pf-line" style="stroke: {{route}}" d="%s"/>' % ''.join(D(geo.rdp(xy_, 0.3)) for _, xy_ in run_xy))
    else:
        mine = ''.join(D(geo.rdp(xy_, 0.3)) for dd, xy_ in run_xy if dd == sel)
        other = ''.join(D(geo.rdp(xy_, 0.3)) for dd, xy_ in run_xy if dd != sel)
        if other:
            out.append('<path class="pf-ghost" d="%s"/>' % other)
        if mine:
            out.append('<path class="pf-line" style="stroke: {{route}}; stroke-width: 2.5" d="%s"/>' % mine)

    # ---- markers (positions first: phone labels keep clear of them)
    imax = max(range(len(pts)), key=lambda i_: pts[i_][1])
    raw_max_m = max((t.gps_max_m for t in tracks if t.gps_max_m is not None), default=hi)
    gx, gy = X(pts[imax][0]), Y(pts[imax][1])
    # keep the GPS-max triangle inside the frame and clear of the start disc / end square
    gx = min(max(gx, pad_l + 8), w - 8)
    if abs(gx - X(total)) < 12:
        gx = min(gx - 10, X(total) - 16)
    elif abs(gx - X(0)) < 12:
        gx = max(gx + 10, X(0) + 16)
    sx0, sy0 = X(0), Y(pts[0][1])
    exs, eys = X(total), Y(pts[-1][1])
    marker_boxes = [(sx0 - 1, sy0 - 5, sx0 + 8, sy0 + 5), (exs - 8, eys - 4, exs, eys + 4), (gx - 7, gy - 12, gx + 7, gy)]

    # ---- day band (multi-day): D-labels and TRANSFER above the plot
    band_out, band_boxes = [], []
    if len(tracks) > 1:
        off = 0
        band = []  # (priority, x, text, style) — placed without collisions after the loop
        for di, tr in enumerate(tracks):
            if di > 0:
                xx = X(off)
                if opts.get('day_band') and di in xfer_b:
                    band_out.append('<path d="M%.1f %dV%.1f" style="stroke: #66686D; stroke-width: 1; stroke-dasharray: 2 2"/>' % (xx, 18, ph))
                    band.append((1, xx, 'TRANSFER', 'fill: #66686D'))
                elif opts.get('day_band'):
                    band_out.append('<path d="M%.1f %dV%.1f" style="stroke: #8C8A83; stroke-width: 1; stroke-dasharray: 2 2"/>' % (xx, 4, ph))
                else:
                    band_out.append('<path class="pf-div" d="M%.1f %dV%.1f"/>' % (xx, top - 6, ph))
            xm = X(off + tr.total / 2)
            if opts.get('day_band'):
                band.append((0, xm, 'D%d' % (di + 1), 'fill: #45474C; font-weight: 600'))
            else:
                band_out.append('<text class="pf-ax" x="%.1f" y="%d" style="text-anchor: middle; fill: %s; font-weight: 600; stroke: #F2F1EC; stroke-width: 3px; paint-order: stroke">D%d</text>'
                                % (xm, top + 12, '#16171A' if sel in (None, di) else '#66686D', di + 1))
                half = text_w('D%d' % (di + 1), 12.1 if phone else 11, mono=True) / 2
                band_boxes.append((xm - half - 2, top + 1, xm + half + 2, top + 15))
            off += tr.total
        placed = []
        for pri, x_, txt, sty in sorted(band, key=lambda b: (b[0], b[1])):
            half = text_w(txt, 11, mono=True) / 2 + 4
            if x_ - half < pad_l - 4 or x_ + half > w + 2 or any(not (x_ + half <= a or x_ - half >= b) for a, b in placed):
                continue
            placed.append((x_ - half, x_ + half))
            band_boxes.append((x_ - half, 1, x_ + half, 15))
            band_out.append('<text class="pf-ax" x="%.1f" y="12" style="text-anchor: middle; %s">%s</text>' % (x_, sty, txt))

    # ---- elevation labels, one group per unit
    segs_xy = [(p_[0], p_[1], q_[0], q_[1]) for _, xy_ in run_xy for p_, q_ in zip(xy_, xy_[1:])]

    def hits(b):
        n_ = sum(1 for s_ in segs_xy if _seg_hits_box(s_[0], s_[1], s_[2], s_[3], b))
        return n_ + sum(3 for mb in marker_boxes + band_boxes if _box_overlap(b, mb))

    def ylabels(ticks, unit):
        """(labels placed clear of the line and markers, html)."""
        if not opts.get('ylabels', True):
            return 0, ''
        rows = [(v, yy) for v, yy in ticks if ph - yy >= 12]
        if not phone:
            return len(rows), ''.join('<text class="pf-ax" x="%d" y="%.1f" style="text-anchor: end; dominant-baseline: central">%s%s</text>'
                                      % (pad_l - 8, yy, fmt_int(v), unit if k == 0 else '') for k, (v, yy) in enumerate(rows))
        def spots(yy):
            # the plot edges first (above the grid line, then below it), then along the line inside the plot
            above = yy - 4 if yy - 4 >= 10 else yy + 13
            ys_ = [above] + ([yy + 13] if above != yy + 13 and yy + 16 <= ph - 1 else [])
            return ([(x_, y_, a_) for y_ in ys_ for x_, a_ in ((2, 'start'), (w - 2, 'end'))] +
                    [(w * f_, y_, 'middle') for y_ in ys_ for f_ in (0.25, 0.5, 0.75)])

        def place(v, yy, first, taken):
            best = None
            txt = fmt_int(v) + (unit if first else '')
            tw_ = text_w(txt, 12.1, mono=True)
            for x_, ly_, anc in spots(yy):
                lx0 = x_ if anc == 'start' else (x_ - tw_ if anc == 'end' else x_ - tw_ / 2)
                b = (lx0 - 2, ly_ - 13, lx0 + tw_ + 2, ly_ + 5)
                if any(_box_overlap(b, tb) for tb in taken):
                    continue  # never on another label
                n_ = hits(b)
                if best is None or n_ < best[0]:
                    best = (n_, x_, ly_, anc, txt, b)
                if n_ == 0:
                    break
            return best
        kept, dropped = [], []
        for v, yy in rows:
            best = place(v, yy, not kept, [k_[5] for k_ in kept])
            if best and best[0] == 0:
                kept.append(best)
            else:
                dropped.append((v, yy))
        # never fewer than two labels: the least-colliding dropped ones come back (still never on another label)
        n_clear = len(kept)
        while len(kept) < 2 and dropped:
            cands_ = [(place(v, yy, not kept, [k_[5] for k_ in kept]), (v, yy)) for v, yy in dropped]
            cands_ = [c_ for c_ in cands_ if c_[0]]
            if not cands_:
                break
            best, row = min(cands_, key=lambda c_: c_[0][0])
            kept.append(best)
            dropped.remove(row)
        kept.sort(key=lambda z: z[2])
        out_ = []
        for k, (_, x_, ly_, anc, txt, _b) in enumerate(kept):
            txt = txt[:-len(unit)] if txt.endswith(unit) else txt
            out_.append('<text class="pf-ax" x="%d" y="%.1f" style="text-anchor: %s; %s">%s%s</text>'
                        % (x_, ly_, anc, AX_HALO, txt, unit if k == 0 else ''))
        return n_clear, ''.join(out_)

    def settle(le0, f, steps, unit):
        """Phones: the first step (the chosen one, then finer, then coarser; >= 20 px apart) whose labels include two
        clear of the line; else the chosen step with its least-colliding labels."""
        order = [le0] + [s_ for s_ in sorted(steps, reverse=True) if s_ < le0] + [s_ for s_ in sorted(steps) if s_ > le0]
        first_ = None
        for le in order:
            if le != le0 and (not phone or not roomy(le, f) or n_labels(le, f) < 2):
                continue
            ticks = elev_ticks(le, f)
            n_clear, html_ = ylabels(ticks, unit)
            first_ = first_ or (ticks, html_)
            if not phone or n_clear >= 2:
                return ticks, html_
        return first_
    ft_ticks, ft_html = settle(lab_ft, 1, (50, 100, 200, 250, 500, 1000, 2000, 4000, 8000), ' ft')
    m_ticks, m_html = settle(lab_m, fm, ELEV_STEPS_M, ' m')
    out[grid_i] = ''.join('<g class="%s">%s</g>' % (cls, ''.join('<path class="pf-grid" d="M%d %.1fH%d"/>' % (pad_l, yy, w) for _, yy in ticks))
                          for cls, ticks in (('u-mi', ft_ticks), ('u-km', m_ticks)))
    out.append('<g class="u-mi">%s</g><g class="u-km">%s</g>' % (ft_html, m_html))
    out.extend(band_out)

    # ---- distance axis, one group per unit
    out.append('<path class="pf-axk" d="M%d %.1fH%d"/>' % (pad_l, ph + 0.5, w))
    ly = ph + (23 if opts.get('grade', True) else 15)
    tot_mi, tot_km = total / MI, total / 1000.0

    def dist_ticks(tot_u, unit_m, ev, unit):
        ticks = [k * ev for k in range(int(tot_u / ev + 1e-6) + 1)]
        labs = []
        for m in ticks:
            xx = X(m * unit_m)
            anchor = 'start' if m == 0 else ('end' if xx > w - 20 else 'middle')
            num = '%g' % round(m, 2)
            if phone:  # the unit rides on the last tick ('12 mi'); the first reads '0'
                lab = (num + ' ' + unit) if m == ticks[-1] else num
            else:
                lab = ('0 ' + unit) if m == 0 else num
            tw = text_w(lab, 12.1 if phone else 11, mono=True)
            x0 = xx if anchor == 'start' else (xx - tw if anchor == 'end' else xx - tw / 2)
            labs.append([xx, anchor, lab, x0, x0 + tw, True])
        # the last label (it carries the unit on phones) wins: drop any earlier label that would touch its neighbour
        keep_x0 = None
        for L in reversed(labs):
            if keep_x0 is not None and L[4] + 6 > keep_x0:
                L[5] = False
                continue
            keep_x0 = L[3]
        o_ = []
        for xx, anchor, lab, _x0, _x1, show in labs:
            o_.append('<path class="pf-axk" d="M%.1f %.1fv4"/>' % (xx, ph))
            if show:
                o_.append('<text class="pf-ax pf-xl" x="%.1f" y="%.1f" style="text-anchor: %s">%s</text>' % (xx, ly, anchor, lab))
        return ''.join(o_)
    ev_mi = opts.get('axis_every_mi') or axis_step(tot_mi, w)
    ev_km = opts.get('axis_every_km') or axis_step(tot_km, w)
    out.append('<g class="u-mi">%s</g><g class="u-km">%s</g>' % (dist_ticks(tot_mi, MI, ev_mi, 'mi'), dist_ticks(tot_km, 1000.0, ev_km, 'km')))

    gh = opts.get('grade_h', 8)
    if opts.get('grade', True):
        gy0 = ph + 1
        bin_m = 0.25 * MI
        gruns = []
        d0 = 0.0
        i_ = 0
        while d0 < total:
            d1 = min(total, d0 + bin_m)
            gsum, glen = 0.0, 0.0
            while i_ < len(pts) - 1 and pts[i_ + 1][0] <= d1:
                seg = pts[i_ + 1][0] - pts[i_][0]
                if seg > 0 and pts[i_][0] >= d0:
                    gsum += abs(pts[i_ + 1][1] - pts[i_][1])
                    glen += seg
                i_ += 1
            g = gsum / glen * 100 if glen > 0 else 0
            c = 0 if g < 10 else (1 if g < 20 else (2 if g < 30 else 3))
            if gruns and gruns[-1][2] == c:
                gruns[-1][1] = d1
            else:
                gruns.append([d0, d1, c])
            d0 = d1
        # merge runs narrower than 12px into the previous run
        merged = []
        for r in gruns:
            if merged and (X(r[1]) - X(r[0])) < 12:
                merged[-1][1] = r[1]
            else:
                merged.append(r)
        cols = ['#D6D4CC', '#B9B4A7', '#8C8A83', '#16171A']
        for a, b, c in merged:
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="6" style="fill: %s"/>' % (X(a), gy0, max(0.5, X(b) - X(a)), cols[c]))
    out.append('<path d="M%.1f %.1fl6 10h-12z" style="fill: {{route}}; stroke: #FFFFFF; stroke-width: 1.5; paint-order: stroke"/>' % (gx, gy - 12))
    info = {'gps_max_ft': raw_max_m * FT, 'min_ft': lo * FT, 'total_mi': tot_mi, 'gx': gx, 'gy': gy,
            'gps_max_mi': pts[imax][0] / MI, 'y_lo': y_lo, 'y_hi': y_hi, 'pad_l': pad_l}
    if opts.get('scrub_mi') is not None:
        dm = opts['scrub_mi'] * MI
        k = min(range(len(pts)), key=lambda i_: abs(pts[i_][0] - dm))
        sx_, sy_ = X(pts[k][0]), Y(pts[k][1])
        txt = '%.1f MI · %s FT' % (pts[k][0] / MI, fmt_int(pts[k][1] * FT))
        tw = text_w(txt, 12, mono=True) + 16
        bx = sx_ + 10 if sx_ + 10 + tw < w else sx_ - 10 - tw
        by = max(top, sy_ - 10 - 24)
        out.append('<path d="M%.1f %dV%.1f" style="stroke: #16171A; stroke-width: 1"/>' % (sx_, top, ph))
        out.append('<circle cx="%.1f" cy="%.1f" r="3.5" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 1.5"/>' % (sx_, sy_))
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="24" style="fill: #16171A"/><text x="%.1f" y="%.1f" style="font: 500 12px/1 %s; fill: #F2F1EC; dominant-baseline: central">%s</text>'
                   % (bx, by, tw, bx + 8, by + 12.5, MONO, txt))
        info['scrub'] = txt
    if opts.get('scrub'):
        dmax = pts[imax][0]
        k0 = max(i_ for i_ in range(len(pts)) if pts[i_][0] <= max(0, dmax - 150))
        g = abs(pts[imax][1] - pts[k0][1]) / max(dmax - pts[k0][0], 1) * 100
        txt = '%.1f mi · %s ft · %d%% grade' % (dmax / MI, fmt_int(raw_max_m * FT), round(g))
        tw = text_w(txt, 12, mono=True) + 16
        bx = gx + 10 if gx + 10 + tw < w else gx - 10 - tw
        out.append('<path d="M%.1f %dV%.1f" style="stroke: #16171A; stroke-width: 1"/>' % (gx, top, ph))
        fy = ph - 30
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="24" style="fill: #16171A"/><text x="%.1f" y="%.1f" style="font: 500 12px/1 %s; fill: #F2F1EC; dominant-baseline: central">%s</text>'
                   % (bx, fy, tw, bx + 8, fy + 12.5, MONO, txt))
        info['scrub'] = txt
    out.append('<circle cx="%.1f" cy="%.1f" r="3.5" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 1.5"/>' % (sx0 + 3.5, sy0))
    out.append('<rect x="%.1f" y="%.1f" width="7" height="7" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 1.5"/>' % (exs - 8, eys - 3.5))
    H = ph + 22 + (gh + 4 if opts.get('grade', True) else 0)
    vpx = (ph - top) / ((y_hi - y_lo) / FT)
    hpx = pw / total
    info['vx'] = vpx / hpx
    info['h'] = H
    svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d"%s role="img" aria-label="%s" style="display: block; overflow: visible">%s</svg>'
           % (w, H, w, H, ' class="pf-ph"' if phone else '', esc(opts.get('aria', 'Elevation profile')), ''.join(out)))
    write_frag(name, svg)
    json.dump(info, open(os.path.join(FRAG, name + '.meta.json'), 'w'))
    return info


# ---------------------------------------------------------------- glyphs & sparklines
def render_glyph(name, track_or_tracks, w, h, cat, pad=6, stroke=2.0, bg=None, planned=False, style=None, transfer_dash=None,
                 transfers=(), tiny_r=3):
    """Track glyph (list rows, cards). transfers: [(a, b)] day pairs joined by a content road transfer, drawn as a dashed
    connector (transfer_dash) from day a's end to day b's start; nothing else is connected (separate crags stay apart).
    tiny_r: with several tracks, a day whose drawing would be under 2 * tiny_r px across becomes a disc of that radius
    (None: always a line, e.g. a thru-hike's many short days)."""
    trs = track_or_tracks if isinstance(track_or_tracks, list) else [track_or_tracks]
    pts_all = [[(p[0], p[1]) for p in decimate(t.raw, 1500)] for t in trs]
    proj = Proj(geo.bbox_of(pts_all), w - 2 * pad, h - 2 * pad, pad=0)
    col = CAT[cat] if cat in CAT else cat
    parts = []
    xys = [[(x + pad, y + pad) for x, y in (proj.xy(a, b) for a, b in pts)] for pts in pts_all]
    for a_, b_ in transfers or ():
        if 0 <= a_ < len(xys) and 0 <= b_ < len(xys) and xys[a_] and xys[b_]:
            (x1, y1), (x2, y2) = xys[a_][-1], xys[b_][0]
            parts.append('<path d="M%.1f %.1fL%.1f %.1f" style="stroke: #66686D; stroke-width: 1; stroke-dasharray: %s; stroke-linecap: butt; fill: none"/>'
                         % (x1, y1, x2, y2, transfer_dash or '2 2'))
    for pts, xy in zip(pts_all, xys):
        if not xy:
            continue
        if tiny_r and len(xys) > 1:
            xs_, ys_ = [q[0] for q in xy], [q[1] for q in xy]
            if math.hypot(max(xs_) - min(xs_), max(ys_) - min(ys_)) < 2 * tiny_r:
                mx_, my_ = xy[len(xy) // 2]
                parts.append('<circle cx="%.1f" cy="%.1f" r="%g" style="fill: %s; stroke: #EEECE6; stroke-width: 1.5"/>'
                             % (mx_, my_, tiny_r, '#45474C' if planned else col))
                continue
        d = runs_d(xy, geo.cumdist(pts), 0.25)
        if planned:
            parts.append('<path class="gl-trk" style="stroke: #45474C; stroke-width: 2; stroke-dasharray: 6 4; stroke-linecap: butt" d="%s"/>' % d)
        else:
            parts.append('<path class="gl-trk" style="stroke: %s; stroke-width: %.1f" d="%s"/>' % (col, stroke, d))
    bgrect = '<rect width="%d" height="%d" style="fill: %s"/>' % (w, h, bg) if bg else ''
    svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d" aria-hidden="true" style="display: block; flex-shrink: 0%s">%s%s</svg>'
           % (w, h, w, h, '; ' + style if style else '', bgrect, ''.join(parts)))
    write_frag(name, svg)
    return svg


def render_tile(name, track, w, h, cat, osm_detail=None, extra_tracks=(), osm_data=None, planned=False, tracks=None, transfers=(),
                tiny_disc=4):
    """Mini-topo tile: map-paper, index contours only, water fill, track 2.5px on a 1.5px casing."""
    trs = tracks or [{'track': track, 'style': 'planned' if planned else 'cat', 'cat': cat, 'width': 2.5, 'trim': DEFAULT_TRIM}]
    spec = {'name': name, 'w': w, 'h': h, 'tracks': trs,
            'pad': 0.12 if tracks else 0.14, 'hillshade': False, 'osm': osm_detail, 'legend': False, 'scale': False, 'north': False,
            'graticule': False, 'miles': False, 'chevrons': False, 'startend': False, 'gpsmax': False,
            'contour_labels': False, 'contour_density': 1.6, 'contour_step': 2.0, 'minor_contours': False, 'peaks_max': 0, 'places': False,
            'water_labels': 0, 'trails': False, 'road_levels': (), 'min_extent_m': 900, 'trim': DEFAULT_TRIM, 'osm_data': osm_data,
            'transfers': list(transfers), 'transfer_dash': '2 3', 'transfer_w': 1, 'transfer_label': False, 'split_base': False,
            'tiny_disc': tiny_disc}
    meta = render_map(spec)
    p = os.path.join(FRAG, name + '.svg.html')
    s = open(p).read()
    s = s.replace('overflow: hidden">', 'overflow: hidden"><rect width="%d" height="%d" style="fill: #EEECE6"/>' % (w, h), 1)
    s = s.replace('style="position: absolute; left: 0; top: 0; display: block; overflow: hidden"', 'style="display: block; overflow: hidden; flex-shrink: 0"')
    s = s.replace('role="img"', 'aria-hidden="true"')
    open(p, 'w').write(s)
    return meta


def render_sparkline(name, track, w, h, color='#45474C', stroke=1.5, domain=None):
    eles = track.ele
    cd = track.cd
    lo, hi = domain if domain else (min(eles), max(eles))
    step = max(1, len(eles) // (w * 2))
    xy = [(cd[i] / track.total * (w - 2) + 1, h - 1 - (eles[i] - lo) / max(hi - lo, 1) * (h - 2)) for i in range(0, len(eles), step)]
    svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d" aria-hidden="true" style="display: block; flex-shrink: 0">'
           '<path d="%s" style="fill: none; stroke: %s; stroke-width: %s; stroke-linejoin: round"/></svg>'
           % (w, h, w, h, D(geo.rdp(xy, 0.2)), color, stroke))
    write_frag(name, svg)
    return svg


def render_speed_chart(name, track, w, h=96):
    """Speed over elapsed time as a 3-minute distance/time average (mph); robust scale; stopped bands only if stops >= 2 min."""
    pts = [p_ for p_ in track.raw if p_[3] is not None]
    t0 = pts[0][3]
    span = max(pts[-1][3] - t0, 1)
    T = [p_[3] - t0 for p_ in pts]
    cum = [0.0]
    for a_, b_ in zip(pts, pts[1:]):
        cum.append(cum[-1] + geo.hav(a_, b_))
    idx = [i_ for i_ in range(len(pts)) if 90 <= T[i_] <= span - 90]
    if len(idx) < 5:
        idx = list(range(len(pts)))
    series = []
    a_i = b_i = 0
    for i_ in idx:
        while a_i < len(T) - 1 and T[a_i] < T[i_] - 90:
            a_i += 1
        while b_i < len(T) - 1 and T[b_i + 1] <= T[i_] + 90:
            b_i += 1
        dt = T[b_i] - T[a_i]
        if dt < 60:
            continue
        series.append((T[i_], (cum[b_i] - cum[a_i]) / dt * 2.23694))
    if not series:
        series = [(0, 0.0), (span, 0.0)]
    vs = sorted(v for _, v in series)
    vref = vs[int(0.98 * (len(vs) - 1))] or 0.5
    step = next((s_ for s_ in (0.5, 1, 2, 5, 10) if math.ceil(vref * 1.25 / s_) <= 4), 10)
    top_v = max(step, math.ceil(vref * 1.25 / step) * step)
    phone = w < 500  # no gutter: y labels inside the plot on a paper halo, 12px lettering (.pf-ph), unit on the last tick
    pad_l = 0 if phone else 72
    pw = w - pad_l
    top, ph = (14 if phone else 6), h - 26

    def X(t):
        return pad_l + t / span * pw

    def Y(v):
        return top + (1 - min(v, top_v) / top_v) * (ph - top)
    parts = []
    stops = []
    run = None
    for t, v in series:
        if v < 0.5:
            run = run or [t, t]
            run[1] = t
        else:
            if run and run[1] - run[0] >= 60:
                stops.append(run)
            run = None
    if run and run[1] - run[0] >= 60:
        stops.append(run)
    stopped_total = sum(b - a for a, b in stops)
    if stopped_total >= 120:
        for a, b in stops:
            parts.append('<rect x="%.1f" y="%d" width="%.1f" height="%.1f" style="fill: #E8E6DF"/>' % (X(a), top, X(b) - X(a), ph - top))
    line = geo.rdp([(X(t), Y(v_)) for t, v_ in series], 0.4)
    segs_xy = [(p_[0], p_[1], q_[0], q_[1]) for p_, q_ in zip(line, line[1:])]
    labels = []
    taken = []
    vals_ = [k_ * step for k_ in range(1, int(top_v / step + 1e-9) + 1)]
    for v in (sorted(vals_, reverse=True) if phone else vals_):  # phones: top-down, so the unit rides on the top label
        yy = Y(v)
        parts.append('<path class="pf-grid" d="M%d %.1fH%d"/>' % (pad_l, yy, w))
        if phone:
            # inside the plot: the first spot clear of the line (left edge, right edge, under the grid line, then along
            # it); a value that fits nowhere is left off (the grid line stays). The unit rides on the top label placed.
            txt = ('%g mph' % v) if not taken else ('%g' % v)
            tw_ = text_w(txt, 12.1, mono=True)
            above = yy - 4 if yy - 4 >= 10 else yy + 13
            ys_ = [above] + ([yy + 13] if above != yy + 13 and yy + 16 <= ph - 1 else [])
            for x_, ly_, anc in ([(x0, y_, a_) for y_ in ys_ for x0, a_ in ((2, 'start'), (w - 2, 'end'))] +
                                 [(w * f_, y_, 'middle') for y_ in ys_ for f_ in (0.25, 0.5, 0.75)]):
                lx0 = x_ if anc == 'start' else (x_ - tw_ if anc == 'end' else x_ - tw_ / 2)
                bx_ = (lx0 - 2, ly_ - 13, lx0 + tw_ + 2, ly_ + 5)
                if any(_box_overlap(bx_, tb) for tb in taken) or any(_seg_hits_box(s_[0], s_[1], s_[2], s_[3], bx_) for s_ in segs_xy):
                    continue
                labels.append('<text class="pf-ax" x="%d" y="%.1f" style="text-anchor: %s; %s">%s</text>' % (x_, ly_, anc, AX_HALO, txt))
                taken.append(bx_)
                break
        else:
            txt = ('%g mph' % v) if abs(v - top_v) < 1e-9 else ('%g' % v)
            labels.append('<text class="pf-ax" x="%d" y="%.1f" style="text-anchor: end; dominant-baseline: central">%s</text>' % (pad_l - 8, yy, txt))
    if not phone:  # on phones the axis line itself reads as 0
        labels.append('<text class="pf-ax" x="%d" y="%.1f" style="text-anchor: end; dominant-baseline: central">0</text>' % (pad_l - 8, Y(0)))
    parts.append('<path class="pf-line" style="stroke: {{route}}; stroke-width: 2" d="%s"/>' % D(line))
    parts.extend(labels)
    parts.append('<path class="pf-axk" d="M%d %.1fH%d"/>' % (pad_l, ph + 0.5, w))
    mins = span / 60
    # minute ticks: the finest step whose labels stay >= 40 px apart ('240' is three digits); the last (it carries the
    # unit on phones) wins where two would touch
    every = next((e_ for e_ in (5, 10, 15, 20, 30, 60, 120, 240) if pw / max(mins / e_, 1) >= 40), 480)
    ticks = [k_ * every for k_ in range(int(mins / every + 1e-6) + 1)]
    labs = []
    for m in ticks:
        x = X(m * 60)
        anchor = 'start' if m == 0 else ('end' if x > w - 20 else 'middle')
        if phone:
            lab = ('%d min' % m) if m == ticks[-1] else '%d' % m
        else:
            lab = '0 min' if m == 0 else '%d' % m
        tw_ = text_w(lab, 12.1 if phone else 11, mono=True)
        x0 = x if anchor == 'start' else (x - tw_ if anchor == 'end' else x - tw_ / 2)
        labs.append([x, anchor, lab, x0, x0 + tw_, True])
    keep_x0 = None
    for L in reversed(labs):
        if keep_x0 is not None and L[4] + 6 > keep_x0:
            L[5] = False
            continue
        keep_x0 = L[3]
    for x, anchor, lab, _x0, _x1, show in labs:
        parts.append('<path class="pf-axk" d="M%.1f %.1fv4"/>' % (x, ph))
        if show:
            parts.append('<text class="pf-ax pf-xl" x="%.1f" y="%.1f" style="text-anchor: %s">%s</text>' % (x, ph + 16, anchor, lab))
    svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d"%s role="img" aria-label="Speed over the paddle, 3-minute average, in miles per hour" style="display: block; overflow: visible">%s</svg>'
           % (w, h, w, h, ' class="pf-ph"' if phone else '', ''.join(parts)))
    write_frag(name, svg)
    return {'span_min': mins, 'vmax_mph': max(v for _, v in series), 'stopped_s': stopped_total, 'top_mph': top_v}
