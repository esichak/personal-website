"""Phase 14 (plan 2, section 14, items 15-20): following the site and reaching Eric.

- gap5-01, gap5-03: content/author.json (sitegen.author.load, strict) puts the address on About ('Follow & contact'),
  in the footer, and the profiles Eric names on About; with no file, nothing of it.
- gap5-08: 'Ask about this trip' on every report, a mailto whose subject is the trip's title and date.
- gap5-05, gap5-07: About's #follow section (copy the feed's address, open the raw feed, a line on RSS-to-email); the
  footer's Follow lands there.
- gap5-02: 'Source on GitHub' last in the footer's Site list, an issue path on About; the repository's owner is the
  site's host.
The address is on the reserved example.test domain; every trip is synthetic.
"""
import json
import os
import tempfile
import unittest
from unittest import mock
from urllib.parse import unquote, urlparse

import helpers
from helpers import Doc

import test_a11y_static as a11y
from sitegen import author, core
from sitegen.pages import about, report

import checks

tearDownModule = helpers.no_region_pages_left

EMAIL = 'trips@example.test'
AUTHOR = {'email': EMAIL, 'links': [{'label': 'Synthetic Profile', 'url': 'https://profile.example.test/synthetic'}]}


class LoadTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = os.path.join(tmp.name, 'author.json')

    def write(self, text):
        with open(self.path, 'w', encoding='utf-8') as fh:
            fh.write(text if isinstance(text, str) else json.dumps(text))

    def refused(self, data):
        self.write(data)
        with self.assertRaises(author.AuthorError) as cm:
            author.load(self.path)
        self.assertTrue(str(cm.exception).startswith('content/author.json: '), str(cm.exception))
        return str(cm.exception)

    def test_no_file_is_no_contact(self):
        self.assertIsNone(author.load(self.path))

    def test_a_valid_file(self):
        self.write({'email': ' %s ' % EMAIL, 'links': AUTHOR['links']})
        self.assertEqual(author.load(self.path), AUTHOR)
        self.write({'links': []})
        self.assertEqual(author.load(self.path), {'email': None, 'links': []})

    def test_anything_else_stops_the_build_naming_the_file(self):
        self.assertIn('unknown key "phone"', self.refused({'email': EMAIL, 'phone': '1'}))
        self.assertIn('"email" is written twice', self.refused('{"email": "%s", "email": "%s"}' % (EMAIL, EMAIL)))
        self.assertIn('not valid JSON', self.refused('{"email": '))
        self.assertIn('top-level value', self.refused(['x']))
        self.assertIn('email must be a non-empty string', self.refused({'email': 7}))
        self.assertIn('is not an address', self.refused({'email': 'trips at example.test'}))
        self.assertIn('is not an address', self.refused({'email': 'a@b@example.test'}))
        for odd in ('a?subject=x@example.test', 'a#b@example.test', 'a&b@example.test', 'a%40b@example.test', 'a@example'):
            self.assertIn('is not an address', self.refused({'email': odd}), odd)     # nothing a mailto reads as its own
        self.assertIn('links must be a list', self.refused({'links': {'label': 'x'}}))
        self.assertIn('https:// address', self.refused({'links': [{'label': 'X', 'url': 'http://example.test/x'}]}))
        self.assertIn('https:// address', self.refused({'links': [{'label': 'X', 'url': 'javascript:alert(1)'}]}))
        self.assertIn('exactly the keys', self.refused({'links': [{'label': 'X'}]}))
        self.assertIn('written twice', self.refused({'links': [{'label': 'X', 'url': 'https://a.example.test/'},
                                                              {'label': 'x', 'url': 'https://b.example.test/'}]}))
        many = [{'label': 'L%d' % i, 'url': 'https://example.test/%d' % i} for i in range(author.MAX_LINKS + 1)]
        self.assertIn('at most %d' % author.MAX_LINKS, self.refused({'links': many}))

    def test_the_content_check_says_the_same(self):
        self.write({'email': 'nope'})
        out = []
        checks._author_findings(self.path, out)
        self.assertEqual([(f['level'], f['file']) for f in out], [('error', 'content/author.json')])
        self.assertIn('is not an address', out[0]['text'])
        os.remove(self.path)
        out = []
        checks._author_findings(self.path, out)
        self.assertEqual(out, [])
        self.assertEqual(checks.AUTHOR_KEYS, author.KEYS)


class FollowTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)

    def test_follow_without_an_author_file(self):
        doc = Doc(about.follow('about/'))
        sec = doc.by_id('follow')
        self.assertEqual(sec.find('h2').text(), 'Follow')
        self.assertIn('esichak.github.io/personal-website/feed.xml', sec.text())
        self.assertEqual(sec.find('button').text(), 'Copy feed address')
        # it only ever copies: a phone's share sheet (base.js turns a button with data-share into one) would offer the feed
        # as 'this page'
        self.assertNotIn('data-share', sec.find('button').attrs)
        self.assertEqual(sec.find('button')['data-copy'], core.SITE_URL + 'feed.xml')
        raw = [a for a in sec.find_all('a') if a['href'] == '../feed.xml']
        self.assertEqual([(a.text(), a['type']) for a in raw], [('Open feed.xml', 'application/rss+xml')])
        self.assertIn('Prefer email? An RSS-to-email service can turn this feed into messages.', sec.text())
        self.assertNotIn('mailto:', str(sec.text()) + about.follow('about/'))
        self.assertNotIn('rel="me', about.follow('about/'))

    def test_follow_and_contact_with_one(self):
        sec = Doc(about.follow('about/', AUTHOR)).by_id('follow')
        self.assertEqual(sec.find('h2').text(), 'Follow & contact')
        mail = [a for a in sec.find_all('a') if (a['href'] or '').startswith('mailto:')]
        self.assertEqual([(a.text(), a['href'], a.classes) for a in mail], [('Email', 'mailto:' + EMAIL, ['btn'])])
        self.assertIn(EMAIL, [p.text() for p in sec.find_all('p', cls='abo-follow-u')])     # written out, works without a script
        me = [a for a in sec.find_all('a') if a['rel']]
        self.assertEqual([(a.text(), a['href'], a['rel']) for a in me],
                         [('Synthetic Profile', 'https://profile.example.test/synthetic', 'me noopener')])
        # links only: still 'Follow & contact', no mailto
        only = about.follow('about/', {'email': None, 'links': AUTHOR['links']})
        self.assertIn('Follow &amp; contact', only)
        self.assertNotIn('mailto:', only)

    def test_the_about_page_has_the_section_and_the_issue_path(self):
        doc = a11y.page_doc('about/')
        self.assertIsNotNone(doc.by_id('follow'))
        issues = [a for a in doc.find_all('a') if a['href'] == core.REPO_URL + '/issues/new']
        self.assertEqual([a.text() for a in issues], ['open an issue'])


class FooterTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)

    def test_follow_and_source_close_the_site_list(self):
        site = Doc(core.footer('ski/')).find('nav', attrs={'aria-labelledby': 'f-site'})
        self.assertEqual([(a.text(), a['href']) for a in site.find_all('a')][-2:],
                         [('Follow', '../about/#follow'), ('Source on GitHub', core.REPO_URL)])

    def test_one_row_for_the_address_only_when_there_is_one(self):
        self.assertNotIn('mailto:', core.footer('ski/'))
        with mock.patch.object(core, '_AUTHOR', [AUTHOR]):
            brand = Doc(core.footer('ski/')).find('div', cls='f-brand')
        self.assertEqual([(a.text(), a['href']) for a in brand.find_all('a', cls='f-mail')], [(EMAIL, 'mailto:' + EMAIL)])
        rules = a11y.published_rules()[0]
        mail = brand.find('a', cls='f-mail')
        self.assertEqual(a11y.computed(mail, 'min-height', rules, a11y.env(390)), '44px')

    def test_the_repository_is_the_sites_owners(self):
        owner = urlparse(core.REPO_URL).path.strip('/').split('/')[0]
        self.assertEqual(urlparse(core.SITE_URL).hostname, owner + '.github.io')
        self.assertEqual(urlparse(core.REPO_URL).path.strip('/').split('/')[1], urlparse(core.SITE_URL).path.strip('/'))


class AskTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)

    def subject(self, html_):
        a = Doc(html_).find('a', cls='rep-ask')
        self.assertEqual(a.text(), 'Ask about this trip')
        address, _q, query = a['href'].partition('?')
        self.assertEqual(address, 'mailto:' + EMAIL)
        self.assertTrue(query.startswith('subject='))
        return unquote(query[len('subject='):])

    def test_no_address_no_link(self):
        t = {'kind': 'trip', 'title': 'Synthetic', 'date': None}
        self.assertEqual(report.ask_link(t), '')
        for url in a11y.site_pages():
            if not url.endswith('.json'):
                self.assertNotIn('rep-ask', a11y.site_pages()[url], url)

    def test_the_subject_is_the_title_and_the_date(self):
        from datetime import date
        with mock.patch.object(core, '_AUTHOR', [AUTHOR]):
            self.assertEqual(self.subject(report.ask_link({'kind': 'trip', 'title': 'Synthetic & <Twin>', 'date': date(2026, 6, 1)})),
                             'Synthetic & <Twin> (Jun 1, 2026)')
            self.assertEqual(self.subject(report.ask_link({'kind': 'multi-day', 'title': 'Synthetic Tour', 'date': date(2026, 3, 10),
                                                           'end_date': date(2026, 3, 12)})), 'Synthetic Tour (Mar 10–12, 2026)')
            self.assertEqual(self.subject(report.ask_link({'kind': 'planned', 'title': 'Synthetic Goal', 'date': None})),
                             'Synthetic Goal (PLANNED)')
            self.assertEqual(self.subject(report.ask_link({'kind': 'trip', 'title': 'Synthetic', 'date': None})), 'Synthetic')
            raw = report.ask_link({'kind': 'trip', 'title': 'A & B', 'date': None})
        self.assertIn('subject=A%20%26%20B"', raw)                          # quoted, so the & starts no new field

    def test_every_report_carries_it_in_its_title_actions_and_its_phone_row(self):
        import importlib
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        mk = helpers.make_trip
        mk(tmp.name, 'syn-a-story', title='Synthetic Story', activity='hike', date='2026-06-01', track=True, body='Synthetic words.')
        mk(tmp.name, 'syn-a-tour', title='Synthetic Tour', activity='ski', kind='multi-day', date='2026-03-10', end_date='2026-03-11',
           days=[{'date': '2026-03-10', 'body': 'Synthetic day.'}, {'date': '2026-03-11'}])
        mk(tmp.name, 'syn-a-goal', title='Synthetic Goal', activity='hike', kind='planned', track=True)
        helpers.make_series(tmp.name, slug='syn-a-journal', title='Synthetic Journal')
        site = helpers.make_site(helpers.load_dir(tmp.name))
        mod = lambda name: importlib.import_module('sitegen.pages.' + name)  # noqa: E731
        by = site['by_slug']
        with mock.patch.object(core, '_AUTHOR', [AUTHOR]):
            pages = {'story': Doc(mod('report').page(by['syn-a-story'], site).html),
                     'tour': Doc(mod('multiday').page(by['syn-a-tour'], site).html),
                     'journal': Doc(mod('series').page(by['syn-a-journal'], site).html),
                     'goal': Doc(mod('report').goal_page(by['syn-a-goal'], site).html)}
        for key, doc in pages.items():
            with self.subTest(page=key):
                # under the place line, not among the buttons (the review: the button row took it from the title's width)
                self.assertEqual(doc.find('div', cls='rep-actions').find_all('a', cls='rep-ask'), [])
                self.assertEqual(len(doc.find('div', cls='rep-head-t').find('p', cls='rep-ask-p').find_all('a', cls='rep-ask')), 1)
                rows = doc.find_all('div', cls='rep-share')
                if key == 'journal':
                    self.assertEqual(rows, [])                                # the journal keeps its title actions on phones
                else:
                    self.assertEqual(len(rows), 1)
                    self.assertIn('rep-share--ask', rows[0].classes)
                    ask = rows[0].find('a', cls='rep-ask')
                    self.assertIsNot(ask.parent, rows[0].find('span', cls='copy'))
                    self.assertIs(ask.parent, rows[0])                       # outside the copy control

    def test_on_phones_the_share_row_carries_it_and_the_journal_keeps_it_under_its_title(self):
        rules = a11y.published_rules()[0]
        for body, shown_phone in (('p-report', False), ('p-report p-goal', False), ('p-multiday', False), ('p-series', True)):
            doc = Doc('<body class="%s"><main><p class="rep-ask-p"><a class="alink rep-ask">x</a></p></main></body>' % body)
            p = doc.find('p')
            with self.subTest(body=body):
                self.assertEqual(a11y.displayed(p, rules, a11y.env(390)), shown_phone)
                self.assertTrue(a11y.displayed(p, rules, a11y.env(1280)))

    def test_the_phone_row_with_the_link_stays_without_a_script(self):
        rules = a11y.published_rules()[0]
        row = Doc('<main><div class="wrap rep-share rep-share--ask"><span class="copy"></span><a class="alink rep-ask">x</a></div></main>')
        div = row.find('div')
        for scripting, w, shown in (('none', 390, True), ('enabled', 390, True), ('none', 900, False)):
            with self.subTest(scripting=scripting, width=w):
                e = a11y.env(w, scripting=scripting)
                self.assertEqual(a11y.displayed(div, rules, e), shown, a11y.why(div, 'display', rules, e))
        self.assertFalse(a11y.displayed(div.find('span'), rules, a11y.env(390, scripting='none')))


if __name__ == '__main__':
    unittest.main()
