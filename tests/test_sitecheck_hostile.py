"""tools/sitegen/sitecheck.py on a folder the build did not write (`tools/validate.py --site DIR` accepts any folder):
malformed and hostile files must come back as problem lines, promptly, never as an exception or a stalled check.
Also the two scanners that replaced one-pattern matching (the head, the structured-data blocks) and the order in which
a trip's days are read. The sound build these tests damage is test_sitecheck.tiny().

contract-phase4.md 10.3 adds: names are compared in one Unicode form (a file held under the decomposed spelling of
'é', as macOS can hold it, is the file a page names with the composed one, and the reverse), and a multi-day trip's
combined "Download all GPX" file is reported when it holds no track at all or is not well-formed XML."""
import os
import time
import unicodedata
import unittest
from html.parser import HTMLParser
from unittest import mock

import helpers
import test_sitecheck as base
from test_sitecheck import Fixture, tiny, swap


class DeclarationTests(Fixture):
    """sitemap.xml and feed.xml are parsed as XML. Nothing the build writes carries a DOCTYPE, and an entity declaration
    can expand a file of a few hundred bytes into gigabytes on an older expat."""

    BOMB = ('<?xml version="1.0"?>\n<!DOCTYPE b [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
            '<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">]>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>&c;</loc></url></urlset>\n')

    def test_a_sitemap_with_a_doctype_is_refused_unparsed(self):
        files = tiny()
        files['sitemap.xml'] = self.BOMB
        self.assertEqual(self.sc.sitemap(self.built(files)),
                         ['SITEMAP sitemap.xml: not well-formed XML (DOCTYPE and entity declarations are not accepted)'])

    def test_a_feed_with_a_doctype_is_refused_unparsed(self):
        files = tiny()
        files['feed.xml'] = self.BOMB.replace('urlset', 'rss')
        self.assertEqual(self.sc.feed(self.built(files)),
                         ['FEED feed.xml: not well-formed XML (DOCTYPE and entity declarations are not accepted)'])

    def test_comments_and_cdata_are_not_declarations(self):
        files = tiny()
        self.assertIn('<urlset', files['sitemap.xml'])
        files['sitemap.xml'] = files['sitemap.xml'].replace('<urlset', '<!-- a comment --><urlset', 1)
        files['feed.xml'] = files['feed.xml'].replace('</channel>', '<description><![CDATA[a <b> c]]></description></channel>', 1)
        out = self.built(files)
        self.assertEqual(self.sc.sitemap(out) + self.sc.feed(out), [])

    def test_the_whole_check_returns_lines_for_it(self):
        files = tiny()
        files['sitemap.xml'] = self.BOMB
        self.assertEqual(self.check(files), ['SITEMAP sitemap.xml: not well-formed XML (DOCTYPE and entity declarations are not accepted)'])


class MalformedFileTests(Fixture):
    """Each of these raised (ValueError, LookupError, RecursionError, NotImplementedError / AssertionError) before."""

    def test_an_encoding_the_parser_does_not_support_is_a_line(self):
        for encoding in ('shift_jis', 'x-nope'):
            with self.subTest(encoding=encoding):
                files = tiny()
                files['sitemap.xml'] = files['sitemap.xml'].replace('<?xml version="1.0" encoding="UTF-8"?>', '<?xml version="1.0" encoding="%s"?>' % encoding)
                self.assertIn('encoding="%s"' % encoding, files['sitemap.xml'])
                lines = self.sc.sitemap(self.built(files))
                self.assertEqual(len(lines), 1)
                self.assertTrue(lines[0].startswith('SITEMAP sitemap.xml: not well-formed XML ('), lines[0])

    def test_a_search_index_nested_too_deeply_is_a_line(self):
        for name in (self.sc.SEARCH_INDEX, self.sc.JOURNAL_INDEX):
            with self.subTest(name=name):
                files = tiny()
                files[name] = '[' * 100000
                self.assertEqual(self.sc.indexes(self.built(files)), ['INDEX %s: not valid JSON (nested too deeply)' % name])

    def test_structured_data_nested_too_deeply_is_a_line(self):
        files = tiny()
        page = 'trips/alpha/index.html'
        block = self.sc.structured_blocks(files[page])
        self.assertEqual(len(block), 1)
        swap(files, page, block[0], '[' * 100000)
        self.assertEqual(self.sc.metadata(self.built(files), page), ['META %s: application/ld+json is not valid JSON (nested too deeply)' % page])

    # A declaration html.parser used to give up on: Python through 3.12.11 raises on it (AssertionError; 3.9 raises
    # NotImplementedError), later releases read it as a comment and go on (3.12.15, which the CI runner had on
    # 2026-10-12, when the two tests below failed there for expecting the older behaviour of every Python).
    GIVEN_UP_ON = '<![foo]>'
    UNREADABLE = 'META about/index.html: the <head> could not be read as HTML'

    def gives_up(self, error):
        """The head parser as a Python whose html.parser raises `error` on GIVEN_UP_ON, whatever this Python does."""
        marker, feed = self.GIVEN_UP_ON, HTMLParser.feed

        def raising(parser, data):
            if marker in data:
                raise error('unknown status keyword in marked section')
            return feed(parser, data)
        return mock.patch.object(self.sc._Head, 'feed', raising)

    def test_a_head_the_html_parser_gives_up_on_is_a_line(self):
        files = tiny()
        base.head_add(files, 'about/index.html', self.GIVEN_UP_ON)
        for error in (AssertionError, NotImplementedError):
            with self.subTest(error=error.__name__), self.gives_up(error):
                out = self.built(files)
                self.assertEqual(self.sc.metadata(out, 'about/index.html'), [self.UNREADABLE])
                self.assertEqual(self.sc.metadata(out, 'trips/alpha/index.html'), [])     # only the head that holds it

    def test_the_same_head_is_a_line_or_is_read_by_this_python(self):
        # the real parser, as it comes: it gives up (older releases) or reads the declaration as a comment (newer
        # ones). Either way nothing is raised, and a head that was read is checked like any other
        files = tiny()
        base.head_add(files, 'about/index.html', self.GIVEN_UP_ON)
        out = self.built(files)
        head = out.head('about/index.html')
        self.assertTrue(head.found)
        self.assertEqual(self.sc.metadata(out, 'about/index.html'), [self.UNREADABLE] if head.unreadable else [])
        if not head.unreadable:
            self.assertEqual(head.titles, 1)

    def test_none_of_them_raises_from_check(self):
        files = tiny()
        files['sitemap.xml'] = files['sitemap.xml'].replace('encoding="UTF-8"', 'encoding="x-nope"')
        files[self.sc.SEARCH_INDEX] = '[' * 100000
        base.head_add(files, 'about/index.html', self.GIVEN_UP_ON)
        others = ['SITEMAP sitemap.xml', 'INDEX %s' % self.sc.SEARCH_INDEX]
        with self.gives_up(AssertionError):
            lines = self.check(files)
        self.assertEqual([ln.split(':')[0] for ln in lines], ['META about/index.html'] + others)
        # with this Python's own parser: the same lines, with or without the one for the head
        lines = self.check(files)
        self.assertIn([ln.split(':')[0] for ln in lines], (['META about/index.html'] + others, others))


class ScannerTests(Fixture):
    """The head and the structured-data blocks are found by position. A page of unclosed tags used to take minutes."""

    def test_the_head_is_what_stands_between_the_tags(self):
        head = self.sc._head_text
        self.assertEqual(head('<html><head><title>x</title></head><body></body></html>'), '<title>x</title>')
        self.assertEqual(head('<HEAD lang="en">\n<title>x</title>\n</HEAD >rest'), '\n<title>x</title>\n')
        self.assertEqual(head('<header>not it</header><head>a</head>'), 'a')
        self.assertEqual(head('<head>a</head><head>b</head>'), 'a')
        for text in ('', '<body></body>', '<head><title>x</title>', '<head lang="en"', '<header>only</header>'):
            self.assertIsNone(head(text), text)

    def test_structured_blocks_are_found_however_the_tag_is_written(self):
        blocks = self.sc.structured_blocks
        self.assertEqual(blocks('<script type="application/ld+json">{"a":1}</script>'), ['{"a":1}'])
        self.assertEqual(blocks("<SCRIPT TYPE='application/ld+json' id=x>\n{}\n</SCRIPT >"), ['\n{}\n'])
        self.assertEqual(blocks('<script type=application/ld+json>{}</script>'), ['{}'])
        self.assertEqual(blocks('<script type="application/ld+json">1</script><p></p><script type="application/ld+json">2</script>'), ['1', '2'])
        self.assertEqual(blocks('<script>var a = 1;</script><script src="x.js"></script><script type="text/plain">{}</script>'), [])
        self.assertEqual(blocks('<script type="application/ld+json">{"a": "</p>"}</script>'), ['{"a": "</p>"}'])
        self.assertEqual(blocks('no script at all'), [])
        # the search goes on after a block's closing tag, so an opening tag quoted inside the block is not a second one
        quoted = '{"a": "<script type=application/ld+json>"}'
        self.assertEqual(blocks('<script type="application/ld+json">%s</script><p>x</p></script>' % quoted), [quoted])
        # a tag or a block that never closes holds no block, and ends the search
        self.assertEqual(blocks('<script type="application/ld+json">{}'), [])
        self.assertEqual(blocks('<script type="application/ld+json"'), [])
        self.assertEqual(blocks('<script type="application/ld+json">1</script><script type="application/ld+json">2'), ['1'])

    def test_the_real_shape_of_a_page_is_read_as_before(self):
        files = tiny()
        out = self.built(files)
        self.assertEqual(len(self.sc.structured_blocks(files['trips/alpha/index.html'])), 1)
        self.assertEqual(self.sc.structured_blocks(files['about/index.html']), [])
        self.assertTrue(out.head('trips/alpha/index.html').found)
        self.assertFalse(out.head('trips/alpha/index.html').unreadable)
        self.assertEqual(out.head('trips/alpha/index.html').titles, 1)

    def test_unclosed_tags_do_not_stall_the_check(self):
        # 300 kB of each took 16 to 43 seconds with one lazy pattern from tag to tag; by position it is milliseconds.
        # The bound is loose on purpose: it separates linear from quadratic, not a fast machine from a slow one.
        cases = (('<head>' * 50000, 'no <head> element'),
                 ('<head>' + '<script type="application/ld+json">' * 9000 + '</head>', None),
                 ('<head></head>' + '<script ' * 40000, None))
        for text, want in cases:
            with self.subTest(text=text[:40]):
                files = tiny()
                files['about/index.html'] = '<!doctype html><html>%s<body><main id="main"></main></body></html>' % text
                out = self.built(files)
                started = time.time()
                lines = self.sc.metadata(out, 'about/index.html')
                self.assertLess(time.time() - started, 5.0)
                if want:
                    self.assertEqual(lines, ['META about/index.html: ' + want])


DAY = ('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1">\n'
       '<trk><name>%s</name><trkseg><trkpt lat="10.0%d" lon="10.0"><ele>1</ele></trkpt>'
       '<trkpt lat="10.0%d" lon="10.01"><ele>2</ele></trkpt></trkseg></trk>\n</gpx>\n')


class DayOrderTests(Fixture):
    """content.load_trip reads the days in the order of their file names ('02-b.md' before '02.md': a dash sorts before
    a dot), and the build writes the combined file in that order. The check must read them the same way."""

    def setUp(self):
        Fixture.setUp(self)
        helpers.make_trip(self.trips, 'tour', title='Tour', kind='multi-day',
                          days=[{'id': '01'}, {'id': '02'}, {'id': '02-b'}])
        self.gpx = {'01': DAY % ('Day 1', 1, 2), '02': DAY % ('Day 2', 3, 4), '02-b': DAY % ('Day 2 b', 5, 6)}
        for day, text in self.gpx.items():
            base.write_text(os.path.join(self.trips, 'tour', 'days', day + '.gpx'), text)

    def files(self, order):
        files = {'trips/tour/gpx/tour-day-%s.gpx' % d: self.gpx[d] for d in self.gpx}
        files['trips/tour/tour.gpx'] = base.combined('Tour', *[self.gpx[d] for d in order])
        return files

    def test_the_loader_reads_02_b_before_02(self):
        import content
        self.assertEqual([d['id'] for d in content.load_trip(os.path.join(self.trips, 'tour'))['days']], ['01', '02-b', '02'])

    def test_the_combined_file_in_the_loaders_order_is_sound(self):
        self.put(self.files(['01', '02-b', '02']))
        self.assertEqual(self.sc.gpx(self.sc.read(self.out), self.trips), [])

    def test_any_other_order_is_still_reported(self):
        self.put(self.files(['01', '02', '02-b']))
        self.assertEqual(self.sc.gpx(self.sc.read(self.out), self.trips),
                         ['GPX trips/tour/tour.gpx: the track of content/trips/tour/days/02.gpx is not in the file unchanged and in day order'])


# ---------------------------------------------------------------- names in one Unicode form (contract 10.3)

NFC = unicodedata.normalize('NFC', 'caf\u00e9')       # 'café' with one character for the é: what an author types, and what
NFD = unicodedata.normalize('NFD', 'caf\u00e9')       # git hands CI; and with two (e + combining acute), as macOS can hold it


class UnicodeNameTests(Fixture):
    """Output.find() and Output.resolve() compare names in NFC, so a file or a folder held under one spelling is found
    under the other. Each case is checked on a site held in memory (the names exactly as given) and on one written to
    disk (the names as this machine's file system hands them back)."""

    PAGE = 'trips/alpha/index.html'

    def outputs(self, files):
        """The same site twice: read back from disk, and held in memory."""
        pages = {k: v for k, v in files.items() if k.endswith('.html')}
        rest = {k: v for k, v in files.items() if not k.endswith('.html')}
        return (('on disk', self.built(files)), ('in memory', self.sc.of(pages, rest)))

    def with_photo(self, held, written):
        """tiny() with one more photo of the report, held under one spelling and named by the page under another: as an
        image, as a srcset candidate, as a link and under the site's full address."""
        files = tiny()
        files['trips/alpha/photos/%s.webp' % held] = ''
        base.body_add(files, self.PAGE, '<img src="photos/%s.webp" srcset="photos/%s.webp 800w, photos/01.webp 1600w" alt="">'
                                        '<a href="photos/%s.webp">Full size</a><a href="%strips/alpha/photos/%s.webp">The same</a>'
                                        % (written, written, written, base.SITE, written))
        return files

    def test_the_two_spellings_are_different_strings_of_the_same_name(self):
        self.assertNotEqual(NFC, NFD)
        self.assertEqual((len(NFC), len(NFD)), (4, 5))
        self.assertEqual(unicodedata.normalize('NFC', NFD), NFC)
        self.assertEqual(NFD.encode('utf-8'), b'cafe\xcc\x81')
        self.assertEqual(NFC.encode('utf-8'), b'caf\xc3\xa9')

    def test_a_file_held_decomposed_and_named_composed_is_found(self):
        for where, out in self.outputs(self.with_photo(NFD, NFC)):
            with self.subTest(where):
                self.assertEqual(self.sc.links(out, self.PAGE), [])
                self.assertEqual(self.sc.links(out), [])

    def test_a_file_held_composed_and_named_decomposed_is_found(self):
        for where, out in self.outputs(self.with_photo(NFC, NFD)):
            with self.subTest(where):
                self.assertEqual(self.sc.links(out, self.PAGE), [])

    def test_the_same_spelling_on_both_sides_is_found_as_before(self):
        for form in (NFC, NFD):
            for where, out in self.outputs(self.with_photo(form, form)):
                with self.subTest(where, form=len(form)):
                    self.assertEqual(self.sc.links(out, self.PAGE), [])

    def test_another_name_is_still_broken(self):
        # one form, not one alphabet: 'cafe' is not 'café', and upper and lower case still differ
        for written in ('cafe', 'Caf\u00e9', 'caf\u00e8', NFC + '2'):
            files = self.with_photo(NFD, written)
            out = self.sc.of({k: v for k, v in files.items() if k.endswith('.html')}, {k: v for k, v in files.items() if not k.endswith('.html')})
            with self.subTest(written=written):
                self.assertEqual(self.sc.links(out, self.PAGE),
                                 ['BROKEN %s -> photos/%s.webp' % (self.PAGE, written)] * 3
                                 + ['BROKEN %s -> %strips/alpha/photos/%s.webp' % (self.PAGE, base.SITE, written)])

    def test_find_gives_the_builds_own_spelling(self):
        files = self.with_photo(NFD, NFC)
        out = self.sc.of({k: v for k, v in files.items() if k.endswith('.html')}, {k: v for k, v in files.items() if not k.endswith('.html')})
        held, asked = 'trips/alpha/photos/%s.webp' % NFD, 'trips/alpha/photos/%s.webp' % NFC
        self.assertIn(held, out.files)
        self.assertNotIn(asked, out.files)
        self.assertEqual(out.find(asked), held)
        self.assertEqual(out.find(held), held)
        self.assertEqual(out.resolve('trips/alpha', 'photos/%s.webp' % NFC), held)
        self.assertIsNone(out.find('trips/alpha/photos/cafe.webp'))
        self.assertIsNone(out.resolve('trips/alpha', 'photos/cafe.webp'))
        self.assertEqual(out.find('trips/alpha/photos/01.webp'), 'trips/alpha/photos/01.webp')

    def test_the_share_image_is_found_under_either_spelling(self):
        for held, written in ((NFD, NFC), (NFC, NFD), (NFC, NFC)):
            files = tiny()
            files['trips/alpha/photos/%s.webp' % held] = ''
            swap(files, self.PAGE, base.share(), base.share(url=base.SITE + 'trips/alpha/photos/%s.webp' % written))
            for where, out in self.outputs(files):
                with self.subTest(where, held=len(held), written=len(written)):
                    self.assertEqual(self.sc.metadata(out, self.PAGE), [])
        files = tiny()
        files['trips/alpha/photos/%s.webp' % NFD] = ''
        swap(files, self.PAGE, base.share(), base.share(url=base.SITE + 'trips/alpha/photos/cafe.webp'))
        self.assertEqual(self.sc.metadata(self.built(files), self.PAGE),
                         ['META %s: og:image file is not in the build: %strips/alpha/photos/cafe.webp' % (self.PAGE, base.SITE)])

    def test_a_folder_is_found_under_either_spelling(self):
        # a folder stands for its index.html; a link into the page needs the id there, which is read from the file as held
        for held, written in ((NFD, NFC), (NFC, NFD)):
            files = tiny()
            page = 'guides/%s/index.html' % held
            files[page] = base.page(page, '<h1 id="top">Guide</h1><a href="../../">Home</a>')
            base.body_add(files, 'about/index.html', '<a href="../guides/%s/">Guide</a><a href="../guides/%s">Guide</a>'
                                                     '<a href="../guides/%s/#top">Its top</a><a href="../guides/%s/index.html">The file</a>'
                                                     % ((written,) * 4))
            for where, out in self.outputs(files):
                with self.subTest(where, held=len(held)):
                    self.assertEqual(self.sc.links(out, 'about/index.html'), [])
                    self.assertEqual(out.resolve('about', '../guides/%s/' % written), out.find(page))
            # ... and a section that is not on that page is still reported
            base.body_add(files, 'about/index.html', '<a href="../guides/%s/#nope">Nowhere</a>' % written)
            self.assertEqual(self.sc.links(self.built(files), 'about/index.html'),
                             ['BROKEN ANCHOR about/index.html -> ../guides/%s/#nope' % written])

    def test_the_whole_check_finds_nothing_in_a_site_with_both_spellings(self):
        files = self.with_photo(NFD, NFC)
        swap(files, self.PAGE, base.share(), base.share(url=base.SITE + 'trips/alpha/photos/%s.webp' % NFC))
        self.assertEqual(self.check(files), [])


# ---------------------------------------------------------------- the combined file: no track, not XML (contract 10.3)

EXT_DAY = ('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1" '
           'xmlns:ns3="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">\n'
           '<trk><name>%s</name><trkseg><trkpt lat="10.0%d" lon="10.0"><ele>1</ele><extensions><ns3:TrackPointExtension>'
           '<ns3:hr>120</ns3:hr></ns3:TrackPointExtension></extensions></trkpt></trkseg></trk>\n</gpx>\n')
NS3 = ' xmlns:ns3="http://www.garmin.com/xmlschemas/TrackPointExtension/v1"'


class CombinedFileTests(Fixture):
    """A multi-day trip's "Download all GPX" file holds its days' <trk> blocks under a root of its own. Two ways it can be
    wrong with every block in place: the days hold no recorded track at all, so the download is empty; and a block uses
    a prefix (a device's extensions) that only the day file's root declared, so the download is not XML."""

    REL = 'trips/tour/tour.gpx'

    def lines(self, combined_text, *day_files):
        """gpx() for a tour whose day files hold these texts and whose combined file is `combined_text`."""
        helpers.make_trip(self.trips, 'tour', title='Tour', kind='multi-day', days=[{'id': '%02d' % (i + 1)} for i in range(len(day_files))])
        files = {self.REL: combined_text}
        for i, text in enumerate(day_files):
            base.write_text(os.path.join(self.trips, 'tour', 'days', '%02d.gpx' % (i + 1)), text)
            files['trips/tour/gpx/tour-day-%02d.gpx' % (i + 1)] = text
        self.put(files)
        return self.sc.gpx(self.sc.read(self.out), self.trips)

    def test_a_sound_combined_file_gives_no_line(self):
        one, two = DAY % ('Day 1', 1, 2), DAY % ('Day 2', 3, 4)
        self.assertEqual(self.lines(base.combined('Tour', one, two), one, two), [])

    def test_day_files_without_a_recorded_track_leave_it_empty(self):
        # both days are planned routes (<rte>, no <trk>): the build still writes the file, since the days have track
        # files, and the page offers it; it holds nothing to download
        route = base.GOAL_GPX
        self.assertNotIn('<trk', route)
        self.assertEqual(self.lines(base.combined('Tour', route, route), route, route),
                         ['GPX %s: holds no track (no day file has a <trk>)' % self.REL])

    def test_one_day_with_a_track_is_not_an_empty_file(self):
        one = DAY % ('Day 1', 1, 2)
        self.assertEqual(self.lines(base.combined('Tour', base.GOAL_GPX, one), base.GOAL_GPX, one), [])

    def test_an_empty_file_beside_days_that_have_tracks_is_the_other_line(self):
        # 'holds no track' is said only when the day files have none either; otherwise the tracks are missing
        one, two = DAY % ('Day 1', 1, 2), DAY % ('Day 2', 3, 4)
        lines = self.lines(base.combined('Tour'), one, two)
        self.assertEqual(lines, ['GPX %s: the track of content/trips/tour/days/01.gpx is not in the file unchanged and in day order' % self.REL,
                                 'GPX %s: the track of content/trips/tour/days/02.gpx is not in the file unchanged and in day order' % self.REL,
                                 'GPX %s: holds 0 <trk> blocks, the day files hold 2' % self.REL])
        self.assertFalse([ln for ln in lines if 'holds no track' in ln])

    def test_a_track_in_the_file_when_the_days_have_none_is_the_count_line(self):
        route = base.GOAL_GPX
        self.assertEqual(self.lines(base.combined('Tour', DAY % ('Stray', 1, 2)), route, route),
                         ['GPX %s: holds 1 <trk> blocks, the day files hold 0' % self.REL])

    def test_a_truncated_file_is_not_well_formed(self):
        one, two = DAY % ('Day 1', 1, 2), DAY % ('Day 2', 3, 4)
        whole = base.combined('Tour', one, two)
        self.assertTrue(whole.endswith('</trk>\n</gpx>\n'))
        lines = self.lines(whole[:-len('</gpx>\n')], one, two)                 # every block is there; the root is never closed
        self.assertEqual(len(lines), 1)
        self.assertRegex(lines[0], r'^GPX trips/tour/tour\.gpx: not well-formed XML \(no element found: line \d+, column \d+\)$')
        # cut inside the last block, the block is missing as well
        lines = self.lines(whole[:-40], one, two)
        self.assertEqual(lines[0], 'GPX %s: the track of content/trips/tour/days/02.gpx is not in the file unchanged and in day order' % self.REL)
        self.assertRegex(lines[-1], r'^GPX trips/tour/tour\.gpx: not well-formed XML \(.+\)$')

    def test_a_prefix_the_root_does_not_declare_is_not_well_formed(self):
        one, two = EXT_DAY % ('Day 1', 1), EXT_DAY % ('Day 2', 2)
        plain = base.combined('Tour', one, two)                                # the header the build wrote before 10.3
        self.assertNotIn('xmlns:ns3', plain)
        self.assertIn('<ns3:hr>120</ns3:hr>', plain)
        lines = self.lines(plain, one, two)
        self.assertEqual(len(lines), 1)
        self.assertRegex(lines[0], r'^GPX trips/tour/tour\.gpx: not well-formed XML \(unbound prefix: line \d+, column \d+\)$')
        # with the declaration the build now writes, the same blocks are a sound file
        declared = plain.replace('xmlns="http://www.topografix.com/GPX/1/1">', 'xmlns="http://www.topografix.com/GPX/1/1"%s>' % NS3, 1)
        self.assertEqual(declared.count('xmlns:ns3='), 1)
        self.assertEqual(self.lines(declared, one, two), [])

    def test_a_doctype_is_refused_unparsed(self):
        one, two = DAY % ('Day 1', 1, 2), DAY % ('Day 2', 3, 4)
        whole = base.combined('Tour', one, two)
        bomb = whole.replace('<gpx ', '<!DOCTYPE gpx [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
                                      '<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">]>\n<gpx ', 1)
        self.assertIn('<!DOCTYPE', bomb)
        started = time.time()
        self.assertEqual(self.lines(bomb, one, two), ['GPX %s: not well-formed XML (DOCTYPE and entity declarations are not accepted)' % self.REL])
        self.assertLess(time.time() - started, 5)
        self.assertEqual(self.lines(whole.replace('<gpx ', '<!DOCTYPE gpx>\n<gpx ', 1), one, two),
                         ['GPX %s: not well-formed XML (DOCTYPE and entity declarations are not accepted)' % self.REL])

    def test_a_comment_or_cdata_is_not_a_declaration(self):
        one, two = DAY % ('Day 1', 1, 2), DAY % ('Day 2', 3, 4)
        whole = base.combined('Tour', one, two)
        text = whole.replace('<metadata>', '<!-- built by the site --><metadata><desc><![CDATA[a <b> c]]></desc>', 1)
        self.assertEqual(self.lines(text, one, two), [])

    def test_a_file_that_is_not_xml_at_all(self):
        one = DAY % ('Day 1', 1, 2)
        lines = self.lines('not a gpx file', one)
        self.assertEqual(lines[:2], ['GPX %s: the track of content/trips/tour/days/01.gpx is not in the file unchanged and in day order' % self.REL,
                                     'GPX %s: holds 0 <trk> blocks, the day files hold 1' % self.REL])
        self.assertRegex(lines[2], r'^GPX trips/tour/tour\.gpx: not well-formed XML \(.+\)$')
        self.assertEqual(len(lines), 3)

    def test_the_whole_check_returns_the_line(self):
        files = tiny()
        files[self.REL] = base.TOUR_GPX[:-len('</gpx>\n')]
        lines = self.check(files)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith('GPX trips/tour/tour.gpx: not well-formed XML ('), lines[0])
        files[self.REL] = base.TOUR_GPX
        self.assertEqual(self.check(files), [])


class SpaceInALinkTests(Fixture):
    """An href or a src is one URL even with a space in it (a file name may hold one); only a srcset is a list of
    candidates. The old check cut every value at its first space, so a link to a real file whose name has a space was
    reported broken, by its stump."""

    def page(self, body):
        files = tiny()
        base.body_add(files, 'about/index.html', body)
        return files

    def test_a_link_to_a_file_with_a_space_in_its_name_is_followed_whole(self):
        files = self.page('<a href="../trips/tour/gpx/tour day two.gpx">a name with spaces</a><img src="../trips/alpha/photos/a b.webp" alt="">')
        files['trips/tour/gpx/tour day two.gpx'] = '<gpx/>'
        files['trips/alpha/photos/a b.webp'] = 'x'
        self.assertEqual(self.sc.links(self.sc.of(files, {})), [])

    def test_a_link_to_a_conflict_copy_is_broken_and_named_whole(self):
        # the check leaves conflict copies out of what it calls the build, so a page that links one links nothing
        files = self.page('<a href="../trips/tour/gpx/tour-day-02 2.gpx">copy</a>')
        files['trips/tour/gpx/tour-day-02 2.gpx'] = '<gpx/>'
        self.assertEqual(self.sc.links(self.sc.of(files, {}), 'about/index.html'),
                         ['BROKEN about/index.html -> ../trips/tour/gpx/tour-day-02 2.gpx'])

    def test_a_missing_one_is_reported_by_its_whole_address(self):
        files = self.page('<a href="../trips/tour/gpx/no such file.gpx">gone</a>')
        self.assertEqual(self.sc.links(self.sc.of(files, {}), 'about/index.html'),
                         ['BROKEN about/index.html -> ../trips/tour/gpx/no such file.gpx'])

    def test_a_srcset_is_still_a_list_of_candidates(self):
        files = self.page('<img src="../trips/alpha/photos/01.webp" srcset="../trips/alpha/photos/01.webp 800w, ../trips/alpha/photos/gone.webp 1600w" alt="">'
                          '<link rel="preload" as="image" imagesrcset="../trips/alpha/photos/01.webp 800w, ../trips/alpha/photos/gone2.webp 1600w">')
        self.assertEqual(self.sc.links(self.sc.of(files, {}), 'about/index.html'),
                         ['BROKEN about/index.html -> ../trips/alpha/photos/gone.webp', 'BROKEN about/index.html -> ../trips/alpha/photos/gone2.webp'])

    def test_urls(self):
        self.assertEqual(self.sc._urls('href', 'a b.gpx'), ['a b.gpx'])
        self.assertEqual(self.sc._urls('src', 'a b.webp'), ['a b.webp'])
        self.assertEqual(self.sc._urls('srcset', 'a.webp 800w, b.webp 1600w'), ['a.webp', 'b.webp'])
        self.assertEqual(self.sc._urls('srcset', 'a.webp'), ['a.webp'])


if __name__ == '__main__':
    unittest.main()
