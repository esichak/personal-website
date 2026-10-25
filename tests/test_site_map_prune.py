"""The build leaves a gone trip's own pin and line out of the site maps (Phase 8, gap7-03; decision 12.8): core.gone_keys
names the keys of a map's entry whose trip is no longer a published trip with a track or an active goal, and
core.frag(..., drop=keys) removes them through core.drop_keys. The overlay here is made from tools/lib/mapkit.py's own
strings (pin_svg, line_links, and the line groups as render_map writes them), and a test reads mapkit's source for those
openings, so a change to its markup fails here before it lets a gone trip's pin through. Slugs start with 'synm-'."""
import contextlib
import importlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import helpers
from sitegen import core

tearDownModule = helpers.no_region_pages_left      # GoneKeysTests registers a site: no region page may stay registered after it

mapkit = importlib.import_module('mapkit')
goals = importlib.import_module('goals')
build = importlib.import_module('build')


def pin(key, title='Synthetic pin', x=20.0, y=30.0):
    """A trip's own pin, as render_map writes one (mapkit.py: the a.mk-pin template around pin_svg)."""
    return ('<a class="mk-pin" href="@@ROOT@@trips/%s/" data-key="%s" aria-label="%s"><title>%s</title>'
            '<circle class="mk-hit" cx="%.1f" cy="%.1f" r="%d" style="fill: transparent"/>%s</a>'
            % (key, key, title, title, x, y, 16, mapkit.pin_svg(x, y, 'HIK')))


def line(key, n=1, opacity=0.9):
    """A trip's line, cased, as render_map writes it in style 'cat' (one geometry drawn twice through <use>)."""
    return ('<g class="mk-cat" data-key="%s" style="opacity: %s"><defs><path id="tk-%d" d="M0 0L9 9"/></defs>'
            '<use href="#tk-%d" class="mk-case" style="stroke-width: 5.5"/><use href="#tk-%d" class="gl-trk" '
            'style="stroke: #4A7FB0; stroke-width: 2.5"/></g>' % (key, opacity, n, n, n))


def disc(key):
    """A day a few pixels across, drawn as a spot (render_map's tiny_disc)."""
    return '<g class="mk-cat" data-key="%s" style="opacity: 1"><circle cx="5.0" cy="5.0" r="3" style="fill: #4A7FB0; stroke: #EEECE6; stroke-width: 1.5"/></g>' % key


def planned(key, n=9):
    return ('<g class="mk-cat mk-planned" data-key="%s"><defs><path id="tk-%d" d="M1 1L8 8"/></defs><use href="#tk-%d" '
            'class="mk-case" style="stroke-width: 3.5; stroke: #EEECE6"/><use href="#tk-%d" class="mk-trk" style="stroke: #66686D"/></g>'
            % (key, n, n, n))


def cluster(keys, titles):
    return ('<g class="mk-cluster" aria-hidden="true" data-keys="%s"><title>%s</title><circle class="mk-hit" cx="50.0" cy="50.0" '
            'r="16" style="fill: transparent"/><text x="50.0" y="50.5">%d</text></g>' % (' '.join(keys), '; '.join(titles), len(keys)))


JOURNAL_LINE = 'synm-journal:synthetic-trail'


def overlay():
    return ('<svg width="400" height="300" viewBox="0 0 400 300">'
            + line('synm-gone', 1) + line('synm-kept', 2) + disc('synm-spot') + planned('synm-goal', 3)
            + line(JOURNAL_LINE, 4)
            + ''.join(mapkit.line_links({JOURNAL_LINE: {'href': '@@ROOT@@trips/synm-journal/#day-2', 'title': 'Synthetic Trail',
                                                        'ids': ['tk-4']}}))
            + pin('synm-gone') + pin('synm-kept')
            + cluster(['synm-gone', 'synm-merged'], ['Synthetic Gone', 'Synthetic Merged'])
            + '</svg>')


class DropKeysTests(unittest.TestCase):

    def setUp(self):
        p = mock.patch.object(core, '_DROP_WARNED', set())
        p.start()
        self.addCleanup(p.stop)

    def drop(self, s, keys, where='rendered/site/region-synthetic-desktop.svg.html'):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = core.drop_keys(s, keys, where)
        return out, err.getvalue()

    def test_a_gone_trips_pin_and_line_are_left_out_and_the_rest_is_as_drawn(self):
        s = overlay()
        out, err = self.drop(s, ['synm-gone'])
        self.assertEqual(err, '')
        self.assertNotIn('data-key="synm-gone"', out)
        self.assertEqual(out, s.replace(pin('synm-gone'), '').replace(line('synm-gone', 1), ''))
        # the cluster keeps the trip in its keys, its title and its count until a render
        self.assertIn(cluster(['synm-gone', 'synm-merged'], ['Synthetic Gone', 'Synthetic Merged']), out)
        self.assertIn(pin('synm-kept'), out)
        self.assertIn(line('synm-kept', 2), out)

    def test_a_spot_a_goal_and_a_journals_line_and_link(self):
        s = overlay()
        out, _err = self.drop(s, ['synm-spot', 'synm-goal', JOURNAL_LINE])
        self.assertNotIn('data-key="synm-spot"', out)
        self.assertNotIn('data-key="synm-goal"', out)
        self.assertNotIn('data-key="%s"' % JOURNAL_LINE, out)
        self.assertNotIn('class="mk-line"', out)            # the link went with the line it draws over
        self.assertNotIn('#tk-4', out)
        self.assertIn('id="tk-2"', out)
        self.assertEqual(out.count('<g '), s.count('<g ') - 3)

    def test_a_key_is_compared_whole(self):
        s = line('synm-a', 1) + line('synm-ab', 2) + pin('synm-ab')
        out, _err = self.drop(s, ['synm-a'])
        self.assertEqual(out, line('synm-ab', 2) + pin('synm-ab'))

    def test_nothing_to_drop_changes_nothing(self):
        s = overlay()
        self.assertEqual(self.drop(s, [])[0], s)
        self.assertEqual(self.drop(s, ())[0], s)

    def test_a_key_with_nothing_to_leave_out_is_said_once_per_map(self):
        s = overlay()
        out, err = self.drop(s, ['synm-gone', 'synm-never-drawn'])
        self.assertNotIn('data-key="synm-gone"', out)
        self.assertEqual(err.count('\n'), 1)
        self.assertIn('rendered/site/region-synthetic-desktop.svg.html', err)
        self.assertIn('synm-never-drawn', err)
        self.assertIn("mapkit's markup", err)
        _out, again = self.drop(s, ['synm-never-drawn'])                       # another page showing the same map
        self.assertEqual(again, '')
        _out, other = self.drop(s, ['synm-never-drawn'], 'rendered/site/region-synthetic-phone.svg.html')
        self.assertEqual(other.count('\n'), 1)

    def test_mapkit_still_writes_the_openings_drop_keys_looks_for(self):
        with open(mapkit.__file__, encoding='utf-8') as fh:
            src = fh.read()
        for opening in ("'<a class=\"mk-pin\" href=\"%s\" data-key=\"%s\"", "'<a class=\"mk-line\" href=\"%s\" data-key=\"%s\"",
                        "'<g class=\"mk-cat\"%s style=\"opacity: %s\">' % (' data-key=\"%s\"'",
                        "'<g class=\"mk-cat mk-planned\" data-key=\"%s\">%s</g>'"):
            with self.subTest(opening=opening[:30]):
                self.assertIn(opening, src)
        self.assertEqual([o for o, _c in core._DROP_OPEN], ['<a class="mk-pin" ', '<a class="mk-line" ', '<g class="mk-cat'])

    def test_frag_drops_before_it_namespaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'region-synthetic-desktop.svg.html')
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(overlay())
            with mock.patch.object(core, 'ROOT', tmp):
                got = core.frag(path, 'map/', 'rg', drop=['synm-gone'])
                whole = core.frag(path, 'map/', 'rg')
        self.assertNotIn('data-key="synm-gone"', got)
        self.assertIn('data-key="synm-gone"', whole)
        self.assertIn('id="rg-tk-2"', got)
        self.assertIn('href="../trips/synm-kept/"', got)


class GoneKeysTests(unittest.TestCase):
    """core.gone_keys against a registered synthetic site: a report with a track, one without, a draft (never loaded),
    a removed folder, an active goal, an archived one, and a journal."""

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = tmp.name
        mk = helpers.make_trip
        mk(root, 'synm-kept', title='Synthetic Kept', date='2026-01-02', track=True)
        mk(root, 'synm-trackless', title='Synthetic Trackless', date='2026-01-03')
        mk(root, 'synm-draft', title='Synthetic Draft', date='2026-01-04', track=True, draft=True)
        helpers.make_series(root, slug='synm-journal', title='Synthetic Journal', written_day=None)
        for slug, archived in (('synm-goal', False), ('synm-done', True)):
            folder = mk(root, slug, title='Synthetic ' + slug, kind='planned', track=True)
            with open(os.path.join(folder, 'goal.json'), 'w', encoding='utf-8') as fh:
                json.dump(dict(goals.defaults(), archived=archived), fh)
        self.site = build.site_of(helpers.load_dir(root))
        self.entry = {'trips': ['synm-kept', 'synm-trackless', 'synm-draft', 'synm-removed', 'synm-goal', 'synm-done'],
                      'journals': [{'slug': 'synm-journal', 'key': 'synm-journal:part-a'},
                                   {'slug': 'synm-old-journal', 'key': 'synm-old-journal:part-b'}]}

    def test_nothing_is_gone_until_a_site_is_registered(self):
        core._ON_MAPS[0] = None
        self.assertEqual(list(core.gone_keys(self.entry)), [])

    def test_the_keys_of_trips_that_are_no_longer_on_the_site(self):
        core.register_site(self.site)
        self.assertEqual(core.gone_keys(self.entry),
                         ['synm-trackless', 'synm-draft', 'synm-removed', 'synm-done', 'synm-old-journal:part-b'])
        self.assertEqual(core.gone_keys({}), [])
        self.assertEqual(core.gone_keys(None), ())
        self.assertEqual(core.gone_keys({'trips': None, 'journals': [None, {'key': 5}]}), [])


if __name__ == '__main__':
    unittest.main()
