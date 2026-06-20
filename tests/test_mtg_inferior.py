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
                            "name": "Better Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "3",
                            "toughness": "3",
                            "rarity": "uncommon"
                        },
                        {
                            "name": "Worse Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "1",
                            "toughness": "1",
                            "rarity": "common"
                        },
                        {
                            "name": "Harder Bears",
                            "manaCost": "{G}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "rarity": "common"
                        },
                        {
                            "name": "Vanilla Bear",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "rarity": "common"
                        },
                        {
                            "name": "Bear with Ability",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "text": "Trample",
                            "rarity": "common"
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
        # Worse Bears should be inferior to Grizzly Bears
        # Grizzly Bears should be inferior to Better Bears

        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Grizzly Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Worse Bears", output)
            self.assertNotIn("Better Bears", output)
            self.assertNotIn("Grizzly Bears", output)

    def test_inferior_to_better(self):
        # Grizzly Bears and Worse Bears should be inferior to Better Bears
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Better Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Grizzly Bears", output)
            self.assertIn("Worse Bears", output)
            self.assertIn("Vanilla Bear", output)

    def test_inferior_pips(self):
        # Grizzly Bears ({1}{G}) should NOT be inferior to Harder Bears ({G}{G})
        # Harder Bears should be inferior to Grizzly Bears (same stats/types, harder cost)
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Grizzly Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Harder Bears", output)

    def test_inferior_mechanics(self):
        # Vanilla Bear (no ability) should be inferior to Bear with Ability (Trample)
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Bear with Ability', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Vanilla Bear", output)
            self.assertIn("Grizzly Bears", output)

    def test_inferior_no_results(self):
        # Worse Bears has no inferior cards
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            test_args = ['mtg_query.py', 'inferior', 'Worse Bears', self.test_file]
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_err.getvalue()
            self.assertIn("No cards found that are inferior to Worse Bears.", output)

if __name__ == '__main__':
    unittest.main()
