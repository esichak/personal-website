"""Phase 1: card summary resolution and provenance (sitegen.core.card_summary)."""
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import markdown  # noqa: E402
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import PCT_PROSE, photo, LANDSCAPE  # noqa: E402

KEYS = {'text', 'source_kind', 'source_label'}
FIRST_PERSON = re.compile(r"\b(I|I'm|my|we|our)\b")
LONG_BODY = ('We **skinned** up the [west couloir](https://example.com/couloir) before dawn and found firm, '
             'edgeable snow all the way to the notch. ' * 3).strip()
DAY_PROSE = 'Climbed over the pass in a cold wind and camped by the first lake on the far side.'


class CardSummaryTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def trip(self, slug='trip', **kw):
        helpers.make_trip(self.tmp, slug, **kw)
        return helpers.load(self.tmp, slug)

    def series(self, slug='journal', **kw):
        helpers.make_series(self.tmp, slug, **kw)
        return helpers.load(self.tmp, slug)

    def multiday(self, slug='multi', days=None, **kw):
        days = days if days is not None else [{}, {}, {}]
        meta = dict(activity='hike', kind='multi-day', date='2024-01-16', end_date='2024-01-18')
        meta.update(kw)
        return self.trip(slug, days=days, **meta)

    # ------------------------------------------------------------ 1. explicit

    def test_explicit_card_summary_wins_verbatim_without_truncation(self):
        text = ('A factual summary of the ski tour up the west couloir, written from the report itself. ' * 3).strip()
        self.assertGreater(len(text), 180)
        t = self.trip(body=LONG_BODY, card_summary=text)
        r = core.card_summary(t)
        self.assertEqual(set(r), KEYS)
        self.assertEqual(r, {'text': text, 'source_kind': 'explicit', 'source_label': ''})
        self.assertEqual(core.card_summary(t, limit=20)['text'], text)

    def test_explicit_card_summary_wins_on_a_series_and_a_multi_day(self):
        s = self.series(slug='explicit-series', card_summary='A thru-hike journal kept by day.')
        r = core.card_summary(s)
        self.assertEqual((r['source_kind'], r['text'], r['source_label']), ('explicit', 'A thru-hike journal kept by day.', ''))
        self.assertNotIn(PCT_PROSE, r['text'])
        m = self.multiday(slug='explicit-multi', days=[{}, {'body': DAY_PROSE}], card_summary='Two days on the hut route.')
        self.assertEqual(core.card_summary(m)['source_kind'], 'explicit')
        self.assertEqual(core.card_summary(m)['text'], 'Two days on the hut route.')

    # ------------------------------------------------------------ 2. report

    def test_writeup_gives_report_kind_with_plain_excerpt_respecting_limit(self):
        t = self.trip(body=LONG_BODY)
        r = core.card_summary(t)
        self.assertEqual(set(r), KEYS)
        self.assertEqual(r['source_kind'], 'report')
        self.assertEqual(r['source_label'], '')
        self.assertEqual(r['text'], markdown.plain(t['body_md'], 180))
        self.assertLessEqual(len(r['text']), 181)        # <= limit characters plus the ellipsis
        self.assertTrue(r['text'].endswith('…'))
        self.assertNotIn('**', r['text'])
        self.assertNotIn('](', r['text'])
        self.assertTrue(r['text'].startswith('We skinned up the west couloir'))
        short = core.card_summary(t, limit=40)
        self.assertEqual(short['text'], markdown.plain(t['body_md'], 40))
        self.assertLessEqual(len(short['text']), 41)

    def test_short_writeup_is_returned_whole(self):
        t = self.trip(body='Quick lap before work.')
        r = core.card_summary(t)
        self.assertEqual((r['source_kind'], r['text']), ('report', 'Quick lap before work.'))

    def test_parent_writeup_beats_written_days(self):
        t = self.multiday(days=[{'body': DAY_PROSE}, {}], body='Three days on the Haute Route.')
        r = core.card_summary(t)
        self.assertEqual((r['source_kind'], r['text'], r['source_label']), ('report', 'Three days on the Haute Route.', ''))

    # ------------------------------------------------------------ 3. labelled day

    def test_multiday_with_writing_only_on_a_day_gives_labelled_day_excerpt(self):
        days = [{'title': 'Approach'}, {'title': 'Forester Pass', 'body': DAY_PROSE}, {'title': 'Out'}]
        t = self.multiday(days=days)
        self.assertEqual(t['body_md'], '')
        r = core.card_summary(t)
        self.assertEqual(set(r), KEYS)
        self.assertEqual(r['source_kind'], 'day')
        self.assertEqual(r['source_label'], 'DAY 2 · FORESTER PASS')
        self.assertEqual(r['source_label'], core.excerpt_parts(t)[0])
        self.assertEqual(r['text'], markdown.plain(DAY_PROSE, 180))
        self.assertEqual(r['text'], DAY_PROSE)

    def test_day_label_without_a_day_title_is_just_the_day(self):
        t = self.multiday(days=[{}, {'body': DAY_PROSE}])
        r = core.card_summary(t)
        self.assertEqual((r['source_kind'], r['source_label']), ('day', 'DAY 2'))

    def test_day_excerpt_respects_limit(self):
        t = self.multiday(days=[{'title': 'Forester Pass', 'body': LONG_BODY}])
        r = core.card_summary(t, limit=40)
        self.assertEqual(r['source_kind'], 'day')
        self.assertEqual(r['text'], markdown.plain(LONG_BODY, 40))
        self.assertLessEqual(len(r['text']), 41)
        self.assertEqual(r['source_label'], 'DAY 1 · FORESTER PASS')

    def test_series_day_true_gives_labelled_day_excerpt(self):
        t = self.series()
        r = core.card_summary(t, series_day=True)
        self.assertEqual(r['source_kind'], 'day')
        self.assertEqual(r['source_label'], 'DAY 1 · CAMPO')
        self.assertEqual(r['text'], markdown.plain(PCT_PROSE, 180))
        self.assertIn('afternoon heat', r['text'])

    def test_a_day_result_always_carries_its_label(self):
        for t in (self.multiday(slug='m', days=[{}, {'body': DAY_PROSE}]), self.series(slug='s', written_day=2)):
            r = core.card_summary(t, series_day=True)
            self.assertEqual(r['source_kind'], 'day')
            self.assertTrue(r['source_label'].startswith('DAY 2'), r['source_label'])

    # ------------------------------------------------------------ 4. facts

    def test_series_default_gives_facts_not_day_prose(self):
        t = self.series()
        self.assertTrue(any(d['body_md'] for d in t['days']))      # the day prose exists...
        r = core.card_summary(t)
        self.assertEqual(set(r), KEYS)
        self.assertEqual(r['source_kind'], 'facts')
        self.assertEqual(r['source_label'], '')
        self.assertIn('recorded days', r['text'])
        self.assertIn(core.frange(t['date'], t['end_date']), r['text'])
        self.assertIn('Apr 22 – Sep 21, 2024', r['text'])
        self.assertNotIn(PCT_PROSE, r['text'])             # ...and never leaks into the series summary
        self.assertNotIn('afternoon heat', r['text'])
        self.assertNotIn('Campo', r['text'])
        self.assertIsNone(FIRST_PERSON.search(r['text']), r['text'])

    def test_series_facts_text_format(self):
        with_place = self.series(slug='with-place')
        self.assertEqual(core.card_summary(with_place)['text'], 'Journal of 2 recorded days, Apr 22 – Sep 21, 2024, Mexico to Canada.')
        no_place = self.series(slug='no-place', place=None)
        self.assertIsNone(no_place['place'])
        self.assertEqual(core.card_summary(no_place)['text'], 'Journal of 2 recorded days, Apr 22 – Sep 21, 2024.')

    def test_series_facts_count_only_days_with_a_track(self):
        t = self.series(tracks=(True, False, False, True, False))
        self.assertEqual(len(t['days']), 5)
        self.assertEqual(sum(1 for d in t['days'] if d['track']), 2)
        text = core.card_summary(t)['text']
        self.assertIn('2 recorded days', text)
        self.assertNotIn('5 recorded days', text)

    def test_series_without_written_days_is_facts_even_with_series_day(self):
        t = self.series(written_day=None)
        self.assertFalse(any(d['body_md'] for d in t['days']))
        for series_day in (False, True):
            with self.subTest(series_day=series_day):
                r = core.card_summary(t, series_day=series_day)
                self.assertEqual(r['source_kind'], 'facts')
                self.assertEqual(r['source_label'], '')
                self.assertIn('recorded days', r['text'])

    def test_multiday_with_no_writing_gives_facts(self):
        for slug, act, word in (('hike-trip', 'hike', 'hiking'), ('ski-trip', 'ski', 'backcountry ski')):
            with self.subTest(activity=act):
                t = self.multiday(slug=slug, activity=act)
                self.assertFalse(t['has_writeup'])
                self.assertEqual(len(t['days']), 3)
                r = core.card_summary(t)
                self.assertEqual(set(r), KEYS)
                self.assertEqual(r['source_kind'], 'facts')
                self.assertEqual(r['source_label'], '')
                self.assertEqual(word, core.act_word(t).lower())
                self.assertEqual(r['text'], '3-day %s trip, Jan 16–18, 2024.' % word)
                self.assertIsNone(FIRST_PERSON.search(r['text']), r['text'])

    def test_facts_never_contain_first_person_prose(self):
        for t in (self.series(slug='s1'), self.series(slug='s2', written_day=2, tracks=(True,) * 4), self.multiday(slug='m1')):
            r = core.card_summary(t)
            self.assertEqual(r['source_kind'], 'facts')
            self.assertIsNone(FIRST_PERSON.search(r['text']), r['text'])
            for d in t['days']:
                if d['body_md']:
                    self.assertNotIn(d['body_md'], r['text'])

    # ------------------------------------------------------------ 5. nothing

    def test_single_day_without_writeup_gives_no_summary(self):
        for slug, kw in (('track-only', dict(track=True)), ('photos-only', dict(photos=[photo('photos/01.webp', LANDSCAPE)])),
                         ('bare', {})):
            with self.subTest(trip=slug):
                t = self.trip(slug, activity='ski', date='2025-12-01', **kw)
                self.assertFalse(t['has_writeup'])
                self.assertEqual(core.card_summary(t), {'text': '', 'source_kind': None, 'source_label': ''})


if __name__ == '__main__':
    unittest.main()
