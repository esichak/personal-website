"""Phase 2T: the public tick list (sitegen.pages.ticklist.build -> tick-list/ and core.goal_card), the goal-page variant of
sitegen.pages.report.page, the report backlink, the publication boundary (goals stay out of published / RSS / search /
curation), the active-goal counts and the header's Tick list link.

A synthetic site in a temp dir: seven non-draft goals (kind: planned) across four regions and no region, in several
statuses and priorities, one archived, one completed with an outing linked to a synthetic published report, one legacy
planned route without goal.json, one with a track but no render, one with a rendered tile (a temp rendered folder), several
without a track; two published reports; one draft goal that must never appear. site['goals'], site['active_goals'] and
site['goal_backlinks'] are built here exactly as the contract describes build.py doing it. Page modules are imported in
setUp, so a missing module fails each test clearly instead of breaking discovery. core.region_map_href reads
rendered/site/meta.json; the fixture regions are patched into core's in-memory copy. Fixture slugs match no real trip.
"""
import hashlib
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
from helpers import Doc  # noqa: E402

HERE = 'tick-list/'
REGIONS = ['Alps', 'Boise', 'Eastern Sierra', 'Lake Tahoe']
GOALS = ['ridge-idea', 'couloir-short', 'alps-someday', 'done-traverse', 'old-archived', 'legacy-ridge', 'tile-goal']
ACTIVE = ['ridge-idea', 'couloir-short', 'alps-someday', 'legacy-ridge', 'tile-goal']
REPORTS = ['real-report', 'other-report']
PCT = 'trips/pacific-crest-trail-2024/'
SITE_LINKS = ['trips/', 'tick-list/', 'map/', 'about/', 'trips/#search']   # the fixture has no PCT series


def load_module(tc, name):
    try:
        return importlib.import_module(name)
    except ImportError as ex:
        tc.fail('%s is not importable: %s' % (name.replace('.', '/') + '.py', ex))


def option_values(select):
    return [o['value'] if o['value'] is not None else o.text() for o in select.find_all('option')]


def write_json(folder, name, data):
    with open(os.path.join(folder, name), 'w', encoding='utf-8') as fh:
        json.dump(data, fh)


def goal_site(trips, goals_mod):
    """The site dict as build.py makes it for Phase 2T: make_site plus goals, active_goals (goals.is_active) and
    goal_backlinks {report slug: [goal trips whose outings name it]}."""
    site = helpers.make_site(trips)
    site['goals'] = list(site['planned'])
    site['active_goals'] = [t for t in site['goals'] if goals_mod.is_active(t['goal'])]
    links = {}
    for t in site['goals']:
        for o in t['goal']['outings']:
            if o.get('report_slug'):
                links.setdefault(o['report_slug'], [])
                if t not in links[o['report_slug']]:
                    links[o['report_slug']].append(t)
    site['goal_backlinks'] = links
    return site


class TickListFixture(unittest.TestCase):

    def setUp(self):
        self.goals_mod = load_module(self, 'goals')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        meta = {'hash': '', 'maps': {}, 'regions': [], 'all_regions': list(REGIONS)}
        patcher = mock.patch.object(core, '_SITE_META', [meta])
        patcher.start()
        self.addCleanup(patcher.stop)
        g = self.goals_mod.defaults
        # Eastern Sierra: an idea without a track, and a high-priority shortlisted couloir with a published track (no render)
        helpers.make_trip(self.tmp, 'ridge-idea', title='Ridge Idea', activity='hike', kind='planned', region='Eastern Sierra',
                          body='Walk the whole crest in a day.')
        write_json(os.path.join(self.tmp, 'ridge-idea'), 'goal.json', dict(g(), added_at='2026-03-01', why='A long ridge I keep looking at.',
                                                                           tags=['ridge-traverse'], legacy=False))
        f = helpers.make_trip(self.tmp, 'couloir-short', title='Short Couloir', activity='ski', kind='planned', region='Eastern Sierra',
                              place='Synthetic Bowl', track=True, stats={'distance_km': 19.8, 'gain_m': 640, 'high_m': 3200},
                              body='Skin the apron, boot the choke.')
        track = b'<gpx version="1.1"><trk><trkseg><trkpt lat="38.9" lon="-120.1"/></trkseg></trk></gpx>\n'
        with open(os.path.join(f, 'track.gpx'), 'wb') as fh:
            fh.write(track)
        sha = hashlib.sha256(track).hexdigest()
        cs = g()
        cs.update(status='shortlisted', priority='high', added_at='2026-05-01', target_months=[4, 5], tags=['couloir'],
                  why='Steep and short.', time_commitment='full-day', route_scope='approach-only',
                  route_source={'kind': 'third-party-recording', 'url': 'https://example.test/rec', 'label': 'A recording',
                                'checked_at': '2026-05-01', 'public_copy_approved': True, 'approximation_note': None},
                  references=[{'id': 'guide-1', 'label': 'Synthetic guidebook', 'url': 'https://example.test/guide', 'checked_at': '2026-05-02'}],
                  field_evidence={'difficulty': {'source_ids': ['guide-1'], 'status': 'approved'},
                                  'season_notes': {'source_ids': ['guide-1'], 'status': 'approved'}},
                  difficulty={'system': 'Ski', 'value': 'D', 'note': 'Narrow choke.'}, season_notes='Usually filled in by April.',
                  checklist=[{'id': 'exit', 'text': 'Does the file include the exit?', 'done': False},
                             {'id': 'road', 'text': 'Is the road open in April?', 'done': True}],
                  route={'source_sha256': sha, 'method': 'ticklist-gpx-1', 'selected': {'type': 'trk', 'index': 0, 'name': None},
                         'alternatives': 1, 'segments': 1, 'points': 1, 'elevation': 'full', 'times': False, 'waypoints': 0})
        write_json(f, 'goal.json', cs)
        # Alps: a someday climb without a track, and a completed hike with an attempt and a completion linked to a report
        helpers.make_trip(self.tmp, 'alps-someday', title="Aiguille d'Example", activity='climb', kind='planned', region='Alps')
        write_json(os.path.join(self.tmp, 'alps-someday'), 'goal.json', dict(g(), status='researching', priority='someday', added_at='2026-01-15',
                                                                             why='Granite.'))
        helpers.make_trip(self.tmp, 'done-traverse', title='Done Traverse', activity='hike', kind='planned', region='Alps', body='Plan notes.')
        write_json(os.path.join(self.tmp, 'done-traverse'), 'goal.json', dict(g(), status='completed', added_at='2025-11-01',
                                                                              outings=[{'outcome': 'attempted', 'date': '2026-07-12', 'report_slug': None, 'note': 'Turned around.'},
                                                                                       {'outcome': 'completed', 'date': '2026-08-30', 'report_slug': 'real-report', 'note': ''}]))
        # no region: an archived mtb goal
        helpers.make_trip(self.tmp, 'old-archived', title='Old Archived Loop', activity='mtb', kind='planned')
        write_json(os.path.join(self.tmp, 'old-archived'), 'goal.json', dict(g(), status='researching', archived=True, added_at='2024-02-02'))
        # Lake Tahoe: a legacy planned route (no goal.json) with a track and front-matter stats, no render
        helpers.make_trip(self.tmp, 'legacy-ridge', title='Legacy Ridge', activity='ski', kind='planned', region='Lake Tahoe', track=True,
                          stats={'distance_km': 8.0})
        # Boise: a hike with a rendered tile (temp rendered folder), no track in content (tile comes from the render)
        helpers.make_trip(self.tmp, 'tile-goal', title='Tile Goal', activity='hike', kind='planned', region='Boise', track=True)
        write_json(os.path.join(self.tmp, 'tile-goal'), 'goal.json', dict(g(), added_at='2026-06-01'))
        # published reports, and a draft goal that must never appear
        helpers.make_trip(self.tmp, 'real-report', title='A Real Synthetic Report', activity='hike', date='2026-08-30', region='Alps', track=True,
                          body='Walked it in a day.')
        helpers.make_trip(self.tmp, 'other-report', title='Other Report', activity='ski', date='2026-02-01', region='Eastern Sierra', track=True)
        helpers.make_trip(self.tmp, 'draft-goal', title='Draft Goal', activity='hike', kind='planned', draft=True, region='Utah')
        self.trips = helpers.load_dir(self.tmp)
        self.by = {t['slug']: t for t in self.trips}
        rdir = os.path.join(self.tmp, '_rendered', 'tile-goal')
        helpers.touch(os.path.join(rdir, 'tile.svg.html'))
        self.by['tile-goal']['rendered'] = rdir
        self.site = goal_site(self.trips, self.goals_mod)


# ---------------------------------------------------------------- the tick-list/ page

class TickListPageTests(TickListFixture):

    def setUp(self):
        super().setUp()
        self.mod = load_module(self, 'sitegen.pages.ticklist')
        pages = self.mod.build(self.site)
        by_url = {p.url: p for p in pages}
        self.assertIn(HERE, by_url)
        self.page = by_url[HERE]
        self.doc = Doc(self.page.html)
        self.main = self.doc.by_id('main')
        self.form = self.doc.by_id('search')

    def card(self, slug):
        return self.main.find('li', attrs={'data-slug': slug})

    def cards(self):
        return self.main.find_all('li', cls='gcard')

    def selects(self):
        return {s['name']: s for s in self.form.find_all('select')}

    def radios(self, attr):
        return [b for b in self.form.find_all('button', attrs={'role': 'radio'}) if b[attr] is not None]

    def test_page_identity(self):
        self.assertEqual(self.page.title, 'Tick list')
        self.assertTrue(self.page.index)
        self.assertTrue(self.page.html.lstrip().lower().startswith('<!doctype html>'))
        h1s = self.doc.find_all('h1')
        self.assertEqual(len(h1s), 1)
        self.assertEqual(h1s[0].text(), 'Tick list')
        self.assertIn('Routes and objectives I’d like to get to.', self.main.text())

    def test_summary_counts_come_from_the_data(self):
        text = self.main.text()
        self.assertIn('5 ACTIVE', text)
        self.assertIn('1 SHORTLISTED', text)
        self.assertIn('1 COMPLETED', text)
        self.assertEqual(len(self.site['active_goals']), 5)
        self.assertEqual(sorted(helpers.slugs(self.site['active_goals'])), sorted(ACTIVE))

    def test_summary_shows_zeros(self):
        site = goal_site([self.by[s] for s in ('ridge-idea', 'real-report')], self.goals_mod)
        doc = Doc({p.url: p for p in self.mod.build(site)}[HERE].html)
        text = doc.by_id('main').text()
        self.assertIn('1 ACTIVE', text)
        self.assertIn('0 SHORTLISTED', text)
        self.assertIn('0 COMPLETED', text)

    def test_every_goal_is_a_card_once_and_nothing_else_is(self):
        self.assertEqual(sorted(c['data-slug'] for c in self.cards()), sorted(GOALS))
        hrefs = sorted(h.find('a')['href'] for h in self.main.find_all('h3', cls='gcard-t'))
        self.assertEqual(hrefs, sorted('../trips/%s/' % s for s in GOALS))
        for s in REPORTS + ['draft-goal']:
            self.assertIsNone(self.card(s), s)
            self.assertNotIn('trips/%s/' % s, self.page.html)
        for word in ('Draft Goal', 'Utah', 'A Real Synthetic Report'):
            self.assertNotIn(word, self.main.text())

    def test_count_line_and_status_row(self):
        count = self.doc.by_id('tkl-count')
        self.assertEqual(count.tag, 'p')
        self.assertIn('t-mono-s', count.classes)
        self.assertEqual(count['aria-live'], 'polite')
        self.assertEqual(count.text(), '7 GOALS')
        chips = self.doc.by_id('tkl-chips')
        self.assertEqual(chips.tag, 'ul')
        self.assertEqual(chips.elements(), [])
        clear = self.doc.by_id('tkl-clear')
        self.assertEqual((clear.tag, clear['type']), ('button', 'button'))
        self.assertIn('hidden', clear)
        none = self.doc.by_id('tkl-none')
        self.assertIn('empty', none.classes)
        self.assertIn('hidden', none)

    def test_form_is_server_rendered_hidden_with_a_labelled_search_input(self):
        form = self.form
        self.assertEqual(form.tag, 'form')
        self.assertIn('tkl-form', form.classes)
        self.assertEqual(form['role'], 'search')
        self.assertIn('hidden', form)
        self.assertNotIn(form['method'] or 'get', ('post', 'POST'))
        q = form.by_id('tkl-q')
        self.assertEqual(q.tag, 'input')
        self.assertEqual(q['name'], 'q')
        self.assertIn(q['type'] or 'text', ('text', 'search'))
        labels = [l for l in self.doc.find_all('label') if l['for'] == 'tkl-q']
        self.assertTrue(labels or q['aria-label'], 'the search input must be labelled')

    def test_activity_chips_only_for_activities_with_a_goal(self):
        radios = self.radios('data-filter')
        self.assertEqual(radios[0]['data-filter'], 'all')
        self.assertEqual({b['data-filter'] for b in radios}, {'all', 'ski', 'climb', 'hike', 'mtb'})
        for b in radios:
            self.assertIn('fchip', b.classes, repr(b))
        self.assertEqual({c['data-act'] for c in self.cards()}, {b['data-filter'] for b in radios} - {'all'})

    def test_selects_match_the_cards(self):
        sel = self.selects()
        for name in ('region', 'status', 'priority', 'month', 'sort'):
            self.assertIn(name, sel, name)
        regions = option_values(sel['region'])
        self.assertEqual(regions[0], '')
        self.assertEqual(set(regions) - {''}, {c['data-region'] for c in self.cards()} - {''})
        self.assertEqual(regions[1:], [content.slugify(r) for r in REGIONS])   # A-Z
        statuses = option_values(sel['status'])
        self.assertEqual(statuses[0], '')
        self.assertTrue(set(statuses) - {''} <= set(self.goals_mod.STATUSES))
        self.assertTrue({c['data-status'] for c in self.cards()} <= set(statuses))
        prios = option_values(sel['priority'])
        self.assertTrue(set(prios) - {''} <= set(self.goals_mod.PRIORITIES))
        self.assertTrue({c['data-priority'] for c in self.cards()} <= set(prios))
        months = option_values(sel['month'])
        self.assertEqual(months[0], '')
        self.assertTrue(set(months) - {''} <= {str(m) for m in range(1, 13)})
        for m in ('4', '5'):
            self.assertIn(m, months)
        for o in sel['month'].find_all('option')[1:]:
            self.assertRegex(o.text(), r'^(January|February|March|April|May|June|July|August|September|October|November|December)$')
        self.assertEqual(option_values(sel['sort']), ['priority', 'added', 'name'])

    def test_gpx_scope_and_view_controls(self):
        self.assertIn('Has a route (GPX)', self.form.text())
        scopes = self.radios('data-scope')
        self.assertEqual({b['data-scope'] for b in scopes}, {'all', 'active', 'shortlisted', 'completed', 'archived'})
        checked = [b['data-scope'] for b in scopes if b['aria-checked'] == 'true']
        self.assertEqual(checked, ['active'])
        views = self.radios('data-view')
        self.assertEqual([b['data-view'] for b in views], ['cards', 'list'])

    def test_no_checkbox_input_anywhere_on_the_page(self):
        self.assertEqual(self.doc.find_all('input', attrs={'type': 'checkbox'}), [])
        for inp in self.doc.find_all('input'):
            self.assertIn(inp['type'], ('text', 'search', 'radio', None), repr(inp))

    def test_noscript_note(self):
        ns = self.doc.find('noscript')
        self.assertIsNotNone(ns)
        self.assertIn('JavaScript', ns.text())

    def test_region_sections_a_to_z_with_no_region_last(self):
        secs = [s for s in self.main.find_all('section', cls='tkl-region')]
        self.assertEqual(len(secs), 5)
        self.assertEqual([s['data-region'] for s in secs[:4]], [content.slugify(r) for r in REGIONS])
        for s, name in zip(secs[:4], REGIONS):
            h2 = s.find('h2')
            self.assertEqual(h2['id'], 'region-' + content.slugify(name))
            self.assertEqual(h2.text(), name)
            grid = s.find('ul', cls='tkl-grid')
            self.assertIn('tgrid', grid.classes)
            for c in grid.find_all('li', cls='gcard'):
                self.assertEqual(c['data-region'], content.slugify(name))
        last = secs[-1]
        self.assertEqual(last.find('h2').text(), 'No region yet')
        self.assertTrue((last.find('h2')['id'] or '').startswith('region-'))
        self.assertNotIn(last['data-region'], [content.slugify(r) for r in REGIONS])
        self.assertEqual([c['data-slug'] for c in last.find_all('li', cls='gcard')], ['old-archived'])
        self.assertEqual([c['data-region'] for c in last.find_all('li', cls='gcard')], [''])
        es = secs[2]
        self.assertEqual([c['data-slug'] for c in es.find_all('li', cls='gcard')], ['couloir-short', 'ridge-idea'])   # high priority first

    def test_region_anchor_ids_are_unique(self):
        ids = [h['id'] for h in self.main.find_all('h2') if (h['id'] or '').startswith('region-')]
        self.assertEqual(len(ids), len(set(ids)))

    def test_sorted_container(self):
        sec = self.doc.by_id('tkl-sorted-sec')
        self.assertEqual(sec.tag, 'section')
        self.assertIn('hidden', sec)
        self.assertIsNotNone(sec.find('h2'))
        self.assertEqual(sec.find('ul').elements(), [])

    def test_links_are_relative(self):
        for a in self.doc.find_all('a'):
            self.assertFalse((a['href'] or '').startswith('/'), a['href'])
        for a in self.main.find_all('a'):
            href = a['href'] or ''
            if href.startswith('#') or href.startswith('http'):
                continue
            self.assertTrue(href.startswith('../'), href)

    def test_header_marks_tick_list_as_the_current_page(self):
        nav = self.doc.find('nav', attrs={'aria-label': 'Main'})
        cur = [(a['href'], a['aria-current']) for a in nav.find_all('a') if a['aria-current']]
        self.assertEqual(cur, [('../tick-list/', 'page')])
        self.assertIn('p-ticklist', self.doc.find('body').classes)

    def test_page_without_goals_still_builds(self):
        site = goal_site([self.by[s] for s in REPORTS], self.goals_mod)
        pages = {p.url: p for p in self.mod.build(site)}
        self.assertIn(HERE, pages)
        doc = Doc(pages[HERE].html)
        self.assertEqual(doc.find_all('li', cls='gcard'), [])
        text = doc.by_id('main').text()
        self.assertIn('0 ACTIVE', text)
        self.assertIn('0 GOALS', doc.by_id('tkl-count').text())


# ---------------------------------------------------------------- core.goal_card and core.goal_tags

class GoalCardTests(TickListFixture):

    def setUp(self):
        super().setUp()
        for name in ('goal_card', 'goal_tags'):
            if not hasattr(core, name):
                self.fail('core.%s is not implemented' % name)

    def card(self, slug, here=HERE):
        return Doc(core.goal_card(self.by[slug], here)).find('li')

    def test_root_li_and_data_attributes(self):
        li = self.card('couloir-short')
        self.assertIn('gcard', li.classes)
        self.assertEqual(li['data-slug'], 'couloir-short')
        self.assertEqual(li['data-act'], 'ski')
        self.assertEqual(li['data-region'], 'eastern-sierra')
        self.assertEqual(li['data-status'], 'shortlisted')
        self.assertEqual(li['data-priority'], 'high')
        self.assertEqual(li['data-months'], '4 5')
        self.assertEqual(li['data-gpx'], '1')
        self.assertEqual(li['data-archived'], '0')
        self.assertEqual(li['data-added'], '2026-05-01')

    def test_data_attributes_of_the_other_goals(self):
        idea = self.card('ridge-idea')
        self.assertEqual((idea['data-status'], idea['data-priority'], idea['data-months'], idea['data-gpx'], idea['data-archived']),
                         ('idea', 'normal', '', '0', '0'))
        arch = self.card('old-archived')
        self.assertEqual((arch['data-region'], arch['data-archived'], arch['data-status'], arch['data-act']), ('', '1', 'researching', 'mtb'))
        done = self.card('done-traverse')
        self.assertEqual((done['data-status'], done['data-gpx'], done['data-added']), ('completed', '0', '2025-11-01'))
        legacy = self.card('legacy-ridge')
        self.assertEqual((legacy['data-status'], legacy['data-priority'], legacy['data-gpx'], legacy['data-added'], legacy['data-region']),
                         ('idea', 'normal', '1', '', 'lake-tahoe'))

    def test_data_text_is_normalised_searchable_text(self):
        text = self.card('couloir-short')['data-text']
        self.assertRegex(text, r'^[a-z0-9]+( [a-z0-9]+)*$')
        for word in ('short', 'couloir', 'synthetic', 'bowl', 'eastern', 'sierra', 'steep'):
            self.assertIn(word, text.split())
        alps = self.card('alps-someday')['data-text']
        self.assertIn('aiguille', alps.split())
        self.assertIn('example', alps.split())
        self.assertIn('granite', alps.split())
        self.assertNotIn("'", alps)
        self.assertIn('ridge', self.card('ridge-idea')['data-text'].split())   # the tag

    def test_media_uses_the_route_tile_when_rendered(self):
        t = self.by['tile-goal']
        self.assertTrue(core.tile(t, HERE))
        li = self.card('tile-goal')
        a = li.find('a', cls='gcard-map')
        self.assertIsNotNone(a)
        self.assertEqual((a['href'], a['tabindex'], a['aria-hidden']), ('../trips/tile-goal/', '-1', 'true'))
        img = a.find('img')
        self.assertEqual(img['src'], '../trips/tile-goal/tile.svg')
        self.assertEqual(img['alt'], '')
        self.assertIsNone(li.find(cls='gcard-map--none'))

    def test_media_fallback_map_not_rendered_yet(self):
        for slug in ('couloir-short', 'legacy-ridge'):
            li = self.card(slug)
            div = li.find('div', cls='gcard-map')
            self.assertIsNotNone(div, slug)
            self.assertIn('gcard-map--none', div.classes)
            self.assertIn('map not rendered yet', div.text().lower())
            self.assertEqual(li.find_all('img'), [])

    def test_media_fallback_route_not_added_yet(self):
        for slug in ('ridge-idea', 'alps-someday', 'old-archived', 'done-traverse'):
            div = self.card(slug).find('div', cls='gcard-map')
            self.assertIsNotNone(div, slug)
            self.assertIn('gcard-map--none', div.classes)
            self.assertIn('route not added yet', div.text().lower())

    def test_meta_line_title_link_and_describedby(self):
        li = self.card('couloir-short')
        meta = li.find('p', cls='gcard-meta')
        self.assertEqual(meta['id'], 'gc-couloir-short-m')
        self.assertIn('t-mono-s', meta.classes)
        text = meta.text().upper()
        self.assertTrue('SYNTHETIC BOWL' in text or 'EASTERN SIERRA' in text, text)
        self.assertTrue('SKI' in text, text)
        a = li.find('h3', cls='gcard-t').find('a')
        self.assertEqual(a['href'], '../trips/couloir-short/')
        self.assertEqual(a['aria-describedby'], 'gc-couloir-short-m')
        self.assertEqual(a.text(), 'Short Couloir')
        self.assertIn('ALPS', self.card('alps-someday').find('p', cls='gcard-meta').text().upper())
        self.assertEqual(self.card('alps-someday').find('h3').find('a').text(), "Aiguille d'Example")

    def test_title_link_is_relative_to_here(self):
        self.assertEqual(self.card('ridge-idea', here='').find('h3').find('a')['href'], 'trips/ridge-idea/')
        self.assertEqual(self.card('ridge-idea', here='trips/x/').find('h3').find('a')['href'], '../../trips/ridge-idea/')

    def test_tags_show_status_priority_and_archived(self):
        tags = self.card('couloir-short').find(cls='gcard-tags')
        words = [t.text() for t in tags.find_all(cls='tag')]
        self.assertEqual(words, ['Shortlisted', 'High priority'])
        self.assertEqual([t.text() for t in self.card('alps-someday').find(cls='gcard-tags').find_all(cls='tag')], ['Researching', 'Someday'])
        self.assertEqual([t.text() for t in self.card('old-archived').find(cls='gcard-tags').find_all(cls='tag')], ['Researching', 'Archived'])
        self.assertEqual([t.text() for t in self.card('done-traverse').find(cls='gcard-tags').find_all(cls='tag')], ['Completed'])
        self.assertEqual([t.text() for t in self.card('ridge-idea').find(cls='gcard-tags').find_all(cls='tag')], ['Idea'])
        self.assertNotIn('Normal priority', core.goal_card(self.by['ridge-idea'], HERE))

    def test_goal_tags_helper(self):
        g = self.goals_mod.defaults()
        self.assertEqual([t.text() for t in Doc(core.goal_tags(g)).find_all(cls='tag')], ['Idea'])
        g.update(status='attempted', priority='someday', archived=True)
        self.assertEqual([t.text() for t in Doc(core.goal_tags(g)).find_all(cls='tag')], ['Attempted', 'Someday', 'Archived'])
        g.update(status='completed', priority='high', archived=False)
        self.assertEqual([t.text() for t in Doc(core.goal_tags(g)).find_all(cls='tag')], ['Completed', 'High priority'])

    def test_approximate_stats_line(self):
        text = self.card('couloir-short').text()
        self.assertIn('≈ 12.3 MI', text)
        self.assertIn('≈ 2,100 FT GAIN', text)
        self.assertIn('≈ 19.8 KM', text)   # the km alternative through core.U
        self.assertNotIn('MOVING', text)

    def test_stats_line_omits_unknown_gain_and_says_route_not_added(self):
        legacy = self.card('legacy-ridge').text()
        self.assertIn('≈ 5.0 MI', legacy)
        self.assertNotIn('GAIN', legacy)
        for slug in ('ridge-idea', 'alps-someday'):
            text = self.card(slug).text()
            self.assertIn('ROUTE NOT ADDED', text)
            self.assertNotIn('MI', text.replace('MIN', ''))

    def test_view_goal_link(self):
        a = self.card('ridge-idea').find('a', cls='gcard-go')
        self.assertIsNotNone(a)
        self.assertIn('alink', a.classes)
        self.assertEqual(a['href'], '../trips/ridge-idea/')
        self.assertTrue(a.text().startswith('View goal'))

    def test_card_has_no_inputs(self):
        for slug in GOALS:
            self.assertEqual(Doc(core.goal_card(self.by[slug], HERE)).find_all('input'), [], slug)


# ---------------------------------------------------------------- goal pages (report.page for kind: planned)

class GoalPageTests(TickListFixture):

    def setUp(self):
        super().setUp()
        self.report = load_module(self, 'sitegen.pages.report')
        self.pages = {}

    def page(self, slug):
        if slug not in self.pages:
            self.pages[slug] = self.report.page(self.by[slug], self.site)
        return self.pages[slug]

    def doc(self, slug):
        return Doc(self.page(slug).html)

    def headings(self, slug):
        return [h.text() for h in self.doc(slug).by_id('main').find_all('h2')]

    def test_breadcrumb_says_tick_list_not_reports(self):
        crumbs = self.doc('couloir-short').find('nav', attrs={'aria-label': 'Breadcrumb'})
        links = [(a.text(), a['href']) for a in crumbs.find_all('a')]
        self.assertEqual(links[0], ('Tick list', '../../tick-list/'))
        self.assertNotIn('Reports', [t for t, _ in links])

    def test_chips_carry_planned_route_and_the_goal_tags(self):
        chips = self.doc('couloir-short').find(cls='rep-chips')
        words = [t.text() for t in chips.find_all(cls='tag')]
        self.assertIn('Planned route', words)
        self.assertIn('Shortlisted', words)
        self.assertIn('High priority', words)
        self.assertIn('Completed', [t.text() for t in self.doc('done-traverse').find(cls='rep-chips').find_all(cls='tag')])
        self.assertIn('Archived', [t.text() for t in self.doc('old-archived').find(cls='rep-chips').find_all(cls='tag')])

    def test_title_value_slot_shows_the_approximate_distance(self):
        head = self.doc('couloir-short').find(cls='rep-title').text()
        self.assertIn('≈', head)
        self.assertIn('12.3 MI', head)
        self.assertNotIn('≈', self.doc('ridge-idea').find(cls='rep-title').text())

    def test_actions(self):
        actions = self.doc('couloir-short').find(cls='rep-actions')
        texts = [a.text() for a in actions.find_all('a')]
        self.assertIn('Download planned GPX', texts)
        self.assertIn('Planning notes', texts)
        dl = next(a for a in actions.find_all('a') if a.text() == 'Download planned GPX')
        self.assertEqual(dl['href'], 'couloir-short.gpx')
        self.assertIn('download', dl)
        notes = next(a for a in actions.find_all('a') if a.text() == 'Planning notes')
        self.assertEqual(notes['href'], '#report')
        self.assertNotIn('Read the report', texts)
        self.assertNotIn('Download GPX', texts)
        idea = [a.text() for a in self.doc('alps-someday').find(cls='rep-actions').find_all('a')]
        self.assertNotIn('Download planned GPX', idea)   # no track, no download
        self.assertNotIn('Planning notes', idea)         # no body

    def test_stats_strip_shows_only_known_approximate_values(self):
        doc = self.doc('couloir-short')
        strip = doc.find('dl', cls='strip')
        self.assertIsNotNone(strip)
        labels = [d.text() for d in strip.find_all('dt')]
        self.assertEqual(labels, ['Distance', 'Gain', 'High point'])
        self.assertNotIn('Moving', labels)
        text = strip.text()
        self.assertIn('≈', text)
        self.assertIn('12.3', text)
        self.assertIn('2,100', text)
        note = doc.find(cls='strip-note').text()
        self.assertIn('Approximate', note)
        self.assertIn('planned route', note)
        self.assertIn('recording', note)   # third-party recording
        self.assertIn('approach', note)    # approach only
        self.assertNotIn('Strava', note)

    def test_stats_strip_without_gain_for_a_legacy_goal(self):
        strip = self.doc('legacy-ridge').find('dl', cls='strip')
        self.assertIsNotNone(strip)
        self.assertEqual([d.text() for d in strip.find_all('dt')], ['Distance'])
        self.assertIsNone(self.doc('ridge-idea').find('dl', cls='strip'))

    def test_map_fallbacks(self):
        doc = self.doc('couloir-short')
        sec = doc.by_id('map')
        self.assertIsNotNone(sec)
        empty = sec.find(cls='empty')
        self.assertIsNotNone(empty)
        self.assertIn('Map not rendered yet', empty.text())
        empty = self.doc('ridge-idea').by_id('map').find(cls='empty')
        self.assertIn('No route added yet', empty.text())

    def test_planning_notes_section_never_trip_report(self):
        doc = self.doc('couloir-short')
        sec = doc.by_id('report')
        self.assertIsNotNone(sec)
        self.assertEqual(sec.find('h2').text(), 'Planning notes')
        self.assertIn('Skin the apron, boot the choke.', sec.text())
        for slug in GOALS:
            html_ = self.page(slug).html
            self.assertNotIn('Trip report', html_, slug)
            self.assertNotIn('recording of Eric', html_, slug)
            self.assertNotIn("Eric's recording", html_, slug)
            self.assertNotIn('Stats from the GPS recording', html_, slug)
            self.assertNotIn('Track:', Doc(html_).by_id('main').text(), slug)
        self.assertIsNone(self.doc('alps-someday').by_id('report'))   # no body: no section

    def test_why_section(self):
        doc = self.doc('couloir-short')
        self.assertIn('Why', self.headings('couloir-short'))
        self.assertIn('Steep and short.', doc.by_id('main').text())
        self.assertNotIn('Why', self.headings('legacy-ridge'))

    def test_season_and_commitment_with_sources(self):
        doc = self.doc('couloir-short')
        self.assertIn('Season and commitment', self.headings('couloir-short'))
        text = doc.by_id('main').text()
        self.assertIn('Usually filled in by April.', text)
        self.assertIn('Full day', text)
        self.assertIn('D (Ski)', text)
        self.assertIn('Narrow choke.', text)
        self.assertNotIn('Season and commitment', self.headings('ridge-idea'))

    def test_route_source_and_references(self):
        doc = self.doc('couloir-short')
        self.assertIn('Route source', self.headings('couloir-short'))
        self.assertIn('References', self.headings('couloir-short'))
        hrefs = [a['href'] for a in doc.by_id('main').find_all('a')]
        self.assertIn('https://example.test/rec', hrefs)
        self.assertIn('https://example.test/guide', hrefs)
        text = doc.by_id('main').text()
        self.assertIn('recording', text.lower())
        self.assertIn('approach', text.lower())
        self.assertIn('Synthetic guidebook', text)
        self.assertRegex(text, r'May 2, 2026|2026-05-02|MAY 2, 2026')
        self.assertNotIn('References', self.headings('ridge-idea'))

    def test_checklist_is_read_only(self):
        doc = self.doc('couloir-short')
        self.assertIn('Still to check', self.headings('couloir-short'))
        sec = doc.by_id('checklist') or next(s for s in doc.by_id('main').find_all('section') if 'Still to check' in s.text())
        text = sec.text()
        self.assertIn('Does the file include the exit?', text)
        self.assertIn('Is the road open in April?', text)
        self.assertIn('Done', text)
        self.assertIn('To check', text)
        self.assertEqual(sec.find_all('input'), [])
        self.assertEqual(doc.find_all('input', attrs={'type': 'checkbox'}), [])
        for slug in GOALS:
            self.assertEqual(Doc(self.page(slug).html).find_all('input', attrs={'type': 'checkbox'}), [], slug)

    def test_outings_section_with_report_link_date_and_undated_attempt(self):
        doc = self.doc('done-traverse')
        hs = self.headings('done-traverse')
        self.assertIn('Outings', hs)
        self.assertLess(hs.index('Outings'), hs.index('Planning notes'))   # a completed goal leads with its outings
        main = doc.by_id('main')
        sec = next(s for s in main.find_all('section') if s.find('h2') and s.find('h2').text() == 'Outings')
        text = sec.text()
        self.assertIn('Completed', text)
        self.assertIn('Attempted', text)
        self.assertIn('Turned around.', text)
        self.assertRegex(text, r'(?i)aug 30, 2026|2026-08-30|august 30, 2026')
        link = next(a for a in sec.find_all('a') if 'real-report' in (a['href'] or ''))
        self.assertEqual(link['href'], '../../trips/real-report/')   # core.link from trips/done-traverse/
        self.assertEqual(link.text(), 'A Real Synthetic Report')
        self.assertNotIn('Outings', self.headings('ridge-idea'))

    def test_outing_without_a_date_says_so(self):
        t = dict(self.by['done-traverse'])
        g = json.loads(json.dumps(t['goal']))
        g['outings'] = [{'outcome': 'completed', 'date': None, 'report_slug': None, 'note': ''}]
        t['goal'] = g
        doc = Doc(self.report.page(t, self.site).html)
        self.assertIn('date not recorded', doc.by_id('main').text().lower())

    def test_pager_leads_back_to_the_tick_list(self):
        doc = self.doc('ridge-idea')
        pager = doc.find('nav', cls='pager')
        self.assertIsNotNone(pager)
        self.assertIn('Back to the tick list', pager.text())
        self.assertIn('../../tick-list/', [a['href'] for a in pager.find_all('a')])

    def test_header_marks_tick_list_true_and_trips_nothing(self):
        nav = self.doc('ridge-idea').find('nav', attrs={'aria-label': 'Main'})
        cur = [(a['href'], a['aria-current']) for a in nav.find_all('a') if a['aria-current']]
        self.assertEqual(cur, [('../../tick-list/', 'true')])

    def test_completed_and_archived_goals_keep_their_pages_and_gpx(self):
        urls = [p.url for p in self.report.build(self.site)]
        for slug in GOALS:
            self.assertIn('trips/%s/' % slug, urls, slug)
        self.assertNotIn('trips/draft-goal/', urls)
        self.assertTrue(self.by['couloir-short']['track'])
        self.assertEqual(self.by['couloir-short']['url'], 'trips/couloir-short/')

    def test_legacy_goal_renders_with_defaults(self):
        doc = self.doc('legacy-ridge')
        self.assertIn('Idea', [t.text() for t in doc.find(cls='rep-chips').find_all(cls='tag')])
        self.assertIn('Map not rendered yet', doc.by_id('map').text())
        self.assertIn('Download planned GPX', [a.text() for a in doc.find(cls='rep-actions').find_all('a')])

    def test_report_backlink(self):
        doc = Doc(self.report.page(self.by['real-report'], self.site).html)
        main = doc.by_id('main')
        line = next((p for p in main.find_all('p') if 'On the tick list' in p.text()), None)
        self.assertIsNotNone(line, 'the referenced report has no "On the tick list" line')
        a = line.find('a')
        self.assertEqual(a['href'], '../../trips/done-traverse/')   # core.link from trips/real-report/
        self.assertEqual(a.text(), 'Done Traverse')
        other = Doc(self.report.page(self.by['other-report'], self.site).html)
        self.assertNotIn('On the tick list', other.by_id('main').text())
        self.assertIn('Trip report', self.report.page(self.by['real-report'], self.site).html)   # reports keep their heading


# ---------------------------------------------------------------- publication boundary and counts

class BoundaryTests(TickListFixture):

    def test_goals_are_not_published(self):
        self.assertEqual(sorted(helpers.slugs(self.site['published'])), sorted(REPORTS))
        self.assertEqual(sorted(helpers.slugs(self.site['goals'])), sorted(GOALS))
        self.assertEqual(sorted(helpers.slugs(self.site['planned'])), sorted(GOALS))

    def test_rss_feed_has_no_goals(self):
        build = load_module(self, 'build')
        xml = build.feed(self.site['trips'])
        for slug in GOALS:
            self.assertNotIn('trips/%s/' % slug, xml)
        for title in ('Short Couloir', 'Ridge Idea', 'Done Traverse', 'Legacy Ridge'):
            self.assertNotIn(title, xml)
        self.assertEqual(xml.count('<item>'), 2)

    def test_search_index_has_no_goals(self):
        search = load_module(self, 'sitegen.search')
        slugs_ = [e['s'] for e in search.build_index(self.site)]
        self.assertEqual(sorted(slugs_), sorted(REPORTS))
        self.assertNotIn('Short Couloir', search.dumps(search.build_index(self.site)))

    def test_curation_rejects_a_goal_as_a_feature(self):
        """tests/test_curation.py::test_planned_slug_raises_saying_planned covers the rule; this pins it for a goal."""
        curation = load_module(self, 'sitegen.curation')
        with self.assertRaises(curation.CurationError) as cm:
            curation.resolve_featured(self.site, {'featured_slugs': ['couloir-short']}, trips_dir=self.tmp)
        self.assertIn('planned', str(cm.exception).lower())

    def test_active_goals_exclude_completed_and_archived(self):
        active = sorted(helpers.slugs(self.site['active_goals']))
        self.assertEqual(active, sorted(ACTIVE))
        for slug in ('done-traverse', 'old-archived'):
            self.assertFalse(self.goals_mod.is_active(self.by[slug]['goal']), slug)
            self.assertIn(slug, helpers.slugs(self.site['goals']))   # still a goal with a page

    def test_count_items_counts_active_goals_only(self):
        items = [x.replace('\xa0', ' ') for x in core.count_items(self.site['published'], self.site['active_goals'])]
        self.assertEqual(items[0], '2 REPORTS')
        self.assertEqual(items[-1], '+ 5 PLANNED ROUTES')
        self.assertNotIn('7 PLANNED', ' '.join(items))

    def test_hiking_page_planned_block_lists_active_goals_only(self):
        section = load_module(self, 'sitegen.pages.section')
        doc = Doc(section.page('hike', self.site).html)
        main = doc.by_id('main')
        hrefs = [a['href'] or '' for a in main.find_all('a')]
        for slug in ('ridge-idea', 'tile-goal'):
            self.assertIn('../trips/%s/' % slug, hrefs, slug)
        self.assertNotIn('../trips/done-traverse/', hrefs)   # completed: not a future route
        text = main.text()
        self.assertIn('2 PLANNED ROUTES', text)
        self.assertNotIn('3 PLANNED', text)
        self.assertIn('1 REPORT', text)

    def test_goal_backlinks_shape(self):
        links = self.site['goal_backlinks']
        self.assertEqual(list(links), ['real-report'])
        self.assertEqual(helpers.slugs(links['real-report']), ['done-traverse'])
        if hasattr(self.goals_mod, 'backlinks'):
            self.assertEqual({k: helpers.slugs(v) for k, v in self.goals_mod.backlinks(self.site).items()}, {'real-report': ['done-traverse']})


# ---------------------------------------------------------------- header, menu, footer (the test_nav pattern)

class HeaderTests(TickListFixture):

    def header(self, here, active=None, trip=None):
        return Doc(core.header(here, active, trip))

    @staticmethod
    def main_nav(doc):
        nav = doc.find('nav', attrs={'aria-label': 'Main'})
        assert nav is not None, 'no <nav aria-label="Main">'
        return [(a['href'], a['aria-current'], a.text()) for a in nav.find_all('a')]

    def current(self, here, active=None, trip=None):
        return [(h, c) for h, c, _ in self.main_nav(self.header(here, active, trip)) if c]

    def test_home_nav_has_tick_list_after_trips(self):
        nav = self.main_nav(self.header('', None))
        self.assertEqual([h for h, _, _ in nav], SITE_LINKS)
        self.assertEqual([t for _, _, t in nav], ['Trips', 'Tick list', 'Map', 'About', 'Search'])
        self.assertEqual([c for _, c, _ in nav], [None] * 5)

    def test_tick_list_page_marks_tick_list_as_page(self):
        self.assertEqual(self.current('tick-list/', 'ticklist'), [('../tick-list/', 'page')])

    def test_nested_tick_list_context_marks_tick_list_true(self):
        self.assertEqual(self.current('trips/ridge-idea/', 'ticklist', self.by['ridge-idea']), [('../../tick-list/', 'true')])

    def test_trips_and_section_pages_unchanged(self):
        self.assertEqual(self.current('trips/', 'trips'), [('../trips/', 'page')])
        self.assertEqual(self.current('hiking/', 'hike'), [('../trips/', 'true')])
        self.assertEqual(self.current('trips/real-report/', 'hike', self.by['real-report']), [('../../trips/', 'true')])
        self.assertEqual(self.current('map/', 'map'), [('../map/', 'page')])

    def test_phone_menu_site_column_has_tick_list_after_trips(self):
        doc = self.header('', None)
        ul = doc.by_id('menu').find('ul', cls='menu-list--site')
        links = ul.find_all('a')
        self.assertEqual([a['href'] for a in links], SITE_LINKS)
        self.assertEqual([a.text() for a in links][:2], ['Trips', 'Tick list'])
        cur = [(a['href'], a['aria-current']) for a in self.header('tick-list/', 'ticklist').by_id('menu').find('ul', cls='menu-list--site').find_all('a')
               if a['aria-current']]
        self.assertEqual(cur, [('../tick-list/', 'page')])

    def test_footer_site_list_has_tick_list_after_trips(self):
        doc = Doc(core.footer('ski/'))
        links = doc.find('nav', attrs={'aria-labelledby': 'f-site'}).find_all('a')
        self.assertEqual([a['href'] for a in links][:2], ['../trips/', '../tick-list/'])
        self.assertEqual([a.text() for a in links][:2], ['Trips', 'Tick list'])

    def test_nav_links_are_relative(self):
        for h, _, _ in self.main_nav(self.header('trips/ridge-idea/', 'ticklist', self.by['ridge-idea'])):
            self.assertTrue(h.startswith('../../'), h)


if __name__ == '__main__':
    unittest.main()
