"""Phase 4: the card-size photo copies (.th), pinned to contract-phase4.md sections 5.3, 10 and 10.5.

Three things have to agree to the pixel, and each is checked against the other two here:

  tools/lib/photos.thumb_size(w, h)   the size tools/thumbs.py and tools/add_trip.py write the copy at
  sitegen core.thumb_width(photo)     the width the page declares for it, in the phone-only <source> of a card cover
                                      (10.5: never in an <img>'s own srcset)
  tools/thumbs.py                     which photos get a copy, where it goes, and what a run may touch

Nothing here needs cwebp or sips: photolib.thumb_copy is replaced by a recorder that writes a small placeholder file,
and photolib.have_cwebp by a fixed answer. photos.web_copies (which needs sips) is not tested. Every trip is synthetic,
written to a temp dir with tests/helpers.py under a slug that starts with PREFIX; content.TRIPS_DIR points at that temp
dir for the whole of every test, so tools/thumbs.py can never load, or write beside, a real trip.
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import photos as photolib  # noqa: E402
from sitegen import core  # noqa: E402
import thumbs  # noqa: E402  (tools/thumbs.py: tools/ is on sys.path)

import helpers  # noqa: E402
from helpers import photo, LANDSCAPE, PORTRAIT, SQUARE  # noqa: E402

PREFIX = 'syn-th-'           # every fixture slug starts with it; no real trip's slug does
CARD_SIZES = '(min-width: 760px) 400px, 112px'
PLACEHOLDER = b'th' * 1536   # what the recorder writes: 3072 bytes, so a run reports '3 KB'

# (w, h) of a photo -> (w, h) of its .th copy: 320 px on the short edge, the long edge in proportion, rounded. The first
# six are the shapes the contract names (every distinct size in the content when Phase 4 was built is one of them or a
# 4:3 / 3:4 photo); the rest are the plain cases around them.
SIZES = [
    ((1600, 1200), (427, 320)),    # 4:3
    ((1200, 1600), (320, 427)),    # 3:4
    ((1600, 1577), (325, 320)),    # near square
    ((3810, 1600), (762, 320)),    # panorama
    ((1600, 731), (700, 320)),     # wide crop
    ((738, 1600), (320, 694)),     # tall crop
    ((1000, 1000), (320, 320)),    # square
    ((1600, 900), (569, 320)),     # 16:9
    ((1600, 1067), (480, 320)),    # 3:2
    ((4032, 3024), (427, 320)),    # a phone original
    ((640, 320), (640, 320)),      # already 320 px on the short edge
    ((320, 320), (320, 320)),
]
# the exact halves: 853 x 640 would be 426.5 px wide. Both sides use Python's round(), which takes a half to the even
# number, and the copies in content/ were written with it, so the rule is part of the contract between the two
HALVES = [
    ((853, 640), (426, 320)),
    ((855, 640), (428, 320)),
    ((640, 853), (320, 426)),
    ((640, 855), (320, 428)),
    ((258, 256), (322, 320)),
    ((262, 256), (328, 320)),
]


def tree(root):
    """Every file under root as {relative path: bytes}."""
    out = {}
    for base, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(base, name)
            with open(path, 'rb') as fh:
                out[os.path.relpath(path, root)] = fh.read()
    return out


class ThumbSizeTests(unittest.TestCase):

    def test_the_short_edge_is_320_px_on_both_sides(self):
        self.assertEqual(photolib.THUMB_EDGE, 320)
        self.assertEqual(core.THUMB_EDGE, 320)
        self.assertEqual(photolib.THUMB_EDGE, core.THUMB_EDGE)

    def test_thumb_size_by_shape(self):
        for (w, h), want in SIZES:
            with self.subTest(photo=(w, h)):
                got = photolib.thumb_size(w, h)
                self.assertEqual(got, want)
                self.assertEqual(min(got), 320)                      # the short edge is the fixed one
                self.assertEqual(got[0] >= got[1], w >= h)            # and the orientation is kept
                self.assertTrue(all(type(v) is int for v in got), got)

    def test_thumb_size_is_symmetric_in_width_and_height(self):
        for (w, h), _want in SIZES + HALVES:
            with self.subTest(photo=(w, h)):
                tw, th = photolib.thumb_size(w, h)
                self.assertEqual(photolib.thumb_size(h, w), (th, tw))

    def test_an_exact_half_goes_to_the_even_number(self):
        for (w, h), want in HALVES:
            with self.subTest(photo=(w, h)):
                self.assertEqual(max(w, h) * 320 % min(w, h) * 2, min(w, h))   # the long edge really lands on a half
                self.assertEqual(photolib.thumb_size(w, h), want)

    def test_the_edge_argument_sets_the_short_edge(self):
        self.assertEqual(photolib.thumb_size(1600, 1200, 160), (213, 160))
        self.assertEqual(photolib.thumb_size(1200, 1600, 400), (400, 533))
        self.assertEqual(photolib.thumb_size(1600, 1200, edge=800), (1067, 800))
        self.assertEqual(photolib.thumb_size(1600, 1200, edge=photolib.THUMB_EDGE), photolib.thumb_size(1600, 1200))
        self.assertEqual(photolib.thumb_size(1600, 1200, edge=1200), (1600, 1200))

    def test_thumb_width_is_the_width_thumb_size_gives(self):
        # sitegen writes thumb_width into the srcset; tools/thumbs.py writes the file at thumb_size
        for (w, h), want in SIZES + HALVES:
            with self.subTest(photo=(w, h)):
                self.assertEqual(core.thumb_width({'w': w, 'h': h}), want[0])
                self.assertEqual(core.thumb_width({'w': w, 'h': h}), photolib.thumb_size(w, h)[0])
                self.assertIs(type(core.thumb_width({'w': w, 'h': h})), int)

    def test_thumb_width_agrees_with_thumb_size_for_every_shape_of_a_1600_px_photo(self):
        # the published photos are 1600 px on the long edge: every short edge from a 4:1 strip to a square, both ways up
        bad = []
        for short in range(400, 1601):
            for w, h in ((1600, short), (short, 1600)):
                if core.thumb_width({'w': w, 'h': h}) != photolib.thumb_size(w, h)[0]:
                    bad.append((w, h))
        self.assertEqual(bad, [])

    def test_thumb_width_reads_only_the_recorded_size(self):
        p = {'file': 'photos/01.webp', 'sm': 'photos/01.sm.webp', 'th': 'photos/01.th.webp', 'w': 3810, 'h': 1600, 'alt': 'x', 'caption': ''}
        before = dict(p)
        self.assertEqual(core.thumb_width(p), 762)
        self.assertEqual(p, before)


class ThumbsFixture(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        self.copies = []          # (src, dst, w, h) of every thumb_copy call
        self.said = []            # every line run() says
        for target, name, kw in ((photolib, 'thumb_copy', {'side_effect': self.fake_copy}),
                                 (photolib, 'have_cwebp', {'return_value': True}),
                                 (content, 'TRIPS_DIR', {'new': self.tmp})):
            patcher = mock.patch.object(target, name, **kw)
            patcher.start()
            self.addCleanup(patcher.stop)
        # tools/thumbs.py works on the two modules patched above, not on copies of them
        self.assertIs(thumbs.photolib, photolib)
        self.assertIs(thumbs.content, content)

    def tearDown(self):
        stray = [name for name in sorted(os.listdir(self.tmp)) if not name.startswith(PREFIX)]
        self.assertEqual(stray, [], 'fixture folders without the %r prefix' % PREFIX)
        outside = [dst for _src, dst, _w, _h in self.copies if not dst.startswith(self.tmp + os.sep)]
        self.assertEqual(outside, [], 'a copy was written outside the temp dir')

    # ------------------------------------------------------------ helpers

    def fake_copy(self, src, dst, w, h, quality=72):
        """photolib.thumb_copy without cwebp: note the call, write a placeholder where the copy would go."""
        self.copies.append((src, dst, w, h))
        with open(dst, 'wb') as fh:
            fh.write(PLACEHOLDER)
        return photolib.thumb_size(w, h)

    def make(self, name, **kw):
        """One synthetic trip folder <tmp>/syn-th-<name>/; returns its slug."""
        slug = PREFIX + name
        self.assertFalse(os.path.lexists(os.path.join(ROOT, 'content', 'trips', slug)), 'fixture slug %r names a real trip' % slug)
        helpers.make_trip(self.tmp, slug, **kw)
        return slug

    def load(self, slug):
        return helpers.load(self.tmp, slug)

    def path(self, slug, *parts):
        return os.path.join(self.tmp, slug, *parts)

    def auto(self):
        """Three photos; the automatic cover is the second (the first one wide enough to lead a page)."""
        return self.make('auto', date='2026-06-01', track=True, body='Synthetic write-up for a test.',
                         photos=[photo('photos/01.webp', PORTRAIT), photo('photos/02.webp', LANDSCAPE, sm=True),
                                 photo('photos/03.webp', (1600, 900))])

    def done(self):
        """One photo whose card-size copy is already on disk."""
        slug = self.make('done', date='2026-05-01', track=True, photos=[photo('photos/01.webp', LANDSCAPE)])
        with open(self.path(slug, 'photos', '01.th.webp'), 'wb') as fh:
            fh.write(b'an earlier copy')
        return slug

    def tour(self):
        """A multi-day trip with day photos only: the cover is day 1's second photo; day 2's photo has no recorded size."""
        return self.make('tour', kind='multi-day', date='2026-03-10', end_date='2026-03-11',
                         days=[{'title': 'Synthetic Day One', 'date': '2026-03-10',
                                'photos': [photo('photos/d01-01.webp', PORTRAIT), photo('photos/d01-02.webp', (1600, 900))]},
                               {'title': 'Synthetic Day Two', 'date': '2026-03-11', 'photos': [photo('photos/d02-01.webp', None)]}])

    def gone(self):
        """A declared photo whose file is not in the folder (the automatic pick does not look at the disk)."""
        return self.make('gone', date='2026-02-01', track=True, photos=[photo('photos/01.webp', SQUARE)], missing=('photos/01.webp',))

    def run_thumbs(self, slugs, **kw):
        return thumbs.run([self.load(s) for s in slugs], say=self.said.append, **kw)

    def main(self, *argv):
        """thumbs.main(argv) -> (exit code, stdout lines, stderr lines)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = thumbs.main(list(argv))
        return code, out.getvalue().splitlines(), err.getvalue().splitlines()

    def copied(self):
        """The copies written, as paths relative to the temp dir."""
        return [os.path.relpath(dst, self.tmp) for _src, dst, _w, _h in self.copies]


class WantedTests(ThumbsFixture):

    def test_the_cover_only_by_default(self):
        t = self.load(self.auto())
        self.assertEqual(t['cover']['photo']['file'], 'photos/02.webp')
        got = thumbs.wanted(t)
        self.assertEqual([p['file'] for p in got], ['photos/02.webp'])
        self.assertIs(got[0], t['cover']['photo'])          # the trip's own photo entry, not a copy of it
        self.assertEqual(thumbs.wanted(t, all_photos=False), got)

    def test_an_explicit_cover_is_the_one_wanted(self):
        slug = self.make('named', cover_photo='photos/03.webp',
                         photos=[photo('photos/01.webp', LANDSCAPE), photo('photos/02.webp', LANDSCAPE), photo('photos/03.webp', PORTRAIT)])
        self.assertEqual([p['file'] for p in thumbs.wanted(self.load(slug))], ['photos/03.webp'])

    def test_a_day_photo_that_is_the_cover_is_wanted(self):
        t = self.load(self.tour())
        self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), ('day', 'photos/d01-02.webp'))
        got = thumbs.wanted(t)
        self.assertEqual([p['file'] for p in got], ['photos/d01-02.webp'])
        self.assertIs(got[0], t['days'][0]['photos'][1])

    def test_a_trip_without_photos_wants_nothing(self):
        t = self.load(self.make('bare', track=True))
        self.assertIsNone(t['cover'])
        self.assertEqual(thumbs.wanted(t), [])
        self.assertEqual(thumbs.wanted(t, all_photos=True), [])

    def test_a_cover_without_a_recorded_size_is_skipped(self):
        # the copy's size is computed from the recorded size, so there is nothing to compute it from
        for name, entry in (('nosize', photo('photos/01.webp', None)),
                            ('width-only', {'file': 'photos/01.webp', 'w': 1600, 'alt': 'Width only'}),
                            ('height-only', {'file': 'photos/01.webp', 'h': 1200, 'alt': 'Height only'})):
            with self.subTest(name):
                t = self.load(self.make(name, photos=[entry]))
                self.assertEqual(t['cover']['photo']['file'], 'photos/01.webp')
                self.assertEqual(thumbs.wanted(t), [])
                self.assertEqual(thumbs.wanted(t, all_photos=True), [])

    def test_all_photos_is_every_declared_photo_the_trips_own_first_then_each_days(self):
        slug = self.make('all', kind='multi-day', date='2026-03-10', end_date='2026-03-11',
                         photos=[photo('photos/01.webp', PORTRAIT), photo('photos/02.webp', LANDSCAPE)],
                         days=[{'photos': [photo('photos/d01-01.webp', LANDSCAPE), photo('photos/d01-02.webp', SQUARE)]},
                               {},
                               {'photos': [photo('photos/d03-01.webp', PORTRAIT)]}])
        t = self.load(slug)
        got = thumbs.wanted(t, all_photos=True)
        self.assertEqual([p['file'] for p in got],
                         ['photos/01.webp', 'photos/02.webp', 'photos/d01-01.webp', 'photos/d01-02.webp', 'photos/d03-01.webp'])
        self.assertIs(got[0], t['photos'][0])
        self.assertIs(got[4], t['days'][2]['photos'][0])
        self.assertEqual([p['file'] for p in thumbs.wanted(t)], ['photos/02.webp'])     # without the flag: the cover alone

    def test_all_photos_skips_photos_without_a_recorded_size(self):
        t = self.load(self.tour())
        self.assertEqual([p['file'] for p in thumbs.wanted(t, all_photos=True)], ['photos/d01-01.webp', 'photos/d01-02.webp'])
        slug = self.make('mixed', photos=[photo('photos/01.webp', None), photo('photos/02.webp', LANDSCAPE),
                                          {'file': 'photos/03.webp', 'w': 1600, 'alt': 'Width only'}])
        self.assertEqual([p['file'] for p in thumbs.wanted(self.load(slug), all_photos=True)], ['photos/02.webp'])

    def test_a_photo_declared_twice_is_wanted_once(self):
        slug = self.make('twice', kind='multi-day', date='2026-03-10',
                         photos=[photo('photos/01.webp', LANDSCAPE), photo('photos/01.webp', LANDSCAPE), photo('photos/02.webp', PORTRAIT)],
                         days=[{'photos': [photo('photos/02.webp', PORTRAIT), photo('photos/d01-01.webp', LANDSCAPE)]}])
        t = self.load(slug)
        got = thumbs.wanted(t, all_photos=True)
        self.assertEqual([p['file'] for p in got], ['photos/01.webp', 'photos/02.webp', 'photos/d01-01.webp'])
        self.assertIs(got[0], t['photos'][0])               # the first declaration is the one kept

    def test_wanted_changes_nothing_in_the_trip(self):
        t = self.load(self.auto())
        before = ([dict(p) for p in t['photos']], dict(t['cover']['photo']))
        thumbs.wanted(t)
        thumbs.wanted(t, all_photos=True)
        self.assertEqual(([dict(p) for p in t['photos']], dict(t['cover']['photo'])), before)
        self.assertEqual(self.copies, [])


class ThPathTests(ThumbsFixture):

    def test_the_copy_sits_beside_the_photo_with_th_before_the_extension(self):
        t = self.load(self.auto())
        self.assertEqual(thumbs.th_path(t, t['photos'][1]), self.path(t['slug'], 'photos', '02.th.webp'))
        self.assertEqual(thumbs.th_path(t, {'file': 'photos/d001-02.webp'}), self.path(t['slug'], 'photos', 'd001-02.th.webp'))
        self.assertEqual(thumbs.th_path(t, {'file': 'photos/01.jpg'}), self.path(t['slug'], 'photos', '01.th.jpg'))
        self.assertEqual(thumbs.th_path(t, {'file': 'photos/ridge.v2.webp'}), self.path(t['slug'], 'photos', 'ridge.v2.th.webp'))

    def test_the_path_is_under_the_trips_own_folder(self):
        for slug in (self.auto(), self.tour()):
            t = self.load(slug)
            for p in thumbs.wanted(t, all_photos=True):
                with self.subTest(photo=p['file']):
                    path = thumbs.th_path(t, p)
                    self.assertEqual(os.path.dirname(path), os.path.join(t['dir'], 'photos'))
                    self.assertTrue(os.path.basename(path).endswith('.th.webp'))

    def test_it_is_the_file_the_loader_records_as_the_photos_th(self):
        # content._photos looks for <name>.th.<ext>: a copy written at th_path is found on the next load
        slug = self.auto()
        t = self.load(slug)
        self.assertEqual([p['th'] for p in t['photos']], [None, None, None])
        helpers.touch(thumbs.th_path(t, t['photos'][1]))
        again = self.load(slug)
        self.assertEqual([p['th'] for p in again['photos']], [None, 'photos/02.th.webp', None])
        self.assertEqual(os.path.join(again['dir'], again['photos'][1]['th']), thumbs.th_path(again, again['photos'][1]))

    def test_a_copy_on_disk_reaches_the_card_covers_phone_source_at_the_width_thumb_size_gives(self):
        # the three sides together: the file thumbs.py would write, the entry the loader makes of it, the width the page
        # states. 10.5: the page states it in the <source> a card cover offers to phones; the <img> the cover always
        # was sits behind it unchanged, its own srcset still the two candidates (10 put the copy at the head of that
        # srcset)
        slug = self.auto()
        base = core.link('trips/', 'trips/%s/' % slug) + 'photos/'       # the trip's photos as the Trips page links them
        without = core.cover_img(self.load(slug), 'trips/', CARD_SIZES)
        self.assertIn('srcset="%s02.sm.webp 800w, %s02.webp 1600w"' % (base, base), without)
        self.assertNotIn('.th.', without)
        self.assertTrue(without.startswith('<img class="cover-img" '), without)
        self.assertEqual(self.run_thumbs([slug]), (1, 0, 0))
        t = self.load(slug)
        img = core.cover_img(t, 'trips/', CARD_SIZES)
        tw = photolib.thumb_size(1600, 1200)[0]
        self.assertEqual(tw, 427)
        self.assertEqual(core.thumb_width(t['cover']['photo']), tw)
        # (the source declares 106 px, core.CARD_PHONE_SIZES, where CARD_SIZES ends with the real 112 px:
        # contract-phase5.md section 5)
        self.assertEqual(img, '<picture class="cover-pic"><source media="(max-width: 559.98px)" '
                              'srcset="%s02.th.webp %dw, %s02.sm.webp 800w, %s02.webp 1600w" sizes="106px">%s</picture>'
                              % (base, tw, base, base, without))
        self.assertEqual((core.CARD_PHONE_SIZES, CARD_SIZES.rsplit(', ', 1)[1]), ('106px', core.CARD_PHONE_SLOT))
        self.assertIn('sizes="%s"' % CARD_SIZES, without)                # the <img> keeps the string it was handed
        self.assertEqual(img.count('.th.'), 1)
        # a lead image and a full-width slot never state it
        self.assertEqual(core.cover_img(t, 'trips/', CARD_SIZES, eager=True), without.replace(' loading="lazy"', ' fetchpriority="high"'))
        self.assertNotIn('.th.', core.cover_img(t, 'trips/', '(min-width: 1200px) 1248px, ' + core.PHONE_FULL))
        self.assertNotIn('.th.', core.cover_preload(t, 'trips/', CARD_SIZES))


class RunTests(ThumbsFixture):

    def test_only_the_missing_copies_are_written(self):
        auto, done, bare = self.auto(), self.done(), self.make('bare', track=True)
        self.assertEqual(self.run_thumbs([auto, done, bare]), (1, 1, 0))
        self.assertEqual(self.copies, [(self.path(auto, 'photos/02.webp'), self.path(auto, 'photos/02.th.webp'), 1600, 1200)])
        with open(self.path(done, 'photos', '01.th.webp'), 'rb') as fh:
            self.assertEqual(fh.read(), b'an earlier copy')          # the copy that was there is left as it was
        self.assertEqual(len(self.said), 1)
        self.assertTrue(self.said[0].startswith('wrote '), self.said[0])
        self.assertTrue(self.said[0].endswith(os.path.join(auto, 'photos', '02.th.webp') + ' (427 x 320, 3 KB)'), self.said[0])

    def test_a_second_run_writes_nothing(self):
        slugs = [self.auto(), self.tour()]
        self.assertEqual(self.run_thumbs(slugs), (2, 0, 0))
        del self.copies[:], self.said[:]
        self.assertEqual(self.run_thumbs(slugs), (0, 2, 0))
        self.assertEqual(self.copies, [])
        self.assertEqual(self.said, [])

    def test_the_copy_is_asked_for_at_the_photos_recorded_size(self):
        slug = self.make('pano', photos=[photo('photos/01.webp', (3810, 1600))])
        self.assertEqual(self.run_thumbs([slug]), (1, 0, 0))
        self.assertEqual(self.copies, [(self.path(slug, 'photos/01.webp'), self.path(slug, 'photos/01.th.webp'), 3810, 1600)])
        self.assertIn('(762 x 320, ', self.said[0])
        self.assertEqual(photolib.thumb_size(3810, 1600), (762, 320))

    def test_the_counts_are_written_existing_and_missing(self):
        slugs = [self.auto(), self.done(), self.gone(), self.tour(), self.make('bare', track=True)]
        self.assertEqual(self.run_thumbs(slugs), (2, 1, 1))
        self.assertEqual(self.copied(), [os.path.join(slugs[0], 'photos', '02.th.webp'), os.path.join(slugs[3], 'photos', 'd01-02.th.webp')])
        self.assertEqual(self.run_thumbs([]), (0, 0, 0))

    def test_a_missing_source_photo_is_skipped_and_counted(self):
        slug = self.gone()
        self.assertFalse(os.path.exists(self.path(slug, 'photos', '01.webp')))
        self.assertEqual(self.run_thumbs([slug]), (0, 0, 1))
        self.assertEqual(self.copies, [])
        self.assertFalse(os.path.exists(self.path(slug, 'photos', '01.th.webp')))
        self.assertEqual(len(self.said), 1)
        self.assertTrue(self.said[0].startswith('skipped '), self.said[0])
        self.assertIn(os.path.join(slug, 'photos', '01.th.webp'), self.said[0])
        self.assertIn('missing', self.said[0])

    def test_dry_run_writes_nothing_and_says_what_it_would_write(self):
        slugs = [self.auto(), self.done(), self.gone(), self.tour()]
        before = tree(self.tmp)
        self.assertEqual(self.run_thumbs(slugs, dry_run=True), (2, 1, 1))     # the same counts a real run gives
        self.assertEqual(self.copies, [])
        self.assertEqual(tree(self.tmp), before)
        would = [s for s in self.said if s.startswith('would write ')]
        self.assertEqual(len(would), 2)
        self.assertTrue(would[0].endswith(os.path.join(slugs[0], 'photos', '02.th.webp') + ' (427 x 320)'), would[0])
        self.assertTrue(would[1].endswith(os.path.join(slugs[3], 'photos', 'd01-02.th.webp') + ' (569 x 320)'), would[1])
        self.assertEqual([s for s in self.said if s.startswith('wrote')], [])
        self.assertEqual(len([s for s in self.said if s.startswith('skipped ')]), 1)
        self.assertEqual(len(self.said), 3)

    def test_force_rewrites_the_copies_that_exist(self):
        auto, done = self.auto(), self.done()
        self.assertEqual(self.run_thumbs([auto, done], force=True), (2, 0, 0))
        self.assertEqual(self.copied(), [os.path.join(auto, 'photos', '02.th.webp'), os.path.join(done, 'photos', '01.th.webp')])
        with open(self.path(done, 'photos', '01.th.webp'), 'rb') as fh:
            self.assertEqual(fh.read(), PLACEHOLDER)
        del self.copies[:]
        self.assertEqual(self.run_thumbs([auto, done], force=True), (2, 0, 0))    # and again: force never counts one as existing
        self.assertEqual(len(self.copies), 2)

    def test_force_with_dry_run_still_writes_nothing(self):
        auto, done = self.auto(), self.done()
        before = tree(self.tmp)
        self.assertEqual(self.run_thumbs([auto, done], force=True, dry_run=True), (2, 0, 0))
        self.assertEqual(self.copies, [])
        self.assertEqual(tree(self.tmp), before)
        self.assertEqual([s.split(' ')[0] for s in self.said], ['would', 'would'])

    def test_all_photos_writes_a_copy_for_every_photo_with_a_recorded_size(self):
        auto, tour = self.auto(), self.tour()
        self.assertEqual(self.run_thumbs([auto, tour], all_photos=True), (5, 0, 0))
        self.assertEqual(self.copied(), [os.path.join(auto, 'photos', n) for n in ('01.th.webp', '02.th.webp', '03.th.webp')]
                         + [os.path.join(tour, 'photos', n) for n in ('d01-01.th.webp', 'd01-02.th.webp')])
        self.assertEqual([(w, h) for _s, _d, w, h in self.copies], [PORTRAIT, LANDSCAPE, (1600, 900), PORTRAIT, (1600, 900)])
        self.assertFalse(os.path.exists(self.path(tour, 'photos', 'd02-01.th.webp')))     # no recorded size: no copy

    def test_all_photos_counts_the_covers_copy_as_existing_after_a_cover_run(self):
        auto = self.auto()
        self.assertEqual(self.run_thumbs([auto]), (1, 0, 0))
        self.assertEqual(self.run_thumbs([auto], all_photos=True), (2, 1, 0))

    def test_a_run_adds_the_th_files_and_touches_nothing_else(self):
        slugs = [self.auto(), self.done(), self.gone(), self.tour(), self.make('bare', track=True, body='Synthetic write-up.')]
        before = tree(self.tmp)
        self.assertEqual(self.run_thumbs(slugs, all_photos=True), (5, 1, 1))
        after = tree(self.tmp)
        added = sorted(set(after) - set(before))
        self.assertEqual(added, sorted(self.copied()))
        self.assertEqual(len(added), 5)
        for path in added:
            self.assertRegex(path, r'^%s[a-z]+%sphotos%s[a-z0-9-]+\.th\.webp$' % (PREFIX, os.sep, os.sep))
        self.assertEqual(sorted(set(before) - set(after)), [])          # nothing was removed
        for path, data in before.items():
            self.assertEqual(after[path], data, '%s changed' % path)   # every index.md, day file, photo and GPX, byte for byte
        for slug in slugs:
            self.assertIn(os.path.join(slug, 'index.md'), before)

    def test_say_defaults_to_print(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(thumbs.run([self.load(self.auto())]), (1, 0, 0))
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith('wrote '), lines)


class MainTests(ThumbsFixture):

    def test_a_clean_run_writes_every_missing_cover_and_prints_the_summary(self):
        auto, done, tour = self.auto(), self.done(), self.tour()
        self.make('bare', track=True)
        code, out, err = self.main()
        self.assertEqual(code, 0)
        self.assertEqual(err, [])
        self.assertEqual(sorted(self.copied()), sorted([os.path.join(auto, 'photos', '02.th.webp'), os.path.join(tour, 'photos', 'd01-02.th.webp')]))
        self.assertEqual(out[-1], 'wrote 2 card-size copies; 1 already there')
        self.assertEqual(len(out), 3)
        self.assertTrue(all(line.startswith('wrote ') for line in out[:-1]), out)
        self.assertTrue(os.path.exists(self.path(done, 'photos', '01.th.webp')))

    def test_one_copy_is_a_copy(self):
        self.auto()
        code, out, err = self.main()
        self.assertEqual((code, err), (0, []))
        self.assertEqual(out[-1], 'wrote 1 card-size copy; 0 already there')
        code, out, err = self.main()
        self.assertEqual((code, err), (0, []))
        self.assertEqual(out, ['wrote 0 card-size copies; 1 already there'])

    def test_the_summary_counts_a_missing_photo(self):
        self.auto()
        self.gone()
        code, out, err = self.main()
        self.assertEqual((code, err), (0, []))
        self.assertEqual(out[-1], 'wrote 1 card-size copy; 0 already there; 1 skipped (photo missing or unreadable)')
        self.assertEqual(len([line for line in out if line.startswith('skipped ')]), 1)

    def test_slugs_limit_the_run_to_those_trips(self):
        auto, tour = self.auto(), self.tour()
        code, out, err = self.main(tour)
        self.assertEqual((code, err), (0, []))
        self.assertEqual(self.copied(), [os.path.join(tour, 'photos', 'd01-02.th.webp')])
        self.assertEqual(out[-1], 'wrote 1 card-size copy; 0 already there')
        self.assertFalse(os.path.exists(self.path(auto, 'photos', '02.th.webp')))
        code, out, err = self.main(auto, tour)
        self.assertEqual((code, err), (0, []))
        self.assertEqual(out[-1], 'wrote 1 card-size copy; 1 already there')

    def test_an_unknown_slug_stops_with_exit_1_and_names_it(self):
        auto = self.auto()
        before = tree(self.tmp)
        code, out, err = self.main(PREFIX + 'nope')
        self.assertEqual(code, 1)
        self.assertEqual(out, [])
        self.assertEqual(len(err), 1)
        self.assertTrue(err[0].startswith('ERROR '), err)
        self.assertIn(PREFIX + 'nope', err[0])
        # a known slug beside it does not get its copy either: nothing is written before the names are checked
        code, out, err = self.main(auto, PREFIX + 'nope', PREFIX + 'neither')
        self.assertEqual((code, out), (1, []))
        self.assertEqual(len(err), 1)
        self.assertIn(PREFIX + 'nope', err[0])
        self.assertIn(PREFIX + 'neither', err[0])
        self.assertNotIn(auto, err[0])
        self.assertEqual(self.copies, [])
        self.assertEqual(tree(self.tmp), before)

    def test_a_content_error_stops_with_exit_1_and_one_error_line(self):
        self.auto()
        bad = self.make('bad', photos=[photo('photos/01.webp', LANDSCAPE)], cover_photo='photos/09.webp')
        before = tree(self.tmp)
        for argv in ((), ('--dry-run',), (PREFIX + 'auto',)):
            with self.subTest(argv=argv):
                code, out, err = self.main(*argv)
                self.assertEqual(code, 1)
                self.assertEqual(out, [])
                self.assertEqual(len(err), 1, err)
                self.assertTrue(err[0].startswith('ERROR content/trips/%s/index.md: cover_photo ' % bad), err[0])
                self.assertIn('photos/09.webp', err[0])
                self.assertNotIn('Traceback', ''.join(err))
        self.assertEqual(self.copies, [])
        self.assertEqual(tree(self.tmp), before)

    def test_without_cwebp_a_run_stops_with_exit_1_before_writing(self):
        auto = self.auto()
        before = tree(self.tmp)
        with mock.patch.object(photolib, 'have_cwebp', return_value=False):
            code, out, err = self.main()
            self.assertEqual(code, 1)
            self.assertEqual(out, [])
            self.assertEqual(len(err), 1)
            self.assertTrue(err[0].startswith('ERROR '), err)
            self.assertIn('cwebp', err[0])
            code, _out, err = self.main(auto, '--force')
            self.assertEqual(code, 1)
            self.assertIn('cwebp', err[0])
        self.assertEqual(self.copies, [])
        self.assertEqual(tree(self.tmp), before)

    def test_without_cwebp_a_dry_run_still_reports(self):
        auto = self.auto()
        self.done()
        before = tree(self.tmp)
        with mock.patch.object(photolib, 'have_cwebp', return_value=False):
            code, out, err = self.main('--dry-run')
        self.assertEqual((code, err), (0, []))
        self.assertEqual(len(out), 2)
        self.assertTrue(out[0].startswith('would write '), out)
        self.assertTrue(out[0].endswith(os.path.join(auto, 'photos', '02.th.webp') + ' (427 x 320)'), out)
        self.assertEqual(out[1], 'would write 1 card-size copy; 1 already there')
        self.assertEqual(self.copies, [])
        self.assertEqual(tree(self.tmp), before)

    def test_dry_run_with_cwebp_writes_nothing_either(self):
        self.auto()
        self.tour()
        before = tree(self.tmp)
        code, out, err = self.main('--dry-run')
        self.assertEqual((code, err), (0, []))
        self.assertEqual(out[-1], 'would write 2 card-size copies; 0 already there')
        self.assertEqual(self.copies, [])
        self.assertEqual(tree(self.tmp), before)

    def test_all_photos_and_force_are_passed_on(self):
        auto, done = self.auto(), self.done()
        code, out, err = self.main('--all-photos')
        self.assertEqual((code, err), (0, []))
        self.assertEqual(out[-1], 'wrote 3 card-size copies; 1 already there')
        self.assertEqual(sorted(self.copied()), [os.path.join(auto, 'photos', n) for n in ('01.th.webp', '02.th.webp', '03.th.webp')])
        del self.copies[:]
        code, out, err = self.main('--force', done)
        self.assertEqual((code, err), (0, []))
        self.assertEqual(out[-1], 'wrote 1 card-size copy; 0 already there')
        self.assertEqual(self.copied(), [os.path.join(done, 'photos', '01.th.webp')])

    def test_drafts_get_their_copies_too(self):
        # a draft becomes a page the day its draft line goes, with nothing else to remember
        slug = self.make('draft', draft=True, photos=[photo('photos/01.webp', SQUARE)])
        self.assertEqual(helpers.load_dir(self.tmp), [])
        code, out, err = self.main()
        self.assertEqual((code, err), (0, []))
        self.assertEqual(self.copied(), [os.path.join(slug, 'photos', '01.th.webp')])
        self.assertEqual([(w, h) for _s, _d, w, h in self.copies], [SQUARE])
        self.assertEqual(out[-1], 'wrote 1 card-size copy; 0 already there')

    def test_a_folder_of_no_trips_is_a_clean_run(self):
        code, out, err = self.main()
        self.assertEqual((code, err), (0, []))
        self.assertEqual(out, ['wrote 0 card-size copies; 0 already there'])

    def test_main_adds_the_th_files_and_touches_nothing_else(self):
        slugs = [self.auto(), self.done(), self.gone(), self.tour()]
        before = tree(self.tmp)
        code, _out, err = self.main('--all-photos')
        self.assertEqual((code, err), (0, []))
        after = tree(self.tmp)
        self.assertEqual(sorted(set(after) - set(before)), sorted(self.copied()))
        self.assertEqual(len(self.copies), 5)
        for path, data in before.items():
            self.assertEqual(after.get(path), data, '%s changed' % path)
        for slug in slugs:
            with open(self.path(slug, 'index.md'), 'rb') as fh:
                self.assertEqual(fh.read(), before[os.path.join(slug, 'index.md')])


class OutsidePathTests(ThumbsFixture):
    """content.load_all does not refuse a photo entry that points outside the trip's photos/ folder (the validator
    does), so thumbs.py must: a copy is only ever written beside a file directly in photos/."""

    def test_in_photos(self):
        for file in ('photos/01.webp', 'photos/d01-02.webp', 'photos/a b.webp'):
            self.assertTrue(thumbs.in_photos(file), file)
        for file in ('../other/photos/01.webp', '/tmp/photos/01.webp', 'photos/../01.webp', 'photos/sub/01.webp', 'photos/',
                     'photos/..', 'photos/.', '01.webp', 'Photos/01.webp', 'photos\\01.webp', 'photos/a\\..\\b.webp', '', None, 5):
            self.assertFalse(thumbs.in_photos(file), file)

    def entry_outside(self, file):
        """A trip whose cover entry names `file`; the file itself exists, outside the trip folder where the path says."""
        slug = self.make('escape', date='2026-06-02', track=True, photos=[photo('photos/01.webp', LANDSCAPE)])
        target = os.path.normpath(os.path.join(self.path(slug), file))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as fh:
            fh.write(PLACEHOLDER)
        t = self.load(slug)
        t['photos'][0]['file'] = file            # what content.load_trip hands over for such an entry
        t['cover'] = {'photo': t['photos'][0], 'focal': (50.0, 50.0), 'source': 'auto'}
        return t, target

    def test_a_photo_outside_the_trips_photos_folder_gets_no_copy(self):
        outside = PREFIX + 'outside'
        for file in ('../%s/photos/secret.webp' % outside, 'photos/../../%s/photos/secret.webp' % outside,
                     os.path.join(self.tmp, outside, 'photos', 'secret.webp')):
            with self.subTest(file=file):
                del self.copies[:], self.said[:]
                t, target = self.entry_outside(file)
                self.assertEqual(thumbs.wanted(t), [])
                self.assertEqual(thumbs.wanted(t, all_photos=True), [])
                self.assertEqual(thumbs.run([t], say=self.said.append), (0, 0, 0))
                self.assertEqual(self.copies, [])
                self.assertFalse(os.path.exists(os.path.splitext(target)[0] + '.th.webp'))


class UnreadablePhotoTests(ThumbsFixture):
    """A photo the converter cannot read (a file an interrupted sync left truncated) is skipped and counted; the run goes
    on to the next photo and the next trip."""

    def test_a_photo_that_cannot_be_converted_is_skipped_and_the_run_goes_on(self):
        import subprocess
        bad = self.make('bad', date='2026-06-03', track=True, photos=[photo('photos/01.webp', LANDSCAPE)])
        good = self.make('good', date='2026-06-04', track=True, photos=[photo('photos/01.webp', LANDSCAPE)])
        for error in (subprocess.CalledProcessError(1, ['cwebp']), OSError('gone'), ValueError('bad size')):
            with self.subTest(error=type(error).__name__):
                del self.copies[:], self.said[:]
                for slug in (bad, good):
                    if os.path.exists(self.path(slug, 'photos', '01.th.webp')):
                        os.remove(self.path(slug, 'photos', '01.th.webp'))

                def copy(src, dst, w, h, quality=72):
                    if os.sep + bad + os.sep in src:
                        raise error
                    return self.fake_copy(src, dst, w, h, quality)

                with mock.patch.object(photolib, 'thumb_copy', side_effect=copy):
                    self.assertEqual(self.run_thumbs([bad, good]), (1, 0, 1))
                self.assertEqual(self.copied(), [os.path.join(good, 'photos', '01.th.webp')])
                self.assertFalse(os.path.exists(self.path(bad, 'photos', '01.th.webp')))
                skipped = [s for s in self.said if s.startswith('skipped ')]
                self.assertEqual(len(skipped), 1)
                self.assertTrue(skipped[0].endswith(os.path.join(bad, 'photos', '01.th.webp') + ': the photo could not be converted'), skipped[0])

    def test_another_kind_of_failure_is_not_swallowed(self):
        slug = self.make('boom', date='2026-06-05', track=True, photos=[photo('photos/01.webp', LANDSCAPE)])
        with mock.patch.object(photolib, 'thumb_copy', side_effect=KeyError('boom')):
            with self.assertRaises(KeyError):
                self.run_thumbs([slug])

    def test_the_summary_counts_it(self):
        import subprocess
        self.make('bad', date='2026-06-03', track=True, photos=[photo('photos/01.webp', LANDSCAPE)])
        with mock.patch.object(photolib, 'thumb_copy', side_effect=subprocess.CalledProcessError(1, ['cwebp'])):
            code, out, err = self.main()
        self.assertEqual((code, err), (0, []))
        self.assertEqual(out[-1], 'wrote 0 card-size copies; 0 already there; 1 skipped (photo missing or unreadable)')


# ---------------------------------------------------------------- photos.thumb_copy: the command it runs (contract 10.3)

class ThumbCopyCommandTests(unittest.TestCase):
    """contract-phase4.md 10.3: thumb_copy keeps the ICC colour profile (`-metadata icc`), like the other two copies, and
    no other metadata. Neither cwebp nor sips is run: subprocess.run is replaced by a recorder that writes an empty
    file where the tool would have written its output."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.calls = []           # (argument list, keyword arguments) of every command
        self.src = os.path.join(self.tmp, 'photos', '01.webp')
        helpers.touch(self.src)
        for patcher in (mock.patch.object(photolib.subprocess, 'run', side_effect=self.fake_run),
                        mock.patch.object(photolib, 'have_cwebp', return_value=True)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def fake_run(self, args, **kw):
        self.calls.append((list(args), kw))
        out = args[args.index('-o') + 1] if '-o' in args else args[args.index('--out') + 1]
        helpers.touch(out)

    def test_the_webp_copy_keeps_the_colour_profile(self):
        dst = os.path.join(self.tmp, 'photos', '01.th.webp')
        self.assertEqual(photolib.thumb_copy(self.src, dst, 1600, 1200), (427, 320))
        self.assertEqual(len(self.calls), 1)
        args, kw = self.calls[0]
        self.assertEqual(args[:-1], ['cwebp', '-quiet', '-q', '72', '-m', '5', '-metadata', 'icc', '-resize', '427', '320', self.src, '-o'])
        self.assertEqual(args.count('-metadata'), 1)
        self.assertEqual(args[args.index('-metadata') + 1], 'icc')
        self.assertLess(args.index('-metadata'), args.index(self.src))          # an option, before the input file
        for value in ('all', 'none', 'exif', 'xmp'):
            self.assertNotIn(value, args)
        self.assertIs(kw.get('check'), True)
        self.assertTrue(os.path.isfile(dst))                                    # the tool's output was moved into place
        self.assertNotEqual(args[-1], dst)                                      # ... from a temporary file, never written in place

    def test_the_size_and_the_quality_are_the_ones_asked_for(self):
        dst = os.path.join(self.tmp, 'photos', '01.th.webp')
        self.assertEqual(photolib.thumb_copy(self.src, dst, 1200, 1600, quality=60), (320, 427))
        args = self.calls[0][0]
        self.assertEqual(args[args.index('-q') + 1], '60')
        self.assertEqual(args[args.index('-resize') + 1:args.index('-resize') + 3], ['320', '427'])
        self.assertEqual(args[args.index('-metadata') + 1], 'icc')

    def test_every_webp_copy_of_a_photo_keeps_the_profile_alike(self):
        # web_copies writes the full file, the 800 px copy and (through thumb_copy) the card-size copy: the same
        # metadata rule on all three. Its JPEG intermediate (sips) is replaced as well
        with mock.patch.object(photolib, 'web_copy', return_value=(1600, 1200)):
            self.assertEqual(photolib.web_copies(self.src, os.path.join(self.tmp, 'out', '01')), ('webp', 1600, 1200))
        self.assertEqual(len(self.calls), 3)
        outputs = [os.path.basename(args[-1]) for args, _kw in self.calls[:2]]
        self.assertEqual(outputs, ['01.webp', '01.sm.webp'])
        for args, kw in self.calls:
            self.assertEqual(args[0], 'cwebp')
            self.assertEqual([args[i + 1] for i, a in enumerate(args) if a == '-metadata'], ['icc'])
            self.assertIs(kw.get('check'), True)
        self.assertIn('-resize', self.calls[2][0])
        self.assertEqual(self.calls[2][0][self.calls[2][0].index('-resize') + 1:][:2], ['427', '320'])
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, 'out', '01.th.webp')))

    def test_without_cwebp_a_webp_copy_is_refused_before_any_command(self):
        with mock.patch.object(photolib, 'have_cwebp', return_value=False):
            with self.assertRaises(RuntimeError) as cm:
                photolib.thumb_copy(self.src, os.path.join(self.tmp, 'photos', '01.th.webp'), 1600, 1200)
        self.assertIn('cwebp is not installed', str(cm.exception))
        self.assertEqual(self.calls, [])

    def test_the_jpeg_copy_is_stripped_of_everything_but_the_profile(self):
        # the fallback format goes through sips and then photos.strip_metadata, which keeps the JFIF header and the ICC
        # profile only
        dst = os.path.join(self.tmp, 'photos', '01.th.jpg')
        with mock.patch.object(photolib, 'strip_metadata') as strip:
            self.assertEqual(photolib.thumb_copy(self.src, dst, 1600, 1200), (427, 320))
        self.assertEqual([args[0] for args, _kw in self.calls], ['sips'])
        args = self.calls[0][0]
        self.assertEqual(args[args.index('-z') + 1:args.index('-z') + 3], ['320', '427'])          # sips takes height, then width
        self.assertEqual(strip.call_count, 1)
        self.assertEqual(strip.call_args[0][0], args[args.index('--out') + 1])
        self.assertTrue(os.path.isfile(dst))


if __name__ == '__main__':
    unittest.main()
