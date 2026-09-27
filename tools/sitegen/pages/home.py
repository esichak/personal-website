"""Home page — / (index.html). Mirrors the Main artboard (desktop) and Phone-Home-A/B (phone).

Sections: hero · featured report · latest reports (report table) · by activity · where I've been (region maps).
Every count and stat is computed from the content; nothing here is written about Eric beyond the site lead.
"""
import json
import os

from sitegen import core
from sitegen.core import esc, U, U_sub, n, link, icon, FT

HERE = ''
LABEL = 'Trip reports · GPX'
# Headline + lead from the approved Main artboard (one line per span; the spans stack on wider screens).
HEADLINE = ('Trip reports from', 'the Sierra, the Alps', 'and beyond.')
LEAD = 'Backcountry ski, climbing, hiking, mountain biking and other trips, each with a GPX map.'
ATTRIB = 'Terrain: AWS Terrain Tiles · Map data © OpenStreetMap contributors · Not for navigation'
HOME_REGIONS = ('Lake Tahoe', 'Eastern Sierra')
LATEST_N = 10


# ---------------------------------------------------------------- small helpers

def plural(k, word, many=None):
    return '%d %s' % (k, word if k == 1 else (many or word + 'S'))


def is_report(t):
    """A 'report' in counts: published and not a series (series are counted separately, as on the canvas)."""
    return t['kind'] not in ('planned', 'series')


def short_date(t):
    """'MAR 28, 2026' / 'MAR 10–15, 2024' — the compact caps date used in tiles and the table's DATE column."""
    if t['kind'] == 'planned':
        return 'PLANNED'
    if t['days'] and t.get('end_date') and t['end_date'] != t['date']:
        return core.frange(t['date'], t['end_date'], caps=True)
    return core.fdate(t['date'], 'short').upper()


def meta_line(bits):
    """Mono-S 'A · B · C' that only breaks after a separator (each item wraps inside itself only if it alone is too wide)."""
    return '&nbsp;· '.join('<span class="hom-nw">%s</span>' % b for b in bits if b)


def slug(s):
    return core.content.slugify(s)


def site_meta():
    p = os.path.join(core.ROOT, 'rendered', 'site', 'meta.json')
    return json.load(open(p)) if os.path.exists(p) else {'maps': {}}


# ---------------------------------------------------------------- hero

def hero():
    h1 = ' '.join('<span class="hom-l">%s</span>' % esc(x) for x in HEADLINE)
    return ('<div class="hom-hero">'
            '<p class="t-label hom-kicker">%s</p>'
            '<h1 class="t-d2 hom-h1">%s</h1>'
            '<div class="hom-hero-b"><p class="hom-lead">%s</p>'
            '<div class="hom-cta">'
            '<a class="btn btn--ink" href="#latest-h">Latest reports<span class="hom-down">%s</span></a>'
            '<a class="btn" href="%s">%sOpen the map</a></div></div></div>'
            % (esc(LABEL), h1, esc(LEAD), icon('arrow-right', 18), link(HERE, 'map/'), icon('map', 18)))


# ---------------------------------------------------------------- featured

def map_variants(t):
    if t['kind'] == 'series':
        return [('overview-tall', 'col'), ('overview-phone', 'phone')], ' hom-fmap--tall'
    if t['kind'] == 'multi-day':
        return [('overview-col', 'col'), ('overview-phone', 'phone')], ''
    return [('map-col', 'col'), ('map-phone', 'phone')], ''


def mini_strip(t):
    """Four-cell strip (distance · gain · GPS max · moving) at Data-M size, the other unit on the sub-line."""
    st = t['stats']
    cells = []
    mi, km = core.dist_vals(st.get('distance_km'))
    if mi:
        cells.append(('Distance', U(mi, km, '<span class="unit">mi</span>', '<span class="unit">km</span>'), U_sub(mi, km, 'mi', 'km')))
    if st.get('gain_m') is not None:
        g = st['gain_m']
        cells.append(('Gain', U(n(g * FT), n(g), '<span class="unit">ft</span>', '<span class="unit">m</span>'), U_sub(n(g * FT), n(g), 'ft', 'm')))
    if st.get('high_m') is not None:
        h = st['high_m']
        cells.append(('GPS max', U(n(h * FT), n(h), '<span class="unit">ft</span>', '<span class="unit">m</span>'), U_sub(n(h * FT), n(h), 'ft', 'm')))
    if st.get('moving_s'):
        if t['days']:
            sub = plural(len(t['days']), 'DAY')
        else:
            sub = ('START ' + core.ftime(t['start_time'])) if t.get('start_time') else ''
        cells.append(('Moving', '%s<span class="unit">h:mm</span>' % core.hm(st['moving_s']), sub))
    if not cells:
        return ''
    out = ''.join('<div class="strip-c"><dt class="t-label">%s</dt><dd class="t-data-m strip-v">%s</dd>%s</div>'
                  % (lab, val, ('<dd class="t-mono-s strip-s">%s</dd>' % sub) if sub else '') for lab, val, sub in cells)
    return '<dl class="strip hom-strip" style="--cells:%d" aria-label="Trip stats">%s</dl>' % (len(cells), out)


def map_caption(t):
    if t['days']:
        first = 'Tracks: Garmin, %s · full tracks, not trimmed · North up' % core.frange(t['date'], t['end_date'])
    else:
        first = 'Track: Garmin, %s · full track, not trimmed · North up' % core.fdate(t['date'], 'short')
    return '<p class="t-small hom-fcap"><span>%s</span> <span>%s</span></p>' % (esc(first), esc(ATTRIB))


def first_photo(t):
    if t['photos']:
        return t['photos'][0]
    for d in t['days']:
        if d['photos']:
            return d['photos'][0]
    return None


def featured(site):
    pool = site['published']
    t = next((x for x in pool if x['featured']), None) or (pool[0] if pool else None)
    if not t:
        return '', None
    href = link(HERE, t['url'])
    variants, tall = map_variants(t)
    # lazy on every variant: the hidden one is then never fetched (an eager col PNG would cost phones ~290 KB), and the
    # visible one still loads at once because it is in the first viewport
    mp = core.map_block(t, HERE, variants, t['url'] + 'map/', 'fm', cls='map--nowide')
    fmap = ('<div class="hom-fmap%s"><a class="hom-maplink" href="%s" tabindex="-1" aria-hidden="true">%s'
            '<span class="hom-ftag">FEATURED</span></a></div>%s' % (tall, href, mp, map_caption(t)))
    p = first_photo(t)
    photo = ''
    if p:
        photo = core.photo(t, p, HERE, sizes='(min-width: 1200px) 506px, (min-width: 1000px) 40vw, 100vw', cls='hom-fphoto', caption=False)
    act = t['activity']
    chips = ('<div class="chips hom-chips">%s%s<span class="t-mono-s hom-cdate">%s</span></div>'
             % (core.chip(t, href=link(HERE, core.section_url(act))), core.trip_tags(t), core.trip_date(t)))
    # phone (Phone-Home-A): the date leaves the chip row and joins distance + gain on one Mono-S line under the title
    pmeta = meta_line([core.trip_date(t)] + [x for x in core.plain_stats(t).split(' · ') if x])
    place = meta_line(core.place_line(t).split(' · ')) if core.place_line(t) else ''
    ex = core.excerpt(t, 230)
    det = ('<div class="hom-det">%s'
           '<h2 class="t-h3 hom-ft" id="feat-t"><a href="%s">%s</a></h2>%s%s%s%s'
           '<a class="alink hom-read" href="%s">Read report%s</a></div>'
           % (chips, href, core.title_html(t['title']),
              ('<p class="t-mono-s hom-pmeta">%s</p>' % pmeta) if pmeta else '',
              ('<p class="t-mono-s hom-place">%s</p>' % place) if place else '',
              mini_strip(t),
              ('<p class="t-excerpt hom-ex">%s</p>' % esc(ex)) if ex else '',
              href, icon('arrow-right', 16)))
    cls = 'hom-feat' + ('' if photo else ' hom-feat--nophoto')
    return ('<article class="%s" aria-labelledby="feat-l feat-t"><p class="sr" id="feat-l">Featured report</p>%s%s%s</article>'
            % (cls, fmap, det, photo)), t


# ---------------------------------------------------------------- latest reports (report table)

def table_row(t):
    """core.table_row with the compact caps date (the 128px DATE column fits 'MAR 28, 2026', not the weekday form)."""
    row = core.table_row(t, HERE)
    long_ = '<span role="cell" class="t-mono-s">%s</span>' % core.trip_date(t)
    row = row.replace(long_, '<span role="cell" class="t-mono-s">%s</span>' % short_date(t), 1)
    if not t['stats'].get('distance_km'):
        row = row.replace('class="rtab-r"', 'class="rtab-r hom-nodist"', 1)
    return row


def latest(site):
    reports = [t for t in site['published'] if is_report(t)]
    rows = site['published'][:LATEST_N]
    if not rows:
        return ''
    total = len(reports)
    return ('<section class="wrap sec hom-latest" aria-labelledby="latest-h">%s'
            '<div class="rtab hom-rtab" role="table" aria-labelledby="latest-h">%s%s</div>'
            '<a class="btn hom-all" href="%s">All %d reports%s</a></section>'
            % (core.section_head('Latest reports', 'SHOWING THE %d NEWEST' % len(rows), id_='latest-h'),
               core.table_head(), ''.join(table_row(t) for t in rows),
               link(HERE, 'map/#all-reports'), total, icon('arrow-right', 18)))


# ---------------------------------------------------------------- by activity

def activity_tile(site, act, label):
    pub = [t for t in site['published'] if t['activity'] == act]
    reps = [t for t in pub if is_report(t)]
    series = [t for t in pub if t['kind'] == 'series']
    multi = [t for t in reps if t['kind'] == 'multi-day']
    planned = [t for t in site['planned'] if t['activity'] == act]
    sub = []
    if multi:
        sub.append(plural(len(multi), 'MULTI-DAY', 'MULTI-DAY'))
    if series:
        sub.append(plural(len(series), 'SERIES', 'SERIES'))
    if planned:
        sub.append(plural(len(planned), 'PLANNED ROUTE'))
    if reps:
        count = ('<div class="hom-tile-c"><span class="hom-tile-num">%d</span><span class="hom-tile-u">%s</span></div>'
                 % (len(reps), 'Report' if len(reps) == 1 else 'Reports'))
    else:
        count = '<div class="hom-tile-c hom-tile-c--none">First reports coming</div>'
    last = pub[0] if pub else None
    if last:
        latest_ = ('<div class="hom-tile-latest"><span class="t-label">Latest</span><span class="hom-tile-t">%s</span>'
                   '<span class="t-mono-s">%s</span></div>' % (core.title_html(last['title']), short_date(last)))
    else:
        latest_ = '<div class="hom-tile-latest hom-tile-latest--none"><span class="t-label">Latest</span><span class="hom-tile-t">No reports yet</span></div>'
    subtypes = ''
    if act == 'other':
        words = [core.SUB_WORD[s] for s in core.content.OTHER_SUBTYPES]
        subtypes = ('<span class="hom-tile-sub">%s</span>'
                    % '<br>'.join(' · '.join(words[i:i + 2]) for i in range(0, len(words), 2)))
    return ('<li><a class="hom-tile" href="%s">'
            '<div class="hom-tile-top">%s%s</div>'
            '<div class="hom-tile-name"><h3 class="hom-tile-n">%s</h3>%s</div>'
            '%s'
            '<div class="hom-tile-count">%s<span class="t-mono-s hom-tile-s">%s</span></div>%s</a></li>'
            % (link(HERE, core.section_url(act)), core.disc(act, 32), icon('arrow-right', 20, 'hom-arr'),
               esc(label), subtypes, latest_, count, meta_line(sub), icon('chevron-right', 20, 'hom-chev')))


def by_activity(site):
    tiles = ''.join(activity_tile(site, act, lab) for act, lab in core.NAV)
    return ('<section class="wrap sec hom-acts" aria-labelledby="act-h">%s<ul class="hom-tiles">%s</ul></section>'
            % (core.section_head('By activity', plural(len(core.NAV), 'ACTIVITY', 'ACTIVITIES'), id_='act-h'), tiles))


# ---------------------------------------------------------------- where I've been

def region_counts(site, slugs):
    by = site['by_slug']
    ts = [by[s] for s in slugs if s in by]
    reps = sum(1 for t in ts if is_report(t))
    planned = sum(1 for t in ts if t['kind'] == 'planned')
    bits = [plural(reps, 'REPORT')] if reps else []
    if planned:
        bits.append(plural(planned, 'PLANNED ROUTE'))
    return bits


def where(site):
    meta = site_meta()['maps']
    blocks = []
    for region in HOME_REGIONS:
        rs = slug(region)
        dk, ph = 'region-%s-desktop' % rs, 'region-%s-phone' % rs
        if dk not in meta and ph not in meta:
            continue
        slugs = (meta.get(dk) or meta.get(ph)).get('trips', [])
        bits = region_counts(site, slugs)
        line = meta_line(bits)
        aria = ('%s: %s. Open the map' % (region, ', '.join(bits).lower())) if bits else '%s: open the map' % region
        mp = core.map_block(None, HERE, [(dk, 'desktop'), (ph, 'phone')], 'assets/maps/', 'rg-' + rs, site_maps=True, attrib=False)
        blocks.append('<div class="hom-reg"><div class="hom-reg-h"><h3 class="hom-reg-n">%s</h3>'
                      '<span class="t-mono-s hom-reg-c">%s</span>'
                      '<a class="hom-reg-a" href="%s" aria-label="%s">Open the map%s</a></div>%s</div>'
                      % (esc(region), line, link(HERE, 'map/#region-' + rs), esc(aria), icon('arrow-right', 16), mp))
    if not blocks:
        return ''
    # regions not drawn here (by number of reports), then series, as one "Also" line
    others = {}
    for t in site['published']:
        r = t.get('region')
        if is_report(t) and r and r not in HOME_REGIONS:
            others[r] = others.get(r, 0) + 1
    item = '<li><a href="%s"><span class="hom-also-w">%s</span><span class="hom-also-c">%s</span></a></li>'
    also = [item % (link(HERE, 'map/#region-' + slug(r)), esc(r), k) for r, k in sorted(others.items(), key=lambda kv: (-kv[1], kv[0]))]
    also += [item % (link(HERE, t['url']), esc(t['title']), 'SERIES') for t in site['published'] if t['kind'] == 'series']
    also_html = ('<div class="hom-also"><span class="t-mono-s" id="also-l">ALSO</span><ul aria-labelledby="also-l">%s</ul></div>'
                 % ''.join(also)) if also else ''
    reports = [t for t in site['published'] if is_report(t)]
    series = [t for t in site['published'] if t['kind'] == 'series']
    head_meta = plural(len(reports), 'REPORT') + ((' · ' + plural(len(series), 'SERIES', 'SERIES')) if series else '')
    return ('<section class="wrap sec hom-where" aria-labelledby="where-h">%s<div class="hom-regions">%s</div>'
            '<p class="t-small hom-attr">North up · %s</p>%s</section>'
            % (core.section_head("Where I’ve been", head_meta, id_='where-h'), ''.join(blocks), esc(ATTRIB), also_html))


# ---------------------------------------------------------------- page

def page(site):
    feat, ft = featured(site)
    body = ['<section class="wrap hom-top" aria-label="Introduction">%s%s</section>' % (hero(), feat),
            latest(site), by_activity(site), where(site)]
    img = None
    if ft:
        p = first_photo(ft)
        if p:
            img = ft['url'] + p['file']
    return core.Page(HERE, core.document(HERE, core.SITE_NAME, ''.join(body), LEAD, active=None, image=img, body_cls='p-home'),
                     core.SITE_NAME)


def build(site):
    return [page(site)]
