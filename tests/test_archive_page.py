"""Phase 4: the map page (sitegen.pages.archive.build -> map/): the anchors that other pages, old links and bookmarks
land on, and the page's share image (contract-phase4.md 4.1; plan section 16, 'URLs and anchors': map/#all-reports,
map/#other-places and one map/#region-<slug> per region).

A region has its anchor in one of two places. A region with a rendered region map (rendered/site/meta.json 'regions')
gets a panel under the tab row: <div class="arc-panel" id="region-<slug>">. Every other region a report is filed under
('all_regions') gets a short list in the 'Not on a region map' block: <div class="arc-oreg" id="region-<slug>"> inside
<div id="other-places">. The report table by year is <section id="all-reports">.

A synthetic site in a temp dir laid out like the repository: <tmp>/trips/<slug>/ and <tmp>/rendered/site/ with a
meta.json and one placeholder fragment per region map. core.ROOT, content.RENDERED and core's in-memory copy of the
site meta point at the temp dir while a test runs, so the real rendered/ and content/ are never read. Two regions have
a region map (the panel variant), two do not (the list variant; one name has an apostrophe), a journal sits on no
region map, and one tick-list goal is an active planned route. Every slug starts with syn-m-.
"""
import importlib
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, photo, LANDSCAPE, PORTRAIT  # noqa: E402

MAPPED = ['Synthetic Range', 'Synthetic Coast']            # a region map each: the panel variant
LISTED = ['Synthetic Desert', "Synthetic O'Plateau"]       # no region map: the list variant
SLUG = {'Synthetic Range': 'synthetic-range', 'Synthetic Coast': 'synthetic-coast', 'Synthetic Desert': 'synthetic-desert',
        "Synthetic O'Plateau": 'synthetic-oplateau'}
COVER_ALT = 'Synthetic "shoreline" & a <synthetic> sky'   # characters an attribute must escape, to be read back verbatim
WRITEUP = 'Synthetic write-up for a test.'


def load_module(tc, name):
    try:
        return importlib.import_module(name)
    except ImportError as ex:
        tc.fail('%s is not importable: %s' % (name.replace('.', '/') + '.py', ex))


def ancestors(node):
    out = []
    p = node.parent
    while p is not None:
        out.append(p)
        p = p.parent
    return out


class MapPageFixture(unittest.TestCase):

    def setUp(self):
        self.archive = load_module(self, 'sitegen.pages.archive')
        self.build_mod = load_module(self, 'build')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.trips_dir = os.path.join(self.tmp, 'trips')
        self.site_dir = os.path.join(self.tmp, 'rendered', 'site')
        os.makedirs(self.trips_dir)
        os.makedirs(self.site_dir)
        # the page modules look for rendered/site/ under core.ROOT and each trip's renders under content.RENDERED;
        # core._SITE_SHARE is swapped for the test so the share image registered here is gone afterwards
        for target, name, value in ((core, 'ROOT', self.tmp), (content, 'RENDERED', os.path.join(self.tmp, 'rendered')),
                                    (core, '_SITE_SHARE', [None])):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        mk = helpers.make_trip
        # Synthetic Range: three reports (one of them a two-day tour); Synthetic Coast: two, one with a photo
        mk(self.trips_dir, 'syn-m-range-a', title='Synthetic Range A', activity='ski', date='2026-03-01', region='Synthetic Range', track=True)
        mk(self.trips_dir, 'syn-m-range-b', title='Synthetic Range B', activity='hike', date='2025-08-02', region='Synthetic Range', track=True,
           body=WRITEUP)
        mk(self.trips_dir, 'syn-m-range-tour', title='Synthetic Range Tour', activity='ski', kind='multi-day', date='2025-04-01',
           end_date='2025-04-02', region='Synthetic Range',
           days=[{'title': 'Synthetic Day One', 'date': '2025-04-01'}, {'title': 'Synthetic Day Two', 'date': '2025-04-02'}])
        mk(self.trips_dir, 'syn-m-coast-a', title='Synthetic Coast A', activity='mtb', date='2026-01-10', region='Synthetic Coast', track=True,
           photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic portrait'), photo('photos/02.webp', LANDSCAPE, alt=COVER_ALT, sm=True)])
        mk(self.trips_dir, 'syn-m-coast-b', title='Synthetic Coast B', activity='hike', date='2024-06-05', region='Synthetic Coast', track=True)
        # no region map: one report each, and an active tick-list goal (a legacy planned route) in the desert
        mk(self.trips_dir, 'syn-m-desert-a', title='Synthetic Desert A', activity='climb', date='2024-10-12', region='Synthetic Desert', track=True)
        mk(self.trips_dir, 'syn-m-plateau-a', title='Synthetic Plateau A', activity='hike', date='2023-09-09', region="Synthetic O'Plateau",
           track=True, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic plateau')])
        mk(self.trips_dir, 'syn-m-desert-goal', title='Synthetic Desert Goal', activity='hike', kind='planned', region='Synthetic Desert')
        # a journal: on no region map, in a region the map page has no anchor for (as the PCT)
        helpers.make_series(self.trips_dir, slug='syn-m-journal', title='Synthetic Journal', region='Synthetic Trail')
        self.use(MAPPED, MAPPED + LISTED, featured=('syn-m-coast-a',))

    # ------------------------------------------------------------ helpers

    def write_meta(self, mapped, all_regions):
        """rendered/site/meta.json in the temp dir: a desktop and a phone region map for each name in `mapped`, each with
        a placeholder fragment, as tools/render.py leaves them; `all_regions` is every region with an anchor."""
        maps = {}
        for name in mapped:
            for size, (w, h) in (('desktop', (1077, 930)), ('phone', (585, 720))):
                key = 'region-%s-%s' % (SLUG[name], size)
                maps[key] = {'w': w, 'h': h, 'png': key + '.webp', 'base': key + '.base.svg'}
                with open(os.path.join(self.site_dir, key + '.svg.html'), 'w', encoding='utf-8') as fh:
                    fh.write('<svg width="%d" height="%d" viewBox="0 0 %d %d"></svg>' % (w, h, w, h))
        meta = {'hash': '', 'maps': maps, 'regions': list(mapped), 'all_regions': list(all_regions)}
        with open(os.path.join(self.site_dir, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(meta, fh)
        return meta

    def use(self, mapped, all_regions, featured=(), only=None):
        """Write the site meta, load the temp trips (all of them, or the slugs in `only`) into a site as build.py does,
        name the featured trips, register the site and build the map page."""
        self.meta = self.write_meta(mapped, all_regions)
        patcher = mock.patch.object(core, '_SITE_META', [self.meta])
        patcher.start()
        self.addCleanup(patcher.stop)
        trips = [t for t in helpers.load_dir(self.trips_dir) if only is None or t['slug'] in only]
        self.site = self.build_mod.site_of(helpers.newest_first(trips))
        self.by = self.site['by_slug']
        self.site['featured'] = [self.by[s] for s in featured]
        core.register_site(self.site)
        self.pages = self.archive.build(self.site)
        self.page = self.pages[0]
        self.doc = Doc(self.page.html)
        self.main = self.doc.by_id('main')

    def with_id(self, id_):
        return [n for n in self.doc.root.walk() if n['id'] == id_]

    def one(self, id_):
        """The one element with this id; fails when the page has none or several."""
        hits = self.with_id(id_)
        self.assertEqual(len(hits), 1, 'the map page has %d elements with id="%s"' % (len(hits), id_))
        self.assertEqual(self.page.html.count('id="%s"' % id_), 1)
        return hits[0]

    def share_meta(self):
        out = {}
        for m in self.doc.find('head').find_all('meta'):
            key = m['property'] or m['name'] or ''
            if key.startswith(('og:image', 'twitter:')):
                self.assertNotIn(key, out, 'two %s tags' % key)
                out[key] = m['content']
        return out


# ---------------------------------------------------------------- the anchors

class AnchorTests(MapPageFixture):

    def test_build_returns_the_map_page(self):
        self.assertEqual([p.url for p in self.pages], ['map/'])
        self.assertEqual(self.page.title, 'Map & archive')
        self.assertTrue(self.page.index)
        self.assertEqual(self.doc.find('link', attrs={'rel': 'canonical'})['href'], core.SITE_URL + 'map/')
        self.assertEqual([h.text() for h in self.doc.find_all('h1')], ['Map & archive'])
        self.assertNotIn('<!-- missing', self.page.html)        # every fragment the fixture names was found in the temp dir

    def test_the_fixture_has_both_variants(self):
        # two regions with a region map (panels), two without (lists), in the archive module's own terms
        regs = self.archive.regions(self.site, self.meta)
        self.assertEqual([name for name, _slug, _ts in regs], MAPPED)
        self.assertEqual([slug for _name, slug, _ts in regs], [SLUG[r] for r in MAPPED])
        self.assertEqual([content.slugify(r) for r in MAPPED + LISTED], [SLUG[r] for r in MAPPED + LISTED])
        self.assertEqual(len(self.main.find_all('div', cls='arc-panel')), 2)
        self.assertEqual(len(self.main.find_all('div', cls='arc-oreg')), 2)

    def test_all_reports_is_on_the_page_exactly_once(self):
        # plan 16: map/#all-reports. Nothing on the site links to it any more (the home page's links moved to trips/),
        # so only this test notices if it goes
        sec = self.one('all-reports')
        self.assertEqual(sec.tag, 'section')
        self.assertIn('arc-all', sec.classes)
        self.assertIs(sec.parent, self.main)
        self.assertEqual(sec['aria-labelledby'], 'all-reports-h')
        self.assertEqual(self.one('all-reports-h').text(), 'All reports')
        self.assertIn(self.one('all-reports-h'), list(sec.walk()))
        # it is the table of every report by year: each published report has a row in it
        hrefs = [a['href'] for a in sec.find_all('a')]
        for t in self.site['published']:
            self.assertIn('../' + t['url'], hrefs, t['slug'])

    def test_other_places_is_on_the_page_exactly_once(self):
        # plan 16: map/#other-places, the 'Not on a region map' block (home's 'N more regions' item links here)
        block = self.one('other-places')
        self.assertEqual((block.tag, block.classes), ('div', ['arc-other']))
        self.assertEqual(self.one('arc-other-h').text(), 'Not on a region map')
        self.assertIn(self.one('arc-other-h'), list(block.walk()))
        self.assertIn('../trips/syn-m-journal/', [a['href'] for a in block.find_all('a')])    # the journal's card is here

    def test_a_region_with_a_region_map_has_its_anchor_on_its_panel(self):
        # the panel variant: <div class="arc-panel" id="region-<slug>">, once, under the tab row
        other = self.one('other-places')
        for name in MAPPED:
            with self.subTest(region=name):
                panel = self.one('region-' + SLUG[name])
                self.assertEqual((panel.tag, panel.classes), ('div', ['arc-panel']))
                self.assertEqual(self.one('arc-ph-' + SLUG[name]).text(), name)
                self.assertIn(self.one('arc-ph-' + SLUG[name]), list(panel.walk()))
                self.assertNotIn(other, ancestors(panel))
                self.assertIn('arc-map', panel.parent.classes)
                # the region's reports are listed in it, and its map is the temp dir's
                rows = [li['data-key'] for li in panel.find_all('li', cls='arc-row')]
                self.assertEqual(sorted(rows), sorted(t['slug'] for t in self.site['trips'] if t['region'] == name))
                self.assertIsNotNone(panel.by_id('arc-map-' + SLUG[name]))

    def test_a_region_without_a_region_map_has_its_anchor_on_its_list(self):
        # the list variant: <div class="arc-oreg" id="region-<slug>">, once, inside #other-places
        other = self.one('other-places')
        for name in LISTED:
            with self.subTest(region=name):
                group = self.one('region-' + SLUG[name])
                self.assertEqual((group.tag, group.classes), ('div', ['arc-oreg']))
                self.assertIn(other, ancestors(group))
                self.assertEqual(self.one('arc-on-' + SLUG[name]).text(), name)
                self.assertIn(self.one('arc-on-' + SLUG[name]), list(group.walk()))
                rows = [li['data-key'] for li in group.find_all('li', cls='arc-row')]
                self.assertEqual(sorted(rows), sorted(t['slug'] for t in self.site['trips'] if t['region'] == name))
        self.assertEqual(SLUG["Synthetic O'Plateau"], 'synthetic-oplateau')       # an apostrophe leaves no hyphen in the id

    def test_every_region_has_exactly_one_anchor_and_no_other_region_id_exists(self):
        ids = sorted(n['id'] for n in self.doc.root.walk() if (n['id'] or '').startswith('region-'))
        self.assertEqual(ids, sorted('region-' + SLUG[r] for r in MAPPED + LISTED))
        for name in MAPPED + LISTED:
            self.assertEqual(self.page.html.count('id="region-%s"' % SLUG[name]), 1, name)

    def test_region_links_from_other_pages_land_on_those_anchors(self):
        # core.region_map_href is what breadcrumbs, the trips browse block and the home page use: map/#region-<slug>
        for name in MAPPED + LISTED:
            with self.subTest(region=name):
                href = core.region_map_href('trips/syn-m-range-a/', name)
                self.assertEqual(href, '../../map/#region-' + SLUG[name])
                self.one(href.split('#', 1)[1])
        self.assertIsNone(core.region_map_href('', 'Synthetic Trail'))       # the journal's region has no anchor, and no link

    def test_each_tab_controls_its_panel(self):
        tabs = self.main.find_all('button', attrs={'role': 'tab'})
        self.assertEqual([b['aria-controls'] for b in tabs], ['region-' + SLUG[r] for r in MAPPED])
        self.assertEqual([b['id'] for b in tabs], ['arc-tab-' + SLUG[r] for r in MAPPED])
        for b in tabs:
            self.assertIn('arc-panel', self.one(b['aria-controls']).classes)

    def test_ids_are_unique_and_every_fragment_link_lands(self):
        ids = [n['id'] for n in self.doc.root.walk() if n['id']]
        self.assertEqual(sorted(ids), sorted(set(ids)))
        frags = [a['href'][1:] for a in self.doc.find_all('a') if (a['href'] or '').startswith('#')]
        self.assertIn('yr-2026', frags)                                      # the year index is among them
        for f in frags:
            self.assertIn(f, ids, 'a link to #%s lands nowhere' % f)
        for attr in ('aria-labelledby', 'aria-controls'):
            for n in self.doc.root.walk():
                for ref in (n[attr] or '').split():
                    self.assertIn(ref, ids, '%s="%s" names no element' % (attr, n[attr]))

    def test_year_groups_keep_their_anchors(self):
        # the year index's targets: yr-<year>, newest first, then yr-planned for the active goal
        sec = self.one('all-reports')
        self.assertEqual([d['data-group'] for d in sec.find_all('div', cls='arc-yr')], ['yr-2026', 'yr-2025', 'yr-2024', 'yr-2023', 'yr-planned'])
        for gid in ('yr-2026', 'yr-2025', 'yr-2024', 'yr-2023', 'yr-planned'):
            self.assertEqual(self.one(gid).tag, 'h3')
        nav = sec.find('nav', cls='arc-years')
        self.assertEqual([a['href'] for a in nav.find_all('a')], ['#yr-2026', '#yr-2025', '#yr-2024', '#yr-2023', '#yr-planned'])

    def test_with_no_region_map_every_region_is_a_list_and_the_three_anchors_stay(self):
        # the list variant alone (no region has three reports yet, or nothing is rendered): no tab row, no panel; every
        # region's anchor is in #other-places, and #all-reports and #other-places are still there once
        self.use([], MAPPED + LISTED)
        self.assertEqual(self.main.find_all('div', cls='arc-panel'), [])
        self.assertEqual(self.main.find_all(attrs={'role': 'tab'}), [])
        other = self.one('other-places')
        self.one('all-reports')
        for name in MAPPED + LISTED:
            with self.subTest(region=name):
                group = self.one('region-' + SLUG[name])
                self.assertEqual(group.classes, ['arc-oreg'])
                self.assertIn(other, ancestors(group))
        ids = sorted(n['id'] for n in self.doc.root.walk() if (n['id'] or '').startswith('region-'))
        self.assertEqual(ids, sorted('region-' + SLUG[r] for r in MAPPED + LISTED))

    def test_with_every_region_mapped_and_no_journal_there_is_nothing_for_other_places(self):
        # the panel variant alone: #other-places exists when something is not on a region map, and only then; nothing
        # on the page (or on the home page: home.also_items) links to it when it is absent
        only = [s for s in self.by if self.by[s]['region'] in MAPPED]
        self.use(MAPPED, MAPPED, only=only)
        self.assertEqual(len(self.site['trips']), 5)
        self.assertEqual(self.with_id('other-places'), [])
        self.assertNotIn('other-places', self.page.html)
        self.one('all-reports')
        for name in MAPPED:
            self.assertEqual(self.one('region-' + SLUG[name]).classes, ['arc-panel'])
        home = load_module(self, 'sitegen.pages.home')
        self.assertNotIn('other-places', ''.join(home.also_items(self.site)))
        # ... and with one region left unmapped again, the home page's link and its target come back together
        self.use(MAPPED, MAPPED + LISTED)
        self.assertIn('href="map/#other-places"', ''.join(home.also_items(self.site)))
        self.one('other-places')

    def test_a_page_with_no_trips_still_builds(self):
        self.use([], [], only=())
        self.assertEqual([p.url for p in self.pages], ['map/'])
        self.one('all-reports')
        self.assertEqual(self.with_id('other-places'), [])


# ---------------------------------------------------------------- the share image

class ShareImageTests(MapPageFixture):

    def test_the_share_image_is_the_site_share(self):
        # contract-phase4.md 4.1: the map page passes image=core.site_share(), the share photo of the first featured
        # trip (the home page's lead): its cover, with the size and alt text recorded for it
        lead = self.by['syn-m-coast-a']
        self.assertTrue(hasattr(core, 'site_share'), 'core.site_share is missing (contract-phase4.md 4.1)')
        share = core.site_share()
        self.assertIsNotNone(share)
        self.assertEqual(share, core.share_photo(lead))
        self.assertEqual(share, {'path': 'trips/syn-m-coast-a/photos/02.webp', 'w': 1600, 'h': 1200, 'alt': COVER_ALT})
        self.assertEqual(self.share_meta(), {'og:image': core.SITE_URL + share['path'], 'og:image:type': 'image/webp',
                                             'og:image:width': '1600', 'og:image:height': '1200', 'og:image:alt': COVER_ALT,
                                             'twitter:card': 'summary_large_image', 'twitter:image:alt': COVER_ALT})
        self.assertIn(core._share_tags(share), self.page.html.split('</head>', 1)[0])
        self.assertEqual(len(self.doc.find('head').find_all('meta', attrs={'property': 'og:image'})), 1)
        self.assertTrue(self.share_meta()['og:image'].startswith('https://'))

    def test_it_follows_the_first_featured_trip(self):
        # the first of content/home.json's features, not the newest trip, the last feature or the first with a photo
        self.use(MAPPED, MAPPED + LISTED, featured=('syn-m-plateau-a', 'syn-m-coast-a'))
        self.assertEqual(core.site_share(), core.share_photo(self.by['syn-m-plateau-a']))
        self.assertEqual(self.share_meta()['og:image'], core.SITE_URL + 'trips/syn-m-plateau-a/photos/01.webp')
        self.assertEqual(self.share_meta()['og:image:alt'], 'Synthetic plateau')
        # a lead without a photo shares none: the second feature's photo is not borrowed
        self.use(MAPPED, MAPPED + LISTED, featured=('syn-m-range-a', 'syn-m-coast-a'))
        self.assertIsNone(self.by['syn-m-range-a']['cover'])
        self.assertIsNone(core.site_share())
        self.assertEqual(self.share_meta(), {'twitter:card': 'summary'})

    def test_no_featured_trip_no_share_image(self):
        self.use(MAPPED, MAPPED + LISTED, featured=())
        self.assertIsNone(core.site_share())
        self.assertEqual(self.share_meta(), {'twitter:card': 'summary'})
        self.assertNotIn('og:image', self.page.html)
        # a site dict without the key at all (the unit tests' sites) registers no share image either
        del self.site['featured']
        core.register_site(self.site)
        self.assertIsNone(core.site_share())
        self.assertNotIn('og:image', self.archive.build(self.site)[0].html)

    def test_the_image_is_the_only_thing_the_feature_changes(self):
        # the share tags are the page's whole difference between a site with a featured trip and one without
        with_ = self.page.html
        self.use(MAPPED, MAPPED + LISTED, featured=())
        without = self.page.html
        tags = core._share_tags(core.share_photo(self.by['syn-m-coast-a']))
        self.assertEqual(with_.count(tags), 1)
        self.assertEqual(with_.replace(tags, '<meta name="twitter:card" content="summary">'), without)


if __name__ == '__main__':
    unittest.main()
