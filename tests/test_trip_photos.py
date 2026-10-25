"""tools/trip_photos.py (Phase 9, gap8-03): photos added to a trip that is on the site, on synthetic trips in a temp dir.
photos.web_copies (sips and cwebp) is replaced by a recorder that writes placeholder copies, as tests/test_add_trip.py
does; subprocess.run (sips for HEIC/PNG) by a recorder too. Numbering after the highest photo, the dNN- prefix of a
day, --cover, --dry-run, the entries appended with an empty alt and the rest of the file kept, and the closing lines."""
import contextlib
import importlib
import io
import os
import tempfile
import unittest
from unittest import mock

import helpers
from helpers import photo, LANDSCAPE

import frontmatter
import photos as photolib

trip_photos = importlib.import_module('trip_photos')


def tree(root):
    out = {}
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            p = os.path.join(dirpath, n)
            with open(p, 'rb') as fh:
                out[os.path.relpath(p, root)] = fh.read()
    return out


class TripPhotosTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.trips = os.path.join(tmp.name, 'trips')
        self.src = os.path.join(tmp.name, 'src')
        os.makedirs(self.src)
        helpers.make_trip(self.trips, 'synp-ridge', title='Synthetic Ridge', date='2026-03-01', track=True,
                          body='Synthetic words.\n',
                          photos=[photo('photos/%02d.webp' % n, LANDSCAPE, alt='Synthetic alt %d' % n, sm=True) for n in (1, 2, 3)])
        helpers.make_trip(self.trips, 'synp-tour', title='Synthetic Tour', kind='multi-day', date='2026-04-01',
                          days=[{'title': 'Synthetic In', 'date': '2026-04-01',
                                 'photos': [photo('photos/d01-01.webp', LANDSCAPE, alt='Synthetic day alt', sm=True)]},
                                {'title': 'Synthetic Out', 'date': '2026-04-02'}])
        self.copies, self.runs = [], []
        for target, name, value in ((trip_photos, 'TRIPS', self.trips), (photolib, 'web_copies', self.fake_copies),
                                    (photolib.subprocess, 'run', self.fake_run)):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)

    def fake_copies(self, src, dst_base, *a, **kw):
        self.copies.append((os.path.basename(src), os.path.relpath(dst_base, self.trips)))
        for suffix in ('.webp', '.sm.webp', '.th.webp'):
            with open(dst_base + suffix, 'wb') as fh:
                fh.write(b'placeholder')
        return 'webp', 1600, 1200

    def fake_run(self, args, *a, **kw):
        self.runs.append([str(x) for x in args])
        with open(args[-1], 'wb') as fh:          # sips writes its --out file
            fh.write(b'jpeg')

    def shots(self, *names):
        for n in names:
            with open(os.path.join(self.src, n), 'wb') as fh:
                fh.write(b'')
        return [os.path.join(self.src, n) for n in names]

    def run_tool(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = trip_photos.main(list(argv))
        return code, out.getvalue()

    def front(self, *parts):
        with open(os.path.join(self.trips, *parts), encoding='utf-8') as fh:
            return frontmatter.split(fh.read())

    def test_new_photos_are_numbered_after_the_highest(self):
        before_meta, before_body = self.front('synp-ridge', 'index.md')
        code, out = self.run_tool('synp-ridge', *self.shots('b.jpg', 'a.jpg'))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.copies, [('b.jpg', 'synp-ridge/photos/04'), ('a.jpg', 'synp-ridge/photos/05')])
        meta, body = self.front('synp-ridge', 'index.md')
        self.assertEqual(body, before_body)
        self.assertEqual(meta['photos'][:3], before_meta['photos'])
        self.assertEqual(meta['photos'][3:], [{'file': 'photos/04.webp', 'w': 1600, 'h': 1200, 'alt': ''},
                                              {'file': 'photos/05.webp', 'w': 1600, 'h': 1200, 'alt': ''}])
        self.assertNotIn('cover_photo', meta)
        self.assertIn('Next: describe each photo in content/trips/synp-ridge/index.md: 2 empty alt: lines (photos/04.webp, '
                      'photos/05.webp)', out)
        self.assertIn('Publish: python3 tools/publish.py synp-ridge --push (no render needed)', out)

    def test_an_empty_published_at_line_is_kept(self):
        # the line add_trip writes for Eric to fill (Phase 9, seo-10) survives the round trip
        index = os.path.join(self.trips, 'synp-ridge', 'index.md')
        with open(index, encoding='utf-8') as fh:
            text = fh.read()
        with open(index, 'w', encoding='utf-8') as fh:
            fh.write(text.replace('\n---\n', '\npublished_at:\n---\n', 1))
        code, out = self.run_tool('synp-ridge', *self.shots('a.jpg'))
        self.assertEqual(code, 0, out)
        meta, _body = self.front('synp-ridge', 'index.md')
        self.assertIn('published_at', meta)                 # present, empty
        self.assertIsNone(meta['published_at'])
        self.assertEqual(len(meta['photos']), 4)

    def test_a_folder_gives_its_photos_in_name_order_and_heic_goes_through_sips(self):
        self.shots('2.heic', '1.jpg', 'notes.txt')
        code, _out = self.run_tool('synp-ridge', self.src)
        self.assertEqual(code, 0)
        self.assertEqual([dst for _s, dst in self.copies], ['synp-ridge/photos/04', 'synp-ridge/photos/05'])
        self.assertEqual(self.copies[0][0], '1.jpg')
        self.assertEqual(self.runs[0][:3], ['sips', '-s', 'format'])
        self.assertFalse(os.path.exists(os.path.join(self.trips, 'synp-ridge', '.convert.jpg')))

    def test_a_day_gets_the_dNN_prefix(self):
        code, _out = self.run_tool('synp-tour', *self.shots('x.jpg'), '--day', '1')
        self.assertEqual(code, 0)
        self.assertEqual(self.copies, [('x.jpg', 'synp-tour/photos/d01-02')])
        meta, _body = self.front('synp-tour', 'days', '01.md')
        self.assertEqual([p['file'] for p in meta['photos']], ['photos/d01-01.webp', 'photos/d01-02.webp'])
        code, _out = self.run_tool('synp-tour', *self.shots('y.jpg'), '--day', '02')
        self.assertEqual(self.copies[-1], ('y.jpg', 'synp-tour/photos/d02-01'))

    def test_a_journal_day_is_found_by_its_number(self):
        helpers.make_series(self.trips, slug='synp-journal', title='Synthetic Journal')
        code, out = self.run_tool('synp-journal', *self.shots('z.jpg'), '--day', '1')
        self.assertEqual(code, 0, out)
        self.assertEqual(self.copies, [('z.jpg', 'synp-journal/photos/d001-03')])     # after the day's two photos
        self.assertIn('content/trips/synp-journal/days/001.md', out)

    def test_cover_sets_cover_photo_to_the_first_added(self):
        self.run_tool('synp-ridge', *self.shots('a.jpg', 'b.jpg'), '--cover')
        self.assertEqual(self.front('synp-ridge', 'index.md')[0]['cover_photo'], 'photos/04.webp')
        self.run_tool('synp-tour', *self.shots('c.jpg'), '--day', '01', '--cover')
        self.assertEqual(self.front('synp-tour', 'index.md')[0]['cover_photo'], 'photos/d01-02.webp')
        self.assertTrue(os.path.exists(os.path.join(self.trips, 'synp-tour', 'photos', 'd01-02.th.webp')))

    def test_dry_run_writes_nothing(self):
        before = tree(self.trips)
        code, out = self.run_tool('synp-ridge', *self.shots('a.jpg'), '--cover', '--dry-run')
        self.assertEqual(code, 0)
        self.assertEqual(tree(self.trips), before)
        self.assertEqual(self.copies, [])
        self.assertIn('would copy %s -> content/trips/synp-ridge/photos/04.webp' % os.path.join(self.src, 'a.jpg'), out)
        self.assertIn('set cover_photo: photos/04.webp', out)
        self.assertIn('dry run: nothing written', out)

    def test_refusals(self):
        for argv in (('synp-none', *self.shots('a.jpg')), ('synp-tour', *self.shots('b.jpg'), '--day', '09'),
                     ('synp-ridge', os.path.join(self.src, 'nothing-here.txt'))):
            with self.subTest(argv=argv[:1] + argv[2:]):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
                    trip_photos.main(list(argv))
                self.assertEqual(cm.exception.code, 2)
        self.assertEqual(self.copies, [])


if __name__ == '__main__':
    unittest.main()
