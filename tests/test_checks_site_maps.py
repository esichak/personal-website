"""tools/lib/checks.py: the warning for a trip the pre-rendered site maps still draw.

The Map page's region maps (and an activity page's map) are drawn by tools/render.py and committed under
rendered/site/; rendered/site/meta.json lists the trips each map draws. Drafting a trip, deleting its folder or removing
its track.gpx takes its page, its download and its own map off the site at the next build, but its line stays on those
shared maps until they are rendered again, and the build and its check pass meanwhile. The validator says so.
Everything here is synthetic and lives in a temp dir.

Phase 6 (RenderHashTests, SiteHashTests): render.py stores in rendered/trips/<slug>/meta.json and rendered/site/meta.json
the hash of what it drew from (lib/renderkey.py), and the validator compares them with the trips as they are now. The
fixture writes those files with renderkey's own functions, the site hash over the live trips in content.load_all's
order (by folder, then newest first), so a clean fixture has no warning at all and each test breaks one thing.
"""
import datetime
import importlib
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import helpers

checks = importlib.import_module('checks')
content = importlib.import_module('content')
renderkey = importlib.import_module('renderkey')

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


# ---------------------------------------------------------------- Phase 6: maps drawn from other inputs

INDEX = 'content/trips/%s/index.md'
SITE_FILE = 'rendered/site/meta.json'
OTHER_INPUTS = ('maps were drawn from other inputs (the track, the title, activity, kind, map: or stats changed since): run '
                'python3 tools/render.py %s')
NO_OSM = ('maps were drawn without OpenStreetMap data (no roads, trails or lake names); run python3 tools/render.py %s '
          'again')
SITE_OTHER = ('the region and ski maps were drawn from other inputs (a trip on one of them changed, was added or was taken '
              'out since); run python3 tools/render.py --site and commit rendered/site/')
SITE_NO_OSM = ('the region and ski maps were drawn without OpenStreetMap data; run python3 tools/render.py --site again and '
               'commit rendered/site/')
GPX_MOVED = GPX.replace('lat="10.002"', 'lat="10.003"')     # the same track with one point moved


def warned(file, msg):
    """A warning as found() gives it: (file, text), the text starting with the file it is about."""
    return (file, '%s: %s' % (file, msg))


class RenderHashFixture(unittest.TestCase):
    """Three reports in one region (so a region map) with a track each, every one drawn as render.py leaves it:
    rendered/trips/<slug>/meta.json with the hash and the inputs of the trip as it is, and rendered/site/meta.json with
    the hash of the site maps. Folder order is not date order, so a site hash taken in any other order than
    content.load_all's does not match."""
    maxDiff = None

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.realpath(tmp.name)
        self.trips = os.path.join(self.root, 'content', 'trips')
        self.rendered = os.path.join(self.root, 'rendered')
        self.home = os.path.join(self.root, 'content', 'home.json')
        os.makedirs(self.trips)
        self.write(self.home, json.dumps({'featured_slugs': []}))
        for slug, day in (('syn-alpha', '2025-06-15'), ('syn-beta', '2025-07-01'), ('syn-gamma', '2025-06-15')):
            self.trip(slug, date=day)
            self.drawn(slug)
        self.site_drawn()

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)

    def trip(self, slug, gpx=GPX, **meta):
        meta.setdefault('title', slug.replace('-', ' ').title())
        meta.setdefault('region', 'Synthetic Range')
        folder = helpers.make_trip(self.trips, slug, **meta)
        self.write(os.path.join(folder, 'track.gpx'), gpx)
        return folder

    def live(self):
        """The trips as content.load_all gives them: no drafts, by folder, then newest first."""
        return helpers.load_dir(self.trips)

    def meta_file(self, slug):
        return os.path.join(self.rendered, 'trips', slug, 'meta.json')

    def drawn(self, slug, **changes):
        """rendered/trips/<slug>/meta.json as render.py writes it for the trip as it is now, with `changes` applied."""
        t = content.load_trip(os.path.join(self.trips, slug))
        meta = {'hash': renderkey.trip_inputs(t), 'inputs': renderkey.input_parts(t), 'slug': slug, 'kind': t['kind'],
                'maps': {}, 'charts': {}}
        meta.update(changes)
        self.write(self.meta_file(slug), json.dumps(meta))

    def site_drawn(self, **changes):
        """rendered/site/meta.json as render.py writes it for the live trips as they are now, with `changes` applied."""
        jobs, groups, mapped = renderkey.site_jobs(self.live())
        meta = {'hash': renderkey.site_hash(jobs), 'regions': sorted(mapped), 'all_regions': sorted(groups),
                'maps': {'%s-desktop' % j[0]: {'w': 718, 'h': 620, 'region': j[1], 'trips': [t['slug'] for t in j[2]]}
                         for j in jobs}}
        meta.update(changes)
        self.write(os.path.join(self.rendered, 'site', 'meta.json'), json.dumps(meta))

    def found(self):
        """(file, text) of every warning of a run; a run of this fixture never has an error."""
        got = checks.run(self.trips, self.home, self.rendered, TODAY)
        self.assertEqual([f['text'] for f in checks.errors(got)], [])
        return [(f['file'], f['text']) for f in checks.warnings(got)]


class RenderHashTests(RenderHashFixture):
    """A trip's rendered/trips/<slug>/meta.json against renderkey.trip_inputs of the trip as it is now."""

    def test_maps_drawn_from_the_trips_as_they_are_get_no_warning(self):
        self.assertEqual(self.found(), [])

    def test_a_hash_of_other_inputs_is_named_on_the_trips_index(self):
        self.drawn('syn-beta', hash='0' * 40)
        self.assertEqual(self.found(), [warned(INDEX % 'syn-beta', OTHER_INPUTS % 'syn-beta')])

    def test_a_track_changed_since_the_render_is_found(self):
        self.write(os.path.join(self.trips, 'syn-gamma', 'track.gpx'), GPX_MOVED)
        self.assertEqual(self.found(), [warned(INDEX % 'syn-gamma', OTHER_INPUTS % 'syn-gamma')])

    def test_a_title_changed_since_the_render_is_found(self):
        self.trip('syn-alpha', date='2025-06-15', title='Renamed Synthetic Alpha')
        self.assertEqual(self.found(), [warned(INDEX % 'syn-alpha', OTHER_INPUTS % 'syn-alpha')])

    def test_maps_drawn_without_osm_data_are_named(self):
        for changes in ({'hash': None, 'osm_failed': True}, {'hash': None}, {'osm_failed': True}):
            with self.subTest(changes=changes):
                self.drawn('syn-alpha', **changes)
                self.assertEqual(self.found(), [warned(INDEX % 'syn-alpha', NO_OSM % 'syn-alpha')])

    def test_a_meta_json_without_a_hash_key_says_nothing(self):
        for text in ('{}', json.dumps({'maps': {}, 'charts': {}})):
            with self.subTest(text=text):
                self.write(self.meta_file('syn-beta'), text)
                self.assertEqual(self.found(), [])

    def test_a_draft_says_nothing_whatever_its_render(self):
        self.trip('syn-draft', date='2025-08-01', draft=True)
        self.assertEqual(self.found(), [])                     # no meta.json, and no 'no rendered map' either
        for changes in ({'hash': '0' * 40}, {'hash': None}, {}):
            with self.subTest(changes=changes):
                self.drawn('syn-draft', **changes)
                self.assertEqual(self.found(), [])

    def test_a_track_icloud_has_offloaded_is_not_read(self):
        self.drawn('syn-beta', hash='0' * 40)
        with mock.patch.object(checks, '_offloaded', return_value=True):
            self.assertEqual(self.found(), [])


class SiteHashTests(RenderHashFixture):
    """rendered/site/meta.json against renderkey.site_hash(site_jobs(the live trips in content.load_all's order))."""

    def test_the_site_hash_is_taken_over_the_trips_in_content_load_all_order(self):
        live = self.live()
        by_folder = sorted(live, key=lambda t: t['slug'])
        self.assertNotEqual([t['slug'] for t in by_folder], [t['slug'] for t in live])
        self.assertEqual(self.found(), [])
        # the same trips hashed in folder order: another hash, so the maps count as drawn from other inputs
        self.site_drawn(hash=renderkey.site_hash(renderkey.site_jobs(by_folder)[0]))
        self.assertEqual(self.found(), [warned(SITE_FILE, SITE_OTHER)])

    def test_site_maps_drawn_from_other_inputs_are_named_on_rendered_site_meta_json(self):
        self.site_drawn(hash='0' * 40)
        self.assertEqual(self.found(), [warned(SITE_FILE, SITE_OTHER)])

    def test_a_trip_added_since_the_site_maps_were_drawn_is_found(self):
        self.trip('syn-delta', date='2025-05-01')
        self.drawn('syn-delta')
        self.assertEqual(self.found(), [warned(SITE_FILE, SITE_OTHER)])
        self.site_drawn()
        self.assertEqual(self.found(), [])

    def test_site_maps_drawn_without_osm_data_are_named(self):
        self.site_drawn(hash=None)
        self.assertEqual(self.found(), [warned(SITE_FILE, SITE_NO_OSM)])

    def test_a_site_meta_json_without_a_hash_key_says_nothing(self):
        self.site_drawn(hash='0' * 40)
        with open(os.path.join(self.rendered, 'site', 'meta.json'), encoding='utf-8') as fh:
            meta = json.load(fh)
        del meta['hash']
        self.write(os.path.join(self.rendered, 'site', 'meta.json'), json.dumps(meta))
        self.assertEqual(self.found(), [])

    def test_no_site_warning_while_a_trip_render_warning_is_in_the_run(self):
        # a new title makes the trip's maps and the site maps stale: only the trip's line is given
        self.trip('syn-gamma', date='2025-06-15', title='Renamed Synthetic Gamma')
        self.assertEqual(self.found(), [warned(INDEX % 'syn-gamma', OTHER_INPUTS % 'syn-gamma')])
        self.drawn('syn-gamma')                                # its own maps drawn again: the site maps' line is left
        self.assertEqual(self.found(), [warned(SITE_FILE, SITE_OTHER)])
        self.site_drawn(hash=None)
        self.drawn('syn-alpha', hash=None)
        self.assertEqual(self.found(), [warned(INDEX % 'syn-alpha', NO_OSM % 'syn-alpha')])


if __name__ == '__main__':
    unittest.main()
