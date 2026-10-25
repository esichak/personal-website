"""Phase 15 (gap9-09): what tools/render.py writes is what build.py and the page modules read.

The page modules read fixed render names from a trip's meta.json and render folder (map-wide, overview-col, day-01-phone,
spark-01, profile-col, tile, g112, ...) and from rendered/site/ (region-<slug>-desktop, ...). A rename on either side
passes every other test: the other page tests hand-write those names, and the built site then drops the map without a
word (core.map_block skips a name its meta does not have) or leaves '<!-- missing ... -->' (core.frag). Here render.py
draws a small synthetic site for real and the pages are built from what it drew:

  1. render.render_trip draws a single-day hike loop, a single-day out-and-back ride, a two-day tour (transfer_before on
     day 2, and a gap between the day tracks) and a three-day journal; render.render_site draws the region map of the
     three reports, with the journal's days 1-2 as its one part (region_days). Only geo.get_tile
     (render_fixtures.synth_tile) and render.fetch_osm (render_fixtures.OSM) are replaced, plus render.cwebp_version,
     so that meta['renderer'] reads the same everywhere; render.OUT, content.RENDERED (each trip's t['rendered']) and
     core.ROOT point into a temp folder. optimize_images runs as it is: WebP hillshades where cwebp is installed, PNGs
     where it is not, and the test takes either.
  2. The report, multi-day, journal, region and map pages are built from that folder (report, multiday, series,
     region and archive page modules), with core.map_block, core.frag and core._drawing watched: what the pages asked
     for is the contract. Every map name a page asked for is in the meta.json it read; no page holds '<!-- missing';
     every page of a trip (all of them have a track) and every region and map page has a <div class="mv">.
  3. Each render folder holds exactly meta.json, each map's .svg.html, hillshade and base layer, each chart, the
     drawings named in core.GLYPH_SIZES at the sizes it gives them, and the fragments the pages read; nothing else.
     Its meta.json has the keys core reads, and meta['renderer'] the version, Python, cwebp, date and OSM state.
  4. build.copy_trip_assets publishes exactly each map's hillshade (.png or .webp) and base layer under map/ and each
     drawing as <name>.svg, and build.copy_part_drawings the journal part's drawing.

Map names are taken from what the pages asked for and from meta.json, drawing names from core.GLYPH_SIZES, and a report
map's frame size from its meta entry, so a renderer change that adds a drawing or a map, or a taller frame, keeps this
test valid; one that renames something a page reads fails it. No byte or gzip size is asserted (base_gz_kb included): a
synthetic hill says nothing about real budgets.

It renders for about 75 s on the Mac's Python 3.9 (47 s on 3.12), so it runs where CI is set (GitHub Actions sets
CI=true) or with RENDER_TESTS=1:

  RENDER_TESTS=1 python3 -m unittest discover -s tests -p test_render_contract.py
"""
import contextlib
import copy
import importlib
import inspect
import io
import json
import os
import platform
import re
import sys
import tempfile
import unittest
import warnings
from datetime import date
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import geo  # noqa: E402
import mapkit  # noqa: E402
import renderkey  # noqa: E402
from sitegen import core  # noqa: E402

import gpx_fixtures as gf  # noqa: E402
import helpers  # noqa: E402
import render_fixtures as rf  # noqa: E402

GATE = bool(os.environ.get('CI') or os.environ.get('RENDER_TESTS'))
REGION = 'Synthetic Range'
REGION_SLUG = content.slugify(REGION)
SYNTH_CWEBP = 'WebP Encoder version 0.0.0 (synthetic, test_render_contract)'
PAGE_MODULES = ('report', 'multiday', 'series', 'region', 'archive')
# core.card_tile shows the 'card' drawing and falls back to the 'tile': a trip may have either; every other drawing in
# core.GLYPH_SIZES has no stand-in, so each trip must have it
DRAWING_FALLBACK = {'card': 'tile'}
# what the renderer records about itself (gap9-05), which tools/lib/checks.py compares across folders
RENDERER_KEYS = {'version', 'python', 'cwebp', 'date', 'osm'}

tearDownModule = helpers.no_region_pages_left


def _stats(pts):
    eles = [p[2] for p in pts]
    gain = sum(max(0.0, b - a) for a, b in zip(eles, eles[1:]))
    return {'distance_km': round(gf.poly_km(pts), 2), 'gain_m': int(round(gain)), 'high_m': int(round(max(eles))),
            'low_m': int(round(min(eles)))}


def _files(folder):
    """Every file under `folder`, as paths relative to it ('meta.json', 'days/001-g64.svg.html')."""
    out = set()
    for d, _, names in os.walk(folder):
        out.update(os.path.relpath(os.path.join(d, n), folder) for n in names)
    return out


def _svg_size(path):
    """(width, height) of the root <svg> of a fragment."""
    with open(path, encoding='utf-8') as fh:
        head = fh.read(400)
    m = re.match(r'\s*<svg width="(\d+)" height="(\d+)"', head)
    return (int(m.group(1)), int(m.group(2))) if m else None


@unittest.skipUnless(GATE, 'draws a synthetic site with tools/render.py (about a minute): runs on CI, or with RENDER_TESTS=1')
class RenderContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.render = importlib.import_module('render')
        cls.build_mod = importlib.import_module('build')
        snap = helpers.snapshot(core)                        # whatever the page builds register with core goes after
        cls.addClassCleanup(helpers.restore, snap)
        stack = contextlib.ExitStack()
        cls.addClassCleanup(stack.close)
        tmp = stack.enter_context(tempfile.TemporaryDirectory())
        cls.tmp = tmp
        cls.trips_dir = os.path.join(tmp, 'content', 'trips')
        cls.rendered = os.path.join(tmp, 'rendered')
        cls.site_out = os.path.join(tmp, '_site')
        os.makedirs(cls.trips_dir)
        r = cls.render
        for target, name, value in (
                (geo, 'get_tile', rf.synth_tile),
                (r, 'fetch_osm', lambda bbox, detail, pooled=True: copy.deepcopy(rf.OSM)),
                (r, 'cwebp_version', lambda: SYNTH_CWEBP),
                (r, 'OUT', cls.rendered),
                (content, 'RENDERED', cls.rendered),
                (core, 'ROOT', tmp),
                (core, '_SITE_META', []),
                (core, '_DROP_WARNED', set()),
                (mapkit, 'FRAG', mapkit.FRAG),                # render.set_out moves both: put back afterwards
                (mapkit, 'MAPPNG', mapkit.MAPPNG),
                (cls.build_mod, 'OUT', cls.site_out)):
            stack.enter_context(mock.patch.object(target, name, value))
        for name in ('overpass', 'osm_layers'):              # every OpenStreetMap answer is the fixture's: nothing fetches
            stack.enter_context(mock.patch.object(geo, name, side_effect=AssertionError('geo.%s called offline' % name)))
        stack.enter_context(mock.patch.dict(os.environ))
        os.environ.pop('REUSE_PNG', None)
        stack.enter_context(mock.patch.dict(mapkit.LAST_OSM))
        cls.write_trips()
        cls.trips = helpers.load_dir(cls.trips_dir)
        cls.by = {t['slug']: t for t in cls.trips}
        cls.days = {date.today().isoformat()}             # the day meta['renderer'] records (a run may pass midnight)
        with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            warnings.simplefilter('ignore', ResourceWarning)  # mapkit leaves some files to the collector
            cls.drew = {t['slug']: r.render_trip(t) for t in cls.trips}
            cls.drew_site = r.render_site(cls.trips)
            cls.days.add(date.today().isoformat())
            cls.metas = {t['slug']: cls.read_json(os.path.join(t['rendered'], 'meta.json')) for t in cls.trips}
            cls.site_meta = cls.read_json(os.path.join(cls.rendered, 'site', 'meta.json'))
            cls.build_pages(stack)
            for t in cls.trips:
                cls.build_mod.copy_trip_assets(t)
            with mock.patch.object(cls.build_mod, 'ROOT', tmp):
                cls.part_drawings = cls.build_mod.copy_part_drawings()

    # ---------------------------------------------------------------- the synthetic site

    @classmethod
    def write_trips(cls):
        mk = helpers.make_trip
        loop = mk(cls.trips_dir, 'syn-c-loop', track=True, title='Synthetic Loop', activity='hike', date='2026-08-01',
                  region=REGION, place='Synthetic Basin', route_shape='loop', stats=_stats(rf.LOOP_PTS),
                  map={'peaks': ['Quillon Peak']})
        ride = mk(cls.trips_dir, 'syn-c-ride', track=True, title='Synthetic Ride', activity='mtb', date='2026-07-01',
                  region=REGION, place='Synthetic Ridge', route_shape='out-and-back', stats=_stats(rf.OUT_BACK_PTS))
        for folder, text in ((loop, rf.LOOP_GPX), (ride, rf.OUT_BACK_GPX)):
            cls.write(os.path.join(folder, 'track.gpx'), text)
        tour = mk(cls.trips_dir, 'syn-c-tour', title='Synthetic Tour', activity='hike', kind='multi-day', date='2026-06-01',
                  end_date='2026-06-02', region=REGION, place='Synthetic Hut',
                  days=[{'title': 'Synthetic Day One', 'date': '2026-06-01', 'stats': _stats(rf.TOUR_DAY_PTS[0])},
                        {'title': 'Synthetic Day Two', 'date': '2026-06-02', 'transfer_before': True,
                         'stats': _stats(rf.TOUR_DAY_PTS[1])}])
        for i, text in enumerate(rf.TOUR_DAY_GPX):
            cls.write(os.path.join(tour, 'days', '%02d.gpx' % (i + 1)), text)
        journal = mk(cls.trips_dir, 'syn-c-journal', title='Synthetic Journal', activity='hike', kind='series',
                     date='2024-05-01', end_date='2024-05-03', region='Synthetic Trail', place='Synthetic start to synthetic end',
                     route_shape='point-to-point', region_days={REGION: '1-2'},
                     days=[{'id': '%03d' % (i + 1), 'date': '2024-05-%02d' % (i + 1), 'stats': _stats(pts)}
                           for i, pts in enumerate(rf.JOURNAL_DAY_PTS)])
        for i, text in enumerate(rf.JOURNAL_DAY_GPX):
            cls.write(os.path.join(journal, 'days', '%03d.gpx' % (i + 1)), text)

    @staticmethod
    def write(path, text):
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)

    @staticmethod
    def read_json(path):
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)

    @classmethod
    def build_pages(cls, stack):
        """Build the page modules from the rendered folder as build.py does, watching what they ask the renders for."""
        cls.asked = {'frag': set(), 'maps': [], 'drawings': []}
        real_frag, real_map_block, real_drawing = core.frag, core.map_block, core._drawing
        sig = inspect.signature(real_map_block)

        def frag(path, *a, **k):
            cls.asked['frag'].add(os.path.abspath(path))
            return real_frag(path, *a, **k)

        def map_block(*a, **k):
            b = sig.bind(*a, **k)
            t, site_maps = b.arguments['t'], b.arguments.get('site_maps', False)
            cls.asked['maps'].append(('site' if site_maps else t['slug'], [n for n, _ in b.arguments['variants']]))
            return real_map_block(*a, **k)

        def drawing(t, here, name, *a, **k):
            cls.asked['drawings'].append((t['slug'], name))
            return real_drawing(t, here, name, *a, **k)
        for name, fn in (('frag', frag), ('map_block', map_block), ('_drawing', drawing)):
            stack.enter_context(mock.patch.object(core, name, fn))
        core._SITE_META[:] = [cls.site_meta]
        site = cls.build_mod.site_of(cls.trips)
        site.update(featured=[], region_maps=None, about=None, region_intros={}, author=None)
        core.register_site(site, cls.site_meta)
        cls.pages = {}
        for name in PAGE_MODULES:
            mod = importlib.import_module('sitegen.pages.' + name)
            cls.pages[name] = {p.url: p.html for p in mod.build(site)}

    # ---------------------------------------------------------------- what render.py drew

    def test_every_trip_and_the_site_maps_were_drawn(self):
        self.assertEqual(self.drew, {t['slug']: True for t in self.trips})
        self.assertIs(self.drew_site, True)
        self.assertEqual(self.site_meta['regions'], [REGION])
        self.assertEqual(self.site_meta['all_regions'], [REGION])   # a journal belongs to no region's group (site_jobs)

    def test_each_trip_folder_holds_exactly_its_maps_charts_drawings_and_the_fragments_the_pages_read(self):
        for t in self.trips:
            with self.subTest(t['slug']):
                meta, folder = self.metas[t['slug']], t['rendered']
                want = {'meta.json'}
                for name, m in meta['maps'].items():
                    want.add(name + '.svg.html')
                    want.update(f for f in (m.get('png'), m.get('base')) if f)
                want.update(name + '.svg.html' for name in meta['charts'])
                want.update(name + '.svg.html' for name in core.GLYPH_SIZES if os.path.exists(os.path.join(folder, name + '.svg.html')))
                want.update(os.path.relpath(p, folder) for p in self.asked['frag'] if p.startswith(folder + os.sep))
                self.assertEqual(sorted(_files(folder) - want), [], 'drawn, but no page reads it')
                self.assertEqual(sorted(want - _files(folder)), [], 'read or listed in meta.json, but not drawn')

    def test_each_trip_has_every_drawing_of_core_glyph_sizes_at_its_size(self):
        for t in self.trips:
            for name, size in core.GLYPH_SIZES.items():
                with self.subTest(t['slug'], drawing=name):
                    p = core.rendered(t, name + '.svg.html')
                    if not os.path.exists(p) and name in DRAWING_FALLBACK:
                        p = core.rendered(t, DRAWING_FALLBACK[name] + '.svg.html')
                        size = core.GLYPH_SIZES[DRAWING_FALLBACK[name]]
                    self.assertTrue(os.path.exists(p), '%s has no %s drawing' % (t['slug'], name))
                    self.assertEqual(_svg_size(p), size)

    def test_each_trip_meta_has_the_keys_core_reads(self):
        for t in self.trips:
            with self.subTest(t['slug']):
                meta = self.metas[t['slug']]
                self.assertTrue({'hash', 'slug', 'kind', 'maps', 'charts', 'start', 'end', 'bbox', 'renderer'} <= set(meta), sorted(meta))
                self.assertEqual((meta['slug'], meta['kind']), (t['slug'], t['kind']))
                self.assertEqual(meta['hash'], renderkey.trip_inputs(t))   # up to date: the next run draws nothing
                self.assertNotIn('osm_failed', meta)
                self.assertTrue(meta['maps'])
                for name, m in meta['maps'].items():
                    # core.map_block: the frame's size, the hillshade and the base layer (a taller frame is fine)
                    self.assertTrue({'w', 'h', 'png', 'base'} <= set(m), (name, sorted(m)))
                    self.assertTrue(isinstance(m['w'], int) and isinstance(m['h'], int) and m['w'] > 0 and m['h'] > 0, (name, m))
                    self.assertTrue(m['png'].endswith(('.png', '.webp')), (name, m['png']))
                    # every map draws a base layer (contours, water, roads) but a journal's overview, which has neither
                    self.assertEqual(m['base'], None if t['kind'] == 'series' else name + '.base.svg', name)
                    self.assertEqual(_svg_size(core.rendered(t, name + '.svg.html')), (m['w'], m['h']), name)
                for name, c in meta['charts'].items():
                    self.assertTrue({'w', 'kind'} <= set(c), (name, sorted(c)))
                self.assertEqual(len(meta['bbox']), 4)
                self.assert_renderer(meta['renderer'])

    def test_the_report_maps_carry_what_the_report_page_reads(self):
        for slug in ('syn-c-loop', 'syn-c-ride'):
            with self.subTest(slug):
                maps = self.metas[slug]['maps']
                for name in ('map-col', 'map-phone'):
                    self.assertIn(name, maps)
                    self.assertTrue({'interval_ft', 'outbound_only'} <= set(maps[name]), (name, sorted(maps[name])))
        self.assertIs(self.metas['syn-c-ride']['maps']['map-col']['outbound_only'], True)
        self.assertIs(self.metas['syn-c-loop']['maps']['map-col']['outbound_only'], False)

    def test_the_site_folder_and_meta(self):
        meta = self.site_meta
        site = os.path.join(self.rendered, 'site')
        self.assertTrue({'hash', 'maps', 'regions', 'all_regions', 'renderer'} <= set(meta), sorted(meta))
        self.assertIsNotNone(meta['hash'])
        self.assert_renderer(meta['renderer'])
        region_maps = sorted(n for n in meta['maps'] if n.startswith('region-%s-' % REGION_SLUG))
        self.assertEqual(region_maps, ['region-%s-desktop' % REGION_SLUG, 'region-%s-phone' % REGION_SLUG])
        want = {'meta.json'}
        for name, m in meta['maps'].items():
            with self.subTest(name):
                self.assertTrue({'w', 'h', 'png', 'base', 'region', 'trips', 'clusters'} <= set(m), sorted(m))
                self.assertTrue(m['png'].endswith(('.png', '.webp')), m['png'])
                self.assertEqual(m['base'], name + '.base.svg')
                self.assertEqual(m['region'], REGION)
                self.assertEqual(sorted(m['trips']), ['syn-c-loop', 'syn-c-ride', 'syn-c-tour'])
                want.update([name + '.svg.html', m['png'], m['base']])
                if name.startswith('region-'):
                    self.assertEqual(len(m['journals']), 1)
                    part = m['journals'][0]
                    self.assertTrue({'slug', 'key', 'title', 'days', 'glyph'} <= set(part), sorted(part))
                    self.assertEqual((part['slug'], part['days']), ('syn-c-journal', ['001', '002']))
                    want.add(part['glyph'] + '.svg.html')
        self.assertEqual(sorted(_files(site) ^ want), [])

    def assert_renderer(self, rec):
        self.assertEqual(set(rec), RENDERER_KEYS)
        self.assertEqual(rec['version'], renderkey.VERSION)
        self.assertEqual(rec['python'], platform.python_version())
        self.assertEqual(rec['cwebp'], SYNTH_CWEBP)
        self.assertIn(rec['date'], self.days)
        self.assertEqual(rec['osm'], 'cached')           # fetch_osm answered every map; nothing fetched, nothing missing

    # ---------------------------------------------------------------- what the pages read

    def test_every_map_a_page_asked_for_was_drawn(self):
        asked = {}
        for who, names in self.asked['maps']:
            asked.setdefault(who, set()).update(names)
        self.assertEqual(sorted(asked), sorted(['site'] + [t['slug'] for t in self.trips]))
        for who, names in sorted(asked.items()):
            with self.subTest(who):
                drawn = self.site_meta['maps'] if who == 'site' else self.metas[who]['maps']
                self.assertEqual(sorted(names - set(drawn)), [], 'asked for by a page, not in its meta.json')

    def test_every_drawing_a_page_asked_for_was_drawn(self):
        for slug, name in sorted(set(self.asked['drawings'])):
            with self.subTest(slug, drawing=name):
                self.assertIn(name, core.GLYPH_SIZES)
                t = self.by[slug]
                there = os.path.exists(core.rendered(t, name + '.svg.html'))
                if not there and name in DRAWING_FALLBACK:
                    there = os.path.exists(core.rendered(t, DRAWING_FALLBACK[name] + '.svg.html'))
                self.assertTrue(there)

    def test_every_trip_page_has_its_map_and_no_page_has_a_missing_fragment(self):
        seen = set()
        for mod, pages in sorted(self.pages.items()):
            for url, page in sorted(pages.items()):
                with self.subTest(url):
                    self.assertNotIn('<!-- missing', page)
                    slug = next((t['slug'] for t in self.trips if url.startswith(t['url'])), None)
                    if slug or mod in ('region', 'archive'):
                        self.assertIn('<div class="mv', page)
                    if slug:
                        seen.add(slug)
        self.assertEqual(sorted(seen), sorted(self.by))
        self.assertIn('regions/%s/' % REGION_SLUG, self.pages['region'])
        self.assertIn('map/', self.pages['archive'])

    # ---------------------------------------------------------------- what build.py publishes

    def test_copy_trip_assets_publishes_exactly_the_hillshades_base_layers_and_drawings(self):
        for t in self.trips:
            with self.subTest(t['slug']):
                out = os.path.join(self.site_out, 'trips', t['slug'])
                meta = self.metas[t['slug']]
                published = _files(out)
                want_maps = {os.path.join('map', f) for m in meta['maps'].values() for f in (m['png'], m['base']) if f}
                want_drawings = {name + '.svg' for name in core.GLYPH_SIZES if os.path.exists(core.rendered(t, name + '.svg.html'))}
                self.assertEqual(sorted(f for f in published if f.startswith('map' + os.sep)), sorted(want_maps))
                self.assertEqual(sorted(f for f in published if f.endswith('.svg') and os.sep not in f), sorted(want_drawings))
                self.assertEqual(sorted(f for f in published if not f.startswith('map' + os.sep) and not f.endswith(('.svg', '.gpx'))), [])

    def test_copy_part_drawings_publishes_the_journal_part_drawing(self):
        glyphs = [p['glyph'] + '.svg' for m in self.site_meta['maps'].values() for p in m.get('journals') or []]
        self.assertTrue(glyphs)
        self.assertEqual(sorted(self.part_drawings), sorted(set(glyphs)))
        for g in glyphs:
            self.assertTrue(os.path.exists(os.path.join(self.site_out, 'assets', 'maps', g)), g)


if __name__ == '__main__':
    unittest.main()
