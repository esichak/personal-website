"""tools/size_report.py (Phase 15, gap10-02) on synthetic trees: the kind classifier, the walk of a build (conflict
copies left out, a --link build's symlinks counted as their targets), growth grouped by trip date, the horizon
arithmetic, and the git parts on a throwaway repository (skipped without git), whose sizes must equal git ls-tree -l."""
import contextlib
import datetime
import importlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import helpers  # noqa: F401  (puts tools/ and tools/lib/ on sys.path)

size_report = importlib.import_module('size_report')
content = helpers.content


def write(path, size=0, data=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as fh:
        fh.write(data if data is not None else b'x' * size)


class KindTests(unittest.TestCase):

    def test_checkout_paths(self):
        cases = {
            'content/trips/synt-a/photos/01.webp': 'photo', 'content/trips/synt-a/photos/01.sm.webp': 'photo_sm',
            'content/trips/synt-a/photos/d002-03.th.jpg': 'photo_th', 'content/about/photos/portrait.JPG': 'photo',
            'content/trips/synt-a/track.gpx': 'gpx', 'content/trips/synt-a/days/01.gpx': 'gpx',
            'rendered/trips/synt-a/map-wide.webp': 'raster', 'rendered/site/region-synt-desktop.png': 'raster',
            'rendered/trips/synt-a/map-col.base.svg': 'base_svg', 'rendered/trips/synt-a/g64.svg.html': 'svg_html',
            'rendered/trips/synt-a/meta.json': 'meta', 'content/trips/synt-a/index.md': 'other',
            'content/trips/synt-a/goal.json': 'other', 'assets/apple-touch-icon.png': 'other',
            'tests/golden/render/synt.base.svg': 'other', 'rendered/trips/synt-a/notmeta.json': 'other',
        }
        self.assertEqual({p: size_report.kind(p) for p in cases}, cases)

    def test_build_paths(self):
        cases = {
            'trips/synt-a/photos/01.webp': 'photo', 'trips/synt-a/photos/01.th.webp': 'photo_th',
            'trips/synt-a/map/map-phone.webp': 'raster', 'trips/synt-a/map/map-phone.base.svg': 'base_svg',
            'assets/maps/region-synt-phone.webp': 'raster', 'trips/synt-a/synt-a.gpx': 'gpx',
            'trips/synt-a/index.html': 'other', 'trips/synt-a/g112.svg': 'other', 'map/index.html': 'other',
        }
        self.assertEqual({p: size_report.kind(p) for p in cases}, cases)

    def test_tally_sums_each_kind(self):
        t = size_report.tally({'a/photos/1.webp': 10, 'a/photos/2.webp': 5, 'a/t.gpx': 7, 'x.css': 1})
        self.assertEqual((t['files'], t['bytes']), (4, 23))
        self.assertEqual(t['kinds']['photo'], {'files': 2, 'bytes': 15})
        self.assertEqual(t['kinds']['gpx'], {'files': 1, 'bytes': 7})
        self.assertEqual(t['kinds']['raster'], {'files': 0, 'bytes': 0})


class WalkTests(unittest.TestCase):

    def test_copies_left_out_and_links_counted_as_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = os.path.join(tmp, 'checkout', 'content', 'trips', 'synt-a', 'photos', '01.webp')
            write(outside, 5000)
            site = os.path.join(tmp, 'site')
            write(os.path.join(site, 'trips', 'synt-a', 'index.html'), 120)
            write(os.path.join(site, 'trips', 'synt-a', 'index 2.html'), 999)            # a conflict copy
            write(os.path.join(site, 'trips', 'synt-a 3', 'index.html'), 999)            # a copied folder
            os.makedirs(os.path.join(site, 'trips', 'synt-a', 'photos'))
            os.symlink(outside, os.path.join(site, 'trips', 'synt-a', 'photos', '01.webp'))
            sizes, copies, links = size_report.walk(site)
        self.assertEqual(sizes, {'trips/synt-a/index.html': 120, 'trips/synt-a/photos/01.webp': 5000})
        self.assertEqual((copies, links), (2, 1))


class GrowthTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        r = self.root = tmp.name
        trips = os.path.join(r, 'content', 'trips')
        helpers.make_trip(trips, 'synt-ridge', title='Synthetic Ridge', date='2025-03-01')
        for name, size in (('01.webp', 1000), ('01.sm.webp', 300), ('01.th.webp', 100)):
            write(os.path.join(trips, 'synt-ridge', 'photos', name), size)
        write(os.path.join(trips, 'synt-ridge', 'track.gpx'), 2000)
        for name, size in (('map-wide.webp', 4000), ('map-wide.base.svg', 1000), ('meta.json', 10), ('meta 3.json', 77)):
            write(os.path.join(r, 'rendered', 'trips', 'synt-ridge', name), size)
        # no date of its own: a multi-day trip takes its first day's, so it belongs to 2024, not 2025
        helpers.make_trip(trips, 'synt-traverse', title='Synthetic Traverse', days=[{'date': '2024-12-30'}, {'date': '2025-01-02'}])
        write(os.path.join(trips, 'synt-traverse', 'days', '01.gpx'), 500)
        write(os.path.join(trips, 'synt-traverse', 'days', '02.gpx'), 700)
        helpers.make_trip(trips, 'synt-draft', title='Synthetic Draft', date='2025-06-01', draft=True)
        helpers.make_trip(trips, 'synt-someday', title='Synthetic Someday')            # no date at all
        write(os.path.join(r, 'rendered', 'trips', 'synt-someday', 'map-wide.webp'), 40)
        patcher = mock.patch.object(content, 'TRIPS_DIR', trips)
        patcher.start()
        self.addCleanup(patcher.stop)

    def rows(self, site=None):
        sizes = size_report.walk(self.root)[0]
        return size_report.growth(content.load_all(include_drafts=True), sizes, site)

    def test_grouped_by_trip_year(self):
        rows = self.rows()
        self.assertEqual(sorted(rows, key=str), [2024, 2025, 'undated'])
        y25 = rows[2025]
        self.assertEqual((y25['trips'], y25['photos'], y25['gpx'], y25['rendered'], y25['tracked']), (2, 1400, 2000, 5010, 8410))
        # photos and rasters whole, GPX at 17 %, the SVG and meta.json at 40 %; the conflict copy not at all
        self.assertAlmostEqual(y25['pack'], 1400 + 2000 * 0.17 + 4000 + 1000 * 0.40 + 10 * 0.40)
        self.assertEqual((rows[2024]['trips'], rows[2024]['gpx'], rows[2024]['tracked']), (1, 1200, 1200))
        self.assertEqual((rows['undated']['trips'], rows['undated']['rendered']), (1, 40))
        self.assertIsNone(y25['site'])

    def test_site_column_sums_each_trips_folder(self):
        site = {'trips/synt-ridge/index.html': 50, 'trips/synt-ridge/photos/01.webp': 1000,
                'trips/synt-traverse/index.html': 70, 'trips/index.html': 5, 'index.html': 999}
        rows = self.rows(site)
        self.assertEqual((rows[2025]['site'], rows[2024]['site'], rows['undated']['site']), (1050, 70, 0))

    def test_main_without_git_reads_the_files(self):
        out = io.StringIO()
        with mock.patch.object(size_report, 'git', side_effect=OSError('no git')), contextlib.redirect_stdout(out):
            self.assertEqual(size_report.main(['--json'], root=self.root, today=datetime.date(2026, 7, 2)), 0)
        r = json.loads(out.getvalue())
        self.assertEqual((r['tracked'], r['history'], r['site']), (None, None, None))
        self.assertEqual(r['growth']['2025']['tracked'], 8410)
        self.assertEqual(r['horizons']['last_full_year']['year'], 2025)
        self.assertIsNone(r['horizons']['last_full_year']['site_years'])                  # no build, no site horizon


class HorizonTests(unittest.TestCase):

    def test_years_to(self):
        self.assertEqual(size_report.years_to(1e9, 4e8, 1e8), 6.0)
        self.assertEqual(size_report.years_to(1e9, 1.2e9, 1e8), 0.0)
        self.assertIsNone(size_report.years_to(1e9, 4e8, 0))

    def test_last_full_year_and_this_year_so_far(self):
        rows = {2025: {'site': 100e6, 'pack': 80e6}, 2026: {'site': 50e6, 'pack': 30e6}, 2024: {'site': 1e9, 'pack': 1e9}}
        h = size_report.horizons(rows, 400e6, 200e6, datetime.date(2026, 7, 2))        # 2 July: day 183
        last, now = h['last_full_year'], h['this_year']
        self.assertEqual((last['year'], last['site_per_year'], last['site_years'], last['pack_years']), (2025, 100000000, 6.0, 10.0))
        self.assertEqual((now['year'], now['days']), (2026, 183))
        self.assertEqual(now['site_per_year'], round(50e6 * 365 / 183))
        self.assertEqual(now['site_years'], round(600e6 / (50e6 * 365 / 183), 2))
        self.assertEqual(now['pack_years'], round(800e6 / (30e6 * 365 / 183), 2))

    def test_no_build_and_a_quiet_year(self):
        h = size_report.horizons({}, None, 300e6, datetime.date(2026, 1, 1))
        self.assertIsNone(h['last_full_year']['site_years'])
        self.assertIsNone(h['last_full_year']['pack_years'])                            # nothing grew: never
        self.assertEqual(h['this_year']['days'], 1)


@unittest.skipUnless(shutil.which('git'), 'git is not installed')
class GitTests(unittest.TestCase):

    def git(self, *args):
        return subprocess.run(['git', '-C', self.root, '-c', 'commit.gpgsign=false'] + list(args), check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True).stdout

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Synthetic Tester')
        trips = os.path.join(self.root, 'content', 'trips')
        helpers.make_trip(trips, 'synt-loop', title='Synthetic Loop', date='2025-05-05')
        write(os.path.join(trips, 'synt-loop', 'photos', '01.webp'), 1234)
        write(os.path.join(trips, 'synt-loop', 'track.gpx'), 321)
        write(os.path.join(self.root, 'rendered', 'trips', 'synt-loop', 'meta.json'), data=b'{}')
        write(os.path.join(self.root, 'tools', 'empty.py'))                                 # index size 0: asked of git
        write(os.path.join(self.root, 'notes', 'a b.txt'), 9)
        self.git('add', '--', '.')
        self.git('commit', '-q', '-m', 'start')
        patcher = mock.patch.object(content, 'TRIPS_DIR', trips)
        patcher.start()
        self.addCleanup(patcher.stop)

    def ls_tree_l(self):
        out = {}
        for rec in self.git('ls-tree', '-r', '-l', '-z', 'HEAD').split('\0'):
            if rec:
                info, path = rec.split('\t', 1)
                out[path] = int(info.split()[3])
        return out

    def test_sizes_equal_ls_tree_l(self):
        self.assertEqual(size_report.tracked(self.root), self.ls_tree_l())

    def test_staged_change_and_fresh_index_still_give_heads_sizes(self):
        write(os.path.join(self.root, 'content', 'trips', 'synt-loop', 'track.gpx'), 50)
        self.git('add', '--', 'content')                                                     # the index now differs
        self.assertEqual(size_report.tracked(self.root)['content/trips/synt-loop/track.gpx'], 321)
        self.git('read-tree', 'HEAD')                                                        # every cached size 0
        self.assertEqual(size_report.tracked(self.root), self.ls_tree_l())

    def test_history_and_main(self):
        h = size_report.history(self.root)
        self.assertGreaterEqual(h['loose_objects'], 8)
        self.assertEqual(h['stored_bytes'], h['pack_bytes'] + max(h['loose_bytes'], h['loose_file_bytes']))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            size_report.main(['--json'], root=self.root, today=datetime.date(2026, 3, 1))
        r = json.loads(out.getvalue())
        self.assertEqual(r['tracked']['files'], 6)
        self.assertEqual(r['tracked']['kinds']['photo'], {'files': 1, 'bytes': 1234})
        self.assertEqual(r['tracked']['largest']['path'], 'content/trips/synt-loop/photos/01.webp')
        self.assertEqual(r['growth']['2025']['tracked'], 1234 + 321 + 2)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            size_report.main([], root=self.root, today=datetime.date(2026, 3, 1))
        text = out.getvalue()
        self.assertIn('grouped by each trip\'s date', text)
        self.assertIn('at the last full year\'s pace (2025', text)
        self.assertIn(size_report.LIMITS_URLS[0], text)


if __name__ == '__main__':
    unittest.main()
