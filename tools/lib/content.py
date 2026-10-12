"""Load content/trips/* into plain dicts shared by tools/render.py and tools/build.py."""
import glob
import os
import re
from datetime import date, datetime, timedelta, timezone

import frontmatter
import goals

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TRIPS_DIR = os.path.join(ROOT, 'content', 'trips')
RENDERED = os.path.join(ROOT, 'rendered')

FT, MI = 3.28084, 1609.344

ACTIVITIES = {
    # key: (label, short label, code, colour, url folder, Strava-ish noun)
    'ski': ('Backcountry Ski', 'Ski', 'SKI', '#4A8CCD', 'ski'),
    'climb': ('Climbing', 'Climb', 'CLM', '#70355E', 'climbing'),
    'hike': ('Hiking', 'Hike', 'HIK', '#69883C', 'hiking'),
    'mtb': ('Mountain Biking', 'MTB', 'MTB', '#845011', 'mountain-biking'),
    'other': ('Other', 'Other', 'OTH', '#1C7D78', 'other'),
}
CAT = {k: v[2] for k, v in ACTIVITIES.items()}  # activity -> mapkit category code
OTHER_SUBTYPES = ['SUP', 'Rafting', 'Kayaking', 'Mountaineering']


def slugify(s):
    import unicodedata
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r"[’']", '', s.lower())
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def _date(v):
    if not v:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v))
    except ValueError:
        return None


def _today():
    """The day the build runs (a function, so tests can fix it)."""
    return date.today()


# re.ASCII: \d is 0-9 only (int() would also take full-width digits, and the value is published as written)
_PUB = re.compile(r'^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?(Z|[+-]\d{2}:\d{2}))?$', re.ASCII)


def _pub_value(meta, key, where):
    """published_at / updated_at of index.md: (the text exactly as written, its moment as an aware datetime or a date) or
    (None, None) when the line is absent or empty. A date is `YYYY-MM-DD`; a date and time needs an explicit offset
    (`2026-10-03T18:30:00-07:00`, or `Z`), because the site never adds a time or a zone of its own. Anything else, and
    an impossible date or time, is a ContentError: a new explicit field is never guessed at."""
    v = meta.get(key)
    if v is None or v == '':
        return None, None
    if isinstance(v, date) and not isinstance(v, datetime):
        v = v.isoformat()
    m = _PUB.match(v.strip()) if isinstance(v, str) else None
    if not m:
        raise ContentError('%s: %s must be a date written YYYY-MM-DD, or a date and time with an offset such as '
                           '2026-10-03T18:30:00-07:00, got %r' % (where, key, v))
    text = v.strip()
    y, mo, d, hh, mm, ss, off = m.groups()
    try:
        if hh is None:
            return text, date(int(y), int(mo), int(d))
        if off == 'Z':
            tz = timezone.utc
        else:
            oh, om = int(off[1:3]), int(off[4:6])
            if oh > 14 or om > 59 or (oh == 14 and om):   # no clock on earth is more than 14 hours from UTC
                raise ValueError('offset')
            tz = timezone((1 if off[0] == '+' else -1) * timedelta(hours=oh, minutes=om))
        return text, datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss or 0), tzinfo=tz)
    except ValueError:
        raise ContentError('%s: %s %r is not a real date or time' % (where, key, v))


def _day_of(moment):
    return moment.date() if isinstance(moment, datetime) else moment


def _publication(meta, t, where):
    """(published_at, updated_at) as written, validated against each other, the trip and today. published_at is the day
    the report first went online on this site and updated_at the day its content last changed materially: neither is
    the trip date, and neither is ever filled in by the build. Absent -> (None, None), and nothing about publication is
    shown or written into the page's metadata."""
    pub, pub_m = _pub_value(meta, 'published_at', where)
    upd, upd_m = _pub_value(meta, 'updated_at', where)
    if not pub and not upd:
        return None, None
    if t['kind'] == 'planned':
        raise ContentError('%s: %s is for a report; this is a planned route (kind: planned)'
                           % (where, 'published_at' if pub else 'updated_at'))
    if upd and not pub:
        raise ContentError('%s: updated_at needs published_at (the day the report first went online)' % where)
    limit = _today() + timedelta(days=1)
    for key, text, moment in (('published_at', pub, pub_m), ('updated_at', upd, upd_m)):
        # a draft is not online, so the day it is planned to go online may lie ahead; the check applies again the
        # moment the draft flag comes off
        if text and not t['draft'] and _day_of(moment) > limit:
            raise ContentError('%s: %s %s is in the future' % (where, key, text))
    # the first day, not the last: a journal or a multi-day page can go online while the trip is still under way, and
    # days added later must not turn a true date into an error
    trip_day = t['date'] or t['end_date']
    if trip_day and _day_of(pub_m) < trip_day:
        raise ContentError('%s: published_at %s is before the trip itself (%s); it is the day the report went online, '
                           'not the trip date' % (where, pub, trip_day.isoformat()))
    if upd:
        both_times = isinstance(pub_m, datetime) and isinstance(upd_m, datetime)
        if (upd_m < pub_m) if both_times else (_day_of(upd_m) < _day_of(pub_m)):
            raise ContentError('%s: updated_at %s is before published_at %s' % (where, upd, pub))
    return pub, upd


def _hm_to_s(v):
    if not v:
        return None
    parts = [int(x) for x in str(v).split(':')]
    while len(parts) < 3:
        parts.append(0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def _s_to_hm(sec):
    if sec is None:
        return None
    h, m = int(sec // 3600), int(round((sec % 3600) / 60.0))
    if m == 60:
        h, m = h + 1, 0
    return '%d:%02d' % (h, m)


def _photos(entries, folder):
    out = []
    for p in entries or []:
        f = p.get('file')
        if not f:
            continue
        base, ext = os.path.splitext(f)
        sm, th = base + '.sm' + ext, base + '.th' + ext   # the 800 px copy and the card-size copy, when they exist
        out.append({'file': f, 'sm': sm if os.path.exists(os.path.join(folder, sm)) else None,
                    'th': th if os.path.exists(os.path.join(folder, th)) else None,
                    'w': p.get('w'), 'h': p.get('h'), 'alt': p.get('alt') or '', 'caption': p.get('caption') or ''})
    return out


class ContentError(ValueError):
    """A content file says something the site cannot publish (a bad cover path, a focal point out of range, ...). The
    message names the file and the field so the fix is obvious; build.py prints it without a traceback."""


def _index_of(slug):
    return 'content/trips/%s/index.md' % slug


def _focal_value(meta, key, where):
    """cover_focal_x / cover_focal_y: a number from 0 to 100 (per cent of the image), 50 when absent."""
    v = meta.get(key)
    if v is None:
        return 50.0
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ContentError('%s: %s must be a number from 0 to 100, got %r' % (where, key, v))
    if not 0 <= v <= 100:
        raise ContentError('%s: %s must be between 0 and 100, got %r' % (where, key, v))
    return float(v)


def _norm_path(s):
    """'./photos//01.webp' -> 'photos/01.webp' (declared photo paths and the cover path compare in this form)."""
    return '/'.join(x for x in str(s).replace('\\', '/').split('/') if x not in ('', '.'))


def _cover_path(raw, where):
    """The cover_photo value, checked: a relative path that stays inside the trip folder. None when absent."""
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ContentError('%s: cover_photo must be a path such as photos/01.webp, got %r' % (where, raw))
    s = raw.strip()
    if '\\' in s or s.startswith('/') or os.path.isabs(s):
        raise ContentError('%s: cover_photo must be a relative path inside the trip folder, got %r' % (where, raw))
    parts = [x for x in s.split('/') if x not in ('', '.')]
    if not parts or '..' in parts:
        raise ContentError('%s: cover_photo may not leave the trip folder, got %r' % (where, raw))
    return s


def _split(text, where):
    """frontmatter.split, with a syntax error (an unclosed ---, a broken quoted value) reported as a ContentError that names
    the file, so build.py prints one line instead of a traceback."""
    try:
        return frontmatter.split(text)
    except ValueError as ex:
        raise ContentError('%s: front matter: %s' % (where, ex))


def day_anchor(label):
    """'day-31', 'day-5-2': the id of a journal day on its page and the fragment every link to it uses. A label is a number
    as a rule ('31', '5.2'); whatever else a day file's `day:` holds becomes a hyphen too, so the id is always safe to
    write into an attribute and a URL. load_trip refuses a journal whose labels give two days the same anchor."""
    return 'day-' + re.sub(r'[^A-Za-z0-9]+', '-', str(label)).strip('-')


DAY_SUB_IDS = ('-n', '-t')   # a day article's own ids: '<anchor>-n' on its number, '<anchor>-t' on its title (series.day_article)


def _day_given(dm):
    """A day file's `day:` as text, or None when the line is absent or empty. `day: 0` is a label (Day 0), not a missing
    one."""
    v = dm.get('day')
    return str(v).strip() if v is not None and str(v).strip() else None


def _day_label(dm, position):
    """A day's label: its `day:` (_day_given), else its position among the day files."""
    given = _day_given(dm)
    return given if given is not None else str(position)


def _check_day_anchors(t, unlabelled=()):
    """A journal page gives every day an anchor built from its label (day_anchor); links, the copy-link address and the
    day search all point at it. Two days with one anchor, or a label with nothing to build one from, is a content error
    named by its day file, not a page with links that land on the wrong day. unlabelled: the ids of the day files
    without a `day:` line, whose label is their position; the message says so, because the file holds no such value
    (a day added to a journal whose labels do not follow the file order, such as the PCT, needs its own `day:`).
    The page also writes two ids of the day's own from the anchor (DAY_SUB_IDS: its number and its title), so a label
    such as '5 n' beside a Day 5 is refused too."""
    seen, used = {}, {}   # anchor -> day id; every id a day's article writes -> day id
    for d in t['days']:
        where = 'content/trips/%s/days/%s.md' % (t['slug'], d['id'])
        a = day_anchor(d['label'])
        if a == 'day-':
            raise ContentError('%s: day: %r has no letter or digit to make its page anchor from' % (where, d['label']))
        if a in seen:
            if d['id'] in unlabelled:
                raise ContentError('%s: no day: line, so this day takes its position, %s, and that gives the same page anchor '
                                   '(#%s) as days/%s.md; add a day: line with a label no other day has'
                                   % (where, d['label'], a, seen[a]))
            raise ContentError('%s: day: %r gives the same page anchor (#%s) as days/%s.md; give each day its own label'
                               % (where, d['label'], a, seen[a]))
        mine = [a] + [a + s for s in DAY_SUB_IDS]
        clash = next((i for i in mine if i in used), None)
        if clash:
            raise ContentError('%s: day: %r needs the page id #%s, which days/%s.md already uses; give each day its own label'
                               % (where, d['label'], clash, used[clash]))
        seen[a] = d['id']
        for i in mine:
            used[i] = d['id']


def _landscape(p):
    return bool(p.get('w') and p.get('h') and p['w'] >= p['h'])


LEAD_MIN_AR = 1.2   # a page's lead photo sits in a 4:3 to 2:1 frame; anything narrower than 6:5 would lose most of itself to it


def _wide(p):
    """Wide enough to lead a page (sitegen report.lead_photo): at least 6:5."""
    return bool(p.get('w') and p.get('h') and p['w'] >= LEAD_MIN_AR * p['h'])


def _auto_cover(photos):
    """The automatic pick among photos in their declared order: the first one wide enough to lead a page, else the first
    that is at least as wide as tall, else None. A square first photo therefore does not keep a later landscape from
    leading the page."""
    return next((p for p in photos if _wide(p)), None) or next((p for p in photos if _landscape(p)), None)


def resolve_cover(t):
    """The photo a card or share image uses for the trip, with where it came from:
    {'photo': {file, sm, w, h, alt, caption}, 'source': 'explicit' | 'parent' | 'day', 'day': day dict or None,
    'focal': (x, y)} or None when the trip has no photo at all.

    An explicit cover_photo must name a photo declared in index.md or a days/NN.md (so its size and alt text are reused)
    and the file must exist; a broken explicit value is a ContentError, never a silent fallback. Without one, the first
    trip photo wide enough to lead a page wins (_auto_cover: at least 6:5, else at least as wide as tall), then the first
    trip photo, then the same over the day photos: an automatic pick, not an editorial choice."""
    focal = tuple(t.get('cover_focal') or (50.0, 50.0))
    want = t.get('cover_photo')
    where = _index_of(t['slug'])
    if want:
        key = _norm_path(want)
        found = None
        for p in t['photos']:
            if _norm_path(p['file']) == key:
                found = (p, None)
                break
        if not found:
            for d in t['days']:
                for p in d['photos']:
                    if _norm_path(p['file']) == key:
                        found = (p, d)
                        break
                if found:
                    break
        if not found:
            raise ContentError('%s: cover_photo %r is not a photo declared under photos: in index.md or a days/NN.md'
                               % (where, want))
        p, d = found
        if not os.path.exists(os.path.join(t['dir'], p['file'])):
            raise ContentError('%s: cover_photo %r is declared but the file is missing from the trip folder' % (where, want))
        return {'photo': p, 'source': 'explicit', 'day': d, 'focal': focal}
    if t['photos']:
        return {'photo': _auto_cover(t['photos']) or t['photos'][0], 'source': 'parent', 'day': None, 'focal': focal}
    for test in (_wide, _landscape):
        for d in t['days']:
            p = next((p for p in d['photos'] if test(p)), None)
            if p:
                return {'photo': p, 'source': 'day', 'day': d, 'focal': focal}
    for d in t['days']:
        if d['photos']:
            return {'photo': d['photos'][0], 'source': 'day', 'day': d, 'focal': focal}
    return None


def _highlights(raw, t, where):
    """journal_highlights: [001, 059] on a series -> the matching day dicts in the listed order (ids as in the days/NNN.md
    file names; a bare number is zero-padded to the width the files use). Absent or empty -> []. An unknown id, a
    repeat, a value that is not a list, or a non-empty list on a trip that is not a journal is a ContentError."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ContentError('%s: journal_highlights must be a list of day ids such as [001, 059], got %r' % (where, raw))
    if not [x for x in raw if x is not None]:
        return []      # an empty list is "none chosen yet", on any trip
    if t['kind'] != 'series':
        # only a journal page shows highlights: on any other trip the list would be accepted and silently never used
        raise ContentError('%s: journal_highlights is for a journal (kind: series); this trip is kind: %s' % (where, t['kind']))
    if not t['days']:
        raise ContentError('%s: journal_highlights needs day files (days/NNN.md); this trip has none' % where)
    by_id = {d['id']: d for d in t['days']}
    width = max(len(d['id']) for d in t['days'])
    out, seen = [], set()
    for item in raw:
        if item is None:
            continue   # a trailing comma's empty item
        key = str(item).strip()
        if isinstance(item, int) or key.isdigit():
            key = key.zfill(width)
        if key not in by_id:
            raise ContentError('%s: journal_highlights names day %r, which is not a days/NNN.md of this trip' % (where, item))
        if key in seen:
            raise ContentError('%s: journal_highlights lists day %r twice' % (where, item))
        seen.add(key)
        out.append(by_id[key])
    return out


_DAY_RANGE = re.compile(r'^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$', re.ASCII)
_DAY_NUMBER = re.compile(r'^\d+(?:\.\d+)?$', re.ASCII)


def _region_days(raw, t, where):
    """region_days on a journal (kind: series): which of its days lie in which region, so that a region's map draws them
    and its list names the journal. The journal itself is filed under one `region:` of its own and spans many.

        region_days:
          Lake Tahoe: 68-75, 147-153
          Eastern Sierra: [59-63]

    -> [{'region': 'Lake Tahoe', 'days': [day dicts, in the journal's order]}, ...] in the order written. A day is named
    by its label, the number the page shows (Day 148), not by its file name: '148' is that day, '68-75' every day whose
    label is a number from 68 to 75 (5.2 lies between 5 and 6). A day may be listed under more than one region. Absent
    or empty -> []. Anything else that is not this shape, a day or range that matches no day, a range written backwards,
    a region without days, or the block on a trip that is not a journal is a ContentError."""
    if raw is None or raw == {} or raw == []:
        return []
    if not isinstance(raw, dict):
        raise ContentError('%s: region_days must be a mapping of a region to its days, such as "Lake Tahoe: 68-75, 147-153", got %r'
                           % (where, raw))
    if t['kind'] != 'series':
        raise ContentError('%s: region_days is for a journal (kind: series); this trip is kind: %s' % (where, t['kind']))
    if not t['days']:
        raise ContentError('%s: region_days needs day files (days/NNN.md); this trip has none' % where)
    numbered = [(float(d['label']), d) for d in t['days'] if _DAY_NUMBER.match(str(d['label']))]
    out = []
    for region, value in raw.items():
        name = str(region).strip() if region is not None else ''
        if not name:
            raise ContentError('%s: region_days has an entry without a region name' % where)
        items = value if isinstance(value, list) else [value]
        parts = []
        for item in items:
            if item is None:
                continue   # a trailing comma's empty item, or a region left without a value
            if isinstance(item, bool) or not isinstance(item, (str, int, float)):
                raise ContentError('%s: region_days: %s must list days such as 68-75, 147-153, got %r' % (where, name, value))
            parts += [p.strip() for p in str(item).split(',') if p.strip()]
        if not parts:
            raise ContentError('%s: region_days: %s names no days; write them as 68-75, 147-153 or take the line out' % (where, name))
        chosen = set()
        for part in parts:
            m = _DAY_RANGE.match(part)
            if m:
                lo, hi = float(m.group(1)), float(m.group(2))
                if lo > hi:
                    raise ContentError('%s: region_days: %s has the range %s, which runs backwards' % (where, name, part))
                hit = [d['id'] for n, d in numbered if lo <= n <= hi]
                if not hit:
                    raise ContentError('%s: region_days: %s has the range %s, which holds no day of this journal' % (where, name, part))
            else:
                hit = [d['id'] for d in t['days'] if str(d['label']) == part]
                if not hit and _DAY_NUMBER.match(part):
                    hit = [d['id'] for n, d in numbered if n == float(part)]
                if not hit:
                    raise ContentError('%s: region_days: %s names day %r, which is no day of this journal (days are named '
                                       'by the number the page shows, as in Day 148)' % (where, name, part))
            chosen.update(hit)
        if any(o['region'] == name for o in out):
            raise ContentError('%s: region_days lists the region %r twice' % (where, name))
        out.append({'region': name, 'days': [d for d in t['days'] if d['id'] in chosen]})
    return out


def _stats(st):
    st = dict(st or {})
    out = {'distance_km': st.get('distance_km'), 'gain_m': st.get('gain_m'), 'loss_m': st.get('loss_m'),
           'high_m': st.get('high_m'), 'low_m': st.get('low_m'),
           'moving_s': _hm_to_s(st.get('moving')), 'elapsed_s': _hm_to_s(st.get('elapsed'))}
    return out


def _sum_stats(days):
    def tot(k):
        vals = [d['stats'][k] for d in days if d['stats'].get(k) is not None]
        return sum(vals) if vals else None

    def mx(k, f=max):
        vals = [d['stats'][k] for d in days if d['stats'].get(k) is not None]
        return f(vals) if vals else None
    return {'distance_km': round(tot('distance_km'), 2) if tot('distance_km') else None, 'gain_m': tot('gain_m'),
            'loss_m': tot('loss_m'), 'high_m': mx('high_m'), 'low_m': mx('low_m', min),
            'moving_s': tot('moving_s'), 'elapsed_s': tot('elapsed_s')}


def display_stats(st):
    """Formatted strings for a stats dict (imperial first, metric second)."""
    d = {}
    km = st.get('distance_km')
    if km is not None:
        d['mi'] = '%.1f' % (km * 1000 / MI) if km * 1000 / MI < 100 else '{:,}'.format(int(round(km * 1000 / MI)))
        d['km'] = '%.1f' % km if km < 100 else '{:,}'.format(int(round(km)))
    for k, fk, mk in (('gain_m', 'gain_ft', 'gain_m'), ('loss_m', 'loss_ft', 'loss_m'), ('high_m', 'high_ft', 'high_m'), ('low_m', 'low_ft', 'low_m')):
        v = st.get(k)
        if v is not None:
            d[fk] = '{:,}'.format(int(round(v * FT)))
            d[mk] = '{:,}'.format(int(round(v)))
    if st.get('moving_s'):
        d['moving'] = _s_to_hm(st['moving_s'])
    if st.get('elapsed_s'):
        d['elapsed'] = _s_to_hm(st['elapsed_s'])
    return d


def season_of(d, activity):
    if not d:
        return None
    if activity == 'ski':
        y = d.year if d.month >= 7 else d.year - 1
        return '%d–%02d' % (y, (y + 1) % 100)
    return str(d.year)


def load_trip(folder):
    slug = os.path.basename(folder)
    with open(os.path.join(folder, 'index.md'), encoding='utf-8') as fh:
        meta, body = _split(fh.read(), _index_of(slug))
    act = meta.get('activity') or 'other'
    kind = meta.get('kind') or 'trip'
    t = {
        'slug': slug, 'dir': folder, 'meta': meta, 'title': meta.get('title') or slug, 'activity': act,
        'activity_label': ACTIVITIES.get(act, ACTIVITIES['other'])[0], 'cat': CAT.get(act, 'OTH'),
        'subtype': meta.get('subtype'), 'kind': kind, 'date': _date(meta.get('date')), 'end_date': _date(meta.get('end_date')),
        'start_time': meta.get('start_time'), 'timezone': meta.get('timezone'), 'place': meta.get('place'),
        'region': meta.get('region'), 'party': meta.get('party'), 'route_shape': meta.get('route_shape'),
        'featured': bool(meta.get('featured')), 'draft': bool(meta.get('draft')),
        'beta': meta.get('beta') or [], 'conditions': meta.get('conditions') or {}, 'map': meta.get('map') or {},
        'body_md': re.sub(r'<!--.*?-->', '', body, flags=re.S).strip(),
        'photos': _photos(meta.get('photos'), folder), 'days': [], 'url': 'trips/%s/' % slug,
        'track': os.path.join(folder, 'track.gpx') if os.path.exists(os.path.join(folder, 'track.gpx')) else None,
        'rendered': os.path.join(RENDERED, 'trips', slug),
    }
    unlabelled = set()   # day files without a `day:` line (their label is their position)
    for f in sorted(glob.glob(os.path.join(folder, 'days', '*.md'))):
        with open(f, encoding='utf-8') as fh:
            dm, db = _split(fh.read(), 'content/trips/%s/days/%s' % (slug, os.path.basename(f)))
        stem = os.path.splitext(os.path.basename(f))[0]
        gpx = os.path.join(folder, 'days', stem + '.gpx')
        if _day_given(dm) is None:
            unlabelled.add(stem)
        t['days'].append({
            'n': len(t['days']) + 1, 'id': stem, 'label': _day_label(dm, len(t['days']) + 1),
            'title': dm.get('title'), 'date': _date(dm.get('date')), 'start_time': dm.get('start_time'),
            'hut': dm.get('hut'), 'transfer_before': bool(dm.get('transfer_before')),
            'stats': _stats(dm.get('stats')), 'photos': _photos(dm.get('photos'), folder),
            'body_md': re.sub(r'<!--.*?-->', '', db, flags=re.S).strip(), 'track': gpx if os.path.exists(gpx) else None,
        })
    if kind == 'series':
        _check_day_anchors(t, unlabelled)
    if t['days']:
        t['stats'] = _sum_stats(t['days'])
        t['date'] = t['date'] or t['days'][0]['date']
        t['end_date'] = t['end_date'] or t['days'][-1]['date']
    else:
        t['stats'] = _stats(meta.get('stats'))
    # optional presentation fields (docs/CONTENT_GUIDE.md): the cover a card shows, its focal point, and a short summary
    where = _index_of(slug)
    t['cover_photo'] = _cover_path(meta.get('cover_photo'), where)
    t['cover_focal'] = (_focal_value(meta, 'cover_focal_x', where), _focal_value(meta, 'cover_focal_y', where))
    cs = meta.get('card_summary')
    if cs is not None and not isinstance(cs, str):
        raise ContentError('%s: card_summary must be text, got %r' % (where, cs))
    t['card_summary'] = (cs or '').strip() or None
    # search_aliases: [PCT] -> other names the trips explorer finds the trip under (never shown as the title)
    al = meta.get('search_aliases')
    if al is None:
        t['aliases'] = []
    elif isinstance(al, str):
        t['aliases'] = [al.strip()] if al.strip() else []
    elif isinstance(al, list) and all(isinstance(x, str) or x is None for x in al):
        t['aliases'] = [x.strip() for x in al if x and x.strip()]  # None: a trailing comma's empty item
    else:
        raise ContentError('%s: search_aliases must be a list of names such as [PCT], got %r' % (where, al))
    t['cover'] = resolve_cover(t)
    # optional, never invented: when the report went online and when it last changed (docs/CONTENT_GUIDE.md)
    t['published_at'], t['updated_at'] = _publication(meta, t, where)
    t['journal_highlights'] = _highlights(meta.get('journal_highlights'), t, where)
    t['region_days'] = _region_days(meta.get('region_days'), t, where)
    # kind: planned trips are tick-list goals: goal.json (or the defaults for a legacy planned route)
    t['goal'] = goals.load_goal(folder, slug, kind)
    t['season'] = season_of(t['date'], act)
    t['has_writeup'] = bool(t['body_md']) or any(d['body_md'] for d in t['days'])
    return t


def load_all(include_drafts=False):
    trips = []
    for folder in sorted(glob.glob(os.path.join(TRIPS_DIR, '*'))):
        if os.path.exists(os.path.join(folder, 'index.md')):
            t = load_trip(folder)
            if t['draft'] and not include_drafts:
                continue
            trips.append(t)
    trips.sort(key=lambda t: (t['date'] or date.min), reverse=True)
    return trips
