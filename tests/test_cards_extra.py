"""Phase 1 review additions: the day label on multi-day home cards, no-photo and recent-card media, the cover image /
preload helpers, home.page()'s share image, facts wording edges, a missing day-photo file, hand-written front matter
and front-matter syntax errors naming their file."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
from sitegen import core  # noqa: E402
from sitegen.pages import home  # noqa: E402

import helpers  # noqa: E402
from helpers import photo, LANDSCAPE, PORTRAIT  # noqa: E402

DAY_PROSE = 'Crossed the pass in soft afternoon snow and dropped to the hut by five.'
WRITEUP = 'Skinned up before dawn and skied the couloir on firm snow.'


class CardMediaTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        helpers.make_trip(self.tmp, 'hut-route', title='Hut Route', activity='hike', kind='multi-day', date='2024-01-16', end_date='2024-01-17',
                          days=[{'title': 'Approach'}, {'title': 'Forester Pass', 'body': DAY_PROSE}])
        helpers.make_trip(self.tmp, 'ski-report', title='West Couloir', activity='ski', date='2026-01-17', place='Sawtooth Ridge',
                          body=WRITEUP, track=True, cover_focal_x=45, cover_focal_y=55,
                          photos=[photo('photos/01.webp', LANDSCAPE, alt='The couloir', sm=True)])
        helpers.make_trip(self.tmp, 'track-only', title='Quick Lap', activity='ski', date='2025-12-01', track=True)
        helpers.make_trip(self.tmp, 'no-dims', title='No Dims', activity='mtb', date='2025-11-01', track=True,
                          photos=[photo('photos/01.webp', None, alt='Trail')])
        self.trips = helpers.load_dir(self.tmp)
        self.site = helpers.make_site(self.trips)
        self.by = self.site['by_slug']

    def feat(self, slugs_):
        self.site['featured'] = [self.by[s] for s in slugs_]
        return home.featured(self.site)

    def test_multiday_card_keeps_the_day_label_above_its_excerpt(self):
        html_ = self.feat(['hut-route'])
        self.assertIn('<p class="t-label hom-card-exl">DAY 2 · FORESTER PASS</p>', html_)
        self.assertIn(DAY_PROSE, html_)
        self.assertLess(html_.index('hom-card-exl'), html_.index('hom-card-ex">'))

    def test_card_without_photo_or_tile_is_marked_nophoto(self):
        html_ = self.feat(['track-only'])
        self.assertIn('hom-card--nophoto', html_)
        self.assertNotIn('<img class="cover-img', html_)

    def test_card_with_photo_has_one_cover_image_and_is_not_nophoto(self):
        html_ = self.feat(['ski-report'])
        self.assertNotIn('hom-card--nophoto', html_)
        self.assertEqual(html_.count('<img class="cover-img'), 1)
        self.assertIn('alt="The couloir"', html_)

    def test_lead_card_cover_is_eager_and_supporting_covers_are_lazy(self):
        html_ = self.feat(['ski-report', 'no-dims'])
        lead, sub = html_.split('hom-card--sub', 1)
        self.assertIn('fetchpriority="high"', lead)
        self.assertNotIn('loading="lazy"', lead.split('</li>')[0])
        self.assertIn('loading="lazy"', sub)

    def test_action_links_name_their_trip_for_link_lists(self):
        html_ = self.feat(['ski-report', 'track-only'])
        self.assertIn('Read the report<span class="sr">: West Couloir</span>', html_)
        self.assertIn('View trip<span class="sr">: Quick Lap</span>', html_)

    def test_recent_cards_show_the_cover_and_describe_titles_by_their_meta_line(self):
        self.site['featured'] = []
        html_ = home.recent(self.site)
        self.assertIn('<img class="cover-img', html_)
        self.assertIn('id="rc-ski-report-m"', html_)
        self.assertIn('aria-describedby="rc-ski-report-m"', html_)

    def test_page_uses_the_lead_cover_as_share_image_and_preloads_it(self):
        self.site['featured'] = [self.by['ski-report']]
        html_ = home.page(self.site).html
        self.assertIn('<meta property="og:image" content="%strips/ski-report/photos/01.webp">' % core.SITE_URL, html_)
        self.assertIn('<link rel="preload" as="image" href="trips/ski-report/photos/01.webp" imagesrcset=', html_)
        self.assertIn('hom-card--lead', html_)

    def test_page_without_features_has_no_share_image(self):
        self.site['featured'] = []
        html_ = home.page(self.site).html
        self.assertNotIn('og:image', html_)
        self.assertNotIn('hom-featured', html_)


class CoverHelperTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def trip(self, slug, **meta):
        helpers.make_trip(self.tmp, slug, **meta)
        return helpers.load(self.tmp, slug)

    def test_cover_img_srcset_focal_and_loading(self):
        t = self.trip('focal', cover_focal_x=45, cover_focal_y=55, photos=[photo('photos/01.webp', LANDSCAPE, alt='A & B "c"', sm=True)])
        img = core.cover_img(t, '', '(min-width: 1200px) 718px, 100vw')
        self.assertTrue(img.startswith('<img class="cover-img"'))
        self.assertIn('src="trips/focal/photos/01.webp"', img)
        self.assertIn('srcset="trips/focal/photos/01.sm.webp 800w, trips/focal/photos/01.webp 1600w"', img)
        self.assertIn('sizes="(min-width: 1200px) 718px, 100vw"', img)
        self.assertIn('width="1600" height="1200"', img)
        self.assertIn('alt="A &amp; B &quot;c&quot;"', img)
        self.assertIn('loading="lazy"', img)
        self.assertNotIn('fetchpriority', img)
        self.assertIn('style="object-position:45% 55%"', img)
        eager = core.cover_img(t, 'ski/', '100vw', eager=True, cls='x')
        self.assertIn('class="cover-img x"', eager)
        self.assertIn('src="../trips/focal/photos/01.webp"', eager)
        self.assertIn('fetchpriority="high"', eager)
        self.assertNotIn('loading="lazy"', eager)

    def test_cover_img_centre_focal_has_no_style_and_no_dims_has_no_srcset(self):
        t = self.trip('plain', photos=[photo('photos/01.webp', None, alt='Trail')])
        img = core.cover_img(t, '', '100vw')
        self.assertNotIn('style=', img)
        self.assertNotIn('srcset', img)
        self.assertNotIn('width=', img)

    def test_cover_img_and_preload_are_empty_without_a_cover(self):
        t = self.trip('bare', track=True)
        self.assertEqual(core.cover_img(t, '', '100vw'), '')
        self.assertEqual(core.cover_preload(t, '', '100vw'), '')

    def test_cover_preload_matches_the_image_candidates(self):
        t = self.trip('pre', photos=[photo('photos/01.webp', LANDSCAPE, sm=True)])
        link = core.cover_preload(t, '', '(min-width: 760px) 50vw, 100vw')
        self.assertEqual(link, '<link rel="preload" as="image" href="trips/pre/photos/01.webp" '
                               'imagesrcset="trips/pre/photos/01.sm.webp 800w, trips/pre/photos/01.webp 1600w" '
                               'imagesizes="(min-width: 760px) 50vw, 100vw" fetchpriority="high">')
        t2 = self.trip('nosm', photos=[photo('photos/01.webp', LANDSCAPE)])
        self.assertEqual(core.cover_preload(t2, '', '100vw'), '<link rel="preload" as="image" href="trips/nosm/photos/01.webp" fetchpriority="high">')

    def test_explicit_day_photo_missing_on_disk_raises(self):
        with self.assertRaises(ValueError) as cm:
            self.trip('gone-day', kind='multi-day', cover_photo='photos/d01-01.webp', missing=('photos/d01-01.webp',),
                      days=[{'photos': [photo('photos/d01-01.webp', LANDSCAPE)]}])
        self.assertIn('content/trips/gone-day/index.md: cover_photo', str(cm.exception))
        self.assertIn('photos/d01-01.webp', str(cm.exception))

    def test_handwritten_bare_cover_photo_counts_as_absent(self):
        folder = os.path.join(self.tmp, 'bare-key')
        os.makedirs(os.path.join(folder, 'photos'))
        open(os.path.join(folder, 'photos', '01.webp'), 'a').close()
        with open(os.path.join(folder, 'index.md'), 'w', encoding='utf-8') as fh:
            fh.write('---\ntitle: Bare Key\nactivity: hike\ncover_photo:\ncard_summary:\nphotos:\n  - file: photos/01.webp\n    w: 1600\n    h: 1200\n    alt: View\n---\n\nText.\n')
        t = content.load_trip(folder)
        self.assertIsNone(t['cover_photo'])
        self.assertIsNone(t['card_summary'])
        self.assertEqual(t['cover']['source'], 'parent')

    def test_front_matter_syntax_error_names_the_file(self):
        folder = os.path.join(self.tmp, 'broken')
        os.makedirs(folder)
        with open(os.path.join(folder, 'index.md'), 'w', encoding='utf-8') as fh:
            fh.write('---\ntitle: Never closed\nactivity: hike\n\nText.\n')
        with self.assertRaises(content.ContentError) as cm:
            content.load_trip(folder)
        self.assertTrue(str(cm.exception).startswith('content/trips/broken/index.md: front matter: '), str(cm.exception))
        folder2 = os.path.join(self.tmp, 'broken-day')
        os.makedirs(os.path.join(folder2, 'days'))
        with open(os.path.join(folder2, 'index.md'), 'w', encoding='utf-8') as fh:
            fh.write('---\ntitle: Ok\nactivity: hike\nkind: multi-day\n---\n')
        with open(os.path.join(folder2, 'days', '01.md'), 'w', encoding='utf-8') as fh:
            fh.write('---\ntitle: "half quoted\n---\n')
        with self.assertRaises(content.ContentError) as cm:
            content.load_trip(folder2)
        self.assertTrue(str(cm.exception).startswith('content/trips/broken-day/days/01.md: front matter: '), str(cm.exception))


class FactsWordingTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def test_single_recorded_day_is_singular(self):
        helpers.make_series(self.tmp, 'one', tracks=(True, False), written_day=None, photos=False)
        t = helpers.load(self.tmp, 'one')
        self.assertEqual(core.card_summary(t)['text'], 'Journal of 1 recorded day, Apr 22 – Sep 21, 2024, Mexico to Canada.')

    def test_series_without_tracks_drops_the_count(self):
        helpers.make_series(self.tmp, 'zero', tracks=(False, False), written_day=None, photos=False)
        t = helpers.load(self.tmp, 'zero')
        self.assertEqual(core.card_summary(t)['text'], 'Journal, Apr 22 – Sep 21, 2024, Mexico to Canada.')

    def test_multiday_without_dates_has_no_dangling_comma(self):
        helpers.make_trip(self.tmp, 'undated', activity='ski', kind='multi-day', days=[{}, {}, {}])
        t = helpers.load(self.tmp, 'undated')
        self.assertEqual(core.card_summary(t)['text'], '3-day backcountry ski trip.')


if __name__ == '__main__':
    unittest.main()
