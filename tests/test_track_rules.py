"""Phase 4, contract-phase4.md 10.2 and 10.3: what the generator says about a recording depends on whether there is one.

  core.has_track(t)        the trip's own track.gpx, or any day's
  core.render_meta(t)      10.3: no maps and no charts for a trip without a track, whatever its rendered folder holds
  core.glyph / core.tile   10.3: no route drawing for it either
  core.summary(t)          the closing fact 'with map and GPX' ('with map, elevation profile and GPX', 'with map, speed
                           chart and GPX') only with a track; with no fact at all the first sentence alone
  core.stats_note(t, cls)  without a track neither 'Stats from the GPS recording.' nor 'GPS max is the highest
                           point in the GPX file, ...'; what is left is the beta's Track line and the pace (flat water)
                           or average-speed (mountain bike) sentence, and '' when nothing is left. 10.3: that
                           sentence is written only when the stats hold a distance and a moving time
  core.photo(...)          width / height and the srcset only when BOTH w and h are recorded

A trip with a track is pinned to the exact strings it always got, so the tables read in pairs: the same content with
its track file, then without it. (No fixture carries a strava_id or a source: line, so its source sentence is the plain
'Stats from the GPS recording.'; SourceWordTests has the 'via Strava' of the real trips and the other forms.) What a page does with these (report.page, report.build, section.pick_featured) is in
tests/test_report_page.py NoTrackTests; the built site, its feed and its JSON-LD in tests/test_build_site.py.

Synthetic trips are written to a temp dir with tests/helpers.py and loaded with content.load_trip. A rendered chart is
a meta.json in the temp dir the trip is pointed at; nothing under content/ or rendered/ is read.
"""
import itertools
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, LANDSCAPE, PORTRAIT  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

PREFIX = 'synt-'             # every fixture slug starts with it; no real trip's slug does
REGION = 'Synthetic Range'
STATS = {'distance_km': 12.0, 'gain_m': 800, 'high_m': 2900, 'low_m': 2100}
TRACK_NOTE = 'Synthetic recorder & one synthetic gap.'          # a beta row labelled Track, with its own full stop

RECORDING = 'Stats from the GPS recording.'
GPS_MAX = 'GPS max is the highest point in the GPX file, not a surveyed summit height.'
AVG_SPEED = 'Average speed is distance divided by moving time.'
PACE = 'Pace is moving time divided by distance.'
MOVING = 'Moving time leaves out stops.'            # Phase 10 (gap6-05): a recorded report whose strip shows Moving
TRACK_LINE = 'Track: Synthetic recorder &amp; one synthetic gap.'
CLOSING = ('with map and GPX', 'with map, elevation profile and GPX', 'with map, speed chart and GPX')


class Fixture(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.k = 0

    def trip(self, **meta):
        """One synthetic trip, loaded; track=True writes its track.gpx."""
        self.k += 1
        slug = '%s%d' % (PREFIX, self.k)
        helpers.make_trip(self.tmp, slug, **meta)
        t = helpers.load(self.tmp, slug)
        self.assertFalse(os.path.lexists(t['rendered']), 'fixture slug %r names a real trip' % slug)
        return t

    def pair(self, **meta):
        """(the trip with its track.gpx, the same content without one)."""
        with_, without = self.trip(track=True, **meta), self.trip(track=False, **meta)
        self.assertTrue(with_['track'])
        self.assertIsNone(without['track'])
        return with_, without

    def tour(self, tracks, kind='multi-day', stats=None, **meta):
        """A trip with one day per entry of `tracks` (True: the day has its GPX)."""
        days = [dict({'title': 'Synthetic Day %d' % (i + 1), 'date': '2026-03-%02d' % (10 + i), 'track': has},
                     **({'stats': stats} if stats else {})) for i, has in enumerate(tracks)]
        if kind == 'series':
            days = [dict(d, id='%03d' % (i + 1)) for i, d in enumerate(days)]
            meta.setdefault('date', '2026-03-10')
            meta.setdefault('end_date', '2026-03-%02d' % (9 + len(tracks)))
        meta.setdefault('title', 'Synthetic Tour')
        meta.setdefault('region', REGION)
        t = self.trip(kind=kind, days=days, **meta)
        self.assertEqual([bool(d['track']) for d in t['days']], list(tracks))
        self.assertIsNone(t['track'])
        return t

    def chart(self, t, kind):
        """Point the trip at a rendered folder in the temp dir whose meta.json lists a profile or a speed chart."""
        folder = os.path.join(self.tmp, '_rendered', t['slug'])
        os.makedirs(folder, exist_ok=True)
        meta = {'maps': {}, 'charts': {'%s-%s' % (kind, size): {'w': w, 'h': 160} for size, w in (('wide', 1248), ('col', 718), ('phone', 358))}}
        with open(os.path.join(folder, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(meta, fh)
        t['rendered'] = folder
        return t


# ---------------------------------------------------------------- core.has_track

class HasTrackTests(Fixture):

    def test_a_single_day_report(self):
        with_, without = self.pair(title='Synthetic Hike', date='2026-06-01')
        self.assertIs(core.has_track(with_), True)
        self.assertIs(core.has_track(without), False)

    def test_a_multi_day_trip_has_one_when_any_day_does(self):
        for tracks, want in (((True, True), True), ((True, False, False), True), ((False, False, True), True), ((False, False), False),
                             ((True,), True), ((False,), False)):
            with self.subTest(tracks=tracks):
                self.assertIs(core.has_track(self.tour(tracks)), want)

    def test_a_journal_has_one_when_any_day_does(self):
        for tracks, want in (((True, True, True), True), ((False, True, False), True), ((False, False, False), False)):
            with self.subTest(tracks=tracks):
                self.assertIs(core.has_track(self.tour(tracks, kind='series', title='Synthetic Journal')), want)

    def test_a_planned_route_and_an_idea(self):
        self.assertIs(core.has_track(self.trip(title='Synthetic Goal', kind='planned', track=True)), True)
        self.assertIs(core.has_track(self.trip(title='Synthetic Idea', kind='planned')), False)

    def test_it_reads_the_two_fields_and_nothing_else(self):
        # the trip dict's 'track' and each day's 'track' (a path or None); a missing key or a missing day list is no track
        self.assertIs(core.has_track({}), False)
        self.assertIs(core.has_track({'track': None, 'days': []}), False)
        self.assertIs(core.has_track({'track': None, 'days': None}), False)
        self.assertIs(core.has_track({'track': '', 'days': [{'track': None}, {}]}), False)
        self.assertIs(core.has_track({'track': '/x/track.gpx'}), True)
        self.assertIs(core.has_track({'track': '/x/track.gpx', 'days': []}), True)
        self.assertIs(core.has_track({'track': None, 'days': [{'track': None}, {'track': '/x/days/02.gpx'}]}), True)
        self.assertIs(core.has_track({'days': [{'track': '/x/days/01.gpx'}]}), True)
        # a rendered folder, stats, a write-up or photos are not a track
        t = self.chart(self.trip(title='Synthetic Hike', stats=STATS, body='Synthetic words.'), 'profile')
        self.assertIs(core.has_track(t), False)


# ---------------------------------------------------------------- core.summary

class SummaryTests(Fixture):

    def assertPair(self, pair, with_, without):
        self.assertEqual(core.summary(pair[0]), with_)
        self.assertEqual(core.summary(pair[1]), without)
        self.assertNoPromise(without)

    def assertNoPromise(self, text):
        self.assertNotIn('GPX', text)
        self.assertNotIn('map', text)
        self.assertNotIn('chart', text)
        self.assertNotIn('profile', text)
        self.assertNotIn(' with ', text)
        self.assertTrue(text.endswith('.') and not text.endswith('..'), text)
        self.assertNotRegex(text, r',\s*[,.]|\s[,.]|\.\s*\.')

    def test_a_single_day_report_with_stats(self):
        # the closing fact follows the others after a comma; without a track the facts end the sentence
        first = 'Hiking trip report: Synthetic Hike, Synthetic Basin, Synthetic Range, Mon, Jun 1, 2026.'
        pair = self.pair(title='Synthetic Hike', date='2026-06-01', place='Synthetic Basin', region=REGION, stats=STATS)
        self.assertPair(pair, first + ' 7.5 mi, 2,625 ft gain, GPS max 9,514 ft, with map and GPX.',
                        first + ' 7.5 mi, 2,625 ft gain, GPS max 9,514 ft.')

    def test_a_single_day_report_with_no_stats_at_all(self):
        # no facts: with a track the closing fact is the whole second sentence, as it always was; without one the
        # summary is the first sentence alone: '<lead>: <title>, <where>, <when>.'
        pair = self.pair(title='Synthetic Hike', date='2026-06-01', region=REGION)
        self.assertPair(pair, 'Hiking trip report: Synthetic Hike, Synthetic Range, Mon, Jun 1, 2026. with map and GPX.',
                        'Hiking trip report: Synthetic Hike, Synthetic Range, Mon, Jun 1, 2026.')
        pair = self.pair(title='Synthetic Hike', date='2026-06-01', place='Synthetic Basin', region=REGION)
        self.assertPair(pair, 'Hiking trip report: Synthetic Hike, Synthetic Basin, Synthetic Range, Mon, Jun 1, 2026. with map and GPX.',
                        'Hiking trip report: Synthetic Hike, Synthetic Basin, Synthetic Range, Mon, Jun 1, 2026.')
        # ... down to the title alone, for a report with no place, no region and no date
        pair = self.pair(title='Synthetic Hike')
        self.assertPair(pair, 'Hiking trip report: Synthetic Hike. with map and GPX.', 'Hiking trip report: Synthetic Hike.')

    def test_one_fact_is_enough_for_the_second_sentence(self):
        pair = self.pair(title='Synthetic Ride', activity='mtb', date='2026-06-01', region=REGION, stats={'distance_km': 20.0})
        self.assertPair(pair, 'Mountain biking trip report: Synthetic Ride, Synthetic Range, Mon, Jun 1, 2026. 12.4 mi, with map and GPX.',
                        'Mountain biking trip report: Synthetic Ride, Synthetic Range, Mon, Jun 1, 2026. 12.4 mi.')
        pair = self.pair(title='Synthetic Climb', activity='climb', date='2026-06-01', region=REGION, stats={'high_m': 2900})
        self.assertPair(pair, 'Climbing trip report: Synthetic Climb, Synthetic Range, Mon, Jun 1, 2026. GPS max 9,514 ft, with map and GPX.',
                        'Climbing trip report: Synthetic Climb, Synthetic Range, Mon, Jun 1, 2026. GPS max 9,514 ft.')

    def test_flat_water_states_the_distance_only(self):
        pair = self.pair(title='Synthetic Paddle', activity='other', subtype='SUP', date='2026-06-01', region=REGION,
                         stats={'distance_km': 5.0, 'gain_m': 12, 'high_m': 1900, 'low_m': 1899, 'moving': '1:00'})
        self.assertPair(pair, 'Paddleboarding trip report: Synthetic Paddle, Synthetic Range, Mon, Jun 1, 2026. 3.1 mi, with map and GPX.',
                        'Paddleboarding trip report: Synthetic Paddle, Synthetic Range, Mon, Jun 1, 2026. 3.1 mi.')

    def test_a_rendered_chart_is_named_only_with_a_track(self):
        # with a track the closing fact names the chart the page draws; without one nothing is promised, whatever a
        # render folder left behind still holds
        first = 'Hiking trip report: Synthetic Hike, Synthetic Range, Mon, Jun 1, 2026.'
        with_, without = self.pair(title='Synthetic Hike', date='2026-06-01', region=REGION, stats=STATS)
        facts = ' 7.5 mi, 2,625 ft gain, GPS max 9,514 ft'
        self.chart(with_, 'profile')
        self.chart(without, 'profile')
        self.assertPair((with_, without), first + facts + ', with map, elevation profile and GPX.', first + facts + '.')
        self.chart(with_, 'speed')
        self.chart(without, 'speed')
        self.assertPair((with_, without), first + facts + ', with map, speed chart and GPX.', first + facts + '.')
        with_, without = self.pair(title='Synthetic Hike', date='2026-06-01', region=REGION)
        self.chart(with_, 'profile')
        self.chart(without, 'profile')
        self.assertPair((with_, without), first + ' with map, elevation profile and GPX.', first)

    def test_a_multi_day_trip_with_and_without_any_day_track(self):
        first = '2-day backcountry skiing trip report: Synthetic Tour, Synthetic Range, Mar 10–11, 2026.'
        day = {'distance_km': 10.0, 'gain_m': 450}
        for tracks in ((True, True), (True, False), (False, True)):
            with self.subTest(tracks=tracks):
                self.assertEqual(core.summary(self.tour(tracks, activity='ski', stats=day)), first + ' 12.4 mi, 2,953 ft gain, with map and GPX.')
                self.assertEqual(core.summary(self.tour(tracks, activity='ski')), first + ' with map and GPX.')
        without = core.summary(self.tour((False, False), activity='ski', stats=day))
        self.assertEqual(without, first + ' 12.4 mi, 2,953 ft gain.')
        self.assertNoPromise(without)
        bare = core.summary(self.tour((False, False), activity='ski'))
        self.assertEqual(bare, first)
        self.assertNoPromise(bare)

    def test_the_journal_with_and_without_any_day_track(self):
        first = 'Hiking series: Synthetic Journal, Synthetic Range, Mar 10–12, 2026.'
        day = {'distance_km': 10.0}
        for tracks in ((True, True, True), (False, True, False)):
            with self.subTest(tracks=tracks):
                t = self.tour(tracks, kind='series', title='Synthetic Journal')
                self.assertEqual(core.summary(t), first + ' 3 recorded days, with map and GPX.')
                t = self.tour(tracks, kind='series', title='Synthetic Journal', stats=day)
                self.assertEqual(core.summary(t), first + ' 3 recorded days, 18.6 mi, with map and GPX.')
        without = core.summary(self.tour((False, False, False), kind='series', title='Synthetic Journal'))
        self.assertEqual(without, first + ' 3 recorded days.')
        self.assertNoPromise(without)
        without = core.summary(self.tour((False, False, False), kind='series', title='Synthetic Journal', stats=day))
        self.assertEqual(without, first + ' 3 recorded days, 18.6 mi.')
        self.assertNoPromise(without)

    def test_the_closing_fact_is_there_exactly_when_the_trip_has_a_track(self):
        trips = list(self.pair(title='Synthetic Hike', date='2026-06-01', stats=STATS)) + list(self.pair(title='Synthetic Hike'))
        trips += [self.tour(t) for t in ((True, False), (False, False))]
        trips += [self.tour(t, kind='series') for t in ((True, False), (False, False))]
        self.assertEqual([core.has_track(t) for t in trips], [True, False] * 4)
        for t in trips:
            with self.subTest(slug=t['slug'], kind=t['kind']):
                text = core.summary(t)
                self.assertEqual(sum(text.count(c) for c in CLOSING[:1]), 1 if core.has_track(t) else 0)
                self.assertEqual(text.endswith('with map and GPX.'), core.has_track(t))
                self.assertEqual('GPX' in text, core.has_track(t))

    def test_a_planned_route_is_worded_as_before(self):
        # not part of 10.2: a goal's summary already said what it has
        goal = self.trip(title='Synthetic Goal', kind='planned', region=REGION, track=True)
        idea = self.trip(title='Synthetic Idea', kind='planned', region=REGION)
        self.assertEqual(core.summary(goal), 'Synthetic Goal: planned hiking route, Synthetic Range. Planned GPX download.')
        self.assertEqual(core.summary(idea), 'Synthetic Idea: planned hiking route, Synthetic Range. An idea on the tick list, no route yet.')


# ---------------------------------------------------------------- core.stats_note

class StatsNoteTests(Fixture):

    # (activity and its fixture) -> the sentence about a derived value the note carries whatever the track
    KINDS = {
        'flat-water': (dict(activity='other', subtype='SUP', stats={'distance_km': 5.0, 'moving': '1:00'}), [PACE]),
        'mtb': (dict(activity='mtb', stats={'distance_km': 20.0, 'gain_m': 500, 'high_m': 900, 'low_m': 400, 'moving': '2:00'}), [AVG_SPEED]),
        'other': (dict(activity='hike', stats=STATS), []),
    }

    def note(self, sentences, cls=''):
        return ('<p class="strip-note%s">%s</p>' % ((' ' + cls) if cls else '', ' '.join(sentences))) if sentences else ''

    def test_every_combination(self):
        # (a track or not) x (flat water, mountain bike, anything else) x (a beta row labelled Track or not)
        seen = set()
        for kind, beta in itertools.product(sorted(self.KINDS), (False, True)):
            meta, derived = self.KINDS[kind]
            rows = [{'label': 'Trailhead', 'value': 'Synthetic Lot'}] + ([{'label': 'Track', 'value': TRACK_NOTE}] if beta else [])
            with_, without = self.pair(title='Synthetic ' + kind, date='2026-06-01', region=REGION, beta=rows, **meta)
            self.assertEqual(core.is_flat(with_), kind == 'flat-water')
            track_line = [TRACK_LINE] if beta else []
            gps_max = [] if kind == 'flat-water' else [GPS_MAX]
            moving = [MOVING] if meta['stats'].get('moving') else []
            with self.subTest(kind=kind, beta=beta, track=True):
                # the source, the beta's Track line, the derived value, what GPS max means, what Moving means (Phase 10)
                self.assertEqual(core.stats_note(with_), self.note([RECORDING] + track_line + derived + gps_max + moving))
            with self.subTest(kind=kind, beta=beta, track=False):
                left = track_line + derived
                got = core.stats_note(without)
                self.assertEqual(got, self.note(left))
                self.assertNotIn('GPS recording', got)
                self.assertNotIn('GPX file', got)
                self.assertNotIn('Strava', got)
                self.assertNotIn('GPS max', got)
                self.assertEqual(got == '', not left)
                seen.add(got)
        self.assertEqual(len(seen), 6)                # six different notes without a track, one of them no note at all
        self.assertIn('', seen)

    def test_the_six_notes_without_a_track_word_for_word(self):
        track = [{'label': 'Track', 'value': TRACK_NOTE}]
        hike = dict(activity='hike', stats=STATS, track=False)
        ride = dict(self.KINDS['mtb'][0], track=False)
        paddle = dict(self.KINDS['flat-water'][0], track=False)
        self.assertEqual(core.stats_note(self.trip(**hike)), '')
        self.assertEqual(core.stats_note(self.trip(beta=track, **hike)),
                         '<p class="strip-note">Track: Synthetic recorder &amp; one synthetic gap.</p>')
        self.assertEqual(core.stats_note(self.trip(**ride)),
                         '<p class="strip-note">Average speed is distance divided by moving time.</p>')
        self.assertEqual(core.stats_note(self.trip(beta=track, **ride)),
                         '<p class="strip-note">Track: Synthetic recorder &amp; one synthetic gap. Average speed is distance divided by moving time.</p>')
        self.assertEqual(core.stats_note(self.trip(**paddle)), '<p class="strip-note">Pace is moving time divided by distance.</p>')
        self.assertEqual(core.stats_note(self.trip(beta=track, **paddle)),
                         '<p class="strip-note">Track: Synthetic recorder &amp; one synthetic gap. Pace is moving time divided by distance.</p>')

    def test_the_note_with_a_track_word_for_word(self):
        t = self.trip(activity='hike', stats=STATS, track=True)
        self.assertEqual(core.stats_note(t), '<p class="strip-note">Stats from the GPS recording. GPS max is the highest point in '
                                             'the GPX file, not a surveyed summit height.</p>')
        t = self.trip(track=True, beta=[{'label': 'Track', 'value': TRACK_NOTE}], **self.KINDS['mtb'][0])
        self.assertEqual(core.stats_note(t),
                         '<p class="strip-note">Stats from the GPS recording. Track: Synthetic recorder &amp; one synthetic gap. '
                         'Average speed is distance divided by moving time. GPS max is the highest point in the GPX file, not a surveyed '
                         'summit height. Moving time leaves out stops.</p>')
        t = self.trip(track=True, **self.KINDS['flat-water'][0])
        self.assertEqual(core.stats_note(t), '<p class="strip-note">Stats from the GPS recording. Pace is moving time divided by '
                                             'distance. Moving time leaves out stops.</p>')

    def test_the_class_is_added_to_a_note_and_never_makes_one(self):
        with_, without = self.pair(activity='hike', stats=STATS)
        self.assertEqual(core.stats_note(with_, 'rep-note-ph'), self.note([RECORDING, GPS_MAX], 'rep-note-ph'))
        self.assertEqual(core.stats_note(with_, cls='rep-note-ph'), core.stats_note(with_, 'rep-note-ph'))
        self.assertEqual(core.stats_note(without, 'rep-note-ph'), '')
        ride = self.trip(track=False, **self.KINDS['mtb'][0])
        self.assertEqual(core.stats_note(ride, 'rep-note-ph'), '<p class="strip-note rep-note-ph">%s</p>' % AVG_SPEED)

    def test_there_is_never_an_empty_paragraph(self):
        for meta in (dict(activity='hike'), dict(activity='ski', stats=STATS), dict(activity='climb'), dict(activity='other', subtype='Rafting',
                                                                                                           stats={'high_m': 900, 'low_m': 100})):
            for beta in ([], [{'label': 'Trailhead', 'value': 'Synthetic Lot'}], [{'label': 'Track', 'value': ''}]):
                with self.subTest(meta=meta, beta=beta):
                    with_, without = self.pair(beta=beta, **meta)
                    self.assertEqual(core.stats_note(without), '')
                    got = Doc(core.stats_note(with_)).find('p', cls='strip-note')
                    self.assertTrue(got.text())

    def test_a_day_track_is_a_recording(self):
        # core.has_track decides: a trip whose days carry the tracks is recorded
        self.assertEqual(core.stats_note(self.tour((True, False))), self.note([RECORDING, GPS_MAX]))
        self.assertEqual(core.stats_note(self.tour((False, False))), '')
        self.assertEqual(core.stats_note(self.tour((False, True, False), kind='series')), self.note([RECORDING, GPS_MAX]))
        self.assertEqual(core.stats_note(self.tour((False, False, False), kind='series')), '')

    def test_a_rendered_folder_is_not_a_recording(self):
        t = self.chart(self.trip(activity='hike', stats=STATS, track=False), 'profile')
        self.assertEqual(core.stats_note(t), '')


class DerivedValueNoteTests(Fixture):
    """contract-phase4.md 10.3: 'Pace is moving time divided by distance.' (flat water) and 'Average speed is distance
    divided by moving time.' (mountain bike) are written only when stats.distance_km and the moving time are both
    there: the condition under which core.strip_cells shows that value. With a track or without one."""

    STATS = {'none': None, 'distance': {'distance_km': 20.0}, 'moving': {'moving': '2:00'}, 'zero': {'distance_km': 0, 'moving': '2:00'},
             'both': {'distance_km': 20.0, 'moving': '2:00'}, 'all': {'distance_km': 20.0, 'gain_m': 500, 'high_m': 900, 'low_m': 880, 'moving': '2:00'}}
    KINDS = (('mtb', {}, AVG_SPEED, 'Avg speed', True), ('other', {'subtype': 'SUP'}, PACE, 'Avg pace', False),
             ('other', {'subtype': 'Kayaking'}, PACE, 'Avg pace', False))

    def note(self, sentences):
        return ('<p class="strip-note">%s</p>' % ' '.join(sentences)) if sentences else ''

    def test_the_sentence_needs_a_distance_and_a_moving_time(self):
        for act, extra, sentence, label, gps_max in self.KINDS:
            for name, stats in sorted(self.STATS.items()):
                meta = dict(activity=act, date='2026-06-01', region=REGION, **extra)
                if stats:
                    meta['stats'] = stats
                with_, without = self.pair(**meta)
                derived = [sentence] if name in ('both', 'all') else []
                moving = [MOVING] if name in ('moving', 'zero', 'both', 'all') else []
                with self.subTest(act=act, subtype=extra.get('subtype'), stats=name):
                    self.assertEqual(core.is_flat(with_), not gps_max)
                    self.assertEqual(core.stats_note(with_), self.note([RECORDING] + derived + ([GPS_MAX] if gps_max else []) + moving))
                    self.assertEqual(core.stats_note(without), self.note(derived))
                    # the sentence explains a value: it is there exactly when the strip shows that value
                    for t in (with_, without):
                        labels = [c[0] for c in core.strip_cells(t)]
                        self.assertEqual(label in labels, bool(derived))
                        self.assertEqual(sentence in core.stats_note(t), label in labels)

    def test_word_for_word(self):
        ride = dict(activity='mtb', track=True)
        self.assertEqual(core.stats_note(self.trip(**ride)),
                         '<p class="strip-note">Stats from the GPS recording. GPS max is the highest point in the GPX file, not a '
                         'surveyed summit height.</p>')
        self.assertEqual(core.stats_note(self.trip(stats={'distance_km': 20.0}, **ride)), core.stats_note(self.trip(**ride)))
        self.assertEqual(core.stats_note(self.trip(stats={'distance_km': 20.0, 'moving': '2:00'}, **ride)),
                         '<p class="strip-note">Stats from the GPS recording. Average speed is distance divided by moving time. GPS '
                         'max is the highest point in the GPX file, not a surveyed summit height. Moving time leaves out stops.</p>')
        self.assertTrue(core.stats_note(self.trip(stats={'distance_km': 20.0, 'moving': '2:00', 'elapsed': '2:40'}, **ride))
                        .endswith(' Moving time leaves out stops; elapsed time includes them.</p>'))
        paddle = dict(activity='other', subtype='SUP', track=True)
        self.assertEqual(core.stats_note(self.trip(**paddle)), '<p class="strip-note">Stats from the GPS recording.</p>')
        self.assertEqual(core.stats_note(self.trip(stats={'moving': '1:00'}, **paddle)),
                         '<p class="strip-note">Stats from the GPS recording. Moving time leaves out stops.</p>')
        self.assertEqual(core.stats_note(self.trip(stats={'distance_km': 5.0, 'moving': '1:00'}, **paddle)),
                         '<p class="strip-note">Stats from the GPS recording. Pace is moving time divided by distance. Moving time '
                         'leaves out stops.</p>')
        # without a track and without both values: nothing to say at all
        for meta in (dict(activity='mtb'), dict(activity='mtb', stats={'distance_km': 20.0}), dict(activity='other', subtype='SUP'),
                     dict(activity='other', subtype='SUP', stats={'moving': '1:00'})):
            self.assertEqual(core.stats_note(self.trip(**meta)), '')

    def test_the_tracks_beta_line_does_not_stand_in_for_the_values(self):
        row = [{'label': 'Track', 'value': TRACK_NOTE}]
        self.assertEqual(core.stats_note(self.trip(activity='mtb', beta=row)), self.note([TRACK_LINE]))
        self.assertEqual(core.stats_note(self.trip(activity='mtb', beta=row, stats={'distance_km': 20.0, 'moving': '2:00'})),
                         self.note([TRACK_LINE, AVG_SPEED]))
        self.assertEqual(core.stats_note(self.trip(activity='other', subtype='SUP', beta=row, track=True)), self.note([RECORDING, TRACK_LINE]))

    def test_other_activities_never_had_the_sentence(self):
        for act in ('hike', 'ski', 'climb'):
            with_, without = self.pair(activity=act, stats=self.STATS['all'])
            self.assertEqual(core.stats_note(with_), self.note([RECORDING, GPS_MAX, MOVING]))
            self.assertEqual(core.stats_note(without), '')     # no recording: nothing said of its moving time either


# ---------------------------------------------------------------- core.render_meta, core.glyph, core.tile

class RenderTests(Fixture):
    """contract-phase4.md 10.3: renders belong to a track. A trip without one (core.has_track) has no maps, no charts
    and no route drawing, whatever rendered/trips/<slug>/ still holds from the days it had a track."""

    META = {'maps': {'map-wide': {'w': 1440, 'h': 640, 'png': 'map-wide.webp'}}, 'charts': {'profile-wide': {'w': 1248, 'h': 160}}}

    def folder(self, t):
        """Point the trip at a render folder in the temp dir that holds a meta.json and the three drawings."""
        folder = os.path.join(self.tmp, '_rendered', t['slug'])
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(self.META, fh)
        for name, (w, h) in core.GLYPH_SIZES.items():
            with open(os.path.join(folder, name + '.svg.html'), 'w', encoding='utf-8') as fh:
                fh.write('<svg class="%s" viewBox="0 0 %d %d"></svg>' % (name, w, h))
        t['rendered'] = folder
        return t

    def assertRendered(self, t, rendered):
        empty = {'maps': {}, 'charts': {}}
        self.assertTrue(os.path.isfile(os.path.join(t['rendered'], 'meta.json')))
        self.assertEqual(core.render_meta(t), self.META if rendered else empty)
        here = 'trips/'
        want = {name: ('<img class="gl gl--%s" src="../%s%s.svg" width="%d" height="%d" alt="" loading="lazy" decoding="async">'
                       % (name, t['url'], name, w, h)) if rendered else '' for name, (w, h) in core.GLYPH_SIZES.items()}
        self.assertEqual(core.tile(t, here), want['tile'])
        self.assertEqual(core.glyph(t, here), want['g112'])
        self.assertEqual(core.glyph(t, here, 'g112'), want['g112'])
        self.assertEqual(core.glyph(t, here, 'g64'), want['g64'])
        self.assertEqual(core.glyph(t, here, 'g112', cls=' glyph'), want['g112'].replace('gl--g112"', 'gl--g112 glyph"'))

    def test_a_single_day_report(self):
        with_, without = self.pair(title='Synthetic Hike', date='2026-06-01', stats=STATS)
        self.assertRendered(self.folder(with_), True)
        self.assertRendered(self.folder(without), False)

    def test_a_multi_day_trip_and_a_journal_follow_their_days(self):
        for kind in ('multi-day', 'series'):
            for tracks, rendered in (((True, True), True), ((False, True), True), ((True, False, False), True), ((False, False), False)):
                with self.subTest(kind=kind, tracks=tracks):
                    self.assertRendered(self.folder(self.tour(tracks, kind=kind)), rendered)

    def test_a_planned_route_and_an_idea(self):
        self.assertRendered(self.folder(self.trip(title='Synthetic Goal', kind='planned', track=True)), True)
        self.assertRendered(self.folder(self.trip(title='Synthetic Idea', kind='planned')), False)

    def test_without_a_folder_nothing_is_rendered_either_way(self):
        with_, without = self.pair(title='Synthetic Hike')
        for t in (with_, without):
            self.assertFalse(os.path.exists(t['rendered']))
            self.assertEqual(core.render_meta(t), {'maps': {}, 'charts': {}})
            self.assertEqual(core.tile(t, 'trips/') + core.glyph(t, 'trips/') + core.glyph(t, 'trips/', 'g64'), '')

    def test_a_drawing_that_is_not_rendered_is_not_drawn(self):
        t = self.folder(self.trip(title='Synthetic Hike', track=True))
        os.remove(os.path.join(t['rendered'], 'g64.svg.html'))
        self.assertEqual(core.glyph(t, 'trips/', 'g64'), '')
        self.assertNotEqual(core.glyph(t, 'trips/', 'g112'), '')
        self.assertNotEqual(core.tile(t, 'trips/'), '')

    def test_the_empty_answer_is_not_shared(self):
        # each call gives a dict of its own: a page that fills it in cannot change what the next trip is told
        t = self.folder(self.trip(title='Synthetic Hike'))
        first = core.render_meta(t)
        first['maps']['map-wide'] = {}
        self.assertEqual(core.render_meta(t), {'maps': {}, 'charts': {}})

    def test_what_reads_the_meta_sees_no_chart_and_no_map(self):
        # the summary's closing fact and the report's chart follow from render_meta: a trip without a track has neither
        from sitegen.pages import report
        without = self.folder(self.trip(title='Synthetic Hike', date='2026-06-01', region=REGION, stats=STATS))
        self.assertEqual(report.has_chart(core.render_meta(without)), '')
        self.assertEqual(report.profile_section(without, without['url'], core.render_meta(without)), '')
        self.assertEqual(core.map_preloads(without, without['url'], [('map-wide', 'wide')], without['url'] + 'map/'), '')
        self.assertEqual(core.map_block(without, without['url'], [('map-wide', 'wide')], without['url'] + 'map/', 'm'), '<div class="map"></div>')
        with_ = self.folder(self.trip(title='Synthetic Hike', date='2026-06-01', region=REGION, stats=STATS, track=True))
        self.assertEqual(report.has_chart(core.render_meta(with_)), 'profile')
        self.assertIn('map-wide.webp', core.map_preloads(with_, with_['url'], [('map-wide', 'wide')], with_['url'] + 'map/'))


# ---------------------------------------------------------------- core.photo

class PhotoSizeTests(Fixture):
    """core.photo writes width / height and the srcset only when both w and h are recorded: one of the two alone says
    nothing about the photo's shape (and used to raise a TypeError). Every photo here has its 800 px .sm copy on disk."""

    HERE = 'trips/x/'

    def photo(self, w=None, h=None, sm=True):
        entry = {'file': 'photos/01.webp', 'alt': 'Synthetic photo', 'sm': sm}
        if w is not None:
            entry['w'] = w
        if h is not None:
            entry['h'] = h
        t = self.trip(title='Synthetic Photos', track=True, photos=[entry])
        p = t['photos'][0]
        self.assertEqual((p['w'], p['h'], p['sm']), (w, h, 'photos/01.sm.webp' if sm else None))
        return t, p

    def img(self, t, p, **kw):
        fig = Doc(core.photo(t, p, t['url'], **kw)).find('figure')
        self.assertEqual(fig.classes, ['photo'])
        imgs = fig.find_all('img')
        self.assertEqual(len(imgs), 1)
        return imgs[0]

    def assertUnsized(self, t, p):
        img = self.img(t, p)
        self.assertEqual(sorted(img.attrs), ['alt', 'decoding', 'loading', 'src'])
        self.assertEqual(img['src'], '../../%sphotos/01.webp' % t['url'])
        self.assertEqual(core.photo(t, p, t['url']),
                         '<figure class="photo"><img src="../../%sphotos/01.webp" alt="Synthetic photo" decoding="async" loading="lazy"></figure>'
                         % t['url'])
        for needle in ('srcset', 'sizes', 'width', 'height', '.sm.'):
            self.assertNotIn(needle, core.photo(t, p, t['url']))

    def test_both_recorded(self):
        t, p = self.photo(*LANDSCAPE)
        img = self.img(t, p)
        base = '../../%sphotos/' % t['url']
        self.assertEqual((img['width'], img['height']), ('1600', '1200'))
        self.assertEqual(img['srcset'], '%s01.sm.webp 800w, %s01.webp 1600w' % (base, base))
        self.assertEqual(img['sizes'], '(min-width: 1200px) 1248px, (min-width: 560px) 100vw, 55vw')
        self.assertEqual(core.photo(t, p, t['url']),
                         '<figure class="photo"><img src="%s01.webp" srcset="%s01.sm.webp 800w, %s01.webp 1600w" '
                         'sizes="(min-width: 1200px) 1248px, (min-width: 560px) 100vw, 55vw" width="1600" height="1200" '
                         'alt="Synthetic photo" decoding="async" loading="lazy"></figure>' % (base, base, base))
        t, p = self.photo(*PORTRAIT)
        img = self.img(t, p, sizes='50vw')
        base = '../../%sphotos/' % t['url']
        self.assertEqual((img['width'], img['height'], img['sizes']), ('1200', '1600', '50vw'))
        self.assertEqual(img['srcset'], '%s01.sm.webp 600w, %s01.webp 1200w' % (base, base))

    def test_the_width_alone(self):
        self.assertUnsized(*self.photo(w=1600))

    def test_the_height_alone(self):
        self.assertUnsized(*self.photo(h=1200))

    def test_neither(self):
        self.assertUnsized(*self.photo())

    def test_a_zero_is_not_a_size(self):
        self.assertUnsized(*self.photo(w=1600, h=0))
        self.assertUnsized(*self.photo(w=0, h=1200))

    def test_both_recorded_without_the_small_copy(self):
        # the size is written, and there is nothing to choose between
        t, p = self.photo(*LANDSCAPE, sm=False)
        img = self.img(t, p)
        self.assertEqual(sorted(img.attrs), ['alt', 'decoding', 'height', 'loading', 'src', 'width'])
        self.assertEqual((img['width'], img['height']), ('1600', '1200'))
        for w, h in ((1600, None), (None, 1200), (None, None)):
            t, p = self.photo(w, h, sm=False)
            self.assertEqual(sorted(self.img(t, p).attrs), ['alt', 'decoding', 'loading', 'src'])

    def test_the_other_attributes_do_not_depend_on_the_size(self):
        for w, h in (LANDSCAPE, (1600, None), (None, 1200), (None, None)):
            with self.subTest(w=w, h=h):
                t, p = self.photo(w, h)
                img = self.img(t, p, eager=True)
                self.assertNotIn('loading', img)
                self.assertEqual((img['alt'], img['decoding']), ('Synthetic photo', 'async'))
                self.assertEqual(Doc(core.photo(t, p, t['url'], cls='sec-feat-photo')).find('figure').classes, ['photo', 'sec-feat-photo'])
                p = dict(p, caption='Synthetic caption')
                self.assertEqual(Doc(core.photo(t, p, t['url'])).find('figcaption').text(), 'Synthetic caption')
                self.assertIsNone(Doc(core.photo(t, p, t['url'], caption=False)).find('figcaption'))

    def test_a_report_with_a_half_measured_photo_builds(self):
        # where the TypeError came from: the gallery, the featured block and the aside all go through core.photo
        from sitegen.pages import report
        report._TITLE_COUNTS.clear()
        self.addCleanup(report._TITLE_COUNTS.clear)
        for w, h in ((1600, None), (None, 1200)):
            with self.subTest(w=w, h=h):
                entries = [{'file': 'photos/01.webp', 'alt': 'Synthetic photo one', 'sm': True},
                           {'file': 'photos/02.webp', 'alt': 'Synthetic photo two', 'sm': True}]
                for e in entries:
                    e.update({k: v for k, v in (('w', w), ('h', h)) if v is not None})
                t = self.trip(title='Synthetic Half Measured', date='2026-06-01', region=REGION, track=True, photos=entries)
                state = (dict(core._TRIPS_BY_URL), list(core._OTHER_SUBS), core._HAS_PCT[0], core._SITE_SHARE[0])
                try:
                    # the page asks whether its region is on map/ (core.region_map_href): from a stand-in for the site
                    # meta, so that the checkout's own rendered/site/meta.json is neither read nor left in core's cache
                    with mock.patch.object(core, '_SITE_META', [{'maps': {}, 'regions': [], 'all_regions': []}]):
                        html_ = report.page(t, helpers.make_site([t])).html
                finally:
                    core._TRIPS_BY_URL.clear()
                    core._TRIPS_BY_URL.update(state[0])
                    core._OTHER_SUBS[:] = state[1]
                    core._HAS_PCT[0], core._SITE_SHARE[0] = state[2], state[3]
                # Phase 10 (report-02): the first leads the page (a photo without both dimensions counts as a landscape)
                doc = Doc(html_)
                imgs = doc.by_id('hero').find_all('img') + doc.by_id('photos').find_all('img')
                self.assertEqual([i['src'] for i in imgs], ['../../%sphotos/01.webp' % t['url'], '../../%sphotos/02.webp' % t['url']])
                for i in imgs:
                    self.assertNotIn('width', i)
                    self.assertNotIn('height', i)
                    self.assertNotIn('srcset', i)


# ---------------------------------------------------------------- the beta's Track row, the empty section

class BetaTrackRowTests(Fixture):
    """The beta row labelled Track is printed by the stats footnote, so the Beta block leaves it out. A report without a
    track and without stats has no strip and no footnote: the row then stays in the block, or it would be nowhere."""

    def setUp(self):
        Fixture.setUp(self)
        import importlib
        self.report = importlib.import_module('sitegen.pages.report')
        self.beta = [{'label': 'Track', 'value': TRACK_NOTE}, {'label': 'Snow', 'value': 'Firm'}]

    def labels(self, t, **kw):
        return [r['label'] for r in self.report.beta_rows(t, **kw)]

    def test_the_row_is_left_out_where_the_footnote_prints_it(self):
        t = self.trip(track=True, beta=self.beta)
        self.assertEqual(self.labels(t), ['Snow'])
        self.assertEqual(self.labels(t, noted=True), ['Snow'])
        self.assertNotIn('Synthetic recorder', self.report.beta_list(t))

    def test_the_row_stays_when_the_page_has_no_footnote(self):
        t = self.trip(track=False, beta=self.beta)
        self.assertEqual(self.labels(t, noted=False), ['Track', 'Snow'])
        block = self.report.beta_list(t, noted=False)
        self.assertIn('<dt>Track</dt>', block)
        self.assertIn('Synthetic recorder &amp; one synthetic gap.', block)

    def test_pitches_is_still_left_out_on_a_climb_either_way(self):
        t = self.trip(track=False, activity='climb', beta=[{'label': 'Pitches', 'value': '5'}] + self.beta)
        self.assertEqual(self.labels(t, noted=False), ['Track', 'Snow'])
        self.assertEqual(self.labels(t), ['Snow'])

    def page(self, t):
        """The trip's built page, in a site that holds only this trip."""
        build = sys.modules.get('build') or __import__('build')
        site = build.site_of([t])
        site['featured'] = []
        held = {name: (dict(v) if isinstance(v, dict) else list(v)) for name, v in
                ((n, getattr(core, n)) for n in ('_TRIPS_BY_URL', '_OTHER_SUBS', '_HAS_PCT', '_SITE_SHARE')) if isinstance(v, (dict, list))}

        def put_back():
            for name, was in held.items():
                now = getattr(core, name)
                if isinstance(now, dict):
                    now.clear()
                    now.update(was)
                else:
                    now[:] = was
        self.addCleanup(put_back)
        core.register_site(site)
        getattr(self.report, '_TITLE_COUNTS', {}).clear()
        return self.report.page(t, site).html

    def test_a_page_without_a_strip_shows_the_row_in_its_beta_block_once(self):
        t = self.trip(track=False, beta=self.beta, body='Synthetic words about a synthetic day. ' * 5)
        html = self.page(t)
        self.assertNotIn('id="stats"', html)
        self.assertIn('id="beta"', html)
        self.assertEqual(html.count('Synthetic recorder &amp; one synthetic gap'), 1)

    def test_a_page_with_a_strip_prints_it_in_the_footnote_and_not_in_the_block(self):
        for track in (True, False):
            with self.subTest(track=track):
                t = self.trip(track=track, beta=self.beta, stats=STATS)
                html = self.page(t)
                self.assertIn('id="stats"', html)
                self.assertIn(TRACK_LINE, html)
                self.assertNotIn('<dt>Track</dt>', html)


class EmptySectionTests(unittest.TestCase):

    def test_a_section_with_no_report_promises_no_track(self):
        import importlib
        section = importlib.import_module('sitegen.pages.section')
        text = section.description('ski', [])
        self.assertNotIn('GPX', text)
        self.assertNotIn('map', text)
        self.assertTrue(text.endswith('.'))


class DayCountTagTests(Fixture):

    def test_one_day_is_a_day(self):
        self.assertIn('Multi-day · 1 day<', core.trip_tags(self.tour((True,))))
        self.assertNotIn('1 days', core.trip_tags(self.tour((True,))))

    def test_more_are_days_as_before(self):
        for n in (2, 5):
            self.assertIn('Multi-day · %d days<' % n, core.trip_tags(self.tour((True,) * n)))



# ---------------------------------------------------------------- Phase 9 (copy-01): the word after 'via'

class SourceWordTests(Fixture):
    """content.stats_source: a source: line from content.SOURCES names the service; else 'Strava' when index.md carries a
    strava_id or every day file does (content.has_strava); else no service at all. The same rule for the single-day
    note (core.stats_note), the multi-day note (multiday.stats_note) and the PCT's series note (series.strip)."""

    def setUp(self):
        super().setUp()
        import importlib
        self.multiday = importlib.import_module('sitegen.pages.multiday')
        self.series = importlib.import_module('sitegen.pages.series')

    def first(self, t):
        return core.stats_note(t).split('. ')[0].replace('<p class="strip-note">', '') + '.'

    def test_single_day(self):
        ride = dict(activity='mtb', track=True)
        self.assertEqual(self.first(self.trip(strava_id=101, **ride)), 'Stats from the GPS recording via Strava.')
        self.assertEqual(self.first(self.trip(**ride)), 'Stats from the GPS recording.')
        for name in ('Strava', 'Garmin', 'CalTopo'):
            with self.subTest(source=name):
                self.assertEqual(self.first(self.trip(source=name, **ride)), 'Stats from the GPS recording via %s.' % name)
        self.assertEqual(self.first(self.trip(source='Garmin', strava_id=101, **ride)), 'Stats from the GPS recording via Garmin.')
        # a name outside the list (the validator's error) names nothing on the page
        self.assertEqual(self.first(self.trip(source='Suunto', **ride)), 'Stats from the GPS recording.')
        self.assertEqual(self.first(self.trip(source='Suunto', strava_id=101, **ride)), 'Stats from the GPS recording via Strava.')
        # no track: no sentence about a recording, whatever the lines say
        self.assertNotIn('GPS recording', core.stats_note(self.trip(activity='mtb', strava_id=101, source='Garmin')))

    def days(self, ids, kind='multi-day', **meta):
        t = self.tour((True,) * len(ids), kind=kind, **meta)
        for d, sid in zip(t['days'], ids):
            d['strava'] = sid is not None        # what load_trip reads from each day file's strava_id line
        return t

    def test_day_files(self):
        from content import has_strava
        loaded = self.trip(kind='multi-day', title='Synthetic Tour', days=[{'date': '2026-03-10', 'strava_id': 7},
                                                                            {'date': '2026-03-11', 'strava_id': 8}])
        self.assertTrue(has_strava(loaded))
        partial = self.trip(kind='multi-day', title='Synthetic Tour', days=[{'date': '2026-03-10', 'strava_id': 7},
                                                                             {'date': '2026-03-11'}])
        self.assertFalse(has_strava(partial))
        note = self.multiday.stats_note
        self.assertIn('Stats from the GPS recordings via Strava. GPS max', note(loaded))
        self.assertIn('Stats from the GPS recordings. GPS max', note(partial))
        self.assertIn('Stats from the GPS recordings via CalTopo. GPS max', note(self.days([None, None], source='CalTopo')))
        self.assertIn('class="strip-note rep-note-ph"', note(loaded, 'rep-note-ph'))

    def test_series(self):
        self.assertIn('Stats from the GPS recordings via Strava. Distance and gain',
                      self.series.strip(self.days([1, 2, 3], kind='series')))
        self.assertIn('Stats from the GPS recordings. Distance and gain', self.series.strip(self.days([1, None], kind='series')))
        self.assertIn('Stats from the GPS recordings via Garmin. Distance and gain',
                      self.series.strip(self.days([None], kind='series', source='Garmin')))


if __name__ == '__main__':
    unittest.main()
