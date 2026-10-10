"""Phase 2: the build-time search index (tools/sitegen/search.py: normalize, entry, build_index, dumps) and the
`search_aliases` front matter it draws on (content.load_trip -> t['aliases']).

tools/sitegen/search.py may not exist yet while Phase 2 is being written: it is imported in setUp, so a missing module
fails each test with a clear message instead of breaking test discovery. tests/norm_cases.json is shared with
tests/trips_js_harness.js, so Python's normalize() and the page's JS norm() are held to one table.
"""
import importlib
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import markdown  # noqa: E402
from sitegen import core  # noqa: E402,F401

import helpers  # noqa: E402
from helpers import photo, LANDSCAPE  # noqa: E402

NORM_CASES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'norm_cases.json')

WRITEUP = ('Skinned up from the lake before dawn and skied the couloir on firm, edgeable snow. The exit apron had softened '
           'by the time we reached it, so the last turns were the best of the day.')
DAY_ONE = 'Crossed the Col du Chardonnet in a cold wind and reached the hut by four.'
DAY_TWO = 'A long glacier walk to Trient under high cloud.'
PARENT_MD = 'Three huts in three days across the **Alps**, see the [route notes](https://example.com/route) for pitches.'
CLIMB_MD = 'Climbed the **classic** 5.9 via the [Mountain Project page](https://www.mountainproject.com/x). Pitch two <was> airy.'


def load_search(tc):
    """sitegen.search, or a clear failure of the calling test when tools/sitegen/search.py is missing."""
    try:
        return importlib.import_module('sitegen.search')
    except ImportError as ex:
        tc.fail('tools/sitegen/search.py is not importable: %s' % ex)


def norm_cases():
    with open(NORM_CASES, encoding='utf-8') as fh:
        cases = json.load(fh)
    assert cases and all(isinstance(c, list) and len(c) == 2 for c in cases), 'norm_cases.json: list of [input, expected]'
    return cases


# ---------------------------------------------------------------- normalize

class NormalizeTests(unittest.TestCase):

    def setUp(self):
        self.search = load_search(self)

    def test_contract_examples(self):
        n = self.search.normalize
        self.assertEqual(n("Lover's Leap: Corrugation Corner"), 'lover s leap corrugation corner')
        self.assertEqual(n('Chamonix – Zermatt'), 'chamonix zermatt')
        self.assertEqual(n(''), '')

    def test_shared_table(self):
        for s, want in norm_cases():
            with self.subTest(s=s):
                self.assertEqual(self.search.normalize(s), want)

    def test_dash_and_curly_apostrophe_become_spaces_not_nothing(self):
        # dropping non-ASCII before splitting would glue the words together ('zurichbern'); the contract replaces every
        # run of non-alphanumerics by one space, and the page's JS norm() does the same
        self.assertEqual(self.search.normalize('Zürich—Bern'), 'zurich bern')
        self.assertEqual(self.search.normalize('Lover’s Leap'), 'lover s leap')

    def test_output_is_lowercase_ascii_words_with_single_spaces(self):
        for s, _ in norm_cases():
            with self.subTest(s=s):
                self.assertRegex(self.search.normalize(s), r'^$|^[a-z0-9]+( [a-z0-9]+)*$')

    def test_idempotent(self):
        for s, _ in norm_cases():
            out = self.search.normalize(s)
            self.assertEqual(self.search.normalize(out), out)


# ---------------------------------------------------------------- search_aliases (content)

class AliasTests(unittest.TestCase):
    """content.load_trip: optional `search_aliases` front matter -> t['aliases']."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def trip(self, slug, **meta):
        helpers.make_trip(self.tmp, slug, date='2025-01-01', **meta)
        return helpers.load(self.tmp, slug)

    def test_inline_list(self):
        self.assertEqual(self.trip('a', search_aliases=['PCT', 'Pacific Crest'])['aliases'], ['PCT', 'Pacific Crest'])

    def test_single_string(self):
        self.assertEqual(self.trip('b', search_aliases='PCT')['aliases'], ['PCT'])

    def test_absent_is_an_empty_list(self):
        t = self.trip('c')
        self.assertNotIn('search_aliases', t['meta'])
        self.assertEqual(t['aliases'], [])

    def test_items_are_stripped_and_empties_dropped(self):
        self.assertEqual(self.trip('d', search_aliases=['  PCT ', '', '  '])['aliases'], ['PCT'])

    def test_invalid_value_raises_content_error_naming_the_file(self):
        for i, bad in enumerate((5, True, {'a': 'b'})):
            slug = 'bad-%d' % i
            with self.subTest(value=bad):
                with self.assertRaises(content.ContentError) as cm:
                    self.trip(slug, search_aliases=bad)
                msg = str(cm.exception)
                self.assertTrue(msg.startswith('content/trips/%s/index.md: ' % slug), msg)
                self.assertIn('search_aliases', msg)

    def test_series_fixture_carries_the_pct_alias(self):
        helpers.make_series(self.tmp, search_aliases=['PCT'])
        self.assertEqual(helpers.load(self.tmp, 'pacific-crest-trail-2024')['aliases'], ['PCT'])


# ---------------------------------------------------------------- entry / build_index / dumps

class IndexFixture(unittest.TestCase):
    """A synthetic site: single-day trips with and without place, region, peaks, aliases and write-ups; a multi-day trip
    with a parent write-up and written days; a multi-day trip written only on a day; the PCT-shaped series; a planned
    route; a draft (dropped by load_dir like content.load_all does)."""

    def setUp(self):
        self.search = load_search(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        helpers.make_trip(self.tmp, 'west-couloir', title='West Couloir', activity='ski', date='2026-01-17', place='Sawtooth Ridge',
                          region='Eastern Sierra', body=WRITEUP, track=True,
                          photos=[photo('photos/01.webp', LANDSCAPE, alt='The couloir', sm=True)])
        helpers.make_trip(self.tmp, 'lovers-leap', title="Lover's Leap: Corrugation Corner", activity='climb', date='2025-06-14',
                          place="Lover's Leap", region='Lake Tahoe', body=CLIMB_MD, track=True)
        helpers.make_trip(self.tmp, 'dana-couloir', title='Dana Couloir', activity='ski', date='2024-05-11', place='Mount Dana',
                          region='Eastern Sierra', track=True, map={'peaks': ['Mount Dana', 'Mount Gibbs']})
        helpers.make_trip(self.tmp, 'both-keys', title='Gibbs Traverse', activity='hike', date='2024-05-12', region='Eastern Sierra',
                          track=True, search_aliases=['Dana'], map={'peaks': ['Mount Gibbs']})
        helpers.make_trip(self.tmp, 'region-only', title='Basin Loop', activity='hike', date='2025-08-10', region='Eastern Sierra',
                          body='A loop over three summits.', track=True)
        helpers.make_trip(self.tmp, 'nowhere', title='Evening Spin', activity='mtb', date='2025-02-02', track=True)
        helpers.make_trip(self.tmp, 'long-body', title='Ridge Walk', activity='hike', date='2023-07-04', track=True,
                          body='Alpenglow ridge walk. ' * 300)
        helpers.make_trip(self.tmp, 'haute-route', title='Haute Route', activity='hike', kind='multi-day', date='2025-04-01',
                          end_date='2025-04-03', region='Alps', body=PARENT_MD,
                          days=[{'title': 'Argentière', 'body': DAY_ONE}, {'title': 'Trient', 'body': DAY_TWO}, {'title': 'Zermatt'}])
        helpers.make_trip(self.tmp, 'hut-days', title='Hut Days', activity='ski', kind='multi-day', date='2024-02-01', end_date='2024-02-02',
                          days=[{'title': 'Approach'}, {'title': 'Forester Pass', 'body': DAY_ONE}])
        helpers.make_series(self.tmp, search_aliases=['PCT'])
        helpers.make_trip(self.tmp, 'someday-ridge', title='Someday Ridge', activity='mtb', kind='planned', date='2027-06-01', track=True)
        helpers.make_trip(self.tmp, 'secret-draft', title='Secret Draft', activity='other', draft=True, date='2026-03-01',
                          body='Unpublished words.', track=True)
        self.trips = helpers.load_dir(self.tmp)
        self.site = helpers.make_site(self.trips)
        self.by = self.site['by_slug']

    def entry(self, slug):
        return self.search.entry(self.by[slug])


class EntryTests(IndexFixture):

    def test_entry_has_the_six_contract_fields_as_strings_and_stays_lean(self):
        # s, t, p, k, x and r (the readable write-up text the body-hit snippet needs; the contract's unused 'n' snippet
        # was dropped after review). Every field stays within the 4000-character cap so the index stays lean (plan §8.5).
        for slug in ('west-couloir', 'haute-route', 'pacific-crest-trail-2024', 'nowhere', 'long-body'):
            e = self.entry(slug)
            with self.subTest(slug=slug):
                self.assertEqual({'s', 't', 'p', 'k', 'x', 'r'}, set(e), sorted(e))
                self.assertTrue(all(isinstance(v, str) for v in e.values()), e)
                for k, v in e.items():
                    self.assertLessEqual(len(v), 4000, k)

    def test_slug_and_normalized_title(self):
        e = self.entry('lovers-leap')
        self.assertEqual(e['s'], 'lovers-leap')
        self.assertEqual(e['t'], 'lover s leap corrugation corner')
        self.assertEqual(self.entry('pacific-crest-trail-2024')['t'], 'pacific crest trail 2024')

    def test_place_and_region(self):
        self.assertEqual(self.entry('west-couloir')['p'], 'sawtooth ridge eastern sierra')
        self.assertEqual(self.entry('lovers-leap')['p'], 'lover s leap lake tahoe')
        self.assertEqual(self.entry('region-only')['p'], 'eastern sierra')   # no place: the region alone
        self.assertEqual(self.entry('nowhere')['p'], '')                      # neither

    def test_keywords_lead_with_the_activity_label(self):
        # plan 8.3: the activity label is searchable; it opens the k field, then aliases, then peaks
        self.assertEqual(self.entry('west-couloir')['k'], 'backcountry ski')
        self.assertEqual(self.entry('pacific-crest-trail-2024')['k'], 'hiking pct')

    def test_other_subtype_word_is_searchable(self):
        helpers.make_trip(self.tmp, 'lake-paddle', title='Lake Paddle', activity='other', subtype='SUP', date='2025-07-01', track=True)
        t = helpers.load(self.tmp, 'lake-paddle')
        self.assertEqual(self.search.entry(t)['k'], 'other paddleboarding')

    def test_peaks_are_searchable_keywords(self):
        self.assertEqual(self.entry('dana-couloir')['k'], 'backcountry ski mount dana mount gibbs')

    def test_peaks_given_as_one_string_or_with_junk_items_still_index_the_names(self):
        helpers.make_trip(self.tmp, 'one-peak', title='One Peak', activity='hike', date='2025-07-02', track=True, map={'peaks': 'Mount Tallac'})
        self.assertEqual(self.search.entry(helpers.load(self.tmp, 'one-peak'))['k'], 'hiking mount tallac')
        t = helpers.load(self.tmp, 'one-peak')
        t['map'] = {'peaks': ['Mount Tallac', {'name': 'Dicks Peak'}, 42]}
        self.assertEqual(self.search.entry(t)['k'], 'hiking mount tallac')

    def test_aliases_come_before_peaks(self):
        self.assertEqual(self.entry('both-keys')['k'], 'hiking dana mount gibbs')

    def test_trailing_comma_in_aliases_is_a_blank_item(self):
        folder = helpers.make_trip(self.tmp, 'comma', title='Comma', activity='hike', date='2025-07-03', track=True)
        with open(os.path.join(folder, 'index.md'), encoding='utf-8') as fh:
            txt = fh.read().replace('activity: hike', 'activity: hike\nsearch_aliases: [Comma Route, ]')
        with open(os.path.join(folder, 'index.md'), 'w', encoding='utf-8') as fh:
            fh.write(txt)
        self.assertEqual(helpers.load(self.tmp, 'comma')['aliases'], ['Comma Route'])

    def test_body_text_is_normalized_plain_text_without_markup_or_urls(self):
        x = self.entry('lovers-leap')['x']
        self.assertEqual(x, self.search.normalize(markdown.plain(self.by['lovers-leap']['body_md'])))
        for words in ('classic', 'mountain project page', 'pitch two was airy'):
            self.assertIn(words, x)
        for bad in ('https', 'mountainproject com', '<', '>', '*', '[', ']'):
            self.assertNotIn(bad, x)
        self.assertEqual(self.entry('dana-couloir')['x'], '')

    def test_body_text_includes_the_parent_and_every_day(self):
        x = self.entry('haute-route')['x']
        self.assertIn('three huts in three days', x)
        self.assertIn('col du chardonnet', x)
        self.assertIn('glacier walk to trient', x)
        self.assertLess(x.index('three huts'), x.index('col du chardonnet'))
        self.assertLess(x.index('col du chardonnet'), x.index('glacier walk'))
        self.assertIn('hauser creek', self.entry('pacific-crest-trail-2024')['x'])
        self.assertIn('col du chardonnet', self.entry('hut-days')['x'])

    def test_body_text_is_capped_at_4000_characters(self):
        self.assertGreater(len(self.search.normalize(markdown.plain(self.by['long-body']['body_md']))), 4000)
        x = self.entry('long-body')['x']
        self.assertLessEqual(len(x), 4000)
        self.assertTrue(x.startswith('alpenglow ridge walk alpenglow ridge walk'), x[:80])

    def test_raw_text_carries_the_parent_and_every_day_for_snippets(self):
        r = self.entry('haute-route')['r']
        self.assertIn('Three huts', r)
        self.assertIn('Chardonnet', r)
        self.assertNotIn('**', r)
        self.assertNotIn('](', r)
        self.assertEqual(self.entry('dana-couloir')['r'], '')
        self.assertLessEqual(len(self.entry('long-body')['r']), 4000)


class IndexTests(IndexFixture):

    def test_entries_follow_published_order_newest_first(self):
        idx = self.search.build_index(self.site)
        self.assertEqual([e['s'] for e in idx], helpers.slugs(self.site['published']))
        self.assertEqual(idx[0]['s'], 'west-couloir')

    def test_excludes_planned_routes_and_drafts(self):
        self.assertEqual(self.site['trips'][0]['slug'], 'someday-ridge')   # the newest of all, but planned
        idx = self.search.build_index(self.site)
        slugs_ = [e['s'] for e in idx]
        self.assertNotIn('someday-ridge', slugs_)
        self.assertNotIn('secret-draft', slugs_)
        text = self.search.dumps(idx).lower()
        self.assertNotIn('someday', text)
        self.assertNotIn('unpublished', text)

    def test_series_is_one_entry_and_its_days_are_not_entries(self):
        idx = self.search.build_index(self.site)
        self.assertEqual(len(idx), len(self.site['published']))
        self.assertEqual(sum(1 for e in idx if e['s'] == 'pacific-crest-trail-2024'), 1)
        self.assertEqual(len({e['s'] for e in idx}), len(idx))

    def test_entries_equal_entry_of_each_published_trip(self):
        self.assertEqual(self.search.build_index(self.site), [self.search.entry(t) for t in self.site['published']])

    def test_index_text_has_no_coordinates_gpx_or_html(self):
        text = self.search.dumps(self.search.build_index(self.site))
        self.assertNotIn('<', text)
        for bad in ('.gpx', 'trkpt', '"lat"', '"lon"', 'photos/', '.webp'):
            self.assertNotIn(bad, text)


class DumpsTests(unittest.TestCase):

    def setUp(self):
        self.search = load_search(self)

    def test_compact_json(self):
        self.assertEqual(self.search.dumps([{'s': 'a', 't': 'b c'}]), '[{"s":"a","t":"b c"}]')
        self.assertEqual(self.search.dumps([]), '[]')

    def test_escapes_angle_brackets_and_round_trips(self):
        entries = [{'s': 'x', 'n': 'Pitch two </script><b>was</b> airy'}]
        text = self.search.dumps(entries)
        self.assertNotIn('<', text)
        self.assertIn('\\u003c', text.lower())
        self.assertEqual(json.loads(text), entries)

    def test_ascii_only_output_round_trips_non_ascii(self):
        entries = [{'s': 'v', 'n': 'Vallée Blanche – Zermatt …'}]
        text = self.search.dumps(entries)
        self.assertTrue(all(ord(ch) < 128 for ch in text), text)
        self.assertEqual(json.loads(text), entries)


if __name__ == '__main__':
    unittest.main()
