"""tools/publish.py, the one publish command (Phase 8), against a temporary git repository holding a synthetic trip.

Every git command is real (git is on the Mac and on the runner); the site check (publish.run_check, which runs build.py
on the real checkout) and the render test (publish.unrendered, render.py's pending_reason) are stand-ins where a test is
about what publish.main does with their answers; one test pins what run_check hands build.main. The deploy watch runs
against a recorded stand-in for subprocess.run, so no test calls gh or the network. Slugs start with 'synp-'.
"""
import contextlib
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import helpers

publish = importlib.import_module('publish')

SLUG = 'synp-ridge-walk'
OTHER = 'synp-old-loop'


def git(root, *args):
    r = subprocess.run(['git', '-C', root] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if r.returncode:
        raise AssertionError('git %s: %s' % (' '.join(args), r.stderr))
    return r.stdout


def write(path, text='x'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


class Repo(unittest.TestCase):
    """A repository laid out like the checkout: one trip already published (OTHER, with its render), rendered/site/ and
    content/home.json committed, and a new trip (SLUG) with its render on disk, not yet in git."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        git(self.root, 'init', '-q', '-b', 'main')
        git(self.root, 'config', 'user.email', 'test@example.invalid')
        git(self.root, 'config', 'user.name', 'Synthetic Tester')
        trips = os.path.join(self.root, 'content', 'trips')
        helpers.make_trip(trips, OTHER, title='Synthetic Old Loop', activity='hike', date='2025-05-01', track=True)
        write(os.path.join(self.root, 'rendered', 'trips', OTHER, 'meta.json'), '{}')
        write(os.path.join(self.root, 'rendered', 'site', 'meta.json'), '{}')
        write(os.path.join(self.root, 'content', 'home.json'), '{"featured_slugs": []}\n')
        write(os.path.join(self.root, 'docs', 'notes.md'), 'synthetic notes\n')
        write(os.path.join(self.root, '.gitignore'), 'rendered/**/* [0-9]*\n.cache/\n')
        git(self.root, 'add', '--', 'content', 'rendered', 'docs', '.gitignore')
        git(self.root, 'commit', '-q', '-m', 'start')
        helpers.make_trip(trips, SLUG, title='Synthetic Ridge Walk', activity='hike', date='2026-06-01', track=True,
                          body='Synthetic words.')
        write(os.path.join(self.root, 'rendered', 'trips', SLUG, 'meta.json'), '{}')
        write(os.path.join(self.root, 'rendered', 'trips', SLUG, 'map-wide.webp'), 'w')
        self.checks = []
        self.stale = []
        p1 = mock.patch.object(publish, 'run_check', self.fake_check)
        p2 = mock.patch.object(publish, 'unrendered', lambda slugs: [s for s in self.stale if s[0] in slugs])
        p3 = mock.patch.object(publish, 'watch', self.fake_watch)
        for p in (p1, p2, p3):
            p.start()
            self.addCleanup(p.stop)
        self.check_fails = False
        self.watched = []

    def fake_check(self):
        self.checks.append(git(self.root, 'diff', '--cached', '--name-only'))       # what was staged when it ran
        return 1 if self.check_fails else 0

    def fake_watch(self, root, sha, slugs):
        self.watched.append((sha, list(slugs)))
        return 0

    def run_main(self, *argv):
        """(exit status, stdout, stderr) of publish.main(argv) on the temp repository."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = publish.main(list(argv), root=self.root)
            except SystemExit as ex:
                code = ex.code
        return code, out.getvalue(), err.getvalue()

    def head(self):
        return git(self.root, 'rev-parse', 'HEAD').strip()

    def last_files(self):
        return sorted(git(self.root, 'show', '--name-only', '--format=', 'HEAD').split())

    def subject(self):
        return git(self.root, 'log', '-1', '--format=%s').strip()

    def staged(self):
        return git(self.root, 'diff', '--cached', '--name-only').split()


class RefusalTests(Repo):

    def test_off_main_it_refuses_and_writes_nothing(self):
        git(self.root, 'switch', '-q', '-c', 'phase-x')
        before = self.head()
        code, _out, err = self.run_main(SLUG)
        self.assertEqual(code, 1)
        self.assertIn('published from main', err)
        self.assertIn('phase-x', err)
        self.assertEqual((self.head(), self.staged(), self.checks), (before, [], []))

    def test_something_unrelated_already_staged_is_refused(self):
        write(os.path.join(self.root, 'docs', 'notes.md'), 'changed\n')
        git(self.root, 'add', '--', 'docs/notes.md')
        code, _out, err = self.run_main(SLUG)
        self.assertEqual(code, 1)
        self.assertIn('docs/notes.md', err)
        self.assertEqual(self.staged(), ['docs/notes.md'])      # left as it was
        self.assertEqual(self.checks, [])

    def test_a_file_of_the_trip_already_staged_is_not_unrelated(self):
        git(self.root, 'add', '--', 'content/trips/%s/index.md' % SLUG)
        code, _out, _err = self.run_main(SLUG)
        self.assertEqual(code, 0)
        self.assertIn('content/trips/%s/index.md' % SLUG, self.last_files())

    def test_a_slug_with_no_folder_and_no_history(self):
        code, _out, err = self.run_main('synp-nothing-here')
        self.assertEqual(code, 1)
        self.assertIn('content/trips/synp-nothing-here/', err)

    def test_a_slug_that_is_not_a_folder_name_is_a_usage_error(self):
        for bad in ('../docs', 'Synp-Ridge', 'a/b', '-x'):
            with self.subTest(slug=bad):
                code, _out, _err = self.run_main('--', bad)
                self.assertEqual(code, 2)

    def test_an_unrendered_trip_is_refused_unless_allowed(self):
        self.stale = [(SLUG, 'new: no maps drawn yet')]
        before = self.head()
        code, _out, err = self.run_main(SLUG)
        self.assertEqual(code, 1)
        self.assertIn('python3 tools/render.py %s' % SLUG, err)
        self.assertIn('new: no maps drawn yet', err)
        self.assertEqual((self.head(), self.checks), (before, []))
        code, _out, _err = self.run_main(SLUG, '--allow-unrendered')
        self.assertEqual(code, 0)
        self.assertEqual(self.subject(), 'Add Synthetic Ridge Walk')

    def test_a_failed_check_stages_nothing(self):
        self.check_fails = True
        before = self.head()
        code, _out, err = self.run_main(SLUG)
        self.assertEqual(code, 1)
        self.assertIn('the check failed', err)
        self.assertEqual((self.head(), self.staged()), (before, []))

    def test_a_conflict_copy_among_the_files_is_refused(self):
        write(os.path.join(self.root, 'content', 'trips', SLUG, 'index 2.md'), 'copy')
        before = self.head()
        code, _out, err = self.run_main(SLUG)
        self.assertEqual(code, 1)
        self.assertIn('index 2.md', err)
        self.assertIn('tidy.py', err)
        self.assertEqual((self.head(), self.staged()), (before, []))

    def test_a_conflict_copy_git_ignores_is_never_staged(self):
        # rendered/ copies are ignored (.gitignore), so git add leaves them out and they are no reason to refuse
        write(os.path.join(self.root, 'rendered', 'trips', SLUG, 'meta 2.json'), '{}')
        code, _out, _err = self.run_main(SLUG)
        self.assertEqual(code, 0)
        self.assertNotIn('rendered/trips/%s/meta 2.json' % SLUG, self.last_files())

    def test_nothing_to_publish(self):
        code, _out, err = self.run_main(OTHER)
        self.assertEqual(code, 1)
        self.assertIn('nothing to publish', err)


class StagingTests(Repo):

    def test_it_stages_exactly_the_trip_and_its_render(self):
        write(os.path.join(self.root, 'docs', 'notes.md'), 'an unrelated edit, not staged\n')
        code, out, _err = self.run_main(SLUG)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.last_files(), ['content/trips/%s/index.md' % SLUG, 'content/trips/%s/track.gpx' % SLUG,
                                             'rendered/trips/%s/map-wide.webp' % SLUG, 'rendered/trips/%s/meta.json' % SLUG])
        self.assertEqual(self.subject(), 'Add Synthetic Ridge Walk')
        self.assertIn('M docs/notes.md', git(self.root, 'status', '--short'))       # still there, unstaged
        self.assertIn('git push origin main', out)
        self.assertEqual(self.watched, [])                                            # no --push, no watch
        self.assertEqual(len(self.checks), 1)
        self.assertEqual(self.checks[0], '')                                          # the check ran before anything was staged

    def test_rendered_site_and_home_json_only_when_they_changed(self):
        write(os.path.join(self.root, 'rendered', 'site', 'meta.json'), '{"hash": "new"}')
        write(os.path.join(self.root, 'content', 'home.json'), '{"featured_slugs": ["%s"]}\n' % SLUG)
        code, _out, _err = self.run_main(SLUG)
        self.assertEqual(code, 0)
        files = self.last_files()
        self.assertIn('rendered/site/meta.json', files)
        self.assertIn('content/home.json', files)
        # and the next publish of an unchanged site stages neither
        write(os.path.join(self.root, 'content', 'trips', OTHER, 'index.md'),
              '---\ntitle: Synthetic Old Loop Renamed\nactivity: hike\ndate: 2025-05-01\n---\n')
        code, _out, _err = self.run_main(OTHER)
        self.assertEqual(code, 0)
        self.assertEqual(self.last_files(), ['content/trips/%s/index.md' % OTHER])
        self.assertEqual(self.subject(), 'Update Synthetic Old Loop Renamed')

    def test_a_removed_trip_is_staged_as_removed(self):
        shutil.rmtree(os.path.join(self.root, 'content', 'trips', OTHER))
        shutil.rmtree(os.path.join(self.root, 'rendered', 'trips', OTHER))
        code, _out, _err = self.run_main(OTHER)
        self.assertEqual(code, 0)
        self.assertEqual(self.subject(), 'Remove %s' % OTHER)
        self.assertEqual(git(self.root, 'ls-files', 'content/trips/%s' % OTHER, 'rendered/trips/%s' % OTHER), '')

    def test_two_trips_and_a_message_of_ones_own(self):
        write(os.path.join(self.root, 'content', 'trips', OTHER, 'index.md'),
              '---\ntitle: Synthetic Old Loop\nactivity: hike\ndate: 2025-05-01\ndraft: true\n---\n')
        code, _out, _err = self.run_main(SLUG, OTHER)
        self.assertEqual(code, 0)
        self.assertEqual(self.subject(), 'Add Synthetic Ridge Walk; Update Synthetic Old Loop')
        code, _out, _err = self.run_main(SLUG, '--message', 'Synthetic message')
        self.assertEqual(code, 1)                    # nothing left to publish
        write(os.path.join(self.root, 'content', 'trips', SLUG, 'index.md'),
              '---\ntitle: Synthetic Ridge Walk\nactivity: hike\ndate: 2026-06-01\n---\nMore synthetic words.\n')
        code, _out, _err = self.run_main(SLUG, '--message', 'Synthetic message')
        self.assertEqual((code, self.subject()), (0, 'Synthetic message'))

    def test_dry_run_writes_nothing(self):
        before = (self.head(), git(self.root, 'status', '--porcelain'))
        index = os.path.join(self.root, '.git', 'index')
        with open(index, 'rb') as fh:
            index_bytes = fh.read()
        code, out, _err = self.run_main(SLUG, '--dry-run')
        self.assertEqual(code, 0)
        self.assertEqual((self.head(), git(self.root, 'status', '--porcelain')), before)
        with open(index, 'rb') as fh:
            self.assertEqual(fh.read(), index_bytes)
        self.assertIn('would stage (4):', out)
        self.assertIn('?? content/trips/%s/index.md' % SLUG, out)
        self.assertIn('would commit: Add Synthetic Ridge Walk', out)
        self.assertEqual(len(self.checks), 1)        # the check runs on a dry run too
        code, _out, _err = self.run_main(SLUG, '--dry-run', '--push')
        self.assertEqual(code, 2)

    def test_push_pushes_main_and_hands_over_to_the_watch(self):
        remote = os.path.join(self.root, '..', os.path.basename(self.root) + '-origin.git')
        self.addCleanup(shutil.rmtree, remote, True)
        subprocess.run(['git', 'init', '-q', '--bare', remote], check=True)
        git(self.root, 'remote', 'add', 'origin', remote)
        git(self.root, 'push', '-q', 'origin', 'main')
        code, out, _err = self.run_main(SLUG, '--push')
        self.assertEqual(code, 0, out)
        sha = self.head()
        self.assertEqual(subprocess.run(['git', '--git-dir', remote, 'rev-parse', 'main'], stdout=subprocess.PIPE,
                                        universal_newlines=True).stdout.strip(), sha)
        self.assertEqual(self.watched, [(sha, [SLUG])])


class ReviewTests(Repo):
    """The cases the review of Phase 8 found: a staged rename out of another trip, what the partial commit would leave
    pointing at trips that are not committed, a render folder removed in an earlier commit, earlier unpushed commits."""

    def test_a_file_moved_out_of_another_trip_is_unrelated(self):
        write(os.path.join(self.root, 'content', 'trips', OTHER, 'notes.md'), 'synthetic notes')
        git(self.root, 'add', '--', 'content/trips/%s/notes.md' % OTHER)
        git(self.root, 'commit', '-q', '-m', 'notes')
        git(self.root, 'mv', 'content/trips/%s/notes.md' % OTHER, 'content/trips/%s/notes.md' % SLUG)
        before = self.head()
        code, _out, err = self.run_main(SLUG)
        self.assertEqual(code, 1)
        self.assertIn('content/trips/%s/notes.md' % OTHER, err)
        self.assertEqual(self.head(), before)

    def test_home_json_featuring_a_trip_not_committed(self):
        write(os.path.join(self.root, 'content', 'home.json'), '{"featured_slugs": ["%s"]}\n' % SLUG)
        code, _out, err = self.run_main(OTHER)          # OTHER has no change of its own: home.json is the change
        self.assertEqual(code, 1)
        self.assertIn('content/home.json features %s' % SLUG, err)
        code, _out, _err = self.run_main(SLUG)            # published with the trip it features: fine
        self.assertEqual(code, 0)
        self.assertIn('content/home.json', self.last_files())

    def test_region_maps_drawn_with_a_trip_not_committed(self):
        write(os.path.join(self.root, 'rendered', 'site', 'meta.json'),
              json.dumps({'maps': {'region-x-desktop': {'trips': [OTHER, SLUG], 'journals': []}}}))
        write(os.path.join(self.root, 'content', 'trips', OTHER, 'index.md'),
              '---\ntitle: Synthetic Old Loop Again\nactivity: hike\ndate: 2025-05-01\n---\n')
        code, _out, err = self.run_main(OTHER)
        self.assertEqual(code, 1)
        self.assertIn('rendered/site (the region maps) was drawn with %s' % SLUG, err)
        code, _out, _err = self.run_main(OTHER, SLUG)
        self.assertEqual(code, 0)

    def test_a_write_up_linking_to_a_trip_not_committed(self):
        write(os.path.join(self.root, 'content', 'trips', OTHER, 'index.md'),
              '---\ntitle: Synthetic Old Loop\nactivity: hike\ndate: 2025-05-01\n---\nSee [the walk](../%s/).\n' % SLUG)
        code, _out, err = self.run_main(OTHER)
        self.assertEqual(code, 1)
        self.assertIn('the write-up of %s links to %s' % (OTHER, SLUG), err)
        # a draft is no reason: its page is not built here either
        index = os.path.join(self.root, 'content', 'trips', SLUG, 'index.md')
        with open(index, encoding='utf-8') as fh:
            text = fh.read()
        write(index, text.replace('\n---\n', '\ndraft: true\n---\n', 1))
        self.assertEqual(self.run_main(OTHER)[0], 1)    # still not committed, and the link would break on GitHub

    def test_a_render_folder_removed_in_an_earlier_commit(self):
        shutil.rmtree(os.path.join(self.root, 'rendered', 'trips', OTHER))
        git(self.root, 'add', '--', 'rendered/trips/%s' % OTHER)
        git(self.root, 'commit', '-q', '-m', 'track removed, render gone')
        write(os.path.join(self.root, 'content', 'trips', OTHER, 'index.md'),
              '---\ntitle: Synthetic Old Loop Edited\nactivity: hike\ndate: 2025-05-01\n---\n')
        code, out, err = self.run_main(OTHER)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.last_files(), ['content/trips/%s/index.md' % OTHER])

    def test_push_refuses_earlier_commits_not_on_github(self):
        remote = os.path.join(self.root, '..', os.path.basename(self.root) + '-origin2.git')
        self.addCleanup(shutil.rmtree, remote, True)
        subprocess.run(['git', 'init', '-q', '--bare', remote], check=True)
        git(self.root, 'remote', 'add', 'origin', remote)
        git(self.root, 'push', '-q', 'origin', 'main')
        git(self.root, 'fetch', '-q', 'origin')
        write(os.path.join(self.root, 'docs', 'notes.md'), 'a local commit\n')
        git(self.root, 'commit', '-qam', 'Synthetic local change')
        before = self.head()
        code, _out, err = self.run_main(SLUG, '--push')
        self.assertEqual(code, 1)
        self.assertIn('Synthetic local change', err)
        self.assertEqual((self.head(), self.staged(), self.watched), (before, [], []))


class SourceTests(unittest.TestCase):

    def test_it_never_adds_everything(self):
        with open(publish.__file__, encoding='utf-8') as fh:
            src = fh.read()
        self.assertIsNone(re.search(r"git add -A|git add \.|'add', '-A'|'add', '\.'|'add', '--all'", src))
        self.assertEqual(src.count("git(root, 'add', '--', *paths)"), 1)

    def test_the_check_is_a_linked_build_into_the_cache(self):
        build = importlib.import_module('build')
        with mock.patch.object(build, 'main', return_value=0) as m:
            self.assertEqual(publish.run_check(), 0)
        self.assertEqual(m.call_args[0][0], ['--out', os.path.join(publish.ROOT, '.cache', 'publish-site'), '--link', '--check'])


class Done(object):
    def __init__(self, returncode=0, stdout=''):
        self.returncode, self.stdout = returncode, stdout


class WatchTests(unittest.TestCase):
    """publish.watch with a recorded stand-in for subprocess.run: what it asks gh, and what it says."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        helpers.make_trip(os.path.join(self.root, 'content', 'trips'), SLUG, title='Synthetic Ridge Walk', track=True)
        helpers.make_trip(os.path.join(self.root, 'content', 'trips'), OTHER, title='Synthetic Old Loop', draft=True)
        self.calls = []
        self.cwds = []

    def runner(self, answers):
        def run(cmd, **kw):
            self.calls.append(cmd[1:])
            self.cwds.append(kw.get('cwd'))
            for prefix, done in answers:
                if cmd[1:1 + len(prefix)] == prefix:
                    return done() if callable(done) else done
            raise AssertionError('unexpected command %r' % cmd)
        return run

    def watch(self, answers, gh='/usr/local/bin/gh'):
        out = io.StringIO()
        sleeps = []
        with contextlib.redirect_stdout(out):
            code = publish.watch(self.root, 'abc1234def', [SLUG, OTHER], run=self.runner(answers), sleep=sleeps.append, gh=gh)
        return code, out.getvalue(), sleeps

    def test_without_gh_it_points_at_the_actions_page_and_succeeds(self):
        with mock.patch('shutil.which', return_value=None):
            code, out, _s = self.watch([], gh='')
        self.assertEqual(code, 0)
        self.assertIn(publish.ACTIONS, out)
        self.assertEqual(self.calls, [])

    def test_signed_out_it_points_at_the_actions_page_and_succeeds(self):
        code, out, _s = self.watch([(['auth', 'status'], Done(1))])
        self.assertEqual(code, 0)
        self.assertIn('gh auth login', out)
        self.assertIn(publish.ACTIONS, out)

    def test_a_run_that_passes_prints_where_each_trip_is(self):
        code, out, sleeps = self.watch([(['auth', 'status'], Done(0)),
                                        (['run', 'list'], Done(0, '[{"databaseId": 42, "status": "queued"}]')),
                                        (['run', 'watch', '42', '--exit-status'], Done(0))])
        self.assertEqual(code, 0)
        self.assertIn(['run', 'list', '--commit', 'abc1234def', '--json', 'databaseId,status', '--limit', '1'], self.calls)
        self.assertIn('live: %strips/%s/' % (publish.SITE_URL, SLUG), out)
        self.assertIn('off the site: %strips/%s/' % (publish.SITE_URL, OTHER), out)       # a draft is taken off
        self.assertEqual(sleeps, [])
        self.assertEqual(set(self.cwds), {self.root})          # gh asked in the checkout, wherever the command ran

    def test_a_run_a_newer_push_cancelled_is_not_a_failure(self):
        code, out, _s = self.watch([(['auth', 'status'], Done(0)), (['run', 'list'], Done(0, '[{"databaseId": 5}]')),
                                    (['run', 'watch', '5', '--exit-status'], Done(1)),
                                    (['run', 'view', '5', '--json', 'conclusion'], Done(0, 'cancelled\n'))])
        self.assertEqual(code, 0)
        self.assertIn('was cancelled', out)
        self.assertNotIn('old site is still up', out)

    def test_a_run_that_appears_late_is_waited_for(self):
        answers = iter([Done(0, '[]'), Done(0, '[]'), Done(0, '[{"databaseId": 7}]')])
        code, _out, sleeps = self.watch([(['auth', 'status'], Done(0)), (['run', 'list'], lambda: next(answers)),
                                         (['run', 'watch', '7', '--exit-status'], Done(0))])
        self.assertEqual(code, 0)
        self.assertEqual(sleeps, [publish.FIND_WAIT] * 2)

    def test_no_run_after_the_wait_points_at_the_actions_page(self):
        code, out, sleeps = self.watch([(['auth', 'status'], Done(0)), (['run', 'list'], Done(0, '[]'))])
        self.assertEqual(code, 0)
        self.assertIn(publish.ACTIONS, out)
        self.assertEqual(len(sleeps), publish.FIND_TRIES - 1)
        self.assertLessEqual(publish.FIND_TRIES * publish.FIND_WAIT, 32)

    def test_a_failed_run_says_the_old_site_is_up_and_shows_the_failed_log(self):
        log = '\n'.join('line %d' % i for i in range(100)) + '\nFAIL: test_synthetic\n'
        code, out, _s = self.watch([(['auth', 'status'], Done(0)), (['run', 'list'], Done(0, '[{"databaseId": 9}]')),
                                    (['run', 'watch', '9', '--exit-status'], Done(1)),
                                    (['run', 'view', '9', '--json', 'conclusion'], Done(0, 'failure\n')),
                                    (['run', 'view', '9', '--log-failed'], Done(0, log))])
        self.assertEqual(code, 1)
        self.assertIn('the old site is still up', out)
        self.assertIn('gh run view 9 --log-failed', out)
        self.assertIn('FAIL: test_synthetic', out)
        self.assertIn('lines before these', out)
        self.assertNotIn('live:', out)


if __name__ == '__main__':
    unittest.main()
