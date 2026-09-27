#!/usr/bin/env python3
"""Build the static site into _site/ (stdlib only; this is what the GitHub Action runs).

  python3 tools/build.py            # build
  python3 tools/build.py --serve    # build, then serve http://localhost:8000
  python3 tools/build.py --check    # build, then verify every internal link and image resolves
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

OUT = os.path.join(ROOT, '_site')
PAGE_MODULES = ['home', 'section', 'report', 'multiday', 'series', 'archive', 'about', 'notfound']


def css_bundle():
    parts = [open(os.path.join(ROOT, 'assets', 'css', 'base.css'), encoding='utf-8').read()]
    parts.append('/* map + profile internals (from tools/lib/mapkit.py) */\n' + mapkit.MAP_CSS.strip()
                 .replace("'Geist Mono', ui-monospace, 'SF Mono', monospace", 'var(--mono)')
                 .replace("Archivo, 'Helvetica Neue', system-ui, sans-serif", 'var(--sans)')
                 .replace("'Source Serif 4', Georgia, serif", 'var(--serif)'))
    for f in sorted(glob.glob(os.path.join(ROOT, 'assets', 'css', 'pages', '*.css'))):
        parts.append('/* %s */\n' % os.path.basename(f) + open(f, encoding='utf-8').read())
    return '\n'.join(parts)


def js_bundle():
    parts = [open(os.path.join(ROOT, 'assets', 'js', 'base.js'), encoding='utf-8').read()]
    for f in sorted(glob.glob(os.path.join(ROOT, 'assets', 'js', 'pages', '*.js'))):
        parts.append('/* %s */\n' % os.path.basename(f) + open(f, encoding='utf-8').read())
    return '\n'.join(parts)


LINK = False


def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if LINK:
        if not os.path.lexists(dst):
            os.symlink(os.path.abspath(src), dst)
    else:
        shutil.copy2(src, dst)


def copy_trip_assets(t):
    out = os.path.join(OUT, 'trips', t['slug'])
    for p in glob.glob(os.path.join(t['dir'], 'photos', '*')):
        copy(p, os.path.join(out, 'photos', os.path.basename(p)))
    for p in glob.glob(os.path.join(t['rendered'], '*.png')) + glob.glob(os.path.join(t['rendered'], '*.webp')):
        copy(p, os.path.join(out, 'map', os.path.basename(p)))
    if t['track']:
        copy(t['track'], os.path.join(out, t['slug'] + '.gpx'))
    for d in t['days']:
        if d['track']:
            copy(d['track'], os.path.join(out, 'gpx', '%s-day-%s.gpx' % (t['slug'], d['id'])))
    if t['kind'] == 'multi-day' and t['days']:
        # one GPX with a <trk> per day, for the "Download all GPX" action
        trks = []
        for d in t['days']:
            if d['track']:
                trks += re.findall(r'<trk>.*?</trk>', open(d['track'], encoding='utf-8').read(), flags=re.S)
        with open(os.path.join(out, t['slug'] + '.gpx'), 'w', encoding='utf-8') as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="Eric Sichak trip reports" '
                     'xmlns="http://www.topografix.com/GPX/1/1">\n<metadata><name>%s</name></metadata>\n%s\n</gpx>\n'
                     % (html.escape(t['title']), '\n'.join(trks)))


def feed(trips):
    items = []
    for t in [x for x in trips if x['kind'] != 'planned'][:30]:
        url = core.SITE_URL + t['url']
        d = datetime(t['date'].year, t['date'].month, t['date'].day, 12, tzinfo=timezone.utc) if t['date'] else None
        items.append('<item><title>%s</title><link>%s</link><guid>%s</guid>%s<description>%s</description></item>'
                     % (html.escape(t['title']), url, url, ('<pubDate>%s</pubDate>' % d.strftime('%a, %d %b %Y %H:%M:%S +0000')) if d else '',
                        html.escape(core.excerpt(t, 400))))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>%s — trip reports</title><link>%s</link>'
            '<description>%s</description><language>en-us</language>%s</channel></rss>\n'
            % (core.SITE_NAME, core.SITE_URL, html.escape(core.SITE_TAGLINE), ''.join(items)))


def sitemap(pages):
    urls = ''.join('<url><loc>%s%s</loc></url>' % (core.SITE_URL, p.url) for p in pages if not p.url.endswith('404.html'))
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls


def build(verbose=True, only=None):
    t0 = time.time()
    trips = content.load_all()
    site = {'trips': trips, 'by_slug': {t['slug']: t for t in trips},
            'published': [t for t in trips if t['kind'] != 'planned'], 'planned': [t for t in trips if t['kind'] == 'planned']}
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
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
        copy(f, os.path.join(OUT, 'assets', os.path.basename(f)))
    for f in glob.glob(os.path.join(ROOT, 'rendered', 'site', '*.png')) + glob.glob(os.path.join(ROOT, 'rendered', 'site', '*.webp')):
        copy(f, os.path.join(OUT, 'assets', 'maps', os.path.basename(f)))
    for t in trips:
        copy_trip_assets(t)
    with open(os.path.join(OUT, 'feed.xml'), 'w', encoding='utf-8') as fh:
        fh.write(feed(site['published']))
    with open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8') as fh:
        fh.write(sitemap(pages))
    with open(os.path.join(OUT, 'robots.txt'), 'w') as fh:
        fh.write('User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n' % core.SITE_URL)
    open(os.path.join(OUT, '.nojekyll'), 'w').close()
    if verbose:
        print('built %d pages, %d trips in %.1fs -> %s' % (len(pages), len(trips), time.time() - t0, os.path.relpath(OUT, ROOT)))
    return pages


_REF = re.compile(r'''(?:href|src|srcset)="([^"]+)"''')


def check(only_pages=False):
    bad = 0
    for f in glob.glob(os.path.join(OUT, '**', '*.html'), recursive=True):
        s = open(f, encoding='utf-8').read()
        here = os.path.dirname(f)
        for ref in _REF.findall(s):
            for u in [x.strip().split(' ')[0] for x in ref.split(',')] if ' ' in ref else [ref]:
                if not u or u.startswith(('http:', 'https:', 'mailto:', '#', 'data:', 'javascript:')):
                    continue
                path = u.split('#')[0].split('?')[0]
                if not path:
                    continue
                target = os.path.normpath(os.path.join(here, path))
                if os.path.isdir(target):
                    target = os.path.join(target, 'index.html')
                if not os.path.exists(target):
                    bad += 1
                    if bad <= 40:
                        print('BROKEN %s -> %s' % (os.path.relpath(f, OUT), u))
        ids = set(re.findall(r'\bid="([^"]+)"', s))
        for frag_ in re.findall(r'href="#([^"]+)"', s):
            if frag_ not in ids:
                bad += 1
                if bad <= 40:
                    print('BROKEN ANCHOR %s -> #%s' % (os.path.relpath(f, OUT), frag_))
        dup = [i for i in ids if len(re.findall(r'\bid="%s"' % re.escape(i), s)) > 1]
        if dup:
            bad += 1
            print('DUPLICATE IDS %s: %s' % (os.path.relpath(f, OUT), ', '.join(sorted(dup)[:6])))
    print('link check: %s' % ('OK' if not bad else '%d problems' % bad))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--serve', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--out', help='output folder (default _site/)')
    ap.add_argument('--only', help='comma-separated page modules to build (default: all)')
    ap.add_argument('--link', action='store_true', help='symlink photos/maps/GPX instead of copying (dev builds)')
    a = ap.parse_args()
    global OUT, LINK
    if a.out:
        OUT = os.path.abspath(a.out)
    LINK = a.link
    build(only=set(a.only.split(',')) if a.only else None)
    if a.check and check():
        sys.exit(1)
    if a.serve:
        import functools
        import http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=OUT)
        print('serving http://localhost:%d  (Ctrl+C to stop)' % a.port)
        http.server.ThreadingHTTPServer(('127.0.0.1', a.port), handler).serve_forever()


if __name__ == '__main__':
    main()
