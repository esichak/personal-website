"""Phase 4: tools/lib/checks.py, the content validator (run, survey, errors / warnings / notes, line, summary).

A small valid site is written once into a temp folder (eight trips: a single-day ski report with photos, beta and
stats, a bare single-day hike, a two-day hut tour, a three-day journal, three tick-list goals and a draft; a
home.json; a rendered/ folder beside it) and copied for every test, which then breaks one thing and reads the
findings. The fixture is clean on purpose (every photo has its .sm and .th copy, every track is real GPX text, every
trip with a track has its rendered meta.json), so a test can assert the exact list of errors and warnings.

CASES is the groundwork's table of 187 malformed inputs (the ones fed through `tools/build.py --check` at HEAD
6f6091d: 31 ended in a traceback, 18 were caught only by the link check, 52 stopped with a clean error, 86 were
accepted). Each runs through checks.run here and must give exactly the errors and warnings written beside it, and never
an exception. For the 52 clean errors the expected text is not written down at all: it is whatever the build's own
loading code raises for that input (build_error), so those messages are proved to come through unchanged.

Nothing here reads content/, rendered/ or _site/ of the checkout: every call names its folders, and the two tests of
the defaults patch them to the temp folder first.
"""
import datetime
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
import warnings
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import checks  # noqa: E402
import content  # noqa: E402
import goals  # noqa: E402
from sitegen import core  # noqa: E402
from sitegen import curation  # noqa: E402

import gpx_fixtures as gf  # noqa: E402
import helpers  # noqa: E402
from helpers import LANDSCAPE, PORTRAIT, photo  # noqa: E402

TODAY = datetime.date(2026, 10, 10)
SKI, HIKE, HUT, JOURNAL = 'ski-report', 'loop-hike', 'hut-tour', 'journal'
ACTS = 'ski, climb, hike, mtb, other'
SAME = object()     # in a case's errors: the message the build's own loading code raises for that input
TB, CHK, CLEAN, OK = 'traceback', 'check-only', 'clean-error', 'accepted'   # what the build did with the input at HEAD

_BASE = None
_BASE_TREE = None


def setUpModule():
    global _BASE, _BASE_TREE
    _BASE = tempfile.TemporaryDirectory()
    build_base(_BASE.name)
    _BASE_TREE = tree(_BASE.name)


def tearDownModule():
    _BASE.cleanup()


def write(path, text, mode='w'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, **({} if 'b' in mode else {'encoding': 'utf-8'})) as fh:
        fh.write(text)


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def build_base(root):
    """The valid site: <root>/content/trips/*, <root>/content/home.json and <root>/rendered/."""
    trips = os.path.join(root, 'content', 'trips')
    os.makedirs(trips)
    helpers.make_trip(trips, SKI, title='West Couloir', activity='ski', date='2026-01-17', place='Sawtooth Ridge',
                      region='Eastern Sierra', route_shape='out-and-back', start_time='06:10',
                      stats={'distance_km': 18.4, 'gain_m': 1450, 'loss_m': 1450, 'high_m': 3700, 'low_m': 2200,
                             'moving': '6:10', 'elapsed': '8:30'},
                      beta=[{'label': 'Trailhead', 'value': 'Twin Lakes'}, {'label': 'Snow', 'value': 'Firm'}],
                      body='Skinned up from Twin Lakes before dawn. ' * 6,
                      photos=[photo('photos/01.webp', LANDSCAPE, alt='Granite spires', caption='The spires'),
                              photo('photos/02.webp', PORTRAIT, alt='Skier in the couloir'),
                              photo('photos/03.webp', LANDSCAPE, alt='The summit ridge')])
    helpers.make_trip(trips, HIKE, title='Basin Loop', activity='hike', date='2025-08-10', place='Desolation',
                      region='Lake Tahoe', stats={'distance_km': 12.0, 'gain_m': 600})
    helpers.make_trip(trips, HUT, title='Hut Tour', activity='ski', kind='multi-day', place='Alps', region='Alps',
                      body='Two days hut to hut.',
                      days=[{'title': 'Approach', 'date': '2024-03-01', 'stats': {'distance_km': 10.0, 'gain_m': 900},
                             'body': 'Up to the hut.', 'photos': [photo('photos/d01-01.webp', LANDSCAPE, alt='The hut')]},
                            {'title': 'Col', 'date': '2024-03-02', 'stats': {'distance_km': 14.0, 'gain_m': 700}}])
    helpers.make_series(trips, JOURNAL, tracks=(True, True, True), photos=False, title='Long Trail Journal')
    f = helpers.make_trip(trips, 'goal-route', title='Someday Ridge', activity='hike', kind='planned', region='Lake Tahoe',
                          stats={'distance_km': 9.0}, body='Planning notes here.')
    write(os.path.join(f, 'track.gpx'), gf.SINGLE)
    sha = hashlib.sha256(gf.SINGLE.encode('utf-8')).hexdigest()
    put_json(os.path.join(f, 'goal.json'), {
        'schema_version': 1, 'status': 'shortlisted', 'priority': 'high', 'archived': False,
        'route_scope': 'full-intended-route',
        'route_source': {'kind': 'planner-export', 'url': None, 'label': None, 'checked_at': None, 'public_copy_approved': True},
        'route': {'source_sha256': sha, 'method': 'ticklist-gpx-1', 'selected': {'type': 'trk', 'index': 0, 'name': 'Synthetic ridge'},
                  'alternatives': 1, 'segments': 1, 'points': 12, 'elevation': 'full', 'times': True, 'waypoints': 0},
        'outings': []})
    f = helpers.make_trip(trips, 'goal-idea', title='An Idea', activity='climb', kind='planned')
    put_json(os.path.join(f, 'goal.json'), {'schema_version': 1, 'status': 'idea', 'priority': 'normal'})
    f = helpers.make_trip(trips, 'goal-done', title='Done Peak', activity='ski', kind='planned', region='Eastern Sierra')
    put_json(os.path.join(f, 'goal.json'), {
        'schema_version': 1, 'status': 'completed', 'priority': 'normal',
        'outings': [{'outcome': 'completed', 'date': '2026-01-17', 'report_slug': SKI, 'note': ''}]})
    helpers.make_trip(trips, 'draft-trip', title='Draft', activity='hike', date='2026-02-02', draft=True, body='Not yet.')
    # real GPX text where helpers left an empty placeholder, and for the three single-day trips
    for slug in (SKI, HIKE, 'draft-trip'):
        write(os.path.join(trips, slug, 'track.gpx'), gf.SINGLE)
    for slug, days in ((HUT, ('01', '02')), (JOURNAL, ('001', '002', '003'))):
        for d in days:
            write(os.path.join(trips, slug, 'days', d + '.gpx'), gf.SINGLE)
    # the 800 px and card-size copies beside every photo
    for slug in os.listdir(trips):
        folder = os.path.join(trips, slug, 'photos')
        for name in (sorted(os.listdir(folder)) if os.path.isdir(folder) else []):
            base, ext = os.path.splitext(name)
            for suffix in ('.sm', '.th'):
                helpers.touch(os.path.join(folder, base + suffix + ext))
    put_json(os.path.join(root, 'content', 'home.json'), {'featured_slugs': [SKI, HUT]})
    for slug in (SKI, HIKE, HUT, JOURNAL, 'goal-route'):
        write(os.path.join(root, 'rendered', 'trips', slug, 'meta.json'), '{}')
    put_json(os.path.join(root, 'rendered', 'site', 'meta.json'),
             {'maps': {}, 'regions': [], 'all_regions': ['Alps', 'Eastern Sierra', 'Lake Tahoe']})


def put_json(path, value):
    write(path, json.dumps(value, indent=2))


class Site:
    """One test's own copy of the valid site, with the handful of edits the tests make to it. It remembers every trip
    folder (and home.json, and rendered/) it has handed out a path to, so reset() can put exactly those back between
    two cases of a loop: a fresh copy of the whole site for each of several hundred cases is most of the running time."""

    def __init__(self, root):
        self.root = root
        self._trips = os.path.join(root, 'content', 'trips')
        self._home = os.path.join(root, 'content', 'home.json')
        self._rendered = os.path.join(root, 'rendered')
        self._touched = set()

    @property
    def trips(self):
        self._touched.add('trips')
        return self._trips

    @property
    def home(self):
        self._touched.add('home')
        return self._home

    @property
    def rendered(self):
        self._touched.add('rendered')
        return self._rendered

    def path(self, slug, *parts):
        self._touched.add(('trip', slug))
        return os.path.join(self._trips, slug, *parts)

    def reset(self):
        """The valid site again, wherever a path was handed out since the last reset."""
        def put_back(mine, base):
            if os.path.isdir(mine):
                shutil.rmtree(mine)
            elif os.path.lexists(mine):
                os.remove(mine)
            if os.path.isdir(base):
                shutil.copytree(base, mine, copy_function=shutil.copyfile)
            elif os.path.exists(base):
                shutil.copyfile(base, mine)
        touched, self._touched = self._touched, set()
        if 'trips' in touched:
            put_back(self._trips, os.path.join(_BASE.name, 'content', 'trips'))
        else:
            for slug in sorted(t[1] for t in touched if isinstance(t, tuple)):
                put_back(os.path.join(self._trips, slug), os.path.join(_BASE.name, 'content', 'trips', slug))
        if 'home' in touched:
            put_back(self._home, os.path.join(_BASE.name, 'content', 'home.json'))
        if 'rendered' in touched:
            put_back(self._rendered, os.path.join(_BASE.name, 'rendered'))

    def index(self, slug):
        return self.path(slug, 'index.md')

    def day(self, slug, day_id):
        return self.path(slug, 'days', day_id + '.md')

    def sub(self, path, old, new):
        text = read(path)
        assert old in text, 'the fixture no longer holds %r in %s:\n%s' % (old, path, text[:800])
        write(path, text.replace(old, new, 1))

    def add(self, slug, line):
        """One more front-matter line in index.md, right under the activity."""
        text = read(self.index(slug))
        act = [ln for ln in text.split('\n') if ln.startswith('activity: ')][0]
        write(self.index(slug), text.replace(act, act + '\n' + line, 1))

    def body(self, slug, text):
        write(self.index(slug), read(self.index(slug)) + '\n' + text + '\n')

    def remove(self, *paths):
        for p in paths:
            os.remove(p)

    def goal(self, slug):
        return json.loads(read(self.path(slug, 'goal.json')))

    def put_goal(self, slug, g):
        put_json(self.path(slug, 'goal.json'), g)

    def setg(self, slug, **kw):
        g = self.goal(slug)
        g.update(kw)
        self.put_goal(slug, g)

    def put_home(self, value):
        write(self.home, value if isinstance(value, str) else json.dumps(value))

    def gpx(self, path):
        write(path, gf.SINGLE)

    def survey(self, today=TODAY):
        return checks.survey(self._trips, self._home, self._rendered, today)

    def run(self, today=TODAY):
        return checks.run(self._trips, self._home, self._rendered, today)


def texts(findings):
    return sorted(f['text'] for f in findings)


def build_error(site):
    """What `tools/build.py` printed after 'ERROR ' for this content at HEAD: the first error of content.load_all (every
    folder, in order, drafts too), then of goals.validate_site, then of the manifest. None when it builds."""
    try:
        trips = helpers.load_dir(site._trips)
        s = helpers.make_site(trips, register=False)
        s['goals'] = s['planned']
        goals.validate_site(s)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')      # the missing-manifest fallback warns; it is not an error
            curation.resolve_featured(s, curation.load_manifest(site._home), trips_dir=site._trips)
    except (content.ContentError, curation.CurationError) as ex:
        return str(ex)
    return None


def tree(root):
    """Every file and folder under root, as relative paths."""
    out = set()
    for folder, dirs, files in os.walk(root):
        out.update(os.path.relpath(os.path.join(folder, n), root) for n in dirs + files)
    return out


class Fixture(unittest.TestCase):
    """Every test starts from the valid site: one copy per test class, put back (Site.reset) before each test."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        root = os.path.join(cls._tmp.name, 'site')
        shutil.copytree(_BASE.name, root, copy_function=shutil.copyfile)
        cls.site = Site(root)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        self.s = self.site
        self.s.reset()
        self.assertEqual(tree(self.s.root), _BASE_TREE, 'an earlier test changed the site behind Site.reset\'s back')

    def errors(self, **kw):
        return texts(checks.errors(self.s.run(**kw)))

    def warnings(self, **kw):
        return texts(checks.warnings(self.s.run(**kw)))

    def notes(self, **kw):
        return texts(checks.notes(self.s.run(**kw)))

    def assertFindings(self, errors=(), warnings=(), **kw):
        """Exactly these errors and exactly these warnings (the fixture has none of its own), whatever the notes."""
        found = self.s.run(**kw)
        self.assertEqual(texts(checks.errors(found)), sorted(errors))
        self.assertEqual(texts(checks.warnings(found)), sorted(warnings))


def I(slug, msg):   # noqa: E743  (index.md of a trip)
    return 'content/trips/%s/index.md: %s' % (slug, msg)


def D(slug, day, msg):
    return 'content/trips/%s/days/%s.md: %s' % (slug, day, msg)


def G(slug, msg):
    return 'content/trips/%s/goal.json: %s' % (slug, msg)


def H(msg):
    return 'content/home.json: %s' % msg


# ---------------------------------------------------------------- the 187 inputs of the groundwork

def outing(**kw):
    return dict({'outcome': 'completed', 'date': None, 'report_slug': None, 'note': ''}, **kw)


def photos_block(s):
    """The whole photos: block of the ski report's index.md."""
    lines, block = read(s.index(SKI)).split('\n'), []
    i = lines.index('photos:')
    block.append(lines[i])
    for ln in lines[i + 1:]:
        if not ln.startswith('  '):
            break
        block.append(ln)
    return '\n'.join(block) + '\n'


def no_route_block(s):
    g = s.goal('goal-route')
    g.pop('route')
    s.put_goal('goal-route', g)


def unapproved(s):
    g = s.goal('goal-route')
    g['route_source']['public_copy_approved'] = False
    s.put_goal('goal-route', g)


def copy_trip(s, name):
    shutil.copytree(s.path(HIKE), s.path(name))


def move_photo_out(s):
    s.sub(s.index(SKI), 'file: photos/02.webp', 'file: pics/02.webp')
    os.makedirs(s.path(SKI, 'pics'))
    shutil.move(s.path(SKI, 'photos', '02.webp'), s.path(SKI, 'pics', '02.webp'))


def planned_days(s):
    write(s.path('goal-idea', 'days', '01.md'), '---\ntitle: D1\n---\n')


P2 = '  - file: photos/02.webp\n    w: 1200\n    h: 1600\n    alt: Skier in the couloir\n'
BETA = 'beta:\n  - label: Trailhead\n    value: Twin Lakes\n  - label: Snow\n    value: Firm\n'
SNOW = '  - label: Snow\n    value: Firm\n'
HIKE_STATS = 'stats:\n  distance_km: 12.0\n  gain_m: 600'
DAY2_STATS = 'stats:\n  distance_km: 14.0\n  gain_m: 700'
DATE = 'date must be a date written YYYY-MM-DD, got %r'
CLOCK = 'start_time must be a time written HH:MM (00:00 to 23:59), got %r'
NO_TITLE = "title is missing or empty (write the trip's name after title:)"
NO_ACT = 'activity is missing; it must be one of ' + ACTS
BAD_ACT = 'activity must be one of ' + ACTS + ', got %r'
NO_DAYS = "kind is %r but the folder has no day files (days/01.md, days/02.md, ...)"
STATS = 'stats must be a block of lines such as distance_km: 12.4, got %r'
PHOTOS = 'photos must be a list of entries, each starting with - file: photos/<name>, got %r'
BETA_LIST = 'beta must be a list of rows, each - label: ... with a value: line under it, got %r'
MAP = 'map must be a block of lines such as peaks: [Mount Tallac], got %r'
PEAKS = 'map.peaks must be a name or a list of names such as [Mount Tallac], got %r'
MISSING = "photos[1].file 'photos/02.webp' is missing from the trip folder"
NO_PAGE = "write-up link %r points at trips/%s/, which is not a page of the site (no content/trips/%s/index.md)"
ROOTED = ('write-up link %r starts with /, which leaves the site (it is served under ' + core.SITE_URL + '); write a relative '
          'link such as ../other-trip/ or the full address')
NO_TRACK = 'no track.gpx: the page has no map, no profile and no GPX download'
A_TRACK = "; a report's track must be a GPX file with at least one point (without the file there is no map and no download for it)"
NO_ROUTE = 'track.gpx is published but there is no route block, so nothing records where the file came from or how it was measured'
NO_REGION = "region %r is not in rendered/site/meta.json, so the map page does not list it yet; run python3 tools/render.py --site --force"
SPELLED = ('region %r is written %r on %s; the two are listed as different regions but share one filter value and one map '
           'anchor (%s)')
FOLDER = 'the folder name %r cannot be a page address: use lower-case letters, digits and single dashes (such as %s)'
UNKNOWN = 'unknown key %r; nothing reads it'


def ski(old, new):
    return lambda s: s.sub(s.index(SKI), old, new)


def hike(old, new):
    return lambda s: s.sub(s.index(HIKE), old, new)


def ski_line(line):
    return lambda s: s.sub(s.index(SKI), 'route_shape: out-and-back', 'route_shape: out-and-back\n' + line)


def hike_line(line):
    return lambda s: s.sub(s.index(HIKE), 'activity: hike', 'activity: hike\n' + line)


def day2(old, new):
    return lambda s: s.sub(s.day(HUT, '02'), old, new)


def goal(slug, **kw):
    return lambda s: s.setg(slug, **kw)


def link(text):
    return lambda s: s.body(SKI, text)


def home(value):
    return lambda s: s.put_home(value)


CASES = [
    # ---- dates and times
    ('SKI date 2026-13-45', TB, ski('date: 2026-01-17', 'date: 2026-13-45'), [I(SKI, DATE % '2026-13-45')], []),
    ('HIKE date 2025-13-45', OK, hike('date: 2025-08-10', 'date: 2025-13-45'), [I(HIKE, DATE % '2025-13-45')], []),
    ('HIKE date non-date string', OK, hike('date: 2025-08-10', 'date: last summer'), [I(HIKE, DATE % 'last summer')], []),
    ('HIKE date US format 8/10/2025', OK, hike('date: 2025-08-10', 'date: 8/10/2025'), [I(HIKE, DATE % '8/10/2025')], []),
    ('HIKE date bare year 2025', OK, hike('date: 2025-08-10', 'date: 2025'), [I(HIKE, DATE % 2025)], []),
    ('HIKE date with time 2025-08-10T07:00', OK, hike('date: 2025-08-10', 'date: 2025-08-10T07:00'),
     [I(HIKE, DATE % '2025-08-10T07:00')], []),
    ('HIKE date in the future 2099-01-01', OK, hike('date: 2025-08-10', 'date: 2099-01-01'),
     [], [I(HIKE, 'date 2099-01-01 is in the future (today is 2026-10-10)')]),
    ('SKI date in the future 2099-01-01', OK, ski('date: 2026-01-17', 'date: 2099-01-01'),
     [], [I(SKI, 'date 2099-01-01 is in the future (today is 2026-10-10)')]),
    ('MULTI end_date before date', OK,
     lambda s: s.sub(s.index(HUT), 'kind: multi-day', 'kind: multi-day\ndate: 2024-03-05\nend_date: 2024-03-01'),
     [I(HUT, 'end_date 2024-03-01 is before date 2024-03-05')], []),
    ('SERIES end_date before date', OK, lambda s: s.sub(s.index(JOURNAL), 'end_date: 2024-09-21', 'end_date: 2023-01-01'),
     [I(JOURNAL, 'end_date 2023-01-01 is before date 2024-04-22')], []),
    ('SINGLE end_date on a single-day trip, before date', OK, hike('date: 2025-08-10', 'date: 2025-08-10\nend_date: 2025-01-01'),
     [I(HIKE, 'end_date 2025-01-01 is before date 2025-08-10')], []),
    ('MULTI day date invalid 2024-02-31', OK, day2('date: 2024-03-02', 'date: 2024-02-31'), [D(HUT, '02', DATE % '2024-02-31')], []),
    ('MULTI days out of order (day 2 before day 1)', OK, day2('date: 2024-03-02', 'date: 2024-02-20'),
     [], [D(HUT, '02', 'date 2024-02-20 is before the day ahead of it (days/01.md, 2024-03-01); days are shown in file order')]),
    ('start_time not a time (dawn)', TB, ski('start_time: "06:10"', 'start_time: dawn'), [I(SKI, CLOCK % 'dawn')], []),
    ('start_time 25:99', OK, ski('start_time: "06:10"', 'start_time: "25:99"'), [I(SKI, CLOCK % '25:99')], []),
    # ---- the older fields
    ('activity unknown (paraglide)', TB, hike('activity: hike', 'activity: paraglide'), [I(HIKE, BAD_ACT % 'paraglide')], []),
    ('activity missing', OK, hike('activity: hike\n', ''), [I(HIKE, NO_ACT)], []),
    ('activity wrong case (Hike)', TB, hike('activity: hike', 'activity: Hike'), [I(HIKE, BAD_ACT % 'Hike')], []),
    ('kind unknown (epic)', CHK, hike_line('kind: epic'),
     [I(HIKE, "kind must be one of multi-day, series, planned (leave the line out for a single-day report), got 'epic'")], []),
    ('kind multi-day without day files', CHK, hike_line('kind: multi-day'), [I(HIKE, NO_DAYS % 'multi-day')], []),
    ('kind trip (default) WITH day files', CHK, lambda s: s.sub(s.index(HUT), 'kind: multi-day\n', ''),
     [I(HUT, 'days/ holds 2 day files but there is no kind: line; add kind: multi-day (or kind: series for a journal)')], []),
    ('kind series without day files', CHK, hike_line('kind: series'), [I(HIKE, NO_DAYS % 'series')], []),
    ('title missing', OK, hike('title: Basin Loop\n', ''), [I(HIKE, NO_TITLE)], []),
    ('title empty', OK, hike('title: Basin Loop', 'title:'), [I(HIKE, NO_TITLE)], []),
    ('title a number (2025)', TB, hike('title: Basin Loop', 'title: 2025'), [I(HIKE, 'title must be text, got 2025')], []),
    ('title a list', TB, hike('title: Basin Loop', 'title: [Basin, Loop]'), [I(HIKE, "title must be text, got ['Basin', 'Loop']")], []),
    ('stats a string', TB, hike(HIKE_STATS, 'stats: fast'), [I(HIKE, STATS % 'fast')], []),
    ('stats a list', TB, hike(HIKE_STATS, 'stats: [12, 600]'), [I(HIKE, STATS % ([12, 600],))], []),
    ('stats.distance_km a string (far)', TB, hike('distance_km: 12.0', 'distance_km: far'),
     [I(HIKE, "stats.distance_km must be a number, got 'far'")], []),
    ('stats.distance_km with unit (12 km)', TB, hike('distance_km: 12.0', 'distance_km: 12 km'),
     [I(HIKE, "stats.distance_km must be a number, got '12 km'")], []),
    ('stats.gain_m with comma ("1,450")', TB, ski('gain_m: 1450', 'gain_m: "1,450"'),
     [I(SKI, "stats.gain_m must be a number, got '1,450'")], []),
    ('stats.distance_km negative', OK, hike('distance_km: 12.0', 'distance_km: -12.0'),
     [I(HIKE, 'stats.distance_km cannot be negative, got -12.0')], []),
    ('stats.distance_km true', OK, hike('distance_km: 12.0', 'distance_km: true'),
     [I(HIKE, 'stats.distance_km must be a number, got True')], []),
    ('stats.moving not h:mm (fast)', TB, ski('moving: "6:10"', 'moving: fast'),
     [I(SKI, 'stats.moving must be a time written H:MM such as "6:10", got \'fast\'')], []),
    ('stats.moving as minutes int (370)', OK, ski('moving: "6:10"', 'moving: 370'), [], []),
    ('stats unknown key (distance_mi)', OK, hike('distance_km: 12.0', 'distance_mi: 7.5'),
     [], [I(HIKE, "unknown key 'distance_mi' in stats (did you mean 'distance_km'?); nothing reads it")]),
    ('day stats a string (multi-day)', TB, day2(DAY2_STATS, 'stats: long'), [D(HUT, '02', STATS % 'long')], []),
    ('day stats.distance_km a string', TB, day2('distance_km: 14.0', 'distance_km: long'),
     [D(HUT, '02', "stats.distance_km must be a number, got 'long'")], []),
    ('route_shape unknown (lollipop)', OK, ski('route_shape: out-and-back', 'route_shape: lollipop'),
     [], [I(SKI, "route_shape 'lollipop' is not one of loop, out-and-back, point-to-point; it is shown as written")]),
    ('region differs only in case (lake tahoe)', OK, hike('region: Lake Tahoe', 'region: lake tahoe'),
     [], [I(HIKE, SPELLED % ('lake tahoe', 'Lake Tahoe', '1 other trip', 'lake-tahoe')), I(HIKE, NO_REGION % 'lake tahoe')]),
    ('draft: no (string)', OK, hike_line('draft: no'), [I(HIKE, "draft must be true or false, got 'no'")], []),
    ('draft: "false" (quoted)', OK, hike_line('draft: "false"'), [I(HIKE, "draft must be true or false, got 'false'")], []),
    ('featured: "false" (quoted)', OK, hike_line('featured: "false"'), [I(HIKE, "featured must be true or false, got 'false'")], []),
    ('subtype unknown on other', OK, hike('activity: hike', 'activity: other\nsubtype: Zorbing'),
     [], [I(HIKE, "subtype 'Zorbing' is not one of SUP, Rafting, Kayaking, Mountaineering; it is shown as written")]),
    ('conditions a string', OK, hike_line('conditions: icy'), [], []),
    ('party a list', TB, hike_line('party: [Sam, Alex]'), [I(HIKE, "party must be text, got ['Sam', 'Alex']")], []),
    ('place a number', TB, hike('place: Desolation', 'place: 9000'), [I(HIKE, 'place must be text, got 9000')], []),
    ('front matter not closed', CLEAN, lambda s: write(s.index(HIKE), '---\ntitle: X\nactivity: hike\n'), [SAME], []),
    ('front matter bad line (no colon)', CLEAN, hike('activity: hike', 'activity hike'), [SAME], []),
    ('front matter broken quote', CLEAN, hike('title: Basin Loop', 'title: "Basin Loop'), [SAME], []),
    ('index.md without front matter', OK, lambda s: write(s.index(HIKE), 'Just prose.\n'), [I(HIKE, NO_ACT), I(HIKE, NO_TITLE)], []),
    ('index.md empty', OK, lambda s: write(s.index(HIKE), ''), [I(HIKE, NO_ACT), I(HIKE, NO_TITLE)], []),
    ('unknown front-matter key (typo: plase)', OK, hike('place: Desolation', 'plase: Desolation'),
     [], [I(HIKE, "unknown key 'plase' (did you mean 'place'?); nothing reads it")]),
    ('duplicate key (title twice)', OK, hike('title: Basin Loop', 'title: Basin Loop\ntitle: Other Name'), [],
     [I(HIKE, "key 'title' is written twice in the front matter; only the last one is read")]),
    # ---- goals
    ('outing names a report slug that does not exist', CLEAN, goal('goal-done', outings=[outing(report_slug='no-such-report')]), [SAME], []),
    ('outing names a DRAFT report', CLEAN, goal('goal-done', outings=[outing(report_slug='draft-trip')]), [SAME], []),
    ('outing names a GOAL (planned route)', CLEAN, goal('goal-done', outings=[outing(report_slug='goal-route')]), [SAME], []),
    ('outing names the goal itself', CLEAN, goal('goal-done', outings=[outing(report_slug='goal-done')]), [SAME], []),
    ('outing report_slug not a slug (Has Spaces)', CLEAN, goal('goal-done', outings=[outing(report_slug='Has Spaces')]), [SAME], []),
    ('completed goal without an outing', CLEAN, goal('goal-done', outings=[]), [SAME], []),
    ('status idea but a completed outing is logged', CLEAN, goal('goal-done', status='idea'), [SAME], []),
    ('attempted status without an attempted outing', CLEAN, goal('goal-idea', status='attempted'), [SAME], []),
    ('two goals claim one report', OK, goal('goal-idea', status='completed', outings=[outing(report_slug=SKI)]), [], []),
    ('one goal lists the same report twice', OK,
     goal('goal-done', outings=[outing(report_slug=SKI, outcome='attempted'), outing(report_slug=SKI)]),
     [], [G('goal-done', "outings[1].report_slug 'ski-report' is already named by outings[0]")]),
    ('outing date invalid (2026-13-45)', CLEAN, goal('goal-done', outings=[outing(date='2026-13-45', report_slug=SKI)]), [SAME], []),
    ('outing date in the future (2099-01-01)', OK, goal('goal-done', outings=[outing(date='2099-01-01', report_slug=SKI)]),
     [], [G('goal-done', 'outings[0].date 2099-01-01 is in the future (today is 2026-10-10); an outing is something that happened')]),
    ('outing date differs from the linked report date', OK, goal('goal-done', outings=[outing(date='2020-05-05', report_slug=SKI)]), [], []),
    ('completed outing dated before an attempted one (order)', OK,
     goal('goal-done', outings=[outing(date='2026-01-17'), outing(outcome='attempted', date='2026-03-01')]), [], []),
    ('goal route file missing (route block, no track.gpx)', OK, lambda s: s.remove(s.path('goal-route', 'track.gpx')),
     [G('goal-route', 'the route block is there but track.gpx is missing from the folder: the page would describe a route it can '
                      'neither draw nor offer; put the file back')], []),
    ('goal route sha mismatch (track.gpx edited)', CLEAN,
     lambda s: write(s.path('goal-route', 'track.gpx'), gf.SINGLE + '<!-- edited -->\n'), [SAME], []),
    ('goal track.gpx present but no route block in goal.json', OK, no_route_block, [], [G('goal-route', NO_ROUTE)]),
    ('goal track.gpx published with public_copy_approved false', OK, unapproved,
     [], [G('goal-route', 'track.gpx is published but route_source.public_copy_approved is false; set it to true once you approve '
                          'publishing the file, or remove track.gpx')]),
    ('goal track.gpx empty (0 bytes) with no route block', OK,
     lambda s: (no_route_block(s), write(s.path('goal-route', 'track.gpx'), '')), [], [G('goal-route', NO_ROUTE)]),
    ('goal.json beside a report', CLEAN, lambda s: shutil.copy(s.path('goal-idea', 'goal.json'), s.path(HIKE, 'goal.json')), [SAME], []),
    ('goal.json malformed JSON', CLEAN, lambda s: write(s.path('goal-idea', 'goal.json'), '{"status": '), [SAME], []),
    ('goal.json a list', CLEAN, lambda s: write(s.path('goal-idea', 'goal.json'), '[]'), [SAME], []),
    ('goal.json empty object', OK, lambda s: write(s.path('goal-idea', 'goal.json'), '{}'), [], []),
    ('goal unknown status', CLEAN, goal('goal-idea', status='done'), [SAME], []),
    ('goal unknown key (private: true)', CLEAN, goal('goal-idea', private=True), [SAME], []),
    ('goal target_months [13]', CLEAN, goal('goal-idea', target_months=[13]), [SAME], []),
    ('goal added_at invalid', CLEAN, goal('goal-idea', added_at='yesterday'), [SAME], []),
    ('goal added_at in the future', OK, goal('goal-idea', added_at='2099-01-01'), [], []),
    ('goal reference url javascript:', CLEAN,
     goal('goal-idea', references=[{'id': 'a', 'label': 'x', 'url': 'javascript:alert(1)', 'checked_at': None}]), [SAME], []),
    ('goal difficulty without approved evidence', CLEAN, goal('goal-idea', difficulty={'system': 'YDS', 'value': '5.7'}), [SAME], []),
    ('goal schema_version 2', CLEAN, goal('goal-idea', schema_version=2), [SAME], []),
    ('planned trip with a date in front matter', OK, lambda s: s.sub(s.index('goal-idea'), 'kind: planned', 'kind: planned\ndate: 2027-07-01'),
     [], [I('goal-idea', "a planned route has a date: line (2027-07-01); a goal has no date, and an outing's date goes in goal.json")]),
    ('planned trip with day files', CHK, planned_days,
     [I('goal-idea', "days/ holds 1 day file but kind is 'planned'; day files belong to kind: multi-day (or kind: series for a "
                     "journal): change the kind or remove days/")], []),
    ('planned trip, unknown activity', TB, lambda s: s.sub(s.index('goal-idea'), 'activity: climb', 'activity: scramble'),
     [I('goal-idea', BAD_ACT % 'scramble')], []),
    ('goal.json on a DRAFT planned trip, invalid status', CLEAN,
     lambda s: (s.sub(s.index('goal-idea'), 'kind: planned', 'kind: planned\ndraft: true'), s.setg('goal-idea', status='done')), [SAME], []),
    # the build stopped at the outing; the manifest names the same report, which is now a draft there too
    ('report draft flag set while a goal outing links it', CLEAN, ski('activity: ski', 'activity: ski\ndraft: true'),
     [SAME, H("'ski-report' is a draft (draft: true in its index.md); drafts cannot be featured")], []),
    # ---- links in write-ups, regions, titles
    ('body link to a report that does not exist [--check]', CHK, link('[LINK](../no-such-trip/)'),
     [I(SKI, NO_PAGE % ('../no-such-trip/', 'no-such-trip', 'no-such-trip'))], []),
    ('body link to a report that does not exist [plain build]', OK, link('[LINK](../no-such-trip/)'),
     [I(SKI, NO_PAGE % ('../no-such-trip/', 'no-such-trip', 'no-such-trip'))], []),
    # an anchor is an id of a built page: only the built-site check (sitecheck) can see whether it exists
    ('body link to a missing anchor on another report', CHK, link('[LINK](../loop-hike/#nope)'), [], []),
    ('body link to a missing anchor on its own page', CHK, link('[LINK](#nope)'), [], []),
    ('body link, absolute site URL to a missing report', OK, link('[LINK](%strips/no-such-trip/)' % core.SITE_URL),
     [I(SKI, NO_PAGE % (core.SITE_URL + 'trips/no-such-trip/', 'no-such-trip', 'no-such-trip'))], []),
    ('body link, root-relative (/trips/loop-hike/)', CHK, link('[LINK](/trips/loop-hike/)'), [I(SKI, ROOTED % '/trips/loop-hike/')], []),
    ('body link, root-relative with the project prefix', CHK, link('[LINK](/personal-website/trips/loop-hike/)'),
     [I(SKI, ROOTED % '/personal-website/trips/loop-hike/')], []),
    ('body link, javascript: scheme', OK, link('[LINK](javascript:alert(1))'),
     [I(SKI, "write-up link 'javascript:alert(1' uses javascript:, and only http, https, mailto links are accepted")], []),
    ('body link to a draft report', CHK, link('[LINK](../draft-trip/)'),
     [I(SKI, "write-up link '../draft-trip/' points at trips/draft-trip/, a draft, which has no page")], []),
    ('body with raw HTML and a script tag', OK, link('<script>alert(1)</script> <b>bold</b>'), [], []),
    ('body markdown image syntax', OK, link('![alt text](photos/02.webp)'), [], []),
    ('two published trips, regions differ only in case', OK, hike('region: Lake Tahoe', 'region: eastern sierra'),
     [], [I(HIKE, SPELLED % ('eastern sierra', 'Eastern Sierra', '2 other trips', 'eastern-sierra')), I(HIKE, NO_REGION % 'eastern sierra')]),
    ('two regions that slugify alike (Lake Tahoe / Lake-Tahoe)', OK, hike('region: Lake Tahoe', 'region: Lake-Tahoe'),
     [], [I(HIKE, SPELLED % ('Lake-Tahoe', 'Lake Tahoe', '1 other trip', 'lake-tahoe')), I(HIKE, NO_REGION % 'Lake-Tahoe')]),
    ('region with only punctuation (slug empty)', OK, hike('region: Lake Tahoe', 'region: "???"'), [], [I(HIKE, NO_REGION % '???')]),
    ('same title on two reports', OK, hike('title: Basin Loop', 'title: West Couloir'), [], []),
    ('same title AND same date on two reports', OK,
     lambda s: (s.sub(s.index(HIKE), 'title: Basin Loop', 'title: West Couloir'), s.sub(s.index(HIKE), 'date: 2025-08-10', 'date: 2026-01-17')),
     [], [I(SKI, "same title and date as content/trips/loop-hike/index.md ('West Couloir', 2026-01-17): the two pages get the same <title>")]),
    ('goal and report share a title', OK, lambda s: s.sub(s.index('goal-idea'), 'title: An Idea', 'title: West Couloir'), [], []),
    # ---- beta, map, the presentation fields, the manifest
    ('beta a string', TB, ski(BETA, 'beta: Twin Lakes trailhead\n'), [I(SKI, BETA_LIST % 'Twin Lakes trailhead')], []),
    ('beta a list of strings', TB, ski(BETA, 'beta: [Twin Lakes, Firm]\n'),
     [I(SKI, "beta[0] must be a row with a label: and a value: line, got 'Twin Lakes'")], []),
    ('beta a mapping (label: value pairs)', TB, ski(BETA, 'beta:\n  Trailhead: Twin Lakes\n  Snow: Firm\n'),
     [I(SKI, BETA_LIST % ({'Trailhead': 'Twin Lakes', 'Snow': 'Firm'},))], []),
    ('beta row without value', TB, ski(SNOW, '  - label: Snow\n'), [I(SKI, 'beta[1] has no value')], []),
    ('beta row without label', OK, ski(SNOW, '  - value: Firm\n'), [I(SKI, 'beta[1] has no label')], []),
    ('beta value a number', OK, ski('value: Firm', 'value: 35'),
     [I(SKI, 'beta[1].value must be text, got 35 (quote a number to keep it as written)')], []),
    ('beta value a list', OK, ski('value: Firm', 'value: [a, b]'), [I(SKI, "beta[1].value must be text, got ['a', 'b']")], []),
    ('beta row with a typo key (lable)', OK, ski('  - label: Snow', '  - lable: Snow'),
     [I(SKI, "beta[1] has no label (is 'lable' a typo for it?)")], []),
    ('beta duplicate labels', OK, ski('  - label: Snow', '  - label: Trailhead'), [], []),
    ('map a string', TB, ski_line('map: zoomed'), [I(SKI, MAP % 'zoomed')], []),
    ('map a list', TB, ski_line('map: [a, b]'), [I(SKI, MAP % (['a', 'b'],))], []),
    ('map.peaks a number', TB, ski_line('map:\n  peaks: 5'), [I(SKI, PEAKS % 5)], []),
    ('map.peaks a mapping', OK, ski_line('map:\n  peaks:\n    a: b'), [I(SKI, PEAKS % ({'a': 'b'},))], []),
    ('map unknown key (zoomm: 2)', OK, ski_line('map:\n  zoomm: 2'), [], [I(SKI, "unknown key 'zoomm' in map; nothing reads it")]),
    ('search_aliases a number', CLEAN, ski_line('search_aliases: 5'), [SAME], []),
    ('search_aliases a mapping', CLEAN, ski_line('search_aliases:\n  a: b'), [SAME], []),
    ('search_aliases list with a number', CLEAN, ski_line('search_aliases: [PCT, 2024]'), [SAME], []),
    ('card_summary a number', CLEAN, ski_line('card_summary: 5'), [SAME], []),
    ('card_summary a list', CLEAN, ski_line('card_summary: [a, b]'), [SAME], []),
    ('card_summary very long (2000 chars)', OK, ski_line('card_summary: ' + 'word ' * 400), [], []),
    ('cover_focal_x 150', CLEAN, ski_line('cover_focal_x: 150'), [SAME], []),
    ('cover_focal_y "45%"', CLEAN, ski_line('cover_focal_y: "45%"'), [SAME], []),
    ('cover_focal without cover_photo and without photos', OK, hike_line('cover_focal_x: 20'), [], []),
    ('cover_photo not declared', CLEAN, ski_line('cover_photo: photos/99.webp'), [SAME], []),
    # the one clean error that reads differently now: the new rule for a declared photo finds the missing file first
    ('cover_photo declared, file missing', CLEAN,
     lambda s: (ski_line('cover_photo: photos/02.webp')(s), s.remove(s.path(SKI, 'photos', '02.webp'))), [I(SKI, MISSING)], []),
    ('cover_photo traversal', CLEAN, ski_line('cover_photo: ../loop-hike/photos/01.webp'), [SAME], []),
    ('cover_photo on a DRAFT, not declared', CLEAN,
     lambda s: s.sub(s.index('draft-trip'), 'draft: true', 'draft: true\ncover_photo: photos/99.webp'), [SAME], []),
    ('journal_highlights unknown id', CLEAN,
     lambda s: s.sub(s.index(JOURNAL), 'kind: series', 'kind: series\njournal_highlights: [001, 999]'), [SAME], []),
    ('journal_highlights repeated', CLEAN,
     lambda s: s.sub(s.index(JOURNAL), 'kind: series', 'kind: series\njournal_highlights: [001, 1]'), [SAME], []),
    ('journal_highlights not a list', CLEAN,
     lambda s: s.sub(s.index(JOURNAL), 'kind: series', 'kind: series\njournal_highlights: 001'), [SAME], []),
    ('journal_highlights on a single-day trip', CLEAN, ski_line('journal_highlights: [01]'), [SAME], []),
    ('SERIES two days with the same day: label', CLEAN, lambda s: s.sub(s.day(JOURNAL, '002'), 'day: "2"', 'day: "1"'), [SAME], []),
    ('home.json unknown slug', CLEAN, home({'featured_slugs': [SKI, 'nope']}), [SAME], []),
    ('home.json draft slug', CLEAN, home({'featured_slugs': ['draft-trip']}), [SAME], []),
    ('home.json planned slug', CLEAN, home({'featured_slugs': ['goal-route']}), [SAME], []),
    ('home.json duplicate slug', CLEAN, home({'featured_slugs': [SKI, SKI]}), [SAME], []),
    ('home.json seven slugs', CLEAN, home({'featured_slugs': ['a', 'b', 'c', 'd', 'e', 'f', 'g']}), [SAME], []),
    ('home.json malformed JSON', CLEAN, home('{"featured_slugs": ['), [SAME], []),
    ('home.json top-level list', CLEAN, home([SKI]), [SAME], []),
    ('home.json featured_slugs a string', CLEAN, home({'featured_slugs': SKI}), [SAME], []),
    ('home.json key missing', CLEAN, home({'featured': [SKI]}),
     [SAME], [H("unknown key 'featured' (did you mean 'featured_slugs'?); nothing reads it")]),
    ('home.json item not a string', CLEAN, home({'featured_slugs': [1]}), [SAME], []),
    ('home.json unknown extra key (tick_list_slugs)', OK, home({'featured_slugs': [SKI], 'tick_list_slugs': ['nope'], 'typo_key': 1}),
     [], [H(UNKNOWN % 'tick_list_slugs'), H(UNKNOWN % 'typo_key')]),
    ('home.json slug with trailing space', CLEAN, home({'featured_slugs': ['ski-report ']}), [SAME], []),
    ('home.json missing file', OK, lambda s: s.remove(s.home),
     [], [H('the file is missing, so the home page falls back to the newest featured report; create it to choose the featured '
            'trips (see docs/CONTENT_GUIDE.md)')]),
    ('home.json empty list', OK, home({'featured_slugs': []}), [], []),
    # ---- photos, days, tracks, folders
    ('photo entry without file', OK, ski(P2, '  - w: 1200\n    h: 1600\n    alt: Skier in the couloir\n'),
     [I(SKI, 'photos[1] has no file: line (an entry starts with - file: photos/<name>)')], []),
    ('photo file missing on disk (declared) [--check]', CHK, lambda s: s.remove(s.path(SKI, 'photos', '02.webp')), [I(SKI, MISSING)], []),
    ('photo file missing on disk (declared) [plain build]', OK, lambda s: s.remove(s.path(SKI, 'photos', '02.webp')), [I(SKI, MISSING)], []),
    ('photo w/h missing', OK, ski(P2, '  - file: photos/02.webp\n    alt: Skier in the couloir\n'),
     [], [I(SKI, 'photos[1] (photos/02.webp) has no w and h, so the page cannot hold its place while it loads; record the pixel size')]),
    ('photo w only (h missing)', TB, ski(P2, '  - file: photos/02.webp\n    w: 1200\n    alt: Skier in the couloir\n'),
     [I(SKI, 'photos[1] (photos/02.webp) has w but no h; record both (the pixel size) or neither')], []),
    ('photo w a string (wide)', TB, ski('    w: 1200\n    h: 1600', '    w: wide\n    h: 1600'),
     [I(SKI, "photos[1].w (photos/02.webp) must be a positive whole number of pixels, got 'wide'")], []),
    ('photo w zero', OK, ski('    w: 1200\n    h: 1600', '    w: 0\n    h: 1600'),
     [I(SKI, 'photos[1].w (photos/02.webp) must be a positive whole number of pixels, got 0')], []),
    ('photo h zero', OK, ski('    w: 1200\n    h: 1600', '    w: 1200\n    h: 0'),
     [I(SKI, 'photos[1].h (photos/02.webp) must be a positive whole number of pixels, got 0')], []),
    ('photo alt missing', OK, ski(P2, '  - file: photos/02.webp\n    w: 1200\n    h: 1600\n'),
     [], [I(SKI, 'photos[1] (photos/02.webp) has no alt text; describe the photo in a sentence')]),
    ('cover photo alt missing (lead photo)', OK, ski('    alt: Granite spires\n', ''),
     [], [I(SKI, 'photos[0] (photos/01.webp) has no alt text; describe the photo in a sentence')]),
    ('photo alt a number', TB, ski('alt: Skier in the couloir', 'alt: 2026'), [I(SKI, 'photos[1].alt (photos/02.webp) must be text, got 2026')], []),
    ('photos a string', TB, lambda s: s.sub(s.index(SKI), photos_block(s), 'photos: photos/01.webp\n'), [I(SKI, PHOTOS % 'photos/01.webp')], []),
    ('photos a list of strings', TB, lambda s: s.sub(s.index(SKI), photos_block(s), 'photos: [photos/01.webp, photos/02.webp]\n'),
     [I(SKI, "photos[0] must be an entry with file, w, h and alt lines, got 'photos/01.webp'")], []),
    ('photos a mapping', TB, lambda s: s.sub(s.index(SKI), photos_block(s), 'photos:\n  file: photos/01.webp\n  alt: x\n'),
     [I(SKI, PHOTOS % ({'file': 'photos/01.webp', 'alt': 'x'},))], []),
    ('duplicate photo file (02 twice)', OK, ski(P2, P2 + P2),
     [], [I(SKI, 'photos[2] declares photos/02.webp again (first in index.md, photos[1]); the page shows it twice')]),
    ('photo file outside the trip folder (../loop-hike/track.gpx)', CHK, ski('file: photos/02.webp', 'file: ../loop-hike/track.gpx'),
     [I(SKI, "photos[1].file may not leave the trip folder, got '../loop-hike/track.gpx'")], []),
    ('photo file absolute (/etc/hosts)', CHK, ski('file: photos/02.webp', 'file: /etc/hosts'),
     [I(SKI, "photos[1].file must be a relative path inside the trip folder, got '/etc/hosts'")], []),
    ('photo file not under photos/ (pics/02.webp, file exists)', CHK, move_photo_out,
     [I(SKI, "photos[1].file must be a file directly in photos/ (only that folder is published), such as photos/01.webp, got 'pics/02.webp'")], []),
    ('photo on disk but not declared', OK, lambda s: write(s.path(SKI, 'photos', '99.webp'), ''),
     [], ['content/trips/ski-report/photos/99.webp: not declared under photos: in index.md or a days/NN.md, and not the .sm or .th '
          'copy of a declared photo; the build publishes it all the same']),
    ('.sm copy missing for a photo (01.sm.webp)', OK, lambda s: s.remove(s.path(SKI, 'photos', '01.sm.webp')),
     [], [I(SKI, 'photos[0] (photos/01.webp) has no 800 px copy (01.sm.webp), so phones load the full file')]),
    ('caption a list', TB, ski('caption: The spires', 'caption: [a, b]'),
     [I(SKI, "photos[0].caption (photos/01.webp) must be text, got ['a', 'b']")], []),
    ('MULTI day file with no matching GPX (02.gpx removed)', OK, lambda s: s.remove(s.path(HUT, 'days', '02.gpx')), [], []),
    ('MULTI no day has a GPX (both removed)', OK, lambda s: s.remove(s.path(HUT, 'days', '01.gpx'), s.path(HUT, 'days', '02.gpx')),
     [], [I(HUT, 'none of the 2 days has a GPX (days/NN.gpx): the page shows an empty map and offers no downloads')]),
    ('SERIES day file with no matching GPX (002.gpx removed)', OK, lambda s: s.remove(s.path(JOURNAL, 'days', '002.gpx')), [], []),
    ('MULTI orphan GPX without a day file (03.gpx)', OK, lambda s: s.gpx(s.path(HUT, 'days', '03.gpx')), [], []),
    ('MULTI two days with the same day: label', OK, day2('day: "2"', 'day: "1"'),
     [], [D(HUT, '02', "day label '1' is also the label of days/01.md; give each day its own day: line")]),
    ('MULTI one day only', OK, lambda s: s.remove(s.path(HUT, 'days', '02.gpx'), s.day(HUT, '02')), [], []),
    # a report without a track is a page without a download now (contract 2.1), so this is a warning, not an error
    ('SINGLE track.gpx missing [--check]', CHK, lambda s: s.remove(s.path(HIKE, 'track.gpx')), [], [I(HIKE, NO_TRACK)]),
    ('SINGLE track.gpx missing [plain build]', OK, lambda s: s.remove(s.path(HIKE, 'track.gpx')), [], [I(HIKE, NO_TRACK)]),
    ('SINGLE track.gpx empty file (0 bytes)', OK, lambda s: write(s.path(HIKE, 'track.gpx'), ''),
     ['content/trips/loop-hike/track.gpx: the file is empty' + A_TRACK], []),
    ('SINGLE track.gpx not XML', OK, lambda s: write(s.path(HIKE, 'track.gpx'), 'not a gpx'),
     ['content/trips/loop-hike/track.gpx: the file is not a GPX file (no <gpx> element at its start)' + A_TRACK], []),
    ('folder without index.md', OK, lambda s: os.makedirs(s.path('stray-folder')), [], []),
    ('slug with a space and capitals (folder "My Trip")', CHK, lambda s: copy_trip(s, 'My Trip'),
     [I('My Trip', FOLDER % ('My Trip', 'my-trip'))], []),
    ('slug with a quote and angle bracket (folder a"b<c)', CHK, lambda s: copy_trip(s, 'a"b<c'), [I('a"b<c', FOLDER % ('a"b<c', 'a-b-c'))], []),
]
# the three link-check-only inputs that are not content errors, and why (see the comments on their rows)
CHECK_ONLY_NOT_ERRORS = {'body link to a missing anchor on another report', 'body link to a missing anchor on its own page',
                         'SINGLE track.gpx missing [--check]'}
# the one clean error whose text is not the build's any more
CLEAN_SUPERSEDED = {'cover_photo declared, file missing'}


class GroundworkCaseTests(Fixture):

    def test_the_table_is_the_groundwork_s_187_inputs(self):
        names = [c[0] for c in CASES]
        self.assertEqual(len(names), len(set(names)), 'a case name is used twice')
        counts = {k: sum(1 for c in CASES if c[1] == k) for k in (TB, CHK, CLEAN, OK)}
        self.assertEqual(counts, {TB: 31, CHK: 18, CLEAN: 52, OK: 86})

    def test_every_input_gives_exactly_its_findings_and_never_an_exception(self):
        for name, was, mutate, errors, warns in CASES:
            with self.subTest(name):
                self.s.reset()
                mutate(self.s)
                expected = [build_error(self.s) if e is SAME else e for e in errors]
                self.assertNotIn(None, expected, 'the build accepts this input: it has no message to pass on')
                found = self.s.run()      # an exception here fails the case: run() never raises on content
                self.assertEqual(texts(checks.errors(found)), sorted(expected))
                self.assertEqual(texts(checks.warnings(found)), sorted(warns))

    def test_every_traceback_input_is_one_error(self):
        for name, was, mutate, errors, warns in CASES:
            if was == TB:
                with self.subTest(name):
                    self.assertEqual(len(errors), 1)
                    self.assertIsNot(errors[0], SAME)

    def test_every_check_only_cause_the_contract_names_is_one_error(self):
        for name, was, mutate, errors, warns in CASES:
            if was == CHK:
                with self.subTest(name):
                    self.assertEqual(len(errors), 0 if name in CHECK_ONLY_NOT_ERRORS else 1)
        self.assertEqual(sum(1 for c in CASES if c[1] == CHK and c[0] not in CHECK_ONLY_NOT_ERRORS), 15)

    def test_every_clean_error_is_the_build_s_own_message(self):
        for name, was, mutate, errors, warns in CASES:
            if was == CLEAN:
                with self.subTest(name):
                    self.assertEqual(SAME in errors, name not in CLEAN_SUPERSEDED)
            else:
                self.assertNotIn(SAME, errors, name)

    def test_the_superseded_clean_error_is_still_what_the_loader_says(self):
        # content.load_trip keeps its own message for a cover whose file is gone; checks reports the missing photo instead
        s = self.s
        ski_line('cover_photo: photos/02.webp')(s)
        s.remove(s.path(SKI, 'photos', '02.webp'))
        self.assertEqual(build_error(s), I(SKI, "cover_photo 'photos/02.webp' is declared but the file is missing from the trip folder"))
        self.assertEqual(self.errors(), [I(SKI, MISSING)])


# ---------------------------------------------------------------- the module's surface

class SurfaceTests(Fixture):

    def test_the_valid_site_has_no_error_and_no_warning(self):
        found, counts = self.s.survey()
        self.assertEqual(checks.errors(found), [])
        self.assertEqual(checks.warnings(found), [])
        self.assertEqual(texts(checks.notes(found)), sorted([
            I('draft-trip', 'no photos'), I('draft-trip', 'no place'),
            D(HUT, '01', '1 photo without a caption'), I(JOURNAL, 'no photos'),
            I(HIKE, 'no photos'), I(HIKE, 'no write-up'), I(SKI, '2 photos without a caption')]))
        self.assertEqual(counts, {'trips': 8, 'photos': 4, 'gpx': 9})

    def test_run_is_the_findings_of_survey(self):
        hike('title: Basin Loop', 'title: 2025')(self.s)
        self.assertEqual(self.s.run(), self.s.survey()[0])
        self.assertIsInstance(self.s.run(), list)

    def test_a_finding_is_level_file_and_a_text_that_starts_with_the_file(self):
        hike('title: Basin Loop', 'title: 2025')(self.s)
        self.s.remove(self.s.home)
        found = self.s.run()
        self.assertEqual({f['level'] for f in found}, {'error', 'warning', 'note'})
        for f in found:
            self.assertEqual(sorted(f), ['file', 'level', 'text'])
            self.assertTrue(f['text'].startswith(f['file'] + ': '), f)
            self.assertNotIn('\n', f['text'])
            self.assertNotIn(self.s.root, f['text'], 'a finding names content/..., never the folder that was read')
        self.assertIn({'level': 'error', 'file': 'content/trips/loop-hike/index.md', 'text': I(HIKE, 'title must be text, got 2025')}, found)

    def test_findings_are_sorted_by_file_then_level_then_text(self):
        s = self.s
        s.add(HIKE, 'zeta: 1')                       # a warning
        s.add(HIKE, 'party: [a]')                    # an error in the same file
        s.add(HIKE, 'place_: x')                     # a second warning, sorting before the first by text
        s.sub(s.index(SKI), 'title: West Couloir', 'title: 7')
        ski('route_shape: out-and-back', 'route_shape: lollipop')(s)     # a warning whose text sorts before that error's
        found = s.run()
        keys = [(f['file'], checks.LEVELS.index(f['level']), f['text']) for f in found]
        self.assertEqual(keys, sorted(keys))
        ski_s = [f for f in found if f['file'] == 'content/trips/ski-report/index.md']
        self.assertEqual([f['level'] for f in ski_s], ['error', 'warning'])
        self.assertLess(ski_s[1]['text'], ski_s[0]['text'])       # by text alone the warning would come first
        mine = [(f['level'], f['text']) for f in found if f['file'] == 'content/trips/loop-hike/index.md']
        self.assertEqual(mine[0], ('error', I(HIKE, "party must be text, got ['a']")))
        self.assertEqual([lv for lv, _ in mine], sorted([lv for lv, _ in mine], key=checks.LEVELS.index))
        self.assertLess(found.index(next(f for f in found if f['file'].startswith('content/trips/loop-hike/'))),
                        found.index(next(f for f in found if f['file'].startswith('content/trips/ski-report/'))))

    def test_errors_warnings_and_notes_split_the_list(self):
        hike('title: Basin Loop', 'title: 2025')(self.s)
        self.s.remove(self.s.home)
        found = self.s.run()
        e, w, n = checks.errors(found), checks.warnings(found), checks.notes(found)
        self.assertEqual((len(e), len(w)), (1, 1))
        self.assertEqual(len(e) + len(w) + len(n), len(found))
        self.assertEqual({f['level'] for f in e}, {'error'})
        self.assertEqual({f['level'] for f in w}, {'warning'})
        self.assertEqual({f['level'] for f in n}, {'note'})

    def test_line_puts_the_level_word_before_the_text(self):
        self.assertEqual(checks.line({'level': 'error', 'file': 'a', 'text': 'a: b'}), 'ERROR a: b')
        self.assertEqual(checks.line({'level': 'warning', 'file': 'a', 'text': 'a: b'}), 'WARNING a: b')
        self.assertEqual(checks.line({'level': 'note', 'file': 'a', 'text': 'a: b'}), 'NOTE a: b')

    def test_summary_is_one_line_with_the_counts(self):
        found, counts = self.s.survey()
        self.assertEqual(checks.summary(found, counts), 'content: 0 errors, 0 warnings, 7 notes (8 trips, 4 photos, 9 GPX files)')
        hike('title: Basin Loop', 'title: 2025')(self.s)
        self.s.remove(self.s.home)
        found, counts = self.s.survey()
        # the broken trip is not loaded, so its two notes are not made
        self.assertEqual(checks.summary(found, counts), 'content: 1 errors, 1 warnings, 5 notes (8 trips, 4 photos, 9 GPX files)')
        self.assertEqual(checks.summary([]), 'content: 0 errors, 0 warnings, 0 notes (0 trips, 0 photos, 0 GPX files)')

    def test_the_counts_are_folders_declared_photos_and_gpx_files(self):
        s = self.s
        s.gpx(s.path(HUT, 'days', '03.gpx'))                     # a GPX without a day file is still a GPX file
        os.makedirs(s.path('stray-folder'))                      # not a trip
        write(s.path(SKI, 'photos', '99.webp'), '')              # not declared
        s.sub(s.index(SKI), P2, '  - w: 1200\n    h: 1600\n')    # an entry without a file is not a photo
        self.assertEqual(s.survey()[1], {'trips': 8, 'photos': 3, 'gpx': 10})

    def test_the_defaults_are_the_checkout_s_own_folders(self):
        s = self.s
        hike('title: Basin Loop', 'title: 2025')(s)
        s.remove(s.path(SKI, 'photos', '01.th.webp'))
        os.remove(os.path.join(s.rendered, 'trips', HUT, 'meta.json'))
        s.put_home({'featured_slugs': ['nope']})
        named = s.survey()
        self.assertEqual(len(checks.errors(named[0])), 2)
        self.assertEqual(len(checks.warnings(named[0])), 2)
        with mock.patch.object(content, 'TRIPS_DIR', s.trips), mock.patch.object(curation, 'HOME_JSON', s.home), \
                mock.patch.object(content, 'RENDERED', s.rendered):
            self.assertEqual(checks.survey(today=TODAY), named)
            self.assertEqual(checks.run(today=TODAY), named[0])

    def test_the_default_day_is_today(self):
        class Day(datetime.date):
            @classmethod
            def today(cls):
                return cls(2026, 10, 10)
        hike('date: 2025-08-10', 'date: 2026-10-12')(self.s)
        with mock.patch.object(checks, 'date', Day):
            found = checks.run(self.s.trips, self.s.home, self.s.rendered)
        self.assertEqual(texts(checks.warnings(found)), [I(HIKE, 'date 2026-10-12 is in the future (today is 2026-10-10)')])

    def test_a_missing_trips_folder_is_one_error_not_an_exception(self):
        found, counts = checks.survey(os.path.join(self.s.root, 'nowhere', 'trips'), self.s.home, self.s.rendered, TODAY)
        self.assertEqual(found, [{'level': 'error', 'file': 'content/trips', 'text': 'content/trips: the folder does not exist'}])
        self.assertEqual(counts, {'trips': 0, 'photos': 0, 'gpx': 0})

    def test_an_empty_trips_folder_is_only_missing_nothing(self):
        shutil.rmtree(self.s.trips)
        os.makedirs(self.s.trips)
        self.s.put_home({'featured_slugs': []})
        self.assertEqual(self.s.survey(), ([], {'trips': 0, 'photos': 0, 'gpx': 0}))

    def test_dot_folders_and_folders_without_index_are_not_trips(self):
        s = self.s
        write(s.path('.hidden', 'index.md'), 'title: [')
        os.makedirs(s.path('stray'))
        write(os.path.join(s.trips, 'notes.txt'), 'x')
        self.assertFindings()
        self.assertEqual(s.survey()[1]['trips'], 8)

    def test_the_known_keys_are_named_constants(self):
        for key in ('title', 'activity', 'kind', 'date', 'end_date', 'stats', 'photos', 'beta', 'map', 'cover_photo', 'card_summary',
                    'search_aliases', 'journal_highlights', 'published_at', 'updated_at', 'strava_id', 'draft', 'featured'):
            self.assertIn(key, checks.INDEX_KEYS)
        for key in ('day', 'title', 'date', 'start_time', 'stats', 'photos', 'hut', 'transfer_before'):
            self.assertIn(key, checks.DAY_KEYS)
        self.assertNotIn('published_at', checks.DAY_KEYS)
        self.assertNotIn('updated_at', checks.DAY_KEYS)
        self.assertEqual(checks.PHOTO_KEYS, ('file', 'w', 'h', 'alt', 'caption'))
        self.assertEqual(checks.STATS_KEYS, ('distance_km', 'moving', 'elapsed', 'gain_m', 'loss_m', 'high_m', 'low_m'))
        self.assertEqual(checks.MAP_KEYS, ('peaks', 'places', 'water_labels'))
        self.assertEqual(checks.HOME_KEYS, ('featured_slugs',))
        self.assertEqual(checks.KINDS, ('trip', 'multi-day', 'series', 'planned'))
        self.assertEqual(checks.ROUTE_SHAPES, ('loop', 'out-and-back', 'point-to-point'))


# ---------------------------------------------------------------- one run, every file, never a traceback

class AggregationTests(Fixture):

    def test_every_broken_file_is_reported_in_one_run(self):
        s = self.s
        hike('title: Basin Loop', 'title: 2025')(s)                          # a raw value
        ski_line('cover_focal_x: 150')(s)                                    # a loader rule
        day2('date: 2024-03-02', 'date: soon')(s)                            # a day file
        s.setg('goal-idea', status='done')                                   # a sidecar
        write(s.index('draft-trip'), '---\ntitle: X\n')                      # a draft whose front matter is broken
        s.put_home({'featured_slugs': [SKI, 'nope']})                        # the manifest
        with self.assertRaises(content.ContentError):                        # the build's loader stops at the first of them
            helpers.load_dir(s.trips)
        self.assertEqual(self.errors(), sorted([
            I(HIKE, 'title must be text, got 2025'),
            I(SKI, 'cover_focal_x must be between 0 and 100, got 150'),
            D(HUT, '02', DATE % 'soon'),
            G('goal-idea', "status must be one of idea, researching, shortlisted, attempted, completed, got 'done'"),
            I('draft-trip', 'front matter: front matter is not closed with ---'),
            H("unknown slug 'nope' in featured_slugs (no content/trips/nope/index.md)")]))

    def test_several_raw_errors_in_one_file_are_all_reported(self):
        s = self.s
        hike('title: Basin Loop', 'title: 2025')(s)
        hike('place: Desolation', 'place: 9000')(s)
        hike('distance_km: 12.0', 'distance_km: far')(s)
        s.add(HIKE, 'draft: no')
        self.assertEqual(self.errors(), sorted([
            I(HIKE, 'title must be text, got 2025'), I(HIKE, 'place must be text, got 9000'),
            I(HIKE, "stats.distance_km must be a number, got 'far'"), I(HIKE, "draft must be true or false, got 'no'")]))

    def test_a_raw_error_keeps_the_loader_away_from_that_folder_only(self):
        s = self.s
        hike('title: Basin Loop', 'title: 2025')(s)
        hike_line('cover_focal_x: 150')(s)             # the loader would refuse this: it is reported once the title is fixed
        ski_line('cover_focal_x: 150')(s)
        self.assertEqual(self.errors(), sorted([I(HIKE, 'title must be text, got 2025'), I(SKI, 'cover_focal_x must be between 0 and 100, got 150')]))
        hike('title: 2025', 'title: Basin Loop')(s)
        self.assertEqual(self.errors(), sorted([I(HIKE, 'cover_focal_x must be between 0 and 100, got 150'),
                                                I(SKI, 'cover_focal_x must be between 0 and 100, got 150')]))

    def test_a_broken_trip_is_not_reported_again_by_what_points_at_it(self):
        # the ski report is featured in home.json, named by goal-done's outing and linked from the hike's write-up
        s = self.s
        s.body(HIKE, 'See [the couloir](../ski-report/).')
        ski('gain_m: 1450', 'gain_m: "1,450"')(s)
        self.assertEqual(self.errors(), [I(SKI, "stats.gain_m must be a number, got '1,450'")])
        s.sub(s.index(SKI), 'gain_m: "1,450"', 'gain_m: 1450')
        write(s.index(SKI), read(s.index(SKI)).replace('---\n', '---\ntitle: "unclosed\n', 1))
        self.assertEqual(self.errors(), [I(SKI, 'front matter: Unterminated string starting at: line 1 column 1 (char 0)')])

    def test_a_broken_planned_trip_still_counts_as_a_planned_route_for_the_manifest(self):
        s = self.s
        s.sub(s.index('goal-route'), 'activity: hike', 'activity: scramble')
        s.put_home({'featured_slugs': ['goal-route']})
        self.assertEqual(self.errors(), sorted([I('goal-route', BAD_ACT % 'scramble'),
                                                H("'goal-route' is a planned route; only published reports can be featured")]))

    def test_a_broken_draft_is_still_a_draft_to_the_manifest_and_to_links(self):
        s = self.s
        s.sub(s.index('draft-trip'), 'title: Draft', 'title: 5')
        s.put_home({'featured_slugs': ['draft-trip']})
        s.body(HIKE, '[d](../draft-trip/)')
        self.assertEqual(self.errors(), sorted([
            I('draft-trip', 'title must be text, got 5'),
            H("'draft-trip' is a draft (draft: true in its index.md); drafts cannot be featured"),
            I(HIKE, "write-up link '../draft-trip/' points at trips/draft-trip/, a draft, which has no page")]))

    def test_an_exception_in_the_loader_is_a_finding_and_the_other_trips_are_still_checked(self):
        real = content.load_trip

        def load(folder):
            if os.path.basename(folder) == HIKE:
                raise RuntimeError('boom')
            return real(folder)
        ski('title: West Couloir', 'title: 7')(self.s)
        with mock.patch.object(content, 'load_trip', load):
            found = self.s.run()
        self.assertEqual(texts(checks.errors(found)), sorted([I(HIKE, 'could not be read (RuntimeError: boom)'), I(SKI, 'title must be text, got 7')]))
        self.assertEqual(checks.warnings(found), [])

    def test_an_exception_in_a_rule_is_a_finding_about_that_folder(self):
        real = checks._check_raw

        def raw(rec, out):
            if rec['slug'] == HIKE:
                raise KeyError('oops')
            return real(rec, out)
        self.s.remove(self.s.home)
        with mock.patch.object(checks, '_check_raw', raw):
            found = self.s.run()
        self.assertEqual(texts(checks.errors(found)), [I(HIKE, "could not be checked (KeyError: 'oops')")])
        self.assertEqual(len(checks.warnings(found)), 1)      # the manifest warning: the run went on

    def test_an_exception_in_a_site_wide_check_does_not_silence_the_others(self):
        self.s.body(SKI, '[x](../nope/)')
        self.s.remove(self.s.home)
        with mock.patch.object(checks, '_outing_findings', side_effect=ValueError('bad')):
            found = self.s.run()
        self.assertEqual(texts(checks.errors(found)), sorted(['content/trips: could not be checked (ValueError: bad)',
                                                              I(SKI, NO_PAGE % ('../nope/', 'nope', 'nope'))]))
        self.assertEqual(len(checks.warnings(found)), 1)
        with mock.patch.object(checks.curation, 'load_manifest', side_effect=OSError('denied')):
            found = self.s.run()
        self.assertIn('content/home.json: could not be checked (OSError: denied)', texts(checks.errors(found)))

    def test_a_file_that_is_not_utf8_is_one_error_naming_it(self):
        s = self.s
        write(s.index(HIKE), b'---\ntitle: Caf\xe9\n---\n', 'wb')
        write(s.day(HUT, '02'), b'\xff\xfe\x00', 'wb')
        errs = self.errors()
        self.assertEqual(len(errs), 2)
        self.assertTrue(errs[0].startswith(D(HUT, '02', 'could not be read (UnicodeDecodeError: ')), errs)
        self.assertTrue(errs[1].startswith(I(HIKE, 'could not be read (UnicodeDecodeError: ')), errs)

    def test_a_file_that_cannot_be_opened_is_named_without_the_local_path(self):
        s = self.s
        s.remove(s.index(HIKE), s.path(SKI, 'track.gpx'))
        os.makedirs(s.index(HIKE))               # a folder where the file should be
        os.makedirs(s.path(SKI, 'track.gpx'))
        found = s.run()
        self.assertEqual(texts(checks.errors(found)), sorted([
            I(HIKE, 'could not be read (IsADirectoryError: Is a directory)'),
            'content/trips/ski-report/track.gpx: the file could not be read (IsADirectoryError: Is a directory)' + A_TRACK]))
        for f in found:
            self.assertNotIn(s.root, f['text'])

    def test_an_exception_s_message_stays_on_one_line(self):
        with mock.patch.object(content, 'load_trip', side_effect=RuntimeError('first line\n  second line\n')):
            found = self.s.run()
        self.assertIn(I(HIKE, 'could not be read (RuntimeError: first line second line)'), texts(checks.errors(found)))
        self.assertEqual([f for f in found if '\n' in f['text']], [])

    def test_a_day_file_s_broken_front_matter_reads_as_the_loader_writes_it(self):
        s = self.s
        write(s.day(HUT, '02'), '---\ntitle: Col\n')
        self.assertEqual(self.errors(), [build_error(s)])
        self.assertEqual(self.errors(), ['content/trips/hut-tour/days/02.md: front matter: front matter is not closed with ---'])


class PassThroughTests(Fixture):
    """The existing messages, byte for byte: whatever the build's loading code raises is what checks reports."""

    def same(self, mutate):
        mutate(self.s)
        was = build_error(self.s)
        self.assertIsNotNone(was)
        self.assertEqual(self.errors(), [was])
        return was

    def test_cover_and_focal_messages(self):
        self.assertEqual(self.same(ski_line('cover_photo: ../loop-hike/photos/01.webp')),
                         I(SKI, "cover_photo may not leave the trip folder, got '../loop-hike/photos/01.webp'"))

    def test_cover_not_declared(self):
        self.assertEqual(self.same(ski_line('cover_photo: photos/99.webp')),
                         I(SKI, "cover_photo 'photos/99.webp' is not a photo declared under photos: in index.md or a days/NN.md"))

    def test_focal_not_a_number(self):
        self.assertEqual(self.same(ski_line('cover_focal_y: "45%"')), I(SKI, "cover_focal_y must be a number from 0 to 100, got '45%'"))

    def test_card_summary_reads_the_same_from_the_raw_check_as_from_the_loader(self):
        ski_line('card_summary: 5')(self.s)
        with self.assertRaises(content.ContentError) as cm:
            content.load_trip(self.s.path(SKI))
        self.assertEqual(self.errors(), [str(cm.exception)])
        self.assertEqual(str(cm.exception), I(SKI, 'card_summary must be text, got 5'))

    def test_search_aliases(self):
        self.assertEqual(self.same(ski_line('search_aliases: [PCT, 2024]')),
                         I(SKI, "search_aliases must be a list of names such as [PCT], got ['PCT', 2024]"))

    def test_journal_highlights(self):
        self.assertEqual(self.same(lambda s: s.sub(s.index(JOURNAL), 'kind: series', 'kind: series\njournal_highlights: [001, 999]')),
                         I(JOURNAL, 'journal_highlights names day 999, which is not a days/NNN.md of this trip'))

    def test_journal_day_anchor(self):
        self.assertEqual(self.same(lambda s: s.sub(s.day(JOURNAL, '002'), 'day: "2"', 'day: "1"')),
                         D(JOURNAL, '002', "day: '1' gives the same page anchor (#day-1) as days/001.md; give each day its own label"))

    def test_goal_json_messages_name_goal_json(self):
        was = self.same(goal('goal-idea', status='done'))
        self.assertEqual(was, G('goal-idea', "status must be one of idea, researching, shortlisted, attempted, completed, got 'done'"))
        self.assertEqual(checks.errors(self.s.run())[0]['file'], 'content/trips/goal-idea/goal.json')

    def test_goal_sidecar_beside_a_report(self):
        was = self.same(lambda s: shutil.copy(s.path('goal-idea', 'goal.json'), s.path(HIKE, 'goal.json')))
        self.assertEqual(was, G(HIKE, 'only a kind: planned trip can carry a goal sidecar (this trip is kind: trip)'))

    def test_goal_checksum(self):
        was = self.same(lambda s: write(s.path('goal-route', 'track.gpx'), gf.SINGLE + '<!-- edited -->\n'))
        self.assertIn('track.gpx has changed since it was imported (SHA-256 ', was)

    def test_manifest_messages_name_home_json(self):
        was = self.same(home({'featured_slugs': [SKI, SKI]}))
        self.assertEqual(was, H("duplicate slug 'ski-report' in featured_slugs"))
        self.assertEqual(checks.errors(self.s.run())[0]['file'], 'content/home.json')

    def test_manifest_json_error(self):
        was = self.same(home('{"featured_slugs": ['))
        self.assertTrue(was.startswith('content/home.json: not valid JSON ('), was)

    def test_draft_named_in_the_manifest(self):
        self.assertEqual(self.same(home({'featured_slugs': ['draft-trip']})),
                         H("'draft-trip' is a draft (draft: true in its index.md); drafts cannot be featured"))

    def test_every_bad_outing_is_reported_where_the_build_stops_at_the_first(self):
        s = self.s
        s.setg('goal-done', outings=[outing(report_slug='nope-one', outcome='attempted'), outing(report_slug='goal-route'),
                                     outing(report_slug=SKI)])
        s.setg('goal-idea', status='attempted', outings=[outing(report_slug='draft-trip', outcome='attempted')])
        errs = self.errors()
        self.assertIn(build_error(s), errs)
        self.assertEqual(errs, sorted([G('goal-done', "outing report_slug 'nope-one' is not a published report"),
                                       G('goal-done', "outing report_slug 'goal-route' is not a published report (it is a planned route)"),
                                       G('goal-idea', "outing report_slug 'draft-trip' is not a published report")]))

    def test_a_draft_goal_s_outings_are_not_looked_up_as_in_the_build(self):
        s = self.s
        s.sub(s.index('goal-done'), 'kind: planned', 'kind: planned\ndraft: true')
        s.setg('goal-done', outings=[outing(report_slug='nope')])
        self.assertIsNone(build_error(s))
        self.assertFindings()

    @unittest.skipUnless(hasattr(content, '_today'), 'this checkout has no published_at yet')
    def test_published_at_is_judged_against_the_day_the_run_was_given(self):
        s = self.s
        s.add(SKI, 'published_at: 2026-10-09')
        clock = content._today
        self.assertFindings(today=datetime.date(2026, 10, 10))
        self.assertIs(content._today, clock, 'the loader has its own clock back after the run')
        # nine days earlier that date is still to come: the loader says so itself when its clock reads that day
        with mock.patch.object(content, '_today', lambda: datetime.date(2026, 10, 1)):
            with self.assertRaises(content.ContentError) as cm:
                content.load_trip(s.path(SKI))
        self.assertIn('published_at', str(cm.exception))
        self.assertFindings(errors=[str(cm.exception)], today=datetime.date(2026, 10, 1))
        self.assertIs(content._today, clock)

    def test_published_at_and_updated_at_are_known_keys_of_index_md_only(self):
        s = self.s
        s.add(SKI, 'published_at: 2026-02-01')
        s.add(SKI, 'updated_at: 2026-03-01')
        day2('date: 2024-03-02', 'date: 2024-03-02\npublished_at: 2026-02-01\nupdated_at: 2026-03-01')(s)
        self.assertFindings(warnings=[D(HUT, '02', UNKNOWN % 'published_at'), D(HUT, '02', UNKNOWN % 'updated_at')])


# ---------------------------------------------------------------- dates

class DateTests(Fixture):

    def test_as_date_takes_a_real_day_written_year_month_day(self):
        d = datetime.date
        self.assertEqual(checks._as_date('2025-08-10'), d(2025, 8, 10))
        self.assertEqual(checks._as_date('2024-02-29'), d(2024, 2, 29))
        self.assertEqual(checks._as_date(d(2025, 8, 10)), d(2025, 8, 10))
        for bad in ('2025-02-29', '2025-13-01', '2025-00-10', '2025-08-00', '2025-8-10', '25-08-10', '20250810', 20250810, 2025,
                    '2025-08-10 ', ' 2025-08-10', '2025-08-10T07:00', '2025-08-10\n', '8/10/2025', 'last summer', '', None, True,
                    ['2025-08-10'], {'y': 2025}, 2025.0810, datetime.datetime(2025, 8, 10, 7, 0)):
            with self.subTest(value=bad):
                self.assertIsNone(checks._as_date(bad))

    def test_a_compact_date_is_refused_on_every_python(self):
        # date.fromisoformat reads '20250810' on 3.12 and not on 3.9; the validator must not depend on which runs it
        hike('date: 2025-08-10', 'date: 20250810')(self.s)
        self.assertFindings(errors=[I(HIKE, DATE % 20250810)])
        hike('date: 20250810', 'date: "20250810"')(self.s)
        self.assertFindings(errors=[I(HIKE, DATE % '20250810')])

    def test_end_date_and_day_dates_are_held_to_the_same_form(self):
        s = self.s
        s.sub(s.index(JOURNAL), 'end_date: 2024-09-21', 'end_date: Sept 21')
        s.sub(s.day(JOURNAL, '002'), 'date: 2024-04-23', 'date: [2024, 4, 23]')
        self.assertFindings(errors=[I(JOURNAL, "end_date must be a date written YYYY-MM-DD, got 'Sept 21'"),
                                    D(JOURNAL, '002', DATE % ([2024, 4, 23],))])

    def test_an_empty_date_line_is_no_date_at_all(self):
        hike('date: 2025-08-10', 'date:')(self.s)
        self.assertFindings(warnings=[I(HIKE, 'no date (add date: YYYY-MM-DD): the page, its card and the feed show none and the trip sorts last')])

    def test_end_date_equal_to_date_is_fine_and_one_day_before_is_not(self):
        hike('date: 2025-08-10', 'date: 2025-08-10\nend_date: 2025-08-10')(self.s)
        self.assertFindings()
        hike('end_date: 2025-08-10', 'end_date: 2025-08-09')(self.s)
        self.assertFindings(errors=[I(HIKE, 'end_date 2025-08-09 is before date 2025-08-10')])

    def test_end_date_without_date_is_held_against_the_first_day(self):
        s = self.s
        s.add(HUT, 'end_date: 2024-03-01')        # the first day is 2024-03-01: the same day is not an error
        late = D(HUT, '02', "date 2024-03-02 is after the trip's end_date 2024-03-01 (index.md), so the page's dates end before this day")
        self.assertFindings(warnings=[late])      # but the second day is then past the stated end, and that is said
        s.sub(s.index(HUT), 'end_date: 2024-03-01', 'end_date: 2024-02-29')
        self.assertFindings(errors=[I(HUT, "end_date 2024-02-29 is before the first day's date 2024-03-01 (days/01.md)")])
        s.sub(s.day(HUT, '01'), 'date: 2024-03-01', 'date: never')    # an unreadable first day: only that is reported
        self.assertFindings(errors=[D(HUT, '01', DATE % 'never')])

    def test_end_date_is_not_compared_with_a_date_that_is_itself_wrong(self):
        hike('date: 2025-08-10', 'date: soon\nend_date: 2025-01-01')(self.s)
        self.assertFindings(errors=[I(HIKE, DATE % 'soon')])
        self.s.sub(self.s.index(HUT), 'kind: multi-day', 'kind: multi-day\ndate: soon\nend_date: 2024-02-01')    # nor with the first day then
        self.assertFindings(errors=[I(HIKE, DATE % 'soon'), I(HUT, DATE % 'soon')])

    def test_a_date_after_the_last_day_is_a_warning(self):
        s = self.s
        s.add(HUT, 'date: 2024-03-05')
        self.assertFindings(warnings=[I(HUT, "date 2024-03-05 is after the last day's date 2024-03-02 (days/02.md), so the page "
                                             "would end the trip before it starts")])
        s.sub(s.index(HUT), 'date: 2024-03-05', 'date: 2024-03-02')
        self.assertFindings()
        s.sub(s.index(HUT), 'date: 2024-03-02', 'date: 2024-03-05\nend_date: 2024-03-06')    # an end_date of its own settles it
        self.assertFindings()

    def test_the_last_day_is_the_last_file_whatever_its_date(self):
        # the page ends the trip on the last day file's date: days 1 and 2 swapped, a date between the two is after "the end"
        s = self.s
        s.sub(s.day(HUT, '01'), 'date: 2024-03-01', 'date: 2024-03-09')
        s.add(HUT, 'date: 2024-03-05')
        self.assertFindings(warnings=[
            D(HUT, '02', 'date 2024-03-02 is before the day ahead of it (days/01.md, 2024-03-09); days are shown in file order'),
            I(HUT, "date 2024-03-05 is after the last day's date 2024-03-02 (days/02.md), so the page would end the trip before it "
                   "starts")])
        s.sub(s.day(HUT, '02'), 'date: 2024-03-02\n', '')      # an undated last day: the page has no end to print
        self.assertFindings()

    def test_the_future_starts_two_days_from_today(self):
        s = self.s
        hike('date: 2025-08-10', 'date: 2026-10-10')(s)
        self.assertFindings()
        hike('date: 2026-10-10', 'date: 2026-10-11')(s)      # tomorrow: somewhere it already is
        self.assertFindings()
        hike('date: 2026-10-11', 'date: 2026-10-12')(s)
        self.assertFindings(warnings=[I(HIKE, 'date 2026-10-12 is in the future (today is 2026-10-10)')])
        self.assertFindings(today=datetime.date(2026, 10, 11))
        self.assertEqual(checks.FUTURE_DAYS, 1)

    def test_a_future_end_date_and_a_future_day_are_named_by_their_own_file(self):
        s = self.s
        s.sub(s.index(JOURNAL), 'end_date: 2024-09-21', 'end_date: 2027-09-21')
        s.sub(s.day(JOURNAL, '003'), 'date: 2024-04-24', 'date: 2027-04-24')
        self.assertFindings(warnings=[I(JOURNAL, 'end_date 2027-09-21 is in the future (today is 2026-10-10)'),
                                      D(JOURNAL, '003', 'date 2027-04-24 is in the future (today is 2026-10-10)')])

    def test_a_report_dated_only_by_its_days_has_a_date(self):
        self.assertNotIn('\ndate: ', read(self.s.index(HUT)))
        self.assertFindings()
        s = self.s
        s.sub(s.day(HUT, '01'), 'date: 2024-03-01\n', '')
        s.sub(s.day(HUT, '02'), 'date: 2024-03-02\n', '')
        self.assertFindings(warnings=[I(HUT, 'no date (add date: YYYY-MM-DD): the page, its card and the feed show none and the trip sorts last')])

    def test_a_planned_route_needs_no_date_and_is_told_when_it_has_one(self):
        s = self.s
        self.assertNotIn('\ndate: ', read(s.index('goal-idea')))
        self.assertFindings()
        s.add('goal-idea', 'date: 2099-07-01')      # only the one warning: a goal's date is not judged as a trip's
        self.assertFindings(warnings=[I('goal-idea', "a planned route has a date: line (2099-07-01); a goal has no date, and an "
                                                     "outing's date goes in goal.json")])

    def test_days_in_order_with_gaps_and_undated_days_are_fine(self):
        s = self.s
        s.sub(s.day(JOURNAL, '002'), 'date: 2024-04-23\n', '')
        s.sub(s.day(JOURNAL, '003'), 'date: 2024-04-24', 'date: 2024-05-30')
        self.assertFindings()
        s.sub(s.day(JOURNAL, '003'), 'date: 2024-05-30', 'date: 2024-04-21')     # before day 1, across the undated day
        self.assertFindings(warnings=[D(JOURNAL, '003', 'date 2024-04-21 is before the day ahead of it (days/001.md, 2024-04-22); '
                                                        'days are shown in file order')])

    def test_every_day_dated_before_an_earlier_one_is_named(self):
        s = self.s
        s.sub(s.day(JOURNAL, '002'), 'date: 2024-04-23', 'date: 2024-04-10')
        s.sub(s.day(JOURNAL, '003'), 'date: 2024-04-24', 'date: 2024-04-15')      # after day 2, still before day 1
        early = 'date %s is before the day ahead of it (days/001.md, 2024-04-22); days are shown in file order'
        self.assertFindings(warnings=[D(JOURNAL, '002', early % '2024-04-10'), D(JOURNAL, '003', early % '2024-04-15')])

    def test_two_days_on_one_date_are_in_order(self):
        day2('date: 2024-03-02', 'date: 2024-03-01')(self.s)
        self.assertFindings()

    def test_start_time(self):
        for ok in ('"06:10"', '"00:00"', '"23:59"', '"6:10"', '06:10'):
            with self.subTest(ok=ok):
                self.s.reset()
                ski('start_time: "06:10"', 'start_time: ' + ok)(self.s)
                self.assertFindings()
        for bad, got in (('"24:00"', '24:00'), ('"12:60"', '12:60'), ('"6:1"', '6:1'), ('"06:10:30"', '06:10:30'), ('6', 6), ('6.5', 6.5),
                         ('"-1:00"', '-1:00'), ('"6h10"', '6h10'), ('[6, 10]', [6, 10]), ('true', True)):
            with self.subTest(bad=bad):
                self.s.reset()
                ski('start_time: "06:10"', 'start_time: ' + bad)(self.s)
                self.assertFindings(errors=[I(SKI, CLOCK % (got,))])

    def test_a_day_s_start_time_is_checked_in_its_own_file(self):
        day2('date: 2024-03-02', 'date: 2024-03-02\nstart_time: noon')(self.s)
        self.assertFindings(errors=[D(HUT, '02', CLOCK % 'noon')])


# ---------------------------------------------------------------- identity: folder, title, activity, kind, flags

class IdentityTests(Fixture):

    def test_folder_names(self):
        for name in ('a', '3k-in-3-hours', 'tallac-2026-09-24', 'x1'):
            with self.subTest(ok=name):
                self.s.reset()
                copy_trip(self.s, name)
                self.assertEqual(self.errors(), [])
        for name, fix in (('Loop', 'loop'), ('a--b', 'a-b'), ('-a', 'a'), ('a-', 'a'), ('a_b', 'a-b'), ('a.b', 'a-b'), ('trip 2', 'trip-2')):
            with self.subTest(bad=name):
                self.s.reset()
                copy_trip(self.s, name)
                self.assertEqual(self.errors(), [I(name, FOLDER % (name, fix))])

    def test_a_folder_name_with_nothing_usable_gets_no_suggestion(self):
        copy_trip(self.s, '___')
        self.assertEqual(self.errors(), [I('___', "the folder name '___' cannot be a page address: use lower-case letters, digits and "
                                                  "single dashes")])

    def test_a_badly_named_folder_is_still_checked_inside(self):
        copy_trip(self.s, 'My Trip')
        self.s.sub(self.s.index('My Trip'), 'title: Basin Loop', 'title: 5')
        self.assertEqual(self.errors(), sorted([I('My Trip', FOLDER % ('My Trip', 'my-trip')), I('My Trip', 'title must be text, got 5')]))

    def test_title(self):
        for value in ('""', '"   "'):
            with self.subTest(value=value):
                self.s.reset()
                hike('title: Basin Loop', 'title: ' + value)(self.s)
                self.assertFindings(errors=[I(HIKE, NO_TITLE)])
        for value, got in (('true', True), ('1.5', 1.5)):
            with self.subTest(value=value):
                self.s.reset()
                hike('title: Basin Loop', 'title: ' + value)(self.s)
                self.assertFindings(errors=[I(HIKE, 'title must be text, got %r' % (got,))])
        self.s.reset()
        hike('title: Basin Loop', 'title: "2025"')(self.s)      # quoted, a number is a title
        self.assertFindings()

    def test_activity(self):
        self.assertEqual(ACTS, ', '.join(content.ACTIVITIES))
        for act in content.ACTIVITIES:
            with self.subTest(act=act):
                self.s.reset()
                hike('activity: hike', 'activity: ' + act)(self.s)
                self.assertEqual(self.errors(), [])
        for value, got in (('[hike, ski]', ['hike', 'ski']), ('5', 5), ('true', True), ('" hike"', ' hike')):
            with self.subTest(value=value):
                self.s.reset()
                hike('activity: hike', 'activity: ' + value)(self.s)
                self.assertFindings(errors=[I(HIKE, BAD_ACT % (got,))])

    def test_kind(self):
        s = self.s
        s.add(HIKE, 'kind: trip')           # the default, spelled out: content.load_trip takes it
        self.assertFindings()
        self.assertEqual(content.load_trip(s.path(HIKE))['kind'], 'trip')
        for value, got in (('[multi-day]', ['multi-day']), ('5', 5), ('Multi-day', 'Multi-day'), ('multiday', 'multiday')):
            with self.subTest(value=value):
                self.s.reset()
                self.s.add(HIKE, 'kind: ' + value)
                self.assertFindings(errors=[I(HIKE, "kind must be one of multi-day, series, planned (leave the line out for a "
                                                    "single-day report), got %r" % (got,))])

    def test_kind_against_the_day_files(self):
        s = self.s
        s.sub(s.index(HUT), 'kind: multi-day', 'kind: series')      # day files under either day kind
        self.assertEqual(self.errors(), [])
        s.sub(s.index(HUT), 'kind: series', 'kind: trip')
        self.assertFindings(errors=[I(HUT, "days/ holds 2 day files but kind is 'trip'; day files belong to kind: multi-day (or "
                                           "kind: series for a journal): change the kind or remove days/")])
        s.remove(s.day(HUT, '02'), s.path(HUT, 'days', '02.gpx'))
        self.assertFindings(errors=[I(HUT, "days/ holds 1 day file but kind is 'trip'; day files belong to kind: multi-day (or "
                                           "kind: series for a journal): change the kind or remove days/")])
        s.sub(s.index(HUT), 'kind: trip\n', '')
        self.assertFindings(errors=[I(HUT, 'days/ holds 1 day file but there is no kind: line; add kind: multi-day (or kind: series '
                                           'for a journal)')])

    def test_an_empty_days_folder_or_gpx_only_days_are_no_day_files(self):
        s = self.s
        os.makedirs(s.path(HIKE, 'days'))
        self.assertFindings()
        s.gpx(s.path(HIKE, 'days', '01.gpx'))
        write(s.path(HIKE, 'days', '.01.md'), 'x')
        self.assertFindings()
        s.add(HIKE, 'kind: multi-day')
        self.assertFindings(errors=[I(HIKE, NO_DAYS % 'multi-day')])

    def test_draft_and_featured_take_true_or_false_only(self):
        for key in ('draft', 'featured'):
            for value, got in (('yes', 'yes'), ('1', 1), ('0', 0), ('"true"', 'true'), ('[true]', [True])):
                with self.subTest(key=key, value=value):
                    self.s.reset()
                    self.s.add(HIKE, '%s: %s' % (key, value))
                    self.assertFindings(errors=[I(HIKE, '%s must be true or false, got %r' % (key, got))])
            for value in ('true', 'false', 'True', 'False', ''):
                with self.subTest(key=key, value=value):
                    self.s.reset()
                    self.s.add(HIKE, '%s: %s' % (key, value))
                    self.assertEqual(self.errors(), [])

    def test_a_day_s_transfer_before_takes_true_or_false_only(self):
        day2('date: 2024-03-02', 'date: 2024-03-02\ntransfer_before: no')(self.s)
        self.assertFindings(errors=[D(HUT, '02', "transfer_before must be true or false, got 'no'")])
        day2('transfer_before: no', 'transfer_before: true')(self.s)
        self.assertFindings()


# ---------------------------------------------------------------- types of the older fields

class TypeTests(Fixture):

    def test_text_fields(self):
        self.assertEqual(checks.TEXT_FIELDS, ('place', 'region', 'party', 'route_shape', 'subtype', 'timezone', 'card_summary'))
        for key in checks.TEXT_FIELDS:
            for value, got in (('5', 5), ('[a, b]', ['a', 'b']), ('true', True)):
                with self.subTest(key=key, value=value):
                    self.s.reset()
                    self.s.add('draft-trip', '%s: %s' % (key, value))
                    # and nothing else: a route_shape or subtype of the wrong type is not also "not one of ..."
                    self.assertFindings(errors=[I('draft-trip', '%s must be text, got %r' % (key, got))])
        for key in checks.TEXT_FIELDS:
            with self.subTest(key=key, value='empty'):
                self.s.reset()
                self.s.add('draft-trip', '%s:' % key)
                self.assertEqual(self.errors(), [])

    def test_a_day_s_title_and_hut_are_text(self):
        s = self.s
        s.sub(s.day(HUT, '01'), 'title: Approach', 'title: 2024')
        s.sub(s.day(HUT, '02'), 'title: Col', 'title: Col\nhut: [Cabane, Refuge]')
        self.assertFindings(errors=[D(HUT, '01', 'title must be text, got 2024'), D(HUT, '02', "hut must be text, got ['Cabane', 'Refuge']")])

    def test_stats_numbers(self):
        self.assertEqual(checks.STATS_NUMBERS, ('distance_km', 'gain_m', 'loss_m', 'high_m', 'low_m'))
        for key in checks.STATS_NUMBERS:
            for value, got in (('"12"', '12'), ('[1]', [1]), ('true', True), ('12 km', '12 km')):
                with self.subTest(key=key, value=value):
                    self.s.reset()
                    hike(HIKE_STATS, 'stats:\n  %s: %s' % (key, value))(self.s)
                    self.assertFindings(errors=[I(HIKE, 'stats.%s must be a number, got %r' % (key, got))])
            for value in ('12', '12.5', '0'):
                with self.subTest(key=key, value=value):
                    self.s.reset()
                    hike(HIKE_STATS, 'stats:\n  %s: %s' % (key, value))(self.s)
                    self.assertFindings()

    def test_stats_signs(self):
        # a distance, a gain and a loss are never negative; a high or a low point can lie below sea level
        for key, value, wrong in (('gain_m', -600, True), ('loss_m', -600, True), ('distance_km', -0.1, True), ('low_m', -86, False),
                                  ('high_m', -12, False)):
            with self.subTest(key=key, value=value):
                self.s.reset()
                hike(HIKE_STATS, 'stats:\n  %s: %r' % (key, value))(self.s)
                self.assertFindings(errors=[I(HIKE, 'stats.%s cannot be negative, got %r' % (key, value))] if wrong else [])

    def test_stats_times(self):
        for key in ('moving', 'elapsed'):
            old = '%s: "%s"' % (key, {'moving': '6:10', 'elapsed': '8:30'}[key])
            for ok in ('"0:05"', '"6:10:30"', '"26:00"', '"6:5"', '6', '0', '"6"'):
                with self.subTest(key=key, ok=ok):
                    self.s.reset()
                    ski(old, '%s: %s' % (key, ok))(self.s)
                    self.assertFindings()
                    content.load_trip(self.s.path(SKI))      # and the loader reads what the check let through
            for bad, got in (('6.5', 6.5), ('true', True), ('"-6:10"', '-6:10'), ('-6', -6), ('"6:75"', '6:75'), ('"6:10:99"', '6:10:99'),
                             ('"6:"', '6:'), ('"6:10:30:5"', '6:10:30:5'), ('"6h 10m"', '6h 10m'), ('[6, 10]', [6, 10])):
                with self.subTest(key=key, bad=bad):
                    self.s.reset()
                    ski(old, '%s: %s' % (key, bad))(self.s)
                    self.assertFindings(errors=[I(SKI, 'stats.%s must be a time written H:MM such as "6:10", got %r' % (key, got))])

    def test_empty_stats_and_stats_on_a_goal(self):
        s = self.s
        hike(HIKE_STATS, 'stats:')(s)
        self.assertFindings()
        s.sub(s.index('goal-route'), 'distance_km: 9.0', 'distance_km: about nine')
        self.assertFindings(errors=[I('goal-route', "stats.distance_km must be a number, got 'about nine'")])

    def test_beta_rows(self):
        s = self.s
        ski('  - label: Snow', '  - label: 35')(s)
        self.assertFindings(errors=[I(SKI, 'beta[1].label must be text, got 35 (quote a number to keep it as written)')])
        ski('  - label: 35', '  - label: ""')(s)
        self.assertFindings(errors=[I(SKI, 'beta[1] has no label')])
        ski('  - label: ""\n    value: Firm', '  - label: Grade\n    value: 5.10')(s)        # a grade read as the number 5.1
        self.assertFindings(errors=[I(SKI, 'beta[1].value must be text, got 5.1 (quote a number to keep it as written)')])
        ski('value: 5.10', 'value: "5.10"')(s)
        self.assertFindings()
        ski('    value: "5.10"\n', '    value: true\n')(s)
        self.assertFindings(errors=[I(SKI, 'beta[1].value must be text, got True')])
        ski(BETA.split('  - label: Snow')[0], 'beta:\n  - label: Trailhead\n    value: Twin Lakes\n  -\n')(s)
        self.assertEqual(len(self.errors()), 2)       # the empty row, and the bad value after it

    def test_an_empty_beta_and_a_row_missing_both_lines(self):
        s = self.s
        ski(BETA, 'beta:\n')(s)
        self.assertFindings()
        ski('beta:\n', 'beta:\n  - note: Firm snow\n')(s)
        self.assertFindings(errors=[I(SKI, 'beta[0] has no label'), I(SKI, 'beta[0] has no value')])

    def test_map_peaks(self):
        for ok in ('peaks: Mount Tallac', 'peaks: [Mount Tallac, Dicks Peak]', 'peaks: []', 'peaks:',
                   'places: 5', 'water_labels: nope'):          # render.py's own business, left alone here
            with self.subTest(ok=ok):
                self.s.reset()
                ski_line('map:\n  ' + ok)(self.s)
                self.assertFindings()
        for bad, got in (('peaks: [Mount Tallac, 9738]', ['Mount Tallac', 9738]), ('peaks: true', True), ('peaks: 9738.5', 9738.5)):
            with self.subTest(bad=bad):
                self.s.reset()
                ski_line('map:\n  ' + bad)(self.s)
                self.assertFindings(errors=[I(SKI, PEAKS % (got,))])


# ---------------------------------------------------------------- photos

class PhotoTests(Fixture):

    def test_a_path_with_a_dot_or_a_doubled_slash_still_names_the_file(self):
        for form in ('./photos/02.webp', 'photos//02.webp', 'photos/./02.webp'):
            with self.subTest(form=form):
                self.s.reset()
                ski('file: photos/02.webp', 'file: ' + form)(self.s)
                self.assertEqual(self.errors(), [])

    def test_a_space_around_the_name_is_part_of_the_name(self):
        # the pages write the value into their links as it is, so 'photos/02.webp ' is a file that is not there
        ski('file: photos/02.webp', 'file: "photos/02.webp "')(self.s)
        self.assertEqual(self.errors(), [I(SKI, "photos[1].file 'photos/02.webp ' is missing from the trip folder")])

    def test_paths_the_build_cannot_publish(self):
        direct = 'must be a file directly in photos/ (only that folder is published), such as photos/01.webp'
        for value, wrong in (('photos/sub/02.webp', direct), ('02.webp', direct), ('photos', direct), ('Photos/02.webp', direct),
                             ('photos/../photos/02.webp', 'may not leave the trip folder'), ('..', 'may not leave the trip folder'),
                             ('.', 'may not leave the trip folder'), ('"photos\\\\02.webp"', 'must be a relative path inside the trip folder'),
                             ('//cdn.example/02.webp', 'must be a relative path inside the trip folder')):
            with self.subTest(value=value):
                self.s.reset()
                ski('file: photos/02.webp', 'file: ' + value)(self.s)
                got = json.loads(value) if value.startswith('"') else value
                self.assertEqual(self.errors(), [I(SKI, 'photos[1].file %s, got %r' % (wrong, got))])

    def test_a_file_that_is_not_text(self):
        for value, got in (('5', 5), ('[photos/02.webp]', ['photos/02.webp']), ('true', True)):
            with self.subTest(value=value):
                self.s.reset()
                ski('file: photos/02.webp', 'file: ' + value)(self.s)
                self.assertFindings(errors=[I(SKI, 'photos[1].file must be a path such as photos/01.webp, got %r' % (got,))])
        for empty in ('file:', 'file: ""'):
            with self.subTest(empty=empty):
                self.s.reset()
                ski('file: photos/02.webp', empty)(self.s)
                self.assertFindings(errors=[I(SKI, 'photos[1] has no file: line (an entry starts with - file: photos/<name>)')])

    def test_the_name_must_match_the_file_exactly(self):
        # macOS finds photos/02.WEBP for photos/02.webp; the published site (Linux) does not
        ski('file: photos/02.webp', 'file: photos/02.WEBP')(self.s)
        self.assertEqual(self.errors(), [I(SKI, "photos[1].file 'photos/02.WEBP' is missing from the trip folder")])

    def test_an_accented_name_matches_in_either_unicode_form(self):
        s = self.s
        composed, decomposed = 'caf\u00e9.webp', 'cafe\u0301.webp'
        for on_disk, declared in ((composed, decomposed), (decomposed, composed)):
            with self.subTest(on_disk=on_disk):
                self.s.reset()
                s = self.s
                for suffix in ('', '.sm', '.th'):
                    base, ext = os.path.splitext(on_disk)
                    os.rename(s.path(SKI, 'photos', '02' + suffix + '.webp'), s.path(SKI, 'photos', base + suffix + ext))
                ski('file: photos/02.webp', 'file: photos/' + declared)(s)
                self.assertFindings()

    def test_dimensions(self):
        size = 'photos[1].%s (photos/02.webp) must be a positive whole number of pixels, got %r'
        for new, msg in (('    h: 1600', 'photos[1] (photos/02.webp) has h but no w; record both (the pixel size) or neither'),
                         ('    w: 1200.0\n    h: 1600', size % ('w', 1200.0)),
                         ('    w: 1200\n    h: -1600', size % ('h', -1600)),
                         ('    w: true\n    h: 1600', size % ('w', True)),
                         ('    w: 1200\n    h: "1600"', size % ('h', '1600'))):
            with self.subTest(new=new):
                self.s.reset()
                ski('    w: 1200\n    h: 1600', new)(self.s)
                self.assertFindings(errors=[I(SKI, msg)])

    def test_both_dimensions_wrong_are_two_errors(self):
        ski('    w: 1200\n    h: 1600', '    w: wide\n    h: tall')(self.s)
        self.assertEqual(len(self.errors()), 2)

    def test_alt_and_caption_types(self):
        ski('caption: The spires', 'caption: 1999')(self.s)
        self.assertFindings(errors=[I(SKI, 'photos[0].caption (photos/01.webp) must be text, got 1999')])
        ski('caption: 1999', 'caption:')(self.s)
        ski('alt: Skier in the couloir', 'alt: [a]')(self.s)
        self.assertFindings(errors=[I(SKI, "photos[1].alt (photos/02.webp) must be text, got ['a']")])

    def test_a_list_with_one_entry_that_is_not_an_entry(self):
        ski(P2, '  - photos/02.webp\n')(self.s)
        self.assertFindings(errors=[I(SKI, "photos[1] must be an entry with file, w, h and alt lines, got 'photos/02.webp'")])

    def test_a_day_s_photo_is_checked_in_its_day_file(self):
        s = self.s
        s.remove(s.path(HUT, 'photos', 'd01-01.webp'))
        self.assertFindings(errors=[D(HUT, '01', "photos[0].file 'photos/d01-01.webp' is missing from the trip folder")])

    def test_a_folder_inside_photos_is_an_error(self):
        os.makedirs(self.s.path(SKI, 'photos', 'originals'))
        self.assertFindings(errors=[I(SKI, 'photos/originals is a folder; photos/ may hold files only (the build copies each entry as one file)')])

    def test_a_declared_name_that_is_a_folder_is_missing(self):
        s = self.s
        s.remove(s.path(SKI, 'photos', '02.webp'))
        os.makedirs(s.path(SKI, 'photos', '02.webp'))
        self.assertEqual(self.errors(), sorted([I(SKI, MISSING), I(SKI, 'photos/02.webp is a folder; photos/ may hold files only (the build '
                                                                         'copies each entry as one file)')]))

    def test_alt_of_spaces_is_no_alt(self):
        ski('alt: Skier in the couloir', 'alt: "  "')(self.s)
        self.assertFindings(warnings=[I(SKI, 'photos[1] (photos/02.webp) has no alt text; describe the photo in a sentence')])

    def test_only_the_cover_needs_a_card_size_copy(self):
        s = self.s
        s.remove(s.path(SKI, 'photos', '02.th.webp'), s.path(SKI, 'photos', '03.th.webp'))
        self.assertFindings()
        s.remove(s.path(SKI, 'photos', '01.th.webp'))
        self.assertFindings(warnings=[I(SKI, 'cover photos/01.webp has no card-size copy (.th); run python3 tools/thumbs.py ski-report')])

    def test_the_card_size_warning_follows_an_explicit_cover(self):
        s = self.s
        ski_line('cover_photo: photos/03.webp')(s)
        s.remove(s.path(SKI, 'photos', '01.th.webp'))
        self.assertFindings()
        s.remove(s.path(SKI, 'photos', '03.th.webp'))
        self.assertFindings(warnings=[I(SKI, 'cover photos/03.webp has no card-size copy (.th); run python3 tools/thumbs.py ski-report')])

    def test_a_cover_declared_in_a_day_file_is_reported_on_the_trip(self):
        s = self.s
        s.remove(s.path(HUT, 'photos', 'd01-01.th.webp'))
        self.assertFindings(warnings=[I(HUT, 'cover photos/d01-01.webp has no card-size copy (.th); run python3 tools/thumbs.py hut-tour')])

    def test_the_800_px_copy_of_a_day_photo(self):
        s = self.s
        s.remove(s.path(HUT, 'photos', 'd01-01.sm.webp'))
        self.assertFindings(warnings=[D(HUT, '01', 'photos[0] (photos/d01-01.webp) has no 800 px copy (d01-01.sm.webp), so phones load '
                                                   'the full file')])

    def test_a_photo_declared_in_index_and_again_in_a_day_file(self):
        s = self.s
        s.sub(s.day(HUT, '02'), 'stats:', 'photos:\n  - file: photos/d01-01.webp\n    w: 1600\n    h: 1200\n    alt: The hut again\nstats:')
        self.assertFindings(warnings=[D(HUT, '02', 'photos[0] declares photos/d01-01.webp again (first in 01.md, photos[0]); the page shows '
                                                   'it twice')])

    def test_a_repeated_declaration_is_reported_once_and_as_nothing_else(self):
        # the repeats carry no size, no alt and no caption: each is still only "declared again", and names the first
        ski(P2, P2 + '  - file: photos/02.webp\n  - file: ./photos/02.webp\n')(self.s)
        self.assertFindings(warnings=[I(SKI, 'photos[2] declares photos/02.webp again (first in index.md, photos[1]); the page shows it twice'),
                                      I(SKI, 'photos[3] declares photos/02.webp again (first in index.md, photos[1]); the page shows it twice')])
        self.assertIn(I(SKI, '2 photos without a caption'), self.notes())

    def test_copies_of_a_photo_nobody_declared_are_stray_files_too(self):
        s = self.s
        for name in ('99.sm.webp', '99.th.webp', 'notes.txt'):
            write(s.path(SKI, 'photos', name), '')
        write(s.path(SKI, 'photos', '.DS_Store'), '')          # a dot file is not published and not mentioned
        stray = ('content/trips/ski-report/photos/%s: not declared under photos: in index.md or a days/NN.md, and not the .sm or .th '
                 'copy of a declared photo; the build publishes it all the same')
        self.assertFindings(warnings=[stray % '99.sm.webp', stray % '99.th.webp', stray % 'notes.txt'])
        found = [f for f in checks.warnings(s.run())]
        self.assertEqual(found[0]['file'], 'content/trips/ski-report/photos/99.sm.webp')

    def test_a_photos_folder_without_any_declaration(self):
        write(self.s.path(HIKE, 'photos', '01.webp'), '')
        self.assertFindings(warnings=['content/trips/loop-hike/photos/01.webp: not declared under photos: in index.md or a days/NN.md, and '
                                      'not the .sm or .th copy of a declared photo; the build publishes it all the same'])

    def test_captions_are_counted_per_file(self):
        s = self.s
        self.assertIn(I(SKI, '2 photos without a caption'), self.notes())
        ski('alt: Skier in the couloir', 'alt: Skier in the couloir\n    caption: Dropping in')(s)
        self.assertIn(I(SKI, '1 photo without a caption'), self.notes())
        ski('alt: The summit ridge', 'alt: The summit ridge\n    caption: "  "')(s)       # spaces are no caption
        self.assertIn(I(SKI, '1 photo without a caption'), self.notes())
        ski('caption: "  "', 'caption: On top')(s)
        self.assertEqual([n for n in self.notes() if n.startswith('content/trips/ski-report/')], [])


# ---------------------------------------------------------------- tracks and rendered maps

class TrackTests(Fixture):

    def gpx_file(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, 'probe.gpx')
        write(path, text)
        return path

    def test_gpx_problem_reads_structure_only(self):
        self.assertIsNone(checks.gpx_problem(self.gpx_file(gf.SINGLE)))
        self.assertIsNone(checks.gpx_problem(self.gpx_file(gf.SINGLE_NO_NS)))
        self.assertIsNone(checks.gpx_problem(self.gpx_file(gf.ROUTE_ONLY)))
        self.assertIsNone(checks.gpx_problem(self.gpx_file(gf.MULTISEG)))
        self.assertEqual(checks.gpx_problem(self.gpx_file('')), 'is empty')
        self.assertEqual(checks.gpx_problem(self.gpx_file('not a gpx')), 'is not a GPX file (no <gpx> element at its start)')
        self.assertEqual(checks.gpx_problem(self.gpx_file('<html><body>404</body></html>')), 'is not a GPX file (no <gpx> element at its start)')
        self.assertEqual(checks.gpx_problem(self.gpx_file(gf.WAYPOINT_ONLY)), 'holds no track or route point')
        self.assertEqual(checks.gpx_problem(self.gpx_file(gf.gpx(gf.trk([[]], 'Nothing')))), 'holds no track or route point')

    def test_gpx_problem_reads_on_past_its_first_block(self):
        many = '\n'.join(gf.wpt(38.9, -120.1, 'Waypoint %d' % i) for i in range(3000))
        text = gf.gpx(many, gf.trk([gf.SEG_A], 'After the waypoints'))
        self.assertGreater(text.index('<trkpt'), checks._GPX_HEAD + 2 * checks._GPX_CHUNK)
        self.assertIsNone(checks.gpx_problem(self.gpx_file(text)))
        self.assertEqual(checks.gpx_problem(self.gpx_file(gf.gpx(many))), 'holds no track or route point')

    def test_gpx_problem_sees_a_tag_cut_by_the_block_boundary(self):
        for cut in range(1, 6):         # '<trkpt' split after its first to fifth character
            for boundary in (checks._GPX_HEAD, checks._GPX_HEAD + checks._GPX_CHUNK):
                with self.subTest(cut=cut, boundary=boundary):
                    head = gf.HEAD + '<trk><trkseg>'
                    pad = boundary - len(head.encode('utf-8')) - cut - len('<!--') - len('-->')
                    text = head + '<!--' + 'x' * pad + '-->' + '<trkpt lat="38.9" lon="-120.1"></trkpt></trkseg></trk></gpx>'
                    self.assertEqual(text.encode('utf-8').index(b'<trkpt'), boundary - cut)
                    self.assertIsNone(checks.gpx_problem(self.gpx_file(text)))

    def test_gpx_problem_wants_the_root_element_at_the_start(self):
        text = '<?xml version="1.0"?>\n<!--' + 'x' * checks._GPX_HEAD + '-->\n' + gf.SINGLE.split('\n', 1)[1]
        self.assertEqual(checks.gpx_problem(self.gpx_file(text)), 'is not a GPX file (no <gpx> element at its start)')

    def test_gpx_problem_does_not_open_a_file_icloud_has_offloaded(self):
        # such a file cannot be made here, so os.stat answers for one: the size it would report, and the dataless flag
        real = os.stat

        def offloaded(size):
            def stat(path, *a, **k):
                st = real(path, *a, **k)
                if not str(path).endswith('probe.gpx'):
                    return st
                return mock.Mock(st_size=size, st_flags=0x40000060, st_mode=st.st_mode)
            return stat
        path = self.gpx_file('not a gpx')
        self.assertEqual(checks.gpx_problem(path), 'is not a GPX file (no <gpx> element at its start)')
        with mock.patch.object(checks.os, 'stat', offloaded(121334)), mock.patch('builtins.open', side_effect=AssertionError('opened')):
            self.assertIsNone(checks.gpx_problem(path))
        with mock.patch.object(checks.os, 'stat', offloaded(0)), mock.patch('builtins.open', side_effect=AssertionError('opened')):
            self.assertEqual(checks.gpx_problem(path), 'is empty')       # its size is known without reading it
        self.assertEqual(checks._DATALESS, 0x40000000)

    def test_gpx_problem_on_something_that_cannot_be_opened(self):
        self.assertEqual(checks.gpx_problem(self.s.path(SKI, 'photos')), 'could not be read (IsADirectoryError: Is a directory)')

    def test_a_report_s_track_files_must_be_gpx(self):
        s = self.s
        write(s.path(HUT, 'days', '02.gpx'), '')
        write(s.path(JOURNAL, 'days', '003.gpx'), gf.WAYPOINT_ONLY)
        write(s.path('draft-trip', 'track.gpx'), '<gpx></gpx>')
        self.assertFindings(errors=['content/trips/hut-tour/days/02.gpx: the file is empty' + A_TRACK,
                                    'content/trips/journal/days/003.gpx: the file holds no track or route point' + A_TRACK,
                                    'content/trips/draft-trip/track.gpx: the file holds no track or route point' + A_TRACK])

    def test_a_gpx_without_a_day_file_is_not_read(self):
        write(self.s.path(HUT, 'days', '03.gpx'), '')
        self.assertFindings()

    def test_a_goal_s_track_is_the_importer_s_business(self):
        s = self.s
        no_route_block(s)
        write(s.path('goal-route', 'track.gpx'), 'not a gpx')
        self.assertFindings(warnings=[G('goal-route', NO_ROUTE)])

    def test_tracks_of_a_trip_whose_index_does_not_parse_are_still_read(self):
        s = self.s
        write(s.index(HIKE), '---\ntitle: X\n')
        write(s.path(HIKE, 'track.gpx'), '')
        self.assertEqual(self.errors(), sorted([I(HIKE, 'front matter: front matter is not closed with ---'),
                                                'content/trips/loop-hike/track.gpx: the file is empty' + A_TRACK]))

    def test_a_journal_without_any_day_gpx(self):
        s = self.s
        for d in ('001', '002', '003'):
            s.remove(s.path(JOURNAL, 'days', d + '.gpx'))
        self.assertFindings(warnings=[I(JOURNAL, 'none of the 3 days has a GPX (days/NN.gpx): the page shows an empty map and offers no downloads')])

    def test_a_goal_without_a_track_is_an_idea(self):
        self.assertFalse(os.path.exists(self.s.path('goal-idea', 'track.gpx')))
        self.assertFindings()

    def test_a_trip_with_a_track_and_no_render(self):
        s = self.s
        for slug in (HIKE, HUT, 'goal-route'):
            os.remove(os.path.join(s.rendered, 'trips', slug, 'meta.json'))
        self.assertFindings(warnings=[
            I(slug, 'no rendered map (rendered/trips/%s/meta.json is missing); run python3 tools/render.py %s' % (slug, slug))
            for slug in (HIKE, HUT, 'goal-route')])

    def test_no_render_is_expected_of_a_draft_or_a_trip_without_a_track(self):
        s = self.s
        self.assertFalse(os.path.exists(os.path.join(s.rendered, 'trips', 'draft-trip')))     # render.py leaves drafts out
        self.assertFalse(os.path.exists(os.path.join(s.rendered, 'trips', 'goal-idea')))
        self.assertFindings()
        s.remove(s.path(HIKE, 'track.gpx'))
        shutil.rmtree(os.path.join(s.rendered, 'trips', HIKE))
        self.assertFindings(warnings=[I(HIKE, NO_TRACK)])

    def test_without_a_rendered_folder_nothing_is_said_about_renders(self):
        s = self.s
        hike('region: Lake Tahoe', 'region: Nevada')(s)
        shutil.rmtree(s.rendered)
        self.assertFindings()

    def test_a_region_the_site_maps_do_not_know(self):
        s = self.s
        hike('region: Lake Tahoe', 'region: Nevada')(s)
        self.assertFindings(warnings=[I(HIKE, NO_REGION % 'Nevada')])
        s.sub(s.index(HUT), 'region: Alps', 'region: Nevada')
        ski('region: Eastern Sierra', 'region: Nevada')(s)
        self.assertFindings(warnings=[I(HUT, "region 'Nevada' (and 2 more trips) is not in rendered/site/meta.json, so the map page does "
                                             "not list it yet; run python3 tools/render.py --site --force")])
        ski('region: Nevada', 'region: Eastern Sierra')(s)
        self.assertFindings(warnings=[I(HUT, "region 'Nevada' (and 1 more trip) is not in rendered/site/meta.json, so the map page does "
                                             "not list it yet; run python3 tools/render.py --site --force")])

    def test_regions_render_py_leaves_out_are_not_expected_in_the_file(self):
        s = self.s
        self.assertIn('region: Pacific Crest Trail', read(s.index(JOURNAL)))           # a journal has no region map
        s.sub(s.index('goal-route'), 'region: Lake Tahoe', 'region: Nevada')             # a goal joins a map only with an active route
        s.add('draft-trip', 'region: Atlantis')                                         # a draft is not rendered
        s.sub(s.index(HIKE), 'region: Lake Tahoe\n', '')                                # no region at all
        self.assertFindings()

    def test_a_site_meta_that_cannot_answer_is_left_alone(self):
        s = self.s
        hike('region: Lake Tahoe', 'region: Nevada')(s)
        meta = os.path.join(s.rendered, 'site', 'meta.json')
        for text in ('{"maps": {}}', '{"all_regions": "Nevada"}', '[]', '{not json'):
            with self.subTest(text=text):
                write(meta, text)
                self.assertFindings()
        os.remove(meta)
        self.assertFindings()


# ---------------------------------------------------------------- goals

class GoalTests(Fixture):

    def legacy(self):
        s = self.s
        s.remove(s.path('goal-route', 'goal.json'))
        return I('goal-route', 'planned route without goal.json: it is listed with the default status and priority; review it and run '
                               'python3 tools/ticklist.py update goal-route to give it one')

    def test_a_planned_route_without_a_sidecar_is_one_warning(self):
        # the legacy goal has a track, no route block and no approval: none of that is reported on top
        self.assertFindings(warnings=[self.legacy()])

    def test_a_legacy_goal_without_a_track(self):
        s = self.s
        s.remove(s.path('goal-idea', 'goal.json'))
        self.assertFindings(warnings=[I('goal-idea', 'planned route without goal.json: it is listed with the default status and priority; '
                                                     'review it and run python3 tools/ticklist.py update goal-idea to give it one')])

    def test_no_route_block_and_no_approval_are_two_warnings(self):
        no_route_block(self.s)
        unapproved(self.s)
        self.assertEqual(len(self.warnings()), 2)

    def test_a_route_block_without_the_file_is_an_error_whatever_the_approval(self):
        s = self.s
        unapproved(s)
        s.remove(s.path('goal-route', 'track.gpx'))
        found = s.run()
        self.assertEqual(len(checks.errors(found)), 1)
        self.assertEqual(checks.errors(found)[0]['file'], 'content/trips/goal-route/goal.json')
        self.assertEqual(checks.warnings(found), [])

    def test_an_outing_today_happened_and_one_tomorrow_did_not(self):
        s = self.s
        s.setg('goal-done', outings=[outing(date='2026-10-10', report_slug=SKI)])
        self.assertFindings()
        s.setg('goal-done', outings=[outing(date='2026-10-11', report_slug=SKI)])
        self.assertFindings(warnings=[G('goal-done', 'outings[0].date 2026-10-11 is in the future (today is 2026-10-10); an outing is '
                                                     'something that happened')])

    def test_outings_without_a_report_are_never_repeats(self):
        self.s.setg('goal-done', outings=[outing(outcome='attempted'), outing(outcome='attempted'), outing()])
        self.assertFindings()

    def test_the_same_report_three_times_is_two_warnings_naming_the_first(self):
        self.s.setg('goal-done', outings=[outing(report_slug=SKI, outcome='attempted'), outing(report_slug=HIKE, outcome='attempted'),
                                          outing(report_slug=SKI, outcome='attempted'), outing(report_slug=SKI)])
        self.assertFindings(warnings=[G('goal-done', "outings[2].report_slug 'ski-report' is already named by outings[0]"),
                                      G('goal-done', "outings[3].report_slug 'ski-report' is already named by outings[0]")])


# ---------------------------------------------------------------- the manifest

class ManifestTests(Fixture):

    def test_unknown_keys_are_warnings_with_the_nearest_known_key(self):
        self.s.put_home({'featured_slugs': [SKI], 'featured_slug': [HUT], 'note': 'x'})
        self.assertFindings(warnings=[H("unknown key 'featured_slug' (did you mean 'featured_slugs'?); nothing reads it"), H(UNKNOWN % 'note')])

    def test_an_unknown_key_is_reported_beside_the_error_it_caused(self):
        self.s.put_home({'featured_slugz': [SKI]})
        self.assertFindings(errors=[H('missing "featured_slugs" (a list of trip slugs)')],
                            warnings=[H("unknown key 'featured_slugz' (did you mean 'featured_slugs'?); nothing reads it")])

    def test_the_missing_file_is_a_plain_warning_and_no_python_warning(self):
        self.s.remove(self.s.home)
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            found = self.s.run()
        self.assertEqual([f['file'] for f in checks.warnings(found)], ['content/home.json'])

    def test_a_valid_manifest_is_quiet(self):
        self.s.put_home({'featured_slugs': [SKI, HUT, HIKE, JOURNAL]})
        self.assertFindings()


# ---------------------------------------------------------------- links in write-ups

class LinkTests(Fixture):

    def problem(self, url, slug=SKI, pages=('ski-report', 'loop-hike', 'goal-route'), drafts=('draft-trip',)):
        return checks._link_problem(url, slug, set(pages), set(drafts))

    def test_links_that_are_fine(self):
        for url in ('#map', '../loop-hike/', '../loop-hike/#nope', '../loop-hike/loop-hike.gpx', '../loop-hike/map/', '../goal-route/',
                    '../ski-report/', './', 'photos/02.webp', 'map/', '../', '../../', '../../map/#region-alps', '../../hiking/',
                    '../../../elsewhere/', 'mailto:someone@example.test', 'https://example.test/trips/nope/', 'http://example.test/',
                    'HTTPS://EXAMPLE.TEST/x', core.SITE_URL, core.SITE_URL + 'trips/', core.SITE_URL + 'trips/loop-hike/',
                    core.SITE_URL + 'trips/loop-hike/#day-2', core.SITE_URL + 'map/', core.SITE_URL + 'trips/ski-report/?x=1',
                    core.SITE_URL.replace('https://', 'http://') + 'trips/loop-hike/', '../loop-hike/?unit=km#top', '../loop-hike?unit=km',
                    '../loop-hike#top'):
            with self.subTest(url=url):
                self.assertIsNone(self.problem(url))

    def test_links_to_pages_that_do_not_exist(self):
        gone = 'points at trips/nope/, which is not a page of the site (no content/trips/nope/index.md)'
        for url in ('../nope/', '../nope', '../nope/#top', '../nope#top', '../nope/nope.gpx', '../nope/?x=1', '../nope?x=1',
                    '../../trips/nope/', '../loop-hike/../nope/',
                    core.SITE_URL + 'trips/nope/', core.SITE_URL + 'trips/nope/map/', core.SITE_URL.replace('https://', 'http://') + 'trips/nope/'):
            with self.subTest(url=url):
                self.assertEqual(self.problem(url), gone)
        self.assertEqual(self.problem('../draft-trip/'), 'points at trips/draft-trip/, a draft, which has no page')
        self.assertEqual(self.problem(core.SITE_URL + 'trips/draft-trip/'), 'points at trips/draft-trip/, a draft, which has no page')

    def test_links_that_leave_the_site_or_use_another_scheme(self):
        rooted = ('starts with /, which leaves the site (it is served under %s); write a relative link such as ../other-trip/ or the '
                  'full address' % core.SITE_URL)
        for url in ('/', '/trips/loop-hike/', '/personal-website/', '//evil.example/x'):
            with self.subTest(url=url):
                self.assertEqual(self.problem(url), rooted)
        for url, scheme in (('javascript:alert(1)', 'javascript'), ('JavaScript:alert(1)', 'javascript'), ('data:text/html,x', 'data'),
                            ('ftp://example.test/x', 'ftp'), ('file:///etc/hosts', 'file'), ('tel:+15550100', 'tel'), ('vbscript:x', 'vbscript')):
            with self.subTest(url=url):
                self.assertEqual(self.problem(url), 'uses %s:, and only http, https, mailto links are accepted' % scheme)
        self.assertEqual(checks.LINK_SCHEMES, ('http', 'https', 'mailto'))

    def test_only_links_the_page_will_carry_are_judged(self):
        s = self.s
        s.body(SKI, 'In code: `[x](../nope/)` and `/abs`.\n\n<!-- [hidden](../nope/) -->\n\nPlain text ../nope/ and (../nope/).')
        self.assertFindings()
        self.assertEqual(checks._links('`[x](../nope/)` <!-- [y](../nope/) --> ../nope/'), [])
        self.assertEqual(checks._links('[a](../one/) and https://example.test/two, then.'), ['../one/', 'https://example.test/two'])
        self.assertEqual(checks._links('[q](../a/?x=1&y=2)'), ['../a/?x=1&y=2'])
        self.assertEqual(checks._links(None), [])
        self.assertEqual(checks._links('no links here'), [])

    def test_a_bare_address_of_the_site_is_a_link_too(self):
        self.s.body(SKI, 'See %strips/nope/ for more.' % core.SITE_URL)
        self.assertFindings(errors=[I(SKI, NO_PAGE % (core.SITE_URL + 'trips/nope/', 'nope', 'nope'))])

    def test_every_bad_link_of_a_write_up_is_reported(self):
        self.s.body(SKI, '[a](../nope/) [b](/x) [c](ftp://example.test/) [d](../loop-hike/) [e](../nope/)')
        self.assertEqual(self.errors(), sorted([
            I(SKI, NO_PAGE % ('../nope/', 'nope', 'nope')), I(SKI, NO_PAGE % ('../nope/', 'nope', 'nope')), I(SKI, ROOTED % '/x'),
            I(SKI, "write-up link 'ftp://example.test/' uses ftp:, and only http, https, mailto links are accepted")]))

    def test_a_link_in_a_day_s_write_up_is_named_by_the_day_file(self):
        s = self.s
        write(s.day(HUT, '02'), read(s.day(HUT, '02')) + '\nOver the col, see [the old trip](../gone/).\n')
        self.assertFindings(errors=[D(HUT, '02', NO_PAGE % ('../gone/', 'gone', 'gone'))])

    def test_a_goal_page_and_a_journal_are_pages(self):
        self.s.body(SKI, '[goal](../goal-idea/) [journal](../journal/#day-2) [tour](../hut-tour/)')
        self.assertFindings()

    def test_a_folder_without_index_is_not_a_page(self):
        os.makedirs(self.s.path('stray'))
        self.s.body(SKI, '[x](../stray/)')
        self.assertFindings(errors=[I(SKI, NO_PAGE % ('../stray/', 'stray', 'stray'))])

    def test_a_draft_may_link_to_a_draft_but_not_to_nothing(self):
        s = self.s
        helpers.make_trip(s.trips, 'second-draft', title='Second', activity='hike', date='2026-03-03', draft=True, body='x')
        s.body('draft-trip', '[other](../second-draft/) [live](../loop-hike/) [gone](../nope/)')
        self.assertEqual(self.errors(), [I('draft-trip', NO_PAGE % ('../nope/', 'nope', 'nope'))])

    def test_links_of_a_trip_with_a_raw_error_are_still_checked(self):
        s = self.s
        ski('title: West Couloir', 'title: 7')(s)
        s.body(SKI, '[x](../nope/)')
        self.assertEqual(self.errors(), sorted([I(SKI, 'title must be text, got 7'), I(SKI, NO_PAGE % ('../nope/', 'nope', 'nope'))]))


# ---------------------------------------------------------------- duplicates across trips

class DuplicateTests(Fixture):

    def twin(self, **meta):
        f = helpers.make_trip(self.s.trips, 'twin', title='West Couloir', activity='ski', date='2026-01-17', **meta)
        self.s.gpx(os.path.join(f, 'track.gpx'))
        write(os.path.join(self.s.rendered, 'trips', 'twin', 'meta.json'), '{}')

    def test_title_and_date_on_two_published_reports(self):
        self.twin()
        self.assertFindings(warnings=[I('twin', "same title and date as content/trips/ski-report/index.md ('West Couloir', 2026-01-17): the two "
                                                "pages get the same <title>")])

    def test_three_reports_alike_are_two_warnings_naming_the_first(self):
        self.twin()
        f = helpers.make_trip(self.s.trips, 'aaa', title='West Couloir', activity='hike', date='2026-01-17')
        self.s.gpx(os.path.join(f, 'track.gpx'))
        write(os.path.join(self.s.rendered, 'trips', 'aaa', 'meta.json'), '{}')
        self.assertEqual(self.warnings(), sorted(
            [I(slug, "same title and date as content/trips/aaa/index.md ('West Couloir', 2026-01-17): the two pages get the same <title>")
             for slug in (SKI, 'twin')]))

    def test_drafts_and_goals_are_not_twins_and_another_date_tells_two_reports_apart(self):
        s = self.s
        self.twin(draft=True)
        s.sub(s.index('goal-idea'), 'title: An Idea', 'title: West Couloir')
        self.assertFindings()
        s.add('goal-idea', 'date: 2026-01-17')       # even a goal with the report's date is not a second report
        self.assertFindings(warnings=[I('goal-idea', "a planned route has a date: line (2026-01-17); a goal has no date, and an "
                                                     "outing's date goes in goal.json")])
        s.sub(s.index('twin'), 'draft: true\n', '')
        s.sub(s.index('twin'), 'date: 2026-01-17', 'date: 2026-01-18')
        self.assertEqual(len(self.warnings()), 1)
        self.assertEqual(self.errors(), [])

    def test_two_undated_reports_with_one_title_are_told_about_their_dates_only(self):
        s = self.s
        self.twin()
        for slug in (SKI, 'twin'):
            s.sub(s.index(slug), 'date: 2026-01-17\n', '')
        no_date = 'no date (add date: YYYY-MM-DD): the page, its card and the feed show none and the trip sorts last'
        self.assertFindings(warnings=[I(SKI, no_date), I('twin', no_date)])

    def test_the_spelling_most_trips_use_is_the_intended_one(self):
        s = self.s
        for slug in (SKI, 'goal-done'):
            s.sub(s.index(slug), 'region: Eastern Sierra', 'region: eastern sierra')
        self.twin(region='Eastern Sierra')
        put_json(os.path.join(s.rendered, 'site', 'meta.json'), {'all_regions': ['Alps', 'Eastern Sierra', 'Lake Tahoe', 'eastern sierra']})
        self.assertEqual([w for w in self.warnings() if 'is written' in w],
                         [I('twin', SPELLED % ('Eastern Sierra', 'eastern sierra', '2 other trips', 'eastern-sierra'))])

    def test_three_spellings(self):
        s = self.s
        hike('region: Lake Tahoe', 'region: LAKE TAHOE')(s)
        s.sub(s.index(HUT), 'region: Alps', 'region: Lake-Tahoe')
        shutil.rmtree(s.rendered)
        # one trip each: the first in sorting order stands in as the intended one, so the answer does not change by the run
        self.assertFindings(warnings=[I('goal-route', SPELLED % ('Lake Tahoe', 'LAKE TAHOE', '1 other trip', 'lake-tahoe')),
                                      I(HUT, SPELLED % ('Lake-Tahoe', 'LAKE TAHOE', '1 other trip', 'lake-tahoe'))])

    def test_a_draft_s_spelling_is_not_counted(self):
        self.s.add('draft-trip', 'region: lake tahoe')
        self.assertFindings()

    def test_repeated_day_labels_on_a_multi_day_trip(self):
        s = self.s
        s.sub(s.day(HUT, '01'), 'day: "1"\n', '')         # no day: line: the label is the position, 1
        self.assertFindings()
        s.sub(s.day(HUT, '02'), 'day: "2"', 'day: 1')     # the number 1 and the position 1 are one label
        self.assertFindings(warnings=[D(HUT, '02', "day label '1' is also the label of days/01.md; give each day its own day: line")])


# ---------------------------------------------------------------- unknown keys

class UnknownKeyTests(Fixture):

    def test_in_every_place_a_key_can_be_mistyped(self):
        s = self.s
        s.add(SKI, 'titel: Typo')
        ski('    alt: Granite spires', '    atl: Granite spires\n    alt: Granite spires')(s)
        ski('  loss_m: 1450', '  loss_m: 1450\n  gain_ft: 4757')(s)
        ski_line('map:\n  peak: [Matterhorn Peak]')(s)
        day2('date: 2024-03-02', 'date: 2024-03-02\ndayy: 2')(s)
        s.sub(s.day(HUT, '01'), '    alt: The hut', '    alt: The hut\n    credit: Sam')
        s.sub(s.day(HUT, '01'), '  gain_m: 900', '  gain_m: 900\n  gain: 900')
        self.assertFindings(warnings=[
            I(SKI, "unknown key 'titel' (did you mean 'title'?); nothing reads it"),
            I(SKI, "unknown key 'atl' in photos[0] (did you mean 'alt'?); nothing reads it"),
            I(SKI, "unknown key 'gain_ft' in stats (did you mean 'gain_m'?); nothing reads it"),
            I(SKI, "unknown key 'peak' in map (did you mean 'peaks'?); nothing reads it"),
            D(HUT, '02', "unknown key 'dayy' (did you mean 'day'?); nothing reads it"),
            D(HUT, '01', "unknown key 'credit' in photos[0]; nothing reads it"),
            D(HUT, '01', "unknown key 'gain' in stats (did you mean 'gain_m'?); nothing reads it")])

    def test_a_typo_is_named_beside_the_error_it_causes(self):
        hike('title: Basin Loop', 'titel: Basin Loop')(self.s)
        self.assertFindings(errors=[I(HIKE, NO_TITLE)], warnings=[I(HIKE, "unknown key 'titel' (did you mean 'title'?); nothing reads it")])

    def test_every_known_key_of_index_md_and_a_day_file_is_quiet(self):
        s = self.s
        value = {'title': 'T', 'activity': 'hike', 'kind': 'trip', 'date': '2025-08-10', 'end_date': '2025-08-10', 'start_time': '"06:10"',
                 'stats': '\n  distance_km: 1.0', 'featured': 'false', 'draft': 'false', 'beta': '\n  - label: A\n    value: B',
                 'map': '\n  peaks: [A]', 'photos': '', 'cover_focal_x': '50', 'cover_focal_y': '50', 'card_summary': 'Text.',
                 'search_aliases': '[A]', 'journal_highlights': '[]', 'cover_photo': '', 'conditions': '', 'strava_id': '"123"',
                 'published_at': '', 'updated_at': ''}
        write(s.index(HIKE), '---\n%s\n---\n' % '\n'.join('%s: %s' % (k, value.get(k, 'Text')) for k in checks.INDEX_KEYS))
        self.assertEqual([w for w in self.warnings() if 'unknown key' in w], [])
        self.assertEqual(self.errors(), [])
        dvalue = {'day': '"2"', 'date': '2024-03-02', 'start_time': '"07:00"', 'stats': '\n  distance_km: 1.0', 'photos': '',
                  'transfer_before': 'true', 'strava_id': '"9"'}
        write(s.day(HUT, '02'), '---\n%s\n---\n' % '\n'.join('%s: %s' % (k, dvalue.get(k, 'Text')) for k in checks.DAY_KEYS))
        self.assertEqual([w for w in self.warnings() if 'unknown key' in w], [])
        self.assertEqual(self.errors(), [])


# ---------------------------------------------------------------- the shapes the real archive has

class LegacyShapeTests(unittest.TestCase):

    def test_what_the_archive_looks_like_today_is_no_error_and_one_warning(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        trips = os.path.join(tmp.name, 'content', 'trips')
        os.makedirs(trips)
        # a bulk-imported ride: no place, no write-up, no photos, a strava_id, stats as the importer wrote them
        f = helpers.make_trip(trips, 'spontaneous-ride', title='Spontaneous ride', activity='mtb', date='2025-06-01', start_time='17:42',
                              timezone='America/Los_Angeles', region='Santa Cruz', route_shape='loop', strava_id='123456789',
                              stats={'distance_km': 14.21, 'moving': '1:12', 'elapsed': '1:30', 'gain_m': 410, 'loss_m': 410, 'high_m': 520,
                                     'low_m': 110})
        write(os.path.join(f, 'track.gpx'), gf.SINGLE)
        # a paddle: activity other with a subtype
        f = helpers.make_trip(trips, 'evening-paddle', title='Evening paddle', activity='other', subtype='SUP', date='2025-07-04',
                              region='Lake Tahoe', route_shape='out-and-back', stats={'distance_km': 3.1, 'moving': '0:48'})
        write(os.path.join(f, 'track.gpx'), gf.SINGLE)
        # a multi-day course whose day files carry no day: line and no title
        f = helpers.make_trip(trips, 'ski-course', title='Ski course', activity='ski', kind='multi-day', region='Lake Tahoe', featured=True)
        for i in (1, 2):
            write(os.path.join(f, 'days', '%02d.md' % i), '---\ndate: 2025-02-%02d\nstart_time: "08:0%d"\nstrava_id: "%d"\nstats:\n'
                                                           '  distance_km: 5.5\n  moving: "2:10"\n---\n' % (i, i, i))
            write(os.path.join(f, 'days', '%02d.gpx' % i), gf.SINGLE)
        # the planned route that predates the tick list: a track, no goal.json
        f = helpers.make_trip(trips, 'someday-traverse', title='Someday Traverse', activity='hike', kind='planned', place='Desolation',
                              region='Lake Tahoe', route_shape='point-to-point', stats={'distance_km': 27.94})
        write(os.path.join(f, 'track.gpx'), gf.SINGLE)
        home = os.path.join(tmp.name, 'content', 'home.json')
        put_json(home, {'featured_slugs': ['ski-course']})
        found, counts = checks.survey(trips, home, os.path.join(tmp.name, 'rendered'), TODAY)
        self.assertEqual(checks.errors(found), [])
        self.assertEqual(texts(checks.warnings(found)), [
            I('someday-traverse', 'planned route without goal.json: it is listed with the default status and priority; review it and run '
                                  'python3 tools/ticklist.py update someday-traverse to give it one')])
        self.assertEqual(texts(checks.notes(found)), sorted([
            I('spontaneous-ride', 'no place'), I('spontaneous-ride', 'no write-up'), I('spontaneous-ride', 'no photos'),
            I('evening-paddle', 'no place'), I('evening-paddle', 'no write-up'), I('evening-paddle', 'no photos'),
            I('ski-course', 'no place'), I('ski-course', 'no write-up'), I('ski-course', 'no photos'),
            D('ski-course', '01', 'no title'), D('ski-course', '02', 'no title')]))
        self.assertEqual(counts, {'trips': 4, 'photos': 0, 'gpx': 5})


if __name__ == '__main__':
    unittest.main()
