"""The build-time search indexes behind trips/, read by assets/js/pages/trips.js.

trips/search.json: one entry per published trip: the slug, four normalised text fields (title; place + region; activity,
aliases and named peaks; the write-ups) and the plain write-up text for snippets around a hit.
trips/journal.json: one entry per day of a journal (kind: series), so a search finds the day by its write-up, its title or
its name, says which journal and which day it is, and links to that day's existing anchor on the journal page. No day
gets a page of its own.
No coordinates, no GPX, no HTML in either. normalize() and trips.js's norm() must agree exactly (tests/norm_cases.json
checks both), so a query typed in the browser is compared in the same form the index was written in.
"""
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import markdown  # noqa: E402

SUB_WORD = {'SUP': 'Paddleboarding', 'Rafting': 'Rafting', 'Kayaking': 'Kayaking', 'Mountaineering': 'Mountaineering'}  # as core.SUB_WORD

_MARKS = re.compile('[\u0300-\u036f]')
CAP = 4000  # characters of normalised write-up text per trip (the longest write-ups are a few thousand characters)
RAW_CAP = 4000  # characters of plain write-up text kept for snippets around a match
DAY_CAP = 6000  # the same two limits for one journal day (the longest day so far is under 2,000 characters)
_MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def normalize(s):
    """Lower-case ASCII words: accents dropped (NFKD, then the U+0300–036F combining marks removed: the same block
    trips.js strips, so the two never disagree), every run of anything but a–z / 0–9 becomes one space.
    "Lover's Leap: Corrugation Corner" -> 'lover s leap corrugation corner'."""
    if not s:
        return ''
    s = _MARKS.sub('', unicodedata.normalize('NFKD', str(s))).lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def _cap(s, n):
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(' ', 1)[0]
    return cut.rstrip()


def entry(t):
    """{'s': slug, 't': title, 'p': place + region, 'k': activity label (and the Other sub-type) + aliases + peaks,
    'x': write-ups, 'r': plain write-up text (for snippets)}; every text field but r normalised."""
    pk = (t.get('map') or {}).get('peaks') or []
    pk = [pk] if isinstance(pk, str) else pk
    peaks = [p for p in pk if isinstance(p, str)]
    words = [t.get('activity_label') or '']
    if t.get('subtype'):
        words.append(SUB_WORD.get(t['subtype'], t['subtype']))
    bodies = [t['body_md']] + [d['body_md'] for d in t['days']]
    plain = ' '.join(markdown.plain(b) for b in bodies if b)
    return {
        's': t['slug'],
        't': normalize(t['title']),
        'p': normalize(' '.join(x for x in (t.get('place'), t.get('region')) if x)),
        'k': normalize(' '.join(words + list(t.get('aliases') or []) + peaks)),
        'x': _cap(normalize(plain), CAP),
        'r': _cap(plain, RAW_CAP),
    }


def build_index(site):
    """Entries for every published trip, newest first (planned routes are not published; drafts are never loaded)."""
    return [entry(t) for t in site['published']]


def day_entry(t, d):
    """One day of a journal: {'s': the journal's slug, 'a': the day's anchor on the journal page (series.day_anchor:
    'day-31', 'day-5-2'), 'n': the day label as written ('31', '5.2'), 'j': the journal's title, 'h': the day's own
    title ('' when it has none), 'w': its date as 'May 22, 2024' ('' when unknown), and the fields trips.js matches
    on: 't' (day title), 'p' (the day's name, 'day <label>': a query must hold it whole), 'k' (''), 'x' (the day's
    write-up), all normalised, plus 'r', the plain write-up for the snippet, and 'q', the journal's title and aliases.
    'q' never finds a day by itself (it finds the journal in the trip index, and would list every one of its days
    here); its words may only come along with something of the day's own ('pct whitney', 'pct day 31')."""
    from sitegen.pages import series   # at call time: series imports core, which imports this module
    plain = markdown.plain(d['body_md'])
    label = str(d['label'])
    when = d.get('date')
    return {
        's': t['slug'], 'a': series.day_anchor(d), 'n': label, 'j': t['title'], 'h': d.get('title') or '',
        'w': ('%s %d, %d' % (_MONTHS[when.month - 1], when.day, when.year)) if when else '',
        't': normalize(d.get('title') or ''),
        'p': normalize('day %s' % label),
        'k': '',
        'x': _cap(normalize(plain), DAY_CAP),
        'r': _cap(plain, DAY_CAP),
        'q': normalize(' '.join([t['title']] + list(t.get('aliases') or []))),
    }


def build_day_index(site):
    """Entries for every day of every published journal (kind: series), journals newest first, days in order. A day is
    found by its write-up, by its title ('Mount Whitney' on a track-only day) or by its name ('day 100'), which is all
    an untitled track-only day has. Multi-day trips stay whole in the trip index, where a hit already shows the day's
    words under the trip's own card."""
    return [day_entry(t, d) for t in site['published'] if t['kind'] == 'series' for d in t['days']]


def dumps(entries):
    """Compact ASCII JSON with '<' escaped, so the text is harmless even inside a <script> element."""
    return json.dumps(entries, separators=(',', ':'), ensure_ascii=True).replace('<', '\\u003c')
