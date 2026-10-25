"""About page — /about/. Who runs the site, what it is, how the maps and stats are made, live counts, RSS.

Everything shown is either a confirmed fact (name, Lake Tahoe, AIARE 2), a description of how the site is built,
or a number computed from the published trips. No bio, portrait or email until Eric writes them: content/about.md,
when it exists, puts his words in place of the computed lede and its photo above them (content.load_about).
"""
import markdown
from sitegen import core
from sitegen.core import esc, U, U_sub, n, link, icon, FT

URL = 'about/'


# ---------------------------------------------------------------- numbers from the content

def activity_counts(site):
    """[(act, published reports, distance_km, sub-type words)] in nav order. Only Other has sub-types: the ones with
    reports, most reports first (core.other_subtypes), the same words and order as the menu's Other row."""
    other = [core.SUB_WORD.get(s, s) for s in core.other_subtypes(site['published'])]
    out = []
    for act, _ in core.NAV:
        xs = [t for t in site['published'] if t['activity'] == act]
        km = sum(t['stats'].get('distance_km') or 0 for t in xs)
        out.append((act, len(xs), km, other if act == 'other' else []))
    return out


def count_word(k, one='REPORT', many='REPORTS'):
    return '%d %s' % (k, one if k == 1 else many)


def act_rows(site, here, cls='', dist=True):
    """64px rows linking to the five sections: disc · name · Mono-S count (+ sub-types present) · distance · chevron.

    Shared with the 404 page (notfound.py), which uses it without distances."""
    rows = []
    for act, k, km, subs in activity_counts(site):
        name = core.ACT[act][0]
        # one .ml line (CSS draws the dots, so a wrapped line never starts or ends with one)
        meta = [core.nb(count_word(k) if k else 'NO REPORTS YET')] + [core.nb(esc(s).upper()) for s in subs]
        d = ''
        if dist and km:
            d = '<span class="abo-act-d t-data-m">%s</span>' % core.distance(km)
        rows.append('<li><a class="abo-act-a" href="%s">%s<span class="abo-act-w"><span class="abo-act-n">%s</span>'
                    '<span class="t-mono-s abo-act-m">%s</span></span>%s%s</a></li>'
                    % (link(here, core.section_url(act)), core.disc(act, 32), esc(name), core.meta_items(meta), d,
                       icon('chevron-right', 20, 'abo-act-c')))
    return '<ul class="abo-act%s">%s</ul>' % ((' ' + cls) if cls else '', ''.join(rows))


def year_stats(site):
    """[(year, reports, days out, distance_km, gain_m)], newest first, one per calendar year a published report starts
    in (the Trips page's year filter, trips/?year=YYYY, counts the same start year). Days out are distinct dates: a
    multi-day trip's and the journal's days count on their own dates (once each, however many reports share a date) and
    the trip itself not again; distance and gain are the trips' own totals (a trip with days has the sums of its days,
    content.load_trip), so nothing is counted twice. 0 where no trip of the year states the value."""
    years = {}
    for t in site['published']:
        if not t['date']:
            continue
        r = years.setdefault(t['date'].year, [0, set(), 0, 0])
        r[0] += 1
        r[1].update([d['date'] for d in t['days'] if d['date']] or [t['date']])
        r[2] += t['stats'].get('distance_km') or 0
        r[3] += t['stats'].get('gain_m') or 0
    return [(y, r[0], len(r[1]), r[2], r[3]) for y, r in sorted(years.items(), reverse=True)]


def year_rows(site, here):
    """By year: a 64px row per year (year_stats) in the act_rows markup: the year · REPORTS · DAYS OUT · gain, the
    distance on the right, linking to the Trips page filtered to that year. A total no trip states is left out."""
    rows = []
    for y, k, days, km, gain in year_stats(site):
        meta = [core.nb(count_word(k)), core.nb(count_word(days, 'DAY OUT', 'DAYS OUT'))]
        if gain:
            # core.nb on the words only: it would put its no-break spaces inside U's tags too
            meta.append(U(core.caps_unit(n(gain * FT), 'FT'), core.caps_unit(n(gain), 'M')) + core.nb(' GAIN'))
        d = ('<span class="abo-act-d t-data-m">%s</span>' % core.distance(km)) if km else ''
        rows.append('<li><a class="abo-act-a" href="%s"><span class="abo-act-w"><span class="abo-act-n">%d</span>'
                    '<span class="t-mono-s abo-act-m">%s</span></span>%s%s</a></li>'
                    % (link(here, 'trips/?year=%d' % y), y, core.meta_items(meta), d, icon('chevron-right', 20, 'abo-act-c')))
    return ('<ul class="abo-act abo-yr">%s</ul>' % ''.join(rows)) if rows else ''


def site_rows(site, here):
    """Trips and Tick list in the .abo-act markup the 404 page's Site rows use: icon · name · Mono-S line · chevron."""
    goals = len(site.get('active_goals', site['planned']))
    rows = [('trips/', 'search', 'Trips', 'SEARCH AND FILTER'), ('tick-list/', 'checkbox', 'Tick list', count_word(goals, 'GOAL', 'GOALS'))]
    return '<ul class="abo-act">%s</ul>' % ''.join(
        '<li><a class="abo-act-a" href="%s"><span class="abo-ic" aria-hidden="true">%s</span><span class="abo-act-w">'
        '<span class="abo-act-n">%s</span><span class="t-mono-s abo-act-m">%s</span></span>%s</a></li>'
        % (link(here, url), icon(ic, 20), name, sub, icon('chevron-right', 20, 'abo-act-c')) for url, ic, name, sub in rows)


# ---------------------------------------------------------------- blocks

# the portrait's column: the intro's width up to 360px (about.css), the phone's width less its gutters below 760px
PORTRAIT_SIZES = '(min-width: 760px) 360px, calc(100vw - 32px)'


def portrait(about, here):
    """content/about.md's photo, 4:5 (about.css crops it there, at its focal point), above the words."""
    p = about['photo']
    x, y = about['focal']
    img = core.photo({'url': URL}, p, here, sizes=PORTRAIT_SIZES, cls='abo-portrait', eager=True, caption=False)
    if (x, y) != (50.0, 50.0):
        img = img.replace('<img ', '<img style="object-position:%s%% %s%%" ' % (core._pct(x), core._pct(y)), 1)
    return img


def intro(site, here=URL):
    """Right column, top: lead + at-a-glance facts. With content/about.md: its photo, then its words verbatim in place
    of the computed lede."""
    pub = [t for t in site['published'] if t['date']]
    rows = [('Based in', 'Lake Tahoe'), ('Avalanche training', 'AIARE 2')]
    if pub:
        a, b = min(t['date'] for t in pub), max(t['date'] for t in pub)
        span = core.fdate(a, 'month') if (a.year, a.month) == (b.year, b.month) else '%s – %s' % (core.fdate(a, 'month'), core.fdate(b, 'month'))
        rows.append(('Trip dates', span))
    dl = ''.join('<div><dt>%s</dt><dd>%s</dd></div>' % (esc(k), esc(v)) for k, v in rows)
    about = site.get('about') or {}
    lead = ('<p class="abo-lead">Trip reports by Eric Sichak: backcountry skiing, climbing, hiking, mountain biking and other trips, '
            'each with the full GPX track and map.</p>')
    if about.get('body_md'):
        lead = '<div class="prose abo-words">%s</div>' % markdown.to_html(about['body_md'], heading_shift=1)
    return ('<div class="abo-intro">%s%s'
            '<section class="abo-sec abo-glance" aria-labelledby="abo-glance-h"><h2 class="t-h3" id="abo-glance-h">At a glance</h2>'
            '<dl class="dl-leader">%s</dl></section></div>'
            # a photo is shown only with the alt text that describes it (the content check requires one)
            % (portrait(about, here) if about.get('photo') and about['photo']['alt'].strip() else '', lead, dl))


def fig(label_, value, sub=''):
    value = core.dx(value)  # Data-XL punctuation pulled in: 3,436 -> 3<span class="dx-p">,</span>436
    return ('<div class="abo-fig"><dt class="t-label">%s</dt><dd class="t-data-xl abo-fig-v">%s</dd>%s</div>'
            % (label_, value, ('<dd class="t-mono-s abo-fig-s">%s</dd>' % sub) if sub else ''))


def numbers(site, here):
    """Left column: totals across every published report, then the five sections."""
    pub = site['published']
    km = sum(t['stats'].get('distance_km') or 0 for t in pub)
    gain = sum(t['stats'].get('gain_m') or 0 for t in pub)
    figs = []
    planned = len(site.get('active_goals', site['planned']))   # completed and archived goals are not future routes
    figs.append(fig('Reports', str(len(pub)), ('+ %d PLANNED ROUTE%s' % (planned, '' if planned == 1 else 'S')) if planned else ''))
    if km:
        mi, k = core.dist_vals(km)
        figs.append(fig('Distance', U(mi, k, 'mi', 'km'), U_sub(mi, k, 'MI', 'KM')))
    if gain:
        figs.append(fig('Gain', U(n(gain * FT), n(gain), 'ft', 'm'), U_sub(n(gain * FT), n(gain), 'FT', 'M')))
    hi = max((t for t in pub if t['stats'].get('high_m') is not None), key=lambda t: t['stats']['high_m'], default=None)
    if hi:
        h = hi['stats']['high_m']
        figs.append(fig('GPS max', U(n(h * FT), n(h), 'ft', 'm'), esc(hi['title']).upper()))
    yr = year_rows(site, here)
    by_year = ('<h3 class="t-label abo-act-h" id="abo-yr-h">By year</h3>' + yr) if yr else ''
    return ('<section class="abo-nums" aria-labelledby="abo-nums-h">'
            '<h2 class="t-h3" id="abo-nums-h">The reports</h2>'
            '<dl class="abo-figs">%s</dl>'
            '<h3 class="t-label abo-act-h" id="abo-act-h">By activity</h3>%s'
            '%s'
            '<h3 class="t-label abo-act-h" id="abo-site-h">Browse</h3>%s'
            '<a class="alink abo-map" href="%s">Open the map%s</a></section>'
            % (''.join(figs), act_rows(site, here), by_year, site_rows(site, here), link(here, 'map/'), icon('arrow-right', 16)))


def method(site):
    items = [
        'Tracks are GPS recordings exported through Strava. Each one is drawn in full, not trimmed, and every report '
        'offers the same full track as a GPX download (on <span class="abo-nw">multi-day trips</span>, one file for the whole '
        'route plus one per day).',
        'Distance, gain and moving time come from that recording. GPS&nbsp;max is the highest point in the GPX file, '
        'not a surveyed summit height.',
    ]
    if site['planned']:
        items.append('Planned routes are drawn as a dashed ink line and tagged PLANNED. Their distance is measured along '
                     'the planned line.')
    items += [
        'Hillshade and contours come from AWS Terrain Tiles. Roads, trails, water and peak names are map data '
        '©&nbsp;OpenStreetMap contributors.',
        'The maps are static and north-up. They are not for navigation.',
        'Reports describe past conditions, not advice. Check the current avalanche forecast before you go.',
        # gap5-02: the repository is public and the site's address already names its owner
        'The site is built from a public repository on GitHub. To report a broken link or a wrong name, '
        '<a href="%s/issues/new">open an issue</a> there. It needs a GitHub account, and it is for problems with the site, '
        'not for private questions.' % core.REPO_URL,
    ]
    lis = ''.join('<li><span class="abo-ol-n" aria-hidden="true">%02d</span><span>%s</span></li>' % (i + 1, s) for i, s in enumerate(items))
    return ('<section class="abo-sec" aria-labelledby="abo-how-h"><h2 class="t-h3" id="abo-how-h">How these reports are made</h2>'
            '<ol class="abo-ol">%s</ol></section>' % lis)


def units_block():
    ctl = ('<div class="units abo-units" role="radiogroup" aria-labelledby="abo-units-h">'
           '<button type="button" role="radio" aria-checked="true" data-units="mi" aria-label="%s">MI</button>'
           '<button type="button" role="radio" aria-checked="false" data-units="km" aria-label="%s">KM</button></div>' % core.UNITS_LABELS)
    return ('<section class="abo-sec" aria-labelledby="abo-units-h"><h2 class="t-h3" id="abo-units-h">Units</h2>'
            # the second sentence is about the switch: without JavaScript the switch is not shown (base.css), and neither
            # is the sentence (about.css)
            '<div class="abo-units-row"><p class="abo-p">Distances and heights are shown in miles and feet by default. '
            # a browser whose language is not English starts in kilometers (gap6-03: core.PREPAINT, which needs the script)
            '<span class="abo-units-how">Browsers set to a language other than English start in kilometers and meters. '
            'The <span class="abo-nw">MI | KM</span> switch changes every page, and this browser remembers the choice.</span>'
            '</p>%s</div></section>' % ctl)


def follow(here, author=None):
    """'Follow' (#follow, where the footer's Follow link lands, gap5-05): what to do with the feed, its address to copy
    (written out too, for a page without scripting), the raw feed and a line on RSS-to-email (gap5-07). With
    content/author.json (sitegen.author) it is 'Follow & contact': the address as a mailto button and as text (gap5-01)
    and the profiles Eric names, each rel="me" (gap5-03)."""
    feed = core.SITE_URL + 'feed.xml'
    shown = feed.split('://', 1)[-1]
    email = (author or {}).get('email')
    links = (author or {}).get('links') or []
    contact = ''
    if email:
        contact += ('<div class="abo-follow-row"><a class="btn" href="mailto:%s">Email</a><p class="abo-follow-u">%s</p></div>'
                    % (esc(email), esc(email)))
    if links:
        contact += ('<ul class="abo-follow-links">%s</ul>'
                    % ''.join('<li><a class="btn" href="%s" rel="me noopener">%s%s</a></li>' % (esc(x['url']), esc(x['label']), icon('arrow-right', 18))
                              for x in links))
    return ('<section class="abo-follow" id="follow" aria-labelledby="abo-follow-h"><div class="abo-follow-t">'
            '<h2 class="t-label" id="abo-follow-h">%s</h2>'
            '<p class="abo-follow-p">New reports go out on the RSS feed. Paste this address into a feed reader, such as '
            'NetNewsWire or Feedly, to see each one as it is published.</p>'
            '<p class="abo-follow-u">%s</p>'
            '<p class="abo-follow-p">Prefer email? An RSS-to-email service can turn this feed into messages.</p></div>'
            '<div class="abo-follow-row">%s<a class="btn abo-follow-b" href="%s" type="application/rss+xml">%sOpen feed.xml</a></div>%s'
            '</section>'
            % ('Follow &amp; contact' if (email or links) else 'Follow', esc(shown),
               core.copy_link(feed, 'Copy feed address', cls='btn', share=False), link(here, 'feed.xml'), icon('rss', 18), contact))


def page(site):
    here = URL
    body = ('<div class="abo wrap">'
            '<header class="abo-title"><h1 class="t-d1">About</h1></header>'
            '<div class="abo-grid">%s%s<div class="abo-more">%s%s%s</div></div></div>'
            % (intro(site, here), numbers(site, here), method(site), units_block(), follow(here, site.get('author'))))
    desc = ('About Eric Sichak\'s trip reports: where the tracks, maps and stats come from, '
            'how many reports there are, and how to follow new ones.')
    return core.Page(here, core.document(here, 'About', body, desc, active='about', body_cls='p-about', image=core.site_share()), 'About')


def build(site):
    return [page(site)]
