"""tools/render_sheet.py (Phase 15, gap9-02) on synthetic inputs: the SHA-1 comparison, the gzip size and mapkit's
base-layer budgets, the iCloud conflict-copy filter, the parsing of git's status, diff and ls-tree output into the
header's counts, --after's preview folder (its counts, a trip it did not draw, a site map named by its key, the card
drawing) and the out-folder guard. Nothing here runs git or reads rendered/."""
import importlib
import json
import os
import tempfile
import unittest
import zlib

import helpers  # noqa: F401  (puts tools/ on sys.path)
import mapkit

sheet = importlib.import_module('render_sheet')


class CompareTests(unittest.TestCase):

    def test_state_by_sha1(self):
        self.assertEqual(sheet.state(b'abc', b'abc'), 'unchanged')
        self.assertEqual(sheet.state(b'abc', b'abd'), 'changed')
        self.assertEqual(sheet.state(None, b'abc'), 'new')
        self.assertEqual(sheet.state(b'abc', None), 'removed')
        self.assertEqual(sheet.state(None, None), 'missing')
        self.assertEqual(sheet.state(b'', b''), 'unchanged')      # an empty file is a file
        self.assertIsNone(sheet.sha1(None))
        self.assertEqual(sheet.sha1(b'abc'), 'a9993e364706816aba3e25717850c26c9cd0d89d')

    def test_gzip_size_as_mapkit_measures_it(self):
        data = b'<svg><path d="M0 0L10 10"/></svg>' * 400
        self.assertAlmostEqual(sheet.gz_kb(data), len(zlib.compress(data, 9)) / 1024.0)
        self.assertLess(sheet.gz_kb(data), len(data) / 1024.0)

    def test_budgets_come_from_mapkit(self):
        phone, other = mapkit.BASE_GZ_KB_PHONE, mapkit.BASE_GZ_KB
        self.assertLess(phone, other)
        for name in ('map-phone', 'map-phone.base.svg', 'day-01-phone', 'region-synt-phone', 'overview-phone-2'):
            self.assertEqual(sheet.budget_kb(name), phone, name)
        for name in ('map-wide', 'map-col.base.svg', 'overview-tall', 'region-synt-desktop', 'day-01-col.base.svg'):
            self.assertEqual(sheet.budget_kb(name), other, name)

    def test_gz_cell_marks_a_size_over_budget(self):
        cell = sheet.gz_cell((12.0, 90.5, 80))
        self.assertIn('12.0 KB', cell)
        self.assertIn('90.5 KB (over)', cell)
        self.assertIn('budget 80 KB', cell)
        self.assertIn('—', sheet.gz_cell((None, 3.0, 40)))

    def test_pair_state(self):
        row = lambda st: ('f', 1, 1, st, None)   # noqa: E731
        self.assertEqual(sheet.pair_state([row('unchanged'), row('unchanged')]), 'unchanged')
        self.assertEqual(sheet.pair_state([row('unchanged'), row('changed')]), 'changed')
        self.assertEqual(sheet.pair_state([row('new'), row('new')]), 'new')
        self.assertEqual(sheet.pair_state([row('removed'), row('missing')]), 'removed')
        self.assertEqual(sheet.pair_state([row('new'), row('removed')]), 'changed')    # .png gave way to .webp
        self.assertEqual(sheet.pair_state([row('missing')]), 'missing')


class ConflictCopyTests(unittest.TestCase):

    def test_any_part_of_the_path(self):
        for p in ('rendered/trips/synt-a/meta 3.json', 'rendered/trips/synt-a 2/meta.json',
                  'rendered/trips/synt-a/map-wide.base 4.svg', 'rendered/site/region-synt-desktop.svg 3.html',
                  'rendered/trips/synt-a/map-col 12.webp'):
            self.assertTrue(sheet.conflict_path(p), p)
        for p in ('rendered/trips/synt-a/meta.json', 'rendered/trips/synt-2026-09-24/map-col.webp',
                  'rendered/site/region-synt-desktop.base.svg', 'rendered/trips/synt-a/day-01-col.svg.html'):
            self.assertFalse(sheet.conflict_path(p), p)


class ChangeCountTests(unittest.TestCase):

    def test_parse_status(self):
        out = '\0'.join([' M rendered/trips/synt-a/meta.json', 'M  rendered/trips/synt-a/tile.svg.html',
                         '?? rendered/trips/synt-b/meta.json', ' D rendered/trips/synt-c/g112.svg.html',
                         'A  rendered/trips/synt-d/map-col.webp', 'AD rendered/trips/synt-e/gone.svg',
                         'MM rendered/site/meta.json', '']) + '\0'
        self.assertEqual(sheet.parse_status(out), [
            ('changed', 'rendered/trips/synt-a/meta.json'), ('changed', 'rendered/trips/synt-a/tile.svg.html'),
            ('new', 'rendered/trips/synt-b/meta.json'), ('removed', 'rendered/trips/synt-c/g112.svg.html'),
            ('new', 'rendered/trips/synt-d/map-col.webp'), ('changed', 'rendered/site/meta.json')])
        self.assertEqual(sheet.parse_status(''), [])

    def test_parse_name_status(self):
        out = 'M\0rendered/trips/synt-a/meta.json\0A\0rendered/trips/synt-b/x.svg\0D\0rendered/site/old.webp\0' \
              'T\0rendered/trips/synt-a/y\0'
        self.assertEqual(sheet.parse_name_status(out), [
            ('changed', 'rendered/trips/synt-a/meta.json'), ('new', 'rendered/trips/synt-b/x.svg'),
            ('removed', 'rendered/site/old.webp'), ('changed', 'rendered/trips/synt-a/y')])
        self.assertEqual(sheet.parse_name_status(''), [])

    def test_tally_skips_conflict_copies(self):
        base = ['rendered/trips/synt-a/meta.json', 'rendered/trips/synt-a/tile.svg.html', 'rendered/trips/synt-c/g112.svg.html',
                'rendered/site/meta.json', 'rendered/trips/synt-a/meta 3.json']        # a committed copy is not counted either
        entries = [('changed', 'rendered/trips/synt-a/meta.json'), ('removed', 'rendered/trips/synt-c/g112.svg.html'),
                   ('new', 'rendered/trips/synt-b/meta.json'), ('new', 'rendered/trips/synt-a/meta 4.json'),
                   ('new', 'rendered/trips/synt-b 2/meta.json'), ('changed', 'rendered/trips/synt-a/meta.json')]
        self.assertEqual(sheet.tally(entries, base),
                         {'changed': 1, 'unchanged': 2, 'new': 1, 'removed': 1, 'skipped': 2})
        self.assertEqual(sheet.tally([], base)['unchanged'], 4)

    def test_changed_trips(self):
        entries = [('changed', 'rendered/trips/synt-b/meta.json'), ('new', 'rendered/trips/synt-a/map-col.webp'),
                   ('changed', 'rendered/trips/synt-b/tile.svg.html'), ('changed', 'rendered/site/meta.json'),
                   ('new', 'rendered/trips/synt-c 2/meta.json'), ('new', 'rendered/trips/synt-d/meta 3.json')]
        self.assertEqual(sheet.changed_trips(entries), ['synt-a', 'synt-b'])


class SampleTests(unittest.TestCase):

    def test_parse_spec(self):
        self.assertEqual(sheet.parse_spec('synt-a'), ('synt-a', None))
        self.assertEqual(sheet.parse_spec('synt-a:overview-wide,day-01-col'), ('synt-a', ['overview-wide', 'day-01-col']))
        self.assertEqual(sheet.parse_spec('site:region-synt-desktop'), ('site', ['region-synt-desktop']))
        self.assertEqual(sheet.folder_of('site'), 'rendered/site')
        self.assertEqual(sheet.folder_of('synt-a'), 'rendered/trips/synt-a')

    def test_size_and_kind(self):
        self.assertEqual([sheet.size_of(n) for n in ('map-wide', 'overview-tall', 'day-01-col', 'map-phone', 'region-x-desktop')],
                         ['wide', 'wide', 'col', 'phone', 'desktop'])
        metas = [{'maps': {'map-col': {}}, 'charts': {'profile-wide': {}}}, None]
        self.assertEqual(sheet.kind_of('map-col', metas), 'map')
        self.assertEqual(sheet.kind_of('profile-wide', metas), 'chart')
        self.assertEqual(sheet.kind_of('tile', metas), 'drawing')
        self.assertEqual(sheet.kind_of('g112', metas), 'drawing')

    def test_files_of_a_map_on_both_sides(self):
        before = {'maps': {'map-col': {'png': 'map-col.png', 'base': 'map-col.base.svg'}}}
        after = {'maps': {'map-col': {'png': 'map-col.webp', 'base': 'map-col.base.svg'}}}
        self.assertEqual(sheet.files_of('map-col', 'map', [before, after]),
                         ['map-col.png', 'map-col.webp', 'map-col.base.svg', 'map-col.svg.html'])
        self.assertEqual(sheet.files_of('map-col', 'map', [None, after]), ['map-col.webp', 'map-col.base.svg', 'map-col.svg.html'])
        self.assertEqual(sheet.files_of('profile-wide', 'chart', [before, after]), ['profile-wide.svg.html'])


class PreviewCompareTests(unittest.TestCase):
    """--after DIR: a folder laid out like rendered/, compared file by file with the base commit's ls-tree."""

    def test_parse_ls_tree_and_blob_id(self):
        out = ('100644 blob ce013625030ba8dba906f756967f9e9ca394464a\trendered/site/meta.json\0'
               '040000 tree 4b825dc642cb6eb9a060e54bf8d69288fbee4904\trendered/trips\0'
               '100644 blob e69de29bb2d1d6434b8b29ae775ad8c2e48c5391\trendered/trips/synt-a/a b.svg\0')
        self.assertEqual(sheet.parse_ls_tree(out), {
            'rendered/site/meta.json': 'ce013625030ba8dba906f756967f9e9ca394464a',
            'rendered/trips/synt-a/a b.svg': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391'})
        self.assertEqual(sheet.blob_id(b'hello\n'), 'ce013625030ba8dba906f756967f9e9ca394464a')   # git hash-object
        self.assertEqual(sheet.blob_id(b''), 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')

    def test_ignored_names_and_owner(self):
        for n in ('meta 3.json', 'synt-a 2', 'synt-a.tmp-4242', 'synt-a.old', '.DS_Store'):
            self.assertTrue(sheet.ignored_name(n), n)
        for n in ('meta.json', 'map-col.base.svg', 'synt-2026-09-24', 'card.svg.html'):
            self.assertFalse(sheet.ignored_name(n), n)
        self.assertEqual(sheet.owner_of('rendered/trips/synt-a/map-col.webp'), 'rendered/trips/synt-a')
        self.assertEqual(sheet.owner_of('rendered/site/mtb-synt-desktop.webp'), 'rendered/site')

    def test_compare_preview(self):
        base = {'rendered/trips/synt-a/meta.json': 'm1', 'rendered/trips/synt-a/map-col.svg.html': 'c1',
                'rendered/trips/synt-a/g112.svg.html': 'g1', 'rendered/trips/synt-b/meta.json': 'm2',
                'rendered/trips/synt-b/tile.svg.html': 't2', 'rendered/site/meta.json': 's1',
                'rendered/site/region-synt-desktop.webp': 'r1'}
        ids = {'rendered/trips/synt-a/meta.json': 'm1', 'rendered/trips/synt-a/map-col.svg.html': 'c9',
               'rendered/trips/synt-a/card.svg.html': 'k9'}
        counts, entries = sheet.compare_preview(ids, base, {'rendered', 'rendered/trips', 'rendered/trips/synt-a'}, 2)
        self.assertEqual(counts, {'changed': 1, 'unchanged': 1, 'new': 1, 'removed': 1, 'not_drawn': 4, 'skipped': 2})
        self.assertEqual(sorted(entries), [('changed', 'rendered/trips/synt-a/map-col.svg.html'),
                                           ('new', 'rendered/trips/synt-a/card.svg.html'),
                                           ('removed', 'rendered/trips/synt-a/g112.svg.html')])
        self.assertEqual(sheet.changed_trips(entries), ['synt-a'])
        line = sheet.summary_line('HEAD (abc1234)', counts, 'preview/rendered')
        self.assertTrue(line.startswith('preview/rendered against HEAD (abc1234): 1 changed'), line)
        self.assertIn('4 not drawn', line)
        working_copy = {k: v for k, v in counts.items() if k != 'not_drawn'}     # without --after: no such count
        self.assertTrue(sheet.summary_line('HEAD', working_copy).startswith('rendered/ against HEAD: '))
        self.assertNotIn('not drawn', sheet.summary_line('HEAD', working_copy))


OVERLAY = ('<svg width="300" height="200" viewBox="0 0 300 200" aria-hidden="true">'
           '<path class="mk-trk" d="M0 0L%d 10" style="stroke: {{route}}"/></svg>\n')
DRAWING = ('<svg width="400" height="267" viewBox="0 0 400 267" aria-hidden="true">'
           '<path class="gl-trk" d="M0 0L5 5" style="stroke: {{route}}"/></svg>\n')
TRIP_META = {'kind': 'trip', 'charts': {},
             'maps': {'map-col': {'w': 300, 'h': 200, 'png': 'map-col.webp', 'base': 'map-col.base.svg'}}}


class FakeBlobs:
    """The base commit's files for a test: {'rendered/...': bytes}."""

    def __init__(self, files):
        self.files = files

    def get(self, path):
        return self.files.get(path)


def put(top, rel, data):
    path = os.path.join(top, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as fh:
        fh.write(data if isinstance(data, bytes) else data.encode('utf-8'))


class PreviewSampleTests(unittest.TestCase):
    """A synthetic base and preview folder drawn through sample_html: a trip the preview holds (a changed map, a new
    card drawing), one it does not (before only, 'not drawn'), and a new site map its meta.json does not list."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out, self.dir = os.path.join(tmp.name, 'out'), os.path.join(tmp.name, 'preview', 'rendered')
        meta = json.dumps(TRIP_META).encode('utf-8')
        base = {}
        for slug in ('synt-a', 'synt-b'):
            base.update({'rendered/trips/%s/meta.json' % slug: meta,
                         'rendered/trips/%s/map-col.svg.html' % slug: (OVERLAY % 10).encode('utf-8'),
                         'rendered/trips/%s/map-col.webp' % slug: b'RIFF-synt-WEBP',
                         'rendered/trips/%s/map-col.base.svg' % slug: b'<svg xmlns="http://www.w3.org/2000/svg"/>'})
        base['rendered/site/meta.json'] = b'{"maps": {}}'
        for rel in ('trips/synt-a/meta.json', 'trips/synt-a/map-col.webp', 'trips/synt-a/map-col.base.svg', 'site/meta.json'):
            put(self.dir, rel, base['rendered/' + rel])
        put(self.dir, 'trips/synt-a/map-col.svg.html', OVERLAY % 20)          # redrawn
        put(self.dir, 'trips/synt-a/card.svg.html', DRAWING)                  # new
        put(self.dir, 'site/mtb-synt-desktop.svg.html', OVERLAY % 30)          # new, and not in the folder's meta.json
        put(self.dir, 'site/mtb-synt-desktop.webp', b'RIFF-synt-WEBP')
        os.makedirs(self.out)
        self.before = sheet.Side('before', 'HEAD (abc1234)', self.out, FakeBlobs(base))
        self.after = sheet.Side('after', 'preview/rendered', self.out, src=self.dir, preview=True)

    def sample(self, where, names):
        report = []
        page = sheet.sample_html(1, where, names, 'named', {}, self.before, self.after, report)
        return page, {name: st for _title, name, st in report}

    def test_a_trip_the_preview_drew(self):
        page, states = self.sample('synt-a', ['map-col', 'card'])
        self.assertEqual(states, {'map-col': 'changed', 'card': 'new'})
        self.assertIn('src="after/trips/synt-a/map-col.webp"', page)
        self.assertIn('src="before/trips/synt-a/map-col.webp"', page)
        self.assertIn('gl--card', page)                                          # core.card_tile's image
        self.assertIn('src="after/trips/synt-a/card.svg"', page)
        self.assertTrue(os.path.isfile(os.path.join(self.out, 'after', 'trips', 'synt-a', 'card.svg')))
        self.assertIn('Not in HEAD (abc1234)', page)                             # the card's before side

    def test_a_trip_the_preview_did_not_draw(self):
        self.assertTrue(self.after.not_drawn('rendered/trips/synt-b'))
        self.assertFalse(self.after.not_drawn('rendered/trips/synt-a'))
        page, states = self.sample('synt-b', None)                              # its default renders: map-col
        self.assertEqual(states, {'map-col': 'not drawn'})
        self.assertIn('not drawn in preview/rendered: before only', page)
        self.assertIn('Not drawn in preview/rendered', page)
        self.assertIn('src="before/trips/synt-b/map-col.webp"', page)
        self.assertNotIn('removed', page)

    def test_a_site_map_by_its_key(self):
        self.assertTrue(sheet.has_item((self.before, self.after), 'rendered/site', 'mtb-synt-desktop'))
        self.assertFalse(sheet.has_item((self.before, self.after), 'rendered/site', 'hike-synt-desktop'))
        self.assertEqual(sheet.guessed_map(self.after, 'rendered/site', 'mtb-synt-desktop'),
                         {'w': 300, 'h': 200, 'png': 'mtb-synt-desktop.webp'})
        page, states = self.sample('site', ['mtb-synt-desktop'])
        self.assertEqual(states, {'mtb-synt-desktop': 'new'})
        self.assertIn('src="after/site/mtb-synt-desktop.webp"', page)
        self.assertIn('aspect-ratio:300/200', page)

    def test_walk_preview(self):
        put(self.dir, 'trips/synt-a/meta 2.json', '{}')
        put(self.dir, '.DS_Store', '')
        put(self.dir, 'trips/synt-c.tmp-99/meta.json', '{}')
        ids, held, skipped = sheet.walk_preview(self.dir)
        self.assertIn('rendered/trips/synt-a/card.svg.html', ids)
        self.assertEqual(ids['rendered/site/meta.json'], sheet.blob_id(b'{"maps": {}}'))
        self.assertFalse([p for p in ids if 'synt-c' in p or ' 2' in p or 'DS_Store' in p])
        self.assertEqual(skipped, 3)
        self.assertIn('rendered/trips/synt-a', held)
        self.assertIn('rendered/site', held)
        self.assertNotIn('rendered/trips/synt-b', held)


class OutFolderTests(unittest.TestCase):

    def test_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(sheet.unsafe_out(os.path.join(tmp, 'new')))
            self.assertIsNone(sheet.unsafe_out(tmp))                                   # empty
            open(os.path.join(tmp, 'a.txt'), 'w').close()
            self.assertIn('not empty', sheet.unsafe_out(tmp))
            open(os.path.join(tmp, sheet.SHEET_MARK), 'w').close()
            self.assertIsNone(sheet.unsafe_out(tmp))                                   # an earlier sheet
            self.assertIn('a file', sheet.unsafe_out(os.path.join(tmp, 'a.txt')))
        self.assertIn('checkout', sheet.unsafe_out(sheet.ROOT))
        self.assertIn('checkout', sheet.unsafe_out(os.path.dirname(sheet.ROOT)))
        self.assertIn('rendered/', sheet.unsafe_out(os.path.join(sheet.ROOT, 'rendered', 'synt')))
        self.assertIsNone(sheet.unsafe_out(os.path.join(sheet.ROOT, '.cache', 'render-sheet-synt-test')))


if __name__ == '__main__':
    unittest.main()
