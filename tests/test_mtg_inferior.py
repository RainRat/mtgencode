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
                            "name": "Expensive Bears",
                            "manaCost": "{2}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "rarity": "common"
                        },
                        {
                            "name": "Plain Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "1",
                            "toughness": "1",
                            "rarity": "common"
                        }
                    ]
                }
            }
        }
        self.test_file = "test_inferior_command.json"
        with open(self.test_file, 'w') as f:
            json.dump(self.test_data, f)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_inferior_basic(self):
        # Grizzly Bears and Expensive Bears and Plain Bears should be inferior to Better Bears
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Better Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Grizzly Bears", output)
            self.assertIn("Expensive Bears", output)
            self.assertIn("Plain Bears", output)
            self.assertNotIn("Better Bears", output) # Should not include itself

    def test_formatting_consistency(self):
        # Verify that stat formatting uses parentheses now
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'search', 'Grizzly Bears', self.test_file, '--fields', 'stats', '--table']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            # It should use (2/2) now, not just 2/2
            self.assertIn("(2/2)", output)

if __name__ == '__main__':
    unittest.main()
