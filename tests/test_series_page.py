"""Phase 3: the journal page of a series (sitegen.pages.series.page: the factual introduction, the title actions, the cover
hero, the optional highlights, the written-entry navigation and the write-ups toggle) and the journal_highlights field
content.load_trip validates.

Synthetic journals in a temp dir. Two shapes: helpers.make_series (PCT-shaped: day ids 001..., one written day, a
portrait and a landscape photo per day) and journal_days() below (six days whose labels run 1, 2, 3, 5.2, 6, 12 across
two months; days 2, 5.2 and 12 are written, the first day is not, one day has no title and no GPX), which is what the
anchor, navigation and highlight tests need. Three smaller day lists cover what that journal cannot: anchor_days()
(labels that are not plain numbers), highlight_days() (every mix of title and date) and undated_days() (no date in any
day file). RICH and SERIES_RICH are write-ups with real markdown in them, for the "write-ups verbatim" rule. Every
write-up is plainly synthetic. sitegen.pages.series is imported in setUp, so a missing module fails each test clearly
instead of breaking discovery. Every fixture slug starts with PREFIX ('syn-j-'), which no real trip's slug does, so
nothing under rendered/trips/ is read (maps, glyphs and sparklines come out as "missing" comments), and core's copy of
rendered/site/meta.json is patched.
"""
import importlib
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import markdown  # noqa: E402
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, PCT_PROSE, photo, LANDSCAPE, PORTRAIT, SQUARE  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

PREFIX = 'syn-j-'            # every fixture slug starts with it; a real trip's slug never does (see JournalFixture)
SLUG = PREFIX + 'journal'
URL = 'trips/%s/' % SLUG
W1 = 'Synthetic write-up for a test, entry one.'
W2 = 'Synthetic write-up for a test, entry two.'
W3 = 'Synthetic write-up for a test, entry three.'
LONG = ' '.join('Synthetic sentence number %d for a test.' % i for i in range(1, 13))   # well past the 160-character excerpt
SERIES_BODY = 'Synthetic write-up for a test.'
ORGANISED = 'One entry per recorded day, grouped by month.'
EVERY_TRACK = 'Every track is the full recording, not trimmed, with its own GPX download.'

# A day's write-up with everything the markdown subset renders: a two-line paragraph, a heading, emphasis, a link, a
# list and characters that must be escaped. It runs well past any excerpt length, so flattening it to plain text,
# dropping the heading shift or cutting it short each change the HTML the page must carry.
LAST_WORDS = 'The last synthetic sentence of this entry ends here.'
RICH = '\n'.join([
    'Synthetic first paragraph for a test, with *emphasis* and **strong words** in it,',
    'and a second line that stays in the same paragraph.',
    '',
    '## Synthetic heading',
    '',
    'Synthetic second paragraph with a [synthetic link](https://example.com/synthetic?a=1&b=2), an ampersand & a <tag> that must stay text.',
    '',
    '- Synthetic list item one',
    '- Synthetic list item two, with *emphasis*',
    '- Synthetic list item three',
    '',
    ' '.join('Synthetic closing sentence number %d for a test.' % i for i in range(1, 11)) + ' ' + LAST_WORDS,
])
# The journal's own write-up (the body of index.md), in other words than any day's.
SERIES_LAST_WORDS = 'The last synthetic sentence of this introduction ends here.'
SERIES_RICH = '\n'.join([
    'Synthetic journal introduction for a test, with **strong words** and *emphasis*.',
    '',
    '## Synthetic journal heading',
    '',
    'Synthetic journal paragraph with a [journal link](https://example.com/journal) in it.',
    '',
    '1. Synthetic numbered item one',
    '2. Synthetic numbered item two',
    '',
    ' '.join('Synthetic journal sentence number %d for a test.' % i for i in range(1, 9)) + ' ' + SERIES_LAST_WORDS,
])


def load_module(tc, name):
    try:
        return importlib.import_module(name)
    except ImportError as ex:
        tc.fail('%s is not importable: %s' % (name.replace('.', '/') + '.py', ex))


def journal_days():
    """Six recorded days: labels 1, 2, 3, 5.2, 6, 12 (file ids 001-006); written: 2, 5.2, 12; day 3 has no title and no
    GPX; day 1 (track only) carries a portrait and then a landscape photo, so the automatic cover is its second photo."""
    return [
        {'id': '001', 'day': '1', 'title': 'Alpha', 'date': '2024-04-22',
         'photos': [photo('photos/d001-01.webp', PORTRAIT, alt='Synthetic portrait'),
                    photo('photos/d001-02.webp', LANDSCAPE, alt='Synthetic landscape', sm=True)]},
        {'id': '002', 'day': '2', 'title': 'Bravo', 'date': '2024-04-23', 'body': W1,
         'photos': [photo('photos/d002-01.webp', LANDSCAPE, alt='Synthetic camp')]},
        {'id': '003', 'day': '3', 'date': '2024-04-24', 'track': False},
        {'id': '004', 'day': '5.2', 'title': 'Charlie', 'date': '2024-04-25', 'body': W2},
        {'id': '005', 'day': '6', 'title': 'Delta', 'date': '2024-05-01'},
        {'id': '006', 'day': '12', 'title': 'Echo', 'date': '2024-05-02', 'body': W3},
    ]


def anchor_days():
    """Four days whose labels are not all plain numbers: 31 (track only), '5 (zero)' (the first written day), 5.2 and
    'Rest & <b>' (both written; the last has no title). Their anchors are day-31, day-5-zero, day-5-2 and day-Rest-b."""
    return [
        {'id': '001', 'day': '31', 'title': 'Alpha', 'date': '2024-04-22'},
        {'id': '002', 'day': '5 (zero)', 'title': 'Bravo', 'date': '2024-04-23', 'body': W1},
        {'id': '003', 'day': '5.2', 'title': 'Charlie', 'date': '2024-04-24', 'body': W2},
        {'id': '004', 'day': 'Rest & <b>', 'date': '2024-04-25', 'body': W3},
    ]


def highlight_days():
    """Five days, one for every mix of title and date a highlight can meet: titled and dated (written), untitled and dated
    (written), titled and undated, untitled and undated (track only), untitled and undated (written)."""
    return [
        {'id': '001', 'day': '1', 'title': 'Alpha', 'date': '2024-04-22', 'body': W1},
        {'id': '002', 'day': '2', 'date': '2024-04-23', 'body': W2},
        {'id': '003', 'day': '3', 'title': 'Charlie'},
        {'id': '004', 'day': '4'},
        {'id': '005', 'day': '5', 'body': W3},
    ]


def undated_days():
    """Three days with no date in any day file: one written, one titled and track only, one bare recording."""
    return [{'id': '001', 'title': 'One', 'body': W1}, {'id': '002', 'title': 'Two'}, {'id': '003'}]


def add_front_matter(folder, *lines):
    """Insert raw lines into the front matter of <folder>/index.md, exactly as an author would type them. frontmatter.dumps
    (what helpers.make_trip writes with) quotes a numeric string ('001' -> "001"), drops an int's zero padding and skips
    an empty list, so it cannot write `[001, 003]`, a trailing comma or `[]`."""
    path = os.path.join(folder, 'index.md')
    with open(path, encoding='utf-8') as fh:
        head, rest = fh.read().split('\n---\n', 1)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('%s\n%s\n---\n%s' % (head, '\n'.join(lines), rest))


def positions(root, *nodes):
    """Document-order positions of nodes under root, by identity."""
    seq = list(root.walk())
    return [next(i for i, x in enumerate(seq) if x is node) for node in nodes]


def image_preloads(doc):
    return [el for el in doc.find('head').find_all('link', attrs={'rel': 'preload'}) if el['as'] == 'image']


def caption_items(root):
    """The items of a core.map_caption() block as a reader sees them, in order, without the screen-reader separators."""
    out = []
    for item in root.find_all('span', cls='mi'):
        own = [c if isinstance(c, str) else ('' if 'sr' in c.classes else c.text(clean=False)) for c in item.children]
        out.append(helpers.plain_text(''.join(own)))
    return out


def article_html(page_html, anchor):
    """One day article exactly as the page carries it, from its opening tag to its closing tag (day articles never nest)."""
    m = re.search(r'<article\b[^>]*\bid="%s"[^>]*>' % re.escape(anchor), page_html)
    if m is None:
        raise AssertionError('the page has no <article id="%s">' % anchor)
    return page_html[m.start():page_html.index('</article>', m.end()) + len('</article>')]


def inner_html(html_, cls):
    """What the first <div> with this class token holds, exactly as written: from the end of its opening tag to the next
    </div>. Right for a write-up, whose markdown never produces a div of its own."""
    m = re.search(r'<div\b[^>]*\bclass="(?:[^"]*\s)?%s(?:\s[^"]*)?"[^>]*>' % re.escape(cls), html_)
    if m is None:
        raise AssertionError('no <div class="... %s ..."> in %r' % (cls, html_[:200]))
    return html_[m.end():html_.index('</div>', m.end())]


class JournalFixture(unittest.TestCase):

    def setUp(self):
        self.series = load_module(self, 'sitegen.pages.series')
        self.report = load_module(self, 'sitegen.pages.report')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        patcher = mock.patch.object(core, '_SITE_META', [{'hash': '', 'maps': {}, 'regions': [], 'all_regions': []}])
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        # whichever helper wrote it, every trip folder of a test carries the fixture prefix
        stray = [name for name in sorted(os.listdir(self.tmp)) if not name.startswith(PREFIX)]
        self.assertEqual(stray, [], 'fixture folders without the %r prefix' % PREFIX)

    def synthetic(self, slug):
        """A page built for this slug must read nothing a real trip rendered: the slug carries the fixture prefix, which no
        real slug does, and no folder of that name exists under rendered/trips/."""
        self.assertTrue(slug.startswith(PREFIX), 'fixture slug %r lacks the %r prefix' % (slug, PREFIX))
        self.assertFalse(os.path.lexists(os.path.join(content.RENDERED, 'trips', slug)), 'fixture slug %r names a real trip' % slug)
        return slug

    def journal(self, slug=SLUG, days=None, lines=(), **meta):
        """The six-day journal (or `days`), loaded; `lines` are raw front-matter lines added to index.md."""
        self.synthetic(slug)
        m = dict(title='Synthetic Journal', kind='series', date='2024-04-22', end_date='2024-05-02', place='Start to Finish',
                 region='Synthetic Range')
        m.update(meta)
        folder = helpers.make_trip(self.tmp, slug, days=journal_days() if days is None else days, **m)
        if lines:
            add_front_matter(folder, *lines)
        return helpers.load(self.tmp, slug)

    def pct(self, slug=SLUG, lines=(), **kw):
        """helpers.make_series under a synthetic slug (its default is the real journal's), loaded."""
        folder = helpers.make_series(self.tmp, self.synthetic(slug), **kw)
        if lines:
            add_front_matter(folder, *lines)
        return helpers.load(self.tmp, slug)

    def page(self, t):
        """The journal's page on a site that holds only this journal."""
        return self.series.page(t, helpers.make_site([t]))

    def doc(self, t):
        return Doc(self.page(t).html)


# ---------------------------------------------------------------- content.load_trip: journal_highlights

class HighlightsFieldTests(JournalFixture):

    def ids(self, t):
        return [d['id'] for d in t['journal_highlights']]

    def assertLoadRaises(self, slug, *needles):
        """load_trip raises content.ContentError prefixed 'content/trips/<slug>/index.md: ' that names the field."""
        with self.assertRaises(content.ContentError) as cm:
            helpers.load(self.tmp, slug)
        msg = str(cm.exception)
        self.assertTrue(msg.startswith('content/trips/%s/index.md: ' % slug), 'unexpected prefix: %r' % msg)
        self.assertIn('journal_highlights', msg)
        for needle in needles:
            self.assertIn(needle, msg)
        return msg

    def test_absent_key_gives_an_empty_list(self):
        # contract 1: absent -> []
        t = self.pct()
        self.assertNotIn('journal_highlights', t['meta'])
        self.assertEqual(t['journal_highlights'], [])

    def test_zero_padded_ids_give_the_day_dicts(self):
        # contract 1: journal_highlights: [001, 003] -> the matching day dicts (ids as written in the days/NNN.md names)
        t = self.pct(lines=['journal_highlights: [001, 003]'])
        self.assertEqual(self.ids(t), ['001', '003'])
        self.assertIs(t['journal_highlights'][0], t['days'][0])
        self.assertIs(t['journal_highlights'][1], t['days'][2])
        self.assertEqual([d['id'] for d in t['days']], ['001', '002', '003'])   # the day list itself is untouched

    def test_listed_order_is_kept_not_file_order(self):
        # contract 1: the matching day dicts in the listed order
        t = self.pct(lines=['journal_highlights: [003, 001, 002]'])
        self.assertEqual(self.ids(t), ['003', '001', '002'])

    def test_bare_ints_are_padded_to_the_file_name_width(self):
        # contract 1: ids may be ints; a bare number is zero-padded to the width the day files use
        three = self.pct(slug='syn-j-three-wide', lines=['journal_highlights: [1, 3]'])
        self.assertEqual(self.ids(three), ['001', '003'])
        two = self.journal(slug='syn-j-two-wide', days=[{'title': 'One'}, {'title': 'Two'}, {'title': 'Three'}],
                           lines=['journal_highlights: [3, 001]'])
        self.assertEqual([d['id'] for d in two['days']], ['01', '02', '03'])
        self.assertEqual(self.ids(two), ['03', '01'])

    def test_a_quoted_id_resolves(self):
        # contract 1: ids may be strings; helpers.make_trip writes a numeric string quoted, which is the form under test
        folder = helpers.make_series(self.tmp, SLUG, journal_highlights=['002', '001'])
        with open(os.path.join(folder, 'index.md'), encoding='utf-8') as fh:
            self.assertIn('journal_highlights: ["002", "001"]\n', fh.read())
        t = helpers.load(self.tmp, SLUG)
        self.assertEqual(self.ids(t), ['002', '001'])
        self.assertIs(t['journal_highlights'][0], t['days'][1])

    def test_a_block_list_reads_like_an_inline_one(self):
        # contract 1: the value is a list of day ids; the front-matter subset also writes a list one `- item` per line
        t = self.pct(lines=['journal_highlights:', '  - 003', '  - "001"'])
        self.assertEqual(self.ids(t), ['003', '001'])

    def test_an_unknown_id_raises(self):
        # contract 1: an id that matches no day is a ContentError prefixed content/trips/<slug>/index.md
        for i, line in enumerate(('journal_highlights: [001, 099]', 'journal_highlights: [4]', 'journal_highlights: ["nope"]')):
            with self.subTest(line=line):
                slug = 'syn-j-unknown-%d' % i
                add_front_matter(helpers.make_series(self.tmp, slug), line)
                self.assertLoadRaises(slug)

    def test_a_day_label_is_not_an_id(self):
        # contract 1: ids are the days/NNN.md file names; the label of day 004 (5.2) names no file
        for i, line in enumerate(('journal_highlights: [5.2]', 'journal_highlights: ["5.2"]')):
            with self.subTest(line=line):
                slug = 'syn-j-label-%d' % i
                folder = helpers.make_trip(self.tmp, slug, kind='series', days=journal_days())
                add_front_matter(folder, line)
                self.assertLoadRaises(slug)

    def test_a_repeat_raises(self):
        # contract 1: a duplicate is a ContentError, however the day is spelled the second time
        for i, line in enumerate(('journal_highlights: [001, 003, 001]', 'journal_highlights: ["001", 1]',
                                  'journal_highlights: [2, 002]')):
            with self.subTest(line=line):
                slug = 'syn-j-repeat-%d' % i
                add_front_matter(helpers.make_series(self.tmp, slug), line)
                self.assertLoadRaises(slug)

    def test_a_non_list_value_raises(self):
        # contract 1: a non-list value is a ContentError
        cases = (['journal_highlights: 001'], ['journal_highlights: "001"'], ['journal_highlights: 001, 003'],
                 ['journal_highlights: true'], ['journal_highlights:', '  first: 001'])
        for i, lines in enumerate(cases):
            with self.subTest(lines=lines):
                slug = 'syn-j-scalar-%d' % i
                add_front_matter(helpers.make_series(self.tmp, slug), *lines)
                self.assertLoadRaises(slug)

    def test_a_trailing_empty_item_is_ignored(self):
        # contract 1 (as search_aliases reads a list): a trailing comma's empty item is not an id
        t = self.pct(lines=['journal_highlights: [001, 003, ]'])
        self.assertEqual(self.ids(t), ['001', '003'])

    def test_an_empty_list_gives_an_empty_list(self):
        # contract 1 / plan 10: the list stays empty until entries are chosen
        t = self.pct(lines=['journal_highlights: []'])
        self.assertEqual(t['journal_highlights'], [])

    def test_a_list_on_a_single_day_trip_raises(self):
        # contract 9: a non-empty list on a trip that is not `kind: series` is a ContentError (this folder has no day files
        # either, but what the author needs to hear is that the field belongs to a journal)
        folder = helpers.make_trip(self.tmp, 'syn-j-single-day', title='Single Day', date='2026-01-17', track=True)
        add_front_matter(folder, 'journal_highlights: [001]')
        self.assertLoadRaises('syn-j-single-day', 'kind: series')

    def test_a_journal_without_day_files_raises(self):
        # contract 1: the ids name days/NNN.md files; a journal folder without any has none to name, and the error says so
        slug = PREFIX + 'no-day-files'
        folder = helpers.make_trip(self.tmp, slug, title='No Day Files', kind='series', date='2024-04-22')
        self.assertFalse(os.path.exists(os.path.join(folder, 'days')))
        bare = helpers.load(self.tmp, slug)                # the folder itself loads: only the list is at fault
        self.assertEqual((bare['kind'], bare['days'], bare['journal_highlights']), ('series', [], []))
        add_front_matter(folder, 'journal_highlights: [001]')
        self.assertLoadRaises(slug, 'needs day files')

    def test_a_list_on_a_trip_that_is_not_a_journal_raises_even_with_day_files(self):
        # only a journal page shows highlights: a multi-day trip that lists some would be accepted and never shown
        folder = helpers.make_trip(self.tmp, 'syn-j-two-days', title='Two Days', kind='multi-day', date='2026-03-01', end_date='2026-03-02',
                                   days=[{'title': 'Up', 'date': '2026-03-01'}, {'title': 'Down', 'date': '2026-03-02'}])
        add_front_matter(folder, 'journal_highlights: [01]')
        self.assertLoadRaises('syn-j-two-days', 'kind: series', 'multi-day')

    def test_an_empty_list_is_fine_on_any_trip(self):
        # 'none chosen yet' is not an error anywhere
        folder = helpers.make_trip(self.tmp, 'syn-j-single-day', title='Single Day', date='2026-01-17', track=True)
        add_front_matter(folder, 'journal_highlights: []')
        self.assertEqual(helpers.load(self.tmp, 'syn-j-single-day')['journal_highlights'], [])
        folder = helpers.make_trip(self.tmp, 'syn-j-two-days', title='Two Days', kind='multi-day', date='2026-03-01', end_date='2026-03-02',
                                   days=[{'title': 'Up', 'date': '2026-03-01'}, {'title': 'Down', 'date': '2026-03-02'}])
        add_front_matter(folder, 'journal_highlights: [ ]')
        self.assertEqual(helpers.load(self.tmp, 'syn-j-two-days')['journal_highlights'], [])

    def test_every_trip_dict_has_the_key(self):
        # contract 1: non-series trips: [] (the key is always present)
        helpers.make_trip(self.tmp, 'syn-j-single-day', title='Single Day', date='2026-01-17', track=True)
        helpers.make_trip(self.tmp, 'syn-j-two-days', title='Two Days', kind='multi-day', date='2026-03-01', end_date='2026-03-02',
                          days=[{'title': 'Up', 'date': '2026-03-01'}, {'title': 'Down', 'date': '2026-03-02'}])
        helpers.make_trip(self.tmp, 'syn-j-some-goal', title='Some Goal', kind='planned')
        helpers.make_series(self.tmp, SLUG)
        for slug in ('syn-j-single-day', 'syn-j-two-days', 'syn-j-some-goal', SLUG):
            with self.subTest(slug=slug):
                t = helpers.load(self.tmp, slug)
                self.assertIn('journal_highlights', t)
                self.assertEqual(t['journal_highlights'], [])


# ---------------------------------------------------------------- lede(): the introduction

class LedeTests(JournalFixture):

    def lede_text(self, t):
        p = Doc(self.series.lede(t)).find('p', cls='ser-lede')
        self.assertIsNotNone(p, 'lede() has no <p class="ser-lede">: %r' % self.series.lede(t))
        return p.text()

    def facts(self, t, place=', Start to Finish'):
        return '%s: %d recorded days, %s%s.' % (t['title'], len(t['days']), core.frange(t['date'], t['end_date']), place)

    def test_facts_sentence_leads_then_how_the_log_is_organised(self):
        # contract 5, Introduction: '<title>: <N> recorded days, <core.frange(date, end_date)>[, <place>].' then the
        # existing sentences, numbers from the days
        t = self.journal()
        facts = 'Synthetic Journal: 6 recorded days, %s, Start to Finish.' % core.frange(t['date'], t['end_date'])
        self.assertEqual(facts, 'Synthetic Journal: 6 recorded days, Apr 22 – May 2, 2024, Start to Finish.')
        want = ' '.join([facts, ORGANISED,
                         'The 3 days with a write-up carry the notes from that day and any photos; the other 3 show the track, '
                         '1 of them with photos.', EVERY_TRACK])
        self.assertEqual(self.lede_text(t), want)

    def test_facts_sentence_without_a_place_ends_at_the_dates(self):
        # contract 5, Introduction: the place is optional ('[, <place>]')
        t = self.journal(place=None)
        self.assertIsNone(t['place'])
        text = self.lede_text(t)
        self.assertTrue(text.startswith(self.facts(t, place='') + ' ' + ORGANISED), text)
        self.assertNotIn('Start to Finish', text)

    def test_track_only_days_without_photos_show_the_track_only(self):
        # contract 5, Introduction: '...the other <R> show the track[, <P> of them with photos | only].'
        days = [dict(d, photos=None) for d in journal_days()]
        t = self.journal(days=days)
        self.assertIn('The 3 days with a write-up carry the notes from that day and any photos; the other 3 show the track only.',
                      self.lede_text(t))

    def test_one_written_day_and_one_track_only_day_read_in_the_singular(self):
        # the same sentences, grammatical for a count of one
        t = self.pct(slug='syn-j-one-written-journal', written_day=1, tracks=(True, True, True))   # 3 days, 1 written, 2 with photos
        text = self.lede_text(t)
        self.assertIn('The one day with a write-up carries its notes and any photos; the other 2 show the track, 2 of them with photos.', text)
        self.assertNotIn('The 1 days', text)
        days = [{'title': 'One', 'date': '2024-04-22', 'body': W1}, {'title': 'Two', 'date': '2024-04-23', 'body': W2},
                {'title': 'Three', 'date': '2024-04-24'}]
        t = self.journal(slug='syn-j-one-track-only-journal', days=days, end_date='2024-04-24')
        self.assertIn('The 2 days with a write-up carry the notes from that day and any photos; the other day shows the track only.',
                      self.lede_text(t))
        one = self.journal(slug='syn-j-one-day-journal', days=[{'title': 'Only', 'date': '2024-04-22'}], end_date='2024-04-22')
        self.assertTrue(self.lede_text(one).startswith('Synthetic Journal: 1 recorded day, '), self.lede_text(one))

    def test_one_track_only_day_with_photos_shows_the_track_and_its_photos(self):
        # contract 9, singular forms: the photos of the one day without a write-up are 'its photos', not '1 of them'
        shot = [photo('photos/d009-01.webp', LANDSCAPE, alt='Synthetic view')]
        want = 'the other day shows the track and its photos.'
        days = [{'title': 'One', 'date': '2024-04-22', 'body': W1}, {'title': 'Two', 'date': '2024-04-23', 'body': W2},
                {'title': 'Three', 'date': '2024-04-24', 'photos': shot}]
        two = self.lede_text(self.journal(slug=PREFIX + 'two-written-one-shot', days=days, end_date='2024-04-24'))
        self.assertIn('The 2 days with a write-up carry the notes from that day and any photos; ' + want, two)
        days = [{'title': 'One', 'date': '2024-04-22', 'body': W1}, {'title': 'Two', 'date': '2024-04-23', 'photos': shot}]
        one = self.lede_text(self.journal(slug=PREFIX + 'one-written-one-shot', days=days, end_date='2024-04-23'))
        self.assertIn('The one day with a write-up carries its notes and any photos; ' + want, one)
        for text in (two, one):
            self.assertNotIn('of them with photos', text)
            self.assertNotIn('track only', text)
            self.assertNotIn('other 1 ', text)
        # only the track-only day's photos count: a written day's photos are already 'any photos'
        days = [{'title': 'One', 'date': '2024-04-22', 'body': W1, 'photos': shot}, {'title': 'Two', 'date': '2024-04-23'}]
        text = self.lede_text(self.journal(slug=PREFIX + 'written-day-shot', days=days, end_date='2024-04-23'))
        self.assertIn('The one day with a write-up carries its notes and any photos; the other day shows the track only.', text)

    def test_every_day_written_says_so(self):
        # contract 5, Introduction: 'Every day has a write-up.' replaces the written / track-only split
        days = [{'title': 'One', 'date': '2024-04-22', 'body': W1}, {'title': 'Two', 'date': '2024-04-23', 'body': W2}]
        t = self.journal(days=days, end_date='2024-04-23')
        self.assertEqual(self.lede_text(t), ' '.join([self.facts(t), ORGANISED, 'Every day has a write-up.', EVERY_TRACK]))

    def test_no_day_written_claims_no_write_up(self):
        # contract 5, Introduction: numbers from the days; with nothing written neither write-up sentence is true
        t = self.pct(written_day=None)
        text = self.lede_text(t)
        self.assertTrue(text.startswith(self.facts(t, place=', Mexico to Canada') + ' ' + ORGANISED), text)
        self.assertTrue(text.endswith(EVERY_TRACK), text)
        self.assertNotIn('write-up', text)

    def test_lede_carries_no_day_prose(self):
        # contract 5, Introduction: from fields only, no feelings, no narrative (the day's own words stay in its entry)
        t = self.pct()
        self.assertEqual(t['days'][0]['body_md'], PCT_PROSE)
        html_ = self.series.lede(t)
        self.assertNotIn(PCT_PROSE, html_)
        self.assertNotIn('Walked north', html_)
        for d in t['days']:
            self.assertNotIn(d['title'], html_)
        self.assertNotIn(PCT_PROSE, self.doc(t).find(cls='ser-intro-t').text())

    def test_the_series_write_up_replaces_the_facts(self):
        # contract 5, Introduction: the series write-up when one exists (verbatim), else the facts
        t = self.pct(body=SERIES_BODY)
        self.assertEqual(t['body_md'], SERIES_BODY)
        lede = Doc(self.series.lede(t))
        self.assertEqual(lede.text(), SERIES_BODY)
        self.assertIsNone(lede.find('p', cls='ser-lede'))
        self.assertNotIn('recorded days', self.series.lede(t))
        intro = self.doc(t).find(cls='ser-intro-t')
        self.assertIn(SERIES_BODY, intro.text())
        self.assertNotIn(ORGANISED, intro.text())

    def test_lede_escapes_the_title_and_the_place(self):
        # contract 5, Introduction: built from fields; a field is text, never markup
        t = self.journal(title='Synthetic <Journal> & Co', place='Here <b>to</b> There')
        html_ = self.series.lede(t)
        self.assertIn('Synthetic &lt;Journal&gt; &amp; Co: 6 recorded days', html_)
        self.assertIsNone(Doc(html_).find('b'))
        self.assertIn(', Here <b>to</b> There.', self.lede_text(t))


# ---------------------------------------------------------------- the page: title actions

class JournalPageFixture(JournalFixture):

    def setUp(self):
        super().setUp()
        self.t = self.journal()
        self.days = self.t['days']
        self.site = helpers.make_site([self.t])
        self.pg = self.series.page(self.t, self.site)
        self.d = Doc(self.pg.html)
        self.main = self.d.by_id('main')
        self.actions = self.main.find(cls='rep-actions')

    def action(self, text):
        return next((a for a in self.actions.find_all('a') if a.text() == text), None)


class TitleActionTests(JournalPageFixture):

    def test_read_the_first_written_entry_targets_the_first_written_day(self):
        # contract 5, Actions: <a class="btn" href="#<anchor of the first written day>">Read the first written entry</a>
        a = self.action('Read the first written entry')
        self.assertIsNotNone(a, 'no "Read the first written entry" action')
        self.assertEqual(a.classes, ['btn', 'btn--ink'])   # Phase 11 (visual-20): the page's one primary action, in ink
        self.assertEqual(a['href'], '#' + self.series.day_anchor(self.days[1]))
        self.assertEqual(a['href'], '#day-2')            # day 1 is track only: the first written entry is not the first day
        self.assertEqual(self.action('Browse all recordings').classes, ['btn'])
        self.assertEqual(self.main.by_id('day-2').tag, 'article')

    def test_read_the_first_written_entry_uses_the_anchor_of_a_decimal_day(self):
        # contract 5, Actions / plan 16: the href is day_anchor() of the day, so a first written Day 5.2 is #day-5-2
        days = journal_days()
        days[1]['body'] = ''                               # Day 2 loses its write-up: Day 5.2 is now the first written day
        t = self.journal(slug=PREFIX + 'decimal-first', days=days)
        first = self.series.first_written(t)
        self.assertEqual((first['id'], first['label']), ('004', '5.2'))
        main = self.doc(t).by_id('main')
        a = next((x for x in main.find(cls='rep-actions').find_all('a') if x.text() == 'Read the first written entry'), None)
        self.assertIsNotNone(a, 'no "Read the first written entry" action')
        self.assertEqual(a['href'], '#day-5-2')
        self.assertEqual(a['href'], '#' + self.series.day_anchor(first))
        target = main.by_id(a['href'][1:])
        self.assertEqual(target.tag, 'article')
        self.assertIn('has-wu', target.classes)            # it lands on a written entry
        self.assertIsNone(main.by_id('day-5.2'))

    def test_read_the_first_written_entry_is_omitted_when_no_day_is_written(self):
        # contract 5, Actions: omitted when no day is written
        t = self.journal(slug='syn-j-unwritten', days=[dict(d, body='') for d in journal_days()])
        actions = self.doc(t).by_id('main').find(cls='rep-actions')
        texts = [a.text() for a in actions.find_all('a') if 'ser-continue' not in a.classes]
        self.assertNotIn('Read the first written entry', texts)
        self.assertEqual(texts, ['Browse all recordings'])

    def test_browse_all_recordings_opens_the_day_log_and_carries_the_filter_hook(self):
        # contract 5, Actions: <a class="btn" href="#days" data-ser-all>Browse all recordings</a>
        a = self.action('Browse all recordings')
        self.assertIsNotNone(a, 'no "Browse all recordings" action')
        self.assertIn('btn', a.classes)
        self.assertEqual(a['href'], '#days')
        self.assertIn('data-ser-all', a)
        self.assertEqual(self.main.by_id('days').tag, 'section')

    def test_copy_link_control_carries_the_page_url(self):
        # contract 4: core.copy_link(core.SITE_URL + here), the last title action (cls 'btn', label 'Copy link')
        copy = self.actions.find('span', cls='copy')
        self.assertIsNotNone(copy, 'no copy-link control among the title actions')
        btn = copy.find('button')
        self.assertEqual(btn['type'], 'button')
        self.assertEqual(btn.classes, ['btn', 'copy-btn'])
        self.assertEqual(btn['data-copy'], core.SITE_URL + self.t['url'])
        self.assertEqual(btn['data-copy'], 'https://esichak.github.io/personal-website/trips/syn-j-journal/')
        self.assertEqual(btn.text(), 'Copy link')
        self.assertEqual(btn.find('span').text(), 'Copy link')
        self.assertIsNotNone(btn.find('svg'), 'the copy-link button has no icon')
        # contract 10.1: the page's own control names nothing further (of=''), so its markup is the plain one
        self.assertEqual(btn.find_all('span', cls='sr'), [])
        self.assertIn(core.copy_link(core.SITE_URL + self.t['url']), self.pg.html)
        msg = copy.find('span', cls='copy-msg')
        self.assertEqual(msg['role'], 'status')
        self.assertIn('t-small', msg.classes)
        self.assertEqual(msg.text(), '')                   # filled by base.js: 'Link copied', or the URL to copy by hand
        self.assertIs(copy.elements()[-1], msg)

    def test_actions_come_in_the_contract_order(self):
        # contract 5, Actions: first written entry, browse all recordings, then the copy-link control; Phase 11 (features-08)
        # adds the 'Continue reading' link last, empty and hidden until series.js fills it from this browser's storage
        self.assertEqual([el.text() for el in self.actions.elements()],
                         ['Read the first written entry', 'Browse all recordings', 'Copy link', ''])
        self.assertEqual([el.tag for el in self.actions.elements()], ['a', 'a', 'span', 'a'])
        cont = self.actions.elements()[-1]
        self.assertEqual(cont.classes, ['alink', 'ser-continue'])
        self.assertIn('hidden', cont)
        self.assertEqual(cont['href'], '#days')

    def test_day_by_day_button_is_gone_and_the_day_log_heading_stays(self):
        # contract 5, Actions: the old 'Day by day' action goes; 'Download all GPX' is not added; the log keeps its heading
        self.assertIsNone(self.action('Day by day'))
        self.assertNotIn('Day by day', self.actions.text())
        self.assertNotIn('Download all GPX', self.main.text())
        h = self.main.by_id('days-h')
        self.assertEqual((h.tag, h.text()), ('h2', 'Day by day'))
        self.assertEqual(self.main.by_id('days')['aria-labelledby'], 'days-h')


class FirstWrittenTests(JournalFixture):

    def test_first_written_is_the_first_day_with_a_write_up(self):
        # contract 5, Actions: series.first_written(t) -> that day dict
        t = self.journal()
        self.assertIs(self.series.first_written(t), t['days'][1])
        self.assertEqual(self.series.first_written(t)['label'], '2')

    def test_first_written_is_none_when_no_day_is_written(self):
        # contract 5, Actions: ... or None
        t = self.pct(written_day=None)
        self.assertIsNone(self.series.first_written(t))


# ---------------------------------------------------------------- highlights()

class HighlightsTests(JournalFixture):

    LINE = 'journal_highlights: [004, 003]'   # Day 5.2 (written, titled), then Day 3 (track only, untitled)

    def setUp(self):
        super().setUp()
        self.t = self.journal(lines=[self.LINE])
        self.listed = self.t['journal_highlights']
        self.sec = Doc(self.series.highlights(self.t, URL)).find('section')
        self.items = self.sec.find('ol', cls='ser-high-l').find_all('li')

    def test_empty_without_listed_days(self):
        # contract 5, Highlights: '' when t['journal_highlights'] is empty (the PCT ships with none)
        t = self.journal(slug='syn-j-no-highlights')
        self.assertEqual(t['journal_highlights'], [])
        self.assertEqual(self.series.highlights(t, t['url']), '')
        main = self.doc(t).by_id('main')
        self.assertIsNone(main.by_id('highlights'))
        self.assertIsNone(main.find(cls='ser-high'))
        self.assertNotIn('Highlights', main.text())

    def test_section_heading_and_entry_count(self):
        # contract 5, Highlights: section.ser-high#highlights labelled by h2#high-h 'Highlights', then 'N ENTRIES'
        self.assertEqual(self.sec['id'], 'highlights')
        self.assertIn('ser-high', self.sec.classes)
        self.assertEqual(self.sec['aria-labelledby'], 'high-h')
        h = self.sec.by_id('high-h')
        self.assertEqual((h.tag, h.text()), ('h2', 'Highlights'))
        self.assertEqual(self.sec.find('span', cls='shead-m').text(), '2 ENTRIES')

    def test_a_single_entry_is_counted_in_the_singular(self):
        # contract 5, Highlights: the count line reads '1 ENTRY' for one listed day
        t = self.journal(slug='syn-j-one-highlight', lines=['journal_highlights: [006]'])
        sec = Doc(self.series.highlights(t, t['url'])).find('section')
        self.assertEqual(sec.find('span', cls='shead-m').text(), '1 ENTRY')
        self.assertEqual(len(sec.find_all('li')), 1)

    def test_one_item_per_listed_day_in_the_listed_order(self):
        # contract 5, Highlights: one <li> per listed day, in the listed order, linking '#' + day_anchor
        self.assertEqual([d['id'] for d in self.listed], ['004', '003'])
        self.assertEqual(len(self.items), 2)
        links = [li.find('a', cls='ser-high-a') for li in self.items]
        self.assertEqual([a['href'] for a in links], ['#' + self.series.day_anchor(d) for d in self.listed])
        self.assertEqual([a['href'] for a in links], ['#day-5-2', '#day-3'])
        self.assertEqual([a.find('span', cls='t-label').text() for a in links], ['Day 5.2', 'Day 3'])
        self.assertEqual(links[0].find('span', cls='ser-high-t').text(), 'Charlie')

    def test_item_markup_of_a_titled_dated_written_day(self):
        # contract 10.6: <li><a class="ser-high-a" href="#<anchor>"><span class="t-label">Day N</span><span
        # class="ser-high-t">name</span></a><p class="t-mono-s">DATE</p><p class="t-excerpt">...</p></li>
        li = self.items[0]
        self.assertEqual([(el.tag, el.classes) for el in li.elements()],
                         [('a', ['ser-high-a']), ('p', ['t-mono-s']), ('p', ['t-excerpt'])])
        a = li.elements()[0]
        self.assertEqual([(el.tag, el.classes, el.text()) for el in a.elements()],
                         [('span', ['t-label'], 'Day 5.2'), ('span', ['ser-high-t'], 'Charlie')])
        self.assertIn('<li><a class="ser-high-a" href="#day-5-2"><span class="t-label">Day 5.2</span>'
                      '<span class="ser-high-t">Charlie</span></a><p class="t-mono-s">THU, APR 25</p>'
                      '<p class="t-excerpt">%s</p></li>' % W2, self.series.highlights(self.t, URL))

    def test_date_line_is_the_day_date_in_caps(self):
        # contract 10.6: <p class="t-mono-s">DATE</p> is core.fdate(d, 'day').upper(), for a day with a title and a date
        d = self.listed[0]
        self.assertTrue(d['title'] and d['date'])
        lines = self.items[0].find_all('p', cls='t-mono-s')
        self.assertEqual([p.text() for p in lines], [core.fdate(d['date'], 'day').upper()])
        self.assertEqual(lines[0].text(), 'THU, APR 25')

    def test_excerpt_only_for_written_days(self):
        # contract 5, Highlights: <p class="t-excerpt"> markdown.plain(body, 160) when the day is written
        self.assertEqual(self.items[0].find('p', cls='t-excerpt').text(), W2)
        self.assertEqual(W2, markdown.plain(self.listed[0]['body_md'], 160))
        self.assertIsNone(self.items[1].find('p', cls='t-excerpt'))
        self.assertEqual(self.items[1].find_all('p'), [])         # track only and untitled: the link is the whole item

    def test_a_long_write_up_is_cut_to_the_excerpt_length(self):
        # contract 5, Highlights: markdown.plain(body, 160), never the whole entry
        days = journal_days()
        days[3]['body'] = LONG
        t = self.journal(slug='syn-j-long-entry', days=days, lines=['journal_highlights: [004]'])
        ex = Doc(self.series.highlights(t, t['url'])).find('p', cls='t-excerpt').text()
        self.assertEqual(ex, markdown.plain(LONG, 160))
        self.assertTrue(ex.endswith('…'), ex)
        self.assertLessEqual(len(ex), 161)
        self.assertTrue(LONG.startswith(ex[:-1]))

    def test_an_untitled_day_shows_its_date_as_the_title(self):
        # contract 10.6: name = the day's title, else its date ('day' format); that date is then not printed a second time
        d, li = self.listed[1], self.items[1]
        self.assertIsNone(d['title'])
        self.assertEqual(li.find('span', cls='ser-high-t').text(), core.fdate(d['date'], 'day'))
        self.assertEqual(li.find('span', cls='ser-high-t').text(), 'Wed, Apr 24')
        self.assertEqual(li.find_all('p', cls='t-mono-s'), [])
        self.assertEqual(li.text().upper().count('APR 24'), 1)
        self.assertEqual(li.find('a', cls='ser-high-a').find('span', cls='t-label').text(), 'Day 3')

    def mixed(self):
        """The five highlight_days(), all listed in file order: (journal, its <li> elements)."""
        t = self.journal(slug=PREFIX + 'mixed-highlights', days=highlight_days(), lines=['journal_highlights: [001, 002, 003, 004, 005]'])
        self.assertEqual([(bool(d['title']), bool(d['date']), bool(d['body_md'])) for d in t['journal_highlights']],
                         [(True, True, True), (False, True, True), (True, False, False), (False, False, False), (False, False, True)])
        return t, Doc(self.series.highlights(t, t['url'])).find('ol', cls='ser-high-l').find_all('li')

    def parts(self, li):
        """(the link's text spans, the date lines, the excerpts) of one highlight."""
        a = li.find('a', cls='ser-high-a')
        self.assertIs(li.elements()[0], a)
        return ([(el.classes, el.text()) for el in a.elements()], [p.text() for p in li.find_all('p', cls='t-mono-s')],
                [p.text() for p in li.find_all('p', cls='t-excerpt')])

    def test_an_untitled_dated_day_is_named_by_its_date_once(self):
        # contract 10.6: an untitled day's date is its name and is not printed twice; a written one keeps its excerpt
        t, items = self.mixed()
        self.assertEqual(self.parts(items[1]), ([(['t-label'], 'Day 2'), (['ser-high-t'], 'Tue, Apr 23')], [], [W2]))
        self.assertEqual([(el.tag, el.classes) for el in items[1].elements()], [('a', ['ser-high-a']), ('p', ['t-excerpt'])])
        self.assertEqual(items[1].text().upper().count('APR 23'), 1)

    def test_an_untitled_undated_day_is_day_n_alone(self):
        # contract 10.6: a day with neither title nor date has no .ser-high-t span (and no date line); the link reads Day N
        t, items = self.mixed()
        bare, written = items[3], items[4]
        self.assertEqual(self.parts(bare), ([(['t-label'], 'Day 4')], [], []))
        self.assertEqual([el.tag for el in bare.elements()], ['a'])
        self.assertEqual(bare.find('a')['href'], '#day-4')
        self.assertEqual(bare.find('a').text(), 'Day 4')
        self.assertEqual(bare.find_all('span', cls='ser-high-t'), [])
        self.assertEqual(self.parts(written), ([(['t-label'], 'Day 5')], [], [W3]))
        self.assertEqual(written.find('a').text(), 'Day 5')
        # nothing empty is left behind where the name would be
        html_ = self.series.highlights(t, t['url'])
        self.assertNotIn('<span class="ser-high-t"></span>', html_)
        self.assertNotIn('<p class="t-mono-s"></p>', html_)

    def test_the_date_line_needs_both_a_title_and_a_date(self):
        # contract 10.6: the date paragraph appears only when the day has a title and a date
        t, items = self.mixed()
        self.assertEqual(self.parts(items[0]), ([(['t-label'], 'Day 1'), (['ser-high-t'], 'Alpha')], ['MON, APR 22'], [W1]))
        self.assertEqual(self.parts(items[2]), ([(['t-label'], 'Day 3'), (['ser-high-t'], 'Charlie')], [], []))
        self.assertEqual([len(li.find_all('p', cls='t-mono-s')) for li in items], [1, 0, 0, 0, 0])
        # every highlight still lands on its day article
        main = self.doc(t).by_id('main')
        for a in main.by_id('highlights').find_all('a', cls='ser-high-a'):
            self.assertEqual(main.by_id(a['href'][1:]).tag, 'article')

    def test_day_text_is_escaped(self):
        # contract 5, Highlights: titles and excerpts are text (the hard rule: write-ups verbatim, never as markup here)
        days = journal_days()
        days[3]['title'] = 'Synthetic <b>pass</b> & col'
        days[3]['body'] = 'Synthetic write-up for a test with a <script> tag & an ampersand.'
        t = self.journal(slug='syn-j-escaped', days=days, lines=['journal_highlights: [004]'])
        sec = Doc(self.series.highlights(t, t['url'])).find('section')
        self.assertIsNone(sec.find('b'))
        self.assertIsNone(sec.find('script'))
        self.assertEqual(sec.find('span', cls='ser-high-t').text(), 'Synthetic <b>pass</b> & col')
        self.assertEqual(sec.find('p', cls='t-excerpt').text(), markdown.plain(days[3]['body'], 160))
        self.assertIn('<script', sec.find('p', cls='t-excerpt').text())
        self.assertIn(' & an ampersand.', sec.find('p', cls='t-excerpt').text())

    def test_highlights_sit_after_the_intro_and_before_the_day_log(self):
        # contract 5, Highlights: placed after the intro row and before the day log
        main = self.doc(self.t).by_id('main')
        intro, high, log = main.find('section', cls='ser-intro'), main.by_id('highlights'), main.by_id('days')
        self.assertIsNotNone(high, 'the page has no #highlights section')
        pos = positions(main, intro, high, log)
        self.assertEqual(pos, sorted(pos))
        self.assertEqual(len(main.find_all(attrs={'id': 'highlights'})), 1)
        # each highlight lands on a day article of this page
        for a in high.find_all('a', cls='ser-high-a'):
            self.assertEqual(main.by_id(a['href'][1:]).tag, 'article')


# ---------------------------------------------------------------- written_nav() and the day article

class WrittenNavTests(JournalPageFixture):

    def nav(self, d):
        html_ = self.series.written_nav(self.t, d, URL)
        return Doc(html_).root.elements()[0] if html_ else None

    def test_empty_for_a_track_only_day(self):
        # contract 5, Written-entry navigation: track-only days get none of this
        for d in (self.days[0], self.days[2], self.days[4]):
            self.assertEqual(d['body_md'], '')
            self.assertEqual(self.series.written_nav(self.t, d, URL), '')

    def test_links_the_nearest_written_days_skipping_track_only_ones(self):
        # contract 5, Written-entry navigation: the nearest written days before and after, labelled by day
        nav = self.nav(self.days[3])                       # Day 5.2: Day 3 before it and Day 6 after it are track only
        prev, nxt = nav.find('a', cls='ser-wnav-p'), nav.find('a', cls='ser-wnav-n')
        self.assertEqual((prev['href'], prev.text()), ('#day-2', 'Previous write-up: Day 2'))
        self.assertEqual((nxt['href'], nxt.text()), ('#day-12', 'Next write-up: Day 12'))
        self.assertEqual(prev['href'], '#' + self.series.day_anchor(self.days[1]))
        self.assertEqual(nxt['href'], '#' + self.series.day_anchor(self.days[5]))
        for a in (prev, nxt):
            self.assertIn('alink', a.classes)
        # the arrows point outward: before 'Previous', after 'Next'
        self.assertEqual(getattr(prev.children[0], 'tag', None), 'svg')
        self.assertEqual(getattr(nxt.children[-1], 'tag', None), 'svg')
        self.assertEqual(len(nav.find_all('a')), 2)

    def test_links_are_omitted_at_the_ends(self):
        # contract 5, Written-entry navigation: each omitted at the ends
        first, last = self.nav(self.days[1]), self.nav(self.days[5])
        self.assertIsNone(first.find('a', cls='ser-wnav-p'))
        self.assertIsNotNone(first.find('a', cls='ser-wnav-n'))
        self.assertNotIn('Previous write-up', first.text())
        self.assertIsNotNone(last.find('a', cls='ser-wnav-p'))
        self.assertIsNone(last.find('a', cls='ser-wnav-n'))
        self.assertNotIn('Next write-up', last.text())

    def test_the_only_written_day_keeps_the_copy_control_alone(self):
        # contract 5, Written-entry navigation: no neighbours to link, the copy-link control stays
        t = self.pct(slug='syn-j-one-written')
        html_ = self.series.written_nav(t, t['days'][0], t['url'])
        nav = Doc(html_).root.elements()[0]
        self.assertEqual(nav.find_all('a'), [])
        self.assertEqual(len(nav.find_all('button', cls='copy-btn')), 1)
        self.assertEqual(nav.find('button', cls='copy-btn').text(), 'Copy link to this entry, Day 1')

    def test_a_decimal_label_keeps_its_dash_anchor(self):
        # contract 5 / hard rules: `#day-<label>` with decimals as day-5-2, through day_anchor(), never a new conversion
        self.assertEqual(self.days[3]['label'], '5.2')
        self.assertEqual(self.series.day_anchor(self.days[3]), 'day-5-2')
        nxt = self.nav(self.days[1]).find('a', cls='ser-wnav-n')
        self.assertEqual((nxt['href'], nxt.text()), ('#day-5-2', 'Next write-up: Day 5.2'))
        prev = self.nav(self.days[5]).find('a', cls='ser-wnav-p')
        self.assertEqual((prev['href'], prev.text()), ('#day-5-2', 'Previous write-up: Day 5.2'))

    def test_copy_link_names_the_entry_anchor(self):
        # contract 5, Written-entry navigation + 10.1: core.copy_link(core.SITE_URL + t['url'] + '#' + day_anchor(d),
        # 'Copy link to this entry', cls='alink', of='Day <label>'), after the links
        for d in (self.days[1], self.days[3], self.days[5]):
            with self.subTest(day=d['label']):
                nav = self.nav(d)
                btn = nav.find('button', cls='copy-btn')
                self.assertEqual(btn['type'], 'button')
                self.assertEqual(btn.classes, ['alink', 'copy-btn'])
                self.assertTrue(btn['data-copy'].startswith(core.SITE_URL + self.t['url']), btn['data-copy'])
                self.assertTrue(btn['data-copy'].endswith('#' + self.series.day_anchor(d)), btn['data-copy'])
                self.assertEqual(btn['data-copy'], core.SITE_URL + self.t['url'] + '#' + self.series.day_anchor(d))
                # the visible label, then the day for assistive technology: the button ends <span class="sr">, Day N</span>
                spans = btn.find_all('span')
                self.assertEqual([(s.classes, s.text(clean=False)) for s in spans],
                                 [(['copy-l'], 'Copy link to this entry'), (['sr'], ', Day %s' % d['label'])])
                # phones with a share sheet: base.js renames it from data-share (phone-06)
                self.assertEqual(btn['data-share'], 'Share this entry')
                self.assertIs(btn.children[-1], spans[-1])
                self.assertEqual(btn.text(), 'Copy link to this entry, Day %s' % d['label'])
                self.assertEqual(nav.find('span', cls='copy-msg')['role'], 'status')
                self.assertIn('copy', nav.elements()[-1].classes)
                self.assertTrue(self.series.written_nav(self.t, d, URL).endswith(
                    core.copy_link(btn['data-copy'], 'Copy link to this entry', cls='alink', of='Day %s' % d['label'],
                                   share='Share this entry') + '</div>'))
        self.assertEqual(self.nav(self.days[3]).find('button')['data-copy'],
                         'https://esichak.github.io/personal-website/trips/syn-j-journal/#day-5-2')
        self.assertIn('<span class="copy-l">Copy link to this entry</span><span class="sr">, Day 5.2</span></button>',
                      self.series.written_nav(self.t, self.days[3], URL))

    def test_every_copy_control_on_the_page_has_its_own_name(self):
        # contract 10.1: `of` gives each control on a page its own accessible name (a page with several written days
        # repeated 'Copy link to this entry' once per entry)
        buttons = self.main.find_all('button', cls='copy-btn')
        names = [b.text() for b in buttons]
        self.assertEqual(names, ['Copy link', 'Copy link to this entry, Day 2', 'Copy link to this entry, Day 5.2',
                                 'Copy link to this entry, Day 12'])
        self.assertEqual(len(set(names)), len(names))
        for b in buttons:                                  # the name is the button's own text: nothing overrides it
            for attr in ('aria-label', 'aria-labelledby', 'title'):
                self.assertNotIn(attr, b)
        # and each entry's control sits inside the article it names
        for d in (self.days[1], self.days[3], self.days[5]):
            inside = self.main.by_id(self.series.day_anchor(d)).find_all('button', cls='copy-btn')
            self.assertEqual([b.text() for b in inside], ['Copy link to this entry, Day %s' % d['label']])

    def test_it_is_a_div_not_a_landmark(self):
        # contract 5, Written-entry navigation: <div class="ser-wnav">, a div, not a nav (one landmark per entry otherwise)
        nav = self.nav(self.days[3])
        self.assertEqual(nav.tag, 'div')
        self.assertEqual(nav.classes, ['ser-wnav'])
        self.assertNotIn('role', nav)
        self.assertEqual(nav.find_all('nav'), [])
        self.assertEqual(self.main.by_id('days').find_all('nav', cls='ser-wnav'), [])

    def test_a_written_day_article_ends_its_body_with_the_navigation(self):
        # contract 5, Written-entry navigation: every written day's .ser-body ends with it, after the write-up and its photos
        # (justified rows since Phase 11's report-18; a track-only day keeps the square sheet, below)
        body = self.main.by_id('day-2').find('div', cls='ser-body')
        self.assertEqual([el.classes[-1] for el in body.elements()], ['ser-wu', 'jrows', 'ser-wnav'])
        self.assertEqual(body.find('div', cls='ser-wu').text(), W1)             # the write-up, verbatim
        self.assertEqual(body.elements()[-1].find('button')['data-copy'], core.SITE_URL + URL + '#day-2')
        no_photos = self.main.by_id('day-5-2').find('div', cls='ser-body')
        self.assertEqual([el.classes[-1] for el in no_photos.elements()], ['ser-wu', 'ser-wnav'])
        for anchor in ('day-2', 'day-5-2', 'day-12'):
            self.assertEqual(len(self.main.by_id(anchor).find_all('div', cls='ser-wnav')), 1, anchor)

    def test_track_only_day_articles_have_no_navigation(self):
        # contract 5, Written-entry navigation: track-only days get none of this
        with_photos = self.main.by_id('day-1')
        self.assertEqual([el.classes[-1] for el in with_photos.find('div', cls='ser-body').elements()], ['ser-phs'])
        for anchor in ('day-1', 'day-3', 'day-6'):
            art = self.main.by_id(anchor)
            self.assertIsNone(art.find(cls='ser-wnav'), anchor)
            self.assertIsNone(art.find('button', cls='copy-btn'), anchor)
        self.assertIsNone(self.main.by_id('day-3').find('div', cls='ser-body'))

    def test_copy_controls_are_the_title_action_and_one_per_written_entry(self):
        # contract 4: on a series page the control is the last title action and sits under every written entry; the phone
        # share row belongs to single-day and goal pages
        urls = [b['data-copy'] for b in self.main.find_all('button', cls='copy-btn')]
        base = core.SITE_URL + URL
        self.assertEqual(urls, [base, base + '#day-2', base + '#day-5-2', base + '#day-12'])
        self.assertIsNone(self.main.find(cls='rep-share'))
        for ns in self.d.find_all('noscript'):
            self.assertIsNone(ns.find(cls='copy-btn'))


# ---------------------------------------------------------------- the cover hero, its preload and the share image

class HeroTests(JournalFixture):

    def hero(self, doc):
        return doc.by_id('hero')

    def test_hero_is_the_automatic_cover(self):
        # contract 5, Cover: <figure class="rep-hero" id="hero"> with core.cover_img(t, ..., eager=True) when t['cover']
        # exists; without cover_photo that is the first landscape day photo
        t = self.pct()
        self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), ('day', 'photos/d001-02.webp'))
        pg = self.page(t)
        fig = self.hero(Doc(pg.html).by_id('main'))
        self.assertIsNotNone(fig, 'the page has no #hero')
        self.assertEqual(fig.tag, 'figure')
        self.assertIn('rep-hero', fig.classes)
        self.assertIn(core.cover_img(t, URL, self.report.HERO_SIZES, eager=True), pg.html)
        img = fig.find('img')
        self.assertIn('cover-img', img.classes)
        self.assertEqual(img['src'], '../../trips/syn-j-journal/photos/d001-02.webp')
        self.assertEqual(img['alt'], 'Ridge view, day 1')
        self.assertEqual(img['fetchpriority'], 'high')
        self.assertNotIn('loading', img)
        self.assertEqual(fig.find('a')['href'], '../../trips/syn-j-journal/photos/d001-02.webp')   # opens the full photo

    def test_hero_follows_the_title_block_and_leads_the_page_images(self):
        # contract 5, Cover: the title block is followed by the hero (then the strip, the intro and the log)
        main = self.doc(self.pct()).by_id('main')
        fig = self.hero(main)
        pos = positions(main, main.by_id('title'), fig, main.by_id('stats'), main.by_id('map'), main.by_id('days'))
        self.assertEqual(pos, sorted(pos))
        self.assertIs(main.find('img'), fig.find('img'))
        self.assertEqual(len(main.find_all(attrs={'id': 'hero'})), 1)

    def test_an_explicit_cover_photo_wins(self):
        # contract 5, Cover: t['cover'] (the PCT's cover_photo from Phase 1) is the hero, the preload and the share image
        t = self.pct(cover_photo='photos/d002-02.webp')        # day 2's landscape, not the automatic pick (day 1's)
        self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), ('explicit', 'photos/d002-02.webp'))
        doc = self.doc(t)
        fig = self.hero(doc)
        self.assertEqual(fig.find('img')['src'], '../../trips/syn-j-journal/photos/d002-02.webp')
        self.assertEqual(fig.find('img')['alt'], 'Ridge view, day 2')
        self.assertEqual([el['href'] for el in image_preloads(doc)], ['../../trips/syn-j-journal/photos/d002-02.webp'])
        self.assertEqual(doc.find('meta', attrs={'property': 'og:image'})['content'], core.SITE_URL + URL + 'photos/d002-02.webp')

    def test_a_portrait_cover_does_not_lead_the_page_but_stays_the_share_image(self):
        # the lead frame is 4:3 to 2:1, so a portrait would lose most of itself: it keeps fronting the cards and the
        # share image, and the page opens without a lead photo
        t = self.pct(cover_photo='photos/d002-01.webp')
        self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), ('explicit', 'photos/d002-01.webp'))
        self.assertIsNone(self.report.lead_photo(t))
        doc = self.doc(t)
        self.assertIsNone(doc.by_id('hero'))
        self.assertEqual(doc.find_all('figure', cls='rep-hero'), [])
        self.assertEqual(image_preloads(doc), [])              # no cover preload (and no rendered overview in the fixture)
        self.assertEqual(doc.find('meta', attrs={'property': 'og:image'})['content'], core.SITE_URL + URL + 'photos/d002-01.webp')

    def test_og_image_is_the_chosen_cover_not_the_first_photo(self):
        # contract 10.4: the share image is the cover whenever the trip has one, whether or not that photo leads the page
        cases = (('later-landscape', 'photos/d003-02.webp', True),    # a later day's landscape, not the automatic pick (d001-02)
                 ('later-portrait', 'photos/d003-01.webp', False),    # a portrait: it fronts the cards, it does not lead the page
                 ('first-day-portrait', 'photos/d001-01.webp', False))
        for name, cover, leads in cases:
            with self.subTest(cover=cover):
                t = self.pct(slug=PREFIX + name, cover_photo=cover)
                first = t['days'][0]['photos'][0]['file']
                self.assertEqual(first, 'photos/d001-01.webp')
                self.assertEqual((t['cover']['source'], t['cover']['photo']['file']), ('explicit', cover))
                self.assertEqual(self.report.lead_photo(t) is not None, leads)
                doc = self.doc(t)
                og = doc.find('head').find_all('meta', attrs={'property': 'og:image'})
                self.assertEqual([m['content'] for m in og], [core.SITE_URL + t['url'] + cover])
                self.assertEqual(doc.by_id('hero') is not None, leads)
                if cover != first:
                    self.assertNotIn(first, og[0]['content'])

    def test_og_image_is_a_square_cover_that_does_not_lead(self):
        # contract 10.4 / 9: a square cover is below LEAD_MIN_AR, so the page has no lead photo; the share image is still it
        days = journal_days()
        days[1]['photos'] = [photo('photos/d002-01.webp', LANDSCAPE, alt='Synthetic camp'),
                             photo('photos/d002-02.webp', SQUARE, alt='Synthetic square')]
        t = self.journal(slug=PREFIX + 'square-cover', days=days, cover_photo='photos/d002-02.webp')
        self.assertEqual((t['cover']['photo']['w'], t['cover']['photo']['h']), SQUARE)
        self.assertIsNone(self.report.lead_photo(t))
        doc = self.doc(t)
        self.assertIsNone(doc.by_id('hero'))
        og = doc.find('head').find_all('meta', attrs={'property': 'og:image'})
        self.assertEqual([m['content'] for m in og], [core.SITE_URL + t['url'] + 'photos/d002-02.webp'])

    def test_cover_is_preloaded_in_the_head(self):
        # contract 5, Cover: preloaded (core.cover_preload(t, here, HERO_SIZES)), with the hero's own srcset and sizes
        t = self.journal()
        self.assertEqual(t['cover']['photo']['sm'], 'photos/d001-02.sm.webp')
        pg = self.page(t)
        doc = Doc(pg.html)
        head = pg.html[:pg.html.index('</head>')]
        self.assertIn(core.cover_preload(t, URL, self.report.HERO_SIZES), head)
        links = image_preloads(doc)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['href'], '../../trips/syn-j-journal/photos/d001-02.webp')
        self.assertEqual(links[0]['fetchpriority'], 'high')
        self.assertEqual(links[0]['imagesizes'], self.report.HERO_SIZES)
        img = self.hero(doc).find('img')
        self.assertEqual(links[0]['imagesrcset'], img['srcset'])
        self.assertEqual(links[0]['imagesizes'], img['sizes'])

    def test_cover_preload_replaces_the_overview_map_preloads(self):
        # contract 5, Cover: preloaded instead of the overview map; without a photo the overview renders keep their preloads
        maps = {'overview-tall': {'png': 'overview-tall.webp', 'w': 560, 'h': 860},
                'overview-phone': {'png': 'overview-phone.webp', 'w': 390, 'h': 600}}
        with mock.patch.object(core, 'render_meta', return_value={'maps': maps, 'charts': {}}):
            with_cover = self.doc(self.pct(slug='syn-j-with-photos'))
            without = self.doc(self.pct(slug='syn-j-without-photos', photos=False))
        self.assertEqual([el['href'] for el in image_preloads(with_cover)], ['../../trips/syn-j-with-photos/photos/d001-02.webp'])
        self.assertEqual(sorted(set(el['href'] for el in image_preloads(without))),
                         ['../../trips/syn-j-without-photos/map/overview-phone.webp', '../../trips/syn-j-without-photos/map/overview-tall.webp'])

    def test_no_hero_and_no_cover_preload_without_any_photo(self):
        # contract 5, Cover: only when t['cover'] exists; a journal without a photo keeps the page it had
        t = self.pct(photos=False)
        self.assertIsNone(t['cover'])
        doc = self.doc(t)
        main = doc.by_id('main')
        self.assertIsNone(self.hero(doc))
        self.assertIsNone(main.find(cls='rep-hero'))
        self.assertEqual(main.find_all('img'), [])
        self.assertEqual(image_preloads(doc), [])
        self.assertIsNone(doc.find('meta', attrs={'property': 'og:image'}))
        for anchor in ('title', 'stats', 'map', 'days', 'day-1'):
            self.assertIsNotNone(main.by_id(anchor), anchor)

    def test_og_image_is_the_cover(self):
        # contract 5, Cover / plan 12.4: the share image is the cover, an absolute URL, not merely the first photo
        t = self.pct()
        self.assertEqual(t['days'][0]['photos'][0]['file'], 'photos/d001-01.webp')   # the first photo is a portrait
        doc = self.doc(t)
        og = doc.find('head').find_all('meta', attrs={'property': 'og:image'})
        self.assertEqual([m['content'] for m in og], [core.SITE_URL + URL + t['cover']['photo']['file']])
        self.assertEqual(og[0]['content'], 'https://esichak.github.io/personal-website/trips/syn-j-journal/photos/d001-02.webp')


# ---------------------------------------------------------------- day_anchor(): one anchor per day, used by every link

class DayAnchorTests(JournalFixture):

    def setUp(self):
        super().setUp()
        self.t = self.journal(slug=PREFIX + 'anchors', days=anchor_days(), lines=['journal_highlights: [002, 004, 001]'])
        self.days = self.t['days']
        self.anchors = [self.series.day_anchor(d) for d in self.days]
        self.pg = self.page(self.t)
        self.main = Doc(self.pg.html).by_id('main')

    def test_day_anchor_of_a_number_a_decimal_and_any_other_label(self):
        # contract 10.6: 'day-' + the label with every run of characters outside A-Z a-z 0-9 replaced by '-', stripped of
        # leading and trailing '-'
        cases = (('31', 'day-31'), ('5.2', 'day-5-2'), ('5 (zero)', 'day-5-zero'),      # the contract's own three
                 ('Rest & <b>', 'day-Rest-b'), ('5..2', 'day-5-2'), ('(zero) 5', 'day-zero-5'), ('5_2', 'day-5-2'),
                 ('12a', 'day-12a'))
        for label, want in cases:
            with self.subTest(label=label):
                self.assertEqual(self.series.day_anchor(dict(self.days[0], label=label)), want)

    def test_loaded_days_keep_their_labels_and_get_these_anchors(self):
        # the label stays what the day file says (it is shown as 'Day <label>'); only the anchor is reduced to a safe token
        self.assertEqual([d['label'] for d in self.days], ['31', '5 (zero)', '5.2', 'Rest & <b>'])
        self.assertEqual(self.anchors, ['day-31', 'day-5-zero', 'day-5-2', 'day-Rest-b'])
        for anchor in self.anchors:
            self.assertRegex(anchor, r'\Aday-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\Z')

    def test_article_ids_are_the_anchors(self):
        # contract 10.6: the day's id on the journal page
        arts = self.main.find_all('article', cls='ser-day')
        self.assertEqual([a['id'] for a in arts], self.anchors)
        for art in arts:
            refs = art['aria-labelledby'].split()
            self.assertEqual(refs[0], art['id'] + '-n')
            for ref in refs:
                self.assertIsNotNone(art.by_id(ref), '%s is labelled by a missing #%s' % (art['id'], ref))

    def test_first_written_entry_action_uses_the_anchor(self):
        # contract 5, Actions: href="#<anchor of the first written day>", here Day 5 (zero)
        self.assertEqual(self.series.first_written(self.t)['label'], '5 (zero)')
        a = next((x for x in self.main.find(cls='rep-actions').find_all('a') if x.text() == 'Read the first written entry'), None)
        self.assertIsNotNone(a, 'no "Read the first written entry" action')
        self.assertEqual(a['href'], '#day-5-zero')

    def test_highlights_use_the_anchor(self):
        # contract 10.6: <a class="ser-high-a" href="#<anchor>">; the label itself stays as written, as text
        links = self.main.by_id('highlights').find_all('a', cls='ser-high-a')
        self.assertEqual([a['href'] for a in links], ['#day-5-zero', '#day-Rest-b', '#day-31'])
        self.assertEqual([a.find('span', cls='t-label').text() for a in links], ['Day 5 (zero)', 'Day Rest & <b>', 'Day 31'])

    def test_written_entry_navigation_uses_the_anchor(self):
        # contract 5, Written-entry navigation: href="#<day_anchor(prev)>" / "#<day_anchor(next)>"
        got = {}
        for d, anchor in zip(self.days, self.anchors):
            links = self.main.by_id(anchor).find_all('a', cls='ser-wnav-p') + self.main.by_id(anchor).find_all('a', cls='ser-wnav-n')
            got[d['id']] = [(a['href'], a.text()) for a in links]
        self.assertEqual(got, {
            '001': [],
            '002': [('#day-5-2', 'Next write-up: Day 5.2')],
            '003': [('#day-5-zero', 'Previous write-up: Day 5 (zero)'), ('#day-Rest-b', 'Next write-up: Day Rest & <b>')],
            '004': [('#day-5-2', 'Previous write-up: Day 5.2')],
        })

    def test_copy_link_urls_use_the_anchor(self):
        # contract 5 + 10.1: data-copy = the page URL + '#' + day_anchor(d); the control's name keeps the label, escaped
        base = core.SITE_URL + self.t['url']
        buttons = self.main.find_all('button', cls='copy-btn')
        self.assertEqual([b['data-copy'] for b in buttons], [base, base + '#day-5-zero', base + '#day-5-2', base + '#day-Rest-b'])
        for b in buttons:
            self.assertNotRegex(b['data-copy'], r'[\s<>"&()]')         # a URL that can be pasted anywhere
        self.assertEqual([b.text() for b in buttons[1:]], ['Copy link to this entry, Day 5 (zero)', 'Copy link to this entry, Day 5.2',
                                                           'Copy link to this entry, Day Rest & <b>'])
        self.assertIn('<span class="sr">, Day Rest &amp; &lt;b&gt;</span></button>', self.pg.html)

    def test_no_reference_to_a_day_carries_the_raw_label(self):
        # contract 10.6: the anchor is always safe in an attribute and a URL; a label that is not a number never reaches
        # an id, an href or the copied address as written
        ids = set(el['id'] for el in self.main.walk() if el['id'])
        seen = 0
        for el in self.main.walk():
            refs = [el['id'] or ''] + (el['aria-labelledby'] or '').split()
            refs += [(el[attr] or '').partition('#')[2] for attr in ('href', 'data-copy')]
            for ref in refs:
                if ref.startswith('day-'):
                    seen += 1
                    self.assertRegex(ref, r'\Aday-[A-Za-z0-9-]+\Z', '%r on %r' % (ref, el))
                    self.assertIn(ref, ids, 'nothing on the page has id %r' % ref)
        self.assertGreater(seen, 20)                       # 4 articles with their label ids, plus every link to them
        self.assertEqual(self.main.find_all('b'), [])      # 'Rest & <b>' is text wherever it is shown
        for raw in ('day-5 (zero)', 'day-5.2"', 'day-Rest &', 'day-Rest%20'):
            self.assertNotIn(raw, self.pg.html)


# ---------------------------------------------------------------- a journal whose day files carry no dates

class UndatedJournalTests(JournalFixture):

    REST = ' '.join([ORGANISED, 'The one day with a write-up carries its notes and any photos; the other 2 show the track only.',
                     EVERY_TRACK])

    def undated(self, name, **meta):
        """Three undated days and no date in index.md either, so the journal has no date range to print."""
        t = self.journal(slug=PREFIX + name, days=undated_days(), date=None, end_date=None, **meta)
        self.assertEqual((t['date'], t['end_date']), (None, None))
        self.assertEqual([d['date'] for d in t['days']], [None, None, None])
        self.assertEqual(core.frange(t['date'], t['end_date']), '')
        return t

    def lede_text(self, t):
        return Doc(self.series.lede(t)).find('p', cls='ser-lede').text()

    def test_map_caption_has_no_as_recorded_item(self):
        # contract 10.5: a journal without any date: no 'As recorded' item at all; the items are 'Full tracks, not
        # trimmed', 'North up', then the credit
        t = self.undated('undated')
        credit = caption_items(Doc(core.map_caption([])))
        self.assertEqual(len(credit), 3)
        want = ['Full tracks, not trimmed', 'North up'] + credit
        self.assertEqual(caption_items(Doc(self.series.map_caption(t))), want)
        self.assertEqual(self.series.map_caption(t), core.map_caption(['Full tracks, not trimmed', 'North up']))
        main = self.doc(t).by_id('main')
        self.assertEqual(caption_items(main.by_id('map').find(cls='mapcap')), want)
        self.assertNotIn('As recorded', main.text())
        # the full-screen map page carries the same caption
        full = Doc(self.series.fullscreen(t).html)
        self.assertEqual(caption_items(full.find(cls='mapcap'))[:2], ['Full tracks, not trimmed', 'North up'])
        self.assertNotIn('As recorded', full.text())

    def test_facts_sentence_leaves_the_dates_out_with_a_place(self):
        # contract 10.5: '<title>: N recorded day(s)[, <date range>][, <place>].' with absent parts left out
        text = self.lede_text(self.undated('undated-place'))
        self.assertEqual(text, 'Synthetic Journal: 3 recorded days, Start to Finish. ' + self.REST)
        self.assertNotRegex(text, r',\s*[,.]|\s[,.]')

    def test_facts_sentence_leaves_the_dates_out_without_a_place(self):
        # contract 10.5: neither a range nor a place: the sentence ends at the count
        text = self.lede_text(self.undated('undated-no-place', place=None))
        self.assertEqual(text, 'Synthetic Journal: 3 recorded days. ' + self.REST)
        self.assertNotRegex(text, r',\s*[,.]|\s[,.]')
        one = self.journal(slug=PREFIX + 'undated-one-day', days=[{'id': '001'}], date=None, end_date=None, place=None)
        self.assertEqual(self.lede_text(one), 'Synthetic Journal: 1 recorded day. %s %s' % (ORGANISED, EVERY_TRACK))

    def test_meta_description_leaves_the_dates_out(self):
        # contract 10.5: '<title>: N recorded days[, <range>], with a GPX track for every day[ and N written up].'
        for name, place in (('undated-place', 'Start to Finish'), ('undated-no-place', None)):
            with self.subTest(place=place):
                doc = self.doc(self.undated(name, place=place))
                desc = doc.find('meta', attrs={'name': 'description'})['content']
                self.assertEqual(desc, 'Synthetic Journal: 3 recorded days, with a GPX track for every day and 1 written up.')
                self.assertNotRegex(desc, r',\s*[,.]|\s[,.]')
                self.assertEqual(doc.find('meta', attrs={'property': 'og:description'})['content'], desc)

    def description(self, t):
        """The page's meta description; og:description is the same text."""
        doc = self.doc(t)
        desc = doc.find('meta', attrs={'name': 'description'})['content']
        self.assertEqual(doc.find('meta', attrs={'property': 'og:description'})['content'], desc)
        self.assertNotRegex(desc, r',\s*[,.]|\s[,.]|\band\s*\.')
        return desc

    def test_meta_description_of_a_dated_journal_keeps_the_range(self):
        # contract 10.5: the same sentence with its range, with and without written days. Phase 4 (2026-10-10): the GPX
        # phrase counts the days that have a track, and neither fixture has one on every day (the six-day journal's
        # day 3 and helpers.make_series' third day are recorded without a GPX), so it reads 'for N of them'
        t = self.journal()
        self.assertEqual([bool(d['track']) for d in t['days']], [True, True, False, True, True, True])
        self.assertEqual(self.description(t),
                         'Synthetic Journal: 6 recorded days, Apr 22 – May 2, 2024, with a GPX track for 5 of them and 3 written up.')
        t = self.pct(slug=PREFIX + 'none-written', written_day=None)
        self.assertEqual([bool(d['track']) for d in t['days']], [True, True, False])
        self.assertEqual(self.description(t), 'Pacific Crest Trail 2024: 3 recorded days, Apr 22 – Sep 21, 2024, with a GPX track for 2 of them.')

    def test_meta_description_of_a_journal_whose_every_day_has_a_track_is_word_for_word_what_it_was(self):
        # the real shape (every day of the real journal has its GPX): 'with a GPX track for every day', with ' and N
        # written up' when days are written, exactly as before the phrase learned to count
        t = self.pct(slug=PREFIX + 'all-tracks', tracks=(True, True, True))
        self.assertEqual([bool(d['track']) for d in t['days']], [True, True, True])
        self.assertEqual(self.description(t),
                         'Pacific Crest Trail 2024: 3 recorded days, Apr 22 – Sep 21, 2024, with a GPX track for every day and 1 written up.')
        t = self.pct(slug=PREFIX + 'all-tracks-none-written', tracks=(True, True, True), written_day=None)
        self.assertEqual(self.description(t), 'Pacific Crest Trail 2024: 3 recorded days, Apr 22 – Sep 21, 2024, with a GPX track for every day.')
        days = journal_days()
        days[2]['track'] = True                              # the six-day journal with its one missing GPX put back
        t = self.journal(slug=PREFIX + 'six-tracks', days=days)
        self.assertEqual(self.description(t),
                         'Synthetic Journal: 6 recorded days, Apr 22 – May 2, 2024, with a GPX track for every day and 3 written up.')
        one = self.journal(slug=PREFIX + 'one-day', days=[{'id': '001', 'date': '2024-04-22', 'body': W1}], end_date='2024-04-22')
        self.assertEqual(self.description(one), 'Synthetic Journal: 1 recorded day, Apr 22, 2024, with a GPX track for every day and 1 written up.')

    def test_meta_description_says_for_how_many_days_there_is_a_track(self):
        # Phase 4 (2026-10-10): 'for every day' only when every day has a track; with some, 'for N of them'; with none
        # the phrase is left out. 'N written up' is joined with ' and ' when both are there and stands alone otherwise
        head = 'Pacific Crest Trail 2024: 3 recorded days, Apr 22 – Sep 21, 2024'
        cases = [
            ('every-written', (True, True, True), 1, head + ', with a GPX track for every day and 1 written up.'),
            ('every-bare', (True, True, True), None, head + ', with a GPX track for every day.'),
            ('two-written', (True, True, False), 1, head + ', with a GPX track for 2 of them and 1 written up.'),
            ('two-bare', (True, True, False), None, head + ', with a GPX track for 2 of them.'),
            ('one-written', (False, True, False), 2, head + ', with a GPX track for 1 of them and 1 written up.'),
            ('one-bare', (False, False, True), None, head + ', with a GPX track for 1 of them.'),
            ('none-written', (False, False, False), 3, head + ', 1 written up.'),
            ('none-bare', (False, False, False), None, head + '.'),
        ]
        for name, tracks, written_day, want in cases:
            with self.subTest(name):
                t = self.pct(slug=PREFIX + 'gpx-' + name, tracks=tracks, written_day=written_day)
                self.assertEqual([bool(d['track']) for d in t['days']], list(tracks))
                desc = self.description(t)
                self.assertEqual(desc, want)
                self.assertEqual('every day' in desc, all(tracks))
                self.assertEqual('GPX' in desc, any(tracks))
                self.assertEqual('of them' in desc, any(tracks) and not all(tracks))

    def test_meta_description_counts_the_written_days_whatever_the_tracks(self):
        # several written days, some without a track; and a journal with no dates, no tracks and nothing written, whose
        # description is the count alone
        days = journal_days()
        for d in days[:4]:
            d['track'] = False
        t = self.journal(slug=PREFIX + 'two-of-six', days=days)
        self.assertEqual(self.description(t),
                         'Synthetic Journal: 6 recorded days, Apr 22 – May 2, 2024, with a GPX track for 2 of them and 3 written up.')
        for d in days:
            d['track'] = False
        t = self.journal(slug=PREFIX + 'none-of-six', days=days)
        self.assertEqual(self.description(t), 'Synthetic Journal: 6 recorded days, Apr 22 – May 2, 2024, 3 written up.')
        bare = self.journal(slug=PREFIX + 'undated-bare', date=None, end_date=None,
                            days=[{'id': '001', 'track': False}, {'id': '002', 'track': False}])
        self.assertEqual(self.description(bare), 'Synthetic Journal: 2 recorded days.')
        some = self.journal(slug=PREFIX + 'undated-some', date=None, end_date=None, days=[{'id': '001'}, {'id': '002', 'track': False}])
        self.assertEqual(self.description(some), 'Synthetic Journal: 2 recorded days, with a GPX track for 1 of them.')
        lone = self.journal(slug=PREFIX + 'undated-lone', date=None, end_date=None, days=[{'id': '001', 'track': False}])
        self.assertEqual(self.description(lone), 'Synthetic Journal: 1 recorded day.')

    def test_the_page_still_lists_every_undated_day(self):
        # hard rules: every anchor kept; a day without a date keeps its article and its id, and every in-page link lands
        doc = self.doc(self.undated('undated'))
        main = doc.by_id('main')
        self.assertEqual([a['id'] for a in main.find_all('article', cls='ser-day')], ['day-1', 'day-2', 'day-3'])
        ids = set(el['id'] for el in doc.root.walk() if el['id'])
        hrefs = [a['href'] for a in doc.find_all('a') if (a['href'] or '').startswith('#')]
        self.assertIn('#day-1', hrefs)                     # 'Read the first written entry'
        for href in hrefs:
            self.assertIn(href[1:], ids, 'dead link %s' % href)


# ---------------------------------------------------------------- write-ups verbatim (a hard rule of the site)

class VerbatimTests(JournalFixture):

    def setUp(self):
        super().setUp()
        days = journal_days()
        days[3]['body'] = RICH                             # Day 5.2
        self.t = self.journal(slug=PREFIX + 'verbatim', days=days, body=SERIES_RICH)
        self.day = self.t['days'][3]
        self.pg = self.page(self.t)
        self.main = Doc(self.pg.html).by_id('main')

    def test_fixture_write_ups_exercise_the_renderer(self):
        # the comparisons below are only as good as the write-ups: both must reach the page unchanged by the loader, be
        # longer than any excerpt, and render differently with and without the day's heading shift
        self.assertEqual(self.day['body_md'], RICH)
        self.assertEqual(self.t['body_md'], SERIES_RICH)
        self.assertGreater(len(RICH), 800)
        self.assertGreater(len(SERIES_RICH), 600)
        self.assertNotEqual(markdown.to_html(RICH, heading_shift=4), markdown.to_html(RICH))
        for html_ in (markdown.to_html(RICH, heading_shift=4), markdown.to_html(SERIES_RICH)):
            self.assertNotIn('<div', html_)                # inner_html() reads up to the next </div>

    def test_a_day_write_up_is_the_markdown_renderers_output_unchanged(self):
        # hard rule: write-ups verbatim. The entry holds exactly markdown.to_html(body, heading_shift=4): not its plain
        # text, not an excerpt, and with the headings shifted under the day's own h4
        got = inner_html(article_html(self.pg.html, 'day-5-2'), 'ser-wu')
        self.assertEqual(got, markdown.to_html(RICH, heading_shift=4))
        self.assertEqual(got, markdown.to_html(self.day['body_md'], heading_shift=4))
        self.assertTrue(got.endswith(LAST_WORDS + '</p>'), got[-120:])

    def test_a_day_write_up_keeps_its_paragraphs_heading_emphasis_link_and_list(self):
        # the same rule, in terms a reader would notice
        wu = self.main.by_id('day-5-2').find('div', cls='ser-wu')
        self.assertIn('prose', wu.classes)                 # set as running text, like a report's write-up
        self.assertEqual([el.tag for el in wu.elements()], ['p', 'h5', 'p', 'ul', 'p'])
        self.assertEqual(len(wu.find_all('p')), 3)
        # the write-up's one heading, '##', is its top level: one under the day's h4 (it was h6 before Phase 8: a gap)
        self.assertEqual(wu.find('h5').text(), 'Synthetic heading')
        for tag in ('h1', 'h2', 'h3', 'h4', 'h6'):
            self.assertEqual(wu.find_all(tag), [], tag)
        link = wu.find('a')
        self.assertEqual((link['href'], link.text()), ('https://example.com/synthetic?a=1&b=2', 'synthetic link'))
        self.assertEqual([li.text() for li in wu.find_all('li')],
                         ['Synthetic list item one', 'Synthetic list item two, with emphasis', 'Synthetic list item three'])
        self.assertEqual([el.text() for el in wu.find_all('em')], ['emphasis', 'emphasis'])
        self.assertEqual([el.text() for el in wu.find_all('strong')], ['strong words'])
        self.assertEqual(len(wu.find_all('br')), 1)        # the line break inside the first paragraph
        self.assertEqual(wu.find_all('tag'), [])           # '<tag>' is text
        self.assertIn('an ampersand & a <tag> that must stay text.', wu.text())
        self.assertTrue(wu.text().endswith(LAST_WORDS), wu.text()[-80:])
        self.assertNotIn('##', wu.text())
        self.assertNotIn('**', wu.text())

    def test_every_written_day_holds_its_own_write_up_and_no_other_day_does(self):
        # hard rule: write-ups verbatim, for each written entry of the page
        for d in self.t['days']:
            with self.subTest(day=d['label']):
                art = article_html(self.pg.html, self.series.day_anchor(d))
                if d['body_md']:
                    self.assertEqual(inner_html(art, 'ser-wu'), markdown.to_html(d['body_md'], heading_shift=4))
                    self.assertEqual(art.count('ser-wu'), 1)
                else:
                    self.assertNotIn('ser-wu', art)
        self.assertEqual(self.pg.html.count(LAST_WORDS), 1)   # the entry is on the page once, whole (no highlight lists it)

    def test_the_journal_write_up_is_the_markdown_renderers_output_unchanged(self):
        # hard rule: write-ups verbatim. The journal's own index.md body is exactly markdown.to_html(body), headings
        # at the report pages' default shift
        lede = self.series.lede(self.t)
        m = re.match(r'\A<div\b[^>]*>(.*)</div>\Z', lede, re.S)
        self.assertIsNotNone(m, 'lede() is not one wrapping <div>: %r' % lede[:120])
        self.assertEqual(m.group(1), markdown.to_html(SERIES_RICH))
        self.assertEqual(m.group(1), markdown.to_html(self.t['body_md']))
        self.assertIn('prose', Doc(lede).root.elements()[0].classes)
        self.assertIn(lede, self.pg.html)                  # and that is what the page's introduction carries
        self.assertEqual(self.pg.html.count(SERIES_LAST_WORDS), 1)

    def test_the_journal_write_up_keeps_its_paragraphs_heading_link_and_list(self):
        intro = self.main.find(cls='ser-intro-t')
        prose = next((el for el in intro.find_all('div') if 'prose' in el.classes), None)
        self.assertIsNotNone(prose, 'the introduction has no prose block')
        self.assertEqual([el.tag for el in prose.elements()], ['p', 'h3', 'p', 'ol', 'p'])
        self.assertEqual(len(prose.find_all('p')), 3)
        # '##' is the write-up's top level: h3 at the default shift of 2 (h4 before Phase 8)
        self.assertEqual(prose.find('h3').text(), 'Synthetic journal heading')
        self.assertEqual(prose.find_all('h6'), [])
        link = prose.find('a')
        self.assertEqual((link['href'], link.text()), ('https://example.com/journal', 'journal link'))
        self.assertEqual([li.text() for li in prose.find_all('li')], ['Synthetic numbered item one', 'Synthetic numbered item two'])
        self.assertEqual([el.text() for el in prose.find_all('strong')], ['strong words'])
        self.assertTrue(prose.text().endswith(SERIES_LAST_WORDS), prose.text()[-80:])
        # the write-up stands in for the factual introduction; no day's words are in it
        self.assertIsNone(intro.find('p', cls='ser-lede'))
        self.assertNotIn(ORGANISED, intro.text())
        self.assertNotIn(LAST_WORDS, intro.text())


# ---------------------------------------------------------------- reader mode: the write-ups toggle

class ToggleTests(JournalPageFixture):

    def test_toggle_keeps_its_markup_and_carries_the_default(self):
        # contract 5, Reader mode: the toggle keeps its markup plus data-default="wu" on the input
        box = self.main.find('div', cls='ser-only')
        self.assertIsNotNone(box, 'the day log has no write-ups toggle')
        self.assertIn('hidden', box)                       # shown by series.js: without JavaScript every day shows
        self.assertIs(self.main.by_id('days').find('div', cls='ser-only'), box)   # in the day log's head, as before
        inp = box.find('input')
        self.assertEqual((inp['id'], inp['type']), ('ser-only', 'checkbox'))
        # the script sets the box; a browser must not refill it afterwards on Back / Forward (review gate, round 5)
        self.assertEqual(inp['autocomplete'], 'off')
        self.assertEqual((inp['data-total'], inp['data-wu']), ('6', '3'))
        self.assertEqual(inp['data-default'], 'wu')
        self.assertNotIn('checked', inp)
        self.assertIs(inp.parent, box.find('label', cls='ser-only-l'))
        self.assertEqual(box.find('span', cls='ser-only-long').text(), 'Show days with write-ups only')
        self.assertEqual(box.find('span', cls='ser-only-short').text(), 'Write-ups only')
        self.assertEqual(len(self.d.find_all(attrs={'id': 'ser-only'})), 1)
        live = self.main.by_id('ser-live')
        self.assertEqual((live['aria-live'], live.text()), ('polite', ''))

    def test_toggle_is_absent_when_every_day_or_no_day_is_written(self):
        # contract 5, Reader mode: series.py sets it whenever the toggle is rendered (only when some days are written)
        every = [dict(d, body='Synthetic write-up for a test, day %s.' % d['day']) for d in journal_days()]
        none = [dict(d, body='') for d in journal_days()]
        for slug, days in (('syn-j-every-day-written', every), ('syn-j-no-day-written', none)):
            with self.subTest(slug=slug):
                main = self.doc(self.journal(slug=slug, days=days)).by_id('main')
                self.assertIsNone(main.by_id('ser-only'))
                self.assertIsNone(main.find(cls='ser-only'))
                self.assertEqual(main.find_all(attrs={'data-default': 'wu'}), [])
                self.assertEqual(len(main.find_all('article', cls='ser-day')), 6)

    def test_filter_classes_mark_what_the_reader_mode_hides(self):
        # contract 5, Reader mode: the filter hides a track-only day and a month without write-ups (series.js reads
        # .ser-day:not(.has-wu) and .ser-month:not(.has-wu))
        days = journal_days() + [{'id': '007', 'day': '40', 'title': 'Foxtrot', 'date': '2024-06-03'}]
        main = self.doc(self.journal(slug='syn-j-three-months', days=days, end_date='2024-06-03')).by_id('main')
        written = [a['id'] for a in main.find_all('article', cls='ser-day') if 'has-wu' in a.classes]
        self.assertEqual(written, ['day-2', 'day-5-2', 'day-12'])
        months = {s['id']: 'has-wu' in s.classes for s in main.find_all('section', cls='ser-month')}
        self.assertEqual(months, {'month-2024-04': True, 'month-2024-05': True, 'month-2024-06': False})


# ---------------------------------------------------------------- what must not change

class UnchangedTests(JournalPageFixture):

    def test_day_article_ids_are_unchanged(self):
        # contract 5 / hard rules: every anchor kept: #day-<label>, decimals as day-5-2
        arts = self.main.find_all('article', cls='ser-day')
        self.assertEqual([a['id'] for a in arts], ['day-1', 'day-2', 'day-3', 'day-5-2', 'day-6', 'day-12'])
        self.assertEqual([a['id'] for a in arts], [self.series.day_anchor(d) for d in self.days])
        for a in arts:
            for ref in a['aria-labelledby'].split():
                self.assertIsNotNone(a.by_id(ref), '%s is labelled by a missing #%s' % (a['id'], ref))

    def test_month_section_ids_are_unchanged(self):
        # contract 5 / hard rules: #month-YYYY-MM kept; the month nav and the month index still point at them
        self.assertEqual([s['id'] for s in self.main.find_all('section', cls='ser-month')], ['month-2024-04', 'month-2024-05'])
        nav = self.main.find('nav', cls='ser-mnav')
        self.assertEqual(nav['aria-label'], 'Months')
        self.assertEqual([(a['href'], a['data-wu']) for a in nav.find_all('a')], [('#month-2024-04', '2'), ('#month-2024-05', '1')])
        index = self.main.find('ol', cls='ser-mi')
        self.assertEqual([a['href'] for a in index.find_all('a')], ['#month-2024-04', '#month-2024-05'])

    def test_gpx_hrefs_and_download_names_are_unchanged(self):
        # contract 5 / hard rules: every GPX download unchanged: the file is named by the day file, the saved name by the label
        got = {}
        for d in self.days:
            a = self.main.by_id(self.series.day_anchor(d)).find('a', cls='ser-gpx')
            got[d['id']] = (a['href'], a['download']) if a else None
            if a:
                self.assertEqual(a['href'], 'gpx/%s-day-%s.gpx' % (self.t['slug'], d['id']))
                self.assertEqual(a['download'], self.series.gpx_name(self.t, d))
                self.assertEqual(a['aria-label'], 'Download Day %s GPX' % d['label'])
        self.assertEqual(got, {
            '001': ('gpx/syn-j-journal-day-001.gpx', 'syn-j-journal-day-1.gpx'),
            '002': ('gpx/syn-j-journal-day-002.gpx', 'syn-j-journal-day-2.gpx'),
            '003': None,                                    # no recording, no download link
            '004': ('gpx/syn-j-journal-day-004.gpx', 'syn-j-journal-day-5-2.gpx'),
            '005': ('gpx/syn-j-journal-day-005.gpx', 'syn-j-journal-day-6.gpx'),
            '006': ('gpx/syn-j-journal-day-006.gpx', 'syn-j-journal-day-12.gpx'),
        })
        self.assertEqual(len([a for a in self.main.find_all('a') if 'download' in a]), 5)   # one per recording, no 'all' link

    def test_map_caption_says_as_recorded_with_the_date_range(self):
        # plan 9.3 / contract 5: the overview map's caption reads 'As recorded <date range>', never implying current conditions
        want = 'As recorded ' + core.frange(self.t['date'], self.t['end_date'])
        self.assertEqual(want, 'As recorded Apr 22 – May 2, 2024')
        cap = self.main.by_id('map').find(cls='mapcap')
        first = cap.find('span', cls='mi')
        self.assertEqual(first.text(), want)
        self.assertNotIn('Tracks:', cap.text())
        self.assertEqual(Doc(self.series.map_caption(self.t)).find('span', cls='mi').text(), want)
        # contract 10.5: the date item, 'Full tracks, not trimmed', 'North up', then the credit
        credit = caption_items(Doc(core.map_caption([])))
        self.assertEqual(len(credit), 3)
        self.assertEqual(caption_items(cap), [want, 'Full tracks, not trimmed', 'North up'] + credit)

    def test_body_class_stays_p_series(self):
        # contract 5: the series page's <body class> stays p-series
        self.assertEqual(self.d.find('body')['class'], 'p-series')

    def test_no_related_block_on_a_series_page(self):
        # contract 3: related reports show on single-day and multi-day pages, not on series pages
        helpers.make_trip(self.tmp, 'syn-j-neighbour', title='Synthetic Neighbour', activity='hike', date='2024-06-01',
                          region='Synthetic Range', body=SERIES_BODY, track=True)
        other = helpers.load(self.tmp, 'syn-j-neighbour')
        site = helpers.make_site([self.t, other])
        self.assertEqual(helpers.slugs(core.related(self.t, site)), ['syn-j-neighbour'])   # there is a candidate
        html_ = self.series.page(self.t, site).html
        main = Doc(html_).by_id('main')
        self.assertIsNone(main.find(cls='rep-related'))
        self.assertIsNone(main.by_id('rel-h'))
        self.assertNotIn('More like this', main.text())
        self.assertIsNotNone(main.find('nav', cls='pager'))   # the newer / older pager stays

    def test_tick_list_backlink_follows_the_title_block(self):
        # contract 5: report.tick_backlink(t, here, site) follows the title block (before the hero)
        helpers.make_trip(self.tmp, 'syn-j-goal', title='Synthetic Goal', activity='hike', kind='planned')
        goal = helpers.load(self.tmp, 'syn-j-goal')
        site = helpers.make_site([self.t, goal])
        site['goal_backlinks'] = {SLUG: [goal]}
        main = Doc(self.series.page(self.t, site).html).by_id('main')
        line = next((p for p in main.find_all('p') if 'On the tick list' in p.text()), None)
        self.assertIsNotNone(line, 'the series page has no "On the tick list" line')
        a = line.find('a')
        self.assertEqual((a['href'], a.text()), ('../../trips/syn-j-goal/', 'Synthetic Goal'))
        pos = positions(main, main.by_id('title'), line, main.by_id('hero'), main.by_id('stats'))
        self.assertEqual(pos, sorted(pos))
        # a journal no goal names has no line
        self.assertNotIn('On the tick list', self.main.text())
        site['goal_backlinks'] = {'syn-j-another-report': [goal]}
        self.assertNotIn('On the tick list', self.series.page(self.t, site).html)

    def test_page_url_canonical_and_build_output_are_unchanged(self):
        # hard rules: every URL unchanged, no duplicate canonical day pages: one page at the trip's url plus its map page
        self.assertEqual(self.t['url'], 'trips/syn-j-journal/')
        self.assertEqual(self.pg.url, self.t['url'])
        self.assertEqual(self.pg.title, 'Synthetic Journal')
        canon = self.d.find('head').find_all('link', attrs={'rel': 'canonical'})
        self.assertEqual([el['href'] for el in canon], [core.SITE_URL + self.t['url']])
        built = self.series.build(self.site)
        self.assertEqual([p.url for p in built], ['trips/syn-j-journal/', 'trips/syn-j-journal/map/'])
        self.assertEqual(built[0].html, self.pg.html)

    def test_legacy_anchors_are_all_present_once(self):
        # hard rules: every anchor kept (#title, #stats, #map, PCT #days, #month-YYYY-MM, #day-<label>)
        t = self.journal(slug='syn-j-with-highlights', lines=['journal_highlights: [004, 003]'])
        doc = self.doc(t)
        ids = [el['id'] for el in doc.root.walk() if el['id']]
        for anchor in ('main', 'title', 'hero', 'stats', 'map', 'highlights', 'days', 'month-2024-04', 'month-2024-05',
                       'day-1', 'day-2', 'day-3', 'day-5-2', 'day-6', 'day-12'):
            self.assertEqual(ids.count(anchor), 1, '#%s appears %d times' % (anchor, ids.count(anchor)))
        self.assertEqual(sorted(set(i for i in ids if ids.count(i) > 1)), [])

    def test_every_hash_link_lands_on_the_page(self):
        # plan 9.1: no navigation link points at an omitted section (actions, highlights, month links, entry navigation)
        t = self.journal(slug='syn-j-with-highlights', lines=['journal_highlights: [004, 003]'])
        doc = self.doc(t)
        ids = set(el['id'] for el in doc.root.walk() if el['id'])
        hrefs = [a['href'] for a in doc.find_all('a') if (a['href'] or '').startswith('#')]
        self.assertIn('#day-5-2', hrefs)
        self.assertIn('#days', hrefs)
        self.assertIn('#month-2024-05', hrefs)
        for href in hrefs:
            self.assertIn(href[1:], ids, 'dead link %s' % href)


if __name__ == '__main__':
    unittest.main()
