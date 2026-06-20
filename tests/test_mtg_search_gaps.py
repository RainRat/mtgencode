import unittest
from unittest.mock import patch
import io
import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

from scripts.mtg_query import main as query_main

class TestMtgSearchGaps(unittest.TestCase):

    def run_main(self, args, stdin_content=None):
        with patch('sys.argv', ['mtg_query.py', 'search'] + args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.stderr', new=io.StringIO()) as fake_err:
                    with patch('sys.stdin', new=io.StringIO(stdin_content or "")):
                        try:
                            query_main()
                            code = 0
                        except SystemExit as e:
                            code = e.code if isinstance(e.code, int) else 0
                        return code, fake_out.getvalue(), fake_err.getvalue()

    def test_similar_to_basic(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--similar-to', 'Uthros Research Craft', '--no-color', '--table'])
        self.assertEqual(code, 0)
        self.assertIn("Uthros Research Craft", out)
        self.assertIn("SEARCH RESULTS", out)

    def test_similar_to_filtering_interplay(self):
        # We need something that IS in the filtered pool to compare against.
        # Let's use manual.json which has "Double Front" (Common).
        # We can filter for Common and search similar-to "Double Front".
        code, out, err = self.run_main(['testdata/manual.json', '--rarity', 'common', '--similar-to', 'Double Front', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Double Front", out)

    def test_similar_to_not_found(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--similar-to', 'NonExistentCard', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Warning: Card 'NonExistentCard' not found", err)

    def test_jsonl_output(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--jsonl'])
        self.assertEqual(code, 0)
        data = json.loads(out.strip())
        self.assertEqual(data['name'], 'Uthros Research Craft')

    def test_fuzzy_suggestions(self):
        # 'Uthrrs' is close to 'Uthros'
        code, out, err = self.run_main(['testdata/uthros.json', '--grep-name', 'Uthrrs'])
        self.assertEqual(code, 0)
        self.assertIn("Did you mean:", err)
        self.assertIn("Uthros", err)

    def test_simulation_fields_box(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--box', '1', '--csv'])
        self.assertEqual(code, 0)
        self.assertIn("Box", out)
        self.assertIn("Pack", out)

    def test_smart_positional_swapping(self):
        # Swap query and filename
        code, out, err = self.run_main(['Uthros', 'testdata/uthros.json', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Uthros Research Craft", out)

    def test_smart_positional_query_only(self):
        # Test the branch where infile is treated as a query because it doesn't exist.
        with patch('os.path.exists', side_effect=lambda x: x == 'testdata/uthros.json'):
             # Provide empty stdin to avoid waiting for input
             code, out, err = self.run_main(['Uthros', '--no-color'], stdin_content="")
             # It will try to read from stdin because 'Uthros' is not a file and AllPrintings doesn't exist.
             self.assertIn("No cards found", err)

    def test_invalid_field_canonicalization(self):
        # Test get_field_value with an unknown field
        from scripts.mtg_query import get_field_value
        from lib.cardlib import Card
        card = Card({"name": "Test"})
        val = get_field_value(card, "invalid_field")
        self.assertEqual(val, "")

    def test_get_field_value_pt_variants(self):
        from scripts.mtg_query import get_field_value
        from lib.cardlib import Card
        card = Card({"name": "Test", "power": "2", "toughness": "3", "types": ["Creature"]})
        self.assertEqual(get_field_value(card, "power"), "2")
        self.assertEqual(get_field_value(card, "toughness"), "3")
        self.assertEqual(get_field_value(card, "pt"), "(2/3)")

    def test_get_field_value_loyalty(self):
        from scripts.mtg_query import get_field_value
        from lib.cardlib import Card
        card = Card({"name": "Test", "loyalty": "5", "types": ["Planeswalker"]})
        self.assertEqual(get_field_value(card, "loyalty"), "(5)")
        self.assertEqual(get_field_value(card, "stats"), "(5)")

if __name__ == '__main__':
    unittest.main()
