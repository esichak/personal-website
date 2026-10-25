"""Phase 12 on the map and region pages (docs/claude-code-website-prompt-2.md, Phase 12), on the synthetic region site of
tests/test_region_page.py (its RegionFixture: every slug starts with syn-r-, nothing under content/ or rendered/ is read):

  gap4-01  every row of a region's list carries id arc-row-<slug> (a journal part arc-row-<region>-<part>), once
  gap4-03  core.region_row_href: a trip's own row, on its region's page or on map/; the plain region link for a trip no
           list rows; 'See on the <Region> map' (core.see_on_map) only with a track
  gap4-04  series.region_parts: the journal's parts, each to its row on the region map's list
  ia-09    core.place_line links the region, keeping the place text
  ia-12    section.areas links region names, never one region's places
  maps-07  archive.inject_acts puts each marker's activity on it; the legend items carry theirs
  phone-04 a region panel's phone map carries the credit tag, the compact key row (keyrow--p) beside the legend (keyrow--d)
  qa-02    each panel's count line has an id and a live region beside it
  phone-03 every year list of 'All reports' has an id its fold button names
  qa-06    map/<region>/ for each region map: noindex, out of the sitemap, data-fs="region"; the phone map's 44 px button

The scripts are tested by tests/maplist_js_harness.js; the sticky parts by ShortViewportTests in tests/test_a11y_static.py."""
import contextlib
import importlib
import io
import re
import unittest
from unittest import mock

import helpers
from helpers import Doc
import test_region_page as rg

from sitegen import core

tearDownModule = helpers.no_region_pages_left


class Phase12Fixture(rg.RegionFixture):

    def archive_pages(self):
        with mock.patch.object(core, '_DROP_WARNED', set()), contextlib.redirect_stderr(io.StringIO()):
            return {p.url: p for p in self.archive.build(self.site)}

    def map_doc(self):
        return Doc(self.archive_pages()['map/'].html)


class RowIdTests(Phase12Fixture):

    def test_every_region_row_has_its_id_once_on_map_and_on_each_region_page(self):
        pages = [self.map_doc()] + [self.doc(name) for name in rg.PAGES]
        for doc in pages:
            rows = doc.find_all('li', cls='arc-row')
            self.assertTrue(rows)
            ids = [r['id'] for r in rows if r['id']]
            self.assertEqual(len(ids), len(set(ids)))
            for r in rows:
                if 'arc-row--journal' not in r.classes and r['id']:
                    self.assertEqual(r['id'], 'arc-row-' + r['data-key'])
        # on a region's own page every report row has it (the page lists by the region field)
        for name in rg.PAGES:
            for r in self.doc(name).find_all('li', cls='arc-row'):
                if 'arc-row--journal' not in r.classes:
                    self.assertEqual(r['id'], 'arc-row-' + r['data-key'], name)

    def test_a_journal_part_id_names_its_region(self):
        part = {'key': 'syn-r-journal:part-a'}
        self.assertEqual(self.archive.journal_part_id('synthetic-range', part), 'arc-row-synthetic-range-syn-r-journal-part-a')

    def test_a_row_carries_its_kind_for_the_cluster_count(self):
        kinds = {r['data-key']: r['data-kind'] for r in self.map_doc().find_all('li', cls='arc-row') if r['data-kind']}
        self.assertTrue(kinds)
        for slug, kind in kinds.items():
            self.assertEqual(kind, self.by[slug]['kind'])


class RowLinkTests(Phase12Fixture):

    def test_a_trip_of_a_region_with_a_page_lands_on_its_row_there(self):
        t = self.by['syn-r-story']
        self.assertEqual(core.region_row_href('trips/syn-r-story/', t), '../../regions/synthetic-range/#arc-row-syn-r-story')

    def test_a_trip_of_a_region_without_a_page_lands_on_its_row_on_map(self):
        others = [t for t in self.site['trips'] if t.get('region') in (rg.PLANS, rg.DESERT) and t['slug'] in core._LISTED[0]]
        self.assertTrue(others)
        for t in others:
            with self.subTest(t['slug']):
                self.assertEqual(core.region_row_href('', t), 'map/#arc-row-' + t['slug'])

    def test_every_row_link_lands_on_an_id_of_its_page(self):
        pages = dict((u, Doc(p.html)) for u, p in self.archive_pages().items())
        pages.update((self.here(n), self.doc(n)) for n in rg.PAGES)
        checked = 0
        for t in self.site['trips']:
            href = core.region_row_href('', t)
            if not href or '#' not in href:
                continue
            url, frag = href.split('#')
            ids = {n['id'] for n in pages[url].root.walk() if n['id']}
            self.assertIn(frag, ids, href)
            checked += 1
        self.assertGreater(checked, 10)

    def test_a_trip_no_list_rows_gets_the_plain_region_link_and_one_without_a_region_none(self):
        t = self.by['syn-r-story']
        with mock.patch.object(core, '_LISTED', [set()]):            # as for a completed or archived goal
            self.assertEqual(core.region_row_href('', t), 'regions/synthetic-range/')
        self.assertIsNone(core.region_row_href('', dict(t, region=None)))
        self.assertIsNone(core.region_row_href('', dict(t, region='Synthetic Nowhere')))

    def test_a_trip_of_a_mapped_region_with_no_panel_and_no_page_gets_the_plain_link(self):
        # the Plans map names only a trip that is gone (until the next render): map/ has no panel and so no row for the goal
        self.use(named={rg.PLANS: ['syn-r-gone']})
        t = self.by['syn-r-plan']
        self.assertNotIn('arc-row', core.region_row_href('', t))
        self.assertEqual(core.region_row_href('', t), core.region_link('', rg.PLANS))
        # a region without a map lists its trips under 'Not on a region map', with their ids: those keep their row link
        desert = self.by['syn-r-desert']
        self.assertEqual(core.region_row_href('', desert), 'map/#arc-row-syn-r-desert')

    def test_see_on_map_needs_a_track(self):
        t = self.by['syn-r-story']
        html_ = core.see_on_map('trips/syn-r-story/', t)
        a = Doc(html_).find('a')
        self.assertEqual((a.classes, a['href'], a.text()), (['alink', 'rep-seemap'], '../../regions/synthetic-range/#arc-row-syn-r-story',
                                                           'See on the Synthetic Range map'))
        self.assertEqual(core.see_on_map('trips/syn-r-story/', dict(t, track=None, days=[])), '')
        self.assertEqual(core.see_on_map('trips/syn-r-story/', dict(t, region=None)), '')


class PlaceAndAreaLinkTests(Phase12Fixture):

    def test_the_place_line_links_the_region_and_keeps_the_place_text(self):
        t = dict(self.by['syn-r-story'], place='Synthetic Basin')
        items = core.place_line(t, items=True, here='trips/syn-r-story/')
        html_ = core.meta_items(items)
        a = Doc(html_).find('a')
        self.assertEqual((a.classes, a['href'], a.text().replace('\u00a0', ' ')), (['mi-a'], '../../regions/synthetic-range/', 'SYNTHETIC RANGE'))
        self.assertIn('SYNTHETIC\u00a0BASIN', html_)
        self.assertNotIn('<a', core.meta_items(core.place_line(t, items=True)))                    # without here: text
        self.assertNotIn('<a', core.meta_items(core.place_line(dict(t, region=None), items=True, here='')))

    def test_section_areas_link_region_names_and_leave_one_regions_places(self):
        section = importlib.import_module('sitegen.pages.section')
        two = [self.by['syn-r-story'], self.by['syn-r-cove-a']]
        items = section.areas(two, 'hiking/')
        self.assertTrue(all(i.startswith('<a class="mi-a" href="../regions/') for i in items), items)
        one = [dict(self.by['syn-r-story'], place='Synthetic Crag A'), dict(self.by['syn-r-words'], place='Synthetic Crag B')]
        self.assertFalse(any('<a' in i for i in section.areas(one, 'climbing/')))


class RegionPartTests(Phase12Fixture):

    def test_each_part_links_to_its_row_on_its_region_map_and_a_region_without_a_map_has_none(self):
        series = importlib.import_module('sitegen.pages.series')
        days = lambda *ls: [{'label': x} for x in ls]  # noqa: E731
        t = {'title': 'Synthetic Journal', 'region_days': [
            {'region': rg.RANGE, 'title': 'Synthetic Rim', 'key': 'syn-r-journal:synthetic-rim', 'days': days('3', '4', '7')},
            {'region': rg.RANGE, 'title': None, 'key': 'syn-r-journal', 'days': days('12')},
            {'region': rg.PLANS, 'title': 'Synthetic Plans Part', 'key': 'syn-r-journal:plans', 'days': days('20', '21')},
            {'region': rg.DESERT, 'title': 'Synthetic Desert Part', 'key': 'syn-r-journal:desert', 'days': days('30')}]}
        ul = Doc(series.region_parts(t, 'trips/syn-r-journal/')).find('ul', cls='ser-parts')
        got = [(a['href'], a.text()) for a in ul.find_all('a')]
        self.assertEqual(got, [
            ('../../regions/synthetic-range/#arc-row-synthetic-range-syn-r-journal-synthetic-rim', 'Days 3–7 · Synthetic Range map (Synthetic Rim)'),
            ('../../regions/synthetic-range/#arc-row-synthetic-range-syn-r-journal', 'Day 12 · Synthetic Range map (Synthetic Journal)'),
            ('../../map/#arc-row-synthetic-plans-syn-r-journal-plans', 'Days 20–21 · Synthetic Plans map (Synthetic Plans Part)')])
        self.assertEqual(series.region_parts({'title': 'x', 'region_days': []}, ''), '')
        # the Plans map names only a trip that is gone (until the next render): map/ has no panel for it, so no row to land on
        self.use(named={rg.PLANS: ['syn-r-gone']})
        self.assertNotIn('synthetic-plans', [s for _n, s, _ts in core.region_groups(self.site, self.meta)])
        hrefs = [a['href'] for a in Doc(series.region_parts(t, 'trips/syn-r-journal/')).find_all('a')]
        self.assertEqual([h.split('#')[0] for h in hrefs], ['../../regions/synthetic-range/'] * 2)


class PanelHookTests(Phase12Fixture):

    def test_inject_acts_marks_tracks_pins_lines_and_clusters(self):
        by = {'syn-a': {'activity': 'ski'}, 'syn-b': {'activity': 'hike'}, 'syn-j': {'activity': 'hike'}}
        svg = ('<g class="mk-cat" data-key="syn-a" style="x"><a class="mk-pin" href="h" data-key="syn-b" aria-label="b">'
               '<a class="mk-line" href="h" data-key="syn-j:part" aria-label="j"><g class="mk-cluster" aria-hidden="true" data-keys="syn-b syn-a syn-x">'
               '<g class="mk-cat" data-key="syn-unknown">')
        out = self.archive.inject_acts(svg, by)
        self.assertIn('data-key="syn-a" data-act="ski"', out)
        self.assertIn('data-key="syn-b" data-act="hike"', out)
        self.assertIn('data-key="syn-j:part" data-act="hike"', out)
        self.assertIn('data-keys="syn-b syn-a syn-x" data-acts="hike ski"', out)
        self.assertIn('data-key="syn-unknown">', out)                               # a key the site does not know: nothing

    def test_a_panel_carries_the_legend_toggles_keys_count_line_and_full_screen_button(self):
        self.use(named={rg.RANGE: rg.RANGE_PUB[:3]})          # the compact key decodes what the map draws: name some trips
        doc = self.map_doc()
        panel = doc.by_id('region-synthetic-range')
        legend = panel.find('div', cls='arc-legend')
        self.assertIn('keyrow--d', legend.classes)
        self.assertTrue(all(li['data-act'] for li in legend.find('ul').find_all('li')))
        self.assertIsNotNone(panel.find('ul', cls='arc-pkey'))
        self.assertIn('keyrow--p', panel.find('ul', cls='arc-pkey').classes)
        # the legend sits in the map column, under the caption (gap2-06)
        col = panel.find('div', cls='arc-mapcol')
        self.assertIs(legend.parent, col)
        self.assertEqual(panel.by_id('arc-count-synthetic-range').classes, ['t-mono-s', 'arc-count'])
        self.assertEqual(panel.find('p', cls='arc-plive')['aria-live'], 'polite')
        self.assertEqual(panel.find('a', cls='mv-fs')['href'], '../map/synthetic-range/')
        self.assertIsNotNone(panel.find('span', cls='mv-attrib'))
        # the region page's panel: the same hooks, its button to the same page
        rpanel = self.doc(rg.RANGE).by_id('map')
        self.assertEqual(rpanel.find('a', cls='mv-fs')['href'], '../../map/synthetic-range/')
        self.assertIsNotNone(rpanel.by_id('arc-count-synthetic-range'))

    def test_every_year_list_has_the_id_its_fold_button_names(self):
        doc = self.map_doc()
        for g in doc.find_all('div', cls='arc-yr'):
            ol = g.find('ol', cls='arc-rows2')
            self.assertEqual(ol['id'], g['data-group'] + '-rows')


class RegionFullScreenTests(Phase12Fixture):

    def test_the_full_screen_page_has_the_compact_key_for_phones_where_the_legend_is_hidden(self):
        self.use(named={rg.RANGE: rg.RANGE_PUB[:3]})
        foot = Doc(self.archive_pages()['map/synthetic-range/'].html).find('div', cls='fs-foot')
        self.assertIn('keyrow--d', foot.find('div', cls='arc-legend').classes)
        key = foot.find('ul', cls='keyrow--p')
        self.assertIsNotNone(key)
        self.assertEqual(key['aria-label'], 'Map key')
        self.assertTrue(key.find_all('li'))

    def test_each_region_map_has_a_full_screen_page(self):
        pages = self.archive_pages()
        fs = sorted(u for u in pages if re.match(r'map/[a-z-]+/$', u))
        self.assertEqual(fs, sorted('map/%s/' % rg.SLUG[n] for n in rg.MAPPED))
        for url in fs:
            with self.subTest(url):
                p = pages[url]
                self.assertFalse(p.index)
                self.assertIn('<meta name="robots" content="noindex">', p.html)
                d = Doc(p.html)
                box = d.find('div', cls='fs-map')
                self.assertEqual(box['data-fs'], 'region')
                self.assertIn('map--fscol', box.find('div', cls='map').classes)
                back = d.find('div', cls='fs-bar').find('a')
                self.assertEqual(back['href'], '../#region-' + url.split('/')[1])
                self.assertEqual(d.find('span', cls='fs-nav').text(), 'NOT FOR NAVIGATION')
                self.assertIsNone(d.by_id('route-start'))                      # many routes: centred, not on one start

    def test_a_region_map_with_no_panel_on_map_has_no_full_screen_button_anywhere(self):
        # the Range's map names only a trip that is gone (until the next render): the Map page has no panel for it and so
        # no map/synthetic-range/, while the Range keeps its own page (it lists by the region field)
        self.use(named={rg.RANGE: ['syn-r-gone']})
        pages = self.archive_pages()
        self.assertNotIn('map/synthetic-range/', pages)
        self.assertIn('map/synthetic-coast/', pages)
        self.assertIsNone(self.doc(rg.RANGE).by_id('map').find('a', cls='mv-fs'))
        self.assertNotIn('map/synthetic-range/', self.html(rg.RANGE))
        self.assertEqual(self.doc(rg.COAST).by_id('map').find('a', cls='mv-fs')['href'], '../../map/synthetic-coast/')
        # and home's block for it: the name and 'Open the map' as before, no corner button
        home = importlib.import_module('sitegen.pages.home')
        self.site['region_maps'] = (rg.RANGE, rg.COAST)
        where = home.where(self.site)
        self.assertNotIn('href="map/synthetic-range/"', where)
        self.assertEqual(where.count('class="mv-fs"'), 1)
        self.assertIn('<a class="mv-fs" href="map/synthetic-coast/"', where)


if __name__ == '__main__':
    unittest.main()
