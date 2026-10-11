"""tools/lib/frontmatter.py: which values are numbers (contract-phase4.md 10.3).

A value is a number only when it is written in the digits 0-9: `frontmatter._NUM` is compiled with re.ASCII. Full-width
digits (`１６００`), Arabic-Indic digits (`١٦٠٠`) and every other script's digits stay the text that was typed, in any
field and at any depth, because Python's int() and float() would read them as numbers and the pages would then
print a value the file does not hold. Plain ASCII numbers parse exactly as before: whole numbers as int, numbers with
a decimal point as float, a leading minus sign kept.

What the loader and the validator then make of such a value (a photo whose `w` is text has no recorded size; the
content check names it) is pinned here for the photo size the contract names, through content.load_trip, core.photo and
checks.run on a synthetic trip in a temp dir. Nothing under content/ is read.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import frontmatter  # noqa: E402

import helpers  # noqa: E402

FULL_WIDTH = '１６００'              # U+FF11 U+FF16 U+FF10 U+FF10
ARABIC_INDIC = '١٦٠٠'            # U+0661 U+0666 U+0660 U+0660
# (as typed, what int() or float() would make of it): every one must stay the text on the left
OTHER_DIGITS = [(FULL_WIDTH, 1600), (ARABIC_INDIC, 1600), ('２０２６', 2026), ('٢٠٢٦', 2026), ('۱۲', 12), ('१२', 12), ('１', 1), ('０', 0),
                ('-１２', -12), ('１２.５', 12.5), ('-٠.٥', -0.5), ('16００', 1600), ('1٢', 12), ('１600', 1600), ('12.５', 12.5),
                ('１２.5', 12.5)]


def value(text):
    """What `key: <text>` parses to."""
    return frontmatter.loads('key: ' + text)['key']


class NumberTests(unittest.TestCase):

    def test_the_fixture_values_are_what_python_would_read_as_numbers(self):
        # the reason for the rule: int() and float() take these digits
        for typed, number in OTHER_DIGITS:
            with self.subTest(typed=typed):
                self.assertFalse(typed.isascii())
                self.assertEqual(float(typed), number)

    def test_ascii_whole_numbers_are_ints(self):
        for typed, want in (('0', 0), ('7', 7), ('12', 12), ('1600', 1600), ('2026', 2026), ('007', 7), ('-12', -12), ('-0', 0),
                            ('123456789012', 123456789012)):
            with self.subTest(typed=typed):
                got = value(typed)
                self.assertEqual(got, want)
                self.assertIs(type(got), int)

    def test_ascii_numbers_with_a_point_are_floats(self):
        for typed, want in (('12.5', 12.5), ('0.5', 0.5), ('-0.5', -0.5), ('3.0', 3.0), ('12.50', 12.5), ('-1450.25', -1450.25), ('5.10', 5.1)):
            with self.subTest(typed=typed):
                got = value(typed)
                self.assertEqual(got, want)
                self.assertIs(type(got), float)

    def test_what_was_never_a_number_is_still_text(self):
        for typed in ('1e3', '1,450', '12 km', '.5', '5.', '+5', '1_000', '0x10', '1.2.3', '--5', '6:10', '2026-07-05', 'nan', 'inf',
                      '-', '1/2', '12%'):
            with self.subTest(typed=typed):
                got = value(typed)
                self.assertEqual(got, typed)
                self.assertIs(type(got), str)

    def test_digits_of_other_scripts_stay_the_text_that_was_typed(self):
        for typed, _number in OTHER_DIGITS:
            with self.subTest(typed=typed):
                got = value(typed)
                self.assertIs(type(got), str)
                self.assertEqual(got, typed)
                self.assertEqual([ord(c) for c in got], [ord(c) for c in typed])       # not folded to ASCII either

    def test_in_any_field_and_at_any_depth(self):
        text = '\n'.join(['title: Synthetic',
                          'cover_focal_x: ５０',
                          'stats:',
                          '  distance_km: １２.５',
                          '  gain_m: ٨٠٠',
                          '  high_m: 2900',
                          'photos:',
                          '  - file: photos/01.webp',
                          '    w: １６００',
                          '    h: 1200',
                          '  - file: photos/02.webp',
                          '    w: 1200',
                          '    h: ١٦٠٠',
                          'target_months: [７, 8, ٩]',
                          'years:',
                          '  - ２０２６',
                          '  - 2027'])
        meta = frontmatter.loads(text)
        self.assertEqual(meta, {'title': 'Synthetic', 'cover_focal_x': '５０',
                                'stats': {'distance_km': '１２.５', 'gain_m': '٨٠٠', 'high_m': 2900},
                                'photos': [{'file': 'photos/01.webp', 'w': '１６００', 'h': 1200},
                                           {'file': 'photos/02.webp', 'w': 1200, 'h': '١٦٠٠'}],
                                'target_months': ['７', 8, '٩'], 'years': ['２０２６', 2027]})
        self.assertIs(type(meta['photos'][0]['w']), str)
        self.assertIs(type(meta['photos'][0]['h']), int)
        self.assertEqual([type(v) for v in meta['target_months']], [str, int, str])
        # through split(), as a trip file is read
        meta, body = frontmatter.split('---\n%s\n---\nSynthetic body.\n' % text)
        self.assertEqual((meta['photos'][1]['h'], meta['stats']['high_m'], body), ('١٦٠٠', 2900, 'Synthetic body.\n'))

    def test_a_quoted_value_is_text_whatever_its_digits(self):
        for typed, want in (('"1600"', '1600'), ("'1600'", '1600'), ('"１６００"', '１６００'), ("'١٦٠٠'", '١٦٠٠')):
            with self.subTest(typed=typed):
                got = value(typed)
                self.assertEqual(got, want)
                self.assertIs(type(got), str)

    def test_text_and_numbers_survive_a_round_trip(self):
        meta = {'w': '１６００', 'h': 1200, 'ratio': 1.5, 'low': -86, 'text': '1600', 'list': ['١٦٠٠', 7]}
        back = frontmatter.loads(frontmatter.dumps(meta))
        self.assertEqual(back, meta)
        self.assertEqual({k: type(v) for k, v in back.items()}, {k: type(v) for k, v in meta.items()})


class PhotoSizeTests(unittest.TestCase):
    """The case the contract names: `w: １６００` on a photo is not a number. The content check then refuses it by name, as it
    refuses `w: wide` (the loader itself was never asked to cope with a size that is not a number: the build runs the
    check first)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def write(self, slug, w, h):
        """A synthetic trip whose one photo states this size, typed as given; -> the path of its index.md."""
        folder = helpers.make_trip(self.tmp, slug, title='Synthetic Photo Sizes', date='2026-06-01',
                                   photos=[{'file': 'photos/01.webp', 'alt': 'Synthetic photo', 'sm': True}])
        path = os.path.join(folder, 'index.md')
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
        self.assertEqual(text.count('  - file: photos/01.webp\n'), 1)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text.replace('  - file: photos/01.webp\n', '  - file: photos/01.webp\n    w: %s\n    h: %s\n' % (w, h)))
        return path

    def photo(self, path):
        with open(path, encoding='utf-8') as fh:
            return frontmatter.split(fh.read())[0]['photos'][0]

    def errors(self):
        import checks
        home = os.path.join(self.tmp, 'home.json')
        with open(home, 'w', encoding='utf-8') as fh:
            fh.write('{"featured_slugs": []}')
        with mock.patch.object(content, 'TRIPS_DIR', self.tmp):
            found = checks.run(trips_dir=self.tmp, home_json=home, rendered_dir=os.path.join(self.tmp, '_no_renders'))
        return [checks.line(f) for f in checks.errors(found)]

    def test_a_photo_size_in_ascii_digits_is_a_number_and_loads(self):
        p = self.photo(self.write('synf-plain', '1600', '1200'))
        self.assertEqual((p['w'], p['h'], type(p['w']), type(p['h'])), (1600, 1200, int, int))
        loaded = helpers.load(self.tmp, 'synf-plain')['photos'][0]
        self.assertEqual((loaded['w'], loaded['h'], loaded['sm']), (1600, 1200, 'photos/01.sm.webp'))
        self.assertEqual(self.errors(), [])

    def test_a_photo_size_in_other_digits_is_text(self):
        for slug, w, h in (('synf-wide-w', FULL_WIDTH, '1200'), ('synf-arabic-h', '1600', '١٢٠٠'), ('synf-both', FULL_WIDTH, '１２００')):
            with self.subTest(w=w, h=h):
                p = self.photo(self.write(slug, w, h))
                self.assertEqual((p['w'], p['h']), (w if not w.isascii() else int(w), h if not h.isascii() else int(h)))
                self.assertIs(type(p['w']), int if w.isascii() else str)
                self.assertIs(type(p['h']), int if h.isascii() else str)

    def test_the_content_check_names_the_field(self):
        # tools/validate.py and the build's own check refuse the value by name
        size = "ERROR content/trips/%s/index.md: photos[0].%s (photos/01.webp) must be a positive whole number of pixels, got %r"
        self.write('synf-check-w', FULL_WIDTH, '1200')
        self.write('synf-check-h', '1600', ARABIC_INDIC)
        self.write('synf-check-ok', '1600', '1200')
        self.assertEqual(self.errors(), [size % ('synf-check-h', 'h', ARABIC_INDIC), size % ('synf-check-w', 'w', FULL_WIDTH)])


class ValidatorDigitTests(unittest.TestCase):
    """tools/lib/checks.py reads a date, a clock time and a duration with the same rule: only 0-9 are digits. A date typed
    in full-width digits used to pass the check, load as no date at all, and leave only a "no date" warning."""

    def setUp(self):
        import importlib
        self.checks = importlib.import_module('checks')

    def test_dates(self):
        import datetime
        self.assertEqual(self.checks._as_date('2026-07-05'), datetime.date(2026, 7, 5))
        for text in ('２０２６-０７-０５', '2026-０7-05', '٢٠٢٦-٠٧-٠٥'):
            self.assertIsNone(self.checks._as_date(text), text)

    def test_clock_times(self):
        self.assertTrue(self.checks._is_clock('06:30'))
        for text in ('０６:３０', '06:３0', '٠٦:٣٠'):
            self.assertFalse(self.checks._is_clock(text), text)

    def test_durations(self):
        for text in ('6:10', '0:45:30', '12'):
            self.assertTrue(self.checks._is_duration(text), text)
        for text in ('６:１０', '6:１0', '٦:١٠'):
            self.assertFalse(self.checks._is_duration(text), text)

    def test_a_trip_dated_in_full_width_digits_is_an_error_that_names_the_field(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = os.path.realpath(tmp.name)
        trips = os.path.join(root, 'content', 'trips')
        folder = helpers.make_trip(trips, 'syn-digits', title='Synthetic Digits', date='2026-07-05', start_time='06:30')
        path = os.path.join(folder, 'index.md')
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
        self.assertIn('2026-07-05', text)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text.replace('2026-07-05', '２０２６-０７-０５').replace('06:30', '０６:３０'))
        home = os.path.join(root, 'content', 'home.json')
        with open(home, 'w', encoding='utf-8') as fh:
            fh.write('{"featured_slugs": []}')
        import datetime
        found = self.checks.run(trips, home, os.path.join(root, 'rendered'), datetime.date(2026, 10, 10))
        errors = [f['text'] for f in self.checks.errors(found)]
        self.assertEqual(len(errors), 2, errors)
        self.assertTrue(any('date must be a date written YYYY-MM-DD' in e for e in errors), errors)
        self.assertTrue(any('start_time must be a time written HH:MM' in e for e in errors), errors)


if __name__ == '__main__':
    unittest.main()
