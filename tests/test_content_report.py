"""tools/content_report.py (Phase 9, copy-07 and the listings after it) on a synthetic site in a temp dir: one row per
published report with what it has and lacks, the --missing filters, the title flags, the --alt listing of the most-seen
photos, the --taxonomy listing and its names to look at, the Markdown file, and that nothing under content/ is written.
Slugs start with 'sync-'; every title and name is synthetic."""
import contextlib
import importlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import helpers
from helpers import photo, LANDSCAPE
from sitegen import core, curation

import content

report = importlib.import_module('content_report')


def snapshot(folder):
    out = {}
    for dirpath, _dirs, names in os.walk(folder):
        for n in names:
            p = os.path.join(dirpath, n)
            with open(p, 'rb') as fh:
                out[os.path.relpath(p, folder)] = (fh.read(), os.stat(p).st_mtime_ns)
    return out


class ReportFixture(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.trips = os.path.join(self.root, 'content', 'trips')
        mk = helpers.make_trip
        mk(self.trips, 'sync-ridge', title='Synthetic Ridge Tour', activity='ski', date='2026-03-01', region='Synthetic Range',
           place='Synthetic Basin', party='A Friend', body='Synthetic words, written by hand.', track=True,
           photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic alt one', sm=True)], cover_photo='photos/01.webp',
           card_summary='A synthetic summary.')
        mk(self.trips, 'sync-ride-a', title='Ride near Synthetic Town', activity='mtb', date='2026-02-01', region='Synthetic Coast',
           place='Synthetic Saddle', track=True, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic alt two', sm=True)])
        mk(self.trips, 'sync-ride-b', title='Ride near Synthetic Town', activity='mtb', date='2026-01-01', region='Synthetic Coast',
           place='Synthetic Saddle Road', track=True)
        mk(self.trips, 'sync-lonely', title='Morning Hike', activity='hike', date='2025-06-01', region='Synthetic Island', track=True)
        mk(self.trips, 'sync-goal', title='Synthetic Goal', kind='planned', region='Synthetic Range')
        mk(self.trips, 'sync-draft', title='Synthetic Draft', date='2026-04-01', draft=True, track=True)
        with open(os.path.join(self.root, 'content', 'home.json'), 'w') as fh:
            json.dump({'featured_slugs': ['sync-ridge']}, fh)
        os.makedirs(os.path.join(self.root, 'rendered', 'site'))
        with open(os.path.join(self.root, 'rendered', 'site', 'meta.json'), 'w') as fh:
            json.dump({'hash': '', 'maps': {}, 'regions': [], 'all_regions': []}, fh)
        for target, name, value in ((content, 'TRIPS_DIR', self.trips), (content, 'RENDERED', os.path.join(self.root, 'rendered')),
                                    (core, 'ROOT', self.root), (core, '_SITE_META', []),
                                    (curation, 'HOME_JSON', os.path.join(self.root, 'content', 'home.json')),
                                    (report, 'ROOT', self.root)):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)

    def run_report(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = report.main(list(argv))
        return code, out.getvalue()


class TableTests(ReportFixture):

    def test_one_row_per_published_report_newest_first(self):
        code, out = self.run_report()
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith('DATE'))
        slugs = [ln.split()[1] for ln in lines[1:-1]]
        self.assertEqual(slugs, ['sync-ridge', 'sync-ride-a', 'sync-ride-b', 'sync-lonely'])     # no goal, no draft
        self.assertEqual(lines[-1], '4 reports')

    def test_what_a_row_says(self):
        rows = {r['slug']: r for r in report.rows(report.published()['published'])}
        r = rows['sync-ridge']
        self.assertEqual((r['date'], r['flag'], r['photos'], r['cover'], r['place'], r['party'], r['summary']),
                         ('2026-03-01', '', 1, 'explicit', 'Synthetic Basin', 'A Friend', 'yes'))
        self.assertEqual(r['writeup'], len('Synthetic words, written by hand.'))
        self.assertEqual((rows['sync-ride-a']['flag'], rows['sync-ride-a']['cover']), ('strava, x2', 'auto'))
        self.assertEqual((rows['sync-ride-b']['cover'], rows['sync-ride-b']['photos']), ('none', 0))
        self.assertEqual(rows['sync-lonely']['flag'], 'strava')

    def test_missing_filters(self):
        expect = {'place': ['sync-lonely'], 'writeup': ['sync-ride-a', 'sync-ride-b', 'sync-lonely'],
                  'photos': ['sync-ride-b', 'sync-lonely'], 'cover': ['sync-ride-a', 'sync-ride-b', 'sync-lonely'],
                  'summary': ['sync-ride-a', 'sync-ride-b', 'sync-lonely']}
        for what, slugs in expect.items():
            with self.subTest(missing=what):
                _code, out = self.run_report('--missing', what)
                self.assertEqual([ln.split()[1] for ln in out.splitlines()[1:-1]], slugs)
                self.assertEqual(out.splitlines()[-1], '%d report%s without %s' % (len(slugs), '' if len(slugs) == 1 else 's', what))

    def test_markdown_goes_to_the_cache_and_content_is_untouched(self):
        before = snapshot(os.path.join(self.root, 'content'))
        _code, out = self.run_report('--markdown')
        self.assertIn('wrote .cache/content-report.md (4 rows)', out)
        with open(os.path.join(self.root, '.cache', 'content-report.md')) as fh:
            md = fh.read()
        self.assertTrue(md.startswith('# Content report\n\n| Date | Slug | Title |'))
        self.assertIn('| sync-ride-a | strava, x2 |', md)
        for argv in ((), ('--alt',), ('--taxonomy',), ('--missing', 'place')):
            self.run_report(*argv)
        self.assertEqual(snapshot(os.path.join(self.root, 'content')), before)


class AltAndTaxonomyTests(ReportFixture):

    def test_alt_lists_the_home_features_and_every_cover(self):
        _code, out = self.run_report('--alt')
        self.assertIn("The home page's featured trips (content/home.json) (1)", out)
        self.assertIn('Every cover (explicit or automatic) (2)', out)
        home = out.split('\n\n')[0]
        self.assertIn('sync-ridge', home)
        self.assertIn('Synthetic alt one', home)
        self.assertIn('Synthetic alt two', out)

    def test_taxonomy_counts_regions_and_places_and_names_what_to_look_at(self):
        _code, out = self.run_report('--taxonomy')
        self.assertIn('3 regions (region: the map grouping; place: the named area inside it)', out)
        self.assertIn('Synthetic Coast', out)
        self.assertRegex(out, r'Synthetic Coast\s+synthetic-coast\s+2 reports')
        self.assertIn("places 'Synthetic Saddle' and 'Synthetic Saddle Road': one name inside the other; the same place?", out)
        self.assertIn('regions of one report (no region page; part of a larger region?): Synthetic Island', out)
        self.assertIn('1 reports without a place: python3 tools/content_report.py --missing place', out)

    def test_a_region_of_one_report_is_named_with_the_region_it_lies_near(self):
        # synthetic points: ~55 km apart, and one far from both; the points themselves are never printed
        pub = [{'slug': 'a', 'region': 'Synthetic Range', 'place': ''}, {'slug': 'b', 'region': 'Synthetic Range', 'place': ''},
               {'slug': 'c', 'region': 'Synthetic Outlier', 'place': ''}, {'slug': 'd', 'region': 'Synthetic Island', 'place': ''}]
        starts = {'a': (0.0, 0.0), 'b': (0.1, 0.0), 'c': (0.5, 0.0), 'd': (10.0, 10.0)}
        notes = report.taxonomy(pub, starts)[2]
        self.assertIn('regions of one report (no region page; part of a larger region?): Synthetic Island, '
                      'Synthetic Outlier (near Synthetic Range)', notes)
        self.assertNotIn('0.5', ' '.join(notes))
        self.assertIn('Synthetic Outlier, ', report.taxonomy(pub)[2][-1] + ', ')      # without starts: the names alone

    def test_two_spellings_of_one_region_are_named(self):
        _regs, _places, notes = report.taxonomy([{'region': 'Synthetic Coast', 'place': ''}, {'region': 'synthetic coast', 'place': ''}])
        self.assertIn("regions 'Synthetic Coast', 'synthetic coast' are one region (synthetic-coast) spelt 2 ways", notes)


if __name__ == '__main__':
    unittest.main()
