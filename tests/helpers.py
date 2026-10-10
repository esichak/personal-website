"""Fixture helpers for the Phase 1 and Phase 2 tests.

Synthetic trips are written as real content folders inside a temporary directory (an index.md in the front-matter
subset tools/lib/frontmatter.py reads, empty placeholder photo and GPX files, optional days/NN.md + NN.gpx) and loaded
with content.load_trip, so every test goes through the same parser and the same trip dict the build uses. Nothing here
touches content/, rendered/ or _site/.
"""
import os
import re
import sys
from datetime import date
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import frontmatter  # noqa: E402
from sitegen import core  # noqa: E402

LANDSCAPE = (1600, 1200)
PORTRAIT = (1200, 1600)
SQUARE = (1000, 1000)

# prose that exists only on a journal day: tests assert it never leaks into a facts summary or a series card
PCT_PROSE = 'Walked north out of Campo in the afternoon heat and camped at Hauser Creek.'


def photo(file, size=LANDSCAPE, alt=None, caption=None, sm=False):
    """A `photos:` entry for make_trip. size=None leaves w/h unrecorded; sm=True also writes the .sm copy on disk."""
    p = {'file': file}
    if size:
        p['w'], p['h'] = size
    p['alt'] = alt if alt is not None else 'Photo %s' % os.path.basename(file)
    if caption:
        p['caption'] = caption
    if sm:
        p['sm'] = True
    return p


def touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'a').close()


def _write_photos(folder, entries, missing):
    """Empty placeholder files for the declared photos (content.load_trip only checks existence, never bytes); the
    fixture-only `sm` flag is stripped before the entry goes into the front matter."""
    out = []
    for p in entries or []:
        p = dict(p)
        sm = p.pop('sm', False)
        f = p['file']
        if f not in missing:
            touch(os.path.join(folder, f))
        if sm:
            base, ext = os.path.splitext(f)
            touch(os.path.join(folder, base + '.sm' + ext))
        out.append(p)
    return out


def make_trip(root, slug, body='', days=None, track=False, missing=(), **meta):
    """Write <root>/<slug>/ as a real trip folder and return its path.

    meta -> front-matter keys of index.md (title, activity, kind, date, end_date, place, region, featured, draft,
    photos, cover_photo, cover_focal_x, cover_focal_y, card_summary, ...), dumped with frontmatter.dumps so the file is
    in exactly the subset tools/lib/frontmatter.py reads back (dates and times as strings, ints, floats, true/false).
    `photos` entries (see photo()) get empty placeholder files unless their file is listed in `missing`.
    body: the write-up below the front matter. track=True writes an empty track.gpx.
    days: a list of dicts, each with optional 'body', 'track' (default True: an empty NN.gpx), 'id' (default 01, 02,
    ...) and day front-matter keys ('day', 'title', 'date', 'photos', 'stats', 'hut').
    """
    folder = os.path.join(root, slug)
    os.makedirs(folder, exist_ok=True)
    meta = dict(meta)
    meta.setdefault('title', slug.replace('-', ' ').title())
    meta.setdefault('activity', 'hike')
    if meta.get('photos') is not None:
        meta['photos'] = _write_photos(folder, meta['photos'], missing)
    with open(os.path.join(folder, 'index.md'), 'w', encoding='utf-8') as fh:
        fh.write(frontmatter.render(meta, body))
    if track:
        touch(os.path.join(folder, 'track.gpx'))
    for i, d in enumerate(days or []):
        d = dict(d)
        did = d.pop('id', '%02d' % (i + 1))
        dbody = d.pop('body', '')
        dtrack = d.pop('track', True)
        d.setdefault('day', str(i + 1))
        if d.get('photos') is not None:
            d['photos'] = _write_photos(folder, d['photos'], missing)
        os.makedirs(os.path.join(folder, 'days'), exist_ok=True)
        with open(os.path.join(folder, 'days', did + '.md'), 'w', encoding='utf-8') as fh:
            fh.write(frontmatter.render(d, dbody))
        if dtrack:
            touch(os.path.join(folder, 'days', did + '.gpx'))
    return folder


def make_series(root, slug='pacific-crest-trail-2024', written_day=1, tracks=(True, True, False), photos=True, **meta):
    """A PCT-shaped journal: kind series, no parent write-up, one day per entry of `tracks` (True = has a GPX), day
    `written_day` carrying PCT_PROSE, each day two photos (portrait first, landscape second) when photos=True."""
    titles = ('Campo', 'Hauser Creek', 'Lake Morena', 'Boulder Oaks', 'Mount Laguna')
    days = []
    for i, has_track in enumerate(tracks):
        d = {'id': '%03d' % (i + 1), 'title': titles[i % len(titles)], 'date': '2024-04-%02d' % (22 + i), 'track': has_track}
        if photos:
            d['photos'] = [photo('photos/d%03d-01.webp' % (i + 1), PORTRAIT, alt='Trail sign, day %d' % (i + 1)),
                           photo('photos/d%03d-02.webp' % (i + 1), LANDSCAPE, alt='Ridge view, day %d' % (i + 1))]
        if written_day is not None and i + 1 == written_day:
            d['body'] = PCT_PROSE
        days.append(d)
    m = dict(title='Pacific Crest Trail 2024', activity='hike', kind='series', date='2024-04-22', end_date='2024-09-21',
             place='Mexico to Canada', region='Pacific Crest Trail', route_shape='point-to-point')
    m.update(meta)
    return make_trip(root, slug, days=days, **m)


def load(root, slug):
    return content.load_trip(os.path.join(root, slug))


def newest_first(trips):
    return sorted(trips, key=lambda t: (t['date'] or date.min), reverse=True)


def load_dir(root, include_drafts=False):
    """content.load_all over a temp folder: every subfolder with an index.md, drafts dropped, newest first."""
    trips = []
    for name in sorted(os.listdir(root)):
        folder = os.path.join(root, name)
        if os.path.exists(os.path.join(folder, 'index.md')):
            t = content.load_trip(folder)
            if t['draft'] and not include_drafts:
                continue
            trips.append(t)
    return newest_first(trips)


def make_site(trips, register=True):
    """The site dict exactly as tools/build.py build() makes it (trips newest first; drafts are never passed in), and
    registered with core like the build does right after loading."""
    trips = newest_first(trips)
    site = {'trips': trips, 'by_slug': {t['slug']: t for t in trips},
            'published': [t for t in trips if t['kind'] != 'planned'],
            'planned': [t for t in trips if t['kind'] == 'planned']}
    if register:
        core.register_site(site)
    return site


def slugs(trips):
    return [t['slug'] for t in trips]


# ---------------------------------------------------------------- a small DOM for asserting on generated HTML

VOID = frozenset('area base br col embed hr img input link meta param source track wbr'.split())


class Node:
    """One element of a parsed page: tag, attrs (a valueless attribute such as `hidden` maps to '') and children (Nodes
    and text strings, in document order). Queries walk the subtree in document order."""

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.parent = parent

    def __getitem__(self, name):
        return self.attrs.get(name)

    def __contains__(self, name):
        return name in self.attrs

    def __repr__(self):
        return '<%s%s>' % (self.tag, ''.join(' %s="%s"' % kv for kv in self.attrs.items()))

    @property
    def classes(self):
        return (self.attrs.get('class') or '').split()

    def walk(self):
        for c in self.children:
            if isinstance(c, Node):
                yield c
                for d in c.walk():
                    yield d

    def find_all(self, tag=None, attrs=None, cls=None):
        """Descendants with this tag name, these exact attribute values and this class token (each optional)."""
        out = []
        for node in self.walk():
            if tag and node.tag != tag:
                continue
            if cls and cls not in node.classes:
                continue
            if attrs and any(node.attrs.get(k) != v for k, v in attrs.items()):
                continue
            out.append(node)
        return out

    def find(self, tag=None, attrs=None, cls=None):
        hits = self.find_all(tag, attrs, cls)
        return hits[0] if hits else None

    def by_id(self, id_):
        return self.find(attrs={'id': id_})

    def elements(self):
        """Direct child elements (text nodes dropped)."""
        return [c for c in self.children if isinstance(c, Node)]

    def text(self, clean=True):
        """The element's text content. clean=True turns nbsp into spaces and collapses whitespace runs."""
        s = ''.join(c if isinstance(c, str) else c.text(clean=False) for c in self.children)
        return plain_text(s) if clean else s


def plain_text(s):
    """Text as a reader sees it: nbsp -> space, whitespace runs collapsed, trimmed."""
    return re.sub(r'\s+', ' ', s.replace('\xa0', ' ')).strip()


class Doc(HTMLParser):
    """html.parser-based tree of a page or fragment: Doc(html_).find('nav', attrs={'aria-label': 'Main'}).find_all('a').
    Attribute order never matters, boolean attributes are present with value '', character references are decoded in
    text, and void elements (img, input, ...) never swallow what follows them."""

    def __init__(self, html_):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = Node('#root')
        self._stack = [self.root]
        self.feed(html_)
        self.close()

    def _add(self, tag, attrs, push):
        node = Node(tag, {k: ('' if v is None else v) for k, v in attrs}, self._stack[-1])
        self._stack[-1].children.append(node)
        if push:
            self._stack.append(node)

    def handle_starttag(self, tag, attrs):
        self._add(tag, attrs, tag not in VOID)

    def handle_startendtag(self, tag, attrs):
        self._add(tag, attrs, False)

    def handle_endtag(self, tag):
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                return

    def handle_data(self, data):
        self._stack[-1].children.append(data)

    def find_all(self, tag=None, attrs=None, cls=None):
        return self.root.find_all(tag, attrs, cls)

    def find(self, tag=None, attrs=None, cls=None):
        return self.root.find(tag, attrs, cls)

    def by_id(self, id_):
        return self.root.by_id(id_)

    def text(self, clean=True):
        return self.root.text(clean)
