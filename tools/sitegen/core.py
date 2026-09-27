"""Shared building blocks for every page: layout, header/footer, units, chips, maps, profiles, photos, rows.

Pages live in tools/sitegen/pages/*.py; each exposes build(site) -> list of Page. CSS for components here lives in
assets/css/base.css; page-specific CSS in assets/css/pages/<module>.css (concatenated by tools/build.py).
All links are relative, so the site works at https://esichak.github.io/personal-website/ and on any domain.
"""
import html
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import icons  # noqa: E402
import markdown  # noqa: E402

FT, MI = content.FT, content.MI
ACT = content.ACTIVITIES  # key -> (label, short, code, colour, folder)
SITE_NAME = 'Eric Sichak'
SITE_TAGLINE = 'Trip reports: backcountry skiing, climbing, hiking, mountain biking and more, each with a GPX map.'
SITE_URL = 'https://esichak.github.io/personal-website/'
HOME_COORDS = '39.09°N 120.04°W · LAKE TAHOE'
FONTS = ('https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100..112,400..700'
         '&family=Source+Serif+4:ital,opsz,wght@0,8..60,400..600;1,8..60,400&family=Geist+Mono:wght@400..600&display=swap')
SUB_ICON = {'SUP': 'SUP', 'Rafting': 'RFT', 'Kayaking': 'KYK', 'Mountaineering': 'MTN'}
SUB_WORD = {'SUP': 'Paddleboarding', 'Rafting': 'Rafting', 'Kayaking': 'Kayaking', 'Mountaineering': 'Mountaineering'}
NAV = [('ski', 'Backcountry Ski'), ('climb', 'Climbing'), ('hike', 'Hiking'), ('mtb', 'Mountain Biking'), ('other', 'Other')]

esc = html.escape


# ---------------------------------------------------------------- pages & urls

class Page:
    def __init__(self, url, html_, title=''):
        self.url = url  # '' for home, 'ski/', 'trips/slug/', '404.html'
        self.html = html_
        self.title = title


def section_url(act):
    return ACT[act][4] + '/'


def prefix(url):
    """Relative prefix from a page URL back to the site root."""
    if url.endswith('.html'):
        url = os.path.dirname(url)
        url = url + '/' if url else ''
    depth = url.count('/')
    return '../' * depth if depth else './'


def link(here, target):
    p = prefix(here)
    return (p if p != './' else '') + target if target else p


# ---------------------------------------------------------------- formatting

def fdate(d, style='long'):
    """long 'Sat, Jan 17, 2026' · short 'Jan 17, 2026' · caps 'SAT, JAN 17, 2026' · day 'Sat, Jan 17' · month 'Jan 2026'."""
    if not d:
        return ''
    if style == 'short':
        return '%s %d, %d' % (d.strftime('%b'), d.day, d.year)
    if style == 'day':
        return '%s, %s %d' % (d.strftime('%a'), d.strftime('%b'), d.day)
    if style == 'month':
        return d.strftime('%b %Y')
    s = '%s, %s %d, %d' % (d.strftime('%a'), d.strftime('%b'), d.day, d.year)
    return s.upper() if style == 'caps' else s


def frange(a, b, caps=False):
    """'Mar 10–15, 2024' / 'Apr 22 – Sep 21, 2024' / across years."""
    if not a:
        return ''
    if not b or a == b:
        s = fdate(a, 'short')
    elif a.year == b.year and a.month == b.month:
        s = '%s %d–%d, %d' % (a.strftime('%b'), a.day, b.day, a.year)
    elif a.year == b.year:
        s = '%s %d – %s %d, %d' % (a.strftime('%b'), a.day, b.strftime('%b'), b.day, a.year)
    else:
        s = '%s – %s' % (fdate(a, 'short'), fdate(b, 'short'))
    return s.upper() if caps else s


def ftime(hhmm):
    """'06:30' -> '6:30 AM'."""
    if not hhmm:
        return ''
    h, m = [int(x) for x in str(hhmm).split(':')[:2]]
    return '%d:%02d %s' % ((h % 12) or 12, m, 'AM' if h < 12 else 'PM')


def n(v, dp=0):
    if v is None:
        return ''
    return '{:,.{p}f}'.format(v, p=dp) if dp else '{:,}'.format(int(round(v)))


def dist_vals(km):
    if km is None:
        return None, None
    mi = km * 1000 / MI
    return (('%.1f' % mi) if mi < 100 else n(mi)), (('%.1f' % km) if km < 100 else n(km))


def U(imp, met, imp_unit='', met_unit='', cls=''):
    """A value shown in miles/feet by default and in km/m when <html class="km">. Units are separate spans."""
    def one(v, unit, which):
        u = (unit if '<span' in unit else '<span class="unit">%s</span>' % unit) if unit else ''
        return '<span class="u-%s">%s%s</span>' % (which, v, u)
    return '<span class="u%s">%s%s</span>' % ((' ' + cls) if cls else '', one(imp, imp_unit, 'mi'), one(met, met_unit, 'km'))


def U_sub(imp, met, imp_unit='', met_unit=''):
    """The *other* unit, for the small secondary line under a value."""
    return ('<span class="u"><span class="u-mi">%s%s</span><span class="u-km">%s%s</span></span>'
            % (met, (' ' + met_unit) if met_unit else '', imp, (' ' + imp_unit) if imp_unit else ''))


def distance(km, units=True):
    mi, k = dist_vals(km)
    if mi is None:
        return ''
    return U(mi, k, ' mi' if units else '', ' km' if units else '')


def elev(m, units=True):
    if m is None:
        return ''
    return U(n(m * FT), n(m), ' ft' if units else '', ' m' if units else '')


def nb(text):
    """Keep one meta item on one line: lines may only break at the ' · ' / ', ' separators."""
    return text.replace(' ', '\u00a0')


def plain_stats(t):
    """Short Mono-S caps line: '12.8 MI · 5,302 FT GAIN' (switches with units)."""
    st = t['stats']
    parts = []
    mi, km = dist_vals(st.get('distance_km'))
    if mi:
        parts.append(U(nb(mi + ' MI'), nb(km + ' KM')))
    if st.get('gain_m') is not None and st.get('gain_m') > 30:
        parts.append(U(nb(n(st['gain_m'] * FT) + ' FT GAIN'), nb(n(st['gain_m']) + ' M GAIN')))
    return ' · '.join(parts)


def hm(sec):
    if not sec:
        return ''
    h, m = int(sec // 3600), int(round((sec % 3600) / 60.0))
    if m == 60:
        h, m = h + 1, 0
    return '%d:%02d' % (h, m)


# ---------------------------------------------------------------- small components

def icon(name, size=24, cls=''):
    return icons.icon(name, size).replace('<svg ', '<svg class="ic%s" ' % ((' ' + cls) if cls else ''), 1)


def act_icon(t_or_act, sub=None):
    act = t_or_act['activity'] if isinstance(t_or_act, dict) else t_or_act
    sub = sub if sub is not None else (t_or_act.get('subtype') if isinstance(t_or_act, dict) else None)
    return SUB_ICON.get(sub) or ACT[act][2]


def act_word(t_or_act, sub=None):
    act = t_or_act['activity'] if isinstance(t_or_act, dict) else t_or_act
    sub = sub if sub is not None else (t_or_act.get('subtype') if isinstance(t_or_act, dict) else None)
    return SUB_WORD.get(sub, sub) if (act == 'other' and sub) else ACT[act][0]


def chip(t_or_act, href=None, variant='title', swatch=True, sub=None):
    """Activity marker. variant 'title' = 28px bordered chip; 'inline' = icon + word (+ swatch)."""
    act = t_or_act['activity'] if isinstance(t_or_act, dict) else t_or_act
    word = act_word(t_or_act, sub)
    sw = '<span class="chip-sw" style="background:%s" aria-hidden="true"></span>' % ACT[act][3] if swatch else ''
    inner = '%s%s<span class="chip-word">%s</span>' % (sw, icon(act_icon(t_or_act, sub), 16), esc(word))
    cls = 'chip chip--%s' % variant
    if href:
        return '<a class="%s" href="%s">%s</a>' % (cls, href, inner)
    return '<span class="%s">%s</span>' % (cls, inner)


def tag(text):
    return '<span class="tag">%s</span>' % esc(text)


SHAPE = {'loop': 'Loop', 'out-and-back': 'Out-and-back', 'point-to-point': 'Point-to-point'}


def trip_tags(t):
    out = []
    if t['kind'] == 'multi-day':
        out.append(tag('%d days' % len(t['days'])))
    if t['kind'] == 'series':
        out.append(tag('Series'))
    if t['kind'] == 'planned':
        out.append(tag('Planned'))
    if t.get('route_shape') and t['kind'] in ('trip', 'multi-day'):
        out.append(tag(SHAPE.get(t['route_shape'], t['route_shape'])))
    return ''.join(out)


def disc(act, size=32, sub=None):
    return ('<span class="disc" style="width:%dpx;height:%dpx;background:%s" aria-hidden="true">%s</span>'
            % (size, size, ACT[act][3], icons.icon(SUB_ICON.get(sub) or ACT[act][2], int(size * 0.58), '#FFFFFF', 1.75 if size < 40 else 1.5)))


def label(text, tag_='span', cls=''):
    return '<%s class="t-label%s">%s</%s>' % (tag_, (' ' + cls) if cls else '', text, tag_)


def section_head(title, meta='', level=2, id_=None, cls=''):
    return ('<div class="shead%s"><h%d class="shead-t"%s>%s</h%d>%s</div>'
            % ((' ' + cls) if cls else '', level, (' id="%s"' % id_) if id_ else '', title, level,
               ('<span class="shead-m t-mono-s">%s</span>' % meta) if meta else ''))


def place_line(t):
    bits = []
    loc = ', '.join(nb(esc(x).upper()) for x in (t.get('place'), t.get('region')) if x)
    if loc:
        bits.append(loc)
    if t.get('party'):
        bits.append(nb('WITH ' + esc(t['party']).upper()))
    return ' · '.join(bits)


def title_html(title):
    """Escaped title that never starts a line with a dash ('Peak – Couloir' keeps the dash on line 1)."""
    return esc(title).replace(' – ', '\u00a0– ').replace(' — ', '\u00a0— ')


def trip_date(t, caps=True, short=False):
    """'SAT, JAN 17, 2026' (short=True: 'JAN 17, 2026'); ranges for multi-day; 'PLANNED' for planned routes."""
    if t['kind'] == 'planned':
        return 'PLANNED' if caps else 'Planned'
    if t['days'] and t.get('end_date') and t['end_date'] != t['date']:
        return nb(frange(t['date'], t['end_date'], caps))
    if short:
        s = fdate(t['date'], 'short')
        return nb(s.upper() if caps else s)
    return nb(fdate(t['date'], 'caps' if caps else 'long'))


# ---------------------------------------------------------------- fragments (rendered SVG)

_ID = re.compile(r'\bid="([^"]+)"')


def frag(path, here, ns=None):
    """Inline a rendered .svg.html fragment: route colour -> CSS var, ids namespaced, @@ROOT@@ -> relative root."""
    if not os.path.exists(path):
        return '<!-- missing %s -->' % os.path.relpath(path, ROOT)
    s = open(path, encoding='utf-8').read()
    s = s.replace('{{route}}', 'var(--route)')
    s = s.replace('@@ROOT@@', prefix(here) if prefix(here) != './' else '')
    if ns:
        ids = set(_ID.findall(s))
        for i in ids:
            s = s.replace('id="%s"' % i, 'id="%s-%s"' % (ns, i)).replace('url(#%s)' % i, 'url(#%s-%s)' % (ns, i))
            s = s.replace('href="#%s"' % i, 'href="#%s-%s"' % (ns, i))
    return s


def rendered(t, *parts):
    return os.path.join(t['rendered'], *parts)


def render_meta(t):
    p = rendered(t, 'meta.json')
    return json.load(open(p)) if os.path.exists(p) else {'maps': {}, 'charts': {}}


def _strip_size(svg):
    return re.sub(r'^<svg width="\d+" height="\d+"', '<svg', svg, count=1)


def map_block(t, here, variants, asset_dir, ns, eager=False, cls='', site_maps=False, attrib=True, fullscreen_href=None, id_=None):
    """Responsive static map: one <div class="mv mv--{size}"> per variant, each a hillshade <img> under an SVG overlay.

    variants: [(name, size)] with size in wide|col|phone|desktop (CSS shows exactly one per breakpoint).
    asset_dir: site-relative folder the PNGs are copied to (e.g. 'trips/slug/map/')."""
    if site_maps:
        mp = os.path.join(ROOT, 'rendered', 'site', 'meta.json')
        meta = json.load(open(mp)) if os.path.exists(mp) else {'maps': {}}
    else:
        meta = render_meta(t)
    base = os.path.join(ROOT, 'rendered', 'site') if site_maps else t['rendered']
    out = []
    for i, (name, size) in enumerate(variants):
        m = meta['maps'].get(name)
        if not m:
            continue
        img = ''
        if m.get('png'):
            # always lazy: CSS hides all but one variant, and hidden lazy images are never fetched
            img = ('<img class="mv-hs" src="%s%s" alt="" width="%d" height="%d" decoding="async" loading="lazy">'
                   % (link(here, asset_dir), m['png'], m['w'], m['h']))
        svg = _strip_size(frag(os.path.join(base, name + '.svg.html'), here, '%s-%s-%s' % (ns, name, size)))
        tagx = '<span class="mv-attrib">© OSM · Not for navigation</span>' if (attrib and size == 'phone') else ''
        fs = ''
        if fullscreen_href and size == 'phone':
            fs = '<a class="mv-fs" href="%s" aria-label="Open the full map">%s</a>' % (fullscreen_href, icon('expand', 20))
        out.append('<div class="mv mv--%s" style="aspect-ratio:%d/%d">%s%s%s%s</div>' % (size, m['w'], m['h'], img, svg, tagx, fs))
    return '<div class="map%s"%s>%s</div>' % ((' ' + cls) if cls else '', (' id="%s"' % id_) if id_ else '', ''.join(out))


def chart_block(t, here, variants, ns, cls=''):
    """Responsive profile / speed chart: [(name, size)] with size wide|col|phone."""
    out = []
    for name, size in variants:
        p = rendered(t, name + '.svg.html')
        if not os.path.exists(p):
            continue
        svg = frag(p, here, '%s-%s-%s' % (ns, name, size))
        m = re.match(r'<svg width="(\d+)" height="(\d+)"', svg)
        ar = ('aspect-ratio:%s/%s' % (m.group(1), m.group(2))) if m else ''
        out.append('<div class="cv cv--%s" style="%s">%s</div>' % (size, ar, _strip_size(svg)))
    return '<div class="chart%s">%s</div>' % ((' ' + cls) if cls else '', ''.join(out))


def glyph(t, here, size='g112', ns=None):
    return frag(rendered(t, size + '.svg.html'), here, ns)


def tile(t, here, ns=None):
    return frag(rendered(t, 'tile.svg.html'), here, ns)


KEY_SYMBOLS = {
    'route': ('Route (GPX)', '<path d="M1 5H15" style="stroke:#fff;stroke-width:7;stroke-linecap:round"/><path d="M1 5H15" style="stroke:var(--route);stroke-width:3;stroke-linecap:round"/>'),
    'skin': ('Skin (ascent)', '<path d="M1 5H15" style="stroke:#fff;stroke-width:5"/><path d="M1 5H15" style="stroke:var(--route);stroke-width:2;stroke-dasharray:5 3"/>'),
    'ski': ('Ski (descent)', '<path d="M1 5H15" style="stroke:#fff;stroke-width:7;stroke-linecap:round"/><path d="M1 5H15" style="stroke:var(--route);stroke-width:3;stroke-linecap:round"/>'),
    'start_end': ('Start · end', '<circle cx="4.5" cy="5" r="4" style="fill:#16171A"/><rect x="9" y="1" width="8" height="8" style="fill:#16171A"/>'),
    'start': ('Start', '<circle cx="8" cy="5" r="4.5" style="fill:#16171A"/>'),
    'end': ('End', '<rect x="4" y="1" width="8" height="8" style="fill:#16171A"/>'),
    'gps': ('GPS max', '<path d="M8 0.5l5 9h-10z" style="fill:var(--route)"/>'),
    'mile': ('Mile', '<circle cx="8" cy="5" r="4.5" style="fill:#fff;stroke:#16171A;stroke-width:1"/>'),
    'mile_out': ('Mile, outbound', '<circle cx="8" cy="5" r="4.5" style="fill:#fff;stroke:#16171A;stroke-width:1"/>'),
    'dayend': ('End of day', '<rect x="3" y="0" width="10" height="10" style="fill:#16171A"/><text x="8" y="5.5" style="font:600 7px/1 var(--mono);fill:#fff;text-anchor:middle;dominant-baseline:central">1</text>'),
    'hut': ('Hut (night)', '<rect x="3" y="0" width="10" height="10" style="fill:#16171A"/><text x="8" y="5.5" style="font:600 7px/1 var(--mono);fill:#fff;text-anchor:middle;dominant-baseline:central">1</text>'),
    'day': ('Day label', '<text x="8" y="5.5" style="font:600 9px/1 var(--mono);fill:#B8300F;text-anchor:middle;dominant-baseline:central">D1</text>'),
    'transfer': ('Transfer', '<path d="M1 5H15" style="stroke:#66686D;stroke-width:1.5;stroke-dasharray:2 3;stroke-linecap:round"/>'),
    'planned': ('Planned', '<path d="M1 5H15" style="stroke:#45474C;stroke-width:1.5;stroke-dasharray:4 3"/>'),
    'ghost': ('Other days', '<path d="M1 5H15" style="stroke:var(--route);stroke-opacity:.35;stroke-width:2"/>'),
    'hatch': ('Skin (ascent)', '<rect x="0" y="0" width="16" height="10" style="fill:#E2DFD6"/><path d="M0 4L4 0M0 10L10 0M6 10L16 0M12 10L16 6" style="stroke:#66686D;stroke-width:1"/>'),
    'fill': ('Ski (descent)', '<rect x="0" y="2" width="16" height="8" style="fill:#E2DFD6"/><path d="M0 2H16" style="stroke:var(--route);stroke-width:2"/>'),
    'speed': ('Speed', '<path d="M1 7L5 3L9 6L15 2" style="fill:none;stroke:var(--route);stroke-width:1.5"/>'),
}


def key_row(items, cls=''):
    """items: ['skin', 'ski', ('gps', 'GPS max'), …] -> Mono caps legend decoding map symbols (never values)."""
    out = []
    for it in items:
        k, lab = (it if isinstance(it, tuple) else (it, None))
        name, sym = KEY_SYMBOLS[k]
        out.append('<li><svg width="16" height="10" viewBox="0 0 16 10" aria-hidden="true">%s</svg>%s</li>' % (sym, esc(lab or name)))
    return '<ul class="keyrow%s" aria-label="Map key">%s</ul>' % ((' ' + cls) if cls else '', ''.join(out))


# ---------------------------------------------------------------- photos

def photo(t, p, here, sizes='(min-width: 1200px) 1248px, 100vw', cls='', eager=False, caption=True):
    base = link(here, t['url'])
    src = base + p['file']
    srcset = ''
    if p.get('sm') and p.get('w'):
        big_w = p['w'] if p['w'] >= p['h'] else int(p['w'])
        small_w = int(round(p['w'] * 800.0 / max(p['w'], p['h'])))
        srcset = ' srcset="%s %dw, %s %dw" sizes="%s"' % (base + p['sm'], small_w, src, big_w, sizes)
    wh = (' width="%d" height="%d"' % (p['w'], p['h'])) if p.get('w') else ''
    img = '<img src="%s"%s%s alt="%s" decoding="async"%s>' % (src, srcset, wh, esc(p.get('alt') or ''), '' if eager else ' loading="lazy"')
    cap = ('<figcaption class="t-small">%s</figcaption>' % esc(p['caption'])) if (caption and p.get('caption')) else ''
    return '<figure class="photo%s">%s%s</figure>' % ((' ' + cls) if cls else '', img, cap)


# ---------------------------------------------------------------- trip lists

def stats_cells(t, keys=('dist', 'gain', 'high', 'time')):
    st = t['stats']
    cells = []
    mi, km = dist_vals(st.get('distance_km'))
    for k in keys:
        if k == 'dist' and mi:
            cells.append(('Dist', U(mi, km, '<span> mi</span>', '<span> km</span>')))
        elif k == 'gain' and st.get('gain_m') is not None:
            cells.append(('Gain', U(n(st['gain_m'] * FT), n(st['gain_m']), '<span> ft</span>', '<span> m</span>')))
        elif k == 'high' and st.get('high_m') is not None:
            cells.append(('GPS max', U(n(st['high_m'] * FT), n(st['high_m']), '<span> ft</span>', '<span> m</span>')))
        elif k == 'time' and st.get('moving_s'):
            cells.append(('Moving', hm(st['moving_s'])))
        elif k == 'days' and t['days']:
            cells.append(('Days', str(len(t['days']))))
    return ''.join('<div class="sc"><dt class="t-label">%s</dt><dd class="t-data-m">%s</dd></div>' % c for c in cells)


def excerpt(t, limit=180):
    txt = t['body_md'] or next((d['body_md'] for d in t['days'] if d['body_md']), '')
    return markdown.plain(txt, limit)


def trip_row(t, here, cls=''):
    """Index list row: 200×152 tile, meta, title, stats, two-line excerpt."""
    href = link(here, t['url'])
    ex = excerpt(t)
    meta_bits = [trip_date(t)]
    loc = ', '.join(x for x in (t.get('place'), t.get('region')) if x)
    if loc:
        meta_bits.append(esc(loc).upper())
    return ('<li class="trow%s" data-key="%s"><a class="trow-a" href="%s">'
            '<div class="trow-tile">%s</div><div class="trow-body">'
            '<p class="t-mono-s trow-meta">%s</p><h3 class="t-h3 trow-t">%s</h3>'
            '<div class="trow-tags">%s</div><dl class="trow-stats">%s</dl>%s</div></a></li>'
            % ((' ' + cls) if cls else '', t['slug'], href, tile(t, here, 'tl-' + t['slug']), ' · '.join(meta_bits), esc(t['title']),
               trip_tags(t), stats_cells(t, ('dist', 'gain', 'high', 'days' if t['days'] else 'time')),
               ('<p class="t-excerpt trow-ex">%s</p>' % esc(ex)) if ex else ''))


def table_head():
    return ('<div class="rtab-h" role="row"><span role="columnheader">Track</span><span role="columnheader">Activity</span>'
            '<span role="columnheader">Title</span><span role="columnheader">Date</span>'
            '<span role="columnheader" class="num">Dist <span class="u"><span class="u-mi">mi</span><span class="u-km">km</span></span></span>'
            '<span role="columnheader" class="num">Gain <span class="u"><span class="u-mi">ft</span><span class="u-km">m</span></span></span>'
            '<span role="columnheader" class="num">GPS max <span class="u"><span class="u-mi">ft</span><span class="u-km">m</span></span></span></div>')


def table_row(t, here):
    st = t['stats']
    mi, km = dist_vals(st.get('distance_km'))
    loc = ', '.join(x for x in (t.get('place'), t.get('region')) if x)
    g = lambda v: U(n(v * FT), n(v)) if v is not None else '—'  # noqa: E731
    return ('<a class="rtab-r" role="row" href="%s" data-key="%s">'
            '<span role="cell" class="rtab-g">%s</span><span role="cell">%s</span>'
            '<span role="cell" class="rtab-title"><span class="rtab-tt">%s</span><span class="t-mono-s rtab-loc">%s</span></span>'
            '<span role="cell" class="t-mono-s">%s</span><span role="cell" class="num">%s</span><span role="cell" class="num">%s</span>'
            '<span role="cell" class="num">%s</span></a>'
            % (link(here, t['url']), t['slug'], glyph(t, here, 'g112', 'g-' + t['slug']), chip(t, variant='inline', swatch=False),
               esc(t['title']), esc(loc).upper(), trip_date(t, short=True),
               U(mi, km) if mi else '—', g(st.get('gain_m')), g(st.get('high_m'))))


def phone_row(t, here):
    st = t['stats']
    mi, km = dist_vals(st.get('distance_km'))
    bits = [trip_date(t, caps=True)]
    if mi:
        bits.append(U(mi + ' MI', km + ' KM'))
    return ('<li class="prow"><a href="%s">%s<span class="prow-b"><span class="prow-t">%s</span>'
            '<span class="t-mono-s prow-m">%s%s</span></span>%s</a></li>'
            % (link(here, t['url']), glyph(t, here, 'g64', 'pg-' + t['slug']), esc(t['title']), icon(act_icon(t), 14),
               ' · '.join(bits), icon('chevron-right', 20)))


# ---------------------------------------------------------------- layout

def units_control():
    return ('<div class="units" role="radiogroup" aria-label="Units">'
            '<button type="button" role="radio" aria-checked="true" data-units="mi">MI</button>'
            '<button type="button" role="radio" aria-checked="false" data-units="km">KM</button></div>')


def header(here, active=None):
    items = []
    for act, lab in NAV:
        cur = active == act
        items.append('<a href="%s"%s>%s</a>' % (link(here, section_url(act)), ' aria-current="page"' if cur else '', lab))
    items2 = []
    for key, lab, url in (('map', 'Map &amp; archive', 'map/'), ('about', 'About', 'about/')):
        items2.append('<a href="%s"%s>%s</a>' % (link(here, url), ' aria-current="page"' if active == key else '', lab))
    menu_rows = []
    for act, lab in NAV:
        sub = ('<span class="menu-sub">Paddleboarding · Rafting<br>Kayaking · Mountaineering</span>' if act == 'other' else '')
        menu_rows.append('<li><a href="%s">%s<span class="menu-w"><span>%s</span>%s</span>%s</a></li>'
                         % (link(here, section_url(act)), disc(act, 32), lab, sub, icon('chevron-right', 20)))
    return ('<a class="skip" href="#main">Skip to content</a>'
            '<header class="site-h"><div class="site-h-in">'
            '<a class="brand" href="%s"><span class="brand-n">%s</span><span class="brand-c">%s</span></a>'
            '<nav class="nav" aria-label="Main"><div class="nav-l">%s</div><span class="nav-sep" aria-hidden="true"></span>'
            '<div class="nav-l">%s</div>%s</nav>'
            '<button class="menu-btn" type="button" aria-expanded="false" aria-controls="menu" aria-label="Menu">%s%s</button>'
            '</div>'
            '<div class="menu" id="menu" hidden><nav aria-label="Menu"><p class="t-label menu-l">Reports</p><ul class="menu-list">%s</ul>'
            '<p class="t-label menu-l">Site</p><ul class="menu-list menu-list--site">'
            '<li><a href="%s">%s<span class="menu-w"><span>Map &amp; archive</span></span>%s</a></li>'
            '<li><a href="%s">%s<span class="menu-w"><span>About</span></span>%s</a></li></ul>'
            '<div class="menu-units"><span class="t-label">Units</span>%s</div></nav></div></header>'
            % (link(here, ''), SITE_NAME, HOME_COORDS, ''.join(items), ''.join(items2), units_control(),
               icon('menu', 24, 'i-open'), icon('close', 24, 'i-close'), ''.join(menu_rows),
               link(here, 'map/'), icon('map', 24), icon('chevron-right', 20),
               link(here, 'about/'), icon('info', 24), icon('chevron-right', 20), units_control()))


def footer(here):
    reports = ''.join('<li><a href="%s">%s</a></li>' % (link(here, section_url(a)), lab) for a, lab in NAV)
    site = ('<li><a href="%s">Map &amp; archive</a></li><li><a href="%s">About</a></li><li><a href="%s">%sRSS</a></li>'
            % (link(here, 'map/'), link(here, 'about/'), link(here, 'feed.xml'), icon('rss', 16)))
    return ('<footer class="site-f"><div class="site-f-in">'
            '<div class="f-brand"><a class="brand-n" href="%s">%s</a><span class="t-mono-s">BASED IN LAKE TAHOE · AIARE 2</span></div>'
            '<nav class="f-nav" aria-labelledby="f-rep"><p class="t-label" id="f-rep">Reports</p><ul>%s</ul></nav>'
            '<nav class="f-nav" aria-labelledby="f-site"><p class="t-label" id="f-site">Site</p><ul>%s</ul></nav>'
            '<div class="f-note"><p>Reports describe past conditions, not advice. Check the current avalanche forecast before you go.</p>'
            '<p class="t-mono-s">MAPS: AWS TERRAIN TILES · © OPENSTREETMAP CONTRIBUTORS</p>'
            '<p class="t-mono-s">© %d ERIC SICHAK</p></div></div></footer>'
            % (link(here, ''), SITE_NAME, reports, site, date.today().year))


def document(here, title, body, description='', active=None, css_pages=(), image=None, extra_head='', body_cls='', bottom=''):
    p = prefix(here)
    p = '' if p == './' else p
    full_title = title if title == SITE_NAME else '%s · %s' % (title, SITE_NAME)
    canon = SITE_URL + (here if not here.endswith('index.html') else here[:-10])
    og = ''
    if image:
        og = '<meta property="og:image" content="%s">' % (SITE_URL + image)
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>%s</title><meta name="description" content="%s">'
            '<link rel="canonical" href="%s">'
            '<meta property="og:type" content="website"><meta property="og:title" content="%s">'
            '<meta property="og:description" content="%s"><meta property="og:url" content="%s">%s'
            '<meta name="theme-color" content="#F2F1EC">'
            '<link rel="icon" href="%sassets/favicon.svg" type="image/svg+xml">'
            '<link rel="alternate" type="application/rss+xml" title="%s — trip reports" href="%sfeed.xml">'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="%s">'
            '<link rel="stylesheet" href="%sassets/site.css">'
            '<script>try{if(localStorage.getItem("units")==="km")document.documentElement.classList.add("km")}catch(e){}</script>'
            '%s</head><body class="%s">%s<main id="main">%s</main>%s%s'
            '<script src="%sassets/site.js" defer></script></body></html>\n'
            % (esc(full_title), esc(description or SITE_TAGLINE), canon, esc(title), esc(description or SITE_TAGLINE), canon, og,
               p, SITE_NAME, p, FONTS.replace('&', '&amp;'), p, extra_head, body_cls, header(here, active), body, footer(here), bottom, p))
