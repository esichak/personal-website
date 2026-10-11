"""Phase 1: homepage curation from content/home.json (tools/sitegen/curation.py).

Every manifest here is written to a temp path and passed as `path` / `trips_dir`; content/home.json is never touched.
"""
import inspect
import json
import os
import sys
import tempfile
import unittest
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
from sitegen import curation  # noqa: E402

import helpers  # noqa: E402
from helpers import slugs  # noqa: E402

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


if __name__ == '__main__':
    unittest.main()
