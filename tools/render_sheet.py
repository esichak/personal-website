#!/usr/bin/env python3
"""A before/after contact sheet of a fixed sample of maps: what a re-render changed, as pictures (gap9-02).

  python3 tools/render_sheet.py                  # the fixed sample: HEAD against the working copy, then open the page
  python3 tools/render_sheet.py --base main~1    # ... against another commit
  python3 tools/render_sheet.py --all            # ... plus a thumbnail row for every trip whose rendered/trips/<slug>/ changed
  python3 tools/render_sheet.py SLUG SLUG:NAME,NAME site:NAME   # ... plus these trips, named renders of a trip, site maps
  python3 tools/render_sheet.py --after PREVIEW/rendered        # the after side from a preview drawn into a scratch folder
  python3 tools/render_sheet.py --out OUT --no-open             # write somewhere else (default .cache/render-sheet/)

A map on the site is three files that core.map_block stacks (the hillshade image, the base.svg image, the inline
.svg.html overlay), so `git diff` cannot show what a render changed. This page shows each sample twice, side by side:
before (the files of the base commit, taken out of git into the out folder) and after (the working copy's rendered/,
or with --after a folder laid out like it, linked into the out folder), each map stacked by core.map_block itself,
each profile by core.chart_block and each drawing (tile, card, g112) as the standalone image build.py publishes. Under
each pair: the bytes of every file before and after, the gzipped size of the base.svg against mapkit's budgets
(BASE_GZ_KB_PHONE for phone renders, BASE_GZ_KB for the others), and 'unchanged' when a file's SHA-1 is the same on
both sides. The header counts the changed, unchanged, new and removed files under rendered/ (git status against HEAD;
git diff for another base), leaving out iCloud conflict copies. With --after it compares every file of the folder with
the base commit's rendered/ instead, and a trip folder (or site/) the preview did not draw at all is 'not drawn', not
removed: its samples show the before side only. A site map is named by its key (site:mtb-<region>-desktop); a map the
folder's meta.json does not list is still shown when its files are there (its size read from the overlay).

The fixed sample: the newest trip of each activity that has a track and a render, matterhorn-peak-west-couloir,
gran-paradiso-haute-route's overview-wide and day-01-col, pacific-crest-trail-2024's overview-tall, and the Lake Tahoe
region and ski maps (rendered/site). Look at the page after a render with no trip name, before staging rendered/.
No network; the standard library and git (read only: nothing is staged, checked out or written to .git).
"""
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import build  # noqa: E402
import content  # noqa: E402
import mapkit  # noqa: E402
from sitegen import core  # noqa: E402
from sitegen import sitecheck  # noqa: E402

DEFAULT_OUT = os.path.join(ROOT, '.cache', 'render-sheet')
SHEET_MARK = '.render-sheet'     # left in the out folder, so a later run knows it may empty it
PAGE = 'index.html'
# the sample after the newest trip of each activity: a trip's default renders, or 'slug:name,name', or 'site:name,name'
FIXED = ('matterhorn-peak-west-couloir',
         'gran-paradiso-haute-route:overview-wide,day-01-col',
         'pacific-crest-trail-2024:overview-tall',
         'site:region-lake-tahoe-desktop,ski-lake-tahoe-desktop')
# a trip's renders on the sheet, in this order, when it names none: the ones its meta.json (or folder) has
DEFAULT_ITEMS = ('map-wide', 'map-col', 'map-phone', 'overview-wide', 'overview-tall', 'overview-col', 'overview-phone',
                 'profile-wide', 'speed-wide', 'tile', 'card', 'g112')
THUMB_MAPS = ('map-col', 'overview-col', 'overview-phone')   # the one map a --all thumbnail row shows
THUMB_WIDTH = 360


class GitError(Exception):
    pass


def git(*args):
    """A read-only git command's output (text). --no-optional-locks: git status does not refresh .git/index."""
    p = subprocess.run(['git', '-C', ROOT, '--no-optional-locks'] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if p.returncode:
        raise GitError(p.stderr.decode('utf-8', 'replace').strip() or 'git %s failed' % args[0])
    return p.stdout.decode('utf-8', 'surrogateescape')


class Blobs:
    """The files of one commit, read through one `git cat-file --batch` process (what git cat-file -p <base>:<path>
    prints, as bytes). get() is None for a path the commit does not have."""

    def __init__(self, commit):
        self.commit = commit
        self.cache = {}
        self.proc = subprocess.Popen(['git', '-C', ROOT, '--no-optional-locks', 'cat-file', '--batch'],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def get(self, path):
        if path not in self.cache:
            self.proc.stdin.write(('%s:%s\n' % (self.commit, path)).encode('utf-8', 'surrogateescape'))
            self.proc.stdin.flush()
            head = self.proc.stdout.readline().decode('utf-8', 'surrogateescape').split()
            data = None
            if len(head) == 3 and head[2].isdigit():      # '<sha> <type> <size>', else '<name> missing'
                body = self.proc.stdout.read(int(head[2]))
                self.proc.stdout.read(1)                      # the newline after the contents
                data = body if head[1] == 'blob' else None
            self.cache[path] = data
        return self.cache[path]

    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            self.proc.wait()
        self.proc.stdout.close()


# ---------------------------------------------------------------- comparing files

def sha1(data):
    return None if data is None else hashlib.sha1(data).hexdigest()


def state(before, after):
    """'unchanged' (same SHA-1), 'changed', 'new', 'removed', or 'missing' (on neither side) for two files' bytes."""
    if before is None and after is None:
        return 'missing'
    if before is None:
        return 'new'
    if after is None:
        return 'removed'
    return 'unchanged' if sha1(before) == sha1(after) else 'changed'


def gz_kb(data):
    """The gzipped size in KB, measured as mapkit measures base_gz_kb (zlib, level 9)."""
    return len(zlib.compress(data, 9)) / 1024.0


def phone_render(name):
    """mapkit's rule for a phone render (its smaller base-layer budget): a name ending in -phone or holding -phone-."""
    return name.endswith('-phone') or '-phone-' in name


def budget_kb(name):
    """The base.svg budget of the map `name` ('map-phone', or its file 'map-phone.base.svg'), from mapkit."""
    if name.endswith('.base.svg'):
        name = name[:-len('.base.svg')]
    return mapkit.BASE_GZ_KB_PHONE if phone_render(name) else mapkit.BASE_GZ_KB


def conflict_path(path):
    """True when any part of a '/'-separated path is an iCloud conflict copy ('meta 3.json', a folder 'a-trip 2/')."""
    return any(sitecheck.conflict_copy(part) for part in path.split('/') if part)


def fmt_bytes(n):
    return '—' if n is None else '{:,} B'.format(n)


# ---------------------------------------------------------------- what changed under rendered/

def parse_status(out):
    """[(state, path)] from `git status --porcelain -z --no-renames` output, state changed | new | removed against
    HEAD. A file added to the index and deleted again is on neither side and left out."""
    found = []
    for entry in out.split('\0'):
        if len(entry) < 4:
            continue
        xy, path = entry[:2], entry[3:]
        if xy == '!!':
            continue
        if xy == '??':
            found.append(('new', path))
        elif 'D' in xy:
            if xy[0] != 'A':
                found.append(('removed', path))
        elif 'A' in xy:
            found.append(('new', path))
        else:
            found.append(('changed', path))
    return found


def parse_name_status(out):
    """[(state, path)] from `git diff --name-status -z --no-renames <base>` output (the base against the working copy)."""
    parts = out.split('\0')
    found = []
    for i in range(0, len(parts) - 1, 2):
        code, path = parts[i], parts[i + 1]
        if not code or not path:
            continue
        found.append(({'A': 'new', 'D': 'removed'}.get(code[0], 'changed'), path))
    return found


def tally(entries, base_files):
    """{changed, unchanged, new, removed, skipped} for the files under rendered/: entries from parse_status /
    parse_name_status, base_files the paths the base commit holds; iCloud conflict copies are skipped (counted in
    'skipped', never in the others)."""
    counts = {'changed': 0, 'new': 0, 'removed': 0, 'skipped': 0}
    seen = set()
    for st, path in entries:
        if path in seen:
            continue
        seen.add(path)
        if conflict_path(path):
            counts['skipped'] += 1
            continue
        counts[st] += 1
    base_n = sum(1 for p in base_files if not conflict_path(p))
    counts['unchanged'] = max(0, base_n - counts['changed'] - counts['removed'])
    return counts


def changed_trips(entries):
    """The slugs of the trips with a changed, new or removed file under rendered/trips/<slug>/ (conflict copies not)."""
    out = set()
    for _st, path in entries:
        parts = path.split('/')
        if len(parts) > 3 and parts[0] == 'rendered' and parts[1] == 'trips' and not conflict_path(path):
            out.add(parts[2])
    return sorted(out)


def rendered_changes(commit, is_head):
    """(counts, entries) for rendered/: the working copy against the base commit."""
    status = git('status', '--porcelain', '-z', '--untracked-files=all', '--no-renames', '--', 'rendered')
    entries = parse_status(status)
    if not is_head:
        # tracked files: the base against the working copy; untracked ones ('??') are new against any base
        untracked = [('new', x[3:]) for x in status.split('\0') if x[:3] == '?? ' and len(x) > 3]
        entries = parse_name_status(git('diff', '--name-status', '-z', '--no-renames', commit, '--', 'rendered')) + untracked
    return tally(entries, list(parse_ls_tree(git('ls-tree', '-r', '-z', commit, '--', 'rendered')))), entries


def parse_ls_tree(out):
    """{path: blob id} from `git ls-tree -r -z` output ('<mode> blob <id>\\t<path>')."""
    found = {}
    for entry in out.split('\0'):
        head, tab, path = entry.partition('\t')
        parts = head.split()
        if tab and len(parts) == 3 and parts[1] == 'blob':
            found[path] = parts[2]
    return found


def blob_id(data):
    """The id git gives a file's contents (the SHA-1 of 'blob <size>\\0' and the bytes), to compare with ls-tree's."""
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def ignored_name(name):
    """A name the preview folder's comparison leaves out: an iCloud conflict copy, render.py's half-drawn '<folder>.tmp-
    <pid>' or '<folder>.old' (the names .gitignore leaves out under rendered/), and dotfiles (.DS_Store)."""
    return sitecheck.conflict_copy(name) or '.tmp-' in name or name.endswith('.old') or name.startswith('.')


def owner_of(path):
    """The folder a rendered file belongs to: rendered/trips/<slug> for a trip's, else its folder below rendered/
    (rendered/site)."""
    parts = path.split('/')
    if len(parts) > 3 and parts[1] == 'trips':
        return '/'.join(parts[:3])
    return '/'.join(parts[:2]) if len(parts) > 2 else parts[0]


def walk_preview(top):
    """({'rendered/<path>': blob id}, the folders it holds, names skipped) for a folder laid out like rendered/."""
    ids, held, skipped = {}, set(), 0
    for dirpath, dirnames, filenames in os.walk(top):
        rel = os.path.relpath(dirpath, top).replace(os.sep, '/')
        here = 'rendered' if rel == '.' else 'rendered/' + rel
        held.add(owner_of(here + '/-'))
        skipped += sum(1 for d in dirnames if ignored_name(d)) + sum(1 for f in filenames if ignored_name(f))
        dirnames[:] = sorted(d for d in dirnames if not ignored_name(d))
        for f in sorted(filenames):
            if not ignored_name(f):
                with open(os.path.join(dirpath, f), 'rb') as fh:
                    ids['%s/%s' % (here, f)] = blob_id(fh.read())
    return ids, held, skipped


def compare_preview(ids, base_ids, held, skipped=0):
    """(counts, entries) for a preview folder against the base commit's rendered/: ids and base_ids {path: blob id},
    held the folders the preview has (owner_of). A base file the preview lacks is 'removed' when the preview holds its
    folder, else 'not drawn' (a preview draws a few trips, not all of them)."""
    counts = {'changed': 0, 'unchanged': 0, 'new': 0, 'removed': 0, 'not_drawn': 0, 'skipped': skipped}
    entries = []
    for path in sorted(ids):
        b = base_ids.get(path)
        st = 'new' if b is None else ('unchanged' if b == ids[path] else 'changed')
        counts[st] += 1
        if st != 'unchanged':
            entries.append((st, path))
    for path in sorted(base_ids):
        if path in ids or any(ignored_name(p) for p in path.split('/')):
            continue
        if owner_of(path) in held:
            counts['removed'] += 1
            entries.append(('removed', path))
        else:
            counts['not_drawn'] += 1
    return counts, entries


def preview_changes(commit, top):
    ids, held, skipped = walk_preview(top)
    return compare_preview(ids, parse_ls_tree(git('ls-tree', '-r', '-z', commit, '--', 'rendered')), held, skipped)


# ---------------------------------------------------------------- the sample

def parse_spec(spec):
    """'slug' -> ('slug', None); 'slug:a,b' -> ('slug', ['a', 'b']); 'site:a' -> ('site', ['a'])."""
    where, _sep, names = spec.partition(':')
    return where, [n for n in names.split(',') if n] or None


def folder_of(where):
    """The folder under the checkout that holds a sample's renders: rendered/site or rendered/trips/<slug>."""
    return 'rendered/site' if where == 'site' else 'rendered/trips/%s' % where


def newest_by_activity(trips, has_render):
    """[(slug, activity)] the newest trip of each activity (content.load_all's order) with a track and a render."""
    out = []
    for act in content.ACTIVITIES:
        for t in trips:
            if t['activity'] == act and core.has_track(t) and has_render(t['slug']):
                out.append((t['slug'], act))
                break
    return out


def size_of(name):
    """The map_block / chart_block size class a render is shown as (overview-tall is the series page's wide map)."""
    for suffix, size in (('-wide', 'wide'), ('-tall', 'wide'), ('-col', 'col'), ('-phone', 'phone'), ('-desktop', 'desktop')):
        if name.endswith(suffix):
            return size
    return 'col'


def kind_of(name, metas):
    if name in core.GLYPH_SIZES:
        return 'drawing'
    if any(name in (m or {}).get('maps', {}) for m in metas):
        return 'map'
    if any(name in (m or {}).get('charts', {}) for m in metas) or 'profile' in name or 'speed' in name:
        return 'chart'
    return 'map'


def files_of(name, kind, metas):
    """The files one render is made of, as named in either side's meta.json (a map's image may change from .png to
    .webp between the two)."""
    if kind != 'map':
        return [name + '.svg.html']
    out = []
    for key in ('png', 'base'):
        for m in metas:
            f = ((m or {}).get('maps', {}).get(name) or {}).get(key)
            if f and f not in out:
                out.append(f)
    return out + [name + '.svg.html']


def link_or_copy(src, dst):
    """The working copy's file linked into the out folder (copied where a link cannot be made)."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        os.symlink(src, dst)
    except OSError:
        shutil.copy2(src, dst)


class Side:
    """One column of the sheet: the files of the base commit (before, through blobs) or of a folder laid out like
    rendered/ (after: the working copy's, or a preview's with --after), staged under <out>/<label>/<folder below
    rendered/>/. name: how the page names the side ('HEAD (be6e5d8)', 'the working copy', 'preview15/rendered')."""

    def __init__(self, label, name, out, blobs=None, src=None, preview=False):
        self.label, self.name, self.out, self.blobs = label, name, out, blobs
        self.caption = '%s · %s' % (label.capitalize(), name)
        self.src = src or os.path.join(ROOT, 'rendered')
        self.preview = preview

    def source(self, rel):
        """A 'rendered/...' path's file on this side's disk (after only)."""
        return os.path.join(self.src, os.path.relpath(rel, 'rendered'))

    def read(self, rel):
        if self.blobs is not None:
            return self.blobs.get(rel)
        path = self.source(rel)
        if not os.path.isfile(path):
            return None
        with open(path, 'rb') as fh:
            return fh.read()

    def not_drawn(self, folder):
        """True when this side is a preview (--after) that does not hold the folder at all: it drew other trips."""
        return self.preview and not os.path.isdir(self.source(folder))

    def staged(self, rel):
        """The file's place in the out folder; None when this side does not have it."""
        dst = os.path.join(self.out, self.label, os.path.relpath(rel, 'rendered'))
        if os.path.lexists(dst):
            return dst
        if self.blobs is not None:
            data = self.blobs.get(rel)
            if data is None:
                return None
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as fh:
                fh.write(data)
        else:
            src = self.source(rel)
            if not os.path.isfile(src):
                return None
            link_or_copy(src, dst)
        return dst

    def meta(self, folder):
        data = self.read(folder + '/meta.json')
        try:
            return json.loads(data.decode('utf-8')) if data else None
        except ValueError:
            return None

    def write_meta(self, folder, meta):
        """The meta.json map_block and render_meta read for this side: the folder's own, plus any map guessed_map
        found, written into the out folder."""
        dst = os.path.join(self.out, self.label, os.path.relpath(folder, 'rendered'), 'meta.json')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.lexists(dst):
            os.remove(dst)
        with open(dst, 'w', encoding='utf-8') as fh:
            json.dump(meta, fh)


_SVG_SIZE = re.compile(r'^\s*<svg\b[^>]*?\swidth="(\d+)"[^>]*?\sheight="(\d+)"')


def guessed_map(side, folder, name):
    """A meta.json 'maps' entry for a map whose files are on this side but whose meta.json does not list it (a preview
    of a new site map): its size from the overlay's <svg width height>, its images by name. None without an overlay."""
    data = side.read('%s/%s.svg.html' % (folder, name))
    m = _SVG_SIZE.match(data[:4096].decode('utf-8', 'replace')) if data else None
    if not m:
        return None
    entry = {'w': int(m.group(1)), 'h': int(m.group(2))}
    for f in (name + '.webp', name + '.png'):
        if side.read('%s/%s' % (folder, f)) is not None:
            entry['png'] = f
            break
    if side.read('%s/%s.base.svg' % (folder, name)) is not None:
        entry['base'] = name + '.base.svg'
    return entry


def has_item(sides, folder, name):
    """True when a render of that name is on either side: listed in a meta.json, or its .svg.html is there."""
    for side in sides:
        m = side.meta(folder) or {}
        if name in (m.get('maps') or {}) or name in (m.get('charts') or {}):
            return True
        if side.read('%s/%s.svg.html' % (folder, name)) is not None:
            return True
    return False


def strip_lazy(s):
    # the sheet shows every map at once: a lazy or async-decoded image under the fold can be missing from a print or a
    # headless screenshot of the whole page
    return s.replace(' loading="lazy"', '').replace(' decoding="async"', '')


def side_html(side, where, folder, name, kind, size, ns, meta):
    """One render on one side, drawn by the site's own code from the files staged for that side; '' when it is not
    there."""
    if not meta and kind == 'map':
        return ''
    sub = os.path.relpath(folder, 'rendered')          # 'site' or 'trips/<slug>'
    local = os.path.join(side.out, side.label, sub)
    asset_dir = '%s/%s/' % (side.label, sub.replace(os.sep, '/'))
    if kind == 'map':
        m = (meta.get('maps') or {}).get(name)
        if not m:
            return ''
        staged = {f: side.staged('%s/%s' % (folder, f)) for f in files_of(name, 'map', [meta])}
        if not staged[name + '.svg.html']:
            return ''     # listed in meta.json but not drawn on this side (a preview that left the map out)
        if where == 'site':
            body = core.map_block({}, PAGE, [(name, size)], asset_dir, ns, site_maps=True, attrib=False, site_dir=local)
        else:
            t = {'slug': where, 'kind': meta.get('kind') or 'trip', 'rendered': local, 'track': 'track.gpx', 'days': [],
                 'url': asset_dir}
            body = core.map_block(t, PAGE, [(name, size)], asset_dir, ns, attrib=False)
        return '<div class="rs-fit" style="max-width:%dpx">%s</div>' % (m.get('w') or 1440, strip_lazy(body))
    t = {'slug': where, 'kind': (meta or {}).get('kind') or 'trip', 'rendered': local, 'track': 'track.gpx', 'days': [],
         'url': asset_dir}
    src = side.staged('%s/%s.svg.html' % (folder, name))
    if not src:
        return ''
    if kind == 'chart':
        w = (((meta or {}).get('charts') or {}).get(name) or {}).get('w') or 1248
        return '<div class="rs-fit" style="max-width:%dpx">%s</div>' % (w, core.chart_block(t, PAGE, [(name, size)], ns))
    svg = build.drawing_svg(src, name)
    if not svg:
        return ''
    with open(os.path.join(local, name + '.svg'), 'w', encoding='utf-8') as fh:
        fh.write(svg)
    # the pages' own helpers; card_tile falls back to the tile, but the card's .svg.html is staged here, so it is the card
    img = {'tile': core.tile, 'card': core.card_tile}.get(name)
    return strip_lazy(img(t, PAGE) if img else core.glyph(t, PAGE, name))


def file_rows(name, kind, folder, before, after, metas):
    """[(file, before bytes, after bytes, state, base.svg sizes or None)] for one render."""
    rows = []
    not_drawn = after.not_drawn(folder)
    for f in files_of(name, kind, metas):
        b, a = before.read('%s/%s' % (folder, f)), after.read('%s/%s' % (folder, f))
        gz = None
        if f.endswith('.base.svg'):
            gz = (None if b is None else gz_kb(b), None if a is None else gz_kb(a), budget_kb(f))
        st = 'not drawn' if (not_drawn and a is None and b is not None) else state(b, a)
        rows.append((f, None if b is None else len(b), None if a is None else len(a), st, gz))
    return rows


def pair_state(rows):
    states = {r[3] for r in rows if r[3] != 'missing'}
    if not states:
        return 'missing'
    for one in ('unchanged', 'new', 'removed', 'not drawn'):
        if states == {one}:
            return one
    return 'changed'


def st_class(st):
    return 'rs-st rs-st--' + st.replace(' ', '-')


def gz_cell(gz):
    b, a, budget = gz

    def one(v):
        if v is None:
            return '—'
        return ('<b class="rs-over">%.1f KB (over)</b>' % v) if v > budget else '%.1f KB' % v
    return 'gzip %s → %s, budget %d KB' % (one(b), one(a), budget)


def rows_html(rows):
    out = ['<table class="rs-files"><thead><tr><th scope="col">File</th><th scope="col">Before</th><th scope="col">After'
           '</th><th scope="col"></th></tr></thead><tbody>']
    for f, b, a, st, gz in rows:
        note = '<span class="%s">%s</span>' % (st_class(st), st)
        if gz:
            note += ' · ' + gz_cell(gz)
        out.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (html.escape(f), fmt_bytes(b), fmt_bytes(a), note))
    return ''.join(out) + '</tbody></table>'


def sample_html(i, where, names, why, trips_by_slug, before, after, report, thumb=False):
    """One row of the sheet: a heading, then a before/after pair per render with its file table."""
    folder = folder_of(where)
    metas = [before.meta(folder), after.meta(folder)]
    if names is None and where == 'site':
        names = sorted({n for m in metas for n in (m or {}).get('maps', {}) if n.endswith('-desktop')})
    elif names is None:
        if thumb:
            names = [next((n for n in THUMB_MAPS if any(n in (m or {}).get('maps', {}) for m in metas)), None)]
            names = [n for n in names if n] or sorted({n for m in metas for n in (m or {}).get('maps', {})})[:1]
        else:
            have = {n for m in metas for n in list((m or {}).get('maps', {})) + list((m or {}).get('charts', {}))}
            names = [n for n in DEFAULT_ITEMS if n in have or (n in core.GLYPH_SIZES and (
                before.read('%s/%s.svg.html' % (folder, n)) is not None or after.read('%s/%s.svg.html' % (folder, n)) is not None))]
    for k, side in enumerate((before, after)):
        # a map the side's meta.json does not list but whose files are there (a preview of a new site map)
        found = {n: guessed_map(side, folder, n) for n in names
                 if kind_of(n, metas) == 'map' and n not in ((metas[k] or {}).get('maps') or {})}
        found = {n: e for n, e in found.items() if e}
        if found:
            metas[k] = dict(metas[k] or {'charts': {}})
            metas[k]['maps'] = dict(metas[k].get('maps') or {}, **found)
        if metas[k] is not None:
            side.write_meta(folder, metas[k])
    t = trips_by_slug.get(where)
    if where == 'site':
        title = 'Site maps'
        sub = ['rendered/site']
    else:
        title = where
        sub = [html.escape(t['title']), html.escape(t['activity_label']), str(t['date'] or '')] if t else ['not in content/trips']
    not_drawn = after.not_drawn(folder)
    meta_st = state(before.read(folder + '/meta.json'), after.read(folder + '/meta.json'))
    sub += [why, 'not drawn in %s: before only' % html.escape(after.name) if not_drawn else 'meta.json %s' % meta_st]
    out = ['<section class="rs-row%s" id="s%d"><h2>%s <small>%s</small></h2>'
           % (' rs-row--thumb' if thumb else '', i, html.escape(title), ' · '.join(s for s in sub if s))]
    for j, name in enumerate(names):
        kind, size = kind_of(name, metas), size_of(name)
        rows = file_rows(name, kind, folder, before, after, metas)
        st = pair_state(rows)
        report.append((title, name, st))
        cols = []
        for side, m, cap in ((before, metas[0], before.caption), (after, metas[1], after.caption)):
            body = side_html(side, where, folder, name, kind, size, 'rs%d%s%d' % (i, side.label[0], j), m)
            if not body:
                body = '<p class="rs-none">%s %s</p>' % ('Not drawn in' if side.not_drawn(folder) else 'Not in',
                                                         html.escape(side.name))
            cols.append('<figure class="rs-col"><figcaption>%s</figcaption>%s</figure>' % (html.escape(cap), body))
        out.append('<div class="rs-pair"><h3>%s <span class="%s">%s</span></h3><div class="rs-cols">%s</div>%s</div>'
                   % (html.escape(name), st_class(st), st, ''.join(cols), rows_html(rows)))
    return ''.join(out) + '</section>'


CSS = """
body.rs { padding: 24px 24px 64px; }
.rs h1 { font: 600 28px/36px var(--sans); }
.rs h2 { font: 600 20px/28px var(--sans); margin: 48px 0 8px; padding-top: 16px; border-top: 2px solid var(--ink); }
.rs h2 small { font: 400 13px/20px var(--mono); color: var(--ink-3); margin-left: 8px; }
.rs h3 { font: 600 14px/20px var(--mono); margin: 24px 0 8px; }
.rs-sum { font: 600 15px/24px var(--mono); margin: 8px 0; }
.rs-note { color: var(--ink-2); max-width: 900px; font-size: 14px; line-height: 20px; }
.rs-toc { display: flex; flex-wrap: wrap; gap: 4px 16px; margin: 12px 0; font: 13px/20px var(--mono); }
.rs-toc a { text-decoration: underline; }
.rs-units { border: 1px solid var(--rule-strong); padding: 2px 10px; font: 13px/20px var(--mono); margin-left: 8px; }
.rs .mv, .rs .cv { display: block; }
.rs .mv-attrib, .rs .mv-fs { display: none; }
.rs-cols { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; align-items: start; }
.rs-col { margin: 0; min-width: 0; }
.rs-col figcaption { font: 12px/18px var(--mono); color: var(--ink-3); margin-bottom: 4px; text-transform: uppercase; }
.rs-fit { width: 100%; }
.rs-none { border: 1px dashed var(--rule-strong); padding: 24px; color: var(--ink-3); font: 13px/20px var(--mono); }
.rs-files { border-collapse: collapse; margin-top: 8px; font: 12px/18px var(--mono); }
.rs-files th, .rs-files td { padding: 2px 16px 2px 0; text-align: right; white-space: nowrap; }
.rs-files th:first-child, .rs-files td:first-child, .rs-files th:last-child, .rs-files td:last-child { text-align: left; }
.rs-files th { color: var(--ink-3); font-weight: 400; border-bottom: 1px solid var(--rule); }
.rs-st { padding: 0 4px; }
.rs-st--unchanged { color: var(--ink-3); }
.rs-st--changed, .rs-st--new, .rs-st--removed { background: var(--route); color: #fff; }
.rs-st--not-drawn { color: var(--ink-3); font-style: italic; }
.rs-over { color: var(--route); }
.rs-row--thumb h2 { margin-top: 24px; font-size: 16px; border-top-width: 1px; }
.rs-row--thumb .rs-fit { max-width: THUMBpx !important; }
.rs-row--thumb .rs-cols { max-width: PAIRpx; }
""".replace('THUMB', str(THUMB_WIDTH)).replace('PAIR', str(2 * THUMB_WIDTH + 16))

SCRIPT = """
(function () {
  var d = document.documentElement, b = document.querySelector('.rs-units');
  function set(km) { d.classList.toggle('km', km); b.setAttribute('aria-pressed', km ? 'true' : 'false'); }
  b.addEventListener('click', function () { set(!d.classList.contains('km')); });
  set(location.hash === '#km');
})();
"""


def summary_line(base_label, counts, after_name=None):
    """The header's counts: rendered/ (or the preview folder) against the base commit."""
    line = '%s against %s: %s changed · %s unchanged · %s new · %s removed' % (
        after_name or 'rendered/', base_label, '{:,}'.format(counts['changed']), '{:,}'.format(counts['unchanged']),
        '{:,}'.format(counts['new']), '{:,}'.format(counts['removed']))
    if 'not_drawn' in counts:
        line += ' · %s not drawn' % '{:,}'.format(counts['not_drawn'])
    return line


def page_html(base_label, counts, samples, thumbs, all_flag, after_name=None):
    toc = ''.join('<a href="#s%d">%s</a>' % (i, html.escape(lab)) for i, lab, _h in samples)
    if all_flag:
        toc += '<a href="#changed">changed trips (%d)</a>' % len(thumbs)
    if after_name:
        after = ('%s, a folder laid out like rendered/ (a preview: a trip folder it does not hold is not drawn, and its '
                 'samples show the before side only)' % html.escape(after_name))
    else:
        after = 'the working copy'
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width, initial-scale=1">'
             '<title>Render sheet</title><link rel="stylesheet" href="assets/site.css"><style>%s</style></head>'
             '<body class="rs"><header><h1>Render sheet</h1><p class="rs-sum">%s</p>'
             '<p class="rs-note">Before: the files of %s, taken out of git. After: %s. Each map is stacked '
             'by core.map_block (hillshade, base.svg, inline overlay), each profile by core.chart_block, each drawing '
             'as the standalone SVG build.py publishes. A file is unchanged when its SHA-1 is the same on both sides; '
             'iCloud conflict copies are not counted (%d skipped).'
             '<button type="button" class="rs-units" aria-pressed="false">KM</button></p><nav class="rs-toc">%s</nav>'
             '</header><main>' % (CSS, html.escape(summary_line(base_label, counts, after_name)), html.escape(base_label),
                                  after, counts['skipped'], toc)]
    parts += [h for _i, _lab, h in samples]
    if all_flag:
        parts.append('<section id="changed"><h2>Changed trips <small>every trip whose %s/trips/&lt;slug&gt;/ '
                     'differs from %s, column map only</small></h2>%s</section>'
                     % (html.escape(after_name or 'rendered'), html.escape(base_label),
                        ''.join(thumbs) or '<p class="rs-note">None.</p>'))
    parts.append('</main><script>%s</script></body></html>\n' % SCRIPT)
    return ''.join(parts)


# ---------------------------------------------------------------- the out folder

def unsafe_out(path):
    """Why `path` must not be the sheet's folder, or None. The sheet empties its folder first, so it may not be this
    checkout, a folder that holds it, or anything inside its source folders; and a folder that is already there must be
    empty or an earlier sheet (each run leaves a .render-sheet file in it)."""
    real, root = os.path.realpath(path), os.path.realpath(ROOT)
    if real == root or root.startswith(real.rstrip(os.sep) + os.sep):
        return 'it is, or holds, this checkout'
    for name in build._SOURCE_FOLDERS:
        src = os.path.realpath(os.path.join(ROOT, name))
        if real == src or real.startswith(src + os.sep):
            return 'it is inside %s/ of this checkout' % name
    if os.path.exists(real) and not os.path.isdir(real):
        return 'it is a file'
    if os.path.isdir(real) and os.listdir(real) and not os.path.exists(os.path.join(real, SHEET_MARK)):
        return 'it is not empty and is not an earlier sheet (it has no %s file)' % SHEET_MARK
    return None


def fresh_out(path):
    """Empty the out folder (an earlier sheet: its links point into the checkout and are removed, never followed)."""
    os.makedirs(path, exist_ok=True)
    for n in os.listdir(path):
        p = os.path.join(path, n)
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p)
        else:
            os.remove(p)
    open(os.path.join(path, SHEET_MARK), 'w').close()
    assets = os.path.join(path, 'assets')
    os.makedirs(assets)
    with open(os.path.join(assets, 'site.css'), 'w', encoding='utf-8') as fh:
        fh.write(build.css_bundle())
    fonts = os.path.join(ROOT, 'assets', 'fonts')      # site.css names them relative to itself (fonts/<name>.woff2)
    for n in sorted(os.listdir(fonts)) if os.path.isdir(fonts) else []:
        if n.endswith('.woff2') and not sitecheck.conflict_copy(n):
            link_or_copy(os.path.join(fonts, n), os.path.join(assets, 'fonts', n))


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('slugs', nargs='*', metavar='SLUG', help='a trip to add to the sample (its default renders), '
                    'SLUG:NAME[,NAME] for named renders of it, site:NAME[,NAME] for site maps')
    ap.add_argument('--base', default='HEAD', help='the commit the before column is taken from (default HEAD)')
    ap.add_argument('--all', action='store_true', help='add a thumbnail row (column map only) for every trip whose '
                                                        'rendered/trips/<slug>/ changed against the base')
    ap.add_argument('--after', metavar='DIR', help='take the after side from DIR, a folder laid out like rendered/ '
                    '(DIR/trips/<slug>/, DIR/site/): a preview drawn into a scratch folder (default: the working copy)')
    ap.add_argument('--out', default=DEFAULT_OUT, help='the folder the sheet is written to (default .cache/render-sheet/)')
    ap.add_argument('--no-open', action='store_true', help='print the page\'s path without opening it')
    a = ap.parse_args(argv)
    try:
        commit = git('rev-parse', '--verify', '--quiet', a.base + '^{commit}').strip()
        head = git('rev-parse', '--verify', 'HEAD^{commit}').strip()
    except GitError:
        ap.error('--base %s: not a commit of this repository' % a.base)
    why = unsafe_out(a.out)
    if why:
        ap.error('--out %s: the sheet empties its folder first, and %s' % (a.out, why))
    out = os.path.abspath(a.out)
    base_label = '%s (%s)' % (a.base, commit[:7]) if a.base != commit[:len(a.base)] else commit[:7]
    after_dir = after_name = None
    if a.after:
        after_dir = os.path.abspath(a.after)
        if not any(os.path.isdir(os.path.join(after_dir, d)) for d in ('trips', 'site')):
            ap.error('--after %s: it holds neither trips/ nor site/ (name the folder laid out like rendered/)' % a.after)
        ro, ra = os.path.realpath(out), os.path.realpath(after_dir)
        if ro == ra or ro.startswith(ra + os.sep) or ra.startswith(ro + os.sep):
            ap.error('--out and --after may not be one inside the other')
        after_name = '/'.join(after_dir.rstrip(os.sep).split(os.sep)[-2:])   # 'preview15/rendered'

    blobs = Blobs(commit)
    try:
        before = Side('before', base_label, out, blobs)
        after = Side('after', after_name or 'working copy', out, src=after_dir, preview=bool(after_dir))

        def has_render(where):
            rel = folder_of(where) + '/meta.json'
            return os.path.isfile(after.source(rel)) or blobs.get(rel) is not None

        for spec in a.slugs:
            where, names = parse_spec(spec)
            if not where or not (has_render(where) or os.path.isdir(after.source(folder_of(where)))):
                ap.error('%s: no %s/ in %s or in %s' % (spec, folder_of(where or '?'), after.name, base_label))
            for n in names or ():
                if n not in core.GLYPH_SIZES and not has_item((before, after), folder_of(where), n):
                    ap.error('%s: no render named %s in %s/ of %s or of %s' % (spec, n, folder_of(where), after.name, base_label))

        trips = content.load_all()
        by_slug = {t['slug']: t for t in trips}
        specs, seen = [], set()
        wanted = ([(s, 'newest %s' % content.ACTIVITIES[act][0]) for s, act in newest_by_activity(trips, has_render)]
                  + [(s, 'fixed sample') for s in FIXED] + [(s, 'named') for s in a.slugs])
        for spec, why_in in wanted:
            where, names = parse_spec(spec)
            key = (where, tuple(names or ()))
            if key in seen:
                continue
            seen.add(key)
            if where == 'site' or why_in == 'named' or has_render(where):    # a named one was checked above
                specs.append((where, names, why_in))

        counts, entries = preview_changes(commit, after_dir) if after_dir else rendered_changes(commit, commit == head)
        fresh_out(out)
        report, samples = [], []
        for i, (where, names, why_in) in enumerate(specs, 1):
            label = where if where != 'site' else ('site: ' + ', '.join(names)) if names else 'site maps'
            samples.append((i, label, sample_html(i, where, names, why_in, by_slug, before, after, report)))
        thumbs = []
        if a.all:
            shown = {w for w, n, _y in specs if n is None}
            for k, slug in enumerate([s for s in changed_trips(entries) if s not in shown], len(specs) + 1):
                thumbs.append(sample_html(k, slug, None, 'changed', by_slug, before, after, report, thumb=True))
    finally:
        blobs.close()

    page = os.path.join(out, PAGE)
    with open(page, 'w', encoding='utf-8') as fh:
        fh.write(page_html(base_label, counts, samples, thumbs, a.all, after_name))
    print('%s (%d skipped)' % (summary_line(base_label, counts, after_name), counts['skipped']))
    for title, name, st in report:
        print('  %-44s %-26s %s' % (title, name, st))
    print(page)
    if not a.no_open and shutil.which('open'):
        subprocess.call(['open', page])
    return 0


if __name__ == '__main__':
    sys.exit(main())
