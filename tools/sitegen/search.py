"""The build-time search index behind trips/ (trips/search.json), read by assets/js/pages/trips.js.

One entry per published trip: the slug, four normalised text fields (title; place + region; activity, aliases and named
peaks; the write-ups) and the plain write-up text for snippets around a hit. No coordinates, no GPX, no HTML.
normalize() and trips.js's norm() must agree exactly (tests/norm_cases.json checks both), so a query typed in the
browser is compared in the same form the index was written in.
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


def dumps(entries):
    """Compact ASCII JSON with '<' escaped, so the text is harmless even inside a <script> element."""
    return json.dumps(entries, separators=(',', ':'), ensure_ascii=True).replace('<', '\\u003c')
