#!/usr/bin/env python3
"""Make the site's three typefaces its own files (perf-02): run once on the Mac, with the internet and Eric's go-ahead.

  python3 tools/fonts.py           # download into assets/fonts/ and write assets/css/fonts.css
  python3 tools/fonts.py --check   # offline: does fonts.css hold exactly the faces of FACES, each file in assets/fonts/?

It asks Google Fonts for the stylesheet core.FONTS names (as a current browser would, so the answer is woff2), keeps
the Latin file of each face the Alpine design uses (Phase 16: Instrument Serif roman and italic, Inter as one variable
file for 400 to 600, IBM Plex Mono 400 and 500), saves them under fixed names (core.FONT_PRELOADS names three of them)
with the three SIL Open Font License texts beside them, and writes assets/css/fonts.css: one @font-face per face with
Google's own ranges and unicode-range, font-display: swap, and the address of the copy (bundled into assets/site.css,
so 'fonts/<file>'). Nothing is written unless every file arrived. From the next build on, build.py puts fonts.css first
in the bundle and copies assets/fonts/, and every page preloads the faces core.FONT_PRELOADS names instead of loading
Google's stylesheet. To go back, delete assets/css/fonts.css (and assets/fonts/).
"""
import argparse
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from sitegen import core  # noqa: E402

# (family as Google names it, font-style, font-weight as Google's block states it, the file it is saved as, its
# licence's file name). Inter is asked for as a range (core.FONTS: wght@400..600), so Google answers with one block and
# one variable file; IBM Plex Mono has no variable file, so its two weights are two blocks and two files
FACES = [('Instrument Serif', 'normal', '400', 'instrument-serif-latin.woff2', 'OFL-instrument-serif.txt'),
         ('Instrument Serif', 'italic', '400', 'instrument-serif-italic-latin.woff2', 'OFL-instrument-serif.txt'),
         ('Inter', 'normal', '400 600', 'inter-latin.woff2', 'OFL-inter.txt'),
         ('IBM Plex Mono', 'normal', '400', 'ibm-plex-mono-400-latin.woff2', 'OFL-ibm-plex-mono.txt'),
         ('IBM Plex Mono', 'normal', '500', 'ibm-plex-mono-500-latin.woff2', 'OFL-ibm-plex-mono.txt')]
# the licence of each family, from the repository Google Fonts publishes them from
LICENSES = {'OFL-instrument-serif.txt': 'https://raw.githubusercontent.com/google/fonts/main/ofl/instrumentserif/OFL.txt',
            'OFL-inter.txt': 'https://raw.githubusercontent.com/google/fonts/main/ofl/inter/OFL.txt',
            'OFL-ibm-plex-mono.txt': 'https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexmono/OFL.txt'}
# Google answers with woff2 only to a browser it knows
AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
         'Chrome/124.0.0.0 Safari/537.36')
FONTS_DIR = os.path.join('assets', 'fonts')
FONTS_CSS = os.path.join('assets', 'css', 'fonts.css')
_BLOCK = re.compile(r'/\*\s*([\w-]+)\s*\*/\s*@font-face\s*\{([^}]*)\}')
_DECL = re.compile(r'([\w-]+)\s*:\s*([^;]+);')
_SRC = re.compile(r'url\(([^)]+)\)')


FONT_HOST = 'https://fonts.gstatic.com/'      # where Google's stylesheet keeps the files; nothing else is fetched
MAX_BYTES = 2 * 1024 * 1024                    # far above any of the five files (Inter's, the largest, is under 0.5 MB)


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('%s is over %d bytes' % (url, MAX_BYTES))
    return data


def faces(css):
    """Google's stylesheet as [(subset, {descriptor: value})], one per '/* <subset> */ @font-face {...}' block."""
    return [(m.group(1), {k: v.strip() for k, v in _DECL.findall(m.group(2))}) for m in _BLOCK.finditer(css)]


def latin(css):
    """The Latin block of each face in FACES, in that order: {file: descriptors}. Raises when one is missing."""
    out = {}
    for family, style, weight, name, _lic in FACES:
        hit = [d for sub, d in faces(css) if sub == 'latin' and d.get('font-family', '').strip('\'"') == family
               and d.get('font-style', 'normal') == style and d.get('font-weight', '400') == weight]
        if len(hit) != 1:
            raise ValueError('%d Latin blocks for %s %s %s in the stylesheet (expected 1)' % (len(hit), family, style, weight))
        out[name] = hit[0]
    return out


def font_css(blocks):
    """assets/css/fonts.css: one @font-face per face, Google's descriptors kept, the copy's address, swap."""
    out = ['/* The site\'s own fonts (perf-02), written by tools/fonts.py: the Latin files of Google Fonts, under the SIL\n'
           '   Open Font License (assets/fonts/OFL-*.txt). build.py bundles this sheet first into assets/site.css. */']
    for name, d in blocks.items():
        lines = ['  font-family: %s;' % d['font-family']]
        for key in ('font-style', 'font-weight', 'font-stretch'):
            if key in d:
                lines.append('  %s: %s;' % (key, d[key]))
        lines.append('  font-display: swap;')
        lines.append('  src: url("fonts/%s") format("woff2");' % name)
        if 'unicode-range' in d:
            lines.append('  unicode-range: %s;' % d['unicode-range'])
        out.append('@font-face {\n%s\n}' % '\n'.join(lines))
    return '\n'.join(out) + '\n'


def check(root):
    """Problems with fonts.css as it is: a face whose file is not in assets/fonts/, a licence that is missing."""
    path = os.path.join(root, FONTS_CSS)
    if not os.path.exists(path):
        return ['%s does not exist: the pages load Google Fonts' % FONTS_CSS]
    with open(path, encoding='utf-8') as fh:
        css = fh.read()
    names = [u.strip('\'"') for u in _SRC.findall(css)]
    found = [] if names else ['%s names no font file' % FONTS_CSS]
    for u in names:
        if not u.startswith('fonts/') or not os.path.isfile(os.path.join(root, 'assets', u)):
            found.append('%s names %s, which is not in %s' % (FONTS_CSS, u, FONTS_DIR))
    # a fonts.css written for another design (FACES changed since it ran): the pages would wear the old faces
    want = sorted('fonts/' + f[3] for f in FACES)
    if names and sorted(names) != want:
        found.append('%s names other faces than FACES (%s): run python3 tools/fonts.py' % (FONTS_CSS, ', '.join(f[3] for f in FACES)))
    for lic in sorted(set(f[4] for f in FACES)):
        if not os.path.isfile(os.path.join(root, FONTS_DIR, lic)):
            found.append('%s is missing from %s' % (lic, FONTS_DIR))
    return found


def download(root, get=fetch):
    """Fetch the stylesheet, the five files and the three licences; write them only once all of them arrived."""
    blocks = latin(get(core.FONTS).decode('utf-8'))
    files = {}
    for name, d in blocks.items():
        url = _SRC.search(d['src']).group(1).strip('\'"')
        if not url.startswith(FONT_HOST):
            raise ValueError('%s is not on %s: %s' % (name, FONT_HOST, url))
        files[name] = get(url)
        if files[name][:4] != b'wOF2':
            raise ValueError('%s is not a woff2 file (%s)' % (name, url))
    for lic, url in LICENSES.items():
        files[lic] = get(url)
    os.makedirs(os.path.join(root, FONTS_DIR), exist_ok=True)
    for name, data in files.items():
        with open(os.path.join(root, FONTS_DIR, name), 'wb') as fh:
            fh.write(data)
    with open(os.path.join(root, FONTS_CSS), 'w', encoding='utf-8') as fh:
        fh.write(font_css(blocks))
    return files


def main(argv=None, root=None, get=fetch):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true', help='only check fonts.css against assets/fonts/ (offline)')
    a = ap.parse_args(argv)
    root = root or ROOT
    if not a.check:
        files = download(root, get)
        for name in sorted(files):
            print('%8d B  %s' % (len(files[name]), os.path.join(FONTS_DIR, name)))
        print('wrote %s' % FONTS_CSS)
    problems = check(root)
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
