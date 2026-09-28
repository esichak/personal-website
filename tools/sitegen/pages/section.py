"""Section index pages — /ski/, /climbing/, /hiking/, /mountain-biking/, /other/ (one module, five pages).

Anatomy: breadcrumb, H1 with the activity disc, Mono-S totals line, optional filter band (Ski: seasons, Other: sub-types),
then either the Ski list + sticky region map panel, or a Featured block followed by "More <x>".
Hiking adds the series section (after Featured) and a Planned block; Mountain Biking adds a full-width elevation profile;
Other adds one line under the filter band naming the sub-types without reports.
"""
import json
import os
import re

import content
import markdown

from sitegen import core
from sitegen.core import esc, U, n, link, icon, FT, SEP

MORE = {'climb': 'More climbs', 'hike': 'More hikes', 'mtb': 'More rides', 'other': 'More reports', 'ski': 'More ski tours'}
OTHER_LINE = "Paddleboarding, rafting, kayaking, mountaineering, and anything that isn't a ski, climb, hike or ride."
AVY = [('Eastern Sierra Avalanche Center', 'https://www.esavalanche.org/'),
       ('Sierra Avalanche Center', 'https://www.sierraavalanchecenter.org/')]
FULL_TRACK = 'full track, not trimmed'
ATTRIB = 'Terrain: AWS Terrain Tiles · Map data © OpenStreetMap contributors · Not for navigation'


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


def totals_line(ts):
    """'10 REPORTS · 264 MI · 101,066 FT GAIN' — every figure computed from the content, units switchable."""
    bits = [core.nb(plural(len(ts), 'REPORT'))]
    km = sum(t['stats'].get('distance_km') or 0 for t in ts)
    gain = sum(t['stats'].get('gain_m') or 0 for t in ts)
    if km:
        mi, k = core.dist_vals(km)
        bits.append(U(core.nb(mi + ' MI'), core.nb(k + ' KM')))
    if gain >= 30:
        bits.append(U(core.nb(n(gain * FT) + ' FT GAIN'), core.nb(n(gain) + ' M GAIN')))
    return SEP.join(bits)


def count_html(k, cls):
    """Visible '5'; assistive tech hears ', 5 reports' after the segment / tab name."""
    return ('<span class="%s"><span class="sr">, </span>%d<span class="sr"> %s</span></span>'
            % (cls, k, 'report' if k == 1 else 'reports'))


def map_caption(t, extra=''):
    first = []
    if t['date']:
        first.append('Track: Garmin, %s' % core.fdate(t['date'], 'short'))
    first.append(FULL_TRACK)
    first.append('North up')
    return ('<div class="mapcap sec-mapcap"><p class="mapcap-t"><span>%s</span><span>%s</span></p>%s</div>'
            % (' · '.join(first), ATTRIB, extra))


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
                  % (date, SEP if place else '', place))
    map_ = core.map_block(t, here, [('map-col', 'col'), ('map-phone', 'phone')], t['url'] + 'map/', 'fm',
                          cls='map--nowide sec-feat-mapv')
    ch = meta.get('charts', {})
    chart = ''
    if act == 'hike' and 'profile-col' in ch:
        chart += profile_block(t, here, [('profile-col', 'col'), ('profile-phone', 'phone')], 'fp', cls='chart--nowide')
    if 'speed-col' in ch:
        chart += speed_block(t, here)
    text_left = not chart and bool(t['photos'])
    if full_row and 'profile-phone' in ch:
        # phones: the full-width profile row is hidden, and this one sits right under the map caption instead
        chart += '<div class="sec-feat-pph">%s</div>' % profile_block(t, here, [('profile-phone', 'phone')], 'fpp')
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
               gpx, icon('download', 18), core.strip(core.strip_cells(t)), core.stats_note(t), grid_cls,
               map_, map_caption(t), chart, ('<div class="sec-feat-pics">%s</div>' % pics) if pics else '', txt, full_row))


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
    vx = core.vx_line(ch, variants, nowide=('chart--nowide' in cls) or None)
    if vx:
        bits.append(vx.replace('VERTICAL ×', 'VERTICAL\u00a0×'))
    return ('<div class="sec-prof"><div class="sec-chart-h"><h3 class="t-label" id="%s-h">Elevation</h3><p class="t-mono-s">%s</p></div>'
            '<div role="group" aria-labelledby="%s-h">%s</div></div>'
            % (ns, SEP.join(bits), ns, core.chart_block(t, here, variants, ns, cls=cls)))


def speed_block(t, here):
    return ('<div class="sec-prof"><div class="sec-chart-h"><h3 class="t-label" id="fs-h">Speed</h3>'
            '<p class="t-mono-s">%s</p>%s</div>'
            '<div role="group" aria-labelledby="fs-h">%s</div></div>'
            % (core.speed_meta(t), core.key_row(['speed'], 'keyrow--inline'),
               core.chart_block(t, here, [('speed-col', 'col'), ('speed-phone', 'phone')], 'fs', cls='chart--nowide')))


def pick_featured(ts):
    singles = [t for t in ts if t['kind'] == 'trip']
    return next((t for t in singles if t['featured']), singles[0] if singles else None)


def row(t, here, tagged=False):
    """The shared list row; on Other each row carries its sub-type so the filter band can show / hide it."""
    return core.trip_row(t, here, filter_key=(t.get('subtype') or '') if tagged else None)


def more_list(title, rows_ts, here, id_='more', meta=None, extra='', tagged=False):
    if not rows_ts:
        return ''
    meta = meta if meta is not None else plural(len(rows_ts), 'REPORT')
    return ('<section class="sec-more wrap" aria-labelledby="%s-h">%s<ol class="tlist sec-tlist">%s</ol>%s</section>'
            % (id_, core.section_head(title, meta, id_=id_ + '-h'), ''.join(row(t, here, tagged) for t in rows_ts), extra))


# ---------------------------------------------------------------- hiking: series section (HikingIndex artboard)

def series_block(t, here):
    """Open section after Featured: head (title link · date range), overview map (4 of 12 columns) | tag, place line,
    the series page's stats, first photo of the first three days with photos, first written day, actions."""
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
    pics = ''.join(core.photo(t, p, here, sizes='(min-width: 1200px) 224px, 30vw', caption=False, cls='sec-ser-ph')
                   for p in firsts)
    sample = ''
    if written:
        d = written[0]
        lab = 'Day %s' % esc(str(d['label'])) + ((' · ' + esc(d['title'])) if d.get('title') else '')
        sample = ('<div class="sec-ser-day"><p class="t-label">%s</p><p class="t-excerpt sec-ser-ex">%s</p></div>'
                  % (lab, esc(markdown.plain(d['body_md'], 200))))
    mp = core.map_block(t, here, [('overview-tall', 'desktop')], t['url'] + 'map/', 'ser', cls='sec-ser-map')
    place = core.place_line(t)
    return ('<section class="sec-ser wrap" aria-labelledby="ser-title">%s'
            '<div class="sec-ser-g">'
            '<div class="sec-ser-mapc">%s<p class="t-small sec-ser-cap"><span>North up · Terrain: AWS Terrain Tiles</span> '
            '<span>Map data ©\u00a0OpenStreetMap contributors · Not\u00a0for\u00a0navigation</span></p></div>'
            '<div class="sec-ser-b">'
            '<div class="chips">%s</div>%s<dl class="sec-ser-stats">%s</dl>'
            '%s%s'
            '<div class="sec-ser-a">%s<a class="btn" href="%s#days">%sDay by day</a></div>'
            '</div></div></section>'
            % (core.section_head('<a href="%s">%s</a>' % (href, esc(t['title'])), core.trip_date(t), id_='ser-title'),
               mp, core.tag('Series'), ('<p class="t-mono-s sec-ser-place">%s</p>' % place) if place else '', stats,
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
                    '<span>%s</span>%s</button>'
                    % (s, s, 'true' if sel else 'false', '0' if sel else '-1', esc(r), count_html(cnt, 'sec-tab-n')))
        mb = core.map_block(None, here, [('ski-%s-desktop' % s, 'desktop'), ('ski-%s-phone' % s, 'phone')],
                            'assets/maps/', 'rm-' + s, site_maps=True, eager=sel)
        mb = dedupe_roads(mb, 'rm-' + s)
        panels.append('<div class="sec-rp" role="tabpanel" id="rp-%s" aria-labelledby="rt-%s"%s>'
                      '<p class="t-label sec-rp-l">%s</p>%s</div>' % (s, s, '' if sel else ' hidden', esc(r), mb))
    cap = ('<p class="sec-pcap"><span class="sec-pcap-h">Hover a report to highlight its track · </span>North up · %s</p>' % ATTRIB)
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
    regions = []
    for t in ts:
        if t.get('region') and t['region'] not in regions:
            regions.append(t['region'])
    where = (' (%s)' % ', '.join(regions)) if regions else ''
    word = act_words(act, ts)
    if len(ts) == 1:
        return '1 %s trip report%s, with the full GPX track and map.' % (word, where)
    return '%d %s trip reports%s, each with the full GPX track and map.' % (len(ts), word, where)


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
            body.append(none_line([s for s in content.OTHER_SUBTYPES if not counts[s]]))
        body.append('<div id="reports" class="sec-reports%s">' % (' sec-reports--band' if act == 'other' else ''))
        feat = pick_featured(ts)
        if feat:
            full = ''
            if act == 'mtb':
                full = profile_block(feat, here, [('profile-wide', 'wide'), ('profile-col', 'col')], 'fw')
                full = ('<div class="sec-feat-full">%s</div>' % full) if full else ''
            body.append(featured(feat, here, full_row=full))
        series = [t for t in ts if t['kind'] == 'series' and t['days']]
        if act == 'hike' and series:
            body.append(series_block(series[0], here))
        rest = [t for t in ts if t is not feat and not (act == 'hike' and t['kind'] == 'series')]
        body.append(more_list(MORE[act], rest, here, tagged=(act == 'other')))
        if act == 'hike' and site['planned']:
            planned = [t for t in site['planned'] if t['activity'] == act]
            body.append(more_list('Planned', planned, here, id_='planned', meta=plural(len(planned), 'PLANNED ROUTE')))
        body.append('</div>')
    title = '%s trip reports' % core.ACT[act][0]
    return core.Page(here, core.document(here, title, ''.join(body), description(act, ts), active=act,
                                         image=og_image(([feat] if feat else []) + ts), extra_head=extra_head,
                                         body_cls='p-section p-section--%s' % act), title)


def build(site):
    return [page(act, site) for act in ('ski', 'climb', 'hike', 'mtb', 'other')]
