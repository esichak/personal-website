"""Phase 3: what tools/sitegen/core.py gains for report pages, pinned to contract-phase3.md sections 3 and 4 and to the
later changes of sections 10.1 and 10.3: core.related (which reports follow a report, and the ones it is told to skip),
core.related_block ('More like this') and the page kinds that show it, report.neighbours (the two reports of a page's
Newer / Older pager, which 'More like this' leaves out) and core.copy_link (the copy-to-clipboard control). Where a
report page puts them is in tests/test_report_page.py.

A synthetic site in a temp dir around one subject, rel-subject (a hike in 'Synthetic Range' on 2026-06-10). Every other
trip is named for its relation to it:

  same region and activity   rel-near-after (5 days later; a write-up and a photo, so its page is a story),
                             rel-near-before (5 days earlier), rel-later (40 days later: the newest report of all, but
                             farther away than rel-near-before, so 'nearest in date' and 'newest first' disagree),
                             rel-far (2025), rel-twin-a and rel-twin-b (the same day in 2024), rel-undated (no date)
  same region only           rel-region-ski (the subject's own day), rel-region-tour (a multi-day ski trip)
  same activity only         rel-act-near (the day before, 'Other Range'), rel-journal (a series, 'Other Range'),
                             rel-act-far (2023, no region), rel-act-nowhere (2021, no region)
  neither                    rel-elsewhere (ski, 'Other Range'), rel-noregion-ski (ski, no region)
  never related              rel-planned (a goal in the subject's region and activity), rel-draft (a draft, never loaded)

The site lists its reports newest first (tools/build.py), an undated one last. A page's pager links to the reports on
either side of it among those of its activity (HIKES and SKIS below are those two runs), and 'More like this' skips them.

Slugs match no real trip, so nothing under rendered/trips/ is consulted; core.region_map_href's site meta is patched
in memory. core's functions are fetched through need() and the page modules are imported inside the tests, so a missing
function or module fails each test clearly instead of breaking discovery. Every sentence in a fixture is synthetic.
"""
import importlib
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, photo, LANDSCAPE, slugs  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

WRITEUP = 'Synthetic write-up for a test.'
REGION = 'Synthetic Range'
OTHER = 'Other Range'
SUBJECT = 'rel-subject'
HERE = 'trips/rel-subject/'
SAME_BOTH = ['rel-near-after', 'rel-near-before', 'rel-later', 'rel-far', 'rel-twin-a', 'rel-twin-b', 'rel-undated']
SAME_REGION = ['rel-region-ski', 'rel-region-tour']
SAME_ACTIVITY = ['rel-act-near', 'rel-journal', 'rel-act-far', 'rel-act-nowhere']
ALL = SAME_BOTH + SAME_REGION + SAME_ACTIVITY     # everything related to the subject, in the contract's order
NEVER = ['rel-elsewhere', 'rel-noregion-ski', 'rel-planned', 'rel-draft', SUBJECT]
# the published reports of each activity in site['published'] order (newest first; one day's reports in folder order)
HIKES = ['rel-later', 'rel-near-after', SUBJECT, 'rel-act-near', 'rel-near-before', 'rel-far', 'rel-journal', 'rel-twin-a',
         'rel-twin-b', 'rel-act-far', 'rel-act-nowhere', 'rel-undated']
SKIS = ['rel-elsewhere', 'rel-region-ski', 'rel-noregion-ski', 'rel-region-tour']


def load_module(tc, name):
    try:
        return importlib.import_module(name)
    except ImportError as ex:
        tc.fail('%s is not importable: %s' % (name.replace('.', '/') + '.py', ex))


def need(tc, mod, name):
    """mod.<name>, or a clear failure of the calling test when the function / constant the contract names is missing."""
    if not hasattr(mod, name):
        tc.fail('%s.%s is missing (contract-phase3.md)' % (mod.__name__, name))
    return getattr(mod, name)


def ml_items(node):
    """The items of a meta line (core.meta_items) as a reader sees them: the screen-reader ', ' separators dropped."""
    return [re.sub(r'^, ', '', m.text()) for m in node.find_all('span', cls='mi')]


class RelatedFixture(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        meta = {'hash': '', 'maps': {}, 'regions': [], 'all_regions': [REGION, OTHER]}
        patcher = mock.patch.object(core, '_SITE_META', [meta])
        patcher.start()
        self.addCleanup(patcher.stop)
        mk = helpers.make_trip
        mk(self.tmp, SUBJECT, title='Synthetic Subject', activity='hike', date='2026-06-10', region=REGION, track=True)
        # same region and same activity
        mk(self.tmp, 'rel-near-after', title='Synthetic Near After', activity='hike', date='2026-06-15', region=REGION, track=True,
           body=WRITEUP, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one', sm=True)])
        mk(self.tmp, 'rel-near-before', title='Synthetic Near Before', activity='hike', date='2026-06-05', region=REGION, track=True)
        mk(self.tmp, 'rel-later', title='Synthetic Later', activity='hike', date='2026-07-20', region=REGION, track=True)
        mk(self.tmp, 'rel-far', title='Synthetic Far', activity='hike', date='2025-01-01', region=REGION, track=True)
        mk(self.tmp, 'rel-twin-a', title='Synthetic Twin A', activity='hike', date='2024-01-01', region=REGION, track=True)
        mk(self.tmp, 'rel-twin-b', title='Synthetic Twin B', activity='hike', date='2024-01-01', region=REGION, track=True)
        mk(self.tmp, 'rel-undated', title='Synthetic Undated', activity='hike', region=REGION, track=True)
        # same region, another activity
        mk(self.tmp, 'rel-region-ski', title='Synthetic Region Ski', activity='ski', date='2026-06-10', region=REGION, track=True)
        mk(self.tmp, 'rel-region-tour', title='Synthetic Region Tour', activity='ski', kind='multi-day', date='2026-03-01', end_date='2026-03-02',
           region=REGION, days=[{'title': 'Synthetic Day One', 'date': '2026-03-01'}, {'title': 'Synthetic Day Two', 'date': '2026-03-02'}])
        # same activity, another region or none
        mk(self.tmp, 'rel-act-near', title='Synthetic Activity Near', activity='hike', date='2026-06-09', region=OTHER, track=True)
        helpers.make_series(self.tmp, slug='rel-journal', title='Synthetic Journal', written_day=None, region=OTHER)   # 2024-04-22 on
        mk(self.tmp, 'rel-act-far', title='Synthetic Activity Far', activity='hike', date='2023-06-10', track=True)
        mk(self.tmp, 'rel-act-nowhere', title='Synthetic Activity Nowhere', activity='hike', date='2021-01-01', track=True)
        # neither
        mk(self.tmp, 'rel-elsewhere', title='Synthetic Elsewhere', activity='ski', date='2026-06-10', region=OTHER, track=True)
        mk(self.tmp, 'rel-noregion-ski', title='Synthetic Regionless Ski', activity='ski', date='2026-06-08', track=True)
        # never: a goal and a draft, both in the subject's region and activity
        mk(self.tmp, 'rel-planned', title='Synthetic Planned', activity='hike', kind='planned', region=REGION, track=True)
        mk(self.tmp, 'rel-draft', title='Synthetic Draft', activity='hike', date='2026-06-11', region=REGION, draft=True, track=True)
        self.related = need(self, core, 'related')
        self.reload()

    def reload(self):
        """(Re)load the temp folder through the real loader and tools/build.py's own site_of(), registered as build() does."""
        self.trips = helpers.load_dir(self.tmp)
        self.site = load_module(self, 'build').site_of(helpers.newest_first(self.trips))
        core.register_site(self.site)
        self.by = self.site['by_slug']
        self.t = self.by[SUBJECT]

    def rel(self, slug=SUBJECT, site=None, **kw):
        site = site or self.site
        return slugs(self.related(site['by_slug'][slug], site, **kw))

    def site_with(self, published):
        """The site with another 'published' list (the order and the members core.related walks)."""
        return dict(self.site, published=list(published))


# ---------------------------------------------------------------- core.related

class RelatedTests(RelatedFixture):

    def test_at_most_three_by_default(self):
        # section 3: core.related(t, site, k=3) -> up to k published trips
        self.assertEqual(self.rel(), ALL[:3])
        self.assertEqual(self.rel(), ['rel-near-after', 'rel-near-before', 'rel-later'])

    def test_k_limits_the_list(self):
        # section 3: at most k
        for k in (0, 1, 2, 5, 11, 99):
            with self.subTest(k=k):
                self.assertEqual(self.rel(k=k), ALL[:k])

    def test_tier_order_region_and_activity_then_region_then_activity(self):
        # section 3: order (1) same region and same activity, (2) same region, (3) same activity only
        got = self.rel(k=99)
        self.assertEqual(got, ALL)
        tiers = [0 if s in SAME_BOTH else (1 if s in SAME_REGION else 2) for s in got]
        self.assertEqual(tiers, sorted(tiers))

    def test_a_tier_beats_a_closer_date(self):
        # section 3: the date only orders trips inside a tier: a same-region ski tour on the subject's own day comes after
        # every hike of the region (even the undated one), and before the hike elsewhere on the day before
        got = self.rel(k=99)
        self.assertEqual(self.by['rel-region-ski']['date'], self.t['date'])
        self.assertLess(got.index('rel-undated'), got.index('rel-region-ski'))
        self.assertLess(got.index('rel-region-tour'), got.index('rel-act-near'))

    def test_nearest_date_first_inside_a_tier(self):
        # section 3: within a tier the nearest in date to t first (absolute difference in days)
        got = self.rel(k=99)
        for tier in (SAME_BOTH[:-1], SAME_REGION, SAME_ACTIVITY):
            gaps = [abs((self.by[s]['date'] - self.t['date']).days) for s in got if s in tier]
            self.assertEqual(gaps, sorted(gaps), tier)
        self.assertEqual([s for s in got if s in SAME_ACTIVITY], ['rel-act-near', 'rel-journal', 'rel-act-far', 'rel-act-nowhere'])

    def test_nearest_in_date_is_not_newest_first(self):
        # section 3 says nearest (section 7's 'newest first' is the older wording): rel-later is the newest report of the
        # tier but 40 days after the subject; rel-near-before is older than the subject and 5 days away, so it comes first
        when = self.t['date']
        later, before = self.by['rel-later']['date'], self.by['rel-near-before']['date']
        self.assertTrue(before < when < later)
        self.assertEqual(((later - when).days, (when - before).days), (40, 5))
        tier = [s for s in self.rel(k=99) if s in SAME_BOTH[:-1]]
        self.assertEqual(tier, ['rel-near-after', 'rel-near-before', 'rel-later', 'rel-far', 'rel-twin-a', 'rel-twin-b'])
        self.assertLess(tier.index('rel-near-before'), tier.index('rel-later'))
        newest_first = sorted(tier, key=lambda s: self.by[s]['date'], reverse=True)   # stable: the twins keep their order
        self.assertEqual(newest_first[0], 'rel-later')
        self.assertNotEqual(tier, newest_first)
        # and from the other side: seen from rel-near-before every report of 2026 is newer, and the nearest still leads
        self.assertEqual(self.rel('rel-near-before'), [SUBJECT, 'rel-near-after', 'rel-later'])

    def test_the_newer_trip_wins_a_tie(self):
        # section 3: ... then the newer one: five days after beats five days before, whatever order the site lists them in
        self.assertEqual(self.rel()[:2], ['rel-near-after', 'rel-near-before'])
        oldest_first = self.site_with(reversed(self.site['published']))
        self.assertEqual(self.rel(site=oldest_first)[:2], ['rel-near-after', 'rel-near-before'])

    def test_an_undated_trip_comes_last_in_its_tier(self):
        # section 3: a trip without a date after every dated one (inside its tier: it still precedes the next tier)
        got = self.rel(k=99)
        self.assertEqual([s for s in got if s in SAME_BOTH][-1], 'rel-undated')
        self.assertEqual(got[len(SAME_BOTH) - 1], 'rel-undated')
        oldest_first = self.site_with(reversed(self.site['published']))
        self.assertEqual(self.rel(site=oldest_first, k=99)[len(SAME_BOTH) - 1], 'rel-undated')

    def test_an_undated_subject_counts_every_candidate_as_undated(self):
        # section 3: every candidate counts as undated when t has no date: the tiers hold, then the newer one first
        self.assertIsNone(self.by['rel-undated']['date'])
        self.assertEqual(self.rel('rel-undated', k=99),
                         ['rel-later', 'rel-near-after', SUBJECT, 'rel-near-before', 'rel-far', 'rel-twin-a', 'rel-twin-b',
                          'rel-region-ski', 'rel-region-tour', 'rel-act-near', 'rel-journal', 'rel-act-far', 'rel-act-nowhere'])

    def test_site_order_settles_what_is_left(self):
        # section 3: ... then site['published'] order: two trips of one tier on one day follow the site's order
        pub = slugs(self.site['published'])
        self.assertLess(pub.index('rel-twin-a'), pub.index('rel-twin-b'))
        got = self.rel(k=99)
        self.assertLess(got.index('rel-twin-a'), got.index('rel-twin-b'))
        swapped = list(self.site['published'])
        i, j = pub.index('rel-twin-a'), pub.index('rel-twin-b')
        swapped[i], swapped[j] = swapped[j], swapped[i]
        got2 = self.rel(site=self.site_with(swapped), k=99)
        self.assertEqual(got2, [{'rel-twin-a': 'rel-twin-b', 'rel-twin-b': 'rel-twin-a'}.get(s, s) for s in got])

    def test_never_the_report_itself(self):
        # section 3: never t
        for slug in slugs(self.site['published']):
            with self.subTest(slug):
                self.assertNotIn(slug, self.rel(slug, k=99))

    def test_never_a_planned_route(self):
        # section 3: never planned, even one in the same region and activity, and even if a site listed it as published
        self.assertEqual(self.by['rel-planned']['kind'], 'planned')
        self.assertNotIn('rel-planned', self.rel(k=99))
        leaky = self.site_with([self.by['rel-planned']] + self.site['published'])
        self.assertEqual(self.rel(site=leaky, k=99), ALL)

    def test_never_a_draft(self):
        # section 3: never drafts (they are not loaded)
        self.assertNotIn('rel-draft', self.by)
        self.assertNotIn('rel-draft', self.rel(k=99))
        self.assertTrue(os.path.exists(os.path.join(self.tmp, 'rel-draft', 'index.md')))   # the draft is on disk all the same

    def test_each_slug_once(self):
        # section 3: each slug once (a trip that shares the region and the activity is one candidate, and a site that
        # lists a trip twice still yields it once)
        for slug in slugs(self.site['published']):
            got = self.rel(slug, k=99)
            self.assertEqual(len(got), len(set(got)), slug)
        doubled = self.site_with(self.site['published'] + self.site['published'])
        self.assertEqual(self.rel(site=doubled, k=99), ALL)

    def test_nothing_unrelated_is_ever_returned(self):
        # section 3: candidates share t's region or t's activity
        got = self.rel(k=99)
        self.assertEqual(sorted(got), sorted(ALL))
        for slug in NEVER:
            self.assertNotIn(slug, got)
        for x in self.related(self.t, self.site, k=99):
            self.assertTrue(x['region'] == REGION or x['activity'] == 'hike', x['slug'])

    def test_a_subject_without_a_region_matches_on_activity_only(self):
        # section 3: candidates share t['region'] (when t has one) or t['activity']: two trips without a region do not
        # share one, so the regionless ski day is no candidate and the regionless hike of 2021 gets no region tier: it
        # takes its place by date among the other hikes
        t = self.by['rel-act-far']
        self.assertIsNone(t['region'])
        self.assertIsNone(self.by['rel-act-nowhere']['region'])
        got = self.rel('rel-act-far', k=99)
        self.assertEqual(got, ['rel-twin-a', 'rel-twin-b', 'rel-journal', 'rel-far', 'rel-act-nowhere', 'rel-near-before',
                               'rel-act-near', SUBJECT, 'rel-near-after', 'rel-later', 'rel-undated'])
        self.assertNotIn('rel-noregion-ski', got)
        self.assertTrue(all(self.by[s]['activity'] == 'hike' for s in got))
        gaps = [abs((self.by[s]['date'] - t['date']).days) for s in got[:-1]]
        self.assertEqual(gaps, sorted(gaps))

    def test_region_counts_across_activities(self):
        # section 3: (2) same region comes before (3) same activity only, from the other side: a ski day in 'Other Range'
        # is followed by that region's hikes, then by ski trips elsewhere
        self.assertEqual(self.rel('rel-elsewhere', k=99),
                         ['rel-act-near', 'rel-journal', 'rel-region-ski', 'rel-noregion-ski', 'rel-region-tour'])

    def test_multi_day_reports_and_series_are_candidates(self):
        # section 3: up to k published trips: any published kind, not only single-day reports
        got = self.rel(k=99)
        self.assertEqual(self.by['rel-region-tour']['kind'], 'multi-day')
        self.assertEqual(self.by['rel-journal']['kind'], 'series')
        self.assertIn('rel-region-tour', got)
        self.assertIn('rel-journal', got)

    def test_alone_in_the_site_gives_an_empty_list(self):
        # sections 3 and 7: empty when alone
        site = helpers.make_site([self.t])
        self.assertEqual(self.related(self.t, site), [])
        self.assertEqual(self.related(self.t, helpers.make_site([self.t, self.by['rel-planned']])), [])

    def test_no_shared_region_or_activity_gives_an_empty_list(self):
        # section 3: no candidate, no list
        site = helpers.make_site([self.by['rel-elsewhere'], self.by['rel-far'], self.by['rel-act-far']])
        self.assertEqual(self.related(self.by['rel-elsewhere'], site), [])

    def test_returns_the_sites_own_trip_dicts(self):
        # section 3: -> up to k published trips (the dicts of site['published'], ready for core.trip_card)
        got = self.related(self.t, self.site)
        self.assertIsInstance(got, list)
        for x in got:
            self.assertIs(x, self.by[x['slug']])

    def test_deterministic(self):
        # section 3: one transparent rule: the same answer every time, for the same site loaded again, and no side effect
        before = slugs(self.site['published'])
        first = self.rel(k=99)
        self.assertEqual(self.rel(k=99), first)
        self.assertEqual(slugs(self.site['published']), before)
        self.reload()
        self.assertEqual(self.rel(k=99), first)

    def test_the_subject_may_be_a_copy_of_its_trip_dict(self):
        # section 3: never t, by slug: a page that works on a copy of the dict still never recommends itself
        self.assertEqual(slugs(self.related(dict(self.t), self.site, k=99)), ALL)

    # ------------------------------------------------------------ skip (contract section 10.3)

    def test_skipped_reports_are_never_returned(self):
        # section 10.3: core.related(t, site, k=3, skip=()): reports in skip are never returned, whatever k; the others
        # keep their order
        skip = (self.by['rel-near-after'], self.by['rel-act-near'])
        left = [s for s in ALL if s not in ('rel-near-after', 'rel-act-near')]
        self.assertEqual(len(left), len(ALL) - 2)
        self.assertEqual(self.rel(k=99, skip=skip), left)
        for k in (0, 1, 2, 3, 5, 99):
            with self.subTest(k=k):
                got = self.rel(k=k, skip=skip)
                self.assertEqual(got, left[:k])
                self.assertFalse({'rel-near-after', 'rel-act-near'} & set(got))

    def test_the_next_reports_take_a_skipped_reports_place(self):
        # section 10.3: still up to k reports: skipping the two nearest brings in the next two
        self.assertEqual(self.rel(), ['rel-near-after', 'rel-near-before', 'rel-later'])
        skip = [self.by['rel-near-after'], self.by['rel-near-before']]
        self.assertEqual(self.rel(skip=skip), ['rel-later', 'rel-far', 'rel-twin-a'])

    def test_skip_is_the_fourth_parameter(self):
        # section 10.3: core.related(t, site, k=3, skip=())
        skip = (self.by['rel-near-after'],)
        self.assertEqual(slugs(self.related(self.t, self.site, 2, skip)), ['rel-near-before', 'rel-later'])
        self.assertEqual(self.related(self.t, self.site, 2, skip), self.related(self.t, self.site, k=2, skip=skip))

    def test_none_entries_in_skip_are_ignored(self):
        # section 10.3: None entries ignored (report.neighbours gives None at either end of an activity's run)
        self.assertEqual(self.rel(k=99, skip=(None, None)), ALL)
        self.assertEqual(self.rel(k=99, skip=[None]), ALL)
        self.assertEqual(self.rel(k=99, skip=(None, self.by['rel-near-before'])), [s for s in ALL if s != 'rel-near-before'])
        self.assertEqual(self.rel(k=99, skip=(self.by['rel-near-after'], None)), [s for s in ALL if s != 'rel-near-after'])

    def test_the_default_skips_nothing(self):
        # section 10.3: everything else is unchanged with the default
        for slug in slugs(self.site['published']):
            with self.subTest(slug):
                t = self.by[slug]
                self.assertEqual(self.related(t, self.site), self.related(t, self.site, 3, ()))
                self.assertEqual(self.related(t, self.site, 99), self.related(t, self.site, 99, skip=()))
                self.assertEqual(self.related(t, self.site, k=99, skip=[]), self.related(t, self.site, k=99))

    def test_skipping_a_report_that_was_no_candidate_changes_nothing(self):
        # section 10.3: skip only takes reports out: one that was never related (another region and activity, a goal, the
        # report itself) leaves the list as it was
        for slug in ('rel-elsewhere', 'rel-planned', SUBJECT):
            self.assertEqual(self.rel(k=99, skip=(self.by[slug],)), ALL, slug)

    def test_skipping_every_candidate_gives_an_empty_list(self):
        # sections 3 and 10.3: nothing left, no list
        self.assertEqual(self.rel(k=99, skip=[self.by[s] for s in ALL]), [])
        site = helpers.make_site([self.t, self.by['rel-near-after'], self.by['rel-near-before']])
        self.assertEqual(slugs(self.related(self.t, site)), ['rel-near-after', 'rel-near-before'])
        self.assertEqual(self.related(self.t, site, skip=(self.by['rel-near-after'], self.by['rel-near-before'])), [])

    def test_skip_is_left_as_it_was(self):
        # no side effect on what the caller passed, nor on the site
        skip = [self.by['rel-near-after'], None, self.by['rel-act-near']]
        before, pub = list(skip), slugs(self.site['published'])
        self.rel(k=99, skip=skip)
        self.assertEqual(len(skip), 3)
        self.assertTrue(all(a is b for a, b in zip(skip, before)))
        self.assertEqual(slugs(self.site['published']), pub)


# ---------------------------------------------------------------- core.related_block

class RelatedBlockTests(RelatedFixture):

    def setUp(self):
        super().setUp()
        self.related_block = need(self, core, 'related_block')
        self.sizes = need(self, core, 'RELATED_SIZES')

    def block(self, slug=SUBJECT, **kw):
        t = self.by[slug]
        return self.related_block(t, t['url'], self.site, **kw)

    def test_empty_string_when_nothing_is_related(self):
        # section 3: related_block -> '' when empty
        site = helpers.make_site([self.t])
        self.assertEqual(self.related_block(self.t, HERE, site), '')
        site = helpers.make_site([self.by['rel-elsewhere'], self.by['rel-far']])
        self.assertEqual(self.related_block(self.by['rel-elsewhere'], 'trips/rel-elsewhere/', site), '')

    def test_section_and_heading(self):
        # section 3: <section class="rep-related wrap sec" aria-labelledby="rel-h"><div class="shead"><h2 class="shead-t"
        # id="rel-h">More like this</h2>
        html_ = self.block()
        self.assertTrue(html_.startswith('<section class="rep-related wrap sec" aria-labelledby="rel-h"><div class="shead">'
                                         '<h2 class="shead-t" id="rel-h">More like this</h2><span class="shead-m t-mono-s">'), html_[:200])
        self.assertTrue(html_.endswith('</ul></section>'))
        doc = Doc(html_)
        self.assertEqual(len(doc.find_all('section')), 1)
        self.assertEqual([h.text() for h in doc.find_all('h2')], ['More like this'])

    def test_rule_line_says_how_the_reports_were_chosen(self):
        # section 3: core.meta_items of ['SAME REGION, THEN ACTIVITY', 'NEAREST IN DATE']
        line = Doc(self.block()).find('span', cls='shead-m')
        self.assertEqual(line.classes, ['shead-m', 't-mono-s'])
        self.assertEqual(ml_items(line), ['SAME REGION, THEN ACTIVITY', 'NEAREST IN DATE'])
        self.assertIsNotNone(line.find('span', cls='ml'))

    def test_rule_line_without_a_region(self):
        # section 3: first item 'SAME ACTIVITY' when t has no region
        line = Doc(self.block('rel-act-far')).find('span', cls='shead-m')
        self.assertEqual(ml_items(line), ['SAME ACTIVITY', 'NEAREST IN DATE'])

    def test_list_of_cards_in_related_order(self):
        # section 3: <ul class="rep-rel tgrid"> of li.tcard, one per related report, in core.related's order
        ul = Doc(self.block()).find('ul')
        self.assertEqual(ul.classes, ['rep-rel', 'tgrid'])
        cards = ul.elements()
        self.assertTrue(all(c.tag == 'li' and 'tcard' in c.classes for c in cards))
        self.assertEqual([c['data-slug'] for c in cards], self.rel())
        self.assertEqual(len(cards), 3)

    def test_cards_are_the_shared_trip_card(self):
        # section 3: core.trip_card(x, here, core.RELATED_SIZES, ns='rel')
        html_ = self.block()
        cards = ''.join(core.trip_card(x, HERE, self.sizes, ns='rel') for x in self.related(self.t, self.site))
        self.assertIn('<ul class="rep-rel tgrid">%s</ul>' % cards, html_)

    def test_whole_block(self):
        # section 3: the markup, whole
        rel = self.related(self.t, self.site)
        want = ('<section class="rep-related wrap sec" aria-labelledby="rel-h"><div class="shead"><h2 class="shead-t" id="rel-h">More like this</h2>'
                '<span class="shead-m t-mono-s">%s</span></div><ul class="rep-rel tgrid">%s</ul></section>'
                % (core.meta_items([core.nb('SAME REGION, THEN ACTIVITY'), core.nb('NEAREST IN DATE')]),
                   ''.join(core.trip_card(x, HERE, self.sizes, ns='rel') for x in rel)))
        self.assertEqual(self.block(), want)

    def test_card_ids_are_namespaced(self):
        # section 3: ns='rel': the cards' ids cannot collide with another list of cards
        doc = Doc(self.block())
        ids = [n['id'] for n in doc.root.walk() if n['id']]
        self.assertEqual(ids, ['rel-h'] + ['rel-%s-m' % s for s in self.rel()])
        for card, slug in zip(doc.find_all('li', cls='tcard'), self.rel()):
            self.assertEqual(card.find('h3').find('a')['aria-describedby'], 'rel-%s-m' % slug)

    def test_card_links_are_relative_to_the_page(self):
        # hard rule (relative links via core.link): from trips/<slug>/ a related report is ../../trips/<other>/
        doc = Doc(self.block())
        self.assertEqual([c.find('h3').find('a')['href'] for c in doc.find_all('li', cls='tcard')],
                         ['../../trips/%s/' % s for s in self.rel()])
        self.assertEqual([c.find('h3').find('a').text() for c in doc.find_all('li', cls='tcard')],
                         [self.by[s]['title'] for s in self.rel()])
        top = Doc(self.related_block(self.t, '', self.site))
        self.assertEqual(top.find('li', cls='tcard').find('h3').find('a')['href'], 'trips/rel-near-after/')

    def test_card_cover_uses_related_sizes(self):
        # section 3: core.RELATED_SIZES is the sizes attribute of a related card's cover
        self.assertIsInstance(self.sizes, str)
        self.assertTrue(self.sizes.strip())
        img = Doc(self.block()).find('li', attrs={'data-slug': 'rel-near-after'}).find('img', cls='cover-img')
        self.assertEqual(img['sizes'], self.sizes)
        self.assertEqual(img['loading'], 'lazy')   # never the page's lead image

    def test_a_cards_place_may_wrap(self):
        # section 10.4: the cards bring core.trip_card's place item to report pages: <span class="mi mi-w"> with ordinary
        # spaces, so a place wider than a narrow card's text column wraps instead of widening the page (the fixture
        # trips have no place, so the card shows the region); the date item stays one unbroken .mi
        cards = Doc(self.block()).find_all('li', cls='tcard')
        self.assertEqual(len(cards), 3)
        for card in cards:
            with self.subTest(card['data-slug']):
                date, place = card.find('p', cls='tcard-meta').find_all('span', cls='mi')
                self.assertEqual(place.classes, ['mi', 'mi-w'])
                self.assertEqual(place.text(clean=False), ', SYNTHETIC RANGE')
                self.assertNotIn('\xa0', place.text(clean=False))
                self.assertEqual(date.classes, ['mi'])
                self.assertEqual(date.text(clean=False), core.trip_date(self.by[card['data-slug']], short=True))
                self.assertNotIn(' ', date.text(clean=False))

    def test_k_is_passed_to_related(self):
        # section 3: related_block(t, here, site, k=3)
        for k in (1, 2, 5):
            cards = Doc(self.block(k=k)).find_all('li', cls='tcard')
            self.assertEqual([c['data-slug'] for c in cards], ALL[:k])
        self.assertEqual(self.block(), self.block(k=3))

    def test_block_never_lists_the_report_a_goal_or_a_draft(self):
        # section 3: never t, never planned, never drafts, each slug once
        for slug in slugs(self.site['published']):
            got = [c['data-slug'] for c in Doc(self.block(slug, k=99)).find_all('li', cls='tcard')]
            self.assertEqual(got, self.rel(slug, k=99), slug)
            self.assertNotIn(slug, got)
            self.assertNotIn('rel-planned', got)
            self.assertNotIn('rel-draft', got)
            self.assertEqual(len(got), len(set(got)))

    # ------------------------------------------------------------ skip (contract section 10.3)

    def test_skip_is_passed_to_related(self):
        # section 10.3: core.related_block(t, here, site, k=3, skip=()): the cards are related(t, site, k, skip)
        skip = (self.by['rel-near-after'], self.by['rel-near-before'])
        cards = Doc(self.block(skip=skip)).find_all('li', cls='tcard')
        self.assertEqual([c['data-slug'] for c in cards], ['rel-later', 'rel-far', 'rel-twin-a'])
        self.assertEqual([c['data-slug'] for c in cards], self.rel(skip=skip))
        for k in (1, 2, 5):
            cards = Doc(self.block(k=k, skip=skip)).find_all('li', cls='tcard')
            self.assertEqual([c['data-slug'] for c in cards], self.rel(k=k, skip=skip))
        self.assertEqual(self.related_block(self.t, HERE, self.site, 3, skip), self.block(skip=skip))   # the fifth parameter

    def test_skip_defaults_to_nothing_and_ignores_none(self):
        # section 10.3: unchanged with the default; None entries ignored
        self.assertEqual(self.block(skip=()), self.block())
        self.assertEqual(self.block(skip=(None, None)), self.block())
        one = self.by['rel-near-after']
        self.assertEqual(self.block(skip=(None, one)), self.block(skip=(one,)))
        self.assertNotEqual(self.block(skip=(one,)), self.block())

    def test_skip_changes_the_cards_and_says_so_in_the_rule_line(self):
        # section 10.3: the heading is unchanged; the rule line gains one item, so the printed rule stays the whole rule
        # (the nearest reports in date are the two the pager shows just below)
        skip = (self.by['rel-near-after'], self.by['rel-near-before'])
        html_ = self.block(skip=skip)
        self.assertEqual(html_.split('<span class="shead-m', 1)[0], self.block().split('<span class="shead-m', 1)[0])
        self.assertEqual(ml_items(Doc(html_).find('span', cls='shead-m')),
                         ['SAME REGION, THEN ACTIVITY', 'NEAREST IN DATE', 'NEWER / OLDER NOT REPEATED'])
        self.assertIn('<ul class="rep-rel tgrid">%s</ul>' % ''.join(core.trip_card(x, HERE, self.sizes, ns='rel')
                                                                   for x in self.related(self.t, self.site, skip=skip)), html_)

    def test_the_rule_line_names_the_pager_only_when_something_was_skipped(self):
        # nothing skipped (no pager on the page, or both ends missing): the two-item rule, exactly as without skip
        self.assertEqual(self.block(skip=()), self.block())
        self.assertEqual(self.block(skip=(None, None)), self.block())
        self.assertEqual(ml_items(Doc(self.block(skip=(None, None))).find('span', cls='shead-m')), ['SAME REGION, THEN ACTIVITY', 'NEAREST IN DATE'])
        # one neighbour is enough (the newest or the oldest report of an activity has only one)
        one = self.block(skip=(None, self.by['rel-near-before']))
        self.assertEqual(ml_items(Doc(one).find('span', cls='shead-m'))[-1], 'NEWER / OLDER NOT REPEATED')
        # a subject without a region keeps its own first item
        t = dict(self.t, region=None)
        line = Doc(self.related_block(t, HERE, self.site, skip=(self.by['rel-near-after'],))).find('span', cls='shead-m')
        self.assertEqual(ml_items(line), ['SAME ACTIVITY', 'NEAREST IN DATE', 'NEWER / OLDER NOT REPEATED'])

    def test_empty_string_when_every_related_report_is_skipped(self):
        # sections 3 and 10.3: '' when empty: never a heading above no cards
        both = (self.by['rel-near-after'], self.by['rel-near-before'])
        site = helpers.make_site([self.t] + list(both))
        self.assertTrue(self.related_block(self.t, HERE, site))
        self.assertTrue(self.related_block(self.t, HERE, site, skip=both[:1]))
        self.assertEqual(self.related_block(self.t, HERE, site, skip=both), '')


# ---------------------------------------------------------------- report.neighbours: the two reports of the pager

class NeighboursTests(RelatedFixture):

    def setUp(self):
        super().setUp()
        self.report = load_module(self, 'sitegen.pages.report')
        self.neighbours = need(self, self.report, 'neighbours')

    def pair(self, slug, site=None):
        """(newer, older) as slugs, None where there is none."""
        got = tuple(self.neighbours(self.by[slug], site or self.site))
        self.assertEqual(len(got), 2)
        return tuple(x['slug'] if x else None for x in got)

    def test_the_fixture_lists_its_reports_newest_first(self):
        # what the cases below stand on: site['published'] order, activity by activity
        pub = self.site['published']
        self.assertEqual([t['slug'] for t in pub if t['activity'] == 'hike'], HIKES)
        self.assertEqual([t['slug'] for t in pub if t['activity'] == 'ski'], SKIS)
        self.assertEqual(len(pub), len(HIKES) + len(SKIS))

    def test_a_report_in_the_middle_has_both(self):
        # section 10.3: (newer, older): the published reports of t's activity on either side of t
        self.assertEqual(self.pair(SUBJECT), ('rel-near-after', 'rel-act-near'))
        self.assertEqual(self.pair('rel-near-after'), ('rel-later', SUBJECT))
        self.assertEqual(self.pair('rel-region-ski'), ('rel-elsewhere', 'rel-noregion-ski'))

    def test_the_first_report_of_an_activity_has_no_newer_one(self):
        # section 10.3: None at an end
        self.assertEqual(self.pair('rel-later'), (None, 'rel-near-after'))
        self.assertEqual(self.pair('rel-elsewhere'), (None, 'rel-region-ski'))

    def test_the_last_report_of_an_activity_has_no_older_one(self):
        # section 10.3: None at an end (an undated report is the last of the site's list)
        self.assertEqual(self.pair('rel-undated'), ('rel-act-nowhere', None))
        self.assertEqual(self.pair('rel-region-tour'), ('rel-noregion-ski', None))

    def test_every_published_report(self):
        # section 10.3, for the whole site: the report before and the report after in the activity's run
        for run in (HIKES, SKIS):
            for i, slug in enumerate(run):
                with self.subTest(slug):
                    self.assertEqual(self.pair(slug), (run[i - 1] if i else None, run[i + 1] if i + 1 < len(run) else None))

    def test_reports_of_other_activities_are_stepped_over(self):
        # section 10.3: of t's activity: the two ski reports the site lists between two hikes are not their neighbours
        pub = slugs(self.site['published'])
        self.assertEqual(pub[pub.index('rel-near-after') + 1:pub.index(SUBJECT)], ['rel-elsewhere', 'rel-region-ski'])
        self.assertEqual(self.pair(SUBJECT)[0], 'rel-near-after')
        for t in self.site['published']:
            for x in self.neighbours(t, self.site):
                if x is not None:
                    self.assertEqual(x['activity'], t['activity'], t['slug'])
                    self.assertIsNot(x, t)

    def test_region_and_kind_do_not_matter(self):
        # section 10.3: activity and site order only: a journal, a multi-day trip and reports of another region are
        # neighbours like any other
        self.assertEqual(self.pair('rel-journal'), ('rel-far', 'rel-twin-a'))
        self.assertEqual(self.pair('rel-far'), ('rel-near-before', 'rel-journal'))
        self.assertEqual(self.by['rel-region-tour']['kind'], 'multi-day')
        self.assertEqual(self.pair('rel-noregion-ski'), ('rel-region-ski', 'rel-region-tour'))

    def test_a_goal_has_none(self):
        # section 10.3: (None, None) when t is not a published report
        t = self.by['rel-planned']
        self.assertNotIn(t, self.site['published'])
        self.assertEqual(tuple(self.neighbours(t, self.site)), (None, None))

    def test_a_draft_has_none(self):
        # section 10.3: (None, None) when t is not a published report: a draft is never in the site
        t = helpers.load(self.tmp, 'rel-draft')
        self.assertTrue(t['draft'])
        self.assertEqual(tuple(self.neighbours(t, self.site)), (None, None))

    def test_the_only_report_of_its_activity_has_none(self):
        # section 10.3: None at an end, here at both
        site = helpers.make_site([self.t, self.by['rel-elsewhere'], self.by['rel-region-ski']])
        self.assertEqual(tuple(self.neighbours(self.t, site)), (None, None))
        self.assertEqual(self.pair('rel-elsewhere', site), (None, 'rel-region-ski'))

    def test_site_order_decides_which_side(self):
        # section 10.3: in site['published'] order: 'newer' is whatever the site lists before t
        oldest_first = self.site_with(reversed(self.site['published']))
        self.assertEqual(self.pair(SUBJECT, oldest_first), ('rel-act-near', 'rel-near-after'))
        self.assertEqual(self.pair('rel-later', oldest_first), ('rel-near-after', None))

    def test_returns_the_sites_own_trip_dicts(self):
        # ready for core.related's skip and for the pager's links
        newer, older = self.neighbours(self.t, self.site)
        self.assertIs(newer, self.by['rel-near-after'])
        self.assertIs(older, self.by['rel-act-near'])

    def test_the_pager_links_to_the_neighbours(self):
        # section 10.3: report.pager uses it: Newer first, then Older, each only when there is one
        for slug in (SUBJECT, 'rel-later', 'rel-undated', 'rel-region-tour'):
            with self.subTest(slug):
                t = self.by[slug]
                newer, older = self.neighbours(t, self.site)
                want = [(lab, '../../' + x['url']) for lab, x in (('Newer', newer), ('Older', older)) if x]
                nav = Doc(self.report.pager(t, t['url'], self.site)).find('nav', cls='pager')
                self.assertEqual([(a.find('span', cls='pager-l').text(), a['href']) for a in nav.find_all('a')], want)

    def test_no_pager_without_neighbours(self):
        # section 10.3: the pager and 'More like this' agree on a page that has no pager: nothing to skip, no nav
        self.assertEqual(self.report.pager(self.by['rel-planned'], 'trips/rel-planned/', self.site), '')
        site = helpers.make_site([self.t, self.by['rel-region-ski']])
        self.assertEqual(self.report.pager(self.t, HERE, site), '')


# ---------------------------------------------------------------- which pages show the block

class RelatedPlacementTests(RelatedFixture):

    def setUp(self):
        super().setUp()
        self.related_block = need(self, core, 'related_block')
        self.report = load_module(self, 'sitegen.pages.report')
        self.neighbours = need(self, self.report, 'neighbours')

    def pager(self, main):
        """The report pager: the page's one nav.pager (the day pagers of a multi-day page are plain divs)."""
        navs = main.find_all('nav', cls='pager')
        self.assertEqual(len(navs), 1, 'the page has %d nav.pager elements' % len(navs))
        return navs[0]

    def pager_slugs(self, main):
        return [a['href'].rstrip('/').rsplit('/', 1)[-1] for a in self.pager(main).find_all('a')]

    def cards(self, main):
        return [c['data-slug'] for c in main.find('ul', cls='rep-rel').find_all('li', cls='tcard')]

    def assertBlockThenPager(self, main, activity):
        """Related reports, then the pager: the block is the element right before the page's nav.pager."""
        nav = self.pager(main)
        self.assertEqual(nav['aria-label'], 'More %s reports' % core.ACT[activity][0].lower())
        block = main.find('section', cls='rep-related')
        self.assertIsNotNone(block)
        els = main.elements()
        self.assertEqual(els.index(block) + 1, els.index(nav))
        order = list(main.walk())
        self.assertLess(order.index(main.by_id('rel-h')), order.index(nav))
        self.assertLess(order.index(main.find('ul', cls='rep-rel')), order.index(nav))

    def assertBlock(self, page, slug):
        """The page carries, once, the block of contract section 10.3: core.related_block with the two reports of the
        page's own pager skipped."""
        t = self.by[slug]
        want = self.related_block(t, t['url'], self.site, skip=self.neighbours(t, self.site))
        self.assertTrue(want)
        self.assertEqual(page.html.count(want), 1, '%s does not carry core.related_block exactly once' % slug)
        doc = Doc(page.html)
        self.assertEqual(len(doc.by_id('main').find_all('section', cls='rep-related')), 1)
        self.assertEqual(len(doc.find_all(attrs={'id': 'rel-h'})), 1)
        return doc

    def assertNoBlock(self, page):
        doc = Doc(page.html)
        self.assertIsNone(doc.find(cls='rep-related'))
        self.assertIsNone(doc.by_id('rel-h'))
        self.assertIsNone(doc.find(cls='rep-rel'))
        self.assertNotIn('More like this', page.html)

    def test_single_day_story_page_has_the_block(self):
        # section 3: shown on single-day report pages, both layouts: the story
        self.assertIs(need(self, self.report, 'narrative')(self.by['rel-near-after']), True)
        doc = self.assertBlock(self.report.page(self.by['rel-near-after'], self.site), 'rel-near-after')
        self.assertIn('p-report--story', doc.find('body').classes)

    def test_single_day_compact_page_has_the_block(self):
        # section 3: shown on single-day report pages, both layouts: the compact one
        doc = self.assertBlock(self.report.page(self.t, self.site), SUBJECT)
        self.assertNotIn('p-report--story', doc.find('body').classes)

    def test_the_block_sits_before_the_pager(self):
        # sections 2.8 and 3: related reports, then the pager, on both layouts
        for slug in (SUBJECT, 'rel-near-after'):
            with self.subTest(slug):
                self.assertBlockThenPager(Doc(self.report.page(self.by[slug], self.site).html).by_id('main'), 'hike')

    def test_multi_day_page_has_the_block_before_its_pager(self):
        # section 3: ... and multi-day pages before the pager
        multiday = load_module(self, 'sitegen.pages.multiday')
        page = multiday.page(self.by['rel-region-tour'], self.site)
        doc = self.assertBlock(page, 'rel-region-tour')
        self.assertBlockThenPager(doc.by_id('main'), 'ski')

    def test_more_like_this_never_repeats_the_pager_on_a_single_day_page(self):
        # section 10.3: single-day pages call core.related_block(t, here, site, skip=report.neighbours(t, site)): no card
        # is one of the two reports of the pager right below, and the block still offers three others
        cases = ((SUBJECT, ['rel-near-after', 'rel-act-near'], ['rel-near-before', 'rel-later', 'rel-far']),            # compact
                 ('rel-near-after', ['rel-later', SUBJECT], ['rel-near-before', 'rel-far', 'rel-twin-a']))             # story
        for slug, pager, cards in cases:
            with self.subTest(slug):
                self.assertTrue(set(self.rel(slug)) & set(pager))   # left alone, the rule would list a pager report
                main = Doc(self.report.page(self.by[slug], self.site).html).by_id('main')
                self.assertEqual(self.pager_slugs(main), pager)
                got = self.cards(main)
                self.assertFalse(set(got) & set(pager), 'More like this repeats the pager: %r' % got)
                self.assertEqual(got, cards)
                self.assertEqual(len(got), 3)
        self.assertEqual(set(self.rel('rel-near-after')) & {'rel-later', SUBJECT}, {'rel-later', SUBJECT})   # both, on the story

    def test_more_like_this_never_repeats_the_pager_on_a_multi_day_page(self):
        # section 10.3: multi-day pages too. A ski day in the tour's region four days after it is its Newer report and,
        # by the rule alone, its nearest related one
        helpers.make_trip(self.tmp, 'rel-tour-newer', title='Synthetic Tour Newer', activity='ski', date='2026-03-05', region=REGION, track=True)
        self.reload()
        t = self.by['rel-region-tour']
        self.assertEqual(self.rel('rel-region-tour'), ['rel-tour-newer', 'rel-region-ski', 'rel-near-before'])
        main = Doc(load_module(self, 'sitegen.pages.multiday').page(t, self.site).html).by_id('main')
        self.assertEqual(self.pager_slugs(main), ['rel-tour-newer'])
        got = self.cards(main)
        self.assertNotIn('rel-tour-newer', got)
        self.assertEqual(got, ['rel-region-ski', 'rel-near-before', SUBJECT])
        self.assertEqual(got, self.rel('rel-region-tour', skip=self.neighbours(t, self.site)))

    def test_no_block_when_the_pager_already_holds_every_related_report(self):
        # sections 3 and 10.3: '' when empty: a page whose only related reports are its Newer and Older ones has the
        # pager and no 'More like this'
        site = helpers.make_site([self.t, self.by['rel-near-after'], self.by['rel-near-before']])
        page = self.report.page(self.t, site)
        self.assertNoBlock(page)
        self.assertEqual(self.pager_slugs(Doc(page.html).by_id('main')), ['rel-near-after', 'rel-near-before'])

    def test_goal_page_has_no_block(self):
        # sections 3 and 7: not on goal pages, although the goal shares a region and an activity with published reports
        t = self.by['rel-planned']
        self.assertTrue(self.related(t, self.site))
        self.assertNoBlock(self.report.page(t, self.site))
        self.assertNoBlock(need(self, self.report, 'goal_page')(t, self.site))

    def test_series_page_has_no_block(self):
        # section 3: not on series pages, although the journal shares a region and an activity with published reports
        series = load_module(self, 'sitegen.pages.series')
        t = self.by['rel-journal']
        self.assertTrue(self.related(t, self.site))
        self.assertNoBlock(series.page(t, self.site))

    def test_a_report_with_nothing_related_has_no_block(self):
        # section 3: '' when empty: no heading without cards
        site = helpers.make_site([self.t])
        self.assertNoBlock(self.report.page(self.t, site))
        site = helpers.make_site([self.by['rel-region-tour']])
        self.assertNoBlock(load_module(self, 'sitegen.pages.multiday').page(self.by['rel-region-tour'], site))

    def test_no_page_lists_itself_a_goal_or_a_draft(self):
        # sections 3 and 10.3 on the built pages: never t, never planned, never drafts, never a report of the pager
        for slug in (SUBJECT, 'rel-near-after', 'rel-undated', 'rel-act-far', 'rel-elsewhere'):
            with self.subTest(slug):
                t = self.by[slug]
                main = Doc(self.report.page(t, self.site).html).by_id('main')
                got = self.cards(main)
                self.assertEqual(got, self.rel(slug, skip=self.neighbours(t, self.site)))
                self.assertLessEqual(len(got), 3)
                self.assertFalse({slug, 'rel-planned', 'rel-draft'} & set(got))
                self.assertFalse(set(self.pager_slugs(main)) & set(got))


# ---------------------------------------------------------------- core.copy_link

class CopyLinkTests(unittest.TestCase):

    URL = core.SITE_URL + 'trips/syn-copy/'

    def setUp(self):
        self.copy_link = need(self, core, 'copy_link')

    def parts(self, *args, **kw):
        root = Doc(self.copy_link(*args, **kw)).root
        self.assertEqual(len(root.elements()), 1)
        box = root.elements()[0]
        return box, box.find('button'), box.find('span', cls='copy-msg')

    def test_markup(self):
        # section 4: <span class="copy"><button type="button" class="<cls> copy-btn" data-copy="<url>">(icon)<span>Copy
        # link</span></button><span class="copy-msg t-small" role="status"></span></span>
        html_ = self.copy_link(self.URL)
        m = re.match(r'^<span class="copy"><button type="button" class="btn copy-btn" data-copy="([^"]*)">(<svg\b.*?</svg>)'
                     r'<span>Copy link</span></button><span class="copy-msg t-small" role="status"></span></span>$', html_, re.S)
        self.assertIsNotNone(m, html_)
        self.assertEqual(m.group(1), self.URL)

    def test_a_real_button_that_never_submits(self):
        # section 4: <button type="button">
        box, btn, _msg = self.parts(self.URL)
        self.assertEqual((box.tag, box.classes), ('span', ['copy']))
        self.assertEqual(btn.tag, 'button')
        self.assertEqual(btn['type'], 'button')
        self.assertEqual(box.find_all('a'), [])
        self.assertEqual(box.find_all('input'), [])

    def test_defaults_are_the_button_style_and_copy_link(self):
        # sections 4 and 10.1: core.copy_link(url, label='Copy link', cls='btn', of='')
        _box, btn, _msg = self.parts(self.URL)
        self.assertEqual(btn.classes, ['btn', 'copy-btn'])
        self.assertEqual(btn.text(), 'Copy link')
        self.assertEqual(self.copy_link(self.URL), self.copy_link(self.URL, 'Copy link', 'btn'))
        self.assertEqual(self.copy_link(self.URL), self.copy_link(self.URL, label='Copy link', cls='btn'))
        self.assertEqual(self.copy_link(self.URL), self.copy_link(self.URL, 'Copy link', 'btn', ''))
        self.assertEqual(self.copy_link(self.URL), self.copy_link(self.URL, label='Copy link', cls='btn', of=''))

    def test_data_copy_is_the_url(self):
        # section 4: data-copy="<url>": the absolute URL the caller passes (core.SITE_URL + here)
        _box, btn, _msg = self.parts(self.URL)
        self.assertEqual(btn['data-copy'], self.URL)
        self.assertTrue(btn['data-copy'].startswith('https://'))
        _box, btn, _msg = self.parts(self.URL + '#day-5-2')
        self.assertEqual(btn['data-copy'], self.URL + '#day-5-2')   # a series entry: the page URL plus its anchor

    def test_label_parameter(self):
        # section 4: 'Copy link to this page' / 'Copy link to this entry'
        for label in ('Copy link to this page', 'Copy link to this entry'):
            _box, btn, _msg = self.parts(self.URL, label)
            self.assertEqual(btn.text(), label)
            self.assertEqual(btn.elements()[-1].tag, 'span')
            self.assertEqual(btn.elements()[-1].text(), label)

    def test_cls_parameter(self):
        # section 4: cls='alink' for the share row and the series entries: '<cls> copy-btn'
        _box, btn, _msg = self.parts(self.URL, 'Copy link to this page', cls='alink')
        self.assertEqual(btn.classes, ['alink', 'copy-btn'])
        self.assertIn('class="alink copy-btn"', self.copy_link(self.URL, cls='alink'))

    def test_status_span_is_empty_and_announces(self):
        # section 4: <span class="copy-msg t-small" role="status"></span>, after the button, filled by base.js
        box, btn, msg = self.parts(self.URL)
        self.assertEqual(msg.classes, ['copy-msg', 't-small'])
        self.assertEqual(msg['role'], 'status')
        self.assertEqual(msg.children, [])
        self.assertEqual(box.elements(), [btn, msg])

    def test_the_status_is_always_rendered_and_the_fallback_field_never_is(self):
        # section 10.1: the status is always rendered: one empty role="status" element right after the button, whatever
        # the arguments, never hidden; the fallback field is not in the static markup (base.js appends its .copy-pop)
        for kw in ({}, {'cls': 'alink'}, {'of': 'Day 3'}, {'label': 'Copy link to this entry', 'cls': 'alink', 'of': 'Day 5.2'}):
            with self.subTest(**kw):
                html_ = self.copy_link(self.URL, **kw)
                self.assertTrue(html_.endswith('</button><span class="copy-msg t-small" role="status"></span></span>'), html_)
                box, btn, msg = self.parts(self.URL, **kw)
                self.assertEqual(box.elements(), [btn, msg])
                self.assertEqual(msg.children, [])
                self.assertEqual(box.find_all(attrs={'role': 'status'}), [msg])
                self.assertEqual(sorted(msg.attrs), ['class', 'role'])     # no hidden, no inline style
                self.assertEqual(box.find_all('input'), [])
                self.assertIsNone(box.find(cls='copy-url'))
                self.assertIsNone(box.find(cls='copy-pop'))
                self.assertEqual(btn.find_all(attrs={'role': 'status'}), [])   # the status is not inside the button

    def test_of_names_what_the_link_is_to(self):
        # section 10.1: with of='Day 3' the button ends ...<span>label</span><span class="sr">, Day 3</span></button>, so
        # each control of a page that repeats the label has its own accessible name
        html_ = self.copy_link(self.URL, 'Copy link to this entry', cls='alink', of='Day 3')
        self.assertIn('<span>Copy link to this entry</span><span class="sr">, Day 3</span></button>', html_)
        box, btn, _msg = self.parts(self.URL, 'Copy link to this entry', cls='alink', of='Day 3')
        self.assertEqual([e.tag for e in btn.elements()], ['svg', 'span', 'span'])
        label, sr = btn.elements()[1:]
        self.assertEqual((label.classes, label.text()), ([], 'Copy link to this entry'))
        self.assertEqual(sr.classes, ['sr'])
        self.assertEqual(sr.text(clean=False), ', Day 3')
        self.assertTrue(sr.text(clean=False).startswith(', '))
        self.assertEqual(box.find_all('span', cls='sr'), [sr])                     # inside the button and nowhere else
        self.assertEqual(btn.text(), 'Copy link to this entry, Day 3')             # the name a screen reader gives the button
        self.assertEqual(btn['data-copy'], self.URL)

    def test_of_gives_each_control_its_own_name(self):
        # section 10.1: the same label on every entry, a different name for each
        names = [self.parts(self.URL + '#day-%s' % a, 'Copy link to this entry', cls='alink', of='Day %s' % d)[1].text()
                 for d, a in (('1', '1'), ('5.2', '5-2'), ('31', '31'))]
        self.assertEqual(names, ['Copy link to this entry, Day 1', 'Copy link to this entry, Day 5.2', 'Copy link to this entry, Day 31'])
        self.assertEqual(len(set(names)), 3)

    def test_of_is_escaped(self):
        # section 10.1: (escaped): markup in a day label is text, and reads back unchanged
        of = 'Day <5.2> & "zero"'
        html_ = self.copy_link(self.URL, of=of)
        self.assertNotIn('<5.2>', html_)
        self.assertNotIn(' & ', html_)
        self.assertIn('Day &lt;5.2&gt; &amp; ', html_)
        _box, btn, _msg = self.parts(self.URL, of=of)
        self.assertEqual([e.tag for e in btn.elements()], ['svg', 'span', 'span'])
        self.assertEqual(btn.find('span', cls='sr').text(clean=False), ', ' + of)
        self.assertEqual(btn.find_all('span', cls='sr')[0].elements(), [])

    def test_markup_without_of_is_unchanged(self):
        # section 10.1: markup with of='' is unchanged: of adds its one span and touches nothing else
        for args, kw in (((self.URL,), {}), ((self.URL, 'Copy link to this page'), {'cls': 'alink'})):
            with self.subTest(args=args[1:], **kw):
                plain = self.copy_link(*args, **kw)
                self.assertEqual(self.copy_link(*args, of='', **kw), plain)
                self.assertNotIn('class="sr"', plain)
                _box, btn, _msg = self.parts(*args, **kw)
                self.assertEqual([e.tag for e in btn.elements()], ['svg', 'span'])
                named = self.copy_link(*args, of='Day 3', **kw)
                self.assertEqual(named.count('<span class="sr">, Day 3</span>'), 1)
                self.assertEqual(named.replace('<span class="sr">, Day 3</span>', ''), plain)
        self.assertEqual(self.copy_link(self.URL, 'Copy link', 'btn', 'Day 3'), self.copy_link(self.URL, of='Day 3'))   # the fourth parameter

    def test_icon_is_the_new_link_icon(self):
        # section 4: icon 'link', new in tools/lib/icons.py
        icons = load_module(self, 'icons')
        self.assertIn('link', icons.PATHS)
        _box, btn, _msg = self.parts(self.URL)
        self.assertEqual([e.tag for e in btn.elements()], ['svg', 'span'])
        self.assertEqual(btn.find('svg')['aria-hidden'], 'true')
        self.assertIn(icons.PATHS['link'], self.copy_link(self.URL))

    def test_url_and_label_are_escaped(self):
        # section 4 / the copy rules: attribute and text are escaped, and read back unchanged
        url = self.URL + '?a=1&b="2"#<x>'
        html_ = self.copy_link(url, 'Copy <this> & "that"')
        self.assertNotIn('"2"', html_)
        self.assertNotIn('<this>', html_)
        _box, btn, _msg = self.parts(url, 'Copy <this> & "that"')
        self.assertEqual(btn['data-copy'], url)
        self.assertEqual(btn.text(), 'Copy <this> & "that"')

    def test_no_noscript_and_no_inline_script(self):
        # section 4: the control is not rendered inside <noscript>; base.js listens for the click
        html_ = self.copy_link(self.URL)
        self.assertNotIn('noscript', html_)
        self.assertNotIn('onclick', html_)
        self.assertNotIn('<script', html_)


if __name__ == '__main__':
    unittest.main()
