"""tools/lib/checks.py: the warning for a trip the pre-rendered site maps still draw.

The Map page's region maps (and an activity page's map) are drawn by tools/render.py and committed under
rendered/site/; rendered/site/meta.json lists the trips each map draws. Drafting a trip, deleting its folder or removing
its track.gpx takes its page, its download and its own map off the site at the next build, but its line stays on those
shared maps until they are rendered again, and the build and its check pass meanwhile. The validator says so.
Everything here is synthetic and lives in a temp dir.
"""
import datetime
import importlib
import json
import os
import shutil
import tempfile
import unittest

import helpers

checks = importlib.import_module('checks')

TODAY = datetime.date(2026, 10, 10)
GPX = ('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1">\n'
       '<trk><name>Synthetic</name><trkseg><trkpt lat="10.001" lon="10.0"><ele>1</ele></trkpt>'
       '<trkpt lat="10.002" lon="10.01"><ele>2</ele></trkpt></trkseg></trk>\n</gpx>\n')
STILL = ('content/trips/%s/index.md: the site maps under rendered/site/ still draw this trip, which %s: its line and title '
         'stay on the pages that show those maps (the home page, the Map page, an activity page) until python3 '
         'tools/render.py has been run and rendered/site/ committed')


class SiteMapTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.realpath(tmp.name)
        self.trips = os.path.join(self.root, 'content', 'trips')
        self.rendered = os.path.join(self.root, 'rendered')
        self.home = os.path.join(self.root, 'content', 'home.json')
        os.makedirs(self.trips)
        for slug, meta in (('syn-ridge', {}), ('syn-lake', {}), ('syn-couloir', {'activity': 'ski'})):
            self.trip(slug, **meta)
        helpers.make_trip(self.trips, 'syn-tour', title='Synthetic Tour', kind='multi-day', date='2025-04-01', region='Synthetic Range',
                          days=[{'date': '2025-04-01'}, {'date': '2025-04-02'}])
        for day in ('01', '02'):
            self.write(os.path.join(self.trips, 'syn-tour', 'days', day + '.gpx'), GPX)
        self.write(self.home, json.dumps({'featured_slugs': []}))
        self.maps({'region-synthetic-range-desktop': ['syn-ridge', 'syn-lake', 'syn-tour'],
                   'region-synthetic-range-phone': ['syn-ridge', 'syn-lake', 'syn-tour'],
                   'ski-synthetic-range-desktop': ['syn-couloir']})

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)

    def trip(self, slug, **meta):
        meta.setdefault('date', '2025-06-15')
        folder = helpers.make_trip(self.trips, slug, title=slug.replace('-', ' ').title(), region='Synthetic Range', **meta)
        self.write(os.path.join(folder, 'track.gpx'), GPX)
        return folder

    def maps(self, drawn, **more):
        meta = {'hash': '', 'regions': ['Synthetic Range'], 'all_regions': ['Synthetic Range'],
                'maps': {name: {'w': 10, 'h': 10, 'region': 'Synthetic Range', 'trips': slugs} for name, slugs in drawn.items()}}
        meta.update(more)
        self.write(os.path.join(self.rendered, 'site', 'meta.json'), json.dumps(meta))

    def index(self, slug):
        return os.path.join(self.trips, slug, 'index.md')

    def add_line(self, slug, line):
        with open(self.index(slug), encoding='utf-8') as fh:
            text = fh.read()
        self.assertTrue(text.startswith('---\n'))
        self.write(self.index(slug), '---\n' + line + '\n' + text[4:])

    def found(self):
        got = checks.run(self.trips, self.home, self.rendered, TODAY)
        self.assertEqual([f['text'] for f in checks.errors(got)], [])
        return [f['text'] for f in checks.warnings(got) if 'site maps' in f['text']]

    def test_a_sound_site_has_no_such_warning(self):
        self.assertEqual(self.found(), [])
        # the fixture's only warnings are that no trip is rendered (it has no rendered/trips folder)
        others = [f['text'] for f in checks.warnings(checks.run(self.trips, self.home, self.rendered, TODAY))]
        self.assertEqual(len(others), 4)
        self.assertTrue(all('no rendered map' in text for text in others), others)

    def test_a_drafted_trip_is_still_drawn(self):
        self.add_line('syn-lake', 'draft: true')
        self.assertEqual(self.found(), [STILL % ('syn-lake', 'is a draft')])

    def test_a_removed_trip_is_still_drawn(self):
        shutil.rmtree(os.path.join(self.trips, 'syn-couloir'))
        self.assertEqual(self.found(), [STILL % ('syn-couloir', 'has no folder under content/trips any more')])

    def test_a_report_whose_track_was_removed_is_still_drawn(self):
        os.remove(os.path.join(self.trips, 'syn-ridge', 'track.gpx'))
        self.assertEqual(self.found(), [STILL % ('syn-ridge', 'has no track any more')])

    def test_a_multi_day_trip_counts_as_drawn_while_any_day_has_a_track(self):
        os.remove(os.path.join(self.trips, 'syn-tour', 'days', '01.gpx'))
        self.assertEqual(self.found(), [])
        os.remove(os.path.join(self.trips, 'syn-tour', 'days', '02.gpx'))
        self.assertEqual(self.found(), [STILL % ('syn-tour', 'has no track any more')])

    def test_one_line_per_trip_however_many_maps_draw_it_sorted_by_trip(self):
        self.add_line('syn-ridge', 'draft: true')
        self.add_line('syn-lake', 'draft: true')
        self.assertEqual(self.found(), [STILL % ('syn-lake', 'is a draft'), STILL % ('syn-ridge', 'is a draft')])

    def test_the_finding_is_a_warning_filed_under_the_trips_index(self):
        self.add_line('syn-lake', 'draft: true')
        mine = [f for f in checks.run(self.trips, self.home, self.rendered, TODAY) if 'site maps' in f['text']]
        self.assertEqual([(f['level'], f['file']) for f in mine], [('warning', 'content/trips/syn-lake/index.md')])

    def test_a_trip_that_does_not_load_gets_its_own_error_and_no_such_warning(self):
        self.write(self.index('syn-lake'), '---\ntitle: Synthetic Lake\n---\n')      # no activity: an error
        got = checks.run(self.trips, self.home, self.rendered, TODAY)
        self.assertEqual(len(checks.errors(got)), 1)
        self.assertEqual([f['text'] for f in got if 'site maps' in f['text']], [])

    def test_a_trip_no_map_draws_is_not_mentioned(self):
        self.trip('syn-new')
        self.add_line('syn-new', 'draft: true')
        self.assertEqual(self.found(), [])

    def test_a_file_this_check_cannot_read_says_nothing(self):
        for text in ('not json', '[]', json.dumps({'maps': []}), json.dumps({'maps': {'m': 'x', 'n': {'trips': 'syn-lake'}, 'o': {'trips': [5, None]}}})):
            with self.subTest(text=text[:20]):
                self.write(os.path.join(self.rendered, 'site', 'meta.json'), text)
                with open(self.index('syn-lake'), encoding='utf-8') as fh:
                    if 'draft: true' not in fh.read():
                        self.add_line('syn-lake', 'draft: true')
                got = checks.run(self.trips, self.home, self.rendered, TODAY)
                self.assertEqual([f['text'] for f in got if 'site maps' in f['text']], [])
                self.assertEqual([f['text'] for f in got if 'could not be checked' in f['text']], [])

    def test_without_a_rendered_folder_nothing_is_said(self):
        self.add_line('syn-lake', 'draft: true')
        shutil.rmtree(self.rendered)
        got = checks.run(self.trips, self.home, self.rendered, TODAY)
        self.assertEqual([f['text'] for f in got if 'site maps' in f['text']], [])


if __name__ == '__main__':
    unittest.main()
