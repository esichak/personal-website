"""Phase 1: the home page's featured cards and recent shelf (sitegen.pages.home.featured / recent).

site['featured'] is set directly here (the build gets it from curation.featured_for); core may read
rendered/site/meta.json lazily, which is fine. Fixture slugs deliberately match no real trip, so nothing under
rendered/trips/ is ever consulted.
"""
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
from sitegen import core  # noqa: E402,F401
from sitegen.pages import home  # noqa: E402

import helpers  # noqa: E402
from helpers import PCT_PROSE, photo, LANDSCAPE, PORTRAIT  # noqa: E402

H3 = re.compile(r'<h3\b[^>]*>(.*?)</h3>', re.S)
HREF = re.compile(r'href="([^"]*)"')
TRIP_HREF = re.compile(r'href="trips/([^/"]+)/"')
LEAD = re.compile(r'(?<![\w-])hom-card--lead(?![\w-])')
SUB = re.compile(r'(?<![\w-])hom-card--sub(?![\w-])')

WRITEUP = 'Skinned up from the lake before dawn and skied the couloir on firm, edgeable snow.'
BRIEFS = [('brief-a', '2025-11-01'), ('brief-b', '2025-10-01'), ('brief-c', '2025-09-01'),
          ('brief-d', '2025-07-01'), ('brief-e', '2025-06-01'), ('brief-f', '2025-05-01')]


def h3_hrefs(html_):
    """The first href inside each <h3>, in document order (None for an h3 without a link)."""
    out = []
    for inner in H3.findall(html_):
        hs = HREF.findall(inner)
        out.append(hs[0] if hs else None)
    return out


def trip_slugs(html_):
    """Slugs of every trips/<slug>/ link, in first-appearance order, without repeats."""
    out = []
    for s in TRIP_HREF.findall(html_):
        if s not in out:
            out.append(s)
    return out


class HomeTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        helpers.make_series(self.tmp, 'journal-series', title='Long Trail 2024')
        helpers.make_trip(self.tmp, 'ski-report', title='West Couloir', activity='ski', date='2026-01-17', place='Sawtooth Ridge',
                          region='Eastern Sierra', body=WRITEUP, track=True,
                          photos=[photo('photos/01.webp', PORTRAIT, alt='Skinning'), photo('photos/02.webp', LANDSCAPE, alt='The couloir', sm=True)])
        helpers.make_trip(self.tmp, 'loop-hike', title='Basin Loop', activity='hike', date='2025-08-10', region='Eastern Sierra',
                          body='A loop over three summits with a long scree descent.', track=True,
                          photos=[photo('photos/01.webp', LANDSCAPE, alt='The basin')])
        helpers.make_trip(self.tmp, 'track-only', title='Quick Lap', activity='ski', date='2025-12-01', track=True)
        for slug, d in BRIEFS:
            helpers.make_trip(self.tmp, slug, activity='mtb', date=d, track=True)
        helpers.make_trip(self.tmp, 'planned-route', title='Someday Ridge', activity='ski', kind='planned', date='2026-06-01', track=True)
        self.trips = helpers.load_dir(self.tmp)
        self.site = helpers.make_site(self.trips)
        self.published = helpers.slugs(self.site['published'])     # newest first

    def feat(self, featured_slugs):
        self.site['featured'] = [self.site['by_slug'][s] for s in featured_slugs]
        return home.featured(self.site)

    # ------------------------------------------------------------ featured

    def test_featured_lists_title_links_in_manifest_order(self):
        order = ['loop-hike', 'journal-series', 'ski-report']
        html_ = self.feat(order)
        self.assertIsInstance(html_, str)
        self.assertEqual(h3_hrefs(html_), ['trips/%s/' % s for s in order])
        # a different order renders in that order: the manifest decides, not dates
        reordered = ['ski-report', 'loop-hike', 'journal-series']
        self.assertEqual(h3_hrefs(self.feat(reordered)), ['trips/%s/' % s for s in reordered])

    def test_featured_empty_list_gives_empty_string(self):
        self.assertEqual(self.feat([]), '')

    def test_featured_renders_1_2_3_and_6_cards(self):
        pool = ['ski-report', 'journal-series', 'loop-hike', 'track-only', 'brief-a', 'brief-b']
        for k in (1, 2, 3, 6):
            with self.subTest(cards=k):
                html_ = self.feat(pool[:k])
                self.assertTrue(html_.strip())
                self.assertEqual(h3_hrefs(html_), ['trips/%s/' % s for s in pool[:k]])
                self.assertEqual(len(LEAD.findall(html_)), 1)
                self.assertEqual(len(SUB.findall(html_)), k - 1)

    def test_lead_card_carries_lead_class_and_the_others_sub(self):
        html_ = self.feat(['ski-report', 'journal-series', 'loop-hike'])
        self.assertEqual(len(LEAD.findall(html_)), 1)
        self.assertEqual(len(SUB.findall(html_)), 2)
        lead_at, first_sub = LEAD.search(html_).start(), SUB.search(html_).start()
        self.assertLess(lead_at, first_sub)
        lead_card = html_[lead_at:first_sub]
        self.assertIn('href="trips/ski-report/"', lead_card)
        self.assertNotIn('trips/journal-series/', lead_card)
        self.assertNotIn('trips/loop-hike/', lead_card)

    def test_single_card_is_the_lead(self):
        html_ = self.feat(['loop-hike'])
        self.assertEqual(len(LEAD.findall(html_)), 1)
        self.assertEqual(SUB.findall(html_), [])

    def test_card_hrefs_are_relative_from_the_home_page(self):
        for href in h3_hrefs(self.feat(['ski-report', 'journal-series', 'loop-hike'])):
            self.assertTrue(href.startswith('trips/'), href)
            self.assertFalse(href.startswith(('/', './', '../', 'http')), href)

    def test_series_card_shows_journal_facts_and_no_day_prose(self):
        t = self.site['by_slug']['journal-series']
        self.assertTrue(any(d['body_md'] for d in t['days']))
        html_ = self.feat(['journal-series'])
        self.assertIn('Explore the journal', html_)
        self.assertIn('Journal', html_)
        # the facts (recorded-day count), however the card sets them: as a sentence or as caps meta items with nbsp
        self.assertIn('recorded days', html_.replace('\xa0', ' ').lower())
        self.assertNotIn(PCT_PROSE, html_)
        self.assertNotIn('afternoon heat', html_)
        self.assertNotIn('Read the report', html_)
        self.assertNotIn('View trip', html_)

    def test_writeup_card_says_read_the_report(self):
        html_ = self.feat(['ski-report'])
        self.assertIn('Read the report', html_)
        self.assertNotIn('View trip', html_)
        self.assertNotIn('Explore the journal', html_)

    def test_track_only_card_says_view_trip(self):
        t = self.site['by_slug']['track-only']
        self.assertFalse(t['has_writeup'])
        self.assertTrue(t['track'])
        html_ = self.feat(['track-only'])
        self.assertIn('View trip', html_)
        self.assertNotIn('Read the report', html_)
        self.assertNotIn('Explore the journal', html_)

    def test_mixed_cards_each_carry_their_own_link_text(self):
        html_ = self.feat(['journal-series', 'ski-report', 'track-only'])
        self.assertIn('Explore the journal', html_)
        self.assertIn('Read the report', html_)
        self.assertIn('View trip', html_)

    # ------------------------------------------------------------ recent

    def test_recent_excludes_featured_and_caps_at_six_newest_first(self):
        self.assertEqual(len(self.published), 10)
        featured = ['ski-report', 'journal-series']
        self.assertEqual(self.published[0], 'ski-report')          # the newest published trip is featured
        self.site['featured'] = [self.site['by_slug'][s] for s in featured]
        html_ = home.recent(self.site)
        self.assertIsInstance(html_, str)
        expected = [s for s in self.published if s not in featured][:6]
        self.assertEqual(len(expected), 6)
        self.assertEqual(trip_slugs(html_), expected)
        for s in featured:
            self.assertNotIn('trips/%s/' % s, html_)

    def test_recent_with_nothing_featured_is_the_six_newest(self):
        self.site['featured'] = []
        self.assertEqual(trip_slugs(home.recent(self.site)), self.published[:6])

    def test_recent_never_includes_a_planned_route(self):
        self.assertEqual(self.site['trips'][0]['slug'], 'planned-route')  # newest of all, but planned
        self.assertNotIn('planned-route', self.published)
        self.site['featured'] = []
        html_ = home.recent(self.site)
        self.assertNotIn('planned-route', trip_slugs(html_))
        self.assertNotIn('Someday Ridge', html_)
        self.site['featured'] = [self.site['by_slug'][s] for s in self.published[:5]]
        self.assertNotIn('planned-route', trip_slugs(home.recent(self.site)))

    def test_recent_lists_everything_when_fewer_than_six_remain(self):
        keep = ['ski-report', 'loop-hike', 'track-only', 'planned-route']
        site2 = helpers.make_site([self.site['by_slug'][s] for s in keep])
        site2['featured'] = [site2['by_slug']['ski-report']]
        self.assertEqual(trip_slugs(home.recent(site2)), ['track-only', 'loop-hike'])

    def test_recent_is_empty_when_every_published_trip_is_featured(self):
        site2 = helpers.make_site([self.site['by_slug'][s] for s in ('ski-report', 'loop-hike', 'planned-route')])
        site2['featured'] = list(site2['published'])
        self.assertEqual(home.recent(site2), '')


if __name__ == '__main__':
    unittest.main()
