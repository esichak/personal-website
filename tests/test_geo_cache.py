"""Phase 6: tools/lib/geo.py's download caches: where they live, that importing geo makes no folder, and how a cached
terrain tile or OpenStreetMap answer is read, fetched again and counted.

Nothing here reaches the network or the real caches. geo.OSM_DIR and geo.TILE_DIR point into a temp folder that may not
exist yet, geo.ROOT and geo.CACHE_HOME are patched for the folder choice (geo._cache_dir), and geo.subprocess.run, the
curl call, is a stub that records its argv and answers with fixed bytes. The import test runs `import geo` in a child
Python whose HOME is an empty temp folder, so the real ~/Library/Caches is never looked at. geo.CACHE (the counts
render.py prints at the end of a run) is emptied before every test and put back after it.
"""
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import warnings
import zlib
from types import SimpleNamespace
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
LIB = os.path.join(ROOT, 'tools', 'lib')
sys.path.insert(0, LIB)
import geo  # noqa: E402

QUERY = '[out:json][timeout:60];way["highway"](38.90,-120.11,38.91,-120.10);out geom;'
ANSWER = {'version': 0.6, 'elements': [{'type': 'way', 'id': 1, 'tags': {'highway': 'path'}}]}
EMPTY_COUNTS = {'tile_hit': 0, 'tile_miss': 0, 'osm_hit': 0, 'osm_miss': 0, 'osm_dates': set(), 'osm_undated': 0}


def answer_file(osm_dir, query=QUERY):
    """Where geo.overpass keeps the answer to `query`."""
    return os.path.join(osm_dir, hashlib.sha1(query.encode()).hexdigest()[:16] + '.json')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def tiny_png(rgb):
    """A 1x1 RGB PNG of this colour (Terrarium tiles encode elevation as r * 256 + g + b / 256 - 32768)."""
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00' + bytes(rgb))) + chunk(b'IEND', b''))


class Curl(object):
    """geo.subprocess.run's stand-in: records each argv (and whether the cache file was there at that moment) and answers
    like curl, with `stdout` bytes, or by writing `body` to the file named after -o."""

    def __init__(self, stdout=b'', body=None, watch=None):
        self.stdout, self.body, self.watch = stdout, body, watch
        self.calls, self.cache_was_there = [], []

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        if self.watch:
            self.cache_was_there.append(os.path.exists(self.watch))
        if self.body is not None:
            with open(argv[argv.index('-o') + 1], 'wb') as fh:
                fh.write(self.body)
        return SimpleNamespace(returncode=0, stdout=self.stdout, stderr=b'')


class GeoFixture(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        saved = {k: (set(v) if isinstance(v, set) else v) for k, v in geo.CACHE.items()}

        def put_back():
            geo.CACHE.clear()
            geo.CACHE.update(saved)
        self.addCleanup(put_back)
        geo.CACHE.clear()
        geo.CACHE.update({k: (set() if isinstance(v, set) else v) for k, v in EMPTY_COUNTS.items()})
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)

    def patch(self, owner, name, value):
        p = mock.patch.object(owner, name, value)
        p.start()
        self.addCleanup(p.stop)

    def counts(self, **expected):
        return dict(EMPTY_COUNTS, **expected)


class CachedAnswerTests(GeoFixture):
    """geo.cached_answer(path): (data, fetched date or None), or None for a file that is missing or cut short."""

    def test_a_missing_file_is_none(self):
        self.assertIsNone(geo.cached_answer(os.path.join(self.tmp, 'nothing-here.json')))

    def test_a_file_that_does_not_parse_is_removed_and_none(self):
        for text in ('', '{"fetched": "2026-05-01", "query": "x", "data": {"elem', '[1, 2'):
            with self.subTest(text=text):
                path = os.path.join(self.tmp, 'cut-short.json')
                write(path, text)
                self.assertIsNone(geo.cached_answer(path))
                self.assertFalse(os.path.exists(path))

    def test_a_dated_answer_gives_its_data_and_the_day_it_was_fetched(self):
        path = os.path.join(self.tmp, 'dated.json')
        write(path, json.dumps({'fetched': '2026-05-01', 'query': QUERY, 'data': ANSWER}))
        self.assertEqual(geo.cached_answer(path), (ANSWER, '2026-05-01'))

    def test_an_answer_cached_before_answers_carried_a_date_is_read_as_it_is(self):
        for obj in (ANSWER, {'data': ANSWER}, [ANSWER]):     # a 'data' key without 'fetched' is no wrapper either
            with self.subTest(obj=obj):
                path = os.path.join(self.tmp, 'bare.json')
                write(path, json.dumps(obj))
                self.assertEqual(geo.cached_answer(path), (obj, None))
                self.assertTrue(os.path.exists(path))


    def test_a_file_that_cannot_be_read_now_is_kept(self):
        # an iCloud placeholder read offline fails with an OSError: the answer is not there for this run, but deleting it
        # would delete the only copy (and iCloud would sync the deletion)
        path = os.path.join(self.tmp, 'offloaded.json')
        write(path, json.dumps({'fetched': '2026-05-01', 'query': QUERY, 'data': ANSWER}))
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)
        if os.access(path, os.R_OK):
            self.skipTest('this user can read a file without permissions (root)')
        self.assertIsNone(geo.cached_answer(path))
        self.assertTrue(os.path.exists(path))


class OverpassTests(GeoFixture):
    """geo.overpass(query) answers from OSM_DIR when it can, and otherwise fetches with curl and caches the answer."""

    def setUp(self):
        super().setUp()
        self.osm = os.path.join(self.tmp, 'osm')
        self.patch(geo, 'OSM_DIR', self.osm)

    def curl(self, **kw):
        stub = Curl(**kw)
        self.patch(geo.subprocess, 'run', stub)
        return stub

    def test_a_cached_answer_is_returned_without_a_fetch_and_counted_with_its_date(self):
        write(answer_file(self.osm), json.dumps({'fetched': '2026-05-01', 'query': QUERY, 'data': ANSWER}))
        curl = self.curl(stdout=b'{}')
        self.assertEqual(geo.overpass(QUERY), ANSWER)
        self.assertEqual(curl.calls, [])
        self.assertEqual(geo.CACHE, self.counts(osm_hit=1, osm_dates={'2026-05-01'}))

    def test_an_undated_cached_answer_is_dated_by_its_file(self):
        path = answer_file(self.osm)
        write(path, json.dumps(ANSWER))
        noon = time.mktime((2025, 3, 4, 12, 0, 0, 0, 0, -1))   # local noon: the same day in any time zone setting
        os.utime(path, (noon, noon))
        curl = self.curl(stdout=b'{}')
        self.assertEqual(geo.overpass(QUERY), ANSWER)
        self.assertEqual(curl.calls, [])
        self.assertEqual(geo.CACHE, self.counts(osm_hit=1, osm_undated=1, osm_dates={'2025-03-04'}))

    def test_a_truncated_cache_file_is_removed_fetched_once_and_cached_with_its_date(self):
        path = answer_file(self.osm)
        write(path, '{"fetched": "2026-05-01", "query": "')
        curl = self.curl(stdout=json.dumps(ANSWER).encode('utf-8'), watch=path)
        before = time.strftime('%Y-%m-%d')
        self.assertEqual(geo.overpass(QUERY), ANSWER)
        after = time.strftime('%Y-%m-%d')
        self.assertEqual(len(curl.calls), 1)
        self.assertEqual(curl.cache_was_there, [False])                 # the broken file went before the fetch
        self.assertEqual(curl.calls[0][0], 'curl')
        self.assertIn('data=' + QUERY, curl.calls[0])
        with open(path, encoding='utf-8') as fh:
            stored = json.load(fh)
        self.assertEqual(sorted(stored), ['data', 'fetched', 'query'])
        self.assertEqual((stored['query'], stored['data']), (QUERY, ANSWER))
        self.assertIn(stored['fetched'], (before, after))
        self.assertEqual(os.listdir(self.osm), [os.path.basename(path)])  # no .part file left
        self.assertEqual(geo.CACHE, self.counts(osm_miss=1, osm_dates={stored['fetched']}))

    def test_the_cache_folder_is_made_on_the_first_answer_written(self):
        self.osm = os.path.join(self.tmp, 'not', 'made', 'yet', 'osm')
        self.patch(geo, 'OSM_DIR', self.osm)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'not')))
        curl = self.curl(stdout=json.dumps(ANSWER).encode('utf-8'))
        self.assertEqual(geo.overpass(QUERY), ANSWER)
        self.assertEqual(os.listdir(self.osm), [os.path.basename(answer_file(self.osm))])
        self.assertEqual(geo.overpass(QUERY), ANSWER)                    # the second time from the cache
        self.assertEqual(len(curl.calls), 1)
        self.assertEqual((geo.CACHE['osm_miss'], geo.CACHE['osm_hit']), (1, 1))


class TileTests(GeoFixture):
    """geo.get_tile counts a tile read from TILE_DIR and one fetched, and makes TILE_DIR on the first fetch."""

    def test_a_fetched_tile_then_a_cached_one_are_counted_and_the_folder_is_made_on_the_fetch(self):
        tiles = os.path.join(self.tmp, 'not-made-yet', 'tiles')
        self.patch(geo, 'TILE_DIR', tiles)
        curl = Curl(body=tiny_png((128, 0, 0)))                         # elevation 0 m
        self.patch(geo.subprocess, 'run', curl)
        memo = mock.patch.dict(geo._tile_cache)                         # the in-process tile memo is put back after
        memo.start()
        self.addCleanup(memo.stop)
        geo._tile_cache.pop((3, 1, 2), None)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', ResourceWarning)             # geo.png_read leaves its file to the collector
            self.assertEqual(list(geo.get_tile(3, 1, 2)), [0.0])      # an array('d') since Phase 15 (gap9-08)
            self.assertEqual(os.listdir(tiles), ['3_1_2.png'])
            del geo._tile_cache[(3, 1, 2)]
            self.assertEqual(list(geo.get_tile(3, 1, 2)), [0.0])      # an array('d') since Phase 15 (gap9-08)
        self.assertEqual(len(curl.calls), 1)
        self.assertEqual((geo.CACHE['tile_miss'], geo.CACHE['tile_hit']), (1, 1))


class CacheDirTests(GeoFixture):
    """geo._cache_dir(env, name): the environment variable, else CACHE_HOME/<name>, except that a checkout whose old
    .cache/<name> exists while CACHE_HOME/<name> does not keeps the old folder. It makes no folder itself."""

    def setUp(self):
        super().setUp()
        self.repo = os.path.join(self.tmp, 'checkout')
        self.home = os.path.join(self.tmp, 'home', 'Library', 'Caches', 'personal-website')
        self.patch(geo, 'ROOT', self.repo)
        self.patch(geo, 'CACHE_HOME', self.home)
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        for name in ('TILE_DIR', 'OSM_DIR'):
            os.environ.pop(name, None)

    def test_the_environment_variable_wins(self):
        for name in ('tiles', 'osm'):
            os.makedirs(os.path.join(self.repo, '.cache', name))
            os.makedirs(os.path.join(self.home, name))
        mine = os.path.join(self.tmp, 'my-tiles')
        os.environ['TILE_DIR'] = mine
        self.assertEqual(geo._cache_dir('TILE_DIR', 'tiles'), mine)
        self.assertEqual(geo._cache_dir('OSM_DIR', 'osm'), os.path.join(self.home, 'osm'))

    def test_the_old_folder_in_the_checkout_is_used_while_the_new_one_does_not_exist(self):
        os.makedirs(os.path.join(self.repo, '.cache', 'osm'))
        self.assertEqual(geo._cache_dir('OSM_DIR', 'osm'), os.path.join(self.repo, '.cache', 'osm'))
        # only the cache that has an old folder keeps it
        self.assertEqual(geo._cache_dir('TILE_DIR', 'tiles'), os.path.join(self.home, 'tiles'))

    def test_the_folder_under_cache_home_otherwise(self):
        self.assertEqual(geo._cache_dir('TILE_DIR', 'tiles'), os.path.join(self.home, 'tiles'))
        self.assertFalse(os.path.exists(self.home))                     # named, not made
        os.makedirs(os.path.join(self.repo, '.cache', 'tiles'))
        os.makedirs(os.path.join(self.home, 'tiles'))                   # moved once: the old folder is left alone
        self.assertEqual(geo._cache_dir('TILE_DIR', 'tiles'), os.path.join(self.home, 'tiles'))


class ImportTests(unittest.TestCase):

    def test_importing_geo_makes_no_folder(self):
        with tempfile.TemporaryDirectory() as home:
            env = {k: v for k, v in os.environ.items() if k not in ('TILE_DIR', 'OSM_DIR')}
            env.update(HOME=home, PYTHONDONTWRITEBYTECODE='1')
            code = 'import sys; sys.path.insert(0, %r); import geo; print(geo.TILE_DIR); print(geo.OSM_DIR)' % LIB
            r = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(os.path.exists(os.path.join(home, 'Library')))
            self.assertEqual(os.listdir(home), [])
            # where the caches would go: under the (temp) home folder, or a checkout's old .cache/ folder
            for got, name in zip(r.stdout.splitlines(), ('tiles', 'osm')):
                self.assertIn(got, (os.path.join(home, 'Library', 'Caches', 'personal-website', name),
                                    os.path.join(ROOT, '.cache', name)))


if __name__ == '__main__':
    unittest.main()
