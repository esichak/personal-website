#!/usr/bin/env python3
"""What each published report has and lacks, one row per trip, newest first (read-only, stdlib only).

  python3 tools/content_report.py                    # every report: date, slug, title flag, write-up, photos, cover, place, party, summary
  python3 tools/content_report.py --missing place    # only the reports without a place: (also writeup, photos, cover, summary)
  python3 tools/content_report.py --alt              # the alt text of the most-seen photos: home features, region Featured rows, covers
  python3 tools/content_report.py --taxonomy         # every region and place with its count, and the names to look at
                                                     # (a region of one report is named with the region it lies near)
  python3 tools/content_report.py --markdown         # the table as Markdown in .cache/content-report.md (git-ignored)

Title flag: 'strava' for a name Strava gives an activity by itself ('Morning Hike', 'Ride near <a town>'), 'xN' for a
title N reports share. Cover: 'explicit' (a cover_photo: line), 'auto' (picked by content.resolve_cover, a fallback,
not an editorial choice) or 'none' (no photo). It reads content/ and rendered/site/meta.json; it writes nothing but the
Markdown file, and never touches content/.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import geo  # noqa: E402
import markdown  # noqa: E402
import strava  # noqa: E402
MISSING = ('place', 'writeup', 'photos', 'cover', 'summary')
MARKDOWN_OUT = os.path.join('.cache', 'content-report.md')


def published():
    """The site dict tools/build.py makes: site['published'] is the reports, newest first (undated last)."""
    import build
    return build.site_of(content.load_all())


def photo_count(t):
    return len(t['photos']) + sum(len(d['photos']) for d in t['days'])


def cover_kind(t):
    if not t.get('cover'):
        return 'none'
    return 'explicit' if t.get('cover_photo') else 'auto'


def writeup_chars(t):
    return len(markdown.plain(t['body_md'] or '')) + sum(len(markdown.plain(d['body_md'] or '')) for d in t['days'])


def rows(pub):
    """[dict] one per published report, in pub's order."""
    shared = {}
    for t in pub:
        shared[t['title'].casefold()] = shared.get(t['title'].casefold(), 0) + 1
    out = []
    for t in pub:
        flags = []
        if strava.default_title(t['title']):
            flags.append('strava')
        if shared[t['title'].casefold()] > 1:
            flags.append('x%d' % shared[t['title'].casefold()])
        out.append({'date': t['date'].isoformat() if t.get('date') else '', 'slug': t['slug'], 'title': t['title'],
                    'flag': ', '.join(flags), 'writeup': writeup_chars(t), 'photos': photo_count(t),
                    'cover': cover_kind(t), 'place': t.get('place') or '', 'party': t.get('party') or '',
                    'summary': 'yes' if t.get('card_summary') else '', 'has_writeup': t['has_writeup']})
    return out


def lacking(r, what):
    return {'place': not r['place'], 'writeup': not r['has_writeup'], 'photos': not r['photos'],
            'cover': r['cover'] != 'explicit', 'summary': not r['summary']}[what]


COLUMNS = (('date', 'DATE', 10), ('slug', 'SLUG', 44), ('flag', 'TITLE', 12), ('writeup', 'CHARS', 6),
           ('photos', 'PHOTOS', 6), ('cover', 'COVER', 8), ('place', 'PLACE', 24), ('party', 'PARTY', 14), ('summary', 'SUMMARY', 7))


def table(rs):
    def cell(v, w):
        v = str(v)
        return (v[:w - 1] + '…') if len(v) > w else v.ljust(w)
    lines = ['  '.join(cell(h, w) for _k, h, w in COLUMNS).rstrip()]
    for r in rs:
        lines.append('  '.join(cell(r[k] if r[k] != '' else '-', w) for k, _h, w in COLUMNS).rstrip())
    return lines


def markdown_table(rs):
    head = '| ' + ' | '.join(h.capitalize() for _k, h, _w in COLUMNS) + ' |'
    lines = [head, '|' + ' --- |' * len(COLUMNS)]
    for r in rs:
        lines.append('| ' + ' | '.join(str(r[k]).replace('|', '\\|') if r[k] != '' else '-' for k, _h, _w in COLUMNS) + ' |')
    return lines


def alt_report(site):
    """(heading, [(slug, photo file, alt)]) for the home features, each region page's Featured row, and every cover."""
    from sitegen import core, curation
    from sitegen.pages import region as region_page
    out = []

    def item(t):
        c = t.get('cover')
        return (t['slug'], c['photo']['file'] if c else '(no photo)', (c['photo'].get('alt') or '') if c else '')
    try:
        # the module's names, looked up now (featured_for's defaults were bound when it was imported)
        featured = curation.resolve_featured(site, curation.load_manifest(curation.HOME_JSON), content.TRIPS_DIR)
    except Exception as ex:                 # noqa: BLE001 — a broken home.json is the build's to report
        featured = []
        print('content/home.json could not be read: %s' % ex, file=sys.stderr)
    out.append(('The home page\'s featured trips (content/home.json)', [item(t) for t in featured]))
    meta = core.read_site_meta()
    for name, _slug, ts in core.region_pages(site, meta):
        out.append(('The Featured row of the %s page' % name, [item(t) for t in region_page.pick_featured(ts)]))
    out.append(('Every cover (explicit or automatic)', [item(t) for t in site['published'] if t.get('cover')]))
    return out


NEAR_KM = 150     # a region of one report whose start lies this close to another region's trips is named beside it


def starts_of(pub):
    """{slug: (lat, lon)}: each report's first point, from its rendered/trips/<slug>/meta.json. Used only to say which
    regions lie near one another; no point is ever printed."""
    out = {}
    for t in pub:
        try:
            with open(os.path.join(t['rendered'], 'meta.json'), encoding='utf-8') as fh:
                start = json.load(fh).get('start')
        except (OSError, ValueError, AttributeError, KeyError):
            continue
        if isinstance(start, list) and len(start) == 2 and all(isinstance(x, (int, float)) for x in start):
            out[t['slug']] = tuple(start)
    return out


def taxonomy(pub, starts=None):
    """(regions [(name, slug, n)], places {region: [(place, n)]}, notes [str]). starts ({slug: (lat, lon)}, starts_of)
    names, beside a region of one report, the region whose trips start nearest, when within NEAR_KM."""
    regions, places = {}, {}
    for t in pub:
        r = (t.get('region') or '').strip()
        p = (t.get('place') or '').strip()
        if r:
            regions[r] = regions.get(r, 0) + 1
        if p:
            places.setdefault(r or '(no region)', {})
            places[r or '(no region)'][p] = places[r or '(no region)'].get(p, 0) + 1
    regs = sorted(((n, content.slugify(n), k) for n, k in regions.items()), key=lambda x: (-x[2], x[0]))
    pl = {r: sorted(v.items(), key=lambda x: (-x[1], x[0])) for r, v in places.items()}
    notes = []
    # regions with regions and places with places: a region that holds a place of its own name is the usual shape
    for kind, names in (('regions', sorted(regions)), ('places', sorted({p for v in places.values() for p in v}))):
        for a in names:
            for b in names:
                if a != b and b.lower().startswith(a.lower() + ' '):
                    notes.append("%s '%s' and '%s': one name inside the other; the same %s?" % (kind, a, b, kind[:-1]))
    by_slug = {}
    for n in regions:
        by_slug.setdefault(content.slugify(n), []).append(n)
    for slug, ns in sorted(by_slug.items()):
        if len(ns) > 1:
            notes.append('regions %s are one region (%s) spelt %d ways' % (', '.join("'%s'" % n for n in ns), slug, len(ns)))
    singles = [n for n, _s, k in regs if k == 1]
    if singles:
        notes.append('regions of one report (no region page; part of a larger region?): %s'
                     % ', '.join(n + near_region(n, pub, starts or {}) for n in singles))
    return regs, pl, notes


def near_region(name, pub, starts):
    """' (near Boise)' when a trip of another region starts within NEAR_KM of this region's, else ''."""
    if not starts:
        return ''
    mine = [starts[t['slug']] for t in pub if (t.get('region') or '').strip() == name and t.get('slug') in starts]
    best = None
    for t in pub:
        r = (t.get('region') or '').strip()
        if r and r != name and t.get('slug') in starts:
            for p in mine:
                d = geo.hav(p, starts[t['slug']])
                if best is None or d < best[0]:
                    best = (d, r)
    return (' (near %s)' % best[1]) if best and best[0] <= NEAR_KM * 1000 else ''


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--missing', choices=MISSING, help='only the reports that lack this')
    ap.add_argument('--alt', action='store_true', help='the alt text of the home features, the region Featured rows and every cover')
    ap.add_argument('--taxonomy', action='store_true', help='every region and place with its count, and the names to look at')
    ap.add_argument('--markdown', action='store_true', help='write the table as Markdown to %s' % MARKDOWN_OUT)
    a = ap.parse_args(argv)
    site = published()
    pub = site['published']
    if a.alt:
        for heading, items in alt_report(site):
            print('%s (%d)' % (heading, len(items)))
            for slug, f, alt in items:
                print('  %-44s %-14s %s' % (slug, f, alt or '(no alt text)'))
            print()
        return 0
    if a.taxonomy:
        regs, pl, notes = taxonomy(pub, starts_of(pub))
        print('%d regions (region: the map grouping; place: the named area inside it)' % len(regs))
        for name, slug, k in regs:
            print('  %-22s %-22s %3d report%s' % (name, slug, k, '' if k == 1 else 's'))
            for p, n in pl.get(name, []):
                print('      %-36s %3d' % (p, n))
        if pl.get('(no region)'):
            print('  (no region)')
            for p, n in pl['(no region)']:
                print('      %-36s %3d' % (p, n))
        print('\n%d reports without a place: python3 tools/content_report.py --missing place' % sum(1 for t in pub if not t.get('place')))
        if notes:
            print('\nTo look at:')
            for n in notes:
                print('  ' + n)
        return 0
    rs = rows(pub)
    if a.missing:
        rs = [r for r in rs if lacking(r, a.missing)]
    if a.markdown:
        path = os.path.join(ROOT, MARKDOWN_OUT)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('# Content report\n\n' + '\n'.join(markdown_table(rs)) + '\n')
        print('wrote %s (%d rows)' % (MARKDOWN_OUT, len(rs)))
        return 0
    for line in table(rs):
        print(line)
    print('%d report%s%s' % (len(rs), '' if len(rs) == 1 else 's', (' without %s' % a.missing) if a.missing else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
