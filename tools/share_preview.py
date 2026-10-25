#!/usr/bin/env python3
"""What each page's share card is made of, read from a built site: python3 tools/share_preview.py [--site DIR]

DIR is the build (default _site/). Every indexable page is read: a page whose head has <meta name="robots"
content="noindex"> (the 404 page, the trips/<slug>/map/ helpers) is left out, and so are iCloud conflict copies
('index 2.html'). From each head it takes the Open Graph tags and prints, first, the flags (each one's count, then
the pages under it), then one line per page:

  PAGE | og:title | og:description | IMAGE WIDTHxHEIGHT TYPE

PAGE is the page's path under the site ('./' for the home page). IMAGE is the og:image's path under SITE_URL, or the
whole address when it is elsewhere, and 'no image' stands for all three when there is none. The size comes from
og:image:width and og:image:height, else from the image file in the build (PNG, JPEG and WebP headers), else it is
'?'; the type from og:image:type, else the file, else the extension.

Flags: no og:image; an og:description that ends in '…' (cut short); an og:title over 60 characters (TITLE_MAX,
where share cards start cutting); an image that is not JPEG or PNG (some previewers draw no WebP); a portrait image
(height over width: a 1.91:1 card crops it).

It only reads, and prints to stdout: nothing is written into the build. The exit status is 0, or 2 when DIR is not a
folder.
"""
import argparse
import os
import posixpath
import re
import struct
import sys
from html.parser import HTMLParser
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from sitegen import core, sitecheck  # noqa: E402

SITE_URL = core.SITE_URL
TITLE_MAX = 60
CUT = '…'
FLAGS = (                                   # (key, label), in the order they are printed
    ('no-image', 'no og:image'),
    ('cut', "og:description ends in '%s'" % CUT),
    ('long-title', 'og:title over %d characters' % TITLE_MAX),
    ('format', 'image not JPEG or PNG'),
    ('portrait', 'portrait image'),
)
_HEAD_END = re.compile(r'</head\s*>|<body[\s>]', re.I)
_MIME = {'image/jpeg': 'jpeg', 'image/jpg': 'jpeg', 'image/pjpeg': 'jpeg', 'image/png': 'png', 'image/webp': 'webp'}
_EXT = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png', '.webp': 'webp'}
_SOF = set(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}   # JPEG frame headers (C4 DHT, C8 JPG, CC DAC are not)


class _Head(HTMLParser):
    """Every <meta> of a page's head by its name or property (lower case): {key: [content, ...]}."""

    def __init__(self, text):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.meta = {}
        m = _HEAD_END.search(text)
        try:
            self.feed(text[:m.start()] if m else text)   # only the head: a report's body is half a megabyte
            self.close()
        except (AssertionError, NotImplementedError):    # a malformed <![...]> up to Python 3.12.11: keep what was read
            pass

    def handle_starttag(self, tag, attrs):
        if tag == 'meta':
            a = {k: (v or '') for k, v in attrs}
            key = (a.get('property') or a.get('name') or '').lower()
            if key:
                self.meta.setdefault(key, []).append(a.get('content', ''))

    def first(self, key):
        """The first content of a key, its whitespace collapsed ('' when absent)."""
        return ' '.join(self.meta.get(key, [''])[0].split())

    @property
    def noindex(self):
        words = re.split(r'[\s,]+', ' '.join(self.meta.get('robots', [])).lower())
        return 'noindex' in words or 'none' in words


def _webp_size(b):
    """(width, height) from the first 30 bytes of a WebP file: its VP8, VP8L or VP8X chunk."""
    chunk = b[12:16]
    if chunk == b'VP8 ' and b[23:26] == b'\x9d\x01\x2a':
        w, h = struct.unpack('<HH', b[26:30])
        return w & 0x3fff, h & 0x3fff                      # the top two bits are the scale
    if chunk == b'VP8L' and b[20:21] == b'\x2f':
        bits = struct.unpack('<I', b[21:25])[0]
        return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
    if chunk == b'VP8X':
        w, h = struct.unpack('<I', b[24:27] + b'\0')[0], struct.unpack('<I', b[27:30] + b'\0')[0]
        return w + 1, h + 1                                  # the canvas size, less one
    return None, None


def _jpeg_size(fh):
    """(width, height) from a JPEG's first frame header, the file read from just after its FFD8."""
    while True:
        b = fh.read(1)
        if not b:
            return None, None
        if b != b'\xff':
            continue
        marker = fh.read(1)
        while marker == b'\xff':                             # fill bytes
            marker = fh.read(1)
        if not marker:
            return None, None
        m = marker[0]
        if m == 0x01 or 0xD0 <= m <= 0xD8:                   # markers without a length
            continue
        if m in (0xD9, 0xDA):                                # the end, or the scan, before any frame header
            return None, None
        seg = fh.read(2)
        if len(seg) < 2:
            return None, None
        length = struct.unpack('>H', seg)[0]
        if m in _SOF:
            data = fh.read(5)                                # precision, height, width
            if len(data) < 5:
                return None, None
            h, w = struct.unpack('>HH', data[1:5])
            return w, h
        fh.seek(length - 2, 1)


def image_header(path):
    """(type, width, height) read from an image file: 'png', 'jpeg' or 'webp'; (None, None, None) for anything else."""
    try:
        with open(path, 'rb') as fh:
            b = fh.read(32)
            if b[:8] == b'\x89PNG\r\n\x1a\n' and b[12:16] == b'IHDR':
                w, h = struct.unpack('>II', b[16:24])
                return 'png', w, h
            if b[:4] == b'RIFF' and b[8:12] == b'WEBP':
                return ('webp',) + _webp_size(b)
            if b[:2] == b'\xff\xd8':
                fh.seek(2)
                return ('jpeg',) + _jpeg_size(fh)
    except (OSError, struct.error):
        pass
    return None, None, None


def image_file(site, page, url):
    """The og:image's file in the build, or None: an address under SITE_URL, or one relative to the page."""
    if url.startswith(SITE_URL):
        rel = url[len(SITE_URL):]
    elif ':' in url.split('/')[0] or url.startswith('/'):
        return None                                          # another host, or a path from the server's root
    else:
        rel = posixpath.normpath(posixpath.join(posixpath.dirname(page), url))
    rel = unquote(rel.split('#')[0].split('?')[0])
    if not rel or rel == '.' or rel.startswith('../'):
        return None
    path = os.path.join(site, *rel.split('/'))
    return path if os.path.isfile(path) else None


def _int(text):
    return int(text) if text.strip().isdigit() else None


def page_path(rel):
    """'trips/x/index.html' -> 'trips/x/', 'index.html' -> './'."""
    if rel == 'index.html':
        return './'
    return rel[:-len('index.html')] if rel.endswith('/index.html') else rel


def pages(site):
    """Every .html file under site, as a '/'-separated path, sorted; conflict copies left out."""
    found = []
    for dirpath, dirnames, filenames in os.walk(site):
        dirnames[:] = [d for d in dirnames if not sitecheck.conflict_copy(d)]
        for f in filenames:
            if f.endswith('.html') and not sitecheck.conflict_copy(f):
                found.append(os.path.relpath(os.path.join(dirpath, f), site).replace(os.sep, '/'))
    return sorted(found)


def card(site, rel):
    """One page's card: {'path', 'title', 'description', 'image', 'width', 'height', 'type', 'flags'}, or None for a
    noindex page."""
    with open(os.path.join(site, rel), encoding='utf-8', errors='replace') as fh:
        head = _Head(fh.read())
    if head.noindex:
        return None
    c = {'path': page_path(rel), 'title': head.first('og:title'), 'description': head.first('og:description'),
         'image': None, 'width': None, 'height': None, 'type': None, 'flags': []}
    url = head.first('og:image')
    if url:
        c['image'] = url[len(SITE_URL):] if url.startswith(SITE_URL) else url
        c['width'], c['height'] = _int(head.first('og:image:width')), _int(head.first('og:image:height'))
        mime = head.first('og:image:type').lower()
        c['type'] = _MIME.get(mime, mime.split('/')[-1]) if mime else None
        if c['width'] is None or c['height'] is None or c['type'] is None:
            path = image_file(site, rel, url)
            kind, w, h = image_header(path) if path else (None, None, None)
            if c['width'] is None or c['height'] is None:
                c['width'], c['height'] = (w, h) if w and h else (None, None)
            c['type'] = c['type'] or kind
        if c['type'] is None:
            ext = posixpath.splitext(url.split('#')[0].split('?')[0])[1].lower()
            c['type'] = _EXT.get(ext, ext[1:] or None)
    flags = c['flags']
    if not c['image']:
        flags.append('no-image')
    if c['description'].endswith(CUT):
        flags.append('cut')
    if len(c['title']) > TITLE_MAX:
        flags.append('long-title')
    if c['image'] and c['type'] not in ('jpeg', 'png'):
        flags.append('format')
    if c['width'] and c['height'] and c['height'] > c['width']:
        flags.append('portrait')
    return c


def line(c):
    """PAGE | og:title | og:description | IMAGE WIDTHxHEIGHT TYPE."""
    if c['image']:
        size = '%dx%d' % (c['width'], c['height']) if c['width'] and c['height'] else '?'
        image = '%s %s %s' % (c['image'], size, c['type'] or '?')
    else:
        image = 'no image'
    return ' | '.join([c['path'], c['title'] or '(none)', c['description'] or '(none)', image])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--site', default=os.path.join(ROOT, '_site'), help='the built site (default _site/)')
    a = ap.parse_args(argv)
    if not os.path.isdir(a.site):
        print('share_preview: no built site at %s (build it first: python3 tools/build.py)' % a.site, file=sys.stderr)
        return 2
    files = pages(a.site)
    cards = sorted((c for c in (card(a.site, rel) for rel in files) if c), key=lambda c: c['path'])   # './' first
    flagged = {key: [c['path'] for c in cards if key in c['flags']] for key, _label in FLAGS}
    print('%d pages: %d indexable, %d noindex left out' % (len(files), len(cards), len(files) - len(cards)))
    for key, label in FLAGS:
        print('%5d  %s' % (len(flagged[key]), label))
    for key, label in FLAGS:
        if flagged[key]:
            print('\n%s (%d):' % (label, len(flagged[key])))
            for path in flagged[key]:
                print('  ' + path)
    print('\nPAGE | og:title | og:description | IMAGE WIDTHxHEIGHT TYPE')
    for c in cards:
        print(line(c))
    return 0


if __name__ == '__main__':
    sys.exit(main())
