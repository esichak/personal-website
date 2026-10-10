"""Trips explorer — /trips/ (index.html) and trips/search.json.

Every published report as one card (core.trip_card), grouped by year, with text search over a build-time index and
combined filters (activity, region, year, format, has a write-up) in assets/js/pages/trips.js. Everything a visitor
needs without JavaScript is server-rendered: the full list, the year anchors and a browse block linking the activity
pages and the map's region panels; the search form is hidden until the script reveals it. Planned routes are not
reports: they stay on the map and their activity page until the Tick list (Phase 2T) gives them a home.
"""
from sitegen import core, search
from sitegen.core import esc, link, icon

import content

HERE = 'trips/'
TRX_SIZES = '(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2), 112px'
FORMATS = [('trip', 'Single-day'), ('multi-day', 'Multi-day'), ('series', 'Series')]
SORTS = [('newest', 'Newest first'), ('oldest', 'Oldest first'), ('relevance', 'Best match')]
VIEWS = [('cards', 'Cards', 'photo'), ('list', 'List', 'list')]


# ---------------------------------------------------------------- data

def plural(k, word, pl=None):
    return '%d %s' % (k, word if k == 1 else (pl or word + 'S'))


def count_n(k):
    """A chip / link count that reads as 'Lake Tahoe, 14 reports' (the visible part is just the number)."""
    return '<span class="sr">, </span>%d<span class="sr"> %s</span>' % (k, 'report' if k == 1 else 'reports')


def regions_of(pub):
    """[(name, slug, count)] most reports first, then A–Z. Keyed by the map-anchor slug, so two spellings of one region
    ('Lake Tahoe', 'Lake tahoe') count as one entry labelled with the first spelling seen."""
    k, label = {}, {}
    for t in pub:
        r = (t.get('region') or '').strip()
        if r:
            s = content.slugify(r)
            k[s] = k.get(s, 0) + 1
            label.setdefault(s, r)
    return [(label[s], s, k[s]) for s in sorted(k, key=lambda s: (-k[s], label[s]))]


def years_of(pub):
    """Years with a report, newest first (a trip's start year)."""
    return sorted({t['date'].year for t in pub if t['date']}, reverse=True)


def groups_of(pub):
    """[(year or None, trips)] newest first, undated trips last (site['published'] is already newest first)."""
    groups = []
    for t in pub:
        y = t['date'].year if t['date'] else None
        if not groups or groups[-1][0] != y:
            groups.append((y, []))
        groups[-1][1].append(t)
    groups.sort(key=lambda g: g[0] is None)  # stable: undated last
    return groups


# ---------------------------------------------------------------- page parts

def head(site):
    pub = site['published']
    bits = [x for x in core.count_items(pub) if not x.startswith('INCL.')]
    regs = regions_of(pub)
    if regs:
        bits.append(core.nb(plural(len(regs), 'REGION')))
    years = years_of(pub)
    if years:
        bits.append(str(years[0]) if len(years) == 1 else '%d–%d' % (years[-1], years[0]))
    return ('<section class="trx-head wrap" aria-labelledby="trips-title"><h1 id="trips-title" class="t-d1">Trips</h1>'
            '<p class="t-mono-s trx-stats">%s</p></section>' % core.meta_items(bits))


def browse(site):
    """Static links that work without JavaScript: activity pages, the map's region panels, the year groups below."""
    pub = site['published']
    acts = []
    for a, lab in core.NAV:
        k = sum(1 for t in pub if t['activity'] == a)
        if k:
            acts.append('<li><a href="%s">%s<span class="trx-bn">%s</span></a></li>' % (link(HERE, core.section_url(a)), esc(lab), count_n(k)))
    regs = []
    for name, slug, k in regions_of(pub):
        # a region with no panel or anchor on map/ (the PCT) links to this page's own filter instead
        href = core.region_map_href(HERE, name) or ('?region=%s' % slug)
        regs.append('<li><a href="%s">%s<span class="trx-bn">%s</span></a></li>' % (href, esc(name), count_n(k)))
    years = ''.join('<li><a href="#y-%d">%d</a></li>' % (y, y) for y in years_of(pub))
    group = lambda lab, items: ('<div class="trx-bgroup"><span class="t-label">%s</span><ul>%s</ul></div>' % (lab, items)) if items else ''  # noqa: E731
    return ('<nav class="trx-browse wrap" aria-label="Browse">%s%s%s</nav>'
            % (group('By activity', ''.join(acts)), group('By region', ''.join(regs)), group('By year', years)))


def select(name, label, options, blank):
    """<label>Label <select name></select></label>: blank is the 'all' option's text (value '')."""
    opts = '<option value="">%s</option>' % esc(blank) + ''.join('<option value="%s">%s</option>' % (esc(v), esc(lab)) for v, lab in options)
    return '<label class="trx-sel"><span>%s</span><select name="%s">%s</select></label>' % (esc(label), name, opts)


def controls(site):
    """The search form, hidden until trips.js reveals it (without the script it could not do anything)."""
    pub = site['published']
    chips = ['<button type="button" class="fchip" role="radio" data-filter="all" aria-checked="true" tabindex="0">'
             '<span class="fchip-l">All</span></button>']
    for a, lab in core.NAV:
        k = sum(1 for t in pub if t['activity'] == a)
        if not k:
            continue
        chips.append('<button type="button" class="fchip" role="radio" data-filter="%s" aria-checked="false" tabindex="-1">'
                     '<span class="chip-sw" style="background:%s" aria-hidden="true"></span><span class="fchip-l">%s</span>'
                     '<span class="fchip-n">%s</span></button>' % (a, core.ACT[a][3], esc(lab), count_n(k)))
    kinds = {t['kind'] for t in pub}
    formats = [(v, lab) for v, lab in FORMATS if v in kinds]
    sort = '<label class="trx-sel"><span>Sort</span><select name="sort">%s</select></label>' % ''.join(
        '<option value="%s">%s</option>' % (v, lab) for v, lab in SORTS)
    views = ''.join('<button type="button" role="radio" data-view="%s" aria-checked="%s" tabindex="%s">%s%s</button>'
                    % (v, 'true' if i == 0 else 'false', '0' if i == 0 else '-1', icon(ic, 16), lab) for i, (v, lab, ic) in enumerate(VIEWS))
    return ('<form class="trx-form wrap" role="search" id="search" action="" hidden>'
            '<label class="sr" for="trx-q">Search trips</label>'
            '<input class="trx-q" type="search" id="trx-q" name="q" placeholder="Search by name, place, region, activity or peak" autocomplete="off" maxlength="200">'
            '<div class="trx-filters">'
            '<div class="trx-acts" role="radiogroup" aria-label="Activity">%s</div>'
            '%s%s%s'
            '<label class="trx-check"><input type="checkbox" name="writeup" value="1"> Has a write-up</label>'
            '%s'
            '<div class="trx-view" role="radiogroup" aria-label="View">%s</div>'
            '</div></form>'
            '<noscript><p class="note wrap trx-noscript">Search and filters need JavaScript. Every report is listed below by year, '
            'and the links above group them by activity and region.</p></noscript>'
            % (''.join(chips),
               select('region', 'Region', [(slug, name) for name, slug, _k in regions_of(pub)], 'All regions'),
               select('year', 'Year', [(str(y), str(y)) for y in years_of(pub)], 'All years'),
               select('format', 'Format', formats, 'Any format'),
               sort, views))


def status(site):
    n = len(site['published'])
    return ('<div class="trx-status wrap">'
            '<p class="t-mono-s trx-count" id="trx-count" aria-live="polite">%s</p>'
            '<ul class="trx-chips" id="trx-chips" aria-label="Active filters"></ul>'
            '<button type="button" class="alink" id="trx-clear" hidden>Clear all%s</button></div>'
            '<p class="note wrap" id="trx-msg" role="status" hidden></p>'
            '<div class="wrap"><div class="empty" id="trx-none" hidden><p>No trips match these filters.</p>'
            '<button type="button" class="btn" data-clear>Clear filters</button></div></div>'
            % (plural(n, 'REPORT'), icon('close', 16)))


def results(site):
    out = []
    for y, ts in groups_of(site['published']):
        yid = 'y-%d' % y if y is not None else 'y-undated'
        label = str(y) if y is not None else 'Undated'
        cards = ''.join(core.trip_card(t, HERE, TRX_SIZES, ns='tc', summary=True) for t in ts)
        out.append('<section class="trx-yr" data-year="%s"><div class="trx-yr-h"><h2 class="t-label" id="%s">%s</h2>'
                   '<span class="t-mono-s trx-yr-n">%s</span></div><ul class="trx-grid tgrid">%s</ul></section>'
                   % (y if y is not None else '', yid, label, plural(len(ts), 'REPORT'), cards))
    # oldest / best-match order: trips.js moves the visible cards into this section (its heading names the order) and hides the years
    return ('<div class="trx-results wrap" id="trx-results">%s<section class="trx-yr" id="trx-sorted-sec" hidden>'
            '<div class="trx-yr-h"><h2 class="t-label" id="trx-sorted-h">Results</h2></div><ul class="trx-grid tgrid" id="trx-sorted"></ul></section></div>'
            % ''.join(out))


def build(site):
    body = head(site) + browse(site) + controls(site) + status(site) + results(site)
    desc = 'Every trip report, searchable by name, place, region, activity, named peak and write-up, with filters by activity, year and format.'
    page = core.Page(HERE, core.document(HERE, 'Trips', body, desc, active='trips', body_cls='p-trips'), 'Trips')
    index = core.Page('trips/search.json', search.dumps(search.build_index(site)), 'Search index', index=False)
    return [page, index]
