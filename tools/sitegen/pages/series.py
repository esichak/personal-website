"""Series (kind: series) — /trips/<slug>/: one long log of recorded days (e.g. Pacific Crest Trail 2024).

Layout: title block + data strip, an intro row (tall overview map beside a short factual intro and a month index),
then the day log grouped by month under a sticky month nav. Every recorded day is an <article id="day-<label>">;
days with a write-up carry Eric's words verbatim and their photos. assets/js/pages/series.js adds the scrollspy
and the "Show days with write-ups only" filter (no JS: every day shows).
"""
import os
import re

import content
import icons
import markdown

from sitegen import core
from sitegen.core import esc, U, U_sub, n, link, icon, FT
from sitegen.pages import archive, report

DL_ICON = '<svg class="ic" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><use href="#ser-i-dl"/></svg>'
DL_SPRITE = ('<svg class="ser-sprite" width="0" height="0" aria-hidden="true" focusable="false"><symbol id="ser-i-dl" viewBox="0 0 24 24">%s'
             '</symbol></svg>' % icons.icon_inner('download'))
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']


# ---------------------------------------------------------------- small helpers

def day_anchor(d):
    """'day-31', 'day-5-2': the day's id on the journal page and the fragment every link to it uses (content.day_anchor,
    which also makes load_trip refuse two days with one anchor)."""
    return content.day_anchor(d['label'])


def day_title(d):
    """The h4 of a day row. A day without a Strava title keeps its heading (screen readers hear "Day 42, track only") but
    the visible cell states what the day holds, in the month index's words, instead of repeating the DAY column."""
    if d['title']:
        return esc(d['title']).replace('/', '/<wbr>')
    k = len(d['photos'])
    pics = ('%s PHOTO%s' % (n(k), '' if k == 1 else 'S')) if k else ''
    if written(d):
        state = 'WRITE-UP' + (core.SEP + pics if pics else '')
    else:
        state = pics or ('TRACK ONLY' if d['track'] else '')
    return ('<span class="sr">Day %s%s</span>%s' % (esc(d['label']), ', ' if state else '',
            ('<span class="t-mono-s ser-t-none">%s</span>' % state) if state else ''))


def gpx_name(t, d):
    """Saved file name of a day's GPX, from Eric's day label ('Day 41' -> <slug>-day-41.gpx, 'Day 5.2' -> <slug>-day-5-2.gpx),
    so the download matches the row it came from (the file on the site is still named by the day file, see build.py)."""
    return '%s-day-%s.gpx' % (t['slug'], day_anchor(d)[4:])


_PT = re.compile(r'([ML])\s*(-?\d+(?:\.\d+)?)[\s,]+(-?\d+(?:\.\d+)?)')
_D = re.compile(r' d="([^"]+)"')


def _n10(v):
    a = abs(v)
    s = str(a // 10) if a % 10 == 0 else '%d.%d' % (a // 10, a % 10)
    return ('-' if v < 0 else '') + (s[1:] if s.startswith('0.') else s)


def compact_path(d):
    """'M50.3 42.9L49.8 42.5…' (absolute, 1 dp) -> 'M50.3 42.9l-.5-.4…' (relative, same points, about half the bytes).
    Anything but a plain absolute M/L polyline (e.g. a fragment render.py already wrote in relative form) passes unchanged."""
    if re.search(r'[^ML0-9.,\s-]', d):
        return d
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


def so_far(t):
    """{day id: km}: the distance recorded from the first day file through each one, in file order (features-07). A gap in
    the day numbers adds nothing: only day files are summed, so the last day's figure is the strip's total."""
    out, km = {}, 0.0
    for d in t['days']:
        km += km_of(d)
        out[d['id']] = km
    return out


def far_item(km):
    """'2,654 MI SO FAR': one meta_items() item for the month heads and the By-month rows, '' before any distance."""
    mi, k = core.dist_vals(km)
    return U(core.nb(mi + ' MI SO FAR'), core.nb(k + ' KM SO FAR')) if mi else ''


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
    return U(core.nb(mi + ' MI'), core.nb(k + ' KM')) if caps else U(mi, k, ' mi', ' km')


def days_item(days):
    """'DAYS 1–9' / 'DAY 125': one meta_items() item (month index rows and month heads)."""
    return core.nb('DAY%s %s' % ('' if len(days) == 1 else 'S', esc(label_range(days))))


def wu_item(wu):
    return core.nb(('%s WRITE-UP%s' % (n(wu), '' if wu == 1 else 'S')) if wu else 'TRACK ONLY')


# ---------------------------------------------------------------- title + strip

def strip(t):
    days = t['days']
    st = t['stats']
    cells = []
    mi, km = core.dist_vals(st.get('distance_km'))
    if mi:
        cells.append(('Distance recorded', U(mi, km, 'mi', 'km'), U_sub(mi, km, 'mi', 'km')))
    if st.get('gain_m') is not None:
        g = st['gain_m']
        cells.append(('Gain', U(n(g * FT), n(g), 'ft', 'm'), U_sub(n(g * FT), n(g), 'ft', 'm')))
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
    note = ('<p class="strip-note">%s Distance and gain are the sums of all %s recordings, '
            'short town days included.%s</p>' % (core.via('Stats from the GPS recordings', t), n(len(days)),
                                                 (' ' + core.MOVING_NOTE[False]) if t['stats'].get('moving_s') else ''))
    # core.strip: the shared Datum strip (Label / Data-XL value with core.dx punctuation / Mono-S sub-line)
    return '<section class="wrap rep-strip" id="stats" aria-label="Stats">%s%s</section>' % (core.strip(cells, label='Series stats'), note)


# ---------------------------------------------------------------- intro row: map + overview + month index

def map_caption(t):
    """The shared map caption (core.map_caption), as on the report and multi-day maps: the track line, then the credit
    (two lines from 1200, one flowing paragraph below; phones drop the credit, which the in-map tag and footer carry)."""
    when = core.recorded(t['date'], t['end_date'])   # 'on <date>' for a journal of one day
    return core.map_caption(([when] if when else []) + ['full tracks, not trimmed', 'North up'])


def lede(t):
    """The series write-up when index.md has one; otherwise a factual introduction from the fields and the day files only:
    what the journal is (title, recorded days, dates, place) and how the log is organised. No day's prose, no adjectives."""
    if t['body_md']:
        return '<div class="prose t-body ser-lede-prose">%s</div>' % markdown.to_html(t['body_md'])
    days = t['days']
    n_wu = sum(1 for d in days if written(d))
    rest = len(days) - n_wu
    pics = sum(1 for d in days if d['photos'] and not written(d))
    # a journal whose day files carry no dates says nothing about when, rather than leaving a hole in the sentence
    facts = ', '.join(x for x in ('%s: %s recorded day%s' % (esc(t['title']), n(len(days)), '' if len(days) == 1 else 's'),
                                  core.frange(t['date'], t['end_date']), esc(t['place']) if t.get('place') else '') if x) + '.'
    bits = [facts, 'One entry per recorded day, grouped by month.']
    if n_wu and rest:
        # the same sentence in the singular when one day is written, or one is not
        first = ('The %s days with a write-up carry the notes from that day and any photos' % n(n_wu)) if n_wu > 1 \
            else 'The one day with a write-up carries its notes and any photos'
        if rest > 1:
            second = 'the other %s show the track%s' % (n(rest), (', %s of them with photos' % n(pics)) if pics else ' only')
        else:
            second = 'the other day shows the track%s' % (' and its photos' if pics else ' only')
        bits.append('%s; %s.' % (first, second))
    elif n_wu:
        bits.append('Every day has a write-up.')
    bits.append('Every track is the full recording, not trimmed, with its own GPX download.')
    return '<p class="ser-lede">%s</p>' % ' '.join(bits)


def ruler(days, width_pct):
    cells = ''.join('<i class="%s" style="flex-grow:%.1f"></i>' % ('w' if written(d) else 't', max(km_of(d), 1.5)) for d in days)
    return '<span class="ser-rl" style="width:%.1f%%" aria-hidden="true">%s</span>' % (width_pct, cells)


MAP_ID = 'ser-map'


def month_key(key):
    """Track key of a month on the overview maps (render.py tags each day track with its month: data-key="m-2024-06")."""
    return 'm-' + key if key != 'undated' else ''


def overview_svg(t, name):
    p = core.rendered(t, name + '.svg.html')
    return core._read(p) if os.path.exists(p) else ''


_KEY = re.compile(r'\bdata-key="(m-[^"]+)"')


def map_month_keys(t):
    """Month keys the overview renders actually carry (so a month row only links to tracks that exist on the map)."""
    return set(k for nm in ('overview-tall', 'overview-phone') for k in _KEY.findall(overview_svg(t, nm)))


def month_index(months, keyed=frozenset(), far=None):
    """Month rows. A row whose month the map carries gets data-key: hovering or focusing it highlights that month's tracks on
    the overview map (base.js, via data-map-target on the list). far: so_far(t), for the distance recorded through each
    month's last day (benchmark-10)."""
    far = far or {}
    top = max(sum(km_of(d) for d in m[3]) for m in months) or 1
    rows = []
    for key, name, year, days in months:
        km = sum(km_of(d) for d in days)
        wu = sum(1 for d in days if written(d))
        meta = core.meta_items([days_item(days), wu_item(wu), far_item(far.get(days[-1]['id']))])
        mk = month_key(key)
        rows.append('<li%s><a class="ser-mi-a" href="#%s"><span class="ser-mi-h"><span class="ser-mi-m">%s</span>'
                    '<span class="t-mono-s ser-mi-s">%s</span></span><span class="ser-mi-v">%s</span>%s</a></li>'
                    % ((' data-key="%s"' % mk) if mk in keyed else '', month_id(key), esc(name), meta, dist_u(km),
                       ruler(days, max(100.0 * km / top, 8))))
    key_ = ('<ul class="keyrow ser-key" aria-label="Key to the month bars">'
            '<li><svg width="16" height="10" viewBox="0 0 16 10" aria-hidden="true"><rect x="0" y="1" width="16" height="8" style="fill:var(--ink)"/></svg>Day with a write-up</li>'
            '<li><svg width="16" height="10" viewBox="0 0 16 10" aria-hidden="true"><rect x="0" y="1" width="16" height="8" style="fill:var(--ser-track)"/></svg>Track only</li>'
            '<li class="ser-key-n">Bar length = distance</li></ul>')
    target = (' data-map-target="%s"' % MAP_ID) if keyed else ''
    return ('<h3 class="t-label ser-bym" id="bym-h">By month</h3><ol class="ser-mi"%s aria-labelledby="bym-h">%s</ol>%s'
            % (target, ''.join(rows), key_))


_START = re.compile(r'<circle[^>]*r="[57]"[^>]*fill: #16171A; stroke: #FFFFFF')
_END = re.compile(r'<rect[^>]*width="1[04]"[^>]*fill: #16171A; stroke: #FFFFFF')


def map_keys(t, name):
    """Key items for the start / end markers an overview render actually draws (key rows decode only what is on the map)."""
    s = overview_svg(t, name)
    start, end = bool(_START.search(s)), bool(_END.search(s))
    return ['start_end'] if (start and end) else (['start'] if start else (['end'] if end else []))


# which overview render each band shows (series.css): the 560x860 render 1:1 in the 560 column >= 1200 and in the
# one-column 560-759 band (map up to 560 wide); the 390x600 render on phones and in the tablet 5fr/6fr column beside the
# overview text at 760-1199 (about 297x457 at 768: 0.76x at 760 up to 1.26x at 1199; the 560 render would be 0.53-0.88x)
# One query per <link>: Chrome's preload scanner fetches a link whose media is a comma list whether or not it matches.
OV_MEDIA = (('overview-tall', ('(min-width: 1200px)', '(min-width: 560px) and (max-width: 759.98px)')),
            ('overview-phone', ('(max-width: 559.98px)', '(min-width: 760px) and (max-width: 1199.98px)')))


def ov_preloads(t, here):
    """<link rel="preload"> for the overview render each band shows (OV_MEDIA), so every width, tablets included, fetches the
    hero hillshade (and base layer, when rendered) at once and never the render it hides."""
    maps = core.render_meta(t)['maps']
    base = link(here, t['url'] + 'map/')
    out = []
    for name, queries in OV_MEDIA:
        m = maps.get(name) or {}
        for media in queries:
            if m.get('png'):
                out.append('<link rel="preload" as="image" href="%s%s" media="%s" fetchpriority="high">' % (base, m['png'], media))
            if m.get('base'):
                out.append('<link rel="preload" as="image" type="image/svg+xml" href="%s%s" media="%s" fetchpriority="high">'
                           % (base, m['base'], media))
    return ''.join(out)


def region_parts(t, here):
    """Under the overview map: the region maps that draw the journal's days (gap4-04), one link per part of
    t['region_days'], 'Days 67–76 · Lake Tahoe map (Pacific Crest Trail)', landing on the part's row in that region's
    list (archive.journal_part_id): the region's page when it has one, else its panel on map/. A region without a map,
    or whose map names none of the site's trips until the next render (no panel on map/), has no list to land on and
    gets no item; '' when no part has one."""
    items = []
    maps = core.site_meta().get('maps', {})
    panels = core._PANELS[0]   # None until a site is registered with its meta: then a map is taken to have its panel
    for part in t.get('region_days') or []:
        days = part.get('days') or []
        region = part.get('region')
        if not days or not region:
            continue
        rs = content.slugify(region)
        on_map = ('region-%s-desktop' % rs) in maps and (panels is None or rs in panels)
        base = core.region_page_href(here, region) or (link(here, 'map/') if on_map else None)
        if not base:
            continue
        text = '%s %s · %s map (%s)' % ('Day' if len(days) == 1 else 'Days', label_range(days), region, part.get('title') or t['title'])
        items.append('<li><a class="alink" href="%s#%s">%s%s</a></li>'
                     % (base, archive.journal_part_id(rs, part), esc(text), icon('arrow-right', 16)))
    return ('<ul class="ser-parts" aria-label="The journal on the region maps">%s</ul>' % ''.join(items)) if items else ''


def intro(t, here, months):
    # map_block shows wide >= 1200 and col 560-1199; series.css swaps the 560x860 render back in for 560-759 (OV_MEDIA)
    fs = core.fullscreen_link(t, here)   # bare: the journal's overview draws no route path to start on
    mp = core.map_block(t, here, [('overview-tall', 'wide'), ('overview-phone', 'col'), ('overview-phone', 'phone')],
                        t['url'] + 'map/', 'ov', cls='ser-map', id_=MAP_ID, fullscreen_href=fs)
    tall, small = map_keys(t, 'overview-tall'), map_keys(t, 'overview-phone')
    if tall == small:
        keys = core.key_row(tall, 'ser-mkey') if tall else ''
    else:
        # one row per render, each shown with its render (series.css), since the swap is not at core's 560 line
        keys = ((core.key_row(tall, 'ser-mkey ser-mkey--tall') if tall else '')
                + (core.key_row(small, 'ser-mkey ser-mkey--390') if small else ''))
    return ('<section class="ser-intro wrap" id="map" aria-labelledby="ov-h">'
            '<div class="ser-intro-map">%s%s%s%s%s</div>'
            '<div class="ser-intro-t"><div class="shead"><h2 class="shead-t" id="ov-h">Overview</h2></div>%s%s</div></section>'
            % (mp, keys, core.map_full_link(fs) if core.render_meta(t)['maps'] else '', map_caption(t), region_parts(t, here), lede(t),
               month_index(months, map_month_keys(t), so_far(t))))


# ---------------------------------------------------------------- day log

def thumb_file(t, p):
    """'photos/d001-01.th.webp' (320 px on the short edge: 2x for the <= 160 px squares) when it exists beside the photo,
    else None."""
    base, ext = os.path.splitext(p['file'])
    th = base + '.th' + ext
    return th if os.path.exists(os.path.join(t['dir'], th)) else None


def thumbs(t, d, here):
    """A track-only day's photos: one even square contact sheet (series.css: 3-6 columns, about 92-145 px squares). Every
    screen gets the .th copy (320 px short edge, so 2x on Retina) and never the 800 px .sm file; each thumbnail links to
    the full photo. A written day shows its photos as photos instead (day_photos)."""
    if not d['photos']:
        return ''
    base = link(here, t['url'])
    out = []
    total = len(d['photos'])
    for i, p in enumerate(d['photos']):
        sm = p['sm'] or p['file']
        th = thumb_file(t, p)
        src = ' src="%s"' % (base + (th or sm))
        wh = (' width="%d" height="%d"' % (p['w'], p['h'])) if p.get('w') and p.get('h') else ''
        alt = p.get('alt') or ''
        label = '' if alt else ' aria-label="Day %s, photo %d of %d (full size)"' % (esc(d['label']), i + 1, total)
        out.append('<li><a class="ser-ph" href="%s"%s><img%s%s alt="%s" loading="lazy" decoding="async"></a></li>'
                   % (base + p['file'], label, src, wh, esc(alt)))
    return '<ul class="ser-phs" aria-label="Day %s photos">%s</ul>' % (esc(d['label']), ''.join(out))


# a written day's photos: justified rows in the write-up's 620 px measure (series.css caps .jrows and sets the clamp to
# 400 / 200 px with a 12 px gap; photo_rows declares the same numbers in each sizes attribute)
DAY_ROWS = dict(per_row=3, col=620, jmax=400, jmin=200, gap=12, narrow=True)


def day_photos(t, d, here):
    """A written day's photos as photos (report-18): core.photo_rows, as on a report, at the journal's measure. They take
    the .th or the .sm copy, never the full file (full=False: on a 2x screen a 620 px row would otherwise fetch the
    1600 px file); the viewer still opens the full file. A track-only day keeps the square sheet (thumbs)."""
    if not written(d):
        return thumbs(t, d, here)
    return core.photo_rows(t, here, d['photos'], ns='d' + d['id'], name='Day %s, photo' % d['label'], full=False, **DAY_ROWS)


def stats_dl(d, far=None):
    """Distance, Gain, Moving and, with far (the km recorded through this day), the running total: under its column
    head 'Recorded so far' from 1000 px, '254 MI SO FAR' in the phone line; never trail mileage."""
    st = d['stats']
    cells = []
    mi, km = core.dist_vals(st.get('distance_km'))
    cells.append(('d', 'Distance', U(mi, km, ' mi', ' km') if mi else '—'))
    g = st.get('gain_m')
    cells.append(('g', 'Gain', U(n(g * FT), n(g), ' ft', ' m') if g is not None else '—'))
    cells.append(('m', 'Moving', ('%s<span class="unit"> moving</span>' % core.hm(st['moving_s'])) if st.get('moving_s') else '—'))
    if far is not None:
        fmi, fkm = core.dist_vals(far)
        cells.append(('f', 'Recorded', (U(fmi, fkm, ' mi', ' km') + '<span class="unit"> so far</span>') if fmi else '—'))
    return ('<dl class="ser-st">%s</dl>'
            % ''.join('<div class="ser-st-%s"><dt>%s</dt><dd>%s</dd></div>' % (k, lab, v) for k, lab, v in cells))


def first_written(t):
    """The first day with a write-up, or None."""
    return next((d for d in t['days'] if written(d)), None)


def highlights(t, here):
    """The author's chosen entries (index.md journal_highlights, validated by content.py), in the listed order: Day N, the
    day's title, the date, and the opening of its write-up when it has one. A day without a title is named by its date,
    which is then not printed a second time; with neither it is 'Day N' alone. '' when none are listed."""
    hs = t.get('journal_highlights') or []
    if not hs:
        return ''
    items = []
    for d in hs:
        date_s = core.fdate(d['date'], 'day') if d['date'] else ''
        name = esc(d['title']) if d['title'] else esc(date_s)
        name = ('<span class="ser-high-t">%s</span>' % name) if name else ''
        date_p = ('<p class="t-mono-s">%s</p>' % esc(date_s.upper())) if date_s and d['title'] else ''
        ex = ('<p class="t-excerpt">%s</p>' % esc(markdown.plain(d['body_md'], 160))) if written(d) else ''
        items.append('<li><a class="ser-high-a" href="#%s"><span class="t-label">Day %s</span>%s</a>%s%s</li>'
                     % (day_anchor(d), esc(d['label']), name, date_p, ex))
    count = core.nb('%s ENTR%s' % (n(len(hs)), 'Y' if len(hs) == 1 else 'IES'))
    return ('<section class="ser-high wrap sec" id="highlights" aria-labelledby="high-h"><div class="shead"><h2 class="shead-t" id="high-h">Highlights</h2>'
            '<span class="shead-m t-mono-s">%s</span></div><ol class="ser-high-l">%s</ol></section>' % (count, ''.join(items)))


def written_nav(t, d, here):
    """Under a written entry: the nearest written entries before and after (track-only days are skipped), each named by its
    day, and a copy-link control for this entry's anchor. A div, not a nav: one landmark per entry would add dozens."""
    if not written(d):
        return ''
    ws = [x for x in t['days'] if written(x)]
    i = ws.index(d)
    # where the entry sits among the written ones (benchmark-10)
    parts = ['<span class="t-mono-s ser-wnav-c">%s</span>' % core.nb('WRITE-UP %s OF %s' % (n(i + 1), n(len(ws))))]
    if i > 0:
        prev = ws[i - 1]
        parts.append('<a class="alink ser-wnav-p" href="#%s">%sPrevious write-up: Day %s</a>' % (day_anchor(prev), icon('arrow-left', 16), esc(prev['label'])))
    if i + 1 < len(ws):
        nxt = ws[i + 1]
        parts.append('<a class="alink ser-wnav-n" href="#%s">Next write-up: Day %s%s</a>' % (day_anchor(nxt), esc(nxt['label']), icon('arrow-right', 16)))
    parts.append(core.copy_link(core.SITE_URL + t['url'] + '#' + day_anchor(d), 'Copy link to this entry', cls='alink',
                                of='Day %s' % d['label'], share='Share this entry'))
    return '<div class="ser-wnav">%s</div>' % ''.join(parts)


def day_article(t, d, here, far=None):
    aid = day_anchor(d)
    days_dir = os.path.join(t['rendered'], 'days')
    glyph = slim_svg(core.frag(os.path.join(days_dir, '%s-g64.svg.html' % d['id']), here), 'gl-trk')
    spark = slim_svg(core.frag(os.path.join(days_dir, '%s-spark.svg.html' % d['id']), here), 'ser-spl')
    date_s = core.fdate(d['date'], 'day') if d['date'] else ''
    gpx = ''
    if d['track']:
        gpx = ('<a class="ser-gpx" href="gpx/%s-day-%s.gpx" download="%s" aria-label="Download Day %s GPX">%s</a>'
               % (t['slug'], d['id'], gpx_name(t, d), esc(d['label']), DL_ICON))
    else:
        gpx = '<span class="ser-gpx" aria-hidden="true"></span>'
    body = ''
    if d['body_md']:
        body += '<div class="prose t-body ser-wu">%s</div>' % markdown.to_html(d['body_md'], heading_shift=4)
    body += day_photos(t, d, here)
    body += written_nav(t, d, here)
    cls = 'ser-day' + (' has-wu' if written(d) else '') + (' has-body' if body else '') + ('' if d['title'] else ' no-title')
    labelled = ('%s-n %s-t' % (aid, aid)) if d['title'] else ('%s-n' % aid)
    return ('<article class="%s" id="%s" aria-labelledby="%s">'
            '<div class="ser-row"><div class="ser-g">%s</div>'
            '<p class="ser-n" id="%s-n"><span class="ser-dn"><span class="ser-dw">Day </span>%s</span>'
            '<span class="ser-dd">%s</span></p>'
            '<h4 class="ser-t" id="%s-t">%s</h4>%s<div class="ser-sp">%s</div>%s</div>%s</article>'
            % (cls, aid, labelled, glyph, aid, esc(d['label']), esc(date_s), aid, day_title(d), stats_dl(d, far), spark, gpx,
               ('<div class="ser-body">%s</div>' % body) if body else ''))


def cols_head():
    return ('<div class="ser-cols" aria-hidden="true"><span></span><span>Day</span><span>Date</span><span>Title</span>'
            '<span class="num">Dist %s</span><span class="num">Gain %s</span><span class="num">Moving</span>'
            '<span class="num">Recorded so far</span><span>Elevation</span><span class="num">GPX</span></div>'
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
    return '<p class="ser-gap">%s</p>' % core.meta_items([core.nb('DAY%s %s' % ('' if a == b else 'S', rng)), core.nb('NO RECORDING')])


def month_section(t, here, key, name, year, days, gaps, far=None):
    mid = month_id(key)
    far = far or {}
    km = sum(km_of(d) for d in days)
    wu = sum(1 for d in days if written(d))
    meta = [days_item(days), wu_item(wu), dist_u(km, caps=True) if km else '', far_item(far.get(days[-1]['id']))]
    title = '%s %s' % (name, year) if year else name
    rows = ''.join((gap_row(*gaps[d['id']]) if d['id'] in gaps else '') + day_article(t, d, here, far.get(d['id'])) for d in days)
    return ('<section class="ser-month%s" id="%s" aria-labelledby="%s-h"><div class="ser-mh"><h3 class="ser-mh-t" id="%s-h">%s</h3>'
            '<p class="t-mono-s ser-mh-m">%s</p></div>%s<div class="ser-days">%s</div></section>'
            % (' has-wu' if wu else '', mid, mid, mid, esc(title), core.meta_items(meta), cols_head(), rows))


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
    far = so_far(t)
    toggle = ''
    if 0 < n_wu < n_days:
        # data-default="wu": series.js starts the filter on (written entries are the reader mode) unless the URL hash
        # targets a day or month the filter would hide. autocomplete="off": series.js sets the box (from the address and
        # the reader's stored choice); a browser that refills it on Back / Forward does so after the script, without a
        # change event, and the list would not follow the box
        toggle = ('<div class="ser-only" hidden><label class="ser-only-l"><input type="checkbox" id="ser-only" autocomplete="off" data-total="%d" data-wu="%d" data-default="wu">'
                  '<span class="ser-only-long">Show days with write-ups only</span><span class="ser-only-short">Write-ups only</span>'
                  '</label></div>' % (n_days, n_wu))
    return ('<section class="ser-log wrap sec" id="days" aria-labelledby="days-h" style="--ser-act:%s">'
            '<div class="shead ser-log-h"><h2 class="shead-t" id="days-h">Day by day</h2>%s</div>'
            '<p class="sr" id="ser-live" aria-live="polite"></p>%s%s%s</section>'
            % (core.ACT[t['activity']][3], toggle, DL_SPRITE, month_nav(months),
               ''.join(month_section(t, here, *m, gaps=gaps, far=far) for m in months)))


# ---------------------------------------------------------------- page

def page(t, site):
    here = t['url']
    months = group_months(t)
    fw = first_written(t)
    actions = ''
    if fw:
        # the page's one primary action, in ink as on every other page type (visual-20)
        actions += '<a class="btn btn--ink" href="#%s">%sRead the first written entry</a>' % (day_anchor(fw), icon('report', 18))
    # data-ser-all: series.js turns the write-ups filter off when this is followed, so every recording shows
    actions += '<a class="btn" href="#days" data-ser-all>%sBrowse all recordings</a>' % icon('list', 18)
    actions += core.copy_link(core.SITE_URL + here)
    # 'Continue reading: Day N · title' (features-08): series.js fills and shows it when this browser has opened an entry
    # before (localStorage); empty and hidden otherwise, so nothing shows without JavaScript or a stored entry
    actions += '<a class="alink ser-continue" href="#days" hidden></a>'
    body = [report.title_block(t, here, actions), report.tick_backlink(t, here, site)]
    cover = t.get('cover')
    lead = bool(cover) and report.lead_photo(t) is not None   # a portrait cover fronts the cards but does not lead the page
    if lead:
        body.append(report.hero(t, here))
    body += [strip(t), intro(t, here, months), highlights(t, here), day_log(t, here, months), report.published_line(t),
             report.pager(t, here, site)]
    n_wu = sum(1 for d in t['days'] if written(d))
    n_gpx = sum(1 for d in t['days'] if d['track'])
    # "for every day" only when every day has one; a journal with some says how many, one with none says nothing
    gpx = ('with a GPX track for every day' if n_gpx == len(t['days'])
           else ('with a GPX track for %s of them' % n(n_gpx)) if n_gpx else '')
    desc = '%s.' % ', '.join(x for x in (
        '%s: %s recorded day%s' % (t['title'], n(len(t['days'])), '' if len(t['days']) == 1 else 's'),
        core.frange(t['date'], t['end_date']),
        ' and '.join(y for y in (gpx, ('%s written up' % n(n_wu)) if n_wu else '') if y)) if x)
    img = core.share_photo(t)   # the cover: content.resolve_cover finds one whenever the journal or a day has a photo
    # the lead photo is the page's first image; without one the overview map's hillshade (and base layer) load at once at
    # every width, each band fetching the render it shows
    head = core.cover_preload(t, here, report.HERO_SIZES) if lead else ov_preloads(t, here)
    return core.Page(here, core.document(here, t['title'], ''.join(body), desc, active=t['activity'], image=img,
                                         body_cls='p-series', og_type='article', extra_head=head, report=t), t['title'])


def build(site):
    out = []
    for t in site['trips']:
        if t['kind'] == 'series' and t['days']:
            out += [page(t, site), fullscreen(t)]
    return out


def fullscreen(t):
    """trips/<slug>/map/: the 560×860 overview at 1.5× for phones (the phone map's full-screen button)."""
    keys = map_keys(t, core.fs_render(t))
    return report.fullscreen_page(t, [(core.fs_render(t), 'fs')], core.key_row(keys) if keys else '', 'map--fs map--fstall',
                                  map_caption(t))
