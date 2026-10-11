"""Run the whole suite with its test modules in another order: python3 -W error tests/run_orders.py --reverse, or
--shuffle SEED (random.Random(SEED)); with neither, discovery's own order (A to Z). From the repository root.

The suite must not depend on the order of its modules: what one module registers with sitegen.core (the site, the
regions that have a page of their own) may not reach the tests of the next. The tests are loaded exactly as
`python3 -m unittest discover -s tests` loads them, one suite per module; only the order of those suites changes, so
every module keeps its own test order and its tearDownModule (helpers.no_region_pages_left). After the run this says
what core still holds and exits with 1 when a test failed or a region page is still registered.

Not a test module (its name does not start with test_): discovery never loads it.
"""
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/


def module_of(suite):
    """The name of the test module a discovered suite holds ('' for an empty one)."""
    for item in suite:
        name = module_of(item) if isinstance(item, unittest.TestSuite) else type(item).__module__
        if name:
            return name
    return ''


def main(argv):
    os.chdir(ROOT)
    modules = list(unittest.TestLoader().discover('tests'))
    label = 'discovery order'
    if '--reverse' in argv:
        modules.reverse()
        label = 'reverse order'
    elif '--shuffle' in argv:
        seed = int(argv[argv.index('--shuffle') + 1])
        random.Random(seed).shuffle(modules)
        label = 'shuffled with random.Random(%d)' % seed
    print('%d test modules, %s: %s' % (len(modules), label, ' '.join(module_of(m) for m in modules)), file=sys.stderr)
    result = unittest.TextTestRunner(verbosity=0).run(unittest.TestSuite(modules))
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    from sitegen import core
    print('after the run core holds: region pages %r, %d cached site meta, %d registered trips'
          % (dict(core._REGION_PAGES), len(core._SITE_META), len(core._TRIPS_BY_URL)), file=sys.stderr)
    return 0 if result.wasSuccessful() and not core._REGION_PAGES else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
