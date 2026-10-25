#!/usr/bin/env python3
"""Build the static site into _site/ (stdlib only; this is what the GitHub Action runs).

  python3 tools/build.py            # build
  python3 tools/build.py --serve    # build (photos, maps and GPX linked, not copied), then serve http://localhost:8000
  python3 tools/build.py --serve --open SLUG --watch   # ... open trips/SLUG/ in the browser, rebuild on every change
  python3 tools/build.py --check    # build, then check the built site: links, images, anchors, metadata, feed, GPX
  python3 tools/build.py --out DIR --only report,home --link   # fast dev build of some page modules
"""
import argparse
import glob
import hashlib
import html
import importlib
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import mapkit  # noqa: E402
from sitegen import core  # noqa: E402
from sitegen import author  # noqa: E402
from sitegen import curation  # noqa: E402
from sitegen import sitecheck  # noqa: E402
import checks  # noqa: E402
import goals  # noqa: E402
import markdown  # noqa: E402

OUT = os.path.join(ROOT, '_site')
PAGE_MODULES = ['home', 'trips', 'ticklist', 'section', 'report', 'multiday', 'series', 'archive', 'region', 'about', 'notfound']


def _text(path):
    """A text file's contents, the handle closed."""
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def strip_css_comments(css):
    """The stylesheet without its comments, for publishing: the sources under assets/css stay commented, the bundle every
    page waits for does not carry them (about a third of its compressed size). Strings are left alone, and a comment
    wedged between two tokens with no space on either side is kept, because removing it could join them (`0/**/auto`)
    and a space could change a selector (`.a/**/.b`). Blank lines left behind are dropped."""
    out, i, n = [], 0, len(css)
    while i < n:
        c = css[i]
        if c in '"\'':
            j = i + 1
            while j < n and css[j] != c:
                j += 2 if css[j] == '\\' else 1
            out.append(css[i:j + 1])
            i = j + 1
        elif css.startswith('/*', i):
            end = i
            while css.startswith('/*', end):   # comments with nothing between them are judged as one
                j = css.find('*/', end + 2)
                end = n if j < 0 else j + 2
            before = out[-1][-1] if out and out[-1] else ''
            after = css[end] if end < n else ''
            if before and after and not before.isspace() and not after.isspace():
                out.append(css[i:end])   # tightly between two tokens: keep it
            i = end
        else:
            out.append(c)
            i += 1
    lines = [ln.rstrip() for ln in ''.join(out).split('\n')]
    return '\n'.join(ln for ln in lines if ln.strip()) + '\n'


def conflict_copy(path):
    """True for an iCloud conflict copy of a rendered file: iCloud Drive names them by adding a space and a number before
    the extension ('meta 3.json', 'map-wide 4.webp', 'region-alps-desktop.svg 3.html'). The renderer never writes such
    a name, so a local build leaves them out of the site (CI's checkout has none). One rule, shared with the site
    checks, which ignore the same names."""
    return sitecheck.conflict_copy(os.path.basename(path))


def css_bundle():
    # the site's own fonts first, when tools/fonts.py has written them (perf-02)
    fonts = os.path.join(ROOT, 'assets', 'css', 'fonts.css')
    parts = (['/* fonts.css */\n' + _text(fonts)] if os.path.exists(fonts) else []) + [_text(os.path.join(ROOT, 'assets', 'css', 'base.css'))]
    parts.append('/* map + profile internals (from tools/lib/mapkit.py) */\n' + mapkit.MAP_CSS.strip()
                 .replace("'Geist Mono', ui-monospace, 'SF Mono', monospace", 'var(--mono)')
                 .replace("Archivo, 'Helvetica Neue', system-ui, sans-serif", 'var(--sans)')
                 .replace("'Source Serif 4', Georgia, serif", 'var(--serif)'))
    for f in sorted(glob.glob(os.path.join(ROOT, 'assets', 'css', 'pages', '*.css'))):
        if conflict_copy(f):   # 'trips 2.css': its rules would be in the bundle twice
            continue
        parts.append('/* %s */\n' % os.path.basename(f) + _text(f))
    # the print sheet last, so its rules win at equal weight (visual-13); a test's temp tree may have none
    prt = os.path.join(ROOT, 'assets', 'css', 'print.css')
    if os.path.exists(prt):
        parts.append('/* print.css */\n' + _text(prt))
    return strip_css_comments('\n'.join(parts))


def js_bundle():
    parts = [_text(os.path.join(ROOT, 'assets', 'js', 'base.js'))]
    for f in sorted(glob.glob(os.path.join(ROOT, 'assets', 'js', 'pages', '*.js'))):
        if conflict_copy(f):   # 'trips 2.js': the page script would run twice
            continue
        parts.append('/* %s */\n' % os.path.basename(f) + _text(f))
    return '\n'.join(parts)


LINK = False


def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if LINK:
        if not os.path.lexists(dst):
            os.symlink(os.path.abspath(src), dst)
    else:
        shutil.copy2(src, dst)


_ROOT_SVG = re.compile(r'^\s*<svg\b([^>]*)>')
_DROP_ATTR = re.compile(r'\s(?:aria-hidden|aria-label|role|style|xmlns)="[^"]*"')
_CSS_RULES = [(re.match(r'\.([\w-]+)', ln).group(1), ln.strip()) for ln in mapkit.MAP_CSS.strip().splitlines()
              if re.match(r'\.([\w-]+)', ln)]


def drawing_svg(src, name):
    """A rendered tile / glyph fragment as a standalone SVG image (core.glyph / core.tile serve it as <img>): the route
    colour filled in, the root's inline-only attributes (aria, style) dropped, and only the mapkit.MAP_CSS rules whose
    class the drawing uses, in its own <style>. Glyphs keep a constant stroke at any drawn size (non-scaling-stroke)."""
    s = _text(src).replace('{{route}}', '#D2381A').replace('@@ROOT@@', '../../')
    m = _ROOT_SVG.match(s)
    if not m:
        return None
    used = {c for v in re.findall(r'class="([^"]+)"', s) for c in v.split()}
    rules = [r for c, r in _CSS_RULES if c in used]
    if name != 'tile':
        rules.append('.gl-trk{vector-effect:non-scaling-stroke}')
    root = '<svg xmlns="http://www.w3.org/2000/svg"%s>' % _DROP_ATTR.sub('', m.group(1))
    style = ('<style>%s</style>' % ''.join(rules)) if rules else ''
    return root + style + s[m.end():]


_TRK = re.compile(r'<trk(?:\s[^>]*)?>.*?</trk>', re.S)   # one recorded track of a day's file, attributes or not
_GPX_TAG = re.compile(r'''<gpx\b(?:[^>"']|"[^"]*"|'[^']*')*>''')   # a '>' inside a quoted attribute value does not end the tag
_XMLNS = re.compile(r'''\sxmlns:([A-Za-z_][\w.-]*)\s*=\s*("[^"]*"|'[^']*')''')


def gpx_root_tag(text):
    """The <gpx ...> start tag of a GPX file's text, '' when it has none before its first track. Comments are skipped (one
    may name the tag), and everything is found by position: a file of a megabyte is read once, whatever it holds."""
    head, out, pos = text[:max(text.find('<trk'), 0)], [], 0
    while True:
        i = head.find('<!--', pos)
        j = head.find('-->', i + 4) if i >= 0 else -1
        if j < 0:
            break
        out.append(head[pos:i])
        pos = j + 3
    head = ''.join(out) + head[pos:]
    i = head.find('<gpx')
    m = _GPX_TAG.match(head, i) if i >= 0 else None
    return m.group(0) if m else ''


def copy_part_drawings():
    """A journal part's drawing for its row in a region's list (rendered/site/<name>-g64.svg.html, render.part_glyph), written
    out as the standalone assets/maps/<name>-g64.svg, as a trip's glyph is (drawing_svg). The names written."""
    out = []
    os.makedirs(os.path.join(OUT, 'assets', 'maps'), exist_ok=True)
    for f in sorted(glob.glob(os.path.join(ROOT, 'rendered', 'site', '*-g64.svg.html'))):
        svg = None if conflict_copy(f) else drawing_svg(f, 'g64')
        if svg:
            name = os.path.basename(f)[:-len('.html')]
            with open(os.path.join(OUT, 'assets', 'maps', name), 'w', encoding='utf-8') as fh:
                fh.write(svg)
            out.append(name)
    return out


def copy_about_assets(about):
    """The About page's photo (content/about.md's photo: line) and its 800 px copy, into _site/about/ beside the page."""
    p = (about or {}).get('photo')
    if not p:
        return
    for f in (p['file'], p.get('sm')):
        src = os.path.join(about['dir'], f) if f else None
        if src and os.path.exists(src):
            copy(src, os.path.join(OUT, 'about', f))


def copy_trip_assets(t):
    out = os.path.join(OUT, 'trips', t['slug'])
    os.makedirs(out, exist_ok=True)
    # the drawings and the map renders are made from the track: a trip whose track is gone publishes none of them, even
    # while rendered/trips/<slug>/ (committed, and only rewritten by tools/render.py) still holds them
    if core.has_track(t):
        for name in ('tile', 'g112', 'g64'):
            src = os.path.join(t['rendered'], name + '.svg.html')
            svg = drawing_svg(src, name) if os.path.exists(src) else None
            if svg:
                with open(os.path.join(out, name + '.svg'), 'w', encoding='utf-8') as fh:
                    fh.write(svg)
        for p in glob.glob(os.path.join(t['rendered'], '*.png')) + glob.glob(os.path.join(t['rendered'], '*.webp')) + glob.glob(os.path.join(t['rendered'], '*.base.svg')):
            if not conflict_copy(p):
                copy(p, os.path.join(out, 'map', os.path.basename(p)))
    for p in glob.glob(os.path.join(t['dir'], 'photos', '*')):
        copy(p, os.path.join(out, 'photos', os.path.basename(p)))
    if t['track']:
        copy(t['track'], os.path.join(out, t['slug'] + '.gpx'))
    for d in t['days']:
        if d['track']:
            copy(d['track'], os.path.join(out, 'gpx', '%s-day-%s.gpx' % (t['slug'], d['id'])))
    if t['kind'] == 'multi-day' and any(d['track'] for d in t['days']):
        # one GPX with a <trk> per day, for the "Download all GPX" action. The condition is multiday.has_gpx(): the page
        # offers this file exactly when a day has a track, so it is written exactly then.
        trks, spaces = [], {}
        for d in t['days']:
            if d['track']:
                # newline='': a day file with Windows line endings keeps them, so each block is in the combined file
                # byte for byte (the site check compares them)
                with open(d['track'], encoding='utf-8', newline='') as fh:
                    text = fh.read()
                blocks = _TRK.findall(text)
                if blocks:
                    # a block may use a prefix its own file declares on <gpx ...> (a device's extensions): the
                    # combined root declares it too, or the download would not be well-formed XML
                    for prefix, uri in _XMLNS.findall(gpx_root_tag(text)):
                        spaces.setdefault(prefix, uri)
                trks += blocks
        declared = ''.join(' xmlns:%s=%s' % (p, spaces[p]) for p in sorted(spaces))
        combined = os.path.join(out, t['slug'] + '.gpx')
        if os.path.islink(combined):
            # a --link build has just linked this name to the trip's own track.gpx: writing through the link would
            # overwrite the content file
            os.remove(combined)
        with open(combined, 'w', encoding='utf-8', newline='') as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="Eric Sichak trip reports" '
                     'xmlns="http://www.topografix.com/GPX/1/1"%s>\n<metadata><name>%s</name></metadata>\n%s\n</gpx>\n'
                     % (declared, html.escape(t['title']), '\n'.join(trks)))


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def pub_moment(t):
    """An item's pubDate: published_at when index.md states it (the day the report went online; a date alone at 12:00
    UTC), else the trip date at 12:00 UTC, the rule from before reports carried publication dates; None undated."""
    if t.get('published_at'):
        return content.publication_utc(t['published_at'])
    d = t['date']
    return datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc) if d else None


def feed_content(t):
    """An item's <content:encoded> (seo-09), for a trip with a write-up of its own: the write-up as the page shows it, a
    multi-day trip's written days each under its 'Day N' heading with that day's photos, the trip's photos (their .sm
    copies, with their alt text) and links to the page and its GPX. Eric's own words and files only, verbatim."""
    url = core.SITE_URL + t['url']
    # a write-up's own links are written relative to its page ('../other-trip/'); a feed reader would resolve them
    # against feed.xml, so each href and src is made absolute against the page
    full = lambda h: re.sub(r'\b(href|src)="([^"]*)"', lambda m: '%s="%s"' % (m.group(1), html.escape(urljoin(url, html.unescape(m.group(2))))), h)  # noqa: E731
    img = lambda p: '<p><img src="%s" alt="%s"></p>' % (url + (p.get('sm') or p['file']), html.escape(p.get('alt') or ''))  # noqa: E731
    parts = [full(markdown.to_html(t['body_md'], heading_shift=1))] + [img(p) for p in t.get('photos') or []]
    if t['kind'] == 'multi-day':
        for d in t['days']:
            if d['body_md']:
                name = (d.get('title') or '').strip()
                parts.append('<h2>Day %d%s</h2>' % (d['n'], (': ' + html.escape(name)) if name else ''))
                parts.append(full(markdown.to_html(d['body_md'], heading_shift=2)))
                parts += [img(p) for p in d.get('photos') or []]
    gpx = (t['slug'] + '.gpx') if (t['track'] if t['kind'] == 'trip' else
                                   (t['kind'] == 'multi-day' and any(d['track'] for d in t['days']))) else ''
    parts.append('<p><a href="%s">Open the report</a>%s</p>'
                 % (url, (' · <a href="%s">Download GPX</a>' % (url + gpx)) if gpx else ''))
    return ''.join(parts)


def feed(trips):
    """RSS 2.0: each item is the factual summary (content fields only) followed by the start of Eric's write-up. A trip
    with days and no trip-level write-up gets the summary alone (a day's excerpt would read as the whole trip's). A trip
    with a write-up of its own also carries all of it, with its photos, as <content:encoded> (feed_content). The 30
    newest by pubDate (pub_moment), undated last; a stable sort, so trips without published_at keep the loader's
    trip-date order."""
    pub = [(pub_moment(x), x) for x in trips if x['kind'] != 'planned']
    pub.sort(key=lambda mt: (mt[0] is not None, mt[0] or _EPOCH), reverse=True)
    items = []
    for d, t in pub[:30]:
        url = core.SITE_URL + t['url']
        ex = core.excerpt(t, 400) if t['body_md'] else ''
        items.append('<item><title>%s</title><link>%s</link><guid>%s</guid>%s<category>%s</category><description>%s</description>%s</item>'
                     % (html.escape(t['title']), url, url, ('<pubDate>%s</pubDate>' % d.strftime('%a, %d %b %Y %H:%M:%S +0000')) if d else '',
                        html.escape(core.ACT[t['activity']][0]), html.escape(core.summary(t) + ((' ' + ex) if ex else '')),
                        ('<content:encoded>%s</content:encoded>' % html.escape(feed_content(t))) if t['body_md'] else ''))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
            'xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>'
            '<title>%s — trip reports</title><link>%s</link>'
            '<atom:link href="%sfeed.xml" rel="self" type="application/rss+xml"/>'
            '<description>%s</description><language>en-us</language>%s</channel></rss>\n'
            % (core.SITE_NAME, core.SITE_URL, core.SITE_URL, html.escape(core.SITE_TAGLINE), ''.join(items)))


def sitemap(pages, trips=()):
    """Every indexable page but the 404. A report whose index.md states updated_at, else published_at, gets that day as
    <lastmod> (W3C date or date-time, as written); no other page carries one, since the build knows no true date for it."""
    when = dict((t['url'], t.get('updated_at') or t.get('published_at')) for t in trips)
    urls = ''.join('<url><loc>%s%s</loc>%s</url>' % (core.SITE_URL, p.url,
                                                    ('<lastmod>%s</lastmod>' % html.escape(when[p.url])) if when.get(p.url) else '')
                   for p in pages if not p.url.endswith('404.html') and getattr(p, 'index', True))
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls


def site_of(trips):
    """The site dict the page modules read, from the loaded trips (newest first, drafts already left out by
    content.load_all). Raises content.ContentError when a goal's outing names something that is not a published report.
    build() adds 'featured' from content/home.json; the tests call this, so they exercise the same wiring."""
    site = {'trips': trips, 'by_slug': {t['slug']: t for t in trips},
            'published': [t for t in trips if t['kind'] != 'planned'], 'planned': [t for t in trips if t['kind'] == 'planned']}
    # tick-list goals: every non-draft planned trip (pages and assets for all of them); the active subset drives the
    # '+ N PLANNED ROUTE' counters; outings that name a report give that report a backlink
    site['goals'] = site['planned']
    site['active_goals'] = [t for t in site['planned'] if goals.is_active(t['goal'])]
    goals.validate_site(site)
    site['goal_backlinks'] = goals.backlinks(site)
    return site


def build(verbose=True, only=None):
    t0 = time.time()
    trips = content.load_all()
    site = site_of(trips)
    # the site meta as it is on disk now decides which regions have a page (the region module reads the same file)
    meta = core.read_site_meta()
    # content/home.json picks the home page's featured trips; an invalid manifest stops the build here, before any page
    site['featured'] = curation.featured_for(site)
    # its optional region_maps (the home page's two maps), checked against those region maps
    site['region_maps'] = curation.region_maps_for(meta)
    # Eric's own words, optional: content/about.md (the About page) and content/regions/<slug>.md (a region page's
    # introduction); read here, beside content/home.json, not in site_of, which the tests call on synthetic trips
    site['about'] = content.load_about()
    site['region_intros'] = content.load_region_intros()
    # how a reader reaches Eric: content/author.json, optional; an invalid file stops the build here (sitegen.author)
    site['author'] = author.load()
    core.register_site(site, meta)
    # the bundles before the pages, which name them with their hashes (perf-01); and the fonts are the site's own once
    # tools/fonts.py has written assets/css/fonts.css (perf-02)
    css, js = css_bundle(), js_bundle()
    core._ASSET_VERSION.update(css=asset_hash(css), js=asset_hash(js))
    core._SELF_FONTS[0] = os.path.exists(os.path.join(ROOT, 'assets', 'css', 'fonts.css'))
    try:
        return _build(trips, site, css, js, t0, verbose, only)
    finally:
        core._ASSET_VERSION.clear()
        core._SELF_FONTS[0] = False


def asset_hash(text):
    """The first 8 hex digits of the SHA-1 of a bundle: its version in the pages' addresses (assets/site.css?v=...)."""
    return hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]


def _build(trips, site, css, js, t0, verbose, only):
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    # GitHub Pages serves the folder as it is; written first, it also marks the folder as a build (unsafe_out), even
    # one that stopped half-way
    open(os.path.join(OUT, BUILD_MARK), 'w').close()
    pages = []
    for name in PAGE_MODULES:
        if only and name not in only:
            continue
        try:
            mod = importlib.import_module('sitegen.pages.' + name)
        except ModuleNotFoundError as ex:
            if ex.name == 'sitegen.pages.' + name:
                print('  (no page module %s yet)' % name)
                continue
            raise
        pages += mod.build(site)
    for p in pages:
        path = os.path.join(OUT, p.url, 'index.html') if (p.url == '' or p.url.endswith('/')) else os.path.join(OUT, p.url)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(p.html)
    os.makedirs(os.path.join(OUT, 'assets', 'maps'), exist_ok=True)
    with open(os.path.join(OUT, 'assets', 'site.css'), 'w', encoding='utf-8') as fh:
        fh.write(css)
    with open(os.path.join(OUT, 'assets', 'site.js'), 'w', encoding='utf-8') as fh:
        fh.write(js)
    # assets/*.* and the fonts' folder (the woff2 files and their licences, tools/fonts.py)
    for f in glob.glob(os.path.join(ROOT, 'assets', '*.*')) + glob.glob(os.path.join(ROOT, 'assets', 'fonts', '*.*')):
        if conflict_copy(f):
            continue
        copy(f, os.path.join(OUT, os.path.relpath(f, ROOT)))
    for f in glob.glob(os.path.join(ROOT, 'rendered', 'site', '*.png')) + glob.glob(os.path.join(ROOT, 'rendered', 'site', '*.webp')) + glob.glob(os.path.join(ROOT, 'rendered', 'site', '*.base.svg')):
        if not conflict_copy(f):
            copy(f, os.path.join(OUT, 'assets', 'maps', os.path.basename(f)))
    copy_part_drawings()
    for t in trips:
        copy_trip_assets(t)
    copy_about_assets(site.get('about'))
    with open(os.path.join(OUT, 'feed.xml'), 'w', encoding='utf-8') as fh:
        fh.write(feed(site['published']))
    with open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8') as fh:
        fh.write(sitemap(pages, site['published']))
    with open(os.path.join(OUT, 'robots.txt'), 'w') as fh:
        fh.write('User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n' % core.SITE_URL)
    if verbose:
        print('built %d pages, %d trips in %.1fs -> %s' % (len(pages), len(trips), time.time() - t0, os.path.relpath(OUT, ROOT)))
    return pages


CHECK_LINES = 40     # problems printed by --check; the summary line counts all of them
WARNING_LINES = 10   # content warnings printed by a build; tools/validate.py lists every one


def check(only_pages=False):
    """Check the built site (sitegen.sitecheck): links, images and anchors as before, and each page's metadata, the
    sitemap, the feed, the search indexes and the published GPX bytes. Prints the problems and returns their count."""
    problems = sitecheck.check(OUT, content.TRIPS_DIR)
    for line in problems[:CHECK_LINES]:
        print(line)
    if len(problems) > CHECK_LINES:
        print('... %d more' % (len(problems) - CHECK_LINES))
    print('link check: %s' % ('OK' if not problems else '%d problems' % len(problems)))
    return len(problems)


def content_errors():
    """Validate content/ (lib/checks.py) before the output folder is touched. Errors go to stderr, one ERROR line each,
    and their count is returned: the build stops. Warnings print (the first few) and the build goes on."""
    findings = checks.run()
    errs, warns = checks.errors(findings), checks.warnings(findings)
    for f in errs:
        print(checks.line(f), file=sys.stderr)
    if errs:
        return len(errs)
    for f in warns[:WARNING_LINES]:
        print(checks.line(f))
    if len(warns) > WARNING_LINES:
        print('... %d more; python3 tools/validate.py lists them' % (len(warns) - WARNING_LINES))
    return 0


BUILD_MARK = '.nojekyll'
_SOURCE_FOLDERS = ('content', 'rendered', 'assets', 'tools', 'tests', 'docs', '.git', '.github')


def unsafe_out(path):
    """Why `path` must not be the output folder, or None. A build empties its output folder before it writes, so --out
    may not name this checkout, a folder that holds it, or anything inside its source folders; and a folder that is
    already there must be empty or an earlier build (every build leaves a .nojekyll file in it)."""
    real, root = os.path.realpath(path), os.path.realpath(ROOT)
    if real == root or root.startswith(real.rstrip(os.sep) + os.sep):
        return 'it is, or holds, this checkout'
    for name in _SOURCE_FOLDERS:
        # by where the source folder really is: one that is a link out of the checkout is still a source folder
        src = os.path.realpath(os.path.join(ROOT, name))
        if real == src or real.startswith(src + os.sep):
            return 'it is inside %s/ of this checkout' % name
    if os.path.exists(real) and not os.path.isdir(real):
        return 'it is a file'
    if os.path.isdir(real) and os.listdir(real) and not os.path.exists(os.path.join(real, BUILD_MARK)):
        return 'it is not empty and is not an earlier build (it has no %s file)' % BUILD_MARK
    return None


# what --watch looks at: the sources a page is made from, and only the shared maps of rendered/ (a trip's own renders
# are thousands of files, about half of them offloaded by iCloud Drive; stat() leaves an offloaded file where it is)
WATCH_DIRS = ('content', 'assets', os.path.join('tools', 'sitegen'), os.path.join('tools', 'lib'), os.path.join('rendered', 'site'))
WATCH_EVERY = 1.0    # seconds between two looks


def watch_state(root=None):
    """{path: (mtime_ns, size)} of every file --watch looks at, conflict copies left out. A trip's photos/ folder counts as
    one entry, its own mtime, which changes when a photo is added, removed or renamed: its hundreds of image files are
    not looked at one by one."""
    root = root or ROOT
    state = {}
    for d in WATCH_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, d)):
            # __pycache__: the child build writes bytecode there, which is no change to the site
            dirnames[:] = sorted(n for n in dirnames if not n.startswith('.') and n != '__pycache__' and not sitecheck.conflict_copy(n))
            if os.path.basename(dirpath) == 'photos':
                try:
                    st = os.stat(dirpath)
                    state[dirpath] = (st.st_mtime_ns, 0)
                except OSError:
                    pass
                dirnames[:] = []
                continue
            for n in filenames:
                if n.startswith('.') or n.endswith('.pyc') or sitecheck.conflict_copy(n):
                    continue
                p = os.path.join(dirpath, n)
                try:
                    st = os.stat(p)
                except OSError:
                    continue          # gone between the listing and the look
                state[p] = (st.st_mtime_ns, st.st_size)
    return state


def changed(before, after):
    """The paths that are new, gone or different between two watch_state() answers, sorted."""
    return sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))


def rebuild(link, why='', only=None):
    """One rebuild for --watch, in a child process: it reads the content again and also the page modules and helpers
    in tools/, which this process imported once and would keep as they were. Prints one line, or the ERROR lines of a
    content mistake; returns True when the build went through. The child empties the output folder first (build()), so
    a page reloaded during the two seconds of a rebuild can be a 404: reload again."""
    import subprocess
    cmd = [sys.executable, os.path.abspath(__file__), '--out', OUT] + (['--link'] if link else []) + \
        (['--only', ','.join(sorted(only))] if only else [])
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print('rebuilt in %.1fs%s' % (time.time() - t0, (': ' + why) if why else ''), flush=True)
        return True
    errs = [ln for ln in r.stderr.splitlines() if ln.startswith('ERROR')]
    for ln in errs or r.stderr.strip().splitlines()[-5:]:
        print(ln, flush=True)
    print('not rebuilt%s: %s; still serving (fix the file and save it again)'
          % ((' (%s)' % why) if why else '',
             'the content check stopped it, and the preview is the last good build' if errs else 'the build stopped'), flush=True)
    return False


def watch(link, every=WATCH_EVERY, stop=None, state=None, only=None):
    """--watch: look every `every` seconds, rebuild when something changed. stop: a threading.Event that ends the loop
    (the tests'); the server's thread is a daemon, so Ctrl+C ends it with the process."""
    before = watch_state() if state is None else state
    while not (stop and stop.is_set()):
        time.sleep(every)
        now = watch_state()
        diff = changed(before, now)
        if diff:
            rebuild(link, '%s changed%s' % (os.path.relpath(diff[0], ROOT), (' (and %d more)' % (len(diff) - 1)) if len(diff) > 1 else ''), only)
        # the look from before the rebuild stays the baseline: a file saved while the child was building differs from
        # it at the next look, and is built then
        before = now


def page_url(port, slug):
    """The address --open opens: the home page, or trips/<slug>/ (a report, a journal or a goal page)."""
    return 'http://localhost:%d/%s' % (port, ('trips/%s/' % slug) if slug else '')


def open_in_browser(url):
    """macOS `open`; elsewhere (or without it) the address is only printed."""
    import subprocess
    try:
        subprocess.Popen(['open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def serve(port, open_slug=None, watch_link=None, server_class=None, only=None):
    """Serve OUT on 127.0.0.1:<port> until Ctrl+C, which ends it quietly. open_slug: None, or '' for the home page, or a
    slug, opened once the server is listening. watch_link: None for no --watch, else whether rebuilds link."""
    import functools
    import http.server
    import threading
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=OUT)
    server = (server_class or http.server.ThreadingHTTPServer)(('127.0.0.1', port), handler)
    print('serving http://localhost:%d  (Ctrl+C to stop)' % port, flush=True)
    if open_slug is not None:
        if open_slug and not os.path.exists(os.path.join(OUT, 'trips', open_slug, 'index.html')):
            print('  no page trips/%s/ in this build (a draft, or a misspelt folder name): opening the home page' % open_slug)
            open_slug = ''
        url = page_url(port, open_slug)
        print('  opening %s' % url, flush=True)
        open_in_browser(url)
    if watch_link is not None:
        print('  watching content/, assets/, tools/ and rendered/site/: a saved change rebuilds the site', flush=True)
        threading.Thread(target=watch, args=(watch_link,), kwargs={'only': only}, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nstopped')
    finally:
        server.server_close()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--serve', action='store_true', help='serve the build on http://localhost:<port>; links photos, maps and '
                                                         'GPX instead of copying them (--copy to copy)')
    ap.add_argument('--open', nargs='?', const='', metavar='SLUG', help='with --serve: open the home page, or trips/SLUG/, '
                                                                        'in the browser once the server is up')
    ap.add_argument('--watch', action='store_true', help='with --serve: rebuild whenever a file under content/, assets/, '
                                                         'tools/sitegen/, tools/lib/ or rendered/site/ changes')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--out', help='output folder (default _site/)')
    ap.add_argument('--only', help='comma-separated page modules to build (default: all)')
    ap.add_argument('--link', action='store_true', help='symlink photos/maps/GPX instead of copying (dev builds)')
    ap.add_argument('--copy', action='store_true', help='with --serve: copy photos, maps and GPX as the published build does')
    a = ap.parse_args(argv)
    if (a.open is not None or a.watch) and not a.serve:
        ap.error('--open and --watch go with --serve')
    if a.copy and a.link:
        ap.error('--copy and --link are opposites; give one')
    only = None
    if a.only is not None:
        only = {n.strip() for n in a.only.split(',') if n.strip()}
        unknown = sorted(only - set(PAGE_MODULES))
        if unknown or not only:
            # a misspelt module used to build nothing and say so nowhere
            ap.error('--only takes page modules (%s), got %s' % (', '.join(PAGE_MODULES), ', '.join(unknown) or 'none'))
    global OUT, LINK
    if a.out:
        why = unsafe_out(a.out)
        if why:
            ap.error('--out %s: a build empties its output folder first, and %s' % (a.out, why))
        OUT = os.path.abspath(a.out)
    # a preview links photos, maps and GPX into the output folder (about 3 s) instead of copying 240 MB of them, which
    # stalls for minutes when iCloud Drive has offloaded half of rendered/; CI's build (plain --check) always copies
    LINK = a.link or (a.serve and not a.copy)
    if content_errors():
        return 1
    try:
        build(only=only)
    except (curation.CurationError, content.ContentError) as ex:
        # a content or curation mistake: the message names the file and field, so no traceback
        print('ERROR %s' % ex, file=sys.stderr)
        return 1
    if a.check and check():
        return 1
    if a.serve:
        return serve(a.port, a.open, LINK if a.watch else None, only=only)
    return 0


if __name__ == '__main__':
    sys.exit(main())
