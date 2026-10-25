"""Phase 9: the About page's new parts and Eric's own words, on synthetic trips in a temp dir.

  ia-19 (a)   the Trips and Tick list rows (about.site_rows) in the .abo-act markup of the 404 page's Site rows
  features-01 the By year block (about.year_stats / year_rows): one row per calendar year a report starts in, newest
              first; days out are distinct dates (a multi-day trip's days on their own dates, never the trip again);
              distance and gain are the trips' own totals; a total no trip states is left out
  visual-16   content/about.md (content.load_about): without it the page is as it was; its words replace the computed
              lede verbatim; its photo is shown at 4:5 above them only with an alt; build.copy_about_assets publishes
              the photo and its 800 px copy; the content check's findings for the file (checks._about_findings)
  about_photo tools/about_photo.py writes the copies and the photo: block, with web_copies replaced by a recorder

Slugs start with 'syna-'; every title, name and sentence is made up."""
import contextlib
import importlib
import io
import os
import tempfile
import unittest
from unittest import mock

import helpers
from helpers import Doc

import checks
import content
import frontmatter
import photos as photolib
from sitegen import core

build = importlib.import_module('build')
about = importlib.import_module('sitegen.pages.about')
about_photo = importlib.import_module('about_photo')

tearDownModule = helpers.no_region_pages_left

LEDE = ('<p class="abo-lead">Trip reports by Eric Sichak: backcountry skiing, climbing, hiking, mountain biking and other '
        'trips, each with the full GPX track and map.</p>')


class AboutFixture(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.join(tmp.name, 'content')
        self.trips = os.path.join(self.root, 'trips')
        os.makedirs(self.trips)
        mk = helpers.make_trip
        mk(self.trips, 'syna-a', title='Synthetic Ridge', date='2026-03-01', track=True,
           stats={'distance_km': 10.0, 'gain_m': 500})
        mk(self.trips, 'syna-b', title='Synthetic Second Lap', date='2026-03-01', track=True)      # the same day: one day out
        mk(self.trips, 'syna-tour', title='Synthetic Tour', kind='multi-day', date='2026-04-01',
           days=[{'title': 'Synthetic In', 'date': '2026-04-01', 'stats': {'distance_km': 4.0, 'gain_m': 300}},
                 {'title': 'Synthetic Out', 'date': '2026-04-02', 'stats': {'distance_km': 6.0, 'gain_m': 400}}])
        mk(self.trips, 'syna-old', title='Synthetic Old Walk', date='2025-07-04', track=True)          # no stats at all
        mk(self.trips, 'syna-goal', title='Synthetic Goal', kind='planned', track=True)
        mk(self.trips, 'syna-draft', title='Synthetic Draft', date='2024-01-01', draft=True, track=True)
        p = mock.patch.object(content, 'TRIPS_DIR', self.trips)
        p.start()
        self.addCleanup(p.stop)

    def site(self, about_=None):
        site = build.site_of(helpers.newest_first(helpers.load_dir(self.trips)))
        site['featured'] = []
        site['about'] = about_
        core.register_site(site, {'maps': {}, 'regions': []})
        return site

    def write_about(self, text):
        with open(os.path.join(self.root, 'about.md'), 'w', encoding='utf-8') as fh:
            fh.write(text)
        return content.load_about()

    def portrait_files(self, *names):
        folder = os.path.join(self.root, 'about', 'photos')
        os.makedirs(folder, exist_ok=True)
        for n in names:
            with open(os.path.join(folder, n), 'wb') as fh:
                fh.write(b'placeholder')


# ---------------------------------------------------------------- By year

class YearTests(AboutFixture):

    def test_one_row_per_year_and_nothing_counted_twice(self):
        self.assertEqual(about.year_stats(self.site()), [(2026, 3, 3, 20.0, 1200), (2025, 1, 1, 0, 0)])

    def test_the_rows(self):
        html_ = about.year_rows(self.site(), 'about/')
        doc = Doc(html_)
        self.assertEqual(doc.find('ul')['class'], 'abo-act abo-yr')
        links = doc.find_all('a', cls='abo-act-a')
        self.assertEqual([a['href'] for a in links], ['../trips/?year=2026', '../trips/?year=2025'])
        self.assertEqual([a.find('span', cls='abo-act-n').text() for a in links], ['2026', '2025'])
        nb = core.nb
        self.assertIn('<span class="mi">%s</span><span class="mi"><span class="sr">, </span>%s</span><span class="mi"><span '
                      'class="sr">, </span>%s%s</span>' % (nb('3 REPORTS'), nb('3 DAYS OUT'), core.U(nb('3,937 FT'), nb('1,200 M')),
                                                         nb(' GAIN')), html_)
        self.assertNotRegex(html_, '<[^>]*\xa0[^>]*>')                    # no no-break space inside a tag
        self.assertEqual(links[0].find('span', cls='abo-act-d').text(), '12.4 mi20.0 km')    # core.distance, as By activity
        # a year whose trips state no distance and no gain says neither, never 0
        self.assertEqual(links[1].find('span', cls='abo-act-m').text(), '1 REPORT, 1 DAY OUT')
        self.assertIsNone(links[1].find('span', cls='abo-act-d'))
        self.assertNotIn(' 0 ', links[1].text())

    def test_the_block_sits_after_by_activity_on_the_page(self):
        html_ = about.page(self.site()).html
        at = [html_.index(x) for x in ('id="abo-act-h"', 'id="abo-yr-h"', 'id="abo-site-h"', 'class="alink abo-map"')]
        self.assertEqual(at, sorted(at))
        self.assertIn('>By year</h3>', html_)


# ---------------------------------------------------------------- Trips and Tick list

class SiteRowsTests(AboutFixture):

    def test_trips_and_tick_list_in_the_404_rows_markup(self):
        rows = Doc(about.site_rows({'active_goals': [{}], 'planned': []}, 'about/'))
        links = rows.find_all('a', cls='abo-act-a')
        self.assertEqual([(a['href'], a.find('span', cls='abo-act-n').text(), a.find('span', cls='abo-act-m').text())
                          for a in links], [('../trips/', 'Trips', 'SEARCH AND FILTER'), ('../tick-list/', 'Tick list', '1 GOAL')])
        self.assertEqual([a.find('span', cls='abo-ic')['aria-hidden'] for a in links], ['true', 'true'])
        self.assertIn('2 GOALS', about.site_rows({'active_goals': [{}, {}], 'planned': []}, 'about/'))
        self.assertIn('0 GOALS', about.site_rows({'active_goals': [], 'planned': []}, 'about/'))

    def test_the_page_counts_the_active_goals(self):
        html_ = about.page(self.site()).html
        self.assertIn('<span class="abo-act-n">Tick list</span><span class="t-mono-s abo-act-m">1 GOAL</span>', html_)

    def test_the_round_icon_is_styled_once_for_both_pages(self):
        css = build.css_bundle()
        self.assertEqual(css.count('.abo-ic, .nf-ic {'), 1)
        self.assertNotIn('\n.nf-ic {', css)


# ---------------------------------------------------------------- content/about.md

class AboutWordsTests(AboutFixture):

    def test_without_the_file_the_lede_stays_and_nothing_is_added(self):
        self.assertIsNone(content.load_about())
        html_ = about.page(self.site(content.load_about())).html
        self.assertIn(LEDE, html_)
        for needle in ('abo-words', 'abo-portrait', '<img'):
            self.assertNotIn(needle, html_)

    def test_the_words_replace_the_lede_verbatim(self):
        a = self.write_about('---\n---\n\nSynthetic words about the *site*.\n\n# Synthetic heading\n\nMore synthetic words.\n'
                             '<!-- a note to myself -->\n')
        html_ = about.page(self.site(a)).html
        self.assertNotIn('class="abo-lead"', html_)
        self.assertIn('<div class="prose abo-words"><p>Synthetic words about the <em>site</em>.</p>', html_)
        self.assertIn('<h2>Synthetic heading</h2>', html_)               # the top level of the words is the page's h2
        self.assertNotIn('a note to myself', html_)
        self.assertLess(html_.index('abo-words'), html_.index('id="abo-glance-h"'))

    def test_a_file_with_neither_words_nor_photo_changes_nothing(self):
        plain = about.page(self.site(None)).html
        self.assertEqual(about.page(self.site(self.write_about('---\n---\n\n'))).html, plain)

    def test_the_photo_at_4_5_above_the_words_with_its_alt_and_focal_point(self):
        self.portrait_files('portrait-01.webp', 'portrait-01.sm.webp')
        a = self.write_about('---\nphoto:\n  file: photos/portrait-01.webp\n  w: 1200\n  h: 1500\n  alt: Synthetic portrait alt\n'
                             'cover_focal_y: 30\n---\n\nSynthetic words.\n')
        html_ = about.page(self.site(a)).html
        fig = Doc(html_).find('figure', cls='abo-portrait')
        img = fig.find('img')
        self.assertEqual((img['src'], img['alt'], img['width'], img['height']),
                         ('../about/photos/portrait-01.webp', 'Synthetic portrait alt', '1200', '1500'))
        self.assertEqual(img['srcset'], '../about/photos/portrait-01.sm.webp 640w, ../about/photos/portrait-01.webp 1200w')
        self.assertEqual(img['style'], 'object-position:50% 30%')
        self.assertIsNone(img['loading'])                                # the page's first image: not lazy
        self.assertLess(html_.index('abo-portrait'), html_.index('abo-words'))
        css = build.css_bundle()
        self.assertIn('.abo-portrait img { display: block; width: 100%; height: auto; aspect-ratio: 4 / 5; object-fit: cover;', css)

    def test_no_photo_is_shown_without_an_alt(self):
        self.portrait_files('portrait-01.webp')
        a = self.write_about('---\nphoto:\n  file: photos/portrait-01.webp\n  w: 1200\n  h: 1500\n  alt:\n---\n')
        self.assertNotIn('<img', about.page(self.site(a)).html)

    def test_the_build_publishes_the_photo_and_its_800px_copy_beside_the_page(self):
        self.portrait_files('portrait-01.webp', 'portrait-01.sm.webp', 'portrait-01.th.webp', 'portrait-00.webp')
        a = self.write_about('---\nphoto:\n  file: photos/portrait-01.webp\n  w: 1200\n  h: 1500\n  alt: Synthetic alt\n---\n')
        out = os.path.join(self.root, '_out')
        with mock.patch.object(build, 'OUT', out), mock.patch.object(build, 'LINK', False):
            build.copy_about_assets(a)
            build.copy_about_assets(None)                                 # no file: nothing
        self.assertEqual(sorted(os.listdir(os.path.join(out, 'about', 'photos'))), ['portrait-01.sm.webp', 'portrait-01.webp'])

    def test_a_photo_path_outside_the_folder_stops_the_load(self):
        for raw in ('../trips/x.webp', '/etc/x.webp', ''):
            with self.subTest(raw=raw):
                with self.assertRaises(content.ContentError) as cm:
                    self.write_about('---\nphoto:\n  file: "%s"\n  alt: Synthetic\n---\n' % raw)
                self.assertTrue(str(cm.exception).startswith('content/about.md: photo file must be'), str(cm.exception))


class AboutCheckTests(AboutFixture):

    def findings(self, text, files=()):
        self.portrait_files(*files) if files else None
        with open(os.path.join(self.root, 'about.md'), 'w', encoding='utf-8') as fh:
            fh.write(text)
        found = checks.run(self.trips, os.path.join(self.root, 'home.json'), os.path.join(self.root, 'rendered'))
        return [(f['level'], f['text'][len('content/about.md: '):]) for f in found if f['file'] == 'content/about.md']

    def test_a_good_file_is_quiet(self):
        self.assertEqual(self.findings('---\nphoto:\n  file: photos/p.webp\n  w: 10\n  h: 12\n  alt: Synthetic alt\n---\n\nWords.\n',
                                       ('p.webp', 'p.sm.webp')), [])
        self.assertEqual(self.findings('---\n---\n\nOnly synthetic words.\n'), [])

    def test_the_alt_is_required(self):
        for alt in ('', '"  "'):
            with self.subTest(alt=alt):
                self.assertEqual(self.findings('---\nphoto:\n  file: photos/p.webp\n  w: 10\n  h: 12\n  alt: %s\n---\n' % alt,
                                               ('p.webp', 'p.sm.webp')),
                                 [('error', 'photo has no alt text: describe what it shows in an alt: line under photo (the '
                                            'page shows no photo without one, and it is what a screen reader says in its place)')])

    def test_the_other_findings(self):
        got = self.findings('---\nphoto:\n  file: photos/gone.webp\n  w: wide\n  alt: Synthetic\n  tint: warm\nbio: x\n---\n\n'
                            '# One\n\n### Three\n')
        self.assertEqual(got, [
            ('error', 'a heading of the write-up skips a level (### after #): go one level at a time, ## after #'),
            ('error', 'photo file photos/gone.webp is missing from content/about/ (python3 tools/about_photo.py writes it)'),
            ('error', "photo.h must be a positive whole number of pixels, got None"),
            ('error', "photo.w must be a positive whole number of pixels, got 'wide'"),
            ('warning', "unknown key 'bio'; nothing reads it"),
            ('warning', "unknown key 'tint' in photo; nothing reads it"),
        ])
        self.assertEqual(self.findings('---\nphoto:\n  file: photos/p.webp\n  w: 10\n  h: 12\n  alt: Synthetic\n---\n', ('p.webp',)),
                         [('warning', 'photo photos/p.webp has no 800 px copy beside it, so every visitor loads the large '
                                      'one; python3 tools/about_photo.py writes both')])
        self.assertEqual(self.findings('---\ncover_focal_x: 20\n---\n'),
                         [('warning', 'cover_focal_x / cover_focal_y say where to crop a photo, and there is no photo: line')])
        self.assertEqual(self.findings('---\ncover_focal_x: 120\n---\n'),
                         [('error', 'cover_focal_x must be between 0 and 100, got 120')])


# ---------------------------------------------------------------- tools/about_photo.py

class AboutPhotoToolTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.content = os.path.join(tmp.name, 'content')
        os.makedirs(self.content)
        self.src = os.path.join(tmp.name, 'me.jpg')
        with open(self.src, 'wb') as fh:
            fh.write(b'')
        self.copies = []
        for target, name, value in ((about_photo, 'CONTENT', self.content), (photolib, 'web_copies', self.fake_copies)):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)

    def fake_copies(self, src, dst_base, *a, **kw):
        self.copies.append(os.path.relpath(dst_base, self.content))
        os.makedirs(os.path.dirname(dst_base), exist_ok=True)       # as web_copies does
        for suffix in ('.webp', '.sm.webp', '.th.webp'):
            with open(dst_base + suffix, 'wb') as fh:
                fh.write(b'placeholder')
        return 'webp', 1200, 1500

    def run_tool(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = about_photo.main(list(argv))
        return code, out.getvalue()

    def about(self):
        with open(os.path.join(self.content, 'about.md'), encoding='utf-8') as fh:
            return fh.read()

    def test_it_writes_the_copies_and_a_new_about_md(self):
        code, out = self.run_tool(self.src)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.copies, ['about/photos/portrait-01'])
        self.assertEqual(self.about(), '---\nphoto:\n  file: photos/portrait-01.webp\n  w: 1200\n  h: 1500\n  alt: ""\n---\n\n\n')
        self.assertIn('Next: describe the photo in content/about.md', out)

    def test_a_second_photo_gets_the_next_name_and_keeps_the_words(self):
        with open(os.path.join(self.content, 'about.md'), 'w', encoding='utf-8') as fh:
            fh.write('---\ncover_focal_y: 30\n---\n\nSynthetic words.\n')
        self.run_tool(self.src)
        code, out = self.run_tool(self.src)
        self.assertEqual(code, 0)
        self.assertEqual(self.copies, ['about/photos/portrait-01', 'about/photos/portrait-02'])
        meta, body = frontmatter.split(self.about())
        self.assertEqual((meta['photo']['file'], meta['photo']['alt'], meta['cover_focal_y']), ('photos/portrait-02.webp', '', 30))
        self.assertEqual(body, 'Synthetic words.\n')
        self.assertIn("the earlier photo's files are still in content/about/: photos/portrait-01.*", out)

    def test_words_written_first_keep_their_place(self):
        # the guide's shape (an empty block) and a file of words alone both take the photo: block in front of the words
        for text in ('---\n---\n\nSynthetic words first.\n', 'Synthetic words first.\n'):
            with self.subTest(text=text):
                with open(os.path.join(self.content, 'about.md'), 'w', encoding='utf-8') as fh:
                    fh.write(text)
                code, out = self.run_tool(self.src)
                self.assertEqual(code, 0, out)
                meta, body = frontmatter.split(self.about())
                self.assertEqual(body, 'Synthetic words first.\n')
                self.assertEqual(sorted(meta['photo']), ['alt', 'file', 'h', 'w'])
        with open(os.path.join(self.content, 'about.md'), 'w', encoding='utf-8') as fh:
            fh.write('---\n# a note to myself\n---\nSynthetic words.\n')          # a comment would be lost: refused
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.run_tool(self.src)[0], 1)

    def test_dry_run_writes_nothing_and_a_non_photo_is_refused(self):
        code, out = self.run_tool(self.src, '--dry-run')
        self.assertEqual((code, self.copies, os.listdir(self.content)), (0, [], []))
        self.assertIn('dry run: nothing written', out)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            about_photo.main([os.path.join(self.content, 'nothing.txt')])


if __name__ == '__main__':
    unittest.main()
