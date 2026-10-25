"""Phase 2: core.header navigation (Trips, Map, PCT, About, Search), aria-current per page, the phone menu's columns and
the footer's Site list. The header reads the registered site (core.register_site, done by helpers.make_site) to decide
whether the PCT link exists. Only the main nav (<nav aria-label="Main">) and the menu's Site column are asserted on;
the menu's Reports column keeps its existing behaviour. Fixture slugs match no real trip except the PCT's, whose
rendered glyph is optional (core.glyph returns '' when the drawing is missing).
"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

PCT = 'trips/pacific-crest-trail-2024/'
SITE_LINKS = ['trips/', 'tick-list/', 'map/', PCT, 'about/']   # then Search: a form (core.search_form), a link on trips/ alone


class HeaderFixture(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        helpers.make_trip(self.tmp, 'west-couloir', title='West Couloir', activity='ski', date='2026-01-17', region='Eastern Sierra', track=True)
        helpers.make_trip(self.tmp, 'basin-loop', title='Basin Loop', activity='hike', date='2025-08-10', region='Eastern Sierra', track=True)
        helpers.make_trip(self.tmp, 'hut-route', title='Hut Route', activity='ski', kind='multi-day', date='2024-01-16', end_date='2024-01-17',
                          days=[{'title': 'In'}, {'title': 'Out'}])
        helpers.make_series(self.tmp, search_aliases=['PCT'])
        helpers.make_trip(self.tmp, 'someday-ridge', title='Someday Ridge', activity='mtb', kind='planned', date='2027-06-01', track=True)
        self.trips = helpers.load_dir(self.tmp)
        self.site = helpers.make_site(self.trips)
        self.by = self.site['by_slug']

    def header(self, here, active=None, trip=None):
        return Doc(core.header(here, active, trip))

    @staticmethod
    def main_nav(doc):
        nav = doc.find('nav', attrs={'aria-label': 'Main'})
        assert nav is not None, 'no <nav aria-label="Main">'
        return [(a['href'], a['aria-current'], a.text()) for a in nav.find_all('a')]

    def current(self, here, active=None, trip=None):
        """(href, aria-current) of every main-nav link that carries aria-current."""
        return [(h, c) for h, c, _ in self.main_nav(self.header(here, active, trip)) if c]

    @staticmethod
    def site_column(doc):
        ul = doc.by_id('menu').find('ul', cls='menu-list--site')
        assert ul is not None, 'no .menu-list--site in #menu'
        return ul.find_all('a')


class HeaderTests(HeaderFixture):

    def test_pct_constants(self):
        self.assertEqual(core.PCT_SLUG, 'pacific-crest-trail-2024')
        self.assertEqual(core.PCT_LABEL, 'PCT')
        self.assertEqual('trips/%s/' % core.PCT_SLUG, PCT)

    def test_home_nav_links_in_order_and_nothing_current(self):
        nav = self.main_nav(self.header('', None))
        self.assertEqual([h for h, _, _ in nav], SITE_LINKS)
        self.assertEqual([t for _, _, t in nav], ['Trips', 'Tick list', 'Map', 'PCT', 'About'])
        self.assertEqual([c for _, c, _ in nav], [None] * 5)

    def test_main_nav_has_no_activity_links(self):
        hrefs = [h for h, _, _ in self.main_nav(self.header('', None))]
        for act, _ in core.NAV:
            self.assertNotIn(core.section_url(act), hrefs)

    def test_trips_index_marks_trips_as_page(self):
        self.assertEqual(self.current('trips/', 'trips'), [('../trips/', 'page')])

    def test_report_page_marks_trips_true(self):
        t = self.by['west-couloir']
        self.assertEqual(self.current('trips/west-couloir/', 'ski', t), [('../../trips/', 'true')])
        self.assertEqual(self.current('trips/west-couloir/map/', 'ski', t), [('../../../trips/', 'true')])   # full-screen map

    def test_multiday_page_marks_trips_true(self):
        t = self.by['hut-route']
        self.assertEqual(self.current('trips/hut-route/', 'ski', t), [('../../trips/', 'true')])

    def test_section_page_marks_trips_true(self):
        self.assertEqual(self.current('ski/', 'ski'), [('../trips/', 'true')])
        self.assertEqual(self.current('hiking/', 'hike'), [('../trips/', 'true')])
        self.assertEqual(self.current('other/', 'other'), [('../trips/', 'true')])

    def test_pct_page_marks_pct_as_page_and_not_trips(self):
        t = self.by['pacific-crest-trail-2024']
        self.assertEqual(self.current(PCT, 'hike', t), [('../../' + PCT, 'page')])

    def test_map_page_marks_map(self):
        self.assertEqual(self.current('map/', 'map'), [('../map/', 'page')])

    def test_about_page_marks_about(self):
        self.assertEqual(self.current('about/', 'about'), [('../about/', 'page')])

    def test_search_is_a_form_that_lands_on_the_explorer_in_best_match_order(self):
        # ia-02 (Phase 7): every page but trips/ has a search box in the header and one in the menu, with their own ids
        for here, active in (('ski/', 'ski'), ('', None), ('trips/west-couloir/', 'ski'), ('map/', 'map')):
            with self.subTest(here=here):
                doc = self.header(here, active)
                nav = doc.find('nav', attrs={'aria-label': 'Main'})
                self.assertEqual([a for a in nav.find_all('a') if a['href'].endswith('#search')], [])
                forms = doc.find_all('form', cls='nav-search')
                self.assertEqual(len(forms), 2)
                header_form, menu_form = forms
                self.assertIs(nav.find('form', cls='nav-search') is not None, True)
                self.assertIsNotNone(doc.by_id('menu').find('form', cls='nav-search'))
                for f, fid in ((header_form, 'nav-q'), (menu_form, 'menu-q')):
                    self.assertEqual((f['role'], f['method'], f['action']), ('search', 'get', core.link(here, 'trips/')))
                    box = f.find('input', attrs={'name': 'q'})
                    self.assertEqual((box['id'], box['type'], box['maxlength'], box['autocomplete']), (fid, 'search', '200', 'off'))
                    self.assertEqual(f.find('label', attrs={'for': fid}).text(), 'Search trips')
                    self.assertEqual([(i['name'], i['value']) for i in f.find_all('input', attrs={'type': 'hidden'})], [('sort', 'relevance')])
                    btn = f.find('button')
                    self.assertEqual((btn['type'], btn['aria-label']), ('submit', 'Search'))
                    self.assertIsNotNone(btn.find('svg'))

    def test_on_trips_itself_search_stays_a_link_to_the_pages_own_box(self):
        doc = self.header('trips/', 'trips')
        nav = doc.find('nav', attrs={'aria-label': 'Main'})
        links = [a for a in nav.find_all('a') if a['href'] == '../trips/#search']
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].text(), 'Search')
        self.assertIsNotNone(links[0].find('svg'))
        self.assertIsNone(links[0]['aria-current'])
        self.assertEqual(doc.find_all('form', cls='nav-search'), [])
        self.assertEqual([a['href'] for a in self.site_column(doc)][-1], '../trips/#search')

    def test_pct_link_only_when_the_series_exists(self):
        helpers.make_site([self.by[s] for s in ('west-couloir', 'basin-loop', 'someday-ridge')])
        doc = self.header('', None)
        self.assertNotIn(PCT, [a['href'] for a in doc.find_all('a')])
        self.assertEqual([h for h, _, _ in self.main_nav(doc)], ['trips/', 'tick-list/', 'map/', 'about/'])
        self.assertEqual([a['href'] for a in self.site_column(doc)], ['./', 'trips/', 'tick-list/', 'map/', 'about/'])
        helpers.make_site(self.trips)
        self.assertIn(PCT, [h for h, _, _ in self.main_nav(self.header('', None))])

    def test_phone_menu_reports_and_site_columns(self):
        doc = self.header('', None)
        menu = doc.by_id('menu')
        self.assertIn('hidden', menu)
        reports = [a['href'] for a in menu.find('div', cls='menu-c1').find_all('a')]
        self.assertEqual(reports, [core.section_url(a) for a, _ in core.NAV])
        site = self.site_column(doc)
        # Home first (Phase 13A, phone-12), marked as the page on the home page
        self.assertEqual([a['href'] for a in site], ['./'] + SITE_LINKS)
        self.assertEqual([a.text() for a in site], ['Home', 'Trips', 'Tick list', 'Map & archive', 'PCT', 'About'])
        self.assertEqual(site[0]['aria-current'], 'page')
        self.assertEqual(site[0].find('path')['d'], 'M3.5 11L12 4l8.5 7')         # the 'home' icon
        units = menu.find(cls='menu-units')
        self.assertIsNotNone(units)
        self.assertIsNotNone(units.find(attrs={'role': 'radiogroup'}))
        # the Units row first, above both lists (Phase 13A, gap6-02), so a phone shows it as the menu opens
        nav = menu.find('nav')
        self.assertEqual([n.classes for n in nav.elements()], [['menu-units'], ['menu-c1'], ['menu-c2']])
        self.assertEqual(len(menu.find_all(cls='menu-units')), 1)

    def test_menu_site_column_marks_current_like_the_main_nav(self):
        cur = [(a['href'], a['aria-current']) for a in self.site_column(self.header('trips/', 'trips')) if a['aria-current']]
        self.assertEqual(cur, [('../trips/', 'page')])                   # Home is the page only on the home page
        t = self.by['pacific-crest-trail-2024']
        cur = [(a['href'], a['aria-current']) for a in self.site_column(self.header(PCT, 'hike', t)) if a['aria-current']]
        self.assertEqual(cur, [('../../' + PCT, 'page')])

    def test_links_are_relative_from_a_nested_page(self):
        nav = self.main_nav(self.header('trips/west-couloir/', 'ski', self.by['west-couloir']))
        self.assertEqual([h for h, _, _ in nav], ['../../' + u for u in SITE_LINKS])
        for h, _, _ in nav:
            self.assertFalse(h.startswith('/'), h)
        nav = self.main_nav(self.header('', None))
        for h, _, _ in nav:
            self.assertFalse(h.startswith(('/', './', '../')), h)

    def test_footer_site_list_starts_with_trips(self):
        doc = Doc(core.footer('ski/'))
        site = doc.find('nav', attrs={'aria-labelledby': 'f-site'})
        links = site.find_all('a')
        self.assertEqual(links[0]['href'], '../trips/')
        self.assertEqual(links[0].text(), 'Trips')
        hrefs = [a['href'] for a in links]
        for want in ('../map/', '../about/', '../feed.xml'):
            self.assertIn(want, hrefs)
        reports = doc.find('nav', attrs={'aria-labelledby': 'f-rep'})
        self.assertEqual([a['href'] for a in reports.find_all('a')], ['../' + core.section_url(a) for a, _ in core.NAV])

    def test_document_passes_active_through_to_the_header(self):
        html_ = core.document('trips/west-couloir/', 'West Couloir', '<p>x</p>', active='ski', body_cls='p-report')
        nav = Doc(html_).find('nav', attrs={'aria-label': 'Main'})
        cur = [(a['href'], a['aria-current']) for a in nav.find_all('a') if a['aria-current']]
        self.assertEqual(cur, [('../../trips/', 'true')])
        html_ = core.document('about/', 'About', '<p>x</p>', active='about', body_cls='p-about')
        nav = Doc(html_).find('nav', attrs={'aria-label': 'Main'})
        self.assertEqual([(a['href'], a['aria-current']) for a in nav.find_all('a') if a['aria-current']], [('../about/', 'page')])


if __name__ == '__main__':
    unittest.main()
