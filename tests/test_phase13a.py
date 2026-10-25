"""Phase 13A (plan 2, section 13): the header, the menu and the units switch.

- visual-17: the header's row from 1000 px (tests/test_a11y_static.py NoScriptTests pin the widths).
- phone-12: a Home row first in the menu's Site list.
- phone-13: the long index pages get the phone title bar (a.ab-page): their title and an up arrow, to the H1 (Trips:
  to its search box), shown once the H1 is under the header, as a trip's page shows its glyph and title.
- gap6-02: the Units row first in the menu, above the lists.
- gap6-03: a browser whose language is set and is not English starts in kilometers (core.PREPAINT, run under node).
- phone-10: a short or sideways phone's header scrolls away, its bottom bar is one row (tests/test_a11y_static.py).
- resilience-01: <html> carries 'js' from the head's script and loses it when site.js fails (tests/test_a11y_static.py).
- phone-09: the Trips and tick-list boxes say Search on the phone keyboard's return key.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

import helpers  # noqa: F401  (puts tools/ and tools/lib on the path)
from helpers import Doc

import test_a11y_static as a11y
from sitegen import core

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# the index pages that get the bar, their H1 and where the bar goes
# (Trips' bar goes to its H1 too: '#search' made trips.js focus the box, raising a phone's keyboard; the review)
BARS = {'trips/': ('Trips', 'trips-title', 'trips-title'), 'map/': ('Map', 'arc-title', 'arc-title'),
        'ski/': ('Backcountry Skiing', 'sec-title', 'sec-title'), 'tick-list/': ('Tick list', 'tkl-title', 'tkl-title')}


class TitleBarTests(unittest.TestCase):

    def test_the_header_writes_the_page_bar_only_for_a_page_without_a_trip(self):
        bar = Doc(core.header('map/', 'map', None, ('Map', 'arc-title'))).find('a', cls='ab-page')
        self.assertEqual((bar['href'], bar['data-ab-title'], bar['aria-label']), ('#arc-title', 'arc-title', 'Back to top: Map'))
        self.assertEqual(bar.find('span', cls='ab-t').text(), 'Map')
        self.assertEqual(bar.find('span', cls='ab-t')['aria-hidden'], 'true')
        self.assertEqual(bar.find('svg').find('path')['d'], 'M12 20V5')          # the up arrow
        trips = Doc(core.header('trips/', 'trips', None, ('Trips', 'trips-title'))).find('a', cls='ab-page')
        self.assertEqual((trips['href'], trips['data-ab-title'], trips['aria-label']), ('#trips-title', 'trips-title', 'Back to top: Trips'))
        self.assertIsNone(Doc(core.header('about/', 'about')).find('a', cls='ab-page'))

    def test_the_long_index_pages_carry_it_and_the_others_do_not(self):
        for url, (title, h1, target) in BARS.items():
            with self.subTest(url):
                doc = a11y.page_doc(url)
                (bar,) = doc.find_all('a', cls='ab-page')
                self.assertEqual((bar['href'], bar['data-ab-title'], bar.find('span', cls='ab-t').text()), ('#' + target, h1, title))
                self.assertIsNotNone(doc.by_id(h1))
                self.assertIsNotNone(doc.by_id(target))
                self.assertEqual(doc.find_all('a', cls='ab-trip'), [])
        for url in a11y.REGION_PAGES:
            bar = a11y.page_doc(url).find('a', cls='ab-page')
            self.assertEqual((bar['href'], bar['data-ab-title']), ('#reg-title', 'reg-title'))
            self.assertEqual(bar.find('span', cls='ab-t').text(), a11y.page_doc(url).by_id('reg-title').text())
        # home, About and a goal have none; a trip's page has its own bar instead
        for url in ('', 'about/', a11y.trip_url('goal')):
            self.assertEqual(a11y.page_doc(url).find_all('a', cls='ab-page'), [], url)
        story = a11y.page_doc(a11y.trip_url('story'))
        self.assertEqual((len(story.find_all('a', cls='ab-trip')), story.find_all('a', cls='ab-page')), (1, []))

    def test_it_shows_on_a_phone_once_the_title_is_under_the_header_and_never_wider(self):
        rules = a11y.parse_css(a11y.source('css', 'base.css'))[0]
        doc = a11y.page_doc('map/')
        bar, brand = doc.find('a', cls='ab-page'), doc.find('header').find('a', cls='brand')
        for width, past, shown in ((390, False, False), (390, True, True), (759, True, True), (760, True, False), (1280, True, False)):
            body = doc.find('body')
            body.attrs['class'] = ' '.join([c for c in body.classes if c != 'past-title'] + (['past-title'] if past else []))
            with self.subTest(width=width, past=past):
                e = a11y.env(width)
                self.assertEqual(a11y.displayed(bar, rules, e), shown, a11y.why(bar, 'display', rules, e))
                self.assertEqual(a11y.displayed(brand, rules, e), not shown)
        body.attrs['class'] = ' '.join(c for c in body.classes if c != 'past-title')

    def test_base_js_waits_for_the_heading_the_bar_names(self):
        src = a11y.source('js', 'base.js')
        self.assertIn("var abPage = document.querySelector('.ab-page');", src)
        self.assertIn("document.getElementById(abPage.getAttribute('data-ab-title'))", src)
        self.assertIn("{ rootMargin: '-52px 0px 0px 0px' }", src)
        # the menu closes from the width the header's row shows (visual-17)
        self.assertIn("if (window.innerWidth >= 1000) closeMenu(false);", src)
        self.assertNotIn('1140', src)


class MenuTests(unittest.TestCase):

    def test_the_units_row_comes_first_and_home_heads_the_site_list(self):
        menu = a11y.page_doc('about/').by_id('menu')
        self.assertEqual([n.classes for n in menu.find('nav').elements()], [['menu-units'], ['menu-c1'], ['menu-c2']])
        site = menu.find('ul', cls='menu-list--site').find_all('a')
        self.assertEqual((site[0]['href'], site[0].text(), site[0]['aria-current']), ('../', 'Home', None))
        self.assertEqual(a11y.page_doc('').by_id('menu').find('ul', cls='menu-list--site').find('a')['aria-current'], 'page')

    def test_on_a_phone_the_units_row_is_one_quiet_row_and_from_760_it_spans_both_columns_first(self):
        rules = a11y.parse_css(a11y.source('css', 'base.css'))[0]
        menu = a11y.page_doc('about/').by_id('menu')
        units, c1, c2 = (menu.find(cls=c) for c in ('menu-units', 'menu-c1', 'menu-c2'))
        phone, tablet = a11y.env(390), a11y.env(800)
        self.assertEqual((a11y.computed(units, 'min-height', rules, phone), a11y.computed(units, 'border-bottom', rules, phone)),
                         ('44px', '1px solid var(--rule)'))
        self.assertIsNone(a11y.computed(units, 'grid-row', rules, phone))
        # first on screen as in the markup, so the Tab order is the order seen (the review: under Site it came last)
        self.assertEqual([a11y.computed(n, 'grid-row', rules, tablet) for n in (units, c1, c2)], ['1', '2', '2'])
        self.assertEqual([a11y.computed(n, 'grid-column', rules, tablet) for n in (units, c1, c2)], ['1 / -1', '1', '2'])


class SearchKeyTests(unittest.TestCase):

    def test_both_search_boxes_say_search_on_the_phone_keyboard(self):
        for url, box in (('trips/', 'trx-q'), ('tick-list/', 'tkl-q')):
            self.assertEqual(a11y.page_doc(url).by_id(box)['enterkeyhint'], 'search', url)


class UnitsByLanguageTests(unittest.TestCase):
    """core.PREPAINT run under node against stand-ins for the document, localStorage and navigator."""

    def setUp(self):
        self.node = shutil.which('node')
        if self.node is None:
            self.skipTest('node is not installed')

    def run_prepaint(self, stored, language, storage_throws=False):
        script = (
            "const cls = new Set();\n"
            "const document = { documentElement: { classList: { add: (c) => cls.add(c) } } };\n"
            "const localStorage = { getItem: (k) => { if (%s) throw new Error('blocked'); return k === 'units' ? %s : null; } };\n"
            "const navigator = { language: %s };\n"
            "%s;\n"
            "console.log(JSON.stringify([...cls].sort()));\n"
        ) % ('true' if storage_throws else 'false', json.dumps(stored), json.dumps(language), core.PREPAINT)
        r = subprocess.run([self.node, '-e', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_stored_choice_wins_then_the_language(self):
        cases = [
            ((None, 'en-US'), ['js']), ((None, 'en'), ['js']), ((None, 'EN-gb'), ['js']),
            ((None, 'de-DE'), ['js', 'km']), ((None, 'fr'), ['js', 'km']), ((None, 'pt-BR'), ['js', 'km']),
            ((None, ''), ['js']), ((None, None), ['js']),                          # no language: miles
            (('mi', 'de-DE'), ['js']), (('km', 'en-US'), ['js', 'km']), (('km', 'fr'), ['js', 'km']),
        ]
        for (stored, lang), want in cases:
            with self.subTest(stored=stored, lang=lang):
                self.assertEqual(self.run_prepaint(stored, lang), want)
        # storage that throws (a private window in some browsers): the language still decides
        self.assertEqual(self.run_prepaint(None, 'it', storage_throws=True), ['js', 'km'])
        self.assertEqual(self.run_prepaint(None, 'en-AU', storage_throws=True), ['js'])

    def test_only_a_press_of_the_switch_stores_the_choice(self):
        # base.js shows the page's start on the switch without storing it, so a browser keeps following its language
        # until the reader chooses; a press stores (and announces) it
        src = a11y.source('js', 'base.js')
        self.assertIn("if (announce) { try { localStorage.setItem('units', u); } catch (e) { /* private mode */ } }", src)
        self.assertEqual(src.count("localStorage.setItem('units'"), 1)
        self.assertIn("setUnits(root.classList.contains('km') ? 'km' : 'mi', false);", src)
        self.assertIn("if (b) setUnits(b.dataset.units, true);", src)

    def test_every_page_runs_it_before_the_body(self):
        html_ = a11y.site_pages()['about/']
        head = html_.split('</head>', 1)[0]
        self.assertEqual(head.count('<script>' + core.PREPAINT + '</script>'), 1)
        self.assertNotIn('<script>', html_.split('</head>', 1)[1].replace('<script src=', ''))


if __name__ == '__main__':
    unittest.main()
