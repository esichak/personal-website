"""tools/doctor.py (Phase 8), on a synthetic repository in a temp folder: each check's answer, that it writes nothing
(the whole tree, .git included, is byte for byte and time for time the same after two runs), that it is quick, and
what makes it exit 1. The disk-space and offload probes and the tool lookup are stand-ins; git is real."""
import contextlib
import importlib
import io
import os
import subprocess
import tempfile
import time
import unittest

import helpers

doctor = importlib.import_module('doctor')


def git(root, *args):
    r = subprocess.run(['git', '-C', root] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if r.returncode:
        raise AssertionError(r.stderr)
    return r.stdout


def write(path, text='x'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def snapshot(root):
    """{path: (bytes, mtime)} of every file under root, .git included."""
    out = {}
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            p = os.path.join(dirpath, n)
            with open(p, 'rb') as fh:
                out[os.path.relpath(p, root)] = (fh.read(), os.stat(p).st_mtime_ns)
    return out


ALL_TOOLS = lambda name: '/opt/bin/' + name   # noqa: E731


class DoctorFixture(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        git(self.root, 'init', '-q', '-b', 'main')
        git(self.root, 'config', 'user.email', 'test@example.invalid')
        git(self.root, 'config', 'user.name', 'Synthetic Tester')
        helpers.make_trip(os.path.join(self.root, 'content', 'trips'), 'synd-walk', title='Synthetic Walk', track=True)
        write(os.path.join(self.root, 'rendered', 'trips', 'synd-walk', 'meta.json'), '{}')
        git(self.root, 'add', '--', 'content', 'rendered')
        git(self.root, 'commit', '-q', '-m', 'start')

    def by_name(self, name, **kw):
        """The rows of doctor.run named `name`, with the probes stubbed: plenty of disk, nothing offloaded, every tool."""
        kw.setdefault('free_bytes', 100e9)
        kw.setdefault('flags', lambda p: 0)
        kw.setdefault('which', ALL_TOOLS)
        return [r for r in doctor.run(self.root, **kw) if r[1] == name]

    def main(self, **kw):
        kw.setdefault('free_bytes', 100e9)
        kw.setdefault('flags', lambda p: 0)
        kw.setdefault('which', ALL_TOOLS)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = doctor.main([], root=self.root, **kw)
        return code, out.getvalue()


class DoctorTests(DoctorFixture):

    def test_a_clean_checkout_on_main_is_ready(self):
        code, out = self.main()
        self.assertEqual(code, 0, out)
        self.assertIn('doctor: ready to publish', out)
        self.assertNotIn('WARN', out.replace('WARN  origin', ''))       # no origin in a temp repo: that one warns

    def test_free_disk_under_30_gb_warns_and_cites_the_incident(self):
        (state, _n, text, blocks), = self.by_name('disk', free_bytes=21e9)
        self.assertEqual((state, blocks), ('WARN', False))
        self.assertIn('21 GB free', text)
        self.assertIn('2026-10-10', text)
        (state, _n, text, _b), = self.by_name('disk', free_bytes=31e9)
        self.assertEqual(state, 'OK')

    def test_a_missing_index_blocks_with_the_read_tree_recipe(self):
        os.remove(os.path.join(self.root, '.git', 'index'))
        (state, _n, text, blocks), = self.by_name('git index')
        self.assertEqual((state, blocks), ('WARN', True))
        self.assertIn('git read-tree HEAD', text)
        code, out = self.main()
        self.assertEqual(code, 1)
        self.assertIn('git index', out.splitlines()[-1])

    def test_stray_index_copies_are_listed_with_the_rm_line(self):
        for n in (2, 3):
            write(os.path.join(self.root, '.git', 'index %d' % n), 'old')
        (state, _n, text, blocks), = self.by_name('index copies')
        self.assertEqual((state, blocks), ('WARN', False))
        self.assertIn('rm ".git/index 2" ".git/index 3"', text)
        self.assertTrue(os.path.exists(os.path.join(self.root, '.git', 'index 2')))      # listed, never deleted

    def test_branch_tree_and_identity(self):
        git(self.root, 'switch', '-q', '-c', 'phase-x')
        (state, _n, text, blocks), = self.by_name('branch')
        self.assertEqual((state, blocks), ('WARN', True))
        self.assertIn('phase-x', text)
        git(self.root, 'switch', '-q', 'main')
        write(os.path.join(self.root, 'content', 'trips', 'synd-walk', 'index.md'), 'changed')
        write(os.path.join(self.root, 'untracked.txt'), 'u')
        (state, _n, text, blocks), = self.by_name('tree')
        self.assertEqual((state, blocks), ('WARN', False))     # publish.py commits such files: no reason to stop
        self.assertIn('1 staged or changed tracked file', text)
        self.assertNotIn('restore', text)
        self.assertIn('1 untracked', text)
        git(self.root, 'checkout', '--', 'content')
        (state, _n, text, blocks), = self.by_name('tree')
        self.assertEqual((state, blocks), ('OK', False))         # an untracked file alone does not block
        (state, _n, text, _b), = self.by_name('identity')
        self.assertEqual(state, 'OK')
        self.assertIn('Synthetic Tester', text)

    def test_ahead_and_behind_origin_from_the_tracking_ref(self):
        remote = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(['rm', '-rf', remote]))
        subprocess.run(['git', 'init', '-q', '--bare', remote], check=True)
        git(self.root, 'remote', 'add', 'origin', remote)
        git(self.root, 'push', '-q', 'origin', 'main')
        git(self.root, 'fetch', '-q', 'origin')
        write(os.path.join(self.root, 'content', 'trips', 'synd-walk', 'index.md'), 'next')
        git(self.root, 'commit', '-qam', 'next')
        (state, _n, text, _b), = self.by_name('origin')
        self.assertEqual(state, 'OK')
        self.assertIn('1 ahead, 0 behind origin/main', text)

    def test_conflict_copies_by_top_folder_naming_content_and_staged_ones(self):
        write(os.path.join(self.root, 'rendered', 'trips', 'synd-walk', 'meta 2.json'), '{}')
        write(os.path.join(self.root, 'rendered', 'trips', 'synd-walk 2', 'meta.json'), '{}')      # a copied folder: once
        write(os.path.join(self.root, 'content', 'trips', 'synd-walk', 'index 3.md'), 'copy')
        git(self.root, 'add', '--', 'content/trips/synd-walk/index 3.md')
        rows = self.by_name('copies')
        self.assertIn('3 iCloud conflict copies: content 1, rendered 2', rows[0][2])
        self.assertIn('content/trips/synd-walk/index 3.md', rows[1][2])
        self.assertEqual(rows[2][3], True)                    # a staged copy blocks
        self.assertIn('staged', rows[2][2])

    def test_offloaded_tracked_files_are_counted_on_macos_only(self):
        offloaded = lambda p: doctor.DATALESS if p.endswith('meta.json') else 0   # noqa: E731
        (state, _n, text, blocks), = self.by_name('offloaded', flags=offloaded)
        self.assertEqual((state, blocks), ('WARN', False))
        self.assertIn('1 of 3 tracked files', text)
        self.assertIn('Keep Downloaded', text)
        rows = [r for r in doctor.run(self.root, free_bytes=1e11, flags=None, which=ALL_TOOLS, platform='linux') if r[1] == 'offloaded']
        self.assertEqual(rows[0][2], 'not checked (macOS only)')

    def test_cwebp_warns_and_the_optional_tools_do_not(self):
        rows = {r[1]: r for r in doctor.run(self.root, free_bytes=1e11, flags=lambda p: 0, which=lambda n: None)}
        self.assertEqual(rows['cwebp'][0], 'WARN')
        self.assertIn('brew install webp', rows['cwebp'][2])
        for tool in ('node', 'python3.12', 'gh'):
            self.assertEqual(rows[tool][0], 'OK')
            self.assertIn('optional', rows[tool][2])

    def test_it_writes_nothing_and_is_quick(self):
        write(os.path.join(self.root, 'content', 'trips', 'synd-walk', 'index.md'), 'changed')    # git status would refresh the index
        before = snapshot(self.root)
        t0 = time.time()
        for _ in range(2):
            self.main()
        self.assertLess(time.time() - t0, 4.0)
        self.assertEqual(snapshot(self.root), before)

    def test_the_real_checkout_is_checked_in_under_two_seconds(self):
        out = io.StringIO()
        t0 = time.time()
        with contextlib.redirect_stdout(out):
            doctor.main([])
        self.assertLess(time.time() - t0, 2.0, out.getvalue())


if __name__ == '__main__':
    unittest.main()
