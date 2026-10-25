"""tools/share_preview.py (Phase 14, seo-13) on a synthetic built site written by hand: which pages it reads, the
flags and their counts, the line per page, the image sizes it reads from the head or the file, and that it writes
nothing into the site."""
import contextlib
import importlib
import io
import os
import struct
import tempfile
import unittest
import zlib

import helpers  # noqa: F401  (puts tools/ on sys.path)

share_preview = importlib.import_module('share_preview')

URL = share_preview.SITE_URL
LONG_TITLE = 'Synthetic page with a title written long enough to pass sixty characters'
HOME = ('./ | Synthetic home | A short synthetic description & more. | '
        'trips/synt-a/photos/01.jpg 1200x630 jpeg')
SYNT_B = ('trips/synt-b/ | Synthetic B | A synthetic page with a tall image. | '
          'trips/synt-b/photos/01.webp 1200x1600 webp')
SYNT_C = 'trips/synt-c/ | %s | A synthetic description cut short… | no image' % LONG_TITLE
SYNT_D = 'trips/synt-d/ | Synthetic D | Its image size is read from the file. | trips/synt-d/photos/01.png 40x20 png'
SYNT_E = 'trips/synt-e/ | Synthetic E | Its image is not in the build. | trips/synt-e/photos/02.webp ? webp'


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as fh:
        fh.write(data.encode('utf-8') if isinstance(data, str) else data)


def page(title, description, image=None, extra='', robots=False):
    """A built page's head (and a body that must not be read), in the order core.document writes it."""
    tags = ['<meta charset="utf-8">']
    if robots:
        tags.append('<meta name="robots" content="noindex">')
    tags += ['<title>%s</title>' % title, '<meta property="og:title" content="%s">' % title,
             '<meta property="og:description" content="%s">' % description]
    if image:
        tags.append('<meta property="og:image" content="%s">' % image)
    tags.append(extra)
    return ('<!doctype html>\n<html lang="en"><head>%s<script>var d=document.documentElement</script></head>'
            '<body><svg><title>Not the page</title></svg><meta property="og:title" content="In the body"></body>'
            '</html>' % ''.join(tags))


def png(width, height):
    """A minimal valid PNG: 8-bit RGB, every pixel black."""
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    rows = b''.join(b'\0' + b'\0' * 3 * width for _ in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def size_tags(w, h, mime):
    return ('<meta property="og:image:type" content="%s"><meta property="og:image:width" content="%d">'
            '<meta property="og:image:height" content="%d">' % (mime, w, h))


def listing(root):
    return sorted(os.path.relpath(os.path.join(d, f), root) for d, _dirs, files in os.walk(root) for f in files)


class SharePreviewTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        s = self.site = tmp.name
        p = lambda *parts: os.path.join(s, *parts)    # noqa: E731
        write(p('index.html'), page('Synthetic home', 'A short synthetic description &amp; more.',
                                    URL + 'trips/synt-a/photos/01.jpg', size_tags(1200, 630, 'image/jpeg')))
        write(p('trips', 'synt-b', 'index.html'), page('Synthetic B', 'A synthetic page with a tall image.',
                                                       URL + 'trips/synt-b/photos/01.webp',
                                                       size_tags(1200, 1600, 'image/webp')))
        write(p('trips', 'synt-c', 'index.html'), page(LONG_TITLE, 'A synthetic description cut short…'))
        write(p('trips', 'synt-c', 'map', 'index.html'), page('Synthetic C map', 'A helper.', robots=True))
        write(p('trips', 'synt-d', 'index.html'), page('Synthetic D', 'Its image size is read from the file.',
                                                       URL + 'trips/synt-d/photos/01.png'))
        write(p('trips', 'synt-d', 'photos', '01.png'), png(40, 20))
        write(p('trips', 'synt-d', 'index 2.html'), page('A conflict copy', 'Never read.'))
        write(p('trips', 'synt-e', 'index.html'), page('Synthetic E', 'Its image is not in the build.',
                                                       URL + 'trips/synt-e/photos/02.webp'))
        write(p('404.html'), page('Page not found', 'Not here.', robots=True))

    def run_tool(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = share_preview.main(list(args))
        return code, out.getvalue().splitlines()

    def test_summary_counts_and_flagged_pages(self):
        code, lines = self.run_tool('--site', self.site)
        self.assertEqual(code, 0)
        self.assertEqual(lines[:6], [
            '7 pages: 5 indexable, 2 noindex left out',
            '    1  no og:image',
            "    1  og:description ends in '…'",
            '    1  og:title over 60 characters',
            '    2  image not JPEG or PNG',
            '    1  portrait image',
        ])
        text = '\n'.join(lines)
        self.assertIn('no og:image (1):\n  trips/synt-c/\n', text)
        self.assertIn("og:description ends in '…' (1):\n  trips/synt-c/\n", text)
        self.assertIn('og:title over 60 characters (1):\n  trips/synt-c/\n', text)
        self.assertIn('image not JPEG or PNG (2):\n  trips/synt-b/\n  trips/synt-e/\n', text)
        self.assertIn('portrait image (1):\n  trips/synt-b/\n', text)

    def test_one_line_per_indexable_page(self):
        _code, lines = self.run_tool('--site', self.site)
        head = lines.index('PAGE | og:title | og:description | IMAGE WIDTHxHEIGHT TYPE')
        self.assertEqual(lines[head + 1:], [HOME, SYNT_B, SYNT_C, SYNT_D, SYNT_E])
        text = '\n'.join(lines)
        for left_out in ('synt-c/map/', '404', 'conflict copy', 'In the body', 'Not the page'):
            self.assertNotIn(left_out, text)

    def test_writes_nothing_into_the_site(self):
        before = listing(self.site)
        self.run_tool('--site', self.site)
        self.assertEqual(listing(self.site), before)

    def test_missing_site_folder(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()) as out:
            code = share_preview.main(['--site', os.path.join(self.site, 'no-such-build')])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), '')
        self.assertIn('no built site at', err.getvalue())

    def test_image_headers(self):
        def riff(chunk, body):
            return b'RIFF' + struct.pack('<I', 12 + len(body)) + b'WEBP' + chunk + struct.pack('<I', len(body)) + body
        files = {
            'a.png': png(3, 5),
            'vp8.webp': riff(b'VP8 ', b'\0\0\0\x9d\x01\x2a' + struct.pack('<HH', 640, 480) + b'\0' * 4),
            'vp8l.webp': riff(b'VP8L', b'\x2f' + struct.pack('<I', (300 - 1) | (500 - 1) << 14) + b'\0' * 4),
            'vp8x.webp': riff(b'VP8X', b'\0' * 4 + struct.pack('<I', 2000 - 1)[:3] + struct.pack('<I', 1000 - 1)[:3]),
            'b.jpg': (b'\xff\xd8' + b'\xff\xe0' + struct.pack('>H', 16) + b'JFIF\0' + b'\0' * 9
                      + b'\xff\xdb' + struct.pack('>H', 4) + b'\0\0'
                      + b'\xff\xc0' + struct.pack('>HBHH', 17, 8, 200, 400) + b'\0' * 10 + b'\xff\xd9'),
            'c.gif': b'GIF89a' + b'\0' * 26,
        }
        want = {'a.png': ('png', 3, 5), 'vp8.webp': ('webp', 640, 480), 'vp8l.webp': ('webp', 300, 500),
                'vp8x.webp': ('webp', 2000, 1000), 'b.jpg': ('jpeg', 400, 200), 'c.gif': (None, None, None)}
        for name, data in files.items():
            path = os.path.join(self.site, 'img', name)
            write(path, data)
            self.assertEqual(share_preview.image_header(path), want[name], name)
        self.assertEqual(share_preview.image_header(os.path.join(self.site, 'img', 'none.png')), (None, None, None))


if __name__ == '__main__':
    unittest.main()
