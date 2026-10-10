"""Phase 3: single-day report pages (sitegen.pages.report.page) in their two layouts, pinned to contract-phase3.md
section 2, to what sections 3 and 4 say a report, a goal and a multi-day page carry (the share row, the copy-link
action, the place of the related block), to the later decisions of section 9 (the #photos anchor on a story whose
only photo is the lead photo, the share row on multi-day pages) and to section 10, which overrides the rest: the
section row's fixed order and the absence of a current marker (10.2), the related block without the pager's two
reports (10.3), the lead-photo threshold, the share image and the numbering of unnamed grid photos (10.4), and the map
captions of undated trips and of the section pages' featured block (10.5). core.related / core.related_block /
core.copy_link and report.neighbours themselves are in tests/test_related.py; the automatic cover pick is in
tests/test_cover.py.

A synthetic site in a temp dir, every slug prefixed syn- so nothing under rendered/trips/ is ever consulted:

  story layout     syn-story      a write-up, four photos (portrait, landscape with a caption, landscape, portrait: the
                                  cover is the first photo wide enough to lead, not the first photo) and a beta row
                   syn-explicit   a write-up, three landscapes, cover_photo names the last one, a focal point
                   syn-one        a write-up and one landscape (the cover is the only photo), no beta
                   syn-one-beta   the same with a beta row
                   syn-two-tall   a write-up and two portraits: a story without a lead photo (no landscape to lead
                                  with; both portraits stay in the Photos section)
                   syn-portrait   a write-up and one portrait: a story without a hero (the aside photo stays)
  compact layout   syn-words      a write-up and a beta row, no photo
                   syn-photos     three photos, no write-up
                   syn-tall-only  one portrait, no write-up
                   syn-track      a track only
                   syn-undated    a track only, no date
  other kinds      syn-goal (planned, with notes, a photo and outings that name syn-story and syn-tour), syn-tour
                   (multi-day, with a write-up and a photo), syn-journal (series, with a write-up and day photos)

A test that needs a trip the fixture lacks writes it with add() (a syn- slug as well) and the site is loaded again.

With no rendered folder core.render_meta returns no maps and no charts and every page still builds; the tests that need
a map or a chart point the trip at a placeholder render folder inside the temp dir (render()). The site dict comes from
tools/build.py's own site_of(), registered with core as build() does. The page modules are imported in setUp and the
contract's functions are fetched through need(), so a missing module or function fails each test clearly instead of
breaking discovery. core.region_map_href reads rendered/site/meta.json; the fixture region is patched into core's
in-memory copy. Every sentence in a fixture is synthetic.
"""
import importlib
import itertools
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
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, photo, LANDSCAPE, PORTRAIT  # noqa: E402

WRITEUP = ('Synthetic write-up for a test.\n\n'
           'Second synthetic paragraph, with *emphasis* and a [synthetic link](https://example.test/).')
NOTES = 'Synthetic planning notes for a test.'
CAPTION = 'Synthetic caption: "quoted" & <bracketed>.'
REGION = 'Synthetic Range'
BETA = [{'label': 'Trailhead', 'value': 'Synthetic Lot'}]
TRACK_NOTE = 'Synthetic recorder, one synthetic gap'      # a beta row labelled Track: the stats footnote prints it
CREDIT = ['Terrain: AWS Terrain Tiles', 'Map data © OpenStreetMap contributors', 'Not for navigation']   # every caption's end
HERO_SIZES = '(min-width: 1200px) 1248px, 100vw'

STORY = ['syn-story', 'syn-explicit', 'syn-one', 'syn-one-beta', 'syn-two-tall', 'syn-portrait']
HERO = ['syn-story', 'syn-explicit', 'syn-one', 'syn-one-beta']   # stories that lead with the cover (a landscape photo)
NO_LEAD = ['syn-two-tall']                                         # a story whose cover is a portrait: no lead photo
ONLY_HERO = ['syn-one', 'syn-one-beta']                                           # ... and have no other photo
COMPACT = ['syn-words', 'syn-photos', 'syn-tall-only', 'syn-track', 'syn-undated']
SINGLE = STORY + COMPACT
# the legacy ids a page carries beyond #title, #stats and #map (#profile comes with a rendered chart). syn-one and
# syn-one-beta have no Photos section, but keep #photos as an anchor on the lead photo (contract section 9)
SECTION_IDS = {'syn-story': {'beta', 'report', 'photos'}, 'syn-explicit': {'report', 'photos'}, 'syn-one': {'report', 'photos'},
               'syn-one-beta': {'beta', 'report', 'photos'}, 'syn-two-tall': {'report', 'photos'}, 'syn-portrait': {'report'},
               'syn-words': {'beta', 'report'}, 'syn-photos': {'photos'}, 'syn-tall-only': set(), 'syn-track': set(),
               'syn-undated': set()}
LEGACY_IDS = ('title', 'stats', 'map', 'profile', 'beta', 'report', 'photos')
BLOCKS = ('rep-tick', 'rep-toc', 'rail-toc', 'rep-aside-ph', 'rep-share', 'rep-related', 'pager')   # blocks without an id
SECTION_NAVS = ('rep-toc', 'rail-toc', 'bbar', 'rep-actions')

REPORT = ('Report', '#report')
MAP = ('Map', '#map')
PHOTOS = ('Photos', '#photos')
BETA_ITEM = ('Beta', '#beta')
STATS = ('Stats', '#stats')
PROFILE = ('Profile', '#profile')
SPEED = ('Speed', '#profile')


def load_module(tc, name):
    try:
        return importlib.import_module(name)
    except ImportError as ex:
        tc.fail('%s is not importable: %s' % (name.replace('.', '/') + '.py', ex))


def need(tc, mod, name):
    """mod.<name>, or a clear failure of the calling test when the function / constant the contract names is missing."""
    if not hasattr(mod, name):
        tc.fail('%s.%s is missing (contract-phase3.md)' % (mod.__name__, name))
    return getattr(mod, name)


def marks(root):
    """The page's blocks in document order: every element id, and '.<class>' for the blocks that carry none."""
    out = []
    for node in root.walk():
        out += ['.' + c for c in BLOCKS if c in node.classes]
        if node['id']:
            out.append(node['id'])
    return out


def ml_items(node):
    """The items of a meta line (core.meta_items) as a reader sees them: the screen-reader ', ' separators dropped."""
    return [re.sub(r'^, ', '', m.text()) for m in node.find_all('span', cls='mi')]


def ancestors(node):
    out = []
    p = node.parent
    while p is not None:
        out.append(p)
        p = p.parent
    return out


def bar_items(nav):
    """[(label, href)] of a phone bottom bar, in order."""
    return [(a.find('span').text(), a['href']) for a in nav.find_all('a')]


def legacy_bar(t, gpx_href, has_beta, has_report, has_gallery, chart=''):
    """The phone bottom bar exactly as report.bottom_bar built it before Phase 3 (the compact layout must not change)."""
    items = [('#map', 'map', 'Map')]
    if has_beta:
        items.append(('#beta', 'beta', 'Beta'))
    elif t['kind'] != 'planned':
        items.append(('#profile', 'profile', 'Speed' if chart == 'speed' else 'Profile') if chart else ('#stats', 'beta', 'Stats'))
    if has_report:
        items.append(('#report', 'report', 'Report'))
    elif has_gallery:
        items.append(('#photos', 'photo', 'Photos'))
    out = ''.join('<a href="%s">%s<span>%s</span></a>' % (h, core.icon(ic, 24), lab) for h, ic, lab in items)
    out += '<a href="%s" download>%s<span>GPX</span></a>' % (gpx_href, core.icon('download', 24))
    return '<nav class="bbar" aria-label="Report sections" style="--n:%d">%s</nav>' % (len(items) + 1, out)


class ReportFixture(unittest.TestCase):

    def setUp(self):
        self.report = load_module(self, 'sitegen.pages.report')
        getattr(self.report, '_TITLE_COUNTS', {}).clear()   # the per-build title cache is keyed by id(): never reuse one
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        meta = {'hash': '', 'maps': {}, 'regions': [], 'all_regions': [REGION]}
        patcher = mock.patch.object(core, '_SITE_META', [meta])
        patcher.start()
        self.addCleanup(patcher.stop)
        mk = helpers.make_trip
        # story layout
        mk(self.tmp, 'syn-story', title='Synthetic Story', activity='hike', date='2026-06-01', region=REGION, place='Synthetic Basin',
           track=True, body=WRITEUP, beta=BETA, stats={'distance_km': 12.0, 'gain_m': 800, 'high_m': 2900, 'low_m': 2100},
           photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic photo one'),
                   photo('photos/02.webp', LANDSCAPE, alt='Synthetic photo two', caption=CAPTION, sm=True),
                   photo('photos/03.webp', LANDSCAPE, alt='Synthetic photo three'),
                   photo('photos/04.webp', PORTRAIT, alt='Synthetic photo four')])
        mk(self.tmp, 'syn-explicit', title='Synthetic Explicit Cover', activity='ski', date='2026-05-20', region=REGION, track=True,
           body=WRITEUP, cover_photo='photos/03.webp', cover_focal_x=30, cover_focal_y=60,
           photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one'), photo('photos/02.webp', LANDSCAPE, alt='Synthetic photo two'),
                   photo('photos/03.webp', LANDSCAPE, alt='')])
        mk(self.tmp, 'syn-one', title='Synthetic One Photo', activity='hike', date='2026-05-10', region=REGION, track=True, body=WRITEUP,
           photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one')])
        mk(self.tmp, 'syn-one-beta', title='Synthetic One Photo With Beta', activity='hike', date='2026-05-05', region=REGION, track=True,
           body=WRITEUP, beta=BETA, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one')])
        mk(self.tmp, 'syn-two-tall', title='Synthetic Two Portraits', activity='climb', date='2026-04-20', region=REGION, track=True,
           body=WRITEUP, photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic photo one'),
                                 photo('photos/02.webp', PORTRAIT, alt='Synthetic photo two')])
        mk(self.tmp, 'syn-portrait', title='Synthetic Lone Portrait', activity='hike', date='2026-04-10', region=REGION, track=True,
           body=WRITEUP, photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic photo one', caption=CAPTION)])
        # compact layout
        mk(self.tmp, 'syn-words', title='Synthetic Words Only', activity='hike', date='2026-03-01', region=REGION, track=True,
           body=WRITEUP, beta=BETA)
        mk(self.tmp, 'syn-photos', title='Synthetic Photos Only', activity='mtb', date='2026-02-01', region=REGION, track=True,
           photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one'), photo('photos/02.webp', PORTRAIT, alt='Synthetic photo two'),
                   photo('photos/03.webp', LANDSCAPE, alt='Synthetic photo three')])
        mk(self.tmp, 'syn-tall-only', title='Synthetic Portrait Only', activity='hike', date='2026-01-20', region=REGION, track=True,
           photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic photo one')])
        mk(self.tmp, 'syn-track', title='Synthetic Track Only', activity='hike', date='2025-12-01', region=REGION, track=True)
        mk(self.tmp, 'syn-undated', title='Synthetic Undated Track', activity='hike', region=REGION, track=True)
        # the other kinds: none of them is ever a story, whatever they carry
        goal = mk(self.tmp, 'syn-goal', title='Synthetic Goal', activity='hike', kind='planned', region=REGION, track=True, body=NOTES,
                  photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one')])
        goals = load_module(self, 'goals')
        with open(os.path.join(goal, 'goal.json'), 'w', encoding='utf-8') as fh:
            json.dump(dict(goals.defaults(), status='completed', added_at='2026-01-01',
                           outings=[{'outcome': 'attempted', 'date': '2026-03-10', 'report_slug': 'syn-tour', 'note': ''},
                                    {'outcome': 'completed', 'date': '2026-06-01', 'report_slug': 'syn-story', 'note': ''}]), fh)
        mk(self.tmp, 'syn-tour', title='Synthetic Tour', activity='ski', kind='multi-day', date='2026-03-10', end_date='2026-03-11',
           region=REGION, body=WRITEUP, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one')],
           days=[{'title': 'Synthetic Day One', 'date': '2026-03-10'}, {'title': 'Synthetic Day Two', 'date': '2026-03-11'}])
        helpers.make_series(self.tmp, slug='syn-journal', title='Synthetic Journal', written_day=None, region=REGION, body=WRITEUP)
        self.load_site()

    # ------------------------------------------------------------ helpers

    def load_site(self):
        """Load the temp folder through the real loader and tools/build.py's own site_of(), registered with core as
        build() does; every page built so far is forgotten."""
        getattr(self.report, '_TITLE_COUNTS', {}).clear()
        self.trips = helpers.load_dir(self.tmp)
        self.by = {t['slug']: t for t in self.trips}
        self.site = load_module(self, 'build').site_of(helpers.newest_first(self.trips))
        core.register_site(self.site)
        self.pages, self.docs = {}, {}

    def add(self, slug, **meta):
        """One more synthetic trip for a single test, written to the temp dir like the fixture's; the site is then loaded
        again, so the trip is published and its page built exactly as the others are. Unless meta says otherwise it is
        a hike in the fixture's region on 2025-06-15 with a track (date=None: an undated trip; a trip with days gets
        no track.gpx). Returns the trip; call it before render(), which a reload forgets."""
        defaults = [('activity', 'hike'), ('date', '2025-06-15'), ('region', REGION), ('title', 'Synthetic ' + slug[4:].replace('-', ' ').title())]
        if not meta.get('days'):
            defaults.append(('track', True))
        for k, v in defaults:
            meta.setdefault(k, v)
        helpers.make_trip(self.tmp, slug, **{k: v for k, v in meta.items() if v is not None})
        self.load_site()
        return self.by[slug]

    def render(self, slug, maps=True, chart=''):
        """Point the trip at a placeholder render folder in the temp dir: meta.json with the three report maps and, with
        chart='profile' | 'speed', that chart, plus the tiny fragments core.map_block / core.chart_block inline."""
        folder = os.path.join(self.tmp, '_rendered', slug)
        os.makedirs(folder, exist_ok=True)
        meta = {'maps': {}, 'charts': {}}
        if maps:
            for name, (w, h) in (('map-wide', (1440, 640)), ('map-col', (718, 400)), ('map-phone', (390, 336))):
                meta['maps'][name] = {'w': w, 'h': h, 'png': name + '.webp', 'base': name + '.base.svg'}
                with open(os.path.join(folder, name + '.svg.html'), 'w', encoding='utf-8') as fh:
                    fh.write('<svg width="%d" height="%d" viewBox="0 0 %d %d"></svg>' % (w, h, w, h))
        if chart:
            for size, w in (('wide', 1248), ('col', 718), ('phone', 358)):
                name = '%s-%s' % (chart, size)
                meta['charts'][name] = {'w': w, 'h': 160, 'kind': chart, 'gps_max_ft': 9514.0, 'min_ft': 6890.0, 'vx': 2.0}
                with open(os.path.join(folder, name + '.svg.html'), 'w', encoding='utf-8') as fh:
                    fh.write('<svg width="%d" height="160" viewBox="0 0 %d 160"></svg>' % (w, w))
        with open(os.path.join(folder, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(meta, fh)
        self.by[slug]['rendered'] = folder
        self.pages.pop(slug, None)
        self.docs.pop(slug, None)

    def page(self, slug):
        if slug not in self.pages:
            self.pages[slug] = self.report.page(self.by[slug], self.site)
        return self.pages[slug]

    def doc(self, slug):
        if slug not in self.docs:
            self.docs[slug] = Doc(self.page(slug).html)
        return self.docs[slug]

    def main(self, slug):
        return self.doc(slug).by_id('main')

    def own(self, slug, tag=None, cls=None):
        """The page's own elements under <main>: the related reports' cards (their covers, their links) left out."""
        return [n for n in self.main(slug).find_all(tag, cls=cls) if not any('rep-related' in p.classes for p in ancestors(n))]

    def here(self, slug):
        return self.by[slug]['url']

    def photo_href(self, slug, file):
        return core.link(self.here(slug), self.here(slug)) + file

    def hero(self, slug):
        return self.main(slug).find('figure', cls='rep-hero')

    def toc(self, slug):
        nav = self.main(slug).find('nav', cls='rep-toc')
        self.assertIsNotNone(nav, '%s has no section row (nav.rep-toc)' % slug)
        return [(a.text(), a['href']) for a in nav.find_all('a')]

    def gallery_files(self, slug):
        sec = self.main(slug).by_id('photos')
        self.assertIsNotNone(sec, '%s has no Photos section' % slug)
        return [a['href'] for a in sec.find_all('a', cls='jph')]

    def actions(self, slug):
        """The title block's actions in order: (text, href) for a link, ('copy', data-copy) for the copy-link control."""
        out = []
        for el in self.main(slug).find('div', cls='rep-actions').elements():
            if el.tag == 'a':
                out.append((el.text(), el['href']))
            elif 'copy' in el.classes:
                out.append(('copy', el.find('button')['data-copy']))
            else:
                out.append((el.tag, None))
        return out

    def bbar(self, slug):
        nav = self.doc(slug).find('nav', cls='bbar')
        self.assertIsNotNone(nav, '%s has no phone bottom bar' % slug)
        return nav

    def caption(self, slug):
        cap = self.main(slug).by_id('map').find('div', cls='mapcap')
        self.assertIsNotNone(cap, '%s: the map section has no caption' % slug)
        return ml_items(cap)

    def head_html(self, slug):
        return self.page(slug).html.split('</head>', 1)[0]

    def preloads(self, slug):
        return self.doc(slug).find('head').find_all('link', attrs={'rel': 'preload', 'as': 'image'})

    def og_image(self, slug):
        m = self.doc(slug).find('head').find('meta', attrs={'property': 'og:image'})
        return m['content'] if m is not None else None

    def assertInOrder(self, seq, wanted):
        for w in wanted:
            self.assertIn(w, seq)
        pos = [seq.index(w) for w in wanted]
        self.assertEqual(pos, sorted(pos), '%r are not in this order in %r' % (wanted, seq))


# ---------------------------------------------------------------- report.narrative(): which layout a trip gets

class NarrativeTests(ReportFixture):

    def setUp(self):
        super().setUp()
        self.narrative = need(self, self.report, 'narrative')

    def test_a_writeup_and_a_landscape_photo_make_a_story(self):
        # section 2: narrative(t) -> True when the trip has a write-up (body_md) and a cover photo (cover)
        for slug in ('syn-story', 'syn-explicit', 'syn-one', 'syn-one-beta'):
            self.assertIs(self.narrative(self.by[slug]), True, slug)

    def test_a_writeup_and_only_a_portrait_photo_make_a_story(self):
        # sections 2.7 and 7: a write-up whose only photo is a portrait is still a story (t['cover'] exists)
        t = self.by['syn-portrait']
        self.assertIsNotNone(t['cover'])
        self.assertIs(self.narrative(t), True)
        self.assertIs(self.narrative(self.by['syn-two-tall']), True)

    def test_photos_without_a_writeup_stay_compact(self):
        # section 7: no write-up -> compact
        self.assertTrue(self.by['syn-photos']['cover'])
        self.assertIs(self.narrative(self.by['syn-photos']), False)
        self.assertIs(self.narrative(self.by['syn-tall-only']), False)

    def test_a_writeup_without_photos_stays_compact(self):
        # section 7: no photo at all -> compact
        t = self.by['syn-words']
        self.assertTrue(t['body_md'])
        self.assertIsNone(t['cover'])
        self.assertIs(self.narrative(t), False)

    def test_a_track_only_report_stays_compact(self):
        # section 2: neither a write-up nor a photo -> False
        self.assertIs(self.narrative(self.by['syn-track']), False)
        self.assertIs(self.narrative(self.by['syn-undated']), False)

    def test_a_planned_goal_is_never_a_story(self):
        # section 2: goal pages are not changed by the layouts, even with notes and a photo
        t = self.by['syn-goal']
        self.assertTrue(t['body_md'] and t['cover'])
        self.assertIs(self.narrative(t), False)

    def test_a_multi_day_trip_and_a_series_are_never_a_story(self):
        # section 2: single-day only; multi-day and series pages are not changed, even with a write-up and a cover
        for slug in ('syn-tour', 'syn-journal'):
            t = self.by[slug]
            self.assertTrue(t['body_md'] and t['cover'], slug)
            self.assertIs(self.narrative(t), False, slug)

    def test_the_fixture_covers_both_layouts(self):
        # the lists the other classes loop over say what narrative() says
        self.assertEqual([s for s in SINGLE if self.narrative(self.by[s])], STORY)


# ---------------------------------------------------------------- the order of the page and its ids

class LayoutTests(ReportFixture):

    def test_story_page_order(self):
        # section 2, items 1-8: title, lead photo, stats strip, section row, write-up (+ Beta rail), map, profile,
        # gallery, then the share row, the related reports and the pager
        self.render('syn-story', chart='profile')
        seq = marks(self.main('syn-story'))
        self.assertInOrder(seq, ['title', 'hero', 'stats', '.rep-toc', 'report', 'map', 'profile', 'photos', '.rep-share',
                                 '.rep-related', 'rel-h', '.pager'])
        self.assertInOrder(seq, ['.rep-toc', 'beta', 'map'])   # the Beta rail sits beside the write-up, as before

    def test_story_page_order_without_a_gallery(self):
        # sections 2 and 9: the same order when the cover was the only photo; #photos is then the anchor on the lead
        # photo, not a section after the map
        seq = marks(self.main('syn-one'))
        self.assertInOrder(seq, ['title', 'hero', 'photos', 'stats', '.rep-toc', 'report', 'map', '.rep-share', 'rel-h', '.pager'])
        self.assertEqual(seq[seq.index('hero') + 1], 'photos')

    def test_compact_page_order_keeps_the_map_before_the_report(self):
        # section 2, compact layout: today's order (title, stats, map, profile, write-up + rail), then share row, related, pager
        self.render('syn-words', chart='profile')
        seq = marks(self.main('syn-words'))
        self.assertInOrder(seq, ['title', 'stats', 'map', 'profile', 'report', '.rep-share', '.rep-related', 'rel-h', '.pager'])
        self.assertInOrder(seq, ['profile', 'beta', '.rep-share'])
        self.assertNotIn('hero', seq)

    def test_compact_photo_page_order_keeps_the_map_before_the_gallery(self):
        # section 2, compact layout: title, stats, map, gallery, then the share row and the related reports
        seq = marks(self.main('syn-photos'))
        self.assertInOrder(seq, ['title', 'stats', 'map', 'photos', '.rep-share', 'rel-h'])

    def test_more_like_this_leaves_out_the_reports_of_the_pager(self):
        # section 10.3: both layouts call core.related_block(t, here, site, skip=report.neighbours(t, site)), so no card
        # repeats the Newer / Older report of the pager right below, and three others are offered
        neighbours = need(self, self.report, 'neighbours')
        related_block = need(self, core, 'related_block')
        self.assertEqual([x and x['slug'] for x in neighbours(self.by['syn-story'], self.site)], [None, 'syn-one'])
        self.assertIn('data-slug="syn-one"', related_block(self.by['syn-story'], 'trips/syn-story/', self.site))   # the rule alone
        for slug in ('syn-story', 'syn-one', 'syn-words'):
            with self.subTest(slug):
                t = self.by[slug]
                skip = neighbours(t, self.site)
                block = related_block(t, t['url'], self.site, skip=skip)
                self.assertTrue(block)
                self.assertEqual(self.page(slug).html.count(block), 1)
                main = self.main(slug)
                navs = main.find_all('nav', cls='pager')
                self.assertEqual(len(navs), 1)
                pager = [a['href'] for a in navs[0].find_all('a')]
                self.assertEqual(pager, ['../../' + x['url'] for x in skip if x])
                cards = [c.find('h3').find('a')['href'] for c in main.find('ul', cls='rep-rel').find_all('li', cls='tcard')]
                self.assertEqual(len(cards), 3)
                self.assertFalse(set(pager) & set(cards), cards)

    def test_the_two_layouts_differ_in_where_the_map_sits(self):
        # sections 2 and 7: story = report before map, compact = map before report
        story, compact = marks(self.main('syn-story')), marks(self.main('syn-words'))
        self.assertLess(story.index('report'), story.index('map'))
        self.assertLess(compact.index('map'), compact.index('report'))

    def test_every_legacy_id_is_present_where_its_section_exists(self):
        # hard rule + sections 2 and 9: #title #stats #map #profile #beta #report #photos are kept wherever the section
        # exists (#photos also on the lead photo when it is the only one), and nowhere else
        for chart in ('', 'profile'):
            for slug in SINGLE:
                with self.subTest(slug=slug, chart=chart):
                    self.render(slug, chart=chart)
                    doc = self.doc(slug)
                    want = {'title', 'stats', 'map'} | SECTION_IDS[slug] | ({'profile'} if chart else set())
                    self.assertEqual({i for i in LEGACY_IDS if doc.by_id(i) is not None}, want)

    def test_legacy_ids_keep_their_elements(self):
        # hard rule: the anchors land on the same kind of element as before (h1, the strip, the map, the rail's Beta block,
        # the write-up, the Photos section)
        self.render('syn-story', chart='profile')
        doc = self.doc('syn-story')
        got = {i: (doc.by_id(i).tag, doc.by_id(i).classes[0] if doc.by_id(i).classes else '') for i in LEGACY_IDS}
        self.assertEqual(got['title'][0], 'h1')
        self.assertEqual(got['stats'], ('section', 'wrap'))
        self.assertIn('rep-strip', doc.by_id('stats').classes)
        self.assertEqual(got['map'], ('section', 'rep-map'))
        self.assertEqual(got['profile'], ('section', 'rep-prof'))
        self.assertEqual(got['beta'], ('div', 'rail-b'))
        self.assertEqual(got['report'], ('div', 'rep-main'))
        self.assertEqual(got['photos'], ('section', 'rep-photos'))

    def test_ids_are_unique_on_every_page(self):
        # hard rule: every anchor kept means one element per id, on both layouts (the hero, the gallery and the related
        # cards add ids of their own)
        for slug in SINGLE:
            with self.subTest(slug):
                self.render(slug, chart='profile')
                ids = [n['id'] for n in self.doc(slug).root.walk() if n['id']]
                self.assertEqual(sorted(ids), sorted(set(ids)))

    def test_no_section_link_points_at_a_missing_id(self):
        # plan 9.1 / section 2.4: no rep-toc, rail-toc, bottom-bar or title-action link may point at an omitted section
        seen = 0
        for chart in ('', 'profile', 'speed'):
            for slug in SINGLE + ['syn-goal']:
                self.render(slug, chart=chart)
                doc = self.doc(slug)
                for cls in SECTION_NAVS:
                    for nav in doc.find_all(cls=cls):
                        for a in nav.find_all('a'):
                            href = a['href'] or ''
                            if href.startswith('#'):
                                seen += 1
                                with self.subTest(slug=slug, chart=chart, nav=cls, href=href):
                                    self.assertIsNotNone(doc.by_id(href[1:]), '%s links to %s, which is not on the page' % (cls, href))
        self.assertGreater(seen, 60)   # the loop really met the navs

    def test_body_class_marks_story_pages_only(self):
        # section 2: body_cls 'p-report p-report--story' on the story layout, 'p-report' alone on the compact one
        for slug in SINGLE:
            with self.subTest(slug):
                classes = self.doc(slug).find('body').classes
                self.assertIn('p-report', classes)
                self.assertEqual('p-report--story' in classes, slug in STORY)

    def test_other_kinds_never_get_the_story_class(self):
        # section 2: goal, multi-day and series pages are not changed by the layouts
        pages = {'syn-goal': self.page('syn-goal'),
                 'syn-tour': load_module(self, 'sitegen.pages.multiday').page(self.by['syn-tour'], self.site),
                 'syn-journal': load_module(self, 'sitegen.pages.series').page(self.by['syn-journal'], self.site)}
        for slug, p in pages.items():
            with self.subTest(slug):
                doc = Doc(p.html)
                self.assertNotIn('p-report--story', doc.find('body').classes)
                self.assertIsNone(doc.find('nav', cls='rep-toc'))
        self.assertIsNone(Doc(pages['syn-goal'].html).find('figure', cls='rep-hero'))   # section 2: a goal has no hero
        self.assertIsNone(Doc(pages['syn-tour'].html).find('figure', cls='rep-hero'))

    def test_the_writeup_is_verbatim_under_its_heading(self):
        # hard rule + section 2.5: id="report", h2 'Trip report', the prose exactly as markdown renders the body
        markdown = load_module(self, 'markdown')
        for slug in ('syn-story', 'syn-words'):
            with self.subTest(slug):
                rep = self.main(slug).by_id('report')
                self.assertEqual(rep.find('h2').text(), 'Trip report')
                self.assertEqual(rep.find('h2')['id'], 'report-h')
                self.assertIn('<div class="prose t-body">%s</div>' % markdown.to_html(self.by[slug]['body_md']), self.page(slug).html)
                self.assertEqual(self.main(slug).text().count('Second synthetic paragraph'), 1)

    def test_the_title_block_is_the_shared_one(self):
        # section 2.1: title_block markup unchanged (one h1#title with the verbatim title, the breadcrumb, the place line)
        for slug in ('syn-story', 'syn-words'):
            with self.subTest(slug):
                doc = self.doc(slug)
                self.assertEqual([h.text() for h in doc.find_all('h1')], [self.by[slug]['title']])
                sec = doc.by_id('main').find('section', cls='rep-title')
                self.assertEqual(sec['aria-labelledby'], 'title')
                self.assertEqual([a.text() for a in sec.find('nav', attrs={'aria-label': 'Breadcrumb'}).find_all('a')],
                                 ['Reports', 'Hiking', REGION])

    def test_the_tick_list_backlink_stays_under_the_title_block(self):
        # section 2 (goal / multi-day paragraph): report.tick_backlink follows the title block, so on a story it sits
        # above the lead photo
        seq = marks(self.main('syn-story'))
        self.assertInOrder(seq, ['title', '.rep-tick', 'hero', 'stats'])
        self.assertNotIn('.rep-tick', marks(self.main('syn-one')))

    def test_the_stats_strip_is_unchanged(self):
        # section 2.3: the strip section keeps its markup on both layouts
        for slug in ('syn-story', 'syn-words'):
            with self.subTest(slug):
                t = self.by[slug]
                self.assertIn('<section class="wrap rep-strip" id="stats" aria-label="Stats">%s%s</section>'
                              % (core.strip(core.strip_cells(t)), core.stats_note(t)), self.page(slug).html)

    def test_page_url_and_title(self):
        # hard rule: every URL unchanged; the page is still trips/<slug>/
        for slug in SINGLE:
            p = self.page(slug)
            self.assertEqual(p.url, 'trips/%s/' % slug)
            self.assertEqual(p.title, self.by[slug]['title'])
            self.assertEqual(self.doc(slug).find('link', attrs={'rel': 'canonical'})['href'], core.SITE_URL + 'trips/%s/' % slug)


# ---------------------------------------------------------------- the section row (report.section_nav)

class SectionNavTests(ReportFixture):

    def setUp(self):
        super().setUp()
        self.section_nav = need(self, self.report, 'section_nav')

    def items(self, *args):
        nav = Doc(self.section_nav(*args)).find('nav')
        return [(a.text(), a['href']) for a in nav.find_all('a')]

    def test_markup(self):
        # section 2.4: <nav class="rep-toc wrap" aria-label="Sections"><ul><li><a class="rep-toc-a" href="#…">…</a></li>
        self.assertEqual(self.section_nav(True, True, True),
                         '<nav class="rep-toc wrap" aria-label="Sections"><ul>'
                         '<li><a class="rep-toc-a" href="#report">Report</a></li>'
                         '<li><a class="rep-toc-a" href="#photos">Photos</a></li>'
                         '<li><a class="rep-toc-a" href="#map">Route</a></li>'
                         '<li><a class="rep-toc-a" href="#beta">Trip details</a></li></ul></nav>')

    def test_all_four_sections_in_the_plans_fixed_order(self):
        # sections 2.4 and 10.2: Report, Photos, Route, Trip details
        self.assertEqual(self.items(True, True, True),
                         [('Report', '#report'), ('Photos', '#photos'), ('Route', '#map'), ('Trip details', '#beta')])

    def test_the_fixed_order_holds_for_every_set_of_sections(self):
        # section 10.2: the plan's fixed order (Report, Photos, Route, Trip details), whichever sections the page has
        fixed = ['Report', 'Photos', 'Route', 'Trip details']
        for args in itertools.product((True, False), repeat=3):
            with self.subTest(has_report=args[0], has_gallery=args[1], has_beta=args[2]):
                labels = [lab for lab, _href in self.items(*args)]
                self.assertEqual(labels, [lab for lab in fixed if lab in labels])
                self.assertEqual(labels[-2:], ['Route', 'Trip details'])   # the two every report has
                self.assertEqual('Report' in labels, args[0])
                self.assertEqual('Photos' in labels, args[1])

    def test_the_fixed_order_is_not_the_order_of_the_page(self):
        # section 10.2: ... not page order: a story runs Beta (or the stats), write-up, map, photos, so the row's last
        # link points at the first of its targets and Photos comes before the map it follows on the page
        self.assertEqual([lab for lab, _href in self.toc('syn-story')], ['Report', 'Photos', 'Route', 'Trip details'])
        seq = marks(self.main('syn-story'))
        by_page = sorted(self.toc('syn-story'), key=lambda item: seq.index(item[1][1:]))
        self.assertEqual([lab for lab, _href in by_page], ['Trip details', 'Report', 'Route', 'Photos'])
        self.assertInOrder(seq, ['beta', 'report', 'map', 'photos'])
        # without beta rows Trip details is the stats strip, above the row itself
        seq = marks(self.main('syn-explicit'))
        self.assertInOrder(seq, ['stats', '.rep-toc', 'report', 'map', 'photos'])
        self.assertEqual([href for _lab, href in self.toc('syn-explicit')], ['#report', '#photos', '#map', '#stats'])

    def test_no_link_in_the_section_row_is_marked_current(self):
        # section 10.2: no link in the section row is ever marked current (base.js marks the current section in the phone
        # bottom bar only): the generator writes no aria-current into the row, for any set of sections ...
        for args in itertools.product((True, False), repeat=3):
            self.assertNotIn('aria-current', self.section_nav(*args), args)
        # ... nor on any built story page, where each link is the bare <a class="rep-toc-a" href="#...">
        for slug in STORY:
            with self.subTest(slug):
                nav = self.main(slug).find('nav', cls='rep-toc')
                links = nav.find_all('a')
                self.assertGreaterEqual(len(links), 3)
                for a in links:
                    self.assertNotIn('aria-current', a)
                    self.assertEqual(sorted(a.attrs), ['class', 'href'])
                self.assertEqual([n for n in nav.walk() if 'aria-current' in n], [])
                self.assertNotIn('aria-current', nav)

    def test_no_photos_item_without_a_gallery(self):
        # section 2.4: Photos only when the gallery has at least one photo
        self.assertEqual(self.items(True, False, True), [('Report', '#report'), ('Route', '#map'), ('Trip details', '#beta')])

    def test_trip_details_points_at_the_stats_without_beta_rows(self):
        # section 2.4: Trip details -> #beta when the trip has beta rows, else #stats
        self.assertEqual(self.items(True, True, False)[-1], ('Trip details', '#stats'))
        self.assertEqual(self.items(True, False, False), [('Report', '#report'), ('Route', '#map'), ('Trip details', '#stats')])

    def test_no_report_item_without_a_report(self):
        # section 2.4: listing only the sections present
        self.assertEqual(self.items(False, True, True), [('Photos', '#photos'), ('Route', '#map'), ('Trip details', '#beta')])

    def test_story_with_gallery_and_beta_lists_all_four(self):
        # sections 2.4 and 7: the toc items match the sections present
        self.assertEqual(self.toc('syn-story'), [('Report', '#report'), ('Photos', '#photos'), ('Route', '#map'), ('Trip details', '#beta')])

    def test_story_without_beta_sends_trip_details_to_the_stats(self):
        # section 2.4: no beta rows -> Trip details -> #stats
        self.assertEqual(self.toc('syn-explicit'), [('Report', '#report'), ('Photos', '#photos'), ('Route', '#map'), ('Trip details', '#stats')])
        self.assertIsNone(self.main('syn-explicit').by_id('beta'))

    def test_no_photos_item_when_the_cover_was_the_only_photo(self):
        # section 7: no Photos when the cover is the only photo
        self.assertEqual(self.toc('syn-one'), [('Report', '#report'), ('Route', '#map'), ('Trip details', '#stats')])
        self.assertEqual(self.toc('syn-one-beta'), [('Report', '#report'), ('Route', '#map'), ('Trip details', '#beta')])

    def test_the_page_uses_section_nav(self):
        # section 2.4: the row on the page is report.section_nav(has_report, has_gallery, has_beta)
        self.assertIn(self.section_nav(True, True, True), self.page('syn-story').html)
        self.assertIn(self.section_nav(True, False, False), self.page('syn-one').html)

    def test_one_section_row_per_story_and_no_rail_contents_list(self):
        # section 2.4: shown on the narrative layout, where it replaces the rail's Contents list
        for slug in STORY:
            with self.subTest(slug):
                main = self.main(slug)
                self.assertEqual(len(main.find_all('nav', cls='rep-toc')), 1)
                self.assertEqual(main.find('nav', cls='rep-toc')['aria-label'], 'Sections')
                self.assertIsNone(main.find('nav', cls='rail-toc'))
                self.assertIsNone(main.by_id('toc-h'))

    def test_compact_pages_have_no_section_row_and_no_hero(self):
        # section 2.4: narrative layout only; the compact layout has no .rep-toc and no .rep-hero
        for slug in COMPACT:
            with self.subTest(slug):
                main = self.main(slug)
                self.assertIsNone(main.find('nav', cls='rep-toc'))
                self.assertIsNone(main.find(cls='rep-hero'))
                self.assertIsNone(main.by_id('hero'))

    def test_compact_pages_have_a_single_content_section_and_no_contents_list(self):
        # the rail's old Contents list needed a write-up and a gallery on one compact page; a trip with both is always a
        # story (any photo resolves a cover), so a compact page has a write-up or a gallery, never both, and the list
        # and its code are gone
        for slug in COMPACT:
            with self.subTest(slug):
                main = self.main(slug)
                self.assertFalse(main.by_id('report') is not None and main.by_id('photos') is not None)
                self.assertIsNone(main.find('nav', cls='rail-toc'))


# ---------------------------------------------------------------- the lead photo (report.hero)

class HeroTests(ReportFixture):

    def test_the_hero_is_the_cover_file(self):
        # section 2.2: <figure class="rep-hero" id="hero"> holding the cover, linked to the full photo
        for slug in HERO:
            with self.subTest(slug):
                fig = self.hero(slug)
                self.assertIsNotNone(fig, '%s has no lead photo' % slug)
                self.assertEqual(fig['id'], 'hero')
                file = self.by[slug]['cover']['photo']['file']
                self.assertEqual(fig.find('a')['href'], self.photo_href(slug, file))
                self.assertEqual(fig.find('img')['src'], self.photo_href(slug, file))
                self.assertEqual(len(self.main(slug).find_all('figure', cls='rep-hero')), 1)

    def test_only_a_landscape_cover_leads_the_page(self):
        # the lead frame is 4:3 to 2:1: a portrait cover (two portraits, no landscape) would be cut to a band, so the
        # page keeps the story order without a lead photo and every photo stays in the Photos section, uncropped
        lead_photo = need(self, self.report, 'lead_photo')
        for slug in HERO:
            self.assertIs(lead_photo(self.by[slug]), self.by[slug]['cover']['photo'], slug)
        for slug in NO_LEAD + ['syn-portrait']:
            self.assertIsNone(lead_photo(self.by[slug]), slug)
        self.assertIsNone(lead_photo(self.by['syn-track']))                    # no cover at all
        for slug in NO_LEAD:
            with self.subTest(slug):
                t, main = self.by[slug], self.main(slug)
                self.assertIs(need(self, self.report, 'narrative')(t), True)   # still a story: write-up first
                self.assertIn('p-report--story', Doc(self.page(slug).html).find('body')['class'])
                self.assertIsNone(main.by_id('hero'))
                self.assertEqual(main.find_all('figure', cls='rep-hero'), [])
                self.assertEqual(main.find_all(cls='rep-anchor'), [])
                self.assertEqual(self.gallery_files(slug), [self.photo_href(slug, p['file']) for p in t['photos']])
                self.assertEqual([a['href'] for a in main.find('nav', cls='rep-toc').find_all('a')], ['#report', '#photos', '#map', '#stats'])
                self.assertLess(marks(main).index('report'), marks(main).index('map'))
        # a square photo is not wide enough either; 4:3 is
        square = dict(self.by['syn-one'], cover=dict(self.by['syn-one']['cover'], photo=dict(self.by['syn-one']['cover']['photo'], w=1000, h=1000)))
        self.assertIsNone(lead_photo(square))
        wide = dict(self.by['syn-one'], cover=dict(self.by['syn-one']['cover'], photo=dict(self.by['syn-one']['cover']['photo'], w=1600, h=1200)))
        self.assertIsNotNone(lead_photo(wide))
        unknown = dict(self.by['syn-one'], cover=dict(self.by['syn-one']['cover'], photo={'file': 'photos/01.webp', 'alt': ''}))
        self.assertIsNotNone(lead_photo(unknown))                               # no recorded size: treated as a landscape

    def test_the_lead_threshold_is_one_point_two(self):
        # section 10.4: content.LEAD_MIN_AR = 1.2; report.LEAD_MIN_AR is the same value (one line, drawn once: the
        # automatic cover pick in content.py and the lead photo in report.py cannot drift apart)
        content = load_module(self, 'content')
        self.assertEqual(need(self, content, 'LEAD_MIN_AR'), 1.2)
        self.assertEqual(need(self, self.report, 'LEAD_MIN_AR'), 1.2)
        self.assertIs(self.report.LEAD_MIN_AR, content.LEAD_MIN_AR)

    def test_a_cover_leads_from_six_to_five_up(self):
        # sections 9 and 10.4: the cover leads when its aspect ratio is at least 1.2: pinned from both sides, so neither
        # 1.1 nor 1.3 passes for the threshold (5:4 leads, 1199:1000 does not)
        lead_photo = need(self, self.report, 'lead_photo')
        base = self.by['syn-one']
        for (w, h), leads in (((1199, 1000), False), ((1200, 1000), True), ((1201, 1000), True), ((6, 5), True), ((599, 500), False),
                              ((1250, 1000), True), ((1150, 1000), False), ((1000, 1000), False), ((1000, 1200), False)):
            with self.subTest(w=w, h=h):
                t = dict(base, cover=dict(base['cover'], photo=dict(base['cover']['photo'], w=w, h=h)))
                self.assertEqual(lead_photo(t) is not None, leads)
                if leads:
                    self.assertIs(lead_photo(t), t['cover']['photo'])

    def test_the_threshold_on_built_pages(self):
        # section 10.4, on the page: a 1199 x 1000 cover does not lead (the photo stays in the Photos section), a
        # 1200 x 1000 cover does (it is the hero, and as the report's only photo it leaves no Photos section)
        lead_photo = need(self, self.report, 'lead_photo')
        self.add('syn-edge-under', date='2025-06-16', body=WRITEUP, photos=[photo('photos/01.webp', (1199, 1000), alt='Synthetic photo one')])
        self.add('syn-edge-at', date='2025-06-17', body=WRITEUP, photos=[photo('photos/01.webp', (1200, 1000), alt='Synthetic photo one')])
        under, at = self.by['syn-edge-under'], self.by['syn-edge-at']
        for t in (under, at):
            self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), ('parent', 'photos/01.webp'))
            self.assertIn('p-report--story', self.doc(t['slug']).find('body').classes)
        self.assertIsNone(lead_photo(under))
        main = self.main('syn-edge-under')
        self.assertIsNone(main.by_id('hero'))
        self.assertEqual(main.find_all('figure', cls='rep-hero'), [])
        self.assertEqual(self.gallery_files('syn-edge-under'), [self.photo_href('syn-edge-under', 'photos/01.webp')])
        self.assertEqual(main.by_id('photos').find('div', cls='rep-sh').find('span').text(), '1 PHOTO')
        self.assertIs(lead_photo(at), at['cover']['photo'])
        main = self.main('syn-edge-at')
        self.assertEqual(self.hero('syn-edge-at').find('a')['href'], self.photo_href('syn-edge-at', 'photos/01.webp'))
        self.assertIsNone(main.find(cls='rep-photos'))
        self.assertIs(main.by_id('photos'), self.hero('syn-edge-at').elements()[0])   # section 9: the anchor on the lead photo

    def test_a_square_first_photo_does_not_keep_a_later_landscape_from_leading(self):
        # section 10.4: the automatic cover is the first photo wide enough to lead, so a story whose first photo is square
        # leads with the landscape after it; the square and the other landscape stay in the grid, in order
        slug = 'syn-square-first'
        t = self.add(slug, body=WRITEUP, photos=[photo('photos/01.webp', (1000, 1000), alt='Synthetic photo one'),
                                                 photo('photos/02.webp', (1600, 1200), alt='Synthetic photo two'),
                                                 photo('photos/03.webp', (1600, 900), alt='Synthetic photo three')])
        self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), ('parent', 'photos/02.webp'))
        self.assertIs(need(self, self.report, 'lead_photo')(t), t['photos'][1])
        self.assertEqual(self.hero(slug).find('a')['href'], self.photo_href(slug, 'photos/02.webp'))
        self.assertEqual(self.gallery_files(slug), [self.photo_href(slug, f) for f in ('photos/01.webp', 'photos/03.webp')])
        self.assertEqual(self.main(slug).by_id('photos').find('div', cls='rep-sh').find('span').text(), '2 PHOTOS')
        self.assertEqual([lab for lab, _href in self.toc(slug)], ['Report', 'Photos', 'Route', 'Trip details'])

    def test_near_square_photos_alone_give_a_story_without_a_lead_photo(self):
        # section 10.4: no photo reaches 1.2: the cover is the first that is at least as wide as tall, and it does not lead
        slug = 'syn-near-square'
        t = self.add(slug, body=WRITEUP, photos=[photo('photos/01.webp', (1150, 1000), alt='Synthetic photo one'),
                                                 photo('photos/02.webp', (1100, 1000), alt='Synthetic photo two')])
        self.assertEqual(t['cover']['photo']['file'], 'photos/01.webp')
        self.assertIsNone(need(self, self.report, 'lead_photo')(t))
        self.assertIn('p-report--story', self.doc(slug).find('body').classes)
        self.assertIsNone(self.hero(slug))
        self.assertEqual(self.gallery_files(slug), [self.photo_href(slug, f) for f in ('photos/01.webp', 'photos/02.webp')])

    def test_the_hero_of_the_fixture_stories(self):
        # sections 2.2, 7 and 10.4: the automatic cover (the first photo wide enough to lead), the explicit one, the only photo
        want = {'syn-story': 'photos/02.webp', 'syn-explicit': 'photos/03.webp', 'syn-one': 'photos/01.webp',
                'syn-one-beta': 'photos/01.webp'}
        for slug, file in want.items():
            with self.subTest(slug):
                self.assertEqual(self.hero(slug).find('a')['href'], '../../trips/%s/%s' % (slug, file))

    def test_the_hero_image_is_eager_with_high_fetch_priority(self):
        # section 2.2: core.cover_img(..., eager=True): no lazy loading, fetchpriority high
        for slug in HERO:
            with self.subTest(slug):
                img = self.hero(slug).find('img')
                self.assertIn('cover-img', img.classes)
                self.assertEqual(img['fetchpriority'], 'high')
                self.assertNotIn('loading', img)

    def test_the_hero_image_is_core_cover_img_at_the_hero_sizes(self):
        # section 2.2: core.cover_img(t, here, HERO_SIZES, eager=True), HERO_SIZES = '(min-width: 1200px) 1248px, 100vw'
        self.assertEqual(need(self, self.report, 'HERO_SIZES'), HERO_SIZES)
        for slug in HERO:
            with self.subTest(slug):
                t = self.by[slug]
                self.assertIn(core.cover_img(t, t['url'], HERO_SIZES, eager=True), self.page(slug).html)
        img = self.hero('syn-story').find('img')   # its cover has the .sm copy, so the srcset and sizes are written
        self.assertEqual(img['sizes'], HERO_SIZES)
        self.assertIn('photos/02.sm.webp 800w', img['srcset'])
        self.assertEqual((img['width'], img['height'], img['alt']), ('1600', '1200', 'Synthetic photo two'))

    def test_the_hero_link_joins_the_photo_viewer_group(self):
        # section 2.2: <a class="jph jph--l rep-hero-a" href="…" data-lb-group="photos">
        for slug in HERO:
            with self.subTest(slug):
                a = self.hero(slug).find('a')
                self.assertEqual(a.classes, ['jph', 'jph--l', 'rep-hero-a'])
                self.assertEqual(a['data-lb-group'], 'photos')
                self.assertIs(a.parent, self.hero(slug))

    def test_a_captioned_cover_gets_data_cap_and_a_figcaption(self):
        # section 2.2: data-cap="<caption>" and <figcaption class="t-small"> when the cover photo has a caption
        fig = self.hero('syn-story')
        self.assertEqual(fig.find('a')['data-cap'], CAPTION)
        cap = fig.find('figcaption')
        self.assertIsNotNone(cap)
        self.assertEqual(cap.classes, ['t-small'])
        self.assertEqual(cap.text(), CAPTION)
        self.assertIs(cap.parent, fig)
        self.assertIsNone(fig.find('a').find('figcaption'))   # the caption is not inside the link

    def test_an_uncaptioned_cover_gets_neither(self):
        # section 2.2: the caption attribute and the figcaption only when the cover photo has a caption
        for slug in ('syn-explicit', 'syn-one', 'syn-one-beta'):
            with self.subTest(slug):
                fig = self.hero(slug)
                self.assertNotIn('data-cap', fig.find('a'))
                self.assertIsNone(fig.find('figcaption'))

    def test_the_hero_keeps_the_covers_focal_point(self):
        # section 6: object-fit cover honours the focal point core.cover_img sets
        self.assertEqual(self.hero('syn-explicit').find('img')['style'], 'object-position:30% 60%')
        self.assertNotIn('style', self.hero('syn-one').find('img'))

    def test_the_hero_link_always_has_a_name(self):
        # docs/DEVELOPING.md accessibility rules (not in the contract): a link around an image without alt text needs a
        # name of its own
        for slug in HERO:
            with self.subTest(slug):
                a = self.hero(slug).find('a')
                self.assertTrue(a.find('img')['alt'] or a['aria-label'], 'the lead photo link has no accessible name')

    def test_page_uses_report_hero(self):
        # sections 2.2 and 9: the figure on the page is report.hero(t, here), with photos_anchor=True when the lead photo
        # is the report's only photo
        hero = need(self, self.report, 'hero')
        for slug in HERO:
            with self.subTest(slug):
                try:
                    html_ = hero(self.by[slug], self.here(slug), photos_anchor=slug in ONLY_HERO)
                except TypeError as ex:
                    self.fail('report.hero takes no photos_anchor= argument (contract section 9): %s' % ex)
                self.assertTrue(html_.startswith('<figure class="rep-hero'))
                self.assertEqual(self.page(slug).html.count(html_), 1)

    def test_a_lone_lead_photo_keeps_the_photos_anchor(self):
        # section 9: no Photos section, but the hero figure starts with <span class="rep-anchor" id="photos"></span>, so
        # an old link to trips/<slug>/#photos still lands on the photo
        for slug in ONLY_HERO:
            with self.subTest(slug):
                fig = self.hero(slug)
                span = fig.elements()[0]
                self.assertEqual((span.tag, span.classes, span['id'], span.children), ('span', ['rep-anchor'], 'photos', []))
                self.assertIs(self.main(slug).by_id('photos'), span)
                self.assertEqual([e.tag for e in fig.elements()], ['span', 'a'])
                self.assertEqual(self.page(slug).html.count('<span class="rep-anchor" id="photos"></span>'), 1)

    def test_the_anchor_is_only_there_without_a_gallery(self):
        # section 9: when a gallery exists the id stays on the gallery section and the hero has no anchor span
        for slug in ('syn-story', 'syn-explicit'):
            with self.subTest(slug):
                self.assertIsNone(self.hero(slug).find(cls='rep-anchor'))
                self.assertEqual(self.main(slug).find_all(cls='rep-anchor'), [])
                target = self.main(slug).by_id('photos')
                self.assertEqual((target.tag, target.classes[0]), ('section', 'rep-photos'))
                self.assertEqual(self.hero(slug).elements()[0].tag, 'a')

    def test_hero_has_no_anchor_unless_asked(self):
        # section 9: report.hero(t, here, photos_anchor=True) adds the span; the default (the series cover too) has none
        hero = need(self, self.report, 'hero')
        t = self.by['syn-one']
        plain = hero(t, t['url'])
        self.assertNotIn('rep-anchor', plain)
        self.assertNotIn('id="photos"', plain)
        try:
            anchored = hero(t, t['url'], photos_anchor=True)
        except TypeError as ex:
            self.fail('report.hero takes no photos_anchor= argument (contract section 9): %s' % ex)
        self.assertEqual(anchored, re.sub(r'^(<figure\b[^>]*>)', r'\1<span class="rep-anchor" id="photos"></span>', plain))
        self.assertEqual(plain, hero(t, t['url'], photos_anchor=False))

    def test_no_photos_anchor_on_pages_that_never_had_a_photos_section(self):
        # section 9 covers the story whose only photo is the lead photo; a lone portrait sits in the aside (it never had
        # a Photos section), and a compact page keeps #photos on its gallery or has none
        for slug in ('syn-portrait', 'syn-tall-only', 'syn-words', 'syn-track', 'syn-photos'):
            with self.subTest(slug):
                self.assertEqual(self.main(slug).find_all(cls='rep-anchor'), [])
        self.assertIsNone(self.main('syn-portrait').by_id('photos'))
        self.assertIsNone(self.main('syn-tall-only').by_id('photos'))

    def test_the_anchor_adds_no_photos_item_anywhere(self):
        # section 9: the section row and the bottom bar still list no Photos item on such a page
        for slug in ONLY_HERO:
            with self.subTest(slug):
                self.assertNotIn('#photos', [h for _t, h in self.toc(slug)])
                self.assertNotIn('#photos', [a['href'] for a in self.bbar(slug).find_all('a')])
                self.assertNotIn('Photos', [t for t, _h in self.toc(slug)])

    def test_a_story_with_only_a_hero_still_gets_the_photo_viewer(self):
        # section 2.2: opening the hero shows it in the viewer, so the dialog is on the page even without a gallery
        self.assertIsNotNone(self.doc('syn-one').find('dialog', cls='lb'))
        self.assertIsNone(self.doc('syn-words').find('dialog', cls='lb'))


# ---------------------------------------------------------------- the gallery without the cover

class GalleryTests(ReportFixture):

    def test_the_gallery_excludes_the_cover_and_keeps_the_order(self):
        # section 2.7: every photo of the trip except the cover, in the original order
        self.assertEqual(self.gallery_files('syn-story'),
                         ['../../trips/syn-story/photos/%s.webp' % n for n in ('01', '03', '04')])

    def test_the_gallery_holds_one_photo_fewer_than_the_trip(self):
        # section 7: photo count = n - 1
        for slug in ('syn-story', 'syn-explicit'):
            with self.subTest(slug):
                t = self.by[slug]
                files = self.gallery_files(slug)
                self.assertEqual(len(files), len(t['photos']) - 1)
                self.assertNotIn(self.photo_href(slug, t['cover']['photo']['file']), files)
                self.assertEqual(files, [self.photo_href(slug, p['file']) for p in t['photos'] if p is not t['cover']['photo']])

    def test_the_heading_counts_the_photos_in_the_grid(self):
        # section 2.7 / the task: the Photos heading's count says n - 1
        want = {'syn-story': '3 PHOTOS', 'syn-explicit': '2 PHOTOS', 'syn-two-tall': '2 PHOTOS'}   # no lead photo: both stay
        for slug, text in want.items():
            with self.subTest(slug):
                sec = self.main(slug).by_id('photos')
                self.assertEqual(sec.find('h2').text(), 'Photos')
                self.assertEqual(sec.find('div', cls='rep-sh').find('span').text(), text)

    def unnamed(self, slug='syn-unnamed'):
        """A story of five photos without alt text (landscape, landscape, portrait, portrait, landscape): the first leads."""
        return self.add(slug, body=WRITEUP, photos=[photo('photos/%02d.webp' % i, size, alt='')
                                                    for i, size in enumerate((LANDSCAPE, LANDSCAPE, PORTRAIT, PORTRAIT, LANDSCAPE), 1)])

    def test_unnamed_grid_photos_are_numbered_as_the_viewer_numbers_them(self):
        # section 10.4: under a lead photo a grid photo without alt text is 'Photo <k + 1> of <n + 1>, full size': the
        # viewer counts the lead photo too, so the first grid photo of a five-photo trip is 'Photo 2 of 5'. The heading
        # still counts the grid only
        slug = 'syn-unnamed'
        t = self.unnamed(slug)
        self.assertEqual(t['cover']['photo']['file'], 'photos/01.webp')
        self.assertIsNotNone(self.hero(slug))
        sec = self.main(slug).by_id('photos')
        links = sec.find_all('a', cls='jph')
        self.assertEqual([a['href'] for a in links], [self.photo_href(slug, 'photos/%02d.webp' % i) for i in (2, 3, 4, 5)])
        self.assertEqual([a['aria-label'] for a in links],
                         ['Photo 2 of 5, full size', 'Photo 3 of 5, full size', 'Photo 4 of 5, full size', 'Photo 5 of 5, full size'])
        self.assertEqual(sec.find('div', cls='rep-sh').find('span').text(), '4 PHOTOS')
        # each label is the photo's place in the viewer's group (the lead photo, then the grid in order)
        group = [n for n in self.main(slug).walk() if n.tag == 'a' and 'jph' in n.classes
                 and (n['data-lb-group'] == 'photos' or any(p['data-lb-group'] == 'photos' for p in ancestors(n)))]
        self.assertEqual(len(group), 5)
        self.assertIs(group[0], self.hero(slug).find('a'))
        for place, a in enumerate(group[1:], 2):
            self.assertEqual(a['aria-label'], 'Photo %d of %d, full size' % (place, len(group)))
        # the lead photo has a name of its own, and nothing on the page is called photo 1 of 4 or of 5
        self.assertTrue(group[0]['aria-label'])
        self.assertNotIn(group[0]['aria-label'], [a['aria-label'] for a in links])
        self.assertNotIn('Photo 1 of', self.page(slug).html)
        self.assertNotIn('of 4, full size', self.page(slug).html)

    def test_unnamed_grid_photos_start_at_one_without_a_lead_photo(self):
        # section 10.4: no lead photo, nothing to add: a story whose cover does not lead and a compact photo page count
        # their grid from 'Photo 1 of n'
        self.add('syn-unnamed-tall', date='2025-06-16', body=WRITEUP,
                 photos=[photo('photos/01.webp', PORTRAIT, alt=''), photo('photos/02.webp', PORTRAIT, alt='')])
        self.add('syn-unnamed-compact', date='2025-06-17',
                 photos=[photo('photos/01.webp', LANDSCAPE, alt=''), photo('photos/02.webp', PORTRAIT, alt=''), photo('photos/03.webp', LANDSCAPE, alt='')])
        self.assertIn('p-report--story', self.doc('syn-unnamed-tall').find('body').classes)
        self.assertNotIn('p-report--story', self.doc('syn-unnamed-compact').find('body').classes)
        for slug, n in (('syn-unnamed-tall', 2), ('syn-unnamed-compact', 3)):
            with self.subTest(slug):
                self.assertIsNone(self.hero(slug))
                sec = self.main(slug).by_id('photos')
                self.assertEqual([a['aria-label'] for a in sec.find_all('a', cls='jph')],
                                 ['Photo %d of %d, full size' % (k, n) for k in range(1, n + 1)])
                self.assertEqual(sec.find('div', cls='rep-sh').find('span').text(), '%d PHOTOS' % n)

    def test_a_named_photo_keeps_its_place_in_the_count(self):
        # section 10.4: only a photo without alt text gets the fallback label; the named ones are counted all the same
        slug = 'syn-half-named'
        self.add(slug, body=WRITEUP, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one'), photo('photos/02.webp', LANDSCAPE, alt=''),
                                             photo('photos/03.webp', LANDSCAPE, alt='Synthetic photo three'), photo('photos/04.webp', LANDSCAPE, alt='')])
        links = self.main(slug).by_id('photos').find_all('a', cls='jph')
        self.assertEqual([a['aria-label'] for a in links], ['Photo 2 of 4, full size', None, 'Photo 4 of 4, full size'])
        self.assertEqual([a.find('img')['alt'] for a in links], ['', 'Synthetic photo three', ''])

    def test_lead_is_a_parameter_of_the_rows_and_of_the_gallery(self):
        # section 10.4: core.photo_rows(..., lead=0) and report.gallery(t, here, photos, ns='ph', lead=0): the default
        # numbers the photos it is given; lead=1 moves every number and the total up by one and changes nothing else
        gallery = need(self, self.report, 'gallery')
        t = self.unnamed()
        here, rest = t['url'], t['photos'][1:]

        def labels(html_):
            return [a['aria-label'] for a in Doc(html_).find_all('a', cls='jph')]

        def unnumbered(html_):
            return re.sub(r'Photo \d+ of \d+,', 'Photo,', html_)
        try:
            rows0, rows1 = core.photo_rows(t, here, rest, lead=0), core.photo_rows(t, here, rest, lead=1)
            gal0, gal1 = gallery(t, here, rest, ns='ph', lead=0), gallery(t, here, rest, lead=1)
        except TypeError as ex:
            self.fail('core.photo_rows / report.gallery take no lead= argument (contract section 10.4): %s' % ex)
        self.assertEqual(core.photo_rows(t, here, rest), rows0)
        self.assertEqual(gallery(t, here, rest), gal0)
        for html_ in (rows0, gal0):
            self.assertEqual(labels(html_), ['Photo %d of 4, full size' % k for k in (1, 2, 3, 4)])
        for html_ in (rows1, gal1):
            self.assertEqual(labels(html_), ['Photo %d of 5, full size' % k for k in (2, 3, 4, 5)])
        self.assertEqual(unnumbered(rows1), unnumbered(rows0))
        self.assertEqual(unnumbered(gal1), unnumbered(gal0))
        self.assertIn(core.photo_rows(t, here, rest, ns='ph', lead=1), gal1)
        for html_ in (gal0, gal1):   # the heading counts the grid, whatever the labels say
            self.assertEqual(Doc(html_).find('div', cls='rep-sh').find('span').text(), '4 PHOTOS')
        # the page passes lead=1 when a lead photo sits above the grid
        self.assertEqual(self.page('syn-unnamed').html.count(gal1), 1)
        self.assertNotIn(gal0, self.page('syn-unnamed').html)

    def test_the_gallery_section_joins_the_photo_viewer_group(self):
        # section 2.2: the gallery section carries data-lb-group="photos" too
        for slug in ('syn-story', 'syn-explicit', 'syn-two-tall'):
            with self.subTest(slug):
                sec = self.main(slug).by_id('photos')
                self.assertEqual(sec.tag, 'section')
                self.assertEqual(sec['data-lb-group'], 'photos')

    def test_the_viewer_group_is_the_hero_then_the_gallery_and_counts_every_photo_once(self):
        # section 2.2: PHOTO k / N over all N photos of the trip, hero first, then the gallery in order (base.js groups
        # a.jph[data-lb-group] and the a.jph inside [data-lb-group])
        for slug in ('syn-story', 'syn-explicit', 'syn-one'):
            with self.subTest(slug):
                t = self.by[slug]
                group = [n['href'] for n in self.main(slug).walk()
                         if n.tag == 'a' and 'jph' in n.classes
                         and (n['data-lb-group'] == 'photos' or any(p['data-lb-group'] == 'photos' for p in ancestors(n)))]
                cover = t['cover']['photo']['file']
                rest = [p['file'] for p in t['photos'] if p['file'] != cover]
                self.assertEqual(group, [self.photo_href(slug, f) for f in [cover] + rest])
                self.assertEqual(len(group), len(t['photos']))
                self.assertEqual(len(self.main(slug).find_all('a', cls='jph')), len(t['photos']))   # no photo link outside the group

    def test_the_gallery_is_omitted_when_the_cover_was_the_only_photo(self):
        # sections 2.7 and 7: omitted entirely when none remain (section 9: #photos then names the lead photo's anchor)
        for slug in ONLY_HERO:
            with self.subTest(slug):
                main = self.main(slug)
                self.assertEqual(main.find_all('section', attrs={'id': 'photos'}), [])
                self.assertIsNone(main.find(cls='rep-photos'))
                self.assertIsNone(main.by_id('ph-h'))
                self.assertIsNone(main.find(cls='jrows'))
                self.assertNotIn('0 PHOTO', main.text())
                self.assertEqual(len(main.find_all('a', cls='jph')), 1)   # the hero alone

    def test_an_explicit_cover_that_is_not_the_first_photo_is_the_one_removed(self):
        # section 2.7 / the task: cover_photo names the third photo: it leads the page and leaves the grid; 01 and 02 stay
        t = self.by['syn-explicit']
        self.assertEqual(t['cover']['source'], 'explicit')
        self.assertEqual(self.hero('syn-explicit').find('a')['href'], '../../trips/syn-explicit/photos/03.webp')
        self.assertEqual(self.gallery_files('syn-explicit'),
                         ['../../trips/syn-explicit/photos/01.webp', '../../trips/syn-explicit/photos/02.webp'])

    def test_no_photo_shows_twice_on_a_story(self):
        # plan 9.4: the same image is never both the hero and a gallery item
        for slug in HERO:
            with self.subTest(slug):
                srcs = [i['src'] for i in self.own(slug, 'img') if '/photos/' in (i['src'] or '')]
                self.assertEqual(sorted(srcs), sorted(set(srcs)))
                self.assertEqual(len(srcs), len(self.by[slug]['photos']))

    def test_the_grid_is_the_shared_justified_rows(self):
        # section 2.7: the gallery markup is report.gallery / core.photo_rows over the remaining photos
        t = self.by['syn-story']
        rest = [p for p in t['photos'] if p['file'] != 'photos/02.webp']
        self.assertIn(core.photo_rows(t, t['url'], rest, ns='ph'), self.page('syn-story').html)
        self.assertIn(need(self, self.report, 'gallery')(t, t['url'], rest), self.page('syn-story').html)

    def test_gallery_of_nothing_is_empty(self):
        # section 2.7: omitted when none remain
        t = self.by['syn-one']
        self.assertEqual(need(self, self.report, 'gallery')(t, t['url'], []), '')

    def test_the_compact_gallery_keeps_every_photo(self):
        # section 2, compact layout: unchanged, so a photo-only report shows all its photos in the grid, in order
        self.assertEqual(self.gallery_files('syn-photos'), ['../../trips/syn-photos/photos/%s.webp' % n for n in ('01', '02', '03')])
        sec = self.main('syn-photos').by_id('photos')
        self.assertEqual(sec.find('div', cls='rep-sh').find('span').text(), '3 PHOTOS')
        self.assertEqual(sec['data-lb-group'], 'photos')   # section 2.2: the gallery section carries the group


# ---------------------------------------------------------------- the lone portrait

class LonePortraitTests(ReportFixture):

    def test_a_lone_portrait_story_keeps_the_aside_photo(self):
        # sections 2.7 and 7: the aside is rendered as before (beside the write-up, linked to the full photo, captioned)
        main = self.main('syn-portrait')
        fig = main.find('figure', cls='rep-aside-ph')
        self.assertIsNotNone(fig)
        a = fig.find('a')
        self.assertEqual(a['href'], '../../trips/syn-portrait/photos/01.webp')
        self.assertIn('jph--p', a.classes)
        self.assertEqual(a['data-cap'], CAPTION)
        self.assertEqual(fig.find('figcaption').text(), CAPTION)
        self.assertIn('rep-body--ph', main.find('div', cls='rep-body').classes)
        t = self.by['syn-portrait']
        self.assertIn(need(self, self.report, 'aside_photo')(t, t['url'], t['photos'][0]), self.page('syn-portrait').html)

    def test_a_lone_portrait_story_has_no_hero(self):
        # section 2.7: when the only photo is a portrait there is no cover hero
        main = self.main('syn-portrait')
        self.assertIsNone(main.find(cls='rep-hero'))
        self.assertIsNone(main.by_id('hero'))
        self.assertEqual(self.own('syn-portrait', 'img', cls='cover-img'), [])
        self.assertEqual(len(main.find_all('a', cls='jph')), 1)   # the photo shows once, in the aside

    def test_a_lone_portrait_story_has_no_photos_item_and_no_gallery(self):
        # section 2.7: the toc then has no Photos item
        self.assertEqual(self.toc('syn-portrait'), [('Report', '#report'), ('Route', '#map'), ('Trip details', '#stats')])
        self.assertIsNone(self.main('syn-portrait').by_id('photos'))

    def test_a_lone_portrait_story_is_still_the_story_layout(self):
        # section 2.7: narrative() is still True: the story order without the hero
        self.assertIn('p-report--story', self.doc('syn-portrait').find('body').classes)
        seq = marks(self.main('syn-portrait'))
        self.assertInOrder(seq, ['title', 'stats', '.rep-toc', 'report', '.rep-aside-ph', 'map', '.rep-share', 'rel-h'])

    def test_a_lone_portrait_story_starts_with_view_route(self):
        # section 2.1: the story's title actions
        self.assertEqual([a[0] for a in self.actions('syn-portrait')], ['View route', 'Download GPX', 'copy'])

    def test_a_lone_portrait_without_a_writeup_stays_compact_with_its_aside(self):
        # section 2, compact layout: unchanged
        main = self.main('syn-tall-only')
        self.assertIsNotNone(main.find('figure', cls='rep-aside-ph'))
        self.assertIsNone(main.by_id('photos'))
        self.assertInOrder(marks(main), ['title', 'stats', 'map', '.rep-aside-ph', '.rep-share'])


# ---------------------------------------------------------------- the map caption

class MapCaptionTests(ReportFixture):

    def test_map_caption_starts_with_as_recorded_on_the_date(self):
        # section 2.6: 'As recorded on <Mon D, YYYY>', then 'full track, not trimmed', 'North up'
        t = self.by['syn-story']
        items = ml_items(Doc(need(self, self.report, 'map_caption')(t)))
        self.assertEqual(items[:3], ['As recorded on ' + core.fdate(t['date'], 'short'), 'full track, not trimmed', 'North up'])
        self.assertEqual(items[0], 'As recorded on Jun 1, 2026')

    def test_caption_on_the_story_layout(self):
        # sections 2.6 and 7: 'As recorded on' in the caption on the story layout
        for slug in STORY:
            with self.subTest(slug):
                t = self.by[slug]
                self.assertEqual(self.caption(slug)[:3], ['As recorded on ' + core.fdate(t['date'], 'short'), 'full track, not trimmed', 'North up'])

    def test_caption_on_the_compact_layout(self):
        # section 2 (compact): the map caption's first item is 'As recorded on <date>'
        for slug in ('syn-words', 'syn-photos', 'syn-tall-only', 'syn-track'):
            with self.subTest(slug):
                t = self.by[slug]
                self.assertEqual(self.caption(slug)[:3], ['As recorded on ' + core.fdate(t['date'], 'short'), 'full track, not trimmed', 'North up'])

    def test_caption_keeps_the_credit_line(self):
        # section 2.6: the existing caption otherwise (core.map_caption's terrain / OSM / not-for-navigation credit)
        self.assertEqual(self.caption('syn-story')[3:],
                         ['Terrain: AWS Terrain Tiles', 'Map data © OpenStreetMap contributors', 'Not for navigation'])

    def test_caption_no_longer_opens_with_track(self):
        # section 2.6: the first item reads 'As recorded on …' (it replaces 'Track: <date>')
        for slug in ('syn-story', 'syn-words'):
            self.assertFalse(any(i.startswith('Track:') for i in self.caption(slug)), slug)

    def test_caption_of_an_undated_report_claims_no_date(self):
        # facts only from content (the single-day counterpart of section 10.5): without a date there is no 'As recorded'
        # item of any wording: the caption is 'full track, not trimmed', 'North up', then the credit
        items = self.caption('syn-undated')
        self.assertEqual(items[:2], ['full track, not trimmed', 'North up'])
        self.assertEqual(items, ['full track, not trimmed', 'North up'] + CREDIT)
        self.assertFalse(any('recorded' in i.lower() for i in items), items)
        self.assertNotIn('As recorded', self.page('syn-undated').html)
        self.assertEqual(ml_items(Doc(need(self, self.report, 'map_caption')(self.by['syn-undated']))), items)

    def test_full_screen_map_page_of_an_undated_report_claims_no_date_either(self):
        # the same caption on trips/<slug>/map/
        self.render('syn-undated')
        page = self.report.fullscreen_page(self.by['syn-undated'])
        self.assertEqual(ml_items(Doc(page.html).find('div', cls='mapcap'))[:2], ['full track, not trimmed', 'North up'])
        self.assertNotIn('As recorded', page.html)

    def test_full_screen_map_page_says_the_same(self):
        # section 2.6: one caption (report.map_caption) for the report map and its full-screen page
        t = self.by['syn-story']
        self.render('syn-story')
        page = self.report.fullscreen_page(t)
        self.assertEqual(page.url, 'trips/syn-story/map/')
        self.assertEqual(ml_items(Doc(page.html).find('div', cls='mapcap'))[0], 'As recorded on Jun 1, 2026')

    def test_multi_day_caption_says_as_recorded_and_the_date_range(self):
        # the task (multi-day pages): 'As recorded ' + the date range, then 'full track, not trimmed', 'North up'
        t = self.by['syn-tour']
        doc = Doc(load_module(self, 'sitegen.pages.multiday').page(t, self.site).html)
        items = ml_items(doc.by_id('map').find('div', cls='mapcap'))
        self.assertEqual(items[:3], ['As recorded ' + core.frange(t['date'], t['end_date']), 'full track, not trimmed', 'North up'])
        self.assertEqual(items[0], 'As recorded Mar 10–11, 2026')

    def test_undated_multi_day_caption_has_no_as_recorded_item(self):
        # section 10.5: a multi-day trip without any date: no 'As recorded' item at all (never a dangling 'As recorded'):
        # the items are 'full track, not trimmed', 'North up', then the credit
        multiday = load_module(self, 'sitegen.pages.multiday')
        t = self.add('syn-tour-undated', kind='multi-day', activity='ski', date=None,
                     days=[{'title': 'Synthetic Day One'}, {'title': 'Synthetic Day Two'}])
        self.assertEqual((t['date'], t['end_date'], [d['date'] for d in t['days']]), (None, None, [None, None]))
        page = multiday.page(t, self.site)
        items = ml_items(Doc(page.html).by_id('map').find('div', cls='mapcap'))
        self.assertEqual(items, ['full track, not trimmed', 'North up'] + CREDIT)
        self.assertFalse(any('recorded' in i.lower() for i in items), items)
        self.assertNotIn('As recorded', page.html)

    def test_multi_day_caption_takes_its_dates_from_the_days_when_the_trip_names_none(self):
        # section 10.5 covers a trip without any date; day dates alone still give the range (content: the first and
        # the last day)
        multiday = load_module(self, 'sitegen.pages.multiday')
        t = self.add('syn-tour-day-dates', kind='multi-day', activity='ski', date=None,
                     days=[{'title': 'Synthetic Day One', 'date': '2025-02-03'}, {'title': 'Synthetic Day Two', 'date': '2025-02-04'}])
        items = ml_items(Doc(multiday.page(t, self.site).html).by_id('map').find('div', cls='mapcap'))
        self.assertEqual(items[:3], ['As recorded Feb 3–4, 2025', 'full track, not trimmed', 'North up'])

    def featured_hike(self):
        """A hike marked featured, with a placeholder map and a beta row labelled Track: core.stats_note prints that row
        as 'Track: <value>.' under the strip, which is not the caption's old 'Track: <date>' and stays."""
        t = self.add('syn-featured', featured=True, date='2026-02-10', body=WRITEUP, beta=[{'label': 'Track', 'value': TRACK_NOTE}],
                     photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one')])
        self.render('syn-featured')
        return t

    def test_section_page_featured_caption_opens_as_recorded_on_the_date(self):
        # section 10.5: section pages' featured map caption opens 'As recorded on <Mon D, YYYY>' (was 'Track: <date>')
        section = load_module(self, 'sitegen.pages.section')
        t = self.featured_hike()
        items = ml_items(Doc(need(self, section, 'map_caption')(t)))
        self.assertEqual(items[0], 'As recorded on Feb 10, 2026')
        self.assertEqual(items[:3], ['As recorded on ' + core.fdate(t['date'], 'short'), 'full track, not trimmed', 'North up'])
        self.assertEqual(items[3:], CREDIT)
        page = section.page('hike', self.site)
        feat = Doc(page.html).by_id('main').by_id('featured')
        self.assertEqual(feat.find('h2').text(), t['title'])          # the featured block is this trip's
        caps = feat.find_all('div', cls='mapcap')
        self.assertEqual(len(caps), 1)
        self.assertEqual(ml_items(caps[0])[:3], ['As recorded on Feb 10, 2026', 'full track, not trimmed', 'North up'])
        self.assertEqual(page.html.count(section.map_caption(t)), 1)
        # the same first words as on the report the block links to
        self.assertEqual(ml_items(caps[0])[0], self.caption('syn-featured')[0])

    def test_section_page_featured_caption_of_an_undated_report_claims_no_date(self):
        # facts only from content: the featured caption has no date item when the report has no date
        section = load_module(self, 'sitegen.pages.section')
        items = ml_items(Doc(need(self, section, 'map_caption')(self.by['syn-undated'])))
        self.assertEqual(items, ['full track, not trimmed', 'North up'] + CREDIT)

    def test_no_section_page_says_track_and_a_date(self):
        # section 10.5: nothing on a built section page says 'Track: ' followed by a date. The stats footnote's
        # 'Track: <beta value>.' (core.stats_note) is a different thing and stays
        section = load_module(self, 'sitegen.pages.section')
        t = self.featured_hike()
        for slug in ('syn-photos', 'syn-two-tall'):   # the reports the mountain biking and climbing pages feature
            self.render(slug)
        # the ski page looks for its region maps in <core.ROOT>/rendered/site/meta.json by itself (the other pages go
        # through core's patched copy): point it at the temp dir, which has none, so the real rendered/ is never read
        with mock.patch.object(core, 'ROOT', self.tmp):
            pages = need(self, section, 'build')(self.site)
        self.assertEqual(sorted(p.url for p in pages), sorted(core.section_url(a) for a in core.ACT))
        dated = re.compile(r'Track:\s*(?:[A-Za-z]{3},\s)?[A-Za-z]{3,9}\.?\s\d{1,2},\s\d{4}')   # any core.fdate style
        self.assertIsNotNone(dated.search('Track: Feb 10, 2026'))
        self.assertIsNotNone(dated.search('Track: TUE, FEB 10, 2026'))
        self.assertIsNone(dated.search('Track: %s.' % TRACK_NOTE))
        featured = 0
        for p in pages:
            with self.subTest(p.url):
                main = Doc(p.html).by_id('main')
                text = main.text()
                self.assertIsNone(dated.search(text), dated.search(text) and dated.search(text).group(0))
                for x in self.site['published']:
                    if x['date']:
                        for style in ('short', 'long', 'caps'):
                            self.assertNotIn('Track: ' + core.fdate(x['date'], style), text)
                for cap in main.find_all('div', cls='mapcap'):
                    self.assertFalse(any(i.startswith('Track') for i in ml_items(cap)), ml_items(cap))
                featured += len(main.find_all(attrs={'id': 'featured'}))
        self.assertEqual(featured, 3)   # hiking, climbing and mountain biking each feature a fixture report, with its map
        hiking = Doc(section.page('hike', self.site).html).by_id('main')
        note = hiking.by_id('featured').find('p', cls='strip-note')
        self.assertIn('Track: %s.' % TRACK_NOTE, note.text())
        self.assertIn(core.stats_note(t), section.page('hike', self.site).html)

    def test_goal_caption_is_unchanged(self):
        # section 2: goal pages are not changed: a planned line was never recorded
        items = ml_items(Doc(self.report.map_caption(self.by['syn-goal'])))
        self.assertEqual(items[:2], ['Planned route, not a recorded track', 'North up'])
        self.assertFalse(any('As recorded' in i for i in items))


# ---------------------------------------------------------------- title actions

class TitleActionTests(ReportFixture):

    def test_story_actions_are_view_route_download_gpx_copy_link(self):
        # section 2.1: View route (#map), the Download GPX ink button, the copy-link control, in this order
        for slug in STORY:
            with self.subTest(slug):
                self.assertEqual(self.actions(slug), [('View route', '#map'), ('Download GPX', slug + '.gpx'),
                                                      ('copy', core.SITE_URL + 'trips/%s/' % slug)])

    def test_story_has_no_read_the_report_button(self):
        # section 2.1: no 'Read the report' button on the story layout
        for slug in STORY:
            self.assertNotIn('Read the report', self.page(slug).html, slug)

    def test_view_route_is_a_plain_button_link(self):
        # section 2.1: <a class="btn" href="#map">View route</a>
        a = self.main('syn-story').find('div', cls='rep-actions').find('a', attrs={'href': '#map'})
        self.assertEqual(a.classes, ['btn'])
        self.assertEqual(a.text(), 'View route')

    def test_compact_actions_with_a_writeup(self):
        # section 2 (compact): 'Read the report' when there is a write-up, then 'Download GPX', then the copy-link control
        self.assertEqual(self.actions('syn-words'), [('Read the report', '#report'), ('Download GPX', 'syn-words.gpx'),
                                                     ('copy', core.SITE_URL + 'trips/syn-words/')])

    def test_compact_actions_without_a_writeup(self):
        # section 2 (compact): 'Download GPX', then the copy-link control; nothing points at a report that is not there
        for slug in ('syn-photos', 'syn-tall-only', 'syn-track', 'syn-undated'):
            with self.subTest(slug):
                self.assertEqual(self.actions(slug), [('Download GPX', slug + '.gpx'), ('copy', core.SITE_URL + 'trips/%s/' % slug)])

    def test_compact_pages_have_no_view_route_button(self):
        # section 2 (compact): unchanged; the map is already the first thing under the strip
        for slug in COMPACT:
            self.assertNotIn('View route', self.page(slug).html, slug)

    def test_download_gpx_is_unchanged(self):
        # hard rule + section 2.1: <a class="btn btn--ink" href="<slug>.gpx" download> on both layouts
        for slug in SINGLE:
            with self.subTest(slug):
                dl = [a for a in self.main(slug).find('div', cls='rep-actions').find_all('a') if a.text() == 'Download GPX']
                self.assertEqual(len(dl), 1)
                self.assertEqual(dl[0].classes, ['btn', 'btn--ink'])
                self.assertEqual(dl[0]['href'], slug + '.gpx')
                self.assertIn('download', dl[0])

    def test_the_copy_link_action_is_the_button_form_of_core_copy_link(self):
        # section 4: the last title action on single-day pages is core.copy_link(core.SITE_URL + here) (cls 'btn', 'Copy link')
        copy_link = need(self, core, 'copy_link')
        for slug in SINGLE:
            with self.subTest(slug):
                box = self.main(slug).find('div', cls='rep-actions')
                last = box.elements()[-1]
                self.assertEqual((last.tag, last.classes), ('span', ['copy']))
                btn = last.find('button')
                self.assertEqual(btn.classes, ['btn', 'copy-btn'])
                self.assertEqual(btn.text(), 'Copy link')
                self.assertEqual(btn['data-copy'], core.SITE_URL + 'trips/%s/' % slug)
                self.assertIn('<div class="rep-actions">', self.page(slug).html)
                self.assertIn(copy_link(core.SITE_URL + self.here(slug)) + '</div>', self.page(slug).html)


# ---------------------------------------------------------------- the phone share row (report.share_row)

class ShareRowTests(ReportFixture):

    def setUp(self):
        super().setUp()
        self.share_row = need(self, self.report, 'share_row')

    def test_markup(self):
        # section 2 (both layouts): <div class="wrap rep-share"> holding core.copy_link(SITE_URL + here, 'Copy link to this
        # page', cls='alink')
        here = 'trips/syn-story/'
        self.assertEqual(self.share_row(here), '<div class="wrap rep-share">%s</div>'
                         % need(self, core, 'copy_link')(core.SITE_URL + here, 'Copy link to this page', cls='alink'))

    def test_the_row_holds_one_text_link_button_for_this_page(self):
        # section 4: the phone share row uses cls='alink' and 'Copy link to this page', with the absolute page URL
        row = Doc(self.share_row('trips/syn-story/')).find('div')
        self.assertEqual(row.classes, ['wrap', 'rep-share'])
        btns = row.find_all('button')
        self.assertEqual(len(btns), 1)
        self.assertEqual(btns[0].classes, ['alink', 'copy-btn'])
        self.assertEqual(btns[0].text(), 'Copy link to this page')
        self.assertEqual(btns[0]['data-copy'], core.SITE_URL + 'trips/syn-story/')
        self.assertEqual(row.find('span', cls='copy-msg')['role'], 'status')

    def test_every_single_day_page_has_one_share_row(self):
        # section 2 (both layouts): the share row is in the markup of both layouts, at every width
        for slug in SINGLE:
            with self.subTest(slug):
                self.assertEqual(self.page(slug).html.count(self.share_row(self.here(slug))), 1)
                self.assertEqual(len(self.main(slug).find_all('div', cls='rep-share')), 1)

    def test_the_row_sits_after_the_gallery_and_before_the_related_block(self):
        # section 2 (both layouts): placed after the gallery and before the related block (and so before the pager)
        for slug in ('syn-story', 'syn-explicit', 'syn-photos'):
            with self.subTest(slug):
                self.assertInOrder(marks(self.main(slug)), ['photos', '.rep-share', '.rep-related', 'rel-h'])
        self.assertInOrder(marks(self.main('syn-story')), ['.rep-share', '.rep-related', '.pager'])

    def test_the_row_follows_the_last_section_when_there_is_no_gallery(self):
        # section 2 (both layouts): story without a gallery: after the map; compact without one: after the write-up
        self.assertInOrder(marks(self.main('syn-one')), ['report', 'map', '.rep-share', '.rep-related'])
        self.assertInOrder(marks(self.main('syn-words')), ['map', 'report', '.rep-share', '.rep-related'])
        self.assertInOrder(marks(self.main('syn-track')), ['map', '.rep-share', '.rep-related'])

    def test_a_single_day_page_has_two_copy_controls_for_the_same_url(self):
        # section 4: the title action and the phone share row, both for the page's own URL
        for slug in SINGLE:
            with self.subTest(slug):
                btns = self.doc(slug).find_all('button', cls='copy-btn')
                self.assertEqual([b['data-copy'] for b in btns], [core.SITE_URL + 'trips/%s/' % slug] * 2)
                self.assertEqual([b.text() for b in btns], ['Copy link', 'Copy link to this page'])

    def test_no_copy_control_sits_inside_noscript(self):
        # section 4: the control is not rendered inside <noscript>
        for slug in ('syn-story', 'syn-words'):
            for b in self.doc(slug).find_all('button', cls='copy-btn'):
                self.assertFalse(any(p.tag == 'noscript' for p in ancestors(b)), slug)

    def test_every_copy_control_has_its_empty_status_and_no_field(self):
        # section 10.1, on the built pages: each .copy holds the button and, right after it, its always-rendered, empty
        # role="status" element; the fallback field is not in the static markup (base.js appends its .copy-pop)
        docs = {slug: self.doc(slug) for slug in SINGLE + ['syn-goal']}
        docs['syn-tour'] = Doc(load_module(self, 'sitegen.pages.multiday').page(self.by['syn-tour'], self.site).html)
        for slug, doc in docs.items():
            with self.subTest(slug):
                boxes = doc.find_all('span', cls='copy')
                self.assertEqual(len(boxes), 2)                                   # the title action and the phone share row
                for box in boxes:
                    btn, msg = box.elements()
                    self.assertEqual((btn.tag, btn['type']), ('button', 'button'))
                    self.assertEqual((msg.tag, msg.classes, msg['role'], msg.children), ('span', ['copy-msg', 't-small'], 'status', []))
                    self.assertNotIn('hidden', msg)
                self.assertEqual(len(doc.find_all(attrs={'role': 'status'})), 2)
                self.assertEqual(doc.find_all('input', cls='copy-url'), [])
                self.assertEqual(doc.find_all(cls='copy-pop'), [])
                names = [b.text() for b in doc.find_all('button', cls='copy-btn')]
                self.assertEqual(len(set(names)), len(names))                      # each control has its own name


# ---------------------------------------------------------------- the phone bottom bar (report.bottom_bar)

class BottomBarTests(ReportFixture):

    def bar(self, has_beta, has_report, has_gallery, chart='', **kw):
        t = self.by['syn-story']
        return self.report.bottom_bar(t, t['url'], 'syn-story.gpx', has_beta, has_report, has_gallery, chart, **kw)

    def story(self, has_beta, has_gallery, chart=''):
        try:
            html_ = self.bar(has_beta, True, has_gallery, chart, story=True)
        except TypeError as ex:
            self.fail('report.bottom_bar takes no story= argument (contract section 2, phone bottom bar): %s' % ex)
        return bar_items(Doc(html_).find('nav'))

    def test_story_with_a_gallery(self):
        # section 2 (bottom bar), case 1: gallery present -> Report · Map · Photos · GPX
        gpx = ('GPX', 'syn-story.gpx')
        self.assertEqual(self.story(False, True), [REPORT, MAP, PHOTOS, gpx])
        self.assertEqual(self.story(True, True), [REPORT, MAP, PHOTOS, gpx])            # the gallery leads, beta or not
        self.assertEqual(self.story(True, True, 'profile'), [REPORT, MAP, PHOTOS, gpx])  # and chart or not
        self.assertEqual(self.story(False, True, 'speed'), [REPORT, MAP, PHOTOS, gpx])

    def test_story_without_a_gallery_with_beta(self):
        # section 2 (bottom bar), case 2: no gallery and beta -> Beta · Report · Map · GPX
        gpx = ('GPX', 'syn-story.gpx')
        self.assertEqual(self.story(True, False), [BETA_ITEM, REPORT, MAP, gpx])
        self.assertEqual(self.story(True, False, 'profile'), [BETA_ITEM, REPORT, MAP, gpx])

    def test_story_without_a_gallery_or_beta_with_a_profile(self):
        # section 2 (bottom bar), case 3: no gallery, no beta -> Report · Map · Profile · GPX when the chart exists
        self.assertEqual(self.story(False, False, 'profile'), [REPORT, MAP, PROFILE, ('GPX', 'syn-story.gpx')])

    def test_story_without_a_gallery_or_beta_with_a_speed_chart(self):
        # section 2 (bottom bar), case 4: the flat-water chart is named Speed and is still #profile
        self.assertEqual(self.story(False, False, 'speed'), [REPORT, MAP, SPEED, ('GPX', 'syn-story.gpx')])

    def test_story_without_a_gallery_beta_or_chart(self):
        # section 2 (bottom bar), case 5: ... else Stats · GPX
        self.assertEqual(self.story(False, False), [REPORT, MAP, STATS, ('GPX', 'syn-story.gpx')])

    def test_story_bar_markup(self):
        # section 2 (bottom bar): <nav class="bbar" aria-label="Report sections" style="--n:4"> as today, four items in
        # every story case, the GPX item a download
        for has_beta, has_gallery, chart in ((False, True, ''), (True, True, 'profile'), (True, False, ''), (False, False, 'profile'),
                                             (False, False, 'speed'), (False, False, '')):
            with self.subTest(has_beta=has_beta, has_gallery=has_gallery, chart=chart):
                nav = Doc(self.bar(has_beta, True, has_gallery, chart, story=True)).find('nav')
                self.assertEqual((nav.classes, nav['aria-label'], nav['style']), (['bbar'], 'Report sections', '--n:4'))
                links = nav.find_all('a')
                self.assertEqual(len(links), 4)
                self.assertEqual([('download' in a) for a in links], [False, False, False, True])
                for a in links:
                    self.assertIsNotNone(a.find('svg'), 'a bottom-bar item has no icon')

    def test_story_defaults_to_false(self):
        # section 2 (bottom bar): report.bottom_bar(..., story=False)
        for args in ((True, True, False, ''), (False, True, True, 'profile'), (False, False, True, '')):
            self.assertEqual(self.bar(*args), self.bar(*args, story=False))

    def test_compact_bar_is_unchanged(self):
        # section 2 (bottom bar): the compact layout is unchanged: byte for byte what the bar was before Phase 3, for
        # every combination of beta, report, gallery and chart
        t = self.by['syn-story']
        for has_beta in (True, False):
            for has_report in (True, False):
                for has_gallery in (True, False):
                    for chart in ('', 'profile', 'speed'):
                        with self.subTest(beta=has_beta, report=has_report, gallery=has_gallery, chart=chart):
                            self.assertEqual(self.bar(has_beta, has_report, has_gallery, chart, story=False),
                                             legacy_bar(t, 'syn-story.gpx', has_beta, has_report, has_gallery, chart))

    def test_compact_bar_cases(self):
        # section 2 (bottom bar): Map · Beta | Profile/Speed | Stats · Report | Photos · GPX
        gpx = ('GPX', 'syn-story.gpx')
        cases = [((True, True, False, ''), [MAP, BETA_ITEM, REPORT, gpx]),
                 ((True, False, True, 'profile'), [MAP, BETA_ITEM, PHOTOS, gpx]),
                 ((False, True, False, 'profile'), [MAP, PROFILE, REPORT, gpx]),
                 ((False, False, True, 'speed'), [MAP, SPEED, PHOTOS, gpx]),
                 ((False, True, False, ''), [MAP, STATS, REPORT, gpx]),
                 ((False, False, False, ''), [MAP, STATS, gpx])]
        for args, want in cases:
            with self.subTest(args=args):
                nav = Doc(self.bar(*args)).find('nav')
                self.assertEqual(bar_items(nav), want)
                self.assertEqual(nav['style'], '--n:%d' % len(want))

    def test_story_pages_with_a_gallery(self):
        # section 7: bottom bar order on the story layout, on the page itself (case 1)
        for slug in ('syn-story', 'syn-explicit', 'syn-two-tall'):
            with self.subTest(slug):
                self.assertEqual(bar_items(self.bbar(slug)), [REPORT, MAP, PHOTOS, ('GPX', slug + '.gpx')])

    def test_story_page_without_a_gallery_with_beta(self):
        # case 2 on the page
        self.assertEqual(bar_items(self.bbar('syn-one-beta')), [BETA_ITEM, REPORT, MAP, ('GPX', 'syn-one-beta.gpx')])

    def test_story_page_without_a_gallery_or_beta(self):
        # cases 3, 4 and 5 on the page: the rendered chart decides (report.has_chart)
        self.assertEqual(bar_items(self.bbar('syn-one')), [REPORT, MAP, STATS, ('GPX', 'syn-one.gpx')])
        self.render('syn-one', chart='profile')
        self.assertEqual(bar_items(self.bbar('syn-one')), [REPORT, MAP, PROFILE, ('GPX', 'syn-one.gpx')])
        self.assertIsNotNone(self.doc('syn-one').by_id('profile'))
        self.render('syn-one', chart='speed')
        self.assertEqual(bar_items(self.bbar('syn-one')), [REPORT, MAP, SPEED, ('GPX', 'syn-one.gpx')])
        self.assertEqual(self.doc('syn-one').by_id('profile').find('h2').text(), 'Speed')

    def test_lone_portrait_story_page(self):
        # the lone portrait is not a gallery: cases 3-5 apply
        self.assertEqual(bar_items(self.bbar('syn-portrait')), [REPORT, MAP, STATS, ('GPX', 'syn-portrait.gpx')])

    def test_compact_pages(self):
        # section 2 (bottom bar): the compact layout is unchanged, on the page itself
        want = {'syn-words': [MAP, BETA_ITEM, REPORT], 'syn-photos': [MAP, STATS, PHOTOS], 'syn-tall-only': [MAP, STATS],
                'syn-track': [MAP, STATS]}
        for slug, items in want.items():
            with self.subTest(slug):
                self.assertEqual(bar_items(self.bbar(slug)), items + [('GPX', slug + '.gpx')])
        self.render('syn-track', chart='profile')
        self.assertEqual(bar_items(self.bbar('syn-track')), [MAP, PROFILE, ('GPX', 'syn-track.gpx')])

    def test_one_bottom_bar_outside_main(self):
        # plan 9.2: the existing phone bottom navigation is adapted, not joined by a second bar
        for slug in ('syn-story', 'syn-words'):
            with self.subTest(slug):
                self.assertEqual(len(self.doc(slug).find_all('nav', cls='bbar')), 1)
                self.assertIsNone(self.main(slug).find('nav', cls='bbar'))

    def test_the_page_passes_its_layout_to_the_bar(self):
        # section 2 (bottom bar): the page's bar is bottom_bar(..., story=narrative(t))
        t = self.by['syn-story']
        self.assertIn(self.report.bottom_bar(t, t['url'], 'syn-story.gpx', True, True, True, '', story=True), self.page('syn-story').html)
        t = self.by['syn-words']
        self.assertIn(self.report.bottom_bar(t, t['url'], 'syn-words.gpx', True, True, False, ''), self.page('syn-words').html)


# ---------------------------------------------------------------- the head: what is preloaded, the share image

class HeadTests(ReportFixture):

    def test_a_story_with_a_hero_preloads_the_cover(self):
        # section 2.2: the hero is the page's preloaded image (core.cover_preload(t, here, HERO_SIZES))
        need(self, core, 'cover_preload')
        for slug in HERO:
            with self.subTest(slug):
                self.render(slug)
                t = self.by[slug]
                links = self.preloads(slug)
                self.assertEqual([l['href'] for l in links], [self.photo_href(slug, t['cover']['photo']['file'])])
                self.assertEqual(links[0]['fetchpriority'], 'high')
                self.assertIn(core.cover_preload(t, t['url'], HERO_SIZES), self.head_html(slug))

    def test_the_cover_preload_carries_the_hero_sizes(self):
        # section 2.2: the preload matches the <img> (same srcset, imagesizes = HERO_SIZES)
        link = self.preloads('syn-story')[0]
        img = self.hero('syn-story').find('img')
        self.assertEqual(link['imagesizes'], HERO_SIZES)
        self.assertEqual(link['imagesrcset'], img['srcset'])
        self.assertEqual(link['href'], img['src'])

    def test_a_story_with_a_hero_drops_the_map_preloads(self):
        # section 2.2: the map preloads are dropped and the map block is not eager (the map is below the fold)
        self.render('syn-story')
        self.assertFalse([l['href'] for l in self.preloads('syn-story') if '/map/' in l['href']])
        imgs = self.main('syn-story').by_id('map').find_all('img')
        self.assertEqual(len(imgs), 6)   # hillshade + base layer for each of the three renders
        for img in imgs:
            self.assertNotIn('fetchpriority', img)
            self.assertEqual(img['loading'], 'lazy')

    def test_a_compact_page_preloads_the_map(self):
        # section 2 (compact): unchanged: core.map_preloads in the head, the map block eager
        for slug in ('syn-words', 'syn-photos', 'syn-track'):
            with self.subTest(slug):
                self.render(slug)
                t = self.by[slug]
                want = core.map_preloads(t, t['url'], [('map-wide', 'wide'), ('map-col', 'col'), ('map-phone', 'phone')], t['url'] + 'map/')
                self.assertTrue(want)
                self.assertIn(want, self.head_html(slug))
                hrefs = [l['href'] for l in self.preloads(slug)]
                self.assertEqual(len(hrefs), 6)
                self.assertTrue(all(h.startswith('../../trips/%s/map/' % slug) for h in hrefs), hrefs)
                for img in self.main(slug).by_id('map').find_all('img'):
                    self.assertEqual(img['fetchpriority'], 'high')

    def test_a_lone_portrait_story_preloads_the_map(self):
        # section 2.2 / the task: the cover is preloaded on story pages with a hero, the map otherwise
        self.render('syn-portrait')
        hrefs = [l['href'] for l in self.preloads('syn-portrait')]
        self.assertEqual(len(hrefs), 6)
        self.assertTrue(all(h.startswith('../../trips/syn-portrait/map/') for h in hrefs), hrefs)
        for img in self.main('syn-portrait').by_id('map').find_all('img'):
            self.assertEqual(img['fetchpriority'], 'high')

    def test_only_one_image_family_is_marked_high_priority(self):
        # section 2.2: one lead image per page: the hero on a story, the map elsewhere, never both
        self.render('syn-story')
        self.render('syn-words')
        story = [i for i in self.main('syn-story').find_all('img') if i['fetchpriority'] == 'high']
        self.assertEqual([i.classes for i in story], [['cover-img']])
        compact = [i for i in self.main('syn-words').find_all('img') if i['fetchpriority'] == 'high']
        self.assertTrue(compact and all(c.classes[0] in ('mv-hs', 'mv-base') for c in compact))

    def test_og_image_is_the_cover_on_story_pages(self):
        # section 10.4: the share image is the cover whenever the trip has one, whether or not the cover leads the page.
        # In syn-one, syn-two-tall and syn-portrait the cover is also the first photo; syn-story (automatic) and
        # syn-explicit (cover_photo) lead with a cover that is not, and the tests below cover the stories without a
        # lead photo
        want = {'syn-story': 'photos/02.webp', 'syn-explicit': 'photos/03.webp', 'syn-one': 'photos/01.webp',
                'syn-two-tall': 'photos/01.webp', 'syn-portrait': 'photos/01.webp'}
        for slug, file in want.items():
            with self.subTest(slug):
                self.assertEqual(self.og_image(slug), core.SITE_URL + 'trips/%s/%s' % (slug, file))
                self.assertEqual(self.og_image(slug), core.SITE_URL + self.here(slug) + self.by[slug]['cover']['photo']['file'])
        for slug in ('syn-story', 'syn-explicit'):
            self.assertNotEqual(self.by[slug]['cover']['photo']['file'], self.by[slug]['photos'][0]['file'], slug)
            self.assertNotEqual(self.og_image(slug), core.SITE_URL + self.here(slug) + self.by[slug]['photos'][0]['file'])

    def assertSharesCover(self, slug, file, story, hero=False):
        """The page's og:image is trips/<slug>/<file>, which is the trip's cover and not its first photo; one og:image."""
        t = self.by[slug]
        self.assertEqual(t['cover']['photo']['file'], file)
        self.assertNotEqual(t['photos'][0]['file'], file)
        self.assertEqual('p-report--story' in self.doc(slug).find('body').classes, story)
        self.assertEqual(self.hero(slug) is not None, hero)
        self.assertEqual(self.og_image(slug), core.SITE_URL + 'trips/%s/%s' % (slug, file))
        self.assertEqual(len(self.doc(slug).find('head').find_all('meta', attrs={'property': 'og:image'})), 1)

    def test_og_image_is_a_portrait_cover_that_does_not_lead(self):
        # section 10.4: cover_photo names a portrait that is not the first photo: the story has no lead photo (section 9)
        # and its share image is still that cover, the photo its cards show
        self.add('syn-tall-cover', date='2025-06-16', body=WRITEUP, cover_photo='photos/02.webp',
                 photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one'), photo('photos/02.webp', PORTRAIT, alt='Synthetic photo two')])
        self.add('syn-tall-pair', date='2025-06-17', body=WRITEUP, cover_photo='photos/02.webp',
                 photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic photo one'), photo('photos/02.webp', PORTRAIT, alt='Synthetic photo two')])
        for slug in ('syn-tall-cover', 'syn-tall-pair'):
            with self.subTest(slug):
                self.assertEqual(self.by[slug]['cover']['source'], 'explicit')
                self.assertIsNone(need(self, self.report, 'lead_photo')(self.by[slug]))
                self.assertSharesCover(slug, 'photos/02.webp', story=True)
                self.assertEqual(len(self.gallery_files(slug)), 2)   # both photos stay in the Photos section

    def test_og_image_is_a_square_cover_that_does_not_lead(self):
        # section 10.4: two portraits, then a square: the square is the cover (the first photo at least as wide as tall)
        # and the share image, though it cannot lead the page
        self.add('syn-square-last', body=WRITEUP, photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic photo one'),
                                                          photo('photos/02.webp', PORTRAIT, alt='Synthetic photo two'),
                                                          photo('photos/03.webp', (1000, 1000), alt='Synthetic photo three')])
        self.assertEqual(self.by['syn-square-last']['cover']['source'], 'parent')
        self.assertSharesCover('syn-square-last', 'photos/03.webp', story=True)

    def test_og_image_is_the_cover_that_leads_after_a_square_first_photo(self):
        # section 10.4: the automatic cover of [square, landscape, landscape] is the second photo: hero and share image
        self.add('syn-square-first', body=WRITEUP, photos=[photo('photos/01.webp', (1000, 1000), alt='Synthetic photo one'),
                                                           photo('photos/02.webp', (1600, 1200), alt='Synthetic photo two'),
                                                           photo('photos/03.webp', (1600, 900), alt='Synthetic photo three')])
        self.assertSharesCover('syn-square-first', 'photos/02.webp', story=True, hero=True)

    def test_og_image_is_the_cover_on_a_compact_page(self):
        # section 10.4: story and compact: a photo report without a write-up shares its cover too, automatic (the first
        # landscape, after a portrait) or named by cover_photo
        self.add('syn-compact-cover', date='2025-06-16',
                 photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic photo one'), photo('photos/02.webp', LANDSCAPE, alt='Synthetic photo two')])
        self.add('syn-compact-named', date='2025-06-17', cover_photo='photos/03.webp',
                 photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one'), photo('photos/02.webp', LANDSCAPE, alt='Synthetic photo two'),
                         photo('photos/03.webp', PORTRAIT, alt='Synthetic photo three')])
        self.assertEqual((self.by['syn-compact-cover']['cover']['source'], self.by['syn-compact-named']['cover']['source']), ('parent', 'explicit'))
        self.assertSharesCover('syn-compact-cover', 'photos/02.webp', story=False)
        self.assertSharesCover('syn-compact-named', 'photos/03.webp', story=False)

    def test_og_image_on_compact_pages(self):
        # section 10.4 (compact): the cover when the report has a photo (here also its first photo), none otherwise.
        # 'Else the first photo' cannot be reached on a report: content.resolve_cover gives every trip with a photo a cover
        self.assertEqual(self.og_image('syn-photos'), core.SITE_URL + 'trips/syn-photos/photos/01.webp')
        self.assertEqual(self.og_image('syn-tall-only'), core.SITE_URL + 'trips/syn-tall-only/photos/01.webp')
        for slug in ('syn-words', 'syn-track', 'syn-undated'):
            self.assertIsNone(self.by[slug]['cover'], slug)
            self.assertIsNone(self.og_image(slug), slug)
        for slug in SINGLE:   # a cover and a share image go together on every fixture page
            self.assertEqual(self.og_image(slug) is not None, self.by[slug]['cover'] is not None, slug)


# ---------------------------------------------------------------- goal pages and multi-day pages

class GoalPageTests(ReportFixture):

    def test_copy_link_is_the_last_title_action(self):
        # section 2 (goal pages) / section 4: the copy-link control is the last title action (cls 'btn', 'Copy link')
        self.assertEqual(self.actions('syn-goal'), [('Planning notes', '#report'), ('Download planned GPX', 'syn-goal.gpx'),
                                                    ('copy', core.SITE_URL + 'trips/syn-goal/')])
        btn = self.main('syn-goal').find('div', cls='rep-actions').find('button')
        self.assertEqual(btn.classes, ['btn', 'copy-btn'])
        self.assertEqual(btn.text(), 'Copy link')

    def test_a_goal_without_notes_or_a_route_still_gets_the_copy_link(self):
        # section 4: the last title action on goal pages, whatever else the goal has
        helpers.make_trip(self.tmp, 'syn-idea', title='Synthetic Idea', activity='hike', kind='planned', region=REGION)
        t = helpers.load(self.tmp, 'syn-idea')
        doc = Doc(self.report.page(t, self.site).html)
        box = doc.by_id('main').find('div', cls='rep-actions')
        self.assertEqual([e.tag for e in box.elements()], ['span'])
        self.assertEqual(box.find('button')['data-copy'], core.SITE_URL + 'trips/syn-idea/')

    def test_share_row_sits_before_the_goal_pager(self):
        # section 2 (goal pages): the share row sits before the goal pager
        main = self.main('syn-goal')
        self.assertEqual(self.page('syn-goal').html.count(need(self, self.report, 'share_row')('trips/syn-goal/')), 1)
        seq = marks(main)
        self.assertInOrder(seq, ['title', 'map', 'report', '.rep-share', '.pager'])
        self.assertEqual(main.find('nav', cls='pager')['aria-label'], 'More goals')
        self.assertEqual(seq.count('.rep-share'), 1)

    def test_goal_page_has_no_hero_section_row_or_related_block(self):
        # section 2 (goal pages): no hero, no section row, no related block
        main = self.main('syn-goal')
        self.assertIsNone(main.find(cls='rep-hero'))
        self.assertIsNone(main.by_id('hero'))
        self.assertIsNone(main.find('nav', cls='rep-toc'))
        self.assertIsNone(main.find(cls='rep-related'))
        self.assertIsNone(main.by_id('rel-h'))
        self.assertNotIn('More like this', main.text())

    def test_goal_page_is_built_by_goal_page(self):
        # section 2: report.page hands a planned trip to report.goal_page
        goal_page = need(self, self.report, 'goal_page')
        self.assertEqual(goal_page(self.by['syn-goal'], self.site).html, self.page('syn-goal').html)
        self.assertEqual(self.doc('syn-goal').find('body').classes, ['p-report', 'p-goal'])

    def test_goal_page_keeps_its_wording(self):
        # section 2: goal pages are not otherwise changed (Planning notes, never Trip report; no 'View route')
        html_ = self.page('syn-goal').html
        self.assertIn('Planning notes', html_)
        self.assertNotIn('Trip report', html_)
        self.assertNotIn('View route', html_)
        self.assertNotIn('As recorded', html_)


class MultiDayPageTests(ReportFixture):

    def setUp(self):
        super().setUp()
        self.multiday = load_module(self, 'sitegen.pages.multiday')
        self.mpage = self.multiday.page(self.by['syn-tour'], self.site)
        self.mdoc = Doc(self.mpage.html)
        self.mmain = self.mdoc.by_id('main')

    def test_copy_link_is_the_last_title_action(self):
        # section 2 (multi-day pages) / section 4: the copy-link control is the last title action
        box = self.mmain.find('div', cls='rep-actions')
        els = box.elements()
        self.assertEqual([(e.tag, e.text()) for e in els[:-1]], [('a', 'Day by day'), ('a', 'Download all GPX')])
        self.assertEqual((els[-1].tag, els[-1].classes), ('span', ['copy']))
        btn = els[-1].find('button')
        self.assertEqual(btn.classes, ['btn', 'copy-btn'])
        self.assertEqual(btn.text(), 'Copy link')
        self.assertEqual(btn['data-copy'], core.SITE_URL + 'trips/syn-tour/')

    def test_existing_actions_and_gpx_are_unchanged(self):
        # hard rule: every URL and GPX download unchanged
        box = self.mmain.find('div', cls='rep-actions')
        dl = [a for a in box.find_all('a') if a.text() == 'Download all GPX'][0]
        self.assertEqual(dl['href'], 'syn-tour.gpx')
        self.assertIn('download', dl)
        self.assertEqual(self.mpage.url, 'trips/syn-tour/')

    def test_tick_backlink_follows_the_title_block(self):
        # section 2 (multi-day pages): report.tick_backlink follows the title block
        seq = marks(self.mmain)
        self.assertInOrder(seq, ['title', '.rep-tick', 'stats', 'map'])
        self.assertEqual(seq[seq.index('title') + 1], '.rep-tick')

    def test_related_block_sits_before_the_pager(self):
        # section 2 (multi-day pages) / sections 3 and 10.3: the related block, built without the two reports of the
        # pager (core.related_block(t, here, site, skip=report.neighbours(t, site))), sits before the pager
        t = self.by['syn-tour']
        neighbours = need(self, self.report, 'neighbours')
        self.assertEqual([x and x['slug'] for x in neighbours(t, self.site)], ['syn-explicit', None])   # the other ski report
        related_block = need(self, core, 'related_block')
        block = related_block(t, 'trips/syn-tour/', self.site, skip=neighbours(t, self.site))
        self.assertTrue(block)
        self.assertEqual(self.mpage.html.count(block), 1)
        self.assertEqual(len(self.mmain.find_all('section', cls='rep-related')), 1)
        cards = [c['data-slug'] for c in self.mmain.find('ul', cls='rep-rel').find_all('li', cls='tcard')]
        self.assertEqual(len(cards), 3)
        self.assertNotIn('syn-explicit', cards)                       # by the rule alone it would be the first card
        self.assertIn('data-slug="syn-explicit"', related_block(t, 'trips/syn-tour/', self.site))
        self.assertInOrder(marks(self.mmain), ['title', 'map', 'days-h', '.rep-related', 'rel-h'])
        helpers.make_trip(self.tmp, 'syn-ski-two', title='Synthetic Second Ski', activity='ski', date='2026-01-05', region=REGION, track=True)
        self.load_site()
        main = Doc(self.multiday.page(self.by['syn-tour'], self.site).html).by_id('main')
        seq = marks(main)
        # each day chapter has a pager of its own (a plain div): the report pager is the page's one nav.pager, and the
        # last pager on the page
        navs = main.find_all('nav', cls='pager')
        self.assertEqual(len(navs), 1)
        self.assertEqual(navs[0]['aria-label'], 'More %s reports' % core.ACT['ski'][0].lower())
        self.assertIs(main.find_all(cls='pager')[-1], navs[0])
        self.assertEqual([a['href'] for a in navs[0].find_all('a')], ['../../trips/syn-explicit/', '../../trips/syn-ski-two/'])
        self.assertEqual(seq[-1], '.pager')
        self.assertInOrder(seq, ['day-2', '.rep-related', 'rel-h'])
        self.assertNotIn('.pager', seq[seq.index('.rep-related'):-1])   # nothing but the cards between the block and the pager
        cards = [c['data-slug'] for c in main.find('ul', cls='rep-rel').find_all('li', cls='tcard')]
        self.assertFalse({'syn-explicit', 'syn-ski-two'} & set(cards), cards)   # neither Newer nor Older is offered twice

    def shared(self, t):
        """The og:image of the trip's multi-day page, None when it has none."""
        m = Doc(self.multiday.page(t, self.site).html).find('head').find_all('meta', attrs={'property': 'og:image'})
        self.assertLessEqual(len(m), 1)
        return m[0]['content'] if m else None

    def test_og_image_is_the_cover(self):
        # section 10.4: the share image of a multi-day page is its cover (multiday.share_image(t)), the photo its cards
        # show, not the first photo on the page (the first day photo)
        share_image = need(self, self.multiday, 'share_image')
        day = {'title': 'Synthetic Day One', 'date': '2025-03-01'}
        two = {'title': 'Synthetic Day Two', 'date': '2025-03-02'}
        # the trip's own photo is the cover; a day photo comes first on the page
        self.add('syn-trek', kind='multi-day', activity='ski', date='2025-03-01', end_date='2025-03-02',
                 photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one')],
                 days=[dict(day, photos=[photo('photos/d01-01.webp', LANDSCAPE, alt='Synthetic day photo one')]), two])
        # day photos only: the landscape of day 2 is the cover, the portrait of day 1 the first photo
        self.add('syn-trek-days', kind='multi-day', activity='ski', date='2025-03-01', end_date='2025-03-02',
                 days=[dict(day, photos=[photo('photos/d01-01.webp', PORTRAIT, alt='Synthetic day photo one')]),
                       dict(two, photos=[photo('photos/d02-01.webp', LANDSCAPE, alt='Synthetic day photo two')])])
        # cover_photo names the portrait of day 2, after a landscape on day 1
        self.add('syn-trek-named', kind='multi-day', activity='ski', date='2025-03-01', end_date='2025-03-02', cover_photo='photos/d02-01.webp',
                 days=[dict(day, photos=[photo('photos/d01-01.webp', LANDSCAPE, alt='Synthetic day photo one')]),
                       dict(two, photos=[photo('photos/d02-01.webp', PORTRAIT, alt='Synthetic day photo two')])])
        want = {'syn-trek': ('parent', 'photos/01.webp'), 'syn-trek-days': ('day', 'photos/d02-01.webp'),
                'syn-trek-named': ('explicit', 'photos/d02-01.webp')}
        for slug, (source, file) in want.items():
            with self.subTest(slug):
                t = self.by[slug]
                self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), (source, file))
                self.assertEqual(share_image(t), 'trips/%s/%s' % (slug, file))
                self.assertEqual(self.shared(t), core.SITE_URL + 'trips/%s/%s' % (slug, file))
                self.assertNotEqual(self.shared(t), core.SITE_URL + 'trips/%s/photos/d01-01.webp' % slug)   # the page's first photo

    def test_og_image_of_the_fixture_tour_and_of_a_tour_without_photos(self):
        # section 10.4: the cover whenever the trip has one; none without photos. 'Else the first photo' cannot be
        # reached through the loader: content.resolve_cover gives a trip with any photo, its own or a day's, a cover
        share_image = need(self, self.multiday, 'share_image')
        t = self.by['syn-tour']
        self.assertEqual(share_image(t), 'trips/syn-tour/' + t['cover']['photo']['file'])
        self.assertEqual(self.shared(t), core.SITE_URL + 'trips/syn-tour/photos/01.webp')
        bare = self.add('syn-trek-bare', kind='multi-day', activity='ski', date='2025-03-01', end_date='2025-03-02',
                        days=[{'title': 'Synthetic Day One', 'date': '2025-03-01'}, {'title': 'Synthetic Day Two', 'date': '2025-03-02'}])
        self.assertIsNone(bare['cover'])
        self.assertIsNone(share_image(bare))
        self.assertIsNone(self.shared(bare))

    def test_share_row_sits_before_the_related_block(self):
        # section 9: multi-day pages also carry the phone share row (report.share_row) before the related block, because
        # multiday.css hides the title actions under 760 px too
        share_row = need(self, self.report, 'share_row')
        self.assertEqual(self.mpage.html.count(share_row('trips/syn-tour/')), 1)
        self.assertInOrder(marks(self.mmain), ['day-2', '.rep-share', '.rep-related', 'rel-h'])
        btns = self.mdoc.find_all('button', cls='copy-btn')
        self.assertEqual([(b.text(), b['data-copy']) for b in btns],
                         [('Copy link', core.SITE_URL + 'trips/syn-tour/'), ('Copy link to this page', core.SITE_URL + 'trips/syn-tour/')])

    def test_multi_day_page_keeps_its_own_layout(self):
        # section 2: multi-day pages are not changed by the layouts: no hero, no section row, body class p-multiday
        self.assertEqual(self.mdoc.find('body').classes, ['p-multiday'])
        self.assertIsNone(self.mmain.find(cls='rep-hero'))
        self.assertIsNone(self.mmain.find('nav', cls='rep-toc'))


if __name__ == '__main__':
    unittest.main()
