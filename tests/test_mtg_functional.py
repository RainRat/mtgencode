import json
import io
import sys
import os
import unittest
import tempfile
from unittest.mock import patch
from scripts.mtg_query import main as query_main

class TestMtgFunctional(unittest.TestCase):

    def run_main(self, args):
        with patch('sys.argv', ['mtg_query.py', 'functional'] + args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.stderr', new=io.StringIO()) as fake_err:
                    try:
                        query_main()
                        code = 0
                    except SystemExit as e:
                        code = e.code if isinstance(e.code, int) else 0
                    return code, fake_out.getvalue(), fake_err.getvalue()

    def test_functional_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_functional.json")
            with open(test_file, "w") as f:
                json.dump([
                    {
                        "name": "Card A",
                        "manaCost": "{1}{W}",
                        "types": ["Creature"],
                        "subtypes": ["Human"],
                        "power": "2",
                        "toughness": "2",
                        "text": "First strike",
                        "rarity": "Common"
                    },
                    {
                        "name": "Card B",
                        "manaCost": "{1}{W}",
                        "types": ["Creature"],
                        "subtypes": ["Human"],
                        "power": "2",
                        "toughness": "2",
                        "text": "First strike",
                        "rarity": "Common"
                    }
                ], f)

            code, out, err = self.run_main([test_file, "--no-color"])
            self.assertEqual(code, 0)
            self.assertIn("FUNCTIONAL REPRINT GROUPS (1 match)", out)
            self.assertIn("Card A, Card B", out)
            self.assertIn("Functional check complete", err)

    def test_functional_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_no_functional.json")
            with open(test_file, "w") as f:
                json.dump([
                    {
                        "name": "Card A",
                        "manaCost": "{1}{W}",
                        "types": ["Creature"],
                        "subtypes": ["Human"],
                        "power": "2",
                        "toughness": "2",
                        "text": "First strike",
                        "rarity": "Common"
                    },
                    {
                        "name": "Card C",
                        "manaCost": "{U}",
                        "types": ["Instant"],
                        "text": "Draw a card.",
                        "rarity": "Common"
                    }
                ], f)

            code, out, err = self.run_main([test_file, "--no-color"])
            self.assertIn("No functional reprints found.", err)

    def test_functional_json_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_functional_json.json")
            with open(test_file, "w") as f:
                json.dump([
                    {"name": "A", "manaCost": "{W}", "types": ["Creature"], "power": "1", "toughness": "1"},
                    {"name": "B", "manaCost": "{W}", "types": ["Creature"], "power": "1", "toughness": "1"}
                ], f)

            code, out, err = self.run_main([test_file, "--json"])
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(len(data), 1)
            self.assertIn("A", data[0]['names'])
            self.assertIn("B", data[0]['names'])

    def test_functional_multi_face(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_functional_multi.json")
            with open(test_file, "w") as f:
                json.dump([
                    {
                        "name": "Split A",
                        "manaCost": "{R}",
                        "types": ["Instant"],
                        "text": "Deal 1 damage.",
                        "bside": {
                            "name": "Split A (Back)",
                            "manaCost": "{G}",
                            "types": ["Sorcery"],
                            "text": "Draw a card."
                        }
                    },
                    {
                        "name": "Split B",
                        "manaCost": "{R}",
                        "types": ["Instant"],
                        "text": "Deal 1 damage.",
                        "bside": {
                            "name": "Split B (Back)",
                            "manaCost": "{G}",
                            "types": ["Sorcery"],
                            "text": "Draw a card."
                        }
                    }
                ], f)

            code, out, err = self.run_main([test_file, "--no-color"])
            self.assertEqual(code, 0)
            self.assertIn("FUNCTIONAL REPRINT GROUPS (1 match)", out)
            self.assertIn("Split A, Split B", out)

if __name__ == '__main__':
    unittest.main()
