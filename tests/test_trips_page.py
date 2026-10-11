"""Phase 2: the Trips explorer (sitegen.pages.trips.build -> trips/ and trips/search.json) and the shared card it is
built from (core.trip_card). Phase 3: the journal-day index (trips/journal.json) and the "Journal days" block that
trips.js fills, after the results.

A synthetic site in a temp dir: five single-day trips across two regions and three years (one title with accents and
an apostrophe), one multi-day trip written on one day, the PCT-shaped series (search_aliases: [PCT]), one planned route
and one draft. sitegen.pages.trips is imported in setUp, so a missing module fails each test clearly instead of
breaking discovery. core.region_map_href reads rendered/site/meta.json; the fixture regions are patched into core's
in-memory copy so the map anchors resolve without reading rendered/. Fixture slugs match no real trip, so nothing under
rendered/trips/ is ever consulted.

Phase 4 (contract-phase4.md): the inline script that shows the search form before first paint (5.1: core.reveal), the
card-size .th copy, which a card offers to phones in a <source> of its own and never in its <img> (5.3 as replaced by
10.5; a .th file here is an empty placeholder written beside the photo) and the page's share image (4.1:
core.site_share).
"""
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
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, PCT_PROSE, photo, LANDSCAPE, PORTRAIT  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

WRITEUP = 'Skinned up from the lake before dawn and skied the couloir on firm, edgeable snow.'
DAY_PROSE = 'Crossed the Col du Chardonnet in a cold wind and reached the hut by four.'
REGIONS = ['Eastern Sierra', 'Alps', 'Pacific Crest Trail']   # most reports first: 4, 2, 1
HERE = 'trips/'
SIZES = '(min-width: 1200px) 400px, 100vw'
PICTURE = re.compile(r'<picture class="cover-pic">(<source [^>]*>)(<img [^>]*>)</picture>')   # a card cover with a .th copy


def unwrap(html_):
    """A page or fragment with every card cover's <picture class="cover-pic"> taken off: the <img> it holds, alone."""
    return PICTURE.sub(lambda m: m.group(2), html_)
BY_YEAR = {'2026': ['west-couloir'],
           '2025': ['basin-loop', 'lovers-leap', 'haute-route'],
           '2024': ['dana-couloir', 'pacific-crest-trail-2024', 'vallee-blanche']}


TRIPS_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'trips.js')
# the journal-day block's parts: trips.js looks each of the last three up by id and gives up on journal-day search when
# one is missing; the heading names the section
DAYS_PARTS = {'trx-days-h': 'h2', 'trx-days-n': 'span', 'trx-days-l': 'ol', 'trx-days-more': 'button'}


def make_journal(root, slug, days, **meta):
    """A journal (kind: series) whose days are exactly `days` (dicts for helpers.make_trip: no 'title' is an untitled
    day, no 'body' a track-only one). helpers.make_series cannot make these cases: it titles every day."""
    m = dict(title='Synthetic Traverse 2022', activity='hike', kind='series', date='2022-07-01', end_date='2022-07-03')
    m.update(meta)
    return helpers.make_trip(root, slug, days=days, **m)


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


def share_meta(doc):
    """{property or name: content} of a page's share-image tags (og:image and its properties, the twitter card)."""
    out = {}
    for m in doc.find('head').find_all('meta'):
        key = m['property'] or m['name'] or ''
        if key.startswith(('og:image', 'twitter:')):
            if key in out:
                raise AssertionError('two %s tags' % key)
            out[key] = m['content']
    return out


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

    def site_with_only_journal(self, days):
        """The fixture's site with its journal replaced by one whose days are `days`: the only journal there is."""
        make_journal(self.tmp, 'synthetic-traverse', days)
        site = helpers.make_site([t for t in helpers.load_dir(self.tmp) if t['slug'] != 'pacific-crest-trail-2024'])
        self.assertEqual([t['slug'] for t in site['published'] if t['kind'] == 'series'], ['synthetic-traverse'])
        return site


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
        # the page, the trip index and, because the fixture has a journal, the journal-day index
        self.assertEqual(sorted(p.url for p in self.pages), ['trips/', 'trips/journal.json', 'trips/search.json'])
        self.assertEqual(self.page.title, 'Trips')
        self.assertTrue(self.page.index)
        self.assertFalse(self.json_page.index)
        self.assertTrue(self.page.html.lstrip().lower().startswith('<!doctype html>'))

    def test_journal_json_lists_the_days_of_the_journal(self):
        search = importlib.import_module('sitegen.search')
        page = pages_by_url(self.pages)['trips/journal.json']
        self.assertFalse(page.index)                       # a data file: not in the sitemap
        self.assertNotIn('<', page.html)
        self.assertEqual(page.html, search.dumps(search.build_day_index(self.site)))
        data = json.loads(page.html)
        self.assertTrue(data)
        self.assertEqual({e['s'] for e in data}, {'pacific-crest-trail-2024'})
        self.assertEqual(set(data[0]), {'s', 'a', 'n', 'j', 'h', 'w', 't', 'p', 'k', 'x', 'r', 'q'})
        # the written day and the two that have only a title (make_series titles every day and writes the first)
        self.assertEqual([(e['n'], e['h'], bool(e['x'])) for e in data],
                         [('1', 'Campo', True), ('2', 'Hauser Creek', False), ('3', 'Lake Morena', False)])

    def test_the_page_has_a_hidden_empty_journal_days_block_naming_its_index(self):
        sec = self.doc.by_id('trx-days')
        self.assertIsNotNone(sec)
        self.assertEqual(sec.tag, 'section')
        self.assertTrue({'trx-days', 'wrap'} <= set(sec.classes), sec.classes)
        self.assertIn('hidden', sec.attrs)
        self.assertEqual(sec['data-index'], 'journal.json')
        self.assertEqual(sec['aria-labelledby'], 'trx-days-h')
        # every part trips.js needs is there, once, inside the block: without #trx-days-l, #trx-days-n or
        # #trx-days-more the script turns journal-day search off without a word
        for id_, tag in DAYS_PARTS.items():
            with self.subTest(id=id_):
                self.assertEqual(len(self.doc.find_all(attrs={'id': id_})), 1)
                part = sec.by_id(id_)
                self.assertIsNotNone(part, '#%s is not inside #trx-days' % id_)
                self.assertEqual(part.tag, tag)
        self.assertEqual(len(self.doc.find_all(attrs={'id': 'trx-days'})), 1)
        self.assertEqual(self.doc.by_id('trx-days-h').text(), 'Journal days')
        self.assertEqual(self.doc.by_id('trx-days-n').text(), '')              # 'N DAYS', written by trips.js with the hits
        self.assertEqual(self.doc.by_id('trx-days-l').elements(), [])          # filled by trips.js, never at build time
        more = self.doc.by_id('trx-days-more')
        self.assertEqual((more.tag, more['type']), ('button', 'button'))
        self.assertIn('hidden', more.attrs)
        self.assertEqual(more.text(), '')

    def test_the_journal_days_block_comes_after_the_results(self):
        # reports first, then the journal days a search finds: a query for the journal's own name shows its card on top
        order = list(self.doc.root.walk())
        count, results, sec = self.doc.by_id('trx-count'), self.doc.by_id('trx-results'), self.doc.by_id('trx-days')
        self.assertLess(order.index(count), order.index(results))
        self.assertLess(order.index(results), order.index(sec))
        # after the results container, not inside it: every card and both result lists come before the block
        self.assertFalse(any(el is sec for el in results.walk()))
        self.assertIs(sec.parent, results.parent)
        cards = self.main.find_all('li', cls='tcard')
        self.assertEqual(len(cards), 7)
        self.assertLess(order.index(cards[-1]), order.index(sec))
        self.assertLess(order.index(self.doc.by_id('trx-sorted')), order.index(sec))

    def test_every_journal_day_hook_trips_js_names_is_on_the_page(self):
        # the script and the page must agree on the ids: getElementById('trx-days-…') for the parts, '#trx-days' for the
        # status line's link to the list
        with open(TRIPS_JS, encoding='utf-8') as fh:
            src = fh.read()
        named = set(re.findall(r"""['"]#?(trx-days[\w-]*)['"]""", src))
        self.assertIn('trx-days', named)
        for id_ in sorted(named):
            with self.subTest(id=id_):
                self.assertIsNotNone(self.doc.by_id(id_), 'trips.js names #%s, which the page does not have' % id_)

    def test_no_journal_block_or_index_without_a_journal(self):
        site = dict(self.site)
        site['published'] = [t for t in self.site['published'] if t['kind'] != 'series']
        site['trips'] = [t for t in self.site['trips'] if t['kind'] != 'series']
        pages = self.trips_mod.build(site)
        self.assertEqual(sorted(p.url for p in pages), ['trips/', 'trips/search.json'])
        self.assertNotIn('trx-days', pages_by_url(pages)['trips/'].html)

    def test_a_journal_of_untitled_track_only_days_still_gets_the_block_and_the_index(self):
        # no word anywhere in it, but each day has a name ('day 2') a reader can type
        site = self.site_with_only_journal([{'id': '001', 'date': '2022-07-01'}, {'id': '002', 'date': '2022-07-02'}, {'id': '003'}])
        journal = site['by_slug']['synthetic-traverse']
        self.assertEqual(len(journal['days']), 3)
        self.assertFalse(any(d['title'] or d['body_md'] for d in journal['days']))
        self.assertTrue(all(d['track'] for d in journal['days']))
        pages = self.build(site)
        self.assertEqual(sorted(pages), ['trips/', 'trips/journal.json', 'trips/search.json'])
        doc = Doc(pages['trips/'].html)
        sec = doc.by_id('trx-days')
        self.assertIsNotNone(sec)
        for id_, tag in DAYS_PARTS.items():
            self.assertIsNotNone(sec.by_id(id_), id_)
        data = json.loads(pages['trips/journal.json'].html)
        self.assertEqual([(e['s'], e['n'], e['a'], e['p'], e['h'], e['t'], e['x'], e['r']) for e in data],
                         [('synthetic-traverse', '1', 'day-1', 'day 1', '', '', '', ''),
                          ('synthetic-traverse', '2', 'day-2', 'day 2', '', '', '', ''),
                          ('synthetic-traverse', '3', 'day-3', 'day 3', '', '', '', '')])
        # the journal itself is still a report on the page and in the trip index
        card = doc.find('li', attrs={'data-slug': 'synthetic-traverse'})
        self.assertIsNotNone(card)
        self.assertEqual((card['data-kind'], card['data-writeup']), ('series', '0'))
        self.assertIn('synthetic-traverse', [e['s'] for e in json.loads(pages['trips/search.json'].html)])

    def test_a_titled_track_only_day_is_in_the_index_with_its_title(self):
        # no write-up anywhere, but one day has a name of its own to be found by
        site = self.site_with_only_journal([{'id': '001', 'date': '2022-07-01'},
                                            {'id': '002', 'title': 'Synthetic Pass', 'date': '2022-07-02'}, {'id': '003'}])
        journal = site['by_slug']['synthetic-traverse']
        self.assertFalse(journal['has_writeup'])
        self.assertEqual([d['title'] for d in journal['days'] if d['title']], ['Synthetic Pass'])
        pages = self.build(site)
        self.assertEqual(sorted(pages), ['trips/', 'trips/journal.json', 'trips/search.json'])
        sec = Doc(pages['trips/'].html).by_id('trx-days')
        self.assertIsNotNone(sec)
        self.assertEqual(sec['data-index'], 'journal.json')
        for id_, tag in DAYS_PARTS.items():
            self.assertIsNotNone(sec.by_id(id_), id_)
            self.assertEqual(sec.by_id(id_).tag, tag)
        data = json.loads(pages['trips/journal.json'].html)
        self.assertEqual([(e['s'], e['n'], e['a'], e['h'], e['t'], e['w'], e['x'], e['r']) for e in data],
                         [('synthetic-traverse', '1', 'day-1', '', '', 'Jul 1, 2022', '', ''),
                          ('synthetic-traverse', '2', 'day-2', 'Synthetic Pass', 'synthetic pass', 'Jul 2, 2022', '', ''),
                          ('synthetic-traverse', '3', 'day-3', '', '', '', '', '')])

    def test_the_journal_days_heading_can_take_the_focus(self):
        # the status line's link to the list moves the focus there by script (trips.js toDays): a heading needs
        # tabindex="-1" for that, and stays out of the tab order
        h = self.doc.by_id('trx-days-h')
        self.assertEqual((h.tag, h['tabindex']), ('h2', '-1'))

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

    def test_the_form_is_shown_by_an_inline_script_right_after_it(self):
        # contract-phase4.md 5.1 and 10: the form still ships hidden (without JavaScript it stays so); core.reveal('search')
        # is the element right after </form> and before the noscript note, so with JavaScript the form is in place at
        # first paint and the results below it do not jump when the deferred bundle arrives
        form = self.form
        self.assertIn('hidden', form)
        siblings = form.parent.elements()
        at = [k for k, n in enumerate(siblings) if n is form]
        self.assertEqual(len(at), 1)
        script, note = siblings[at[0] + 1], siblings[at[0] + 2]
        self.assertEqual((script.tag, script.attrs), ('script', {}))      # inline and classic: it runs as the parser passes it
        self.assertEqual(script.children, ['document.getElementById("search").hidden=false'])
        self.assertEqual(note.tag, 'noscript')
        self.assertIn('JavaScript', note.text())
        self.assertTrue(hasattr(core, 'reveal'), 'core.reveal is missing (contract-phase4.md 10)')
        self.assertIn('</form>' + core.reveal('search') + '<noscript>', self.page.html)
        self.assertEqual(self.page.html.count(core.reveal('search')), 1)
        # the script finds the form by its id: one element has it, and it is the form (the header's Search link, #search)
        self.assertEqual(len(self.doc.find_all(attrs={'id': 'search'})), 1)
        self.assertIs(self.doc.by_id('search'), form)
        # the body's other script is the deferred bundle, at the very end
        scripts = self.doc.find('body').find_all('script')
        self.assertEqual([('src' in s, 'defer' in s) for s in scripts], [(False, False), (True, True)])
        self.assertIs(scripts[0], script)
        # nothing else on the page is revealed this way: the status parts and the journal block wait for trips.js
        for id_ in ('trx-clear', 'trx-msg', 'trx-none', 'trx-sorted-sec', 'trx-days'):
            self.assertIn('hidden', self.doc.by_id(id_), id_)

    def test_core_reveal_is_one_statement_on_the_named_element(self):
        # contract-phase4.md 10: reveal(el_id) -> <script>document.getElementById("<id>").hidden=false</script>
        self.assertEqual(core.reveal('search'), '<script>document.getElementById("search").hidden=false</script>')
        self.assertEqual(core.reveal('trx-form'), '<script>document.getElementById("trx-form").hidden=false</script>')

    def test_the_page_shares_the_site_image_when_a_trip_is_featured(self):
        # contract-phase4.md 4.1: trips/ passes image=core.site_share(), the share photo of the first featured trip;
        # none when nothing is featured (the fixture's own site has no 'featured')
        self.assertEqual(share_meta(self.doc), {'twitter:card': 'summary'})
        self.assertNotIn('og:image', self.page.html)
        self.site['featured'] = [self.by['west-couloir'], self.by['basin-loop']]
        with mock.patch.object(core, '_SITE_SHARE', [None]):
            core.register_site(self.site)
            self.assertTrue(hasattr(core, 'site_share'), 'core.site_share is missing (contract-phase4.md 4.1)')
            self.assertEqual(core.site_share(), core.share_photo(self.by['west-couloir']))
            self.assertEqual(core.site_share(), {'path': 'trips/west-couloir/photos/02.webp', 'w': 1600, 'h': 1200, 'alt': 'The couloir'})
            doc = Doc(self.build(self.site)['trips/'].html)
            self.assertEqual(share_meta(doc), {'og:image': core.SITE_URL + 'trips/west-couloir/photos/02.webp', 'og:image:type': 'image/webp',
                                               'og:image:width': '1600', 'og:image:height': '1200', 'og:image:alt': 'The couloir',
                                               'twitter:card': 'summary_large_image', 'twitter:image:alt': 'The couloir'})
            # the JSON indexes are data, not pages: no head, no image
            self.assertNotIn('og:image', self.build(self.site)['trips/search.json'].html)
        del self.site['featured']
        core.register_site(self.site)
        self.assertIsNone(core.site_share())

    def test_a_card_offers_the_card_size_copy_to_phones_only(self):
        # contract-phase4.md 10.5 (it replaces 5.3, under which the copy led the <img>'s own srcset and a 1x desktop
        # screen took it for the 400 px slot): on trips/ a cover with a .th copy is wrapped in <picture class="cover-pic">
        # whose one <source> applies below 560 px and lists the copy first, at its real width (427 px for a 1600 x 1200
        # photo), for the 112 px slot; the <img> keeps its two candidates and TRX_SIZES. contract-phase5.md section 5:
        # the source declares that slot as 106 px (core.CARD_PHONE_SIZES), so a 3x phone takes the 320 px copy of a
        # portrait or square cover; the <img>'s own string still ends with the real 112 px
        sizes = '(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2), 112px'
        self.assertEqual(self.trips_mod.TRX_SIZES, sizes)
        base = '../trips/west-couloir/photos/'
        two = '%s02.sm.webp 800w, %s02.webp 1600w' % (base, base)
        img = self.card('west-couloir').find('img')
        self.assertEqual(img['srcset'], two)                                                      # no .th file yet: as before
        self.assertNotIn('<picture', self.page.html)
        self.assertNotIn('<source', self.page.html)
        helpers.touch(os.path.join(self.tmp, 'west-couloir', 'photos', '02.th.webp'))
        site = helpers.make_site(helpers.load_dir(self.tmp))
        self.assertEqual([p['th'] for p in site['by_slug']['west-couloir']['photos']], [None, 'photos/02.th.webp'])
        html_ = self.build(site)['trips/'].html
        card = Doc(html_).find('li', attrs={'data-slug': 'west-couloir'})
        img = card.find('img')
        self.assertEqual(img['srcset'], two)                                                      # with the file: the same <img>
        self.assertEqual(img['sizes'], sizes)
        self.assertEqual((img['src'], img['width'], img['height'], img['loading']), (base + '02.webp', '1600', '1200', 'lazy'))
        link_ = card.find('a', cls='tcard-img')
        self.assertEqual([n.tag for n in link_.elements()], ['picture'])
        pic = link_.find('picture')
        self.assertEqual((pic.classes, [n.tag for n in pic.elements()]), (['cover-pic'], ['source', 'img']))
        source = pic.find('source')
        self.assertEqual((source['media'], source['sizes']), ('(max-width: 559.98px)', '106px'))
        self.assertEqual((source['sizes'], img['sizes'].rsplit(', ', 1)[1]), (core.CARD_PHONE_SIZES, core.CARD_PHONE_SLOT))
        self.assertEqual(source['srcset'], '%s02.th.webp 427w, %s' % (base, two))
        self.assertEqual(sorted(source.attrs), ['media', 'sizes', 'srcset'])
        # it is the page's only wrapper (no other report has the copy), and nothing else on the page names the file
        self.assertEqual((html_.count('<picture'), html_.count('<source'), html_.count('.th.')), (1, 1, 1))
        for i in Doc(html_).find_all('img'):
            self.assertNotIn('.th.', (i['srcset'] or '') + (i['src'] or ''))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, 'west-couloir', 'photos', '02.th.webp')))
        # wrapper apart, the page is the page of the site without the .th file
        self.assertEqual(unwrap(html_), self.page.html)
        self.assertNotEqual(html_, self.page.html)

    def test_every_card_with_a_copy_is_wrapped_and_the_page_is_otherwise_the_same(self):
        # 10.5 on the whole page: give every photo that has an .sm copy a .th copy as well, and one more report a cover
        # with both; then each card whose cover has the copy is wrapped, each other card is not, every source names a
        # file that exists, and the page without its wrappers is the page built before any .th file was written
        helpers.make_trip(self.tmp, 'tall-cover', title='Tall Cover', activity='hike', date='2023-02-02', region='Alps', track=True,
                          photos=[photo('photos/01.webp', PORTRAIT, alt='Tall', sm=True)])
        before = self.build(helpers.make_site(helpers.load_dir(self.tmp)))['trips/'].html
        self.assertNotIn('<picture', before)
        self.assertNotIn('.th.', before)
        made = []
        for t in helpers.load_dir(self.tmp, include_drafts=True):
            for ph in t['photos'] + [x for d in t['days'] for x in d['photos']]:
                if ph['sm']:
                    base, ext = os.path.splitext(ph['file'])
                    helpers.touch(os.path.join(self.tmp, t['slug'], base + '.th' + ext))
                    made.append((t['slug'], base + '.th' + ext))
        self.assertIn(('west-couloir', 'photos/02.th.webp'), made)
        self.assertIn(('tall-cover', 'photos/01.th.webp'), made)
        site = helpers.make_site(helpers.load_dir(self.tmp))
        html_ = self.build(site)['trips/'].html
        doc = Doc(html_)
        wrapped = []
        for card in doc.find_all('li', cls='tcard'):
            t = site['by_slug'][card['data-slug']]
            cover = t.get('cover')
            has = bool(cover and cover['photo']['th'] and cover['photo']['sm'] and cover['photo']['w'])
            pics = card.find_all('picture')
            self.assertEqual(len(pics), 1 if has else 0, card['data-slug'])
            if has:
                wrapped.append(card['data-slug'])
                first = pics[0].find('source')['srcset'].split(', ')[0]
                self.assertEqual(first, '../%s%s %dw' % (t['url'], cover['photo']['th'], core.thumb_width(cover['photo'])))
                self.assertTrue(os.path.isfile(os.path.join(self.tmp, t['slug'], cover['photo']['th'])))
                self.assertEqual(pics[0].find('img')['srcset'].count('.th.'), 0)
                self.assertEqual(html_.count(core.cover_img(t, HERE, self.trips_mod.TRX_SIZES)), 1)
        self.assertIn('west-couloir', wrapped)
        self.assertIn('tall-cover', wrapped)
        self.assertEqual(len(doc.find_all('picture')), len(wrapped))
        self.assertEqual(html_.count('.th.'), len(wrapped))
        self.assertEqual(doc.find('li', attrs={'data-slug': 'tall-cover'}).find('source')['srcset'],
                         ', '.join('../trips/tall-cover/photos/' + c for c in ('01.th.webp 320w', '01.sm.webp 600w', '01.webp 1200w')))
        for i in doc.find_all('img'):
            self.assertNotIn('.th.', (i['srcset'] or '') + (i['src'] or ''))
        self.assertEqual(doc.find('head').find_all('link', attrs={'rel': 'preload', 'as': 'image'}), [])      # trips/ preloads no image
        self.assertEqual(unwrap(html_), before)

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

    def test_cover_srcset_with_and_without_the_card_size_copy(self):
        # contract-phase4.md 5.3: content.load_trip records p['th'] when <name>.th.<ext> exists beside the photo. 10.5:
        # the <img>'s srcset is the two candidates it always was, with the file or without it (under 5.3 it started
        # with the copy); a card whose sizes string is a card's (it ends ', 112px') wraps the <img> in a <picture> whose
        # phone-only <source> lists the copy first, and any other string leaves the <img> bare
        card_sizes = '(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2), 112px'
        base = '../trips/west-couloir/photos/'
        two = '%s02.sm.webp 800w, %s02.webp 1600w' % (base, base)
        self.assertEqual([p['th'] for p in self.by['west-couloir']['photos']], [None, None])
        self.assertEqual(self.card('west-couloir').find('img')['srcset'], two)
        without = {sizes: core.trip_card(self.by['west-couloir'], HERE, sizes) for sizes in (SIZES, card_sizes)}
        helpers.touch(os.path.join(self.tmp, 'west-couloir', 'photos', '02.th.webp'))
        t = helpers.load(self.tmp, 'west-couloir')
        self.assertEqual([(p['file'], p['sm'], p['th']) for p in t['photos']],
                         [('photos/01.webp', None, None), ('photos/02.webp', 'photos/02.sm.webp', 'photos/02.th.webp')])
        self.assertEqual(t['cover']['photo']['th'], 'photos/02.th.webp')
        # SIZES ('..., 100vw') is not a card's string: the card is what it was, and names no .th file
        plain = core.trip_card(t, HERE, SIZES)
        self.assertEqual(plain, without[SIZES])
        img = Doc(plain).find('img')
        self.assertEqual(img['srcset'], two)
        self.assertEqual((img['src'], img['sizes'], img['alt']), (base + '02.webp', SIZES, 'The couloir'))
        self.assertEqual((img['width'], img['height']), ('1600', '1200'))     # the full file's size, whichever copy loads
        self.assertNotIn('.th.', plain)
        self.assertNotIn('<picture', plain)
        # at a card's string the same <img> sits in the wrapper, behind the source
        card = core.trip_card(t, HERE, card_sizes)
        doc = Doc(card)
        self.assertEqual([n.tag for n in doc.find('a', cls='tcard-img').elements()], ['picture'])
        self.assertEqual(doc.find('picture').classes, ['cover-pic'])
        self.assertEqual(doc.find('source')['srcset'], '%s02.th.webp 427w, %s' % (base, two))
        self.assertEqual((doc.find('source')['media'], doc.find('source')['sizes']), ('(max-width: 559.98px)', '106px'))
        self.assertEqual((doc.find('img')['srcset'], doc.find('img')['sizes']), (two, card_sizes))      # the <img> string: 112 px as before
        self.assertEqual(unwrap(card), without[card_sizes])
        self.assertEqual(card.count('.th.'), 1)
        # from another folder depth the three candidates of the source move together, and the two of the <img>
        doc = Doc(core.trip_card(t, 'trips/dana-couloir/', card_sizes))
        self.assertEqual(doc.find('source')['srcset'], ', '.join('../../trips/west-couloir/photos/' + c for c in ('02.th.webp 427w', '02.sm.webp 800w', '02.webp 1600w')))
        self.assertEqual(doc.find('img')['srcset'], ', '.join('../../trips/west-couloir/photos/' + c for c in ('02.sm.webp 800w', '02.webp 1600w')))
        # a portrait cover's copy is 320 px wide (the short edge)
        helpers.make_trip(self.tmp, 'tall-cover', title='Tall Cover', activity='hike', date='2023-02-02', track=True,
                          photos=[photo('photos/01.webp', PORTRAIT, alt='Tall', sm=True)])
        helpers.touch(os.path.join(self.tmp, 'tall-cover', 'photos', '01.th.webp'))
        tall = helpers.load(self.tmp, 'tall-cover')
        doc = Doc(core.trip_card(tall, HERE, card_sizes))
        self.assertEqual(doc.find('source')['srcset'], ', '.join('../trips/tall-cover/photos/' + c for c in ('01.th.webp 320w', '01.sm.webp 600w', '01.webp 1200w')))
        # ... which is why the source says 106 px: three times that is 318, within the 320 px of this copy
        self.assertEqual(doc.find('source')['sizes'], '106px')
        self.assertLessEqual(3 * int(doc.find('source')['sizes'][:-2]), 320)
        self.assertEqual(doc.find('img')['srcset'], ', '.join('../trips/tall-cover/photos/' + c for c in ('01.sm.webp 600w', '01.webp 1200w')))
        self.assertEqual(Doc(core.trip_card(tall, HERE, SIZES)).find_all('source'), [])

    def test_the_wrapper_changes_nothing_a_reader_or_a_keyboard_meets(self):
        # 10.5: <picture> and <source> are not interactive and carry no name, role or tab stop; they sit inside the card's
        # photo link, which was already hidden from assistive technology and skipped by the Tab key (the title link is
        # the card's name); the <img> keeps its alt text. So the card reads and tabs exactly as it did
        card_sizes = '(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2), 112px'
        plain = Doc(core.trip_card(self.by['west-couloir'], HERE, card_sizes)).find('li')
        helpers.touch(os.path.join(self.tmp, 'west-couloir', 'photos', '02.th.webp'))
        li = Doc(core.trip_card(helpers.load(self.tmp, 'west-couloir'), HERE, card_sizes)).find('li')
        pic = li.find('picture')
        self.assertIsNotNone(pic)
        link_ = pic.parent
        self.assertEqual((link_.tag, link_.classes, link_['tabindex'], link_['aria-hidden']), ('a', ['tcard-img'], '-1', 'true'))
        for node in [pic] + list(pic.walk()):
            self.assertIn(node.tag, ('picture', 'source', 'img'))
            for attr in ('tabindex', 'role', 'href', 'onclick', 'aria-label', 'aria-hidden', 'id'):
                self.assertNotIn(attr, node, '%r carries %s' % (node, attr))
        self.assertEqual([i['alt'] for i in pic.find_all('img')], ['The couloir'])
        self.assertNotIn('alt', pic.find('source'))
        # what a reader and the Tab key meet: the same links, in the same order, with the same names
        links = lambda root: [(a['href'], a['tabindex'], a['aria-hidden'], a['aria-describedby'], a.text()) for a in root.find_all('a')]   # noqa: E731
        self.assertEqual(links(li), links(plain))
        self.assertEqual(li.find('h3').text(), plain.find('h3').text())
        self.assertEqual([n.tag for n in li.walk() if n.tag not in ('picture', 'source')], [n.tag for n in plain.walk()])

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


# ---------------------------------------------------------------- Phase 5: "By region" links to a region's own page

def legacy_browse(mod, site):
    """trips.browse as it was at commit fb425ab (Phase 4), copied line for line: what the browse block was before a
    region could have a page of its own."""
    esc, link, here = core.esc, core.link, mod.HERE
    pub = site['published']
    acts = []
    for a, lab in core.NAV:
        k = sum(1 for t in pub if t['activity'] == a)
        if k:
            acts.append('<li><a href="%s">%s<span class="trx-bn">%s</span></a></li>' % (link(here, core.section_url(a)), esc(lab), mod.count_n(k)))
    regs = []
    for name, slug, k in mod.regions_of(pub):
        href = core.region_map_href(here, name) or ('?region=%s' % slug)
        regs.append('<li><a href="%s">%s<span class="trx-bn">%s</span></a></li>' % (href, esc(name), mod.count_n(k)))
    years = ''.join('<li><a href="#y-%d">%d</a></li>' % (y, y) for y in mod.years_of(pub))
    group = lambda lab, items: ('<div class="trx-bgroup"><span class="t-label">%s</span><ul>%s</ul></div>' % (lab, items)) if items else ''  # noqa: E731
    return ('<nav class="trx-browse wrap" aria-label="Browse">%s%s%s</nav>'
            % (group('By activity', ''.join(acts)), group('By region', ''.join(regs)), group('By year', years)))


class RegionLinkTests(ExplorerFixture):
    """contract-phase5.md section 2: a 'By region' browse link goes to regions/<slug>/ when the region has a page
    (core.region_page_href), else to its place on map/ as before, else to this page's own filter. Here Eastern Sierra
    has a region map and so a page, the Alps are on map/ without one, and the journal's region is on neither. With no
    site registered, or with one registered without a site meta (REVISED in round 2: what every test helper does), the
    block is byte for byte the old one (legacy_browse, a copy of the function body of fb425ab)."""

    def setUp(self):
        helpers.keep_state(self)              # the region page this class registers with core is gone afterwards
        super().setUp()
        self.trips_mod = load_trips_module(self)
        meta = {'hash': '', 'maps': {'region-eastern-sierra-%s' % size: {'w': 100, 'h': 80} for size in ('desktop', 'phone')},
                'regions': ['Eastern Sierra'], 'all_regions': ['Eastern Sierra', 'Alps', 'Lake Tahoe', 'Utah']}
        patcher = mock.patch.object(core, '_SITE_META', [meta])
        patcher.start()
        self.addCleanup(patcher.stop)
        self.meta = meta
        core.register_site(self.site, meta)   # with the site meta, as build.py does: without it no region has a page

    def region_links(self, html_):
        nav = Doc(html_).find('nav', cls='trx-browse')
        group = [g for g in nav.find_all('div', cls='trx-bgroup') if g.find('span', cls='t-label').text() == 'By region']
        self.assertEqual(len(group), 1)
        return [(a['href'], a.text()) for a in group[0].find_all('a')]

    def test_a_region_with_a_page_links_to_it_and_the_others_as_before(self):
        self.assertEqual(core._REGION_PAGES, {'Eastern Sierra': 'eastern-sierra'})
        self.assertEqual(self.region_links(self.trips_mod.browse(self.site)),
                         [('../regions/eastern-sierra/', 'Eastern Sierra, 4 reports'),           # its own page
                          ('../map/#region-alps', 'Alps, 2 reports'),                             # on map/, no region map: no page
                          ('?region=pacific-crest-trail', 'Pacific Crest Trail, 1 report')])      # on neither: this page's filter
        page = pages_by_url(self.trips_mod.build(self.site))['trips/'].html
        self.assertEqual(self.region_links(page), self.region_links(self.trips_mod.browse(self.site)))
        self.assertEqual(page.count(self.trips_mod.browse(self.site)), 1)

    def test_a_test_of_this_class_leaves_no_region_page_registered(self):
        helpers.assert_puts_core_back(self, RegionLinkTests('test_a_region_with_a_page_links_to_it_and_the_others_as_before'))

    def test_the_link_is_the_old_one_with_another_address(self):
        new, old = self.trips_mod.browse(self.site), legacy_browse(self.trips_mod, self.site)
        self.assertEqual(old.count('href="../map/#region-eastern-sierra"'), 1)
        self.assertEqual(new, old.replace('href="../map/#region-eastern-sierra"', 'href="../regions/eastern-sierra/"'))
        self.assertIn('<li><a href="../regions/eastern-sierra/">Eastern Sierra<span class="trx-bn">%s</span></a></li>' % self.trips_mod.count_n(4), new)

    def test_with_no_site_registered_the_block_is_byte_for_byte_the_old_one(self):
        core._REGION_PAGES.clear()
        self.assertEqual(self.trips_mod.browse(self.site), legacy_browse(self.trips_mod, self.site))
        self.assertEqual(self.region_links(self.trips_mod.browse(self.site)),
                         [('../map/#region-eastern-sierra', 'Eastern Sierra, 4 reports'), ('../map/#region-alps', 'Alps, 2 reports'),
                          ('?region=pacific-crest-trail', 'Pacific Crest Trail, 1 report')])
        self.assertNotIn('regions/', pages_by_url(self.trips_mod.build(self.site))['trips/'].html)

    def test_registered_without_a_site_meta_the_block_is_the_old_one_too(self):
        # REVISED in round 2: the explorer fixture's own way (helpers.make_site). The region map is still in core's
        # copy of the meta, and Eastern Sierra has no page for all that
        with_page = self.trips_mod.browse(self.site)
        for register in (lambda: core.register_site(self.site), lambda: helpers.make_site(self.site['trips'])):
            core.register_site(self.site, self.meta)
            self.assertEqual(core._REGION_PAGES, {'Eastern Sierra': 'eastern-sierra'})
            register()
            self.assertEqual(core._REGION_PAGES, {})
            self.assertIn('region-eastern-sierra-desktop', core.site_meta()['maps'])
            self.assertEqual(self.trips_mod.browse(self.site), legacy_browse(self.trips_mod, self.site))
            self.assertNotIn('regions/', pages_by_url(self.trips_mod.build(self.site))['trips/'].html)
        core.register_site(self.site, self.meta)
        self.assertEqual(self.trips_mod.browse(self.site), with_page)

    def test_the_count_beside_the_link_is_the_number_of_reports_the_region_page_lists(self):
        # REVISED in round 2: the page lists every report whose `region` is the name (core.region_pages), which is what
        # trips.regions_of counts for a region written one way
        (name, slug, ts), = core.region_pages(self.site, self.meta)
        self.assertEqual((name, slug), ('Eastern Sierra', 'eastern-sierra'))
        counted = dict((n, k) for n, _s, k in self.trips_mod.regions_of(self.site['published']))
        self.assertEqual(len([t for t in ts if t['kind'] != 'planned']), counted['Eastern Sierra'])
        self.assertEqual(counted['Eastern Sierra'], 4)
        self.assertIn(('../regions/eastern-sierra/', 'Eastern Sierra, 4 reports'), self.region_links(self.trips_mod.browse(self.site)))
        self.assertEqual(sorted(t['slug'] for t in ts if t['kind'] != 'planned'),
                         sorted(t['slug'] for t in self.site['published'] if t['region'] == 'Eastern Sierra'))

    def test_a_region_page_changes_that_one_link_on_the_whole_page(self):
        with_page = pages_by_url(self.trips_mod.build(self.site))
        core._REGION_PAGES.clear()
        without = pages_by_url(self.trips_mod.build(self.site))
        self.assertEqual(sorted(with_page), sorted(without))
        self.assertEqual(with_page['trips/'].html.count('regions/'), 1)
        self.assertEqual(with_page['trips/'].html.replace('href="../regions/eastern-sierra/"', 'href="../map/#region-eastern-sierra"'),
                         without['trips/'].html)
        for url in ('trips/search.json', 'trips/journal.json'):
            self.assertEqual(with_page[url].html, without[url].html)       # the search indexes know nothing of region pages
            self.assertNotIn('regions/', with_page[url].html)

    def test_without_any_region_map_no_link_changes(self):
        # the explorer fixture's own meta (no region map at all): a registered site without region pages
        plain = {'hash': '', 'maps': {}, 'regions': [], 'all_regions': list(REGIONS)}
        with mock.patch.object(core, '_SITE_META', [plain]):
            core.register_site(self.site, plain)
            self.assertEqual(core._REGION_PAGES, {})
            self.assertEqual(self.trips_mod.browse(self.site), legacy_browse(self.trips_mod, self.site))
            self.assertEqual([h for h, _t in self.region_links(self.trips_mod.browse(self.site))],
                             ['../map/#region-%s' % content.slugify(r) for r in REGIONS])

    def test_the_page_is_asked_for_by_the_name_the_link_shows(self):
        # trips.regions_of labels a region with the first spelling it meets; the page belongs to the name core recorded
        asked = []
        with mock.patch.object(core, 'region_page_href', lambda here, region: asked.append((here, region)) or None):
            html_ = self.trips_mod.browse(self.site)
        self.assertEqual(asked, [('trips/', r) for r in REGIONS])
        self.assertEqual(html_, legacy_browse(self.trips_mod, self.site))


if __name__ == '__main__':
    unittest.main()
