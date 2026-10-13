import os
import sys
import tempfile
import json
import unittest
from unittest.mock import patch, MagicMock

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
if libdir not in sys.path:
    sys.path.append(libdir)

from cardlib import Card
import sortcards
import utils


class TestSortcardsGaps(unittest.TestCase):
    def test_inclusive_and_exclusive_classes(self):
        kicker_card = Card({
            "name": "Kicker Spell",
            "manaCost": "{1}{R}",
            "types": ["Instant"],
            "text": "Kicker {2} - deal damage.",
            "rarity": "uncommon"
        })
        counter_card = Card({
            "name": "Counter Card",
            "manaCost": "{1}{U}",
            "types": ["Sorcery"],
            "text": "Put a +1/+1 counter on target creature.",
            "rarity": "common"
        })
        counter_card.raw = "Counter Card |cost|{1}{U}|text|% counter #"

        uncast_card = Card({
            "name": "Uncast Spell",
            "manaCost": "{2}{B}",
            "types": ["Sorcery"],
            "text": "This spell is uncast.",
            "rarity": "rare"
        })
        choice_card = Card({
            "name": "Choice Spell",
            "manaCost": "{G}",
            "types": ["Instant"],
            "text": "Choose one = test.",
            "rarity": "common"
        })
        choice_card.raw = "Choice Spell |text|[option1 = test]"

        equip_card = Card({
            "name": "Sword of Test",
            "manaCost": "{2}",
            "types": ["Artifact"],
            "subtypes": ["Equipment"],
            "text": "Equip {2}",
            "rarity": "uncommon"
        })
        leveler_card = Card({
            "name": "Leveler Knight",
            "manaCost": "{W}",
            "types": ["Creature"],
            "text": "Level up {1}",
            "rarity": "rare"
        })
        legendary_card = Card({
            "name": "Legendary Hero",
            "manaCost": "{1}{W}{U}",
            "supertypes": ["Legendary"],
            "types": ["Creature"],
            "text": "Legendary hero text.",
            "rarity": "mythic"
        })

        classes = sortcards.sortcards([
            kicker_card, counter_card, uncast_card,
            choice_card, equip_card, leveler_card, legendary_card
        ])

        self.assertTrue(len(classes['kicker cards']) > 0)
        self.assertTrue(len(classes['counter cards']) > 0)
        self.assertTrue(len(classes['uncast cards']) > 0)
        self.assertTrue(len(classes['choice cards']) > 0)
        self.assertTrue(len(classes['equipment']) > 0)
        self.assertTrue(len(classes['levelers']) > 0)
        self.assertTrue(len(classes['legendary']) > 0)

    def test_exclusive_card_types(self):
        land_card = Card({"name": "Test Land", "types": ["Land"], "rarity": "basic land"})
        instant_card = Card({"name": "Test Instant", "manaCost": "{U}", "types": ["Instant"], "rarity": "common"})
        sorceries_card = Card({"name": "Test Sorcery", "manaCost": "{B}", "types": ["Sorcery"], "rarity": "common"})
        enchantment_card = Card({"name": "Test Enchantment", "manaCost": "{1}{G}", "types": ["Enchantment"], "rarity": "uncommon"})
        artifact_card = Card({"name": "Test Artifact", "manaCost": "{3}", "types": ["Artifact"], "rarity": "uncommon"})
        other_card = Card({"name": "Test Other", "types": ["Dungeon"], "rarity": "special"})

        classes = sortcards.sortcards([
            land_card, instant_card, sorceries_card,
            enchantment_card, artifact_card, other_card
        ])

        self.assertTrue(len(classes['lands']) > 0)
        self.assertTrue(len(classes['instants']) > 0)
        self.assertTrue(len(classes['sorceries']) > 0)
        self.assertTrue(len(classes['enchantments']) > 0)
        self.assertTrue(len(classes['noncreature artifacts']) > 0)
        self.assertTrue(len(classes['other']) > 0)

    def test_colorless_land_and_nonland(self):
        colorless_land = Card({"name": "Wastes", "types": ["Land"], "rarity": "basic land"})
        colorless_nonland = Card({"name": "Sol Ring", "manaCost": "{1}", "types": ["Artifact"], "rarity": "uncommon"})

        classes = sortcards.sortcards([colorless_land, colorless_nonland])

        self.assertTrue(len(classes['colorless land']) > 0)
        self.assertTrue(len(classes['colorless nonland']) > 0)

    def test_color_counts_and_rarities(self):
        zero_color = Card({"name": "Artifact Zero", "manaCost": "{2}", "types": ["Artifact"], "rarity": "common"})
        one_color = Card({"name": "Red Spell", "manaCost": "{R}", "types": ["Instant"], "rarity": "common"})
        two_color = Card({"name": "Izzet Spell", "manaCost": "{U}{R}", "types": ["Instant"], "rarity": "uncommon"})
        three_color = Card({"name": "Esper Charm", "manaCost": "{W}{U}{B}", "types": ["Instant"], "rarity": "uncommon"})
        four_color = Card({"name": "Omnath", "manaCost": "{W}{U}{B}{R}", "types": ["Creature"], "rarity": "mythic"})
        five_color = Card({"name": "Sliver Queen", "manaCost": "{W}{U}{B}{R}{G}", "types": ["Creature"], "rarity": "mythic"})

        special_rarity = Card({"name": "Timeshifted Card", "manaCost": "{1}", "types": ["Artifact"], "rarity": "special"})
        basic_land_rarity = Card({"name": "Island", "types": ["Land"], "rarity": "basic land"})
        unknown_rarity = Card({"name": "Custom Rarity", "manaCost": "{1}", "types": ["Artifact"], "rarity": "unknown_custom_rarity_val"})

        classes = sortcards.sortcards([
            zero_color, one_color, two_color, three_color,
            four_color, five_color, special_rarity, basic_land_rarity, unknown_rarity
        ])

        self.assertTrue(len(classes['zero colors']) > 0)
        self.assertTrue(len(classes['one color']) > 0)
        self.assertTrue(len(classes['two colors']) > 0)
        self.assertTrue(len(classes['three colors']) > 0)
        self.assertTrue(len(classes['four colors']) > 0)
        self.assertTrue(len(classes['five colors']) > 0)
        self.assertTrue(len(classes['special']) > 0)
        self.assertTrue(len(classes['basic land']) > 0)
        self.assertTrue(len(classes['unknown rarity']) > 0)

    def test_cmc_categories(self):
        c0 = Card({"name": "C0", "manaCost": "{0}", "types": ["Artifact"], "rarity": "common"})
        c1 = Card({"name": "C1", "manaCost": "{1}", "types": ["Artifact"], "rarity": "common"})
        c3 = Card({"name": "C3", "manaCost": "{3}", "types": ["Artifact"], "rarity": "common"})
        c4 = Card({"name": "C4", "manaCost": "{4}", "types": ["Artifact"], "rarity": "common"})
        c5 = Card({"name": "C5", "manaCost": "{5}", "types": ["Artifact"], "rarity": "common"})
        c6 = Card({"name": "C6", "manaCost": "{6}", "types": ["Artifact"], "rarity": "common"})
        c7 = Card({"name": "C7", "manaCost": "{7}", "types": ["Artifact"], "rarity": "common"})

        classes = sortcards.sortcards([c0, c1, c3, c4, c5, c6, c7])

        self.assertTrue(len(classes['CMC 0']) > 0)
        self.assertTrue(len(classes['CMC 1']) > 0)
        self.assertTrue(len(classes['CMC 3']) > 0)
        self.assertTrue(len(classes['CMC 4']) > 0)
        self.assertTrue(len(classes['CMC 5']) > 0)
        self.assertTrue(len(classes['CMC 6']) > 0)
        self.assertTrue(len(classes['CMC 7+']) > 0)

    def test_markdown_summary_and_raw_fallback(self):
        card = Card({"name": "Test Summary Card", "manaCost": "{1}{W}", "types": ["Instant"], "rarity": "common"})
        card.raw = ""

        classes_summary = sortcards.sortcards([card], use_summary=True)
        self.assertTrue(any(len(v) > 0 for k, v in classes_summary.items() if v))

        classes_md = sortcards.sortcards([card], use_markdown=True)
        self.assertTrue(any(len(v) > 0 for k, v in classes_md.items() if v))

        classes_raw_fallback = sortcards.sortcards([card], use_markdown=False)
        self.assertTrue(any(len(v) > 0 for k, v in classes_raw_fallback.items() if v))

    def test_dry_run_unnamed_cards(self):
        card = Card({"types": ["Creature"], "power": "1", "toughness": "1", "rarity": "common"})
        card.name = None
        card.raw = "Unnamed raw card string"

        with patch("sys.stdout"):
            with patch("jdecode.mtg_open_file", return_value=[card]):
                sortcards.main("dummy.json", dry_run=True, quiet=True)

    def test_main_encodings(self):
        card_data = {
            "name": "Encoding Test",
            "manaCost": "{1}{R}",
            "types": ["Creature"],
            "power": "2",
            "toughness": "2",
            "rarity": "common"
        }
        card = Card(card_data)

        with tempfile.TemporaryDirectory() as tmpdir:
            for enc in ['named', 'noname', 'old', 'norarity']:
                out = os.path.join(tmpdir, f"out_{enc}.txt")
                with patch("jdecode.mtg_open_file", return_value=[card]):
                    sortcards.main("dummy.json", oname=out, encoding=enc, quiet=True, verbose=False)
                self.assertTrue(os.path.exists(out))

    def test_file_opening_errors(self):
        card = Card({"name": "Test", "types": ["Creature"], "rarity": "common"})
        invalid_path = "/non_existent_folder_xyz_123/output.txt"

        # Test error handling when opening text output file fails
        with patch("jdecode.mtg_open_file", return_value=[card]):
            with patch("sys.stderr"):
                with self.assertRaises(SystemExit) as cm:
                    sortcards.main("dummy.json", oname=invalid_path, verbose=True, quiet=True)
                self.assertEqual(cm.exception.code, 1)

        # Test error handling when opening CSV output file fails
        invalid_csv_path = "/non_existent_folder_xyz_123/output.csv"
        with patch("jdecode.mtg_open_file", return_value=[card]):
            with patch("sys.stderr"):
                with self.assertRaises(SystemExit) as cm:
                    sortcards.main("dummy.json", oname=invalid_csv_path, use_csv=True, verbose=True, quiet=True)
                self.assertEqual(cm.exception.code, 1)

    def test_main_sorting_and_limiting(self):
        c1 = Card({"name": "Alpha", "manaCost": "{1}", "types": ["Artifact"], "rarity": "common"})
        c2 = Card({"name": "Beta", "manaCost": "{2}", "types": ["Artifact"], "rarity": "common"})

        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out_sort.txt")
            with patch("jdecode.mtg_open_file", return_value=[c2, c1]):
                sortcards.main("dummy.json", oname=out, sort="name", limit=1, quiet=False, verbose=True, use_color=True)
            self.assertTrue(os.path.exists(out))
            with open(out, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn("alpha", content.lower())

    def test_cli_parsing_options(self):
        card = Card({"name": "CLI Card", "manaCost": "{G}", "types": ["Creature"], "rarity": "common"})
        with tempfile.TemporaryDirectory() as tmpdir:
            out_txt = os.path.join(tmpdir, "cli_out.txt")
            test_args = [
                "sortcards.py", "dummy.json", "-o", out_txt,
                "-e", "named", "-n", "10", "--sort", "name", "--reverse",
                "--shuffle", "--seed", "123", "-S", "--md", "-v"
            ]
            with patch("sys.argv", test_args):
                with patch("jdecode.mtg_open_file", return_value=[card]):
                    sortcards.cli()
            self.assertTrue(os.path.exists(out_txt))


if __name__ == '__main__':
    unittest.main()
