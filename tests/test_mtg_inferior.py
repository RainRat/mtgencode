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
                            "name": "Worse Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "1",
                            "toughness": "1",
                            "rarity": "common"
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
                            "name": "Vanilla Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
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
        # Grizzly Bears should be superior to Worse Bears and Expensive Bears
        # Worse Bears and Expensive Bears should be inferior to Grizzly Bears
        # Flying Bears should NOT be inferior to Grizzly Bears (it is superior)
        # Vanilla Bears is identical to Grizzly Bears, so NOT strictly inferior

        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Grizzly Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Worse Bears", output)
            self.assertIn("Expensive Bears", output)
            self.assertNotIn("Flying Bears", output)
            self.assertNotIn("Vanilla Bears", output)
            self.assertNotIn("Grizzly Bears", output) # Should not include itself

    def test_inferior_from_superior(self):
        # Flying Bears is superior to Grizzly Bears
        # So Grizzly Bears should be inferior to Flying Bears
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()):
            test_args = ['mtg_query.py', 'inferior', 'Flying Bears', self.test_file, '--fields', 'name']
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Grizzly Bears", output)
            self.assertIn("Worse Bears", output)
            self.assertIn("Expensive Bears", output)

    def test_inferior_no_results(self):
        # Worse Bears is already the worst
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            test_args = ['mtg_query.py', 'inferior', 'Worse Bears', self.test_file]
            with patch('sys.argv', test_args):
                mtg_query.main()

            output = fake_err.getvalue()
            self.assertIn("No cards found that are inferior to Worse Bears.", output)

    def test_inferior_shell(self):
        # Test shell /inferior command
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()), \
             patch('builtins.input', side_effect=['/inferior Grizzly Bears', 'exit']):

            # Create a mock for input
            mock_input = MagicMock()
            mock_input.side_effect = ['/inferior Grizzly Bears', 'exit']

            with patch('builtins.input', mock_input):
                test_args = ['mtg_query.py', 'shell', self.test_file, '--fields', 'name']
                with patch('sys.argv', test_args):
                    mtg_query.main()

            output = fake_out.getvalue()
            self.assertIn("Worse Bears", output)
            self.assertIn("Expensive Bears", output)

if __name__ == '__main__':
    unittest.main()
