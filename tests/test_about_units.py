"""The About page's Units section without JavaScript: the MI | KM switch is hidden (assets/css/base.css), so the sentence
that says what the switch does is hidden with it (assets/css/pages/about.css). The first sentence, which is true either
way, stays."""
import importlib
import re
import unittest

import helpers  # noqa: F401  (puts tools/ and tools/lib on the path)

build = importlib.import_module('build')
about = importlib.import_module('sitegen.pages.about')

FIRST = 'Distances and heights are shown in miles and feet by default.'
# Phase 13A (gap6-03): a browser set to another language than English starts in kilometers, which the script decides
SWITCH = ('Browsers set to a language other than English start in kilometers and meters. The <span class="abo-nw">MI | KM</span> '
          'switch changes every page, and this browser remembers the choice.')


class UnitsSentenceTests(unittest.TestCase):

    def test_the_sentence_about_the_switch_is_one_element_and_the_first_sentence_is_outside_it(self):
        block = about.units_block()
        self.assertEqual(block.count('<span class="abo-units-how">%s</span>' % SWITCH), 1)
        self.assertIn('<p class="abo-p">%s <span class="abo-units-how">' % FIRST, block)
        self.assertEqual(block.count('class="units abo-units"'), 1)

    def test_the_words_are_what_they_were(self):
        text = re.sub(r'<[^>]+>', '', about.units_block())
        self.assertIn(FIRST + ' Browsers set to a language other than English start in kilometers and meters. The MI | KM switch '
                      'changes every page, and this browser remembers the choice.', text)

    def test_the_published_stylesheet_hides_it_only_without_scripting(self):
        # without scripting, and (Phase 13A, resilience-01) when the bundle did not run: <html> then lacks 'js'
        css = build.css_bundle()
        rules = [' '.join(r.split()) for r in re.findall(r'[^{};/]*\.abo-units-how\s*\{[^}]*\}', css)]
        self.assertEqual(rules, ['.abo-units-how { display: none; }', ':where(html:not(.js)) .abo-units-how { display: none; }'])
        at = css.index('.abo-units-how { display: none; }')
        self.assertTrue(css[:at].rstrip().endswith('@media (scripting: none) {'), css[at - 60:at])


if __name__ == '__main__':
    unittest.main()
