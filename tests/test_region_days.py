"""A journal's days on the region maps: `region_days` in a journal's index.md (content._region_days).

A journal (kind: series) is filed under one region of its own and walks through many. `region_days` says which of its
days lie in which region:

    region_days:
      Synthetic Range: 1-2, 4

Then (a) tools/render.py draws those days on that region's map, which stays framed by the region's own trips (a day
is drawn where it crosses the map and cut off at its edge), with a pin for each run of consecutive days that starts
inside the region, linking to that day on the journal page, and records the days in the map's entry of
rendered/site/meta.json under 'journals' ('trips' stays the region's own reports); (b) the region's list, on the Map page and on the region's page,
names the journal in one row that carries the journal's key, as its lines on the map do; no count of reports includes
it; (c) the validator refuses a region that no report is filed under and warns when a region map was drawn with other
days than the block lists.

Nothing here draws or fetches: the renderer tests use test_render_goals' fixture (render_map, fetch_osm and
optimize_images stubbed, render.OUT in a temp dir), the page tests test_archive_page's synthetic site, and the
validator tests a temp tree of their own. Every slug, name and sentence is made up.
"""
import datetime
import importlib
import json
import os
import sys
import tempfile
import unittest

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
            ({'Synthetic Range': {'a': 1}}, "region_days: Synthetic Range must list days such as 68-75, 147-153, got {'a': 1}"),
            ({'': '1'}, 'region_days has an entry without a region name'),
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

    def test_the_parts_are_the_listed_days_that_have_a_track(self):
        j = self.journal({REGION: '1-4', 'Synthetic Coast': '5'}, tracks=(True, True, False, True, True))
        parts = self.render.journal_parts(self.walks() + [j])
        self.assertEqual(sorted(parts), ['Synthetic Coast', REGION])
        self.assertEqual([(t['slug'], [d['label'] for d in days]) for t, days in parts[REGION]], [(JOURNAL, ['1', '2', '4'])])
        self.assertEqual(self.render.journal_parts(self.walks()), {})
        # a region whose listed days hold no track has no part
        k = self.journal({REGION: '3'}, tracks=(True, True, False, True, True), slug='syn-d-other')
        self.assertEqual(self.render.journal_parts([k]), {})

    def test_days_that_follow_one_another_are_one_run(self):
        j = self.journal({REGION: '1-2, 4-5'})
        days = j['region_days'][0]['days']
        self.assertEqual([[d['label'] for d in run] for run in self.render.day_runs(j, days)], [['1', '2'], ['4', '5']])
        self.assertEqual([[d['label'] for d in run] for run in self.render.day_runs(j, j['days'])], [['1', '2', '3', '4', '5']])
        self.assertEqual(self.render.day_runs(j, []), [])

    def test_without_a_frame_a_run_gets_its_pin_at_the_start_of_its_first_day(self):
        j = self.journal({REGION: '1-2, 4-5'})
        pins = self.render.journal_pins(j, j['region_days'][0]['days'])
        self.assertEqual([(p['key'], p['title'], p['href'], p['cat']) for p in pins],
                         [(JOURNAL, 'Synthetic Journal, Day 1', '@@ROOT@@trips/%s/#day-1' % JOURNAL, j['cat']),
                          (JOURNAL, 'Synthetic Journal, Day 4', '@@ROOT@@trips/%s/#day-4' % JOURNAL, j['cat'])])
        self.assertEqual([(round(p['lat'], 3), round(p['lon'], 3)) for p in pins], [(38.895, -120.1), (39.1, -120.1)])

    def test_with_a_frame_only_a_run_that_starts_in_the_region_has_a_pin(self):
        # a pin marks a start. Day 2 starts inside the walks' box; day 1 starts south of it and walks in; days 4 and 5
        # are far to the north
        j = self.journal({REGION: '2, 4-5'})
        pins = self.render.journal_pins(j, j['region_days'][0]['days'], OWN_BOX)
        self.assertEqual([(p['title'], p['href']) for p in pins],
                         [('Synthetic Journal, Day 2', '@@ROOT@@trips/%s/#day-2' % JOURNAL)])
        self.assertEqual((round(pins[0]['lat'], 3), round(pins[0]['lon'], 3)), (38.906, -120.1))
        # a run that comes in from outside has none, however much of it lies inside
        k = self.journal({REGION: '1-2'}, slug='syn-d-through')
        self.assertEqual(self.render.journal_pins(k, k['region_days'][0]['days'], OWN_BOX), [])
        self.assertEqual(len(self.render.journal_pins(k, k['region_days'][0]['days'])), 1)      # without a frame it has its pin

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
            self.assertEqual(meta['maps'][name]['journals'], [{'slug': JOURNAL, 'days': ['001', '002', '004']}])
        self.assertEqual(len(self.maps), 2)
        for spec in self.maps:
            mine = [tr for tr in spec['tracks'] if tr['key'] == JOURNAL]
            self.assertEqual(len(mine), 3)                                                   # one line per day, never joined
            self.assertTrue(all(tr['style'] == 'cat' and tr['cat'] == j['cat'] and not tr['thin'] for tr in mine))
            self.assertEqual(len([tr for tr in spec['tracks'] if tr['key'] != JOURNAL]), 3)
            # the run of days 1 and 2 walks in from outside and day 4 lies outside: lines, and no pin
            self.assertEqual([p for p in spec['pins'] if p['key'] == JOURNAL], [])
            self.assertEqual(sorted(p['key'] for p in spec['pins'] if p['key'] != JOURNAL), ['walk-1', 'walk-2', 'walk-3'])
        # a run that starts inside the region has its pin
        del self.maps[:]
        k = self.journal({REGION: '2-3'}, slug='syn-d-inside')
        self.assertIs(self.render.render_site(trips[:3] + [k], force=True), True)
        for spec in self.maps:
            self.assertEqual([p['href'] for p in spec['pins'] if p['key'] == 'syn-d-inside'], ['@@ROOT@@trips/syn-d-inside/#day-2'])

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
            self.assertEqual(sorted(entry), ['base', 'clusters', 'h', 'png', 'region', 'trips', 'w'])
        self.assertTrue(all(tr['key'] != JOURNAL for spec in self.maps for tr in spec['tracks']))

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
        self.assertIs(self.render.render_site(walks + [self.journal({REGION: '1-2'})], force=True), True)
        self.assertIs(self.render.render_site(walks + [self.journal({REGION: '1-2'})]), False)       # same inputs: nothing is redrawn
        self.assertIs(self.render.render_site(walks + [self.journal({REGION: '1-3'})]), True)
        self.assertEqual(self.meta()['maps']['region-%s-desktop' % content.slugify(REGION)]['journals'],
                         [{'slug': JOURNAL, 'days': ['001', '002', '003']}])
        self.assertIs(self.render.render_site(walks + [self.journal(None)]), True)                    # and so does taking them out
        self.assertNotIn('journals', self.meta()['maps']['region-%s-desktop' % content.slugify(REGION)])


# ---------------------------------------------------------------- the region's list (Map page and region page)

RANGE, COAST = MAPPED
PAGE_JOURNAL = 'syn-m-journal'


class ListRowTests(MapPageFixture):
    REGION_PAGES = True

    def setUp(self):
        super().setUp()
        # the fixture's journal again, now a mountain-bike journal (an activity no report of the Range has) of four days,
        # three of them in the Synthetic Range
        journal(self.trips_dir, slug=PAGE_JOURNAL, labels=('1', '2', '3', '4'), stats={'1': 10.0, '2': 12.5, '3': 7.0},
                activity='mtb', region_days={RANGE: '2-3, 1'})
        self.use(MAPPED, MAPPED + LISTED, featured=('syn-m-coast-a',))

    def drawn(self, days=('001', '002', '003')):
        """The site meta as the renderer leaves it once it has drawn the journal's days on the Range's maps; the page is
        built again."""
        for size in ('desktop', 'phone'):
            self.meta['maps']['region-%s-%s' % (SLUG[RANGE], size)]['journals'] = [{'slug': PAGE_JOURNAL, 'days': list(days)}]
        with open(os.path.join(self.site_dir, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(self.meta, fh)
        self.page = self.archive.build(self.site)[0]
        self.doc = Doc(self.page.html)
        self.main = self.doc.by_id('main')

    def panel(self, name):
        return self.one('region-' + SLUG[name])

    def journal_rows(self, node):
        return [li for li in node.find_all('li') if 'arc-row--journal' in li.classes]

    def test_the_parts_are_the_published_journals_days_in_that_region(self):
        parts = self.archive.journal_parts(self.site, RANGE)
        self.assertEqual([(t['slug'], [d['label'] for d in days]) for t, days in parts], [(PAGE_JOURNAL, ['1', '2', '3'])])
        self.assertEqual(self.archive.journal_parts(self.site, COAST), [])
        self.assertEqual(self.archive.journal_parts(self.site, 'Synthetic Trail'), [])     # its own region is no part
        self.assertEqual(self.archive.journal_parts(None, RANGE), [])
        self.assertEqual(self.archive.journal_parts({'published': []}, RANGE), [])

    def test_the_regions_list_names_the_journal_in_one_row(self):
        rows = self.journal_rows(self.panel(RANGE))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['data-key'], PAGE_JOURNAL)               # the key its lines and pins on the map carry
        a = row.find('a')
        self.assertEqual(a['href'], '../trips/%s/#day-1' % PAGE_JOURNAL)     # the first of its days here, on the journal page
        self.assertEqual(a['data-act'], 'mtb')
        self.assertEqual(row.find('span', cls='arc-row-t').text(), 'Synthetic Journal')
        text = helpers.plain_text(row.find('span', cls='arc-row-m').text())
        self.assertIn('3 JOURNAL DAYS', text.replace(' ', ' '))
        mi, km = core_dist(29.5)
        self.assertIn(mi + ' MI', text.replace(' ', ' '))
        self.assertIn(km + ' KM', text.replace(' ', ' '))
        self.assertEqual(self.journal_rows(self.panel(COAST)), [])
        self.assertEqual(len(self.journal_rows(self.main)), 1)        # and nowhere else on the page

    def test_it_is_no_report_of_the_region(self):
        panel = self.panel(RANGE)
        own = [li['data-key'] for li in panel.find_all('li') if 'arc-row' in li.classes and 'arc-row--journal' not in li.classes]
        self.assertEqual(sorted(own), ['syn-m-range-a', 'syn-m-range-b', 'syn-m-range-tour'])
        count = helpers.plain_text(panel.find('div', cls='arc-inreg-h').find('span', cls='t-mono-s').text()).replace(' ', ' ')
        self.assertIn('3 REPORTS', count)
        self.assertNotIn('4 REPORTS', count)
        self.assertNotIn('JOURNAL', count)
        tab = self.one('arc-tab-' + SLUG[RANGE])
        self.assertIn('3', tab.find('span', cls='arc-tab-n').text())

    def test_it_stands_where_its_last_day_here_puts_it(self):
        # newest first: the journal's last day in the Range is 2024-05-03, older than the Range's three reports
        keys = [li['data-key'] for li in self.panel(RANGE).find_all('li') if 'arc-row' in li.classes]
        self.assertEqual(keys, ['syn-m-range-a', 'syn-m-range-b', 'syn-m-range-tour', PAGE_JOURNAL])
        rows = self.archive._rows_with_journals
        a, b, c = (self.by[s] for s in ('syn-m-range-a', 'syn-m-range-b', 'syn-m-range-tour'))
        j = self.by[PAGE_JOURNAL]

        def at(day):
            return [dict(d, date=day) for d in j['days'][:1]]
        order = lambda day: [t['slug'] for t, _d in rows([a, b, c], [(j, at(day))])]   # noqa: E731
        self.assertEqual(order(datetime.date(2026, 6, 1)), [PAGE_JOURNAL, 'syn-m-range-a', 'syn-m-range-b', 'syn-m-range-tour'])
        self.assertEqual(order(datetime.date(2025, 9, 1)), ['syn-m-range-a', PAGE_JOURNAL, 'syn-m-range-b', 'syn-m-range-tour'])
        self.assertEqual(order(datetime.date(2020, 1, 1)), ['syn-m-range-a', 'syn-m-range-b', 'syn-m-range-tour', PAGE_JOURNAL])
        goal = self.by['syn-m-desert-goal']
        self.assertEqual([t['slug'] for t, _d in rows([a, goal], [(j, at(datetime.date(2020, 1, 1)))])],
                         ['syn-m-range-a', PAGE_JOURNAL, 'syn-m-desert-goal'])            # before the planned routes

    def test_the_legend_names_its_activity_once_the_map_draws_it(self):
        def activities(panel):
            return [li.text() for li in panel.find('ul', attrs={'aria-label': 'Activities'}).find_all('li')]
        before = activities(self.panel(RANGE))
        self.assertNotIn('Mountain Biking', before)        # the map was not drawn with the journal's days yet
        self.drawn()
        self.assertEqual(sorted(activities(self.panel(RANGE))), sorted(before + ['Mountain Biking']))
        # a map entry that names another journal, or is not a list, adds nothing
        for other in ([{'slug': 'syn-m-no-such-journal', 'days': ['001']}], 'nope', [None]):
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
        self.assertEqual(with_site.count('arc-row--journal'), 1)
        # the row is the only difference
        row = with_site[with_site.index('<li class="arc-row arc-row--journal'):]
        row = row[:row.index('</li>') + len('</li>')]
        self.assertEqual(with_site.replace(row, ''), bare)

    def test_the_regions_own_page_has_the_row_too(self):
        region = load_module(self, 'sitegen.pages.region')
        pages = {p.url: p for p in region.build(self.site)}
        page = pages['regions/%s/' % SLUG[RANGE]]
        doc = Doc(page.html)
        rows = [li for li in doc.by_id('map').find_all('li') if 'arc-row--journal' in li.classes]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].find('a')['href'], '../../trips/%s/#day-1' % PAGE_JOURNAL)
        other = Doc(pages['regions/%s/' % SLUG[COAST]].html)
        self.assertEqual([li for li in other.find_all('li') if 'arc-row--journal' in li.classes], [])
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
