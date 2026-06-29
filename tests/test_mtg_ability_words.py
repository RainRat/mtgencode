import unittest
import re
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from lib.cardlib import Card
import lib.utils as utils

class TestMtgAbilityWords(unittest.TestCase):

    def test_landfall_search_fixed(self):
        # Card with Landfall
        src = {
            "name": "Steppe Lynx",
            "manaCost": "{W}",
            "types": ["Creature"],
            "subtypes": ["Cat"],
            "rarity": "Common",
            "text": "Landfall \u2014 Whenever a land enters the battlefield under your control, Steppe Lynx gets +2/+2 until end of turn.",
            "power": "0",
            "toughness": "1"
        }
        card = Card(src)

        # Verify it is stripped from text
        self.assertNotIn("landfall", card.text.text.lower())

        # Verify it IS now in mechanics
        self.assertIn("Landfall", card.mechanics)

        # Verify it IS searchable
        pattern = re.compile("Landfall", re.IGNORECASE)
        self.assertTrue(card.search(pattern), "Should now find Landfall because it is in mechanics")

    def test_metalcraft_search_fixed(self):
        # Card with Metalcraft
        src = {
            "name": "Ardent Recruit",
            "manaCost": "{W}",
            "types": ["Creature"],
            "subtypes": ["Human", "Soldier"],
            "rarity": "Common",
            "text": "Metalcraft \u2014 Ardent Recruit gets +2/+2 as long as you control three or more artifacts.",
            "power": "1",
            "toughness": "1"
        }
        card = Card(src)

        self.assertNotIn("metalcraft", card.text.text.lower())
        self.assertIn("Metalcraft", card.mechanics)

        pattern = re.compile("Metalcraft", re.IGNORECASE)
        self.assertTrue(card.search(pattern), "Should now find Metalcraft because it is in mechanics")

    def test_multiple_ability_words(self):
         src = {
            "name": "Test Card",
            "text": "Landfall \u2014 effect 1. Metalcraft \u2014 effect 2.",
            "types": ["Sorcery"],
            "rarity": "Rare"
        }
         card = Card(src)
         self.assertIn("Landfall", card.mechanics)
         self.assertIn("Metalcraft", card.mechanics)

if __name__ == '__main__':
    unittest.main()
