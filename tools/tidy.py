#!/usr/bin/env python3
"""List the iCloud conflict copies in the checkout, and delete the ones that only copy generated files.

  python3 tools/tidy.py            # list: one line per copy, then the counts
  python3 tools/tidy.py --delete   # ... and delete the copies under rendered/ and _site/

iCloud Drive names a conflict copy by adding a space and a number before the extension ('meta 3.json', 'map-wide
4.webp', 'a-trip 2/'): sitecheck.conflict_copy's rule, the one the build and the site checks use. Copies under
rendered/ (what render.py writes) and _site/ (what build.py writes) are never built or published, so --delete removes
them. A copy under content/ or assets/ is a copy of something written by hand and may hold the newer text: it is
compared with the file it copies and marked 'identical', 'older' (it differs and is older) or 'DIFFERS' (it differs and
is newer, or its original is gone), and only listed, as are the stray '.git/index N' files, with the line to delete
them by hand once you have looked (ADDING-TRIPS.md 'When something goes wrong').
"""
import argparse
import filecmp
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from sitegen import sitecheck  # noqa: E402

DELETABLE = ('rendered', '_site')                # copies of generated files, never built or published
BY_HAND = ('content', 'assets')                  # copies of what is written by hand: compared, listed, never deleted
LISTED = DELETABLE + BY_HAND
_NUMBER = re.compile(r' \d+((?:\.[A-Za-z0-9]+)*)$')
_INDEX_COPY = re.compile(r'^index \d+$')


def original_of(path):
    """The name a copy copies: 'meta 3.json' -> 'meta.json', 'first-tallac-lap 2' -> 'first-tallac-lap'."""
    head, tail = os.path.split(path)
    return os.path.join(head, _NUMBER.sub(r'\1', tail))


def _files(top):
    out = {}
    for dirpath, _dirs, names in os.walk(top):
        for n in names:
            full = os.path.join(dirpath, n)
            out[os.path.relpath(full, top)] = full
    return out


def compare(copy, original):
    """'identical', 'older' or 'DIFFERS' for a copy under content/ (a file, or a folder compared file by file)."""
    if not os.path.lexists(original):
        return 'DIFFERS'
    if os.path.isdir(copy) != os.path.isdir(original):
        return 'DIFFERS'
    if os.path.isdir(copy):
        a, b = _files(copy), _files(original)
        same = set(a) == set(b) and all(filecmp.cmp(a[k], b[k], shallow=False) for k in a)
        newest = max([os.path.getmtime(p) for p in a.values()] or [os.path.getmtime(copy)])
        theirs = max([os.path.getmtime(p) for p in b.values()] or [os.path.getmtime(original)])
    else:
        same = filecmp.cmp(copy, original, shallow=False)
        newest, theirs = os.path.getmtime(copy), os.path.getmtime(original)
    if same:
        return 'identical'
    return 'older' if newest < theirs else 'DIFFERS'


def find(root):
    """[(path relative to root, is a folder)] of every copy under LISTED (a copied folder once, not what it holds)."""
    found = []
    for top in LISTED:
        base = os.path.join(root, top)
        for dirpath, dirnames, filenames in os.walk(base):
            for d in sorted(dirnames):
                if sitecheck.conflict_copy(d):
                    found.append((os.path.relpath(os.path.join(dirpath, d), root), True))
            dirnames[:] = sorted(d for d in dirnames if not sitecheck.conflict_copy(d))
            for f in sorted(filenames):
                if sitecheck.conflict_copy(f):
                    found.append((os.path.relpath(os.path.join(dirpath, f), root), False))
    return found


def index_copies(root):
    gitdir = os.path.join(root, '.git')
    return sorted(n for n in (os.listdir(gitdir) if os.path.isdir(gitdir) else []) if _INDEX_COPY.match(n))


def main(argv=None, root=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--delete', action='store_true', help='delete the copies under rendered/ and _site/')
    a = ap.parse_args(argv)
    root = root or ROOT
    copies = find(root)
    deleted, by_top, by_hand = 0, {}, []
    for rel, is_dir in copies:
        top = rel.split(os.sep)[0]
        by_top[top] = by_top.get(top, 0) + 1
        shown = rel + ('/' if is_dir else '')
        if top in BY_HAND:
            print('%-9s %s' % (compare(os.path.join(root, rel), os.path.join(root, original_of(rel))), shown))
            by_hand.append(rel)
            continue
        if a.delete:
            full = os.path.join(root, rel)
            if is_dir and not os.path.islink(full):
                shutil.rmtree(full)
            else:
                os.remove(full)
            deleted += 1
            print('deleted   %s' % shown)
        else:
            print('copy      %s' % shown)
    stray = index_copies(root)
    for n in stray:
        print('copy      .git/%s' % n)
    print('%d conflict copies (%s)%s' % (len(copies), ', '.join('%s %d' % kv for kv in sorted(by_top.items())) or 'none',
                                          '; %d deleted' % deleted if a.delete else ''))
    if copies and not a.delete and len(copies) > len(by_hand):
        print('python3 tools/tidy.py --delete removes the %d under %s/' % (len(copies) - len(by_hand), '/, '.join(DELETABLE)))
    if by_hand:
        print('under content/ and assets/ (by hand, once you have compared each with its original): rm -r %s'
              % ' '.join('"%s"' % p for p in by_hand))
    if stray:
        print('stray copies of the git index (by hand, once git status works): rm %s' % ' '.join('".git/%s"' % n for n in stray))
    return 0


if __name__ == '__main__':
    sys.exit(main())
