import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Add lib directory to sys.path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import cardlib
import sortcards
import utils


class TestSortCardsGaps(unittest.TestCase):

    def test_sortcards_various_categories(self):
        # Test split card (multicards)
        card_bside = cardlib.Card({
            "name": "Fire",
            "manaCost": "{1}{R}",
            "types": ["Instant"],
            "rarity": "uncommon"
        })
        card_bside.bside = cardlib.Card({
            "name": "Ice",
            "manaCost": "{1}{U}",
            "types": ["Instant"],
            "rarity": "uncommon"
        })
        card_bside.raw = f"Fire{utils.bsidesep}Ice"

        # Test inclusive features: kicker, counter, uncast, choice, equipment, leveler, legendary
        card_kicker = cardlib.Card({
            "name": "Kicker Spell",
            "manaCost": "{2}",
            "types": ["Sorcery"],
            "text": "Kicker {1}. If kicked, deal 3 damage.",
            "rarity": "common"
        })

        card_counter = cardlib.Card({
            "name": "Counter Card",
            "manaCost": "{1}",
            "types": ["Creature"],
            "text": "Put a +1/+1 counter on this.",
            "rarity": "common"
        })
        card_counter.raw = "Counter Card % +1/+1 counter #"

        card_uncast = cardlib.Card({
            "name": "Uncast Card",
            "manaCost": "{3}",
            "types": ["Instant"],
            "text": "This card is uncastable from hand.",
            "rarity": "common"
        })

        card_choice = cardlib.Card({
            "name": "Choice Card",
            "manaCost": "{1}",
            "types": ["Instant"],
            "text": "Choose one — [mode A] or [mode B].",
            "rarity": "common"
        })
        card_choice.raw = "Choice Card [mode A] = mode B"

        card_equipment = cardlib.Card({
            "name": "Short Sword",
            "manaCost": "{1}",
            "types": ["Instant"],
            "subtypes": ["Equipment"],
            "text": "Equipped creature gets +1/+1. Equip {1}.",
            "rarity": "common"
        })

        card_leveler = cardlib.Card({
            "name": "Level Up Knight",
            "manaCost": "{1}",
            "types": ["Creature"],
            "text": "Level up {2}. level & 2-4: 3/3",
            "rarity": "uncommon"
        })

        card_legendary = cardlib.Card({
            "name": "Legendary Hero",
            "manaCost": "{2}{W}{U}{B}{R}{G}",
            "supertypes": ["Legendary"],
            "types": ["Creature"],
            "rarity": "mythic",
            "power": "6",
            "toughness": "6"
        })

        # Exclusive categories: enchantment, noncreature artifact, other
        card_enchantment = cardlib.Card({
            "name": "Pacificism",
            "manaCost": "{1}",
            "types": ["Enchantment"],
            "rarity": "common"
        })

        card_artifact = cardlib.Card({
            "name": "Sol Ring",
            "manaCost": "{1}",
            "types": ["Artifact"],
            "rarity": "uncommon"
        })

        card_other = cardlib.Card({
            "name": "Strange Card",
            "manaCost": "{0}",
            "types": ["Tribal"],
            "rarity": "special"
        })

        # Colors: Black, Red, Green, Colorless land
        card_black = cardlib.Card({"name": "B", "manaCost": "{B}", "types": ["Instant"], "rarity": "common"})
        card_red = cardlib.Card({"name": "R", "manaCost": "{R}", "types": ["Instant"], "rarity": "common"})
        card_green = cardlib.Card({"name": "G", "manaCost": "{G}", "types": ["Instant"], "rarity": "common"})
        card_colorless_land = cardlib.Card({"name": "Wastes", "types": ["Land"], "rarity": "basic land"})

        # Multi-color counts: 2, 3, 4, 5
        card_2c = cardlib.Card({"name": "2C", "manaCost": "{W}{U}", "types": ["Instant"], "rarity": "common"})
        card_3c = cardlib.Card({"name": "3C", "manaCost": "{W}{U}{B}", "types": ["Instant"], "rarity": "common"})
        card_4c = cardlib.Card({"name": "4C", "manaCost": "{W}{U}{B}{R}", "types": ["Instant"], "rarity": "common"})
        card_5c = cardlib.Card({"name": "5C", "manaCost": "{W}{U}{B}{R}{G}", "types": ["Instant"], "rarity": "common"})

        # CMC 6 and CMC 7+
        card_cmc6 = cardlib.Card({"name": "CMC6", "manaCost": "{6}", "types": ["Instant"], "rarity": "common"})
        card_cmc7 = cardlib.Card({"name": "CMC7", "manaCost": "{7}", "types": ["Instant"], "rarity": "unknown"})

        cards = [
            card_bside, card_kicker, card_counter, card_uncast, card_choice,
            card_equipment, card_leveler, card_legendary, card_enchantment,
            card_artifact, card_other, card_black, card_red, card_green,
            card_colorless_land, card_2c, card_3c, card_4c, card_5c,
            card_cmc6, card_cmc7
        ]

        classes = sortcards.sortcards(cards, verbose=False, use_markdown=False, use_color=True)

        self.assertEqual(len(classes['multicards']), 1)
        self.assertIn(' // ', classes['multicards'][0])
        self.assertEqual(len(classes['kicker cards']), 1)
        self.assertEqual(len(classes['counter cards']), 1)
        self.assertEqual(len(classes['uncast cards']), 1)
        self.assertEqual(len(classes['choice cards']), 1)
        self.assertEqual(len(classes['equipment']), 1)
        self.assertEqual(len(classes['levelers']), 1)
        self.assertEqual(len(classes['legendary']), 1)
        self.assertEqual(len(classes['enchantments']), 1)
        self.assertEqual(len(classes['noncreature artifacts']), 1)
        self.assertEqual(len(classes['other']), 1)
        self.assertEqual(len(classes['black']), 5)  # legend + black + 3c + 4c + 5c
        self.assertEqual(len(classes['red']), 4)    # legend + red + 4c + 5c
        self.assertEqual(len(classes['green']), 3)  # legend + green + 5c
        self.assertEqual(len(classes['colorless land']), 1)
        self.assertEqual(len(classes['two colors']), 1)
        self.assertEqual(len(classes['three colors']), 1)
        self.assertEqual(len(classes['four colors']), 1)
        self.assertEqual(len(classes['five colors']), 2)  # legend + 5c
        self.assertEqual(len(classes['mythic']), 1)
        self.assertEqual(len(classes['special']), 1)
        self.assertEqual(len(classes['basic land']), 1)
        self.assertEqual(len(classes['unknown rarity']), 1)
        self.assertEqual(len(classes['CMC 6']), 1)
        self.assertEqual(len(classes['CMC 7+']), 2)  # legend + cmc7

    def test_main_encodings_and_options(self):
        card = cardlib.Card({"name": "Test Card", "manaCost": "{1}", "types": ["Artifact"], "rarity": "common"})

        for enc in ['named', 'noname', 'old', 'norarity']:
            with patch("jdecode.mtg_open_file", return_value=[card]):
                with patch("sys.stdout"):
                    sortcards.main("dummy.json", encoding=enc, limit=1, sort="name", quiet=True)

    def test_main_verbose_json_and_color_text(self):
        card = cardlib.Card({"name": "Colored Card", "manaCost": "{1}{R}", "types": ["Sorcery"], "rarity": "common"})

        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, "out.json")
            txt_file = os.path.join(tmpdir, "out.txt")

            with patch("jdecode.mtg_open_file", return_value=[card]):
                # Test verbose JSON output
                sortcards.main("dummy.json", json_file, verbose=True, use_json=True)
                self.assertTrue(os.path.exists(json_file))

                # Test ANSI color text output
                sortcards.main("dummy.json", txt_file, verbose=True, use_color=True, quiet=False)
                self.assertTrue(os.path.exists(txt_file))

    def test_file_open_errors(self):
        card = cardlib.Card({"name": "Test Card", "manaCost": "{1}", "types": ["Artifact"], "rarity": "common"})

        invalid_path = "/nonexistent_dir/test_output.txt"

        with patch("jdecode.mtg_open_file", return_value=[card]):
            with patch("sys.stderr"):
                with self.assertRaises(SystemExit) as cm1:
                    sortcards.main("dummy.json", invalid_path, use_csv=True)
                self.assertEqual(cm1.exception.code, 1)

                with self.assertRaises(SystemExit) as cm2:
                    sortcards.main("dummy.json", invalid_path, use_csv=False)
                self.assertEqual(cm2.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
