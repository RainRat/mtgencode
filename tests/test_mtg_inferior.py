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
                "INF": {
                    "name": "Inferiority Test",
                    "code": "INF",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Superior Bear",
                            "manaCost": "{1}{G}",
                            "type": "Creature — Bear",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "text": "Trample",
                            "power": "3",
                            "toughness": "3",
                            "rarity": "rare"
                        },
                        {
                            "name": "Grizzly Bears",
                            "manaCost": "{1}{G}",
                            "type": "Creature — Bear",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "text": "",
                            "power": "2",
                            "toughness": "2",
                            "rarity": "common"
                        },
                        {
                            "name": "Inferior Bear",
                            "manaCost": "{2}{G}",
                            "type": "Creature — Bear",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "text": "",
                            "power": "2",
                            "toughness": "2",
                            "rarity": "common"
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
        # Grizzly Bears and Inferior Bear should be inferior to Superior Bear
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Superior Bear', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Grizzly Bears", output)
            self.assertIn("Inferior Bear", output)
            self.assertNotIn("Superior Bear", output)

    def test_inferior_reference_grizzly(self):
        # Inferior Bear should be inferior to Grizzly Bears
        # Superior Bear and Flying Bears are NOT inferior to Grizzly Bears
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Grizzly Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Inferior Bear", output)
            self.assertNotIn("Superior Bear", output)
            self.assertNotIn("Flying Bears", output)

    def test_inferior_no_results(self):
        # Inferior Bear has no cards inferior to it in this set
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            test_args = ['mtg_query.py', 'inferior', 'Inferior Bear', self.test_file]
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_err.getvalue()
            self.assertIn("No cards found that are inferior to Inferior Bear.", output)

    def test_superior_regression(self):
        # Verify that superior still works after refactor
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            test_args = ['mtg_query.py', 'superior', 'Grizzly Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Superior Bear", output)
            self.assertIn("Flying Bears", output)
            self.assertNotIn("Inferior Bear", output)

if __name__ == '__main__':
    unittest.main()
