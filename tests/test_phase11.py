"""Phase 11 on the journal, the photo viewer's markup and the full-screen map (docs/claude-code-website-prompt-2.md,
Phase 11), on synthetic trips only (the journal fixture of tests/test_series_page.py, the report fixture of
tests/test_report_page.py; nothing under content/ or rendered/ is read):

  report-18    a written day's photos are justified rows in the write-up's measure, from the .th or .sm copy only; a
               track-only day keeps the square sheet
  features-07  each day row's 'Recorded so far' is the running sum of the day files' distances; a gap adds nothing
  benchmark-10 'WRITE-UP 2 OF 3' under a written entry; month heads and By-month rows say 'N MI SO FAR', the last one
               the strip's total
  a11y-07      the month bar's empty months are styled, never disabled (series.css; the script: series_js_harness.js)
  resil-13     the full-screen page marks the route's start (#route-start) at the first point of the first route path
               that is not faded, the dashed ascent's on a ski map; links to the page name it exactly when it is there
  gap1-02      'Open the full map' after the key rows
  maps-10      the full-screen bar's scale (both units, drawn at the page's size) and 'NOT FOR NAVIGATION'

The viewer's and the share sheet's behaviour: tests/viewer_js_harness.js; the cascade of 'Open the full map' and the
viewer's description: tests/test_a11y_static.py."""
import importlib
import json
import os
import re
import unittest
from unittest import mock

import helpers
from helpers import Doc, photo, LANDSCAPE, PORTRAIT
import test_report_page as rp
import test_series_page as sp

from sitegen import core

tearDownModule = helpers.no_region_pages_left


def css(name):
    with open(os.path.join(rp.ROOT, 'assets', 'css', name), encoding='utf-8') as fh:
        return fh.read()


def km_days():
    """The six-day journal with distances: 10, 12.5, (none), 8, 4.25 and 20 km; labels 1, 2, 3, 5.2, 6, 12 (so days 4-5
    and 7-11 are gaps); written: 2, 5.2, 12. Day 2's photo has its .sm copy (and, in the fixture, its .th copy)."""
    days = sp.journal_days()
    for d, km in zip(days, (10.0, 12.5, None, 8.0, 4.25, 20.0)):
        if km is not None:
            d['stats'] = {'distance_km': km}
    days[1]['photos'] = [photo('photos/d002-01.webp', LANDSCAPE, alt='', sm=True),
                         photo('photos/d002-02.webp', PORTRAIT, alt='Synthetic tent', sm=True)]
    return days


class JournalFixture(sp.JournalFixture):

    def setUp(self):
        super().setUp()
        self.synthetic(sp.SLUG)
        folder = helpers.make_trip(self.tmp, sp.SLUG, days=km_days(), title='Synthetic Journal', kind='series',
                                   date='2024-04-22', end_date='2024-05-02', place='Start to Finish', region='Synthetic Range')
        helpers.touch(os.path.join(folder, 'photos', 'd002-01.th.webp'))      # the card-size copy of the first photo only
        self.t = helpers.load(self.tmp, sp.SLUG)
        self.main = Doc(self.series.page(self.t, helpers.make_site([self.t])).html).by_id('main')

    def body(self, anchor):
        return self.main.by_id(anchor).find('div', cls='ser-body')


# ---------------------------------------------------------------- report-18

class DayPhotoTests(JournalFixture):

    def test_a_written_day_shows_its_photos_as_justified_rows(self):
        rows = self.body('day-2').find('div', cls='jrows')
        self.assertIsNotNone(rows)
        self.assertEqual([a.classes[:2] for a in rows.find_all('a', cls='jph')], [['jph', 'jph--l'], ['jph', 'jph--p']])
        self.assertIsNone(self.body('day-2').find('ul', cls='ser-phs'))
        # a track-only day keeps the square contact sheet
        self.assertEqual([el.classes[-1] for el in self.body('day-1').elements()], ['ser-phs'])

    def test_they_take_the_th_or_sm_copy_never_the_full_file(self):
        imgs = self.body('day-2').find_all('img')
        first, second = imgs
        self.assertTrue(first['src'].endswith('photos/d002-01.sm.webp'), first['src'])
        cands = [c.strip().split(' ')[0] for c in first['srcset'].split(',')]
        self.assertEqual([os.path.basename(c) for c in cands], ['d002-01.th.webp', 'd002-01.sm.webp'])
        self.assertEqual([os.path.basename(c.strip().split(' ')[0]) for c in second['srcset'].split(',')], ['d002-02.sm.webp'])
        for img in imgs:
            self.assertNotRegex(img['srcset'], r'd002-0\d\.webp ')
        # the link still opens the full file (the viewer adds it back to the set: base.js)
        self.assertEqual([os.path.basename(a['href']) for a in self.body('day-2').find_all('a', cls='jph')],
                         ['d002-01.webp', 'd002-02.webp'])

    def test_a_photo_without_alt_is_named_by_its_day(self):
        a = self.body('day-2').find_all('a', cls='jph')[0]
        self.assertEqual(a['aria-label'], 'Day 2, photo 1 of 2, full size')

    def test_the_rows_match_the_write_ups_measure(self):
        self.assertEqual(self.series.DAY_ROWS, dict(per_row=3, col=620, jmax=400, jmin=200, gap=12, narrow=True))
        self.assertIn('.ser-body .jrows { --jmax: 400px; --jmin: 200px; --jgap: 12px; max-width: 620px;', css('pages/series.css'))
        # the sizes attribute declares those numbers from 760 px (the column is 620 px or a little less there), not a share
        # of the report's 100vw - 80px column: a landscape and a portrait in one 620 px row with a 12 px gap
        imgs = self.body('day-2').find_all('img')
        ws = [int(re.match(r'\(min-width: 760px\) (\d+)px, ', img['sizes']).group(1)) for img in imgs]
        self.assertEqual(sum(ws), 620 - 12)
        for img in imgs:
            self.assertNotIn('100vw - 80px', img['sizes'])


# ---------------------------------------------------------------- features-07 and benchmark-10

class SoFarTests(JournalFixture):

    def test_each_row_says_the_distance_recorded_so_far(self):
        # both units through core.U ('22.5 mi' | '36.2 km'), then ' so far' (hidden from 1000 px, under the column head)
        want = {'day-1': 10.0, 'day-2': 22.5, 'day-3': 22.5, 'day-5-2': 30.5, 'day-6': 34.75, 'day-12': 54.75}
        days = dict((self.series.day_anchor(d), d) for d in self.t['days'])
        for anchor, km in want.items():
            with self.subTest(anchor):
                cell = self.main.by_id(anchor).find('div', cls='ser-st-f')
                self.assertEqual(cell.find('dt').text(), 'Recorded')
                mi, k = core.dist_vals(km)
                self.assertIn('<dd>%s<span class="unit"> so far</span></dd>' % core.U(mi, k, ' mi', ' km'),
                              self.series.stats_dl(days[anchor], km))

    def test_the_page_carries_the_running_sum_through_its_months(self):
        # the figure in each row as the page prints it (month_section hands day_article its day's sum)
        for anchor, km in (('day-2', 22.5), ('day-12', 54.75)):
            mi, k = core.dist_vals(km)
            dd = self.main.by_id(anchor).find('div', cls='ser-st-f').find('dd')
            self.assertEqual(dd.text().replace('\u00a0', ' '), '%s mi%s km so far' % (mi, k))

    def test_a_gap_and_a_day_without_distance_add_nothing(self):
        far = self.series.so_far(self.t)
        ids = [d['id'] for d in self.t['days']]
        self.assertEqual([far[i] for i in ids], [10.0, 22.5, 22.5, 30.5, 34.75, 54.75])
        self.assertEqual(len(self.main.find_all('p', cls='ser-gap')), 2)          # days 4-5 and 7-11, between the rows
        self.assertEqual(far[ids[-1]], self.t['stats']['distance_km'])

    def test_the_column_head_says_recorded_so_far(self):
        heads = [s.text() for s in self.main.find('div', cls='ser-cols').elements()]
        self.assertIn('Recorded so far', heads)
        self.assertLess(heads.index('Moving'), heads.index('Recorded so far'))
        self.assertLess(heads.index('Recorded so far'), heads.index('Elevation'))

    def test_month_heads_and_by_month_rows_say_how_far_so_far(self):
        def far_text(km):
            mi, k = core.dist_vals(km)
            return '%s MI SO FAR' % mi
        heads = [m.text().replace('\u00a0', ' ') for m in self.main.find_all('p', cls='ser-mh-m')]
        self.assertEqual(len(heads), 2)
        self.assertIn(far_text(30.5), heads[0])                                  # April: days 1, 2, 3 and 5.2
        self.assertIn(far_text(54.75), heads[1])                                 # May: through day 12, the total
        rows = [s.text().replace('\u00a0', ' ') for s in self.main.find_all('span', cls='ser-mi-s')]
        self.assertIn(far_text(30.5), rows[0])
        self.assertIn(far_text(54.75), rows[-1])
        strip_total = core.dist_vals(self.t['stats']['distance_km'])[0]
        self.assertIn('%s MI SO FAR' % strip_total, rows[-1])

    def test_a_written_entry_says_its_place_among_the_write_ups(self):
        for anchor, n in (('day-2', 1), ('day-5-2', 2), ('day-12', 3)):
            with self.subTest(anchor):
                c = self.main.by_id(anchor).find('span', cls='ser-wnav-c')
                self.assertEqual(c.text().replace('\u00a0', ' '), 'WRITE-UP %d OF 3' % n)
        self.assertIsNone(self.main.by_id('day-1').find('span', cls='ser-wnav-c'))


class MonthBarStyleTests(unittest.TestCase):

    def test_an_empty_month_is_lighter_but_never_disabled(self):
        sheet = css('pages/series.css')
        self.assertNotIn('aria-disabled', sheet)
        self.assertNotIn('pointer-events: none', sheet.split('.ser-mnav a.is-empty')[1].split('}')[0])
        self.assertIn('.ser-mnav a.is-empty { color: var(--ink-3); }', sheet)


# ---------------------------------------------------------------- resilience-13, gap1-02, maps-10

TRK = '<path class="mk-trk" style="stroke: {{route}}; stroke-width: 3.0" d="M%s %sl10 10 5-5"/>'
ASCENT = '<path class="mk-trk" style="stroke: {{route}}; stroke-width: 2; stroke-dasharray: 5 3; stroke-linecap: butt" d="M%s %sl-10 -10"/>'
FADED = '<path class="mk-trk" style="stroke: {{route}}; stroke-width: 3.0; stroke-opacity: .35" d="M%s %sl1 1"/>'
SCALE = ('<g class="u-mi"><rect x="1279.9" y="616.0" width="32.0" height="5" style="fill: #16171A"/><rect x="1312.0" y="616.0" '
         'width="32.0" height="5" style="fill: #FFFFFF"/><text class="mk-lbl" x="1279.9" y="611.0">0</text><text class="mk-lbl" '
         'x="1344.0" y="611.0">0.5 mi</text></g><g class="u-km"><rect x="1265.2" y="616.0" width="19.9" height="5" '
         'style="fill: #16171A"/><rect x="1285.1" y="616.0" width="19.9" height="5" style="fill: #FFFFFF"/><text class="mk-lbl" '
         'x="1265.2" y="611.0">0</text><text class="mk-lbl" x="1311.0" y="621.0">500 m</text></g>')
SPAN = re.compile(r'<span id="route-start" class="mv-start" style="left:([\d.]+)%;top:([\d.]+)%" aria-hidden="true"></span>')


class RouteStartTests(rp.ReportFixture):

    def overlay(self, slug, body, name='map-wide'):
        """Give the fixture's placeholder render of `name` route paths (and a scale) in its overlay."""
        self.render(slug)
        t = self.by[slug]
        w, h = core.render_meta(t)['maps'][name]['w'], core.render_meta(t)['maps'][name]['h']
        with open(core.rendered(t, name + '.svg.html'), 'w', encoding='utf-8') as fh:
            fh.write('<svg width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>' % (w, h, w, h, body))
        self.pages.pop(slug, None)
        self.docs.pop(slug, None)
        return t

    def fs_html(self, t):
        return self.report.fullscreen_page(t).html

    def test_the_start_is_the_first_route_paths_first_point(self):
        t = self.overlay('syn-words', TRK % (720, 320) + TRK % (100, 100))
        self.assertEqual(core.route_start(t, 'map-wide'), (50.0, 50.0))
        m = SPAN.search(self.fs_html(t))
        self.assertIsNotNone(m)
        self.assertEqual((m.group(1), m.group(2)), ('50.00', '50.00'))
        self.assertEqual(SPAN.findall(self.fs_html(t)), [('50.00', '50.00')])    # one span, inside the map's .mv

    def test_a_ski_map_starts_at_the_dashed_ascent(self):
        # mapkit draws the descent first: its first point is the far end, not the trailhead
        t = self.overlay('syn-words', TRK % (1080, 160) + ASCENT % (360, 480))
        self.assertEqual(core.route_start(t, 'map-wide'), (25.0, 75.0))

    def test_the_start_disc_wins_over_the_paths(self):
        # mapkit draws its start disc at the recording's first point: a ski day that opens with a descent starts there,
        # not at the ascent's first point
        disc = '<circle cx="1296" cy="64" r="7" style="fill: #16171A; stroke: #FFFFFF; stroke-width: 3; paint-order: stroke"/>'
        t = self.overlay('syn-words', TRK % (1080, 160) + ASCENT % (360, 480) + disc)
        self.assertEqual(core.route_start(t, 'map-wide'), (90.0, 10.0))
        # a white disc (a mile marker) is not the start
        mile = '<circle cx="10" cy="10" r="7" style="fill: #FFFFFF; stroke: #16171A"/>'
        t = self.overlay('syn-words', TRK % (720, 320) + mile)
        self.assertEqual(core.route_start(t, 'map-wide'), (50.0, 50.0))

    def test_a_faded_path_is_passed_over(self):
        t = self.overlay('syn-words', FADED % (0, 0) + TRK % (144, 64))
        self.assertEqual(core.route_start(t, 'map-wide'), (10.0, 10.0))

    def test_no_route_path_or_a_start_outside_the_frame_marks_nothing(self):
        for body in ('<path class="gl-trk" d="M1 1L9 9"/>', TRK % (1500, 320), TRK % (100, -4)):
            with self.subTest(body=body[:40]):
                t = self.overlay('syn-words', body)
                self.assertIsNone(core.route_start(t, 'map-wide'))
                self.assertIsNone(SPAN.search(self.fs_html(t)))
                self.assertEqual(core.fullscreen_link(t, t['url']), '../../trips/syn-words/map/')

    def test_links_to_the_page_name_the_start_exactly_when_it_is_marked(self):
        t = self.overlay('syn-words', TRK % (720, 320))
        href = '../../trips/syn-words/map/#route-start'
        self.assertEqual(core.fullscreen_link(t, t['url']), href)
        html_ = self.page('syn-words').html
        self.assertIn('<a class="mv-fs" href="%s" aria-label="Open the full map">' % href, html_)
        self.assertIn('<a class="alink map-full" href="%s">Open the full map' % href, html_)
        self.assertEqual(html_.count('syn-words/map/"'), 0)                      # no bare link to it is left
        # 'Open the full map' sits after the key rows and before the caption
        wrap = self.main('syn-words').by_id('map').find('div', cls='wrap')
        names = [el.classes[0] for el in wrap.elements()]
        self.assertLess(max(i for i, c in enumerate(names) if c == 'keyrow'), names.index('alink'))
        self.assertLess(names.index('alink'), names.index('mapcap'))

    def test_the_page_shows_the_render_one_rule_names(self):
        t = self.by['syn-words']
        self.render('syn-words')
        self.assertEqual(core.fs_render(t), 'map-wide')
        self.assertEqual(core.fs_render(dict(t, kind='series')), 'overview-tall')
        self.assertEqual(core.fs_render(dict(t, kind='multi-day')), 'overview-col')     # no overview-wide in the meta


class FullScreenBarTests(rp.ReportFixture):

    def page_of(self, body, cls=None):
        self.render('syn-words')
        t = self.by['syn-words']
        with open(core.rendered(t, 'map-wide.svg.html'), 'w', encoding='utf-8') as fh:
            fh.write('<svg width="1440" height="640" viewBox="0 0 1440 640">%s</svg>' % body)
        return t, Doc(self.report.fullscreen_page(t).html)

    def test_the_bar_keeps_a_scale_in_both_units_and_the_disclaimer(self):
        _t, d = self.page_of(TRK % (720, 320) + SCALE)
        bar = d.find('div', cls='fs-bar')
        line = bar.find('div', cls='fs-line2')
        svg = line.find('svg', cls='fs-scale')
        self.assertEqual((svg['width'], svg['height'], svg['aria-hidden']), ('160', '24', 'true'))
        self.assertIn('viewBox="0 0 160 24"', core.fs_scale(_t, 'map-wide', 1440))
        self.assertEqual([g.classes for g in svg.find_all('g')], [['u-mi'], ['u-km']])
        self.assertEqual([t.text() for t in svg.find_all('text')], ['0', '0.5 mi', '0', '500 m'])
        self.assertEqual(line.find('span', cls='fs-nav').text(), 'NOT FOR NAVIGATION')
        # drawn at the page's size: the 1440 px render 1:1, so the mile bar is 64 px long
        mi = svg.find_all('g')[0].find_all('rect')
        self.assertEqual([r['width'] for r in mi], ['32.0', '32.0'])
        # the key row and the caption stay under the map
        self.assertIsNotNone(d.find('div', cls='fs-foot').find('ul', cls='keyrow'))

    def test_a_render_shown_larger_gets_a_scale_drawn_larger(self):
        t, _d = self.page_of(SCALE)
        svg = core.fs_scale(t, 'map-wide', 2160)
        self.assertEqual(re.findall(r'width="([\d.]+)" height="5"', svg)[:2], ['48.0', '48.0'])
        self.assertEqual(core.fs_scale(t, 'map-wide', 1440).count('<g class='), 2)

    def test_no_scale_in_the_render_leaves_the_disclaimer_alone(self):
        _t, d = self.page_of(TRK % (720, 320))
        line = d.find('div', cls='fs-line2')
        self.assertIsNone(line.find('svg'))
        self.assertEqual(line.find('span', cls='fs-nav').text(), 'NOT FOR NAVIGATION')

    def test_drag_to_pan_shows_without_a_script(self):
        sheet = css('base.css')
        self.assertIn('.fs-pan { color: var(--ink-3); margin-left: 12px; }', sheet)
        self.assertIn('.is-fit .fs-pan { display: none; }', sheet)
        self.assertIn('max-height: calc(100svh - 168px)', sheet)


class JournalMapLinkTests(sp.JournalFixture):

    def test_the_journal_offers_the_full_map_with_a_bare_link(self):
        # its overview draws the days without route paths, so its full-screen page marks no start; 'Open the full map'
        # only when the overview is rendered
        t = self.journal()
        maps = {'overview-tall': {'png': 'overview-tall.webp', 'w': 560, 'h': 860},
                'overview-phone': {'png': 'overview-phone.webp', 'w': 390, 'h': 600}}
        with mock.patch.object(core, 'render_meta', return_value={'maps': maps, 'charts': {}}):
            intro = Doc(self.series.page(t, helpers.make_site([t])).html).by_id('map')
        a = intro.find('a', cls='map-full')
        self.assertEqual(a['href'], '../../trips/%s/map/' % sp.SLUG)
        unrendered = Doc(self.series.page(t, helpers.make_site([t])).html).by_id('map')
        self.assertIsNone(unrendered.find('a', cls='map-full'))


class MultiDayFullMapTests(rp.ReportFixture):

    def test_the_overview_and_its_full_screen_page_mark_the_start_after_slim(self):
        multiday = importlib.import_module('sitegen.pages.multiday')
        tour = self.by['syn-tour']
        folder = os.path.join(self.tmp, '_rendered', 'syn-tour-fs')
        os.makedirs(folder, exist_ok=True)
        maps = {'overview-wide': {'w': 1440, 'h': 560}, 'overview-col': {'w': 718, 'h': 440}, 'overview-phone': {'w': 390, 'h': 260}}
        with open(os.path.join(folder, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump({'maps': maps, 'charts': {}}, fh)
        for name, m in maps.items():
            with open(os.path.join(folder, name + '.svg.html'), 'w', encoding='utf-8') as fh:
                fh.write('<svg width="%d" height="%d" viewBox="0 0 %d %d">%s%s</svg>'
                         % (m['w'], m['h'], m['w'], m['h'], FADED % (1, 1), TRK % (m['w'] / 4, m['h'] / 2)))
        tour['rendered'] = folder
        self.assertEqual(core.fs_render(tour), 'overview-wide')
        self.assertEqual(core.route_start(tour, 'overview-wide'), (25.0, 50.0))
        href = '../../trips/syn-tour/map/#route-start'
        sec = multiday.overview_map(tour, tour['url'], core.render_meta(tour))
        self.assertIn('<a class="alink map-full" href="%s">' % href, sec)
        self.assertIn('<a class="mv-fs" href="%s"' % href, sec)
        fs = multiday.fullscreen(tour).html
        self.assertEqual(SPAN.findall(fs), [('25.00', '50.00')])                  # it survives multiday.slim
        self.assertIn('NOT FOR NAVIGATION', fs)


class ViewerMarkupTests(unittest.TestCase):

    def test_the_dialog_is_described_by_its_live_region_and_offers_the_file_on_an_error(self):
        d = Doc(core.lightbox())
        dlg = d.find('dialog', cls='lb')
        self.assertEqual(dlg['aria-describedby'], 'lb-live')
        self.assertIsNotNone(d.by_id('lb-live'))
        a = dlg.find('a', cls='lb-file')
        self.assertIn('hidden', a)
        self.assertEqual(a.text(), 'Open the file')
        self.assertNotIn('href', a)

    def test_a_drag_reaches_the_script_and_the_page_behind_stays_put(self):
        sheet = css('base.css')
        self.assertRegex(sheet, r'\.lb \{[^}]*touch-action: pinch-zoom;')
        self.assertIn('html:has(dialog.lb[open]) { overflow: hidden; }', sheet)


if __name__ == '__main__':
    unittest.main()
