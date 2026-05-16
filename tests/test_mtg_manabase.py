import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os
import json

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

from scripts.mtg_manabase import main, calculate_manabase
import cardlib
from manalib import Manacost, Manatext

class TestMtgManabase(unittest.TestCase):

    def test_calculate_manabase_proportional(self):
        # Create dummy cards with specific pips
        card_w = MagicMock(spec=cardlib.Card)
        card_w.is_land = False
        card_w.cost = MagicMock(spec=Manacost)
        card_w.cost.allsymbols = {'W': 1}
        card_w.text = MagicMock(spec=Manatext)
        card_w.text.costs = []
        card_w.bside = None

        card_u = MagicMock(spec=cardlib.Card)
        card_u.is_land = False
        card_u.cost = MagicMock(spec=Manacost)
        card_u.cost.allsymbols = {'U': 2}
        card_u.text = MagicMock(spec=Manatext)
        card_u.text.costs = []
        card_u.bside = None

        cards = [card_w, card_u]

        # 10 lands total.
        # Total pips: 3 (1 W, 2 U)
        # Minimums: W=1, U=1 (Rem=8)
        # Proportional: W=8*(1/3)=2.66 (floor 2), U=8*(2/3)=5.33 (floor 5)
        # Totals: W=3, U=6 (Total=9, Rem=1)
        # Remainder priority: W(0.66) > U(0.33)
        # Final: Plains 4, Island 6

        recommendation, pips, total = calculate_manabase(cards, 10)
        self.assertEqual(pips['W'], 1)
        self.assertEqual(pips['U'], 2)
        self.assertEqual(total, 3)
        self.assertEqual(recommendation['Plains'], 4)
        self.assertEqual(recommendation['Island'], 6)
        self.assertEqual(recommendation['Swamp'], 0)

    def test_calculate_manabase_minimums(self):
        # Even if a color has very few pips, it should get at least 1 land if target_lands > color_count
        card_w = MagicMock(spec=cardlib.Card)
        card_w.is_land = False
        card_w.cost = MagicMock(spec=Manacost)
        card_w.cost.allsymbols = {'W': 100}
        card_w.text = MagicMock(spec=Manatext)
        card_w.text.costs = []
        card_w.bside = None

        card_u = MagicMock(spec=cardlib.Card)
        card_u.is_land = False
        card_u.cost = MagicMock(spec=Manacost)
        card_u.cost.allsymbols = {'U': 1}
        card_u.text = MagicMock(spec=Manatext)
        card_u.text.costs = []
        card_u.bside = None

        cards = [card_w, card_u]
        recommendation, _, _ = calculate_manabase(cards, 10)

        self.assertGreaterEqual(recommendation['Plains'], 1)
        self.assertGreaterEqual(recommendation['Island'], 1)
        self.assertEqual(sum(recommendation.values()), 10)

    def test_main_execution(self):
        # Test main function with mocked open_file
        test_json = {
            "data": {
                "TEST": {
                    "name": "Test Set",
                    "code": "TEST",
                    "type": "expansion",
                    "cards": [
                        {"name": "Spell", "manaCost": "{W}{U}", "types": ["Instant"], "setCode": "TEST", "rarity": "common"}
                    ]
                }
            }
        }

        with open("test_manabase.json", "w") as f:
            json.dump(test_json, f)

        try:
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_manabase.py', 'test_manabase.json', '--lands', '20', '--no-color']):
                    main()
                    output = fake_out.getvalue()
                    self.assertIn("MANA BASE ADVISOR", output)
                    self.assertIn("Plains", output)
                    self.assertIn("Island", output)
                    # For {W}{U} and 20 lands, should be 10/10
                    self.assertIn("Suggested: 10 Plains, 10 Island", output)
        finally:
            if os.path.exists("test_manabase.json"):
                os.remove("test_manabase.json")

if __name__ == '__main__':
    unittest.main()
