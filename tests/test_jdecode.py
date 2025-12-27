import json
import os
import sys
import unittest
import tempfile

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode, utils

class TestJDecodeMerging(unittest.TestCase):
    def setUp(self):
        self.tmp_path = None

    def tearDown(self):
        if self.tmp_path and os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def create_json_file(self, data):
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False, encoding='utf-8') as tmp:
            json.dump(data, tmp)
            self.tmp_path = tmp.name
        return self.tmp_path

    def test_split_card_merging(self):
        # Data representing a split card (Fire // Ice)
        # They should be merged into "Fire" with "Ice" as bside.
        test_data = {
            "data": {
                "APC": {
                    "name": "Apocalypse",
                    "code": "APC",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Fire",
                            "number": "101a",
                            "types": ["Instant"],
                            "text": "Fire deals 2 damage.",
                            "manaCost": "{1}{R}",
                            "rarity": "Uncommon"
                        },
                        {
                            "name": "Ice",
                            "number": "101b",
                            "types": ["Instant"],
                            "text": "Tap target permanent.",
                            "manaCost": "{1}{U}",
                            "rarity": "Uncommon"
                        }
                    ]
                }
            }
        }

        fname = self.create_json_file(test_data)
        allcards, bad_sets = jdecode.mtg_open_json(fname)

        # Expect "fire" to be in allcards
        self.assertIn("fire", allcards)
        # Expect "ice" NOT to be in allcards (as a top-level card)
        self.assertNotIn("ice", allcards)

        fire_card = allcards["fire"][0]
        # Check that bside is present and correct
        self.assertIn(utils.json_field_bside, fire_card)
        bside = fire_card[utils.json_field_bside]
        self.assertEqual(bside["name"], "Ice")
        self.assertEqual(bside["number"], "101b")

    def test_alt_art_no_merging(self):
        # Data representing alternate art cards (same name, a/b suffixes)
        # Like Brothers Yamazaki. Should NOT be merged.
        # The 'b' side is dropped to avoid duplication.
        test_data = {
            "data": {
                "CHK": {
                    "name": "Champions of Kamigawa",
                    "code": "CHK",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Brothers Yamazaki",
                            "number": "160a",
                            "types": ["Creature"],
                            "text": "Bushido 1",
                            "rarity": "Uncommon"
                        },
                        {
                            "name": "Brothers Yamazaki",
                            "number": "160b",
                            "types": ["Creature"],
                            "text": "Bushido 1",
                            "rarity": "Uncommon"
                        }
                    ]
                }
            }
        }

        fname = self.create_json_file(test_data)
        allcards, bad_sets = jdecode.mtg_open_json(fname)

        # Expect "brothers yamazaki" to be in allcards
        self.assertIn("brothers yamazaki", allcards)

        cards = allcards["brothers yamazaki"]

        # We expect only one card (160a), and it should NOT have a bside
        self.assertEqual(len(cards), 1)
        self.assertNotIn(utils.json_field_bside, cards[0])
        self.assertEqual(cards[0]["number"], "160a")

    def test_regular_card(self):
        test_data = {
            "data": {
                "SET": {
                    "name": "Set",
                    "code": "SET",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Regular",
                            "number": "1",
                            "types": ["Land"],
                            "rarity": "Common"
                        }
                    ]
                }
            }
        }
        fname = self.create_json_file(test_data)
        allcards, bad_sets = jdecode.mtg_open_json(fname)

        self.assertIn("regular", allcards)
        self.assertNotIn(utils.json_field_bside, allcards["regular"][0])

    def test_single_card_input(self):
        # Test that a single card JSON object (not wrapped in data/set structure)
        # is correctly detected and wrapped into a list.
        test_data = {
            "name": "Single Card",
            "types": ["Creature"],
            "text": "Destroy target world.",
            "manaCost": "{B}{B}{B}{B}",
            "rarity": "Rare",
            "setCode": "TEST"
        }

        fname = self.create_json_file(test_data)
        allcards, bad_sets = jdecode.mtg_open_json(fname)

        self.assertIn("single card", allcards)
        card = allcards["single card"][0]
        self.assertEqual(card["name"], "Single Card")
        self.assertEqual(card["setCode"], "TEST")

if __name__ == '__main__':
    unittest.main()
