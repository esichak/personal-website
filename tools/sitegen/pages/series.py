"""Series (kind: series) — /trips/<slug>/: one long log of recorded days (e.g. Pacific Crest Trail 2024).

Layout: title block + data strip, an intro row (tall overview map beside a short factual intro and a month index),
then the day log grouped by month under a sticky month nav. Every recorded day is an <article id="day-<label>">;
days with a write-up carry Eric's words verbatim and their photos. assets/js/pages/series.js adds the scrollspy
and the "Show days with write-ups only" filter (no JS: every day shows).
"""
import os
import re

import icons
import markdown

from sitegen import core
from sitegen.core import esc, U, U_sub, n, link, icon, FT
from sitegen.pages import report

DL_ICON = '<svg class="ic" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><use href="#ser-i-dl"/></svg>'
DL_SPRITE = ('<svg class="ser-sprite" width="0" height="0" aria-hidden="true" focusable="false"><symbol id="ser-i-dl" viewBox="0 0 24 24">%s'
             '</symbol></svg>' % icons.icon_inner('download'))
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']


# ---------------------------------------------------------------- small helpers

def day_anchor(d):
    return 'day-' + str(d['label']).replace('.', '-')


def day_title(d):
    return d['title'] or 'Day %s' % d['label']


_PT = re.compile(r'([ML])\s*(-?\d+(?:\.\d+)?)[\s,]+(-?\d+(?:\.\d+)?)')
_D = re.compile(r' d="([^"]+)"')


def _n10(v):
    a = abs(v)
    s = str(a // 10) if a % 10 == 0 else '%d.%d' % (a // 10, a % 10)
    return ('-' if v < 0 else '') + (s[1:] if s.startswith('0.') else s)


def compact_path(d):
    """'M50.3 42.9L49.8 42.5…' (absolute, 1 dp) -> 'M50.3 42.9l-.5-.4…' (relative, same points, about half the bytes)."""
    pts = _PT.findall(d)
    if not pts or pts[0][0] != 'M' or any(c != 'L' for c, _, _ in pts[1:]) or len(pts) != d.count('M') + d.count('L'):
        return d
    xy = [(int(round(float(x) * 10)), int(round(float(y) * 10))) for _, x, y in pts]
    out, last = 'M%s %s' % (_n10(xy[0][0]), _n10(xy[0][1])), ''
    if len(xy) > 1:
        out += 'l'
        last = ''
        for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
            for v in (x1 - x0, y1 - y0):
                tok = _n10(v)
                if last and not tok.startswith('-') and not (tok.startswith('.') and '.' in last):
                    out += ' '
                out += tok
                last = tok
    return out


def slim_svg(svg, path_cls):
    """Day glyph / sparkline fragment without the repeated inline styles (series.css styles them) and with compact path data."""
    svg = svg.replace(' style="display: block; flex-shrink: 0"', '', 1)
    def path(m):
        tag = re.sub(r' (?:class|style)="[^"]*"', '', m.group(0))
        return tag.replace('<path', '<path class="%s"' % path_cls, 1)
    svg = re.sub(r'<path\b[^>]*>', path, svg)
    return _D.sub(lambda m: ' d="%s"' % compact_path(m.group(1)), svg)


def written(d):
    return bool(d['body_md'])


def km_of(d):
    return d['stats'].get('distance_km') or 0.0


def group_months(t):
    """[(key, label, short, [days])] in file order; days without a date fall into one 'Undated' group."""
    out = []
    for d in t['days']:
        dt = d['date']
        key = dt.strftime('%Y-%m') if dt else 'undated'
        if not out or out[-1][0] != key:
            name = MONTHS[dt.month - 1] if dt else 'Undated'
            out.append((key, name, dt.year if dt else None, []))
        out[-1][3].append(d)
    return out


def month_id(key):
    return 'month-' + key


def label_range(days):
    a, b = days[0]['label'], days[-1]['label']
    return a if a == b else '%s–%s' % (a, b)


def dist_u(km, caps=False):
    mi, k = core.dist_vals(km)
    if mi is None:
        return ''
    return U(mi + ' MI', k + ' KM') if caps else U(mi, k, ' mi', ' km')


# ---------------------------------------------------------------- title + strip

def strip(t):
    days = t['days']
    st = t['stats']
    cells = []
    mi, km = core.dist_vals(st.get('distance_km'))
    if mi:
        cells.append(('Distance recorded', U(mi, km, '<span class="unit">mi</span>', '<span class="unit">km</span>'), U_sub(mi, km, 'mi', 'km')))
    if st.get('gain_m') is not None:
        g = st['gain_m']
        cells.append(('Gain', U(n(g * FT), n(g), '<span class="unit">ft</span>', '<span class="unit">m</span>'), U_sub(n(g * FT), n(g), 'ft', 'm')))
    longest = max(days, key=km_of)
    sub = ''
    if km_of(longest):
        lmi, lkm = core.dist_vals(longest['stats']['distance_km'])
        sub = 'LONGEST %s' % U(lmi + ' MI', lkm + ' KM')
    cells.append(('Days recorded', n(len(days)), sub))
    wu = sum(1 for d in days if written(d))
    photos = sum(len(d['photos']) for d in days)
    cells.append(('Write-ups', '%s<span class="unit">day%s</span>' % (n(wu), '' if wu == 1 else 's'),
                  ('%s PHOTO%s' % (n(photos), '' if photos == 1 else 'S')) if photos else ''))
    out = ''.join('<div class="strip-c"><dt class="t-label">%s</dt><dd class="t-data-xl strip-v">%s</dd>%s</div>'
                  % (lab, val, ('<dd class="t-mono-s strip-s">%s</dd>' % sub) if sub else '') for lab, val, sub in cells)
    note = ('<p class="strip-note">Stats from the Garmin recordings via Strava. Distance and gain are the sums of all %s recordings, '
            'short town days included.</p>' % n(len(days)))
    return ('<section class="wrap rep-strip" id="stats" aria-label="Stats"><dl class="strip" style="--cells:%d" aria-label="Series stats">%s</dl>%s</section>'
            % (len(cells), out, note))


# ---------------------------------------------------------------- intro row: map + overview + month index

def map_caption(t):
    """Same two-line caption as the report and multi-day maps (track line · North up / terrain + OSM line)."""
    rng = core.frange(t['date'], t['end_date'])
    lines = [['Tracks: Garmin, ' + rng, 'full tracks, not trimmed', 'North up'],
             ['Terrain: AWS Terrain Tiles', 'Map data © OpenStreetMap contributors', 'Not for navigation']]
    return '<p class="mapcap-t ser-mapcap">%s</p>' % ''.join(
        '<span>%s</span>' % ' · '.join('<span class="ser-nw">%s</span>' % esc(seg) for seg in line) for line in lines)


def lede(t):
    """The series write-up when index.md has one; otherwise a short factual note on how the log is organised."""
    if t['body_md']:
        return '<div class="prose t-body ser-lede-prose">%s</div>' % markdown.to_html(t['body_md'])
    days = t['days']
    n_wu = sum(1 for d in days if written(d))
    rest = len(days) - n_wu
    pics = sum(1 for d in days if d['photos'] and not written(d))
    bits = ['One entry per recorded day, grouped by month.']
    if n_wu and rest:
        bits.append('The %s days with a write-up carry the notes from that day and any photos; the other %s show the track%s.'
                    % (n(n_wu), n(rest), (', %s of them with photos' % n(pics)) if pics else ' only'))
    elif n_wu:
        bits.append('Every day has a write-up.')
    bits.append('Every track is the full recording, not trimmed, with its own GPX download.')
    return '<p class="ser-lede">%s</p>' % ' '.join(bits)


def ruler(days, width_pct):
    cells = ''.join('<i class="%s" style="flex-grow:%.1f"></i>' % ('w' if written(d) else 't', max(km_of(d), 1.5)) for d in days)
    return '<span class="ser-rl" style="width:%.1f%%" aria-hidden="true">%s</span>' % (width_pct, cells)


def month_index(months):
    top = max(sum(km_of(d) for d in m[3]) for m in months) or 1
    rows = []
    for key, name, year, days in months:
        km = sum(km_of(d) for d in days)
        wu = sum(1 for d in days if written(d))
        meta = 'DAY%s %s' % ('' if len(days) == 1 else 'S', esc(label_range(days)))
        meta += ' · %s WRITE-UP%s' % (n(wu), '' if wu == 1 else 'S') if wu else ' · TRACK ONLY'
        rows.append('<li><a class="ser-mi-a" href="#%s"><span class="ser-mi-h"><span class="ser-mi-m">%s</span>'
                    '<span class="t-mono-s ser-mi-s">%s</span></span><span class="ser-mi-v">%s</span>%s</a></li>'
                    % (month_id(key), esc(name), meta, dist_u(km), ruler(days, max(100.0 * km / top, 8))))
    key_ = ('<ul class="keyrow ser-key" aria-label="Key to the month bars">'
            '<li><svg width="16" height="10" viewBox="0 0 16 10" aria-hidden="true"><rect x="0" y="1" width="16" height="8" style="fill:var(--ink-2)"/></svg>Day with a write-up</li>'
            '<li><svg width="16" height="10" viewBox="0 0 16 10" aria-hidden="true"><rect x="0" y="1" width="16" height="8" style="fill:var(--ser-track)"/></svg>Track only</li>'
            '<li class="ser-key-n">Bar length = distance</li></ul>')
    return ('<h3 class="t-label ser-bym" id="bym-h">By month</h3><ol class="ser-mi" aria-labelledby="bym-h">%s</ol>%s'
            % (''.join(rows), key_))


def intro(t, here, months):
    mp = core.map_block(t, here, [('overview-tall', 'desktop'), ('overview-phone', 'phone')], t['url'] + 'map/', 'ov',
                        cls='ser-map')
    return ('<section class="ser-intro wrap" id="map" aria-labelledby="ov-h">'
            '<div class="ser-intro-map">%s%s</div>'
            '<div class="ser-intro-t"><div class="shead"><h2 class="shead-t" id="ov-h">Overview</h2></div>%s%s</div></section>'
            % (mp, map_caption(t), lede(t), month_index(months)))


# ---------------------------------------------------------------- day log

def thumbs(t, d, here):
    if not d['photos']:
        return ''
    base = link(here, t['url'])
    out = []
    total = len(d['photos'])
    for i, p in enumerate(d['photos']):
        src = base + (p['sm'] or p['file'])
        wh = (' width="%d" height="%d"' % (p['w'], p['h'])) if p.get('w') and p.get('h') else ''
        alt = p.get('alt') or ''
        label = '' if alt else ' aria-label="Day %s, photo %d of %d (full size)"' % (esc(d['label']), i + 1, total)
        out.append('<li><a class="ser-ph" href="%s"%s><img src="%s"%s alt="%s" loading="lazy" decoding="async"></a></li>'
                   % (base + p['file'], label, src, wh, esc(alt)))
    return '<ul class="ser-phs" aria-label="Day %s photos">%s</ul>' % (esc(d['label']), ''.join(out))


def stats_dl(d):
    st = d['stats']
    cells = []
    mi, km = core.dist_vals(st.get('distance_km'))
    cells.append(('d', 'Distance', U(mi, km, ' mi', ' km') if mi else '—'))
    g = st.get('gain_m')
    cells.append(('g', 'Gain', U(n(g * FT), n(g), ' ft', ' m') if g is not None else '—'))
    cells.append(('m', 'Moving', ('%s<span class="unit"> moving</span>' % core.hm(st['moving_s'])) if st.get('moving_s') else '—'))
    return ('<dl class="ser-st">%s</dl>'
            % ''.join('<div class="ser-st-%s"><dt>%s</dt><dd>%s</dd></div>' % (k, lab, v) for k, lab, v in cells))


def day_article(t, d, here):
    aid = day_anchor(d)
    days_dir = os.path.join(t['rendered'], 'days')
    glyph = slim_svg(core.frag(os.path.join(days_dir, '%s-g64.svg.html' % d['id']), here), 'gl-trk')
    spark = slim_svg(core.frag(os.path.join(days_dir, '%s-spark.svg.html' % d['id']), here), 'ser-spl')
    date_s = core.fdate(d['date'], 'day') if d['date'] else ''
    gpx = ''
    if d['track']:
        gpx = ('<a class="ser-gpx" href="gpx/%s-day-%s.gpx" download aria-label="Download Day %s GPX">%s</a>'
               % (t['slug'], d['id'], esc(d['label']), DL_ICON))
    else:
        gpx = '<span class="ser-gpx" aria-hidden="true"></span>'
    body = ''
    if d['body_md']:
        body += '<div class="prose t-body ser-wu">%s</div>' % markdown.to_html(d['body_md'], heading_shift=4)
    body += thumbs(t, d, here)
    cls = 'ser-day' + (' has-wu' if written(d) else '') + (' has-body' if body else '') + ('' if d['title'] else ' no-title')
    labelled = ('%s-n %s-t' % (aid, aid)) if d['title'] else ('%s-n' % aid)
    return ('<article class="%s" id="%s" aria-labelledby="%s">'
            '<div class="ser-row"><div class="ser-g">%s</div>'
            '<p class="ser-n" id="%s-n"><span class="ser-dn"><span class="ser-dw">Day </span>%s</span>'
            '<span class="ser-dd">%s</span></p>'
            '<h4 class="ser-t" id="%s-t">%s</h4>%s<div class="ser-sp">%s</div>%s</div>%s</article>'
            % (cls, aid, labelled, glyph, aid, esc(d['label']), esc(date_s), aid, esc(day_title(d)), stats_dl(d), spark, gpx,
               ('<div class="ser-body">%s</div>' % body) if body else ''))


def cols_head():
    return ('<div class="ser-cols" aria-hidden="true"><span></span><span>Day</span><span>Date</span><span>Title</span>'
            '<span class="num">Dist %s</span><span class="num">Gain %s</span><span class="num">Moving</span>'
            '<span>Elevation</span><span class="num">GPX</span></div>'
            % (U('mi', 'km'), U('ft', 'm')))


def label_gaps(days):
    """{day id: (first, last)} for whole day numbers the log skips before that day (e.g. Day 125, Days 138–140)."""
    out, prev = {}, None
    for d in days:
        m = re.match(r'(\d+)', str(d['label']))
        if not m:
            continue
        cur = int(m.group(1))
        if prev is not None and cur > prev + 1:
            out[d['id']] = (prev + 1, cur - 1)
        prev = cur if prev is None else max(prev, cur)
    return out


def gap_row(a, b):
    rng = str(a) if a == b else '%d–%d' % (a, b)
    return '<p class="ser-gap">DAY%s %s · NO RECORDING</p>' % ('' if a == b else 'S', rng)


def month_section(t, here, key, name, year, days, gaps):
    mid = month_id(key)
    km = sum(km_of(d) for d in days)
    wu = sum(1 for d in days if written(d))
    meta = ['DAYS %s' % esc(label_range(days)), '%s WRITE-UP%s' % (n(wu), '' if wu == 1 else 'S') if wu else 'TRACK ONLY']
    if km:
        meta.append(dist_u(km, caps=True))
    title = '%s %s' % (name, year) if year else name
    rows = ''.join((gap_row(*gaps[d['id']]) if d['id'] in gaps else '') + day_article(t, d, here) for d in days)
    return ('<section class="ser-month%s" id="%s" aria-labelledby="%s-h"><div class="ser-mh"><h3 class="ser-mh-t" id="%s-h">%s</h3>'
            '<p class="t-mono-s ser-mh-m">%s</p></div>%s<div class="ser-days">%s</div></section>'
            % (' has-wu' if wu else '', mid, mid, mid, esc(title), ' · '.join(meta), cols_head(), rows))


def month_nav(months):
    items = []
    for key, name, year, days in months:
        short, rest = name[:3], name[3:]
        rng = label_range(days)
        items.append('<li><a href="#%s" data-wu="%d"><span class="ser-mn-m">%s<span class="ser-mn-x">%s</span></span>'
                     '<span class="ser-mn-s"><span class="ser-mn-x">Days </span>%s</span></a></li>'
                     % (month_id(key), sum(1 for d in days if written(d)), esc(short), esc(rest), esc(rng)))
    return '<nav class="ser-mnav" aria-label="Months"><ol style="--n:%d">%s</ol></nav>' % (len(months), ''.join(items))


def day_log(t, here, months):
    n_days = len(t['days'])
    n_wu = sum(1 for d in t['days'] if written(d))
    gaps = label_gaps(t['days'])
    toggle = ''
    if 0 < n_wu < n_days:
        toggle = ('<div class="ser-only" hidden><label class="ser-only-l"><input type="checkbox" id="ser-only" data-total="%d" data-wu="%d">'
                  '<span class="ser-only-long">Show days with write-ups only</span><span class="ser-only-short">Write-ups only</span>'
                  '</label></div>' % (n_days, n_wu))
    return ('<section class="ser-log wrap sec" id="days" aria-labelledby="days-h" style="--ser-act:%s">'
            '<div class="shead ser-log-h"><h2 class="shead-t" id="days-h">Day by day</h2>%s</div>'
            '<p class="sr" id="ser-live" aria-live="polite"></p>%s%s%s</section>'
            % (core.ACT[t['activity']][3], toggle, DL_SPRITE, month_nav(months),
               ''.join(month_section(t, here, *m, gaps=gaps) for m in months)))


# ---------------------------------------------------------------- page

def page(t, site):
    here = t['url']
    months = group_months(t)
    actions = '<a class="btn" href="#days">%sDay by day</a>' % icon('list', 18)
    body = [report.title_block(t, here, actions), strip(t), intro(t, here, months), day_log(t, here, months),
            report.pager(t, here, site)]
    n_wu = sum(1 for d in t['days'] if written(d))
    desc = '%s: %s recorded days, %s, with a GPX track for every day%s.' % (
        t['title'], n(len(t['days'])), core.frange(t['date'], t['end_date']),
        (' and %s written up' % n(n_wu)) if n_wu else '')
    first_photo = next((d['photos'][0] for d in t['days'] if d['photos']), None)
    img = (t['url'] + first_photo['file']) if first_photo else ((t['url'] + t['photos'][0]['file']) if t['photos'] else None)
    return core.Page(here, core.document(here, t['title'], ''.join(body), desc, active=t['activity'], image=img,
                                         body_cls='p-series'), t['title'])


def build(site):
    return [page(t, site) for t in site['trips'] if t['kind'] == 'series' and t['days']]
