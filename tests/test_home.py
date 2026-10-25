"""Phase 1: the home page's featured cards and recent shelf (sitegen.pages.home.featured / recent).

site['featured'] is set directly here (the build gets it from curation.featured_for). Fixture slugs deliberately match
no real trip, so nothing under rendered/trips/ is ever consulted, and core's copy of rendered/site/meta.json is a
synthetic one without region maps for the length of each test (core._SITE_META, with core.ROOT in the temp dir), so
home.page() builds without reading the real rendered/site/.

Phase 4 (contract-phase4.md), in HomePageTests: the page's share image is core.share_photo of the lead card's trip, with
its recorded size and alt text, and there is none without a feature (4.1); the lead image and its preload name the
same candidates and sizes; the three feature-card sizes strings end with core.PHONE_FULL (5.2); a recent card's cover
that has a card-size .th copy offers it to phones in a <source> of its own, and no <img> and no preload on the page
lists it (5.3 as replaced by 10.5; a .th file is an empty placeholder the test writes).

Review gate (fix A), in LatestAnchorTests and LatestAnchorBuiltTests: the 'Recent outings' section carries
id="latest-h", the id the public home page's 'Latest reports' list had, so that a saved address ending in #latest-h
lands on the newest reports again. The id is on the page once and only while the section is; on a site built from
the synthetic fixture of tests/test_build_site.py the site checks find no id twice and a link to it resolves.
"""
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
from sitegen import core  # noqa: E402,F401
from sitegen import sitecheck  # noqa: E402
from sitegen.pages import archive, home  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, PCT_PROSE, photo, LANDSCAPE, PORTRAIT  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

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


class HomeFixture(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        # no region map is rendered in this fixture: home.where() then draws none, and nothing is read from rendered/site/
        for target, name, value in ((core, '_SITE_META', [{'hash': '', 'maps': {}, 'regions': [], 'all_regions': ['Eastern Sierra']}]),
                                    (core, 'ROOT', self.tmp), (core, '_SITE_SHARE', [None])):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
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


class HomeTests(HomeFixture):

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

    # ------------------------------------------------------------ recent cards: the write-up's opening, a repeated title (Phase 7)

    def recent_cards(self):
        return {li['data-slug']: li for li in Doc(home.recent(self.site)).find_all('li', cls='tcard')}

    def test_a_written_recent_card_opens_its_write_up_and_a_track_only_one_stays_bare(self):
        self.site['featured'] = []
        cards = self.recent_cards()
        ex = cards['loop-hike'].find('p', cls='tcard-ex')
        self.assertIsNotNone(ex)
        self.assertEqual(ex.text(), core.card_summary(self.site['by_slug']['loop-hike'])['text'])
        self.assertEqual(ex.text(), 'A loop over three summits with a long scree descent.')        # the write-up, verbatim
        for slug in ('track-only', 'brief-a'):
            self.assertEqual(cards[slug].find_all('p', cls='tcard-ex') + cards[slug].find_all('p', cls='tcard-exl'), [], slug)

    def test_a_title_two_cards_carry_names_the_date_in_its_link(self):
        helpers.make_trip(self.tmp, 'quick-lap-again', title='Quick Lap', activity='ski', date='2025-12-02', track=True)
        self.site = helpers.make_site(helpers.load_dir(self.tmp))
        self.site['featured'] = []
        cards = self.recent_cards()
        for slug in ('track-only', 'quick-lap-again'):
            t = self.site['by_slug'][slug]
            link_ = cards[slug].find('h3').find('a')
            self.assertEqual([sp.text() for sp in link_.find_all('span', cls='sr')], [', ' + helpers.plain_text(core.trip_date(t, caps=False, short=True))])
            self.assertTrue(link_.text().startswith('Quick Lap, '))
        # a title of its own does not
        own = [slug for slug in cards if slug not in ('track-only', 'quick-lap-again')]
        self.assertTrue(own)
        for slug in own:
            self.assertEqual(cards[slug].find('h3').find('a').find_all('span', cls='sr'), [], slug)

    def test_a_recent_card_that_repeats_a_featured_title_names_its_date_too(self):
        helpers.make_trip(self.tmp, 'couloir-again', title='West Couloir', activity='ski', date='2025-11-15', track=True)
        self.site = helpers.make_site(helpers.load_dir(self.tmp))
        self.site['featured'] = [self.site['by_slug']['ski-report']]
        link_ = self.recent_cards()['couloir-again'].find('h3').find('a')
        self.assertEqual(len(link_.find_all('span', cls='sr')), 1)


def share_meta(doc):
    """{property or name: content} of a page's share-image tags (og:image and its properties, the twitter card)."""
    out = {}
    for m in doc.find('head').find_all('meta'):
        key = m['property'] or m['name'] or ''
        if key.startswith(('og:image', 'twitter:')):
            if key in out:
                raise AssertionError('two %s tags' % key)
            out[key] = m['content']
    return out


class HomePageTests(HomeFixture):
    """home.page(site): the head's share image and preload, and what the cards' images tell a browser to load."""

    PHONE_FULL = '(min-width: 560px) 100vw, 55vw'    # contract-phase4.md 5.2: core.PHONE_FULL, written out

    def page(self, featured_slugs):
        """The home page of the fixture site with these features, registered with core as build.py does."""
        self.site['featured'] = [self.site['by_slug'][s] for s in featured_slugs]
        core.register_site(self.site)
        p = home.page(self.site)
        return p, Doc(p.html)

    def reload(self):
        """Load the temp folder again (after a test added a file to it)."""
        self.trips = helpers.load_dir(self.tmp)
        self.site = helpers.make_site(self.trips)

    def lead_img(self, doc):
        return doc.by_id('main').find('li', cls='hom-card--lead').find('img', cls='cover-img')

    def preloads(self, doc):
        return doc.find('head').find_all('link', attrs={'rel': 'preload', 'as': 'image'})

    # ------------------------------------------------------------ the share image (4.1)

    def test_the_share_image_is_the_share_photo_of_the_lead(self):
        # 4.1 and 10: home passes core.share_photo(lead): the cover of the first featured trip, with the size and the
        # alt text recorded for it; the og:image is SITE_URL + its path
        p, doc = self.page(['ski-report', 'loop-hike'])
        lead = self.site['by_slug']['ski-report']
        share = core.share_photo(lead)
        self.assertEqual(share, {'path': 'trips/ski-report/photos/02.webp', 'w': 1600, 'h': 1200, 'alt': 'The couloir'})
        self.assertEqual(share_meta(doc), {'og:image': core.SITE_URL + share['path'], 'og:image:type': 'image/webp',
                                           'og:image:width': '1600', 'og:image:height': '1200', 'og:image:alt': 'The couloir',
                                           'twitter:card': 'summary_large_image', 'twitter:image:alt': 'The couloir'})
        self.assertEqual(share_meta(doc)['og:image'], core.SITE_URL + 'trips/ski-report/photos/02.webp')
        self.assertIn(core._share_tags(share), p.html.split('</head>', 1)[0])
        # it is the photo the lead card shows, and what the site-level pages share (core.site_share)
        self.assertEqual(self.lead_img(doc)['src'], share['path'])
        self.assertEqual(core.site_share(), share)
        # the lead decides, not the newest or the last feature
        _p, doc = self.page(['loop-hike', 'ski-report'])
        self.assertEqual(share_meta(doc)['og:image'], core.SITE_URL + 'trips/loop-hike/photos/01.webp')
        self.assertEqual((share_meta(doc)['og:image:alt'], share_meta(doc)['twitter:image:alt']), ('The basin', 'The basin'))

    def test_a_journal_lead_shares_its_day_cover(self):
        # the cover of a journal is a day's photo: its size and alt text come from that day file
        _p, doc = self.page(['journal-series'])
        lead = self.site['by_slug']['journal-series']
        self.assertEqual(lead['cover']['source'], 'day')
        self.assertEqual(share_meta(doc), {'og:image': core.SITE_URL + 'trips/journal-series/photos/d001-02.webp', 'og:image:type': 'image/webp',
                                           'og:image:width': '1600', 'og:image:height': '1200', 'og:image:alt': 'Ridge view, day 1',
                                           'twitter:card': 'summary_large_image', 'twitter:image:alt': 'Ridge view, day 1'})

    def test_no_share_image_without_a_feature(self):
        # 4.1: nothing is featured, nothing is shared: no og:image and none of its properties, the small card
        p, doc = self.page([])
        self.assertEqual(share_meta(doc), {'twitter:card': 'summary'})
        self.assertNotIn('og:image', p.html)
        self.assertNotIn('twitter:image', p.html)
        self.assertIsNone(core.site_share())
        self.assertEqual(self.preloads(doc), [])

    def test_a_lead_without_a_photo_shares_none(self):
        # the second feature's photo is not borrowed for the page
        p, doc = self.page(['track-only', 'ski-report'])
        self.assertIsNone(self.site['by_slug']['track-only']['cover'])
        self.assertIsNone(core.share_photo(self.site['by_slug']['track-only']))
        self.assertEqual(share_meta(doc), {'twitter:card': 'summary'})
        self.assertNotIn('og:image', p.html)
        self.assertEqual(self.preloads(doc), [])

    def test_one_title_one_description_one_canonical(self):
        # the page around the share tags is as it was
        p, doc = self.page(['ski-report'])
        head = doc.find('head')
        self.assertEqual([t.text() for t in head.find_all('title')], [home.TITLE])
        self.assertEqual([m['content'] for m in head.find_all('meta', attrs={'name': 'description'})], [core.TAGLINE])
        self.assertEqual([l['href'] for l in head.find_all('link', attrs={'rel': 'canonical'})], [core.SITE_URL])
        self.assertEqual([m['content'] for m in head.find_all('meta', attrs={'property': 'og:url'})], [core.SITE_URL])
        self.assertEqual(p.url, '')

    # ------------------------------------------------------------ the lead image and its preload (5.2)

    def test_the_lead_image_and_its_preload_agree(self):
        # the head preloads exactly what the lead card's <img> will ask for: the same file, candidates and sizes, for a
        # cover with every copy (the .th file exists: 10.5 keeps it out of both), with the .sm copy alone, and for a
        # cover that has neither
        helpers.make_trip(self.tmp, 'th-lead', title='Thumb Lead', activity='hike', date='2025-03-03', track=True,
                          photos=[photo('photos/01.webp', LANDSCAPE, alt='A lead with every copy', sm=True)])
        helpers.touch(os.path.join(self.tmp, 'th-lead', 'photos', '01.th.webp'))
        self.reload()
        for slug, has_srcset in (('th-lead', True), ('ski-report', True), ('loop-hike', False)):
            with self.subTest(lead=slug):
                p, doc = self.page([slug, 'track-only'])
                links = self.preloads(doc)
                self.assertEqual(len(links), 1)
                img = self.lead_img(doc)
                self.assertEqual(links[0]['href'], img['src'])
                self.assertEqual(links[0]['imagesrcset'], img['srcset'])
                self.assertEqual(links[0]['imagesizes'], img['sizes'])
                self.assertEqual((links[0]['fetchpriority'], img['fetchpriority']), ('high', 'high'))
                self.assertNotIn('loading', img)
                self.assertEqual(img['srcset'] is not None, has_srcset)
                self.assertEqual(img['sizes'], home.LEAD_SIZES if has_srcset else None)
                self.assertIn(core.cover_preload(self.site['by_slug'][slug], '', home.LEAD_SIZES), p.html.split('</head>', 1)[0])
                # the lead image is never wrapped, and neither it nor its preload names a .th file
                self.assertEqual(img.parent.tag, 'a')
                self.assertNotIn('.th.', (img['srcset'] or '') + (links[0]['imagesrcset'] or '') + links[0]['href'])
                self.assertEqual(doc.by_id('main').find('ul', cls='hom-cards').find_all('picture'), [])
        self.assertEqual(self.site['by_slug']['th-lead']['cover']['photo']['th'], 'photos/01.th.webp')
        _p, doc = self.page(['th-lead', 'track-only'])
        self.assertEqual(self.lead_img(doc)['srcset'], 'trips/th-lead/photos/01.sm.webp 800w, trips/th-lead/photos/01.webp 1600w')

    def test_feature_card_sizes_end_with_the_phone_slot(self):
        # 10: LEAD_SIZES, SUB_SIZES and WIDE_SUB_SIZES end with core.PHONE_FULL in place of a bare 100vw; the recent cards'
        # string (a 112 px thumbnail on a phone) is unchanged
        self.assertEqual(core.PHONE_FULL, self.PHONE_FULL)
        want = {'LEAD_SIZES': '(min-width: 1200px) 718px, (min-width: 760px) calc(100vw - 80px), ',
                'SUB_SIZES': '(min-width: 1200px) 200px, (min-width: 760px) calc((100vw - 104px) / 2), ',
                'WIDE_SUB_SIZES': '(min-width: 1200px) 400px, (min-width: 760px) calc((100vw - 104px) / 2), '}
        for name, start in want.items():
            with self.subTest(name):
                self.assertTrue(hasattr(home, name), 'home.%s is missing' % name)
                sizes = getattr(home, name)
                self.assertEqual(sizes, start + self.PHONE_FULL)
                self.assertTrue(sizes.endswith(', ' + core.PHONE_FULL))
                entries = re.split(r', (?=\(|\d)', sizes)           # the entries (a calc() holds no ', ')
                self.assertEqual(entries[-1], core.PHONE_SLOT)       # the unconditional fallback is the slot ...
                self.assertNotIn('100vw', entries)                   # ... and no entry is a bare 100vw
                self.assertTrue(all(e.startswith('(min-width: ') for e in entries[:-1]), entries)
        self.assertEqual(home.RECENT_SIZES, '(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2), 112px')

    def test_each_feature_card_uses_its_own_sizes(self):
        # the lead card, a supporting card and one of cards 4-6 (three to a row), for a cover with an .sm copy
        t = self.site['by_slug']['ski-report']
        got = [Doc(home.card(t, **kw)).find('img', cls='cover-img')['sizes'] for kw in ({'lead': True}, {}, {'wide': True})]
        self.assertEqual(got, [home.LEAD_SIZES, home.SUB_SIZES, home.WIDE_SUB_SIZES])
        self.assertEqual(len(set(got)), 3)
        # on the page, with six features: the lead, a supporting card (2-3) and a card of the second row (4-6)
        for slug in ('sub-photo', 'wide-photo'):
            helpers.make_trip(self.tmp, slug, activity='hike', date='2025-02-02', track=True,
                              photos=[photo('photos/01.webp', LANDSCAPE, alt='A synthetic view', sm=True)])
        self.reload()
        _p, doc = self.page(['ski-report', 'sub-photo', 'track-only', 'wide-photo', 'brief-a', 'brief-b'])
        cards = doc.by_id('main').find('ul', cls='hom-cards').find_all('li', cls='hom-card')
        self.assertEqual(len(cards), 6)
        sizes = [c.find('img', cls='cover-img') and c.find('img', cls='cover-img')['sizes'] for c in cards]
        self.assertEqual(sizes, [home.LEAD_SIZES, home.SUB_SIZES, None, home.WIDE_SUB_SIZES, None, None])

    # ------------------------------------------------------------ the card-size copy (5.3, 10.5)

    PICTURE = re.compile(r'<picture class="cover-pic">(<source [^>]*>)(<img [^>]*>)</picture>')

    def unwrap(self, html_):
        """The markup with every card cover's <picture class="cover-pic"> taken off: the <img> it holds, alone."""
        return self.PICTURE.sub(lambda m: m.group(2), html_)

    def test_recent_cards_offer_the_card_size_copy_to_phones_only(self):
        # 10.5 (it replaces 5.3, under which the .th copy led the <img>'s own srcset): a recent-outing card (core.trip_card
        # at RECENT_SIZES) whose cover has the copy is wrapped in <picture class="cover-pic"> with one phone-only <source>
        # that lists the copy first; its <img> is the <img> of the card without the file
        base = 'trips/ski-report/photos/'
        two = '%s02.sm.webp 800w, %s02.webp 1600w' % (base, base)
        self.site['featured'] = []
        before = home.recent(self.site)
        img = Doc(before).find('li', attrs={'data-slug': 'ski-report'}).find('img')
        self.assertEqual(img['srcset'], two)                                                            # no .th file: as before
        self.assertNotIn('<picture', before)
        _p, doc = self.page([])
        page_before = _p.html
        helpers.touch(os.path.join(self.tmp, 'ski-report', 'photos', '02.th.webp'))
        self.reload()
        self.assertEqual([p['th'] for p in self.site['by_slug']['ski-report']['photos']], [None, 'photos/02.th.webp'])
        self.site['featured'] = []
        after = home.recent(self.site)
        cards = Doc(after)
        card = cards.find('li', attrs={'data-slug': 'ski-report'})
        img = card.find('img')
        self.assertEqual(img['srcset'], two)                                                            # with the file: the same
        self.assertEqual(img['sizes'], home.RECENT_SIZES)
        self.assertEqual((img['src'], img['loading']), (base + '02.webp', 'lazy'))
        pic = card.find('picture')
        self.assertEqual((pic.classes, [n.tag for n in pic.elements()], pic.parent.classes), (['cover-pic'], ['source', 'img'], ['tcard-img']))
        source = pic.find('source')
        # the source declares 106 px (core.CARD_PHONE_SIZES, contract-phase5.md section 5), the <img> string still ends
        # with the real 112 px slot
        self.assertEqual((source['media'], source['sizes'], source['srcset']),
                         ('(max-width: 559.98px)', '106px', '%s02.th.webp 427w, %s' % (base, two)))
        self.assertEqual((source['sizes'], img['sizes'].rsplit(', ', 1)[1]), (core.CARD_PHONE_SIZES, core.CARD_PHONE_SLOT))
        self.assertEqual((after.count('<picture'), after.count('.th.')), (1, 1))
        self.assertEqual(self.unwrap(after), before)
        # a cover without an .sm copy stays a plain src, unwrapped
        plain = cards.find('li', attrs={'data-slug': 'loop-hike'}).find('img')
        self.assertEqual((plain['src'], plain['srcset'], plain['sizes']), ('trips/loop-hike/photos/01.webp', None, None))
        self.assertEqual(cards.find('li', attrs={'data-slug': 'loop-hike'}).find_all('picture'), [])
        # ... and on the built page the same card carries the same picture, the page being otherwise what it was
        p, doc = self.page([])
        on_page = doc.by_id('main').find('ul', cls='hom-rcards').find('li', attrs={'data-slug': 'ski-report'})
        self.assertEqual((on_page.find('img')['srcset'], on_page.find('img')['sizes']), (img['srcset'], img['sizes']))
        self.assertEqual(on_page.find('source')['srcset'], source['srcset'])
        self.assertEqual(p.html.count(core.cover_img(self.site['by_slug']['ski-report'], '', home.RECENT_SIZES)), 1)
        self.assertEqual(self.unwrap(p.html), page_before)
        self.assertNotEqual(p.html, page_before)

    def test_a_feature_card_is_never_wrapped_and_no_img_or_preload_names_the_copy(self):
        # 10.5: the featured cards' strings are full-width ones (they end with the phone slot, not ', 112px'), and the
        # lead card is the page's lead image: none of them gets a source, with every copy on disk. Only the recent
        # shelf's cards do
        for slug, day in (('sub-photo', '2026-12-01'), ('wide-photo', '2026-12-02')):       # the two newest: on the recent shelf
            helpers.make_trip(self.tmp, slug, activity='hike', date=day, track=True,
                              photos=[photo('photos/01.webp', LANDSCAPE, alt='A synthetic view', sm=True)])
        for slug, name in (('ski-report', '02'), ('sub-photo', '01'), ('wide-photo', '01')):
            helpers.touch(os.path.join(self.tmp, slug, 'photos', name + '.th.webp'))
        self.reload()
        featured = ['ski-report', 'sub-photo', 'track-only', 'wide-photo', 'brief-a', 'brief-b']
        for slug in ('ski-report', 'sub-photo', 'wide-photo'):
            self.assertTrue(self.site['by_slug'][slug]['cover']['photo']['th'], slug)
        p, doc = self.page(featured)
        main = doc.by_id('main')
        self.assertEqual(main.find('ul', cls='hom-cards').find_all('picture') + main.find('ul', cls='hom-cards').find_all('source'), [])
        for img in doc.find_all('img'):
            self.assertNotIn('.th.', (img['srcset'] or '') + (img['src'] or ''))
        for ln in doc.find('head').find_all('link'):
            self.assertNotIn('.th.', (ln['imagesrcset'] or '') + (ln['href'] or ''))
        # the lead and its preload: the same two candidates
        lead, links = self.lead_img(doc), self.preloads(doc)
        self.assertEqual([(ln['href'], ln['imagesrcset'], ln['imagesizes']) for ln in links], [(lead['src'], lead['srcset'], lead['sizes'])])
        self.assertEqual(lead['srcset'], 'trips/ski-report/photos/02.sm.webp 800w, trips/ski-report/photos/02.webp 1600w')
        # every .th file the page names is named by the source of a recent card whose report has it, and is on disk
        sources = doc.find_all('source')
        self.assertEqual(p.html.count('.th.'), len(sources))
        self.assertEqual(len(doc.find_all('picture')), len(sources))
        for source in sources:
            card = source.parent.parent.parent
            self.assertIn('tcard', card.classes)
            self.assertIs(source.parent.parent.parent.parent, main.find('ul', cls='hom-rcards'))
            t = self.site['by_slug'][card['data-slug']]
            first = source['srcset'].split(', ')[0].split(' ')[0]
            self.assertEqual(first, t['url'] + t['cover']['photo']['th'])
            self.assertTrue(os.path.isfile(os.path.join(self.tmp, t['slug'], t['cover']['photo']['th'])))
        # the recent shelf lists the reports that are not featured: none of the three with a copy is among them here
        shelf = [c['data-slug'] for c in main.find('ul', cls='hom-rcards').find_all('li', cls='tcard')]
        self.assertEqual(sorted(s['srcset'].split('/')[1] for s in sources), sorted(x for x in shelf if x in ('ski-report', 'sub-photo', 'wide-photo')))
        # with nothing featured the shelf holds the newest reports, and each of them that has the copy is wrapped
        p, doc = self.page([])
        rcards = doc.by_id('main').find('ul', cls='hom-rcards')
        shelf = [c['data-slug'] for c in rcards.find_all('li', cls='tcard')]
        wrapped = [pic.parent.parent['data-slug'] for pic in rcards.find_all('picture')]
        self.assertEqual(wrapped, [x for x in shelf if x in ('ski-report', 'sub-photo', 'wide-photo')])
        self.assertIn('sub-photo', wrapped)
        self.assertIn('wide-photo', wrapped)
        self.assertEqual(p.html.count('.th.'), len(wrapped))


# ---------------------------------------------------------------- Phase 5: the links to a region's own page

PEAKS = "Synthetic O'Brien & <Peaks>"      # a region name every context must escape


def legacy_also_items(site):
    """home.also_items as it was at commit fb425ab (Phase 4), copied line for line."""
    esc, link, HERE = core.esc, core.link, home.HERE
    mapped = set(core.site_meta().get('regions') or [])
    counts = {}
    for t in site['published']:
        r = t.get('region')
        if r and home.is_report(t) and t['kind'] != 'series':
            counts[r] = counts.get(r, 0) + 1
    item = '<li><a href="%s"><span class="hom-also-w">%s</span>%s</a></li>'
    out = []
    for r in sorted((r for r in mapped if r not in home.HOME_REGIONS), key=lambda r: (-counts.get(r, 0), r)):
        k = counts.get(r, 0)
        out.append(item % (core.region_map_href(HERE, r) or link(HERE, 'map/#region-' + home.slug(r)), esc(r),
                           ('<span class="hom-also-c">%d</span>' % k) if k else ''))
    unmapped = [r for r in counts if r not in mapped and r not in home.HOME_REGIONS]
    if unmapped:
        more = '%d more region%s' % (len(unmapped), '' if len(unmapped) == 1 else 's')
        out.append(item % (link(HERE, 'map/#other-places'), esc(more), ''))
    out += [item % (link(HERE, t['url']), esc(t['title']), '<span class="hom-also-c">SERIES</span>')
            for t in site['published'] if t['kind'] == 'series']
    return out


def legacy_where(site):
    """home.where as it was at commit fb425ab, copied line for line (with legacy_also_items for its Also row)."""
    esc, link, icon, HERE = core.esc, core.link, core.icon, home.HERE
    meta = core.site_meta().get('maps', {})
    blocks = []
    drawn = []
    for region in home.HOME_REGIONS:
        rs = home.slug(region)
        dk, ph = 'region-%s-desktop' % rs, 'region-%s-phone' % rs
        if dk not in meta and ph not in meta:
            continue
        drawn += [x for x in (dk, ph) if x in meta]
        slugs = (meta.get(dk) or meta.get(ph)).get('trips', [])
        bits = home.region_counts(site, slugs)
        line = home.meta_line(bits[:1])
        spoken = ', '.join(b.replace(' ', ' ').replace('+ ', '') for b in bits).lower()
        aria = ('%s: %s. Open the map' % (region, spoken)) if bits else '%s: open the map' % region
        mp = core.map_block(None, HERE, [(dk, 'desktop'), (ph, 'phone')], 'assets/maps/', 'rg-' + rs, site_maps=True, attrib=False)
        blocks.append('<div class="hom-reg"><div class="hom-reg-h"><h3 class="hom-reg-n">%s</h3>'
                      '<span class="t-mono-s hom-reg-c">%s</span>'
                      '<a class="hom-reg-a" href="%s" aria-label="%s">Open the map%s</a></div>%s</div>'
                      % (esc(region), line, link(HERE, 'map/#region-' + rs), esc(aria), icon('arrow-right', 16), mp))
    if not blocks:
        return ''
    also = legacy_also_items(site)
    also_html = ('<div class="hom-also"><span class="t-mono-s" id="also-l">ALSO</span><ul aria-labelledby="also-l">%s</ul></div>'
                 % ''.join(also)) if also else ''
    head_meta = home.plural(sum(1 for t in site['published'] if home.is_report(t)), 'REPORT')
    return ('<section class="wrap sec hom-where" aria-labelledby="where-h">%s<div class="hom-regions">%s</div>'
            '%s<p class="t-small hom-attr">North up · %s</p>%s</section>'
            % (core.section_head("Where I’ve been", head_meta, id_='where-h'), ''.join(blocks), home.region_key(site, meta, drawn),
               esc(home.ATTRIB), also_html))


class RegionLinkTests(HomeFixture):
    """contract-phase5.md section 2 on the home page: the name of a region map block (h3.hom-reg-n) is a link to the
    region's page when it has one, 'Open the map' still goes to the Map page, and a region of the 'Also' row links to
    its page instead of its panel. Region maps are placeholders written into the temp dir (rendered/site/, where
    home.where reads them): Eastern Sierra (two reports: a page) and Lake Tahoe (a planned route only: a map block and
    no page) are the home page's two regions; Synthetic Coast (one report: a page) and Synthetic Plans (a planned route
    only: none) are in the Also row, with one region that has no region map and the journal. With no site registered,
    or with one registered without a site meta (REVISED in round 2: what helpers.make_site does), both functions are
    byte for byte the old ones (legacy_also_items, legacy_where: copies of the bodies of fb425ab).

    Round 3: the Also row names a mapped region only while the Map page has a panel for it (core.region_groups lists
    it). A region map outlives its reports until the next render: when they have all been made drafts or removed, the
    old row still linked to map/#region-<slug>, an anchor the Map page no longer has. A mapped region that holds only
    active goals has a panel and keeps its item."""

    MAPPED = {'Eastern Sierra': ['ski-report', 'loop-hike'], 'Lake Tahoe': ['tahoe-plan'], 'Synthetic Coast': ['coast-a'],
              'Synthetic Plans': ['plans-goal']}

    def setUp(self):
        helpers.keep_state(self)              # the region pages this class registers with core are gone afterwards
        super().setUp()
        mk = helpers.make_trip
        mk(self.tmp, 'tahoe-plan', title='Synthetic Tahoe Plan', activity='ski', kind='planned', region='Lake Tahoe')
        mk(self.tmp, 'coast-a', title='Synthetic Coast A', activity='hike', date='2024-02-02', region='Synthetic Coast', track=True)
        mk(self.tmp, 'plans-goal', title='Synthetic Plans Goal', activity='hike', kind='planned', region='Synthetic Plans')
        mk(self.tmp, 'desert-a', title='Synthetic Desert A', activity='climb', date='2024-03-03', region='Synthetic Desert', track=True)
        self.use(self.MAPPED)

    def use(self, mapped):
        """rendered/site/ in the temp dir with a region map (and the trips it draws) for each name in `mapped`; the
        trips loaded again and registered with core together with that meta, as build.py does (registered without it,
        as helpers.make_site alone does, no region would have a page)."""
        site_dir = os.path.join(self.tmp, 'rendered', 'site')
        os.makedirs(site_dir, exist_ok=True)
        maps = {}
        for name, slugs in mapped.items():
            for size, (w, h) in (('desktop', (718, 620)), ('phone', (390, 480))):
                key = 'region-%s-%s' % (home.slug(name), size)
                maps[key] = {'w': w, 'h': h, 'png': key + '.webp', 'base': key + '.base.svg', 'trips': list(slugs)}
                with open(os.path.join(site_dir, key + '.svg.html'), 'w', encoding='utf-8') as fh:
                    fh.write('<svg width="%d" height="%d" viewBox="0 0 %d %d"></svg>' % (w, h, w, h))
        meta = {'hash': '', 'maps': maps, 'regions': sorted(mapped), 'all_regions': sorted(mapped) + ['Synthetic Desert']}
        with open(os.path.join(site_dir, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(meta, fh)
        patcher = mock.patch.object(core, '_SITE_META', [meta])
        patcher.start()
        self.addCleanup(patcher.stop)
        self.meta = meta
        self.trips = helpers.load_dir(self.tmp)
        self.site = helpers.make_site(self.trips, register=False)
        core.register_site(self.site, meta)

    def blocks(self, html_):
        return Doc(html_).find_all('div', cls='hom-reg')

    def also(self, items):
        doc = Doc('<ul>%s</ul>' % ''.join(items))
        return [(a['href'], a.find('span', cls='hom-also-w').text(), a.find('span', cls='hom-also-c').text() if a.find('span', cls='hom-also-c') else None)
                for a in doc.find_all('a')]

    # ------------------------------------------------------------ the fixture

    def test_the_fixture_has_regions_with_a_page_and_without(self):
        self.assertEqual(core._REGION_PAGES, {'Eastern Sierra': 'eastern-sierra', 'Synthetic Coast': 'synthetic-coast'})
        self.assertEqual(home.HOME_REGIONS, ('Lake Tahoe', 'Eastern Sierra'))
        self.assertNotIn('<!-- missing', home.where(self.site))        # both map fragments were found in the temp dir

    def test_a_test_of_this_class_leaves_no_region_page_registered(self):
        helpers.assert_puts_core_back(self, RegionLinkTests('test_the_fixture_has_regions_with_a_page_and_without'))

    # ------------------------------------------------------------ the region map blocks

    def test_the_name_of_a_region_with_a_page_is_a_link_to_it(self):
        tahoe, sierra = self.blocks(home.where(self.site))
        h3 = sierra.find('h3', cls='hom-reg-n')
        (a,) = h3.elements()
        self.assertEqual((a.tag, a['href'], a.children, sorted(a.attrs)), ('a', 'regions/eastern-sierra/', ['Eastern Sierra'], ['href']))
        self.assertEqual(h3.text(), 'Eastern Sierra')
        self.assertEqual(h3.children, [a])                                         # the link is the whole heading
        self.assertIn('<h3 class="hom-reg-n"><a href="regions/eastern-sierra/">Eastern Sierra</a></h3>', home.where(self.site))
        # a region with a region map and no report has no page: its name is the text it was
        self.assertEqual(tahoe.find('h3', cls='hom-reg-n').children, ['Lake Tahoe'])
        self.assertIn('<h3 class="hom-reg-n">Lake Tahoe</h3>', home.where(self.site))

    def test_open_the_map_stays_and_still_goes_to_the_map_page(self):
        tahoe, sierra = self.blocks(home.where(self.site))
        for block, slug, label in ((tahoe, 'lake-tahoe', 'Lake Tahoe: 1 planned route. Open the map'),
                                   (sierra, 'eastern-sierra', 'Eastern Sierra: 2 reports. Open the map')):
            (a,) = block.find_all('a', cls='hom-reg-a')
            self.assertEqual((a['href'], a.text(), a['aria-label']), ('map/#region-' + slug, 'Open the map', label))
        # the heading's link and 'Open the map' are the block's two links; the other block has the one it had
        self.assertEqual([a['href'] for a in sierra.find('div', cls='hom-reg-h').find_all('a')], ['regions/eastern-sierra/', 'map/#region-eastern-sierra'])
        self.assertEqual([a['href'] for a in tahoe.find('div', cls='hom-reg-h').find_all('a')], ['map/#region-lake-tahoe'])
        self.assertEqual([n.tag for n in sierra.find('div', cls='hom-reg-h').elements()], ['h3', 'span', 'a'])

    def test_the_linked_name_is_escaped(self):
        helpers.make_trip(self.tmp, 'peaks-a', title='Synthetic Peaks A', activity='climb', date='2023-01-01', region=PEAKS, track=True)
        with mock.patch.object(home, 'HOME_REGIONS', (PEAKS, 'Eastern Sierra')):
            self.use(dict(self.MAPPED, **{PEAKS: ['peaks-a']}))
            html_ = home.where(self.site)
            self.assertIn('<h3 class="hom-reg-n"><a href="regions/synthetic-obrien-peaks/">Synthetic O&#x27;Brien &amp; &lt;Peaks&gt;</a></h3>', html_)
            self.assertEqual(self.blocks(html_)[0].find('h3').text(), PEAKS)
            self.assertNotIn('<Peaks>', html_)
            # ... and in the Also row, where a region that is not one of the two is listed
        with mock.patch.object(home, 'HOME_REGIONS', ('Eastern Sierra',)):
            self.assertIn(('regions/synthetic-obrien-peaks/', PEAKS, '1'), self.also(home.also_items(self.site)))

    def test_a_name_without_a_page_is_the_escaped_text_it_was(self):
        helpers.make_trip(self.tmp, 'peaks-plan', title='Synthetic Peaks Plan', activity='climb', kind='planned', region=PEAKS)
        with mock.patch.object(home, 'HOME_REGIONS', (PEAKS, 'Eastern Sierra')):
            self.use(dict(self.MAPPED, **{PEAKS: ['peaks-plan']}))
            self.assertNotIn(PEAKS, core._REGION_PAGES)                 # a region map and a planned route only: no page
            html_ = home.where(self.site)
            self.assertIn('<h3 class="hom-reg-n">Synthetic O&#x27;Brien &amp; &lt;Peaks&gt;</h3>', html_)
            self.assertNotIn('<Peaks>', html_)
            core._REGION_PAGES.clear()
            self.assertEqual(home.where(self.site), legacy_where(self.site))

    # ------------------------------------------------------------ the Also row

    def test_an_also_region_with_a_page_links_to_it_and_the_others_as_before(self):
        self.assertEqual(self.also(home.also_items(self.site)),
                         [('regions/synthetic-coast/', 'Synthetic Coast', '1'),           # a region map and a report: its own page
                          ('map/#region-synthetic-plans', 'Synthetic Plans', None),       # a region map, a planned route only: its panel
                          ('map/#other-places', '1 more region', None),                   # no region map: the Map page's block
                          ('trips/journal-series/', 'Long Trail 2024', 'SERIES')])
        self.assertIn('<li><a href="regions/synthetic-coast/"><span class="hom-also-w">Synthetic Coast</span><span class="hom-also-c">1</span></a></li>',
                      home.also_items(self.site))

    def test_the_also_row_is_the_old_one_with_one_address_changed(self):
        old = legacy_also_items(self.site)
        self.assertEqual(''.join(old).count('href="map/#region-synthetic-coast"'), 1)
        self.assertEqual(home.also_items(self.site), [x.replace('href="map/#region-synthetic-coast"', 'href="regions/synthetic-coast/"') for x in old])

    # ------------------------------------------------------------ round 3: a region map the Map page has no panel for

    GHOST = 'Synthetic Ghost'
    GHOST_ITEM = '<li><a href="map/#region-synthetic-ghost"><span class="hom-also-w">Synthetic Ghost</span></a></li>'
    ALSO = [('regions/synthetic-coast/', 'Synthetic Coast', '1'), ('map/#region-synthetic-plans', 'Synthetic Plans', None),
            ('map/#other-places', '1 more region', None), ('trips/journal-series/', 'Long Trail 2024', 'SERIES')]

    def ghost(self, named=('ghost-a', 'ghost-b')):
        """The fixture with one more region map, drawn when Synthetic Ghost had two reports. One has since been made a
        draft and the other removed; the map and its entry in the site meta stay until the next render."""
        helpers.make_trip(self.tmp, 'ghost-a', title='Synthetic Ghost A', activity='hike', date='2023-05-05', region=self.GHOST, track=True,
                          draft=True)
        self.use(dict(self.MAPPED, **{self.GHOST: list(named)}))

    def map_ids(self):
        """Every id of the Map page built for the fixture's site: what a map/#... link of the home page can land on."""
        return {n['id'] for n in Doc(archive.build(self.site)[0].html).root.walk() if n['id']}

    def dead(self, items):
        """The links of an Also row that land on nothing: a map/#id the Map page does not have, or a region page that
        is not built."""
        ids = self.map_ids()
        out = []
        for href, _word, _count in self.also(items):
            if href.startswith('map/#'):
                if href[len('map/#'):] not in ids:
                    out.append(href)
            elif href.startswith('regions/'):
                if href[len('regions/'):-1] not in core._REGION_PAGES.values():
                    out.append(href)
            elif not (href.startswith('trips/') and href[len('trips/'):-1] in self.site['by_slug']):
                out.append(href)
        return out

    def test_a_mapped_region_whose_reports_are_all_gone_has_no_item(self):
        self.assertEqual(self.also(home.also_items(self.site)), self.ALSO)
        self.ghost()
        # the region still has its map, and no trip of the site is on it or filed under it
        self.assertIn(self.GHOST, core.site_meta()['regions'])
        self.assertEqual(core.site_meta()['maps']['region-synthetic-ghost-desktop']['trips'], ['ghost-a', 'ghost-b'])
        self.assertTrue(os.path.exists(os.path.join(self.tmp, 'rendered', 'site', 'region-synthetic-ghost-desktop.svg.html')))
        self.assertEqual([t['slug'] for t in self.site['trips'] if t['slug'].startswith('ghost') or t.get('region') == self.GHOST], [])
        self.assertNotIn(self.GHOST, [name for name, _slug, _ts in core.region_groups(self.site)])
        items = home.also_items(self.site)
        self.assertEqual(self.also(items), self.ALSO)                    # the row it was without that map
        self.assertNotIn('ghost', ''.join(items).lower())
        # the row of commit c7ed3ee (the body of fb425ab) kept it, between the regions it sorts among (no report: by name)
        old = legacy_also_items(self.site)
        self.assertEqual(old.count(self.GHOST_ITEM), 1)
        self.assertEqual([w for _h, w, _c in self.also(old)], ['Synthetic Coast', self.GHOST, 'Synthetic Plans', '1 more region', 'Long Trail 2024'])

    def test_the_home_page_then_holds_no_link_to_a_panel_the_map_page_lacks(self):
        self.ghost()
        html_ = home.page(self.site).html
        self.assertNotIn('map/#region-synthetic-ghost', html_)
        self.assertNotIn('synthetic-ghost', html_)
        self.assertNotIn(self.GHOST, html_)
        ids = self.map_ids()
        self.assertNotIn('region-synthetic-ghost', ids)                  # the Map page has no panel and no list for it
        linked = sorted(set(re.findall(r'href="map/#([^"]+)"', html_)))
        self.assertEqual(linked, ['other-places', 'region-eastern-sierra', 'region-lake-tahoe', 'region-synthetic-plans'])
        self.assertEqual([i for i in linked if i not in ids], [])
        self.assertEqual(self.dead(home.also_items(self.site)), [])
        # before: the one dead link of the page
        self.assertEqual(self.dead(legacy_also_items(self.site)), ['map/#region-synthetic-ghost'])
        with mock.patch.object(home, 'also_items', legacy_also_items):
            before = home.page(self.site).html
        self.assertEqual([i for i in sorted(set(re.findall(r'href="map/#([^"]+)"', before))) if i not in ids], ['region-synthetic-ghost'])
        # and the two pages differ in that item and, as before round 3, in the address of the region that has a page
        self.assertEqual(before.replace(self.GHOST_ITEM, '').replace('href="map/#region-synthetic-coast"', 'href="regions/synthetic-coast/"'), html_)

    def test_a_map_whose_entry_names_no_trip_is_treated_the_same(self):
        # an entry without trips falls back to the trips filed under the region (core.region_groups): there are none
        self.ghost(named=())
        self.assertEqual(core.site_meta()['maps']['region-synthetic-ghost-desktop']['trips'], [])
        self.assertEqual(self.also(home.also_items(self.site)), self.ALSO)
        self.assertEqual(self.dead(home.also_items(self.site)), [])
        self.assertEqual(self.dead(legacy_also_items(self.site)), ['map/#region-synthetic-ghost'])
        # with a report filed under it again the region has its panel, and its item, again
        helpers.make_trip(self.tmp, 'ghost-c', title='Synthetic Ghost C', activity='hike', date='2026-02-02', region=self.GHOST, track=True)
        self.use(dict(self.MAPPED, **{self.GHOST: []}))
        self.assertIn(self.GHOST, [name for name, _slug, _ts in core.region_groups(self.site)])
        self.assertEqual(self.also(home.also_items(self.site)),
                         [('regions/synthetic-coast/', 'Synthetic Coast', '1'), ('regions/synthetic-ghost/', self.GHOST, '1')] + self.ALSO[1:])
        self.assertEqual(self.dead(home.also_items(self.site)), [])
        # A stale map that names only trips that are gone, while a newer report is filed under the region: the region
        # has a page of its own (it lists by the content) and still no panel on the Map page (that goes by the map's
        # entry). The row names it, with its count, and links to that page, never to the panel
        self.use(dict(self.MAPPED, **{self.GHOST: ['ghost-b']}))
        self.assertEqual(core._REGION_PAGES.get(self.GHOST), 'synthetic-ghost')
        self.assertNotIn('region-synthetic-ghost', self.map_ids())
        self.assertNotIn(self.GHOST, [name for name, _slug, _ts in core.region_groups(self.site)])
        self.assertEqual(self.also(home.also_items(self.site)),
                         [('regions/synthetic-coast/', 'Synthetic Coast', '1'), ('regions/synthetic-ghost/', self.GHOST, '1')] + self.ALSO[1:])
        self.assertEqual(self.dead(home.also_items(self.site)), [])
        self.assertNotIn('map/#region-synthetic-ghost', home.page(self.site).html)
        self.assertEqual(self.dead(legacy_also_items(self.site)), ['map/#region-synthetic-ghost'])

    def test_a_mapped_region_of_active_goals_only_keeps_its_item(self):
        # Synthetic Plans: a region map and one planned route. The Map page gives it a panel, so the link lands; it has
        # no report, so no page of its own and no count
        self.ghost()
        items = home.also_items(self.site)
        self.assertIn('<li><a href="map/#region-synthetic-plans"><span class="hom-also-w">Synthetic Plans</span></a></li>', items)
        self.assertIn(('map/#region-synthetic-plans', 'Synthetic Plans', None), self.also(items))
        self.assertNotIn('Synthetic Plans', core._REGION_PAGES)
        group = {name: ts for name, _slug, ts in core.region_groups(self.site)}['Synthetic Plans']
        self.assertEqual([(t['slug'], t['kind']) for t in group], [('plans-goal', 'planned')])
        self.assertIn('region-synthetic-plans', self.map_ids())
        # as the build names the goals that are still to do (site['active_goals']): the same while the goal is one of them
        self.site['active_goals'] = [self.site['by_slug']['plans-goal'], self.site['by_slug']['tahoe-plan']]
        self.assertEqual(self.also(home.also_items(self.site)), self.ALSO)
        # once it is done or shelved the Map page lists nothing there, and the row follows
        self.site['active_goals'] = [self.site['by_slug']['tahoe-plan']]
        self.assertNotIn('region-synthetic-plans', self.map_ids())
        self.assertEqual(self.also(home.also_items(self.site)), [self.ALSO[0]] + self.ALSO[2:])
        self.assertEqual(self.dead(home.also_items(self.site)), [])
        self.assertEqual(self.dead(legacy_also_items(self.site)), ['map/#region-synthetic-ghost', 'map/#region-synthetic-plans'])

    def test_the_other_items_keep_their_order_and_their_counts(self):
        # two more mapped regions with reports, so that the row has an order to keep: most reports first, then A to Z,
        # the regions without a report last; then the regions without a map, then the journal
        mk = helpers.make_trip
        for slug, day in (('bay-a', '2024-06-01'), ('bay-b', '2024-06-02'), ('bay-c', '2024-06-03')):
            mk(self.tmp, slug, title='Synthetic ' + slug, activity='mtb', date=day, region='Synthetic Bay', track=True)
        mk(self.tmp, 'alps-a', title='Synthetic Alps A', activity='ski', date='2024-01-05', region='Synthetic Alps', track=True)
        mapped = dict(self.MAPPED, **{'Synthetic Bay': ['bay-a', 'bay-b', 'bay-c'], 'Synthetic Alps': ['alps-a']})
        self.use(mapped)
        want = [('regions/synthetic-bay/', 'Synthetic Bay', '3'), ('regions/synthetic-alps/', 'Synthetic Alps', '1'),
                ('regions/synthetic-coast/', 'Synthetic Coast', '1'), ('map/#region-synthetic-plans', 'Synthetic Plans', None),
                ('map/#other-places', '1 more region', None), ('trips/journal-series/', 'Long Trail 2024', 'SERIES')]
        without = home.also_items(self.site)
        self.assertEqual(self.also(without), want)
        # the same site with the maps of two regions whose reports are gone (both sort among the regions without a report)
        helpers.make_trip(self.tmp, 'ghost-a', title='Synthetic Ghost A', activity='hike', date='2023-05-05', region=self.GHOST, track=True, draft=True)
        self.use(dict(mapped, **{self.GHOST: ['ghost-a', 'ghost-b'], 'Synthetic Aa': ['aa-gone']}))
        items = home.also_items(self.site)
        self.assertEqual(items, without)                                 # to the byte: every other item where it was, as it was
        self.assertEqual(self.also(items), want)
        old = legacy_also_items(self.site)
        self.assertEqual([w for _h, w, _c in self.also(old)],
                         ['Synthetic Bay', 'Synthetic Alps', 'Synthetic Coast', 'Synthetic Aa', self.GHOST, 'Synthetic Plans', '1 more region', 'Long Trail 2024'])
        kept = [x for x in old if 'synthetic-ghost' not in x and 'synthetic-aa' not in x]
        self.assertEqual(len(kept), len(old) - 2)
        self.assertEqual(items, [re.sub(r'href="map/#region-synthetic-(bay|alps|coast)"', r'href="regions/synthetic-\1/"', x) for x in kept])
        self.assertEqual(self.dead(items), [])
        self.assertEqual(self.dead(old), ['map/#region-synthetic-aa', 'map/#region-synthetic-ghost'])

    def test_the_row_asks_the_map_pages_own_grouping(self):
        # home.also_items goes by core.region_groups(site) under core's site meta, the grouping archive.regions hands the
        # Map page's panels: whatever that says has a panel has an item. Of the rest, only a region with a page of its
        # own has one (Synthetic Coast here), linked to that page; a region with neither (Synthetic Plans, whose goal
        # the stand-in grouping does not list) has none
        self.ghost()
        asked = []

        def groups(site, meta=None):
            asked.append((site, meta))
            return [(self.GHOST, 'synthetic-ghost', []), ('Eastern Sierra', 'eastern-sierra', [])]

        with mock.patch.object(core, 'region_groups', groups):
            got = self.also(home.also_items(self.site))
        self.assertEqual(asked, [(self.site, None)])                     # once, and with core's own meta (the one `mapped` is read from)
        # the region with a page and the ghost (a home region is never in the row), then what does not depend on a panel
        self.assertEqual(got, [self.ALSO[0], ('map/#region-synthetic-ghost', self.GHOST, None)] + self.ALSO[2:])
        self.assertEqual({name for name, _slug, _ts in core.region_groups(self.site)},
                         {name for name, _slug, _ts in archive.regions(self.site, archive.site_meta())})

    # ------------------------------------------------------------ nothing else changes; nothing changes unregistered

    def test_with_no_site_registered_both_functions_are_byte_for_byte_the_old_ones(self):
        core._REGION_PAGES.clear()
        self.assertEqual(home.also_items(self.site), legacy_also_items(self.site))
        self.assertEqual(home.where(self.site), legacy_where(self.site))
        self.assertNotIn('regions/', home.where(self.site))
        self.assertIn('<h3 class="hom-reg-n">Eastern Sierra</h3>', home.where(self.site))
        self.assertEqual([h for h, _w, _c in self.also(home.also_items(self.site))],
                         ['map/#region-synthetic-coast', 'map/#region-synthetic-plans', 'map/#other-places', 'trips/journal-series/'])

    def test_registered_without_a_site_meta_both_functions_are_the_old_ones_too(self):
        # REVISED in round 2: helpers.make_site registers the site and hands over no meta. The region maps are still in
        # core's own copy of the meta (home.where draws them from it), and no region has a page for all that
        self.assertEqual(sorted(core._REGION_PAGES), ['Eastern Sierra', 'Synthetic Coast'])
        with_pages = home.where(self.site)
        site = helpers.make_site(self.trips)
        self.assertEqual(core._REGION_PAGES, {})
        self.assertEqual(sorted(core.site_meta()['regions']), sorted(self.MAPPED))
        self.assertEqual(home.also_items(site), legacy_also_items(site))
        self.assertEqual(home.where(site), legacy_where(site))
        self.assertNotIn('regions/', home.where(site))
        self.assertEqual(len(self.blocks(home.where(site))), 2)                      # both region maps are drawn as before
        self.assertNotIn('regions/', home.page(site).html)
        # handed the meta, the same site has its two links again
        core.register_site(site, self.meta)
        self.assertEqual(home.where(site), with_pages)
        self.assertEqual(with_pages.count('regions/'), 2)

    def test_a_site_without_region_pages_changes_nothing_either(self):
        # region maps for regions without a published report: registered, and no region has a page
        self.use({'Lake Tahoe': ['tahoe-plan'], 'Synthetic Plans': ['plans-goal']})
        self.assertEqual(core._REGION_PAGES, {})
        self.assertEqual(home.where(self.site), legacy_where(self.site))
        self.assertEqual(home.also_items(self.site), legacy_also_items(self.site))
        self.assertEqual(len(self.blocks(home.where(self.site))), 1)

    def test_the_section_is_the_old_one_with_the_two_links(self):
        old = legacy_where(self.site)
        new = home.where(self.site)
        self.assertEqual(old.count('<h3 class="hom-reg-n">Eastern Sierra</h3>'), 1)
        want = (old.replace('<h3 class="hom-reg-n">Eastern Sierra</h3>', '<h3 class="hom-reg-n"><a href="regions/eastern-sierra/">Eastern Sierra</a></h3>')
                .replace('href="map/#region-synthetic-coast"', 'href="regions/synthetic-coast/"'))
        self.assertEqual(new, want)
        self.assertEqual(new.count('regions/'), 2)

    def test_the_whole_page_differs_only_in_those_two_links(self):
        with_pages = home.page(self.site).html
        core._REGION_PAGES.clear()
        without = home.page(self.site).html
        self.assertNotIn('regions/', without)
        self.assertEqual(with_pages.count('regions/'), 2)
        self.assertEqual(with_pages.replace('<h3 class="hom-reg-n"><a href="regions/eastern-sierra/">Eastern Sierra</a></h3>',
                                            '<h3 class="hom-reg-n">Eastern Sierra</h3>')
                         .replace('href="regions/synthetic-coast/"', 'href="map/#region-synthetic-coast"'), without)
        # one h1 and no heading inside a link's way: the h3 keeps its class and level
        self.assertEqual(len(Doc(with_pages).find_all('h3', cls='hom-reg-n')), 2)


# ---------------------------------------------------------------- review gate, fix A: the old address #latest-h

OLD_ID = 'latest-h'              # the id of the 'Latest reports' list on the home page that is public today
SECTION = '<section class="wrap sec hom-recent" id="latest-h" aria-labelledby="recent-h">'


def holders(doc, id_):
    """Every element of a parsed page, or inside an element of one, that carries this id."""
    return [n for n in getattr(doc, 'root', doc).walk() if n['id'] == id_]


class LatestAnchorTests(HomeFixture):
    """home.recent(site) and home.page(site): where the old id is, how often, and when it is not there at all."""

    def page(self, featured_slugs, site=None):
        site = site or self.site
        site['featured'] = [site['by_slug'][s] for s in featured_slugs]
        core.register_site(site)
        p = home.page(site)
        return p, Doc(p.html)

    def test_the_recent_section_carries_the_old_id_beside_its_label(self):
        self.site['featured'] = []
        html_ = home.recent(self.site)
        self.assertTrue(html_.startswith(SECTION), html_[:120])
        (sec,) = Doc(html_).root.elements()                      # the section is the whole of what recent() returns
        self.assertEqual((sec.tag, sec['id'], sec['aria-labelledby'], sec.classes), ('section', OLD_ID, 'recent-h', ['wrap', 'sec', 'hom-recent']))
        # its label is still its own heading, under the id it had
        (h2,) = holders(sec, 'recent-h')
        self.assertEqual((h2.tag, h2.text()), ('h2', 'Recent outings'))
        # and it is the element that holds the newest reports: an address to it lands on them
        cards = sec.find('ul', cls='hom-rcards').find_all('li', cls='tcard')
        self.assertEqual([c['data-slug'] for c in cards], self.published[:6])
        self.assertEqual(holders(sec, OLD_ID), [])               # nothing inside it has the id as well
        self.assertEqual(html_.count(OLD_ID), 1)

    def test_the_id_is_on_the_page_once(self):
        for featured in ([], ['ski-report'], ['ski-report', 'journal-series', 'loop-hike']):
            with self.subTest(featured=featured):
                p, doc = self.page(featured)
                (sec,) = holders(doc, OLD_ID)
                self.assertEqual((sec.tag, sec['aria-labelledby'], sec.classes), ('section', 'recent-h', ['wrap', 'sec', 'hom-recent']))
                self.assertEqual(p.html.count('id="%s"' % OLD_ID), 1)
                self.assertEqual(p.html.count(SECTION), 1)
                self.assertEqual(len(holders(doc, 'recent-h')), 1)
                # it is in <main>, after the features and before the sections that follow
                main = doc.by_id('main')
                self.assertIs(sec.parent, main)
                order = [n['aria-labelledby'] or n['aria-label'] for n in main.elements() if n.tag == 'section']
                self.assertEqual(order, ['Introduction'] + (['feat-h'] if featured else []) + ['recent-h', 'act-h'])
                # and the page uses no id twice
                ids = [n['id'] for n in doc.root.walk() if n['id']]
                self.assertEqual(sorted(i for i in set(ids) if ids.count(i) > 1), [])

    def test_no_second_element_has_the_id_and_nothing_else_is_named_after_it(self):
        # the old page had the id on the list's heading and named it from two more places (aria-labelledby on the
        # section and on the list); here it is the section's id and nothing refers to it
        p, doc = self.page(['ski-report'])
        self.assertEqual(p.html.count(OLD_ID), 1)                # the one attribute: no other id, label reference or link
        for attr in ('aria-labelledby', 'aria-describedby', 'aria-controls', 'for', 'href'):
            self.assertEqual([n for n in doc.root.walk() if OLD_ID in (n[attr] or '')], [], attr)
        self.assertEqual([n.tag for n in doc.find_all('h2') if n['id'] == OLD_ID], [])
        # the heading keeps recent-h, which the section names: the section's accessible name is unchanged
        self.assertEqual(doc.by_id(OLD_ID)['aria-labelledby'], 'recent-h')
        self.assertEqual(doc.by_id('recent-h').text(), 'Recent outings')

    def test_without_a_recent_row_the_section_and_the_id_are_absent(self):
        # every published report is featured: nothing is left for the shelf, so there is no section to carry the id
        site2 = helpers.make_site([self.site['by_slug'][s] for s in ('ski-report', 'loop-hike', 'planned-route')])
        site2['featured'] = list(site2['published'])
        self.assertEqual(home.recent_trips(site2), [])
        self.assertEqual(home.recent(site2), '')
        p, doc = self.page(['ski-report', 'loop-hike'], site2)
        self.assertNotIn(OLD_ID, p.html)
        self.assertNotIn('recent-h', p.html)
        self.assertNotIn('hom-recent', p.html)
        self.assertEqual(holders(doc, OLD_ID), [])
        self.assertIsNotNone(doc.by_id('feat-h'))                 # the page is otherwise there
        # nor on a site with nothing published at all
        site3 = helpers.make_site([self.site['by_slug']['planned-route']])
        p, doc = self.page([], site3)
        self.assertEqual(home.recent(site3), '')
        self.assertNotIn(OLD_ID, p.html)
        # one report that is not featured is enough for the section, and the id, to be there
        p, doc = self.page(['ski-report'], site2)
        self.assertEqual([c['data-slug'] for c in doc.by_id(OLD_ID).find_all('li', cls='tcard')], ['loop-hike'])
        self.assertEqual(p.html.count('id="%s"' % OLD_ID), 1)

    def test_a_link_to_the_old_address_resolves_on_this_page_and_not_without_the_id(self):
        # the site checks on the page as generated: a same-page link, a link from another page and the full address all
        # land; with the id taken off again (the page of commit dbce17b) each of them is reported
        p, _doc = self.page(['ski-report'])
        here = '<a href="#latest-h">Latest reports</a>'
        there = '<p><a href="../#latest-h">Latest reports</a> <a href="%s#latest-h">The same, in full</a></p>' % core.SITE_URL
        linked = p.html.replace('</main>', here + '</main>', 1)
        self.assertNotEqual(linked, p.html)
        out = sitecheck.of({'index.html': linked, 'other/index.html': there}, site_url=core.SITE_URL)
        self.assertEqual(sitecheck.anchors(out, 'index.html'), [])
        self.assertEqual(sitecheck.links(out, 'other/index.html'), [])
        self.assertEqual(sitecheck.duplicate_ids(out, 'index.html'), [])
        without = sitecheck.of({'index.html': linked.replace(' id="latest-h"', '', 1), 'other/index.html': there}, site_url=core.SITE_URL)
        self.assertEqual(sitecheck.anchors(without, 'index.html'), ['BROKEN ANCHOR index.html -> #latest-h'])
        self.assertEqual(sitecheck.links(without, 'other/index.html'),
                         ['BROKEN ANCHOR other/index.html -> ../#latest-h', 'BROKEN ANCHOR other/index.html -> %s#latest-h' % core.SITE_URL])
        # and a second element with the id would be reported as well
        twice = sitecheck.of({'index.html': p.html.replace('id="recent-h"', 'id="latest-h"', 1)}, site_url=core.SITE_URL)
        self.assertEqual(sitecheck.duplicate_ids(twice, 'index.html'), ['DUPLICATE IDS index.html: latest-h'])


class LatestAnchorBuiltTests(unittest.TestCase):
    """The same on a built site: tools/build.py on the synthetic repository of tests/test_build_site.py (its write_site
    and run_build, in a temp folder of this class), then the checks `build.py --check` runs."""

    @classmethod
    def setUpClass(cls):
        import test_build_site as fixture        # the module, for its fixture: none of its tests is loaded from here
        cls.tmp = tempfile.TemporaryDirectory()
        fixture.write_site(cls.tmp.name)
        cls.out, cls.pages = fixture.run_build(cls.tmp.name)
        cls.trips_dir = os.path.join(cls.tmp.name, 'content', 'trips')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, rel):
        with open(os.path.join(self.out, *rel.split('/')), encoding='utf-8') as fh:
            return fh.read()

    def test_the_built_home_page_has_the_section_with_the_id_once(self):
        html_ = self.read('index.html')
        self.assertEqual((html_.count(SECTION), html_.count('id="latest-h"'), html_.count(OLD_ID)), (1, 1, 1))
        doc = Doc(html_)
        sec = doc.by_id(OLD_ID)
        self.assertEqual((sec.tag, sec['aria-labelledby'], doc.by_id('recent-h').text()), ('section', 'recent-h', 'Recent outings'))
        self.assertGreater(len(sec.find_all('li', cls='tcard')), 0)
        self.assertIn(OLD_ID, sitecheck.read(self.out).ids('index.html'))
        # no other page of the site has the id: the address is the home page's
        out = sitecheck.read(self.out)
        self.assertEqual([page for page in out.pages if OLD_ID in out.ids(page)], ['index.html'])

    def test_the_site_checks_find_no_id_twice(self):
        out = sitecheck.read(self.out)
        self.assertIn('index.html', out.pages)
        self.assertEqual(sitecheck.duplicate_ids(out), [])
        self.assertEqual(sitecheck.duplicate_ids(out, 'index.html'), [])
        self.assertEqual(sitecheck.anchors(out, 'index.html'), [])
        self.assertEqual(sitecheck.check(self.out, self.trips_dir), [])            # and nothing else is wrong with the build

    def test_a_link_to_the_old_address_from_the_built_home_page_resolves(self):
        # the built pages, with a link to #latest-h put on the home page (the old page's 'Latest reports' button) and on
        # the Trips page: the link check finds both targets
        home_html, trips_html = self.read('index.html'), self.read('trips/index.html')
        linked = {'index.html': home_html.replace('</main>', '<a class="btn" href="#latest-h">Latest reports</a></main>', 1),
                  'trips/index.html': trips_html.replace('</main>', '<a href="../#latest-h">Latest reports</a></main>', 1)}
        self.assertNotEqual(linked['index.html'], home_html)
        self.assertNotEqual(linked['trips/index.html'], trips_html)
        out = sitecheck.of(linked, site_url=core.SITE_URL)
        self.assertEqual(sitecheck.anchors(out, 'index.html'), [])
        self.assertEqual([ln for ln in sitecheck.links(out, 'trips/index.html') if 'latest-h' in ln], [])
        self.assertEqual(sitecheck.duplicate_ids(out, 'index.html'), [])
        # on the folder itself, with the link written into the built file and taken out again
        path = os.path.join(self.out, 'index.html')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(linked['index.html'])
        try:
            self.assertEqual(sitecheck.anchors(sitecheck.read(self.out), 'index.html'), [])
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(linked['index.html'].replace(' id="latest-h"', '', 1))
            self.assertEqual(sitecheck.anchors(sitecheck.read(self.out), 'index.html'), ['BROKEN ANCHOR index.html -> #latest-h'])
        finally:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(home_html)
        self.assertEqual(sitecheck.check(self.out, self.trips_dir), [])


if __name__ == '__main__':
    unittest.main()
