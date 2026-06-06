import unittest
from unittest.mock import patch
import sys
import io
import json
import os

# Add scripts directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))
import mtg_analyze

class TestMtgAudit(unittest.TestCase):
    def setUp(self):
        self.test_json = "test_audit_lib.json"
        with open(self.test_json, "w") as f:
            json.dump({
                "data": {
                    "TST": {
                        "name": "Test Set",
                        "code": "TST",
                        "type": "expansion",
                        "cards": [
                            {
                                "name": "Blue Murder",
                                "manaCost": "{U}",
                                "types": ["Instant"],
                                "text": "Deathtouch\nDestroy target creature.",
                                "rarity": "common"
                            },
                            {
                                "name": "Green Bear",
                                "manaCost": "{G}{G}",
                                "types": ["Creature"],
                                "subtypes": ["Bear"],
                                "text": "Trample",
                                "power": "2",
                                "toughness": "2",
                                "rarity": "common"
                            },
                            {
                                "name": "Red Fire",
                                "manaCost": "{R}",
                                "types": ["Sorcery"],
                                "text": "Deals 2 damage to each creature.",
                                "rarity": "rare"
                            }
                        ]
                    }
                }
            }, f)

    def tearDown(self):
        if os.path.exists(self.test_json):
            os.remove(self.test_json)

    def test_audit_tty(self):
        test_args = ['mtg_analyze.py', 'audit', self.test_json, '--no-color']
        with patch('sys.argv', test_args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                mtg_analyze.main()
                output = fake_out.getvalue()
                self.assertIn("DESIGN HEALTH AUDIT", output)
                self.assertIn("Creature Density: 33.3%", output)
                self.assertIn("Removal Density: 66.7%", output) # Blue Murder and Red Fire
                self.assertIn("Color Pie Violations:", output)
                self.assertIn("Blue Murder: Color Pie Break: Deathtouch (Expected BGC)", output)

    def test_audit_json(self):
        test_args = ['mtg_analyze.py', 'audit', self.test_json, '--json']
        with patch('sys.argv', test_args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                mtg_analyze.main()
                output = fake_out.getvalue()
                data = json.loads(output)
                self.assertEqual(data['total_cards'], 3)
                self.assertAlmostEqual(data['creature_density'], 33.333, places=2)
                self.assertIn('Blue Murder', [b['card'] for b in data['color_pie_breaks']])

if __name__ == '__main__':
    unittest.main()
