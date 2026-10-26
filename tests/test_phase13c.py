"""Phase 13C (plan 2, section 13): accessibility and copy.

- a11y-05: a unit is shown abbreviated and read as its word (core.unit_word, core.caps_unit, inside core.U); the units
  switch's buttons say which system they are.
- a11y-04 / a11y-15 / qa-01: forced colours keep the activity colours that key a map; a contrast block; the meta line's
  dot is drawn and not read.
- ia-13, copy-11 to copy-14, copy-20, gap6-07: one word per destination ('Map', 'By activity'), 'Backcountry Skiing',
  the PCT link named 'PCT journal', one verb per kind of destination, the map captions' one wording, the tick list's
  empty sentence, the footer's training label.
The home region link's 44 px box and the heading order are in tests/test_a11y_static.py (TargetSizeTests, PageTests).
"""
import inspect
import re
import unittest
from unittest import mock

import helpers  # noqa: F401  (puts tools/ and tools/lib on the path)
from helpers import Doc

import test_a11y_static as a11y
from sitegen import core
from sitegen.pages import multiday, ticklist

import content


class UnitWordTests(unittest.TestCase):

    def test_a_unit_is_shown_short_and_read_as_its_word(self):
        self.assertEqual(core.unit_word(' mi'), ' <span aria-hidden="true">mi</span><span class="sr">miles</span>')
        self.assertEqual(core.unit_word('FT'), '<span aria-hidden="true">FT</span><span class="sr">feet</span>')
        for abbr, word in (('km', 'kilometers'), ('m', 'meters'), ('mph', 'miles per hour'), ('min/mi', 'minutes per mile')):
            self.assertIn('<span class="sr">%s</span>' % word, core.unit_word(abbr))
        self.assertEqual(core.unit_word(' bpm'), ' bpm')                     # one it does not know: as it was
        self.assertIn('<span class="sr">hours and minutes</span>', core.unit_word(' h:mm'))
        self.assertEqual(core.caps_unit('5,302', 'FT', 'GAIN'),
                         '5,302\xa0<span aria-hidden="true">FT</span><span class="sr">feet</span>\xa0GAIN')

    def test_core_u_reads_its_units_and_shows_them_as_before(self):
        u = Doc(core.U('12.8', '20.6', ' mi', ' km'))
        self.assertEqual(helpers.seen_text(u.root), '12.8 mi20.6 km')
        mi = u.find('span', cls='u-mi')
        self.assertEqual(mi.find('span', cls='sr').text(), 'miles')
        self.assertEqual(mi.find('span', cls='unit').find('span')['aria-hidden'], 'true')

    def test_each_stat_speaks_its_unit_once(self):
        t = {'stats': {'distance_km': 20.6, 'gain_m': 1616, 'high_m': 3643, 'moving_s': 23640}, 'activity': 'ski', 'kind': 'trip'}
        for name, html_ in (('stats line', core.SEP.join(core.plain_stats(t, items=True))), ('cells', core.stats_cells(t))):
            with self.subTest(name):
                sr = [s.text() for s in Doc(html_).find_all('span', cls='sr')]
                self.assertEqual(sr.count('miles'), 1)
                self.assertEqual(sr.count('kilometers'), 1)
                self.assertGreaterEqual(sr.count('feet'), 1)

    def test_the_other_systems_line_and_the_multi_day_heights_read_their_words(self):
        sub = Doc(core.U_sub('12.8', '20.6', 'MI', 'KM'))                 # the line under a strip value
        self.assertEqual(helpers.seen_text(sub.root), '20.6 KM12.8 MI')
        self.assertEqual([s.text() for s in sub.find_all('span', cls='sr')], ['kilometers', 'miles'])
        gain = Doc(multiday.caps_elev(1000, 'GAIN'))
        self.assertEqual(helpers.plain_text(helpers.seen_text(gain.find('span', cls='u-mi'))), '3,281 FT GAIN')
        self.assertEqual([s.text() for s in gain.find_all('span', cls='sr')], ['feet', 'meters'])
        # a day's profile head: its gain and loss go through caps_unit too
        self.assertNotRegex(inspect.getsource(multiday.day_profile), r"%s (FT|M)'")
        self.assertIn('<span class="sr">kilometers</span>', core.KEY_HTML['mile'])

    def test_no_number_is_read_with_a_bare_unit_abbreviation(self):
        # every fixture page as a screen reader reads it (aria-hidden and the drawings left out; write-ups and titles are
        # the author's words): a number never meets 'MI', 'km', 'FT', 'mph' or 'h:mm' as letters
        unit = re.compile(r'(?<![\w.])[+−-]?\d[\d,.]*[ \xa0]?(MI|KM|FT|M|MPH|KM/H|MIN/MI|MIN/KM|H:MM)(?![\w/])', re.I)
        skip_tags = {'head', 'script', 'style', 'template', 'svg', 'h1'}

        def read(node, out):
            for c in node.children:
                if isinstance(c, str):
                    out.append(c)
                elif c.tag in skip_tags or c['aria-hidden'] == 'true' or 'prose' in c.classes:
                    out.append(' ')
                else:
                    read(c, out)
        seen = 0
        for url, html_ in a11y.site_pages().items():
            if not (url == '' or url.endswith('/') or url.endswith('.html')):
                continue
            out = []
            read(Doc(html_).root, out)
            text = ''.join(out)
            seen += text.count('miles')
            with self.subTest(page=url):
                self.assertEqual([text[max(0, m.start() - 20):m.end() + 5] for m in unit.finditer(text)], [])
        self.assertGreater(seen, 20)                                      # the words are there instead

    def test_the_units_switch_says_which_system_each_button_is(self):
        doc = Doc(core.units_control())
        labels = [(b.text(), b['aria-label']) for b in doc.find_all('button')]
        self.assertEqual(labels, [('MI', 'MI: miles and feet'), ('KM', 'KM: kilometers and meters')])
        for text, label in labels:
            self.assertTrue(label.startswith(text))                          # the name holds the visible text
        about = a11y.page_doc('about/').find('div', cls='abo-units')
        self.assertEqual([b['aria-label'] for b in about.find_all('button')], list(core.UNITS_LABELS))


class StylesheetTests(unittest.TestCase):

    def setUp(self):
        self.rules = a11y.published_rules()[0]

    def decls(self, sel, media_word):
        return [dict((k, v[0]) for k, v in r.decls.items()) for r in self.rules
                if r.selector == sel and any(media_word in q for q in r.media)]

    def test_forced_colours_keep_the_activity_colours_that_key_a_map(self):
        for sel in ('.keyrow--compact .disc', '.fchip .chip-sw', '.ser-rl i'):
            self.assertEqual([d['forced-color-adjust'] for d in self.decls(sel, 'forced-colors')], ['none'], sel)
        self.assertEqual(self.decls('.ser-rl i', 'forced-colors')[0]['outline'], '1px solid CanvasText')
        self.assertEqual(self.decls('.ser-mnav a.is-empty', 'forced-colors')[0]['color'], 'GrayText')
        # a disc beside its own word that keys nothing stays forced
        self.assertEqual(self.decls('.sec-h1row .disc', 'forced-colors'), [])

    def test_more_contrast_raises_the_third_ink_and_the_map_labels(self):
        root = self.decls(':root', 'prefers-contrast')
        # Alpine (Phase 16): the strong rule is ink already, so the hairlines darken instead
        self.assertEqual(root, [{'--ink-3': 'var(--ink-2)', '--rule': '#767676'}])
        for sel in ('svg .pf-ax', 'svg .mk-lbl'):
            self.assertEqual(self.decls(sel, 'prefers-contrast'), [{'fill': 'var(--ink-2)'}], sel)

    def test_the_meta_lines_dot_is_drawn_and_not_read(self):
        (rule,) = [r for r in self.rules if r.selector == '.ml > .mi::before' and not r.media]
        self.assertEqual(rule.decls['content'][0], '"·" / ""')
        src = a11y.source('css', 'base.css')
        self.assertIn('.ml > .mi::before { content: "·"; content: "·" / "";', src)    # the fallback first
        # the PCT page's day label and stats line draw their dots the same way
        for sel, dot in (('.ser-dd:not(:empty)::before', '" · " / ""'), ('.ser-st > div::before', '"·" / ""')):
            (r,) = [r for r in self.rules if r.selector == sel and not r.media]
            self.assertEqual(r.decls['content'][0], dot, sel)
        # ... and a day's label reads 'Day 2, <date>' in its article's name: a hidden comma where the dot is drawn
        dates = [dd for dd in a11y.page_doc(a11y.trip_url('journal')).find_all('span', cls='ser-dd') if dd.children]
        self.assertTrue(dates)
        for dd in dates:
            self.assertEqual((dd.children[0].classes, dd.children[0].text(clean=False)), (['sr'], ', '))


class WordsTests(unittest.TestCase):

    def test_one_word_per_destination(self):
        doc = a11y.page_doc('')
        nav = doc.find('nav', attrs={'aria-label': 'Main'})
        self.assertIn('Map', [a.text() for a in nav.find_all('a')])
        menu = doc.by_id('menu')
        self.assertEqual(menu.find('div', cls='menu-c1').find('p', cls='menu-l').text(), 'By activity')
        self.assertIn('Map', [a.text() for a in menu.find('ul', cls='menu-list--site').find_all('a')])
        foot = doc.find('footer', cls='site-f')
        self.assertEqual(foot.by_id('f-rep').text(), 'By activity')
        self.assertIn('Map', [a.text() for a in foot.find_all('a')])
        arc = a11y.page_doc('map/')
        self.assertEqual((arc.find('h1').text(), arc.find('title').text()), ('Map', 'Map · Eric Sichak'))
        nf = a11y.page_doc('404.html')
        self.assertEqual([h.text() for h in nf.find_all('h2', cls='nf-l')], ['By activity', 'Site'])
        self.assertIn('Map', [s.text() for s in nf.find_all('span', cls='abo-act-n')])
        for url in ('', 'map/', '404.html', a11y.trip_url('story')):
            self.assertNotIn('Map &amp; archive', a11y.site_pages()[url], url)
        # the crumb root is still 'Reports', to home
        crumbs = a11y.page_doc(a11y.trip_url('story')).find('nav', cls='crumbs')
        self.assertEqual(crumbs.find('a').text(), 'Reports')

    def test_the_pct_link_is_named_pct_journal(self):
        with mock.patch.object(core, '_HAS_PCT', [True]):                 # the header shows the link when the journal exists
            doc = Doc(core.header('', None))
        pct = [a for a in doc.find_all('a') if a['href'] == 'trips/%s/' % core.PCT_SLUG]
        self.assertEqual(len(pct), 2)                                     # the header's and the menu's
        for a in pct:
            self.assertEqual(a['aria-label'], 'PCT journal')
            self.assertIn(helpers.plain_text(a.text()), a['aria-label'])
        # the menu button keeps its name; aria-expanded says whether it is open
        self.assertEqual(doc.find('button', cls='menu-btn')['aria-label'], 'Menu')
        self.assertEqual(a11y.page_doc('').find('button', cls='menu-btn')['aria-label'], 'Menu')

    def test_backcountry_skiing(self):
        self.assertEqual(core.ACT['ski'][0], 'Backcountry Skiing')
        self.assertEqual(dict(core.NAV)['ski'], 'Backcountry Skiing')
        self.assertEqual(content.ACTIVITIES['ski'][0], 'Backcountry Skiing')
        self.assertEqual(core.section_url('ski'), 'ski/')

    def test_one_verb_per_kind_of_destination(self):
        html_ = ''.join(a11y.site_pages()[u] for u in a11y.site_pages() if u.endswith('/') or u == '')
        for old in ('View trip<', 'Read report<', 'Explore the journal', 'Read the series', 'View goal'):
            self.assertNotIn(old, html_, old)
        home = importlib_home()
        self.assertEqual(home.card_action({'kind': 'series', 'has_writeup': True}), 'Open the journal')
        self.assertEqual(home.card_action({'kind': 'trip', 'has_writeup': True}), 'Read the report')
        self.assertEqual(home.card_action({'kind': 'trip', 'has_writeup': False}), 'View the trip')

    def test_every_map_caption_item_starts_with_a_capital_or_a_digit(self):
        seen = 0
        for url in a11y.site_pages():
            if not url.endswith('/') and url:
                continue
            for cap in a11y.page_doc(url).find_all('p', cls='mapcap-t'):
                for mi in cap.find_all('span', cls='mi'):
                    text = helpers.plain_text(helpers.seen_text(mi))
                    if text:
                        seen += 1
                        self.assertRegex(text, r'^[A-Z0-9≈©]', (url, text))
        self.assertGreater(seen, 20)
        self.assertEqual((core.FULL_TRACK, core.FULL_TRACKS), ('Full track, not trimmed', 'Full tracks, not trimmed'))

    def test_the_empty_tick_list_and_the_footer_line(self):
        self.assertEqual(ticklist.EMPTY, 'Nothing on the list yet.')
        self.assertIn("all: 'Nothing on the list yet.'", a11y.source('js', 'pages', 'ticklist.js'))
        self.assertNotIn('ticklist.py add', a11y.source('js', 'pages', 'ticklist.js'))
        foot = a11y.page_doc('').find('footer', cls='site-f')
        self.assertIn('AVALANCHE TRAINING: AIARE 2', helpers.plain_text(foot.text()))


def importlib_home():
    import importlib
    return importlib.import_module('sitegen.pages.home')


if __name__ == '__main__':
    unittest.main()
