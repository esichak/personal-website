"""Single-day trip report (kind: trip) and planned routes (kind: planned) — /trips/<slug>/."""
import os

import markdown
import mapkit
import fit_reader

from sitegen import core
from sitegen.core import esc, U, U_sub, n, link, icon, FT, MI


def title_block(t, here, actions):
    act = t['activity']
    crumbs = ['<a href="%s">Reports</a>' % link(here, ''),
              '<a href="%s">%s</a>' % (link(here, core.section_url(act)), esc(core.ACT[act][0]))]
    if t.get('region'):
        crumbs.append('<span>%s</span>' % esc(t['region']))
    long_ = len(t['title']) > 28
    return ('<section class="rep-title wrap" aria-labelledby="title">'
            '<nav class="crumbs t-mono-s" aria-label="Breadcrumb">%s</nav>'
            '<div class="chips rep-chips">%s%s<span class="t-mono-s">%s</span></div>'
            '<div class="rep-head"><div class="rep-head-t"><h1 id="title" class="t-d1%s">%s</h1>'
            '<p class="t-mono-s rep-place">%s</p></div><div class="rep-actions">%s</div></div></section>'
            % ('<span aria-hidden="true">/</span>'.join(crumbs), core.chip(t, href=link(here, core.section_url(act))), core.trip_tags(t),
               core.trip_date(t), ' t-d1--long' if long_ else '', core.title_html(t['title']), core.place_line(t), actions))


def strip(t, cells_extra=()):
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
        sub = ('Start ' + core.ftime(t['start_time'])) if t.get('start_time') else ''
        cells.append(('Moving', '%s<span class="unit">h:mm</span>' % core.hm(st['moving_s']), sub))
    cells += list(cells_extra)
    out = ''.join('<div class="strip-c"><dt class="t-label">%s</dt><dd class="t-data-xl strip-v">%s</dd>%s</div>'
                  % (lab, val, ('<dd class="t-mono-s strip-s">%s</dd>' % sub) if sub else '') for lab, val, sub in cells)
    return '<dl class="strip" style="--cells:%d" aria-label="Trip stats">%s</dl>' % (max(len(cells), 1), out)


def stats_note(t):
    src = 'Stats from the Garmin recording via Strava.' if t['kind'] != 'planned' else 'Planned route, drawn by hand — distance and gain are estimates from the line.'
    return '<p class="strip-note">%s GPS max is the highest point in the GPX file, not a surveyed summit height.</p>' % src


def key_items(t, meta):
    if t['kind'] == 'planned':
        return ['planned', 'start_end']
    flat = 'speed-wide' in meta.get('charts', {})
    items = ['skin', 'ski'] if t['activity'] == 'ski' else ['route']
    items += ['start', 'end'] if t.get('route_shape') == 'point-to-point' else ['start_end']
    if not flat:
        items.append('gps')
        m = meta['maps'].get('map-wide') or meta['maps'].get('map-col') or {}
        items.append('mile_out' if m.get('outbound_only') else 'mile')
    return items


def map_caption(t, here, gpx_href):
    first = []
    if t['kind'] == 'planned':
        first.append('Planned route (approximate), not a recorded track')
    elif t['date']:
        first.append('Track: Garmin, %s' % core.fdate(t['date'], 'short'))
    first.append('full track, not trimmed')
    first.append('North up')
    return ('<div class="mapcap"><p class="mapcap-t"><span>%s</span><span>Terrain: AWS Terrain Tiles · Map data © OpenStreetMap contributors · Not for navigation</span></p>'
            '<div class="mapcap-a"><a class="btn" href="%s" download>%sDownload GPX</a></div></div>'
            % (' · '.join(first), gpx_href, icon('download', 18)))


def elevation_table(t, track_path, stats):
    """Mile-by-mile elevation from the GPX (smoothed), for the 'View as table' disclosure."""
    try:
        pts = fit_reader.read_gpx(track_path)
        tr = mapkit.Track(pts, t['slug'], t['cat'])
    except Exception:  # noqa: BLE001
        return ''
    if not tr.ele or tr.total <= 0:
        return ''
    f = (stats['distance_km'] * 1000.0 / tr.total) if stats.get('distance_km') else 1.0
    total_mi = tr.total * f / MI
    step = 0.5 if total_mi <= 8 else (1 if total_mi <= 20 else 2)
    rows = []
    m = 0.0
    j = 0
    while m <= total_mi + 1e-6:
        target = m * MI / f
        while j < len(tr.cd) - 1 and tr.cd[j] < target:
            j += 1
        e = tr.ele[j]
        rows.append('<tr><td>%s</td><td>%s</td></tr>' % (U(('%g' % m), ('%.1f' % (m * MI / 1000))), U(n(e * FT), n(e))))
        m += step
    e = tr.ele[-1]
    rows.append('<tr><td>%s</td><td>%s</td></tr>' % (U('%.1f' % total_mi, '%.1f' % (total_mi * MI / 1000)), U(n(e * FT), n(e))))
    return ('<details class="eltab"><summary>%sView as table</summary><table><thead><tr><th scope="col">%s</th><th scope="col">%s</th></tr></thead>'
            '<tbody>%s</tbody></table></details>'
            % (icon('chevron-down', 18), U('Mile', 'Km'), U('Elevation (ft)', 'Elevation (m)'), ''.join(rows)))


def profile_section(t, here, meta, ns='pf'):
    ch = meta.get('charts', {})
    if 'speed-wide' in ch:
        return ('<section class="rep-prof wrap sec" aria-labelledby="%s-h"><div class="rep-prof-h"><h2 class="t-label" id="%s-h">Speed</h2>'
                '<p class="t-mono-s">MPH, 3-MIN MEDIAN · FLAT WATER, NO ELEVATION PROFILE</p>%s</div>%s</section>'
                % (ns, ns, core.key_row(['speed'], 'keyrow--inline'),
                   core.chart_block(t, here, [('speed-wide', 'wide'), ('speed-col', 'col'), ('speed-phone', 'phone')], ns)))
    p = ch.get('profile-wide')
    if not p:
        return ''
    st = t['stats']
    hi = st.get('high_m') or (p['gps_max_ft'] / FT)
    lo = st.get('low_m') or (p['min_ft'] / FT)
    meta_line = 'GPS MAX %s · MIN %s · VERTICAL ×%.1f' % (U(n(hi * FT) + ' FT', n(hi) + ' M'), U(n(lo * FT) + ' FT', n(lo) + ' M'), p.get('vx', 1))
    keys = core.key_row(['hatch', 'fill'], 'keyrow--inline') if t['activity'] == 'ski' else ''
    return ('<section class="rep-prof wrap sec" aria-labelledby="%s-h"><div class="rep-prof-h"><h2 class="t-label" id="%s-h">Elevation</h2>'
            '<p class="t-mono-s">%s</p>%s</div>%s%s</section>'
            % (ns, ns, meta_line, keys, core.chart_block(t, here, [('profile-wide', 'wide'), ('profile-col', 'col'), ('profile-phone', 'phone')], ns),
               elevation_table(t, t['track'], st)))


def beta_list(t):
    rows = list(t['beta'])
    if t.get('route_shape'):
        rows.append({'label': 'Route', 'value': core.SHAPE.get(t['route_shape'], t['route_shape'])})
    if t.get('party'):
        rows.append({'label': 'Party', 'value': 'With ' + t['party']})
    if not rows:
        return ''
    return ('<div class="rail-b"><h2 class="t-label" id="beta">Beta</h2><dl class="dl-leader">%s</dl></div>'
            % ''.join('<div><dt>%s</dt><span class="lead" aria-hidden="true"></span><dd>%s</dd></div>' % (esc(r['label']), esc(str(r['value'])))
                      for r in rows if r.get('label')))


def gallery(t, here, photos, ns='ph'):
    if not photos:
        return ''
    first, rest = photos[0], photos[1:]
    big = core.photo(t, first, here, sizes='(min-width: 1200px) 1248px, 100vw', cls='photo--lead')
    grid = ''.join('<a class="gal-a" href="%s%s">%s</a>' % (link(here, t['url']), p['file'],
                                                           core.photo(t, p, here, sizes='(min-width: 760px) 400px, 50vw', caption=False))
                   for p in rest)
    return ('<section class="rep-photos wrap sec" aria-labelledby="%s-h"><div class="shead"><h2 class="shead-t" id="%s-h">Photos</h2>'
            '<span class="shead-m t-mono-s">%d PHOTO%s</span></div><div class="gal">%s%s</div></section>'
            % (ns, ns, len(photos), '' if len(photos) == 1 else 'S', big, ('<div class="gal-grid">%s</div>' % grid) if grid else ''))


def pager(t, here, site):
    same = [x for x in site['published'] if x['activity'] == t['activity']]
    if t not in same:
        return ''
    i = same.index(t)
    newer = same[i - 1] if i > 0 else None
    older = same[i + 1] if i + 1 < len(same) else None
    cells = []
    for lab, x, cls in (('Newer', newer, 'prev'), ('Older', older, 'next')):
        if not x:
            continue
        arrow = icon('arrow-left' if cls == 'prev' else 'arrow-right', 14)
        lbl = ('%s<span>%s</span>' % (arrow, lab)) if cls == 'prev' else ('<span>%s</span>%s' % (lab, arrow))
        g = core.glyph(x, here, 'g112', 'pg-%s' % x['slug']).replace('<svg ', '<svg class="glyph" ', 1)
        txt = ('<span class="pager-t"><span class="t-label pager-l">%s</span><span class="pager-n">%s</span>'
               '<span class="t-mono-s">%s · %s</span></span>' % (lbl, esc(x['title']), core.trip_date(x), core.plain_stats(x)))
        cells.append('<a class="%s" href="%s">%s</a>' % (cls, link(here, x['url']), (g + txt) if cls == 'prev' else (txt + g)))
    if not cells:
        return ''
    return '<nav class="pager wrap sec" aria-label="More %s reports">%s</nav>' % (esc(core.ACT[t['activity']][0].lower()), ''.join(cells))


def bottom_bar(t, here, gpx_href, has_beta, has_report):
    items = [('#map', 'map', 'Map')]
    if has_beta:
        items.append(('#beta', 'beta', 'Beta'))
    elif t['kind'] != 'planned':
        items.append(('#stats', 'beta', 'Stats'))
    if has_report:
        items.append(('#report', 'report', 'Report'))
    elif t['photos']:
        items.append(('#photos', 'photo', 'Photos'))
    out = ''.join('<a href="%s">%s<span>%s</span></a>' % (h, icon(ic, 24), lab) for h, ic, lab in items)
    out += '<a href="%s" download>%s<span>GPX</span></a>' % (gpx_href, icon('download', 24))
    return '<nav class="bbar" aria-label="Report sections" style="--n:%d">%s</nav>' % (len(items) + 1, out)


def page(t, site):
    here = t['url']
    meta = core.render_meta(t)
    gpx_href = t['slug'] + '.gpx'
    has_report = bool(t['body_md'])
    actions = ''
    if has_report:
        actions += '<a class="btn" href="#report">%sRead the report</a>' % icon('report', 18)
    actions += '<a class="btn btn--ink" href="%s" download>%sDownload GPX</a>' % (gpx_href, icon('download', 18))
    body = [title_block(t, here, actions)]
    if t['kind'] != 'planned':
        body.append('<section class="wrap rep-strip" id="stats" aria-label="Stats">%s%s</section>' % (strip(t), stats_note(t)))
    variants = [('map-wide', 'wide'), ('map-col', 'col'), ('map-phone', 'phone')]
    body.append('<section class="rep-map" id="map" aria-label="Route map"><div class="bleed">%s</div><div class="wrap">%s%s</div></section>'
                % (core.map_block(t, here, variants, t['url'] + 'map/', 'm', eager=True, cls='map--report' + (' map--nowide' if 'map-wide' not in meta['maps'] else '')),
                   core.key_row(key_items(t, meta)), map_caption(t, here, gpx_href)))
    if t['kind'] != 'planned':
        body.append(profile_section(t, here, meta))
    beta = beta_list(t)
    contents = []
    if has_report:
        contents.append(('#report', 'Trip report'))
    if t['photos']:
        contents.append(('#photos', 'Photos'))
    toc = ''
    if len(contents) > 1:
        toc = ('<nav class="rail-toc" aria-labelledby="toc-h"><h2 class="t-label" id="toc-h">Contents</h2><ul>%s</ul></nav>'
               % ''.join('<li><a href="%s">%s</a></li>' % c for c in contents))
    main = ''
    if has_report:
        main = ('<h2 class="t-h3 rep-h" id="report">Trip report</h2><div class="prose t-body">%s</div>' % markdown.to_html(t['body_md']))
    elif t['kind'] == 'planned':
        main = ('<h2 class="t-h3 rep-h" id="report">Planned</h2><div class="prose t-body"><p>A route I want to do. The line is drawn by hand, '
                'so treat distance and gain as rough. A report will replace this page once it is done.</p></div>')
    if beta or toc or main:
        body.append('<div class="rep-body wrap sec"><aside class="rep-rail">%s%s</aside><div class="rep-main">%s</div></div>' % (beta, toc, main))
    if t['photos']:
        body.append('<div id="photos">%s</div>' % gallery(t, here, t['photos']))
    body.append(pager(t, here, site))
    desc = core.excerpt(t, 155) or '%s — %s trip report with GPX map.' % (t['title'], core.ACT[t['activity']][0])
    img = (t['url'] + t['photos'][0]['file']) if t['photos'] else None
    return core.Page(here, core.document(here, t['title'], ''.join(body), desc, active=t['activity'], image=img, body_cls='p-report',
                                         bottom=bottom_bar(t, here, gpx_href, bool(beta), has_report)), t['title'])


def build(site):
    return [page(t, site) for t in site['trips'] if not t['days'] and t['kind'] in ('trip', 'planned')]
