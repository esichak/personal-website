#!/usr/bin/env python3
"""Run the checks a change to tools/, tests/ or assets/ needs before a push, and say which passed.

  python3 tools/check.py           # validate.py, the suite on /usr/bin/python3 and on python3.12 (-W error), the linked build check
  python3 tools/check.py --quick   # the same without the second Python

Every step runs even after one fails; each gets one summary line with its wall time, and the output of a failed step
is printed (its end). The exit status is 1 when any step failed. CI runs the suite on Python 3.12 and this Mac's
/usr/bin/python3 is 3.9: a change has to pass on both. Without python3.12 the second run is skipped with one line
saying how to install it (it is not a failure). The build check is linked into .cache/check (about 4 s).
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_PYTHON = '/usr/bin/python3'
TAIL = 80        # lines of a failed step's output that are printed


def steps(quick=False, which=shutil.which):
    """[(name, command or None, why it is skipped)] in the order they run."""
    first = SYSTEM_PYTHON if os.path.exists(SYSTEM_PYTHON) else sys.executable
    tests = ['-W', 'error', '-m', 'unittest', 'discover', '-s', 'tests']
    out = [('validate', [sys.executable, os.path.join('tools', 'validate.py')], None),
           ('tests (%s)' % os.path.basename(first), [first] + tests, None)]
    if not quick:
        second = which('python3.12')
        out.append(('tests (python3.12)', [second] + tests if second else None,
                    None if second else 'python3.12 not found: brew install python@3.12 (CI runs 3.12)'))
    out.append(('build --check', [sys.executable, os.path.join('tools', 'build.py'), '--check', '--out',
                                  os.path.join('.cache', 'check'), '--link'], None))
    return out


def run_step(cmd, run=subprocess.run):
    """(exit status, output) of one step, run from the checkout with its output captured."""
    r = run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    return r.returncode, r.stdout or ''


def main(argv=None, run=subprocess.run, which=shutil.which, clock=time.time):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--quick', action='store_true', help='skip the suite on python3.12')
    a = ap.parse_args(argv)
    results = []
    for name, cmd, skipped in steps(a.quick, which):
        if cmd is None:
            results.append(('SKIP', name, 0.0, skipped))
            print('SKIP  %-20s %s' % (name, skipped), flush=True)
            continue
        print('...   %-20s %s' % (name, ' '.join(os.path.relpath(c, ROOT) if os.path.isabs(c) and c.startswith(ROOT) else c
                                                  for c in cmd)), flush=True)
        t0 = clock()
        code, output = run_step(cmd, run)
        took = clock() - t0
        if code:
            lines = output.rstrip('\n').split('\n')
            print('--- the end of its output (%d of %d lines):' % (min(TAIL, len(lines)), len(lines)))
            print('\n'.join(lines[-TAIL:]))
        results.append(('OK' if code == 0 else 'FAIL', name, took, ''))
    print()
    for state, name, took, why in results:
        print('%-5s %-20s %s' % (state, name, why if state == 'SKIP' else '%.1f s' % took))
    failed = [name for state, name, _t, _w in results if state == 'FAIL']
    print('check: %s' % ('all passed' if not failed else 'FAILED: ' + ', '.join(failed)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
