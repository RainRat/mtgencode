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
                        },
                        {
                            "name": "Gray Ogre",
                            "manaCost": "{2}{R}",
                            "types": ["Creature"],
                            "subtypes": ["Ogre"],
                            "power": "2",
                            "toughness": "2",
                            "rarity": "common"
                        },
                        {
                            "name": "Invasion of Alara",
                            "manaCost": "{W}{U}{B}{R}{G}",
                            "types": ["Battle"],
                            "subtypes": ["Siege"],
                            "loyalty": "7",
                            "rarity": "rare"
                        },
                        {
                            "name": "Better Battle",
                            "manaCost": "{W}{U}{B}{R}{G}",
                            "types": ["Battle"],
                            "subtypes": ["Siege"],
                            "loyalty": "5",
                            "rarity": "rare"
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
        # Grizzly Bears should be inferior to Better Bears, Cheaper Bears, and Flying Bears
        # We test by asking for cards inferior to Better Bears
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Better Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Grizzly Bears", output)
            self.assertNotIn("Better Bears", output)
            self.assertNotIn("Cheaper Bears", output)

    def test_inferior_pips(self):
        # Grizzly Bears ({1}{G}) should be inferior to Cheaper Bears ({G})
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Cheaper Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Grizzly Bears", output)

    def test_inferior_mechanics(self):
        # Grizzly Bears (no abilities) should be inferior to Flying Bears (with Flying)
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Flying Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Grizzly Bears", output)

    def test_inferior_no_results(self):
        # Grizzly Bears has no inferior cards in this set
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            test_args = ['mtg_query.py', 'inferior', 'Grizzly Bears', self.test_file]
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_err.getvalue()
            self.assertIn("No cards found that are inferior to Grizzly Bears.", output)

    def test_inferior_not_found(self):
        # Reference card does not exist
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            test_args = ['mtg_query.py', 'inferior', 'Nonexistent Card', self.test_file]
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_err.getvalue()
            self.assertIn("Error: Could not find reference card 'Nonexistent Card'", output)

    def test_inferior_battles(self):
        # For battles, lower defense is better.
        # So Invasion of Alara (Defense 7) should be inferior to Better Battle (Defense 5).
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Better Battle', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Invasion of Alara", output)

    def test_superior_integration(self):
        # Verify that superior still works after refactoring
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'superior', 'Grizzly Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Better Bears", output)
            self.assertIn("Cheaper Bears", output)
            self.assertIn("Flying Bears", output)

if __name__ == '__main__':
    unittest.main()
