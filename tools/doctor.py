#!/usr/bin/env python3
"""One read-only look at this Mac and this checkout before publishing: python3 tools/doctor.py

One line per check, OK or WARN with the fix. It reads only: no network, no build, no validate, nothing written (git
is asked with --no-optional-locks, so even the index's cached file times are left alone). The exit status is 1 only
for what stops a publish: the checkout is not on main, .git/index is missing, or a conflict copy is staged. Changed
and staged files are a warning: publish.py commits the trips it is given and refuses what is unrelated.

Checks: free disk space (WARN under 30 GB: low space is when iCloud Drive offloads files, and on 2026-10-10 it removed
.git/index); .git/index present (else the git read-tree HEAD recipe); stray '.git/index N' copies (listed with the rm
line to run by hand); the branch, a clean tree, ahead/behind origin/main (from the last fetch) and the git identity;
iCloud conflict copies by top folder, naming any under content/ or staged; tracked files under rendered/ and content/
that iCloud has offloaded (macOS only); cwebp, and the optional node, python3.12 and gh.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from sitegen import sitecheck  # noqa: E402

LOW_GB = 30
DATALESS = 0x40000000          # macOS SF_DATALESS: the file's bytes are in iCloud, not on this disk
SKIP_DIRS = ('.git', '.cache', 'node_modules')
_INDEX_COPY = re.compile(r'^index \d+$')


def git(root, *args):
    return subprocess.run(['git', '--no-optional-locks', '-C', root] + list(args), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)


def check_disk(root, free_bytes=None):
    free = shutil.disk_usage(root).free if free_bytes is None else free_bytes
    gb = free / 1e9
    if gb < LOW_GB:
        return ('WARN', 'disk', '%.0f GB free: under %d GB iCloud Drive offloads files, and on 2026-10-10 it removed '
                '.git/index; free some space before a render or a big build' % (gb, LOW_GB), False)
    return ('OK', 'disk', '%.0f GB free' % gb, False)


def check_index(root):
    if os.path.exists(os.path.join(root, '.git', 'index')):
        return [('OK', 'git index', '.git/index is there', False)]
    return [('WARN', 'git index', '.git/index is missing: git read-tree HEAD, then git status --short; nothing is lost '
             'but the staging list, so git add again what was staged; then free disk space', True)]


def check_index_copies(root):
    gitdir = os.path.join(root, '.git')
    copies = sorted(n for n in (os.listdir(gitdir) if os.path.isdir(gitdir) else []) if _INDEX_COPY.match(n))
    if not copies:
        return [('OK', 'index copies', 'no stray .git/index N copies', False)]
    return [('WARN', 'index copies', '%d stray cop%s of .git/index (iCloud); once git status works, delete them by hand: '
             % (len(copies), 'y' if len(copies) == 1 else 'ies') + 'rm ' + ' '.join('".git/%s"' % n for n in copies), False)]


def check_git(root, which=shutil.which):
    out = []
    branch = git(root, 'branch', '--show-current').stdout.strip()
    if branch == 'main':
        out.append(('OK', 'branch', 'on main', False))
    else:
        out.append(('WARN', 'branch', 'on %s: publish.py publishes from main (git switch main)' % (branch or 'a detached HEAD'), True))
    status = git(root, 'status', '--porcelain', '--untracked-files=no').stdout.strip()
    untracked = len([ln for ln in git(root, 'status', '--porcelain', '--untracked-files=normal').stdout.splitlines()
                     if ln.startswith('??')])
    note = ' (%d untracked: publish.py stages by path, so they stay out)' % untracked if untracked else ''
    if status:
        n = len(status.splitlines())
        out.append(('WARN', 'tree', '%d staged or changed tracked file%s (git status --short): publish.py commits only the '
                    'trips you name and refuses anything unrelated that is staged%s' % (n, '' if n == 1 else 's', note), False))
    else:
        out.append(('OK', 'tree', 'no staged or changed tracked file' + note, False))
    counts = git(root, 'rev-list', '--left-right', '--count', 'origin/main...HEAD')
    if counts.returncode == 0 and len(counts.stdout.split()) == 2:
        behind, ahead = (int(x) for x in counts.stdout.split())
        state = 'OK' if not behind else 'WARN'
        out.append((state, 'origin', '%d ahead, %d behind origin/main (as of the last fetch)%s'
                    % (ahead, behind, '; git pull --ff-only before publishing' if behind else ''), False))
    else:
        out.append(('WARN', 'origin', 'no origin/main to compare with (git fetch origin)', False))
    name = git(root, 'config', 'user.name').stdout.strip()
    email = git(root, 'config', 'user.email').stdout.strip()
    if name and email:
        out.append(('OK', 'identity', 'git commits as %s' % name, False))
    else:
        out.append(('WARN', 'identity', 'no git identity: git config --global user.name "..." and user.email "..."', False))
    return out


def conflict_copies(root):
    """{top folder: [path]} of every iCloud conflict copy in the checkout (a copied folder counts once), .git and
    .cache left out."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        if rel == '.':
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for d in list(dirnames):
            if sitecheck.conflict_copy(d):
                dirnames.remove(d)
                path = os.path.normpath(os.path.join(rel, d))
                found.setdefault(path.split(os.sep)[0], []).append(path + '/')
        for f in filenames:
            if sitecheck.conflict_copy(f):
                path = os.path.normpath(os.path.join(rel, f))
                found.setdefault(path.split(os.sep)[0] if os.sep in path else '.', []).append(path)
    return found


def check_copies(root):
    found = conflict_copies(root)
    if not found:
        return [('OK', 'copies', 'no iCloud conflict copies', False)]
    out = [('WARN', 'copies', '%d iCloud conflict copies: %s; python3 tools/tidy.py lists them and --delete removes those '
            'of generated files (rendered/, _site/)' % (sum(len(v) for v in found.values()),
                                  ', '.join('%s %d' % (k, len(v)) for k, v in sorted(found.items()))), False)]
    if found.get('content'):
        out.append(('WARN', 'copies', 'under content/ (the validator stops on these; compare, then delete by hand): '
                    + ', '.join(found['content'][:10]) + (' ...' if len(found['content']) > 10 else ''), False))
    staged = [p for p in git(root, 'diff', '--cached', '--name-only').stdout.splitlines() if sitecheck.conflict_copy(p)]
    if staged:
        out.append(('WARN', 'copies', 'staged: %s (git restore --staged <path>)' % ', '.join(staged), True))
    return out


def check_offloaded(root, flags=None, platform=sys.platform):
    if platform != 'darwin' and flags is None:
        return [('OK', 'offloaded', 'not checked (macOS only)', False)]
    flags = flags or (lambda p: getattr(os.lstat(p), 'st_flags', 0))
    tracked = [p for p in git(root, 'ls-files', '-z', '--', 'rendered', 'content').stdout.split('\0') if p]
    gone = []
    for p in tracked:
        try:
            if flags(os.path.join(root, p)) & DATALESS:
                gone.append(p)
        except OSError:
            continue
    if not gone:
        return [('OK', 'offloaded', 'all %d tracked files under rendered/ and content/ are on this disk' % len(tracked), False)]
    tops = {}
    for p in gone:
        top = '/'.join(p.split('/')[:2])
        tops[top] = tops.get(top, 0) + 1
    return [('WARN', 'offloaded', '%d of %d tracked files under rendered/ and content/ are only in iCloud (%s): a build '
             'waits while each downloads; in Finder, Keep Downloaded on the folder' % (len(gone), len(tracked),
                                                                                   ', '.join('%s %d' % kv for kv in sorted(tops.items()))), False)]


def check_tools(which=shutil.which):
    out = []
    out.append(('OK', 'cwebp', 'found', False) if which('cwebp') else
               ('WARN', 'cwebp', 'not found: add_trip.py writes the photo copies with it (brew install webp)', False))
    for tool, why in (('node', 'the JavaScript tests run with it and skip without it (brew install node)'),
                      ('python3.12', 'CI runs the suite on 3.12; check.py runs it here too (brew install python@3.12)'),
                      ('gh', 'publish.py --push watches the deploy with it (brew install gh; gh auth login)')):
        out.append(('OK', tool, 'found', False) if which(tool) else ('OK', tool, 'not found (optional): ' + why, False))
    return out


def run(root=ROOT, free_bytes=None, flags=None, which=shutil.which, platform=sys.platform):
    """[(state, name, text, blocks a publish)] of every check, in order."""
    out = [check_disk(root, free_bytes)]
    out += check_index(root)
    out += check_index_copies(root)
    out += check_git(root, which)
    out += check_copies(root)
    out += check_offloaded(root, flags, platform)
    out += check_tools(which)
    return out


def main(argv=None, **kw):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args(argv)
    results = run(**kw)
    for state, name, text, _blocks in results:
        print('%-5s %-13s %s' % (state, name, text))
    blocking = [name for _s, name, _t, blocks in results if blocks]
    print('doctor: %s' % ('ready to publish' if not blocking else 'fix before publishing: ' + ', '.join(dict.fromkeys(blocking))))
    return 1 if blocking else 0


if __name__ == '__main__':
    sys.exit(main())
