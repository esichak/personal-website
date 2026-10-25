"""Phase 15 (gap9-01): the renderer, run offline against golden files.

tools/lib/mapkit.py draws every map, profile, tile, glyph and sparkline on the site, and render.py runs it only on the
author's Mac. Here it runs in full with no network: geo.get_tile is replaced by tests/render_fixtures.synth_tile (a
synthetic hill, decoded as a Terrarium tile would be), each map gets render_fixtures.OSM as its OpenStreetMap answer
(spec['osm_data'], as render_single hands it over), and mapkit.FRAG / mapkit.MAPPNG point at a temp folder. Three cases,
each with its golden files under tests/golden/render/<case>/:

  hike-loop             a loop over the hill: map-wide, map-col and map-phone from the specs render_single builds out of
                        render.REPORT and render.SMALL, the three profiles single_charts draws, the card tile, both glyphs
                        and two sparklines. Only map-phone draws its hillshade (hillshade=False elsewhere, to keep the
                        module quick); its PNG is compared by width, height and a sha1 of the decoded pixels.
  mtb-out-and-back      an out-and-back ride: is_out_and_back, mile discs on the way out only (meta outbound_only), the
                        phone map's outbound-only line, and chevrons, which an out-and-back never gets and a one-way leg does
  planned-two-segments  a planned route of two segments (gpxroute.as_tracks of gpx_fixtures.JUMP), drawn as two parts on
                        the maps, the tile and the glyphs

The .svg.html and .base.svg files are compared as exact text (a failure prints a unified diff of the SVG split after
every '>'), each .meta.json with its floats rounded to 2 places and without base_gz_kb (the gzip size measures the
host's zlib, and the .base.svg it is measured from is compared exactly), and a PNG by width, height and pixel sha1
(geo.png_read), never by its bytes; a WebP never appears, cwebp is not involved. A renderer change ships with goldens
regenerated on purpose and the diff reviewed:

  UPDATE_GOLDEN=1 python3 -m unittest discover -s tests -p test_mapkit_golden.py

File names with a space (iCloud conflict copies) and dot files in a golden folder are ignored.

gap9-08 (TileCache below): geo.get_tile keeps a decoded tile as array('d') in an LRU of geo.TILE_CACHE_MAX tiles.
DEM.sample reads the same values from an array as from a list, a Terrarium PNG decodes to exactly synth_tile's values,
and the oldest tile is the one dropped; the hike loop's hillshade PNG above pins the drawn pixels.
"""
import array
import contextlib
import copy
import difflib
import hashlib
import importlib
import io
import json
import math
import os
import struct
import sys
import tempfile
import unittest
import warnings
import zlib
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import geo  # noqa: E402
import gpxroute  # noqa: E402
import mapkit  # noqa: E402

import gpx_fixtures as gf  # noqa: E402
import render_fixtures as rf  # noqa: E402

GOLDEN = os.path.join(ROOT, 'tests', 'golden', 'render')
UPDATE = os.environ.get('UPDATE_GOLDEN') == '1'
DIFF_LINES = 60   # lines of each file's diff shown in a failure


def single_specs(render, t, drawn, planned=False):
    """The three map specs render.render_single builds for a single-day trip (tools/render.py), from render.REPORT and
    render.SMALL, with each spec's tracks as render_single sets them."""
    act, mo = t['activity'], t['map']
    peaks = mo.get('peaks') or []
    small = render.extent_m(drawn) < 3000
    flat = render.is_flat(t)
    base = {}
    if small:
        base.update(min_extent_m=1000 if flat else 1400, hs_zoom=15)
    if flat:
        base.update(gpsmax=False, miles=False, water_labels=6)
    if planned:
        base.update(gpsmax=False, miles=False, chevrons=False, startend=True)
    aria = render.aria_for(t)
    REPORT, SMALL, water_labels = render.REPORT, render.SMALL, render.water_labels
    specs = [
        dict(REPORT, **base, name='map-wide', w=1440, h=640, skin=(act == 'ski'), peaks_max=2, priority_peaks=peaks,
             places_allow=mo.get('places'), extra_water_labels=water_labels(mo.get('water_labels'), 1440, 640), aria=aria),
        dict(REPORT, **base, name='map-col', w=718, h=400, png_scale=2.0, skin=(act == 'ski'), peaks_max=2, priority_peaks=peaks,
             places_allow=mo.get('places'), extra_water_labels=water_labels(mo.get('water_labels'), 718, 400), aria=aria),
        dict(SMALL, **{k: v for k, v in base.items() if k not in ('water_labels',)}, name='map-phone', w=390, h=336, scale_corner='bl',
             priority_peaks=peaks, reserve=[(0, 0, 60, 60), (390 - 208, 336 - 36, 390, 336)], pad_bottom_px=40, aria=aria),
    ]
    style = 'planned' if planned else 'route'
    for s in specs:
        s['tracks'] = [{'track': x, 'style': style, 'width': 3} for x in drawn]
    return specs


def _rounded(v):
    if isinstance(v, float):
        r = round(v, 2)
        return 0.0 if r == 0 else r   # never '-0.0'
    if isinstance(v, list):
        return [_rounded(x) for x in v]
    if isinstance(v, dict):
        return {k: _rounded(x) for k, x in v.items()}
    return v


def _read(path):
    with open(path, encoding='utf-8', newline='') as fh:
        return fh.read()


def _json_text(obj):
    return json.dumps(obj, indent=1, sort_keys=True) + '\n'


def collect(folder):
    """{golden file name: text} for everything the renderer wrote into `folder`."""
    got = {}
    for f in sorted(os.listdir(folder)):
        p = os.path.join(folder, f)
        if f.endswith('.svg.html') or f.endswith('.base.svg'):
            got[f] = _read(p)
        elif f.endswith('.meta.json'):
            with open(p, encoding='utf-8') as fh:
                meta = json.load(fh)
            if isinstance(meta, dict):
                meta.pop('base_gz_kb', None)
            got[f] = _json_text(_rounded(meta))
        elif f.endswith('.png'):
            w, h, _, px = geo.png_read(p)
            got[f[:-len('.png')] + '.png.json'] = _json_text({'width': w, 'height': h, 'sha1': hashlib.sha1(bytes(px)).hexdigest()})
        else:
            raise AssertionError('unexpected render output %s (the golden test never involves cwebp)' % f)
    return got


def _ours(name):
    """A golden file name, not an iCloud conflict copy ('map-wide 2.svg.html') or a dot file."""
    return ' ' not in name and not name.startswith('.')


def _diff(name, want, got):
    split = name.endswith('.svg.html') or name.endswith('.base.svg')
    a = (want.replace('>', '>\n') if split else want).splitlines()
    b = (got.replace('>', '>\n') if split else got).splitlines()
    lines = list(difflib.unified_diff(a, b, 'golden/' + name, 'rendered/' + name, n=1, lineterm=''))
    more = len(lines) - DIFF_LINES
    return '\n'.join(lines[:DIFF_LINES] + (['… %d more diff lines' % more] if more > 0 else []))


class GoldenRender(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.render = importlib.import_module('render')   # tools/render.py: its REPORT / SMALL specs and helpers

    def setUp(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        # mapkit leaves some files for the collector to close and prints its size warnings: neither is under test
        stack.enter_context(warnings.catch_warnings())
        warnings.simplefilter('ignore', ResourceWarning)
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.tmp = stack.enter_context(tempfile.TemporaryDirectory())
        self.out = os.path.join(self.tmp, 'out')
        os.makedirs(self.out)
        stack.enter_context(mock.patch.object(geo, 'get_tile', rf.synth_tile))
        stack.enter_context(mock.patch.object(mapkit, 'FRAG', self.out))
        stack.enter_context(mock.patch.object(mapkit, 'MAPPNG', self.out))
        stack.enter_context(mock.patch.dict(mapkit.LAST_OSM))
        stack.enter_context(mock.patch.dict(os.environ))
        os.environ.pop('REUSE_PNG', None)   # set, render_map would keep a PNG already in MAPPNG instead of drawing one
        for name in ('overpass', 'osm_layers'):   # every map has its OpenStreetMap answer: nothing may fetch one
            stack.enter_context(mock.patch.object(geo, name, side_effect=AssertionError('geo.%s called offline' % name)))
        self.osm = copy.deepcopy(rf.OSM)   # one answer shared by a trip's maps and tile, as render_single shares it

    def gpx_file(self, name, text):
        p = os.path.join(self.tmp, name + '.gpx')
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(text)
        return p

    def output(self, name):
        return _read(os.path.join(self.out, name))

    def draw_maps(self, specs, hillshade=()):
        metas = {}
        for s in specs:
            s['osm_data'] = self.osm
            if s['name'] not in hillshade:
                s['hillshade'] = False
            metas[s['name']] = mapkit.render_map(s)
        return metas

    def check_golden(self, case):
        got = collect(self.out)
        folder = os.path.join(GOLDEN, case)
        if UPDATE:
            os.makedirs(folder, exist_ok=True)
            for f in os.listdir(folder):
                if _ours(f) and f not in got:
                    os.remove(os.path.join(folder, f))
            for f, text in got.items():
                with open(os.path.join(folder, f), 'w', encoding='utf-8', newline='') as fh:
                    fh.write(text)
            return
        if not os.path.isdir(folder):
            self.fail('no golden files for %s: run UPDATE_GOLDEN=1 python3 -m unittest discover -s tests -p test_mapkit_golden.py' % case)
        have = {f for f in os.listdir(folder) if _ours(f)}
        problems = []
        for f in sorted(set(got) - have):
            problems.append('%s: drawn, but there is no golden file for it' % f)
        for f in sorted(have - set(got)):
            problems.append('%s: in the goldens, but no longer drawn' % f)
        for f in sorted(have & set(got)):
            want = _read(os.path.join(folder, f))
            if want != got[f]:
                problems.append(_diff(f, want, got[f]))
        if problems:
            self.fail('%s: the renderer no longer draws what tests/golden/render/%s holds. If the change is meant, run '
                      'UPDATE_GOLDEN=1 python3 -m unittest discover -s tests -p test_mapkit_golden.py and review the diff.\n\n%s'
                      % (case, case, '\n\n'.join(problems)))

    # ---------------------------------------------------------------- the cases

    def test_hike_loop(self):
        r = self.render
        t = {'slug': 'golden-hike-loop', 'title': 'Quillon Peak Loop', 'activity': 'hike', 'cat': 'HIK', 'kind': 'report',
             'map': {'peaks': ['Quillon Peak']}, 'stats': dict(rf.LOOP_STATS), 'route_shape': 'loop'}
        tr = r.load_track(self.gpx_file('loop', rf.LOOP_GPX), t['slug'], t['cat'], t['stats'])
        self.assertFalse(mapkit.is_out_and_back(tr))
        metas = self.draw_maps(single_specs(r, t, [tr]), hillshade=('map-phone',))
        self.assertIs(metas['map-wide']['outbound_only'], False)
        self.assertEqual([n for n in metas if metas[n].get('png')], ['map-phone'])
        # the profiles single_charts draws
        tot = tr.total / geo.MI
        for nm, w, ph in (('profile-wide', 1248, 140), ('profile-col', 718, 110), ('profile-phone', 358, 100)):
            mapkit.render_profile(nm, [tr], w, ph, dict(skin=(t['activity'] == 'ski'), grade=False, axis_every_mi=r.axis_step(tot, w),
                                                        aria='Elevation profile of ' + t['title']))
        mapkit.render_tile('tile', tr, 200, 152, t['cat'], osm_detail=None, osm_data=self.osm, planned=False, tracks=None)
        mapkit.render_glyph('g112', tr, 112, 64, t['cat'], planned=False)
        mapkit.render_glyph('g64', tr, 64, 48, t['cat'], planned=False, pad=5)
        mapkit.render_sparkline('spark', tr, 96, 24)
        mapkit.render_sparkline('spark-cur', tr, 96, 24, color='{{route}}', stroke=2)
        self.check_golden('hike-loop')

    def test_mtb_out_and_back(self):
        r = self.render
        t = {'slug': 'golden-mtb-out-and-back', 'title': 'Ostrey Ridge Ride', 'activity': 'mtb', 'cat': 'MTB', 'kind': 'report',
             'map': {}, 'stats': dict(rf.OUT_BACK_STATS), 'route_shape': 'out-and-back'}
        tr = r.load_track(self.gpx_file('ride', rf.OUT_BACK_GPX), t['slug'], t['cat'], t['stats'])
        self.assertTrue(mapkit.is_out_and_back(tr))
        metas = self.draw_maps(single_specs(r, t, [tr]))
        self.assertIs(metas['map-wide']['outbound_only'], True)    # mile discs on the way out only
        self.assertIs(metas['map-col']['outbound_only'], True)
        # chevrons: never on an out-and-back (they would point both ways), drawn on a one-way leg
        far = max(range(len(tr.raw)), key=lambda k: geo.hav(tr.raw[0], tr.raw[k]))
        out_leg = mapkit.Track(tr.raw[:far + 1], t['slug'] + '-out', t['cat'])
        self.assertFalse(mapkit.is_out_and_back(out_leg))
        for name, track in (('map-chev', tr), ('map-chev-out', out_leg)):
            mapkit.render_map(dict(r.REPORT, name=name, w=718, h=400, chevrons=True, hillshade=False, contours=False, osm_data=None,
                                   aria='Chevrons on ' + name, tracks=[{'track': track, 'style': 'route', 'width': 3}]))
        self.assertNotIn('mk-chev', self.output('map-chev.svg.html'))
        self.assertIn('mk-chev', self.output('map-chev-out.svg.html'))
        self.check_golden('mtb-out-and-back')

    def test_planned_two_segments(self):
        r = self.render
        t = {'slug': 'golden-planned-two-segments', 'title': 'Vardle Traverse', 'activity': 'hike', 'cat': 'HIK', 'kind': 'planned',
             'map': {}, 'stats': {}}
        drawn = gpxroute.as_tracks(self.gpx_file('plan', gf.JUMP), t['slug'], t['cat'])
        self.assertEqual(len(drawn), 2)
        self.draw_maps(single_specs(r, t, drawn, planned=True))
        for name in ('map-wide', 'map-col', 'map-phone'):   # two parts, never joined across the gap
            self.assertEqual(self.output(name + '.svg.html').count('stroke-dasharray: 8 5'), 2, name)
        multi = [{'track': x, 'style': 'planned', 'cat': t['cat'], 'width': 2.5, 'trim': mapkit.DEFAULT_TRIM} for x in drawn]
        mapkit.render_tile('tile', drawn[0], 200, 152, t['cat'], osm_detail=None, osm_data=self.osm, planned=True, tracks=multi)
        mapkit.render_glyph('g112', drawn, 112, 64, t['cat'], planned=True)
        mapkit.render_glyph('g64', drawn, 64, 48, t['cat'], planned=True, pad=5)
        self.check_golden('planned-two-segments')


# ---------------------------------------------------------------- gap9-08: the bounded tile cache

def _png_1x1(rgb):
    """A 1x1 RGB PNG of this colour (Terrarium: elevation = r * 256 + g + b / 256 - 32768)."""
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00' + bytes(rgb))) + chunk(b'IEND', b''))


def _pixel_ll(z, gx, gy):
    """(lat, lon) of global pixel position (gx, gy) at zoom z (pixel k's centre is at k + 0.5)."""
    n = 256 * 2 ** z
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * gy / n)))), gx / n * 360.0 - 180.0


class TileCache(unittest.TestCase):
    """geo.get_tile keeps a decoded tile as array('d') in an LRU of TILE_CACHE_MAX (256) tiles, and DEM.sample reads the
    same values from it as from the list it used to be. The hike loop's hillshade PNG in the goldens pins the rest. No
    network: TILE_DIR is a temp folder holding the tiles the test wrote, and a curl call fails the test."""

    def setUp(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(warnings.catch_warnings())
        warnings.simplefilter('ignore', ResourceWarning)   # geo.png_read leaves its file to the collector
        self.tiles = os.path.join(stack.enter_context(tempfile.TemporaryDirectory()), 'tiles')
        os.makedirs(self.tiles)
        stack.enter_context(mock.patch.object(geo, 'TILE_DIR', self.tiles))
        stack.enter_context(mock.patch.dict(geo._tile_cache, clear=True))   # the process's own tiles come back after
        stack.enter_context(mock.patch.dict(geo.CACHE))
        geo.CACHE['tile_hit'] = geo.CACHE['tile_miss'] = 0
        stack.enter_context(mock.patch.object(geo.subprocess, 'run', side_effect=AssertionError('a tile fetch was attempted')))

    def put(self, z, x, y, data):
        with open(os.path.join(self.tiles, '%d_%d_%d.png' % (z, x, y)), 'wb') as fh:
            fh.write(data)

    def test_dem_sample_reads_the_same_values_from_an_array_as_from_a_list(self):
        grid = [(rf.LAT0 + dy / rf.KY, rf.LON0 + dx / rf.KX) for dy in range(-3000, 3001, 750) for dx in range(-3000, 3001, 750)]
        for z in (13, 15):   # z15: the hillshade zoom of a small map (hs_zoom)
            fx, fy = geo.tile_xy(rf.LAT0, rf.LON0, z)
            x, y = int(fx), int(fy)
            self.assertIsInstance(rf.synth_tile(z, x, y), array.array)
            # spots whose four neighbouring pixels lie in two or four tiles: across an edge and at a corner
            edges = [_pixel_ll(z, gx, gy) for gx, gy in (((x + 1) * 256 + 0.2, y * 256 + 100.0), (x * 256 + 60.0, (y + 1) * 256 + 0.3),
                                                         ((x + 1) * 256 + 0.1, (y + 1) * 256 + 0.4))]
            spots = grid + edges
            dem = geo.DEM(z)
            with mock.patch.object(geo, 'get_tile', lambda z_, x_, y_: list(rf.synth_tile(z_, x_, y_))):
                from_list = [dem.sample(lat, lon) for lat, lon in spots]
            with mock.patch.object(geo, 'get_tile', lambda z_, x_, y_: array.array('d', rf.synth_tile(z_, x_, y_))):
                from_array = [dem.sample(lat, lon) for lat, lon in spots]
            self.assertEqual(from_array, from_list)
            self.assertTrue(all(1700 < v < 2700 for v in from_array), from_array)

    def test_get_tile_decodes_a_terrarium_png_into_an_array_of_the_values_synth_tile_gives(self):
        z = 13
        fx, fy = geo.tile_xy(rf.LAT0, rf.LON0, z)
        x, y = int(fx), int(fy)
        self.put(z, x, y, rf.terrarium_png(z, x, y))
        t = geo.get_tile(z, x, y)
        self.assertIsInstance(t, array.array)
        self.assertEqual((t.typecode, len(t)), ('d', 256 * 256))
        self.assertEqual(list(t), list(rf.synth_tile(z, x, y)))
        # DEM.sample inside that tile: the decoded PNG and the stub give the same elevations
        spots = [_pixel_ll(z, x * 256 + i, y * 256 + j) for i, j in ((20.0, 30.0), (128.3, 77.7), (200.6, 230.1), (2.5, 250.2))]
        dem = geo.DEM(z)
        decoded = [dem.sample(lat, lon) for lat, lon in spots]
        with mock.patch.object(geo, 'get_tile', rf.synth_tile):
            self.assertEqual([dem.sample(lat, lon) for lat, lon in spots], decoded)
        self.assertEqual((geo.CACHE['tile_hit'], geo.CACHE['tile_miss']), (1, 0))   # read from disk once, then from memory

    def test_the_cache_keeps_the_most_recently_used_tiles_and_drops_the_oldest(self):
        self.assertEqual(geo.TILE_CACHE_MAX, 256)
        for k in range(4):
            self.put(5, 0, k, _png_1x1((128, k, 0)))   # elevation k m
        with mock.patch.object(geo, 'TILE_CACHE_MAX', 3):
            for k in (0, 1, 2):
                self.assertEqual(list(geo.get_tile(5, 0, k)), [float(k)])
            self.assertEqual(list(geo._tile_cache), [(5, 0, 0), (5, 0, 1), (5, 0, 2)])
            geo.get_tile(5, 0, 0)                     # a hit: from memory, and now the most recent
            self.assertEqual(geo.CACHE['tile_hit'], 3)
            self.assertEqual(list(geo._tile_cache), [(5, 0, 1), (5, 0, 2), (5, 0, 0)])
            geo.get_tile(5, 0, 3)                     # a fourth tile: the least recently used one (1) goes
            self.assertEqual(list(geo._tile_cache), [(5, 0, 2), (5, 0, 0), (5, 0, 3)])
            self.assertEqual(list(geo.get_tile(5, 0, 1)), [1.0])   # read from disk again, and 2 goes
            self.assertEqual(geo.CACHE['tile_hit'], 5)
            self.assertEqual(list(geo._tile_cache), [(5, 0, 0), (5, 0, 3), (5, 0, 1)])


if __name__ == '__main__':
    unittest.main()
