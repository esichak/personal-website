#!/usr/bin/env python3
"""Make the card-size copies (.th) of cover photos.

A trip card shows its cover in a slot 112 px wide on a phone, but a photo used to come only as an 800 px copy (.sm)
and the full file. The .th copy is 320 px on its short edge (427 x 320 for a 4:3 photo, about 20 KB): the size the
PCT's day photos already had. The build offers it to phones when the file is there (sitegen.core._card_source) and
leaves the card with the other two when it is not, so running this is never required for a build to pass;
`python3 tools/validate.py` says which covers have no copy yet.

  python3 tools/thumbs.py                  # every trip: its cover, where the copy is missing
  python3 tools/thumbs.py SLUG [SLUG ...]  # just these trips
  python3 tools/thumbs.py --all-photos     # every declared photo, not only covers
  python3 tools/thumbs.py --dry-run        # say what would be written, write nothing
  python3 tools/thumbs.py --force          # rewrite copies that exist

It only adds files beside the photos (content/trips/<slug>/photos/<name>.th.webp); no photo, no index.md and nothing
else is changed. New trips do not need it: tools/add_trip.py writes the copy for every photo it imports. Needs cwebp
(brew install webp). After changing a trip's cover_photo, run it for that trip and commit the new file.
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))

import content  # noqa: E402
import photos as photolib  # noqa: E402


def wanted(t, all_photos=False):
    """The photo entries of a loaded trip that should have a .th copy: its cover, or with all_photos every declared
    photo (its own and its days'). Only photos with recorded dimensions qualify: the copy's size is computed from them."""
    if all_photos:
        ps = list(t['photos']) + [p for d in t['days'] for p in d['photos']]
    else:
        ps = [t['cover']['photo']] if t.get('cover') else []
    seen, out = set(), []
    for p in ps:
        if p['file'] not in seen and p.get('w') and p.get('h') and in_photos(p['file']):
            seen.add(p['file'])
            out.append(p)
    return out


def in_photos(file):
    """True for a photo path the build publishes: photos/<name>, nothing above or outside it. content.load_all does not
    refuse an entry such as ../../elsewhere/x.webp (the validator does), and a copy must never be written beside a
    file outside the trip's own photos/ folder."""
    parts = file.split('/') if isinstance(file, str) else []
    return len(parts) == 2 and parts[0] == 'photos' and parts[1] not in ('', '.', '..') and '\\' not in file


def th_path(t, p):
    base, ext = os.path.splitext(p['file'])
    return os.path.join(t['dir'], base + '.th' + ext)


def run(trips, all_photos=False, dry_run=False, force=False, say=print):
    """Make the missing copies for `trips` (loaded trip dicts). Returns (written, existing, skipped): skipped counts the
    photos that are not on disk and the ones the converter could not read."""
    written = existing = missing = 0
    for t in trips:
        for p in wanted(t, all_photos):
            src, dst = os.path.join(t['dir'], p['file']), th_path(t, p)
            rel = os.path.relpath(dst, ROOT)
            if os.path.exists(dst) and not force:
                existing += 1
                continue
            if not os.path.exists(src):
                missing += 1
                say('skipped %s: the photo itself is missing' % rel)
                continue
            tw, th = photolib.thumb_size(p['w'], p['h'])
            if dry_run:
                say('would write %s (%d x %d)' % (rel, tw, th))
            else:
                try:
                    photolib.thumb_copy(src, dst, p['w'], p['h'])
                except (subprocess.CalledProcessError, OSError, ValueError):
                    # a photo the converter cannot read (a truncated file): say so and go on to the next one
                    missing += 1
                    say('skipped %s: the photo could not be converted' % rel)
                    continue
                say('wrote %s (%d x %d, %.0f KB)' % (rel, tw, th, os.path.getsize(dst) / 1024.0))
            written += 1
    return written, existing, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description='Make the card-size (.th) copies of cover photos.')
    ap.add_argument('slugs', nargs='*', help='trip folder names; default: every trip')
    ap.add_argument('--all-photos', action='store_true', help='every declared photo, not only the cover')
    ap.add_argument('--dry-run', action='store_true', help='say what would be written, write nothing')
    ap.add_argument('--force', action='store_true', help='rewrite copies that exist')
    a = ap.parse_args(argv)
    try:
        trips = content.load_all(include_drafts=True)
    except content.ContentError as ex:
        print('ERROR %s' % ex, file=sys.stderr)
        return 1
    if a.slugs:
        by = {t['slug']: t for t in trips}
        unknown = [s for s in a.slugs if s not in by]
        if unknown:
            print('ERROR no trip folder named %s under content/trips/' % ', '.join(unknown), file=sys.stderr)
            return 1
        trips = [by[s] for s in a.slugs]
    if not a.dry_run and not photolib.have_cwebp() and any(p['file'].lower().endswith('.webp') for t in trips for p in wanted(t, a.all_photos)):
        print('ERROR cwebp is not installed (brew install webp)', file=sys.stderr)
        return 1
    written, existing, missing = run(trips, a.all_photos, a.dry_run, a.force)
    print('%s %d card-size cop%s; %d already there%s'
          % ('would write' if a.dry_run else 'wrote', written, 'y' if written == 1 else 'ies', existing,
             ('; %d skipped (photo missing or unreadable)' % missing) if missing else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
