"""Section index pages — /ski/, /climbing/, /hiking/, /mountain-biking/, /other/ (one module, five pages).

Anatomy: breadcrumb, H1 with the activity disc, Mono-S totals line, optional filter band (Ski: seasons, Other: sub-types),
then either the Ski list + sticky region map panel, or a Featured block followed by "More <x>".
Hiking adds the series card (under the header) and a Planned block; Mountain Biking adds a full-width elevation profile;
Other adds the "first reports coming" empty states for sub-types without reports.
"""
import json
import os
import re

import content
import markdown

from sitegen import core
from sitegen.core import esc, U, U_sub, n, link, icon, FT, MI

MORE = {'climb': 'More climbs', 'hike': 'More hikes', 'mtb': 'More rides', 'other': 'More reports', 'ski': 'More ski tours'}
OTHER_LINE = "Paddleboarding, rafting, kayaking, mountaineering, and anything that isn't a ski, climb, hike or ride."
EMPTY_LINE = {  # only what every report on the site already has (track, map, strip, chart), no promised extra fields
    'Rafting': 'Rafting reports will show the full river track on a map, distance and moving time.',
    'Kayaking': 'Kayaking reports will show the paddled track on a map, distance, moving time and pace.',
    'Mountaineering': 'Mountaineering reports will show the full track on a map, gain, GPS max and an elevation profile.',
    'SUP': 'Paddleboarding reports will show the paddled track on a map, distance, moving time and pace.',
}
AVY = [('Eastern Sierra Avalanche Center', 'https://www.esavalanche.org/'),
       ('Sierra Avalanche Center', 'https://www.sierraavalanchecenter.org/')]
FULL_TRACK = 'full track, not trimmed'


# ---------------------------------------------------------------- small helpers

def slug(s):
    return content.slugify(str(s).replace('\u2013', '-').replace('\u2014', '-'))


def plural(k, word, words=None):
    return '%s %s' % (n(k), word if k == 1 else (words or word + 'S'))


def reports_of(site, act):
    return [t for t in site['published'] if t['activity'] == act]


def totals_line(ts):
    """'10 REPORTS · 264 MI · 101,066 FT GAIN' — every figure computed from the content, units switchable."""
    bits = [plural(len(ts), 'REPORT')]
    km = sum(t['stats'].get('distance_km') or 0 for t in ts)
    gain = sum(t['stats'].get('gain_m') or 0 for t in ts)
    if km:
        mi, k = core.dist_vals(km)
        bits.append(U(mi + ' MI', k + ' KM'))
    if gain >= 30:
        bits.append(U(n(gain * FT) + ' FT GAIN', n(gain) + ' M GAIN'))
    return ' · '.join(bits)


def unit(u):
    return '<span class="unit">%s</span>' % u


def cell_dist(st):
    mi, km = core.dist_vals(st.get('distance_km'))
    if not mi:
        return None
    return ('Distance', U(mi, km, 'mi', 'km'), U_sub(mi, km, 'mi', 'km'))


def cell_m(lab, m):
    if m is None:
        return None
    return (lab, U(n(m * FT), n(m), 'ft', 'm'), U_sub(n(m * FT), n(m), 'ft', 'm'))


def cell_moving(t):
    st = t['stats']
    if not st.get('moving_s'):
        return None
    sub = ('Start ' + core.ftime(t['start_time'])) if t.get('start_time') else ''
    return ('Moving', '%s%s' % (core.hm(st['moving_s']), unit('h:mm')), sub)


def is_flat(t):
    st = t['stats']
    return t['activity'] == 'other' and (st.get('gain_m') or 0) < 30


def beta_value(t, label):
    for b in t['beta']:
        if str(b.get('label', '')).lower() == label.lower():
            return str(b.get('value', ''))
    return ''


def feat_cells(t):
    """Data-strip cells for the featured report, per activity (only values the content has)."""
    st = t['stats']
    act = t['activity']
    cells = []
    if act == 'climb':
        p = beta_value(t, 'Pitches')
        if p:
            routes = [r for r in beta_value(t, 'Routes').split(',') if r.strip()]
            cells.append(('Pitches', esc(p), plural(len(routes), 'ROUTE') if routes else ''))
        cells += [cell_dist(st), cell_m('GPS max', st.get('high_m')), cell_moving(t)]
    elif is_flat(t):
        cells += [cell_dist(st), cell_moving(t)]
        if st.get('distance_km') and st.get('moving_s'):
            mins = st['moving_s'] / 60.0
            mi = st['distance_km'] * 1000 / MI
            per_mi, per_km = mins / mi, mins / st['distance_km']
            cells.append(('Avg pace', U(n(per_mi), n(per_km), 'min/mi', 'min/km'),
                          U_sub(n(per_mi), n(per_km), 'min/mi', 'min/km') + ' · MOVING'))
    else:
        cells += [cell_dist(st), cell_m('Gain', st.get('gain_m')), cell_m('GPS max', st.get('high_m')), cell_moving(t)]
        if act == 'mtb' and st.get('distance_km') and st.get('moving_s'):
            h = st['moving_s'] / 3600.0
            mph, kmh = st['distance_km'] * 1000 / MI / h, st['distance_km'] / h
            cells.append(('Avg speed', U('%.1f' % mph, '%.1f' % kmh, 'mph', 'km/h'),
                          U_sub('%.1f' % mph, '%.1f' % kmh, 'mph', 'km/h') + ' · MOVING'))
    return [c for c in cells if c]


def strip(cells):
    out = ''.join('<div class="strip-c"><dt class="t-label">%s</dt><dd class="t-data-xl strip-v">%s</dd>%s</div>'
                  % (lab, val, ('<dd class="t-mono-s strip-s">%s</dd>' % sub) if sub else '') for lab, val, sub in cells)
    return '<dl class="strip" style="--cells:%d" aria-label="Trip stats">%s</dl>' % (max(len(cells), 1), out)


def stats_note(t):
    bits = ['Stats from the Garmin recording via Strava.']
    track = beta_value(t, 'Track')
    if track:
        bits.append('Track: %s.' % esc(track.rstrip('.')))
    if is_flat(t):
        bits.append('Pace is moving time divided by distance.')
    else:
        if t['activity'] == 'mtb':
            bits.append('Average speed is distance divided by moving time.')
        bits.append('GPS max is the highest point in the GPX file, not a surveyed summit height.')
    return '<p class="strip-note">%s</p>' % ' '.join(bits)


def map_caption(t, extra=''):
    first = []
    if t['date']:
        first.append('Track: Garmin, %s' % core.fdate(t['date'], 'short'))
    first.append(FULL_TRACK)
    first.append('North up')
    return ('<div class="mapcap sec-mapcap"><p class="mapcap-t"><span>%s</span>'
            '<span>Terrain: AWS Terrain Tiles · Map data © OpenStreetMap contributors · Not for navigation</span></p>%s</div>'
            % (' · '.join(first), extra))


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

def header(act, here, ts, intro=''):
    lab = core.ACT[act][0]
    crumbs = '<a href="%s">Reports</a><span aria-hidden="true">/</span><span aria-current="page">%s</span>' % (link(here, ''), esc(lab))
    return ('<section class="sec-head wrap" aria-labelledby="sec-title">'
            '<nav class="crumbs t-mono-s" aria-label="Breadcrumb">%s</nav>'
            '<div class="sec-h1row">%s<h1 id="sec-title" class="t-d1">%s</h1></div>'
            '<p class="sec-stats">%s</p>%s</section>'
            % (crumbs, core.disc(act, 48), esc(lab), totals_line(ts),
               ('<p class="sec-intro">%s</p>' % esc(intro)) if intro else ''))


def band(label, segs, scope_id):
    """Segmented filter as links: without JS they jump to the group; section.js turns them into filters.
    segs: [(key, text, count|None, href|None (None = disabled), icon_name|None)]."""
    out = []
    for i, (key, text, cnt, href, ic) in enumerate(segs):
        inner = '%s<span>%s</span>%s' % (icon(ic, 20) if ic else '', esc(text),
                                         ('<span class="sec-seg-n">%s</span>' % cnt) if cnt else '')
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

def featured(t, here, full_row=''):
    """Datum featured anatomy: label → chips → H2 row (Download GPX bottom-aligned) → place line → strip → map | photo + write-up.

    With no chart under the map, the write-up moves under the map on desktop and a second photo fills the right column
    (ClimbingIndex artboard), so neither column ends in a large blank."""
    act = t['activity']
    href = link(here, t['url'])
    gpx = link(here, t['url'] + t['slug'] + '.gpx')
    meta = core.render_meta(t)
    date = core.trip_date(t)
    place = core.place_line(t)
    # phones: chips-only chip row, the date moves to the start of the place line (GUIDE round 3)
    chips = '%s%s<span class="t-mono-s sec-feat-date">%s</span>' % (core.chip(t, variant='title'), core.trip_tags(t), date)
    place_html = ('<p class="t-mono-s sec-feat-place"><span class="sec-feat-pdate">%s%s</span>%s</p>'
                  % (date, ' · ' if place else '', place))
    map_ = core.map_block(t, here, [('map-col', 'col'), ('map-phone', 'phone')], t['url'] + 'map/', 'fm',
                          cls='map--nowide sec-feat-mapv')
    ch = meta.get('charts', {})
    chart = ''
    if act == 'hike' and 'profile-col' in ch:
        chart += profile_block(t, here, [('profile-col', 'col'), ('profile-phone', 'phone')], 'fp', cls='chart--nowide')
    if 'speed-col' in ch:
        chart += speed_block(t, here)
    text_left = not chart and bool(t['photos'])
    photos = t['photos'][:2 if text_left else 1]
    pics = ''.join(core.photo(t, p, here, sizes='(min-width: 1200px) 506px, (min-width: 760px) 50vw, 100vw', cls='sec-feat-photo')
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
            '<div class="sec-feat-grid%s"><div class="sec-feat-map">%s%s%s</div>'
            '<div class="sec-feat-side">%s%s</div></div>%s</section>'
            % (esc(t.get('subtype') or ''), chips, href, core.title_html(t['title']), place_html,
               gpx, icon('download', 18), strip(feat_cells(t)), stats_note(t), grid_cls,
               map_, map_caption(t), chart, ('<div class="sec-feat-pics">%s</div>' % pics) if pics else '', txt, full_row))


def vx_line(ch, variants):
    """VERTICAL ×N differs per chart width; show the one that matches the visible variant."""
    out = []
    for name, size in variants:
        if name in ch and ch[name].get('vx'):
            out.append('<span class="sec-vx sec-vx--%s">VERTICAL ×%.1f</span>' % (size, ch[name]['vx']))
    return ''.join(out)


def profile_block(t, here, variants, ns, cls=''):
    ch = core.render_meta(t).get('charts', {})
    first = next((ch[nm] for nm, _ in variants if nm in ch), None)
    if not first:
        return ''
    st = t['stats']
    hi = st.get('high_m') if st.get('high_m') is not None else first.get('gps_max_ft', 0) / FT
    lo = st.get('low_m') if st.get('low_m') is not None else first.get('min_ft', 0) / FT
    meta_line = 'GPS MAX %s · MIN %s · %s' % (U(n(hi * FT) + ' FT', n(hi) + ' M'), U(n(lo * FT) + ' FT', n(lo) + ' M'),
                                             vx_line(ch, variants))
    wrap_cls = 'sec-prof sec-prof--%s' % variants[0][1]
    return ('<div class="%s"><div class="sec-chart-h"><h3 class="t-label" id="%s-h">Elevation</h3><p class="t-mono-s">%s</p></div>'
            '<div role="group" aria-labelledby="%s-h">%s</div></div>'
            % (wrap_cls, ns, meta_line, ns, core.chart_block(t, here, variants, ns, cls=cls)))


def speed_block(t, here):
    return ('<div class="sec-prof sec-prof--col"><div class="sec-chart-h"><h3 class="t-label" id="fs-h">Speed</h3>'
            '<p class="t-mono-s">MPH, 3-MIN MEDIAN · FLAT WATER, NO ELEVATION PROFILE</p>%s</div>'
            '<div role="group" aria-labelledby="fs-h">%s</div></div>'
            % (core.key_row(['speed'], 'keyrow--inline'),
               core.chart_block(t, here, [('speed-col', 'col'), ('speed-phone', 'phone')], 'fs', cls='chart--nowide')))


def pick_featured(ts):
    singles = [t for t in ts if t['kind'] == 'trip']
    return next((t for t in singles if t['featured']), singles[0] if singles else None)


_ROW_STATS = re.compile(r'<dl class="trow-stats">.*?</dl>', re.S)
_ROW_MOVING = re.compile(r'(<dt class="t-label">Moving</dt><dd class="t-data-m">)([^<]+)(</dd>)')


def day_ruler(t):
    """Multi-day rows: one bar per day, widths proportional to that day's distance, labelled D1…DN (SkiIndex artboard)."""
    if t['kind'] != 'multi-day' or len(t['days']) < 2:
        return ''
    ds = [d['stats'].get('distance_km') or 0 for d in t['days']]
    if not sum(ds):
        return ''
    return ('<div class="sec-dr" aria-hidden="true">%s</div>'
            % ''.join('<span style="flex-grow:%.2f">D%s</span>' % (v, esc(d['label'])) for v, d in zip(ds, t['days'])))


def row(t, here, tagged=False):
    """core.trip_row adjusted to the GUIDE list-row rules (see core_requests): route shape in the Mono-S meta line,
    status-only tags (MULTI-DAY · N DAYS, SERIES, PLANNED), DIST · GAIN · GPS MAX · MOVING on every row, day ruler on multi-day."""
    r = core.trip_row(t, here)
    shape = t.get('route_shape') if t['kind'] in ('trip', 'multi-day') else None
    if shape:
        word = core.SHAPE.get(shape, shape)
        if core.tag(word) in r:
            r = r.replace(core.tag(word), '', 1)
            r = r.replace('</p><h3 class="t-h3 trow-t">', ' · %s</p><h3 class="t-h3 trow-t">' % esc(word.upper()), 1)
    if t['kind'] == 'planned':  # the PLANNED tag already says it
        r = r.replace('<p class="t-mono-s trow-meta">PLANNED · ', '<p class="t-mono-s trow-meta">', 1)
    if t['kind'] == 'multi-day':
        k = len(t['days'])
        r = r.replace(core.tag('%d days' % k), core.tag('Multi-day · %d days' % k), 1)
    stats = _ROW_MOVING.sub(r'\1\2<span class="unit sec-hm"> h:mm</span>\3', core.stats_cells(t, ('dist', 'gain', 'high', 'time')))
    r = _ROW_STATS.sub(lambda m: '<dl class="trow-stats">%s</dl>%s' % (stats, day_ruler(t)), r, count=1)
    if tagged:  # Other: each row carries its sub-type so the filter band can show / hide it
        r = r.replace('<li class="trow"', '<li class="trow" data-f="%s"' % esc(t.get('subtype') or ''), 1)
    return r


def more_list(title, rows_ts, here, id_='more', meta=None, extra='', tagged=False):
    if not rows_ts:
        return ''
    meta = meta if meta is not None else plural(len(rows_ts), 'REPORT')
    return ('<section class="sec-more wrap" aria-labelledby="%s-h">%s<ol class="tlist sec-tlist">%s</ol>%s</section>'
            % (id_, core.section_head(title, meta, id_=id_ + '-h'), ''.join(row(t, here, tagged) for t in rows_ts), extra))


# ---------------------------------------------------------------- hiking series card

def series_card(t, here):
    href = link(here, t['url'])
    days = t['days']
    written = [d for d in days if d['body_md']]
    mi, km = core.dist_vals(t['stats'].get('distance_km'))
    cells = [('Recorded days', n(len(days)), '')]
    if mi:
        cells.append(('Distance recorded', U(mi, km, 'mi', 'km'), ''))
    if written:
        cells.append(('Write-ups', '%s%s' % (n(len(written)), unit('days')), ''))
    stats = ''.join('<div class="sc"><dt class="t-label">%s</dt><dd class="t-data-m">%s</dd></div>' % (a, b) for a, b, _ in cells)
    sample = ''
    if written:
        d = written[0]
        lab = 'DAY %s' % esc(d['label']) + ((' · ' + esc(d['title']).upper()) if d.get('title') else '')
        sample = ('<div class="sec-ser-day"><p class="t-label">%s</p><p class="t-excerpt sec-ser-ex">%s</p></div>'
                  % (lab, esc(markdown.plain(d['body_md'], 200))))
    return ('<section class="sec-ser wrap" aria-labelledby="ser-title"><div class="sec-ser-card">'
            '<a class="sec-ser-tile" href="%s" tabindex="-1" aria-hidden="true">%s</a>'
            '<div class="sec-ser-b"><div class="chips">%s<span class="t-mono-s">%s</span></div>'
            '<h2 class="t-h2 sec-ser-t" id="ser-title"><a href="%s">%s</a></h2>'
            '<p class="t-mono-s sec-ser-place">%s</p><dl class="sec-ser-stats">%s</dl>%s'
            '<div class="sec-ser-a">%s</div></div></div></section>'
            % (href, core.tile(t, here, 'ser-' + t['slug']), core.tag('Series'), core.trip_date(t), href, esc(t['title']),
               core.place_line(t), stats, sample, arrow_link(href, 'Read the series', 'btn btn--ink')))


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
    regions = []
    for t in ts:  # newest first -> region of the latest trip first
        if t.get('region') and t['region'] not in regions:
            regions.append(t['region'])
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
                    '<span>%s</span><span class="sec-tab-n">%d</span></button>'
                    % (s, s, 'true' if sel else 'false', '0' if sel else '-1', esc(r), cnt))
        mb = core.map_block(None, here, [('ski-%s-desktop' % s, 'desktop'), ('ski-%s-phone' % s, 'phone')],
                            'assets/maps/', 'rm-' + s, site_maps=True, eager=sel)
        mb = dedupe_roads(mb, 'rm-' + s)
        panels.append('<div class="sec-rp" role="tabpanel" id="rp-%s" aria-labelledby="rt-%s"%s>'
                      '<p class="t-label sec-rp-l">%s</p>%s</div>' % (s, s, '' if sel else ' hidden', esc(r), mb))
    cap = ('<p class="sec-pcap"><span class="sec-pcap-h">Hover a report to highlight its track · </span>North up · '
           'Terrain: AWS Terrain Tiles · Map data © OpenStreetMap contributors · Not for navigation</p>')
    return ('<aside class="sec-panel" aria-labelledby="panel-h"><div class="sec-panel-in">'
            '<h2 class="sec-panel-h" id="panel-h">Ski map by region</h2>'
            '<div class="sec-tabs" role="tablist" aria-label="Region">%s</div>'
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
    return ('<div class="sec-split wrap" id="reports"><div class="sec-list" data-map-target="ski-map">%s</div>%s</div>'
            '<div class="wrap sec-avy-w">%s</div>' % (''.join(groups), ski_panel(ts, here), avy)), seasons


NOSCRIPT = ('<noscript><style>.sec-rp[hidden]{display:block!important}.sec-rp+.sec-rp{margin-top:24px}'
            '.sec-rp-l{display:block!important}.sec-tabs,.sec-pcap-h{display:none!important}'
            '.sec-panel-in{position:static!important}</style></noscript>')


# ---------------------------------------------------------------- other: empty states

def empty_states(subs):
    if not subs:
        return ''
    cards = ''.join('<li class="sec-empty"><span class="sec-empty-i">%s</span><div class="sec-empty-b"><h3 class="t-h4">%s</h3>'
                    '<p class="t-label sec-empty-l">First reports coming</p><p class="sec-empty-p">%s</p></div></li>'
                    % (icon(core.SUB_ICON[s], 32), esc(core.SUB_WORD[s]), esc(EMPTY_LINE[s])) for s in subs)
    return ('<section class="sec-empties wrap" aria-labelledby="empty-h" data-f="">%s<ul class="sec-empty-g">%s</ul></section>'
            % (core.section_head('No reports yet', plural(len(subs), 'SUB-TYPE'), id_='empty-h'), cards))


# ---------------------------------------------------------------- pages

def description(act, ts):
    lab = core.ACT[act][0]
    regions = []
    for t in ts:
        if t.get('region') and t['region'] not in regions:
            regions.append(t['region'])
    where = (' (%s)' % ', '.join(regions)) if regions else ''
    if len(ts) == 1:
        return '1 %s trip report%s with the full GPS track, a map and stats.' % (lab, where)
    return '%d %s trip reports%s, each with the full GPS track, a map and stats.' % (len(ts), lab, where)


def og_image(ts):
    for t in ts:
        if t['photos']:
            return t['url'] + t['photos'][0]['file']
    return None


def page(act, site):
    here = core.section_url(act)
    ts = reports_of(site, act)
    body = []
    extra_head = ''
    intro = OTHER_LINE if act == 'other' else ''
    body.append(header(act, here, ts, intro))
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
        if act == 'other':
            counts = {s: len([t for t in ts if t.get('subtype') == s]) for s in content.OTHER_SUBTYPES}
            segs = [('all', 'All', None, '#reports', 'OTH')]
            for s in content.OTHER_SUBTYPES:
                segs.append((s, core.SUB_WORD[s], counts[s] or None, ('#featured' if counts[s] else None), core.SUB_ICON[s]))
            body.append(band('Filter by type', segs, 'reports'))
        body.append('<div id="reports" class="sec-reports%s">' % (' sec-reports--band' if act == 'other' else ''))
        series = [t for t in ts if t['kind'] == 'series']
        if act == 'hike' and series:
            body.append(series_card(series[0], here))
        feat = pick_featured(ts)
        if feat:
            full = ''
            if act == 'mtb':
                full = profile_block(feat, here, [('profile-wide', 'wide'), ('profile-col', 'col'), ('profile-phone', 'phone')], 'fw')
                full = ('<div class="sec-feat-full">%s</div>' % full) if full else ''
            body.append(featured(feat, here, full_row=full))
        rest = [t for t in ts if t is not feat and not (act == 'hike' and t['kind'] == 'series')]
        body.append(more_list(MORE[act], rest, here, tagged=(act == 'other')))
        if act == 'hike' and site['planned']:
            planned = [t for t in site['planned'] if t['activity'] == act]
            body.append(more_list('Planned', planned, here, id_='planned', meta=plural(len(planned), 'PLANNED ROUTE')))
        if act == 'other':
            body.append(empty_states([s for s in content.OTHER_SUBTYPES if not counts[s]]))
        body.append('</div>')
    title = core.ACT[act][0]
    return core.Page(here, core.document(here, title, ''.join(body), description(act, ts), active=act,
                                         image=og_image(([feat] if feat else []) + ts), extra_head=extra_head,
                                         body_cls='p-section p-section--%s' % act), title)


def build(site):
    return [page(act, site) for act in ('ski', 'climb', 'hike', 'mtb', 'other')]
