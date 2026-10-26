"""Phase 17 (docs/redesign-c/PROMPT.md 2.6, "Home"): what the new home page adds outside tests/test_home.py.

- The validator's note when the first featured trip has no photo (the home page then shows it as a title on white).
- core.trip_row(photo=True): the cover as a 4:3 thumbnail in the tile's place, its .th copy in a <source> of its own,
  the route tile when the trip has no photo; ROW_THUMB_SIZES; the wide list's rule in base.css.
- The By the numbers band: plain blocks with the counts as text, no script, the figures' links named by their words.
Synthetic trips only (helpers.make_trip).
"""
import json
import os
import re
import tempfile
import unittest

import helpers
from helpers import Doc, photo, LANDSCAPE

from sitegen import core
from sitegen.pages import home
import checks

tearDownModule = helpers.no_region_pages_left


def read(*parts):
    with open(os.path.join(helpers.ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


class HeroNoteTests(unittest.TestCase):

    def run_checks(self, first):
        with tempfile.TemporaryDirectory() as tmp:
            trips = os.path.join(tmp, 'trips')
            helpers.make_trip(trips, 'syn-photo', title='Synthetic Photo', activity='hike', date='2026-01-02', place='Synthetic Basin',
                              body='Synthetic words.', photos=[photo('photos/01.webp', LANDSCAPE, alt='A synthetic view')])
            # no track: an empty placeholder GPX would be an error, and a broken trip is a stand-in the note does not ask
            helpers.make_trip(trips, 'syn-bare', title='Synthetic Bare', activity='hike', date='2026-01-03', place='Synthetic Basin')
            home_json = os.path.join(tmp, 'home.json')
            with open(home_json, 'w', encoding='utf-8') as fh:
                json.dump({'featured_slugs': [first, 'syn-photo' if first == 'syn-bare' else 'syn-bare']}, fh)
            found = checks.run(trips, home_json, os.path.join(tmp, 'rendered'))
        return [f for f in found if f['file'] == 'content/home.json']

    def test_a_first_feature_without_a_photo_is_a_note(self):
        self.assertEqual(self.run_checks('syn-bare'), [{
            'level': 'note', 'file': 'content/home.json',
            'text': "content/home.json: the first of featured_slugs, 'syn-bare', has no photo, so the home page shows it as a title on "
                    'white, without the hero photo; give it a photo or put a trip that has one first'}])

    def test_a_first_feature_with_a_photo_says_nothing(self):
        self.assertEqual(self.run_checks('syn-photo'), [])         # the second one's lack of a photo is no matter


class RowThumbnailTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        helpers.make_trip(tmp.name, 'syn-row', title='Synthetic Row', activity='hike', date='2026-01-02', track=True,
                          photos=[photo('photos/01.webp', LANDSCAPE, alt='A synthetic view', sm=True)])
        helpers.touch(os.path.join(tmp.name, 'syn-row', 'photos', '01.th.webp'))
        helpers.make_trip(tmp.name, 'syn-bare', title='Synthetic Bare', activity='hike', date='2026-01-01', track=True)
        self.site = helpers.make_site(helpers.load_dir(tmp.name))
        self.by = self.site['by_slug']

    def test_the_cover_takes_the_tiles_place_with_its_copy_in_a_source(self):
        row = Doc(core.trip_row(self.by['syn-row'], '', ns='x-', photo=True))
        tile = row.find('div', cls='trow-tile')
        self.assertEqual((tile.classes, tile['aria-hidden']), (['trow-tile', 'trow-tile--photo'], 'true'))
        pic = tile.find('picture')
        source, img = pic.find('source'), pic.find('img')
        self.assertIsNone(source['media'])
        self.assertEqual(source['sizes'], core.ROW_THUMB_SIZES)
        self.assertTrue(source['srcset'].startswith('trips/syn-row/photos/01.th.webp 427w, '))
        self.assertNotIn('.th.', img['srcset'] + img['src'])        # no <img> names the copy (contract-phase4.md 10.5)
        self.assertEqual((img['sizes'], img['loading']), (core.ROW_THUMB_SIZES, 'lazy'))
        self.assertEqual(core.ROW_THUMB_SIZES, '(min-width: 760px) 132px, (min-width: 560px) 160px, 96px')

    def test_without_a_photo_the_row_keeps_its_route_tile_and_the_default_row_is_as_it_was(self):
        self.assertNotIn('trow-tile--photo', core.trip_row(self.by['syn-bare'], '', photo=True))
        for slug in ('syn-row', 'syn-bare'):
            self.assertEqual(core.trip_row(self.by[slug], '', photo=False), core.trip_row(self.by[slug], ''))
            self.assertNotIn('<picture', core.trip_row(self.by[slug], ''))

    def test_the_wide_list_puts_the_stats_at_the_right_from_1000(self):
        css = read('assets', 'css', 'base.css')
        # 760-999: the thumbnail beside the title, the stats under it (a stats column would leave the date line 116 px)
        mid = css.split('@media (min-width: 760px) {\n  .tlist--wide .trow-a', 1)[1].split('}\n}', 1)[0]
        self.assertIn('grid-template-columns: 132px minmax(0, 1fr);', mid)
        self.assertNotIn('trow-stats', mid)
        wide = css.split('@media (min-width: 1000px) {\n  .tlist--wide .trow-a', 1)[1].split('}\n}', 1)[0]
        self.assertIn('grid-template-columns: 132px minmax(0, 1fr) 384px;', wide)
        # the cells in 96 px columns from the right, so a row of three ends at the same edge as a row of four
        self.assertIn('.tlist--wide .trow-stats { grid-column: 3;', wide)
        self.assertIn('grid-auto-flow: column; grid-auto-columns: 96px; column-gap: 0; justify-content: end;', wide)
        self.assertIn('.trow-tile--photo { aspect-ratio: 4 / 3;', css)


class HeroSheetTests(unittest.TestCase):
    """The hero's rules the review of Phase 17 asked for (home.css)."""

    def setUp(self):
        self.css = read('assets', 'css', 'pages', 'home.css')

    def test_the_words_have_their_own_dark_ground_and_a_white_focus_ring(self):
        self.assertIn('rgba(17, 17, 17, 0.68) var(--hero-pt)', self.css)       # 6:1 and more for white over snow
        self.assertIn('.hom-hero-b { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; padding: var(--hero-pt) 0 28px; }', self.css)
        self.assertIn('.hom-hero:not(.hom-hero--plain) :focus-visible { outline-color: var(--on-photo); }', self.css)

    def test_the_plain_hero_wins_over_the_sizes_and_clips_nothing(self):
        plain = self.css.index('.hom-hero.hom-hero--plain { min-height: 0; overflow: visible;')
        self.assertGreater(plain, self.css.index('@media (min-width: 1200px) {\n  .hom-hero { min-height: 720px; }'))
        self.assertIn('.hom-hero--plain .hom-hero-f { background: none; }', self.css)

    def test_the_hero_says_gain_to_a_screen_reader(self):
        t = {'kind': 'trip', 'activity': 'hike', 'stats': {'distance_km': 10.0, 'gain_m': 900, 'moving_s': 3600}, 'route_shape': 'loop'}
        for caps in (True, False):
            self.assertIn('<span class="sr"> gain</span>', home.stat_items(t, caps=caps)[1])


class NumbersBandTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for i, (act, year) in enumerate((('ski', 2023), ('ski', 2025), ('hike', 2025), ('mtb', 2026))):
            helpers.make_trip(tmp.name, 'syn-n%d' % i, activity=act, date='%d-03-0%d' % (year, i + 1), track=True)
        self.site = helpers.make_site(helpers.load_dir(tmp.name))

    def test_a_year_without_a_report_has_a_bar_of_nothing_and_says_zero(self):
        doc = Doc(home.numbers(self.site))
        years = {int(li.find('span', cls='hom-yr-y').text()): li for li in doc.find_all('li', cls='hom-yr')}
        self.assertEqual(sorted(years), [2023, 2024, 2025, 2026])
        self.assertEqual(years[2024].find('span', cls='hom-yr-n').text(), '2024: 0 reports')
        self.assertIn('height:0px', years[2024].find('span', cls='hom-yr-b')['style'])
        self.assertEqual(years[2025].find('span', cls='hom-yr-n').text(), '2025: 2 reports')
        self.assertEqual(years[2023].find('span', cls='hom-yr-n').text(), '2023: 1 report')
        self.assertIn('height:%dpx' % home.BAR_MAX, years[2025].find('span', cls='hom-yr-b')['style'])

    def test_no_script_and_no_series_sentence_without_a_journal(self):
        html_ = home.numbers(self.site)
        self.assertNotIn('<script', html_)
        self.assertIsNone(Doc(html_).find('p', cls='hom-years-n'))
        self.assertEqual(home.series_line(self.site), '')
        # the figures: the total to trips/, then each activity most reports first, ties in core.NAV's order
        figs = Doc(html_).find_all('a', cls='hom-fig')
        self.assertEqual([(a['href'], a.find('span', cls='hom-fig-n').text()) for a in figs],
                         [('trips/', '4'), ('ski/', '2'), ('hiking/', '1'), ('mountain-biking/', '1'), ('climbing/', '0'), ('other/', '0')])
        self.assertEqual(re.sub(r'\s+', ' ', figs[1].text()).strip(), '2Backcountry Skiing reports')


if __name__ == '__main__':
    unittest.main()
