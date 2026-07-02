import unittest
from unittest.mock import patch
import sys
import os
import json
import io

# Add scripts and lib to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

import mtg_query
import cardlib
import utils

class TestMtgSuperiorEnhanced(unittest.TestCase):
    def setUp(self):
        # Create a test dataset with Planeswalkers, Battles, and Mechanics
        self.test_data = {
            "data": {
                "ENH": {
                    "name": "Enhanced Test Set",
                    "code": "ENH",
                    "type": "expansion",
                    "cards": [
                        # Planeswalkers
                        {
                            "name": "Base Planeswalker",
                            "manaCost": "{2}{W}{W}",
                            "types": ["Planeswalker"],
                            "subtypes": ["Elspeth"],
                            "loyalty": "4",
                            "rarity": "mythic"
                        },
                        {
                            "name": "High Loyalty Planeswalker",
                            "manaCost": "{2}{W}{W}",
                            "types": ["Planeswalker"],
                            "subtypes": ["Elspeth"],
                            "loyalty": "5",
                            "rarity": "mythic"
                        },
                        {
                            "name": "Low Loyalty Planeswalker",
                            "manaCost": "{2}{W}{W}",
                            "types": ["Planeswalker"],
                            "subtypes": ["Elspeth"],
                            "loyalty": "3",
                            "rarity": "mythic"
                        },
                        # Battles
                        {
                            "name": "Base Battle",
                            "manaCost": "{1}{R}",
                            "types": ["Battle"],
                            "subtypes": ["Siege"],
                            "loyalty": "5", # MTGJSON uses loyalty field for Battle defense
                            "rarity": "uncommon"
                        },
                        {
                            "name": "Low Defense Battle",
                            "manaCost": "{1}{R}",
                            "types": ["Battle"],
                            "subtypes": ["Siege"],
                            "loyalty": "4",
                            "rarity": "uncommon"
                        },
                        {
                            "name": "High Defense Battle",
                            "manaCost": "{1}{R}",
                            "types": ["Battle"],
                            "subtypes": ["Siege"],
                            "loyalty": "6",
                            "rarity": "uncommon"
                        },
                        # Mechanics and Actions
                        {
                            "name": "Base Mechanic Creature",
                            "manaCost": "{1}{U}",
                            "types": ["Creature"],
                            "subtypes": ["Wizard"],
                            "power": "1",
                            "toughness": "1",
                            "text": "Flying",
                            "rarity": "common"
                        },
                        {
                            "name": "More Mechanic Creature",
                            "manaCost": "{1}{U}",
                            "types": ["Creature"],
                            "subtypes": ["Wizard"],
                            "power": "1",
                            "toughness": "1",
                            "text": "Flying\nWard {2}",
                            "rarity": "uncommon"
                        },
                        {
                            "name": "Different Mechanic Creature",
                            "manaCost": "{1}{U}",
                            "types": ["Creature"],
                            "subtypes": ["Wizard"],
                            "power": "1",
                            "toughness": "1",
                            "text": "Ward {2}",
                            "rarity": "common"
                        }
                    ]
                }
            }
        }
        self.test_file = "test_superior_enhanced.json"
        with open(self.test_file, 'w') as f:
            json.dump(self.test_data, f)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_superior_planeswalker_loyalty(self):
        # High Loyalty Planeswalker (5) should be superior to Base Planeswalker (4)
        # Low Loyalty Planeswalker (3) should NOT be superior to Base Planeswalker (4)
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'superior', 'Base Planeswalker', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("High Loyalty Planeswalker", output)
            self.assertNotIn("Low Loyalty Planeswalker", output)

    def test_inferior_planeswalker_loyalty(self):
        # Base Planeswalker (4) should have Low Loyalty Planeswalker (3) as inferior
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Base Planeswalker', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Low Loyalty Planeswalker", output)
            self.assertNotIn("High Loyalty Planeswalker", output)

    def test_superior_battle_defense(self):
        # Low Defense Battle (4) should be superior to Base Battle (5)
        # High Defense Battle (6) should NOT be superior to Base Battle (5)
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'superior', 'Base Battle', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Low Defense Battle", output)
            self.assertNotIn("High Defense Battle", output)

    def test_inferior_battle_defense(self):
        # Base Battle (5) should have High Defense Battle (6) as inferior
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Base Battle', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("High Defense Battle", output)
            self.assertNotIn("Low Defense Battle", output)

    def test_superior_mechanics_superset(self):
        # More Mechanic Creature (Flying, Ward 2) should be superior to Base Mechanic Creature (Flying)
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'superior', 'Base Mechanic Creature', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("More Mechanic Creature", output)

        # Different Mechanic Creature (Ward 2) should NOT be superior to Base Mechanic Creature (Flying)
        # as it is not a superset.
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'superior', 'Base Mechanic Creature', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertNotIn("Different Mechanic Creature", output)

if __name__ == '__main__':
    unittest.main()
