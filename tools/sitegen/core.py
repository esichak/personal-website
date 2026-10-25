"""Shared building blocks for every page: layout, header/footer, units, chips, maps, profiles, photos, rows.

Pages live in tools/sitegen/pages/*.py; each exposes build(site) -> list of Page. CSS for components here lives in
assets/css/base.css; page-specific CSS in assets/css/pages/<module>.css (concatenated by tools/build.py).
All links are relative, so the site works at https://esichak.github.io/personal-website/ and on any domain.
"""
import html
import json
import math
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
# the one tagline: RSS channel, default meta description, home dek (home.LEAD) and the About lede
TAGLINE = 'Backcountry skiing, climbing, hiking, mountain biking and other trips, each with the full GPX track and map.'
SITE_TAGLINE = TAGLINE
SITE_URL = 'https://esichak.github.io/personal-website/'
AUTHOR_NAME = SITE_NAME          # the one author of every write-up (structured data); never a `party:` name
AUTHOR_URL = SITE_URL + 'about/'
STRUCTURED_MIN_CHARS = 100       # a report needs this much of Eric's own text to be marked up as a BlogPosting
HOME_COORDS = '39.09°N 120.04°W · LAKE TAHOE'
FONTS = ('https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100..112,400..700'
         '&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;1,8..60,400&family=Geist+Mono:wght@400..600&display=swap')  # serif: 400 only
SUB_ICON = {'SUP': 'SUP', 'Rafting': 'RFT', 'Kayaking': 'KYK', 'Mountaineering': 'MTN'}
SUB_WORD = {'SUP': 'Paddleboarding', 'Rafting': 'Rafting', 'Kayaking': 'Kayaking', 'Mountaineering': 'Mountaineering'}
NAV = [('ski', 'Backcountry Ski'), ('climb', 'Climbing'), ('hike', 'Hiking'), ('mtb', 'Mountain Biking'), ('other', 'Other')]
PCT_SLUG = 'pacific-crest-trail-2024'  # the journal the header's PCT link opens (shown only when that trip exists)
PCT_LABEL = 'PCT'
SEP = '\u00a0· '  # plain-text separator only (aria-labels, descriptions, RSS); Mono-S lines use meta_items()

esc = html.escape


# ---------------------------------------------------------------- pages & urls

class Page:
    def __init__(self, url, html_, title='', index=True):
        self.url = url  # '' for home, 'ski/', 'trips/slug/', '404.html'
        self.html = html_
        self.title = title
        self.index = index  # False: left out of sitemap.xml (noindex helper pages such as trips/<slug>/map/)


def section_url(act):
    return ACT[act][4] + '/'


_SITE_META = []


def read_site_meta():
    """rendered/site/meta.json (region + ski-panel overview maps) as it is on disk now."""
    return read_json(os.path.join(ROOT, 'rendered', 'site', 'meta.json'), {'maps': {}, 'regions': []})


def site_meta():
    """rendered/site/meta.json, read once."""
    if not _SITE_META:
        _SITE_META.append(read_site_meta())
    return _SITE_META[0]


def region_map_href(here, region):
    """Link to the region on map/: its map panel when a region map is rendered for it, else its entry in the 'Not on a
    region map' block (every region in rendered/site/meta.json 'all_regions' has an anchor there). None for an unknown
    region. build.py --check verifies every map/#region-* anchor resolves."""
    if not region:
        return None
    s = content.slugify(region)
    sm = site_meta()
    if ('region-%s-desktop' % s) not in sm.get('maps', {}) and region not in sm.get('all_regions', []):
        return None
    return link(here, 'map/#region-' + s)


def listed_trips(site):
    """The trips a region group lists and counts: every report, and the tick-list goals that are still future routes
    (site['active_goals']: a completed or archived goal keeps its page and leaves these lists, as on Home and the
    section pages)."""
    goals_ = site.get('active_goals')
    if goals_ is None:
        goals_ = site.get('planned')
    if goals_ is None:   # a bare site dict (register_site in a test): every planned route counts as active
        goals_ = [t for t in site['trips'] if t['kind'] == 'planned']
    active = {t['slug'] for t in goals_}
    return [t for t in site['trips'] if t['kind'] != 'planned' or t['slug'] in active]


def region_groups(site, meta=None):
    """[(name, slug, trips newest-first with planned last)] for the regions that have a region map (meta 'regions';
    meta None: site_meta()), ordered by number of published trips, then name. The trips are the ones the map's own
    entry names, or failing that the listed trips filed under the region; a series is on no region map."""
    meta = site_meta() if meta is None else meta
    out = []
    trips = listed_trips(site)
    for name in meta.get('regions') or []:
        slug = content.slugify(name)
        m = (meta.get('maps') or {}).get('region-%s-desktop' % slug) or {}
        keys = set(m.get('trips') or [t['slug'] for t in trips if t['region'] == name and t['kind'] != 'series'])
        ts = [t for t in trips if t['slug'] in keys]
        ts.sort(key=lambda t: t['kind'] == 'planned')  # stable: keeps newest-first, planned last
        if ts:
            out.append((name, slug, ts))
    out.sort(key=lambda r: (-sum(1 for t in r[2] if t['kind'] != 'planned'), r[0]))
    return out


def region_pages(site, meta=None):
    """[(name, slug, ts)] for the regions that get a page of their own (regions/<slug>/, sitegen.pages.region): a region
    with a region map (meta 'regions' and a 'region-<slug>-desktop' or '-phone' entry under 'maps'; meta None:
    site_meta()) and at least one published report filed under it. ts is every listed trip (listed_trips) whose `region`
    is exactly the name, newest first with planned routes last: what the content says, not what the map was last drawn
    with, so a report without a track, a journal, or a report newer than the last render is on its region's page, and
    the page's count is the count the Trips page gives the region. A region of planned routes only has no page, nor has
    a name without a slug; of two names with one slug only the first has one. Most published reports first, then A-Z."""
    meta = site_meta() if meta is None else meta
    maps = meta.get('maps') or {}
    trips = listed_trips(site)
    out, seen = [], set()
    for name in meta.get('regions') or []:
        slug = content.slugify(name)
        if not slug or slug in seen:
            continue
        if ('region-%s-desktop' % slug) not in maps and ('region-%s-phone' % slug) not in maps:
            continue
        ts = [t for t in trips if t.get('region') == name]
        ts.sort(key=lambda t: t['kind'] == 'planned')  # stable: keeps newest-first, planned last
        if not any(t['kind'] != 'planned' for t in ts):
            continue
        seen.add(slug)
        out.append((name, slug, ts))
    out.sort(key=lambda r: (-sum(1 for t in r[2] if t['kind'] != 'planned'), r[0]))
    return out


_REGION_PAGES = {}   # region name -> slug, for the regions with a page; register_site() fills it


def region_page_href(here, region):
    """Link to the region's own page, or None when it has none (no region map, or the site was registered without a
    site meta: then a caller links to map/ as before, see region_map_href). Asked by the exact name, as the page lists
    by it: a second spelling of a region is not on the page, so it keeps its link to map/."""
    slug = _REGION_PAGES.get(region) if region else None
    return link(here, 'regions/%s/' % slug) if slug else None


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


def recorded(a, b=None):
    """The opening item of a map caption: 'As recorded on Mar 28, 2026' for one date, 'As recorded Apr 22 – Sep 21, 2024'
    for a range, '' without a date (the caption then says nothing about when)."""
    if not a:
        return ''
    return ('As recorded %s' if (b and b != a) else 'As recorded on %s') % frange(a, b)


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


_ML_BR = '<span class="ml-br" aria-hidden="true"></span>'


def meta_items(items, br_after=None, cls=''):
    """One Mono-S meta line (the .ml component): CSS draws the '·' between items, so a wrapped line never starts or ends
    with a dot and an item never splits (keep nb() inside items). items: HTML strings or (html, extra_cls) tuples; empty
    items are skipped. br_after=i puts a line-break slot after item i (.ml-br, shown per breakpoint by page CSS).
    Screen readers hear ', ' between items."""
    out, k = [], 0
    for i, it in enumerate(items):
        h, c = it if isinstance(it, tuple) else (it, '')
        if h:
            out.append('<span class="mi%s">%s%s</span>' % ((' ' + c) if c else '', '<span class="sr">, </span>' if k else '', h))
            k += 1
        if br_after is not None and i == br_after and k and out[-1] != _ML_BR:
            out.append(_ML_BR)
    while out and out[-1] == _ML_BR:
        out.pop()
    if not out:
        return ''
    return '<span class="ml%s">%s</span>' % ((' ' + cls.strip()) if cls.strip() else '', ''.join(out))


def approx(t):
    """'≈ ' before a tick-list goal's numbers, '' before a report's. A goal's distance, gain and high point are measured
    from a planned line, so every place that shows them (cards, list rows, the map page's table) marks them approximate."""
    return '≈ ' if t.get('kind') == 'planned' else ''


def plain_stats(t, items=False):
    """Short Mono-S caps stats: '12.8 MI · 5,302 FT GAIN' (switches with units; '≈ 12.8 MI' for a tick-list goal). No gain
    for climbing (the GPX gain of a climb is the walk, not the route) or flat water. items=True: the list for
    meta_items(); default: the legacy string."""
    st = t['stats']
    parts = []
    p = approx(t)
    mi, km = dist_vals(st.get('distance_km'))
    if mi:
        parts.append(U(nb(p + mi + ' MI'), nb(p + km + ' KM')))
    if t['activity'] != 'climb' and not is_flat(t) and st.get('gain_m') is not None and st.get('gain_m') > 30:
        parts.append(U(nb(p + n(st['gain_m'] * FT) + ' FT GAIN'), nb(p + n(st['gain_m']) + ' M GAIN')))
    return parts if items else SEP.join(parts)


def clip_words(s, limit=155):
    """Plain text cut to <= limit characters on a word boundary, with an ellipsis (meta descriptions)."""
    if len(s) <= limit:
        return s
    cut = s[:limit - 1].rsplit(' ', 1)[0].rstrip(',;:·')
    return cut if cut.endswith(('.', '!', '?')) else cut + '…'


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
SHAPE_CAPS = {k: v.upper().replace('-', '\u2011') for k, v in SHAPE.items()}  # 'OUT‑AND‑BACK' (non-breaking hyphens)


def trip_tags(t, shape=True, status=True):
    """Status tags (MULTI-DAY · N DAYS, SERIES, PLANNED) and, with shape=True (title chip rows), the route-shape tag.
    List rows pass shape=False: they carry the route shape in their Mono-S meta line instead. status=False drops the
    status tags (planned list rows: their meta line already opens 'PLANNED ROUTE')."""
    out = []
    if status and t['kind'] == 'multi-day':
        out.append(tag('Multi-day · %d day%s' % (len(t['days']), '' if len(t['days']) == 1 else 's')))
    if status and t['kind'] == 'series':
        out.append(tag('Series'))
    if status and t['kind'] == 'planned':
        out.append(tag('Planned'))
    if shape and t.get('route_shape') and t['kind'] in ('trip', 'multi-day', 'planned'):
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


def place_line(t, items=False):
    """'PLACE, REGION · WITH PARTY'. items=True: the list for meta_items() (the place item may wrap at its comma
    when it alone is wider than the line); default: the legacy string for callers that still join with SEP."""
    bits = []
    loc = ', '.join(nb(esc(x).upper()) for x in (t.get('place'), t.get('region')) if x)
    if loc:
        bits.append((loc, 'mi-w'))
    if t.get('party'):
        bits.append(nb('WITH ' + esc(t['party']).upper()))
    if items:
        return bits
    return SEP.join(b[0] if isinstance(b, tuple) else b for b in bits)


def title_html(title):
    """Escaped title that never starts a line with a dash ('Peak – Couloir' keeps the dash on line 1)."""
    return esc(title).replace(' – ', '\u00a0– ').replace(' — ', '\u00a0— ')


def trip_date(t, caps=True, short=False):
    """'SAT, JAN 17, 2026' (short=True: 'JAN 17, 2026', 'APR–SEP 2024' for a long series); ranges for multi-day;
    'PLANNED' for planned routes."""
    if t['kind'] == 'planned':
        return 'PLANNED' if caps else 'Planned'
    if short:
        a, b = t['date'], t.get('end_date')
        if t['days'] and b and b != a and a.year == b.year and (b - a).days > 31:
            s = '%s–%s %d' % (a.strftime('%b'), b.strftime('%b'), a.year)
        elif t['days'] and b and b != a:
            s = frange(a, b)
        else:
            s = fdate(a, 'short')
        return nb(s.upper() if caps else s)
    if t['days'] and t.get('end_date') and t['end_date'] != t['date']:
        return nb(frange(t['date'], t['end_date'], caps))
    return nb(fdate(t['date'], 'caps' if caps else 'long'))


# ---------------------------------------------------------------- fragments (rendered SVG)

_ID = re.compile(r'\bid="([^"]+)"')


def _read(path):
    """The text of a rendered fragment (closed after reading)."""
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def read_json(path, default=None):
    """A JSON file's value, the handle closed; `default` when the file does not exist."""
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def frag(path, here, ns=None):
    """Inline a rendered .svg.html fragment: route colour -> CSS var, ids namespaced, @@ROOT@@ -> relative root."""
    if not os.path.exists(path):
        return '<!-- missing %s -->' % os.path.relpath(path, ROOT)
    s = _read(path)
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
    """What tools/render.py drew for the trip (rendered/trips/<slug>/meta.json): its maps and charts. Empty when nothing
    is rendered, and when the trip has no track: every render is made from the track, so once the track is gone the
    committed renders are not shown (no map, profile, key or preload), whatever the folder still holds."""
    p = rendered(t, 'meta.json')
    if not has_track(t) or not os.path.exists(p):
        return {'maps': {}, 'charts': {}}
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def _strip_size(svg):
    return re.sub(r'^<svg width="\d+" height="\d+"', '<svg', svg, count=1)


def map_block(t, here, variants, asset_dir, ns, eager=False, cls='', site_maps=False, attrib=True, fullscreen_href=None, id_=None):
    """Responsive static map: one <div class="mv mv--{size}"> per render, each a hillshade <img> under an SVG overlay.

    variants: [(name, size)] with size in wide|col|phone|desktop (CSS shows exactly one per breakpoint), or fs (the
    full-screen map page, always shown). Consecutive variants of one render share one div (<div class="mv mv--col
    mv--phone">), so its SVG is inlined once. asset_dir: site-relative folder the PNGs are copied to ('trips/slug/map/').
    eager=True marks the hero map: fetchpriority="high" on every variant (pair it with map_preloads() in the head).
    The fs map loads at once (it is the whole page)."""
    if site_maps:
        mp = os.path.join(ROOT, 'rendered', 'site', 'meta.json')
        meta = read_json(mp, {'maps': {}})
    else:
        meta = render_meta(t)
    base = os.path.join(ROOT, 'rendered', 'site') if site_maps else t['rendered']
    groups = []
    for name, size in variants:
        if groups and groups[-1][0] == name:
            groups[-1][1].append(size)
        else:
            groups.append((name, [size]))
    out = []
    for name, sizes in groups:
        m = meta['maps'].get(name)
        if not m:
            continue
        fs_page = 'fs' in sizes
        # lazy everywhere but the fs page: CSS hides all but one variant, and hidden lazy images are never fetched
        lazy = '' if fs_page else ' loading="lazy"'
        img = ''
        if m.get('png'):
            img = ('<img class="mv-hs" src="%s%s" alt="" width="%d" height="%d" decoding="async"%s%s>'
                   % (link(here, asset_dir), m['png'], m['w'], m['h'], lazy, ' fetchpriority="high"' if (eager or fs_page) else ''))
        if m.get('base'):
            # static contours, water and roads: a cached image shared by every page that shows this map
            img += ('<img class="mv-base" src="%s%s" alt="" width="%d" height="%d" decoding="async"%s%s>'
                    % (link(here, asset_dir), m['base'], m['w'], m['h'], lazy, ' fetchpriority="high"' if eager else ''))
        svg = _strip_size(frag(os.path.join(base, name + '.svg.html'), here, '%s-%s-%s' % (ns, name, sizes[0])))
        tagx = '<span class="mv-attrib">© OSM · Not for navigation</span>' if (attrib and 'phone' in sizes) else ''
        fs = ''
        if fullscreen_href and 'phone' in sizes:
            fs = '<a class="mv-fs" href="%s" aria-label="Open the full map">%s</a>' % (fullscreen_href, icon('expand', 20))
        out.append('<div class="mv %s" style="aspect-ratio:%d/%d">%s%s%s%s</div>'
                   % (' '.join('mv--' + x for x in sizes), m['w'], m['h'], img, svg, tagx, fs))
    return '<div class="map%s"%s>%s</div>' % ((' ' + cls) if cls else '', (' id="%s"' % id_) if id_ else '', ''.join(out))


PRELOAD_MEDIA = {'wide': '(min-width: 1200px)', 'col': '(min-width: 560px) and (max-width: 1199.98px)',
                 'phone': '(max-width: 559.98px)', 'desktop': '(min-width: 560px)'}


def map_preloads(t, here, variants, asset_dir, nowide=False, site_maps=False):
    """<link rel="preload"> for the hillshade and the base layer (contours, water, roads) each breakpoint shows, so the
    hero map (the LCP image) paints in one step. Pass only the hero variants. nowide=True: the col variant also serves
    >= 1200 (map--nowide)."""
    meta = site_meta() if site_maps else render_meta(t)
    out = []
    for name, size in variants:
        m = meta['maps'].get(name)
        if not m:
            continue
        media = '(min-width: 560px)' if (size == 'col' and nowide) else PRELOAD_MEDIA.get(size)
        if not media:
            continue
        if m.get('png'):
            out.append('<link rel="preload" as="image" href="%s%s" media="%s" fetchpriority="high">'
                       % (link(here, asset_dir), m['png'], media))
        if m.get('base'):
            out.append('<link rel="preload" as="image" type="image/svg+xml" href="%s%s" media="%s" fetchpriority="high">'
                       % (link(here, asset_dir), m['base'], media))
    return ''.join(out)


def vx_line(charts, variants, nowide=None, items=False):
    """'VERTICAL ×N' per chart width: each rendered width has its own exaggeration, so one item per (name, size) and CSS
    shows the one that matches the visible chart (.vx--wide|col|phone). One item when every rounded value is the same.
    nowide: the col chart also serves >= 1200 (chart--nowide); None = when no wide variant is present.
    items=True: [(html, cls)] for meta_items(); default: the legacy run of spans."""
    vals = [(size, charts[name]['vx']) for name, size in variants if name in charts and charts[name].get('vx')]
    if not vals:
        return [] if items else ''
    if len({'%.1f' % v for _, v in vals}) == 1:
        its = [(nb('VERTICAL ×%.1f' % vals[0][1]), '')]
    else:
        if nowide is None:
            nowide = not any(size == 'wide' for size, _ in vals)
        its = [(nb('VERTICAL ×%.1f' % v), 'vx vx--%s%s' % (size, ' vx--nowide' if (nowide and size == 'col') else '')) for size, v in vals]
    if items:
        return its
    return ''.join('<span%s>%s</span>' % ((' class="%s"' % c) if c else '', h) for h, c in its)


_START_MK = re.compile(r'<circle[^>]*r="[57]"[^>]*fill: #16171A; stroke: #FFFFFF')
_END_MK = re.compile(r'<rect[^>]*width="1[04]"[^>]*fill: #16171A; stroke: #FFFFFF')


def drawn_ends(t, name):
    """(start, end): whether the rendered map `name` draws mapkit's start disc / end square, so key rows only
    decode markers that are actually on the map."""
    p = rendered(t, name + '.svg.html')
    s = _read(p) if os.path.exists(p) else ''
    return bool(_START_MK.search(s)), bool(_END_MK.search(s))


def speed_meta(t):
    """Mono-S meta for the flat-water speed chart. Names the smoothing the rendered chart actually uses (its aria-label
    says 'median' for the old rolling-median render, 'average' for the distance/time window), so the label never lies."""
    p = rendered(t, 'speed-col.svg.html')
    s = _read(p) if os.path.exists(p) else ''
    how = 'MEDIAN' if '3-minute median' in s else 'AVERAGE'
    return meta_items([nb('MPH, 3\u2011MIN %s' % how), nb('FLAT WATER, NO ELEVATION PROFILE')])


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


GLYPH_SIZES = {'g112': (112, 64), 'g64': (64, 48), 'tile': (200, 152)}


def _drawing(t, here, name, cls):
    """A trip's track drawing as a cached image: build.py writes rendered/trips/<slug>/<name>.svg.html out as the standalone
    trips/<slug>/<name>.svg (route colour and the map CSS it uses baked in), so every page that lists the trip shares one
    file. Decorative (alt=""): rows and links name the trip in text. '' when the drawing is not rendered, or when the
    trip has no track (a drawing left in rendered/ by a track that was removed is not published: build.py)."""
    if not has_track(t) or not os.path.exists(rendered(t, name + '.svg.html')):
        return ''
    w, h = GLYPH_SIZES[name]
    return ('<img class="gl gl--%s%s" src="%s%s.svg" width="%d" height="%d" alt="" loading="lazy" decoding="async">'
            % (name, cls, link(here, t['url']), name, w, h))


def glyph(t, here, size='g112', ns=None, cls=''):
    """Track glyph (g112 112×64 or g64 64×48) as an <img> (see _drawing). ns is unused (images need no id namespace);
    cls: extra classes with a leading space (' glyph')."""
    return _drawing(t, here, size, cls)


def tile(t, here, ns=None, cls=''):
    """200×152 map tile (list rows, cards) as an <img> (see _drawing)."""
    return _drawing(t, here, 'tile', cls)


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
    # the heavy line the planned report map draws (2.5px ink-2 on a 5.5px casing, dash 8/5 at map scale)
    'planned': ('Planned', '<path d="M1 5H15" style="stroke:#EEECE6;stroke-width:5.5"/><path d="M1 5H15" style="stroke:#45474C;stroke-width:2.5;stroke-dasharray:6 3"/>'),
    # the light planned line on region maps (#66686D 1.5px, dash 4/3 on a 3.5px casing, as render_site draws it)
    'planned_site': ('Planned route', '<path d="M1 5H15" style="stroke:#EEECE6;stroke-width:3.5"/><path d="M1 5H15" style="stroke:#66686D;stroke-width:1.5;stroke-dasharray:4 3"/>'),
    'ghost': ('Other days', '<path d="M1 5H15" style="stroke:var(--route);stroke-opacity:.35;stroke-width:2"/>'),
    'hatch': ('Skin (ascent)', '<rect x="0" y="0" width="16" height="10" style="fill:#E2DFD6"/><path d="M0 4L4 0M0 10L10 0M6 10L16 0M12 10L16 6" style="stroke:#66686D;stroke-width:1"/>'),
    'fill': ('Ski (descent)', '<rect x="0" y="2" width="16" height="8" style="fill:#E2DFD6"/><path d="M0 2H16" style="stroke:var(--route);stroke-width:2"/>'),
    'speed': ('Speed', '<path d="M1 7L5 3L9 6L15 2" style="fill:none;stroke:var(--route);stroke-width:1.5"/>'),
}


def key_row(items, cls='', label='Map key'):
    """items: ['skin', 'ski', ('gps', 'GPS max'), …] -> Mono caps legend decoding map symbols (never values).
    label: the list's accessible name ('Elevation key' / 'Speed key' for chart legends)."""
    out = []
    for it in items:
        k, lab = (it if isinstance(it, tuple) else (it, None))
        name, sym = KEY_SYMBOLS[k]
        out.append('<li><svg width="16" height="10" viewBox="0 0 16 10" aria-hidden="true">%s</svg>%s</li>' % (sym, esc(lab or name)))
    return '<ul class="keyrow%s" aria-label="%s">%s</ul>' % ((' ' + cls) if cls else '', esc(label), ''.join(out))


def key_rows(desk, phone, cls=''):
    """One key row when the desktop and phone maps draw the same symbols, else one per map (CSS swaps them at 560)."""
    desk, phone = list(desk), list(phone)
    if desk == phone:
        return key_row(desk, cls)
    c = (' ' + cls) if cls else ''
    return key_row(desk, 'keyrow--d' + c) + key_row(phone, 'keyrow--p' + c)


def _draws(t, name, pattern):
    """True when the rendered fragment `name` contains `pattern` (a regex)."""
    try:
        return re.search(pattern, _read(rendered(t, name + '.svg.html'))) is not None
    except OSError:
        return False


def feature_key(t, variants, miles=True, cls='keyrow--compact'):
    """Compact key row under a featured map (home, section pages): decodes only symbols the rendered variant actually
    draws — skin/ski styling (dashed skin on ski col renders) or a plain route line, the start/end markers, GPS max and,
    with miles=True, the mile discs ('mile_out' when the map numbers the outbound leg only). The home featured map hides
    its discs, so home passes miles=False. Single-day trips only: overview maps draw day symbols this row does not decode."""
    if t['kind'] != 'trip':
        return ''
    ends = ['start', 'end'] if t.get('route_shape') == 'point-to-point' else ['start_end']
    flat = is_flat(t)
    maps = render_meta(t).get('maps', {})
    rows = []
    for name, _size in variants:
        skin = t['activity'] == 'ski' and _draws(t, name, r'<path class="mk-trk"[^>]*stroke-dasharray')
        gps = not flat and _draws(t, name, r'class="mk-gps"|l6 10h-12z"[^>]*fill: \{\{route\}\}')  # label or red triangle
        row = (['skin', 'ski'] if skin else ['route']) + ends + (['gps'] if gps else [])
        if miles and _draws(t, name, r'class="mk-mile'):
            row.append('mile_out' if (maps.get(name) or {}).get('outbound_only') else 'mile')
        rows.append(row)
    if not rows:
        return ''
    return key_rows(rows[0], rows[-1], cls)


def map_caption(first_items, attrib=True):
    """The one map caption (Small, under the key row): first_items (e.g. ['As recorded on Mar 28, 2026', 'full track, not trimmed',
    'North up'] — no device name: some tracks are Strava GPX exports, so the caption only claims what every file supports —
    or ['North up'] for maps with no single track), then the terrain / OSM / not-for-navigation
    credit. Two lines from 1200 (.ml-br), one flowing paragraph below; phones (< 560) drop the credit (.mapcap-2): the
    in-map tag and the footer carry it. No button slot: the title block and the phone bottom bar carry GPX."""
    items = list(first_items)
    if attrib:
        items += [('Terrain: AWS Terrain Tiles', 'mapcap-2'), ('Map data © OpenStreetMap contributors', 'mapcap-2'),
                  ('Not for navigation', 'mapcap-2')]
    return ('<div class="mapcap"><p class="mapcap-t">%s</p></div>'
            % meta_items(items, br_after=(len(first_items) - 1) if (attrib and first_items) else None))


# ---------------------------------------------------------------- photos

# What a phone is told about a photo that fills its width. Photos come as an 800 px copy and the full 1600 px file,
# and a 3x phone asked for a 390 px slot needs 1170 px, so it took the full file: 250-370 KB for the lead photo, which
# measured as a largest-contentful-paint of 4-6 s on a throttled phone (docs/IMPLEMENTATION_REPORT.md). Below 560 px
# the slot is therefore declared as 55vw, which makes every phone up to 484 px wide take the 800 px copy: about two
# source pixels per CSS pixel (0.68 per device pixel on a 3x phone, softer than the full file under magnification).
# The viewer still opens the full file. From 560 px the declared width is the real one.
PHONE_SLOT = '55vw'
PHONE_FULL = '(min-width: 560px) 100vw, ' + PHONE_SLOT
PHONE_SHAPES = (1.2, 1.6)   # width / height: the landscape shapes (about 4:3 to 3:2) the 800 px copy is enough for
THUMB_EDGE = 320   # the short edge of a .th copy (the card-size derivative; tools/thumbs.py makes them)


def phone_sizes(sizes, p):
    """`sizes` for one photo. PHONE_FULL suits an ordinary landscape photo, whose .sm copy is 800 px wide. A portrait's
    .sm copy is only 600 px wide and a panorama's is 800 px along the edge its slot crops, so for those shapes (and
    for a photo whose size is not recorded) a phone is told the real width, 100vw, and takes the full file when it
    needs it. A string without PHONE_FULL is returned as it is."""
    w, h = p.get('w'), p.get('h')
    if PHONE_FULL not in sizes or (w and h and PHONE_SHAPES[0] <= w / float(h) <= PHONE_SHAPES[1]):
        return sizes
    return sizes.replace(PHONE_FULL, '100vw')


def photo(t, p, here, sizes='(min-width: 1200px) 1248px, ' + PHONE_FULL, cls='', eager=False, caption=True):
    base = link(here, t['url'])
    src = base + p['file']
    srcset = ''
    sizes = phone_sizes(sizes, p)
    sized = bool(p.get('w') and p.get('h'))   # only as a pair: one of the two alone says nothing about the shape
    if p.get('sm') and sized:
        big_w = p['w'] if p['w'] >= p['h'] else int(p['w'])
        small_w = int(round(p['w'] * 800.0 / max(p['w'], p['h'])))
        srcset = ' srcset="%s %dw, %s %dw" sizes="%s"' % (base + p['sm'], small_w, src, big_w, sizes)
    wh = (' width="%d" height="%d"' % (p['w'], p['h'])) if sized else ''
    img = '<img src="%s"%s%s alt="%s" decoding="async"%s>' % (src, srcset, wh, esc(p.get('alt') or ''), '' if eager else ' loading="lazy"')
    cap = ('<figcaption class="t-small">%s</figcaption>' % esc(p['caption'])) if (caption and p.get('caption')) else ''
    return '<figure class="photo%s">%s%s</figure>' % ((' ' + cls) if cls else '', img, cap)


def _pct(v):
    return ('%g' % v) if v == int(v) else ('%.1f' % v).rstrip('0').rstrip('.')


def thumb_width(p):
    """The pixel width of a photo's .th copy: THUMB_EDGE on the short edge, the other edge in proportion and rounded,
    exactly as tools/lib/photos.thumb_copy writes it (427 for a 1600 x 1200 photo, 320 for a 1200 x 1600 one)."""
    return int(round(p['w'] * float(THUMB_EDGE) / min(p['w'], p['h'])))


CARD_PHONE_SLOT = '112px'                    # a card's cover on a phone: the last item of every card sizes string
CARD_PHONE_MEDIA = '(max-width: 559.98px)'   # where that slot applies: below the cards' first breakpoint (560 px)
# What the phone <source> declares for that slot: 106 px, the widest whole number at which a 3x phone is still served
# by the 320 px short edge of a .th copy (3 x 106 = 318). Declared at the real 112 px, a 3x phone wanted 336 px, so for
# a portrait or square cover (a .th copy 320 px wide) it took the 600 px copy instead: 154 KB where 42 KB do, measured
# on the first Featured card of a region page. A landscape cover's copy is 427 px wide and is chosen either way.
CARD_PHONE_SIZES = '%dpx' % (THUMB_EDGE // 3)


def _cover_srcset(t, p, here):
    """(src, srcset or '') for a cover image: the 800px .sm copy and the full file, as core.photo builds them."""
    base = link(here, t['url'])
    src = base + p['file']
    if p.get('sm') and p.get('w') and p.get('h'):
        small_w = int(round(p['w'] * 800.0 / max(p['w'], p['h'])))
        return src, '%s %dw, %s %dw' % (base + p['sm'], small_w, src, p['w'])
    return src, ''


def _card_source(t, p, here, sizes):
    """The <source> that offers a card cover's .th copy to phones, or ''. A card's slot is CARD_PHONE_SLOT wide below
    560 px, and there the .th copy (427 px wide for a landscape cover, 320 px for a portrait or square one) is plenty;
    the source declares the slot as CARD_PHONE_SIZES so that a 3x phone takes it for every shape. From 560 px up the
    slot grows to 400 px: a 1x screen would then be handed the .th copy at almost one source pixel per screen pixel,
    visibly softer than the 800 px copy it had always had, so wider screens are not offered it at all. Only for a card
    sizes string (one that ends with CARD_PHONE_SLOT), a photo with both copies and a recorded size."""
    if not (p.get('th') and p.get('sm') and p.get('w') and p.get('h') and sizes.endswith(', ' + CARD_PHONE_SLOT)):
        return ''
    base = link(here, t['url'])
    small_w = int(round(p['w'] * 800.0 / max(p['w'], p['h'])))
    return ('<source media="%s" srcset="%s %dw, %s %dw, %s %dw" sizes="%s">'
            % (CARD_PHONE_MEDIA, base + p['th'], thumb_width(p), base + p['sm'], small_w, base + p['file'], p['w'], CARD_PHONE_SIZES))


def cover_img(t, here, sizes, eager=False, cls='', list_sizes=None):
    """The trip's cover (content.resolve_cover) as one <img class="cover-img">, cropped by CSS (object-fit: cover) around
    its focal point. eager=True marks the page's lead image (no lazy loading, fetchpriority high; pair with
    cover_preload()). A card cover that has a .th copy is wrapped in <picture class="cover-pic"> with the phone-only
    <source> of _card_source (the picture has no box of its own: base.css). list_sizes: the slot of the explorer's list
    view, whose thumbnail is at most 200 px wide; the image then also carries data-srcset-list (the .th copy, the .sm copy
    and the full file) and data-sizes-list, which trips.js puts in place of srcset and sizes while the list view is on,
    and takes back for the cards. The card view's own candidates stay as they are (the .th copy is never one of them:
    a 400 px card slot would take it and look soft). '' when the trip has no photo."""
    c = t.get('cover')
    if not c:
        return ''
    p = c['photo']
    sizes = phone_sizes(sizes, p)
    src, srcset = _cover_srcset(t, p, here)
    x, y = c['focal']
    pos = (' style="object-position:%s%% %s%%"' % (_pct(x), _pct(y))) if (x, y) != (50.0, 50.0) else ''
    wh = (' width="%d" height="%d"' % (p['w'], p['h'])) if (p.get('w') and p.get('h')) else ''
    listed = ''
    if list_sizes and srcset and p.get('th'):
        listed = (' data-srcset-list="%s %dw, %s" data-sizes-list="%s"'
                  % (link(here, t['url']) + p['th'], thumb_width(p), srcset, list_sizes))
    img = ('<img class="cover-img%s" src="%s"%s%s alt="%s" decoding="async"%s%s%s>'
           % ((' ' + cls) if cls else '', src, (' srcset="%s" sizes="%s"' % (srcset, sizes)) if srcset else '', wh,
              esc(p.get('alt') or ''), ' fetchpriority="high"' if eager else ' loading="lazy"', pos, listed))
    source = '' if eager else _card_source(t, p, here, sizes)
    return ('<picture class="cover-pic">%s%s</picture>' % (source, img)) if source else img


def cover_preload(t, here, sizes):
    """<link rel="preload"> for the lead cover (the page's LCP image), so it is requested before the stylesheet lands."""
    c = t.get('cover')
    if not c:
        return ''
    sizes = phone_sizes(sizes, c['photo'])   # as cover_img: the preload must name the candidate the image takes
    src, srcset = _cover_srcset(t, c['photo'], here)
    if srcset:
        return '<link rel="preload" as="image" href="%s" imagesrcset="%s" imagesizes="%s" fetchpriority="high">' % (src, srcset, sizes)
    return '<link rel="preload" as="image" href="%s" fetchpriority="high">' % src


def photo_ar(p):
    return (p['w'] / float(p['h'])) if p.get('w') and p.get('h') else 1.5


def photo_partition(photos, per_row=4):
    """Rows for photo_rows(), in photo order. Each landscape (w >= h) is its own row; a run of portraits splits into
    balanced rows of <= per_row (5 -> 3+2, 6 -> 3+3, 7 -> 4+3); a portrait row of 1-2 photos then joins an adjacent
    single-landscape row: the previous one unless it already took a row, else the next one."""
    rows, run = [], []

    def flush():
        if not run:
            return
        k = -(-len(run) // per_row)
        size, extra = divmod(len(run), k)
        i = 0
        for r in range(k):
            m = size + (1 if r < extra else 0)
            rows.append({'ph': run[i:i + m], 'land': False, 'took': False})
            i += m
        del run[:]
    for p in photos:
        if photo_ar(p) >= 1:
            flush()
            rows.append({'ph': [p], 'land': True, 'took': False})
        else:
            run.append(p)
    flush()
    single = lambda r: r is not None and r['land'] and not r['took'] and len(r['ph']) == 1  # noqa: E731
    out = []
    for i, r in enumerate(rows):
        if not r['land'] and len(r['ph']) <= 2:
            prev = out[-1] if out else None
            nxt = rows[i + 1] if i + 1 < len(rows) else None
            if single(prev):
                prev['ph'] = prev['ph'] + r['ph']
                prev['took'] = True
                continue
            if single(nxt):
                nxt['ph'] = r['ph'] + nxt['ph']
                nxt['took'] = True
                continue
        out.append(r)
    return [r['ph'] for r in out]


def photo_rows(t, here, photos, per_row=4, ns='ph', col=1248, jmax=624, jmin=280, gap=24, lead=0):
    """Justified photo rows (reports, multi-day chapters): every row fills the column at one height (1248: a landscape
    alone 1248×624, four portraits 294×392), clamped in CSS so a row of portraits never runs taller than 624. Phones
    (< 760) show a 2-column grid: landscapes and unpaired portraits full width. Each photo links to its full-size file
    (the lightbox opens it in-page; data-cap carries a caption when the content has one).
    col / jmax / jmin / gap: the desktop column and the CSS clamp (.jrows --jmax / --jmin / --jgap) of the page, so each
    image's sizes attribute declares the width it is drawn at (a 294px portrait picks the 800px .sm file).
    lead: how many of the trip's photos sit above the grid in the same viewer group (a story's lead photo: 1), so a photo
    without alt text is numbered as the viewer numbers it ('Photo 2 of 7' for the first one in the grid)."""
    photos = [p for p in photos if p.get('file')]
    if not photos:
        return ''
    base = link(here, t['url'])
    out = []
    k = 0
    for row in photo_partition(photos, per_row):
        ars = [photo_ar(p) for p in row]
        # math.fsum, not sum(): Python 3.12's sum() rounds a float total differently from 3.9's, and CI (3.12) would then
        # print a different fourth decimal than a local build (3.9) for the same photos
        tot = math.fsum(ars)
        lone_land = len(row) == 1 and ars[0] >= 1
        one = len(row) == 1 and not lone_land
        # drawn height at >= 1200: the row's natural height, never below jmin (object-fit: cover then crops the sides); a row
        # clamped at jmax still fills the column (the photos flex-grow), so its widths stay the natural ones
        h = max((col - gap * (len(row) - 1)) / tot, jmin)
        # portraits pair up in order within the row (phones show a pair side by side); an odd one out is 'solo'
        port = [i for i, a in enumerate(ars) if a < 1]
        solo = set(port[len(port) - (len(port) % 2):])
        figs = []
        for i, (p, a) in enumerate(zip(row, ars)):
            k += 1
            land = a >= 1
            if lone_land:
                sizes = '(min-width: 1200px) %dpx, %s' % (col, PHONE_FULL)
            elif one:
                sizes = '(min-width: 760px) %dpx, %s' % (round(min(col, a * jmax)), PHONE_FULL)  # .jrow--one: min(100%, ar × jmax)
            else:
                sizes = ('(min-width: 1200px) %dpx, (min-width: 760px) calc((100vw - 80px) * %.3f), %s'
                         % (round(a * h), a / tot, PHONE_FULL if (land or i in solo) else '50vw'))
            c = 'jph jph--%s%s' % ('l' if land else 'p', ' jph--solo' if i in solo else '')
            name = '' if p.get('alt') else ' aria-label="Photo %d of %d, full size"' % (k + lead, len(photos) + lead)
            cap = (' data-cap="%s"' % esc(p['caption'])) if p.get('caption') else ''
            figs.append('<a class="%s" href="%s%s" style="--ar:%.4f;--fg:%d"%s%s>%s</a>'
                        % (c, base, p['file'], a, round(a * 1000), cap, name, photo(t, p, here, sizes=sizes, caption=False)))
        out.append('<div class="jrow%s" style="--n:%d;--sum:%.4f;--ar:%.4f">%s</div>'
                   % (' jrow--one' if one else '', len(row), tot, ars[0], ''.join(figs)))
        caps = [p['caption'] for p in row if p.get('caption')]
        if caps:
            out.append('<p class="t-small jcap">%s</p>' % ' · '.join(esc(c) for c in caps))
    return '<div class="jrows">%s</div>' % ''.join(out)


# ---------------------------------------------------------------- data strip (reports + featured blocks)

def dx(html_):
    """Data-XL punctuation: tighten the , . : between digits ('11,952', '12.8', '6:34')."""
    return re.sub(r'(?<=\d)([,.:])(?=\d)', r'<span class="dx-p">\1</span>', html_)


def is_flat(t):
    """Flat water: paddling sub-types (SUP, Kayaking), or any 'other' trip whose track has under 30 m of relief (high minus
    low). render.py uses the identical rule to choose the speed chart, so the list cells, strip and chart always agree:
    pace + speed chart instead of gain / GPS max / profile."""
    if t['activity'] != 'other':
        return False
    st = t['stats']
    return t.get('subtype') in ('SUP', 'Kayaking') or ((st.get('high_m') or 0) - (st.get('low_m') or 0)) < 30


def beta_value(t, label):
    for b in t['beta']:
        if str(b.get('label', '')).lower() == label.lower():
            return str(b.get('value', ''))
    return ''


def _plural(k, word):
    return '%s %s' % (n(k), word if k == 1 else word + 'S')


def _cell_dist(st):
    mi, km = dist_vals(st.get('distance_km'))
    if not mi:
        return None
    return ('Distance', U(mi, km, 'mi', 'km'), U_sub(mi, km, 'mi', 'km'))


def _cell_m(lab, m):
    if m is None:
        return None
    return (lab, U(n(m * FT), n(m), 'ft', 'm'), U_sub(n(m * FT), n(m), 'ft', 'm'))


def _cell_moving(t):
    st = t['stats']
    if not st.get('moving_s'):
        return None
    sub = nb('Start ' + ftime(t['start_time'])) if t.get('start_time') else ''
    return ('Moving', '%s<span class="unit">h:mm</span>' % hm(st['moving_s']), sub)


def _pace(st):
    """(min per mile, min per km) from moving time and distance."""
    mins = st['moving_s'] / 60.0
    return mins / (st['distance_km'] * 1000 / MI), mins / st['distance_km']


def strip_cells(t):
    """Data-strip cells [(label, value html, sub-line)] for a single-day report or a featured block (only values the content has).
    Climbing leads with Pitches / N ROUTES from the beta; flat water is Distance · Moving · Avg pace; MTB adds Avg speed."""
    st = t['stats']
    act = t['activity']
    cells = []
    if act == 'climb':
        p = beta_value(t, 'Pitches')
        if p:
            routes = [r for r in beta_value(t, 'Routes').split(',') if r.strip()]
            cells.append(('Pitches', esc(p), _plural(len(routes), 'ROUTE') if routes else ''))
        cells += [_cell_dist(st), _cell_m('GPS max', st.get('high_m')), _cell_moving(t)]
    elif is_flat(t):
        cells += [_cell_dist(st), _cell_moving(t)]
        if st.get('distance_km') and st.get('moving_s'):
            per_mi, per_km = _pace(st)
            cells.append(('Avg pace', U(n(per_mi), n(per_km), 'min/mi', 'min/km'),
                          meta_items([U_sub(n(per_mi), n(per_km), 'min/mi', 'min/km'), 'MOVING'])))
    else:
        cells += [_cell_dist(st), _cell_m('Gain', st.get('gain_m')), _cell_m('GPS max', st.get('high_m')), _cell_moving(t)]
        if act == 'mtb' and st.get('distance_km') and st.get('moving_s'):
            h = st['moving_s'] / 3600.0
            mph, kmh = st['distance_km'] * 1000 / MI / h, st['distance_km'] / h
            cells.append(('Avg speed', U('%.1f' % mph, '%.1f' % kmh, 'mph', 'km/h'),
                          meta_items([U_sub('%.1f' % mph, '%.1f' % kmh, 'mph', 'km/h'), 'MOVING'])))
    return [c for c in cells if c]


def strip(cells, cls='', label='Trip stats'):
    """The Datum data strip: Label / Data-XL value (tightened punctuation) / Mono-S sub-line per cell. Five cells get
    .strip--5 (tighter tablet padding and values, base.css)."""
    cls = ' '.join(x for x in (cls.strip(), 'strip--5' if len(cells) == 5 else '') if x)
    out = ''.join('<div class="strip-c"><dt class="t-label">%s</dt><dd class="t-data-xl strip-v">%s</dd>%s</div>'
                  % (lab, dx(val), ('<dd class="t-mono-s strip-s">%s</dd>' % sub) if sub else '') for lab, val, sub in cells)
    return ('<dl class="strip%s" style="--cells:%d" aria-label="%s">%s</dl>'
            % ((' ' + cls) if cls else '', max(len(cells), 1), esc(label), out))


def has_track(t):
    """True when the trip publishes a recording: its own track.gpx, or a day's. What a page says about "the recording"
    or "the GPX file", and every control that leads to one, depends on this."""
    return bool(t.get('track')) or any(d.get('track') for d in t.get('days') or [])


def stats_note(t, cls=''):
    """The one stats footnote under a strip (source, track note from the beta, how derived values are computed). A
    report without a track says nothing about a recording or a GPX file; '' when nothing is left to say."""
    recorded = has_track(t)
    bits = ['Stats from the GPS recording via Strava.'] if recorded else []
    track = beta_value(t, 'Track')
    if track:
        bits.append('Track: %s.' % esc(track.rstrip('.')))
    st = t['stats']
    derived = bool(st.get('distance_km') and st.get('moving_s'))   # strip_cells shows pace / average speed only then
    if is_flat(t):
        if derived:
            bits.append('Pace is moving time divided by distance.')
    else:
        if t['activity'] == 'mtb' and derived:
            bits.append('Average speed is distance divided by moving time.')
        if recorded:
            bits.append('GPS max is the highest point in the GPX file, not a surveyed summit height.')
    if not bits:
        return ''
    return '<p class="strip-note%s">%s</p>' % ((' ' + cls) if cls else '', ' '.join(bits))


# ---------------------------------------------------------------- trip lists

def stats_cells(t):
    """List-row stats at Data-M, in the data strip's activity order (no sub-lines): climbing Pitches (from the beta, when
    present) · Dist · GPS max · Moving; flat water Dist · Moving · Avg pace; everything else Dist · Gain · GPS max · Moving."""
    st = t['stats']
    a = approx(t)
    hi = 'High point' if a else 'GPS max'   # a plan was never recorded by a GPS: its top is the highest point of the file
    mi, km = dist_vals(st.get('distance_km'))
    dist = ('Dist', U(a + mi, a + km, ' mi', ' km')) if mi else None

    def elev_cell(lab, v):
        return (lab, U(a + n(v * FT), a + n(v), ' ft', ' m')) if v is not None else None
    moving = ('Moving', hm(st['moving_s']) + '<span class="unit u-hm"> h:mm</span>') if st.get('moving_s') else None
    if t['activity'] == 'climb':
        p = beta_value(t, 'Pitches')
        cells = [('Pitches', esc(p)) if p else None, dist, elev_cell(hi, st.get('high_m')), moving]
    elif is_flat(t):
        pace = None
        if st.get('distance_km') and st.get('moving_s'):
            per_mi, per_km = _pace(st)
            pace = ('Avg pace', U(n(per_mi), n(per_km), ' min/mi', ' min/km'))
        cells = [dist, moving, pace]
    else:
        cells = [dist, elev_cell('Gain', st.get('gain_m')), elev_cell(hi, st.get('high_m')), moving]
    return ''.join('<div class="sc"><dt class="t-label">%s</dt><dd class="t-data-m">%s</dd></div>' % c for c in cells if c)


def excerpt_parts(t, limit=180):
    """(label, text): label is '' when the trip has its own write-up, else 'DAY 5 · TITLE' of the first written day."""
    if t['body_md']:
        return '', markdown.plain_sentences(t['body_md'], limit)
    d = next((d for d in t['days'] if d['body_md']), None)
    if not d:
        return '', ''
    title = (d.get('title') or '').strip()
    if re.fullmatch(r'day\s*%s' % re.escape(str(d['label'])), title, re.I):
        title = ''  # a day titled just 'Day 4' would read 'DAY 4 · DAY 4'
    lab = 'DAY %s' % esc(str(d['label'])) + ((' · ' + esc(title).upper()) if title else '')
    return lab, markdown.plain_sentences(d['body_md'], limit)


def excerpt(t, limit=180):
    return excerpt_parts(t, limit)[1]


def card_summary(t, limit=180, series_day=False):
    """The short text a card shows for a trip, with its provenance: {'text', 'source_kind', 'source_label'}.

    1. an explicit card_summary from the front matter (verbatim)            -> 'explicit'
    2. the start of the trip's own write-up                                   -> 'report'
    3. multi-day trips (and a series only when series_day=True): the first
       written day's excerpt, always with its 'DAY N · TITLE' label           -> 'day'
    4. a series (by default), or a multi-day trip with no writing: a neutral
       line from the fields only ('Journal of 150 recorded days, ...')        -> 'facts'
    5. nothing (a track-only single-day trip)                                 -> None
    A series never passes one day's anecdote off as the whole journal, and nothing here is ever written about Eric."""
    if t.get('card_summary'):
        return {'text': t['card_summary'], 'source_kind': 'explicit', 'source_label': ''}
    if t['body_md']:
        return {'text': markdown.plain_sentences(t['body_md'], limit), 'source_kind': 'report', 'source_label': ''}
    if t['days'] and (t['kind'] == 'multi-day' or (t['kind'] == 'series' and series_day)):
        lab, ex = excerpt_parts(t, limit)
        if ex:
            return {'text': ex, 'source_kind': 'day', 'source_label': lab}
    if t['kind'] == 'series':
        k = sum(1 for d in t['days'] if d.get('track'))
        bits = [('Journal of %s recorded day%s' % (n(k), '' if k == 1 else 's')) if k else 'Journal', frange(t['date'], t.get('end_date'))]
        if t.get('place'):
            bits.append(t['place'])
        return {'text': ', '.join(b for b in bits if b) + '.', 'source_kind': 'facts', 'source_label': ''}
    if t['kind'] == 'multi-day' and t['days']:
        bits = ['%d-day %s trip' % (len(t['days']), act_word(t).lower()), frange(t['date'], t.get('end_date'))]
        return {'text': ', '.join(b for b in bits if b) + '.', 'source_kind': 'facts', 'source_label': ''}
    return {'text': '', 'source_kind': None, 'source_label': ''}


def day_ruler(t):
    """Multi-day rows: one bar per day, widths proportional to that day's distance, labelled D1…DN (SkiIndex artboard)."""
    if t['kind'] != 'multi-day' or len(t['days']) < 2:
        return ''
    ds = [d['stats'].get('distance_km') or 0 for d in t['days']]
    if not sum(ds):
        return ''
    return ('<div class="trow-dr" aria-hidden="true">%s</div>'
            % ''.join('<span style="flex-grow:%.2f">D%s</span>' % (v, esc(str(d['label']))) for v, d in zip(ds, t['days'])))


def row_stats_line(t):
    """The phone list row's Mono-S stats line (it replaces the 4-cell stat grid below 560): climbing '3 PITCHES · 1.2 MI',
    flat water '3.1 MI · 1:05 MOVING', everything else plain_stats() ('7.9 MI · 2,930 FT GAIN')."""
    st = t['stats']
    a = approx(t)
    if t['activity'] == 'climb':
        mi, km = dist_vals(st.get('distance_km'))
        p = beta_value(t, 'Pitches').strip()
        return meta_items([nb(esc('%s PITCH%s' % (p, '' if p == '1' else 'ES'))) if p else '',
                           U(nb(a + mi + ' MI'), nb(a + km + ' KM')) if mi else ''])
    if is_flat(t):
        mi, km = dist_vals(st.get('distance_km'))
        return meta_items([U(nb(a + mi + ' MI'), nb(a + km + ' KM')) if mi else '',
                           nb(hm(st['moving_s']) + ' MOVING') if st.get('moving_s') else ''])
    return meta_items(plain_stats(t, items=True))


def trip_row(t, here, ns='', filter_key=None, cls=''):
    """Index list row (one component everywhere): 200×152 tile · Mono-S meta (date · place · route shape, a meta_items()
    line: phones drop the shape, 560–1199 break after the date) · H3 · status tags · activity-aware stats · day ruler
    (multi-day) · two-line excerpt. The region lives in breadcrumbs, table title cells and map tabs, so the row names
    only the place (the region when there is no place).
    A single-day or planned row with no excerpt is .trow--brief: a 120px tile in the same column (titles keep one x) and a
    tighter row. Phones (< 560) show a Mono-S stats line (.trow-ps) instead of the stat grid. The link is named by the
    title, then the meta line, so repeated titles ('Ride near Day Valley') stay distinct."""
    href = link(here, t['url'])
    k = ns + t['slug']
    date_ = 'PLANNED ROUTE' if t['kind'] == 'planned' else trip_date(t)
    loc = t.get('place') or t.get('region') or ''
    shape = SHAPE_CAPS.get(t['route_shape'], esc(t['route_shape']).upper()) if t.get('route_shape') else ''
    meta = meta_items([date_, (nb(esc(loc).upper()), 'trow-loc') if loc else '', (shape, 'trow-shape') if shape else ''], br_after=0)
    lab, ex = excerpt_parts(t)
    exh = ''
    if ex:
        exh = (('<p class="t-label trow-exl">%s</p>' % lab) if lab else '') + '<p class="t-excerpt trow-ex">%s</p>' % esc(ex)
    brief = not ex and t['kind'] in ('trip', 'planned')
    c = ' '.join(x for x in (cls.strip(), 'trow--brief' if brief else '') if x)
    ps = row_stats_line(t)
    return ('<li class="trow%s" data-key="%s"%s><a class="trow-a" href="%s" aria-labelledby="tt-%s tm-%s">'
            '<div class="trow-tile" aria-hidden="true">%s</div><div class="trow-body">'
            '<p class="t-mono-s trow-meta" id="tm-%s">%s</p><h3 class="t-h3 trow-t" id="tt-%s">%s</h3>%s'
            '<div class="trow-tags">%s</div><dl class="trow-stats">%s</dl>%s%s</div></a></li>'
            % ((' ' + c) if c else '', t['slug'], (' data-f="%s"' % esc(filter_key)) if filter_key is not None else '',
               href, k, k, tile(t, here), k, meta, k, title_html(t['title']),
               ('<p class="t-mono-s trow-ps">%s</p>' % ps) if ps else '',
               trip_tags(t, shape=False, status=t['kind'] != 'planned'), stats_cells(t), day_ruler(t), exh))


TABLE_UNITS = (('Dist', 'mi', 'km'), ('Gain', 'ft', 'm'), ('GPS max', 'ft', 'm'))


def table_head():
    """Visual header of the report table (rows are links, so the header is hidden from assistive tech; cells speak their units)."""
    nums = ''.join('<span class="num">%s <span class="u"><span class="u-mi">%s</span><span class="u-km">%s</span></span></span>' % u
                   for u in TABLE_UNITS)
    return ('<div class="rtab-h" aria-hidden="true"><span>Track</span><span>Activity</span><span>Title</span><span>Date</span>%s</div>'
            % nums)


def table_row(t, here, cls='', tags='', attrs=''):
    """Report-table row as a list-item link (put rows in <ol class="rtab-rows">): glyph · activity · title (+ tags, place) ·
    date · dist · gain · GPS max. No ARIA table roles. Numbers carry spoken units; the activity cell is visual only and the
    word is spoken from the title cell, so it is read once whether or not the Activity column is shown. Flat water has no
    meaningful gain or high point, so those cells read '—' (climbing keeps the GPX numbers). data-act colours the phone
    compact row's icon (.rtab--compact); .rtab-nodist marks a row without a distance."""
    st = t['stats']
    mi, km = dist_vals(st.get('distance_km'))
    loc = ', '.join(x for x in (t.get('place'), t.get('region')) if x)
    none = '<span aria-hidden="true">—</span><span class="sr">none</span>'
    flat = is_flat(t)
    a = approx(t)   # a tick-list goal's row: '≈' before each number, spoken as 'about'

    def num(lab, v, imp, met):
        if not v:
            return '<span class="num"><span class="sr">%s </span>%s</span>' % (lab, none)
        ap = '<span aria-hidden="true">≈ </span><span class="sr">about </span>' if a else ''
        return ('<span class="num"><span class="sr">%s </span>%s</span>'
                % (lab, U(ap + v[0] + '<span class="sr"> %s</span>' % imp, ap + v[1] + '<span class="sr"> %s</span>' % met)))
    g = lambda v: (n(v * FT), n(v)) if (v is not None and not flat) else None  # noqa: E731
    when = trip_date(t, short=True)
    c = ' '.join(x for x in (cls.strip(), '' if mi else 'rtab-nodist') if x)
    return ('<li><a class="rtab-r%s" href="%s" data-key="%s" data-act="%s"%s>'
            '<span class="rtab-g" aria-hidden="true">%s</span>'
            '<span class="rtab-act" aria-hidden="true">%s</span>'
            '<span class="rtab-title"><span class="rtab-tt">%s</span><span class="sr">, %s</span>%s<span class="t-mono-s rtab-loc">%s</span></span>'
            '<span class="t-mono-s rtab-date">%s</span>%s%s%s</a></li>'
            % ((' ' + c) if c else '', link(here, t['url']), t['slug'], t['activity'], attrs,
               glyph(t, here, 'g112', 'g-' + t['slug']), chip(t, variant='inline', swatch=False),
               title_html(t['title']), esc(act_word(t)), tags, esc(loc).upper(), when,
               num('Distance', (mi, km) if mi else None, 'miles', 'kilometers'),
               num('Gain', g(st.get('gain_m')), 'feet', 'meters'),
               num('High point' if a else 'GPS max', g(st.get('high_m')), 'feet', 'meters')))


def phone_row(t, here):
    st = t['stats']
    mi, km = dist_vals(st.get('distance_km'))
    bits = [trip_date(t, short=True)]
    if mi:
        bits.append(U(nb(mi + ' MI'), nb(km + ' KM')))
    return ('<li class="prow"><a href="%s">%s<span class="prow-b"><span class="prow-t">%s</span>'
            '<span class="t-mono-s prow-m">%s%s</span></span>%s</a></li>'
            % (link(here, t['url']), glyph(t, here, 'g64', 'pg-' + t['slug']), esc(t['title']), icon(act_icon(t), 14),
               meta_items(bits), icon('chevron-right', 20)))


def repeated_titles(ts):
    """The titles (case-folded) more than one of these trips carries: their cards name the date as well (trip_card)."""
    seen = {}
    for x in ts:
        seen[x['title'].casefold()] = seen.get(x['title'].casefold(), 0) + 1
    return {k for k, v in seen.items() if v > 1}


def trip_card(t, here, sizes, ns='tc', cls='', summary=False, repeated=(), list_sizes=None):
    """One trip as a card (home's recent outings, the trips/ explorer): the cover (core.cover_img), else the route tile,
    else the activity disc; DATE · PLACE; the H3 title link, described by that line (repeated titles such as 'Tallac'
    stay distinct); the inline activity chip, status tags and the Mono-S stats line; and, with summary=True, the card
    summary (core.card_summary) unless it is only facts. The photo link is skipped by keyboards and readers: the title
    link is the card's name. repeated: the case-folded titles that more than one card of the page carries
    (repeated_titles); such a card's link also names its date, for readers (a links list does not read the
    aria-describedby line). list_sizes: cover_img's list-view slot (the explorer). data-* attributes carry the facets
    trips.js filters and sorts on: region as its map-anchor slug, month 'MM', distance in km to one decimal, gain in
    metres, the number of photos (the trip's own and its days'); '' where the content has no value."""
    href = link(here, t['url'])
    img = cover_img(t, here, sizes, list_sizes=list_sizes)
    if img:
        media = '<a class="tcard-img" href="%s" tabindex="-1" aria-hidden="true">%s</a>' % (href, img)
    else:
        tl = tile(t, here)
        if tl:
            media = '<a class="tcard-img tcard-img--tile" href="%s" tabindex="-1" aria-hidden="true">%s</a>' % (href, tl)
        else:
            media = '<div class="tcard-img tcard-img--none" aria-hidden="true">%s</div>' % disc(t['activity'], 32, t.get('subtype'))
    loc = t.get('place') or t.get('region') or ''
    # the place may wrap at its spaces when it alone is wider than the card's text column (a 320 px phone)
    meta = meta_items([trip_date(t, short=True), (esc(loc).upper(), 'mi-w') if loc else ''])
    mid = '%s-%s-m' % (ns, t['slug'])
    stats = row_stats_line(t)
    ex = ''
    if summary:
        sm = card_summary(t)
        if sm['text'] and sm['source_kind'] != 'facts':
            ex = ((('<p class="t-label tcard-exl">%s</p>' % sm['source_label']) if sm['source_label'] else '')
                  + '<p class="t-excerpt tcard-ex">%s</p>' % esc(sm['text']))
    st = t.get('stats') or {}
    km, gain = st.get('distance_km'), st.get('gain_m')
    photos = len(t['photos']) + sum(len(d['photos']) for d in t['days'])
    from sitegen import search as _s
    months = ' '.join('%02d' % m for m in _s.trip_months(t))     # every month the trip spans: the Month filter
    data = (' data-slug="%s" data-act="%s" data-kind="%s" data-region="%s" data-year="%s" data-month="%s" data-writeup="%s"'
            ' data-photos="%d" data-km="%s" data-gain="%s" data-date="%s"'
            % (esc(t['slug']), t['activity'], t['kind'], content.slugify(t['region']) if t.get('region') else '',
               t['date'].year if t['date'] else '', months, '1' if t['has_writeup'] else '0',
               photos, ('%.1f' % km) if isinstance(km, (int, float)) else '', str(int(round(gain))) if isinstance(gain, (int, float)) else '',
               t['date'].isoformat() if t['date'] else ''))
    when = trip_date(t, caps=False, short=True) if (t['title'].casefold() in repeated and t['date']) else ''
    return ('<li class="tcard%s"%s>%s<div class="tcard-b"><p class="t-mono-s tcard-meta" id="%s">%s</p>'
            '<h3 class="tcard-t"><a href="%s" aria-describedby="%s">%s%s</a></h3>'
            '<div class="tcard-act">%s%s%s</div>%s</div></li>'
            % ((' ' + cls) if cls else '', data, media, mid, meta, href, mid, title_html(t['title']),
               ('<span class="sr">, %s</span>' % when) if when else '',
               chip(t, variant='inline'), trip_tags(t, shape=False),
               ('<p class="t-mono-s tcard-ps">%s</p>' % stats) if stats else '', ex))


RELATED_SIZES = '(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2), 112px'


_NAME_WORDS = [None, frozenset()]   # [the published list they were worked out from, the words]: held, so never a reused id
NAME_MIN = 5   # a title word pairs two trips only when it is this long and the proper part of some place: or peak name
NAME_MAX = 2   # ... and names no more than this many different places (a word in many names is a kind of place, not one)
# the generic part of a place name ('Mount Tallac', 'Sawtooth Ridge'): never the word that makes two trips one place
NAME_GENERIC = frozenset('mount mountain mountains peak peaks ridge ridges lake lakes creek canyon valley basin range pass '
                         'point falls river shore trail trails grade forest ranch county national state park summit '
                         'meadow meadows north south east west upper lower little wilderness village'.split())


def name_words(site):
    """The words that can pair two trips by their titles: the words of every place: and map: peaks value of the published
    reports, normalised (search.normalize), of NAME_MIN letters or more, not a generic part of a name (NAME_GENERIC) and
    found in no more than NAME_MAX different names. 'tallac' (Mount Tallac) is one; 'mount', 'ridge', 'south' or 'season'
    never are. Worked out once per site."""
    from sitegen import search as _s
    if _NAME_WORDS[0] is not site['published']:
        names = set()
        for x in site['published']:
            for nm in [x.get('place') or ''] + [p for p in ((x.get('map') or {}).get('peaks') or []) if isinstance(p, str)]:
                if _s.normalize(nm):
                    names.add(_s.normalize(nm))
        seen = {}
        for nm in names:
            for w in set(nm.split()):
                seen[w] = seen.get(w, 0) + 1
        _NAME_WORDS[:] = [site['published'], frozenset(w for w, k in seen.items() if len(w) >= NAME_MIN and not w.isdigit()
                                                       and w not in NAME_GENERIC and k <= NAME_MAX)]
    return _NAME_WORDS[1]


def same_name(t, x, words):
    """t and x share a place (case-folded), a named peak, or a title word that is a place or peak word (name_words)."""
    from sitegen import search as _s
    if t.get('place') and x.get('place') and t['place'].strip().casefold() == x['place'].strip().casefold():
        return True
    peaks = lambda y: {p.strip().casefold() for p in ((y.get('map') or {}).get('peaks') or []) if isinstance(p, str)}  # noqa: E731
    if peaks(t) & peaks(x):
        return True
    return bool(set(_s.normalize(t['title']).split()) & set(_s.normalize(x['title']).split()) & words)


def related(t, site, k=3, skip=()):
    """Up to k published reports to read next, by one transparent rule. Candidates share t's region or its activity; they
    are ordered: same activity and the same place or name (same_name: a shared place, peak, or title word that names a
    place somewhere on the site, so two Tallac tours pair while two trips called 'south' do not), then same region and
    same activity, then same region, then same activity; within each, the nearest in date to t first (a trip without a
    date last), then the newer one, then site['published'] order. Never t itself, never a planned route, never a draft
    (never loaded), each slug once. skip: reports the page already links to right beside this list (its Newer / Older
    pager), left out so the page does not offer the same report twice."""
    region, act, when = t.get('region'), t['activity'], t.get('date')
    words = name_words(site)

    def key(ix):
        i, x = ix
        same_region = bool(region) and x.get('region') == region
        same_act = x['activity'] == act
        if same_act and same_name(t, x, words):
            tier = 0
        else:
            tier = 1 if (same_region and same_act) else (2 if same_region else 3)
        d = x.get('date')
        gap = abs((d - when).days) if (d and when) else None
        return (tier, gap is None, gap or 0, -(d.toordinal()) if d else 0, i)
    seen, cands = {t['slug']} | {x['slug'] for x in skip if x}, []
    for i, x in enumerate(site['published']):
        if x['slug'] in seen or x['kind'] == 'planned':
            continue
        if (region and x.get('region') == region) or x['activity'] == act:
            seen.add(x['slug'])
            cands.append((i, x))
    return [x for _i, x in sorted(cands, key=key)[:k]]


def related_block(t, here, site, k=3, skip=()):
    """'More like this': the related() reports as cards (trip_card), or '' when there are none. The meta line states the
    rule, so the choice is never a mystery, and says so when the page's Newer / Older reports were left out. skip: the
    reports of the page's Newer / Older pager (related())."""
    rel = related(t, site, k, skip)
    if not rel:
        return ''
    # the first rule is long: it may wrap after a comma (a phone), never inside a clause
    tiers = (('SAME PLACE OR NAME AND ACTIVITY', 'THEN REGION AND ACTIVITY', 'THEN REGION', 'THEN ACTIVITY') if t.get('region')
             else ('SAME PLACE OR NAME AND ACTIVITY', 'THEN ACTIVITY'))
    rule = [', '.join(nb(c) for c in tiers), nb('NEAREST IN DATE')]
    if any(skip):
        rule.append(nb('NEWER / OLDER NOT REPEATED'))
    return ('<section class="rep-related wrap sec" aria-labelledby="rel-h"><div class="shead"><h2 class="shead-t" id="rel-h">More like this</h2>'
            '<span class="shead-m t-mono-s">%s</span></div><ul class="rep-rel tgrid">%s</ul></section>'
            % (meta_items(rule), ''.join(trip_card(x, here, RELATED_SIZES, ns='rel') for x in rel)))


def copy_link(url, label='Copy link', cls='btn', of=''):
    """A copy-to-clipboard control for an absolute url (base.js). On success 'Link copied' shows under the button for a
    few seconds; when the clipboard is unavailable the url appears there in a read-only, selected field to copy by hand.
    Both hang out of the flow (report.css), so the row the control sits in never moves. `of` names what the link is to
    ('Day 3') for assistive technology, on a page that repeats the same label. The status is its own element after the
    button and is always rendered: a live region that appears together with its text is not reliably announced. With
    scripting off the control is not shown (report.css): the address bar already holds the page's URL."""
    more = '<span class="sr">, %s</span>' % esc(of) if of else ''
    return ('<span class="copy"><button type="button" class="%s copy-btn" data-copy="%s">%s<span>%s</span>%s</button>'
            '<span class="copy-msg t-small" role="status"></span></span>' % (cls, esc(url), icon('link', 18), esc(label), more))


def goal_tags(goal):
    """A goal's status tag (Idea … Completed), its priority when not normal, and Archived when archived."""
    import goals
    out = [tag(goals.STATUS_LABELS.get(goal['status'], goal['status']))]
    if goal['priority'] != 'normal':
        out.append(tag(goals.PRIORITY_LABELS[goal['priority']]))
    if goal['archived']:
        out.append(tag('Archived'))
    return ''.join(out)


def goal_stats_line(t):
    """'≈ 12.3 MI · ≈ 2,100 FT GAIN' (gain only when the file had full elevation; a legacy goal shows what its front matter
    says), 'ROUTE NOT ADDED' with no track."""
    if not t['track']:
        return meta_items([nb('ROUTE NOT ADDED')])
    st = t['stats']
    mi, km = dist_vals(st.get('distance_km'))
    items = []
    if mi:
        items.append(U(nb('≈ ' + mi + ' MI'), nb('≈ ' + km + ' KM')))
    if st.get('gain_m') is not None:
        items.append(U(nb('≈ ' + n(st['gain_m'] * FT) + ' FT GAIN'), nb('≈ ' + n(st['gain_m']) + ' M GAIN')))
    return meta_items(items)


def goal_card(t, here):
    """A tick-list goal as a map-led card: the route tile (else 'Map not rendered yet' with a track, 'Route not added yet'
    without), REGION / PLACE · ACTIVITY, the H3 title link (described by that line), status / priority / archived tags,
    the approximate stats line and a 'View goal' link. data-* carries the facets ticklist.js filters on; data-text is the
    normalised searchable text (title, place, region, tags, why, and the opening of the planning notes, which the goal page
    publishes). No input of any kind: the public list is read-only."""
    import content as _c
    from sitegen import search as _s
    g = t['goal']
    href = link(here, t['url'])
    tl = tile(t, here)
    if tl:
        media = '<a class="gcard-map" href="%s" tabindex="-1" aria-hidden="true">%s</a>' % (href, tl)
    else:
        media = ('<div class="gcard-map gcard-map--none" aria-hidden="true"><span class="t-mono-s">%s</span></div>'
                 % ('MAP NOT RENDERED YET' if t['track'] else 'ROUTE NOT ADDED YET'))
    loc = t.get('place') or t.get('region') or ''
    meta = meta_items([(nb(esc(loc).upper()), 'mi-w') if loc else '', nb(esc(act_word(t)).upper())])
    mid = 'gc-%s-m' % t['slug']
    notes = markdown.plain(t['body_md'], 600) if t.get('body_md') else ''
    text = _s.normalize(' '.join(x for x in [t['title'], t.get('place') or '', t.get('region') or ''] + g['tags'] + [g['why'], notes] if x))
    data = (' data-slug="%s" data-act="%s" data-region="%s" data-status="%s" data-priority="%s" data-months="%s" data-gpx="%s"'
            ' data-archived="%s" data-added="%s" data-text="%s"'
            % (esc(t['slug']), t['activity'], _c.slugify(t['region']) if t.get('region') else '', g['status'], g['priority'],
               ' '.join(str(m) for m in g['target_months']), '1' if t['track'] else '0', '1' if g['archived'] else '0',
               g['added_at'] or '', esc(text)))
    return ('<li class="gcard"%s>%s<div class="gcard-b"><p class="t-mono-s gcard-meta" id="%s">%s</p>'
            '<h3 class="gcard-t"><a href="%s" aria-describedby="%s">%s</a></h3><div class="chips gcard-tags">%s</div>'
            '<p class="t-mono-s gcard-stats">%s</p><a class="alink gcard-go" href="%s">View goal<span class="sr">: %s</span>%s</a></div></li>'
            % (data, media, mid, meta, href, mid, title_html(t['title']), goal_tags(g), goal_stats_line(t), href, esc(t['title']),
               icon('arrow-right', 16)))


def count_items(ts, planned=0):
    """Mono-S count items for a set of trips: ['23 REPORTS', 'INCL. 1 MULTI-DAY, 1 SERIES', '+ 1 PLANNED ROUTE'] (the last
    two only when present). A multi-day trip or a series counts as one report; planned routes are never counted as
    reports. planned: a number or a list of planned trips. Use with meta_items()."""
    pub = [t for t in ts if t['kind'] != 'planned']
    k_planned = planned if isinstance(planned, int) else len(planned)
    items = [nb(_plural(len(pub), 'REPORT'))]
    incl = []
    md = sum(1 for t in pub if t['kind'] == 'multi-day')
    se = sum(1 for t in pub if t['kind'] == 'series')
    if md:
        incl.append('%d MULTI-DAY' % md)
    if se:
        incl.append('%d SERIES' % se)
    if incl:
        items.append(nb('INCL. ' + ', '.join(incl)))
    if k_planned:
        items.append(nb('+ ' + _plural(k_planned, 'PLANNED ROUTE')))
    return items


def summary(t):
    """Factual one-paragraph summary (meta description, RSS) built only from content fields — never from prose."""
    act = act_word(t)
    st = t['stats']
    mi, _ = dist_vals(st.get('distance_km'))
    where = ', '.join(x for x in (t.get('place'), t.get('region')) if x)
    if t['kind'] == 'planned':
        head = '%s: planned %s route' % (t['title'], act.lower())
        tail = ((' About %s mi, planned GPX download.' % mi) if mi else ' Planned GPX download.') if t.get('track') else ' An idea on the tick list, no route yet.'
        return '%s%s.%s' % (head, (', ' + where) if where else '', tail)
    if t['kind'] == 'series':
        when = frange(t['date'], t.get('end_date'))
        first = '%s series: %s' % (act, ', '.join(x for x in (t['title'], where, when) if x))
        facts = ['%s recorded days' % n(len(t['days']))]
        if mi:
            facts.append('%s mi' % mi)
        if has_track(t):
            facts.append('with map and GPX')
        return '%s. %s.' % (first, ', '.join(facts))
    if t['days']:
        when = frange(t['date'], t.get('end_date'))
        lead = '%d-day %s trip report' % (len(t['days']), act.lower())
    else:
        when = fdate(t['date'])
        lead = ('%s trip report' % act.lower()).capitalize()
    first = '%s: %s' % (lead, ', '.join(x for x in (t['title'], where, when) if x))
    flat = is_flat(t)
    facts = []
    if mi:
        facts.append('%s mi' % mi)
    if not flat and st.get('gain_m') is not None:
        facts.append('%s ft gain' % n(st['gain_m'] * FT))
    if not flat and st.get('high_m') is not None:
        facts.append('GPS max %s ft' % n(st['high_m'] * FT))
    charts = render_meta(t).get('charts', {})
    if not has_track(t):
        pass   # no recording: the page has no map and no download, so the summary promises neither
    elif any(k.startswith('speed-') for k in charts):
        facts.append('with map, speed chart and GPX')
    elif any(k.startswith('profile-') for k in charts):
        facts.append('with map, elevation profile and GPX')
    else:
        facts.append('with map and GPX')
    return ('%s. %s.' % (first, ', '.join(facts))) if facts else (first + '.')


# ---------------------------------------------------------------- layout

def units_control():
    return ('<div class="units" role="radiogroup" aria-label="Units">'
            '<button type="button" role="radio" aria-checked="true" data-units="mi">MI</button>'
            '<button type="button" role="radio" aria-checked="false" data-units="km">KM</button></div>')


_TRIPS_BY_URL = {}
_OTHER_SUBS = []
_HAS_PCT = [False]


def other_subtypes(ts):
    """The sub-types present among published 'other' trips, most reports first, then by name (e.g. ['SUP', 'Rafting']).
    The menu's Other row names exactly these, so it never lists a sub-type with no report."""
    counts = {}
    for t in ts:
        if t['activity'] == 'other' and t['kind'] != 'planned' and t.get('subtype'):
            counts[t['subtype']] = counts.get(t['subtype'], 0) + 1
    return sorted(counts, key=lambda s: (-counts[s], s))


def reveal(el_id):
    """One inline script, placed right after an element that ships `hidden` because it only works with JavaScript (the
    search forms of trips/ and tick-list/). It shows the element while the page is still being parsed, so it is in place
    at first paint and nothing below it jumps when the deferred bundle arrives (measured before: layout shift 0.49 on
    tick-list/ and 0.14 on trips/ on a throttled phone). Without JavaScript the script never runs and the element stays
    hidden. The bundle wires the controls a moment later and adopts anything typed in the meantime."""
    return '<script>document.getElementById("%s").hidden=false</script>' % el_id


_SITE_SHARE = [None]
_IMG_TYPES = {'.webp': 'image/webp', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif'}


def share_photo(t):
    """The photo a shared link to the trip shows: its cover (content.resolve_cover), with the size and the description
    recorded for it in the content, as {'path', 'w', 'h', 'alt'}; None for a trip without a photo. Every page that
    shares a trip's photo takes it from here, so the card, the lead photo and the share image never disagree."""
    c = t.get('cover') if t else None
    if not c:
        return None
    p = c['photo']
    return {'path': t['url'] + p['file'], 'w': p.get('w'), 'h': p.get('h'), 'alt': p.get('alt') or ''}


def site_share():
    """The share image of the pages that stand for the whole site and have no photo of their own (About, Map, Trips,
    Tick list): the cover of the first featured trip in content/home.json, so it follows the author's own choice.
    None when nothing is featured. Never used on a trip page: a report without a photo shares no image."""
    return _SITE_SHARE[0]


def _pixels(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def _share_tags(image):
    """The Open Graph image tags and the Twitter card for a share image: a share_photo() dict, or a site-relative path.
    Width and height are written only when both are recorded, the description only when the photo has alt text:
    nothing is measured or worded here."""
    if not image:
        return '<meta name="twitter:card" content="summary">'
    if isinstance(image, str):
        image = {'path': image}
    out = '<meta property="og:image" content="%s">' % esc(SITE_URL + image['path'])
    kind = _IMG_TYPES.get(os.path.splitext(image['path'])[1].lower())
    if kind:
        out += '<meta property="og:image:type" content="%s">' % kind
    if _pixels(image.get('w')) and _pixels(image.get('h')):
        out += ('<meta property="og:image:width" content="%d"><meta property="og:image:height" content="%d">'
                % (image['w'], image['h']))
    alt = image.get('alt') or ''
    if alt:
        out += '<meta property="og:image:alt" content="%s">' % esc(alt)
    out += '<meta name="twitter:card" content="summary_large_image">'
    if alt:
        out += '<meta name="twitter:image:alt" content="%s">' % esc(alt)
    return out


def written_report(t):
    """True for a page that is one of Eric's written reports, for structured data: a published trip (never a planned
    route) whose own write-ups, as plain text, come to at least STRUCTURED_MIN_CHARS characters across index.md and its
    day files. A caption-length note under a track is not marked up as an article."""
    if not t or t['kind'] == 'planned':
        return False
    text = ' '.join(markdown.plain(b) for b in [t['body_md']] + [d['body_md'] for d in t['days']] if b)
    return len(text) >= STRUCTURED_MIN_CHARS


def blog_posting(t, canon, description, image=None):
    """The schema.org BlogPosting of a written report, from content only: the title as written, the page's own URL and
    description, the one author, the report's own share photo when its size is recorded, and the publication dates
    only when index.md states them (published_at / updated_at). The trip date is not a publication date and never
    appears here; there is no rating, publisher logo or other property the content does not hold."""
    d = {'@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': t['title'], 'url': canon,
         'mainEntityOfPage': {'@type': 'WebPage', '@id': canon}, 'description': description, 'inLanguage': 'en',
         'author': {'@type': 'Person', 'name': AUTHOR_NAME, 'url': AUTHOR_URL}}
    if isinstance(image, dict) and _pixels(image.get('w')) and _pixels(image.get('h')):
        d['image'] = {'@type': 'ImageObject', 'url': SITE_URL + image['path'], 'width': image['w'], 'height': image['h']}
    if t.get('published_at'):
        d['datePublished'] = t['published_at']
    if t.get('updated_at'):
        d['dateModified'] = t['updated_at']
    return d


def _report_head(t, canon, description, image):
    """Head tags only a report page carries: article:published_time / modified_time when index.md states them, and the
    BlogPosting block when the page is a written report. '<' is written as \\u003c so no title can close the script."""
    out = ''
    if t.get('published_at'):
        out += '<meta property="article:published_time" content="%s">' % esc(t['published_at'])
    if t.get('updated_at'):
        out += '<meta property="article:modified_time" content="%s">' % esc(t['updated_at'])
    if written_report(t):
        out += ('<script type="application/ld+json">%s</script>'
                % json.dumps(blog_posting(t, canon, description, image), ensure_ascii=False).replace('<', '\\u003c'))
    return out


def register_site(site, meta=None):
    """build.py hands over the loaded site, so document() can find the trip a page belongs to (the phone app bar's
    glyph + title), the header can name the Other sub-types that exist, and a region link knows which regions have a
    page (region_page_href), without every page module passing them. meta: the site meta (rendered/site/meta.json)
    that decides the region pages; build.py passes the one on disk. Without it no region has a page, so a site
    registered in a test never reads the checkout's own rendered/ folder."""
    _TRIPS_BY_URL.clear()
    _TRIPS_BY_URL.update({t['url']: t for t in site['trips']})
    _HAS_PCT[0] = any(t['slug'] == PCT_SLUG for t in site['trips'])
    feat = site.get('featured') or []
    _SITE_SHARE[0] = share_photo(feat[0]) if feat else None
    _OTHER_SUBS[:] = other_subtypes(site.get('published') or [t for t in site['trips'] if t['kind'] != 'planned'])
    _REGION_PAGES.clear()
    if meta is not None:
        _REGION_PAGES.update({name: slug for name, slug, _ts in region_pages(site, meta)})


def main_nav():
    """[(key, label, url)] of the primary destinations: Trips, Tick list, Map, PCT (when that journal exists), About."""
    out = [('trips', 'Trips', 'trips/'), ('ticklist', 'Tick list', 'tick-list/'), ('map', 'Map', 'map/')]
    if _HAS_PCT[0]:
        out.append(('pct', PCT_LABEL, 'trips/%s/' % PCT_SLUG))
    out.append(('about', 'About', 'about/'))
    return out


def search_form(here, fid):
    """A search box that lands on the explorer: trips/?q=<words>&sort=relevance (the hidden sort is what makes a search
    started here open in Best match order; clearing the box there goes back to Newest). fid: the input's id, unique on
    the page (nav-q in the header, menu-q in the menu). The words are never written back into a page."""
    return ('<form class="nav-search" role="search" aria-label="Search trips" action="%s" method="get">'
            '<label class="sr" for="%s">Search trips</label>'
            '<input class="nav-q" id="%s" name="q" type="search" placeholder="Search" maxlength="200" autocomplete="off">'
            '<input type="hidden" name="sort" value="relevance">'
            '<button class="nav-go" type="submit" aria-label="Search">%s</button></form>'
            % (link(here, 'trips/'), fid, fid, icon('search', 18)))


def header(here, active=None, trip=None):
    """Site header + menu. Main nav: Trips · Tick list · Map · PCT · About, then Search: a search box that lands on the
    explorer (search_form), except on trips/ itself, which has its own box and keeps a link to it. active:
    'trips', 'ticklist', 'goal' (a goal page: Tick list is current as 'true'), 'map', 'about', or an activity key (section,
    report, multi-day and full-screen-map pages: Trips is current as 'true', and the phone menu's activity row as before).
    aria-current="page" only on the page a link points to; the PCT journal page marks PCT alone. The activity pages stay reachable from the phone menu's Reports column, the
    footer and the home page. trip: report, multi-day and series pages get the phone compact app bar (glyph + title,
    shown once the H1 has scrolled under the header; links back to the top)."""
    pct_page = bool(trip) and trip.get('slug') == PCT_SLUG and here == trip.get('url')

    def cur(key, url):
        if key == 'pct':
            state = 'page' if pct_page else None
        elif key == 'ticklist':
            state = 'page' if (active == 'ticklist' and here == url) else ('true' if active in ('ticklist', 'goal') else None)
        elif key == 'trips':
            state = None if pct_page else ('page' if here == url else ('true' if (active == 'trips' or active in ACT) else None))
        elif active == key:
            state = 'page' if here == url else 'true'
        else:
            state = None
        return (' aria-current="%s"' % state) if state else ''
    main = main_nav()
    items = ['<a href="%s"%s>%s</a>' % (link(here, url), cur(key, url), lab) for key, lab, url in main]
    on_trips = here == 'trips/'
    search = ('<a class="nav-search" href="%s">%sSearch</a>' % (link(here, 'trips/#search'), icon('search', 18)) if on_trips
              else search_form(here, 'nav-q'))
    menu_rows = []
    for act, lab in NAV:
        # the 'Other' row names the sub-types that have reports (other_subtypes, via register_site); .ml draws the separators
        sub = ''
        if act == 'other' and _OTHER_SUBS:
            sub = '<span class="menu-sub">%s</span>' % meta_items([nb(esc(SUB_WORD.get(s, s))) for s in _OTHER_SUBS])
        menu_rows.append('<li><a href="%s"%s>%s<span class="menu-w"><span>%s</span>%s</span>%s</a></li>'
                         % (link(here, section_url(act)), cur(act, section_url(act)), disc(act, 32), lab, sub,
                            icon('chevron-right', 20)))
    site_rows = []
    menu_icons = {'trips': 'list', 'ticklist': 'checkbox', 'map': 'map', 'pct': 'HIK', 'about': 'info'}
    for key, lab, url in main + ([('search', 'Search', 'trips/#search')] if on_trips else []):
        word = 'Map &amp; archive' if key == 'map' else lab
        site_rows.append('<li><a href="%s"%s>%s<span class="menu-w"><span>%s</span></span>%s</a></li>'
                         % (link(here, url), cur(key, url) if key != 'search' else '', icon(menu_icons.get(key, 'search'), 24), word,
                            icon('chevron-right', 20)))
    if not on_trips:
        site_rows.append('<li class="menu-search">%s</li>' % search_form(here, 'menu-q'))
    ab = ''
    if trip:
        ab = ('<a class="ab-trip" href="#title" aria-label="Back to top: %s"><span class="ab-g" aria-hidden="true">%s</span>'
              '<span class="ab-t" aria-hidden="true">%s</span></a>' % (esc(trip['title']), glyph(trip, here, 'g64', 'ab'), esc(trip['title'])))
    return ('<a class="skip" href="#main">Skip to content</a>'
            '<header class="site-h"><div class="site-h-in">'
            '<a class="brand" href="%s"><span class="brand-n">%s</span><span class="brand-c">%s</span></a>%s'
            '<nav class="nav" aria-label="Main"><div class="nav-l">%s</div><span class="nav-sep" aria-hidden="true"></span>'
            '<div class="nav-l">%s</div>%s</nav>'
            '<button class="menu-btn" type="button" aria-expanded="false" aria-controls="menu" aria-label="Menu">%s%s</button>'
            '</div>'
            '<div class="menu" id="menu" hidden><nav aria-label="Menu">'
            '<div class="menu-c1"><p class="t-label menu-l">Reports</p><ul class="menu-list">%s</ul></div>'
            '<div class="menu-c2"><p class="t-label menu-l">Site</p><ul class="menu-list menu-list--site">%s</ul>'
            '<div class="menu-units"><span class="t-label">Units</span>%s</div></div></nav></div></header>'
            % (link(here, ''), SITE_NAME, HOME_COORDS, ab, ''.join(items), search, units_control(),
               icon('menu', 24, 'i-open'), icon('close', 24, 'i-close'), ''.join(menu_rows), ''.join(site_rows), units_control()))


def footer(here):
    reports = ''.join('<li><a href="%s">%s</a></li>' % (link(here, section_url(a)), lab) for a, lab in NAV)
    site = ('<li><a href="%s">Trips</a></li><li><a href="%s">Tick list</a></li><li><a href="%s">Map &amp; archive</a></li><li><a href="%s">About</a></li><li><a href="%s">%sRSS</a></li>'
            % (link(here, 'trips/'), link(here, 'tick-list/'), link(here, 'map/'), link(here, 'about/'), link(here, 'feed.xml'), icon('rss', 16)))
    return ('<footer class="site-f"><div class="site-f-in">'
            '<div class="f-brand"><a class="brand-n" href="%s">%s</a><span class="t-mono-s">%s</span></div>'
            '<nav class="f-nav" aria-labelledby="f-rep"><p class="t-label" id="f-rep">Reports</p><ul>%s</ul></nav>'
            '<nav class="f-nav" aria-labelledby="f-site"><p class="t-label" id="f-site">Site</p><ul>%s</ul></nav>'
            '<div class="f-note"><p>Reports describe past conditions, not advice. Check the current avalanche forecast before you go.</p>'
            '<p class="t-mono-s">%s</p>'
            '<p class="t-mono-s">© %d ERIC SICHAK</p></div></div></footer>'
            % (link(here, ''), SITE_NAME, meta_items([nb('BASED IN LAKE TAHOE'), nb('AIARE 2')]), reports, site,
               meta_items([nb('MAPS: AWS TERRAIN TILES'), nb('© OPENSTREETMAP CONTRIBUTORS')]), date.today().year))


def lightbox():
    """The in-page photo viewer (base.js). Photo links keep their .webp hrefs, so without JS they still open the file.
    #lb-live announces 'Photo N of M. <alt>' when the viewer moves to another photo."""
    return ('<dialog class="lb" aria-label="Photo viewer"><img class="lb-img" alt=""><div class="lb-bar">'
            '<span class="t-mono-s lb-n"></span><p class="t-small lb-cap"></p>'
            '<button type="button" class="lb-prev" aria-label="Previous photo">%s</button>'
            '<button type="button" class="lb-next" aria-label="Next photo">%s</button>'
            '<button type="button" class="lb-close" aria-label="Close">%s</button></div>'
            '<p class="sr" id="lb-live" aria-live="polite"></p></dialog>'
            % (icon('arrow-left', 20), icon('arrow-right', 20), icon('close', 20)))


def document(here, title, body, description='', active=None, css_pages=(), image=None, extra_head='', body_cls='', bottom='',
             og_type='website', full_title=None, trip=None, canonical=True, report=None):
    """full_title: the whole <title> text (default '<title> · Eric Sichak'), also the og:title; og_type: 'article' on trip
    pages. trip: the trip the page shows (default: looked up by URL, see register_site()) for the phone app bar.
    image: the share image, a share_photo() dict (or a site-relative path). canonical=False: a page that stands for no
    URL of its own (the 404 page) gets neither a canonical link nor og:url. report: the published trip a report page
    is about; it adds the publication dates index.md states and, for a written report, one BlogPosting block."""
    p = prefix(here)
    p = '' if p == './' else p
    if not full_title:
        full_title = title if title == SITE_NAME else '%s · %s' % (title, SITE_NAME)
    if trip is None:
        trip = _TRIPS_BY_URL.get(here)
    canon = SITE_URL + (here if not here.endswith('index.html') else here[:-10])
    og = _share_tags(image)
    if report is not None:
        og += _report_head(report, canon, description or SITE_TAGLINE, image)
    canon_link = ('<link rel="canonical" href="%s">' % canon) if canonical else ''
    og_url = ('<meta property="og:url" content="%s">' % canon) if canonical else ''
    lb = lightbox() if any(('class="%s' % c) in body for c in ('jph', 'mul-ph', 'ser-ph')) else ''
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>%s</title><meta name="description" content="%s">'
            '%s'
            '<meta property="og:type" content="%s"><meta property="og:title" content="%s">'
            '<meta property="og:description" content="%s">%s%s'
            '<meta name="theme-color" content="#F2F1EC">'
            '<link rel="icon" href="%sassets/favicon.svg" type="image/svg+xml">'
            '<link rel="alternate" type="application/rss+xml" title="%s — trip reports" href="%sfeed.xml">'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="%s">'
            '<link rel="stylesheet" href="%sassets/site.css">'
            '<script>try{if(localStorage.getItem("units")==="km")document.documentElement.classList.add("km")}catch(e){}</script>'
            '%s</head><body class="%s">%s<main id="main">%s</main>%s%s%s'
            '<script src="%sassets/site.js" defer></script></body></html>\n'
            % (esc(full_title), esc(description or SITE_TAGLINE), canon_link, og_type, esc(full_title), esc(description or SITE_TAGLINE), og_url, og,
               p, SITE_NAME, p, FONTS.replace('&', '&amp;'), p, extra_head, body_cls, header(here, active, trip), body, footer(here),
               bottom, lb, p))
