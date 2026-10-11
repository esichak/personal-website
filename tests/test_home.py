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
"""
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
from sitegen.pages import home  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, PCT_PROSE, photo, LANDSCAPE, PORTRAIT  # noqa: E402

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
        self.assertEqual((source['media'], source['sizes'], source['srcset']),
                         ('(max-width: 559.98px)', '112px', '%s02.th.webp 427w, %s' % (base, two)))
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


if __name__ == '__main__':
    unittest.main()
