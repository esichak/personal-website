"""tools/check.py (Phase 8): the steps it runs and in what order, --quick, the skipped second Python, the summary lines
and the exit status. subprocess.run and the clock are stand-ins: nothing here runs the suite inside the suite."""
import contextlib
import importlib
import io
import os
import sys
import unittest

import helpers  # noqa: F401  (puts tools/ on sys.path)

check = importlib.import_module('check')


class Done(object):
    def __init__(self, returncode, stdout=''):
        self.returncode, self.stdout = returncode, stdout


class CheckTests(unittest.TestCase):

    def run_check(self, argv=(), fail=(), which=lambda n: '/opt/bin/' + n):
        calls = []
        ticks = iter(range(0, 1000, 2))

        def run(cmd, **kw):
            calls.append((cmd, kw))
            name = ' '.join(cmd)
            return Done(1, 'line\n' * 100 + 'FAIL: test_synthetic\n') if any(f in name for f in fail) else Done(0, 'ok\n')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check.main(list(argv), run=run, which=which, clock=lambda: next(ticks))
        return code, out.getvalue(), [c for c, _kw in calls], [kw for _c, kw in calls]

    def test_the_four_steps_in_order(self):
        code, out, cmds, kws = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(len(cmds), 4)
        self.assertEqual(cmds[0][1:], [os.path.join('tools', 'validate.py')])
        tests = ['-W', 'error', '-m', 'unittest', 'discover', '-s', 'tests']
        first = check.SYSTEM_PYTHON if os.path.exists(check.SYSTEM_PYTHON) else sys.executable
        self.assertEqual(cmds[1], [first] + tests)
        self.assertEqual(cmds[2], ['/opt/bin/python3.12'] + tests)
        self.assertEqual(cmds[3][1:], [os.path.join('tools', 'build.py'), '--check', '--out', os.path.join('.cache', 'check'), '--link'])
        self.assertTrue(all(kw['cwd'] == check.ROOT for kw in kws))
        summary = out.split('\n\n')[-1].splitlines()
        self.assertEqual([ln.split()[0] for ln in summary[:4]], ['OK'] * 4)
        self.assertTrue(all(ln.endswith(' s') for ln in summary[:4]))
        self.assertIn('2.0 s', summary[0])                     # its own wall time
        self.assertEqual(summary[-1], 'check: all passed')

    def test_quick_skips_the_second_python(self):
        code, _out, cmds, _kws = self.run_check(['--quick'])
        self.assertEqual((code, len(cmds)), (0, 3))
        self.assertNotIn('/opt/bin/python3.12', [c[0] for c in cmds])

    def test_no_python312_is_one_line_and_not_a_failure(self):
        code, out, cmds, _kws = self.run_check(which=lambda n: None)
        self.assertEqual((code, len(cmds)), (0, 3))
        self.assertIn('SKIP  tests (python3.12)', out)
        self.assertIn('brew install python@3.12', out)

    def test_every_step_runs_and_a_failure_is_shown_and_counted(self):
        code, out, cmds, _kws = self.run_check(fail=('validate.py',))
        self.assertEqual(code, 1)
        self.assertEqual(len(cmds), 4)                         # the rest ran all the same
        self.assertIn('FAIL: test_synthetic', out)
        self.assertIn('80 of 101 lines', out)
        self.assertIn('FAIL  validate', out)
        self.assertEqual(out.splitlines()[-1], 'check: FAILED: validate')


if __name__ == '__main__':
    unittest.main()
