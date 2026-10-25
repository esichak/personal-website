#!/usr/bin/env python3
"""Add a trip report (or a day of a multi-day trip) from a GPS track or a Strava export.

Examples
  # from a Garmin/any FIT or GPX file (or Garmin Connect's "Export Original" .zip as it is), with photos
  python3 tools/add_trip.py ~/Downloads/Morning_Ski.fit --title "Rose Knob Peak" --activity ski \\
      --place "Mount Rose" --region "Lake Tahoe" --photos ~/Desktop/rose/

  # from a Strava bulk export (uses Strava's title, stats, description and photos)
  python3 tools/add_trip.py --strava-export "/path/to/Strava export folder" --strava-id 1234567890

  # the activities of that export that are on no trip yet (prints only; creates nothing)
  python3 tools/add_trip.py --strava-export "/path/to/Strava export folder" --list --type Hike,Ride --since 2026-01-01

  # add day 3 to an existing multi-day trip
  python3 tools/add_trip.py day3.fit --day-of chamonix-zermatt-haute-route --title "Le Châble → Cabane de Prafleuri"

  # set a trip's time zone and work its date and start time out again from its own track.gpx (offline)
  python3 tools/add_trip.py --retime rose-knob-peak --timezone America/Chicago

  # a better recording of a trip that is on the site: new track, date, start time, route shape and stats; the write-up,
  # photos and every other line stay as they are (--dry-run shows the change to index.md first)
  python3 tools/add_trip.py better.fit --update rose-knob-peak --dry-run

Then edit content/trips/<slug>/index.md (write-up, place, party, beta, photo alt text), check it locally with
`python3 tools/build.py --serve --open <slug>`, and push. Maps are rendered here (they need the internet); the GitHub
Action only assembles pages. Tracks are published in full (not trimmed); use --strip-times to drop timestamps.
"""
import argparse
import difflib
import glob
import os
import re
import subprocess
import sys
import unicodedata
import zipfile
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import frontmatter  # noqa: E402
import photos as photolib  # noqa: E402
import strava  # noqa: E402
import tracks  # noqa: E402

TRIPS = os.path.join(ROOT, 'content', 'trips')
ACTIVITIES = ('ski', 'climb', 'hike', 'mtb', 'other')
PHOTO_EXT = photolib.PHOTO_EXT
PLACEHOLDER = '<!-- Write the trip report here (Markdown). -->'
PUBLISHED_AT = object()   # marks the published_at: line an import writes empty
# index.md lines an import never writes with a value: their presence means someone worked on the trip, and --force would drop them
KEPT_KEYS = ('beta', 'map', 'cover_photo', 'cover_focal_x', 'cover_focal_y', 'card_summary', 'featured', 'search_aliases',
             'published_at', 'updated_at', 'region_days', 'journal_highlights', 'kind', 'end_date', 'summits',
             'conditions')   # conditions: retired, but the words in it are still someone's (CONTENT_GUIDE 7.12)
_DAY_PHOTO = re.compile(r'^d\d+-\d+\.(?:webp|jpg)$')   # a day's full-size photo; the .sm / .th copies do not count


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r"[’']", '', s.lower())
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:60].strip('-') or 'trip'


def clean_title(s):
    # drop emoji and pictographs from titles (write-ups keep them)
    s = ''.join(ch for ch in s if not (unicodedata.category(ch) == 'So' or 0x1F000 <= ord(ch) <= 0x1FFFF))
    s = re.sub(r'\s*-\s+', ' – ', s)  # "Matterhorn Peak- West Couloir" -> "Matterhorn Peak – West Couloir"
    return re.sub(r'\s+', ' ', s).strip()


def collect_photos(paths):
    return photolib.collect(paths)


def add_photos(folder, files, prefix='', start=1):
    """Web copies of the photos into the trip folder (photos.import_photos, shared with tools/trip_photos.py)."""
    return photolib.import_photos(folder, files, prefix, start)


def day_photo_count(folder):
    """The day photos a trip already has (photos/dNN-MM.webp, or .jpg where cwebp was missing), copies not counted."""
    try:
        return sum(1 for f in os.listdir(os.path.join(folder, 'photos')) if _DAY_PHOTO.match(f))
    except OSError:
        return 0


def day_notes(folder, day):
    """What the author still has to type after a day was added to a trip, as plain sentences: the build would stop on
    either (python3 tools/validate.py says the same), so say it now. A trip with day files needs `kind: multi-day` (or
    `series`) in its index.md; and in a trip whose other days carry a `day:` label (the PCT: its labels do not follow
    the file order) the new day needs one no other day has, or it takes its position and may collide."""
    notes = []
    try:
        with open(os.path.join(folder, 'index.md'), encoding='utf-8') as fh:
            meta, _body = frontmatter.split(fh.read())
        if meta.get('kind') not in ('multi-day', 'series'):
            notes.append('index.md has no `kind: multi-day` line; a trip with day files needs it (and `end_date:` for its last day)')
        labelled = 0
        for f in glob.glob(os.path.join(folder, 'days', '*.md')):
            if os.path.basename(f) == day + '.md':
                continue
            with open(f, encoding='utf-8') as fh:
                dm, _db = frontmatter.split(fh.read())
            labelled += 1 if dm.get('day') not in (None, '') else 0
        if labelled:
            notes.append('the other days carry a `day:` label; add one to days/%s.md that no other day has' % day)
    except (OSError, ValueError):
        pass   # unreadable front matter is the build's to report, with the file named
    return notes


def _plural(n, word):
    return '%d %s%s' % (n, word, '' if n == 1 else 's')


def _and(items):
    return items[0] if len(items) == 1 else '%s and %s' % (', '.join(items[:-1]), items[-1])


def force_refusal(folder, slug):
    """Why --force must not overwrite this trip folder, or None. --force rebuilds index.md from the track and the flags
    and numbers photos from 01, so it may only replace a folder that holds no index.md or an untouched import (the
    placeholder body or none, empty alt lines, no line an import does not write, no day files, no goal.json)."""
    where = 'content/trips/%s' % slug
    move = ('For a better recording use --update %s instead; to import from scratch, move the folder out of '
            'content/trips/ first (git keeps the old one: git checkout -- %s restores it).' % (slug, where))
    lost, extra = [], []      # (what, is it plural): what the import would drop, from index.md and from the folder
    index = os.path.join(folder, 'index.md')
    if os.path.exists(index):
        try:
            with open(index, encoding='utf-8') as fh:
                meta, body = frontmatter.split(fh.read())
        except (OSError, UnicodeDecodeError, ValueError) as ex:
            return ('%s/index.md cannot be read (%s), so --force cannot tell what it would erase. %s' % (where, ex, move))
        if body.strip() not in ('', PLACEHOLDER):
            lost.append(('a write-up', False))
        alts = sum(1 for p in (meta.get('photos') or []) if isinstance(p, dict) and str(p.get('alt') or '').strip())
        if alts:
            lost.append((_plural(alts, 'photo description'), alts > 1))
        keys = [k for k in KEPT_KEYS if meta.get(k) not in (None, '')]     # an empty line holds nothing to lose
        if meta.get('source') not in (None, '', 'Strava'):                  # Strava is what an export import writes
            keys.append('source')
        if keys:
            lost.append(('the %s line%s' % (_and(keys), 's' if len(keys) > 1 else ''), len(keys) > 1))
    if os.path.isdir(os.path.join(folder, 'days')):
        extra.append(('day files (days/)', True))
    if os.path.exists(os.path.join(folder, 'goal.json')):
        extra.append(('a goal.json (a tick-list goal)', False))
    if not lost and not extra:
        return None
    said = []
    if lost:
        said.append('%s/index.md has %s' % (where, _and([w for w, _ in lost])))
    if extra:
        said.append(('the folder holds %s' if lost else where + '/ holds %s') % _and([w for w, _ in extra]))
    items = lost + extra
    return '%s; --force would erase %s. %s' % (' and '.join(said), 'it' if len(items) == 1 and not items[0][1] else 'them', move)


def known_regions(trips_dir):
    """{region name: number of trips} as the trips' index.md files spell them, drafts and goals included. A file that
    does not read is skipped: the validator names it."""
    names = {}
    for f in sorted(glob.glob(os.path.join(trips_dir, '*', 'index.md'))):
        try:
            with open(f, encoding='utf-8') as fh:
                region = frontmatter.split(fh.read())[0].get('region')
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if isinstance(region, str) and region.strip():
            names[region] = names.get(region, 0) + 1
    return names


def region_problem(region, names):
    """A usage error for a second spelling of an existing region ('eastern sierra' beside 'Eastern Sierra'), or None. The
    slug is content.slugify, the one the validator, the filters and the region pages use."""
    rslug = content.slugify(region)
    same = sorted(((n, c) for n, c in names.items() if content.slugify(n) == rslug and n != region), key=lambda x: (-x[1], x[0]))
    if same and region not in names:
        name, count = same[0]
        return 'region "%s" is written "%s" on %s; use that spelling' % (region, name, _plural(count, 'trip'))
    return None


def known_strava_ids(trips_dir):
    """The strava_id of every index.md and days/NN.md: the activities that are already on a trip or a day."""
    ids = set()
    for f in glob.glob(os.path.join(trips_dir, '*', 'index.md')) + glob.glob(os.path.join(trips_dir, '*', 'days', '*.md')):
        try:
            with open(f, encoding='utf-8') as fh:
                sid = frontmatter.split(fh.read())[0].get('strava_id')
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if sid not in (None, ''):
            ids.add(str(sid))
    return ids


def list_strava(export, types, since):
    """Print the export's activities that are on no trip or day, newest first; nothing is written."""
    want = {t.strip().lower() for t in types.split(',') if t.strip()} if types else None
    recs = export.not_imported(known_strava_ids(TRIPS))
    shown = [r for r in recs if (want is None or r['type'].lower() in want) and (since is None or r['date_utc'].date() >= since)]
    for r in shown:
        km = '%.1f km' % (r['distance_m'] / 1000.0) if r['distance_m'] else '-'
        print('%s  %-12s  %-20s %9s  %-6s  %s' % (r['date_utc'].date().isoformat(), r['id'], r['type'][:20], km,
                                                 'photos' if r['media'] else '', r['name']))
    print('%d %s not on the site%s (of %d in the export)' % (len(shown), 'activity' if len(shown) == 1 else 'activities',
                                                            ' with these filters' if (want or since) else '', len(export.rows)))
    if export.skipped:
        print('%s of activities.csv could not be read (no date in the form Strava writes) and %s left out'
              % (_plural(export.skipped, 'row'), 'is' if export.skipped == 1 else 'are'))
    print('add one: python3 tools/add_trip.py --strava-export "<the same folder>" --strava-id <id>')
    return 0


def rewritten(path, updates):
    """(the file's text, its text with these top-level front-matter keys set, {key: old value}) through the frontmatter
    round trip, which gives every content file back byte for byte; a file it would change otherwise (a comment inside
    the block, a hand-made layout) raises ValueError. A key not there yet is added at the end of the block; the others
    keep their place."""
    with open(path, encoding='utf-8') as fh:
        text = fh.read()
    meta, body = frontmatter.split(text)
    if frontmatter.render(meta, body, keep_empty=True) != text:
        raise ValueError('%s would change in more places than these lines when it is written back (a comment or an '
                         'unusual layout in its front matter); edit it by hand' % os.path.relpath(path, ROOT))
    old = {k: meta.get(k) for k in updates}
    meta.update(updates)
    return text, frontmatter.render(meta, body, keep_empty=True), old


def rewrite_keys(path, updates):
    """Set top-level front-matter keys of `path` (rewritten); returns {key: old value}."""
    _text, new, old = rewritten(path, updates)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(new)
    return old


def _as_day(v):
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v), '%Y-%m-%d').date()
    except ValueError:
        return None


def bump_end_date(folder, day_date):
    """After --day-of: when index.md states an end_date earlier than the new day, move it to the day's date (the page's
    date range follows that line). No end_date line: none is written (the page ends on the last day file's date)."""
    index = os.path.join(folder, 'index.md')
    try:
        with open(index, encoding='utf-8') as fh:
            meta = frontmatter.split(fh.read())[0]
    except (OSError, UnicodeDecodeError, ValueError):
        return    # the build names the file
    end = _as_day(meta.get('end_date'))
    if day_date is None or end is None or end >= day_date:
        return
    try:
        rewrite_keys(index, {'end_date': day_date.isoformat()})
        print('end_date %s -> %s (index.md)' % (end.isoformat(), day_date.isoformat()))
    except ValueError as ex:
        print('note: end_date in index.md is %s, before this day (%s), and was not changed: %s'
              % (end.isoformat(), day_date.isoformat(), ex))


def zone_problem(name):
    """Why `name` is not a time zone this Python can use, or None."""
    if tracks.ZoneInfo is None:
        return None
    try:
        tracks.ZoneInfo(name)
    except (KeyError, ValueError, OSError):   # not found: KeyError; malformed: ValueError; a folder ('America') on 3.9: OSError
        return '--timezone %s: not a time zone name (an IANA name such as America/Chicago)' % name
    return None


def retime(ap, slug, zone):
    """--retime: timezone, date and start_time of a single-day trip worked out again from its own track.gpx, which keeps
    the UTC time of every fix. None of the three is in the render hash, so no map is drawn again."""
    folder = os.path.join(TRIPS, slug)
    where = 'content/trips/%s' % slug
    index = os.path.join(folder, 'index.md')
    if not os.path.exists(index):
        ap.error('--retime %s: no %s/index.md' % (slug, where))
    if os.path.isdir(os.path.join(folder, 'days')):
        print('%s has day files: --retime works on a single-day trip, whose own track.gpx has the times; change the day '
              'files by hand' % where, file=sys.stderr)
        return 1
    gpx = os.path.join(folder, 'track.gpx')
    if not os.path.exists(gpx):
        print('%s has no track.gpx, so there are no recorded times to work from' % where, file=sys.stderr)
        return 1
    try:
        with open(index, encoding='utf-8') as fh:
            meta = frontmatter.split(fh.read())[0]
        pts = tracks.read(gpx)
    except Exception as ex:   # noqa: BLE001 — one line naming the file, never a traceback
        print('%s cannot be read (%s: %s)' % (where, type(ex).__name__, ex), file=sys.stderr)
        return 1
    if not zone and isinstance(meta.get('timezone'), str) and meta['timezone'].strip():
        zone = meta['timezone'].strip()
        if zone_problem(zone):
            print('%s/index.md says timezone: %s, which is not a time zone name; give --timezone (an IANA name such as '
                  'America/Chicago)' % (where, zone), file=sys.stderr)
            return 1
    start, tz = tracks.local_start(pts, zone)
    if start is None:
        print('%s/track.gpx has no timestamps (imported with --strip-times?): nothing to work the start out from'
              % where, file=sys.stderr)
        return 1
    new = {'timezone': tz, 'date': start.date().isoformat(), 'start_time': start.strftime('%H:%M')}
    try:
        old = rewrite_keys(index, new)
    except ValueError as ex:
        print(str(ex), file=sys.stderr)
        return 1
    for k in ('timezone', 'date', 'start_time'):
        was = '' if old[k] is None else str(old[k])
        print('%-10s %s -> %s%s' % (k, was or '(none)', new[k], '' if was != new[k] else ' (unchanged)'))
    print('%s/index.md updated; no render needed (python3 tools/build.py --serve --open %s to look)' % (where, slug))
    return 0


def update(ap, a):
    """--update SLUG: a better recording of a single-day trip that is on the site. The track is replaced, and the lines
    worked out from it (date, start_time, route_shape, stats unless --keep-stats; timezone only with --timezone, the
    trip's own line winning otherwise) are set in index.md through the round trip; every other line and the write-up
    stay byte for byte. The maps are drawn again unless --no-render: the track's bytes are in the render hash."""
    slug = a.update
    folder, where = os.path.join(TRIPS, slug), 'content/trips/%s' % slug
    index = os.path.join(folder, 'index.md')
    if not os.path.exists(index):
        ap.error('--update %s: no %s/index.md (an existing trip\'s folder name; a new trip needs no --update)' % (slug, where))
    if a.strip_times:
        ap.error('--update keeps the timestamps of the new track (--strip-times is for a new import)')
    if os.path.isdir(os.path.join(folder, 'days')):
        print('%s has day files: --update replaces the track of a single-day trip; replace a day\'s NN.gpx and its '
              'lines by hand' % where, file=sys.stderr)
        return 1
    for flag, given in (('--title', a.title), ('--activity', a.activity), ('--subtype', a.subtype), ('--place', a.place),
                        ('--region', a.region), ('--party', a.party), ('--photos', a.photos), ('--slug', a.slug),
                        ('--draft', a.draft), ('--force', a.force), ('--strava-export', a.strava_export),
                        ('--strava-id', a.strava_id)):
        if given:
            ap.error('%s does not go with --update, which keeps every line but the ones the track decides: change them in '
                     '%s/index.md (more photos: tools/trip_photos.py)' % (flag, where))
    if a.keep_stats and a.source:
        ap.error("--source does not go with --keep-stats: the figures stay the old recording's, and so does its source")
    if not a.track or not os.path.exists(os.path.expanduser(a.track)):
        ap.error('--update needs the new track file: python3 tools/add_trip.py TRACK --update %s' % slug)
    try:
        with open(index, encoding='utf-8') as fh:
            meta = frontmatter.split(fh.read())[0]
        pts = tracks.read(os.path.expanduser(a.track))
    except Exception as ex:   # noqa: BLE001 — one line naming the file, never a traceback
        print('cannot read %s or %s/index.md (%s: %s)' % (a.track, where, type(ex).__name__, ex), file=sys.stderr)
        return 1
    if len(pts) < 2:
        print('no GPS points in ' + a.track, file=sys.stderr)
        return 1
    if meta.get('kind') == 'planned':
        print('%s is a planned route (a tick-list goal): --update is for a report; tools/ticklist.py changes a goal'
              % where, file=sys.stderr)
        return 1
    try:
        old_pts = tracks.read(os.path.join(folder, 'track.gpx')) if os.path.exists(os.path.join(folder, 'track.gpx')) else []
    except Exception:   # noqa: BLE001 — a damaged old file is being replaced; it has nothing to keep
        old_pts = []
    if old_pts and all(p[3] is None for p in old_pts):
        print('%s/track.gpx has no timestamps (imported with --strip-times), and --update writes the new file with its '
              "times; take the times out of the new file first, or wait for decision 2 of docs/PRIVACY_NOTES.md" % where,
              file=sys.stderr)
        return 1
    # the stats note names a service: figures from another recording must not go out under the old one's name
    named = [k for k in ('source', 'strava_id') if meta.get(k) not in (None, '')]
    if named and not a.keep_stats and not a.source:
        print('%s/index.md says where its stats come from (%s), and the new file\'s figures would be shown under that '
              'name: give --source %s for where the new recording came from, or keep the old figures with --keep-stats'
              % (where, ' and '.join(k + ':' for k in named), '|'.join(content.SOURCES)), file=sys.stderr)
        return 1
    zone = a.timezone
    if not zone and isinstance(meta.get('timezone'), str) and meta['timezone'].strip() and not zone_problem(meta['timezone'].strip()):
        zone = meta['timezone'].strip()
    start, tz = tracks.local_start(pts, zone)
    updates = {'route_shape': tracks.route_shape(pts)}
    if start is not None:
        updates.update({'date': start.date().isoformat(), 'start_time': start.strftime('%H:%M'), 'timezone': tz})
    if not a.keep_stats:
        updates['stats'] = tracks.compute_stats(pts)
    if a.source:
        updates['source'] = a.source
    try:
        before, after, old = rewritten(index, updates)
    except ValueError as ex:
        print(str(ex), file=sys.stderr)
        return 1
    simple = tracks.simplify(pts, 2.0)
    if a.dry_run:
        sys.stdout.writelines(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                   where + '/index.md', where + '/index.md (updated)'))
        print('would write %s/index.md and %s/track.gpx (%d points kept of %d)%s'
              % (where, where, len(simple), len(pts), '' if a.no_render else ', then draw its maps again'))
        print('dry run: nothing written')
        return 0
    with open(index, 'w', encoding='utf-8') as fh:
        fh.write(after)
    tracks.write_gpx(os.path.join(folder, 'track.gpx'), simple, meta.get('title') or slug, kind=meta.get('activity'), times=True)
    for k in updates:
        was = old[k]
        print('%-11s %s' % (k, 'changed' if was != updates[k] else 'unchanged'))
    print('updated %s/index.md and %s/track.gpx (%d points kept of %d); the write-up, photos and other lines are as '
          'they were' % (where, where, len(simple), len(pts)))
    try:
        import checks
        for f in checks.run(TRIPS):
            if f['file'].startswith(where + '/') and f['level'] != 'note':
                print(checks.line(f))
    except Exception as ex:   # noqa: BLE001 — the check is a courtesy here; build.py runs it again
        print('the content check could not run (%s); python3 tools/validate.py' % ex)
    if a.no_render:
        print('maps not drawn: python3 tools/render.py %s (the new track is in the render hash)' % slug)
    else:
        print('drawing the maps again: the track\'s bytes are in the render hash')
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'render.py'), slug], check=False)
    print('Publish: python3 tools/publish.py %s --push (ADDING-TRIPS.md, step 5)' % slug)
    return 0


def checklist(slug, edit, alt_empty, draft, rendered, strava_body):
    """The steps left after an import, numbered, in the order ADDING-TRIPS.md gives them."""
    f = 'content/trips/%s/%s' % (slug, edit)
    if edit.startswith('days/'):
        steps = ['Edit %s: %s' % (f, "the Strava description is the day's entry under the closing ---: read it over"
                                  if strava_body else "write the day's entry under the closing ---")]
    else:
        steps = ['Edit %s: %s, and check place, region and party' % (
            f, 'the Strava description is the report under the closing ---: read it over' if strava_body
            else 'write the report under the closing ---')]
    if alt_empty:
        steps.append('Describe the photos: %d alt: %s empty (alt: "Two skiers skin up a ridge.")'
                     % (alt_empty, 'line is' if alt_empty == 1 else 'lines are'))
    steps.append('Optional: beta: rows, and map: peaks: [...] to label summits (peaks need python3 tools/render.py %s again)' % slug)
    if not rendered and not draft:
        steps.append('Draw the maps (internet needed): python3 tools/render.py %s' % slug)
    steps.append('Preview: python3 tools/build.py --serve --open %s' % slug)
    if draft:
        steps.append('Publish as a draft (ADDING-TRIPS.md, step 5): python3 tools/publish.py %s --push' % slug)
    else:
        steps.append('Publish (ADDING-TRIPS.md, step 5): python3 tools/publish.py %s --push (--dry-run first lists what '
                     'it would commit)' % slug)
    print('Next steps:')
    for i, s in enumerate(steps, 1):
        print('  %d. %s' % (i, s))


def render_status(slug):
    """render.py --status for the trip: what is still to draw, read from content/ and rendered/ only. Its exit status:
    0 when nothing is left to draw."""
    return subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'render.py'), '--status', slug], check=False).returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('track', nargs='?', help='.fit, .fit.gz or .gpx file, or a .zip that holds one (Garmin "Export Original")')
    ap.add_argument('--strava-export', help='folder of a Strava bulk export')
    ap.add_argument('--strava-id', help='activity ID in that export')
    ap.add_argument('--list', action='store_true', help='with --strava-export: list the activities on no trip yet, then stop')
    ap.add_argument('--type', help='with --list: only these Strava types, comma-separated (Hike,Ride)')
    ap.add_argument('--since', help='with --list: only activities on or after this date (YYYY-MM-DD)')
    ap.add_argument('--title')
    ap.add_argument('--activity', choices=ACTIVITIES)
    ap.add_argument('--subtype', choices=content.OTHER_SUBTYPES, help='for Other: %s' % ', '.join(content.OTHER_SUBTYPES))
    ap.add_argument('--place', help='e.g. "Sawtooth Ridge"')
    ap.add_argument('--region', help='e.g. "Eastern Sierra" (an existing region must be spelt as the site spells it)')
    ap.add_argument('--party', help='who you went with, e.g. "Adam"')
    ap.add_argument('--photos', nargs='*', help='photo files or folders')
    ap.add_argument('--slug')
    ap.add_argument('--day-of', metavar='SLUG', help='append this track as the next day of a multi-day trip')
    ap.add_argument('--retime', metavar='SLUG', help="work a trip's date and start time out again from its track.gpx "
                                                     '(with --timezone to change the zone)')
    ap.add_argument('--timezone', help='IANA zone, e.g. America/Los_Angeles (guessed from the track otherwise)')
    ap.add_argument('--strip-times', action='store_true', help='publish the GPX without timestamps')
    ap.add_argument('--draft', action='store_true', help='keep it off the site until you set draft: false')
    ap.add_argument('--no-render', action='store_true', help='skip map rendering (run tools/render.py later)')
    ap.add_argument('--force', action='store_true', help='rewrite index.md of an existing trip folder that is still an '
                                                         'untouched import (refused once it has a write-up, alt text or other '
                                                         'edits; for a trip on the site see --update and ADDING-TRIPS.md, '
                                                         '"Changing a trip that is on the site")')
    ap.add_argument('--update', metavar='SLUG', help="a better recording of a trip on the site: replace its track and the "
                                                     "lines worked out from it, keep the write-up, photos and the rest")
    ap.add_argument('--keep-stats', action='store_true', help='with --update: keep the stats block as it is')
    ap.add_argument('--dry-run', action='store_true', help='with --update: print the change to index.md; write nothing')
    ap.add_argument('--source', choices=content.SOURCES,
                    help='the service the recording came through, named in the stats note (written as source:); an '
                         'import from a Strava export is Strava')
    a = ap.parse_args(argv)

    if a.timezone:
        why = zone_problem(a.timezone)
        if why:
            ap.error(why)
    # before any branch, so that no command takes an option it would ignore (--retime --dry-run would write)
    if (a.keep_stats or a.dry_run) and not a.update:
        ap.error('--keep-stats and --dry-run go with --update')
    if a.source and (a.retime or a.day_of or a.list):
        ap.error("--source goes with a new trip or --update (a day file has no source: line; the trip's index.md has it)")
    if a.retime:
        return retime(ap, a.retime, a.timezone)
    if a.update:
        return update(ap, a)

    rec = None
    if a.strava_export:
        try:
            export = strava.Export(a.strava_export)
        except FileNotFoundError:
            ap.error('--strava-export %s: no activities.csv in that folder (give the unzipped Strava export folder)' % a.strava_export)
        if a.list:
            since = None
            if a.since:
                since = _as_day(a.since)
                if since is None:
                    ap.error('--since %s: write the date as YYYY-MM-DD' % a.since)
            return list_strava(export, a.type, since)
        if not a.strava_id:
            ap.error('--strava-id is required with --strava-export (or --list to see the activities)')
        if a.source and a.source != 'Strava':
            ap.error('--source %s: the stats of an import from a Strava export are Strava\'s' % a.source)
        try:
            rec = export.by_id(a.strava_id)
        except KeyError:
            ap.error('--strava-id %s: no such activity in %s/activities.csv' % (a.strava_id, a.strava_export))
        track_path = rec['file']
    else:
        if a.list:
            ap.error('--list needs --strava-export (the folder that holds activities.csv)')
        track_path = a.track

    act, sub = (a.activity, a.subtype)
    if rec and not act:
        act, sub0 = strava.TYPE_MAP.get(rec['type'], ('other', rec['type']))
        sub = sub or sub0
    if act == 'other' and sub is not None and sub not in content.OTHER_SUBTYPES and not a.day_of:
        # the Strava type maps to a sub-type the site has no word, icon or menu row for
        ap.error('the Strava type "%s" gives the sub-type "%s", which the site does not have (%s): give --activity, or '
                 '--subtype with one of those' % (rec['type'] if rec else '', sub, ', '.join(content.OTHER_SUBTYPES)))
    if a.region and not a.day_of:
        names = known_regions(TRIPS)
        why = region_problem(a.region, names)
        if why:
            ap.error(why)
        if a.region not in names:
            print('new region: %s (existing: %s)' % (a.region, ', '.join(sorted(names, key=lambda n: (-names[n], n))) or 'none'))

    if not track_path or not os.path.exists(os.path.expanduser(track_path)):
        ap.error('need a track file (or --strava-export/--strava-id)')
    try:
        pts = tracks.read(os.path.expanduser(track_path))
    except (ValueError, zipfile.BadZipFile) as ex:
        ap.error('%s: %s' % (track_path, ex))
    except Exception as ex:   # noqa: BLE001 — a damaged file (bad XML, a broken .gz, a folder): one line, never a traceback
        ap.error('%s: cannot be read as a track (%s: %s)' % (track_path, type(ex).__name__, ex))
    if len(pts) < 2:
        print('no GPS points in ' + track_path, file=sys.stderr)
        return 1
    start, tz = tracks.local_start(pts, a.timezone)
    if start is not None:
        print('timezone %s, %s' % (tz, 'from --timezone' if a.timezone else 'guessed; --timezone to change'))
    simple = tracks.simplify(pts, 2.0)
    stats = strava.stats_from(rec) if rec else tracks.compute_stats(pts)
    title = clean_title(a.title or (rec['name'] if rec else os.path.splitext(os.path.basename(track_path))[0].replace('_', ' ')))
    if not a.title and strava.default_title(title):
        print('note: the title "%s" looks like one Strava gives an activity by itself; pass --title with the name of '
              'the trip (the folder name is the address, so a title can also be changed later in index.md)' % title)
    body = strava.paragraphs(rec['desc']) if rec else ''
    photo_files = (rec['media'] if rec else []) + collect_photos(a.photos)
    photo_files = [f for f in photo_files if f.lower().endswith(PHOTO_EXT)]

    if a.day_of:
        folder = os.path.join(TRIPS, a.day_of)
        if not os.path.exists(os.path.join(folder, 'index.md')):
            print('no trip %s' % a.day_of, file=sys.stderr)
            return 1
        n = len(glob.glob(os.path.join(folder, 'days', '*.md'))) + 1
        day = '%02d' % n
        tracks.write_gpx(os.path.join(folder, 'days', day + '.gpx'), simple, title, times=not a.strip_times)
        existing = day_photo_count(folder)
        ph = add_photos(folder, photo_files, prefix='d%s-' % day)
        meta = {'title': title, 'date': start.date().isoformat() if start else None,
                'start_time': start.strftime('%H:%M') if start else None, 'stats': stats, 'photos': ph}
        with open(os.path.join(folder, 'days', day + '.md'), 'w', encoding='utf-8') as fh:
            fh.write(frontmatter.render(meta, body))
        print('added day %d to %s (%d photos, %d existing)' % (n, a.day_of, len(ph), existing))
        slug = a.day_of
        bump_end_date(folder, start.date() if start else None)
        for note in day_notes(folder, day):
            print('note: ' + note)
        edit = 'days/%s.md' % day
        draft = False
        try:
            with open(os.path.join(folder, 'index.md'), encoding='utf-8') as fh:
                draft = frontmatter.split(fh.read())[0].get('draft') is True
        except (OSError, UnicodeDecodeError, ValueError):
            pass
    else:
        if not act:
            ap.error('--activity is required (ski, climb, hike, mtb or other)')
        slug = a.slug or slugify(title)
        folder = os.path.join(TRIPS, slug)
        if os.path.exists(folder):
            if not a.force:
                print('%s already exists (use --slug or --force)' % folder, file=sys.stderr)
                return 1
            why = force_refusal(folder, slug)
            if why:
                print(why, file=sys.stderr)
                return 1
            mine = [f for f in ('index.md', 'track.gpx') if os.path.exists(os.path.join(folder, f))]
            names = {'%02d' % i for i in range(1, len(photo_files) + 1)}
            shots = sorted(os.listdir(os.path.join(folder, 'photos'))) if os.path.isdir(os.path.join(folder, 'photos')) else []
            over = [f for f in shots if f.split('.')[0] in names]
            left = [f for f in shots if f.split('.')[0] not in names]
            print('--force: content/trips/%s/ is an untouched import; overwriting %s'
                  % (slug, _and(mine + (['photos/' + f for f in over] if over else [])) if (mine or over) else 'nothing (no index.md)'))
            if left:
                print('  left in photos/ from the earlier import, declared nowhere: %s (delete them)' % ', '.join(left))
        os.makedirs(folder, exist_ok=True)
        tracks.write_gpx(os.path.join(folder, 'track.gpx'), simple, title, kind=act, times=not a.strip_times)
        meta = {
            'title': title, 'activity': act, 'subtype': sub,
            'date': start.date().isoformat() if start else (rec['date_utc'].date().isoformat() if rec else None),
            'start_time': start.strftime('%H:%M') if start else None, 'timezone': tz,
            'place': a.place, 'region': a.region, 'party': a.party,
            'route_shape': tracks.route_shape(pts), 'stats': stats,
            # the service the stats note names (content.stats_source): a FIT or GPX file does not say which one it
            # was, so only --source names it
            'source': a.source or ('Strava' if rec else None),
            'draft': True if a.draft else None,
            'published_at': PUBLISHED_AT,
            'photos': add_photos(folder, photo_files),
        }
        ph = meta['photos']
        if not body:
            body = PLACEHOLDER
        # an empty published_at: line to fill on the day the report goes online (ADDING-TRIPS.md, step 5); every other
        # absent value is left out
        meta = dict((k, None if v is PUBLISHED_AT else v) for k, v in meta.items() if v is not None)
        with open(os.path.join(folder, 'index.md'), 'w', encoding='utf-8') as fh:
            fh.write(frontmatter.render(meta, body, keep_empty=True))
        print('created content/trips/%s/ (%d points kept of %d, %d photos)' % (slug, len(simple), len(pts), len(ph)))
        edit = 'index.md'
        draft = bool(a.draft)
    rendered = False
    if a.no_render:
        print('maps not drawn: python3 tools/render.py %s' % slug)
    else:
        drawn = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'render.py'), slug], check=False)
        # drawn only when the render went through and --status has nothing left to draw: a meta.json from an earlier
        # render can still be there after a failed one (--day-of, a re-import)
        rendered = drawn.returncode == 0 and render_status(slug) == 0
    checklist(slug, edit, sum(1 for p in ph if not p.get('alt')), draft, rendered, bool(rec and rec.get('desc')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
