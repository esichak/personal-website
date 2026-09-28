"""Section index pages — /ski/, /climbing/, /hiking/, /mountain-biking/, /other/ (one module, five pages).

Anatomy: breadcrumb, H1 with the activity disc, Mono-S totals line (counts on line 1, places by size on line 2), optional
filter band, then either the Ski list + sticky region map panel, or a Featured block followed by "More <x>".
Filter bands: Ski (seasons), Other (sub-types), Mountain Biking and Hiking (years). The long MTB and Hiking lists are
grouped by year under their "More <x>" head (the Ski season markup, one level down). section.js turns each band into a
radio group that filters [data-f]; without JS the segments are links that jump to the group.
Hiking adds the series section (after Featured) and a Planned block (shown under All only); Mountain Biking adds a
full-width elevation profile; Other adds one line under the filter band naming the sub-types without reports.
"""
import json
import os
import re

import content
import markdown

from sitegen import core
from sitegen.core import esc, U, n, link, icon, FT

MORE = {'climb': 'More climbs', 'hike': 'More hikes', 'mtb': 'More rides', 'other': 'More reports', 'ski': 'More ski tours'}
OTHER_LINE = "Paddleboarding, rafting, kayaking, mountaineering and anything that isn't a ski, climb, hike or ride."
AVY = [('Eastern Sierra Avalanche Center', 'https://www.esavalanche.org/'),
       ('Sierra Avalanche Center', 'https://www.sierraavalanchecenter.org/')]
FULL_TRACK = 'full track, not trimmed'
MAX_AREAS = 3
YEAR_ACTS = ('mtb', 'hike')  # long lists grouped by year, with a year band
YEAR_ROWS = 20  # ... when 'More <x>' has more rows than this (Climbing and Other stay flat)


# ---------------------------------------------------------------- small helpers

def slug(s):
    return content.slugify(str(s).replace('–', '-').replace('—', '-'))


def plural(k, word, words=None):
    return '%s %s' % (n(k), word if k == 1 else (words or word + 'S'))


def words_list(ws, conj='or'):
    """'rafting, kayaking or mountaineering'."""
    return ws[0] if len(ws) == 1 else '%s %s %s' % (', '.join(ws[:-1]), conj, ws[-1])


def reports_of(site, act):
    return [t for t in site['published'] if t['activity'] == act]


def area_names(ts):
    """Where the reports are, biggest first: the distinct regions ordered by (-reports, name); when every report shares one
    region, the distinct places inside it instead, ordered the same way (climbing: LOVER'S LEAP · KINGSBURY GRADE)."""
    def by_size(key):
        k = {}
        for t in ts:
            v = (t.get(key) or '').strip()
            if v:
                k[v] = k.get(v, 0) + 1
        return sorted(k, key=lambda v: (-k[v], v))
    names = by_size('region')
    if len(names) == 1:
        names = by_size('place') or names
    return names


def areas(ts):
    """The places items of the totals line: every name when there are at most MAX_AREAS + 1 (never '1 MORE'), otherwise
    the MAX_AREAS biggest and 'N MORE'."""
    names = area_names(ts)
    if len(names) <= MAX_AREAS + 1:
        return [core.nb(esc(x).upper()) for x in names]
    return [core.nb(esc(x).upper()) for x in names[:MAX_AREAS]] + [core.nb('%d MORE' % (len(names) - MAX_AREAS))]


def totals_line(ts, act=None, planned=()):
    """Counts and places only (a meta_items() line in two lines: .ml-br after the counts): '4 REPORTS · INCL. 1 SERIES ·
    + 1 PLANNED ROUTE' / 'LAKE TAHOE · OREGON · …'. No summed distance or gain: climbing gain is the walk-off only, and one
    series would dominate the hiking totals. act is accepted for symmetry with the other section helpers."""
    counts = core.count_items(ts, list(planned))
    return core.meta_items(counts + areas(ts), br_after=len(counts) - 1)


def count_html(k, cls):
    """Visible '5'; assistive tech hears ', 5 reports' after the segment / tab name."""
    return ('<span class="%s"><span class="sr">, </span>%d<span class="sr"> %s</span></span>'
            % (cls, k, 'report' if k == 1 else 'reports'))


def map_caption(t):
    """The shared caption (core.map_caption), as on the report. Phones (< 560) keep one line — the date and North up —
    since the credit moves into the map tag and the footer (.mapcap-2) and the report carries 'full track, not trimmed'."""
    first = []
    if t['date']:
        first.append('Track: %s' % core.fdate(t['date'], 'short'))
    first.append((FULL_TRACK, 'sec-cap-x'))
    first.append('North up')
    return core.map_caption(first)


def arrow_link(href, text, cls='alink'):
    return '<a class="%s" href="%s">%s%s</a>' % (cls, href, text, icon('arrow-right', 16))


def writeup(t, limit=600):
    """Eric's write-up, verbatim when short; a plain excerpt when long (the report has the rest)."""
    if not t['body_md']:
        ex = core.excerpt(t, 220)
        return ('<p class="sec-prose">%s</p>' % esc(ex)) if ex else ''
    if len(markdown.plain(t['body_md'])) <= limit:
        return '<div class="prose sec-prose">%s</div>' % markdown.to_html(t['body_md'])
    return '<p class="sec-prose">%s</p>' % esc(markdown.plain(t['body_md'], limit))


# ---------------------------------------------------------------- header + filter band

def header(act, here, ts, intro='', planned=()):
    lab = core.ACT[act][0]
    crumbs = '<a href="%s">Reports</a><span aria-hidden="true">/</span><span aria-current="page">%s</span>' % (link(here, ''), esc(lab))
    return ('<section class="sec-head wrap" aria-labelledby="sec-title">'
            '<nav class="crumbs t-mono-s" aria-label="Breadcrumb">%s</nav>'
            '<div class="sec-h1row">%s<h1 id="sec-title" class="t-d1">%s</h1></div>'
            '<p class="sec-stats">%s</p>%s</section>'
            % (crumbs, core.disc(act, 48), esc(lab), totals_line(ts, act, planned),
               ('<p class="sec-intro">%s</p>' % esc(intro)) if intro else ''))


def band(label, segs, scope_id):
    """Segmented filter as links: without JS they jump to the group; section.js turns them into filters.
    segs: [(key, text, count|None, href|None (None = disabled), icon_name|None)]."""
    out = []
    for i, (key, text, cnt, href, ic) in enumerate(segs):
        inner = '%s<span>%s</span>%s' % (icon(ic, 20) if ic else '', esc(text), count_html(cnt, 'sec-seg-n') if cnt else '')
        if href is None:
            out.append('<a class="sec-seg-a" role="link" aria-disabled="true">%s</a>' % inner)
        else:
            out.append('<a class="sec-seg-a" href="%s" data-filter="%s"%s>%s</a>'
                       % (href, key, ' aria-current="true"' if i == 0 else '', inner))
    return ('<div class="sec-band"><div class="wrap sec-band-in">'
            '<nav class="sec-seg" aria-label="%s" data-filter-nav="%s">%s</nav>'
            '<p class="sr" aria-live="polite" data-filter-live></p></div></div>'
            % (esc(label), scope_id, ''.join(out)))


# ---------------------------------------------------------------- featured block

def featured(t, here, full_row='', fkey=None):
    """Datum featured anatomy: label → chips → H2 row (Download GPX bottom-aligned) → place line → strip → map, key row,
    caption | photo + write-up.

    With no chart under the map, the write-up moves under the map on desktop and a second photo fills the right column
    (ClimbingIndex artboard), so neither column ends in a large blank. Phones (< 760) get the compact block (CSS): no GPX
    button, strip sub-lines, footnote or charts (the report keeps them), one photo and four lines of the write-up.
    The map is the page's LCP image: eager, with page() preloading it (core.map_preloads). fkey: the block's filter key
    (data-f; the year on MTB / Hiking), default the sub-type (Other)."""
    act = t['activity']
    href = link(here, t['url'])
    gpx = link(here, t['url'] + t['slug'] + '.gpx')
    meta = core.render_meta(t)
    date = core.trip_date(t)
    # phones: chips-only chip row, the date leads the place line instead (as on the report title block)
    chips = '%s%s<span class="t-mono-s sec-feat-date">%s</span>' % (core.chip(t, variant='title'), core.trip_tags(t), date)
    place_html = ('<p class="t-mono-s sec-feat-place">%s</p>'
                  % core.meta_items([(date, 'sec-feat-pdate')] + core.place_line(t, items=True)))
    variants = [('map-col', 'col'), ('map-phone', 'phone')]
    map_ = core.map_block(t, here, variants, t['url'] + 'map/', 'fm', eager=True, cls='map--nowide sec-feat-mapv')
    key = core.feature_key(t, variants, miles=True)
    ch = meta.get('charts', {})
    chart = ''
    # charts are hidden on phones (the report has them), so no phone variant is inlined
    if act == 'hike' and 'profile-col' in ch:
        chart += profile_block(t, here, [('profile-col', 'col')], 'fp', cls='chart--nowide')
    if 'speed-col' in ch:
        chart += speed_block(t, here)
    text_left = not chart and bool(t['photos'])
    photos = t['photos'][:2 if text_left else 1]
    pics = ''.join(core.photo(t, p, here, sizes='(min-width: 1200px) 506px, (min-width: 760px) 50vw, 100vw',
                              cls='sec-feat-photo' + (' sec-feat-photo--p' if core.photo_ar(p) < 1 else ''))
                   for p in photos)
    body = writeup(t)
    txt = ('<div class="sec-feat-txt">%s%s</div>'
           % (('<h3 class="t-h3 sec-feat-h3">Trip report</h3>%s' % body) if body else '',
              arrow_link(href, 'Read report', 'alink sec-read')))
    grid_cls = ('' if photos else ' sec-feat-grid--nophoto') + (' sec-feat-grid--txtl' if text_left else '')
    return ('<section class="sec-feat wrap" id="featured" aria-labelledby="feat-title" data-f="%s">'
            '<p class="t-label sec-feat-l">Featured</p>'
            '<div class="chips sec-feat-chips">%s</div>'
            '<div class="sec-feat-h"><h2 class="t-h2 sec-feat-t" id="feat-title"><a href="%s">%s</a></h2>%s'
            '<a class="btn btn--ink sec-feat-gpx" href="%s" download>%sDownload GPX</a></div>'
            '<div class="sec-feat-strip">%s%s</div>'
            '<div class="sec-feat-grid%s"><div class="sec-feat-map">%s%s%s%s</div>'
            '<div class="sec-feat-side">%s%s</div></div>%s</section>'
            % (esc(fkey if fkey is not None else (t.get('subtype') or '')), chips, href, core.title_html(t['title']), place_html,
               gpx, icon('download', 18), core.strip(core.strip_cells(t)), core.stats_note(t), grid_cls,
               map_, key, map_caption(t), chart, ('<div class="sec-feat-pics">%s</div>' % pics) if pics else '', txt, full_row))


def profile_block(t, here, variants, ns, cls=''):
    ch = core.render_meta(t).get('charts', {})
    first = next((ch[nm] for nm, _ in variants if nm in ch), None)
    if not first:
        return ''
    st = t['stats']
    hi = st.get('high_m') if st.get('high_m') is not None else first.get('gps_max_ft', 0) / FT
    lo = st.get('low_m') if st.get('low_m') is not None else first.get('min_ft', 0) / FT
    bits = [U(core.nb('GPS MAX %s FT' % n(hi * FT)), core.nb('GPS MAX %s M' % n(hi))),
            U(core.nb('MIN %s FT' % n(lo * FT)), core.nb('MIN %s M' % n(lo)))]
    bits += core.vx_line(ch, variants, nowide=('chart--nowide' in cls) or None, items=True)
    return ('<div class="sec-prof"><div class="sec-chart-h"><h3 class="t-label" id="%s-h">Elevation</h3><p class="t-mono-s">%s</p></div>'
            '<div role="group" aria-labelledby="%s-h">%s</div></div>'
            % (ns, core.meta_items(bits), ns, core.chart_block(t, here, variants, ns, cls=cls)))


def speed_block(t, here):
    return ('<div class="sec-prof"><div class="sec-chart-h"><h3 class="t-label" id="fs-h">Speed</h3>'
            '<p class="t-mono-s">%s</p>%s</div>'
            '<div role="group" aria-labelledby="fs-h">%s</div></div>'
            % (core.speed_meta(t), core.key_row(['speed'], 'keyrow--inline', label='Speed key'),
               core.chart_block(t, here, [('speed-col', 'col')], 'fs', cls='chart--nowide')))


def pick_featured(ts):
    singles = [t for t in ts if t['kind'] == 'trip']
    return next((t for t in singles if t['featured']), singles[0] if singles else None)


def row(t, here, fkey=None):
    """The shared list row. fkey(t) -> the row's filter key (data-f: the sub-type on Other, the year on MTB / Hiking), so
    the filter band can show / hide it; None: no filter."""
    return core.trip_row(t, here, filter_key=fkey(t) if fkey else None)


def sub_key(t):
    return t.get('subtype') or ''


def year_key(t):
    """A non-ski trip's year ('2022'); '' when undated (shown under All only)."""
    return t.get('season') or ''


def years_of(t):
    """Every year a report covers: a series spans its days' years, anything else its start year."""
    if t['kind'] == 'series' and t['days']:
        ys = sorted({str(d['date'].year) for d in t['days'] if d.get('date')}, reverse=True)
        if ys:
            return ys
    return [year_key(t)] if year_key(t) else []


def year_groups(rows_ts, here):
    """The Ski season markup one level down (H3 under the 'More <x>' head), newest year first; undated rows last."""
    years = sorted({year_key(t) for t in rows_ts if year_key(t)}, reverse=True)
    if any(not year_key(t) for t in rows_ts):
        years.append('')
    out = []
    for y in years:
        rs = [t for t in rows_ts if year_key(t) == y]
        yid = 'year-' + (y or 'undated')
        out.append('<section class="sec-season sec-year" id="%s" aria-labelledby="%s-h" data-f="%s">'
                   '<div class="sec-div"><h3 class="sec-div-t" id="%s-h">%s</h3><span class="t-mono-s">%s</span></div>'
                   '<ol class="tlist sec-tlist">%s</ol></section>'
                   % (yid, yid, y, yid, esc(y or 'Undated'), plural(len(rs), 'REPORT'),
                      ''.join(row(t, here, year_key) for t in rs)))
    return ''.join(out)


def more_list(title, rows_ts, here, id_='more', meta=None, extra='', fkey=None, by_year=False, sec_f=None):
    """'More <x>': H2 section head with the count, then one list, or year groups (by_year). sec_f: a filter key for the
    whole block (the Planned block's 'planned' shows under All only)."""
    if not rows_ts:
        return ''
    meta = meta if meta is not None else plural(len(rows_ts), 'REPORT')
    body = (year_groups(rows_ts, here) if by_year
            else '<ol class="tlist sec-tlist">%s</ol>' % ''.join(row(t, here, fkey) for t in rows_ts))
    return ('<section class="sec-more wrap" aria-labelledby="%s-h"%s>%s%s%s</section>'
            % (id_, (' data-f="%s"' % esc(sec_f)) if sec_f else '', core.section_head(title, meta, id_=id_ + '-h'), body, extra))


# ---------------------------------------------------------------- hiking: series section (HikingIndex artboard)

def series_block(t, here, fkey=None):
    """Open section after Featured: head (title link · date range), overview map | tag, place line, the series page's
    stats, first photo of the first three days with photos, first written day, actions. The map is the 390×600 render
    the series page uses for its column, so it shows near 1:1 (6 of 12 columns at 560–999, 5 at 1000–1199, 4 from 1200).
    fkey: its filter key (data-f: the space-joined years of its days) when the page has a year band."""
    href = link(here, t['url'])
    days = t['days']
    written = [d for d in days if d['body_md']]
    mi, km = core.dist_vals(t['stats'].get('distance_km'))
    cells = []
    if mi:
        cells.append(('Distance recorded', U(mi, km, 'mi', 'km')))
    cells.append(('Days recorded', n(len(days))))
    if written:
        cells.append(('Write-ups', '%s<span class="unit">day%s</span>' % (n(len(written)), '' if len(written) == 1 else 's')))
    stats = ''.join('<div class="sc"><dt class="t-label">%s</dt><dd class="t-data-m">%s</dd></div>' % c for c in cells)
    firsts = [d['photos'][0] for d in days if d['photos']][:3]
    pics = ''.join(core.photo(t, p, here, sizes='(min-width: 1200px) 224px, (min-width: 560px) 15vw, 30vw', caption=False,
                              cls='sec-ser-ph')
                   for p in firsts)
    sample = ''
    if written:
        d = written[0]
        lab = 'Day %s' % esc(str(d['label'])) + ((' · ' + esc(d['title'])) if d.get('title') else '')
        sample = ('<div class="sec-ser-day"><p class="t-label">%s</p><p class="t-excerpt sec-ser-ex">%s</p></div>'
                  % (lab, esc(markdown.plain(d['body_md'], 200))))
    mp = core.map_block(t, here, [('overview-phone', 'desktop')], t['url'] + 'map/', 'ser', cls='sec-ser-map')
    place = core.meta_items(core.place_line(t, items=True))
    return ('<section class="sec-ser wrap" id="series" aria-labelledby="ser-title"%s>%s'
            '<div class="sec-ser-g">'
            '<div class="sec-ser-mapc">%s%s</div>'
            '<div class="sec-ser-b">'
            '<div class="chips">%s</div>%s<dl class="sec-ser-stats">%s</dl>'
            '%s%s'
            '<div class="sec-ser-a">%s<a class="btn" href="%s#days">%sDay by day</a></div>'
            '</div></div></section>'
            % ((' data-f="%s"' % esc(fkey)) if fkey is not None else '',
               core.section_head('<a href="%s">%s</a>' % (href, esc(t['title'])), core.trip_date(t), id_='ser-title'),
               mp, core.map_caption(['North up']), core.tag('Series'),
               ('<p class="t-mono-s sec-ser-place">%s</p>' % place) if place else '', stats,
               ('<div class="sec-ser-phs">%s</div>' % pics) if pics else '', sample,
               arrow_link(href, 'Read the series', 'btn btn--ink'), href, icon('list', 18)))


# ---------------------------------------------------------------- ski: seasons + region panel

def dedupe_roads(svg, ns):
    """Road casing and road fill share one path: define it once and draw it twice with <use> (halves the Alps map)."""
    i = [0]

    def rep(m):
        d = m.group(1)
        if len(d) < 2000:
            return m.group(0)
        i[0] += 1
        pid = '%s-rd%d' % (ns, i[0])
        return ('<defs><path id="%s" d="%s"/></defs><use href="#%s" class="mk-roadc"/><use href="#%s" class="mk-road"/>'
                % (pid, d, pid, pid))
    return re.sub(r'<path class="mk-roadc" d="([^"]+)"/><path class="mk-road" d="\1"/>', rep, svg)


def ski_regions(ts):
    """The panel's regions, biggest first (as on map/); the sort is stable, so ties keep the newest trip's region first.
    Only regions with a rendered ski panel map."""
    regions = []
    for t in ts:  # newest first
        if t.get('region') and t['region'] not in regions:
            regions.append(t['region'])
    regions.sort(key=lambda r: -sum(1 for t in ts if t.get('region') == r))
    meta_p = os.path.join(core.ROOT, 'rendered', 'site', 'meta.json')
    have = json.load(open(meta_p))['maps'] if os.path.exists(meta_p) else {}
    return [r for r in regions if ('ski-%s-desktop' % slug(r)) in have]


def ski_panel(ts, here):
    regions = ski_regions(ts)
    if not regions:
        return ''
    tabs, panels = [], []
    for i, r in enumerate(regions):
        s = slug(r)
        cnt = len([t for t in ts if t.get('region') == r])
        sel = i == 0
        tabs.append('<button type="button" role="tab" id="rt-%s" aria-controls="rp-%s" aria-selected="%s" tabindex="%s">'
                    '<span>%s</span>%s</button>'
                    % (s, s, 'true' if sel else 'false', '0' if sel else '-1', esc(r), count_html(cnt, 'sec-tab-n')))
        mb = core.map_block(None, here, [('ski-%s-desktop' % s, 'desktop'), ('ski-%s-phone' % s, 'phone')],
                            'assets/maps/', 'rm-' + s, site_maps=True, eager=sel)
        mb = dedupe_roads(mb, 'rm-' + s)
        panels.append('<div class="sec-rp" role="tabpanel" id="rp-%s" aria-labelledby="rt-%s"%s>'
                      '<p class="t-label sec-rp-l">%s</p>%s</div>' % (s, s, '' if sel else ' hidden', esc(r), mb))
    # the shared map caption; the hover hint is dropped on touch screens and without JS (.sec-pcap-h)
    cap = '<div class="sec-pcap">%s</div>' % core.map_caption([('Hover a report to highlight its track', 'sec-pcap-h'), 'North up'])
    return ('<aside class="sec-panel" aria-labelledby="panel-h"><div class="sec-panel-in">'
            '<h2 class="sec-panel-h" id="panel-h">Ski map by region</h2>'
            '<div class="tabs-x sec-tabs-x"><div class="sec-tabs" role="tablist" aria-label="Region">%s</div></div>'
            '<div class="map sec-maps" id="ski-map">%s</div>%s</div></aside>'
            % (''.join(tabs), ''.join(panels), cap))


def ski_body(ts, here):
    seasons = []
    for t in ts:
        if t['season'] not in seasons:
            seasons.append(t['season'])
    groups = []
    for s in seasons:
        rows = [t for t in ts if t['season'] == s]
        sid = 'season-' + slug(s)
        groups.append('<section class="sec-season" id="%s" aria-labelledby="%s-h" data-f="%s">'
                      '<div class="sec-div"><h2 class="sec-div-t" id="%s-h">%s season</h2><span class="t-mono-s">%s</span></div>'
                      '<ol class="tlist sec-tlist">%s</ol></section>'
                      % (sid, sid, slug(s), sid, esc(s), plural(len(rows), 'REPORT'), ''.join(row(t, here) for t in rows)))
    avy = ('<div class="sec-avy"><p class="t-label">Current avalanche forecasts</p><ul>%s</ul></div>'
           % ''.join('<li>%s</li>' % arrow_link(u, esc(nm)) for nm, u in AVY))
    # the panel comes first in reading order, as it shows below 960 (tabs + map above the seasons, as on map/); from 960
    # the grid puts it in the right-hand column beside the list
    return ('<div class="sec-split wrap" id="reports">%s<div class="sec-list" data-map-target="ski-map">%s</div></div>'
            '<div class="wrap sec-avy-w">%s</div>' % (ski_panel(ts, here), ''.join(groups), avy)), seasons


# without JS every region map shows (no tabs), so below 960 the panel moves under the list
NOSCRIPT = ('<noscript><style>.sec-rp[hidden]{display:block!important}.sec-rp+.sec-rp{margin-top:24px}'
            '.sec-rp-l{display:block!important}.sec-tabs-x,.sec-pcap-h{display:none!important}'
            '.sec-panel-in{position:static!important}'
            '@media (max-width:959.98px){.sec-panel{order:1!important;margin:var(--sec) 0 0!important}}</style></noscript>')


# ---------------------------------------------------------------- other: sub-types without reports

def none_line(subs):
    """'No rafting, kayaking or mountaineering reports yet.' — one line under the filter band (the segments stay, disabled)."""
    if not subs:
        return ''
    return ('<p class="t-small sec-none wrap">No %s reports yet.</p>'
            % esc(words_list([core.SUB_WORD[s].lower() for s in subs])))


# ---------------------------------------------------------------- pages

def act_words(act, ts):
    """'backcountry ski'; on Other the sub-types the reports have ('paddleboarding')."""
    if act == 'other':
        subs = []
        for t in ts:
            w = core.SUB_WORD.get(t.get('subtype') or '', t.get('subtype') or '')
            if w and w.lower() not in subs:
                subs.append(w.lower())
        if subs:
            return words_list(subs, 'and')
    return core.ACT[act][0].lower()


def description(act, ts):
    """'61 mountain biking trip reports (Santa Cruz, Lake Tahoe, Bay Area and 2 more regions), each with …' — the regions
    in the totals line's order (biggest first); every name when there are at most MAX_AREAS + 1."""
    regions = []
    for t in ts:
        if t.get('region') and t['region'] not in regions:
            regions.append(t['region'])
    regions.sort(key=lambda r: (-sum(1 for t in ts if t.get('region') == r), r))
    where = ''
    if len(regions) > MAX_AREAS + 1:
        k = len(regions) - MAX_AREAS
        where = ' (%s and %d more regions)' % (', '.join(regions[:MAX_AREAS]), k)
    elif regions:
        where = ' (%s)' % words_list(regions, 'and')
    word = act_words(act, ts)
    if len(ts) == 1:
        return '1 %s trip report%s, with the full GPX track and map.' % (word, where)
    return '%d %s trip reports%s, each with the full GPX track and map.' % (len(ts), word, where)


def og_image(ts):
    for t in ts:
        if t['photos']:
            return t['url'] + t['photos'][0]['file']
    return None


def year_segs(years, shown, feat, ser, rest):
    """The year band: All, then each year with its published reports (rows + featured + series). A segment jumps to its
    year group without JS; a year whose only report is the featured trip or the series jumps there instead."""
    grouped = {year_key(t) for t in rest}
    segs = [('all', 'All', None, '#reports', None)]
    for y in years:
        k = sum(1 for t in shown if y in years_of(t))
        if y in grouped:
            href = '#year-' + y
        elif feat is not None and year_key(feat) == y:
            href = '#featured'
        else:
            href = '#series'
        segs.append((y, y, k, href, None))
    return segs


def page(act, site):
    here = core.section_url(act)
    ts = reports_of(site, act)
    body = []
    extra_head = ''
    intro = OTHER_LINE if act == 'other' else ''
    planned = [t for t in site['planned'] if t['activity'] == act]
    body.append(header(act, here, ts, intro, planned))
    feat = None
    if act == 'ski':
        main, seasons = ski_body(ts, here)
        segs = [('all', 'All', None, '#reports', None)]
        segs += [(slug(s), s, len([t for t in ts if t['season'] == s]), '#season-' + slug(s), None) for s in seasons]
        if len(seasons) > 1:
            body.append(band('Filter by season', segs, 'reports'))
        body.append(main)
        extra_head = NOSCRIPT
    else:
        feat = pick_featured(ts)
        ser = next((t for t in ts if t['kind'] == 'series' and t['days']), None) if act == 'hike' else None
        rest = [t for t in ts if t is not feat and not (act == 'hike' and t['kind'] == 'series')]
        shown = ([feat] if feat else []) + ([ser] if ser else []) + rest
        years = sorted({y for t in shown for y in years_of(t)}, reverse=True)
        by_year = act in YEAR_ACTS and len(rest) > YEAR_ROWS and len(years) > 1
        if act == 'other':
            counts = {s: len([t for t in ts if t.get('subtype') == s]) for s in content.OTHER_SUBTYPES}
            segs = [('all', 'All', None, '#reports', 'OTH')]
            for s in content.OTHER_SUBTYPES:
                segs.append((s, core.SUB_WORD[s], counts[s] or None, ('#featured' if counts[s] else None), core.SUB_ICON[s]))
            body.append(band('Filter by type', segs, 'reports'))
            body.append(none_line([s for s in content.OTHER_SUBTYPES if not counts[s]]))
        if by_year:
            body.append(band('Filter by year', year_segs(years, shown, feat, ser, rest), 'reports'))
        body.append('<div id="reports" class="sec-reports%s">' % (' sec-reports--band' if (act == 'other' or by_year) else ''))
        if feat:
            full = ''
            if act == 'mtb':
                full = profile_block(feat, here, [('profile-wide', 'wide'), ('profile-col', 'col')], 'fw')
                full = ('<div class="sec-feat-full">%s</div>' % full) if full else ''
            body.append(featured(feat, here, full_row=full, fkey=year_key(feat) if by_year else None))
            # the featured map is the LCP image: preload the variant each breakpoint shows
            extra_head = core.map_preloads(feat, here, [('map-col', 'col'), ('map-phone', 'phone')], feat['url'] + 'map/',
                                           nowide=True)
        if ser:
            body.append(series_block(ser, here, fkey=' '.join(years_of(ser)) if by_year else None))
        body.append(more_list(MORE[act], rest, here, fkey=sub_key if act == 'other' else None, by_year=by_year))
        if act == 'hike' and planned:
            body.append(more_list('Planned', planned, here, id_='planned', meta=plural(len(planned), 'PLANNED ROUTE'),
                                  sec_f='planned' if by_year else None))
        body.append('</div>')
    title = '%s trip reports' % core.ACT[act][0]
    return core.Page(here, core.document(here, title, ''.join(body), description(act, ts), active=act,
                                         image=og_image(([feat] if feat else []) + ts), extra_head=extra_head,
                                         body_cls='p-section p-section--%s' % act), title)


def build(site):
    return [page(act, site) for act in ('ski', 'climb', 'hike', 'mtb', 'other')]
