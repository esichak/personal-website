"""Phase 18 (docs/redesign-c/PROMPT.md 2.6, "Single-day reports", "Multi-day trips"): what the report pages add outside
tests/test_report_page.py.

- report.head_line: the sans line under the title (date, place and region, party), and a goal's approximate distance.
- report.lead_paragraph: the first <p> of a write-up as the lead, the words untouched.
- report.hero_head: the words over the photo first in the markup, the caption under the frame, the chips and actions
  under it; title_block's new order (crumbs, title, line, chips, ask, actions).
- The sheets: the hero frame, the Beta list, 'More like this' as 4:5 cards (core.REL_SIZES), the full-screen bar, the
  multi-day day bar as underline tabs and the serif day titles and numbers.
Synthetic trips only (helpers.make_trip).
"""
import os
import re
import tempfile
import unittest

import helpers
from helpers import Doc, photo, LANDSCAPE, PORTRAIT

from sitegen import core
from sitegen.pages import report, multiday
import markdown

tearDownModule = helpers.no_region_pages_left

WRITEUP = ('First synthetic paragraph, long enough to be a written report on its own: a ridge, a col and a descent.\n\n'
           'Second synthetic paragraph with *emphasis* and a [link](https://example.com/).')


def read(*parts):
    with open(os.path.join(helpers.ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


def text(html_):
    return re.sub(r'\s+', ' ', Doc(html_).root.text()).strip()


class Fixture(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        helpers.make_trip(self.tmp, 'syn-wide', title='Synthetic Wide Couloir', activity='ski', date='2026-01-17',
                          place='Synthetic Ridge', region='Synthetic Range', party='Sam', body=WRITEUP, track=True,
                          photos=[photo('photos/01.webp', LANDSCAPE, alt='A synthetic ridge', caption='Synthetic caption')])
        helpers.make_trip(self.tmp, 'syn-tall', title='Synthetic Tall', activity='climb', date='2026-01-10',
                          region='Synthetic Range', body=WRITEUP, track=True,
                          photos=[photo('photos/01.webp', PORTRAIT, alt='A synthetic wall'),
                                  photo('photos/02.webp', PORTRAIT, alt='A synthetic pitch')])
        helpers.make_trip(self.tmp, 'syn-same', title='Synthetic Same', activity='hike', date='2026-01-05',
                          place='Synthetic Range', region='Synthetic Range', track=True)
        helpers.make_trip(self.tmp, 'syn-tour', title='Synthetic Tour', activity='ski', kind='multi-day', date='2026-02-01',
                          end_date='2026-02-02', region='Synthetic Range', body=WRITEUP,
                          photos=[photo('photos/01.webp', LANDSCAPE, alt='A synthetic hut')],
                          days=[{'date': '2026-02-01', 'title': 'Synthetic Col'}, {'date': '2026-02-02', 'title': 'Synthetic Pass'}])
        self.site = helpers.make_site(helpers.load_dir(self.tmp))
        self.by = self.site['by_slug']


class HeadLineTests(Fixture):

    def test_the_line_is_date_place_region_and_party_in_the_sans(self):
        t = self.by['syn-wide']
        line = Doc(report.head_line(t, t['url']))
        items = [re.sub(r'^, ', '', m.text()) for m in line.find_all('span', cls='mi')]
        self.assertEqual(items, ['Sat, Jan 17, 2026', 'Synthetic Ridge, Synthetic Range', 'with Sam'])
        self.assertEqual(line.find('span', cls='rep-pdate').text(), 'Sat, Jan 17, 2026')
        # the region is a link where the breadcrumb's is (core.region_link); this fixture has no region page and no
        # region map, so it is text, as in the breadcrumb
        href = core.region_link(t['url'], 'Synthetic Range')
        a = line.find('a', cls='mi-a')
        self.assertEqual(a['href'] if a else None, href)

    def test_a_place_that_is_its_region_is_said_once(self):
        t = self.by['syn-same']
        items = [re.sub(r'^, ', '', m.text()) for m in Doc(report.head_line(t, t['url'])).find_all('span', cls='mi')]
        self.assertEqual(items[1:], ['Synthetic Range'])

    def test_a_goal_states_its_approximate_distance_unless_its_strip_does(self):
        t = dict(self.by['syn-same'], kind='planned', stats=dict(self.by['syn-same']['stats'] or {}, distance_km=28.0))
        line = report.head_line(t, t['url'])
        self.assertIn('≈ 17.4', text(line))
        self.assertNotIn('MI', text(line))                              # the line's case, not the strip's caps
        self.assertNotIn('≈', report.head_line(t, t['url'], strip_follows=True))


class LeadParagraphTests(unittest.TestCase):

    def test_the_first_paragraph_gets_the_class_and_nothing_else_changes(self):
        raw = markdown.to_html(WRITEUP)
        out = report.lead_paragraph(raw)
        self.assertEqual(out.count('<p class="t-lede">'), 1)
        self.assertTrue(out.startswith('<p class="t-lede">First synthetic paragraph'))
        self.assertEqual(out.replace(' class="t-lede"', '', 1), raw)
        self.assertEqual(text(out), text(raw))

    def test_a_write_up_without_a_paragraph_is_untouched(self):
        self.assertEqual(report.lead_paragraph(''), '')
        self.assertEqual(report.lead_paragraph('<ul><li>One</li></ul>'), '<ul><li>One</li></ul>')


class HeadTests(Fixture):

    def head(self, slug):
        page = report.page(self.by[slug], self.site) if self.by[slug]['kind'] == 'trip' else multiday.page(self.by[slug], self.site)
        return Doc(page.html).by_id('main').find('section', cls='rep-title')

    def test_the_hero_head_puts_the_words_first_and_the_caption_under_the_frame(self):
        head = self.head('syn-wide')
        self.assertEqual(head.classes, ['rep-title', 'rep-title--hero'])
        frame, cap, under = head.elements()
        self.assertEqual((frame.classes, cap.classes, under.classes),
                         (['rep-hero-frame'], ['wrap', 't-small', 'rep-hero-cap'], ['wrap', 'rep-hero-under']))
        words, fig = frame.elements()
        self.assertEqual(words.classes, ['rep-hero-b'])
        self.assertEqual([e.tag for e in words.elements()[0].elements()], ['nav', 'h1', 'p'])
        self.assertEqual((fig.tag, fig['id'], fig.classes), ('figure', 'hero', ['rep-hero', 'rep-hero--full']))
        self.assertEqual(cap.text(), 'Synthetic caption')
        self.assertIsNone(fig.find('figcaption'))
        # under the frame: the chip and tags, the ask, the actions (View route, Download GPX, Copy link)
        self.assertIsNotNone(under.find('a', cls='chip--title'))
        self.assertEqual([a.text().strip() for a in under.find('div', cls='rep-actions').find_all('a')], ['View route', 'Download GPX'])

    def test_a_portrait_cover_keeps_the_head_on_white_in_the_new_order(self):
        head = self.head('syn-tall')
        self.assertEqual(head.classes, ['rep-title', 'wrap'])
        self.assertIsNone(head.find('figure'))
        crumbs, row = head.elements()
        self.assertEqual(crumbs.tag, 'nav')
        left, actions = row.elements()
        # 'Ask about this trip' comes last when content/author.json gives a contact (this fixture has none)
        self.assertEqual([(e.tag, e['class']) for e in left.elements()][:3],
                         [('h1', 't-d1'), ('p', 'rep-place'), ('div', 'chips rep-chips')])
        self.assertEqual(actions.classes, ['rep-actions'])

    def test_the_write_up_leads_with_its_first_paragraph(self):
        for slug, sel in (('syn-wide', 'prose'), ('syn-tour', 'mul-ov-p')):
            with self.subTest(slug):
                page = report.page(self.by[slug], self.site) if slug == 'syn-wide' else multiday.page(self.by[slug], self.site)
                prose = Doc(page.html).find('div', cls=sel)
                self.assertEqual(prose.find('p')['class'], 't-lede')
                self.assertEqual(len(prose.find_all('p', cls='t-lede')), 1)

    def test_a_multi_day_trip_with_a_landscape_cover_has_the_hero_head(self):
        head = self.head('syn-tour')
        self.assertEqual(head.classes, ['rep-title', 'rep-title--hero'])
        self.assertEqual(head.find('a', cls='rep-hero-a').find_all('span', cls='rep-anchor'), [])
        self.assertIn('Day by day', head.find('div', cls='rep-actions').text())


class SheetTests(unittest.TestCase):

    def setUp(self):
        self.rep = read('assets', 'css', 'pages', 'report.css')
        self.mul = read('assets', 'css', 'pages', 'multiday.css')
        self.base = read('assets', 'css', 'base.css')

    def test_the_hero_frame(self):
        self.assertIn('.rep-hero-frame { position: relative; display: flex; flex-direction: column; justify-content: flex-end; min-height: 500px;', self.rep)
        self.assertIn('  .rep-hero-frame { min-height: min(72vh, 820px); }', self.rep)
        self.assertIn('rgba(17, 17, 17, 0.68) var(--hero-pt)', self.rep)
        self.assertIn('.rep-hero-b { --hero-pt: 96px; position: relative; z-index: 1; pointer-events: none;', self.rep)
        self.assertIn('.rep-hero-b a { pointer-events: auto; }', self.rep)
        self.assertIn('.rep-hero-b :focus-visible { outline-color: var(--on-photo); }', self.rep)
        # the old date slot's rules are gone with it
        self.assertNotIn('.rep-pdate', self.rep)

    def test_the_beta_list_and_the_related_cards(self):
        self.assertIn(':is(.rail-b, .goal-sec) .dl-leader div { display: grid; grid-template-columns: 110px minmax(0, 1fr);', self.rep)
        self.assertIn('  .rep-rel .tcard-img { aspect-ratio: 4 / 5; }', self.rep)
        self.assertIn('  .rep-rel .tcard-t { font-size: 22px; line-height: 1.1; }', self.rep)
        self.assertTrue(core.REL_SIZES.endswith(', ' + core.CARD_PHONE_SLOT))
        self.assertTrue(core.REL_SIZES.startswith('(min-width: 1200px) 730px, (min-width: 760px) '))
        # two across at 560-759 px (the third waits), three from 760 px
        self.assertIn('@media (min-width: 560px) and (max-width: 759.98px) { .rep-rel > li:nth-child(n+3) { display: none; } }', self.rep)
        self.assertIn('@media (min-width: 760px) { .rep-rel { margin-top: 24px; grid-template-columns: repeat(3, minmax(0, 1fr)); } }', self.rep)

    def test_the_photos_ring_and_short_windows(self):
        # the ring is drawn over the words' band, and lets a press through to the words' links
        self.assertIn('.rep-hero--full .rep-hero-a:focus-visible::after { content: ""; position: absolute; z-index: 2; inset: 6px; pointer-events: none;', self.rep)
        # a short phone keeps the date line above the bottom bar; a short window's band is shallower
        self.assertIn('  .rep-hero-frame { min-height: min(500px, calc(100svh - var(--header-h) - 96px)); }', self.rep)
        self.assertIn('@media (max-height: 700px) {\n  .rep-hero-b { --hero-pt: 64px; }\n  .rep-hero-bi { padding-top: 64px; padding-bottom: 24px; }\n}', self.rep)
        self.assertGreater(self.rep.index('@media (max-height: 700px) {'), self.rep.index('.rep-hero-bi { padding-top: 128px;'))
        # the multi-day rail's GPX button stays in view down to 620 px of height (gap2-03) with the serif title
        short = self.mul.split('@media (min-width: 1000px) and (max-height: 719.98px) {', 1)[1].split('\n}', 1)[0]
        self.assertIn('  .mul-dtitle { font-size: 22px; }', short)
        # the strip after a head over a photo keeps its spacing
        self.assertIn('.p-report--story .rep-strip, .rep-title--hero ~ .rep-strip { margin-top: 24px; }', self.rep)
        self.assertNotIn('.rep-hero + .rep-strip', self.rep)

    def test_the_head_prints_in_ink_on_white_with_the_photo_under_it(self):
        css = read('assets', 'css', 'print.css')
        self.assertIn('.rep-hero-frame { display: block; min-height: 0; overflow: visible; background: none; }', css)
        self.assertIn('.rep-hero-b { background: none; color: #000; }', css)
        self.assertIn('.rep-hero.rep-hero--full, .rep-hero--full .rep-hero-a { position: static; }', css)

    def test_the_full_screen_bar_and_the_day_bar(self):
        self.assertIn('.fs-pan, .fs-nav { font: 500 12px/16px var(--sans); letter-spacing: 0.12em; text-transform: uppercase; }', self.base)
        self.assertNotIn('.mul-dn-i + .mul-dn-i { border-left: 1px solid var(--rule); }', self.mul)
        self.assertIn('.mul-dn-date { font: 400 12px/16px var(--mono); letter-spacing: 0.06em; text-transform: uppercase;', self.mul)
        self.assertIn('.mul-num { flex-shrink: 0; font: 400 64px/56px var(--serif);', self.mul)
        self.assertIn('.mul-dtitle { font: 400 26px/1.1 var(--serif);', self.mul)
        self.assertIn('.mul-sp .sp-c path { stroke: var(--ink) !important; }', self.mul)


if __name__ == '__main__':
    unittest.main()
