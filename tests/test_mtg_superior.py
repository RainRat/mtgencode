import unittest
from unittest.mock import patch, MagicMock
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

class TestMtgSuperior(unittest.TestCase):
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
                            "name": "Kalonian Tusker",
                            "manaCost": "{G}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Boar"],
                            "power": "3",
                            "toughness": "3",
                            "rarity": "uncommon"
                        },
                        {
                            "name": "Better Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "3",
                            "toughness": "2",
                            "rarity": "uncommon"
                        },
                        {
                            "name": "Cheaper Bears",
                            "manaCost": "{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "rarity": "rare"
                        },
                        {
                            "name": "Flying Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "text": "Flying",
                            "rarity": "rare"
                        },
                        {
                            "name": "Hill Giant",
                            "manaCost": "{3}{R}",
                            "types": ["Creature"],
                            "subtypes": ["Giant"],
                            "power": "3",
                            "toughness": "3",
                            "rarity": "common"
                        }
                    ]
                }
            }
        }
        self.test_file = "test_superior.json"
        with open(self.test_file, 'w') as f:
            json.dump(self.test_data, f)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_superior_basic(self):
        # Better Bears and Cheaper Bears and Flying Bears should be superior to Grizzly Bears
        # Kalonian Tusker is NOT strictly superior to Grizzly Bears because {G}{G} is not a subset of {1}{G} (it requires more Green mana)
        # Hill Giant is NOT superior (different types/colors/higher CMC)

        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'superior', 'Grizzly Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Better Bears", output)
            self.assertIn("Cheaper Bears", output)
            self.assertIn("Flying Bears", output)
            self.assertNotIn("Kalonian Tusker", output)
            self.assertNotIn("Hill Giant", output)
            self.assertNotIn("Grizzly Bears", output) # Should not include itself

    def test_superior_pips(self):
        # Verify pip logic: {G} is superior to {1}{G}
        # {G}{G} is NOT superior to {1}{G} (needs 2 green vs 1)
        # {G} is superior to {1}{G} (needs 1 green vs 1, and 1 generic vs 0)

        # Add a card that requires more pips but same CMC
        self.test_data['data']['TEST']['cards'].append({
            "name": "Pip Bear",
            "manaCost": "{G}{G}",
            "types": ["Creature"],
            "power": "2",
            "toughness": "2",
        })
        with open(self.test_file, 'w') as f:
            json.dump(self.test_data, f)

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            test_args = ['mtg_query.py', 'superior', 'Grizzly Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertNotIn("Pip Bear", output)

    def test_superior_mechanics(self):
        # Flying Bears (with Flying) should be superior to Grizzly Bears (no abilities)
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'superior', 'Grizzly Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Flying Bears", output)

    def test_superior_no_results(self):
        # Hill Giant has no superior cards in this set
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            test_args = ['mtg_query.py', 'superior', 'Hill Giant', self.test_file]
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_err.getvalue()
            self.assertIn("No cards found that are superior to Hill Giant.", output)

    def test_superior_not_found(self):
        # Reference card does not exist
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            test_args = ['mtg_query.py', 'superior', 'Nonexistent Card', self.test_file]
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_err.getvalue()
            self.assertIn("Error: Could not find reference card 'Nonexistent Card'", output)

if __name__ == '__main__':
    unittest.main()
