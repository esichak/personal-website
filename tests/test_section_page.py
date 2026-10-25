"""Phase 13B (visual-11): the section pages' lists name their stat columns once per group.

From 760 px a ski season, a year of Hiking or Mountain biking, or a flat list (Climbing; Hiking's planned routes)
shows its rows' stat labels once, under its heading and lined up with the rows' stat columns, and every row keeps its
own labels for screen readers only. The labels come from the rows (core.group_stat_labels): shown only when every
row's labels are a start of the longest row's. The Other page keeps each row's labels (flat water beside the rest).
Synthetic trips with front-matter stats; the cascade is read with tests/test_a11y_static.py's evaluator.
"""
import importlib
import tempfile
import unittest

import helpers
from helpers import Doc

import test_a11y_static as a11y
from sitegen import core

tearDownModule = helpers.no_region_pages_left

SKI = {'distance_km': 12.0, 'gain_m': 900, 'high_m': 2900, 'moving': '4:00'}
CLIMB = {'distance_km': 4.0, 'high_m': 2400, 'moving': '2:00'}
PLAN = {'distance_km': 9.0}


class Fixture(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        mk = lambda slug, **kw: helpers.make_trip(tmp.name, slug, track=True, **kw)  # noqa: E731
        mk('syn-s-a', title='Synthetic Ski A', activity='ski', date='2026-01-10', stats=SKI, body='Synthetic words.')
        mk('syn-s-b', title='Synthetic Ski B', activity='ski', date='2025-12-20', stats=SKI)
        mk('syn-s-c', title='Synthetic Ski C', activity='ski', date='2024-02-02', stats=SKI)
        mk('syn-c-a', title='Synthetic Climb A', activity='climb', date='2025-07-01', stats=CLIMB)
        mk('syn-c-b', title='Synthetic Climb B', activity='climb', date='2024-07-01', stats=CLIMB)
        mk('syn-h-a', title='Synthetic Hike A', activity='hike', date='2025-06-01', stats=SKI)
        mk('syn-h-plan', title='Synthetic Hike Plan', activity='hike', kind='planned', stats=PLAN)
        mk('syn-o-sup', title='Synthetic Paddle', activity='other', subtype='SUP', date='2025-08-01', stats={'distance_km': 5.0, 'moving': '1:00'})
        mk('syn-o-run', title='Synthetic Other', activity='other', date='2025-05-01', stats=SKI)
        self.trips = helpers.load_dir(tmp.name)
        self.site = helpers.make_site(self.trips)
        self.by = self.site['by_slug']
        self.section = importlib.import_module('sitegen.pages.section')

    def page(self, act):
        return Doc(self.section.page(act, self.site).html)


class LabelTests(Fixture):

    def test_a_group_shares_its_rows_labels_when_each_row_starts_like_the_longest(self):
        labels = core.group_stat_labels
        self.assertEqual(labels([self.by['syn-s-a'], self.by['syn-s-b']]), ['Dist', 'Gain', 'GPS max', 'Moving'])
        self.assertEqual(labels([self.by['syn-c-a'], self.by['syn-c-b']]), ['Dist', 'GPS max', 'Moving'])
        # a planned route's lone Dist lines up under Dist
        self.assertEqual(core.stats_labels(self.by['syn-h-plan']), ['Dist'])
        self.assertEqual(labels([self.by['syn-h-a'], self.by['syn-h-plan']]), ['Dist', 'Gain', 'GPS max', 'Moving'])
        # rows that disagree share nothing: climbs (no Gain) beside skis, flat water beside the rest
        self.assertIsNone(labels([self.by['syn-s-a'], self.by['syn-c-a']]))
        self.assertIsNone(labels([self.by['syn-o-sup'], self.by['syn-o-run']]))
        self.assertIsNone(labels([]))
        self.assertIsNone(labels([dict(self.by['syn-s-a'], stats={})]))
        # the labels are those of the row's own cells, in their order
        self.assertEqual(core.stats_labels(self.by['syn-s-a']),
                         [dt.text() for dt in Doc('<dl>%s</dl>' % core.stats_cells(self.by['syn-s-a'])).find_all('dt')])


class MarkupTests(Fixture):

    def cols(self, node):
        return [s.text() for s in node.find('div', cls='sec-cols').find_all('span')]

    def test_each_ski_season_has_its_column_header_and_its_rows_keep_their_labels(self):
        doc = self.page('ski')
        seasons = [s for s in doc.find_all('section') if 'sec-season' in s.classes]
        self.assertEqual(len(seasons), 2)
        for s in seasons:
            with self.subTest(s['id']):
                self.assertIn('sec--cols', s.classes)
                head = s.find('div', cls='sec-div')
                cols = head.find('div', cls='sec-cols')
                self.assertEqual((cols['aria-hidden'], cols.classes), ('true', ['sec-cols', 't-label']))
                self.assertEqual(self.cols(head), ['Dist', 'Gain', 'GPS max', 'Moving'])
                for row in s.find_all('li', cls='trow'):
                    self.assertEqual([dt.text() for dt in row.find_all('dt')], ['Dist', 'Gain', 'GPS max', 'Moving'])

    def test_a_flat_list_has_its_header_under_the_head_and_other_has_none(self):
        doc = self.page('climb')
        sec = next(s for s in doc.find_all('section') if 'sec-more' in s.classes)
        self.assertIn('sec--cols', sec.classes)
        row = sec.find('div', cls='sec-colrow')
        self.assertEqual(row['aria-hidden'], 'true')
        self.assertEqual(self.cols(row), ['Dist', 'GPS max', 'Moving'])
        other = self.page('other')
        self.assertEqual(other.find_all(cls='sec-cols'), [])
        self.assertEqual([s for s in other.find_all('section') if 'sec--cols' in s.classes], [])
        # Hiking's planned routes: their own block, headed by the one label they have
        hike = self.page('hike')
        block = next(s for s in hike.find_all('section') if s['aria-labelledby'] == 'planned-h')
        self.assertEqual(self.cols(block.find('div', cls='sec-colrow')), ['Dist'])


class HeadingTests(Fixture):

    def test_rows_under_a_year_are_one_level_under_its_heading(self):
        # Phase 13C (a11y-08): Hiking and Mountain biking group a long list by year (section.year_groups, an H3 per year);
        # each row's title is then an H4 with the H3's look, and a list that is not grouped keeps H3 rows
        doc = Doc(self.section.year_groups([self.by['syn-h-a'], self.by['syn-s-b'], self.by['syn-s-c']], 'hiking/'))
        years = [h.tag for h in doc.find_all(cls='sec-div-t')]
        self.assertGreater(len(years), 1)
        self.assertEqual(set(years), {'h3'})
        rows = doc.find_all(cls='trow-t')
        self.assertEqual([(h.tag, h.classes) for h in rows], [('h4', ['t-h3', 'trow-t'])] * 3)
        climb = self.page('climb').find_all(cls='trow-t')
        self.assertTrue(climb)
        self.assertEqual({h.tag for h in climb}, {'h3'})


class CascadeTests(Fixture):

    def test_from_760_the_header_shows_and_the_rows_labels_go_to_screen_readers(self):
        rules = a11y.published_rules()[0]
        doc = self.page('ski')
        season = next(s for s in doc.find_all('section') if 'sec--cols' in s.classes)
        cols, dt = season.find('div', cls='sec-cols'), season.find('dt')
        for w, shown, pad, sr in ((390, False, None, False), (759, False, None, False), (800, True, '224px', True),
                                  (1000, False, None, False), (1100, True, '180px', True), (1200, True, '180px', True),
                                  (1440, True, '224px', True)):
            e = a11y.env(w)
            with self.subTest(width=w):
                self.assertEqual(a11y.displayed(cols, rules, e), shown, a11y.why(cols, 'display', rules, e))
                if shown:
                    self.assertEqual(a11y.computed(cols, 'padding-left', rules, e), pad)
                    self.assertEqual(a11y.computed(cols, 'grid-template-columns', rules, e), 'repeat(4, minmax(0, 120px))')
                self.assertEqual(a11y.computed(dt, 'position', rules, e) == 'absolute', sr, a11y.why(dt, 'position', rules, e))
                # under 560 px the row shows its stats line instead of the cells (base.css); from there the label is read out
                self.assertEqual(a11y.displayed(dt, rules, e), w >= 560)
        # a list that is not the Ski list keeps its header at 960-1099 px, where only the Ski list's cells go two by two
        climb = next(s for s in self.page('climb').find_all('section') if 'sec--cols' in s.classes)
        self.assertTrue(a11y.displayed(climb.find('div', cls='sec-cols'), rules, a11y.env(1000)))
        self.assertEqual(a11y.computed(climb.find('dt'), 'position', rules, a11y.env(1000)), 'absolute')


if __name__ == '__main__':
    unittest.main()
