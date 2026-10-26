"""Phase 2T: the public tick list (sitegen.pages.ticklist.build -> tick-list/ and core.goal_card), the goal-page variant of
sitegen.pages.report.page, the report backlink, the publication boundary (goals stay out of published / RSS / search /
curation), the active-goal counts and the header's Tick list link.

A synthetic site in a temp dir: seven non-draft goals (kind: planned) across four regions and no region, in several
statuses and priorities, one archived, one completed with an outing linked to a synthetic published report, one legacy
planned route without goal.json, one with a track but no render, one with a rendered tile (a temp rendered folder), several
without a track; two published reports; one draft goal that must never appear. site['goals'], site['active_goals'] and
site['goal_backlinks'] come from tools/build.py's own site_of(), so the build's wiring is what runs. Page modules are imported in
setUp, so a missing module fails each test clearly instead of breaking discovery. core.region_map_href reads
rendered/site/meta.json; the fixture regions are patched into core's in-memory copy. Fixture slugs match no real trip.

Phase 4 (contract-phase4.md) adds: the inline script that shows the search form before first paint (5.1: core.reveal),
the goal page's phone bar without a GPX item when the goal has no route (2.1), the tick-list page's share image (4.1),
the rule that nothing completes a goal but a logged outing (a report with the goal's title and the very same track
bytes changes nothing), and one scan of everything the build would publish as text (every page of every page module
for the fixture, the feed, the sitemap and the bundled site.css / site.js) for absolute local paths and
credential-shaped strings.
"""
import hashlib
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
from helpers import Doc, photo, LANDSCAPE, PORTRAIT  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

HERE = 'tick-list/'
REGIONS = ['Alps', 'Boise', 'Eastern Sierra', 'Lake Tahoe']
GOALS = ['ridge-idea', 'couloir-short', 'alps-someday', 'done-traverse', 'old-archived', 'legacy-ridge', 'tile-goal']
ACTIVE = ['ridge-idea', 'couloir-short', 'alps-someday', 'legacy-ridge', 'tile-goal']
REPORTS = ['real-report', 'other-report']
PCT = 'trips/pacific-crest-trail-2024/'
SITE_LINKS = ['trips/', 'tick-list/', 'map/', 'about/']   # the fixture has no PCT series; Search is a form (core.search_form)


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


def bar_items(nav):
    """[(label, href, is a download)] of a phone bottom bar, in order."""
    return [(a.find('span').text(), a['href'], 'download' in a) for a in nav.find_all('a')]


# What must never be in a published file: a path on the machine that built it ...
LOCAL_PATHS = [('a macOS home folder', r'/Users/'), ('a macOS private folder', r'/private/'), ('a Linux home folder', r'/home/'),
               ('a Windows drive path', r'[A-Za-z]:\\'), ('a macOS temp folder', r'/var/folders/'), ('a mounted volume', r'/Volumes/'),
               ('a temp folder', r'/tmp/'), ('a file: URL', r'file:///')]
# ... or anything shaped like a credential. Shapes, not words: 'tokens' and 'credentials: same-origin' are ordinary
# JavaScript in site.js.
CREDENTIALS = [('an AWS access key id', r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b'),
               ('a GitHub token', r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,})'),
               ('a Slack token', r'\bxox[abprs]-[A-Za-z0-9-]{10,}'),
               ('a Google API key', r'\bAIza[0-9A-Za-z_-]{35}'),
               ('a secret key (sk-...)', r'\bsk-[A-Za-z0-9_-]{20,}'),
               ('a live or test API key', r'\b[rs]k_(?:live|test)_[A-Za-z0-9]{16,}'),
               ('a private key block', r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
               ('a JSON web token', r'\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}'),
               ('a bearer token', r'(?i)\bbearer\s+[A-Za-z0-9._~+/-]{16,}'),
               ('a URL with a user and password', r'https?://[^/\s:@"\'<>]+:[^/\s:@"\'<>]+@'),
               ('a named secret', r'(?i)\b(?:pass(?:word|wd)?|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|private[_-]?key)'
                                  r'\b\s*[=:]\s*["\']?[A-Za-z0-9+/_-]{8,}')]
# One string each pattern must find (so a pattern that can match nothing fails the scan's own test). They are put
# together here from pieces: this file itself holds nothing shaped like a secret.
SAMPLES = {'a macOS home folder': '/Us' + 'ers/someone/Documents/x.gpx', 'a macOS private folder': '/pri' + 'vate/tmp/x', 'a Linux home folder': '/ho' + 'me/someone/x',
           'a Windows drive path': 'C:' + '\\Users\\someone', 'a macOS temp folder': '/var/' + 'folders/ab/T/x', 'a mounted volume': '/Vol' + 'umes/Disk/x',
           'a temp folder': '/t' + 'mp/x', 'a file: URL': 'file:' + '///x/y',
           'an AWS access key id': 'AK' + 'IA' + 'A' * 16, 'a GitHub token': 'gh' + 'p_' + 'a1' * 18, 'a Slack token': 'xo' + 'xb-' + '1' * 12,
           'a Google API key': 'AI' + 'za' + 'a' * 35, 'a secret key (sk-...)': 's' + 'k-' + 'a1' * 12, 'a live or test API key': 's' + 'k_live_' + 'a1' * 8,
           'a private key block': '-----BEGIN ' + 'RSA PRIVATE KEY-----', 'a JSON web token': 'ey' + 'J' + 'a' * 10 + '.ey' + 'J' + 'b' * 10 + '.' + 'c' * 10,
           'a bearer token': 'Bear' + 'er ' + 'a1' * 10, 'a URL with a user and password': 'https://us' + 'er:pw@example.test/',
           'a named secret': 'api_' + 'key = "' + 'a1' * 6 + '"'}


def findings(texts, extra=()):
    """['<file>: <what> "...context..."'] for every LOCAL_PATHS / CREDENTIALS match and every literal string of `extra`
    ([(what, string)]) in texts ({file: text}); [] when the texts are clean."""
    checks = [(what, re.compile(rx)) for what, rx in LOCAL_PATHS + CREDENTIALS] + [(what, re.compile(re.escape(s))) for what, s in extra if s]
    out = []
    for name in sorted(texts):
        for what, rx in checks:
            for m in rx.finditer(texts[name]):
                out.append('%s: %s %r' % (name, what, texts[name][max(0, m.start() - 30):m.end() + 30]))
    return out


def goal_site(trips, goals_mod=None):
    """The site dict from tools/build.py's own site_of() (goals, active_goals, the outing check and goal_backlinks are the
    build's wiring, not a copy of it), registered with core as build() does next."""
    build = importlib.import_module('build')
    site = build.site_of(helpers.newest_first(trips))
    core.register_site(site)
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
    """The page with its search form. The fixture has five active goals, under ticklist.FILTERS_FROM (six), so the form
    is asked for here by lowering the threshold to one; FormThresholdTests pins the threshold itself."""

    def setUp(self):
        super().setUp()
        self.mod = load_module(self, 'sitegen.pages.ticklist')
        p = mock.patch.object(self.mod, 'FILTERS_FROM', 1)
        p.start()
        self.addCleanup(p.stop)
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

    def test_the_form_asks_browsers_not_to_refill_its_controls(self):
        # as on the Trips page: the script sets the selects from the address, and a browser that refills them on Back /
        # Forward does it afterwards, with another history entry's values
        form = self.form
        self.assertEqual(form['autocomplete'], 'off')
        self.assertEqual(form.by_id('tkl-q')['autocomplete'], 'off')
        selects = form.find_all('select')
        self.assertGreaterEqual(len(selects), 2)
        for s in selects:                       # none opts back in
            self.assertNotIn('autocomplete', s.attrs)

    def test_the_form_is_shown_by_an_inline_script_right_after_it(self):
        # contract-phase4.md 5.1 and 10: the form still ships hidden (without JavaScript it stays so); core.reveal('search')
        # is the element right after </form> and before the noscript note, so with JavaScript the form is in place at
        # first paint and nothing below it moves when the deferred bundle arrives
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
        # the script finds the form by its id: one element has it, and it is the form
        self.assertEqual(len(self.doc.find_all(attrs={'id': 'search'})), 1)
        self.assertIs(self.doc.by_id('search'), form)
        # the body's other script is the deferred bundle, at the very end
        scripts = self.doc.find('body').find_all('script')
        self.assertEqual([('src' in s, 'defer' in s) for s in scripts], [(False, False), (True, True)])
        self.assertIs(scripts[0], script)

    def test_core_reveal_is_one_statement_on_the_named_element(self):
        # contract-phase4.md 10: reveal(el_id) -> <script>document.getElementById("<id>").hidden=false</script>
        self.assertEqual(core.reveal('search'), '<script>document.getElementById("search").hidden=false</script>')
        self.assertEqual(core.reveal('tkl-form'), '<script>document.getElementById("tkl-form").hidden=false</script>')

    def test_the_page_shares_the_site_image_when_a_trip_is_featured(self):
        # contract-phase4.md 4.1: tick-list/ passes image=core.site_share(), the share photo of the first featured trip;
        # none when nothing is featured (the fixture's own site: no 'featured' at all)
        self.assertEqual(share_meta(self.doc), {'twitter:card': 'summary'})
        self.assertNotIn('og:image', self.page.html)
        helpers.make_trip(self.tmp, 'photo-report', title='Photo Report', activity='hike', date='2026-07-01', region='Alps', track=True,
                          photos=[photo('photos/01.webp', LANDSCAPE, alt='A synthetic view')])
        trips = helpers.load_dir(self.tmp)
        site = load_module(self, 'build').site_of(helpers.newest_first(trips))
        site['featured'] = [site['by_slug']['photo-report'], site['by_slug']['real-report']]
        with mock.patch.object(core, '_SITE_SHARE', [None]):
            core.register_site(site)
            self.assertEqual(core.site_share(), {'path': 'trips/photo-report/photos/01.webp', 'w': 1600, 'h': 1200, 'alt': 'A synthetic view'})
            doc = Doc({p.url: p for p in self.mod.build(site)}[HERE].html)
            self.assertEqual(share_meta(doc), {'og:image': core.SITE_URL + 'trips/photo-report/photos/01.webp', 'og:image:type': 'image/webp',
                                               'og:image:width': '1600', 'og:image:height': '1200', 'og:image:alt': 'A synthetic view',
                                               'twitter:card': 'summary_large_image', 'twitter:image:alt': 'A synthetic view'})
        core.register_site(self.site)

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
            if inp['type'] == 'hidden':
                # the header's and the menu's search forms (core.search_form) carry the explorer's sort, nothing else
                self.assertEqual((inp['name'], inp['value']), ('sort', 'relevance'), repr(inp))
                continue
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
        self.assertIsNone(doc.by_id('tkl-count'))     # no goal to filter: no form and no status line, whatever the threshold
        self.assertIn('Nothing on the list yet', text)


class FormThresholdTests(TickListFixture):
    """visual-05 (Phase 7): the search form and the status line appear once there are FILTERS_FROM (6) active goals;
    with fewer the page is its head and the active goals, completed and archived ones left off."""

    def build(self, site=None):
        mod = load_module(self, 'sitegen.pages.ticklist')
        return mod, Doc({p.url: p for p in mod.build(site or self.site)}[HERE].html)

    def test_the_threshold_is_six_active_goals(self):
        mod, _doc = self.build()
        self.assertEqual(mod.FILTERS_FROM, 6)
        active = [t for t in self.site['goals'] if self.goals_mod.is_active(t['goal'])]
        self.assertEqual(len(active), 5)
        self.assertFalse(mod.with_form(self.site))

    def test_below_it_the_page_is_the_head_and_the_active_goals(self):
        _mod, doc = self.build()
        main = doc.by_id('main')
        self.assertIsNone(doc.by_id('search'))
        self.assertIsNone(doc.by_id('tkl-count'))
        self.assertIsNone(doc.by_id('tkl-none'))
        self.assertEqual(doc.find_all('noscript'), [])
        self.assertIn('5 ACTIVE GOALS', main.find('p', cls='tkl-stats').text())     # the head counts every kind still
        shown = sorted(c['data-slug'] for c in main.find_all('li', cls='gcard'))
        self.assertEqual(shown, sorted(t['slug'] for t in self.site['goals'] if self.goals_mod.is_active(t['goal'])))
        self.assertNotIn('done-traverse', shown)
        self.assertNotIn('old-archived', shown)

    def test_at_it_the_form_and_the_status_line_are_there_and_every_goal_is_listed(self):
        mod = load_module(self, 'sitegen.pages.ticklist')
        with mock.patch.object(mod, 'FILTERS_FROM', 5):
            self.assertTrue(mod.with_form(self.site))
            doc = Doc({p.url: p for p in mod.build(self.site)}[HERE].html)
        self.assertIsNotNone(doc.by_id('search'))
        self.assertIsNotNone(doc.by_id('tkl-count'))
        shown = {c['data-slug'] for c in doc.by_id('main').find_all('li', cls='gcard')}
        self.assertIn('done-traverse', shown)                        # the script's Active scope hides it on load
        self.assertIn('old-archived', shown)

    def test_with_goals_but_none_active_the_page_says_so(self):
        site = dict(self.site)
        site['goals'] = [t for t in self.site['goals'] if not self.goals_mod.is_active(t['goal'])]
        _mod, doc = self.build(site)
        self.assertEqual(doc.find_all('li', cls='gcard'), [])
        self.assertIn('No active goals right now.', doc.by_id('main').text())


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
        text = helpers.plain_text(helpers.seen_text(self.card('couloir-short')))
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
        self.assertTrue(a.text().startswith('Open the goal'))

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

    def test_the_approximate_distance_is_said_once(self):
        # Phase 10 (visual-19): the strip under the title states ≈ distance, so the title's value slot leaves it out;
        # the strip is one cell, capped like a four-cell strip's cells (strip--1)
        doc = self.doc('couloir-short')
        self.assertNotIn('≈', doc.find(cls='rep-title').text())
        strip = doc.by_id('stats')
        self.assertIn('≈', strip.text())
        self.assertIn('12.3', strip.text())
        self.assertNotIn('≈', self.doc('ridge-idea').find(cls='rep-title').text())
        cells = len(strip.find_all(cls='strip-c'))
        self.assertEqual('strip--%d' % cells in strip.find('dl')['class'], cells in (1, 2, 5))

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

    def test_phone_bar_has_a_gpx_item_only_when_the_goal_has_a_route(self):
        # contract-phase4.md 2.1: no track, no download. report.goal_bottom_bar: Map · Notes · GPX, each only when the
        # page has it; --n counts what is shown; no bar at all for a single item
        want = {'couloir-short': [('Map', '#map', False), ('Notes', '#report', False), ('GPX', 'couloir-short.gpx', True)],   # route and notes
                'legacy-ridge': [('Map', '#map', False), ('GPX', 'legacy-ridge.gpx', True)],                                 # a route, no notes
                'ridge-idea': [('Map', '#map', False), ('Notes', '#report', False)],                                         # notes, no route
                'done-traverse': [('Map', '#map', False), ('Notes', '#report', False)],
                'alps-someday': None, 'old-archived': None}                                                                  # neither: no bar
        for slug, items in want.items():
            with self.subTest(slug):
                t = self.by[slug]
                self.assertEqual(bool(t['track']), bool(items) and items[-1][0] == 'GPX')
                doc = self.doc(slug)
                navs = doc.find_all('nav', cls='bbar')
                if items is None:
                    self.assertEqual(navs, [])
                else:
                    self.assertEqual(len(navs), 1)
                    self.assertEqual(navs[0]['aria-label'], 'Goal sections')
                    self.assertEqual(bar_items(navs[0]), items)
                    self.assertEqual(navs[0]['style'], '--n:%d' % len(items))
                    for a in navs[0].find_all('a'):
                        if a['href'].startswith('#'):
                            self.assertIsNotNone(doc.by_id(a['href'][1:]), a['href'])
                # the bar's item and the title action go together, and without a route nothing on the page is a download
                downloads = [(a.text(), a['href']) for a in doc.find_all('a') if 'download' in a or '.gpx' in (a['href'] or '')]
                if t['track']:
                    self.assertEqual(downloads, [('Download planned GPX', slug + '.gpx'), ('GPX', slug + '.gpx')])
                else:
                    self.assertEqual(downloads, [])
                    self.assertNotIn('.gpx', self.page(slug).html)

    def test_goal_bottom_bar_cases(self):
        # the function itself, for each mix of notes and route
        bar = self.report.goal_bottom_bar
        routed, idea = self.by['legacy-ridge'], self.by['alps-someday']
        self.assertEqual(bar(idea, False), '')
        cases = [((idea, True), [('Map', '#map', False), ('Notes', '#report', False)]),
                 ((routed, False), [('Map', '#map', False), ('GPX', 'legacy-ridge.gpx', True)]),
                 ((routed, True), [('Map', '#map', False), ('Notes', '#report', False), ('GPX', 'legacy-ridge.gpx', True)])]
        for args, items in cases:
            with self.subTest(track=bool(args[0]['track']), notes=args[1]):
                nav = Doc(bar(*args)).find('nav')
                self.assertEqual(bar_items(nav), items)
                self.assertEqual(nav['style'], '--n:%d' % len(items))

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
        self.assertIn('<h2 class="t-h3 rep-h" id="report-h">Report</h2>', self.report.page(self.by['real-report'], self.site).html)   # reports keep their heading


    def test_backlink_on_multi_day_and_series_reports(self):
        # an outing may name any published report, so the multi-day and series page builders carry the line too
        helpers.make_trip(self.tmp, 'hut-report', title='Hut Report', activity='ski', kind='multi-day', date='2026-03-01', end_date='2026-03-02',
                          region='Alps', days=[{'title': 'Up', 'date': '2026-03-01'}, {'title': 'Down', 'date': '2026-03-02'}])
        helpers.make_series(self.tmp, slug='long-walk', title='Long Walk')
        trips = helpers.load_dir(self.tmp)
        by = {t['slug']: t for t in trips}
        for slug in ('hut-report', 'long-walk'):
            by['done-traverse']['goal']['outings'].append({'outcome': 'attempted', 'date': None, 'report_slug': slug, 'note': ''})
        site = goal_site(trips, self.goals_mod)
        self.assertEqual(sorted(site['goal_backlinks']), ['hut-report', 'long-walk', 'real-report'])
        for slug, name in (('hut-report', 'sitegen.pages.multiday'), ('long-walk', 'sitegen.pages.series')):
            with self.subTest(slug):
                mod = load_module(self, name)
                doc = Doc(mod.page(by[slug], site).html)
                line = next((p for p in doc.by_id('main').find_all('p') if 'On the tick list' in p.text()), None)
                self.assertIsNotNone(line, '%s has no "On the tick list" line' % slug)
                self.assertEqual(line.find('a')['href'], '../../trips/done-traverse/')
                self.assertEqual(line.find('a').text(), 'Done Traverse')
        # a multi-day report no goal names has no line
        helpers.make_trip(self.tmp, 'plain-tour', title='Plain Tour', activity='ski', kind='multi-day', date='2026-01-10', end_date='2026-01-11',
                          days=[{'title': 'One', 'date': '2026-01-10'}, {'title': 'Two', 'date': '2026-01-11'}])
        plain = content.load_trip(os.path.join(self.tmp, 'plain-tour'))
        html_ = load_module(self, 'sitegen.pages.multiday').page(plain, site).html
        self.assertNotIn('On the tick list', html_)

    def test_legacy_goal_claims_no_provenance_it_cannot_back(self):
        # a planned route without goal.json has a GPX but no recorded source or checksum
        legacy = self.doc('legacy-ridge').by_id('main').text()
        self.assertNotIn('byte for byte', legacy)
        self.assertNotIn('measured from it', legacy)
        self.assertIn('not recorded', legacy)
        self.assertIn('not a recording of a trip', legacy)
        # a goal imported through the tick list (a route block with its checksum) keeps the statement
        self.assertIn('byte for byte', self.doc('couloir-short').by_id('main').text())

    def test_a_reopened_goal_lists_the_reopening_with_its_outings(self):
        t = dict(self.by['done-traverse'])
        g = dict(t['goal'])
        g['status'] = 'shortlisted'
        g['outings'] = list(g['outings']) + [{'outcome': 'reopened', 'date': '2026-09-15', 'report_slug': None, 'note': 'Back for the north side.'}]
        t['goal'] = self.goals_mod.validate({k: v for k, v in g.items() if k != 'legacy'}, 'done-traverse')
        t['goal']['legacy'] = False
        doc = Doc(self.report.page(t, self.site).html)
        outs = doc.by_id('outings')
        self.assertIsNotNone(outs)
        self.assertEqual([x.text() for x in outs.find_all(cls='tag')], ['Attempted', 'Completed', 'Reopened'])
        self.assertIn('Back for the north side.', outs.text())
        self.assertIn('A Real Synthetic Report', outs.text())   # the completed outing still links its report


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

    def test_about_page_counts_active_goals_only(self):
        about = load_module(self, 'sitegen.pages.about')
        text = Doc(about.numbers(self.site, 'about/')).text().replace('\xa0', ' ')
        self.assertIn('+ 5 PLANNED ROUTES', text)     # the same figure as count_items: completed and archived goals are out
        self.assertNotIn('7 PLANNED', text)

    def test_map_page_region_groups_list_and_count_active_goals_only(self):
        archive = load_module(self, 'sitegen.pages.archive')
        meta = core._SITE_META[0]     # the fixture's: no region has a rendered map, so every region is a plain list
        doc = Doc(archive.other_places(self.site, 'map/', meta))
        alps = doc.by_id('region-alps')
        self.assertIsNotNone(alps)
        hrefs = [a['href'] for a in alps.find_all('a')]
        self.assertIn('../trips/alps-someday/', hrefs)        # an active goal is a future route in its region
        self.assertIn('../trips/real-report/', hrefs)
        self.assertNotIn('../trips/done-traverse/', hrefs)    # completed: it has its page, not a Planned row
        text = alps.text().replace('\xa0', ' ')
        self.assertIn('+ 1 PLANNED ROUTE', text)
        self.assertNotIn('2 PLANNED', text)
        self.assertEqual(sorted(helpers.slugs(archive.listed(self.site))),
                         sorted(REPORTS + ACTIVE))

    def test_home_region_counts_count_active_goals_only(self):
        home = load_module(self, 'sitegen.pages.home')
        items = [x.replace('\xa0', ' ') for x in home.region_counts(self.site, ['real-report', 'alps-someday', 'done-traverse'])]
        self.assertEqual(items[0], '1 REPORT')
        self.assertEqual(items[-1], '+ 1 PLANNED ROUTE')
        only_done = home.region_counts(self.site, ['done-traverse', 'old-archived'])
        self.assertEqual(only_done, [])                        # nothing future to count

    def test_a_goals_numbers_are_marked_approximate_in_every_row(self):
        goal, report = self.by['couloir-short'], self.by['other-report']
        self.assertEqual(core.approx(goal), '≈ ')
        self.assertEqual(core.approx(report), '')
        for item in core.plain_stats(goal, items=True):
            self.assertIn('≈', item)
        self.assertIn('≈', core.row_stats_line(goal))
        cells = Doc(core.stats_cells(goal))
        labels = [d.text() for d in cells.find_all('dt')]
        self.assertIn('High point', labels)                    # a plan was never recorded: no 'GPS max'
        self.assertNotIn('GPS max', labels)
        for dd in cells.find_all('dd'):
            self.assertTrue(dd.text().startswith('≈'), dd.text())
        row = Doc(core.table_row(goal, 'map/'))
        nums = row.find_all('span', cls='num')
        self.assertEqual(len(nums), 3)
        for num in nums:
            self.assertIn('about', num.text())                 # spoken; the sign itself is aria-hidden
            self.assertIn('≈', num.text())
        self.assertIn('High point', nums[2].text())
        archive = load_module(self, 'sitegen.pages.archive')
        self.assertIn('≈', archive.dist_line(goal))
        # a report's numbers are recordings: never marked
        report['stats'].update(distance_km=12.0, gain_m=900, high_m=3000)
        self.assertNotIn('≈', ''.join(core.plain_stats(report, items=True)) + core.stats_cells(report) + core.table_row(report, 'map/')
                         + archive.dist_line(report))
        self.assertIn('GPS max', core.stats_cells(report))

    def test_the_home_band_counts_no_goal_and_the_map_head_counts_active_goals_only(self):
        home = load_module(self, 'sitegen.pages.home')
        archive = load_module(self, 'sitegen.pages.archive')
        # the home page's By the numbers band (Phase 17, in place of the activity tiles) counts published reports only: no
        # goal, active or not, is a figure or a bar
        band = Doc(home.numbers(self.site)).text().replace('\xa0', ' ')
        self.assertNotIn('PLANNED', band.upper())
        pub = [t for t in self.site['published']]
        self.assertEqual(dict((act, k) for act, _lab, k in home.activity_counts(self.site)),
                         dict((act, sum(1 for t in pub if t['activity'] == act)) for act, _lab in core.NAV))
        head = Doc(archive.head_block(self.site, [], core._SITE_META[0])).text().replace('\xa0', ' ')
        self.assertIn('2 REPORTS', head)
        self.assertIn('+ 5 PLANNED ROUTES', head)
        self.assertNotIn('7 PLANNED', head)
        # the map page's 'All reports' table: its Planned group lists the five active goals only
        hrefs = [a['href'] for a in Doc(archive.archive_section(self.site, 'map/')).find_all('a')]
        for slug in ACTIVE:
            self.assertIn('../trips/%s/' % slug, hrefs, slug)
        for slug in ('done-traverse', 'old-archived'):
            self.assertNotIn('../trips/%s/' % slug, hrefs, slug)

    def test_the_builds_own_site_wiring_checks_outings_and_derives_the_subsets(self):
        build = load_module(self, 'build')
        site = build.site_of(helpers.newest_first(self.trips))
        self.assertEqual(sorted(helpers.slugs(site['goals'])), sorted(GOALS))
        self.assertEqual(sorted(helpers.slugs(site['active_goals'])), sorted(ACTIVE))
        self.assertEqual({k: helpers.slugs(v) for k, v in site['goal_backlinks'].items()}, {'real-report': ['done-traverse']})
        self.assertNotIn('draft-goal', site['by_slug'])            # content.load_all leaves drafts out before site_of sees them
        # an outing that names another goal, or nothing that exists, stops the build with the goal's file in the message
        for bad in ('alps-someday', 'no-such-report'):
            with self.subTest(report=bad):
                trips = helpers.load_dir(self.tmp)
                by = {t['slug']: t for t in trips}
                by['done-traverse']['goal']['outings'][1]['report_slug'] = bad
                with self.assertRaises(content.ContentError) as cm:
                    build.site_of(trips)
                self.assertIn('done-traverse', str(cm.exception))
                self.assertIn(bad, str(cm.exception))

    def test_drafts_never_reach_the_site_through_the_real_loader(self):
        build = load_module(self, 'build')
        with mock.patch.object(content, 'TRIPS_DIR', self.tmp):
            site = build.site_of(content.load_all())
        self.assertNotIn('draft-goal', site['by_slug'])
        self.assertEqual(sorted(helpers.slugs(site['goals'])), sorted(GOALS))
        self.assertEqual(sorted(helpers.slugs(site['published'])), sorted(REPORTS))

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

    def twin(self, status='idea'):
        """An idea goal and a published report that could be mistaken for its completion: the same title, the same
        region and activity, and a track.gpx with the very same bytes. Returns (trips, site) loaded from the temp dir."""
        track = b'<gpx version="1.1"><trk><trkseg><trkpt lat="45.9" lon="7.6"><ele>2000</ele></trkpt></trkseg></trk></gpx>\n'
        sha = hashlib.sha256(track).hexdigest()
        goal = helpers.make_trip(self.tmp, 'twin-goal', title='Twin Line', activity='hike', kind='planned', region='Alps', track=True)
        rep = helpers.make_trip(self.tmp, 'twin-report', title='Twin Line', activity='hike', date='2026-09-01', region='Alps', track=True,
                                body='Walked the twin line in a day.')
        for folder in (goal, rep):
            with open(os.path.join(folder, 'track.gpx'), 'wb') as fh:
                fh.write(track)
        g = self.goals_mod.defaults()
        g.update(status=status, added_at='2026-01-01', route_scope='full-intended-route',
                 route_source={'kind': 'own-prior-recording', 'url': None, 'label': None, 'checked_at': None, 'public_copy_approved': True,
                               'approximation_note': None},
                 route={'source_sha256': sha, 'method': 'ticklist-gpx-1', 'selected': {'type': 'trk', 'index': 0, 'name': None},
                        'alternatives': 1, 'segments': 1, 'points': 1, 'elevation': 'full', 'times': False, 'waypoints': 0})
        write_json(goal, 'goal.json', g)
        trips = helpers.load_dir(self.tmp)
        return trips, goal_site(trips, self.goals_mod)

    def test_a_report_that_matches_a_goal_never_completes_it(self):
        # plan 16, goal lifecycle: no auto-completion. Completion exists only as an outing logged with tools/ticklist.py;
        # the build infers nothing from a report with the goal's title and the same track bytes
        trips, site = self.twin()
        by = site['by_slug']
        goal, rep = by['twin-goal'], by['twin-report']
        self.assertEqual(goal['title'], rep['title'])
        with open(goal['track'], 'rb') as a, open(rep['track'], 'rb') as b:
            self.assertEqual(a.read(), b.read())
        with open(os.path.join(goal['dir'], 'goal.json'), 'rb') as fh:
            sidecar = fh.read()
        # the goal is what its sidecar says: an idea, with no outing, still active, not a report
        self.assertEqual(goal['goal']['status'], 'idea')
        self.assertEqual(goal['goal']['outings'], [])
        self.assertTrue(self.goals_mod.is_active(goal['goal']))
        self.assertIn('twin-goal', helpers.slugs(site['active_goals']))
        self.assertNotIn('twin-goal', helpers.slugs(site['published']))
        self.assertIn('twin-report', helpers.slugs(site['published']))
        # the report gets no backlink: only an outing that names it makes one
        self.assertEqual({k: helpers.slugs(v) for k, v in site['goal_backlinks'].items()}, {'real-report': ['done-traverse']})
        self.assertEqual({k: helpers.slugs(v) for k, v in self.goals_mod.backlinks(site).items()}, {'real-report': ['done-traverse']})
        report = load_module(self, 'sitegen.pages.report')
        self.assertEqual(report.tick_backlink(rep, rep['url'], site), '')
        rep_html = report.page(rep, site).html
        self.assertNotIn('On the tick list', rep_html)
        self.assertNotIn('trips/twin-goal/', rep_html)
        # the goal page: still an idea, no Outings section, no link to the report
        goal_doc = Doc(report.page(goal, site).html)
        tags = [x.text() for x in goal_doc.find(cls='rep-chips').find_all(cls='tag')]
        self.assertIn('Idea', tags)
        self.assertNotIn('Completed', tags)
        self.assertNotIn('Attempted', tags)
        self.assertIsNone(goal_doc.by_id('outings'))
        self.assertNotIn('trips/twin-report/', report.page(goal, site).html)
        # the tick list: an idea among the active goals, one completed goal as before
        ticklist = load_module(self, 'sitegen.pages.ticklist')
        tl = Doc({p.url: p for p in ticklist.build(site)}[HERE].html)
        card = tl.find('li', attrs={'data-slug': 'twin-goal'})
        self.assertEqual((card['data-status'], card['data-archived'], card['data-gpx']), ('idea', '0', '1'))
        self.assertNotIn('Completed', [x.text() for x in card.find(cls='gcard-tags').find_all(cls='tag')])
        text = tl.by_id('main').text()
        self.assertIn('6 ACTIVE', text)
        self.assertIn('1 COMPLETED', text)
        # nothing was written back: the sidecar on disk is byte for byte what the author left
        with open(os.path.join(goal['dir'], 'goal.json'), 'rb') as fh:
            self.assertEqual(fh.read(), sidecar)

    def test_only_a_logged_outing_links_the_two(self):
        # the other way round, so the test above cannot pass by accident: the same pair with an outing in goal.json is
        # completed, and the report then carries the backlink
        trips, _site = self.twin()
        folder = os.path.join(self.tmp, 'twin-goal')
        with open(os.path.join(folder, 'goal.json'), encoding='utf-8') as fh:
            g = json.load(fh)
        g.update(status='completed', outings=[{'outcome': 'completed', 'date': '2026-09-01', 'report_slug': 'twin-report', 'note': ''}])
        write_json(folder, 'goal.json', g)
        site = goal_site(helpers.load_dir(self.tmp), self.goals_mod)
        self.assertEqual(site['by_slug']['twin-goal']['goal']['status'], 'completed')
        self.assertEqual({k: helpers.slugs(v) for k, v in site['goal_backlinks'].items()},
                         {'real-report': ['done-traverse'], 'twin-report': ['twin-goal']})
        report = load_module(self, 'sitegen.pages.report')
        self.assertIn('On the tick list', report.page(site['by_slug']['twin-report'], site).html)
        self.assertNotIn('twin-goal', helpers.slugs(site['active_goals']))

    def published_texts(self):
        """Every text file the build would publish for the fixture plus a report with photos, a multi-day trip and a
        journal: each page of each page module in tools/build.py's PAGE_MODULES (the two JSON search indexes among
        them), feed.xml, sitemap.xml, and the bundled assets/site.css and assets/site.js. The trips are loaded again
        with content.RENDERED and core.ROOT inside the temp dir, so no page module looks at the real rendered/."""
        build = load_module(self, 'build')
        # report.py keeps a per-build title cache keyed by id(): start from an empty one and leave an empty one behind
        title_counts = getattr(load_module(self, 'sitegen.pages.report'), '_TITLE_COUNTS', {})
        title_counts.clear()
        self.addCleanup(title_counts.clear)
        helpers.make_trip(self.tmp, 'photo-report', title='Photo Report', activity='hike', date='2026-07-01', region='Alps', track=True,
                          body='Synthetic words for a test. ' * 8,
                          photos=[photo('photos/01.webp', LANDSCAPE, alt='A synthetic view', caption='A synthetic caption', sm=True),
                                  photo('photos/02.webp', PORTRAIT, alt='A second synthetic view')])
        helpers.touch(os.path.join(self.tmp, 'photo-report', 'photos', '01.th.webp'))
        # a placeholder render, so the report has its full-screen map page (Phase 6: a track without a render has none)
        rdir = os.path.join(self.tmp, '_rendered', 'trips', 'photo-report')
        os.makedirs(rdir)
        maps = {}
        for name, (w, h) in (('map-wide', (1440, 640)), ('map-col', (718, 400)), ('map-phone', (390, 336))):
            maps[name] = {'w': w, 'h': h, 'png': name + '.webp', 'base': name + '.base.svg'}
            with open(os.path.join(rdir, name + '.svg.html'), 'w', encoding='utf-8') as fh:
                fh.write('<svg width="%d" height="%d" viewBox="0 0 %d %d"></svg>' % (w, h, w, h))
        with open(os.path.join(rdir, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump({'maps': maps, 'charts': {}}, fh)
        helpers.make_trip(self.tmp, 'hut-report', title='Hut Report', activity='ski', kind='multi-day', date='2026-03-01', end_date='2026-03-02',
                          region='Alps', days=[{'title': 'Up', 'date': '2026-03-01', 'body': 'Synthetic day words.'}, {'title': 'Down', 'date': '2026-03-02'}])
        helpers.make_series(self.tmp, slug='long-walk', title='Long Walk')
        with mock.patch.object(content, 'RENDERED', os.path.join(self.tmp, '_rendered')), mock.patch.object(core, 'ROOT', self.tmp), \
                mock.patch.object(core, '_SITE_SHARE', [None]):
            site = build.site_of(helpers.newest_first(helpers.load_dir(self.tmp)))
            site['featured'] = [site['by_slug']['photo-report']]
            core.register_site(site)
            pages = []
            for name in build.PAGE_MODULES:
                pages += load_module(self, 'sitegen.pages.' + name).build(site)
            texts = {p.url or 'index.html': p.html for p in pages}
            texts['feed.xml'] = build.feed(site['published'])
            texts['sitemap.xml'] = build.sitemap(pages)
        core.register_site(self.site)
        texts['assets/site.css'] = build.css_bundle()
        texts['assets/site.js'] = build.js_bundle()
        return texts

    def test_nothing_published_names_a_local_path_or_looks_like_a_credential(self):
        # plan 16, tick-list publication: no raw private paths or credentials in the output. Scanned: every file of the
        # fixture site (pages of every kind, both JSON indexes, the feed, the sitemap) and the real CSS and JS bundles
        texts = self.published_texts()
        self.assertGreaterEqual(len(texts), 30)
        for name in ('index.html', 'trips/', 'trips/search.json', 'trips/journal.json', 'tick-list/', 'map/', 'about/', '404.html', 'hiking/', 'ski/',
                     'trips/couloir-short/', 'trips/photo-report/', 'trips/photo-report/map/', 'trips/hut-report/', 'trips/long-walk/',
                     'feed.xml', 'sitemap.xml', 'assets/site.css', 'assets/site.js'):
            self.assertIn(name, texts)
            self.assertTrue(texts[name].strip(), name)
        self.assertGreater(len(texts['assets/site.css']), 20000)
        self.assertGreater(len(texts['assets/site.js']), 20000)
        # the folders this very build read from, wherever the machine keeps them
        here = [('the fixture folder', self.tmp), ('the fixture folder', os.path.realpath(self.tmp)), ('the repository folder', ROOT),
                ('the repository folder', os.path.realpath(ROOT)), ('the home folder', os.path.expanduser('~')),
                ('the temp folder', tempfile.gettempdir()), ('the temp folder', os.path.realpath(tempfile.gettempdir()))]
        self.assertEqual(findings(texts, extra=here), [])

    def test_the_scan_finds_what_it_looks_for(self):
        # every pattern matches its sample, in any of the files, and a leaked fixture path is reported with its file
        self.assertEqual(sorted(SAMPLES), sorted(what for what, _rx in LOCAL_PATHS + CREDENTIALS))
        for what, _rx in LOCAL_PATHS + CREDENTIALS:
            with self.subTest(what):
                got = findings({'trips/x/index.html': '<p>clean</p>', 'assets/site.js': 'var a = 1; // %s\n' % SAMPLES[what]})
                self.assertTrue(got and all(f.startswith('assets/site.js: ') for f in got), got)
                self.assertIn(what, ' '.join(got))
        self.assertEqual(findings({'a.html': '<a href="../trips/x/x.gpx" download>GPX</a> tokens credentials: same-origin'}), [])
        leak = findings({'trips/x/index.html': '<!-- %s -->' % os.path.join(self.tmp, 'x', 'track.gpx')}, extra=[('the fixture folder', self.tmp)])
        self.assertTrue(any(f.startswith('trips/x/index.html: the fixture folder') for f in leak), leak)

    def test_goal_backlinks_shape(self):
        links = self.site['goal_backlinks']
        self.assertEqual(list(links), ['real-report'])
        self.assertEqual(helpers.slugs(links['real-report']), ['done-traverse'])
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
        self.assertEqual([t for _, _, t in nav], ['Trips', 'Tick list', 'Map', 'About'])
        self.assertEqual([c for _, c, _ in nav], [None] * 4)
        form = self.header('', None).find('nav', attrs={'aria-label': 'Main'}).find('form', cls='nav-search')
        self.assertEqual(form['action'], 'trips/')                 # Phase 7: the header's search lands on the explorer

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
        self.assertEqual([a['href'] for a in links], ['./'] + SITE_LINKS)                    # Home first (Phase 13A)
        self.assertEqual([a.text() for a in links][:3], ['Home', 'Trips', 'Tick list'])
        self.assertEqual(ul.find('form', cls='nav-search').find('input', attrs={'name': 'q'})['id'], 'menu-q')
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
