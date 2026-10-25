"""Phase 4: tools/sitegen/sitecheck.py, the checks `tools/build.py --check` runs on a built folder.

The built folders are made by hand in a temp dir: a few HTML strings with the head core.document writes (spelled out
here, so each rule is tested against fixed text and not against whatever the generator produces today), a sitemap, a
feed, the two search indexes, synthetic GPX files (tests/gpx_fixtures.py) and a matching content folder written with
helpers.make_trip. tiny() is a sound build; a test breaks one thing in it and asserts the whole list check() returns,
so a rule that fired by accident somewhere else fails the test too. The three lines build.check() always printed
(BROKEN, BROKEN ANCHOR, DUPLICATE IDS) are pinned character for character.

GeneratorTests build a real small site with tools/build.py build(): every root it reads or writes (content, rendered,
assets, the output folder, the home manifest) is patched to the temp dir, and sitecheck must find nothing, so the rules
and the generator agree. Nothing here reads or writes content/, rendered/ or _site/ of the checkout (the generator
tests look at _site's timestamp before and after, as a guard), and nothing touches the network. sitecheck is imported
in setUp so a missing module fails each test clearly instead of breaking discovery.
"""
import hashlib
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
from sitegen import core  # noqa: E402
from sitegen import curation  # noqa: E402

import gpx_fixtures as gf  # noqa: E402
import helpers  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

SITE = core.SITE_URL
PHOTO = SITE + 'trips/alpha/photos/01.webp'

# synthetic tracks (an invented spot on open water, see gpx_fixtures): one report, two days of a tour (the second day
# recorded as two tracks), one journal day, and a goal whose file is a planned route without a <trk>
ALPHA_GPX = gf.gpx(gf.trk([gf.SEG_A], 'Alpha ridge'))
DAY1_GPX = gf.gpx(gf.trk([gf.SEG_M1], 'Tour day 1'))
DAY2_GPX = gf.gpx(gf.trk([gf.SEG_M2], 'Tour day 2, morning'), gf.trk([gf.SEG_M3], 'Tour day 2, afternoon'))
JOURNAL_GPX = gf.gpx(gf.trk([gf.SEG_SPARSE], 'Journal day 1'))
GOAL_GPX = gf.ROUTE_ONLY


def load_sitecheck(tc):
    """tools/sitegen/sitecheck.py, or a clear failure of the calling test when it is missing."""
    try:
        return importlib.import_module('sitegen.sitecheck')
    except ImportError as ex:
        tc.fail('tools/sitegen/sitecheck.py is not importable: %s' % ex)


def sha12(data):
    return hashlib.sha256(data.encode('utf-8') if isinstance(data, str) else data).hexdigest()[:12]


def trks(text):
    return re.findall(r'<trk>.*?</trk>', text, flags=re.S)


def combined(title, *sources):
    """A multi-day trip's "Download all GPX" file as build.copy_trip_assets writes it: every <trk> block of every day's
    file, in day order, under a header of its own."""
    blocks = [b for s in sources for b in trks(s)]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="Eric Sichak trip reports" '
            'xmlns="http://www.topografix.com/GPX/1/1">\n<metadata><name>%s</name></metadata>\n%s\n</gpx>\n'
            % (title, '\n'.join(blocks)))


TOUR_GPX = combined('Tour', DAY1_GPX, DAY2_GPX)


# ---------------------------------------------------------------- hand-made pages and site files

def own(rel):
    """A page's own address, as core.document writes its canonical: index.html dropped."""
    folder, name = os.path.split(rel)
    return SITE + ((folder + '/' if folder else '') if name == 'index.html' else rel)


def page(rel, body='', head='', title='A page', description='What the page is about.', canonical=True, robots=None):
    """A page with the head core.document writes: one title, one description, a canonical and og:url that are the
    page's own address (canonical=False: neither, as on the 404 page), `head` appended, and a skip link to #main."""
    canon = ('<link rel="canonical" href="%s">' % own(rel)) if canonical else ''
    og_url = ('<meta property="og:url" content="%s">' % own(rel)) if canonical else ''
    noindex = ('<meta name="robots" content="%s">' % robots) if robots else ''
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>%s</title><meta name="description" content="%s">%s'
            '<meta property="og:type" content="website"><meta property="og:title" content="%s">'
            '<meta property="og:description" content="%s">%s%s%s</head>'
            '<body><a class="skip" href="#main">Skip to content</a><main id="main">%s</main></body></html>\n'
            % (title, description, canon, title, description, og_url, head, noindex, body))


def share(url=PHOTO, width=1600, height=1200, alt='The ridge at dawn'):
    """The share-image tags of contract 4.2, in its order: og:image, then type, width and height, alt, the card."""
    out = '<meta property="og:image" content="%s"><meta property="og:image:type" content="image/webp">' % url
    if width is not None:
        out += '<meta property="og:image:width" content="%d">' % width
    if height is not None:
        out += '<meta property="og:image:height" content="%d">' % height
    return out + ('<meta property="og:image:alt" content="%s"><meta name="twitter:card" content="summary_large_image">'
                  '<meta name="twitter:image:alt" content="%s">' % (alt, alt))


def ld(**over):
    """One structured-data block as core writes it: a BlogPosting, '<' escaped so no title can close the script."""
    d = {'@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': 'Alpha <ridge>', 'url': own('trips/alpha/index.html'),
         'author': {'@type': 'Person', 'name': 'Eric Sichak'}}
    d.update(over)
    return '<script type="application/ld+json">%s</script>' % json.dumps(d, ensure_ascii=False).replace('<', '\\u003c')


ARTICLE = ('<meta property="article:published_time" content="2026-10-03">'
           '<meta property="article:modified_time" content="2026-10-05T18:30:00-07:00">')
# pages a search engine may list, in sitemap order; the helper map page and the 404 page are built but not listed
LISTED = ['index.html', 'about/index.html', 'trips/index.html', 'trips/alpha/index.html', 'trips/tour/index.html',
          'trips/journal/index.html', 'trips/goal/index.html']


def sitemap_xml(urls):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n'
            % ''.join('<url><loc>%s</loc></url>' % u for u in urls))


def feed_item(url, title='A trip', guid=None):
    return ('<item><title>%s</title><link>%s</link><guid>%s</guid><pubDate>Sat, 03 Oct 2026 12:00:00 +0000</pubDate>'
            '<category>Hiking</category><description>Facts.</description></item>' % (title, url, guid or url))


def feed_xml(items):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
            '<title>Trip reports</title><link>%s</link><atom:link href="%sfeed.xml" rel="self" type="application/rss+xml"/>'
            '<description>Trips.</description><language>en-us</language>%s</channel></rss>\n' % (SITE, SITE, ''.join(items)))


def tiny():
    """A small sound build, {path: text}: home, About, the explorer, a report (share photo, publication dates, one
    BlogPosting block, an inline script, a link to another page by its full address), its noindex map helper, a
    multi-day trip, a journal with two day anchors, a goal, the 404 page, and the files beside them."""
    f = {}
    f['index.html'] = page('index.html', (
        '<a href="trips/">Trips</a><a href="about/">About</a><a href="trips/alpha/">Alpha</a>'
        '<img src="trips/alpha/photos/01.webp" srcset="trips/alpha/photos/01.sm.webp 800w, trips/alpha/photos/01.webp 1600w" alt="">'),
        head='<link rel="stylesheet" href="assets/site.css?v=3">')
    f['about/index.html'] = page('about/index.html', '<a href="../">Home</a><a href="../feed.xml">RSS</a><a href="../trips">Trips</a>')
    f['trips/index.html'] = page('trips/index.html', (
        '<a href="alpha/">Alpha</a><a href="tour/">Tour</a><a href="journal/#day-5-2">Day 5.2</a><a href="goal/">Goal</a>'
        '<a href="../#main">Home</a><form id="search" hidden></form><script>document.getElementById("search").hidden=false</script>'))
    f['trips/alpha/index.html'] = page('trips/alpha/index.html', (
        '<h1 id="title">Alpha</h1><a href="#title">Top</a><a href="alpha.gpx" download>Download GPX</a><a href="map/">Map</a>'
        '<a href="%strips/tour/">The tour</a><a href="https://example.test/elsewhere">Elsewhere</a>' % SITE),
        head=share() + ARTICLE + ld())
    f['trips/alpha/map/index.html'] = page('trips/alpha/map/index.html', '<a href="../">Back to the report</a>', robots='noindex')
    f['trips/tour/index.html'] = page('trips/tour/index.html', (
        '<a href="tour.gpx" download>Download all GPX</a><a href="gpx/tour-day-01.gpx">Day 1</a><a href="gpx/tour-day-02.gpx">Day 2</a>'))
    f['trips/journal/index.html'] = page('trips/journal/index.html', (
        '<section id="day-1"><a href="gpx/journal-day-001.gpx">GPX</a></section><section id="day-5-2"></section>'))
    f['trips/goal/index.html'] = page('trips/goal/index.html', '<a href="goal.gpx" download>Download GPX</a>')
    f['404.html'] = page('404.html', '<a href="./">Home</a><a href="trips/">Trips</a>', canonical=False, robots='noindex',
                         head="<base href='/personal-website/'>")
    f['assets/site.css'] = 'body{margin:0}\n'
    f['trips/alpha/photos/01.webp'] = ''
    f['trips/alpha/photos/01.sm.webp'] = ''
    f['trips/alpha/alpha.gpx'] = ALPHA_GPX
    f['trips/tour/tour.gpx'] = TOUR_GPX
    f['trips/tour/gpx/tour-day-01.gpx'] = DAY1_GPX
    f['trips/tour/gpx/tour-day-02.gpx'] = DAY2_GPX
    f['trips/journal/gpx/journal-day-001.gpx'] = JOURNAL_GPX
    f['trips/goal/goal.gpx'] = GOAL_GPX
    f['sitemap.xml'] = sitemap_xml(own(p) for p in LISTED)
    f['feed.xml'] = feed_xml([feed_item(own('trips/alpha/index.html'), 'Alpha'), feed_item(own('trips/tour/index.html'), 'Tour')])
    f['robots.txt'] = 'User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n' % SITE
    f['trips/search.json'] = json.dumps([{'s': 'alpha', 't': 'alpha'}, {'s': 'tour', 't': 'tour'}, {'s': 'journal', 't': 'journal'}])
    f['trips/journal.json'] = json.dumps([{'s': 'journal', 'a': 'day-1', 'n': '1'}, {'s': 'journal', 'a': 'day-5-2', 'n': '5.2'}])
    return f


def write(folder, files):
    """Write {path: text or bytes} under folder."""
    for rel, data in files.items():
        path = os.path.join(folder, *rel.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as fh:
            fh.write(data if isinstance(data, bytes) else data.encode('utf-8'))


def write_text(path, text):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def write_content(trips):
    """The content folder tiny() was 'built' from: the report, the tour (three days, the third without a track), the
    journal, the goal."""
    helpers.make_trip(trips, 'alpha', title='Alpha', track=True)
    helpers.make_trip(trips, 'tour', title='Tour', kind='multi-day', days=[{}, {}, {'track': False}])
    helpers.make_trip(trips, 'journal', title='Journal', kind='series', days=[{'id': '001'}, {'id': '002', 'track': False}])
    helpers.make_trip(trips, 'goal', title='Goal', kind='planned', track=True)
    write_text(os.path.join(trips, 'alpha', 'track.gpx'), ALPHA_GPX)
    write_text(os.path.join(trips, 'tour', 'days', '01.gpx'), DAY1_GPX)
    write_text(os.path.join(trips, 'tour', 'days', '02.gpx'), DAY2_GPX)
    write_text(os.path.join(trips, 'journal', 'days', '001.gpx'), JOURNAL_GPX)
    write_text(os.path.join(trips, 'goal', 'track.gpx'), GOAL_GPX)


def body_add(files, rel, html_):
    """Append to a page's <main>."""
    assert '</main>' in files[rel]
    files[rel] = files[rel].replace('</main>', html_ + '</main>')


def head_add(files, rel, html_):
    assert '</head>' in files[rel]
    files[rel] = files[rel].replace('</head>', html_ + '</head>')


def swap(files, rel, old, new):
    """Replace text that must be there (a fixture that drifted fails here, not in a confusing assertion later)."""
    assert old in files[rel], '%r is not in %s' % (old, rel)
    files[rel] = files[rel].replace(old, new)


class Fixture(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.sc = load_sitecheck(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        self.out = os.path.join(self.tmp, 'site')
        self.trips = os.path.join(self.tmp, 'content', 'trips')
        os.makedirs(self.out)
        os.makedirs(self.trips)

    def put(self, files, keep=False):
        """Write the files as the output folder: a fresh one each time, unless keep (a test that placed symlinks)."""
        if not keep:
            shutil.rmtree(self.out)
            os.makedirs(self.out)
        write(self.out, files)

    def built(self, files, keep=False):
        """The files written to the output folder, read back as sitecheck reads a build."""
        self.put(files, keep)
        return self.sc.read(self.out)

    def check(self, files, content_dir=True):
        """sitecheck.check() over the files, with the matching content folder unless content_dir is False."""
        self.put(files)
        if content_dir and not os.listdir(self.trips):
            write_content(self.trips)
        return self.sc.check(self.out, self.trips if content_dir else None)


# ---------------------------------------------------------------- conflict copies, reading a folder

class ConflictCopyTests(unittest.TestCase):
    COPIES = ('meta 3.json', 'map-wide 4.webp', 'first-tallac-lap 2', 'region-alps-desktop.base 3.svg',
              'region-alps-desktop.svg 4.html', 'index 12.html', 'track 2.gpx', '01 5.md', '01.sm 2.webp',
              'export 2.tar.gz')   # whatever extensions follow the number, as tools/build.py reads these names
    REAL = ('meta.json', 'index.html', '404.html', '3.json', '01.sm.webp', 'back-at-tallac-2026-08-16', 'day-5-2', 'aiare-2',
            'a b.webp', 'photo 2a.webp', ' 3x', 'tour-day-01.gpx', 'day 2 notes.md', 'aiare-2-day-01.gpx')

    def setUp(self):
        self.sc = load_sitecheck(self)

    def test_names_ending_in_a_space_and_a_number_are_conflict_copies(self):
        for name in self.COPIES + ('assets/maps/region-alps-phone 3.webp', 'rendered/trips/first-tallac-lap 2'):
            with self.subTest(name):
                self.assertTrue(self.sc.conflict_copy(name))

    def test_ordinary_names_are_not(self):
        # of a path the last part is the name: a folder that only sits inside a copy is judged where the copy is met
        for name in self.REAL + ('trips/aiare-2/gpx/aiare-2-day-01.gpx', 'trips/first-tallac-lap 2/index.html'):
            with self.subTest(name):
                self.assertFalse(self.sc.conflict_copy(name))

    def test_the_build_leaves_out_the_same_names(self):
        # tools/build.py has a conflict_copy of its own for what it copies; the two must not drift apart
        build = load_build(self)
        if not hasattr(build, 'conflict_copy'):
            self.skipTest('tools/build.py has no conflict_copy')
        for name in self.COPIES + self.REAL:
            with self.subTest(name):
                self.assertEqual(build.conflict_copy(os.path.join('rendered', 'site', name)), self.sc.conflict_copy(name))


class OutputTests(Fixture):

    def test_read_lists_files_folders_and_pages(self):
        out = self.built({'index.html': page('index.html'), 'trips/alpha/index.html': page('trips/alpha/index.html'),
                          'trips/alpha/alpha.gpx': ALPHA_GPX, '404.html': page('404.html'), 'assets/site.css': '', '.nojekyll': ''})
        self.assertEqual(out.files, {'index.html', 'trips/alpha/index.html', 'trips/alpha/alpha.gpx', '404.html',
                                     'assets/site.css', '.nojekyll'})
        self.assertEqual(out.dirs, {'', 'trips', 'trips/alpha', 'assets'})
        self.assertEqual(out.pages, ['404.html', 'index.html', 'trips/alpha/index.html'])   # sorted by path
        self.assertEqual(out.out_dir, self.out)
        self.assertEqual(out.text('index.html'), page('index.html'))
        self.assertEqual(out.data('trips/alpha/alpha.gpx'), ALPHA_GPX.encode('utf-8'))
        self.assertEqual(out.ids('index.html'), {'main'})

    def test_conflict_copies_are_not_part_of_the_build(self):
        out = self.built({'index.html': page('index.html'), 'index 2.html': '<a href="nowhere/">',
                          'assets/meta 3.json': '{}', 'assets/maps/region-alps-phone 4.webp': '',
                          'trips/alpha 2/index.html': '<a href="nowhere/">', 'trips/alpha 2/photos/01.webp': ''})
        self.assertEqual(out.files, {'index.html'})
        self.assertEqual(out.dirs, {'', 'assets', 'assets/maps', 'trips'})
        self.assertEqual(out.pages, ['index.html'])

    def test_symlinks_are_followed_and_a_dangling_one_is_no_file(self):
        # a build made with --link: photos and tracks are links into the content folder
        src = os.path.join(self.tmp, 'content-photos')
        write(src, {'01.webp': 'x', 'more/02.webp': 'y'})
        write(self.out, {'index.html': page('index.html')})
        os.symlink(os.path.join(src, '01.webp'), os.path.join(self.out, 'photo.webp'))
        os.symlink(os.path.join(src, 'more'), os.path.join(self.out, 'more'))
        os.symlink(os.path.join(src, 'gone.webp'), os.path.join(self.out, 'gone.webp'))
        out = self.sc.read(self.out)
        self.assertEqual(out.files, {'index.html', 'photo.webp', 'more/02.webp'})
        self.assertEqual(out.dirs, {'', 'more'})
        self.assertEqual(out.data('photo.webp'), b'x')

    def test_a_link_back_up_the_tree_does_not_loop(self):
        write(self.out, {'index.html': page('index.html'), 'a/b/c.txt': ''})
        os.symlink(self.out, os.path.join(self.out, 'a', 'b', 'top'))
        os.symlink(os.path.join(self.out, 'a'), os.path.join(self.out, 'a', 'b', 'up'))
        out = self.sc.read(self.out)
        self.assertEqual(out.files, {'index.html', 'a/b/c.txt'})

    def test_two_links_to_one_folder_are_both_part_of_the_build(self):
        src = os.path.join(self.tmp, 'shared')
        write(src, {'01.webp': 'x'})
        write(self.out, {'index.html': page('index.html', '<img src="one/01.webp" alt=""><img src="two/01.webp" alt="">')})
        os.symlink(src, os.path.join(self.out, 'one'))
        os.symlink(src, os.path.join(self.out, 'two'))
        out = self.sc.read(self.out)
        self.assertEqual(out.files, {'index.html', 'one/01.webp', 'two/01.webp'})
        self.assertEqual(self.sc.links(out), [])

    def test_pages_skip_dot_folders_and_dot_files(self):
        # as glob('**/*.html') listed them for the old check; the files are still there for a link to find
        out = self.built({'index.html': page('index.html'), '.cache/index.html': '<a href="x/">', '.draft.html': '<a href="x/">'})
        self.assertEqual(out.pages, ['index.html'])
        self.assertIn('.cache/index.html', out.files)
        self.assertFalse([ln for ln in self.sc.check(self.out) if '.cache' in ln or '.draft' in ln])

    def test_a_missing_folder_is_an_oserror(self):
        with self.assertRaises(OSError):
            self.sc.read(os.path.join(self.tmp, 'no-such-folder'))
        with self.assertRaises(OSError):
            self.sc.check(os.path.join(self.tmp, 'no-such-folder'))

    def test_of_holds_a_site_in_memory(self):
        out = self.sc.of({'index.html': page('index.html', '<a href="a/x.gpx">x</a><a href="b/">b</a>'), 'index 2.html': 'copy',
                          'trips/alpha 2/index.html': 'inside a copy'},
                         files={'a/x.gpx': b'<gpx/>', 'feed.xml': '<rss/>', 'a/x 3.gpx': b''})
        self.assertEqual(out.files, {'index.html', 'a/x.gpx', 'feed.xml'})
        self.assertEqual(out.dirs, {'', 'a'})
        self.assertEqual(out.pages, ['index.html'])
        self.assertIsNone(out.out_dir)
        self.assertIsNone(out.path('index.html'))
        self.assertEqual(out.data('a/x.gpx'), b'<gpx/>')
        self.assertEqual(out.data('feed.xml'), b'<rss/>')
        self.assertEqual(self.sc.links(out), ['BROKEN index.html -> b/'])
        names_only = self.sc.of({'index.html': page('index.html', '<a href="a/x.gpx">x</a>')}, files=['a/x.gpx'])
        self.assertEqual(names_only.files, {'index.html', 'a/x.gpx'})
        self.assertEqual(self.sc.links(names_only), [])
        as_bytes = self.sc.of({'index.html': page('index.html', '<a href="a/">é</a>').encode('utf-8')})
        self.assertEqual(self.sc.links(as_bytes), ['BROKEN index.html -> a/'])

    def test_every_rule_takes_a_folder_or_an_output(self):
        files = tiny()
        swap(files, 'index.html', 'href="about/"', 'href="aboot/"')
        write(self.out, files)
        write_content(self.trips)
        out = self.sc.read(self.out)
        for rule in (self.sc.links, self.sc.anchors, self.sc.duplicate_ids, self.sc.metadata, self.sc.sitemap,
                     self.sc.feed, self.sc.indexes):
            with self.subTest(rule.__name__):
                self.assertEqual(rule(self.out), rule(out))
        self.assertEqual(self.sc.gpx(self.out, self.trips), self.sc.gpx(out, self.trips))
        self.assertEqual(self.sc.links(self.out), ['BROKEN index.html -> aboot/'])

    def test_a_page_address_drops_index_html_and_only_that(self):
        out = self.sc.of({'index.html': '', 'trips/alpha/index.html': '', 'about.html': '', 'trips/myindex.html': '', '404.html': ''})
        self.assertEqual(out.url_of('index.html'), SITE)
        self.assertEqual(out.url_of('trips/alpha/index.html'), SITE + 'trips/alpha/')
        self.assertEqual(out.url_of('about.html'), SITE + 'about.html')
        self.assertEqual(out.url_of('trips/myindex.html'), SITE + 'trips/myindex.html')
        self.assertEqual(out.page_at(SITE), 'index.html')
        self.assertEqual(out.page_at(SITE + 'trips/alpha/'), 'trips/alpha/index.html')
        self.assertEqual(out.page_at(SITE + 'about.html'), 'about.html')
        for other in (SITE + 'trips/alpha', SITE + 'trips/alpha/index.html', SITE + 'index.html', SITE + 'trips/beta/',
                      'https://example.test/trips/alpha/', 'trips/alpha/', ''):
            with self.subTest(other):
                self.assertIsNone(out.page_at(other))

    def test_the_site_address_is_core_site_url_unless_given(self):
        self.assertEqual(self.sc.of({}).site_url, core.SITE_URL)
        with mock.patch.object(core, 'SITE_URL', 'https://example.test/moved/'):
            self.assertEqual(self.sc.of({}).site_url, 'https://example.test/moved/')
            write(self.out, {'index.html': ''})
            self.assertEqual(self.sc.read(self.out).site_url, 'https://example.test/moved/')
        given = self.sc.read(self.out, site_url='https://example.test/given/')
        self.assertEqual(given.url_of('index.html'), 'https://example.test/given/')
        files = {'index.html': page('index.html'), 'sitemap.xml': sitemap_xml([SITE]), 'feed.xml': feed_xml([])}
        write(self.out, files)
        self.assertEqual(self.sc.check(self.out), [])
        moved = 'https://example.test/given/'
        self.assertEqual(self.sc.check(self.out, site_url=moved),
                         ['META index.html: canonical is %s (expected %s)' % (SITE, moved),
                          'META index.html: og:url is %s (expected %s)' % (SITE, moved),
                          'SITEMAP sitemap.xml: %s is not listed' % moved,
                          'SITEMAP sitemap.xml: %s is not the address of a page of this build' % SITE])


# ---------------------------------------------------------------- the three lines build.check() always printed

class LinkTests(Fixture):

    def lines(self, body, rel='index.html', files=None, keep=False):
        """links() for one page with this body, beside a home page, an About page with two ids, and a few files."""
        f = {'index.html': page('index.html'), 'about/index.html': page('about/index.html', '<h2 id="day-1">Day</h2><h2 id="région">R</h2>'),
             'assets/site.css': '', 'trips/alpha/photos/01.webp': '', 'trips/alpha/photos/01.sm.webp': '', 'trips/alpha/alpha.gpx': ''}
        f.update(files or {})
        f[rel] = page(rel, body)
        return self.sc.links(self.built(f, keep), rel)

    def test_a_broken_link_is_one_line_naming_the_page_and_the_reference_as_written(self):
        self.assertEqual(self.lines('<a href="aboot/">About</a>'), ['BROKEN index.html -> aboot/'])
        self.assertEqual(self.lines('<img src="../alpha/photos/zz.webp?v=2" alt="">', rel='trips/beta/index.html'),
                         ['BROKEN trips/beta/index.html -> ../alpha/photos/zz.webp?v=2'])
        self.assertEqual(self.lines('<a href="about/missing.html#top">x</a>'), ['BROKEN index.html -> about/missing.html#top'])

    def test_links_that_resolve_give_no_line(self):
        self.assertEqual(self.lines('<a href="about/">a</a><a href="about">b</a><a href="about/index.html">c</a><a href="./">d</a>'
                                    '<a href="./about/../index.html">e</a><link rel="stylesheet" href="assets/site.css?v=3">'
                                    '<a href="trips/alpha/alpha.gpx" download>f</a><img src="trips/alpha/photos/01.webp" alt="">'), [])
        self.assertEqual(self.lines('<a href="../../">home</a><a href="../../about/">a</a><a href="alpha.gpx">g</a>'
                                    '<img src="photos/01.webp" alt="">', rel='trips/alpha/index.html'), [])

    def test_a_folder_stands_for_its_index_page(self):
        # assets/ has no index.html: a link to the folder goes nowhere
        self.assertEqual(self.lines('<a href="assets/">files</a><a href="trips/alpha/">no page here</a>'),
                         ['BROKEN index.html -> assets/', 'BROKEN index.html -> trips/alpha/'])

    def test_every_srcset_candidate_is_checked(self):
        self.assertEqual(self.lines('<img src="trips/alpha/photos/01.webp" alt="" '
                                    'srcset="trips/alpha/photos/01.th.webp 427w, trips/alpha/photos/01.sm.webp 800w, '
                                    'trips/alpha/photos/01.webp 1600w">'),
                         ['BROKEN index.html -> trips/alpha/photos/01.th.webp'])
        # a preload's imagesrcset is read too, with or without a space after the comma
        self.assertEqual(self.lines('<link rel="preload" as="image" href="trips/alpha/photos/01.webp" '
                                    'imagesrcset="trips/alpha/photos/01.sm.webp 800w,trips/alpha/photos/02.webp 1600w">'),
                         ['BROKEN index.html -> trips/alpha/photos/02.webp'])
        self.assertEqual(self.lines('<img data-src="lazy.webp" alt="">'), ['BROKEN index.html -> lazy.webp'])
        # ... and a <source>'s: the phone-only source of a card cover (contract-phase4.md 10.5) names the card-size copy
        # nothing else names, so this is the only rule that notices the file missing
        picture = ('<picture class="cover-pic"><source media="(max-width: 559.98px)" srcset="trips/alpha/photos/01.th.webp 427w, '
                   'trips/alpha/photos/01.sm.webp 800w, trips/alpha/photos/01.webp 1600w" sizes="106px">'
                   '<img class="cover-img" src="trips/alpha/photos/01.webp" srcset="trips/alpha/photos/01.sm.webp 800w, '
                   'trips/alpha/photos/01.webp 1600w" sizes="(min-width: 560px) 400px, 112px" alt=""></picture>')
        self.assertEqual(self.lines(picture), ['BROKEN index.html -> trips/alpha/photos/01.th.webp'])
        self.assertEqual(self.lines(picture, files={'trips/alpha/photos/01.th.webp': ''}), [])

    def test_a_value_without_a_space_is_one_reference(self):
        # only a value with a space is read as a srcset; a comma alone does not split it
        self.assertEqual(self.lines('<a href="a,b.html">x</a>', files={'a,b.html': page('a,b.html')}), [])
        self.assertEqual(self.lines('<a href="a,c.html">x</a>'), ['BROKEN index.html -> a,c.html'])

    def test_what_is_never_followed(self):
        self.assertEqual(self.lines(
            '<a href="https://example.test/x">a</a><a href="http://example.test/">b</a><a href="mailto:eric@example.test">c</a>'
            '<img src="data:image/png;base64,AAAA" alt=""><a href="javascript:void(0)">d</a><a href="#nowhere">e</a>'
            '<a href="?q=1">f</a><a href="">g</a>' "<base href='/personal-website/'><a href='missing/'>single-quoted</a>"), [])
        # a query or a fragment alone names the page itself, also where its folder has no index page
        self.assertEqual(self.lines('<a href="?q=1">f</a><a href="#nowhere">e</a><a href="?q=1#x">h</a>', rel='trips/alpha/other.html'), [])

    def test_a_reference_is_taken_as_written(self):
        # no percent-decoding and no entity decoding of the path: the file must be named as the reference is spelled
        self.assertEqual(self.lines('<a href="p%20q.html">x</a>', files={'p q.html': page('p q.html')}),
                         ['BROKEN index.html -> p%20q.html'])
        self.assertEqual(self.lines('<a href="p%20q.html">x</a>', files={'p%20q.html': page('p%20q.html')}), [])

    def test_a_link_into_another_page_needs_the_id_there(self):
        self.assertEqual(self.lines('<a href="about/#day-1">ok</a><a href="about/#day-2">no</a><a href="about/index.html#gone">no</a>'),
                         ['BROKEN ANCHOR index.html -> about/#day-2', 'BROKEN ANCHOR index.html -> about/index.html#gone'])
        self.assertEqual(self.lines('<a href="../../about/?x=1#nope">no</a>', rel='trips/alpha/index.html'),
                         ['BROKEN ANCHOR trips/alpha/index.html -> ../../about/?x=1#nope'])

    def test_the_fragment_of_a_link_is_percent_decoded(self):
        self.assertEqual(self.lines('<a href="about/#day%2D1">a</a><a href="about/#r%C3%A9gion">b</a><a href="about/#day%2D2">c</a>'),
                         ['BROKEN ANCHOR index.html -> about/#day%2D2'])

    def test_a_fragment_on_a_file_that_is_not_a_page_is_not_looked_up(self):
        self.assertEqual(self.lines('<a href="trips/alpha/alpha.gpx#anything">x</a><a href="about/#">empty</a>'), [])

    def test_every_occurrence_is_a_line_in_page_order(self):
        self.assertEqual(self.lines('<a href="zz/">1</a><a href="about/#no">2</a><a href="yy.html">3</a><a href="zz/">4</a>'
                                    '<a href="about/#no">5</a>'),
                         ['BROKEN index.html -> zz/', 'BROKEN ANCHOR index.html -> about/#no', 'BROKEN index.html -> yy.html',
                          'BROKEN index.html -> zz/', 'BROKEN ANCHOR index.html -> about/#no'])

    def test_an_address_under_the_site_url_is_followed_like_a_relative_one(self):
        self.assertEqual(self.lines('<a href="%sabout/">a</a><a href="%s">home</a><a href="%sabout/#day-1">d</a>'
                                    '<img src="%strips/alpha/photos/01.webp" alt=""><a href="%sassets/site.css?v=1">c</a>'
                                    % (SITE, SITE, SITE, SITE, SITE), rel='trips/alpha/index.html'), [])
        self.assertEqual(self.lines('<a href="%strips/zz/">a</a><a href="%sabout/#day-9">b</a><a href="%sassets/">c</a>'
                                    % (SITE, SITE, SITE), rel='trips/alpha/index.html'),
                         ['BROKEN trips/alpha/index.html -> %strips/zz/' % SITE,
                          'BROKEN ANCHOR trips/alpha/index.html -> %sabout/#day-9' % SITE,
                          'BROKEN trips/alpha/index.html -> %sassets/' % SITE])
        # resolved from the site root, not from the page's own folder
        self.assertEqual(self.lines('<a href="%sphotos/01.webp">x</a>' % SITE, rel='trips/alpha/index.html'),
                         ['BROKEN trips/alpha/index.html -> %sphotos/01.webp' % SITE])
        # another site, and the same host by another scheme or without the site's path, stay out of it
        elsewhere = SITE.replace('https:', 'http:') + 'trips/zz/'
        self.assertEqual(self.lines('<a href="%s">x</a><a href="https://example.test/trips/zz/">y</a>' % elsewhere), [])

    def test_a_path_that_leaves_the_site_is_broken(self):
        self.assertEqual(self.lines('<a href="/personal-website/about/">a</a><a href="../about/">b</a>'
                                    '<a href="//example.test/x.js">c</a><a href="about/../../x">d</a>'),
                         ['BROKEN index.html -> /personal-website/about/', 'BROKEN index.html -> ../about/',
                          'BROKEN index.html -> //example.test/x.js', 'BROKEN index.html -> about/../../x'])
        # even when the file system has something there: the folder above the build is not the site
        write(self.tmp, {'outside.html': page('outside.html')})
        self.assertEqual(self.lines('<a href="../outside.html">x</a>'), ['BROKEN index.html -> ../outside.html'])

    def test_a_reference_must_match_the_file_name_exactly(self):
        # a Mac's file system ignores case; the web server (and CI) does not
        self.assertEqual(self.lines('<a href="About/">a</a><img src="trips/alpha/photos/01.WEBP" alt="">'),
                         ['BROKEN index.html -> About/', 'BROKEN index.html -> trips/alpha/photos/01.WEBP'])

    def test_linked_files_resolve_and_a_dangling_link_is_broken(self):
        src = os.path.join(self.tmp, 'content-photos')
        write(src, {'02.webp': 'x'})
        os.symlink(os.path.join(src, '02.webp'), os.path.join(self.out, '02.webp'))
        os.symlink(os.path.join(src, '03.webp'), os.path.join(self.out, '03.webp'))
        self.assertEqual(self.lines('<img src="02.webp" alt=""><img src="03.webp" alt="">', keep=True),
                         ['BROKEN index.html -> 03.webp'])


class AnchorTests(Fixture):

    def lines(self, body):
        return self.sc.anchors(self.built({'index.html': page('index.html', body)}))

    def test_a_same_page_link_needs_its_id(self):
        self.assertEqual(self.lines('<a href="#top">a</a><h2 id="top">T</h2><a href="#main">b</a>'), [])
        self.assertEqual(self.lines('<a href="#gone">a</a>'), ['BROKEN ANCHOR index.html -> #gone'])

    def test_every_occurrence_is_a_line_in_page_order(self):
        self.assertEqual(self.lines('<a href="#b">1</a><a href="#a">2</a><h2 id="ok">x</h2><a href="#ok">3</a><a href="#b">4</a>'),
                         ['BROKEN ANCHOR index.html -> #b', 'BROKEN ANCHOR index.html -> #a', 'BROKEN ANCHOR index.html -> #b'])

    def test_the_fragment_is_compared_as_written(self):
        # unlike a link to another page, a same-page fragment is not percent-decoded
        self.assertEqual(self.lines('<h2 id="day-1">D</h2><a href="#day%2D1">x</a>'), ['BROKEN ANCHOR index.html -> #day%2D1'])

    def test_any_attribute_ending_in_href_counts(self):
        self.assertEqual(self.lines('<svg><use xlink:href="#sym"/></svg><button data-href="#panel">x</button><div id="panel"></div>'),
                         ['BROKEN ANCHOR index.html -> #sym'])


class DuplicateIdTests(Fixture):

    def lines(self, body, rel='index.html'):
        return self.sc.duplicate_ids(self.built({rel: page(rel, body)}))

    def test_an_id_used_twice_is_one_line(self):
        self.assertEqual(self.lines('<h2 id="map">a</h2><div id="map"></div>'), ['DUPLICATE IDS index.html: map'])
        self.assertEqual(self.lines('<h2 id="main">again</h2>', rel='trips/alpha/index.html'),
                         ['DUPLICATE IDS trips/alpha/index.html: main'])
        self.assertEqual(self.lines('<h2 id="map">a</h2><div id="Map"></div><p id="map2"></p>'), [])

    def test_one_line_per_page_with_the_first_six_ids_sorted(self):
        body = ''.join('<i id="%s"></i>' % i for i in 'hgfedcba') * 2 + '<b id="once"></b>'
        self.assertEqual(self.lines(body), ['DUPLICATE IDS index.html: a, b, c, d, e, f'])
        self.assertEqual(self.lines('<i id="z"></i><i id="y"></i><i id="z"></i><i id="y"></i><i id="z"></i>'),
                         ['DUPLICATE IDS index.html: y, z'])

    def test_an_attribute_that_only_ends_in_id_is_not_an_id(self):
        self.assertEqual(self.lines('<div id="a" uuid="a" grid="a" data-uid="a"></div>'), [])


# ---------------------------------------------------------------- ARIA-REF and HEADING (Phase 8)

class AriaTests(Fixture):

    def lines(self, body, rel='index.html', head=''):
        return self.sc.aria(self.built({rel: page(rel, body, head=head)}))

    def test_every_aria_reference_names_an_id_of_the_page(self):
        self.assertEqual(self.lines('<h1 id="t">T</h1><p id="m">M</p><a aria-describedby="m" aria-labelledby="t m">x</a>'
                                    '<button aria-controls="panel">Show</button><div id="panel" hidden></div>'), [])
        self.assertEqual(self.lines('<h1>T</h1><button aria-controls="nopanel">Show</button>'
                                    '<a aria-labelledby="t gone" aria-describedby="">x</a><h2 id="t">t</h2>'),
                         ['ARIA-REF index.html: aria-controls="nopanel" names no id on the page',
                          'ARIA-REF index.html: aria-labelledby="gone" names no id on the page'])

    def test_a_tab_whose_panel_becomes_a_tabpanel_only_with_the_script_is_sound(self):
        # map/'s region tabs: the panel is a plain section with the id until archive.js gives it role="tabpanel"
        self.assertEqual(self.lines('<h1>Map</h1><div role="tablist"><button role="tab" id="t-a" aria-controls="region-a">A</button></div>'
                                    '<section id="region-a"><h2>A</h2></section>'), [])

    def test_a_heading_level_may_go_up_one_and_down_any_number(self):
        self.assertEqual(self.lines('<h1>A</h1><h2>B</h2><h3>C</h3><h4>D</h4><h2>E</h2><h3>F</h3><h2>G</h2>'), [])

    def test_a_skipped_level_inside_main_is_one_line_with_its_words(self):
        self.assertEqual(self.lines('<h1>Trip</h1><h2>Photos</h2><h4 class="t-h3">The <b>ridge</b>  at dawn</h4>'),
                         ['HEADING index.html: h4 after h2 ("The ridge at dawn")'])
        self.assertEqual(self.lines('<h2>Opens the page</h2>'), ['HEADING index.html: h2 is the first heading ("Opens the page")'])

    def test_headings_above_main_set_where_main_starts(self):
        # the title above <main> (a site header's own h1 would be one): <main> may then open with an h2
        html_ = page('index.html', '<h2>In main</h2>').replace('<main id="main">', '<h1>Above</h1><main id="main">')
        self.assertEqual(self.sc.aria(self.built({'index.html': html_})), [])
        # headings outside <main> are never judged themselves
        html_ = page('index.html', '<h1>In main</h1>').replace('</main>', '</main><footer><h4>Footer</h4></footer>')
        self.assertEqual(self.sc.aria(self.built({'index.html': html_})), [])

    def test_the_sound_build_has_neither(self):
        self.assertEqual(self.sc.aria(self.built(tiny())), [])


# ---------------------------------------------------------------- META

class MetadataTests(Fixture):

    def meta(self, files):
        return self.sc.metadata(self.built(files))

    def one(self, rel='about/index.html', **kw):
        """metadata() of one hand-made page."""
        return self.meta({rel: page(rel, **kw)})

    def test_the_sound_build_has_no_lines(self):
        # the report page carries og:image:type / :width / :height / :alt, twitter:image:alt, article:published_time and
        # article:modified_time, one BlogPosting block and an inline script: all allowed
        self.assertEqual(self.meta(tiny()), [])

    def test_exactly_one_title(self):
        files = {'about/index.html': page('about/index.html').replace('<title>A page</title>', '')}
        self.assertEqual(self.meta(files), ['META about/index.html: 0 <title> elements in the head (expected 1)'])
        self.assertEqual(self.one(head='<title>Another</title>'), ['META about/index.html: 2 <title> elements in the head (expected 1)'])

    def test_a_title_in_the_body_is_not_the_page_title(self):
        svg = '<svg role="img"><title>Elevation profile</title><desc>d</desc></svg>'
        self.assertEqual(self.one(body=svg), [])
        files = {'about/index.html': page('about/index.html', svg).replace('<title>A page</title>', '')}
        self.assertEqual(self.meta(files), ['META about/index.html: 0 <title> elements in the head (expected 1)'])

    def test_exactly_one_description(self):
        files = {'about/index.html': page('about/index.html').replace('<meta name="description" content="What the page is about.">', '')}
        self.assertEqual(self.meta(files), ['META about/index.html: 0 meta description tags (expected 1)'])
        self.assertEqual(self.one(head='<meta content="Again." name="description">'),
                         ['META about/index.html: 2 meta description tags (expected 1)'])
        # og:description and twitter:description are other tags; the name itself is not case-sensitive in HTML
        self.assertEqual(self.one(head='<meta name="twitter:description" content="x">'), [])
        self.assertEqual(self.one(head='<META NAME="Description" CONTENT="Again.">'),
                         ['META about/index.html: 2 meta description tags (expected 1)'])

    def test_one_canonical_that_is_the_page_address(self):
        rel = 'trips/alpha/index.html'
        url = SITE + 'trips/alpha/'
        missing = {rel: page(rel).replace('<link rel="canonical" href="%s">' % url, '')}
        self.assertEqual(self.meta(missing), ['META %s: 0 canonical links (expected 1)' % rel])
        self.assertEqual(self.one(rel, head='<link href="%s" rel="canonical">' % url), ['META %s: 2 canonical links (expected 1)' % rel])
        # other links in a head are not canonicals (every real page has the feed's alternate link and a stylesheet)
        self.assertEqual(self.one(rel, head='<link rel="alternate" type="application/rss+xml" href="../../feed.xml">'
                                            '<link rel="stylesheet" href="../../assets/site.css"><link rel="icon" href="x.svg">'), [])
        for wrong in (SITE, url + 'index.html', SITE + 'trips/alpha', 'trips/alpha/', url.replace('https:', 'http:'), url + '?ref=1'):
            with self.subTest(wrong):
                files = {rel: page(rel).replace('<link rel="canonical" href="%s">' % url, '<link rel="canonical" href="%s">' % wrong)}
                self.assertEqual(self.meta(files), ['META %s: canonical is %s (expected %s)' % (rel, wrong, url)])

    def test_one_og_url_equal_to_the_canonical(self):
        rel = 'trips/alpha/index.html'
        url = SITE + 'trips/alpha/'
        tag = '<meta property="og:url" content="%s">' % url
        self.assertEqual(self.meta({rel: page(rel).replace(tag, '')}), ['META %s: 0 og:url tags (expected 1)' % rel])
        self.assertEqual(self.one(rel, head=tag), ['META %s: 2 og:url tags (expected 1)' % rel])
        self.assertEqual(self.meta({rel: page(rel).replace(tag, tag.replace(url, SITE))}),
                         ['META %s: og:url is %s (expected %s)' % (rel, SITE, url)])

    def test_the_home_page_and_a_page_that_is_not_an_index(self):
        self.assertEqual(self.meta({'index.html': page('index.html'), 'about.html': page('about.html'),
                                    'trips/myindex.html': page('trips/myindex.html')}), [])
        files = {'about.html': page('about/index.html')}   # a head that names about/ on the file about.html
        self.assertEqual(self.meta(files), ['META about.html: canonical is %sabout/ (expected %sabout.html)' % (SITE, SITE),
                                            'META about.html: og:url is %sabout/ (expected %sabout.html)' % (SITE, SITE)])

    def test_the_404_page_has_no_canonical_no_og_url_and_is_noindex(self):
        sound = page('404.html', canonical=False, robots='noindex', head="<base href='/personal-website/'>")
        self.assertEqual(self.meta({'404.html': sound}), [])
        # the page built like any other would name the home page as its canonical
        self.assertEqual(self.meta({'404.html': page('404.html').replace(SITE + '404.html', SITE)}),
                         ['META 404.html: the 404 page has a canonical link (%s)' % SITE,
                          'META 404.html: the 404 page has an og:url (%s)' % SITE,
                          'META 404.html: the 404 page is not noindex'])
        self.assertEqual(self.meta({'404.html': page('404.html', canonical=False)}), ['META 404.html: the 404 page is not noindex'])
        self.assertEqual(self.meta({'404.html': page('404.html', canonical=False, robots='NOINDEX, nofollow')}), [])
        self.assertEqual(self.meta({'404.html': page('404.html', canonical=False, robots='none')}), [])   # noindex, nofollow
        # only the page at the site root is the 404 page GitHub Pages serves
        self.assertEqual(self.meta({'trips/404.html': page('trips/404.html')}), [])
        self.assertEqual(self.meta({'404.html': page('404.html', canonical=False, robots='index,follow')}),
                         ['META 404.html: the 404 page is not noindex'])

    def test_a_noindex_helper_page_keeps_its_own_canonical(self):
        rel = 'trips/alpha/map/index.html'
        self.assertEqual(self.one(rel, robots='noindex'), [])
        missing = {rel: page(rel, robots='noindex').replace('<link rel="canonical" href="%strips/alpha/map/">' % SITE, '')}
        self.assertEqual(self.meta(missing), ['META %s: 0 canonical links (expected 1)' % rel])

    def test_a_share_image_is_one_absolute_address_whose_file_is_built(self):
        rel = 'trips/alpha/index.html'
        photo = {'trips/alpha/photos/01.webp': '', 'trips/alpha/photos/02.webp': ''}

        def lines(head, files=photo):
            f = dict(files)
            f[rel] = page(rel, head=head)
            return self.meta(f)

        self.assertEqual(lines(share()), [])
        self.assertEqual(lines('<meta content="%s" property="og:image">' % PHOTO), [])   # attribute order is free
        self.assertEqual(lines(share(PHOTO.replace('01', '09'))),
                         ['META %s: og:image file is not in the build: %strips/alpha/photos/09.webp' % (rel, SITE)])
        self.assertEqual(lines(share('photos/01.webp')),
                         ['META %s: og:image is not an absolute URL under %s: photos/01.webp' % (rel, SITE)])
        self.assertEqual(lines(share('https://example.test/trips/alpha/photos/01.webp')),
                         ['META %s: og:image is not an absolute URL under %s: https://example.test/trips/alpha/photos/01.webp' % (rel, SITE)])
        self.assertEqual(lines(share(SITE + 'trips/alpha/photos/')),   # a folder is not an image
                         ['META %s: og:image file is not in the build: %strips/alpha/photos/' % (rel, SITE)])
        self.assertEqual(lines(share(SITE + 'trips/alpha/')),          # nor is the page itself, by its address
                         ['META %s: og:image file is not in the build: %strips/alpha/' % (rel, SITE)])
        two = share() + '<meta property="og:image" content="%s">' % PHOTO.replace('01', '02')
        self.assertEqual(lines(two), ['META %s: 2 og:image tags (expected at most 1)' % rel])
        self.assertEqual(lines(two.replace('02', '03')),
                         ['META %s: 2 og:image tags (expected at most 1)' % rel,
                          'META %s: og:image file is not in the build: %strips/alpha/photos/03.webp' % (rel, SITE)])
        # a conflict copy is not a file of the build
        copy = SITE + 'trips/alpha/photos/01 2.webp'
        self.assertEqual(lines(share(copy), {'trips/alpha/photos/01 2.webp': ''}),
                         ['META %s: og:image file is not in the build: %s' % (rel, copy)])

    def test_share_image_width_and_height_come_together(self):
        rel = 'trips/alpha/index.html'
        photo = {'trips/alpha/photos/01.webp': ''}

        def lines(**kw):
            f = dict(photo)
            f[rel] = page(rel, head=share(**kw))
            return self.meta(f)

        self.assertEqual(lines(), [])
        self.assertEqual(lines(width=None, height=None), [])
        self.assertEqual(lines(height=None), ['META %s: og:image:width without og:image:height' % rel])
        self.assertEqual(lines(width=None), ['META %s: og:image:height without og:image:width' % rel])

    def test_at_most_one_structured_data_block_and_it_is_a_blog_posting(self):
        rel = 'trips/alpha/index.html'
        self.assertEqual(self.one(rel, head=ld()), [])
        self.assertEqual(self.one(rel, head=ld() + ld()), ['META %s: 2 application/ld+json blocks (expected at most 1)' % rel])
        # wherever the second one stands
        self.assertEqual(self.one(rel, head=ld(), body=ld()), ['META %s: 2 application/ld+json blocks (expected at most 1)' % rel])
        single = "<script type='application/ld+json'>%s</script>"   # however the type is quoted
        self.assertEqual(self.one(rel, body=single % json.dumps({'@type': 'BlogPosting'})), [])
        self.assertEqual(self.one(rel, body=single % json.dumps({'@type': 'Recipe'})),
                         ['META %s: application/ld+json @type is "Recipe" (expected BlogPosting)' % rel])
        self.assertEqual(self.one(rel, head=ld(**{'@type': 'Article'})),
                         ['META %s: application/ld+json @type is "Article" (expected BlogPosting)' % rel])
        untyped = '<script type="application/ld+json">{"headline": "x"}</script>'
        self.assertEqual(self.one(rel, head=untyped), ['META %s: application/ld+json @type is null (expected BlogPosting)' % rel])
        listed = '<script type="application/ld+json">[{"@type": "BlogPosting"}]</script>'
        self.assertEqual(self.one(rel, head=listed), ['META %s: application/ld+json @type is null (expected BlogPosting)' % rel])
        self.assertEqual(self.one(rel, head=ld() + ld(**{'@type': 'FAQPage'})),
                         ['META %s: 2 application/ld+json blocks (expected at most 1)' % rel,
                          'META %s: application/ld+json @type is "FAQPage" (expected BlogPosting)' % rel])

    def test_a_structured_data_block_must_be_json(self):
        rel = 'trips/alpha/index.html'
        lines = self.one(rel, head='<script type="application/ld+json">{"@type": "BlogPosting",}</script>')
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith('META %s: application/ld+json is not valid JSON (' % rel), lines[0])
        self.assertTrue(lines[0].endswith(')'))

    def test_a_title_inside_the_structured_data_does_not_count(self):
        # core writes '<' as <; even unescaped, a script's text is not markup
        raw = '<script type="application/ld+json">{"@type": "BlogPosting", "headline": "<title>x</title>"}</script>'
        self.assertEqual(self.one('trips/alpha/index.html', head=raw), [])
        self.assertEqual(self.one('trips/alpha/index.html', head=ld(headline='</script><title>T</title>')), [])

    def test_other_scripts_are_not_structured_data(self):
        body = ('<script>try{if(localStorage.getItem("units")==="km")document.documentElement.classList.add("km")}catch(e){}</script>'
                '<script type="application/json">{"@type": "Thing"}</script><script src="x.js" defer></script>')
        self.assertEqual(self.sc.metadata(self.sc.of({'index.html': page('index.html', body)})), [])

    def test_a_page_without_a_head(self):
        self.assertEqual(self.meta({'frag.html': '<p>A stray fragment.</p>'}), ['META frag.html: no <head> element'])
        self.assertEqual(self.meta({'frag.html': '<p>x</p>' + ld() + ld()}),
                         ['META frag.html: no <head> element', 'META frag.html: 2 application/ld+json blocks (expected at most 1)'])

    def test_lines_come_in_rule_order_page_by_page(self):
        files = {'b/index.html': page('b/index.html', head='<title>2</title><meta name="description" content="2">' + ld() + ld()),
                 'a/index.html': page('a/index.html', head=share('x.webp', height=None))}
        self.assertEqual(self.meta(files),
                         ['META a/index.html: og:image is not an absolute URL under %s: x.webp' % SITE,
                          'META a/index.html: og:image:width without og:image:height',
                          'META b/index.html: 2 <title> elements in the head (expected 1)',
                          'META b/index.html: 2 meta description tags (expected 1)',
                          'META b/index.html: 2 application/ld+json blocks (expected at most 1)'])
        self.assertEqual(self.sc.metadata(self.out, 'a/index.html'), self.meta(files)[:2])


# ---------------------------------------------------------------- SITEMAP, FEED, INDEX

class SitemapTests(Fixture):

    def lines(self, files):
        return self.sc.sitemap(self.built(files))

    def test_the_sound_build_has_no_lines(self):
        self.assertEqual(self.lines(tiny()), [])

    def test_a_missing_or_malformed_file(self):
        files = tiny()
        del files['sitemap.xml']
        self.assertEqual(self.lines(files), ['SITEMAP sitemap.xml: missing from the build'])
        files['sitemap.xml'] = sitemap_xml([SITE]).replace('</urlset>', '')
        lines = self.lines(files)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith('SITEMAP sitemap.xml: not well-formed XML ('), lines[0])

    def test_every_indexable_page_is_listed(self):
        files = tiny()
        files['sitemap.xml'] = sitemap_xml(own(p) for p in LISTED if p not in ('trips/tour/index.html', 'index.html'))
        self.assertEqual(self.lines(files), ['SITEMAP sitemap.xml: %s is not listed' % SITE,
                                             'SITEMAP sitemap.xml: %strips/tour/ is not listed' % SITE])

    def test_nothing_else_is_listed(self):
        files = tiny()
        extra = [SITE + 'trips/alpha/map/', SITE + '404.html', SITE + 'trips/search.json', SITE + 'trips/alpha/alpha.gpx',
                 SITE + 'trips/gone/', SITE + 'trips/alpha/index.html', 'https://example.test/', own('about/index.html')]
        files['sitemap.xml'] = sitemap_xml([own(p) for p in LISTED] + extra)
        self.assertEqual(self.lines(files),   # in the file's order: About stands near the top
                         ['SITEMAP sitemap.xml: %sabout/ is listed 2 times' % SITE,
                          'SITEMAP sitemap.xml: %strips/alpha/map/ is a noindex page' % SITE,
                          'SITEMAP sitemap.xml: %s404.html is the 404 page' % SITE,
                          'SITEMAP sitemap.xml: %strips/search.json is not the address of a page of this build' % SITE,
                          'SITEMAP sitemap.xml: %strips/alpha/alpha.gpx is not the address of a page of this build' % SITE,
                          'SITEMAP sitemap.xml: %strips/gone/ is not the address of a page of this build' % SITE,
                          'SITEMAP sitemap.xml: %strips/alpha/index.html is not the address of a page of this build' % SITE,
                          'SITEMAP sitemap.xml: https://example.test/ is not the address of a page of this build'])

    def test_missing_pages_come_before_wrong_entries(self):
        files = tiny()
        files['sitemap.xml'] = sitemap_xml([SITE + 'trips/gone/'] + [own(p) for p in LISTED if p != 'about/index.html'])
        self.assertEqual(self.lines(files), ['SITEMAP sitemap.xml: %sabout/ is not listed' % SITE,
                                             'SITEMAP sitemap.xml: %strips/gone/ is not the address of a page of this build' % SITE])

    def test_a_noindex_page_of_any_kind_is_left_out(self):
        files = tiny()
        files['trips/goal/index.html'] = page('trips/goal/index.html', '<a href="goal.gpx">GPX</a>', robots='nofollow, noindex')
        self.assertEqual(self.lines(files), ['SITEMAP sitemap.xml: %strips/goal/ is a noindex page' % SITE])
        files['sitemap.xml'] = sitemap_xml(own(p) for p in LISTED if p != 'trips/goal/index.html')
        self.assertEqual(self.lines(files), [])

    def test_whitespace_around_an_address_and_other_tags_are_fine(self):
        files = tiny()
        files['sitemap.xml'] = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                + ''.join('  <url>\n    <loc>\n      %s\n    </loc>\n    <priority>0.5</priority>\n  </url>\n' % own(p)
                                          for p in LISTED) + '</urlset>\n')
        self.assertEqual(self.lines(files), [])

    def test_a_conflict_copy_of_a_page_is_not_expected(self):
        files = tiny()
        files['about/index 2.html'] = page('about/index.html')
        files['trips/alpha 2/index.html'] = page('trips/alpha/index.html')
        self.assertEqual(self.lines(files), [])


class FeedTests(Fixture):

    def lines(self, files):
        return self.sc.feed(self.built(files))

    def test_the_sound_build_has_no_lines(self):
        self.assertEqual(self.lines(tiny()), [])
        files = tiny()
        files['feed.xml'] = feed_xml([])   # a site without reports: a channel and no item
        self.assertEqual(self.lines(files), [])

    def test_a_missing_or_malformed_file(self):
        files = tiny()
        del files['feed.xml']
        self.assertEqual(self.lines(files), ['FEED feed.xml: missing from the build'])
        files['feed.xml'] = feed_xml([feed_item(SITE + 'trips/alpha/', 'Rock & ice')])   # a bare ampersand
        lines = self.lines(files)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith('FEED feed.xml: not well-formed XML ('), lines[0])

    def test_every_item_links_to_a_built_page(self):
        files = tiny()
        files['feed.xml'] = feed_xml([
            feed_item(SITE + 'trips/alpha/'),
            feed_item(SITE + 'trips/draft/'),                                              # no such page: both tags
            feed_item(SITE + 'trips/tour/', guid='https://example.test/trips/tour/'),      # the guid alone
            feed_item(SITE + 'trips/tour/index.html', guid=SITE + 'trips/tour/'),          # not the page's address
            feed_item('trips/alpha/', guid=SITE + 'trips/alpha/alpha.gpx'),                # relative; a file, not a page
        ])
        gone = '%s is not the address of a page of this build'
        self.assertEqual(self.lines(files),
                         ['FEED feed.xml: item 2 link ' + gone % (SITE + 'trips/draft/'),
                          'FEED feed.xml: item 2 guid ' + gone % (SITE + 'trips/draft/'),
                          'FEED feed.xml: item 3 guid ' + gone % 'https://example.test/trips/tour/',
                          'FEED feed.xml: item 4 link ' + gone % (SITE + 'trips/tour/index.html'),
                          'FEED feed.xml: item 5 link ' + gone % 'trips/alpha/',
                          'FEED feed.xml: item 5 guid ' + gone % (SITE + 'trips/alpha/alpha.gpx')])

    def test_an_item_needs_a_link_and_a_guid(self):
        files = tiny()
        item = feed_item(SITE + 'trips/alpha/')
        files['feed.xml'] = feed_xml([item.replace('<link>%strips/alpha/</link>' % SITE, ''),
                                      item.replace('<guid>%strips/alpha/</guid>' % SITE, ''), item])
        self.assertEqual(self.lines(files), ['FEED feed.xml: item 1 has no <link>', 'FEED feed.xml: item 2 has no <guid>'])

    def test_the_channel_link_is_not_an_item(self):
        files = tiny()
        files['feed.xml'] = feed_xml([feed_item(SITE + 'trips/alpha/')]).replace('<link>%s</link>' % SITE, '<link>https://example.test/</link>')
        self.assertEqual(self.lines(files), [])


class IndexTests(Fixture):

    def lines(self, files):
        return self.sc.indexes(self.built(files))

    def test_the_sound_build_has_no_lines(self):
        self.assertEqual(self.lines(tiny()), [])

    def test_a_build_without_the_indexes_has_no_lines(self):
        files = tiny()
        del files['trips/search.json']
        del files['trips/journal.json']
        self.assertEqual(self.lines(files), [])
        self.assertEqual(self.check(files), [])

    def test_a_file_that_is_not_a_json_list(self):
        files = tiny()
        files['trips/search.json'] = '[{"s": "alpha"},'
        files['trips/journal.json'] = '{"s": "journal", "a": "day-1"}'
        lines = self.lines(files)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith('INDEX trips/search.json: not valid JSON ('), lines[0])
        self.assertEqual(lines[1], 'INDEX trips/journal.json: not a list of entries')

    def test_every_slug_is_a_built_trip_page(self):
        files = tiny()
        files['trips/search.json'] = json.dumps([{'s': 'alpha'}, {'s': 'draft-trip'}, {'t': 'no slug'}, 'text', {'s': ''}, {'s': 7},
                                                 {'s': 'alpha/map'}, {'s': 'tour'}])
        self.assertEqual(self.lines(files),
                         ['INDEX trips/search.json: "draft-trip" has no page trips/draft-trip/',
                          'INDEX trips/search.json: entry 3 has no "s" (the trip\'s slug)',
                          'INDEX trips/search.json: entry 4 has no "s" (the trip\'s slug)',
                          'INDEX trips/search.json: entry 5 has no "s" (the trip\'s slug)',
                          'INDEX trips/search.json: entry 6 has no "s" (the trip\'s slug)'])

    def test_a_trip_entry_needs_no_anchor(self):
        files = tiny()
        files['trips/search.json'] = json.dumps([{'s': 'alpha', 'a': 'nowhere'}, {'s': 'tour'}])
        self.assertEqual(self.lines(files), [])

    def test_every_journal_day_is_an_id_on_its_journal_page(self):
        files = tiny()
        files['trips/journal.json'] = json.dumps([
            {'s': 'journal', 'a': 'day-1'}, {'s': 'journal', 'a': 'day-2'}, {'s': 'journal'}, {'s': 'journal', 'a': ''},
            {'s': 'gone', 'a': 'day-1'}, {'s': 'alpha', 'a': 'day-1'}, {'s': 'journal', 'a': 'main'}, {'a': 'day-1'}])
        self.assertEqual(self.lines(files),
                         ['INDEX trips/journal.json: "journal" day "day-2" is not an id on trips/journal/',
                          'INDEX trips/journal.json: entry 3 has no "a" (the day\'s anchor)',
                          'INDEX trips/journal.json: entry 4 has no "a" (the day\'s anchor)',
                          'INDEX trips/journal.json: "gone" has no page trips/gone/',
                          'INDEX trips/journal.json: "alpha" day "day-1" is not an id on trips/alpha/',
                          'INDEX trips/journal.json: entry 8 has no "s" (the trip\'s slug)'])

    def test_a_repeated_problem_is_one_line(self):
        files = tiny()
        files['trips/journal.json'] = json.dumps([{'s': 'pct', 'a': 'day-%d' % i} for i in range(1, 6)]
                                                 + [{'s': 'journal', 'a': 'day-9'}, {'s': 'journal', 'a': 'day-9'}])
        files['trips/search.json'] = json.dumps([{'s': 'pct'}, {'s': 'alpha'}])
        self.assertEqual(self.lines(files),
                         ['INDEX trips/search.json: "pct" has no page trips/pct/',
                          'INDEX trips/journal.json: "pct" has no page trips/pct/',
                          'INDEX trips/journal.json: "journal" day "day-9" is not an id on trips/journal/'])


# ---------------------------------------------------------------- GPX

class GpxTests(Fixture):

    def lines(self, files, prepare=None):
        """gpx() over the files and the content folder; prepare(trips) changes the content first."""
        self.put(files)
        if not os.listdir(self.trips):
            write_content(self.trips)
        if prepare:
            prepare(self.trips)
        return self.sc.gpx(self.sc.read(self.out), self.trips)

    def test_the_sound_build_has_no_lines(self):
        self.assertEqual(self.lines(tiny()), [])

    def test_a_published_track_is_its_source_byte_for_byte(self):
        files = tiny()
        stripped = re.sub(r'<time>.*?</time>', '', ALPHA_GPX)   # the same track without its timestamps
        self.assertNotEqual(stripped, ALPHA_GPX)
        files['trips/alpha/alpha.gpx'] = stripped
        self.assertEqual(self.lines(files),
                         ['GPX trips/alpha/alpha.gpx: not the bytes of content/trips/alpha/track.gpx (sha256 %s published, %s source)'
                          % (sha12(stripped), sha12(ALPHA_GPX))])
        files['trips/alpha/alpha.gpx'] = ALPHA_GPX + '\n'   # one byte more
        self.assertEqual(len(self.lines(files)), 1)
        files['trips/alpha/alpha.gpx'] = ALPHA_GPX.replace('\n', '\r\n')
        self.assertEqual(len(self.lines(files)), 1)

    def test_a_day_a_journal_day_and_a_goal_track_are_compared_too(self):
        files = tiny()
        files['trips/tour/gpx/tour-day-02.gpx'] = DAY1_GPX
        files['trips/journal/gpx/journal-day-001.gpx'] = JOURNAL_GPX.replace('Journal day 1', 'Renamed')
        files['trips/goal/goal.gpx'] = GOAL_GPX.replace('Ridge route', 'Another name')
        self.assertEqual(self.lines(files),
                         ['GPX trips/goal/goal.gpx: not the bytes of content/trips/goal/track.gpx (sha256 %s published, %s source)'
                          % (sha12(files['trips/goal/goal.gpx']), sha12(GOAL_GPX)),
                          'GPX trips/journal/gpx/journal-day-001.gpx: not the bytes of content/trips/journal/days/001.gpx '
                          '(sha256 %s published, %s source)' % (sha12(files['trips/journal/gpx/journal-day-001.gpx']), sha12(JOURNAL_GPX)),
                          'GPX trips/tour/gpx/tour-day-02.gpx: not the bytes of content/trips/tour/days/02.gpx '
                          '(sha256 %s published, %s source)' % (sha12(DAY1_GPX), sha12(DAY2_GPX))])

    def test_without_a_content_folder_nothing_is_compared(self):
        files = tiny()
        files['trips/alpha/alpha.gpx'] = 'not the track'
        self.assertEqual(self.check(files, content_dir=False), [])
        self.assertEqual(len(self.check(files)), 1)

    def test_a_download_without_a_source_is_left_alone(self):
        files = tiny()
        files['trips/elsewhere/elsewhere.gpx'] = 'x'               # no such trip folder
        files['trips/tour/gpx/tour-day-03.gpx'] = 'x'              # day 3 has no track in the content
        files['trips/journal/journal.gpx'] = 'x'                   # a journal has no track.gpx and no combined file
        files['trips/alpha/other.gpx'] = 'x'                       # not a name the build writes
        files['trips/alpha/gpx/tour-day-01.gpx'] = 'x'             # another trip's day name
        files['trips/alpha/photos/alpha.gpx'] = 'x'
        files['alpha.gpx'] = 'x'
        self.assertEqual(self.lines(files), [])

    def test_the_combined_file_holds_every_day_track_unchanged(self):
        files = tiny()
        # a different title and header are the build's own; the tracks are what must not change
        files['trips/tour/tour.gpx'] = combined('Another title &amp; more', DAY1_GPX, DAY2_GPX).replace('creator="Eric', 'creator="E')
        self.assertEqual(self.lines(files), [])
        b1, _b2, b3 = trks(DAY1_GPX) + trks(DAY2_GPX)
        gone = 'GPX trips/tour/tour.gpx: the track of content/trips/tour/days/%s.gpx is not in the file unchanged and in day order'
        files['trips/tour/tour.gpx'] = TOUR_GPX.replace(b1, re.sub(r'<time>.*?</time>', '', b1))   # day 1 without timestamps
        self.assertEqual(self.lines(files), [gone % '01'])
        files['trips/tour/tour.gpx'] = TOUR_GPX.replace(b3, b3.replace('<ele>2015</ele>', '<ele>2016</ele>'))   # one point of day 2
        self.assertEqual(self.lines(files), [gone % '02'])

    def test_the_combined_file_keeps_day_order(self):
        files = tiny()
        files['trips/tour/tour.gpx'] = combined('Tour', DAY2_GPX, DAY1_GPX)
        self.assertEqual(self.lines(files), ['GPX trips/tour/tour.gpx: the track of content/trips/tour/days/02.gpx is not in the '
                                             'file unchanged and in day order'])
        b1, b2, b3 = trks(DAY1_GPX) + trks(DAY2_GPX)
        files['trips/tour/tour.gpx'] = combined('Tour', b1 + b3 + b2)   # the two tracks of day 2 swapped
        self.assertEqual(self.lines(files), ['GPX trips/tour/tour.gpx: the track of content/trips/tour/days/02.gpx is not in the '
                                             'file unchanged and in day order'])

    def test_the_combined_file_holds_no_other_track(self):
        files = tiny()
        files['trips/tour/tour.gpx'] = combined('Tour', DAY1_GPX, DAY2_GPX, JOURNAL_GPX)
        self.assertEqual(self.lines(files), ['GPX trips/tour/tour.gpx: holds 4 <trk> blocks, the day files hold 3'])
        files['trips/tour/tour.gpx'] = combined('Tour', DAY1_GPX)
        self.assertEqual(self.lines(files),
                         ['GPX trips/tour/tour.gpx: the track of content/trips/tour/days/02.gpx is not in the file unchanged and in day order',
                          'GPX trips/tour/tour.gpx: holds 1 <trk> blocks, the day files hold 3'])
        files['trips/tour/tour.gpx'] = DAY1_GPX   # one day's file published as the whole tour
        self.assertEqual(len(self.lines(files)), 2)

    def test_two_days_with_the_same_track_are_each_looked_for(self):
        def same_track_twice(trips):
            write_text(os.path.join(trips, 'tour', 'days', '02.gpx'), DAY1_GPX)
        files = tiny()
        files['trips/tour/gpx/tour-day-02.gpx'] = DAY1_GPX
        files['trips/tour/tour.gpx'] = combined('Tour', DAY1_GPX, DAY1_GPX)
        self.assertEqual(self.lines(files, same_track_twice), [])
        files['trips/tour/tour.gpx'] = combined('Tour', DAY1_GPX)
        self.assertEqual(self.lines(files),
                         ['GPX trips/tour/tour.gpx: the track of content/trips/tour/days/02.gpx is not in the file unchanged and in day order',
                          'GPX trips/tour/tour.gpx: holds 1 <trk> blocks, the day files hold 2'])

    def test_days_are_the_day_files_in_name_order(self):
        def more_days(trips):
            days = os.path.join(trips, 'tour', 'days')
            write_text(os.path.join(days, '10.md'), '---\nday: "10"\n---\n')
            write_text(os.path.join(days, '10.gpx'), JOURNAL_GPX)
            write_text(os.path.join(days, '04.gpx'), ALPHA_GPX)        # a track without a day file is no day
            write_text(os.path.join(days, '02 2.md'), '---\nday: "2"\n---\n')   # iCloud conflict copies of day 2
            write_text(os.path.join(days, '02 2.gpx'), ALPHA_GPX)
        files = tiny()
        files['trips/tour/tour.gpx'] = combined('Tour', DAY1_GPX, DAY2_GPX, JOURNAL_GPX)
        files['trips/tour/gpx/tour-day-10.gpx'] = JOURNAL_GPX
        self.assertEqual(self.lines(files, more_days), [])

    def test_a_multi_day_trip_without_day_tracks_is_compared_with_its_own_track(self):
        # build.copy_trip_assets writes no combined file then; a track.gpx beside index.md is published as it is
        helpers.make_trip(self.trips, 'walk', title='Walk', kind='multi-day', track=True, days=[{'track': False}, {'track': False}])
        write_text(os.path.join(self.trips, 'walk', 'track.gpx'), ALPHA_GPX)
        files = tiny()
        files['trips/walk/walk.gpx'] = ALPHA_GPX
        self.assertEqual(self.lines(files), [])
        files['trips/walk/walk.gpx'] = DAY1_GPX
        self.assertEqual(self.lines(files),
                         ['GPX trips/walk/walk.gpx: not the bytes of content/trips/walk/track.gpx (sha256 %s published, %s source)'
                          % (sha12(DAY1_GPX), sha12(ALPHA_GPX))])

    def test_only_a_multi_day_trip_has_a_combined_file(self):
        # a journal (kind: series) with a track.gpx of its own: a plain copy, whatever its days hold
        def journal_track(trips):
            write_text(os.path.join(trips, 'journal', 'track.gpx'), ALPHA_GPX)
        files = tiny()
        files['trips/journal/journal.gpx'] = ALPHA_GPX
        self.assertEqual(self.lines(files, journal_track), [])
        files['trips/journal/journal.gpx'] = combined('Journal', JOURNAL_GPX)
        self.assertEqual(self.lines(files),
                         ['GPX trips/journal/journal.gpx: not the bytes of content/trips/journal/track.gpx (sha256 %s published, %s source)'
                          % (sha12(files['trips/journal/journal.gpx']), sha12(ALPHA_GPX))])

    def test_an_index_file_that_cannot_be_read_is_not_a_crash(self):
        def break_index(trips):
            write_text(os.path.join(trips, 'tour', 'index.md'), '---\ntitle: Tour\nkind: multi-day\n')   # front matter never closed
            os.remove(os.path.join(trips, 'goal', 'index.md'))
        files = tiny()
        self.assertEqual(self.lines(files, break_index), [])   # the tour has no track.gpx to compare with; the goal still has

    def test_a_linked_download_is_its_source(self):
        # --link: the published file is a symlink to the content file
        files = tiny()
        del files['trips/alpha/alpha.gpx']
        del files['trips/tour/gpx/tour-day-01.gpx']
        write(self.out, files)
        write_content(self.trips)
        os.symlink(os.path.join(self.trips, 'alpha', 'track.gpx'), os.path.join(self.out, 'trips', 'alpha', 'alpha.gpx'))
        os.symlink(os.path.join(self.trips, 'tour', 'days', '02.gpx'), os.path.join(self.out, 'trips', 'tour', 'gpx', 'tour-day-01.gpx'))
        self.assertEqual(self.sc.gpx(self.out, self.trips),
                         ['GPX trips/tour/gpx/tour-day-01.gpx: not the bytes of content/trips/tour/days/01.gpx '
                          '(sha256 %s published, %s source)' % (sha12(DAY2_GPX), sha12(DAY1_GPX))])
        self.assertEqual(self.sc.check(self.out, self.trips), self.sc.gpx(self.out, self.trips))

    def test_a_conflict_copy_of_a_download_is_not_compared(self):
        files = tiny()
        files['trips/alpha/alpha 2.gpx'] = 'x'
        files['trips/tour/gpx/tour-day-01 3.gpx'] = 'x'
        files['trips/alpha 2/alpha 2.gpx'] = 'x'
        self.assertEqual(self.lines(files), [])

    def test_a_site_held_in_memory_is_compared_with_the_folder(self):
        write_content(self.trips)
        files = tiny()
        out = self.sc.of({k: v for k, v in files.items() if k.endswith('.html')},
                         files={k: v for k, v in files.items() if not k.endswith('.html')})
        self.assertEqual(self.sc.gpx(out, self.trips), [])
        files['trips/alpha/alpha.gpx'] = ALPHA_GPX.encode('utf-8') + b'\n'
        out = self.sc.of({}, files=files)
        self.assertEqual(len(self.sc.gpx(out, self.trips)), 1)


# ---------------------------------------------------------------- check(): everything, in order

class CheckTests(Fixture):

    def test_the_sound_build_has_no_problem(self):
        self.assertEqual(self.check(tiny()), [])
        self.assertEqual(self.sc.check(self.out), [])

    def test_conflict_copies_never_cause_a_line(self):
        files = tiny()
        files['index 2.html'] = '<a href="nowhere/">x</a><i id="a"></i><i id="a"></i>'
        files['trips/alpha 3/index.html'] = page('trips/alpha/index.html', '<a href="#gone">x</a>')
        files['trips/alpha 3/alpha 3.gpx'] = 'x'
        files['trips/alpha/alpha 2.gpx'] = 'x'
        files['sitemap 2.xml'] = '<broken'
        files['feed 4.xml'] = '<broken'
        files['trips/search 2.json'] = '{'
        files['assets/maps/region-alps-desktop 3.webp'] = ''
        self.assertEqual(self.check(files), [])

    def test_lines_come_page_by_page_then_family_by_family(self):
        files = tiny()
        body_add(files, 'trips/index.html', '<a href="zz/">1</a><a href="#gone">2</a><a href="journal/#day-9">3</a><i id="main"></i>'
                                            '<i id="search"></i><button aria-controls="nopanel">x</button><h3>Deep</h3>')
        body_add(files, '404.html', '<a href="nope/">x</a>')
        body_add(files, 'about/index.html', '<a href="#nowhere">x</a><a href="../trips/alpha/photos/02.webp">y</a>')
        head_add(files, 'about/index.html', '<title>Second</title>')
        head_add(files, 'index.html', '<meta property="og:image" content="%strips/alpha/photos/09.webp">' % SITE)
        files['sitemap.xml'] = sitemap_xml([own(p) for p in LISTED] + [SITE + '404.html'])
        files['feed.xml'] = feed_xml([feed_item(SITE + 'trips/gone/')])
        files['trips/search.json'] = json.dumps([{'s': 'gone'}])
        files['trips/goal/goal.gpx'] = 'changed'
        self.assertEqual(self.check(files), [
            'BROKEN 404.html -> nope/',
            'BROKEN about/index.html -> ../trips/alpha/photos/02.webp',
            'BROKEN ANCHOR about/index.html -> #nowhere',
            'BROKEN trips/index.html -> zz/',
            'BROKEN ANCHOR trips/index.html -> journal/#day-9',
            'BROKEN ANCHOR trips/index.html -> #gone',
            'DUPLICATE IDS trips/index.html: main, search',
            'ARIA-REF trips/index.html: aria-controls="nopanel" names no id on the page',
            'HEADING trips/index.html: h3 is the first heading ("Deep")',
            'META about/index.html: 2 <title> elements in the head (expected 1)',
            'META index.html: og:image file is not in the build: %strips/alpha/photos/09.webp' % SITE,
            'SITEMAP sitemap.xml: %s404.html is the 404 page' % SITE,
            'FEED feed.xml: item 1 link %strips/gone/ is not the address of a page of this build' % SITE,
            'FEED feed.xml: item 1 guid %strips/gone/ is not the address of a page of this build' % SITE,
            'INDEX trips/search.json: "gone" has no page trips/gone/',
            'GPX trips/goal/goal.gpx: not the bytes of content/trips/goal/track.gpx (sha256 %s published, %s source)'
            % (sha12('changed'), sha12(GOAL_GPX)),
        ])
        # the same list every time, and build.check's summary line counts every one of them
        again = self.sc.check(self.out, self.trips)
        self.assertEqual(again, self.check(files))
        self.assertTrue(all(isinstance(ln, str) and '\n' not in ln for ln in again))

    def test_a_build_without_sitemap_and_feed_says_so(self):
        self.assertEqual(self.check({'index.html': page('index.html')}),
                         ['SITEMAP sitemap.xml: missing from the build', 'FEED feed.xml: missing from the build'])

    def test_a_page_that_is_not_utf8_is_still_checked(self):
        files = tiny()
        files['about/index.html'] = files['about/index.html'].encode('utf-8').replace(b'What the page', b'Caf\xe9: what the page')
        body = b'<a href="gone/">x</a>'
        files['about/index.html'] = files['about/index.html'].replace(b'</main>', body + b'</main>')
        self.assertEqual(self.check(files), ['BROKEN about/index.html -> gone/'])


# ---------------------------------------------------------------- the generator's own output

def load_build(tc):
    """tools/build.py as a module, or a clear failure of the calling test."""
    try:
        return importlib.import_module('build')
    except ImportError as ex:
        tc.fail('tools/build.py is not importable: %s' % ex)


WRITEUP = ('Skinned up from the lake before dawn and skied the couloir on firm, edgeable snow. The exit was a long traverse '
           'back to the car, and [the loop](%strips/basin-loop/) is the same approach in summer.' % SITE)
REGIONS = ['Eastern Sierra', 'Alps']   # every region that lists a report on the map page (the journal's region does not)


class GeneratorTests(unittest.TestCase):
    """A small site built by tools/build.py build() itself. Every root is a temp dir: content.TRIPS_DIR and
    content.RENDERED (the trips and their rendered folders: the two single-day reports and the multi-day trip with a
    track get a placeholder render, render(), since a track without one has no map and no full-screen page), build.ROOT
    (a stand-in checkout holding the three asset files the bundles need), build.OUT, core.ROOT and core._SITE_META
    (rendered/site/meta.json, written here with the fixture's regions and no maps), and curation.load_manifest
    (content/home.json)."""
    maxDiff = None

    def setUp(self):
        self.sc = load_sitecheck(self)
        self.build = load_build(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        self.root = os.path.join(self.tmp, 'checkout')
        self.trips = os.path.join(self.root, 'content', 'trips')
        self.out = os.path.join(self.tmp, 'site')
        os.makedirs(self.trips)
        write(self.root, {'assets/css/base.css': 'body{margin:0}\n', 'assets/js/base.js': '/* base */\n',
                          'assets/favicon.svg': '<svg xmlns="http://www.w3.org/2000/svg"/>\n',
                          'rendered/site/meta.json': json.dumps({'hash': '', 'maps': {}, 'regions': [], 'all_regions': REGIONS})})
        self.featured = ['west-couloir']
        # what register_site leaves in core is put back, so no later test module sees this fixture's trips
        for name in ('_TRIPS_BY_URL', '_OTHER_SUBS', '_HAS_PCT', '_SITE_SHARE'):
            held = getattr(core, name, None)
            if isinstance(held, dict):
                self.addCleanup(lambda held=held, was=dict(held): (held.clear(), held.update(was)))
            elif isinstance(held, list):
                self.addCleanup(lambda held=held, was=list(held): held.__setitem__(slice(None), was))
        real_site = os.path.join(ROOT, '_site')
        self.real_site = os.stat(real_site).st_mtime_ns if os.path.exists(real_site) else None
        self.addCleanup(self.assert_checkout_untouched)

    def assert_checkout_untouched(self):
        real_site = os.path.join(ROOT, '_site')
        self.assertEqual(os.stat(real_site).st_mtime_ns if os.path.exists(real_site) else None, self.real_site)

    def reports(self):
        P = helpers.photo
        helpers.make_trip(self.trips, 'west-couloir', title='West Couloir & <the> "notch"', activity='ski', date='2026-01-17',
                          place='Sawtooth Ridge', region='Eastern Sierra', body=WRITEUP, track=True, featured=True,
                          published_at='2026-02-01', updated_at='2026-02-03', stats={'distance_km': 12.7, 'gain_m': 893},
                          photos=[P('photos/01.webp', helpers.LANDSCAPE, alt='The couloir from the lake', sm=True),
                                  P('photos/02.webp', helpers.PORTRAIT, alt='Skinning', caption='The apron')])
        helpers.make_trip(self.trips, 'basin-loop', title='Basin Loop', activity='hike', date='2025-08-10', region='Eastern Sierra',
                          route_shape='loop', track=True)
        helpers.make_trip(self.trips, 'haute-route', title='Haute Route', activity='ski', kind='multi-day', date='2025-04-01',
                          region='Alps', days=[{'title': 'Argentiere', 'date': '2025-04-01'},
                                               {'title': 'Trient', 'date': '2025-04-02', 'body': 'Crossed the col in a cold wind.'},
                                               {'title': 'Rest day', 'date': '2025-04-03', 'track': False}])
        helpers.make_series(self.trips, search_aliases=['PCT'])
        helpers.make_trip(self.trips, 'someday-ridge', title='Someday Ridge', activity='climb', kind='planned', region='Eastern Sierra',
                          track=True)
        helpers.make_trip(self.trips, 'hidden-draft', title='Hidden', activity='hike', date='2025-01-01', draft=True, track=True)
        write_text(os.path.join(self.trips, 'west-couloir', 'track.gpx'), ALPHA_GPX)
        write_text(os.path.join(self.trips, 'haute-route', 'days', '01.gpx'), DAY1_GPX)
        write_text(os.path.join(self.trips, 'haute-route', 'days', '02.gpx'), DAY2_GPX)
        write_text(os.path.join(self.trips, 'pacific-crest-trail-2024', 'days', '001.gpx'), JOURNAL_GPX)
        write_text(os.path.join(self.trips, 'someday-ridge', 'track.gpx'), GOAL_GPX)
        for slug in ('west-couloir', 'basin-loop'):
            self.render(slug, ('map-wide', 'map-col', 'map-phone'))
        self.render('haute-route', ('overview-wide', 'overview-col', 'overview-phone'))

    def render(self, slug, names):
        """A placeholder render folder for the trip, as tools/render.py leaves one: meta.json naming the maps, each map's
        inline fragment, its image and its base layer (empty files: the build copies them, the check finds them)."""
        folder = os.path.join(self.root, 'rendered', 'trips', slug)
        os.makedirs(folder, exist_ok=True)
        meta = {'hash': '', 'maps': {}, 'charts': {}}
        for name in names:
            meta['maps'][name] = {'w': 718, 'h': 400, 'png': name + '.webp', 'base': name + '.base.svg'}
            write_text(os.path.join(folder, name + '.svg.html'), '<svg width="718" height="400" viewBox="0 0 718 400"></svg>')
            for f in (name + '.webp', name + '.base.svg'):
                write_text(os.path.join(folder, f), '')
        write_text(os.path.join(folder, 'meta.json'), json.dumps(meta))

    def generate(self):
        """build.build() into the temp output folder; returns its pages."""
        real_rmtree = shutil.rmtree

        def rmtree(path, *args, **kw):   # build() empties its output folder first: never one outside the temp dir
            if not os.path.realpath(path).startswith(self.tmp + os.sep):
                raise AssertionError('build() would remove %s' % path)
            return real_rmtree(path, *args, **kw)

        manifest = {'featured_slugs': list(self.featured)}
        with mock.patch.object(content, 'TRIPS_DIR', self.trips), mock.patch.object(content, 'RENDERED', os.path.join(self.root, 'rendered')), \
                mock.patch.object(self.build, 'ROOT', self.root), mock.patch.object(self.build, 'OUT', self.out), \
                mock.patch.object(self.build, 'LINK', False), mock.patch.object(core, 'ROOT', self.root), \
                mock.patch.object(core, '_SITE_META', []), mock.patch.object(curation, 'load_manifest', lambda path=None: manifest), \
                mock.patch.object(shutil, 'rmtree', rmtree):
            return self.build.build(verbose=False)

    def read_out(self, rel):
        with open(os.path.join(self.out, *rel.split('/')), encoding='utf-8') as fh:
            return fh.read()

    def test_a_generated_site_is_sound(self):
        self.reports()
        pages = self.generate()
        self.assertEqual(self.sc.check(self.out, self.trips), [])
        out = self.sc.read(self.out)
        # the fixture exercised the rules: every page type, a share photo, a full-address link, the indexes, the tracks
        self.assertEqual(set(out.pages), {p.url + 'index.html' if (p.url == '' or p.url.endswith('/')) else p.url
                                          for p in pages if not p.url.endswith('.json')})
        for rel in ('index.html', '404.html', 'trips/index.html', 'tick-list/index.html', 'map/index.html', 'about/index.html',
                    'ski/index.html', 'trips/west-couloir/index.html', 'trips/west-couloir/map/index.html',
                    'trips/haute-route/index.html', 'trips/pacific-crest-trail-2024/index.html', 'trips/someday-ridge/index.html',
                    'trips/search.json', 'trips/journal.json', 'sitemap.xml', 'feed.xml', 'trips/west-couloir/west-couloir.gpx',
                    'trips/haute-route/haute-route.gpx', 'trips/haute-route/gpx/haute-route-day-02.gpx',
                    'trips/pacific-crest-trail-2024/gpx/pacific-crest-trail-2024-day-001.gpx', 'trips/someday-ridge/someday-ridge.gpx'):
            self.assertIn(rel, out.files)
        self.assertNotIn('trips/hidden-draft/index.html', out.files)
        report = self.read_out('trips/west-couloir/index.html')
        self.assertIn('<meta property="og:image" content="%strips/west-couloir/photos/01.webp">' % SITE, report)
        self.assertIn('href="%strips/basin-loop/"' % SITE, report)
        self.assertEqual(out.head('trips/west-couloir/map/index.html').noindex, True)
        self.assertEqual(out.head('404.html').canonicals, [])
        self.assertEqual(len(trks(self.read_out('trips/haute-route/haute-route.gpx'))), 3)

    def test_reports_without_a_track_are_sound_too(self):
        # contract 2.1: no track.gpx, no GPX control anywhere; a multi-day trip without any day track has no download
        self.reports()
        helpers.make_trip(self.trips, 'no-track', title='No Track', activity='hike', date='2025-09-01', region='Eastern Sierra',
                          featured=True, body='A walk without a recording.')
        helpers.make_trip(self.trips, 'tour-no-gpx', title='Tour without tracks', activity='hike', kind='multi-day', date='2025-03-01',
                          region='Alps', days=[{'title': 'One', 'track': False}, {'title': 'Two', 'track': False}])
        self.featured = ['no-track', 'west-couloir']
        pages = self.generate()
        self.assertEqual(self.sc.check(self.out, self.trips), [])
        self.assertFalse(os.path.exists(os.path.join(self.out, 'trips', 'no-track', 'no-track.gpx')))
        # contract 10.2: a report without a track has no map section and no full-screen map page; the reports with a
        # track and a render keep theirs (Phase 6: a track without a render has none), and so does the tour without day
        # tracks, whose page keeps its empty map
        out = self.sc.read(self.out)
        self.assertEqual(set(out.pages), {p.url + 'index.html' if (p.url == '' or p.url.endswith('/')) else p.url
                                          for p in pages if not p.url.endswith('.json')})
        self.assertIn('trips/no-track/index.html', out.pages)
        self.assertNotIn('trips/no-track/map/index.html', out.files)
        self.assertEqual([f for f in out.files if f.startswith('trips/no-track/')], ['trips/no-track/index.html'])
        for slug in ('west-couloir', 'basin-loop', 'haute-route', 'tour-no-gpx', 'pacific-crest-trail-2024'):
            self.assertIn('trips/%s/map/index.html' % slug, out.pages)
        page = self.read_out('trips/no-track/index.html')
        for needle in ('id="map"', 'href="#map"', 'href="map/', '.gpx', 'GPX', 'View route'):
            self.assertNotIn(needle, page)
        self.assertNotIn('%strips/no-track/map/' % SITE, self.read_out('sitemap.xml'))
        self.assertIn('<loc>%strips/no-track/</loc>' % SITE, self.read_out('sitemap.xml'))
        # ... and is never the section's featured report, though it is the newest hike and marked featured: the block is
        # built around the map, so Hiking features the newest report that has a track
        hiking = helpers.Doc(self.read_out('hiking/index.html'))
        feat = hiking.by_id('featured')
        self.assertIsNotNone(feat, 'hiking/ has no featured block')
        self.assertEqual(feat.find('h2').find('a')['href'], '../trips/basin-loop/')
        self.assertIn('../trips/no-track/', [a['href'] for a in hiking.by_id('reports').find_all('a')])    # it is a row instead
        self.assertNotIn('../trips/no-track/', [a['href'] for a in feat.find_all('a')])

    def test_a_generated_site_that_is_then_damaged_is_caught(self):
        self.reports()
        self.generate()

        def damaged(rel, change):
            """check() after one file of the build was changed (None: removed), the file put back afterwards."""
            path = os.path.join(self.out, *rel.split('/'))
            with open(path, 'rb') as fh:
                before = fh.read()
            if change is None:
                os.remove(path)
            else:
                with open(path, 'wb') as fh:
                    fh.write(change(before.decode('utf-8')).encode('utf-8'))
            try:
                return self.sc.check(self.out, self.trips)
            finally:
                with open(path, 'wb') as fh:
                    fh.write(before)

        lines = damaged('trips/west-couloir/photos/01.webp', None)
        self.assertIn('BROKEN trips/west-couloir/index.html -> ../../trips/west-couloir/photos/01.webp', lines)
        self.assertIn('META trips/west-couloir/index.html: og:image file is not in the build: %strips/west-couloir/photos/01.webp' % SITE, lines)
        self.assertTrue(all(ln.startswith(('BROKEN ', 'META ')) for ln in lines), lines)

        lines = damaged('trips/basin-loop/index.html', None)
        self.assertIn('BROKEN trips/west-couloir/index.html -> %strips/basin-loop/' % SITE, lines)   # the write-up's full address
        self.assertIn('SITEMAP sitemap.xml: %strips/basin-loop/ is not the address of a page of this build' % SITE, lines)
        self.assertIn('INDEX trips/search.json: "basin-loop" has no page trips/basin-loop/', lines)
        self.assertTrue([ln for ln in lines if ln.startswith('FEED feed.xml: item ') and 'trips/basin-loop/' in ln], lines)

        self.assertEqual(damaged('trips/west-couloir/west-couloir.gpx', lambda s: re.sub(r'<time>.*?</time>', '', s)),
                         ['GPX trips/west-couloir/west-couloir.gpx: not the bytes of content/trips/west-couloir/track.gpx '
                          '(sha256 %s published, %s source)' % (sha12(re.sub(r'<time>.*?</time>', '', ALPHA_GPX)), sha12(ALPHA_GPX))])
        self.assertEqual(damaged('trips/haute-route/haute-route.gpx', lambda s: s.replace('<ele>2005</ele>', '<ele>2006</ele>', 1)),
                         ['GPX trips/haute-route/haute-route.gpx: the track of content/trips/haute-route/days/01.gpx is not in the '
                          'file unchanged and in day order'])
        self.assertEqual(damaged('404.html', lambda s: s.replace('<meta name="robots" content="noindex">', '')),
                         ['META 404.html: the 404 page is not noindex'])
        self.assertEqual(damaged('trips/west-couloir/map/index.html', lambda s: s.replace('<meta name="robots" content="noindex">', '')),
                         ['SITEMAP sitemap.xml: %strips/west-couloir/map/ is not listed' % SITE])
        lines = damaged('trips/pacific-crest-trail-2024/index.html', lambda s: s.replace('id="day-2"', 'id="day-two"'))
        self.assertIn('INDEX trips/journal.json: "pacific-crest-trail-2024" day "day-2" is not an id on trips/pacific-crest-trail-2024/',
                      lines)
        self.assertTrue(all('day-2' in ln for ln in lines), lines)
        self.assertEqual(self.sc.check(self.out, self.trips), [])   # everything was put back


if __name__ == '__main__':
    unittest.main()
