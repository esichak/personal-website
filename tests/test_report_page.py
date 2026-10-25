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

Phase 4 (contract-phase4.md) adds, on the same fixture: capability-driven rendering (2.1 as replaced by 10.2: a
single-day report without track.gpx has no route at all: no GPX control and no 'View route', no Route map section, no
Route item in the section row, no Map item in the phone bar and no bar when one item would be left, no full-screen map
page, and a section page never features it, while a report with a track is exactly what it was, rendered or not; a
multi-day page offers 'Download all GPX' only when a day has a track, and a day without one has no link of its own),
what a phone is told about a photo that fills its width (5.2: core.PHONE_SLOT / PHONE_FULL, report.HERO_SIZES), the
card-size .th copy in cover srcsets (5.3: core.thumb_width, core._cover_srcset) and the share photo (4.1:
core.share_photo, multiday.share_image). A .th file is an empty placeholder the test writes beside the photo; nothing
here needs cwebp or sips. core.has_track, core.summary, core.stats_note and core.photo are pinned by themselves in
tests/test_track_rules.py. 10.3 (review round 1) on top of that: a report without a track and without stats has no Stats
strip; a rendered folder left behind by a removed track is shown and published nowhere (core.render_meta, core.glyph and
core.tile give nothing without core.has_track); and core.phone_sizes tells a phone 100vw, not the 55vw slot, for a
portrait, a square, a panorama or an unsized photo (PhoneShapeTests). 10.5 (after the screenshot comparison): the .th
copy is a candidate of no <img> and no preload (core._cover_srcset is the two candidates it was before the phase); a
card cover that has one is wrapped in <picture class="cover-pic"> with a phone-only <source> (core._card_source:
CardSourceTests).

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
import posixpath
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

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

WRITEUP = ('Synthetic write-up for a test.\n\n'
           'Second synthetic paragraph, with *emphasis* and a [synthetic link](https://example.test/).')
NOTES = 'Synthetic planning notes for a test.'
CAPTION = 'Synthetic caption: "quoted" & <bracketed>.'
REGION = 'Synthetic Range'
BETA = [{'label': 'Trailhead', 'value': 'Synthetic Lot'}]
TRACK_NOTE = 'Synthetic recorder, one synthetic gap'      # a beta row labelled Track: the stats footnote prints it
CREDIT = ['Terrain: AWS Terrain Tiles', 'Map data © OpenStreetMap contributors', 'Not for navigation']   # every caption's end
PHONE_FULL = '(min-width: 560px) 100vw, 55vw'             # contract-phase4.md 5.2: core.PHONE_FULL, written out
HERO_SIZES = '(min-width: 1200px) 1248px, ' + PHONE_FULL   # ... and report.HERO_SIZES (was '... 1248px, 100vw')

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
PROFILE = ('Elevation', '#profile')        # Phase 10 (copy-09): one label table names #profile Elevation
SPEED = ('Speed', '#profile')


def load_module(tc, name):
    try:
        return importlib.import_module(name)
    except ImportError as ex:
        tc.fail('%s is not importable: %s' % (name.replace('.', '/') + '.py', ex))


def pick_candidate(widths, slot_px, dpr):
    """The srcset candidate a browser takes for a slot `slot_px` CSS px wide on a screen of `dpr` device px per px: the
    first of the listed widths that is at least slot x DPR wide, else the largest."""
    need_px = slot_px * dpr
    return next((w for w in widths if w >= need_px), widths[-1])


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


def gpx_title_action(slug):
    """The 'Download GPX' title action of a single-day report, exactly as report.page writes it."""
    return '<a class="btn btn--ink" href="%s.gpx" download>%sDownload GPX</a>' % (slug, core.icon('download', 18))


def gpx_bar_item(href):
    """The phone bottom bar's GPX item, exactly as report.bottom_bar writes it."""
    return '<a href="%s" download>%s<span>GPX</span></a>' % (href, core.icon('download', 24))


def without_gpx(html_, slug):
    """A single-day report page (or a part of it) with its GPX controls taken out: the title action, the bottom bar's
    item, and the bar's --n one lower. What report.bottom_bar must give without a file to offer, given the bar with one
    (the page of a report without a track loses more than this: without_track(), further down)."""
    out = html_.replace(gpx_title_action(slug), '').replace(gpx_bar_item(slug + '.gpx'), '')
    return re.sub(r'(<nav class="bbar" aria-label="Report sections" style="--n:)(\d+)', lambda m: m.group(1) + str(int(m.group(2)) - 1), out)


def gpx_links(node):
    """Every link under node that names a .gpx file or is a download, as (text, href), in document order."""
    return [(a.text(), a['href']) for a in node.find_all('a') if 'download' in a or '.gpx' in (a['href'] or '').lower()]


def legacy_bar(t, gpx_href, has_beta, has_report, has_gallery, chart=''):
    """The compact phone bottom bar written out: the items it has had since Phase 3, in the page's order and with the
    names of the one label table since Phase 10 (copy-09: Stats, which sits above the map, comes first; the chart is
    Elevation)."""
    items = [('#map', 'map', 'Map')]
    if has_beta:
        items.append(('#beta', 'beta', 'Beta'))
    elif t['kind'] != 'planned':
        items.append(('#profile', 'profile', 'Speed' if chart == 'speed' else 'Elevation') if chart else ('#stats', 'beta', 'Stats'))
    if has_report:
        items.append(('#report', 'report', 'Report'))
    elif has_gallery:
        items.append(('#photos', 'photo', 'Photos'))
    items.sort(key=lambda it: ('#stats', '#map', '#profile', '#beta', '#report', '#photos').index(it[0]))
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

    def render(self, slug, maps=True, chart='', drawn=False):
        """Point the trip at a placeholder render folder in the temp dir: meta.json with the three report maps and, with
        chart='profile' | 'speed', that chart, plus the tiny fragments core.map_block / core.chart_block inline.
        drawn=True: also what else tools/render.py leaves there and a build publishes: the three route drawings (tile,
        g112, g64) and the image files of the maps."""
        folder = os.path.join(self.tmp, '_rendered', slug)
        os.makedirs(folder, exist_ok=True)
        if drawn:
            for name, (w, h) in core.GLYPH_SIZES.items():
                with open(os.path.join(folder, name + '.svg.html'), 'w', encoding='utf-8') as fh:
                    fh.write('<svg class="%s" viewBox="0 0 %d %d" aria-hidden="true"><path class="gl-trk" d="M1 1L9 9"/></svg>' % (name, w, h))
            for name in ('map-wide', 'map-col', 'map-phone') if maps else ():
                helpers.touch(os.path.join(folder, name + '.webp'))
                helpers.touch(os.path.join(folder, name + '.base.svg'))
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
        """The map caption's items. The caption is drawn only under a rendered map (Phase 6: a track without one gets
        the 'Map not rendered yet' box), so a fixture report that has none is pointed at a placeholder render first."""
        if self.by[slug]['track'] and not core.render_meta(self.by[slug])['maps']:
            self.render(slug)
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
        # Phase 10 (report-11): a multi-day trip leads with its landscape cover, without the story class or a section row
        self.assertIsNotNone(Doc(pages['syn-tour'].html).find('figure', cls='rep-hero'))

    def test_the_writeup_is_verbatim_under_its_heading(self):
        # hard rule + section 2.5: id="report", h2 'Report' (Phase 10: the row's word), the prose exactly as markdown renders it
        markdown = load_module(self, 'markdown')
        for slug in ('syn-story', 'syn-words'):
            with self.subTest(slug):
                rep = self.main(slug).by_id('report')
                self.assertEqual(rep.find('h2').text(), 'Report')
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
                              % (core.strip(core.strip_cells(t)), core.stats_note(t, here=t['url'])), self.page(slug).html)
                # Phase 9 (ia-19): the note ends with the link to About's method, which resolves to about/#abo-how-h
                self.assertTrue(core.stats_note(t, here=t['url']).endswith(' %s</p>' % HOW))
                self.assertEqual(posixpath.normpath(posixpath.join(t['url'], '../../about/')) + '/', 'about/')

    def test_page_url_and_title(self):
        # hard rule: every URL unchanged; the page is still trips/<slug>/
        for slug in SINGLE:
            p = self.page(slug)
            self.assertEqual(p.url, 'trips/%s/' % slug)
            self.assertEqual(p.title, self.by[slug]['title'])
            self.assertEqual(self.doc(slug).find('link', attrs={'rel': 'canonical'})['href'], core.SITE_URL + 'trips/%s/' % slug)


# ---------------------------------------------------------------- the section row (report.section_nav)

class SummitsRowTests(ReportFixture):
    """Phase 9 (features-05): a report's summits: list is the last row of its Beta rail, 'Summits', in the beta_list
    markup: one name alone, two or more stacked one per line; a route and an outcome other than summit are said after the
    name. A report with summits and no beta rows gets the Beta block for that row."""

    def test_one_and_several(self):
        one = self.add('syn-one-summit', beta=[{'label': 'Grade', 'value': 'Synthetic II'}], summits=[{'name': 'Synthetic Peak'}])
        self.assertEqual(self.report.beta_list(one),
                         '<div class="rail-b" id="beta"><h2 class="t-label" id="beta-h">Beta</h2><dl class="dl-leader">'
                         '<div><dt>Grade</dt><dd>Synthetic II</dd></div><div><dt>Summits</dt><dd>Synthetic Peak</dd></div></dl></div>')
        two = self.add('syn-two-summits', summits=[{'name': 'Synthetic Peak', 'outcome': 'summit'},
                                                   {'name': 'Synthetic Dome', 'outcome': 'turned-around', 'route': 'the north ridge, mostly'},
                                                   {'name': 'Synthetic Spire', 'outcome': 'traverse'}])
        self.assertIn('<div><dt>Summits</dt><dd class="dl-list"><span>Synthetic Peak,</span> <span>Synthetic Dome via the north '
                      'ridge, mostly (turned around),</span> <span>Synthetic Spire (traverse)</span></dd></div>',
                      self.report.beta_list(two))
        self.assertIsNotNone(self.doc('syn-two-summits').by_id('beta'))     # no beta rows: the block is there for the row

    def test_no_list_no_row(self):
        plain = self.add('syn-no-summit')
        self.assertEqual(self.report.beta_list(plain), '')
        self.assertNotIn('Summits', self.page('syn-no-summit').html)


class SectionNavTests(ReportFixture):

    def setUp(self):
        super().setUp()
        self.section_nav = need(self, self.report, 'section_nav')

    def items(self, *args):
        nav = Doc(self.section_nav(*args)).find('nav')
        return [(a.text(), a['href']) for a in nav.find_all('a')]

    def test_markup(self):
        # section 2.4, as Phase 10 (copy-09) left it: <nav class="rep-toc wrap" aria-label="Sections"> in page order,
        # each section named by report.LABELS
        self.assertEqual(self.section_nav(True, True, True, 'profile'),
                         '<nav class="rep-toc wrap" aria-label="Sections"><ul>'
                         '<li><a class="rep-toc-a" href="#report">Report</a></li>'
                         '<li><a class="rep-toc-a" href="#map">Map</a></li>'
                         '<li><a class="rep-toc-a" href="#profile">Elevation</a></li>'
                         '<li><a class="rep-toc-a" href="#photos">Photos</a></li></ul></nav>')
        self.assertIn('href="#profile">Speed</a>', self.section_nav(True, True, True, 'speed'))

    def test_every_set_of_sections_in_page_order(self):
        order = ['#report', '#map', '#profile', '#photos']
        for has_report, has_gallery, has_map, chart in itertools.product((True, False), (True, False), (True, False), ('', 'profile')):
            with self.subTest(report=has_report, gallery=has_gallery, map=has_map, chart=chart):
                hrefs = [h for _lab, h in self.items(has_report, has_gallery, has_map, chart)]
                self.assertEqual(hrefs, [h for h in order if h in hrefs])
                self.assertEqual(('#report' in hrefs, '#photos' in hrefs, '#map' in hrefs, '#profile' in hrefs),
                                 (has_report, has_gallery, has_map, bool(chart)))

    def test_the_row_follows_the_page(self):
        # the row lists its targets in the order they run on the page; 'Route' and 'Trip details' are retired
        for slug in STORY:
            with self.subTest(slug):
                seq = marks(self.main(slug))
                hrefs = [h[1:] for _lab, h in self.toc(slug)]
                self.assertEqual(hrefs, sorted(hrefs, key=seq.index))
                self.assertFalse({'Route', 'Trip details'} & {lab for lab, _h in self.toc(slug)})
        self.assertEqual(self.toc('syn-story'), [REPORT, MAP, PHOTOS])

    def test_no_link_in_the_section_row_is_marked_current(self):
        # section 10.2: no link in the section row is ever marked current (base.js marks the current section in the phone
        # bottom bar only): the generator writes no aria-current into the row, for any set of sections ...
        for args in itertools.product((True, False), (True, False), (True, False), ('', 'profile')):
            self.assertNotIn('aria-current', self.section_nav(*args), args)
        # ... nor on any built story page, where each link is the bare <a class="rep-toc-a" href="#...">
        for slug in STORY:
            with self.subTest(slug):
                nav = self.main(slug).find('nav', cls='rep-toc')
                links = nav.find_all('a')
                self.assertGreaterEqual(len(links), 2)
                for a in links:
                    self.assertNotIn('aria-current', a)
                    self.assertEqual(sorted(a.attrs), ['class', 'href'])
                self.assertEqual([n for n in nav.walk() if 'aria-current' in n], [])
                self.assertNotIn('aria-current', nav)

    def test_no_photos_item_when_the_cover_was_the_only_photo(self):
        # section 7: no Photos when the cover is the only photo
        self.assertEqual(self.toc('syn-one'), [REPORT, MAP])
        self.assertEqual(self.toc('syn-one-beta'), [REPORT, MAP])

    def test_the_page_uses_section_nav(self):
        # the row on the page is report.section_nav(has_report, has_gallery, has_map, chart)
        self.assertIn(self.section_nav(True, True, True, ''), self.page('syn-story').html)
        self.assertIn(self.section_nav(True, False, True, ''), self.page('syn-one').html)
        self.render('syn-one', chart='profile')
        self.assertIn(self.section_nav(True, False, True, 'profile'), self.page('syn-one').html)

    def test_one_section_row_per_story_and_no_rail_contents_list(self):
        # section 2.4: shown on the narrative layout, where it replaces the rail's Contents list
        for slug in STORY:
            with self.subTest(slug):
                main = self.main(slug)
                self.assertEqual(len(main.find_all('nav', cls='rep-toc')), 1)
                self.assertEqual(main.find('nav', cls='rep-toc')['aria-label'], 'Sections')
                self.assertIsNone(main.find('nav', cls='rail-toc'))
                self.assertIsNone(main.by_id('toc-h'))

    def test_compact_pages_have_no_section_row_and_only_a_photo_only_report_has_a_hero(self):
        # section 2.4: the compact layout has no .rep-toc; since Phase 10 (report-02) a photo-only report whose cover is a
        # landscape (syn-photos) leads with it, and only that one
        for slug in COMPACT:
            with self.subTest(slug):
                main = self.main(slug)
                self.assertIsNone(main.find('nav', cls='rep-toc'))
                self.assertEqual(main.find(cls='rep-hero') is not None, slug == 'syn-photos')
                self.assertEqual(main.by_id('hero') is not None, slug == 'syn-photos')

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
                self.assertEqual([a['href'] for a in main.find('nav', cls='rep-toc').find_all('a')], ['#report', '#map', '#photos'])
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
        self.assertEqual([lab for lab, _href in self.toc(slug)], ['Report', 'Map', 'Photos'])

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
        # section 2.2: core.cover_img(t, here, HERO_SIZES, eager=True). contract-phase4.md 5.2 and 10: HERO_SIZES is
        # '(min-width: 1200px) 1248px, ' + core.PHONE_FULL (it ended in a bare 100vw), so below 560 px a phone is told
        # the 55vw slot and takes the 800 px copy instead of the full file
        self.assertEqual(need(self, self.report, 'HERO_SIZES'), '(min-width: 1200px) 1248px, ' + need(self, core, 'PHONE_FULL'))
        self.assertEqual(self.report.HERO_SIZES, HERO_SIZES)
        for slug in HERO:
            with self.subTest(slug):
                t = self.by[slug]
                self.assertIn(core.cover_img(t, t['url'], HERO_SIZES, eager=True), self.page(slug).html)
        img = self.hero('syn-story').find('img')   # its cover has the .sm copy, so the srcset and sizes are written
        self.assertEqual(img['sizes'], HERO_SIZES)
        self.assertEqual(img['sizes'], '(min-width: 1200px) 1248px, (min-width: 560px) 100vw, 55vw')
        self.assertIn('photos/02.sm.webp 800w', img['srcset'])
        # no .th file in this fixture, so the list is the two candidates it always was (CoverSrcsetTests has the rest)
        self.assertEqual(img['srcset'], '../../trips/syn-story/photos/02.sm.webp 800w, ../../trips/syn-story/photos/02.webp 1600w')
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
        sec = self.main('syn-unnamed-tall').by_id('photos')
        self.assertIsNone(self.hero('syn-unnamed-tall'))
        self.assertEqual([a['aria-label'] for a in sec.find_all('a', cls='jph')], ['Photo 1 of 2, full size', 'Photo 2 of 2, full size'])
        self.assertEqual(sec.find('div', cls='rep-sh').find('span').text(), '2 PHOTOS')
        # a photo-only report leads with its landscape cover (Phase 10): the grid counts on from it, as a story's does
        self.assertIsNotNone(self.hero('syn-unnamed-compact'))
        sec = self.main('syn-unnamed-compact').by_id('photos')
        self.assertEqual([a['aria-label'] for a in sec.find_all('a', cls='jph')], ['Photo 2 of 3, full size', 'Photo 3 of 3, full size'])

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

    def test_the_compact_gallery_is_every_photo_but_the_lead(self):
        # section 2, compact layout: a photo-only report whose cover leads it (Phase 10, report-02) shows the rest of its
        # photos in the grid, in order, as a story does
        self.assertEqual(self.gallery_files('syn-photos'), ['../../trips/syn-photos/photos/%s.webp' % n for n in ('02', '03')])
        self.assertEqual(self.hero('syn-photos').find('a')['href'], '../../trips/syn-photos/photos/01.webp')


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
        self.assertEqual(self.toc('syn-portrait'), [REPORT, MAP])
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
        render_overview(self.tmp, t)
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
        render_overview(self.tmp, t)
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
        render_overview(self.tmp, t)
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
        self.assertIn(core.stats_note(t, here=core.section_url('hike')), section.page('hike', self.site).html)
        self.assertTrue(note.text().endswith(' ' + HOW_TEXT))

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
        # hard rule + section 2.1: <a class="btn btn--ink" href="<slug>.gpx" download> on both layouts. contract-phase4.md
        # 2.1: on a report that has a track, which every report of the fixture does (NoTrackTests: the ones that do not)
        for slug in SINGLE:
            with self.subTest(slug):
                self.assertTrue(self.by[slug]['track'], '%s: the fixture report has no track.gpx' % slug)
                dl = [a for a in self.main(slug).find('div', cls='rep-actions').find_all('a') if a.text() == 'Download GPX']
                self.assertEqual(len(dl), 1)
                self.assertEqual(dl[0].classes, ['btn', 'btn--ink'])
                self.assertEqual(dl[0]['href'], slug + '.gpx')
                self.assertIn('download', dl[0])
                self.assertEqual(self.page(slug).html.count(gpx_title_action(slug)), 1)
                # the phone bar's last item is the same file, and the page links no other
                self.assertEqual(bar_items(self.bbar(slug))[-1], ('GPX', slug + '.gpx'))
                self.assertIn('download', self.bbar(slug).find_all('a')[-1])
                self.assertEqual(gpx_links(self.doc(slug).root), [('Download GPX', slug + '.gpx'), ('GPX', slug + '.gpx')])

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
        # section 2 (bottom bar), case 5: ... else Stats, which comes first in page order (Phase 10)
        self.assertEqual(self.story(False, False), [STATS, REPORT, MAP, ('GPX', 'syn-story.gpx')])

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

    def test_compact_bar_is_the_written_out_one(self):
        # section 2 (bottom bar): the compact layout's bar, byte for byte, for every combination of beta, report,
        # gallery and chart (legacy_bar: Phase 3's items, Phase 10's order and names)
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
                 ((False, True, False, ''), [STATS, MAP, REPORT, gpx]),       # page order: the strip is above the map
                 ((False, False, False, ''), [STATS, MAP, gpx])]
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
        self.assertEqual(bar_items(self.bbar('syn-one')), [STATS, REPORT, MAP, ('GPX', 'syn-one.gpx')])   # page order
        self.render('syn-one', chart='profile')
        self.assertEqual(bar_items(self.bbar('syn-one')), [REPORT, MAP, PROFILE, ('GPX', 'syn-one.gpx')])
        self.assertIsNotNone(self.doc('syn-one').by_id('profile'))
        self.render('syn-one', chart='speed')
        self.assertEqual(bar_items(self.bbar('syn-one')), [REPORT, MAP, SPEED, ('GPX', 'syn-one.gpx')])
        self.assertEqual(self.doc('syn-one').by_id('profile').find('h2').text(), 'Speed')

    def test_lone_portrait_story_page(self):
        # the lone portrait is not a gallery: cases 3-5 apply
        self.assertEqual(bar_items(self.bbar('syn-portrait')), [STATS, REPORT, MAP, ('GPX', 'syn-portrait.gpx')])

    def test_compact_pages(self):
        # section 2 (bottom bar): the compact layout, on the page itself (Phase 10: in page order, the strip first)
        want = {'syn-words': [MAP, BETA_ITEM, REPORT], 'syn-photos': [STATS, MAP, PHOTOS], 'syn-tall-only': [STATS, MAP],
                'syn-track': [STATS, MAP]}
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
        # section 2.2: the hero is the page's preloaded image (core.cover_preload(t, here, HERO_SIZES)); contract-phase4.md
        # 5.2: 'the same string feeds the preload', so HERO_SIZES here is report.HERO_SIZES with the phone slot
        need(self, core, 'cover_preload')
        self.assertEqual(need(self, self.report, 'HERO_SIZES'), HERO_SIZES)
        for slug in HERO:
            with self.subTest(slug):
                self.render(slug)
                t = self.by[slug]
                links = self.preloads(slug)
                self.assertEqual([l['href'] for l in links], [self.photo_href(slug, t['cover']['photo']['file'])])
                self.assertEqual(links[0]['fetchpriority'], 'high')
                self.assertIn(core.cover_preload(t, t['url'], HERO_SIZES), self.head_html(slug))
                # ... and it is the hero <img>'s own source, candidates and sizes (none of the last two without an .sm copy)
                img = self.hero(slug).find('img')
                self.assertEqual((links[0]['href'], links[0]['imagesrcset'], links[0]['imagesizes']), (img['src'], img['srcset'], img['sizes']))
        self.assertEqual(self.preloads('syn-story')[0]['imagesizes'], HERO_SIZES)   # the one fixture cover with an .sm copy

    def test_the_cover_preload_carries_the_hero_sizes(self):
        # section 2.2 and contract-phase4.md 10: the preload matches the <img>: the same srcset, and its imagesizes is
        # the hero image's sizes exactly, '(min-width: 1200px) 1248px, ' + core.PHONE_FULL
        link = self.preloads('syn-story')[0]
        img = self.hero('syn-story').find('img')
        self.assertIsNotNone(img['sizes'])
        self.assertEqual(link['imagesizes'], img['sizes'])
        self.assertEqual(link['imagesizes'], '(min-width: 1200px) 1248px, ' + core.PHONE_FULL)
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
        # section 2 (compact): core.map_preloads in the head, the map block eager; not on a photo-only report, whose cover
        # leads it since Phase 10 (test_a_photo_only_report_preloads_its_cover)
        for slug in ('syn-words', 'syn-track'):
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

    def share_meta(self, slug):
        """{property or name: content} of the page's share-image tags (og:image and its properties, the twitter card)."""
        out = {}
        for m in self.doc(slug).find('head').find_all('meta'):
            key = m['property'] or m['name'] or ''
            if key.startswith(('og:image', 'twitter:')):
                self.assertNotIn(key, out, 'two %s tags' % key)
                out[key] = m['content']
        return out

    def test_the_share_image_is_the_share_photo_with_what_is_recorded_for_it(self):
        # contract-phase4.md 4.1 and 4.2: both layouts pass core.share_photo(t): the cover's path, and its size and alt
        # text only as far as index.md records them; nothing is measured or worded for the tags
        self.assertTrue(hasattr(core, 'share_photo'), 'core.share_photo is missing (contract-phase4.md 4.1)')
        for slug in ('syn-story', 'syn-photos'):        # a story (the cover is the second photo) and a compact page
            with self.subTest(slug):
                t = self.by[slug]
                p = t['cover']['photo']
                share = core.share_photo(t)
                self.assertEqual(share, {'path': 'trips/%s/%s' % (slug, p['file']), 'w': p['w'], 'h': p['h'], 'alt': p['alt']})
                self.assertEqual(self.og_image(slug), core.SITE_URL + share['path'])
                self.assertEqual(self.share_meta(slug), {'og:image': core.SITE_URL + share['path'], 'og:image:type': 'image/webp',
                                                         'og:image:width': str(p['w']), 'og:image:height': str(p['h']), 'og:image:alt': p['alt'],
                                                         'twitter:card': 'summary_large_image', 'twitter:image:alt': p['alt']})
        # a cover without alt text (syn-explicit's) is described by no tag; its size is still stated
        self.assertEqual(self.by['syn-explicit']['cover']['photo']['alt'], '')
        self.assertEqual(self.share_meta('syn-explicit'), {'og:image': core.SITE_URL + 'trips/syn-explicit/photos/03.webp', 'og:image:type': 'image/webp',
                                                           'og:image:width': '1600', 'og:image:height': '1200', 'twitter:card': 'summary_large_image'})
        # a cover without a recorded size gets no width or height (never one of the two, never a guess)
        self.add('syn-unsized', date='2025-06-16', body=WRITEUP, photos=[photo('photos/01.jpg', None, alt='Synthetic "unsized" & <plain> photo')])
        self.assertEqual(core.share_photo(self.by['syn-unsized']), {'path': 'trips/syn-unsized/photos/01.jpg', 'w': None, 'h': None,
                                                                    'alt': 'Synthetic "unsized" & <plain> photo'})
        self.assertEqual(self.share_meta('syn-unsized'), {'og:image': core.SITE_URL + 'trips/syn-unsized/photos/01.jpg', 'og:image:type': 'image/jpeg',
                                                          'og:image:alt': 'Synthetic "unsized" & <plain> photo',
                                                          'twitter:card': 'summary_large_image', 'twitter:image:alt': 'Synthetic "unsized" & <plain> photo'})
        # ... and when only one of the two is recorded, neither is written (4.2: both or none)
        self.add('syn-half-sized', date='2025-06-17', body=WRITEUP, photos=[{'file': 'photos/01.webp', 'w': 1600, 'alt': 'Synthetic half-sized photo'}])
        self.assertEqual(core.share_photo(self.by['syn-half-sized']), {'path': 'trips/syn-half-sized/photos/01.webp', 'w': 1600, 'h': None,
                                                                       'alt': 'Synthetic half-sized photo'})
        self.assertEqual(self.share_meta('syn-half-sized'), {'og:image': core.SITE_URL + 'trips/syn-half-sized/photos/01.webp', 'og:image:type': 'image/webp',
                                                             'og:image:alt': 'Synthetic half-sized photo',
                                                             'twitter:card': 'summary_large_image', 'twitter:image:alt': 'Synthetic half-sized photo'})
        for half in ({'w': 1600, 'h': None}, {'w': None, 'h': 1200}, {'w': 1600, 'h': 0}, {'w': '1600', 'h': '1200'}, {'w': True, 'h': True}):
            tags = core._share_tags(dict(half, path='trips/syn-half-sized/photos/01.webp', alt=''))
            self.assertNotIn('og:image:width', tags, half)
            self.assertNotIn('og:image:height', tags, half)
        # no photo, no image: the small card alone
        self.assertIsNone(core.share_photo(self.by['syn-words']))
        self.assertEqual(self.share_meta('syn-words'), {'twitter:card': 'summary'})

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
        # Phase 10 (report-02): the landscape cover leads its photo-only page; a portrait cover does not
        self.assertSharesCover('syn-compact-cover', 'photos/02.webp', story=False, hero=True)
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
        # hard rule: every URL and GPX download unchanged (contract-phase4.md 2.1: for a tour whose days have tracks)
        self.assertTrue(all(d['track'] for d in self.by['syn-tour']['days']))
        box = self.mmain.find('div', cls='rep-actions')
        dl = [a for a in box.find_all('a') if a.text() == 'Download all GPX']
        self.assertEqual(len(dl), 1)
        dl = dl[0]
        self.assertEqual(dl['href'], 'syn-tour.gpx')
        self.assertEqual(dl.classes, ['btn', 'btn--ink'])
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

    def share_meta(self, t):
        """{property or name: content} of the share-image tags in the head of the trip's multi-day page."""
        head = Doc(self.multiday.page(t, self.site).html).find('head')
        out = {}
        for m in head.find_all('meta'):
            key = m['property'] or m['name'] or ''
            if key.startswith(('og:image', 'twitter:')):
                self.assertNotIn(key, out, 'two %s tags' % key)
                out[key] = m['content']
        return out

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
        want = {'syn-trek': ('parent', 'photos/01.webp', LANDSCAPE, 'Synthetic photo one'),
                'syn-trek-days': ('day', 'photos/d02-01.webp', LANDSCAPE, 'Synthetic day photo two'),
                'syn-trek-named': ('explicit', 'photos/d02-01.webp', PORTRAIT, 'Synthetic day photo two')}
        for slug, (source, file, (w, h), alt) in want.items():
            with self.subTest(slug):
                t = self.by[slug]
                self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), (source, file))
                # contract-phase4.md 4.1 and 10: share_image(t) is core.share_photo(t), the cover with the size and the
                # alt text recorded for it (it was a bare path), and the page's og:image is SITE_URL + its path
                self.assertEqual(share_image(t), core.share_photo(t))
                self.assertEqual(share_image(t), {'path': 'trips/%s/%s' % (slug, file), 'w': w, 'h': h, 'alt': alt})
                self.assertEqual(self.shared(t), core.SITE_URL + share_image(t)['path'])
                self.assertEqual(self.shared(t), core.SITE_URL + 'trips/%s/%s' % (slug, file))
                self.assertNotEqual(self.shared(t), core.SITE_URL + 'trips/%s/photos/d01-01.webp' % slug)   # the page's first photo
                self.assertEqual(self.share_meta(t), {'og:image': core.SITE_URL + 'trips/%s/%s' % (slug, file), 'og:image:type': 'image/webp',
                                                      'og:image:width': str(w), 'og:image:height': str(h), 'og:image:alt': alt,
                                                      'twitter:card': 'summary_large_image', 'twitter:image:alt': alt})

    def test_og_image_of_the_fixture_tour_and_of_a_tour_without_photos(self):
        # section 10.4: the cover whenever the trip has one; none without photos. 'Else the first photo' cannot be
        # reached through the loader: content.resolve_cover gives a trip with any photo, its own or a day's, a cover
        share_image = need(self, self.multiday, 'share_image')
        t = self.by['syn-tour']
        # contract-phase4.md 4.1 and 10: the share photo (a dict: path, recorded size, alt), not a bare path
        self.assertEqual(share_image(t), need(self, core, 'share_photo')(t))
        self.assertEqual(share_image(t), {'path': 'trips/syn-tour/' + t['cover']['photo']['file'], 'w': 1600, 'h': 1200, 'alt': 'Synthetic photo one'})
        self.assertEqual(self.shared(t), core.SITE_URL + share_image(t)['path'])
        self.assertEqual(self.shared(t), core.SITE_URL + 'trips/syn-tour/photos/01.webp')
        bare = self.add('syn-trek-bare', kind='multi-day', activity='ski', date='2025-03-01', end_date='2025-03-02',
                        days=[{'title': 'Synthetic Day One', 'date': '2025-03-01'}, {'title': 'Synthetic Day Two', 'date': '2025-03-02'}])
        self.assertIsNone(bare['cover'])
        self.assertIsNone(core.share_photo(bare))
        self.assertIsNone(share_image(bare))
        self.assertIsNone(self.shared(bare))
        # a photo-less tour shares no image at all: the small card, and none of the image's tags
        self.assertEqual(self.share_meta(bare), {'twitter:card': 'summary'})

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
        # section 2: multi-day pages keep their own layout: no section row (the day nav is one), body class p-multiday;
        # since Phase 10 (report-11) the landscape cover leads them, after the title block and before the strip
        self.assertEqual(self.mdoc.find('body').classes, ['p-multiday'])
        self.assertIsNotNone(self.mmain.find(cls='rep-hero'))
        self.assertInOrder(marks(self.mmain), ['title', 'hero', 'stats', 'map'])
        self.assertIsNone(self.mmain.find('nav', cls='rep-toc'))

    # ------------------------------------------------------------ contract-phase4.md 2.1: downloads only where a track is

    DAY_GPX = ('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="synthetic" xmlns="http://www.topografix.com/GPX/1/1">'
               '<trk><name>Synthetic day %s</name><trkseg><trkpt lat="1.0" lon="2.0"></trkpt></trkseg></trk></gpx>\n')

    def trek(self, slug, tracks, written=None):
        """A three-day (or len(tracks)-day) ski tour whose day k has a GPX when tracks[k-1] is true; day `written` has a
        write-up. Each day GPX holds one synthetic <trk>, so the build has something to put in the combined file."""
        days = [{'title': 'Synthetic Day %d' % (i + 1), 'date': '2025-03-%02d' % (i + 1), 'track': bool(has)} for i, has in enumerate(tracks)]
        if written:
            days[written - 1]['body'] = WRITEUP
        t = self.add(slug, kind='multi-day', activity='ski', date='2025-03-01', end_date='2025-03-%02d' % len(tracks), days=days)
        for d in t['days']:
            if d['track']:
                with open(d['track'], 'w', encoding='utf-8') as fh:
                    fh.write(self.DAY_GPX % d['id'])
        return t

    def mdoc_of(self, t):
        return Doc(self.multiday.page(t, self.site).html)

    def stage_links(self, doc):
        """Per row of the stage table, the day's GPX link as (href, aria-label, download?) or None."""
        out = []
        for tr in doc.by_id('stages').find('tbody').find_all('tr'):
            cell = tr.find('td', cls='c-gpx')
            self.assertIsNotNone(cell, 'a stage row has no GPX cell')
            links = cell.find_all('a')
            self.assertLessEqual(len(links), 1)
            out.append((links[0]['href'], links[0]['aria-label'], 'download' in links[0]) if links else None)
        return out

    def chapter_links(self, doc):
        """Per day chapter, its 'Day N GPX' button as (text, href, download?) or None."""
        out = []
        for sec in doc.by_id('main').find_all('section', cls='mul-day'):
            links = sec.find_all('a', cls='mul-dgpx')
            self.assertLessEqual(len(links), 1)
            out.append((links[0].text(), links[0]['href'], 'download' in links[0]) if links else None)
        return out

    def test_the_fixture_tour_has_tracks_so_it_offers_them(self):
        # 2.1: 'Download all GPX' is there because a day has a track; the fixture tour's two days both do
        t = self.by['syn-tour']
        self.assertEqual([bool(d['track']) for d in t['days']], [True, True])
        self.assertIs(need(self, self.multiday, 'has_gpx')(t), True)
        self.assertEqual(gpx_links(self.mmain.find('div', cls='rep-actions')), [('Download all GPX', 'syn-tour.gpx')])
        bar = self.mdoc.find('nav', cls='bbar')
        self.assertEqual(bar_items(bar), [MAP, ('Days', '#overview'), ('GPX', 'syn-tour.gpx')])
        self.assertEqual(bar['style'], '--n:3')
        self.assertEqual(self.stage_links(self.mdoc), [('gpx/syn-tour-day-01.gpx', 'Download Day 1 GPX', True),
                                                      ('gpx/syn-tour-day-02.gpx', 'Download Day 2 GPX', True)])
        self.assertEqual(self.chapter_links(self.mdoc), [('Day 1 GPX', 'gpx/syn-tour-day-01.gpx', True), ('Day 2 GPX', 'gpx/syn-tour-day-02.gpx', True)])

    def test_a_day_without_a_track_has_no_link_and_the_tour_keeps_download_all(self):
        # 2.1: one trackless day among three: 'Download all GPX' stays (two days have tracks), and that day has no link
        # of its own, in the stage table or in its chapter, while the days on either side keep theirs
        t = self.trek('syn-trek-gap', (True, False, True), written=2)
        self.assertEqual([bool(d['track']) for d in t['days']], [True, False, True])
        self.assertIs(need(self, self.multiday, 'has_gpx')(t), True)
        gpx_href = need(self, self.multiday, 'gpx_href')
        self.assertEqual([gpx_href(t, d) for d in t['days']], ['gpx/syn-trek-gap-day-01.gpx', '', 'gpx/syn-trek-gap-day-03.gpx'])
        doc = self.mdoc_of(t)
        main = doc.by_id('main')
        actions = main.find('div', cls='rep-actions')
        self.assertEqual([(e.tag, e.text()) for e in actions.elements()], [('a', 'Day by day'), ('a', 'Download all GPX'), ('span', 'Copy link')])
        dl = actions.find_all('a')[1]
        self.assertEqual((dl['href'], dl.classes, 'download' in dl), ('syn-trek-gap.gpx', ['btn', 'btn--ink'], True))
        self.assertEqual(self.stage_links(doc), [('gpx/syn-trek-gap-day-01.gpx', 'Download Day 1 GPX', True), None,
                                                 ('gpx/syn-trek-gap-day-03.gpx', 'Download Day 3 GPX', True)])
        self.assertEqual(self.chapter_links(doc), [('Day 1 GPX', 'gpx/syn-trek-gap-day-01.gpx', True), None,
                                                   ('Day 3 GPX', 'gpx/syn-trek-gap-day-03.gpx', True)])
        # the day itself is still on the page, with its row, its chapter and its write-up
        self.assertEqual(len(doc.by_id('stages').find('tbody').find_all('tr')), 3)
        self.assertIsNotNone(main.by_id('day-2'))
        self.assertIn('Second synthetic paragraph', main.by_id('day-2').text())
        # every download on the page, in order: all days, the two rows, the two chapters, the phone bar
        self.assertEqual(gpx_links(doc.root), [('Download all GPX', 'syn-trek-gap.gpx'), ('', 'gpx/syn-trek-gap-day-01.gpx'),
                                               ('', 'gpx/syn-trek-gap-day-03.gpx'), ('Day 1 GPX', 'gpx/syn-trek-gap-day-01.gpx'),
                                               ('Day 3 GPX', 'gpx/syn-trek-gap-day-03.gpx'), ('GPX', 'syn-trek-gap.gpx')])
        self.assertNotIn('day-02.gpx', self.multiday.page(t, self.site).html)
        bar = doc.find('nav', cls='bbar')
        self.assertEqual(bar_items(bar), [MAP, ('Days', '#overview'), ('Report', '#day-2'), ('GPX', 'syn-trek-gap.gpx')])
        self.assertEqual(bar['style'], '--n:4')
        self.assertEqual(['download' in a for a in bar.find_all('a')], [False, False, False, True])

    def test_a_tour_without_any_day_track_offers_no_gpx_at_all(self):
        # 2.1: 'Download all GPX' only when at least one day has a track: with none there is no title action, no GPX item
        # in the phone bar (whose --n counts what it shows) and no .gpx link anywhere on the page
        t = self.trek('syn-trek-none', (False, False), written=1)
        self.assertEqual([d['track'] for d in t['days']], [None, None])
        self.assertIs(need(self, self.multiday, 'has_gpx')(t), False)
        page = self.multiday.page(t, self.site)
        doc = Doc(page.html)
        main = doc.by_id('main')
        self.assertEqual(page.url, 'trips/syn-trek-none/')
        actions = main.find('div', cls='rep-actions')
        self.assertEqual([(e.tag, e.text()) for e in actions.elements()], [('a', 'Day by day'), ('span', 'Copy link')])
        self.assertNotIn('Download all GPX', page.html)
        self.assertEqual(gpx_links(doc.root), [])
        self.assertNotIn('.gpx', page.html.lower())
        self.assertEqual([n for n in doc.root.walk() if 'download' in n], [])
        bar = doc.find('nav', cls='bbar')
        self.assertEqual(bar_items(bar), [MAP, ('Days', '#overview'), ('Report', '#day-1')])
        self.assertEqual(bar['style'], '--n:%d' % len(bar.find_all('a')))
        self.assertEqual(bar['style'], '--n:3')
        self.assertEqual(self.stage_links(doc), [None, None])
        self.assertEqual(self.chapter_links(doc), [None, None])
        # the page is otherwise whole: both days, the stage table with its (empty) GPX column, the share row
        self.assertEqual([s['data-day'] for s in main.find_all('section', cls='mul-day')], ['1', '2'])
        self.assertEqual(len(doc.by_id('stages').find('thead').find_all('th', cls='c-gpx')), 1)
        self.assertEqual(page.html.count(need(self, self.report, 'share_row')('trips/syn-trek-none/')), 1)
        # without a written day either, the bar is Map and Days alone
        bare = self.trek('syn-trek-bare-none', (False, False))
        bar = self.mdoc_of(bare).find('nav', cls='bbar')
        self.assertEqual((bar_items(bar), bar['style']), ([MAP, ('Days', '#overview')], '--n:2'))

    def test_the_bar_counts_its_items_with_and_without_the_gpx(self):
        # 2.1: multiday.bottom_bar's --n is the number of items it shows, whichever of Report and GPX the tour has
        bottom_bar = need(self, self.multiday, 'bottom_bar')
        cases = [('syn-bar-a', (True, True), 1, 4), ('syn-bar-b', (True, True), None, 3), ('syn-bar-c', (False, False), 2, 3),
                 ('syn-bar-d', (False, False), None, 2), ('syn-bar-e', (False, True), None, 3)]
        for slug, tracks, written, want in cases:
            with self.subTest(slug):
                t = self.trek(slug, tracks, written=written)
                nav = Doc(bottom_bar(t)).find('nav')
                links = nav.find_all('a')
                self.assertEqual(len(links), want)
                self.assertEqual(nav['style'], '--n:%d' % want)
                self.assertEqual([a['href'] for a in links if 'download' in a], [slug + '.gpx'] if any(tracks) else [])

    def test_the_build_writes_exactly_the_gpx_files_the_page_links_to(self):
        # 2.1 and 10: build.py writes no combined file when no day has a track, so a download is offered exactly when
        # its file is published: per day, and for 'Download all GPX'
        build = load_module(self, 'build')
        out = os.path.join(self.tmp, '_out')
        cases = {'syn-trek-gap': (True, False, True), 'syn-trek-none': (False, False), 'syn-trek-all': (True, True)}
        for slug, tracks in cases.items():
            self.trek(slug, tracks)
        with mock.patch.object(build, 'OUT', out), mock.patch.object(build, 'LINK', False):
            for slug in cases:   # a copy of the trip whose render folder is in the temp dir: the real rendered/ is not looked at
                build.copy_trip_assets(dict(self.by[slug], rendered=os.path.join(self.tmp, '_rendered', slug)))
        for slug, tracks in cases.items():
            with self.subTest(slug):
                t = self.by[slug]
                folder = os.path.join(out, 'trips', slug)
                written = sorted(os.path.relpath(os.path.join(d, f), folder).replace(os.sep, '/')
                                 for d, _dirs, files in os.walk(folder) for f in files if f.endswith('.gpx'))
                linked = sorted({href for _text, href in gpx_links(self.mdoc_of(t).root)})
                self.assertEqual(written, linked)
                self.assertEqual(slug + '.gpx' in written, any(tracks))
                if any(tracks):
                    with open(os.path.join(folder, slug + '.gpx'), encoding='utf-8') as fh:
                        combined = fh.read()
                    self.assertEqual(re.findall(r'<name>Synthetic day (\d+)</name>', combined), [d['id'] for d in t['days'] if d['track']])


# ---------------------------------------------------------------- Phase 6: a track whose maps are not drawn yet

RECORDINGS = 'Stats from the GPS recordings.'                                   # multiday.stats_note, plural
GPS_MAX_FILES = 'GPS max is the highest point in the GPX files, not a surveyed summit height.'


class NotRenderedMapTests(ReportFixture):
    """Phase 6 (resilience-12): a page whose track render.py has not drawn yet (--no-render, no internet) says so in
    place of the map instead of showing an empty map with a key and a caption for it.

    A multi-day trip with at least one day track and no rendered overview: #map is the goal page's empty box with the
    label 'Route map, all days', the sentence NOT_RENDERED_DAYS and the phones' copy of the stats note; no key row, no
    caption; 'Download all GPX' stays; and multiday.build makes no trips/<slug>/map/ page (a full-screen page round a
    map that is not drawn would be empty). Once the overview is rendered (render_overview) the map, its caption and its
    key are back, and so is the map page. A multi-day trip with no day track at all keeps the old empty map section and
    its map page, unchanged. A single-day report through report.build: no map page without a render, the box on the
    page, and a story keeps its 'View route' action, which leads to the box. The fixture tour syn-tour has two day tracks
    (empty GPX files) and, like every syn- trip, no render folder until a test points it at one."""

    def setUp(self):
        super().setUp()
        self.multiday = load_module(self, 'sitegen.pages.multiday')

    def box(self, label, text):
        """The #map section of a track without a rendered map, written out: the box and the sentence (Phase 10: the stats
        note stays under the strip on phones too, so the box holds no copy of it)."""
        return ('<section class="rep-map rep-map--empty" id="map" aria-label="%s"><div class="wrap"><div class="empty">%s<p>%s</p></div></div></section>'
                % (label, core.icon('map', 24), text))

    def bare_tour(self):
        """A two-day ski tour neither of whose days has a GPX."""
        return self.add('syn-trek-bare', kind='multi-day', activity='ski', date='2025-03-01', end_date='2025-03-02',
                        days=[{'title': 'Synthetic Day 1', 'date': '2025-03-01', 'track': False},
                              {'title': 'Synthetic Day 2', 'date': '2025-03-02', 'track': False}])

    def multiday_urls(self):
        return [p.url for p in self.multiday.build(self.site)]

    def test_a_tour_with_day_tracks_and_no_render_gets_the_box(self):
        t = self.by['syn-tour']
        self.assertEqual([bool(d['track']) for d in t['days']], [True, True])
        self.assertEqual(core.render_meta(t)['maps'], {})
        page = self.multiday.page(t, self.site)
        doc = Doc(page.html)
        sec = doc.by_id('map')
        self.assertEqual((sec.tag, sec.classes, sec['aria-label']), ('section', ['rep-map', 'rep-map--empty'], 'Route map, all days'))
        self.assertEqual(sec.find('div', cls='empty').find('p').text(), NOT_RENDERED_DAYS)
        self.assertIsNone(sec.find('p', cls='strip-note'))                     # the note is under the strip
        self.assertEqual(doc.by_id('stats').find('p', cls='strip-note').text(), '%s %s %s' % (RECORDINGS, GPS_MAX_FILES, HOW_TEXT))
        want = self.box('Route map, all days', NOT_RENDERED_DAYS)
        self.assertEqual(page.html.count(want), 1)
        # no map, no key row, no caption, no button to a full-screen page; the day chapters have no map, key or caption of
        # their own either (their maps are not drawn: the box says so for the whole trip)
        self.assertEqual(sec.find_all(cls='keyrow') + sec.find_all(cls='mapcap') + sec.find_all(cls='map'), [])
        self.assertEqual(doc.find_all(cls='mul-dmap-w') + doc.find_all(cls='mul-dmap') + doc.find_all(cls='mul-dcap'), [])
        self.assertEqual(doc.find_all(cls='keyrow'), [])
        self.assertEqual(doc.find_all(cls='mapcap'), [])
        self.assertNotIn('href="../../trips/syn-tour/map/"', page.html)
        self.assertNotIn(NOT_RENDERED, page.html)                         # the single-day sentence is not the tour's
        # the section stands where the map stood, and the GPX downloads stay
        self.assertInOrder(marks(doc.by_id('main')), ['title', 'stats', 'map', 'days-h'])
        actions = doc.by_id('main').find('div', cls='rep-actions')
        self.assertEqual(gpx_links(actions), [('Download all GPX', 'syn-tour.gpx')])
        self.assertEqual(bar_items(doc.find('nav', cls='bbar')), [MAP, ('Days', '#overview'), ('GPX', 'syn-tour.gpx')])

    def test_a_tour_with_day_tracks_and_no_render_has_no_map_page(self):
        urls = self.multiday_urls()
        self.assertIn('trips/syn-tour/', urls)
        self.assertNotIn('trips/syn-tour/map/', urls)

    def test_one_day_track_is_enough_for_the_box(self):
        t = self.add('syn-trek-one', kind='multi-day', activity='ski', date='2025-03-01', end_date='2025-03-02',
                     days=[{'title': 'Synthetic Day 1', 'date': '2025-03-01', 'track': False},
                           {'title': 'Synthetic Day 2', 'date': '2025-03-02'}])
        self.assertEqual([bool(d['track']) for d in t['days']], [False, True])
        sec = Doc(self.multiday.page(t, self.site).html).by_id('map')
        self.assertEqual(sec.classes, ['rep-map', 'rep-map--empty'])
        self.assertEqual(sec.find('div', cls='empty').find('p').text(), NOT_RENDERED_DAYS)
        self.assertNotIn('trips/syn-trek-one/map/', self.multiday_urls())

    def test_a_rendered_overview_brings_back_the_map_its_caption_its_key_and_the_map_page(self):
        t = self.by['syn-tour']
        render_overview(self.tmp, t)
        self.assertTrue(core.render_meta(t)['maps'])
        page = self.multiday.page(t, self.site)
        doc = Doc(page.html)
        self.assertEqual(len(doc.find_all(cls='mul-dmap-w')), 2)        # each day's map block is back with the render
        sec = doc.by_id('map')
        self.assertEqual((sec.tag, sec.classes, sec['aria-label']), ('section', ['rep-map', 'mul-map'], 'Route map, all days'))
        self.assertIsNotNone(sec.find('div', cls='mapcap'))
        self.assertTrue(sec.find_all('ul', cls='keyrow'))
        self.assertIsNone(sec.find('p', cls='strip-note'))             # Phase 10: the note stays under the strip
        self.assertIsNone(sec.find('div', cls='empty'))
        self.assertNotIn(NOT_RENDERED_DAYS, page.html)
        self.assertNotIn('rep-map--empty', page.html)
        self.assertIn('href="../../trips/syn-tour/map/"', page.html)
        self.assertEqual(gpx_links(doc.by_id('main').find('div', cls='rep-actions')), [('Download all GPX', 'syn-tour.gpx')])
        urls = self.multiday_urls()
        self.assertIn('trips/syn-tour/map/', urls)
        self.assertEqual(urls.index('trips/syn-tour/map/'), urls.index('trips/syn-tour/') + 1)

    def test_a_tour_without_any_day_track_keeps_the_old_empty_map_section_and_its_map_page(self):
        t = self.bare_tour()
        self.assertEqual([d['track'] for d in t['days']], [None, None])
        page = self.multiday.page(t, self.site)
        doc = Doc(page.html)
        sec = doc.by_id('map')
        self.assertEqual((sec.tag, sec.classes, sec['aria-label']), ('section', ['rep-map', 'mul-map'], 'Route map, all days'))
        self.assertIn('<div class="bleed"><div class="map map--report map--nowide"></div></div>', page.html)
        self.assertIsNotNone(sec.find('div', cls='mapcap'))
        self.assertTrue(sec.find_all('ul', cls='keyrow'))
        self.assertIsNone(sec.find('div', cls='empty'))
        self.assertNotIn(NOT_RENDERED_DAYS, page.html)
        self.assertNotIn('rep-map--empty', page.html)
        self.assertNotIn('Download all GPX', page.html)
        urls = self.multiday_urls()
        self.assertIn('trips/syn-trek-bare/', urls)
        self.assertIn('trips/syn-trek-bare/map/', urls)
        self.assertNotIn('trips/syn-tour/map/', urls)                    # the tour with day tracks, beside it, still has none

    def test_report_build_a_track_without_a_render_has_the_box_and_no_map_page(self):
        t = self.by['syn-story']
        self.assertTrue(t['track'])
        self.assertTrue(need(self, self.report, 'narrative')(t))
        self.assertEqual(core.render_meta(t)['maps'], {})
        pages = {p.url: p for p in self.report.build(self.site)}
        self.assertIn('trips/syn-story/', pages)
        self.assertNotIn('trips/syn-story/map/', pages)
        html_ = pages['trips/syn-story/'].html
        doc = Doc(html_)
        self.assertEqual(html_.count(self.box('Route map', NOT_RENDERED)), 1)
        self.assertEqual(doc.find_all(cls='keyrow') + doc.find_all(cls='mapcap'), [])
        # the story keeps 'View route', and it leads to the box; the GPX download stays
        self.assertEqual(html_.count(view_route_action()), 1)
        self.assertEqual(html_.count(gpx_title_action('syn-story')), 1)
        actions = [(a.text(), a['href']) for a in doc.by_id('main').find('div', cls='rep-actions').find_all('a')]
        self.assertEqual(actions, [('View route', '#map'), ('Download GPX', 'syn-story.gpx')])
        self.assertEqual(doc.by_id('map')['aria-label'], 'Route map')
        self.assertIn('rep-map--empty', doc.by_id('map').classes)
        # drawn, the same report gets its map page back
        self.render('syn-story')
        self.assertIn('trips/syn-story/map/', [p.url for p in self.report.build(self.site)])


# ---------------------------------------------------------------- Phase 4: no track, no route (contract-phase4.md 10.2, 10.3)

RECORDING = 'Stats from the GPS recording.'                                    # core.stats_note, sentence by sentence
GPS_MAX = 'GPS max is the highest point in the GPX file, not a surveyed summit height.'
AVG_SPEED = 'Average speed is distance divided by moving time.'
MOVING = 'Moving time leaves out stops.'               # Phase 10 (gap6-05): when the strip shows Moving
PACE = 'Pace is moving time divided by distance.'
MAP_ROW_ITEM = '<li><a class="rep-toc-a" href="#map">Map</a></li>'                          # the story section row's Map item
# the Route map section: the map with its key and caption, or (Phase 6, resilience-12) the box of a track not rendered yet
MAP_SECTION = re.compile(r'<section class="rep-map(?: rep-map--empty)?" id="map" aria-label="Route map">.*?</section>', re.S)
NOT_RENDERED = 'Map not rendered yet. The GPX file is published: use the Download GPX button.'
NOT_RENDERED_DAYS = 'Map not rendered yet. The GPX files of the days are published: use the Download all GPX button.'
STRIP_SECTION = re.compile(r'<section class="wrap rep-strip" id="stats" aria-label="Stats">.*?</section>', re.S)
DRAWING = re.compile(r'(?:^|/)trips/([^/]+)/(tile|g112|g64)\.svg$')                        # a trip's route drawing, as an <img> src
BBAR = re.compile(r'<nav class="bbar" aria-label="Report sections" style="--n:(\d+)">(.*?)</nav>', re.S)
# what a single-day report without a track neither says nor links (10.2): the two title actions, the map key's route
# symbol, the map caption's 'full track, not trimmed', and the two sentences of the stats note that speak of a recording
ROUTE_WORDS = ('View route', 'Download GPX', 'Route (GPX)', 'full track', 'GPS recording', 'GPX file')
ROUTE = ('Map', '#map')          # the section row's map item (Phase 10: named Map, as in the bar; 'Route' is retired)
REPORT_ROW, PHOTOS_ROW = REPORT, PHOTOS      # the section row names these two as the phone bar does


def view_route_action():
    """The story layout's 'View route' title action, exactly as report.page writes it."""
    return '<a class="btn" href="#map">%sView route</a>' % core.icon('map', 18)


def map_bar_item():
    """The phone bottom bar's Map item, exactly as report.bottom_bar writes it."""
    return '<a href="#map">%s<span>Map</span></a>' % core.icon('map', 24)


def stats_bar_item():
    """The phone bottom bar's Stats item, exactly as report.bottom_bar writes it."""
    return '<a href="#stats">%s<span>Stats</span></a>' % core.icon('beta', 24)


# Phase 9 (ia-19): on a page every stats note ends with this link to About's method, in that heading's own words
HOW = '<a href="../../about/#abo-how-h">How these reports are made</a>'          # from a trip page, trips/<slug>/
SECTION_HOW = '<a href="../about/#abo-how-h">How these reports are made</a>'      # from a section page (hiking/)
HOW_TEXT = 'How these reports are made'


def strip_note(sentences, cls='', how=HOW):
    """The stats note of these sentences as a page writes it (core.stats_note with the page's here: the sentences, then
    the link `how`; how='' for core.stats_note without here); '' for none (there is never an empty paragraph)."""
    return ('<p class="strip-note%s">%s</p>' % ((' ' + cls) if cls else '', ' '.join(sentences + ([how] if how else []))))\
        if sentences else ''


def drawings(node, slug=None):
    """The route drawings (tile.svg / g112.svg / g64.svg) a page or fragment shows as <img>, as (slug, name), in order;
    with slug, only that trip's."""
    found = [DRAWING.search(i['src'] or '') for i in node.find_all('img')]
    return [m.groups() for m in found if m and (slug is None or m.group(1) == slug)]


def render_overview(tmp, t):
    """Point a multi-day trip at a placeholder render folder in the temp dir holding its three overview maps (the
    caption and the key are drawn only under a rendered overview since Phase 6)."""
    folder = os.path.join(tmp, '_rendered', t['slug'])
    os.makedirs(folder, exist_ok=True)
    meta = {'maps': {}, 'charts': {}}
    for name, (w, h) in (('overview-wide', (1440, 560)), ('overview-col', (718, 440)), ('overview-phone', (390, 260))):
        meta['maps'][name] = {'w': w, 'h': h, 'png': name + '.webp', 'base': name + '.base.svg'}
        with open(os.path.join(folder, name + '.svg.html'), 'w', encoding='utf-8') as fh:
            fh.write('<svg width="%d" height="%d" viewBox="0 0 %d %d"></svg>' % (w, h, w, h))
    with open(os.path.join(folder, 'meta.json'), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh)
    t['rendered'] = folder


def without_track(body, slug, note, note_left, stats=True):
    """A single-day report page from <body> on with everything that needs a track taken out, and nothing else: the 'View
    route' and 'Download GPX' title actions, the whole Route map section (map, key rows, caption), the sentences of the
    stats note under the strip that speak of the recording (note -> note_left, lists of sentences), the section row's
    Map item, and the phone bar's Map and GPX items with its --n two lower; the bar itself when fewer than two items
    are left. stats=False (10.3): the report has no stats cells either, so the whole Stats strip goes as well, with the
    bar's Stats item. What the page of a report without a track must be, given the page of the same report with one."""
    out = body.replace(view_route_action(), '').replace(gpx_title_action(slug), '')
    out = MAP_SECTION.sub('', out)
    if stats:
        out = out.replace(strip_note(note), strip_note(note_left))
    else:
        out = STRIP_SECTION.sub('', out)
    out = out.replace(MAP_ROW_ITEM, '')

    def bar(m):
        k, items = int(m.group(1)), m.group(2)
        for gone in [map_bar_item(), gpx_bar_item(slug + '.gpx')] + ([] if stats else [stats_bar_item()]):
            k -= items.count(gone)
            items = items.replace(gone, '')
        return ('<nav class="bbar" aria-label="Report sections" style="--n:%d">%s</nav>' % (k, items)) if k >= 2 else ''
    return BBAR.sub(bar, out)


def expected_bar(t, gpx_href, has_beta, has_report, has_gallery, chart='', story=False, has_map=True, has_stats=True):
    """The phone bottom bar as contract-phase4.md 10.2 and 10.3 word it, written out independently of report.bottom_bar:
    the items in page order for the layout, the Map item only with a map, the Stats item (which stands in for a chart)
    only with a stats strip, the GPX item only with a file, --n the number shown, and no bar at all when fewer than
    two items are left."""
    chart_item = [('#profile', 'profile', 'Speed' if chart == 'speed' else 'Elevation')] if chart else \
        ([('#stats', 'beta', 'Stats')] if has_stats else [])
    the_map = [('#map', 'map', 'Map')] if has_map else []
    if story:
        if has_gallery:
            items = [('#report', 'report', 'Report')] + the_map + [('#photos', 'photo', 'Photos')]
        elif has_beta:
            items = [('#beta', 'beta', 'Beta'), ('#report', 'report', 'Report')] + the_map
        else:
            items = [('#report', 'report', 'Report')] + the_map + chart_item
    else:
        items = the_map + ([('#beta', 'beta', 'Beta')] if has_beta else chart_item)
        if has_report:
            items.append(('#report', 'report', 'Report'))
        elif has_gallery:
            items.append(('#photos', 'photo', 'Photos'))
    # Phase 10 (copy-09): in the order the sections run on the page, the strip's Stats first
    order = ('#stats', '#beta', '#report', '#map', '#profile', '#photos') if story else ('#stats', '#map', '#profile', '#beta', '#report', '#photos')
    items.sort(key=lambda it: order.index(it[0]))
    out = ['<a href="%s">%s<span>%s</span></a>' % (h, core.icon(ic, 24), lab) for h, ic, lab in items]
    if gpx_href:
        out.append('<a href="%s" download>%s<span>GPX</span></a>' % (gpx_href, core.icon('download', 24)))
    if len(out) < 2:
        return ''
    return '<nav class="bbar" aria-label="Report sections" style="--n:%d">%s</nav>' % (len(out), ''.join(out))


class NoTrackTests(ReportFixture):
    """contract-phase4.md 10.2 as amended by 10.3: a single-day report without track.gpx has no route. Its page has no
    'Download GPX' and no 'View route' title action, no Route map section at all, no Route item in the story section
    row, no Map and no GPX item in the phone bar (and no bar when a single item would be left), a stats note and a
    description that say nothing of a recording, a GPX file or a map, and no full-screen map page; a section page never
    features it. 10.3: when it has no stats cells either it has no Stats strip and no Stats item in the bar; and a rendered folder its track left behind is not shown anywhere (no
    map, chart, key, preload or route drawing). A report WITH a track is exactly what it was, rendered or not.

    both() builds the page of a fixture report, takes its track.gpx away, loads the site again and builds the page once
    more, so the two pages differ in the track alone. The render folder is the same on both sides."""

    # slug, its render folder (None: none; {}: the three maps), then for the page WITH its track the section row (None:
    # the compact layout has none) and the phone bar before its GPX item, and for the page WITHOUT it the title actions
    # before the copy link, the section row and the phone bar (None: no bar, fewer than two items would be left). Only
    # syn-story has stats (STATS_CELLS); the others lose their Stats strip with the track (10.3)
    # Phase 10 (copy-09): the section row and the bar name the sections from one table, in page order; the row's
    # Route and Trip details items are retired (the row is Report · Map · Elevation · Photos)
    CASES = (
        ('syn-story', {}, [REPORT_ROW, ROUTE, PHOTOS_ROW], [REPORT, MAP, PHOTOS],
         [], [REPORT_ROW, PHOTOS_ROW], [REPORT, PHOTOS]),
        ('syn-one', None, [REPORT_ROW, ROUTE], [STATS, REPORT, MAP],
         [], [REPORT_ROW], None),
        ('syn-one-beta', {}, [REPORT_ROW, ROUTE], [BETA_ITEM, REPORT, MAP],
         [], [REPORT_ROW], [BETA_ITEM, REPORT]),
        ('syn-two-tall', None, [REPORT_ROW, ROUTE, PHOTOS_ROW], [REPORT, MAP, PHOTOS],
         [], [REPORT_ROW, PHOTOS_ROW], [REPORT, PHOTOS]),
        ('syn-portrait', None, [REPORT_ROW, ROUTE], [STATS, REPORT, MAP],
         [], [REPORT_ROW], None),
        ('syn-words', None, None, [MAP, BETA_ITEM, REPORT], [('Read the report', '#report')], None, [BETA_ITEM, REPORT]),
        ('syn-photos', None, None, [STATS, MAP, PHOTOS], [], None, None),
        ('syn-tall-only', None, None, [STATS, MAP], [], None, None),
        ('syn-track', None, None, [STATS, MAP], [], None, None),
        ('syn-undated', None, None, [STATS, MAP], [], None, None),
    )
    STATS_CELLS = ('syn-story',)       # the fixture reports whose index.md states stats: the strip has cells
    # core.summary of each case: its first sentence (without the full stop) and its facts before the closing one. With a
    # track the closing fact is 'with map and GPX'; without, the summary ends where these end
    SUMMARY = {
        'syn-story': ('Hiking trip report: Synthetic Story, Synthetic Basin, Synthetic Range, Mon, Jun 1, 2026',
                      '7.5 mi, 2,625 ft gain, GPS max 9,514 ft'),
        'syn-one': ('Hiking trip report: Synthetic One Photo, Synthetic Range, Sun, May 10, 2026', ''),
        'syn-one-beta': ('Hiking trip report: Synthetic One Photo With Beta, Synthetic Range, Tue, May 5, 2026', ''),
        'syn-two-tall': ('Climbing trip report: Synthetic Two Portraits, Synthetic Range, Mon, Apr 20, 2026', ''),
        'syn-portrait': ('Hiking trip report: Synthetic Lone Portrait, Synthetic Range, Fri, Apr 10, 2026', ''),
        'syn-words': ('Hiking trip report: Synthetic Words Only, Synthetic Range, Sun, Mar 1, 2026', ''),
        'syn-photos': ('Mountain biking trip report: Synthetic Photos Only, Synthetic Range, Sun, Feb 1, 2026', ''),
        'syn-tall-only': ('Hiking trip report: Synthetic Portrait Only, Synthetic Range, Tue, Jan 20, 2026', ''),
        'syn-track': ('Hiking trip report: Synthetic Track Only, Synthetic Range, Mon, Dec 1, 2025', ''),
        'syn-undated': ('Hiking trip report: Synthetic Undated Track, Synthetic Range', ''),
    }

    def both(self, slug, render=None):
        """(the page with its track, the page without it), for one report folder."""
        if render is not None:
            self.render(slug, **render)
        self.assertTrue(self.by[slug]['track'], '%s: the fixture report has no track to take away' % slug)
        with_ = self.page(slug).html
        os.remove(os.path.join(self.tmp, slug, 'track.gpx'))
        self.load_site()
        self.assertIsNone(self.by[slug]['track'], slug)
        if render is not None:
            self.render(slug, **render)
        return with_, self.page(slug).html

    @staticmethod
    def head_but_descriptions(html_):
        """The head's elements in order, the description tags left out (test_a_page_without_a_track_lacks_exactly_this
        compares those word for word)."""
        skip = ({'name': 'description'}, {'property': 'og:description'}, {'type': 'application/ld+json'})
        return [(n.tag, sorted(n.attrs.items()), n.text(clean=False)) for n in Doc(html_).find('head').elements()
                if not any(all(n[k] == v for k, v in s.items()) for s in skip)]

    @staticmethod
    def descriptions(html_):
        """(meta description, og:description) of a page."""
        head = Doc(html_).find('head')
        return (head.find('meta', attrs={'name': 'description'})['content'],
                head.find('meta', attrs={'property': 'og:description'})['content'])

    def note_of(self, slug):
        """(the stats note's sentences with a track, the ones left without) for a fixture report: none of them has a beta
        row labelled Track, is flat water or states a distance and a moving time, so the note is the two sentences about
        the recording and nothing is left of it without one (10.3: a mountain bike report gets the average-speed
        sentence only with both values; syn-photos has neither)."""
        st = self.by[slug]['stats']
        self.assertFalse(st.get('distance_km') and st.get('moving_s'), slug)
        return [RECORDING, GPS_MAX], []

    def assertNoRoute(self, slug):
        """Item by item, what contract 10.2 and 10.3 say the page of a single-day report without a track does not have,
        whatever its rendered folder holds, and that what it does link to on itself is there."""
        html_, doc = self.page(slug).html, self.doc(slug)
        main = self.main(slug)
        self.assertIsNone(doc.by_id('map'), '%s has an element with id="map"' % slug)
        self.assertNotIn('id="map"', html_)
        self.assertEqual(doc.find_all(cls='rep-map'), [])
        self.assertEqual(doc.find_all(cls='mapcap'), [])
        self.assertEqual(doc.find_all(cls='rep-note-ph'), [])
        self.assertEqual(doc.find('body').find_all(cls='map'), [])
        self.assertEqual(doc.find('body').find_all(cls='mv'), [])
        # 10.3: nothing a render folder holds: no chart section, no key of any kind, no preload of a map image, and
        # no drawing of the route (the phone app bar would carry its glyph)
        self.assertIsNone(doc.by_id('profile'), '%s has an element with id="profile"' % slug)
        self.assertEqual(doc.find_all(cls='rep-prof'), [])
        self.assertEqual(doc.find_all(cls='chart'), [])
        self.assertEqual(doc.find_all(cls='keyrow'), [])
        self.assertEqual([ln['href'] for ln in doc.find('head').find_all('link', attrs={'rel': 'preload'}) if '/map/' in (ln['href'] or '')], [])
        self.assertEqual(drawings(doc, slug), [])
        self.assertEqual([i['src'] for i in doc.find_all('img') if '/%s/map/' % slug in (i['src'] or '')], [])
        # 10.3: the Stats strip is there exactly when the report states a stat, and is linked only then
        strips = doc.find_all('section', cls='rep-strip')
        self.assertEqual(len(strips), 1 if core.strip_cells(self.by[slug]) else 0)
        self.assertEqual(doc.by_id('stats') is not None, bool(strips))
        if not strips:
            self.assertNotIn('#stats', html_)
            self.assertNotIn('id="stats"', html_)
            self.assertEqual(doc.find_all(cls='strip') + doc.find_all(cls='strip-note'), [])
            self.assertNotIn('Trip stats', html_)
            self.assertNotIn('<span>Stats</span>', html_)
        else:
            self.assertTrue(strips[0].find_all('div', cls='strip-c'), '%s has a stats strip without a cell' % slug)
        hrefs = [n['href'] for n in doc.root.walk() if 'href' in n]
        self.assertNotIn('#map', hrefs)
        self.assertNotIn('href="#map"', html_)
        # no link ends in 'map/' but the header's and the footer's to the site's own Map page; none leads to the
        # report's full-screen map page (trips/<slug>/map/), which is not built
        self.assertEqual([h for h in (a['href'] or '' for a in main.find_all('a')) if h.endswith('map/')], [])
        self.assertEqual(sorted(set(h for h in hrefs if h.endswith('map/'))), ['../../map/'])
        here = 'trips/%s/' % slug
        resolved = [os.path.normpath(os.path.join(here, h.split('#')[0])).replace(os.sep, '/') for h in hrefs
                    if '://' not in h and not h.startswith('#')]
        self.assertEqual([r for r in resolved if r.startswith('trips/%s/map' % slug)], [])
        self.assertNotIn('.gpx', html_.lower())
        self.assertEqual(gpx_links(doc.root), [])
        self.assertEqual([n for n in doc.root.walk() if 'download' in n], [])
        for words in ROUTE_WORDS:
            self.assertNotIn(words, html_, '%s says %r' % (slug, words))
            self.assertNotIn(words, doc.text(), '%s says %r' % (slug, words))
        ids = [n['id'] for n in doc.root.walk() if n['id']]
        self.assertEqual(len(ids), len(set(ids)))
        for h in hrefs:
            if h.startswith('#'):
                self.assertIn(h[1:], ids, '%s links %s, which is not an id on the page' % (slug, h))
        # the stats note is a paragraph with something to say, or not there
        for p in doc.find_all('p', cls='strip-note'):
            self.assertTrue(p.text(), '%s has an empty stats note' % slug)
        self.assertNotRegex(html_, r'<p class="strip-note[^"]*">\s*</p>')
        self.assertLessEqual(len(doc.find_all('p', cls='strip-note')), 1)
        for text in self.descriptions(html_):
            self.assertNotIn('GPX', text)
            self.assertNotIn('map', text.lower())

    def test_the_cases_cover_both_layouts(self):
        narrative = need(self, self.report, 'narrative')
        self.assertEqual([narrative(self.by[c[0]]) for c in self.CASES], [True] * 5 + [False] * 5)
        self.assertEqual(sorted(c[0] for c in self.CASES), sorted(set(SINGLE) - {'syn-explicit'}))
        self.assertEqual(sorted(self.SUMMARY), sorted(c[0] for c in self.CASES))

    def test_no_download_gpx_and_no_view_route_title_action(self):
        # 10.2: no 'Download GPX' and no 'View route' title action; 'Read the report' (compact, with a write-up) and the
        # copy link stay
        for slug, render, _row, _bar, actions, _row2, _bar2 in self.CASES:
            with self.subTest(slug):
                with_, without = self.both(slug, render)
                gpx, route = ('Download GPX', slug + '.gpx'), ('View route', '#map')
                before = [(a.text(), a['href']) for a in Doc(with_).by_id('main').find('div', cls='rep-actions').find_all('a')]
                self.assertEqual(before.count(gpx), 1)            # the controls are there because the track is ...
                self.assertEqual(before.count(route), 1 if need(self, self.report, 'narrative')(self.by[slug]) else 0)
                after = self.actions(slug)
                self.assertNotIn(gpx, after)                      # ... and gone with it
                self.assertNotIn(route, after)
                self.assertEqual([text for text, _v in after if text in ('Download GPX', 'View route')], [])
                self.assertEqual(after, actions + [('copy', core.SITE_URL + 'trips/%s/' % slug)])
                self.assertEqual([x for x in after if x[0] != 'copy'], [x for x in before if x not in (gpx, route)])
                self.assertNotIn('Download GPX', without)
                self.assertNotIn('View route', without)

    def test_no_map_and_no_gpx_item_in_the_phone_bar_and_the_bar_counts_what_it_shows(self):
        # 10.2: no Map item and no GPX item in the phone bottom bar; --n counts only what is shown; with fewer than two
        # items left there is no bar at all (one link is not navigation). 10.3: and no Stats item for a report that
        # states no stats, since it has no strip to go to
        for slug, render, _row, bar_with, _actions, _row2, bar in self.CASES:
            with self.subTest(slug):
                with_, without = self.both(slug, render)
                gpx = ('GPX', slug + '.gpx')
                before = Doc(with_).find('nav', cls='bbar')
                self.assertEqual(bar_items(before), bar_with + [gpx])
                self.assertEqual(before['style'], '--n:%d' % len(before.find_all('a')))
                gone = (MAP, gpx) + (() if slug in self.STATS_CELLS else (STATS,))
                left = [x for x in bar_items(before) if x not in gone]
                self.assertEqual(len(left), len(bar_items(before)) - 2 - (1 if STATS in bar_with and STATS in gone else 0))
                navs = self.doc(slug).find_all('nav', cls='bbar')
                if len(left) < 2:
                    self.assertIsNone(bar)
                    self.assertEqual(navs, [])
                    self.assertNotIn('bbar', without)
                    self.assertNotIn('Report sections', without)
                    continue
                self.assertEqual(len(navs), 1)
                after = navs[0]
                self.assertEqual(bar_items(after), bar)
                self.assertEqual(bar_items(after), left)
                self.assertNotIn('GPX', [lab for lab, _h in bar_items(after)])
                self.assertNotIn('Map', [lab for lab, _h in bar_items(after)])
                self.assertEqual(after['style'], '--n:%d' % len(after.find_all('a')))
                self.assertEqual(after['style'], '--n:%d' % len(left))
                self.assertEqual([a for a in after.find_all('a') if 'download' in a], [])
                ids = {n['id'] for n in self.doc(slug).root.walk() if n['id']}
                for a in after.find_all('a'):
                    self.assertTrue((a['href'] or '').startswith('#'))
                    self.assertIn(a['href'][1:], ids)

    def test_no_map_item_in_the_section_row(self):
        # 10.2: the story section row lists exactly the sections the page has; without a track there is no map, so no
        # Map item (Phase 10: the row names no Beta block and no strip any more)
        for slug, render, row_with, _bar, _actions, row, _bar2 in self.CASES:
            with self.subTest(slug):
                with_, without = self.both(slug, render)
                before = Doc(with_).by_id('main').find_all('nav', cls='rep-toc')
                after = self.main(slug).find_all('nav', cls='rep-toc')
                if row is None:                                   # the compact layout never had a section row
                    self.assertEqual((before, after), ([], []))
                    self.assertNotIn('rep-toc', without)
                    continue
                self.assertEqual([(a.text(), a['href']) for a in before[0].find_all('a')], row_with)
                self.assertEqual(self.toc(slug), row)
                self.assertEqual(self.toc(slug), [x for x in row_with if x != ROUTE])
                self.assertEqual(len(after), 1)
                ids = {n['id'] for n in self.doc(slug).root.walk() if n['id']}
                self.assertEqual([h[1:] for _t, h in self.toc(slug) if h[1:] not in ids], [])
                section_nav = need(self, self.report, 'section_nav')
                self.assertEqual(without.count(section_nav(True, PHOTOS_ROW in row, False, '')), 1)

    def test_no_gpx_link_anywhere_on_the_page(self):
        # 2.1 / 10.2: no GPX control anywhere: no .gpx href and no download attribute in the whole document; no map either
        for slug, render, _row, _bar, _actions, _row2, _bar2 in self.CASES:
            with self.subTest(slug):
                with_, without = self.both(slug, render)
                self.assertEqual(gpx_links(Doc(with_).root), [('Download GPX', slug + '.gpx'), ('GPX', slug + '.gpx')])
                doc = self.doc(slug)
                self.assertEqual(gpx_links(doc.root), [])
                self.assertEqual([n for n in doc.root.walk() if 'download' in n], [])
                self.assertNotIn('.gpx', without.lower())
                self.assertNoRoute(slug)
                # ... all of which the page with the track has: the list is what the track brings, not what no page has.
                # The key's route symbol and the caption come with a rendered map; without one the box stands there
                for needle in ('id="map"', 'href="#map"', 'Download GPX', 'GPS recording', 'GPX file') + (
                        ('Route (GPX)', 'full track') if render is not None else (NOT_RENDERED,)):
                    self.assertIn(needle, with_)
                # ... and, once rendered, the phone map's link to the full-screen map page
                self.assertEqual('href="../../trips/%s/map/"' % slug in with_, render is not None)

    def test_a_page_without_a_track_lacks_exactly_this(self):
        # 10.2: 'a report WITH a track is exactly as before', and what the same report lacks without it is a list: from
        # <body> on, the page without a track is the page with one minus that list (without_track), byte for byte. The
        # head differs in nothing but the description, which loses its closing fact 'with map and GPX'. 10.3 adds to
        # the list, for a report that states no stats: the Stats strip and the two links that led to it
        for slug, render, _row, _bar, _actions, _row2, _bar2 in self.CASES:
            with self.subTest(slug):
                with_, without = self.both(slug, render)
                story = need(self, self.report, 'narrative')(self.by[slug])
                note, left = self.note_of(slug)
                body_with, body = with_.split('</head>', 1)[1], without.split('</head>', 1)[1]
                # everything on the list is on the page with a track, once (Phase 10: the note too; phones show it under the strip)
                self.assertEqual(body_with.count(view_route_action()), 1 if story else 0)
                self.assertEqual(body_with.count(gpx_title_action(slug)), 1)
                self.assertEqual(body_with.count(MAP_ROW_ITEM), 1 if story else 0)
                self.assertEqual(body_with.count(map_bar_item()), 1)
                self.assertEqual(body_with.count(gpx_bar_item(slug + '.gpx')), 1)
                self.assertEqual(body_with.count(strip_note(note)), 1)
                sections = MAP_SECTION.findall(body_with)
                self.assertEqual(len(sections), 1)
                self.assertEqual(sections[0].count('<section'), 1)
                self.assertNotIn('rep-note-ph', body_with)
                self.assertEqual(len(BBAR.findall(body_with)), 1)
                # the Stats strip is on the page with a track whether or not the report states a stat, as it always was:
                # without cells it is the empty list and the note
                stats = slug in self.STATS_CELLS
                self.assertEqual(bool(core.strip_cells(self.by[slug])), stats)
                strips = STRIP_SECTION.findall(body_with)
                self.assertEqual(len(strips), 1)
                self.assertEqual(strips[0].count('<section'), 1)
                if not stats:
                    self.assertEqual(strips[0], '<section class="wrap rep-strip" id="stats" aria-label="Stats">'
                                                '<dl class="strip" style="--cells:1" aria-label="Trip stats"></dl>%s</section>' % strip_note(note))
                self.assertEqual(body_with.count(stats_bar_item()), 1 if STATS in _bar else 0)
                self.assertEqual(body, without_track(body_with, slug, note, left, stats=stats))
                self.assertNotEqual(body, without_track(body_with, slug, note, left, stats=not stats))
                self.assertNotEqual(without, with_)
                # the sections that do not need the track are all still there, under the same ids and in the same order
                ids = lambda html_: [n['id'] for n in Doc(html_).root.walk() if n['id']]   # noqa: E731
                gone = set(n['id'] for n in Doc(sections[0]).root.walk() if n['id']) | {'map'} | (set() if stats else {'stats'})
                self.assertEqual(ids(without), [i for i in ids(with_) if i not in gone])
                self.assertIn('map', ids(with_))
                self.assertIn('stats', ids(with_))
                # the head: the same elements, and the description without its closing fact
                self.assertEqual(self.head_but_descriptions(without), self.head_but_descriptions(with_))
                self.assertNotIn('ld+json', with_)
                first, facts = self.SUMMARY[slug]
                ex = core.excerpt(self.by[slug], 400)
                tail = (' ' + ex) if ex else ''
                closing = (facts + ', ' if facts else '') + 'with map and GPX'
                want_with = core.clip_words('%s. %s.%s' % (first, closing, tail), 155)
                want = core.clip_words('%s.%s%s' % (first, (' %s.' % facts) if facts else '', tail), 155)
                self.assertEqual(self.descriptions(with_), (want_with, want_with))
                self.assertEqual(self.descriptions(without), (want, want))
                self.assertIn('with map and GPX.', want_with)
                self.assertNotIn('GPX', want)
                self.assertNotIn('map', want)

    def test_the_map_section_of_a_report_with_a_track_is_what_it_was(self):
        # 10.2: a report with a track and a rendered map is exactly as before: the Route map section is the map block,
        # the two key rows, the caption and the phones' copy of the stats note, in the place its layout gives it, and the
        # map is the page's eager image only when no photo leads. Phase 6 (resilience-12): while the track is not
        # rendered the section is the 'Map not rendered yet' box (the goal page's), with the phones' copy of the note
        # and no map, key or caption; the section stays where it was and the Download GPX action stays
        variants = [('map-wide', 'wide'), ('map-col', 'col'), ('map-phone', 'phone')]
        for slug, rendered in (('syn-story', True), ('syn-story', False), ('syn-portrait', False), ('syn-words', True), ('syn-words', False),
                               ('syn-photos', True), ('syn-track', False), ('syn-undated', True)):
            with self.subTest(slug, rendered=rendered):
                if rendered:
                    self.render(slug)
                else:
                    self.by[slug]['rendered'] = os.path.join(self.tmp, '_rendered', 'never-' + slug)
                    self.pages.pop(slug, None)
                    self.docs.pop(slug, None)
                t = self.by[slug]
                self.assertTrue(t['track'])
                meta = core.render_meta(t)
                self.assertEqual(sorted(meta['maps']), ['map-col', 'map-phone', 'map-wide'] if rendered else [])
                hero = self.hero(slug) is not None
                block = core.map_block(t, t['url'], variants, t['url'] + 'map/', 'm', eager=not hero,
                                       cls='map--report' + ('' if rendered else ' map--nowide'),
                                       fullscreen_href='../../trips/%s/map/' % slug)
                self.assertEqual('href="../../trips/%s/map/"' % slug in block, rendered)
                if not rendered:
                    self.assertEqual(block, '<div class="map map--report map--nowide"></div>')
                    want = ('<section class="rep-map rep-map--empty" id="map" aria-label="Route map"><div class="wrap"><div class="empty">'
                            '%s<p>%s</p></div></div></section>' % (core.icon('map', 24), NOT_RENDERED))
                else:
                    # Phase 10 (gap6-04): no copy of the stats note under the caption; phones show it under the strip.
                    # Phase 11 (gap1-02): 'Open the full map' between the key rows and the caption (a fixture render draws
                    # no route path, so its address names no #route-start)
                    want = ('<section class="rep-map" id="map" aria-label="Route map"><div class="bleed">%s</div><div class="wrap">%s%s%s</div></section>'
                            % (block, core.key_rows(self.report.key_items(t, meta), self.report.key_items(t, meta, phone=True)),
                               core.map_full_link('../../trips/%s/map/' % slug),
                               # Phase 12 (gap4-03): 'See on the <Region> map' after the caption, to the report's row
                               self.report.map_caption(t) + core.see_on_map(t['url'], t)))
                html_ = self.page(slug).html
                self.assertEqual(MAP_SECTION.findall(html_), [want])
                self.assertEqual('fetchpriority="high"' in want, rendered and not hero)
                story = need(self, self.report, 'narrative')(t)
                self.assertInOrder(marks(self.main(slug)), ['stats', 'report', 'map'] if story else ['stats', 'map'])
                self.assertEqual(self.actions(slug)[-2], ('Download GPX', slug + '.gpx'))
                if rendered:
                    self.assertEqual(self.caption(slug)[-len(CREDIT) - 2:-len(CREDIT)], ['full track, not trimmed', 'North up'])
                else:
                    self.assertEqual(self.doc(slug).find_all(cls='mapcap') + self.doc(slug).find_all(cls='keyrow'), [])

    def test_reports_written_without_a_track(self):
        # plan 12.5: fixtures of the missing case, in both layouts, written without a track from the start: a story
        # with a lead photo, a story without one, a compact report with a write-up, a bare one, and a bare mountain
        # bike report whose beta has a Track row (the one sentence its stats note keeps company with)
        mk = helpers.make_trip
        mk(self.tmp, 'syn-nt-lead', title='Synthetic Trackless Story', date='2025-06-19', region=REGION, body=WRITEUP, beta=BETA,
           stats={'distance_km': 12.0, 'gain_m': 800, 'high_m': 2900, 'low_m': 2100},
           photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one'), photo('photos/02.webp', LANDSCAPE, alt='Synthetic photo two')])
        mk(self.tmp, 'syn-nt-tall', title='Synthetic Trackless Portrait', date='2025-06-18', region=REGION, body=WRITEUP,
           photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic photo one')])
        mk(self.tmp, 'syn-nt-words', title='Synthetic Trackless Words', date='2025-06-17', region=REGION, body=WRITEUP)
        mk(self.tmp, 'syn-nt-bare', title='Synthetic Trackless Bare', date='2025-06-16', region=REGION)
        mk(self.tmp, 'syn-nt-ride', title='Synthetic Trackless Ride', activity='mtb', date='2025-06-15', region=REGION,
           beta=[{'label': 'Track', 'value': TRACK_NOTE}], stats={'distance_km': 20.0, 'moving': '1:00'})
        self.load_site()
        slugs = ['syn-nt-lead', 'syn-nt-tall', 'syn-nt-words', 'syn-nt-bare', 'syn-nt-ride']
        self.assertEqual([self.by[s]['track'] for s in slugs], [None] * 5)
        self.assertEqual([need(self, self.report, 'narrative')(self.by[s]) for s in slugs], [True, True, False, False, False])
        self.assertEqual([self.hero(s) is not None for s in slugs], [True, False, False, False, False])
        # slug: title actions before the copy link, the section row, the phone bar, the ids of its sections, its stats
        # note. 10.3: only the first and the last state stats; the other three have no Stats strip, so no Stats bar item
        # led there, and a bar of Report alone is no bar (Phase 10: the row names no Beta block or strip)
        want = {'syn-nt-lead': ([], [REPORT_ROW, PHOTOS_ROW], [REPORT, PHOTOS], ['title', 'hero', 'stats', 'beta', 'report', 'photos'], ''),
                'syn-nt-tall': ([], [REPORT_ROW], None, ['title', 'report'], ''),
                'syn-nt-words': ([('Read the report', '#report')], None, None, ['title', 'report'], ''),
                'syn-nt-bare': ([], None, None, ['title'], ''),
                'syn-nt-ride': ([], None, None, ['title', 'stats'], 'Track: %s. %s' % (TRACK_NOTE, AVG_SPEED))}
        self.assertEqual([bool(core.strip_cells(self.by[s])) for s in slugs], [True, False, False, False, True])
        for slug, (actions, row, bar, sections, note) in want.items():
            with self.subTest(slug):
                html_ = self.page(slug).html
                self.assertEqual(self.page(slug).url, 'trips/%s/' % slug)
                self.assertNoRoute(slug)
                self.assertEqual(self.actions(slug), actions + [('copy', core.SITE_URL + 'trips/%s/' % slug)])
                if row is None:
                    self.assertEqual(self.main(slug).find_all('nav', cls='rep-toc'), [])
                else:
                    self.assertEqual(self.toc(slug), row)
                navs = self.doc(slug).find_all('nav', cls='bbar')
                if bar is None:
                    self.assertEqual(navs, [])
                    self.assertNotIn('class="bbar"', html_)
                else:
                    self.assertEqual([(bar_items(n), n['style']) for n in navs], [(bar, '--n:%d' % len(bar))])
                self.assertEqual([m for m in marks(self.main(slug)) if m in LEGACY_IDS + ('hero',)], sections)
                notes = self.doc(slug).find_all('p', cls='strip-note')
                self.assertEqual([p.text() for p in notes], ['%s %s' % (note, HOW_TEXT)] if note else [])
                self.assertEqual(html_.count('strip-note'), 1 if note else 0)
                if note:
                    self.assertIs(notes[0].parent, self.doc(slug).by_id('stats'))
        # their descriptions: the summary's first sentence and the facts the content has, then the write-up; nothing else
        ex = core.excerpt(self.by['syn-nt-words'], 400)
        self.assertEqual(self.descriptions(self.page('syn-nt-lead').html)[0],
                         core.clip_words('Hiking trip report: Synthetic Trackless Story, Synthetic Range, Thu, Jun 19, 2025. '
                                         '7.5 mi, 2,625 ft gain, GPS max 9,514 ft. ' + ex, 155))
        self.assertEqual(self.descriptions(self.page('syn-nt-words').html)[0],
                         core.clip_words('Hiking trip report: Synthetic Trackless Words, Synthetic Range, Tue, Jun 17, 2025. ' + ex, 155))
        self.assertEqual(self.descriptions(self.page('syn-nt-bare').html),
                         ('Hiking trip report: Synthetic Trackless Bare, Synthetic Range, Mon, Jun 16, 2025.',) * 2)
        self.assertEqual(self.descriptions(self.page('syn-nt-ride').html),
                         ('Mountain biking trip report: Synthetic Trackless Ride, Synthetic Range, Sun, Jun 15, 2025. 12.4 mi.',) * 2)
        # their neighbours with tracks keep everything (the pager and 'More like this' link reports, never files)
        self.assertEqual(gpx_links(self.doc('syn-track').root), [('Download GPX', 'syn-track.gpx'), ('GPX', 'syn-track.gpx')])
        self.assertIsNotNone(self.doc('syn-track').by_id('map'))
        self.assertEqual(bar_items(self.bbar('syn-track')), [STATS, MAP, ('GPX', 'syn-track.gpx')])

    def test_the_stats_strip_of_a_report_without_a_track(self):
        # 10.3: a report without a track has the Stats strip exactly when it states a stat. (no stats, a distance, a
        # distance and a moving time) x (story, compact) x (beta rows or not), on mountain bike reports, whose note
        # carries the one sentence that needs both values: the strip section, the note, the section row and the bar
        mk = helpers.make_trip
        stats_of = {'none': None, 'dist': {'distance_km': 20.0}, 'both': {'distance_km': 20.0, 'moving': '2:00'}}
        labels_of = {'none': [], 'dist': ['Distance'], 'both': ['Distance', 'Moving', 'Avg speed']}
        cases = []
        for k, (stats, story, beta) in enumerate(itertools.product(('none', 'dist', 'both'), (True, False), (True, False))):
            slug = 'syn-st-%s-%s-%s' % (stats, 'story' if story else 'compact', 'beta' if beta else 'plain')
            meta = dict(title='Synthetic %s' % slug[7:].replace('-', ' ').title(), activity='mtb', date='2025-07-%02d' % (k + 1),
                        region=REGION, body=WRITEUP)
            if stats_of[stats]:
                meta['stats'] = stats_of[stats]
            if beta:
                meta['beta'] = BETA
            if story:
                meta['photos'] = [photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one')]
            mk(self.tmp, slug, **meta)
            cases.append((slug, stats, story, beta))
        self.load_site()
        self.assertEqual(len(cases), 12)
        for slug, stats, story, beta in cases:
            with self.subTest(slug):
                t = self.by[slug]
                self.assertIsNone(t['track'])
                self.assertEqual(need(self, self.report, 'narrative')(t), story)
                html_, doc = self.page(slug).html, self.doc(slug)
                self.assertNoRoute(slug)
                # the strip section: not there without a stat; else the cells the content has and, only with a
                # distance and a moving time, the sentence about the value derived from them
                note = [AVG_SPEED] if stats == 'both' else []
                found = STRIP_SECTION.findall(html_)
                if stats == 'none':
                    self.assertEqual(found, [])
                    self.assertIsNone(doc.by_id('stats'))
                    self.assertNotIn('strip', [c for n in doc.find('body').walk() for c in n.classes])
                else:
                    self.assertEqual(found, ['<section class="wrap rep-strip" id="stats" aria-label="Stats">%s%s</section>'
                                             % (core.strip(core.strip_cells(t)), strip_note(note))])
                    self.assertEqual([dt.text() for dt in doc.by_id('stats').find_all('dt')], labels_of[stats])
                    self.assertEqual(doc.by_id('stats').find('dl')['style'], '--cells:%d' % len(labels_of[stats]))
                self.assertEqual([p.text() for p in doc.find_all('p', cls='strip-note')], [x + ' ' + HOW_TEXT for x in note])
                self.assertEqual(html_.count('Average speed is'), len(note))
                # the section row (story): Report alone, with no map (Phase 10: the row names no Beta block or strip)
                if story:
                    self.assertEqual(self.toc(slug), [REPORT_ROW])
                else:
                    self.assertEqual(self.main(slug).find_all('nav', cls='rep-toc'), [])
                # the bar: Beta, else Stats when there is a strip, with Report; one item is no bar
                if story:
                    bar = [BETA_ITEM, REPORT] if beta else ([STATS, REPORT] if stats != 'none' else [REPORT])   # page order
                else:
                    bar = ([BETA_ITEM] if beta else ([STATS] if stats != 'none' else [])) + [REPORT]
                navs = doc.find_all('nav', cls='bbar')
                if len(bar) < 2:
                    self.assertEqual(navs, [])
                else:
                    self.assertEqual([(bar_items(n), n['style']) for n in navs], [(bar, '--n:%d' % len(bar))])
                self.assertEqual('<span>Stats</span>' in html_, STATS in bar and len(bar) > 1)
        # the same three sets of stats on flat water (the pace sentence) and on a hike (no derived value, so no sentence)
        for act, extra, both_labels, sentence in (('other', {'subtype': 'SUP'}, ['Distance', 'Moving', 'Avg pace'], [PACE]),
                                                  ('hike', {}, ['Distance', 'Moving'], [])):
            for k, stats in enumerate(('none', 'dist', 'both')):
                slug = 'syn-st-%s-%s' % (act, stats)
                meta = dict(title='Synthetic %s %s' % (act, stats), activity=act, date='2025-08-%02d' % (k + 1), region=REGION, **extra)
                if stats_of[stats]:
                    meta['stats'] = stats_of[stats]
                mk(self.tmp, slug, **meta)
            self.load_site()
            for stats in ('none', 'dist', 'both'):
                with self.subTest(act=act, stats=stats):
                    slug = 'syn-st-%s-%s' % (act, stats)
                    doc = self.doc(slug)
                    self.assertNoRoute(slug)
                    labels = {'none': None, 'dist': ['Distance'], 'both': both_labels}[stats]
                    if labels is None:
                        self.assertIsNone(doc.by_id('stats'))
                    else:
                        self.assertEqual([dt.text() for dt in doc.by_id('stats').find_all('dt')], labels)
                    self.assertEqual([p.text() for p in doc.find_all('p', cls='strip-note')],
                                     [x + ' ' + HOW_TEXT for x in sentence] if stats == 'both' else [])
                    self.assertEqual(doc.find_all('nav', cls='bbar'), [])          # Stats alone, or nothing, is no bar

    def test_a_tracked_report_without_stats_keeps_its_strip(self):
        # 10.3: a report WITH a track always has the Stats strip, even with no cell: byte for byte the section it was,
        # with its Stats bar item. (Every fixture report but syn-story is one: the layout,
        # bar and section-row tests above this class pin the rest of those pages.)
        note = strip_note([RECORDING, GPS_MAX])
        self.assertEqual(note, '<p class="strip-note">Stats from the GPS recording. GPS max is the highest point in the GPX '
                               'file, not a surveyed summit height. <a href="../../about/#abo-how-h">How these reports are '
                               'made</a></p>')
        empty = '<section class="wrap rep-strip" id="stats" aria-label="Stats"><dl class="strip" style="--cells:1" aria-label="Trip stats"></dl>%s</section>'
        for slug in ('syn-one', 'syn-portrait', 'syn-words', 'syn-tall-only', 'syn-track', 'syn-undated', 'syn-two-tall'):
            with self.subTest(slug):
                t = self.by[slug]
                self.assertTrue(t['track'])
                self.assertEqual(core.strip_cells(t), [])
                self.assertEqual(STRIP_SECTION.findall(self.page(slug).html), [empty % note])
                self.assertEqual(self.page(slug).html.count(note), 1)
        self.assertEqual(self.toc('syn-one'), [REPORT_ROW, ROUTE])
        self.assertEqual(bar_items(self.bbar('syn-one')), [STATS, REPORT, MAP, ('GPX', 'syn-one.gpx')])   # page order
        self.assertEqual(bar_items(self.bbar('syn-track')), [STATS, MAP, ('GPX', 'syn-track.gpx')])
        # the one change 10.3 makes to a tracked report: the sentence about a derived value is written only when the
        # strip shows that value, so a mountain bike or flat-water report without a distance and a moving time no
        # longer explains an average speed or a pace it does not state
        self.assertEqual(self.by['syn-photos']['activity'], 'mtb')
        self.assertEqual(STRIP_SECTION.findall(self.page('syn-photos').html), [empty % note])
        ride = self.add('syn-ride-stats', activity='mtb', date='2025-09-01', stats={'distance_km': 20.0, 'moving': '2:00'})
        self.assertEqual(self.doc('syn-ride-stats').by_id('stats').find('p', cls='strip-note').text(), ' '.join([RECORDING, AVG_SPEED, GPS_MAX, MOVING, HOW_TEXT]))
        self.assertEqual([dt.text() for dt in self.doc('syn-ride-stats').by_id('stats').find_all('dt')], ['Distance', 'Moving', 'Avg speed'])
        self.assertTrue(ride['track'])
        half = self.add('syn-ride-half', activity='mtb', date='2025-09-02', stats={'distance_km': 20.0})
        self.assertEqual(self.doc('syn-ride-half').by_id('stats').find('p', cls='strip-note').text(), ' '.join([RECORDING, GPS_MAX, HOW_TEXT]))
        self.assertTrue(half['track'])
        paddle = self.add('syn-paddle-bare', activity='other', subtype='SUP', date='2025-09-03')
        self.assertTrue(paddle['track'])
        self.assertEqual(STRIP_SECTION.findall(self.page('syn-paddle-bare').html), [empty % strip_note([RECORDING])])
        self.add('syn-paddle-stats', activity='other', subtype='SUP', date='2025-09-04', stats={'distance_km': 5.0, 'moving': '1:00'})
        self.assertEqual(self.doc('syn-paddle-stats').by_id('stats').find('p', cls='strip-note').text(), ' '.join([RECORDING, PACE, MOVING, HOW_TEXT]))

    def rendered_files(self, slug):
        """What the render folder of the temp dir holds for a trip, on disk."""
        folder = os.path.join(self.tmp, '_rendered', slug)
        return sorted(os.listdir(folder)) if os.path.isdir(folder) else []

    def test_a_stale_render_folder_shows_nothing(self):
        # 10.3: renders belong to a track. A report whose track.gpx was removed while its rendered folder (maps, a
        # chart, the route drawings) is still there is, byte for byte, the page of a report that was never rendered:
        # no map, no chart section, no key, no map preload, no drawing in the phone app bar. With the track back the
        # page is again what it was
        charts = {}

        def reload():
            """Load the site again and give every report rendered so far its folder back (a reload forgets them)."""
            self.load_site()
            for done, kind in charts.items():
                self.render(done, chart=kind, drawn=True)

        for slug, chart in (('syn-story', 'profile'), ('syn-one', 'profile'), ('syn-words', 'profile'), ('syn-photos', 'speed'),
                            ('syn-track', 'profile')):
            with self.subTest(slug):
                track = os.path.join(self.tmp, slug, 'track.gpx')
                self.render(slug, chart=chart, drawn=True)
                with_, doc = self.page(slug).html, self.doc(slug)
                hero = self.hero(slug) is not None
                # with its track everything rendered is on the page ...
                self.assertIsNotNone(doc.by_id('map'))
                self.assertIsNotNone(doc.by_id('profile'))
                self.assertEqual(doc.by_id('profile').find('h2').text(), 'Speed' if chart == 'speed' else 'Elevation')
                self.assertTrue(doc.find_all(cls='keyrow'))
                self.assertEqual(len([i for i in doc.find_all('img') if '/%s/map/' % slug in (i['src'] or '')]), 6)
                self.assertEqual(len([ln for ln in self.preloads(slug) if '/map/' in ln['href']]), 0 if hero else 6)
                self.assertEqual(drawings(doc, slug), [(slug, 'g64')])
                self.assertEqual(drawings(doc.find('a', cls='ab-trip'), slug), [(slug, 'g64')])        # the phone app bar
                # ... the report without its track and without a render folder ...
                os.remove(track)
                reload()
                self.assertEqual(self.rendered_files(slug)[:3], ['g112.svg.html', 'g64.svg.html', 'map-col.base.svg'])
                t = self.by[slug]
                self.assertFalse(os.path.exists(t['rendered']))        # after a reload the trip points at no folder
                bare = self.page(slug).html
                # ... is the report without its track whose folder is still there
                self.render(slug, chart=chart, drawn=True)
                t = self.by[slug]
                with open(os.path.join(t['rendered'], 'meta.json'), encoding='utf-8') as fh:
                    on_disk = json.load(fh)
                self.assertEqual((sorted(on_disk['maps']), len(on_disk['charts'])), (['map-col', 'map-phone', 'map-wide'], 3))
                self.assertEqual(core.render_meta(t), {'maps': {}, 'charts': {}})
                self.assertEqual(need(self, self.report, 'has_chart')(core.render_meta(t)), '')
                self.assertEqual(self.page(slug).html, bare)
                self.assertNoRoute(slug)
                self.assertEqual(len(self.preloads(slug)), 1 if hero else 0)
                self.assertEqual([ln['href'] for ln in self.preloads(slug) if '/map/' in ln['href']], [])
                self.assertNotIn('class="map', bare)
                self.assertNotIn('mv-hs', bare)
                self.assertNotIn('.svg"', bare.split('<main', 1)[0].split('</head>', 1)[1])            # the app bar's glyph
                # with the track back, all of it again
                helpers.touch(track)
                charts[slug] = chart
                reload()
                self.assertEqual(self.page(slug).html, with_)
                self.assertEqual(drawings(self.doc(slug), slug), [(slug, 'g64')])

    def test_a_stale_render_folder_draws_the_route_on_no_page(self):
        # 10.3: ... nor is its route drawn where other pages list the report: a card (the tile, for a report without a
        # photo), a section row, a table row, a phone row, a pager cell, the section page
        section = load_module(self, 'sitegen.pages.section')
        slug = 'syn-track'                                  # no photo: its cards and rows show the route tile
        track = os.path.join(self.tmp, slug, 'track.gpx')

        def seen():
            """{where: the drawings of syn-track there} for every place that lists it."""
            t = self.by[slug]
            newer, older = need(self, self.report, 'neighbours')(t, self.site)
            self.assertEqual((newer['slug'], older['slug']), ('syn-tall-only', 'syn-journal'))      # the hikes on either side
            out = {'own page': drawings(self.doc(slug), slug),
                   'pager, newer': drawings(Doc(self.report.pager(newer, newer['url'], self.site)), slug),
                   'pager, older': drawings(Doc(self.report.pager(older, older['url'], self.site)), slug),
                   'newer page': drawings(Doc(self.report.page(newer, self.site).html), slug),
                   'card': drawings(Doc(core.trip_card(t, 'trips/', core.RELATED_SIZES)), slug),
                   'row': drawings(Doc(core.trip_row(t, 'hiking/')), slug),
                   'table row': drawings(Doc('<table>%s</table>' % core.table_row(t, 'map/')), slug),
                   'section page': drawings(Doc(section.page('hike', self.site).html), slug)}
            related = [x['slug'] for x in self.site['published']
                       if x is not t and slug in [c['slug'] for c in core.related(x, self.site, skip=self.report.neighbours(x, self.site))]]
            self.assertTrue(related, 'no report lists syn-track under More like this')
            out['related card'] = drawings(Doc(core.related_block(self.by[related[0]], self.by[related[0]]['url'], self.site,
                                                                  skip=self.report.neighbours(self.by[related[0]], self.site))), slug)
            return out

        self.render(slug, chart='profile', drawn=True)
        want = {'own page': [(slug, 'g64')], 'pager, newer': [(slug, 'g112')], 'pager, older': [(slug, 'g112')],
                'newer page': [(slug, 'g112')], 'card': [(slug, 'tile')], 'row': [(slug, 'tile')], 'table row': [(slug, 'g112')],
                'section page': [(slug, 'tile')], 'related card': [(slug, 'tile')]}
        self.assertEqual(seen(), want)
        os.remove(track)
        self.load_site()
        self.render(slug, chart='profile', drawn=True)
        t = self.by[slug]
        self.assertEqual(self.rendered_files(slug)[:2], ['g112.svg.html', 'g64.svg.html'])
        self.assertEqual(seen(), {k: [] for k in want})
        for name, size in (('tile', None), ('g112', 'g112'), ('g64', 'g64')):
            self.assertTrue(os.path.isfile(os.path.join(t['rendered'], name + '.svg.html')))
            self.assertEqual(core.tile(t, 'trips/') if size is None else core.glyph(t, 'trips/', size), '')
        # the card falls back to what a report that was never rendered shows: the activity disc
        card = Doc(core.trip_card(t, 'trips/', core.RELATED_SIZES))
        self.assertEqual(card.find_all('img'), [])
        self.assertIsNotNone(card.find('div', cls='tcard-img--none'))
        # ... while the other reports' drawings are untouched: syn-undated has its own folder and its track
        self.render('syn-undated', drawn=True)
        self.assertEqual(drawings(Doc(core.trip_row(self.by['syn-undated'], 'hiking/'))), [('syn-undated', 'tile')])
        helpers.touch(track)
        self.load_site()
        self.render(slug, chart='profile', drawn=True)
        self.assertEqual(seen(), want)

    def test_the_build_publishes_no_render_of_a_trip_without_a_track(self):
        # 10.3: build.copy_trip_assets writes tile.svg / g112.svg / g64.svg and the map/ renders only for a trip that
        # has a track (its own, or a day's); the photos are copied either way
        build = load_module(self, 'build')
        out = os.path.join(self.tmp, '_out')

        def published(slug, name):
            """The files a build writes for the trip, relative to its folder, sorted."""
            with mock.patch.object(build, 'OUT', os.path.join(out, name)), mock.patch.object(build, 'LINK', False):
                build.copy_trip_assets(self.by[slug])
            folder = os.path.join(out, name, 'trips', slug)
            return sorted(os.path.relpath(os.path.join(d, f), folder).replace(os.sep, '/') for d, _dirs, files in os.walk(folder) for f in files)

        slug = 'syn-photos'
        photos = ['photos/01.webp', 'photos/02.webp', 'photos/03.webp']
        renders = ['g112.svg', 'g64.svg'] + ['map/map-%s.%s' % (n, e) for n in ('col', 'phone', 'wide') for e in ('base.svg', 'webp')]
        self.render(slug, chart='speed', drawn=True)
        self.assertEqual(published(slug, 'with'), sorted(renders + photos + [slug + '.gpx', 'tile.svg']))
        os.remove(os.path.join(self.tmp, slug, 'track.gpx'))
        self.load_site()
        self.render(slug, chart='speed', drawn=True)
        self.assertEqual(self.rendered_files(slug)[:2], ['g112.svg.html', 'g64.svg.html'])     # the folder is all there
        self.assertEqual(published(slug, 'without'), photos)
        self.assertFalse(os.path.exists(os.path.join(out, 'without', 'trips', slug, 'map')))
        helpers.touch(os.path.join(self.tmp, slug, 'track.gpx'))
        self.load_site()
        self.render(slug, chart='speed', drawn=True)
        self.assertEqual(published(slug, 'back'), sorted(renders + photos + [slug + '.gpx', 'tile.svg']))
        # a multi-day trip: no day track, no drawings and no map renders; one day track is enough for all of them
        days = [{'title': 'Synthetic Day One', 'date': '2025-02-01', 'track': False}, {'title': 'Synthetic Day Two', 'date': '2025-02-02', 'track': False}]
        self.add('syn-trek-stale', kind='multi-day', activity='ski', date='2025-02-01', end_date='2025-02-02', days=days,
                 photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one')])
        self.render('syn-trek-stale', drawn=True)
        self.assertIs(core.has_track(self.by['syn-trek-stale']), False)
        self.assertEqual(core.render_meta(self.by['syn-trek-stale']), {'maps': {}, 'charts': {}})
        self.assertEqual(published('syn-trek-stale', 'tour-without'), ['photos/01.webp'])
        helpers.touch(os.path.join(self.tmp, 'syn-trek-stale', 'days', '02.gpx'))
        self.load_site()
        self.render('syn-trek-stale', drawn=True)
        self.assertIs(core.has_track(self.by['syn-trek-stale']), True)
        self.assertEqual(sorted(core.render_meta(self.by['syn-trek-stale'])['maps']), ['map-col', 'map-phone', 'map-wide'])
        self.assertEqual(published('syn-trek-stale', 'tour-with'),
                         sorted(renders + ['photos/01.webp', 'tile.svg', 'gpx/syn-trek-stale-day-02.gpx', 'syn-trek-stale.gpx']))

    def test_bottom_bar_without_a_gpx_href(self):
        # 10: report.bottom_bar(..., gpx_href='') has no GPX item and --n counts only what is shown, for every
        # combination of beta, report, gallery, chart and layout; with an href the item is the last one, as before
        t = self.by['syn-story']
        for has_beta, has_report, has_gallery in itertools.product((True, False), repeat=3):
            for chart in ('', 'profile', 'speed'):
                for story in (False, True):
                    with self.subTest(beta=has_beta, report=has_report, gallery=has_gallery, chart=chart, story=story):
                        with_ = self.report.bottom_bar(t, t['url'], 'syn-story.gpx', has_beta, has_report, has_gallery, chart, story=story)
                        without = self.report.bottom_bar(t, t['url'], '', has_beta, has_report, has_gallery, chart, story=story)
                        self.assertEqual(without, without_gpx(with_, 'syn-story'))
                        nav = Doc(without).find('nav')
                        links = nav.find_all('a')
                        self.assertEqual(nav['style'], '--n:%d' % len(links))
                        self.assertGreaterEqual(len(links), 2)
                        self.assertEqual([a for a in links if 'download' in a], [])
                        self.assertEqual(Doc(with_).find('nav')['style'], '--n:%d' % (len(links) + 1))
                        self.assertEqual(bar_items(Doc(with_).find('nav')), bar_items(nav) + [('GPX', 'syn-story.gpx')])

    def test_bottom_bar_without_a_map(self):
        # 10.2: report.bottom_bar(..., story=False, has_map=True): has_map=False leaves the Map item out, whatever the
        # layout; the bar is '' when fewer than two items would be left; has_map defaults to True, where nothing changed.
        # 10.3: ... has_stats=True: has_stats=False leaves the Stats item out (the item that stands in for a chart)
        t = self.by['syn-story']
        bottom_bar = need(self, self.report, 'bottom_bar')
        gpx = ('GPX', 'syn-story.gpx')
        empty = []
        for has_beta, has_report, has_gallery in itertools.product((True, False), repeat=3):
            for chart, story in itertools.product(('', 'profile', 'speed'), (False, True)):
                args = (has_beta, has_report, has_gallery, chart)
                full = bottom_bar(t, t['url'], 'syn-story.gpx', *args, story=story)
                for gpx_href, has_map, has_stats in itertools.product(('syn-story.gpx', ''), (True, False), (True, False)):
                    with self.subTest(beta=has_beta, report=has_report, gallery=has_gallery, chart=chart, story=story, gpx=gpx_href,
                                      has_map=has_map, has_stats=has_stats):
                        got = bottom_bar(t, t['url'], gpx_href, *args, story=story, has_map=has_map, has_stats=has_stats)
                        self.assertEqual(got, expected_bar(t, gpx_href, *args, story=story, has_map=has_map, has_stats=has_stats))
                        left = [x for x in bar_items(Doc(full).find('nav'))
                                if (has_map or x != MAP) and (gpx_href or x != gpx) and (has_stats or x != STATS)]
                        if len(left) < 2:
                            self.assertEqual(got, '')
                            empty.append((args, story, gpx_href, has_map, has_stats))
                            continue
                        nav = Doc(got).find('nav')
                        self.assertEqual(bar_items(nav), left)
                        self.assertEqual(nav['style'], '--n:%d' % len(left))
                        self.assertEqual((nav.classes, nav['aria-label']), (['bbar'], 'Report sections'))
                        self.assertEqual(MAP in left, has_map)
                        self.assertEqual(gpx in left, bool(gpx_href))
                        if not has_stats:
                            self.assertNotIn('#stats', got)
                        if has_map and has_stats:
                            self.assertEqual(got, bottom_bar(t, t['url'], gpx_href, *args, story=story))      # the defaults
                            self.assertEqual(got, bottom_bar(t, t['url'], gpx_href, has_beta, has_report, has_gallery, chart, story, True, True))
                        if has_stats:
                            self.assertEqual(got, bottom_bar(t, t['url'], gpx_href, *args, story=story, has_map=has_map))
        # no bar: never with a file and a map (those two are a bar by themselves). With a strip (has_stats), only without
        # a map and a file on a compact page with neither a write-up nor a gallery, whose one item would be Beta, the
        # chart or Stats; a story always keeps Report and one more
        self.assertTrue(empty)
        for (has_beta, has_report, has_gallery, chart), story, gpx_href, has_map, has_stats in empty:
            self.assertFalse(gpx_href and has_map)
            if has_stats:
                self.assertEqual((has_report, has_gallery, story, gpx_href, has_map), (False, False, False, '', False))
        self.assertEqual(len([e for e in empty if e[4]]), 6)
        # without a strip, and without a map and a file: a story of Report alone, a compact page of Report or Photos alone
        # or of nothing at all, are no bar; a chart still counts as an item
        bare = [(e[0], e[1]) for e in empty if not e[4] and not e[3] and not e[2]]
        self.assertIn(((False, True, False, ''), True), bare)             # story: Report alone
        self.assertIn(((False, True, False, ''), False), bare)            # compact: Report alone
        self.assertIn(((False, False, True, ''), False), bare)            # compact: Photos alone
        self.assertIn(((False, False, False, ''), False), bare)           # compact: nothing
        self.assertNotIn(((False, True, False, 'profile'), True), bare)   # story: Report and Profile
        self.assertNotIn(((True, True, False, ''), False), bare)          # compact: Beta and Report
        nav = Doc(bottom_bar(t, t['url'], '', False, True, False, 'profile', story=True, has_map=False, has_stats=False)).find('nav')
        self.assertEqual((bar_items(nav), nav['style']), ([REPORT, PROFILE], '--n:2'))
        self.assertEqual(bottom_bar(t, t['url'], '', False, True, False, '', story=True, has_map=False, has_stats=False), '')
        self.assertEqual(bottom_bar(t, t['url'], '', False, True, False, '', has_map=False, has_stats=False), '')
        # one item and a file is two items: the bar stays
        nav = Doc(bottom_bar(t, t['url'], 'syn-story.gpx', False, False, False, '', has_map=False)).find('nav')
        self.assertEqual((bar_items(nav), nav['style']), ([STATS, gpx], '--n:2'))
        # and exactly two items without either is still a bar
        nav = Doc(bottom_bar(t, t['url'], '', False, True, False, '', has_map=False)).find('nav')
        self.assertEqual((bar_items(nav), nav['style']), ([STATS, REPORT], '--n:2'))

    def test_section_nav_without_a_map(self):
        # 10.2: report.section_nav(has_report, has_gallery, has_map=True, chart=''): has_map=False drops the Map item and
        # nothing else; the default is the row with a map
        section_nav = need(self, self.report, 'section_nav')
        for has_report, has_gallery, chart in itertools.product((True, False), (True, False), ('', 'profile')):
            with self.subTest(report=has_report, gallery=has_gallery, chart=chart):
                with_ = section_nav(has_report, has_gallery, True, chart)
                self.assertEqual(section_nav(has_report, has_gallery, chart=chart), with_)
                self.assertEqual(with_.count(MAP_ROW_ITEM), 1)
                without = section_nav(has_report, has_gallery, False, chart)
                self.assertEqual(without, with_.replace(MAP_ROW_ITEM, ''))
                items = [(a.text(), a['href']) for a in Doc(without).find_all('a')]
                want = ([REPORT_ROW] if has_report else []) + ([PROFILE] if chart else []) + ([PHOTOS_ROW] if has_gallery else [])
                self.assertEqual(items, want)
                self.assertNotIn('#map', without)

    def test_build_makes_a_map_page_exactly_for_the_reports_with_a_track(self):
        # 10.2 as amended by Phase 6 (resilience-12): report.build builds trips/<slug>/map/ for a single-day report with
        # a track and a rendered map, as for a goal, and for no report without one, whatever a stale render folder
        # holds: a full-screen page round a map that is not drawn would be empty. (tests/test_metadata.py pins the goal
        # on its built site; the fixture goal here has a track and no render)
        mk = helpers.make_trip
        mk(self.tmp, 'syn-nt-words', title='Synthetic Trackless Words', date='2025-06-17', region=REGION, body=WRITEUP)
        mk(self.tmp, 'syn-nt-bare', title='Synthetic Trackless Bare', date='2025-06-16', region=REGION)
        mk(self.tmp, 'syn-nt-stale', title='Synthetic Trackless Stale', date='2025-06-15', region=REGION)
        self.load_site()
        self.render('syn-story')
        self.render('syn-words', chart='profile')
        self.render('syn-nt-stale', chart='profile')
        no_track = ['syn-nt-words', 'syn-nt-bare', 'syn-nt-stale']
        self.assertEqual([self.by[s]['track'] for s in no_track], [None] * 3)
        with open(os.path.join(self.by['syn-nt-stale']['rendered'], 'meta.json'), encoding='utf-8') as fh:
            self.assertEqual(sorted(json.load(fh)['maps']), ['map-col', 'map-phone', 'map-wide'])     # the folder is there ...
        self.assertEqual(core.render_meta(self.by['syn-nt-stale']), {'maps': {}, 'charts': {}})          # ... and is not read (10.3)
        pages = need(self, self.report, 'build')(self.site)
        urls = [p.url for p in pages]
        self.assertEqual(len(urls), len(set(urls)))
        want = []
        for t in self.site['trips']:                          # in site order: each report, then its map page
            if t['slug'] in SINGLE:
                want += [t['url']] + ([t['url'] + 'map/'] if t['slug'] in ('syn-story', 'syn-words') else [])
            elif t['slug'] in no_track:
                want.append(t['url'])
        self.assertEqual([u for u in urls if not u.startswith('trips/syn-goal/')], want)
        self.assertEqual(len(want), len(SINGLE) + 2 + 3)
        for slug in SINGLE:
            if slug not in ('syn-story', 'syn-words'):
                self.assertNotIn('trips/%s/map/' % slug, urls)          # a track, but no map drawn: no full-screen page
        for slug in no_track:
            self.assertIn('trips/%s/' % slug, urls)
            self.assertNotIn('trips/%s/map/' % slug, urls)
        by_url = {p.url: p for p in pages}
        for slug in ('syn-story', 'syn-words'):
            with self.subTest(slug):
                self.assertTrue(self.by[slug]['track'])
                helper = by_url['trips/%s/map/' % slug]
                self.assertIs(helper.index, False)
                self.assertIn('<meta name="robots" content="noindex">', helper.html)
                self.assertEqual(helper.html, self.report.fullscreen_page(self.by[slug]).html)
                # its way back lands on the section the report page has
                back = Doc(helper.html).find('a', attrs={'href': '../#map'})
                self.assertIsNotNone(back)
                self.assertEqual(back.text(), 'Back to report')
                self.assertIsNotNone(Doc(by_url['trips/%s/' % slug].html).by_id('map'))
                self.assertEqual(by_url['trips/%s/' % slug].html, self.report.page(self.by[slug], self.site).html)
        # the multi-day trip and the journal are other modules' pages
        self.assertEqual([u for u in urls if 'syn-tour' in u or 'syn-journal' in u], [])

    # ------------------------------------------------------------ section pages: the featured block

    def featured_page(self, section):
        return section.page('hike', self.site).html

    def test_a_section_pages_featured_block_offers_the_gpx_only_with_a_track(self):
        # 10.2: a report without a track is never a section's featured report; section.featured keeps its own guard (no
        # 'Download GPX' button without a track) for a direct call
        section = load_module(self, 'sitegen.pages.section')
        self.add('syn-featured', featured=True, date='2026-02-10', body=WRITEUP, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one')])
        self.render('syn-featured')
        button = ('<a class="btn btn--ink sec-feat-gpx" href="../trips/syn-featured/syn-featured.gpx" download>%sDownload GPX</a>'
                  % core.icon('download', 18))
        with_ = self.featured_page(section)
        feat = Doc(with_).by_id('main').by_id('featured')
        self.assertEqual(feat.find('h2').text(), 'Synthetic Featured')      # the block is this report's
        self.assertEqual([(a.text(), a['href'], a.classes, 'download' in a) for a in feat.find_all('a', cls='sec-feat-gpx')],
                         [('Download GPX', '../trips/syn-featured/syn-featured.gpx', ['btn', 'btn--ink', 'sec-feat-gpx'], True)])
        self.assertEqual(gpx_links(Doc(with_).root), [('Download GPX', '../trips/syn-featured/syn-featured.gpx')])
        self.assertEqual(with_.count(button), 1)
        block_with = need(self, section, 'featured')(self.by['syn-featured'], 'hiking/')
        self.assertIn(button, block_with)
        self.assertIn(block_with, with_)
        self.assertIn('mv--col', block_with)                                 # its rendered map is in the block
        # the same block before the report was rendered: the empty map (what 10.3 makes of a folder without a track)
        unrendered = section.featured(dict(self.by['syn-featured'], rendered=os.path.join(self.tmp, '_rendered', 'never')), 'hiking/')
        self.assertIn(button, unrendered)
        self.assertIn('<div class="map map--nowide sec-feat-mapv"></div>', unrendered)
        os.remove(os.path.join(self.tmp, 'syn-featured', 'track.gpx'))
        self.load_site()
        self.render('syn-featured')
        self.assertIsNone(self.by['syn-featured']['track'])
        self.assertIs(self.by['syn-featured']['featured'], True)             # still flagged, and no longer the one
        without = self.featured_page(section)
        doc = Doc(without)
        feat = doc.by_id('main').by_id('featured')
        self.assertEqual(feat.find('h2').text(), 'Synthetic Story')          # the newest hike that has a track
        self.assertEqual(feat.find('h2').find('a')['href'], '../trips/syn-story/')
        self.assertEqual(gpx_links(doc.root), [('Download GPX', '../trips/syn-story/syn-story.gpx')])
        self.assertNotIn('syn-featured.gpx', without)
        self.assertNotIn('trips/syn-featured/map/', without)
        self.assertNotIn('../trips/syn-featured/', [a['href'] for a in feat.find_all('a')])
        # the report is a row of the list now, where the newest hike with a track was, and that one is not listed twice
        rows = [a['href'] for a in doc.by_id('main').by_id('reports').find_all('a') if a not in feat.find_all('a')]
        self.assertIn('../trips/syn-featured/', rows)
        self.assertNotIn('../trips/syn-story/', rows)
        self.assertIn('../trips/syn-story/', [a['href'] for a in Doc(with_).by_id('main').by_id('reports').find_all('a')])
        # a direct call: the block of a report without a track has no button and names no file. 10.3: the folder its
        # track left behind is not drawn either, so the rest of it is the block of the unrendered report with its
        # track, minus the sentences of the stats note that speak of the recording
        block = section.featured(self.by['syn-featured'], 'hiking/')
        self.assertTrue(os.path.isfile(os.path.join(self.by['syn-featured']['rendered'], 'map-col.svg.html')))
        self.assertNotIn('sec-feat-gpx', block)
        self.assertNotIn('.gpx', block)
        self.assertNotIn('Download GPX', block)
        self.assertEqual([n for n in Doc(block).root.walk() if 'download' in n], [])
        self.assertNotIn('mv--col', block)
        self.assertEqual(Doc(block).find_all('img', cls='mv-hs'), [])
        recorded = strip_note([RECORDING, GPS_MAX], how=SECTION_HOW)
        self.assertEqual(unrendered.count(recorded), 1)
        self.assertEqual(block, unrendered.replace(button, '').replace(recorded, ''))
        self.assertNotEqual(block, block_with.replace(button, '').replace(recorded, ''))
        # the place line's region links to the region since Phase 12 (ia-09)
        self.assertEqual([a['href'] for a in Doc(block).find_all('a')],
                         ['../trips/syn-featured/', '../map/#region-synthetic-range', 'https://example.test/', '../trips/syn-featured/'])

    def test_pick_featured_takes_only_reports_with_a_track(self):
        # 10.2: section.pick_featured(ts): only single-day reports with a track are candidates: the first one marked
        # featured: true, else the newest; None when there is none
        section = load_module(self, 'sitegen.pages.section')
        pick = need(self, section, 'pick_featured')
        hikes = lambda: need(self, section, 'reports_of')(self.site, 'hike')   # noqa: E731
        self.assertEqual(pick(hikes())['slug'], 'syn-story')                  # nothing flagged: the newest (with a track)
        mk = helpers.make_trip
        mk(self.tmp, 'syn-pf-new', title='Synthetic Newest', date='2026-12-01', region=REGION, featured=True, body=WRITEUP)   # no track
        mk(self.tmp, 'syn-pf-next', title='Synthetic Next', date='2026-11-01', region=REGION)                               # no track
        self.load_site()
        ts = hikes()
        self.assertEqual([t['slug'] for t in ts[:3]], ['syn-pf-new', 'syn-pf-next', 'syn-story'])
        self.assertEqual([(bool(t['track']), t['featured']) for t in ts[:3]], [(False, True), (False, False), (True, False)])
        self.assertEqual(pick(ts)['slug'], 'syn-story')         # skips the flagged report and the newer one: neither has a track
        self.assertIs(pick(ts), self.by['syn-story'])
        mk(self.tmp, 'syn-pf-flag', title='Synthetic Flagged', date='2024-01-01', region=REGION, featured=True, track=True)
        mk(self.tmp, 'syn-pf-flag-old', title='Synthetic Flagged Earlier', date='2023-01-01', region=REGION, featured=True, track=True)
        self.load_site()
        ts = hikes()
        self.assertEqual(pick(ts)['slug'], 'syn-pf-flag')       # featured: true wins among the reports with a track, the newest such
        self.assertEqual(pick([t for t in ts if t['slug'] != 'syn-pf-flag'])['slug'], 'syn-pf-flag-old')
        self.assertEqual(pick([t for t in ts if not t['slug'].startswith('syn-pf-flag')])['slug'], 'syn-story')
        # None: nothing, only reports without a track (flagged or not), only trips of other kinds
        no_track = [t for t in ts if t['kind'] == 'trip' and not t['track']]
        self.assertEqual(sorted(t['slug'] for t in no_track), ['syn-pf-new', 'syn-pf-next'])
        self.assertIsNone(pick([]))
        self.assertIsNone(pick(no_track))
        self.assertIsNone(pick([self.by['syn-pf-new']]))
        tour, journal = self.by['syn-tour'], self.by['syn-journal']
        self.assertTrue(core.has_track(tour) and core.has_track(journal))
        self.assertIsNone(pick([tour, journal]))                # a multi-day trip or a journal is never the featured report
        self.assertEqual(pick([tour, self.by['syn-pf-new'], journal, self.by['syn-track']])['slug'], 'syn-track')
        # ... not even one that carries a track.gpx of its own beside its day files, flagged or not; nor is a planned route
        mk(self.tmp, 'syn-pf-tour', title='Synthetic Tour With Its Own Track', kind='multi-day', date='2026-10-01', end_date='2026-10-02',
           region=REGION, featured=True, track=True, days=[{'title': 'Synthetic Day One', 'date': '2026-10-01'},
                                                           {'title': 'Synthetic Day Two', 'date': '2026-10-02'}])
        self.load_site()
        own = self.by['syn-pf-tour']
        self.assertTrue(own['track'] and own['featured'] and own['kind'] == 'multi-day')
        self.assertIsNone(pick([own]))
        self.assertIsNone(pick([own, self.by['syn-goal']]))
        self.assertTrue(self.by['syn-goal']['track'])
        self.assertEqual(pick(hikes())['slug'], 'syn-pf-flag')
        self.assertEqual(pick([own, self.by['syn-track']])['slug'], 'syn-track')
        # every pick has a track, whatever the list
        for k in range(len(ts)):
            got = pick(ts[k:])
            self.assertTrue(got is None or got['track'])

    def test_a_section_whose_newest_report_has_no_track_features_the_newest_that_has_one(self):
        # 10.2 on the built page: climbing's newest report has no track, so the block is the next one's, complete with its
        # map section link and its download; the trackless report is a row of the list
        section = load_module(self, 'sitegen.pages.section')
        mk = helpers.make_trip
        mk(self.tmp, 'syn-crag-new', title='Synthetic Newest Crag', activity='climb', date='2026-09-01', region=REGION, body=WRITEUP)
        mk(self.tmp, 'syn-crag-old', title='Synthetic Older Crag', activity='climb', date='2026-01-05', region=REGION, track=True)
        self.load_site()
        climbs = need(self, section, 'reports_of')(self.site, 'climb')
        self.assertEqual([(t['slug'], bool(t['track'])) for t in climbs],
                         [('syn-crag-new', False), ('syn-two-tall', True), ('syn-crag-old', True)])
        html_ = section.page('climb', self.site).html
        doc = Doc(html_)
        feat = doc.by_id('main').by_id('featured')
        self.assertEqual(feat.find('h2').text(), 'Synthetic Two Portraits')
        self.assertEqual(gpx_links(doc.root), [('Download GPX', '../trips/syn-two-tall/syn-two-tall.gpx')])
        rows = [a['href'] for a in doc.by_id('main').by_id('reports').find_all('a') if a not in feat.find_all('a')]
        self.assertEqual([h for h in rows if h.startswith('../trips/')], ['../trips/syn-crag-new/', '../trips/syn-crag-old/'])
        self.assertNotIn('syn-crag-new.gpx', html_)
        self.assertNotIn('trips/syn-crag-new/map/', html_)
        self.assertIn(section.featured(self.by['syn-two-tall'], 'climbing/'), html_)

    def test_a_section_of_reports_without_a_track_has_no_featured_block(self):
        # 10.2: a section whose single-day reports all lack a track has no featured block: every report is a row, no
        # link names a file or a map page, and every link the page keeps to itself has its target
        section = load_module(self, 'sitegen.pages.section')
        for slug in ('syn-photos', 'syn-two-tall'):          # the one mountain bike report and the one climbing report
            os.remove(os.path.join(self.tmp, slug, 'track.gpx'))
        helpers.make_trip(self.tmp, 'syn-ride-two', title='Synthetic Second Ride', activity='mtb', date='2025-10-01', region=REGION)
        self.load_site()
        for act, here, slugs in (('mtb', 'mountain-biking/', ['syn-photos', 'syn-ride-two']), ('climb', 'climbing/', ['syn-two-tall'])):
            with self.subTest(act):
                ts = need(self, section, 'reports_of')(self.site, act)
                self.assertEqual([(t['slug'], t['track']) for t in ts], [(s, None) for s in slugs])
                self.assertIsNone(need(self, section, 'pick_featured')(ts))
                page = section.page(act, self.site)
                doc = Doc(page.html)
                self.assertEqual(page.url, here)
                self.assertIsNone(doc.by_id('featured'))
                self.assertNotIn('sec-feat', page.html)
                self.assertNotIn('Featured', doc.by_id('main').text())
                self.assertEqual(gpx_links(doc.root), [])
                self.assertNotIn('.gpx', page.html.lower())
                self.assertNotIn('Download GPX', page.html)
                hrefs = [a['href'] or '' for a in doc.by_id('main').find_all('a')]
                self.assertEqual([h for h in hrefs if h.startswith('../trips/')], ['../trips/%s/' % s for s in slugs])
                self.assertEqual([h for h in hrefs if '/map/' in h and not h.startswith('../map/')], [])
                ids = {n['id'] for n in doc.root.walk() if n['id']}
                for h in [a['href'] or '' for a in doc.find_all('a')]:
                    if h.startswith('#'):
                        self.assertIn(h[1:], ids, '%s links %s, which is not an id on the page' % (here, h))
                self.assertEqual(doc.find('head').find_all('link', attrs={'rel': 'preload', 'as': 'image'}), [])
        # the hiking page, whose reports have tracks, still has its block
        self.assertIsNotNone(Doc(section.page('hike', self.site).html).by_id('featured'))

    def test_the_other_pages_type_segments_link_the_featured_block_only_when_there_is_one(self):
        # 10.3: on other/, the segment of a sub-type that has reports is a link into the page for readers without
        # JavaScript: to #featured when the page has a featured block, else to #reports (it was #featured either way,
        # a dead link on a page whose reports all lack a track). A sub-type without reports is a disabled link
        section = load_module(self, 'sitegen.pages.section')

        def segments():
            doc = Doc(section.page('other', self.site).html)
            nav = doc.find('nav', attrs={'data-filter-nav': 'reports'})
            self.assertIsNotNone(nav, 'other/ has no type filter')
            ids = {n['id'] for n in doc.root.walk() if n['id']}
            for a in doc.find_all('a'):
                if (a['href'] or '').startswith('#'):
                    self.assertIn(a['href'][1:], ids, 'other/ links %s, which is not an id on the page' % a['href'])
            return [(a.find('span').text(), a['href'], a['aria-disabled']) for a in nav.find_all('a')], doc.by_id('featured')

        mk = helpers.make_trip
        mk(self.tmp, 'syn-paddle', title='Synthetic Paddle', activity='other', subtype='SUP', date='2025-05-01', region=REGION, track=True)
        mk(self.tmp, 'syn-raft', title='Synthetic Raft', activity='other', subtype='Rafting', date='2025-04-01', region=REGION)
        self.load_site()
        segs, feat = segments()
        self.assertIsNotNone(feat)                       # the paddle has a track: it is the featured report
        self.assertEqual(feat.find('h2').text(), 'Synthetic Paddle')
        self.assertEqual(segs, [('All', '#reports', None), ('Paddleboarding', '#featured', None), ('Rafting', '#featured', None),
                                ('Kayaking', None, 'true'), ('Mountaineering', None, 'true')])
        # without the paddle's track nothing can be featured: both segments lead to the list
        os.remove(os.path.join(self.tmp, 'syn-paddle', 'track.gpx'))
        self.load_site()
        segs, feat = segments()
        self.assertIsNone(feat)
        self.assertEqual(segs, [('All', '#reports', None), ('Paddleboarding', '#reports', None), ('Rafting', '#reports', None),
                                ('Kayaking', None, 'true'), ('Mountaineering', None, 'true')])
        self.assertNotIn('#featured', section.page('other', self.site).html)
        # and with a track on the raft instead, the block is the raft's and the segments point at it again
        helpers.touch(os.path.join(self.tmp, 'syn-raft', 'track.gpx'))
        self.load_site()
        segs, feat = segments()
        self.assertEqual(feat.find('h2').text(), 'Synthetic Raft')
        self.assertEqual([href for _lab, href, _dis in segs], ['#reports', '#featured', '#featured', None, None])

    def test_the_build_copies_the_gpx_exactly_when_the_page_links_it(self):
        # 2.1: the download is offered when the file is published, and only then
        build = load_module(self, 'build')
        out = os.path.join(self.tmp, '_out')
        self.add('syn-notrack-bare', track=False, date='2025-06-18')
        with mock.patch.object(build, 'OUT', out), mock.patch.object(build, 'LINK', False):
            for slug in ('syn-track', 'syn-notrack-bare'):   # the render folder in the temp dir: the real rendered/ is not looked at
                build.copy_trip_assets(dict(self.by[slug], rendered=os.path.join(self.tmp, '_rendered', slug)))
        for slug, has in (('syn-track', True), ('syn-notrack-bare', False)):
            with self.subTest(slug):
                self.assertEqual(os.path.exists(os.path.join(out, 'trips', slug, slug + '.gpx')), has)
                self.assertEqual(sorted({href for _text, href in gpx_links(self.doc(slug).root)}), [slug + '.gpx'] if has else [])


# ---------------------------------------------------------------- Phase 4: what a phone is told (contract-phase4.md 5.2)

class PhoneSlotTests(ReportFixture):
    """contract-phase4.md 5.2: below 560 px a photo that fills the screen is declared as core.PHONE_SLOT (55vw), so a 3x
    phone takes the 800 px copy; the same string ends the hero's sizes, core.photo's default and the gallery rows'
    strings for a photo drawn at full width. A portrait drawn two to a row keeps 50vw. 10.3: the slot is for an
    ordinary landscape photo (core.PHONE_SHAPES); a portrait, a square, a panorama or an unsized photo shown at full
    width is told the real width, 100vw (core.phone_sizes: PhoneShapeTests). Fixture photos here have their .sm copy,
    because srcset and sizes are only written for a photo that has one."""

    def sized(self, html_):
        """{photo file name: sizes} of every <img> with a srcset in a fragment."""
        return {os.path.basename(i['src']): i['sizes'] for i in Doc(html_).find_all('img') if i['srcset']}

    def test_the_phone_slot_strings(self):
        self.assertEqual(need(self, core, 'PHONE_SLOT'), '55vw')
        self.assertEqual(need(self, core, 'PHONE_FULL'), '(min-width: 560px) 100vw, 55vw')
        self.assertEqual(core.PHONE_FULL, PHONE_FULL)
        self.assertEqual(core.PHONE_FULL, '(min-width: 560px) 100vw, ' + core.PHONE_SLOT)

    def test_hero_sizes_end_with_the_phone_slot(self):
        # 10: report.HERO_SIZES = '(min-width: 1200px) 1248px, ' + core.PHONE_FULL; no bare 100vw is left as the phone
        # fallback: every 100vw has a min-width before it and the last, unconditional entry is the slot
        sizes = need(self, self.report, 'HERO_SIZES')
        self.assertEqual(sizes, '(min-width: 1200px) 1248px, (min-width: 560px) 100vw, 55vw')
        self.assertTrue(sizes.endswith(', ' + core.PHONE_FULL))
        entries = sizes.split(', ')
        self.assertEqual(entries[-1], core.PHONE_SLOT)
        self.assertNotIn('100vw', entries)
        self.assertTrue(all(e.startswith('(min-width: ') for e in entries[:-1]), entries)

    def test_core_photo_tells_a_phone_the_slot_by_default(self):
        # 10: core.photo's default sizes end with core.PHONE_FULL in place of 100vw
        t = self.add('syn-sized', body=WRITEUP, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one', sm=True)])
        img = Doc(core.photo(t, t['photos'][0], t['url'])).find('img')
        self.assertEqual(img['sizes'], '(min-width: 1200px) 1248px, (min-width: 560px) 100vw, 55vw')
        self.assertEqual(img['srcset'], '../../trips/syn-sized/photos/01.sm.webp 800w, ../../trips/syn-sized/photos/01.webp 1600w')
        # a photo in the viewer or the gallery is never given the card-size copy
        helpers.touch(os.path.join(self.tmp, 'syn-sized', 'photos', '01.th.webp'))
        self.load_site()
        t = self.by['syn-sized']
        self.assertEqual(t['photos'][0]['th'], 'photos/01.th.webp')
        self.assertEqual(Doc(core.photo(t, t['photos'][0], t['url'])).find('img')['srcset'], img['srcset'])

    def test_gallery_rows_tell_a_phone_the_width_each_photo_fills(self):
        # 10: the three core.photo_rows strings end with core.PHONE_FULL for a photo a phone shows at full width (a
        # landscape, a portrait alone in its row, the odd portrait of a row); a portrait paired two-up keeps 50vw.
        # 10.3: of those, only the landscape keeps PHONE_FULL: a portrait at full width is told 100vw (its 800 px copy
        # is 600 px wide, too small for the 55vw slot's arithmetic)
        ph = lambda n, size: photo('photos/%02d.webp' % n, size, alt='Synthetic photo %d' % n, sm=True)   # noqa: E731
        t = self.add('syn-rows', photos=[ph(1, LANDSCAPE),                                  # a row of its own
                                         ph(2, PORTRAIT), ph(3, PORTRAIT), ph(4, PORTRAIT),   # a row of three: a pair and one
                                         ph(5, LANDSCAPE), ph(6, LANDSCAPE)])
        rows = core.photo_partition(t['photos'])
        self.assertEqual([[os.path.basename(p['file']) for p in r] for r in rows],
                         [['01.webp'], ['02.webp', '03.webp', '04.webp'], ['05.webp'], ['06.webp']])
        got = self.sized(core.photo_rows(t, t['url'], t['photos']))
        self.assertEqual(got['01.webp'], '(min-width: 1200px) 1248px, ' + PHONE_FULL)
        self.assertEqual(got['05.webp'], got['01.webp'])
        for name in ('02.webp', '03.webp'):                                    # two-up on a phone
            self.assertTrue(got[name].endswith(', 50vw'), got[name])
            self.assertNotIn('55vw', got[name])
            self.assertEqual(got[name], '(min-width: 1200px) 400px, (min-width: 760px) calc((100vw - 80px) * 0.333), 50vw')
        self.assertEqual(got['04.webp'], '(min-width: 1200px) 400px, (min-width: 760px) calc((100vw - 80px) * 0.333), 100vw')
        # a landscape that shares its row with a pair of portraits is still full width on a phone; the pair is not
        t = self.add('syn-rows-mixed', date='2025-06-16', photos=[ph(1, LANDSCAPE), ph(2, PORTRAIT), ph(3, PORTRAIT)])
        self.assertEqual(len(core.photo_partition(t['photos'])), 1)
        got = self.sized(core.photo_rows(t, t['url'], t['photos']))
        self.assertTrue(got['01.webp'].endswith(', ' + PHONE_FULL), got['01.webp'])
        self.assertTrue(got['02.webp'].endswith(', 50vw') and got['03.webp'].endswith(', 50vw'), got)
        # a single portrait in the grid has a row to itself (.jrow--one): min(column, ar x 624) wide from 760, the full
        # width below
        t = self.add('syn-rows-one', date='2025-06-17', photos=[ph(1, PORTRAIT)])
        got = self.sized(core.photo_rows(t, t['url'], t['photos']))
        self.assertEqual(got, {'01.webp': '(min-width: 760px) 468px, 100vw'})
        # the last, unconditional entry of every string in the rows: the slot for a landscape, half the screen for a
        # paired portrait, the whole screen for a portrait shown alone
        for slug in ('syn-rows', 'syn-rows-mixed', 'syn-rows-one'):
            x = self.by[slug]
            got = self.sized(core.photo_rows(x, x['url'], x['photos']))
            self.assertEqual(len(got), len(x['photos']))
            for p in x['photos']:
                last = got[os.path.basename(p['file'])].split(', ')[-1]
                if p['w'] > p['h']:
                    self.assertEqual(last, core.PHONE_SLOT)
                    self.assertTrue(got[os.path.basename(p['file'])].endswith(', ' + PHONE_FULL))
                else:
                    self.assertIn(last, ('50vw', '100vw'))
                    self.assertNotIn(core.PHONE_SLOT, got[os.path.basename(p['file'])])
        self.assertEqual(sorted(v.split(', ')[-1] for v in self.sized(core.photo_rows(self.by['syn-rows'], 'trips/syn-rows/',
                                                                                   self.by['syn-rows']['photos'])).values()),
                         ['100vw', '50vw', '50vw', '55vw', '55vw', '55vw'])

    def test_the_gallery_on_a_page_uses_those_strings(self):
        # on a built story page: the lead photo at HERO_SIZES, the gallery's landscape at the full-width string, its two
        # portraits two-up
        ph = lambda n, size: photo('photos/%02d.webp' % n, size, alt='Synthetic photo %d' % n, sm=True)   # noqa: E731
        slug = 'syn-rows-page'
        self.add(slug, body=WRITEUP, photos=[ph(1, LANDSCAPE), ph(2, LANDSCAPE), ph(3, PORTRAIT), ph(4, PORTRAIT)])
        self.assertEqual(self.hero(slug).find('img')['sizes'], HERO_SIZES)
        sec = self.main(slug).by_id('photos')
        got = {os.path.basename(i['src']): i['sizes'] for i in sec.find_all('img')}
        self.assertEqual(sorted(got), ['02.webp', '03.webp', '04.webp'])
        self.assertTrue(got['02.webp'].endswith(', ' + PHONE_FULL), got['02.webp'])
        self.assertTrue(got['03.webp'].endswith(', 50vw') and got['04.webp'].endswith(', 50vw'), got)

    def test_the_lone_portrait_beside_the_writeup_is_full_width_on_a_phone(self):
        # the aside photo of a lone-portrait story fills the phone's width as well. 10.3: and, being a portrait, is told
        # so: 100vw where the string ended with the 55vw slot
        slug = 'syn-aside-sized'
        self.add(slug, body=WRITEUP, photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic photo one', sm=True)])
        img = self.main(slug).find('figure', cls='rep-aside-ph').find('img')
        self.assertEqual(img['sizes'], '(min-width: 1200px) 294px, (min-width: 1000px) 22vw, (min-width: 760px) 240px, 100vw')
        self.assertNotIn(core.PHONE_SLOT, img['sizes'])
        self.assertEqual(img['srcset'], '../../trips/%s/photos/01.sm.webp 600w, ../../trips/%s/photos/01.webp 1200w' % (slug, slug))


# ---------------------------------------------------------------- Phase 4: the phone slot by photo shape (contract-phase4.md 10.3)

class PhoneShapeTests(ReportFixture):
    """contract-phase4.md 10.3: core.PHONE_SHAPES = (1.2, 1.6) and core.phone_sizes(sizes, p). The 55vw slot of
    core.PHONE_FULL is right for an ordinary landscape photo, whose .sm copy is 800 px wide; a portrait, a square, a
    panorama wider than 1.6 or a photo without a recorded size is told 100vw instead. core.photo, core.cover_img and
    core.cover_preload pass their sizes through it first. 10.5: the card-size .th copy is in no <img> srcset and no
    preload, whatever the shape and the string; a card cover that has one gets it from a phone-only <source>
    (CardSourceTests). A .th or .sm file is an empty placeholder beside the photo."""

    FULL = '(min-width: 1200px) 1248px, (min-width: 560px) 100vw, 55vw'       # report.HERO_SIZES, core.photo's default
    WIDE = '(min-width: 1200px) 1248px, 100vw'                                # ... with PHONE_FULL replaced
    # name: (w, h), inside PHONE_SHAPES?, the widths of its .th and .sm copies
    SHAPES = {'landscape': ((1600, 1200), True, 427, 800), 'three-two': ((1600, 1067), True, 480, 800),
              'six-five': ((1200, 1000), True, 384, 800), 'eight-five': ((1600, 1000), True, 512, 800),
              'portrait': ((1200, 1600), False, 320, 600), 'square': ((1000, 1000), False, 320, 800),
              'panorama': ((3810, 1600), False, 762, 800), 'sixteen-nine': ((1600, 900), False, 569, 800)}

    def cover(self, name, size, th=True, sm=True, **meta):
        """A report whose one photo (photos/01.webp, of this size; None: unsized) has its .sm and .th copies."""
        slug = 'syn-shape-' + name
        meta.setdefault('date', '2025-06-20')
        helpers.make_trip(self.tmp, slug, title='Synthetic ' + name, region=REGION, track=True,
                          photos=[photo('photos/01.webp', size, alt='Synthetic photo one', sm=sm)], **meta)
        if th:
            helpers.touch(os.path.join(self.tmp, slug, 'photos', '01.th.webp'))
        self.load_site()
        return self.by[slug]

    def test_the_shapes(self):
        self.assertEqual(need(self, core, 'PHONE_SHAPES'), (1.2, 1.6))
        self.assertEqual(core.PHONE_FULL, '(min-width: 560px) 100vw, 55vw')
        self.assertEqual(self.report.HERO_SIZES, self.FULL)
        self.assertEqual(self.FULL.replace(core.PHONE_FULL, '100vw'), self.WIDE)

    def test_phone_sizes_at_the_boundaries(self):
        phone_sizes = need(self, core, 'phone_sizes')
        cases = [((1200, 1000), self.FULL),      # 1.2 exactly: inside
                 ((1199, 1000), self.WIDE),      # just under
                 ((6, 5), self.FULL), ((1600, 1000), self.FULL),      # 1.6 exactly: inside
                 ((1601, 1000), self.WIDE),      # just over
                 ((8, 5), self.FULL), ((1600, 1200), self.FULL), ((1500, 1000), self.FULL), ((1600, 1067), self.FULL),
                 ((1200, 1001), self.WIDE), ((1599, 1000), self.FULL), ((1201, 1000), self.FULL)]
        for (w, h), want in cases:
            with self.subTest(w=w, h=h):
                self.assertEqual(phone_sizes(self.FULL, {'w': w, 'h': h}), want)

    def test_phone_sizes_by_shape(self):
        phone_sizes = need(self, core, 'phone_sizes')
        for name, ((w, h), inside, _th, _sm) in self.SHAPES.items():
            with self.subTest(name):
                self.assertEqual(phone_sizes(self.FULL, {'w': w, 'h': h}), self.FULL if inside else self.WIDE)
                self.assertEqual(core.PHONE_SHAPES[0] <= w / float(h) <= core.PHONE_SHAPES[1], inside)
        # a photo whose size is not recorded (or only half of it, or a zero) is told the real width too
        for p in ({}, {'w': None, 'h': None}, {'w': 1600}, {'h': 1200}, {'w': 1600, 'h': None}, {'w': 0, 'h': 1200}, {'w': 1600, 'h': 0}):
            with self.subTest(p=p):
                self.assertEqual(phone_sizes(self.FULL, p), self.WIDE)
        # every PHONE_FULL in the string is replaced, and nothing else of it
        for sizes in (core.PHONE_FULL, '(min-width: 760px) 468px, ' + core.PHONE_FULL,
                      '(min-width: 1200px) 400px, (min-width: 760px) calc((100vw - 80px) * 0.333), ' + core.PHONE_FULL):
            self.assertEqual(phone_sizes(sizes, {'w': 1200, 'h': 1600}), sizes[:-len(core.PHONE_FULL)] + '100vw')
            self.assertEqual(phone_sizes(sizes, {'w': 1600, 'h': 1200}), sizes)

    def test_a_string_without_the_full_width_slot_is_untouched(self):
        phone_sizes = need(self, core, 'phone_sizes')
        home, trips = load_module(self, 'sitegen.pages.home'), load_module(self, 'sitegen.pages.trips')
        for sizes in (core.RELATED_SIZES, trips.TRX_SIZES, home.RECENT_SIZES, '50vw', '100vw', '', core.PHONE_SLOT,
                      '(min-width: 760px) 50vw, 55vw', '(min-width: 1200px) 400px, (min-width: 760px) calc((100vw - 80px) * 0.333), 50vw'):
            self.assertNotIn(core.PHONE_FULL, sizes)
            for p in ({'w': 1600, 'h': 1200}, {'w': 1200, 'h': 1600}, {'w': 1000, 'h': 1000}, {'w': 3810, 'h': 1600}, {}):
                with self.subTest(sizes=sizes, p=p):
                    self.assertEqual(phone_sizes(sizes, p), sizes)
        for sizes in (self.report.HERO_SIZES, home.LEAD_SIZES, home.SUB_SIZES, home.WIDE_SUB_SIZES):      # ... and these are not
            self.assertIn(core.PHONE_FULL, sizes)
            self.assertEqual(phone_sizes(sizes, {'w': 1200, 'h': 1600}), sizes.replace(core.PHONE_FULL, '100vw'))
            self.assertTrue(phone_sizes(sizes, {'w': 1200, 'h': 1600}).endswith(', 100vw'))

    def test_photo_cover_img_and_cover_preload_apply_it(self):
        # each of the three writes phone_sizes(sizes, the photo) where it wrote sizes; the cover's <img> and its preload
        # therefore carry the same srcset and the same sizes, whatever the shape. 10.5: that srcset is the two
        # candidates it was before Phase 4 for every shape (a cover outside the shapes listed its .th copy under 10.3);
        # the .th copy is only in the phone <source> of a card
        for k, (name, (size, inside, th_w, sm_w)) in enumerate(sorted(self.SHAPES.items())):
            with self.subTest(name):
                t = self.cover(name, size, date='2025-06-%02d' % (k + 1))
                p = t['cover']['photo']
                self.assertEqual(p['th'], 'photos/01.th.webp')
                base = '../../trips/%s/photos/' % t['slug']
                two = '%s01.sm.webp %dw, %s01.webp %dw' % (base, sm_w, base, size[0])
                three = '%s01.th.webp %dw, %s' % (base, th_w, two)
                sizes = self.FULL if inside else self.WIDE
                self.assertEqual(sizes, core.phone_sizes(self.FULL, p))
                # core.photo: its default string, and one handed to it (a gallery photo is never given the .th copy)
                img = Doc(core.photo(t, p, t['url'])).find('img')
                self.assertEqual((img['sizes'], img['srcset']), (sizes, two))
                img = Doc(core.photo(t, p, t['url'], sizes='(min-width: 760px) 468px, ' + core.PHONE_FULL)).find('img')
                self.assertEqual(img['sizes'], '(min-width: 760px) 468px, ' + (core.PHONE_FULL if inside else '100vw'))
                # core.cover_img and core.cover_preload at the lead photo's string: the bare <img>, two candidates
                lead = core.cover_img(t, t['url'], self.report.HERO_SIZES, eager=True)
                self.assertTrue(lead.startswith('<img class="cover-img" '), lead)
                img = Doc(lead).find('img')
                link_ = Doc(core.cover_preload(t, t['url'], self.report.HERO_SIZES)).find('link')
                self.assertEqual(img['sizes'], sizes)
                self.assertEqual(img['srcset'], two)
                self.assertEqual((link_['imagesizes'], link_['imagesrcset'], link_['href']), (img['sizes'], img['srcset'], img['src']))
                self.assertNotIn('.th.', lead + core.cover_img(t, t['url'], self.report.HERO_SIZES) + core.cover_preload(t, t['url'], self.report.HERO_SIZES))
                # a card's string holds no PHONE_FULL: untouched. Its <img> has the same two candidates for every shape,
                # and so has a preload asked for at that string; the three-candidate list is the <source>'s
                card = Doc(core.cover_img(t, t['url'], core.RELATED_SIZES))
                img = card.find('img')
                self.assertEqual((img['sizes'], img['srcset']), (core.RELATED_SIZES, two))
                # (the source declares the slot as 106 px, core.CARD_PHONE_SIZES: contract-phase5.md section 5)
                self.assertEqual([(s_['srcset'], s_['sizes'], s_['media']) for s_ in card.find_all('source')],
                                 [(three, '106px', '(max-width: 559.98px)')])
                link_ = Doc(core.cover_preload(t, t['url'], core.RELATED_SIZES)).find('link')
                self.assertEqual((link_['imagesizes'], link_['imagesrcset']), (core.RELATED_SIZES, two))

    def test_a_cover_without_a_th_copy_keeps_its_two_candidates_at_either_width(self):
        for name, size, sm_w in (('portrait', PORTRAIT, 600), ('landscape', LANDSCAPE, 800)):
            with self.subTest(name):
                t = self.cover(name + '-two', size, th=False, date='2025-06-21')
                base = '../../trips/%s/photos/' % t['slug']
                img = Doc(core.cover_img(t, t['url'], self.report.HERO_SIZES)).find('img')
                self.assertEqual(img['srcset'], '%s01.sm.webp %dw, %s01.webp %dw' % (base, sm_w, base, size[0]))
                self.assertEqual(img['sizes'], self.WIDE if name == 'portrait' else self.FULL)

    def test_an_unsized_cover_has_no_srcset_and_no_sizes(self):
        # nothing to choose between, so nothing is said about a width; the preload is the plain file as well
        t = self.cover('unsized', None)
        img = Doc(core.cover_img(t, t['url'], self.report.HERO_SIZES, eager=True)).find('img')
        self.assertEqual((img['srcset'], img['sizes']), (None, None))
        self.assertEqual(core.cover_preload(t, t['url'], self.report.HERO_SIZES),
                         '<link rel="preload" as="image" href="../../trips/syn-shape-unsized/photos/01.webp" fetchpriority="high">')
        self.assertNotIn('sizes', core.photo(t, t['cover']['photo'], t['url']))
        self.assertEqual(core.phone_sizes(self.FULL, t['cover']['photo']), self.WIDE)

    def test_the_lead_photo_of_a_story_and_its_preload_agree_for_every_shape_that_leads(self):
        # on a built page: a panorama and a 16:9 photo lead the page (wide enough for the frame) and are told 100vw; an
        # ordinary landscape keeps the slot. The head's preload repeats the <img> exactly, so the browser preloads the
        # file it then shows. 10.5: two candidates for every shape (the wide ones listed their .th copy under 10.3), and
        # the lead photo is never wrapped in a <picture>
        want = {'landscape': self.FULL, 'three-two': self.FULL, 'six-five': self.FULL, 'eight-five': self.FULL,
                'panorama': self.WIDE, 'sixteen-nine': self.WIDE}
        for k, (name, sizes) in enumerate(sorted(want.items())):
            with self.subTest(name):
                t = self.cover(name + '-lead', self.SHAPES[name][0], body=WRITEUP, date='2025-07-%02d' % (k + 1))
                slug = t['slug']
                self.assertEqual(t['cover']['photo']['th'], 'photos/01.th.webp')
                links = self.preloads(slug)
                self.assertEqual(len(links), 1)
                img = self.hero(slug).find('img')
                self.assertEqual(img['sizes'], sizes)
                base = '../../trips/%s/photos/' % slug
                self.assertEqual(img['srcset'], '%s01.sm.webp 800w, %s01.webp %dw' % (base, base, self.SHAPES[name][0][0]))
                self.assertEqual((links[0]['href'], links[0]['imagesrcset'], links[0]['imagesizes']), (img['src'], img['srcset'], img['sizes']))
                self.assertIs(img.parent, self.hero(slug).find('a'))                 # straight in its link: no <picture>
                self.assertEqual(self.hero(slug).find_all('picture') + self.hero(slug).find_all('source'), [])
                self.assertNotIn('.th.', self.head_html(slug))
                self.assertNotIn('.th.', self.page(slug).html.split('<main', 1)[1].split('rep-related', 1)[0])
        # a portrait or a square cover does not lead a page: no lead photo, no cover preload
        for name in ('portrait', 'square'):
            slug = self.cover(name + '-lead', self.SHAPES[name][0], body=WRITEUP, date='2025-08-01')['slug']
            self.assertIsNone(self.hero(slug))
            self.assertEqual([ln for ln in self.preloads(slug) if '/photos/' in ln['href']], [])

    def test_the_home_page_strings_follow_the_cover_too(self):
        # the home page's featured cards go through core.cover_img: a portrait cover there is told 100vw, a landscape the
        # slot. 10.5: neither lists its .th copy and neither is wrapped: these are full-width strings, not a card's
        home = load_module(self, 'sitegen.pages.home')
        tall, wide = self.cover('portrait-home', PORTRAIT), self.cover('landscape-home', LANDSCAPE, date='2025-06-21')
        tall = self.by[tall['slug']]
        self.assertEqual((tall['cover']['photo']['th'], wide['cover']['photo']['th']), ('photos/01.th.webp', 'photos/01.th.webp'))
        for sizes in (home.LEAD_SIZES, home.SUB_SIZES, home.WIDE_SUB_SIZES):
            with self.subTest(sizes=sizes):
                self.assertEqual(Doc(core.cover_img(tall, '', sizes)).find('img')['sizes'], sizes.replace(core.PHONE_FULL, '100vw'))
                self.assertEqual(Doc(core.cover_img(wide, '', sizes)).find('img')['sizes'], sizes)
                for t in (tall, wide):
                    for eager in (False, True):
                        got = core.cover_img(t, '', sizes, eager=eager)
                        self.assertNotIn('.th.', got)
                        self.assertTrue(got.startswith('<img class="cover-img" ') and got.endswith('>') and got.count('<') == 1, got)
        base = 'trips/%s/photos/' % tall['slug']
        self.assertEqual(Doc(core.cover_img(tall, '', home.LEAD_SIZES)).find('img')['srcset'], '%s01.sm.webp 600w, %s01.webp 1200w' % (base, base))


# ---------------------------------------------------------------- Phase 4: the card-size copy (contract-phase4.md 5.3, 10.5)

PICTURE = re.compile(r'<picture class="cover-pic">(<source [^>]*>)(<img [^>]*>)</picture>')


def unwrap(html_):
    """A page or fragment with every card cover's <picture class="cover-pic"> taken off: the <img> it holds, alone. What
    the markup was before a .th copy existed (contract 10.5: the <img> itself is not changed by the wrapper)."""
    return PICTURE.sub(lambda m: m.group(2), html_)


class CoverSrcsetTests(ReportFixture):
    """contract-phase4.md 5.3 as replaced by 10.5: content.load_trip records a photo's card-size copy (320 px on the
    short edge) as p['th'] when the file exists, and core.thumb_width gives its width. That copy is a candidate in no
    <img> srcset and no preload: core._cover_srcset is the two candidates it was before Phase 4, whatever is on disk.
    A card cover offers it to phones in a <source> of its own (CardSourceTests). A .th file is an empty placeholder
    written beside the photo by the test: the loader only looks whether it is there."""

    def with_copies(self, slug, size, th=True, sm=True, **meta):
        """A report whose one photo (photos/01.webp, `size`) has an .sm copy and, with th=True, a .th copy."""
        meta.setdefault('date', '2025-06-20')
        self.add(slug, photos=[photo('photos/01.webp', size, alt='Synthetic photo one', sm=sm)], **meta)
        if th:
            helpers.touch(os.path.join(self.tmp, slug, 'photos', '01.th.webp'))
            self.load_site()
        return self.by[slug]

    def srcset(self, t):
        return need(self, core, '_cover_srcset')(t, t['cover']['photo'], t['url'])

    def test_thumb_width_is_320_on_the_short_edge(self):
        thumb_width = need(self, core, 'thumb_width')
        self.assertEqual(need(self, core, 'THUMB_EDGE'), 320)
        for (w, h), want in (((1600, 1200), 427), ((1200, 1600), 320), ((3810, 1600), 762), ((1000, 1000), 320),
                             ((738, 1600), 320), ((1600, 900), 569), ((1600, 1067), 480)):
            with self.subTest(w=w, h=h):
                got = thumb_width({'w': w, 'h': h})
                self.assertEqual(got, want)
                self.assertIs(type(got), int)

    def test_thumb_width_is_the_width_the_copy_is_written_at(self):
        # the srcset states the file's real width: core.thumb_width and tools/lib/photos.thumb_size agree to the pixel
        photos = load_module(self, 'photos')
        self.assertEqual(need(self, photos, 'THUMB_EDGE'), core.THUMB_EDGE)
        for w in list(range(601, 1700, 37)) + [738, 1200, 1600, 3810, 4032]:
            for h in list(range(599, 1700, 41)) + [738, 1200, 1600, 3024]:
                tw, th = photos.thumb_size(w, h)
                self.assertEqual(core.thumb_width({'w': w, 'h': h}), tw, (w, h))
                self.assertEqual(min(tw, th), 320, (w, h))

    def test_load_trip_records_the_th_copy_only_when_the_file_exists(self):
        with_th = self.with_copies('syn-th', LANDSCAPE)
        without = self.with_copies('syn-no-th', LANDSCAPE, th=False)
        self.assertEqual(with_th['photos'][0]['th'], 'photos/01.th.webp')
        self.assertEqual(with_th['photos'][0]['sm'], 'photos/01.sm.webp')
        self.assertIn('th', without['photos'][0])
        self.assertIsNone(without['photos'][0]['th'])
        self.assertIs(with_th['cover']['photo'], with_th['photos'][0])
        # day photos too (a multi-day cover is often a day's photo)
        t = self.add('syn-th-days', kind='multi-day', activity='ski', date='2025-03-01', end_date='2025-03-02',
                     days=[{'title': 'Synthetic Day One', 'date': '2025-03-01',
                            'photos': [photo('photos/d01-01.webp', LANDSCAPE, alt='Synthetic day photo one', sm=True)]},
                           {'title': 'Synthetic Day Two', 'date': '2025-03-02',
                            'photos': [photo('photos/d02-01.webp', LANDSCAPE, alt='Synthetic day photo two', sm=True)]}])
        self.assertEqual([d['photos'][0]['th'] for d in t['days']], [None, None])
        helpers.touch(os.path.join(self.tmp, 'syn-th-days', 'photos', 'd01-01.th.webp'))
        self.load_site()
        self.assertEqual([d['photos'][0]['th'] for d in self.by['syn-th-days']['days']], ['photos/d01-01.th.webp', None])

    def test_a_cover_with_a_th_copy_still_lists_two_candidates(self):
        # 10.5: core._cover_srcset(t, p, here) -> '<sm> <w>w, <full> <w>w', whatever copies are on disk: the .th copy
        # (which 10 listed first, at core.thumb_width) is not a candidate of the <img>
        cases = (('syn-th-land', LANDSCAPE, (800, 1600)), ('syn-th-port', PORTRAIT, (600, 1200)), ('syn-th-pano', (3810, 1600), (800, 3810)))
        for slug, size, widths in cases:
            with self.subTest(slug):
                bare = self.with_copies(slug + '-bare', size, th=False, date='2025-06-19')
                t = self.with_copies(slug, size)
                self.assertEqual((bare['cover']['photo']['th'], t['cover']['photo']['th']), (None, 'photos/01.th.webp'))
                base = '../../trips/%s/photos/' % slug
                src, srcset = self.srcset(t)
                self.assertEqual(src, base + '01.webp')
                self.assertEqual(srcset, '%s01.sm.webp %dw, %s01.webp %dw' % (base, widths[0], base, widths[1]))
                self.assertNotIn('.th.', srcset)
                # the same list as for the same photo without the copy
                self.assertEqual(srcset.replace(slug, slug + '-bare'), self.srcset(bare)[1])
                got = [int(c.rsplit(' ', 1)[1][:-1]) for c in srcset.split(', ')]
                self.assertEqual(got, sorted(got))
                self.assertEqual(len(got), 2)

    def test_cover_srcset_takes_no_sizes(self):
        # 10.5: the list no longer depends on the slot, so the function has no sizes parameter: a caller that still
        # passes one is told so at once
        t = self.with_copies('syn-th-args', LANDSCAPE)
        cover_srcset = need(self, core, '_cover_srcset')
        p = t['cover']['photo']
        self.assertEqual(cover_srcset(t, p, t['url']), cover_srcset(t=t, p=p, here=t['url']))
        for extra in (core.RELATED_SIZES, self.report.HERO_SIZES, ''):
            with self.assertRaises(TypeError):
                cover_srcset(t, p, t['url'], extra)
        with self.assertRaises(TypeError):
            cover_srcset(t, p, t['url'], sizes=core.RELATED_SIZES)

    def test_a_cover_without_a_th_copy_keeps_the_two_candidates(self):
        # 5.3: 'Missing .th: today's srcset'
        t = self.with_copies('syn-two', LANDSCAPE, th=False)
        self.assertEqual(self.srcset(t), ('../../trips/syn-two/photos/01.webp',
                                          '../../trips/syn-two/photos/01.sm.webp 800w, ../../trips/syn-two/photos/01.webp 1600w'))
        t = self.with_copies('syn-two-tall', PORTRAIT, th=False, date='2025-06-21')
        self.assertEqual(self.srcset(t)[1], '../../trips/syn-two-tall/photos/01.sm.webp 600w, ../../trips/syn-two-tall/photos/01.webp 1200w')

    def test_no_srcset_without_the_sm_copy_or_the_size(self):
        # as before: a photo without its .sm copy, or without a recorded size, is a plain src, .th file or not
        t = self.with_copies('syn-th-only', LANDSCAPE, sm=False)
        self.assertEqual(t['cover']['photo']['th'], 'photos/01.th.webp')
        self.assertEqual(self.srcset(t), ('../../trips/syn-th-only/photos/01.webp', ''))
        t = self.with_copies('syn-th-unsized', None, date='2025-06-21')
        self.assertEqual(self.srcset(t), ('../../trips/syn-th-unsized/photos/01.webp', ''))
        self.assertNotIn('srcset', core.cover_img(t, t['url'], core.RELATED_SIZES))

    def test_no_img_and_no_preload_lists_the_th_copy(self):
        # 10.5: at a full-width string and at a card string alike, the <img> and the preload of a cover that has a .th
        # copy carry the two candidates they carried before Phase 4. (10.2 kept the copy out of the full-width
        # strings only: with 427w in a card's list a 1x desktop screen took it for the card's 400 px slot.)
        t = self.with_copies('syn-th-lead', LANDSCAPE)
        p = t['cover']['photo']
        self.assertEqual(p['th'], 'photos/01.th.webp')
        base = '../../trips/syn-th-lead/photos/'
        two = '%s01.sm.webp 800w, %s01.webp 1600w' % (base, base)
        self.assertEqual(need(self, core, '_cover_srcset')(t, p, t['url']), (base + '01.webp', two))
        home, trips = load_module(self, 'sitegen.pages.home'), load_module(self, 'sitegen.pages.trips')
        full = (self.report.HERO_SIZES, home.LEAD_SIZES, home.SUB_SIZES, home.WIDE_SUB_SIZES, core.PHONE_FULL, core.PHONE_SLOT)
        cards = (core.RELATED_SIZES, trips.TRX_SIZES, home.RECENT_SIZES)
        for sizes in full + cards:
            for eager in (False, True):
                with self.subTest(sizes=sizes, eager=eager):
                    got = core.cover_img(t, t['url'], sizes, eager=eager)
                    imgs = Doc(got).find_all('img')
                    self.assertEqual([(i['srcset'], i['sizes']) for i in imgs], [(two, sizes)])
                    self.assertIn('<img class="cover-img" src="%s01.webp" srcset="%s" sizes="%s" width="1600" height="1200" ' % (base, two, sizes), got)
                    # the copy is named at most once in the whole fragment: in the phone <source> of a card that is not
                    # the page's lead image
                    self.assertEqual(got.count('.th.'), 1 if (sizes in cards and not eager) else 0)
            with self.subTest(sizes=sizes, preload=True):
                self.assertEqual(core.cover_preload(t, t['url'], sizes),
                                 '<link rel="preload" as="image" href="%s01.webp" imagesrcset="%s" imagesizes="%s" fetchpriority="high">'
                                 % (base, two, sizes))
        for sizes in full:
            self.assertIn(core.PHONE_SLOT, sizes)
        for sizes in cards:
            self.assertNotIn(core.PHONE_SLOT, sizes)
            self.assertTrue(sizes.endswith(', 112px'))

    def test_the_phone_slot_picks_the_800_px_copy_on_every_phone_up_to_1440_device_pixels_wide(self):
        # the arithmetic behind PHONE_SLOT, as a browser does it: the first candidate at least slot x DPR wide. With
        # the two candidates of a full-width landscape photo (800 and 1600), a phone 320 to 440 px wide takes the
        # 800 px copy at any DPR, as long as its screen is at most 1440 device pixels wide (the widest phone panels).
        # With a 427 px candidate in the list the small 2x phones would be handed that one.
        self.assertTrue(core.PHONE_SLOT.endswith('vw'))
        share = float(core.PHONE_SLOT[:-2]) / 100

        def pick(widths, vw, dpr):
            need_px = vw * share * dpr
            return next((w for w in widths if w >= need_px), widths[-1])

        seen = 0
        for vw in range(320, 441):
            for dpr in (1, 1.5, 2, 2.625, 2.75, 3, 3.5, 3.75, 4):
                if vw * dpr <= 1440:
                    seen += 1
                    self.assertEqual(pick((800, 1600), vw, dpr), 800, (vw, dpr))
        self.assertGreater(seen, 800)
        self.assertEqual(pick((800, 1600), 440, 3), 800)        # the widest 3x phone
        self.assertEqual(pick((800, 1600), 412, 3.5), 800)
        self.assertEqual(pick((800, 1600), 384, 3.75), 800)
        self.assertEqual(pick((427, 800, 1600), 375, 2), 427)   # what leaving .th in the list would do
        self.assertEqual(pick((427, 800, 1600), 390, 3), 800)

    def test_the_card_slots_pick_the_th_copy_on_a_phone_and_never_on_a_desktop(self):
        # the arithmetic behind 10.5, as a browser does it: the first candidate at least slot x DPR wide, else the
        # largest (pick_candidate). Below 560 px a card's cover is 112 px wide and the <source> applies: its list is the
        # .th copy, the 800 px copy and the full file, and 427 px is enough for that slot at any pixel density a phone
        # has, whether the slot is declared at the real 112 px or, as since Phase 5, at 106 px (CardSourceTests has the
        # arithmetic of that change)
        pick = pick_candidate
        self.assertEqual(need(self, core, 'CARD_PHONE_SLOT'), '112px')
        slot = int(core.CARD_PHONE_SLOT[:-2])
        declared = int(need(self, core, 'CARD_PHONE_SIZES')[:-2])
        for dpr in (1, 1.25, 1.5, 2, 2.25, 2.5, 2.625, 2.75, 3, 3.5, 3.75):
            with self.subTest(dpr=dpr):
                self.assertEqual(pick((427, 800, 1600), slot, dpr), 427)
                self.assertEqual(pick((427, 800, 1600), declared, dpr), 427)
        self.assertLessEqual(slot * 3.75, 427)
        self.assertEqual(pick((427, 800, 1600), slot, 4), 800)                  # past 427 / 112 = 3.8 the next copy up
        # a portrait cover's copy is 320 px wide (the short edge). Declared at 112 px that was enough up to 2.85x and
        # a 3x phone took the 600 px copy; declared at 106 px the 3x phone takes the copy as well
        self.assertEqual([pick((320, 600, 1200), slot, dpr) for dpr in (1, 2, 2.75, 3, 3.75)], [320, 320, 320, 600, 600])
        self.assertEqual([pick((320, 600, 1200), declared, dpr) for dpr in (1, 2, 2.75, 3, 3.75)], [320, 320, 320, 320, 600])
        # From 560 px up the <source> does not apply and the <img> decides. Its slot grows to 400 px on a desktop
        # (RELATED_SIZES / TRX_SIZES / RECENT_SIZES: '(min-width: 1200px) 400px'), and its list is the 800 px copy and the
        # full file: 800 at 1x and at 2x, the full file at 3x, as before Phase 4.
        self.assertIn('(min-width: 1200px) 400px, ', core.RELATED_SIZES)
        self.assertEqual([pick((800, 1600), 400, dpr) for dpr in (1, 2, 3)], [800, 800, 1600])
        # With 427 in that second list a 1x screen would pick 427 for the 400 px slot (1.07 source pixels per screen
        # pixel, visibly softer than the 800 px copy it had before the phase): what this rule prevents.
        self.assertEqual(pick((427, 800, 1600), 400, 1), 427)
        self.assertEqual([pick((427, 800, 1600), 400, dpr) for dpr in (2, 3)], [800, 1600])

    def test_more_like_this_cards_offer_the_th_copy_to_phones_only(self):
        # 10.5: a card cover on a report page ('More like this', core.RELATED_SIZES: unchanged) whose report has a .th
        # copy is wrapped in <picture class="cover-pic"> with one phone-only <source> that lists the copy first; its
        # <img> keeps the two candidates (under 5.3 the copy was the first candidate of the <img> itself). A card
        # without the copy is the bare <img> it always was
        self.with_copies('syn-rel-th', LANDSCAPE, region='Synthetic Other Range', activity='mtb', date='2025-01-10')
        self.with_copies('syn-rel-plain', LANDSCAPE, th=False, region='Synthetic Other Range', activity='mtb', date='2025-01-11')
        self.with_copies('syn-rel-none', LANDSCAPE, th=False, sm=False, region='Synthetic Other Range', activity='mtb', date='2025-01-12')
        self.add('syn-rel-page', region='Synthetic Other Range', activity='climb', date='2025-01-13')
        items = {c['data-slug']: c for c in self.main('syn-rel-page').find('ul', cls='rep-rel').find_all('li', cls='tcard')}
        cards = {slug: c.find('img') for slug, c in items.items()}
        self.assertEqual(sorted(cards), ['syn-rel-none', 'syn-rel-plain', 'syn-rel-th'])
        base = '../../trips/%s/photos/'
        two = ', '.join([base % 'syn-rel-th' + '01.sm.webp 800w', base % 'syn-rel-th' + '01.webp 1600w'])
        self.assertEqual(cards['syn-rel-th']['srcset'], two)
        self.assertEqual(cards['syn-rel-plain']['srcset'], ', '.join([base % 'syn-rel-plain' + '01.sm.webp 800w', base % 'syn-rel-plain' + '01.webp 1600w']))
        self.assertNotIn('srcset', cards['syn-rel-none'])
        sizes = '(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2), 112px'
        self.assertEqual(need(self, core, 'RELATED_SIZES'), sizes)                 # the card strings are unchanged
        self.assertEqual((cards['syn-rel-th']['sizes'], cards['syn-rel-plain']['sizes']), (sizes, sizes))
        for slug, img in cards.items():
            self.assertEqual(img['src'], base % slug + '01.webp')                  # the fallback src is still the full file
            self.assertEqual(img['loading'], 'lazy')
        # the wrapper: only around the cover that has the copy, inside the card's photo link, holding the source and the img
        self.assertEqual({slug: [n.tag for n in c.find('a', cls='tcard-img').elements()] for slug, c in items.items()},
                         {'syn-rel-th': ['picture'], 'syn-rel-plain': ['img'], 'syn-rel-none': ['img']})
        pic = items['syn-rel-th'].find('picture')
        self.assertEqual((pic.classes, [n.tag for n in pic.elements()]), (['cover-pic'], ['source', 'img']))
        src = pic.find('source')
        self.assertEqual(sorted(src.attrs), ['media', 'sizes', 'srcset'])
        self.assertEqual((src['media'], src['sizes']), ('(max-width: 559.98px)', '106px'))       # core.CARD_PHONE_SIZES: what the source declares
        self.assertEqual(src['srcset'], base % 'syn-rel-th' + '01.th.webp 427w, ' + two)
        html_ = self.page('syn-rel-page').html
        self.assertEqual((html_.count('<picture'), html_.count('</picture>'), html_.count('<source'), html_.count('.th.')), (1, 1, 1, 1))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, 'syn-rel-th', 'photos', '01.th.webp')))      # the file the source names
        # without the .th file the page is the same page minus that wrapper
        os.remove(os.path.join(self.tmp, 'syn-rel-th', 'photos', '01.th.webp'))
        self.load_site()
        before = self.page('syn-rel-page').html
        self.assertNotIn('<picture', before)
        self.assertNotIn('.th.', before)
        self.assertEqual(unwrap(html_), before)
        self.assertNotEqual(html_, before)

    def test_the_preload_and_the_lead_image_always_agree(self):
        # 5.2 / 5.3: whatever copies the cover has, the head's preload names the candidates and the sizes of the hero
        # <img> exactly, so the browser preloads the file it then shows
        cases = (('syn-lead-th', True, True), ('syn-lead-sm', False, True), ('syn-lead-plain', False, False), ('syn-lead-th-only', True, False))
        for k, (slug, th, sm) in enumerate(cases):
            with self.subTest(slug):
                self.with_copies(slug, LANDSCAPE, th=th, sm=sm, body=WRITEUP, date='2025-07-%02d' % (k + 1))
                links = self.preloads(slug)
                self.assertEqual(len(links), 1)
                img = self.hero(slug).find('img')
                self.assertEqual(links[0]['href'], img['src'])
                self.assertEqual(links[0]['imagesrcset'], img['srcset'])
                self.assertEqual(links[0]['imagesizes'], img['sizes'])
                self.assertEqual(img['srcset'] is not None, sm)
                self.assertEqual(img['sizes'], HERO_SIZES if sm else None)
                self.assertEqual((links[0]['fetchpriority'], img['fetchpriority']), ('high', 'high'))


# ---------------------------------------------------------------- Phase 4: the phone-only source of a card cover (contract-phase4.md 10.5)

class CardSourceTests(ReportFixture):
    """contract-phase4.md 10.5: the card-size .th copy is offered to phones only. core.CARD_PHONE_SLOT ('112px') and
    core.CARD_PHONE_MEDIA ('(max-width: 559.98px)'); core._card_source(t, p, here, sizes) is the <source> for a card
    sizes string (one that ends ', 112px') when the photo has its .th and .sm copies and a recorded size, else '';
    core.cover_img wraps a card cover that is not the page's lead image in <picture class="cover-pic"> with that
    source in front of the <img> it has always written. Reason: with 427w in the <img>'s own list a 1x desktop screen
    took the .th copy for the card's 400 px slot, and the photo looked softer than before the phase.

    contract-phase5.md section 5 (the card-size copy): the source declares the slot as core.CARD_PHONE_SIZES, '106px'
    (THUMB_EDGE // 3), instead of the real 112 px, so that a 3x phone is served by the 320 px copy of a portrait or
    square cover. CARD_PHONE_SLOT stays '112px': it still ends every card sizes string and still decides which strings
    get a source. Nothing else about the source changes."""

    CARD = '(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2), 112px'

    def cover(self, name, size, th=True, sm=True, **meta):
        """A report whose one photo (photos/01.webp, `size`; None: unsized) has its .sm copy and, with th, its .th copy."""
        slug = 'syn-card-' + name
        meta.setdefault('date', '2025-06-20')
        helpers.make_trip(self.tmp, slug, title='Synthetic ' + name, region=REGION, track=True,
                          photos=[photo('photos/01.webp', size, alt='Synthetic "photo" one', sm=sm)], **meta)
        if th:
            helpers.touch(os.path.join(self.tmp, slug, 'photos', '01.th.webp'))
        self.load_site()
        return self.by[slug]

    def strings(self):
        """(the card strings, strings that are not a card's)."""
        home, trips = load_module(self, 'sitegen.pages.home'), load_module(self, 'sitegen.pages.trips')
        cards = (core.RELATED_SIZES, trips.TRX_SIZES, home.RECENT_SIZES)
        others = (self.report.HERO_SIZES, home.LEAD_SIZES, home.SUB_SIZES, home.WIDE_SUB_SIZES, core.PHONE_FULL, '100vw', '',
                  '(min-width: 1200px) 400px, 100vw', '112px', '(min-width: 560px) 50vw,112px', '(min-width: 560px) 50vw, 112px ',
                  '112px, 100vw', '(min-width: 560px) 50vw, 1112px', '(min-width: 560px) 50vw, 112PX')
        return cards, others

    def test_the_two_constants(self):
        self.assertEqual(need(self, core, 'CARD_PHONE_SLOT'), '112px')
        self.assertEqual(need(self, core, 'CARD_PHONE_MEDIA'), '(max-width: 559.98px)')
        # ... and the third: what the source declares for that slot, six px under the real one
        self.assertEqual(need(self, core, 'CARD_PHONE_SIZES'), '106px')
        self.assertEqual(core.CARD_PHONE_SIZES, '%dpx' % (core.THUMB_EDGE // 3))
        self.assertEqual(core.THUMB_EDGE, 320)
        cards, others = self.strings()
        for sizes in cards:
            self.assertNotIn(core.CARD_PHONE_SIZES, sizes)                    # no sizes string of an <img> carries the declared 106 px
        for sizes in cards:
            # a card's phone slot is the last, unconditional item of its string, and its first breakpoint is where the
            # source's media query ends
            self.assertEqual(sizes, self.CARD)
            self.assertTrue(sizes.endswith(', ' + core.CARD_PHONE_SLOT))
            self.assertIn('(min-width: 560px) ', sizes)
        for sizes in others:
            self.assertFalse(sizes.endswith(', ' + core.CARD_PHONE_SLOT), sizes)

    def test_card_source_for_a_landscape_a_portrait_and_a_panorama(self):
        # '<source media="(max-width: 559.98px)" srcset="<th> <thumb_width>w, <sm> <w>w, <full> <w>w" sizes="106px">'
        card_source = need(self, core, '_card_source')
        want = '<source media="(max-width: 559.98px)" srcset="%s01.th.webp %dw, %s01.sm.webp %dw, %s01.webp %dw" sizes="106px">'
        cases = (('landscape', LANDSCAPE, (427, 800, 1600)), ('portrait', PORTRAIT, (320, 600, 1200)), ('panorama', (3810, 1600), (762, 800, 3810)),
                 ('square', (1000, 1000), (320, 800, 1000)), ('sixteen-nine', (1600, 900), (569, 800, 1600)))
        for k, (name, size, widths) in enumerate(cases):
            with self.subTest(name):
                t = self.cover(name, size, date='2025-06-%02d' % (k + 1))
                p = t['cover']['photo']
                base = '../../trips/%s/photos/' % t['slug']
                got = card_source(t, p, t['url'], self.CARD)
                self.assertEqual(got, want % (base, widths[0], base, widths[1], base, widths[2]))
                self.assertEqual(widths[0], core.thumb_width(p))
                self.assertEqual(sorted(widths), list(widths))               # for these shapes the list ascends
                src = Doc(got).find('source')
                self.assertEqual((src['media'], src['sizes']), (core.CARD_PHONE_MEDIA, core.CARD_PHONE_SIZES))
                self.assertNotEqual(src['sizes'], core.CARD_PHONE_SLOT)       # the string it was handed ends with 112 px; the source says 106
                # from another folder depth the three candidates move together
                self.assertEqual(card_source(t, p, 'trips/', self.CARD), got.replace('../../trips/', '../trips/'))
                self.assertEqual(card_source(t, p, '', self.CARD), got.replace('../../trips/', 'trips/'))
                # ... and they are the <img>'s two candidates with the .th copy put in front
                self.assertEqual(src['srcset'], '%s01.th.webp %dw, %s' % (base, widths[0], core._cover_srcset(t, p, t['url'])[1]))

    def test_the_candidates_of_a_very_wide_panorama_do_not_ascend(self):
        # .th is 320 px on the SHORT edge and .sm 800 px on the LONG one: past 2.5 : 1 the .th copy is the wider file. The
        # source lists them in the same order all the same (a browser picks by width, not by position)
        t = self.cover('strip', (4000, 1500))
        p = t['cover']['photo']
        base = '../../trips/%s/photos/' % t['slug']
        self.assertEqual(core.thumb_width(p), 853)
        self.assertEqual(need(self, core, '_card_source')(t, p, t['url'], self.CARD),
                         '<source media="(max-width: 559.98px)" srcset="%s01.th.webp 853w, %s01.sm.webp 800w, %s01.webp 4000w" sizes="106px">'
                         % (base, base, base))

    def test_no_source_without_both_copies_and_a_recorded_size(self):
        card_source = need(self, core, '_card_source')
        t = self.cover('all', LANDSCAPE)
        p = t['cover']['photo']
        self.assertTrue(card_source(t, p, t['url'], self.CARD).startswith('<source '))
        for lacking in ({'th': None}, {'sm': None}, {'w': None}, {'h': None}, {'w': None, 'h': None}, {'w': 0}, {'h': 0}, {'th': ''}, {'sm': ''}):
            with self.subTest(lacking=lacking):
                self.assertEqual(card_source(t, dict(p, **lacking), t['url'], self.CARD), '')
        # as loaded from disk: no .th file, no .sm file, no size in index.md
        for name, kw in (('no-th', dict(th=False)), ('no-sm', dict(sm=False)), ('no-size', dict(size=None))):
            with self.subTest(name):
                x = self.cover(name, kw.pop('size', LANDSCAPE), **kw)
                self.assertEqual(card_source(x, x['cover']['photo'], x['url'], self.CARD), '')
                self.assertNotIn('<picture', core.cover_img(x, x['url'], self.CARD))
                self.assertNotIn('<source', core.cover_img(x, x['url'], self.CARD))

    def test_no_source_for_a_string_that_is_not_a_cards(self):
        card_source = need(self, core, '_card_source')
        t = self.cover('strings', LANDSCAPE)
        p = t['cover']['photo']
        cards, others = self.strings()
        for sizes in cards + ('50vw, 112px', '(min-width: 560px) 300px, 112px'):
            with self.subTest(sizes=sizes):
                self.assertTrue(card_source(t, p, t['url'], sizes).startswith('<source media="(max-width: 559.98px)" srcset="'), sizes)
                # the declared slot (CARD_PHONE_SIZES), not the string it was handed and not the 112 px that string ends with
                self.assertTrue(card_source(t, p, t['url'], sizes).endswith(' sizes="106px">'))
                self.assertEqual(card_source(t, p, t['url'], sizes).count('sizes="'), 1)
        for sizes in others:
            with self.subTest(sizes=sizes):
                self.assertEqual(card_source(t, p, t['url'], sizes), '')
                got = core.cover_img(t, t['url'], sizes)
                self.assertNotIn('<picture', got)
                self.assertNotIn('<source', got)
                self.assertNotIn('.th.', got)

    def test_the_media_the_slot_and_the_declared_size_come_from_the_three_constants(self):
        t = self.cover('constants', LANDSCAPE)
        p = t['cover']['photo']
        base = '../../trips/%s/photos/' % t['slug']
        three = 'srcset="%s01.th.webp 427w, %s01.sm.webp 800w, %s01.webp 1600w"' % (base, base, base)
        # CARD_PHONE_SLOT decides which strings get a source (the ones that end with it) and is not what the source says;
        # CARD_PHONE_SIZES is what the source says and decides nothing else; CARD_PHONE_MEDIA is where it applies
        with mock.patch.object(core, 'CARD_PHONE_MEDIA', '(max-width: 479.98px)'), mock.patch.object(core, 'CARD_PHONE_SLOT', '96px'):
            self.assertEqual(core._card_source(t, p, t['url'], self.CARD), '')                       # no longer ends with the slot
            self.assertEqual(core._card_source(t, p, t['url'], '(min-width: 480px) 300px, 96px'),
                             '<source media="(max-width: 479.98px)" %s sizes="106px">' % three)
            with mock.patch.object(core, 'CARD_PHONE_SIZES', '90px'):
                self.assertEqual(core._card_source(t, p, t['url'], '(min-width: 480px) 300px, 96px'),
                                 '<source media="(max-width: 479.98px)" %s sizes="90px">' % three)
        with mock.patch.object(core, 'CARD_PHONE_SIZES', '90px'):
            self.assertEqual(core._card_source(t, p, t['url'], self.CARD), '<source media="(max-width: 559.98px)" %s sizes="90px">' % three)
            self.assertEqual(core._card_source(t, p, t['url'], '(min-width: 560px) 50vw, 90px'), '')      # a string that ends with 90 px is no card's
            self.assertEqual(core._card_source(t, p, t['url'], '(min-width: 560px) 50vw, 106px'), '')
        self.assertEqual(core._card_source(t, p, t['url'], self.CARD), '<source media="(max-width: 559.98px)" %s sizes="106px">' % three)
        self.assertEqual(core._card_source(t, p, t['url'], '(min-width: 560px) 50vw, 106px'), '')         # nor is one that ends with 106 px

    def test_at_106_px_a_3x_phone_takes_the_320_px_copy_of_a_portrait_and_a_square_cover(self):
        # contract-phase5.md section 5, as a browser does it (pick_candidate: the first candidate at least
        # slot x DPR wide, else the largest), over the candidates _card_source really writes for each shape
        pick = pick_candidate
        declared, real = int(core.CARD_PHONE_SIZES[:-2]), int(core.CARD_PHONE_SLOT[:-2])
        self.assertEqual((declared, real), (106, 112))
        widths = {}
        for k, (name, size) in enumerate((('landscape', LANDSCAPE), ('portrait', PORTRAIT), ('square', (1000, 1000)))):
            t = self.cover('pick-' + name, size, date='2025-06-%02d' % (k + 1))
            source = Doc(core._card_source(t, t['cover']['photo'], t['url'], self.CARD)).find('source')
            self.assertEqual(source['sizes'], '106px')
            widths[name] = tuple(int(w) for w in re.findall(r' (\d+)w', source['srcset']))
        self.assertEqual(widths, {'landscape': (427, 800, 1600), 'portrait': (320, 600, 1200), 'square': (320, 800, 1000)})
        # at 106 px a 3x screen wants 318 px: the 320 px copy of a portrait or square cover, the 427 px copy of a landscape
        self.assertEqual(declared * 3, 318)
        self.assertEqual({name: pick(w, declared, 3) for name, w in widths.items()}, {'landscape': 427, 'portrait': 320, 'square': 320})
        # at the real 112 px it wanted 336 px and stepped past 320w: the 600 px copy of the portrait, the 800 px one of
        # the square (the contract's measurement on a region page's first Featured card: 154 KB where 42 KB do)
        self.assertEqual(real * 3, 336)
        self.assertEqual({name: pick(w, real, 3) for name, w in widths.items()}, {'landscape': 427, 'portrait': 600, 'square': 800})
        # at 1x and 2x, and at every density up to 2.75x, the choice is the same as before for every shape: the .th copy
        for dpr in (1, 1.25, 1.5, 2, 2.25, 2.5, 2.625, 2.75):
            for name, w in widths.items():
                with self.subTest(dpr=dpr, shape=name):
                    self.assertEqual(pick(w, declared, dpr), pick(w, real, dpr))
                    self.assertEqual(pick(w, declared, dpr), w[0])
        # a landscape cover is served by its 427 px copy at either declaration on every phone up to 3.75x
        for dpr in (3, 3.5, 3.75):
            self.assertEqual((pick(widths['landscape'], declared, dpr), pick(widths['landscape'], real, dpr)), (427, 427))
        # past 3x a portrait or square cover goes to the next copy at either declaration, as before
        for name in ('portrait', 'square'):
            self.assertEqual([pick(widths[name], declared, dpr) for dpr in (3.5, 3.75)], [pick(widths[name], real, dpr) for dpr in (3.5, 3.75)])
            self.assertEqual(pick(widths[name], declared, 3.5), widths[name][1])
        # 106 is the widest whole number of px that does it: three times it is within the copy's 320 px short edge, and
        # one px more is not
        self.assertEqual(declared, core.THUMB_EDGE // 3)
        self.assertLessEqual(3 * declared, core.THUMB_EDGE)
        self.assertGreater(3 * (declared + 1), core.THUMB_EDGE)
        self.assertEqual(pick(widths['portrait'], declared + 1, 3), 600)
        self.assertEqual(pick(widths['square'], declared + 1, 3), 800)

    def test_cover_img_wraps_a_card_cover_and_leaves_the_img_as_it_was(self):
        # for each card string: <picture class="cover-pic"> + the source + the <img>, and that <img> is character for
        # character what cover_img gives for the same report before its .th file exists
        cards, _others = self.strings()
        for k, (name, size) in enumerate((('landscape', LANDSCAPE), ('portrait', PORTRAIT), ('panorama', (3810, 1600)))):
            before = self.cover('wrap-' + name, size, th=False, date='2025-06-%02d' % (k + 1))
            plain = {(sizes, here): core.cover_img(before, here, sizes) for sizes in cards for here in (before['url'], 'trips/', '')}
            helpers.touch(os.path.join(self.tmp, before['slug'], 'photos', '01.th.webp'))
            self.load_site()
            t = self.by[before['slug']]
            self.assertEqual(t['cover']['photo']['th'], 'photos/01.th.webp')
            for (sizes, here), img in sorted(plain.items()):
                with self.subTest(name, sizes=sizes, here=here):
                    self.assertTrue(img.startswith('<img class="cover-img" src="') and img.endswith(' loading="lazy">') and img.count('<') == 1, img)
                    self.assertNotIn('.th.', img)
                    got = core.cover_img(t, here, sizes)
                    source = core._card_source(t, t['cover']['photo'], here, sizes)
                    self.assertTrue(source)
                    self.assertEqual(got, '<picture class="cover-pic">' + source + img + '</picture>')
                    self.assertEqual(unwrap(got), img)
                    doc = Doc(got)
                    self.assertEqual([n.tag for n in doc.root.elements()], ['picture'])
                    pic = doc.find('picture')
                    self.assertEqual((sorted(pic.attrs), pic.classes), (['class'], ['cover-pic']))
                    self.assertEqual([n.tag for n in pic.elements()], ['source', 'img'])           # the source first: a browser takes the first that matches
                    self.assertEqual(got.count('.th.'), 1)

    def test_a_lead_image_is_never_wrapped(self):
        # eager=True is the page's lead image (preloaded, fetchpriority high): the bare <img>, even at a card string
        t = self.cover('eager', LANDSCAPE)
        cards, others = self.strings()
        for sizes in cards + others[:4]:
            with self.subTest(sizes=sizes):
                got = core.cover_img(t, t['url'], sizes, eager=True)
                self.assertTrue(got.startswith('<img class="cover-img" src="'), got)
                self.assertTrue(got.endswith(' fetchpriority="high">'), got)
                self.assertEqual(got.count('<'), 1)
                self.assertNotIn('.th.', got)
                self.assertNotIn('loading', got)
                # the same <img> as the lazy one, but for how it loads
                lazy = unwrap(core.cover_img(t, t['url'], sizes))
                self.assertEqual(got.replace(' fetchpriority="high"', ' loading="lazy"'), lazy)
                # ... and its preload names what it names
                link_ = Doc(core.cover_preload(t, t['url'], sizes)).find('link')
                img = Doc(got).find('img')
                self.assertEqual((link_['href'], link_['imagesrcset'], link_['imagesizes']), (img['src'], img['srcset'], img['sizes']))
        self.assertIn('<picture class="cover-pic">', core.cover_img(t, t['url'], self.CARD, eager=False))

    def test_the_class_and_the_focal_point_stay_on_the_img(self):
        t = self.cover('focal', LANDSCAPE, cover_focal_x=30, cover_focal_y=62.5)
        got = core.cover_img(t, t['url'], self.CARD, cls='tcard-cover extra')
        doc = Doc(got)
        pic, img = doc.find('picture'), doc.find('img')
        self.assertEqual(pic.classes, ['cover-pic'])
        self.assertEqual(sorted(pic.attrs), ['class'])
        self.assertEqual(img.classes, ['cover-img', 'tcard-cover', 'extra'])
        self.assertEqual(img['style'], 'object-position:30% 62.5%')
        self.assertEqual((img['alt'], img['width'], img['height'], img['loading'], img['decoding']), ('Synthetic "photo" one', '1600', '1200', 'lazy', 'async'))
        self.assertEqual(sorted(doc.find('source').attrs), ['media', 'sizes', 'srcset'])
        self.assertTrue(got.endswith(' loading="lazy" style="object-position:30% 62.5%"></picture>'), got)
        self.assertIn('<img class="cover-img tcard-cover extra" src="', got)
        # the same <img> as without the wrapper: the bare one a full-width string gives, at the card's string
        bare = core.cover_img(t, t['url'], self.report.HERO_SIZES, cls='tcard-cover extra')
        self.assertTrue(bare.startswith('<img ') and bare.count('<') == 1)
        self.assertEqual(unwrap(got), bare.replace(HERO_SIZES, self.CARD))

    def test_a_trip_without_a_photo_has_neither(self):
        self.assertEqual(core.cover_img(self.by['syn-track'], 'trips/', self.CARD), '')
        self.assertEqual(core.cover_preload(self.by['syn-track'], 'trips/', self.CARD), '')

    def test_on_a_report_page_every_card_with_a_copy_is_wrapped_and_nothing_else_names_it(self):
        # 'More like this' on built pages: every card whose report has a .th copy is wrapped and its source names the
        # file that exists; the lead photo and its preload are not touched; no <img srcset> and no imagesrcset names a
        # .th file; and the pages are, wrapper apart, the pages of the same site without any .th file
        with_th = ['syn-story', 'syn-explicit', 'syn-one', 'syn-two-tall']
        for slug in STORY:
            for p in self.by[slug]['photos']:
                base, ext = os.path.splitext(p['file'])
                helpers.touch(os.path.join(self.tmp, slug, base + '.sm' + ext))
                if slug in with_th:
                    helpers.touch(os.path.join(self.tmp, slug, base + '.th' + ext))
        self.load_site()
        self.assertEqual({slug: bool(self.by[slug]['cover']['photo']['th']) for slug in STORY},
                         {slug: slug in with_th for slug in STORY})
        pages = {slug: self.page(slug).html for slug in SINGLE}
        wrapped = 0
        for slug, html_ in sorted(pages.items()):
            with self.subTest(slug):
                doc = Doc(html_)
                # nothing but a <source> names a .th file
                for img in doc.find_all('img'):
                    self.assertNotIn('.th.', (img['srcset'] or '') + (img['src'] or ''))
                for ln in doc.find_all('link'):
                    self.assertNotIn('.th.', (ln['imagesrcset'] or '') + (ln['href'] or ''))
                self.assertEqual(html_.count('.th.'), len(doc.find_all('source')))
                self.assertEqual(len(doc.find_all('picture')), len(doc.find_all('source')))
                for card in doc.find_all('li', cls='tcard'):
                    t = self.by[card['data-slug']]
                    pics = card.find_all('picture')
                    has = bool(t.get('cover') and t['cover']['photo']['th'])
                    self.assertEqual(len(pics), 1 if has else 0, card['data-slug'])
                    for pic in pics:
                        wrapped += 1
                        first = pic.find('source')['srcset'].split(', ')[0].split(' ')[0]
                        self.assertEqual(first, '../../%s%s' % (t['url'], t['cover']['photo']['th']))
                        self.assertTrue(os.path.isfile(os.path.join(self.tmp, t['slug'], t['cover']['photo']['th'])))
                        # the card's cover is core.cover_img at the card string, to the character
                        self.assertEqual(html_.count(core.cover_img(t, 'trips/%s/' % slug, core.RELATED_SIZES)), 1)
                # the lead photo (a story with a landscape cover) is the bare <img>, and the preload repeats it
                hero = doc.find('figure', cls='rep-hero')
                if hero is not None:
                    self.assertEqual(hero.find_all('picture'), [])
                    img = hero.find('img')
                    preloads = doc.find('head').find_all('link', attrs={'rel': 'preload', 'as': 'image'})
                    self.assertEqual([(ln['href'], ln['imagesrcset'], ln['imagesizes']) for ln in preloads], [(img['src'], img['srcset'], img['sizes'])])
        self.assertGreater(wrapped, 5)
        # the same site without any .th file: the same pages, wrapper apart
        for slug in with_th:
            for p in self.by[slug]['photos']:
                os.remove(os.path.join(self.tmp, slug, p['th']))
        self.load_site()
        for slug in SINGLE:
            with self.subTest(slug, th=False):
                bare = self.page(slug).html
                self.assertNotIn('<picture', bare)
                self.assertNotIn('.th.', bare)
                self.assertEqual(unwrap(pages[slug]), bare)


# ---------------------------------------------------------------- Phase 5: the links to a region's own page

DESERT = 'Synthetic Desert'            # a region on map/ without a region map: it has no page of its own
RS, DS = 'synthetic-range', 'synthetic-desert'


def legacy_region_cell(t, here):
    """The pagers' second cell as report.planned_pager and report.goal_pager wrote it at commit fb425ab (Phase 4),
    copied from those two function bodies, where it stood twice: [] or the one link to the region on map/."""
    reg = core.region_map_href(here, t.get('region'))
    if not reg:
        return []
    return ['<a class="next" href="%s"><span class="pager-t"><span class="t-label pager-l"><span>%s</span>%s</span>'
            '<span class="pager-n">Open the map</span></span></a>' % (reg, core.esc(t['region']), core.icon('arrow-right', 14))]


def legacy_goal_pager(t, here):
    """report.goal_pager as it was at commit fb425ab, copied line for line."""
    cells = ['<a class="prev" href="%s"><span class="pager-t"><span class="t-label pager-l">%s<span>Tick list</span></span>'
             '<span class="pager-n">Back to the tick list</span></span></a>' % (core.link(here, 'tick-list/'), core.icon('arrow-left', 14))]
    cells += legacy_region_cell(t, here)
    return '<nav class="pager wrap sec" aria-label="More goals">%s</nav>' % ''.join(cells)


def legacy_planned_pager(t, here, site):
    """report.planned_pager as it was at commit fb425ab, copied line for line."""
    act = t['activity']
    word = core.ACT[act][0]
    same = [x for x in site['trips'] if x['activity'] == act]
    counts = core.meta_items(core.count_items([x for x in same if x['kind'] != 'planned'], [x for x in same if x['kind'] == 'planned']))
    cells = ['<a class="prev" href="%s"><span class="pager-t"><span class="t-label pager-l">%s<span>%s</span></span>'
             '<span class="pager-n">All %s reports</span><span class="t-mono-s">%s</span></span></a>'
             % (core.link(here, core.section_url(act)), core.icon('arrow-left', 14), core.esc(word), core.esc(word.lower()), counts)]
    cells += legacy_region_cell(t, here)
    return '<nav class="pager wrap sec" aria-label="More %s">%s</nav>' % (core.esc(word.lower()), ''.join(cells))


class RegionLinkTests(ReportFixture):
    """contract-phase5.md section 2, on the pages report.py writes or shares its title block with: the region crumb of a
    report, a multi-day, a journal and a goal page, and the region cell of the two pagers (report.region_cell). The
    fixture's region gets a region map here (so core.region_pages gives it a page); a second region, on map/ without a
    region map, has none. With no page registered every link is what it was before the phase: the breadcrumb is
    written out by hand below, and the pagers are compared with copies of the old function bodies (legacy_goal_pager,
    legacy_planned_pager). REVISED in round 2: core.register_site records region pages only when it is handed a site
    meta, so this class registers its site with one (load_site below), as tools/build.py does; the fixture's own
    load_site registers without one, and every other class of this file therefore builds its pages as before."""

    meta = None                               # the site meta load_site registers with, once setUp has written it

    def setUp(self):
        helpers.keep_state(self)              # the region pages this class registers with core are gone afterwards
        super().setUp()
        meta = {'hash': '', 'maps': {'region-%s-%s' % (RS, size): {'w': 100, 'h': 80} for size in ('desktop', 'phone')},
                'regions': [REGION], 'all_regions': [REGION, DESERT]}
        patcher = mock.patch.object(core, '_SITE_META', [meta])
        patcher.start()
        self.addCleanup(patcher.stop)
        self.meta = meta
        self.multiday = load_module(self, 'sitegen.pages.multiday')
        self.series = load_module(self, 'sitegen.pages.series')
        mk = helpers.make_trip
        mk(self.tmp, 'syn-desert', title='Synthetic Desert Walk', activity='hike', date='2025-02-02', region=DESERT, track=True)
        mk(self.tmp, 'syn-desert-goal', title='Synthetic Desert Goal', activity='hike', kind='planned', region=DESERT)
        mk(self.tmp, 'syn-nowhere-goal', title='Synthetic Nowhere Goal', activity='hike', kind='planned', region='Synthetic Nowhere')
        mk(self.tmp, 'syn-regionless-goal', title='Synthetic Regionless Goal', activity='hike', kind='planned')
        self.load_site()

    def load_site(self):
        """The fixture's site, registered again with the site meta: the regions with a region map get their pages."""
        super().load_site()
        if self.meta is not None:
            core.register_site(self.site, self.meta)

    def html(self, slug):
        """The trip's page, built now by the module that owns its kind."""
        t = self.by[slug]
        if t['kind'] == 'multi-day':
            return self.multiday.page(t, self.site).html
        if t['kind'] == 'series':
            return self.series.page(t, self.site).html
        return self.report.page(t, self.site).html

    def crumbs(self, html_):
        nav = Doc(html_).by_id('main').find('nav', attrs={'aria-label': 'Breadcrumb'})
        return [(a.text(), a['href']) for a in nav.find_all('a')]

    def unregistered(self):
        core._REGION_PAGES.clear()            # core as it is before any site is registered (helpers.keep_state undoes it)

    # ------------------------------------------------------------ the fixture

    def test_the_fixture_has_a_region_with_a_page_and_one_without(self):
        self.assertEqual(core._REGION_PAGES, {REGION: RS})
        self.assertEqual(core.region_page_href('trips/syn-story/', REGION), '../../regions/synthetic-range/')
        self.assertIsNone(core.region_page_href('trips/syn-desert/', DESERT))
        self.assertEqual(core.region_map_href('trips/syn-desert/', DESERT), '../../map/#region-synthetic-desert')
        self.assertIsNone(core.region_map_href('trips/syn-nowhere-goal/', 'Synthetic Nowhere'))

    def test_a_test_of_this_class_leaves_no_region_page_registered(self):
        helpers.assert_puts_core_back(self, RegionLinkTests('test_the_fixture_has_a_region_with_a_page_and_one_without'))

    # ------------------------------------------------------------ the breadcrumb

    def test_the_region_crumb_opens_the_regions_own_page(self):
        want = {'syn-story': [('Reports', '../../'), ('Hiking', '../../hiking/'), (REGION, '../../regions/synthetic-range/')],
                'syn-tour': [('Reports', '../../'), ('Backcountry Ski', '../../ski/'), (REGION, '../../regions/synthetic-range/')],
                'syn-journal': [('Reports', '../../'), ('Hiking', '../../hiking/'), (REGION, '../../regions/synthetic-range/')],
                'syn-goal': [('Tick list', '../../tick-list/'), (REGION, '../../regions/synthetic-range/')]}
        for slug in sorted(want):
            with self.subTest(slug=slug):
                html_ = self.html(slug)
                self.assertEqual(self.crumbs(html_), want[slug])
                self.assertEqual(html_.count('<a href="../../regions/synthetic-range/">Synthetic Range</a>'), 1)
                self.assertNotIn('<a href="../../map/#region-synthetic-range">', html_)

    def test_a_region_without_a_page_keeps_its_crumb_to_the_map_page(self):
        self.assertEqual(self.crumbs(self.html('syn-desert')),
                         [('Reports', '../../'), ('Hiking', '../../hiking/'), (DESERT, '../../map/#region-synthetic-desert')])
        self.assertEqual(self.crumbs(self.html('syn-desert-goal')), [('Tick list', '../../tick-list/'), (DESERT, '../../map/#region-synthetic-desert')])
        self.assertNotIn('regions/', self.html('syn-desert'))
        self.assertNotIn('regions/', self.html('syn-desert-goal'))
        # a region that map/ has no anchor for, and no region: no region crumb, as before
        self.assertEqual(self.crumbs(self.html('syn-nowhere-goal')), [('Tick list', '../../tick-list/')])
        self.assertEqual(self.crumbs(self.html('syn-regionless-goal')), [('Tick list', '../../tick-list/')])

    def test_title_block_is_relative_to_the_page_it_is_on(self):
        nav = Doc(self.report.title_block(self.by['syn-story'], 'a/b/c/', '')).find('nav')
        self.assertEqual([a['href'] for a in nav.find_all('a')], ['../../../', '../../../hiking/', '../../../regions/synthetic-range/'])

    def test_with_no_site_registered_the_breadcrumb_is_the_old_one(self):
        self.unregistered()
        # written out by hand: the breadcrumb of a report page as Phase 4 left it
        self.assertIn('<nav class="crumbs" aria-label="Breadcrumb"><a href="../../">Reports</a><span aria-hidden="true">/</span>'
                      '<a href="../../hiking/">Hiking</a><span aria-hidden="true">/</span>'
                      '<a href="../../map/#region-synthetic-range">Synthetic Range</a></nav>', self.html('syn-story'))
        self.assertIn('<nav class="crumbs" aria-label="Breadcrumb"><a href="../../tick-list/">Tick list</a><span aria-hidden="true">/</span>'
                      '<a href="../../map/#region-synthetic-range">Synthetic Range</a></nav>', self.html('syn-goal'))
        for slug in ('syn-story', 'syn-tour', 'syn-journal', 'syn-goal', 'syn-desert', 'syn-desert-goal'):
            self.assertNotIn('regions/', self.html(slug), slug)

    def test_the_region_links_are_the_only_things_a_region_page_changes_on_a_report(self):
        # the crumb and, since Phase 12, the place line's region (ia-09) go to the region's page, and 'See on the <Region>
        # map' (gap4-03) to the report's row on it; without the page they go to map/ (the row there, for the last)
        with_page = {slug: self.html(slug) for slug in ('syn-story', 'syn-tour', 'syn-journal', 'syn-desert', 'syn-words', 'syn-undated')}
        self.unregistered()
        for slug, html_ in sorted(with_page.items()):
            with self.subTest(slug=slug):
                old = self.html(slug)
                if slug == 'syn-desert':
                    self.assertEqual(html_, old)                              # its region has no page: nothing differs
                    continue
                self.assertEqual(html_.count('href="../../regions/synthetic-range/"'), 2)      # the crumb, the place line
                t = self.by[slug]                 # the link sits in a drawn map's section, which a journal page has not
                self.assertEqual(html_.count('href="../../regions/synthetic-range/#arc-row-%s"' % slug),
                                 1 if (core.render_meta(t)['maps'] and t['kind'] != 'series') else 0)
                self.assertEqual(html_.replace('href="../../regions/synthetic-range/#arc-row-', 'href="../../map/#arc-row-')
                                 .replace('href="../../regions/synthetic-range/"', 'href="../../map/#region-synthetic-range"'), old)

    def test_a_page_built_before_registration_equals_one_that_never_has_a_region_page(self):
        # 'no site registered' and 'this region has no page' are one answer (None): every caller does what it did
        self.unregistered()
        plain = {slug: self.html(slug) for slug in ('syn-story', 'syn-tour', 'syn-goal')}
        core.register_site(self.site, self.meta)
        with mock.patch.object(core, 'region_page_href', lambda here, region: None):
            for slug in sorted(plain):
                self.assertEqual(self.html(slug), plain[slug], slug)

    def test_registered_without_a_site_meta_every_link_is_the_old_one(self):
        # REVISED in round 2: what ReportFixture.load_site and helpers.make_site do. The region map is in core's own copy
        # of the meta all the same; the region has no page, and the crumb and the pager cell are the ones of Phase 4
        slugs = ('syn-story', 'syn-tour', 'syn-journal', 'syn-goal', 'syn-desert', 'syn-desert-goal')
        with_page = {slug: self.html(slug) for slug in slugs}
        self.unregistered()
        never = {slug: self.html(slug) for slug in slugs}
        for register in (lambda: core.register_site(self.site), lambda: core.register_site(self.site, None), lambda: ReportFixture.load_site(self)):
            core.register_site(self.site, self.meta)
            self.assertEqual(core._REGION_PAGES, {REGION: RS})
            register()
            self.assertEqual(core._REGION_PAGES, {})
            self.assertIn('region-%s-desktop' % RS, core.site_meta()['maps'])
            for slug in slugs:
                self.assertEqual(self.html(slug), never[slug], slug)
                self.assertNotIn('regions/', self.html(slug), slug)
            self.assertEqual(self.report.region_cell(self.by['syn-goal'], 'trips/syn-goal/'), legacy_region_cell(self.by['syn-goal'], 'trips/syn-goal/'))
        self.assertIn('<a href="../../map/#region-synthetic-range">Synthetic Range</a></nav>', never['syn-story'])
        # handed the meta, the pages are the ones with the links again
        self.load_site()
        for slug in slugs:
            self.assertEqual(self.html(slug), with_page[slug], slug)
        self.assertNotEqual(with_page['syn-story'], never['syn-story'])
        self.assertEqual(with_page['syn-desert'], never['syn-desert'])

    def test_a_journal_and_a_report_without_a_track_link_to_the_page_that_lists_them(self):
        # REVISED in round 2: the page lists every listed trip whose region is the name (core.region_pages), so every
        # report that gets the crumb is on the page it leads to: the journal and a report without a track as well
        self.add('syn-notrack', track=False, body=WRITEUP)
        (name, slug, ts), = core.region_pages(self.site, self.meta)
        listed = {t['slug'] for t in ts}
        self.assertEqual((name, slug), (REGION, RS))
        for trip in ('syn-journal', 'syn-notrack', 'syn-tour', 'syn-story', 'syn-undated'):
            with self.subTest(slug=trip):
                self.assertIn(trip, listed)
                self.assertEqual(self.crumbs(self.html(trip))[-1], (REGION, '../../regions/synthetic-range/'))
        self.assertEqual((self.by['syn-journal']['kind'], core.has_track(self.by['syn-notrack'])), ('series', False))
        # a trip of another region is neither on the page nor linked to it
        self.assertNotIn('syn-desert', listed)
        self.assertNotIn('regions/', self.html('syn-desert'))

    # ------------------------------------------------------------ report.region_cell

    def test_region_cell_is_one_link_to_the_regions_page(self):
        cell = need(self, self.report, 'region_cell')
        got = cell(self.by['syn-goal'], 'trips/syn-goal/')
        # Phase 12 (gap4-03): a goal the region's list rows lands on its row; this one is no active goal, so on the page
        self.assertNotIn('syn-goal', core._LISTED[0])
        self.assertEqual(got, ['<a class="next" href="../../regions/synthetic-range/"><span class="pager-t"><span class="t-label pager-l">'
                               '<span>Synthetic Range</span>%s</span><span class="pager-n">All Synthetic Range reports</span></span></a>'
                               % core.icon('arrow-right', 14)])
        a = Doc(got[0]).find('a')
        self.assertEqual((a.classes, a['href']), (['next'], '../../regions/synthetic-range/'))
        self.assertEqual(a.find('span', cls='pager-l').text(), REGION)              # the label line stays the region name
        self.assertEqual(a.find('span', cls='pager-n').text(), 'All Synthetic Range reports')
        # any trip of the region, from any page
        self.assertEqual(Doc(cell(self.by['syn-story'], '')[0]).find('a')['href'], 'regions/synthetic-range/#arc-row-syn-story')

    def test_region_cell_for_a_region_without_a_page_is_the_old_cell(self):
        cell = need(self, self.report, 'region_cell')
        got = cell(self.by['syn-desert-goal'], 'trips/syn-desert-goal/')
        self.assertEqual(got, ['<a class="next" href="../../map/#arc-row-syn-desert-goal"><span class="pager-t"><span class="t-label pager-l">'
                               '<span>Synthetic Desert</span>%s</span><span class="pager-n">Open the map</span></span></a>'
                               % core.icon('arrow-right', 14)])
        # the old cell, landing on the goal's row in 'Not on a region map' instead of the region's heading
        self.assertEqual(got, [c.replace('#region-synthetic-desert', '#arc-row-syn-desert-goal')
                               for c in legacy_region_cell(self.by['syn-desert-goal'], 'trips/syn-desert-goal/')])

    def test_region_cell_is_empty_without_a_region_or_a_place_on_the_map_page(self):
        cell = need(self, self.report, 'region_cell')
        self.assertEqual(cell(self.by['syn-regionless-goal'], 'trips/syn-regionless-goal/'), [])
        self.assertEqual(cell(self.by['syn-nowhere-goal'], 'trips/syn-nowhere-goal/'), [])
        self.assertIsInstance(cell(self.by['syn-regionless-goal'], ''), list)

    def test_region_cell_escapes_the_region_name(self):
        cell = need(self, self.report, 'region_cell')
        name = "Synthetic O'Brien & <Peaks>"
        t = dict(self.by['syn-goal'], region=name)
        with mock.patch.dict(core._REGION_PAGES, {name: 'synthetic-obrien-peaks'}):
            (html_,) = cell(t, 'trips/syn-goal/')
        self.assertIn('<span>Synthetic O&#x27;Brien &amp; &lt;Peaks&gt;</span>', html_)
        self.assertIn('<span class="pager-n">All Synthetic O&#x27;Brien &amp; &lt;Peaks&gt; reports</span>', html_)
        self.assertEqual(Doc(html_).find('a')['href'], '../../regions/synthetic-obrien-peaks/')
        self.assertEqual(Doc(html_).find('span', cls='pager-n').text(), "All Synthetic O'Brien & <Peaks> reports")
        self.assertNotIn('<Peaks>', html_)

    def test_with_no_site_registered_region_cell_is_the_old_cell(self):
        cell = need(self, self.report, 'region_cell')
        self.unregistered()
        for slug in ('syn-goal', 'syn-story', 'syn-desert-goal', 'syn-nowhere-goal', 'syn-regionless-goal'):
            for here in ('trips/%s/' % slug, ''):
                # but for the row it lands on (Phase 12), when the region's list on map/ rows the trip
                old = legacy_region_cell(self.by[slug], here)
                if slug in core._LISTED[0]:
                    old = [re.sub(r'map/#region-[a-z-]+"', 'map/#arc-row-%s"' % slug, c) for c in old]
                self.assertEqual(cell(self.by[slug], here), old)
        self.assertIn('Open the map', cell(self.by['syn-goal'], '')[0])

    # ------------------------------------------------------------ the goal pager and the planned-route pager

    def test_the_goal_pagers_second_cell_is_the_region_cell(self):
        t, here = self.by['syn-goal'], 'trips/syn-goal/'
        nav = Doc(self.report.goal_pager(t, here)).find('nav', cls='pager')
        self.assertEqual([(a.classes, a['href']) for a in nav.find_all('a')],
                         [(['prev'], '../../tick-list/'), (['next'], '../../regions/synthetic-range/')])
        self.assertEqual(nav.find('a', cls='next').find('span', cls='pager-n').text(), 'All Synthetic Range reports')
        # the old pager with its second cell replaced, and nothing else
        old = legacy_goal_pager(t, here)
        self.assertEqual(self.report.goal_pager(t, here),
                         old.replace(legacy_region_cell(t, here)[0], self.report.region_cell(t, here)[0]))
        self.assertEqual(old.count(legacy_region_cell(t, here)[0]), 1)
        # ... and it is what the goal's page carries
        self.assertEqual(self.html('syn-goal').count(self.report.goal_pager(t, here)), 1)
        self.assertNotIn('Open the map', self.html('syn-goal'))

    def test_the_planned_pagers_second_cell_is_the_region_cell(self):
        t, here = self.by['syn-goal'], 'trips/syn-goal/'
        nav = Doc(self.report.planned_pager(t, here, self.site)).find('nav', cls='pager')
        self.assertEqual([(a.classes, a['href']) for a in nav.find_all('a')],
                         [(['prev'], '../../hiking/'), (['next'], '../../regions/synthetic-range/')])
        self.assertEqual(nav.find('a', cls='next').find('span', cls='pager-n').text(), 'All Synthetic Range reports')
        self.assertEqual(nav.find('a', cls='prev').find('span', cls='pager-n').text(), 'All hiking reports')
        old = legacy_planned_pager(t, here, self.site)
        self.assertEqual(self.report.planned_pager(t, here, self.site),
                         old.replace(legacy_region_cell(t, here)[0], self.report.region_cell(t, here)[0]))

    def test_a_region_without_a_page_keeps_both_pagers_as_they_were(self):
        # but for the row the region cell lands on (Phase 12): the goal's own row in 'Not on a region map'
        for slug in ('syn-desert-goal', 'syn-nowhere-goal', 'syn-regionless-goal'):
            t, here = self.by[slug], 'trips/%s/' % slug
            row = lambda x: x.replace('#region-synthetic-desert', '#arc-row-syn-desert-goal')  # noqa: E731
            with self.subTest(slug=slug):
                self.assertEqual(self.report.goal_pager(t, here), row(legacy_goal_pager(t, here)))
                self.assertEqual(self.report.planned_pager(t, here, self.site), row(legacy_planned_pager(t, here, self.site)))
        nav = Doc(self.html('syn-desert-goal')).find('nav', cls='pager')
        self.assertEqual([(a['href'], a.find('span', cls='pager-n').text()) for a in nav.find_all('a')],
                         [('../../tick-list/', 'Back to the tick list'), ('../../map/#arc-row-syn-desert-goal', 'Open the map')])
        self.assertEqual(len(Doc(self.html('syn-nowhere-goal')).find('nav', cls='pager').find_all('a')), 1)

    def test_with_no_region_page_both_pagers_are_the_old_ones_landing_on_the_row(self):
        self.unregistered()
        for slug in ('syn-goal', 'syn-desert-goal', 'syn-nowhere-goal', 'syn-regionless-goal'):
            t, here = self.by[slug], 'trips/%s/' % slug
            row = ((lambda x: re.sub(r'map/#region-[a-z-]+"', 'map/#arc-row-%s"' % slug, x)) if slug in core._LISTED[0]  # noqa: E731
                   else (lambda x: x))
            with self.subTest(slug=slug):
                self.assertEqual(self.report.goal_pager(t, here), row(legacy_goal_pager(t, here)))
                self.assertEqual(self.report.planned_pager(t, here, self.site), row(legacy_planned_pager(t, here, self.site)))
        self.assertIn('<span class="pager-n">Open the map</span>', self.html('syn-goal'))
        self.assertIn('href="../../map/#region-synthetic-range"><span class="pager-t">', self.html('syn-goal'))   # no row: no active goal

    def test_a_region_page_changes_two_links_on_a_goal_page_and_nothing_else(self):
        with_page = self.html('syn-goal')
        self.unregistered()
        old = self.html('syn-goal')
        # the crumb, the place line (Phase 12) and the pager cell (the goal is no active one, so no row to land on)
        self.assertEqual(with_page.count('href="../../regions/synthetic-range/"'), 3)
        self.assertEqual(with_page.replace('href="../../regions/synthetic-range/#arc-row-', 'href="../../map/#arc-row-')
                         .replace('href="../../regions/synthetic-range/"', 'href="../../map/#region-synthetic-range"')
                         .replace('<span class="pager-n">All Synthetic Range reports</span>', '<span class="pager-n">Open the map</span>'), old)

    def test_the_report_pager_between_reports_has_no_region_cell(self):
        # Newer / Older is a pager of reports: the phase does not touch it
        with_page = self.report.pager(self.by['syn-one'], 'trips/syn-one/', self.site)
        self.assertNotIn('regions/', with_page)
        self.assertNotIn(REGION, with_page)
        self.unregistered()
        self.assertEqual(self.report.pager(self.by['syn-one'], 'trips/syn-one/', self.site), with_page)


if __name__ == '__main__':
    unittest.main()
