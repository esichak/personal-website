#!/usr/bin/env python3
"""What the site and its history weigh and how fast they grow, in decimal MB (1 MB = 1,000,000 bytes).

  python3 tools/size_report.py               # tracked, history, site (_site/), growth by year, GitHub's limits
  python3 tools/size_report.py --site DIR    # measure the build in DIR instead of _site/ (a --link build is fine)
  python3 tools/size_report.py --json        # the same as one JSON object, sizes in bytes

Read-only: no network, nothing written, git only asked (--no-optional-locks; never gc, repack or fetch). tracked: every
blob in HEAD by kind (photos full/.sm/.th as tools/lib/photos.py names them, GPX, rendered .webp/.png, .base.svg,
.svg.html, meta.json, the rest) at the sizes git ls-tree -r -l HEAD prints, read from the index for each blob it holds
unchanged and from git cat-file --batch-check for the others: -l opens every object, and iCloud offloads loose objects
(the first -l run on 2026-10-25 fetched about 15 a minute). history: git count-objects -v, no verify-pack. site: _site/
or --site walked by the same kinds, a --link build's symlinks counted as their targets (what a copying build ships).
growth: content.load_all(), drafts included, each trip's photos, GPX and rendered/trips/<slug> summed by the calendar
year of its date; 'pack est.' keeps photos and rasters whole, GPX at 17 %, the rest at 40 % (measured 2026-10-13).
iCloud conflict copies (sitecheck.conflict_copy) are left out and counted.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
from sitegen import sitecheck  # noqa: E402

MB, GB = 1e6, 1e9
KINDS = (('photo', 'photos full'), ('photo_sm', 'photos .sm'), ('photo_th', 'photos .th'), ('gpx', 'GPX'),
         ('raster', 'rendered .webp/.png'), ('base_svg', 'rendered .base.svg'), ('svg_html', 'rendered .svg.html'),
         ('meta', 'rendered meta.json'), ('other', 'other'))
STORED = {'photo': 1.0, 'photo_sm': 1.0, 'photo_th': 1.0, 'raster': 1.0, 'gpx': 0.17}   # share the pack keeps; else 0.40
LIMITS_READ = '2026-10-25'   # the day both pages were last read (docs/DEVELOPING.md, "Yearly upkeep")
LIMITS_URLS = ('https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits',
               'https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github')
LIMITS = (('site', 'published Pages site', '1 GB'), ('history', 'source repository', '1 GB recommended, 5 GB strongly'),
          ('file', 'one file', 'warns over 50 MiB (52.4 MB), blocked over 100 MiB (104.9 MB)'),
          (None, 'deploy-pages timeout', '10 minutes'), (None, 'bandwidth', '100 GB a month, soft'))
_MAP_DIRS = {'rendered', 'map', 'maps'}       # rendered/ in the tree; trips/<slug>/map/ and assets/maps/ in a build
_MAP_KINDS = (('.base.svg', 'base_svg'), ('.svg.html', 'svg_html'), ('/meta.json', 'meta'), ('.webp', 'raster'), ('.png', 'raster'))
_ENTRY = re.compile(r'^\d+ ([0-9a-f]{40,64}) \d\t.*?^  size: (\d+)', re.M | re.S)   # git ls-files -s --debug


def kind(path):
    """The KINDS key of a '/'-separated path, in the checkout or in a build."""
    parts = path.lower().split('/')
    stem, ext = os.path.splitext(parts[-1])
    if ext == '.gpx':
        return 'gpx'
    if ext in ('.webp', '.jpg', '.jpeg', '.png') and 'photos' in parts[:-1]:
        return 'photo_sm' if stem.endswith('.sm') else 'photo_th' if stem.endswith('.th') else 'photo'
    hits = [k for suffix, k in _MAP_KINDS if ('/' + parts[-1]).endswith(suffix)] if _MAP_DIRS.intersection(parts[:-1]) else []
    return hits[0] if hits else 'other'


def tally(sizes):
    kinds = {k: {'files': 0, 'bytes': 0} for k, _label in KINDS}
    for p, b in sizes.items():
        kinds[kind(p)]['files'] += 1
        kinds[kind(p)]['bytes'] += b
    return {'files': len(sizes), 'bytes': sum(sizes.values()), 'kinds': kinds}


def git(root, *args, **kw):
    return subprocess.run(['git', '--no-optional-locks', '-C', root] + list(args), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True, check=True, **kw).stdout


def tracked(root):
    """{path: bytes} of every blob in HEAD, the sizes git ls-tree -r -l HEAD prints."""
    head = {}
    for info, _tab, path in (rec.partition('\t') for rec in git(root, 'ls-tree', '-r', '-z', 'HEAD').split('\0')):
        if info.split()[1:2] == ['blob']:
            head[path] = info.split()[2]
    known = {m.group(1): int(m.group(2)) for m in _ENTRY.finditer(git(root, 'ls-files', '-s', '--debug')) if m.group(2) != '0'}
    ask = sorted(set(head.values()) - set(known))   # staged changes; 0 for an empty file, a racy entry, a fresh read-tree
    for line in git(root, 'cat-file', '--batch-check', input='\n'.join(ask) + '\n').splitlines() if ask else ():
        known[line.split()[0]] = int(line.split()[2])
    return {p: known[sha] for p, sha in head.items()}


def history(root):
    """git count-objects -v in bytes, and the loose objects iCloud offloaded (git sums disk blocks: they count 0)."""
    v = {k: int(x) for k, _s, x in (line.partition(': ') for line in git(root, 'count-objects', '-v').splitlines())}
    objects = os.path.join(root, git(root, 'rev-parse', '--git-dir').strip(), 'objects')
    loose = [os.lstat(os.path.join(objects, d, n)) for d in os.listdir(objects) if re.match(r'^[0-9a-f]{2}$', d)
             for n in os.listdir(os.path.join(objects, d))]
    h = {'loose_objects': v['count'], 'loose_bytes': v['size'] * 1024, 'packed_objects': v['in-pack'], 'packs': v['packs'],
         'pack_bytes': v['size-pack'] * 1024, 'loose_file_bytes': sum(st.st_size for st in loose),
         'offloaded_loose': sum(1 for st in loose if getattr(st, 'st_flags', 0) & 0x40000000)}   # SF_DATALESS (doctor.py)
    h['stored_bytes'] = h['pack_bytes'] + max(h['loose_bytes'], h['loose_file_bytes'])
    return h


def walk(top):
    """({'/'-separated path under top: bytes}, conflict copies left out, symlinks counted as their targets)."""
    sizes, copies, links = {}, 0, 0
    for dirpath, dirs, files in os.walk(top):
        copies += sum(1 for n in dirs + files if sitecheck.conflict_copy(n))
        dirs[:] = sorted(d for d in dirs if not sitecheck.conflict_copy(d))
        for full in (os.path.join(dirpath, f) for f in files if not sitecheck.conflict_copy(f)):
            links += os.path.islink(full)
            st = os.stat(full) if os.path.exists(full) else os.lstat(full)   # stat: no iCloud download, links followed
            sizes[os.path.relpath(full, top).replace(os.sep, '/')] = st.st_size
    return sizes, copies, links


def growth(trips, sizes, site=None):
    """{year or 'undated': row}: each trip's photos, GPX and rendered/trips/<slug> bytes from sizes ({path: bytes} in
    the checkout), the pack they cost (est.) and, given a build's {path: bytes}, the bytes of its trips/<slug>/."""
    by_slug, on_site, rows = {}, {}, {}
    for p, b in sizes.items():
        parts, k = p.split('/'), kind(p)
        col = 'rendered' if parts[0] == 'rendered' else 'photos' if k.startswith('photo') else 'gpx' if k == 'gpx' else None
        if len(parts) > 3 and parts[1] == 'trips' and parts[0] in ('content', 'rendered') and col:
            by_slug.setdefault(parts[2], []).append((col, b, b * STORED.get(k, 0.40)))
    for p, b in (site or {}).items():
        parts = p.split('/')
        if len(parts) > 2 and parts[0] == 'trips':
            on_site[parts[1]] = on_site.get(parts[1], 0) + b
    for t in trips:
        row = rows.setdefault(t['date'].year if t.get('date') else 'undated', dict(
            trips=0, photos=0, gpx=0, rendered=0, tracked=0, pack=0.0, site=None if site is None else 0))
        row['trips'] += 1
        for col, b, stored in by_slug.get(t['slug'], ()):
            row[col], row['tracked'], row['pack'] = row[col] + b, row['tracked'] + b, row['pack'] + stored
        if site is not None:
            row['site'] += on_site.get(t['slug'], 0)
    return rows


def years_to(limit, now, per_year):
    """Years until now bytes reach limit at per_year bytes a year: 0 when already there, None when nothing grows."""
    return 0.0 if now >= limit else (limit - now) / per_year if per_year > 0 else None


def horizons(rows, site_now, pack_now, today):
    """Years to 1 GB for the site and the pack: at the last full calendar year's pace, and at this year's so far."""
    out, day = {}, today.timetuple().tm_yday
    for name, year, days in (('last_full_year', today.year - 1, 365), ('this_year', today.year, day)):
        row = rows.get(year) or {}
        site_rate, pack_rate = (row.get('site') or 0) * 365.0 / days, row.get('pack', 0) * 365.0 / days
        site_years = None if site_now is None else years_to(GB, site_now, site_rate)
        pack_years = None if pack_now is None else years_to(GB, pack_now, pack_rate)
        out[name] = {'year': year, 'days': days, 'site_per_year': int(round(site_rate)), 'pack_per_year': int(round(pack_rate)),
                     'site_years': site_years and round(site_years, 2), 'pack_years': pack_years and round(pack_years, 2)}
    return out


def _lines(r):
    mb, n = (lambda b: '%.1f' % (b / MB)), (lambda i: format(i, ','))   # noqa: E731
    out = ['Size report %s at %s, decimal MB (1 MB = 1,000,000 bytes)' % (r['date'], r['head'] or 'no git repository')]
    for key, title in (('tracked', 'tracked (HEAD, as git ls-tree -r -l HEAD)'), ('site', 'site (%s)' % r['site_dir'])):
        s = r[key]
        out.append('%s: %s files, %s MB' % (title, n(s['files']), mb(s['bytes'])) if s else '%s: not measured' % title)
        out += ['  %-20s %6s files %8s MB' % (lb, n(s['kinds'][k]['files']), mb(s['kinds'][k]['bytes']))
                for k, lb in KINDS] if s else []
        out += ['  %s symlinks counted as their targets (what a copying build ships)' % n(s['links'])] if s and s.get('links') else []
        out += ['  %d iCloud conflict copies left out' % s['copies']] if s and s['copies'] else []
        out += ['  largest file %s MB: %s' % (mb(s['largest']['bytes']), s['largest']['path'])] if s and s.get('largest') else []
    h = r['history']
    if h:
        out += ['history (git count-objects -v): %s MB stored' % mb(h['stored_bytes']),
                '  loose  %6s objects %8s MB on disk' % (n(h['loose_objects']), mb(h['loose_bytes'])),
                '  packed %6s objects %8s MB in %d pack(s)' % (n(h['packed_objects']), mb(h['pack_bytes']), h['packs'])]
        out += ['  %s loose objects are offloaded to iCloud and count 0 on disk; by file size the loose objects are %s MB, '
                'the figure in "stored"' % (n(h['offloaded_loose']), mb(h['loose_file_bytes']))] if h['offloaded_loose'] else []
    out += ['growth by year: each trip\'s photos, GPX and rendered/trips/<slug>; site: its trips/<slug>/ in the build',
            '  %-8s %5s %8s %7s %9s %8s %10s %7s' % ('year', 'trips', 'photos', 'GPX', 'rendered', 'tracked', 'pack est.', 'site')]
    for y in sorted(r['growth'], key=lambda y: (y == 'undated', -int(y) if y != 'undated' else 0)):
        g = r['growth'][y]
        out.append('  %-8s %5d %8s %7s %9s %8s %10s %7s' % (y, g['trips'], mb(g['photos']), mb(g['gpx']), mb(g['rendered']),
                                                         mb(g['tracked']), mb(g['pack']), '-' if g['site'] is None else mb(g['site'])))
    out += ['  grouped by each trip\'s date (a multi-day trip\'s first day), not by commit date: the bulk import landed on one day',
            'GitHub\'s limits (read %s): %s' % (LIMITS_READ, ', '.join(LIMITS_URLS))]
    now = {'site': r['site'] and 'site now %s MB' % mb(r['site']['bytes']), 'history': h and 'now %s MB stored' % mb(h['stored_bytes']),
           'file': r['tracked'] and r['tracked']['largest'] and 'largest now %s MB' % mb(r['tracked']['largest']['bytes'])}
    out += [('  %-22s %-62s %s' % (label, value, now.get(key) or '')).rstrip() for key, label, value in LIMITS]
    for name, what in (('last_full_year', 'the last full year\'s pace (%(year)d'),
                       ('this_year', 'this year\'s pace so far (%(year)d, %(days)d days')):
        z = r['horizons'][name]
        out.append('at %s: site +%s, pack +%s MB a year): site 1 GB in %s, pack 1 GB in %s' % (
            what % z, mb(z['site_per_year']), mb(z['pack_per_year']),
            *('n/a' if v is None else '%.1f years' % v for v in (z['site_years'], z['pack_years']))))
    return out


def main(argv=None, root=None, today=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--site', metavar='DIR', help='the build to measure (default: _site/ in the checkout)')
    ap.add_argument('--json', action='store_true', help='print one JSON object, sizes in bytes')
    a = ap.parse_args(argv)
    root, today = root or ROOT, today or datetime.date.today()
    site_dir = os.path.abspath(a.site) if a.site else os.path.join(root, '_site')
    if a.site and not os.path.isdir(site_dir):
        ap.error('no such folder: %s' % a.site)
    r = {'date': today.isoformat(), 'site_dir': site_dir, 'tracked': None, 'history': None, 'head': None, 'site': None}
    try:
        sizes, r['history'], r['head'] = tracked(root), history(root), git(root, 'rev-parse', '--short', 'HEAD').strip()
        copies = {p for p in sizes if any(sitecheck.conflict_copy(part) for part in p.split('/'))}
        sizes = {p: b for p, b in sizes.items() if p not in copies}
        big = max(sizes, key=sizes.get) if sizes else None
        r['tracked'] = dict(tally(sizes), copies=len(copies), largest=big and {'path': big, 'bytes': sizes[big]})
    except (OSError, subprocess.CalledProcessError):   # no git: the files under content/ and rendered/ stand in
        sizes = {'%s/%s' % (top, p): b for top in ('content', 'rendered') for p, b in walk(os.path.join(root, top))[0].items()}
    site = walk(site_dir) if os.path.isdir(site_dir) else None
    if site:
        r['site'] = dict(tally(site[0]), copies=site[1], links=site[2])
    try:
        trips = content.load_all(include_drafts=True)
    except ValueError as e:                             # content.ContentError: the rest of the report still stands
        print('growth left out: %s' % e, file=sys.stderr)
        trips = []
    rows = growth(trips, sizes, site and site[0])
    r['horizons'] = horizons(rows, r['site'] and r['site']['bytes'], r['history'] and r['history']['stored_bytes'], today)
    r['growth'] = {str(y): dict(g, pack=int(round(g['pack']))) for y, g in rows.items()}
    r['limits'] = {'read': LIMITS_READ, 'urls': list(LIMITS_URLS), 'items': [{'name': lb, 'value': v} for _k, lb, v in LIMITS]}
    print(json.dumps(r, indent=1, sort_keys=True) if a.json else '\n'.join(_lines(r)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
