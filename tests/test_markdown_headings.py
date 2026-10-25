"""A write-up's own headings (Phase 8, after the review that added the site check's HEADING rule): markdown.to_html counts
a heading's level from the write-up's own top level, so a write-up whose first heading is '##' starts one level under
its section as one written '#' does; and the content check stops a build whose write-up skips a level inside itself,
naming the file, before the built page could. Text is synthetic."""
import os
import tempfile
import unittest

import helpers

import checks
import markdown


class HeadingLevelTests(unittest.TestCase):

    def test_the_first_level_is_one_under_the_section_whatever_its_hashes(self):
        for text in ('# Gear\n\nSynthetic words.\n\n## Food\n', '## Gear\n\nSynthetic words.\n\n### Food\n'):
            with self.subTest(first=text[:2]):
                self.assertEqual(markdown.to_html(text), '<h3>Gear</h3>\n<p>Synthetic words.</p>\n<h4>Food</h4>')

    def test_heading_shift_is_kept(self):
        self.assertEqual(markdown.to_html('## A\n', heading_shift=3), '<h4>A</h4>')     # a multi-day day
        self.assertEqual(markdown.to_html('### A\n#### B\n', heading_shift=4), '<h5>A</h5>\n<h6>B</h6>')   # a journal day

    def test_a_write_up_led_by_one_hash_renders_as_before(self):
        # today's rule for '#'-led text: '#' + 2
        self.assertEqual(markdown.to_html('# A\n## B\n### C\n'), '<h3>A</h3>\n<h4>B</h4>\n<h5>C</h5>')

    def test_levels_and_jumps(self):
        self.assertEqual(markdown.heading_levels('## A\ntext\n#### B\n> # quoted\n'), [2, 4])
        self.assertEqual(markdown.heading_jumps('## A\n#### B\n## C\n### D\n'), [(4, 2)])
        self.assertEqual(markdown.heading_jumps('# A\n## B\n# C\n### D'), [(3, 1)])
        self.assertEqual(markdown.heading_jumps('No headings at all.'), [])


class HeadingCheckTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.trips = os.path.join(tmp.name, 'trips')
        os.makedirs(self.trips)

    def lines(self):
        found = checks.run(self.trips, os.path.join(self.trips, '..', 'home.json'), os.path.join(self.trips, '..', 'rendered'))
        return [checks.line(f) for f in found if f['level'] == 'error']

    def test_a_skipped_level_in_a_write_up_stops_the_build_naming_the_file(self):
        helpers.make_trip(self.trips, 'synh-walk', title='Synthetic Walk', date='2026-01-02',
                          body='## Approach\n\nSynthetic words.\n\n#### Gear\n\nMore synthetic words.')
        self.assertEqual(self.lines(), ['ERROR content/trips/synh-walk/index.md: a heading of the write-up skips a level '
                                        '(#### after ##): go one level at a time, ### after ##'])

    def test_a_day_file_is_named_and_a_sound_write_up_passes(self):
        helpers.make_trip(self.trips, 'synh-tour', title='Synthetic Tour', activity='ski', kind='multi-day', date='2026-02-01',
                          body='## Overview\n\n### Snow\n',
                          days=[{'title': 'Synthetic In', 'date': '2026-02-01', 'body': '# Up\n\n### Down\n', 'track': False},
                                {'title': 'Synthetic Out', 'date': '2026-02-02', 'body': '## Out\n', 'track': False}])
        self.assertEqual(self.lines(), ['ERROR content/trips/synh-tour/days/01.md: a heading of the write-up skips a level '
                                        '(### after #): go one level at a time, ## after #'])


if __name__ == '__main__':
    unittest.main()
