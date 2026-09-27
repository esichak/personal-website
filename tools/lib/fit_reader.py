"""Minimal stdlib FIT decoder: returns track points from record messages (global msg 20).

Each point: (lat, lon, ele_m or None, unix_ts or None).
"""
import gzip
import struct

FIT_EPOCH = 631065600  # 1989-12-31T00:00:00Z in unix seconds
SEMI = 180.0 / 2 ** 31

# base type sizes and struct formats (little-endian; endianness applied per definition)
BASE = {
    0x00: 'B', 0x01: 'b', 0x02: 'B', 0x83: 'h', 0x84: 'H', 0x85: 'i', 0x86: 'I',
    0x07: 's', 0x88: 'f', 0x89: 'd', 0x0A: 'B', 0x8B: 'H', 0x8C: 'I', 0x0D: 'B',
    0x8E: 'q', 0x8F: 'Q', 0x90: 'Q',
}
INVALID = {'b': 0x7F, 'B': 0xFF, 'h': 0x7FFF, 'H': 0xFFFF, 'i': 0x7FFFFFFF, 'I': 0xFFFFFFFF}


def _read_value(buf, off, size, btype, endian):
    fmt = BASE.get(btype & 0x9F if btype not in BASE else btype)
    if fmt is None or fmt == 's':
        return None
    n = struct.calcsize(fmt)
    if size != n:
        # arrays: take first element only
        if size < n:
            return None
    v = struct.unpack_from(endian + fmt, buf, off)[0]
    if fmt in INVALID and v == INVALID[fmt]:
        return None
    return v


def read_fit(path):
    raw = open(path, 'rb').read()
    if path.endswith('.gz'):
        raw = gzip.decompress(raw)
    pts = []
    pos = 0
    while pos + 12 <= len(raw):
        hsize = raw[pos]
        if raw[pos + 8:pos + 12] != b'.FIT':
            break
        data_size = struct.unpack_from('<I', raw, pos + 4)[0]
        start = pos + hsize
        end = start + data_size
        defs = {}
        last_ts = None
        i = start
        while i < end:
            hdr = raw[i]
            i += 1
            if hdr & 0x80:  # compressed timestamp header
                local = (hdr >> 5) & 0x03
                offset = hdr & 0x1F
                d = defs.get(local)
                if d is None:
                    break
                ts = None
                if last_ts is not None:
                    ts = last_ts + ((offset - (last_ts & 0x1F)) & 0x1F)
                    last_ts = ts
                rec = _parse_data(raw, i, d)
                i += d['size']
                if d['global'] == 20:
                    rec.setdefault(253, ts)
                    _add_point(pts, rec)
                continue
            local = hdr & 0x0F
            if hdr & 0x40:  # definition
                dev = bool(hdr & 0x20)
                arch = raw[i + 1]
                endian = '>' if arch == 1 else '<'
                glob = struct.unpack_from(endian + 'H', raw, i + 2)[0]
                nf = raw[i + 4]
                i += 5
                fields = []
                size = 0
                for _ in range(nf):
                    fnum, fsize, btype = raw[i], raw[i + 1], raw[i + 2]
                    fields.append((fnum, fsize, btype))
                    size += fsize
                    i += 3
                if dev:
                    nd = raw[i]
                    i += 1
                    for _ in range(nd):
                        size += raw[i + 1]
                        i += 3
                defs[local] = {'global': glob, 'fields': fields, 'size': size, 'endian': endian}
            else:
                d = defs.get(local)
                if d is None:
                    break
                rec = _parse_data(raw, i, d)
                i += d['size']
                if 253 in rec and rec[253] is not None:
                    last_ts = rec[253]
                if d['global'] == 20:
                    _add_point(pts, rec)
        pos = end + 2  # skip file CRC; chained files follow
    return pts


def _parse_data(raw, i, d):
    rec = {}
    off = i
    for fnum, fsize, btype in d['fields']:
        if fnum in (253, 0, 1, 2, 78, 5):
            rec[fnum] = _read_value(raw, off, fsize, btype, d['endian'])
        off += fsize
    return rec


def _add_point(pts, rec):
    lat, lon = rec.get(0), rec.get(1)
    if lat is None or lon is None:
        return
    ele = None
    if rec.get(78) is not None:
        ele = rec[78] / 5.0 - 500
    elif rec.get(2) is not None:
        ele = rec[2] / 5.0 - 500
    ts = rec.get(253)
    pts.append((lat * SEMI, lon * SEMI, ele, (ts + FIT_EPOCH) if ts is not None else None))


def read_gpx(path):
    import re
    import xml.etree.ElementTree as ET
    from datetime import datetime, timezone
    root = ET.parse(path).getroot()
    m = re.match(r'\{.*\}', root.tag)
    ns = m.group(0) if m else ''
    pts = []
    for p in root.iter(ns + 'trkpt'):
        e = p.find(ns + 'ele')
        t = p.find(ns + 'time')
        ts = None
        if t is not None and t.text:
            s = t.text.strip().replace('Z', '+00:00')
            try:
                ts = datetime.fromisoformat(s.split('.')[0] + ('+00:00' if '+' not in s[10:] else '')).timestamp()
            except ValueError:
                ts = None
        pts.append((float(p.get('lat')), float(p.get('lon')), float(e.text) if e is not None else None, ts))
    return pts


def read_track(path):
    return read_gpx(path) if path.lower().endswith('.gpx') else read_fit(path)


if __name__ == '__main__':
    import sys
    for f in sys.argv[1:]:
        p = read_track(f)
        eles = [x[2] for x in p if x[2] is not None]
        print(f.split('/')[-1], len(p), 'pts', 'ele', (min(eles), max(eles)) if eles else None,
              'ts', p[0][3] if p else None, 'first', p[0][:2] if p else None)
