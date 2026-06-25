import unittest
import sys
import os
import io
import json
from unittest.mock import patch

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib import jdecode, utils, cardlib

class TestJDecodeComprehensiveQA(unittest.TestCase):

    def test_normalize_scryfall_rulings(self):
        # Triggers lines 176-179: Scryfall rulings normalization
        scryfall_card = {
            "object": "card",
            "name": "Test Card",
            "rulings": [
                {"published_at": "2023-01-01", "comment": "Rule 1"},
                {"date": "2023-02-01", "text": "Rule 2"}
            ]
        }
        normalized = jdecode._normalize_scryfall_card(scryfall_card)
        self.assertEqual(normalized['rulings'][0]['date'], "2023-01-01")
        self.assertEqual(normalized['rulings'][0]['text'], "Rule 1")
        self.assertEqual(normalized['rulings'][1]['date'], "2023-02-01")
        self.assertEqual(normalized['rulings'][1]['text'], "Rule 2")

    def test_mse_loyalty_reconstruction(self):
        # Triggers lines 606-607, 614: MSE loyalty cost reconstruction
        mse_content = "card:\n\tname: Jace\n\tcasting cost: 1UU\n\tsuper type: Planeswalker\n\trarity: mythic\n\tloyalty: 3\n\trule text:\n\t\tDraw.\n\t\t\n\t\tMill.\n\t\tUlt.\n\tloyalty cost 1: +1\n\tloyalty cost 2: -2\n"
        srcs, _ = jdecode.mtg_open_mse_content(mse_content)
        card_dict = srcs["jace"][0]
        # card_dict is raw dict, reconstruction happened in mtg_open_mse_content
        self.assertEqual(card_dict['text'], "+1: Draw.\n\n-2: Mill.\nUlt.")

    def test_mtg_open_file_filters_extra(self):
        # Triggers lines 1357-1364 (actions), 1368-1377 (produces), 1393-1395 (color_pie_break)
        # Note: cards must be 'valid' to be included by mtg_open_file
        cards_json = [
            {
                "name": "Llanowar Elves",
                "manaCost": "{G}",
                "text": "Add {G}.",
                "types": ["Creature"],
                "rarity": "Common",
                "power": "1",
                "toughness": "1"
            },
            {
                "name": "Heroic Intervention",
                "manaCost": "{1}{G}",
                "text": "Permanents you control gain indestructible.",
                "types": ["Instant"],
                "rarity": "Rare"
            },
            {
                "name": "Broken Card",
                "manaCost": "{U}",
                "text": "Deathtouch", # Deathtouch is not U (it's BGC)
                "types": ["Instant"],
                "rarity": "Common"
            }
        ]

        json_str = json.dumps(cards_json)

        # 1. Test Produces filter
        with patch('sys.stdin', io.StringIO(json_str)):
            res = jdecode.mtg_open_file('-', produces=["G"])
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0].name, "llanowar elves")

        # 2. Test Actions filter
        with patch('sys.stdin', io.StringIO(json_str)):
            res = jdecode.mtg_open_file('-', actions=["Protection"])
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0].name, "heroic intervention")

        # 3. Test Color Pie Break filter
        with patch('sys.stdin', io.StringIO(json_str)):
            res = jdecode.mtg_open_file('-', color_pie_break=True)
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0].name, "broken card")

if __name__ == '__main__':
    unittest.main()
