"""Phase 16 (docs/redesign-c/PROMPT.md): the foundations of the Alpine design.

- The footer's facts line names the service the recordings came through only when every published recording names
  the same one (core.site_via, content.stats_source); otherwise it says nothing of it.
- The committed renders wear the new design without a redraw: core.frag turns the renders' inline mono and the
  profile's area colour into tokens, and build.css_bundle turns mapkit's sans, the old one and the new one, into
  var(--sans).
- The fonts: core.FONTS asks for Alpine's three families, tools/fonts.py FACES names their files, and the two faces
  core.FONT_PRELOADS names are among them.
- The tokens: every text colour of base.css passes 4.5:1 on every background it sits on (read from the stylesheet, so a
  later change to a token is held to the rule).
Synthetic trips only (helpers.make_trip).
"""
import importlib
import os
import re
import tempfile
import unittest

import helpers
from helpers import Doc

from sitegen import core
import mapkit

tearDownModule = helpers.no_region_pages_left


def read(*parts):
    with open(os.path.join(helpers.ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


class SiteViaTests(unittest.TestCase):

    def setUp(self):
        helpers.keep_state(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name

    def trips(self, *specs):
        out = []
        for i, meta in enumerate(specs):
            slug = 'syn-via-%d' % i
            track = meta.pop('track', True)
            helpers.make_trip(self.root, slug, date='2026-0%d-01' % (i + 1), track=track, **meta)
            out.append(helpers.load(self.root, slug))
        return out

    def test_every_recording_via_one_service_names_it(self):
        ts = self.trips({'strava_id': '1001'}, {'strava_id': '1002'}, {'track': False})   # a report without a track does not count
        self.assertEqual(core.site_via(ts), 'Strava')
        helpers.make_site(ts)
        facts = Doc(core.footer('')).find('span', cls='f-facts')
        self.assertEqual(helpers.plain_text(facts.text()),
                         'BASED IN LAKE TAHOE, AVALANCHE TRAINING: AIARE 2, GPS RECORDINGS VIA STRAVA')

    def test_a_recording_without_a_service_or_with_another_names_none(self):
        self.assertIsNone(core.site_via(self.trips({'strava_id': '1001'}, {})))
        self.assertIsNone(core.site_via(self.trips({'strava_id': '1003'}, {'source': 'Garmin'})))
        self.assertEqual(core.site_via(self.trips({'source': 'Garmin'}, {'source': 'Garmin'})), 'Garmin')
        self.assertIsNone(core.site_via([]))
        ts = self.trips({}, {})
        helpers.make_site(ts)
        facts = Doc(core.footer('')).find('span', cls='f-facts')
        self.assertNotIn('RECORDINGS', facts.text())
        self.assertIn('AVALANCHE TRAINING: AIARE 2', facts.text())


class RenderRewriteTests(unittest.TestCase):

    def test_frag_turns_the_renders_mono_and_profile_fill_into_tokens(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'x.svg.html')
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write('<svg><text style="font: 600 12px/1 %s">3</text><path style="fill: #E2DFD6"/>'
                         '<path class="pf-line" style="stroke: {{route}}"/></svg>' % mapkit.MONO)
            s = core.frag(p, '')
        self.assertIn('font: 600 12px/1 var(--mono)', s)
        self.assertIn('fill: var(--profile-fill)', s)
        self.assertIn('stroke: var(--route)', s)                  # the line stays the route's; base.css draws a chart's in ink
        self.assertNotIn('Geist', s)

    def test_the_bundle_names_no_font_stack_of_its_own_in_the_map_rules(self):
        build = importlib.import_module('build')
        css = build.css_bundle()
        self.assertIn(mapkit.SANS, mapkit.MAP_CSS)                       # mapkit's rules name the sans ...
        # ... and the bundle names the token instead: the stack stands once, where base.css defines --sans
        self.assertEqual(css.count(mapkit.SANS), 1)
        self.assertIn('--sans: ' + mapkit.SANS + ';', css)
        self.assertNotIn("Archivo, 'Helvetica Neue', system-ui, sans-serif", css)
        self.assertNotIn(mapkit.MONO, css)
        self.assertIn('.mk-hut{font:600 12px/1 var(--sans)', css)
        self.assertIn('.pf-ax{font:400 11px/1 var(--mono)', css)
        # the old stack's replacement stays exactly as it was (renders drawn before Phase 16 name it)
        self.assertIn(""".replace("Archivo, 'Helvetica Neue', system-ui, sans-serif", 'var(--sans)')""",
                      read('tools', 'build.py'))

    def test_a_chart_line_is_ink_over_the_routes_red(self):
        css = read('assets', 'css', 'base.css')
        self.assertIn('.cv .pf-line { stroke: var(--ink) !important; stroke-width: 1.5px; }', css)
        # the chart keys draw what the chart draws: an ink line, the profile's grey (the review of Phase 16)
        for key in ('fill', 'speed'):
            self.assertIn('stroke:var(--ink)', core.KEY_SYMBOLS[key][1], key)
            self.assertNotIn('var(--route)', core.KEY_SYMBOLS[key][1], key)
        for key in ('fill', 'hatch'):
            self.assertIn('fill:var(--profile-fill)', core.KEY_SYMBOLS[key][1], key)

    def test_frag_turns_the_multi_day_profiles_tints_and_halos_into_tokens(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'x.svg.html')
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write('<svg><path style="fill: #EAE7DF"/><text style="fill: #16171A; stroke: #F2F1EC; stroke-width: 3px">D1</text></svg>')
            s = core.frag(p, '')
        self.assertIn('fill: var(--surface)', s)
        self.assertIn('stroke: var(--paper)', s)


class FontTests(unittest.TestCase):

    def test_the_address_the_faces_and_the_preloads_agree(self):
        fonts = importlib.import_module('fonts')
        self.assertIn('family=Instrument+Serif:ital@0;1', core.FONTS)
        self.assertIn('family=Inter:wght@400..600', core.FONTS)
        self.assertIn('family=IBM+Plex+Mono:wght@400;500', core.FONTS)
        self.assertEqual([f[0] for f in fonts.FACES], ['Instrument Serif', 'Instrument Serif', 'Inter', 'IBM Plex Mono', 'IBM Plex Mono'])
        files = {f[3] for f in fonts.FACES}
        self.assertEqual(len(files), len(fonts.FACES))
        self.assertEqual([p.split('/')[-1] for p in core.FONT_PRELOADS], ['instrument-serif-latin.woff2', 'inter-latin.woff2'])
        self.assertTrue(all(p.split('/')[-1] in files for p in core.FONT_PRELOADS))
        self.assertEqual(set(f[4] for f in fonts.FACES), set(fonts.LICENSES))
        # base.css names the same three families first in its stacks
        css = read('assets', 'css', 'base.css')
        for var, fam in (('--serif', "'Instrument Serif'"), ('--sans', 'Inter'), ('--mono', "'IBM Plex Mono'")):
            self.assertRegex(css, r'%s: %s,' % (re.escape(var), re.escape(fam)))


def _lum(h):
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class TokenContrastTests(unittest.TestCase):

    def tokens(self):
        css = read('assets', 'css', 'base.css')
        root = css[css.index(':root {'):css.index('}', css.index(':root {'))]
        return dict(re.findall(r'(--[\w-]+): (#[0-9A-Fa-f]{6})', root))

    def test_every_text_colour_passes_on_every_background(self):
        tk = self.tokens()
        self.assertEqual((tk['--paper'], tk['--ink'], tk['--ink-2'], tk['--ink-3']), ('#FFFFFF', '#111111', '#5E5E5E', '#6B6B6B'))
        for text in ('--ink', '--ink-2', '--ink-3'):
            for ground in ('--paper', '--surface', '--sunk', '--map-paper', '--profile-fill'):
                with self.subTest(text=text, ground=ground):
                    self.assertGreaterEqual(contrast(tk[text], tk[ground]), 4.5)
        self.assertGreaterEqual(contrast(tk['--paper'], tk['--ink']), 4.5)              # white words on an ink button or chip
        # the white text over a photo on the scrim's darkest stop, over the lightest photo there is (white): #454545
        self.assertGreaterEqual(contrast('#FFFFFF', '#454545'), 4.5)
        self.assertIn('--scrim: linear-gradient(180deg, rgba(17, 17, 17, 0) 40%, rgba(17, 17, 17, 0.78) 100%);',
                      read('assets', 'css', 'base.css'))


if __name__ == '__main__':
    unittest.main()
