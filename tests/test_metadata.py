"""Phase 4: share metadata, structured data and publication dates, pinned to contract-phase4.md section 4 (names and
exact strings: section 10) and to the Metadata row of plan section 16.

  1. content: the optional `published_at` / `updated_at` lines of index.md: every accepted form, kept exactly as
     written, and every refusal with its message. "Today" is content._today, patched to a fixed day far from the real
     one, so "the future" is deterministic and a build that read the real clock instead would fail here.
  2. core._share_tags / core.document(image=...): which Open Graph image tags are written, in which order, and when.
  3. the head of every page type, built through the real page modules: one title, one description, one canonical
     equal to the page's own URL (none on the 404 page), the share image with its recorded size and description, the
     site-wide fallback on the four site pages only, noindex on the map helpers and the 404 page.
  4. structured data: one BlogPosting on a written report and none anywhere else; publication dates in the page only
     when index.md states them, never the trip date and never the day of the build.
  5. foundations nothing pinned before: build.feed() and build.sitemap().

A synthetic site in a temp dir, every slug prefixed synm- (no real trip has that prefix). The loader, tools/build.py's
site_of() and every page module are the real ones; content.RENDERED and core.ROOT point into the temp dir and
core._SITE_META is replaced, so nothing under the real rendered/ or content/ is read (sandbox()). Every report with a
track and the goal have a placeholder render folder in the temp dir (Site.render), so each has its map helper page
(trips/<slug>/map/): since Phase 6 a track whose map is not rendered gets neither a map nor a helper page. The shared fixture is
built once for the module (fixture()) because its pages are only read; a test that needs another trip builds a small
site of its own (Site). core's registered site (the header's lookups and the fallback share image) is put back after
every build, so no test leaks into another module's.

  synm-newest   hike, the newest report, a track only                      -> no share image
  synm-story    hike, a write-up, three photos, cover_photo names the      -> story layout; the home lead
                third (1400 x 1000, an alt text with quotes, & and <>)
  synm-short    hike, a caption-length write-up and one photo              -> a story, but not a written report
  synm-compact  mtb, two photos (portrait, landscape), no write-up         -> compact layout with photos
  synm-flag     mtb, older, `featured: true`, cover_photo names its        -> leads the Mountain Biking page
                second photo
  synm-words    climb, a write-up, no photo                                -> a written report without an image
  synm-nosize   other, a write-up, one photo with no recorded size and     -> og:image alone
                an empty alt
  synm-ski      ski, a track only
  synm-tour     ski, multi-day; neither day's write-up reaches the         -> a written report; the cover is a day photo
                minimum alone, together they do; day 2 has two photos
  synm-journal  hike, series; day 1 two photos, day 2 a long write-up,
                day 3 a short one
  synm-goal     hike, planned, a track, long notes, two photos, a          -> a goal page and its map helper
                placeholder render folder in the temp dir
  synm-idea     hike, planned, nothing else
  synm-draft    a draft: never on the site

Every sentence in a fixture is synthetic.
"""
import contextlib
import email.utils
import importlib
import json
import os
import re
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import markdown  # noqa: E402
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, photo, LANDSCAPE, PORTRAIT  # noqa: E402

PREFIX = 'synm-'
TODAY = date(2031, 5, 20)     # the day every fixture build "runs": years away from the real one, on purpose
REGION = 'Synthetic Range'
SITE_META = {'hash': '', 'maps': {}, 'regions': [], 'all_regions': [REGION]}
U = core.SITE_URL

LONG = ('Synthetic write-up for a metadata test, long enough to count as a written report.\n\n'
        'Second synthetic paragraph, with *emphasis* and a [synthetic link](https://example.test/).')
SHORT = 'Synthetic caption-length note.'
DAY_ONE = 'Synthetic first day note, clearly longer than fifty characters in all.'
DAY_TWO = 'Synthetic second day note, also clearly longer than fifty characters.'
NOTES = ('Synthetic planning notes for a metadata test, long enough that a report with this much text would be marked up '
         'as an article.')
COVER_ALT = 'Synthetic cover: "quoted" & <angled>'
PARTY = 'Synthetic Partner'

FEATURED = ['synm-story', 'synm-tour']
REPORTS = ['synm-newest', 'synm-story', 'synm-short', 'synm-compact', 'synm-flag', 'synm-words', 'synm-nosize', 'synm-ski',
           'synm-tour', 'synm-journal']
GOALS = ['synm-goal', 'synm-idea']
WRITTEN = ['synm-story', 'synm-words', 'synm-nosize', 'synm-tour', 'synm-journal']   # core.written_report: one BlogPosting each
SECTIONS = ['ski/', 'climbing/', 'hiking/', 'mountain-biking/', 'other/']
SITE_PAGES = ['about/', 'map/', 'trips/', 'tick-list/']      # the pages that stand for the whole site (core.site_share)
HELPERS = ['trips/%s/map/' % s for s in REPORTS + ['synm-goal']]   # synm-idea has no rendered map, so no helper page


def crumbed(url):
    """The pages that show crumbs, and so carry one BreadcrumbList (seo-06): a trip's page (report, multi-day, journal,
    goal), an activity section and a region page; never home, the site pages, a map helper or the 404 page."""
    return (url.startswith('trips/') and url.count('/') == 2) or url in SECTIONS or url.startswith('regions/')
JSON_PAGES = ['trips/search.json', 'trips/journal.json']
# slug -> its cover as content records it: (site-relative path, w, h, alt)
COVER = {
    'synm-story': ('trips/synm-story/photos/03.webp', 1400, 1000, COVER_ALT),
    'synm-short': ('trips/synm-short/photos/01.webp', 1600, 1200, 'Synthetic short photo'),
    'synm-compact': ('trips/synm-compact/photos/02.webp', 1600, 1200, 'Synthetic compact landscape'),
    'synm-flag': ('trips/synm-flag/photos/02.webp', 1600, 1200, 'Synthetic flag second'),
    'synm-nosize': ('trips/synm-nosize/photos/01.webp', None, None, ''),
    'synm-tour': ('trips/synm-tour/photos/d2-02.webp', 1600, 1200, 'Synthetic tour day two'),
    'synm-journal': ('trips/synm-journal/photos/d001-02.webp', 1600, 1200, 'Synthetic journal landscape'),
    'synm-goal': ('trips/synm-goal/photos/02.webp', 1600, 1200, 'Synthetic goal landscape'),
}
# page URL -> the slug whose cover it shares (None: no image), with the fixture's two features
SHARES = {'': 'synm-story', 'hiking/': 'synm-story', 'mountain-biking/': 'synm-flag', 'ski/': 'synm-tour', 'other/': 'synm-nosize',
          'climbing/': None, '404.html': None}
SHARES.update({u: 'synm-story' for u in SITE_PAGES})
SHARES.update({'trips/%s/' % s: (s if s in COVER else None) for s in REPORTS + GOALS})
SHARES.update({u: None for u in HELPERS})

SHAPE = ('%s must be a date written YYYY-MM-DD, or a date and time with an offset such as 2026-10-03T18:30:00-07:00, got %r')
NOT_REAL = '%s %r is not a real date or time'
FUTURE = '%s %s is in the future'
BEFORE_TRIP = ('published_at %s is before the trip itself (%s); it is the day the report went online, not the trip date')
NEEDS = 'updated_at needs published_at (the day the report first went online)'
BEFORE_PUB = 'updated_at %s is before published_at %s'
PLANNED = '%s is for a report; this is a planned route (kind: planned)'

LD_KEYS = {'@context', '@type', 'headline', 'url', 'mainEntityOfPage', 'description', 'inLanguage', 'author'}
LD_OPTIONAL = {'image', 'datePublished', 'dateModified'}


def module(name):
    return importlib.import_module(name)


def page_module(name):
    return importlib.import_module('sitegen.pages.' + name)


def fake_date(day):
    """datetime.date whose today() is `day`, for the modules that read the clock themselves (the footer's year)."""
    class _Date(date):
        @classmethod
        def today(cls):
            return cls(day.year, day.month, day.day)
    return _Date


def fake_datetime(moment):
    """datetime.datetime whose now() / utcnow() / today() are `moment`."""
    class _DateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(moment.year, moment.month, moment.day, moment.hour, moment.minute, tzinfo=tz)

        @classmethod
        def utcnow(cls):
            return cls(moment.year, moment.month, moment.day, moment.hour, moment.minute)

        @classmethod
        def today(cls):
            return cls(moment.year, moment.month, moment.day, moment.hour, moment.minute)
    return _DateTime


def generator_modules():
    """core and every page module tools/build.py builds with (imported here, so each is there to be patched)."""
    return [core] + [page_module(name) for name in module('build').PAGE_MODULES]


def forget_builds():
    """Empty the page modules' per-build caches (report: the title counts of one site; multi-day: what a slug's maps draw)."""
    for name, cache in (('report', '_TITLE_COUNTS'), ('multiday', '_DRAWN')):
        getattr(page_module(name), cache, {}).clear()


@contextlib.contextmanager
def sandbox(root, today=TODAY):
    """Everything a load or a page build reads besides the trip folders, pointed at the temp dir `root` or fixed: the
    render folders (content.RENDERED: a trip's own; core.ROOT: the site maps), the site map index (core._SITE_META),
    and the day it is: content._today for the loader, and the `date` / `datetime` classes of core and of every page
    module, whose today() and now() answer `today` (the footer's year reads the clock that way). core's registered
    site and the page modules' per-build caches are put back on the way out."""
    saved = (dict(core._TRIPS_BY_URL), list(core._OTHER_SUBS), core._HAS_PCT[0], core._SITE_SHARE[0])
    clock = {date: fake_date(today), datetime: fake_datetime(datetime(today.year, today.month, today.day, 12))}
    patches = [(content, 'RENDERED', os.path.join(root, 'rendered')), (content, '_today', lambda: today),
               (core, 'ROOT', root), (core, '_SITE_META', [dict(SITE_META)])]
    for mod in generator_modules():
        patches += [(mod, name, clock[value]) for name, value in sorted(vars(mod).items()) if value is date or value is datetime]
    with contextlib.ExitStack() as stack:
        for target, name, value in patches:
            stack.enter_context(mock.patch.object(target, name, value))
        forget_builds()
        try:
            yield
        finally:
            core._TRIPS_BY_URL.clear()
            core._TRIPS_BY_URL.update(saved[0])
            core._OTHER_SUBS[:] = saved[1]
            core._HAS_PCT[0] = saved[2]
            core._SITE_SHARE[0] = saved[3]
            forget_builds()


def add_front_matter(folder, *lines):
    """Insert raw lines into the front matter of <folder>/index.md, exactly as an author would type them (helpers.make_trip
    writes through frontmatter.dumps, which quotes any value with a colon in it)."""
    path = os.path.join(folder, 'index.md')
    with open(path, encoding='utf-8') as fh:
        head, rest = fh.read().split('\n---\n', 1)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('%s\n%s\n---\n%s' % (head, '\n'.join(lines), rest))


def metas(node):
    """[(property or name, content)] of the <meta> tags under a node that carry either, in document order."""
    return [(m['property'] or m['name'], m['content']) for m in node.find_all('meta') if (m['property'] or m['name'])]


def share_run(pairs):
    """The share-image part of a head: its og:image* and twitter:* tags, in order."""
    return [(k, v) for k, v in pairs if k.startswith(('og:image', 'twitter:'))]


def expected_share(path, w, h, alt, kind='image/webp'):
    """What contract 4.2 says a page with this share image writes, in order."""
    out = [('og:image', U + path)]
    if kind:
        out.append(('og:image:type', kind))
    if w and h:
        out += [('og:image:width', str(w)), ('og:image:height', str(h))]
    if alt:
        out.append(('og:image:alt', alt))
    out.append(('twitter:card', 'summary_large_image'))
    if alt:
        out.append(('twitter:image:alt', alt))
    return out


NO_SHARE = [('twitter:card', 'summary')]
# a report's article tags (Phase 14, seo-03): its author, its activity's label, one tag per region and summit
ARTICLE = ['article:author', 'article:section', 'article:tag']
_LD_OPEN = re.compile(r'<script\b[^>]*\btype\s*=\s*["\']?application/ld\+json["\']?[^>]*>', re.I)


def ld_raw(html_, crumbs=False):
    """The text of every <script type="application/ld+json"> block of a page, up to the first </script> after it (what
    a browser takes as the block). Since Phase 14 a crumbed page also carries a BreadcrumbList (seo-06, CrumbsLdTests);
    the tests here are about the BlogPosting, so that block is left out unless crumbs."""
    out = []
    for m in _LD_OPEN.finditer(html_):
        raw = html_[m.end():html_.index('</script>', m.end())]
        if crumbs or not _is_crumbs(raw):
            out.append(raw)
    return out


def _is_crumbs(raw):
    try:
        return json.loads(raw).get('@type') == 'BreadcrumbList'
    except (ValueError, AttributeError):
        return False


def ld_blocks(html_):
    return [json.loads(s) for s in ld_raw(html_)]


class Built:
    """One build of a Site: the site dict, the trips by slug and every page the page modules returned."""

    def __init__(self, site, pages, trips_dir):
        self.site = site
        self.by = site['by_slug']
        self.pages = pages
        self.by_url = {p.url: p for p in pages}
        self.trips_dir = trips_dir
        self._docs = {}

    def html(self, url):
        return self.by_url[url].html

    def doc(self, url):
        if url not in self._docs:
            self._docs[url] = Doc(self.html(url))
        return self._docs[url]

    def head(self, url):
        return self.doc(url).find('head')

    def metas(self, url):
        return metas(self.head(url))

    def meta(self, url, key):
        """Every content of the head's <meta> with this property or name."""
        return [v for k, v in self.metas(url) if k == key]

    def canonicals(self, url):
        return [ln['href'] for ln in self.doc(url).find_all('link', attrs={'rel': 'canonical'})]

    def ld(self, url):
        return ld_blocks(self.html(url))

    def html_urls(self):
        return [p.url for p in self.pages if not p.url.endswith('.json')]


class Site:
    """A synthetic site under <root>/content/trips, written with helpers.make_trip and built like tools/build.py does:
    the real loader, build.site_of(), `featured` as content/home.json would give it, core.register_site, then build()
    of every module in build.PAGE_MODULES."""

    def __init__(self, root, today=TODAY):
        self.root = root
        self.today = today
        self.trips_dir = os.path.join(root, 'content', 'trips')
        os.makedirs(self.trips_dir, exist_ok=True)

    def add(self, slug, lines=(), **meta):
        assert slug.startswith(PREFIX), 'fixture slug %r lacks the %r prefix' % (slug, PREFIX)
        folder = helpers.make_trip(self.trips_dir, slug, **{k: v for k, v in meta.items() if v is not None})
        if lines:
            add_front_matter(folder, *lines)
        return folder

    REPORT_MAPS = (('map-wide', (1440, 640)), ('map-col', (718, 400)), ('map-phone', (390, 336)))
    OVERVIEW_MAPS = (('overview-wide', (1440, 560)), ('overview-col', (718, 440)), ('overview-phone', (390, 260)))

    def render(self, slug, maps=REPORT_MAPS):
        """A placeholder render folder for the trip inside the temp dir: meta.json with the three report maps (or the
        multi-day overview's, maps=OVERVIEW_MAPS) and the tiny fragments core.map_block inlines."""
        folder = os.path.join(self.root, 'rendered', 'trips', slug)
        os.makedirs(folder, exist_ok=True)
        meta = {'maps': {}, 'charts': {}}
        for name, (w, h) in maps:
            meta['maps'][name] = {'w': w, 'h': h, 'png': name + '.webp', 'base': name + '.base.svg'}
            with open(os.path.join(folder, name + '.svg.html'), 'w', encoding='utf-8') as fh:
                fh.write('<svg width="%d" height="%d" viewBox="0 0 %d %d"></svg>' % (w, h, w, h))
        with open(os.path.join(folder, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(meta, fh)

    def load(self, today=None):
        """The site dict (build.site_of), loaded on `today`; nothing registered, no page built."""
        with sandbox(self.root, today or self.today):
            return module('build').site_of(helpers.load_dir(self.trips_dir))

    def build(self, featured=(), today=None, only=None):
        with sandbox(self.root, today or self.today):
            build = module('build')
            site = build.site_of(helpers.load_dir(self.trips_dir))
            site['featured'] = [site['by_slug'][s] for s in featured]
            core.register_site(site)
            pages = []
            for name in build.PAGE_MODULES:
                if only is None or name in only:
                    pages += page_module(name).build(site)
        return Built(site, pages, self.trips_dir)


def fixture_site(root):
    """The module's fixture (see the docstring), written but not built."""
    s = Site(root)
    s.add('synm-newest', title='Synthetic Newest Track', activity='hike', date='2026-07-01', region=REGION, track=True)
    s.add('synm-story', title='Synthetic Story', activity='hike', date='2026-06-01', region=REGION, place='Synthetic Basin',
          party=PARTY, track=True, body=LONG, cover_photo='photos/03.webp',
          stats={'distance_km': 12.0, 'gain_m': 800, 'high_m': 2900, 'low_m': 2100},
          photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic story portrait'),
                  photo('photos/02.webp', LANDSCAPE, alt='Synthetic story landscape', sm=True),
                  photo('photos/03.webp', (1400, 1000), alt=COVER_ALT, caption='Synthetic caption for the cover.')])
    s.add('synm-short', title='Synthetic Short Note', activity='hike', date='2026-04-15', region=REGION, track=True, body=SHORT,
          photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic short photo')])
    s.add('synm-compact', title='Synthetic Photos Only', activity='mtb', date='2026-05-01', region=REGION, track=True,
          photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic compact portrait'),
                  photo('photos/02.webp', LANDSCAPE, alt='Synthetic compact landscape')])
    s.add('synm-flag', title='Synthetic Flagged Ride', activity='mtb', date='2026-02-01', region=REGION, track=True, featured=True,
          cover_photo='photos/02.webp',
          photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic flag first'), photo('photos/02.webp', LANDSCAPE, alt='Synthetic flag second')])
    s.add('synm-words', title='Synthetic Words Only', activity='climb', date='2026-03-20', region=REGION, track=True, body=LONG)
    s.add('synm-nosize', title='Synthetic Unmeasured Photo', activity='other', subtype='SUP', date='2026-04-10', region=REGION,
          track=True, body=LONG, photos=[photo('photos/01.webp', None, alt='')])
    s.add('synm-ski', title='Synthetic Ski Track', activity='ski', date='2026-04-01', region=REGION, track=True)
    s.add('synm-tour', title='Synthetic Tour', activity='ski', kind='multi-day', date='2026-03-10', end_date='2026-03-11',
          region=REGION,
          days=[{'title': 'Synthetic Day One', 'date': '2026-03-10', 'body': DAY_ONE},
                {'title': 'Synthetic Day Two', 'date': '2026-03-11', 'body': DAY_TWO,
                 'photos': [photo('photos/d2-01.webp', PORTRAIT, alt='Synthetic tour portrait'),
                            photo('photos/d2-02.webp', LANDSCAPE, alt='Synthetic tour day two')]}])
    s.add('synm-journal', title='Synthetic Journal', activity='hike', kind='series', date='2024-04-22', end_date='2024-04-24',
          region=REGION, place='Start to Finish',
          days=[{'id': '001', 'title': 'Synthetic Camp One', 'date': '2024-04-22',
                 'photos': [photo('photos/d001-01.webp', PORTRAIT, alt='Synthetic journal portrait'),
                            photo('photos/d001-02.webp', LANDSCAPE, alt='Synthetic journal landscape')]},
                {'id': '002', 'title': 'Synthetic Camp Two', 'date': '2024-04-23', 'body': LONG},
                {'id': '003', 'title': 'Synthetic Camp Three', 'date': '2024-04-24', 'body': SHORT, 'track': False}])
    for slug in REPORTS:
        if slug == 'synm-tour':
            s.render(slug, Site.OVERVIEW_MAPS)
        elif slug != 'synm-journal':          # a journal's map page needs no render (series.py)
            s.render(slug)
    s.add('synm-goal', title='Synthetic Goal', activity='hike', kind='planned', region=REGION, track=True, body=NOTES,
          photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic goal portrait'), photo('photos/02.webp', LANDSCAPE, alt='Synthetic goal landscape')])
    s.render('synm-goal')
    s.add('synm-idea', title='Synthetic Idea', activity='hike', kind='planned', region=REGION)
    s.add('synm-draft', title='Synthetic Draft', activity='hike', date='2026-08-01', region=REGION, track=True, draft=True, body=LONG,
          photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic draft photo')])
    return s


_SHARED = {}


def fixture():
    """The shared fixture, built once: .site (the Site), .feat (built with FEATURED) and .bare (built with no feature)."""
    if 'fx' not in _SHARED:
        tmp = tempfile.TemporaryDirectory()
        _SHARED['tmp'] = tmp
        site = fixture_site(tmp.name)
        _SHARED['fx'] = types.SimpleNamespace(site=site, feat=site.build(FEATURED), bare=site.build([]))
    return _SHARED['fx']


def tearDownModule():
    _SHARED.pop('fx', None)
    tmp = _SHARED.pop('tmp', None)
    if tmp is not None:
        tmp.cleanup()
    helpers.no_region_pages_left()      # this module registers sites: no region page may stay registered after it


class TempCase(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def site(self, name='a', today=TODAY):
        """An empty Site in its own folder of the test's temp dir."""
        return Site(os.path.join(self.tmp, name), today)


# ================================================================ 1. published_at / updated_at in content

class PublicationFieldTests(TempCase):

    def setUp(self):
        TempCase.setUp(self)
        self.k = 0

    def slug(self):
        self.k += 1
        return '%spub-%d' % (PREFIX, self.k)

    def trip(self, lines=(), today=TODAY, slug=None, **meta):
        """One synthetic report (a hike on 2026-06-01 unless meta says otherwise; date=None: undated), raw `lines` added
        to its front matter as typed, loaded with the build's day fixed to `today`."""
        slug = slug or self.slug()
        meta.setdefault('date', '2026-06-01')
        folder = helpers.make_trip(self.tmp, slug, **{k: v for k, v in meta.items() if v is not None})
        if lines:
            add_front_matter(folder, *lines)
        with mock.patch.object(content, '_today', lambda: today):
            return helpers.load(self.tmp, slug)

    def refused(self, message, lines=(), today=TODAY, **meta):
        slug = self.slug()
        with self.assertRaises(content.ContentError) as cm:
            self.trip(lines, today, slug=slug, **meta)
        self.assertEqual(str(cm.exception), 'content/trips/%s/index.md: %s' % (slug, message))

    # ------------------------------------------------------------ accepted

    ACCEPTED = ['2026-10-03', '2026-10-03T18:30:00Z', '2026-10-03T18:30Z', '2026-10-03T18:30:00+02:00', '2026-10-03T18:30+02:00',
                '2026-10-03T18:30:00-07:00', '2026-10-03T18:30-07:00', '2026-10-03T00:00:00+14:00', '2026-10-03T23:59:59-12:00']

    def test_absent_fields_are_none(self):
        t = self.trip()
        self.assertIn('published_at', t)
        self.assertIn('updated_at', t)
        self.assertIsNone(t['published_at'])
        self.assertIsNone(t['updated_at'])

    def test_absent_fields_are_none_on_every_kind(self):
        tour = self.trip(kind='multi-day', days=[{'date': '2026-06-01'}, {'date': '2026-06-02'}])
        journal = self.trip(kind='series', days=[{'id': '001', 'date': '2026-06-01'}])
        goal = self.trip(kind='planned', date=None)
        for t in (tour, journal, goal):
            self.assertEqual((t['published_at'], t['updated_at']), (None, None), t['kind'])

    def test_an_empty_line_is_absent(self):
        for lines in (['published_at:'], ['published_at: ""'], ["published_at: ''"], ['published_at:', 'updated_at:'],
                      ['published_at: ""', 'updated_at: ""'], ['updated_at:']):
            with self.subTest(lines=lines):
                t = self.trip(lines)
                self.assertEqual((t['published_at'], t['updated_at']), (None, None))

    def test_every_accepted_form_is_kept_exactly_as_typed(self):
        for v in self.ACCEPTED:
            with self.subTest(typed=v):
                t = self.trip(['published_at: ' + v])
                self.assertEqual(t['published_at'], v)
                self.assertIs(type(t['published_at']), str)
                self.assertIsNone(t['updated_at'])

    def test_every_accepted_form_is_kept_when_quoted(self):
        # helpers.make_trip dumps a value with a colon in double quotes; an author may also use single quotes
        for v in self.ACCEPTED:
            with self.subTest(dumped=v):
                self.assertEqual(self.trip(published_at=v)['published_at'], v)
            with self.subTest(single_quoted=v):
                self.assertEqual(self.trip(["published_at: '%s'" % v])['published_at'], v)

    def test_updated_at_takes_the_same_forms(self):
        for v in self.ACCEPTED:
            with self.subTest(typed=v):
                t = self.trip(['published_at: 2026-10-03', 'updated_at: ' + v])
                self.assertEqual((t['published_at'], t['updated_at']), ('2026-10-03', v))
                self.assertIs(type(t['updated_at']), str)

    def test_a_leap_day_is_a_real_date(self):
        self.assertEqual(self.trip(['published_at: 2024-02-29'], date='2024-01-05')['published_at'], '2024-02-29')

    def test_fields_are_accepted_on_multi_day_trips_and_journals(self):
        tour = self.trip(['published_at: 2026-06-05', 'updated_at: 2026-06-06T08:00:00-07:00'], kind='multi-day',
                         days=[{'date': '2026-06-01'}, {'date': '2026-06-02'}])
        self.assertEqual((tour['published_at'], tour['updated_at']), ('2026-06-05', '2026-06-06T08:00:00-07:00'))
        journal = self.trip(['published_at: 2026-06-05T12:00Z'], kind='series', days=[{'id': '001', 'date': '2026-06-01'}])
        self.assertEqual((journal['published_at'], journal['updated_at']), ('2026-06-05T12:00Z', None))

    def test_an_undated_report_can_state_when_it_went_online(self):
        self.assertEqual(self.trip(['published_at: 2019-01-01'], date=None)['published_at'], '2019-01-01')

    def test_the_fields_of_a_day_file_are_not_the_reports(self):
        # contract 4.4: in a days/NN.md file the keys are unknown keys (a warning of the content check), nothing more
        t = self.trip(kind='multi-day', days=[{'date': '2026-06-01', 'published_at': '2026-06-05', 'updated_at': '2026-06-06'},
                                              {'date': '2026-06-02'}])
        self.assertEqual((t['published_at'], t['updated_at']), (None, None))

    # ------------------------------------------------------------ the shape

    def test_any_other_shape_is_refused(self):
        cases = [('2026', 2026), ('20261003', 20261003), ('2026.5', 2026.5), ('true', True), ('[2026-10-03]', ['2026-10-03']),
                 ('10/03/2026', '10/03/2026'), ('Oct 3, 2026', 'Oct 3, 2026'), ('2026-6-3', '2026-6-3'), ('26-10-03', '26-10-03'),
                 ('2026-10-03T18:30', '2026-10-03T18:30'), ('2026-10-03T18:30:00', '2026-10-03T18:30:00'),
                 ('2026-10-03T18Z', '2026-10-03T18Z'), ('2026-10-03 18:30:00-07:00', '2026-10-03 18:30:00-07:00'),
                 ('2026-10-03T18:30:00-0700', '2026-10-03T18:30:00-0700'), ('2026-10-03T18:30:00-07', '2026-10-03T18:30:00-07'),
                 ('2026-10-03T18:30:00z', '2026-10-03T18:30:00z'), ('2026-10-03t18:30:00Z', '2026-10-03t18:30:00Z'),
                 ('2026-10-03T18:30:00.5Z', '2026-10-03T18:30:00.5Z'), ('2026-10-03Z', '2026-10-03Z'),
                 ('2026-10-03T18:30:00 UTC', '2026-10-03T18:30:00 UTC')]
        for typed, value in cases:
            with self.subTest(typed=typed):
                self.refused(SHAPE % ('published_at', value), ['published_at: ' + typed])
            with self.subTest(typed=typed, field='updated_at'):
                self.refused(SHAPE % ('updated_at', value), ['published_at: 2026-10-03', 'updated_at: ' + typed])

    def test_a_time_without_an_offset_is_refused_by_name(self):
        # the cases the task names one by one, with the whole message spelled out once
        self.refused('published_at must be a date written YYYY-MM-DD, or a date and time with an offset such as '
                     "2026-10-03T18:30:00-07:00, got '2026-10-03T18:30'", ['published_at: 2026-10-03T18:30'])
        self.refused('published_at must be a date written YYYY-MM-DD, or a date and time with an offset such as '
                     '2026-10-03T18:30:00-07:00, got 2026', ['published_at: 2026'])
        self.refused('published_at must be a date written YYYY-MM-DD, or a date and time with an offset such as '
                     "2026-10-03T18:30:00-07:00, got '10/03/2026'", ['published_at: 10/03/2026'])

    # ------------------------------------------------------------ impossible dates and times

    def test_an_impossible_date_or_time_is_refused(self):
        cases = ['2026-02-30', '2025-02-29', '2026-13-01', '2026-00-10', '2026-10-00', '2026-10-32', '2026-10-03T24:00:00Z',
                 '2026-10-03T18:60Z', '2026-10-03T18:30:60Z', '2026-10-03T18:30:00+15:00', '2026-10-03T18:30-15:00',
                 '2026-10-03T18:30:00+99:00', '2026-10-03T18:30:00+02:60']
        for v in cases:
            with self.subTest(typed=v):
                self.refused(NOT_REAL % ('published_at', v), ['published_at: ' + v])
            with self.subTest(typed=v, field='updated_at'):
                self.refused(NOT_REAL % ('updated_at', v), ['published_at: 2026-10-03', 'updated_at: ' + v])

    def test_the_impossible_cases_the_contract_names(self):
        self.refused("published_at '2026-02-30' is not a real date or time", ['published_at: 2026-02-30'])
        self.refused("published_at '2026-10-03T25:00Z' is not a real date or time", ['published_at: 2026-10-03T25:00Z'])
        self.refused("published_at '2026-10-03T18:30+15:00' is not a real date or time", ['published_at: 2026-10-03T18:30+15:00'])

    def test_an_offset_of_fourteen_hours_is_real(self):
        for v in ('2026-10-03T18:30+14:00', '2026-10-03T18:30-14:00', '2026-10-03T18:30+00:00', '2026-10-03T18:30+05:45'):
            with self.subTest(typed=v):
                self.assertEqual(self.trip(['published_at: ' + v])['published_at'], v)

    def test_fourteen_hours_is_the_largest_offset(self):
        # contract 10.2: no clock on earth is more than 14 hours from UTC, so an offset above 14:00 is refused like +15:00,
        # whatever its sign and whether or not the time has seconds (+14:30 used to load: only the hours were looked at)
        for v in ('2026-10-03T18:30+14:01', '2026-10-03T18:30+14:30', '2026-10-03T18:30:00+14:30', '2026-10-03T18:30+14:59',
                  '2026-10-03T18:30-14:01', '2026-10-03T18:30:00-14:30', '2026-10-03T18:30-14:59'):
            with self.subTest(typed=v):
                self.refused(NOT_REAL % ('published_at', v), ['published_at: ' + v])
            with self.subTest(typed=v, field='updated_at'):
                self.refused(NOT_REAL % ('updated_at', v), ['published_at: 2026-10-03', 'updated_at: ' + v])
        # the whole message, spelled out once for each of the three the task names
        self.refused("published_at '2026-10-03T18:30+14:01' is not a real date or time", ['published_at: 2026-10-03T18:30+14:01'])
        self.refused("published_at '2026-10-03T18:30+14:30' is not a real date or time", ['published_at: 2026-10-03T18:30+14:30'])
        self.refused("published_at '2026-10-03T18:30-14:59' is not a real date or time", ['published_at: 2026-10-03T18:30-14:59'])

    def test_fourteen_hours_exactly_and_everything_below_it_still_load(self):
        # ... and the limit itself is inside: +14:00 and -14:00 (and the minute before either) load as typed, in both fields
        for v in ('2026-10-03T18:30+14:00', '2026-10-03T18:30:00+14:00', '2026-10-03T18:30-14:00', '2026-10-03T18:30:00-14:00',
                  '2026-10-03T18:30+13:59', '2026-10-03T18:30-13:59', '2026-10-03T18:30+13:30'):
            with self.subTest(typed=v):
                self.assertEqual(self.trip(['published_at: ' + v])['published_at'], v)
            with self.subTest(typed=v, field='updated_at'):
                t = self.trip(['published_at: 2026-10-03', 'updated_at: ' + v])
                self.assertEqual((t['published_at'], t['updated_at']), ('2026-10-03', v))
        # the moment read from it is the one written: fourteen hours either side of UTC, to the minute
        for v, minutes in (('2026-10-03T18:30+14:00', 840), ('2026-10-03T18:30-14:00', -840), ('2026-10-03T18:30+13:59', 839),
                           ('2026-10-03T18:30-13:59', -839)):
            with self.subTest(moment=v):
                text, moment = content._pub_value({'published_at': v}, 'published_at', 'x')
                self.assertEqual(text, v)
                self.assertEqual(moment.utcoffset(), timedelta(minutes=minutes))

    def test_only_the_digits_0_to_9_are_digits(self):
        # content._PUB is compiled with re.ASCII: int() would read full-width or Arabic-Indic digits as numbers, and the
        # value is published exactly as written, so such a line is not a date. It gets the ordinary shape message, for
        # both fields, and the same value in plain ASCII digits loads
        cases = [('２０２６-０７-０５', '2026-07-05'),                       # full-width digits in the date
                 ('2026-07-05T１０:００:００Z', '2026-07-05T10:00:00Z'),     # ... in the time alone
                 ('٢٠٢٦-٠٧-٠٥', '2026-07-05'),                                # Arabic-Indic digits
                 ('2026-07-0５', '2026-07-05'),                                # one full-width digit among nine plain ones
                 ('2026-07-05T10:00:00+０２:００', '2026-07-05T10:00:00+02:00')]   # ... in the offset alone
        for typed, plain in cases:
            self.assertNotEqual(typed, plain)
            self.assertEqual(len(typed), len(plain))
            self.assertFalse(typed.isascii())
            self.assertTrue(plain.isascii())
            with self.subTest(typed=typed):
                self.refused(SHAPE % ('published_at', typed), ['published_at: ' + typed])
            with self.subTest(typed=typed, field='updated_at'):
                self.refused(SHAPE % ('updated_at', typed), ['published_at: 2026-07-01', 'updated_at: ' + typed])
            with self.subTest(plain=plain):
                self.assertEqual(self.trip(['published_at: ' + plain])['published_at'], plain)
            with self.subTest(plain=plain, field='updated_at'):
                t = self.trip(['published_at: 2026-07-01', 'updated_at: ' + plain])
                self.assertEqual((t['published_at'], t['updated_at']), ('2026-07-01', plain))
        # the whole message, spelled out once for each of the three the task names
        shape = ('published_at must be a date written YYYY-MM-DD, or a date and time with an offset such as '
                 '2026-10-03T18:30:00-07:00, got %s')
        self.refused(shape % "'２０２６-０７-０５'", ['published_at: ２０２６-０７-０５'])
        self.refused(shape % "'2026-07-05T１０:００:００Z'", ['published_at: 2026-07-05T１０:００:００Z'])
        self.refused(shape % "'٢٠٢٦-٠٧-٠٥'", ['published_at: ٢٠٢٦-٠٧-٠٥'])
        # quoted, the value is the same string and is refused the same way
        self.refused(shape % "'２０２６-０７-０５'", ['published_at: "２０２６-０７-０５"'])

    # ------------------------------------------------------------ the future

    def test_tomorrow_is_tolerated_and_the_day_after_is_the_future(self):
        ok, late = (TODAY + timedelta(days=1)).isoformat(), (TODAY + timedelta(days=2)).isoformat()
        self.assertEqual((ok, late), ('2031-05-21', '2031-05-22'))
        self.assertEqual(self.trip(['published_at: ' + TODAY.isoformat()])['published_at'], TODAY.isoformat())
        self.assertEqual(self.trip(['published_at: ' + ok])['published_at'], ok)
        self.refused('published_at 2031-05-22 is in the future', ['published_at: ' + late])

    def test_the_future_is_measured_from_the_patched_today_not_from_the_clock(self):
        # 2020-01-03 is years ago for the real clock; on a build that runs on 2020-01-01 it is the future
        early = date(2020, 1, 1)
        self.assertEqual(self.trip(['published_at: 2020-01-02'], today=early, date='2019-12-01')['published_at'], '2020-01-02')
        self.refused(FUTURE % ('published_at', '2020-01-03'), ['published_at: 2020-01-03'], today=early, date='2019-12-01')
        # and a day that is the future today is fine once today has moved on
        self.assertEqual(self.trip(['published_at: 2031-05-22'], today=date(2031, 5, 21))['published_at'], '2031-05-22')

    def test_a_future_time_is_refused_as_typed(self):
        ok, late = '2031-05-21T23:59:00-07:00', '2031-05-22T00:01:00-07:00'
        self.assertEqual(self.trip(['published_at: ' + ok])['published_at'], ok)
        self.refused(FUTURE % ('published_at', late), ['published_at: ' + late])

    def test_updated_at_has_the_same_tolerance(self):
        t = self.trip(['published_at: 2031-05-19', 'updated_at: 2031-05-21'])
        self.assertEqual(t['updated_at'], '2031-05-21')
        self.refused('updated_at 2031-05-22 is in the future', ['published_at: 2031-05-19', 'updated_at: 2031-05-22'])
        self.refused(FUTURE % ('updated_at', '2031-05-22T09:00Z'), ['published_at: 2031-05-19', 'updated_at: 2031-05-22T09:00Z'])

    # ------------------------------------------------------------ never before the trip

    def test_published_before_the_trip_date_is_refused(self):
        self.refused('published_at 2026-05-31 is before the trip itself (2026-06-01); it is the day the report went online, '
                     'not the trip date', ['published_at: 2026-05-31'])
        self.refused(BEFORE_TRIP % ('2026-05-31T23:00:00-07:00', '2026-06-01'), ['published_at: 2026-05-31T23:00:00-07:00'])
        self.refused(BEFORE_TRIP % ('2020-01-01', '2026-06-01'), ['published_at: 2020-01-01'])

    def test_published_on_the_trip_day_is_accepted(self):
        self.assertEqual(self.trip(['published_at: 2026-06-01'])['published_at'], '2026-06-01')
        self.assertEqual(self.trip(['published_at: 2026-06-01T06:00:00-07:00'])['published_at'], '2026-06-01T06:00:00-07:00')

    def test_a_multi_day_trip_is_measured_from_its_first_day(self):
        # contract 10.3: published_at is compared with the trip's FIRST day (it was the last): a multi-day page can go
        # online while the trip is under way. From the first day on it is accepted; the day before is refused, and the
        # message names the first day
        days = [{'date': '2026-03-10'}, {'date': '2026-03-11'}, {'date': '2026-03-12'}]
        tour = dict(kind='multi-day', date='2026-03-10', end_date='2026-03-12', days=days)
        for v in ('2026-03-10', '2026-03-11', '2026-03-12', '2026-03-13', '2026-03-10T00:00:00-07:00', '2026-03-11T23:59Z'):
            with self.subTest(published_at=v):
                self.assertEqual(self.trip(['published_at: ' + v], **tour)['published_at'], v)
        self.refused('published_at 2026-03-09 is before the trip itself (2026-03-10); it is the day the report went online, '
                     'not the trip date', ['published_at: 2026-03-09'], **tour)
        self.refused(BEFORE_TRIP % ('2026-03-09T23:59:59-07:00', '2026-03-10'), ['published_at: 2026-03-09T23:59:59-07:00'], **tour)
        self.refused(BEFORE_TRIP % ('2020-01-01', '2026-03-10'), ['published_at: 2020-01-01'], **tour)

    def test_the_first_day_counts_when_date_is_not_written(self):
        # a multi-day trip without date / end_date lines takes both from its day files: the first day file's date is the
        # one published_at is held against
        days = [{'date': '2026-03-10'}, {'date': '2026-03-11'}]
        t = self.trip(['published_at: 2026-03-10'], kind='multi-day', date=None, days=days)
        self.assertEqual((t['published_at'], t['date'].isoformat(), t['end_date'].isoformat()), ('2026-03-10', '2026-03-10', '2026-03-11'))
        self.assertEqual(self.trip(['published_at: 2026-03-11'], kind='multi-day', date=None, days=days)['published_at'], '2026-03-11')
        self.refused(BEFORE_TRIP % ('2026-03-09', '2026-03-10'), ['published_at: 2026-03-09'], kind='multi-day', date=None, days=days)

    def test_a_journal_is_measured_from_its_first_day(self):
        journal = dict(kind='series', date='2024-04-22', end_date='2024-09-21', days=[{'id': '001', 'date': '2024-04-22'}])
        for v in ('2024-04-22', '2024-04-23', '2024-09-20', '2024-09-21', '2024-09-22'):
            with self.subTest(published_at=v):
                self.assertEqual(self.trip(['published_at: ' + v], **journal)['published_at'], v)
        self.refused(BEFORE_TRIP % ('2024-04-21', '2024-04-22'), ['published_at: 2024-04-21'], **journal)
        # without a date line in index.md the first day file's date stands in
        days = [{'id': '001', 'date': '2024-04-22'}, {'id': '002', 'date': '2024-04-25'}]
        self.assertEqual(self.trip(['published_at: 2024-04-22'], kind='series', date=None, days=days)['published_at'], '2024-04-22')
        self.refused(BEFORE_TRIP % ('2024-04-21', '2024-04-22'), ['published_at: 2024-04-21'], kind='series', date=None, days=days)

    def test_a_journal_that_went_online_under_way_stays_valid_when_days_are_added(self):
        # the reviewer's scenario: a journal published on 2026-10-02 with its first day (2026-10-01) written; a week later
        # day 002 (2026-10-08) is added. The true publication date must not become an error
        slug = self.slug()
        one = [{'id': '001', 'title': 'Synthetic Camp One', 'date': '2026-10-01'}]
        two = one + [{'id': '002', 'title': 'Synthetic Camp Two', 'date': '2026-10-08'}]
        t = self.trip(slug=slug, kind='series', date=None, published_at='2026-10-02', days=one)
        self.assertEqual((t['published_at'], t['date'].isoformat(), t['end_date'].isoformat()), ('2026-10-02', '2026-10-01', '2026-10-01'))
        t = self.trip(slug=slug, kind='series', date=None, published_at='2026-10-02', days=two)
        self.assertEqual([d['id'] for d in t['days']], ['001', '002'])
        self.assertEqual((t['published_at'], t['date'].isoformat(), t['end_date'].isoformat()), ('2026-10-02', '2026-10-01', '2026-10-08'))
        # ... with the range written in index.md as well, and for a multi-day trip
        t = self.trip(kind='series', date='2026-10-01', end_date='2026-10-08', published_at='2026-10-02', days=two)
        self.assertEqual(t['published_at'], '2026-10-02')
        t = self.trip(kind='multi-day', date=None, published_at='2026-10-02', days=[dict(d, id=d['id'][1:]) for d in two])
        self.assertEqual((t['published_at'], t['end_date'].isoformat()), ('2026-10-02', '2026-10-08'))
        # an update after the new day is fine; the day before the first day still is not a publication date
        t = self.trip(kind='series', date=None, published_at='2026-10-02', updated_at='2026-10-09', days=two)
        self.assertEqual((t['published_at'], t['updated_at']), ('2026-10-02', '2026-10-09'))
        self.refused(BEFORE_TRIP % ('2026-09-30', '2026-10-01'), kind='series', date=None, published_at='2026-09-30', days=two)

    def test_the_trip_day_is_the_date_or_else_the_end_date(self):
        # contract 10.3: `t['date'] or t['end_date']`. A trip that states only when it ended is held against that day
        self.assertEqual(self.trip(['published_at: 2026-06-10'], date=None, end_date='2026-06-10')['published_at'], '2026-06-10')
        self.refused(BEFORE_TRIP % ('2026-06-09', '2026-06-10'), ['published_at: 2026-06-09'], date=None, end_date='2026-06-10')
        # a single-day report with both: the first day
        self.assertEqual(self.trip(['published_at: 2026-06-01'], end_date='2026-06-03')['published_at'], '2026-06-01')

    # ------------------------------------------------------------ a draft may name the day it is planned to go online

    def test_a_draft_is_not_checked_for_the_future(self):
        # contract 10.3: a draft is not online, so its published_at (and updated_at) may lie ahead of today
        for lines in (['published_at: 2031-05-22'], ['published_at: 2031-06-01'], ['published_at: 2040-01-01T09:00:00-07:00'],
                      ['published_at: 2031-05-19', 'updated_at: 2031-05-22'], ['published_at: 2031-06-01', 'updated_at: 2031-06-02'],
                      ['published_at: 2031-06-01T09:00Z', 'updated_at: 2035-01-01T09:00Z']):
            with self.subTest(lines=lines):
                t = self.trip(lines, draft=True)
                self.assertIs(t['draft'], True)
                self.assertEqual(t['published_at'], lines[0].split(': ', 1)[1])
                self.assertEqual(t['updated_at'], lines[1].split(': ', 1)[1] if len(lines) > 1 else None)
        # on every kind of report
        t = self.trip(['published_at: 2031-06-01'], draft=True, kind='multi-day', days=[{'date': '2026-06-01'}, {'date': '2026-06-02'}])
        self.assertEqual(t['published_at'], '2031-06-01')
        t = self.trip(['published_at: 2031-06-01'], draft=True, kind='series', days=[{'id': '001', 'date': '2026-06-01'}])
        self.assertEqual(t['published_at'], '2031-06-01')

    def test_the_same_file_without_the_draft_flag_is_refused(self):
        # ... and the check applies again the moment the flag comes off (or is written as false)
        for lines, message in ((['published_at: 2031-05-22'], FUTURE % ('published_at', '2031-05-22')),
                               (['published_at: 2031-06-01'], FUTURE % ('published_at', '2031-06-01')),
                               (['published_at: 2031-05-19', 'updated_at: 2031-05-22'], FUTURE % ('updated_at', '2031-05-22'))):
            with self.subTest(lines=lines):
                self.assertEqual(self.trip(lines, draft=True)['published_at'], lines[0].split(': ', 1)[1])
                self.refused(message, lines)
                self.refused(message, lines, draft=False)
                self.refused(message, lines + ['draft: false'])
        self.refused('published_at 2031-06-01 is in the future', ['published_at: 2031-06-01'])

    def test_every_other_check_still_applies_to_a_draft(self):
        # a malformed value, an impossible one, updated_at alone, updated before published, published before the trip, a
        # planned route: a draft is refused for each exactly as a published report is
        cases = [(SHAPE % ('published_at', '10/03/2031'), ['published_at: 10/03/2031']),
                 (SHAPE % ('published_at', '2031-06-01T09:00'), ['published_at: 2031-06-01T09:00']),
                 (SHAPE % ('updated_at', 'soon'), ['published_at: 2031-06-01', 'updated_at: soon']),
                 (NOT_REAL % ('published_at', '2031-02-30'), ['published_at: 2031-02-30']),
                 (NOT_REAL % ('published_at', '2031-06-01T09:00+14:30'), ['published_at: 2031-06-01T09:00+14:30']),
                 (NEEDS, ['updated_at: 2031-06-01']),
                 (NEEDS, ['updated_at: 2026-10-05']),
                 (BEFORE_PUB % ('2031-05-31', '2031-06-01'), ['published_at: 2031-06-01', 'updated_at: 2031-05-31']),
                 (BEFORE_PUB % ('2026-10-02', '2026-10-03'), ['published_at: 2026-10-03', 'updated_at: 2026-10-02']),
                 (BEFORE_TRIP % ('2026-05-31', '2026-06-01'), ['published_at: 2026-05-31'])]
        for message, lines in cases:
            with self.subTest(lines=lines):
                self.refused(message, lines, draft=True)
        self.refused(PLANNED % 'published_at', ['published_at: 2031-06-01'], draft=True, kind='planned', date=None)
        # and a draft whose dates are sound in every other respect loads
        t = self.trip(['published_at: 2031-06-01', 'updated_at: 2031-06-01'], draft=True)
        self.assertEqual((t['published_at'], t['updated_at']), ('2031-06-01', '2031-06-01'))

    # ------------------------------------------------------------ updated_at against published_at

    def test_updated_at_without_published_at_is_refused(self):
        self.refused('updated_at needs published_at (the day the report first went online)', ['updated_at: 2026-10-05'])
        self.refused(NEEDS, ['updated_at: 2026-10-05T08:00Z'])
        self.refused(NEEDS, ['published_at:', 'updated_at: 2026-10-05'])

    def test_updated_before_published_by_date_is_refused(self):
        self.refused('updated_at 2026-10-02 is before published_at 2026-10-03', ['published_at: 2026-10-03', 'updated_at: 2026-10-02'])
        t = self.trip(['published_at: 2026-10-03', 'updated_at: 2026-10-03'])     # the same day is not "before"
        self.assertEqual((t['published_at'], t['updated_at']), ('2026-10-03', '2026-10-03'))

    def test_updated_before_published_by_time_is_refused(self):
        pub = '2026-10-03T18:30:00-07:00'
        self.refused(BEFORE_PUB % ('2026-10-03T18:29:59-07:00', pub), ['published_at: ' + pub, 'updated_at: 2026-10-03T18:29:59-07:00'])
        self.assertEqual(self.trip(['published_at: ' + pub, 'updated_at: ' + pub])['updated_at'], pub)
        self.assertEqual(self.trip(['published_at: ' + pub, 'updated_at: 2026-10-03T18:30:01-07:00'])['updated_at'],
                         '2026-10-03T18:30:01-07:00')

    def test_two_times_are_compared_as_moments_across_offsets(self):
        # 18:30 at -07:00 is 01:30 UTC the next day: an update typed as 01:00Z on that next day came half an hour earlier
        pub, earlier = '2026-10-03T18:30:00-07:00', '2026-10-04T01:00:00Z'
        self.refused('updated_at 2026-10-04T01:00:00Z is before published_at 2026-10-03T18:30:00-07:00',
                     ['published_at: ' + pub, 'updated_at: ' + earlier])
        # the other way round the update's date reads earlier, but its moment is later
        t = self.trip(['published_at: ' + earlier, 'updated_at: ' + pub])
        self.assertEqual((t['published_at'], t['updated_at']), (earlier, pub))

    def test_a_date_and_a_time_are_compared_by_day(self):
        pub = '2026-10-03T18:30:00-07:00'
        self.assertEqual(self.trip(['published_at: ' + pub, 'updated_at: 2026-10-03'])['updated_at'], '2026-10-03')
        self.refused(BEFORE_PUB % ('2026-10-02', pub), ['published_at: ' + pub, 'updated_at: 2026-10-02'])
        self.refused(BEFORE_PUB % ('2026-10-02T23:59:00-07:00', '2026-10-03'),
                     ['published_at: 2026-10-03', 'updated_at: 2026-10-02T23:59:00-07:00'])
        self.assertEqual(self.trip(['published_at: 2026-10-03', 'updated_at: 2026-10-03T00:00:00-07:00'])['updated_at'],
                         '2026-10-03T00:00:00-07:00')

    # ------------------------------------------------------------ planned routes

    def test_either_field_on_a_planned_route_is_refused(self):
        self.refused('published_at is for a report; this is a planned route (kind: planned)', ['published_at: 2026-10-03'],
                     kind='planned', date=None)
        self.refused('updated_at is for a report; this is a planned route (kind: planned)', ['updated_at: 2026-10-03'],
                     kind='planned', date=None)
        self.refused(PLANNED % 'published_at', ['published_at: 2026-10-03', 'updated_at: 2026-10-04'], kind='planned', date=None)

    def test_a_refusal_is_a_content_error_that_names_the_file_and_the_field(self):
        slug = self.slug()
        with self.assertRaises(content.ContentError) as cm:
            self.trip(['published_at: 2026'], slug=slug)
        self.assertIsInstance(cm.exception, ValueError)
        self.assertTrue(str(cm.exception).startswith('content/trips/%s/index.md: published_at ' % slug))


# ================================================================ 2. core._share_tags and core.document(image=...)

def tag_pairs(html_):
    return metas(Doc(html_).root)


class ShareTagTests(unittest.TestCase):

    PATH = 'trips/synm-x/photos/01.webp'

    def tags(self, **image):
        image.setdefault('path', self.PATH)
        return core._share_tags(image)

    def test_no_image_is_exactly_the_summary_card(self):
        for image in (None, '', {}):
            with self.subTest(image=image):
                self.assertEqual(core._share_tags(image), '<meta name="twitter:card" content="summary">')

    def test_a_share_photo_writes_seven_tags_in_order(self):
        out = self.tags(w=1600, h=1200, alt='Synthetic alt')
        self.assertEqual(tag_pairs(out), [('og:image', U + self.PATH), ('og:image:type', 'image/webp'), ('og:image:width', '1600'),
                                          ('og:image:height', '1200'), ('og:image:alt', 'Synthetic alt'),
                                          ('twitter:card', 'summary_large_image'), ('twitter:image:alt', 'Synthetic alt')])
        self.assertEqual(out.count('<meta '), 7)

    def test_open_graph_tags_use_property_and_twitter_tags_use_name(self):
        doc = Doc(self.tags(w=1600, h=1200, alt='Synthetic alt'))
        for m in doc.find_all('meta'):
            key = m['property'] or m['name']
            self.assertEqual('property' in m, key.startswith('og:'), key)
            self.assertEqual('name' in m, key.startswith('twitter:'), key)

    def test_width_and_height_are_written_only_as_a_pair_of_positive_whole_numbers(self):
        without = ['og:image', 'og:image:type', 'og:image:alt', 'twitter:card', 'twitter:image:alt']
        for w, h in ((None, None), (1600, None), (None, 1200), (0, 1200), (1600, 0), (0, 0), ('1600', '1200'), ('1600', 1200),
                     (1600, '1200'), (True, True), (True, 1200), (1600, True), (-1600, 1200), (1600, -1200), (1600.5, 1200)):
            with self.subTest(w=w, h=h):
                out = self.tags(w=w, h=h, alt='Synthetic alt')
                self.assertEqual([k for k, _v in tag_pairs(out)], without)
                self.assertNotIn('og:image:width', out)
                self.assertNotIn('og:image:height', out)
        out = core._share_tags({'path': self.PATH, 'alt': 'Synthetic alt'})      # the keys not there at all
        self.assertEqual([k for k, _v in tag_pairs(out)], without)

    def test_the_recorded_numbers_are_written_as_they_are(self):
        pairs = dict(tag_pairs(self.tags(w=738, h=1600, alt='')))
        self.assertEqual((pairs['og:image:width'], pairs['og:image:height']), ('738', '1600'))

    def test_alt_tags_are_written_only_for_a_recorded_description(self):
        for alt in ('', None):
            with self.subTest(alt=alt):
                out = self.tags(w=1600, h=1200, alt=alt)
                self.assertEqual([k for k, _v in tag_pairs(out)],
                                 ['og:image', 'og:image:type', 'og:image:width', 'og:image:height', 'twitter:card'])
                self.assertNotIn(':alt', out)
        out = core._share_tags({'path': self.PATH, 'w': 1600, 'h': 1200})
        self.assertNotIn(':alt', out)
        self.assertIn(('twitter:card', 'summary_large_image'), tag_pairs(out))

    def test_alt_is_written_verbatim_and_escaped(self):
        out = self.tags(w=1600, h=1200, alt=COVER_ALT)
        pairs = tag_pairs(out)
        self.assertEqual([v for k, v in pairs if k in ('og:image:alt', 'twitter:image:alt')], [COVER_ALT, COVER_ALT])
        self.assertEqual(len(pairs), 7)                     # a quote in the alt closed no attribute
        self.assertNotIn('<angled>', out)
        self.assertNotIn('"quoted"', out)
        self.assertIn('&amp;', out)

    def test_type_follows_the_extension(self):
        cases = [('01.webp', 'image/webp'), ('01.jpg', 'image/jpeg'), ('01.jpeg', 'image/jpeg'), ('01.png', 'image/png'),
                 ('01.gif', 'image/gif'), ('01.WEBP', 'image/webp'), ('01.JPG', 'image/jpeg'), ('01.Jpeg', 'image/jpeg'),
                 ('01.PNG', 'image/png'), ('01.GIF', 'image/gif'), ('01.th.webp', 'image/webp')]
        for name, kind in cases:
            with self.subTest(name=name):
                path = 'trips/synm-x/photos/' + name
                self.assertEqual(tag_pairs(core._share_tags({'path': path, 'w': 10, 'h': 10, 'alt': 'a'}))[:2],
                                 [('og:image', U + path), ('og:image:type', kind)])

    def test_an_unknown_extension_gives_no_type(self):
        for name in ('01.svg', '01.avif', '01.tiff', '01', '01.webp.bak', 'webp'):
            with self.subTest(name=name):
                out = core._share_tags({'path': 'trips/synm-x/photos/' + name, 'w': 10, 'h': 10, 'alt': 'a'})
                self.assertNotIn('og:image:type', out)
                self.assertEqual([k for k, _v in tag_pairs(out)],
                                 ['og:image', 'og:image:width', 'og:image:height', 'og:image:alt', 'twitter:card', 'twitter:image:alt'])

    def test_a_plain_path_gives_the_image_its_type_and_the_large_card(self):
        self.assertEqual(tag_pairs(core._share_tags(self.PATH)),
                         [('og:image', U + self.PATH), ('og:image:type', 'image/webp'), ('twitter:card', 'summary_large_image')])
        self.assertEqual(tag_pairs(core._share_tags('trips/synm-x/photos/01.bin')),
                         [('og:image', U + 'trips/synm-x/photos/01.bin'), ('twitter:card', 'summary_large_image')])

    def test_the_image_url_is_absolute_under_the_site_url(self):
        url = dict(tag_pairs(self.tags(w=1, h=1)))['og:image']
        self.assertTrue(url.startswith('https://'))
        self.assertEqual(url, core.SITE_URL + self.PATH)


class DocumentHeadTests(TempCase):
    """core.document() itself, with nothing registered."""

    HERE = 'trips/synm-x/'
    IMAGE = {'path': 'trips/synm-x/photos/01.webp', 'w': 1600, 'h': 1200, 'alt': COVER_ALT}

    def document(self, here=None, **kw):
        with sandbox(self.tmp):
            core.register_site({'trips': []})
            return core.document(self.HERE if here is None else here, 'Synthetic Title', '<p>Synthetic body.</p>',
                                 'Synthetic description.', **kw)

    def test_the_share_tags_follow_og_url_and_nothing_comes_between_them(self):
        html_ = self.document(image=self.IMAGE)
        keys = [k for k, _v in metas(Doc(html_).find('head'))]
        self.assertEqual(keys, ['viewport', 'description', 'og:type', 'og:title', 'og:description', 'og:site_name', 'og:locale',
                                'og:url', 'og:image', 'og:image:type', 'og:image:width', 'og:image:height', 'og:image:alt',
                                'twitter:card', 'twitter:image:alt', 'theme-color'])
        self.assertIn(core._share_tags(self.IMAGE), html_)

    def test_a_page_without_an_image_keeps_the_tags_it_had(self):
        # contract 4.2: byte-identical to before in these tags, but for the site's name and locale (Phase 14, seo-03)
        canon = U + self.HERE
        for kw in ({}, {'image': None}, {'image': ''}):
            with self.subTest(kw=kw):
                html_ = self.document(**kw)
                self.assertIn('<link rel="canonical" href="%s">'
                              '<meta property="og:type" content="website"><meta property="og:title" content="Synthetic Title · %s">'
                              '<meta property="og:description" content="Synthetic description.">'
                              '<meta property="og:site_name" content="Eric Sichak"><meta property="og:locale" content="en_US">'
                              '<meta property="og:url" content="%s"><meta name="twitter:card" content="summary">'
                              '<meta name="theme-color" content="#FFFFFF">' % (canon, core.SITE_NAME, canon), html_)
                self.assertNotIn('og:image', html_)
                self.assertNotIn('twitter:image', html_)

    def test_a_plain_path_still_works(self):
        html_ = self.document(image='trips/synm-x/photos/01.webp')
        self.assertEqual(share_run(metas(Doc(html_).find('head'))),
                         [('og:image', U + 'trips/synm-x/photos/01.webp'), ('og:image:type', 'image/webp'),
                          ('twitter:card', 'summary_large_image')])

    def test_canonical_false_writes_neither_canonical_nor_og_url_and_changes_nothing_else(self):
        with_, without = self.document(), self.document(canonical=False)
        canon = U + self.HERE
        link, og_url = '<link rel="canonical" href="%s">' % canon, '<meta property="og:url" content="%s">' % canon
        self.assertEqual(with_.count(link), 1)
        self.assertEqual(with_.count(og_url), 1)
        self.assertNotIn('rel="canonical"', without)
        self.assertNotIn('og:url', without)
        self.assertEqual(with_.replace(link, '').replace(og_url, ''), without)

    def test_canonical_is_the_site_url_plus_the_page_url(self):
        for here, want in (('', U), ('about/', U + 'about/'), ('trips/synm-x/', U + 'trips/synm-x/'),
                           ('trips/synm-x/map/', U + 'trips/synm-x/map/'), ('about/index.html', U + 'about/'), ('index.html', U)):
            with self.subTest(here=here):
                doc = Doc(self.document(here=here))
                self.assertEqual([ln['href'] for ln in doc.find_all('link', attrs={'rel': 'canonical'})], [want])
                self.assertEqual([v for k, v in metas(doc.find('head')) if k == 'og:url'], [want])

    def test_without_a_report_there_is_no_article_meta_and_no_structured_data(self):
        html_ = self.document(image=self.IMAGE, og_type='article')
        self.assertNotIn('article:', html_)
        self.assertNotIn('ld+json', html_)


class SharePhotoTests(TempCase):

    def load(self, **meta):
        s = self.site()
        s.add('synm-one', **meta)
        return s.load()['by_slug']['synm-one']

    def test_share_photo_is_the_cover_with_what_content_records_for_it(self):
        t = self.load(date='2026-06-01', cover_photo='photos/02.webp',
                      photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic first'), photo('photos/02.webp', (1400, 1000), alt=COVER_ALT)])
        self.assertEqual(core.share_photo(t), {'path': 'trips/synm-one/photos/02.webp', 'w': 1400, 'h': 1000, 'alt': COVER_ALT})

    def test_share_photo_of_a_day_cover(self):
        t = self.load(kind='multi-day', days=[{'date': '2026-06-01'},
                                              {'date': '2026-06-02', 'photos': [photo('photos/d2.webp', LANDSCAPE, alt='Synthetic day')]}])
        self.assertEqual(core.share_photo(t), {'path': 'trips/synm-one/photos/d2.webp', 'w': 1600, 'h': 1200, 'alt': 'Synthetic day'})

    def test_share_photo_keeps_missing_size_and_alt_missing(self):
        t = self.load(date='2026-06-01', photos=[photo('photos/01.webp', None, alt='')])
        self.assertEqual(core.share_photo(t), {'path': 'trips/synm-one/photos/01.webp', 'w': None, 'h': None, 'alt': ''})
        self.assertEqual(tag_pairs(core._share_tags(core.share_photo(t))),
                         [('og:image', U + 'trips/synm-one/photos/01.webp'), ('og:image:type', 'image/webp'),
                          ('twitter:card', 'summary_large_image')])

    def test_one_recorded_dimension_alone_is_never_written(self):
        s = self.site()
        folder = s.add('synm-one', date='2026-06-01', photos=[{'file': 'photos/01.webp', 'w': 1600, 'alt': 'Synthetic wide'}])
        self.assertIn('w: 1600', open_text(os.path.join(folder, 'index.md')))
        share = core.share_photo(s.load()['by_slug']['synm-one'])
        self.assertEqual((share['w'], share['h']), (1600, None))
        out = core._share_tags(share)
        self.assertNotIn('og:image:width', out)
        self.assertNotIn('og:image:height', out)
        self.assertEqual(dict(tag_pairs(out))['og:image:alt'], 'Synthetic wide')

    def test_no_photo_no_share_photo(self):
        self.assertIsNone(core.share_photo(self.load(date='2026-06-01', track=True)))
        self.assertIsNone(core.share_photo(None))

    def test_site_share_is_the_first_featured_trips_cover_once_registered(self):
        s = self.site()
        s.add('synm-newest', date='2026-07-01', photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic newest')])
        s.add('synm-plain', date='2026-06-15')
        s.add('synm-lead', date='2026-06-01', photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic lead')])
        s.add('synm-second', date='2026-05-01', photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic second')])
        with sandbox(s.root):
            site = module('build').site_of(helpers.load_dir(s.trips_dir))
            by = site['by_slug']
            lead = {'path': 'trips/synm-lead/photos/01.webp', 'w': 1600, 'h': 1200, 'alt': 'Synthetic lead'}
            cases = [(['synm-lead', 'synm-second'], lead), (['synm-lead'], lead),
                     (['synm-second', 'synm-lead'], dict(lead, path='trips/synm-second/photos/01.webp', alt='Synthetic second')),
                     ([], None),                               # nothing featured: nothing, never the newest report's photo
                     (['synm-plain', 'synm-lead'], None)]      # the lead has no photo: nothing, never the next feature's
            for slugs, want in cases:
                with self.subTest(featured=slugs):
                    site['featured'] = [by[x] for x in slugs]
                    core.register_site(site)
                    self.assertEqual(core.site_share(), want)
            del site['featured']                                # a site dict without the key (unit tests of other modules)
            core.register_site(site)
            self.assertIsNone(core.site_share())

    def test_without_a_feature_no_site_page_borrows_a_reports_photo(self):
        # the newest report has a photo and nothing is featured: Home, About, Map, Trips and Tick list share no image
        s = self.site()
        s.add('synm-newest', date='2026-07-01', region=REGION, track=True, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic newest')])
        s.add('synm-flagged', date='2026-06-01', region=REGION, track=True, featured=True,
              photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic flagged')])
        built = s.build([], only=('home', 'about', 'archive', 'trips', 'ticklist'))
        self.assertEqual(sorted(built.html_urls()), ['', 'about/', 'map/', 'tick-list/', 'trips/'])
        for url in built.html_urls():
            with self.subTest(page=url or '(home)'):
                self.assertEqual(share_run(built.metas(url)), NO_SHARE)
                self.assertNotIn('og:image', built.html(url))

    def test_the_sandbox_puts_the_registered_site_back(self):
        before = (dict(core._TRIPS_BY_URL), list(core._OTHER_SUBS), core._HAS_PCT[0], core._SITE_SHARE[0])
        s = self.site()
        s.add('synm-lead', date='2026-06-01', photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic lead')])
        s.build(['synm-lead'])
        self.assertEqual((dict(core._TRIPS_BY_URL), list(core._OTHER_SUBS), core._HAS_PCT[0], core._SITE_SHARE[0]), before)


def open_text(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


# ================================================================ 3. the head of every page type

class FixtureCase(unittest.TestCase):

    def setUp(self):
        self.fx = fixture()
        self.feat, self.bare = self.fx.feat, self.fx.bare

    def assertShares(self, built, url, slug):
        """The page's share tags are exactly those of `slug`'s cover (None: the summary card and no image)."""
        got = share_run(built.metas(url))
        want = expected_share(*COVER[slug]) if slug else NO_SHARE
        self.assertEqual(got, want, 'share tags of %r' % url)


class FixtureTests(FixtureCase):
    """The fixture is what the docstring says, so the tables above mean what they say."""

    def test_the_build_gives_exactly_these_pages(self):
        want = ([''] + SITE_PAGES + SECTIONS + ['trips/%s/' % s for s in REPORTS + GOALS] + HELPERS + ['404.html'] + JSON_PAGES)
        for built in (self.feat, self.bare):
            self.assertEqual(sorted(p.url for p in built.pages), sorted(want))
            self.assertEqual(len(built.pages), len(want))             # no URL twice

    def test_the_draft_is_not_on_the_site(self):
        self.assertNotIn('synm-draft', self.feat.by)
        self.assertFalse([u for u in self.feat.by_url if 'synm-draft' in u])
        for url in self.feat.html_urls():
            self.assertNotIn('synm-draft', self.feat.html(url), url)

    def test_the_features_are_not_simply_the_newest_reports(self):
        published = [t['slug'] for t in self.feat.site['published']]
        self.assertEqual(published[0], 'synm-newest')
        self.assertEqual([t['slug'] for t in self.feat.site['featured']], FEATURED)
        self.assertEqual(self.bare.site['featured'], [])

    def test_the_covers_are_the_ones_the_table_names(self):
        for slug in REPORTS + GOALS:
            t = self.feat.by[slug]
            if slug not in COVER:
                self.assertIsNone(t['cover'], slug)
                continue
            path, w, h, alt = COVER[slug]
            p = t['cover']['photo']
            self.assertEqual((t['url'] + p['file'], p['w'], p['h'], p['alt']), (path, w, h, alt), slug)
            self.assertTrue(os.path.isfile(os.path.join(self.feat.trips_dir, slug, p['file'])), slug)
        # the covers that prove something: not the first photo of the trip, and for the tour and the journal a day's
        for slug in ('synm-story', 'synm-compact', 'synm-flag', 'synm-goal'):
            self.assertNotEqual(self.feat.by[slug]['cover']['photo']['file'], self.feat.by[slug]['photos'][0]['file'], slug)
        for slug in ('synm-tour', 'synm-journal'):
            self.assertEqual(self.feat.by[slug]['photos'], [], slug)

    def test_the_write_ups_sit_on_the_sides_of_the_minimum_the_docstring_says(self):
        n = core.STRUCTURED_MIN_CHARS
        self.assertEqual(n, 100)
        self.assertGreaterEqual(len(markdown.plain(LONG)), n)
        self.assertGreaterEqual(len(markdown.plain(NOTES)), n)
        self.assertLess(len(markdown.plain(SHORT)), n)
        self.assertLess(len(markdown.plain(DAY_ONE)), n)
        self.assertLess(len(markdown.plain(DAY_TWO)), n)
        self.assertGreaterEqual(len(markdown.plain(DAY_ONE)) + len(markdown.plain(DAY_TWO)), n)
        self.assertEqual(self.feat.by['synm-tour']['body_md'], '')
        self.assertEqual(self.feat.by['synm-journal']['body_md'], '')
        self.assertEqual([s for s in REPORTS + GOALS if core.written_report(self.feat.by[s])], WRITTEN)

    def test_the_layouts_are_the_ones_the_docstring_names(self):
        report = page_module('report')
        self.assertEqual([s for s in REPORTS if report.narrative(self.feat.by[s])], ['synm-story', 'synm-short', 'synm-nosize'])
        self.assertIn('p-report--story', self.feat.html('trips/synm-story/'))
        self.assertNotIn('p-report--story', self.feat.html('trips/synm-compact/'))
        self.assertIn('p-multiday', self.feat.html('trips/synm-tour/'))
        self.assertIn('p-series', self.feat.html('trips/synm-journal/'))
        self.assertIn('p-goal', self.feat.html('trips/synm-goal/'))
        self.assertIn('p-fsmap', self.feat.html('trips/synm-story/map/'))


class HeadContractTests(FixtureCase):

    def html_pages(self, *builds):
        """[(build, url)] of every HTML page of the fixture, with and without features (or of the builds given)."""
        return [(b, url) for b in (builds or (self.feat, self.bare)) for url in b.html_urls()]

    def sub(self, b, url):
        return self.subTest(page=url or '(home)', featured=b is self.feat)

    def test_every_page_has_exactly_one_title(self):
        for b, url in self.html_pages():
            with self.sub(b, url):
                head_html = b.html(url).split('</head>', 1)[0]
                self.assertEqual(len(re.findall(r'<title\b', head_html)), 1)
                self.assertEqual(len(b.head(url).find_all('title')), 1)
                self.assertTrue(b.head(url).find('title').text())

    def test_every_page_has_exactly_one_meta_description(self):
        for b, url in self.html_pages():
            with self.sub(b, url):
                found = b.doc(url).find_all('meta', attrs={'name': 'description'})
                self.assertEqual(len(found), 1)
                self.assertTrue(found[0]['content'].strip())
                self.assertEqual(b.html(url).count('name="description"'), 1)

    def test_every_page_but_the_404_has_one_canonical_equal_to_its_own_url(self):
        for b, url in self.html_pages():
            if url == '404.html':
                continue
            with self.sub(b, url):
                self.assertEqual(b.canonicals(url), [U + url])
                self.assertEqual(b.html(url).count('rel="canonical"'), 1)
                self.assertNotIn('index.html', b.canonicals(url)[0])

    def test_og_url_is_the_canonical(self):
        for b, url in self.html_pages():
            if url == '404.html':
                continue
            with self.sub(b, url):
                self.assertEqual(b.meta(url, 'og:url'), [U + url])
                self.assertEqual(b.meta(url, 'og:url'), b.canonicals(url))
                self.assertEqual(b.html(url).count('og:url'), 1)

    def test_og_title_and_og_description_repeat_the_title_and_the_description(self):
        for b, url in self.html_pages():
            with self.sub(b, url):
                self.assertEqual(b.meta(url, 'og:title'), [b.head(url).find('title').text(clean=False)])
                self.assertEqual(b.meta(url, 'og:description'), b.meta(url, 'description'))
                self.assertEqual(b.doc(url).find('html')['lang'], 'en')

    def test_og_type_is_article_on_report_pages_and_website_everywhere_else(self):
        articles = {'trips/%s/' % s for s in REPORTS}
        self.assertEqual(len(articles), 10)
        for b, url in self.html_pages():
            with self.sub(b, url):
                self.assertEqual(b.meta(url, 'og:type'), ['article' if url in articles else 'website'])

    def test_every_page_has_one_twitter_card_and_at_most_one_og_image(self):
        for b, url in self.html_pages():
            with self.sub(b, url):
                card = b.meta(url, 'twitter:card')
                image = b.meta(url, 'og:image')
                self.assertEqual(len(card), 1)
                self.assertLessEqual(len(image), 1)
                self.assertEqual(card[0], 'summary_large_image' if image else 'summary')

    def test_no_two_indexable_pages_share_a_title(self):
        pages = [u for u in self.feat.html_urls() if self.feat.by_url[u].index and u != '404.html']
        titles = [self.feat.head(u).find('title').text() for u in pages]
        self.assertEqual(len(set(titles)), len(titles))

    # ------------------------------------------------------------ robots, helpers, the 404 page

    def test_only_the_map_helpers_and_the_404_page_are_noindex(self):
        for b, url in self.html_pages():
            with self.sub(b, url):
                want = ['noindex'] if (url in HELPERS or url == '404.html') else []
                self.assertEqual(b.meta(url, 'robots'), want)
                self.assertEqual(b.html(url).count('noindex'), len(want))

    def test_a_map_helper_page_is_a_noindex_page_with_its_own_canonical(self):
        self.assertEqual(len(HELPERS), 11)
        for url in HELPERS:
            for built in (self.feat, self.bare):
                with self.subTest(page=url, featured=built is self.feat):
                    self.assertIs(built.by_url[url].index, False)
                    self.assertEqual(built.canonicals(url), [U + url])
                    self.assertEqual(built.meta(url, 'og:url'), [U + url])
                    self.assertEqual(built.meta(url, 'robots'), ['noindex'])
                    self.assertEqual(built.meta(url, 'og:type'), ['website'])
                    self.assertEqual(share_run(built.metas(url)), NO_SHARE)
                    self.assertEqual(ld_raw(built.html(url)), [])
                    self.assertNotIn('article:', built.html(url))

    def test_every_other_page_is_indexable_and_the_json_indexes_are_not(self):
        for b, url in self.html_pages():
            if url not in HELPERS and url != '404.html':        # sitemap() leaves the 404 page out by its name
                with self.sub(b, url):
                    self.assertIs(b.by_url[url].index, True)
        for url in JSON_PAGES:
            self.assertIs(self.feat.by_url[url].index, False)

    def test_the_404_page_names_no_url_and_is_noindex(self):
        for built in (self.feat, self.bare):
            with self.subTest(featured=built is self.feat):
                html_ = built.html('404.html')
                self.assertEqual(built.canonicals('404.html'), [])
                self.assertNotIn('canonical', html_)
                self.assertEqual(built.meta('404.html', 'og:url'), [])
                self.assertNotIn('og:url', html_)
                self.assertEqual(built.meta('404.html', 'robots'), ['noindex'])
                self.assertEqual(html_.count('name="robots"'), 1)
                self.assertEqual(share_run(built.metas('404.html')), NO_SHARE)
                self.assertNotIn('og:image', html_)
                self.assertEqual(built.meta('404.html', 'og:type'), ['website'])
                self.assertEqual(ld_raw(html_), [])
                self.assertEqual(len(built.head('404.html').find_all('title')), 1)
                self.assertEqual(built.meta('404.html', 'description'), ['This page is not on the map.'])


class ShareImageTests(FixtureCase):

    def test_the_table_covers_every_page(self):
        self.assertEqual(sorted(SHARES), sorted(self.feat.html_urls()))

    def test_every_page_shares_the_cover_the_table_names_and_nothing_else(self):
        for url, slug in sorted(SHARES.items()):
            with self.subTest(page=url or '(home)'):
                self.assertShares(self.feat, url, slug)

    def test_a_story_shares_its_cover_with_the_recorded_size_and_alt(self):
        self.assertEqual(share_run(self.feat.metas('trips/synm-story/')),
                         [('og:image', U + 'trips/synm-story/photos/03.webp'), ('og:image:type', 'image/webp'),
                          ('og:image:width', '1400'), ('og:image:height', '1000'), ('og:image:alt', COVER_ALT),
                          ('twitter:card', 'summary_large_image'), ('twitter:image:alt', COVER_ALT)])

    def test_the_share_tags_sit_between_og_url_and_theme_color(self):
        keys = [k for k, _v in self.feat.metas('trips/synm-compact/')]
        self.assertEqual(keys, ['viewport', 'description', 'og:type', 'og:title', 'og:description', 'og:site_name', 'og:locale',
                                'og:url', 'og:image', 'og:image:type', 'og:image:width', 'og:image:height', 'og:image:alt',
                                'twitter:card', 'twitter:image:alt'] + ARTICLE + ['theme-color'])

    def test_the_alt_survives_as_an_attribute_value(self):
        html_ = self.feat.html('trips/synm-story/')
        head_html = html_.split('</head>', 1)[0]
        self.assertNotIn('<angled>', head_html)
        self.assertEqual(self.feat.meta('trips/synm-story/', 'og:image:alt'), [COVER_ALT])
        self.assertEqual(self.feat.meta('trips/synm-story/', 'twitter:image:alt'), [COVER_ALT])

    def test_a_report_without_photos_has_no_og_image_and_the_summary_card(self):
        for slug in ('synm-newest', 'synm-words', 'synm-ski', 'synm-idea'):
            for built in (self.feat, self.bare):
                with self.subTest(slug=slug, featured=built is self.feat):
                    url = 'trips/%s/' % slug
                    self.assertEqual(share_run(built.metas(url)), [('twitter:card', 'summary')])
                    head_html = built.html(url).split('</head>', 1)[0]
                    self.assertNotIn('og:image', head_html)
                    self.assertNotIn('twitter:image', head_html)

    def test_a_cover_without_a_recorded_size_or_alt_shares_the_image_alone(self):
        self.assertEqual(share_run(self.feat.metas('trips/synm-nosize/')),
                         [('og:image', U + 'trips/synm-nosize/photos/01.webp'), ('og:image:type', 'image/webp'),
                          ('twitter:card', 'summary_large_image')])

    def test_every_og_image_is_absolute_and_names_a_photo_file_of_its_trip(self):
        seen = 0
        for built in (self.feat, self.bare):
            for url in built.html_urls():
                for image in built.meta(url, 'og:image'):
                    seen += 1
                    with self.subTest(page=url, image=image):
                        self.assertTrue(image.startswith(U + 'trips/' + PREFIX))
                        self.assertTrue(os.path.isfile(os.path.join(built.trips_dir, image[len(U + 'trips/'):])))
        self.assertGreater(seen, 20)

    def test_a_section_page_shares_the_cover_of_the_first_trip_in_its_list_that_has_one(self):
        # hiking: the featured block's trip (the newest) has no photo, the next one's cover is not its first photo
        self.assertShares(self.feat, 'hiking/', 'synm-story')
        # mountain biking: the trip flagged featured leads the list although a newer report has photos
        self.assertShares(self.feat, 'mountain-biking/', 'synm-flag')
        # ski: the newest has no photo; the tour's photos are on a day
        self.assertShares(self.feat, 'ski/', 'synm-tour')
        # climbing: a report, but no photo anywhere
        self.assertShares(self.feat, 'climbing/', None)
        self.assertShares(self.feat, 'other/', 'synm-nosize')

    def test_section_pages_do_not_depend_on_the_home_features(self):
        for url in SECTIONS:
            with self.subTest(page=url):
                self.assertEqual(share_run(self.bare.metas(url)), share_run(self.feat.metas(url)))
                self.assertShares(self.bare, url, SHARES[url])

    def test_trip_pages_do_not_depend_on_the_home_features(self):
        for slug in REPORTS + GOALS:
            with self.subTest(slug=slug):
                url = 'trips/%s/' % slug
                self.assertShares(self.bare, url, SHARES[url])
                self.assertEqual(self.bare.metas(url), self.feat.metas(url))

    def test_a_goal_page_shares_its_cover(self):
        self.assertShares(self.feat, 'trips/synm-goal/', 'synm-goal')
        self.assertEqual(self.feat.meta('trips/synm-goal/', 'og:type'), ['website'])
        self.assertNotIn('article:', self.feat.html('trips/synm-goal/'))


class FallbackShareTests(FixtureCase):

    def test_home_shares_the_lead_features_cover(self):
        self.assertShares(self.feat, '', 'synm-story')

    def test_home_without_features_shares_no_image(self):
        self.assertEqual(share_run(self.bare.metas('')), NO_SHARE)
        self.assertNotIn('og:image', self.bare.html(''))

    def test_the_four_site_pages_carry_the_lead_cover_once_a_feature_is_registered(self):
        self.assertEqual(sorted(SITE_PAGES), ['about/', 'map/', 'tick-list/', 'trips/'])
        for url in SITE_PAGES:
            with self.subTest(page=url):
                self.assertEqual(share_run(self.feat.metas(url)),
                                 [('og:image', U + 'trips/synm-story/photos/03.webp'), ('og:image:type', 'image/webp'),
                                  ('og:image:width', '1400'), ('og:image:height', '1000'), ('og:image:alt', COVER_ALT),
                                  ('twitter:card', 'summary_large_image'), ('twitter:image:alt', COVER_ALT)])

    def test_the_four_site_pages_carry_nothing_without_a_feature(self):
        for url in SITE_PAGES:
            with self.subTest(page=url):
                self.assertEqual(share_run(self.bare.metas(url)), NO_SHARE)
                self.assertNotIn('og:image', self.bare.html(url))
                self.assertNotIn('twitter:image', self.bare.html(url))

    def test_the_fallback_is_the_only_difference_in_those_heads(self):
        for url in SITE_PAGES:
            with self.subTest(page=url):
                with_ = [kv for kv in self.feat.metas(url) if not kv[0].startswith(('og:image', 'twitter:'))]
                without = [kv for kv in self.bare.metas(url) if not kv[0].startswith(('og:image', 'twitter:'))]
                self.assertEqual(with_, without)
                self.assertEqual(self.feat.canonicals(url), self.bare.canonicals(url))

    def test_the_fallback_never_reaches_a_trip_page_a_helper_page_or_the_404_page(self):
        lead = U + COVER['synm-story'][0]
        own = {'', 'hiking/', 'trips/synm-story/'} | set(SITE_PAGES)       # the pages that share that photo by right
        for url in self.feat.html_urls():
            with self.subTest(page=url):
                if url in own:
                    self.assertEqual(self.feat.meta(url, 'og:image'), [lead])
                else:
                    self.assertNotIn(lead, self.feat.meta(url, 'og:image'))
        for url in HELPERS + ['404.html', 'trips/synm-newest/', 'trips/synm-words/', 'trips/synm-ski/', 'trips/synm-idea/', 'climbing/']:
            with self.subTest(page=url, no_image=True):
                self.assertEqual(self.feat.meta(url, 'og:image'), [])

    def test_a_lead_without_a_photo_gives_no_fallback(self):
        built = self.fx.site.build(['synm-words', 'synm-story'], only=('home', 'about', 'archive', 'trips', 'ticklist'))
        for url in [''] + SITE_PAGES:
            with self.subTest(page=url):
                self.assertEqual(share_run(built.metas(url)), NO_SHARE)

    def test_the_fallback_follows_the_order_of_the_features(self):
        built = self.fx.site.build(['synm-tour', 'synm-story'], only=('home', 'about', 'archive', 'trips', 'ticklist'))
        for url in [''] + SITE_PAGES:
            with self.subTest(page=url):
                self.assertEqual(share_run(built.metas(url)), expected_share(*COVER['synm-tour']))


# ================================================================ 4. structured data and publication dates

class StructuredDataTests(FixtureCase):

    def test_exactly_one_block_on_a_written_report_and_none_anywhere_else(self):
        with_block = {'trips/%s/' % s for s in WRITTEN}
        for built in (self.feat, self.bare):
            for url in built.html_urls():
                with self.subTest(page=url or '(home)', featured=built is self.feat):
                    html_ = built.html(url)
                    want = 1 if url in with_block else 0
                    self.assertEqual(len(ld_raw(html_)), want)
                    # beside it, a crumbed page's BreadcrumbList (Phase 14): every block in the head
                    every = want + (1 if crumbed(url) else 0)
                    self.assertEqual(len(ld_raw(html_, crumbs=True)), every)
                    self.assertEqual(html_.lower().count('application/ld+json'), every)
                    scripts = [s for s in built.doc(url).find_all('script') if (s['type'] or '').lower() == 'application/ld+json']
                    self.assertEqual(len(scripts), every)
                    for sc in scripts:
                        self.assertIs(sc.parent, built.head(url))

    def test_the_pages_without_a_block_are_the_ones_the_contract_lists(self):
        none = (['trips/synm-short/', 'trips/synm-newest/', 'trips/synm-compact/', 'trips/synm-flag/', 'trips/synm-ski/',
                 'trips/synm-goal/', 'trips/synm-idea/', '', '404.html'] + HELPERS + SECTIONS + SITE_PAGES)
        for url in none:
            with self.subTest(page=url or '(home)'):
                self.assertNotIn('BlogPosting', self.feat.html(url))
                self.assertEqual(ld_raw(self.feat.html(url)), [])
                if not crumbed(url):                  # a crumbed page's one block is its BreadcrumbList (Phase 14)
                    self.assertNotIn('ld+json', self.feat.html(url))
                    self.assertNotIn('schema.org', self.feat.html(url))

    def test_the_block_of_a_story_is_exactly_this(self):
        url = 'trips/synm-story/'
        self.assertEqual(self.feat.ld(url), [{
            '@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': 'Synthetic Story', 'url': U + url,
            'mainEntityOfPage': {'@type': 'WebPage', '@id': U + url},
            'description': self.feat.meta(url, 'description')[0], 'inLanguage': 'en',
            'author': {'@type': 'Person', 'name': 'Eric Sichak', 'url': U + 'about/'},
            'image': {'@type': 'ImageObject', 'url': U + 'trips/synm-story/photos/03.webp', 'width': 1400, 'height': 1000}}])

    def test_the_block_equals_core_blog_posting_for_the_page(self):
        for slug in WRITTEN:
            with self.subTest(slug=slug):
                url = 'trips/%s/' % slug
                t = self.feat.by[slug]
                want = core.blog_posting(t, U + url, self.feat.meta(url, 'description')[0], core.share_photo(t))
                self.assertEqual(self.feat.ld(url), [want])
                self.assertEqual(list(self.feat.ld(url)[0]), list(want))        # and in its order (sort_keys=False)

    def test_the_block_holds_exactly_the_keys_the_contract_lists(self):
        with_image = {'synm-story', 'synm-tour', 'synm-journal'}
        for slug in WRITTEN:
            with self.subTest(slug=slug):
                url = 'trips/%s/' % slug
                d = self.feat.ld(url)[0]
                self.assertEqual(set(d), LD_KEYS | ({'image'} if slug in with_image else set()))
                self.assertEqual(d['@context'], 'https://schema.org')
                self.assertEqual(d['@type'], 'BlogPosting')
                self.assertEqual(d['headline'], self.feat.by[slug]['title'])
                self.assertEqual(d['url'], U + url)
                self.assertEqual(d['url'], self.feat.canonicals(url)[0])
                self.assertEqual(d['mainEntityOfPage'], {'@type': 'WebPage', '@id': U + url})
                self.assertEqual(d['description'], self.feat.meta(url, 'description')[0])
                self.assertEqual(d['inLanguage'], 'en')
                self.assertEqual(d['author'], {'@type': 'Person', 'name': core.AUTHOR_NAME, 'url': U + 'about/'})
                for banned in ('aggregateRating', 'review', 'publisher', 'dateCreated', 'datePublished', 'dateModified'):
                    self.assertNotIn(banned, d)

    def test_the_author_is_the_one_author_never_the_party(self):
        self.assertEqual(self.feat.by['synm-story']['party'], PARTY)
        self.assertEqual(core.AUTHOR_NAME, core.SITE_NAME)
        self.assertEqual(core.AUTHOR_URL, U + 'about/')
        self.assertNotIn(PARTY, ld_raw(self.feat.html('trips/synm-story/'))[0])

    def test_the_image_is_the_pages_own_share_photo_with_its_recorded_size(self):
        for slug in ('synm-story', 'synm-tour', 'synm-journal'):
            with self.subTest(slug=slug):
                url = 'trips/%s/' % slug
                path, w, h, _alt = COVER[slug]
                self.assertEqual(self.feat.ld(url)[0]['image'], {'@type': 'ImageObject', 'url': U + path, 'width': w, 'height': h})
                self.assertEqual(self.feat.ld(url)[0]['image']['url'], self.feat.meta(url, 'og:image')[0])

    def test_no_image_without_a_recorded_size_and_never_the_site_fallback(self):
        # synm-nosize shares its photo (og:image) but nothing records its size; synm-words has no photo at all, while
        # the site has a fallback share image (the lead feature's cover)
        self.assertEqual(len(self.feat.meta('trips/synm-nosize/', 'og:image')), 1)
        self.assertNotIn('image', self.feat.ld('trips/synm-nosize/')[0])
        self.assertEqual(self.feat.meta('about/', 'og:image'), [U + COVER['synm-story'][0]])       # the fallback exists
        self.assertNotIn('image', self.feat.ld('trips/synm-words/')[0])
        self.assertNotIn('synm-story', ld_raw(self.feat.html('trips/synm-words/'))[0])

    def test_blog_posting_takes_an_image_only_as_a_dict_with_both_sizes(self):
        t = self.feat.by['synm-story']
        base = dict(path='trips/synm-story/photos/03.webp', alt='a')
        for image in (None, 'trips/synm-story/photos/03.webp', dict(base), dict(base, w=1400), dict(base, h=1000),
                      dict(base, w=0, h=1000), dict(base, w='1400', h='1000'), dict(base, w=True, h=True), dict(base, w=None, h=None)):
            with self.subTest(image=image):
                self.assertNotIn('image', core.blog_posting(t, U + t['url'], 'Synthetic description.', image))
        d = core.blog_posting(t, U + t['url'], 'Synthetic description.', dict(base, w=1400, h=1000))
        self.assertEqual(d['image'], {'@type': 'ImageObject', 'url': U + base['path'], 'width': 1400, 'height': 1000})
        self.assertEqual(d['description'], 'Synthetic description.')

    def test_the_journal_has_one_block_for_the_page_not_one_per_written_day(self):
        self.assertEqual(sum(1 for d in self.feat.by['synm-journal']['days'] if d['body_md']), 2)
        self.assertEqual(len(self.feat.ld('trips/synm-journal/')), 1)
        self.assertEqual(self.feat.ld('trips/synm-journal/')[0]['headline'], 'Synthetic Journal')

    def test_the_block_is_json_with_non_ascii_text_as_it_is(self):
        raw = ld_raw(self.feat.html('trips/synm-tour/'))[0]
        self.assertIn('–', self.feat.ld('trips/synm-tour/')[0]['description'])      # 'Mar 10–11, 2026' in the summary
        self.assertIn('–', raw)                                                    # ensure_ascii=False
        self.assertNotIn('\\u2013', raw)

    def test_written_report_is_about_the_plain_text_of_the_reports_own_write_ups(self):
        by = self.feat.by
        self.assertTrue(core.written_report(by['synm-story']))
        self.assertTrue(core.written_report(by['synm-tour']))              # two days that reach the minimum together
        self.assertTrue(core.written_report(by['synm-journal']))
        self.assertFalse(core.written_report(by['synm-short']))
        self.assertFalse(core.written_report(by['synm-newest']))
        self.assertFalse(core.written_report(by['synm-goal']))             # long notes, but a plan is not a report
        self.assertFalse(core.written_report(None))


class WrittenReportBoundaryTests(TempCase):

    def test_the_minimum_is_inclusive(self):
        n = core.STRUCTURED_MIN_CHARS
        s = self.site()
        s.add('synm-under', date='2026-06-01', track=True, body='y' * (n - 1))
        s.add('synm-exact', date='2026-06-02', track=True, body='y' * n)
        built = s.build(only=('report',))
        self.assertEqual(len(ld_raw(built.html('trips/synm-under/'))), 0)
        self.assertEqual(len(ld_raw(built.html('trips/synm-exact/'))), 1)

    def test_markup_and_link_addresses_do_not_count(self):
        n = core.STRUCTURED_MIN_CHARS
        body = '[%s](https://example.test/%s) **%s**' % ('a' * 30, 'b' * n, 'c' * 30)
        self.assertGreater(len(body), n)
        self.assertLess(len(markdown.plain(body)), n)
        s = self.site()
        s.add('synm-markup', date='2026-06-01', track=True, body=body)
        built = s.build(only=('report',))
        self.assertFalse(core.written_report(built.by['synm-markup']))
        self.assertEqual(ld_raw(built.html('trips/synm-markup/')), [])

    def test_a_multi_day_trip_counts_its_days_together(self):
        short = 'Synthetic short day note.'
        self.assertLess(2 * len(short) + 1, core.STRUCTURED_MIN_CHARS)
        s = self.site()
        s.add('synm-long-days', kind='multi-day', days=[{'date': '2026-03-10', 'body': DAY_ONE}, {'date': '2026-03-11', 'body': DAY_TWO}])
        s.add('synm-short-days', kind='multi-day', days=[{'date': '2026-02-10', 'body': short}, {'date': '2026-02-11', 'body': short}])
        s.add('synm-silent-days', kind='multi-day', days=[{'date': '2026-01-10'}, {'date': '2026-01-11'}])
        built = s.build(only=('multiday',))
        self.assertEqual(len(ld_raw(built.html('trips/synm-long-days/'))), 1)
        self.assertEqual(ld_raw(built.html('trips/synm-short-days/')), [])
        self.assertEqual(ld_raw(built.html('trips/synm-silent-days/')), [])

    def test_a_journal_with_only_a_short_note_has_no_block(self):
        s = self.site()
        s.add('synm-quiet', kind='series', date='2024-04-22', days=[{'id': '001', 'date': '2024-04-22', 'body': SHORT},
                                                                    {'id': '002', 'date': '2024-04-23'}])
        built = s.build(only=('series',))
        self.assertEqual(ld_raw(built.html('trips/synm-quiet/')), [])
        self.assertNotIn('ld+json', built.html('trips/synm-quiet/map/'))


class HostileTitleTests(TempCase):
    """A title is written verbatim into the block, so it must not be able to end it."""

    TITLE = 'Synthetic "Quoted" & Co </script><script>alert(1)</script> <!-- end'

    def setUp(self):
        TempCase.setUp(self)
        s = self.site()
        self.titles = {'trips/synm-hostile/': self.TITLE, 'trips/synm-hostile-tour/': self.TITLE + ' two',
                       'trips/synm-hostile-journal/': self.TITLE + ' three'}
        self.urls = sorted(self.titles)
        s.add('synm-hostile', title=self.titles['trips/synm-hostile/'], date='2026-06-01', region=REGION, track=True, body=LONG,
              photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo')])
        s.add('synm-hostile-tour', title=self.titles['trips/synm-hostile-tour/'], kind='multi-day', activity='ski', region=REGION,
              days=[{'date': '2026-03-10', 'body': LONG}, {'date': '2026-03-11'}])
        s.add('synm-hostile-journal', title=self.titles['trips/synm-hostile-journal/'], kind='series', region=REGION,
              days=[{'id': '001', 'date': '2024-04-22', 'body': LONG}])
        self.built = s.build(only=('report', 'multiday', 'series'))

    def test_the_headline_is_the_title_verbatim(self):
        for url in self.urls:
            with self.subTest(page=url):
                blocks = self.built.ld(url)
                self.assertEqual(len(blocks), 1)
                self.assertEqual(blocks[0]['headline'], self.titles[url])
                self.assertEqual(blocks[0]['description'], self.built.meta(url, 'description')[0])

    def test_a_description_that_quotes_the_title_is_verbatim_too(self):
        # the multi-day description opens with the factual summary, which names the trip
        url = 'trips/synm-hostile-tour/'
        self.assertIn(self.titles[url], self.built.ld(url)[0]['description'])
        self.assertIn(self.titles[url], self.built.meta(url, 'description')[0])

    def test_the_block_contains_no_raw_less_than_sign(self):
        for url in self.urls:
            with self.subTest(page=url):
                raw = ld_raw(self.built.html(url))[0]
                self.assertNotIn('<', raw)
                self.assertIn('\\u003c/script>', raw)
                json.loads(raw)

    def test_the_page_still_has_exactly_one_closing_tag_for_the_block(self):
        for url in self.urls:
            with self.subTest(page=url):
                html_ = self.built.html(url)
                self.assertEqual(html_.count('<script'), html_.count('</script>'))
                self.assertNotIn('<script>alert(1)', html_)
                self.assertNotIn('alert(1)</script>', html_)
                doc = self.built.doc(url)
                ld = [json.loads(s.text(clean=False)) for s in doc.find_all('script') if s['type'] == 'application/ld+json']
                self.assertEqual([d['@type'] for d in ld], ['BlogPosting', 'BreadcrumbList'])   # the crumbs: Phase 14
                self.assertEqual(ld[0]['headline'], self.titles[url])
                # the first </script> after the block's opening tag is the block's own: the head goes on behind it
                after = html_[html_.index('</script>', _LD_OPEN.search(html_).end()):]
                self.assertTrue(after.startswith('</script><meta name="theme-color"'))
                self.assertEqual(len(doc.find_all('script')), html_.count('<script'))
                self.assertEqual(doc.find('h1').text(), helpers.plain_text(self.titles[url]))

    def test_the_title_tag_and_og_title_are_escaped(self):
        for url in self.urls:
            with self.subTest(page=url):
                # the title as written, then its activity and region (Phase 14, seo-01)
                act = core.ACT[self.built.by[url.split('/')[1]]['activity']][0]
                want = '%s · %s, %s · %s' % (self.titles[url], act, REGION, core.SITE_NAME)
                self.assertEqual(self.built.head(url).find('title').text(clean=False), want)
                self.assertEqual(self.built.meta(url, 'og:title'), [want])
                self.assertEqual(len(self.built.head(url).find_all('title')), 1)

    def test_two_reports_with_one_title_get_dated_titles_and_the_verbatim_headline(self):
        # the <title> of a repeated title carries the date; the headline is the title as written, like the H1
        s = self.site('twins')
        for slug, day in (('synm-twin-a', '2026-06-01'), ('synm-twin-b', '2026-06-08')):
            s.add(slug, title='Synthetic Twin', date=day, region=REGION, track=True, body=LONG)
        built = s.build(only=('report',))
        titles = [built.head('trips/%s/' % x).find('title').text() for x in ('synm-twin-a', 'synm-twin-b')]
        self.assertEqual(titles, ['Synthetic Twin · Hiking, %s, Jun 1, 2026 · Eric Sichak' % REGION,
                                  'Synthetic Twin · Hiking, %s, Jun 8, 2026 · Eric Sichak' % REGION])
        for slug in ('synm-twin-a', 'synm-twin-b'):
            url = 'trips/%s/' % slug
            self.assertEqual(built.ld(url)[0]['headline'], 'Synthetic Twin')
            self.assertEqual(built.doc(url).find('h1').text(), 'Synthetic Twin')
            self.assertEqual(built.ld(url)[0]['description'], built.meta(url, 'description')[0])
            self.assertEqual(len(built.head(url).find_all('title')), 1)


PUB, UPD = '2026-10-03T23:30:00-07:00', '2026-10-05T04:15Z'


class PublicationSurfaceTests(TempCase):
    """Where published_at / updated_at show: the visible line, the two article:* tags and the block's two dates; and that
    none of them exists when index.md does not state them."""

    def one(self, lines=(), kind=None, body=LONG, today=TODAY, name='a', **meta):
        """A site with one report (and a second, plain one, so the pager and the related block have something), built."""
        s = self.site(name, today)
        days = None
        if kind == 'multi-day':
            days = [{'date': '2026-06-01', 'body': body}, {'date': '2026-06-02'}]
        elif kind == 'series':
            days = [{'id': '001', 'date': '2026-06-01', 'body': body}, {'id': '002', 'date': '2026-06-02'}]
        m = dict(title='Synthetic Dated Report', activity='hike', region=REGION, kind=kind, days=days,
                 photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo')])
        if not days:
            m.update(date='2026-06-01', track=True, body=body)
        m.update(meta)
        s.add('synm-dated', lines, **m)
        s.add('synm-other', title='Synthetic Other Report', activity='hike', region=REGION, date='2026-05-01', track=True)
        # rendered, so each report has its map helper page (a series needs none)
        if kind != 'series':
            s.render('synm-dated', Site.OVERVIEW_MAPS if kind == 'multi-day' else Site.REPORT_MAPS)
        s.render('synm-other')
        return s.build(only=('report', 'multiday', 'series'))

    def pub_line(self, built, url='trips/synm-dated/'):
        return built.doc(url).find_all('p', cls='rep-pub')

    KINDS = (None, 'multi-day', 'series')

    # ------------------------------------------------------------ present

    def test_published_alone_shows_one_line_one_meta_tag_and_one_date_in_the_block(self):
        for kind in self.KINDS:
            with self.subTest(kind=kind):
                built = self.one(['published_at: 2026-10-03'], kind=kind, name='k-%s' % kind)
                url = 'trips/synm-dated/'
                html_ = built.html(url)
                self.assertEqual(html_.count('<p class="wrap rep-pub t-mono-s">Published <time datetime="2026-10-03">Oct 3, 2026</time></p>'), 1)
                self.assertEqual(html_.count('rep-pub'), 1)
                self.assertEqual(built.meta(url, 'article:published_time'), ['2026-10-03'])
                self.assertEqual(built.meta(url, 'article:modified_time'), [])
                self.assertNotIn('article:modified_time', html_)
                d = built.ld(url)[0]
                self.assertEqual(d['datePublished'], '2026-10-03')
                self.assertNotIn('dateModified', d)
                self.assertEqual(set(d), LD_KEYS | {'image', 'datePublished'})
                self.assertNotIn('Updated', built.doc(url).by_id('main').text())

    def test_both_fields_show_as_written_and_the_visible_date_comes_from_the_date_part(self):
        # 23:30 at -07:00 is already Oct 4 in UTC, and 04:15Z is still Oct 4 in California: the line shows what was typed
        for kind in self.KINDS:
            with self.subTest(kind=kind):
                built = self.one(['published_at: ' + PUB, 'updated_at: ' + UPD], kind=kind, name='k-%s' % kind)
                url = 'trips/synm-dated/'
                html_ = built.html(url)
                self.assertIn('<p class="wrap rep-pub t-mono-s">Published <time datetime="2026-10-03T23:30:00-07:00">Oct 3, 2026</time>'
                              ' · Updated <time datetime="2026-10-05T04:15Z">Oct 5, 2026</time></p>', html_)
                self.assertEqual(html_.count('rep-pub'), 1)
                line = self.pub_line(built)[0]
                self.assertEqual(line.text(), 'Published Oct 3, 2026 · Updated Oct 5, 2026')
                self.assertEqual([(t['datetime'], t.text()) for t in line.find_all('time')],
                                 [(PUB, 'Oct 3, 2026'), (UPD, 'Oct 5, 2026')])
                self.assertEqual(built.meta(url, 'article:published_time'), [PUB])
                self.assertEqual(built.meta(url, 'article:modified_time'), [UPD])
                d = built.ld(url)[0]
                self.assertEqual((d['datePublished'], d['dateModified']), (PUB, UPD))
                self.assertEqual(set(d), LD_KEYS | LD_OPTIONAL)
                self.assertEqual(list(d)[-2:], ['datePublished', 'dateModified'])
                self.assertEqual((built.by['synm-dated']['published_at'], built.by['synm-dated']['updated_at']), (PUB, UPD))
                # the report's map helper page is not the report: no dates, no block
                helper = built.html(url + 'map/')
                for needle in ('article:', 'rep-pub', 'ld+json', 'datePublished', PUB, UPD, 'Published'):
                    self.assertNotIn(needle, helper, needle)

    def test_the_article_tags_follow_the_share_tags_and_the_block_follows_them(self):
        built = self.one(['published_at: ' + PUB, 'updated_at: ' + UPD])
        url = 'trips/synm-dated/'
        keys = [k for k, _v in built.metas(url)]
        self.assertEqual(keys, ['viewport', 'description', 'og:type', 'og:title', 'og:description', 'og:site_name', 'og:locale',
                                'og:url', 'og:image', 'og:image:type', 'og:image:width', 'og:image:height', 'og:image:alt',
                                'twitter:card', 'twitter:image:alt'] + ARTICLE
                         + ['article:published_time', 'article:modified_time', 'theme-color'])
        html_ = built.html(url)
        self.assertIn('<meta property="article:published_time" content="%s"><meta property="article:modified_time" content="%s">'
                      '<script type="application/ld+json">' % (PUB, UPD), html_)
        self.assertEqual(built.meta(url, 'og:type'), ['article'])

    def test_the_line_sits_before_the_share_row_on_single_and_multi_day_pages(self):
        for kind in (None, 'multi-day'):
            with self.subTest(kind=kind):
                built = self.one(['published_at: 2026-10-03'], kind=kind, name='k-%s' % kind)
                html_ = built.html('trips/synm-dated/')
                main = html_[html_.index('<main'):html_.index('</main>')]
                self.assertIn('</time></p><div class="wrap rep-share">', main)
                self.assertEqual(main.count('<nav class="pager'), 1)
                self.assertLess(main.index('rep-pub'), main.index('<nav class="pager'))
                self.assertGreater(main.index('rep-pub'), main.index('id="map"'))

    def test_the_line_sits_before_the_pager_on_the_journal(self):
        built = self.one(['published_at: 2026-10-03'], kind='series')
        html_ = built.html('trips/synm-dated/')
        main = html_[html_.index('<main'):html_.index('</main>')]
        self.assertIn('</time></p><nav class="pager', main)
        self.assertGreater(main.index('rep-pub'), main.index('id="days"'))

    def test_a_track_only_report_shows_its_dates_without_becoming_an_article_in_structured_data(self):
        built = self.one(['published_at: 2026-10-03', 'updated_at: 2026-10-04'], body='')
        url = 'trips/synm-dated/'
        self.assertFalse(core.written_report(built.by['synm-dated']))
        self.assertEqual(ld_raw(built.html(url)), [])
        self.assertEqual(built.meta(url, 'article:published_time'), ['2026-10-03'])
        self.assertEqual(built.meta(url, 'article:modified_time'), ['2026-10-04'])
        self.assertEqual(self.pub_line(built)[0].text(), 'Published Oct 3, 2026 · Updated Oct 4, 2026')

    def test_published_line_is_empty_without_published_at(self):
        report = page_module('report')
        self.assertEqual(report.published_line({'published_at': None, 'updated_at': None}), '')
        self.assertEqual(report.published_line({}), '')
        self.assertEqual(report.published_line({'published_at': '2026-10-03', 'updated_at': None}),
                         '<p class="wrap rep-pub t-mono-s">Published <time datetime="2026-10-03">Oct 3, 2026</time></p>')
        self.assertEqual(report.published_line({'published_at': '2026-12-31T23:59:59+14:00', 'updated_at': '2027-01-01'}),
                         '<p class="wrap rep-pub t-mono-s">Published <time datetime="2026-12-31T23:59:59+14:00">Dec 31, 2026</time>'
                         ' · Updated <time datetime="2027-01-01">Jan 1, 2027</time></p>')

    def test_blog_posting_takes_its_dates_only_from_the_two_fields(self):
        t = dict(self.one().by['synm-dated'])
        base = core.blog_posting(t, U + t['url'], 'Synthetic description.', None)
        self.assertEqual(set(base), LD_KEYS)
        t['published_at'] = '2026-10-03'
        self.assertEqual(core.blog_posting(t, U + t['url'], 'Synthetic description.', None), dict(base, datePublished='2026-10-03'))
        t['updated_at'] = UPD
        self.assertEqual(core.blog_posting(t, U + t['url'], 'Synthetic description.', None),
                         dict(base, datePublished='2026-10-03', dateModified=UPD))

    # ------------------------------------------------------------ absent

    def test_absent_fields_write_nothing_about_publication(self):
        for kind in self.KINDS:
            with self.subTest(kind=kind):
                built = self.one(kind=kind, name='k-%s' % kind)
                url = 'trips/synm-dated/'
                html_ = built.html(url)
                for needle in ('rep-pub', 'article:published_time', 'article:modified_time', 'datePublished',
                               'dateModified', 'dateCreated', '>Published', 'Updated <time'):
                    self.assertNotIn(needle, html_, needle)
                self.assertEqual(self.pub_line(built), [])
                d = built.ld(url)[0]
                self.assertEqual(set(d), LD_KEYS | {'image'})

    def test_the_trip_date_is_never_presented_as_a_publication_date(self):
        for kind in self.KINDS:
            with self.subTest(kind=kind):
                built = self.one(kind=kind, name='k-%s' % kind)
                url = 'trips/synm-dated/'
                raw = ld_raw(built.html(url))[0]
                for iso in ('2026-06-01', '2026-06-02'):
                    self.assertNotIn(iso, raw)
                    self.assertNotIn(iso, [v for k, v in built.metas(url) if k not in ('description', 'og:description')])
                self.assertEqual([k for k, _v in built.metas(url) if k.startswith('article:') and k.endswith('_time')], [])
                text = built.doc(url).by_id('main').text()
                self.assertNotIn('Published', text)
                self.assertNotIn('Updated', text)

    def test_the_day_of_the_build_never_shows(self):
        a, b = date(2031, 3, 7), date(2031, 11, 23)        # one year, so the footer's © line is the same
        for kind in self.KINDS:
            with self.subTest(kind=kind):
                one = self.one(kind=kind, today=a, name='a-%s' % kind)
                two = self.one(kind=kind, today=b, name='b-%s' % kind)
                for url in ('trips/synm-dated/', 'trips/synm-dated/map/', 'trips/synm-other/'):
                    self.assertEqual(one.html(url), two.html(url), url)
                html_ = one.html('trips/synm-dated/')
                self.assertIn('© 2031', html_)               # the patched clock is the one the page read
                for needle in ('2031-03-07', '2031-11-23', 'Mar 7, 2031', 'Nov 23, 2031', '2031-03', '2031-11'):
                    self.assertNotIn(needle, html_)
                self.assertNotIn('2031', ld_raw(html_)[0])

    def test_the_fields_of_a_day_file_reach_no_page(self):
        s = self.site()
        s.add('synm-dated', kind='multi-day', region=REGION,
              days=[{'date': '2026-06-01', 'body': LONG, 'published_at': '2026-10-03', 'updated_at': '2026-10-04'}, {'date': '2026-06-02'}])
        built = s.build(only=('multiday',))
        html_ = built.html('trips/synm-dated/')
        for needle in ('rep-pub', 'article:published', 'article:modified', 'datePublished', 'dateModified', '2026-10-03', '2026-10-04'):
            self.assertNotIn(needle, html_, needle)

    # ------------------------------------------------------------ nothing else changes

    def test_the_fields_change_only_the_reports_own_page_the_feed_and_the_sitemap(self):
        # contract 4.4 as Phase 9 (seo-10) left it: the report's page, its feed item (pubDate, and the item order) and
        # its sitemap <lastmod>; never the site's order, the home page or any other page
        build = module('build')

        def whole(lines, name):
            s = self.site(name)
            s.add('synm-dated', lines, title='Synthetic Dated Report', activity='hike', region=REGION, date='2026-05-01', track=True,
                  body=LONG, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo')])
            s.add('synm-newer', title='Synthetic Newer Report', activity='hike', region=REGION, date='2026-06-01', track=True, body=LONG)
            s.add('synm-older', title='Synthetic Older Report', activity='hike', region=REGION, date='2026-04-01', track=True)
            built = s.build(['synm-newer', 'synm-dated'])
            return built, build.feed(built.site['published']), build.sitemap(built.pages, built.site['published'])
        (plain, feed_a, map_a), (dated, feed_b, map_b) = whole((), 'plain'), whole(['published_at: 2026-10-03', 'updated_at: 2026-10-05'], 'dated')
        self.assertEqual(dated.by['synm-dated']['published_at'], '2026-10-03')
        self.assertEqual([p.url for p in plain.pages], [p.url for p in dated.pages])
        changed = [p.url for p in plain.pages if p.html != dated.by_url[p.url].html]
        self.assertEqual(changed, ['trips/synm-dated/'])
        self.assertEqual([t['slug'] for t in dated.site['published']], ['synm-newer', 'synm-dated', 'synm-older'])
        links = lambda text: [i.findtext('link')[len(U):] for i in ET.fromstring(text.encode('utf-8')).iter('item')]
        self.assertEqual(links(feed_a), ['trips/synm-newer/', 'trips/synm-dated/', 'trips/synm-older/'])
        self.assertEqual(links(feed_b), ['trips/synm-dated/', 'trips/synm-newer/', 'trips/synm-older/'])
        self.assertIn('<pubDate>Sat, 03 Oct 2026 12:00:00 +0000</pubDate>', feed_b)
        for needle in ('2026-10-05', 'Oct 3, 2026', 'Published'):
            self.assertNotIn(needle, feed_b)
        self.assertNotIn('lastmod', map_a)
        self.assertEqual(map_b.replace('<lastmod>2026-10-05</lastmod>', ''), map_a)
        self.assertEqual(map_b.count('<lastmod>'), 1)


# ================================================================ 5. feed.xml and sitemap.xml

ATOM = '{http://www.w3.org/2005/Atom}'
SM = '{http://www.sitemaps.org/schemas/sitemap/0.9}'


class FeedTests(FixtureCase):

    def setUp(self):
        FixtureCase.setUp(self)
        self.build = module('build')
        self.published = self.feat.site['published']
        with sandbox(self.fx.site.root):
            self.text = self.build.feed(self.published)
        self.rss = ET.fromstring(self.text.encode('utf-8'))
        self.channel = self.rss.find('channel')
        self.items = self.channel.findall('item')

    def test_it_is_well_formed_rss_2(self):
        self.assertTrue(self.text.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"'))
        self.assertTrue(self.text.endswith('</channel></rss>\n'))
        self.assertEqual(self.rss.tag, 'rss')
        self.assertEqual(self.rss.get('version'), '2.0')
        self.assertEqual(len(self.rss.findall('channel')), 1)
        self.assertEqual(list(self.rss), [self.channel])

    def test_the_channel_names_the_site_and_itself(self):
        self.assertEqual(self.channel.findtext('title'), '%s — trip reports' % core.SITE_NAME)
        self.assertEqual(self.channel.findtext('link'), U)
        self.assertEqual(self.channel.findtext('description'), core.SITE_TAGLINE)
        self.assertEqual(self.channel.findtext('language'), 'en-us')
        self_link = self.channel.find(ATOM + 'link')
        self.assertEqual((self_link.get('href'), self_link.get('rel'), self_link.get('type')),
                         (U + 'feed.xml', 'self', 'application/rss+xml'))

    def test_the_channel_carries_no_date_of_its_own(self):
        self.assertEqual([c.tag for c in self.channel if c.tag != 'item'], ['title', 'link', ATOM + 'link', 'description', 'language'])
        for needle in ('lastBuildDate', '<pubDate></pubDate>', 'generator', 'ttl', 'updated'):
            self.assertNotIn(needle, self.text)

    def test_one_item_per_published_report_in_the_sites_order_and_no_planned_route(self):
        self.assertEqual([i.findtext('link') for i in self.items], [U + 'trips/%s/' % t['slug'] for t in self.published])
        self.assertEqual([t['slug'] for t in self.published],
                         ['synm-newest', 'synm-story', 'synm-compact', 'synm-short', 'synm-nosize', 'synm-ski', 'synm-words',
                          'synm-tour', 'synm-flag', 'synm-journal'])
        for slug in GOALS + ['synm-draft']:
            self.assertNotIn(slug, self.text)

    def test_planned_routes_are_left_out_even_when_they_are_passed_in(self):
        with sandbox(self.fx.site.root):
            text = self.build.feed(self.feat.site['trips'])
        self.assertEqual(text, self.text)
        self.assertEqual(len(self.feat.site['trips']), len(self.published) + len(GOALS))

    def test_link_and_guid_are_the_trips_absolute_url(self):
        for item, t in zip(self.items, self.published):
            with self.subTest(slug=t['slug']):
                self.assertEqual(item.findtext('link'), U + t['url'])
                self.assertEqual(item.findtext('guid'), U + t['url'])
                self.assertEqual(item.find('guid').attrib, {})             # a permalink: no isPermaLink="false"
                self.assertEqual(item.findtext('link'), self.feat.canonicals(t['url'])[0])
        self.assertNotIn('isPermaLink', self.text)

    def test_every_item_has_these_children_in_this_order(self):
        for item, t in zip(self.items, self.published):
            with self.subTest(slug=t['slug']):
                # and the whole write-up when the trip has one of its own (Phase 14, seo-09; tests/test_phase14.py)
                self.assertEqual([c.tag for c in item], ['title', 'link', 'guid', 'pubDate', 'category', 'description']
                                 + (['{http://purl.org/rss/1.0/modules/content/}encoded'] if t['body_md'] else []))
                self.assertEqual(item.findtext('title'), t['title'])
                self.assertEqual(item.findtext('category'), core.ACT[t['activity']][0])

    def test_pub_date_is_the_trip_date_at_noon_utc(self):
        by = {i.findtext('link'): i for i in self.items}
        self.assertEqual(by[U + 'trips/synm-story/'].findtext('pubDate'), 'Mon, 01 Jun 2026 12:00:00 +0000')
        self.assertEqual(by[U + 'trips/synm-tour/'].findtext('pubDate'), 'Tue, 10 Mar 2026 12:00:00 +0000')        # its first day
        self.assertEqual(by[U + 'trips/synm-journal/'].findtext('pubDate'), 'Mon, 22 Apr 2024 12:00:00 +0000')
        for item, t in zip(self.items, self.published):
            with self.subTest(slug=t['slug']):
                when = email.utils.parsedate_to_datetime(item.findtext('pubDate'))
                self.assertEqual(when, datetime(t['date'].year, t['date'].month, t['date'].day, 12, tzinfo=timezone.utc))
                self.assertEqual(when.utcoffset(), timedelta(0))
                self.assertEqual(item.findtext('pubDate'), email.utils.format_datetime(when))

    def test_the_description_is_the_factual_summary_then_the_start_of_the_write_up(self):
        by = {i.findtext('link'): i for i in self.items}
        with sandbox(self.fx.site.root):
            track = core.summary(self.feat.by['synm-newest'])
            story = core.summary(self.feat.by['synm-story'])
            tour = core.summary(self.feat.by['synm-tour'])
        self.assertEqual(by[U + 'trips/synm-newest/'].findtext('description'), track)
        self.assertEqual(by[U + 'trips/synm-story/'].findtext('description'),
                         story + ' Synthetic write-up for a metadata test, long enough to count as a written report. '
                                 'Second synthetic paragraph, with emphasis and a synthetic link.')
        # a trip with days and no trip-level write-up gets the summary alone
        self.assertEqual(by[U + 'trips/synm-tour/'].findtext('description'), tour)
        self.assertNotIn(PARTY, self.text)

    def test_the_feed_holds_no_value_of_the_build(self):
        texts = []
        for moment in (datetime(2031, 3, 7, 9, 41), datetime(2044, 11, 23, 22, 5)):
            with sandbox(self.fx.site.root, today=moment.date()), mock.patch.object(self.build, 'datetime', fake_datetime(moment)):
                texts.append(self.build.feed(self.published))
        self.assertEqual(texts[0], texts[1])
        self.assertEqual(texts[0], self.text)
        for needle in ('2031', '2044', TODAY.isoformat(), '09:41', '22:05'):
            self.assertNotIn(needle, self.text)
        years = set(re.findall(r'\b((?:19|20)\d\d)\b', self.text.replace('http://www.w3.org/2005/Atom', '')))
        self.assertEqual(years, {'2024', '2026'})                    # the fixture's trip years and nothing else


class FeedShapeTests(TempCase):

    def test_at_most_thirty_items_the_first_thirty_of_the_list(self):
        s = self.site()
        for i in range(33):
            s.add('synm-n%02d' % i, title='Synthetic Report %02d' % i, date=(date(2026, 1, 1) + timedelta(days=i)).isoformat(), track=True)
        s.add('synm-goal', kind='planned', track=True)
        s.add('synm-goal-two', kind='planned')
        site = s.load()
        self.assertEqual(len(site['published']), 33)
        with sandbox(s.root):
            text = module('build').feed(site['published'])
            mixed = module('build').feed(site['trips'])
        links = [i.findtext('link') for i in ET.fromstring(text.encode('utf-8')).iter('item')]
        self.assertEqual(len(links), 30)
        self.assertEqual(links, [U + 'trips/synm-n%02d/' % i for i in range(32, 2, -1)])       # newest first: 32 ... 3
        self.assertEqual(mixed, text)                                                        # goals do not use up a place

    def test_an_undated_report_has_no_pub_date(self):
        s = self.site()
        s.add('synm-dated', title='Synthetic Dated', date='2026-06-01', track=True)
        s.add('synm-undated', title='Synthetic Undated', track=True)
        site = s.load()
        with sandbox(s.root):
            text = module('build').feed(site['published'])
        items = {i.findtext('link'): i for i in ET.fromstring(text.encode('utf-8')).iter('item')}
        undated = items[U + 'trips/synm-undated/']
        self.assertIsNone(undated.find('pubDate'))
        self.assertEqual([c.tag for c in undated], ['title', 'link', 'guid', 'category', 'description'])
        self.assertEqual(items[U + 'trips/synm-dated/'].findtext('pubDate'), 'Mon, 01 Jun 2026 12:00:00 +0000')
        self.assertEqual(text.count('<pubDate>'), 1)

    def test_an_empty_site_gives_a_channel_without_items(self):
        with sandbox(self.tmp):
            text = module('build').feed([])
        rss = ET.fromstring(text.encode('utf-8'))
        self.assertEqual(rss.find('channel').findall('item'), [])
        self.assertEqual(rss.find('channel').findtext('link'), U)

    def test_the_exact_bytes_of_a_one_item_feed(self):
        s = self.site()
        s.add('synm-only', title='Synthetic & <Only>', activity='climb', date='2026-06-01', region=REGION, track=True)
        site = s.load()
        with sandbox(s.root):
            text = module('build').feed(site['published'])
        self.assertEqual(text, (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>'
            '<title>Eric Sichak — trip reports</title><link>https://esichak.github.io/personal-website/</link>'
            '<atom:link href="https://esichak.github.io/personal-website/feed.xml" rel="self" type="application/rss+xml"/>'
            '<description>%s</description><language>en-us</language>'
            '<item><title>Synthetic &amp; &lt;Only&gt;</title>'
            '<link>https://esichak.github.io/personal-website/trips/synm-only/</link>'
            '<guid>https://esichak.github.io/personal-website/trips/synm-only/</guid>'
            '<pubDate>Mon, 01 Jun 2026 12:00:00 +0000</pubDate><category>Climbing</category>'
            '<description>Climbing trip report: Synthetic &amp; &lt;Only&gt;, Synthetic Range, Mon, Jun 1, 2026. with map and GPX.</description>'
            '</item></channel></rss>\n') % core.SITE_TAGLINE)

    def test_published_at_is_the_pub_date_and_orders_the_items(self):
        # Phase 9 (seo-10): a report that states published_at reaches feed readers on the day it went online
        def feed_of(dated, older, name):
            s = self.site(name)
            s.add('synm-dated', dated, title='Synthetic Dated', date='2026-06-01', track=True, body=LONG)
            s.add('synm-older', older, title='Synthetic Older', date='2026-05-01', track=True)
            site = s.load()
            with sandbox(s.root):
                text = module('build').feed(site['published'])
            items = list(ET.fromstring(text.encode('utf-8')).iter('item'))
            return site, text, [(i.findtext('link')[len(U):], i.findtext('pubDate')) for i in items]
        plain_site, plain, plain_items = feed_of((), (), 'plain')
        self.assertEqual(plain_items, [('trips/synm-dated/', 'Mon, 01 Jun 2026 12:00:00 +0000'),
                                       ('trips/synm-older/', 'Fri, 01 May 2026 12:00:00 +0000')])
        self.assertIsNone(plain_site['by_slug']['synm-dated']['published_at'])
        dated_site, dated, dated_items = feed_of(['published_at: 2026-09-01T08:00:00-07:00', 'updated_at: 2026-09-15'], (),
                                                 'dated')
        self.assertEqual(dated_site['by_slug']['synm-dated']['published_at'], '2026-09-01T08:00:00-07:00')
        self.assertEqual(dated_items, [('trips/synm-dated/', 'Tue, 01 Sep 2026 15:00:00 +0000'),     # in UTC; updated_at plays no part
                                       ('trips/synm-older/', 'Fri, 01 May 2026 12:00:00 +0000')])
        self.assertEqual(dated.replace('Tue, 01 Sep 2026 15:00:00', 'Mon, 01 Jun 2026 12:00:00'), plain)
        # an older trip written up later comes first; a date alone is 12:00 UTC
        _site, _text, items = feed_of(['published_at: 2026-09-01T08:00:00-07:00'], ['published_at: 2026-09-10'], 'later')
        self.assertEqual(items, [('trips/synm-older/', 'Thu, 10 Sep 2026 12:00:00 +0000'),
                                 ('trips/synm-dated/', 'Tue, 01 Sep 2026 15:00:00 +0000')])
        # one dated report among undated ones takes its place by its publication moment
        _site, _text, items = feed_of((), ['published_at: 2026-05-20'], 'between')
        self.assertEqual([u for u, _d in items], ['trips/synm-dated/', 'trips/synm-older/'])
        _site, _text, items = feed_of((), ['published_at: 2026-06-02'], 'ahead')
        self.assertEqual([u for u, _d in items], ['trips/synm-older/', 'trips/synm-dated/'])


class SitemapTests(FixtureCase):

    def setUp(self):
        FixtureCase.setUp(self)
        self.build = module('build')

    def locs(self, text):
        root = ET.fromstring(text.encode('utf-8'))
        self.assertEqual(root.tag, SM + 'urlset')
        for url in root:
            self.assertEqual(url.tag, SM + 'url')
            self.assertEqual([c.tag for c in url], [SM + 'loc'])           # no lastmod, changefreq or priority
        return [u.findtext(SM + 'loc') for u in root]

    def test_the_exact_text_for_a_handful_of_pages(self):
        pages = [core.Page('', '<html>'), core.Page('about/', '<html>'), core.Page('trips/synm-a/', '<html>'),
                 core.Page('trips/synm-a/map/', '<html>', index=False), core.Page('trips/search.json', '{}', index=False),
                 core.Page('404.html', '<html>')]
        self.assertEqual(self.build.sitemap(pages),
                         '<?xml version="1.0" encoding="UTF-8"?>\n'
                         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                         '<url><loc>https://esichak.github.io/personal-website/</loc></url>'
                         '<url><loc>https://esichak.github.io/personal-website/about/</loc></url>'
                         '<url><loc>https://esichak.github.io/personal-website/trips/synm-a/</loc></url>'
                         '</urlset>\n')

    def test_no_pages_no_urls(self):
        self.assertEqual(self.locs(self.build.sitemap([])), [])

    def test_it_lists_exactly_the_indexable_pages_but_the_404_once_each(self):
        for built in (self.feat, self.bare):
            with self.subTest(featured=built is self.feat):
                text = self.build.sitemap(built.pages)
                locs = self.locs(text)
                want = [U + p.url for p in built.pages if p.index and p.url != '404.html']
                self.assertEqual(locs, want)                               # in page order
                self.assertEqual(len(set(locs)), len(locs))
                self.assertEqual(sorted(locs), sorted(U + u for u in [''] + SITE_PAGES + SECTIONS + ['trips/%s/' % s for s in REPORTS + GOALS]))

    def test_it_lists_no_helper_no_json_and_not_the_404_page(self):
        text = self.build.sitemap(self.feat.pages)
        locs = self.locs(text)
        for url in HELPERS + JSON_PAGES + ['404.html']:
            self.assertNotIn(U + url, locs)
        self.assertEqual([loc for loc in locs if re.search(r'trips/[^/]+/map/', loc)], [])     # map/ itself is the archive page
        for needle in ('synm-story/map/', '404', '.json', '.gpx', 'lastmod', 'changefreq', 'priority', 'feed.xml', 'synm-draft'):
            self.assertNotIn(needle, text)

    def test_every_listed_url_is_the_canonical_of_a_page_without_noindex(self):
        locs = self.locs(self.build.sitemap(self.feat.pages))
        by_canonical = {self.feat.canonicals(u)[0]: u for u in self.feat.html_urls() if u != '404.html'}
        for loc in locs:
            with self.subTest(loc=loc):
                self.assertIn(loc, by_canonical)
                self.assertEqual(self.feat.meta(by_canonical[loc], 'robots'), [])
        # and the other way round: every page without noindex is listed
        self.assertEqual(sorted(locs), sorted(c for c, u in by_canonical.items() if not self.feat.meta(u, 'robots')))

    def test_a_page_object_is_indexable_unless_it_says_otherwise(self):
        self.assertIs(core.Page('x/', '').index, True)
        self.assertIs(core.Page('x/', '', 'T', index=False).index, False)

    def test_lastmod_is_updated_at_else_published_at_as_written(self):
        # Phase 9 (seo-10): only a report that states a publication date carries one; nothing else is dated
        trips = [{'url': 'trips/synm-a/', 'published_at': '2026-09-01', 'updated_at': '2026-09-15T08:00:00-07:00'},
                 {'url': 'trips/synm-b/', 'published_at': '2026-06-05T12:00Z', 'updated_at': None},
                 {'url': 'trips/synm-c/', 'published_at': None, 'updated_at': None}]
        pages = [core.Page('', '<html>'), core.Page('trips/synm-a/', '<html>'), core.Page('trips/synm-b/', '<html>'),
                 core.Page('trips/synm-c/', '<html>'), core.Page('trips/synm-a/map/', '<html>', index=False)]
        self.assertEqual(self.build.sitemap(pages, trips),
                         '<?xml version="1.0" encoding="UTF-8"?>\n'
                         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                         '<url><loc>https://esichak.github.io/personal-website/</loc></url>'
                         '<url><loc>https://esichak.github.io/personal-website/trips/synm-a/</loc>'
                         '<lastmod>2026-09-15T08:00:00-07:00</lastmod></url>'
                         '<url><loc>https://esichak.github.io/personal-website/trips/synm-b/</loc>'
                         '<lastmod>2026-06-05T12:00Z</lastmod></url>'
                         '<url><loc>https://esichak.github.io/personal-website/trips/synm-c/</loc></url>'
                         '</urlset>\n')
        # the fixture site states no publication date, so its built sitemap has no lastmod
        self.assertEqual(self.build.sitemap(self.feat.pages, self.feat.site['published']), self.build.sitemap(self.feat.pages))

    def test_the_sitemap_holds_no_value_of_the_build(self):
        with mock.patch.object(self.build, 'datetime', fake_datetime(datetime(2044, 11, 23, 22, 5))):
            later = self.build.sitemap(self.feat.pages)
        self.assertEqual(later, self.build.sitemap(self.feat.pages))
        self.assertIsNone(re.search(r'(?:19|20)\d\d', later))                    # no year, so no date of any kind


if __name__ == '__main__':
    unittest.main()
