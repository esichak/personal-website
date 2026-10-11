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
SWITCH = ('The <span class="abo-nw">MI | KM</span> switch changes every page to kilometers and meters, and this browser '
          'remembers the choice.')


class UnitsSentenceTests(unittest.TestCase):

    def test_the_sentence_about_the_switch_is_one_element_and_the_first_sentence_is_outside_it(self):
        block = about.units_block()
        self.assertEqual(block.count('<span class="abo-units-how">%s</span>' % SWITCH), 1)
        self.assertIn('<p class="abo-p">%s <span class="abo-units-how">' % FIRST, block)
        self.assertEqual(block.count('class="units abo-units"'), 1)

    def test_the_words_are_what_they_were(self):
        text = re.sub(r'<[^>]+>', '', about.units_block())
        self.assertIn(FIRST + ' The MI | KM switch changes every page to kilometers and meters, and this browser remembers the choice.', text)

    def test_the_published_stylesheet_hides_it_only_without_scripting(self):
        css = build.css_bundle()
        rules = re.findall(r'\.abo-units-how\s*\{[^}]*\}', css)
        self.assertEqual(rules, ['.abo-units-how { display: none; }'])
        at = css.index(rules[0])
        self.assertTrue(css[:at].rstrip().endswith('@media (scripting: none) {'), css[at - 60:at])


if __name__ == '__main__':
    unittest.main()
