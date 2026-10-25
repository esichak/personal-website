"""Single-day trip report (kind: trip) and tick-list goals (kind: planned) — /trips/<slug>/, plus the phone full-screen
map page /trips/<slug>/map/. A goal page says Planned route and Planning notes, never Trip report: its line is a plan or
somebody else's recording, its numbers are approximate, and completion exists only as an explicitly logged outing.

Four cases (page()): a story (a write-up and a photo, narrative()) leads with the cover, a stats strip, a section row and
the write-up, then the map, the profile and the remaining photos; a written report without photos whose write-up
clears core.STRUCTURED_MIN_CHARS takes the same order without the photo (written_first()); a photo-only report keeps the
compact map-first order with its cover leading (when lead_photo() allows); every other report keeps the compact order.
All end with related reports and the pager, and all keep the ids #title #stats #map #profile #beta #report #photos.
One label table (LABELS) names the sections in the section row, the phone bottom bar and multiday's bar."""
from datetime import date

import markdown
import goals
import content

from sitegen import core
from sitegen.core import esc, U, U_sub, n, link, icon, FT, MI


HERO_SIZES = '(min-width: 1200px) 1248px, ' + core.PHONE_FULL   # phones take the 800 px copy (core.PHONE_SLOT)


def narrative(t):
    """True when a single-day report reads as a story: Eric wrote it up and it has a photo (t['cover']). Track-only
    reports, photo-only reports and write-ups without a photo do not (written_first() has the last of those)."""
    return t['kind'] == 'trip' and bool(t['body_md']) and bool(t.get('cover'))


def has_photos(t):
    return any(p.get('file') for p in t['photos'])


def written_first(t):
    """True for a single-day report with a write-up and no photo whose words clear core.STRUCTURED_MIN_CHARS (the
    BlogPosting floor, core.written_report): it leads with the words, in the story order without a lead photo. A note
    under that floor stays in the compact order, after the map (Phase 10, report-01)."""
    return t['kind'] == 'trip' and bool(t['body_md']) and not has_photos(t) and core.written_report(t)


LEAD_MIN_AR = content.LEAD_MIN_AR   # 1.2: the lead frame is 4:3 to 2:1; the automatic cover pick uses the same line


def lead_photo(t):
    """The trip's cover when it can lead a page: a landscape photo (LEAD_MIN_AR; a photo without recorded dimensions counts
    as one). A portrait or square cover stays where it is, in the Photos section or beside the write-up: it
    still fronts the trip's cards, whose frames are much less wide. None when the trip has no cover."""
    c = t.get('cover')
    if not c or core.photo_ar(c['photo']) < LEAD_MIN_AR:
        return None
    return c['photo']


def hero(t, here, photos_anchor=False):
    """The lead photo of a story, of a photo-only report, of a multi-day trip or of the journal: the cover
    (content.resolve_cover) at full width, linked to its file so the viewer opens it; data-lb-group ties it to a report's
    Photos grid, so the viewer counts every photo of the trip once. A multi-day trip and the journal have no such grid,
    so there it opens on its own, and the photo shows again in its day.
    photos_anchor: the report's only photo is this one, so there is no Photos section below; an empty #photos target here
    keeps an old link to trips/<slug>/#photos landing on the photo."""
    c = t['cover']
    p = c['photo']
    cap = (' data-cap="%s"' % esc(p['caption'])) if p.get('caption') else ''
    fc = ('<figcaption class="t-small">%s</figcaption>' % esc(p['caption'])) if p.get('caption') else ''
    name = '' if p.get('alt') else ' aria-label="Lead photo, full size"'
    anchor = '<span class="rep-anchor" id="photos"></span>' if photos_anchor else ''
    return ('<figure class="rep-hero wrap" id="hero">%s<a class="jph jph--l rep-hero-a" href="%s%s" data-lb-group="photos"%s%s>%s</a>%s</figure>'
            % (anchor, link(here, t['url']), p['file'], cap, name, core.cover_img(t, here, HERO_SIZES, eager=True), fc))


def published_line(t):
    """'Published Oct 3, 2026 · Updated Oct 5, 2026', only when index.md states published_at (and updated_at): the visible,
    labelled date the page's structured data must agree with. '' otherwise: the trip date is not a publication date."""
    def when(text):
        return '<time datetime="%s">%s</time>' % (esc(text), core.fdate(date.fromisoformat(text[:10]), 'short'))
    if not t.get('published_at'):
        return ''
    bits = ['Published ' + when(t['published_at'])]
    if t.get('updated_at'):
        bits.append('Updated ' + when(t['updated_at']))
    return '<p class="wrap rep-pub t-mono-s">%s</p>' % ' · '.join(bits)


def share_row(here):
    """Phones hide the title block's actions (the bottom bar carries the sections and the GPX), so the copy-link control
    sits at the end of the page there, before what to read next. Hidden from 760 up, where the title actions hold it."""
    return '<div class="wrap rep-share">%s</div>' % core.copy_link(core.SITE_URL + here, 'Copy link to this page', cls='alink')


# one name per section, wherever a list leads to it: the section row, the phone bottom bar, multiday's bar (copy-09)
LABELS = {'#stats': 'Stats', '#beta': 'Beta', '#report': 'Report', '#map': 'Map', '#profile': 'Elevation', '#photos': 'Photos'}
ICONS = {'#stats': 'beta', '#beta': 'beta', '#report': 'report', '#map': 'map', '#profile': 'profile', '#photos': 'photo'}
# the order the sections run in on the page: the story (and written-first) order puts the write-up and its Beta rail
# before the map; the compact order puts the map and its chart first
STORY_ORDER = ('#stats', '#beta', '#report', '#map', '#profile', '#photos')
COMPACT_ORDER = ('#stats', '#map', '#profile', '#beta', '#report', '#photos')


def label(href, chart=''):
    """A section's name (LABELS); the chart of a flat-water report is its Speed chart."""
    return 'Speed' if href == '#profile' and chart == 'speed' else LABELS[href]


def section_nav(has_report, has_gallery, has_map=True, chart=''):
    """The section row under the strip of the story and written-first layouts: Report · Map · Elevation (or Speed) ·
    Photos, the sections the page has, in page order, named as LABELS names them. No link is marked current: the row
    scrolls away with the header, so it is on screen only above the sections it lists. has_map=False: a report without
    a track has no map section; chart: has_chart(meta)."""
    items = [h for h, on in (('#report', has_report), ('#map', has_map), ('#profile', bool(chart)), ('#photos', has_gallery)) if on]
    return ('<nav class="rep-toc wrap" aria-label="Sections"><ul>%s</ul></nav>'
            % ''.join('<li><a class="rep-toc-a" href="%s">%s</a></li>' % (h, label(h, chart)) for h in items))


def date_slot(t):
    """The Mono-S value after the chips: the date, or the planned distance for a planned route (it has no date; the
    PLANNED tag chip before it already says so)."""
    if t['kind'] == 'planned':
        mi, km = core.dist_vals(t['stats'].get('distance_km'))
        return U(core.nb('≈ ' + mi + ' MI'), core.nb('≈ ' + km + ' KM')) if mi else ''
    return core.trip_date(t)


def title_block(t, here, actions, strip_follows=False):
    """Shared by single-day, planned, multi-day and series pages. Phones (< 760) drop the crumbs and the date slot; the date
    then leads the place line (Phone-Report-A). strip_follows: a goal page whose strip states the ≈ distance, which the
    date slot then leaves out (said once, visual-19)."""
    act = t['activity']
    sec = link(here, core.section_url(act))
    if t['kind'] == 'planned':
        crumbs = ['<a href="%s">Tick list</a>' % link(here, 'tick-list/')]
        tags = core.tag('Planned route') + core.goal_tags(t['goal'])
    else:
        crumbs = ['<a href="%s">Reports</a>' % link(here, ''), '<a href="%s">%s</a>' % (sec, esc(core.ACT[act][0]))]
        tags = core.trip_tags(t)
    # the region's own page when it has one (a region with a region map), else its place on map/
    reg = core.region_page_href(here, t.get('region')) or core.region_map_href(here, t.get('region'))
    if reg:
        crumbs.append('<a href="%s">%s</a>' % (reg, esc(t['region'])))
    long_ = len(t['title']) > 28
    date_ = '' if (strip_follows and t['kind'] == 'planned') else date_slot(t)
    # one meta line: the date item leads it on phones only (>= 760 the date sits in the chip row)
    place = core.meta_items(([(date_, 'rep-pdate')] if date_ else []) + core.place_line(t, items=True))
    return ('<section class="rep-title wrap" aria-labelledby="title">'
            '<nav class="crumbs" aria-label="Breadcrumb">%s</nav>'
            '<div class="chips rep-chips">%s%s%s</div>'
            '<div class="rep-head"><div class="rep-head-t"><h1 id="title" class="t-d1%s">%s</h1>'
            '<p class="t-mono-s rep-place">%s</p></div><div class="rep-actions">%s</div></div></section>'
            % ('<span aria-hidden="true">/</span>'.join(crumbs), core.chip(t, href=sec), tags,
               ('<span class="t-mono-s">%s</span>' % date_) if date_ else '',
               ' t-d1--long' if long_ else '', core.title_html(t['title']), place, actions))


def key_items(t, meta, phone=False):
    """Symbols the map draws. The phone render (render.py SMALL) draws no skin/ski styling and no mile markers."""
    planned = t['kind'] == 'planned'
    flat = 'speed-wide' in meta.get('charts', {})
    ends = ['start', 'end'] if t.get('route_shape') == 'point-to-point' else ['start_end']
    if planned:
        # the planned render only gets its start / end markers with render-markers; never key a marker the map lacks
        m = meta['maps']
        name = 'map-phone' if phone else next((k for k in ('map-wide', 'map-col') if k in m), 'map-col')
        start, end = core.drawn_ends(t, name)
        if ends == ['start_end'] and not (start and end):
            ends = ['start'] if start else (['end'] if end else [])
        else:
            ends = [k for k in ends if (k == 'start' and start) or (k == 'end' and end)]
        return ['planned'] + ends
    if phone:
        return ['route'] + ends + ([] if flat else ['gps'])
    items = (['skin', 'ski'] if t['activity'] == 'ski' else ['route']) + ends
    if not flat:
        items.append('gps')
        m = meta['maps'].get('map-wide') or meta['maps'].get('map-col') or {}
        items.append('mile_out' if m.get('outbound_only') else 'mile')
    # the base layer's trails and roads, when the desktop renders draw them (maps-02)
    return items + core.base_keys(t, [k for k in ('map-wide', 'map-col') if k in meta['maps']])


def map_caption(t):
    """The shared map caption (core.map_caption): what the line is, the contour interval of the visible render, then
    the credit. No GPX button: the ink title button (>= 760) and the phone bottom bar carry it."""
    first = []
    if t['kind'] == 'planned':
        first.append('Planned route, not a recorded track')
    else:
        if t['date']:
            first.append(core.recorded(t['date']))
        first.append('full track, not trimmed')
    first.append('North up')
    return core.map_caption(first + core.contour_items(t, [('map-wide', 'wide'), ('map-col', 'col'), ('map-phone', 'phone')]))


def has_chart(meta):
    """The chart profile_section() draws: 'speed' (flat water), 'profile' or '' (none)."""
    ch = meta.get('charts', {})
    return 'speed' if 'speed-wide' in ch else ('profile' if 'profile-wide' in ch else '')


def profile_section(t, here, meta, ns='pf'):
    """The Elevation (or flat-water Speed) section; id="profile" is the phone bottom bar's target."""
    ch = meta.get('charts', {})
    if 'speed-wide' in ch:
        return ('<section class="rep-prof wrap sec" id="profile" aria-labelledby="%s-h"><div class="rep-prof-h"><h2 class="t-label" id="%s-h">Speed</h2>'
                '<p class="t-mono-s">%s</p>%s</div>%s</section>'
                % (ns, ns, core.speed_meta(t), core.key_row(['speed'], 'keyrow--inline', label='Speed key'),
                   core.chart_block(t, here, [('speed-wide', 'wide'), ('speed-col', 'col'), ('speed-phone', 'phone')], ns)))
    p = ch.get('profile-wide')
    if not p:
        return ''
    st = t['stats']
    hi = st.get('high_m') or (p['gps_max_ft'] / FT)
    lo = st.get('low_m') or (p['min_ft'] / FT)
    variants = [('profile-wide', 'wide'), ('profile-col', 'col'), ('profile-phone', 'phone')]
    tr = core.read_track(t['track'], t['slug'], t['cat'])
    when = core.gps_max_clock(tr, t.get('timezone'))
    meta_line = core.meta_items(['GPS\u00a0MAX\u00a0' + U(core.nb(n(hi * FT) + ' FT'), core.nb(n(hi) + ' M'))
                                 + (core.nb(' AT ' + when) if when else ''),
                                 'MIN\u00a0' + U(core.nb(n(lo * FT) + ' FT'), core.nb(n(lo) + ' M'))] + core.vx_line(ch, variants, items=True))
    keys = core.key_row(['hatch', 'fill'], 'keyrow--inline', label='Elevation key') if t['activity'] == 'ski' else ''
    return ('<section class="rep-prof wrap sec" id="profile" aria-labelledby="%s-h"><div class="rep-prof-h"><h2 class="t-label" id="%s-h">Elevation</h2>'
            '<p class="t-mono-s">%s</p>%s</div>%s%s</section>'
            % (ns, ns, meta_line, keys, core.chart_block(t, here, variants, ns, readout=core.profile_readout(tr, st)),
               core.elevation_table(tr, st, t.get('timezone'))))


def beta_rows(t, noted=True):
    """Beta rows from the front matter, minus what the page already shows: 'Track' (the stats footnote prints it) and, for
    climbing, 'Pitches' (the data strip leads with it). Route shape lives in the chip row, party in the place line.
    noted=False: the page has no stats strip, so no footnote either, and the Track row stays in the block."""
    skip = ({'track'} if noted else set()) | ({'pitches'} if t['activity'] == 'climb' else set())
    return [r for r in t['beta'] if r.get('label') and str(r['label']).strip().lower() not in skip]


SUMMIT_OUTCOME_WORDS = {'turned-around': 'turned around', 'traverse': 'traverse'}   # 'summit' says nothing extra


def summit_item(s):
    """One summits: entry as the Beta rail says it: 'Mount Tallac', 'Mount Tallac via the East Ridge (turned around)'."""
    word = SUMMIT_OUTCOME_WORDS.get(s['outcome'])
    return esc(s['name'] + ((' via ' + s['route']) if s['route'] else '') + ((' (%s)' % word) if word else ''))


def beta_list(t, noted=True):
    """The rail's Beta block: dotted leaders drawn by the dt (base.css .dl-leader), values right-aligned and balanced.
    The trip's summits: (Phase 9) are its last row, Summits, one per line when there are two or more."""
    rows = beta_rows(t, noted)
    summits = [summit_item(s) for s in t.get('summits') or []]
    if not rows and not summits:
        return ''
    def value(v):
        # a list value ('Corrugation Corner, Surrealistic Pillar') stacks one item per line, right-aligned, so the dd is
        # only as wide as its longest item and the leader runs up to the text
        parts = [x.strip() for x in str(v).split(', ') if x.strip()]
        if len(parts) < 2:
            return esc(str(v))
        return ' '.join('<span>%s%s</span>' % (esc(x), ',' if i < len(parts) - 1 else '') for i, x in enumerate(parts))
    def linked(r):
        # a row's url: makes its value a link when it is a full http or https address (content.web_url, the check's
        # own test, which refuses anything else)
        url = content.web_url(r.get('url'))
        v = value(r['value'])
        return ('<a href="%s" rel="noopener">%s</a>' % (esc(url), v)) if url else v
    out = ''.join('<div><dt>%s</dt><dd%s>%s</dd></div>' % (esc(r['label']), ' class="dl-list"' if '<span>' in value(r['value']) else '',
                                                           linked(r)) for r in rows)
    if summits:
        # the names are stacked as a list value is, each written out whole (a route may hold a comma of its own)
        out += ('<div><dt>Summits</dt><dd class="dl-list">%s</dd></div>'
                % ' '.join('<span>%s%s</span>' % (x, ',' if i < len(summits) - 1 else '') for i, x in enumerate(summits))
                if len(summits) > 1 else '<div><dt>Summits</dt><dd>%s</dd></div>' % summits[0])
    return '<div class="rail-b" id="beta"><h2 class="t-label" id="beta-h">Beta</h2><dl class="dl-leader">%s</dl></div>' % out


def lone_portrait(t):
    """The report's only photo when it is a portrait: it sits beside the write-up instead of in a Photos section."""
    ps = [p for p in t['photos'] if p.get('file')]
    return ps[0] if len(ps) == 1 and core.photo_ar(ps[0]) < 1 else None


def aside_photo(t, here, p):
    cap = (' data-cap="%s"' % esc(p['caption'])) if p.get('caption') else ''
    fc = ('<figcaption class="t-small">%s</figcaption>' % esc(p['caption'])) if p.get('caption') else ''
    return ('<figure class="rep-aside-ph"><a class="jph jph--p" href="%s%s"%s>%s</a>%s</figure>'
            % (link(here, t['url']), p['file'], cap,
               core.photo(t, p, here, sizes='(min-width: 1200px) 294px, (min-width: 1000px) 22vw, (min-width: 760px) 240px, ' + core.PHONE_FULL,
                          caption=False), fc))


def gallery(t, here, photos, ns='ph', lead=0):
    """Photos in their order as justified rows (core.photo_rows): every row fills the column; landscapes alone are 2:1,
    runs of portraits share a row, never cropped into the wide format. lead: 1 when the lead photo sits above (it is
    not in `photos`): the heading counts the grid, the unnamed photos are numbered as the viewer numbers them."""
    if not photos:
        return ''
    return ('<section class="rep-photos wrap sec" id="photos" aria-labelledby="%s-h" data-lb-group="photos"><div class="rep-sh"><h2 class="t-h3" id="%s-h">Photos</h2>'
            '<span class="t-mono-s">%d PHOTO%s</span></div>%s</section>'
            % (ns, ns, len(photos), '' if len(photos) == 1 else 'S', core.photo_rows(t, here, photos, ns=ns, lead=lead)))


def neighbours(t, site):
    """(newer, older): the published reports of t's activity on either side of it, None at an end (or for a page that is
    not a published report). The pager links to them, and 'More like this' leaves them out."""
    same = [x for x in site['published'] if x['activity'] == t['activity']]
    if t not in same:
        return None, None
    i = same.index(t)
    return (same[i - 1] if i > 0 else None), (same[i + 1] if i + 1 < len(same) else None)


def pager(t, here, site):
    newer, older = neighbours(t, site)
    cells = []
    for lab, x, cls in (('Newer', newer, 'prev'), ('Older', older, 'next')):
        if not x:
            continue
        arrow = icon('arrow-left' if cls == 'prev' else 'arrow-right', 14)
        lbl = ('%s<span>%s</span>' % (arrow, lab)) if cls == 'prev' else ('<span>%s</span>%s' % (lab, arrow))
        g = core.glyph(x, here, 'g112', cls=' glyph')
        meta = core.meta_items([core.trip_date(x)] + core.plain_stats(x, items=True), br_after=0)
        txt = ('<span class="pager-t"><span class="t-label pager-l">%s</span><span class="pager-n">%s</span>'
               '<span class="t-mono-s">%s</span></span>' % (lbl, core.title_html(x['title']), meta))
        cells.append('<a class="%s" href="%s">%s</a>' % (cls, link(here, x['url']), (g + txt) if cls == 'prev' else (txt + g)))
    if not cells:
        return ''
    return '<nav class="pager wrap sec" aria-label="More %s reports">%s</nav>' % (esc(core.ACT[t['activity']][0].lower()), ''.join(cells))


def planned_pager(t, here, site):
    """A planned route's way onward (the pager markup, no glyphs): back to the section, and the region on the map."""
    act = t['activity']
    word = core.ACT[act][0]
    same = [x for x in site['trips'] if x['activity'] == act]
    counts = core.meta_items(core.count_items([x for x in same if x['kind'] != 'planned'], [x for x in same if x['kind'] == 'planned']))
    cells = ['<a class="prev" href="%s"><span class="pager-t"><span class="t-label pager-l">%s<span>%s</span></span>'
             '<span class="pager-n">All %s reports</span><span class="t-mono-s">%s</span></span></a>'
             % (link(here, core.section_url(act)), icon('arrow-left', 14), esc(word), esc(word.lower()), counts)]
    cells += region_cell(t, here)
    return '<nav class="pager wrap sec" aria-label="More %s">%s</nav>' % (esc(word.lower()), ''.join(cells))


def bottom_bar(t, here, gpx_href, has_beta, has_report, has_gallery, chart='', story=False, has_map=True, has_stats=True):
    """Phone bottom bar, in page order (STORY_ORDER, COMPACT_ORDER), named by LABELS. Compact layout: Map, Beta (or the
    Elevation / Speed chart when there is no beta), Report (or Photos), GPX; Stats, when there is neither beta nor a
    chart, comes first (the strip sits above the map). Story and written-first layouts: Report · Map · Photos · GPX;
    without a Photos grid, Beta · Report · Map · GPX when there is beta, else Report · Map · Elevation / Speed · GPX, or
    Stats · Report · Map · GPX without a chart. chart: has_chart(meta). gpx_href: '' for a report
    without a track, which then has no GPX item and, with has_map=False, no Map item either; has_stats=False: no Stats
    item (the page has no strip). '' when a single item would be left: one link is not navigation."""
    chart_item = ['#profile'] if chart else (['#stats'] if has_stats else [])
    map_item = ['#map'] if has_map else []
    if story:
        items = []
        if has_beta and not has_gallery:
            items.append('#beta')
        items += ['#report'] + map_item
        if has_gallery:
            items.append('#photos')
        elif not has_beta:
            items += chart_item
    else:
        items = list(map_item)
        if has_beta:
            items.append('#beta')
        elif t['kind'] != 'planned':
            items += chart_item
        if has_report:
            items.append('#report')
        elif has_gallery:
            items.append('#photos')
    items.sort(key=(STORY_ORDER if story else COMPACT_ORDER).index)
    k = len(items) + (1 if gpx_href else 0)
    if k < 2:
        return ''
    out = ''.join('<a href="%s">%s<span>%s</span></a>' % (h, icon(ICONS[h], 24), label(h, chart)) for h in items)
    if gpx_href:
        out += '<a href="%s" download>%s<span>GPX</span></a>' % (gpx_href, icon('download', 24))
    return '<nav class="bbar" aria-label="Report sections" style="--n:%d">%s</nav>' % (k, out)


# ---------------------------------------------------------------- tick-list goal pages (kind: planned)

def goal_strip(t):
    """The approximate numbers a goal has (distance; gain only with full elevation; the file's high point), each marked ≈,
    with a note saying where they come from and what is unknown. Never a moving time: a plan has none."""
    g, st = t['goal'], t['stats']
    cells = []
    mi, km = core.dist_vals(st.get('distance_km'))
    if mi:
        cells.append(('Distance', '≈ ' + U(mi, km, 'mi', 'km'), U_sub(mi, km, 'mi', 'km')))
    if st.get('gain_m') is not None:
        v = st['gain_m']
        cells.append(('Gain', '≈ ' + U(n(v * FT), n(v), 'ft', 'm'), U_sub(n(v * FT), n(v), 'ft', 'm')))
    if st.get('high_m') is not None:
        v = st['high_m']
        cells.append(('High point', '≈ ' + U(n(v * FT), n(v), 'ft', 'm'), U_sub(n(v * FT), n(v), 'ft', 'm')))
    if not cells:
        return ''
    if g.get('route'):
        src = goals.SOURCE_LABELS[g['route_source']['kind']]
        bits = ['Approximate, measured from the planned route (%s, %s).' % (src, goals.SCOPE_LABELS[g['route_scope']])]
        if g['route']['elevation'] == 'none':
            bits.append('The file has no elevation, so no gain is shown.')
        elif g['route']['elevation'] == 'partial':
            bits.append('Elevation covers only part of the route, so no gain is shown.')
    else:
        bits = ['Approximate values from the planned route file.']
    if st.get('high_m') is not None:
        bits.append('The high point is the highest point in the file, not a surveyed summit.')
    return ('<section class="wrap rep-strip" id="stats" aria-label="Approximate stats">%s<p class="strip-note">%s</p></section>'
            % (core.strip(cells, label='Approximate stats'), ' '.join(bits)))


def goal_map_section(t, here, meta):
    variants = [('map-wide', 'wide'), ('map-col', 'col'), ('map-phone', 'phone')]
    if meta['maps']:
        nowide = 'map-wide' not in meta['maps']
        return ('<section class="rep-map" id="map" aria-label="Planned route map"><div class="bleed">%s</div><div class="wrap">%s%s</div></section>'
                % (core.map_block(t, here, variants, t['url'] + 'map/', 'm', eager=True, cls='map--report' + (' map--nowide' if nowide else ''),
                                  fullscreen_href=link(here, t['url'] + 'map/')),
                   core.key_rows(key_items(t, meta), key_items(t, meta, phone=True)), map_caption(t)))
    if t['track']:
        # no direction ('above'): on phones the download is the bottom bar's GPX item
        text = 'Map not rendered yet. The planned GPX is published: use the Download planned GPX button.'
    else:
        text = 'No route added yet: this is an idea without a GPX.'
    # .rep-map: the same distance from the strip as a rendered map, so the page keeps its rhythm either way
    return not_rendered_section('Planned route map', text)


def not_rendered_section(name, text):
    """The #map section of a page whose track has no rendered map yet: the goal page's empty box and the sentence."""
    return ('<section class="rep-map rep-map--empty" id="map" aria-label="%s"><div class="wrap"><div class="empty">%s<p>%s</p></div></div></section>'
            % (esc(name), icon('map', 24), esc(text)))


def goal_bottom_bar(t, has_notes):
    """Phone bottom bar of a goal: Map · Notes · GPX, each only when the page has it. '' when it would hold a single item
    (an idea without notes or a route: one link to the 'no route yet' box is not navigation)."""
    items = [('#map', 'map', 'Map')]
    if has_notes:
        items.append(('#report', 'report', 'Notes'))
    k = len(items) + (1 if t['track'] else 0)
    if k < 2:
        return ''
    out = ''.join('<a href="%s">%s<span>%s</span></a>' % (h, icon(ic, 24), lab) for h, ic, lab in items)
    if t['track']:
        out += '<a href="%s" download>%s<span>GPX</span></a>' % (t['slug'] + '.gpx', icon('download', 24))
    return '<nav class="bbar" aria-label="Goal sections" style="--n:%d">%s</nav>' % (k, out)


def region_cell(t, here):
    """The pager's second cell: the region's own page ('All <Region> reports') when it has one, else its place on map/
    ('Open the map'); [] for a trip without a region, or one whose region is not on map/."""
    own = core.region_page_href(here, t.get('region'))
    reg = own or core.region_map_href(here, t.get('region'))
    if not reg:
        return []
    text = ('All %s reports' % esc(t['region'])) if own else 'Open the map'
    return ['<a class="next" href="%s"><span class="pager-t"><span class="t-label pager-l"><span>%s</span>%s</span>'
            '<span class="pager-n">%s</span></span></a>' % (reg, esc(t['region']), icon('arrow-right', 14), text)]


def goal_pager(t, here):
    cells = ['<a class="prev" href="%s"><span class="pager-t"><span class="t-label pager-l">%s<span>Tick list</span></span>'
             '<span class="pager-n">Back to the tick list</span></span></a>' % (link(here, 'tick-list/'), icon('arrow-left', 14))]
    cells += region_cell(t, here)
    return '<nav class="pager wrap sec" aria-label="More goals">%s</nav>' % ''.join(cells)


def _refs(g, ids, here):
    """Links for the reference ids an approved field_evidence entry names."""
    by = {r['id']: r for r in g['references']}
    out = []
    for rid in ids:
        r = by.get(rid)
        if r:
            out.append('<a href="%s" rel="noopener">%s</a>' % (esc(r['url']), esc(r['label'] or r['url'])))
    return (' <span class="t-small goal-src">Source: %s</span>' % ', '.join(out)) if out else ''


def _fdate(iso, style='short'):
    try:
        return core.fdate(date.fromisoformat(iso), style)
    except (TypeError, ValueError):
        return ''


def goal_sections(t, here, site):
    """Why · Planning notes · Season and commitment · Route source · References · Still to check · Outings (a completed
    goal leads with its outings). Each only when it has content; nothing is invented to fill a slot."""
    g = t['goal']
    by = site.get('by_slug') or {}
    secs = []

    def sec(id_, title, inner, cls=''):
        secs.append('<section class="goal-sec%s" id="%s" aria-labelledby="%s-h"><h2 class="t-h3 rep-h" id="%s-h">%s</h2>%s</section>'
                    % ((' ' + cls) if cls else '', id_, id_, id_, esc(title), inner))

    def outings():
        if not g['outings']:
            return
        items = []
        for o in g['outings']:
            lab = {'completed': 'Completed', 'attempted': 'Attempted', 'reopened': 'Reopened'}[o['outcome']]
            when = _fdate(o['date'], 'long') if o['date'] else 'date not recorded'
            rep = by.get(o['report_slug']) if o['report_slug'] else None
            bits = ['<span class="tag">%s</span>' % lab, '<span class="t-mono-s">%s</span>' % esc(when.upper())]
            if rep:
                bits.append('<a class="goal-rep" href="%s">%s</a>' % (link(here, rep['url']), core.title_html(rep['title'])))
            elif o['report_slug']:
                bits.append('<span class="t-small">report %s</span>' % esc(o['report_slug']))
            items.append('<li><div class="goal-out">%s</div>%s</li>' % (' '.join(bits), ('<p class="t-excerpt">%s</p>' % esc(o['note'])) if o['note'] else ''))
        sec('outings', 'Outings', '<ul class="goal-outs">%s</ul>' % ''.join(items))
    if g['status'] == 'completed':
        outings()
    if g['why']:
        sec('why', 'Why', '<p class="t-body goal-why">%s</p>' % esc(g['why']))
    if t['body_md']:
        sec('report', 'Planning notes', '<div class="prose t-body">%s</div>' % markdown.to_html(t['body_md']))
    rows = []
    if g['time_commitment']:
        rows.append('<div><dt>Time</dt><dd>%s</dd></div>' % esc(goals.COMMITMENT_LABELS[g['time_commitment']]))
    if g['difficulty']:
        d = g['difficulty']
        rows.append('<div><dt>Difficulty</dt><dd>%s (%s)%s%s</dd></div>'
                    % (esc(d['value']), esc(d['system']), (' – ' + esc(d['note'])) if d['note'] else '', _refs(g, g['field_evidence']['difficulty']['source_ids'], here)))
    if g['target_months'] or g['target_year']:
        from sitegen.pages.ticklist import MONTHS
        names = [lab for m, lab in MONTHS if m in g['target_months']]
        when = ', '.join(names) + ((' %d' % g['target_year']) if g['target_year'] else '')
        rows.append('<div><dt>My window</dt><dd>%s</dd></div>' % esc(when.strip()))
    season = ('<p class="t-excerpt goal-season">%s%s</p>' % (esc(g['season_notes']), _refs(g, g['field_evidence']['season_notes']['source_ids'], here))) if g['season_notes'] else ''
    if rows or season:
        sec('season', 'Season and commitment', ('<dl class="dl-leader">%s</dl>' % ''.join(rows) if rows else '') + season)
    src = g['route_source']
    bits = []
    if t['track'] or src['kind'] != 'unknown' or src['label'] or src['url']:
        what = goals.SOURCE_LABELS[src['kind']]
        line = 'The line is %s, %s.' % (what, goals.SCOPE_LABELS[g['route_scope']])
        if src['label'] or src['url']:
            ref = ('<a href="%s" rel="noopener">%s</a>' % (esc(src['url']), esc(src['label'] or src['url']))) if src['url'] else esc(src['label'])
            line += ' From %s%s.' % (ref, (', checked %s' % _fdate(src['checked_at'])) if src['checked_at'] else '')
        # nothing known at all (a route saved before the tick list): the sentence below says so once, in plain words
        nothing_known = (not g.get('route') and src['kind'] == 'unknown' and g['route_scope'] == 'unknown'
                         and not (src['label'] or src['url']))
        if not nothing_known:
            bits.append('<p>%s</p>' % line)
        if src['approximation_note']:
            bits.append('<p class="t-small">%s</p>' % esc(src['approximation_note']))
        if t['track'] and g.get('route'):
            bits.append('<p class="t-small">The GPX published here is that source, kept byte for byte; the numbers above are measured from it and are approximate. It is a plan, not a recording of a trip.</p>')
        elif t['track']:
            # a planned route saved before the tick list recorded sources: no checksum or method exists, so none is claimed
            bits.append('<p class="t-small">The GPX published here was saved before the tick list recorded where a route came from, so its source and how it was made are not recorded. It is a plan, not a recording of a trip.</p>')
        else:
            bits.append('<p class="t-small">No GPX is published for this goal.</p>')
        sec('source', 'Route source', ''.join(bits))
    if g['references']:
        items = ''.join('<li><a href="%s" rel="noopener">%s</a>%s%s</li>'
                        % (esc(r['url']), esc(r['label'] or r['url']), (' <span class="t-mono-s">CHECKED %s</span>' % esc(_fdate(r['checked_at']).upper())) if r['checked_at'] else '',
                           ('<p class="t-small">%s</p>' % esc(r['note'])) if r['note'] else '') for r in g['references'])
        sec('references', 'References', '<ul class="goal-refs">%s</ul>' % items)
    if g['checklist']:
        items = ''.join('<li class="%s"><span class="goal-mark" aria-hidden="true">%s</span><span class="sr">%s: </span>%s</li>'
                        % ('is-done' if c['done'] else '', '✓' if c['done'] else '○', 'Done' if c['done'] else 'To check', esc(c['text'])) for c in g['checklist'])
        sec('checklist', 'Still to check', '<ul class="goal-check">%s</ul>', )
        secs[-1] = secs[-1].replace('<ul class="goal-check">%s</ul>', '<ul class="goal-check">%s</ul>' % items)
    if g['status'] != 'completed':
        outings()
    if not secs:
        return ''
    return '<div class="wrap sec goal-body">%s</div>' % ''.join(secs)


def goal_page(t, site):
    here = t['url']
    meta = core.render_meta(t)
    has_notes = bool(t['body_md'])
    actions = ''
    if has_notes:
        actions += '<a class="btn" href="#report">%sPlanning notes</a>' % icon('report', 18)
    if t['track']:
        actions += '<a class="btn btn--ink" href="%s" download>%sDownload planned GPX</a>' % (t['slug'] + '.gpx', icon('download', 18))
    actions += core.copy_link(core.SITE_URL + here)
    strip_ = goal_strip(t)
    body = [title_block(t, here, actions, strip_follows=bool(strip_)), strip_, goal_map_section(t, here, meta),
            goal_sections(t, here, site), share_row(here), goal_pager(t, here)]
    desc = core.clip_words(core.summary(t) + ((' ' + t['goal']['why']) if t['goal']['why'] else ''), 155)
    head = core.map_preloads(t, here, [('map-wide', 'wide'), ('map-col', 'col'), ('map-phone', 'phone')], t['url'] + 'map/',
                             nowide='map-wide' not in meta['maps']) if meta['maps'] else ''
    return core.Page(here, core.document(here, t['title'], ''.join(body), desc, active='goal', image=core.share_photo(t),
                                         body_cls='p-report p-goal',
                                         bottom=goal_bottom_bar(t, has_notes), extra_head=head, trip=t), t['title'])


def tick_backlink(t, here, site):
    """'On the tick list: <goal>' under a report's title block, for every goal whose outing names this report."""
    gs = (site.get('goal_backlinks') or {}).get(t['slug'])
    if not gs:
        return ''
    links = ', '.join('<a href="%s">%s</a>' % (link(here, g['url']), core.title_html(g['title'])) for g in gs)
    return '<p class="wrap t-small rep-tick">%sOn the tick list: %s</p>' % (icon('checkbox', 16), links)


def page(t, site):
    if t['kind'] == 'planned':
        return goal_page(t, site)
    here = t['url']
    meta = core.render_meta(t)
    # no track.gpx, no download: the title action and the phone bar's GPX item are only there when the file is
    gpx_href = (t['slug'] + '.gpx') if t['track'] else ''
    has_report = bool(t['body_md'])
    story = narrative(t)
    written = written_first(t)
    lone = lone_portrait(t)
    # the cover leads a story, and a photo-only report too (Phase 10, report-02), when it is a landscape (lead_photo)
    show_hero = (story or (not has_report and has_photos(t))) and not lone and lead_photo(t) is not None
    cover_file = t['cover']['photo']['file'] if show_hero else None
    # the lead photo leaves the grid (it is already on the page) but stays in the viewer's group
    photos = [p for p in t['photos'] if p.get('file') and p['file'] != cover_file]
    has_gallery = bool(photos) and not lone
    # no track.gpx, no route: no map section, no link to one, no full-screen map page (build() below)
    has_map = bool(t['track'])
    actions = ''
    if story or written:
        if has_map:
            # the write-up starts right under the photo and the strip; the route is further down, so its link leads
            actions += '<a class="btn" href="#map">%sView route</a>' % icon('map', 18)
    elif has_report:
        actions += '<a class="btn" href="#report">%sRead the report</a>' % icon('report', 18)
    if gpx_href:
        actions += '<a class="btn btn--ink" href="%s" download>%sDownload GPX</a>' % (gpx_href, icon('download', 18))
    actions += core.copy_link(core.SITE_URL + here)
    body = [title_block(t, here, actions), tick_backlink(t, here, site)]
    # a recorded report has stats (tools/add_trip.py writes them from the track). One without a track may have none:
    # then there is no strip, rather than an empty list under a "Stats" label with links leading to it
    cells = core.strip_cells(t)
    has_stats = bool(cells) or has_map
    beta = beta_list(t, noted=has_stats)
    strip_ = ('<section class="wrap rep-strip" id="stats" aria-label="Stats">%s%s</section>' % (core.strip(cells), core.stats_note(t, here=here))) if has_stats else ''
    variants = [('map-wide', 'wide'), ('map-col', 'col'), ('map-phone', 'phone')]
    nowide = 'map-wide' not in meta['maps']
    # a track whose maps render.py has not drawn yet (--no-render, no internet): the section says so instead of holding
    # an empty map with a key and a caption for it; the GPX download and the links to #map stay
    drawn = has_map and bool(meta['maps'])
    map_ = ''
    if drawn:
        map_ = ('<section class="rep-map" id="map" aria-label="Route map"><div class="bleed">%s</div><div class="wrap">%s%s</div></section>'
                % (core.map_block(t, here, variants, t['url'] + 'map/', 'm', eager=not show_hero, cls='map--report' + (' map--nowide' if nowide else ''),
                                  fullscreen_href=link(here, t['url'] + 'map/')),
                   core.key_rows(key_items(t, meta), key_items(t, meta, phone=True)), map_caption(t)))
    elif has_map:
        map_ = not_rendered_section('Route map', 'Map not rendered yet. The GPX file is published: use the Download GPX button.')
    profile = profile_section(t, here, meta)
    main = ''
    if has_report:
        main = ('<div class="rep-main" id="report"><h2 class="t-h3 rep-h" id="report-h">%s</h2><div class="prose t-body">%s</div></div>'
                % (LABELS['#report'], markdown.to_html(t['body_md'])))
    aside = aside_photo(t, here, lone) if lone else ''
    # the rail holds the Beta block only: its old Contents list needed a write-up and a Photos section on one compact
    # page, and a report with both is a story, whose section row (section_nav) does that job
    rep_body = ''
    if beta or main or aside:
        rep_body = ('<div class="rep-body wrap sec%s"><aside class="rep-rail">%s</aside>%s%s</div>'
                    % (' rep-body--ph' if aside else '', beta, main or '<div class="rep-main"></div>', aside))
    if show_hero:
        body.append(hero(t, here, photos_anchor=not has_gallery))
    if story or written:
        body += [strip_, section_nav(has_report, has_gallery, has_map, has_chart(meta)), rep_body, map_, profile]
    else:
        body += [strip_, map_, profile, rep_body]
    if has_gallery:
        body.append(gallery(t, here, photos, lead=1 if show_hero else 0))
    body.append(published_line(t))
    body.append(share_row(here))
    body.append(core.related_block(t, here, site, skip=neighbours(t, site)))
    body.append(pager(t, here, site))
    # a title shared by several reports ('Morning Ride') gets its date in the <title> / og:title (the H1 stays
    # verbatim) and a description that leads with the factual summary, as does a report with little or no write-up
    dup = t['date'] and title_counts(site).get(t['title'].casefold(), 0) > 1
    full_title = ('%s, %s · %s' % (t['title'], core.fdate(t['date'], 'short'), core.SITE_NAME)) if dup else None
    # 'little': under 100 characters of writing in all (excerpt() cuts at a sentence end, so its 155-character excerpt
    # can be shorter than that while the write-up is not; its 400-character one is whole below 400)
    desc, ex = core.excerpt(t, 155), core.excerpt(t, 400)
    if dup or len(ex) < 100:
        desc = core.clip_words(core.summary(t) + ((' ' + ex) if ex else ''), 155)
    # the share image is the cover the trip's cards show, whether or not it leads the page (a portrait cover does not)
    img = core.share_photo(t)
    if show_hero:
        head = core.cover_preload(t, here, HERO_SIZES)
    else:
        head = core.map_preloads(t, here, variants, t['url'] + 'map/', nowide=nowide)
    return core.Page(here, core.document(here, t['title'], ''.join(body), desc, active=t['activity'], image=img,
                                         body_cls='p-report' + (' p-report--story' if story else (' p-report--written' if written else '')),
                                         bottom=bottom_bar(t, here, gpx_href, bool(beta), has_report, has_gallery, has_chart(meta), story=story or written,
                                                           has_map=has_map, has_stats=has_stats),
                                         extra_head=head, og_type='article', trip=t, full_title=full_title, report=t), t['title'])


_TITLE_COUNTS = {}


def title_counts(site):
    """How many published reports carry each title (casefolded), counted once per build."""
    key = id(site['published'])
    if key not in _TITLE_COUNTS:
        c = {}
        for x in site['published']:
            c[x['title'].casefold()] = c.get(x['title'].casefold(), 0) + 1
        _TITLE_COUNTS.clear()
        _TITLE_COUNTS[key] = c
    return _TITLE_COUNTS[key]


def fullscreen_page(t, variants=None, key_html=None, cls=None, caption=None, post=None):
    """trips/<slug>/map/: a report's map at full size for phones (pan + pinch zoom), linked from the phone map's button.
    Defaults fit a single-day or planned report; multi-day and series pages pass their own render (variants
    [(name, 'fs')]), desktop key row, map class (e.g. 'map--fs map--fstall') and caption. post: an optional filter for
    the map HTML (multiday.slim clips off-frame features)."""
    here = t['url'] + 'map/'
    meta = core.render_meta(t)
    if variants is None:
        name = 'map-wide' if 'map-wide' in meta['maps'] else 'map-col'
        variants = [(name, 'fs')]
        cls = 'map--fs' + ('' if name == 'map-wide' else ' map--fscol')
    mp = core.map_block(t, here, variants, t['url'] + 'map/', 'fs', attrib=False, cls=cls or 'map--fs')
    if post:
        mp = post(mp)
    body = ('<h1 class="sr">%s: map</h1><div class="wrap fs-bar"><a class="btn" href="../#map">%sBack to report</a>'
            '<span class="t-small fs-pan">Drag to pan</span></div>'
            '<div class="fs-map" tabindex="0" role="region" aria-label="Map, scroll to pan">%s</div><div class="wrap fs-foot">%s%s</div>'
            % (esc(t['title']), icon('arrow-left', 18), mp,
               key_html if key_html is not None else core.key_row(key_items(t, meta)),
               caption if caption is not None else map_caption(t)))
    desc = 'Full-size route map for %s.' % t['title']
    return core.Page(here, core.document(here, t['title'] + ' map', body, desc, active=t['activity'], body_cls='p-fsmap',
                                         extra_head='<meta name="robots" content="noindex">'), t['title'] + ' map', index=False)


def build(site):
    out = []
    for t in site['trips']:
        if not t['days'] and t['kind'] in ('trip', 'planned'):
            out.append(page(t, site))
            # a goal or a report without a rendered map (a report without a track has none) has no full-screen map page
            if core.render_meta(t)['maps'] and (t['kind'] == 'planned' or t['track']):
                out.append(fullscreen_page(t))
    return out
