"""Journal day labels and anchors (content.day_anchor, the label and anchor checks in content.load_trip), the shared
caption opener (core.recorded), and what a journal of one day says about itself.

Synthetic journals in a temp dir; every slug starts with 'syn-d-', which no real trip's slug does, so nothing under
rendered/trips/ is read.
"""
import datetime
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

PREFIX = 'syn-d-'
SLUG = PREFIX + 'journal'


class Fixture(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        patcher = mock.patch.object(core, '_SITE_META', [{'hash': '', 'maps': {}, 'regions': [], 'all_regions': []}])
        patcher.start()
        self.addCleanup(patcher.stop)
        self.assertFalse(os.path.lexists(os.path.join(content.RENDERED, 'trips', SLUG)), 'the fixture slug names a real trip')

    def make(self, days, slug=SLUG, kind='series', **meta):
        m = dict(title='Synthetic Journal', kind=kind, place='Start to Finish', region='Synthetic Range')
        m.update(meta)
        return helpers.make_trip(self.tmp, slug, days=days, **m)

    def load(self, days, **kw):
        self.make(days, **kw)
        return helpers.load(self.tmp, kw.get('slug', SLUG))

    def raw_day(self, stem, *lines):
        """Write days/<stem>.md with front matter exactly as typed (frontmatter.render would quote a string '0')."""
        folder = os.path.join(self.tmp, SLUG, 'days')
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, stem + '.md'), 'w', encoding='utf-8') as fh:
            fh.write('---\n%s\n---\n' % '\n'.join(lines))
        helpers.touch(os.path.join(folder, stem + '.gpx'))


class DayAnchorTests(unittest.TestCase):

    def test_numbers_keep_the_form_the_site_has_always_used(self):
        self.assertEqual(content.day_anchor('31'), 'day-31')
        self.assertEqual(content.day_anchor('5.2'), 'day-5-2')
        self.assertEqual(content.day_anchor(31), 'day-31')
        self.assertEqual(content.day_anchor(5.2), 'day-5-2')
        self.assertEqual(content.day_anchor('0'), 'day-0')

    def test_anything_else_becomes_a_hyphen_so_the_id_is_safe_in_an_attribute_and_a_url(self):
        self.assertEqual(content.day_anchor('5 (zero)'), 'day-5-zero')
        self.assertEqual(content.day_anchor('Rest & <b>"x"'), 'day-Rest-b-x')
        self.assertEqual(content.day_anchor(' 12 '), 'day-12')
        for label in ('5 (zero)', 'a"b', "it's", 'x<y>', 'tab\there', 'né 8'):
            self.assertRegex(content.day_anchor(label), r'^day-[A-Za-z0-9]+(-[A-Za-z0-9]+)*$', label)

    def test_the_journal_page_uses_the_same_function(self):
        from sitegen.pages import series
        for label in ('31', '5.2', '5 (zero)', 'Rest & <b>'):
            self.assertEqual(series.day_anchor({'label': label}), content.day_anchor(label))


class DayLabelTests(Fixture):

    def test_a_missing_or_empty_day_takes_its_position(self):
        self.make([])
        self.raw_day('001', 'title: One')
        self.raw_day('002', 'day: ""', 'title: Two')
        self.raw_day('003', 'day: 7')
        self.raw_day('004', 'title: Four')
        t = helpers.load(self.tmp, SLUG)
        self.assertEqual([d['label'] for d in t['days']], ['1', '2', '7', '4'])

    def test_day_zero_is_a_label_not_a_missing_one(self):
        # `day: 0` parses as the number 0, which is falsy: it used to be replaced by the day's position, so a Day 0
        # before Day 1 gave two days the label 1 and one anchor
        self.make([])
        self.raw_day('000', 'day: 0', 'title: Travel')
        self.raw_day('001', 'day: 1', 'title: Start')
        self.raw_day('002', 'day: "0.5"')
        t = helpers.load(self.tmp, SLUG)
        self.assertEqual([d['label'] for d in t['days']], ['0', '1', '0.5'])
        self.assertEqual([content.day_anchor(d['label']) for d in t['days']], ['day-0', 'day-1', 'day-0-5'])

    def test_a_decimal_label_stays_as_written(self):
        self.make([])
        self.raw_day('001', 'day: 5.2')
        self.raw_day('002', 'day: 12')
        self.assertEqual([d['label'] for d in helpers.load(self.tmp, SLUG)['days']], ['5.2', '12'])


class AnchorCheckTests(Fixture):

    def error(self, days, **kw):
        self.make(days, **kw)
        with self.assertRaises(content.ContentError) as cm:
            helpers.load(self.tmp, kw.get('slug', SLUG))
        return str(cm.exception)

    def test_two_days_with_one_anchor_are_refused_by_name(self):
        msg = self.error([{'id': '001', 'day': '1'}, {'id': '002', 'day': '5.2'}, {'id': '007', 'day': '5-2'}])
        self.assertTrue(msg.startswith('content/trips/%s/days/007.md: ' % SLUG), msg)
        self.assertIn("'5-2'", msg)
        self.assertIn('#day-5-2', msg)
        self.assertIn('days/002.md', msg)

    def test_the_same_label_twice_is_refused(self):
        msg = self.error([{'id': '001', 'day': '3'}, {'id': '002', 'day': '3'}])
        self.assertTrue(msg.startswith('content/trips/%s/days/002.md: ' % SLUG), msg)
        self.assertIn('#day-3', msg)
        self.assertIn('days/001.md', msg)

    def test_a_label_with_no_letter_or_digit_is_refused(self):
        for i, label in enumerate(('?', '-', '. .', '()')):
            with self.subTest(label=label):
                slug = PREFIX + 'bare-%d' % i
                msg = self.error([{'id': '001', 'day': '1'}, {'id': '002', 'day': label}], slug=slug)
                self.assertTrue(msg.startswith('content/trips/%s/days/002.md: ' % slug), msg)
                self.assertIn('no letter or digit', msg)
                self.assertIn(repr(label), msg)

    def test_a_position_that_collides_with_a_typed_label_is_refused(self):
        # day file 2 has no `day:` and takes position 2; day file 3 says it is day 2
        self.make([])
        self.raw_day('001', 'day: 1')
        self.raw_day('002', 'title: Unlabelled')
        self.raw_day('003', 'day: 2')
        with self.assertRaises(content.ContentError) as cm:
            helpers.load(self.tmp, SLUG)
        self.assertIn('days/003.md', str(cm.exception))
        self.assertIn('days/002.md', str(cm.exception))

    def test_an_unlabelled_day_that_collides_is_told_it_has_no_day_line(self):
        # the PCT's case: labels do not follow the file order, and a day added without a `day:` line (add_trip.py
        # --day-of writes none) takes a position another day already uses as its label. The message must not quote a
        # `day:` value the file does not hold.
        self.make([])
        self.raw_day('001', 'day: 1')
        self.raw_day('002', 'day: 3')
        self.raw_day('003', 'title: Added later')
        with self.assertRaises(content.ContentError) as cm:
            helpers.load(self.tmp, SLUG)
        msg = str(cm.exception)
        self.assertTrue(msg.startswith('content/trips/%s/days/003.md: no day: line' % SLUG), msg)
        self.assertIn('its position, 3,', msg)
        self.assertIn('#day-3', msg)
        self.assertIn('days/002.md', msg)
        self.assertIn('add a day: line', msg)
        self.assertNotIn("day: '3'", msg)

    def test_a_typed_label_that_collides_with_an_unlabelled_day_quotes_what_was_typed(self):
        self.make([])
        self.raw_day('001', 'title: Unlabelled')
        self.raw_day('002', 'day: 1')
        with self.assertRaises(content.ContentError) as cm:
            helpers.load(self.tmp, SLUG)
        msg = str(cm.exception)
        self.assertTrue(msg.startswith("content/trips/%s/days/002.md: day: '1' gives the same page anchor (#day-1) as days/001.md" % SLUG), msg)

    def test_distinct_labels_load(self):
        t = self.load([{'id': '001', 'day': '1'}, {'id': '002', 'day': '5.2'}, {'id': '003', 'day': '5 (zero)'}, {'id': '004', 'day': '52'}])
        self.assertEqual([content.day_anchor(d['label']) for d in t['days']], ['day-1', 'day-5-2', 'day-5-zero', 'day-52'])

    def test_only_a_journal_builds_anchors_from_labels(self):
        # a multi-day trip's page numbers its days by position, so repeated or odd labels are not an error there
        days = [{'id': '01', 'day': '1'}, {'id': '02', 'day': '1'}, {'id': '03', 'day': '?'}, {'id': '04', 'day': '1 n'}]
        for i, kind in enumerate(('multi-day', 'trip', 'planned')):
            with self.subTest(kind=kind):
                t = self.load(days, kind=kind, slug=PREFIX + 'other-%d' % i)
                self.assertEqual(t['kind'], kind)
                self.assertEqual([d['label'] for d in t['days']], ['1', '1', '?', '1 n'])

    def test_an_anchor_may_not_be_another_days_number_or_title_id(self):
        # the page writes '<anchor>-n' on a day's number and '<anchor>-t' on its title: a later 'Day 5 n' would get the
        # first of those as its own anchor, and a link to it would land on Day 5's number
        from sitegen.pages import series
        msg = self.error([{'id': '001', 'day': '5'}, {'id': '002', 'day': '5 n'}])
        self.assertTrue(msg.startswith('content/trips/%s/days/002.md: ' % SLUG), msg)
        self.assertIn("'5 n'", msg)
        self.assertIn('#day-5-n', msg)
        self.assertIn('days/001.md', msg)
        # the title id, and the other order (the odd label first)
        msg = self.error([{'id': '001', 'day': '12'}, {'id': '002', 'day': '12.t'}], slug=PREFIX + 'sub-t')
        self.assertIn('#day-12-t', msg)
        msg = self.error([{'id': '001', 'day': '5-n'}, {'id': '002', 'day': '5'}], slug=PREFIX + 'sub-rev')
        self.assertTrue(msg.startswith('content/trips/%s/days/002.md: ' % (PREFIX + 'sub-rev')), msg)
        self.assertIn('#day-5-n', msg)
        self.assertIn('days/001.md', msg)
        # the two suffixes are the ones the day article writes
        t = self.load([{'id': '001', 'day': '7', 'title': 'Synthetic', 'date': '2024-05-01'}], slug=PREFIX + 'ids')
        html_ = series.day_article(t, t['days'][0], t['url'])
        for suffix in content.DAY_SUB_IDS:
            self.assertIn('id="day-7%s"' % suffix, html_)
        self.assertEqual(sorted(set(re.findall(r'id="(day-7[^"]*)"', html_))), ['day-7', 'day-7-n', 'day-7-t'])

    def test_labels_that_only_look_alike_load(self):
        # 'n' and 't' inside a label are fine; only a whole '-n' / '-t' tail on another day's anchor collides
        t = self.load([{'id': '001', 'day': '5'}, {'id': '002', 'day': '5n'}, {'id': '003', 'day': '5.2'}, {'id': '004', 'day': 'n'},
                       {'id': '005', 'day': '50'}], slug=PREFIX + 'alike')
        self.assertEqual([content.day_anchor(d['label']) for d in t['days']], ['day-5', 'day-5n', 'day-5-2', 'day-n', 'day-50'])


class RecordedTests(unittest.TestCase):

    def test_one_date_reads_on_a_range_does_not_and_no_date_says_nothing(self):
        d = datetime.date
        self.assertEqual(core.recorded(d(2026, 3, 28)), 'As recorded on Mar 28, 2026')
        self.assertEqual(core.recorded(d(2026, 3, 28), None), 'As recorded on Mar 28, 2026')
        self.assertEqual(core.recorded(d(2025, 2, 1), d(2025, 2, 1)), 'As recorded on Feb 1, 2025')
        self.assertEqual(core.recorded(d(2024, 3, 10), d(2024, 3, 15)), 'As recorded Mar 10–15, 2024')
        self.assertEqual(core.recorded(d(2024, 4, 22), d(2024, 9, 21)), 'As recorded Apr 22 – Sep 21, 2024')
        self.assertEqual(core.recorded(d(2023, 12, 30), d(2024, 1, 2)), 'As recorded Dec 30, 2023 – Jan 2, 2024')
        self.assertEqual(core.recorded(None), '')
        self.assertEqual(core.recorded(None, d(2024, 1, 2)), '')

    def test_the_range_is_core_frange(self):
        d = datetime.date
        for a, b in ((d(2024, 3, 10), d(2024, 3, 15)), (d(2024, 4, 22), d(2024, 9, 21)), (d(2023, 12, 30), d(2024, 1, 2))):
            self.assertEqual(core.recorded(a, b), 'As recorded ' + core.frange(a, b))


def caption_items(root):
    """The items of a core.map_caption() block as a reader sees them, without the screen-reader separators."""
    out = []
    for item in root.find_all('span', cls='mi'):
        own = [c if isinstance(c, str) else ('' if 'sr' in c.classes else c.text(clean=False)) for c in item.children]
        out.append(helpers.plain_text(''.join(own)))
    return out


class OneDayTests(Fixture):
    """The state of any new journal on its first day, and of a multi-day trip recorded on one date."""

    def journal_page(self, days, **meta):
        from sitegen.pages import series
        t = self.load(days, **meta)
        site = helpers.make_site([t])
        return t, series.page(t, site).html

    def test_a_one_day_journal_counts_one_day_everywhere(self):
        t, html_ = self.journal_page([{'id': '001', 'day': '1', 'title': 'Start', 'date': '2024-05-01', 'body': 'Synthetic entry.'}])
        self.assertEqual(len(t['days']), 1)
        doc = Doc(html_)
        desc = doc.find('head').find('meta', attrs={'name': 'description'})['content']
        self.assertIn('Synthetic Journal: 1 recorded day, May 1, 2024, with a GPX track for every day and 1 written up.', desc)
        self.assertNotIn('1 recorded days', html_)
        og = doc.find('head').find('meta', attrs={'property': 'og:description'})['content']
        self.assertEqual(og, desc)
        self.assertIn('Synthetic Journal: 1 recorded day, May 1, 2024, Start to Finish.', doc.find('p', cls='ser-lede').text())

    def test_a_one_day_journal_is_recorded_on_its_date(self):
        _, html_ = self.journal_page([{'id': '001', 'day': '1', 'date': '2024-05-01'}])
        cap = caption_items(Doc(html_).find('div', cls='mapcap'))
        self.assertEqual(cap[:3], ['As recorded on May 1, 2024', 'full tracks, not trimmed', 'North up'])

    def test_a_journal_of_several_days_is_recorded_over_its_range(self):
        t, html_ = self.journal_page([{'id': '001', 'day': '1', 'date': '2024-05-01'}, {'id': '002', 'day': '2', 'date': '2024-05-03'}])
        cap = caption_items(Doc(html_).find('div', cls='mapcap'))
        self.assertEqual(cap[:3], ['As recorded May 1–3, 2024', 'full tracks, not trimmed', 'North up'])
        desc = Doc(html_).find('head').find('meta', attrs={'name': 'description'})['content']
        self.assertIn('2 recorded days, May 1–3, 2024, with a GPX track for every day.', desc)

    def test_a_multi_day_trip_whose_days_share_a_date_is_recorded_on_it(self):
        from sitegen.pages import multiday
        t = self.load([{'id': '01', 'day': '1', 'date': '2025-02-01'}, {'id': '02', 'day': '2', 'date': '2025-02-01'}], kind='multi-day')
        self.assertEqual(caption_items(Doc(multiday.overview_caption(t)).root)[:3],
                         ['As recorded on Feb 1, 2025', 'full track, not trimmed', 'North up'])
        t = self.load([{'id': '01', 'day': '1', 'date': '2025-02-01'}, {'id': '02', 'day': '2', 'date': '2025-02-03'}],
                      kind='multi-day', slug=PREFIX + 'range')
        self.assertEqual(caption_items(Doc(multiday.overview_caption(t)).root)[0], 'As recorded Feb 1–3, 2025')
        t = self.load([{'id': '01', 'day': '1'}, {'id': '02', 'day': '2'}], kind='multi-day', slug=PREFIX + 'undated')
        self.assertEqual(caption_items(Doc(multiday.overview_caption(t)).root)[:2], ['full track, not trimmed', 'North up'])


if __name__ == '__main__':
    unittest.main()
