"""tools/tidy.py (Phase 8) on a synthetic tree laid out like the checkout: what it lists, how it marks a copy under
content/ and assets/, and that --delete removes only the copies of generated files, under rendered/ and _site/."""
import contextlib
import importlib
import io
import os
import tempfile
import time
import unittest

import helpers  # noqa: F401  (puts tools/ on sys.path)

tidy = importlib.import_module('tidy')


def write(path, text='x', mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


class TidyTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        r = self.root = tmp.name
        now = time.time()
        self.p = lambda *parts: os.path.join(r, *parts)    # noqa: E731
        write(self.p('rendered', 'trips', 'synt-a', 'meta.json'), '{}')
        write(self.p('rendered', 'trips', 'synt-a', 'meta 3.json'), '{}')
        write(self.p('rendered', 'trips', 'synt-a', 'g64.svg 4.html'), 's')
        write(self.p('rendered', 'trips', 'synt-b 2', 'meta.json'), '{}')                 # a copied folder
        write(self.p('assets', 'css', 'base.css'), 'c', now - 100)
        write(self.p('assets', 'css', 'base 2.css'), 'c newer', now)                     # hand-written: compared, kept
        write(self.p('assets', 'css', 'pages 2', 'trips.css'), 't')                       # a copied folder of sources
        os.makedirs(self.p('_site', 'trips', 'synt-a 2'))                                  # an empty copied folder
        write(self.p('content', 'trips', 'synt-a', 'index.md'), 'same', now - 100)
        write(self.p('content', 'trips', 'synt-a', 'index 2.md'), 'same', now - 50)        # identical
        write(self.p('content', 'trips', 'synt-a', 'track.gpx'), 'new', now)
        write(self.p('content', 'trips', 'synt-a', 'track 2.gpx'), 'old', now - 500)       # older
        write(self.p('content', 'trips', 'synt-a', 'orphan 3.md'), 'orphan')               # no original: DIFFERS
        write(self.p('content', 'trips', 'synt-a', 'photos', '01.webp'), 'p', now - 500)
        write(self.p('content', 'trips', 'synt-a', 'photos 2', '01.webp'), 'q', now)       # a folder, newer: DIFFERS
        write(self.p('content', 'trips', 'synt-a', 'notes.md'), 'kept')
        write(self.p('.git', 'index'), 'live')
        write(self.p('.git', 'index 2'), 'stray')
        write(self.p('docs', 'plan 2.md'), 'not looked at')                                # outside the four folders

    def run_tidy(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tidy.main(list(argv), root=self.root)
        return code, out.getvalue()

    def test_original_of(self):
        self.assertEqual(tidy.original_of('a/meta 3.json'), 'a/meta.json')
        self.assertEqual(tidy.original_of('a/g64.svg 4.html'), 'a/g64.svg.html')
        self.assertEqual(tidy.original_of('trips/synt-lap 2'), 'trips/synt-lap')
        self.assertEqual(tidy.original_of('a/region.base 4.svg'), 'a/region.base.svg')

    def test_the_list_names_every_copy_once_and_marks_content_copies(self):
        code, out = self.run_tidy()
        self.assertEqual(code, 0)
        lines = out.splitlines()
        for want in ('copy      rendered/trips/synt-a/meta 3.json', 'copy      rendered/trips/synt-a/g64.svg 4.html',
                     'copy      rendered/trips/synt-b 2/', 'DIFFERS   assets/css/base 2.css', 'DIFFERS   assets/css/pages 2/',
                     'copy      _site/trips/synt-a 2/',
                     'identical content/trips/synt-a/index 2.md', 'older     content/trips/synt-a/track 2.gpx',
                     'DIFFERS   content/trips/synt-a/orphan 3.md', 'DIFFERS   content/trips/synt-a/photos 2/',
                     'copy      .git/index 2'):
            self.assertIn(want, lines)
        self.assertNotIn('rendered/trips/synt-b 2/meta.json', out)            # inside a copied folder: not listed again
        self.assertNotIn('docs/plan 2.md', out)
        self.assertNotIn('.git/index\n', out)
        self.assertIn('10 conflict copies (_site 1, assets 2, content 4, rendered 3)', out)
        self.assertIn('tidy.py --delete removes the 4 under rendered/, _site/', out)
        by_hand = [ln for ln in lines if ln.startswith('under content/ and assets/')][0]
        self.assertIn(': rm -r ', by_hand)
        for p in ('content/trips/synt-a/photos 2', 'content/trips/synt-a/index 2.md', 'content/trips/synt-a/orphan 3.md',
                  'content/trips/synt-a/track 2.gpx', 'assets/css/base 2.css', 'assets/css/pages 2'):
            self.assertIn('"%s"' % p, by_hand)
        self.assertIn('rm ".git/index 2"', out)
        self.assertTrue(os.path.exists(self.p('rendered', 'trips', 'synt-a', 'meta 3.json')))     # listing deletes nothing

    def test_delete_removes_only_the_ignored_copies(self):
        code, out = self.run_tidy('--delete')
        self.assertEqual(code, 0)
        for gone in (('rendered', 'trips', 'synt-a', 'meta 3.json'), ('rendered', 'trips', 'synt-b 2'), ('_site', 'trips', 'synt-a 2')):
            self.assertFalse(os.path.lexists(self.p(*gone)), gone)
        for kept in (('rendered', 'trips', 'synt-a', 'meta.json'), ('content', 'trips', 'synt-a', 'index 2.md'),
                     ('content', 'trips', 'synt-a', 'photos 2', '01.webp'), ('.git', 'index 2'), ('.git', 'index'),
                     ('docs', 'plan 2.md'), ('assets', 'css', 'base 2.css'), ('assets', 'css', 'pages 2', 'trips.css')):
            self.assertTrue(os.path.exists(self.p(*kept)), kept)
        self.assertIn('4 deleted', out)
        code, out = self.run_tidy()
        self.assertIn('6 conflict copies (assets 2, content 4)', out)


if __name__ == '__main__':
    unittest.main()
