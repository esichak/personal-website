"""Review gate (fix F): the 404 page (sitegen.pages.notfound -> /404.html) and its "Site" list.

The list offered one way on, 'Map & archive'. It now offers Trips first ('SEARCH AND FILTER', the page a visitor with a
dead link to a report most likely wants), then 'Map & archive' with the count line it had. Pinned here: the two links
in that order, each with its text, its line and its icon; that the rest of the page is byte for byte the page of commit
dbce17b (legacy_page, a copy of that body); that both links resolve against the page's <base> from wherever GitHub Pages
serves the page, and name pages a build has; and that the page still names no canonical URL and is noindex.

The site is synthetic (tests/helpers.py); the built one is the repository of tests/test_build_site.py in a temp folder.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import urljoin, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
from sitegen import core  # noqa: E402
from sitegen import sitecheck  # noqa: E402
from sitegen.pages import notfound  # noqa: E402
from sitegen.pages.about import act_rows  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

BASE = '/personal-website/'
# the Trips row, as the page writes it: the search icon, the name, the line, the chevron of every row
TRIPS_ROW = ('<li><a class="abo-act-a" href="trips/"><span class="nf-ic" aria-hidden="true">%s</span>'
             '<span class="abo-act-w"><span class="abo-act-n">Trips</span>'
             '<span class="t-mono-s abo-act-m">SEARCH AND FILTER</span></span>%s</a></li>')
# the 'Map & archive' row as the page of commit dbce17b wrote it (%d: the published reports)
MAP_ROW = ('<li><a class="abo-act-a" href="map/"><span class="nf-ic" aria-hidden="true">%s</span>'
           '<span class="abo-act-w"><span class="abo-act-n">Map &amp; archive</span>'
           '<span class="t-mono-s abo-act-m">ALL %d REPORTS</span></span>%s</a></li>')


def legacy_page(site):
    """notfound.page as it was at commit dbce17b (before the Trips row), copied line for line."""
    link, icon, here = core.link, core.icon, notfound.HERE
    body = ('<div class="nf wrap"><div class="nf-grid">'
            '<div class="nf-intro">'
            '<p class="t-mono-s nf-code">404 · PAGE NOT FOUND</p>'
            '<h1 class="t-d1 nf-h">Off route</h1>'
            '<p class="nf-line">There is no page at this address. The link may be old or mistyped.</p>'
            '<a class="btn btn--ink nf-home" href="%s">Go to the home page%s</a>'
            '</div>'
            '<nav class="nf-nav" aria-label="Ways back"><h2 class="t-label nf-l">Reports</h2>%s'
            '<h2 class="t-label nf-l nf-l2">Site</h2><ul class="abo-act"><li><a class="abo-act-a" href="%s"><span class="nf-ic" aria-hidden="true">%s</span>'
            '<span class="abo-act-w"><span class="abo-act-n">Map &amp; archive</span>'
            '<span class="t-mono-s abo-act-m">ALL %d REPORTS</span></span>%s</a></li></ul></nav>'
            '</div></div>'
            % (link(here, ''), icon('arrow-right', 18), act_rows(site, here, dist=False),
               link(here, 'map/'), icon('map', 20), len(site['published']), icon('chevron-right', 20, 'abo-act-c')))
    extra = notfound.base_tag() + '<meta name="robots" content="noindex">'
    html_ = core.document(here, 'Page not found', body, 'This page is not on the map.', body_cls='p-404', extra_head=extra,
                          canonical=False)
    return html_.replace(extra, '', 1).replace('<meta charset="utf-8">', '<meta charset="utf-8">' + extra, 1)


class NotFoundFixture(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        # no site meta is read from rendered/: the header and the footer need none of it
        patcher = mock.patch.object(core, '_SITE_META', [{'hash': '', 'maps': {}, 'regions': [], 'all_regions': ['Synthetic Range']}])
        patcher.start()
        self.addCleanup(patcher.stop)
        mk = helpers.make_trip
        mk(self.tmp, 'synf-couloir', title='Synthetic Couloir', activity='ski', date='2026-01-17', region='Synthetic Range', track=True)
        mk(self.tmp, 'synf-loop', title='Synthetic Loop', activity='hike', date='2025-08-10', region='Synthetic Range',
           body='A synthetic loop over three synthetic summits.')
        mk(self.tmp, 'synf-crag', title='Synthetic Crag', activity='climb', date='2025-06-01', region='Synthetic Range')
        mk(self.tmp, 'synf-tour', title='Synthetic Tour', activity='ski', kind='multi-day', date='2024-02-01', end_date='2024-02-02',
           days=[{'title': 'In'}, {'title': 'Out'}])
        helpers.make_series(self.tmp, 'synf-journal', title='Synthetic Journal 2024')
        mk(self.tmp, 'synf-goal', title='Synthetic Goal', activity='ski', kind='planned', date='2027-06-01', track=True)
        mk(self.tmp, 'synf-draft', title='Synthetic Draft', activity='hike', date='2026-03-03', draft=True)
        self.trips = helpers.load_dir(self.tmp)
        self.site = helpers.make_site(self.trips)
        self.page = notfound.page(self.site)
        self.html = self.page.html
        self.doc = Doc(self.html)

    def ways_back(self, doc=None):
        (nav,) = (doc or self.doc).find_all('nav', attrs={'aria-label': 'Ways back'})
        return nav

    def site_list(self, doc=None):
        """The <ul> that follows the 'Site' heading in the page's 'Ways back' nav."""
        parts = self.ways_back(doc).elements()
        self.assertEqual([(n.tag, n.text()) for n in parts if n.tag == 'h2'], [('h2', 'Reports'), ('h2', 'Site')])
        self.assertEqual([n.tag for n in parts], ['h2', 'ul', 'h2', 'ul'])
        return parts[3]

    def rows(self, ul):
        """(href, name, line) of every row of an .abo-act list."""
        out = []
        for li in ul.elements():
            (a,) = li.elements()
            out.append((a['href'], a.find('span', cls='abo-act-n').text(), a.find('span', cls='abo-act-m').text()))
        return out


class SiteListTests(NotFoundFixture):

    def test_the_fixture_has_five_published_reports(self):
        self.assertEqual(sorted(t['slug'] for t in self.site['published']),
                         ['synf-couloir', 'synf-crag', 'synf-journal', 'synf-loop', 'synf-tour'])
        self.assertEqual([t['slug'] for t in self.site['planned']], ['synf-goal'])
        self.assertEqual((self.page.url, notfound.URL, notfound.HERE), ('404.html', '404.html', ''))

    def test_the_site_list_offers_trips_then_map_and_archive(self):
        ul = self.site_list()
        self.assertEqual(ul.classes, ['abo-act'])
        self.assertEqual(self.rows(ul), [('trips/', 'Trips', 'SEARCH AND FILTER'), ('map/', 'Map & archive', 'ALL 5 REPORTS')])
        self.assertEqual(len(ul.find_all('a')), 2)
        # each is one link with the list's parts: an icon that is not read out, the name over its line, the chevron
        for li in ul.elements():
            (a,) = li.elements()
            self.assertEqual((li.tag, a.tag, a.classes), ('li', 'a', ['abo-act-a']))
            self.assertEqual([(n.tag, n.classes) for n in a.elements()],
                             [('span', ['nf-ic']), ('span', ['abo-act-w']), ('svg', ['ic', 'abo-act-c'])])
            self.assertEqual(a.find('span', cls='nf-ic')['aria-hidden'], 'true')
            self.assertEqual([n.classes for n in a.find('span', cls='abo-act-w').elements()], [['abo-act-n'], ['t-mono-s', 'abo-act-m']])
        # the link's whole text: the name and the line, nothing from the icons
        self.assertEqual([a.text() for a in ul.find_all('a')], ['TripsSEARCH AND FILTER', 'Map & archiveALL 5 REPORTS'])

    def test_the_trips_row_is_written_once_with_the_search_icon_before_the_map_row(self):
        chevron = core.icon('chevron-right', 20, 'abo-act-c')
        trips = TRIPS_ROW % (core.icon('search', 20), chevron)
        the_map = MAP_ROW % (core.icon('map', 20), 5, chevron)
        self.assertEqual((self.html.count(trips), self.html.count(the_map)), (1, 1))
        self.assertIn('<h2 class="t-label nf-l nf-l2">Site</h2><ul class="abo-act">' + trips + the_map + '</ul></nav>', self.html)
        self.assertNotEqual(core.icon('search', 20), core.icon('map', 20))
        self.assertEqual(self.html.count('SEARCH AND FILTER'), 1)

    def test_the_map_row_keeps_its_count_line(self):
        # 'ALL N REPORTS': the published reports (a journal is one, a planned route and a draft are none), as before
        chevron = core.icon('chevron-right', 20, 'abo-act-c')
        self.assertEqual(len(self.site['published']), 5)
        for keep in (['synf-couloir'], ['synf-couloir', 'synf-loop', 'synf-goal'], ['synf-goal'], [t['slug'] for t in self.trips]):
            with self.subTest(trips=keep):
                site = helpers.make_site([self.site['by_slug'][s] for s in keep])
                n = len(site['published'])
                html_ = notfound.page(site).html
                self.assertEqual(self.rows(self.site_list(Doc(html_))),
                                 [('trips/', 'Trips', 'SEARCH AND FILTER'), ('map/', 'Map & archive', 'ALL %d REPORTS' % n)])
                self.assertEqual(html_.count(MAP_ROW % (core.icon('map', 20), n, chevron)), 1)
                self.assertEqual(html_.count('SEARCH AND FILTER'), 1)          # the Trips line counts nothing

    def test_the_rest_of_the_page_is_the_page_it_was(self):
        # take the Trips row and the search box (Phase 7) out and the page is, byte for byte, the one commit dbce17b built
        # for the same site (with today's header, which both are built with)
        trips = TRIPS_ROW % (core.icon('search', 20), core.icon('chevron-right', 20, 'abo-act-c'))
        box = notfound.search_block(notfound.HERE)
        old = legacy_page(self.site)
        self.assertEqual((self.html.count(trips), self.html.count(box)), (1, 1))
        self.assertEqual(self.html.replace(trips, '').replace(box, ''), old)
        self.assertEqual(len(self.html) - len(old), len(trips) + len(box))
        self.assertNotIn('SEARCH AND FILTER', old)
        self.assertEqual(self.rows(self.site_list(Doc(old))), [('map/', 'Map & archive', 'ALL 5 REPORTS')])
        # the Reports list above it is untouched: the five activity pages, in the site's order
        reports = self.ways_back().elements()[1]
        self.assertEqual([a['href'] for a in reports.find_all('a')], [core.section_url(act) for act, _label in core.NAV])
        self.assertEqual(self.ways_back().elements()[1].find_all('a'), reports.find_all('a'))
        self.assertEqual(len(self.ways_back().find_all('a')), len(core.NAV) + 2)

    def test_build_returns_the_one_page(self):
        (p,) = notfound.build(self.site)
        self.assertEqual((p.url, p.html), ('404.html', self.html))


class BaseTests(NotFoundFixture):
    """GitHub Pages serves 404.html for a missing path at any depth, so the page's links are written from the site
    root and the page tells the browser where that is: <base href='/personal-website/'>."""

    # where a visitor may be when the page is served: the root, a missing report, a missing file three folders down
    SERVED_AT = ('', 'no-such-page', 'trips/gone-report/', 'trips/gone-report/map/', 'a/b/c/d.html')

    def base(self):
        (base,) = self.doc.find_all('base')
        return base

    def resolve(self, href, served_at):
        """The address a browser opens for this href on the 404 page served at SITE_URL + served_at."""
        return urljoin(urljoin(core.SITE_URL + served_at, self.base()['href']), href)

    def test_the_page_has_one_base_and_it_is_the_site_root(self):
        self.assertEqual(self.base()['href'], BASE)
        self.assertEqual(BASE, urlparse(core.SITE_URL).path)
        self.assertEqual(self.html.count('<base '), 1)
        self.assertIs(self.base().parent, self.doc.find('head'))
        # before anything in the page that names a URL: a <base> only applies to what follows it
        head = self.html[:self.html.index('</head>')]
        first_url = min(head.index(a) for a in (' href="', ' src="', ' content="http') if a in head)
        self.assertLess(head.index('<base '), first_url)
        self.assertIn('<head><meta charset="utf-8">' + notfound.base_tag(), head)
        self.assertEqual(notfound.base_tag(), "<base href='%s'>" % BASE)        # single-quoted: the link check reads href="…" as a file

    def test_both_site_links_resolve_against_the_base(self):
        hrefs = [a['href'] for a in self.site_list().find_all('a')]
        self.assertEqual(hrefs, ['trips/', 'map/'])
        for href in hrefs:
            self.assertFalse(href.startswith(('/', './', '../', 'http', '#')), href)
        for served_at in self.SERVED_AT:
            with self.subTest(served_at=served_at):
                self.assertEqual([self.resolve(h, served_at) for h in hrefs], [core.SITE_URL + 'trips/', core.SITE_URL + 'map/'])
        # without the base the same two links would lead nowhere from a missing report's address
        there = core.SITE_URL + 'trips/gone-report/'
        self.assertEqual([urljoin(there, h) for h in hrefs], [there + 'trips/', there + 'map/'])

    def test_every_other_link_of_the_ways_back_resolves_the_same_way(self):
        nav = self.ways_back()
        want = [core.SITE_URL + core.section_url(act) for act, _label in core.NAV] + [core.SITE_URL + 'trips/', core.SITE_URL + 'map/']
        for served_at in self.SERVED_AT:
            with self.subTest(served_at=served_at):
                self.assertEqual([self.resolve(a['href'], served_at) for a in nav.find_all('a')], want)
                (home,) = self.doc.find_all('a', cls='nf-home')
                self.assertEqual(self.resolve(home['href'], served_at), core.SITE_URL)

    def test_the_two_links_name_pages_of_a_built_site(self):
        # tools/build.py on the synthetic repository of tests/test_build_site.py: the built 404.html has the two rows, and
        # the link check, which follows a page's links from its own folder (here the site root, the base), finds both
        import test_build_site as fixture        # the module, for its fixture: none of its tests is loaded from here
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        fixture.write_site(tmp.name)
        out_dir, _pages = fixture.run_build(tmp.name)
        with open(os.path.join(out_dir, '404.html'), encoding='utf-8') as fh:
            html_ = fh.read()
        doc = Doc(html_)
        published = len(fixture.REPORTS)
        self.assertEqual(self.rows(self.site_list(doc)),
                         [('trips/', 'Trips', 'SEARCH AND FILTER'), ('map/', 'Map & archive', 'ALL %d REPORTS' % published)])
        out = sitecheck.read(out_dir)
        self.assertEqual([out.resolve('', a['href']) for a in self.site_list(doc).find_all('a')], ['trips/index.html', 'map/index.html'])
        self.assertEqual(sitecheck.links(out, '404.html'), [])
        self.assertEqual(sitecheck.metadata(out, '404.html'), [])
        self.assertEqual(sitecheck.check(out_dir, os.path.join(tmp.name, 'content', 'trips')), [])
        # a row that named a page the build lacks would be reported
        pages = dict((page, out.text(page)) for page in out.pages)
        pages['404.html'] = html_.replace('<a class="abo-act-a" href="trips/">', '<a class="abo-act-a" href="trip/">', 1)
        self.assertNotEqual(pages['404.html'], html_)
        broken = sitecheck.of(pages, files=sorted(out.files))
        self.assertEqual(sitecheck.links(broken, '404.html'), ['BROKEN 404.html -> trip/'])


class HeadTests(NotFoundFixture):

    def test_the_page_still_has_no_canonical(self):
        head = self.doc.find('head')
        self.assertEqual(head.find_all('link', attrs={'rel': 'canonical'}), [])
        self.assertEqual([m for m in head.find_all('meta') if m['property'] == 'og:url'], [])
        self.assertNotIn('canonical', self.html)
        self.assertNotIn('og:url', self.html)
        # the home page, whose address the page would otherwise be given (its links are written from ''), has one
        self.assertIn('<link rel="canonical" href="%s">' % core.SITE_URL, core.document('', 'Home', '<p>x</p>'))

    def test_the_page_keeps_noindex(self):
        robots = self.doc.find('head').find_all('meta', attrs={'name': 'robots'})
        self.assertEqual([m['content'] for m in robots], ['noindex'])
        self.assertEqual(self.html.count('<meta name="robots" content="noindex">'), 1)
        self.assertEqual(self.html.count('name="robots"'), 1)

    def test_the_site_checks_pass_its_head_and_would_report_either_loss(self):
        pages = {'404.html': self.html}
        self.assertEqual(sitecheck.metadata(sitecheck.of(pages, site_url=core.SITE_URL), '404.html'), [])
        indexed = {'404.html': self.html.replace('<meta name="robots" content="noindex">', '', 1)}
        named = {'404.html': self.html.replace('</head>', '<link rel="canonical" href="%s404.html"></head>' % core.SITE_URL, 1)}
        for what, changed in (('noindex', indexed), ('canonical', named)):
            with self.subTest(lost=what):
                self.assertNotEqual(changed['404.html'], self.html)
                problems = sitecheck.metadata(sitecheck.of(changed, site_url=core.SITE_URL), '404.html')
                self.assertEqual(len(problems), 1, problems)
                self.assertTrue(problems[0].startswith('META 404.html: '), problems[0])
                self.assertIn(what, problems[0])

    def test_title_description_and_body_class_are_as_they_were(self):
        head = self.doc.find('head')
        self.assertEqual(len(head.find_all('title')), 1)
        self.assertIn('Page not found', head.find('title').text())
        self.assertEqual([m['content'] for m in head.find_all('meta', attrs={'name': 'description'})], ['This page is not on the map.'])
        self.assertEqual(self.doc.find('body').classes, ['p-404'])
        self.assertEqual([h.text() for h in self.doc.find_all('h1')], ['Off route'])


class SearchBoxTests(NotFoundFixture):
    """seo-14 (Phase 7): a search box on the 404 page that lands on the explorer (trips/?q=…&sort=relevance), resolved
    against the page's <base> from wherever it is served; notfound.js prefills it from a /trips/<slug>/ address alone."""

    def test_the_form_lands_on_the_explorer_in_best_match_order(self):
        (form,) = self.doc.find_all('form', cls='nf-search')
        self.assertEqual((form['role'], form['method'], form['action']), ('search', 'get', 'trips/'))
        box = form.find('input', attrs={'name': 'q'})
        self.assertEqual((box['id'], box['type'], box['maxlength'], box['autocomplete'], box['value']), ('nf-q', 'search', '200', 'off', None))
        self.assertEqual(form.find('label', attrs={'for': 'nf-q'}).text(), 'Search trips')
        self.assertEqual([(i['name'], i['value']) for i in form.find_all('input', attrs={'type': 'hidden'})], [('sort', 'relevance')])
        self.assertEqual(form.find('button')['type'], 'submit')
        for served_at in ('', 'trips/gone-report/', 'a/b/c.html'):
            self.assertEqual(urljoin(urljoin(core.SITE_URL + served_at, BASE), form['action']), core.SITE_URL + 'trips/')

    def test_the_question_line_is_empty_and_hidden_in_the_page(self):
        ask = self.doc.by_id('nf-ask')
        self.assertIn('hidden', ask)
        self.assertEqual(ask.text(), '')
        self.assertNotIn('Looking for', self.html)                      # only the script writes it, from the address

    def test_the_header_and_menu_boxes_have_ids_of_their_own(self):
        ids = [i['id'] for i in self.doc.find_all('input', attrs={'name': 'q'})]
        self.assertEqual(sorted(ids), ['menu-q', 'nav-q', 'nf-q'])

    def test_the_script_writes_text_never_html(self):
        with open(os.path.join(ROOT, 'assets', 'js', 'pages', 'notfound.js'), encoding='utf-8') as fh:
            src = fh.read()
        self.assertNotIn('innerHTML', src)
        self.assertIn('ask.textContent', src)
        self.assertIn('box.value = words', src)

    def run_script(self, path):
        """(box value, question text, question hidden) after notfound.js runs at `path`, with a stand-in for the page."""
        node = shutil.which('node')
        if not node:
            self.skipTest('node is not installed')
        script = os.path.join(ROOT, 'assets', 'js', 'pages', 'notfound.js')
        prog = (
            'const els = { "nf-q": { value: "" }, "nf-ask": { textContent: "", hidden: true } };'
            'global.document = { body: { classList: { contains: (c) => c === "p-404" } }, getElementById: (id) => els[id] || null,'
            ' addEventListener: () => {} };'
            'global.location = { pathname: %s };'
            'require(%s);'
            'process.stdout.write(JSON.stringify([els["nf-q"].value, els["nf-ask"].textContent, els["nf-ask"].hidden]));'
            % (json.dumps(path), json.dumps(script)))
        out = subprocess.run([node, '-e', prog], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return tuple(json.loads(out.stdout))

    def test_a_missing_trip_address_prefills_the_slugs_words(self):
        self.assertEqual(self.run_script('/personal-website/trips/old-tallac-lap/'),
                         ('old tallac lap', 'Looking for \u201cold tallac lap\u201d?', False))
        self.assertEqual(self.run_script('/personal-website/trips/old-tallac-lap/map/')[0], 'old tallac lap')
        self.assertEqual(self.run_script('/personal-website/trips/caf%C3%A9_run')[0], 'caf\u00e9 run')

    def test_a_dated_address_keeps_its_year_and_leaves_out_month_and_day(self):
        # the index holds a trip's year and month names, never a day of the month: '09' or '25' would find nothing
        self.assertEqual(self.run_script('/personal-website/trips/old-tallac-lap-2026-09-25/'),
                         ('old tallac lap 2026', 'Looking for \u201cold tallac lap 2026\u201d?', False))
        self.assertEqual(self.run_script('/personal-website/trips/day-7-of-24/')[0], 'day of')
        self.assertEqual(self.run_script('/personal-website/trips/09-25/'), ('', '', True))     # nothing left: no question
        self.assertEqual(self.run_script('/personal-website/trips/peak-100-2026/')[0], 'peak 100 2026')

    def test_any_other_address_leaves_the_box_and_the_line_alone(self):
        for path in ('/personal-website/no-such-page', '/personal-website/', '/personal-website/trips/', '/personal-website/a/b.html',
                     '/personal-website/trips/%E0%A4%A/'):
            with self.subTest(path=path):
                self.assertEqual(self.run_script(path), ('', '', True))

    def test_what_the_address_holds_is_text(self):
        value, line, hidden = self.run_script('/personal-website/trips/%3Cimg%20src%3Dx%3E/')
        self.assertEqual(value, '<img src=x>')
        self.assertEqual(line, 'Looking for \u201c<img src=x>\u201d?')       # set as textContent: shown, never parsed
        self.assertFalse(hidden)


if __name__ == '__main__':
    unittest.main()
