"""Region pages — /regions/<slug>/: one page for every region that has a region map.

A region gets a region map once it has three trips with a track (tools/render.py draws it; rendered/site/meta.json lists
it), and every such region with at least one published report gets a page here (core.region_pages). The page lists what
the content files say: every report and active tick-list goal whose `region` is the region's name, whether or not the
map was drawn with it. The Map page stays the parent and keeps every #region-<slug> anchor; a region without a map has
no page and keeps its list on the Map page.

Anatomy: breadcrumb (Reports / Map / region), H1, a Mono-S line of counts and years with the places on a second line
(counts and names from front matter; Eric's own introduction under it only when content/regions/<slug>.md has
words), the Map page's panel for the region (map,
legend and the region's rows beside it), a Featured row of up to three cards, every report by year with the Map
page's activity filter, and links to the other region pages. archive.js drives the list and the filter (body.p-region).
"""
import content
import markdown

from sitegen import core
from sitegen.core import esc, link, icon
from sitegen.pages import archive, section

FEATURED_MAX = 3   # cards in the Featured row
MAX_PLACES = 3     # places named on the head's second line before 'N MORE' (one more is named rather than '1 MORE')


def url(name):
    return 'regions/%s/' % content.slugify(name)


def regions(site, meta=None):
    """[(name, slug, ts)] for the regions that get a page (core.region_pages): most published reports first, then A–Z.
    ts is every report filed under the region, newest first, then its active tick-list goals. meta None: the site
    meta on disk."""
    return core.region_pages(site, archive.site_meta() if meta is None else meta)


# ---------------------------------------------------------------- head

def years_item(pub):
    """'2022–2026', or '2026' when the reports share a year; '' when none is dated."""
    years = sorted({t['date'].year for t in pub if t['date']} | {t['end_date'].year for t in pub if t.get('end_date')})
    if not years:
        return ''
    return str(years[0]) if years[0] == years[-1] else '%d–%d' % (years[0], years[-1])


def place_names(pub):
    """The distinct places of the reports as the head shows them (upper case), most reports first, then A–Z. Two
    spellings that read the same in upper case are one place."""
    k = {}
    for t in pub:
        v = (t.get('place') or '').strip().upper()
        if v:
            k[v] = k.get(v, 0) + 1
    return sorted(k, key=lambda v: (-k[v], v))


def place_items(pub):
    """The second line of the head: every place when there are at most MAX_PLACES + 1, else the biggest MAX_PLACES and
    'N MORE' (the rule of the section pages' totals line). A place is free text, so its item may wrap at its spaces
    when it alone is wider than the line (.mi-w), as a card's place does; the page never scrolls sideways for it."""
    names = place_names(pub)
    if len(names) <= MAX_PLACES + 1:
        return [(esc(x), 'mi-w') for x in names]
    return [(esc(x), 'mi-w') for x in names[:MAX_PLACES]] + [core.nb('%d MORE' % (len(names) - MAX_PLACES))]


def activity_items(slug, here, pub):
    """The region's activities with their counts, each linking to the explorer narrowed to them
    (trips/?region=<slug>&activity=<key>, which trips.js reads; ia-10): 'BACKCOUNTRY SKIING 37', in the menu's order, an
    activity without a report left out. Without JavaScript the explorer shows its full list, as the page's other two
    links to it accept."""
    out = []
    for a, lab in core.NAV:
        k = sum(1 for t in pub if t['activity'] == a)
        if k:
            out.append('<a class="reg-act" href="%s?region=%s&amp;activity=%s">%s<span>%s</span><span class="reg-act-n"><span class="sr">: </span>%d</span><span class="sr"> %s</span></a>'
                       % (link(here, 'trips/'), slug, a, core.disc(a, 16), core.nb(esc(lab).upper()), k, 'report' if k == 1 else 'reports'))
    return out


def crumb_items(name, here):
    """The region page's crumbs, Reports / Map / <region> (the page itself), for the nav and its BreadcrumbList."""
    return [('Reports', link(here, '')), ('Map', link(here, 'map/')), (name, None)]


def head(name, here, pub, planned, intro=None, slug=None):
    """The H1, the counts line, the activities line and, when content/regions/<slug>.md has words, those words verbatim
    under them."""
    first = core.count_items(pub, planned) + [x for x in [years_item(pub)] if x]
    words = ('<div class="prose t-body reg-intro">%s</div>' % markdown.to_html(intro['body_md'], heading_shift=1)
             if intro and intro.get('body_md') else '')
    crumbs = core.crumbs(here, crumb_items(name, here))[0]
    return ('<section class="reg-head wrap" aria-labelledby="reg-title">'
            '<nav class="crumbs t-mono-s" aria-label="Breadcrumb">%s</nav>'
            '<h1 id="reg-title" class="t-d1">%s</h1>'
            '<p class="reg-stats">%s</p>%s%s</section>'
            % (crumbs, esc(name), core.meta_items(first + place_items(pub), br_after=len(first) - 1),
               # .reg-x: like the page's other links into the explorer, hidden when scripting is off (region.css)
               ('<p class="t-mono-s reg-acts reg-x">%s</p>' % core.meta_items(activity_items(slug, here, pub))) if slug else '', words))


# ---------------------------------------------------------------- featured

def pick_featured(ts):
    """Up to FEATURED_MAX reports for the Featured row: the ones marked `featured: true` in front matter (the flag behind
    the section pages' Featured block), then written reports with a cover photo, then written reports without one;
    newest first inside each (the order of ts). A report with no write-up and no flag is never one of them, so a region
    of bare tracks has no Featured row. A planned route is never one; a journal filed under the region can be."""
    def tier(t):
        if t.get('featured'):
            return 0
        if core.written_report(t):
            return 1 if t.get('cover') else 2
        return None
    cands = [(tier(t), i, t) for i, t in enumerate(ts) if t['kind'] != 'planned' and tier(t) is not None]
    return [t for _tier, _i, t in sorted(cands, key=lambda c: c[:2])[:FEATURED_MAX]]


def featured(slug, here, pub, feat):
    if not feat:
        return ''
    # a title the region's list repeats (the page lists every report of the region) names its date in the card's link
    repeated = core.repeated_titles(pub)
    cards = ''.join(core.trip_card(t, here, core.RELATED_SIZES, ns='rf', summary=True, repeated=repeated) for t in feat)
    k = sum(1 for t in pub if t['has_writeup'])
    more = ''
    if k > 1:
        # the explorer applies the filters with JavaScript: the link is hidden when scripting is off (region.css, .reg-x)
        more = ('<p class="reg-more reg-x"><a class="alink" href="%s?region=%s&amp;writeup=1">All %d write-ups in Trips%s</a></p>'
                % (link(here, 'trips/'), slug, k, icon('arrow-right', 16)))
    return ('<section class="reg-feat wrap sec" aria-labelledby="reg-feat-h">%s<ul class="reg-cards tgrid">%s</ul>%s</section>'
            % (core.section_head('Featured', id_='reg-feat-h'), cards, more))


# ---------------------------------------------------------------- other regions

def others(slug, here, regs):
    rest = [(n_, s, ts) for n_, s, ts in regs if s != slug]
    if not rest:
        return ''
    items = ''.join('<li><a href="%s">%s<span class="trx-bn">%s</span></a></li>'
                    % (link(here, 'regions/%s/' % s), esc(n_), archive.count_n(sum(1 for t in ts if t['kind'] != 'planned')))
                    for n_, s, ts in rest)
    items += '<li><a href="%s">Map</a></li>' % link(here, 'map/')
    return ('<nav class="reg-others wrap sec" aria-labelledby="reg-others-l"><div class="trx-browse"><div class="trx-bgroup">'
            '<span class="t-label" id="reg-others-l">Other regions</span><ul>%s</ul></div></div></nav>' % items)


# ---------------------------------------------------------------- page

def activity_words(pub):
    """What the reports are, lower case, in the menu's order: 'backcountry skiing', 'hiking', ...; for Other the sub-types
    its reports have, each as its own word ('paddleboarding', 'rafting'), or 'other' when none names one."""
    out = []
    for a, _lab in core.NAV:
        ts = [t for t in pub if t['activity'] == a]
        if not ts:
            continue
        if a == 'other':
            subs = []
            for t in ts:
                w = core.SUB_WORD.get(t.get('subtype') or '', t.get('subtype') or '').lower()
                if w and w not in subs:
                    subs.append(w)
            out += subs or [core.ACT[a][0].lower()]
        else:
            out.append(core.ACT[a][0].lower())
    return out


def description(name, pub):
    """One factual sentence: the region, how many reports, over which years, of which activities, and that the page has
    a map of the region; the GPX clause only when every report has a track (core.has_track, as on the section pages).
    The region leads, so no preposition has to suit its name: 'Tetons: 4 trip reports, 2026 (backcountry skiing), with a
    map of the region and the full GPX track of each.' The map is not said to show every report: it shows what it was
    last drawn with."""
    acts = activity_words(pub)
    years = sorted({t['date'].year for t in pub if t['date']} | {t['end_date'].year for t in pub if t.get('end_date')})
    when = '' if not years else (', %d' % years[0] if years[0] == years[-1] else ', %d to %d' % (years[0], years[-1]))
    tracked = bool(pub) and all(core.has_track(t) for t in pub)
    gpx = '' if not tracked else (' and its full GPX track' if len(pub) == 1 else ' and the full GPX track of each')
    return ('%s: %s%s%s, with a map of the region%s.'
            % (name, '1 trip report' if len(pub) == 1 else '%d trip reports' % len(pub), when,
               (' (%s)' % section.words_list(acts, 'and')) if acts else '', gpx))


def share_image(feat, pub):
    """The cover of the first Featured card that has one, else of the newest report with one, else the site's."""
    t = next((x for x in list(feat) + list(pub) if x.get('cover')), None)
    return core.share_photo(t) if t else core.site_share()


def map_trips(name, site, meta):
    """The trips the region's map draws (the Map page's group for the region, core.region_groups): what the legend
    beside the map describes. [] when the map names none of the site's trips."""
    return next((ts for n_, _slug, ts in core.region_groups(site, meta) if n_ == name), [])


def page(name, slug, ts, site, meta, regs):
    here = 'regions/%s/' % slug
    pub = [t for t in ts if t['kind'] != 'planned']
    planned = [t for t in ts if t['kind'] == 'planned']
    feat = pick_featured(ts)
    find = ('<p class="reg-find reg-x wrap"><a class="alink" href="%s?region=%s">Search and filter these in Trips%s</a></p>'
            % (link(here, 'trips/'), slug, icon('arrow-right', 16)))
    body = (head(name, here, pub, planned, (site.get('region_intros') or {}).get(slug), slug)
            + '<section class="arc-map reg-map wrap" aria-labelledby="reg-map-h"><h2 class="sr" id="reg-map-h">Map</h2>%s</section>'
            % archive.region_panel(name, slug, ts, here, meta, True, page=True, drawn=map_trips(name, site, meta) or None, site=site)
            + featured(slug, here, pub, feat)
            + archive.archive_section(site, here, published=pub, active=planned)
            + find
            + others(slug, here, regs))
    title = '%s trip reports' % name
    preload = core.map_preloads(None, here, [('region-%s-desktop' % slug, 'desktop'), ('region-%s-phone' % slug, 'phone')],
                                'assets/maps/', site_maps=True)
    return core.Page(here, core.document(here, title, body, description(name, pub), active='map', body_cls='p-region',
                                         image=share_image(feat, pub), extra_head=preload, page_bar=(name, 'reg-title'),
                                         ld=[core.crumbs(here, crumb_items(name, here))[1]]), title)


def build(site):
    meta = archive.site_meta()
    regs = regions(site, meta)
    return [page(name, slug, ts, site, meta, regs) for name, slug, ts in regs]
