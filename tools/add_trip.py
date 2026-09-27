#!/usr/bin/env python3
"""Add a trip report (or a day of a multi-day trip) from a GPS track or a Strava export.

Examples
  # from a Garmin/any FIT or GPX file, with photos
  python3 tools/add_trip.py ~/Downloads/Morning_Ski.fit --title "Rose Knob Peak" --activity ski \\
      --place "Mount Rose" --region "Lake Tahoe" --photos ~/Desktop/rose/

  # from a Strava bulk export (uses Strava's title, stats, description and photos)
  python3 tools/add_trip.py --strava-export "~/Documents/Outdoors/Strava Export 4:14:26" --strava-id 17094418552

  # add day 3 to an existing multi-day trip
  python3 tools/add_trip.py day3.fit --day-of chamonix-zermatt-haute-route --title "Le Châble → Cabane de Prafleuri"

Then edit content/trips/<slug>/index.md (write-up, place, party, beta, photo alt text), check it locally with
`python3 tools/build.py --serve`, and push. Maps are rendered here (they need the internet); the GitHub
Action only assembles pages. Tracks are published in full (not trimmed); use --strip-times to drop timestamps.
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import frontmatter  # noqa: E402
import photos as photolib  # noqa: E402
import strava  # noqa: E402
import tracks  # noqa: E402

TRIPS = os.path.join(ROOT, 'content', 'trips')
ACTIVITIES = ('ski', 'climb', 'hike', 'mtb', 'other')
PHOTO_EXT = ('.jpg', '.jpeg', '.png', '.heic', '.heif')


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
    out = []
    for p in paths or []:
        p = os.path.expanduser(p)
        if os.path.isdir(p):
            out += sorted(f for f in glob.glob(os.path.join(p, '*')) if f.lower().endswith(PHOTO_EXT))
        elif p.lower().endswith(PHOTO_EXT):
            out.append(p)
    return out


def add_photos(folder, files, prefix='', start=1):
    """Web copies (1600 px + 800 px WebP, upright, no EXIF/GPS). Returns front-matter photo entries."""
    entries = []
    n = start
    for f in files:
        src = f
        tmp = None
        if not f.lower().endswith(('.jpg', '.jpeg')):
            tmp = os.path.join(folder, '.convert.jpg')
            subprocess.run(['sips', '-s', 'format', 'jpeg', f, '--out', tmp], check=True, capture_output=True)
            src = tmp
        name = '%s%02d' % (prefix, n)
        ext, w, h = photolib.web_copies(src, os.path.join(folder, 'photos', name))
        if tmp:
            os.remove(tmp)
        entries.append({'file': 'photos/%s.%s' % (name, ext), 'w': w, 'h': h, 'alt': ''})
        n += 1
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('track', nargs='?', help='.fit, .fit.gz or .gpx file')
    ap.add_argument('--strava-export', help='folder of a Strava bulk export')
    ap.add_argument('--strava-id', help='activity ID in that export')
    ap.add_argument('--title')
    ap.add_argument('--activity', choices=ACTIVITIES)
    ap.add_argument('--subtype', help='for Other: SUP, Rafting, Kayaking, Mountaineering, …')
    ap.add_argument('--place', help='e.g. "Sawtooth Ridge"')
    ap.add_argument('--region', help='e.g. "Eastern Sierra"')
    ap.add_argument('--party', help='who you went with, e.g. "Adam"')
    ap.add_argument('--photos', nargs='*', help='photo files or folders')
    ap.add_argument('--slug')
    ap.add_argument('--day-of', metavar='SLUG', help='append this track as the next day of a multi-day trip')
    ap.add_argument('--timezone', help='IANA zone, e.g. America/Los_Angeles (guessed from the track otherwise)')
    ap.add_argument('--strip-times', action='store_true', help='publish the GPX without timestamps')
    ap.add_argument('--draft', action='store_true', help='keep it off the site until you set draft: false')
    ap.add_argument('--no-render', action='store_true', help='skip map rendering (run tools/render.py later)')
    ap.add_argument('--force', action='store_true', help='overwrite an existing trip folder')
    a = ap.parse_args()

    rec = None
    if a.strava_export:
        if not a.strava_id:
            ap.error('--strava-id is required with --strava-export')
        rec = strava.Export(a.strava_export).by_id(a.strava_id)
        track_path = rec['file']
    else:
        track_path = a.track
    if not track_path or not os.path.exists(os.path.expanduser(track_path)):
        ap.error('need a track file (or --strava-export/--strava-id)')
    pts = tracks.read(os.path.expanduser(track_path))
    if len(pts) < 2:
        sys.exit('no GPS points in ' + track_path)
    start, tz = tracks.local_start(pts, a.timezone)
    simple = tracks.simplify(pts, 2.0)
    stats = strava.stats_from(rec) if rec else tracks.compute_stats(pts)
    title = clean_title(a.title or (rec['name'] if rec else os.path.splitext(os.path.basename(track_path))[0].replace('_', ' ')))
    act, sub = (a.activity, a.subtype)
    if rec and not act:
        act, sub0 = strava.TYPE_MAP.get(rec['type'], ('other', rec['type']))
        sub = sub or sub0
    body = strava.paragraphs(rec['desc']) if rec else ''
    photo_files = (rec['media'] if rec else []) + collect_photos(a.photos)
    photo_files = [f for f in photo_files if f.lower().endswith(PHOTO_EXT)]

    if a.day_of:
        folder = os.path.join(TRIPS, a.day_of)
        if not os.path.exists(os.path.join(folder, 'index.md')):
            sys.exit('no trip %s' % a.day_of)
        n = len(glob.glob(os.path.join(folder, 'days', '*.md'))) + 1
        day = '%02d' % n
        tracks.write_gpx(os.path.join(folder, 'days', day + '.gpx'), simple, title, times=not a.strip_times)
        existing = len(glob.glob(os.path.join(folder, 'photos', '*.jpg')))
        ph = add_photos(folder, photo_files, prefix='d%s-' % day)
        meta = {'title': title, 'date': start.date().isoformat() if start else None,
                'start_time': start.strftime('%H:%M') if start else None, 'stats': stats, 'photos': ph}
        with open(os.path.join(folder, 'days', day + '.md'), 'w') as fh:
            fh.write(frontmatter.render(meta, body))
        print('added day %d to %s (%d photos, %d existing)' % (n, a.day_of, len(ph), existing))
        slug = a.day_of
    else:
        if not act:
            ap.error('--activity is required (ski, climb, hike, mtb or other)')
        slug = a.slug or slugify(title)
        folder = os.path.join(TRIPS, slug)
        if os.path.exists(folder) and not a.force:
            sys.exit('%s already exists (use --slug or --force)' % folder)
        os.makedirs(folder, exist_ok=True)
        tracks.write_gpx(os.path.join(folder, 'track.gpx'), simple, title, kind=act, times=not a.strip_times)
        meta = {
            'title': title, 'activity': act, 'subtype': sub,
            'date': start.date().isoformat() if start else (rec['date_utc'].date().isoformat() if rec else None),
            'start_time': start.strftime('%H:%M') if start else None, 'timezone': tz,
            'place': a.place, 'region': a.region, 'party': a.party,
            'route_shape': tracks.route_shape(pts), 'stats': stats,
            'draft': True if a.draft else None,
            'photos': add_photos(folder, photo_files),
        }
        if not body:
            body = '<!-- Write the trip report here (Markdown). -->'
        with open(os.path.join(folder, 'index.md'), 'w') as fh:
            fh.write(frontmatter.render(meta, body))
        print('created content/trips/%s/ (%d points kept of %d, %d photos)' % (slug, len(simple), len(pts), len(meta['photos'])))
    if not a.no_render:
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'render.py'), slug], check=False)
    print('next: edit content/trips/%s/index.md, then python3 tools/build.py --serve' % slug)


if __name__ == '__main__':
    main()
