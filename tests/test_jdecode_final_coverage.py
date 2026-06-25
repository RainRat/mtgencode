import unittest
import sys
import os
import io
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib import jdecode, utils, cardlib

class TestJDecodeFinalCoverage(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_normalize_scryfall_card_rulings(self):
        # Covers lines 174-179
        scryfall_card = {
            "object": "card",
            "name": "Test Card",
            "rulings": [
                {"published_at": "2023-01-01", "comment": "First ruling"},
                {"date": "2023-02-01", "text": "Second ruling"}
            ]
        }
        normalized = jdecode._normalize_scryfall_card(scryfall_card)
        self.assertEqual(len(normalized['rulings']), 2)
        self.assertEqual(normalized['rulings'][0]['date'], "2023-01-01")
        self.assertEqual(normalized['rulings'][0]['text'], "First ruling")
        self.assertEqual(normalized['rulings'][1]['date'], "2023-02-01")
        self.assertEqual(normalized['rulings'][1]['text'], "Second ruling")

    def test_mtg_open_mse_content_reconstruct_loyalty_edge_cases(self):
        # Covers lines 604-607 (empty lines) and 614 (no loyalty cost key)
        mse_content = "card:\n\tname: PW\n\tsuper type: Legendary Planeswalker\n\trule text:\n\t\tLine 1\n\t\t\n\t\tLine 3\n\tloyalty cost 1: +1\n"
        srcs, _ = jdecode.mtg_open_mse_content(mse_content)
        card_dict = srcs["pw"][0]
        # Line 1 should have +1: prefix
        # Empty line should remain empty (line 606)
        # Line 3 should NOT have prefix (line 614)
        expected_text = "+1: Line 1\n\nLine 3"
        self.assertEqual(card_dict["text"], expected_text)

    def test_mtg_open_file_single_json_verbose(self):
        # Covers lines 1172-1178
        json_path = os.path.join(self.test_dir, "test.json")
        with open(json_path, 'w') as f:
            f.write(json.dumps({"name": "Test", "types": ["Land"], "rarity": "Common"}))

        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            cards = jdecode.mtg_open_file(json_path, verbose=True)
            self.assertIn("This looks like a json file", fake_err.getvalue())
            self.assertEqual(len(cards), 1)

    def test_mtg_open_file_filtering_complex_gaps(self):
        # Covers complex filtering logic in mtg_open_file
        cards_json = [
            {
                "name": "Removal Card",
                "types": ["Instant"],
                "rarity": "Common",
                "manaCost": "{B}",
                "text": "Destroy target creature." # 'Removal' action
            },
            {
                "name": "Producer Card",
                "types": ["Artifact"],
                "rarity": "Common",
                "manaCost": "{G}",
                "text": "{T}: Add {G}." # 'G' production
            },
            {
                "name": "Universal Producer",
                "types": ["Artifact"],
                "rarity": "Common",
                "manaCost": "{2}",
                "text": "{T}: Add one mana of any color." # 'Any' production
            },
            {
                "name": "Colorless Card",
                "types": ["Artifact"],
                "rarity": "Common",
                "manaCost": "{1}" # Colorless identity
            },
            {
                "name": "Break Card",
                "types": ["Enchantment"],
                "rarity": "Common",
                "manaCost": "{U}",
                "text": "Deathtouch" # Color pie break (Blue Deathtouch)
            }
        ]
        json_path = os.path.join(self.test_dir, "cards.json")
        with open(json_path, 'w') as f:
            f.write(json.dumps(cards_json))

        # Test action filtering (1357-1364)
        cards = jdecode.mtg_open_file(json_path, actions=["Removal"])
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, "removal card")

        # Test produces filtering (1368-1377)
        # Match 'G' (hits Producer Card and Universal Producer)
        cards = jdecode.mtg_open_file(json_path, produces=["G"])
        self.assertEqual(len(cards), 2)

        # Match 'Any' (hits only Universal Producer)
        cards = jdecode.mtg_open_file(json_path, produces=["Any"])
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, "universal producer")

        # Test identity filtering for colorless (1380-1389)
        cards = jdecode.mtg_open_file(json_path, identities=["A"])
        self.assertEqual(len(cards), 2) # Universal Producer and Colorless Card both have empty color identity

        # Test color pie break filtering (1392-1395)
        cards = jdecode.mtg_open_file(json_path, color_pie_break=True)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, "break card")

        # Test identity count filtering (1398-1404)
        # Universal Producer and Colorless Card both have 0 colors in identity
        cards = jdecode.mtg_open_file(json_path, id_counts=["0"])
        self.assertEqual(len(cards), 2)

    def test_mtg_open_file_decklist_probing_loop(self):
        # Covers lines 1113-1124 (probing loop for decklist pattern)
        decklist_txt = os.path.join(self.test_dir, "mydeck.txt")
        # Starts with digits + space on 3rd line
        with open(decklist_txt, 'w') as f:
            f.write("Line 1\nLine 2\n4 Grizzly Bears\n")

        # We need to mock _hydrate_decklist to return something so it doesn't try to load AllPrintings.json
        with patch('lib.jdecode._hydrate_decklist') as mock_hydrate:
            mock_hydrate.return_value = []
            jdecode.mtg_open_file(decklist_txt)
            self.assertTrue(mock_hydrate.called)

if __name__ == '__main__':
    unittest.main()
