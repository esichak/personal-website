"""Home page — / (index.html).

Sections: hero · featured trips (the cards content/home.json names, in its order) · recent outings (six, skipping the
featured ones) · by activity · where I've been (region maps).
Every count, stat and summary is computed from the content; nothing here is written about Eric beyond the site lead.
"""
import os
import re

from sitegen import core
from sitegen.core import esc, U, n, link, icon

HERE = ''
LABEL = 'Trip reports · GPX'
# Headline + lead from the approved Main artboard (one line per span; the spans stack on wider screens).
HEADLINE = ('Trip reports from', 'the Sierra, the Alps', 'and beyond.')
LEAD = core.TAGLINE  # the one site tagline (dek, meta description, RSS channel)
ATTRIB = 'Terrain: AWS Terrain Tiles · Map data © OpenStreetMap contributors · Not for navigation'
HOME_REGIONS = ('Lake Tahoe', 'Eastern Sierra')   # unless content/home.json names others ("region_maps", home_regions)
RECENT_N = 6
# the width each cover is drawn at (so srcset picks the 800 px copy where it is enough): the lead card is 7 of 12 columns
# from 1200, the full row on tablets; supporting cards sit beside their copy from 1200 (200 px) and two to a row on
# tablets; recent cards are 3 / 2 / 1 to a row (a 112 px thumbnail on phones)
# below 760 px the cards are a full-width column; phones are told core.PHONE_FULL (the 800 px copy, not the full file)
LEAD_SIZES = '(min-width: 1200px) 718px, (min-width: 760px) calc(100vw - 80px), ' + core.PHONE_FULL
SUB_SIZES = '(min-width: 1200px) 200px, (min-width: 760px) calc((100vw - 104px) / 2), ' + core.PHONE_FULL
WIDE_SUB_SIZES = '(min-width: 1200px) 400px, (min-width: 760px) calc((100vw - 104px) / 2), ' + core.PHONE_FULL  # cards 4-6: three to a row
RECENT_SIZES = '(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2), 112px'
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
    # both actions stay visible on every width (they wrap on narrow phones)
    return ('<div class="hom-hero">'
            '<p class="t-label hom-kicker">%s</p>'
            '<h1 class="t-d2 hom-h1">%s</h1>'
            '<div class="hom-hero-b"><p class="hom-lead">%s</p>'
            '<div class="hom-cta">'
            '<a class="btn btn--ink" href="%s">Browse all trips%s</a>'
            '<a class="btn" href="%s">%sExplore the map</a></div></div></div>'
            % (esc(LABEL), h1, esc(LEAD), link(HERE, 'trips/'), icon('arrow-right', 18), link(HERE, 'map/'), icon('map', 18)))


# ---------------------------------------------------------------- featured trips (content/home.json)

def card_tags(t):
    """Status tags for a card: a series is a 'Journal' here (its link says 'Explore the journal'); multi-day keeps its
    day count; single-day trips carry none (the chip and the meta line say enough)."""
    if t['kind'] == 'series':
        return core.tag('Journal')
    return core.trip_tags(t, shape=False)


def card_place(t):
    """The place, or the region when there is no place (as the list rows do); never the party."""
    loc = t.get('place') or t.get('region') or ''
    return core.nb(esc(loc).upper()) if loc else ''


def card_data(t):
    """At most two data points, Mono-S, as meta_items() items. A series says what it is: recorded days and recorded
    distance ('150 RECORDED DAYS · 3,167 MI RECORDED'), never a trail length or days on trail. Everything else is
    distance · gain (core.plain_stats: no gain for climbs or flat water)."""
    if t['kind'] == 'series':
        k = sum(1 for d in t['days'] if d.get('track'))
        items = [core.nb('%s RECORDED DAY%s' % (n(k), '' if k == 1 else 'S'))] if k else []
        mi, km = core.dist_vals(t['stats'].get('distance_km'))
        if mi:
            items.append(U(core.nb(mi + ' MI RECORDED'), core.nb(km + ' KM RECORDED')))
        return items[:2]
    return core.plain_stats(t, items=True)[:2]


def card_action(t):
    if t['kind'] == 'series':
        return 'Explore the journal'
    return 'Read the report' if t['has_writeup'] else 'View trip'


def card(t, lead=False, wide=False):
    """One featured card: cover (the title link names the card, so the photo link is skipped by keyboards and readers),
    activity chip + tags, H3 title link, DATE · PLACE line, up to two data points, the card summary (an explicit
    card_summary, else the write-up's opening, else a labelled day excerpt for a multi-day trip) and the action link.
    No carousel, no overlay text on the photo."""
    href = link(HERE, t['url'])
    img = core.cover_img(t, HERE, LEAD_SIZES if lead else (WIDE_SUB_SIZES if wide else SUB_SIZES), eager=lead)
    if img:
        media = '<a class="hom-card-img" href="%s" tabindex="-1" aria-hidden="true">%s</a>' % (href, img)
    else:
        tile = core.tile(t, HERE)
        media = ('<a class="hom-card-img hom-card-img--tile" href="%s" tabindex="-1" aria-hidden="true">%s</a>' % (href, tile)) if tile else ''
    chips = '<div class="chips hom-card-chips">%s%s</div>' % (core.chip(t, href=link(HERE, core.section_url(t['activity']))), card_tags(t))
    meta = meta_line([core.trip_date(t), card_place(t)])
    data = meta_line(card_data(t))
    summ = core.card_summary(t, 230)
    ex = ''
    # a 'facts' summary (a series, or a multi-day trip with no writing) repeats the DATE · PLACE and data lines above
    # it, so the card leaves it out: the lines already say what the trip is, and nothing is invented to fill the slot
    if summ['text'] and summ['source_kind'] != 'facts':
        ex = ((('<p class="t-label hom-card-exl">%s</p>' % summ['source_label']) if summ['source_label'] else '')
              + '<p class="t-excerpt hom-card-ex">%s</p>' % esc(summ['text']))
    mid = 'fc-%s-m' % t['slug']
    return ('<li class="hom-card %s%s">%s<div class="hom-card-b">%s'
            '<h3 class="t-h3 hom-card-t"><a href="%s"%s>%s</a></h3>%s%s%s'
            '<a class="alink hom-card-go" href="%s">%s<span class="sr">: %s</span>%s</a></div></li>'
            % ('hom-card--lead' if lead else 'hom-card--sub', '' if media else ' hom-card--nophoto', media, chips,
               href, (' aria-describedby="%s"' % mid) if meta else '', core.title_html(t['title']),
               ('<p class="t-mono-s hom-card-meta" id="%s">%s</p>' % (mid, meta)) if meta else '',
               ('<p class="t-mono-s hom-card-data">%s</p>' % data) if data else '',
               ex, href, card_action(t), esc(t['title']), icon('arrow-right', 16)))


def featured(site):
    """The curated features (site['featured'], from content/home.json), the first as the lead card. '' when the manifest
    lists none: an explicit empty list hides the section rather than showing some other trip."""
    feats = site.get('featured') or []
    if not feats:
        return ''
    cards = ''.join(card(t, lead=(i == 0), wide=(i >= 3)) for i, t in enumerate(feats))
    return ('<section class="wrap sec hom-featured" aria-labelledby="feat-h">%s<ul class="hom-cards hom-cards--%d">%s</ul></section>'
            % (core.section_head('Featured trips', plural(len(feats), 'TRIP'), id_='feat-h'), len(feats), cards))


# ---------------------------------------------------------------- recent outings

def recent_trips(site):
    """The six newest published trips that are not featured above (they stay on the Trips page); planned routes are never
    in site['published']. Ordered by trip date, as the whole site is."""
    skip = {t['slug'] for t in (site.get('featured') or [])}
    return [t for t in site['published'] if t['slug'] not in skip][:RECENT_N]


def rcard(t, repeated=()):
    """A recent-outing card: the shared core.trip_card (cover photo, else route tile, else activity disc; DATE · PLACE;
    the H3 title link; activity + stats), with the opening of Eric's write-up where the trip has one (trip_card leaves out
    a facts-only summary, so a track-only outing has no excerpt and carries the Track only tag). repeated: the titles more than one trip on the page carries
    (core.repeated_titles), whose links also name the date."""
    return core.trip_card(t, HERE, RECENT_SIZES, ns='rc', summary=True, repeated=repeated)


def recent(site):
    rows = recent_trips(site)
    if not rows:
        return ''
    total = sum(1 for t in site['published'] if is_report(t))
    repeated = core.repeated_titles(rows + list(site.get('featured') or []))
    # id="latest-h": the address of the old home page's 'Latest reports' list (and of its hero button), kept so that a
    # saved link to it still lands on the newest reports
    return ('<section class="wrap sec hom-recent" id="latest-h" aria-labelledby="recent-h">%s<ul class="hom-rcards tgrid">%s</ul>'
            '<a class="btn hom-all" href="%s">All %d reports%s</a></section>'
            % (core.section_head('Recent outings', 'NEWEST FIRST', id_='recent-h'), ''.join(rcard(t, repeated) for t in rows),
               link(HERE, 'trips/'), total, icon('arrow-right', 18)))


# ---------------------------------------------------------------- by activity

def activity_tile(site, act, label):
    pub = [t for t in site['published'] if t['activity'] == act]
    reps = [t for t in pub if is_report(t)]
    planned = [t for t in site.get('active_goals', site['planned']) if t['activity'] == act]  # the live tick-list goals
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
    active = {t['slug'] for t in site.get('active_goals', site['planned'])}   # completed / archived goals are not future routes
    planned = [t for t in ts if t['kind'] == 'planned' and t['slug'] in active]
    if pub:
        return core.count_items(pub, planned)  # '14 REPORTS · + 1 PLANNED ROUTE', as on map/ and the section heads
    return [core.nb(plural(len(planned), 'PLANNED ROUTE'))] if planned else []


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
    meta = core.site_meta().get('maps', {})
    blocks = []
    drawn = []
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
        line = meta_line(bits[:1])
        spoken = ', '.join(b.replace('\u00a0', ' ').replace('+ ', '') for b in bits).lower()
        aria = ('%s: %s. Open the map' % (region, spoken)) if bits else '%s: open the map' % region
        mp = core.map_block(None, HERE, [(dk, 'desktop'), (ph, 'phone')], 'assets/maps/', 'rg-' + rs, site_maps=True, attrib=False)
        # the name opens the region's own page when it has one; 'Open the map' still goes to its panel on map/
        own = core.region_page_href(HERE, region)
        name = ('<a href="%s">%s</a>' % (own, esc(region))) if own else esc(region)
        blocks.append('<div class="hom-reg"><div class="hom-reg-h"><h3 class="hom-reg-n">%s</h3>'
                      '<span class="t-mono-s hom-reg-c">%s</span>'
                      '<a class="hom-reg-a" href="%s" aria-label="%s">Open the map%s</a></div>%s</div>'
                      % (name, line, link(HERE, 'map/#region-' + rs), esc(aria), icon('arrow-right', 16), mp))
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
    feats = site.get('featured') or []
    lead = feats[0] if feats else None
    body = ['<section class="wrap hom-top" aria-label="Introduction">%s</section>' % hero(),
            featured(site), recent(site), by_activity(site), where(site)]
    # the lead card's cover is the share image and the first-screen image: preloaded, never lazy (core.cover_img eager)
    img = core.share_photo(lead)
    head = core.cover_preload(lead, HERE, LEAD_SIZES) if lead else ''
    doc = core.document(HERE, core.SITE_NAME, ''.join(body), LEAD, active=None, image=img, body_cls='p-home', full_title=TITLE,
                        extra_head=head)
    return core.Page(HERE, doc, core.SITE_NAME)


def build(site):
    return [page(site)]
