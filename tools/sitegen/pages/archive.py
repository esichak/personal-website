"""Map & archive — /map/: region maps (ARIA tabs) with an "In this region" list, then every report by year."""
import json
import os
import re

from sitegen import core
from sitegen.core import esc, U, link, icon

import content

HERE = 'map/'
SHOW = 8  # "In this region" rows shown before the "Show all" toggle (JS only; without JS every row shows)


# ---------------------------------------------------------------- data

def site_meta():
    p = os.path.join(core.ROOT, 'rendered', 'site', 'meta.json')
    return json.load(open(p)) if os.path.exists(p) else {'maps': {}, 'regions': []}


def regions(site, meta):
    """[(name, slug, trips newest-first with planned last)] ordered by number of published trips."""
    out = []
    for name in meta.get('regions') or []:
        slug = content.slugify(name)
        m = meta['maps'].get('region-%s-desktop' % slug) or {}
        keys = set(m.get('trips') or [t['slug'] for t in site['trips'] if t['region'] == name and t['kind'] != 'series'])
        ts = [t for t in site['trips'] if t['slug'] in keys]
        ts.sort(key=lambda t: t['kind'] == 'planned')  # stable: keeps newest-first, planned last
        if ts:
            out.append((name, slug, ts))
    out.sort(key=lambda r: (-sum(1 for t in r[2] if t['kind'] != 'planned'), r[0]))
    return out


def plural(k, word, pl=None):
    return '%d %s' % (k, word if k == 1 else (pl or word + 'S'))


def count_n(k):
    """A tab / chip count that reads as 'Lake Tahoe, 14 reports' (the visible part is just the number)."""
    return '<span class="sr">, </span>%d<span class="sr"> %s</span>' % (k, 'report' if k == 1 else 'reports')


def count_line(ts):
    """'9 REPORTS' · '3 REPORTS INCL. 2 MULTI-DAY, 1 SERIES' · '23 REPORTS INCL. 2 MULTI-DAY, 1 SERIES · 1 PLANNED ROUTE'.
    Multi-day and series are subsets of the reports (a series counts as one report), as on Home's activity tiles. Each item
    stays on one line; a wrapped line breaks before INCL. or at ', ' / ' · ' (archive.js countLine() mirrors this)."""
    item = lambda x: '<span class="arc-seg">%s</span>' % x  # noqa: E731
    pub = [t for t in ts if t['kind'] != 'planned']
    bits = []
    if pub:
        md = sum(1 for t in pub if t['kind'] == 'multi-day')
        se = sum(1 for t in pub if t['kind'] == 'series')
        sub = [x for x in (('%d MULTI-DAY' % md) if md else '', ('%d SERIES' % se) if se else '') if x]
        head = item(plural(len(pub), 'REPORT'))
        if sub:
            head += ' ' + ', '.join(item(('INCL. ' if i == 0 else '') + x) for i, x in enumerate(sub))
        bits.append(head)
    pl = len(ts) - len(pub)
    if pl:
        bits.append(item(plural(pl, 'PLANNED ROUTE')))
    return core.SEP.join(bits)


def segs(line):
    """Wrap each ' · ' segment so a wrapped meta line breaks between items, never inside one, and never starts with '·'."""
    parts = line.split(' · ')
    return ' '.join('<span class="arc-seg">%s%s</span>' % (b, '&nbsp;·' if i < len(parts) - 1 else '') for i, b in enumerate(parts))


_CASING = re.compile(r'<path class="(mk-roadc|mk-minorc)" d="([^"]+)"/>')
_TOP = {'mk-roadc': 'mk-road', 'mk-minorc': 'mk-minor'}


def share_casings(svg, ns):
    """Road casing and road fill are the same geometry drawn twice: keep one copy in <defs> and <use> it for both.

    Lossless (stroke/fill props inherit into the use clone because the shared path has no class of its own); halves the
    road bytes, which are most of the region maps' weight (see core_requests: render.py should emit it this way)."""
    k = [0]

    def rep(m):
        casing, d = m.group(1), m.group(2)
        top = '<path class="%s" d="%s"/>' % (_TOP[casing], d)
        if top not in svg:
            return m.group(0)
        k[0] += 1
        pid = '%s-rd%d' % (ns, k[0])
        tops.append((top, '<use href="#%s" class="%s"/>' % (pid, _TOP[casing])))
        return '<defs><path id="%s" d="%s"/></defs><use href="#%s" class="%s"/>' % (pid, d, pid, casing)
    tops = []
    out = _CASING.sub(rep, svg)
    for top, use in tops:
        out = out.replace(top, use, 1)
    return out


def series_tag(t):
    """The series card's tag carries the day count ('SERIES · 150 DAYS'); table rows use core.trip_tags."""
    return 'Series · %d days' % len(t['days']) if t['days'] else 'Series'


def dist_line(t):
    mi, km = core.dist_vals(t['stats'].get('distance_km'))
    return U(core.nb(mi + ' MI'), core.nb(km + ' KM')) if mi else ''


# ---------------------------------------------------------------- page parts

def head_block(site, regs):
    pub = site['published']
    bits = [plural(len(pub), 'REPORT')]  # same count as the "All reports" meta and the filter chips (series included)
    if site['planned']:
        bits.append(plural(len(site['planned']), 'PLANNED ROUTE'))
    bits.append(plural(len(regs), 'REGION'))
    years = sorted({t['date'].year for t in pub if t['date']} | {t['end_date'].year for t in pub if t.get('end_date')})
    if years:
        bits.append(str(years[0]) if years[0] == years[-1] else '%d–%d' % (years[0], years[-1]))
    return ('<section class="arc-head wrap" aria-labelledby="arc-title"><h1 id="arc-title" class="t-d1">Map &amp; archive</h1>'
            '<p class="t-mono-s arc-stats">%s</p></section>' % segs(' · '.join(bits)))


def legend(ts, meta_d):
    acts = [a for a, _ in core.NAV if any(t['activity'] == a and t['kind'] != 'planned' for t in ts)]
    items = []
    for a in acts:
        subs = sorted({t.get('subtype') for t in ts if t['activity'] == a and t.get('subtype')})
        word = core.ACT[a][0] if not (a == 'other' and len(subs) == 1) else core.act_word(a, subs[0])
        items.append('<li>%s<span>%s</span></li>' % (core.disc(a, 16, subs[0] if (a == 'other' and len(subs) == 1) else None), esc(word)))
    sym = []
    if any(t['kind'] == 'planned' for t in ts):
        sym.append('<li><svg width="28" height="12" viewBox="0 0 28 12" aria-hidden="true"><path d="M2 6H26" style="stroke:#EEECE6;stroke-width:3.5"/>'
                   '<path d="M2 6H26" style="stroke:#45474C;stroke-width:1.5;stroke-dasharray:4 3"/></svg><span>Planned route</span></li>')
    if any(c.get('n', 0) > 1 for c in (meta_d.get('clusters') or [])):
        sym.append('<li><svg width="28" height="20" viewBox="0 0 28 20" aria-hidden="true"><circle cx="14" cy="10" r="9" style="fill:#F2F1EC;stroke:#16171A;stroke-width:1.5"/>'
                   '<text x="14" y="10.5" style="font:600 11px/1 var(--mono);fill:#16171A;text-anchor:middle;dominant-baseline:central">2</text></svg>'
                   '<span>Several reports start here</span></li>')
    return ('<div class="arc-legend"><p class="t-label">Legend</p><div class="arc-legend-c"><ul aria-label="Activities">%s</ul>%s</div></div>'
            % (''.join(items), ('<ul aria-label="Map symbols">%s</ul>' % ''.join(sym)) if sym else ''))


def region_row(t, here, more=False):
    if t['kind'] != 'planned' and not t['days'] and t['date']:
        # 'SUN, APR 5, 2026': the weekday drops out at 1000–1199, where the side column is narrow (archive.css)
        bits = ['<span class="arc-wd">%s,\u00a0</span>%s' % (t['date'].strftime('%a').upper(), core.trip_date(t, short=True))]
    else:
        bits = [core.trip_date(t)]
    d = dist_line(t)
    if d:
        bits.append(d)
    g = core.glyph(t, here, 'g64', 'rg-%s' % t['slug']).replace('<svg ', '<svg class="arc-row-g" ', 1)
    # every row carries its key: the region map's planned line (mk-cat mk-planned) has one too, so hover highlights it
    return ('<li class="arc-row%s" data-key="%s"><a href="%s">%s<span class="arc-row-b"><span class="arc-row-t">%s</span>'
            '<span class="t-mono-s arc-row-m">%s<span class="sr">%s · </span><span>%s</span></span></span></a></li>'
            % (' arc-more' if more else '', t['slug'], link(here, t['url']), g,
               core.title_html(t['title']), icon(core.act_icon(t), 14), esc(core.act_word(t)), core.SEP.join(bits)))


def region_panel(name, slug, ts, here, meta, first):
    md = meta['maps'].get('region-%s-desktop' % slug) or {}
    map_id = 'arc-map-' + slug
    anchor = ts[0]  # map_block needs a trip dict only for per-trip renders; site maps read rendered/site/
    mp = core.map_block(anchor, here, [('region-%s-desktop' % slug, 'desktop'), ('region-%s-phone' % slug, 'phone')],
                        'assets/maps/', 'rg-' + slug, eager=first, cls='arc-mapv', site_maps=True, attrib=False)
    mp = share_casings(mp.replace('<div class="map', '<div id="%s" class="map' % map_id, 1), 'arc-' + slug)
    cap = ('<p class="arc-cap"><span>%s</span><span>%s</span></p>'
           % (segs('Pins mark each start and link to the report · Full tracks, not trimmed · North up'),
              segs('Terrain: AWS Terrain Tiles · Map data © OpenStreetMap contributors · Not for navigation')))
    rows = ''.join(region_row(t, here, i >= SHOW and len(ts) > SHOW + 1) for i, t in enumerate(ts))
    return ('<div class="arc-panel" id="region-%s">'
            '<h3 class="arc-panel-h t-h3" id="arc-ph-%s">%s</h3>'
            '<div class="arc-grid"><div class="arc-mapcol">%s%s</div>'
            '<div class="arc-side">%s<div class="arc-inreg"><div class="arc-inreg-h"><h4 class="t-label" id="arc-in-%s">In this region</h4>'
            '<span class="t-mono-s">%s</span></div><ol class="arc-rows" id="arc-rows-%s" aria-labelledby="arc-in-%s arc-ph-%s" data-map-target="%s">%s</ol>%s</div>'
            '</div></div></div>'
            % (slug, slug, esc(name), mp, cap, legend(ts, md), slug, count_line(ts), slug, slug, slug, map_id, rows,
               ('<button type="button" class="alink arc-all-btn" aria-expanded="false" aria-controls="arc-rows-%s" hidden>Show all %d%s</button>'
                % (slug, len(ts), icon('chevron-down', 16))) if len(ts) > SHOW + 1 else ''))


def series_card(site, here):
    ts = [t for t in site['published'] if t['kind'] == 'series']
    if not ts:
        return ''
    out = []
    for t in ts:
        meta = [core.trip_date(t, short=True)]
        if t.get('place'):
            meta.append(esc(t['place']).upper())
        d = dist_line(t)
        if d:
            meta.append(d)
        g = '<span class="arc-series-g">%s</span>' % core.tile(t, here, 'sc-%s' % t['slug'])
        out.append('<a class="arc-series" href="%s">%s<span class="arc-series-b"><span class="t-label">Not on a region map</span>'
                   '<span class="arc-series-t">%s</span><span class="arc-series-m">%s%s<span class="t-mono-s arc-series-d">%s</span></span></span>'
                   '<span class="arc-series-go">%s%s</span></a>'
                   % (link(here, t['url']), g, core.title_html(t['title']), core.chip(t, variant='inline'), core.tag(series_tag(t)),
                      segs(' · '.join(meta)), 'Read the series' if t['kind'] == 'series' else 'Read report', icon('arrow-right', 16)))
    return '<div class="arc-series-w">%s</div>' % ''.join(out)


def map_section(site, here, regs, meta):
    if not regs:
        return ''
    tabs = ''.join('<button type="button" role="tab" id="arc-tab-%s" aria-controls="region-%s" aria-selected="%s" tabindex="%s">'
                   '<span>%s</span><span class="arc-tab-n">%s</span></button>'
                   % (slug, slug, 'true' if i == 0 else 'false', '0' if i == 0 else '-1', esc(name),
                      count_n(sum(1 for t in ts if t['kind'] != 'planned')))
                   for i, (name, slug, ts) in enumerate(regs))
    panels = ''.join(region_panel(name, slug, ts, here, meta, i == 0) for i, (name, slug, ts) in enumerate(regs))
    return ('<section class="arc-map wrap" aria-labelledby="arc-map-h"><h2 class="sr" id="arc-map-h">Map by region</h2>'
            '<div class="arc-tabs-w"><div class="arc-tabs" role="tablist" aria-label="Region" hidden>%s</div></div>'
            '%s%s</section>' % (tabs, panels, series_card(site, here)))


def archive_section(site, here):
    trips = site['published'] + site['planned']
    groups = []
    for t in site['published']:
        y = t['date'].year if t['date'] else None
        if not groups or groups[-1][0] != y:
            groups.append((y, []))
        groups[-1][1].append(t)
    if site['planned']:
        groups.append(('Planned', list(site['planned'])))
    chips = ['<button type="button" class="arc-chip" data-filter="all" aria-pressed="true"><span class="arc-chip-l">All</span></button>']
    for a, lab in core.NAV:
        k = sum(1 for t in site['published'] if t['activity'] == a)
        if not k:
            continue
        chips.append('<button type="button" class="arc-chip" data-filter="%s" aria-pressed="false">'
                     '<span class="chip-sw" style="background:%s" aria-hidden="true"></span><span class="arc-chip-l">%s</span>'
                     '<span class="arc-chip-n">%s</span></button>' % (a, core.ACT[a][3], esc(lab), count_n(k)))
    # rows are core.table_row (li > a): status-only tags (planned rows say PLANNED in the date cell) + filter data for archive.js
    row = lambda t: core.table_row(t, here, tags='' if t['kind'] == 'planned' else core.trip_tags(t, shape=False),  # noqa: E731
                                   attrs=' data-act="%s" data-kind="%s"' % (t['activity'], t['kind']))
    body = []
    for y, ts in groups:
        gid = 'yr-%s' % str(y if y is not None else 'undated').lower()
        label = str(y) if y is not None else 'Undated'
        body.append('<div class="arc-yr" data-group="%s"><div class="arc-yr-h"><h3 class="t-label" id="%s">%s</h3>'
                    '<span class="t-mono-s arc-yr-n">%s</span></div><ol class="arc-rows2" aria-labelledby="%s">%s</ol></div>'
                    % (gid, gid, label, count_line(ts), gid, ''.join(row(t) for t in ts)))
    return ('<section class="arc-all wrap sec" id="all-reports" aria-labelledby="all-reports-h">%s'
            '<div class="arc-filt" role="group" aria-label="Filter by activity" hidden>%s</div>'
            '<p class="sr" id="arc-live" aria-live="polite"></p>'
            '<div class="rtab arc-table"><div aria-hidden="true">%s</div>%s</div></section>'
            % (core.section_head('All reports', count_line(trips), id_='all-reports-h'), ''.join(chips), core.table_head(), ''.join(body)))


def build(site):
    here = HERE
    meta = site_meta()
    regs = regions(site, meta)
    body = head_block(site, regs) + map_section(site, here, regs, meta) + archive_section(site, here)
    desc = 'Every trip report on a map by region, and the full archive by year with GPX tracks.'
    return [core.Page(here, core.document(here, 'Map & archive', body, desc, active='map', body_cls='p-archive'), 'Map & archive')]
