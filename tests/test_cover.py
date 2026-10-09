"""Phase 1: cover resolution and the optional presentation fields in the trip dict (tools/lib/content.py)."""
import os
import sys
import tempfile
import unittest
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402

import helpers  # noqa: E402
from helpers import LANDSCAPE, PORTRAIT, SQUARE, photo  # noqa: E402

COVER_KEYS = {'photo', 'source', 'day', 'focal'}


class CoverTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def trip(self, slug='trip', **kw):
        helpers.make_trip(self.tmp, slug, **kw)
        return helpers.load(self.tmp, slug)

    def assertLoadRaises(self, slug, *needles, **kw):
        """load_trip raises ValueError prefixed 'content/trips/<slug>/index.md: ' and naming every needle."""
        helpers.make_trip(self.tmp, slug, **kw)
        with self.assertRaises(ValueError) as cm:
            helpers.load(self.tmp, slug)
        msg = str(cm.exception)
        self.assertTrue(msg.startswith('content/trips/%s/index.md: ' % slug), 'unexpected prefix: %r' % msg)
        for needle in needles:
            self.assertIn(needle, msg)
        return msg

    # ------------------------------------------------------------ explicit selection

    def test_explicit_parent_photo_resolves_with_declared_metadata(self):
        photos = [photo('photos/01.webp', LANDSCAPE, alt='First, landscape'),
                  photo('photos/02.webp', PORTRAIT, alt='A skier on the ridge', sm=True)]
        t = self.trip(photos=photos, cover_photo='photos/02.webp')
        self.assertEqual(t['cover_photo'], 'photos/02.webp')
        c = t['cover']
        self.assertEqual(set(c), COVER_KEYS)
        self.assertEqual(c['source'], 'explicit')
        self.assertIsNone(c['day'])
        self.assertEqual(c['focal'], (50.0, 50.0))
        self.assertEqual(c['photo'], t['photos'][1])
        p = c['photo']
        self.assertEqual((p['file'], p['w'], p['h'], p['alt'], p['sm']),
                         ('photos/02.webp', 1200, 1600, 'A skier on the ridge', 'photos/02.sm.webp'))

    def test_explicit_day_photo_resolves_with_its_day(self):
        days = [{'title': 'Approach', 'photos': [photo('photos/d01-01.webp', LANDSCAPE)]},
                {'title': 'Hut day', 'photos': [photo('photos/d02-01.webp', PORTRAIT, alt='The hut at dusk')]}]
        t = self.trip(kind='multi-day', date='2024-01-16', end_date='2024-01-17', days=days, cover_photo='photos/d02-01.webp')
        c = t['cover']
        self.assertEqual(c['source'], 'explicit')
        self.assertEqual(c['photo'], t['days'][1]['photos'][0])
        self.assertEqual(c['photo']['alt'], 'The hut at dusk')
        self.assertEqual(c['day'], t['days'][1])
        self.assertEqual(c['day']['n'], 2)

    def test_explicit_cover_carries_focal_point_and_matches_resolve_cover(self):
        t = self.trip(photos=[photo('photos/01.webp', PORTRAIT), photo('photos/02.webp', LANDSCAPE)],
                      cover_photo='photos/01.webp', cover_focal_x=30, cover_focal_y=60)
        self.assertEqual(t['cover']['focal'], (30.0, 60.0))
        self.assertEqual(t['cover']['photo']['file'], 'photos/01.webp')
        self.assertEqual(content.resolve_cover(t), t['cover'])

    def test_dot_slash_and_repeated_slashes_normalise_to_the_declared_file(self):
        for i, value in enumerate(('./photos/01.webp', 'photos//01.webp', 'photos/./01.webp')):
            with self.subTest(cover_photo=value):
                t = self.trip(slug='norm-%d' % i, photos=[photo('photos/01.webp', PORTRAIT), photo('photos/02.webp', LANDSCAPE)],
                              cover_photo=value)
                self.assertEqual(t['cover']['source'], 'explicit')
                self.assertEqual(t['cover']['photo']['file'], 'photos/01.webp')

    # ------------------------------------------------------------ automatic fallback

    def test_automatic_prefers_landscape_parent_photo_over_earlier_portrait(self):
        t = self.trip(photos=[photo('photos/01.webp', PORTRAIT), photo('photos/02.webp', LANDSCAPE), photo('photos/03.webp', LANDSCAPE)])
        self.assertIsNone(t['cover_photo'])
        c = t['cover']
        self.assertEqual((c['source'], c['photo']['file'], c['day']), ('parent', 'photos/02.webp', None))
        self.assertEqual(c['photo'], t['photos'][1])
        self.assertEqual(c['focal'], (50.0, 50.0))

    def test_automatic_square_photo_counts_as_landscape(self):
        t = self.trip(photos=[photo('photos/01.webp', PORTRAIT), photo('photos/02.webp', SQUARE)])
        self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), ('parent', 'photos/02.webp'))

    def test_automatic_takes_first_parent_photo_when_none_is_landscape(self):
        t = self.trip(photos=[photo('photos/01.webp', PORTRAIT), photo('photos/02.webp', PORTRAIT)])
        self.assertEqual((t['cover']['source'], t['cover']['photo']['file'], t['cover']['day']), ('parent', 'photos/01.webp', None))

    def test_automatic_parent_photo_beats_landscape_day_photo(self):
        days = [{'photos': [photo('photos/d01-01.webp', LANDSCAPE)]}]
        t = self.trip(kind='multi-day', days=days, photos=[photo('photos/01.webp', PORTRAIT)])
        self.assertEqual((t['cover']['source'], t['cover']['photo']['file'], t['cover']['day']), ('parent', 'photos/01.webp', None))

    def test_automatic_falls_back_to_landscape_day_photo_when_trip_has_no_photos(self):
        days = [{'photos': [photo('photos/d01-01.webp', PORTRAIT)]},
                {'photos': [photo('photos/d02-01.webp', PORTRAIT), photo('photos/d02-02.webp', LANDSCAPE)]},
                {'photos': [photo('photos/d03-01.webp', LANDSCAPE)]}]
        t = self.trip(kind='multi-day', days=days)
        self.assertEqual(t['photos'], [])
        c = t['cover']
        self.assertEqual((c['source'], c['photo']['file']), ('day', 'photos/d02-02.webp'))
        self.assertEqual(c['day'], t['days'][1])
        self.assertEqual(c['photo'], t['days'][1]['photos'][1])

    def test_automatic_day_fallback_takes_first_photo_of_first_day_with_photos_when_none_is_landscape(self):
        days = [{}, {'photos': [photo('photos/d02-01.webp', PORTRAIT), photo('photos/d02-02.webp', PORTRAIT)]},
                {'photos': [photo('photos/d03-01.webp', PORTRAIT)]}]
        t = self.trip(kind='multi-day', days=days)
        c = t['cover']
        self.assertEqual((c['source'], c['photo']['file']), ('day', 'photos/d02-01.webp'))
        self.assertEqual(c['day'], t['days'][1])

    def test_no_photos_anywhere_gives_none(self):
        self.assertIsNone(self.trip(slug='single', track=True, body='Text.')['cover'])
        self.assertIsNone(self.trip(slug='multi', kind='multi-day', days=[{}, {'body': 'Prose.'}])['cover'])
        self.assertIsNone(self.trip(slug='bare')['cover'])

    def test_automatic_fallback_never_raises_for_missing_files(self):
        # a declared photo that is not on disk is the existing situation on some trips: automatic resolution must not raise
        t = self.trip(photos=[photo('photos/01.webp', LANDSCAPE)], missing=('photos/01.webp',))
        self.assertEqual(t['cover']['photo']['file'], 'photos/01.webp')

    # ------------------------------------------------------------ explicit errors

    def test_explicit_undeclared_path_raises_naming_path_and_index(self):
        folder = helpers.make_trip(self.tmp, 'undeclared', photos=[photo('photos/01.webp', LANDSCAPE)], cover_photo='photos/09.webp')
        helpers.touch(os.path.join(folder, 'photos', '09.webp'))      # exists on disk but is not declared under photos:
        with self.assertRaises(ValueError) as cm:
            helpers.load(self.tmp, 'undeclared')
        msg = str(cm.exception)
        self.assertTrue(msg.startswith('content/trips/undeclared/index.md: '), msg)
        self.assertIn('photos/09.webp', msg)
        self.assertIn('cover_photo', msg)

    def test_explicit_declared_but_missing_on_disk_raises(self):
        self.assertLoadRaises('gone', 'photos/02.webp', 'cover_photo',
                              photos=[photo('photos/01.webp', LANDSCAPE), photo('photos/02.webp', LANDSCAPE)],
                              missing=('photos/02.webp',), cover_photo='photos/02.webp')

    def test_explicit_path_traversal_raises(self):
        abs_path = os.path.join(self.tmp, 'abs', 'photos', '01.webp')
        cases = [('dotdot', '../x/photos/01.webp'), ('abs', abs_path), ('backslash', 'photos\\01.webp'),
                 ('inner-dotdot', 'photos/../photos/01.webp'), ('root-slash', '/photos/01.webp')]
        for slug, value in cases:
            with self.subTest(cover_photo=value):
                msg = self.assertLoadRaises(slug, 'cover_photo', photos=[photo('photos/01.webp', LANDSCAPE)], cover_photo=value)
                # the message names the offending path, raw or repr()-quoted (repr doubles a backslash)
                self.assertTrue(value in msg or repr(value) in msg, 'path %r not named in %r' % (value, msg))

    def test_cover_photo_not_a_string_or_empty_raises(self):
        for i, bad in enumerate(('', 5, True, ['photos/01.webp'])):
            with self.subTest(cover_photo=bad):
                self.assertLoadRaises('bad-%d' % i, 'cover_photo', photos=[photo('photos/01.webp', LANDSCAPE)], cover_photo=bad)

    # ------------------------------------------------------------ dimensions

    def test_photo_without_dimensions_is_explicit_ok_but_not_preferred_automatically(self):
        nodim = photo('photos/01.webp', None, alt='No size recorded')
        land = photo('photos/02.webp', LANDSCAPE)
        auto = self.trip(slug='auto', photos=[nodim, land])
        self.assertEqual((auto['cover']['source'], auto['cover']['photo']['file']), ('parent', 'photos/02.webp'))
        explicit = self.trip(slug='explicit', photos=[nodim, land], cover_photo='photos/01.webp')
        c = explicit['cover']
        self.assertEqual((c['source'], c['photo']['file'], c['photo']['w'], c['photo']['h']), ('explicit', 'photos/01.webp', None, None))
        self.assertEqual(c['photo']['alt'], 'No size recorded')

    def test_photo_without_dimensions_is_still_the_last_resort(self):
        only = self.trip(slug='only', photos=[photo('photos/01.webp', None)])
        self.assertEqual((only['cover']['source'], only['cover']['photo']['file']), ('parent', 'photos/01.webp'))
        days = [{'photos': [photo('photos/d01-01.webp', None)]}, {'photos': [photo('photos/d02-01.webp', LANDSCAPE)]}]
        t = self.trip(slug='days', kind='multi-day', days=days)
        self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), ('day', 'photos/d02-01.webp'))
        self.assertEqual(t['cover']['day'], t['days'][1])

    def test_half_known_dimensions_do_not_count_as_landscape(self):
        half = {'file': 'photos/01.webp', 'w': 1600, 'alt': 'Width only'}
        t = self.trip(photos=[half, photo('photos/02.webp', LANDSCAPE)])
        self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), ('parent', 'photos/02.webp'))

    # ------------------------------------------------------------ focal point

    def test_cover_focal_defaults_to_centre(self):
        t = self.trip(photos=[photo('photos/01.webp', LANDSCAPE)])
        self.assertEqual(t['cover_focal'], (50.0, 50.0))
        self.assertTrue(all(isinstance(v, float) for v in t['cover_focal']))
        self.assertEqual(t['cover']['focal'], (50.0, 50.0))

    def test_cover_focal_valid_values_are_kept_as_floats(self):
        cases = [({'cover_focal_x': 0, 'cover_focal_y': 0}, (0.0, 0.0)),
                 ({'cover_focal_x': 100, 'cover_focal_y': 100}, (100.0, 100.0)),
                 ({'cover_focal_x': 45.5, 'cover_focal_y': 12}, (45.5, 12.0)),
                 ({'cover_focal_x': 30}, (30.0, 50.0)),
                 ({'cover_focal_y': 70}, (50.0, 70.0))]
        for i, (fields, expected) in enumerate(cases):
            with self.subTest(**fields):
                t = self.trip(slug='focal-%d' % i, photos=[photo('photos/01.webp', LANDSCAPE)], **fields)
                self.assertEqual(t['cover_focal'], expected)
                self.assertIsInstance(t['cover_focal'], tuple)
                self.assertTrue(all(isinstance(v, float) for v in t['cover_focal']), t['cover_focal'])
                self.assertEqual(t['cover']['focal'], expected)

    def test_cover_focal_invalid_values_raise_naming_field(self):
        i = 0
        for field in ('cover_focal_x', 'cover_focal_y'):
            for bad in (-1, 101, 'abc', '50%', True, 100.5, -0.5):
                with self.subTest(field=field, value=bad):
                    i += 1
                    self.assertLoadRaises('focal-bad-%d' % i, field, photos=[photo('photos/01.webp', LANDSCAPE)], **{field: bad})

    # ------------------------------------------------------------ card_summary and backward compatibility

    def test_card_summary_is_stripped_and_empty_means_none(self):
        t = self.trip(slug='padded', card_summary='  A short, factual summary.  ', body='Prose.')
        self.assertEqual(t['card_summary'], 'A short, factual summary.')
        self.assertIsNone(self.trip(slug='empty', card_summary='')['card_summary'])
        self.assertIsNone(self.trip(slug='absent')['card_summary'])

    def test_card_summary_not_a_string_raises(self):
        for i, bad in enumerate((5, True, ['a', 'b'])):
            with self.subTest(card_summary=bad):
                self.assertLoadRaises('summary-bad-%d' % i, 'card_summary', card_summary=bad)

    def test_trip_without_new_fields_loads_as_before(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            t = self.trip(slug='plain', activity='ski', date='2026-01-17', body='Skinned up before dawn.', track=True,
                          photos=[photo('photos/01.webp', LANDSCAPE, alt='Ridge')])
            bare = self.trip(slug='bare')
            multi = self.trip(slug='multi', kind='multi-day', days=[{'body': 'Day one.'}, {}])
        self.assertEqual([str(w.message) for w in caught if issubclass(w.category, UserWarning)], [])
        for x in (t, bare, multi):
            self.assertIsNone(x['cover_photo'])
            self.assertIsNone(x['card_summary'])
            self.assertEqual(x['cover_focal'], (50.0, 50.0))
        # the pre-existing shape is intact
        self.assertEqual(t['title'], 'Plain')
        self.assertEqual(t['photos'][0]['file'], 'photos/01.webp')
        self.assertEqual(t['body_md'], 'Skinned up before dawn.')
        self.assertTrue(t['track'])
        self.assertEqual(t['cover']['source'], 'parent')
        self.assertIsNone(bare['cover'])
        self.assertEqual(len(multi['days']), 2)


if __name__ == '__main__':
    unittest.main()
