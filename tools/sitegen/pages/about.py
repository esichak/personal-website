"""About page — /about/. Who runs the site, what it is, how the maps and stats are made, live counts, RSS.

Everything shown is either a confirmed fact (name, Lake Tahoe, AIARE 2), a description of how the site is built,
or a number computed from the published trips. No bio, portrait or email until Eric writes them.
"""
from sitegen import core
from sitegen.core import esc, U, U_sub, n, link, icon, FT

URL = 'about/'


# ---------------------------------------------------------------- numbers from the content

def activity_counts(site):
    """[(act, published reports, distance_km, subtypes present)] in nav order."""
    out = []
    for act, _ in core.NAV:
        xs = [t for t in site['published'] if t['activity'] == act]
        km = sum(t['stats'].get('distance_km') or 0 for t in xs)
        subs = []
        for t in xs:
            s = t.get('subtype')
            if s and core.SUB_WORD.get(s, s) not in subs:
                subs.append(core.SUB_WORD.get(s, s))
        out.append((act, len(xs), km, subs))
    return out


def count_word(k, one='REPORT', many='REPORTS'):
    return '%d %s' % (k, one if k == 1 else many)


def act_rows(site, here, cls='', dist=True):
    """64px rows linking to the five sections: disc · name · Mono-S count (+ sub-types present) · distance · chevron.

    Shared with the 404 page (notfound.py), which uses it without distances."""
    rows = []
    for act, k, km, subs in activity_counts(site):
        name = core.ACT[act][0]
        meta = [count_word(k) if k else 'NO REPORTS YET'] + [esc(s).upper() for s in subs]
        d = ''
        if dist and km:
            d = '<span class="abo-act-d t-data-m">%s</span>' % core.distance(km)
        rows.append('<li><a class="abo-act-a" href="%s">%s<span class="abo-act-w"><span class="abo-act-n">%s</span>'
                    '<span class="t-mono-s abo-act-m">%s</span></span>%s%s</a></li>'
                    % (link(here, core.section_url(act)), core.disc(act, 32), esc(name), core.SEP.join(meta), d,
                       icon('chevron-right', 20, 'abo-act-c')))
    return '<ul class="abo-act%s">%s</ul>' % ((' ' + cls) if cls else '', ''.join(rows))


# ---------------------------------------------------------------- blocks

def intro(site):
    """Right column, top: lead + at-a-glance facts."""
    pub = [t for t in site['published'] if t['date']]
    rows = [('Based in', 'Lake Tahoe'), ('Avalanche training', 'AIARE 2')]
    if pub:
        a, b = min(t['date'] for t in pub), max(t['date'] for t in pub)
        span = core.fdate(a, 'month') if (a.year, a.month) == (b.year, b.month) else '%s – %s' % (core.fdate(a, 'month'), core.fdate(b, 'month'))
        rows.append(('Trip dates', span))
    dl = ''.join('<div><dt>%s</dt><dd>%s</dd></div>' % (esc(k), esc(v)) for k, v in rows)
    return ('<div class="abo-intro">'
            '<p class="abo-lead">Trip reports by Eric Sichak: backcountry skiing, climbing, hiking, mountain biking and other trips, '
            'each with the full GPX track.</p>'
            '<section class="abo-sec abo-glance" aria-labelledby="abo-glance-h"><h2 class="t-h3" id="abo-glance-h">At a glance</h2>'
            '<dl class="abo-dl">%s</dl></section></div>' % dl)


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
    planned = len(site['planned'])
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
    return ('<section class="abo-nums" aria-labelledby="abo-nums-h">'
            '<h2 class="t-h3" id="abo-nums-h">The reports</h2>'
            '<dl class="abo-figs">%s</dl>'
            '<h3 class="t-label abo-act-h" id="abo-act-h">By activity</h3>%s'
            '<a class="alink abo-map" href="%s">Open the map%s</a></section>'
            % (''.join(figs), act_rows(site, here), link(here, 'map/'), icon('arrow-right', 16)))


def method(site):
    items = [
        'Tracks are Garmin recordings, exported through Strava. Each one is drawn in full, not trimmed, and every report '
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
    ]
    lis = ''.join('<li><span class="abo-ol-n" aria-hidden="true">%02d</span><span>%s</span></li>' % (i + 1, s) for i, s in enumerate(items))
    return ('<section class="abo-sec" aria-labelledby="abo-how-h"><h2 class="t-h3" id="abo-how-h">How these reports are made</h2>'
            '<ol class="abo-ol">%s</ol></section>' % lis)


def units_block():
    ctl = ('<div class="units abo-units" role="radiogroup" aria-labelledby="abo-units-h">'
           '<button type="button" role="radio" aria-checked="true" data-units="mi">MI</button>'
           '<button type="button" role="radio" aria-checked="false" data-units="km">KM</button></div>')
    return ('<section class="abo-sec" aria-labelledby="abo-units-h"><h2 class="t-h3" id="abo-units-h">Units</h2>'
            '<div class="abo-units-row"><p class="abo-p">Distances and heights are shown in miles and feet by default. The <span class="abo-nw">MI | KM</span> switch '
            'changes every page to kilometres and metres, and this browser remembers the choice.</p>%s</div></section>' % ctl)


def follow(here):
    feed = core.SITE_URL + 'feed.xml'
    shown = feed.split('://', 1)[-1]
    return ('<section class="abo-follow" aria-labelledby="abo-follow-h"><div class="abo-follow-t">'
            '<h2 class="t-label" id="abo-follow-h">Follow</h2>'
            '<p class="abo-follow-p">New reports go out on the RSS feed.</p>'
            '<p class="abo-follow-u">%s</p></div>'
            '<a class="btn abo-follow-b" href="%s">%sRSS feed</a></section>'
            % (esc(shown), link(here, 'feed.xml'), icon('rss', 18)))


def page(site):
    here = URL
    body = ('<div class="abo wrap">'
            '<header class="abo-title"><h1 class="t-d1">About</h1></header>'
            '<div class="abo-grid">%s%s<div class="abo-more">%s%s%s</div></div></div>'
            % (intro(site), numbers(site, here), method(site), units_block(), follow(here)))
    desc = ('About Eric Sichak\'s trip reports: where the tracks, maps and stats come from, '
            'how many reports there are, and how to follow new ones.')
    return core.Page(here, core.document(here, 'About', body, desc, active='about', body_cls='p-about'), 'About')


def build(site):
    return [page(site)]
