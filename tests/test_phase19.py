"""Phase 19 (docs/redesign-c/PROMPT.md 2.6, "The Trips explorer" to "404"): what the list pages and the rest add outside
the page modules' own tests.

- The journal opens like a report: report.hero_head over its lead photo, the photo inside the head.
- The heads of the section pages, the region pages and map/ are t-d2; the Trips page, the tick list, About and the 404
  keep t-d1.
- The sheets: the bare search boxes and selects, the underline tabs (the view switch, the section band, the month bar),
  the serif heads and titles, About's mono values, the section Featured block from 1200 px, the rows' tiles.
Synthetic trips only (helpers.make_trip, helpers.make_series).
"""
import os
import re
import tempfile
import unittest

import helpers
from helpers import Doc

from sitegen import core
from sitegen.pages import series, report

tearDownModule = helpers.no_region_pages_left


def read(*parts):
    with open(os.path.join(helpers.ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


class JournalHeadTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        helpers.make_series(tmp.name, 'syn-journal', title='Synthetic Journal 2024')
        self.site = helpers.make_site(helpers.load_dir(tmp.name))
        self.t = self.site['by_slug']['syn-journal']

    def test_a_journal_with_a_landscape_cover_opens_like_a_report(self):
        self.assertIsNotNone(report.lead_photo(self.t))
        main = Doc(series.page(self.t, self.site).html).by_id('main')
        head = main.find('section', cls='rep-title')
        self.assertEqual(head.classes, ['rep-title', 'rep-title--hero'])
        fig = head.find('figure', cls='rep-hero')
        self.assertEqual((fig['id'], fig.classes), ('hero', ['rep-hero', 'rep-hero--full']))
        self.assertIs(fig.parent, head.find('div', cls='rep-hero-frame'))
        self.assertEqual(len(main.find_all('figure', cls='rep-hero')), 1)      # no second, framed lead photo under it
        # the three actions under the frame, the journal's own
        acts = head.find('div', cls='rep-actions').text()
        for words in ('Read the first written entry', 'Browse all recordings'):
            self.assertIn(words, acts)

    def test_a_journal_without_a_lead_photo_keeps_its_head_on_white(self):
        t = dict(self.t, cover=None)
        head = Doc(series.page(t, self.site).html).by_id('main').find('section', cls='rep-title')
        self.assertEqual(head.classes, ['rep-title', 'wrap'])
        self.assertIsNone(head.find('figure'))


class HeadClassTests(unittest.TestCase):

    def test_the_index_heads_are_t_d2_and_the_others_t_d1(self):
        for mod, h1 in (('section', '<h1 id="sec-title" class="t-d2">'), ('region', '<h1 id="reg-title" class="t-d2">'),
                        ('archive', '<h1 id="arc-title" class="t-d2">'), ('trips', '<h1 id="trips-title" class="t-d1">'),
                        ('ticklist', '<h1 id="tkl-title" class="t-d1">'), ('notfound', '<h1 class="t-d1 nf-h">'),
                        ('about', '<h1 class="t-d1">')):
            self.assertIn(h1, read('tools', 'sitegen', 'pages', mod + '.py'), mod)


class SheetTests(unittest.TestCase):

    def setUp(self):
        self.css = {n: read('assets', 'css', 'pages', n + '.css') for n in
                    ('trips', 'section', 'region', 'archive', 'ticklist', 'series', 'about', 'notfound')}
        self.base = read('assets', 'css', 'base.css')

    def test_the_search_boxes_and_selects_are_bare(self):
        self.assertIn('border: 0; border-bottom: 1px solid var(--ink); border-radius: 0; background: none;', self.css['trips'].split('.trx-q {', 1)[1].split('}', 1)[0])
        self.assertIn('border: 0; border-bottom: 1px solid var(--ink); border-radius: 0; background: transparent', self.css['trips'])
        self.assertIn('border: 0; border-bottom: 1px solid var(--ink); border-radius: 0;', self.css['notfound'].split('.nf-q {', 1)[1].split('}', 1)[0])

    def test_rows_of_choices_are_underline_tabs_in_mono_capitals(self):
        view = self.css['trips'].split('.trx-view button {', 1)[1].split('}', 1)[0]
        self.assertIn('font: 400 12px/16px var(--mono); letter-spacing: 0.1em; text-transform: uppercase;', view)
        self.assertIn('.trx-view button[aria-checked="true"] { background: none; color: var(--ink); box-shadow: inset 0 -2px 0 var(--ink); }', self.css['trips'])
        seg = self.css['section'].split('.sec-seg-a { position: relative;', 1)[1].split('}', 1)[0]
        self.assertIn('font: 400 12px/16px var(--mono); letter-spacing: 0.1em; text-transform: uppercase;', seg)
        self.assertIn('.sec-seg-a:is([aria-checked="true"], [aria-current="true"]) { color: var(--ink); box-shadow: inset 0 -2px 0 var(--ink); }', self.css['section'])
        self.assertIn('.ser-mn-m { font: 400 12px/16px var(--mono); letter-spacing: 0.1em; text-transform: uppercase; }', self.css['series'])
        self.assertNotIn('.ser-mnav li + li { border-left', self.css['series'])

    def test_heads_and_titles_are_in_the_serif(self):
        for sheet, rule in (('trips', '.p-trips .trx-yr-h h2 { font: 400 32px/1.05 var(--serif);'),
                            ('trips', '.trx-day-t { font: 400 22px/1.15 var(--serif);'),
                            ('section', '.sec-div-t { font: 400 26px/1.05 var(--serif);'),
                            ('section', '.sec-panel-h { margin-bottom: 8px; font: 400 26px/1.1 var(--serif);'),
                            ('region', '.reg-intro h2, .reg-intro h3 { font: 400 28px/1.1 var(--serif);'),
                            ('archive', '.arc-row-t { font: 400 20px/1.15 var(--serif);'),
                            ('archive', '.arc-series-t { font: 400 26px/1.1 var(--serif);'),
                            ('archive', '.p-archive .arc-yr-h h3, .p-region .arc-yr-h h3 { font: 400 26px/1.05 var(--serif);'),
                            ('ticklist', '.gcard-t { margin-top: 6px; font: 400 22px/1.1 var(--serif);'),
                            ('series', '.ser-mh-t { font: 400 32px/1.05 var(--serif);'),
                            ('series', '.ser-t { grid-area: t; font: 400 22px/1.15 var(--serif);'),
                            ('series', '.ser-high-t { font: 400 26px/1.1 var(--serif);'),
                            ('series', '.ser-mi-m { font: 400 24px/1.1 var(--serif);'),
                            ('about', '.abo-act-n { font: 400 22px/1.1 var(--serif);')):
            self.assertIn(rule, self.css[sheet], sheet)
        # no page sheet keeps Datum's bold stretched sans for a head
        for name, css in self.css.items():
            self.assertNotIn('font-stretch: 108%', css, name)

    def test_about_glance_values_are_mono_and_the_journal_lede_a_dek(self):
        self.assertIn('.abo-glance .dl-leader dd { font: 400 15px/24px var(--mono); }', self.css['about'])
        self.assertIn('.ser-lede { margin-top: 20px; max-width: 600px; font: 400 16px/1.5 var(--sans); color: var(--ink-2); }', self.css['series'])

    def test_the_featured_block_is_a_photo_card_beside_a_map_panel_from_1200(self):
        wide = self.css['section'].split("@media (min-width: 1200px) {\n  /* the map column's parts", 1)[1].split('\n}', 1)[0]
        self.assertIn('.sec-feat-side { grid-column: 1 / span 8; grid-row: 1 / span 4; display: block; }', wide)
        # the map column's parts join the grid: the map, its key and caption in the last third, the chart under the card
        self.assertIn('.sec-feat-map { display: contents; }', wide)
        self.assertIn('.sec-feat-map > * { grid-column: 9 / span 4; min-width: 0; }', wide)
        self.assertIn('.sec-feat-map > .sec-prof { grid-column: 1 / span 8; grid-row: 5; margin-top: 48px; }', wide)
        self.assertIn('.sec-feat-map .mv--phone { display: block; }', wide)
        # the key is the phone render's, the render shown there
        self.assertIn('.sec-feat-map .keyrow--d { display: none; }', wide)
        self.assertIn('.sec-feat-map .keyrow--p { display: flex; }', wide)
        # the photo's sizes follow its slot (739 px at 1200, 899 at 1440); each map render is preloaded where it shows
        from sitegen.pages import section
        self.assertEqual(section.FEAT_SIZES, '(min-width: 1440px) 899px, (min-width: 1200px) calc((100vw - 80px) * 0.667 - 8px), '
                                             '(min-width: 760px) 50vw, ' + core.PHONE_FULL)
        self.assertEqual(section.FEAT_MAP_MEDIA, {'col': '(min-width: 560px) and (max-width: 1199.98px)',
                                                  'phone': '(max-width: 559.98px), (min-width: 1200px)'})
        self.assertNotIn('.photo + .photo', self.css['section'])                  # one photo, in the markup too

    def test_the_bands_focus_ring_and_first_tab_are_not_clipped(self):
        self.assertIn('.sec-seg-a:focus-visible { outline-offset: -2px; }', self.css['section'])
        self.assertIn('  .sec-band-in { width: min(1400px, 100% - 2 * var(--m) + 40px); padding-inline: 20px; scroll-padding-inline: 20px; }',
                      self.css['section'])

    def test_the_region_heads_links_and_the_legend_lie_above_the_maps_lines(self):
        # the review gate of 2026-10-26: a map line that runs off the map (the journal's on Eastern Sierra) has a box
        # reaching over the head's activity links and the legend, and a tester counted them covered (target-size)
        self.assertIn('.reg-acts { position: relative; z-index: 1;', self.css['region'])
        self.assertIn('.arc-legend { position: relative; z-index: 1;', self.css['archive'])

    def test_a_rows_tile_keeps_its_own_height(self):
        self.assertIn('.trow-tile { width: 160px; align-self: start; }', self.base)


if __name__ == '__main__':
    unittest.main()
