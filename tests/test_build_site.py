"""Phase 4: tools/build.py end to end on a small synthetic site, and its two pure helpers (strip_css_comments,
conflict_copy). Pinned to contract-phase4.md sections 2.1 as replaced by 10.2 (a single-day report without a track has
no GPX control, no map section, no full-screen map page and no place in a section's featured block; its descriptions
promise neither a map nor a file), 4.6 (robots.txt, the sitemap and the feed are written as before), 5.4 (the
published stylesheet carries no comments), 5.5 (iCloud conflict copies of rendered files stay out of the site), 10.1
(the combined GPX of a multi-day trip is written exactly when its page offers it; a run of adjacent comments is judged
as one) and 10.3 (the renders of a trip without a track are not published; a report without a track and without stats
has no Stats strip; conflict copies under assets/ are in neither bundle and are not copied; the combined GPX declares
the namespace prefixes its day files use; an Other segment links #featured only when there is a featured block; a
section's description promises a track and a map only when every report has a track) and 10.5 (the card-size .th
copy is offered to phones only: a card cover that has one is wrapped in <picture class="cover-pic"> with a
phone-only <source>, and no <img> and no preload of the site lists the copy). build.main(), its exit codes and the
output of check() are not tested here (tests/test_build_cli.py).

build.build() itself runs, unchanged, against a synthetic repository root in a temp dir:

  <root>/content/trips/synb-*/   the trips below, written with tests/helpers.py; the GPX files hold real <trk> blocks
  <root>/content/home.json       features synb-story, then synb-tour
  <root>/rendered/               a render folder for synb-story and a rendered/site/ folder, each with files a renderer
                                 writes and iCloud conflict copies of them ('map-wide 3.webp', 'meta 2.json'); and a
                                 whole render folder for synb-notrack and for synb-tour-none, left behind by tracks
                                 that are gone (STALE)
  <root>/assets/                 two small stylesheets and scripts and a favicon, and conflict copies of them
                                 ('alpha 2.css', 'trips 2.js', 'favicon 2.svg')
  <root>/_site/                  the output

redirected() points every module constant the build reads at that root: content.TRIPS_DIR and content.RENDERED,
core.ROOT (the site maps), build.ROOT (assets and rendered/site) and build.OUT. content/home.json cannot be redirected
by patching curation.HOME_JSON: curation.featured_for(site, path=HOME_JSON) and its two helpers bound the real path
(and the real content/trips/) as default arguments when the module was imported, and build() calls featured_for(site)
with no path. So the defaults of those functions are replaced too, value for value (redirect_defaults). core's
registered site is put back afterwards. Nothing under the real content/, rendered/ or _site/ is read or written; the
one test that reads the repository reads assets/css, to check the real stylesheets publish without a comment.

  synb-story        hike, a track, a write-up, one photo with .sm and .th copies   the home lead; a render folder
  synb-notrack      mtb, a write-up and a photo, NO track.gpx                      story layout; Mountain Biking's only report
  synb-plain        other, nothing but its index.md: no track either              compact layout; Other's only report
  synb-tour         ski, multi-day, both days with a track                         a combined GPX
  synb-tour-half    ski, multi-day, only day 1 with a track                        a combined GPX of one <trk>
  synb-tour-none    climb, multi-day, no day track                                 no combined GPX, no download
  synb-journal      hike, series, days 1 and 2 with a track
  synb-goal         hike, planned, a track
  synb-idea         hike, planned, nothing else
  synb-draft        a draft with a track and a photo: never in the output

A second, smaller site (write_no_track_site, built once as well) holds what the first lacks for contract 10.2: sections
whose newest or flagged report has no track beside older reports that have one, a section of nothing but reports
without a track, and two reports that share a title, so that a written report's JSON-LD description leads with the
factual summary. None of its trips is rendered.

Every sentence in a fixture is synthetic.
"""
import contextlib
import hashlib
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import mapkit  # noqa: E402
from sitegen import core  # noqa: E402
from sitegen import curation  # noqa: E402
from sitegen import sitecheck  # noqa: E402
from sitegen.pages import home as home_page  # noqa: E402
import build  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, photo, LANDSCAPE  # noqa: E402

PREFIX = 'synb-'
TODAY = date(2031, 5, 20)
REGION = 'Synthetic Range'
U = core.SITE_URL
LONG = ('Synthetic write-up for a build test, long enough to count as a written report.\n\n'
        'Second synthetic paragraph of the same write-up, with a few more synthetic words.')
REPORTS = ['synb-story', 'synb-notrack', 'synb-plain', 'synb-tour', 'synb-tour-half', 'synb-tour-none', 'synb-journal']
GOALS = ['synb-goal', 'synb-idea']
NEWEST_FIRST = ['synb-story', 'synb-notrack', 'synb-plain', 'synb-tour', 'synb-tour-half', 'synb-tour-none', 'synb-journal']
NO_TRACK = ['synb-notrack', 'synb-plain']
TITLES = {'synb-story': 'Synthetic Story', 'synb-notrack': 'Synthetic Without Track', 'synb-plain': 'Synthetic Plain',
          'synb-tour': 'Synthetic Tour & Traverse', 'synb-tour-half': 'Synthetic Half Tour', 'synb-tour-none': 'Synthetic Trackless Tour',
          'synb-journal': 'Synthetic Journal', 'synb-goal': 'Synthetic Goal', 'synb-idea': 'Synthetic Idea', 'synb-draft': 'Synthetic Draft'}
SECTIONS = ['ski/', 'climbing/', 'hiking/', 'mountain-biking/', 'other/']
SITE_PAGES = ['', 'trips/', 'tick-list/', 'map/', 'about/']
# full-screen map pages (contract 10.2 as amended by Phase 6, resilience-12): a report with a track gets one only with a
# rendered map, which here is synb-story alone; the two tours with day tracks are not rendered, so they have none. The
# tour without any day track keeps its page with the empty map, and the journal keeps its own (series.py). No goal has a
# rendered map here, so none has a helper page
UNRENDERED = ['synb-tour', 'synb-tour-half']
HELPERS = ['trips/%s/map/' % s for s in REPORTS if s not in NO_TRACK + UNRENDERED]
# every GPX file the site publishes: output path -> source path under content/trips/ (None: written by the build)
GPX_FILES = {
    'trips/synb-story/synb-story.gpx': 'synb-story/track.gpx',
    'trips/synb-goal/synb-goal.gpx': 'synb-goal/track.gpx',
    'trips/synb-tour/synb-tour.gpx': None,
    'trips/synb-tour/gpx/synb-tour-day-01.gpx': 'synb-tour/days/01.gpx',
    'trips/synb-tour/gpx/synb-tour-day-02.gpx': 'synb-tour/days/02.gpx',
    'trips/synb-tour-half/synb-tour-half.gpx': None,
    'trips/synb-tour-half/gpx/synb-tour-half-day-01.gpx': 'synb-tour-half/days/01.gpx',
    'trips/synb-journal/gpx/synb-journal-day-001.gpx': 'synb-journal/days/001.gpx',
    'trips/synb-journal/gpx/synb-journal-day-002.gpx': 'synb-journal/days/002.gpx',
}
CONFLICT_NAME = re.compile(r' \d+(\.[A-Za-z0-9]+)*$')      # a name iCloud gives a conflict copy: 'meta 3.json', 'x 2'

BASE_CSS = ('/* synthetic base stylesheet: no comment of it may be published */\n'
            ':root { --synb-ink: #111; }   /* a trailing comment */\n'
            '\n'
            '/*\n'
            ' * a block comment\n'
            ' * over three lines\n'
            ' */\n'
            '.synb-base { color: var(--synb-ink); }\n')
ALPHA_CSS = '/* alpha page */\n.synb-alpha { margin: 0 auto; }\n\n\n.synb-alpha-two { padding: 0; }\n'
BETA_CSS = '.synb-beta { display: none; } /* why it is hidden */\n'
PRINT_CSS = '/* the print sheet */\n@media print { .synb-print { display: none; } }\n'   # appended after the page sheets (Phase 13B)
BASE_JS = '/* synthetic base script */\nwindow.SYNB = {base: true};\n'
ALPHA_JS = 'window.SYNB.alpha = true;\n'
BETA_JS = 'window.SYNB.beta = true;\n'


def write(path, text=''):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def read_bytes(path):
    with open(path, 'rb') as fh:
        return fh.read()


def sha(path):
    return hashlib.sha256(read_bytes(path)).hexdigest()


def trk(name):
    """One <trk> block as a recorder writes it: several lines, indented points, an entity in the name."""
    return ('<trk><name>%s &amp; back</name><type>synthetic</type><trkseg>\n'
            '  <trkpt lat="39.1000" lon="-120.1000"><ele>2000.5</ele><time>2026-03-10T08:00:00Z</time></trkpt>\n'
            '  <trkpt lat="39.2000" lon="-120.2000"><ele>2100.0</ele><time>2026-03-10T09:00:00Z</time></trkpt>\n'
            '</trkseg></trk>' % name)


def gpx(name):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1" creator="synthetic recorder" xmlns="http://www.topografix.com/GPX/1/1">\n'
            '<metadata><name>%s</name></metadata>\n%s\n</gpx>\n' % (name, trk(name)))


def forget_builds():
    """Empty the page modules' per-build caches: report's title counts are keyed by the identity of one site's list and
    multi-day's drawn symbols by slug, so neither may outlive a build (another temp root reuses both)."""
    for name, cache in (('report', '_TITLE_COUNTS'), ('multiday', '_DRAWN')):
        mod = sys.modules.get('sitegen.pages.' + name)
        if mod is not None and hasattr(mod, cache):
            getattr(mod, cache).clear()


def trk_tags(text):
    """How many <trk> elements a GPX text opens (<trkseg> and <trkpt> are not counted)."""
    return len(re.findall(r'<trk[\s>]', text))


def redirect_defaults(fn, stand_ins):
    """fn.__defaults__ with every value that is one of the real paths replaced by its stand-in in the temp root."""
    return tuple(stand_ins.get(v, v) if isinstance(v, str) else v for v in (fn.__defaults__ or ()))


@contextlib.contextmanager
def redirected(root, today=TODAY):
    """tools/build.py and everything it calls, pointed at the synthetic repository root `root` (see the docstring)."""
    trips = os.path.join(root, 'content', 'trips')
    home = os.path.join(root, 'content', 'home.json')
    out = os.path.join(root, '_site')
    stand_ins = {curation.HOME_JSON: home, content.TRIPS_DIR: trips}
    # what a build registers with core (the trips by address, the Other sub-types, the share image and, since Phase 5,
    # the regions that have a page) is put back afterwards: core's own lists and dicts, with what they held
    saved = helpers.snapshot(core)
    with contextlib.ExitStack() as stack:
        for fn in [v for v in vars(curation).values() if isinstance(v, types.FunctionType) and v.__module__ == curation.__name__]:
            if redirect_defaults(fn, stand_ins) != (fn.__defaults__ or ()):
                stack.enter_context(mock.patch.object(fn, '__defaults__', redirect_defaults(fn, stand_ins)))
        for target, name, value in ((content, 'TRIPS_DIR', trips), (content, 'RENDERED', os.path.join(root, 'rendered')),
                                    (content, '_today', lambda: today), (curation, 'HOME_JSON', home),
                                    (core, 'ROOT', root), (core, '_SITE_META', []),
                                    (build, 'ROOT', root), (build, 'OUT', out), (build, 'LINK', False)):
            stack.enter_context(mock.patch.object(target, name, value))
        forget_builds()
        try:
            yield out
        finally:
            helpers.restore(saved)
            forget_builds()


def run_build(root, today=TODAY, only=None):
    """build.build() on the synthetic root; -> (the output folder, the pages it returned). only: the page modules to
    build, as `build.py --only` hands them over."""
    with redirected(root, today) as out:
        assert build.OUT == out and out.startswith(root), 'the output folder is not inside the temp root'
        return out, build.build(verbose=False, only=only)


def add_trip(root, slug, lines=(), **meta):
    assert slug.startswith(PREFIX), 'fixture slug %r lacks the %r prefix' % (slug, PREFIX)
    folder = helpers.make_trip(os.path.join(root, 'content', 'trips'), slug, **meta)
    if lines:
        path = os.path.join(folder, 'index.md')
        head, rest = read(path).split('\n---\n', 1)
        write(path, '%s\n%s\n---\n%s' % (head, '\n'.join(lines), rest))
    return folder


# iCloud conflict copies under assets/ (contract 10.3): a copy of a page stylesheet and of a page script beside the real
# ones (their rules and statements would be in the bundle twice), a copy whose original is gone, and a copy of a file the
# build copies as it is. path under assets/ -> text; every one says 'conflict copy', which no published file may
ASSET_COPIES = {
    'css/pages/alpha 2.css': ALPHA_CSS + '.synb-conflict-alpha { color: red; } /* conflict copy */\n',
    'css/pages/trips 2.css': '.synb-conflict-trips { content: "conflict copy"; }\n',
    'js/pages/alpha 2.js': ALPHA_JS + 'window.SYNB.conflictAlpha = "conflict copy";\n',
    'js/pages/trips 2.js': 'window.SYNB.conflictTrips = "conflict copy";\n',
    'favicon 2.svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><!-- conflict copy --></svg>',
    'site 3.webmanifest': '{"name": "conflict copy"}',
}


def write_assets(root):
    write(os.path.join(root, 'assets', 'css', 'base.css'), BASE_CSS)
    write(os.path.join(root, 'assets', 'css', 'pages', 'alpha.css'), ALPHA_CSS)
    write(os.path.join(root, 'assets', 'css', 'pages', 'beta.css'), BETA_CSS)
    write(os.path.join(root, 'assets', 'css', 'print.css'), PRINT_CSS)
    write(os.path.join(root, 'assets', 'js', 'base.js'), BASE_JS)
    write(os.path.join(root, 'assets', 'js', 'pages', 'alpha.js'), ALPHA_JS)
    write(os.path.join(root, 'assets', 'js', 'pages', 'beta.js'), BETA_JS)
    write(os.path.join(root, 'assets', 'favicon.svg'), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"/>')
    for rel, text in ASSET_COPIES.items():
        write(os.path.join(root, 'assets', *rel.split('/')), text)


def write_home(root, slugs):
    write(os.path.join(root, 'content', 'home.json'), json.dumps({'featured_slugs': slugs}))


RENDERED_STORY = ['map-wide.webp', 'map-col.webp', 'map-phone.webp', 'map-wide.base.svg', 'map-col.base.svg', 'map-phone.base.svg',
                  'legacy.png']
RENDERED_STORY_COPIES = ['map-wide 3.webp', 'map-col 2.webp', 'map-phone 12.webp', 'map-wide 2.base.svg', 'map-col 4.base.svg',
                         'legacy 5.png']
RENDERED_SITE = ['region-synb-desktop.webp', 'region-synb-phone.webp', 'region-synb-desktop.base.svg', 'legend.png']
RENDERED_SITE_COPIES = ['region-synb-desktop 3.webp', 'region-synb-phone 2.webp', 'region-synb-desktop 2.base.svg', 'legend 4.png']


# render folders left behind by tracks that are gone (contract 10.3: renders belong to a track): the single-day report
# without a track.gpx and the multi-day trip none of whose days has a track. Every file in them says 'stale render'
STALE = ['synb-notrack', 'synb-tour-none']
STALE_FILES = ['map-wide.webp', 'map-col.webp', 'map-phone.webp', 'map-wide.base.svg', 'map-col.base.svg', 'map-phone.base.svg',
               'overview-wide.webp', 'overview-col.webp', 'overview-phone.webp', 'overview-wide.base.svg', 'legacy.png']


def write_stale(root):
    for slug in STALE:
        folder = os.path.join(root, 'rendered', 'trips', slug)
        meta = {'maps': {}, 'charts': {}}
        sizes = {'wide': (1440, 640), 'col': (718, 400), 'phone': (390, 336)}
        for kind in ('map', 'overview'):
            for size, (w, h) in sizes.items():
                name = '%s-%s' % (kind, size)
                meta['maps'][name] = {'w': w, 'h': h, 'png': name + '.webp', 'base': name + '.base.svg'}
                write(os.path.join(folder, name + '.svg.html'), '<svg width="%d" height="%d" viewBox="0 0 %d %d"><!-- stale render --></svg>' % (w, h, w, h))
        for size, w in (('wide', 1248), ('col', 718), ('phone', 358)):
            for kind in ('profile', 'speed'):
                name = '%s-%s' % (kind, size)
                meta['charts'][name] = {'w': w, 'h': 160, 'kind': kind, 'gps_max_ft': 9514.0, 'min_ft': 6890.0, 'vx': 2.0}
                write(os.path.join(folder, name + '.svg.html'), '<svg width="%d" height="160" viewBox="0 0 %d 160"><!-- stale render --></svg>' % (w, w))
        write(os.path.join(folder, 'meta.json'), json.dumps(meta))
        for name in STALE_FILES:
            write(os.path.join(folder, name), 'stale render ' + name)
        for name in ('tile', 'g112', 'g64'):
            write(os.path.join(folder, name + '.svg.html'),
                  '<svg class="%s" viewBox="0 0 200 152" aria-hidden="true"><!-- stale render -->'
                  '<path class="gl-trk" d="M0 0L1 1" style="stroke: {{route}}"/></svg>' % name)


def write_rendered(root):
    """What tools/render.py leaves for one trip and for the site maps, plus iCloud's conflict copies of those files."""
    write_stale(root)
    folder = os.path.join(root, 'rendered', 'trips', 'synb-story')
    meta = {'maps': {}, 'charts': {}}
    for name, (w, h) in (('map-wide', (1440, 640)), ('map-col', (718, 400)), ('map-phone', (390, 336))):
        meta['maps'][name] = {'w': w, 'h': h, 'png': name + '.webp', 'base': name + '.base.svg'}
        write(os.path.join(folder, name + '.svg.html'), '<svg width="%d" height="%d" viewBox="0 0 %d %d"></svg>' % (w, h, w, h))
    write(os.path.join(folder, 'meta.json'), json.dumps(meta))
    write(os.path.join(folder, 'meta 2.json'), json.dumps({'maps': {}, 'charts': {}}))     # a stale conflict copy
    for name in RENDERED_STORY:
        write(os.path.join(folder, name), 'real ' + name)
    for name in RENDERED_STORY_COPIES:
        write(os.path.join(folder, name), 'conflict copy ' + name)
    for name in ('tile', 'g112', 'g64'):
        write(os.path.join(folder, name + '.svg.html'),
              '<svg class="%s" viewBox="0 0 200 152" aria-hidden="true"><path class="gl-trk" d="M0 0L1 1" style="stroke: {{route}}"/></svg>' % name)
    write(os.path.join(folder, 'tile 2.svg.html'), '<svg class="tile" viewBox="0 0 1 1"></svg>')
    # a whole conflict-copy folder beside the trip's (iCloud makes those too): no trip has that slug
    write(os.path.join(root, 'rendered', 'trips', 'synb-story 2', 'map-wide.webp'), 'conflict folder')
    write(os.path.join(root, 'rendered', 'trips', 'synb-story 2', 'meta.json'), json.dumps(meta))
    site = os.path.join(root, 'rendered', 'site')
    write(os.path.join(site, 'meta.json'), json.dumps({'hash': '', 'maps': {}, 'regions': [], 'all_regions': [REGION]}))
    write(os.path.join(site, 'meta 3.json'), json.dumps({'hash': 'stale', 'maps': {}, 'regions': [], 'all_regions': []}))
    for name in RENDERED_SITE:
        write(os.path.join(site, name), 'real ' + name)
    for name in RENDERED_SITE_COPIES:
        write(os.path.join(site, name), 'conflict copy ' + name)


def write_site(root):
    """The fixture of the module docstring."""
    story = add_trip(root, 'synb-story', title=TITLES['synb-story'], activity='hike', date='2026-06-01', region=REGION, place='Synthetic Basin',
                     body=LONG, track=True, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic story photo', sm=True)])
    write(os.path.join(story, 'track.gpx'), gpx('Synthetic story'))
    helpers.touch(os.path.join(story, 'photos', '01.th.webp'))
    add_trip(root, 'synb-notrack', title=TITLES['synb-notrack'], activity='mtb', date='2026-05-01', region=REGION, body=LONG,
             photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic trackless photo')])
    add_trip(root, 'synb-plain', title=TITLES['synb-plain'], activity='other', subtype='SUP', date='2026-04-20', region=REGION)
    tour = add_trip(root, 'synb-tour', title=TITLES['synb-tour'], activity='ski', kind='multi-day', region=REGION,
                    days=[{'title': 'Synthetic Day One', 'date': '2026-03-10', 'body': LONG}, {'title': 'Synthetic Day Two', 'date': '2026-03-11'}])
    write(os.path.join(tour, 'days', '01.gpx'), gpx('Synthetic tour day one'))
    write(os.path.join(tour, 'days', '02.gpx'), gpx('Synthetic tour day two'))
    half = add_trip(root, 'synb-tour-half', title=TITLES['synb-tour-half'], activity='ski', kind='multi-day', region=REGION,
                    days=[{'title': 'Synthetic Day One', 'date': '2026-02-20'}, {'title': 'Synthetic Day Two', 'date': '2026-02-21', 'track': False}])
    write(os.path.join(half, 'days', '01.gpx'), gpx('Synthetic half tour day one'))
    add_trip(root, 'synb-tour-none', title=TITLES['synb-tour-none'], activity='climb', kind='multi-day', region=REGION,
             days=[{'title': 'Synthetic Day One', 'date': '2026-02-10', 'track': False, 'body': LONG},
                   {'title': 'Synthetic Day Two', 'date': '2026-02-11', 'track': False}])
    journal = add_trip(root, 'synb-journal', title=TITLES['synb-journal'], activity='hike', kind='series', date='2024-04-22', end_date='2024-04-24',
                       region=REGION,
                       days=[{'id': '001', 'title': 'Synthetic Camp One', 'date': '2024-04-22'},
                             {'id': '002', 'title': 'Synthetic Camp Two', 'date': '2024-04-23', 'body': LONG},
                             {'id': '003', 'title': 'Synthetic Camp Three', 'date': '2024-04-24', 'track': False}])
    write(os.path.join(journal, 'days', '001.gpx'), gpx('Synthetic journal day one'))
    write(os.path.join(journal, 'days', '002.gpx'), gpx('Synthetic journal day two'))
    goal = add_trip(root, 'synb-goal', title=TITLES['synb-goal'], activity='hike', kind='planned', region=REGION, track=True)
    write(os.path.join(goal, 'track.gpx'), gpx('Synthetic goal'))
    add_trip(root, 'synb-idea', title=TITLES['synb-idea'], activity='hike', kind='planned', region=REGION)
    draft = add_trip(root, 'synb-draft', title=TITLES['synb-draft'], activity='hike', date='2026-08-01', region=REGION, draft=True, track=True,
                     body=LONG, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic draft photo')])
    write(os.path.join(draft, 'track.gpx'), gpx('Synthetic draft'))
    write_home(root, ['synb-story', 'synb-tour'])
    write_assets(root)
    write_rendered(root)
    # something a previous build left behind: build() starts from an empty output folder
    write(os.path.join(root, '_site', 'stale', 'index.html'), '<p>stale</p>')
    write(os.path.join(root, '_site', 'trips', 'synb-gone', 'synb-gone.gpx'), 'stale')


_SHARED = {}


def built():
    """The fixture, written and built once for the module: .root, .out, .pages (what build() returned), .trips_dir."""
    if 'fx' not in _SHARED:
        tmp = tempfile.TemporaryDirectory()
        _SHARED['tmp'] = tmp
        write_site(tmp.name)
        out, pages = run_build(tmp.name)
        _SHARED['fx'] = types.SimpleNamespace(root=tmp.name, out=out, pages=pages, trips_dir=os.path.join(tmp.name, 'content', 'trips'))
    return _SHARED['fx']


def tearDownModule():
    _SHARED.pop('fx', None)
    _SHARED.pop('nt', None)
    _SHARED.pop('rg', None)
    for key in ('tmp', 'nt_tmp', 'rg_tmp'):
        tmp = _SHARED.pop(key, None)
        if tmp is not None:
            tmp.cleanup()
    helpers.no_region_pages_left()      # the builds of this module registered sites with region pages: none may stay


def files_of(folder):
    """Every file under a folder, as sorted posix paths relative to it."""
    out = []
    for dirpath, _dirs, names in os.walk(folder):
        for name in names:
            out.append(os.path.relpath(os.path.join(dirpath, name), folder).replace(os.sep, '/'))
    return sorted(out)


def page_path(url):
    """Where build() writes a page: '' and 'x/' are folders with an index.html, anything else is the file itself."""
    return (url + 'index.html') if (url == '' or url.endswith('/')) else url


class BuiltCase(unittest.TestCase):

    def setUp(self):
        self.fx = built()
        self.out = self.fx.out
        self._docs = {}

    def path(self, rel):
        return os.path.join(self.out, *rel.split('/'))

    def html(self, url):
        return read(self.path(page_path(url)))

    def doc(self, url):
        if url not in self._docs:
            self._docs[url] = Doc(self.html(url))
        return self._docs[url]

    def html_files(self):
        return [f for f in files_of(self.out) if f.endswith('.html')]

    def gpx_hrefs(self, rel):
        """Every href of a built page that names a .gpx file, as (href, the output path it resolves to)."""
        out = []
        for href in re.findall(r'href="([^"]+)"', read(self.path(rel))):
            target = href.split('#')[0].split('?')[0]
            if not target.lower().endswith('.gpx'):
                continue
            if target.startswith(U):
                resolved = target[len(U):]
            else:
                resolved = os.path.normpath(os.path.join(os.path.dirname(rel), target)).replace(os.sep, '/')
            out.append((href, resolved))
        return out

    def links(self, url):
        """Every href of a built page that stays on the site, as (href, the output path it resolves to)."""
        out = []
        folder = os.path.dirname(page_path(url))
        for href in re.findall(r'href="([^"]+)"', self.html(url)):
            target = href.split('#')[0].split('?')[0]
            if target.startswith(U):
                out.append((href, target[len(U):]))
            elif target and '://' not in target and not target.startswith(('mailto:', 'data:')):
                out.append((href, os.path.normpath(os.path.join(folder, target)).replace(os.sep, '/') + ('/' if target.endswith('/') else '')))
        return out

    def actions(self, url):
        """(text, href, has the download attribute) of the links in the page's title actions."""
        box = self.doc(url).find('div', cls='rep-actions')
        self.assertIsNotNone(box, '%s has no title actions' % url)
        return [(a.text(), a['href'], 'download' in a) for a in box.find_all('a')]

    def bar(self, url):
        """(labels, --n) of the phone bottom bar."""
        nav = self.doc(url).find('nav', cls='bbar')
        self.assertIsNotNone(nav, '%s has no phone bottom bar' % url)
        return [a.find('span').text() for a in nav.find_all('a')], int(re.search(r'--n:(\d+)', nav['style']).group(1))


# ================================================================ what the build writes

class OutputTests(BuiltCase):

    def test_the_build_ran_inside_the_temp_root_and_the_module_constants_are_back(self):
        self.assertTrue(self.out.startswith(self.fx.root + os.sep))
        self.assertEqual(build.ROOT, ROOT)                                       # the module constants are back
        self.assertFalse(build.OUT.startswith(self.fx.root))
        self.assertEqual(content.TRIPS_DIR, os.path.join(ROOT, 'content', 'trips'))
        self.assertEqual(content.RENDERED, os.path.join(ROOT, 'rendered'))
        self.assertEqual(curation.HOME_JSON, os.path.join(ROOT, 'content', 'home.json'))
        for fn in (curation.featured_for, curation.load_manifest, curation.resolve_featured):
            self.assertFalse([d for d in (fn.__defaults__ or ()) if isinstance(d, str) and d.startswith(self.fx.root)], fn.__name__)

    def test_robots_txt_is_exactly_three_lines(self):
        self.assertEqual(read(self.path('robots.txt')),
                         'User-agent: *\nAllow: /\nSitemap: https://esichak.github.io/personal-website/sitemap.xml\n')
        self.assertEqual(read(self.path('robots.txt')), 'User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n' % core.SITE_URL)

    def test_nojekyll_is_written(self):
        self.assertEqual(read_bytes(self.path('.nojekyll')), b'')

    def test_every_page_the_build_returned_is_written_where_its_url_says(self):
        for p in self.fx.pages:
            with self.subTest(page=p.url or '(home)'):
                self.assertEqual(read(self.path(page_path(p.url))), p.html)
        urls = [p.url for p in self.fx.pages]
        self.assertEqual(len(set(urls)), len(urls))

    def test_the_pages_are_exactly_these(self):
        # contract 10.2: no trips/<slug>/map/ page for the two single-day reports without a track (HELPERS)
        want = (SITE_PAGES + SECTIONS + ['trips/%s/' % s for s in REPORTS + GOALS] + HELPERS
                + ['404.html', 'trips/search.json', 'trips/journal.json'])
        self.assertEqual(sorted(p.url for p in self.fx.pages), sorted(want))
        self.assertEqual(self.html_files(), sorted(page_path(u) for u in want if not u.endswith('.json')))
        self.assertEqual(len(HELPERS), len(REPORTS) - 4)
        self.assertEqual(sorted(u for u in want if re.fullmatch(r'trips/[^/]+/map/', u)),
                         sorted('trips/%s/map/' % s for s in ('synb-journal', 'synb-story', 'synb-tour-none')))

    def test_each_trip_has_its_page(self):
        for slug in REPORTS + GOALS:
            with self.subTest(slug=slug):
                doc = self.doc('trips/%s/' % slug)
                self.assertEqual(doc.find('h1').text(), TITLES[slug])
                self.assertEqual([ln['href'] for ln in doc.find_all('link', attrs={'rel': 'canonical'})], [U + 'trips/%s/' % slug])

    def test_the_draft_is_nowhere_in_the_output(self):
        self.assertTrue(os.path.isfile(os.path.join(self.fx.trips_dir, 'synb-draft', 'track.gpx')))
        self.assertFalse(os.path.exists(self.path('trips/synb-draft')))
        for rel in files_of(self.out):
            self.assertNotIn('synb-draft', rel)
            if rel.endswith(('.html', '.json', '.xml', '.txt', '.gpx')):
                self.assertNotIn('synb-draft', read(self.path(rel)), rel)
                self.assertNotIn(TITLES['synb-draft'], read(self.path(rel)), rel)

    def test_the_build_starts_from_an_empty_output_folder(self):
        self.assertFalse(os.path.exists(self.path('stale')))
        self.assertFalse(os.path.exists(self.path('trips/synb-gone')))

    def test_photos_are_copied_with_their_smaller_copies(self):
        self.assertEqual([f for f in files_of(self.out) if f.startswith('trips/synb-story/photos/')],
                         ['trips/synb-story/photos/01.sm.webp', 'trips/synb-story/photos/01.th.webp', 'trips/synb-story/photos/01.webp'])
        self.assertTrue(os.path.isfile(self.path('trips/synb-notrack/photos/01.webp')))

    def test_the_favicon_is_copied(self):
        self.assertEqual(read(self.path('assets/favicon.svg')), read(os.path.join(self.fx.root, 'assets', 'favicon.svg')))

    def test_the_home_page_features_what_the_temp_home_json_names(self):
        # the proof that content/home.json was read from the temp root, and that the build registered the features
        # before any page was made: the home page and the About page share the lead's cover
        want = U + 'trips/synb-story/photos/01.webp'
        for url in ('', 'about/', 'map/', 'trips/', 'tick-list/'):
            with self.subTest(page=url or '(home)'):
                found = [m['content'] for m in self.doc(url).find_all('meta', attrs={'property': 'og:image'})]
                self.assertEqual(found, [want])
        feat = self.doc('').find('section', cls='hom-featured')
        self.assertIsNotNone(feat, 'the home page has no featured section')
        links = [a['href'] for a in feat.find_all('a') if (a['href'] or '').startswith('trips/')]
        self.assertEqual(sorted(set(links), key=links.index), ['trips/synb-story/', 'trips/synb-tour/'])

    def test_core_is_left_as_it_was(self):
        self.assertNotIn('trips/synb-story/', core._TRIPS_BY_URL)
        share = core.site_share()
        self.assertFalse(share and PREFIX in share['path'])
        built_regions()                                    # the site with region pages (below) is built by now as well
        for name in RG_PAGES + [RG_PLANS, RG_DESERT]:
            self.assertNotIn(name, core._REGION_PAGES)
            self.assertIsNone(core.region_page_href('', name))


class FeedAndSitemapFileTests(BuiltCase):

    def test_sitemap_xml_is_build_sitemap_of_the_pages(self):
        text = read(self.path('sitemap.xml'))
        self.assertEqual(text, build.sitemap(self.fx.pages))
        ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
        root = ET.fromstring(text.encode('utf-8'))
        locs = [u.findtext(ns + 'loc') for u in root.findall(ns + 'url')]
        self.assertEqual(sorted(locs), sorted(U + u for u in SITE_PAGES + SECTIONS + ['trips/%s/' % s for s in REPORTS + GOALS]))
        self.assertEqual(len(locs), len(set(locs)))
        for needle in ('synb-story/map/', '404', '.json', '.gpx', 'lastmod', 'synb-draft'):
            self.assertNotIn(needle, text)

    def test_every_sitemap_url_is_a_built_page(self):
        ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
        for u in ET.fromstring(read(self.path('sitemap.xml')).encode('utf-8')).iter(ns + 'loc'):
            self.assertTrue(u.text.startswith(U))
            self.assertTrue(os.path.isfile(self.path(page_path(u.text[len(U):]))), u.text)

    def test_feed_xml_lists_the_published_reports_newest_first(self):
        text = read(self.path('feed.xml'))
        rss = ET.fromstring(text.encode('utf-8'))
        self.assertEqual((rss.tag, rss.get('version')), ('rss', '2.0'))
        items = rss.find('channel').findall('item')
        self.assertEqual([i.findtext('link') for i in items], [U + 'trips/%s/' % s for s in NEWEST_FIRST])
        self.assertEqual([i.findtext('guid') for i in items], [i.findtext('link') for i in items])
        self.assertEqual(items[0].findtext('pubDate'), 'Mon, 01 Jun 2026 12:00:00 +0000')
        self.assertEqual([i.findtext('title') for i in items], [TITLES[s] for s in NEWEST_FIRST])
        for slug in GOALS + ['synb-draft']:
            self.assertNotIn(slug, text)
        for i in items:
            self.assertTrue(os.path.isfile(self.path(page_path(i.findtext('link')[len(U):]))))

    def test_feed_xml_carries_nothing_of_the_day_it_was_built(self):
        text = read(self.path('feed.xml'))
        self.assertNotIn('2031', text)
        self.assertNotIn('lastBuildDate', text)


class StylesheetAndScriptTests(BuiltCase):

    def setUp(self):
        BuiltCase.setUp(self)
        self.css = read(self.path('assets/site.css'))
        self.js = read(self.path('assets/site.js'))

    def test_site_css_has_no_comment(self):
        self.assertNotIn('/*', self.css)
        self.assertNotIn('*/', self.css)
        for words in ('synthetic base stylesheet', 'a trailing comment', 'a block comment', 'over three lines', 'alpha page',
                      'why it is hidden', 'alpha.css', 'beta.css', 'map + profile internals'):
            self.assertNotIn(words, self.css)

    def test_site_css_keeps_every_rule_of_the_sources_in_bundle_order(self):
        lines = self.css.split('\n')
        map_rules = [ln.strip() for ln in mapkit.MAP_CSS.strip().splitlines() if ln.strip() in lines]
        self.assertGreater(len(map_rules), 10)          # the map styles of tools/lib/mapkit.py are in the bundle
        rules = [':root { --synb-ink: #111; }', '.synb-base { color: var(--synb-ink); }', map_rules[0], map_rules[-1],
                 '.synb-alpha { margin: 0 auto; }', '.synb-alpha-two { padding: 0; }', '.synb-beta { display: none; }',
                 '@media print { .synb-print { display: none; } }']
        for rule in rules:
            self.assertEqual(lines.count(rule), 1, rule)
        at = [lines.index(r) for r in rules]
        self.assertEqual(at, sorted(at))          # base.css, the map styles, pages/*.css by file name, then print.css

    def test_site_css_has_no_blank_line_no_trailing_space_and_one_final_newline(self):
        self.assertTrue(self.css.endswith('}\n'))
        self.assertNotIn('\n\n', self.css)
        for line in self.css.split('\n')[:-1]:
            self.assertTrue(line.strip())
            self.assertEqual(line, line.rstrip())

    def test_site_css_is_css_bundle_and_stripping_it_again_changes_nothing(self):
        with redirected(self.fx.root):
            self.assertEqual(self.css, build.css_bundle())
        self.assertEqual(build.strip_css_comments(self.css), self.css)

    def test_site_js_holds_the_scripts_in_order(self):
        at = [self.js.index(x) for x in (BASE_JS, ALPHA_JS, BETA_JS)]
        self.assertEqual(at, sorted(at))
        self.assertEqual(self.js.count('window.SYNB.alpha = true;'), 1)
        with redirected(self.fx.root):
            self.assertEqual(self.js, build.js_bundle())

    def test_every_page_links_the_two_bundles(self):
        for rel in self.html_files():
            with self.subTest(page=rel):
                up = '../' * rel.count('/')        # 404.html resolves its links against <base>, the site root
                text = read(self.path(rel))
                self.assertIn('<link rel="stylesheet" href="%sassets/site.css">' % up, text)
                # site.js's onerror takes the head script's 'js' (and 'km') back off when the bundle fails to load (Phase 13A)
                self.assertIn('<script src="%sassets/site.js" defer onerror="document.documentElement.classList.remove(\'js\', \'km\')"></script>' % up, text)

    def test_the_real_stylesheets_publish_without_a_comment(self):
        # the one read of the repository itself: assets/css through the real build.css_bundle()
        css = build.css_bundle()
        at = css.find('/*')
        self.assertEqual(at, -1, 'a comment (or comment-like text) survives in the published stylesheet: %r' % css[max(0, at - 60):at + 80])
        self.assertEqual(build.strip_css_comments(css), css)
        self.assertNotIn('\n\n', css)
        self.assertGreater(len(css), 10000)


# ================================================================ GPX: only what a trip has (contract 2.1)

class GpxTests(BuiltCase):

    def test_the_published_gpx_files_are_exactly_these(self):
        self.assertEqual([f for f in files_of(self.out) if f.lower().endswith('.gpx')], sorted(GPX_FILES))

    def test_a_copied_track_has_the_bytes_of_its_source(self):
        for rel, src in sorted(GPX_FILES.items()):
            if src is None:
                continue
            with self.subTest(file=rel):
                self.assertEqual(sha(self.path(rel)), sha(os.path.join(self.fx.trips_dir, *src.split('/'))))
                self.assertGreater(os.path.getsize(self.path(rel)), 100)

    def test_every_gpx_link_of_every_page_names_a_published_file(self):
        linked = set()
        for rel in self.html_files():
            for href, target in self.gpx_hrefs(rel):
                with self.subTest(page=rel, href=href):
                    self.assertTrue(os.path.isfile(self.path(target)), '%s links %s, which is not in the output' % (rel, href))
                    linked.add(target)
        self.assertEqual(sorted(linked), sorted(GPX_FILES))          # and every published file is offered somewhere

    # ------------------------------------------------------------ a single-day report without track.gpx

    def test_a_report_without_a_track_builds(self):
        # contract 10.2: its page is built; a full-screen map page is not (there is no map to show at full size)
        for slug in NO_TRACK:
            with self.subTest(slug=slug):
                self.assertFalse(os.path.exists(os.path.join(self.fx.trips_dir, slug, 'track.gpx')))
                self.assertTrue(os.path.isfile(self.path('trips/%s/index.html' % slug)))
                self.assertFalse(os.path.exists(self.path('trips/%s/map/index.html' % slug)))
                self.assertFalse(os.path.exists(self.path('trips/%s/map' % slug)))
                self.assertNotIn('trips/%s/map/' % slug, [p.url for p in self.fx.pages])
                self.assertEqual([f for f in files_of(self.path('trips/' + slug)) if not f.startswith('photos/')], ['index.html'])
        # the report with a track beside them has both pages
        self.assertTrue(os.path.isfile(self.path('trips/synb-story/index.html')))
        self.assertTrue(os.path.isfile(self.path('trips/synb-story/map/index.html')))

    def test_no_gpx_file_is_published_for_a_report_without_a_track(self):
        for slug in NO_TRACK:
            with self.subTest(slug=slug):
                self.assertEqual([f for f in files_of(self.path('trips/' + slug)) if f.lower().endswith('.gpx')], [])
                self.assertFalse(os.path.exists(self.path('trips/%s/%s.gpx' % (slug, slug))))
                self.assertFalse(os.path.exists(self.path('trips/%s/gpx' % slug)))

    def test_the_page_of_a_report_without_a_track_offers_no_download(self):
        # contract 10.2: no download, no route: no title action for either, no map section, no Map or GPX item in the
        # phone bar. 10.3: neither report states a stat, so neither has a Stats strip or a Stats item: the story's bar
        # would be Report alone and the bare report's nothing, and fewer than two items is no bar
        bars = {'synb-notrack': None, 'synb-plain': None}
        for slug in NO_TRACK:
            with self.subTest(slug=slug):
                url = 'trips/%s/' % slug
                text = self.html(url)
                self.assertNotIn('.gpx', text)
                self.assertNotIn('Download GPX', self.doc(url).text())
                self.assertNotIn('Download GPX', [a[0] for a in self.actions(url)])
                self.assertEqual([a for a in self.actions(url) if a[2]], [])                    # nothing to download at all
                self.assertEqual(self.actions(url), [])                                         # and no 'View route'
                self.assertEqual([n for n in self.doc(url).find('body').walk() if 'download' in n], [])
                navs = self.doc(url).find_all('nav', cls='bbar')
                if bars[slug] is None:
                    self.assertEqual(navs, [])
                else:
                    self.assertEqual(len(navs), 1)
                    labels, n = self.bar(url)
                    self.assertEqual((labels, n), bars[slug])
                    self.assertNotIn('GPX', labels)
                    self.assertNotIn('Map', labels)
                    self.assertEqual(n, len(labels))
                    self.assertEqual(navs[0].find_all('a', attrs={'download': ''}), [])
                self.assertIsNone(self.doc(url).by_id('map'))
                self.assertIsNone(self.doc(url).by_id('stats'))
                self.assertEqual(self.doc(url).find_all(cls='strip') + self.doc(url).find_all(cls='strip-note'), [])
                for needle in ('href="#map"', 'href="#stats"', 'View route', 'Route (GPX)', 'full track', 'GPS recording', 'GPX file', 'GPX'):
                    self.assertNotIn(needle, text)
                ids = {n['id'] for n in self.doc(url).root.walk() if n['id']}
                for href in re.findall(r'href="#([^"]+)"', text):
                    self.assertIn(href, ids, '%s links #%s, which is not an id on the page' % (url, href))
                # nothing on the page leads to a full-screen map page: there is none
                self.assertEqual([h for h, _f in self.links(url) if _f.startswith('trips/%s/map' % slug)], [])

    def test_no_page_of_the_site_links_a_gpx_of_a_report_without_a_track(self):
        for slug in NO_TRACK:
            for rel in files_of(self.out):
                if rel.endswith(('.html', '.json', '.xml')):
                    with self.subTest(slug=slug, file=rel):
                        text = read(self.path(rel))
                        self.assertNotIn(slug + '.gpx', text)
                        self.assertNotIn('%s/gpx/' % slug, text)

    def test_no_section_page_features_a_report_without_a_track(self):
        # contract 10.2: the featured block is built around the map, so a report without a track is never the one. Each
        # of these two sections has no other single-day report, so it has no featured block: the report is a row
        for url, slug in (('mountain-biking/', 'synb-notrack'), ('other/', 'synb-plain')):
            with self.subTest(page=url):
                doc = self.doc(url)
                self.assertIsNone(doc.by_id('featured'), '%s features a report without a track' % url)
                self.assertNotIn('sec-feat', self.html(url))
                rows = doc.by_id('reports')
                self.assertIsNotNone(rows, '%s has no report list' % url)
                self.assertIsNotNone(rows.find('a', attrs={'href': '../trips/%s/' % slug}))
                self.assertEqual(doc.find_all('a', cls='sec-feat-gpx'), [])
                self.assertNotIn('Download GPX', doc.text())
                self.assertNotIn('.gpx', self.html(url))
                self.assertNotIn('trips/%s/map/' % slug, self.html(url))
        # mountain-biking/ keeps no link to itself that leads nowhere (other/: SiteCheckTests, below)
        ids = {n['id'] for n in self.doc('mountain-biking/').root.walk() if n['id']}
        self.assertEqual([h for h in re.findall(r'href="#([^"]+)"', self.html('mountain-biking/')) if h not in ids], [])

    def test_a_report_with_a_track_keeps_its_three_controls(self):
        # the positive control: the same pages and blocks do offer the file when there is one
        self.assertIn(('Download GPX', 'synb-story.gpx', True), self.actions('trips/synb-story/'))
        labels, n = self.bar('trips/synb-story/')
        self.assertEqual(labels[-1], 'GPX')
        self.assertEqual(n, len(labels))
        last = self.doc('trips/synb-story/').find('nav', cls='bbar').find_all('a')[-1]
        self.assertEqual((last['href'], 'download' in last), ('synb-story.gpx', True))
        button = self.doc('hiking/').by_id('featured').find('a', cls='sec-feat-gpx')
        self.assertIsNotNone(button)
        self.assertEqual((button.text(), button['href'], 'download' in button), ('Download GPX', '../trips/synb-story/synb-story.gpx', True))

    # ------------------------------------------------------------ multi-day trips

    def test_a_multi_day_trip_without_any_day_track_gets_no_combined_file(self):
        self.assertEqual([f for f in files_of(self.path('trips/synb-tour-none')) if f.lower().endswith('.gpx')], [])
        self.assertFalse(os.path.exists(self.path('trips/synb-tour-none/synb-tour-none.gpx')))
        self.assertFalse(os.path.exists(self.path('trips/synb-tour-none/gpx')))

    def test_its_page_offers_no_download_all(self):
        url = 'trips/synb-tour-none/'
        self.assertNotIn('Download all GPX', self.doc(url).text())
        self.assertNotIn('.gpx', self.html(url))
        self.assertEqual([a for a in self.actions(url) if a[2] or 'GPX' in a[0]], [])
        labels, n = self.bar(url)
        self.assertNotIn('GPX', labels)
        self.assertEqual(n, len(labels))
        self.assertEqual(self.actions(url)[0][:2], ('Day by day', '#day-1'))        # the other actions are as before

    def test_a_multi_day_trip_with_tracks_offers_download_all(self):
        for slug in ('synb-tour', 'synb-tour-half'):
            with self.subTest(slug=slug):
                url = 'trips/%s/' % slug
                self.assertIn(('Download all GPX', slug + '.gpx', True), self.actions(url))
                labels, n = self.bar(url)
                self.assertEqual(labels[-1], 'GPX')
                self.assertEqual(n, len(labels))
                last = self.doc(url).find('nav', cls='bbar').find_all('a')[-1]
                self.assertEqual((last['href'], 'download' in last), (slug + '.gpx', True))

    def test_the_combined_file_holds_every_days_trk_block_unchanged_and_in_order(self):
        text = read(self.path('trips/synb-tour/synb-tour.gpx'))
        one, two = trk('Synthetic tour day one'), trk('Synthetic tour day two')
        self.assertEqual(text.count(one), 1)
        self.assertEqual(text.count(two), 1)
        self.assertLess(text.index(one), text.index(two))
        self.assertEqual(text.count('<trk>'), 2)
        root = ET.fromstring(text.encode('utf-8'))
        ns = '{http://www.topografix.com/GPX/1/1}'
        self.assertEqual(root.tag, ns + 'gpx')
        self.assertEqual(root.find(ns + 'metadata').findtext(ns + 'name'), TITLES['synb-tour'])      # the & escaped in the file
        self.assertEqual([t.findtext(ns + 'name') for t in root.findall(ns + 'trk')],
                         ['Synthetic tour day one & back', 'Synthetic tour day two & back'])
        self.assertEqual(len(root.findall('%strk/%strkseg/%strkpt' % (ns, ns, ns))), 4)

    def test_a_day_without_a_track_adds_nothing_to_the_combined_file(self):
        text = read(self.path('trips/synb-tour-half/synb-tour-half.gpx'))
        self.assertEqual(text.count('<trk>'), 1)
        self.assertEqual(text.count(trk('Synthetic half tour day one')), 1)
        ET.fromstring(text.encode('utf-8'))
        self.assertFalse(os.path.exists(self.path('trips/synb-tour-half/gpx/synb-tour-half-day-02.gpx')))
        self.assertNotIn('synb-tour-half-day-02.gpx', self.html('trips/synb-tour-half/'))
        self.assertIn('gpx/synb-tour-half-day-01.gpx', self.html('trips/synb-tour-half/'))

    def test_a_journal_gets_its_day_files_and_no_combined_file(self):
        self.assertFalse(os.path.exists(self.path('trips/synb-journal/synb-journal.gpx')))
        self.assertEqual([f for f in files_of(self.path('trips/synb-journal')) if f.endswith('.gpx')],
                         ['gpx/synb-journal-day-001.gpx', 'gpx/synb-journal-day-002.gpx'])

    def test_goals_publish_a_gpx_only_with_a_track(self):
        self.assertIn(('Download planned GPX', 'synb-goal.gpx', True), self.actions('trips/synb-goal/'))
        self.assertEqual([f for f in files_of(self.path('trips/synb-idea')) if f.endswith('.gpx')], [])
        self.assertNotIn('.gpx', self.html('trips/synb-idea/'))


class SiteCheckTests(BuiltCase):
    """The fixture site through the checks `build.py --check` runs (tools/sitegen/sitecheck.py), GPX bytes included."""

    def test_the_built_site_has_no_problem(self):
        self.assertEqual(sitecheck.check(self.out, self.fx.trips_dir), [])

    def test_a_section_of_reports_without_a_track_keeps_no_dead_link_to_its_featured_block(self):
        # contract 10.3: on other/, whose one report (synb-plain, SUP) has no track, there is no featured block, and the
        # Paddleboarding segment of the type filter links the report list instead (it linked #featured, an id the page
        # did not have: the one line the site check used to find here)
        doc = self.doc('other/')
        self.assertIsNone(doc.by_id('featured'))
        ids = {n['id'] for n in doc.root.walk() if n['id']}
        dead = [h for h in re.findall(r'href="#([^"]+)"', self.html('other/')) if h not in ids]
        self.assertEqual(dead, [])
        self.assertEqual(sitecheck.check(self.out, self.fx.trips_dir), [])
        self.assertNotIn('#featured', self.html('other/'))

    def test_the_other_pages_type_segments(self):
        # 10.3: All -> #reports; a sub-type with reports -> #featured when the page has a featured block, else #reports;
        # a sub-type without reports is a disabled link without an href
        nav = self.doc('other/').find('nav', attrs={'data-filter-nav': 'reports'})
        self.assertIsNotNone(nav, 'other/ has no type filter')
        segs = [(a.find('span').text(), a['href'], a['data-filter'], a['aria-disabled']) for a in nav.find_all('a')]
        self.assertEqual(segs, [('All', '#reports', 'all', None), ('Paddleboarding', '#reports', 'SUP', None),
                                ('Rafting', None, None, 'true'), ('Kayaking', None, None, 'true'), ('Mountaineering', None, None, 'true')])
        self.assertIsNotNone(self.doc('other/').by_id('reports'))


class SectionDescriptionTests(BuiltCase):
    """contract 10.3: a section's description ends ', with the full GPX track and map.' (one report) or ', each with the
    full GPX track and map.' only when every report it lists has a track (core.has_track: its own, or a day's)."""

    def description(self, url):
        head = self.doc(url).find('head')
        desc = head.find('meta', attrs={'name': 'description'})['content']
        self.assertEqual(head.find('meta', attrs={'property': 'og:description'})['content'], desc)
        return desc

    def test_the_fixture_sections(self):
        # hiking: the story and the journal, both with tracks; ski: two tours, each with a day track; the other three
        # sections each list one trip without any track
        self.assertEqual(self.description('hiking/'), '2 hiking trip reports (Synthetic Range), each with the full GPX track and map.')
        self.assertEqual(self.description('ski/'), '2 backcountry skiing trip reports (Synthetic Range), each with the full GPX track and map.')
        self.assertEqual(self.description('mountain-biking/'), '1 mountain biking trip report (Synthetic Range).')
        self.assertEqual(self.description('other/'), '1 paddleboarding trip report (Synthetic Range).')
        self.assertEqual(self.description('climbing/'), '1 climbing trip report (Synthetic Range).')

    def test_a_section_with_some_tracks_and_one_with_none(self):
        self.fx = built_no_track()
        self.out = self.fx.out
        self.assertEqual(self.description('hiking/'), '4 hiking trip reports (Synthetic Range).')            # two of four
        self.assertEqual(self.description('climbing/'), '3 climbing trip reports (Synthetic Range).')        # two of three
        self.assertEqual(self.description('mountain-biking/'), '2 mountain biking trip reports (Synthetic Range).')      # none
        for url in ('hiking/', 'climbing/', 'mountain-biking/'):
            self.assertNotIn('GPX', self.description(url))
            self.assertNotIn('map', self.description(url))

    def test_description_word_for_word(self):
        from sitegen.pages import section
        with redirected(self.fx.root):
            trips = {t['slug']: t for t in content.load_all()}
        story, journal, notrack = trips['synb-story'], trips['synb-journal'], trips['synb-notrack']
        tour, half, none = trips['synb-tour'], trips['synb-tour-half'], trips['synb-tour-none']
        self.assertEqual([core.has_track(t) for t in (story, journal, notrack, tour, half, none)], [True, True, False, True, True, False])
        d = section.description
        promise_one, promise_each = ', with the full GPX track and map.', ', each with the full GPX track and map.'
        # every trip tracked: singular and plural, as it always read
        self.assertEqual(d('hike', [story]), '1 hiking trip report (Synthetic Range)' + promise_one)
        self.assertEqual(d('hike', [story, journal]), '2 hiking trip reports (Synthetic Range)' + promise_each)
        self.assertEqual(d('ski', [tour, half]), '2 backcountry skiing trip reports (Synthetic Range)' + promise_each)   # a day's track counts
        self.assertEqual(d('ski', [half]), '1 backcountry skiing trip report (Synthetic Range)' + promise_one)
        # some, and none: the sentence ends after the regions
        self.assertEqual(d('hike', [story, notrack]), '2 hiking trip reports (Synthetic Range).')
        self.assertEqual(d('hike', [notrack, story, journal]), '3 hiking trip reports (Synthetic Range).')
        self.assertEqual(d('ski', [tour, none]), '2 backcountry skiing trip reports (Synthetic Range).')
        self.assertEqual(d('mtb', [notrack]), '1 mountain biking trip report (Synthetic Range).')
        self.assertEqual(d('climb', [none]), '1 climbing trip report (Synthetic Range).')
        self.assertEqual(d('climb', [none, notrack]), '2 climbing trip reports (Synthetic Range).')
        # without a region the promise, when it is made, follows the count directly
        bare, bare_none = dict(story, region=None), dict(notrack, region=None)
        self.assertEqual(d('hike', [bare]), '1 hiking trip report' + promise_one)
        self.assertEqual(d('hike', [bare_none]), '1 hiking trip report.')
        self.assertEqual(d('hike', [bare, bare]), '2 hiking trip reports' + promise_each)
        self.assertEqual(d('hike', [bare, bare_none]), '2 hiking trip reports.')


# ================================================================ a site of reports without a track (contract 10.2)

SHORT = 'Synthetic note.'
PLAIN_LONG = ('Synthetic write-up for a build test, long enough to count as a written report. '
              'Second synthetic paragraph of the same write-up, with a few more synthetic words.')
NT_TITLES = {'synb-nt-flag': 'Synthetic Flagged Without Track', 'synb-nt-twin': 'Synthetic Twin', 'synb-twin': 'Synthetic Twin',
             'synb-hike-flag': 'Synthetic Flagged Hike', 'synb-nt-climb': 'Synthetic Newest Climb', 'synb-climb-a': 'Synthetic Climb A',
             'synb-climb-b': 'Synthetic Climb B', 'synb-nt-ride-a': 'Synthetic Ride A', 'synb-nt-ride-b': 'Synthetic Ride B'}
NT_WITH = ['synb-twin', 'synb-hike-flag', 'synb-climb-a', 'synb-climb-b']                               # a track, none rendered
NT_WITHOUT = ['synb-nt-flag', 'synb-nt-twin', 'synb-nt-climb', 'synb-nt-ride-a', 'synb-nt-ride-b']     # no track.gpx
# core.summary of each report without a track: what its descriptions lead with (or are, when it has no write-up)
NT_SUMMARY = {
    'synb-nt-flag': 'Hiking trip report: Synthetic Flagged Without Track, Synthetic Range, Wed, Jul 1, 2026.',
    'synb-nt-twin': 'Hiking trip report: Synthetic Twin, Synthetic Range, Sat, Jun 20, 2026. 7.5 mi, 2,625 ft gain.',
    'synb-nt-climb': 'Climbing trip report: Synthetic Newest Climb, Synthetic Range, Fri, Apr 10, 2026. 1.9 mi.',
    'synb-nt-ride-a': 'Mountain biking trip report: Synthetic Ride A, Synthetic Range, Sun, Feb 1, 2026. 12.4 mi.',
    'synb-nt-ride-b': 'Mountain biking trip report: Synthetic Ride B, Synthetic Range, Thu, Jan 15, 2026.',
}
NT_BODY = {'synb-nt-flag': PLAIN_LONG, 'synb-nt-twin': PLAIN_LONG, 'synb-nt-climb': SHORT, 'synb-nt-ride-a': '', 'synb-nt-ride-b': ''}


def write_no_track_site(root):
    """Hiking: the newest report is marked featured and has no track; the next one has none either and shares its title
    with a third, which has a track; the oldest is marked featured and has a track. Climbing: the newest report has no
    track, two older ones do. Mountain biking: two reports, neither with a track. The home page features the flagged
    report without a track and the twin with one."""
    add_trip(root, 'synb-nt-flag', title=NT_TITLES['synb-nt-flag'], activity='hike', date='2026-07-01', region=REGION, featured=True, body=LONG,
             photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one', sm=True),
                     photo('photos/02.webp', LANDSCAPE, alt='Synthetic photo two')])
    add_trip(root, 'synb-nt-twin', title=NT_TITLES['synb-nt-twin'], activity='hike', date='2026-06-20', region=REGION, body=LONG,
             stats={'distance_km': 12.0, 'gain_m': 800})
    add_trip(root, 'synb-nt-climb', title=NT_TITLES['synb-nt-climb'], activity='climb', date='2026-04-10', region=REGION, body=SHORT,
             stats={'distance_km': 3.0})
    add_trip(root, 'synb-nt-ride-a', title=NT_TITLES['synb-nt-ride-a'], activity='mtb', date='2026-02-01', region=REGION,
             stats={'distance_km': 20.0, 'moving': '1:00'})
    add_trip(root, 'synb-nt-ride-b', title=NT_TITLES['synb-nt-ride-b'], activity='mtb', date='2026-01-15', region=REGION)
    for slug, extra in (('synb-twin', dict(activity='hike', date='2026-06-10', body=LONG)),
                        ('synb-hike-flag', dict(activity='hike', date='2026-05-01', featured=True)),
                        ('synb-climb-a', dict(activity='climb', date='2026-03-01')),
                        ('synb-climb-b', dict(activity='climb', date='2026-01-01'))):
        folder = add_trip(root, slug, title=NT_TITLES[slug], region=REGION, track=True, **extra)
        write(os.path.join(folder, 'track.gpx'), gpx(NT_TITLES[slug]))
    write_home(root, ['synb-nt-flag', 'synb-twin'])
    write_assets(root)


def built_no_track():
    """The second site, written and built once for the module: .root, .out, .pages, .trips_dir."""
    if 'nt' not in _SHARED:
        tmp = tempfile.TemporaryDirectory()
        _SHARED['nt_tmp'] = tmp
        write_no_track_site(tmp.name)
        out, pages = run_build(tmp.name)
        _SHARED['nt'] = types.SimpleNamespace(root=tmp.name, out=out, pages=pages, trips_dir=os.path.join(tmp.name, 'content', 'trips'))
    return _SHARED['nt']


class NoTrackSiteTests(BuiltCase):
    """contract-phase4.md 10.2 on a built site: which report a section features, which pages and files exist, and what
    every description of a report without a track says (the page's, the feed's, the structured data's)."""

    def setUp(self):
        self.fx = built_no_track()
        self.out = self.fx.out
        self._docs = {}

    def featured(self, url):
        feat = self.doc(url).by_id('featured')
        self.assertIsNotNone(feat, '%s has no featured block' % url)
        return feat

    def rows(self, url):
        """The trip links of the section's report list outside its featured block, in order."""
        feat = self.doc(url).by_id('featured')
        inside = feat.find_all('a') if feat is not None else []
        seen = []
        for a in self.doc(url).by_id('reports').find_all('a'):
            href = a['href'] or ''
            if href.startswith('../trips/') and not any(a is x for x in inside) and href not in seen:
                seen.append(href)
        return seen

    def descriptions(self, slug):
        """What the page says the report is: (meta description, og:description, the JSON-LD description or None)."""
        head = self.doc('trips/%s/' % slug).find('head')
        ld = head.find_all('script', attrs={'type': 'application/ld+json'})
        self.assertLessEqual(len(ld), 1)
        return (head.find('meta', attrs={'name': 'description'})['content'],
                head.find('meta', attrs={'property': 'og:description'})['content'],
                json.loads(ld[0].text(clean=False))['description'] if ld else None)

    def feed_descriptions(self):
        rss = ET.fromstring(read(self.path('feed.xml')).encode('utf-8'))
        return {i.findtext('link')[len(U) + len('trips/'):-1]: i.findtext('description') for i in rss.find('channel').findall('item')}

    # ------------------------------------------------------------ the fixture is what the docstring says

    def test_the_fixture(self):
        for slug in NT_WITH:
            self.assertTrue(os.path.isfile(os.path.join(self.fx.trips_dir, slug, 'track.gpx')), slug)
        for slug in NT_WITHOUT:
            self.assertFalse(os.path.exists(os.path.join(self.fx.trips_dir, slug, 'track.gpx')), slug)
        self.assertFalse(os.path.exists(os.path.join(self.fx.root, 'rendered')))        # nothing is rendered
        self.assertEqual(sorted(NT_SUMMARY), sorted(NT_WITHOUT))
        for text in list(NT_TITLES.values()) + [PLAIN_LONG, SHORT, REGION]:
            self.assertNotIn('GPX', text)                # no title or sentence of the fixture says what the summary must not
            self.assertNotIn('map', text.lower())

    def test_the_site_check_finds_nothing(self):
        self.assertEqual(sitecheck.check(self.out, self.fx.trips_dir), [])

    # ------------------------------------------------------------ pages and files

    def test_a_map_page_for_no_report_without_a_rendered_map(self):
        # contract 10.2 as amended by Phase 6 (resilience-12): no fixture trip here is rendered, so no report has a
        # full-screen map page; a report with a track keeps its #map section, which is the 'Map not rendered yet' box,
        # and its GPX download
        urls = [p.url for p in self.fx.pages]
        self.assertEqual(sorted(u for u in urls if u.startswith('trips/') and u.endswith('/map/')), [])
        for slug in NT_WITH + NT_WITHOUT:
            with self.subTest(slug=slug):
                self.assertIn('trips/%s/' % slug, urls)
                self.assertFalse(os.path.exists(self.path('trips/%s/map' % slug)), slug)
                self.assertEqual(os.path.isfile(self.path('trips/%s/%s.gpx' % (slug, slug))), slug in NT_WITH)
                box = self.doc('trips/%s/' % slug).by_id('map')
                self.assertEqual(box is not None, slug in NT_WITH)
                if box is not None:
                    self.assertIn('rep-map--empty', box.classes)
                    self.assertIn('Map not rendered yet', box.text())
        for slug in NT_WITHOUT:
            self.assertEqual([f for f in files_of(self.path('trips/' + slug)) if f.lower().endswith('.gpx')], [])

    def test_the_sitemap_lists_the_reports_and_no_map_page(self):
        text = read(self.path('sitemap.xml'))
        for slug in NT_WITH + NT_WITHOUT:
            self.assertIn('<loc>%strips/%s/</loc>' % (U, slug), text)
        self.assertNotIn('/map/</loc>', text.replace('<loc>%smap/</loc>' % U, ''))

    def test_no_page_of_the_site_links_a_file_or_a_map_page_of_a_report_without_a_track(self):
        for rel in files_of(self.out):
            if not rel.endswith(('.html', '.json', '.xml')):
                continue
            text = read(self.path(rel))
            for slug in NT_WITHOUT:
                with self.subTest(file=rel, slug=slug):
                    self.assertNotIn(slug + '.gpx', text)
                    self.assertNotIn('%s/gpx/' % slug, text)
                    self.assertNotIn('%s/map/' % slug, text)
        home = self.html('')
        self.assertIn('href="trips/synb-nt-flag/"', home)          # the home page does feature it: it links the report
        self.assertIn('href="trips/synb-twin/"', home)

    def test_the_pages_of_the_reports_without_a_track(self):
        # slug -> title actions, the phone bar (None: no bar), the stats note, the labels of its stats strip (None: no
        # strip, contract 10.3: the report states no stat)
        want = {'synb-nt-flag': ([], (['Report', 'Photos'], 2), None, None),
                # Phase 10 (report-01): a write-up over 100 characters without photos leads the page, so no action jumps to it
                'synb-nt-twin': ([], (['Stats', 'Report'], 2), None, ['Distance', 'Gain']),
                'synb-nt-climb': ([('Read the report', '#report', False)], (['Stats', 'Report'], 2), None, ['Distance']),
                'synb-nt-ride-a': ([], None, 'Average speed is distance divided by moving time.', ['Distance', 'Moving', 'Avg speed']),
                'synb-nt-ride-b': ([], None, None, None)}
        for slug, (actions, bar, note, cells) in want.items():
            with self.subTest(slug=slug):
                url = 'trips/%s/' % slug
                text, doc = self.html(url), self.doc(url)
                self.assertEqual(self.actions(url), actions)
                navs = doc.find_all('nav', cls='bbar')
                if bar is None:
                    self.assertEqual(navs, [])
                else:
                    self.assertEqual(self.bar(url), bar)
                    self.assertEqual(len(navs), 1)
                notes = doc.find_all('p', cls='strip-note')
                # Phase 9 (ia-19): a note ends with the link to About's method
                self.assertEqual([p.text() for p in notes], [note + ' How these reports are made'] if note else [])
                self.assertEqual([p.find('a')['href'] for p in notes], ['../../about/#abo-how-h'] if note else [])
                strip = doc.by_id('stats')
                self.assertEqual([dt.text() for dt in strip.find_all('dt')] if strip is not None else None, cells)
                self.assertEqual('href="#stats"' in text, cells is not None and bar is not None)
                self.assertIsNone(doc.by_id('map'))
                for needle in ('href="#map"', '.gpx', 'View route', 'Download GPX', 'Route (GPX)', 'full track', 'GPS recording', 'GPX file'):
                    self.assertNotIn(needle, text)
                self.assertEqual([n for n in doc.find('body').walk() if 'download' in n], [])
                ids = {n['id'] for n in doc.root.walk() if n['id']}
                self.assertEqual([h for h in re.findall(r'href="#([^"]+)"', text) if h not in ids], [])
                self.assertEqual([f for _h, f in self.links(url) if f.startswith('trips/%s/map' % slug)], [])
        # the story's section row lists the two sections it has (no track, so no Map item)
        row = self.doc('trips/synb-nt-flag/').find('nav', cls='rep-toc')
        self.assertEqual([(a.text(), a['href']) for a in row.find_all('a')], [('Report', '#report'), ('Photos', '#photos')])
        # the report with a track beside them is whole
        self.assertEqual(self.actions('trips/synb-twin/'), [('View route', '#map', False), ('Download GPX', 'synb-twin.gpx', True)])
        self.assertEqual(self.bar('trips/synb-twin/'), (['Stats', 'Report', 'Map', 'GPX'], 4))     # written first: page order

    # ------------------------------------------------------------ the featured block of each section

    def test_hiking_features_the_flagged_report_that_has_a_track(self):
        # featured: true wins among the reports with a track; the newest hike is flagged too, has none, and is skipped,
        # as is the newer unflagged hike with a track
        feat = self.featured('hiking/')
        self.assertEqual(feat.find('h2').text(), NT_TITLES['synb-hike-flag'])
        self.assertEqual(feat.find('h2').find('a')['href'], '../trips/synb-hike-flag/')
        button = feat.find('a', cls='sec-feat-gpx')
        self.assertEqual((button.text(), button['href'], 'download' in button), ('Download GPX', '../trips/synb-hike-flag/synb-hike-flag.gpx', True))
        self.assertEqual(self.rows('hiking/'), ['../trips/synb-nt-flag/', '../trips/synb-nt-twin/', '../trips/synb-twin/'])
        self.assertEqual([h for h, _f in self.gpx_hrefs('hiking/index.html')], ['../trips/synb-hike-flag/synb-hike-flag.gpx'])

    def test_climbing_features_the_newest_report_that_has_a_track(self):
        # nothing flagged: the newest climb has no track, so the block is the next one's
        feat = self.featured('climbing/')
        self.assertEqual(feat.find('h2').text(), NT_TITLES['synb-climb-a'])
        self.assertEqual(feat.find('h2').find('a')['href'], '../trips/synb-climb-a/')
        self.assertEqual(self.rows('climbing/'), ['../trips/synb-nt-climb/', '../trips/synb-climb-b/'])
        self.assertEqual([h for h, _f in self.gpx_hrefs('climbing/index.html')], ['../trips/synb-climb-a/synb-climb-a.gpx'])
        self.assertNotIn(NT_TITLES['synb-nt-climb'], feat.text())

    def test_mountain_biking_has_no_featured_block(self):
        # every single-day report of the section lacks a track: no featured block, both reports are rows, no file and
        # no map page is linked, and no link of the page to itself leads nowhere
        doc = self.doc('mountain-biking/')
        text = self.html('mountain-biking/')
        self.assertIsNone(doc.by_id('featured'))
        self.assertNotIn('sec-feat', text)
        self.assertEqual(self.rows('mountain-biking/'), ['../trips/synb-nt-ride-a/', '../trips/synb-nt-ride-b/'])
        self.assertEqual(self.gpx_hrefs('mountain-biking/index.html'), [])
        self.assertNotIn('.gpx', text)
        self.assertNotIn('Download GPX', text)
        ids = {n['id'] for n in doc.root.walk() if n['id']}
        self.assertEqual([h for h in re.findall(r'href="#([^"]+)"', text) if h not in ids], [])
        for href, target in self.links('mountain-biking/'):
            self.assertTrue(os.path.exists(self.path(target.rstrip('/'))) or target == '', '%s is not in the output' % href)
        self.assertEqual(doc.find('head').find_all('link', attrs={'rel': 'preload', 'as': 'image'}), [])

    def test_every_page_links_only_ids_it_has(self):
        for rel in self.html_files():
            with self.subTest(page=rel):
                text = read(self.path(rel))
                ids = set(re.findall(r'\bid="([^"]+)"', text))
                self.assertEqual([h for h in re.findall(r'href="#([^"]+)"', text) if h not in ids], [])

    # ------------------------------------------------------------ what the report is said to be

    def test_no_description_of_a_report_without_a_track_promises_a_map_or_a_file(self):
        feed = self.feed_descriptions()
        for slug in NT_WITHOUT:
            with self.subTest(slug=slug):
                meta, og, ld = self.descriptions(slug)
                for name, text in (('description', meta), ('og:description', og), ('JSON-LD', ld), ('feed', feed[slug])):
                    if text is None:
                        continue
                    self.assertNotIn('GPX', text, name)
                    self.assertNotIn('map', text.lower(), name)
                    self.assertNotIn('chart', text.lower(), name)
                    self.assertNotIn('elevation profile', text.lower(), name)
                self.assertEqual(og, meta)
                # the feed: the factual summary, then the start of the write-up
                self.assertEqual(feed[slug], NT_SUMMARY[slug] + ((' ' + NT_BODY[slug]) if NT_BODY[slug] else ''))

    def test_the_descriptions_word_for_word(self):
        # a report with little or no write-up, or with a title another report has, leads its description with the
        # summary; a long write-up under a title of its own is the description by itself
        clip = core.clip_words
        self.assertEqual(self.descriptions('synb-nt-ride-b'), (NT_SUMMARY['synb-nt-ride-b'],) * 2 + (None,))
        self.assertEqual(self.descriptions('synb-nt-ride-a'), (NT_SUMMARY['synb-nt-ride-a'],) * 2 + (None,))
        self.assertEqual(self.descriptions('synb-nt-climb'), (NT_SUMMARY['synb-nt-climb'] + ' ' + SHORT,) * 2 + (None,))
        twin = clip(NT_SUMMARY['synb-nt-twin'] + ' ' + PLAIN_LONG, 155)
        self.assertTrue(twin.startswith(NT_SUMMARY['synb-nt-twin'] + ' Synthetic write-up for a build test'))
        self.assertEqual(self.descriptions('synb-nt-twin'), (twin, twin, twin))            # the JSON-LD description as well
        flag = self.descriptions('synb-nt-flag')
        self.assertEqual(flag[0], flag[2])
        self.assertTrue(flag[0].startswith('Synthetic write-up for a build test, long enough to count as a written report.'))
        # the twin WITH a track is described as it always was
        with_ = clip('Hiking trip report: Synthetic Twin, Synthetic Range, Wed, Jun 10, 2026. with map and GPX. ' + PLAIN_LONG, 155)
        self.assertEqual(self.descriptions('synb-twin'), (with_, with_, with_))
        self.assertEqual(self.feed_descriptions()['synb-twin'],
                         'Hiking trip report: Synthetic Twin, Synthetic Range, Wed, Jun 10, 2026. with map and GPX. ' + PLAIN_LONG)
        self.assertEqual(self.feed_descriptions()['synb-climb-a'],
                         'Climbing trip report: Synthetic Climb A, Synthetic Range, Sun, Mar 1, 2026. with map and GPX.')
        self.assertEqual(self.doc('trips/synb-nt-twin/').find('title').text(), 'Synthetic Twin, Jun 20, 2026 · %s' % core.SITE_NAME)

    def test_the_structured_data_of_a_written_report_without_a_track(self):
        for slug in ('synb-nt-flag', 'synb-nt-twin'):
            with self.subTest(slug=slug):
                ld = self.doc('trips/%s/' % slug).find('head').find_all('script', attrs={'type': 'application/ld+json'})
                self.assertEqual(len(ld), 1)
                data = json.loads(ld[0].text(clean=False))
                self.assertEqual((data['@type'], data['headline'], data['url']), ('BlogPosting', NT_TITLES[slug], U + 'trips/%s/' % slug))
                self.assertNotIn('GPX', json.dumps(data))
                self.assertNotIn('/map/', json.dumps(data))
        for slug in ('synb-nt-climb', 'synb-nt-ride-a', 'synb-nt-ride-b'):
            self.assertNotIn('ld+json', self.html('trips/%s/' % slug))


# ================================================================ a site with region pages (contract-phase5.md)

RG_RANGE, RG_COAST, RG_PLANS, RG_DESERT = 'Synthetic Reach', 'Synthetic Shore', 'Synthetic Schemes', 'Synthetic Dunes'
RG_PAGES = [RG_RANGE, RG_COAST]                 # a region map and a published report each: regions/<slug>/
RG_SLUG = {RG_RANGE: 'synthetic-reach', RG_COAST: 'synthetic-shore', RG_PLANS: 'synthetic-schemes', RG_DESERT: 'synthetic-dunes'}
RG_REPORTS = ['synb-rg-story', 'synb-rg-words', 'synb-rg-lap', 'synb-rg-shore', 'synb-rg-shore-walk', 'synb-rg-dunes',
              'synb-rg-journal']                # newest first
RG_NO_TRACK = ['synb-rg-shore-walk']            # a report without a track: no full-screen map page, and on no region map
RG_GOALS = ['synb-rg-goal', 'synb-rg-scheme']
# The trips each region map was drawn with (its entry in rendered/site/meta.json). The Reach map is in step with the
# content. The Shore map is not (contract-phase5.md section 1, as revised in round 2): it does not name the Shore's
# report without a track, and it still draws a report that is filed under the Dunes
RG_MAPS = {RG_RANGE: ['synb-rg-story', 'synb-rg-words', 'synb-rg-lap', 'synb-rg-goal'], RG_COAST: ['synb-rg-shore', 'synb-rg-dunes'],
           RG_PLANS: ['synb-rg-scheme']}
RG_CLUSTERS = {RG_RANGE: [['synb-rg-words', 'synb-rg-lap'], ['synb-rg-story', 'synb-rg-goal']]}      # the pins each cluster marker merged
RG_URLS = ['regions/synthetic-reach/', 'regions/synthetic-shore/']


def write_region_site(root):
    """A third site, with region maps: Synthetic Reach (three reports of three activities, two of them written, and a
    goal), Synthetic Shore (two reports of one activity, one of them without a track), Synthetic Schemes (a region map
    and a planned route only: no page), Synthetic Dunes (a report and no region map: no page) and a journal on no
    region map. rendered/site/ holds what tools/render.py leaves: meta.json naming the three mapped regions and the
    trips each map draws (RG_MAPS), the two image files of each map, and a fragment with a pin per trip that links to
    its page and, on the Reach map, two cluster markers (RG_CLUSTERS)."""
    story = add_trip(root, 'synb-rg-story', title='Synthetic Reach Story', activity='hike', date='2026-06-01', region=RG_RANGE,
                     place='Synthetic Basin', body=LONG, track=True, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic reach photo', sm=True)])
    write(os.path.join(story, 'track.gpx'), gpx('Synthetic reach story'))
    words = add_trip(root, 'synb-rg-words', title='Synthetic Reach Words', activity='climb', date='2025-07-01', region=RG_RANGE, body=LONG, track=True)
    write(os.path.join(words, 'track.gpx'), gpx('Synthetic reach words'))
    lap = add_trip(root, 'synb-rg-lap', title='Synthetic Reach Lap', activity='ski', date='2025-01-10', region=RG_RANGE, track=True)
    write(os.path.join(lap, 'track.gpx'), gpx('Synthetic reach lap'))
    shore = add_trip(root, 'synb-rg-shore', title='Synthetic Shore Ride', activity='mtb', date='2024-09-09', region=RG_COAST, track=True)
    write(os.path.join(shore, 'track.gpx'), gpx('Synthetic shore ride'))
    add_trip(root, 'synb-rg-shore-walk', title='Synthetic Shore Carry', activity='mtb', date='2024-08-08', region=RG_COAST)
    dunes = add_trip(root, 'synb-rg-dunes', title='Synthetic Dunes Walk', activity='hike', date='2024-05-05', region=RG_DESERT, track=True)
    write(os.path.join(dunes, 'track.gpx'), gpx('Synthetic dunes walk'))
    journal = add_trip(root, 'synb-rg-journal', title='Synthetic Reach Journal', activity='hike', kind='series', date='2023-04-22',
                       end_date='2023-04-23', region='Synthetic Trail',
                       days=[{'id': '001', 'title': 'Synthetic Camp One', 'date': '2023-04-22', 'body': LONG},
                             {'id': '002', 'title': 'Synthetic Camp Two', 'date': '2023-04-23', 'track': False}])
    write(os.path.join(journal, 'days', '001.gpx'), gpx('Synthetic reach journal day one'))
    add_trip(root, 'synb-rg-goal', title='Synthetic Reach Goal', activity='hike', kind='planned', region=RG_RANGE)
    add_trip(root, 'synb-rg-scheme', title='Synthetic Scheme', activity='ski', kind='planned', region=RG_PLANS)
    write_home(root, ['synb-rg-story'])
    write_assets(root)
    site = os.path.join(root, 'rendered', 'site')
    meta = {'hash': '', 'maps': {}, 'regions': [RG_PLANS, RG_COAST, RG_RANGE], 'all_regions': [RG_COAST, RG_DESERT, RG_RANGE, RG_PLANS]}
    for name, slugs in RG_MAPS.items():
        pins = ''.join('<a class="mk-pin" href="@@ROOT@@trips/%s/" data-key="%s" aria-label="Synthetic pin"><title>Synthetic pin</title>'
                       '<circle class="mk-hit" cx="9" cy="9" r="12" style="fill: transparent"/></a>' % (s, s) for s in slugs)
        # a cluster marker as tools/lib/mapkit.py writes it: hidden from readers, its data-keys the trips it stands for
        pins += ''.join('<g class="mk-cluster" aria-hidden="true" data-keys="%s"><title>Synthetic cluster</title>'
                        '<circle class="mk-hit" cx="40" cy="40" r="14" style="fill: transparent"/><text x="40" y="40">%d</text></g>'
                        % (' '.join(keys), len(keys)) for keys in RG_CLUSTERS.get(name, []))
        for size, (w, h) in (('desktop', (718, 620)), ('phone', (390, 480))):
            key = 'region-%s-%s' % (RG_SLUG[name], size)
            meta['maps'][key] = {'w': w, 'h': h, 'png': key + '.webp', 'base': key + '.base.svg', 'region': name, 'trips': list(slugs)}
            write(os.path.join(site, key + '.svg.html'), '<svg width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>' % (w, h, w, h, pins))
            write(os.path.join(site, key + '.webp'), 'real ' + key)
            write(os.path.join(site, key + '.base.svg'), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d"/>' % (w, h))
    write(os.path.join(site, 'meta.json'), json.dumps(meta))


def built_regions():
    """The third site, written and built once for the module: .root, .out, .pages, .trips_dir."""
    if 'rg' not in _SHARED:
        tmp = tempfile.TemporaryDirectory()
        _SHARED['rg_tmp'] = tmp
        write_region_site(tmp.name)
        out, pages = run_build(tmp.name)
        _SHARED['rg'] = types.SimpleNamespace(root=tmp.name, out=out, pages=pages, trips_dir=os.path.join(tmp.name, 'content', 'trips'))
    return _SHARED['rg']


class RegionSiteTests(BuiltCase):
    """contract-phase5.md on a built site: build.build() writes regions/<slug>/index.html for the regions that have a
    region map and a published report and for no other, lists them in sitemap.xml, leaves the feed and both search
    indexes without them, and the whole site passes the checks `build.py --check` runs. `--only region` builds them
    alone."""

    def setUp(self):
        self.fx = built_regions()
        self.out = self.fx.out
        self._docs = {}

    def test_region_is_a_page_module(self):
        self.assertIn('region', build.PAGE_MODULES)
        self.assertEqual(build.PAGE_MODULES.index('region'), build.PAGE_MODULES.index('archive') + 1)

    def test_a_page_is_written_for_each_mapped_region_with_a_report(self):
        self.assertEqual([p.url for p in self.fx.pages if p.url.startswith('regions')], RG_URLS)      # most reports first
        self.assertEqual(files_of(self.path('regions')), ['synthetic-reach/index.html', 'synthetic-shore/index.html'])
        for p in self.fx.pages:
            if p.url.startswith('regions'):
                self.assertEqual(read(self.path(page_path(p.url))), p.html)
        for name, url in zip(RG_PAGES, RG_URLS):
            with self.subTest(region=name):
                doc = self.doc(url)
                self.assertEqual([h.text() for h in doc.find_all('h1')], [name])
                self.assertEqual(doc.find('body')['class'], 'p-region')
                self.assertEqual([ln['href'] for ln in doc.find_all('link', attrs={'rel': 'canonical'})], [U + url])
                self.assertNotIn('<!-- missing', self.html(url))

    def test_no_page_for_a_region_without_a_report_or_without_a_region_map(self):
        for name in (RG_PLANS, RG_DESERT, 'Synthetic Trail'):
            slug = RG_SLUG.get(name, 'synthetic-trail')
            self.assertFalse(os.path.exists(self.path('regions/' + slug)), name)
            for rel in self.html_files():
                self.assertNotIn('regions/%s/' % slug, read(self.path(rel)), rel)
        self.assertFalse(os.path.exists(self.path('regions/index.html')))            # no index of the region pages
        # both keep their place on the Map page: a panel for the mapped one, a list for the other
        ids = {n['id'] for n in self.doc('map/').root.walk() if n['id']}
        for name in (RG_RANGE, RG_COAST, RG_PLANS, RG_DESERT):
            self.assertIn('region-' + RG_SLUG[name], ids)

    def test_the_pages_of_the_site_are_exactly_these(self):
        # no report of this site is rendered: of the full-screen map pages of trips only the journal's is built (series.py);
        # each region map has its own, map/<slug>/ (Phase 12, qa-06)
        want = (SITE_PAGES + SECTIONS + RG_URLS + ['trips/%s/' % s for s in RG_REPORTS + RG_GOALS]
                + ['trips/synb-rg-journal/map/', '404.html', 'trips/search.json', 'trips/journal.json']
                + ['map/%s/' % RG_SLUG[name] for name in (RG_RANGE, RG_COAST, RG_PLANS)])
        self.assertEqual(sorted(p.url for p in self.fx.pages), sorted(want))

    def test_the_sitemap_lists_the_region_pages(self):
        text = read(self.path('sitemap.xml'))
        self.assertEqual(text, build.sitemap(self.fx.pages))
        ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
        locs = [u.findtext(ns + 'loc') for u in ET.fromstring(text.encode('utf-8')).findall(ns + 'url')]
        self.assertEqual(sorted(locs), sorted(U + u for u in SITE_PAGES + SECTIONS + RG_URLS + ['trips/%s/' % s for s in RG_REPORTS + RG_GOALS]))
        for url in RG_URLS:
            self.assertEqual(locs.count(U + url), 1)
        self.assertEqual([u for u in locs if '/regions/' in u], [U + u for u in RG_URLS])
        for p in self.fx.pages:
            if p.url.startswith('regions'):
                self.assertIs(p.index, True)

    def test_the_feed_has_no_region_page(self):
        text = read(self.path('feed.xml'))
        self.assertNotIn('regions/', text)
        items = ET.fromstring(text.encode('utf-8')).find('channel').findall('item')
        self.assertEqual([i.findtext('link') for i in items], [U + 'trips/%s/' % s for s in RG_REPORTS])

    def test_neither_search_index_has_a_region_page(self):
        for rel in ('trips/search.json', 'trips/journal.json'):
            with self.subTest(index=rel):
                text = read(self.path(rel))
                data = json.loads(text)
                self.assertTrue(data)
                self.assertNotIn('regions/', text)
                self.assertNotIn('trip reports', text)                    # no region page's title either
        # the trips index is one entry per report, keyed by its slug, and nothing else; the journal index is the journal's days
        self.assertEqual([e['s'] for e in json.loads(read(self.path('trips/search.json')))], RG_REPORTS)
        self.assertEqual({e['s'] for e in json.loads(read(self.path('trips/journal.json')))}, {'synb-rg-journal'})
        for name in RG_PAGES:
            self.assertNotIn(RG_SLUG[name], [e['s'] for e in json.loads(read(self.path('trips/search.json')))])
        self.assertEqual([f for f in files_of(self.out) if f.endswith('.json')], ['trips/journal.json', 'trips/search.json'])

    def test_the_site_check_finds_nothing(self):
        self.assertEqual(sitecheck.check(self.out, self.fx.trips_dir), [])

    def test_the_site_check_would_notice_a_region_page_that_went_missing(self):
        # the checks do look at these pages and at the links to them: without one, its links are broken lines
        with tempfile.TemporaryDirectory() as tmp:
            copy = os.path.join(tmp, 'site')
            shutil.copytree(self.out, copy)
            shutil.rmtree(os.path.join(copy, 'regions', 'synthetic-shore'))
            problems = sitecheck.check(copy, self.fx.trips_dir)
        self.assertTrue(problems)
        self.assertTrue(any('regions/synthetic-shore' in line for line in problems), problems[:5])

    def test_every_link_and_file_of_a_region_page_is_in_the_output(self):
        for url in RG_URLS:
            with self.subTest(page=url):
                checked = 0
                for href, target in self.links(url):
                    self.assertFalse(href.startswith('/'), href)
                    if href.startswith(U):
                        self.assertEqual(href, U + url)                    # the canonical link and og:url: the page itself
                    path = self.path(target + 'index.html' if (target == '' or target.endswith('/')) else target)
                    self.assertTrue(os.path.isfile(path), '%s on %s names nothing in the output (%s)' % (href, url, target))
                    checked += 1
                self.assertGreater(checked, 30)
                for src in re.findall(r'src="([^"]+)"', self.html(url)):
                    self.assertFalse(src.startswith(('/', 'http')), src)
                    self.assertTrue(os.path.isfile(os.path.normpath(os.path.join(self.path(url), src))), '%s on %s' % (src, url))
        # the map a region page draws is published, and preloaded by the page
        for f in ('region-synthetic-reach-desktop.webp', 'region-synthetic-reach-desktop.base.svg', 'region-synthetic-reach-phone.webp',
                  'region-synthetic-reach-phone.base.svg'):
            self.assertTrue(os.path.isfile(self.path('assets/maps/' + f)))
            self.assertIn('<link rel="preload" as="image"', self.html(RG_URLS[0]))
            self.assertIn('href="../../assets/maps/%s"' % f, self.html(RG_URLS[0]).split('</head>', 1)[0])

    def test_the_pins_of_a_region_pages_map_link_from_its_folder(self):
        # the fragment's @@ROOT@@ is the way back from regions/<slug>/, two folders deep
        pins = self.doc(RG_URLS[0]).by_id('arc-map-synthetic-reach').find_all('a', cls='mk-pin')
        self.assertEqual(sorted({a['href'] for a in pins}), sorted('../../trips/%s/' % s for s in RG_MAPS[RG_RANGE]))
        self.assertEqual(len(pins), 2 * len(RG_MAPS[RG_RANGE]))                  # the desktop and the phone render

    def test_the_other_pages_link_to_the_region_pages(self):
        # the report's breadcrumb, the goal's breadcrumb and pager, the Trips page's browse row, the Map page's panel
        crumbs = self.doc('trips/synb-rg-story/').find('nav', cls='crumbs')
        self.assertEqual([a['href'] for a in crumbs.find_all('a')][-1], '../../regions/synthetic-reach/')
        goal = self.doc('trips/synb-rg-goal/')
        self.assertEqual([a['href'] for a in goal.find('nav', cls='crumbs').find_all('a')][-1], '../../regions/synthetic-reach/')
        cell = goal.find('nav', cls='pager').find('a', cls='next')
        # Phase 12 (gap4-03): the pager cell lands on the goal's own row of the region's list
        self.assertEqual((cell['href'], cell.find('span', cls='pager-n').text()),
                         ('../../regions/synthetic-reach/#arc-row-synb-rg-goal', 'All Synthetic Reach reports'))
        browse = [a['href'] for a in self.doc('trips/').find('nav', cls='trx-browse').find_all('a')]
        self.assertIn('../regions/synthetic-reach/', browse)
        self.assertIn('../regions/synthetic-shore/', browse)
        self.assertIn('../map/#region-synthetic-dunes', browse)                  # no page: its place on the Map page, as before
        # a region of journals alone is left out (Phase 7, trips.regions_of), as the Map page leaves it out
        self.assertFalse([h for h in browse if 'synthetic-trail' in h])
        panel = self.doc('map/').by_id('region-synthetic-reach')
        self.assertEqual([(a['href'], a.text()) for a in panel.find_all('a', cls='arc-reg-a')], [('../regions/synthetic-reach/', 'All Synthetic Reach reports')])
        self.assertEqual(self.doc('map/').by_id('region-synthetic-schemes').find_all('a', cls='arc-reg-a'), [])
        # a trip of a region without a page keeps its links to the Map page
        dunes = self.doc('trips/synb-rg-dunes/').find('nav', cls='crumbs')
        self.assertEqual([a['href'] for a in dunes.find_all('a')][-1], '../../map/#region-synthetic-dunes')
        scheme = self.doc('trips/synb-rg-scheme/').find('nav', cls='pager').find('a', cls='next')
        # ... landing on the goal's own row of that region's panel there (Phase 12)
        self.assertEqual((scheme['href'], scheme.find('span', cls='pager-n').text()), ('../../map/#arc-row-synb-rg-scheme', 'Open the map'))

    def test_the_region_pages_carry_what_the_content_says(self):
        html_ = self.html(RG_URLS[0])
        doc = self.doc(RG_URLS[0])
        self.assertEqual(doc.find('meta', attrs={'name': 'description'})['content'],
                         'Synthetic Reach: 3 trip reports, 2025 to 2026 (backcountry skiing, climbing and hiking), with a map of the region '
                         'and the full GPX track of each.')
        self.assertEqual([m['content'] for m in doc.find_all('meta', attrs={'property': 'og:image'})], [U + 'trips/synb-rg-story/photos/01.webp'])
        self.assertEqual([li['data-slug'] for li in doc.find_all('li', cls='tcard')], ['synb-rg-story', 'synb-rg-words'])
        self.assertEqual([a['data-key'] for a in doc.by_id('all-reports').find_all('a', cls='rtab-r')],
                         ['synb-rg-story', 'synb-rg-words', 'synb-rg-lap', 'synb-rg-goal'])
        self.assertIn('href="../../trips/?region=synthetic-reach&amp;writeup=1">All 2 write-ups in Trips', html_)
        self.assertEqual([a['href'] for a in doc.find('nav', cls='reg-others').find_all('a')], ['../../regions/synthetic-shore/', '../../map/'])
        shore = self.doc(RG_URLS[1])
        self.assertIsNone(shore.find('section', cls='reg-feat'))                  # two bare reports: no Featured row
        self.assertIsNone(shore.find('div', cls='arc-filt'))                      # one activity: no filter row
        # one of its reports has no track: the sentence promises the map and no GPX file
        self.assertEqual(shore.find('meta', attrs={'name': 'description'})['content'],
                         'Synthetic Shore: 2 trip reports, 2024 (mountain biking), with a map of the region.')

    def test_a_region_page_lists_what_the_content_says_and_the_map_page_what_its_map_names(self):
        # contract-phase5.md section 1 (REVISED in round 2), on a built site whose Shore map is out of step with the
        # content (RG_MAPS): the page lists the reports filed under the region, the report without a track included
        # and the report filed elsewhere left out; the Map page's panel keeps the trips its map was drawn with
        shore = self.doc(RG_URLS[1])
        filed = ['synb-rg-shore', 'synb-rg-shore-walk']
        self.assertEqual([li['data-key'] for li in shore.by_id('arc-rows-synthetic-shore').find_all('li', cls='arc-row')], filed)
        self.assertEqual([a['data-key'] for a in shore.by_id('all-reports').find_all('a', cls='rtab-r')], filed)
        self.assertIn('2\xa0REPORTS', self.html(RG_URLS[1]).split('<p class="reg-stats">', 1)[1].split('</p>', 1)[0])
        self.assertNotIn('trips/synb-rg-dunes/"', self.html(RG_URLS[1]).split('<div class="arc-side">', 1)[1])      # in no list of the page
        panel = self.doc('map/').by_id('region-synthetic-shore')
        self.assertEqual([li['data-key'] for li in panel.find_all('li', cls='arc-row')], RG_MAPS[RG_COAST])
        self.assertEqual([(a['href'], a.text()) for a in panel.find_all('a', cls='arc-reg-a')],
                         [('../regions/synthetic-shore/', 'All Synthetic Shore reports')])
        # the count the Trips page gives the region beside its link is the page's count
        browse = {a['href']: a.text() for a in self.doc('trips/').find('nav', cls='trx-browse').find_all('a')}
        self.assertEqual(browse['../regions/synthetic-shore/'], 'Synthetic Shore, 2 reports')
        self.assertEqual(browse['../regions/synthetic-reach/'], 'Synthetic Reach, 3 reports')
        self.assertEqual(len([a for a in self.doc(RG_URLS[0]).by_id('all-reports').find_all('a', cls='rtab-r') if a['data-kind'] != 'planned']), 3)
        # each report's breadcrumb leads to the page that lists it: the one without a track to the Shore's, the one the
        # Shore map still draws to its own region's place on the Map page
        walk = self.doc('trips/synb-rg-shore-walk/').find('nav', cls='crumbs')
        self.assertEqual([a['href'] for a in walk.find_all('a')][-1], '../../regions/synthetic-shore/')
        dunes = self.doc('trips/synb-rg-dunes/').find('nav', cls='crumbs')
        self.assertEqual([a['href'] for a in dunes.find_all('a')][-1], '../../map/#region-synthetic-dunes')
        self.assertFalse(os.path.exists(self.path('trips/synb-rg-shore-walk/map')))                # no track: no map page

    def test_every_cluster_marker_of_a_region_pages_map_has_a_row_for_each_of_its_trips(self):
        # base.js sends a click on a cluster marker to the first row of the list beside the map whose data-key is one of
        # the marker's data-keys (the list is the one whose data-map-target names the map). Every key has its row on the
        # built page, the goal's included, so no marker is dead
        doc = self.doc(RG_URLS[0])
        block = doc.by_id('arc-map-synthetic-reach')
        clusters = block.find_all('g', cls='mk-cluster')
        self.assertEqual([g['data-keys'].split() for g in clusters], RG_CLUSTERS[RG_RANGE] * 2)       # the desktop and the phone render
        lists = doc.find_all(attrs={'data-map-target': 'arc-map-synthetic-reach'})
        self.assertEqual([(n.tag, n['id']) for n in lists], [('ol', 'arc-rows-synthetic-reach')])
        rows = [n['data-key'] for n in lists[0].walk() if n['data-key']]
        self.assertEqual(rows, RG_MAPS[RG_RANGE])
        for g in clusters:
            self.assertEqual(g['aria-hidden'], 'true')
            for key in g['data-keys'].split():
                self.assertIn(key, rows)
        for pin in block.find_all('a', cls='mk-pin'):
            self.assertIn(pin['data-key'], rows)
        # the same fragment on the Map page, whose list is found the same way
        panel = self.doc('map/').by_id('region-synthetic-reach')
        there = [n['data-key'] for n in panel.find('ol', cls='arc-rows').walk() if n['data-key']]
        self.assertEqual(panel.find('ol', cls='arc-rows')['data-map-target'], 'arc-map-synthetic-reach')
        for g in panel.find_all('g', cls='mk-cluster'):
            for key in g['data-keys'].split():
                self.assertIn(key, there)

    def test_the_legend_beside_a_region_pages_map_is_the_map_pages_legend_for_that_map(self):
        # round 3: the legend is the key to the map, so it is made from the trips the map draws (RG_MAPS), as the Map
        # page's panel for the same map makes it, and not from the page's list. The Shore map still draws the hike that
        # is filed under the Dunes; both reports on the Shore's list are rides, one of them without a track
        def legend(html_):
            # since Phase 12 the legend is in the map column, under the caption, with the phone's compact key row after it
            start = html_.index('<div class="arc-legend')
            return html_[start:html_.index('<div class="arc-side">', start)]

        def words(html_):
            return [li.elements()[-1].text() for li in Doc(legend(html_)).find('div', cls='arc-legend').find_all('li')]

        archive_page = self.html('map/')
        for name, url in zip(RG_PAGES, RG_URLS):
            with self.subTest(region=name):
                panel = archive_page[archive_page.index('<div class="arc-panel" id="region-%s">' % RG_SLUG[name]):]
                self.assertTrue(legend(self.html(url)).startswith('<div class="arc-legend keyrow--d"><p class="t-label">Legend</p>'))
                self.assertEqual(legend(self.html(url)), legend(panel))
        self.assertEqual(words(self.html(RG_URLS[0])), ['Backcountry Skiing', 'Climbing', 'Hiking', 'Planned route'])
        self.assertEqual(words(self.html(RG_URLS[1])), ['Hiking', 'Mountain Biking'])
        listed = [li['data-key'] for li in self.doc(RG_URLS[1]).by_id('arc-rows-synthetic-shore').find_all('li', cls='arc-row')]
        self.assertEqual(listed, ['synb-rg-shore', 'synb-rg-shore-walk'])               # no hike among them
        self.assertEqual(self.doc(RG_URLS[1]).by_id('all-reports').find_all('a', attrs={'data-act': 'hike'}), [])

    def test_only_region_builds_the_region_pages_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_region_site(tmp)
            out, pages = run_build(tmp, only={'region'})
            self.assertEqual([p.url for p in pages], RG_URLS)
            self.assertEqual([f for f in files_of(out) if f.endswith('.html')], ['regions/synthetic-reach/index.html', 'regions/synthetic-shore/index.html'])
            for url in RG_URLS:
                # the same page as in the whole build: a region page needs no other module to have run
                self.assertEqual(read(os.path.join(out, page_path(url))), self.html(url))
            self.assertEqual(read(os.path.join(out, 'sitemap.xml')), build.sitemap(pages))
            self.assertEqual(re.findall(r'<loc>([^<]+)</loc>', read(os.path.join(out, 'sitemap.xml'))), [U + u for u in RG_URLS])
            # and a partial build that leaves the module out writes none
            out, pages = run_build(tmp, only={'archive', 'home'})
            self.assertEqual(sorted(p.url for p in pages), sorted(['', 'map/'] + ['map/%s/' % RG_SLUG[n] for n in (RG_RANGE, RG_COAST, RG_PLANS)]))
            self.assertFalse(os.path.exists(os.path.join(out, 'regions')))
            # the Map page of that build still links to the pages a full build writes (region_page_href asks the site, not the build)
            self.assertIn('href="../regions/synthetic-reach/"', read(os.path.join(out, 'map', 'index.html')))

    def test_a_build_without_region_maps_writes_no_region_page(self):
        # the first fixture of this file: its site meta names no region map
        fx = built()
        self.assertEqual([p.url for p in fx.pages if p.url.startswith('regions')], [])
        self.assertFalse(os.path.exists(os.path.join(fx.out, 'regions')))
        self.assertNotIn('regions/', read(os.path.join(fx.out, 'sitemap.xml')))
        for rel in files_of(fx.out):
            if rel.endswith('.html'):
                self.assertNotIn('regions/', read(os.path.join(fx.out, rel)), rel)


# ================================================================ a region map whose reports are all gone (round 3)

RG_WRAITH, RG_WRAITH_SLUG = 'Synthetic Wraith', 'synthetic-wraith'
RG_WRAITH_MAP = ['synb-rg-wraith', 'synb-rg-vanished']        # what the map was drawn with: a report that is a draft now, one that is gone


class RetitleLabelTests(BuiltCase):
    """gap8-04 (Phase 9) on the built site with region maps: the fixture's fragments say 'Synthetic pin' and 'Synthetic
    cluster' where render.py would have written the titles; the build writes the trips' titles there now, so a trip
    retitled since the render shows its new name on every page that shows the map, without a site render."""

    def setUp(self):
        self.fx = built_regions()
        self.out = self.fx.out
        self._docs = {}

    def test_pins_and_clusters_carry_the_titles_of_the_trips(self):
        html_ = self.html(RG_URLS[0])
        # (data-act and data-acts: each pin's and cluster's activities, which the build adds since Phase 12)
        self.assertIn('data-key="synb-rg-lap" data-act="ski" aria-label="Synthetic Reach Lap"><title>Synthetic Reach Lap</title>', html_)
        self.assertIn('data-keys="synb-rg-words synb-rg-lap" data-acts="climb ski"><title>Synthetic Reach Words; Synthetic Reach Lap</title>', html_)
        self.assertNotIn('Synthetic pin', html_)
        self.assertNotIn('Synthetic cluster', html_)
        self.assertNotIn('Synthetic pin', self.html('map/'))


class DraftedPinTests(unittest.TestCase):
    """gap7-03 (Phase 8, decision 12.8) on a built site: a report with a pin of its own on a region map is made a draft,
    and nothing is rendered. The build leaves its pin and its line out of the maps on the home page, the Map page and the
    region page, so the site passes the checks build.py --check runs (it failed with BROKEN links to trips/<slug>/
    before); the cluster it was merged into is as rendered; and the validator's warning says how to redraw the maps."""

    def test_a_drafted_trip_with_a_pin_of_its_own_passes_the_check_without_a_render(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = tmp.name
        write_region_site(root)
        index = os.path.join(root, 'content', 'trips', 'synb-rg-lap', 'index.md')
        write(index, read(index).replace('\n---\n', '\ndraft: true\n---\n', 1))
        with mock.patch.object(home_page, 'HOME_REGIONS', (RG_RANGE,)):
            out, _pages = run_build(root)
        trips_dir = os.path.join(root, 'content', 'trips')
        self.assertEqual(sitecheck.check(out, trips_dir), [])
        self.assertFalse(os.path.exists(os.path.join(out, 'trips', 'synb-rg-lap')))
        for page in ('index.html', 'map/index.html', 'regions/synthetic-reach/index.html'):
            with self.subTest(page=page):
                html_ = read(os.path.join(out, page))
                self.assertIn('data-key="synb-rg-words"', html_)                 # the map is there, its other pins too
                self.assertNotIn('data-key="synb-rg-lap"', html_)
                self.assertNotIn('trips/synb-rg-lap/', html_)
                self.assertIn('data-keys="synb-rg-words synb-rg-lap"', html_)      # the cluster as rendered
        with redirected(root):
            checks = importlib.import_module('checks')
            lines = [checks.line(f) for f in checks.run()]
        warned = [ln for ln in lines if 'synb-rg-lap' in ln and 'still draw this trip' in ln]
        self.assertEqual(len(warned), 1, lines)
        self.assertIn('which is a draft: the build leaves its own pin and line out of them', warned[0])
        self.assertIn('render.py --site when online', warned[0])


def write_wraith_site(root):
    """The site with region maps (write_region_site) and one region map more, for Synthetic Wraith, as tools/render.py
    left it when the region had two reports. Since then one has been made a draft (it is still in content/, and never
    in the output) and the other removed. The map, its entry in rendered/site/meta.json and the region's name in
    'regions' and 'all_regions' stay as they are until the next render: no trip of the site is on that map or filed
    under that region."""
    write_region_site(root)
    draft = add_trip(root, 'synb-rg-wraith', title='Synthetic Wraith Walk', activity='hike', date='2024-02-02', region=RG_WRAITH, draft=True,
                     track=True)
    write(os.path.join(draft, 'track.gpx'), gpx('Synthetic wraith walk'))
    site = os.path.join(root, 'rendered', 'site')
    meta = json.loads(read(os.path.join(site, 'meta.json')))
    meta['regions'].append(RG_WRAITH)
    meta['all_regions'].append(RG_WRAITH)
    pins = ''.join('<a class="mk-pin" href="@@ROOT@@trips/%s/" data-key="%s" aria-label="Synthetic pin"><title>Synthetic pin</title>'
                   '<circle class="mk-hit" cx="9" cy="9" r="12" style="fill: transparent"/></a>' % (s, s) for s in RG_WRAITH_MAP)
    for size, (w, h) in (('desktop', (718, 620)), ('phone', (390, 480))):
        key = 'region-%s-%s' % (RG_WRAITH_SLUG, size)
        meta['maps'][key] = {'w': w, 'h': h, 'png': key + '.webp', 'base': key + '.base.svg', 'region': RG_WRAITH, 'trips': list(RG_WRAITH_MAP)}
        write(os.path.join(site, key + '.svg.html'), '<svg width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>' % (w, h, w, h, pins))
        write(os.path.join(site, key + '.webp'), 'real ' + key)
        write(os.path.join(site, key + '.base.svg'), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d"/>' % (w, h))
    write(os.path.join(site, 'meta.json'), json.dumps(meta))


def also_items_c7ed3ee(site):
    """sitegen.pages.home.also_items as it was at commit c7ed3ee (the body of fb425ab, Phase 4), copied line for line:
    every mapped region that is not one of the home page's two gets an item, with or without a panel on the Map page."""
    is_report, slug, HOME_REGIONS, HERE = home_page.is_report, home_page.slug, home_page.HOME_REGIONS, home_page.HERE
    esc, link = core.esc, core.link
    mapped = set(core.site_meta().get('regions') or [])
    counts = {}
    for t in site['published']:
        r = t.get('region')
        if r and is_report(t) and t['kind'] != 'series':
            counts[r] = counts.get(r, 0) + 1
    item = '<li><a href="%s"><span class="hom-also-w">%s</span>%s</a></li>'
    out = []
    for r in sorted((r for r in mapped if r not in HOME_REGIONS), key=lambda r: (-counts.get(r, 0), r)):
        k = counts.get(r, 0)
        out.append(item % (core.region_map_href(HERE, r) or link(HERE, 'map/#region-' + slug(r)), esc(r),
                           ('<span class="hom-also-c">%d</span>' % k) if k else ''))
    unmapped = [r for r in counts if r not in mapped and r not in HOME_REGIONS]
    if unmapped:
        more = '%d more region%s' % (len(unmapped), '' if len(unmapped) == 1 else 's')
        out.append(item % (link(HERE, 'map/#other-places'), esc(more), ''))
    out += [item % (link(HERE, t['url']), esc(t['title']), '<span class="hom-also-c">SERIES</span>')
            for t in site['published'] if t['kind'] == 'series']
    return out


class WraithRegionSiteTests(unittest.TestCase):
    """Round 3 of the region pages, on a built site: the home page's Also row names a mapped region only while the Map
    page has a panel for it. With the map of a region whose reports are all gone still in rendered/site/, the site
    passes the checks `build.py --check` runs; with home.also_items as it was at commit c7ed3ee the same site has one
    broken anchor, the Also row's link to a panel the Map page does not write.

    The home page draws the maps of home.HOME_REGIONS only, and has an Also row only when it draws one: the builds here
    run with Synthetic Reach as the home page's one region."""

    WRAITH_LINK = 'map/#region-' + RG_WRAITH_SLUG

    def build(self, writer=write_wraith_site, also_items=None):
        """A build of the site in a temp root of its own: (the output folder, its content/trips folder)."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        writer(tmp.name)
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(home_page, 'HOME_REGIONS', (RG_RANGE,)))
            if also_items is not None:
                stack.enter_context(mock.patch.object(home_page, 'also_items', also_items))
            out, _pages = run_build(tmp.name)
        return out, os.path.join(tmp.name, 'content', 'trips')

    def also(self, out):
        row = Doc(read(os.path.join(out, 'index.html'))).find('div', cls='hom-also')
        self.assertIsNotNone(row, 'the home page has no Also row')
        return [(a['href'], a.find('span', cls='hom-also-w').text(), a.find('span', cls='hom-also-c').text() if a.find('span', cls='hom-also-c') else None)
                for a in row.find_all('a')]

    def test_the_site_passes_the_site_check(self):
        out, trips_dir = self.build()
        self.assertEqual(sitecheck.check(out, trips_dir), [])
        # the state the check passes in: the map is in the site meta and published, and nothing of the site is on it
        meta = json.loads(read(os.path.join(os.path.dirname(os.path.dirname(trips_dir)), 'rendered', 'site', 'meta.json')))
        self.assertIn(RG_WRAITH, meta['regions'])
        self.assertEqual(meta['maps']['region-%s-desktop' % RG_WRAITH_SLUG]['trips'], RG_WRAITH_MAP)
        self.assertTrue(os.path.isfile(os.path.join(out, 'assets', 'maps', 'region-%s-desktop.webp' % RG_WRAITH_SLUG)))
        self.assertTrue(os.path.isdir(os.path.join(trips_dir, 'synb-rg-wraith')))                # the draft is still content
        for slug in RG_WRAITH_MAP:
            self.assertFalse(os.path.exists(os.path.join(out, 'trips', slug)), slug)
        # no page names the region, links to it or holds an anchor for it
        ids = {n['id'] for n in Doc(read(os.path.join(out, 'map', 'index.html'))).root.walk() if n['id']}
        self.assertNotIn('region-' + RG_WRAITH_SLUG, ids)
        self.assertFalse(os.path.exists(os.path.join(out, 'regions', RG_WRAITH_SLUG)))
        for rel in files_of(out):
            if rel.endswith('.html'):
                text = read(os.path.join(out, rel))
                self.assertNotIn(RG_WRAITH_SLUG, text, rel)
                self.assertNotIn(RG_WRAITH, text, rel)
        # the Also row: the Shore to its own page with its two reports, the Schemes (a planned route only) to their panel
        # on the Map page without a count, the one region without a region map, the journal
        self.assertEqual(self.also(out), [('regions/synthetic-shore/', RG_COAST, '2'), ('map/#region-synthetic-schemes', RG_PLANS, None),
                                          ('map/#other-places', '1 more region', None), ('trips/synb-rg-journal/', 'Synthetic Reach Journal', 'SERIES')])
        self.assertIn('region-synthetic-schemes', ids)
        self.assertIn('other-places', ids)

    def test_at_commit_c7ed3ee_the_same_site_had_a_broken_anchor(self):
        out, trips_dir = self.build(also_items=also_items_c7ed3ee)
        self.assertEqual(sitecheck.check(out, trips_dir), ['BROKEN ANCHOR index.html -> ' + self.WRAITH_LINK])
        self.assertEqual(self.also(out), [('map/#region-synthetic-shore', RG_COAST, '2'), ('map/#region-synthetic-schemes', RG_PLANS, None),
                                          (self.WRAITH_LINK, RG_WRAITH, None),
                                          ('map/#other-places', '1 more region', None), ('trips/synb-rg-journal/', 'Synthetic Reach Journal', 'SERIES')])
        # the Map page of that build is the Map page of today's: it never had the panel
        now, _trips = self.build()
        self.assertEqual(read(os.path.join(out, 'map', 'index.html')), read(os.path.join(now, 'map', 'index.html')))
        # the two builds differ in the home page alone, and there in that item and in the address of the Shore
        self.assertEqual(files_of(out), files_of(now))
        self.assertEqual([rel for rel in files_of(out) if read_bytes(os.path.join(out, rel)) != read_bytes(os.path.join(now, rel))], ['index.html'])
        item = '<li><a href="%s"><span class="hom-also-w">%s</span></a></li>' % (self.WRAITH_LINK, RG_WRAITH)
        before = read(os.path.join(out, 'index.html'))
        self.assertEqual(before.count(item), 1)
        self.assertEqual(before.replace(item, '').replace('href="map/#region-synthetic-shore"', 'href="regions/synthetic-shore/"'),
                         read(os.path.join(now, 'index.html')))

    def test_the_old_row_and_the_new_agree_while_every_region_map_has_a_panel(self):
        # the site with region maps as it is (no map without a trip): both rows land, and differ in the Shore's address
        old, trips_dir = self.build(writer=write_region_site, also_items=also_items_c7ed3ee)
        self.assertEqual(sitecheck.check(old, trips_dir), [])
        new, trips_dir = self.build(writer=write_region_site)
        self.assertEqual(sitecheck.check(new, trips_dir), [])
        self.assertEqual(read(os.path.join(old, 'index.html')).replace('href="map/#region-synthetic-shore"', 'href="regions/synthetic-shore/"'),
                         read(os.path.join(new, 'index.html')))
        self.assertEqual(self.also(new), [('regions/synthetic-shore/', RG_COAST, '2'), ('map/#region-synthetic-schemes', RG_PLANS, None),
                                          ('map/#other-places', '1 more region', None), ('trips/synb-rg-journal/', 'Synthetic Reach Journal', 'SERIES')])


class CombinedGpxTests(unittest.TestCase):
    """Contract 10.1: the combined file of a multi-day trip is written exactly when a day has a track file, the condition
    under which its page offers "Download all GPX" (multiday.has_gpx), and it holds every <trk ...>...</trk> block of
    the day files, unchanged and in day order. So the page never offers a file the build did not write, whatever a
    day's GPX looks like."""

    ROUTE = ('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="synthetic planner" xmlns="http://www.topografix.com/GPX/1/1">\n'
             '<rte><name>Synthetic route day</name><rtept lat="39.1" lon="-120.1"/><rtept lat="39.2" lon="-120.2"/></rte>\n</gpx>\n')

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def build_days(self, name, *day_files):
        """A site with one multi-day trip whose days hold these GPX texts (None: a day without a track file), built;
        -> ("Download all GPX" is offered, the combined file's text or None)."""
        root = os.path.join(self.tmp, name)
        write_assets(root)
        write_home(root, [])
        days = [{'title': 'Synthetic Day %d' % (i + 1), 'date': '2026-03-%02d' % (10 + i), 'track': text is not None}
                for i, text in enumerate(day_files)]
        folder = add_trip(root, 'synb-days', title='Synthetic Days', activity='hike', kind='multi-day', region=REGION, days=days)
        for i, text in enumerate(day_files):
            if text is not None:
                write(os.path.join(folder, 'days', '%02d.gpx' % (i + 1)), text)
        out, _pages = run_build(root)
        page = read(os.path.join(out, 'trips', 'synb-days', 'index.html'))
        offered = 'Download all GPX' in page
        self.assertEqual(offered, 'href="synb-days.gpx"' in page)
        combined = os.path.join(out, 'trips', 'synb-days', 'synb-days.gpx')
        return offered, (read(combined) if os.path.isfile(combined) else None)

    def test_plain_trk_blocks(self):
        offered, text = self.build_days('plain', gpx('Synthetic one'), gpx('Synthetic two'))
        self.assertTrue(offered)
        self.assertEqual([text.count(trk('Synthetic one')), text.count(trk('Synthetic two')), trk_tags(text)], [1, 1, 2])

    def test_a_trk_tag_with_attributes_counts(self):
        one = trk('Synthetic one').replace('<trk>', '<trk xmlns:syn="urn:synthetic">')
        two = trk('Synthetic two').replace('<trk>', '<trk\n  syn="2">')
        offered, text = self.build_days('attribute', gpx('Synthetic one').replace(trk('Synthetic one'), one),
                                        gpx('Synthetic two').replace(trk('Synthetic two'), two))
        self.assertTrue(offered)
        self.assertIsNotNone(text, '"Download all GPX" is offered but trips/synb-days/synb-days.gpx was not written')
        self.assertEqual([text.count(one), text.count(two), trk_tags(text)], [1, 1, 2])
        self.assertLess(text.index(one), text.index(two))

    def test_a_day_file_without_a_track_block_adds_nothing_and_the_download_still_has_its_file(self):
        offered, text = self.build_days('route', self.ROUTE, self.ROUTE)
        self.assertTrue(offered)                      # both days have a track file
        self.assertIsNotNone(text, '"Download all GPX" is offered but trips/synb-days/synb-days.gpx was not written')
        self.assertEqual(trk_tags(text), 0)
        self.assertNotIn('<trkpt', text)
        self.assertNotIn('<rte', text)
        self.assertEqual(ET.fromstring(text.encode('utf-8')).tag, '{http://www.topografix.com/GPX/1/1}gpx')
        offered, text = self.build_days('mixed', self.ROUTE, gpx('Synthetic two'))
        self.assertTrue(offered)
        self.assertEqual([text.count(trk('Synthetic two')), trk_tags(text)], [1, 1])

    def test_every_block_of_every_day_in_day_order(self):
        two_tracks = gpx('Synthetic morning').replace('\n</gpx>', '\n%s\n</gpx>' % trk('Synthetic afternoon'))
        offered, text = self.build_days('order', two_tracks, None, gpx('Synthetic third day'))
        self.assertTrue(offered)
        blocks = [trk('Synthetic morning'), trk('Synthetic afternoon'), trk('Synthetic third day')]
        self.assertEqual([text.count(b) for b in blocks], [1, 1, 1])
        at = [text.index(b) for b in blocks]
        self.assertEqual(at, sorted(at))
        self.assertEqual(trk_tags(text), 3)

    def test_no_day_track_no_file_and_no_download(self):
        self.assertEqual(self.build_days('none', None, None), (False, None))

    # ------------------------------------------------------------ prefixes a day file declares on its <gpx> root (10.3)

    HEADER = ('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="Eric Sichak trip reports" '
              'xmlns="http://www.topografix.com/GPX/1/1"%s>\n<metadata><name>Synthetic Days</name></metadata>\n')
    TPX = 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'

    @staticmethod
    def ext_trk(name, prefix):
        """A <trk> whose points carry a device extension under a prefix that only the file's root declares."""
        return ('<trk><name>%s</name><trkseg>\n'
                '  <trkpt lat="39.1000" lon="-120.1000"><ele>2000.5</ele><extensions><%s:TrackPointExtension><%s:hr>121</%s:hr>'
                '</%s:TrackPointExtension></extensions></trkpt>\n'
                '  <trkpt lat="39.2000" lon="-120.2000"><ele>2100.0</ele><extensions><%s:TrackPointExtension><%s:hr>133</%s:hr>'
                '</%s:TrackPointExtension></extensions></trkpt>\n'
                '</trkseg></trk>' % ((name,) + (prefix,) * 8))

    def ext_gpx(self, name, prefix, uri=None, quote='"', more=''):
        """A day file as a device writes it: the prefix declared on <gpx ...>, used inside each trkpt."""
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<gpx version="1.1" creator="synthetic device" xmlns="http://www.topografix.com/GPX/1/1" xmlns:%s=%s%s%s%s>\n'
                '<metadata><name>%s</name></metadata>\n%s\n</gpx>\n'
                % (prefix, quote, uri or self.TPX, quote, more, name, self.ext_trk(name, prefix)))

    def test_without_prefixes_the_header_is_byte_for_byte_the_old_one(self):
        offered, text = self.build_days('plain-header', gpx('Synthetic one'), gpx('Synthetic two'))
        self.assertTrue(offered)
        self.assertEqual(text, self.HEADER % '' + trk('Synthetic one') + '\n' + trk('Synthetic two') + '\n</gpx>\n')
        self.assertNotIn('xmlns:', text)
        self.assertEqual(text.count('xmlns='), 1)

    def test_a_prefix_both_day_files_declare_is_declared_once_and_the_file_parses(self):
        one, two = self.ext_gpx('Synthetic one', 'ns3'), self.ext_gpx('Synthetic two', 'ns3')
        ET.fromstring(one.encode('utf-8'))                                 # each day file is well-formed by itself
        with self.assertRaises(ET.ParseError):                             # ... and its block is not, without the declaration
            ET.fromstring(('<gpx xmlns="http://www.topografix.com/GPX/1/1">%s</gpx>' % self.ext_trk('Synthetic one', 'ns3')).encode('utf-8'))
        offered, text = self.build_days('ns3', one, two)
        self.assertTrue(offered)
        self.assertEqual(text, self.HEADER % (' xmlns:ns3="%s"' % self.TPX) + self.ext_trk('Synthetic one', 'ns3') + '\n'
                         + self.ext_trk('Synthetic two', 'ns3') + '\n</gpx>\n')
        self.assertEqual(text.count('xmlns:ns3='), 1)
        root = ET.fromstring(text.encode('utf-8'))
        ns = '{http://www.topografix.com/GPX/1/1}'
        self.assertEqual(root.tag, ns + 'gpx')
        self.assertEqual([t.findtext(ns + 'name') for t in root.findall(ns + 'trk')], ['Synthetic one', 'Synthetic two'])
        self.assertEqual([e.text for e in root.iter('{%s}hr' % self.TPX)], ['121', '133', '121', '133'])
        # and the site check, which reads the combined file as XML, finds nothing
        self.assertEqual(sitecheck.check(os.path.join(self.tmp, 'ns3', '_site'), os.path.join(self.tmp, 'ns3', 'content', 'trips')), [])

    def test_two_day_files_with_different_prefixes(self):
        other = 'urn:synthetic:power'
        offered, text = self.build_days('two-prefixes', self.ext_gpx('Synthetic one', 'ns3'), self.ext_gpx('Synthetic two', 'gpxpx', other))
        self.assertTrue(offered)
        # every prefix once, sorted by prefix, whatever the day order
        self.assertEqual(text.split('\n')[1], '<gpx version="1.1" creator="Eric Sichak trip reports" xmlns="http://www.topografix.com/GPX/1/1" '
                                               'xmlns:gpxpx="urn:synthetic:power" xmlns:ns3="%s">' % self.TPX)
        root = ET.fromstring(text.encode('utf-8'))
        self.assertEqual([e.text for e in root.iter('{%s}hr' % self.TPX)], ['121', '133'])
        self.assertEqual([e.text for e in root.iter('{%s}hr' % other)], ['121', '133'])
        self.assertEqual([text.count(self.ext_trk('Synthetic one', 'ns3')), text.count(self.ext_trk('Synthetic two', 'gpxpx'))], [1, 1])
        self.assertEqual(sitecheck.check(os.path.join(self.tmp, 'two-prefixes', '_site'),
                                         os.path.join(self.tmp, 'two-prefixes', 'content', 'trips')), [])

    def test_a_prefix_of_a_day_file_that_adds_no_track_is_not_copied(self):
        route = self.ROUTE.replace('xmlns="http://www.topografix.com/GPX/1/1">', 'xmlns="http://www.topografix.com/GPX/1/1" xmlns:plan="urn:synthetic:planner">')
        self.assertIn('xmlns:plan=', route)
        offered, text = self.build_days('route-prefix', route, self.ext_gpx('Synthetic two', 'ns3'), gpx('Synthetic three'))
        self.assertTrue(offered)
        self.assertNotIn('plan', text)
        self.assertEqual(text.split('\n')[1], '<gpx version="1.1" creator="Eric Sichak trip reports" xmlns="http://www.topografix.com/GPX/1/1" '
                                               'xmlns:ns3="%s">' % self.TPX)
        self.assertEqual(trk_tags(text), 2)
        ET.fromstring(text.encode('utf-8'))
        # only route days, each with a prefix: nothing is declared, and the header is the plain one
        offered, text = self.build_days('route-prefix-only', route, route)
        self.assertEqual(text, self.HEADER % '' + '\n</gpx>\n')

    def test_a_declaration_is_copied_as_the_day_file_wrote_it(self):
        # single quotes, a line break between the attributes, and other attributes of the root (which are not copied)
        more = '\n     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 gpx.xsd"'
        offered, text = self.build_days('quotes', self.ext_gpx('Synthetic one', 'ns3', quote="'", more=more))
        self.assertTrue(offered)
        self.assertEqual(text.split('\n')[1], '<gpx version="1.1" creator="Eric Sichak trip reports" xmlns="http://www.topografix.com/GPX/1/1" '
                                               'xmlns:ns3=\'%s\' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' % self.TPX)
        self.assertNotIn('schemaLocation', text)
        self.assertNotIn('synthetic device', text)
        ET.fromstring(text.encode('utf-8'))

    def test_the_first_declaration_of_a_prefix_wins(self):
        # contract 10.3: 'first declaration wins': one declaration of ns3, the first day's
        offered, text = self.build_days('same-prefix', self.ext_gpx('Synthetic one', 'ns3'), self.ext_gpx('Synthetic two', 'ns3', 'urn:synthetic:other'))
        self.assertTrue(offered)
        self.assertEqual(text.count('xmlns:ns3='), 1)
        self.assertIn(' xmlns:ns3="%s">' % self.TPX, text)
        self.assertNotIn('urn:synthetic:other', text)
        ET.fromstring(text.encode('utf-8'))


# ================================================================ iCloud conflict copies (contract 5.5)

class ConflictCopyBuildTests(BuiltCase):

    def test_the_fixture_has_conflict_copies_beside_the_real_files(self):
        story = os.path.join(self.fx.root, 'rendered', 'trips', 'synb-story')
        site = os.path.join(self.fx.root, 'rendered', 'site')
        for folder, names in ((story, RENDERED_STORY + RENDERED_STORY_COPIES + ['meta.json', 'meta 2.json', 'tile 2.svg.html']),
                              (site, RENDERED_SITE + RENDERED_SITE_COPIES + ['meta.json', 'meta 3.json'])):
            for name in names:
                self.assertTrue(os.path.isfile(os.path.join(folder, name)), name)
        for name in RENDERED_STORY_COPIES + RENDERED_SITE_COPIES + ['meta 2.json', 'meta 3.json', 'tile 2.svg.html', 'synb-story 2']:
            self.assertTrue(build.conflict_copy(name), name)
        for name in RENDERED_STORY + RENDERED_SITE:
            self.assertFalse(build.conflict_copy(name), name)

    def test_the_trips_map_folder_holds_the_real_files_only(self):
        self.assertEqual([f for f in files_of(self.path('trips/synb-story/map')) if f != 'index.html'], sorted(RENDERED_STORY))
        for name in RENDERED_STORY:
            self.assertEqual(read(self.path('trips/synb-story/map/' + name)), 'real ' + name)

    def test_the_site_maps_folder_holds_the_real_files_only(self):
        self.assertEqual(files_of(self.path('assets/maps')), sorted(RENDERED_SITE))
        for name in RENDERED_SITE:
            self.assertEqual(read(self.path('assets/maps/' + name)), 'real ' + name)

    def test_no_file_or_folder_of_the_output_has_a_conflict_copy_name(self):
        for dirpath, dirs, names in os.walk(self.out):
            for name in dirs + names:
                with self.subTest(name=os.path.relpath(os.path.join(dirpath, name), self.out)):
                    self.assertIsNone(CONFLICT_NAME.search(name))
                    self.assertFalse(build.conflict_copy(os.path.join(dirpath, name)))

    def test_no_bytes_of_a_conflict_copy_are_in_the_output(self):
        for rel in files_of(self.out):
            data = read_bytes(self.path(rel))
            self.assertNotIn(b'conflict copy', data, rel)
            self.assertNotIn(b'conflict folder', data, rel)
        self.assertFalse(os.path.exists(self.path('trips/synb-story 2')))
        self.assertEqual([f for f in files_of(self.out) if os.path.basename(f).startswith('meta')], [])

    def test_the_stale_copies_of_meta_json_are_not_what_the_pages_were_built_from(self):
        # the trip's 'meta 2.json' lists no map; the page shows the three its real meta.json lists
        text = self.html('trips/synb-story/')
        for name in ('map-wide.webp', 'map-col.webp', 'map-phone.webp'):
            self.assertIn('map/' + name, text)
        # the site's 'meta 3.json' knows no region; the real one does, so the report links its region on the map page
        crumbs = self.doc('trips/synb-story/').find('nav', cls='crumbs')
        self.assertIn('../../map/#region-synthetic-range', [a['href'] for a in crumbs.find_all('a')])
        self.assertIsNotNone(self.doc('map/').by_id('region-synthetic-range'))

    def test_the_trips_drawings_are_written_from_the_real_fragments(self):
        self.assertEqual([f for f in files_of(self.path('trips/synb-story')) if f.endswith('.svg') and '/' not in f],
                         ['g112.svg', 'g64.svg', 'tile.svg'])
        tile = read(self.path('trips/synb-story/tile.svg'))
        self.assertTrue(tile.startswith('<svg xmlns="http://www.w3.org/2000/svg" class="tile" viewBox="0 0 200 152">'))
        self.assertNotIn('{{route}}', tile)


class AssetConflictCopyTests(BuiltCase):
    """contract 10.3: an iCloud conflict copy under assets/ ('alpha 2.css', 'trips 2.js', 'favicon 2.svg') is left out of the
    CSS bundle, the JS bundle and the files copied to assets/, like the ones under rendered/."""

    def test_the_fixture_has_conflict_copies_under_assets(self):
        for rel in ASSET_COPIES:
            self.assertTrue(os.path.isfile(os.path.join(self.fx.root, 'assets', *rel.split('/'))), rel)
            self.assertIs(build.conflict_copy(rel), True, rel)
            self.assertIn('conflict copy', ASSET_COPIES[rel])
        for rel in ('css/base.css', 'css/pages/alpha.css', 'css/pages/beta.css', 'js/base.js', 'js/pages/alpha.js', 'js/pages/beta.js', 'favicon.svg'):
            self.assertIs(build.conflict_copy(rel), False, rel)

    def test_the_css_bundle_holds_no_rule_of_a_copy(self):
        css = read(self.path('assets/site.css'))
        for needle in ('synb-conflict', 'conflict copy', 'alpha 2', 'trips 2'):
            self.assertNotIn(needle, css)
        # the copy of alpha.css repeats its rules: each is in the bundle once
        for rule in ('.synb-alpha { margin: 0 auto; }', '.synb-alpha-two { padding: 0; }', '.synb-beta { display: none; }'):
            self.assertEqual(css.count(rule), 1, rule)
        with redirected(self.fx.root):
            self.assertEqual(css, build.css_bundle())

    def test_the_js_bundle_holds_no_statement_of_a_copy(self):
        js = read(self.path('assets/site.js'))
        for needle in ('conflictAlpha', 'conflictTrips', 'conflict copy', 'alpha 2.js', 'trips 2.js'):
            self.assertNotIn(needle, js)
        for statement in ('window.SYNB = {base: true};', 'window.SYNB.alpha = true;', 'window.SYNB.beta = true;'):
            self.assertEqual(js.count(statement), 1, statement)     # the page script runs once
        self.assertEqual(js, '\n'.join([BASE_JS, '/* alpha.js */\n' + ALPHA_JS, '/* beta.js */\n' + BETA_JS]))
        with redirected(self.fx.root):
            self.assertEqual(js, build.js_bundle())

    def test_the_assets_folder_holds_the_real_files_only(self):
        self.assertEqual([f for f in files_of(self.path('assets')) if not f.startswith('maps/')], ['favicon.svg', 'site.css', 'site.js'])
        self.assertEqual(read(self.path('assets/favicon.svg')), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"/>')
        for name in ('favicon 2.svg', 'site 3.webmanifest'):
            self.assertFalse(os.path.exists(self.path('assets/' + name)), name)

    def test_no_published_file_holds_the_bytes_of_an_asset_copy(self):
        for rel in files_of(self.out):
            self.assertNotIn(b'conflict copy', read_bytes(self.path(rel)), rel)
            self.assertNotIn(b'synb-conflict', read_bytes(self.path(rel)), rel)


# ================================================================ the card-size copy on the built site (contract 10.5)

PICTURE = re.compile(r'<picture class="cover-pic">(<source [^>]*>)(<img [^>]*>)</picture>')


# the explorer's list-view candidates (core.cover_img list_sizes): only on a cover that has a .th copy
LIST_ATTRS = re.compile(r' data-srcset-list="[^"]*" data-sizes-list="[^"]*"')


def unwrap(html_):
    """A page with every card cover's <picture class="cover-pic"> taken off (the <img> it holds, alone) and the explorer's
    list-view candidates, which name the .th copy, taken off its <img>."""
    return LIST_ATTRS.sub('', PICTURE.sub(lambda m: m.group(2), html_))


class CardCopyBuildTests(BuiltCase):
    """contract-phase4.md 10.5 on the built fixture site, whose one photo with a .th copy is synb-story's cover (it is
    also the home page's lead, the hiking page's featured report and the lead photo of its own page): the copy is
    offered to phones by the cards that show that cover, in a <source>, and by nothing else but the Trips explorer's
    list view (Phase 7: data-srcset-list on the card's <img>, which trips.js swaps in while the list view is on)."""

    TH = 'trips/synb-story/photos/01.th.webp'

    def sources(self):
        """[(page file, the <source> node)] of every <source> of the built site."""
        out = []
        for rel in self.html_files():
            out += [(rel, node) for node in Doc(read(self.path(rel))).find_all('source')]
        return out

    def test_the_fixture_has_one_th_copy_and_the_build_publishes_it(self):
        self.assertEqual([f for f in files_of(self.out) if '.th.' in f], [self.TH])
        self.assertEqual([f for f in files_of(self.fx.trips_dir) if '.th.' in f], ['synb-story/photos/01.th.webp'])

    def test_every_card_that_shows_the_cover_is_wrapped_and_its_source_names_the_file(self):
        found = self.sources()
        pages = sorted({rel for rel, _node in found})
        # the Trips explorer lists every report; a report page lists synb-story under 'More like this' when it is
        # related; the home page shows it as its lead (never wrapped), so not on its recent shelf
        self.assertIn('trips/index.html', pages)
        self.assertGreaterEqual(len(found), 2)
        for rel, node in found:
            with self.subTest(page=rel):
                pic = node.parent
                self.assertEqual((pic.tag, pic.classes, [n.tag for n in pic.elements()]), ('picture', ['cover-pic'], ['source', 'img']))
                self.assertEqual(sorted(node.attrs), ['media', 'sizes', 'srcset'])
                # the source declares the slot as 106 px (core.CARD_PHONE_SIZES: contract-phase5.md section 5), the
                # <img> behind it keeps a string that ends with the real 112 px
                self.assertEqual((node['media'], node['sizes']), (core.CARD_PHONE_MEDIA, core.CARD_PHONE_SIZES))
                self.assertEqual((node['media'], node['sizes']), ('(max-width: 559.98px)', '106px'))
                up = '../' * rel.count('/')
                base = up + 'trips/synb-story/photos/'
                self.assertEqual(node['srcset'], '%s01.th.webp 427w, %s01.sm.webp 800w, %s01.webp 1600w' % (base, base, base))
                for candidate in node['srcset'].split(', '):
                    target = os.path.normpath(os.path.join(os.path.dirname(rel), candidate.split(' ')[0])).replace(os.sep, '/')
                    self.assertTrue(os.path.isfile(self.path(target)), '%s names %s, which is not in the build' % (rel, candidate))
                img = pic.find('img')
                self.assertEqual((img['srcset'], img['loading']), ('%s01.sm.webp 800w, %s01.webp 1600w' % (base, base), 'lazy'))
                self.assertTrue(img['sizes'].endswith(', 112px'))
                self.assertTrue(img['sizes'].endswith(', ' + core.CARD_PHONE_SLOT))
                self.assertNotIn('106px', img['sizes'])
                card = pic.parent.parent
                self.assertEqual((pic.parent.classes, card.classes[:1], card['data-slug']), (['tcard-img'], ['tcard'], 'synb-story'))
        # every card of the report is wrapped: none of them is left with the bare <img>
        for rel in self.html_files():
            for card in Doc(read(self.path(rel))).find_all('li', attrs={'data-slug': 'synb-story'}):
                if 'tcard' in card.classes:
                    self.assertEqual(len(card.find_all('picture')), 1, rel)
        # ... and no other report's card is: none of them has the copy
        for rel in self.html_files():
            for pic in Doc(read(self.path(rel))).find_all('picture'):
                self.assertEqual(pic.parent.parent['data-slug'], 'synb-story', rel)

    def test_no_img_and_no_preload_of_the_site_names_a_th_file(self):
        seen = 0
        for rel in self.html_files():
            with self.subTest(page=rel):
                text = read(self.path(rel))
                doc = Doc(text)
                for img in doc.find_all('img'):
                    seen += 1
                    self.assertNotIn('.th.', (img['srcset'] or '') + ' ' + (img['src'] or ''))
                for ln in doc.find_all('link'):
                    self.assertNotIn('.th.', (ln['imagesrcset'] or '') + ' ' + (ln['href'] or ''))
                # whatever names the copy on this page is a <source>, or the explorer's list-view candidates
                listed = [img for img in doc.find_all('img') if img['data-srcset-list']]
                self.assertEqual(text.count('.th.'), len(doc.find_all('source')) + len(listed))
                self.assertEqual(bool(listed), rel == 'trips/index.html')
                for img in listed:
                    self.assertEqual(img['data-srcset-list'].count('.th.'), 1)
                self.assertNotRegex(text, r'<img\b[^>]*\s(?:src|srcset)="[^"]*\.th\.')
                self.assertNotRegex(text, r'imagesrcset="[^"]*\.th\.')
        self.assertGreater(seen, 10)
        for rel in files_of(self.out):
            if rel.endswith(('.json', '.xml', '.txt', '.css', '.js')):
                self.assertNotIn('.th.', read(self.path(rel)), rel)

    def test_a_lead_photo_and_its_preload_carry_the_same_candidates(self):
        # the home page's lead card and the report's own lead photo: the cover that has every copy, never wrapped, two
        # candidates, and the head's preload repeats the <img>
        cases = (('', 'hom-card--lead', 'trips/synb-story/photos/'), ('trips/synb-story/', 'rep-hero', '../../trips/synb-story/photos/'))
        for url, cls, base in cases:
            with self.subTest(page=url or '(home)'):
                doc = self.doc(url)
                holder = doc.find(cls=cls)
                self.assertIsNotNone(holder, '%s has no .%s' % (url or 'the home page', cls))
                self.assertEqual(holder.find_all('picture') + holder.find_all('source'), [])
                img = holder.find('img', cls='cover-img')
                self.assertEqual(img['srcset'], '%s01.sm.webp 800w, %s01.webp 1600w' % (base, base))
                self.assertEqual((img['fetchpriority'], img['loading']), ('high', None))
                links = [ln for ln in doc.find('head').find_all('link', attrs={'rel': 'preload', 'as': 'image'}) if '/photos/' in ln['href']]
                self.assertEqual([(ln['href'], ln['imagesrcset'], ln['imagesizes']) for ln in links], [(img['src'], img['srcset'], img['sizes'])])
                self.assertIn(core.PHONE_FULL, img['sizes'])

    def test_a_missing_th_file_is_a_broken_line_of_the_site_check(self):
        # the site check follows a srcset wherever it stands, a <source>'s included: take the copy out of a copy of the
        # build and every page whose card names it is reported
        self.assertEqual(sitecheck.links(self.out), [])
        named = sorted({rel for rel, _node in self.sources()})
        with tempfile.TemporaryDirectory() as tmp:
            damaged = os.path.join(tmp, 'site')
            shutil.copytree(self.out, damaged)
            os.remove(os.path.join(damaged, *self.TH.split('/')))
            lines = sitecheck.links(damaged)
            whole = sitecheck.check(damaged, self.fx.trips_dir)
        want = ['BROKEN %s -> %strips/synb-story/photos/01.th.webp' % (rel, '../' * rel.count('/')) for rel in named]
        self.assertEqual(sorted(set(lines)), sorted(want))
        self.assertEqual(len(lines), len(self.sources()))                       # one line per source
        self.assertEqual(whole, lines)                                          # and nothing else is wrong with that copy
        self.assertTrue(os.path.isfile(self.path(self.TH)))                     # the shared build is untouched

    def test_the_site_without_any_th_file_is_the_same_site_but_for_the_wrappers(self):
        # the same content with the one .th file removed, built: every page is the page of the fixture with its wrappers
        # taken off (so each card's <img> is byte for byte what it is without the copy), and every other text file is equal
        with tempfile.TemporaryDirectory() as tmp:
            write_site(tmp)
            os.remove(os.path.join(tmp, 'content', 'trips', 'synb-story', 'photos', '01.th.webp'))
            out, _pages = run_build(tmp)
            bare = {rel: read(os.path.join(out, *rel.split('/'))) for rel in files_of(out)
                    if rel.endswith(('.html', '.json', '.xml', '.txt', '.css', '.js', '.gpx', '.svg'))}
            names = files_of(out)
        self.assertEqual(sorted(names + [self.TH]), files_of(self.out))
        changed = []
        for rel, text in sorted(bare.items()):
            with self.subTest(file=rel):
                here = read(self.path(rel))
                self.assertNotIn('<picture', text)
                self.assertNotIn('.th.', text)
                self.assertEqual(unwrap(here), text)
                if here != text:
                    changed.append(rel)
        self.assertEqual(changed, sorted({rel for rel, _node in self.sources()} | {'trips/index.html'}))
        self.assertTrue(changed)

    def test_the_published_stylesheet_gives_the_wrapper_no_box(self):
        # 10.5: `picture.cover-pic { display: contents; }` in assets/css/base.css, so the card's frame sizes the <img>
        # as it did when the <img> was its child (the one read of the repository's own stylesheets in this class)
        css = build.css_bundle()
        self.assertRegex(css, r'picture\.cover-pic\s*\{\s*display:\s*contents;?\s*\}')


# ================================================================ renders left behind by a track that is gone (contract 10.3)

class StaleRenderBuildTests(BuiltCase):
    """contract 10.3: renders belong to a track. rendered/trips/synb-notrack/ and rendered/trips/synb-tour-none/ hold maps,
    charts, drawings and image files, and neither trip has a track (its own, or a day's): nothing of those folders is
    shown or published. The report with a track beside them (synb-story) has all of it."""

    def test_the_fixture_has_the_stale_folders(self):
        for slug in STALE:
            folder = os.path.join(self.fx.root, 'rendered', 'trips', slug)
            names = os.listdir(folder)
            for name in STALE_FILES + ['meta.json', 'tile.svg.html', 'g112.svg.html', 'g64.svg.html', 'map-wide.svg.html', 'profile-wide.svg.html']:
                self.assertIn(name, names)
            meta = json.loads(read(os.path.join(folder, 'meta.json')))
            self.assertEqual((len(meta['maps']), len(meta['charts'])), (6, 6))
        with redirected(self.fx.root):
            trips = {t['slug']: t for t in content.load_all()}
            for slug in STALE:
                self.assertIs(core.has_track(trips[slug]), False, slug)
                self.assertTrue(os.path.isfile(os.path.join(trips[slug]['rendered'], 'meta.json')))
                self.assertEqual(core.render_meta(trips[slug]), {'maps': {}, 'charts': {}})
            self.assertEqual(sorted(core.render_meta(trips['synb-story'])['maps']), ['map-col', 'map-phone', 'map-wide'])

    def test_no_drawing_and_no_map_render_is_published_for_them(self):
        self.assertEqual(files_of(self.path('trips/synb-notrack')), ['index.html', 'photos/01.webp'])       # its photo, still
        self.assertEqual(files_of(self.path('trips/synb-tour-none')), ['index.html', 'map/index.html'])
        for slug in STALE:
            for name in ('tile.svg', 'g112.svg', 'g64.svg'):
                self.assertFalse(os.path.exists(self.path('trips/%s/%s' % (slug, name))), '%s/%s' % (slug, name))
            for name in STALE_FILES:
                self.assertFalse(os.path.exists(self.path('trips/%s/map/%s' % (slug, name))), '%s/map/%s' % (slug, name))
        # the trip with a track has its three drawings and its map files
        for name in ('tile.svg', 'g112.svg', 'g64.svg', 'map/map-wide.webp', 'map/map-phone.base.svg'):
            self.assertTrue(os.path.isfile(self.path('trips/synb-story/' + name)), name)

    def test_no_bytes_of_a_stale_render_are_in_the_output(self):
        for rel in files_of(self.out):
            self.assertNotIn(b'stale render', read_bytes(self.path(rel)), rel)

    def test_no_page_draws_or_loads_anything_of_them(self):
        seen = 0
        for rel in self.html_files():
            text = read(self.path(rel))
            for slug in STALE:
                with self.subTest(page=rel, slug=slug):
                    refs = [u for u in re.findall(r'(?:src|href|srcset|imagesrcset)="([^"]*)"', text)
                            if re.search(r'trips/%s/(?:map/[^"/]+\.|tile\.svg|g112\.svg|g64\.svg)' % slug, u)]
                    self.assertEqual(refs, [])
            seen += len(re.findall(r'trips/synb-story/(?:tile|g112|g64)\.svg"', text))
        self.assertGreater(seen, 3)          # ... while the tracked report's drawings are on its own page and in the lists

    def test_their_pages_are_those_of_trips_that_were_never_rendered(self):
        report = self.doc('trips/synb-notrack/')
        for id_ in ('map', 'profile'):
            self.assertIsNone(report.by_id(id_))
        self.assertEqual(report.find_all(cls='keyrow') + report.find_all(cls='chart') + report.find_all(cls='mv'), [])
        self.assertEqual([ln['href'] for ln in report.find('head').find_all('link', attrs={'rel': 'preload'}) if '/map/' in ln['href']], [])
        self.assertEqual(report.find('a', cls='ab-trip').find_all('img'), [])           # no glyph in the phone app bar
        tour = self.doc('trips/synb-tour-none/')
        self.assertEqual(tour.find_all(cls='mv') + tour.find_all('img', cls='gl'), [])
        self.assertEqual(self.doc('trips/synb-tour-none/map/').find_all(cls='mv'), [])
        self.assertEqual([ln['href'] for ln in tour.find('head').find_all('link', attrs={'rel': 'preload'}) if '/map/' in ln['href']], [])
        # where they are listed, the row or card shows no drawing of theirs
        for url, slug in (('mountain-biking/', 'synb-notrack'), ('climbing/', 'synb-tour-none'), ('trips/', 'synb-notrack'), ('', 'synb-notrack')):
            for img in self.doc(url).find_all('img'):
                self.assertNotRegex(img['src'] or '', r'trips/%s/(tile|g112|g64)\.svg' % slug)
        self.assertIsNotNone(self.doc('trips/synb-story/').find('a', cls='ab-trip').find('img', cls='gl'))


# ================================================================ a build that must stop

class StoppedBuildTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        add_trip(self.root, 'synb-one', title='Synthetic One', date='2026-06-01', region=REGION, track=True)
        add_trip(self.root, 'synb-two', title='Synthetic Two', date='2026-05-01', region=REGION, track=True, featured=True)
        add_trip(self.root, 'synb-hidden', title='Synthetic Hidden', date='2026-04-01', region=REGION, track=True, draft=True)
        write_assets(self.root)
        self.marker = os.path.join(self.root, '_site', 'previous-build.txt')
        write(self.marker, 'the last good build')

    def assertStops(self, error, message):
        with self.assertRaises(error) as cm:
            run_build(self.root)
        self.assertEqual(str(cm.exception), message)
        self.assertEqual(files_of(os.path.join(self.root, '_site')), ['previous-build.txt'])      # nothing removed, nothing written
        self.assertEqual(read(self.marker), 'the last good build')

    def test_a_valid_site_builds_and_replaces_the_previous_output(self):
        write_home(self.root, ['synb-two'])
        out, pages = run_build(self.root)
        self.assertFalse(os.path.exists(self.marker))
        self.assertTrue(os.path.isfile(os.path.join(out, 'trips', 'synb-one', 'index.html')))
        self.assertFalse(os.path.exists(os.path.join(out, 'trips', 'synb-hidden')))
        self.assertIn('trips/synb-two/', [p.url for p in pages])

    def test_an_unknown_feature_stops_the_build_before_the_output_is_touched(self):
        write_home(self.root, ['synb-one', 'synb-missing'])
        self.assertStops(curation.CurationError,
                         "content/home.json: unknown slug 'synb-missing' in featured_slugs (no content/trips/synb-missing/index.md)")

    def test_a_featured_draft_is_named_as_a_draft(self):
        # the draft is looked up in the temp trips folder: the build read content/home.json and content/trips/ there
        write_home(self.root, ['synb-hidden'])
        self.assertStops(curation.CurationError,
                         "content/home.json: 'synb-hidden' is a draft (draft: true in its index.md); drafts cannot be featured")

    def test_a_content_error_stops_the_build_before_the_output_is_touched(self):
        write_home(self.root, ['synb-one'])
        add_trip(self.root, 'synb-late', lines=['published_at: 2031-05-22'], title='Synthetic Late', date='2026-03-01', region=REGION, track=True)
        self.assertStops(content.ContentError, 'content/trips/synb-late/index.md: published_at 2031-05-22 is in the future')

    def test_the_same_report_builds_once_today_has_caught_up(self):
        write_home(self.root, ['synb-one'])
        add_trip(self.root, 'synb-late', lines=['published_at: 2031-05-22'], title='Synthetic Late', date='2026-03-01', region=REGION, track=True)
        out, _pages = run_build(self.root, today=date(2031, 5, 21))
        self.assertIn('Published <time datetime="2031-05-22">May 22, 2031</time>', read(os.path.join(out, 'trips', 'synb-late', 'index.html')))

    def test_a_draft_with_a_future_published_at_does_not_stop_the_build(self):
        # contract 10.3: a draft may name the day it is planned to go online; it stays out of the site as every draft does
        write_home(self.root, ['synb-one'])
        add_trip(self.root, 'synb-soon', lines=['published_at: 2031-06-15', 'updated_at: 2031-06-16'], title='Synthetic Soon', date='2026-03-01',
                 region=REGION, track=True, draft=True)
        out, pages = run_build(self.root)
        self.assertFalse(os.path.exists(os.path.join(out, 'trips', 'synb-soon')))
        self.assertNotIn('trips/synb-soon/', [p.url for p in pages])
        for rel in files_of(out):
            if rel.endswith(('.html', '.json', '.xml')):
                self.assertNotIn('synb-soon', read(os.path.join(out, *rel.split('/'))), rel)
        self.assertTrue(os.path.isfile(os.path.join(out, 'trips', 'synb-one', 'index.html')))

    def test_the_same_report_no_longer_a_draft_stops_the_build(self):
        # ... and the moment the flag comes off, a date still ahead is the error it always was
        write_home(self.root, ['synb-one'])
        add_trip(self.root, 'synb-soon', lines=['published_at: 2031-06-15'], title='Synthetic Soon', date='2026-03-01', region=REGION, track=True)
        self.assertStops(content.ContentError, 'content/trips/synb-soon/index.md: published_at 2031-06-15 is in the future')

    def test_a_draft_with_a_malformed_published_at_still_stops_the_build(self):
        write_home(self.root, ['synb-one'])
        add_trip(self.root, 'synb-soon', lines=['published_at: next week'], title='Synthetic Soon', date='2026-03-01', region=REGION, track=True,
                 draft=True)
        self.assertStops(content.ContentError,
                         'content/trips/synb-soon/index.md: published_at must be a date written YYYY-MM-DD, or a date and time with an '
                         "offset such as 2026-10-03T18:30:00-07:00, got 'next week'")

    def test_without_home_json_the_build_warns_and_features_the_flagged_report(self):
        self.assertFalse(os.path.exists(os.path.join(self.root, 'content', 'home.json')))
        with self.assertWarns(UserWarning) as cm:
            out, _pages = run_build(self.root)
        self.assertIn('content/home.json is missing', str(cm.warning))
        feat = Doc(read(os.path.join(out, 'index.html'))).find('section', cls='hom-featured')
        self.assertIsNotNone(feat, 'the home page has no featured section')
        links = {a['href'] for a in feat.find_all('a') if (a['href'] or '').startswith('trips/')}
        self.assertEqual(links, {'trips/synb-two/'})          # the report flagged `featured: true`, not the newest one


# ================================================================ build.strip_css_comments

class StripCssCommentsTests(unittest.TestCase):

    # input -> exactly what is published
    TABLE = [
        # plain rules pass through; the result always ends with one newline
        ('a{b:c}', 'a{b:c}\n'),
        ('a{b:c}\n', 'a{b:c}\n'),
        ('a{b:c}\n\n\n', 'a{b:c}\n'),
        ('a {\n  b: c;\n}\n', 'a {\n  b: c;\n}\n'),
        # comments go: on their own line, at the end of a line, inside a rule, over several lines
        ('/* x */\na{b:c}\n', 'a{b:c}\n'),
        ('a{b:c} /* x */\n', 'a{b:c}\n'),
        ('a{b:c}\n/* x */', 'a{b:c}\n'),
        ('a{b:c; /* x */ d:e}', 'a{b:c;  d:e}\n'),
        ('a{b:c;/* x */ d:e}', 'a{b:c; d:e}\n'),
        ('a{b:c; /* x */d:e}', 'a{b:c; d:e}\n'),
        ('/*\n * x\n * y\n */\na{b:c}\n', 'a{b:c}\n'),
        ('a{b:c}\n/* x */\n/* y */\nd{e:f}\n', 'a{b:c}\nd{e:f}\n'),
        ('/**/a{b:c}', 'a{b:c}\n'),
        ('a{b:c}/**/', 'a{b:c}\n'),
        ('/* x *//* y */\na{b:c}', 'a{b:c}\n'),
        ('a /* x */ /* y */ b{c:d}', 'a   b{c:d}\n'),
        # comments with nothing between them are judged as one run (contract 10.1): it goes unless both of ITS sides are tokens
        ('a /* x *//* y */b{c:d}', 'a b{c:d}\n'),
        ('a/* x *//* y */ b{c:d}', 'a b{c:d}\n'),
        ('a/* x *//* y */\nb{c:d}', 'a\nb{c:d}\n'),
        ('a{b:c}/* x *//* y *//* z */', 'a{b:c}\n'),
        ('a{b:c}/* x *//* never closed\nd{e:f}', 'a{b:c}\n'),
        ('a{margin:0/* x *//* y */auto}', 'a{margin:0/* x *//* y */auto}\n'),
        ('.a/* x *//* y *//* z */.b{c:d}', '.a/* x *//* y *//* z */.b{c:d}\n'),
        ('/* a comment with a * star and a / slash */a{b:c}', 'a{b:c}\n'),
        ('/* a comment with /* an opening inside */a{b:c}', 'a{b:c}\n'),
        # a quote inside a comment opens no string
        ("/* it's */\na{b:c}\n/* isn't */\nd{e:f}\n", 'a{b:c}\nd{e:f}\n'),
        ('/* say "x */\na{b:c}', 'a{b:c}\n'),
        # strings are left alone, whatever they hold
        ('a{content:"/* not a comment */"}', 'a{content:"/* not a comment */"}\n'),
        ("a{content:'/* not a comment */'}", "a{content:'/* not a comment */'}\n"),
        ('a{content:"/*"}\nb{content:"*/"}', 'a{content:"/*"}\nb{content:"*/"}\n'),
        ('a{content:"\\"/* still the string */"}', 'a{content:"\\"/* still the string */"}\n'),
        ("a{content:'it\\'s /* x */'}", "a{content:'it\\'s /* x */'}\n"),
        ('a{content:"x"} /* y */', 'a{content:"x"}\n'),
        ('a{content:"x"; d:"/* y */"} /* z */\ne{f:g}', 'a{content:"x"; d:"/* y */"}\ne{f:g}\n'),
        ('a{b:url("img/*.png")}', 'a{b:url("img/*.png")}\n'),
        ("a{content:'\"'} /* x */ b{content:\"'\"}", "a{content:'\"'}  b{content:\"'\"}\n"),
        # text that only looks like the start or the end of a comment
        ('a{b:calc(4/2)}', 'a{b:calc(4/2)}\n'),
        ('a{b:calc(2*3)}', 'a{b:calc(2*3)}\n'),
        ('a{b:c} */ d{e:f}', 'a{b:c} */ d{e:f}\n'),
        ('a{b:url(//example.test/x.png)}', 'a{b:url(//example.test/x.png)}\n'),
        ('a > * / b{c:d}', 'a > * / b{c:d}\n'),
        # a comment wedged between two tokens with no space on either side stays: removing it could join them
        ('a{margin:0/**/auto}', 'a{margin:0/**/auto}\n'),
        ('.a/**/.b{c:d}', '.a/**/.b{c:d}\n'),
        ('a{b:c}/* x */d{e:f}', 'a{b:c}/* x */d{e:f}\n'),
        ('a{b:1px/* x */2px}', 'a{b:1px/* x */2px}\n'),
        # ... but not when either side is a space, a line break or the edge of the file
        ('a{margin:0 /**/auto}', 'a{margin:0 auto}\n'),
        ('a{margin:0/**/ auto}', 'a{margin:0 auto}\n'),
        ('a{b:c}/* x */\nd{e:f}', 'a{b:c}\nd{e:f}\n'),
        ('a{b:c}\n/* x */d{e:f}', 'a{b:c}\nd{e:f}\n'),
        # a comment that is never closed runs to the end of the file
        ('a{b:c}\n/* never closed\nd{e:f}', 'a{b:c}\n'),
        ('a{b:c} /*', 'a{b:c}\n'),
        ('a{b:c}/*', 'a{b:c}\n'),
        ('/* never closed', '\n'),
        # ... and so does a string that is never closed: nothing in it is taken for a comment
        ('a{b:"never closed /* x */', 'a{b:"never closed /* x */\n'),
        # blank lines collapse, lines emptied by a comment go, trailing spaces go, indentation stays
        ('a{b:c}\n\n\n\nd{e:f}\n\n', 'a{b:c}\nd{e:f}\n'),
        ('a{b:c}\n   \n\t\nd{e:f}', 'a{b:c}\nd{e:f}\n'),
        ('a{b:c}   \nd{e:f}\t\n', 'a{b:c}\nd{e:f}\n'),
        ('a {\n  b: c; /* x */\n  /* y */\n  d: e;\n}\n', 'a {\n  b: c;\n  d: e;\n}\n'),
        ('\n\n  a{b:c}\n', '  a{b:c}\n'),
        ('a{b:c}\r\n/* x */\r\nd{e:f}\r\n', 'a{b:c}\nd{e:f}\n'),
        ('', '\n'),
        ('\n\n', '\n'),
        ('/* only a comment */', '\n'),
    ]

    def test_table(self):
        for source, want in self.TABLE:
            with self.subTest(source=source):
                self.assertEqual(build.strip_css_comments(source), want)

    def test_it_is_idempotent(self):
        for source, _want in self.TABLE:
            with self.subTest(source=source):
                once = build.strip_css_comments(source)
                self.assertEqual(build.strip_css_comments(once), once)

    def test_the_result_ends_with_exactly_one_newline_and_has_no_blank_line(self):
        for source, _want in self.TABLE:
            with self.subTest(source=source):
                out = build.strip_css_comments(source)
                self.assertTrue(out.endswith('\n'))
                self.assertFalse(out.endswith('\n\n'))
                self.assertNotIn('\n\n', out)
                self.assertTrue(all(line == line.rstrip() for line in out.split('\n')))

    def test_a_string_survives_byte_for_byte(self):
        for text in ('"/* a */"', "'/* a */'", '"a \\" /* b */ \\" c"', "'\\'/*'", '"*/ /* */"'):
            with self.subTest(text=text):
                source = 'a{content:%s} /* gone */' % text
                self.assertEqual(build.strip_css_comments(source), 'a{content:%s}\n' % text)

    def test_a_run_of_comments_that_ends_at_a_space_is_dropped_whole(self):
        # only a comment wedged tightly between two TOKENS is kept. Here the first comment is followed by another
        # comment and then a space: nothing would be joined by dropping both, and keeping the first one would make a
        # second pass give a different result (contract 10.1: a run is judged as one, so the function is idempotent)
        source = 'a/* x *//* y */ b{c:d}'
        once = build.strip_css_comments(source)
        self.assertEqual(build.strip_css_comments(once), once, 'not idempotent: %r -> %r' % (source, once))
        self.assertNotIn('/*', once)

    def test_a_run_of_comments_between_two_tokens_keeps_them_apart(self):
        out = build.strip_css_comments('a{margin:0/* x *//* y */auto}')
        self.assertNotEqual(out, 'a{margin:0auto}\n')
        self.assertRegex(out, r'^a\{margin:0(/\*.*\*/)auto\}\n$')
        self.assertEqual(build.strip_css_comments(out), out)

    def test_the_bundle_of_two_sources_has_their_rules_and_no_comment(self):
        out = build.strip_css_comments('\n'.join([BASE_CSS, '/* alpha.css */\n' + ALPHA_CSS, '/* beta.css */\n' + BETA_CSS]))
        self.assertEqual(out, ':root { --synb-ink: #111; }\n.synb-base { color: var(--synb-ink); }\n.synb-alpha { margin: 0 auto; }\n'
                              '.synb-alpha-two { padding: 0; }\n.synb-beta { display: none; }\n')


# ================================================================ build.conflict_copy

class ConflictCopyTests(unittest.TestCase):

    def test_names_icloud_gives_a_conflict_copy(self):
        for name in ('meta 3.json', 'map-wide 4.webp', 'map-wide 2.base.svg', 'tile 2.svg.html', 'region-alps-desktop.svg 3.html',
                     'map-wide 12.webp', 'map-wide 100.webp', 'first-tallac-lap 2', 'first-tallac-lap 10', 'overview-tall 5.png',
                     '001-g64 2.svg.html', 'region-lake-tahoe-desktop 3.webp'):
            with self.subTest(name=name):
                self.assertIs(build.conflict_copy(name), True)

    def test_names_the_renderer_writes(self):
        for name in ('meta.json', 'map-wide.webp', 'map-wide.base.svg', 'tile.svg.html', 'g112.svg.html', 'g64.svg.html', 'map-phone.png',
                     'overview-tall.webp', 'profile-wide.svg.html', '001-g64.svg.html', '059-spark.svg.html', 'first-tallac-lap',
                     'region-lake-tahoe-desktop.webp', 'ski-eastern-sierra-phone.base.svg', 'map 2 wide.webp', 'map-wide2.webp',
                     'map-wide-2.webp', 'meta3.json', 'meta 3a.json', 'meta 3 .json', 'meta a.json', 'day 2 map.webp', ''):
            with self.subTest(name=name):
                self.assertIs(build.conflict_copy(name), False)

    def test_only_the_last_part_of_a_path_counts(self):
        self.assertIs(build.conflict_copy(os.path.join('rendered', 'trips', 'first-tallac-lap', 'meta 3.json')), True)
        self.assertIs(build.conflict_copy(os.path.join(os.sep, 'tmp', 'a folder 2', 'rendered', 'site', 'meta.json')), False)
        self.assertIs(build.conflict_copy(os.path.join('rendered', 'trips', 'first-tallac-lap 2')), True)
        self.assertIs(build.conflict_copy(os.path.join('Strava Export 9', 'rendered', 'site', 'region-x-desktop.webp')), False)


if __name__ == '__main__':
    unittest.main()
