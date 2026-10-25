"""Phase 15 (plan 2, section 15): what a render round leaves behind, checked offline.

- gap9-05: the content check warns when the trip folders under rendered/trips were drawn by different renderer
  versions (a re-render left half done), or the site maps by an older one than the newest trip; silent otherwise.
- maps-15: Mountain biking and Hiking get the Ski page's map panel once their panel maps are drawn ('mtb-<region>',
  'hike-<region>'); one region shows no tab row; without the maps the pages are as they were.
- visual-01 step 2: a card without a photo shows the 400 x 267 'card' drawing, else the 200 x 152 tile.
- copy-18, maps-01, maps-06: a cluster's tooltip, the map key's kilometre wording, labels at points along a line.
Synthetic folders in a temp directory; nothing is drawn or fetched.
"""
import importlib
import json
import os
import tempfile
import unittest
from unittest import mock

import helpers
from helpers import Doc

import checks
from sitegen import core

tearDownModule = helpers.no_region_pages_left


def write_meta(root, rel, version=None):
    os.makedirs(os.path.join(root, os.path.dirname(rel)), exist_ok=True)
    meta = {'hash': 'synthetic', 'maps': {}}
    if version is not None:
        meta['renderer'] = {'version': version, 'python': '3.9.6', 'cwebp': None, 'date': '2026-01-01', 'osm': 'cached'}
    with open(os.path.join(root, rel), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh)


class RendererVersionTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.live = [{'slug': 'syn-%02d' % i} for i in range(1, 8)]

    def findings(self):
        out = []
        checks._renderer_version_findings(self.live, self.root, out)
        return [(f['level'], f['file'], f['text']) for f in out]

    def test_one_version_everywhere_is_silent(self):
        for t in self.live:
            write_meta(self.root, 'trips/%s/meta.json' % t['slug'], 8)
        write_meta(self.root, 'site/meta.json', 8)
        self.assertEqual(self.findings(), [])
        # folders drawn before the record existed, all of them: silent too (one version, unknown)
        for t in self.live:
            write_meta(self.root, 'trips/%s/meta.json' % t['slug'])
        write_meta(self.root, 'site/meta.json')
        self.assertEqual(self.findings(), [])

    def test_a_half_done_re_render_names_the_older_folders(self):
        for i, t in enumerate(self.live):
            write_meta(self.root, 'trips/%s/meta.json' % t['slug'], 8 if i < 1 else None)
        write_meta(self.root, 'site/meta.json')
        (trips, site) = self.findings()
        self.assertEqual(trips[:2], ('warning', 'rendered/trips'))
        self.assertIn('6 of 7 renders are at renderer no recorded version and 1 at version 8: the re-render is unfinished; '
                      'run python3 tools/render.py (still older: syn-02, syn-03, syn-04, syn-05, syn-06, ...)', trips[2])
        self.assertEqual(site, ('warning', 'rendered/site/meta.json', 'rendered/site/meta.json: the site maps are at renderer '
                                'no recorded version and the newest trip at version 8: run python3 tools/render.py --site'))

    def test_a_trip_without_a_render_counts_for_nothing(self):
        write_meta(self.root, 'trips/syn-01/meta.json', 8)
        self.assertEqual(self.findings(), [])


class PanelTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        mk = lambda slug, **kw: helpers.make_trip(tmp.name, slug, track=True, **kw)  # noqa: E731
        for i in range(6):
            mk('syn-r-%d' % i, title='Synthetic Ride %d' % i, activity='mtb', date='2025-0%d-01' % (i + 1),
               region='Synthetic Coast' if i % 2 else 'Synthetic Range')
            mk('syn-h-%d' % i, title='Synthetic Hike %d' % i, activity='hike', date='2024-0%d-01' % (i + 1), region='Synthetic Range')
        mk('syn-s-0', title='Synthetic Ski', activity='ski', date='2026-01-01', region='Synthetic Range')
        self.site = helpers.make_site(helpers.load_dir(tmp.name))
        self.section = importlib.import_module('sitegen.pages.section')

    def page(self, act, regions):
        with mock.patch.object(self.section, 'ski_regions', lambda ts, a='ski': list(regions)):
            return Doc(self.section.page(act, self.site).html)

    def test_rides_get_the_panel_beside_their_list(self):
        doc = self.page('mtb', ['Synthetic Range', 'Synthetic Coast'])
        split = doc.find('div', cls='sec-split')
        self.assertEqual(split.classes, ['sec-split', 'sec-split--mtb', 'wrap'])
        self.assertEqual(split.find('aside', cls='sec-panel').find('h2').text(), 'Ride map by region')
        self.assertEqual(split.find('div', cls='sec-maps')['id'], 'mtb-map')
        self.assertEqual(len(split.find('div', attrs={'role': 'tablist'}).find_all('button')), 2)
        lst = split.find('div', cls='sec-list')
        self.assertEqual(lst['data-map-target'], 'mtb-map')
        more = lst.find('section', cls='sec-more')
        self.assertNotIn('wrap', more.classes)                       # inside the split's own wrap
        self.assertTrue(lst.find_all('li', cls='trow'))
        # without scripting every region's map shows (the Ski page's noscript rules, in this page's head)
        with mock.patch.object(self.section, 'ski_regions', lambda ts, a='ski': ['Synthetic Range', 'Synthetic Coast']):
            self.assertIn(self.section.NOSCRIPT, self.section.page('mtb', self.site).html.split('</head>')[0])

    def test_one_region_shows_its_map_without_a_tab_row(self):
        doc = self.page('hike', ['Synthetic Range'])
        aside = doc.find('aside', cls='sec-panel')
        self.assertEqual(aside.find('h2').text(), 'Hike map by region')
        self.assertIsNone(aside.find('div', attrs={'role': 'tablist'}))
        panel = aside.find('div', cls='sec-rp')
        self.assertEqual((panel['role'], panel['hidden'], panel['aria-labelledby']), (None, None, None))
        # its label names the region with scripting on too: the heading is visually hidden from 960 px and no tab says it
        self.assertEqual(panel.classes, ['sec-rp', 'sec-rp--one'])
        self.assertEqual(panel.find('p', cls='sec-rp-l').text(), 'Synthetic Range')
        with open(os.path.join(helpers.ROOT, 'assets', 'css', 'pages', 'section.css'), encoding='utf-8') as fh:
            self.assertIn('.sec-rp--one .sec-rp-l { display: block; }', fh.read())

    def test_a_tab_counts_every_report_its_map_draws(self):
        # the featured ride is no row of the More list, but its line is on the region's map: the tab counts it
        doc = self.page('mtb', ['Synthetic Range', 'Synthetic Coast'])
        tabs = doc.find('div', attrs={'role': 'tablist'}).find_all('button')
        self.assertEqual([b.find('span', cls='sec-tab-n').text() for b in tabs], [', 3 reports', ', 3 reports'])

    def test_the_regions_are_those_with_a_drawn_panel_map_of_the_activity(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, 'rendered', 'site'))
            with open(os.path.join(tmp, 'rendered', 'site', 'meta.json'), 'w', encoding='utf-8') as fh:
                json.dump({'maps': {'mtb-synthetic-coast-desktop': {}, 'ski-synthetic-range-desktop': {}}}, fh)
            with mock.patch.object(core, 'ROOT', tmp):
                rides = [t for t in self.site['trips'] if t['activity'] == 'mtb']
                hikes = [t for t in self.site['trips'] if t['activity'] == 'hike']
                self.assertEqual(self.section.ski_regions(rides, 'mtb'), ['Synthetic Coast'])
                self.assertEqual(self.section.ski_regions(hikes, 'hike'), [])

    def test_without_panel_maps_the_pages_are_as_they_were(self):
        for act in ('mtb', 'hike'):
            with self.subTest(act=act):
                doc = self.page(act, [])
                self.assertIsNone(doc.find('div', cls='sec-split'))
                self.assertIn('wrap', doc.find('section', cls='sec-more').classes)

    def test_the_ski_panel_keeps_its_tab_row_for_one_region(self):
        doc = self.page('ski', ['Synthetic Range'])
        self.assertIsNotNone(doc.find('div', attrs={'role': 'tablist'}))
        self.assertEqual(doc.find('div', cls='sec-maps')['id'], 'ski-map')


class CardTileTests(unittest.TestCase):

    def test_the_card_drawing_when_rendered_else_the_tile(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = {'url': 'trips/syn-c/', 'rendered': tmp, 'track': os.path.join(tmp, 'track.gpx'), 'days': [], 'kind': 'trip'}
            open(os.path.join(tmp, 'track.gpx'), 'w').close()
            open(os.path.join(tmp, 'tile.svg.html'), 'w').close()
            self.assertIn('src="../../trips/syn-c/tile.svg" width="200" height="152"', core.card_tile(t, 'x/y/'))
            open(os.path.join(tmp, 'card.svg.html'), 'w').close()
            self.assertIn('src="../../trips/syn-c/card.svg" width="400" height="267"', core.card_tile(t, 'x/y/'))
            self.assertIn('tile.svg', core.tile(t, 'x/y/'))          # list rows keep the small tile


class RendererPieceTests(unittest.TestCase):

    def test_a_clusters_titles_are_read_back_one_per_key(self):
        # renderkey.drawn_titles (the old hash's retitle test) reads copy-18's form, and the form drawn before it
        import renderkey
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'm.svg.html')
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write('<g class="mk-cluster" aria-hidden="true" data-keys="syn-a syn-b"><title>2 reports start here: '
                         'Synthetic A; Synthetic B</title></g><g class="mk-cluster" aria-hidden="true" data-keys="syn-c syn-d">'
                         '<title>Synthetic C; Synthetic D</title></g><g class="mk-cluster" aria-hidden="true" '
                         'data-keys="syn-e syn-f syn-g syn-h syn-i"><title>5 reports start here: E; F; G and 2 more</title></g>')
            self.assertEqual(renderkey.drawn_titles([p]), {'syn-a': 'Synthetic A', 'syn-b': 'Synthetic B',
                                                          'syn-c': 'Synthetic C', 'syn-d': 'Synthetic D'})

    def test_a_cluster_names_its_count_and_three_titles(self):
        import mapkit
        self.assertEqual(mapkit.cluster_title(['A', 'B']), '2 reports start here: A; B')
        self.assertEqual(mapkit.cluster_title(['A', 'B', 'A', 'C', 'D', 'E']), '6 reports start here: A; B; C and 2 more')
        self.assertEqual(mapkit.cluster_title(['A']), '1 report starts here: A')

    def test_the_build_writes_a_clusters_tooltip_the_same_way(self):
        helpers.keep_state(self)
        core._TITLES.clear()
        core._TITLES.update({'syn-a': 'Synthetic A', 'syn-b': 'Synthetic B'})
        frag = '<g class="mk-cluster" aria-hidden="true" data-keys="syn-a syn-b"><title>old; titles</title></g>'
        self.assertIn('<title>2 reports start here: Synthetic A; Synthetic B</title>', core.relabel(frag))

    def test_a_map_with_kilometre_discs_keys_them_as_kilometers_in_the_km_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = {'rendered': tmp}
            with open(os.path.join(tmp, 'map-wide.svg.html'), 'w') as fh:
                fh.write('<g class="u-mi"><g class="mk-mile"></g></g>')
            self.assertEqual((core.mile_key(t, 'map-wide'), core.mile_key(t, 'map-wide', True)), ('mile', 'mile_out'))
            with open(os.path.join(tmp, 'map-wide.svg.html'), 'w') as fh:
                fh.write('<g class="u-mi"><g class="mk-mile"></g></g><g class="u-km"><g class="mk-mile mk-km"></g></g>')
            self.assertEqual((core.mile_key(t, 'map-wide'), core.mile_key(t, 'map-wide', True)), ('mile_km', 'mile_km_out'))
        row = Doc(core.key_row(['mile_km']))
        self.assertEqual([s_.text() for s_ in row.find_all('span', cls='u-km')], ['Kilometer'])

    def test_point_labels_sit_beside_the_line_with_a_tick(self):
        import geo
        import mapkit
        import render_fixtures as rf
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(geo, 'get_tile', rf.synth_tile), \
                mock.patch.object(mapkit, 'FRAG', tmp), mock.patch.object(mapkit, 'MAPPNG', tmp):
            tr = mapkit.Track(rf.LOOP_PTS, 'syn-loop', 'HIK')
            mid = rf.LOOP_PTS[len(rf.LOOP_PTS) // 2]
            mapkit.render_map(dict(name='m', w=390, h=600, tracks=[{'track': tr, 'style': 'cat', 'cat': 'HIK', 'width': 2.6}],
                                   osm=None, osm_data={}, hillshade=False, contours=False, legend=False, graticule=False,
                                   miles=False, chevrons=False, startend=False, gpsmax=False, north=False, scale=False, trim=False,
                                   point_labels=[(mid[0], mid[1], 'MAY'), (90.0, 0.0, 'OFF')]))
            with open(os.path.join(tmp, 'm.svg.html')) as fh:
                svg = fh.read()
        self.assertEqual(svg.count('class="mk-plbl"'), 1)                    # the point off the map is left out
        self.assertIn('>MAY</text>', svg)
        self.assertRegex(svg, r'<g class="mk-plbl"><path d="M[0-9.]+ [0-9.]+h-?6"')


if __name__ == '__main__':
    unittest.main()
