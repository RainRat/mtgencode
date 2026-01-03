import unittest
import random
from lib import transforms
from lib import utils

class TestTransformsRandomization(unittest.TestCase):

    def test_separate_lines_categorization(self):
        lines = [
            "equip {1}",
            "enchant creature",
            "flying",
            "trample",
            "deal 2 damage.",
            "destroy target.",
            "kicker {R}",
            "cycling {2}",
            "countertype % time",
        ]
        text = utils.newline.join(lines)

        prelines, keylines, mainlines, costlines, postlines = transforms.separate_lines(text)

        self.assertIn("equip {1}", prelines)
        self.assertIn("enchant creature", prelines)
        self.assertEqual(len(prelines), 2)

        self.assertIn("flying", keylines)
        self.assertIn("trample", keylines)
        self.assertEqual(len(keylines), 2)

        self.assertIn("deal 2 damage.", mainlines)
        self.assertIn("destroy target.", mainlines)
        self.assertEqual(len(mainlines), 2)

        self.assertIn("kicker {R}", costlines)
        self.assertIn("cycling {2}", costlines)
        self.assertEqual(len(costlines), 2)

        self.assertIn("countertype % time", postlines)
        self.assertEqual(len(postlines), 1)

    def test_separate_lines_modal_choice(self):
        modal_line = "choose one " + utils.dash_marker + " destroy target artifact."
        text = modal_line
        pre, key, main, cost, post = transforms.separate_lines(text)
        self.assertIn(modal_line, main)

    def test_separate_lines_monstrosity(self):
        line = "{4}{G}{G}: monstrosity 2."
        text = line
        pre, key, main, cost, post = transforms.separate_lines(text)
        self.assertIn(line, cost)

    def test_separate_lines_exclusions(self):
        self.assertEqual(transforms.separate_lines(""), ([], [], [], [], []))

        text = "level up {1}" + utils.newline + "level 1-4"
        self.assertEqual(transforms.separate_lines(text), ([], [], [], [], []))

    def test_randomize_choice(self):
        divider = ' ' + utils.bullet_marker + ' '
        valid_choice_str = (utils.choice_open_delimiter + "header" +
                            divider + "OptionA" +
                            divider + "OptionB" +
                            utils.choice_close_delimiter)

        res = transforms.randomize_choice(valid_choice_str)

        self.assertTrue(res.startswith(utils.choice_open_delimiter + "header"))
        self.assertIn("OptionA", res)
        self.assertIn("OptionB", res)

        generated = set()
        for _ in range(20):
             generated.add(transforms.randomize_choice(valid_choice_str))

        self.assertGreater(len(generated), 1)

    def test_randomize_lines_integration(self):
        lines = [
            "enchant creature",
            "flying",
            "trample",
            "deal damage.",
            "kicker {1}"
        ]
        text = utils.newline.join(lines)

        randomized_text = transforms.randomize_lines(text)

        randomized_lines = randomized_text.split(utils.newline)
        self.assertEqual(len(randomized_lines), len(lines))
        for line in lines:
            self.assertIn(line, randomized_lines)

        variants = set()
        for _ in range(20):
            variants.add(transforms.randomize_lines(text))

        self.assertGreater(len(variants), 1)

    def test_randomize_lines_level_up(self):
        text = "level up {1}"
        self.assertEqual(transforms.randomize_lines(text), text)

if __name__ == '__main__':
    unittest.main()
