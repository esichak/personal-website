"""Photo helpers (stdlib + macOS `sips`, `cwebp` from Homebrew): read EXIF orientation and size, make web copies.

Web copies are upright (EXIF orientation applied to the pixels), resized, re-encoded as JPEG, and stripped of
every metadata segment except the JFIF header and the ICC colour profile, so no GPS, camera or date tags are published.
"""
import os
import struct
import subprocess
import tempfile

KEEP_APP = {0xE0, 0xE2}  # APP0 JFIF, APP2 ICC profile
SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def _segments(data):
    """Yield (marker, start, end) for header segments up to SOS."""
    if data[:2] != b'\xff\xd8':
        raise ValueError('not a JPEG')
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            raise ValueError('bad marker at %d' % i)
        while data[i] == 0xFF:
            i += 1
        m = data[i]
        i += 1
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            continue
        ln = struct.unpack('>H', data[i:i + 2])[0]
        yield m, i - 2, i + ln
        if m == 0xDA:  # start of scan: the rest is image data
            return
        i += ln


def _exif_orientation(seg):
    if seg[:6] != b'Exif\x00\x00':
        return None
    t = seg[6:]
    end = '<' if t[:2] == b'II' else '>'
    off = struct.unpack(end + 'I', t[4:8])[0]
    n = struct.unpack(end + 'H', t[off:off + 2])[0]
    for k in range(n):
        e = off + 2 + 12 * k
        tag, typ, cnt = struct.unpack(end + 'HHI', t[e:e + 8])
        if tag == 0x0112:
            return struct.unpack(end + 'H', t[e + 8:e + 10])[0]
    return None


def info(path):
    """Return dict(w, h, orientation) of a JPEG without decoding it."""
    data = open(path, 'rb').read()
    out = {'w': None, 'h': None, 'orientation': 1}
    for m, a, b in _segments(data):
        if m == 0xE1:
            try:
                o = _exif_orientation(data[a + 4:b])
                if o:
                    out['orientation'] = o
            except (struct.error, IndexError):
                pass
        elif m in SOF:
            h, w = struct.unpack('>HH', data[a + 5:a + 9])
            out['w'], out['h'] = w, h
    return out


def strip_metadata(path):
    """Rewrite a JPEG in place without EXIF/XMP/IPTC/comment segments."""
    data = open(path, 'rb').read()
    parts = [b'\xff\xd8']
    rest = None
    for m, a, b in _segments(data):
        if m == 0xDA:
            rest = data[a:]
            break
        if (0xE0 <= m <= 0xEF and m not in KEEP_APP) or m == 0xFE:
            continue
        parts.append(data[a:b])
    if rest is None:
        raise ValueError('no image data in ' + path)
    open(path, 'wb').write(b''.join(parts) + rest)


ROTATE = {3: 180, 6: 90, 8: 270, 5: 90, 7: 270}
FLIP = {2: 'horizontal', 4: 'vertical', 5: 'horizontal', 7: 'horizontal'}


def web_copy(src, dst, max_px, quality=82):
    """Upright, resized (long edge <= max_px), metadata-free JPEG copy. Returns (w, h)."""
    o = info(src).get('orientation') or 1
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, 'x.jpg')
        cmd = ['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', str(quality)]
        if o in ROTATE:
            cmd += ['--rotate', str(ROTATE[o])]
        if o in FLIP:
            cmd += ['--flip', FLIP[o]]
        cmd += ['-Z', str(max_px), src, '--out', tmp]
        subprocess.run(cmd, check=True, capture_output=True)
        strip_metadata(tmp)
        os.replace(tmp, dst)
    i = info(dst)
    return i['w'], i['h']


def have_cwebp():
    from shutil import which
    return which('cwebp') is not None


def web_copies(src, dst_base, big=1600, small=800, quality=72):
    """Write dst_base.webp (long edge <= big) and dst_base.sm.webp (<= small); JPEG fallback without cwebp.

    Returns (extension, w, h) of the large copy. Only the ICC colour profile is kept (no EXIF/GPS/XMP)."""
    os.makedirs(os.path.dirname(dst_base), exist_ok=True)
    if not have_cwebp():
        w, h = web_copy(src, dst_base + '.jpg', big, quality=78)
        web_copy(src, dst_base + '.sm.jpg', small, quality=74)
        return 'jpg', w, h
    with tempfile.TemporaryDirectory() as td:
        mid = os.path.join(td, 'm.jpg')
        w, h = web_copy(src, mid, big, quality=95)
        subprocess.run(['cwebp', '-quiet', '-q', str(quality), '-m', '5', '-metadata', 'icc', mid, '-o', dst_base + '.webp'],
                       check=True, capture_output=True)
        rs = ['-resize', str(small), '0'] if w >= h else ['-resize', '0', str(small)]
        subprocess.run(['cwebp', '-quiet', '-q', str(quality), '-m', '5', '-metadata', 'icc'] + rs + [mid, '-o', dst_base + '.sm.webp'],
                       check=True, capture_output=True)
    return 'webp', w, h
