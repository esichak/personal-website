#!/usr/bin/env python3
"""Build the static site into _site/ (stdlib only; this is what the GitHub Action runs).

  python3 tools/build.py            # build
  python3 tools/build.py --serve    # build, then serve http://localhost:8000
  python3 tools/build.py --check    # build, then check the built site: links, images, anchors, metadata, feed, GPX
  python3 tools/build.py --out DIR --only report,home --link   # fast dev build of some page modules
"""
import argparse
import glob
import html
import importlib
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import mapkit  # noqa: E402
from sitegen import core  # noqa: E402
from sitegen import curation  # noqa: E402
from sitegen import sitecheck  # noqa: E402
import checks  # noqa: E402
import goals  # noqa: E402

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
    parts = [_text(os.path.join(ROOT, 'assets', 'css', 'base.css'))]
    parts.append('/* map + profile internals (from tools/lib/mapkit.py) */\n' + mapkit.MAP_CSS.strip()
                 .replace("'Geist Mono', ui-monospace, 'SF Mono', monospace", 'var(--mono)')
                 .replace("Archivo, 'Helvetica Neue', system-ui, sans-serif", 'var(--sans)')
                 .replace("'Source Serif 4', Georgia, serif", 'var(--serif)'))
    for f in sorted(glob.glob(os.path.join(ROOT, 'assets', 'css', 'pages', '*.css'))):
        if conflict_copy(f):   # 'trips 2.css': its rules would be in the bundle twice
            continue
        parts.append('/* %s */\n' % os.path.basename(f) + _text(f))
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


def feed(trips):
    """RSS 2.0: each item is the factual summary (content fields only) followed by the start of Eric's write-up. A trip
    with days and no trip-level write-up gets the summary alone (a day's excerpt would read as the whole trip's)."""
    items = []
    for t in [x for x in trips if x['kind'] != 'planned'][:30]:
        url = core.SITE_URL + t['url']
        d = datetime(t['date'].year, t['date'].month, t['date'].day, 12, tzinfo=timezone.utc) if t['date'] else None
        ex = core.excerpt(t, 400) if t['body_md'] else ''
        items.append('<item><title>%s</title><link>%s</link><guid>%s</guid>%s<category>%s</category><description>%s</description></item>'
                     % (html.escape(t['title']), url, url, ('<pubDate>%s</pubDate>' % d.strftime('%a, %d %b %Y %H:%M:%S +0000')) if d else '',
                        html.escape(core.ACT[t['activity']][0]), html.escape(core.summary(t) + ((' ' + ex) if ex else ''))))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
            '<title>%s — trip reports</title><link>%s</link>'
            '<atom:link href="%sfeed.xml" rel="self" type="application/rss+xml"/>'
            '<description>%s</description><language>en-us</language>%s</channel></rss>\n'
            % (core.SITE_NAME, core.SITE_URL, core.SITE_URL, html.escape(core.SITE_TAGLINE), ''.join(items)))


def sitemap(pages):
    urls = ''.join('<url><loc>%s%s</loc></url>' % (core.SITE_URL, p.url) for p in pages
                   if not p.url.endswith('404.html') and getattr(p, 'index', True))
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
    # content/home.json picks the home page's featured trips; an invalid manifest stops the build here, before any page
    site['featured'] = curation.featured_for(site)
    # the site meta as it is on disk now decides which regions have a page (the region module reads the same file)
    core.register_site(site, core.read_site_meta())
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
        fh.write(css_bundle())
    with open(os.path.join(OUT, 'assets', 'site.js'), 'w', encoding='utf-8') as fh:
        fh.write(js_bundle())
    for f in glob.glob(os.path.join(ROOT, 'assets', '*.*')):
        if conflict_copy(f):
            continue
        copy(f, os.path.join(OUT, 'assets', os.path.basename(f)))
    for f in glob.glob(os.path.join(ROOT, 'rendered', 'site', '*.png')) + glob.glob(os.path.join(ROOT, 'rendered', 'site', '*.webp')) + glob.glob(os.path.join(ROOT, 'rendered', 'site', '*.base.svg')):
        if not conflict_copy(f):
            copy(f, os.path.join(OUT, 'assets', 'maps', os.path.basename(f)))
    for t in trips:
        copy_trip_assets(t)
    with open(os.path.join(OUT, 'feed.xml'), 'w', encoding='utf-8') as fh:
        fh.write(feed(site['published']))
    with open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8') as fh:
        fh.write(sitemap(pages))
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--serve', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--out', help='output folder (default _site/)')
    ap.add_argument('--only', help='comma-separated page modules to build (default: all)')
    ap.add_argument('--link', action='store_true', help='symlink photos/maps/GPX instead of copying (dev builds)')
    a = ap.parse_args(argv)
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
    LINK = a.link
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
        import functools
        import http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=OUT)
        print('serving http://localhost:%d  (Ctrl+C to stop)' % a.port)
        http.server.ThreadingHTTPServer(('127.0.0.1', a.port), handler).serve_forever()
    return 0


if __name__ == '__main__':
    sys.exit(main())
