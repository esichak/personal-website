"""Map & archive — /map/: region maps (ARIA tabs) with an "In this region" list, then every report by year."""
import json
import os
import re

from sitegen import core
from sitegen.core import esc, U, link, icon

import content
import geo

HERE = 'map/'
SHOW = 8  # "In this region" rows shown before the "Show all" toggle (JS only; without JS every row shows)


# ---------------------------------------------------------------- data

def site_meta():
    """rendered/site/meta.json as it is on disk now (core.read_site_meta)."""
    return core.read_site_meta()


def listed(site):
    """The trips a region group lists and counts (core.listed_trips): every report and the active tick-list goals."""
    return core.listed_trips(site)


def regions(site, meta):
    """[(name, slug, trips newest-first with planned last)] ordered by number of published trips (core.region_groups,
    which the region pages share)."""
    return core.region_groups(site, meta)


def plural(k, word, pl=None):
    return '%d %s' % (k, word if k == 1 else (pl or word + 'S'))


def count_n(k):
    """A tab / chip count that reads as 'Lake Tahoe, 14 reports' (the visible part is just the number)."""
    return '<span class="sr">, </span>%d<span class="sr"> %s</span>' % (k, 'report' if k == 1 else 'reports')


def count_line(ts, cls=''):
    """'9 REPORTS' · '3 REPORTS · INCL. 2 MULTI-DAY, 1 SERIES' · '23 REPORTS · INCL. 2 MULTI-DAY, 1 SERIES · + 1 PLANNED ROUTE'
    (core.count_items, as on Home and the section heads: a series or multi-day trip counts as one report, and a planned
    route is never one of them); a group of planned routes only reads '1 PLANNED ROUTE'. One .ml meta line, so a wrapped
    line never starts or ends with a dot (archive.js countLine() mirrors this)."""
    pub = [t for t in ts if t['kind'] != 'planned']
    pl = len(ts) - len(pub)
    items = core.count_items(pub, pl) if pub else [core.nb(plural(pl, 'PLANNED ROUTE'))]
    return core.meta_items(items, cls=cls)


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


_MARK = re.compile(r'<(g|a) class="(mk-cat|mk-pin|mk-line)([^"]*)"([^>]*?) data-key="([^"]+)"')
_CLUSTER_KEYS = re.compile(r'<g class="mk-cluster([^"]*)"([^>]*?) data-keys="([^"]*)"')


def inject_acts(svg, by_slug):
    """The legend's filter (maps-07) needs each marker's activity: data-act="<activity>" on every track (g.mk-cat), pin
    (a.mk-pin) and journal line (a.mk-line, keyed '<journal slug>:<part>'), and data-acts="ski hike" (each once, sorted)
    on a cluster marker, from the site's trips (by_slug). A key the site does not know gets nothing. The render is not
    touched: this runs on the inlined fragment at build time."""
    def act_of(key):
        t = by_slug.get(key.split(':')[0])
        return t['activity'] if t else None

    def mark(m):
        a = act_of(m.group(5))
        return m.group(0) + ((' data-act="%s"' % a) if a else '')

    def cluster(m):
        acts = sorted({a for a in (act_of(k) for k in m.group(3).split()) if a})
        return m.group(0) + ((' data-acts="%s"' % ' '.join(acts)) if acts else '')
    return _CLUSTER_KEYS.sub(cluster, _MARK.sub(mark, svg))


def series_tag(t):
    """The series card's tag carries the day count ('SERIES · 150 DAYS'); table rows use core.trip_tags."""
    return 'Series · %d days' % len(t['days']) if t['days'] else 'Series'


def dist_line(t):
    mi, km = core.dist_vals(t['stats'].get('distance_km'))
    p = core.approx(t)   # '≈ ' for a tick-list goal: its number is measured from a plan, not recorded
    return U(core.nb(p + mi + ' MI'), core.nb(p + km + ' KM')) if mi else ''


# ---------------------------------------------------------------- page parts

def head_block(site, regs, meta):
    pub = site['published']
    # same count as the "All reports" meta and the filter chips (series included); the planned route is never a report
    bits = [x for x in core.count_items(pub, site.get('active_goals', site['planned'])) if not x.startswith('INCL.')]
    # every region a report is filed under, mapped or not (rendered/site/meta.json 'all_regions'; each has an anchor on this page)
    bits.append(core.nb(plural(len(meta.get('all_regions') or [r[0] for r in regs]), 'REGION')))
    years = sorted({t['date'].year for t in pub if t['date']} | {t['end_date'].year for t in pub if t.get('end_date')})
    if years:
        bits.append(str(years[0]) if years[0] == years[-1] else '%d–%d' % (years[0], years[-1]))
    return ('<section class="arc-head wrap" aria-labelledby="arc-title"><h1 id="arc-title" class="t-d1">Map &amp; archive</h1>'
            '<p class="t-mono-s arc-stats">%s</p></section>' % core.meta_items(bits))


def _site_draws(name, pattern):
    """True when the site map fragment rendered/site/<name>.svg.html contains `pattern` (a regex)."""
    try:
        return re.search(pattern, core._read(os.path.join(core.ROOT, 'rendered', 'site', name + '.svg.html'))) is not None
    except OSError:
        return False


# the pin cluster as the region maps draw it (paper disc, ink ring, Mono count), at key-row size
CLUSTER_SYM = ('<svg class="hom-key-cl" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">'
               '<circle cx="10" cy="10" r="9" style="fill:#F2F1EC;stroke:#16171A;stroke-width:1.5"/>'
               '<text x="10" y="10.5" style="font:600 11px/1 var(--mono);fill:#16171A;text-anchor:middle;dominant-baseline:central">2</text></svg>')


def region_key(site, meta, names, cls='hom-rkey'):
    """One compact key row under the region maps (archive.legend's item logic): an activity disc + word for every activity
    whose pins the drawn maps carry ('other' reads as its sub-type when only one occurs), the planned-route line when a
    planned track is drawn, and the cluster symbol when pins merge. Symbols only, never counts. Home's maps show it at
    every width (cls 'hom-rkey'); a region panel shows it on phones only, beside the full legend (phone-04)."""
    by = site['by_slug']
    keys = set()
    for nm in names:
        m = meta.get(nm) or {}
        cl = m.get('clusters')  # every pin, merged or not (a lone pin is a cluster of 1)
        keys.update([k for c in cl for k in c.get('keys', [])] if cl else m.get('trips', []))
    ts = [by[k] for k in keys if k in by]
    items = []
    for a, _lab in core.NAV:
        if not any(t['activity'] == a and t['kind'] != 'planned' for t in ts):
            continue
        subs = sorted({t.get('subtype') for t in ts if t['activity'] == a and t.get('subtype')})
        sub = subs[0] if (a == 'other' and len(subs) == 1) else None
        items.append('<li>%s%s</li>' % (core.disc(a, 16, sub), esc(core.act_word(a, sub) if sub else core.ACT[a][0])))
    if any(_site_draws(nm, r'class="mk-cat mk-planned"') for nm in names):
        word, sym = core.KEY_SYMBOLS['planned_site']
        items.append('<li><svg width="16" height="10" viewBox="0 0 16 10" aria-hidden="true">%s</svg>%s</li>' % (sym, esc(word)))
    if any(c.get('n', 0) > 1 for nm in names for c in ((meta.get(nm) or {}).get('clusters') or [])):
        items.append('<li>%sSeveral reports start here</li>' % CLUSTER_SYM)
    if not items:
        return ''
    return '<ul class="keyrow keyrow--compact %s" aria-label="Map key">%s</ul>' % (cls, ''.join(items))


def legend(ts, meta_d):
    acts = [a for a, _ in core.NAV if any(t['activity'] == a and t['kind'] != 'planned' for t in ts)]
    items = []
    for a in acts:
        subs = sorted({t.get('subtype') for t in ts if t['activity'] == a and t.get('subtype')})
        word = core.ACT[a][0] if not (a == 'other' and len(subs) == 1) else core.act_word(a, subs[0])
        # data-act: archive.js makes each item a toggle that filters the map and the list (maps-07)
        items.append('<li data-act="%s">%s<span>%s</span></li>' % (a, core.disc(a, 16, subs[0] if (a == 'other' and len(subs) == 1) else None), esc(word)))
    sym = []
    if any(t['kind'] == 'planned' for t in ts):
        # the region maps' light planned line (core.KEY_SYMBOLS['planned_site'], drawn 28 wide)
        sym.append('<li><svg width="28" height="12" viewBox="0 0 28 12" aria-hidden="true"><path d="M2 6H26" style="stroke:#EEECE6;stroke-width:3.5"/>'
                   '<path d="M2 6H26" style="stroke:#66686D;stroke-width:1.5;stroke-dasharray:4 3"/></svg><span>Planned route</span></li>')
    if any(c.get('n', 0) > 1 for c in (meta_d.get('clusters') or [])):
        sym.append('<li><svg width="28" height="20" viewBox="0 0 28 20" aria-hidden="true"><circle cx="14" cy="10" r="9" style="fill:#F2F1EC;stroke:#16171A;stroke-width:1.5"/>'
                   '<text x="14" y="10.5" style="font:600 11px/1 var(--mono);fill:#16171A;text-anchor:middle;dominant-baseline:central">2</text></svg>'
                   '<span>Several reports start here</span></li>')
    # keyrow--d: from 560 px; phones get the compact key row instead (region_key, keyrow--p; phone-04)
    return ('<div class="arc-legend keyrow--d"><p class="t-label">Legend</p><div class="arc-legend-c"><ul aria-label="Activities">%s</ul>%s</div></div>'
            % (''.join(items), ('<ul aria-label="Map symbols">%s</ul>' % ''.join(sym)) if sym else ''))


def region_row(t, here, more=False, region=None):
    """One report's row in a region's list. Its id, arc-row-<slug> (a report's 'See on the <Region> map' names it), only
    in the list of the trip's own region: a map drawn before the trip was filed elsewhere still lists it in the old
    region's panel, and map/ then shows it twice (region: the list's region; None, the trip's own)."""
    if t['kind'] != 'planned' and not t['days'] and t['date']:
        # 'SUN, APR 5, 2026': the weekday drops out at 1000–1199, where the side column is narrow (archive.css)
        bits = ['<span class="arc-wd">%s,\u00a0</span>%s' % (t['date'].strftime('%a').upper(), core.trip_date(t, short=True))]
    else:
        bits = [core.trip_date(t)]
    d = dist_line(t)
    if d:
        bits.append(d)
    g = core.glyph(t, here, 'g64', cls=' arc-row-g')
    # every row carries its key: the region map's planned line (mk-cat mk-planned) has one too, so hover highlights it
    rid = (' id="arc-row-%s"' % t['slug']) if (region is None or t.get('region') == region) else ''
    # data-kind: a cluster's selection counts reports, never the planned route among its keys (base.js)
    return ('<li class="arc-row%s" data-key="%s"%s data-kind="%s"><a href="%s" data-act="%s">%s<span class="arc-row-b"><span class="arc-row-t">%s</span>'
            '<span class="t-mono-s arc-row-m"><span class="arc-row-i">%s</span><span class="sr">%s · </span><span>%s</span></span></span></a></li>'
            % (' arc-more' if more else '', t['slug'], rid, t['kind'], link(here, t['url']), t['activity'], g,
               core.title_html(t['title']), icon(core.act_icon(t), 14), esc(core.act_word(t)), core.SEP.join(bits)))


def journal_parts(site, name):
    """[(journal, part)]: the parts of the published journals that lie in the region `name`, as their region_days
    (content.py) list them, in the order written. A journal is filed under a region of its own and is no report of this
    one; a part is what the region's map draws of it (render.journal_parts) and what its list names in one row
    (journal_row)."""
    out = []
    for t in (site or {}).get('published') or []:
        if t['kind'] != 'series':
            continue
        for rd in t.get('region_days') or []:
            if rd['region'] == name and rd['days']:
                out.append((t, rd))
    return out


def part_glyph(name, here):
    """A journal part's own drawing (render.part_glyph, published by build.py as assets/maps/<name>.svg) as an <img>,
    as core.glyph is for a trip. '' when the name is None, is not a plain file name, or the drawing is not rendered."""
    if not isinstance(name, str) or not re.match(r'[A-Za-z0-9_-]+\Z', name):
        return ''
    if not os.path.exists(os.path.join(core.ROOT, 'rendered', 'site', name + '.svg.html')):
        return ''
    w, h = core.GLYPH_SIZES['g64']
    return ('<img class="gl gl--g64 arc-row-g" src="%s%s.svg" width="%d" height="%d" alt="" loading="lazy" decoding="async">'
            % (link(here, 'assets/maps/'), esc(name), w, h))


def part_day_km(t, part, d):
    """The distance one day adds to a journal part, in km: the day file's own figure, or, for a day the part takes one
    stretch of, the length of that stretch along its track (content.day_points; a ContentError when the track has no
    such stretch). None when there is no figure."""
    n = (part.get('stretches') or {}).get(d['id'])
    if n is None:
        return d['stats'].get('distance_km')
    pts = content.day_points(d, n, 'content/trips/%s/index.md' % t['slug'])
    return geo.cumdist(pts)[-1] / 1000.0 if pts else None


def journal_part_id(region_slug, part):
    """'arc-row-lake-tahoe-pacific-crest-trail-2024-...': a journal part's row id, qualified by its region, since one
    part key can be in two regions' lists on map/ (an untitled part's key is the journal's slug alone)."""
    return 'arc-row-%s-%s' % (region_slug, content.slugify(part['key']))


def journal_row(t, part, here, drawing=None, region_slug=None):
    """One part of a journal as a row of a region's list: the part's own name when it has one (Tahoe Rim Trail), else
    the journal's title; then the dates of its first and last day, how many journal days it is and the distance they add
    up to (from the day files' own stats). The link goes to the first of those days on the journal page. The row
    carries the part's key, as its lines on the region map do, so hovering one picks out the other. It is not a report
    of the region: no count includes it, and it is never folded away behind 'Show all'.
    A day the part takes one stretch of ('146/2') is a journal day like the others, and counts with the length of that
    stretch, measured along its track (part_day_km): the day file's distance is the whole day's.
    drawing: the name of the part's own drawing (the map's 'journals' entry names it); without one the row shows the
    journal's, which is the whole journal."""
    days = part['days']
    dates = [d['date'] for d in days if d['date']]
    bits = [core.nb(core.frange(min(dates), max(dates), caps=True))] if dates else []
    bits.append(core.nb(plural(len(days), 'JOURNAL DAY')))
    km = [k for k in (part_day_km(t, part, d) for d in days) if k]
    mi_, km_ = core.dist_vals(sum(km)) if km else ('', '')
    if mi_:
        bits.append(U(core.nb(mi_ + ' MI'), core.nb(km_ + ' KM')))
    g = part_glyph(drawing, here) or core.glyph(t, here, 'g64', cls=' arc-row-g')
    rid = (' id="%s"' % journal_part_id(region_slug, part)) if region_slug else ''
    return ('<li class="arc-row arc-row--journal" data-key="%s"%s><a href="%s#%s" data-act="%s">%s<span class="arc-row-b"><span class="arc-row-t">%s</span>'
            '<span class="t-mono-s arc-row-m"><span class="arc-row-i">%s</span><span class="sr">%s · </span><span>%s</span></span></span></a></li>'
            % (esc(part['key']), rid, link(here, t['url']), content.day_anchor(days[0]['label']), t['activity'], g,
               core.title_html(part.get('title') or t['title']), icon(core.act_icon(t), 14), esc(core.act_word(t)), core.SEP.join(bits)))


def region_panel(name, slug, ts, here, meta, first, page=False, drawn=None, site=None):
    """One region: its map, caption and legend, and beside them the region's rows (the first SHOW until 'Show all').
    On map/ (page=False) the panel has its own heading and id (#region-<slug>) and, when the region has a page of its
    own, ends with a link to it. On that page (page=True, sitegen.pages.region) the H1 already names the region, so
    the panel has no heading of its own (the list's heading moves up to H3), its id is #map (#region-<slug> belongs to
    map/), and it carries no link to the page it is on. Everything else is the same markup, so archive.js and base.js
    treat both alike: 'Show all', row and pin highlighting, and a cluster marker's click to its report's row.
    drawn: the trips the map draws, when they are not ts (a region page lists by the region field, and a report without
    a track or newer than the last render is on the list and not on the map): the legend is the key to the map, so it
    names their activities and symbols, not the list's.
    site: the site, for the journals that have days in this region (journal_parts): each part gets one row, after the
    reports and before the planned routes, and those rows are shown whether the list is folded or not. The legend
    names a journal's activity when the map draws its days (the map's 'journals' entry). None: no such rows."""
    md = meta['maps'].get('region-%s-desktop' % slug) or {}
    parts = journal_parts(site, name)
    on_map = {j.get('slug') for j in (md.get('journals') or []) if isinstance(j, dict)}
    key_ts = (ts if (drawn is None or not page) else drawn) + [jt for jt, _part in parts if jt['slug'] in on_map]
    map_id = 'arc-map-' + slug
    anchor = ts[0]  # map_block needs a trip dict only for per-trip renders; site maps read rendered/site/
    # attrib: the credit tag in the phone map's corner, as on a report (phone-04); fullscreen_href: its 44 px button to the
    # region's full-screen page, map/<slug>/ (qa-06), which build() writes for each panel of map/. A region page whose
    # map names none of the site's trips until the next render has no panel there, so no such page and no button
    fs = not (page and site is not None and slug not in {s for _n, s, _ts in core.region_groups(site, meta)})
    mp = core.map_block(anchor, here, [('region-%s-desktop' % slug, 'desktop'), ('region-%s-phone' % slug, 'phone')],
                        'assets/maps/', 'rg-' + slug, eager=first, cls='arc-mapv', site_maps=True, attrib=True,
                        fullscreen_href=link(here, 'map/%s/' % slug) if fs else None)
    mp = share_casings(mp.replace('<div class="map', '<div id="%s" class="map' % map_id, 1), 'arc-' + slug)
    if site:
        mp = inject_acts(mp, site.get('by_slug') or {t['slug']: t for t in site['trips']})
    cap = '<div class="arc-cap">%s</div>' % core.map_caption(['Pins mark each start and link to the report', 'Full tracks, not trimmed', 'North up'])
    # the legend beside the map, under its caption (gap2-06: it stays in view with the stuck map from 1000 px), and the
    # compact key row in its place on phones
    pkey = region_key(site, meta['maps'], ['region-%s-desktop' % slug, 'region-%s-phone' % slug], 'keyrow--p arc-pkey') if site else ''
    cap += legend(key_ts, md) + pkey
    fold = len(ts) > SHOW + 1
    rows = [region_row(t, here, i >= SHOW and fold, region=name) for i, t in enumerate(ts)]
    # the journal rows go in after the reports: before the first planned route of the list as it was handed over
    at = next((i for i, t in enumerate(ts) if t['kind'] == 'planned'), len(ts))
    drawings = {j['key']: j.get('glyph') for j in (md.get('journals') or []) if isinstance(j, dict) and isinstance(j.get('key'), str)}
    rows = ''.join(rows[:at] + [journal_row(jt, part, here, drawings.get(part['key']), slug) for jt, part in parts] + rows[at:])
    n_pub = sum(1 for t in ts if t['kind'] != 'planned')  # 'Show all 86' matches the tab's count (a planned route is not a report)
    show_all = (('<button type="button" class="alink arc-all-btn" aria-expanded="false" aria-controls="arc-rows-%s" hidden>Show all %d%s</button>'
                 % (slug, n_pub, icon('chevron-down', 16))) if fold else '')
    if page:
        return ('<div class="arc-panel" id="map">'
                '<div class="arc-grid"><div class="arc-mapcol">%s%s</div>'
                '<div class="arc-side"><div class="arc-inreg"><div class="arc-inreg-h"><h3 class="t-label" id="arc-in-%s">In this region</h3>'
                '<span class="t-mono-s arc-count" id="arc-count-%s">%s</span></div><p class="sr arc-plive" aria-live="polite"></p>'
                '<ol class="arc-rows" id="arc-rows-%s" aria-labelledby="arc-in-%s" data-map-target="%s">%s</ol>%s</div>'
                '</div></div></div>'
                % (mp, cap, slug, slug, count_line(ts, 'ml--end'), slug, slug, map_id,
                   rows, show_all))
    own = core.region_page_href(here, name)   # None unless the region has a page (and the site is registered)
    return ('<div class="arc-panel" id="region-%s">'
            '<h3 class="arc-panel-h t-h3" id="arc-ph-%s">%s</h3>'
            '<div class="arc-grid"><div class="arc-mapcol">%s%s</div>'
            '<div class="arc-side"><div class="arc-inreg"><div class="arc-inreg-h"><h4 class="t-label" id="arc-in-%s">In this region</h4>'
            '<span class="t-mono-s arc-count" id="arc-count-%s">%s</span></div><p class="sr arc-plive" aria-live="polite"></p>'
            '<ol class="arc-rows" id="arc-rows-%s" aria-labelledby="arc-in-%s arc-ph-%s" data-map-target="%s">%s</ol>%s%s</div>'
            '</div></div></div>'
            % (slug, slug, esc(name), mp, cap, slug, slug, count_line(ts, 'ml--end'), slug, slug, slug, map_id, rows,
               show_all,
               ('<a class="alink arc-reg-a" href="%s">All %s reports%s</a>' % (own, esc(name), icon('arrow-right', 16))) if own else ''))


def series_cards(ts, here):
    """One card per series: a series spans many places, so it is on no region map."""
    out = []
    for t in ts:
        meta = [core.trip_date(t, short=True)]
        if t.get('place'):
            meta.append(esc(t['place']).upper())
        d = dist_line(t)
        if d:
            meta.append(d)
        g = '<span class="arc-series-g">%s</span>' % core.tile(t, here, 'sc-%s' % t['slug'])
        out.append('<a class="arc-series" href="%s">%s<span class="arc-series-b">'
                   '<span class="arc-series-t">%s</span><span class="arc-series-m">%s%s<span class="t-mono-s arc-series-d">%s</span></span></span>'
                   '<span class="arc-series-go">%s%s</span></a>'
                   % (link(here, t['url']), g, core.title_html(t['title']), core.chip(t, variant='inline'), core.tag(series_tag(t)),
                      core.meta_items([core.nb(x) if '<' not in x else x for x in meta]), 'Read the series', icon('arrow-right', 16)))
    return '<div class="arc-series-w">%s</div>' % ''.join(out)


def other_places(site, here, meta):
    """'Not on a region map': the series card(s), then one short list per region with too few reports for a region map
    (render.py draws one from three). Every region in meta 'all_regions' without a map panel gets its #region-<slug> anchor
    here, so region links on Home and in report breadcrumbs always land (build.py --check verifies them)."""
    series = [t for t in site['published'] if t['kind'] == 'series']
    mapped = set(meta.get('regions') or [])
    groups = []
    for name in meta.get('all_regions') or []:
        if name in mapped:
            continue
        ts = [t for t in listed(site) if t['region'] == name and t['kind'] != 'series']
        ts.sort(key=lambda t: t['kind'] == 'planned')  # stable: newest first, planned last
        if ts:
            groups.append((name, content.slugify(name), ts))
    groups.sort(key=lambda g: (-sum(1 for t in g[2] if t['kind'] != 'planned'), g[0]))  # Utah 2, then A–Z
    if not series and not groups:
        return ''
    regs = ''.join('<div class="arc-oreg" id="region-%s"><div class="arc-oreg-h"><h4 class="arc-oreg-n" id="arc-on-%s">%s</h4>'
                   '<span class="t-mono-s">%s</span></div><ol class="arc-rows" aria-labelledby="arc-on-%s">%s</ol></div>'
                   % (slug, slug, esc(name), count_line(ts, 'ml--end'), slug, ''.join(region_row(t, here, region=name) for t in ts))
                   for name, slug, ts in groups)
    every = series + [t for _, _, ts in groups for t in ts]
    return ('<div class="arc-other" id="other-places"><div class="arc-inreg-h"><h3 class="t-label" id="arc-other-h">Not on a region map</h3>'
            '<span class="t-mono-s">%s</span></div>%s%s</div>'
            % (count_line(every, 'ml--end'), series_cards(series, here) if series else '',
               ('<div class="arc-oregs">%s</div>' % regs) if regs else ''))


def map_section(site, here, regs, meta):
    other = other_places(site, here, meta)
    if not regs and not other:
        return ''
    tabs = ''.join('<button type="button" role="tab" id="arc-tab-%s" aria-controls="region-%s" aria-selected="%s" tabindex="%s">'
                   '<span>%s</span><span class="arc-tab-n">%s</span></button>'
                   % (slug, slug, 'true' if i == 0 else 'false', '0' if i == 0 else '-1', esc(name),
                      count_n(sum(1 for t in ts if t['kind'] != 'planned')))
                   for i, (name, slug, ts) in enumerate(regs))
    panels = ''.join(region_panel(name, slug, ts, here, meta, i == 0, site=site) for i, (name, slug, ts) in enumerate(regs))
    # the tab row is a .tabs-x (base.css / base.js): it scrolls sideways with a fade instead of widening the page
    return ('<section class="arc-map wrap" aria-labelledby="arc-map-h"><h2 class="sr" id="arc-map-h">Map by region</h2>'
            '%s%s%s</section>'
            % (('<div class="arc-tabs-w tabs-x"><div class="arc-tabs" role="tablist" aria-label="Region" hidden>%s</div></div>' % tabs)
               if tabs else '', panels, other))


def archive_section(site, here, published=None, active=None):
    """Every report by year, with the activity filter and the year index. published / active: a subset to list instead
    of the whole site (a region page passes its region's reports and active goals); the markup and the ids are the same,
    and a subset with a single activity gets no filter row."""
    scoped = published is not None
    pub = site['published'] if published is None else list(published)
    if active is None:
        active = site.get('active_goals', site['planned'])  # completed / archived goals keep their pages, not a Planned row
    active = list(active)
    trips = pub + active
    groups = []
    for t in pub:
        y = t['date'].year if t['date'] else None
        if not groups or groups[-1][0] != y:
            groups.append((y, []))
        groups[-1][1].append(t)
    if active:
        groups.append(('Planned', list(active)))
    # activity filter: a radio group (base.js gives it one tab stop and arrow / Home / End keys; archive.js applies it)
    chips = ['<button type="button" class="fchip" role="radio" data-filter="all" aria-checked="true" tabindex="0">'
             '<span class="fchip-l">All</span></button>']
    for a, lab in core.NAV:
        k = sum(1 for t in pub if t['activity'] == a)
        if not k:
            continue
        chips.append('<button type="button" class="fchip" role="radio" data-filter="%s" aria-checked="false" tabindex="-1">'
                     '<span class="chip-sw" style="background:%s" aria-hidden="true"></span><span class="fchip-l">%s</span>'
                     '<span class="fchip-n">%s</span></button>' % (a, core.ACT[a][3], esc(lab), count_n(k)))
    # rows are core.table_row (li > a): status-only tags (planned rows say PLANNED in the date cell) + filter data for archive.js
    row = lambda t: core.table_row(t, here, tags='' if t['kind'] == 'planned' else core.trip_tags(t, shape=False),  # noqa: E731
                                   attrs=' data-kind="%s"' % t['kind'])  # core.table_row emits data-act
    body, years = [], []
    for y, ts in groups:
        gid = 'yr-%s' % str(y if y is not None else 'undated').lower()
        label = str(y) if y is not None else 'Undated'
        body.append('<div class="arc-yr" data-group="%s"><div class="arc-yr-h"><h3 class="t-label" id="%s">%s</h3>'
                    '<span class="t-mono-s arc-yr-n">%s</span></div><ol class="arc-rows2" id="%s-rows" aria-labelledby="%s">%s</ol></div>'
                    % (gid, gid, label, count_line(ts, 'ml--end'), gid, gid, ''.join(row(t) for t in ts)))
        # year index: the count is the group's published reports (archive.js rescopes it to the activity filter); none on Planned
        k = sum(1 for t in ts if t['kind'] != 'planned')
        years.append('<li data-group="%s"><a href="#%s">%s%s</a></li>'
                     % (gid, gid, label, '' if y == 'Planned' else '<span class="arc-years-n">%s</span>' % count_n(k)))
    index = ('<nav class="arc-years" aria-label="Jump to year"><ul>%s</ul></nav>' % ''.join(years)) if len(years) > 1 else ''
    # chips[0] is 'All': with one activity besides it there is nothing to choose (only a subset can be that small)
    filt = ('<div class="arc-filt" role="radiogroup" aria-label="Filter by activity" hidden>%s</div>' % ''.join(chips)
            if not (scoped and len(chips) <= 2) else '')
    return ('<section class="arc-all wrap sec" id="all-reports" aria-labelledby="all-reports-h">%s'
            '%s%s'
            '<p class="sr" id="arc-live" aria-live="polite"></p>'
            '<div class="rtab arc-table"><div aria-hidden="true">%s</div>%s</div></section>'
            % (core.section_head('All reports', count_line(trips), id_='all-reports-h'), filt, index,
               core.table_head(), ''.join(body)))


def region_fullscreen(name, slug, ts, meta, site):
    """map/<slug>/ (qa-06): the region's map at full size for phones, linked from the 44 px button in the phone map's
    corner on map/, the region's page and home. The 718 x 620 desktop render shown at 1077 px (map--fscol), as its
    hillshade is drawn; pins and journal lines stay links; data-fs="region" makes base.js centre the whole map (it draws
    many routes, and a planned one among its .mk-trk). The bar keeps the scale and the disclaimer in view as on a
    report's page; Back returns to the region's panel on map/. noindex, and out of the sitemap (index=False)."""
    here = 'map/%s/' % slug
    name_d = 'region-%s-desktop' % slug
    md = meta['maps'].get(name_d) or {}
    mp = core.map_block(None, here, [(name_d, 'fs')], 'assets/maps/', 'fs', site_maps=True, attrib=False, cls='map--fs map--fscol')
    mp = inject_acts(share_casings(mp, 'fs-' + slug), site.get('by_slug') or {t['slug']: t for t in site['trips']})
    scale = core.fs_scale(None, name_d, core.FS_WIDTHS['map--fscol'], site_maps=True)
    body = ('<h1 class="sr">%s: map</h1><div class="wrap fs-bar"><a class="btn" href="../#region-%s">%sBack to the map</a>'
            '<span class="t-small fs-pan">Drag to pan</span><div class="fs-line2">%s<span class="t-mono-s fs-nav">NOT FOR NAVIGATION</span></div></div>'
            '<div class="fs-map" data-fs="region" tabindex="0" role="region" aria-label="Map, scroll to pan">%s</div>'
            '<div class="wrap fs-foot">%s%s%s</div>'
            % (esc(name), slug, icon('arrow-left', 18), scale, mp, legend(ts, md),
               region_key(site, meta['maps'], [name_d], 'keyrow--p'),
               core.map_caption(['Pins mark each start and link to the report', 'Full tracks, not trimmed', 'North up'])))
    title = '%s map' % name
    return core.Page(here, core.document(here, title, body, 'Full-size map of %s.' % name, active='map', body_cls='p-fsmap',
                                         extra_head='<meta name="robots" content="noindex">'), title, index=False)


def build(site):
    here = HERE
    meta = site_meta()
    regs = regions(site, meta)
    body = head_block(site, regs, meta) + map_section(site, here, regs, meta) + archive_section(site, here)
    desc = 'Every trip report by region and by year, with GPX tracks; region maps where there are three or more reports.'
    head = ''
    if regs:
        # the first region panel's map is the first-screen image: preload its hillshade and base layer (other panels stay lazy)
        rs = regs[0][1]
        head = core.map_preloads(None, here, [('region-%s-desktop' % rs, 'desktop'), ('region-%s-phone' % rs, 'phone')],
                                 'assets/maps/', site_maps=True)
    return ([core.Page(here, core.document(here, 'Map & archive', body, desc, active='map', body_cls='p-archive', extra_head=head,
                                     page_bar=('Map & archive', 'arc-title'),
                                     image=core.site_share()),
                       'Map & archive')]
            + [region_fullscreen(name, slug, ts, meta, site) for name, slug, ts in regs])
