"""Single-day trip report (kind: trip) and planned routes (kind: planned) — /trips/<slug>/, plus the phone full-screen
map page /trips/<slug>/map/."""
import markdown
import mapkit
import fit_reader

from sitegen import core
from sitegen.core import esc, U, n, link, icon, FT, MI


def date_slot(t):
    """The Mono-S value after the chips: the date, or the planned distance for a planned route (it has no date)."""
    if t['kind'] == 'planned':
        mi, km = core.dist_vals(t['stats'].get('distance_km'))
        return U(core.nb(mi + ' MI PLANNED'), core.nb(km + ' KM PLANNED')) if mi else ''
    return core.trip_date(t)


def title_block(t, here, actions):
    """Shared by single-day, planned, multi-day and series pages. Phones (< 760) drop the crumbs and the date slot; the date
    then leads the place line (Phone-Report-A)."""
    act = t['activity']
    sec = link(here, core.section_url(act))
    crumbs = ['<a href="%s">Reports</a>' % link(here, ''), '<a href="%s">%s</a>' % (sec, esc(core.ACT[act][0]))]
    reg = core.region_map_href(here, t.get('region'))
    if reg:
        crumbs.append('<a href="%s">%s</a>' % (reg, esc(t['region'])))
    long_ = len(t['title']) > 28
    date_ = date_slot(t)
    place = core.place_line(t)
    pdate = ('<span class="rep-pdate">%s%s</span>' % (date_, core.SEP if place else '')) if date_ else ''
    return ('<section class="rep-title wrap" aria-labelledby="title">'
            '<nav class="crumbs" aria-label="Breadcrumb">%s</nav>'
            '<div class="chips rep-chips">%s%s%s</div>'
            '<div class="rep-head"><div class="rep-head-t"><h1 id="title" class="t-d1%s">%s</h1>'
            '<p class="t-mono-s rep-place">%s%s</p></div><div class="rep-actions">%s</div></div></section>'
            % ('<span aria-hidden="true">/</span>'.join(crumbs), core.chip(t, href=sec), core.trip_tags(t),
               ('<span class="t-mono-s">%s</span>' % date_) if date_ else '',
               ' t-d1--long' if long_ else '', core.title_html(t['title']), pdate, place, actions))


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
    return items


def map_caption(t, here, gpx_href=None):
    """Two Small lines under the key row; the outline GPX button only where the title block has no ink one (never on planned)."""
    first = []
    if t['kind'] == 'planned':
        first.append('Planned route, not a recorded track')
    else:
        if t['date']:
            first.append('Track: Garmin, %s' % core.fdate(t['date'], 'short'))
        first.append('full track, not trimmed')
    first.append('North up')
    btn = ''
    if gpx_href and t['kind'] != 'planned':
        btn = '<div class="mapcap-a"><a class="btn" href="%s" download>%sDownload GPX</a></div>' % (gpx_href, icon('download', 18))
    return ('<div class="mapcap"><p class="mapcap-t"><span>%s</span><span>Terrain: AWS Terrain Tiles · Map data © OpenStreetMap contributors · Not for navigation</span></p>'
            '%s</div>' % (' · '.join(first), btn))


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
                '<p class="t-mono-s">%s</p>%s</div>%s</section>'
                % (ns, ns, core.speed_meta(t), core.key_row(['speed'], 'keyrow--inline'),
                   core.chart_block(t, here, [('speed-wide', 'wide'), ('speed-col', 'col'), ('speed-phone', 'phone')], ns)))
    p = ch.get('profile-wide')
    if not p:
        return ''
    st = t['stats']
    hi = st.get('high_m') or (p['gps_max_ft'] / FT)
    lo = st.get('low_m') or (p['min_ft'] / FT)
    variants = [('profile-wide', 'wide'), ('profile-col', 'col'), ('profile-phone', 'phone')]
    meta_line = 'GPS MAX %s · MIN %s · %s' % (U(core.nb(n(hi * FT) + ' FT'), core.nb(n(hi) + ' M')),
                                             U(core.nb(n(lo * FT) + ' FT'), core.nb(n(lo) + ' M')), core.vx_line(ch, variants))
    keys = core.key_row(['hatch', 'fill'], 'keyrow--inline') if t['activity'] == 'ski' else ''
    return ('<section class="rep-prof wrap sec" aria-labelledby="%s-h"><div class="rep-prof-h"><h2 class="t-label" id="%s-h">Elevation</h2>'
            '<p class="t-mono-s">%s</p>%s</div>%s%s</section>'
            % (ns, ns, meta_line, keys, core.chart_block(t, here, variants, ns),
               elevation_table(t, t['track'], st)))


def beta_list(t):
    """Beta rows from the front matter only (route shape lives in the chip row, party in the place line)."""
    rows = [r for r in t['beta'] if r.get('label')]
    if not rows:
        return ''
    return ('<div class="rail-b"><h2 class="t-label" id="beta">Beta</h2><dl class="dl-leader">%s</dl></div>'
            % ''.join('<div><dt>%s</dt><span class="lead" aria-hidden="true"></span><dd>%s</dd></div>' % (esc(r['label']), esc(str(r['value'])))
                      for r in rows if r.get('label')))


def gallery(t, here, photos, ns='ph'):
    """Photos in their order: each landscape photo full width (2:1, 3:2 on phones); runs of portraits in a 3:4 grid
    (2-up phone, 3-up tablet, 4-up 294×392 desktop). A portrait is never cropped into the wide format."""
    if not photos:
        return ''
    parts, run = [], []

    def flush():
        if run:
            parts.append('<div class="gal-grid gal-grid--n%d">%s</div>' % (len(run), ''.join(
                '<a class="gal-a" href="%s%s">%s</a>' % (link(here, t['url']), p['file'],
                                                        core.photo(t, p, here, sizes='(min-width: 1200px) 294px, (min-width: 760px) 33vw, 50vw',
                                                                   caption=False)) for p in run)))
            del run[:]
    for p in photos:
        if (p.get('w') or 1) >= (p.get('h') or 0):
            flush()
            parts.append('<a class="gal-a" href="%s%s">%s</a>' % (link(here, t['url']), p['file'],
                                                                 core.photo(t, p, here, sizes='(min-width: 1200px) 1248px, 100vw', cls='gal-wide')))
        else:
            run.append(p)
    flush()
    return ('<section class="rep-photos wrap sec" aria-labelledby="%s-h"><div class="rep-sh"><h2 class="t-h3" id="%s-h">Photos</h2>'
            '<span class="t-mono-s">%d PHOTO%s</span></div><div class="gal">%s</div></section>'
            % (ns, ns, len(photos), '' if len(photos) == 1 else 'S', ''.join(parts)))


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
               '<span class="t-mono-s">%s</span></span>' % (lbl, esc(x['title']), core.SEP.join(b for b in (core.trip_date(x), core.plain_stats(x)) if b)))
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
    planned = t['kind'] == 'planned'
    gpx_href = t['slug'] + '.gpx'
    has_report = bool(t['body_md'])
    actions = ''
    if has_report:
        actions += '<a class="btn" href="#report">%sRead the report</a>' % icon('report', 18)
    actions += '<a class="btn btn--ink" href="%s" download>%sDownload GPX</a>' % (gpx_href, icon('download', 18))
    body = [title_block(t, here, actions)]
    if not planned:
        body.append('<section class="wrap rep-strip" id="stats" aria-label="Stats">%s%s</section>'
                    % (core.strip(core.strip_cells(t)), core.stats_note(t)))
    variants = [('map-wide', 'wide'), ('map-col', 'col'), ('map-phone', 'phone')]
    nowide = 'map-wide' not in meta['maps']
    after = core.stats_note(t, 'rep-note-ph') if not planned else ''
    if planned:
        after += '<p class="t-small rep-plan">Planned route: there is no recorded track, write-up or stats for it.</p>'
    body.append('<section class="rep-map" id="map" aria-label="Route map"><div class="bleed">%s</div><div class="wrap">%s%s%s</div></section>'
                % (core.map_block(t, here, variants, t['url'] + 'map/', 'm', eager=True, cls='map--report' + (' map--nowide' if nowide else ''),
                                  fullscreen_href=link(here, t['url'] + 'map/')),
                   core.key_rows(key_items(t, meta), key_items(t, meta, phone=True)), map_caption(t, here, gpx_href), after))
    if not planned:
        body.append(profile_section(t, here, meta))
    beta = beta_list(t)
    if not planned:
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
        if beta or toc or main:
            body.append('<div class="rep-body wrap sec"><aside class="rep-rail">%s%s</aside><div class="rep-main">%s</div></div>' % (beta, toc, main))
    else:
        beta = ''
    if t['photos']:
        body.append('<div id="photos">%s</div>' % gallery(t, here, t['photos']))
    body.append(pager(t, here, site))
    desc = core.excerpt(t, 155) or core.summary(t)
    img = (t['url'] + t['photos'][0]['file']) if t['photos'] else None
    head = core.map_preloads(t, here, variants, t['url'] + 'map/', nowide=nowide)
    return core.Page(here, core.document(here, t['title'], ''.join(body), desc, active=t['activity'], image=img, body_cls='p-report',
                                         bottom=bottom_bar(t, here, gpx_href, bool(beta), has_report), extra_head=head,
                                         og_type='article'), t['title'])


def fullscreen_page(t):
    """trips/<slug>/map/: the report map at full size for phones (pan + pinch zoom), linked from the phone map's button."""
    here = t['url'] + 'map/'
    meta = core.render_meta(t)
    name = 'map-wide' if 'map-wide' in meta['maps'] else 'map-col'
    mp = core.map_block(t, here, [(name, 'fs')], t['url'] + 'map/', 'fs', attrib=False,
                        cls='map--fs' + ('' if name == 'map-wide' else ' map--fscol'))
    body = ('<h1 class="sr">%s: map</h1><div class="wrap fs-bar"><a class="btn" href="../#map">%sBack to report</a></div>'
            '<div class="fs-map">%s</div><div class="wrap fs-foot">%s%s</div>'
            % (esc(t['title']), icon('arrow-left', 18), mp, core.key_row(key_items(t, meta)), map_caption(t, here)))
    desc = 'Full-size route map for %s.' % t['title']
    return core.Page(here, core.document(here, t['title'] + ' map', body, desc, active=t['activity'], body_cls='p-fsmap',
                                         extra_head='<meta name="robots" content="noindex">'), t['title'] + ' map', index=False)


def build(site):
    out = []
    for t in site['trips']:
        if not t['days'] and t['kind'] in ('trip', 'planned'):
            out += [page(t, site), fullscreen_page(t)]
    return out
