"""Phase 5: region pages (sitegen.pages.region.build -> regions/<slug>/), pinned to contract-phase5.md sections 1
(which regions get a page: core.read_site_meta, core.listed_trips, core.region_groups, core.region_pages,
core.region_page_href and what core.register_site records), 3 (the page: head, map panel, Featured, All reports, Other
regions, the document) and 5 (the guard of assets/js/pages/archive.js). The links other pages gained (section 2) are
tested in the files that own those pages; a whole build with region pages is in tests/test_build_site.py; the new CSS
is read in tests/test_a11y_static.py.

The contract was revised after a first round of review (the parts marked 'REVISED in round 2'), and this file follows
the revision: a region page lists what the content says (every listed trip whose `region` is the region's name: a
report without a track, a journal, a report the map's entry does not name), while the Map page's grouping
(core.region_groups) keeps the map entry's rule; core.register_site records region pages only when it is handed a
site meta; the page's side list is the Map page's list ('In this region', every row, 'Show all N'); the description
and the places of the head have their revised wording and order.

A synthetic site in a temp dir laid out like the repository: <tmp>/trips/<slug>/ and <tmp>/rendered/site/ with a
meta.json and one placeholder fragment per region map (tests/test_archive_page.py does the same for the Map page).
core.ROOT, content.RENDERED and core's in-memory copy of the site meta point at the temp dir while a test runs, so the
real rendered/ and content/ are never read. The fixture registers its site with that meta, as tools/build.py does
(core.register_site(site, core.read_site_meta())). Every slug starts with syn-r-, every name and sentence is made up.

  Synthetic Range              eleven reports of every activity (one flagged, two written with a cover, two written
                               without, one with a note too short to count, one undated, one without a track), seven
                               places, an active goal and an archived one                       the big page
  Synthetic Coast              three hikes of one year, each with a track, one written          a single activity
  Synthetic O'Brien & <Peaks>  two written reports without a photo; a name and a place that every context must escape
  Synthetic Plans              a region map and one planned route: no page
  Synthetic Desert             one report and no region map: no page
  Synthetic Trail              a journal: on no region map

A test that needs another site writes its trips with mk() and calls use() again. Nothing registered with core outlives
a test: helpers.keep_state() puts core's private lists and dicts back, so the order of test modules never matters
(the module's tearDownModule, helpers.no_region_pages_left, fails when a region page is still registered at its end).

Two functions that existed before the phase are held to what they wrote at commit fb425ab by comparing them with a
copy of the old function body kept in this file (legacy_region_panel, legacy_archive_section): archive.region_panel
without page=True, apart from its one new link, and archive.archive_section without the new keywords.

Round 3 (LegendTests, with a site of its own): the legend beside a region page's map is the key to the map, so it is
built from the trips the map draws (region.map_trips: the Map page's group for the region, core.region_groups) and
not from the page's list, which may hold a report without a track, a journal or a goal without a route. It is the
legend the Map page shows for the same map. When the map's entry names no trip of the site the list is used.
archive.region_panel takes those trips as `drawn`, in page mode only: without page=True it is still the function of
fb425ab and its one link.
"""
import contextlib
import importlib
import io
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
from sitegen.core import esc, icon  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, photo, LANDSCAPE, PORTRAIT  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

RANGE, COAST, PEAKS = 'Synthetic Range', 'Synthetic Coast', "Synthetic O'Brien & <Peaks>"
PLANS, DESERT, TRAIL = 'Synthetic Plans', 'Synthetic Desert', 'Synthetic Trail'
SLUG = {RANGE: 'synthetic-range', COAST: 'synthetic-coast', PEAKS: 'synthetic-obrien-peaks', PLANS: 'synthetic-plans',
        DESERT: 'synthetic-desert', TRAIL: 'synthetic-trail'}
MAPPED = [RANGE, COAST, PEAKS, PLANS]             # a region map each (rendered/site/meta.json 'regions')
PAGES = [RANGE, COAST, PEAKS]                     # the ones that get a page, in the Map page's order: 11, 3 and 2 reports
WALL = "Synthetic O'Neil & <Wall>"                # a place every context must escape
# a write-up long enough to be a written report (core.STRUCTURED_MIN_CHARS), and a note that is not
LONG = ('Synthetic write-up for a region test, long enough to stand as a written report in every sense of the word.\n\n'
        'Second synthetic paragraph of the same write-up.')
SHORT = 'Synthetic note.'
COVER_ALT = 'Synthetic "ridge" & a <synthetic> sky'

# Synthetic Range, newest first, as the pages list it (the undated one last); the active goal comes after them
RANGE_PUB = ['syn-r-story', 'syn-r-flag', 'syn-r-words', 'syn-r-tour', 'syn-r-photo', 'syn-r-short', 'syn-r-paddle',
             'syn-r-raft', 'syn-r-lap', 'syn-r-old', 'syn-r-undated']
COAST_PUB = ['syn-r-cove-b', 'syn-r-cove-c', 'syn-r-cove-a']
PEAKS_PUB = ['syn-r-wall-a', 'syn-r-wall-b']


def load_module(tc, name):
    try:
        return importlib.import_module(name)
    except ImportError as ex:
        tc.fail('%s is not importable: %s' % (name.replace('.', '/') + '.py', ex))


def need(tc, mod, name):
    """mod.name, or a clear failure of the calling test when the contract's function is missing."""
    if not hasattr(mod, name):
        tc.fail('%s.%s is missing (contract-phase5.md)' % (mod.__name__, name))
    return getattr(mod, name)


def ancestors(node):
    out = []
    p = node.parent
    while p is not None:
        out.append(p)
        p = p.parent
    return out


def inner(html_, open_tag, close_tag):
    """What stands between the first `open_tag` and the next `close_tag` of a string."""
    start = html_.index(open_tag) + len(open_tag)
    return html_[start:html_.index(close_tag, start)]


def ml_items(node):
    """The items of a .ml meta line as a reader sees them (the ', ' a screen reader hears between items left out)."""
    out = []
    for mi in node.find_all('span', cls='mi'):
        text = ''.join(c if isinstance(c, str) else ('' if 'sr' in c.classes else c.text(clean=False)) for c in mi.children)
        out.append(helpers.plain_text(text))
    return out


# ---------------------------------------------------------------- the two functions as they were at commit fb425ab

def legacy_region_panel(archive, name, slug, ts, here, meta, first):
    """archive.region_panel as it was at commit fb425ab (Phase 4), copied line for line: what the Map page's panel was
    before the phase. It calls the module's own helpers (region_row, legend, count_line, share_casings), which the
    phase did not touch."""
    SHOW = archive.SHOW
    md = meta['maps'].get('region-%s-desktop' % slug) or {}
    map_id = 'arc-map-' + slug
    anchor = ts[0]
    mp = core.map_block(anchor, here, [('region-%s-desktop' % slug, 'desktop'), ('region-%s-phone' % slug, 'phone')],
                        'assets/maps/', 'rg-' + slug, eager=first, cls='arc-mapv', site_maps=True, attrib=False)
    mp = archive.share_casings(mp.replace('<div class="map', '<div id="%s" class="map' % map_id, 1), 'arc-' + slug)
    cap = '<div class="arc-cap">%s</div>' % core.map_caption(['Pins mark each start and link to the report', 'Full tracks, not trimmed', 'North up'])
    rows = ''.join(archive.region_row(t, here, i >= SHOW and len(ts) > SHOW + 1) for i, t in enumerate(ts))
    n_pub = sum(1 for t in ts if t['kind'] != 'planned')
    return ('<div class="arc-panel" id="region-%s">'
            '<h3 class="arc-panel-h t-h3" id="arc-ph-%s">%s</h3>'
            '<div class="arc-grid"><div class="arc-mapcol">%s%s</div>'
            '<div class="arc-side">%s<div class="arc-inreg"><div class="arc-inreg-h"><h4 class="t-label" id="arc-in-%s">In this region</h4>'
            '<span class="t-mono-s">%s</span></div><ol class="arc-rows" id="arc-rows-%s" aria-labelledby="arc-in-%s arc-ph-%s" data-map-target="%s">%s</ol>%s</div>'
            '</div></div></div>'
            % (slug, slug, esc(name), mp, cap, archive.legend(ts, md), slug, archive.count_line(ts, 'ml--end'), slug, slug, slug, map_id, rows,
               ('<button type="button" class="alink arc-all-btn" aria-expanded="false" aria-controls="arc-rows-%s" hidden>Show all %d%s</button>'
                % (slug, n_pub, icon('chevron-down', 16))) if len(ts) > SHOW + 1 else ''))


PANEL_TAIL = '</div></div></div></div>'       # what closes .arc-inreg, .arc-side, .arc-grid and .arc-panel


def legacy_archive_section(archive, site, here):
    """archive.archive_section as it was at commit fb425ab, copied line for line: the Map page's table of every report."""
    count_n, count_line = archive.count_n, archive.count_line
    active = site.get('active_goals', site['planned'])
    trips = site['published'] + active
    groups = []
    for t in site['published']:
        y = t['date'].year if t['date'] else None
        if not groups or groups[-1][0] != y:
            groups.append((y, []))
        groups[-1][1].append(t)
    if active:
        groups.append(('Planned', list(active)))
    chips = ['<button type="button" class="fchip" role="radio" data-filter="all" aria-checked="true" tabindex="0">'
             '<span class="fchip-l">All</span></button>']
    for a, lab in core.NAV:
        k = sum(1 for t in site['published'] if t['activity'] == a)
        if not k:
            continue
        chips.append('<button type="button" class="fchip" role="radio" data-filter="%s" aria-checked="false" tabindex="-1">'
                     '<span class="chip-sw" style="background:%s" aria-hidden="true"></span><span class="fchip-l">%s</span>'
                     '<span class="fchip-n">%s</span></button>' % (a, core.ACT[a][3], esc(lab), count_n(k)))
    row = lambda t: core.table_row(t, here, tags='' if t['kind'] == 'planned' else core.trip_tags(t, shape=False),  # noqa: E731
                                   attrs=' data-kind="%s"' % t['kind'])
    body, years = [], []
    for y, ts in groups:
        gid = 'yr-%s' % str(y if y is not None else 'undated').lower()
        label = str(y) if y is not None else 'Undated'
        body.append('<div class="arc-yr" data-group="%s"><div class="arc-yr-h"><h3 class="t-label" id="%s">%s</h3>'
                    '<span class="t-mono-s arc-yr-n">%s</span></div><ol class="arc-rows2" aria-labelledby="%s">%s</ol></div>'
                    % (gid, gid, label, count_line(ts, 'ml--end'), gid, ''.join(row(t) for t in ts)))
        k = sum(1 for t in ts if t['kind'] != 'planned')
        years.append('<li data-group="%s"><a href="#%s">%s%s</a></li>'
                     % (gid, gid, label, '' if y == 'Planned' else '<span class="arc-years-n">%s</span>' % count_n(k)))
    index = ('<nav class="arc-years" aria-label="Jump to year"><ul>%s</ul></nav>' % ''.join(years)) if len(years) > 1 else ''
    return ('<section class="arc-all wrap sec" id="all-reports" aria-labelledby="all-reports-h">%s'
            '<div class="arc-filt" role="radiogroup" aria-label="Filter by activity" hidden>%s</div>%s'
            '<p class="sr" id="arc-live" aria-live="polite"></p>'
            '<div class="rtab arc-table"><div aria-hidden="true">%s</div>%s</div></section>'
            % (core.section_head('All reports', count_line(trips), id_='all-reports-h'), ''.join(chips), index,
               core.table_head(), ''.join(body)))


# ---------------------------------------------------------------- the fixture

class RegionFixture(unittest.TestCase):
    DEFAULT = True        # False: setUp writes no trip and builds nothing (the test writes its own site)

    def setUp(self):
        helpers.keep_state(self)          # first: whatever a test registers with core is undone last
        # a fixture's map entry may name a trip its fragment does not draw, which the build reports on stderr once per
        # map (core.drop_keys); that line is kept out of the test run's own output (use() keeps it for a test to read)
        for ctx in (mock.patch.object(core, '_DROP_WARNED', set()), contextlib.redirect_stderr(io.StringIO())):
            ctx.__enter__()
            self.addCleanup(ctx.__exit__, None, None, None)
        self.archive = load_module(self, 'sitegen.pages.archive')
        self.region = load_module(self, 'sitegen.pages.region')
        self.build_mod = load_module(self, 'build')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.trips_dir = os.path.join(self.tmp, 'trips')
        self.site_dir = os.path.join(self.tmp, 'rendered', 'site')
        os.makedirs(self.trips_dir)
        os.makedirs(self.site_dir)
        # the page modules look for rendered/site/ under core.ROOT and each trip's renders under content.RENDERED
        for target, name, value in ((core, 'ROOT', self.tmp), (content, 'RENDERED', os.path.join(self.tmp, 'rendered'))):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self._meta_patch = None
        if self.DEFAULT:
            self.write_default()
            self.use()

    # ------------------------------------------------------------ writing the site

    def mk(self, slug, **meta):
        """One synthetic trip folder (helpers.make_trip): a hike with a track unless meta says otherwise."""
        self.assertTrue(slug.startswith('syn-r-'), slug)
        meta.setdefault('activity', 'hike')
        if not meta.get('days'):
            meta.setdefault('track', True)
        return helpers.make_trip(self.trips_dir, slug, **meta)

    def goal(self, slug, archived=False, **meta):
        """A tick-list goal: a planned route with a goal.json sidecar (archived=True: it keeps its page and is no longer
        an active goal, so no region lists it)."""
        folder = self.mk(slug, kind='planned', track=False, **meta)
        goals = load_module(self, 'goals')
        with open(os.path.join(folder, 'goal.json'), 'w', encoding='utf-8') as fh:
            json.dump(dict(goals.defaults(), status='idea', archived=archived, added_at='2026-01-01'), fh)
        return folder

    def write_default(self):
        mk = self.mk
        cover = [photo('photos/01.webp', PORTRAIT, alt='Synthetic portrait'), photo('photos/02.webp', LANDSCAPE, alt=COVER_ALT, sm=True)]
        # Synthetic Range
        mk('syn-r-story', title='Synthetic Story', date='2026-06-01', region=RANGE, place='Synthetic Basin', body=LONG, photos=cover)
        mk('syn-r-flag', title='Synthetic Flagged Lap', activity='ski', date='2025-12-20', region=RANGE, place='Synthetic Basin', featured=True)
        mk('syn-r-words', title='Synthetic Words', activity='climb', date='2025-08-02', region=RANGE, place='Synthetic Crag', body=LONG)
        mk('syn-r-tour', title='Synthetic Tour', activity='ski', kind='multi-day', date='2025-04-01', end_date='2025-04-02', region=RANGE,
           place='Synthetic Hut', days=[{'title': 'Synthetic Day One', 'date': '2025-04-01', 'body': LONG},
                                        {'title': 'Synthetic Day Two', 'date': '2025-04-02'}])
        mk('syn-r-photo', title='Synthetic Photos Only', activity='mtb', date='2024-09-14', region=RANGE, place='Synthetic Basin',
           photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo')])
        mk('syn-r-short', title='Synthetic Short Note', date='2024-07-01', region=RANGE, body=SHORT, track=False)
        mk('syn-r-paddle', title='Synthetic Paddle', activity='other', subtype='SUP', date='2024-06-01', region=RANGE, place='Synthetic Lake')
        mk('syn-r-raft', title='Synthetic Raft', activity='other', subtype='Rafting', date='2023-06-10', region=RANGE, place='Synthetic River')
        mk('syn-r-lap', title='Synthetic Lap', activity='ski', date='2023-01-15', region=RANGE, place='Synthetic Bowl')
        mk('syn-r-old', title='Synthetic Old Story', date='2022-08-20', region=RANGE, place='Synthetic Ridge', body=LONG,
           photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic old photo')])
        mk('syn-r-undated', title='Synthetic Undated', region=RANGE)
        self.goal('syn-r-goal', title='Synthetic Goal', region=RANGE)
        self.goal('syn-r-shelved', archived=True, title='Synthetic Shelved Goal', region=RANGE)
        # Synthetic Coast: one activity, one year, every report with a track
        mk('syn-r-cove-a', title='Synthetic Cove A', date='2026-01-10', region=COAST, place='Synthetic Cove', body=LONG,
           photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic cove')])
        mk('syn-r-cove-b', title='Synthetic Cove B', date='2026-03-05', region=COAST, place='Synthetic Cove')
        mk('syn-r-cove-c', title='Synthetic Cove C', date='2026-02-02', region=COAST)
        # Synthetic O'Brien & <Peaks>
        mk('syn-r-wall-a', title='Synthetic Wall A', activity='climb', date='2025-05-05', region=PEAKS, place=WALL, body=LONG)
        mk('syn-r-wall-b', title='Synthetic Wall B', activity='mtb', date='2024-05-05', region=PEAKS, place=WALL, body=LONG)
        # a region map and nothing but a planned route; a region without a region map; a journal on no region map
        self.goal('syn-r-plan', title='Synthetic Plan', region=PLANS)
        mk('syn-r-desert', title='Synthetic Desert A', activity='climb', date='2024-10-12', region=DESERT)
        helpers.make_series(self.trips_dir, slug='syn-r-journal', title='Synthetic Journal', region=TRAIL)

    def write_meta(self, mapped, all_regions=None, named=None, extra=None, marks=None):
        """rendered/site/meta.json in the temp dir: a desktop and a phone region map for each name in `mapped`, each with
        a placeholder fragment, as tools/render.py leaves them. named: {region: [slugs]}, the trips a map's entry names
        ('trips'); a region left out of it has no such list, and its Map page group falls back to the trips filed under
        it. marks: {region: svg markup}, what the region's two fragments draw (pins and cluster markers written as
        tools/lib/mapkit.py writes them); a region left out of it has an empty map."""
        maps = {}
        for name in mapped:
            slug = content.slugify(name)
            for size, (w, h) in (('desktop', (1077, 930)), ('phone', (585, 720))):
                key = 'region-%s-%s' % (slug, size)
                maps[key] = {'w': w, 'h': h, 'png': key + '.webp', 'base': key + '.base.svg'}
                if named and name in named:
                    maps[key]['trips'] = list(named[name])
                with open(os.path.join(self.site_dir, key + '.svg.html'), 'w', encoding='utf-8') as fh:
                    fh.write('<svg width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>' % (w, h, w, h, (marks or {}).get(name, '')))
        meta = {'hash': '', 'maps': maps, 'regions': list(mapped),
                'all_regions': list(all_regions if all_regions is not None else list(mapped) + [DESERT])}
        meta.update(extra or {})
        with open(os.path.join(self.site_dir, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(meta, fh)
        return meta

    def use(self, mapped=MAPPED, all_regions=None, named=None, featured=(), only=None, register=True, extra=None, marks=None):
        """Write the site meta, load the temp trips (all of them, or the slugs in `only`) into a site as build.py does,
        name the home page's featured trips, register the site with the meta (as build.py does: without one no region
        would have a page) and build the region pages."""
        self.meta = self.write_meta(mapped, all_regions, named, extra, marks)
        if self._meta_patch is not None:
            self._meta_patch.stop()
        self._meta_patch = mock.patch.object(core, '_SITE_META', [self.meta])
        self._meta_patch.start()
        self.addCleanup(self._meta_patch.stop)
        trips = [t for t in helpers.load_dir(self.trips_dir) if only is None or t['slug'] in only]
        self.site = self.build_mod.site_of(helpers.newest_first(trips))
        self.by = self.site['by_slug']
        self.site['featured'] = [self.by[s] for s in featured]
        if register:
            core.register_site(self.site, self.meta)
        self.regs = self.region.regions(self.site, self.meta)
        # a map entry may name a trip the fixture's fragment does not draw: the build then says so once per map
        # (core.drop_keys), on stderr, kept here instead of in the test run's output
        with mock.patch.object(core, '_DROP_WARNED', set()), contextlib.redirect_stderr(io.StringIO()) as err:
            self.built = self.region.build(self.site)
        self.stderr = err.getvalue()
        self.pages = {p.url: p for p in self.built}
        self._docs = {}

    # ------------------------------------------------------------ reading it

    def here(self, name):
        return 'regions/%s/' % SLUG.get(name, content.slugify(name))

    def page(self, name):
        self.assertIn(self.here(name), self.pages, '%s has no page' % name)
        return self.pages[self.here(name)]

    def html(self, name):
        return self.page(name).html

    def doc(self, name):
        if name not in self._docs:
            self._docs[name] = Doc(self.html(name))
        return self._docs[name]

    def main(self, name):
        return self.doc(name).by_id('main')

    def group(self, name):
        return next(ts for n, _slug, ts in self.regs if n == name)

    def pub(self, name):
        return [t for t in self.group(name) if t['kind'] != 'planned']

    def planned(self, name):
        return [t for t in self.group(name) if t['kind'] == 'planned']

    def one(self, name, id_):
        """The one element of the region's page with this id; fails when the page has none or several."""
        hits = [n for n in self.doc(name).root.walk() if n['id'] == id_]
        self.assertEqual(len(hits), 1, '%s has %d elements with id="%s"' % (self.here(name), len(hits), id_))
        return hits[0]

    def trips(self, *slugs):
        return [self.by[s] for s in slugs]


def names(groups):
    return [name for name, _slug, _ts in groups]


def as_slugs(groups):
    """[(name, slug, [trip slugs])] of region groups, for comparing them by value."""
    return [(name, slug, helpers.slugs(ts)) for name, slug, ts in groups]


# ---------------------------------------------------------------- section 1: which regions get a page

class RuleTests(RegionFixture):

    def setUp(self):
        super().setUp()
        self.listed_trips = need(self, core, 'listed_trips')
        self.region_groups = need(self, core, 'region_groups')
        self.region_pages = need(self, core, 'region_pages')
        self.href = need(self, core, 'region_page_href')

    # ------------------------------------------------------------ core.listed_trips

    def test_listed_trips_are_every_report_and_the_active_goals(self):
        listed = self.listed_trips(self.site)
        # the site's own order (newest first), the archived goal left out: it keeps its page and leaves the lists
        self.assertEqual(helpers.slugs(listed), [t['slug'] for t in self.site['trips'] if t['slug'] != 'syn-r-shelved'])
        self.assertIn('syn-r-shelved', self.by)
        for slug in ('syn-r-goal', 'syn-r-plan', 'syn-r-journal', 'syn-r-desert', 'syn-r-undated'):
            self.assertIn(slug, helpers.slugs(listed))
        self.assertEqual([t['slug'] for t in listed if t['kind'] == 'planned'], helpers.slugs(self.site['active_goals']))

    def test_archive_listed_is_a_wrapper_with_the_same_result(self):
        self.assertEqual(self.archive.listed(self.site), self.listed_trips(self.site))
        self.assertEqual([id(t) for t in self.archive.listed(self.site)], [id(t) for t in self.listed_trips(self.site)])

    def test_an_empty_list_of_active_goals_lists_no_planned_route(self):
        # 'no active goal' is an answer, not a missing key: nothing falls back to every planned route
        site = dict(self.site, active_goals=[])
        self.assertEqual([t for t in self.listed_trips(site) if t['kind'] == 'planned'], [])
        self.assertEqual(helpers.slugs(self.listed_trips(site)), helpers.slugs(self.site['published']))

    def test_without_active_goals_every_planned_route_of_the_site_counts(self):
        # a site dict made without build.site_of (helpers.make_site): 'planned' stands for the active goals
        trips = self.site['trips']
        plain = helpers.make_site(trips, register=False)
        self.assertNotIn('active_goals', plain)
        self.assertEqual(helpers.slugs(self.listed_trips(plain)), helpers.slugs(trips))
        # ... but only the planned routes that list names
        chosen = dict(plain, planned=[self.by['syn-r-plan']])
        self.assertEqual([t['slug'] for t in self.listed_trips(chosen) if t['kind'] == 'planned'], ['syn-r-plan'])
        # a bare dict (core.register_site in a unit test): every planned route counts
        self.assertEqual(helpers.slugs(self.listed_trips({'trips': trips})), helpers.slugs(trips))

    # ------------------------------------------------------------ core.region_groups

    def test_region_groups_are_the_mapped_regions_with_their_trips(self):
        groups = self.region_groups(self.site, self.meta)
        self.assertEqual(as_slugs(groups), [(RANGE, SLUG[RANGE], RANGE_PUB + ['syn-r-goal']),
                                            (COAST, SLUG[COAST], COAST_PUB),
                                            (PEAKS, SLUG[PEAKS], PEAKS_PUB),
                                            (PLANS, SLUG[PLANS], ['syn-r-plan'])])
        for group in groups:
            self.assertIsInstance(group, tuple)
            self.assertEqual(group[1], content.slugify(group[0]))
        # no group for a region without a region map, whatever is filed under it
        self.assertNotIn(DESERT, names(groups))
        self.assertNotIn(TRAIL, names(groups))
        # the trips are the site's own dicts
        self.assertIs(groups[0][2][0], self.by['syn-r-story'])

    def test_archive_regions_is_a_wrapper_with_the_same_result(self):
        self.assertEqual(as_slugs(self.archive.regions(self.site, self.meta)), as_slugs(self.region_groups(self.site, self.meta)))
        self.assertEqual(self.archive.regions(self.site, self.meta), self.region_groups(self.site, self.meta))

    def test_a_group_is_newest_first_with_planned_routes_last(self):
        ts = self.region_groups(self.site, self.meta)[0][2]
        dated = [t for t in ts if t['date']]
        self.assertEqual(dated, sorted(dated, key=lambda t: t['date'], reverse=True))
        self.assertEqual([t['kind'] for t in ts][-1], 'planned')
        self.assertEqual([t['kind'] == 'planned' for t in ts], [False] * 11 + [True])
        # the archived goal is in no group; the undated report is the last report, before the goal
        self.assertNotIn('syn-r-shelved', helpers.slugs(ts))
        self.assertEqual(helpers.slugs(ts)[-2:], ['syn-r-undated', 'syn-r-goal'])

    def test_groups_are_ordered_by_published_reports_then_by_name(self):
        # the order of meta 'regions' never matters; a planned route is not a report, however many a region has
        self.use(mapped=[PLANS, PEAKS, COAST, RANGE])
        self.assertEqual(names(self.region_groups(self.site, self.meta)), [RANGE, COAST, PEAKS, PLANS])
        for k in range(4):
            self.goal('syn-r-plan-%d' % k, title='Synthetic Plan %d' % k, region=PEAKS)
        self.mk('syn-r-tie', title='Synthetic Tie', date='2021-01-01', region='Synthetic Alp')
        self.mk('syn-r-tie-2', title='Synthetic Tie Two', date='2021-01-02', region='Synthetic Alp')
        self.use(mapped=[PLANS, PEAKS, 'Synthetic Alp', COAST, RANGE])
        groups = self.region_groups(self.site, self.meta)
        # 11, 3, then two regions of two reports each from A to Z (the one with four more planned routes is not first)
        self.assertEqual(names(groups), [RANGE, COAST, 'Synthetic Alp', PEAKS, PLANS])
        self.assertEqual([sum(1 for t in ts if t['kind'] != 'planned') for _n, _s, ts in groups], [11, 3, 2, 2, 0])
        self.assertEqual(len(groups[3][2]), 6)

    def test_a_mapped_region_without_a_listed_trip_is_dropped(self):
        # a region map whose trips are gone, one with nothing but an archived goal, one with nothing but a journal
        self.goal('syn-r-old-plan', archived=True, title='Synthetic Old Plan', region='Synthetic Shelf')
        self.use(mapped=MAPPED + ['Synthetic Empty', 'Synthetic Shelf', TRAIL])
        groups = self.region_groups(self.site, self.meta)
        self.assertEqual(names(groups), [RANGE, COAST, PEAKS, PLANS])
        self.assertEqual([t['region'] for t in self.site['trips'] if t['slug'] in ('syn-r-old-plan', 'syn-r-journal')],
                         [TRAIL, 'Synthetic Shelf'])

    def test_a_journal_is_in_no_group_of_the_region_it_is_filed_under(self):
        helpers.make_series(self.trips_dir, slug='syn-r-range-journal', title='Synthetic Range Journal', region=RANGE)
        self.use()
        self.assertEqual(self.by['syn-r-range-journal']['region'], RANGE)
        ts = self.region_groups(self.site, self.meta)[0][2]
        self.assertEqual(helpers.slugs(ts), RANGE_PUB + ['syn-r-goal'])
        self.assertNotIn('series', [t['kind'] for t in ts])

    def test_the_trips_a_map_names_are_the_group(self):
        # the map's own entry decides when it has a list (tools/render.py writes the trips it drew): a trip of the region
        # that the map does not name is left out, one filed elsewhere that it names is in; a slug that is no listed trip
        # (unknown, or the archived goal) is skipped
        named = {RANGE: ['syn-r-lap', 'syn-r-goal', 'syn-r-story', 'syn-r-desert', 'syn-r-shelved', 'syn-r-gone']}
        self.use(named=named)
        groups = self.region_groups(self.site, self.meta)
        self.assertEqual(as_slugs(groups)[:2], [(COAST, SLUG[COAST], COAST_PUB),
                                                (RANGE, SLUG[RANGE], ['syn-r-story', 'syn-r-desert', 'syn-r-lap', 'syn-r-goal'])])
        self.assertEqual(self.by['syn-r-desert']['region'], DESERT)
        # an empty list is no list: the group falls back to the trips filed under the region
        self.use(named={RANGE: []})
        self.assertEqual(as_slugs(self.region_groups(self.site, self.meta))[0], (RANGE, SLUG[RANGE], RANGE_PUB + ['syn-r-goal']))

    def test_the_desktop_maps_entry_is_the_one_that_is_read(self):
        meta = json.loads(json.dumps(self.meta))
        meta['maps']['region-%s-phone' % SLUG[RANGE]]['trips'] = ['syn-r-lap']
        self.assertEqual(as_slugs(self.region_groups(self.site, meta))[0][2], RANGE_PUB + ['syn-r-goal'])
        meta['maps']['region-%s-desktop' % SLUG[RANGE]]['trips'] = ['syn-r-lap']
        self.assertEqual(as_slugs(self.region_groups(self.site, meta))[2:], [(RANGE, SLUG[RANGE], ['syn-r-lap']),
                                                                             (PLANS, SLUG[PLANS], ['syn-r-plan'])])

    def test_without_a_meta_the_groups_come_from_cores_site_meta(self):
        self.assertEqual(as_slugs(self.region_groups(self.site)), as_slugs(self.region_groups(self.site, self.meta)))
        self.assertEqual(as_slugs(self.region_groups(self.site, None)), as_slugs(self.region_groups(self.site, self.meta)))
        other = {'hash': '', 'maps': self.meta['maps'], 'regions': [COAST]}
        with mock.patch.object(core, '_SITE_META', [other]):
            self.assertEqual(names(self.region_groups(self.site)), [COAST])
            self.assertEqual(names(self.region_groups(self.site, self.meta)), [RANGE, COAST, PEAKS, PLANS])
        # a meta that names no region has no group (and an empty meta is still a meta: nothing is read in its place)
        self.assertEqual(self.region_groups(self.site, {'maps': {}, 'regions': []}), [])
        self.assertEqual(self.region_groups(self.site, {'maps': {}}), [])
        self.assertEqual(self.region_groups(self.site, {}), [])
        self.assertEqual(self.region_pages(self.site, {}), [])
        self.assertEqual(need(self, self.region, 'regions')(self.site, {}), [])

    # ------------------------------------------------------------ core.region_pages (REVISED in round 2)

    def test_region_pages_are_the_mapped_regions_with_a_published_report(self):
        pages = self.region_pages(self.site, self.meta)
        self.assertEqual(as_slugs(pages), [(RANGE, SLUG[RANGE], RANGE_PUB + ['syn-r-goal']),
                                           (COAST, SLUG[COAST], COAST_PUB),
                                           (PEAKS, SLUG[PEAKS], PEAKS_PUB)])
        for page in pages:
            self.assertIsInstance(page, tuple)
            self.assertEqual(page[1], content.slugify(page[0]))
        self.assertIs(pages[0][2][0], self.by['syn-r-story'])            # the site's own trip dicts
        # Here no map's entry names its trips and no journal is filed under a mapped region, so the Map page's groups
        # hold the same trips; the region of planned routes only has a group and no page
        groups = self.region_groups(self.site, self.meta)
        self.assertEqual(pages, groups[:3])
        self.assertEqual(names(groups)[3:], [PLANS])

    def test_a_page_lists_what_the_content_files_under_the_region_not_what_the_map_names(self):
        # A map that is out of step with the content: its entry names two reports and the goal of the region, a report
        # that is filed elsewhere, the archived goal and a slug that is gone. Since it was drawn a report was added, and
        # a journal is filed under the region. The page lists by the `region` field; the Map page's group keeps the
        # map entry's rule. Both are asked on the same site and the same meta
        helpers.make_series(self.trips_dir, slug='syn-r-range-journal', title='Synthetic Range Journal', region=RANGE)
        self.mk('syn-r-new', title='Synthetic New Report', date='2026-07-04', region=RANGE)
        named = {RANGE: ['syn-r-lap', 'syn-r-goal', 'syn-r-story', 'syn-r-desert', 'syn-r-shelved', 'syn-r-gone']}
        self.use(named=named)
        want = ['syn-r-new'] + RANGE_PUB[:7] + ['syn-r-range-journal'] + RANGE_PUB[7:] + ['syn-r-goal']
        page = next(p for p in self.region_pages(self.site, self.meta) if p[0] == RANGE)
        self.assertEqual((page[0], page[1], helpers.slugs(page[2])), (RANGE, SLUG[RANGE], want))
        listed = helpers.slugs(page[2])
        # every trip filed under the name, whatever its kind: newest first, the active goal after the reports
        self.assertEqual(want, [t['slug'] for t in self.listed_trips(self.site) if t['region'] == RANGE and t['kind'] != 'planned'] + ['syn-r-goal'])
        self.assertEqual({self.by[s]['kind'] for s in listed}, {'trip', 'multi-day', 'series', 'planned'})
        self.assertEqual({self.by[s]['region'] for s in listed}, {RANGE})
        for slug, why in (('syn-r-short', 'a report without a track'), ('syn-r-range-journal', 'a journal'),
                          ('syn-r-new', 'a report added since the map was drawn'), ('syn-r-words', 'a report the map does not name'),
                          ('syn-r-undated', 'an undated report')):
            self.assertIn(slug, listed, why)
        self.assertFalse(core.has_track(self.by['syn-r-short']))
        for slug, why in (('syn-r-desert', 'named by the map, filed under another region'), ('syn-r-shelved', 'an archived goal'),
                          ('syn-r-gone', 'a slug that is no trip')):
            self.assertNotIn(slug, listed, why)
        self.assertEqual(self.by['syn-r-desert']['region'], DESERT)
        # the Map page's group for the same region, from the same call arguments: the trips the map's entry names
        group = next(g for g in self.region_groups(self.site, self.meta) if g[0] == RANGE)
        self.assertEqual(helpers.slugs(group[2]), ['syn-r-story', 'syn-r-desert', 'syn-r-lap', 'syn-r-goal'])
        self.assertEqual(as_slugs(self.archive.regions(self.site, self.meta)), as_slugs(self.region_groups(self.site, self.meta)))
        # ... and the page that is built lists the same trips beside its map and in its table
        self.assertEqual([li['data-key'] for li in self.one(RANGE, 'arc-rows-' + SLUG[RANGE]).elements()], want)
        self.assertEqual([a['data-key'] for a in self.one(RANGE, 'all-reports').find_all('a', cls='rtab-r')], want)
        self.assertNotIn('syn-r-desert', self.html(RANGE))

    def test_the_pages_report_count_is_the_count_the_trips_page_gives_the_region(self):
        # one spelling per region (as on the real site): whatever the map entries say, a page counts the reports that
        # trips.regions_of counts for its name, the number beside the Trips page's 'By region' link to it
        trips = load_module(self, 'sitegen.pages.trips')
        helpers.make_series(self.trips_dir, slug='syn-r-coast-journal', title='Synthetic Coast Journal', region=COAST)
        self.mk('syn-r-peaks-plain', title='Synthetic Peaks Walk', date='2020-02-02', region=PEAKS, track=False)
        self.use(named={RANGE: ['syn-r-lap'], COAST: ['syn-r-cove-a', 'syn-r-desert'], PEAKS: PEAKS_PUB})
        counted = {name: k for name, _slug, k in trips.regions_of(self.site['published'])}
        self.assertEqual([counted[name] for name in PAGES], [11, 4, 3])
        self.assertEqual(len({content.slugify(t['region']) for t in self.site['published']}), len({t['region'] for t in self.site['published']}))
        pages = self.region_pages(self.site, self.meta)
        self.assertEqual(names(pages), PAGES)
        for name, _slug, ts in pages:
            with self.subTest(region=name):
                self.assertEqual(sum(1 for t in ts if t['kind'] != 'planned'), counted[name])
                # the head of the page says that number, and so does the link that leads to it
                self.assertEqual(stat_lines(self.main(name).find('p', cls='reg-stats'))[0][0], '%d REPORTS' % counted[name])
                link = [a for a in Doc(trips.browse(self.site)).find_all('a') if a['href'] == '../regions/%s/' % SLUG[name]]
                self.assertEqual([a.text() for a in link], ['%s, %d reports' % (name, counted[name])])
        # the Map page's groups, by the map entries' rule, count otherwise on this site
        grouped = {name: sum(1 for t in ts if t['kind'] != 'planned') for name, _slug, ts in self.region_groups(self.site, self.meta)}
        self.assertEqual([grouped[name] for name in PAGES], [1, 2, 2])

    def test_a_journal_is_a_report_of_the_region_it_is_filed_under(self):
        # the Trail of the fixture has a journal and nothing else: with a region map it has a page (the Map page has
        # no group for it: a series is on no region map)
        self.use(mapped=MAPPED + [TRAIL])
        self.assertEqual(as_slugs(self.region_pages(self.site, self.meta))[3], (TRAIL, SLUG[TRAIL], ['syn-r-journal']))
        self.assertNotIn(TRAIL, names(self.region_groups(self.site, self.meta)))
        self.assertEqual(self.by['syn-r-journal']['kind'], 'series')
        self.assertEqual(self.href('', TRAIL), 'regions/synthetic-trail/')
        self.assertEqual([li['data-key'] for li in self.one(TRAIL, 'arc-rows-' + SLUG[TRAIL]).elements()], ['syn-r-journal'])
        self.assertEqual([a['href'] for a in self.one(TRAIL, 'all-reports').find_all('a', cls='rtab-r')], ['../../trips/syn-r-journal/'])

    def test_a_region_without_a_region_map_has_no_page(self):
        # named in meta 'regions' and no entry under 'maps': the Map page has a group for it (the trips filed under
        # it), and it has no page
        meta = json.loads(json.dumps(self.meta))
        meta['regions'].append(DESERT)
        self.assertIn((DESERT, SLUG[DESERT], ['syn-r-desert']), as_slugs(self.region_groups(self.site, meta)))
        self.assertEqual(names(self.region_pages(self.site, meta)), PAGES)
        # either render of the region map is one; a map of another kind for the same slug is not
        for key, want in (('region-synthetic-desert-desktop', PAGES + [DESERT]), ('region-synthetic-desert-phone', PAGES + [DESERT]),
                          ('ski-synthetic-desert-desktop', PAGES), ('region-synthetic-desert', PAGES), ('region-synthetic-desert-wide', PAGES)):
            with self.subTest(key=key):
                one = json.loads(json.dumps(meta))
                one['maps'][key] = {'w': 10, 'h': 10}
                self.assertEqual(names(self.region_pages(self.site, one)), want)
        # a region map whose region meta 'regions' does not name has no page either
        gone = json.loads(json.dumps(self.meta))
        gone['regions'].remove(COAST)
        self.assertIn('region-%s-desktop' % SLUG[COAST], gone['maps'])
        self.assertEqual(names(self.region_pages(self.site, gone)), [RANGE, PEAKS])
        # a meta without one of the two keys, or with nothing under it, gives no page (and is no error)
        for meta in ({'regions': [RANGE]}, {'regions': [RANGE], 'maps': None}, {'regions': [RANGE], 'maps': {}}, {'maps': self.meta['maps']},
                     {'maps': self.meta['maps'], 'regions': None}, {'maps': self.meta['maps'], 'regions': []}):
            self.assertEqual(self.region_pages(self.site, meta), [])

    def test_one_published_report_is_enough_and_a_planned_route_is_not(self):
        self.mk('syn-r-plans-report', title='Synthetic Plans Report', date='2020-01-01', region=PLANS)
        self.use()
        self.assertEqual(names(self.region_pages(self.site, self.meta)), [RANGE, COAST, PEAKS, PLANS])
        self.assertEqual(helpers.slugs(self.region_pages(self.site, self.meta)[3][2]), ['syn-r-plans-report', 'syn-r-plan'])

    def test_the_report_has_to_be_filed_under_the_region(self):
        # a map entry that names another region's report gives the Map page's group a report, and the region no page
        self.use(named={PLANS: ['syn-r-plan', 'syn-r-desert']})
        group = next(g for g in self.region_groups(self.site, self.meta) if g[0] == PLANS)
        self.assertEqual(helpers.slugs(group[2]), ['syn-r-desert', 'syn-r-plan'])
        self.assertEqual(names(self.region_pages(self.site, self.meta)), PAGES)
        self.assertIsNone(self.href('', PLANS))
        # an archived goal is no listed trip: with nothing else under the name there is no page
        self.goal('syn-r-old-plan', archived=True, title='Synthetic Old Plan', region='Synthetic Shelf')
        self.use(mapped=MAPPED + ['Synthetic Shelf', 'Synthetic Empty'])
        self.assertEqual(names(self.region_pages(self.site, self.meta)), PAGES)

    def test_pages_are_ordered_by_published_reports_then_by_name(self):
        # the order of meta 'regions' never orders the pages; a planned route is not a report, however many there are
        self.use(mapped=[PLANS, PEAKS, COAST, RANGE])
        self.assertEqual(names(self.region_pages(self.site, self.meta)), [RANGE, COAST, PEAKS])
        for k in range(4):
            self.goal('syn-r-plan-%d' % k, title='Synthetic Plan %d' % k, region=PEAKS)
        self.mk('syn-r-tie', title='Synthetic Tie', date='2021-01-01', region='Synthetic Alp')
        self.mk('syn-r-tie-2', title='Synthetic Tie Two', date='2021-01-02', region='Synthetic Alp')
        self.use(mapped=[PLANS, PEAKS, 'Synthetic Alp', COAST, RANGE])
        pages = self.region_pages(self.site, self.meta)
        # 11, 3, then two regions of two reports each from A to Z (the one with four more planned routes is not first)
        self.assertEqual(names(pages), [RANGE, COAST, 'Synthetic Alp', PEAKS])
        self.assertEqual([sum(1 for t in ts if t['kind'] != 'planned') for _n, _s, ts in pages], [11, 3, 2, 2])
        self.assertEqual([t['kind'] for t in pages[3][2]], ['trip', 'trip'] + ['planned'] * 4)
        self.assertEqual([p.url for p in self.built], ['regions/%s/' % s for _n, s, _ts in pages])

    def test_a_name_without_a_slug_gets_no_page(self):
        self.mk('syn-r-odd', title='Synthetic Odd', date='2021-03-03', region='???')
        self.use(mapped=MAPPED + ['???'])
        self.assertEqual(content.slugify('???'), '')
        self.assertIn(('???', '', ['syn-r-odd']), as_slugs(self.region_groups(self.site, self.meta)))
        self.assertIn('region--desktop', self.meta['maps'])                   # even with a map entry under its empty slug
        self.assertEqual(names(self.region_pages(self.site, self.meta)), PAGES)
        self.assertNotIn('regions//', [p.url for p in self.built])
        self.assertIsNone(self.href('', '???'))

    def test_of_two_names_with_one_slug_only_the_earlier_gets_the_page(self):
        twin = 'Synthetic coast'
        self.assertEqual(content.slugify(twin), SLUG[COAST])
        self.mk('syn-r-twin', title='Synthetic Twin', date='2021-04-04', region=twin)
        self.use(mapped=MAPPED + [twin])
        self.assertEqual(names(self.region_groups(self.site, self.meta)), [RANGE, COAST, PEAKS, twin, PLANS])     # the Map page has both
        self.assertEqual(names(self.region_pages(self.site, self.meta)), PAGES)
        self.assertEqual([p.url for p in self.built].count('regions/%s/' % SLUG[COAST]), 1)
        self.assertEqual(self.href('', COAST), 'regions/synthetic-coast/')
        self.assertIsNone(self.href('', twin))
        # the page lists by the exact name: the other spelling's report is not on it
        self.assertEqual(helpers.slugs(self.group(COAST)), COAST_PUB)
        self.assertNotIn('syn-r-twin', self.html(COAST))
        # 'Earlier' is the order of meta 'regions' (REVISED in round 2): the other spelling does not take the page by
        # having more reports, nor by the alphabet
        for k in range(3):
            self.mk('syn-r-twin-%d' % k, title='Synthetic Twin %d' % k, date='2021-05-0%d' % (k + 1), region=twin)
        self.use(mapped=MAPPED + [twin])
        self.assertEqual(names(self.region_groups(self.site, self.meta))[:3], [RANGE, twin, COAST])               # four reports, then three
        self.assertEqual(as_slugs(self.region_pages(self.site, self.meta))[1], (COAST, SLUG[COAST], COAST_PUB))
        self.assertEqual(names(self.region_pages(self.site, self.meta)), PAGES)
        self.assertIsNone(self.href('', twin))
        # named first, it is the one with the page (and the pages are still ordered by their reports)
        self.use(mapped=[twin] + MAPPED)
        self.assertEqual(names(self.region_pages(self.site, self.meta)), [RANGE, twin, PEAKS])
        self.assertEqual(core._REGION_PAGES, {RANGE: SLUG[RANGE], twin: SLUG[COAST], PEAKS: SLUG[PEAKS]})
        self.assertIsNone(self.href('', COAST))
        self.assertEqual(self.html(COAST).count('<h1 id="reg-title" class="t-d1">Synthetic coast</h1>'), 1)
        self.assertEqual(helpers.slugs(self.group(twin)), ['syn-r-twin-2', 'syn-r-twin-1', 'syn-r-twin-0', 'syn-r-twin'])

    def test_an_earlier_name_that_gets_no_page_does_not_take_the_slug(self):
        # the contract's 'a slug not already taken by an earlier name' is read as the code reads it: a name takes its
        # slug by getting a page. An earlier spelling with nothing published under it leaves the page to the next one
        caps = 'SYNTHETIC COAST'
        self.assertEqual(content.slugify(caps), SLUG[COAST])
        self.goal('syn-r-caps-goal', title='Synthetic Caps Goal', region=caps)
        self.use(mapped=[caps] + MAPPED)
        self.assertEqual(self.meta['regions'][:2], [caps, RANGE])
        self.assertEqual(names(self.region_pages(self.site, self.meta)), PAGES)
        self.assertEqual(self.href('', COAST), 'regions/synthetic-coast/')
        self.assertIsNone(self.href('', caps))

    def test_without_a_meta_the_pages_come_from_cores_site_meta(self):
        self.assertEqual(self.region_pages(self.site), self.region_pages(self.site, self.meta))
        self.assertEqual(self.region_pages(self.site, None), self.region_pages(self.site, self.meta))
        with mock.patch.object(core, '_SITE_META', [{'hash': '', 'maps': self.meta['maps'], 'regions': [PEAKS, PLANS]}]):
            self.assertEqual(names(self.region_pages(self.site)), [PEAKS])
            self.assertEqual(names(self.region_pages(self.site, self.meta)), PAGES)
        # an empty meta is a meta: nothing is asked in its place
        self.assertEqual(self.region_pages(self.site, {}), [])
    # ------------------------------------------------------------ region.regions, region.url

    def test_region_regions_is_core_region_pages(self):
        regions = need(self, self.region, 'regions')
        self.assertEqual(regions(self.site, self.meta), self.region_pages(self.site, self.meta))
        self.assertEqual(names(regions(self.site, self.meta)), PAGES)
        only_coast = {'hash': '', 'maps': self.meta['maps'], 'regions': [COAST]}
        self.assertEqual(names(regions(self.site, only_coast)), [COAST])
        self.assertEqual(regions(self.site, {'maps': {}, 'regions': []}), [])

    def test_region_regions_without_a_meta_reads_the_archive_modules_site_meta(self):
        # archive.site_meta() is rendered/site/meta.json under core.ROOT, read each time; core.site_meta() is the copy
        # core keeps. They are the same file in a build; here the copy is swapped to tell which one is asked
        regions = need(self, self.region, 'regions')
        self.assertEqual(self.archive.site_meta(), self.meta)
        with mock.patch.object(core, '_SITE_META', [{'hash': '', 'maps': {}, 'regions': []}]):
            self.assertEqual(self.region_pages(self.site), [])
            self.assertEqual(names(regions(self.site)), PAGES)
            self.assertEqual(names(regions(self.site, None)), PAGES)
        with mock.patch.object(self.archive, 'site_meta', lambda: {'maps': self.meta['maps'], 'regions': [PEAKS]}):
            self.assertEqual(names(regions(self.site)), [PEAKS])
            self.assertEqual(names(regions(self.site, self.meta)), PAGES)

    def test_region_url(self):
        url = need(self, self.region, 'url')
        self.assertEqual(url(RANGE), 'regions/synthetic-range/')
        self.assertEqual(url(PEAKS), 'regions/synthetic-obrien-peaks/')
        self.assertEqual(url('Synthétique Côte'), 'regions/synthetique-cote/')
        for name in PAGES:
            self.assertEqual(url(name), 'regions/%s/' % content.slugify(name))
        self.assertEqual([p.url for p in self.built], [url(name) for name in PAGES])

    # ------------------------------------------------------------ core.region_page_href and core.register_site

    def test_register_site_records_the_regions_with_a_page(self):
        self.assertEqual(core._REGION_PAGES, {RANGE: 'synthetic-range', COAST: 'synthetic-coast', PEAKS: 'synthetic-obrien-peaks'})

    def test_region_page_href_is_the_relative_link_to_the_page(self):
        for here, prefix in (('', ''), ('map/', '../'), ('trips/', '../'), ('trips/syn-r-story/', '../../'),
                             ('trips/syn-r-story/map/', '../../../'), ('regions/synthetic-coast/', '../../'), ('404.html', '')):
            for name in PAGES:
                with self.subTest(here=here, region=name):
                    self.assertEqual(self.href(here, name), prefix + 'regions/%s/' % SLUG[name])
                    self.assertEqual(self.href(here, name), core.link(here, 'regions/%s/' % SLUG[name]))

    def test_region_page_href_is_none_for_a_region_without_a_page(self):
        # a region of planned routes only, one without a region map, the journal's, one nobody filed anything under,
        # another spelling of a region that has one, and no region at all
        for name in (PLANS, DESERT, TRAIL, 'Synthetic Nowhere', 'synthetic range', 'synthetic-range', ' Synthetic Range', 'Synthetic Range ',
                     'SYNTHETIC RANGE', '', None):
            with self.subTest(region=name):
                self.assertIsNone(self.href('trips/syn-r-story/', name))
                self.assertIsNone(self.href('', name))

    def test_before_a_site_is_registered_no_region_has_a_page(self):
        core._REGION_PAGES.clear()                                    # core as it is when nothing has registered a site
        for name in PAGES + [PLANS, DESERT, None]:
            self.assertIsNone(self.href('', name))
            self.assertIsNone(self.href('trips/syn-r-story/', name))
        # the pages are still there to be asked for: only the record is empty
        self.assertEqual(names(self.region_pages(self.site, self.meta)), PAGES)
        core.register_site(self.site, self.meta)
        self.assertEqual(self.href('', RANGE), 'regions/synthetic-range/')

    def test_register_site_clears_what_an_earlier_site_registered(self):
        record = core._REGION_PAGES
        self.assertEqual(sorted(record), sorted(PAGES))
        self.use(mapped=[COAST, PLANS])                                # the same trips, one region map with reports
        self.assertIs(core._REGION_PAGES, record)                      # the same dict, cleared and refilled
        self.assertEqual(record, {COAST: 'synthetic-coast'})
        self.assertIsNone(self.href('', RANGE))
        self.assertIsNone(self.href('', PEAKS))
        self.assertEqual(self.href('', COAST), 'regions/synthetic-coast/')
        self.use(mapped=[])                                            # a site without region maps: no page at all
        self.assertEqual(record, {})
        for name in PAGES:
            self.assertIsNone(self.href('', name))
        self.assertEqual(self.built, [])

    def test_register_site_records_the_pages_of_the_meta_it_is_handed(self):
        # REVISED in round 2: region_pages(site, meta) for the meta of the call, whatever core's own copy says and
        # whatever is on disk (the fixture's file names all four region maps)
        other = {'hash': '', 'maps': self.meta['maps'], 'regions': [PEAKS, PLANS]}
        with mock.patch.object(core, '_SITE_META', [other]):
            core.register_site(self.site, self.meta)
            self.assertEqual(sorted(core._REGION_PAGES), sorted(PAGES))
            core.register_site(self.site, {'maps': self.meta['maps'], 'regions': [COAST]})
            self.assertEqual(core._REGION_PAGES, {COAST: SLUG[COAST]})
        core.register_site(self.site, other)
        self.assertEqual(core._REGION_PAGES, {PEAKS: SLUG[PEAKS]})
        self.assertEqual(core._REGION_PAGES, {name: slug for name, slug, _ts in self.region_pages(self.site, other)})
        core.register_site(self.site, meta=self.meta)                  # by keyword as well
        self.assertEqual(core._REGION_PAGES, {name: slug for name, slug, _ts in self.region_pages(self.site, self.meta)})
        self.assertEqual(core._REGION_PAGES, {RANGE: 'synthetic-range', COAST: 'synthetic-coast', PEAKS: 'synthetic-obrien-peaks'})
        # an empty meta is a meta: it names no region map, so no region has a page, and nothing is asked in its place
        core.register_site(self.site, {})
        self.assertEqual(core._REGION_PAGES, {})

    def test_without_a_meta_no_region_has_a_page(self):
        # REVISED in round 2: every test helper registers this way (helpers.make_site), and every caller then does what
        # it did before the phase. core's own copy of the site meta and the file under core.ROOT both name the region
        # maps of this fixture, and neither is asked
        calls = (lambda: core.register_site(self.site), lambda: core.register_site(self.site, None),
                 lambda: core.register_site(self.site, meta=None), lambda: helpers.make_site(self.site['trips']),
                 lambda: core.register_site({'trips': self.site['trips']}))
        for call in calls:
            core.register_site(self.site, self.meta)
            self.assertEqual(sorted(core._REGION_PAGES), sorted(PAGES))
            call()
            self.assertEqual(core._REGION_PAGES, {})
            for name in PAGES:
                self.assertIsNone(self.href('', name))
                self.assertIsNone(self.href('trips/syn-r-story/', name))
        self.assertEqual(names(self.region_pages(self.site)), PAGES)                              # core.site_meta() would give them
        self.assertEqual(names(self.region_pages(self.site, core.read_site_meta())), PAGES)       # and so would the file

    def test_without_a_meta_nothing_is_read_from_rendered(self):
        # core.ROOT is the fixture's folder, whose rendered/site/meta.json gives three region pages when it is read,
        # and core's cached copy is emptied, so a call of core.site_meta() would have to read that file
        rendered = os.path.join(self.tmp, 'rendered') + os.sep
        opened = []
        real_open = open

        def spy(path, *args, **kwargs):
            if isinstance(path, (str, bytes, os.PathLike)) and os.path.abspath(os.fsdecode(path)).startswith(rendered):
                opened.append(os.fsdecode(path))
            return real_open(path, *args, **kwargs)

        def refuse(*args, **kwargs):
            raise AssertionError('registering a site without a site meta read one')

        for register in (lambda: core.register_site(self.site), lambda: core.register_site(self.site, None),
                         lambda: helpers.make_site(self.site['trips'])):
            # 1. with everything that could read the meta refusing to
            with mock.patch.object(core, '_SITE_META', []) as cache, mock.patch.object(core, 'read_site_meta', refuse), \
                    mock.patch.object(core, 'site_meta', refuse), mock.patch.object(core, 'read_json', refuse), \
                    mock.patch.object(self.archive, 'site_meta', refuse):
                register()
                self.assertEqual(core._REGION_PAGES, {})
                self.assertEqual(cache, [])
            # 2. with the file there to be read: no file under rendered/ is opened, and nothing is kept
            with mock.patch.object(core, '_SITE_META', []) as cache, mock.patch('builtins.open', spy):
                register()
                self.assertEqual(opened, [])
                self.assertEqual(cache, [])
                self.assertEqual(core._REGION_PAGES, {})
        # the proof is not an empty one: the same folder, read, gives the three pages (and the spy sees the read)
        with mock.patch.object(core, '_SITE_META', []) as cache, mock.patch('builtins.open', spy):
            core.register_site(self.site, core.read_site_meta())
            self.assertEqual(sorted(core._REGION_PAGES), sorted(PAGES))
            self.assertEqual([os.path.relpath(p, self.tmp) for p in opened], [os.path.join('rendered', 'site', 'meta.json')])
            self.assertEqual(cache, [])                                # read_site_meta keeps nothing either
            self.assertEqual(names(self.region_pages(self.site)), PAGES)
            self.assertEqual(cache, [self.meta])                       # core.site_meta() is the call that reads once and keeps

    def test_a_bare_site_dict_registers(self):
        # the unit tests' sites (helpers.make_site): 'trips' and no goal lists. With a meta they have their region pages
        core.register_site({'trips': self.site['trips']}, self.meta)
        self.assertEqual(sorted(core._REGION_PAGES), sorted(PAGES))
        plain = helpers.make_site(self.site['trips'])                  # registered without one: none
        self.assertNotIn('active_goals', plain)
        self.assertEqual(core._REGION_PAGES, {})
        core.register_site(plain, self.meta)
        self.assertEqual(sorted(core._REGION_PAGES), sorted(PAGES))
        core.register_site(helpers.make_site([], register=False), self.meta)
        self.assertEqual(core._REGION_PAGES, {})

    def test_the_other_things_register_site_records_are_as_before(self):
        self.assertEqual(sorted(core._TRIPS_BY_URL), sorted(t['url'] for t in self.site['trips']))
        self.assertEqual(core._OTHER_SUBS, ['Rafting', 'SUP'])
        self.assertIsNone(core.site_share())
        self.use(featured=('syn-r-cove-a',))
        self.assertEqual(core.site_share(), core.share_photo(self.by['syn-r-cove-a']))
        # ... and they are the same with a meta and without one: the meta decides the region pages and nothing else
        with_meta = [(k, v.copy()) for k, v in sorted(vars(core).items())
                     if k.startswith('_') and not k.startswith('__') and isinstance(v, (list, dict)) and k != '_REGION_PAGES']
        core.register_site(self.site)
        without = [(k, v.copy()) for k, v in sorted(vars(core).items())
                   if k.startswith('_') and not k.startswith('__') and isinstance(v, (list, dict)) and k != '_REGION_PAGES']
        self.assertEqual(without, with_meta)
        self.assertIn('_TRIPS_BY_URL', [k for k, _v in with_meta])
        self.assertEqual(core._REGION_PAGES, {})

    # ------------------------------------------------------------ core.read_site_meta, core.site_meta, archive.site_meta

    def test_read_site_meta_is_the_file_as_it_is_on_disk_now(self):
        read = need(self, core, 'read_site_meta')
        self.assertEqual(read(), self.meta)
        self.assertIsNot(read(), read())                               # read at each call, never kept
        changed = self.write_meta([COAST])
        self.assertEqual(read(), changed)
        self.assertEqual(read()['regions'], [COAST])
        # core's cached copy is neither asked nor filled
        with mock.patch.object(core, '_SITE_META', [{'maps': {}, 'regions': ['Synthetic Cached']}]):
            self.assertEqual(read(), changed)
        with mock.patch.object(core, '_SITE_META', []) as cache:
            read()
            self.assertEqual(cache, [])
        # it is rendered/site/meta.json under core.ROOT; without the file there is no map and no region
        with tempfile.TemporaryDirectory() as other, mock.patch.object(core, 'ROOT', other):
            self.assertEqual(read(), {'maps': {}, 'regions': []})
            os.makedirs(os.path.join(other, 'rendered', 'site'))
            with open(os.path.join(other, 'rendered', 'site', 'meta.json'), 'w', encoding='utf-8') as fh:
                json.dump({'maps': {}, 'regions': ['Synthetic Elsewhere']}, fh)
            self.assertEqual(read(), {'maps': {}, 'regions': ['Synthetic Elsewhere']})
            self.assertEqual(self.region_pages(self.site, read()), [])
        self.assertEqual(read(), changed)

    def test_site_meta_is_that_file_read_once(self):
        with mock.patch.object(core, '_SITE_META', []) as cache:
            first = core.site_meta()
            self.assertEqual(first, self.meta)
            self.assertEqual(cache, [first])
            self.write_meta([COAST])
            self.assertIs(core.site_meta(), first)                     # the copy: the file is not read again
            self.assertEqual(core.read_site_meta()['regions'], [COAST])
            self.assertEqual(len(cache), 1)                            # and nothing more was kept
        reads = []
        real = core.read_site_meta
        with mock.patch.object(core, '_SITE_META', []), mock.patch.object(core, 'read_site_meta', lambda: reads.append(1) or real()):
            for _k in range(3):
                core.site_meta()
                core.region_pages(self.site)
                core.region_groups(self.site)
                core.region_map_href('', RANGE)
            self.assertEqual(reads, [1])                               # one read for every caller of the cached copy
        marker = {'maps': {}, 'regions': ['Synthetic Marker']}
        with mock.patch.object(core, '_SITE_META', []), mock.patch.object(core, 'read_site_meta', lambda: marker):
            self.assertIs(core.site_meta(), marker)                    # the first read is core.read_site_meta()

    def test_archive_site_meta_is_core_read_site_meta(self):
        self.assertEqual(self.archive.site_meta(), self.meta)
        self.assertEqual(self.archive.site_meta(), core.read_site_meta())
        marker = {'maps': {}, 'regions': ['Synthetic Marker']}
        with mock.patch.object(core, 'read_site_meta', lambda: marker):
            self.assertIs(self.archive.site_meta(), marker)
        with mock.patch.object(core, '_SITE_META', [marker]):          # not core's cached copy
            self.assertEqual(self.archive.site_meta(), self.meta)
        changed = self.write_meta([PEAKS])
        self.assertEqual(self.archive.site_meta(), changed)            # read at each call
class NoStateLeftTests(unittest.TestCase):
    """What the fixture registers with core is gone when a test ends (helpers.keep_state), so no other module's tests
    meet a region page that is not theirs."""

    def test_a_fixture_test_leaves_core_as_it_found_it(self):
        before = {k: (v.copy() if hasattr(v, 'copy') else v) for k, v in vars(core).items()
                  if k.startswith('_') and not k.startswith('__') and isinstance(v, (list, dict))}
        root, rendered = core.ROOT, content.RENDERED

        class Probe(RegionFixture):
            seen = {}

            def runTest(self):
                Probe.seen = dict(core._REGION_PAGES)
                self.assertEqual(sorted(Probe.seen), sorted(PAGES))
                self.assertNotEqual(core.ROOT, root)

        result = unittest.TestResult()
        Probe().run(result)
        self.assertEqual((result.errors, result.failures, result.testsRun), ([], [], 1))
        self.assertEqual(sorted(Probe.seen), sorted(PAGES))
        after = {k: v for k, v in vars(core).items() if k in before}
        self.assertEqual(after, before)
        self.assertEqual((core.ROOT, content.RENDERED), (root, rendered))
        for name in PAGES:
            if name not in before['_REGION_PAGES']:
                self.assertIsNone(core.region_page_href('', name))

    def test_the_module_guard_reports_region_pages_that_were_left_and_clears_them(self):
        # helpers.no_region_pages_left is the tearDownModule of every test module that registers a site
        helpers.keep_state(self)
        core._REGION_PAGES.clear()
        self.assertIsNone(helpers.no_region_pages_left())                    # nothing registered: nothing to say
        core._REGION_PAGES.update({'Synthetic Left': 'synthetic-left', 'Synthetic Behind': 'synthetic-behind'})
        with self.assertRaises(AssertionError) as caught:
            helpers.no_region_pages_left()
        self.assertIn("['Synthetic Behind', 'Synthetic Left']", str(caught.exception))
        self.assertIn('keep_state', str(caught.exception))                   # the message says how to put it right
        self.assertEqual(core._REGION_PAGES, {})                             # cleared: the next module is not blamed for it
        self.assertIsNone(helpers.no_region_pages_left())
        self.assertIs(sys.modules[__name__].tearDownModule, helpers.no_region_pages_left)

    def test_every_test_module_that_registers_a_site_has_the_module_guard(self):
        # A module registers a site when it calls core.register_site, helpers.make_site (unless every call says
        # register=False) or a whole build (build.build). Its tearDownModule has to be, or has to call,
        # helpers.no_region_pages_left: then a run of the suite in any order of its modules fails in the module that
        # left a region page registered, and ends with none
        import ast
        folder = os.path.dirname(os.path.abspath(__file__))
        registering, missing = [], []
        for name in sorted(os.listdir(folder)):
            if not (name.startswith('test_') and name.endswith('.py')):
                continue
            with open(os.path.join(folder, name), encoding='utf-8') as fh:
                tree = ast.parse(fh.read())
            registers = False
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                called = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
                if called == 'register_site':
                    registers = True
                elif called == 'make_site' and not any(k.arg == 'register' and getattr(k.value, 'value', None) is False for k in node.keywords):
                    registers = True
                elif called == 'build' and isinstance(node.func, ast.Attribute) and any(k.arg == 'verbose' for k in node.keywords):
                    registers = True                                         # build.build(verbose=False, ...)
            if not registers:
                continue
            registering.append(name)
            guarded = False
            for node in tree.body:
                if isinstance(node, ast.Assign) and [getattr(t, 'id', None) for t in node.targets] == ['tearDownModule']:
                    guarded = isinstance(node.value, ast.Attribute) and node.value.attr == 'no_region_pages_left'
                elif isinstance(node, ast.FunctionDef) and node.name == 'tearDownModule':
                    guarded = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'no_region_pages_left'
                                  for n in ast.walk(node))
            if not guarded:
                missing.append(name)
        self.assertEqual(missing, [], 'add `tearDownModule = helpers.no_region_pages_left` to: %s' % ', '.join(missing))
        for name in ('test_curation.py', 'test_region_page.py', 'test_home.py', 'test_trips_page.py', 'test_report_page.py',
                     'test_archive_page.py', 'test_a11y_static.py', 'test_build_site.py', 'test_sitecheck.py', 'test_nav.py'):
            self.assertIn(name, registering)
        self.assertGreaterEqual(len(registering), 18)


# ---------------------------------------------------------------- section 3.1: the head

def stat_lines(p, classes=False):
    """(line 1, line 2) of p.reg-stats: the items before and after the break slot, as a reader sees them; line 2 is
    None when there is no break slot. classes=True: each item's class list instead of its text."""
    ml = p.elements()
    assert [n.classes for n in ml] == [['ml']], 'p.reg-stats holds one .ml line'
    lines = [[]]
    for node in ml[0].elements():
        if 'ml-br' in node.classes:
            lines.append([])
        else:
            assert node.classes in (['mi'], ['mi', 'mi-w']), node
            text = ''.join(c if isinstance(c, str) else ('' if 'sr' in c.classes else c.text(clean=False)) for c in node.children)
            lines[-1].append(node.classes if classes else helpers.plain_text(text))
    return (lines[0], lines[1] if len(lines) > 1 else None)


class HeadTests(RegionFixture):

    def head(self, name):
        return self.main(name).elements()[0]

    def stats(self, name):
        return self.head(name).find('p', cls='reg-stats')

    def test_the_head_is_the_first_section_and_the_h1_labels_it(self):
        for name in PAGES:
            with self.subTest(region=name):
                sec = self.head(name)
                self.assertEqual((sec.tag, sec.classes, sec['aria-labelledby']), ('section', ['reg-head', 'wrap'], 'reg-title'))
                self.assertEqual([(n.tag, n.classes) for n in sec.elements()],
                                 [('nav', ['crumbs', 't-mono-s']), ('h1', ['t-d1']), ('p', ['reg-stats'])])
                self.assertIs(self.one(name, 'reg-title'), sec.find('h1'))

    def test_it_is_region_head_of_the_published_reports_and_the_active_goals(self):
        head = need(self, self.region, 'head')
        for name in PAGES:
            with self.subTest(region=name):
                html_ = head(name, self.here(name), self.pub(name), self.planned(name))
                self.assertTrue(html_.startswith('<section class="reg-head wrap" aria-labelledby="reg-title">'))
                self.assertTrue(html_.endswith('</p></section>'))
                self.assertEqual(self.html(name).count(html_), 1)
                self.assertIn('<main id="main">' + html_, self.html(name))

    def test_the_breadcrumb_is_reports_map_and_the_region(self):
        for name in PAGES:
            with self.subTest(region=name):
                nav = self.head(name).find('nav')
                self.assertEqual(nav['aria-label'], 'Breadcrumb')
                self.assertEqual([(a.text(), a['href']) for a in nav.find_all('a')], [('Reports', '../../'), ('Map', '../../map/')])
                kids = nav.elements()
                self.assertEqual([n.tag for n in kids], ['a', 'span', 'a', 'span', 'span'])
                for sep in (kids[1], kids[3]):
                    self.assertEqual((sep['aria-hidden'], sep.text(), sep.classes), ('true', '/', []))
                self.assertEqual((kids[4]['aria-current'], kids[4].text()), ('page', name))
                self.assertEqual(kids[4].find_all('a'), [])                       # the page's own name is not a link
                self.assertEqual([n for n in nav.walk() if n['aria-current']], [kids[4]])
        # the markup of the section pages' crumbs, to the byte
        self.assertIn('<nav class="crumbs t-mono-s" aria-label="Breadcrumb"><a href="../../">Reports</a><span aria-hidden="true">/</span>'
                      '<a href="../../map/">Map</a><span aria-hidden="true">/</span><span aria-current="page">Synthetic Range</span></nav>',
                      self.html(RANGE))

    def test_the_breadcrumb_links_are_relative_to_the_page(self):
        head = need(self, self.region, 'head')
        for here, home, map_ in (('regions/synthetic-range/', '../../', '../../map/'), ('a/', '../', '../map/'), ('', './', 'map/'),
                                 ('a/b/c/', '../../../', '../../../map/')):
            nav = Doc(head(RANGE, here, self.pub(RANGE), self.planned(RANGE))).find('nav')
            self.assertEqual([a['href'] for a in nav.find_all('a')], [home, map_])

    def test_the_h1_is_the_region_name_and_nothing_else(self):
        for name in PAGES:
            with self.subTest(region=name):
                h1 = self.one(name, 'reg-title')
                self.assertEqual(h1.children, [name])                             # one text node: no tag, no count, no link
                self.assertEqual(h1.text(clean=False), name)
        self.assertIn('<h1 id="reg-title" class="t-d1">Synthetic Range</h1>', self.html(RANGE))

    def test_a_region_name_is_escaped_wherever_the_head_writes_it(self):
        html_ = need(self, self.region, 'head')(PEAKS, self.here(PEAKS), self.pub(PEAKS), self.planned(PEAKS))
        escaped = 'Synthetic O&#x27;Brien &amp; &lt;Peaks&gt;'
        self.assertEqual(escaped, esc(PEAKS))
        self.assertIn('<span aria-current="page">%s</span>' % escaped, html_)
        self.assertIn('<h1 id="reg-title" class="t-d1">%s</h1>' % escaped, html_)
        self.assertEqual(html_.count(escaped), 2)
        for raw in ('<Peaks>', '<PEAKS>', "O'Brien", '& <', '&amp;amp;', '&amp;lt;', '&amp;#x27;'):
            self.assertNotIn(raw, html_)
        self.assertEqual(self.doc(PEAKS).find_all('peaks'), [])
        self.assertEqual(self.doc(PEAKS).find_all('wall'), [])

    # ------------------------------------------------------------ the stats line

    def test_the_stats_are_one_meta_line_in_two_lines(self):
        want = {RANGE: (['11 REPORTS', 'INCL. 1 MULTI-DAY', '+ 1 PLANNED ROUTE', '2022–2026'],
                        ['SYNTHETIC BASIN', 'SYNTHETIC BOWL', 'SYNTHETIC CRAG', '4 MORE']),
                COAST: (['3 REPORTS', '2026'], ['SYNTHETIC COVE']),
                PEAKS: (['2 REPORTS', '2024–2025'], ["SYNTHETIC O'NEIL & <WALL>"])}
        for name in PAGES:
            with self.subTest(region=name):
                p = self.stats(name)
                self.assertEqual(stat_lines(p), want[name])
                # one break slot, between the two lines: hidden from readers, shown by region.css
                slots = p.find_all('span', cls='ml-br')
                self.assertEqual([(s['aria-hidden'], s.children) for s in slots], [('true', [])])
                self.assertEqual(p.text(), ', '.join(want[name][0] + want[name][1]))      # what a screen reader hears

    def test_the_stats_line_is_core_meta_items_with_the_break_after_line_one(self):
        years_item, place_items = need(self, self.region, 'years_item'), need(self, self.region, 'place_items')
        for name in PAGES:
            with self.subTest(region=name):
                pub, planned = self.pub(name), self.planned(name)
                first = core.count_items(pub, planned) + [years_item(pub)]
                want = '<p class="reg-stats">%s</p>' % core.meta_items(first + place_items(pub), br_after=len(first) - 1)
                self.assertEqual(self.html(name).count(want), 1)
                self.assertIn('<span class="ml">', want)
                # the break slot stands between the year and the first place, which carries the class of a place
                self.assertRegex(want, r'20\d\d</span><span class="ml-br" aria-hidden="true"></span><span class="mi mi-w"><span class="sr">, </span>SYNTHETIC')
                self.assertEqual(place_items(pub)[0][1], 'mi-w')

    def test_the_counts_are_core_count_items(self):
        # '1 REPORT'; a multi-day trip is one report and is named; planned routes are added, never counted
        self.goal('syn-r-cove-goal', title='Synthetic Cove Goal', region=COAST)
        self.goal('syn-r-cove-goal-2', title='Synthetic Cove Goal Two', region=COAST)
        self.use(mapped=[RANGE, COAST], only=['syn-r-tour', 'syn-r-cove-a', 'syn-r-cove-b', 'syn-r-cove-goal', 'syn-r-cove-goal-2'])
        self.assertEqual(stat_lines(self.stats(COAST)), (['2 REPORTS', '+ 2 PLANNED ROUTES', '2026'], ['SYNTHETIC COVE']))
        self.assertEqual(stat_lines(self.stats(RANGE)), (['1 REPORT', 'INCL. 1 MULTI-DAY', '2025'], ['SYNTHETIC HUT']))

    def test_years_item(self):
        years_item = need(self, self.region, 'years_item')
        self.assertEqual(years_item(self.pub(RANGE)), '2022–2026')                       # an en dash, not a hyphen
        self.assertNotIn('-', years_item(self.pub(RANGE)))
        self.assertEqual(years_item(self.pub(COAST)), '2026')                                # one year, once
        self.assertEqual(years_item(self.trips('syn-r-lap')), '2023')
        self.assertEqual(years_item(self.trips('syn-r-lap', 'syn-r-raft')), '2023')
        self.assertEqual(years_item(self.trips('syn-r-old', 'syn-r-lap')), '2022–2023')  # whatever the order of the list
        self.assertEqual(years_item(self.trips('syn-r-lap', 'syn-r-old')), '2022–2023')
        self.assertEqual(years_item(self.trips('syn-r-story', 'syn-r-words', 'syn-r-old')), '2022–2026')   # the span, not the years
        # an undated report has no year: it is skipped among dated ones, and alone it gives no item
        self.assertEqual(years_item(self.trips('syn-r-undated', 'syn-r-lap')), '2023')
        self.assertEqual(years_item(self.trips('syn-r-undated')), '')
        self.assertEqual(years_item([]), '')

    def test_years_item_counts_the_year_a_trip_ended_in(self):
        years_item = need(self, self.region, 'years_item')
        self.mk('syn-r-nye', title='Synthetic New Year Tour', activity='ski', kind='multi-day', date='2019-12-30', end_date='2020-01-02',
                region=RANGE, days=[{'title': 'Synthetic Day One', 'date': '2019-12-30'}, {'title': 'Synthetic Day Two', 'date': '2020-01-02'}])
        self.use()
        nye = self.by['syn-r-nye']
        self.assertEqual((nye['date'].year, nye['end_date'].year), (2019, 2020))
        self.assertEqual(years_item([nye]), '2019–2020')
        self.assertEqual(years_item([self.by['syn-r-lap'], nye]), '2019–2023')
        self.assertEqual(stat_lines(self.stats(RANGE))[0][-1], '2019–2026')

    def test_no_year_and_no_second_line_when_nothing_is_dated_or_placed(self):
        self.use(mapped=[RANGE], only=['syn-r-undated'])
        self.assertEqual(stat_lines(self.stats(RANGE)), (['1 REPORT'], None))
        self.assertIn('<p class="reg-stats"><span class="ml"><span class="mi">1\xa0REPORT</span></span></p>', self.html(RANGE))
        self.assertNotIn('ml-br', inner(self.html(RANGE), '<p class="reg-stats">', '</p>'))

    def test_no_second_line_when_no_report_names_a_place(self):
        self.use(mapped=[COAST], only=['syn-r-cove-c'])
        self.assertIsNone(self.by['syn-r-cove-c']['place'])
        self.assertEqual(stat_lines(self.stats(COAST)), (['1 REPORT', '2026'], None))
        self.assertEqual(self.stats(COAST).find_all('span', cls='ml-br'), [])
        self.assertEqual(need(self, self.region, 'place_items')(self.pub(COAST)), [])
        # ... and a year, when there is no place, is the last item of the only line
        self.assertTrue(inner(self.html(COAST), '<p class="reg-stats">', '</p>').endswith('2026</span></span>'))

    # ------------------------------------------------------------ the places (REVISED in round 2)

    def placed(self, *places):
        """One report per name in `places` (None: a report that names no place): copies of a fixture report."""
        return [dict(self.by['syn-r-lap'], slug='syn-r-placed-%d' % i, place=p) for i, p in enumerate(places)]

    def test_place_items_are_the_places_most_reports_first_then_a_to_z_in_capitals(self):
        place_items = need(self, self.region, 'place_items')
        self.assertEqual(self.region.MAX_PLACES, 3)
        # one place per report here: A to Z. An item is (the place, 'mi-w'): the class that lets it wrap at its spaces
        four = self.trips('syn-r-paddle', 'syn-r-tour', 'syn-r-words', 'syn-r-lap')
        self.assertEqual(place_items(four), [('SYNTHETIC BOWL', 'mi-w'), ('SYNTHETIC CRAG', 'mi-w'), ('SYNTHETIC HUT', 'mi-w'),
                                             ('SYNTHETIC LAKE', 'mi-w')])
        # the place with more reports comes first, whatever its name and wherever its reports are in the list
        self.assertEqual(place_items(self.trips('syn-r-lap', 'syn-r-raft', 'syn-r-raft', 'syn-r-words')),
                         [('SYNTHETIC RIVER', 'mi-w'), ('SYNTHETIC BOWL', 'mi-w'), ('SYNTHETIC CRAG', 'mi-w')])
        self.assertEqual(place_items(self.trips('syn-r-story', 'syn-r-flag')), [('SYNTHETIC BASIN', 'mi-w')])     # a place is named once
        # a report without a place adds nothing
        self.assertEqual(place_items(self.trips('syn-r-short', 'syn-r-undated', 'syn-r-lap')), [('SYNTHETIC BOWL', 'mi-w')])
        self.assertEqual(place_items(self.trips('syn-r-short', 'syn-r-undated')), [])
        self.assertEqual(place_items(self.placed(None, '', '   ')), [])
        self.assertEqual(place_items([]), [])

    def test_place_names_are_the_upper_case_forms_in_that_order(self):
        place_names = need(self, self.region, 'place_names')
        self.assertEqual(place_names(self.pub(RANGE)), ['SYNTHETIC BASIN', 'SYNTHETIC BOWL', 'SYNTHETIC CRAG', 'SYNTHETIC HUT', 'SYNTHETIC LAKE',
                                                        'SYNTHETIC RIDGE', 'SYNTHETIC RIVER'])
        self.assertEqual(place_names(self.pub(PEAKS)), ["SYNTHETIC O'NEIL & <WALL>"])              # the name itself: nothing is escaped yet
        self.assertEqual(place_names(self.pub(COAST)), ['SYNTHETIC COVE'])
        self.assertEqual(place_names(self.placed(None, '')), [])
        self.assertEqual(place_names([]), [])
        # place_items is those names, escaped, each with its class, cut at MAX_PLACES
        for pub in (self.pub(COAST), self.pub(PEAKS), self.trips('syn-r-paddle', 'syn-r-tour', 'syn-r-words', 'syn-r-lap')):
            self.assertEqual(self.region.place_items(pub), [(esc(x), 'mi-w') for x in place_names(pub)])

    def test_two_spellings_that_read_the_same_in_upper_case_are_one_place(self):
        place_items, place_names = need(self, self.region, 'place_items'), need(self, self.region, 'place_names')
        # the head shows upper case, so 'Synthetic Basin' and 'SYNTHETIC BASIN' would be the same words twice: they are
        # one item, and their reports are counted together
        pub = self.placed('Synthetic Crag', 'Synthetic Basin', 'Synthetic Crag', 'SYNTHETIC BASIN', 'synthetic basin')
        self.assertEqual(place_names(pub), ['SYNTHETIC BASIN', 'SYNTHETIC CRAG'])                  # 3 reports, then 2
        self.assertEqual(place_items(pub), [('SYNTHETIC BASIN', 'mi-w'), ('SYNTHETIC CRAG', 'mi-w')])
        # counted apart, the Crag (two reports) would lead and the Basin would be named three times
        self.assertEqual(place_names(self.placed('Synthetic Crag', 'Synthetic Crag', 'Synthetic Basin')), ['SYNTHETIC CRAG', 'SYNTHETIC BASIN'])
        # spaces around a name are not part of it
        self.assertEqual(place_names(self.placed(' Synthetic Basin', 'Synthetic Basin  ', 'Synthetic Crag')), ['SYNTHETIC BASIN', 'SYNTHETIC CRAG'])
        # one spelling with one report each: still one place, and it ties with the others from A to Z
        self.assertEqual(place_names(self.placed('Synthetic Dome', 'synthetic arch', 'Synthetic Arch', 'Synthetic Dome')),
                         ['SYNTHETIC ARCH', 'SYNTHETIC DOME'])

    def test_ties_are_a_to_z_on_the_upper_case_form(self):
        place_names = need(self, self.region, 'place_names')
        # a lower-case particle sorts as the capitals the head shows: 'DE ANZA' before 'DOME' (as written, 'de Anza'
        # would come after every capital), and a name in small letters is in its place among the others
        self.assertEqual(place_names(self.placed('Synthetic Dome', 'Synthetic de Anza', 'synthetic cirque', 'Synthetic Butte')),
                         ['SYNTHETIC BUTTE', 'SYNTHETIC CIRQUE', 'SYNTHETIC DE ANZA', 'SYNTHETIC DOME'])
        self.assertEqual(sorted(['Synthetic Dome', 'Synthetic de Anza', 'synthetic cirque', 'Synthetic Butte']),
                         ['Synthetic Butte', 'Synthetic Dome', 'Synthetic de Anza', 'synthetic cirque'])      # the order of the names as written
        # whatever the order of the reports
        self.assertEqual(place_names(self.placed('Synthetic de Anza', 'Synthetic Butte', 'Synthetic Dome', 'synthetic cirque')),
                         ['SYNTHETIC BUTTE', 'SYNTHETIC CIRQUE', 'SYNTHETIC DE ANZA', 'SYNTHETIC DOME'])
        # the count comes first: A to Z only among places with as many reports
        self.assertEqual(place_names(self.placed('Synthetic Dome', 'Synthetic de Anza', 'Synthetic Dome', 'Synthetic Butte', 'synthetic zawn',
                                                 'Synthetic Zawn')),
                         ['SYNTHETIC DOME', 'SYNTHETIC ZAWN', 'SYNTHETIC BUTTE', 'SYNTHETIC DE ANZA'])

    def test_at_most_four_places_are_named_and_beyond_that_three_and_a_count(self):
        place_items = need(self, self.region, 'place_items')
        nb = core.nb
        one_each = self.trips('syn-r-words', 'syn-r-tour', 'syn-r-paddle', 'syn-r-raft', 'syn-r-lap', 'syn-r-old')   # six places
        names4 = [('SYNTHETIC BOWL', 'mi-w'), ('SYNTHETIC CRAG', 'mi-w'), ('SYNTHETIC HUT', 'mi-w'), ('SYNTHETIC LAKE', 'mi-w')]
        self.assertEqual(place_items(self.trips('syn-r-words', 'syn-r-tour', 'syn-r-paddle', 'syn-r-lap')), names4)   # MAX_PLACES + 1: all
        five = place_items(self.trips('syn-r-words', 'syn-r-tour', 'syn-r-paddle', 'syn-r-lap', 'syn-r-old'))
        self.assertEqual(five, names4[:3] + [nb('2 MORE')])                                     # never '1 MORE'
        self.assertEqual(place_items(one_each), names4[:3] + [nb('3 MORE')])
        self.assertEqual(place_items(self.pub(RANGE)), [('SYNTHETIC BASIN', 'mi-w'), ('SYNTHETIC BOWL', 'mi-w'), ('SYNTHETIC CRAG', 'mi-w'),
                                                        nb('4 MORE')])
        # the count is one item that never breaks, without the place class: a plain string with a no-break space
        self.assertEqual(five[-1], '2\xa0MORE')
        # the constant is the rule: with MAX_PLACES = 1, two places are both named and three are one and '2 MORE'
        with mock.patch.object(self.region, 'MAX_PLACES', 1):
            self.assertEqual(place_items(self.trips('syn-r-words', 'syn-r-lap')), names4[:2])
            self.assertEqual(place_items(self.trips('syn-r-words', 'syn-r-lap', 'syn-r-tour')), [names4[0], nb('2 MORE')])
        with mock.patch.object(self.region, 'MAX_PLACES', 5):
            self.assertEqual(len(place_items(one_each)), 6)                                     # six places: MAX_PLACES + 1
            self.assertEqual(place_items(self.pub(RANGE))[4:], [('SYNTHETIC LAKE', 'mi-w'), nb('2 MORE')])   # seven: five and a count

    def test_the_cut_counts_places_after_two_spellings_became_one(self):
        place_items = need(self, self.region, 'place_items')
        # five spellings, four places: all four are named (counted as written they would be three and '2 MORE')
        pub = self.placed('Synthetic Arch', 'Synthetic Butte', 'Synthetic Cirque', 'Synthetic Dome', 'SYNTHETIC DOME')
        self.assertEqual(place_items(pub), [('SYNTHETIC DOME', 'mi-w'), ('SYNTHETIC ARCH', 'mi-w'), ('SYNTHETIC BUTTE', 'mi-w'),
                                            ('SYNTHETIC CIRQUE', 'mi-w')])
        # seven spellings, five places: three and '2 MORE', and the two that are left out are the last from A to Z
        pub = self.placed('Synthetic Arch', 'synthetic arch', 'Synthetic Butte', 'Synthetic Cirque', 'Synthetic Dome', 'SYNTHETIC DOME',
                          'Synthetic Edge')
        self.assertEqual(place_items(pub), [('SYNTHETIC ARCH', 'mi-w'), ('SYNTHETIC DOME', 'mi-w'), ('SYNTHETIC BUTTE', 'mi-w'),
                                            core.nb('2 MORE')])

    def test_a_place_may_wrap_at_its_spaces_and_nowhere_carries_a_no_break_space(self):
        place_items = need(self, self.region, 'place_items')
        long_ = 'Synthetic Long Named Valley Of The Far North Fork'
        items = place_items(self.placed(long_, 'Synthetic Crag'))
        self.assertEqual(items, [('SYNTHETIC CRAG', 'mi-w'), (long_.upper(), 'mi-w')])
        for html_, cls in items:
            self.assertEqual(cls, 'mi-w')
            self.assertNotIn('\xa0', html_)                              # core.nb is not applied: every space is one a line may break at
            self.assertNotIn('&nbsp;', html_)
            self.assertIn(' ', html_)
        self.assertEqual(items[1][0].count(' '), 8)
        # in the head that is <span class="mi mi-w">: base.css lets an item of that class wrap (.ml > .mi-w)
        html_ = need(self, self.region, 'head')(RANGE, self.here(RANGE), self.placed(long_), [])
        self.assertIn('<span class="mi mi-w"><span class="sr">, </span>%s</span>' % long_.upper(), html_)
        for name in PAGES:
            first, second = stat_lines(self.stats(name), classes=True)
            self.assertEqual(first, [['mi']] * len(first))               # counts and years: one line each, as before
            places = [c for c in second if c == ['mi', 'mi-w']]
            self.assertEqual(second, places + [['mi']] * (len(second) - len(places)))      # the places, then the count that follows them
            self.assertEqual(len(places), min(len(self.region.place_names(self.pub(name))), 3))
        self.assertEqual(stat_lines(self.stats(RANGE), classes=True)[1], [['mi', 'mi-w']] * 3 + [['mi']])
        # the only no-break spaces of the stats line are in the counts and in 'N MORE'
        line = inner(self.html(RANGE), '<p class="reg-stats">', '</p>')
        self.assertEqual(re.findall(r'[^<>]*\xa0[^<>]*', line), ['11\xa0REPORTS', 'INCL.\xa01\xa0MULTI-DAY', '+\xa01\xa0PLANNED\xa0ROUTE', '4\xa0MORE'])

    def test_a_place_name_is_escaped_after_it_is_put_in_upper_case(self):
        place_items = need(self, self.region, 'place_items')
        items = place_items(self.pub(PEAKS))
        # 'SYNTHETIC O&#x27;NEIL &amp; &lt;WALL&gt;': the references are the ones html.escape writes, in their own case
        self.assertEqual(items, [(esc(WALL.upper()), 'mi-w')])
        self.assertEqual(items, [('SYNTHETIC O&#x27;NEIL &amp; &lt;WALL&gt;', 'mi-w')])
        self.assertEqual(Doc('<p>%s</p>' % items[0][0]).text(), "SYNTHETIC O'NEIL & <WALL>")
        for raw in ('<WALL>', '<Wall>', "O'NEIL", '& ', '&AMP;', '&LT;', '&GT;', '&#X27;'):
            self.assertNotIn(raw, items[0][0])
        self.assertEqual(place_items(self.placed('Synthetic Fish & Chips')), [('SYNTHETIC FISH &amp; CHIPS', 'mi-w')])
        self.assertEqual(place_items(self.placed('Synthetic "Quoted" Tarn')), [('SYNTHETIC &quot;QUOTED&quot; TARN', 'mi-w')])
        # in a list that is cut as well: the three places named before 'N MORE'
        pub = self.placed('Synthetic A & B', 'Synthetic A & B', "Synthetic C's", 'Synthetic <D>', 'Synthetic E', 'Synthetic F')
        self.assertEqual(place_items(pub), [('SYNTHETIC A &amp; B', 'mi-w'), ('SYNTHETIC &lt;D&gt;', 'mi-w'), ('SYNTHETIC C&#x27;S', 'mi-w'),
                                            core.nb('2 MORE')])
        # on the page: read back as the name, and no reference in capitals anywhere in the head
        self.assertEqual(stat_lines(self.stats(PEAKS))[1], ["SYNTHETIC O'NEIL & <WALL>"])
        head = self.html(PEAKS)[self.html(PEAKS).index('<section class="reg-head'):self.html(PEAKS).index('</section>')]
        self.assertIn('<span class="mi mi-w"><span class="sr">, </span>SYNTHETIC O&#x27;NEIL &amp; &lt;WALL&gt;</span>', head)
        self.assertEqual(re.findall(r'&[A-Z#][A-Z0-9]*;', head), [])
        self.assertEqual(self.doc(PEAKS).find_all('wall'), [])
# ---------------------------------------------------------------- section 3.2: the map

MAPCOL, SIDE, INREG = '<div class="arc-mapcol">', '<div class="arc-side">', '<div class="arc-inreg">'


class PanelTests(RegionFixture):

    def section(self, name):
        return self.main(name).elements()[1]

    def panel(self, name):
        return self.one(name, 'map')

    def panel_html(self, name, first=True, page=True, here=None):
        here = self.here(name) if here is None else here
        return self.archive.region_panel(name, SLUG[name], self.group(name), here, self.meta, first, page=page)

    def test_the_map_section_follows_the_head(self):
        for name in PAGES:
            with self.subTest(region=name):
                sec = self.section(name)
                self.assertEqual((sec.tag, sec.classes, sec['aria-labelledby']), ('section', ['arc-map', 'reg-map', 'wrap'], 'reg-map-h'))
                h2, panel = sec.elements()                                   # the heading and the panel: no tab row
                self.assertEqual((h2.tag, h2.classes, h2['id'], h2.text()), ('h2', ['sr'], 'reg-map-h', 'Map'))
                self.assertEqual((panel.tag, panel.classes, panel['id']), ('div', ['arc-panel'], 'map'))
                self.assertEqual(self.doc(name).find_all(attrs={'role': 'tablist'}), [])
                self.assertEqual(self.doc(name).find_all(attrs={'role': 'tab'}), [])

    def test_it_is_the_map_pages_panel_built_in_page_mode(self):
        for name in PAGES:
            with self.subTest(region=name):
                want = ('<section class="arc-map reg-map wrap" aria-labelledby="reg-map-h"><h2 class="sr" id="reg-map-h">Map</h2>%s</section>'
                        % self.panel_html(name))
                self.assertEqual(self.html(name).count(want), 1)

    def test_the_wrapper_is_map_and_the_region_anchor_stays_on_the_map_page(self):
        for name in PAGES:
            with self.subTest(region=name):
                html_ = self.html(name)
                self.assertTrue(self.panel_html(name).startswith('<div class="arc-panel" id="map"><div class="arc-grid">'))
                self.assertEqual(html_.count('id="map"'), 1)
                ids = [n['id'] for n in self.doc(name).root.walk() if n['id']]
                self.assertEqual([i for i in ids if i.startswith(('region-', 'arc-ph-', 'arc-tab-'))], [])
                self.assertNotIn('id="region-', html_)

    def test_there_is_no_heading_with_the_region_name_in_the_panel(self):
        for name in PAGES:
            with self.subTest(region=name):
                panel = self.panel(name)
                self.assertEqual(panel.find_all(cls='arc-panel-h'), [])
                self.assertEqual([h.text() for h in panel.find_all('h3')], ['In this region'])       # the list's heading, not the region's
                self.assertEqual(panel.find_all('h4'), [])
                self.assertNotIn(name, [h.text() for h in self.doc(name).find_all('h2') + self.doc(name).find_all('h3')])
                self.assertEqual([el.tag for el in panel.elements()], ['div'])           # the grid alone: the h1 names the region
                self.assertEqual(panel.elements()[0].classes, ['arc-grid'])

    def test_the_map_block_is_the_regions_site_render_marked_eager(self):
        for name in PAGES:
            with self.subTest(region=name):
                slug = SLUG[name]
                block = self.one(name, 'arc-map-' + slug)
                self.assertEqual((block.tag, block.classes), ('div', ['map', 'arc-mapv']))
                self.assertIn(self.panel(name), ancestors(block))
                self.assertEqual([v.classes for v in block.elements()], [['mv', 'mv--desktop'], ['mv', 'mv--phone']])
                imgs = block.find_all('img')
                self.assertEqual([i['src'] for i in imgs], ['../../assets/maps/region-%s-%s' % (slug, f) for f in
                                                           ('desktop.webp', 'desktop.base.svg', 'phone.webp', 'phone.base.svg')])
                self.assertEqual([i['fetchpriority'] for i in imgs], ['high'] * 4)        # the first-screen map, as map/'s first panel
                self.assertEqual([i['alt'] for i in imgs], [''] * 4)
                self.assertEqual(len(block.find_all('svg')), 2)                          # both fragments were found in the temp dir
                self.assertNotIn('<!-- missing', self.html(name))

    def test_the_map_caption_and_legend_are_those_of_the_map_page(self):
        archive_page = self.archive.build(self.site)[0].html
        for name in PAGES:
            with self.subTest(region=name):
                mine, theirs = self.panel_html(name), self.panel_html(name, page=False)
                # the map column (map and caption) and the legend, to the byte, for the same page address
                self.assertEqual(inner(mine, MAPCOL, INREG), inner(theirs, MAPCOL, INREG))
                self.assertIn('<div class="arc-cap">', inner(mine, MAPCOL, SIDE))
                self.assertIn('<div class="arc-legend">', inner(mine, SIDE, INREG))
                cap = self.panel(name).find('div', cls='arc-cap')
                self.assertEqual(ml_items(cap)[:3], ['Pins mark each start and link to the report', 'Full tracks, not trimmed', 'North up'])
        # ... and on the Map page itself, one folder up, the first panel's column is the same column
        mine = inner(self.panel_html(RANGE), MAPCOL, INREG)
        start = archive_page.index('<div class="arc-panel" id="region-synthetic-range">')
        self.assertEqual(inner(archive_page[start:], MAPCOL, INREG), mine.replace('../../', '../'))
        legend = self.panel(RANGE).find('div', cls='arc-legend')
        self.assertEqual([li.text() for li in legend.find_all('li')],
                         ['Backcountry Ski', 'Climbing', 'Hiking', 'Mountain Biking', 'Other', 'Planned route'])

    # ------------------------------------------------------------ the side list (REVISED in round 2: the Map page's list)

    def rows(self, name):
        return self.one(name, 'arc-rows-' + SLUG[name]).elements()

    def test_the_list_is_headed_in_this_region_by_an_h3_with_the_count_line_beside_it(self):
        want = {RANGE: ['11 REPORTS', 'INCL. 1 MULTI-DAY', '+ 1 PLANNED ROUTE'], COAST: ['3 REPORTS'], PEAKS: ['2 REPORTS']}
        for name in PAGES:
            with self.subTest(region=name):
                slug = SLUG[name]
                box = self.panel(name).find('div', cls='arc-inreg')
                head = box.elements()[0]
                self.assertEqual(head.classes, ['arc-inreg-h'])
                h3, count = head.elements()                                  # the heading and the count line, as on the Map page
                # an h3, since the panel has no heading of its own between it and the section's h2
                self.assertEqual((h3.tag, h3.classes, h3['id'], h3.children), ('h3', ['t-label'], 'arc-in-' + slug, ['In this region']))
                self.assertEqual((count.tag, count.classes), ('span', ['t-mono-s']))
                self.assertEqual(ml_items(count), want[name])
                self.assertEqual(box.elements()[1].tag, 'ol')
                self.assertIn('<div class="arc-inreg"><div class="arc-inreg-h"><h3 class="t-label" id="arc-in-%s">In this region</h3>'
                              '<span class="t-mono-s">%s</span></div><ol ' % (slug, self.archive.count_line(self.group(name), 'ml--end')),
                              self.html(name))
                self.assertNotIn('Latest', self.html(name))                  # the first round's heading
        self.assertIn('<span class="ml ml--end">', self.archive.count_line(self.group(RANGE), 'ml--end'))

    def test_the_rows_keep_the_list_the_map_highlights_from(self):
        for name in PAGES:
            with self.subTest(region=name):
                slug = SLUG[name]
                ol = self.one(name, 'arc-rows-' + slug)
                self.assertEqual((ol.tag, ol.classes), ('ol', ['arc-rows']))
                self.assertEqual(ol['aria-labelledby'], 'arc-in-' + slug)           # the h3 alone: there is no panel heading
                self.assertEqual(self.one(name, ol['aria-labelledby']).text(), 'In this region')
                self.assertEqual(self.one(name, ol['aria-labelledby']).tag, 'h3')
                # hovering a row highlights its pin, and a pin or a cluster marker finds its row: the list names its map
                self.assertEqual(ol['data-map-target'], 'arc-map-' + slug)
                self.assertIn('map', self.one(name, ol['data-map-target']).classes)
                self.assertEqual(sorted(ol.attrs), ['aria-labelledby', 'class', 'data-map-target', 'id'])
                self.assertEqual(len(self.doc(name).find_all(attrs={'data-map-target': 'arc-map-' + slug})), 1)

    def test_the_rows_are_every_trip_of_the_region_as_region_rows(self):
        self.assertEqual(self.archive.SHOW, 8)
        for name, want in ((RANGE, RANGE_PUB + ['syn-r-goal']), (COAST, COAST_PUB), (PEAKS, PEAKS_PUB)):
            with self.subTest(region=name):
                ts = self.group(name)
                rows = self.rows(name)
                self.assertEqual([(li.tag, li['data-key']) for li in rows], [('li', s) for s in want])       # every trip, in the page's order
                self.assertEqual([li.find('a')['href'] for li in rows], ['../../trips/%s/' % s for s in want])
                hidden = len(ts) > 9
                rows_html = ''.join(self.archive.region_row(t, self.here(name), i >= 8 and hidden) for i, t in enumerate(ts))
                self.assertEqual(inner(self.panel_html(name), 'data-map-target="arc-map-%s">' % SLUG[name], '</ol>'), rows_html)
                self.assertEqual(self.html(name).count('<ol class="arc-rows" id="arc-rows-%s" aria-labelledby="arc-in-%s" data-map-target="arc-map-%s">%s</ol>'
                                                       % (SLUG[name], SLUG[name], SLUG[name], rows_html)), 1)
        # the table under the map lists the same trips: nothing is in one list and not in the other
        for name in PAGES:
            table = [a['data-key'] for a in self.one(name, 'all-reports').find_all('a', cls='rtab-r')]
            self.assertEqual([li['data-key'] for li in self.rows(name)], table)

    def test_the_active_goals_are_the_last_rows(self):
        # as on the Map page: a planned route is a row (its line is on the map), after the reports
        self.goal('syn-r-cove-goal', title='Synthetic Cove Goal', region=COAST)
        self.use()
        self.assertEqual(helpers.slugs(self.group(COAST)), COAST_PUB + ['syn-r-cove-goal'])
        for name, want in ((RANGE, RANGE_PUB + ['syn-r-goal']), (COAST, COAST_PUB + ['syn-r-cove-goal'])):
            rows = self.rows(name)
            self.assertEqual([li['data-key'] for li in rows], want)
            self.assertEqual([self.by[li['data-key']]['kind'] == 'planned' for li in rows], [False] * (len(want) - 1) + [True])
            self.assertEqual(rows[-1].find('a')['href'], '../../trips/%s/' % want[-1])
        # the archived goal of the Range is no row, and no row of another region is here
        self.assertNotIn('syn-r-shelved', self.html(RANGE))
        self.assertIn('Planned route', self.panel(COAST).find('div', cls='arc-legend').text())
        # the count line beside the heading counts it apart, and 'Show all' would count the reports only
        self.assertEqual(ml_items(self.panel(COAST).find('div', cls='arc-inreg-h')), ['3 REPORTS', '+ 1 PLANNED ROUTE'])

    def test_above_show_plus_one_trips_the_rest_is_hidden_behind_show_all(self):
        # the Range has twelve trips: the ninth on are marked arc-more, and one hidden button opens them. archive.js
        # collapses the list and shows the button; without JavaScript every row is simply there
        self.assertEqual(len(self.group(RANGE)), 12)
        rows = self.rows(RANGE)
        self.assertEqual([li.classes for li in rows], [['arc-row']] * 8 + [['arc-row', 'arc-more']] * 4)
        self.assertEqual([li['data-key'] for li in rows if 'arc-more' in li.classes], ['syn-r-lap', 'syn-r-old', 'syn-r-undated', 'syn-r-goal'])
        box = self.panel(RANGE).find('div', cls='arc-inreg')
        self.assertEqual([(n.tag, n.classes) for n in box.elements()],
                         [('div', ['arc-inreg-h']), ('ol', ['arc-rows']), ('button', ['alink', 'arc-all-btn'])])
        button = box.find('button')
        self.assertEqual((button['type'], button['aria-expanded'], button['aria-controls'], 'hidden' in button, button.text()),
                         ('button', 'false', 'arc-rows-synthetic-range', True, 'Show all 11'))
        self.assertIs(self.one(RANGE, button['aria-controls']), box.find('ol'))
        self.assertEqual(sorted(button.attrs), ['aria-controls', 'aria-expanded', 'class', 'hidden', 'type'])
        # the label is the button's first node (archive.js swaps it for 'Show fewer'), the chevron follows it
        self.assertEqual((button.children[0], [n.tag for n in button.elements()]), ('Show all 11', ['svg']))
        # a hidden row holds a link: the first of them takes the focus when the list opens
        self.assertTrue(all(li.find('a') is not None for li in rows if 'arc-more' in li.classes))
        # N is the published reports (the goal is the twelfth trip and is not counted), as the Map page's tab says it
        self.assertEqual((len(self.group(RANGE)), len(self.pub(RANGE))), (12, 11))
        want = ('<button type="button" class="alink arc-all-btn" aria-expanded="false" aria-controls="arc-rows-synthetic-range" hidden>'
                'Show all 11%s</button>' % icon('chevron-down', 16))
        self.assertEqual(self.html(RANGE).count(want), 1)
        self.assertIn('</li></ol>' + want + PANEL_TAIL + '</section>', self.html(RANGE))       # the last thing of the list's box
        self.assertEqual(len(self.doc(RANGE).find_all('button', cls='arc-all-btn')), 1)
        self.assertNotIn('arc-collapsed', self.html(RANGE))                                   # the script's class: never written

    def test_up_to_show_plus_one_trips_there_is_no_button_and_no_hidden_row(self):
        for name in (COAST, PEAKS):
            self.assertNotIn('arc-all-btn', self.html(name))
            self.assertNotIn('arc-more', self.html(name))
            self.assertNotIn('Show all', self.html(name))
            box = self.panel(name).find('div', cls='arc-inreg')
            self.assertEqual([n.tag for n in box.elements()], ['div', 'ol'])
            self.assertTrue(self.panel_html(name).endswith('</li></ol>' + PANEL_TAIL))
        # exactly SHOW + 1 trips (eight reports and a goal): one more row is shown rather than a button for one row
        self.use(mapped=[RANGE], only=RANGE_PUB[:8] + ['syn-r-goal'])
        self.assertEqual((len(self.group(RANGE)), len(self.pub(RANGE))), (9, 8))
        self.assertEqual([li.classes for li in self.rows(RANGE)], [['arc-row']] * 9)
        self.assertEqual(self.panel(RANGE).find_all('button'), [])
        # one more trip: eight rows shown, two behind the button, which counts the nine reports
        self.use(mapped=[RANGE], only=RANGE_PUB[:9] + ['syn-r-goal'])
        self.assertEqual([li.classes for li in self.rows(RANGE)], [['arc-row']] * 8 + [['arc-row', 'arc-more']] * 2)
        self.assertEqual([b.text() for b in self.panel(RANGE).find_all('button', cls='arc-all-btn')], ['Show all 9'])

    def test_show_is_where_the_hidden_rows_begin(self):
        with mock.patch.object(self.archive, 'SHOW', 2):
            for name, total, pub in ((RANGE, 12, 11), (COAST, 3, 3), (PEAKS, 2, 2)):
                panel = Doc(self.panel_html(name))
                rows = panel.find_all('li', cls='arc-row')
                self.assertEqual(len(rows), total)                                            # every row is written whatever SHOW is
                more = [li for li in rows if 'arc-more' in li.classes]
                self.assertEqual(more, rows[2:] if total > 3 else [])
                self.assertEqual([b.text() for b in panel.find_all('button', cls='arc-all-btn')], ['Show all %d' % pub] if total > 3 else [])
        with mock.patch.object(self.archive, 'SHOW', 11):
            panel = Doc(self.panel_html(RANGE))                                               # twelve trips: SHOW + 1
            self.assertEqual(len(panel.find_all('li', cls='arc-row')), 12)
            self.assertEqual(panel.find_all('li', cls='arc-more'), [])
            self.assertEqual(panel.find_all('button'), [])
        with mock.patch.object(self.archive, 'SHOW', 10):
            panel = Doc(self.panel_html(RANGE))
            self.assertEqual([li['data-key'] for li in panel.find_all('li', cls='arc-more')], ['syn-r-undated', 'syn-r-goal'])
            self.assertEqual([b.text() for b in panel.find_all('button', cls='arc-all-btn')], ['Show all 11'])

    def test_there_is_no_link_to_the_page_it_is_on(self):
        # a.arc-reg-a ('All <Region> reports') is the Map page's link to this page; the first round's 'All N reports'
        # link down to the table is gone with the short list it stood under
        for name in PAGES:
            with self.subTest(region=name):
                self.assertEqual(self.doc(name).find_all('a', cls='arc-reg-a'), [])
                self.assertNotIn('arc-reg-a', self.html(name))
                self.assertNotIn('arc-reg-a', self.panel_html(name))
                box = self.panel(name).find('div', cls='arc-inreg')
                self.assertEqual([n.tag for n in box.elements() if n.tag == 'a'], [])
                hrefs = [a['href'] for a in self.panel(name).find_all('a')]
                self.assertEqual([h for h in hrefs if 'regions/' in h or h.startswith('#')], [])
                self.assertEqual(len(hrefs), len(self.group(name)))                           # the rows' links and no other (the map is empty)
                self.assertNotIn('reports<svg', inner(self.html(name), INREG, '</section>'))
        # the Map page's panel for the same region does have it (the site is registered with its region pages)
        self.assertEqual([a.text() for a in Doc(self.panel_html(RANGE, page=False, here='map/')).find_all('a', cls='arc-reg-a')],
                         ['All Synthetic Range reports'])

    def test_the_page_mode_panel_never_depends_on_what_is_registered(self):
        with_pages = {name: self.panel_html(name) for name in PAGES}
        core._REGION_PAGES.clear()
        for name in PAGES:
            self.assertEqual(self.panel_html(name), with_pages[name])
            self.assertNotIn('regions/', inner(self.panel_html(name), INREG, PANEL_TAIL))
        with mock.patch.object(core, 'region_page_href', lambda here, region: self.fail('the page-mode panel asked for a region page')):
            for name in PAGES:
                self.assertEqual(self.panel_html(name), with_pages[name])

    # ------------------------------------------------------------ the two modes side by side

    def as_page(self, old, name, slug):
        """The Map page's panel of commit fb425ab turned into the region page's: the three places where the contract
        makes the two differ (the wrapper and its heading, the list heading's level, what labels the list)."""
        swaps = (('<div class="arc-panel" id="region-%s"><h3 class="arc-panel-h t-h3" id="arc-ph-%s">%s</h3>' % (slug, slug, esc(name)),
                  '<div class="arc-panel" id="map">'),
                 ('<h4 class="t-label" id="arc-in-%s">In this region</h4>' % slug, '<h3 class="t-label" id="arc-in-%s">In this region</h3>' % slug),
                 (' aria-labelledby="arc-in-%s arc-ph-%s" ' % (slug, slug), ' aria-labelledby="arc-in-%s" ' % slug))
        for was, now in swaps:
            self.assertEqual(old.count(was), 1, was)
            old = old.replace(was, now)
        return old

    def test_the_page_mode_panel_is_the_map_pages_panel_but_for_three_things(self):
        # byte for byte: the panel of commit fb425ab (legacy_region_panel, which has no link to a region page) with its
        # wrapper id and heading, the level of the list's heading and the list's label changed, and nothing else: the
        # map, the caption, the legend, the count line, every row, the arc-more marks and the 'Show all' button
        for name, slug, ts in self.regs:
            for first in (True, False):
                for here in (self.here(name), 'map/', ''):
                    with self.subTest(region=name, first=first, here=here):
                        old = legacy_region_panel(self.archive, name, slug, ts, here, self.meta, first)
                        new = self.archive.region_panel(name, slug, ts, here, self.meta, first, page=True)
                        self.assertEqual(new, self.as_page(old, name, slug))
                        self.assertEqual(self.archive.region_panel(name, slug, ts, here, self.meta, first, True), new)
        self.assertEqual(names(self.regs), PAGES)
        # a map entry that records merged pins adds the cluster symbol to the legend: in both modes alike
        meta = json.loads(json.dumps(self.meta))
        meta['maps']['region-%s-desktop' % SLUG[RANGE]]['clusters'] = [{'x': 40, 'y': 40, 'n': 2, 'keys': ['syn-r-lap', 'syn-r-old']}]
        name, slug, ts = self.regs[0]
        old = legacy_region_panel(self.archive, name, slug, ts, self.here(name), meta, True)
        new = self.archive.region_panel(name, slug, ts, self.here(name), meta, True, page=True)
        self.assertEqual(new, self.as_page(old, name, slug))
        self.assertNotEqual(inner(new, SIDE, INREG), inner(self.panel_html(RANGE), SIDE, INREG))       # the legend is the one with the symbol

    def test_both_modes_write_the_same_rows_marks_and_button_for_the_same_trips(self):
        def parts(html_):
            doc = Doc(html_)
            ol = doc.find('ol', cls='arc-rows')
            return (inner(html_, '<ol class="arc-rows"', '</ol>').split('>', 1)[1],              # the rows, to the byte
                    [(li['data-key'], li.classes) for li in ol.elements()],
                    [(b['aria-controls'], b['aria-expanded'], 'hidden' in b, b.text()) for b in doc.find_all('button')],
                    ml_items(doc.find('div', cls='arc-inreg-h')), (ol['id'], ol['data-map-target']))

        for name in PAGES:
            for here in (self.here(name), 'map/'):
                with self.subTest(region=name, here=here):
                    self.assertEqual(parts(self.panel_html(name, here=here)), parts(self.panel_html(name, page=False, here=here)))
        mine = parts(self.panel_html(RANGE))
        self.assertEqual(len(mine[1]), 12)
        self.assertEqual([c for _k, c in mine[1]].count(['arc-row', 'arc-more']), 4)
        self.assertEqual(mine[2], [('arc-rows-synthetic-range', 'false', True, 'Show all 11')])
        # for any list of trips handed over, not only a region's own: a short one, one at the limit, a long one
        ts = self.group(RANGE)
        for k in (1, 8, 9, 10, 12):
            with self.subTest(trips=k):
                args = (RANGE, SLUG[RANGE], ts[:k], self.here(RANGE), self.meta, True)
                self.assertEqual(parts(self.archive.region_panel(*args, page=True)), parts(self.archive.region_panel(*args)))
                self.assertEqual(len(parts(self.archive.region_panel(*args, page=True))[2]), 1 if k > 9 else 0)

    # ------------------------------------------------------------ pins and cluster markers find their rows

    def marks(self, pins, clusters):
        """A region map's markers as tools/lib/mapkit.py writes them: a link per pin, an aria-hidden group per cluster
        whose data-keys names the trips whose pins it merged."""
        out = ''.join('<a class="mk-pin" href="@@ROOT@@trips/%s/" data-key="%s" aria-label="Synthetic pin"><title>Synthetic pin</title>'
                      '<circle class="mk-hit" cx="9" cy="9" r="12" style="fill: transparent"/></a>' % (s, s) for s in pins)
        return out + ''.join('<g class="mk-cluster" aria-hidden="true" data-keys="%s"><title>Synthetic cluster</title>'
                             '<circle class="mk-hit" cx="40" cy="40" r="14" style="fill: transparent"/><text x="40" y="40">%d</text></g>'
                             % (' '.join(keys), len(keys)) for keys in clusters)

    def test_every_key_of_every_cluster_marker_has_a_row_in_the_list_that_targets_the_map(self):
        # base.js: a click on a cluster marker looks, among the rows of the list whose data-map-target is the map's id,
        # for the first row whose data-key is one of the marker's data-keys; when that row is hidden it presses the
        # 'Show all' button of the row's list, then focuses the row's link. With the first round's short list (the eight
        # newest reports) a cluster of older reports, or of a report and a goal, found no row: a dead marker
        clusters = [['syn-r-story', 'syn-r-lap'],                 # a row that is shown and one behind 'Show all'
                    ['syn-r-old', 'syn-r-undated', 'syn-r-lap'],  # hidden rows only: reports nine to eleven
                    ['syn-r-raft', 'syn-r-goal'],                 # a report and the active goal
                    ['syn-r-short', 'syn-r-tour']]                # the report without a track of its own and the multi-day tour
        pins = ['syn-r-flag', 'syn-r-words', 'syn-r-photo', 'syn-r-paddle']
        self.use(marks={RANGE: self.marks(pins, clusters), COAST: self.marks([], [COAST_PUB])})
        for name, n_clusters in ((RANGE, 4), (COAST, 1)):
            with self.subTest(region=name):
                doc = self.doc(name)
                block = self.one(name, 'arc-map-' + SLUG[name])
                found = block.find_all('g', cls='mk-cluster')
                self.assertEqual(len(found), 2 * n_clusters)                                  # the desktop and the phone render
                lists = doc.find_all(attrs={'data-map-target': block['id']})
                self.assertEqual(len(lists), 1)
                rows = [n for n in lists[0].walk() if n['data-key']]
                keys_with_a_row = [n['data-key'] for n in rows]
                self.assertEqual(len(keys_with_a_row), len(set(keys_with_a_row)))
                for g in found:
                    keys = g['data-keys'].split()
                    self.assertGreater(len(keys), 1)
                    for key in keys:
                        self.assertIn(key, keys_with_a_row, 'a cluster marker names %s, which has no row beside the map' % key)
                    # the row the click goes to, and the way to it when the list is collapsed
                    row = next(n for n in rows if n['data-key'] in keys)
                    self.assertTrue(row.find('a')['href'].endswith('/trips/%s/' % row['data-key']))
                    if 'arc-more' in row.classes:
                        ol = lists[0]
                        opener = [b for b in doc.find_all('button') if b['aria-controls'] == ol['id'] and b['aria-expanded'] == 'false']
                        self.assertEqual(len(opener), 1, 'the row of %s is hidden and nothing opens its list' % row['data-key'])
                # every pin has its row as well (hovering one marks the other)
                for pin in block.find_all('a', cls='mk-pin'):
                    self.assertIn(pin['data-key'], keys_with_a_row)
                    self.assertEqual(pin['href'], '../../trips/%s/' % pin['data-key'])
        # the fixture does have a cluster that only hidden rows answer, and one that a planned route is part of
        hidden = {li['data-key'] for li in self.rows(RANGE) if 'arc-more' in li.classes}
        self.assertTrue(set(clusters[1]) <= hidden)
        self.assertIn('syn-r-goal', hidden)
        # ... and the list holds a row for every trip of the page, so no marker of an up-to-date map can be dead
        for name in PAGES:
            self.assertEqual([li['data-key'] for li in self.rows(name)], helpers.slugs(self.group(name)))
    # ------------------------------------------------------------ without page=True: the Map page's panel, as it was

    def groups(self):
        return self.archive.regions(self.site, self.meta)                 # every mapped region, the planned-only one too

    def test_without_a_registered_site_the_panel_is_byte_for_byte_the_old_one(self):
        # compared with legacy_region_panel, the function body of commit fb425ab copied into this file
        core._REGION_PAGES.clear()
        self.assertEqual(names(self.groups()), [RANGE, COAST, PEAKS, PLANS])
        for name, slug, ts in self.groups():
            for first in (True, False):
                for here in ('map/', 'regions/%s/' % slug, ''):
                    with self.subTest(region=name, first=first, here=here):
                        old = legacy_region_panel(self.archive, name, slug, ts, here, self.meta, first)
                        self.assertEqual(self.archive.region_panel(name, slug, ts, here, self.meta, first), old)
                        self.assertEqual(self.archive.region_panel(name, slug, ts, here, self.meta, first, page=False), old)
                        self.assertEqual(self.archive.region_panel(name, slug, ts, here, self.meta, first, False), old)
                        self.assertNotIn('arc-reg-a', old)
                        self.assertTrue(old.endswith(PANEL_TAIL))

    def test_for_a_site_registered_without_a_meta_the_panel_is_the_old_one_too(self):
        # REVISED in round 2: no meta, no region page, so no link: what every helper-made site gets
        core.register_site(self.site)
        for name, slug, ts in self.groups():
            for here in ('map/', ''):
                with self.subTest(region=name, here=here):
                    self.assertEqual(self.archive.region_panel(name, slug, ts, here, self.meta, True),
                                     legacy_region_panel(self.archive, name, slug, ts, here, self.meta, True))
        self.assertNotIn('arc-reg-a', self.archive.build(self.site)[0].html)

    def test_with_a_region_page_the_panel_is_the_old_one_and_one_link(self):
        self.assertEqual(sorted(core._REGION_PAGES), sorted(PAGES))
        for name, slug, ts in self.groups():
            for first in (True, False):
                with self.subTest(region=name, first=first):
                    old = legacy_region_panel(self.archive, name, slug, ts, 'map/', self.meta, first)
                    new = self.archive.region_panel(name, slug, ts, 'map/', self.meta, first)
                    if name == PLANS:                                       # a region map, no report: no page, no link
                        self.assertEqual(new, old)
                        continue
                    link = '<a class="alink arc-reg-a" href="../regions/%s/">All %s reports%s</a>' % (slug, esc(name), icon('arrow-right', 16))
                    self.assertEqual(new, old[:-len(PANEL_TAIL)] + link + PANEL_TAIL)
                    self.assertEqual(new.count('arc-reg-a'), 1)

    def test_the_link_comes_after_the_rows_and_the_show_all_button(self):
        new = self.panel_html(RANGE, page=False, here='map/')
        button = ('<button type="button" class="alink arc-all-btn" aria-expanded="false" aria-controls="arc-rows-synthetic-range" hidden>'
                  'Show all 11%s</button>' % icon('chevron-down', 16))
        link = '<a class="alink arc-reg-a" href="../regions/synthetic-range/">All Synthetic Range reports%s</a>' % icon('arrow-right', 16)
        self.assertTrue(new.endswith('</li></ol>' + button + link + PANEL_TAIL))
        # a region with few reports has no button: the link follows the rows
        coast = self.panel_html(COAST, page=False, here='map/')
        self.assertNotIn('arc-all-btn', coast)
        self.assertTrue(coast.endswith('</li></ol><a class="alink arc-reg-a" href="../regions/synthetic-coast/">All Synthetic Coast reports%s</a>'
                                       % icon('arrow-right', 16) + PANEL_TAIL))
        # the name is escaped, the address is relative to the page the panel is on
        peaks = self.panel_html(PEAKS, page=False, here='')
        self.assertIn('<a class="alink arc-reg-a" href="regions/synthetic-obrien-peaks/">All Synthetic O&#x27;Brien &amp; &lt;Peaks&gt; reports<svg', peaks)
        self.assertEqual(Doc(peaks).find('a', cls='arc-reg-a').text(), "All Synthetic O'Brien & <Peaks> reports")

    def test_the_two_modes_differ_where_the_contract_says(self):
        old, new = Doc(self.panel_html(RANGE, page=False)).find('div', cls='arc-panel'), Doc(self.panel_html(RANGE)).find('div', cls='arc-panel')
        self.assertEqual((old['id'], new['id']), ('region-synthetic-range', 'map'))
        self.assertEqual([h.tag for h in old.find_all(cls='t-label') if h['id']], ['h4'])
        self.assertEqual([h.tag for h in new.find_all(cls='t-label') if h['id']], ['h3'])
        self.assertEqual(old.find('ol')['aria-labelledby'], 'arc-in-synthetic-range arc-ph-synthetic-range')
        self.assertEqual(new.find('ol')['aria-labelledby'], 'arc-in-synthetic-range')
        self.assertEqual((len(old.find_all('li', cls='arc-row')), len(new.find_all('li', cls='arc-row'))), (12, 12))      # the same rows
        self.assertEqual((len(old.find_all('li', cls='arc-more')), len(new.find_all('li', cls='arc-more'))), (4, 4))
        self.assertEqual((old.find('ol')['id'], old.find('ol')['data-map-target']), (new.find('ol')['id'], new.find('ol')['data-map-target']))
        self.assertEqual([b.text() for b in old.find_all('button')], [b.text() for b in new.find_all('button')])
        # the heading with the region's name is the Map page's alone, and so is the link to the region's page
        self.assertEqual(([h.text() for h in old.find_all(cls='arc-panel-h')], new.find_all(cls='arc-panel-h')), ([RANGE], []))
        self.assertEqual((len(old.find_all('a', cls='arc-reg-a')), len(new.find_all('a', cls='arc-reg-a'))), (1, 0))
        # in both the list's box ends the panel: the rows, the button, and on the Map page the link after them
        self.assertEqual([n.tag for n in old.find('div', cls='arc-inreg').elements()], ['div', 'ol', 'button', 'a'])
        self.assertEqual([n.tag for n in new.find('div', cls='arc-inreg').elements()], ['div', 'ol', 'button'])


# ---------------------------------------------------------------- round 3: the legend is the key to the map

SKI, CLIMB, RIDE = 'Backcountry Ski', 'Climbing', 'Mountain Biking'


class LegendTests(RegionFixture):
    """The legend beside the map of a region page (round 3). A region page lists what the content files under the region;
    its map shows what it was last drawn with. The legend explains the map, so it names the activities and the symbols of
    the trips the map draws, as the Map page's legend for the same map does, and not those of the page's list.

    The site: under Synthetic Range three reports with a track, of three activities (what the map's entry names in most
    tests), and three more things that are on the page's list and on no map: a report without a track, the only one of
    its activity (Other, paddleboarding); a journal (a hike); an active goal without a route. Synthetic Coast has two
    reports and a map entry that names both."""

    DEFAULT = False
    DRAWN = ['syn-r-ski', 'syn-r-climb', 'syn-r-ride']                       # the map's entry, newest first
    LISTED = ['syn-r-paddle', 'syn-r-ski', 'syn-r-climb', 'syn-r-ride', 'syn-r-journal', 'syn-r-goal']       # the page's rows
    COVES = ['syn-r-cove-b', 'syn-r-cove-a']

    def setUp(self):
        super().setUp()
        mk = self.mk
        mk('syn-r-ski', title='Synthetic Ski Lap', activity='ski', date='2026-03-01', region=RANGE)
        mk('syn-r-climb', title='Synthetic Climb', activity='climb', date='2025-08-01', region=RANGE)
        mk('syn-r-ride', title='Synthetic Ride', activity='mtb', date='2024-06-01', region=RANGE)
        mk('syn-r-paddle', title='Synthetic Paddle', activity='other', subtype='SUP', date='2026-05-01', region=RANGE, track=False)
        helpers.make_series(self.trips_dir, slug='syn-r-journal', title='Synthetic Journal', region=RANGE)      # a hike, April 2024
        self.goal('syn-r-goal', title='Synthetic Goal', region=RANGE)
        mk('syn-r-cove-a', title='Synthetic Cove A', date='2026-01-10', region=COAST)
        mk('syn-r-cove-b', title='Synthetic Cove B', activity='mtb', date='2026-03-05', region=COAST)

    def draw(self, range_trips=DRAWN, **kw):
        """The site with a region map for the Range whose entry names `range_trips` (None: an entry without a list)."""
        named = {COAST: self.COVES}
        if range_trips is not None:
            named[RANGE] = list(range_trips)
        self.use(mapped=[RANGE, COAST], all_regions=[RANGE, COAST], named=named, **kw)

    def entry(self, name=RANGE):
        return self.meta['maps']['region-%s-desktop' % SLUG[name]]

    def legend_html(self, html_):
        """The legend of a panel or of a page that holds one panel: what stands between the side column's start and the
        list's box, which is archive.legend's whole output."""
        return inner(html_, SIDE, INREG)

    def legend(self, name=RANGE):
        """(the activities, the map symbols) the legend of the region's page names, as a reader sees them."""
        box = self.one(name, 'map').find('div', cls='arc-legend')
        self.assertEqual([(n.tag, n.text()) for n in box.elements()][:1], [('p', 'Legend')])
        lists = box.find_all('ul')
        self.assertEqual([ul['aria-label'] for ul in lists], ['Activities', 'Map symbols'][:len(lists)])
        # an item is a drawing and its word: the word is the item's last element (the cluster symbol's drawing has a digit)
        return [[li.elements()[-1].text() for li in ul.find_all('li')] for ul in lists] + [[]] * (2 - len(lists))

    def map_panel(self, name=RANGE):
        """The region's panel on the Map page built for the same site."""
        html_ = self.archive.build(self.site)[0].html
        start = html_.index('<div class="arc-panel" id="region-%s">' % SLUG[name])
        return html_[start:html_.index(PANEL_TAIL, start) + len(PANEL_TAIL)]

    # ------------------------------------------------------------ the fixture

    def test_the_page_lists_more_than_its_map_draws(self):
        self.draw()
        self.assertEqual(names(self.regs), [RANGE, COAST])
        self.assertEqual(helpers.slugs(self.group(RANGE)), self.LISTED)
        self.assertEqual([li['data-key'] for li in self.one(RANGE, 'arc-rows-' + SLUG[RANGE]).elements()], self.LISTED)
        self.assertEqual(ml_items(self.one(RANGE, 'map').find('div', cls='arc-inreg-h')), ['5 REPORTS', 'INCL. 1 SERIES', '+ 1 PLANNED ROUTE'])
        on_the_map = helpers.slugs(self.region.map_trips(RANGE, self.site, self.meta))
        self.assertEqual(on_the_map, self.DRAWN)
        # what the list has and the map has not: each would put something of its own into a legend made from the list
        extra = self.trips(*[s for s in self.LISTED if s not in on_the_map])
        self.assertEqual([(t['slug'], t['kind'], t['activity'], core.has_track(t)) for t in extra],
                         [('syn-r-paddle', 'trip', 'other', False), ('syn-r-journal', 'series', 'hike', True), ('syn-r-goal', 'planned', 'hike', False)])
        drawn = self.trips(*self.DRAWN)
        self.assertEqual([t['activity'] for t in drawn], ['ski', 'climb', 'mtb'])
        self.assertTrue(all(core.has_track(t) and t['kind'] == 'trip' for t in drawn))
        # a legend made from the list, as the page had it before round 3, would name all of this
        self.assertEqual([li.elements()[-1].text() for li in Doc(self.archive.legend(self.group(RANGE), self.entry())).find_all('li')],
                         [SKI, CLIMB, 'Hiking', RIDE, 'Paddleboarding', 'Planned route'])

    # ------------------------------------------------------------ what the legend names

    def test_the_legend_names_the_activities_of_the_trips_the_map_draws_and_no_other(self):
        self.draw()
        self.assertEqual(self.legend(), [[SKI, CLIMB, RIDE], []])
        # no disc for the report without a track or for the journal, and no line for the goal without a route
        html_ = self.legend_html(self.html(RANGE))
        for word in ('Paddleboarding', 'Other', 'Hiking', 'Planned route', 'Map symbols'):
            self.assertNotIn(word, html_)
        self.assertEqual(html_.count('<li>'), 3)
        # all three are on the page all the same: in the list beside the map and in the table
        rows = [li['data-key'] for li in self.one(RANGE, 'arc-rows-' + SLUG[RANGE]).elements()]
        table = [a['data-key'] for a in self.one(RANGE, 'all-reports').find_all('a', cls='rtab-r')]
        for slug in ('syn-r-paddle', 'syn-r-journal', 'syn-r-goal'):
            self.assertIn(slug, rows)
            self.assertIn(slug, table)

    def test_it_follows_the_map_whichever_trips_the_map_draws(self):
        # one activity; two; the report filed under another region that a stale map still draws
        for named, want in ((['syn-r-climb'], [CLIMB]), (['syn-r-ride', 'syn-r-ski'], [SKI, RIDE]),
                            (['syn-r-ski', 'syn-r-cove-a'], [SKI, 'Hiking']), (self.DRAWN + ['syn-r-journal'], [SKI, CLIMB, 'Hiking', RIDE])):
            with self.subTest(named=named):
                self.draw(named)
                self.assertEqual(self.legend(), [want, []])

    def test_a_goal_the_map_draws_brings_the_planned_route_symbol(self):
        # a second goal, this one with a route: on the list it adds nothing to the legend either
        helpers.touch(os.path.join(self.goal('syn-r-route', title='Synthetic Route', region=RANGE), 'track.gpx'))
        self.draw()
        self.assertEqual(helpers.slugs(self.planned(RANGE)), ['syn-r-goal', 'syn-r-route'])
        self.assertTrue(core.has_track(self.by['syn-r-route']))
        self.assertEqual(self.legend(), [[SKI, CLIMB, RIDE], []])
        # named by the map's entry, it is drawn: the legend explains its line
        self.draw(self.DRAWN + ['syn-r-route'])
        self.assertEqual(helpers.slugs(self.region.map_trips(RANGE, self.site, self.meta)), self.DRAWN + ['syn-r-route'])
        self.assertEqual(self.legend(), [[SKI, CLIMB, RIDE], ['Planned route']])
        symbols = self.one(RANGE, 'map').find('ul', attrs={'aria-label': 'Map symbols'})
        self.assertEqual(len(symbols.find_all('svg')), 1)
        # a goal alone on the map: its symbol and no activity (a planned route is no report)
        self.draw(['syn-r-route'])
        self.assertEqual(self.legend(), [[], ['Planned route']])

    def test_the_cluster_symbol_still_comes_from_the_maps_entry(self):
        # the map's entry records the pins it merged: the symbol is in the legend whoever is on the list, as on the Map page
        self.draw()
        self.entry()['clusters'] = [{'x': 40, 'y': 40, 'n': 2, 'keys': ['syn-r-ski', 'syn-r-climb']}, {'x': 9, 'y': 9, 'n': 1, 'keys': ['syn-r-ride']}]
        with open(os.path.join(self.site_dir, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(self.meta, fh)                             # the page module reads the file as it is on disk
        self.pages = {p.url: p for p in self.region.build(self.site)}
        self._docs = {}
        self.assertEqual(self.legend(), [[SKI, CLIMB, RIDE], ['Several reports start here']])
        self.assertEqual(self.legend_html(self.html(RANGE)), self.archive.legend(self.trips(*self.DRAWN), self.entry()))
        self.assertEqual(self.legend_html(self.html(RANGE)), self.legend_html(self.map_panel(RANGE)))
        self.assertEqual(self.legend(COAST), [['Hiking', RIDE], []])              # an entry without a merged pin: no symbol

    # ------------------------------------------------------------ it is the Map page's legend for the same map

    def test_it_is_archive_legend_of_the_maps_group_and_the_maps_entry(self):
        for named in (self.DRAWN, ['syn-r-climb'], self.LISTED):
            with self.subTest(named=named):
                self.draw(named)
                group = self.region.map_trips(RANGE, self.site, self.meta)
                self.assertEqual(self.legend_html(self.html(RANGE)), self.archive.legend(group, self.entry()))
                # the page's rows name the report without a track, which no map draws: the build has nothing of it
                # to leave out, and says so for each of the Range's two maps
                self.assertEqual(self.stderr.count('no pin or line to leave out for syn-r-paddle'), 2 if 'syn-r-paddle' in named else 0)
        self.draw()
        self.assertNotEqual(self.archive.legend(self.trips(*self.DRAWN), self.entry()), self.archive.legend(self.group(RANGE), self.entry()))

    def test_it_equals_the_legend_the_map_page_shows_for_the_same_map(self):
        helpers.touch(os.path.join(self.goal('syn-r-route', title='Synthetic Route', region=RANGE), 'track.gpx'))
        for named in (self.DRAWN, self.DRAWN + ['syn-r-route'], ['syn-r-ski', 'syn-r-cove-a'], None):
            with self.subTest(named=named):
                self.draw(named)
                mine = self.legend_html(self.html(RANGE))
                group = self.region.map_trips(RANGE, self.site, self.meta)
                # archive.region_panel as the Map page calls it (page=False), on the map's group
                for here in ('map/', self.here(RANGE)):
                    theirs = self.archive.region_panel(RANGE, SLUG[RANGE], group, here, self.meta, True)
                    self.assertEqual(self.legend_html(theirs), mine)
                    self.assertEqual(self.legend_html(self.archive.region_panel(RANGE, SLUG[RANGE], group, here, self.meta, False, page=False)), mine)
                # ... and on the Map page as built, where that panel stands
                self.assertEqual(self.legend_html(self.map_panel(RANGE)), mine)
                self.assertEqual([li['data-key'] for li in Doc(self.map_panel(RANGE)).find_all('li', cls='arc-row')], helpers.slugs(group))
        # a map in step with the content (the Coast's): the legend is the list's, as it always was
        self.draw()
        self.assertEqual(helpers.slugs(self.region.map_trips(COAST, self.site, self.meta)), helpers.slugs(self.group(COAST)))
        self.assertEqual(self.legend_html(self.html(COAST)), self.archive.legend(self.group(COAST), self.entry(COAST)))
        self.assertEqual(self.legend_html(self.html(COAST)), self.legend_html(self.map_panel(COAST)))
        self.assertEqual(self.legend(COAST), [['Hiking', RIDE], []])

    def test_a_maps_entry_without_a_list_of_trips_has_the_map_pages_fallback_group(self):
        # core.region_groups then takes the listed trips filed under the region, a journal left out (it is on no region
        # map): the Map page's legend for that map, and so the page's
        self.draw(None)
        self.assertNotIn('trips', self.entry())
        group = self.region.map_trips(RANGE, self.site, self.meta)
        self.assertEqual(helpers.slugs(group), ['syn-r-paddle', 'syn-r-ski', 'syn-r-climb', 'syn-r-ride', 'syn-r-goal'])
        self.assertEqual(self.legend(), [[SKI, CLIMB, RIDE, 'Paddleboarding'], ['Planned route']])
        self.assertEqual(self.legend_html(self.html(RANGE)), self.legend_html(self.map_panel(RANGE)))
        self.assertIn('syn-r-journal', [li['data-key'] for li in self.one(RANGE, 'arc-rows-' + SLUG[RANGE]).elements()])      # on the list still

    # ------------------------------------------------------------ a map that draws nothing of the site: the list

    def test_when_the_map_names_no_trip_of_the_site_the_legend_is_made_from_the_list(self):
        # every report the map was drawn with has since been removed or renamed: there is no group to ask
        self.draw(['syn-r-gone', 'syn-r-renamed'])
        self.assertEqual(self.region.map_trips(RANGE, self.site, self.meta), [])
        self.assertNotIn(RANGE, names(core.region_groups(self.site, self.meta)))             # and no panel on the Map page
        self.assertIn(self.here(RANGE), self.pages)                                           # the page is there all the same
        self.assertEqual(self.legend(), [[SKI, CLIMB, 'Hiking', RIDE, 'Paddleboarding'], ['Planned route']])
        self.assertEqual(self.legend_html(self.html(RANGE)), self.archive.legend(self.group(RANGE), self.entry()))
        # not an empty legend, which is what the trips the map draws would give
        self.assertEqual(Doc(self.archive.legend([], self.entry())).find_all('li'), [])
        # an archived goal or a draft the map still names is no trip of the site either
        self.goal('syn-r-shelved', archived=True, title='Synthetic Shelved Goal', region=RANGE)
        mk_draft = self.mk('syn-r-draft', title='Synthetic Draft', activity='climb', date='2026-07-01', region=RANGE, draft=True)
        self.assertTrue(os.path.isdir(mk_draft))
        self.draw(['syn-r-shelved', 'syn-r-draft'])
        self.assertEqual(self.region.map_trips(RANGE, self.site, self.meta), [])
        self.assertEqual(self.legend(), [[SKI, CLIMB, 'Hiking', RIDE, 'Paddleboarding'], ['Planned route']])

    # ------------------------------------------------------------ region.map_trips

    def test_map_trips_is_the_map_pages_group_for_the_region(self):
        self.draw()
        map_trips = need(self, self.region, 'map_trips')
        groups = {name: ts for name, _slug, ts in core.region_groups(self.site, self.meta)}
        self.assertEqual(sorted(groups), sorted([RANGE, COAST]))
        for name in (RANGE, COAST):
            with self.subTest(region=name):
                got = map_trips(name, self.site, self.meta)
                self.assertIsInstance(got, list)
                self.assertEqual(helpers.slugs(got), helpers.slugs(groups[name]))
                self.assertTrue(all(a is b for a, b in zip(got, groups[name])))              # the site's own trip dicts
        self.assertEqual(helpers.slugs(map_trips(RANGE, self.site, self.meta)), self.DRAWN)
        self.assertEqual(helpers.slugs(map_trips(COAST, self.site, self.meta)), self.COVES)   # each region its own, not the first group
        # in the group's order whatever order the entry names them in: newest first, a planned route last
        helpers.touch(os.path.join(self.goal('syn-r-route', title='Synthetic Route', region=RANGE), 'track.gpx'))
        self.draw(['syn-r-route', 'syn-r-ride', 'syn-r-ski', 'syn-r-climb'])
        self.assertEqual(helpers.slugs(map_trips(RANGE, self.site, self.meta)), self.DRAWN + ['syn-r-route'])

    def test_map_trips_is_an_empty_list_for_a_region_without_a_group(self):
        self.draw()
        map_trips = self.region.map_trips
        for name in (DESERT, PLANS, 'Synthetic Nowhere', '', None, RANGE.lower(), RANGE + ' '):
            with self.subTest(region=name):
                self.assertEqual(map_trips(name, self.site, self.meta), [])
                self.assertIsInstance(map_trips(name, self.site, self.meta), list)
        self.assertEqual(map_trips(RANGE, self.site, {'maps': {}, 'regions': []}), [])
        self.assertEqual(map_trips(RANGE, self.site, {}), [])
        self.draw(['syn-r-gone'])
        self.assertEqual(map_trips(RANGE, self.site, self.meta), [])
        self.assertEqual(helpers.slugs(map_trips(COAST, self.site, self.meta)), self.COVES)

    def test_map_trips_reads_the_meta_it_is_handed(self):
        self.draw()
        other = json.loads(json.dumps(self.meta))
        other['maps']['region-%s-desktop' % SLUG[RANGE]]['trips'] = ['syn-r-climb']
        self.assertEqual(helpers.slugs(self.region.map_trips(RANGE, self.site, other)), ['syn-r-climb'])
        self.assertEqual(helpers.slugs(self.region.map_trips(RANGE, self.site, self.meta)), self.DRAWN)
        self.assertEqual(core.site_meta(), self.meta)                    # core's own copy was the fixture's all along
        # the desktop map's entry is the one that is read, as core.region_groups reads it
        other['maps']['region-%s-phone' % SLUG[RANGE]]['trips'] = ['syn-r-ride']
        self.assertEqual(helpers.slugs(self.region.map_trips(RANGE, self.site, other)), ['syn-r-climb'])
        with mock.patch.object(core, 'region_groups', return_value=[(COAST, SLUG[COAST], ['a']), (RANGE, SLUG[RANGE], ['b', 'c'])]) as asked:
            self.assertEqual(self.region.map_trips(RANGE, self.site, other), ['b', 'c'])
            self.assertEqual(self.region.map_trips('Synthetic Nowhere', self.site, other), [])
        self.assertEqual([c[0] for c in asked.call_args_list], [(self.site, other)] * 2)

    # ------------------------------------------------------------ how the page hands them to the panel

    def panel_calls(self):
        """What region.page hands archive.region_panel for each page of the site: {region: (args, kwargs)}."""
        real, calls = self.archive.region_panel, {}

        def recorder(*args, **kw):
            calls[args[0]] = (args, kw)
            return real(*args, **kw)

        with mock.patch.object(self.archive, 'region_panel', recorder):
            self.region.build(self.site)
        return calls

    def test_the_page_hands_the_panel_the_trips_its_map_draws(self):
        self.draw()
        calls = self.panel_calls()
        self.assertEqual(sorted(calls), sorted([RANGE, COAST]))
        for name in (RANGE, COAST):
            with self.subTest(region=name):
                args, kw = calls[name]
                self.assertEqual(args[:2], (name, SLUG[name]))
                self.assertEqual(helpers.slugs(args[2]), helpers.slugs(self.group(name)))     # the list is the page's own, as before
                self.assertEqual(args[3:], (self.here(name), self.meta, True))
                self.assertEqual(sorted(kw), ['drawn', 'page', 'site'])
                self.assertIs(kw['page'], True)
                self.assertIs(kw['site'], self.site)      # for the journals that have days in the region (journal_parts)
                self.assertEqual(helpers.slugs(kw['drawn']), helpers.slugs(self.region.map_trips(name, self.site, self.meta)))
        self.assertEqual(helpers.slugs(calls[RANGE][1]['drawn']), self.DRAWN)

    def test_without_a_group_the_page_hands_over_none_and_the_panel_uses_its_list(self):
        self.draw(['syn-r-gone'])
        calls = self.panel_calls()
        self.assertIsNone(calls[RANGE][1]['drawn'])
        self.assertEqual(helpers.slugs(calls[COAST][1]['drawn']), self.COVES)
        args = (RANGE, SLUG[RANGE], self.group(RANGE), self.here(RANGE), self.meta, True)
        self.assertEqual(self.archive.region_panel(*args, page=True, drawn=None), self.archive.region_panel(*args, page=True))
        self.assertEqual(self.html(RANGE).count(self.archive.region_panel(*args, page=True)), 1)

    # ------------------------------------------------------------ archive.region_panel(..., drawn=...)

    def test_drawn_changes_the_legend_and_nothing_else_of_the_page_mode_panel(self):
        self.draw()
        ts, entry = self.group(RANGE), self.entry()
        for here in (self.here(RANGE), 'map/'):
            for first in (True, False):
                args = (RANGE, SLUG[RANGE], ts, here, self.meta, first)
                plain = self.archive.region_panel(*args, page=True)
                self.assertEqual(plain.count(self.archive.legend(ts, entry)), 1)
                for drawn in (self.DRAWN, ['syn-r-climb'], ['syn-r-goal'], self.LISTED, ['syn-r-cove-a', 'syn-r-ski']):
                    with self.subTest(here=here, first=first, drawn=drawn):
                        got = self.archive.region_panel(*args, page=True, drawn=self.trips(*drawn))
                        self.assertEqual(got, plain.replace(self.archive.legend(ts, entry), self.archive.legend(self.trips(*drawn), entry)))
                        # the rows, the count line and the 'Show all' button are the list's whatever the map draws
                        self.assertEqual(inner(got, INREG, PANEL_TAIL), inner(plain, INREG, PANEL_TAIL))
                        self.assertEqual(inner(got, MAPCOL, SIDE), inner(plain, MAPCOL, SIDE))
                # the list handed over as what the map draws: the same panel
                self.assertEqual(self.archive.region_panel(*args, page=True, drawn=list(ts)), plain)
        # the page as built is that panel, in its one map section
        page_panel = self.archive.region_panel(RANGE, SLUG[RANGE], ts, self.here(RANGE), self.meta, True, page=True, drawn=self.trips(*self.DRAWN))
        self.assertEqual(self.html(RANGE).count('<h2 class="sr" id="reg-map-h">Map</h2>%s</section>' % page_panel), 1)

    def test_the_whole_page_differs_from_the_list_made_one_in_its_legend_alone(self):
        self.draw()
        ts, entry = self.group(RANGE), self.entry()
        mine = self.html(RANGE)
        with mock.patch.object(self.region, 'map_trips', lambda name, site, meta: []):
            from_list = {p.url: p.html for p in self.region.build(self.site)}[self.here(RANGE)]
        key, listed = self.archive.legend(self.trips(*self.DRAWN), entry), self.archive.legend(ts, entry)
        self.assertEqual((mine.count(key), from_list.count(listed)), (1, 1))
        self.assertEqual(mine.replace(key, listed), from_list)
        # the head, the description and the table go by the list, not by the map
        self.assertIn('5\xa0REPORTS', mine.split('<p class="reg-stats">', 1)[1].split('</p>', 1)[0])
        self.assertIn('Synthetic Range: 5 trip reports, 2024 to 2026 (backcountry ski, climbing, hiking, mountain biking and paddleboarding)', mine)

    def test_without_page_mode_the_panel_takes_no_notice_of_drawn(self):
        # the Map page's panel is the function of commit fb425ab (legacy_region_panel) and, for a region with a page, its
        # one link: its legend is made from the trips it is handed, as it always was, whatever `drawn` says
        self.draw()
        self.assertEqual(sorted(core._REGION_PAGES), sorted([RANGE, COAST]))
        link = '<a class="alink arc-reg-a" href="../regions/%s/">All %s reports%s</a>' % (SLUG[RANGE], esc(RANGE), icon('arrow-right', 16))
        others = [None, [], self.trips('syn-r-climb'), self.trips(*self.DRAWN), self.trips('syn-r-cove-a'), self.trips('syn-r-goal')]
        for ts in (self.group(RANGE), self.region.map_trips(RANGE, self.site, self.meta), self.trips('syn-r-goal', 'syn-r-paddle')):
            for first in (True, False):
                old = legacy_region_panel(self.archive, RANGE, SLUG[RANGE], ts, 'map/', self.meta, first)
                want = old[:-len(PANEL_TAIL)] + link + PANEL_TAIL
                self.assertEqual(self.archive.region_panel(RANGE, SLUG[RANGE], ts, 'map/', self.meta, first), want)
                for drawn in others:
                    with self.subTest(trips=helpers.slugs(ts), first=first, drawn=drawn and helpers.slugs(drawn)):
                        self.assertEqual(self.archive.region_panel(RANGE, SLUG[RANGE], ts, 'map/', self.meta, first, drawn=drawn), want)
                        self.assertEqual(self.archive.region_panel(RANGE, SLUG[RANGE], ts, 'map/', self.meta, first, False, drawn), want)
                        self.assertEqual(self.archive.region_panel(RANGE, SLUG[RANGE], ts, 'map/', self.meta, first, page=False, drawn=drawn), want)
        # with no region page registered: the old function to the byte
        core._REGION_PAGES.clear()
        for ts in (self.group(RANGE), self.region.map_trips(RANGE, self.site, self.meta)):
            for drawn in others:
                self.assertEqual(self.archive.region_panel(RANGE, SLUG[RANGE], ts, 'map/', self.meta, True, page=False, drawn=drawn),
                                 legacy_region_panel(self.archive, RANGE, SLUG[RANGE], ts, 'map/', self.meta, True))

    def test_the_map_page_is_built_as_before(self):
        # its panels are still the old function on core.region_groups, and one link each
        self.draw()
        html_ = self.archive.build(self.site)[0].html
        for name, slug, ts in self.archive.regions(self.site, self.meta):
            with self.subTest(region=name):
                old = legacy_region_panel(self.archive, name, slug, ts, 'map/', self.meta, name == RANGE)
                link = '<a class="alink arc-reg-a" href="../regions/%s/">All %s reports%s</a>' % (slug, esc(name), icon('arrow-right', 16))
                self.assertEqual(html_.count(old[:-len(PANEL_TAIL)] + link + PANEL_TAIL), 1)
        self.assertEqual(names(self.archive.regions(self.site, self.meta)), [RANGE, COAST])


# ---------------------------------------------------------------- section 3.3: Featured

class FeaturedTests(RegionFixture):

    def setUp(self):
        super().setUp()
        self.pick = need(self, self.region, 'pick_featured')

    def picks(self, *slugs):
        return helpers.slugs(self.pick(self.trips(*slugs)))

    def section(self, name):
        return self.main(name).find('section', cls='reg-feat')

    # ------------------------------------------------------------ region.pick_featured

    def test_the_fixture_has_every_kind_of_candidate(self):
        by = self.by
        self.assertTrue(by['syn-r-flag']['featured'])
        self.assertFalse(by['syn-r-flag']['has_writeup'] or by['syn-r-flag']['cover'])
        for slug, written, cover in (('syn-r-story', True, True), ('syn-r-old', True, True), ('syn-r-words', True, False),
                                     ('syn-r-tour', True, False), ('syn-r-photo', False, True), ('syn-r-short', False, False),
                                     ('syn-r-lap', False, False)):
            self.assertEqual((core.written_report(by[slug]), bool(by[slug]['cover'])), (written, cover), slug)
            self.assertFalse(by[slug]['featured'], slug)
        self.assertTrue(by['syn-r-short']['has_writeup'])              # a note: a write-up, not a written report
        self.assertEqual(by['syn-r-tour']['body_md'], '')              # written on a day, not in index.md

    def test_the_flagged_then_the_written_with_a_cover_then_the_written_without(self):
        self.assertEqual(self.region.FEATURED_MAX, 3)
        self.assertEqual(helpers.slugs(self.pick(self.group(RANGE))), ['syn-r-flag', 'syn-r-story', 'syn-r-old'])
        self.assertEqual(helpers.slugs(self.pick(self.group(COAST))), ['syn-r-cove-a'])
        self.assertEqual(helpers.slugs(self.pick(self.group(PEAKS))), ['syn-r-wall-a', 'syn-r-wall-b'])
        self.assertIs(self.pick(self.group(RANGE))[0], self.by['syn-r-flag'])       # the trips themselves, in a list

    def test_each_tier_comes_before_the_next_whatever_the_dates(self):
        # tier 0, the flag: before a newer written report with a cover
        self.assertEqual(self.picks('syn-r-story', 'syn-r-flag'), ['syn-r-flag', 'syn-r-story'])
        # tier 1, written with a cover: before newer written reports without one
        self.assertEqual(self.picks('syn-r-words', 'syn-r-tour', 'syn-r-old'), ['syn-r-old', 'syn-r-words', 'syn-r-tour'])
        # tier 2, written without a cover: still a candidate, after the two others
        self.assertEqual(self.picks('syn-r-words', 'syn-r-old', 'syn-r-flag'), ['syn-r-flag', 'syn-r-old', 'syn-r-words'])
        self.assertEqual(self.picks('syn-r-tour'), ['syn-r-tour'])

    def test_inside_a_tier_the_order_of_the_list_is_kept(self):
        # the list is newest first, so that is newest first; the function does not sort by date itself
        self.assertEqual(self.picks('syn-r-story', 'syn-r-old'), ['syn-r-story', 'syn-r-old'])
        self.assertEqual(self.picks('syn-r-old', 'syn-r-story'), ['syn-r-old', 'syn-r-story'])
        self.assertEqual(self.picks('syn-r-tour', 'syn-r-words'), ['syn-r-tour', 'syn-r-words'])
        flagged_story = dict(self.by['syn-r-story'], featured=True)
        self.assertEqual(self.pick([flagged_story, self.by['syn-r-flag']]), [flagged_story, self.by['syn-r-flag']])
        self.assertEqual(self.pick([self.by['syn-r-flag'], flagged_story]), [self.by['syn-r-flag'], flagged_story])

    def test_a_flagged_report_needs_neither_a_write_up_nor_a_photo_and_is_picked_once(self):
        self.assertEqual(self.picks('syn-r-lap', 'syn-r-flag'), ['syn-r-flag'])
        flagged_story = dict(self.by['syn-r-story'], featured=True)       # flagged, written, with a cover: one card
        self.assertEqual(self.pick([flagged_story]), [flagged_story])

    def test_the_cap_is_featured_max(self):
        five = ['syn-r-story', 'syn-r-flag', 'syn-r-words', 'syn-r-tour', 'syn-r-old']
        self.assertEqual(self.picks(*five), ['syn-r-flag', 'syn-r-story', 'syn-r-old'])
        for cap, want in ((1, ['syn-r-flag']), (2, ['syn-r-flag', 'syn-r-story']),
                          (4, ['syn-r-flag', 'syn-r-story', 'syn-r-old', 'syn-r-words']),
                          (9, ['syn-r-flag', 'syn-r-story', 'syn-r-old', 'syn-r-words', 'syn-r-tour'])):
            with mock.patch.object(self.region, 'FEATURED_MAX', cap):
                self.assertEqual(self.picks(*five), want)
        self.assertEqual(self.picks('syn-r-story', 'syn-r-old'), ['syn-r-story', 'syn-r-old'])        # fewer than the cap: all of them

    def test_no_candidate_gives_an_empty_list(self):
        self.assertEqual(self.pick([]), [])
        self.assertEqual(self.picks('syn-r-photo', 'syn-r-short', 'syn-r-paddle', 'syn-r-raft', 'syn-r-lap', 'syn-r-undated'), [])

    def test_an_unwritten_report_is_never_picked(self):
        # photos and no write-up; a note shorter than a written report; a bare track: none of them, with or without
        # better candidates beside them
        for slug in ('syn-r-photo', 'syn-r-short', 'syn-r-lap', 'syn-r-undated', 'syn-r-cove-b'):
            with self.subTest(slug=slug):
                self.assertEqual(self.picks(slug), [])
                self.assertEqual(self.picks(slug, 'syn-r-words'), ['syn-r-words'])
        with mock.patch.object(self.region, 'FEATURED_MAX', 99):
            self.assertEqual(helpers.slugs(self.pick(self.group(RANGE))), ['syn-r-flag', 'syn-r-story', 'syn-r-old', 'syn-r-words', 'syn-r-tour'])

    def test_a_planned_route_is_never_picked(self):
        # even one that is flagged and has long planning notes and a photo
        self.mk('syn-r-flag-goal', title='Synthetic Flagged Goal', kind='planned', region=RANGE, featured=True, body=LONG,
                photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic goal photo')])
        self.use()
        goal = self.by['syn-r-flag-goal']
        self.assertEqual((goal['kind'], goal['featured'], bool(goal['body_md']), bool(goal['cover'])), ('planned', True, True, True))
        self.assertIn(goal, self.group(RANGE))
        self.assertEqual(self.pick([goal]), [])
        self.assertEqual(self.pick([goal, self.by['syn-r-goal']]), [])
        self.assertEqual(helpers.slugs(self.pick(self.group(RANGE))), ['syn-r-flag', 'syn-r-story', 'syn-r-old'])
        self.assertNotIn('syn-r-flag-goal', [li['data-slug'] for li in self.section(RANGE).find_all('li', cls='tcard')])

    def test_a_journal_filed_under_the_region_can_be_picked(self):
        # REVISED in round 2: the page lists a journal that is filed under the region, so it is a candidate like any
        # other report: flagged it leads, written with a cover it stands among those by its date
        helpers.make_series(self.trips_dir, slug='syn-r-range-journal', title='Synthetic Range Journal', region=RANGE, body=LONG)
        self.use()
        journal = self.by['syn-r-range-journal']
        self.assertEqual((journal['kind'], core.written_report(journal), bool(journal['cover']), journal['featured']), ('series', True, True, False))
        self.assertIn(journal, self.group(RANGE))
        self.assertEqual(self.pick([journal]), [journal])
        # 2024: after the story of 2026, before the old story of 2022, which it pushes out of the three
        self.assertEqual(helpers.slugs(self.pick(self.group(RANGE))), ['syn-r-flag', 'syn-r-story', 'syn-r-range-journal'])
        cards = self.section(RANGE).find_all('li', cls='tcard')
        self.assertEqual([li['data-slug'] for li in cards], ['syn-r-flag', 'syn-r-story', 'syn-r-range-journal'])
        self.assertIn(core.trip_card(journal, self.here(RANGE), core.RELATED_SIZES, ns='rf', summary=True), self.html(RANGE))
        self.assertEqual(cards[2].find('h3').find('a')['href'], '../../trips/syn-r-range-journal/')
        self.assertEqual(self.pick([dict(journal, featured=True), self.by['syn-r-flag']])[0]['slug'], 'syn-r-range-journal')
        # an unwritten journal is no candidate, like any unwritten report
        self.assertEqual(self.pick([self.by['syn-r-journal']]), [])

    # ------------------------------------------------------------ the section

    def test_the_section_follows_the_map_and_is_headed_featured(self):
        for name in PAGES:
            with self.subTest(region=name):
                sec = self.main(name).elements()[2]
                self.assertEqual((sec.tag, sec.classes, sec['aria-labelledby']), ('section', ['reg-feat', 'wrap', 'sec'], 'reg-feat-h'))
                self.assertIs(sec, self.section(name))
                self.assertEqual([(n.tag, n.classes) for n in sec.elements()][:2], [('div', ['shead']), ('ul', ['reg-cards', 'tgrid'])])
                h2 = self.one(name, 'reg-feat-h')
                self.assertEqual((h2.tag, h2.classes, h2.children), ('h2', ['shead-t'], ['Featured']))
                self.assertIn(core.section_head('Featured', id_='reg-feat-h') + '<ul class="reg-cards tgrid">', self.html(name))

    def test_the_cards_are_core_trip_cards_of_the_picks(self):
        for name, want in ((RANGE, ['syn-r-flag', 'syn-r-story', 'syn-r-old']), (COAST, ['syn-r-cove-a']), (PEAKS, PEAKS_PUB)):
            with self.subTest(region=name):
                ul = self.section(name).find('ul')
                cards = ul.elements()
                self.assertEqual([(li.tag, li.classes, li['data-slug']) for li in cards], [('li', ['tcard'], s) for s in want])
                html_ = ''.join(core.trip_card(self.by[s], self.here(name), core.RELATED_SIZES, ns='rf', summary=True) for s in want)
                self.assertIn('<ul class="reg-cards tgrid">%s</ul>' % html_, self.html(name))
                self.assertEqual([li.find('h3').find('a')['href'] for li in cards], ['../../trips/%s/' % s for s in want])
                self.assertEqual([li.find('p', cls='tcard-meta')['id'] for li in cards], ['rf-%s-m' % s for s in want])   # the 'rf' namespace
        # summary=True: a written report's card opens its write-up; the flagged track shows none
        cards = {li['data-slug']: li for li in self.section(RANGE).find_all('li', cls='tcard')}
        self.assertTrue(cards['syn-r-story'].find('p', cls='tcard-ex').text().startswith('Synthetic write-up for a region test'))
        self.assertIsNone(cards['syn-r-flag'].find('p', cls='tcard-ex'))
        # the cover is drawn at the related cards' sizes
        self.assertEqual(cards['syn-r-story'].find('img', cls='cover-img')['sizes'], core.RELATED_SIZES)

    def test_region_featured_writes_the_section(self):
        featured = need(self, self.region, 'featured')
        for name in PAGES:
            with self.subTest(region=name):
                html_ = featured(SLUG[name], self.here(name), self.pub(name), self.pick(self.group(name)))
                self.assertTrue(html_.startswith('<section class="reg-feat wrap sec" aria-labelledby="reg-feat-h">'))
                self.assertEqual(self.html(name).count(html_), 1)

    def test_without_a_candidate_the_whole_section_is_left_out(self):
        featured = need(self, self.region, 'featured')
        self.assertEqual(featured(SLUG[RANGE], self.here(RANGE), self.pub(RANGE), []), '')
        self.mk('syn-r-short-2', title='Synthetic Second Note', date='2024-07-02', region=RANGE, body=SHORT)
        self.use(mapped=[RANGE], only=['syn-r-lap', 'syn-r-photo', 'syn-r-short', 'syn-r-short-2', 'syn-r-undated'])
        self.assertEqual(self.pick(self.group(RANGE)), [])
        html_ = self.html(RANGE)
        for needle in ('reg-feat', 'reg-cards', 'Featured', 'reg-more', 'write-ups', 'writeup=1', 'tcard'):
            self.assertNotIn(needle, html_)
        self.assertEqual(sum(1 for t in self.pub(RANGE) if t['has_writeup']), 2)     # two write-ups, and still no link: no section
        self.assertEqual([h.text() for h in self.doc(RANGE).find_all('h2')], ['Map', 'All reports'])
        self.assertEqual([(n.tag, n.classes[0]) for n in self.main(RANGE).elements()],
                         [('section', 'reg-head'), ('section', 'arc-map'), ('section', 'arc-all'), ('p', 'reg-find')])

    # ------------------------------------------------------------ the write-ups link

    def test_from_two_write_ups_a_link_opens_them_in_the_explorer(self):
        for name, k in ((RANGE, 5), (PEAKS, 2)):
            with self.subTest(region=name):
                sec = self.section(name)
                p = sec.elements()[-1]
                self.assertEqual((p.tag, p.classes), ('p', ['reg-more', 'reg-x']))
                self.assertEqual(len(sec.elements()), 3)                         # the heading, the cards, the link
                (a,) = p.elements()
                self.assertEqual((a.tag, a.classes), ('a', ['alink']))
                self.assertEqual(a['href'], '../../trips/?region=%s&writeup=1' % SLUG[name])
                self.assertEqual(a.text(), 'All %d write-ups in Trips' % k)
                want = ('<p class="reg-more reg-x"><a class="alink" href="../../trips/?region=%s&amp;writeup=1">All %d write-ups in Trips%s</a></p>'
                        % (SLUG[name], k, icon('arrow-right', 16)))
                self.assertEqual(self.html(name).count(want), 1)
                self.assertIn('</ul>' + want + '</section>', self.html(name))
                self.assertNotIn('&writeup=1', self.html(name))                   # the ampersand is written as &amp;
                self.assertEqual(sum(1 for t in self.pub(name) if t['has_writeup']), k)
        self.assertEqual(len(self.doc(RANGE).find_all(cls='reg-more')), 1)

    def test_k_is_every_report_with_a_write_up_not_the_written_reports_alone(self):
        self.use(mapped=[RANGE], only=['syn-r-story', 'syn-r-short', 'syn-r-lap'])
        self.assertEqual([core.written_report(t) for t in self.pub(RANGE)], [True, False, False])
        self.assertEqual([t['has_writeup'] for t in self.pub(RANGE)], [True, True, False])
        self.assertEqual(self.section(RANGE).find('p', cls='reg-more').text(), 'All 2 write-ups in Trips')
        self.assertEqual(len(self.section(RANGE).find_all('li', cls='tcard')), 1)

    def test_with_one_write_up_or_none_there_is_no_such_link(self):
        featured = need(self, self.region, 'featured')
        self.assertEqual(sum(1 for t in self.pub(COAST) if t['has_writeup']), 1)
        self.assertIsNotNone(self.section(COAST))
        self.assertNotIn('reg-more', self.html(COAST))
        self.assertNotIn('writeup=1', self.html(COAST))
        self.assertNotIn('write-ups', self.html(COAST))
        self.assertEqual([n.tag for n in self.section(COAST).elements()], ['div', 'ul'])
        self.assertTrue(featured(SLUG[COAST], self.here(COAST), self.pub(COAST), self.pick(self.group(COAST))).endswith('</li></ul></section>'))
        # a Featured row without any write-up: the flagged track alone
        self.use(mapped=[RANGE], only=['syn-r-flag', 'syn-r-lap'])
        self.assertEqual([li['data-slug'] for li in self.section(RANGE).find_all('li', cls='tcard')], ['syn-r-flag'])
        self.assertNotIn('reg-more', self.html(RANGE))
        self.assertNotIn('write-ups', self.html(RANGE))

    def test_the_link_names_the_page_it_is_on_not_the_cards(self):
        featured = need(self, self.region, 'featured')
        html_ = featured('synthetic-slug', 'a/b/', self.pub(RANGE), self.trips('syn-r-flag'))
        self.assertIn('href="../../trips/?region=synthetic-slug&amp;writeup=1">All 5 write-ups in Trips<svg', html_)
        self.assertEqual(html_.count('<li class="tcard"'), 1)


# ---------------------------------------------------------------- section 3.4: All reports

class TableTests(RegionFixture):

    def section(self, name):
        return self.one(name, 'all-reports')

    def rows(self, name):
        return [a['data-key'] for a in self.section(name).find_all('a', cls='rtab-r')]

    def chips(self, node):
        return [(b['data-filter'], b.text()) for b in node.find_all('button', cls='fchip')]

    def test_the_table_is_the_map_pages_section_for_the_regions_trips(self):
        for name in PAGES:
            with self.subTest(region=name):
                want = self.archive.archive_section(self.site, self.here(name), published=self.pub(name), active=self.planned(name))
                self.assertEqual(self.html(name).count(want), 1)
                sec = self.section(name)
                self.assertEqual((sec.tag, sec.classes, sec['aria-labelledby']), ('section', ['arc-all', 'wrap', 'sec'], 'all-reports-h'))
                self.assertIs(sec.parent, self.main(name))
                self.assertEqual(self.one(name, 'all-reports-h').text(), 'All reports')
                self.assertEqual(self.one(name, 'all-reports-h').tag, 'h2')

    def test_only_the_regions_reports_are_listed(self):
        for name, want in ((RANGE, RANGE_PUB + ['syn-r-goal']), (COAST, COAST_PUB), (PEAKS, PEAKS_PUB)):
            with self.subTest(region=name):
                self.assertEqual(self.rows(name), want)
                self.assertEqual([a['href'] for a in self.section(name).find_all('a', cls='rtab-r')], ['../../trips/%s/' % s for s in want])
                # nothing of another region (the journal is the Trail's), no archived goal, nothing of a region without a page
                for other in ('syn-r-desert', 'syn-r-journal', 'syn-r-shelved', 'syn-r-plan'):
                    self.assertNotIn(other, self.html(name))
        self.assertNotIn('syn-r-cove-a', self.html(RANGE))
        self.assertNotIn('syn-r-story', self.section(COAST).text())

    def test_a_journal_and_a_report_without_a_track_are_rows_of_the_table(self):
        # REVISED in round 2: the table is every report filed under the region, as the list beside the map is
        helpers.make_series(self.trips_dir, slug='syn-r-range-journal', title='Synthetic Range Journal', region=RANGE)
        self.use()
        want = RANGE_PUB[:7] + ['syn-r-range-journal'] + RANGE_PUB[7:] + ['syn-r-goal']
        self.assertEqual(self.rows(RANGE), want)
        kinds = {a['data-key']: a['data-kind'] for a in self.section(RANGE).find_all('a', cls='rtab-r')}
        self.assertEqual((kinds['syn-r-range-journal'], kinds['syn-r-short'], kinds['syn-r-goal']), ('series', 'trip', 'planned'))
        self.assertFalse(core.has_track(self.by['syn-r-short']))
        self.assertEqual(ml_items(self.section(RANGE).find('div', cls='shead')),
                         ['12 REPORTS', 'INCL. 1 MULTI-DAY, 1 SERIES', '+ 1 PLANNED ROUTE'])
        # the journal's own region page (the Trail has no region map here) does not exist, and it is on no other page
        for name in (COAST, PEAKS):
            self.assertNotIn('syn-r-range-journal', self.html(name))

    def test_the_count_line_counts_the_region(self):
        want = {RANGE: ['11 REPORTS', 'INCL. 1 MULTI-DAY', '+ 1 PLANNED ROUTE'], COAST: ['3 REPORTS'], PEAKS: ['2 REPORTS']}
        for name in PAGES:
            self.assertEqual(ml_items(self.section(name).find('div', cls='shead')), want[name])

    def test_year_groups_the_planned_group_and_their_ids(self):
        sec = self.section(RANGE)
        ids = ['yr-2026', 'yr-2025', 'yr-2024', 'yr-2023', 'yr-2022', 'yr-undated', 'yr-planned']
        self.assertEqual([d['data-group'] for d in sec.find_all('div', cls='arc-yr')], ids)
        for gid, label in zip(ids, ['2026', '2025', '2024', '2023', '2022', 'Undated', 'Planned']):
            h3 = self.one(RANGE, gid)
            self.assertEqual((h3.tag, h3.text()), ('h3', label))
            self.assertEqual(h3.parent.parent.find('ol')['aria-labelledby'], gid)
        nav = sec.find('nav', cls='arc-years')
        self.assertEqual(nav['aria-label'], 'Jump to year')
        self.assertEqual([a['href'] for a in nav.find_all('a')], ['#' + i for i in ids])
        self.assertEqual([a.text() for a in nav.find_all('a')],
                         ['2026, 1 report', '2025, 3 reports', '2024, 3 reports', '2023, 2 reports', '2022, 1 report', 'Undated, 1 report', 'Planned'])
        # the Planned group is the region's active goals: not the archived one, not another region's
        planned = self.one(RANGE, 'yr-planned').parent.parent
        self.assertEqual([a['data-key'] for a in planned.find_all('a', cls='rtab-r')], ['syn-r-goal'])
        self.assertEqual([a['data-kind'] for a in planned.find_all('a', cls='rtab-r')], ['planned'])
        self.assertEqual(ml_items(planned.find('span', cls='arc-yr-n')), ['1 PLANNED ROUTE'])
        # a region without an active goal has no Planned group; one year alone has no year index
        for name in (COAST, PEAKS):
            self.assertNotIn('yr-planned', self.html(name))
        self.assertEqual([d['data-group'] for d in self.section(COAST).find_all('div', cls='arc-yr')], ['yr-2026'])
        self.assertIsNone(self.section(COAST).find('nav', cls='arc-years'))
        self.assertEqual([a['href'] for a in self.section(PEAKS).find('nav', cls='arc-years').find_all('a')], ['#yr-2025', '#yr-2024'])

    def test_the_live_region_and_the_table_head_are_there_on_every_page(self):
        for name in PAGES:
            with self.subTest(region=name):
                live = self.one(name, 'arc-live')
                self.assertEqual((live.tag, live.classes, live['aria-live'], live.children), ('p', ['sr'], 'polite', []))
                self.assertIn(self.section(name), ancestors(live))
                table = self.section(name).find('div', cls='arc-table')
                self.assertEqual(table.classes, ['rtab', 'arc-table'])
                self.assertEqual(table.elements()[0]['aria-hidden'], 'true')
                self.assertIn('<div class="rtab arc-table"><div aria-hidden="true">%s</div>' % core.table_head(), self.html(name))

    def test_there_is_a_chip_for_each_activity_the_region_has_and_no_other(self):
        bar = self.section(RANGE).find('div', cls='arc-filt')
        self.assertEqual((bar['role'], bar['aria-label'], 'hidden' in bar), ('radiogroup', 'Filter by activity', True))
        self.assertEqual(self.chips(bar), [('all', 'All'), ('ski', 'Backcountry Ski, 3 reports'), ('climb', 'Climbing, 1 report'),
                                           ('hike', 'Hiking, 4 reports'), ('mtb', 'Mountain Biking, 1 report'), ('other', 'Other, 2 reports')])
        self.assertEqual([b['aria-checked'] for b in bar.find_all('button')], ['true'] + ['false'] * 5)
        # two activities: the row is there, in the menu's order, and counts the region's reports only
        peaks = self.section(PEAKS).find('div', cls='arc-filt')
        self.assertEqual(self.chips(peaks), [('all', 'All'), ('climb', 'Climbing, 1 report'), ('mtb', 'Mountain Biking, 1 report')])
        # every chip filters something that is in the table
        for name in (RANGE, PEAKS):
            acts = {a['data-act'] for a in self.section(name).find_all('a', cls='rtab-r') if a['data-kind'] != 'planned'}
            self.assertEqual({f for f, _t in self.chips(self.section(name))} - {'all'}, acts)

    def test_a_region_of_one_activity_has_no_filter_row_at_all(self):
        self.assertEqual({t['activity'] for t in self.pub(COAST)}, {'hike'})
        self.assertIsNone(self.section(COAST).find('div', cls='arc-filt'))
        for needle in ('arc-filt', 'fchip', 'radiogroup" aria-label="Filter by activity"', 'data-filter="all"', 'data-filter="hike"'):
            self.assertNotIn(needle, inner(self.html(COAST), '<main id="main">', '</main>'))
        self.assertIn(core.section_head('All reports', self.archive.count_line(self.pub(COAST)), id_='all-reports-h')
                      + '<p class="sr" id="arc-live" aria-live="polite"></p>', self.html(COAST))

    def test_a_planned_route_of_another_activity_adds_no_chip(self):
        # chips count published reports: a ski goal in a region of hikes leaves it a region of one activity
        self.goal('syn-r-cove-goal', title='Synthetic Cove Goal', activity='ski', region=COAST)
        self.use()
        self.assertEqual(self.rows(COAST), COAST_PUB + ['syn-r-cove-goal'])
        self.assertIsNone(self.section(COAST).find('div', cls='arc-filt'))
        self.assertNotIn('fchip', inner(self.html(COAST), '<main id="main">', '</main>'))

    def test_the_way_into_the_explorer_follows_the_table(self):
        for name in PAGES:
            with self.subTest(region=name):
                kids = self.main(name).elements()
                p = kids[kids.index(self.section(name)) + 1]
                self.assertEqual((p.tag, p.classes), ('p', ['reg-find', 'reg-x', 'wrap']))
                (a,) = p.elements()
                self.assertEqual((a.tag, a.classes, a['href'], a.text()),
                                 ('a', ['alink'], '../../trips/?region=%s' % SLUG[name], 'Search and filter these in Trips'))
                want = ('</section><p class="reg-find reg-x wrap"><a class="alink" href="../../trips/?region=%s">Search and filter these in Trips%s</a></p>'
                        % (SLUG[name], icon('arrow-right', 16)))
                self.assertEqual(self.html(name).count(want), 1)
                self.assertEqual(len(self.doc(name).find_all(cls='reg-find')), 1)

    # ------------------------------------------------------------ archive.archive_section without the new keywords

    def test_the_unscoped_section_is_byte_for_byte_the_old_one(self):
        # compared with legacy_archive_section, the function body of commit fb425ab copied into this file
        for here in ('map/', '', 'regions/synthetic-range/'):
            with self.subTest(here=here):
                old = legacy_archive_section(self.archive, self.site, here)
                self.assertEqual(self.archive.archive_section(self.site, here), old)
                self.assertEqual(self.archive.archive_section(self.site, here, None, None), old)
                self.assertEqual(self.archive.archive_section(self.site, here, published=None, active=None), old)
        self.assertEqual(self.archive.build(self.site)[0].html.count(legacy_archive_section(self.archive, self.site, 'map/')), 1)
        # the whole site's table lists every report and every active goal, the journal and the other regions too
        keys = [a['data-key'] for a in Doc(self.archive.archive_section(self.site, 'map/')).find_all('a', cls='rtab-r')]
        self.assertEqual(keys, helpers.slugs(self.site['published']) + helpers.slugs(self.site['active_goals']))
        self.assertEqual(len(keys), 18 + 2)

    def test_the_unscoped_section_keeps_its_filter_row_for_a_site_of_one_activity(self):
        # 'no filter row with one activity' is a rule of the subset: the Map page of a site of hikes is what it was
        self.use(mapped=[COAST], only=COAST_PUB)
        old = legacy_archive_section(self.archive, self.site, 'map/')
        new = self.archive.archive_section(self.site, 'map/')
        self.assertEqual(new, old)
        self.assertEqual(self.chips(Doc(new)), [('all', 'All'), ('hike', 'Hiking, 3 reports')])
        scoped = self.archive.archive_section(self.site, 'map/', published=self.site['published'], active=[])
        self.assertNotIn('arc-filt', scoped)
        row = '<div class="arc-filt"' + inner(old, '<div class="arc-filt"', '</div>') + '</div>'
        self.assertEqual(scoped, old.replace(row, ''))                    # the same section without the row
        # a site with no report at all: the unscoped section still has its row with the All chip alone
        self.use(mapped=[], only=())
        self.assertEqual(self.archive.archive_section(self.site, 'map/'), legacy_archive_section(self.archive, self.site, 'map/'))
        self.assertEqual(self.chips(Doc(self.archive.archive_section(self.site, 'map/'))), [('all', 'All')])

    def test_the_scoped_section_differs_from_the_unscoped_one_only_in_what_it_lists(self):
        # the whole site passed as the subset is the Map page's section (it has several activities)
        scoped = self.archive.archive_section(self.site, 'map/', published=self.site['published'], active=self.site['active_goals'])
        self.assertEqual(scoped, self.archive.archive_section(self.site, 'map/'))
        # lists are read, not kept: tuples and generators of the same trips give the same section
        pub, planned = self.pub(RANGE), self.planned(RANGE)
        want = self.archive.archive_section(self.site, 'x/', published=pub, active=planned)
        self.assertEqual(self.archive.archive_section(self.site, 'x/', published=tuple(pub), active=tuple(planned)), want)
        self.assertEqual((helpers.slugs(pub), helpers.slugs(planned)), (RANGE_PUB, ['syn-r-goal']))
        # an empty list of goals is 'no Planned group', not 'the site's goals'
        none = self.archive.archive_section(self.site, 'x/', published=pub, active=[])
        self.assertNotIn('yr-planned', none)
        self.assertNotIn('PLANNED', none)


# ---------------------------------------------------------------- section 3.5: other regions

class OthersTests(RegionFixture):

    def nav(self, name):
        return self.main(name).find('nav', cls='reg-others')

    def links(self, name):
        return [(a['href'], a.text()) for a in self.nav(name).find_all('a')]

    def test_the_nav_is_the_last_block_and_is_labelled_other_regions(self):
        for name in PAGES:
            with self.subTest(region=name):
                nav = self.main(name).elements()[-1]
                self.assertIs(nav, self.nav(name))
                self.assertEqual((nav.tag, nav.classes, nav['aria-labelledby']), ('nav', ['reg-others', 'wrap', 'sec'], 'reg-others-l'))
                label = self.one(name, 'reg-others-l')
                self.assertEqual((label.tag, label.classes, label.children), ('span', ['t-label'], ['Other regions']))
                # the browse-row markup of the Trips page: div.trx-browse > div.trx-bgroup > span.t-label + ul > li > a
                (browse,) = nav.elements()
                self.assertEqual((browse.tag, browse.classes), ('div', ['trx-browse']))
                (group,) = browse.elements()
                self.assertEqual((group.tag, group.classes), ('div', ['trx-bgroup']))
                self.assertEqual([n.tag for n in group.elements()], ['span', 'ul'])
                self.assertIs(group.elements()[0], label)
                for li in group.elements()[1].elements():
                    self.assertEqual((li.tag, [n.tag for n in li.elements()]), ('li', ['a']))

    def test_one_link_per_other_region_page_in_the_map_pages_order_then_the_map(self):
        self.assertEqual(self.links(RANGE), [('../../regions/synthetic-coast/', 'Synthetic Coast, 3 reports'),
                                             ('../../regions/synthetic-obrien-peaks/', "Synthetic O'Brien & <Peaks>, 2 reports"),
                                             ('../../map/', 'Map & archive')])
        self.assertEqual(self.links(COAST), [('../../regions/synthetic-range/', 'Synthetic Range, 11 reports'),
                                             ('../../regions/synthetic-obrien-peaks/', "Synthetic O'Brien & <Peaks>, 2 reports"),
                                             ('../../map/', 'Map & archive')])
        self.assertEqual(self.links(PEAKS), [('../../regions/synthetic-range/', 'Synthetic Range, 11 reports'),
                                             ('../../regions/synthetic-coast/', 'Synthetic Coast, 3 reports'),
                                             ('../../map/', 'Map & archive')])
        for name in PAGES:
            # never the page itself, never a region without a page
            self.assertNotIn('../../' + self.here(name), [h for h, _t in self.links(name)])
            self.assertNotIn(SLUG[PLANS], self.nav(name).text() + ''.join(h for h, _t in self.links(name)))
            self.assertNotIn('Synthetic Plans', self.nav(name).text())
            self.assertNotIn('Synthetic Desert', self.nav(name).text())

    def test_a_count_is_the_published_reports_written_as_the_map_pages_counts(self):
        a = self.nav(COAST).find_all('a')[0]
        self.assertEqual(a.children[0], 'Synthetic Range')
        bn = a.elements()[0]
        self.assertEqual((bn.tag, bn.classes), ('span', ['trx-bn']))
        self.assertEqual(len(self.group(RANGE)), 12)                              # 11 reports and a goal: the count says 11
        self.assertIn('<li><a href="../../regions/synthetic-range/">Synthetic Range<span class="trx-bn">%s</span></a></li>'
                      % self.archive.count_n(11), self.html(COAST))
        self.assertEqual(self.archive.count_n(11), '<span class="sr">, </span>11<span class="sr"> reports</span>')
        # what is on the screen is the number; a screen reader hears ', 11 reports'
        self.assertEqual([c for c in bn.children if isinstance(c, str)], ['11'])
        self.assertEqual([s.classes for s in bn.elements()], [['sr'], ['sr']])
        # the map link carries no count
        last = self.nav(COAST).find_all('a')[-1]
        self.assertEqual((last.children, last.elements()), (['Map & archive'], []))
        self.assertIn('<li><a href="../../map/">Map &amp; archive</a></li></ul>', self.html(COAST))

    def test_one_report_is_spoken_as_one_report(self):
        self.use(only=RANGE_PUB + ['syn-r-cove-a'])
        self.assertEqual(self.links(RANGE), [('../../regions/synthetic-coast/', 'Synthetic Coast, 1 report'), ('../../map/', 'Map & archive')])

    def test_region_others_writes_the_nav(self):
        others = need(self, self.region, 'others')
        for name in PAGES:
            html_ = others(SLUG[name], self.here(name), self.regs)
            self.assertTrue(html_.startswith('<nav class="reg-others wrap sec" aria-labelledby="reg-others-l"><div class="trx-browse">'))
            self.assertTrue(self.html(name).endswith(html_ + '</main>' + self.html(name).split('</main>', 1)[1]))
        # links are relative to the page, and the page is left out by its slug
        html_ = others(SLUG[COAST], 'a/', self.regs)
        self.assertEqual([a['href'] for a in Doc(html_).find_all('a')], ['../regions/synthetic-range/', '../regions/synthetic-obrien-peaks/', '../map/'])
        self.assertEqual(len(Doc(others('synthetic-nowhere', 'a/', self.regs)).find_all('a')), 4)

    def test_without_another_region_page_there_is_no_nav(self):
        others = need(self, self.region, 'others')
        self.assertEqual(others(SLUG[RANGE], self.here(RANGE), self.regs[:1]), '')
        self.assertEqual(others(SLUG[RANGE], self.here(RANGE), []), '')
        # one region page on the site (the other mapped region has planned routes only)
        self.use(mapped=[RANGE, PLANS])
        self.assertEqual(names(self.regs), [RANGE])
        self.assertIsNone(self.nav(RANGE))
        for needle in ('reg-others', 'Other regions', 'trx-browse', 'trx-bgroup'):
            self.assertNotIn(needle, self.html(RANGE))
        self.assertEqual(self.main(RANGE).elements()[-1].classes, ['reg-find', 'reg-x', 'wrap'])
        self.assertTrue(inner(self.html(RANGE), '<main id="main">', '</main>').endswith('</a></p>'))


# ---------------------------------------------------------------- the description, the share image, the document

class DescriptionTests(RegionFixture):

    def setUp(self):
        super().setUp()
        self.description = need(self, self.region, 'description')
        self.words = need(self, self.region, 'activity_words')

    def test_the_sentence_of_each_fixture_page(self):
        # REVISED in round 2: every sentence ends with the map of the region; the GPX clause follows only when every
        # report has a track (the Range has one without)
        self.assertEqual(self.description(RANGE, self.pub(RANGE)),
                         'Synthetic Range: 11 trip reports, 2022 to 2026 (backcountry ski, climbing, hiking, mountain biking, '
                         'paddleboarding and rafting), with a map of the region.')
        self.assertEqual(self.description(COAST, self.pub(COAST)),
                         'Synthetic Coast: 3 trip reports, 2026 (hiking), with a map of the region and the full GPX track of each.')
        self.assertEqual(self.description(PEAKS, self.pub(PEAKS)),
                         "Synthetic O'Brien & <Peaks>: 2 trip reports, 2024 to 2025 (climbing and mountain biking), with a map of the "
                         'region and the full GPX track of each.')

    def test_it_starts_with_the_region_as_written(self):
        # the region leads, a colon follows; nothing is escaped here (core.document escapes the attribute once)
        for name in (RANGE, PEAKS, 'Synthétique Côte'):
            self.assertTrue(self.description(name, self.pub(COAST)).startswith(name + ': 3 trip reports, '))

    def test_one_report_is_singular(self):
        # '1 trip report' and 'its full GPX track'; from two on 'N trip reports' and 'the full GPX track of each'
        self.assertEqual(self.description(COAST, self.trips('syn-r-cove-b')),
                         'Synthetic Coast: 1 trip report, 2026 (hiking), with a map of the region and its full GPX track.')
        self.assertEqual(self.description(COAST, self.trips('syn-r-cove-b', 'syn-r-cove-c')),
                         'Synthetic Coast: 2 trip reports, 2026 (hiking), with a map of the region and the full GPX track of each.')

    def test_the_three_endings_singular_and_plural(self):
        d = self.description
        lap, raft, short, undated = self.trips('syn-r-lap', 'syn-r-raft', 'syn-r-short', 'syn-r-undated')
        self.assertEqual([core.has_track(t) for t in (lap, raft, short, undated)], [True, True, False, True])
        each, its, bare = (', with a map of the region and the full GPX track of each.', ', with a map of the region and its full GPX track.',
                           ', with a map of the region.')
        cases = (([lap], '1 trip report', its),                       # one report, with a track
                 ([lap, raft], '2 trip reports', each),               # several, each with a track
                 ([lap, raft, undated], '3 trip reports', each),
                 ([short], '1 trip report', bare),                    # one report, without a track: the map alone
                 ([lap, short], '2 trip reports', bare),              # several, one of them without: no promise for any
                 ([short, lap, raft], '3 trip reports', bare))
        for pub, count, ending in cases:
            with self.subTest(pub=helpers.slugs(pub)):
                text = d(RANGE, pub)
                self.assertTrue(text.startswith('Synthetic Range: %s, ' % count) or text.startswith('Synthetic Range: %s (' % count), text)
                self.assertTrue(text.endswith(')' + ending), text)
                self.assertEqual(text.count('with a map of the region'), 1)
                self.assertEqual(text.count('GPX'), 0 if ending == bare else 1)
                # the two GPX wordings never stand in for each other
                self.assertEqual('of each' in text, ending == each)
                self.assertEqual(' its ' in text, ending == its)
        self.assertEqual(d(RANGE, [lap]), 'Synthetic Range: 1 trip report, 2023 (backcountry ski), with a map of the region and its full GPX track.')
        self.assertEqual(d(RANGE, [short]), 'Synthetic Range: 1 trip report, 2024 (hiking), with a map of the region.')
        self.assertEqual(d(RANGE, [lap, short]), 'Synthetic Range: 2 trip reports, 2023 to 2024 (backcountry ski and hiking), with a map of the region.')
        # a list without a report promises no track either (a page always has one: core.region_pages)
        self.assertEqual(d(RANGE, []), 'Synthetic Range: 0 trip reports, with a map of the region.')

    def test_it_never_says_the_reports_are_on_the_map(self):
        # the map shows what it was last drawn with, which may be fewer reports than the page lists: the sentence says
        # the page has a map of the region and makes no claim about what is on it (the first round said 'on one map')
        for name in PAGES:
            for pub in (self.pub(name), self.pub(name)[:1]):
                text = self.description(name, pub)
                for claim in ('on one map', 'on the map', 'on a map', 'all on', 'every report', 'each with', 'mapped'):
                    self.assertNotIn(claim, text)
                self.assertIn(', with a map of the region', text)

    def test_the_years(self):
        d = self.description
        self.assertIn(', 2026 (', d(RANGE, self.trips('syn-r-story')))                                  # one year
        self.assertIn(', 2022 to 2026 (', d(RANGE, self.trips('syn-r-story', 'syn-r-old')))             # a span, in words
        self.assertIn(', 2022 to 2026 (', d(RANGE, self.trips('syn-r-old', 'syn-r-lap', 'syn-r-story')))
        self.assertIn(', 2023 (', d(RANGE, self.trips('syn-r-raft', 'syn-r-lap', 'syn-r-undated')))     # an undated report has no year
        for text in (d(RANGE, self.pub(RANGE)), d(COAST, self.pub(COAST))):
            self.assertNotIn('–', text)                                                            # no dash in a sentence
            self.assertNotRegex(text, r'\d-\d')
        # nothing dated: the years are left out, and nothing stands in their place
        self.assertEqual(d(RANGE, self.trips('syn-r-undated')), 'Synthetic Range: 1 trip report (hiking), with a map of the region and its full GPX track.')

    def test_the_years_count_the_year_a_trip_ended_in(self):
        self.mk('syn-r-nye', title='Synthetic New Year Tour', activity='ski', kind='multi-day', date='2019-12-30', end_date='2020-01-02',
                region=RANGE, days=[{'title': 'Synthetic Day One', 'date': '2019-12-30'}, {'title': 'Synthetic Day Two', 'date': '2020-01-02'}])
        self.use()
        self.assertEqual(self.description(RANGE, self.trips('syn-r-nye')),
                         'Synthetic Range: 1 trip report, 2019 to 2020 (backcountry ski), with a map of the region and its full GPX track.')

    def test_the_activities_are_in_the_menus_order_lower_case_in_brackets(self):
        self.assertEqual([a for a, _lab in core.NAV], ['ski', 'climb', 'hike', 'mtb', 'other'])
        # whatever the order of the reports
        self.assertEqual(self.words(self.trips('syn-r-photo', 'syn-r-story', 'syn-r-words', 'syn-r-lap')),
                         ['backcountry ski', 'climbing', 'hiking', 'mountain biking'])
        self.assertEqual(self.words(self.trips('syn-r-story', 'syn-r-old', 'syn-r-undated')), ['hiking'])                # each once
        self.assertEqual(self.words([]), [])
        d = self.description
        self.assertIn(' (hiking), ', d(RANGE, self.trips('syn-r-story')))
        self.assertIn(' (backcountry ski and hiking), ', d(RANGE, self.trips('syn-r-story', 'syn-r-lap')))
        self.assertIn(' (backcountry ski, climbing and hiking), ', d(RANGE, self.trips('syn-r-story', 'syn-r-lap', 'syn-r-words')))
        self.assertIn(' (backcountry ski, climbing, hiking and mountain biking), ',
                      d(RANGE, self.trips('syn-r-photo', 'syn-r-story', 'syn-r-lap', 'syn-r-words')))
        for text in (d(RANGE, self.pub(RANGE)), d(PEAKS, self.pub(PEAKS))):
            words = inner(text, '(', ')')
            self.assertEqual(words, words.lower())
            self.assertNotIn(', and', text)                                    # no comma before the final 'and'
            self.assertNotIn(' or ', text)

    def test_other_is_named_by_the_sub_types_its_reports_have(self):
        self.assertEqual((core.SUB_WORD['SUP'], core.SUB_WORD['Rafting']), ('Paddleboarding', 'Rafting'))
        self.assertEqual(self.words(self.trips('syn-r-paddle')), ['paddleboarding'])
        self.assertEqual(self.words(self.trips('syn-r-raft')), ['rafting'])
        # each sub-type is a word of its own, once, after the four named activities; the word 'other' is not there
        self.assertEqual(self.words(self.trips('syn-r-paddle', 'syn-r-raft', 'syn-r-paddle', 'syn-r-story')), ['hiking', 'paddleboarding', 'rafting'])
        self.assertEqual(sorted(self.words(self.trips('syn-r-raft', 'syn-r-paddle'))), ['paddleboarding', 'rafting'])
        self.assertIn(' (hiking, paddleboarding and rafting), ', self.description(RANGE, self.trips('syn-r-paddle', 'syn-r-raft', 'syn-r-story')))
        self.assertNotIn('other', self.description(RANGE, self.pub(RANGE)))
        for sub, word in sorted(core.SUB_WORD.items()):
            self.assertEqual(self.words([dict(self.by['syn-r-paddle'], subtype=sub)]), [word.lower()])

    def test_the_sub_types_are_named_in_the_order_the_reports_name_them(self):
        # the contract does not fix an order among the sub-types; the function names them as the list meets them,
        # which on a page is newest first
        self.assertEqual(self.words(self.trips('syn-r-raft', 'syn-r-paddle')), ['rafting', 'paddleboarding'])
        self.assertEqual(self.words(self.trips('syn-r-paddle', 'syn-r-raft')), ['paddleboarding', 'rafting'])

    def test_other_without_a_sub_type_is_other(self):
        self.mk('syn-r-misc', title='Synthetic Misc', activity='other', date='2021-06-06', region=RANGE)
        self.use()
        misc = self.by['syn-r-misc']
        self.assertIsNone(misc['subtype'])
        self.assertEqual(self.words([misc]), ['other'])
        self.assertEqual(self.description(RANGE, [misc]), 'Synthetic Range: 1 trip report, 2021 (other), with a map of the region and its full GPX track.')
        self.assertEqual(self.words([misc, self.by['syn-r-story']]), ['hiking', 'other'])
        # as soon as one names a sub-type, the sub-types are the words
        self.assertEqual(self.words([misc, self.by['syn-r-raft']]), ['rafting'])

    def test_the_track_promise_is_made_only_when_every_report_has_a_track(self):
        with_track, with_one, without = (', with a map of the region and the full GPX track of each.',
                                         ', with a map of the region and its full GPX track.', ', with a map of the region.')
        self.assertFalse(core.has_track(self.by['syn-r-short']))
        d = self.description
        self.assertTrue(d(RANGE, self.trips('syn-r-story', 'syn-r-lap')).endswith(with_track))
        self.assertTrue(d(RANGE, self.trips('syn-r-story', 'syn-r-short', 'syn-r-lap')).endswith(')' + without))
        self.assertTrue(d(RANGE, self.trips('syn-r-short')).endswith(')' + without))
        self.assertNotIn('GPX', d(RANGE, self.trips('syn-r-short', 'syn-r-story')))
        self.assertNotIn('GPX', d(RANGE, self.trips('syn-r-story', 'syn-r-short')))          # wherever it is in the list
        self.assertNotIn('GPX', d(RANGE, self.pub(RANGE)))
        # a multi-day trip has a track when a day has one (core.has_track), though it has no track.gpx of its own
        tour = self.by['syn-r-tour']
        self.assertEqual((bool(tour['track']), core.has_track(tour)), (False, True))
        self.assertTrue(d(RANGE, [tour]).endswith(with_one))
        self.assertTrue(d(RANGE, self.trips('syn-r-tour', 'syn-r-story')).endswith(with_track))
        # the rule is core.has_track, whatever it says
        with mock.patch.object(core, 'has_track', lambda t: False):
            self.assertTrue(d(COAST, self.pub(COAST)).endswith(')' + without))
        with mock.patch.object(core, 'has_track', lambda t: True):
            self.assertTrue(d(RANGE, self.pub(RANGE)).endswith(with_track))

    def test_nothing_but_counts_and_fields(self):
        # one sentence, no adjective: the words are the region, the numbers, the activities and the fixed endings
        for name in PAGES:
            text = self.description(name, self.pub(name))
            self.assertEqual(text.count('.'), 1)
            self.assertTrue(text.endswith('.'))
            rest = text[len(name):]
            rest = re.sub(r'\(.*\)', '()', rest)
            self.assertRegex(rest, r'^: \d+ trip reports?(, \d{4}( to \d{4})?)? \(\), with a map of the region( and (the full GPX track of each|its full GPX track))?\.$')


class ShareImageTests(RegionFixture):

    def setUp(self):
        super().setUp()
        self.share_image = need(self, self.region, 'share_image')

    def og(self, name):
        return [m['content'] for m in self.doc(name).find('head').find_all('meta', attrs={'property': 'og:image'})]

    def test_the_first_featured_card_that_has_a_cover(self):
        feat = self.region.pick_featured(self.group(RANGE))
        self.assertEqual([bool(t['cover']) for t in feat], [False, True, True])       # the flagged track leads and has no photo
        self.assertEqual(self.share_image(feat, self.pub(RANGE)), core.share_photo(self.by['syn-r-story']))
        self.assertEqual(self.share_image(feat, self.pub(RANGE)),
                         {'path': 'trips/syn-r-story/photos/02.webp', 'w': 1600, 'h': 1200, 'alt': COVER_ALT})
        # a Featured card's cover wins over a newer report's that is not a card
        old, photo_ = self.by['syn-r-old'], self.by['syn-r-photo']
        self.assertEqual(self.share_image([old], [photo_, old]), core.share_photo(old))
        self.assertEqual(self.share_image([old, self.by['syn-r-story']], self.pub(RANGE)), core.share_photo(old))

    def test_else_the_first_report_that_has_a_cover(self):
        photo_, old, words, lap = self.trips('syn-r-photo', 'syn-r-old', 'syn-r-words', 'syn-r-lap')
        self.assertEqual(self.share_image([words], [words, photo_, lap, old]), core.share_photo(photo_))   # no card has a photo
        self.assertEqual(self.share_image([], [lap, photo_, old]), core.share_photo(photo_))               # no card at all
        self.assertEqual(self.share_image([], [lap, old, photo_]), core.share_photo(old))                  # first in the list

    def test_else_the_sites_share_image(self):
        words, lap = self.trips('syn-r-words', 'syn-r-lap')
        self.assertIsNone(core.site_share())
        self.assertIsNone(self.share_image([words], [words, lap]))
        self.assertIsNone(self.share_image([], []))
        self.use(featured=('syn-r-cove-a',))
        words, lap = self.trips('syn-r-words', 'syn-r-lap')
        self.assertEqual(self.share_image([words], [words, lap]), core.site_share())
        self.assertEqual(self.share_image([], []), core.share_photo(self.by['syn-r-cove-a']))
        # ... which never replaces a photo the region has
        self.assertEqual(self.share_image([words], [words, self.by['syn-r-old']]), core.share_photo(self.by['syn-r-old']))

    def test_the_pages_share_what_share_image_says(self):
        self.assertEqual(self.og(RANGE), [core.SITE_URL + 'trips/syn-r-story/photos/02.webp'])
        self.assertEqual(self.og(COAST), [core.SITE_URL + 'trips/syn-r-cove-a/photos/01.webp'])
        self.assertEqual(self.og(PEAKS), [])                                      # no photo in the region, nothing featured on the site
        self.assertIn('<meta name="twitter:card" content="summary">', self.html(PEAKS))
        self.assertIn(core._share_tags(core.share_photo(self.by['syn-r-story'])), self.html(RANGE).split('</head>', 1)[0])
        # with a featured trip on the site, the region without a photo shares the site's image and the others keep theirs
        self.use(featured=('syn-r-old',))
        self.assertEqual(self.og(PEAKS), [core.SITE_URL + 'trips/syn-r-old/photos/01.webp'])
        self.assertEqual(self.og(RANGE), [core.SITE_URL + 'trips/syn-r-story/photos/02.webp'])
        self.assertEqual(self.og(COAST), [core.SITE_URL + 'trips/syn-r-cove-a/photos/01.webp'])

    def test_a_region_whose_only_photo_is_on_an_unwritten_report_shares_it(self):
        self.use(mapped=[RANGE], only=['syn-r-words', 'syn-r-photo', 'syn-r-lap'], featured=())
        self.assertEqual(helpers.slugs(self.region.pick_featured(self.group(RANGE))), ['syn-r-words'])
        self.assertEqual(self.og(RANGE), [core.SITE_URL + 'trips/syn-r-photo/photos/01.webp'])


class DocumentTests(RegionFixture):

    def head(self, name):
        return self.doc(name).find('head')

    def meta_tag(self, region, attr, value):
        hits = self.head(region).find_all('meta', attrs={attr: value})
        self.assertEqual(len(hits), 1, '%d meta tags with %s="%s"' % (len(hits), attr, value))
        return hits[0]['content']

    def test_build_returns_one_page_per_region_in_the_map_pages_order(self):
        self.assertEqual([p.url for p in self.built], ['regions/synthetic-range/', 'regions/synthetic-coast/', 'regions/synthetic-obrien-peaks/'])
        for p, name in zip(self.built, PAGES):
            self.assertIsInstance(p, core.Page)
            self.assertEqual(p.title, name + ' trip reports')
            self.assertIs(p.index, True)                                          # listed in sitemap.xml
            self.assertTrue(p.html.startswith('<!doctype html>\n<html lang="en">'))
        # no regions/ index page, no page for a region without a map or without a report
        urls = [p.url for p in self.built]
        self.assertNotIn('regions/', urls)
        for name in (PLANS, DESERT, TRAIL):
            self.assertNotIn('regions/%s/' % SLUG[name], urls)

    def test_build_is_page_for_each_of_region_regions(self):
        page = need(self, self.region, 'page')
        regs = self.region.regions(self.site, self.meta)
        for (name, slug, ts), built in zip(regs, self.built):
            with self.subTest(region=name):
                one = page(name, slug, ts, self.site, self.meta, regs)
                self.assertEqual((one.url, one.title, one.index, one.html), (built.url, built.title, built.index, built.html))
        # build() reads the meta from the archive module, as the Map page does
        with mock.patch.object(self.archive, 'site_meta', lambda: dict(self.meta, regions=[COAST])):
            self.assertEqual([p.url for p in self.region.build(self.site)], ['regions/synthetic-coast/'])
        with mock.patch.object(self.archive, 'site_meta', lambda: {'maps': {}, 'regions': []}):
            self.assertEqual(self.region.build(self.site), [])

    def test_title_and_description(self):
        for name in PAGES:
            with self.subTest(region=name):
                title = '%s trip reports · Eric Sichak' % name
                self.assertEqual([t.text(clean=False) for t in self.head(name).find_all('title')], [title])
                self.assertEqual(self.meta_tag(name, 'property', 'og:title'), title)
                desc = self.region.description(name, self.pub(name))
                self.assertEqual(self.meta_tag(name, 'name', 'description'), desc)
                self.assertEqual(self.meta_tag(name, 'property', 'og:description'), desc)
        self.assertIn('<title>Synthetic O&#x27;Brien &amp; &lt;Peaks&gt; trip reports · Eric Sichak</title>', self.html(PEAKS))
        self.assertIn('<meta name="description" content="Synthetic O&#x27;Brien &amp; &lt;Peaks&gt;: 2 trip reports, ', self.html(PEAKS))
        self.assertNotIn('&amp;amp;', self.html(PEAKS))

    def test_canonical_and_open_graph(self):
        for name in PAGES:
            with self.subTest(region=name):
                url = core.SITE_URL + 'regions/%s/' % SLUG[name]
                self.assertEqual([ln['href'] for ln in self.head(name).find_all('link', attrs={'rel': 'canonical'})], [url])
                self.assertEqual(self.meta_tag(name, 'property', 'og:url'), url)
                self.assertEqual(self.meta_tag(name, 'property', 'og:type'), 'website')
                self.assertEqual(self.head(name).find_all('meta', attrs={'name': 'robots'}), [])       # indexed

    def test_no_structured_data_and_no_article_dates(self):
        for name in PAGES:
            self.assertEqual(self.doc(name).find_all('script', attrs={'type': 'application/ld+json'}), [])
            self.assertNotIn('ld+json', self.html(name))
            self.assertNotIn('article:', self.html(name))
            self.assertNotIn('schema.org', self.html(name))

    def test_the_body_class_is_p_region(self):
        for name in PAGES:
            self.assertEqual(self.doc(name).find('body')['class'], 'p-region')
        self.assertEqual(Doc(self.archive.build(self.site)[0].html).find('body')['class'], 'p-archive')

    def test_the_header_marks_map_as_the_section_the_page_is_in(self):
        for name in PAGES:
            with self.subTest(region=name):
                header = self.doc(name).find('header', cls='site-h')
                nav = header.find('nav', attrs={'aria-label': 'Main'})
                self.assertEqual([(a.text(), a['href'], a['aria-current']) for a in nav.find_all('a') if 'nav-search' not in a.classes],
                                 [('Trips', '../../trips/', None), ('Tick list', '../../tick-list/', None), ('Map', '../../map/', 'true'),
                                  ('About', '../../about/', None)])
                # the phone menu's row as well, and nothing else in the header: 'true', since the link is not this page
                marked = [(a['href'], a['aria-current']) for a in header.find_all('a') if a['aria-current']]
                self.assertEqual(marked, [('../../map/', 'true'), ('../../map/', 'true')])
                # the one aria-current="page" of the document is the breadcrumb's last item
                page = [n for n in self.doc(name).root.walk() if n['aria-current'] == 'page']
                self.assertEqual([(n.tag, n.text()) for n in page], [('span', name)])

    def test_the_first_screen_map_is_preloaded(self):
        for name in PAGES:
            with self.subTest(region=name):
                slug = SLUG[name]
                here = self.here(name)
                want = core.map_preloads(None, here, [('region-%s-desktop' % slug, 'desktop'), ('region-%s-phone' % slug, 'phone')],
                                         'assets/maps/', site_maps=True)
                self.assertTrue(want)
                self.assertIn(want + '</head>', self.html(name))
                links = self.head(name).find_all('link', attrs={'rel': 'preload'})
                self.assertEqual([(ln['href'], ln['media'], ln['as'], ln['fetchpriority']) for ln in links],
                                 [('../../assets/maps/region-%s-desktop.webp' % slug, '(min-width: 560px)', 'image', 'high'),
                                  ('../../assets/maps/region-%s-desktop.base.svg' % slug, '(min-width: 560px)', 'image', 'high'),
                                  ('../../assets/maps/region-%s-phone.webp' % slug, '(max-width: 559.98px)', 'image', 'high'),
                                  ('../../assets/maps/region-%s-phone.base.svg' % slug, '(max-width: 559.98px)', 'image', 'high')])
                # every preloaded file is one the map block draws
                srcs = [i['src'] for i in self.one(name, 'arc-map-' + slug).find_all('img')]
                self.assertEqual([ln['href'] for ln in links], srcs)

    def test_the_page_carries_no_other_regions_map(self):
        for name in PAGES:
            for other in PAGES:
                if other != name:
                    self.assertNotIn('region-%s-desktop' % SLUG[other], self.html(name))


# ---------------------------------------------------------------- the page as a whole

def headings(doc):
    return [(int(n.tag[1]), n.text()) for n in doc.find('body').walk() if re.fullmatch(r'h[1-6]', n.tag)]


class PageTests(RegionFixture):

    def test_the_body_is_the_six_blocks_in_order(self):
        r = self.region
        for name in PAGES:
            with self.subTest(region=name):
                here, slug, ts = self.here(name), SLUG[name], self.group(name)
                pub, planned = self.pub(name), self.planned(name)
                body = (r.head(name, here, pub, planned)
                        + '<section class="arc-map reg-map wrap" aria-labelledby="reg-map-h"><h2 class="sr" id="reg-map-h">Map</h2>%s</section>'
                        % self.archive.region_panel(name, slug, ts, here, self.meta, True, page=True)
                        + r.featured(slug, here, pub, r.pick_featured(ts))
                        + self.archive.archive_section(self.site, here, published=pub, active=planned)
                        + '<p class="reg-find reg-x wrap"><a class="alink" href="../../trips/?region=%s">Search and filter these in Trips%s</a></p>'
                        % (slug, icon('arrow-right', 16))
                        + r.others(slug, here, self.regs))
                self.assertEqual(inner(self.html(name), '<main id="main">', '</main>'), body)
        self.assertEqual([(n.tag, n.classes[0]) for n in self.main(RANGE).elements()],
                         [('section', 'reg-head'), ('section', 'arc-map'), ('section', 'reg-feat'), ('section', 'arc-all'),
                          ('p', 'reg-find'), ('nav', 'reg-others')])

    def test_exactly_one_h1(self):
        for name in PAGES:
            h1 = self.doc(name).find_all('h1')
            self.assertEqual([h.text() for h in h1], [name])
            self.assertIn(self.main(name), ancestors(h1[0]))
            self.assertEqual(self.html(name).count('<h1'), 1)

    def test_heading_levels_never_skip(self):
        for name in PAGES:
            with self.subTest(region=name):
                found = headings(self.doc(name))
                self.assertEqual(found[0], (1, name))
                for (prev, _a), (level, text) in zip(found, found[1:]):
                    self.assertLessEqual(level, prev + 1, 'h%d "%s" follows an h%d' % (level, text, prev))
        self.assertEqual(headings(self.doc(RANGE)),
                         [(1, 'Synthetic Range'), (2, 'Map'), (3, 'In this region'), (2, 'Featured'), (3, 'Synthetic Flagged Lap'), (3, 'Synthetic Story'),
                          (3, 'Synthetic Old Story'), (2, 'All reports'), (3, '2026'), (3, '2025'), (3, '2024'), (3, '2023'), (3, '2022'),
                          (3, 'Undated'), (3, 'Planned')])
        self.assertEqual(headings(self.doc(COAST)),
                         [(1, 'Synthetic Coast'), (2, 'Map'), (3, 'In this region'), (2, 'Featured'), (3, 'Synthetic Cove A'), (2, 'All reports'), (3, '2026')])
        # the list's heading is an h3 directly under the map section's h2 (an h4 there, as on the Map page, would skip a level)
        for name in PAGES:
            self.assertEqual(self.doc(name).find_all('h4'), [])

    def test_heading_levels_never_skip_without_a_featured_row(self):
        self.use(mapped=[RANGE], only=['syn-r-lap', 'syn-r-raft'])
        self.assertEqual(headings(self.doc(RANGE)), [(1, 'Synthetic Range'), (2, 'Map'), (3, 'In this region'), (2, 'All reports'), (3, '2023')])

    def test_every_id_is_unique_and_every_reference_lands(self):
        for name in PAGES:
            with self.subTest(region=name):
                doc = self.doc(name)
                ids = [n['id'] for n in doc.root.walk() if n['id']]
                self.assertEqual(sorted(ids), sorted(set(ids)))
                for want in ('main', 'reg-title', 'reg-map-h', 'map', 'arc-map-' + SLUG[name], 'arc-in-' + SLUG[name], 'arc-rows-' + SLUG[name],
                             'reg-feat-h', 'all-reports', 'all-reports-h', 'arc-live', 'reg-others-l'):
                    self.assertIn(want, ids)
                frags = [a['href'][1:] for a in doc.find_all('a') if (a['href'] or '').startswith('#')]
                self.assertIn('main', frags)
                for f in frags:
                    self.assertIn(f, ids, 'a link to #%s lands nowhere' % f)
                for attr in ('aria-labelledby', 'aria-controls', 'aria-describedby', 'data-map-target'):
                    for n in doc.root.walk():
                        for ref in (n[attr] or '').split():
                            self.assertIn(ref, ids, '%s="%s" names no element' % (attr, n[attr]))
        # the page's links into itself: the skip link and the year index (the first round's link down to the table is gone)
        self.assertEqual([a['href'][1:] for a in self.doc(RANGE).find_all('a') if (a['href'] or '').startswith('#')],
                         ['main', 'yr-2026', 'yr-2025', 'yr-2024', 'yr-2023', 'yr-2022', 'yr-undated', 'yr-planned'])
        # 'Show all' names the list it opens, and the list names its map and its heading
        button = self.doc(RANGE).find('button', cls='arc-all-btn')
        self.assertEqual(self.one(RANGE, button['aria-controls']).tag, 'ol')
        self.assertEqual(self.one(RANGE, 'arc-rows-synthetic-range')['data-map-target'], 'arc-map-synthetic-range')

    def test_ids_stay_unique_with_a_goal_and_a_journal_in_the_fixture(self):
        # a card and a table row of the same report, a goal row, an undated group: no id is written twice
        doc = self.doc(RANGE)
        self.assertEqual(len(doc.find_all(attrs={'data-key': 'syn-r-story'})), 2)        # the row beside the map and the table row
        self.assertEqual(len(doc.find_all(attrs={'data-key': 'syn-r-goal'})), 2)         # the goal is in both lists as well
        self.assertEqual(len(doc.find_all(attrs={'data-slug': 'syn-r-story'})), 1)       # the Featured card
        ids = [n['id'] for n in doc.root.walk() if n['id']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_img_has_an_alt_and_every_control_a_name(self):
        for name in PAGES:
            doc = self.doc(name)
            for img in doc.find_all('img'):
                self.assertIn('alt', img)
            for node in doc.find('body').walk():
                if node.tag in ('a', 'button') and node['aria-hidden'] != 'true' and 'hidden' not in node:
                    self.assertTrue(node['aria-label'] or node.text() or node.find_all('img'), repr(node))

    def test_the_two_explorer_links_are_the_only_ones_that_need_javascript(self):
        # .reg-x marks them (region.css hides the class when scripting is off): both carry a query for trips.js
        for name in PAGES:
            marked = self.doc(name).find_all(cls='reg-x')
            hrefs = [n.find('a')['href'] for n in marked]
            self.assertEqual([h for h in hrefs if '?' not in h], [])
            queried = [a['href'] for a in self.main(name).find_all('a') if '?' in (a['href'] or '')]
            self.assertEqual(sorted(queried), sorted(hrefs))
        self.assertEqual([n['class'] for n in self.doc(RANGE).find_all(cls='reg-x')], ['reg-more reg-x', 'reg-find reg-x wrap'])
        self.assertEqual([n['class'] for n in self.doc(COAST).find_all(cls='reg-x')], ['reg-find reg-x wrap'])


# ---------------------------------------------------------------- the pages among the rest of the site

def resolve(here, href):
    """(the site-relative address a relative href on the page `here` names, its fragment): 'regions/a/' + '../../map/#x'
    -> ('map/', 'x'). The query is dropped. A folder address keeps its final slash; the home page is ''."""
    target, _hash, frag = href.partition('#')
    target = target.split('?', 1)[0]
    parts = [p for p in here.split('/')[:-1]]
    for seg in target.split('/'):
        if seg == '..':
            if not parts:
                raise AssertionError('%s on %s climbs out of the site' % (href, here or 'the home page'))
            parts.pop()
        elif seg not in ('', '.'):
            parts.append(seg)
    out = '/'.join(parts)
    if out and (target.endswith('/') or target in ('', '.', '..') or target.endswith('/..')):
        out += '/'
    return out, frag


class SiteLinkTests(RegionFixture):
    """Every page the page modules build for the fixture site, in memory (build.PAGE_MODULES, as tools/build.py runs
    them): the region pages link only to pages that exist, and the links other pages gained land on them."""

    def setUp(self):
        super().setUp()
        home = load_module(self, 'sitegen.pages.home')
        patcher = mock.patch.object(home, 'HOME_REGIONS', (RANGE, COAST))     # the home page draws these two region maps
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.forget)
        self.build_all()

    def build_all(self):
        """Every page of the site as it is now (call it again after use())."""
        self.forget()
        self.all = {}
        for name in self.build_mod.PAGE_MODULES:
            for p in importlib.import_module('sitegen.pages.' + name).build(self.site):
                self.assertNotIn(p.url, self.all, 'two pages at %r' % p.url)
                self.all[p.url] = p.html
        self._all_docs = {}

    def forget(self):
        # the page modules' per-build caches (keyed by the identity of one site's objects) may not outlive this site
        for name, cache in (('report', '_TITLE_COUNTS'), ('multiday', '_DRAWN')):
            mod = sys.modules.get('sitegen.pages.' + name)
            if mod is not None and hasattr(mod, cache):
                getattr(mod, cache).clear()

    def page_doc(self, url):
        if url not in self._all_docs:
            self._all_docs[url] = Doc(self.all[url])
        return self._all_docs[url]

    def ids(self, url):
        return {n['id'] for n in self.page_doc(url).root.walk() if n['id']}

    def region_urls(self):
        return ['regions/%s/' % SLUG[name] for name in PAGES]

    def test_region_is_a_page_module_after_archive(self):
        mods = self.build_mod.PAGE_MODULES
        self.assertIn('region', mods)
        self.assertEqual(mods.index('region'), mods.index('archive') + 1)
        self.assertEqual(mods.count('region'), 1)

    def test_the_site_has_the_three_region_pages_and_no_index_of_them(self):
        self.assertEqual(sorted(u for u in self.all if u.startswith('regions')), sorted(self.region_urls()))
        self.assertNotIn('regions/', self.all)
        for url in self.region_urls():
            self.assertEqual(self.all[url], self.pages[url].html)             # what region.build alone gave

    def test_every_link_of_a_region_page_is_relative_and_lands_on_a_built_page(self):
        checked = 0
        for url in self.region_urls():
            doc = self.page_doc(url)
            for a in doc.find('body').find_all('a'):
                href = a['href']
                with self.subTest(page=url, href=href):
                    self.assertIsNotNone(href)
                    self.assertFalse(href.startswith('/'), 'a root-relative link breaks under the site\'s folder on GitHub Pages')
                    self.assertNotIn('://', href)                              # the body links nowhere else, and never by full address
                    self.assertFalse(href.startswith(('mailto:', 'javascript:', '//')))
                    self.assertNotIn('index.html', href)
                    target, frag = resolve(url, href)
                    checked += 1
                    if target == 'feed.xml':                                   # the footer's RSS link: a file the build writes
                        continue
                    self.assertTrue(target in self.all, '%s on %s is no page of the site' % (href, url))
                    if frag:
                        self.assertTrue(frag in self.ids(target), '%s on %s: no such id on %s' % (href, url, target or 'the home page'))
        self.assertGreater(checked, 120)

    def test_a_region_page_links_where_the_contract_says(self):
        want = {'', 'map/', 'trips/', 'tick-list/', 'about/', 'feed.xml', 'regions/synthetic-range/', 'regions/synthetic-coast/'}
        want |= {core.section_url(a) for a in core.ACT}
        want |= {'trips/%s/' % s for s in PEAKS_PUB}
        url = 'regions/synthetic-obrien-peaks/'
        got = {resolve(url, a['href'])[0] for a in self.page_doc(url).find('body').find_all('a') if not a['href'].startswith('#')}
        self.assertEqual(got, want)
        # its links into the explorer keep their query
        self.assertEqual(sorted(a['href'] for a in self.page_doc(url).by_id('main').find_all('a') if 'trips/?' in a['href']),
                         ['../../trips/?region=synthetic-obrien-peaks', '../../trips/?region=synthetic-obrien-peaks&writeup=1'])

    def test_every_file_a_region_page_loads_is_addressed_relatively(self):
        for url in self.region_urls():
            doc = self.page_doc(url)
            files = [(n.tag, n['src']) for n in doc.root.walk() if n['src']]
            files += [(n.tag, n['href']) for n in doc.find('head').find_all('link') if n['rel'] in ('stylesheet', 'icon', 'alternate', 'preload')]
            self.assertGreater(len(files), 10)
            for tag, ref in files:
                with self.subTest(page=url, ref=ref):
                    if ref.startswith('https://fonts.googleapis.com/'):
                        continue                                               # the one stylesheet from elsewhere, on every page
                    self.assertNotIn('://', ref)
                    self.assertFalse(ref.startswith('/'))
                    target = resolve(url, ref)[0]
                    self.assertRegex(target, r'^(assets/(site\.css|site\.js|favicon\.svg|maps/region-[a-z-]+-(desktop|phone)\.(webp|base\.svg))'
                                             r'|feed\.xml|trips/syn-r-[a-z-]+/photos/\d\d(\.sm)?\.webp)$')
            # the only full addresses in the head are the page's own, in the canonical link and the share tags
            head = self.all[url].split('</head>', 1)[0]
            own = re.findall(r'"(https://[^"]+)"', head)
            self.assertEqual([u for u in own if not u.startswith(('https://fonts.', core.SITE_URL))], [])
            self.assertEqual({u for u in own if u.startswith(core.SITE_URL) and '/photos/' not in u}, {core.SITE_URL + url})

    def test_the_other_pages_link_to_the_region_pages(self):
        into = {}
        for url in sorted(self.all):
            if url.endswith('.json'):
                continue
            for a in self.page_doc(url).find('body').find_all('a'):
                href = a['href'] or ''
                if href.startswith('#') or '://' in href:
                    continue
                target, _frag = resolve(url, href)
                if target.startswith('regions/'):
                    self.assertTrue(target in self.all, '%s on %s is no page' % (href, url or 'the home page'))
                    into.setdefault(target, set()).add(url)
        self.assertEqual(sorted(into), sorted(self.region_urls()))
        # the Map page's panel, the Trips page's browse row, the home page, a report's breadcrumb, a goal's pager, and
        # the other region pages
        for name, report, goal in ((RANGE, 'syn-r-story', 'syn-r-goal'), (COAST, 'syn-r-cove-a', None), (PEAKS, 'syn-r-wall-a', None)):
            with self.subTest(region=name):
                url = 'regions/%s/' % SLUG[name]
                want = {'', 'map/', 'trips/', 'trips/%s/' % report} | ({'trips/%s/' % goal} if goal else set())
                want |= {u for u in self.region_urls() if u != url}
                self.assertEqual(want - into[url], set())
                self.assertNotIn(url, into[url])                               # no page links to itself this way
        # a region without a page is linked to nowhere as a page
        for name in (PLANS, DESERT, TRAIL):
            self.assertNotIn('regions/%s/' % SLUG[name], ''.join(self.all.values()))

    def test_the_map_pages_region_anchors_all_stay(self):
        ids = self.ids('map/')
        for name in MAPPED + [DESERT]:
            self.assertIn('region-' + SLUG[name], ids)
        for name in MAPPED:
            self.assertEqual(self.page_doc('map/').by_id('region-' + SLUG[name]).classes, ['arc-panel'])
        self.assertIn('other-places', ids)
        self.assertIn('all-reports', ids)
        # ... and 'Open the map' on the home page still goes to the panel, not to the page
        home = self.page_doc('').find('section', cls='hom-where')
        self.assertEqual([a['href'] for a in home.find_all('a', cls='hom-reg-a')], ['map/#region-synthetic-range', 'map/#region-synthetic-coast'])

    def test_the_explorer_reads_the_two_queries_the_region_pages_write(self):
        # trips/?region=<slug>&writeup=1 is the explorer's own canonical form: its form has a region select with that
        # slug as a value and a 'writeup' checkbox whose value is 1, and its cards carry the slug the query names
        form = self.page_doc('trips/').by_id('search')
        region = form.find('select', attrs={'name': 'region'})
        values = [o['value'] for o in region.find_all('option')]
        for name in PAGES:
            self.assertIn(SLUG[name], values)
            self.assertIn('?region=%s' % SLUG[name], self.all['regions/%s/' % SLUG[name]])
        box = form.find('input', attrs={'name': 'writeup'})
        self.assertEqual((box['type'], box['value']), ('checkbox', '1'))
        cards = self.page_doc('trips/').find_all('li', cls='tcard')
        self.assertEqual(sorted(c['data-slug'] for c in cards if c['data-region'] == SLUG[PEAKS] and c['data-writeup'] == '1'), PEAKS_PUB)
        self.assertEqual(len([c for c in cards if c['data-region'] == SLUG[RANGE] and c['data-writeup'] == '1']), 5)

    def test_the_explorer_shows_the_reports_the_region_page_lists(self):
        # REVISED in round 2: 'Search and filter these in Trips' opens trips/?region=<slug>, and the page lists every
        # report whose region is its name. The explorer's cards with that slug are exactly those reports, a journal
        # and a report without a track included, and the cards among them with a write-up are the K of the page's
        # 'All K write-ups in Trips'
        helpers.make_series(self.trips_dir, slug='syn-r-range-journal', title='Synthetic Range Journal', region=RANGE, body=LONG)
        self.use(named={RANGE: ['syn-r-lap', 'syn-r-desert']})                # a map entry out of step changes nothing here
        self.build_all()
        cards = self.page_doc('trips/').find_all('li', cls='tcard')
        for name in PAGES:
            with self.subTest(region=name):
                shown = [c for c in cards if c['data-region'] == SLUG[name]]
                self.assertEqual([c['data-slug'] for c in shown], helpers.slugs(self.pub(name)))
                written = [c for c in shown if c['data-writeup'] == '1']
                more = self.main(name).find('p', cls='reg-more')
                self.assertEqual(more.text() if more else None, ('All %d write-ups in Trips' % len(written)) if len(written) > 1 else None)
                # ... and the 'By region' link beside the same count leads back to the page
                link = [a for a in self.page_doc('trips/').find('nav', cls='trx-browse').find_all('a') if a['href'] == '../regions/%s/' % SLUG[name]]
                self.assertEqual([a.text() for a in link], ['%s, %d reports' % (name, len(shown))])
        self.assertIn('syn-r-range-journal', [c['data-slug'] for c in cards if c['data-region'] == SLUG[RANGE]])
        self.assertIn('syn-r-short', [c['data-slug'] for c in cards if c['data-region'] == SLUG[RANGE]])
        self.assertEqual(self.main(RANGE).find('p', cls='reg-more').text(), 'All 6 write-ups in Trips')
        # the Map page's panel for the region, by its own rule, shows the two trips its map names
        panel = self.page_doc('map/').by_id('region-' + SLUG[RANGE])
        self.assertEqual([li['data-key'] for li in panel.find_all('li', cls='arc-row')], ['syn-r-desert', 'syn-r-lap'])

    def test_no_region_page_is_in_a_search_index(self):
        for url in ('trips/search.json', 'trips/journal.json', 'tick-list/search.json'):
            if url in self.all:
                self.assertNotIn('regions/', self.all[url])
        self.assertIn('trips/search.json', self.all)


# ---------------------------------------------------------------- section 5: the guard of archive.js

def strip_js_comments(src):
    """A script with its comments blanked; strings are kept (a '//' inside a quoted string is not a comment)."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in '"\'`':
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == '\\' else 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith('//', i):
            j = src.find('\n', i)
            i = n if j < 0 else j
        elif src.startswith('/*', i):
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
            out.append(' ')
        else:
            out.append(c)
            i += 1
    return ''.join(out)


class Unreadable(ValueError):
    """A guard written in a shape this file does not read: a person has to look at it."""


def read_guard(src):
    """(alias, condition) of the script's first statement after 'use strict': `if (<condition>) return;`, optionally
    after `var <alias> = document.body.classList;`. Raises Unreadable for any other opening."""
    code = strip_js_comments(src).strip()
    m = re.match(r"""\(function\s*\(\s*\)\s*\{\s*(['"])use strict\1\s*;\s*"""
                 r"""(?:(?:var|const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*document\.body\.classList\s*;\s*)?"""
                 r"""if\s*\((.*?)\)\s*return\s*;""", code, re.S)
    if not m:
        raise Unreadable('the script does not open with a body-class guard')
    return m.group(2), m.group(3)


def guard_returns(cond, alias, classes):
    """True when the guard's condition holds (the script returns at once) for a page whose <body> has these classes.
    The condition is read as `!`, `&&`, `||` and brackets over `<list>.contains('<class>')`, where <list> is
    document.body.classList or its alias; anything else is Unreadable."""
    owners = ['document.body.classList'] + ([alias] if alias else [])
    token = re.compile(r"""\s*(?:(?:%s)\s*\.\s*contains\(\s*(?:'(?P<a>[\w-]+)'|"(?P<b>[\w-]+)")\s*\)|(?P<op>&&|\|\||!|\(|\)))"""
                       % '|'.join(re.escape(o) for o in owners))
    toks, at = [], 0
    while cond[at:].strip():
        m = token.match(cond, at)
        if not m:
            raise Unreadable(cond)
        toks.append((m.group('op') or 'contains', m.group('a') or m.group('b')))
        at = m.end()
    pos = [0]

    def peek():
        return toks[pos[0]][0] if pos[0] < len(toks) else None

    def take():
        if pos[0] >= len(toks):
            raise Unreadable(cond)
        pos[0] += 1
        return toks[pos[0] - 1]

    def unary():
        tok, cls = take()
        if tok == '!':
            return not unary()
        if tok == '(':
            value = either()
            if take()[0] != ')':
                raise Unreadable(cond)
            return value
        if not cls:
            raise Unreadable(cond)
        return cls in classes

    def both():
        value = unary()
        while peek() == '&&':
            take()
            value = unary() and value
        return value

    def either():
        value = both()
        while peek() == '||':
            take()
            value = both() or value
        return value

    value = either()
    if pos[0] != len(toks):
        raise Unreadable(cond)
    return value


def guard_classes(cond):
    return sorted(set(re.findall(r"""contains\(\s*['"]([\w-]+)['"]\s*\)""", cond)))


class ScriptGuardTests(unittest.TestCase):
    """assets/js/pages/archive.js runs on the Map page and on a region page (its activity filter is the table's code)
    and on no other page. No Node harness drives this script: the guard is read out of the source as text, in the one
    shape it is written in (see read_guard and guard_returns), and tried against every body class the site writes."""

    def setUp(self):
        with open(os.path.join(ROOT, 'assets', 'js', 'pages', 'archive.js'), encoding='utf-8') as fh:
            self.src = fh.read()
        self.alias, self.cond = read_guard(self.src)

    def returns(self, *classes):
        return guard_returns(self.cond, self.alias, set(classes))

    def body_classes(self):
        """Every class a page module gives <body>, read from the modules' sources (body_cls='...')."""
        found = set()
        folder = os.path.join(ROOT, 'tools', 'sitegen', 'pages')
        for name in sorted(os.listdir(folder)):
            if name.endswith('.py'):
                with open(os.path.join(folder, name), encoding='utf-8') as fh:
                    for value in re.findall(r"body_cls='([^']*)'", fh.read()):
                        found.update(c for c in value.replace('%s', 'x').split() if c)
        return found

    def test_the_reader_reads_the_shapes_it_says_it_reads(self):
        old = "(function () {\n  'use strict';\n  if (!document.body.classList.contains('p-archive')) return;\n  go();\n})();"
        alias, cond = read_guard(old)
        self.assertEqual((alias, guard_classes(cond)), (None, ['p-archive']))
        self.assertFalse(guard_returns(cond, alias, {'p-archive'}))
        self.assertTrue(guard_returns(cond, alias, {'p-region'}))
        self.assertTrue(guard_returns(cond, alias, set()))
        both = ("/* a comment with if (x) return; in it */\n(function () {\n  'use strict'; // and 'p-home' here\n  var c = document.body.classList;\n"
                "  if (!(c.contains('p-a') || c.contains(\"p-b\"))) return;\n})();")
        alias, cond = read_guard(both)
        self.assertEqual((alias, guard_classes(cond)), ('c', ['p-a', 'p-b']))
        self.assertEqual([guard_returns(cond, alias, s) for s in (set(), {'p-a'}, {'p-b'}, {'p-a', 'p-b'}, {'p-c'})], [True, False, False, False, True])
        for unreadable in ("(function () { 'use strict'; go(); if (!document.body.classList.contains('p-a')) return; })();",
                           "(function () { 'use strict'; if (!/p-(a|b)/.test(document.body.className)) return; })();",
                           "(function () { 'use strict'; if (!other.contains('p-a')) return; })();"):
            with self.assertRaises(Unreadable):
                alias, cond = read_guard(unreadable)
                guard_returns(cond, alias, {'p-a'})

    def test_the_guard_is_the_first_thing_the_script_does(self):
        code = strip_js_comments(self.src).strip()
        self.assertTrue(code.startswith('(function () {'))
        self.assertTrue(code.endswith('})();'))
        before = code[:code.index('return;')]
        self.assertNotIn('querySelector', before)                       # nothing is looked up or wired before the guard
        self.assertNotIn('addEventListener', before)
        self.assertEqual(before.count(';'), 2 if self.alias else 1)      # 'use strict'; (the class list;) then the guard

    def test_it_names_p_archive_and_p_region_and_nothing_else(self):
        self.assertEqual(guard_classes(self.cond), ['p-archive', 'p-region'])

    def test_it_runs_on_the_map_page_and_on_a_region_page(self):
        self.assertFalse(self.returns('p-archive'))
        self.assertFalse(self.returns('p-region'))
        self.assertFalse(self.returns('p-archive', 'p-region'))
        self.assertFalse(self.returns('p-region', 'km'))                # another class beside it changes nothing

    def test_it_returns_at_once_on_every_other_page(self):
        classes = self.body_classes()
        for known in ('p-home', 'p-trips', 'p-ticklist', 'p-section', 'p-report', 'p-goal', 'p-multiday', 'p-series', 'p-fsmap', 'p-about',
                      'p-404', 'p-archive', 'p-region'):
            self.assertIn(known, classes)                                # the page modules still write the classes tried here
        for cls in sorted(classes - {'p-archive', 'p-region'}):
            with self.subTest(body=cls):
                self.assertTrue(self.returns(cls))
        self.assertTrue(self.returns())                                  # a page without a body class
        self.assertTrue(self.returns('p-report', 'p-goal'))
        self.assertTrue(self.returns('p-regions'))                       # a class is a whole word
        self.assertTrue(self.returns('p-archives'))
        self.assertTrue(self.returns('region'))

    def test_the_rest_of_the_script_still_looks_for_what_a_region_page_has(self):
        # the 'Show all' toggle and the filter are the code a region page needs (REVISED in round 2: the page has the
        # Map page's list): their hooks are the ones the page-mode panel and the scoped table write, and the one block
        # a region page lacks (the tab list) is looked up in a way that finds nothing there
        code = strip_js_comments(self.src)
        for hook in ("querySelector('.arc-filt')", "querySelectorAll('.arc-yr')", "getElementById('arc-live')",
                     "querySelectorAll('.arc-years li[data-group]')", "querySelectorAll('.arc-all-btn')",
                     "querySelector('.arc-tabs[role=\"tablist\"]')"):
            self.assertIn(hook, code)
        self.assertIn('if (!bar) return;', code)                         # a region of one activity has no filter row
        self.assertIn('if (list && sec) {', code)                        # no tab list: the tab code is skipped
        # 'Show all' is wired before the script leaves for want of a filter row, so a long list of one activity opens too
        self.assertLess(code.index("querySelectorAll('.arc-all-btn')"), code.index('if (!bar) return;'))
        # what the toggle reads is what the panel writes: the list by the button's aria-controls, the hidden rows by
        # .arc-more, the collapsed state by a class of the list, the label as the button's first node
        for hook in ("document.getElementById(b.getAttribute('aria-controls'))", "ol.classList.add('arc-collapsed')", "b.hidden = false",
                     "ol.querySelector('.arc-more a')", 'b.firstChild.nodeValue'):
            self.assertIn(hook, code)


if __name__ == '__main__':
    unittest.main()
