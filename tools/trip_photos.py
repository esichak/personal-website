#!/usr/bin/env python3
"""Add photos to a trip that is already on the site.

  python3 tools/trip_photos.py rose-knob-peak ~/Desktop/more/            # a folder of photos, or files
  python3 tools/trip_photos.py haute-route day3.heic --day 3             # to a day of a multi-day trip (days/03.md)
  python3 tools/trip_photos.py rose-knob-peak best.jpg --cover           # ... and make the first one the cover
  python3 tools/trip_photos.py rose-knob-peak ~/Desktop/more/ --dry-run  # the files and lines it would write; writes nothing

The photos get the copies an import makes (1600 px, 800 px and card-size WebP, upright, no EXIF or GPS; HEIC and PNG
through sips), numbered after the highest photo the trip (or the day, as dNN-MM) already has, and an entry each under
photos: of index.md (or days/NN.md) with its size and an empty alt: line to fill. --cover sets cover_photo: in index.md
to the first one. No render is needed: stage the trip's folder (ADDING-TRIPS.md, "Changing a trip that is on the site").
Removing a photo is still done by hand: delete its three files and its entry.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import frontmatter  # noqa: E402
import photos as photolib  # noqa: E402

TRIPS = os.path.join(ROOT, 'content', 'trips')


def read_md(path):
    """(meta, body) of a content file, refused (ValueError) when writing it back would change more than its photos."""
    with open(path, encoding='utf-8') as fh:
        text = fh.read()
    meta, body = frontmatter.split(text)
    if frontmatter.render(meta, body, keep_empty=True) != text:
        raise ValueError('%s would change in more places than its photos: lines when written back (a comment or an unusual '
                         'layout in its front matter); add the photos by hand' % os.path.relpath(path, ROOT))
    return meta, body


def day_file(folder, given):
    """The stem of the day file --day names, whatever its zero padding (`3` finds days/03.md, or days/003.md in the
    journal); None when there is none."""
    try:
        want = int(given)
    except ValueError:
        return None
    try:
        names = sorted(os.listdir(os.path.join(folder, 'days')))
    except OSError:
        return None
    stems = [n[:-3] for n in names if n.endswith('.md') and n[:-3].isdigit() and int(n[:-3]) == want]
    return stems[0] if stems else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('slug', help='the trip folder under content/trips/')
    ap.add_argument('files', nargs='+', help='photo files or folders (.jpg, .jpeg, .png, .heic, .heif)')
    ap.add_argument('--day', metavar='NN', help="add them to days/NN.md instead (a multi-day trip's day)")
    ap.add_argument('--cover', action='store_true', help='set cover_photo: in index.md to the first photo added')
    ap.add_argument('--dry-run', action='store_true', help='print the files and the entries; write nothing')
    a = ap.parse_args(argv)
    folder = os.path.join(TRIPS, a.slug)
    where = 'content/trips/%s' % a.slug
    index = os.path.join(folder, 'index.md')
    if not os.path.exists(index):
        ap.error('no %s/index.md' % where)
    target, prefix = index, ''
    if a.day:
        day = day_file(folder, a.day)
        if day is None:
            ap.error('no %s/days/%s.md' % (where, a.day.zfill(2)))
        target, prefix = os.path.join(folder, 'days', day + '.md'), 'd%s-' % day
    files = photolib.collect(a.files)
    if not files:
        ap.error('no photo among %s (%s)' % (', '.join(a.files), ', '.join(photolib.PHOTO_EXT)))
    try:
        meta, body = read_md(target)
        imeta, ibody = read_md(index) if (a.cover and target != index) else (meta, body)
    except ValueError as ex:
        print(str(ex), file=sys.stderr)
        return 1
    start = photolib.next_number(folder, prefix)
    names = ['%s%02d' % (prefix, n) for n in range(start, start + len(files))]
    rel = '%s/%s' % (where, ('days/%s.md' % day) if a.day else 'index.md')
    if a.dry_run:
        for src, name in zip(files, names):
            print('would copy %s -> %s/photos/%s.webp (+ .sm.webp, .th.webp)' % (src, where, name))
        print('would add %d entr%s under photos: in %s%s' % (len(files), 'y' if len(files) == 1 else 'ies', rel,
                                                            ' and set cover_photo: photos/%s.webp in %s/index.md' % (names[0], where)
                                                            if a.cover else ''))
        print('dry run: nothing written')
        return 0
    entries = photolib.import_photos(folder, files, prefix, start)
    meta['photos'] = list(meta.get('photos') or []) + entries
    if a.cover and target == index:
        meta['cover_photo'] = entries[0]['file']
    with open(target, 'w', encoding='utf-8') as fh:
        fh.write(frontmatter.render(meta, body, keep_empty=True))
    if a.cover and target != index:
        imeta['cover_photo'] = entries[0]['file']
        with open(index, 'w', encoding='utf-8') as fh:
            fh.write(frontmatter.render(imeta, ibody, keep_empty=True))
    for e in entries:
        print('added %s (%dx%d)' % (e['file'], e['w'], e['h']))
    if a.cover:
        print('cover_photo: %s (its card-size copy is written)' % entries[0]['file'])
    print('Next: describe each photo in %s: %d empty alt: line%s (%s)'
          % (rel, len(entries), '' if len(entries) == 1 else 's', ', '.join(e['file'] for e in entries)))
    try:
        import checks
        for f in checks.run(TRIPS):
            if f['file'].startswith(where + '/') and f['level'] != 'note':
                print(checks.line(f))
    except Exception as ex:   # noqa: BLE001 — a courtesy here; build.py runs the check again
        print('the content check could not run (%s); python3 tools/validate.py' % ex)
    print('Publish: python3 tools/publish.py %s --push (no render needed)' % a.slug)
    return 0


if __name__ == '__main__':
    sys.exit(main())
