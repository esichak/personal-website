"""tools/lib/checks.py: rules added after the author's guides were followed literally on scratch content.

- an iCloud conflict copy inside a trip folder (a day file's copy is published as one more day: an error);
- a multi-day trip whose day files hold routes and no recorded track (the combined download would be empty);
- a track.gpx left beside day files (on no page);
- a day dated after the trip's stated end_date;
- a key written twice in the front matter (the parser keeps the last and says nothing).
Everything is synthetic and lives in a temp dir.
"""
import datetime
import importlib
import os
import tempfile
import unittest

import helpers

checks = importlib.import_module('checks')

TODAY = datetime.date(2026, 10, 10)
HEAD = '<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1">\n'
TRACK = HEAD + ('<trk><name>Synthetic</name><trkseg><trkpt lat="10.001" lon="10.0"><ele>1</ele></trkpt>'
                '<trkpt lat="10.002" lon="10.01"><ele>2</ele></trkpt></trkseg></trk>\n</gpx>\n')
ROUTE = HEAD + '<rte><name>Synthetic route</name><rtept lat="10.001" lon="10.0"/><rtept lat="10.002" lon="10.01"/></rte>\n</gpx>\n'
COPY_DAY = 'looks like an iCloud conflict copy (the name ends in a space and a number): it would be published as one more day; delete it'
COPY_OTHER = ('looks like an iCloud conflict copy (the name ends in a space and a number): nothing reads it, but git add of '
              'the folder would stage it; delete it')
NO_TRACKS = ('none of the day GPX files holds a recorded track (<trk>): "Download all GPX" would be an empty file; a day\'s '
             'file is that day\'s recording')
ROUTE_DAY = 'holds a route and no recorded track (<trk>): "Download all GPX" leaves this day out'
UNUSED = 'is not used: this trip has day files, and its page, maps and downloads come from days/NN.gpx; remove the file'


class Fixture(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.realpath(tmp.name)
        self.trips = os.path.join(self.root, 'content', 'trips')
        self.home = os.path.join(self.root, 'content', 'home.json')
        self.write(self.home, '{"featured_slugs": []}')
        self.walk = helpers.make_trip(self.trips, 'syn-walk', title='Synthetic Walk', date='2025-06-15', region='Synthetic Range')
        self.write(os.path.join(self.walk, 'track.gpx'), TRACK)
        self.tour = self.make_tour('syn-tour')

    def make_tour(self, slug, kind='multi-day', gpx=(TRACK, TRACK), **meta):
        days = [{'date': '2025-04-%02d' % (i + 1), 'id': ('%03d' if kind == 'series' else '%02d') % (i + 1)} for i in range(len(gpx))]
        folder = helpers.make_trip(self.trips, slug, title=slug.replace('-', ' ').title(), kind=kind, date='2025-04-01',
                                   region='Synthetic Range', days=days, **meta)
        for d, text in zip(days, gpx):
            path = os.path.join(folder, 'days', d['id'] + '.gpx')
            if text is None:
                os.remove(path)
            else:
                self.write(path, text)
        return folder

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)

    def copy(self, path, new):
        with open(path, encoding='utf-8') as fh:
            self.write(os.path.join(os.path.dirname(path), new), fh.read())

    def run_checks(self):
        return checks.run(self.trips, self.home, os.path.join(self.root, 'rendered'), TODAY)

    def found(self, level):
        return [f['text'] for f in self.run_checks() if f['level'] == level]

    def test_the_fixture_is_sound(self):
        self.assertEqual(self.found('error'), [])
        self.assertEqual(self.found('warning'), [])


class ConflictCopyTests(Fixture):

    def test_a_copy_of_a_day_file_stops_the_build(self):
        self.copy(os.path.join(self.tour, 'days', '02.md'), '02 2.md')
        self.assertEqual(self.found('error'), ['content/trips/syn-tour/days/02 2.md: ' + COPY_DAY])

    def test_a_copy_of_a_days_gpx_stops_it_too(self):
        self.copy(os.path.join(self.tour, 'days', '02.gpx'), '02 3.gpx')
        self.assertEqual(self.found('error'), ['content/trips/syn-tour/days/02 3.gpx: ' + COPY_DAY])

    def test_both_copies_are_named_one_line_each(self):
        self.copy(os.path.join(self.tour, 'days', '01.md'), '01 2.md')
        self.copy(os.path.join(self.tour, 'days', '01.gpx'), '01 2.gpx')
        self.assertEqual(self.found('error'), ['content/trips/syn-tour/days/01 2.gpx: ' + COPY_DAY,
                                               'content/trips/syn-tour/days/01 2.md: ' + COPY_DAY])

    def test_a_copy_of_index_md_or_the_track_is_a_warning(self):
        self.copy(os.path.join(self.walk, 'index.md'), 'index 2.md')
        self.copy(os.path.join(self.walk, 'track.gpx'), 'track 12.gpx')
        self.assertEqual(self.found('error'), [])
        self.assertEqual(self.found('warning'), ['content/trips/syn-walk/index 2.md: ' + COPY_OTHER,
                                                 'content/trips/syn-walk/track 12.gpx: ' + COPY_OTHER])

    def test_another_stray_file_in_days_is_a_warning_not_an_error(self):
        self.write(os.path.join(self.tour, 'days', 'notes 2.txt'), 'x')
        self.assertEqual(self.found('error'), [])
        self.assertEqual(self.found('warning'), ['content/trips/syn-tour/days/notes 2.txt: ' + COPY_OTHER])

    def test_names_that_only_look_alike_are_left_alone(self):
        self.write(os.path.join(self.walk, 'notes v2.txt'), 'x')
        self.write(os.path.join(self.walk, '2.txt'), 'x')
        self.assertEqual(self.found('error') + self.found('warning'), [])

    def test_a_trip_with_a_copied_day_is_still_counted_as_a_page_by_the_site_wide_checks(self):
        # the folder has an error, so it is not loaded; a link to it from another write-up is not a second error
        self.copy(os.path.join(self.tour, 'days', '02.md'), '02 2.md')
        with open(os.path.join(self.walk, 'index.md'), 'a', encoding='utf-8') as fh:
            fh.write('\nSee [the tour](../syn-tour/).\n')
        self.assertEqual(self.found('error'), ['content/trips/syn-tour/days/02 2.md: ' + COPY_DAY])


class DayTrackTests(Fixture):

    def test_a_tour_of_routes_only_is_an_error_on_its_index(self):
        self.make_tour('syn-routes', gpx=(ROUTE, ROUTE))
        self.assertEqual(self.found('error'), ['content/trips/syn-routes/index.md: ' + NO_TRACKS])

    def test_one_route_day_among_recorded_days_is_a_warning_on_that_file(self):
        self.make_tour('syn-mixed', gpx=(TRACK, ROUTE, TRACK))
        self.assertEqual(self.found('error'), [])
        self.assertEqual(self.found('warning'), ['content/trips/syn-mixed/days/02.gpx: ' + ROUTE_DAY])

    def test_a_track_tag_with_attributes_is_a_track(self):
        self.make_tour('syn-attr', gpx=(TRACK.replace('<trk>', '<trk xmlns:x="urn:x">'), TRACK.replace('<trk>', '<trk\n>')))
        self.assertEqual(self.found('error') + self.found('warning'), [])

    def test_trkseg_and_trkpt_alone_are_not_a_track_element(self):
        odd = HEAD + '<rte><rtept lat="10.0" lon="10.0"/></rte><!-- <trkseg> <trkpt> -->\n</gpx>\n'
        self.make_tour('syn-odd', gpx=(odd, odd))
        self.assertEqual(self.found('error'), ['content/trips/syn-odd/index.md: ' + NO_TRACKS])

    def test_a_tag_split_across_the_read_boundary_is_still_seen(self):
        pad = '<!-- %s -->\n' % ('x' * (checks._GPX_CHUNK - len(HEAD.encode()) - 12))
        text = HEAD + pad + TRACK[len(HEAD):]
        self.assertGreater(len(text.encode()), checks._GPX_CHUNK)
        self.make_tour('syn-split', gpx=(text, text))
        self.assertEqual(self.found('error') + self.found('warning'), [])

    def test_a_journal_of_routes_is_not_this_rules_business(self):
        # a journal has no combined download: each day links its own file
        self.make_tour('syn-journal', kind='series', gpx=(ROUTE, ROUTE))
        self.assertEqual(self.found('error') + self.found('warning'), [])

    def test_a_day_without_a_file_is_not_counted_as_a_route(self):
        self.make_tour('syn-gap', gpx=(TRACK, None, ROUTE))
        self.assertEqual(self.found('error'), [])
        self.assertEqual(self.found('warning'), ['content/trips/syn-gap/days/03.gpx: ' + ROUTE_DAY])

    def test_a_broken_day_file_keeps_its_own_error_and_is_not_called_a_route(self):
        self.make_tour('syn-bad', gpx=('', ROUTE))
        errors = self.found('error')
        self.assertEqual(len(errors), 2)
        self.assertTrue(errors[0].startswith('content/trips/syn-bad/days/01.gpx: the file is empty'), errors[0])
        self.assertEqual(errors[1], 'content/trips/syn-bad/index.md: ' + NO_TRACKS)


class UnusedTrackTests(Fixture):

    def test_a_track_beside_day_files_is_not_used(self):
        for kind in ('multi-day', 'series'):
            with self.subTest(kind=kind):
                folder = self.make_tour('syn-both-' + kind.replace('-', ''), kind=kind)
                self.write(os.path.join(folder, 'track.gpx'), TRACK)
                slug = os.path.basename(folder)
                self.assertEqual([w for w in self.found('warning') if slug in w], ['content/trips/%s/track.gpx: %s' % (slug, UNUSED)])
                self.assertEqual(self.found('error'), [])

    def test_a_single_day_reports_own_track_is_used(self):
        self.assertEqual(self.found('warning'), [])


class LateDayTests(Fixture):

    def add_line(self, folder, line):
        path = os.path.join(folder, 'index.md')
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
        self.write(path, '---\n' + line + '\n' + text[4:])

    def test_a_day_after_the_stated_end_is_named(self):
        self.add_line(self.tour, 'end_date: 2025-04-01')
        self.assertEqual(self.found('error'), [])
        self.assertEqual(self.found('warning'), ["content/trips/syn-tour/days/02.md: date 2025-04-02 is after the trip's end_date "
                                                 "2025-04-01 (index.md), so the page's dates end before this day"])

    def test_the_last_day_on_the_stated_end_is_fine(self):
        self.add_line(self.tour, 'end_date: 2025-04-02')
        self.assertEqual(self.found('error') + self.found('warning'), [])

    def test_without_an_end_date_nothing_is_said(self):
        self.assertEqual(self.found('warning'), [])


class RepeatedKeyTests(Fixture):

    def rewrite(self, path, old, new):
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
        self.assertIn(old, text)
        self.write(path, text.replace(old, new, 1))

    def test_a_key_written_twice_is_a_warning(self):
        self.rewrite(os.path.join(self.walk, 'index.md'), 'title: Synthetic Walk', 'title: Synthetic Walk\ntitle: Another Name')
        self.assertEqual(self.found('warning'), ["content/trips/syn-walk/index.md: key 'title' is written twice in the front matter; "
                                                 'only the last one is read'])

    def test_three_times_is_two_warnings_and_a_day_file_is_read_too(self):
        day = os.path.join(self.tour, 'days', '01.md')
        self.rewrite(day, 'date: 2025-04-01', 'date: 2025-04-01\ndate: 2025-04-01\ndate: 2025-04-01')
        self.assertEqual(self.found('warning'), ["content/trips/syn-tour/days/01.md: key 'date' is written twice in the front matter; "
                                                 'only the last one is read'] * 2)

    def test_the_same_word_inside_a_block_or_in_the_write_up_is_not_a_repeat(self):
        path = os.path.join(self.walk, 'index.md')
        self.rewrite(path, 'title: Synthetic Walk', 'title: Synthetic Walk\nstats:\n  distance_km: 5.0\nmap:\n  peaks: [Synthetic Peak]')
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write('\ntitle: this line is in the write-up\ndate: so is this\n')
        self.assertEqual(self.found('error') + self.found('warning'), [])

    def test_top_keys(self):
        self.assertEqual(checks._top_keys('---\na: 1\nb:\n  a: 2\n- a: 3\na: 4\n---\na: 5\n'), ['a', 'b', 'a'])
        self.assertEqual(checks._top_keys('no front matter\na: 1\n'), [])
        self.assertEqual(checks._top_keys('---\na: 1\nnever closed\n'), [])


if __name__ == '__main__':
    unittest.main()
