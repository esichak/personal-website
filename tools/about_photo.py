#!/usr/bin/env python3
"""Put a photo on the About page (content/about.md), or replace the one there.

  python3 tools/about_photo.py ~/Desktop/portrait.jpg              # .jpg, .jpeg, .png, .heic or .heif
  python3 tools/about_photo.py ~/Desktop/portrait.jpg --dry-run    # the files and the lines it would write; writes nothing

The photo gets the copies a trip photo gets (1600 px, 800 px and card-size WebP, upright, no EXIF or GPS; HEIC and PNG
through sips) in content/about/photos/, numbered after any earlier one so no browser keeps showing the old file, and a
photo: block in content/about.md (the file is made when there is none) with its size and an empty alt: line. The page
shows the photo, cropped to 4:5 above the words, only once that alt: line describes it: the content check stops the
build until then. cover_focal_x / cover_focal_y (0 to 100) move the crop. Whether a portrait goes on a public site is
Eric's call; nothing here publishes it.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import frontmatter  # noqa: E402
import photos as photolib  # noqa: E402

CONTENT = os.path.join(ROOT, 'content')
PREFIX = 'portrait-'


def blank_front(text):
    """True when the file has no front matter, or a block with nothing but blank lines in it."""
    if not text.startswith('---'):
        return True
    end = text.find('\n---', 3)
    return end != -1 and not text[3:end].strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file', help='the photo (.jpg, .jpeg, .png, .heic, .heif)')
    ap.add_argument('--dry-run', action='store_true', help='print the files and the lines; write nothing')
    a = ap.parse_args(argv)
    if not os.path.isfile(a.file) or not a.file.lower().endswith(photolib.PHOTO_EXT):
        ap.error('%s is not a photo file (%s)' % (a.file, ', '.join(photolib.PHOTO_EXT)))
    path, folder = os.path.join(CONTENT, 'about.md'), os.path.join(CONTENT, 'about')
    meta, body = {}, ''
    if os.path.exists(path):
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
        meta, body = frontmatter.split(text)
        # no front matter, or an empty block (`---` twice, as docs/CONTENT_GUIDE.md section 12 shows it): nothing in it
        # to lose; otherwise the block must come back byte for byte
        if not (not meta and blank_front(text)) and frontmatter.render(meta, body, keep_empty=True) != text:
            print('content/about.md would change in more places than its photo: lines when written back (a comment or '
                  'an unusual layout in its front matter); add the photo by hand', file=sys.stderr)
            return 1
    old = meta.get('photo') if isinstance(meta.get('photo'), dict) else None
    n = photolib.next_number(folder, PREFIX)
    name = '%s%02d' % (PREFIX, n)
    if a.dry_run:
        print('would copy %s -> content/about/photos/%s.webp (+ .sm.webp, .th.webp)' % (a.file, name))
        print('would %s the photo: block of content/about.md, with an empty alt: line'
              % ('replace' if old else ('add' if meta or body else 'write content/about.md with')))
        print('dry run: nothing written')
        return 0
    entry = photolib.import_photos(folder, [a.file], PREFIX, n)[0]
    meta['photo'] = entry                                   # file, w, h and an empty alt: the old alt described the old photo
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(frontmatter.render(meta, body, keep_empty=True))
    print('added %s (%dx%d) to content/about/' % (entry['file'], entry['w'], entry['h']))
    if old and old.get('file'):
        stem = os.path.splitext(old['file'])[0]
        print('the earlier photo\'s files are still in content/about/: %s.* (delete them; git keeps them in its history)' % stem)
    print('Next: describe the photo in content/about.md: the alt: line under photo: is empty, and the page shows the photo '
          'only once it says what is in it (the content check stops the build until then)')
    print('Publish: git add content/about.md content/about/photos, commit, push (publish.py stages trips only)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
