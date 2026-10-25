"""The build-time search indexes behind trips/, read by assets/js/pages/trips.js.

trips/search.json: one entry per published trip: the slug, four normalised text fields (title; place + region; the
activity with its other forms, aliases, named peaks, the trip's year and months and its route shape; the write-ups) and
the plain write-up text for snippets around a hit.
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
_APOSTROPHES = re.compile("['\u2019\u2018]")
# a one-letter word elided onto the next ("d'Argentière", "l’été"): its apostrophe is a word break, as it always was, so
# 'argentiere' still starts a word. re.ASCII: \b and [a-z] as trips.js reads them
_ELISION = re.compile("\\b([a-z])['\u2019\u2018](?=[a-z])", re.ASCII)
CAP = 4000  # characters of normalised write-up text per trip (the longest write-ups are a few thousand characters)
RAW_CAP = 4000  # characters of plain write-up text kept for snippets around a match
DAY_CAP = 6000  # the same two limits for one journal day (the longest day so far is under 2,000 characters)
_MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
MONTH_NAMES = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november',
               'december')
# The other words a searcher uses for an activity, written into the keyword field after the activity's label. Only
# inflections and the sport's common names, never gear or a style one trip happens to have ('splitboard', 'rock'), and the
# longest forms only: a typed word matches the start of an index word, so 'ski' is found in 'skiing' and 'bike' in 'bikes'.
ACTIVITY_WORDS = {
    'ski': 'skiing skied skis skimo skinning touring',
    'climb': 'climbing climbs climbed',
    'hike': 'hiking hikes hiked',
    'mtb': 'mountain biking bikes rides riding mtb cycling',
}
SUBTYPE_WORDS = {   # the Other sub-types (content.OTHER_SUBTYPES)
    'SUP': 'paddleboarding paddleboards paddling sup standup',
    'Rafting': 'rafting rafts',
    'Kayaking': 'kayaking kayaks',
    'Mountaineering': 'mountaineering',
}


def normalize(s):
    """Lower-case ASCII words: accents dropped (NFKD, then the U+0300–036F combining marks removed: the same block
    trips.js strips, so the two never disagree), apostrophes (' ’ ‘) dropped so a word keeps its letters together, except
    after a one-letter word elided onto the next, where the apostrophe is a space; then every run of anything but a–z /
    0–9 becomes one space. "Lover's Leap: Corrugation Corner" -> 'lovers leap corrugation corner', "didn’t" -> 'didnt',
    "Refuge d'Argentière" -> 'refuge d argentiere'."""
    if not s:
        return ''
    s = _MARKS.sub('', unicodedata.normalize('NFKD', str(s))).lower()
    return re.sub(r'[^a-z0-9]+', ' ', _APOSTROPHES.sub('', _ELISION.sub(r'\1 ', s))).strip()


def _cap(s, n):
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(' ', 1)[0]
    return cut.rstrip()


def trip_months(t):
    """The months (1-12) a trip spans, from date to end_date, in the order met, each once (at most twelve); [] for an
    undated trip. The cards' data-month and the Trips page's Month menu use them, as the index's date words do."""
    start = t.get('date')
    if not start:
        return []
    end = t.get('end_date') or start
    if end < start:
        end = start
    months, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month) and len(months) < 12:
        if m not in months:
            months.append(m)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


def date_words(t):
    """The words of a trip's own date, as its card prints it: its year (both years when it ends in another) and the
    full English name of every month from date to end_date ('jun' then finds 'june'). No day of the month (a bare
    number would start every year) and no ski season. [] for an undated trip. The words are a bag: a trip from
    December 2023 to January 2024 is also found by 'december 2024'."""
    start = t.get('date')
    if not start:
        return []
    end = max(t.get('end_date') or start, start)
    years = [str(start.year)] + ([str(end.year)] if end.year != start.year else [])
    return years + [MONTH_NAMES[m - 1] for m in trip_months(t)]


def entry(t):
    """{'s': slug, 't': title, 'p': place + region, 'k': keywords, 'x': write-ups, 'r': plain write-up text (for
    snippets)}; every text field but r normalised. 'k' is, in this order: the activity label (and the Other sub-type's
    word), the activity's other forms (ACTIVITY_WORDS, SUBTYPE_WORDS), the aliases, the named peaks and the summits: names
    (the trip's and its days'), the trip's year and months (date_words) and its route shape ('loop', 'out and back',
    'point to point')."""
    pk = (t.get('map') or {}).get('peaks') or []
    pk = [pk] if isinstance(pk, str) else pk
    peaks = [p for p in pk if isinstance(p, str)]
    for s in list(t.get('summits') or []) + [s for d in t.get('days') or [] for s in d.get('summits') or []]:
        if s['name'] not in peaks:
            peaks.append(s['name'])
    words = [t.get('activity_label') or '']
    if t.get('subtype'):
        words.append(SUB_WORD.get(t['subtype'], t['subtype']))
    # the activity's other forms, less the words its label already holds ('hiking' after 'Hiking')
    said = set(normalize(' '.join(words)).split())
    more = ACTIVITY_WORDS.get(t.get('activity'), '').split() + (SUBTYPE_WORDS.get(t['subtype'], '').split() if t.get('subtype') else [])
    words.append(' '.join(w for w in more if w not in said))
    bodies = [t['body_md']] + [d['body_md'] for d in t['days']]
    plain = ' '.join(markdown.plain(b) for b in bodies if b)
    return {
        's': t['slug'],
        't': normalize(t['title']),
        'p': normalize(' '.join(x for x in (t.get('place'), t.get('region')) if x)),
        'k': normalize(' '.join(words + list(t.get('aliases') or []) + peaks + date_words(t) + [t.get('route_shape') or ''])),
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
    write-up), 'd' (the month's full name and the day of the month, 'may 22', never the year: the year is the journal's
    and is in 'q', so '2024' alone lists no day), all normalised, plus 'r', the plain write-up for the snippet, 'f' ('1'
    when the day has photos, else '': the Has photos filter asks it of the day) and 'q', the journal's title and aliases.
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
        'd': ('%s %d' % (MONTH_NAMES[when.month - 1], when.day)) if when else '',
        'f': '1' if d.get('photos') else '',
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
