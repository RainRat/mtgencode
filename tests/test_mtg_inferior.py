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

class TestMtgInferior(unittest.TestCase):
    def setUp(self):
        # Create a small test dataset
        self.test_data = {
            "data": {
                "TEST": {
                    "name": "Test Set",
                    "code": "TEST",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Grizzly Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "rarity": "common"
                        },
                        {
                            "name": "Worse Bears",
                            "manaCost": "{2}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "rarity": "common"
                        },
                        {
                            "name": "Weak Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "1",
                            "toughness": "1",
                            "rarity": "common"
                        },
                        {
                            "name": "Hill Giant",
                            "manaCost": "{3}{R}",
                            "types": ["Creature"],
                            "subtypes": ["Giant"],
                            "power": "3",
                            "toughness": "3",
                            "rarity": "common"
                        },
                        {
                            "name": "Kalonian Tusker",
                            "manaCost": "{G}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Boar"],
                            "power": "3",
                            "toughness": "3",
                            "rarity": "uncommon"
                        }
                    ]
                }
            }
        }
        self.test_file = "test_inferior.json"
        with open(self.test_file, 'w') as f:
            json.dump(self.test_data, f)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_inferior_basic(self):
        # Grizzly Bears should have Worse Bears and Weak Bears as inferior cards
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Grizzly Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Worse Bears", output)
            self.assertIn("Weak Bears", output)
            self.assertNotIn("Hill Giant", output)
            self.assertNotIn("Kalonian Tusker", output)
            self.assertNotIn("Grizzly Bears", output)

    def test_inferior_no_results(self):
        # Weak Bears has no inferior cards in this set
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            test_args = ['mtg_query.py', 'inferior', 'Weak Bears', self.test_file]
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_err.getvalue()
            self.assertIn("No cards found that are inferior to Weak Bears.", output)

    def test_inferior_target_superior_to_reference(self):
        # Kalonian Tusker (3/3 for GG) vs Grizzly Bears (2/2 for 1G)
        # Grizzly Bears is NOT inferior to Kalonian Tusker because GG is more restrictive than 1G
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()) as fake_err:
            test_args = ['mtg_query.py', 'inferior', 'Kalonian Tusker', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertNotIn("Grizzly Bears", output)

if __name__ == '__main__':
    unittest.main()
