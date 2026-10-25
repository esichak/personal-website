"""A journal's days on the region maps: `region_days` in a journal's index.md (content._region_days).

A journal (kind: series) is filed under one region of its own and walks through many. `region_days` says which of its
days lie in which region, either as the region's days or as named parts:

    region_days:
      Synthetic Range:
        Synthetic Crest: 1-2
        Synthetic Loop: 4
      Synthetic Coast: 6

A part is one line on the region's map and one row in its list, tied together by the part's key. A day may be listed
as one stretch of its recording ('4/2': what was recorded after a drive, geo.stretches): it is then drawn, pinned,
drawn small and measured with that stretch alone. Then (a)
tools/render.py draws a part's days on that region's map, which stays framed by the region's own trips (a day is drawn
where it crosses the map and cut off at its edge); the part's lines are a link to its first day on the journal page
(mapkit.line_links), a run of consecutive days that starts inside the region also has a pin, and the days are recorded
in the map's entry of rendered/site/meta.json under 'journals' ('trips' stays the region's own reports), with the name
of the part's own drawing (render.part_glyph), which build.py publishes as an image (copy_part_drawings); (b) the
region's list, on the Map page and on the region's page, names each part in one row after the reports (in a folded
list, after the reports that stay shown), shown whether the list is folded or not, with that drawing; no count of reports includes it; (c) the validator refuses a region that
no report is filed under and warns when a region map was drawn with other days than the block lists.

Nothing here draws or fetches: the renderer tests use test_render_goals' fixture (render_map, fetch_osm and
optimize_images stubbed, render.OUT in a temp dir), the page tests test_archive_page's synthetic site, and the
validator tests a temp tree of their own. Every slug, name and sentence is made up.
"""
import datetime
import importlib
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402

import gpx_fixtures as gf  # noqa: E402
import helpers  # noqa: E402
from helpers import Doc  # noqa: E402
from test_archive_page import MapPageFixture, MAPPED, LISTED, SLUG, load_module  # noqa: E402
from test_render_goals import RenderGoalsFixture, REGION  # noqa: E402

checks = importlib.import_module('checks')

tearDownModule = helpers.no_region_pages_left      # the page tests register a site: no region page may stay registered

JOURNAL = 'syn-d-journal'
WHERE = 'content/trips/%s/index.md' % JOURNAL
LABELS = ('1', '2', '3', '4', '5.2', '6', '10')


def journal(root, slug=JOURNAL, labels=LABELS, tracks=None, stats=None, **meta):
    """A journal with one day per label (day files 001, 002, ...), dated from 2024-05-01, each with an empty track file
    unless `tracks` says otherwise. stats: {label: distance_km}."""
    days = []
    for i, label in enumerate(labels):
        d = {'id': '%03d' % (i + 1), 'day': label, 'date': '2024-05-%02d' % (i + 1),
             'track': True if tracks is None else tracks[i]}
        if stats and label in stats:
            d['stats'] = {'distance_km': stats[label]}
        days.append(d)
    m = dict(title='Synthetic Journal', activity='hike', kind='series', date='2024-05-01', end_date='2024-05-%02d' % len(labels),
             place='Synthetic start to synthetic end', region='Synthetic Trail')
    m.update(meta)
    return helpers.make_trip(root, slug, days=days, **m)


def labels_of(part):
    return [d['label'] for d in part['days']]


# A day recorded in two stretches: twelve fixes far to the south (37.000 ... 37.011), a drive, then twelve fixes that start
# inside the walks' box and leave northwards (38.906 ... 38.917). 0.001 degrees of latitude is 111.19 m here.
FAR = gf.line(37.000, -120.100, 12)
NEAR = gf.line(38.906, -120.100, 12, t0=400)
TWO_STRETCHES = gf.gpx(gf.trk([FAR + NEAR], 'Synthetic split day'))
STRETCH_KM = 11 * 0.111195


class StretchTests(unittest.TestCase):
    """geo.stretches and content.day_points: a recording falls into stretches where two fixes lie far apart."""

    def setUp(self):
        self.geo = importlib.import_module('geo')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name

    def day(self, text, label='4'):
        path = os.path.join(self.root, 'day.gpx')
        if text is not None:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(text)
        return {'id': '004', 'label': label, 'track': path if text is not None else None}

    def test_a_recording_is_split_where_two_fixes_lie_far_apart(self):
        s = self.geo.stretches
        self.assertEqual(s([]), [])
        self.assertEqual(s([(38.9, -120.1)]), [(0, 1)])
        self.assertEqual(s(gf.SEG_A), [(0, 12)])                                # a walk: one stretch
        self.assertEqual(s(FAR + NEAR), [(0, 12), (12, 24)])
        self.assertEqual(s(FAR + NEAR + FAR), [(0, 12), (12, 24), (24, 36)])
        self.assertEqual(self.geo.STRETCH_GAP_M, 20000.0)
        # a lost signal of a few kilometres is no split (0.1 degrees of latitude is 11 km), a drive of 20 km and more is
        self.assertEqual(s([(38.0, -120.1), (38.1, -120.1)]), [(0, 2)])
        self.assertEqual(s([(38.0, -120.1), (38.2, -120.1)]), [(0, 1), (1, 2)])
        self.assertEqual(s([(38.0, -120.1), (38.1, -120.1)], gap_m=5000), [(0, 1), (1, 2)])

    def test_day_points_gives_the_day_or_one_stretch_of_it(self):
        d = self.day(TWO_STRETCHES)
        lats = lambda pts: [round(p[0], 3) for p in pts]   # noqa: E731
        self.assertEqual(len(content.day_points(d)), 24)
        self.assertEqual(lats(content.day_points(d, 1)), [round(p[0], 3) for p in FAR])
        self.assertEqual(lats(content.day_points(d, 2)), [round(p[0], 3) for p in NEAR])
        self.assertEqual(content.day_points(self.day(gf.SINGLE), 1), content.day_points(self.day(gf.SINGLE)))
        self.assertEqual(content.day_points(self.day(None)), [])

    def test_a_stretch_the_track_does_not_have_is_refused(self):
        d = self.day(TWO_STRETCHES)
        for n in (3, 0, -1):
            with self.subTest(stretch=n):
                with self.assertRaises(content.ContentError) as cm:
                    content.day_points(d, n, WHERE)
                self.assertEqual(str(cm.exception), '%s: region_days takes stretch %d of day 4, whose track has 2 (a stretch ends '
                                                    'where two fixes lie more than 20 km apart)' % (WHERE, n))
        with self.assertRaises(content.ContentError) as cm:
            content.day_points(self.day(gf.SINGLE), 2)
        self.assertEqual(str(cm.exception), 'region_days takes stretch 2 of day 4, whose track has 1 (a stretch ends where two '
                                            'fixes lie more than 20 km apart)')
        with self.assertRaises(content.ContentError) as cm:
            content.day_points(self.day(None), 1, WHERE)
        self.assertEqual(str(cm.exception), '%s: region_days takes stretch 1 of day 4, whose track holds no fixes' % WHERE)


# ---------------------------------------------------------------- the block, as content.load_trip reads it

class LoaderTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name

    def load(self, **meta):
        return content.load_trip(journal(self.root, **meta))

    def refused(self, **meta):
        with self.assertRaises(content.ContentError) as cm:
            self.load(**meta)
        return str(cm.exception)

    def test_a_journal_without_the_block_has_none(self):
        self.assertEqual(self.load()['region_days'], [])
        for empty in ({}, []):
            with self.subTest(value=empty):
                self.assertEqual(content._region_days(empty, self.load(), WHERE), [])

    def test_ranges_and_single_days_name_days_by_their_label(self):
        t = self.load(region_days={'Synthetic Range': '1-2, 4', 'Synthetic Coast': '6'})
        self.assertEqual([p['region'] for p in t['region_days']], ['Synthetic Range', 'Synthetic Coast'])   # the order written
        self.assertEqual([labels_of(p) for p in t['region_days']], [['1', '2', '4'], ['6']])
        self.assertIs(t['region_days'][0]['days'][0], t['days'][0])            # the journal's own day dicts
        # a region's days are one part, without a name of its own, under the journal's own key
        self.assertEqual([(p['title'], p['key']) for p in t['region_days']], [(None, JOURNAL), (None, JOURNAL)])

    def test_a_region_may_hold_named_parts(self):
        t = self.load(region_days={'Synthetic Range': {'Synthetic Crest': '1-2', 'Synthetic Loop': [4, '6-10']}, 'Synthetic Coast': '3'})
        self.assertEqual([(p['region'], p['title'], p['key'], labels_of(p)) for p in t['region_days']],
                         [('Synthetic Range', 'Synthetic Crest', JOURNAL + ':synthetic-crest', ['1', '2']),
                          ('Synthetic Range', 'Synthetic Loop', JOURNAL + ':synthetic-loop', ['4', '6', '10']),
                          ('Synthetic Coast', None, JOURNAL, ['3'])])
        for p in t['region_days']:
            self.assertNotIn(' ', p['key'])       # a key is one word: a cluster marker lists keys separated by spaces
        # the same name in two regions is two parts with one key, each on its own region's map
        t = self.load(region_days={'Synthetic Range': {'Synthetic Crest': '1'}, 'Synthetic Coast': {'Synthetic Crest': '2'}})
        self.assertEqual([p['key'] for p in t['region_days']], [JOURNAL + ':synthetic-crest'] * 2)

    def test_a_range_takes_every_day_whose_number_lies_in_it(self):
        t = self.load(region_days={'Synthetic Range': '4-6'})
        self.assertEqual(labels_of(t['region_days'][0]), ['4', '5.2', '6'])     # Day 5.2 lies between 5 and 6
        t = self.load(region_days={'Synthetic Range': '6-99'})
        self.assertEqual(labels_of(t['region_days'][0]), ['6', '10'])           # a number, not text: 10 is not before 6

    def test_the_days_come_out_once_and_in_the_journals_order(self):
        t = self.load(region_days={'Synthetic Range': '10, 4-6, 5.2, 1'})
        self.assertEqual(labels_of(t['region_days'][0]), ['1', '4', '5.2', '6', '10'])

    def test_a_list_and_a_bare_number_are_read_like_the_text(self):
        base = self.load()
        for raw, want in ((['1-2', '4'], ['1', '2', '4']), (4, ['4']), (5.2, ['5.2']), (['1', 2, None], ['1', '2']), ('2 - 4', ['2', '3', '4'])):
            with self.subTest(value=raw):
                got = content._region_days({'Synthetic Range': raw}, base, WHERE)
                self.assertEqual(labels_of(got[0]), want)

    def test_a_day_may_lie_in_two_regions(self):
        t = self.load(region_days={'Synthetic Range': '1-3', 'Synthetic Coast': '3-4'})
        self.assertEqual([labels_of(p) for p in t['region_days']], [['1', '2', '3'], ['3', '4']])

    def test_a_day_may_be_listed_as_one_stretch_of_its_recording(self):
        t = self.load(region_days={'Synthetic Range': {'Synthetic Loop': '4/2, 1-2', 'Synthetic Crest': '6'}, 'Synthetic Coast': ' 5.2 / 1 '})
        loop, crest, coast = t['region_days']
        self.assertEqual(labels_of(loop), ['1', '2', '4'])              # a day like the others, in the journal's order
        self.assertEqual(loop['stretches'], {'004': 2})                 # by the day's id, as the map's entry names days
        self.assertEqual(crest['stretches'], {})                        # always there
        self.assertEqual((labels_of(coast), coast['stretches']), (['5.2'], {'005': 1}))
        # the same stretch twice is the same thing said twice
        again = content._region_days({'Synthetic Range': '4/2, 4/2'}, t, WHERE)
        self.assertEqual((labels_of(again[0]), again[0]['stretches']), (['4'], {'004': 2}))
        # the loader reads no track: a stretch the track does not have is seen by day_points and the validator
        self.assertEqual(content._region_days({'Synthetic Range': '4/99'}, t, WHERE)[0]['stretches'], {'004': 99})

    def test_what_is_refused_names_the_file_and_the_fault(self):
        base = self.load()
        cases = (
            ('nope', 'region_days must be a mapping of a region to its days, such as "Lake Tahoe: 68-75, 147-153", got \'nope\''),
            ({'Synthetic Range': '7'}, "region_days: Synthetic Range names day '7', which is no day of this journal (days are named "
                                       'by the number the page shows, as in Day 148)'),
            ({'Synthetic Range': '20-30'}, 'region_days: Synthetic Range has the range 20-30, which holds no day of this journal'),
            ({'Synthetic Range': '4-2'}, 'region_days: Synthetic Range has the range 4-2, which runs backwards'),
            ({'Synthetic Range': None}, 'region_days: Synthetic Range names no days; write them as 68-75, 147-153 or take the line out'),
            ({'Synthetic Range': [True]}, 'region_days: Synthetic Range must list days such as 68-75, 147-153, got [True]'),
            ({'Synthetic Range': {'Synthetic Loop': {'a': 1}}},
             "region_days: Synthetic Range: Synthetic Loop must list days such as 68-75, 147-153, got {'a': 1}"),
            ({'Synthetic Range': {'Synthetic Loop': '7'}},
             "region_days: Synthetic Range: Synthetic Loop names day '7', which is no day of this journal (days are named by the "
             'number the page shows, as in Day 148)'),
            ({'Synthetic Range': {'Synthetic Loop': None}},
             'region_days: Synthetic Range: Synthetic Loop names no days; write them as 68-75, 147-153 or take the line out'),
            ({'Synthetic Range': {'Synthetic Loop': '1', 'synthetic loop': '2'}}, "region_days: Synthetic Range names the part 'synthetic loop' twice"),
            ({'Synthetic Range': {'!!': '1'}}, 'region_days: Synthetic Range has a part without a name (a name needs a letter or a digit)'),
            ({'': '1'}, 'region_days has an entry without a region name'),
            ({'Synthetic Range': '1-2/2'}, 'region_days: Synthetic Range has 1-2/2: a stretch is of one day, not of a range'),
            ({'Synthetic Range': '4/0'}, 'region_days: Synthetic Range has 4/0: after the / comes the number of the stretch, counted '
                                         'from 1 (146/2 is the second stretch of day 146)'),
            ({'Synthetic Range': '4/b'}, 'region_days: Synthetic Range has 4/b: after the / comes the number of the stretch, counted '
                                         'from 1 (146/2 is the second stretch of day 146)'),
            ({'Synthetic Range': '4/'}, 'region_days: Synthetic Range has 4/: after the / comes the number of the stretch, counted '
                                        'from 1 (146/2 is the second stretch of day 146)'),
            ({'Synthetic Range': '7/1'}, "region_days: Synthetic Range names day '7', which is no day of this journal (days are named "
                                         'by the number the page shows, as in Day 148)'),
            ({'Synthetic Range': '4, 4/2'}, 'region_days: Synthetic Range lists day 4 twice, whole and as a stretch or as two '
                                            'stretches; a part takes a day whole or one stretch of it'),
            ({'Synthetic Range': '4/2, 2-4'}, 'region_days: Synthetic Range lists day 4 twice, whole and as a stretch or as two '
                                              'stretches; a part takes a day whole or one stretch of it'),
            ({'Synthetic Range': {'Synthetic Loop': '4/1, 4/2'}},
             'region_days: Synthetic Range: Synthetic Loop lists day 4 twice, whole and as a stretch or as two stretches; a part '
             'takes a day whole or one stretch of it'),
        )
        for raw, text in cases:
            with self.subTest(value=raw):
                with self.assertRaises(content.ContentError) as cm:
                    content._region_days(raw, base, WHERE)
                self.assertEqual(str(cm.exception), '%s: %s' % (WHERE, text))

    def test_the_block_is_for_a_journal_only(self):
        folder = helpers.make_trip(self.root, 'syn-d-walk', title='Synthetic Walk', date='2025-01-01', region='Synthetic Range',
                                   track=True, region_days={'Synthetic Range': '1'})
        with self.assertRaises(content.ContentError) as cm:
            content.load_trip(folder)
        self.assertEqual(str(cm.exception), 'content/trips/syn-d-walk/index.md: region_days is for a journal (kind: series); '
                                            'this trip is kind: trip')
        # an empty block on any trip is "none yet"
        folder = helpers.make_trip(self.root, 'syn-d-walk-2', title='Synthetic Walk Two', date='2025-01-02', track=True, region_days={})
        self.assertEqual(content.load_trip(folder)['region_days'], [])

    def test_the_file_itself_reads_back(self):
        # the block as an author writes it, read from the file by the front-matter parser
        folder = journal(self.root)
        path = os.path.join(folder, 'index.md')
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
        head, rest = text.split('\n---\n', 1)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(head + '\nregion_days:\n  Synthetic Range: 1-2, 4\n  Synthetic Coast: [5.2, 10]\n---\n' + rest)
        t = content.load_trip(folder)
        self.assertEqual([(p['region'], labels_of(p)) for p in t['region_days']],
                         [('Synthetic Range', ['1', '2', '4']), ('Synthetic Coast', ['5.2', '10'])])


# ---------------------------------------------------------------- the renderer (drawing stubbed)

def day_gpx(i):
    """A line of its own for day i, north of the walks (gf.SINGLE runs from 38.900 to 38.911 at -120.100) unless it is
    day 1 or day 2. Day 1 starts south of them and walks north through their box; day 2 starts inside it and leaves
    northwards; the others never come into it."""
    if i == 1:
        return gf.gpx(gf.trk([gf.line(38.895, -120.100, 12)], 'Synthetic day 1'))       # 38.895 ... 38.906
    if i == 2:
        return gf.gpx(gf.trk([gf.line(38.906, -120.100, 12)], 'Synthetic day 2'))       # 38.906 ... 38.917
    return gf.gpx(gf.trk([gf.line(38.900 + 0.05 * i, -120.100, 6)], 'Synthetic day %d' % i))


OWN_BOX = (38.900, -120.100, 38.911, -120.100)      # (s, w, n, e) of three walks that are all gf.SINGLE


class RendererTests(RenderGoalsFixture):

    def journal(self, region_days, labels=('1', '2', '3', '4', '5'), tracks=None, slug=JOURNAL, **meta):
        folder = journal(self.trips_dir, slug=slug, labels=labels, tracks=tracks, region_days=region_days, **meta)
        for i in range(len(labels)):
            path = os.path.join(folder, 'days', '%03d.gpx' % (i + 1))
            if os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(day_gpx(i + 1))
        t = content.load_trip(folder)
        t['rendered'] = os.path.join(self.out, 'trips', slug)
        return t

    def walks(self, n=3, **meta):
        return [self.trip('walk-%d' % i, gf.SINGLE, date='2026-08-%02d' % i, **meta) for i in range(1, n + 1)]

    def meta(self):
        with open(os.path.join(self.out, 'site', 'meta.json')) as fh:
            return json.load(fh)

    def part(self, j, i=0):
        """The i-th part of a journal as the renderer takes it (journal_parts): with the journal under 'trip'."""
        return dict(j['region_days'][i], trip=j)

    def test_the_parts_are_the_listed_days_that_have_a_track(self):
        j = self.journal({REGION: '1-4', 'Synthetic Coast': '5'}, tracks=(True, True, False, True, True))
        parts = self.render.journal_parts(self.walks() + [j])
        self.assertEqual(sorted(parts), ['Synthetic Coast', REGION])
        self.assertEqual([(p['trip']['slug'], p['key'], p['title'], [d['label'] for d in p['days']]) for p in parts[REGION]],
                         [(JOURNAL, JOURNAL, None, ['1', '2', '4'])])
        self.assertEqual(self.render.journal_parts(self.walks()), {})
        # a part whose listed days hold no track is no part
        k = self.journal({REGION: '3'}, tracks=(True, True, False, True, True), slug='syn-d-other')
        self.assertEqual(self.render.journal_parts([k]), {})
        # named parts come one by one, in the order written
        n = self.journal({REGION: {'Synthetic Crest': '1-2', 'Synthetic Loop': '4-5'}}, slug='syn-d-named')
        self.assertEqual([(p['key'], p['title'], [d['label'] for d in p['days']]) for p in self.render.journal_parts([n])[REGION]],
                         [('syn-d-named:synthetic-crest', 'Synthetic Crest', ['1', '2']), ('syn-d-named:synthetic-loop', 'Synthetic Loop', ['4', '5'])])

    def test_days_that_follow_one_another_are_one_run(self):
        j = self.journal({REGION: '1-2, 4-5'})
        days = j['region_days'][0]['days']
        self.assertEqual([[d['label'] for d in run] for run in self.render.day_runs(j, days)], [['1', '2'], ['4', '5']])
        self.assertEqual([[d['label'] for d in run] for run in self.render.day_runs(j, j['days'])], [['1', '2', '3', '4', '5']])
        self.assertEqual(self.render.day_runs(j, []), [])

    def test_without_a_frame_a_run_gets_its_pin_at_the_start_of_its_first_day(self):
        j = self.journal({REGION: '1-2, 4-5'})
        pins = self.render.journal_pins(j, self.part(j))
        self.assertEqual([(p['key'], p['title'], p['href'], p['cat']) for p in pins],
                         [(JOURNAL, 'Synthetic Journal, Day 1', '@@ROOT@@trips/%s/#day-1' % JOURNAL, j['cat']),
                          (JOURNAL, 'Synthetic Journal, Day 4', '@@ROOT@@trips/%s/#day-4' % JOURNAL, j['cat'])])
        self.assertEqual([(round(p['lat'], 3), round(p['lon'], 3)) for p in pins], [(38.895, -120.1), (39.1, -120.1)])

    def test_with_a_frame_only_a_run_that_starts_in_the_region_has_a_pin(self):
        # a pin marks a start. Day 2 starts inside the walks' box; day 1 starts south of it and walks in; days 4 and 5
        # are far to the north
        j = self.journal({REGION: {'Synthetic Loop': '2, 4-5'}})
        pins = self.render.journal_pins(j, self.part(j), OWN_BOX)
        self.assertEqual([(p['key'], p['title'], p['href']) for p in pins],
                         [(JOURNAL + ':synthetic-loop', 'Synthetic Loop: Synthetic Journal, Day 2', '@@ROOT@@trips/%s/#day-2' % JOURNAL)])
        self.assertEqual((round(pins[0]['lat'], 3), round(pins[0]['lon'], 3)), (38.906, -120.1))
        # a run that comes in from outside has none, however much of it lies inside
        k = self.journal({REGION: '1-2'}, slug='syn-d-through')
        self.assertEqual(self.render.journal_pins(k, self.part(k), OWN_BOX), [])
        self.assertEqual(len(self.render.journal_pins(k, self.part(k))), 1)      # without a frame it has its pin

    def test_a_run_that_goes_on_where_the_part_stopped_starts_nothing_new(self):
        # days 1 and 2 walk north to 38.917; day 3 is a day off somewhere else and is left out of the part; day 4 goes on
        def journal_with_day_4_at(lat, slug):
            j = self.journal({REGION: {'Synthetic Crest': '1-2, 4'}}, slug=slug)
            with open(os.path.join(self.trips_dir, slug, 'days', '004.gpx'), 'w', encoding='utf-8') as fh:
                fh.write(gf.gpx(gf.trk([gf.line(lat, -120.100, 6)], 'Synthetic day 4')))
            return j
        self.assertEqual(self.render.RESUME_M, 5000.0)
        for lat, starts in ((38.917, ['1']),            # at the very place
                            (38.947, ['1']),            # 3.3 km on (the other end of a lake, the far side of a road)
                            (38.977, ['1', '4']),       # 6.7 km on: another walk
                            (39.100, ['1', '4'])):
            with self.subTest(day_4_starts_at=lat):
                j = journal_with_day_4_at(lat, 'syn-d-resume-%d' % round(lat * 1000))
                pins = self.render.journal_pins(j, self.part(j))
                self.assertEqual([p['title'].rsplit('Day ', 1)[1] for p in pins], starts)
        # the days that follow one another are still one run, wherever each starts (a hitch between two days)
        k = self.journal({REGION: '2-3'}, slug='syn-d-hitch')
        self.assertEqual([p['title'] for p in self.render.journal_pins(k, self.part(k))], ['Synthetic Journal, Day 2'])
        # a run that goes on has no pin inside the frame either; one that starts anew inside it has
        inside = journal_with_day_4_at(38.947, 'syn-d-resume-box')
        self.assertEqual(self.render.journal_pins(inside, self.part(inside), (38.900, -120.2, 39.0, -120.0)), [])
        anew = journal_with_day_4_at(38.977, 'syn-d-anew-box')
        self.assertEqual([p['title'] for p in self.render.journal_pins(anew, self.part(anew), (38.900, -120.2, 39.0, -120.0))],
                         ['Synthetic Crest: Synthetic Journal, Day 4'])

    def test_a_parts_lines_are_a_link_to_its_first_day(self):
        j = self.journal({REGION: {'Synthetic Loop': '4-5'}, 'Synthetic Coast': '1'})
        loop, coast = self.part(j, 0), self.part(j, 1)
        self.assertEqual(self.render.part_href(j, loop), '@@ROOT@@trips/%s/#day-4' % JOURNAL)
        self.assertEqual(self.render.part_name(j, loop), 'Synthetic Loop: Synthetic Journal, Day 4 to Day 5')
        self.assertEqual(self.render.part_name(j, coast), 'Synthetic Journal, Day 1')             # one day, and no name of its own
        tracks = self.render.site_tracks(j, part=loop)
        self.assertEqual(len(tracks), 2)                                                      # one line per day, never joined
        for tr in tracks:
            self.assertEqual((tr['key'], tr['href'], tr['title'], tr['style'], tr['thin']),
                             (JOURNAL + ':synthetic-loop', '@@ROOT@@trips/%s/#day-4' % JOURNAL,
                              'Synthetic Loop: Synthetic Journal, Day 4 to Day 5', 'cat', False))
        # a report's lines are no link: its pin is
        walk = self.walks(1)[0]
        for tr in self.render.site_tracks(walk):
            self.assertNotIn('href', tr)
            self.assertEqual(tr['key'], 'walk-1')

    def test_render_site_draws_the_days_on_the_regions_map(self):
        j = self.journal({REGION: '1-2, 4'})
        trips = self.walks() + [j]
        self.assertIs(self.render.render_site(trips, force=True), True)
        meta = self.meta()
        self.assertEqual(meta['regions'], [REGION])
        self.assertEqual(meta['all_regions'], [REGION])            # the journal's own region is no region of the maps, as before
        slug = content.slugify(REGION)
        for name in ('region-%s-desktop' % slug, 'region-%s-phone' % slug):
            self.assertEqual(sorted(meta['maps'][name]['trips']), ['walk-1', 'walk-2', 'walk-3'])      # the region's own reports
            self.assertEqual(meta['maps'][name]['journals'], [{'slug': JOURNAL, 'key': JOURNAL, 'title': None, 'days': ['001', '002', '004'],
                                                               'glyph': 'region-%s-%s-g64' % (slug, JOURNAL)}])
        self.assertEqual(len(self.maps), 2)
        for spec in self.maps:
            mine = [tr for tr in spec['tracks'] if tr['key'] == JOURNAL]
            self.assertEqual(len(mine), 3)                                                   # one line per day, never joined
            self.assertTrue(all(tr['style'] == 'cat' and tr['cat'] == j['cat'] and not tr['thin'] for tr in mine))
            self.assertTrue(all(tr['href'] == '@@ROOT@@trips/%s/#day-1' % JOURNAL for tr in mine))
            self.assertEqual(len([tr for tr in spec['tracks'] if tr['key'] != JOURNAL]), 3)
            # the run of days 1 and 2 walks in from outside and day 4 lies outside: lines, and no pin
            self.assertEqual([p for p in spec['pins'] if p['key'] == JOURNAL], [])
            self.assertEqual(sorted(p['key'] for p in spec['pins'] if p['key'] != JOURNAL), ['walk-1', 'walk-2', 'walk-3'])
        # a run that starts inside the region has its pin, and named parts are drawn under their own keys
        del self.maps[:]
        k = self.journal({REGION: {'Synthetic Loop': '2-3', 'Synthetic Crest': '1'}}, slug='syn-d-inside')
        self.assertIs(self.render.render_site(trips[:3] + [k], force=True), True)
        for spec in self.maps:
            self.assertEqual([(p['key'], p['href']) for p in spec['pins'] if p['key'].startswith('syn-d-inside')],
                             [('syn-d-inside:synthetic-loop', '@@ROOT@@trips/syn-d-inside/#day-2')])
            keys = [tr['key'] for tr in spec['tracks'] if tr['key'].startswith('syn-d-inside')]
            self.assertEqual(keys, ['syn-d-inside:synthetic-loop'] * 2 + ['syn-d-inside:synthetic-crest'])
        self.assertEqual(self.meta()['maps']['region-%s-desktop' % slug]['journals'],
                         [{'slug': 'syn-d-inside', 'key': 'syn-d-inside:synthetic-loop', 'title': 'Synthetic Loop', 'days': ['002', '003'],
                           'glyph': 'region-%s-syn-d-inside-synthetic-loop-g64' % slug},
                          {'slug': 'syn-d-inside', 'key': 'syn-d-inside:synthetic-crest', 'title': 'Synthetic Crest', 'days': ['001'],
                           'glyph': 'region-%s-syn-d-inside-synthetic-crest-g64' % slug}])

    def split_journal(self, days, slug='syn-d-split'):
        """A journal whose day 1 was recorded in two stretches (TWO_STRETCHES): far to the south, then from inside the
        walks' box northwards. Day 2 goes on from there, as day_gpx(2) does."""
        j = self.journal({REGION: {'Synthetic Loop': days}}, slug=slug)
        with open(os.path.join(self.trips_dir, slug, 'days', '001.gpx'), 'w', encoding='utf-8') as fh:
            fh.write(TWO_STRETCHES)
        return j

    def test_a_day_listed_as_a_stretch_is_drawn_and_pinned_with_that_stretch(self):
        j = self.split_journal('1/2, 2')
        part = self.part(j)
        self.assertEqual(part['stretches'], {'001': 2})
        first, second = self.render.site_tracks(j, part=part)
        lats = [p[0] for p in first['track'].raw]
        self.assertEqual((len(lats), round(min(lats), 3), round(max(lats), 3)), (12, 38.906, 38.917))      # the stretch, and no fix of the other
        self.assertEqual(len(second['track'].raw), 12)                                                   # a whole day stays whole
        # the run starts where the stretch starts, which is inside the box: a pin, named after the day
        (pin,) = self.render.journal_pins(j, part, OWN_BOX)
        self.assertEqual((round(pin['lat'], 3), pin['title'], pin['href']),
                         (38.906, 'Synthetic Loop: Synthetic Journal, Day 1', '@@ROOT@@trips/syn-d-split/#day-1'))
        # the same day taken whole starts 200 km to the south: its lines are on the map, and it has no pin
        whole = self.split_journal('1-2', slug='syn-d-whole')
        self.assertEqual(self.render.journal_pins(whole, self.part(whole), OWN_BOX), [])
        self.assertEqual(len(self.render.site_tracks(whole, part=self.part(whole))[0]['track'].raw), 24)
        # the other stretch
        other = self.split_journal('1/1', slug='syn-d-other-stretch')
        (line,) = self.render.site_tracks(other, part=self.part(other))
        self.assertEqual(round(max(p[0] for p in line['track'].raw), 3), 37.011)
        # a stretch the track does not have stops the render, with the file's name
        bad = self.split_journal('1/3', slug='syn-d-bad-stretch')
        with self.assertRaises(content.ContentError) as cm:
            self.render.site_tracks(bad, part=self.part(bad))
        self.assertIn('content/trips/syn-d-bad-stretch/index.md: region_days takes stretch 3 of day 1, whose track has 2', str(cm.exception))

    def test_render_site_records_the_stretch_and_draws_it_small(self):
        walks = self.walks()
        j = self.split_journal('1/2, 2')
        self.assertIs(self.render.render_site(walks + [j], force=True), True)
        slug = content.slugify(REGION)
        for size in ('desktop', 'phone'):
            (entry,) = self.meta()['maps']['region-%s-%s' % (slug, size)]['journals']
            self.assertEqual((entry['days'], entry['stretches']), (['001', '002'], {'001': 2}))
        for spec in self.maps:
            mine = [tr for tr in spec['tracks'] if tr['key'] == 'syn-d-split:synthetic-loop']
            self.assertEqual([len(tr['track'].raw) for tr in mine], [12, 12])
            self.assertGreater(min(p[0] for tr in mine for p in tr['track'].raw), 38.9)                 # nothing of the far stretch
            self.assertEqual([p['key'] for p in spec['pins'] if p['key'].startswith('syn-d-split')], ['syn-d-split:synthetic-loop'])
        def runs():
            """How many separate runs each line of the part's drawing has (a recording gap splits a line in two)."""
            with open(os.path.join(self.out, 'site', entry['glyph'] + '.svg.html'), encoding='utf-8') as fh:
                return [d_.count('M') for d_ in re.findall(r' d="([^"]+)"', fh.read())]
        self.assertEqual(runs(), [1, 1])                                 # the stretch and day 2, each one unbroken line
        # the stretch is an input: taking the day whole, or the same stretch again, is seen
        self.assertIs(self.render.render_site(walks + [self.split_journal('1/2, 2')]), False)
        self.assertIs(self.render.render_site(walks + [self.split_journal('1-2')]), True)
        (entry,) = self.meta()['maps']['region-%s-desktop' % slug]['journals']
        self.assertNotIn('stretches', entry)                             # a part of whole days has no such key
        self.assertEqual(runs(), [2, 1])                                 # the whole day: the far stretch is in the drawing too
        self.assertIs(self.render.render_site(walks + [self.split_journal('1/2, 2')]), True)

    def test_each_part_gets_a_drawing_of_its_own(self):
        # the journal's glyph is the whole journal; a part's row in the region's list shows the part
        self.assertEqual(self.render.part_glyph('region-syn', {'key': 'syn-j:synthetic-loop'}), 'region-syn-syn-j-synthetic-loop-g64')
        self.assertEqual(self.render.part_glyph('region-syn', {'key': 'syn-j'}), 'region-syn-syn-j-g64')
        j = self.journal({REGION: {'Synthetic Loop': '2-3, 5', 'Synthetic Crest': '1'}})
        self.assertIs(self.render.render_site(self.walks() + [j], force=True), True)
        slug = content.slugify(REGION)
        names = ['region-%s-%s-synthetic-loop-g64' % (slug, JOURNAL), 'region-%s-%s-synthetic-crest-g64' % (slug, JOURNAL)]
        for size in ('desktop', 'phone'):
            self.assertEqual([e['glyph'] for e in self.meta()['maps']['region-%s-%s' % (slug, size)]['journals']], names)
        for name, days in zip(names, (3, 1)):
            with open(os.path.join(self.out, 'site', name + '.svg.html'), encoding='utf-8') as fh:
                svg = fh.read()
            self.assertTrue(svg.startswith('<svg width="64" height="48" viewBox="0 0 64 48"'), svg[:80])
            # every day of the part, far outside the map's frame or not, each a line (a short day is never a spot)
            self.assertEqual(svg.count('class="gl-trk"'), days)
            self.assertNotIn('<circle', svg)
        # a region without a journal part gets no drawing, and neither does a ski map
        self.assertEqual(sorted(f for f in os.listdir(os.path.join(self.out, 'site')) if f.endswith('-g64.svg.html')),
                         sorted(n + '.svg.html' for n in names))

    def test_the_map_keeps_the_frame_of_the_regions_own_trips(self):
        # a journal passes through: its days, however far they reach, do not move or widen the map
        walks = self.walks()
        self.assertIs(self.render.render_site(walks + [self.journal({REGION: '1-5'})], force=True), True)
        self.assertEqual(len(self.maps), 2)
        for spec in self.maps:
            self.assertEqual(tuple(round(v, 3) for v in spec['bbox']), OWN_BOX)
            lats = [p[0] for tr in spec['tracks'] if tr['key'] == JOURNAL for p in tr['track'].raw]
            self.assertLess(min(lats), OWN_BOX[0])           # the days are drawn whole; the map's edge cuts them off
            self.assertGreater(max(lats), OWN_BOX[2] + 0.2)
        # without a journal the renderer works the frame out itself, as it always did
        del self.maps[:]
        self.assertIs(self.render.render_site(walks, force=True), True)
        self.assertTrue(all('bbox' not in spec for spec in self.maps))

    def test_without_the_block_the_map_entry_is_what_it_was(self):
        j = self.journal(None)
        self.assertIs(self.render.render_site(self.walks() + [j], force=True), True)
        for entry in self.meta()['maps'].values():
            self.assertNotIn('journals', entry)
            self.assertEqual(sorted(entry), ['base', 'base_gz_kb', 'clusters', 'h', 'png', 'region', 'trips', 'w'])   # base_gz_kb: Phase 15
        self.assertTrue(all(tr['key'] != JOURNAL for spec in self.maps for tr in spec['tracks']))
        self.assertTrue(all('href' not in tr for spec in self.maps for tr in spec['tracks']))

    def test_the_days_do_not_make_a_region_map_and_stay_off_the_ski_maps(self):
        # two reports and a journal's days: not the three reports a region map needs
        j = self.journal({REGION: '1-5'})
        self.assertIs(self.render.render_site(self.walks(2) + [j], force=True), True)
        self.assertEqual(self.meta()['regions'], [])
        self.assertEqual(self.maps, [])
        # a region map and a ski map: the days are on the first only
        ski = [self.trip('ski-%d' % i, gf.SINGLE, activity='ski', date='2026-02-%02d' % i) for i in (1, 2, 3)]
        self.assertIs(self.render.render_site(ski + [j], force=True), True)
        meta = self.meta()
        slug = content.slugify(REGION)
        self.assertIn('journals', meta['maps']['region-%s-desktop' % slug])
        self.assertNotIn('journals', meta['maps']['ski-%s-desktop' % slug])
        by_name = {spec['name']: spec for spec in self.maps}
        self.assertTrue(any(tr['key'] == JOURNAL for tr in by_name['region-%s-desktop' % slug]['tracks']))
        self.assertFalse(any(tr['key'] == JOURNAL for tr in by_name['ski-%s-desktop' % slug]['tracks']))
        self.assertFalse(any(p['key'] == JOURNAL for p in by_name['ski-%s-desktop' % slug]['pins']))

    def test_changing_the_days_draws_the_maps_again_and_nothing_else_does(self):
        walks = self.walks()
        entry = lambda: self.meta()['maps']['region-%s-desktop' % content.slugify(REGION)]   # noqa: E731
        self.assertIs(self.render.render_site(walks + [self.journal({REGION: '1-2'})], force=True), True)
        self.assertIs(self.render.render_site(walks + [self.journal({REGION: '1-2'})]), False)       # same inputs: nothing is redrawn
        self.assertIs(self.render.render_site(walks + [self.journal({REGION: '1-3'})]), True)
        self.assertEqual([j['days'] for j in entry()['journals']], [['001', '002', '003']])
        self.assertIs(self.render.render_site(walks + [self.journal({REGION: {'Synthetic Loop': '1-3'}})]), True)   # a name is an input too
        self.assertEqual([(j['key'], j['title']) for j in entry()['journals']], [(JOURNAL + ':synthetic-loop', 'Synthetic Loop')])
        self.assertIs(self.render.render_site(walks + [self.journal(None)]), True)                    # and so is taking them out
        self.assertNotIn('journals', entry())


class LineLinkTests(unittest.TestCase):
    """mapkit.line_links: the links a map gets for lines that have no pin (a journal's days on a region map)."""

    def setUp(self):
        self.mapkit = importlib.import_module('mapkit')

    def test_one_link_per_key_over_every_line_of_it(self):
        links = {'syn-j:synthetic-loop': {'href': '@@ROOT@@trips/syn-j/#day-4', 'title': 'Synthetic Loop: Synthetic "Journal" & <more>, Day 4 to Day 5',
                                          'ids': ['tk-7', 'tk-8']},
                 'syn-j': {'href': '@@ROOT@@trips/syn-j/#day-1', 'title': 'Synthetic Journal, Day 1', 'ids': ['tk-9']}}
        out = self.mapkit.line_links(links)
        self.assertEqual(len(out), 2)
        doc = Doc('<svg>%s</svg>' % ''.join(out))
        a, b = doc.find_all('a')
        self.assertEqual((a['class'], a['href'], a['data-key']), ('mk-line', '@@ROOT@@trips/syn-j/#day-4', 'syn-j:synthetic-loop'))
        self.assertEqual(a['aria-label'], 'Synthetic Loop: Synthetic "Journal" & <more>, Day 4 to Day 5')     # escaped, and read back whole
        self.assertEqual(a.find('title').text(), a['aria-label'])
        uses = a.find_all('use')
        self.assertEqual([u['href'] for u in uses], ['#tk-7', '#tk-8'])
        for u in uses:
            self.assertEqual((u['class'], u['style']), ('mk-hit', None))     # MAP_CSS draws it (Phase 15: one rule, not a style on each use)
        self.assertIn('.mk-line .mk-hit{fill:none;stroke:transparent;stroke-width:%dpx;pointer-events:stroke}' % self.mapkit.LINE_HIT,
                      self.mapkit.MAP_CSS)
        self.assertEqual([u['href'] for u in b.find_all('use')], ['#tk-9'])
        self.assertGreaterEqual(self.mapkit.LINE_HIT, 12)        # wide enough to point at; the line itself is 2.5 px
        self.assertEqual(self.mapkit.line_links({}), [])

    def test_the_page_script_treats_such_a_link_as_a_pin(self):
        with open(os.path.join(ROOT, 'assets', 'js', 'base.js'), encoding='utf-8') as fh:
            src = fh.read()
        self.assertIn("document.querySelectorAll('.mk-pin[data-key], .mk-cluster, .mk-line[data-key]')", src)
        with open(os.path.join(ROOT, 'assets', 'css', 'base.css'), encoding='utf-8') as fh:
            css = fh.read()
        self.assertIn('.mk-line { cursor: pointer; }', css)


class PublishedDrawingTests(unittest.TestCase):
    """build.copy_part_drawings: a part's drawing in rendered/site/ becomes the image its row names."""

    def test_each_drawing_is_written_as_a_standalone_image(self):
        build = importlib.import_module('build')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        site = os.path.join(tmp.name, 'rendered', 'site')
        os.makedirs(site)
        frag = ('<svg width="64" height="48" viewBox="0 0 64 48" aria-hidden="true" style="display: block; flex-shrink: 0">'
                '<path class="gl-trk" style="stroke: #5E7F2E; stroke-width: 2.0" d="M5 5L50 40"/></svg>')
        files = {'region-syn-syn-j-synthetic-loop-g64.svg.html': frag,
                 'region-syn-syn-j-g64.svg.html': frag,
                 'region-syn-syn-j-g64.svg 2.html': frag.replace('M5 5', 'M9 9'),        # iCloud conflict copies: never published
                 'region-syn-syn-j-g64 3.svg.html': frag.replace('M5 5', 'M9 9'),
                 'region-syn-desktop.svg.html': '<svg width="718" height="620"></svg>',  # a map's overlay is no drawing
                 'region-syn-broken-g64.svg.html': 'not a drawing'}
        for name, text in files.items():
            with open(os.path.join(site, name), 'w', encoding='utf-8') as fh:
                fh.write(text)
        out = os.path.join(tmp.name, '_site')
        with mock.patch.object(build, 'ROOT', tmp.name), mock.patch.object(build, 'OUT', out):
            written = build.copy_part_drawings()
        self.assertEqual(written, ['region-syn-syn-j-g64.svg', 'region-syn-syn-j-synthetic-loop-g64.svg'])
        self.assertEqual(sorted(os.listdir(os.path.join(out, 'assets', 'maps'))), written)
        for name in written:
            with open(os.path.join(out, 'assets', 'maps', name), encoding='utf-8') as fh:
                svg = fh.read()
            self.assertTrue(svg.startswith('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="48" viewBox="0 0 64 48">'), svg[:90])
            self.assertIn('vector-effect:non-scaling-stroke', svg)          # as a trip's glyph image
            self.assertIn('d="M5 5L50 40"', svg)
            self.assertNotIn('aria-hidden', svg)


# ---------------------------------------------------------------- the region's list (Map page and region page)

RANGE, COAST = MAPPED
PAGE_JOURNAL = 'syn-m-journal'
CREST, LOOP = PAGE_JOURNAL + ':synthetic-crest', PAGE_JOURNAL + ':synthetic-loop'


class ListRowTests(MapPageFixture):
    REGION_PAGES = True

    def setUp(self):
        super().setUp()
        # the fixture's journal again, now a mountain-bike journal (an activity no report of the Range has) of five days:
        # two parts in the Synthetic Range, one day in the Synthetic Coast
        journal(self.trips_dir, slug=PAGE_JOURNAL, labels=('1', '2', '3', '4', '5'), stats={'1': 10.0, '2': 12.5, '3': 7.0, '4': 3.0},
                activity='mtb', region_days={RANGE: {'Synthetic Crest': '1-3', 'Synthetic Loop': '4'}, COAST: '5'})
        self.use(MAPPED, MAPPED + LISTED, featured=('syn-m-coast-a',))

    def drawn(self, glyphs=None):
        """The site meta as the renderer leaves it once it has drawn the journal's parts on the Range's maps; the page is
        built again. glyphs: {part key: the name of its drawing}, for the entries that name one."""
        entries = [{'slug': PAGE_JOURNAL, 'key': CREST, 'title': 'Synthetic Crest', 'days': ['001', '002', '003']},
                   {'slug': PAGE_JOURNAL, 'key': LOOP, 'title': 'Synthetic Loop', 'days': ['004']}]
        for e in entries:
            if glyphs and e['key'] in glyphs:
                e['glyph'] = glyphs[e['key']]
        for size in ('desktop', 'phone'):
            self.meta['maps']['region-%s-%s' % (SLUG[RANGE], size)]['journals'] = [dict(e) for e in entries]
        with open(os.path.join(self.site_dir, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(self.meta, fh)
        self.page = self.archive.build(self.site)[0]
        self.doc = Doc(self.page.html)
        self.main = self.doc.by_id('main')

    def panel(self, name):
        return self.one('region-' + SLUG[name])

    def rows(self, node):
        return [li for li in node.find_all('li') if 'arc-row' in li.classes]

    def journal_rows(self, node):
        return [li for li in self.rows(node) if 'arc-row--journal' in li.classes]

    def meta_text(self, row):
        return helpers.plain_text(row.find('span', cls='arc-row-m').text()).replace('\u00a0', ' ')

    def test_the_parts_are_the_published_journals_parts_in_that_region(self):
        parts = self.archive.journal_parts(self.site, RANGE)
        self.assertEqual([(t['slug'], p['key'], p['title'], [d['label'] for d in p['days']]) for t, p in parts],
                         [(PAGE_JOURNAL, CREST, 'Synthetic Crest', ['1', '2', '3']), (PAGE_JOURNAL, LOOP, 'Synthetic Loop', ['4'])])
        self.assertEqual([(p['key'], p['title']) for _t, p in self.archive.journal_parts(self.site, COAST)], [(PAGE_JOURNAL, None)])
        self.assertEqual(self.archive.journal_parts(self.site, 'Synthetic Trail'), [])     # its own region is no part
        self.assertEqual(self.archive.journal_parts(None, RANGE), [])
        self.assertEqual(self.archive.journal_parts({'published': []}, RANGE), [])

    def test_each_part_has_one_row_named_after_it(self):
        crest, loop = self.journal_rows(self.panel(RANGE))
        self.assertEqual((crest['data-key'], loop['data-key']), (CREST, LOOP))          # the keys their lines on the map carry
        self.assertEqual(crest.find('span', cls='arc-row-t').text(), 'Synthetic Crest')
        self.assertEqual(loop.find('span', cls='arc-row-t').text(), 'Synthetic Loop')
        a = crest.find('a')
        self.assertEqual(a['href'], '../trips/%s/#day-1' % PAGE_JOURNAL)     # the first of its days, on the journal page
        self.assertEqual(a['data-act'], 'mtb')
        self.assertEqual(loop.find('a')['href'], '../trips/%s/#day-4' % PAGE_JOURNAL)
        text = self.meta_text(crest)
        self.assertIn('MAY 1–3, 2024', text)                                 # its first and last day
        self.assertIn('3 JOURNAL DAYS', text)
        mi, km = core_dist(29.5)
        self.assertIn(mi + ' MI', text)
        self.assertIn(km + ' KM', text)
        one = self.meta_text(loop)
        self.assertIn('MAY 4, 2024', one)
        self.assertIn('1 JOURNAL DAY', one)
        self.assertNotIn('1 JOURNAL DAYS', one)
        # a part without a name of its own is called by the journal's title, under the journal's key
        (coast,) = self.journal_rows(self.panel(COAST))
        self.assertEqual((coast['data-key'], coast.find('span', cls='arc-row-t').text()), (PAGE_JOURNAL, 'Synthetic Journal'))
        self.assertNotIn('MI', self.meta_text(coast))                        # day 5 has no distance: none is shown
        self.assertEqual(len(self.journal_rows(self.main)), 3)               # and nowhere else on the page

    def test_each_part_row_has_an_id_that_names_its_region(self):
        # Phase 12 (gap4-01): arc-row-<region>-<part>, as one journal key may be in two regions' lists on map/
        crest, loop = self.journal_rows(self.panel(RANGE))
        (coast,) = self.journal_rows(self.panel(COAST))
        self.assertEqual([r['id'] for r in (crest, loop, coast)],
                         ['arc-row-%s-%s' % (SLUG[RANGE], content.slugify(CREST)), 'arc-row-%s-%s' % (SLUG[RANGE], content.slugify(LOOP)),
                          'arc-row-%s-%s' % (SLUG[COAST], content.slugify(PAGE_JOURNAL))])
        ids = [n['id'] for n in self.doc.root.walk() if n['id']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_a_row_shows_the_parts_own_drawing_once_it_is_rendered(self):
        def drawings(row):
            return [i for i in row.find_all('img') if 'assets/maps/' in i['src']]
        for row in self.journal_rows(self.panel(RANGE)):
            self.assertEqual(drawings(row), [])                # the map was not drawn with the parts yet
        names = {CREST: 'region-%s-%s-synthetic-crest-g64' % (SLUG[RANGE], PAGE_JOURNAL),
                 LOOP: 'region-%s-%s-synthetic-loop-g64' % (SLUG[RANGE], PAGE_JOURNAL)}
        # the Crest's drawing is rendered; the Loop's is named by the map's entry and is not there
        with open(os.path.join(self.site_dir, names[CREST] + '.svg.html'), 'w', encoding='utf-8') as fh:
            fh.write('<svg width="64" height="48" viewBox="0 0 64 48" aria-hidden="true"><path class="gl-trk" d="M1 1L9 9"/></svg>')
        self.drawn(names)
        crest, loop = self.journal_rows(self.panel(RANGE))
        (img,) = drawings(crest)
        self.assertEqual(img['src'], '../assets/maps/%s.svg' % names[CREST])
        self.assertEqual((img['width'], img['height'], img['alt']), ('64', '48', ''))
        self.assertIn('arc-row-g', img.classes)
        self.assertEqual(len(crest.find_all('img')), 1)        # in place of the journal's glyph, not beside it
        self.assertEqual(drawings(loop), [])
        # on the region's own page the same image, one folder deeper
        region = load_module(self, 'sitegen.pages.region')
        page = next(p for p in region.build(self.site) if p.url == 'regions/%s/' % SLUG[RANGE])
        row = next(li for li in Doc(page.html).by_id('map').find_all('li') if 'arc-row--journal' in li.classes)
        self.assertEqual([i['src'] for i in drawings(row)], ['../../assets/maps/%s.svg' % names[CREST]])
        # no name, a name that is not rendered, and a name that is no plain file name (a damaged meta.json): no image
        with open(os.path.join(self.tmp, 'rendered', 'outside-g64.svg.html'), 'w', encoding='utf-8') as fh:
            fh.write('<svg width="64" height="48"></svg>')
        for name in (None, '', 'region-syn-no-such-g64', '../outside-g64', 'a/b', 'a b', 7, ['x'], {'x': 1}):
            with self.subTest(name=name):
                self.assertEqual(self.archive.part_glyph(name, 'map/'), '')
        self.assertIn('assets/maps/%s.svg' % names[CREST], self.archive.part_glyph(names[CREST], 'map/'))
        # and a map entry whose 'glyph' is not a name leaves the row with the journal's own
        self.drawn({CREST: ['x'], LOOP: '../outside-g64'})
        for row in self.journal_rows(self.panel(RANGE)):
            self.assertEqual(drawings(row), [])

    def test_a_stretch_counts_with_its_own_length(self):
        # day 1 was recorded in two stretches; its day file says 10 km, which is the whole day
        folder = journal(self.trips_dir, slug='syn-m-split', labels=('1', '2', '3'), stats={'1': 10.0, '2': 12.5},
                         region_days={RANGE: {'Synthetic Loop': '1/2, 2', 'Synthetic Whole': '1-2', 'Synthetic Short': '1/2, 3'}})
        with open(os.path.join(folder, 'days', '001.gpx'), 'w', encoding='utf-8') as fh:
            fh.write(TWO_STRETCHES)
        t = content.load_trip(folder)
        loop, whole, short = t['region_days']
        self.assertAlmostEqual(self.archive.part_day_km(t, loop, t['days'][0]), STRETCH_KM, places=2)     # measured along the stretch
        self.assertEqual(self.archive.part_day_km(t, loop, t['days'][1]), 12.5)                           # a whole day: the day file's figure
        self.assertEqual(self.archive.part_day_km(t, whole, t['days'][0]), 10.0)
        self.assertIsNone(self.archive.part_day_km(t, short, t['days'][2]))                               # no figure, as before

        def text(part):
            row = Doc(self.archive.journal_row(t, part, 'map/')).find('li')
            return row, self.meta_text(row)
        row, got = text(loop)
        self.assertEqual(row.find('a')['href'], '../trips/syn-m-split/#day-1')
        self.assertIn('MAY 1–2, 2024', got)                                  # the day of the stretch is a day of the part
        self.assertIn('2 JOURNAL DAYS', got)
        mi, km = core_dist(STRETCH_KM + 12.5)
        self.assertIn(mi + ' MI', got)
        self.assertIn(km + ' KM', got)
        mi_whole, _km = core_dist(22.5)
        self.assertNotEqual(mi, mi_whole)
        self.assertIn(mi_whole + ' MI', text(whole)[1])                       # the same days taken whole: the day files' sum
        self.assertIn(core_dist(STRETCH_KM)[0] + ' MI', text(short)[1])       # a stretch alone still has its length
        # a stretch the track does not have stops the build, with the file's name
        bad = dict(loop, stretches={'001': 3})
        with self.assertRaises(content.ContentError) as cm:
            self.archive.journal_row(t, bad, 'map/')
        self.assertIn('content/trips/syn-m-split/index.md: region_days takes stretch 3 of day 1', str(cm.exception))

    def test_a_row_whose_line_has_the_pointer_looks_like_a_hovered_row(self):
        # base.js marks the row of a pin or line under the pointer (is-map-hl); the list's stylesheet shows it
        with open(os.path.join(ROOT, 'assets', 'css', 'pages', 'archive.css'), encoding='utf-8') as fh:
            css = fh.read()
        # the same look as a hovered row; since Phase 13B the hover itself is under (hover: hover), the mark is not
        self.assertIn('.arc-row.is-map-hl a { color: var(--ink); background: var(--surface); }', css)
        self.assertIn('@media (hover: hover) { .arc-row a:hover { color: var(--ink); background: var(--surface); } }', css)
        self.assertIn('.arc-row.is-map-hl .arc-row-t { text-decoration: underline;', css)
        self.assertIn('@media (hover: hover) { .arc-row a:hover .arc-row-t { text-decoration: underline;', css)

    def test_they_are_no_reports_of_the_region(self):
        panel = self.panel(RANGE)
        own = [li['data-key'] for li in self.rows(panel) if 'arc-row--journal' not in li.classes]
        self.assertEqual(sorted(own), ['syn-m-range-a', 'syn-m-range-b', 'syn-m-range-tour'])
        count = helpers.plain_text(panel.find('div', cls='arc-inreg-h').find('span', cls='t-mono-s').text()).replace('\u00a0', ' ')
        self.assertIn('3 REPORTS', count)
        self.assertNotIn('JOURNAL', count)
        tab = self.one('arc-tab-' + SLUG[RANGE])
        self.assertIn('3', tab.find('span', cls='arc-tab-n').text())

    def test_they_stand_after_the_reports_and_before_a_planned_route(self):
        self.assertEqual([li['data-key'] for li in self.rows(self.panel(RANGE))],
                         ['syn-m-range-a', 'syn-m-range-b', 'syn-m-range-tour', CREST, LOOP])
        regs = self.archive.regions(self.site, self.meta)
        name, slug, ts = next(r for r in regs if r[0] == RANGE)
        goal = self.by['syn-m-desert-goal']
        panel = Doc(self.archive.region_panel(name, slug, ts + [goal], 'map/', self.meta, True, site=self.site))
        self.assertEqual([li['data-key'] for li in self.rows(panel)],
                         ['syn-m-range-a', 'syn-m-range-b', 'syn-m-range-tour', CREST, LOOP, 'syn-m-desert-goal'])

    def test_a_folded_list_still_shows_them(self):
        # 'Show all N' folds away the reports after the first SHOW; a journal row is never one of the folded
        regs = self.archive.regions(self.site, self.meta)
        name, slug, ts = next(r for r in regs if r[0] == RANGE)
        many = (ts * 5)[:self.archive.SHOW + 4]
        panel = Doc(self.archive.region_panel(name, slug, many, 'map/', self.meta, True, site=self.site))
        rows = self.rows(panel)
        folded = [li for li in rows if 'arc-more' in li.classes]
        self.assertEqual(len(folded), 4)
        self.assertEqual([li for li in folded if 'arc-row--journal' in li.classes], [])
        # right after the rows that stay shown and before the folded ones, so folding at load does not move them
        self.assertEqual([li['data-key'] for li in rows[self.archive.SHOW:self.archive.SHOW + 2]], [CREST, LOOP])
        self.assertEqual([li for li in rows[:self.archive.SHOW] if 'arc-more' in li.classes], [])
        self.assertEqual(rows[self.archive.SHOW + 2:], folded)
        button = panel.find('button', cls='arc-all-btn')
        self.assertIn('Show all %d' % len(many), button.text())               # the button counts reports, as before
        # and a short list with them is not folded for their sake
        short = Doc(self.archive.region_panel(name, slug, ts, 'map/', self.meta, True, site=self.site))
        self.assertIsNone(short.find('button', cls='arc-all-btn'))

    def test_the_legend_names_its_activity_once_the_map_draws_it(self):
        def activities(panel):
            return [li.text() for li in panel.find('ul', attrs={'aria-label': 'Activities'}).find_all('li')]
        before = activities(self.panel(RANGE))
        self.assertNotIn('Mountain Biking', before)        # the map was not drawn with the journal's days yet
        self.drawn()
        self.assertEqual(sorted(activities(self.panel(RANGE))), sorted(before + ['Mountain Biking']))
        # a map entry that names another journal, or is not a list, adds nothing
        for other in ([{'slug': 'syn-m-no-such-journal', 'days': ['001']}], 'nope', [None], [{'slug': PAGE_JOURNAL + '-x', 'key': ['a'], 'glyph': 7}]):
            with self.subTest(journals=other):
                self.meta['maps']['region-%s-desktop' % SLUG[RANGE]]['journals'] = other
                regs = self.archive.regions(self.site, self.meta)
                name, slug, ts = next(r for r in regs if r[0] == RANGE)
                panel = Doc(self.archive.region_panel(name, slug, ts, 'map/', self.meta, True, site=self.site))
                self.assertEqual(sorted(activities(panel)), sorted(before))

    def test_without_a_site_the_panel_is_the_one_it_was(self):
        regs = self.archive.regions(self.site, self.meta)
        name, slug, ts = next(r for r in regs if r[0] == RANGE)
        bare = self.archive.region_panel(name, slug, ts, 'map/', self.meta, True)
        self.assertNotIn('arc-row--journal', bare)
        with_site = self.archive.region_panel(name, slug, ts, 'map/', self.meta, True, site=self.site)
        self.assertEqual(with_site.count('arc-row--journal'), 2)
        # the two rows are the only difference
        start = with_site.index('<li class="arc-row arc-row--journal')
        end = with_site.rindex('<li class="arc-row arc-row--journal')
        end = with_site.index('</li>', end) + len('</li>')
        self.assertEqual(with_site[:start] + with_site[end:], bare)

    def test_the_regions_own_page_has_the_rows_too(self):
        region = load_module(self, 'sitegen.pages.region')
        pages = {p.url: p for p in region.build(self.site)}
        page = pages['regions/%s/' % SLUG[RANGE]]
        doc = Doc(page.html)
        rows = [li for li in doc.by_id('map').find_all('li') if 'arc-row--journal' in li.classes]
        self.assertEqual([li['data-key'] for li in rows], [CREST, LOOP])
        self.assertEqual(rows[0].find('a')['href'], '../../trips/%s/#day-1' % PAGE_JOURNAL)
        other = Doc(pages['regions/%s/' % SLUG[COAST]].html)
        self.assertEqual([li['data-key'] for li in other.find_all('li') if 'arc-row--journal' in li.classes], [PAGE_JOURNAL])
        # the page's table of reports does not take the journal in
        table = [a['href'] for a in doc.by_id('all-reports').find_all('a')]
        self.assertTrue(table)
        self.assertFalse([h for h in table if PAGE_JOURNAL in h])


def core_dist(km):
    from sitegen import core
    return core.dist_vals(km)


# ---------------------------------------------------------------- the validator

GPX = ('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1">\n'
       '<trk><name>Synthetic</name><trkseg><trkpt lat="10.001" lon="10.0"><ele>1</ele></trkpt>'
       '<trkpt lat="10.002" lon="10.01"><ele>2</ele></trkpt></trkseg></trk>\n</gpx>\n')
TODAY = datetime.date(2026, 10, 12)


class ValidatorTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.realpath(tmp.name)
        self.trips = os.path.join(self.root, 'content', 'trips')
        self.rendered = os.path.join(self.root, 'rendered')
        self.home = os.path.join(self.root, 'content', 'home.json')
        os.makedirs(self.trips)
        for i, slug in enumerate(('syn-v-ridge', 'syn-v-lake', 'syn-v-pass')):
            folder = helpers.make_trip(self.trips, slug, title=slug.replace('-', ' ').title(), date='2025-06-%02d' % (10 + i),
                                       region='Synthetic Range')
            self.write(os.path.join(folder, 'track.gpx'), GPX)
        folder = helpers.make_trip(self.trips, 'syn-v-cove', title='Syn V Cove', date='2025-07-01', region='Synthetic Coast')
        self.write(os.path.join(folder, 'track.gpx'), GPX)
        self.write(self.home, json.dumps({'featured_slugs': []}))

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)

    def journal(self, region_days, tracks=None):
        folder = journal(self.trips, labels=('1', '2', '3'), tracks=tracks, region_days=region_days)
        for name in sorted(os.listdir(os.path.join(folder, 'days'))):
            if name.endswith('.gpx'):
                self.write(os.path.join(folder, 'days', name), GPX)

    def maps(self, journals=None, mapped=('Synthetic Range',)):
        entry = {'w': 10, 'h': 10, 'region': 'Synthetic Range', 'trips': ['syn-v-ridge', 'syn-v-lake', 'syn-v-pass']}
        if journals is not None:
            entry = dict(entry, journals=journals)
        meta = {'hash': '', 'regions': list(mapped), 'all_regions': ['Synthetic Coast', 'Synthetic Range'],
                'maps': {'region-synthetic-range-desktop': entry, 'region-synthetic-range-phone': entry}}
        self.write(os.path.join(self.rendered, 'site', 'meta.json'), json.dumps(meta))

    def findings(self, rendered=True):
        out = checks.run(self.trips, self.home, self.rendered if rendered else os.path.join(self.root, 'no-such-folder'), TODAY)
        return [checks.line(f) for f in out if 'region_days' in f['text'] or 'the region map of' in f['text']]

    AGAIN = 'run python3 tools/render.py --site and commit rendered/site/'

    def test_days_the_map_draws_are_quiet(self):
        self.journal({'Synthetic Range': '1-2'})
        self.maps(journals=[{'slug': JOURNAL, 'days': ['001', '002']}])
        self.assertEqual(self.findings(), [])

    def test_a_region_no_report_is_filed_under_is_an_error(self):
        self.journal({'Synthetic Rnage': '1-2'})
        self.maps()
        self.assertEqual(self.findings(), ["ERROR %s: region_days names the region 'Synthetic Rnage', which no report is filed under "
                                           "(did you mean 'Synthetic Range'?)" % WHERE])
        # also without a rendered folder to read
        self.assertEqual(self.findings(rendered=False), self.findings())

    def test_a_region_without_a_region_map_is_a_warning(self):
        self.journal({'Synthetic Coast': '1'})
        self.maps()
        self.assertEqual(self.findings(), ["WARNING %s: region_days: 'Synthetic Coast' has no region map (one is drawn from three "
                                           'reports with a track), so these days are shown on no map' % WHERE])

    def test_a_map_drawn_before_the_days_were_listed_is_a_warning(self):
        self.journal({'Synthetic Range': '1-2'})
        self.maps()
        self.assertEqual(self.findings(), ['WARNING %s: region_days: the region map of Synthetic Range was last drawn without these '
                                           'days; %s' % (WHERE, self.AGAIN)])

    def test_a_map_drawn_with_other_days_is_a_warning(self):
        self.journal({'Synthetic Range': '1-3'})
        self.maps(journals=[{'slug': JOURNAL, 'days': ['001', '002']}])
        self.assertEqual(self.findings(), ['WARNING %s: region_days: the region map of Synthetic Range was last drawn with other '
                                           'days of this journal; %s' % (WHERE, self.AGAIN)])

    def test_a_stretch_is_compared_too(self):
        self.journal({'Synthetic Range': '1/1, 2'})
        drawn = {'slug': JOURNAL, 'days': ['001', '002']}
        self.maps(journals=[dict(drawn, stretches={'001': 1})])
        self.assertEqual(self.findings(), [])
        # the same days, drawn whole or with another stretch
        for other in (drawn, dict(drawn, stretches={'001': 2}), dict(drawn, stretches={'002': 1}), dict(drawn, stretches='nope')):
            with self.subTest(journals=other):
                self.maps(journals=[other])
                self.assertEqual(self.findings(), ['WARNING %s: region_days: the region map of Synthetic Range was last drawn with '
                                                   'another stretch of one of these days; %s' % (WHERE, self.AGAIN)])
        # and a map drawn with a stretch of a day the block now takes whole
        self.journal({'Synthetic Range': '1-2'})
        self.maps(journals=[dict(drawn, stretches={'001': 1})])
        self.assertEqual(self.findings(), ['WARNING %s: region_days: the region map of Synthetic Range was last drawn with '
                                           'another stretch of one of these days; %s' % (WHERE, self.AGAIN)])

    def test_a_stretch_the_track_does_not_have_is_an_error(self):
        # the fixture's days are one short line each: one stretch
        self.journal({'Synthetic Range': {'Synthetic Loop': '1/2, 2'}})
        self.maps(journals=[{'slug': JOURNAL, 'key': JOURNAL + ':synthetic-loop', 'title': 'Synthetic Loop', 'days': ['001', '002'],
                             'stretches': {'001': 2}}])
        self.assertEqual(self.findings(), ['ERROR %s: region_days takes stretch 2 of day 1, whose track has 1 (a stretch ends where '
                                           'two fixes lie more than 20 km apart)' % WHERE])
        # without a site meta the stretch is still looked at
        self.assertEqual(self.findings(rendered=False), ['ERROR %s: region_days takes stretch 2 of day 1, whose track has 1 (a stretch '
                                                         'ends where two fixes lie more than 20 km apart)' % WHERE])

    def test_a_stretch_of_a_day_without_a_track_is_an_error(self):
        self.journal({'Synthetic Range': '1/1, 2'}, tracks=(False, True, True))
        self.maps(journals=[{'slug': JOURNAL, 'days': ['002']}])
        self.assertEqual(self.findings(), ['ERROR %s: region_days takes stretch 1 of day 1, whose track holds no fixes' % WHERE])

    def test_named_parts_are_compared_part_by_part(self):
        self.journal({'Synthetic Range': {'Synthetic Crest': '1-2', 'Synthetic Loop': '3'}})
        crest = {'slug': JOURNAL, 'key': JOURNAL + ':synthetic-crest', 'title': 'Synthetic Crest', 'days': ['001', '002']}
        loop = {'slug': JOURNAL, 'key': JOURNAL + ':synthetic-loop', 'title': 'Synthetic Loop', 'days': ['003']}
        self.maps(journals=[crest, loop])
        self.assertEqual(self.findings(), [])
        # one part drawn with other days, the other not drawn at all: a line each, naming the part
        self.maps(journals=[dict(crest, days=['001'])])
        self.assertEqual(self.findings(), [
            'WARNING %s: region_days: the region map of Synthetic Range (Synthetic Crest) was last drawn with other days of this '
            'journal; %s' % (WHERE, self.AGAIN),
            'WARNING %s: region_days: the region map of Synthetic Range (Synthetic Loop) was last drawn without these days; %s'
            % (WHERE, self.AGAIN)])
        # a map drawn before the parts had names still draws the days under the journal's own key
        self.maps(journals=[{'slug': JOURNAL, 'days': ['001', '002', '003']}])
        self.assertEqual(len([f for f in self.findings() if 'was last drawn without these days' in f]), 2)
        self.assertEqual(len([f for f in self.findings() if 'still draws days of this journal' in f]), 1)

    def test_a_mistyped_region_with_several_parts_is_one_line(self):
        self.journal({'Synthetic Rnage': {'Synthetic Crest': '1-2', 'Synthetic Loop': '3'}})
        self.maps()
        self.assertEqual(self.findings(), ["ERROR %s: region_days names the region 'Synthetic Rnage', which no report is filed under "
                                           "(did you mean 'Synthetic Range'?)" % WHERE])

    def test_listed_days_without_a_track_are_not_expected_on_the_map(self):
        self.journal({'Synthetic Range': '1-3'}, tracks=(True, False, True))
        self.maps(journals=[{'slug': JOURNAL, 'days': ['001', '003']}])
        self.assertEqual(self.findings(), [])

    def test_a_map_that_still_draws_days_the_block_dropped_is_a_warning(self):
        self.journal(None)
        self.maps(journals=[{'slug': JOURNAL, 'days': ['001', '002']}])
        self.assertEqual(self.findings(), ['WARNING %s: the region map of Synthetic Range still draws days of this journal that '
                                           'region_days no longer lists there; %s' % (WHERE, self.AGAIN)])

    def test_without_a_site_meta_only_the_names_are_checked(self):
        self.journal({'Synthetic Range': '1-2'})
        self.assertEqual(self.findings(rendered=False), [])
        self.write(os.path.join(self.rendered, 'site', 'meta.json'), '{not json')
        self.assertEqual(self.findings(), [])

    def test_the_block_is_a_known_key(self):
        self.journal({'Synthetic Range': '1-2'})
        self.maps(journals=[{'slug': JOURNAL, 'days': ['001', '002']}])
        out = checks.run(self.trips, self.home, self.rendered, TODAY)
        self.assertEqual([checks.line(f) for f in out if 'unknown key' in f['text']], [])
        self.assertIn('region_days', checks.INDEX_KEYS)


if __name__ == '__main__':
    unittest.main()
