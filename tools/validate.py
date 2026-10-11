#!/usr/bin/env python3
"""Check the content before it is built: every broken file in one run, one line each (stdlib only).

  python3 tools/validate.py                 # content/: errors and warnings, then a summary line
  python3 tools/validate.py -v              # also list the notes (optional fields that are simply absent)
  python3 tools/validate.py -q              # errors and the summary line only
  python3 tools/validate.py --strict        # a warning fails the run too
  python3 tools/validate.py --json          # every finding as JSON: [{"level", "file", "text"}, ...]
  python3 tools/validate.py --site _site    # also check a built site (links, metadata, sitemap, feed, GPX copies)
  python3 tools/validate.py --content DIR   # a folder laid out like content/ (trips/ and home.json inside)

Exit status: 0 when there is no error (warnings may print), 1 for an error, or for a warning under --strict, 2 for a
mistake on the command line. The rules are in tools/lib/checks.py (content) and tools/sitegen/sitecheck.py (a built
site); tools/build.py runs the content rules before every build, so this command is for looking without building.
It reads only: nothing is written, rendered or fetched.
"""
import argparse
import datetime
import importlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import checks  # noqa: E402
import content  # noqa: E402


class Usage(Exception):
    """A mistake on the command line that argparse cannot see (a folder that is not there): one line, exit status 2."""


def _today(text):
    """--today: a real calendar day written YYYY-MM-DD, or argparse's own usage error."""
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
            raise ValueError(text)
        return datetime.date(int(text[:4]), int(text[5:7]), int(text[8:]))
    except ValueError:
        raise argparse.ArgumentTypeError('%r is not a date written YYYY-MM-DD' % text)


def build_parser():
    ap = argparse.ArgumentParser(prog='validate.py', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--content', metavar='DIR', help='a folder laid out like content/ (default: this checkout\'s)')
    ap.add_argument('--site', metavar='DIR', help='also check a built site, such as _site')
    ap.add_argument('--strict', action='store_true', help='exit 1 on a warning as well')
    ap.add_argument('--json', action='store_true', help='print every finding as a JSON list instead of lines')
    loud = ap.add_mutually_exclusive_group()
    loud.add_argument('-q', '--quiet', action='store_true', help='print errors and the summary line only')
    loud.add_argument('-v', '--verbose', action='store_true', help='also list the notes one by one')
    ap.add_argument('--today', type=_today, metavar='YYYY-MM-DD',
                    help='the day dates are judged against (default: today)')
    return ap


def content_folders(arg):
    """(trips_dir, home_json, rendered_dir) for --content DIR; without it three Nones, which checks.survey reads as
    this checkout's own folders. A content folder's renders sit beside it, as rendered/ sits beside content/ here; when
    there is no such folder checks says nothing about renders."""
    if not arg:
        return None, None, None
    base = os.path.abspath(arg)
    trips = os.path.join(base, 'trips')
    if not os.path.isdir(trips):
        raise Usage('--content %s: there is no trips/ folder in it' % arg)
    return trips, os.path.join(base, 'home.json'), os.path.join(os.path.dirname(base), 'rendered')


def site_checker(arg):
    """sitecheck.check for --site DIR, imported only when asked for (a content check needs none of it)."""
    if not os.path.isdir(arg):
        raise Usage('--site %s: no such folder (build the site first: python3 tools/build.py)' % arg)
    try:
        check = getattr(importlib.import_module('sitegen.sitecheck'), 'check', None)
    except ImportError as ex:
        raise Usage('--site: the built-site checks are unavailable (tools/sitegen/sitecheck.py: %s)' % ex)
    if check is None:
        raise Usage('--site: the built-site checks are unavailable (tools/sitegen/sitecheck.py has no check())')
    return check


def main(argv=None):
    try:
        a = build_parser().parse_args(argv)
    except SystemExit as ex:           # argparse has printed its message (or the help); hand its status back
        return ex.code if isinstance(ex.code, int) else 2
    try:
        trips_dir, home_json, rendered_dir = content_folders(a.content)
        check_site = site_checker(a.site) if a.site else None
    except Usage as ex:
        print('ERROR %s' % ex, file=sys.stderr)
        return 2
    findings, counts = checks.survey(trips_dir, home_json, rendered_dir, a.today)
    problems = []
    if check_site:
        problems = list(check_site(os.path.abspath(a.site), content_trips_dir=trips_dir or content.TRIPS_DIR))
    failed = bool(checks.errors(findings) or problems or (a.strict and checks.warnings(findings)))
    if a.json:
        # a built-site problem is a line about a page, not about a content file: it has no file of its own here
        site = [{'level': 'error', 'file': '', 'text': p} for p in problems]
        print(json.dumps(findings + site, ensure_ascii=False, indent=1))
        return 1 if failed else 0
    shown = ('error',) if a.quiet else ('error', 'warning', 'note') if a.verbose else ('error', 'warning')
    for f in findings:
        if f['level'] in shown:
            print(checks.line(f))
    for p in problems:
        print('ERROR %s' % p)
    print(checks.summary(findings, counts))
    if check_site:
        print('site: %d problems' % len(problems))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
