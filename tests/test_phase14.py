"""Phase 14 (plan 2, section 14): titles, descriptions, head metadata and the crumbs' structured data.

- seo-01: core.page_title, '{title} · {activity}, {place or region}[, {short date}] · Eric Sichak', a place or region
  already named by the title passed over.
- seo-02: core.describe, the factual summary whole when the facts lead, a write-up cut at a sentence end from 80 to 160
  characters when it leads.
- seo-03: og:site_name and og:locale on every page; article:author, article:section and article:tag on a report.
- seo-06: core.crumbs, the visible crumbs and their BreadcrumbList from one list, on every crumbed page.
- perf-01: the bundles' addresses carry their hash (build.asset_hash) during a build, and only then.
- perf-02: tools/fonts.py (with a fake download) and the head of a page whose fonts are the site's own.
- perf-07, perf-14: the Ski page preloads its first panel map; a small slot lists a photo's .th copy first.
- seo-09: the feed carries a trip's whole write-up, its photos and its links as <content:encoded>.
- phone-16, seo-12: the home-screen icon on every page; the verification tags written only when set.
Synthetic trips only (helpers.make_trip); the built pages are tests/test_a11y_static.py's fixture site.
"""
import importlib
import json
import os
import tempfile
import unittest
from unittest import mock
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import helpers
from helpers import Doc

import test_a11y_static as a11y
from sitegen import core

tearDownModule = helpers.no_region_pages_left

STATS = {'distance_km': 12.0, 'gain_m': 900, 'high_m': 2900}
SENT = 'Synthetic first sentence of a write-up.'                 # 39 characters
LONG = ' '.join(['Synthetic words run on without a stop'] * 8)        # no sentence end at all


class Fixture(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        mk = lambda slug, **kw: helpers.make_trip(tmp.name, slug, **kw)  # noqa: E731
        mk('syn-p-place', title='Synthetic Ridge Tour', activity='ski', date='2026-01-10', place='Synthetic Basin',
           region='Synthetic Range', stats=STATS, map={'peaks': ['Synthetic Peak', 'synthetic peak', 'Synthetic Dome']})
        mk('syn-p-named', title='Synthetic Basin Loop', activity='hike', date='2025-06-01', place='Synthetic Basin',
           region='Synthetic Range', stats=STATS)
        mk('syn-p-both', title='Synthetic Basin, Synthetic Range', activity='hike', date='2025-06-02', place='Synthetic Basin',
           region='Synthetic Range', stats=STATS)
        mk('syn-p-region', title='Synthetic Lap', activity='mtb', date='2025-07-01', region='Synthetic Coast', stats=STATS)
        mk('syn-p-fits', title='Synthetic Short', activity='hike', date='2025-05-01', region='Synthetic Range',
           body=SENT + ' ' + SENT)
        mk('syn-p-long', title='Synthetic Long', activity='hike', date='2025-05-02', region='Synthetic Range', body=LONG)
        mk('syn-p-short-first', title='Synthetic Short First', activity='hike', date='2025-05-04', region='Synthetic Range',
           body='Synthetic opening sentence of some length here.  ' + LONG)
        mk('syn-p-story', title='Synthetic Story', activity='hike', date='2025-05-03', region='Synthetic Range',
           body='Synthetic opening words. ' + ' '.join(['Synthetic sentence number %d of the story.' % i for i in range(8)]))
        mk('syn-p-tour', title='Synthetic Tour', activity='ski', kind='multi-day', date='2026-03-10', end_date='2026-03-11',
           region='Synthetic Range', days=[{'date': '2026-03-10', 'body': SENT}, {'date': '2026-03-11'}])
        self.by = {t['slug']: t for t in helpers.load_dir(tmp.name)}


class TitleTests(Fixture):

    def test_the_activity_and_the_place_follow_the_title(self):
        self.assertEqual(core.page_title(self.by['syn-p-place']),
                         'Synthetic Ridge Tour · Backcountry Skiing, Synthetic Basin · Eric Sichak')
        self.assertEqual(core.page_title(self.by['syn-p-region']), 'Synthetic Lap · Mountain Biking, Synthetic Coast · Eric Sichak')

    def test_a_place_the_title_names_gives_way_to_the_region_and_both_named_keep_the_old_form(self):
        self.assertEqual(core.page_title(self.by['syn-p-named']), 'Synthetic Basin Loop · Hiking, Synthetic Range · Eric Sichak')
        self.assertEqual(core.page_title(self.by['syn-p-both']), 'Synthetic Basin, Synthetic Range · Eric Sichak')
        self.assertEqual(core.page_title(self.by['syn-p-both'], dup=True), 'Synthetic Basin, Synthetic Range, Jun 2, 2025 · Eric Sichak')

    def test_a_repeated_title_takes_its_date_after_the_place(self):
        self.assertEqual(core.page_title(self.by['syn-p-region'], dup=True),
                         'Synthetic Lap · Mountain Biking, Synthetic Coast, Jul 1, 2025 · Eric Sichak')
        self.assertEqual(core.page_title(dict(self.by['syn-p-region'], date=None), dup=True),
                         'Synthetic Lap · Mountain Biking, Synthetic Coast · Eric Sichak')


class DescriptionTests(Fixture):

    def test_the_facts_lead_whole_and_whole_sentences_follow_when_they_fit(self):
        t = self.by['syn-p-fits']
        summary = core.summary(t)
        both = summary + ' ' + SENT + ' ' + SENT
        self.assertLessEqual(len(both), core.DESC_LIMIT)
        self.assertEqual(core.describe(t, facts=True), both)
        # with less room only the first sentence; with none, the summary alone, never a cut
        self.assertEqual(core.describe(t, facts=True, limit=len(summary) + 1 + len(SENT) + 5), summary + ' ' + SENT)
        self.assertEqual(core.describe(t, facts=True, limit=len(summary) + 10), summary)
        self.assertEqual(core.describe(t, facts=True, limit=20), summary)              # longer than the limit, written whole
        # a write-up with no sentence end that does not fit adds nothing
        self.assertEqual(core.describe(self.by['syn-p-long'], facts=True), core.summary(self.by['syn-p-long']))

    def test_a_write_up_that_leads_ends_at_its_last_sentence_in_reach(self):
        d = core.describe(self.by['syn-p-story'], facts=False)
        self.assertTrue(80 <= len(d) <= 160, len(d))
        self.assertTrue(d.endswith('of the story.'), d)
        self.assertTrue(self.by['syn-p-story']['body_md'].startswith(d))
        # a first sentence under 80 characters, then none by 160: that sentence alone (DESC_FLOOR is 40)
        self.assertEqual(core.describe(self.by['syn-p-short-first'], facts=False), 'Synthetic opening sentence of some length here.')
        # no sentence end at all within 160: the facts lead instead, never a cut
        t = self.by['syn-p-long']
        self.assertEqual(core.describe(t, facts=False), core.summary(t))

    def test_a_multi_day_trip_adds_its_first_written_day(self):
        t = self.by['syn-p-tour']
        self.assertEqual(core.describe(t, facts=True), core.summary(t) + ' Day 1: ' + SENT)

    def test_a_goal_adds_its_why(self):
        t = dict(self.by['syn-p-region'], kind='planned', goal={'why': SENT})
        self.assertEqual(core.describe(t, facts=True), core.summary(t) + ' ' + SENT)


class HeadTests(Fixture):

    def test_a_report_names_its_author_section_and_tags(self):
        t = self.by['syn-p-place']
        tags = Doc('<head>%s</head>' % core._report_head(t, core.SITE_URL + t['url'], 'x', None)).find_all('meta')
        self.assertEqual([(m['property'], m['content']) for m in tags], [
            ('article:author', core.AUTHOR_URL), ('article:section', 'Backcountry Skiing'),
            ('article:tag', 'Synthetic Range'), ('article:tag', 'Synthetic Peak'), ('article:tag', 'Synthetic Dome')])

    def test_every_page_names_the_site_and_its_locale(self):
        for url in a11y.site_pages():
            if url.endswith('.json'):
                continue
            with self.subTest(page=url):
                head = a11y.page_doc(url).find('head')
                props = [m['property'] for m in head.find_all('meta') if m['property']]
                self.assertEqual(props.count('og:site_name'), 1)
                self.assertEqual(head.find('meta', attrs={'property': 'og:site_name'})['content'], core.SITE_NAME)
                self.assertEqual(head.find('meta', attrs={'property': 'og:locale'})['content'], 'en_US')


class CrumbsTests(unittest.TestCase):

    def test_one_list_gives_the_nav_and_the_breadcrumb_list(self):
        html_, ld = core.crumbs('trips/syn-x/', [('Reports', '../../'), ('Hiking & more', '../../hiking/'), ('Here', None)])
        doc = Doc('<nav>%s</nav>' % html_)
        self.assertEqual([(a.text(), a['href']) for a in doc.find_all('a')], [('Reports', '../../'), ('Hiking & more', '../../hiking/')])
        self.assertEqual(doc.find('span', attrs={'aria-current': 'page'}).text(), 'Here')
        self.assertEqual(ld['itemListElement'], [
            {'@type': 'ListItem', 'position': 1, 'name': 'Reports', 'item': core.SITE_URL},
            {'@type': 'ListItem', 'position': 2, 'name': 'Hiking & more', 'item': core.SITE_URL + 'hiking/'},
            {'@type': 'ListItem', 'position': 3, 'name': 'Here'}])
        self.assertNotIn('<', core.ld_script({'name': '</script>'})[len('<script type="application/ld+json">'):-len('</script>')])

    def test_every_crumbed_page_carries_its_crumbs_as_a_breadcrumb_list(self):
        seen = 0
        for url in a11y.site_pages():
            if url.endswith('.json'):
                continue
            doc = a11y.page_doc(url)
            nav = doc.find('nav', cls='crumbs')
            lists = [json.loads(s.text(clean=False)) for s in doc.find_all('script', attrs={'type': 'application/ld+json'})]
            lists = [x for x in lists if x.get('@type') == 'BreadcrumbList']
            with self.subTest(page=url):
                if nav is None:
                    self.assertEqual(lists, [])
                    continue
                seen += 1
                self.assertEqual(len(lists), 1)
                shown = [helpers.plain_text(n.text()) for n in nav.children if not isinstance(n, str) and n['aria-hidden'] != 'true']
                self.assertEqual([i['name'] for i in lists[0]['itemListElement']], shown)
                hrefs = [n['href'] for n in nav.children if not isinstance(n, str) and n.tag == 'a']
                items = [i['item'] for i in lists[0]['itemListElement'] if 'item' in i]
                self.assertEqual(len(items), len(hrefs))
                for href, item in zip(hrefs, items):              # each item is the page its link opens
                    self.assertEqual(item, urljoin(core.SITE_URL + url, href))
                    self.assertTrue(item.startswith(core.SITE_URL), item)
        self.assertGreater(seen, 15)


class AssetVersionTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)

    def head(self):
        return Doc(core.document('trips/syn-x/', 'Synthetic', '<p>Synthetic.</p>')).find('head')

    def test_outside_a_build_the_bundles_have_their_bare_names(self):
        doc = Doc(core.document('trips/syn-x/', 'Synthetic', '<p>Synthetic.</p>'))
        self.assertEqual([ln['href'] for ln in doc.find_all('link', attrs={'rel': 'stylesheet'})][-1], '../../assets/site.css')
        self.assertEqual(doc.find_all('script')[-1]['src'], '../../assets/site.js')

    def test_during_a_build_they_carry_their_hash(self):
        with mock.patch.dict(core._ASSET_VERSION, css='0123abcd', js='89ef4567'):
            doc = Doc(core.document('trips/syn-x/', 'Synthetic', '<p>Synthetic.</p>'))
        self.assertEqual([ln['href'] for ln in doc.find_all('link', attrs={'rel': 'stylesheet'})][-1], '../../assets/site.css?v=0123abcd')
        self.assertEqual(doc.find_all('script')[-1]['src'], '../../assets/site.js?v=89ef4567')
        build = importlib.import_module('build')
        self.assertEqual(build.asset_hash('a'), '86f7e437')                  # sha1('a'), its first 8 hex digits


class FontHeadTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)

    def test_google_fonts_until_the_fonts_are_the_sites_own(self):
        html_ = core.document('trips/syn-x/', 'Synthetic', '<p>Synthetic.</p>')
        self.assertIn('https://fonts.googleapis.com/css2?', html_)
        self.assertNotIn('as="font"', html_)
        with mock.patch.object(core, '_SELF_FONTS', [True]):
            html_ = core.document('trips/syn-x/', 'Synthetic', '<p>Synthetic.</p>')
        self.assertNotIn('fonts.googleapis.com', html_)
        self.assertNotIn('fonts.gstatic.com', html_)
        # no font preloads (core.FONT_PRELOADS, measured): a test that sets one sees it written with crossorigin
        self.assertEqual(Doc(html_).find('head').find_all('link', attrs={'rel': 'preload'}), [])
        with mock.patch.object(core, '_SELF_FONTS', [True]), mock.patch.object(core, 'FONT_PRELOADS', ('assets/fonts/x.woff2',)):
            pre = Doc(core.document('trips/syn-x/', 'Synthetic', '<p>Synthetic.</p>')).find('head').find_all('link', attrs={'rel': 'preload'})
        self.assertEqual([(ln['href'], ln['as'], ln['type'], 'crossorigin' in ln) for ln in pre],
                         [('../../assets/fonts/x.woff2', 'font', 'font/woff2', True)])


GOOGLE_CSS = ''.join(
    "/* %s */\n@font-face {\n  font-family: '%s';\n  font-style: %s;\n  font-weight: 400 700;\n  font-display: swap;\n"
    "  src: url(https://fonts.gstatic.com/s/%s-%s-%s.woff2) format('woff2');\n  unicode-range: U+%s;\n}\n"
    % (sub, fam, style, fam.replace(' ', ''), style, sub, rng, )
    for fam, style in (('Archivo', 'normal'), ('Source Serif 4', 'normal'), ('Source Serif 4', 'italic'), ('Geist Mono', 'normal'))
    for sub, rng in (('latin-ext', '0100-02AF'), ('latin', '0000-00FF')))


class FontsToolTests(unittest.TestCase):

    def setUp(self):
        self.fonts = importlib.import_module('fonts')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        os.makedirs(os.path.join(self.root, 'assets', 'css'))
        self.asked = []

    def get(self, url):
        self.asked.append(url)
        if url == core.FONTS:
            return GOOGLE_CSS.encode('utf-8')
        if url.endswith('.woff2'):
            return b'wOF2synthetic'
        return b'Synthetic licence text.'

    def test_it_keeps_the_latin_file_of_each_face_and_writes_the_sheet(self):
        with mock.patch('sys.stdout'):
            self.assertEqual(self.fonts.main([], root=self.root, get=self.get), 0)
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, 'assets', 'fonts'))),
                         sorted([f[2] for f in self.fonts.FACES] + list(self.fonts.LICENSES)))
        self.assertNotIn('latin-ext', ' '.join(self.asked))
        css = open(os.path.join(self.root, 'assets', 'css', 'fonts.css')).read()
        self.assertEqual(css.count('@font-face'), 4)
        self.assertEqual(css.count('font-display: swap;'), 4)
        self.assertEqual(css.count('unicode-range: U+0000-00FF;'), 4)
        for f in self.fonts.FACES:                                          # each face's copy, addressed from site.css
            self.assertIn('src: url("fonts/%s") format("woff2");' % f[2], css)
        self.assertEqual(self.fonts.check(self.root), [])

    def test_nothing_is_written_unless_every_file_arrived(self):
        bad = lambda url: b'<html>not a font</html>' if url.endswith('.woff2') else self.get(url)  # noqa: E731
        with self.assertRaises(ValueError):
            self.fonts.download(self.root, bad)
        short = lambda url: GOOGLE_CSS.replace('Geist Mono', 'Other Mono').encode('utf-8') if url == core.FONTS else self.get(url)  # noqa: E731
        with self.assertRaises(ValueError):
            self.fonts.download(self.root, short)
        # a stylesheet that names a file anywhere but Google's font host is not followed (file:, another site)
        for elsewhere in ('file:///synthetic/OFL.txt', 'https://fonts.example.test/x.woff2'):
            odd = lambda url, e=elsewhere: GOOGLE_CSS.replace('https://fonts.gstatic.com/s/Archivo-normal-latin.woff2', e).encode('utf-8') \
                if url == core.FONTS else self.get(url)  # noqa: E731
            with self.assertRaises(ValueError):
                self.fonts.download(self.root, odd)
        self.assertNotIn('file:///synthetic/OFL.txt', self.asked)
        self.assertFalse(os.path.exists(os.path.join(self.root, 'assets', 'fonts')))
        self.assertFalse(os.path.exists(os.path.join(self.root, 'assets', 'css', 'fonts.css')))
        with mock.patch('sys.stdout'):
            self.assertEqual(self.fonts.main(['--check'], root=self.root), 1)

    def test_the_build_bundles_the_sheet_first(self):
        build = importlib.import_module('build')
        self.fonts.download(self.root, self.get)
        with open(os.path.join(self.root, 'assets', 'css', 'base.css'), 'w') as fh:
            fh.write('.synthetic-base { color: red; }\n')
        with mock.patch.object(build, 'ROOT', self.root):
            css = build.css_bundle()
        self.assertTrue(css.startswith('@font-face {'), css[:40])
        self.assertLess(css.rindex('@font-face'), css.index('.synthetic-base'))

    def test_the_sheet_in_the_checkout_names_files_that_are_there(self):
        # every @font-face src of assets/css/fonts.css is a file under assets/fonts/, with the three licences
        if not os.path.exists(os.path.join(helpers.ROOT, 'assets', 'css', 'fonts.css')):
            self.skipTest('the fonts are not the site\'s own yet (tools/fonts.py has not run)')
        self.assertEqual(self.fonts.check(helpers.ROOT), [])


class ImageTests(Fixture):

    def test_the_ski_page_preloads_its_first_panel_map_for_both_breakpoints(self):
        section = importlib.import_module('sitegen.pages.section')
        site = helpers.make_site(list(self.by.values()))
        maps = {'ski-synthetic-range-%s' % v: {'png': 'ski-synthetic-range-%s.webp' % v, 'base': 'ski-synthetic-range-%s.base.svg' % v}
                for v in ('desktop', 'phone')}
        with mock.patch.object(section, 'ski_regions', lambda ts: ['Synthetic Range']), \
                mock.patch.object(core, 'site_meta', lambda: {'maps': maps}):
            head = Doc(section.page('ski', site).html).find('head')
        pre = [(ln['href'], ln['media']) for ln in head.find_all('link', attrs={'rel': 'preload'})]
        d, p = section.SKI_MEDIA['desktop'], section.SKI_MEDIA['phone']
        self.assertEqual(pre, [('../assets/maps/ski-synthetic-range-desktop.webp', d), ('../assets/maps/ski-synthetic-range-desktop.base.svg', d),
                               ('../assets/maps/ski-synthetic-range-phone.webp', p), ('../assets/maps/ski-synthetic-range-phone.base.svg', p)])
        with mock.patch.object(section, 'ski_regions', lambda ts: []):
            self.assertNotIn('rel="preload"', section.page('ski', site).html)        # no panel map, nothing to preload

    def test_each_ski_preload_holds_exactly_where_the_panel_shows_that_map(self):
        # the review's finding: (min-width: 560px) fetched the desktop render at 760-1199, where the panel shows the phone
        # one; SKI_MEDIA against section.css's own cascade, at every size the panel's rules turn on
        section = importlib.import_module('sitegen.pages.section')
        rules = a11y.published_rules()[0]
        doc = Doc('<main><div class="sec-maps"><div class="mv mv--desktop"></div><div class="mv mv--phone"></div></div></main>')
        views = {v: doc.find('div', cls='mv--' + v) for v in ('desktop', 'phone')}
        for w in (320, 559, 560, 759, 760, 959, 960, 1199, 1200, 1440):
            for h in (700, 759, 760, 900):
                e = a11y.env(w, h)
                for v, node in views.items():
                    with self.subTest(width=w, height=h, view=v):
                        self.assertEqual(a11y.media_matches(section.SKI_MEDIA[v], e), a11y.displayed(node, rules, e))

    def test_the_hiking_journal_squares_list_their_th_copy_first(self):
        # section.series_block (the Hiking page's journal block) on a synthetic journal whose day photos have their copies
        section = importlib.import_module('sitegen.pages.section')
        with tempfile.TemporaryDirectory() as tmp:
            days = [{'id': '%03d' % i, 'date': '2024-04-%02d' % (21 + i), 'track': False,
                     'photos': [helpers.photo('photos/d%03d-01.webp' % i, helpers.LANDSCAPE, alt='Synthetic photo %d' % i, sm=True)]}
                    for i in (1, 2, 3)]
            folder = helpers.make_trip(tmp, 'syn-j', title='Synthetic Journal', activity='hike', kind='series', date='2024-04-22',
                                       end_date='2024-04-24', days=days)
            for i in (1, 2, 3):
                helpers.touch(os.path.join(folder, 'photos', 'd%03d-01.th.webp' % i))
            t = helpers.load(tmp, 'syn-j')
            imgs = [f.find('img') for f in Doc(section.series_block(t, 'hiking/')).find_all('figure', cls='sec-ser-ph')]
        self.assertEqual(len(imgs), 3)
        for i, img in enumerate(imgs, 1):
            self.assertEqual(img['srcset'].split(', ')[0], '../trips/syn-j/photos/d%03d-01.th.webp 427w' % i)

    def test_a_small_slot_lists_the_th_copy_first(self):
        t = {'url': 'trips/syn-x/'}
        p = {'file': 'photos/01.webp', 'sm': 'photos/01.sm.webp', 'th': 'photos/01.th.webp', 'w': 1600, 'h': 1200, 'alt': 'x'}
        srcset = lambda html_: Doc(html_).find('img')['srcset']  # noqa: E731
        self.assertEqual(srcset(core.photo(t, p, 'hiking/', thumb=True)),
                         '../trips/syn-x/photos/01.th.webp 427w, ../trips/syn-x/photos/01.sm.webp 800w, ../trips/syn-x/photos/01.webp 1600w')
        self.assertEqual(srcset(core.photo(t, p, 'hiking/')), '../trips/syn-x/photos/01.sm.webp 800w, ../trips/syn-x/photos/01.webp 1600w')
        no_th = dict(p, th=None)
        self.assertEqual(srcset(core.photo(t, no_th, 'hiking/', thumb=True)), srcset(core.photo(t, no_th, 'hiking/')))


class FeedContentTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.build = importlib.import_module('build')

    def trips(self):
        return helpers.load_dir(self.root)

    def test_a_written_report_carries_its_write_up_photos_and_links(self):
        helpers.make_trip(self.root, 'syn-f-story', title='Synthetic Story', activity='hike', date='2026-06-01', track=True,
                          body='Synthetic *words* & more.\n\n# Synthetic Head\n\nSee [the other](../syn-f-other/).', photos=[helpers.photo('photos/01.webp', helpers.LANDSCAPE, alt='Synthetic <alt>', sm=True)])
        (t,) = self.trips()
        url = core.SITE_URL + 'trips/syn-f-story/'
        self.assertEqual(self.build.feed_content(t),
                         '<p>Synthetic <em>words</em> &amp; more.</p>\n<h2>Synthetic Head</h2>\n'
                         '<p>See <a href="%strips/syn-f-other/">the other</a>.</p>'          # a relative link made absolute
                         '<p><img src="%sphotos/01.sm.webp" alt="Synthetic &lt;alt&gt;"></p>'
                         '<p><a href="%s">Open the report</a> · <a href="%ssyn-f-story.gpx">Download GPX</a></p>' % (core.SITE_URL, url, url, url))
        root = ET.fromstring(self.build.feed([t]))
        enc = root.find('channel/item/{http://purl.org/rss/1.0/modules/content/}encoded')
        self.assertEqual(enc.text, self.build.feed_content(t))              # escaped once in the XML, whole when read

    def test_a_multi_day_trip_adds_each_written_day_and_one_without_its_own_write_up_none(self):
        helpers.make_trip(self.root, 'syn-f-tour', title='Synthetic Tour', activity='ski', kind='multi-day', date='2026-03-10',
                          end_date='2026-03-12', body='Synthetic overview.',
                          days=[{'date': '2026-03-10', 'title': 'Synthetic Hut', 'body': 'Synthetic day one.'},
                                {'date': '2026-03-11'}, {'date': '2026-03-12', 'body': 'Synthetic day three.'}])
        helpers.make_trip(self.root, 'syn-f-days', title='Synthetic Days', activity='ski', kind='multi-day', date='2026-02-10',
                          days=[{'date': '2026-02-10', 'body': 'Synthetic day words.'}])
        by = {t['slug']: t for t in self.trips()}
        html_ = self.build.feed_content(by['syn-f-tour'])
        self.assertIn('<p>Synthetic overview.</p><h2>Day 1: Synthetic Hut</h2><p>Synthetic day one.</p>'
                      '<h2>Day 3</h2><p>Synthetic day three.</p>', html_)
        self.assertNotIn('Day 2', html_)
        items = ET.fromstring(self.build.feed(list(by.values()))).findall('channel/item')
        has = {i.findtext('title'): i.find('{http://purl.org/rss/1.0/modules/content/}encoded') is not None for i in items}
        self.assertEqual(has, {'Synthetic Tour': True, 'Synthetic Days': False})


class HeadExtrasTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)

    def test_a_page_links_the_home_screen_icon_the_checkout_has(self):
        icon = os.path.join(helpers.ROOT, 'assets', 'apple-touch-icon.png')
        with open(icon, 'rb') as fh:
            head = fh.read(24)
        self.assertEqual((head[:8], int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')),
                         (b'\x89PNG\r\n\x1a\n', 180, 180))
        with mock.patch.object(core, 'ROOT', helpers.ROOT):
            links = Doc(core.document('trips/syn-x/', 'Synthetic', '<p>Synthetic.</p>')).find('head').find_all('link', attrs={'rel': 'apple-touch-icon'})
        self.assertEqual([ln['href'] for ln in links], ['../../assets/apple-touch-icon.png'])
        # a tree without the file (a test's temporary one) links none, so the site check finds no broken link
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(core, 'ROOT', tmp):
            self.assertNotIn('apple-touch-icon', core.document('trips/syn-x/', 'Synthetic', '<p>Synthetic.</p>'))

    def test_the_verification_tags_are_written_only_when_set(self):
        plain = core.document('trips/syn-x/', 'Synthetic', '<p>Synthetic.</p>')
        self.assertNotIn('site-verification', plain)
        with mock.patch.object(core, 'VERIFY_TAGS', (('google-site-verification', 'syn-token'), ('msvalidate.01', 'SYN<"x">'))):
            html_ = core.document('trips/syn-x/', 'Synthetic', '<p>Synthetic.</p>')
        self.assertIn('<meta name="theme-color" content="#F2F1EC"><meta name="google-site-verification" content="syn-token">'
                      '<meta name="msvalidate.01" content="SYN&lt;&quot;x&quot;&gt;">', html_)
        self.assertEqual(html_.replace('<meta name="google-site-verification" content="syn-token">', '')
                         .replace('<meta name="msvalidate.01" content="SYN&lt;&quot;x&quot;&gt;">', ''), plain)


if __name__ == '__main__':
    unittest.main()
