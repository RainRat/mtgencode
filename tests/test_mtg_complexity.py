import unittest
from unittest.mock import patch
import io
import sys
import os
import json

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from cardlib import Card
from scripts.mtg_complexity import main as complexity_main
from scripts.mtg_search import main as search_main

class TestMtgComplexity(unittest.TestCase):

    def test_card_complexity_properties(self):
        # Basic creature
        card_json = {
            "name": "Grizzly Bears",
            "manaCost": "{1}{G}",
            "types": ["Creature"],
            "subtypes": ["Bear"],
            "power": "2",
            "toughness": "2",
            "rarity": "Common",
            "text": ""
        }
        card = Card(card_json)
        self.assertEqual(card.total_words, 0)
        self.assertEqual(card.total_lines, 0)
        # 0 + 0*5 + 0*8 + 1*3 (G) = 3
        self.assertEqual(card.complexity_score, 3)

        # Complex card
        card_json2 = {
            "name": "Uthros Research Craft",
            "manaCost": "{2}{U}",
            "types": ["Artifact"],
            "subtypes": ["Spacecraft"],
            "power": "0",
            "toughness": "8",
            "rarity": "Rare",
            "text": "Flying\nWhenever @ attacks, draw a card.\nPut a % counter on @.\n{X}: Do something."
        }
        card2 = Card(card_json2)
        # Flying (1)
        # Whenever @ attacks, draw a card. (5)
        # Put a % counter on @. (5)
        # {X}: Do something. (3)
        # Total words: 1 + 5 + 4 + 3 = 13
        self.assertEqual(card2.total_words, 13)
        self.assertEqual(card2.total_lines, 4)
        # Mechanics: Flying, Triggered, Draw A Card, Counters, X-Cost/Effect, Activated = 6
        self.assertEqual(len(card2.mechanics), 6)
        self.assertEqual(card2.color_identity, "U")
        # Score: 13 (words) + 4*5 (lines) + 6*8 (mechanics) + 1*3 (CI) + 10 (X bonus) = 13 + 20 + 48 + 3 + 10 = 94
        self.assertEqual(card2.complexity_score, 94)

    def test_complexity_cli_basic(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_complexity.py', 'testdata/uthros.json', '--no-color']):
                complexity_main()
                output = fake_out.getvalue()
                self.assertIn("COMPLEXITY ANALYSIS", output)
                self.assertIn("Average Complexity Score: 107.00", output)
                self.assertIn("Uthros Research Craft", output)

    def test_complexity_cli_json(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_complexity.py', 'testdata/uthros.json', '--json']):
                complexity_main()
                output = fake_out.getvalue()
                data = json.loads(output)
                self.assertEqual(data['average_complexity'], 107.0)
                self.assertEqual(len(data['top_cards']), 1)
                self.assertEqual(data['top_cards'][0]['complexity'], 107)

    def test_search_complexity_field(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--fields', 'name,complexity', '--text', '--no-color']):
                search_main()
                output = fake_out.getvalue()
                self.assertIn("Uthros Research Craft | 107", output)

if __name__ == '__main__':
    unittest.main()
