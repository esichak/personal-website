"""Review gate (fix E): no test or harness file quotes a real write-up.

Every fixture sentence in tests/ is meant to be synthetic. One was not: the snippet check of tests/trips_js_harness.js
held two sentences of a report (replaced at the gate). The repository is public and the write-ups are Eric's, so a quote
in a test is published a second time, out of its place, and stays behind when the report is edited or taken down.

The rule, as a test: for the body of every content/trips/*/index.md and content/trips/*/days/*.md (what stands below
the front matter), no run of eight consecutive words of it appears in any file under tests/. Words are compared in
lower case with everything that is not a letter or a digit read as a space, so quotes, line breaks, a string split
over two source lines, Markdown marks and punctuation hide nothing.

The test of the real content is skipped where content/ is absent (a scratch copy of tools/ and tests/); the CI
checkout has it, so it runs there. The scan itself is tested on synthetic folders in a temp dir, always. A failure
names the test file, its line and the content file, never the words.
"""
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
TESTS = os.path.join(ROOT, 'tests')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import frontmatter  # noqa: E402

import helpers  # noqa: E402

RUN = 8                                    # this many consecutive words of a write-up are a quote
_NOT_A_WORD = re.compile(r'[\W_]+')


def words(text):
    """The words of a text as they are compared: lower case, letters and digits only."""
    return _NOT_A_WORD.sub(' ', text.lower()).split()


def body_of(text):
    """What stands below the front matter of a content file (the whole text when it has none, or none that closes)."""
    try:
        return frontmatter.split(text)[1]
    except ValueError:
        return text


def write_up_files(trips_dir):
    """Every index.md and days/*.md of the trip folders, sorted: [(path relative to the folder, absolute path)]."""
    out = []
    for slug in sorted(os.listdir(trips_dir)):
        folder = os.path.join(trips_dir, slug)
        if os.path.isfile(os.path.join(folder, 'index.md')):
            out.append((slug + '/index.md', os.path.join(folder, 'index.md')))
        days = os.path.join(folder, 'days')
        if os.path.isdir(days):
            out += [('%s/days/%s' % (slug, name), os.path.join(days, name)) for name in sorted(os.listdir(days)) if name.endswith('.md')]
    return out


def runs_of(trips_dir, n=RUN):
    """({run of n words: the content file it is from}, the files read, the words read) for every write-up body."""
    runs, files, count = {}, 0, 0
    for rel, path in write_up_files(trips_dir):
        with open(path, encoding='utf-8') as fh:
            w = words(body_of(fh.read()))
        files += 1
        count += len(w)
        for i in range(len(w) - n + 1):
            runs.setdefault(' '.join(w[i:i + n]), rel)
    return runs, files, count


def quotes_in(folder, runs, n=RUN):
    """Where files under `folder` hold a run of write-up words: [(file relative to the folder, line of the first run, the
    content file it is from, how many runs)], sorted. Compiled files and files that are not UTF-8 text are passed over."""
    found = []
    for dirpath, dirs, names in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d != '__pycache__')
        for name in sorted(names):
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding='utf-8') as fh:
                    lines = fh.read().split('\n')
            except (UnicodeDecodeError, OSError):
                continue
            w, at = [], []
            for number, line in enumerate(lines, 1):
                for word in words(line):
                    w.append(word)
                    at.append(number)
            hits = {}
            for i in range(len(w) - n + 1):
                source = runs.get(' '.join(w[i:i + n]))
                if source is not None:
                    first, k = hits.get(source, (at[i], 0))
                    hits[source] = (first, k + 1)
            rel = os.path.relpath(path, folder).replace(os.sep, '/')
            found += [(rel, first, source, k) for source, (first, k) in sorted(hits.items())]
    return found


class NoWriteUpIsQuotedTests(unittest.TestCase):
    """The rule on this checkout: tests/ against content/trips/."""

    def setUp(self):
        if not os.path.isdir(content.TRIPS_DIR):
            self.skipTest('content/ is not in this copy of the repository (the CI checkout has it)')

    def test_no_file_under_tests_holds_eight_consecutive_words_of_a_write_up(self):
        runs, files, count = runs_of(content.TRIPS_DIR)
        # the scan had something to compare with: the reports are there and some of them are written
        self.assertGreater(files, 0, 'no content/trips/*/index.md was read')
        self.assertGreater(len(runs), 0, 'no write-up of %d words or more was read' % RUN)
        self.assertGreater(count, len(runs) // 2)
        found = quotes_in(TESTS, runs)
        self.assertEqual(['tests/%s, line %d: %d run%s of %d consecutive words of content/trips/%s'
                          % (rel, line, k, '' if k == 1 else 's', RUN, source) for rel, line, source, k in found], [],
                         'a test or harness file quotes a real write-up: replace the fixture text with synthetic words '
                         '(the write-up itself stays as it is)')

    def test_the_scan_covers_this_folder_and_every_kind_of_file_in_it(self):
        # the harnesses and the JSON table are read as well as the Python files; this file is one of them
        seen = set()
        for dirpath, dirs, names in os.walk(TESTS):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            seen.update(os.path.splitext(name)[1] for name in names)
        self.assertLessEqual({'.py', '.js', '.json'}, seen)
        marker = 'zq%dxv marker words that only this one line of this file holds' % RUN
        runs = dict((' '.join(words(marker)[i:i + RUN]), 'marker') for i in range(len(words(marker)) - RUN + 1))
        self.assertEqual([(rel, source) for rel, _line, source, _k in quotes_in(TESTS, runs)], [('test_fixture_text.py', 'marker')])


class ScanTests(unittest.TestCase):
    """The scan itself, on a synthetic content folder and a synthetic tests folder in a temp dir."""

    BODY = ('Synthetic opening line of a synthetic report, written for this test alone.\n\n'
            'We left the synthetic trailhead before dawn; the “creek” was low, and nobody minded -- not even the dog!\n')
    DAY = 'A synthetic second day with eleven plain words in its one line.\n'

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.trips = os.path.join(tmp.name, 'content', 'trips')
        self.tests = os.path.join(tmp.name, 'tests')
        os.makedirs(self.tests)
        helpers.make_trip(self.trips, 'synq-report', title='Synthetic title of nine words that is front matter only', body=self.BODY,
                          card_summary='A synthetic card summary of nine words, front matter too')
        helpers.make_trip(self.trips, 'synq-journal', title='Synthetic Journal', kind='series', date='2024-04-22',
                          days=[{'title': 'Synthetic day title'}, {'title': 'Second', 'body': self.DAY}])
        os.makedirs(os.path.join(self.trips, 'not-a-trip'))                # a folder without an index.md is no report
        self.runs, self.files, self.count = runs_of(self.trips)

    def put(self, name, text):
        path = os.path.join(self.tests, *name.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)

    def found(self):
        return quotes_in(self.tests, self.runs)

    def test_the_bodies_are_read_and_the_front_matter_is_not(self):
        self.assertEqual([rel for rel, _path in write_up_files(self.trips)],
                         ['synq-journal/index.md', 'synq-journal/days/01.md', 'synq-journal/days/02.md', 'synq-report/index.md'])
        self.assertEqual(self.files, 4)
        self.assertEqual(self.count, len(words(self.BODY)) + len(words(self.DAY)))
        self.assertEqual(len(self.runs), len(words(self.BODY)) - RUN + 1 + len(words(self.DAY)) - RUN + 1)
        self.assertEqual(sorted(set(self.runs.values())), ['synq-journal/days/02.md', 'synq-report/index.md'])
        # a title or a card summary is not a write-up: quoting one is not reported
        self.put('test_title.py', "TITLE = 'Synthetic title of nine words that is front matter only'\n"
                                  "CARD = 'A synthetic card summary of nine words, front matter too'\n")
        self.assertEqual(self.found(), [])

    def test_eight_words_are_a_quote_and_seven_are_not(self):
        w = self.BODY.split()
        self.put('test_seven.py', "TEXT = '%s'\n" % ' '.join(w[:RUN - 1]))
        self.assertEqual(self.found(), [])
        self.put('test_eight.py', "# a comment\nTEXT = '%s'\n" % ' '.join(w[:RUN]))
        self.assertEqual(self.found(), [('test_eight.py', 2, 'synq-report/index.md', 1)])
        self.put('test_ten.py', "\n\n\nTEXT = '%s'\n" % ' '.join(w[3:3 + RUN + 2]))
        self.assertEqual(self.found(), [('test_eight.py', 2, 'synq-report/index.md', 1), ('test_ten.py', 4, 'synq-report/index.md', 3)])

    def test_a_day_file_is_a_write_up_too(self):
        self.put('harness.js', "const raw = '%s';\n" % self.DAY.strip())
        self.assertEqual(self.found(), [('harness.js', 1, 'synq-journal/days/02.md', len(words(self.DAY)) - RUN + 1)])

    def test_case_punctuation_quotes_and_line_breaks_hide_nothing(self):
        # the second paragraph in capitals, without its punctuation, split over two string literals and two lines
        self.put('test_split.py', "TEXT = ('WE LEFT THE SYNTHETIC TRAILHEAD BEFORE DAWN THE '\n"
                                  "        'creek was low and nobody minded')\n")
        self.assertEqual([(rel, line, source) for rel, line, source, _k in self.found()], [('test_split.py', 1, 'synq-report/index.md')])
        # the same eight words with one of them changed are not a quote
        self.put('test_split.py', "TEXT = 'we left the synthetic trailhead before noon the creek was low and nobody minded'\n")
        self.assertEqual(self.found(), [])

    def test_every_text_file_is_read_and_others_are_passed_over(self):
        quote = ' '.join(self.BODY.split()[:RUN + 1])
        self.put('cases.json', '["%s"]\n' % quote)
        self.put('deeper/notes.txt', quote + '\n')
        self.put('__pycache__/test_x.cpython-39.pyc', quote + '\n')
        with open(os.path.join(self.tests, 'picture.bin'), 'wb') as fh:
            fh.write(b'\xff\xfe\x00' + quote.encode('utf-8'))
        self.assertEqual([rel for rel, _line, _source, _k in self.found()], ['cases.json', 'deeper/notes.txt'])

    def test_words_are_letters_and_digits_in_lower_case(self):
        self.assertEqual(words('Lover’s Leap: “Day 5.2” -- 3,167 MI_recorded\n\tÉtoile'), ['lover', 's', 'leap', 'day', '5', '2', '3', '167', 'mi', 'recorded', 'étoile'])
        self.assertEqual(words(''), [])
        self.assertEqual(body_of('---\ntitle: T\n---\n\nThe body.\n'), 'The body.\n')
        self.assertEqual(body_of('No front matter.\n'), 'No front matter.\n')
        self.assertEqual(body_of('---\ntitle: never closed\n'), '---\ntitle: never closed\n')


if __name__ == '__main__':
    unittest.main()
