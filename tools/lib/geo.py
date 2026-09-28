"""Geo toolkit (stdlib only): projection, AWS terrain tiles, PNG io, contours, OSM (Overpass), simplification."""
import hashlib
import json
import math
import os
import struct
import subprocess
import time
import urllib.parse
import zlib

SP = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SP, '..', '..'))
TILE_DIR = os.environ.get('TILE_DIR') or os.path.join(ROOT, '.cache', 'tiles')
OSM_DIR = os.environ.get('OSM_DIR') or os.path.join(ROOT, '.cache', 'osm')
os.makedirs(TILE_DIR, exist_ok=True)
os.makedirs(OSM_DIR, exist_ok=True)

M_PER_DEG_LAT = 110574.0
M_PER_DEG_LON_EQ = 111320.0
FT = 3.28084
MI = 1609.344


# ---------------------------------------------------------------- distances
def hav(a, b):
    R = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(min(1.0, d)))


def cumdist(pts):
    out = [0.0]
    for i in range(1, len(pts)):
        out.append(out[-1] + hav(pts[i - 1], pts[i]))
    return out


# ---------------------------------------------------------------- projection
class Proj:
    """Local equirectangular fitted to a bbox inside a w x h frame (px)."""

    def __init__(self, bbox, w, h, pad=0.12, lat0=None):
        s, wv, n, e = bbox  # south, west, north, east
        self.lat0 = lat0 if lat0 is not None else (s + n) / 2
        self.lon0 = (wv + e) / 2
        self.kx = M_PER_DEG_LON_EQ * math.cos(math.radians(self.lat0))
        self.ky = M_PER_DEG_LAT
        bw = (e - wv) * self.kx
        bh = (n - s) * self.ky
        avail_w, avail_h = w * (1 - 2 * pad), h * (1 - 2 * pad)
        self.scale = min(avail_w / max(bw, 1), avail_h / max(bh, 1))  # px per meter
        self.w, self.h = w, h
        self.cx, self.cy = w / 2, h / 2
        self.latc = (s + n) / 2

    def xy(self, lat, lon):
        return (self.cx + (lon - self.lon0) * self.kx * self.scale,
                self.cy - (lat - self.latc) * self.ky * self.scale)

    def ll(self, x, y):
        lon = self.lon0 + (x - self.cx) / (self.kx * self.scale)
        lat = self.latc - (y - self.cy) / (self.ky * self.scale)
        return lat, lon

    def bounds(self, margin=0):
        lat_n, lon_w = self.ll(-margin, -margin)
        lat_s, lon_e = self.ll(self.w + margin, self.h + margin)
        return lat_s, lon_w, lat_n, lon_e

    @property
    def m_per_px(self):
        return 1.0 / self.scale


def bbox_of(pts_list):
    lats = [p[0] for pts in pts_list for p in pts]
    lons = [p[1] for pts in pts_list for p in pts]
    return min(lats), min(lons), max(lats), max(lons)


# ---------------------------------------------------------------- PNG io
def png_read(path):
    data = open(path, 'rb').read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos = 8
    idat = b''
    w = h = bd = ct = None
    plte = None
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', body)
            assert bd == 8 and il == 0, (bd, il)
        elif typ == b'PLTE':
            plte = body
        elif typ == b'IDAT':
            idat += body
        elif typ == b'IEND':
            break
        pos += 12 + ln
    raw = zlib.decompress(idat)
    bpp = {2: 3, 6: 4, 0: 1, 3: 1, 4: 2}[ct]
    stride = w * bpp
    out = bytearray(h * stride)
    prev = bytearray(stride)
    i = 0
    for y in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        if f == 1:
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) & 255
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif f == 3:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif f == 4:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line
    if ct == 3:
        rgb = bytearray(w * h * 3)
        for k in range(w * h):
            idx = out[k] * 3
            rgb[k * 3:k * 3 + 3] = plte[idx:idx + 3]
        return w, h, 3, rgb
    return w, h, bpp, out


def png_write_palette(path, w, h, indices, palette):
    """indices: bytearray w*h of palette indices; palette: list of (r,g,b)."""
    def chunk(t, b):
        c = struct.pack('>I', len(b)) + t + b
        return c + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(indices[y * w:(y + 1) * w])
    plte = b''.join(bytes(c) for c in palette)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 3, 0, 0, 0))
    png += chunk(b'PLTE', plte) + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b'')
    open(path, 'wb').write(png)


# ---------------------------------------------------------------- terrain tiles
TILE_URL = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
_tile_cache = {}


def tile_xy(lat, lon, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    lr = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lr)) / math.pi) / 2.0 * n
    return x, y


def get_tile(z, x, y):
    key = (z, x, y)
    if key in _tile_cache:
        return _tile_cache[key]
    p = os.path.join(TILE_DIR, '%d_%d_%d.png' % (z, x, y))

    def fetch():
        url = TILE_URL.format(z=z, x=x, y=y)
        tmp = '%s.%d.part' % (p, os.getpid())  # write-then-rename: parallel renders never read a half-written tile
        for attempt in range(3):
            r = subprocess.run(['curl', '-s', '-f', '--max-time', '30', '-o', tmp, url])
            if r.returncode == 0:
                os.replace(tmp, p)
                return
            time.sleep(1.5)
        raise RuntimeError('tile fetch failed ' + url)
    if not os.path.exists(p):
        fetch()
    try:
        w, h, bpp, px = png_read(p)
    except Exception:  # noqa: BLE001 — a truncated cache file: fetch it again
        fetch()
        w, h, bpp, px = png_read(p)
    elev = [0.0] * (w * h)
    for k in range(w * h):
        r, g, b = px[k * bpp], px[k * bpp + 1], px[k * bpp + 2]
        elev[k] = (r * 256 + g + b / 256.0) - 32768.0
    _tile_cache[key] = elev
    return elev


class DEM:
    def __init__(self, z):
        self.z = z

    def sample(self, lat, lon):
        fx, fy = tile_xy(lat, lon, self.z)
        px, py = fx * 256 - 0.5, fy * 256 - 0.5
        x0, y0 = math.floor(px), math.floor(py)
        tx, ty = px - x0, py - y0
        v = 0.0
        for dx, dy, wgt in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)), (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
            gx, gy = x0 + dx, y0 + dy
            t = get_tile(self.z, gx // 256, gy // 256)
            v += wgt * t[(gy % 256) * 256 + (gx % 256)]
        return v


def pick_zoom(lat, m_per_px_target, zmax=13, zmin=4):
    for z in range(zmax, zmin - 1, -1):
        mpp = 156543.03 * math.cos(math.radians(lat)) / (2 ** z)
        if mpp >= m_per_px_target * 0.9:
            return min(zmax, z + 1)
    return zmin


def dem_grid(proj, step, zoom=None, margin=0):
    """Elevation grid at every `step` px across the frame (plus margin). Returns (grid, nx, ny, x0, y0)."""
    if zoom is None:
        zoom = pick_zoom(proj.latc, proj.m_per_px * step)
    dem = DEM(zoom)
    x0 = -margin
    y0 = -margin
    nx = int((proj.w + 2 * margin) / step) + 2
    ny = int((proj.h + 2 * margin) / step) + 2
    grid = [[0.0] * nx for _ in range(ny)]
    for j in range(ny):
        for i in range(nx):
            lat, lon = proj.ll(x0 + i * step, y0 + j * step)
            grid[j][i] = dem.sample(lat, lon)
    return grid, nx, ny, x0, y0


def blur(grid, passes=1):
    ny, nx = len(grid), len(grid[0])
    for _ in range(passes):
        g2 = [row[:] for row in grid]
        for j in range(ny):
            for i in range(nx):
                s = 0.0
                c = 0
                for dj in (-1, 0, 1):
                    jj = j + dj
                    if 0 <= jj < ny:
                        for di in (-1, 0, 1):
                            ii = i + di
                            if 0 <= ii < nx:
                                s += grid[jj][ii]
                                c += 1
                g2[j][i] = s / c
        grid = g2
    return grid


# ---------------------------------------------------------------- contours (marching squares)
def contour_lines(grid, level, x0, y0, step):
    ny, nx = len(grid), len(grid[0])
    segs = {}  # edge -> list of (edge_other)
    def ekey(kind, i, j):
        return (kind, i, j)
    def epos(k):
        kind, i, j = k
        if kind == 'h':  # edge between (i,j) and (i+1,j)
            a, b = grid[j][i], grid[j][i + 1]
            t = (level - a) / (b - a) if b != a else 0.5
            return (x0 + (i + t) * step, y0 + j * step)
        a, b = grid[j][i], grid[j + 1][i]
        t = (level - a) / (b - a) if b != a else 0.5
        return (x0 + i * step, y0 + (j + t) * step)
    adj = {}
    def link(a, b):
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    for j in range(ny - 1):
        r0, r1 = grid[j], grid[j + 1]
        for i in range(nx - 1):
            tl, tr, br, bl = r0[i], r0[i + 1], r1[i + 1], r1[i]
            c = (tl >= level) * 8 + (tr >= level) * 4 + (br >= level) * 2 + (bl >= level)
            if c == 0 or c == 15:
                continue
            top, right, bottom, left = ekey('h', i, j), ekey('v', i + 1, j), ekey('h', i, j + 1), ekey('v', i, j)
            if c in (1, 14):
                link(left, bottom)
            elif c in (2, 13):
                link(bottom, right)
            elif c in (3, 12):
                link(left, right)
            elif c in (4, 11):
                link(top, right)
            elif c == 5:
                center = (tl + tr + br + bl) / 4
                if center >= level:
                    link(left, top); link(bottom, right)
                else:
                    link(left, bottom); link(top, right)
            elif c in (6, 9):
                link(top, bottom)
            elif c in (7, 8):
                link(left, top)
            elif c == 10:
                center = (tl + tr + br + bl) / 4
                if center >= level:
                    link(left, bottom); link(top, right)
                else:
                    link(left, top); link(bottom, right)
    # chain
    lines = []
    seen = set()
    for start in list(adj.keys()):
        if start in seen:
            continue
        # walk to an end if open
        cur = start
        prev = None
        # find an endpoint for open lines
        path_keys = [cur]
        seen.add(cur)
        # extend forward
        def walk(cur, prev, acc):
            while True:
                nxt = [k for k in adj[cur] if k != prev and k not in seen]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                seen.add(cur)
                acc.append(cur)
            return acc
        fwd = walk(cur, None, [])
        bwd = walk(cur, None, [])
        keys = list(reversed(bwd)) + [cur] + fwd
        closed = len(keys) > 2 and keys[0] in adj.get(keys[-1], [])
        pts = [epos(k) for k in keys]
        if closed:
            pts.append(pts[0])
        lines.append(pts)
    return lines


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        best, bi = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if L == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * px - dx * py + bx * ay - by * ax) / L
            if d > best:
                best, bi = d, i
        if best > eps and bi > 0:
            keep[bi] = True
            stack.append((a, bi))
            stack.append((bi, b))
    return [p for p, k in zip(pts, keep) if k]


def path_len(pts):
    return sum(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) for i in range(1, len(pts)))


def _num_i(k, prec):
    """An integer count of 10^-prec units as the shortest path number: 12.0 -> '12', 0.5 -> '.5', -0.5 -> '-.5'."""
    if prec <= 0:
        return str(k)
    neg = k < 0
    q, r = divmod(abs(k), 10 ** prec)
    s = str(q)
    if r:
        s = ('' if q == 0 else s) + '.' + ('%0*d' % (prec, r)).rstrip('0')
    return ('-' + s) if (neg and s != '0') else s


def _join_nums(toks):
    """Numbers joined with the fewest separators: a '-' sign separates by itself, and '.5' after a number that already
    has a decimal point needs no space ('1.5.5' reads as 1.5, .5 — valid SVG path grammar)."""
    out = []
    last = ''
    for t in toks:
        if last and not t.startswith('-') and not (t.startswith('.') and '.' in last):
            out.append(' ')
        out.append(t)
        last = t
    return ''.join(out)


def d_attr(pts, closed=False, prec=1, rel=False):
    """SVG path data for a polyline. rel=True: 'M x y l dx dy dx dy …' — the absolute points are rounded first and the
    deltas are taken between the rounded points, so the drawn geometry is exactly the absolute one (no drift); zero-length
    steps are dropped. About half the bytes of the absolute form."""
    if not pts:
        return ''
    if rel:
        m = 10 ** prec
        q = [(int(round(x * m)), int(round(y * m))) for x, y in pts]
        out = 'M' + _join_nums([_num_i(q[0][0], prec), _num_i(q[0][1], prec)])
        toks = []
        for (x0, y0), (x1, y1) in zip(q, q[1:]):
            if x1 == x0 and y1 == y0:
                continue
            toks += [_num_i(x1 - x0, prec), _num_i(y1 - y0, prec)]
        if toks:
            out += 'l' + _join_nums(toks)
        return out + ('z' if closed else '')
    f = '%.' + str(prec) + 'f'
    last = (f % pts[0][0]) + ' ' + (f % pts[0][1])
    out = ['M' + last]
    for x, y in pts[1:]:
        cur = (f % x) + ' ' + (f % y)
        if cur == last:
            continue  # same point at this precision: a zero-length segment only adds bytes
        out.append('L' + cur)
        last = cur
    if closed:
        out.append('Z')
    return ''.join(out).replace('.0 ', ' ').replace('.0L', 'L')


# ---------------------------------------------------------------- OSM
OVERPASS = ['https://overpass-api.de/api/interpreter', 'https://maps.mail.ru/osm/tools/overpass/api/interpreter']


def overpass(query):
    h = hashlib.sha1(query.encode()).hexdigest()[:16]
    p = os.path.join(OSM_DIR, h + '.json')
    if os.path.exists(p):
        return json.load(open(p))
    last = None
    for attempt in range(4):
        ep = OVERPASS[attempt % len(OVERPASS)]
        r = subprocess.run(['curl', '-s', '--max-time', '180', '-A', 'esichak-personal-website/1.0 (+https://esichak.github.io/personal-website/)',
                            '--data-urlencode', 'data=' + query, ep], capture_output=True)
        try:
            d = json.loads(r.stdout.decode('utf-8'))
            tmp = '%s.%d.part' % (p, os.getpid())
            with open(tmp, 'w') as fh:
                json.dump(d, fh)
            os.replace(tmp, p)
            return d
        except Exception as ex:  # noqa
            last = r.stdout[:300]
            time.sleep(4 + attempt * 4)
    raise RuntimeError('overpass failed: %r' % last)


def osm_layers(bbox, detail='report'):
    """bbox = (s, w, n, e). detail: report|overview|region."""
    s, w, n, e = bbox
    bb = '%.5f,%.5f,%.5f,%.5f' % (s, w, n, e)
    parts = [
        'nwr["natural"="water"](%s);' % bb,
        'nwr["natural"="glacier"](%s);' % bb,
        'node["natural"="peak"]["name"](%s);' % bb,
        'way["highway"~"^(motorway|trunk|primary|secondary)$"](%s);' % bb,
    ]
    if detail in ('report', 'overview'):
        parts.append('way["highway"~"^(tertiary|unclassified)$"](%s);' % bb)
        parts.append('node["place"~"^(city|town|village)$"](%s);' % bb)
        parts.append('nwr["tourism"~"^(alpine_hut|wilderness_hut)$"](%s);' % bb)
    if detail == 'report':
        parts.append('way["highway"~"^(path|footway|track)$"](%s);' % bb)
        parts.append('way["waterway"~"^(river|stream)$"](%s);' % bb)
        parts.append('node["natural"="saddle"]["name"](%s);' % bb)
    if detail == 'region':
        parts.append('node["place"~"^(city|town)$"](%s);' % bb)
        parts.append('way["waterway"="river"]["name"](%s);' % bb)
    q = '[out:json][timeout:160];(' + ''.join(parts) + ');out geom qt;'
    return overpass(q)


def join_rings(ways):
    """ways: list of coordinate lists [(lat,lon),...]; join by shared endpoints into rings."""
    ways = [list(w) for w in ways if len(w) >= 2]
    rings = []
    while ways:
        cur = ways.pop(0)
        changed = True
        while changed and cur[0] != cur[-1]:
            changed = False
            for k, w in enumerate(ways):
                if w[0] == cur[-1]:
                    cur += w[1:]
                elif w[-1] == cur[-1]:
                    cur += list(reversed(w))[1:]
                elif w[-1] == cur[0]:
                    cur = w[:-1] + cur
                elif w[0] == cur[0]:
                    cur = list(reversed(w))[:-1] + cur
                else:
                    continue
                ways.pop(k)
                changed = True
                break
        rings.append(cur)
    return rings


def osm_polys(data, key, val):
    """Return list of (outer_rings, inner_rings, tags) for areas with tag key=val."""
    out = []
    for el in data.get('elements', []):
        t = el.get('tags', {})
        if t.get(key) != val:
            continue
        if el['type'] == 'way' and 'geometry' in el:
            ring = [(g['lat'], g['lon']) for g in el['geometry']]
            out.append(([ring], [], t))
        elif el['type'] == 'relation':
            outer = [[(g['lat'], g['lon']) for g in m['geometry']] for m in el.get('members', [])
                     if m.get('role') == 'outer' and 'geometry' in m]
            inner = [[(g['lat'], g['lon']) for g in m['geometry']] for m in el.get('members', [])
                     if m.get('role') == 'inner' and 'geometry' in m]
            out.append((join_rings(outer), join_rings(inner), t))
    return out


def osm_lines(data, pred):
    out = []
    for el in data.get('elements', []):
        t = el.get('tags', {})
        if el['type'] == 'way' and 'geometry' in el and pred(t):
            out.append(([(g['lat'], g['lon']) for g in el['geometry']], t))
    return out


def osm_nodes(data, pred):
    out = []
    for el in data.get('elements', []):
        t = el.get('tags', {})
        if not pred(t):
            continue
        if el['type'] == 'node':
            out.append(((el['lat'], el['lon']), t))
        elif 'center' in el:
            out.append(((el['center']['lat'], el['center']['lon']), t))
        elif 'bounds' in el:
            b = el['bounds']
            out.append((((b['minlat'] + b['maxlat']) / 2, (b['minlon'] + b['maxlon']) / 2), t))
        elif 'geometry' in el:
            g = el['geometry']
            out.append(((sum(p['lat'] for p in g) / len(g), sum(p['lon'] for p in g) / len(g)), t))
    return out


def clip_poly_to_frame(pts, w, h, margin=40):
    """Crude: keep polygon if any vertex within expanded frame."""
    return any(-margin <= x <= w + margin and -margin <= y <= h + margin for x, y in pts)
