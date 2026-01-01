import unittest
from lib import transforms
from lib import utils

class TestTransformsCardname(unittest.TestCase):
    def test_basic_replacement(self):
        # Basic case: name appears in text
        name = "dark confidant"
        text = "at the beginning of your upkeep, reveal the top card of your library and put that card into your hand. you lose life equal to its mana value. dark confidant is a 2/1 creature."
        expected = "at the beginning of your upkeep, reveal the top card of your library and put that card into your hand. you lose life equal to its mana value. " + utils.this_marker + " is a 2/1 creature."
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

    def test_edge_cases_keywords(self):
        # 'sacrifice' is a keyword, shouldn't be replaced unless it's the card name
        text = "sacrifice a creature."
        expected = utils.this_marker + " a creature."
        self.assertEqual(transforms.text_pass_2_cardname(text, "sacrifice"), expected)

        # 'fear' is skipped explicitly
        text = "fear cannot be blocked except by artifact creatures and black creatures."
        self.assertEqual(transforms.text_pass_2_cardname(text, "fear"), text)

    def test_legend_nicknames(self):
        # Full name replacement with comma (implicit nickname detection)
        name = "skithiryx, the blight dragon"
        text = "flying, infect, haste. regenerate skithiryx."
        expected = "flying, infect, haste. regenerate " + utils.this_marker + "."
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

    def test_overrides(self):
        # Partial name replacement (explicit overrides list)
        overrides = {
            "crovax the cursed": "crovax",
            "rashka the slayer": "rashka",
            "phage the untouchable": "phage",
            "shimatsu the bloodcloaked": "shimatsu",
            "1996 world champion": "world champion",
            "axelrod gunnarson": "axelrod",
            "hazezon tamar": "hazezon",
            "rubinia soulsinger": "rubinia",
            "rasputin dreamweaver": "rasputin",
            "hivis of the scale": "hivis"
        }

        for fullname, shortname in overrides.items():
            text = f"{shortname} enters the battlefield."
            expected = f"{utils.this_marker} enters the battlefield."
            self.assertEqual(transforms.text_pass_2_cardname(text, fullname), expected, f"Failed for {fullname}")

    def test_planeswalker_pronouns(self):
        name = "jace beleren"

        # "to him."
        text = "prevent all damage that would be dealt to him."
        expected = "prevent all damage that would be dealt to " + utils.this_marker + "."
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

        # "to him this"
        text = "prevent all damage that would be dealt to him this turn."
        expected = "prevent all damage that would be dealt to " + utils.this_marker + " this turn."
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

        # "to himself"
        text = "jace beleren deals 2 damage to himself."
        expected = utils.this_marker + " deals 2 damage to itself."
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

        # "he's"
        text = "as long as he's on the battlefield"
        expected = "as long as " + utils.this_marker + " is on the battlefield"
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

    def test_negative_replacements(self):
        # These verify that specific phrases restore the card name instead of leaving the marker
        name = "grizzly bears"

        # "named ~" -> "named [Name]"
        text = "creatures named grizzly bears get +1/+1."
        # Logic: First replaces "grizzly bears" with "~". Then sees "named ~" and replaces with "named grizzly bears".
        expected = text
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

        # "name is still ~"
        text = "its name is still grizzly bears."
        expected = text
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

    def test_context_specific_negatives(self):
        # keeper of
        name = "progenitus"
        text = "named keeper of progenitus"
        self.assertEqual(transforms.text_pass_2_cardname(text, name), text)

        # kobolds of
        name = "kher keep"
        text = "named kobolds of kher keep"
        self.assertEqual(transforms.text_pass_2_cardname(text, name), text)

        # sword of kaldra
        # This handles lists where the card name appears after "named sword of kaldra, "
        name = "helm of kaldra"
        text = "equipment named sword of kaldra, helm of kaldra, or shield of kaldra"
        self.assertEqual(transforms.text_pass_2_cardname(text, name), text)

if __name__ == '__main__':
    unittest.main()
