import unittest
import sys
import os

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

from cardlib import Card
from datalib import Datamine

class TestDatalibMechanics(unittest.TestCase):
    def test_basic_keyword_profiling(self):
        card_data = {
            "name": "Aerial Elf",
            "manaCost": "{1}{G}",
            "types": ["Creature"],
            "subtypes": ["Elf"],
            "text": "Flying\nTrample",
            "rarity": "common",
            "power": "2",
            "toughness": "2"
        }
        card = Card(card_data)
        mine = Datamine([card])

        self.assertIn('Flying', mine.by_mechanic)
        self.assertIn('Trample', mine.by_mechanic)
        self.assertEqual(len(mine.by_mechanic['Flying']), 1)

    def test_structural_mechanics(self):
        card_data = {
            "name": "Test Wizard",
            "manaCost": "{U}",
            "types": ["Creature"],
            "text": "When @ enters the battlefield, draw a card.\n{1}, {T}: Scry 1.",
            "rarity": "rare",
            "power": "1",
            "toughness": "1"
        }
        card = Card(card_data)
        mine = Datamine([card])

        self.assertIn('Triggered', mine.by_mechanic)
        self.assertIn('Activated', mine.by_mechanic)
        self.assertIn('ETB Effect', mine.by_mechanic)
        self.assertIn('Draw A Card', mine.by_mechanic)
        self.assertIn('Scry', mine.by_mechanic)

    def test_modal_and_x_cost(self):
        card_data = {
            "name": "Fireball",
            "manaCost": "{X}{R}",
            "types": ["Sorcery"],
            "text": "Choose one \u2014\n\u2022 Fireball deals X damage to target creature.\n\u2022 Fireball deals X damage to target player.",
            "rarity": "uncommon"
        }

        card = Card(card_data)
        mine = Datamine([card])

        self.assertIn('Modal/Choice', mine.by_mechanic)
        self.assertIn('X-Cost/Effect', mine.by_mechanic)

    def test_recursive_bside_profiling(self):
        # Split card
        card_data = {
            "name": "Fire // Ice",
            "manaCost": "{1}{R}",
            "types": ["Instant"],
            "text": "Fire deals 2 damage.",
            "rarity": "uncommon",
            "bside": {
                "name": "Ice",
                "manaCost": "{1}{U}",
                "types": ["Instant"],
                "text": "Tap target permanent. Draw a card."
            }
        }
        card = Card(card_data)
        mine = Datamine([card])

        # B-side has 'Draw A Card'
        self.assertIn('Draw A Card', mine.by_mechanic)
        # Check counts
        self.assertEqual(len(mine.by_mechanic['Draw A Card']), 1)

    def test_keyword_boundaries(self):
        # Ensure 'mill' doesn't match 'million'
        card_data = {
            "name": "Rich Man",
            "text": "I have a million dollars.",
            "types": ["Creature"],
            "rarity": "common"
        }
        card = Card(card_data)
        mine = Datamine([card])
        self.assertNotIn('Mill', mine.by_mechanic)

        # Ensure it matches at boundaries
        card_data["text"] = "Mill three cards."
        card = Card(card_data)
        mine = Datamine([card])
        self.assertIn('Mill', mine.by_mechanic)

    def test_json_export_consistency(self):
        card_data = {
            "name": "Flying Token Maker",
            "types": ["Sorcery"],
            "text": "Create a 1/1 white Spirit creature token with flying.",
            "rarity": "common"
        }
        card = Card(card_data)
        mine = Datamine([card])

        d = mine.to_dict()
        self.assertIn('by_mechanic', d['indices'])
        # Datamine.to_dict() converts counts to strings: {str(k): len(v) for k, v in index.items()}
        # Wait, I saw len(v) was 1 and it failed 1 != '1'.
        # result['indices'][name] = {str(k): len(v) for k, v in index.items()}
        # Flying is the key 'k'. len(v) is 1. So it should be 1 (int).
        # Ah, the test said AssertionError: 1 != '1'.
        # Let's check datalib.py again.

        self.assertEqual(d['indices']['by_mechanic']['Flying'], 1)
        self.assertEqual(d['indices']['by_mechanic']['Token'], 1)

if __name__ == '__main__':
    unittest.main()
