import json
import io
import sys
import os
import unittest
import tempfile
from unittest.mock import patch
from scripts.mtg_query import main as query_main

class TestMtgCounterparts(unittest.TestCase):

    def run_main(self, args):
        with patch('sys.argv', ['mtg_query.py', 'counterparts'] + args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.stderr', new=io.StringIO()) as fake_err:
                    try:
                        query_main()
                        code = 0
                    except SystemExit as e:
                        code = e.code if isinstance(e.code, int) else 0
                    return code, fake_out.getvalue(), fake_err.getvalue()

    def test_counterparts_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_counterparts.json")
            # Create color-shifted pairs
            # Prodigal Sorcerer (U) vs Prodigal Pyromancer (R)
            # Concentrate (U) vs Harmonize (G)
            with open(test_file, "w") as f:
                json.dump([
                    {
                        "name": "Concentrate",
                        "manaCost": "{2}{U}{U}",
                        "types": ["Sorcery"],
                        "text": "Draw three cards.",
                        "rarity": "Uncommon"
                    },
                    {
                        "name": "Harmonize",
                        "manaCost": "{2}{G}{G}",
                        "types": ["Sorcery"],
                        "text": "Draw three cards.",
                        "rarity": "Uncommon"
                    },
                    {
                        "name": "Prodigal Sorcerer",
                        "manaCost": "{2}{U}",
                        "types": ["Creature"],
                        "subtypes": ["Human", "Wizard"],
                        "power": "1",
                        "toughness": "1",
                        "text": "{T}: @ deals 1 damage to any target.",
                        "rarity": "Common"
                    },
                    {
                        "name": "Prodigal Pyromancer",
                        "manaCost": "{2}{R}",
                        "types": ["Creature"],
                        "subtypes": ["Human", "Wizard"],
                        "power": "1",
                        "toughness": "1",
                        "text": "{T}: @ deals 1 damage to any target.",
                        "rarity": "Common"
                    },
                    {
                        "name": "Clone Concentrate",
                        "manaCost": "{2}{U}{U}",
                        "types": ["Sorcery"],
                        "text": "Draw three cards.",
                        "rarity": "Uncommon"
                    }
                ], f)

            # 1. Test Concentrate -> Harmonize
            code, out, err = self.run_main(["Concentrate", test_file, "--no-color", "--fields", "name"])
            self.assertEqual(code, 0)
            self.assertIn("Harmonize", out)
            self.assertNotIn("Clone Concentrate", out) # Same color, not a counterpart
            self.assertNotIn("Concentrate", out) # Should not include itself

            # 2. Test Prodigal Sorcerer -> Prodigal Pyromancer
            code, out, err = self.run_main(["Prodigal Sorcerer", test_file, "--no-color", "--fields", "name"])
            self.assertEqual(code, 0)
            self.assertIn("Prodigal Pyromancer", out)
            self.assertNotIn("Prodigal Sorcerer", out)

    def test_counterparts_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_no_counterparts.json")
            with open(test_file, "w") as f:
                json.dump([
                    {
                        "name": "Unique Card",
                        "manaCost": "{W}",
                        "types": ["Instant"],
                        "text": "Gain 3 life.",
                        "rarity": "Common"
                    }
                ], f)

            code, out, err = self.run_main(["Unique Card", test_file, "--no-color"])
            self.assertIn("No color-shifted counterparts found for Unique Card.", err)

    def test_counterparts_fuzzy_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_fuzzy.json")
            with open(test_file, "w") as f:
                json.dump([
                    {"name": "Concentrate", "manaCost": "{2}{U}{U}", "types": ["Sorcery"], "text": "Draw three cards."},
                    {"name": "Harmonize", "manaCost": "{2}{G}{G}", "types": ["Sorcery"], "text": "Draw three cards."}
                ], f)

            # Test using a partial name
            code, out, err = self.run_main(["Concen", test_file, "--no-color", "--fields", "name"])
            self.assertEqual(code, 0)
            self.assertIn("Harmonize", out)

if __name__ == '__main__':
    unittest.main()
