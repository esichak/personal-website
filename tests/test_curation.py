"""Phase 1: homepage curation from content/home.json (tools/sitegen/curation.py).

Every manifest here is written to a temp path and passed as `path` / `trips_dir`; content/home.json is never touched.

Review gate (fix D): a key written twice in the manifest is an error that names the key (json itself keeps the last
one and says nothing), in the top-level object or in one inside it. DuplicateKeyTests holds curation.load_manifest to
that; DuplicateKeyReportTests reads what the content checks (checks.run), tools/validate.py and tools/build.py say
about such a manifest, on the synthetic repository of tests/test_build_site.py: one ERROR line, and the build stops
before its output folder is touched.
"""
import contextlib
import importlib
import inspect
import io
import json
import os
import sys
import tempfile
import unittest
import warnings
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
from sitegen import core  # noqa: E402
from sitegen import curation  # noqa: E402

import helpers  # noqa: E402
from helpers import slugs  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

INITIAL = ['pacific-crest-trail-2024', 'matterhorn-peak-west-couloir', 'peak-bagging-szn']
EXTRAS = ['extra-a', 'extra-b', 'extra-c', 'extra-d']


class CurationTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.trips_dir = os.path.join(self.root, 'trips')
        os.makedirs(self.trips_dir)
        # the three contracted trips as they are in content/: PCT and Matterhorn carry featured: true, Peak Bagging does not
        helpers.make_series(self.trips_dir, 'pacific-crest-trail-2024', featured=True)
        helpers.make_trip(self.trips_dir, 'matterhorn-peak-west-couloir', title='Matterhorn Peak – West Couloir', activity='ski',
                          date='2026-01-17', place='Sawtooth Ridge', region='Eastern Sierra', featured=True,
                          body='Skinned up from Twin Lakes before dawn.', track=True,
                          photos=[helpers.photo('photos/01.webp', helpers.LANDSCAPE, alt='Granite spires above snow couloirs')])
        helpers.make_trip(self.trips_dir, 'peak-bagging-szn', title='PEAK BAGGING SZN', activity='hike', date='2025-08-10',
                          region='Eastern Sierra', body='A loop over three summits.', track=True,
                          photos=[helpers.photo('photos/01.webp', helpers.PORTRAIT), helpers.photo('photos/03.webp', helpers.LANDSCAPE)])
        for slug, d in zip(EXTRAS, ('2025-12-01', '2025-11-01', '2025-10-01', '2025-09-01')):
            helpers.make_trip(self.trips_dir, slug, activity='ski', date=d, track=True)
        helpers.make_trip(self.trips_dir, 'planned-route', activity='ski', kind='planned', date='2026-06-01', track=True)
        helpers.make_trip(self.trips_dir, 'secret-draft', activity='hike', date='2026-02-02', draft=True, body='Not yet.')
        self.trips = helpers.load_dir(self.trips_dir)      # drafts dropped, like content.load_all
        self.site = helpers.make_site(self.trips)

    # ------------------------------------------------------------ helpers

    def resolve(self, featured_slugs):
        return curation.resolve_featured(self.site, {'featured_slugs': featured_slugs}, trips_dir=self.trips_dir)

    def write_manifest(self, raw, name='home.json'):
        """Write a manifest file in the temp root (raw str as-is, anything else JSON-encoded) and return its path."""
        path = os.path.join(self.root, name)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(raw if isinstance(raw, str) else json.dumps(raw))
        return path

    def assertCurationError(self, featured_slugs, *needles):
        with self.assertRaises(curation.CurationError) as cm:
            self.resolve(featured_slugs)
        msg = str(cm.exception)
        self.assertTrue(msg.startswith('content/home.json: '), 'message must start with "content/home.json: ": %r' % msg)
        for needle in needles:
            self.assertIn(needle, msg)
        return msg

    # ------------------------------------------------------------ module surface

    def test_curation_error_is_a_value_error(self):
        self.assertTrue(issubclass(curation.CurationError, ValueError))

    def test_constants(self):
        self.assertEqual(curation.MAX_FEATURED, 6)
        self.assertTrue(os.path.isabs(curation.HOME_JSON))
        self.assertEqual(os.path.relpath(curation.HOME_JSON, ROOT), os.path.join('content', 'home.json'))

    def test_resolve_featured_defaults_trips_dir_to_content(self):
        self.assertEqual(inspect.signature(curation.resolve_featured).parameters['trips_dir'].default, content.TRIPS_DIR)

    # ------------------------------------------------------------ valid manifests

    def test_initial_three_resolve_in_order(self):
        self.assertEqual(slugs(self.resolve(INITIAL)), INITIAL)
        path = self.write_manifest({'featured_slugs': INITIAL})
        self.assertEqual(slugs(curation.featured_for(self.site, path=path)), INITIAL)

    def test_result_items_are_the_site_trips(self):
        for t, s in zip(self.resolve(INITIAL), INITIAL):
            self.assertIs(t, self.site['by_slug'][s])

    def test_reordering_manifest_reorders_result(self):
        order = [INITIAL[2], INITIAL[0], INITIAL[1]]
        self.assertEqual(slugs(self.resolve(order)), order)
        self.assertEqual(slugs(self.resolve(list(reversed(INITIAL)))), list(reversed(INITIAL)))

    def test_entry_counts_0_1_2_3_6_resolve_to_that_many_in_order(self):
        pool = INITIAL + EXTRAS[:3]
        for k in (0, 1, 2, 3, 6):
            with self.subTest(entries=k):
                out = self.resolve(pool[:k])
                self.assertEqual(len(out), k)
                self.assertEqual(slugs(out), pool[:k])

    def test_seven_entries_raise(self):
        pool = INITIAL + EXTRAS
        self.assertEqual(len(pool), 7)
        for s in pool:
            self.assertIn(s, self.site['by_slug'])     # every slug is valid: only the count is wrong
        self.assertCurationError(pool)

    def test_explicit_empty_list_returns_empty_and_never_substitutes_a_trip(self):
        self.assertEqual(self.resolve([]), [])
        path = self.write_manifest({'featured_slugs': []})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            self.assertEqual(curation.featured_for(self.site, path=path), [])
        self.assertEqual([w for w in caught if issubclass(w.category, UserWarning)], [])

    def test_featured_flag_in_front_matter_is_not_required_and_not_consulted(self):
        t = self.site['by_slug']['peak-bagging-szn']
        self.assertFalse(t['featured'])
        self.assertNotIn('featured', t['meta'])
        # listed without the flag -> resolves; flagged but not listed (Matterhorn, PCT) -> absent
        self.assertEqual(slugs(self.resolve(['peak-bagging-szn'])), ['peak-bagging-szn'])

    def test_newer_trip_does_not_displace_or_reorder_a_valid_selection(self):
        before = slugs(self.resolve(INITIAL))
        self.assertEqual(before, INITIAL)
        helpers.make_trip(self.trips_dir, 'brand-new-trip', activity='ski', date='2026-09-01', body='Fresh snow.', track=True,
                          featured=True)
        site2 = helpers.make_site(helpers.load_dir(self.trips_dir))
        self.assertEqual(site2['published'][0]['slug'], 'brand-new-trip')
        after = curation.resolve_featured(site2, {'featured_slugs': INITIAL}, trips_dir=self.trips_dir)
        self.assertEqual(slugs(after), before)

    # ------------------------------------------------------------ rejected manifests

    def test_duplicate_slug_raises_naming_slug_and_file(self):
        dup = 'matterhorn-peak-west-couloir'
        self.assertCurationError([dup, 'peak-bagging-szn', dup], dup, 'content/home.json')

    def test_unknown_slug_raises_saying_unknown_and_naming_it(self):
        msg = self.assertCurationError(['pacific-crest-trail-2024', 'no-such-trip'], 'no-such-trip')
        self.assertIn('unknown', msg.lower())

    def test_draft_slug_raises_saying_draft(self):
        self.assertNotIn('secret-draft', self.site['by_slug'])
        self.assertTrue(os.path.exists(os.path.join(self.trips_dir, 'secret-draft', 'index.md')))
        msg = self.assertCurationError(['secret-draft'], 'secret-draft')
        self.assertIn('draft', msg.lower())

    def test_draft_is_refused_as_a_draft_whatever_its_slug_says(self):
        # With the draft rule switched off the slug is still refused, as unknown (drafts are never in the site), so only
        # the message tells the two apart. The slug here does not contain the word the message is checked for.
        slug = 'quiet-ridge-walk'
        self.assertNotIn('draft', slug)
        helpers.make_trip(self.trips_dir, slug, title='Quiet Ridge Walk', activity='hike', date='2026-02-03', draft=True, body='Not yet.')
        site = helpers.make_site(helpers.load_dir(self.trips_dir))       # loaded again, as a build would: the draft is left out
        self.assertNotIn(slug, site['by_slug'])
        self.assertEqual(sorted(site['by_slug']), sorted(self.site['by_slug']))
        for featured in ([slug], ['peak-bagging-szn', slug]):
            with self.subTest(featured_slugs=featured):
                with self.assertRaises(curation.CurationError) as cm:
                    curation.resolve_featured(site, {'featured_slugs': featured}, trips_dir=self.trips_dir)
                msg = str(cm.exception)
                self.assertEqual(msg, "content/home.json: 'quiet-ridge-walk' is a draft (draft: true in its index.md); "
                                      "drafts cannot be featured")
                self.assertNotIn('unknown', msg.lower())
        # the day its draft line goes it is a report like any other, and can be featured
        helpers.make_trip(self.trips_dir, slug, title='Quiet Ridge Walk', activity='hike', date='2026-02-03', body='Not yet.')
        site = helpers.make_site(helpers.load_dir(self.trips_dir))
        self.assertEqual(slugs(curation.resolve_featured(site, {'featured_slugs': [slug]}, trips_dir=self.trips_dir)), [slug])

    def test_a_slug_with_no_folder_is_unknown_not_a_draft(self):
        # the other side of the same rule: 'draft' in a slug does not make it one
        for slug in ('no-such-trip', 'first-draft-of-nothing'):
            with self.subTest(slug=slug):
                self.assertFalse(os.path.exists(os.path.join(self.trips_dir, slug)))
                msg = self.assertCurationError([slug], slug)
                self.assertEqual(msg, "content/home.json: unknown slug '%s' in featured_slugs (no content/trips/%s/index.md)" % (slug, slug))
                self.assertNotIn('is a draft', msg)
        # nor does a folder: it is the draft line in its index.md that makes a draft. This report was written after the
        # site was loaded, so the site does not know it, and it is not called a draft for that
        helpers.make_trip(self.trips_dir, 'late-addition', activity='hike', date='2026-02-04', body='Written after the site was loaded.')
        self.assertNotIn('late-addition', self.site['by_slug'])
        msg = self.assertCurationError(['late-addition'], 'late-addition', 'unknown slug')
        self.assertNotIn('is a draft', msg)

    def test_planned_slug_raises_saying_planned(self):
        self.assertIn('planned-route', self.site['by_slug'])
        msg = self.assertCurationError(['matterhorn-peak-west-couloir', 'planned-route'], 'planned-route')
        self.assertIn('planned', msg.lower())

    def test_featured_slugs_missing_raises(self):
        with self.assertRaises(curation.CurationError) as cm:
            curation.resolve_featured(self.site, {}, trips_dir=self.trips_dir)
        msg = str(cm.exception)
        self.assertTrue(msg.startswith('content/home.json: '), msg)
        self.assertIn('featured_slugs', msg)
        with self.assertRaises(curation.CurationError):
            curation.resolve_featured(self.site, {'featured': INITIAL}, trips_dir=self.trips_dir)

    def test_featured_slugs_not_a_list_raises(self):
        for bad in ('pacific-crest-trail-2024', {'0': 'pacific-crest-trail-2024'}, None, 3, True):
            with self.subTest(value=bad):
                with self.assertRaises(curation.CurationError) as cm:
                    curation.resolve_featured(self.site, {'featured_slugs': bad}, trips_dir=self.trips_dir)
                self.assertTrue(str(cm.exception).startswith('content/home.json: '), str(cm.exception))

    def test_non_string_items_raise(self):
        for bad in ([1], [None], [['pacific-crest-trail-2024']], [{'slug': 'pacific-crest-trail-2024'}], [''],
                    ['pacific-crest-trail-2024', 2]):
            with self.subTest(items=bad):
                self.assertCurationError(bad)

    # ------------------------------------------------------------ the file

    def test_load_manifest_returns_the_object(self):
        path = self.write_manifest({'featured_slugs': INITIAL})
        self.assertEqual(curation.load_manifest(path), {'featured_slugs': INITIAL})

    def test_load_manifest_missing_file_is_none(self):
        self.assertIsNone(curation.load_manifest(os.path.join(self.root, 'absent.json')))

    def test_malformed_json_raises_curation_error(self):
        for raw in ('{"featured_slugs": [', '', 'featured_slugs: [a, b]', '{"featured_slugs": ["a",]}'):
            with self.subTest(raw=raw):
                path = self.write_manifest(raw)
                with self.assertRaises(curation.CurationError) as cm:
                    curation.load_manifest(path)
                self.assertTrue(str(cm.exception).startswith('content/home.json: '), str(cm.exception))
                with self.assertRaises(curation.CurationError):
                    curation.featured_for(self.site, path=path)

    def test_top_level_list_instead_of_object_raises(self):
        for raw in (INITIAL, 'pacific-crest-trail-2024', 3, None):
            with self.subTest(value=raw):
                path = self.write_manifest(raw)
                with self.assertRaises(curation.CurationError) as cm:
                    curation.load_manifest(path)
                self.assertTrue(str(cm.exception).startswith('content/home.json: '), str(cm.exception))

    def test_featured_for_combines_load_and_resolve(self):
        path = self.write_manifest({'featured_slugs': ['peak-bagging-szn', 'extra-b']})
        self.assertEqual(slugs(curation.featured_for(self.site, path=path)), ['peak-bagging-szn', 'extra-b'])
        bad = self.write_manifest({'featured_slugs': ['peak-bagging-szn', 'nope']}, name='bad.json')
        with self.assertRaises(curation.CurationError):
            curation.featured_for(self.site, path=bad)

    # ------------------------------------------------------------ legacy fallback (file absent)

    def test_missing_file_returns_legacy_featured_flag_pick_and_warns(self):
        path = os.path.join(self.root, 'absent.json')
        with self.assertWarns(UserWarning) as cm:
            out = curation.featured_for(self.site, path=path)
        self.assertIn('home.json', str(cm.warning))
        # legacy: the first featured-flagged published trip in newest-first order (Matterhorn 2026 before PCT 2024)
        self.assertEqual(slugs(out), ['matterhorn-peak-west-couloir'])

    def test_missing_file_legacy_pick_is_newest_published_when_nothing_is_flagged(self):
        unflagged = [t for t in self.trips if not t['featured']]
        site2 = helpers.make_site(unflagged)
        self.assertEqual(site2['trips'][0]['slug'], 'planned-route')      # newest overall, but planned
        self.assertEqual(site2['published'][0]['slug'], 'extra-a')
        with self.assertWarns(UserWarning):
            out = curation.resolve_featured(site2, None, trips_dir=self.trips_dir)
        self.assertEqual(slugs(out), ['extra-a'])

    def test_missing_file_with_no_published_trips_gives_empty_list(self):
        site3 = helpers.make_site([self.site['by_slug']['planned-route']])
        self.assertEqual(site3['published'], [])
        with self.assertWarns(UserWarning):
            self.assertEqual(curation.resolve_featured(site3, None, trips_dir=self.trips_dir), [])


class RegisteredSiteTests(unittest.TestCase):
    """contract-phase5.md section 1, as revised in round 2: helpers.make_site registers the site with core and hands
    over no site meta, so no region of a site made in a test has a page of its own and nothing is read from rendered/
    to find out. The fixture of this file (CurationTests.setUp, used here as it is) is the case that matters: two of
    its reports are filed under a region name that the site meta of a checkout may well map. The site meta here is a
    stand-in in a temp folder (core.ROOT points at it): one that would give that region a page if it were read."""

    def setUp(self):
        helpers.keep_state(self)          # first: what the tests register with core is put back
        fixture = CurationTests('test_constants')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root, self.trips_dir, self.trips, self.site = fixture.root, fixture.trips_dir, fixture.trips, fixture.site
        self.resolve = fixture.resolve
        self.checkout = os.path.join(self.root, 'checkout')
        site_dir = os.path.join(self.checkout, 'rendered', 'site')
        os.makedirs(site_dir)
        self.meta = {'hash': '', 'regions': ['Eastern Sierra'], 'all_regions': ['Eastern Sierra'],
                     'maps': {'region-eastern-sierra-%s' % size: {'w': 100, 'h': 80} for size in ('desktop', 'phone')}}
        with open(os.path.join(site_dir, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(self.meta, fh)
        patcher = mock.patch.object(core, 'ROOT', self.checkout)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_stand_in_meta_would_give_the_region_a_page(self):
        # the proof below is not an empty one: read and handed over, the meta gives the region its page
        self.assertEqual(core.read_site_meta(), self.meta)
        pages = core.region_pages(self.site, core.read_site_meta())
        self.assertEqual([(name, slug, slugs(ts)) for name, slug, ts in pages],
                         [('Eastern Sierra', 'eastern-sierra', ['matterhorn-peak-west-couloir', 'peak-bagging-szn'])])
        core.register_site(self.site, core.read_site_meta())
        self.assertEqual(core._REGION_PAGES, {'Eastern Sierra': 'eastern-sierra'})
        self.assertEqual(core.region_page_href('trips/peak-bagging-szn/', 'Eastern Sierra'), '../../regions/eastern-sierra/')

    def test_a_site_made_by_the_helper_has_no_region_page(self):
        with mock.patch.object(core, '_SITE_META', []) as cache:
            core.register_site(self.site, self.meta)                  # as if an earlier site had left its pages
            self.assertEqual(core._REGION_PAGES, {'Eastern Sierra': 'eastern-sierra'})
            site = helpers.make_site(self.trips)
            self.assertEqual(core._REGION_PAGES, {})
            self.assertIsNone(core.region_page_href('', 'Eastern Sierra'))
            self.assertIsNone(core.region_page_href('trips/peak-bagging-szn/', 'Eastern Sierra'))
            self.assertEqual(cache, [])                               # core's copy of the site meta was not filled: nothing was read
            self.assertEqual([t['slug'] for t in site['published'] if t['region'] == 'Eastern Sierra'],
                             ['matterhorn-peak-west-couloir', 'peak-bagging-szn'])

    def test_the_helper_reads_no_site_meta(self):
        def refuse(*args, **kwargs):
            raise AssertionError('helpers.make_site read a site meta')

        with mock.patch.object(core, '_SITE_META', []) as cache, mock.patch.object(core, 'read_site_meta', refuse), \
                mock.patch.object(core, 'site_meta', refuse), mock.patch.object(core, 'read_json', refuse):
            helpers.make_site(self.trips)
            helpers.make_site([])
            self.assertEqual((core._REGION_PAGES, cache), ({}, []))
        # curation, which this file is about, registers nothing and reads no site meta either
        with mock.patch.object(core, 'read_site_meta', refuse), mock.patch.object(core, 'site_meta', refuse):
            self.resolve(INITIAL)
            self.assertEqual(core._REGION_PAGES, {})

    def test_every_test_of_this_file_starts_and_ends_without_a_region_page(self):
        # the fixture's own setUp has registered its site by now, and so has every test that ran before this one
        self.assertEqual(core._REGION_PAGES, {})
        result = unittest.TestResult()
        CurationTests('test_initial_three_resolve_in_order').run(result)
        self.assertEqual((result.testsRun, result.errors, result.failures), (1, [], []))
        self.assertEqual(core._REGION_PAGES, {})


# ---------------------------------------------------------------- review gate, fix D: a key written twice

TWICE = 'content/home.json: "%s" is written twice; keep one'


class DuplicateKeyTests(unittest.TestCase):
    """curation.load_manifest on a manifest that names a key twice. The site and the temp folder are the fixture of
    CurationTests (its setUp, used as RegisteredSiteTests uses it)."""

    def setUp(self):
        fixture = CurationTests('test_constants')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root, self.site, self.write_manifest = fixture.root, fixture.site, fixture.write_manifest

    def error(self, raw):
        """The message load_manifest refuses this manifest text with (the test fails when it is not refused)."""
        path = self.write_manifest(raw, name='twice.json')
        with self.assertRaises(curation.CurationError) as cm:
            curation.load_manifest(path)
        return str(cm.exception)

    def test_featured_slugs_written_twice_is_refused_whichever_list_comes_last(self):
        a, b = json.dumps(INITIAL), json.dumps(['peak-bagging-szn', 'extra-a'])
        for first, last in ((a, b), (b, a), (a, a), (a, '[]'), ('[]', a), ('[]', '[]'), ('["no-such-trip"]', a), (a, '"not a list"')):
            with self.subTest(first=first, last=last):
                raw = '{"featured_slugs": %s, "featured_slugs": %s}' % (first, last)
                # json alone reads this without a word and keeps the last list
                self.assertEqual(json.loads(raw), {'featured_slugs': json.loads(last)})
                self.assertEqual(self.error(raw), 'content/home.json: "featured_slugs" is written twice; keep one')
                self.assertEqual(self.error(raw), TWICE % 'featured_slugs')
                with self.assertRaises(curation.CurationError) as cm:
                    curation.featured_for(self.site, path=self.write_manifest(raw, name='twice.json'))
                self.assertEqual(str(cm.exception), TWICE % 'featured_slugs')

    def test_it_is_refused_however_the_file_is_laid_out(self):
        for raw in ('{\n  "featured_slugs": ["extra-a"],\n\n  "featured_slugs": ["extra-b"]\n}\n',
                    '{"featured_slugs":["extra-a"],"note":"between","featured_slugs":["extra-b"]}',
                    '{"featured_slugs": ["extra-a"], "featured_slugs": ["extra-a"], "featured_slugs": ["extra-a"]}',
                    '{"featured_slugs": ["extra-a"], "featured\\u005fslugs": ["extra-b"]}'):      # the same key, escaped
            with self.subTest(raw=raw):
                self.assertEqual(self.error(raw), TWICE % 'featured_slugs')

    def test_another_key_written_twice_names_that_key(self):
        self.assertEqual(self.error('{"note": "one", "featured_slugs": ["extra-a"], "note": "two"}'), TWICE % 'note')
        self.assertEqual(self.error('{"featured_slugs": ["extra-a"], "tick_list_slugs": [], "tick_list_slugs": []}'), TWICE % 'tick_list_slugs')
        self.assertEqual(self.error('{"": 1, "": 2}'), TWICE % '')
        # the first key that comes round a second time is the one named
        self.assertEqual(self.error('{"b": 1, "a": 1, "a": 2, "b": 2}'), TWICE % 'a')
        # a key that only looks alike is another key
        path = self.write_manifest('{"featured_slugs": ["extra-a"], "Featured_slugs": [], "featured_slugs ": []}', name='alike.json')
        self.assertEqual(sorted(curation.load_manifest(path)), ['Featured_slugs', 'featured_slugs', 'featured_slugs '])

    def test_a_key_repeated_in_a_nested_object_is_caught_too(self):
        self.assertEqual(self.error('{"featured_slugs": ["extra-a"], "notes": {"why": "one", "why": "two"}}'), TWICE % 'why')
        self.assertEqual(self.error('{"featured_slugs": [{"slug": "extra-a", "slug": "extra-b"}]}'), TWICE % 'slug')
        self.assertEqual(self.error('{"a": {"b": {"c": [1, {"deep": 1, "deep": 1}]}}, "featured_slugs": []}'), TWICE % 'deep')
        # the same key in two different objects is written once in each
        path = self.write_manifest('{"featured_slugs": ["extra-a"], "x": {"note": 1}, "y": {"note": 2, "featured_slugs": 3}}', name='apart.json')
        self.assertEqual(curation.load_manifest(path), {'featured_slugs': ['extra-a'], 'x': {'note': 1}, 'y': {'note': 2, 'featured_slugs': 3}})

    def test_a_manifest_with_distinct_keys_loads_as_before(self):
        for data in ({'featured_slugs': INITIAL}, {'featured_slugs': []}, {}, {'featured_slugs': INITIAL, 'note': 'x', 'more': {'a': [1, {'b': None}]}},
                     {'featured': INITIAL}):
            with self.subTest(data=data):
                raw = json.dumps(data)
                loaded = curation.load_manifest(self.write_manifest(raw, name='once.json'))
                self.assertEqual(loaded, json.loads(raw))
                self.assertIs(type(loaded), dict)
                self.assertEqual(list(loaded), list(data))               # in the order written
        loaded = curation.load_manifest(self.write_manifest({'featured_slugs': INITIAL, 'more': {'a': 1}}, name='once.json'))
        self.assertIs(type(loaded['more']), dict)
        # and resolves as before, the unknown keys ignored here (the content checks warn about them)
        path = self.write_manifest({'note': 'x', 'featured_slugs': ['peak-bagging-szn', 'extra-b']}, name='once.json')
        self.assertEqual(slugs(curation.featured_for(self.site, path=path)), ['peak-bagging-szn', 'extra-b'])

    def test_invalid_json_still_says_not_valid_json(self):
        for raw in ('{"featured_slugs": [', '', 'featured_slugs: [a, b]', '{"featured_slugs": ["a",]}',
                    '{"featured_slugs": ["a"], "featured_slugs": ["b"]',          # twice, and the object is never closed
                    "{'featured_slugs': ['a'], 'featured_slugs': ['b']}"):
            with self.subTest(raw=raw):
                msg = self.error(raw)
                self.assertTrue(msg.startswith('content/home.json: not valid JSON ('), msg)
                self.assertTrue(msg.endswith(')'), msg)
                self.assertNotIn('written twice', msg)
        # and the message for a key written twice is that message alone, not wrapped as a JSON error
        msg = self.error('{"featured_slugs": [], "featured_slugs": []}')
        self.assertNotIn('not valid JSON', msg)
        self.assertEqual(msg.count('content/home.json'), 1)

    def test_the_other_refusals_keep_their_messages(self):
        self.assertEqual(self.error('["extra-a"]'),
                         'content/home.json: the top-level value must be a JSON object such as {"featured_slugs": [...]}')
        with self.assertRaises(curation.CurationError) as cm:
            curation.featured_for(self.site, path=self.write_manifest({'featured_slugs': ['extra-a', 'extra-a']}, name='dup.json'))
        self.assertEqual(str(cm.exception), "content/home.json: duplicate slug 'extra-a' in featured_slugs")
        self.assertIsNone(curation.load_manifest(os.path.join(self.root, 'absent.json')))


class DuplicateKeyReportTests(unittest.TestCase):
    """What a writer is told about a manifest with "featured_slugs" twice: by the content checks, by tools/validate.py
    and by tools/build.py, which stops before it touches its output folder. The content is the synthetic repository of
    tests/test_build_site.py (write_site) in a temp folder, with its home.json rewritten."""

    LINE = 'ERROR content/home.json: "featured_slugs" is written twice; keep one'
    RAW = '{\n  "featured_slugs": ["synb-story", "synb-tour"],\n  "featured_slugs": ["synb-tour"]\n}\n'

    def setUp(self):
        import test_build_site as fixture        # the module, for its fixture: none of its tests is loaded from here
        self.fixture = fixture
        self.build = importlib.import_module('build')
        self.checks = importlib.import_module('checks')
        self.validate = importlib.import_module('validate')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        fixture.write_site(self.root)
        self.content = os.path.join(self.root, 'content')
        self.home = os.path.join(self.content, 'home.json')
        self.out = os.path.join(self.root, '_site')

    def twice(self):
        with open(self.home, 'w', encoding='utf-8') as fh:
            fh.write(self.RAW)

    def run_checks(self):
        return self.checks.run(os.path.join(self.content, 'trips'), self.home, os.path.join(self.root, 'rendered'), self.fixture.TODAY)

    def captured(self, fn, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = fn(*args)
        return code, out.getvalue(), err.getvalue()

    def test_the_fixture_is_clean_until_the_key_is_written_twice(self):
        self.assertEqual(self.checks.errors(self.run_checks()), [])
        self.twice()
        self.assertEqual(json.loads(self.RAW), {'featured_slugs': ['synb-tour']})          # what json would have kept
        errors = self.checks.errors(self.run_checks())
        self.assertEqual(errors, [{'level': 'error', 'file': 'content/home.json',
                                   'text': 'content/home.json: "featured_slugs" is written twice; keep one'}])
        self.assertEqual([self.checks.line(f) for f in errors], [self.LINE])
        # one finding about the manifest, and no other: nothing is said about the slugs of a list that was not chosen
        self.assertEqual([f['text'] for f in self.run_checks() if f['file'] == 'content/home.json'], [errors[0]['text']])

    def test_validate_prints_the_one_error_line_and_exits_1(self):
        argv = ['--content', self.content, '--today', self.fixture.TODAY.isoformat(), '-q']
        code, out, err = self.captured(self.validate.main, argv)
        self.assertEqual((code, err), (0, ''))
        clean = out
        self.assertRegex(clean, r'\Acontent: 0 errors, \d+ warnings, \d+ notes \(10 trips, 3 photos, 8 GPX files\)\n\Z')
        self.twice()
        code, out, err = self.captured(self.validate.main, argv)
        self.assertEqual((code, err), (1, ''))
        self.assertEqual(out, self.LINE + '\n' + clean.replace('content: 0 errors', 'content: 1 errors'))
        code, out, _err = self.captured(self.validate.main, argv[:-1] + ['--json'])
        self.assertEqual(code, 1)
        self.assertEqual([f for f in json.loads(out) if f['level'] == 'error'],
                         [{'level': 'error', 'file': 'content/home.json', 'text': self.LINE[len('ERROR '):]}])

    def test_the_build_stops_with_that_line_before_the_output_folder_is_touched(self):
        self.twice()
        before = self.fixture.files_of(self.out)
        self.assertEqual(before, ['stale/index.html', 'trips/synb-gone/synb-gone.gpx'])     # what an earlier build left
        with self.fixture.redirected(self.root) as out_dir:
            self.assertEqual(out_dir, self.out)
            for argv in ([], ['--check'], ['--only', 'home']):
                with self.subTest(argv=argv):
                    code, out, err = self.captured(self.build.main, argv)
                    self.assertEqual((code, out, err), (1, '', self.LINE + '\n'))
                    self.assertEqual(self.fixture.files_of(self.out), before)
            # a folder named with --out is not made either
            other = os.path.join(self.root, 'elsewhere')
            code, out, err = self.captured(self.build.main, ['--out', other])
            self.assertEqual((code, out, err), (1, '', self.LINE + '\n'))
            self.assertFalse(os.path.exists(other))
        self.assertFalse(os.path.exists(os.path.join(self.out, self.build.BUILD_MARK)))

    def test_the_build_itself_refuses_the_manifest_should_the_checks_be_passed(self):
        # the second line of defence: build() reads the manifest (curation.featured_for) before it empties the output
        # folder, so with the content checks standing aside the same message stops it, and nothing has been removed
        self.twice()
        before = self.fixture.files_of(self.out)
        with self.fixture.redirected(self.root):
            with mock.patch.object(self.checks, 'run', lambda *a, **kw: []):
                code, out, err = self.captured(self.build.main, [])
            self.assertEqual((code, out, err), (1, '', self.LINE + '\n'))
            self.assertEqual(self.fixture.files_of(self.out), before)
            with self.assertRaises(curation.CurationError) as cm:
                self.build.build(verbose=False)
            self.assertEqual(str(cm.exception), TWICE % 'featured_slugs')
            self.assertEqual(self.fixture.files_of(self.out), before)

    def test_with_the_key_once_the_same_content_builds(self):
        # the control: the fixture as written builds, and the earlier build's files are replaced
        with self.fixture.redirected(self.root):
            code, _out, err = self.captured(self.build.main, [])
        self.assertEqual((code, err), (0, ''))
        files = self.fixture.files_of(self.out)
        self.assertIn('index.html', files)
        self.assertIn(self.build.BUILD_MARK, files)
        self.assertNotIn('stale/index.html', files)


if __name__ == '__main__':
    unittest.main()
