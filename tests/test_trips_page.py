"""Phase 2: the Trips explorer (sitegen.pages.trips.build -> trips/ and trips/search.json) and the shared card it is
built from (core.trip_card).

A synthetic site in a temp dir: five single-day trips across two regions and three years (one title with accents and
an apostrophe), one multi-day trip written on one day, the PCT-shaped series (search_aliases: [PCT]), one planned route
and one draft. sitegen.pages.trips is imported in setUp, so a missing module fails each test clearly instead of
breaking discovery. core.region_map_href reads rendered/site/meta.json; the fixture regions are patched into core's
in-memory copy so the map anchors resolve without reading rendered/. Fixture slugs match no real trip, so nothing under
rendered/trips/ is ever consulted.
"""
import importlib
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, PCT_PROSE, photo, LANDSCAPE, PORTRAIT  # noqa: E402

WRITEUP = 'Skinned up from the lake before dawn and skied the couloir on firm, edgeable snow.'
DAY_PROSE = 'Crossed the Col du Chardonnet in a cold wind and reached the hut by four.'
REGIONS = ['Eastern Sierra', 'Alps', 'Pacific Crest Trail']   # most reports first: 4, 2, 1
HERE = 'trips/'
SIZES = '(min-width: 1200px) 400px, 100vw'
BY_YEAR = {'2026': ['west-couloir'],
           '2025': ['basin-loop', 'lovers-leap', 'haute-route'],
           '2024': ['dana-couloir', 'pacific-crest-trail-2024', 'vallee-blanche']}


def load_trips_module(tc):
    """sitegen.pages.trips, or a clear failure of the calling test when tools/sitegen/pages/trips.py is missing."""
    try:
        return importlib.import_module('sitegen.pages.trips')
    except ImportError as ex:
        tc.fail('tools/sitegen/pages/trips.py is not importable: %s' % ex)


def option_values(select):
    return [o['value'] if o['value'] is not None else o.text() for o in select.find_all('option')]


def pages_by_url(pages):
    return {p.url: p for p in pages}


class ExplorerFixture(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        meta = {'hash': '', 'maps': {}, 'regions': [], 'all_regions': list(REGIONS) + ['Lake Tahoe', 'Utah']}
        patcher = mock.patch.object(core, '_SITE_META', [meta])
        patcher.start()
        self.addCleanup(patcher.stop)
        # Eastern Sierra: 4 reports (ski, climb, ski, hike)
        helpers.make_trip(self.tmp, 'west-couloir', title='West Couloir', activity='ski', date='2026-01-17', place='Sawtooth Ridge',
                          region='Eastern Sierra', body=WRITEUP, track=True, stats={'distance_km': 12.7, 'gain_m': 893},
                          photos=[photo('photos/01.webp', PORTRAIT, alt='Skinning'), photo('photos/02.webp', LANDSCAPE, alt='The couloir', sm=True)])
        helpers.make_trip(self.tmp, 'lovers-leap', title="Lover's Leap: Corrugation Corner", activity='climb', date='2025-06-14',
                          place="Lover's Leap", region='Eastern Sierra', body='Three pitches of perfect granite dikes.', track=True)
        helpers.make_trip(self.tmp, 'dana-couloir', title='Dana Couloir', activity='ski', date='2024-05-11', place='Mount Dana',
                          region='Eastern Sierra', track=True, map={'peaks': ['Mount Dana']})
        helpers.make_trip(self.tmp, 'basin-loop', title='Basin Loop', activity='hike', date='2025-08-10', region='Eastern Sierra',
                          route_shape='loop', body='A loop over three summits with a long scree descent.')
        # Alps: 2 reports (ski, multi-day hike written on day 2 only)
        helpers.make_trip(self.tmp, 'vallee-blanche', title='Aiguille du Midi – Vallée Blanche', activity='ski', date='2024-03-02',
                          place='Chamonix', region='Alps', body='Down the glacier from the Midi in flat light.', track=True)
        helpers.make_trip(self.tmp, 'haute-route', title='Haute Route', activity='hike', kind='multi-day', date='2025-04-01',
                          end_date='2025-04-03', region='Alps',
                          days=[{'title': 'Argentière'}, {'title': 'Trient', 'body': DAY_PROSE}, {'title': 'Zermatt'}])
        # Pacific Crest Trail: 1 report (the series, three days, two with tracks)
        helpers.make_series(self.tmp, search_aliases=['PCT'])
        # never listed: a planned route (the only mtb trip and the only Lake Tahoe one) and a draft (the only 'other' trip)
        helpers.make_trip(self.tmp, 'someday-ridge', title='Someday Ridge', activity='mtb', kind='planned', date='2027-06-01',
                          region='Lake Tahoe', track=True)
        helpers.make_trip(self.tmp, 'secret-draft', title='Secret Draft', activity='other', draft=True, date='2026-03-01',
                          region='Utah', body='Unpublished words.', track=True)
        self.trips = helpers.load_dir(self.tmp)
        self.site = helpers.make_site(self.trips)
        self.by = self.site['by_slug']
        self.published = helpers.slugs(self.site['published'])   # newest first

    def build(self, site):
        return pages_by_url(self.trips_mod.build(site))


# ---------------------------------------------------------------- the trips/ page and trips/search.json

class ExplorerPageTests(ExplorerFixture):

    def setUp(self):
        super().setUp()
        self.trips_mod = load_trips_module(self)
        self.pages = self.trips_mod.build(self.site)
        by_url = pages_by_url(self.pages)
        self.assertIn('trips/', by_url)
        self.assertIn('trips/search.json', by_url)
        self.page = by_url['trips/']
        self.json_page = by_url['trips/search.json']
        self.doc = Doc(self.page.html)
        self.main = self.doc.by_id('main')
        self.form = self.doc.by_id('search')

    def card(self, slug):
        return self.doc.find('li', attrs={'data-slug': slug})

    def selects(self):
        return {s['name']: s for s in self.form.find_all('select')}

    def test_build_returns_the_page_and_the_search_json(self):
        self.assertEqual(len(self.pages), 2)
        self.assertEqual(self.page.title, 'Trips')
        self.assertTrue(self.page.index)
        self.assertFalse(self.json_page.index)
        self.assertTrue(self.page.html.lstrip().lower().startswith('<!doctype html>'))

    def test_search_json_is_the_dumped_index(self):
        data = json.loads(self.json_page.html)
        self.assertEqual([e['s'] for e in data], self.published)
        self.assertNotIn('<', self.json_page.html)
        try:
            search = importlib.import_module('sitegen.search')
        except ImportError as ex:
            self.fail('tools/sitegen/search.py is not importable: %s' % ex)
        self.assertEqual(self.json_page.html, search.dumps(search.build_index(self.site)))

    def test_title_count_line_and_body_class(self):
        h1s = self.doc.find_all('h1')
        self.assertEqual(len(h1s), 1)
        self.assertEqual(h1s[0]['id'], 'trips-title')
        self.assertEqual(h1s[0].text(), 'Trips')
        self.assertIn('p-trips', self.doc.find('body').classes)
        text = self.main.text()
        self.assertEqual(len(self.published), 7)
        # the head mirrors map/'s head block, which drops count_items' 'INCL. ...' item (the stats line is counts only)
        for want in ('7 REPORTS', '3 REGIONS', '2024–2026'):
            self.assertIn(want, text)
        self.assertNotIn('8 REPORTS', text)        # the planned route is not a report
        self.assertNotIn('PLANNED ROUTE', text)
        self.assertNotIn('9 REPORTS', text)        # nor are the series' days

    def test_browse_block_lists_activities_regions_and_years_as_plain_links(self):
        nav = self.doc.find('nav', cls='trx-browse')
        self.assertIsNotNone(nav)
        self.assertEqual(nav['aria-label'], 'Browse')
        self.assertEqual(len(nav.find_all('ul')), 3)
        links = nav.find_all('a')
        hrefs = [a['href'] for a in links]
        for act in ('ski', 'climb', 'hike'):
            self.assertIn('../' + core.section_url(act), hrefs)
        for act in ('mtb', 'other'):
            self.assertNotIn('../' + core.section_url(act), hrefs)
        self.assertEqual([h for h in hrefs if '#region-' in h],
                         ['../map/#region-%s' % content.slugify(r) for r in REGIONS])   # most reports first
        self.assertNotIn('../map/#region-lake-tahoe', hrefs)
        self.assertEqual([h for h in hrefs if h.startswith('#y-')], ['#y-2026', '#y-2025', '#y-2024'])
        ski = next(a for a in links if a['href'] == '../ski/')
        self.assertRegex(ski.parent.text(), r'\b3\b')
        es = next(a for a in links if a['href'] == '../map/#region-eastern-sierra')
        self.assertIn('Eastern Sierra', es.parent.text())
        self.assertRegex(es.parent.text(), r'\b4\b')

    def test_form_is_server_rendered_hidden_with_a_labelled_search_input(self):
        form = self.form
        self.assertIsNotNone(form)
        self.assertEqual(form.tag, 'form')
        self.assertIn('trx-form', form.classes)
        self.assertEqual(form['role'], 'search')
        self.assertIn('hidden', form)
        q = form.by_id('trx-q')
        self.assertIsNotNone(q)
        self.assertEqual(q.tag, 'input')
        self.assertEqual(q['name'], 'q')
        self.assertIn(q['type'] or 'text', ('text', 'search'))
        labels = [l for l in self.doc.find_all('label') if l['for'] == 'trx-q']
        labelled = (labels and 'Search trips' in labels[0].text()) or q['aria-label'] == 'Search trips'
        self.assertTrue(labelled, 'the search input must be labelled "Search trips"')

    def test_activity_radios_only_for_activities_with_a_report(self):
        radios = [b for b in self.form.find_all('button', attrs={'role': 'radio'}) if b['data-filter'] is not None]
        self.assertEqual(radios[0]['data-filter'], 'all')
        self.assertEqual({b['data-filter'] for b in radios}, {'all', 'ski', 'climb', 'hike'})
        for b in radios:
            self.assertIn('fchip', b.classes, repr(b))
        counts = {b['data-filter']: b.text() for b in radios}
        self.assertIn('All', counts['all'])   # like the archive's All chip, no count: #trx-count carries the total
        self.assertRegex(counts['ski'], r'\b3\b')
        self.assertRegex(counts['climb'], r'\b1\b')
        self.assertRegex(counts['hike'], r'\b3\b')

    def test_selects_checkbox_and_view_controls(self):
        sel = self.selects()
        self.assertEqual(option_values(sel['region']), ['', 'eastern-sierra', 'alps', 'pacific-crest-trail'])
        for name, opt in zip(REGIONS, sel['region'].find_all('option')[1:]):
            self.assertIn(name, opt.text())
        self.assertEqual(option_values(sel['year']), ['', '2026', '2025', '2024'])
        self.assertEqual(option_values(sel['format']), ['', 'trip', 'multi-day', 'series'])
        labels = [o.text() for o in sel['format'].find_all('option')]
        self.assertTrue(labels[0].startswith('Any'), labels[0])   # 'Any' or 'Any format'
        self.assertEqual(labels[1:], ['Single-day', 'Multi-day', 'Series'])
        self.assertEqual(option_values(sel['sort']), ['newest', 'oldest', 'relevance'])
        cb = self.form.find('input', attrs={'type': 'checkbox', 'name': 'writeup'})
        self.assertIsNotNone(cb)
        self.assertEqual(cb['value'], '1')
        self.assertIn('Has a write-up', self.form.text())
        views = [b for b in self.form.find_all('button', attrs={'role': 'radio'}) if b['data-view'] is not None]
        self.assertEqual([b['data-view'] for b in views], ['cards', 'list'])

    def test_control_values_match_the_cards_data_attributes(self):
        cards = self.main.find_all('li', cls='tcard')
        self.assertEqual(len(cards), 7)
        sel = self.selects()
        filters = {b['data-filter'] for b in self.form.find_all('button', attrs={'role': 'radio'}) if b['data-filter']}
        self.assertEqual({c['data-act'] for c in cards}, filters - {'all'})
        self.assertEqual({c['data-region'] for c in cards}, set(option_values(sel['region'])) - {''})
        self.assertEqual({c['data-year'] for c in cards}, set(option_values(sel['year'])) - {''})
        self.assertEqual({c['data-kind'] for c in cards}, set(option_values(sel['format'])) - {''})
        self.assertEqual({c['data-writeup'] for c in cards}, {'0', '1'})
        for c in cards:
            t = self.by[c['data-slug']]
            self.assertEqual(c['data-writeup'], '1' if t['has_writeup'] else '0', c['data-slug'])
            self.assertEqual(c['data-date'], t['date'].isoformat())
            self.assertEqual(c['data-act'], t['activity'])
            self.assertEqual(c['data-kind'], t['kind'])

    def test_noscript_note(self):
        ns = self.doc.find('noscript')
        self.assertIsNotNone(ns)
        self.assertIn('JavaScript', ns.text())

    def test_status_elements(self):
        count = self.doc.by_id('trx-count')
        self.assertEqual(count.tag, 'p')
        self.assertTrue({'t-mono-s', 'trx-count'} <= set(count.classes), count.classes)
        self.assertEqual(count['aria-live'], 'polite')
        self.assertEqual(count.text(), '7 REPORTS')
        chips = self.doc.by_id('trx-chips')
        self.assertEqual(chips.tag, 'ul')
        self.assertIn('trx-chips', chips.classes)
        self.assertEqual(chips['aria-label'], 'Active filters')
        self.assertEqual(chips.elements(), [])
        clear = self.doc.by_id('trx-clear')
        self.assertEqual((clear.tag, clear['type']), ('button', 'button'))
        self.assertIn('hidden', clear)
        self.assertEqual(clear.text(), 'Clear all')
        msg = self.doc.by_id('trx-msg')
        self.assertEqual(msg.tag, 'p')
        self.assertIn('note', msg.classes)
        self.assertIn('hidden', msg)
        none = self.doc.by_id('trx-none')
        self.assertEqual(none.tag, 'div')
        self.assertIn('empty', none.classes)
        self.assertIn('hidden', none)
        self.assertIsNotNone(none.find('button'))

    def test_year_groups_newest_first_with_anchors_and_counts(self):
        groups = [g for g in self.main.find_all('section', cls='trx-yr') if 'data-year' in g]
        self.assertEqual([g['data-year'] for g in groups], ['2026', '2025', '2024'])
        for g in groups:
            y = g['data-year']
            with self.subTest(year=y):
                h2 = g.find('h2')
                self.assertEqual(h2['id'], 'y-' + y)
                self.assertIn('t-label', h2.classes)
                self.assertEqual(h2.text(), y)
                n = g.find(cls='trx-yr-n')
                self.assertIn('t-mono-s', n.classes)
                self.assertRegex(n.text(), r'\b%d\b' % len(BY_YEAR[y]))
                grid = g.find('ul', cls='trx-grid')
                cards = grid.find_all('li', cls='tcard')
                self.assertEqual([c['data-slug'] for c in cards], BY_YEAR[y])   # published order within the year
                for c in cards:
                    self.assertEqual(c['data-year'], y)
        self.assertIsNone(self.doc.by_id('y-2027'))
        self.assertEqual(len(self.doc.find_all(attrs={'id': 'y-2025'})), 1)

    def test_results_wrapper_and_sorted_container(self):
        res = self.doc.by_id('trx-results')
        self.assertIsNotNone(res)
        self.assertEqual(len([g for g in res.find_all('section', cls='trx-yr') if 'data-year' in g]), 3)
        sec = self.doc.by_id('trx-sorted-sec')
        self.assertEqual(sec.tag, 'section')
        self.assertIn('hidden', sec)
        self.assertEqual(sec.find('h2')['id'], 'trx-sorted-h')   # the heading keeps the outline h1 > h2 > h3 in sorted views
        sorted_ = self.doc.by_id('trx-sorted')
        self.assertEqual(sorted_.tag, 'ul')
        self.assertIn('trx-grid', sorted_.classes)
        self.assertEqual(sorted_.elements(), [])
        self.assertEqual(len(self.main.find_all('ul', cls='trx-grid')), 4)

    def test_every_published_trip_is_a_card_once_and_nothing_else_is(self):
        cards = self.main.find_all('li', cls='tcard')
        self.assertEqual(sorted(c['data-slug'] for c in cards), sorted(self.published))
        hrefs = sorted(h.find('a')['href'] for h in self.main.find_all('h3', cls='tcard-t'))
        self.assertEqual(hrefs, sorted('../trips/%s/' % s for s in self.published))
        for s in ('someday-ridge', 'secret-draft'):
            self.assertNotIn(s, self.page.html)
        text = self.main.text()
        for name in ('Someday Ridge', 'Secret Draft', 'Unpublished', 'Lake Tahoe', 'Utah'):
            self.assertNotIn(name, text)
        self.assertNotIn('lake-tahoe', self.page.html)
        main_hrefs = [a['href'] or '' for a in self.main.find_all('a')]
        for bad in ('mountain-biking/', 'other/'):
            self.assertFalse(any(h.endswith(bad) for h in main_hrefs), bad)

    def test_titles_keep_accents_and_apostrophes(self):
        for slug in ('lovers-leap', 'vallee-blanche', 'west-couloir'):
            a = self.card(slug).find('h3', cls='tcard-t').find('a')
            self.assertEqual(a.text(), self.by[slug]['title'])

    def test_links_are_relative_and_leave_the_explorer_folder_with_dot_dot(self):
        for a in self.doc.find_all('a'):
            self.assertFalse((a['href'] or '').startswith('/'), a['href'])
        for a in self.main.find_all('a'):
            href = a['href'] or ''
            if href.startswith('#') or href.startswith('http'):
                continue
            self.assertTrue(href.startswith('../'), href)

    def test_card_summaries_follow_card_summary_and_skip_facts(self):
        ex = self.card('west-couloir').find('p', cls='tcard-ex')
        self.assertIsNotNone(ex)
        self.assertIn('Skinned up from the lake', ex.text())
        self.assertIsNone(self.card('west-couloir').find(cls='tcard-exl'))
        series = self.card('pacific-crest-trail-2024')
        self.assertIsNone(series.find(cls='tcard-ex'))
        self.assertNotIn('Journal of', series.text())
        self.assertNotIn(PCT_PROSE, series.text())
        md = self.card('haute-route')
        self.assertEqual(md.find('p', cls='tcard-exl').text(), 'DAY 2 · TRIENT')
        self.assertIn(DAY_PROSE, md.find('p', cls='tcard-ex').text())
        self.assertIsNone(self.card('dana-couloir').find(cls='tcard-ex'))

    def test_header_marks_trips_as_the_current_page(self):
        nav = self.doc.find('nav', attrs={'aria-label': 'Main'})
        cur = [(a['href'], a['aria-current']) for a in nav.find_all('a') if a['aria-current']]
        self.assertEqual(cur, [('../trips/', 'page')])

    def test_format_options_only_list_kinds_present(self):
        site2 = helpers.make_site([self.by[s] for s in ('west-couloir', 'lovers-leap', 'someday-ridge')])
        doc = Doc(self.build(site2)['trips/'].html)
        form = doc.by_id('search')
        sel = {s['name']: s for s in form.find_all('select')}
        self.assertEqual(option_values(sel['format']), ['', 'trip'])
        self.assertEqual(option_values(sel['year']), ['', '2026', '2025'])
        self.assertEqual(doc.by_id('trx-count').text(), '2 REPORTS')
        self.assertNotIn('INCL.', doc.by_id('main').text())
        self.assertEqual(len(doc.find_all('li', cls='tcard')), 2)

    def test_undated_trips_form_a_last_group(self):
        helpers.make_trip(self.tmp, 'no-date', title='Undated Lap', activity='ski', track=True)
        site = helpers.make_site(helpers.load_dir(self.tmp))
        doc = Doc(self.build(site)['trips/'].html)
        groups = [g for g in doc.find_all('section', cls='trx-yr') if 'data-year' in g]
        self.assertEqual([g['data-year'] for g in groups], ['2026', '2025', '2024', ''])
        last = groups[-1]
        self.assertEqual(last.find('h2').text(), 'Undated')
        card = last.find('li', cls='tcard')
        self.assertEqual((card['data-slug'], card['data-year'], card['data-date']), ('no-date', '', ''))
        sel = {s['name']: s for s in doc.by_id('search').find_all('select')}
        self.assertEqual(option_values(sel['year']), ['', '2026', '2025', '2024'])
        self.assertEqual(doc.by_id('trx-count').text(), '8 REPORTS')


# ---------------------------------------------------------------- core.trip_card

class TripCardTests(ExplorerFixture):

    def setUp(self):
        super().setUp()
        if not hasattr(core, 'trip_card'):
            self.fail('core.trip_card is not implemented')

    def card(self, slug, here=HERE, **kw):
        return Doc(core.trip_card(self.by[slug], here, SIZES, **kw)).find('li')

    def test_root_li_and_data_attributes(self):
        li = self.card('west-couloir')
        self.assertEqual(li.classes, ['tcard'])
        self.assertEqual(li['data-slug'], 'west-couloir')
        self.assertEqual(li['data-act'], 'ski')
        self.assertEqual(li['data-kind'], 'trip')
        self.assertEqual(li['data-region'], 'eastern-sierra')
        self.assertEqual(li['data-year'], '2026')
        self.assertEqual(li['data-writeup'], '1')
        self.assertEqual(li['data-date'], '2026-01-17')
        md = self.card('haute-route')
        self.assertEqual((md['data-kind'], md['data-region'], md['data-writeup'], md['data-date']), ('multi-day', 'alps', '1', '2025-04-01'))
        se = self.card('pacific-crest-trail-2024')
        self.assertEqual((se['data-kind'], se['data-act'], se['data-region'], se['data-year']), ('series', 'hike', 'pacific-crest-trail', '2024'))
        self.assertEqual(self.card('dana-couloir')['data-writeup'], '0')

    def test_missing_region_and_date_give_empty_attributes(self):
        helpers.make_trip(self.tmp, 'bare', title='Bare', activity='ski', track=True)
        li = Doc(core.trip_card(helpers.load(self.tmp, 'bare'), HERE, SIZES)).find('li')
        self.assertEqual((li['data-region'], li['data-year'], li['data-date']), ('', '', ''))
        self.assertEqual(li['data-slug'], 'bare')

    def test_extra_class(self):
        self.assertEqual(self.card('west-couloir', cls='hom-rcard').classes, ['tcard', 'hom-rcard'])

    def test_media_cover_image(self):
        li = self.card('west-couloir')
        a = li.find('a', cls='tcard-img')
        self.assertIsNotNone(a)
        self.assertEqual(a['href'], '../trips/west-couloir/')
        self.assertEqual(a['tabindex'], '-1')
        self.assertEqual(a['aria-hidden'], 'true')
        self.assertNotIn('tcard-img--tile', a.classes)
        img = a.find('img')
        self.assertIn('cover-img', img.classes)
        self.assertEqual(img['alt'], 'The couloir')
        self.assertEqual(img['src'], '../trips/west-couloir/photos/02.webp')
        self.assertIn('srcset', img)
        self.assertEqual(img['sizes'], SIZES)
        self.assertEqual(len(li.find_all('img')), 1)
        self.assertIsNone(li.find(cls='tcard-img--none'))

    def test_media_falls_back_to_the_route_tile(self):
        t = dict(self.by['dana-couloir'])   # a copy whose rendered folder is a temp dir holding a tile
        rdir = os.path.join(self.tmp, '_rendered', 'dana-couloir')
        helpers.touch(os.path.join(rdir, 'tile.svg.html'))
        t['rendered'] = rdir
        self.assertTrue(core.tile(t, HERE))
        li = Doc(core.trip_card(t, HERE, SIZES)).find('li')
        a = li.find('a', cls='tcard-img')
        self.assertIsNotNone(a)
        self.assertIn('tcard-img--tile', a.classes)
        self.assertEqual((a['href'], a['tabindex'], a['aria-hidden']), ('../trips/dana-couloir/', '-1', 'true'))
        img = a.find('img')
        self.assertIn('gl--tile', img.classes)
        self.assertEqual(img['src'], '../trips/dana-couloir/tile.svg')
        self.assertEqual(img['alt'], '')
        self.assertIsNone(li.find(cls='cover-img'))
        self.assertIsNone(li.find(cls='tcard-img--none'))

    def test_media_falls_back_to_the_activity_disc(self):
        li = self.card('basin-loop')   # no photo, no rendered tile
        div = li.find('div', cls='tcard-img')
        self.assertIsNotNone(div)
        self.assertIn('tcard-img--none', div.classes)
        self.assertEqual(div['aria-hidden'], 'true')
        self.assertIsNotNone(div.find(cls='disc'))
        self.assertEqual(li.find_all('img'), [])
        self.assertIsNone(li.find('a', cls='tcard-img'))

    def test_meta_line_id_and_describedby(self):
        li = self.card('west-couloir')
        meta = li.find('p', cls='tcard-meta')
        self.assertEqual(meta['id'], 'tc-west-couloir-m')
        self.assertIn('t-mono-s', meta.classes)
        text = meta.text().lower()
        self.assertIn('jan 17, 2026', text)
        self.assertIn('sawtooth ridge', text)
        a = li.find('h3', cls='tcard-t').find('a')
        self.assertEqual(a['aria-describedby'], 'tc-west-couloir-m')
        self.assertEqual(a.text(), 'West Couloir')
        # no place: the region
        self.assertIn('eastern sierra', self.card('basin-loop').find('p', cls='tcard-meta').text().lower())
        # the series shows its short range
        self.assertIn('apr–sep 2024', self.card('pacific-crest-trail-2024').find('p', cls='tcard-meta').text().lower())

    def test_namespace_changes_the_ids(self):
        li = self.card('west-couloir', ns='rc')
        self.assertEqual(li.find('p', cls='tcard-meta')['id'], 'rc-west-couloir-m')
        self.assertEqual(li.find('h3').find('a')['aria-describedby'], 'rc-west-couloir-m')

    def test_title_link_is_relative_to_here(self):
        self.assertEqual(self.card('west-couloir', here='').find('h3').find('a')['href'], 'trips/west-couloir/')
        self.assertEqual(self.card('west-couloir', here='trips/').find('h3').find('a')['href'], '../trips/west-couloir/')
        self.assertEqual(self.card('lovers-leap').find('h3').find('a').text(), "Lover's Leap: Corrugation Corner")
        self.assertEqual(self.card('vallee-blanche').find('h3').find('a').text(), 'Aiguille du Midi – Vallée Blanche')

    def test_activity_row_has_chip_tags_and_stats(self):
        act = self.card('west-couloir').find('div', cls='tcard-act')
        self.assertIsNotNone(act)
        chip = act.find(cls='chip')
        self.assertIn('chip--inline', chip.classes)
        self.assertIn('Backcountry Ski', chip.text())
        self.assertTrue(core.row_stats_line(self.by['west-couloir']))
        self.assertIn('MI', act.text())
        self.assertIn('FT GAIN', act.text())
        self.assertIn('Multi-day · 3 days', self.card('haute-route').find('div', cls='tcard-act').text())
        self.assertIn('Series', self.card('pacific-crest-trail-2024').find('div', cls='tcard-act').text())
        self.assertNotIn('Loop', self.card('basin-loop').find('div', cls='tcard-act').text())   # shape=False

    def test_summary_off_by_default(self):
        for slug in ('west-couloir', 'haute-route', 'pacific-crest-trail-2024'):
            li = self.card(slug)
            self.assertIsNone(li.find(cls='tcard-ex'), slug)
            self.assertIsNone(li.find(cls='tcard-exl'), slug)

    def test_summary_shows_the_report_excerpt(self):
        li = self.card('west-couloir', summary=True)
        ex = li.find('p', cls='tcard-ex')
        self.assertIn('t-excerpt', ex.classes)
        self.assertEqual(ex.text(), core.card_summary(self.by['west-couloir'])['text'])
        self.assertIsNone(li.find(cls='tcard-exl'))

    def test_summary_multiday_has_the_day_label_above_its_excerpt(self):
        li = self.card('haute-route', summary=True)
        lab = li.find('p', cls='tcard-exl')
        self.assertIn('t-label', lab.classes)
        self.assertEqual(lab.text(), 'DAY 2 · TRIENT')
        ex = li.find('p', cls='tcard-ex')
        self.assertEqual(ex.text(), DAY_PROSE)
        order = list(li.walk())
        self.assertLess(order.index(lab), order.index(ex))

    def test_summary_never_shows_facts(self):
        series = self.by['pacific-crest-trail-2024']
        self.assertEqual(core.card_summary(series)['source_kind'], 'facts')
        li = self.card('pacific-crest-trail-2024', summary=True)
        self.assertIsNone(li.find(cls='tcard-ex'))
        self.assertNotIn('Journal of', li.text())
        self.assertNotIn(PCT_PROSE, li.text())
        helpers.make_trip(self.tmp, 'hut-days', title='Hut Days', activity='ski', kind='multi-day', date='2024-02-01', end_date='2024-02-02',
                          days=[{'title': 'Approach'}, {'title': 'Hut'}])
        t = helpers.load(self.tmp, 'hut-days')
        self.assertEqual(core.card_summary(t)['source_kind'], 'facts')
        li = Doc(core.trip_card(t, HERE, SIZES, summary=True)).find('li')
        self.assertIsNone(li.find(cls='tcard-ex'))
        self.assertNotIn('2-day', li.text())

    def test_summary_is_absent_for_a_track_only_trip(self):
        li = self.card('dana-couloir', summary=True)
        self.assertIsNone(li.find(cls='tcard-ex'))
        self.assertIsNone(li.find(cls='tcard-exl'))


if __name__ == '__main__':
    unittest.main()
