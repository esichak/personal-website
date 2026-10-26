"""Home page — / (index.html), Alpine (Phase 17, docs/redesign-c/PROMPT.md 2.6 "Home").

From the top: the hero (the first trip content/home.json features, its cover full width with the title over it) · the
site statement and one computed sentence · By the numbers (the published reports and each activity's count, the
reports by year) · the other features as a grid · Recent written reports and Recent recordings as list rows · Where
I've been (the region maps). Every count, stat and summary is computed from the content; nothing here is written about
Eric beyond the site's statement and tagline.
"""
import re

from sitegen import core
from sitegen.core import esc, U, n, link, icon
from sitegen.pages import archive

HERE = ''
# the site's statement (the lede of the home page since Phase 1) and its tagline
STATEMENT = 'Trip reports from the Sierra, the Alps and beyond.'
LEAD = core.TAGLINE  # the one site tagline (dek, meta description, RSS channel)
# the page's own heading, read by screen readers only: the hero's title is the first heading seen (Phase 17 log)
H1 = 'Eric Sichak: trip reports'
ATTRIB = 'Terrain: AWS Terrain Tiles · Map data © OpenStreetMap contributors · Not for navigation'
HOME_REGIONS = ('Lake Tahoe', 'Eastern Sierra')   # unless content/home.json names others ("region_maps", home_regions)
RECENT_N = 6
# the width each cover is drawn at, so srcset picks the right copy. The hero runs the full width: the 1600 px file from
# 760 px; below 560 px a landscape is declared at core.PHONE_SLOT (the 800 px copy) and core.phone_sizes gives a
# portrait, a square or a panorama its real width
HERO_SIZES = '(min-width: 760px) 100vw, ' + core.PHONE_FULL
# the feature grid inside the 1360 px column: the large card two thirds of the row, the stacked ones the last third, a
# fifth and sixth half each; one column below 760 px
BIG_SIZES = '(min-width: 1400px) 891px, (min-width: 760px) calc((100vw - 104px) * 2 / 3), ' + core.PHONE_FULL
SIDE_SIZES = '(min-width: 1400px) 445px, (min-width: 760px) calc((100vw - 104px) / 3), ' + core.PHONE_FULL
PAIR_SIZES = '(min-width: 1400px) 668px, (min-width: 760px) calc((100vw - 104px) / 2), ' + core.PHONE_FULL
TITLE = 'Eric Sichak · Trip reports: backcountry skiing, climbing, hiking and more'
BAR_MAX = 96          # px: the tallest year's bar


# ---------------------------------------------------------------- small helpers

def plural(k, word, many=None):
    return '%d %s' % (k, word if k == 1 else (many or word + 'S'))


def is_report(t):
    """A 'report' in counts: anything published. A series counts as one report (the same count as every other page)."""
    return t['kind'] != 'planned'


def slug(s):
    return core.content.slugify(s)


def reports(site):
    return [t for t in site['published'] if is_report(t)]


def first_year(site):
    """The earliest year a published report is dated, or None."""
    ys = [t['date'].year for t in reports(site) if t.get('date')]
    return min(ys) if ys else None


def card_action(t):
    """The destination link's one verb (copy-12)."""
    if t['kind'] == 'series':
        return 'Open the journal'
    return 'Read the report' if t['has_writeup'] else 'View the trip'


def place_words(t):
    """'Sawtooth Ridge, Eastern Sierra': the place and the region as written, either alone when the other is missing,
    the region left out when the place already is it."""
    bits = [x for x in (t.get('place'), t.get('region')) if x]
    if len(bits) == 2 and bits[0].strip().casefold() == bits[1].strip().casefold():
        bits = bits[:1]
    return ', '.join(bits)


def stat_items(t, caps=False):
    """The facts line's numbers, through core.U: distance · gain · moving time ('19.9 mi · 7,546 ft · 9:55 moving'; in
    Mono-S caps with caps=True). No gain for a climb or flat water (core.plain_stats' rule), nothing for a series (its
    line is its date range), nothing a trip does not record."""
    if t['kind'] == 'series':
        return []
    st = t['stats'] or {}
    out = []
    mi, km = core.dist_vals(st.get('distance_km'))
    if mi:
        out.append(U(core.caps_unit(mi, 'MI'), core.caps_unit(km, 'KM')) if caps else U(core.nb(mi), core.nb(km), ' mi', ' km'))
    if t['activity'] != 'climb' and not core.is_flat(t) and (st.get('gain_m') or 0) > 30:
        ft, m = n(st['gain_m'] * core.FT), n(st['gain_m'])
        out.append((U(core.caps_unit(ft, 'FT'), core.caps_unit(m, 'M')) if caps else U(ft, m, ' ft', ' m'))
                   + '<span class="sr"> gain</span>')
    if st.get('moving_s'):
        out.append(core.nb(core.hm(st['moving_s']) + (' MOVING' if caps else ' moving')))
    return out


# ---------------------------------------------------------------- the hero

def hero(site):
    """The first featured trip, its cover full width with the scrim and the words over it: FEATURED · ACTIVITY · DATE, the
    title (an h2: the page's h1 is H1, for screen readers), the place and region and, in mono, the stats, then the one
    destination link. A trip without a cover keeps the same parts as a title block on white (the validator warns)."""
    feats = site.get('featured') or []
    if not feats:
        return ''
    t = feats[0]
    href = link(HERE, t['url'])
    img = core.cover_img(t, HERE, HERO_SIZES, eager=True, cls='hom-hero-img')
    over = core.meta_items([core.nb('FEATURED'), core.nb(esc('JOURNAL' if t['kind'] == 'series' else core.act_word(t).upper())),
                            core.trip_date(t)])
    long_ = ' t-d1--long' if len(t['title']) > 28 else ''
    stats = core.meta_items(stat_items(t, caps=True))
    where_ = place_words(t)
    line = ''
    if where_ or stats:
        line = ('<p class="hom-hero-l">%s%s</p>'
                % (('<span class="hom-hero-p">%s</span>' % esc(where_)) if where_ else '',
                   ('<span class="hom-hero-s">%s</span>' % stats) if stats else ''))
    return ('<section class="hom-hero%s" aria-labelledby="hero-t">%s'
            '<div class="hom-hero-f"><div class="hom-hero-b wrap"><p class="t-mono-s hom-hero-o">%s</p>'
            '<h2 class="t-d1%s hom-hero-t" id="hero-t"><a href="%s">%s</a></h2>%s'
            '<a class="hom-hero-go" href="%s">%s<span class="sr">: %s</span>%s</a></div></div></section>'
            % ('' if img else ' hom-hero--plain',
               ('<div class="hom-hero-m">%s<span class="hom-scrim" aria-hidden="true"></span></div>' % img) if img else '',
               over, long_, href, core.title_html(t['title']), line, href, card_action(t), esc(t['title']), icon('arrow-right', 18)))


# ---------------------------------------------------------------- the statement

def statement(site):
    """The site's statement, its tagline and one computed sentence: '167 reports since 2021.' (the count of published
    reports and the year of the earliest date; nothing typed)."""
    k, y = len(reports(site)), first_year(site)
    since = (' %s since %d.' % (plural(k, 'report', 'reports'), y)) if (k and y) else ''
    return ('<section class="wrap hom-intro" aria-label="Introduction"><p class="t-d2 hom-state">%s</p>'
            '<p class="t-dek hom-dek">%s%s</p></section>'
            % (esc(STATEMENT), esc(LEAD), ('<span class="hom-since">%s</span>' % esc(since)) if since else ''))


# ---------------------------------------------------------------- by the numbers

def activity_counts(site):
    """[(act, label, count)] of the five activities, most published reports first, ties in core.NAV order."""
    pub = reports(site)
    rows = [(act, lab, sum(1 for t in pub if t['activity'] == act)) for act, lab in core.NAV]
    order = {act: i for i, (act, _lab) in enumerate(core.NAV)}
    return sorted(rows, key=lambda r: (-r[2], order[r[0]]))


def year_counts(site):
    """[(year, count)] from the earliest dated report's year to the latest, a year without one counted 0. A series or a
    multi-day trip counts once, in the year of its date."""
    ys = [t['date'].year for t in reports(site) if t.get('date')]
    if not ys:
        return []
    return [(y, ys.count(y)) for y in range(min(ys), max(ys) + 1)]


def series_line(site):
    """One sentence per published series, from its fields: '2024 is the Pacific Crest Trail: one journal, Mexico to
    Canada, counted once.' (the start year; the title, less a trailing start year it repeats; the place)."""
    out = []
    for t in reports(site):
        if t['kind'] != 'series' or not t.get('date'):
            continue
        y = t['date'].year
        name = re.sub(r'\s+%d$' % y, '', t['title'].strip())
        out.append('%d is the %s: one journal%s, counted once.' % (y, name, (', ' + t['place']) if t.get('place') else ''))
    return ' '.join(out)


def numbers(site):
    """'By the numbers' (decision 5): the published reports (to trips/) and each activity's count (to its page), then
    one bar per year. Every number is counted from site['published'] at build time; no script."""
    pub = reports(site)
    if not pub:
        return ''
    years = year_counts(site)
    span = ('%d – %d' % (years[0][0], years[-1][0])) if len(years) > 1 else (str(years[0][0]) if years else '')
    meta = core.meta_items([core.nb(span) if span else '', core.nb('COUNTED FROM THE PUBLISHED REPORTS')])
    fig = ('<li><a class="hom-fig" href="%s"><span class="hom-fig-n">%s</span><span class="t-label hom-fig-l">%s</span></a></li>')
    figs = [fig % (link(HERE, 'trips/'), n(len(pub)), 'Reports')]
    for act, lab, k in activity_counts(site):
        dot = '<span class="hom-fig-d" style="background:%s" aria-hidden="true"></span>' % core.ACT[act][3]
        figs.append(fig % (link(HERE, core.section_url(act)), n(k), '%s%s<span class="sr"> reports</span>' % (dot, esc(lab))))
    bars = ''
    if years:
        top = max(k for _y, k in years) or 1
        last = years[-1][0]
        cells = ''.join('<li class="hom-yr%s"><span class="hom-yr-n"><span class="sr">%d: </span>%d<span class="sr"> %s</span></span>'
                        '<span class="hom-yr-b" style="height:%dpx" aria-hidden="true"></span>'
                        '<span class="hom-yr-y" aria-hidden="true">%d</span></li>'
                        % (' hom-yr--last' if y == last else '', y, k, 'report' if k == 1 else 'reports',
                           max(1, round(k * BAR_MAX / top)) if k else 0, y)
                        for y, k in years)
        note = series_line(site)
        bars = ('<div class="hom-years-w"><div class="hom-years-t"><p class="t-label" id="yr-l">Reports by year</p>%s</div>'
                '<ol class="hom-years" aria-labelledby="yr-l">%s</ol></div>'
                % (('<p class="hom-years-n">%s</p>' % esc(note)) if note else '', cells))
    # id="act-h": the address of the old home page's By activity section, which this band replaces
    return ('<section class="wrap sec hom-nums" aria-labelledby="act-h">%s<ul class="hom-figs">%s</ul>%s</section>'
            % (core.section_head('By the numbers', meta, id_='act-h'), ''.join(figs), bars))


# ---------------------------------------------------------------- the other features

def feature(t, i, size):
    """One card of the grid: the cover (the title link names the card, so the photo link is skipped by keyboards and
    readers), else the route tile; '02 · HIKING · SEP 20, 2026'; the serif title; the place and the stats; the card
    summary (core.card_summary: an explicit card_summary, the write-up's opening, a labelled day excerpt), never a
    facts-only one."""
    href = link(HERE, t['url'])
    sizes = {'big': BIG_SIZES, 'side': SIDE_SIZES, 'pair': PAIR_SIZES}[size]
    img = core.cover_img(t, HERE, sizes)
    if img:
        media = '<a class="hom-f-img" href="%s" tabindex="-1" aria-hidden="true">%s</a>' % (href, img)
    else:
        tile = core.card_tile(t, HERE)
        media = ('<a class="hom-f-img hom-f-img--tile" href="%s" tabindex="-1" aria-hidden="true">%s</a>' % (href, tile)) if tile else ''
    mid = 'fc-%s-m' % t['slug']
    over = core.meta_items([core.nb('%02d' % i), core.nb(esc('JOURNAL' if t['kind'] == 'series' else core.act_word(t).upper())),
                            core.trip_date(t, short=True)])
    facts = core.meta_items([core.nb(esc(t.get('place') or t.get('region') or ''))] + stat_items(t))
    summ = core.card_summary(t, 230)
    ex = ''
    if summ['text'] and summ['source_kind'] != 'facts':
        ex = ((('<p class="t-label hom-f-exl">%s</p>' % summ['source_label']) if summ['source_label'] else '')
              + '<p class="t-excerpt hom-f-ex">%s</p>' % esc(summ['text']))
    return ('<li class="hom-f hom-f--%s%s">%s<div class="hom-f-b"><p class="t-mono-s hom-f-o" id="%s">%s</p>'
            '<h3 class="hom-f-t"><a href="%s" aria-describedby="%s">%s</a></h3>%s%s</div></li>'
            % (size, '' if media else ' hom-f--nophoto', media, mid, over, href, mid, core.title_html(t['title']),
               ('<p class="hom-f-pl">%s</p>' % facts) if facts else '', ex))


def features(site):
    """site['featured'][1:] (the first is the hero): the second large, two thirds of the row; the third and fourth
    stacked in the last third; a fifth and sixth a row of two. '' with one featured trip or none."""
    rest = (site.get('featured') or [])[1:]
    if not rest:
        return ''
    cards = ''.join(feature(t, i + 2, 'big' if i == 0 else ('side' if i < 3 else 'pair')) for i, t in enumerate(rest))
    return ('<section class="wrap sec hom-feats" aria-labelledby="feat-h"><h2 class="sr" id="feat-h">More featured trips</h2>'
            '<ul class="hom-fgrid hom-fgrid--%d">%s</ul></section>' % (len(rest), cards))


# ---------------------------------------------------------------- recent reports and recordings

def written(site):
    """The six newest published trips that are written reports (core.written_report: a write-up of 100 characters or
    more, the trip's and its days'), featured or not."""
    return [t for t in site['published'] if core.written_report(t)][:RECENT_N]


def recordings(site):
    """The six newest published trips that are not written reports (a track alone, photos, a line under the track; a
    single day or several): the outings Recent written reports leaves out, so a visitor who found the latest outing on
    the old home page's Recent outings (any published trip) still finds it here or in the list above."""
    return [t for t in site['published'] if not core.written_report(t)][:RECENT_N]


def recent(site):
    rows = written(site)
    if not rows:
        return ''
    total = len(reports(site))
    more = '<a class="hom-all" href="%s">All %d reports%s</a>' % (link(HERE, 'trips/'), total, icon('arrow-right', 16))
    # id="latest-h": the address of the old home page's 'Latest reports' list (and of its hero button), kept so that a
    # saved link to it still lands on the newest reports
    return ('<section class="wrap sec hom-recent" id="latest-h" aria-labelledby="recent-h">'
            '<div class="shead"><h2 class="shead-t" id="recent-h">Recent written reports</h2>%s</div>'
            '<ol class="tlist tlist--wide hom-rows">%s</ol></section>'
            % (more, ''.join(core.trip_row(t, HERE, ns='rw-', photo=True) for t in rows)))


def recent_recordings(site):
    rows = recordings(site)
    if not rows:
        return ''
    return ('<section class="wrap sec hom-recs" aria-labelledby="recs-h">%s<ol class="tlist tlist--wide hom-rows">%s</ol></section>'
            % (core.section_head('Recent recordings', 'NEWEST FIRST', id_='recs-h'),
               ''.join(core.trip_row(t, HERE, ns='rr-') for t in rows)))


# ---------------------------------------------------------------- where I've been

def region_counts(site, slugs):
    by = site['by_slug']
    ts = [by[s] for s in slugs if s in by]
    pub = [t for t in ts if is_report(t)]
    active = {t['slug'] for t in site.get('active_goals', site['planned'])}   # completed / archived goals are not future routes
    planned = [t for t in ts if t['kind'] == 'planned' and t['slug'] in active]
    if pub:
        return core.count_items(pub, planned)  # '14 REPORTS · + 1 PLANNED ROUTE', as on map/ and the section heads
    return [core.nb(plural(len(planned), 'PLANNED ROUTE'))] if planned else []


# the compact key row of the region maps lives in archive.py (the region panels show it on phones too)
_site_draws, CLUSTER_SYM, region_key = archive._site_draws, archive.CLUSTER_SYM, archive.region_key


def also_items(site):
    """The 'Also' line under the region maps: every other mapped region (core.site_meta()['regions'], most reports first,
    each to its own page, or to its panel on map/ when it has none), then one 'N more regions' item for the regions
    without a region map (map/'s 'Not on a region map' block, #other-places), then the series. Region counts are
    published reports, series left out (a series has its own item)."""
    mapped = set(core.site_meta().get('regions') or [])
    # map/ gives a mapped region a panel (and its #region-<slug> anchor) only while it lists a trip there; a region
    # without one is named here only when it has a page of its own to link to (reports filed under it that its stale
    # map does not draw)
    paneled = {name for name, _slug, _ts in core.region_groups(site)}
    counts = {}
    for t in site['published']:
        r = t.get('region')
        if r and is_report(t) and t['kind'] != 'series':
            counts[r] = counts.get(r, 0) + 1
    item = '<li><a href="%s"><span class="hom-also-w">%s</span>%s</a></li>'
    out = []
    shown = home_regions(site)
    others = [r for r in mapped if r not in shown and (r in paneled or core.region_page_href(HERE, r))]
    for r in sorted(others, key=lambda r: (-counts.get(r, 0), r)):
        k = counts.get(r, 0)
        # the region's own page when it has one, else its panel on map/
        href = core.region_page_href(HERE, r) or core.region_map_href(HERE, r) or link(HERE, 'map/#region-' + slug(r))
        out.append(item % (href, esc(r), ('<span class="hom-also-c">%d</span>' % k) if k else ''))
    unmapped = [r for r in counts if r not in mapped and r not in shown]
    if unmapped:
        more = '%d more region%s' % (len(unmapped), '' if len(unmapped) == 1 else 's')
        out.append(item % (link(HERE, 'map/#other-places'), esc(more), ''))
    out += [item % (link(HERE, t['url']), esc(t['title']), '<span class="hom-also-c">SERIES</span>')
            for t in site['published'] if t['kind'] == 'series']
    return out


def home_regions(site):
    """The regions 'Where I've been' maps: content/home.json's region_maps (build.py checks them, as
    curation.resolve_region_maps), else HOME_REGIONS."""
    return tuple(site.get('region_maps') or HOME_REGIONS)


def where(site):
    """The one or two region maps as plates: the render, then the region's name (to its own page when it has one), its
    count and 'Open the map' (to its panel on map/); one key row and the credit under both, the Also line, and the
    section's own 'Open the map', to map/."""
    meta = core.site_meta().get('maps', {})
    blocks = []
    drawn = []
    panels = {s for _n, s, _ts in core.region_groups(site)}   # the regions with a full-screen page, map/<slug>/
    for region in home_regions(site):
        rs = slug(region)
        dk, ph = 'region-%s-desktop' % rs, 'region-%s-phone' % rs
        if dk not in meta and ph not in meta:
            continue
        drawn += [x for x in (dk, ph) if x in meta]
        slugs = (meta.get(dk) or meta.get(ph)).get('trips', [])
        bits = region_counts(site, slugs)
        # the caption shows the count only ('86 REPORTS'); the multi-day / planned breakdown lives on map/, and the link's
        # aria-label keeps the full spoken text
        line = core.meta_items(bits[:1])
        spoken = ', '.join(b.replace('\u00a0', ' ').replace('+ ', '') for b in bits).lower()
        aria = ('%s: %s. Open the map' % (region, spoken)) if bits else '%s: open the map' % region
        # the phone map's corner button opens the region's full-screen page, map/<slug>/ (qa-06), which the Map page writes
        # for each of its panels; no in-map credit tag here, since .hom-attr credits the maps at every width
        mp = core.map_block(None, HERE, [(dk, 'desktop'), (ph, 'phone')], 'assets/maps/', 'rg-' + rs, site_maps=True, attrib=False,
                            fullscreen_href=link(HERE, 'map/%s/' % rs) if rs in panels else None)
        # the name opens the region's own page when it has one; 'Open the map' still goes to its panel on map/
        own = core.region_page_href(HERE, region)
        name = ('<a href="%s">%s</a>' % (own, esc(region))) if own else esc(region)
        blocks.append('<div class="hom-reg">%s<div class="hom-reg-h"><h3 class="hom-reg-n">%s</h3>'
                      '<span class="t-mono-s hom-reg-c">%s</span>'
                      '<a class="hom-reg-a" href="%s" aria-label="%s">Open the map%s</a></div></div>'
                      % (mp, name, line, link(HERE, 'map/#region-' + rs), esc(aria), icon('arrow-right', 16)))
    if not blocks:
        return ''
    also = also_items(site)
    also_html = ('<div class="hom-also"><span class="t-mono-s" id="also-l">ALSO</span><ul aria-labelledby="also-l">%s</ul></div>'
                 % ''.join(also)) if also else ''
    head = ('<div class="shead"><h2 class="shead-t" id="where-h">Where I’ve been</h2>'
            '<a class="hom-all" href="%s">Open the map%s</a></div>' % (link(HERE, 'map/'), icon('arrow-right', 16)))
    return ('<section class="wrap sec hom-where" aria-labelledby="where-h">%s<div class="hom-regions">%s</div>'
            '%s<p class="t-small hom-attr">North up · %s</p>%s</section>'
            % (head, ''.join(blocks), region_key(site, meta, drawn), esc(ATTRIB), also_html))


# ---------------------------------------------------------------- page

def page(site):
    feats = site.get('featured') or []
    lead = feats[0] if feats else None
    body = ['<h1 class="sr">%s</h1>' % esc(H1), hero(site), statement(site), numbers(site), features(site), recent(site),
            recent_recordings(site), where(site)]
    # the hero's cover is the share image and the first-screen image: preloaded, never lazy (core.cover_img eager)
    img = core.share_photo(lead)
    head = core.cover_preload(lead, HERE, HERO_SIZES) if lead else ''
    doc = core.document(HERE, core.SITE_NAME, ''.join(body), LEAD, active=None, image=img, body_cls='p-home', full_title=TITLE,
                        extra_head=head)
    return core.Page(HERE, doc, core.SITE_NAME)


def build(site):
    return [page(site)]
