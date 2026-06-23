import unittest
from unittest.mock import patch
import sys
import os
import json
import io

# Add lib and scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import mtg_query

class TestMtgInferior(unittest.TestCase):
    def setUp(self):
        self.test_data = {
            "data": {
                "TEST": {
                    "code": "TEST",
                    "name": "Test Set",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Alpha Bear",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "text": "Trample"
                        },
                        {
                            "name": "Beta Bear",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "text": ""
                        },
                        {
                            "name": "Gamma Bear",
                            "manaCost": "{2}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "text": ""
                        },
                        {
                            "name": "Sigma Siege",
                            "manaCost": "{1}{G}",
                            "types": ["Battle"],
                            "subtypes": ["Siege"],
                            "loyalty": "4",
                            "text": "ETB: Draw a card."
                        },
                        {
                            "name": "Delta Siege",
                            "manaCost": "{1}{G}",
                            "types": ["Battle"],
                            "subtypes": ["Siege"],
                            "loyalty": "5",
                            "text": "ETB: Draw a card."
                        }
                    ]
                }
            }
        }
        self.test_file = "test_inferior_data.json"
        with open(self.test_file, 'w') as f:
            json.dump(self.test_data, f)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_inferior_basic(self):
        # Alpha Bear (2/2 Trample) should be superior to Beta Bear (2/2 vanilla)
        # So Beta Bear should be inferior to Alpha Bear.
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_query.py', 'inferior', 'Alpha Bear', self.test_file, '--table']):
                mtg_query.main()
                output = fake_out.getvalue()
                self.assertIn("Beta Bear", output)
                self.assertIn("Gamma Bear", output)
                self.assertNotIn("Alpha Bear", output)

    def test_superior_basic(self):
        # Alpha Bear should be superior to Beta Bear
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_query.py', 'superior', 'Beta Bear', self.test_file, '--table']):
                mtg_query.main()
                output = fake_out.getvalue()
                self.assertIn("Alpha Bear", output)
                self.assertNotIn("Beta Bear", output)
                self.assertNotIn("Gamma Bear", output)

    def test_battle_superiority(self):
        # For Battles, LOWER defense is superior.
        # Sigma Siege (Defense 4) should be superior to Delta Siege (Defense 5).

        # 1. Superior check
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_query.py', 'superior', 'Delta Siege', self.test_file, '--table']):
                mtg_query.main()
                output = fake_out.getvalue()
                self.assertIn("Sigma Siege", output)

        # 2. Inferior check
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_query.py', 'inferior', 'Sigma Siege', self.test_file, '--table']):
                mtg_query.main()
                output = fake_out.getvalue()
                self.assertIn("Delta Siege", output)

if __name__ == '__main__':
    unittest.main()
