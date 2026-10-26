"""The deploy workflow (.github/workflows/pages.yml) after Phase 8: the actions' majors, Node pinned before the tests,
the unit tests only when code changed since the last successful push run, the dispatch input that builds a past commit,
the paths a push may change without starting a run, and the Chrome smoke job that never gates the deploy. The 'changed'
step's own shell script is taken out of the file and run with bash -eo pipefail in a temporary git repository, with a
stand-in `gh` on PATH that answers the last successful run's commit: a content push, a code push, a content push after
a code push that failed, no successful run yet, an answer that is no commit, a commit that cannot be fetched, and a
manual run."""
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest

import helpers  # noqa: F401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLOW = os.path.join(ROOT, '.github', 'workflows', 'pages.yml')


def flow():
    with open(FLOW, encoding='utf-8') as fh:
        return fh.read()


def job(text, name):
    """The lines of one job, from '  <name>:' to the next job."""
    m = re.search(r'(?ms)^  %s:\n(.*?)(?=^  \w[\w-]*:\n|\Z)' % re.escape(name), text)
    return m.group(1) if m else ''


def changed_script(text):
    m = re.search(r'(?ms)id: changed\n.*?run: \|\n(.*?)(?=^      - )', text)
    return textwrap.dedent(m.group(1))


class WorkflowShapeTests(unittest.TestCase):

    def test_the_actions_are_the_majors_that_run_on_node_24(self):
        # bumped together (docs/DEVELOPING.md, Yearly upkeep, item 2); upload-pages-artifact@v5 uploads through
        # upload-artifact@v7, which the smoke job's download-artifact@v8 reads
        uses = re.findall(r'uses: (\S+)', flow())
        self.assertEqual(sorted(set(uses)), ['actions/checkout@v7', 'actions/configure-pages@v6',
                                             'actions/deploy-pages@v5', 'actions/download-artifact@v8',
                                             'actions/setup-node@v7', 'actions/setup-python@v7',
                                             'actions/upload-pages-artifact@v5'])

    def test_node_22_is_set_up_before_the_tests(self):
        build = job(flow(), 'build')
        self.assertIn("uses: actions/setup-node@v7\n        with:\n          node-version: '22'", build)
        self.assertLess(build.index('actions/setup-node@v7'), build.index('name: Unit tests'))

    def test_the_tests_run_only_when_the_changed_step_says_code(self):
        build = job(flow(), 'build')
        self.assertIn("- name: Unit tests\n        if: steps.changed.outputs.code == 'true'\n        run: python3 -m unittest discover -s tests", build)
        self.assertLess(build.index('id: changed'), build.index('name: Unit tests'))
        self.assertIn('id: changed\n        shell: bash\n', build)                 # bash -eo pipefail, as tested below
        self.assertIn('  actions: read', flow())                                  # gh run list in that step
        self.assertIn('- name: Build\n        run: python3 tools/build.py --check', build)       # the build always runs

    def test_a_dispatch_builds_the_commit_it_is_given(self):
        text = flow()
        self.assertIn("workflow_dispatch:\n    inputs:\n      ref:\n        description: 'commit to build and deploy (empty: this branch)'\n"
                      "        required: false", text)
        self.assertEqual(text.count('ref: ${{ inputs.ref || github.sha }}'), 2)     # the build and the smoke checkout

    def test_paths_a_push_may_change_without_a_run(self):
        ignored = re.search(r'(?ms)paths-ignore:\n(.*?)\n  workflow_dispatch', flow()).group(1)
        names = re.findall(r"- '([^']+)'", ignored)
        self.assertIn('*.md', names)
        self.assertIn('docs/WEBSITE_IMPLEMENTATION_LOG.md', names)
        for never in ('docs/PRIVACY_NOTES.md', 'content', 'rendered', 'docs/**', 'docs/*.md', '**/*.md', 'tools', 'tests', 'assets'):
            self.assertFalse(any(n == never or n.startswith(never + '/') for n in names), never)

    def test_the_smoke_job_reports_and_the_deploy_does_not_wait_for_it(self):
        text = flow()
        smoke, deploy = job(text, 'smoke'), job(text, 'deploy')
        self.assertIn('needs: build', smoke)
        self.assertIn('continue-on-error: true', smoke)
        self.assertIn('timeout-minutes: 10', smoke)
        self.assertIn('python3 tools/smoke.py _site', smoke)
        self.assertIn('needs: build\n', deploy)
        self.assertNotIn('smoke', deploy)
        # the deploy job is as it was
        self.assertIn('uses: actions/deploy-pages@v5', deploy)


class ChangedStepTests(unittest.TestCase):
    """The step's script with bash, in a repository whose 'origin' is a bare copy holding its commits, and a `gh` that
    prints what the test says the last successful push run was (FAKE_BASE)."""

    def setUp(self):
        if not shutil.which('bash'):
            self.skipTest('bash is not installed')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.repo = os.path.join(self.tmp, 'repo')
        self.git('init', '-q', '-b', 'main', self.repo, cwd=self.tmp)
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Synthetic Tester')
        self.bin = os.path.join(self.tmp, 'bin')
        os.makedirs(self.bin)
        with open(os.path.join(self.bin, 'gh'), 'w') as fh:       # gh run list ... --jq ...: the run's headSha, or ''
            fh.write('#!/bin/sh\necho "$* " > "$GH_ARGS"\nprintf \'%s\\n\' "$FAKE_BASE"\n')
        os.chmod(os.path.join(self.bin, 'gh'), 0o755)
        self.script = changed_script(flow())

    def git(self, *args, cwd=None):
        r = subprocess.run(['git'] + list(args), cwd=cwd or self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True)
        if r.returncode:
            raise AssertionError(r.stderr)
        return r.stdout.strip()

    def commit(self, path, text='x'):
        full = os.path.join(self.repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w') as fh:
            fh.write(text)
        self.git('add', '--', path)
        self.git('commit', '-q', '-m', 'change %s' % path)
        return self.git('rev-parse', 'HEAD')

    def decide(self, base, event='push'):
        bare = os.path.join(self.tmp, 'origin.git')
        if not os.path.exists(bare):
            self.git('clone', '-q', '--bare', self.repo, bare, cwd=self.tmp)
            self.git('remote', 'add', 'origin', bare)
        else:
            self.git('push', '-q', 'origin', 'main')
        out = os.path.join(self.tmp, 'output')
        open(out, 'w').close()
        self.gh_args = os.path.join(self.tmp, 'gh-args')
        env = dict(os.environ, EVENT=event, SHA=self.git('rev-parse', 'HEAD'), GITHUB_OUTPUT=out, FAKE_BASE=base,
                   GH_ARGS=self.gh_args, PATH=self.bin + os.pathsep + os.environ.get('PATH', ''))
        # as Actions runs a step whose shell is bash
        r = subprocess.run(['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', self.script], cwd=self.repo, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out) as fh:
            return fh.read().strip()

    def test_it_asks_for_the_last_successful_push_run_on_main(self):
        good = self.commit('content/start.md')
        self.decide(good)
        with open(self.gh_args) as fh:
            args = fh.read().split()
        self.assertEqual(args[:2], ['run', 'list'])
        for pair in (['--workflow', 'pages.yml'], ['--branch', 'main'], ['--event', 'push'], ['--status', 'success'],
                     ['--limit', '1'], ['--json', 'headSha']):
            self.assertIn(' '.join(pair), ' '.join(args))

    def test_a_content_push_skips_the_tests(self):
        good = self.commit('content/trips/synw-a/index.md')
        self.commit('content/trips/synw-a/index.md', 'edited')
        self.commit('rendered/trips/synw-a/meta.json', '{}')
        self.assertEqual(self.decide(good), 'code=false')

    def test_a_push_touching_code_or_the_privacy_notes_runs_them(self):
        for path in ('tools/build.py', 'tests/test_x.py', 'assets/js/base.js', '.github/workflows/pages.yml', 'docs/PRIVACY_NOTES.md'):
            with self.subTest(path=path):
                good = self.commit('content/x-%d.md' % len(path))
                self.commit(path, path)
                self.assertEqual(self.decide(good), 'code=true')

    def test_a_content_push_after_a_code_push_that_failed_runs_them(self):
        # the review's case: the code push's run failed (or was cancelled), so the last success is the commit before it
        good = self.commit('content/start.md')
        self.commit('tools/build.py', 'code whose tests failed')
        self.commit('content/trips/synw-b/index.md', 'a trip published after it')
        self.assertEqual(self.decide(good), 'code=true')

    def test_other_docs_do_not_count_as_code(self):
        good = self.commit('content/start.md')
        self.commit('docs/DEVELOPING.md', 'd')
        self.commit('docs/PRIVACY_NOTES.md.bak', 'not the notes')
        self.assertEqual(self.decide(good), 'code=false')

    def test_no_successful_run_an_odd_answer_or_a_manual_run_runs_them(self):
        self.commit('content/start.md')
        for base in ('', 'null', 'abc1234', 'not a commit at all', '1234567890abcdef1234567890abcdef12345678'):
            with self.subTest(base=base):
                self.assertEqual(self.decide(base), 'code=true')
        good = self.git('rev-parse', 'HEAD')
        self.assertEqual(self.decide(good, event='workflow_dispatch'), 'code=true')

    def test_a_push_of_thousands_of_files_with_code_among_them_runs_them(self):
        # grep must read the whole list: one that stops at the first match breaks the pipe, and under pipefail the
        # step would then say code=false
        good = self.commit('content/start.md')
        for n in range(3000):
            path = os.path.join(self.repo, 'rendered', 'trips', 'synw-%04d' % n, 'meta.json')
            os.makedirs(os.path.dirname(path))
            open(path, 'w').close()
        tools = os.path.join(self.repo, 'assets', 'a.js')
        os.makedirs(os.path.dirname(tools))
        open(tools, 'w').close()
        self.git('add', '--', 'rendered', 'assets')
        self.git('commit', '-q', '-m', 'many')
        self.assertEqual(self.decide(good), 'code=true')


if __name__ == '__main__':
    unittest.main()
