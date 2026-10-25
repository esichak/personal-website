"""Phase 10 on the report and multi-day pages (docs/claude-code-website-prompt-2.md, Phase 10), on the synthetic site of
tests/test_report_page.py (its ReportFixture: every slug starts with syn-, nothing under content/ or rendered/ is read):

  report-02  a photo-only report leads with its landscape cover, in the compact order
  report-01  a written report without photos whose words clear core.STRUCTURED_MIN_CHARS leads with the words
  report-11  a multi-day trip leads with its cover; a strip of one square per day with photos, each to #day-N
  report-03  the lead photo's frame is 3:2 on every screen from 560 (the variant picked from the side-by-side sheet)
  report-04  the Moving cell says Elapsed and Start, and keeps that line on phones (strip-c--time)
  report-05  the mile table has a Time column and the profile head the time at the GPS max, in the trip's zone
  gap6-04    the stats footnote stays under the strip on phones: no copy under the map caption (rep-note-ph is gone)
  maps-01/02 'Contours every 200 ft' per visible render; 'Mile (1.6 km)' under KM; Trail (OSM) and Road key items only
             where the render's base layer draws them; 'VERTICAL SCALE ×N'
  copy-04    a 'Track only' tag on a single-day report with neither words nor photos
  bench-11   a Beta row's url: makes its value a link
  a11y-09    'View as table' under a multi-day day chart and the section featured chart
  resil-06   phone galleries keep a photo's own shape (--ar, --arp)
  report-10  a multi-day day's chip and row say WRITE-UP / N PHOTOS; the Overview head counts them
  maps-04    the data the profile readout reads (data-pf, data-pf-km, each render's data-w and data-pad)

The readout script itself is tested by tests/profile_js_harness.js (tests/test_profile_js.py); the section row, the
bottom bar and the related head by tests/test_report_page.py and tests/test_related.py."""
import importlib
import json
import os
import re
import unittest

import helpers
from helpers import Doc, photo, LANDSCAPE, PORTRAIT
import gpx_fixtures as gf
import test_report_page as rp

from sitegen import core

tearDownModule = helpers.no_region_pages_left

LONG = ('A synthetic write-up long enough to clear the floor: more than a hundred characters of words written for a test, '
        'in two sentences.')
TIMED = gf.gpx(gf.trk([gf.SEG_A]))                     # 12 points a minute apart from 15:00 UTC; the top at the last
UNTIMED = gf.gpx(gf.trk([gf.line(38.9, -120.1, 12, eles=gf.ELES_A, times=False)]))
ZONE = 'America/Los_Angeles'                            # 15:00 UTC in July is 8:00 AM there


def css(name):
    with open(os.path.join(rp.ROOT, 'assets', 'css', name), encoding='utf-8') as fh:
        return fh.read()



def contours(ft, m):
    """The caption's contour item as core.map_caption writes it: since Phase 13C each unit is read out as its word."""
    return core.U(core.nb('Contours every %s' % ft) + '\xa0' + core.unit_word('ft'), core.nb('Contours every %s' % m) + '\xa0' + core.unit_word('m'))

class Fixture(rp.ReportFixture):

    def with_track(self, slug, text, **meta):
        t = self.add(slug, **meta)
        with open(os.path.join(self.tmp, slug, 'track.gpx'), 'w', encoding='utf-8') as fh:
            fh.write(text)
        self.load_site()
        return self.by[slug]


# ---------------------------------------------------------------- the four layout cases

class LayoutCaseTests(Fixture):

    def test_a_photo_only_report_leads_with_its_landscape_cover(self):
        self.render('syn-photos')
        main = self.main('syn-photos')
        self.assertInOrder(rp.marks(main), ['title', 'hero', 'stats', 'map', 'photos'])
        body = self.doc('syn-photos').find('body').classes
        self.assertNotIn('p-report--story', body)
        self.assertNotIn('p-report--written', body)
        self.assertIsNone(main.find('nav', cls='rep-toc'))                 # the compact order keeps no section row
        head = self.doc('syn-photos').find('head')
        self.assertEqual([l['href'] for l in head.find_all('link', attrs={'rel': 'preload'})], ['../../trips/syn-photos/photos/01.webp'])
        self.assertEqual([i['fetchpriority'] for i in main.by_id('map').find_all('img')], [None] * len(main.by_id('map').find_all('img')))

    def test_a_portrait_cover_keeps_the_compact_page(self):
        self.assertIsNone(self.hero('syn-tall-only'))

    def test_a_written_report_without_photos_leads_with_the_words(self):
        self.add('syn-written', body=LONG)
        self.render('syn-written')
        self.assertTrue(core.written_report(self.by['syn-written']))
        doc, main = self.doc('syn-written'), self.main('syn-written')
        self.assertIn('p-report--written', doc.find('body').classes)
        self.assertNotIn('p-report--story', doc.find('body').classes)
        self.assertIsNone(self.hero('syn-written'))
        self.assertInOrder(rp.marks(main), ['title', 'stats', '.rep-toc', 'report', 'map'])
        self.assertEqual(self.toc('syn-written'), [rp.REPORT, rp.MAP])
        self.assertEqual(self.actions('syn-written'), [('View route', '#map'), ('Download GPX', 'syn-written.gpx'),
                                                       ('copy', core.SITE_URL + 'trips/syn-written/')])
        self.assertEqual(rp.bar_items(self.bbar('syn-written')), [rp.STATS, rp.REPORT, rp.MAP, ('GPX', 'syn-written.gpx')])
        self.assertIn('.p-report--written .rep-toc + .rep-body', css('pages/report.css'))

    def test_a_note_under_the_floor_stays_compact(self):
        t = self.by['syn-words']
        self.assertFalse(core.written_report(t))                           # 93 characters of plain text
        self.render('syn-words')
        self.assertIsNone(self.main('syn-words').find('nav', cls='rep-toc'))
        self.assertInOrder(rp.marks(self.main('syn-words')), ['stats', 'map', 'report'])
        self.assertNotIn('p-report--written', self.doc('syn-words').find('body').classes)


class MultiDayLeadTests(Fixture):

    def test_the_day_navs_fourth_line_stays_one_line(self):
        # .ml wraps by default (base.css): in the 80 px bar a second item on a new line spilled out of the chip
        sheet = css('pages/multiday.css')
        self.assertIn('.mul-dn-c .ml { flex-wrap: nowrap; }', sheet)
        self.assertIn('.mul-dn-c .ml > .mi { min-width: 0; overflow: hidden; text-overflow: ellipsis; }', sheet)

    def setUp(self):
        super().setUp()
        helpers.make_trip(self.tmp, 'syn-hut', title='Synthetic Hut Tour', activity='ski', kind='multi-day', date='2026-03-01',
                          end_date='2026-03-03', region=rp.REGION,
                          days=[{'title': 'Synthetic In', 'date': '2026-03-01', 'body': rp.WRITEUP,
                                 'photos': [photo('photos/d01-01.webp', LANDSCAPE, alt='Synthetic day photo', sm=True)]},
                                {'title': 'Synthetic Over', 'date': '2026-03-02',
                                 'photos': [photo('photos/d02-01.webp', PORTRAIT, alt='Synthetic tall photo', sm=True),
                                            photo('photos/d02-02.webp', LANDSCAPE, alt='Synthetic second photo', sm=True)]},
                                {'title': 'Synthetic Out', 'date': '2026-03-03'}])
        self.load_site()
        self.multiday = importlib.import_module('sitegen.pages.multiday')
        self.mdoc = Doc(self.multiday.page(self.by['syn-hut'], self.site).html)

    def test_the_cover_leads_and_is_preloaded(self):
        main = self.mdoc.by_id('main')
        hero = main.find('figure', cls='rep-hero')
        self.assertEqual(hero.find('a')['href'], '../../trips/syn-hut/photos/d01-01.webp')
        self.assertInOrder(rp.marks(main), ['title', 'hero', 'stats', 'map'])
        self.assertEqual([l['href'] for l in self.mdoc.find('head').find_all('link', attrs={'rel': 'preload'})],
                         ['../../trips/syn-hut/photos/d01-01.webp'])

    def test_one_square_per_day_with_photos_each_to_its_day(self):
        strip = self.mdoc.find('ul', cls='mul-pst')
        links = strip.find_all('a', cls='mul-pst-a')
        self.assertEqual([a['href'] for a in links], ['#day-1', '#day-2'])
        self.assertEqual([a.find('span').text() for a in links], ['DAY 1', 'DAY 2'])
        self.assertEqual([a.find('img')['src'] for a in links],
                         ['../../trips/syn-hut/photos/d01-01.sm.webp', '../../trips/syn-hut/photos/d02-01.sm.webp'])
        self.assertEqual([a.find('img')['alt'] for a in links], ['', ''])      # the link's text names the day
        self.assertEqual(strip['aria-label'], 'Days with photos')

    def test_the_day_chips_and_rows_say_what_a_day_holds(self):
        chips = self.mdoc.find_all('a', cls='mul-dn-day')
        self.assertEqual([c.classes.count('is-written') for c in chips], [1, 0, 0])
        self.assertEqual([rp.ml_items(c.find('span', cls='mul-dn-c')) if c.find('span', cls='mul-dn-c') else None for c in chips],
                         [['WRITE-UP', '1 PHOTO'], ['2 PHOTOS'], None])
        rows = self.mdoc.find('ol', cls='mul-di').find_all('li')
        self.assertIn('WRITE-UP', rp.ml_items(rows[0].find('span', cls='mul-di-m')))
        self.assertIn('2 PHOTOS', rp.ml_items(rows[1].find('span', cls='mul-di-m')))
        head = self.mdoc.by_id('overview').find('span', cls='shead-m')
        self.assertEqual(rp.ml_items(head)[-2:], ['1 WRITE-UP', '3 PHOTOS'])
        bundle = css('pages/multiday.css')
        self.assertIn('.mul-dn-day.is-written .mul-dn-d::after', bundle)

    def test_the_note_is_under_the_strip(self):
        self.assertIsNotNone(self.mdoc.by_id('stats').find('p', cls='strip-note'))
        self.assertNotIn('rep-note-ph', str(self.mdoc.root.text()) + self.multiday.page(self.by['syn-hut'], self.site).html)


# ---------------------------------------------------------------- the lead photo's frame

class HeroFrameTests(unittest.TestCase):

    def test_three_to_two_on_every_screen_from_560(self):
        # report-03: variant A of the side-by-side sheet (.cache/plan2/phase10/sheet/); phones keep 4:3
        sheet = css('pages/report.css')
        self.assertIn('.rep-hero .cover-img { display: block; width: 100%; height: auto; aspect-ratio: 3 / 2; object-fit: cover; }', sheet)
        self.assertNotIn('aspect-ratio: 2 / 1', sheet)
        self.assertIn('.rep-hero .cover-img { aspect-ratio: 4 / 3; }', sheet)


# ---------------------------------------------------------------- the strip, the footnote, times of day

class StripTimeTests(Fixture):

    def test_the_moving_cell_says_elapsed_and_start(self):
        t = self.add('syn-timed-cell', stats={'distance_km': 10.0, 'moving': '2:00', 'elapsed': '2:40'}, start_time='06:30')
        cell = [c for c in core.strip_cells(t) if c[0] == 'Moving'][0]
        self.assertEqual(cell[3], 'strip-c--time')
        self.assertEqual(cell[2], core.meta_items([core.nb('Elapsed 2:40'), core.nb('Start 6:30 AM')]))
        strip = Doc(core.strip(core.strip_cells(t)))
        self.assertEqual([c.classes for c in strip.find_all('div', cls='strip-c')][-1], ['strip-c', 'strip-c--time'])
        self.assertEqual(core.strip_cells(self.add('syn-moving-only', stats={'moving': '1:00'}))[0][2], '')   # nothing to say

    def test_phones_keep_the_time_line_and_the_note(self):
        sheet = css('pages/report.css')
        self.assertIn('body.p-report .rep-strip .strip-c--time .strip-s { display: block; }', sheet)
        self.assertIn('body.p-report .rep-strip .strip-s { display: none; }', sheet)
        self.assertNotIn('rep-note-ph', sheet + css('pages/multiday.css') + css('base.css'))
        for slug in rp.SINGLE:
            with self.subTest(slug):
                self.assertNotIn('rep-note-ph', self.page(slug).html)

    def test_the_mile_table_has_the_clock_in_the_trips_zone(self):
        t = self.with_track('syn-timed', TIMED, timezone=ZONE)
        self.render('syn-timed', chart='profile')
        prof = self.main('syn-timed').by_id('profile')
        table = prof.find('table')
        self.assertEqual([th.text() for th in table.find_all('th')][-1], 'Time')
        self.assertEqual([tr.find_all('td')[-1].text() for tr in table.find('tbody').find_all('tr')], ['8:00 AM', '8:08 AM', '8:11 AM'])
        meta = rp.ml_items(prof.find('p', cls='t-mono-s'))
        self.assertTrue(meta[0].endswith(' AT 8:11 AM'), meta[0])          # Doc.text() reads no-break spaces as spaces
        self.assertEqual(core.gps_max_clock(core.read_track(t['track']), 'Not/AZone'), '')        # never a UTC clock instead

    def test_no_time_column_without_times_or_a_zone(self):
        self.with_track('syn-untimed', UNTIMED, timezone=ZONE)
        self.render('syn-untimed', chart='profile')
        table = self.main('syn-untimed').by_id('profile').find('table')
        self.assertEqual([th.text() for th in table.find_all('th')], ['MileKm', 'Elevation (ft)Elevation (m)'])
        self.assertNotIn(' AT ', self.main('syn-untimed').by_id('profile').find('p', cls='t-mono-s').text())
        tr = core.read_track(self.by['syn-untimed']['track'])
        self.assertNotIn('Time', core.elevation_table(core.read_track(os.path.join(self.tmp, 'syn-untimed', 'track.gpx')), {}, None))
        self.assertIsNotNone(tr)

    def test_a_timed_track_without_a_zone_it_can_load_shows_no_clock(self):
        # no timezone: line, and one zoneinfo does not know: the page shows neither the column nor ' AT …', never UTC
        for slug, zone in (('syn-timed-nozone', None), ('syn-timed-badzone', 'Not/AZone')):
            with self.subTest(zone=zone):
                self.with_track(slug, TIMED, **({'timezone': zone} if zone else {}))
                self.render(slug, chart='profile')
                prof = self.main(slug).by_id('profile')
                self.assertEqual([th.text() for th in prof.find('table').find_all('th')], ['MileKm', 'Elevation (ft)Elevation (m)'])
                self.assertNotIn(' AT ', prof.find('p', cls='t-mono-s').text())


# ---------------------------------------------------------------- captions and keys

class CaptionKeyTests(Fixture):

    def intervals(self, slug, values):
        self.render(slug)
        folder = self.by[slug]['rendered']
        with open(os.path.join(folder, 'meta.json'), encoding='utf-8') as fh:
            meta = json.load(fh)
        for name, ft in values.items():
            meta['maps'][name]['interval_ft'] = ft
        with open(os.path.join(folder, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(meta, fh)
        self.pages.pop(slug, None)
        self.docs.pop(slug, None)

    def test_the_caption_names_the_visible_renders_contour_interval(self):
        self.intervals('syn-track', {'map-wide': 200, 'map-col': 400, 'map-phone': 500})
        cap = self.report.map_caption(self.by['syn-track'])
        items = re.findall(r'<span class="mi([^"]*)">(?:<span class="sr">, </span>)?(<span class="u">.*?</span></span>)', cap)
        self.assertEqual([c for c, _h in items], [' vx vx--wide', ' vx vx--col', ' vx vx--phone'])
        self.assertIn(contours('200', '61'), cap)
        self.assertIn(contours('400', '122'), cap)
        self.intervals('syn-track', {'map-wide': 200, 'map-col': 200, 'map-phone': 200})
        cap = self.report.map_caption(self.by['syn-track'])
        self.assertEqual(cap.count(contours('200', '61')), 1)
        self.assertNotIn('vx--', cap)
        self.render('syn-photos')
        self.assertNotIn('Contours', self.report.map_caption(self.by['syn-photos']))      # a render that states no interval

    def test_a_mile_disc_says_its_kilometres_under_km(self):
        row = core.key_row(['mile', 'mile_out'])
        km = core.unit_word(' km')                                   # Phase 13C: shown 'km', read 'kilometers'
        self.assertIn(core.U('Mile', 'Mile (1.6%s)' % km), row)
        self.assertIn(core.U('Mile, outbound', 'Mile (1.6%s), outbound' % km), row)
        self.assertEqual([helpers.seen_text(s) for s in Doc(row).find_all('span', cls='u-km')],
                         ['Mile (1.6 km)', 'Mile (1.6 km), outbound'])
        self.assertIn('>Custom</li>', core.key_row([('mile', 'Custom')]))       # a label given is escaped text as before

    def test_trail_and_road_only_where_the_base_layer_draws_them(self):
        self.render('syn-track')
        t = self.by['syn-track']
        meta = core.render_meta(t)
        self.assertNotIn('trail', self.report.key_items(t, meta))
        for name, body in (('map-wide', '<path class="mk-trail" d="M0 0"/><path class="mk-minor" d="M0 0"/>'),
                           ('map-col', '<path class="mk-trail" d="M0 0"/>'),
                           ('map-phone', '<path class="mk-road" d="M0 0"/>')):
            with open(os.path.join(t['rendered'], name + '.base.svg'), 'w', encoding='utf-8') as fh:
                fh.write('<svg>%s</svg>' % body)
        items = self.report.key_items(t, meta)
        self.assertEqual(items[-1], 'trail')                                    # both desktop renders draw trails
        self.assertNotIn('road', items)                                         # the col render draws no road
        self.assertNotIn('trail', self.report.key_items(t, meta, phone=True))
        self.assertIn('Trail (OSM)', core.key_row(items))

    def test_the_chart_head_says_vertical_scale(self):
        charts = {'profile-wide': {'vx': 1.4}, 'profile-col': {'vx': 1.9}}
        items = core.vx_line(charts, [('profile-wide', 'wide'), ('profile-col', 'col')], items=True)
        self.assertEqual([h for h, _c in items], ['VERTICAL\u00a0SCALE\u00a0×1.4', 'VERTICAL\u00a0SCALE\u00a0×1.9'])


# ---------------------------------------------------------------- the Track only tag

class TrackOnlyTagTests(Fixture):

    def test_a_report_with_neither_words_nor_photos_is_track_only(self):
        tag = '<span class="tag">Track only</span>'
        self.assertIn(tag, core.trip_tags(self.by['syn-track']))
        chips = self.main('syn-track').find('div', cls='rep-chips')
        self.assertIn('Track only', [x.text() for x in chips.find_all('span', cls='tag')])     # the title block
        for slug in ('syn-words', 'syn-photos', 'syn-story'):
            self.assertNotIn('Track only', core.trip_tags(self.by[slug]), slug)
        for slug in ('syn-tour', 'syn-journal', 'syn-goal'):
            self.assertNotIn('Track only', core.trip_tags(self.by[slug]), slug)
        card = core.trip_card(self.by['syn-track'], 'trips/', '50vw', ns='t')
        row = core.trip_row(self.by['syn-track'], 'trips/')
        self.assertIn('Track only', card)
        self.assertIn('Track only', row)


# ---------------------------------------------------------------- a Beta row's url

class BetaUrlTests(Fixture):

    def test_a_url_makes_the_value_a_link(self):
        t = self.add('syn-beta-url', body=rp.WRITEUP, beta=[{'label': 'Route', 'value': 'Synthetic Line', 'url': 'https://example.test/route'},
                                                         {'label': 'Grade', 'value': 'Synthetic II', 'url': 'javascript:alert(1)'},
                                                         {'label': 'Guide', 'value': 'Synthetic Guide', 'url': 'https:example.test'}])
        block = self.report.beta_list(t)
        self.assertIn('<dd><a href="https://example.test/route" rel="noopener">Synthetic Line</a></dd>', block)
        self.assertIn('<dd>Synthetic II</dd>', block)                           # never a link the check would refuse
        self.assertIn('<dd>Synthetic Guide</dd>', block)                        # the check refuses it too (content.web_url)


# ---------------------------------------------------------------- 'View as table' under every elevation chart

class TableEverywhereTests(Fixture):

    def test_a_multi_day_day_chart_and_the_section_featured_chart_have_the_table(self):
        multiday = importlib.import_module('sitegen.pages.multiday')
        section = importlib.import_module('sitegen.pages.section')
        tour = self.by['syn-tour']
        folder = os.path.join(self.tmp, '_rendered', 'syn-tour')
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump({'maps': {}, 'charts': {'day-01-profile-col': {'w': 718, 'h': 120, 'vx': 2.0}}}, fh)
        with open(os.path.join(folder, 'day-01-profile-col.svg.html'), 'w', encoding='utf-8') as fh:
            fh.write('<svg width="718" height="120" viewBox="0 0 718 120"></svg>')
        tour['rendered'] = folder
        d = tour['days'][0]
        with open(d['track'], 'w', encoding='utf-8') as fh:
            fh.write(TIMED)
        html_ = multiday.day_profile(tour, tour['url'], core.render_meta(tour), d)
        self.assertIn('<details class="eltab">', html_)
        self.assertNotIn('>Time<', html_)                                       # a day's zone waits on the trip's (12.12)
        t = self.with_track('syn-featured-chart', TIMED, timezone=ZONE)
        self.render('syn-featured-chart', chart='profile')
        block = section.profile_block(self.by['syn-featured-chart'], 'hiking/', [('profile-col', 'col'), ('profile-phone', 'phone')], 'fp')
        self.assertIn('<details class="eltab">', block)
        self.assertIn(core.U('Mile', 'Km'), block)


# ---------------------------------------------------------------- phone galleries keep a photo's shape

class GalleryShapeTests(Fixture):

    def test_each_photo_carries_its_shape_and_the_phone_rules_use_it(self):
        t = self.add('syn-shapes', body=rp.WRITEUP, photos=[photo('photos/01.webp', (2800, 1000), alt='Synthetic panorama'),
                                                           photo('photos/02.webp', (460, 1000), alt='Synthetic tall one')])
        html_ = core.photo_rows(t, t['url'], t['photos'])
        self.assertIn('style="--ar:2.8000;--arp:2.8000;', html_)
        self.assertIn('style="--ar:0.4600;--arp:0.6000;', html_)
        sheet = css('base.css')
        block = sheet[sheet.index('.jrows { --jgap: 12px; }'):]
        self.assertIn('.jph--l img { aspect-ratio: var(--ar); }', block)
        self.assertIn('.jph--solo img { aspect-ratio: var(--arp); }', block)
        self.assertIn('.jph--p img { aspect-ratio: 3 / 4; }', block)


# ---------------------------------------------------------------- the readout's data

class ReadoutDataTests(Fixture):

    def test_a_finger_on_the_chart_still_scrolls_and_zooms_the_page(self):
        # pan-y alone would stop a pinch that starts on the chart (about 358 of 390 px on a phone) from zooming
        self.assertIn('.chart[data-pf] .cv { position: relative; touch-action: pan-y pinch-zoom; }', css('pages/report.css'))

    def test_the_profile_carries_its_elevations_and_each_renders_axis(self):
        t = self.with_track('syn-readout', TIMED, timezone=ZONE, stats={'distance_km': 2.0})
        self.render('syn-readout', chart='profile')
        chart = self.main('syn-readout').by_id('profile').find('div', cls='chart')
        pf = json.loads(chart['data-pf'])
        self.assertEqual(len(pf), core.READOUT_SAMPLES + 1)
        self.assertEqual((pf[0], pf[-1]), (2000, 2050))
        self.assertEqual(chart['data-pf-km'], '2')
        self.assertEqual([(cv['data-w'], cv['data-pad']) for cv in chart.find_all('div', cls='cv')],
                         [('1248', '0'), ('718', '0'), ('358', '0')])
        size = len('data-pf="%s" data-pf-km="2"' % chart['data-pf'])
        self.assertLess(size, 1500)

    def test_no_data_without_a_track(self):
        self.render('syn-track', chart='profile')
        os.remove(os.path.join(self.tmp, 'syn-track', 'track.gpx'))
        self.load_site()
        self.render('syn-track', chart='profile')
        self.assertNotIn('data-pf', self.page('syn-track').html)


if __name__ == '__main__':
    unittest.main()
