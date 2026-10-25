"""Phase 6: tools/lib/strava.py, the reader of a Strava bulk export (activities.csv beside activities/ and media/).

Every export here is a synthetic activities.csv written with csv.writer into a temp dir. A real export names two columns
'Distance' (the first in km, the second in metres) and two 'Elapsed Time'; HEADER does the same, and HEADER_ONE has one
of each, so record() is pinned on both shapes. Names, descriptions and ids are invented; the dates use Strava's own form
('Jul 4, 2026, 3:00:00 PM', UTC). Pinned: by_id (and its KeyError), search, record (the two-column rule, media and track
paths joined to the folder, the date format, short rows), stats_from, paragraphs and not_imported (known ids as int or
str, newest first, empty rows skipped, unreadable rows counted in .skipped and the count reset by the next call).
"""
import csv
import io
import os
import sys
import tempfile
import unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import strava  # noqa: E402

HEADER = ['Activity ID', 'Activity Date', 'Activity Name', 'Activity Type', 'Activity Description', 'Elapsed Time',
          'Distance', 'Filename', 'Elapsed Time', 'Moving Time', 'Distance', 'Elevation Gain', 'Elevation Loss',
          'Elevation Low', 'Elevation High', 'Media']
HEADER_ONE = ['Activity ID', 'Activity Date', 'Activity Name', 'Activity Type', 'Activity Description', 'Elapsed Time',
              'Distance', 'Filename', 'Moving Time', 'Elevation Gain', 'Elevation Loss', 'Elevation Low',
              'Elevation High', 'Media']


def row(act_id, when, name, kind='Hike', desc='', elapsed=('9000', '9300.0'), distance=('12.34', '12345.6'),
        filename='', moving='7200.0', gain='812.4', loss='799.6', low='1900.2', high='2700.4', media=''):
    """A row in HEADER's column order; elapsed and distance are the (first, second) column pair."""
    return [str(act_id), when, name, kind, desc, elapsed[0], distance[0], filename, elapsed[1], moving, distance[1],
            gain, loss, low, high, media]


def row_one(act_id, when, name, kind='Hike', elapsed='9000', distance='12.34', moving='7200.0'):
    """A row in HEADER_ONE's column order (one Distance, one Elapsed Time)."""
    return [str(act_id), when, name, kind, '', elapsed, distance, '', moving, '812.4', '799.6', '1900.2', '2700.4', '']


def write_export(folder, header, rows, tail=''):
    """activities.csv in `folder`: the header, the rows, then `tail` as raw text (blank lines and the like)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    with open(os.path.join(folder, 'activities.csv'), 'w', encoding='utf-8', newline='') as fh:
        fh.write(buf.getvalue() + tail)
    return folder


class ExportFixture(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = tmp.name

    def export(self, rows, header=HEADER, tail=''):
        write_export(self.folder, header, rows, tail)
        return strava.Export(self.folder)


class LookupTests(ExportFixture):

    def setUp(self):
        ExportFixture.setUp(self)
        self.ex = self.export([
            row(101, 'Jul 4, 2026, 3:00:00 PM', 'Synthetic Morning Loop'),
            row(102, 'Jun 1, 2026, 7:30:00 AM', 'Invented Ridge Ride', kind='Ride'),
            row(103, 'Aug 2, 2026, 6:15:00 AM', 'Evening loop walk', kind='Walk'),
        ])

    def test_the_header_row_is_kept_apart_from_the_rows(self):
        self.assertEqual(self.ex.hdr, HEADER)
        self.assertEqual(len(self.ex.rows), 3)

    def test_by_id_finds_the_row_with_that_activity_id(self):
        rec = self.ex.by_id('102')
        self.assertEqual((rec['id'], rec['name'], rec['type']), ('102', 'Invented Ridge Ride', 'Ride'))

    def test_by_id_takes_an_int_as_well(self):
        self.assertEqual(self.ex.by_id(103)['name'], 'Evening loop walk')

    def test_by_id_raises_key_error_for_an_id_not_in_the_export(self):
        with self.assertRaises(KeyError) as cm:
            self.ex.by_id('999')
        self.assertIn('999', str(cm.exception))

    def test_search_is_case_insensitive_in_the_names(self):
        self.assertEqual([r['id'] for r in self.ex.search('LOOP')], ['101', '103'])
        self.assertEqual([r['id'] for r in self.ex.search('ridge')], ['102'])
        self.assertEqual(self.ex.search('no such words'), [])

    def test_a_description_over_several_lines_is_one_activity(self):
        # csv.reader, not line splitting: a quoted description with line breaks stays in its row
        ex = self.export([row(201, 'Jul 4, 2026, 3:00:00 PM', 'Synthetic Loop', desc='First thought.\nSecond thought.'),
                          row(202, 'Jul 5, 2026, 3:00:00 PM', 'Second Loop')])
        self.assertEqual(len(ex.rows), 2)
        self.assertEqual(ex.by_id(201)['desc'], 'First thought.\nSecond thought.')


class RecordTests(ExportFixture):

    def test_with_two_distance_columns_the_second_in_metres_is_used(self):
        rec = self.export([row(1, 'Jul 4, 2026, 3:00:00 PM', 'A', distance=('12.34', '12345.6'))]).by_id(1)
        self.assertEqual(rec['distance_m'], 12345.6)

    def test_with_one_distance_column_it_is_read_as_km(self):
        rec = self.export([row_one(1, 'Jul 4, 2026, 3:00:00 PM', 'A', distance='12.34')], header=HEADER_ONE).by_id(1)
        self.assertAlmostEqual(rec['distance_m'], 12340.0, places=6)

    def test_the_second_elapsed_time_is_used_when_it_is_there(self):
        rec = self.export([row(1, 'Jul 4, 2026, 3:00:00 PM', 'A', elapsed=('9000', '9300.0'))]).by_id(1)
        self.assertEqual(rec['elapsed_s'], 9300.0)

    def test_an_empty_second_elapsed_time_falls_back_to_the_first(self):
        rec = self.export([row(1, 'Jul 4, 2026, 3:00:00 PM', 'A', elapsed=('9000', ''))]).by_id(1)
        self.assertEqual(rec['elapsed_s'], 9000.0)

    def test_one_elapsed_time_column_is_read(self):
        rec = self.export([row_one(1, 'Jul 4, 2026, 3:00:00 PM', 'A', elapsed='5400')], header=HEADER_ONE).by_id(1)
        self.assertEqual(rec['elapsed_s'], 5400.0)

    def test_media_paths_are_split_on_bars_and_joined_to_the_export_folder(self):
        rec = self.export([row(1, 'Jul 4, 2026, 3:00:00 PM', 'A', media='media/aa.jpg|media/bb.jpg')]).by_id(1)
        self.assertEqual(rec['media'], [os.path.join(self.folder, 'media', 'aa.jpg'),
                                        os.path.join(self.folder, 'media', 'bb.jpg')])

    def test_no_media_is_an_empty_list(self):
        self.assertEqual(self.export([row(1, 'Jul 4, 2026, 3:00:00 PM', 'A')]).by_id(1)['media'], [])

    def test_the_track_file_is_joined_to_the_folder_and_none_without_one(self):
        ex = self.export([row(1, 'Jul 4, 2026, 3:00:00 PM', 'A', filename='activities/1.fit.gz'),
                          row(2, 'Jul 4, 2026, 3:00:00 PM', 'B')])
        self.assertEqual(ex.by_id(1)['file'], os.path.join(self.folder, 'activities', '1.fit.gz'))
        self.assertIsNone(ex.by_id(2)['file'])

    def test_the_activity_date_is_read_in_stravas_form_as_a_utc_clock(self):
        ex = self.export([row(1, 'Jul 4, 2026, 3:00:00 PM', 'A'), row(2, 'Jan 9, 2025, 9:05:07 AM', 'B'),
                          row(3, 'Dec 31, 2025, 12:00:00 AM', 'C')])
        self.assertEqual(ex.by_id(1)['date_utc'], datetime(2026, 7, 4, 15, 0, 0))
        self.assertEqual(ex.by_id(2)['date_utc'], datetime(2025, 1, 9, 9, 5, 7))
        self.assertEqual(ex.by_id(3)['date_utc'], datetime(2025, 12, 31, 0, 0, 0))
        self.assertIsNone(ex.by_id(1)['date_utc'].tzinfo)

    def test_a_date_in_another_form_is_a_value_error(self):
        ex = self.export([row(1, '2026-07-04 15:00:00', 'A')])
        with self.assertRaises(ValueError):
            ex.by_id(1)

    def test_names_and_descriptions_are_stripped_and_numbers_read(self):
        rec = self.export([row(1, 'Jul 4, 2026, 3:00:00 PM', '  Synthetic Loop  ', desc='  A line.  ')]).by_id(1)
        self.assertEqual((rec['name'], rec['desc']), ('Synthetic Loop', 'A line.'))
        self.assertEqual((rec['moving_s'], rec['gain_m'], rec['loss_m'], rec['low_m'], rec['high_m']),
                         (7200.0, 812.4, 799.6, 1900.2, 2700.4))

    def test_a_short_row_reads_its_missing_cells_as_empty(self):
        full = row(1, 'Jul 4, 2026, 3:00:00 PM', 'Short one', distance=('12.34', '12345.6'), media='media/aa.jpg')
        ex = self.export([full[:8]])     # cut after Filename: no second Elapsed Time, second Distance, elevations, Media
        rec = ex.by_id(1)
        self.assertEqual(rec['name'], 'Short one')
        self.assertEqual(rec['media'], [])
        self.assertEqual(rec['elapsed_s'], 9000.0)
        self.assertAlmostEqual(rec['distance_m'], 12340.0, places=6)
        self.assertEqual((rec['moving_s'], rec['gain_m'], rec['loss_m'], rec['low_m'], rec['high_m']),
                         (None, None, None, None, None))


class StatsAndParagraphTests(ExportFixture):

    def test_stats_from_a_full_record(self):
        rec = self.export([row(1, 'Jul 4, 2026, 3:00:00 PM', 'A')]).by_id(1)
        self.assertEqual(strava.stats_from(rec), {'distance_km': 12.35, 'moving': '2:00', 'elapsed': '2:35',
                                                  'gain_m': 812, 'loss_m': 800, 'high_m': 2700, 'low_m': 1900})

    def test_stats_from_leaves_out_what_the_record_lacks(self):
        rec = self.export([row(1, 'Jul 4, 2026, 3:00:00 PM', 'A', distance=('0', '0'), moving='', elapsed=('', ''),
                               gain='0', loss='', low='', high='')]).by_id(1)
        # no distance or time to state; a recorded gain of 0 m is still a value
        self.assertEqual(strava.stats_from(rec), {'gain_m': 0})

    def test_paragraphs_makes_each_non_empty_line_its_own_paragraph(self):
        self.assertEqual(strava.paragraphs('First thought.\nSecond thought.'), 'First thought.\n\nSecond thought.')
        self.assertEqual(strava.paragraphs('  One. \r\n\r\n\n  Two.  \n'), 'One.\n\nTwo.')

    def test_paragraphs_of_nothing_is_empty(self):
        self.assertEqual(strava.paragraphs(''), '')
        self.assertEqual(strava.paragraphs(None), '')
        self.assertEqual(strava.paragraphs('\n \n'), '')


class NotImportedTests(ExportFixture):

    def setUp(self):
        ExportFixture.setUp(self)
        self.rows = [
            row(101, 'Jul 4, 2026, 3:00:00 PM', 'Synthetic Morning Loop'),
            row(102, 'Jun 1, 2026, 7:30:00 AM', 'Invented Ridge Ride', kind='Ride'),
            row(103, 'Aug 2, 2026, 6:15:00 AM', 'Evening loop walk', kind='Walk'),
            row(104, 'Jan 9, 2025, 9:05:07 AM', 'Old Synthetic Hike'),
        ]

    def ids(self, recs):
        return [r['id'] for r in recs]

    def test_every_activity_newest_first_when_none_is_known(self):
        ex = self.export(self.rows)
        self.assertEqual(self.ids(ex.not_imported(set())), ['103', '101', '102', '104'])
        self.assertEqual(ex.skipped, 0)

    def test_known_ids_as_int_or_str_are_left_out(self):
        ex = self.export(self.rows)
        self.assertEqual(self.ids(ex.not_imported({101, '103'})), ['102', '104'])
        self.assertEqual(self.ids(ex.not_imported(['102', 104])), ['103', '101'])

    def test_empty_rows_are_skipped_without_being_counted(self):
        ex = self.export(self.rows, tail='\n,,,,,,,,,,,,,,,\n\n')
        self.assertEqual(len(ex.rows), 7)     # two blank lines and a row of empty cells are rows to csv.reader
        self.assertEqual(self.ids(ex.not_imported(())), ['103', '101', '102', '104'])
        self.assertEqual(ex.skipped, 0)

    def test_a_row_with_a_bad_date_is_left_out_and_counted(self):
        ex = self.export(self.rows + [row(105, 'sometime in July', 'Undated Loop')])
        self.assertEqual(self.ids(ex.not_imported(())), ['103', '101', '102', '104'])
        self.assertEqual(ex.skipped, 1)

    def test_the_skipped_count_is_reset_by_the_next_call(self):
        ex = self.export(self.rows + [row(105, 'sometime in July', 'Undated Loop'), row(106, '', 'No date at all')])
        ex.not_imported(())
        self.assertEqual(ex.skipped, 2)
        ex.not_imported({105})
        self.assertEqual(ex.skipped, 1)
        ex.not_imported({105, 106})
        self.assertEqual(ex.skipped, 0)

    def test_a_short_row_is_listed_with_its_missing_cells_empty(self):
        short = row(107, 'Sep 3, 2026, 8:00:00 AM', 'Short Synthetic Walk', kind='Walk')[:5]
        ex = self.export(self.rows + [short])
        recs = ex.not_imported({101, 102, 103, 104})
        self.assertEqual(self.ids(recs), ['107'])
        self.assertEqual((recs[0]['media'], recs[0]['distance_m'], recs[0]['file']), ([], None, None))
        self.assertEqual(ex.skipped, 0)


if __name__ == '__main__':
    unittest.main()
