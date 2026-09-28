"""Home page — / (index.html). Mirrors the Main artboard (desktop) and Phone-Home-A/B (phone).

Sections: hero · featured report · latest reports (report table) · by activity · where I've been (region maps).
Every count and stat is computed from the content; nothing here is written about Eric beyond the site lead.
"""
import os
import re

from sitegen import core
from sitegen.core import esc, U, U_sub, n, link, icon, FT

HERE = ''
LABEL = 'Trip reports · GPX'
# Headline + lead from the approved Main artboard (one line per span; the spans stack on wider screens).
HEADLINE = ('Trip reports from', 'the Sierra, the Alps', 'and beyond.')
LEAD = core.TAGLINE  # the one site tagline (dek, meta description, RSS channel)
ATTRIB = 'Terrain: AWS Terrain Tiles · Map data © OpenStreetMap contributors · Not for navigation'
HOME_REGIONS = ('Lake Tahoe', 'Eastern Sierra')
LATEST_N = 10
TITLE = 'Eric Sichak · Trip reports: backcountry skiing, climbing, hiking and more'


# ---------------------------------------------------------------- small helpers

def plural(k, word, many=None):
    return '%d %s' % (k, word if k == 1 else (many or word + 'S'))


def is_report(t):
    """A 'report' in counts: anything published. A series counts as one report (the same count as every other page)."""
    return t['kind'] != 'planned'


def meta_line(bits):
    """Mono-S 'A · B · C' as the shared .ml line (core.meta_items): CSS draws the dots, so a wrapped line never ends with
    one and an item never splits (a place item may wrap at its comma)."""
    return core.meta_items(bits)


def slug(s):
    return core.content.slugify(s)


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
    """The shared map caption (core.map_caption), as on report and section maps."""
    if t['days']:
        first = ['Tracks: %s' % core.frange(t['date'], t['end_date']), 'full tracks, not trimmed', 'North up']
    else:
        first = ['Track: %s' % core.fdate(t['date'], 'short'), 'full track, not trimmed', 'North up']
    return '<div class="hom-fcap">%s</div>' % core.map_caption(first)


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
    # 'Featured' is an in-flow Label above the map, as on section pages (an overlay tag covered map labels); it also names
    # the article. The key decodes only what the map shows: the home map hides mile discs (CSS), hence miles=False.
    fmap = ('<div class="hom-fmap%s"><p class="t-label hom-fl" id="feat-l">Featured</p>'
            '<a class="hom-maplink" href="%s" tabindex="-1" aria-hidden="true">%s</a></div><div class="hom-fkey">%s%s</div>'
            % (tall, href, mp, core.feature_key(t, variants, miles=False), map_caption(t)))
    p = first_photo(t)
    photo = ''
    if p:
        photo = core.photo(t, p, HERE, sizes='(min-width: 1200px) 506px, (min-width: 1000px) 40vw, 100vw', cls='hom-fphoto', caption=False)
    act = t['activity']
    chips = ('<div class="chips hom-chips">%s%s<span class="t-mono-s hom-cdate">%s</span></div>'
             % (core.chip(t, href=link(HERE, core.section_url(act))), core.trip_tags(t), core.trip_date(t)))
    # phone (Phone-Home-A): the date leaves the chip row and joins distance + gain on one Mono-S line under the title
    pmeta = meta_line([core.trip_date(t)] + core.plain_stats(t, items=True))
    place = meta_line(core.place_line(t, items=True))
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
    return ('<article class="%s" aria-labelledby="feat-l feat-t">%s%s%s</article>'
            % (cls, fmap, det, photo)), t


# ---------------------------------------------------------------- latest reports (report table)

def table_row(t):
    """core.table_row (li > a, compact caps date; rows without a distance carry .rtab-nodist)."""
    return core.table_row(t, HERE)


def latest(site):
    reports = [t for t in site['published'] if is_report(t)]
    rows = site['published'][:LATEST_N]
    if not rows:
        return ''
    total = len(reports)
    return ('<section class="wrap sec hom-latest" aria-labelledby="latest-h">%s'
            '<div class="rtab rtab--compact hom-rtab">%s<ol class="rtab-rows" aria-labelledby="latest-h">%s</ol></div>'
            '<a class="btn hom-all" href="%s">All %d reports%s</a></section>'
            % (core.section_head('Latest reports', 'SHOWING THE %d NEWEST' % len(rows), id_='latest-h'),
               core.table_head(), ''.join(table_row(t) for t in rows),
               link(HERE, 'map/#all-reports'), total, icon('arrow-right', 18)))


# ---------------------------------------------------------------- by activity

def activity_tile(site, act, label):
    pub = [t for t in site['published'] if t['activity'] == act]
    reps = [t for t in pub if is_report(t)]
    planned = [t for t in site['planned'] if t['activity'] == act]
    # core.count_items after the report count: 'INCL. 2 MULTI-DAY, 1 SERIES', then '+ 1 PLANNED ROUTE' (never a report),
    # one per line
    sub = core.count_items(reps, planned)[1:]
    if reps:
        count = ('<div class="hom-tile-c"><span class="hom-tile-num">%d</span> <span class="hom-tile-u">%s</span></div>'
                 % (len(reps), 'Report' if len(reps) == 1 else 'Reports'))
    else:
        count = '<div class="hom-tile-c hom-tile-c--none">First reports coming</div>'
    last = pub[0] if pub else None
    if last:
        latest_ = ('<div class="hom-tile-latest"><span class="t-label">Latest</span><span class="hom-tile-t">%s</span>'
                   '<span class="t-mono-s">%s</span></div>' % (core.title_html(last['title']), core.trip_date(last, short=True)))
    else:
        latest_ = '<div class="hom-tile-latest hom-tile-latest--none"><span class="t-label">Latest</span><span class="hom-tile-t">No reports yet</span></div>'
    subtypes = ''
    if act == 'other':
        # only the sub-types that have reports (core.other_subtypes, as the menu's Other row), most reports first:
        # one .ml line, 'Paddleboarding · Rafting'
        words = [core.SUB_WORD.get(s, s) for s in core.other_subtypes(pub)]
        line = core.meta_items([core.nb(esc(w)) for w in words])
        subtypes = ('<span class="hom-tile-sub">%s</span>' % line) if line else ''
    # the link's name is the activity; the count block is its description (the Latest title stays out of both)
    return ('<li><a class="hom-tile" href="%s" aria-labelledby="act-%s-n" aria-describedby="act-%s-c">'
            '<div class="hom-tile-top">%s%s</div>'
            '<div class="hom-tile-name"><h3 class="hom-tile-n" id="act-%s-n">%s</h3>%s</div>'
            '%s'
            '<div class="hom-tile-count" id="act-%s-c">%s <span class="t-mono-s hom-tile-s">%s</span></div>%s</a></li>'
            % (link(HERE, core.section_url(act)), act, act, core.disc(act, 32), icon('arrow-right', 20, 'hom-arr'),
               act, esc(label), subtypes, latest_, act, count, core.meta_items(sub, br_after=0), icon('chevron-right', 20, 'hom-chev')))


def by_activity(site):
    tiles = ''.join(activity_tile(site, act, lab) for act, lab in core.NAV)
    return ('<section class="wrap sec hom-acts" aria-labelledby="act-h">%s<ul class="hom-tiles">%s</ul></section>'
            % (core.section_head('By activity', plural(len(core.NAV), 'ACTIVITY', 'ACTIVITIES'), id_='act-h'), tiles))


# ---------------------------------------------------------------- where I've been

def region_counts(site, slugs):
    by = site['by_slug']
    ts = [by[s] for s in slugs if s in by]
    pub = [t for t in ts if is_report(t)]
    planned = [t for t in ts if t['kind'] == 'planned']
    if pub:
        return core.count_items(pub, planned)  # '14 REPORTS · + 1 PLANNED ROUTE', as on map/ and the section heads
    return [core.nb(plural(len(planned), 'PLANNED ROUTE'))] if planned else []


def _site_draws(name, pattern):
    """True when the site map fragment rendered/site/<name>.svg.html contains `pattern` (a regex)."""
    try:
        return re.search(pattern, open(os.path.join(core.ROOT, 'rendered', 'site', name + '.svg.html'), encoding='utf-8').read()) is not None
    except OSError:
        return False


# the pin cluster as the region maps draw it (paper disc, ink ring, Mono count), at key-row size
CLUSTER_SYM = ('<svg class="hom-key-cl" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">'
               '<circle cx="10" cy="10" r="9" style="fill:#F2F1EC;stroke:#16171A;stroke-width:1.5"/>'
               '<text x="10" y="10.5" style="font:600 11px/1 var(--mono);fill:#16171A;text-anchor:middle;dominant-baseline:central">2</text></svg>')


def region_key(site, meta, names):
    """One compact key row under the region maps (archive.legend's item logic): an activity disc + word for every activity
    whose pins the drawn maps carry ('other' reads as its sub-type when only one occurs), the planned-route line when a
    planned track is drawn, and the cluster symbol when pins merge. Symbols only, never counts."""
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
    return '<ul class="keyrow keyrow--compact hom-rkey" aria-label="Map key">%s</ul>' % ''.join(items)


def also_items(site):
    """The 'Also' line under the region maps: every other mapped region (core.site_meta()['regions'], most reports first,
    each to its panel on map/), then one 'N more regions' item for the regions without a region map (map/'s 'Not on a
    region map' block, #other-places), then the series. Region counts are published reports, series left out (a series
    has its own item)."""
    mapped = set(core.site_meta().get('regions') or [])
    counts = {}
    for t in site['published']:
        r = t.get('region')
        if r and is_report(t) and t['kind'] != 'series':
            counts[r] = counts.get(r, 0) + 1
    item = '<li><a href="%s"><span class="hom-also-w">%s</span>%s</a></li>'
    out = []
    for r in sorted((r for r in mapped if r not in HOME_REGIONS), key=lambda r: (-counts.get(r, 0), r)):
        k = counts.get(r, 0)
        out.append(item % (core.region_map_href(HERE, r) or link(HERE, 'map/#region-' + slug(r)), esc(r),
                           ('<span class="hom-also-c">%d</span>' % k) if k else ''))
    unmapped = [r for r in counts if r not in mapped and r not in HOME_REGIONS]
    if unmapped:
        more = '%d more region%s' % (len(unmapped), '' if len(unmapped) == 1 else 's')
        out.append(item % (link(HERE, 'map/#other-places'), esc(more), ''))
    out += [item % (link(HERE, t['url']), esc(t['title']), '<span class="hom-also-c">SERIES</span>')
            for t in site['published'] if t['kind'] == 'series']
    return out


def where(site):
    meta = core.site_meta().get('maps', {})
    blocks = []
    drawn = []
    for region in HOME_REGIONS:
        rs = slug(region)
        dk, ph = 'region-%s-desktop' % rs, 'region-%s-phone' % rs
        if dk not in meta and ph not in meta:
            continue
        drawn += [x for x in (dk, ph) if x in meta]
        slugs = (meta.get(dk) or meta.get(ph)).get('trips', [])
        bits = region_counts(site, slugs)
        # the caption shows the count only ('86 REPORTS'); the multi-day / planned breakdown lives on map/, and the link's
        # aria-label keeps the full spoken text
        line = meta_line(bits[:1])
        spoken = ', '.join(b.replace('\u00a0', ' ').replace('+ ', '') for b in bits).lower()
        aria = ('%s: %s. Open the map' % (region, spoken)) if bits else '%s: open the map' % region
        mp = core.map_block(None, HERE, [(dk, 'desktop'), (ph, 'phone')], 'assets/maps/', 'rg-' + rs, site_maps=True, attrib=False)
        blocks.append('<div class="hom-reg"><div class="hom-reg-h"><h3 class="hom-reg-n">%s</h3>'
                      '<span class="t-mono-s hom-reg-c">%s</span>'
                      '<a class="hom-reg-a" href="%s" aria-label="%s">Open the map%s</a></div>%s</div>'
                      % (esc(region), line, link(HERE, 'map/#region-' + rs), esc(aria), icon('arrow-right', 16), mp))
    if not blocks:
        return ''
    also = also_items(site)
    also_html = ('<div class="hom-also"><span class="t-mono-s" id="also-l">ALSO</span><ul aria-labelledby="also-l">%s</ul></div>'
                 % ''.join(also)) if also else ''
    head_meta = plural(sum(1 for t in site['published'] if is_report(t)), 'REPORT')
    return ('<section class="wrap sec hom-where" aria-labelledby="where-h">%s<div class="hom-regions">%s</div>'
            '%s<p class="t-small hom-attr">North up · %s</p>%s</section>'
            % (core.section_head("Where I’ve been", head_meta, id_='where-h'), ''.join(blocks), region_key(site, meta, drawn),
               esc(ATTRIB), also_html))


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
    head = ''
    if ft:
        # the featured map is the first-screen image: its hillshade and base layer load at once (hero variants only)
        variants, _tall = map_variants(ft)
        head = core.map_preloads(ft, HERE, variants, ft['url'] + 'map/', nowide=True)
    doc = core.document(HERE, core.SITE_NAME, ''.join(body), LEAD, active=None, image=img, body_cls='p-home', full_title=TITLE,
                        extra_head=head)
    return core.Page(HERE, doc, core.SITE_NAME)


def build(site):
    return [page(site)]
