"""Track helpers: read FIT/GPX, simplify, write GPX, compute stats, guess the local time zone."""
import math
import os
from datetime import datetime, timezone
from xml.sax.saxutils import escape

import fit_reader
import geo

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None


TRACK_EXT = ('.fit', '.fit.gz', '.gpx')
ZIP_MAX = 50 * 1024 * 1024   # a single recording is a few MB; a member larger than this is not one


def read(path):
    """[(lat, lon, ele_m|None, unix_ts|None)] from .fit, .fit.gz or .gpx, or from a .zip that holds exactly one of them
    (Garmin Connect's 'Export Original' download), read from memory without unpacking anything to disk."""
    if path.lower().endswith('.zip'):
        pts = fit_reader.read_track_bytes(*zip_member(path))
    else:
        pts = fit_reader.read_track(path)
    return [p for p in pts if p[0] is not None and p[1] is not None]


def zip_member(path):
    """(name, bytes) of the one track file in a .zip. ValueError when the archive holds none or several (named), or one
    larger than ZIP_MAX; zipfile.BadZipFile when it is not a zip at all."""
    import zipfile
    with zipfile.ZipFile(path) as zf:
        found = [i for i in zf.infolist() if not i.is_dir() and i.filename.lower().endswith(TRACK_EXT)
                 and not i.filename.startswith('__MACOSX/') and not os.path.basename(i.filename).startswith('.')]
        if not found:
            raise ValueError('the .zip holds no .fit, .fit.gz or .gpx file')
        if len(found) > 1:
            raise ValueError('the .zip holds %d track files (%s); unzip it and give the one you mean'
                             % (len(found), ', '.join(i.filename for i in found)))
        info = found[0]
        if info.file_size > ZIP_MAX:
            raise ValueError('%s in the .zip is %d MB, more than a recording (limit %d MB)'
                             % (info.filename, info.file_size // (1024 * 1024), ZIP_MAX // (1024 * 1024)))
        with zf.open(info) as fh:
            data = fh.read(ZIP_MAX + 1)   # the size the archive states is not trusted: read no more than the limit
        if len(data) > ZIP_MAX:
            raise ValueError('%s in the .zip is larger than a recording (limit %d MB)' % (info.filename, ZIP_MAX // (1024 * 1024)))
        return info.filename, data


def simplify(pts, eps_m=2.0):
    """3-D Ramer–Douglas–Peucker in local metres (elevation counts as a third axis). Keeps first/last points."""
    if len(pts) < 3:
        return list(pts)
    lat0 = pts[0][0]
    kx = geo.M_PER_DEG_LON_EQ * math.cos(math.radians(lat0))
    ky = geo.M_PER_DEG_LAT
    last_e = next((p[2] for p in pts if p[2] is not None), 0.0)
    xyz = []
    for p in pts:
        if p[2] is not None:
            last_e = p[2]
        xyz.append(((p[1] - pts[0][1]) * kx, (p[0] - lat0) * ky, last_e))
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        ax, ay, az = xyz[a]
        bx, by, bz = xyz[b]
        dx, dy, dz = bx - ax, by - ay, bz - az
        L2 = dx * dx + dy * dy + dz * dz
        best, bi = -1.0, -1
        for i in range(a + 1, b):
            px, py, pz = xyz[i]
            if L2 == 0:
                d2 = (px - ax) ** 2 + (py - ay) ** 2 + (pz - az) ** 2
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy + (pz - az) * dz) / L2))
                d2 = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2 + (pz - az - t * dz) ** 2
            if d2 > best:
                best, bi = d2, i
        if best > eps_m * eps_m:
            keep[bi] = True
            stack.append((a, bi))
            stack.append((bi, b))
    return [p for p, k in zip(pts, keep) if k]


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def write_gpx(path, pts, name='', kind='', times=True):
    """GPX 1.1 with lat/lon (6 dp), elevation (0.1 m) and, if times, UTC timestamps."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<gpx version="1.1" creator="Eric Sichak trip reports" xmlns="http://www.topografix.com/GPX/1/1">']
    t0 = next((p[3] for p in pts if p[3] is not None), None)
    out.append('<metadata><name>%s</name>%s</metadata>' % (escape(name), '<time>%s</time>' % _iso(t0) if (times and t0) else ''))
    out.append('<trk><name>%s</name>%s<trkseg>' % (escape(name), '<type>%s</type>' % escape(kind) if kind else ''))
    for lat, lon, ele, ts in pts:
        inner = ''
        if ele is not None:
            inner += '<ele>%.1f</ele>' % ele
        if times and ts is not None:
            inner += '<time>%s</time>' % _iso(ts)
        out.append('<trkpt lat="%.6f" lon="%.6f">%s</trkpt>' % (lat, lon, inner))
    out.append('</trkseg></trk>')
    out.append('</gpx>')
    with open(path, 'w') as fh:
        fh.write('\n'.join(out) + '\n')


def guess_tz(lat, lon):
    """Good enough for where Eric travels; override with `timezone:` in front matter (or add_trip.py --timezone). Boxes,
    not borders: Arizona's box comes first because Arizona keeps no summer time, and a start near a state line can land
    in the neighbour's zone. 'UTC' where no box applies."""
    if -10 < lon < 30 and lat > 35:
        return 'Europe/Zurich'
    if 31.3 <= lat <= 37 and -114.8 <= lon <= -109:
        return 'America/Phoenix'
    if lon < -114.5 and lat > 32:
        return 'America/Los_Angeles'
    if -114.5 <= lon < -102 and lat > 31:
        return 'America/Denver'
    if -102 <= lon < -85 and lat > 25:
        return 'America/Chicago'
    if -85 <= lon < -66 and lat > 24:
        return 'America/New_York'
    return 'UTC'


def local_start(pts, tz_name=None):
    ts = next((p[3] for p in pts if p[3] is not None), None)
    if ts is None:
        return None, tz_name
    tz_name = tz_name or guess_tz(pts[0][0], pts[0][1])
    tz = ZoneInfo(tz_name) if ZoneInfo else timezone.utc
    return datetime.fromtimestamp(ts, tz), tz_name


def fmt_hm(sec):
    if sec is None:
        return None
    sec = int(round(sec))
    h, m = sec // 3600, int(round((sec % 3600) / 60.0))
    if m == 60:
        h, m = h + 1, 0
    return '%d:%02d' % (h, m)


def compute_stats(pts):
    """Distance, moving/elapsed time, gain/loss and high/low from the raw points (used when no Strava stats exist)."""
    cd = geo.cumdist(pts)
    dist = cd[-1] if cd else 0.0
    moving = 0.0
    for a, b in zip(pts, pts[1:]):
        if a[3] is None or b[3] is None:
            continue
        dt = b[3] - a[3]
        if 0 < dt <= 120 and geo.hav(a, b) / dt >= 0.3:
            moving += dt
    ts = [p[3] for p in pts if p[3] is not None]
    elapsed = (ts[-1] - ts[0]) if len(ts) > 1 else None
    eles = [p[2] for p in pts if p[2] is not None]
    gain = loss = 0.0
    if eles:
        ref = eles[0]
        for e in eles[1:]:  # 3 m hysteresis to ignore barometer noise
            if e - ref >= 3:
                gain += e - ref
                ref = e
            elif ref - e >= 3:
                loss += ref - e
                ref = e
    return {'distance_km': round(dist / 1000.0, 2), 'moving': fmt_hm(moving) if moving else None,
            'elapsed': fmt_hm(elapsed), 'gain_m': int(round(gain)) if eles else None, 'loss_m': int(round(loss)) if eles else None,
            'high_m': int(round(max(eles))) if eles else None, 'low_m': int(round(min(eles))) if eles else None}


def route_shape(pts):
    if len(pts) < 2:
        return None
    if geo.hav(pts[0], pts[-1]) > 400:
        return 'point-to-point'
    import mapkit
    tr = mapkit.Track(pts, 'x', 'HIK')
    return 'out-and-back' if mapkit.is_out_and_back(tr) else 'loop'
