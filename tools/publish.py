#!/usr/bin/env python3
"""Publish trips: check the site, stage exactly their files, commit, and with --push push to main and watch the deploy.

  python3 tools/publish.py rose-knob-peak                # check, stage, commit; then prints the push line
  python3 tools/publish.py rose-knob-peak --dry-run      # everything but staging and the commit: writes nothing
  python3 tools/publish.py rose-knob-peak --push         # ... then pushes to main and watches the GitHub Actions run
  python3 tools/publish.py one-trip another-trip --message "Add two spring tours"

It stops at the first thing that is wrong, in this order: the checkout is not on main; with --push, main holds earlier
commits that are not on GitHub; something unrelated is already staged; a slug has no folder and no history; a trip's
maps are not drawn (render.py --status; --allow-unrendered publishes it anyway); the site check (build.py --out
.cache/publish-site --link --check) fails; a conflict copy is among the files to stage; what is staged names a trip
that is in this folder but not committed and not being published (content/home.json features it, rendered/site was
drawn with it, or a published write-up links to it), which the local check sees and GitHub's would not. It stages content/trips/<slug>/, rendered/trips/<slug>/ when it is there or was,
rendered/site/ when it changed and content/home.json when it changed: never the whole tree. Commit message: 'Add
<title>' for a trip new to git, 'Update <title>' for one it knows, 'Remove <slug>' for a folder that is gone.
ADDING-TRIPS.md step 5 lists the commands it runs, to type by hand if this tool ever fails.
"""
import argparse
import functools
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import frontmatter  # noqa: E402
from sitegen import sitecheck  # noqa: E402

SLUG = re.compile(r'^[a-z0-9][a-z0-9-]*$')
CHECK_OUT = os.path.join('.cache', 'publish-site')
SITE_URL = 'https://esichak.github.io/personal-website/'
ACTIONS = 'https://github.com/esichak/personal-website/actions'
FIND_TRIES, FIND_WAIT = 15, 2      # looking for the push's Actions run: about 30 s
LOG_LINES = 60                     # the end of a failed run's log that is printed


def git(root, *args):
    return subprocess.run(['git', '-C', root] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


def changed(root, path):
    """Whether git sees a change under path (staged or not; untracked files count, ignored ones do not)."""
    return bool(git(root, 'status', '--porcelain', '--untracked-files=all', '--', path).stdout.strip())


def known(root, path):
    """Whether path is in git: tracked now, or in an earlier commit (a folder that was deleted since)."""
    return bool(git(root, 'log', '-1', '--format=%h', '--', path).stdout.strip())


def tracked(root, path):
    """Whether the index holds anything under path (what git add can stage a removal of)."""
    return bool(git(root, 'ls-files', '--', path).stdout.strip())


def committed(root, slug):
    """Whether the trip is in the commit main points at."""
    return git(root, 'cat-file', '-e', 'HEAD:content/trips/%s/index.md' % slug).returncode == 0


def unpublished(root, slug, ours):
    """A trip that is in this folder but in no commit and not among the slugs being published now: the local check
    builds it, GitHub's would not."""
    return (slug not in ours and os.path.exists(os.path.join(root, 'content', 'trips', slug, 'index.md'))
            and not committed(root, slug))


def crossings(root, slugs, paths):
    """[(what, slug)] for every trip that what is staged names although it is unpublished (see unpublished)."""
    out = []
    if 'content/home.json' in paths:
        try:
            with open(os.path.join(root, 'content', 'home.json'), encoding='utf-8') as fh:
                featured = json.load(fh).get('featured_slugs') or []
        except (OSError, ValueError, AttributeError):
            featured = []
        out += [('content/home.json features', s) for s in featured if isinstance(s, str) and unpublished(root, s, slugs)]
    if 'rendered/site' in paths:
        try:
            with open(os.path.join(root, 'rendered', 'site', 'meta.json'), encoding='utf-8') as fh:
                maps = json.load(fh).get('maps') or {}
        except (OSError, ValueError, AttributeError):
            maps = {}
        drawn = set()
        for m in maps.values() if isinstance(maps, dict) else []:
            if isinstance(m, dict):
                drawn.update(s for s in (m.get('trips') or []) if isinstance(s, str))
                drawn.update(j.get('slug') for j in (m.get('journals') or []) if isinstance(j, dict) and isinstance(j.get('slug'), str))
        out += [('rendered/site (the region maps) was drawn with', s) for s in sorted(drawn) if unpublished(root, s, slugs)]
    folder = os.path.join(root, 'content', 'trips')
    waiting = [s for s in (sorted(os.listdir(folder)) if os.path.isdir(folder) else []) if unpublished(root, s, slugs)]
    for slug in slugs:
        text = ''
        for dirpath, _dirs, names in os.walk(os.path.join(folder, slug)):
            for n in names:
                if n.endswith('.md'):
                    try:
                        with open(os.path.join(dirpath, n), encoding='utf-8') as fh:
                            text += fh.read()
                    except (OSError, UnicodeDecodeError):
                        pass
        out += [('the write-up of %s links to' % slug, w) for w in waiting
                if re.search(r'(?<![\w-])%s/' % re.escape(w), text)]
    return out


def pending_files(root, paths):
    """[(two-letter status, path)] of what git would stage under paths, from git status --porcelain -z (names exact,
    whatever they hold); a staged rename's old name is skipped."""
    out = git(root, 'status', '--porcelain', '-z', '--no-renames', '--untracked-files=all', '--', *paths).stdout.split('\0')
    entries, i = [], 0
    while i < len(out):
        rec = out[i]
        i += 1
        if len(rec) < 4:
            continue
        entries.append((rec[:2], rec[3:]))
        if rec[0] in 'RC':
            i += 1                  # the rename's source follows as its own field
    return entries


def title_of(root, slug):
    try:
        with open(os.path.join(root, 'content', 'trips', slug, 'index.md'), encoding='utf-8') as fh:
            meta, _body = frontmatter.split(fh.read())
        return str(meta.get('title') or slug), bool(meta.get('draft'))
    except (OSError, ValueError):
        return slug, False


def message_for(root, slugs):
    parts = []
    for slug in slugs:
        if not os.path.isdir(os.path.join(root, 'content', 'trips', slug)):
            parts.append('Remove %s' % slug)
            continue
        title, _draft = title_of(root, slug)
        parts.append('%s %s' % ('Update' if known(root, 'content/trips/' + slug) else 'Add', title))
    return '; '.join(parts)


def unrendered(slugs):
    """[(slug, why)] of the trips named whose maps a render.py run would draw now (render.py --status's test). A draft or
    a removed trip has none to draw."""
    import render
    trips = {t['slug']: t for t in content.load_all(include_drafts=True)}
    out = []
    for slug in slugs:
        t = trips.get(slug)
        why = None if (t is None or t['draft']) else render.pending_reason(t)
        if why:
            out.append((slug, why))
    return out


def run_check():
    """The site check, linked into .cache/publish-site (about 4 s): build.py's validation, build and --check."""
    import build
    return build.main(['--out', os.path.join(ROOT, CHECK_OUT), '--link', '--check'])


def watch(root, sha, slugs, run=subprocess.run, sleep=time.sleep, gh=None):
    """After the push: find the Actions run of sha, watch it to the end and say where the trips are live, or that it
    failed with the end of its log. Without gh, or gh signed out, it prints the Actions page: never a failure. gh runs
    in the checkout, so it finds the repository whatever folder the command was started in."""
    run = functools.partial(run, cwd=root)
    gh = gh if gh is not None else shutil.which('gh')
    if not gh:
        print('gh is not installed: watch the deploy at %s' % ACTIONS)
        return 0
    if run([gh, 'auth', 'status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode != 0:
        print('gh is not signed in (gh auth login): watch the deploy at %s' % ACTIONS)
        return 0
    run_id = None
    for n in range(FIND_TRIES):
        r = run([gh, 'run', 'list', '--commit', sha, '--json', 'databaseId,status', '--limit', '1'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        try:
            found = json.loads(r.stdout or '[]') if r.returncode == 0 else []
        except ValueError:
            found = []
        if found:
            run_id = found[0].get('databaseId')
            break
        if n + 1 < FIND_TRIES:
            sleep(FIND_WAIT)
    if run_id is None:
        print('no Actions run for %s yet: watch the deploy at %s' % (sha[:7], ACTIONS))
        return 0
    print('watching run %s (gh run watch %s) ...' % (run_id, run_id))
    if run([gh, 'run', 'watch', str(run_id), '--exit-status']).returncode == 0:
        for slug in slugs:
            title, draft = title_of(root, slug)
            gone = draft or not os.path.isdir(os.path.join(root, 'content', 'trips', slug))
            print('%s %strips/%s/' % ('off the site:' if gone else 'live:', SITE_URL, slug))
        return 0
    seen = run([gh, 'run', 'view', str(run_id), '--json', 'conclusion', '--jq', '.conclusion'],
               stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True).stdout.strip()
    if seen == 'cancelled':
        print('run %s was cancelled: a newer push replaced it, and that push\'s run publishes this commit too (gh run list -L 3)'
              % run_id)
        return 0
    print('the deploy failed; the old site is still up. The failed steps (gh run view %s --log-failed):' % run_id)
    log = run([gh, 'run', 'view', str(run_id), '--log-failed'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
              universal_newlines=True).stdout or ''
    lines = log.rstrip('\n').split('\n') if log.strip() else []
    if len(lines) > LOG_LINES:
        print('... (%d lines before these)' % (len(lines) - LOG_LINES))
    for line in lines[-LOG_LINES:]:
        print(line)
    return 1


def refuse(text):
    print('publish: %s' % text, file=sys.stderr)
    return 1


def main(argv=None, root=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('slugs', nargs='+', metavar='SLUG', help='a folder name under content/trips/')
    ap.add_argument('--message', help='the commit message (default: Add / Update <title>, Remove <slug>)')
    ap.add_argument('--dry-run', action='store_true', help='check and list what would be staged and committed; write nothing')
    ap.add_argument('--push', action='store_true', help='after the commit, push to main and watch the deploy')
    ap.add_argument('--allow-unrendered', action='store_true', help="publish a trip whose maps render.py would still draw")
    a = ap.parse_args(argv)
    root = root or ROOT
    slugs = list(dict.fromkeys(a.slugs))
    bad = [s for s in slugs if not SLUG.match(s)]
    if bad:
        ap.error('a slug is a folder name under content/trips/ (lower-case letters, digits, hyphens): %s' % ', '.join(bad))
    if a.dry_run and a.push:
        ap.error('--dry-run writes nothing, so it cannot --push')

    branch = git(root, 'branch', '--show-current').stdout.strip()
    if branch != 'main':
        return refuse('the site is published from main, and this checkout is on %s; git switch main first'
                      % (branch or 'no branch (a detached HEAD)'))
    if a.push:
        ahead = git(root, 'log', '--format=%h %s', 'origin/main..HEAD').stdout.strip()
        if ahead:
            return refuse('main holds commits that are not on GitHub yet (as of the last fetch), and --push would publish '
                          'them with this one:\n  %s\nread them, push them yourself (git push origin main), or publish '
                          'without --push' % ahead.replace('\n', '\n  '))
    targets = []
    for slug in slugs:
        folder = 'content/trips/' + slug
        if not os.path.isdir(os.path.join(root, folder)) and not known(root, folder):
            return refuse('no %s/ here and none in git' % folder)
        targets += [folder, 'rendered/trips/' + slug]

    def ours(path):
        return (path == 'content/home.json' or path.startswith('rendered/site/')
                or any(path == t or path.startswith(t + '/') for t in targets))
    # both names of a staged rename: a file moved out of another trip's folder is unrelated to this one
    staged = [p for p in git(root, 'diff', '--cached', '--name-only', '--no-renames', '-z').stdout.split('\0') if p]
    others = [p for p in staged if not ours(p)]
    if others:
        return refuse('already staged and not part of %s: %s; commit or unstage them first (git restore --staged <path>)'
                      % (', '.join(slugs), ', '.join(others[:10]) + (' ...' if len(others) > 10 else '')))

    if not a.allow_unrendered:
        try:
            stale = unrendered(slugs)
        except content.ContentError as ex:
            return refuse(str(ex))
        if stale:
            for slug, why in stale:
                print('  %-44s %s' % (slug, why), file=sys.stderr)
            return refuse('maps not drawn: run python3 tools/render.py %s (needs the internet), or publish with '
                          '--allow-unrendered' % ' '.join(s for s, _why in stale))

    print('checking the site (build.py --out %s --link --check) ...' % CHECK_OUT)
    if run_check():
        return refuse('the check failed: nothing was staged or committed')

    # a folder removed in an earlier commit is neither here nor in the index: git add would stop on it
    paths = [p for p in targets if os.path.lexists(os.path.join(root, p)) or tracked(root, p)]
    for extra in ('rendered/site', 'content/home.json'):
        if changed(root, extra):
            paths.append(extra)
    entries = pending_files(root, paths)
    copies = [p for _code, p in entries if sitecheck.conflict_copy(p) and os.path.lexists(os.path.join(root, p))]
    if copies:
        return refuse('iCloud conflict copies among the files to stage: %s; delete them (python3 tools/tidy.py lists '
                      'them) and run again' % ', '.join(copies))
    if not entries and not staged:
        return refuse('nothing to publish: no change under %s' % ', '.join(paths))
    crossed = crossings(root, slugs, paths)
    if crossed:
        for what, slug in crossed:
            print('  %s %s' % (what, slug), file=sys.stderr)
        return refuse('these trips are here but not committed, so the check on GitHub would fail or show them early: publish '
                      'them in the same command (publish.py %s %s), or after them, or set draft: true'
                      % (' '.join(slugs), ' '.join(sorted({s for _w, s in crossed}))))
    msg = a.message or message_for(root, slugs)

    if a.dry_run:
        print('would stage (%d):' % len(entries))
        for code, p in entries:
            print('  %s %s' % (code, p))
        print('would commit: %s' % msg)
        print('dry run: nothing staged, nothing committed')
        return 0
    add = git(root, 'add', '--', *paths)
    if add.returncode:
        return refuse('git add failed: %s' % add.stderr.strip())
    print('staged:')
    print(git(root, 'diff', '--cached', '--name-status').stdout.rstrip('\n'))
    done = git(root, 'commit', '-q', '-m', msg)
    if done.returncode:
        return refuse('git commit failed (the files stay staged): %s' % (done.stderr.strip() or done.stdout.strip()))
    sha = git(root, 'rev-parse', 'HEAD').stdout.strip()
    print('committed %s %s' % (sha[:7], msg))
    if not a.push:
        print('to publish it: git push origin main')
        return 0
    pushed = git(root, 'push', 'origin', 'main')
    if pushed.returncode:
        print(pushed.stderr.strip(), file=sys.stderr)
        return refuse('the push failed; the commit is made: git push origin main when the problem is fixed')
    print('pushed %s to main' % sha[:7])
    return watch(root, sha, slugs)


if __name__ == '__main__':
    sys.exit(main())
