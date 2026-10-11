"""Checks of a built site folder: what `tools/build.py --check` runs after a build, and `tools/validate.py --site DIR`.

check(out_dir, content_trips_dir=None) reads the folder once and returns one line per problem, in a stable order (pages
by path, then the site-wide files). It prints nothing and writes nothing: the caller prints the lines and sets the exit
code. The rules are also functions of their own (links, anchors, duplicate_ids, metadata, sitemap, feed, indexes, gpx),
each taking an Output (read(out_dir), or of({path: html}) for a site held in memory) or simply the folder.

The three rules build.check() always had keep their exact lines and its reading of a page (what is skipped, how a
srcset is split, a folder standing for its index.html, the decoding of a fragment); links() says where it is stricter:

    BROKEN <page> -> <ref>           an href / src / srcset that names no file of the build
    BROKEN ANCHOR <page> -> <ref>    a link to an id (#x, ../map/#x) that the page it lands on does not have
    DUPLICATE IDS <page>: a, b, c    ids that occur more than once on a page (the first six, sorted)

The newer rules cover what a link check cannot see, one line each, starting with the family:

    META       per page: one <title>, one description, one canonical that is the page's own URL and an og:url equal to
               it (the 404 page: neither, and noindex), a share image that exists, at most one BlogPosting block
    SITEMAP    sitemap.xml lists every indexable page once and nothing else
    FEED       every feed.xml item links to a page of the build
    INDEX      trips/search.json and trips/journal.json name built pages, and journal days name ids on them
    GPX        (with content_trips_dir) every download is its source file byte for byte, and a multi-day trip's
               combined file holds each day's track unchanged, in day order

A local checkout sits in iCloud Drive, which leaves conflict copies beside the real files ('meta 3.json',
'map-wide 4.webp', a folder 'first-tallac-lap 2'). They are never part of the published site (CI builds from git), so
every rule here treats them as absent: not a page, not a link target, not a download. A build made with --link holds
symlinks to the content; they are followed like the files they stand for.
"""
import collections
import hashlib
import json
import os
import posixpath
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import unquote

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import frontmatter  # noqa: E402

NOT_FOUND = '404.html'   # build.sitemap() leaves it out, and it is the one page without a canonical
SITEMAP = 'sitemap.xml'
FEED = 'feed.xml'
SEARCH_INDEX = 'trips/search.json'
JOURNAL_INDEX = 'trips/journal.json'

_CONFLICT = re.compile(r' \d+(\.[A-Za-z0-9]+)*$')   # the names tools/build.py leaves out of a build, read the same way


def conflict_copy(name):
    """True for an iCloud conflict copy: a file or folder name that ends in a space and a number, before the extension
    when there is one ('meta 3.json', 'region-alps-desktop.base 4.svg', 'first-tallac-lap 2'). Nothing the site makes
    is named like that (slugs and photo names have no spaces). Of a '/'-separated path the last part is looked at."""
    return bool(_CONFLICT.search(name.rsplit('/', 1)[-1]))


def _nfc(name):
    return unicodedata.normalize('NFC', name)


def _site_url():
    """core.SITE_URL, looked up when a check runs: this module stays importable without the page generator, and a test
    that patches the constant is followed."""
    from sitegen import core
    return core.SITE_URL


# ---------------------------------------------------------------- the built folder

_ID = re.compile(r'\bid="([^"]+)"')


class Output:
    """A built site as the checks see it: `files` and `dirs` (paths relative to the folder, '/'-separated, '' for the
    folder itself, conflict copies left out), `pages` (the .html files, sorted: the order every rule reports in),
    `site_url` (the public address the pages are checked against) and the text of each page. Made by read() from a
    folder or by of() from strings."""

    def __init__(self, files, dirs, out_dir=None, texts=None, site_url=None):
        self.out_dir = out_dir
        self.files = set(files)
        self.dirs = set(dirs) | {''}
        # as glob('**/*.html') listed them for build.check(): nothing inside a dot-folder, no dot-file
        self.pages = sorted(f for f in self.files
                            if f.endswith('.html') and not any(part.startswith('.') for part in f.split('/')))
        self.site_url = site_url or _site_url()
        self._by_url = {self.url_of(rel): rel for rel in self.pages}
        self._texts = dict(texts or {})   # of(): every file's text; read(): empty, files are read as they are needed
        self._last = (None, None)         # the page being checked: one at a time, so a large site is never held whole
        self._ids = {}
        self._heads = {}
        # names compared in one Unicode form: macOS can hold 'é' as two characters where the page was typed with one,
        # and git hands CI the one-character name either way, so the two spellings are the same file
        self._nfc_files = {_nfc(f): f for f in self.files}
        self._nfc_dirs = {_nfc(d) for d in self.dirs}

    def find(self, rel):
        """The build's own name for a file path, or None when it holds no such file (see _nfc_files)."""
        return rel if rel in self.files else self._nfc_files.get(_nfc(rel))

    def path(self, rel):
        """The file on disk, or None for a site held in memory."""
        return os.path.join(self.out_dir, *rel.split('/')) if self.out_dir is not None else None

    def data(self, rel):
        """A file's bytes."""
        if rel in self._texts:
            v = self._texts[rel]
            return v if isinstance(v, bytes) else v.encode('utf-8')
        with open(self.path(rel), 'rb') as fh:
            return fh.read()

    def _read(self, rel):
        if rel in self._texts:
            v = self._texts[rel]
            return v.decode('utf-8', 'replace') if isinstance(v, bytes) else v
        # a page that is not UTF-8 is still checked (the build writes UTF-8; this is for a folder from elsewhere)
        with open(self.path(rel), encoding='utf-8', errors='replace') as fh:
            return fh.read()

    def text(self, rel):
        """A page's HTML. The last page asked for is kept, so rules that follow each other on one page read it once."""
        if self._last[0] != rel:
            self._last = (rel, self._read(rel))
        return self._last[1]

    def ids(self, rel):
        """The id set of a page, read once per check (a page is the target of many links)."""
        if rel not in self._ids:
            self._ids[rel] = set(_ID.findall(self.text(rel) if self._last[0] == rel else self._read(rel)))
        return self._ids[rel]

    def resolve(self, here, path):
        """The file a URL path names when it is followed from the folder `here` ('' for the site root): a folder stands
        for its index.html. None when the build has no such file, which is also the answer for a path that leaves the
        site (/x, ../../../x): only the build's own files are looked at, never the disk around it."""
        target = posixpath.normpath(posixpath.join(here, path))
        if target == '.':
            target = ''
        if target in self.dirs or _nfc(target) in self._nfc_dirs:
            target = posixpath.join(target, 'index.html')
        return self.find(target)

    def url_of(self, page):
        """A page's own address: the site URL and its path, with index.html dropped (as core.document's canonical)."""
        head, name = posixpath.split(page)
        if name == 'index.html':
            return self.site_url + (head + '/' if head else '')
        return self.site_url + page

    def page_at(self, url):
        """The page whose own address this is (SITE_URL + 'trips/x/' -> 'trips/x/index.html'), or None. The address is
        taken as written: another spelling of a page (.../trips/x/index.html, .../trips/x) is not its address."""
        return self._by_url.get(url)

    def head(self, page):
        """What the page's <head> declares (see _Head), parsed once."""
        if page not in self._heads:
            self._heads[page] = _Head(self.text(page))
        return self._heads[page]

    def indexable(self, page):
        """A page a search engine may list, which is what sitemap.xml holds: not noindex, and not the 404 page."""
        return not is_not_found(page) and not self.head(page).noindex


def _folder_key(st):
    return st.st_dev, st.st_ino


def read(out_dir, site_url=None):
    """The Output of a built folder. Symlinks are followed (a --link build), a dangling one is no file, and a link
    that leads back to a folder it sits in is not entered (the walk would never end). Raises OSError when out_dir is
    not a readable folder."""
    files, dirs = set(), set()
    stack = [('', out_dir, frozenset([_folder_key(os.stat(out_dir))]))]
    while stack:
        prefix, folder, above = stack.pop()
        with os.scandir(folder) as entries:
            for e in entries:
                if conflict_copy(e.name):
                    continue
                if e.is_dir():
                    key = _folder_key(e.stat())
                    if key in above:
                        continue
                    dirs.add(prefix + e.name)
                    stack.append((prefix + e.name + '/', e.path, above | {key}))
                elif e.is_file():
                    files.add(prefix + e.name)
    return Output(files, dirs, out_dir=out_dir, site_url=site_url)


def of(pages, files=(), site_url=None):
    """An Output held in memory, for unit tests: `pages` is {path: html}; `files` names what else the build holds, as a
    list of paths or as {path: text or bytes} for the ones a rule reads (sitemap.xml, feed.xml, the indexes, GPX)."""
    texts = dict(pages)
    if isinstance(files, dict):
        texts.update(files)
    names = {n for n in set(texts) | set(files) if not any(conflict_copy(part) for part in n.split('/'))}
    dirs = set()
    for n in names:
        parts = n.split('/')[:-1]
        dirs.update('/'.join(parts[:i]) for i in range(1, len(parts) + 1))
    return Output(names, dirs, texts={n: texts.get(n, '') for n in names}, site_url=site_url)


def _output(out):
    return out if isinstance(out, Output) else read(out)


def _pages(out, page):
    return out.pages if page is None else [page]


def is_not_found(page):
    """The 404 page: the one GitHub Pages serves for a missing path, at the site root."""
    return page == NOT_FOUND


# ---------------------------------------------------------------- links, anchors, ids (the rules build.check() had)

_REF = re.compile(r'''(href|src|srcset)="([^"]+)"''')
_SELF = re.compile(r'href="#([^"]+)"')
_ELSEWHERE = ('http:', 'https:', 'mailto:', '#', 'data:', 'javascript:')


def _urls(attr, value):
    """The URLs of one attribute value. A srcset ('a.webp 800w, b.webp 1600w') is the first word of each
    comma-separated candidate; an href or a src is one URL, spaces and all (a file name may hold one: the old check
    cut such a link at its first space and then reported the stump as broken)."""
    if attr != 'srcset':
        return [value]
    return [x.strip().split(' ')[0] for x in value.split(',')] if ' ' in value else [value]


def links(out, page=None):
    """BROKEN and BROKEN ANCHOR lines for links that leave the page, in the order the page holds them (a link that
    occurs three times is three lines, as before). Every double-quoted href, src and srcset is read, wherever it stands
    (imagesrcset and data-src too). Skipped: other sites, mailto:, data:, javascript: and same-page #fragments (see
    anchors). The path is taken as written (no percent-decoding), a folder means its index.html, and a #fragment,
    which is percent-decoded, must be an id of the page the link lands on.

    Two things differ from build.check(), both on purpose. An address under the site's own URL (SITE_URL + path: the
    canonical link, a write-up that links to another report in full) is followed like a relative one instead of being
    skipped. And a path is looked up in the build only, by its exact spelling: a link that climbs out of the folder, or
    that differs from the file name in upper and lower case, is broken here on every machine, as it is on the web
    server, where the old check asked the local file system (which on a Mac ignores case)."""
    out = _output(out)
    problems = []
    for rel in _pages(out, page):
        here = posixpath.dirname(rel)
        for attr, value in _REF.findall(out.text(rel)):
            for u in _urls(attr, value):
                if not u:
                    continue
                if u.startswith(out.site_url):
                    base, path = '', u[len(out.site_url):].split('#')[0].split('?')[0] or '.'
                elif u.startswith(_ELSEWHERE):
                    continue
                else:
                    base, path = here, u.split('#')[0].split('?')[0]
                    if not path:
                        continue
                target = out.resolve(base, path)
                if target is None:
                    problems.append('BROKEN %s -> %s' % (rel, u))
                    continue
                # a link into another page's section (map/#region-utah, ../#map) must land on an element with that id
                fragment = unquote(u.split('#', 1)[1]) if '#' in u else ''
                if fragment and target.endswith('.html') and fragment not in out.ids(target):
                    problems.append('BROKEN ANCHOR %s -> %s' % (rel, u))
    return problems


def anchors(out, page=None):
    """BROKEN ANCHOR lines for same-page links: every href="#x" needs an element with id="x" on its own page (the
    fragment is compared as written)."""
    out = _output(out)
    problems = []
    for rel in _pages(out, page):
        ids = out.ids(rel)
        for fragment in _SELF.findall(out.text(rel)):
            if fragment not in ids:
                problems.append('BROKEN ANCHOR %s -> #%s' % (rel, fragment))
    return problems


def duplicate_ids(out, page=None):
    """One DUPLICATE IDS line per page that uses an id more than once, naming the first six in sorted order."""
    out = _output(out)
    problems = []
    for rel in _pages(out, page):
        counts = collections.Counter(_ID.findall(out.text(rel)))
        dup = sorted(i for i, n in counts.items() if n > 1)
        if dup:
            problems.append('DUPLICATE IDS %s: %s' % (rel, ', '.join(dup[:6])))
    return problems


# ---------------------------------------------------------------- head metadata

# Found by position, not by one lazy pattern from tag to tag: on a page with an opening tag that is never closed such a
# pattern scans to the end of the file once per opening tag, which takes minutes on a large page from elsewhere.
_HEAD_OPEN = re.compile(r'<head\b', re.I)
_HEAD_CLOSE = re.compile(r'</head\s*>', re.I)
_SCRIPT_OPEN = re.compile(r'<script\b', re.I)
_SCRIPT_CLOSE = re.compile(r'</script\s*>', re.I)
_LD_TYPE = re.compile(r'''\btype\s*=\s*["']?application/ld\+json["']?''', re.I)
_DECLARATION = re.compile(rb'<!(?!--|\[CDATA\[)')   # a DOCTYPE or an entity declaration (tools/lib/gpxroute.py's rule)


def _head_text(text):
    """What stands between <head ...> and </head>, or None when the page has no such pair."""
    m = _HEAD_OPEN.search(text)
    if not m:
        return None
    start = text.find('>', m.end())
    if start < 0:
        return None
    end = _HEAD_CLOSE.search(text, start + 1)
    return text[start + 1:end.start()] if end else None


class _Head(HTMLParser):
    """The tags of a page's <head> that the META rules read: how many <title> elements, every <meta> (its attributes)
    and the href of every <link rel="canonical">. Only the head is parsed: an inline SVG in the body may hold a
    <title> of its own, and a page of half a megabyte has a head of two kilobytes. A script's text is never read as
    tags (html.parser), so a title quoted inside the structured-data block does not count."""

    def __init__(self, text):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.titles = 0
        self.metas = []
        self.canonicals = []
        head = _head_text(text)
        self.found = head is not None
        self.unreadable = False
        if self.found:
            try:
                self.feed(head)
                self.close()
            except (AssertionError, NotImplementedError):   # html.parser gives up on a malformed <![...]> declaration
                self.unreadable = True

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.titles += 1
        elif tag == 'meta':
            self.metas.append({k: (v or '') for k, v in attrs})
        elif tag == 'link':
            a = dict(attrs)
            if 'canonical' in (a.get('rel') or '').lower().split():
                self.canonicals.append(a.get('href') or '')

    def named(self, name):
        """The content of every <meta name="...">."""
        return [m.get('content', '') for m in self.metas if m.get('name', '').lower() == name]

    def prop(self, name):
        """The content of every <meta property="...">."""
        return [m.get('content', '') for m in self.metas if m.get('property', '') == name]

    @property
    def noindex(self):
        words = re.split(r'[\s,]+', ' '.join(self.named('robots')).lower())
        return 'noindex' in words or 'none' in words


def structured_blocks(text):
    """The text of every <script type="application/ld+json"> on a page, head or body."""
    blocks, pos = [], 0
    while True:
        m = _SCRIPT_OPEN.search(text, pos)
        if not m:
            break
        end = text.find('>', m.end())
        if end < 0:
            break   # the tag never closes, and so does none after it
        pos = end + 1
        if not _LD_TYPE.search(text, m.end(), end):
            continue
        close = _SCRIPT_CLOSE.search(text, pos)
        if not close:
            break
        blocks.append(text[pos:close.start()])
        pos = close.end()
    return blocks


def _count(n, what, expected):
    return '%d %s (expected %s)' % (n, what, expected)


def _page_metadata(out, rel):
    """What is wrong with one page's metadata, as the texts that follow 'META <page>: '."""
    found = []
    head = out.head(rel)
    if not head.found:
        found.append('no <head> element')
    elif head.unreadable:
        found.append('the <head> could not be read as HTML')
    else:
        if head.titles != 1:
            found.append(_count(head.titles, '<title> elements in the head', '1'))
        n = len(head.named('description'))
        if n != 1:
            found.append(_count(n, 'meta description tags', '1'))
        canonicals, og_urls = head.canonicals, head.prop('og:url')
        if is_not_found(rel):
            if canonicals:
                found.append('the 404 page has a canonical link (%s)' % canonicals[0])
            if og_urls:
                found.append('the 404 page has an og:url (%s)' % og_urls[0])
            if not head.noindex:
                found.append('the 404 page is not noindex')
        else:
            own = out.url_of(rel)
            for values, one, many in ((canonicals, 'canonical', 'canonical links'), (og_urls, 'og:url', 'og:url tags')):
                if len(values) != 1:
                    found.append(_count(len(values), many, '1'))
                elif values[0] != own:
                    found.append('%s is %s (expected %s)' % (one, values[0], own))
        images = head.prop('og:image')
        if len(images) > 1:
            found.append(_count(len(images), 'og:image tags', 'at most 1'))
        for url in images:
            if not url.startswith(out.site_url):
                found.append('og:image is not an absolute URL under %s: %s' % (out.site_url, url))
            elif out.find(url[len(out.site_url):]) is None:
                found.append('og:image file is not in the build: %s' % url)
        w, h = head.prop('og:image:width'), head.prop('og:image:height')
        if w and not h:
            found.append('og:image:width without og:image:height')
        if h and not w:
            found.append('og:image:height without og:image:width')
    blocks = structured_blocks(out.text(rel))
    if len(blocks) > 1:
        found.append(_count(len(blocks), 'application/ld+json blocks', 'at most 1'))
    for block in blocks:
        try:
            data = json.loads(block)
        except (ValueError, RecursionError) as ex:
            found.append('application/ld+json is not valid JSON (%s)' % (ex if isinstance(ex, ValueError) else 'nested too deeply'))
            continue
        kind = data.get('@type') if isinstance(data, dict) else None
        if kind != 'BlogPosting':
            found.append('application/ld+json @type is %s (expected BlogPosting)' % json.dumps(kind))
    return found


def metadata(out, page=None):
    """META lines, per page, in this order:

    - exactly one <title> and one <meta name="description"> in the head;
    - exactly one <link rel="canonical">, equal to the page's own URL (the site URL and its path, index.html dropped),
      and exactly one og:url equal to it. The 404 page stands for no URL: it has neither, and it is noindex;
    - at most one og:image, an absolute URL under the site URL whose file is in the build;
    - og:image:width and og:image:height both or neither;
    - at most one <script type="application/ld+json"> anywhere on the page, and it is JSON whose @type is BlogPosting.

    Everything else in a head is left alone (og:image:type and :alt, twitter:image:alt, article:published_time and
    article:modified_time, inline scripts)."""
    out = _output(out)
    return ['META %s: %s' % (rel, text) for rel in _pages(out, page) for text in _page_metadata(out, rel)]


# ---------------------------------------------------------------- sitemap.xml, feed.xml, the search indexes

def _local(tag):
    """An XML tag without its namespace ('{http://www.sitemaps.org/schemas/sitemap/0.9}loc' -> 'loc')."""
    return tag.rsplit('}', 1)[-1]


def _xml(out, name, family):
    """(root element, None), or (None, the one problem line) when the file is missing or is not well-formed XML."""
    if name not in out.files:
        return None, '%s %s: missing from the build' % (family, name)
    data = out.data(name)
    if _DECLARATION.search(data):
        # nothing the build writes has one, and an entity declaration can expand a small file into gigabytes
        return None, '%s %s: not well-formed XML (DOCTYPE and entity declarations are not accepted)' % (family, name)
    try:
        return ET.fromstring(data), None
    except (ET.ParseError, ValueError, LookupError) as ex:   # also an encoding the parser does not know or support
        return None, '%s %s: not well-formed XML (%s)' % (family, name, ex)


def sitemap(out):
    """SITEMAP lines: sitemap.xml is there and parses; every indexable page (not noindex, not the 404 page) is listed,
    by its own URL, exactly once; and nothing else is listed (no helper map page, no 404, no data file, no address
    without a page). Missing pages come first, in page order, then the listed addresses in the file's order."""
    out = _output(out)
    root, problem = _xml(out, SITEMAP, 'SITEMAP')
    if problem:
        return [problem]
    locs = [(el.text or '').strip() for el in root.iter() if _local(el.tag) == 'loc']
    counts = collections.Counter(locs)
    problems = []
    for rel in out.pages:
        if out.indexable(rel) and out.url_of(rel) not in counts:
            problems.append('SITEMAP %s: %s is not listed' % (SITEMAP, out.url_of(rel)))
    for url in dict.fromkeys(locs):
        rel = out.page_at(url)
        if rel is None:
            problems.append('SITEMAP %s: %s is not the address of a page of this build' % (SITEMAP, url))
        elif is_not_found(rel):
            problems.append('SITEMAP %s: %s is the 404 page' % (SITEMAP, url))
        elif out.head(rel).noindex:
            problems.append('SITEMAP %s: %s is a noindex page' % (SITEMAP, url))
        elif counts[url] > 1:
            problems.append('SITEMAP %s: %s is listed %d times' % (SITEMAP, url, counts[url]))
    return problems


def feed(out):
    """FEED lines: feed.xml is there and parses, and every item's <link> and <guid> is the site URL plus a built page
    (items are numbered from 1, in the feed's order)."""
    out = _output(out)
    root, problem = _xml(out, FEED, 'FEED')
    if problem:
        return [problem]
    problems = []
    for i, item in enumerate((el for el in root.iter() if _local(el.tag) == 'item'), 1):
        for what in ('link', 'guid'):
            found = [el for el in item if _local(el.tag) == what]
            if not found:
                problems.append('FEED %s: item %d has no <%s>' % (FEED, i, what))
            for el in found:
                url = (el.text or '').strip()
                if out.page_at(url) is None:
                    problems.append('FEED %s: item %d %s %s is not the address of a page of this build'
                                    % (FEED, i, what, url))
    return problems


def indexes(out):
    """INDEX lines for the two search indexes trips.js reads, when the build has them: every entry's "s" is the slug of
    a built trips/<s>/ page, and every journal-day entry's "a" is an id on that page (the day's anchor the result links
    to). A slug or day that many entries share is reported once."""
    out = _output(out)
    problems = []

    def add(name, s):
        line = 'INDEX %s: %s' % (name, s)
        if line not in problems:
            problems.append(line)

    for name in (SEARCH_INDEX, JOURNAL_INDEX):
        if name not in out.files:
            continue
        try:
            entries = json.loads(out.data(name).decode('utf-8'))
        except (ValueError, RecursionError) as ex:
            add(name, 'not valid JSON (%s)' % (ex if isinstance(ex, ValueError) else 'nested too deeply'))
            continue
        if not isinstance(entries, list):
            add(name, 'not a list of entries')
            continue
        for i, e in enumerate(entries, 1):
            slug = e.get('s') if isinstance(e, dict) else None
            if not isinstance(slug, str) or not slug:
                add(name, 'entry %d has no "s" (the trip\'s slug)' % i)
                continue
            target = 'trips/%s/index.html' % slug
            if out.page_at(out.site_url + 'trips/%s/' % slug) is None:
                add(name, '"%s" has no page trips/%s/' % (slug, slug))
                continue
            if name != JOURNAL_INDEX:
                continue
            anchor = e.get('a')
            if not isinstance(anchor, str) or not anchor:
                add(name, 'entry %d has no "a" (the day\'s anchor)' % i)
            elif anchor not in out.ids(target):
                add(name, '"%s" day "%s" is not an id on trips/%s/' % (slug, anchor, slug))
    return problems


# ---------------------------------------------------------------- GPX downloads against their sources

_GPX = re.compile(r'^trips/([^/]+)/(?:\1\.gpx|gpx/\1-day-([^/]+)\.gpx)$')
_TRK = re.compile(rb'<trk(?:\s[^>]*)?>.*?</trk>', re.S)   # the blocks build.copy_trip_assets lifts out of each day's file


def _file_bytes(path):
    with open(path, 'rb') as fh:
        return fh.read()


def _kind(folder):
    """`kind` of a trip folder's index.md ('trip' when the line is absent), or None when the file cannot be read."""
    try:
        with open(os.path.join(folder, 'index.md'), encoding='utf-8') as fh:
            meta, _body = frontmatter.split(fh.read())
    except (OSError, ValueError):
        return None
    return meta.get('kind') or 'trip'


def _day_tracks(folder):
    """[(day id, path of its GPX)] for the days of a trip folder that have a track, in day order: content.load_trip's
    rule (one day per days/*.md, sorted; its track is the .gpx of the same name)."""
    days = os.path.join(folder, 'days')
    if not os.path.isdir(days):
        return []
    # sorted by file name, then the extension dropped: '02-b.md' comes before '02.md', as in content.load_trip
    stems = [os.path.splitext(n)[0] for n in sorted(n for n in os.listdir(days) if n.endswith('.md') and not conflict_copy(n))]
    return [(s, os.path.join(days, s + '.gpx')) for s in stems if os.path.isfile(os.path.join(days, s + '.gpx'))]


def _copied(out, rel, source, name):
    """A download that must be its source file byte for byte: [] when it is (or when there is no source to compare it
    with), else the one GPX line with the first twelve digits of both SHA-256 sums."""
    if not os.path.isfile(source):
        return []
    path = out.path(rel)
    if path is not None and os.path.realpath(path) == os.path.realpath(source):
        return []   # a --link build: the download is the source file itself
    published, original = hashlib.sha256(out.data(rel)).hexdigest(), hashlib.sha256(_file_bytes(source)).hexdigest()
    if published == original:
        return []
    return ['GPX %s: not the bytes of %s (sha256 %s published, %s source)' % (rel, name, published[:12], original[:12])]


def _combined(out, rel, days, where):
    """A multi-day trip's "Download all GPX" file: every <trk> block of every day's file must be in it unchanged, in
    day order, and it must hold no other track. days: [(day id, [block, ...])]."""
    data = out.data(rel)
    problems, pos, total = [], 0, 0
    for day, blocks in days:
        total += len(blocks)
        for block in blocks:
            at = data.find(block, pos)
            if at < 0:
                problems.append('GPX %s: the track of %sdays/%s.gpx is not in the file unchanged and in day order'
                                % (rel, where, day))
                break
            pos = at + len(block)
    held = len(_TRK.findall(data))
    if held != total:
        problems.append('GPX %s: holds %d <trk> blocks, the day files hold %d' % (rel, held, total))
    elif not total:
        # the page offers this file as "Download all GPX": day files that hold a route and no recorded track leave it empty
        problems.append('GPX %s: holds no track (no day file has a <trk>)' % rel)
    # each block is the day file's own bytes, but under another root: a prefix declared on the day file's <gpx> must be
    # declared here too, or the download is not XML a GPX reader can open
    if _DECLARATION.search(data):
        problems.append('GPX %s: not well-formed XML (DOCTYPE and entity declarations are not accepted)' % rel)
    else:
        try:
            ET.fromstring(data)
        except (ET.ParseError, ValueError, LookupError) as ex:
            problems.append('GPX %s: not well-formed XML (%s)' % (rel, ex))
    return problems


def gpx(out, content_trips_dir):
    """GPX lines: the published tracks against the content they come from (content_trips_dir: a folder of trip folders,
    as content/trips). The names are build.copy_trip_assets':

    - trips/<slug>/<slug>.gpx is content/trips/<slug>/track.gpx byte for byte (a report or a tick-list goal), or, for a
      multi-day trip whose days have tracks, the combined file: each day's <trk> blocks unchanged, in day order;
    - trips/<slug>/gpx/<slug>-day-<id>.gpx is content/trips/<slug>/days/<id>.gpx byte for byte (a multi-day trip's or a
      journal's day).

    A download without a source file is not this rule's business (a link to a missing download is a BROKEN line)."""
    out = _output(out)
    problems = []
    for rel in sorted(out.files):
        m = _GPX.match(rel)
        if not m:
            continue
        slug, day = m.group(1), m.group(2)
        folder = os.path.join(content_trips_dir, slug)
        where = 'content/trips/%s/' % slug
        if day is not None:
            problems += _copied(out, rel, os.path.join(folder, 'days', day + '.gpx'), '%sdays/%s.gpx' % (where, day))
            continue
        days = []
        if _kind(folder) == 'multi-day':
            days = [(d, _TRK.findall(_file_bytes(p))) for d, p in _day_tracks(folder)]
        if days:   # build.copy_trip_assets writes the combined file when any day has a track file
            problems += _combined(out, rel, days, where)
        else:
            problems += _copied(out, rel, os.path.join(folder, 'track.gpx'), where + 'track.gpx')
    return problems


# ---------------------------------------------------------------- everything

def check(out_dir, content_trips_dir=None, site_url=None):
    """Every problem of a built folder, as lines. First the link, anchor and id lines page by page (pages sorted by
    path; within a page: links in page order, then same-page anchors, then the DUPLICATE IDS line), which is what
    build.check() printed; then META page by page, SITEMAP, FEED, INDEX, and GPX when content_trips_dir is given.
    site_url: the site's public address (default core.SITE_URL). [] means the build is sound."""
    out = read(out_dir, site_url)
    problems, meta = [], []
    for rel in out.pages:
        problems += links(out, rel) + anchors(out, rel) + duplicate_ids(out, rel)
        meta += metadata(out, rel)
    problems += meta + sitemap(out) + feed(out) + indexes(out)
    if content_trips_dir:
        problems += gpx(out, content_trips_dir)
    return problems
