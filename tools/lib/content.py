"""Load content/trips/* into plain dicts shared by tools/render.py and tools/build.py."""
import glob
import os
import re
from datetime import date

import frontmatter

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
        sm = base + '.sm' + ext
        out.append({'file': f, 'sm': sm if os.path.exists(os.path.join(folder, sm)) else None,
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


def _landscape(p):
    return bool(p.get('w') and p.get('h') and p['w'] >= p['h'])


def resolve_cover(t):
    """The photo a card or share image uses for the trip, with where it came from:
    {'photo': {file, sm, w, h, alt, caption}, 'source': 'explicit' | 'parent' | 'day', 'day': day dict or None,
    'focal': (x, y)} or None when the trip has no photo at all.

    An explicit cover_photo must name a photo declared in index.md or a days/NN.md (so its size and alt text are reused)
    and the file must exist; a broken explicit value is a ContentError, never a silent fallback. Without one, the first
    landscape trip photo wins, then the first trip photo, then the first landscape day photo, then the first day photo:
    an automatic pick, not an editorial choice."""
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
        p = next((p for p in t['photos'] if _landscape(p)), t['photos'][0])
        return {'photo': p, 'source': 'parent', 'day': None, 'focal': focal}
    for d in t['days']:
        p = next((p for p in d['photos'] if _landscape(p)), None)
        if p:
            return {'photo': p, 'source': 'day', 'day': d, 'focal': focal}
    for d in t['days']:
        if d['photos']:
            return {'photo': d['photos'][0], 'source': 'day', 'day': d, 'focal': focal}
    return None


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
    for f in sorted(glob.glob(os.path.join(folder, 'days', '*.md'))):
        with open(f, encoding='utf-8') as fh:
            dm, db = _split(fh.read(), 'content/trips/%s/days/%s' % (slug, os.path.basename(f)))
        stem = os.path.splitext(os.path.basename(f))[0]
        gpx = os.path.join(folder, 'days', stem + '.gpx')
        t['days'].append({
            'n': len(t['days']) + 1, 'id': stem, 'label': str(dm.get('day') or (len(t['days']) + 1)),
            'title': dm.get('title'), 'date': _date(dm.get('date')), 'start_time': dm.get('start_time'),
            'hut': dm.get('hut'), 'transfer_before': bool(dm.get('transfer_before')),
            'stats': _stats(dm.get('stats')), 'photos': _photos(dm.get('photos'), folder),
            'body_md': re.sub(r'<!--.*?-->', '', db, flags=re.S).strip(), 'track': gpx if os.path.exists(gpx) else None,
        })
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
    t['cover'] = resolve_cover(t)
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
