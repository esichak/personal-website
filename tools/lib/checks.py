"""Content validation: everything wrong with content/ as a list of findings, never an exception.

    findings = checks.run()                      # the real content/, or run(trips_dir, home_json, rendered_dir, today)
    for f in checks.errors(findings):
        print(checks.line(f))                    # 'ERROR content/trips/<slug>/index.md: activity must be one of ...'

content.load_all stops at the first broken file, and before this module only the fields added since Phase 1 were
checked at all: a wrong type in an older field (`title: 2025`, `stats: fast`, `photos:` as text) ended in a traceback
somewhere inside a page module, and a missing photo or an unknown `kind:` built a site with dead links. run() reads
every trip folder, reports every broken file in one pass and leaves the loading rules where they are: whatever
content.load_trip, goals.validate and curation.resolve_featured refuse comes through with its message unchanged.

A finding is {'level': 'error' | 'warning' | 'note', 'file': <repo-relative posix path>, 'text': <one line>}; the text
starts with the file and ': ', the form every ContentError already has. Errors stop a build (a broken explicit value,
or a value the generator cannot read). Warnings are optional metadata left incomplete, which the pages cope with.
Notes are optional fields that are simply absent; they are counted, and listed only on request.

Per trip folder the work is: (a) read index.md and the day files raw; (b) check the raw values, so a wrong type is
named by its file and field, and the folder's own files (iCloud conflict copies, the track files); (c) only when (b)
found nothing, load the trip the way the build does; (d) look at the loaded trip for the warnings and notes. Then the
checks that need every trip: content/home.json, goal outings, write-up links, repeated titles, region spellings, the
regions a journal's region_days name, and those that read rendered/site/meta.json (a region the site maps do not list;
a trip they still draw although it is a draft, is gone, or has lost its track; a region map drawn with other journal
days than region_days lists).

The file names in findings are always written content/trips/<slug>/..., whichever folder was read, exactly as
content.py writes them, so a run over a temporary folder (the tests, `tools/validate.py --content DIR`) reads the same.
"""
import difflib
import html
import json
import os
import posixpath
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import frontmatter  # noqa: E402
import goals  # noqa: E402
import markdown  # noqa: E402
import renderkey  # noqa: E402
import strava  # noqa: E402
from sitegen import author  # noqa: E402
from sitegen import core  # noqa: E402
from sitegen import curation  # noqa: E402
from sitegen.sitecheck import conflict_copy  # noqa: E402

# ---------------------------------------------------------------- what the files may hold (a new field is one line)

# index.md: every key content.load_trip, a page module, tools/render.py or tools/add_trip.py reads or writes
INDEX_KEYS = (
    'title', 'activity', 'subtype', 'kind', 'date', 'end_date', 'start_time', 'timezone', 'place', 'region', 'party',
    'route_shape', 'stats', 'featured', 'draft', 'beta', 'map', 'photos',
    'cover_photo', 'cover_focal_x', 'cover_focal_y', 'card_summary', 'search_aliases', 'journal_highlights',
    'region_days',
    'published_at', 'updated_at',
    'source',       # the service the recording came through (content.SOURCES): the word after 'via' in the stats note
    'summits',      # [{name, outcome, route}]: the Beta rail's Summits row and the search (content._summits)
    'strava_id',    # written by the first bulk import, on 156 trips and every day file; add_trip.py --list reads it
)
# days/NN.md (published_at / updated_at belong to index.md: in a day file they are unknown keys)
DAY_KEYS = ('day', 'title', 'date', 'start_time', 'stats', 'photos', 'hut', 'transfer_before', 'strava_id', 'summits')
SUMMIT_KEYS = ('name', 'outcome', 'route')
PHOTO_KEYS = ('file', 'w', 'h', 'alt', 'caption')
# keys a page once could have read and none does: the unknown-key warning says where the words go instead
RETIRED = {'conditions': 'conditions go in beta: rows, such as Snow, Weather or Water level, under the report\'s own date'}
STATS_KEYS = ('distance_km', 'moving', 'elapsed', 'gain_m', 'loss_m', 'high_m', 'low_m')
MAP_KEYS = ('peaks', 'places', 'water_labels')
BETA_KEYS = ('label', 'value')                       # both required
BETA_OPTIONAL = ('url',)                             # a guidebook or route page the value links to (benchmark-11)
HOME_KEYS = ('featured_slugs', 'region_maps')
AUTHOR_KEYS = author.KEYS                                       # content/author.json (sitegen.author.load refuses any other)
ABOUT_KEYS = ('photo', 'cover_focal_x', 'cover_focal_y')       # content/about.md (content.load_about)
REGION_INTRO_KEYS = ('title',)                                  # content/regions/<slug>.md (content.load_region_intros)

KINDS = ('trip', 'multi-day', 'series', 'planned')   # 'trip' is the single-day default, written by leaving the line out
DAY_KINDS = ('multi-day', 'series')                  # the kinds built from days/NN.md files
ROUTE_SHAPES = ('loop', 'out-and-back', 'point-to-point')
TEXT_FIELDS = ('place', 'region', 'party', 'route_shape', 'subtype', 'timezone', 'card_summary')
BOOL_FIELDS = ('draft', 'featured')
DAY_TEXT_FIELDS = ('title', 'hut')
DAY_BOOL_FIELDS = ('transfer_before',)
STATS_NUMBERS = ('distance_km', 'gain_m', 'loss_m', 'high_m', 'low_m')
STATS_NOT_NEGATIVE = ('distance_km', 'gain_m', 'loss_m')   # a high or low point can lie below sea level
STATS_TIMES = ('moving', 'elapsed')
LINK_SCHEMES = ('http', 'https', 'mailto')           # what a write-up link may use
FUTURE_DAYS = 1                                      # a trip dated tomorrow is a time zone, not a typo

LEVELS = ('error', 'warning', 'note')
_WORD = {'error': 'ERROR', 'warning': 'WARNING', 'note': 'NOTE'}
_SLUG = re.compile(r'[a-z0-9]+(-[a-z0-9]+)*')
# re.ASCII: only 0-9 are digits here. A date typed in full-width digits is not one the loader reads either.
_DATE = re.compile(r'\d{4}-\d{2}-\d{2}', re.ASCII)
_CLOCK = re.compile(r'(\d{1,2}):(\d{2})', re.ASCII)
_DURATION = re.compile(r'\d+(:[0-5]?\d){0,2}', re.ASCII)
_SCHEME = re.compile(r'^([A-Za-z][A-Za-z0-9+.-]*):')
_HREF = re.compile(r'<a href="([^"]*)"')
_WHERE = re.compile(r'^(content/.+?\.(?:md|json)): ')
_GPX_HEAD = 8192     # a GPX file names its root element in its first lines
_GPX_CHUNK = 65536
_DATALESS = 0x40000000   # macOS st_flags, SF_DATALESS: iCloud Drive holds the bytes, this disk the name and size


# ---------------------------------------------------------------- findings

def _finding(level, file, msg):
    return {'level': level, 'file': file, 'text': '%s: %s' % (file, msg)}


def _err(out, file, msg):
    out.append(_finding('error', file, msg))


def _warn(out, file, msg):
    out.append(_finding('warning', file, msg))


def _note(out, file, msg):
    out.append(_finding('note', file, msg))


def _raised(text, default_file):
    """An error for a message that already starts with its file (a ContentError, a CurationError), text unchanged."""
    m = _WHERE.match(text)
    return {'level': 'error', 'file': m.group(1) if m else default_file, 'text': text}


def _why(ex):
    """'IsADirectoryError: Is a directory', 'RuntimeError: boom': an exception as part of one line. An OSError gives its
    reason without the path (the finding names the file already, and not by where this checkout happens to live)."""
    reason = ex.strerror if isinstance(ex, OSError) and ex.strerror else str(ex)
    return '%s: %s' % (type(ex).__name__, ' '.join(reason.split()))


def _unreadable(out, file, ex, verb='read'):
    _err(out, file, 'could not be %s (%s)' % (verb, _why(ex)))


def errors(findings):
    return [f for f in findings if f['level'] == 'error']


def warnings(findings):
    return [f for f in findings if f['level'] == 'warning']


def notes(findings):
    return [f for f in findings if f['level'] == 'note']


def line(f):
    """The finding as it is printed: 'ERROR ' / 'WARNING ' / 'NOTE ' and its text."""
    return '%s %s' % (_WORD[f['level']], f['text'])


def summary(findings, counts=None):
    """'content: 0 errors, 1 warnings, 467 notes (168 trips, 398 photos, 341 GPX files)'. counts: the dict survey()
    returns beside the findings ({'trips', 'photos', 'gpx'}); left out, the numbers read 0."""
    c = counts or {}
    return ('content: %d errors, %d warnings, %d notes (%d trips, %d photos, %d GPX files)'
            % (len(errors(findings)), len(warnings(findings)), len(notes(findings)),
               c.get('trips', 0), c.get('photos', 0), c.get('gpx', 0)))


# ---------------------------------------------------------------- file names, as content.py writes them

def _index(slug):
    return 'content/trips/%s/index.md' % slug


def _day_file(slug, day_id):
    return 'content/trips/%s/days/%s.md' % (slug, day_id)


def _goal_file(slug):
    return 'content/trips/%s/goal.json' % slug


# ---------------------------------------------------------------- small value tests

def _as_date(v):
    """The calendar day a front-matter value stands for, or None when it is not one written YYYY-MM-DD. The parser
    hands dates over as text; a datetime.date is taken too, a number, a list or a date with a time is not. Stricter
    than content._date on purpose: date.fromisoformat reads '20250810' on Python 3.12 and refuses it on 3.9."""
    if isinstance(v, datetime):
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, str) and _DATE.fullmatch(v):
        try:
            return date(int(v[:4]), int(v[5:7]), int(v[8:10]))
        except ValueError:
            return None
    return None


def _is_clock(v):
    """HH:MM from 00:00 to 23:59 (core.ftime turns it into '6:30 AM')."""
    m = _CLOCK.fullmatch(v) if isinstance(v, str) else None
    return bool(m) and int(m.group(1)) <= 23 and int(m.group(2)) <= 59


def _is_duration(v):
    """What content._hm_to_s reads without an error or a negative result: 'H:MM' or 'H:MM:SS' as text, or a whole
    number of hours."""
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return v >= 0
    return isinstance(v, str) and bool(_DURATION.fullmatch(v))


def _is_whole(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _plural(n, word):
    return '%d %s%s' % (n, word, '' if n == 1 else 's')


def _iso(d):
    return d.isoformat()


def _unknown_keys(mapping, known, file, inside, out):
    """A warning for each key nothing reads, with the known key it most resembles: a typo such as `plase:` is otherwise
    ignored without a word and the place line simply goes missing."""
    for k in mapping:
        if k in known:
            continue
        near = difflib.get_close_matches(str(k), known, n=1, cutoff=0.6)
        hint = (' (did you mean %r?)' % near[0]) if near else ''
        if k in RETIRED:
            hint = ' (%s)' % RETIRED[k]
        _warn(out, file, 'unknown key %r%s%s; nothing reads it' % (k, (' in %s' % inside) if inside else '', hint))


# ---------------------------------------------------------------- (a) the raw files

def _split_file(path, file, out):
    """(meta, body) of one Markdown file, or None with an error finding: the file cannot be read as UTF-8 text, or its
    front matter does not parse (the message content.load_trip gives, unchanged)."""
    try:
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError) as ex:
        _unreadable(out, file, ex)
        return None
    try:
        parsed = frontmatter.split(text)
    except ValueError as ex:
        _err(out, file, 'front matter: %s' % ex)
        return None
    seen = set()
    for key in _top_keys(text):
        if key in seen:
            _warn(out, file, 'key %r is written twice in the front matter; only the last one is read' % key)
        seen.add(key)
    for n, kept, note in _cut_notes(text):
        _warn(out, file, 'line %d: %r after a space starts a note, so the line is read as %r; quote the value if the # '
                         'belongs to it' % (n, note, kept))
    return parsed


_TOP_KEY = re.compile(r'^([A-Za-z_][\w-]*):')


def _top_keys(text):
    """The keys written at the left margin of a file's front matter, in order, repeats included (the parser keeps the
    last of two and says nothing)."""
    if not text.startswith('---'):
        return []
    keys = []
    for ln in text.split('\n')[1:]:
        if ln.rstrip() == '---':
            return keys
        m = _TOP_KEY.match(ln)
        if m:
            keys.append(m.group(1))
    return []


def _cut_notes(text):
    """[(line number, the line as read, the note)] for front-matter lines where a note cut a value short in a way that
    looks unintended: the '#' is followed by a letter or digit ('Lap #2', '#hashtag'), as a value's own '#' is and a
    comment ('# a note') is not. frontmatter reads ' #' as YAML does: everything from it is a note."""
    if not text.startswith('---'):
        return []
    found = []
    for n, ln in enumerate(text.split('\n')[1:], 2):
        if ln.rstrip() == '---':
            return found
        if ln.lstrip().startswith('#'):
            continue
        kept = frontmatter._strip_comment(ln)
        note = ln[len(kept):].strip()
        if note[1:2].isalnum():
            found.append((n, kept.strip(), note))
    return []


def _nfc(name):
    """A file name in one Unicode form: macOS can hand back 'é' as two characters where index.md holds one."""
    return unicodedata.normalize('NFC', name)


def _listing(folder):
    """{name: is a folder} for what the build would publish from a folder (dot files are not copied)."""
    if not os.path.isdir(folder):
        return {}
    with os.scandir(folder) as it:
        return {e.name: e.is_dir() for e in it if not e.name.startswith('.')}


def _read_folder(folder, slug, out):
    """One trip folder as it is on disk, nothing interpreted yet: {'slug', 'folder', 'file' (its index.md, as findings
    name it), 'meta' / 'body' (None when index.md does not parse), 'days': [{'id', 'file', 'meta', 'body', 'gpx' (path
    or None)}] in the order content.load_trip reads them, 'photos': the listing of photos/, 'track': the path of
    track.gpx or None, 'gpx_files': how many GPX files the folder holds}."""
    rec = {'slug': slug, 'folder': folder, 'file': _index(slug), 'meta': None, 'body': None, 'days': [],
           'photos': {_nfc(n): d for n, d in _listing(os.path.join(folder, 'photos')).items()}, 'track': None,
           'gpx_files': 0}
    parsed = _split_file(os.path.join(folder, 'index.md'), rec['file'], out)
    if parsed:
        rec['meta'], rec['body'] = parsed
    track = os.path.join(folder, 'track.gpx')
    if os.path.exists(track):
        rec['track'] = track
        rec['gpx_files'] += 1
    days = os.path.join(folder, 'days')
    names = _listing(days)
    rec['gpx_files'] += sum(1 for n in names if n.endswith('.gpx'))
    for name in sorted(n for n in names if n.endswith('.md')):     # the order of content.load_trip's sorted glob
        stem = os.path.splitext(name)[0]
        d = {'id': stem, 'file': _day_file(slug, stem), 'meta': None, 'body': None, 'gpx': None}
        parsed = _split_file(os.path.join(days, name), d['file'], out)
        if parsed:
            d['meta'], d['body'] = parsed
        if stem + '.gpx' in names:
            d['gpx'] = os.path.join(days, stem + '.gpx')
        rec['days'].append(d)
    return rec


def _photo_count(rec):
    n = 0
    for meta in [rec['meta']] + [d['meta'] for d in rec['days']]:
        entries = meta.get('photos') if isinstance(meta, dict) else None
        if isinstance(entries, list):
            n += sum(1 for p in entries if isinstance(p, dict) and isinstance(p.get('file'), str) and p['file'])
    return n


# ---------------------------------------------------------------- (b) raw values

def _check_text(meta, keys, file, out):
    for k in keys:
        v = meta.get(k)
        if v is not None and not isinstance(v, str):
            # the wording content.load_trip uses for card_summary, so that message reads the same from either place
            _err(out, file, '%s must be text, got %r' % (k, v))


def _check_bool(meta, keys, file, out):
    """`draft: no` parses as the text 'no', which counts as true: the trip would vanish from the site without a word."""
    for k in keys:
        v = meta.get(k)
        if v is not None and not isinstance(v, bool):
            _err(out, file, '%s must be true or false, got %r' % (k, v))


def _check_date(meta, key, file, out):
    """The date under `key`, or None when the line is absent or (with an error finding) is not a real date."""
    v = meta.get(key)
    if v is None:
        return None
    d = _as_date(v)
    if d is None:
        _err(out, file, '%s must be a date written YYYY-MM-DD, got %r' % (key, v))
    return d


def _check_start_time(meta, file, out):
    v = meta.get('start_time')
    if v is not None and not _is_clock(v):
        _err(out, file, 'start_time must be a time written HH:MM (00:00 to 23:59), got %r' % (v,))


def _check_stats(meta, file, out):
    st = meta.get('stats')
    if st is None:
        return
    if not isinstance(st, dict):
        _err(out, file, 'stats must be a block of lines such as distance_km: 12.4, got %r' % (st,))
        return
    _unknown_keys(st, STATS_KEYS, file, 'stats', out)
    for k in STATS_NUMBERS:
        v = st.get(k)
        if v is None:
            continue
        if not _is_number(v):
            _err(out, file, 'stats.%s must be a number, got %r' % (k, v))
        elif v < 0 and k in STATS_NOT_NEGATIVE:
            _err(out, file, 'stats.%s cannot be negative, got %r' % (k, v))
    for k in STATS_TIMES:
        v = st.get(k)
        if v is not None and not _is_duration(v):
            _err(out, file, 'stats.%s must be a time written H:MM such as "6:10", got %r' % (k, v))


def _photo_path(value):
    """(file name inside photos/, None) for a `file:` the build can publish, else (None, what is wrong with it). Only
    files directly in photos/ are copied to the site, so that is the one place a photo may live. The value is taken as
    written, spaces and all: the pages put it into their links unchanged."""
    s = value
    if '\\' in s or s.startswith('/') or os.path.isabs(s):
        return None, 'must be a relative path inside the trip folder'
    parts = [x for x in s.split('/') if x not in ('', '.')]
    if not parts or '..' in parts:
        return None, 'may not leave the trip folder'
    if len(parts) != 2 or parts[0] != 'photos':
        return None, 'must be a file directly in photos/ (only that folder is published), such as photos/01.webp'
    return _nfc(parts[1]), None


def _check_photos(meta, rec, file, out):
    entries = meta.get('photos')
    if entries is None:
        return
    if not isinstance(entries, list):
        _err(out, file, 'photos must be a list of entries, each starting with - file: photos/<name>, got %r'
             % (entries,))
        return
    bad = next((i for i, p in enumerate(entries) if not isinstance(p, dict)), None)
    if bad is not None:
        _err(out, file, 'photos[%d] must be an entry with file, w, h and alt lines, got %r' % (bad, entries[bad]))
    for i, p in enumerate(entries):
        if not isinstance(p, dict):
            continue
        at = 'photos[%d]' % i
        _unknown_keys(p, PHOTO_KEYS, file, at, out)
        f = p.get('file')
        named = ''
        if f is None or f == '':
            _err(out, file, '%s has no file: line (an entry starts with - file: photos/<name>)' % at)
        elif not isinstance(f, str):
            _err(out, file, '%s.file must be a path such as photos/01.webp, got %r' % (at, f))
        else:
            named = ' (%s)' % f
            name, wrong = _photo_path(f)
            if wrong:
                _err(out, file, '%s.file %s, got %r' % (at, wrong, f))
            elif rec['photos'].get(name) is not False:      # absent, or a folder of that name
                _err(out, file, '%s.file %r is missing from the trip folder' % (at, f))
        w, h = p.get('w'), p.get('h')
        if (w is None) != (h is None):
            have, lack = ('w', 'h') if h is None else ('h', 'w')
            _err(out, file, '%s%s has %s but no %s; record both (the pixel size) or neither' % (at, named, have, lack))
        for k in ('w', 'h'):
            v = p.get(k)
            if v is not None and not _is_whole(v):
                _err(out, file, '%s.%s%s must be a positive whole number of pixels, got %r' % (at, k, named, v))
        for k in ('alt', 'caption'):
            v = p.get(k)
            if v is not None and not isinstance(v, str):
                _err(out, file, '%s.%s%s must be text, got %r' % (at, k, named, v))


def _check_beta(meta, file, out):
    """beta: rows of label / value, both text. A number is refused as well: `value: 5.10` parses as 5.1."""
    rows = meta.get('beta')
    if rows is None:
        return
    if not isinstance(rows, list):
        _err(out, file, 'beta must be a list of rows, each - label: ... with a value: line under it, got %r' % (rows,))
        return
    bad = next((i for i, r in enumerate(rows) if not isinstance(r, dict)), None)
    if bad is not None:
        _err(out, file, 'beta[%d] must be a row with a label: and a value: line, got %r' % (bad, rows[bad]))
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            continue
        hinted = set()     # keys the missing-key error already names as a typo, not reported twice below
        for k in BETA_KEYS:
            v = r.get(k)
            if v is None or v == '':
                near = difflib.get_close_matches(k, [x for x in r if x not in BETA_KEYS], n=1, cutoff=0.6)
                hinted.update(near)
                _err(out, file, 'beta[%d] has no %s%s' % (i, k, (' (is %r a typo for it?)' % near[0]) if near else ''))
            elif not isinstance(v, str):
                hint = ' (quote a number to keep it as written)' if _is_number(v) else ''
                _err(out, file, 'beta[%d].%s must be text, got %r%s' % (i, k, v, hint))
        url = r.get('url')
        if url is not None and not content.web_url(url):
            _err(out, file, 'beta[%d].url must be a full http or https address, such as '
                            'https://www.example.org/route, got %r' % (i, url))
        for k in r:
            if k not in BETA_KEYS + BETA_OPTIONAL and k not in hinted:
                near = difflib.get_close_matches(str(k).lower(), BETA_KEYS + BETA_OPTIONAL, n=1, cutoff=0.6)
                _warn(out, file, 'beta[%d] has an unknown key %r%s; a row takes label:, value: and url:'
                                 % (i, k, (' (is it %s:?)' % near[0]) if near else ''))


def _check_map(meta, file, out):
    mp = meta.get('map')
    if mp is None:
        return
    if not isinstance(mp, dict):
        _err(out, file, 'map must be a block of lines such as peaks: [Mount Tallac], got %r' % (mp,))
        return
    _unknown_keys(mp, MAP_KEYS, file, 'map', out)
    pk = mp.get('peaks')
    names = isinstance(pk, list) and all(isinstance(x, str) for x in pk)
    if pk is not None and not isinstance(pk, str) and not names:
        _err(out, file, 'map.peaks must be a name or a list of names such as [Mount Tallac], got %r' % (pk,))


def gpx_problem(path):
    """None when the file is GPX with at least one track or route point, else what is wrong with it, as the end of a
    sentence. A recorded track is trusted content, so this looks at structure only and reads no further than it must:
    the root element in the first lines, then on to the first point. A file iCloud Drive has offloaded is not opened
    at all (its size is still known): reading one byte would fetch the whole file and stall the build, and a checkout
    from git, which is what gets published, never has such files."""
    try:
        st = os.stat(path)
        if st.st_size == 0:
            return 'is empty'
        if getattr(st, 'st_flags', 0) & _DATALESS:
            return None
        with open(path, 'rb') as fh:
            head = fh.read(_GPX_HEAD)
            if b'<gpx' not in head:
                return 'is not a GPX file (no <gpx> element at its start)'
            tail = head
            while True:
                if b'<trkpt' in tail or b'<rtept' in tail:
                    return None
                more = fh.read(_GPX_CHUNK)
                if not more:
                    return 'holds no track or route point'
                tail = tail[-8:] + more      # a tag cut in two by the chunk boundary
    except OSError as ex:
        return 'could not be read (%s)' % _why(ex)


def _check_tracks(rec, out):
    """A report's track.gpx and its days' NN.gpx, when present, must be GPX with a point: an empty file is otherwise
    offered as a download and drawn as nothing. A goal's file is the importer's business (goals.validate checks it
    against the SHA-256 it recorded)."""
    slug = rec['slug']
    files = [('content/trips/%s/track.gpx' % slug, rec['track'])]
    files += [('content/trips/%s/days/%s.gpx' % (slug, d['id']), d['gpx']) for d in rec['days']]
    sound = []
    for file, path in files:
        wrong = gpx_problem(path) if path else None
        if wrong:
            _err(out, file, 'the file %s; a report\'s track must be a GPX file with at least one point (without the '
                            'file there is no map and no download for it)' % wrong)
        elif path:
            sound.append((file, path))
    kind = rec['meta'].get('kind') if isinstance(rec['meta'], dict) else None
    if rec['days'] and rec['track'] and kind in DAY_KINDS:
        _warn(out, files[0][0], 'is not used: this trip has day files, and its page, maps and downloads come from '
                                'days/NN.gpx; remove the file')
    if kind == 'multi-day':
        # "Download all GPX" is made of the day files' <trk> blocks (tools/build.py): a day file that holds only a
        # route adds nothing to it, and when no day file has a track the built-site check refuses the empty download
        days = [(file, path) for file, path in sound if '/days/' in file]
        routes = [file for file, path in days if not _has_trk(path)]
        if days and len(routes) == len(days):
            _err(out, rec['file'], 'none of the day GPX files holds a recorded track (<trk>): "Download all GPX" would be '
                                   'an empty file; a day\'s file is that day\'s recording')
        else:
            for file in routes:
                _warn(out, file, 'holds a route and no recorded track (<trk>): "Download all GPX" leaves this day out')


def _has_trk(path):
    """True when a GPX file holds a <trk> element (an offloaded file is not opened: see gpx_problem)."""
    try:
        if getattr(os.stat(path), 'st_flags', 0) & _DATALESS:
            return True
        with open(path, 'rb') as fh:
            tail = b''
            while True:
                more = fh.read(_GPX_CHUNK)
                if not more:
                    return False
                tail = tail[-8:] + more
                if re.search(rb'<trk[\s>]', tail):
                    return True
    except OSError:
        return True               # gpx_problem has already said what is wrong with it


def _check_copies(rec, out):
    """iCloud Drive conflict copies inside a trip folder: the same name with a space and a number ('02 2.md',
    'index 2.md'). .gitignore hides the ones under rendered/; here they are content. A copy of a day file is read as
    one more day and published, so it stops the build; any other copy is not read, but `git add` of the folder would
    stage it. (A copy in photos/ gets the 'not declared under photos:' warning, since the build publishes it.)"""
    slug, folder = rec['slug'], rec['folder']
    for sub in ('', 'days/'):
        for name in sorted(_listing(os.path.join(folder, sub) if sub else folder)):
            if not conflict_copy(name):
                continue
            file = 'content/trips/%s/%s%s' % (slug, sub, name)
            if sub and name.endswith(('.md', '.gpx')):
                _err(out, file, 'looks like an iCloud conflict copy (the name ends in a space and a number): it would be '
                                'published as one more day; delete it')
            else:
                _warn(out, file, 'looks like an iCloud conflict copy (the name ends in a space and a number): nothing '
                                 'reads it, but git add of the folder would stage it; delete it')


def _check_kind(rec, out):
    """kind: against the day files. A kind the page modules do not know, or day files beside a single-day kind, builds
    no page at all, and every link to the trip is then dead."""
    meta, file = rec['meta'], rec['file']
    kind = meta.get('kind')
    n_days = len(rec['days'])
    if kind is not None and (not isinstance(kind, str) or kind not in KINDS):
        _err(out, file, 'kind must be one of %s (leave the line out for a single-day report), got %r'
             % (', '.join(k for k in KINDS if k != 'trip'), kind))
    elif (kind or 'trip') in DAY_KINDS and not n_days:
        _err(out, file, 'kind is %r but the folder has no day files (days/01.md, days/02.md, ...)' % kind)
    elif (kind or 'trip') not in DAY_KINDS and n_days:
        files = _plural(n_days, 'day file')
        if kind:
            _err(out, file, 'days/ holds %s but kind is %r; day files belong to kind: multi-day (or kind: series for a '
                            'journal): change the kind or remove days/' % (files, kind))
        else:
            _err(out, file, 'days/ holds %s but there is no kind: line; add kind: multi-day (or kind: series for a '
                            'journal)' % files)


def _check_span(rec, out):
    """date and end_date of index.md, and the two against each other. Without a date: line the page starts the trip on
    its first day's date (content.load_trip), so an end_date is compared with that."""
    meta, file = rec['meta'], rec['file']
    start = _check_date(meta, 'date', file, out)
    end = _check_date(meta, 'end_date', file, out)
    if end is None:
        return
    if start is not None:
        if end < start:
            _err(out, file, 'end_date %s is before date %s' % (_iso(end), _iso(start)))
    elif meta.get('date') is None and rec['days'] and rec['days'][0]['meta'] is not None:
        first = rec['days'][0]
        first_day = _as_date(first['meta'].get('date'))
        if first_day is not None and end < first_day:
            _err(out, file, 'end_date %s is before the first day\'s date %s (days/%s.md)'
                 % (_iso(end), _iso(first_day), first['id']))


def _check_index(rec, out):
    """Every raw-value rule of index.md. The older fields (title, activity, kind, dates, stats, photos, beta, map) were
    never checked on load: each rule here names a value that used to end in a traceback, a dead link or a page that
    quietly said something else."""
    meta, file = rec['meta'], rec['file']
    _unknown_keys(meta, INDEX_KEYS, file, '', out)
    title = meta.get('title')
    if title is None or (isinstance(title, str) and not title.strip()):
        _err(out, file, 'title is missing or empty (write the trip\'s name after title:)')
    elif not isinstance(title, str):
        _err(out, file, 'title must be text, got %r' % (title,))
    acts = ', '.join(content.ACTIVITIES)
    act = meta.get('activity')
    if act is None:
        _err(out, file, 'activity is missing; it must be one of %s' % acts)
    elif not isinstance(act, str) or act not in content.ACTIVITIES:
        _err(out, file, 'activity must be one of %s, got %r' % (acts, act))
    _check_kind(rec, out)
    _check_span(rec, out)
    _check_bool(meta, BOOL_FIELDS, file, out)
    _check_start_time(meta, file, out)
    _check_text(meta, TEXT_FIELDS, file, out)
    for key, allowed in (('route_shape', ROUTE_SHAPES), ('subtype', content.OTHER_SUBTYPES)):
        v = meta.get(key)
        if isinstance(v, str) and v not in allowed:
            _warn(out, file, '%s %r is not one of %s; it is shown as written' % (key, v, ', '.join(allowed)))
    src = meta.get('source')
    if src is not None and src not in content.SOURCES:
        _err(out, file, 'source must be one of %s (the service the recording came through, named in the stats note), got '
                        '%r; leave the line out when it is none of them' % (', '.join(content.SOURCES), src))
    _check_stats(meta, file, out)
    _check_photos(meta, rec, file, out)
    _check_beta(meta, file, out)
    _check_map(meta, file, out)
    _check_summits(meta, file, out)


def _check_summits(meta, file, out):
    """summits: a list of entries, each with a name (text), an optional outcome from content.SUMMIT_OUTCOMES and an
    optional route (text); a name only once per file. Written by hand, so a wrong entry is an error, not a guess."""
    raw = meta.get('summits')
    if raw is None:
        return
    if not isinstance(raw, list):
        _err(out, file, 'summits must be a list of entries, each starting with - name: <summit>, got %r' % (raw,))
        return
    seen = set()
    for i, e in enumerate(raw):
        at = 'summits[%d]' % i
        if not isinstance(e, dict):
            _err(out, file, '%s must be an entry with a name: line (- name: <summit>), got %r' % (at, e))
            continue
        _unknown_keys(e, SUMMIT_KEYS, file, at, out)
        name = e.get('name')
        if not isinstance(name, str) or not name.strip():
            _err(out, file, '%s has no name: line; each entry names one summit' % at)
        elif name.strip().casefold() in seen:
            _err(out, file, '%s: %r is in the list twice' % (at, name.strip()))
        else:
            seen.add(name.strip().casefold())
        outcome = e.get('outcome')
        if outcome is not None and outcome not in content.SUMMIT_OUTCOMES:
            _err(out, file, '%s.outcome must be one of %s, got %r' % (at, ', '.join(content.SUMMIT_OUTCOMES), outcome))
        route = e.get('route')
        if route is not None and not isinstance(route, str):
            _err(out, file, '%s.route must be text, got %r' % (at, route))


def _check_day(rec, d, out):
    meta, file = d['meta'], d['file']
    _unknown_keys(meta, DAY_KEYS, file, '', out)
    _check_summits(meta, file, out)
    _check_date(meta, 'date', file, out)
    _check_text(meta, DAY_TEXT_FIELDS, file, out)
    _check_bool(meta, DAY_BOOL_FIELDS, file, out)
    _check_start_time(meta, file, out)
    _check_stats(meta, file, out)
    _check_photos(meta, rec, file, out)


def _check_raw(rec, out):
    """Stage (b) for one folder: its name, index.md, each day file, the photos folder and the track files."""
    slug, file = rec['slug'], rec['file']
    if not _SLUG.fullmatch(slug):
        fix = content.slugify(slug)
        _err(out, file, 'the folder name %r cannot be a page address: use lower-case letters, digits and single '
                        'dashes%s' % (slug, (' (such as %s)' % fix) if fix else ''))
    _check_copies(rec, out)
    for name, is_dir in sorted(rec['photos'].items()):
        if is_dir:
            _err(out, file, 'photos/%s is a folder; photos/ may hold files only (the build copies each entry as one '
                            'file)' % name)
    if rec['meta'] is not None:
        _check_index(rec, out)
    for d in rec['days']:
        if d['meta'] is not None:
            _check_day(rec, d, out)
    if rec['meta'] is None or rec['meta'].get('kind') != 'planned':
        _check_tracks(rec, out)


# ---------------------------------------------------------------- (d) the loaded trip

def _entries(rec):
    """Every declared photo of a loaded trip, in page order: (the Markdown file declaring it, its index there, the
    entry)."""
    out = []
    for file, meta in [(rec['file'], rec['meta'])] + [(d['file'], d['meta']) for d in rec['days']]:
        for i, p in enumerate(meta.get('photos') or []):
            out.append((file, i, p))
    return out


def _derived(name, suffix):
    """'01.webp', '.sm' -> '01.sm.webp': the name of a photo's smaller copy."""
    base, ext = os.path.splitext(name)
    return base + suffix + ext


def _photo_warnings(t, rec, out):
    slug, have = t['slug'], rec['photos']
    seen, declared, uncaptioned = {}, set(), {}
    for file, i, p in _entries(rec):
        name, _wrong = _photo_path(p['file'])
        key, at = 'photos/' + name, 'photos[%d]' % i
        if key in seen:
            _warn(out, file, '%s declares %s again (first in %s, photos[%d]); the page shows it twice'
                  % (at, key, posixpath.basename(seen[key][0]), seen[key][1]))
            continue
        seen[key] = (file, i)
        declared.add(name)
        if p.get('w') is None:
            _warn(out, file, '%s (%s) has no w and h, so the page cannot hold its place while it loads; record the '
                             'pixel size' % (at, key))
        if not (p.get('alt') or '').strip():
            _warn(out, file, '%s (%s) has no alt text; describe the photo in a sentence' % (at, key))
        if _derived(name, '.sm') not in have:
            _warn(out, file, '%s (%s) has no 800 px copy (%s), so phones load the full file'
                  % (at, key, _derived(name, '.sm')))
        if not (p.get('caption') or '').strip():
            uncaptioned[file] = uncaptioned.get(file, 0) + 1
    for file, n in sorted(uncaptioned.items()):
        _note(out, file, '%s without a caption' % _plural(n, 'photo'))
    cover = (t.get('cover') or {}).get('photo')
    if cover:
        name, _wrong = _photo_path(cover['file'])
        if _derived(name, '.th') not in have:
            _warn(out, rec['file'], 'cover photos/%s has no card-size copy (.th); run python3 tools/thumbs.py %s'
                  % (name, slug))
    copies = set(_derived(n, s) for n in declared for s in ('.sm', '.th'))
    for name in sorted(have):
        if name not in declared and name not in copies:
            _warn(out, 'content/trips/%s/photos/%s' % (slug, name),
                  'not declared under photos: in index.md or a days/NN.md, and not the .sm or .th copy of a declared '
                  'photo; the build publishes it all the same')


def _date_warnings(t, rec, today, out):
    meta, file = rec['meta'], rec['file']
    if t['kind'] == 'planned':
        if meta.get('date') is not None:
            _warn(out, file, 'a planned route has a date: line (%s); a goal has no date, and an outing\'s date goes in '
                             'goal.json' % meta['date'])
        return
    if t['date'] is None:
        _warn(out, file, 'no date (add date: YYYY-MM-DD): the page, its card and the feed show none and the trip sorts '
                         'last')
    limit = today + timedelta(days=FUTURE_DAYS)
    dated = [(file, k, _as_date(meta.get(k))) for k in ('date', 'end_date')]
    dated += [(d['file'], 'date', _as_date(d['meta'].get('date'))) for d in rec['days']]
    for where, key, day in dated:
        if day is not None and day > limit:
            _warn(out, where, '%s %s is in the future (today is %s)' % (key, _iso(day), _iso(today)))
    last = None
    for d in rec['days']:
        day = _as_date(d['meta'].get('date'))
        if day is None:
            continue
        if last and day < last[1]:
            _warn(out, d['file'], 'date %s is before the day ahead of it (days/%s.md, %s); days are shown in file order'
                  % (_iso(day), last[0], _iso(last[1])))
        else:
            last = (d['id'], day)
    stated_end = _as_date(meta.get('end_date'))
    if stated_end is not None:
        for d in rec['days']:
            day = _as_date(d['meta'].get('date'))
            if day is not None and day > stated_end:
                _warn(out, d['file'], 'date %s is after the trip\'s end_date %s (index.md), so the page\'s dates end '
                                      'before this day' % (_iso(day), _iso(stated_end)))
    # without an end_date: line the page ends the trip on its last day's date (content.load_trip)
    start = _as_date(meta.get('date'))
    final = rec['days'][-1] if rec['days'] else None
    end = _as_date(final['meta'].get('date')) if final and meta.get('end_date') is None else None
    if start is not None and end is not None and end < start:
        _warn(out, file, 'date %s is after the last day\'s date %s (days/%s.md), so the page would end the trip before '
                         'it starts' % (_iso(start), _iso(end), final['id']))


def _goal_findings(t, rec, today, out):
    """What goals.validate does not look at: the sidecar against the folder, and the outings against the calendar."""
    slug, goal = t['slug'], t['goal']
    if goal.get('legacy'):
        _warn(out, rec['file'], 'planned route without goal.json: it is listed with the default status and priority; '
                                'review it and run python3 tools/ticklist.py update %s to give it one' % slug)
        return
    file = _goal_file(slug)
    if goal.get('route') and not t['track']:
        _err(out, file, 'the route block is there but track.gpx is missing from the folder: the page would describe a '
                        'route it can neither draw nor offer; put the file back')
    if t['track']:
        if not goal.get('route'):
            _warn(out, file, 'track.gpx is published but there is no route block, so nothing records where the file '
                             'came from or how it was measured')
        if not goal['route_source'].get('public_copy_approved'):
            _warn(out, file, 'track.gpx is published but route_source.public_copy_approved is false; set it to true '
                             'once you approve publishing the file, or remove track.gpx')
    first = {}
    for i, o in enumerate(goal['outings']):
        day = _as_date(o.get('date'))
        if day is not None and day > today:
            _warn(out, file, 'outings[%d].date %s is in the future (today is %s); an outing is something that happened'
                  % (i, _iso(day), _iso(today)))
        rs = o.get('report_slug')
        if rs in first:
            _warn(out, file, 'outings[%d].report_slug %r is already named by outings[%d]' % (i, rs, first[rs]))
        elif rs:
            first[rs] = i


_NAMES_A_SUMMIT = re.compile(r'\b(Peak|Mount|Mountain|Couloir|Chute|Bowl|Lake)\b')


def _trip_findings(t, rec, today, rendered_dir, out):
    """Stage (d): the warnings and notes of one loaded trip (and the one goal error that needs the loaded sidecar)."""
    slug, file, kind = t['slug'], rec['file'], t['kind']
    _date_warnings(t, rec, today, out)
    if kind == 'trip' and not t['track']:
        _warn(out, file, 'no track.gpx: the page has no map, no profile and no GPX download')
    if t['days'] and not any(d['track'] for d in t['days']):
        _warn(out, file, 'none of the %s has a GPX (days/NN.gpx): the page shows an empty map and offers no downloads'
              % _plural(len(t['days']), 'day'))
    _photo_warnings(t, rec, out)
    # a heading of a write-up that skips a level is a gap on the page (the site check's HEADING line): stop here instead
    for where, body in [(file, t['body_md'])] + [(_day_file(slug, d['id']), d['body_md']) for d in t['days']]:
        _heading_jumps(where, body, out)
    if kind == 'planned':
        _goal_findings(t, rec, today, out)
    if kind == 'multi-day':
        first = {}
        for d in t['days']:
            if d['label'] in first:
                _warn(out, _day_file(slug, d['id']), 'day label %r is also the label of days/%s.md; give each day its '
                                                     'own day: line' % (d['label'], first[d['label']]))
            else:
                first[d['label']] = d['id']
    has_track = bool(t['track']) or any(d['track'] for d in t['days'])
    if rendered_dir and has_track and not t['draft']:
        meta_file = os.path.join(rendered_dir, 'trips', slug, 'meta.json')
        if not os.path.exists(meta_file):
            # a series page keeps its own map section (DEVELOPING.md, "No file, no control"); the others show the box
            _warn(out, file, 'no rendered map (rendered/trips/%s/meta.json is missing); run python3 tools/render.py %s%s'
                  % (slug, slug, '' if kind == 'series' else ' (until then the page shows "Map not rendered yet")'))
        else:
            stale = _render_staleness(t, meta_file)
            if stale:
                _warn(out, file, stale)
    if kind != 'planned' and t['track'] and t.get('timezone') == 'UTC' and t.get('start_time'):
        # tracks.guess_tz answers UTC where it knows no zone: the page's Start line is then a UTC clock
        _note(out, file, 'timezone is UTC, so start_time is a UTC clock; set the zone with python3 tools/add_trip.py '
                         '--retime %s --timezone <zone>' % slug)
    if kind != 'planned':
        # a Strava default ('Hike near South Lake Tahoe') names a town, not a summit: the content report flags those
        if (_NAMES_A_SUMMIT.search(t['title']) and not ((t.get('map') or {}).get('peaks'))
                and not strava.default_title(t['title'])):
            _note(out, file, 'the title names a summit or a feature (%s) and there is no map: peaks: line; the name there '
                             'labels the map and is found by the search' % _NAMES_A_SUMMIT.search(t['title']).group(0))
        if not t.get('place'):
            _note(out, file, 'no place')
        if not t['has_writeup']:
            _note(out, file, 'no write-up')
        if not t['photos'] and not any(d['photos'] for d in t['days']):
            _note(out, file, 'no photos')
    for d in t['days']:
        if not d.get('title'):
            _note(out, _day_file(slug, d['id']), 'no title')


def _offloaded(paths):
    """True when iCloud Drive holds the bytes of one of these files and this disk only its name: hashing it would make
    a check wait for a download, so a check that needs the bytes says nothing instead."""
    for p in paths:
        try:
            if p and getattr(os.stat(p), 'st_flags', 0) & _DATALESS:
                return True
        except OSError:
            pass
    return False


def _render_staleness(t, meta_file):
    """Why the maps in rendered/trips/<slug>/ no longer match the trip, or None: render.py stores the hash of what it
    drew from (renderkey.trip_inputs) and of a run that lost its OpenStreetMap data writes null. A meta.json without a
    'hash' key was not written by render.py, and a track iCloud Drive has offloaded is not read: nothing is said."""
    try:
        with open(meta_file, encoding='utf-8') as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(meta, dict) or 'hash' not in meta:
        return None
    if meta['hash'] is None or meta.get('osm_failed'):
        return ('maps were drawn without OpenStreetMap data (no roads, trails or lake names); run python3 tools/render.py '
                '%s again' % t['slug'])
    if _offloaded(renderkey.input_files(t)):
        return None
    if meta['hash'] != _inputs(t):
        return ('maps were drawn from other inputs (the track, the title, activity, kind, map: or stats changed since): '
                'run python3 tools/render.py %s' % t['slug'])
    return None


_INPUTS = {}


def _inputs(t, how=None):
    """renderkey.trip_inputs (or another of its functions, how), once per trip and run (the site maps' hash asks again
    for every trip on a map)."""
    how = how or renderkey.trip_inputs
    key = (t['slug'], t['dir'], how.__name__)
    if key not in _INPUTS:
        _INPUTS[key] = how(t)
    return _INPUTS[key]


def _site_inputs(t):
    return _inputs(t, renderkey.site_inputs)


def _site_hash_findings(live, rendered_dir, out):
    """The region and ski maps under rendered/site/ drawn from other inputs than the trips have now (a title, a track or
    a region changed, a trip was added or taken out), or without OpenStreetMap data. One warning for the whole folder,
    and none when another line of the run already asks for a render: `render.py <slug>` draws the site maps again too,
    and the other lines (a trip's maps, a draft or a gone trip still drawn, journal days) say why."""
    try:
        with open(os.path.join(rendered_dir, 'site', 'meta.json'), encoding='utf-8') as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        return
    if not isinstance(meta, dict) or 'hash' not in meta or any('tools/render.py' in f['text'] for f in out):
        return
    if meta['hash'] is None:
        _warn(out, 'rendered/site/meta.json', 'the region and ski maps were drawn without OpenStreetMap data; run python3 '
                                              'tools/render.py --site again and commit rendered/site/')
        return
    # content.load_all's order: by folder name, then newest first (the order is part of the hash)
    trips = sorted(live, key=lambda t: (t['date'] or date.min), reverse=True)
    if _offloaded([p for t in trips for p in renderkey.input_files(t)]):
        return
    try:
        jobs = renderkey.site_jobs(trips)[0]
        now = (renderkey.site_hash(jobs, _site_inputs), renderkey.site_hash_with_titles(jobs, _inputs))
        if meta['hash'] not in now:
            # the hash written before Phase 9 holds every title as the maps were drawn; a retitle since (the build writes
            # the new title into the labels) matches it with the title the trip's pin shows, until the next site render
            maps = meta.get('maps')
            frags = renderkey.drawn_paths(os.path.join(rendered_dir, 'site'), maps if isinstance(maps, dict) else {})
            if _offloaded(frags):
                return
            drawn = renderkey.drawn_titles(frags)
            if drawn:
                now += (renderkey.site_hash_as_drawn(jobs, drawn, _inputs),)
    except Exception:   # noqa: BLE001 — a goal file the renderer could not read either: its own check names it
        return
    if meta['hash'] not in now:
        _warn(out, 'rendered/site/meta.json', 'the region and ski maps were drawn from other inputs (a trip on one of them '
                                              'changed, was added or was taken out since); run python3 tools/render.py '
                                              '--site and commit rendered/site/')


# ---------------------------------------------------------------- the checks that need every trip

def _links(body):
    """The link targets a write-up produces, read back from the HTML the pages will carry (so a link inside `code`, or
    a bare address the generator links by itself, is judged exactly as it is published)."""
    text = re.sub(r'<!--.*?-->', '', body or '', flags=re.S)
    if '](' not in text and '://' not in text:
        return []
    return [html.unescape(h) for h in _HREF.findall(markdown.to_html(text))]


def _own_path(url):
    """The site-relative path of an absolute link to this site ('trips/x/' for SITE_URL + 'trips/x/'), else None."""
    for base in (core.SITE_URL, core.SITE_URL.replace('https://', 'http://', 1)):
        if url.startswith(base):
            return url[len(base):]
    return None


def _link_problem(url, slug, pages, drafts):
    """What is wrong with one write-up link of trips/<slug>/, or None. pages: the slugs that have a page; drafts: the
    slugs kept off the site. Anchors and files inside a page are the built-site check's business (sitecheck)."""
    if url.startswith('#'):
        return None
    if url.startswith('/'):
        return ('starts with /, which leaves the site (it is served under %s); write a relative link such as '
                '../other-trip/ or the full address' % core.SITE_URL)
    m = _SCHEME.match(url)
    if m:
        scheme = m.group(1).lower()
        if scheme not in LINK_SCHEMES:
            return 'uses %s:, and only %s links are accepted' % (scheme, ', '.join(LINK_SCHEMES))
        path = _own_path(url)
        if path is None:
            return None
    else:
        path = posixpath.join('trips/%s/' % slug, url)
    path = posixpath.normpath(path.split('#')[0].split('?')[0] or '.')
    m = re.match(r'trips/([^/]+)(?:/|$)', path)
    target = m.group(1) if m else None
    if target is None or target == slug or target in pages:
        return None
    if target in drafts:
        return 'points at trips/%s/, a draft, which has no page' % target
    return 'points at trips/%s/, which is not a page of the site (no content/trips/%s/index.md)' % (target, target)


def _link_findings(records, pages, drafts, out):
    for rec in records:
        # a draft may point at another draft: both are still off the site
        ok = (pages | drafts) if rec['slug'] in drafts else pages
        for file, body in [(rec['file'], rec['body'])] + [(d['file'], d['body']) for d in rec['days']]:
            for url in _links(body):
                wrong = _link_problem(url, rec['slug'], ok, drafts)
                if wrong:
                    _err(out, file, 'write-up link %r %s' % (url, wrong))


def _home_findings(home_json, by_slug, trips_dir, rendered_dir, out):
    """content/home.json through curation's own rules (messages unchanged), plus its unknown keys. A missing file is the
    one case the build tolerates: it falls back to the old pick, which is worth a line every time."""
    try:
        manifest = curation.load_manifest(home_json)
        if manifest is None:
            _warn(out, curation.FILE, 'the file is missing, so the home page falls back to the newest featured report; '
                                      'create it to choose the featured trips (see docs/CONTENT_GUIDE.md)')
            return
        _unknown_keys(manifest, HOME_KEYS, curation.FILE, '', out)
        curation.resolve_featured({'by_slug': by_slug, 'published': []}, manifest, trips_dir=trips_dir)
    except curation.CurationError as ex:
        out.append(_raised(str(ex), curation.FILE))
        return
    if 'region_maps' in manifest and rendered_dir:
        try:
            with open(os.path.join(rendered_dir, 'site', 'meta.json'), encoding='utf-8') as fh:
                meta = json.load(fh)
        except (OSError, ValueError):
            return                # no site maps to check the names against here; the build checks them against its own
        try:
            curation.resolve_region_maps(manifest, meta if isinstance(meta, dict) else {})
        except curation.CurationError as ex:
            out.append(_raised(str(ex), curation.FILE))


def _outing_findings(loaded, by_slug, out):
    """goals.validate_site, one outing at a time, so every outing that names something other than a published report is
    reported in one run (the function itself stops at the first)."""
    for t in loaded:
        if t['kind'] != 'planned' or t['draft']:
            continue
        for o in t['goal']['outings']:
            try:
                goals.validate_site({'by_slug': by_slug, 'goals': [{'slug': t['slug'], 'goal': {'outings': [o]}}]})
            except content.ContentError as ex:
                out.append(_raised(str(ex), _goal_file(t['slug'])))


def _title_findings(live, out):
    """Two published reports with one title and one date: their pages get the same <title>, which the date was meant to
    tell apart."""
    first = {}
    for t in live:
        if t['kind'] == 'planned' or t['date'] is None:
            continue
        key = (t['title'], t['date'])
        if key in first:
            _warn(out, _index(t['slug']), 'same title and date as %s (%r, %s): the two pages get the same <title>'
                  % (_index(first[key]), t['title'], _iso(t['date'])))
        else:
            first[key] = t['slug']


def _region_spellings(live, out):
    """'Eastern Sierra' beside 'eastern sierra': one slug, so one filter value and one map anchor, but two regions
    wherever the name itself is compared. The spelling most trips use is taken as the intended one."""
    spellings = {}
    for t in live:
        if t.get('region'):
            spellings.setdefault(content.slugify(t['region']), {}).setdefault(t['region'], []).append(t['slug'])
    for rslug, names in sorted(spellings.items()):
        if len(names) < 2:
            continue
        main = sorted(names, key=lambda n: (-len(names[n]), n))[0]
        for name in sorted(n for n in names if n != main):
            for slug in names[name]:
                _warn(out, _index(slug), 'region %r is written %r on %s; the two are listed as different regions but '
                                         'share one filter value and one map anchor (%s)'
                      % (name, main, _plural(len(names[main]), 'other trip'), rslug))


def _region_findings(live, rendered_dir, out):
    """A report whose region the rendered site maps do not know: the map page lists regions from that file, so the trip
    is missing from it until the site maps are drawn again (render.py: every non-journal report with a region)."""
    try:
        with open(os.path.join(rendered_dir, 'site', 'meta.json'), encoding='utf-8') as fh:
            known = json.load(fh).get('all_regions')
    except (OSError, ValueError, AttributeError):
        return                    # no such file, or not one this check can read: the build has its own say about that
    if not isinstance(known, list):
        return
    missing = {}
    for t in live:
        if t['kind'] in ('trip', 'multi-day') and t.get('region') and t['region'] not in known:
            missing.setdefault(t['region'], []).append(t['slug'])
    for region, slugs in sorted(missing.items()):
        more = (' (and %s)' % _plural(len(slugs) - 1, 'more trip')) if len(slugs) > 1 else ''
        _warn(out, _index(slugs[0]), 'region %r%s is not in rendered/site/meta.json, so the map page does not list it '
                                     'yet; run python3 tools/render.py --site --force' % (region, more))


def _site_map_findings(live, by_slug, drafts, rendered_dir, out):
    """A trip the rendered site maps still draw although it no longer has a page with a track: a draft, a folder that was
    removed, or a report whose track.gpx is gone. The region maps (on the home page, the Map page and the Ski page) are
    drawn by tools/render.py and committed. Since Phase 8 the build leaves such a trip's own pin and line out of them
    (core.gone_keys, core.drop_keys), so the site and its check pass; a numbered cluster the trip was merged into keeps
    its count and its title until the maps are drawn again. rendered/site/meta.json lists the trips each map draws."""
    try:
        with open(os.path.join(rendered_dir, 'site', 'meta.json'), encoding='utf-8') as fh:
            maps = json.load(fh).get('maps')
    except (OSError, ValueError, AttributeError):
        return
    if not isinstance(maps, dict):
        return
    drawn = set()
    for m in maps.values():
        if isinstance(m, dict) and isinstance(m.get('trips'), list):
            drawn.update(s for s in m['trips'] if isinstance(s, str))
    tracked = {t['slug']: core.has_track(t) for t in live}
    for slug in sorted(drawn):
        if slug in drafts:
            why = 'is a draft'
        elif slug in tracked:
            if tracked[slug]:
                continue
            why = 'has no track any more'
        elif slug in by_slug:
            continue              # a folder that does not load: its own error says so, and it may well have a track
        else:
            why = 'has no folder under content/trips any more'
        _warn(out, _index(slug), 'the site maps under rendered/site/ still draw this trip, which %s: the build leaves '
                                 'its own pin and line out of them; run python3 tools/render.py --site when online (and '
                                 'commit rendered/site/) to redraw the maps, their merged pins and counts' % why)


def _journal_region_findings(live, rendered_dir, out):
    """A journal's region_days (content.py) name regions and the days of the journal that lie in them. A region that no
    report is filed under is a mistyped name: the days would be drawn and listed nowhere (an error). A region without a
    region map shows them on no map either (render.py draws a region map from three reports with a track). And a region
    map drawn before the days were listed, or with other days, shows what it was drawn with until the site maps are
    drawn again; so does one that still draws days the journal no longer lists there."""
    regions = {t['region'] for t in live if t['kind'] in ('trip', 'multi-day') and t.get('region')}
    try:
        with open(os.path.join(rendered_dir or '', 'site', 'meta.json'), encoding='utf-8') as fh:
            meta = json.load(fh)
        maps, mapped = meta.get('maps'), meta.get('regions')
    except (OSError, ValueError, AttributeError):
        maps = mapped = None
    if not isinstance(maps, dict) or not isinstance(mapped, list):
        maps = mapped = None      # no such file, or not one this check can read: only the names are checked

    def drawn_days(name, slug, key):
        """(the day ids, {day id: stretch}) the region's map drew of this part; (None, {}) when it drew nothing of it."""
        entry = maps.get('region-%s-desktop' % content.slugify(name))
        js = entry.get('journals') if isinstance(entry, dict) else None
        for j in js if isinstance(js, list) else []:
            if isinstance(j, dict) and j.get('slug') == slug and j.get('key', slug) == key:
                return j.get('days'), j.get('stretches') or {}
        return None, {}

    again = 'run python3 tools/render.py --site and commit rendered/site/'
    listed, named = set(), set()
    for t in live:
        if t['kind'] != 'series':
            continue
        for rd in t.get('region_days') or []:
            name = rd['region']
            listed.add((t['slug'], name, rd['key']))
            for d in rd['days']:
                # '146/2': the day's track must have that stretch (the loader reads no track, so this is where it is seen)
                n = (rd.get('stretches') or {}).get(d['id'])
                if n is not None:
                    try:
                        content.day_points(d, n)
                    except content.ContentError as e:
                        _err(out, _index(t['slug']), str(e))
                    except Exception as e:      # a track that cannot be read at all: the GPX checks say why
                        _err(out, _index(t['slug']), 'region_days takes stretch %d of day %s, whose track cannot be read (%s)'
                             % (n, d['label'], type(e).__name__))
            if name in named and name not in regions:
                continue          # a mistyped region with several parts is one mistake: one line
            named.add(name)
            if name not in regions:
                near = difflib.get_close_matches(name, sorted(regions), 1)
                _err(out, _index(t['slug']), 'region_days names the region %r, which no report is filed under%s'
                     % (name, (' (did you mean %r?)' % near[0]) if near else ''))
                continue
            if maps is None:
                continue
            if name not in mapped:
                _warn(out, _index(t['slug']), 'region_days: %r has no region map (one is drawn from three reports with a '
                                              'track), so these days are shown on no map' % name)
                continue
            want = [d['id'] for d in rd['days'] if d['track']]
            cut = {i: n for i, n in (rd.get('stretches') or {}).items() if i in want}
            have, had = drawn_days(name, t['slug'], rd['key'])
            what = ('%s (%s)' % (name, rd['title'])) if rd.get('title') else name
            if want and (have != want or had != cut):
                _warn(out, _index(t['slug']), 'region_days: the region map of %s was last drawn %s; %s'
                      % (what, 'without these days' if have is None else 'with other days of this journal' if have != want
                         else 'with another stretch of one of these days', again))
    if maps is None:
        return
    slugs = {t['slug'] for t in live if t['kind'] == 'series'}
    for key, entry in sorted(maps.items()):
        js = entry.get('journals') if isinstance(entry, dict) else None
        if not key.endswith('-desktop') or not isinstance(js, list):
            continue
        for j in js:
            slug, name = (j.get('slug'), entry.get('region')) if isinstance(j, dict) else (None, None)
            if slug in slugs and (slug, name, j.get('key', slug)) not in listed:
                _warn(out, _index(slug), 'the region map of %s still draws days of this journal that region_days no longer '
                                         'lists there; %s' % (name, again))


# ---------------------------------------------------------------- the run

class _FixedDay:
    """While a run is given its day, content.load_trip's own clock (content._today, where this checkout has it) answers
    the same day, so published_at and updated_at are judged against the day the caller named."""

    def __init__(self, day):
        self.day = day
        self.had = None

    def __enter__(self):
        if self.day is not None and hasattr(content, '_today'):
            self.had = content._today
            content._today = lambda: self.day

    def __exit__(self, *exc):
        if self.had is not None:
            content._today = self.had
        return False


def _load(rec, out):
    """Stage (c): the trip as the build loads it, or None with one error finding (a ContentError's own text, unchanged;
    anything else as 'could not be read', never a traceback)."""
    try:
        return content.load_trip(rec['folder'])
    except content.ContentError as ex:
        out.append(_raised(str(ex), rec['file']))
    except Exception as ex:
        _unreadable(out, rec['file'], ex)
    return None


def _stub(rec):
    """A stand-in for a trip that did not load, so the manifest, a goal's outing or a write-up link that names it is
    not reported a second time as pointing at nothing. A draft gets none: it has no page either way."""
    meta = rec['meta'] or {}
    if meta.get('draft') is True:
        return None
    kind = meta.get('kind')
    return {'slug': rec['slug'], 'kind': kind if isinstance(kind, str) and kind in KINDS else 'trip'}


def _folder_findings(folder, slug, today, rendered_dir, counts):
    """Stages (a) to (d) for one trip folder: (findings, raw record or None, loaded trip or None)."""
    out, rec, t = [], None, None
    try:
        rec = _read_folder(folder, slug, out)
        counts['trips'] += 1
        counts['photos'] += _photo_count(rec)
        counts['gpx'] += rec['gpx_files']
        _check_raw(rec, out)
        if not errors(out):
            t = _load(rec, out)
        if t is not None:
            _trip_findings(t, rec, today, rendered_dir, out)
    except Exception as ex:   # a rule that trips over a file is a finding about that file, never a traceback
        _unreadable(out, _index(slug), ex, 'checked')
        t = None
    return out, rec, t


def survey(trips_dir=None, home_json=None, rendered_dir=None, today=None):
    """(findings, counts): the sorted findings of run(), and {'trips', 'photos', 'gpx'}: the trip folders, declared
    photos and GPX files that were looked at (the numbers summary() prints)."""
    trips_dir = trips_dir or content.TRIPS_DIR
    home_json = home_json or curation.HOME_JSON
    rendered_dir = rendered_dir or content.RENDERED
    if not os.path.isdir(rendered_dir):
        rendered_dir = None       # a content folder checked on its own: nothing is said about renders
    fixed, today = today, today or date.today()
    out, counts = [], {'trips': 0, 'photos': 0, 'gpx': 0}
    if not os.path.isdir(trips_dir):
        return [_finding('error', 'content/trips', 'the folder does not exist')], counts
    records, loaded, by_slug, drafts = [], [], {}, set()
    _INPUTS.clear()               # the render hashes are worked out again for every run (a track may have changed)
    with _FixedDay(fixed):
        for slug in sorted(n for n in os.listdir(trips_dir) if not n.startswith('.')):
            folder = os.path.join(trips_dir, slug)
            if not os.path.exists(os.path.join(folder, 'index.md')):
                continue          # not a trip: content.load_all skips it too
            mine, rec, t = _folder_findings(folder, slug, today, rendered_dir, counts)
            out += mine
            if rec is not None:
                records.append(rec)
            if t is not None:
                loaded.append(t)
            # who has a page: a loaded trip that is not a draft, and (as a stand-in) a broken one that is not a draft
            page = t if t is not None else (_stub(rec) if rec is not None else {'slug': slug, 'kind': 'trip'})
            if page is None or page.get('draft'):
                drafts.add(slug)
            else:
                by_slug[slug] = page
    live = sorted((t for t in loaded if not t['draft']), key=lambda t: t['slug'])
    site_wide = [(curation.FILE, _home_findings, (home_json, by_slug, trips_dir, rendered_dir)),
                 ('content/trips', _outing_findings, (loaded, by_slug)),
                 ('content/trips', _link_findings, (records, set(by_slug), drafts)),
                 ('content/trips', _title_findings, (live,)),
                 ('content/trips', _region_spellings, (live,)),
                 ('content/trips', _journal_region_findings, (live, rendered_dir))]
    if rendered_dir:
        site_wide.append(('content/trips', _region_findings, (live, rendered_dir)))
        site_wide.append(('content/trips', _site_map_findings, (live, by_slug, drafts, rendered_dir)))
        # last: it stays quiet when one of the lines above already named the site maps
        site_wide.append(('rendered/site/meta.json', _site_hash_findings, (live, rendered_dir)))
    root = os.path.dirname(trips_dir)
    site_wide += [('content/about.md', _about_findings, (root,)),
                  (author.FILE, _author_findings, (os.path.join(root, 'author.json'),)),
                  ('content/regions', _region_intro_findings, (root, records, live, rendered_dir))]
    for file, check, args in site_wide:
        try:
            check(*(args + (out,)))
        except Exception as ex:   # as for a folder: a finding, and the other checks still run
            _unreadable(out, file, ex, 'checked')
    out = _caption_count(out)
    return sorted(out, key=lambda f: (f['file'], LEVELS.index(f['level']), f['text'])), counts


def _heading_jumps(where, body, out):
    for lvl, before in markdown.heading_jumps(body or ''):
        _err(out, where, 'a heading of the write-up skips a level (%s after %s): go one level at a time, %s after %s'
             % ('#' * lvl, '#' * before, '#' * (before + 1), '#' * before))


def _author_findings(path, out):
    """content/author.json (optional): what the build would refuse, word for word (sitegen.author.load, whose keys are
    AUTHOR_KEYS). A missing file is no finding: the site then shows no contact."""
    try:
        author.load(path)
    except author.AuthorError as ex:
        out.append(_raised(str(ex), author.FILE))


def _about_findings(root, out):
    """content/about.md (optional; the About page's words and photo). Its photo is published with the alt text it states
    and no other description, so an alt is required, as are the photo's file and pixel size."""
    file = 'content/about.md'
    try:
        about = content.load_about(root)
    except content.ContentError as ex:
        _err(out, file, str(ex).split(': ', 1)[-1])
        return
    if about is None:
        return
    _unknown_keys(about['meta'], ABOUT_KEYS, file, '', out)
    _heading_jumps(file, about['body_md'], out)
    raw = about['meta'].get('photo')
    if raw is None:
        if about['meta'].get('cover_focal_x') is not None or about['meta'].get('cover_focal_y') is not None:
            _warn(out, file, 'cover_focal_x / cover_focal_y say where to crop a photo, and there is no photo: line')
        return
    _unknown_keys(raw, [k for k in PHOTO_KEYS if k != 'caption'], file, 'photo', out)
    p = about['photo']
    if not os.path.isfile(os.path.join(about['dir'], p['file'])):
        _err(out, file, 'photo file %s is missing from content/about/ (python3 tools/about_photo.py writes it)' % p['file'])
    elif not p['sm']:
        _warn(out, file, 'photo %s has no 800 px copy beside it, so every visitor loads the large one; python3 '
                         'tools/about_photo.py writes both' % p['file'])
    for k in ('w', 'h'):
        v = raw.get(k)
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            _err(out, file, 'photo.%s must be a positive whole number of pixels, got %r' % (k, v))
    alt = raw.get('alt')
    if not isinstance(alt, str) or not alt.strip():
        _err(out, file, 'photo has no alt text: describe what it shows in an alt: line under photo (the page shows no '
                        'photo without one, and it is what a screen reader says in its place)')


def _region_intro_findings(root, records, live, rendered_dir, out):
    """content/regions/<slug>.md (optional; a region page's introduction). The slug is the region's name as the trips
    spell it, through content.slugify: a file that matches no region is an error, one whose region has no page (fewer
    reports, or no region map) a warning, since its words are shown nowhere."""
    try:
        intros = content.load_region_intros(root)
    except content.ContentError as ex:
        _err(out, 'content/regions', str(ex))
        return
    if not intros:
        return
    names = {}
    # the names as the files spell them, a trip that does not load included (its own error stops the build already)
    for rec in records:
        meta = rec.get('meta') or {}
        r = meta.get('region')
        if meta.get('draft') is not True and isinstance(r, str) and r.strip():
            names.setdefault(content.slugify(r), r)
    pages = None
    meta = None
    if rendered_dir:
        try:
            with open(os.path.join(rendered_dir, 'site', 'meta.json'), encoding='utf-8') as fh:
                meta = json.load(fh)
        except (OSError, ValueError):
            meta = None
    if isinstance(meta, dict):
        pages = {slug for _n, slug, _ts in core.region_pages({'trips': live}, meta)}
    for slug, intro in sorted(intros.items()):
        file = intro['file']
        _unknown_keys(intro['meta'], REGION_INTRO_KEYS, file, '', out)
        _heading_jumps(file, intro['body_md'], out)
        if slug not in names:
            near = difflib.get_close_matches(slug, sorted(names), n=1, cutoff=0.6)
            _err(out, file, 'no region is called this: the file name must be a region\'s slug (the name in lower case, '
                            'hyphens for spaces: Eastern Sierra is eastern-sierra.md)%s'
                 % ((' (did you mean %s.md?)' % near[0]) if near else ''))
            continue
        title = intro['title']
        if title is not None and title != names[slug]:
            _err(out, file, 'title %r is not the region\'s name as the trips spell it, %r' % (title, names[slug]))
        if pages is not None and slug not in pages:
            _warn(out, file, 'the region %r has no page (a region page needs a region map and a published report), so '
                             'these words are shown nowhere' % names[slug])


_UNCAPTIONED = re.compile(r'^(\d+) photos? without a caption$')


def _caption_count(out):
    """The per-file 'N photos without a caption' notes as one count line (Phase 9), so validate.py -v stays readable;
    the line points at tools/content_report.py --alt, the list of the photos seen most."""
    kept, files, photos = [], 0, 0
    for f in out:
        m = _UNCAPTIONED.match(f['text'][len(f['file']) + 2:]) if f['level'] == 'note' else None
        if m:
            files += 1
            photos += int(m.group(1))
        else:
            kept.append(f)
    if files:
        kept.append(_finding('note', 'content/trips', '%s without a caption, in %s (a caption is optional; '
                                                      'python3 tools/content_report.py --alt lists the most-seen photos)'
                             % (_plural(photos, 'photo'), _plural(files, 'file'))))
    return kept


def run(trips_dir=None, home_json=None, rendered_dir=None, today=None):
    """Every finding about the content, sorted by file, then errors before warnings before notes, then text. Defaults:
    content.TRIPS_DIR, curation.HOME_JSON, content.RENDERED and today's date. Drafts are checked too: a broken draft
    stops a build just the same. Never raises on content."""
    return survey(trips_dir, home_json, rendered_dir, today)[0]
