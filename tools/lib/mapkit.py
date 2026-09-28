"""Map, profile and glyph renderers for the Datum mockups.

Maps = hillshade/band PNG (uploaded asset) + SVG overlay fragment (classes styled by MAP_CSS).
"""
import json
import math
import os
import re

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
""" % {'mono': MONO, 'sans': SANS, 'serif': SERIF}


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
            d = geo.d_attr(s_, prec=1)
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
            parts.append(geo.d_attr(pts, closed=True))
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


LAST_OSM = {}


def render_map(spec):
    """spec keys: name, w, h, tracks:[{track, style, cat, i0,i1, pin, highlight, day}], bbox?, pad, detail,
    osm: detail level or None, legend, scale, north, graticule, miles, chevrons, startend, gpsmax, waypoints,
    skin, huts, png_scale, hillshade, peaks_max, day_labels, contour_labels, trim_m, pins, aria"""
    name = spec['name']
    w, h = spec['w'], spec['h']
    trks = spec['tracks']
    trim_m = spec.get('trim_m', 0.25 * MI)
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
    marker_pts = []

    # project tracks (decimated) for drawing
    proj_tracks = []
    for t in trks:
        tr = t['track']
        seg = tr.raw[t['i0']:t['i1'] + 1]
        cds = tr.cd[t['i0']:t['i1'] + 1]
        idx = list(range(len(seg)))
        xy = [proj.xy(p[0], p[1]) for p in seg]
        simp_eps = spec.get('track_eps', 0.35)
        proj_tracks.append((t, xy, cds, seg))
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

    def hits_track(b, pad=3):
        for x_, y_ in trk_pts:
            if b[0] - pad <= x_ <= b[2] + pad and b[1] - pad <= y_ <= b[3] + pad:
                return True
        return False

    dense_trk = []
    for pt in proj_tracks:
        xy_ = pt[1]
        for (xa, ya), (xb, yb) in zip(xy_, xy_[1:]):
            n_ = max(1, int(math.hypot(xb - xa, yb - ya) / 4))
            dense_trk.extend((xa + (xb - xa) * k / n_, ya + (yb - ya) * k / n_) for k in range(n_))

    def hits_track_dense(b, pad=3):
        return any(b[0] - pad <= x_ <= b[2] + pad and b[1] - pad <= y_ <= b[3] + pad for x_, y_ in dense_trk)

    def free(b, pad=2, track=True):
        return (not overlaps(b, boxes, pad)) and b[0] > 4 and b[2] < w - 4 and b[1] > 4 and b[3] < h - 4 and not (track and hits_track(b))

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
                d = ''.join(geo.d_attr(geo.rdp(r, 0.5)) for r in clip_runs([proj.xy(a, b) for a, b in pts], w, h))
                if d:
                    layers['water'].append('<path class="%s" d="%s"/>' % (cls, d))
        else:
            for pts, tags in geo.osm_lines(osm, lambda t: t.get('waterway') == 'river'):
                runs = [geo.rdp(r, max(0.7, peps)) for r in clip_runs([proj.xy(a, b) for a, b in pts], w, h)]
                runs = [r for r in runs if geo.path_len(r) > 30]
                if runs:
                    layers['water'].append('<path class="mk-river" d="%s"/>' % ''.join(geo.d_attr(r) for r in runs))
        # roads & trails
        road_lbls = []
        minors, majors, trails = [], [], []
        levels = spec.get('road_levels', ('motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'path', 'footway', 'track'))
        reps = max(0.6, spec.get('poly_eps', 0.4))
        for pts, tags in geo.osm_lines(osm, lambda t: 'highway' in t):
            hw = tags['highway']
            if hw not in levels:
                continue
            raw_xy = [proj.xy(a, b) for a, b in pts]
            runs, cur = [], []
            for x_, y_ in raw_xy:
                if -12 <= x_ <= w + 12 and -12 <= y_ <= h + 12:
                    cur.append((x_, y_))
                else:
                    if cur:
                        cur.append((x_, y_))
                        runs.append(cur)
                    cur = []
            if cur:
                runs.append(cur)
            runs = [geo.rdp(r, reps) for r in runs if len(r) >= 2]
            if not runs:
                continue
            xy = max(runs, key=len)
            d = ''.join(geo.d_attr(r) for r in runs)
            if hw in ('motorway', 'trunk', 'primary', 'secondary'):
                majors.append(d)
                ref = tags.get('ref') or ''
                if ref:
                    road_lbls.append((xy, ref.replace(';', ' / ')))
            elif hw in ('tertiary', 'unclassified'):
                minors.append(d)
            elif hw in ('path', 'footway', 'track') and spec.get('trails', True):
                trails.append(d)
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
    gps_pts = {}
    for idx_t, (t, xy, cds, seg) in enumerate(proj_tracks):
        tr = t['track']
        if t.get('gpsmax', spec.get('gpsmax')) and t.get('style', 'route') == 'route' and tr.imax is not None:
            gps_pts[idx_t] = proj.xy(tr.raw[tr.imax][0], tr.raw[tr.imax][1])
            gx, gy = gps_pts[idx_t]
            boxes.append((gx - 8, gy - 9, gx + 8, gy + 6))
    for idx_t, (t, xy, cds, seg) in enumerate(proj_tracks):
        style = t.get('style', 'route')
        xy_s = geo.rdp(xy, spec.get('track_eps', 0.35))
        d = geo.d_attr(xy_s)
        tr = t['track']
        oab = style == 'route' and is_out_and_back(tr)
        if style == 'route' and small and oab:
            far_i = max(range(len(xy)), key=lambda k: math.hypot(xy[k][0] - xy[0][0], xy[k][1] - xy[0][1]))
            out_leg = xy[:far_i + 1:max(1, (far_i + 1) // 400)]
            back = xy[far_i::max(1, (len(xy) - far_i) // 200)]
            dists = sorted(min(math.hypot(bx - ax, by - ay) for ax, ay in out_leg) for bx, by in back)
            if dists and dists[int(0.9 * (len(dists) - 1))] < 4:
                xy_s = geo.rdp(xy[:far_i + 1], spec.get('track_eps', 1.2))
                d = geo.d_attr(xy_s)
        if style == 'route' and spec.get('skin') and tr.ele and not small:
            # skin (ascent) dashed thin, ski (descent) solid; out-and-back legs offset apart
            segs_ = turning_segments(tr.cd, tr.ele, 30)
            asc, desc = [], []
            for a, b, dirn in segs_:
                a2, b2 = max(a, t['i0']), min(b, t['i1'])
                if b2 - a2 < 2:
                    continue
                sub = [proj.xy(p_[0], p_[1]) for p_ in tr.raw[a2:b2 + 1]]
                sub = geo.rdp(sub, 1.0 if oab else 0.5)
                if oab:
                    sub = offset_line(sub, -4 if dirn == 'up' else 4)
                (asc if dirn == 'up' else desc).append(geo.d_attr(sub))
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
            gd = ''.join(geo.d_attr(r) for r in clip_runs(xy_s, w, h))
            if gd:
                layers['track'].insert(0, '<path class="mk-trk" style="stroke: {{route}}; stroke-opacity: .35; stroke-width: 2" d="%s"/>' % gd)
        elif style == 'cat':
            op = t.get('opacity', 1)
            wdt = t.get('width', 2.5)
            case = '<path class="mk-case" style="stroke-width: %.1f" d="%s"/>' % (wdt + 3, d) if t.get('casing', True) else ''
            layers['track'].append('<g class="mk-cat"%s style="opacity: %s">%s<path class="gl-trk" style="stroke: %s; stroke-width: %.1f" d="%s"/></g>'
                                   % (' data-key="%s"' % esc(t['key']) if t.get('key') else '', op, case, CAT[t.get('cat', 'SKI')], wdt, d))
        elif style == 'planned':
            pl = ('<path class="mk-case" style="stroke-width: 5.5; stroke: #EEECE6" d="%s"/><path class="mk-trk" style="stroke: #45474C; stroke-width: 2.5; stroke-dasharray: 8 5; stroke-linecap: butt; stroke-linejoin: round" d="%s"/>' % (d, d))
            if t.get('key'):
                pl = '<g class="mk-cat mk-planned" data-key="%s">%s</g>' % (esc(t['key']), pl)
            layers['track'].append(pl)
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
                if min(math.hypot(x - xy[0][0], y - xy[0][1]), math.hypot(x - xy[-1][0], y - xy[-1][1])) < 18:
                    return True
                if gpt and math.hypot(x - gpt[0], y - gpt[1]) < 22:
                    return True
                if any(math.hypot(x - a_, y - b_) < 22 for a_, b_ in placed_discs):
                    return True
                return overlaps((x - 10, y - 10, x + 10, y + 10), boxes, 1)
            while m * MI < limit:
                if cds[0] <= m * MI <= cds[-1]:
                    pos = None
                    for dm in (0, 0.05, -0.05, 0.1, -0.1, 0.15, -0.15, 0.2, -0.2, 0.25, -0.25):
                        tgt = (m + dm) * MI
                        if not (cds[0] <= tgt <= cds[-1]):
                            continue
                        x, y, ang = along(xy, cds, tgt)
                        if not blocked(x, y):
                            pos = (x, y)
                            break
                    if pos is None:
                        pos = along(xy, cds, m * MI)[:2]
                        if gpt and math.hypot(pos[0] - gpt[0], pos[1] - gpt[1]) < 22:
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
        if idx_t in gps_pts:
            gx, gy = gps_pts[idx_t]
            at_start = None
            if not small:
                for tag_, (mx_, my_) in (('START', xy[0]), ('END', xy[-1])):
                    if math.hypot(gx - mx_, gy - my_) < 22:
                        at_start = tag_
                        gx, gy = mx_ + 13, my_
                        break
            layers['markers'].append('<path d="M%.1f %.1fl6 10h-12z" style="fill: {{route}}; stroke: #FFFFFF; stroke-width: 1.5; paint-order: stroke"/>' % (gx, gy - 6))
            marker_pts.append((gx, gy))
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
                    spec.setdefault('_prio_done', set()).add(summit)
            if spec.get('gps_label', True) and summit:
                l1, l2 = summit.upper(), 'GPS MAX %s FT' % fmt_int(tr.gps_max_m * FT)
                bw_ = max(text_w(l1, 12, 0.12), text_w(l2, 11, 0.02, True))
                placed = None
                for strict in (True, False):
                    for dx, dy in ((12, -6), (12, 8), (-12 - bw_, -6), (-12 - bw_, 8), (-bw_ / 2, -34), (-bw_ / 2, 20), (16, -20), (-16 - bw_, -20),
                                   (16, 22), (-16 - bw_, 22), (-bw_ / 2, -48), (-bw_ / 2, 34), (28, -6), (-28 - bw_, -6), (28, 14), (-28 - bw_, 14)):
                        b = (gx + dx - 2, gy + dy - 10, gx + dx + bw_ + 2, gy + dy + 18)
                        if free(b, 2, track=strict):
                            placed = (dx, dy, b)
                            break
                    if placed:
                        break
                dx, dy, b = placed or (12, -6, (gx + 10, gy - 16, gx + 14 + bw_, gy + 12))
                layers['labels'].append('<text class="mk-peak" x="%.1f" y="%.1f" style="fill: #16171A">%s</text><text class="mk-gps" x="%.1f" y="%.1f">%s</text>'
                                        % (gx + dx, gy + dy, esc(l1), gx + dx, gy + dy + 14, l2))
                boxes.append(b)
            elif spec.get('gps_label', True):
                txt = ('%s · GPS MAX %s FT' % (at_start, fmt_int(tr.gps_max_m * FT))) if at_start else ('GPS MAX %s FT' % fmt_int(tr.gps_max_m * FT))
                tw = text_w(txt, 11, 0.02, True)
                first = spec.get('gps_label_first')
                cands = [(12, 4, 'start'), (12, 18, 'start'), (-12, 4, 'end'), (12, -10, 'start'), (-12, 18, 'end'), (-12, -10, 'end'),
                         (0, -16, 'middle'), (0, 24, 'middle'), (24, 4, 'start'), (-24, 4, 'end'), (18, 30, 'start'), (-18, 30, 'end'),
                         (18, -22, 'start'), (-18, -22, 'end'), (0, -30, 'middle'), (0, 38, 'middle')]
                if first:
                    cands.insert(0, first)
                placed = None
                for strict in (True, False):
                    for dx, dy, anchor in cands:
                        bx = gx + dx if anchor == 'start' else (gx + dx - tw if anchor == 'end' else gx - tw / 2)
                        b = (bx - 2, gy + dy - 9, bx + tw + 2, gy + dy + 4)
                        if free(b, 2, track=strict):
                            placed = (dx, dy, anchor, b)
                            break
                    if placed:
                        break
                dx, dy, anchor, b = placed or (12, 4, 'start', (gx + 10, gy - 5, gx + 14 + tw, gy + 8))
                layers['labels'].append('<text class="mk-gps" x="%.1f" y="%.1f" text-anchor="%s">%s</text>' % (gx + dx, gy + dy, anchor, txt))
                boxes.append(b)
        if t.get('pin'):
            sx, sy = xy[0]
            layers['markers'].append(pin_svg(sx, sy, t.get('cat', 'SKI'), t.get('pin_num')))
            marker_pts.append((sx, sy))
            boxes.append((sx - 12, sy - 12, sx + 12, sy + 12))
        if t.get('hut_end'):
            ex, ey = xy[-1]
            hb = spec.setdefault('_hut_boxes', [])
            near = next((b_ for b_ in hb if math.hypot(b_['x'] - ex, b_['y'] - ey) < 22), None)
            if near:
                near['nums'].append(t['hut_end']['n'])
                txt = '·'.join(str(n_) for n_ in near['nums'])
                bw = text_w(txt, 11, mono=True) + 10
                layers['markers'][near['i']] = ('<rect x="%.1f" y="%.1f" width="%.1f" height="20" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 1.5; paint-order: stroke"/><text class="mk-day" x="%.1f" y="%.1f">%s</text>'
                                                % (near['x'] - bw / 2, near['y'] - 10, bw, near['x'], near['y'] + 0.5, txt))
            else:
                layers['markers'].append('<rect x="%.1f" y="%.1f" width="20" height="20" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 1.5; paint-order: stroke"/><text class="mk-day" x="%.1f" y="%.1f">%d</text>'
                                         % (ex - 10, ey - 10, ex, ey + 0.5, t['hut_end']['n']))
                hb.append({'x': ex, 'y': ey, 'nums': [t['hut_end']['n']], 'i': len(layers['markers']) - 1})
                boxes.append((ex - 11, ey - 11, ex + 11, ey + 11))
                if t['hut_end'].get('label'):
                    meta.setdefault('hut_labels', []).append((ex, ey, re.sub(r'\s+(CAS|CAF|SAC|CAI)$', '', t['hut_end']['label'])))

    if spec.get('overall_startend') and proj_tracks:
        sx, sy = proj_tracks[0][1][0]
        ex, ey = proj_tracks[-1][1][-1]
        layers['markers'].append('<rect x="%.1f" y="%.1f" width="10" height="10" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 2; paint-order: stroke"/>' % (ex - 5, ey - 5))
        layers['markers'].append('<circle cx="%.1f" cy="%.1f" r="5" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 2; paint-order: stroke"/>' % (sx, sy))
        boxes += [(sx - 8, sy - 8, sx + 8, sy + 8), (ex - 8, ey - 8, ex + 8, ey + 8)]
    # transfers (dashed connector between a day end and the next start)
    for a_i, b_i in spec.get('transfers', []):
        ax, ay = proj_tracks[a_i][1][-1]
        bx_, by_ = proj_tracks[b_i][1][0]
        layers['track'].append('<path d="M%.1f %.1fL%.1f %.1f" style="fill: none; stroke: #66686D; stroke-width: %s; stroke-dasharray: %s; stroke-linecap: butt"/>'
                               % (ax, ay, bx_, by_, spec.get('transfer_w', 1.5), spec.get('transfer_dash', '2 4')))
        if not spec.get('transfer_label', True):
            continue
        mx, my = (ax + bx_) / 2, (ay + by_) / 2
        tw = text_w('TRANSFER', 11, mono=True)
        for dy in (-8, 16, -20, 28):
            b = (mx - tw / 2 - 2, my + dy - 9, mx + tw / 2 + 2, my + dy + 3)
            if free(b, 2, track=False):
                layers['labels'].append('<text class="mk-lbl" x="%.1f" y="%.1f" text-anchor="middle">TRANSFER</text>' % (mx, my + dy))
                boxes.append(b)
                break

    # waypoints
    for n, (lat, lon) in enumerate(spec.get('waypoints', []), 1):
        x, y = proj.xy(lat, lon)
        layers['markers'].append('<circle cx="%.1f" cy="%.1f" r="11" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 1.5; paint-order: stroke"/><text class="mk-numw" x="%.1f" y="%.1f">%d</text>' % (x, y, x, y + 0.5, n))
        marker_pts.append((x, y))
        boxes.append((x - 12, y - 12, x + 12, y + 12))
    # hut labels
    for ex, ey, lbl in meta.get('hut_labels', []):
        tw = text_w(lbl, 12)
        placed = False
        for strict in (True, False):
            for dx, dy, anchor in ((14, 4, 'start'), (-14, 4, 'end'), (0, -16, 'middle'), (0, 24, 'middle'), (14, -12, 'start'),
                                   (-14, -12, 'end'), (14, 20, 'start'), (-14, 20, 'end'), (0, -30, 'middle'), (0, 38, 'middle')):
                bx = ex + dx if anchor == 'start' else (ex + dx - tw if anchor == 'end' else ex - tw / 2)
                b = (bx, ey + dy - 10, bx + tw, ey + dy + 3)
                if free(b, 2, track=strict):
                    layers['labels'].append('<text class="mk-hut" x="%.1f" y="%.1f" text-anchor="%s">%s</text>' % (ex + dx, ey + dy, anchor, esc(lbl)))
                    boxes.append(b)
                    placed = True
                    break
            if placed:
                break
    # day labels: route-ink text beside the track, no boxes
    if spec.get('day_labels', True):
        for idx_t, (t, xy, cds, seg) in enumerate(proj_tracks):
            if not t.get('day_label'):
                continue
            lbl = 'D%d' % t['day_label']
            tw = text_w(lbl, 11, mono=True) + 2
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
                            done = True
                            break
                    if done:
                        break
                if done:
                    break

    # scale bar: compact single-unit bar in the freest corner
    if spec.get('scale', True):
        max_px = 80 if w <= 400 else 120
        mi_len, mi_m = nice_len(max_px * proj.m_per_px, 'mi')
        spec['_scale'] = None
        for attempt in range(4):
            bar_px = mi_m / proj.m_per_px
            lab_w_ = text_w('%g mi' % mi_len, 11, mono=True)
            if bar_px < text_w('0', 11, mono=True) + 8 + lab_w_:
                bw_ = bar_px + 6 + lab_w_ + 24
            else:
                bw_ = bar_px + 24
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
            if best[0] == 0 or spec.get('scale_corner') or attempt == 3:
                spec['_scale'] = (best[1], best[2], mi_len, bar_px)
                boxes.append(best[2])
                break
            # step down to the next nice length
            smaller = [c for c in (0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 20, 50, 100) if c < mi_len]
            if not smaller:
                spec['_scale'] = (best[1], best[2], mi_len, bar_px)
                boxes.append(best[2])
                break
            mi_len = smaller[-1]
            mi_m = mi_len * MI
        spec['_scale_corner'] = spec['_scale'][0]

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
                    pin_ = ('<a class="mk-pin" href="%s" data-key="%s" aria-label="%s"><title>%s</title><circle class="mk-hit" cx="%.1f" cy="%.1f" r="22" style="fill: transparent"/>%s</a>'
                            % (esc(pn['href']), esc(pn.get('key', '')), esc(pn.get('title', '')), esc(pn.get('title', '')), x, y, pin_))
                layers['pins'].append(pin_)
            else:
                n = len(c['items'])
                cats_ = set(i_['cat'] for i_ in c['items'])
                ring = CAT[list(cats_)[0]] if len(cats_) == 1 else '#16171A'
                layers['pins'].append('<g class="mk-cluster" aria-hidden="true" data-keys="%s"><title>%s</title><circle class="mk-hit" cx="%.1f" cy="%.1f" r="22" style="fill: transparent"/><circle cx="%.1f" cy="%.1f" r="11" style="fill: #F2F1EC; stroke: %s; stroke-width: 2"/><text x="%.1f" y="%.1f" style="font: 600 12px/1 %s; fill: #16171A; text-anchor: middle; dominant-baseline: central">%d</text></g>'
                                      % (esc(' '.join(i_.get('key', '') for i_ in c['items'])), esc('; '.join(i_.get('title', '') for i_ in c['items'])), x, y, x, y, ring, x, y + 0.5, MONO, n))
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
            if not (6 < x < w - 6 and 6 < y < h - 6):
                continue
            txt = tags['name'].upper()
            tw = text_w(txt, 12, 0.12)
            ok = False
            strict_track = spec.get('prio_avoid_track') or spec.get('overview_labels')
            for pad_ in ((4,) if spec.get('overview_labels') else (2, 1)):
                for dx, dy, anchor in ((8, 4, 'start'), (-8, 4, 'end'), (0, -10, 'middle'), (0, 19, 'middle'), (8, -8, 'start'), (-8, -8, 'end'), (8, 16, 'start'), (-8, 16, 'end')):
                    bx = x + dx if anchor == 'start' else (x + dx - tw if anchor == 'end' else x - tw / 2)
                    b = (bx - 1, y + dy - 10, bx + tw + 1, y + dy + 3)
                    if not overlaps(b, boxes, pad_) and b[0] > 6 and b[2] < w - 6 and b[1] > 6 and b[3] < h - 6 and \
                            not (strict_track and hits_track(b, 6 if spec.get('overview_labels') else 2)):
                        layers['labels'].append('<path class="mk-tri" d="M%.1f %.1fl3.5 6h-7z"/><text class="mk-peak" x="%.1f" y="%.1f" text-anchor="%s" style="fill: #16171A">%s</text>'
                                                % (x, y - 3.5, x + dx, y + dy, anchor, esc(txt)))
                        boxes.append(b)
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
            for dx, dy, anchor in ((8, 4, 'start'), (-8, 4, 'end'), (0, -9, 'middle'), (0, 17, 'middle')):
                bx = x + dx if anchor == 'start' else (x + dx - tw if anchor == 'end' else x - tw / 2)
                b = (bx - 1, y + dy - 10, bx + tw + 1, y + dy + 3)
                if not overlaps(b, boxes, 8) and b[0] > 6 and b[2] < w - 6 and b[1] > 6 and b[3] < h - 6 and not avoid((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, max(8, tw / 2 - 4)):
                    layers['labels'].append('<path class="mk-tri" d="M%.1f %.1fl3.5 6h-7z"/><text class="mk-peak" x="%.1f" y="%.1f" text-anchor="%s">%s</text>'
                                            % (x, y - 3.5, x + dx, y + dy, anchor, esc(txt)))
                    boxes.append(b)
                    boxes.append((x - 4, y - 4, x + 4, y + 3))
                    n_ok += 1
                    break
        # places
        if spec.get('places', True):
            cand = []
            txy = [p for pt in proj_tracks for p in pt[1][::10]] + [tuple(c) for c in marker_pts]
            rank = {'city': 0, 'town': 1, 'village': 2}
            allow = spec.get('places_allow')
            for (lat, lon), tags in geo.osm_nodes(osm, lambda t: t.get('place') in (('city', 'town', 'village', 'hamlet') if allow else ('city', 'town', 'village')) and t.get('name')):
                if allow is not None and tags['name'] not in allow:
                    continue
                x, y = proj.xy(lat, lon)
                dmin = min((math.hypot(x - a, y - b) for a, b in txy), default=0)
                cand.append((rank.get(tags.get('place'), 3) if spec.get('places_by_rank') else 0, dmin, x, y, tags))
            cand.sort(key=lambda c: (c[0], c[1]))
            n_places = 0
            seen_pl = set()
            pin_xy = [proj.xy(pn['lat'], pn['lon']) for pn in spec.get('pins', [])]
            for _, _, x, y, tags in cand:
                if n_places >= (99 if spec.get('places_allow') else spec.get('places_max', 8)):
                    break
                if spec.get('places_near_pins') and not any(math.hypot(x - a_, y - b_) < spec['places_near_pins'] for a_, b_ in pin_xy):
                    continue
                if tags['name'] in seen_pl:
                    continue
                seen_pl.add(tags['name'])
                txt = tags['name']
                tw = text_w(txt, 12)
                b = (x + 7, y - 7, x + 7 + tw, y + 7)
                if 20 < x < w - 20 - tw and 20 < y < h - 20 and not overlaps(b, boxes, 3):
                    layers['labels'].append('<circle cx="%.1f" cy="%.1f" r="3.5" style="fill: #EEECE6; stroke: #45474C; stroke-width: 1.5"/><text class="mk-place" x="%.1f" y="%.1f">%s</text>'
                                            % (x, y, x + 8, y + 4, esc(txt)))
                    boxes.append(b)
                    n_places += 1
        # water labels
        water_named.sort(key=lambda z: -z[0])
        seen = set()
        manual = set(txt_ for _, _, txt_ in spec.get('extra_water_labels', []))
        for area, rings_xy, nm in water_named[:spec.get('water_labels', 6)]:
            if nm in seen or nm in manual:
                continue
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
                if b[0] > 4 and b[2] < w - 4 and b[1] > 4 and b[3] < h - 4 and not overlaps(b, boxes, 3) and not hits_track_dense(b, 6):
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
            tw = text_w(txt, 11, mono=True)
            b = (mid[0] - tw / 2 - 3, mid[1] - 8, mid[0] + tw / 2 + 3, mid[1] + 8)
            if 10 < b[0] and b[2] < w - 10 and 10 < b[1] and b[3] < h - 10 and not overlaps(b, boxes, 4) and not hits_track(b, 24):
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
        order = ['base', 'track', 'markers', 'labels']
    else:
        order = ['base', 'water', 'contours', 'lines', 'track', 'markers', 'labels']
    body = ''.join(''.join(layers[k]) for k in order) + ''.join(fur)
    if layers['pins']:
        svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d" role="group" aria-label="%s" '
               'style="position: absolute; left: 0; top: 0; display: block; overflow: hidden"><g aria-hidden="true">%s</g>%s</svg>') % (w, h, w, h, esc(aria), body, ''.join(layers['pins']))
    else:
        svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s" '
               'style="position: absolute; left: 0; top: 0; display: block; overflow: hidden">%s</svg>') % (w, h, w, h, esc(aria), body)
    write_frag(name, svg)
    meta['bytes'] = len(svg)
    meta['total_mi'] = total_mi
    json.dump(meta, open(os.path.join(FRAG, name + '.meta.json'), 'w'), default=str)
    return meta


def nice_len(max_m, units):
    unit_m = MI if units == 'mi' else 1000.0
    cands = [0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 20, 50, 100, 200]
    best = cands[0]
    for c in cands:
        if c * unit_m <= max_m:
            best = c
    return best, best * unit_m


def scale_bar_compact(corner, box, mi_len, bar_px):
    x0, y0 = box[0] + 12, box[1] + 22
    seg = bar_px / 2
    parts = []
    for k in range(2):
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="5" style="fill: %s; stroke: #16171A; stroke-width: .75"/>'
                     % (x0 + k * seg, y0, seg, '#16171A' if k == 0 else '#FFFFFF'))
    halo = 'stroke: #EEECE6; stroke-width: 3px; paint-order: stroke; stroke-linejoin: round; fill: #45474C'
    lab = '%g mi' % mi_len
    parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" style="%s; text-anchor: start">0</text>' % (x0, y0 - 5, halo))
    if bar_px < text_w('0', 11, mono=True) + 8 + text_w(lab, 11, mono=True):
        parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" style="%s; text-anchor: start">%s</text>' % (x0 + bar_px + 6, y0 + 5, halo, lab))
    else:
        parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" style="%s; text-anchor: end">%s</text>' % (x0 + bar_px, y0 - 5, halo, lab))
    return ''.join(parts)


def scale_bar(proj, w, h, corner='br'):
    max_px = 180
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
    parts.append('<text class="mk-lbl" x="%.1f" y="%.1f" text-anchor="start" style="stroke-width: 0; fill: #45474C">%s km</text>' % (x0 + km_px - 4, y0 + 21, lab(km_len)))
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
def render_profile(name, tracks, w, plot_h, opts):
    """Elevation profile with a left y-axis gutter. Fragment size stays w x H (H unchanged vs earlier renders)."""
    pts = []  # (dist_m, ele_m, day)
    off = 0.0
    for di, tr in enumerate(tracks):
        for d, e in zip(tr.cd, tr.ele):
            pts.append((off + d, e, di))
        off += tr.total
    total = off
    eles = [p[1] for p in pts]
    lo, hi = min(eles), max(eles)
    lo_ft, hi_ft = lo * FT, hi * FT
    rng = max(hi_ft - lo_ft, 1)
    pad_l = 72
    pw = w - pad_l
    top = 24 if opts.get('day_band') else 8
    ph = plot_h
    y_lo = lo_ft - 0.06 * rng
    y_hi = hi_ft + 0.10 * rng
    lab_every = opts.get('label_every_ft') or (1000 if rng > 4000 else 500)
    max_lab = 3 if plot_h <= 96 else 5
    while True:
        n_ticks = int(math.floor(y_hi / lab_every) - math.ceil(y_lo / lab_every)) + 1
        if n_ticks <= max_lab or lab_every >= 8000:
            break
        lab_every *= 2

    def X(d):
        return pad_l + d / total * pw

    def Y(e_m):
        return top + (y_hi - e_m * FT) / (y_hi - y_lo) * (ph - top)
    step = max(1, len(pts) // (w * 2))
    sp = pts[::step] + [pts[-1]]
    out = []
    uid = name.replace('-', '_')
    out.append('<defs><pattern id="%s_hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
               '<rect width="5" height="5" style="fill: #E2DFD6"/><path d="M0 0V5" style="stroke: #66686D; stroke-width: 1"/></pattern></defs>' % uid)
    ylabels = []
    v = math.floor(y_hi / lab_every) * lab_every
    first_tick = True
    while v >= y_lo - 0.1:
        yy = Y(v / FT)
        out.append('<path class="pf-grid" d="M%d %.1fH%d"/>' % (pad_l, yy, w))
        if opts.get('ylabels', True) and ph - yy >= 12:
            ylabels.append('<text class="pf-ax" x="%d" y="%.1f" style="text-anchor: end; dominant-baseline: central">%s%s</text>'
                           % (pad_l - 8, yy, fmt_int(v), ' ft' if first_tick else ''))
            first_tick = False
        v -= lab_every
    segs = []
    if opts.get('skin'):
        base_i = 0
        for tr in tracks:
            for a, b, dirn in turning_segments(tr.cd, tr.ele, 30):
                segs.append((base_i + a, base_i + b, dirn))
            base_i += len(tr.cd)
    else:
        segs = [(0, len(pts) - 1, 'down')]
    base_y = ph
    if opts.get('day_tints') and len(tracks) > 1:
        segs = []
        base_i = 0
        for di_, tr in enumerate(tracks):
            segs.append((base_i, base_i + len(tr.cd) - 1, 'tint%d' % (di_ % 2)))
            base_i += len(tr.cd)
    for a, b, dirn in segs:
        sub = pts[a:b + 1:max(1, step)] + [pts[b]]
        poly = [(X(sub[0][0]), base_y)] + [(X(d), Y(e)) for d, e, _ in sub] + [(X(sub[-1][0]), base_y)]
        fill = {'up': 'url(#%s_hatch)' % uid, 'tint0': '#E2DFD6', 'tint1': '#EAE7DF'}.get(dirn, '#E2DFD6')
        out.append('<path d="%s" style="fill: %s"/>' % (geo.d_attr(poly, closed=True), fill))
    sel = opts.get('selected')
    breaks = set(b_ for a_, b_ in opts.get('transfers', ()))  # day index that starts after a transfer
    if sel is None and breaks:
        groups, cur = [], []
        for d, e, dd in sp:
            if cur and dd in breaks and cur[-1][2] != dd:
                groups.append(cur)
                cur = []
            cur.append((d, e, dd))
        groups.append(cur)
        out.append('<path class="pf-line" style="stroke: {{route}}" d="%s"/>'
                   % ''.join(geo.d_attr(geo.rdp([(X(d), Y(e)) for d, e, _ in g_], 0.3)) for g_ in groups if len(g_) > 1))
    elif sel is None:
        line = [(X(d), Y(e)) for d, e, _ in sp]
        out.append('<path class="pf-line" style="stroke: {{route}}" d="%s"/>' % geo.d_attr(geo.rdp(line, 0.3)))
    else:
        for di in range(len(tracks)):
            sub = [(X(d), Y(e)) for d, e, dd in sp if dd == di]
            if not sub:
                continue
            if di == sel:
                out.append('<path class="pf-line" style="stroke: {{route}}; stroke-width: 2.5" d="%s"/>' % geo.d_attr(geo.rdp(sub, 0.3)))
            else:
                out.append('<path class="pf-ghost" d="%s"/>' % geo.d_attr(geo.rdp(sub, 0.3)))
    out.extend(ylabels)
    if len(tracks) > 1:
        off = 0
        band = []  # (priority, x, text, style) — placed without collisions after the loop
        for di, tr in enumerate(tracks):
            if di > 0:
                xx = X(off)
                if opts.get('day_band') and di in breaks:
                    out.append('<path d="M%.1f %dV%.1f" style="stroke: #66686D; stroke-width: 1; stroke-dasharray: 2 2"/>' % (xx, 18, ph))
                    band.append((1, xx, 'TRANSFER', 'fill: #66686D'))
                elif opts.get('day_band'):
                    out.append('<path d="M%.1f %dV%.1f" style="stroke: #8C8A83; stroke-width: 1; stroke-dasharray: 2 2"/>' % (xx, 4, ph))
                else:
                    out.append('<path class="pf-div" d="M%.1f %dV%.1f"/>' % (xx, top - 6, ph))
            xm = X(off + tr.total / 2)
            if opts.get('day_band'):
                band.append((0, xm, 'D%d' % (di + 1), 'fill: #45474C; font-weight: 600'))
            else:
                out.append('<text class="pf-ax" x="%.1f" y="%d" style="text-anchor: middle; fill: %s; font-weight: 600; stroke: #F2F1EC; stroke-width: 3px; paint-order: stroke">D%d</text>'
                           % (xm, top + 12, '#16171A' if sel in (None, di) else '#66686D', di + 1))
            off += tr.total
        placed = []
        for pri, x_, txt, sty in sorted(band, key=lambda b: (b[0], b[1])):
            half = text_w(txt, 11, mono=True) / 2 + 4
            if x_ - half < pad_l - 4 or x_ + half > w + 2 or any(not (x_ + half <= a or x_ - half >= b) for a, b in placed):
                continue
            placed.append((x_ - half, x_ + half))
            out.append('<text class="pf-ax" x="%.1f" y="12" style="text-anchor: middle; %s">%s</text>' % (x_, sty, txt))
    out.append('<path class="pf-axk" d="M%d %.1fH%d"/>' % (pad_l, ph + 0.5, w))
    tot_mi = total / MI
    ev = opts.get('axis_every_mi') or (1 if tot_mi <= 15 else (2 if tot_mi <= 30 else 5))
    m = 0
    while m <= tot_mi + 1e-6:
        xx = X(m * MI)
        anchor = 'start' if m == 0 else ('end' if xx > w - 20 else 'middle')
        ly = ph + (23 if opts.get('grade', True) else 15)
        out.append('<path class="pf-axk" d="M%.1f %.1fv4"/><text class="pf-ax" x="%.1f" y="%.1f" style="text-anchor: %s">%s</text>'
                   % (xx, ph, xx, ly, anchor, ('0 mi' if m == 0 else '%d' % m)))
        m += ev
    imax = max(range(len(pts)), key=lambda i_: pts[i_][1])
    raw_max_m = max((t.gps_max_m for t in tracks if t.gps_max_m is not None), default=hi)
    gx, gy = X(pts[imax][0]), Y(pts[imax][1])
    gh = opts.get('grade_h', 8)
    if opts.get('grade', True):
        gy0 = ph + 1
        bin_m = 0.25 * MI
        runs = []
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
            if runs and runs[-1][2] == c:
                runs[-1][1] = d1
            else:
                runs.append([d0, d1, c])
            d0 = d1
        # merge runs narrower than 12px into the previous run
        merged = []
        for r in runs:
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
    sx0, sy0 = X(0), Y(pts[0][1])
    out.append('<circle cx="%.1f" cy="%.1f" r="3.5" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 1.5"/>' % (sx0 + 3.5, sy0))
    out.append('<rect x="%.1f" y="%.1f" width="7" height="7" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 1.5"/>' % (X(total) - 8, Y(pts[-1][1]) - 3.5))
    H = ph + 22 + (gh + 4 if opts.get('grade', True) else 0)
    vpx = (ph - top) / ((y_hi - y_lo) / FT)
    hpx = pw / total
    info['vx'] = vpx / hpx
    info['h'] = H
    svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s" style="display: block; overflow: visible">%s</svg>'
           % (w, H, w, H, esc(opts.get('aria', 'Elevation profile')), ''.join(out)))
    write_frag(name, svg)
    json.dump(info, open(os.path.join(FRAG, name + '.meta.json'), 'w'))
    return info


# ---------------------------------------------------------------- glyphs & sparklines
def render_glyph(name, track_or_tracks, w, h, cat, pad=6, stroke=2.0, bg=None, planned=False, style=None, transfer_dash=None):
    trs = track_or_tracks if isinstance(track_or_tracks, list) else [track_or_tracks]
    pts_all = [[(p[0], p[1]) for p in decimate(t.raw, 1500)] for t in trs]
    proj = Proj(geo.bbox_of(pts_all), w, h, pad=0)
    # manual padding
    proj = Proj(geo.bbox_of(pts_all), w - 2 * pad, h - 2 * pad, pad=0)
    parts = []
    if transfer_dash and len(pts_all) > 1:
        for a_, b_ in zip(pts_all[:-1], pts_all[1:]):
            if geo.hav(a_[-1], b_[0]) > 500:
                x1, y1 = proj.xy(*a_[-1])
                x2, y2 = proj.xy(*b_[0])
                parts.append('<path d="M%.1f %.1fL%.1f %.1f" style="stroke: #66686D; stroke-width: 1; stroke-dasharray: %s; stroke-linecap: butt; fill: none"/>'
                             % (x1 + pad, y1 + pad, x2 + pad, y2 + pad, transfer_dash))
    for pts in pts_all:
        xy = [(x + pad, y + pad) for x, y in (proj.xy(a, b) for a, b in pts)]
        d = geo.d_attr(geo.rdp(xy, 0.25))
        if planned:
            parts.append('<path class="gl-trk" style="stroke: #45474C; stroke-width: 2; stroke-dasharray: 6 4; stroke-linecap: butt" d="%s"/>' % d)
        else:
            parts.append('<path class="gl-trk" style="stroke: %s; stroke-width: %.1f" d="%s"/>' % (CAT[cat] if cat in CAT else cat, stroke, d))
    bgrect = '<rect width="%d" height="%d" style="fill: %s"/>' % (w, h, bg) if bg else ''
    svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d" aria-hidden="true" style="display: block; flex-shrink: 0%s">%s%s</svg>'
           % (w, h, w, h, '; ' + style if style else '', bgrect, ''.join(parts)))
    write_frag(name, svg)
    return svg


def render_tile(name, track, w, h, cat, osm_detail=None, extra_tracks=(), osm_data=None, planned=False, tracks=None, transfers=()):
    """Mini-topo tile: map-paper, index contours only, water fill, track 2.5px on a 1.5px casing."""
    trs = tracks or [{'track': track, 'style': 'planned' if planned else 'cat', 'cat': cat, 'width': 2.5, 'trim': DEFAULT_TRIM}]
    spec = {'name': name, 'w': w, 'h': h, 'tracks': trs,
            'pad': 0.12 if tracks else 0.14, 'hillshade': False, 'osm': osm_detail, 'legend': False, 'scale': False, 'north': False,
            'graticule': False, 'miles': False, 'chevrons': False, 'startend': False, 'gpsmax': False,
            'contour_labels': False, 'contour_density': 1.6, 'contour_step': 2.0, 'minor_contours': False, 'peaks_max': 0, 'places': False,
            'water_labels': 0, 'trails': False, 'road_levels': (), 'min_extent_m': 900, 'trim': DEFAULT_TRIM, 'osm_data': osm_data,
            'transfers': list(transfers), 'transfer_dash': '2 3', 'transfer_w': 1, 'transfer_label': False, 'split_base': False}
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
           % (w, h, w, h, geo.d_attr(geo.rdp(xy, 0.2)), color, stroke))
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
    pad_l = 44 if w < 500 else 72
    pw = w - pad_l
    top, ph = 6, h - 26

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
    labels = []
    k = 1
    while k * step <= top_v + 1e-9:
        v = k * step
        yy = Y(v)
        parts.append('<path class="pf-grid" d="M%d %.1fH%d"/>' % (pad_l, yy, w))
        txt = ('%g mph' % v) if abs(v - top_v) < 1e-9 else ('%g' % v)
        labels.append('<text class="pf-ax" x="%d" y="%.1f" style="text-anchor: end; dominant-baseline: central">%s</text>' % (pad_l - 8, yy, txt))
        k += 1
    labels.append('<text class="pf-ax" x="%d" y="%.1f" style="text-anchor: end; dominant-baseline: central">0</text>' % (pad_l - 8, Y(0)))
    line = geo.rdp([(X(t), Y(v_)) for t, v_ in series], 0.4)
    parts.append('<path class="pf-line" style="stroke: {{route}}; stroke-width: 1.5" d="%s"/>' % geo.d_attr(line))
    parts.extend(labels)
    parts.append('<path class="pf-axk" d="M%d %.1fH%d"/>' % (pad_l, ph + 0.5, w))
    mins = span / 60
    every = 10 if pw / max(mins / 10, 1) >= 36 else 20
    m = 0
    while m <= mins + 0.1:
        x = X(m * 60)
        anchor = 'start' if m == 0 else ('end' if x > w - 20 else 'middle')
        parts.append('<path class="pf-axk" d="M%.1f %.1fv4"/><text class="pf-ax" x="%.1f" y="%.1f" style="text-anchor: %s">%s</text>'
                     % (x, ph, x, ph + 16, anchor, '0 min' if m == 0 else '%d' % m))
        m += every
    svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="Speed over the paddle, 3-minute average, in miles per hour" style="display: block; overflow: visible">%s</svg>'
           % (w, h, w, h, ''.join(parts)))
    write_frag(name, svg)
    return {'span_min': mins, 'vmax_mph': max(v for _, v in series), 'stopped_s': stopped_total, 'top_mph': top_v}
