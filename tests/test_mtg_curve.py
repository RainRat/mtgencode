import unittest
from unittest.mock import patch
import io
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

import scripts.mtg_curve as mtg_curve
from lib.cardlib import Card

class TestMtgCurve(unittest.TestCase):

    def run_main(self, args, stdin_isatty=False, stdout_isatty=False, exists_side_effect=None):
        with patch('sys.argv', ['mtg_curve.py'] + args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.stdout.isatty', return_value=stdout_isatty):
                    with patch('sys.stderr', new=io.StringIO()) as fake_err:
                        with patch('sys.stdin.isatty', return_value=stdin_isatty):
                            real_exists = os.path.exists
                            def careful_exists(path):
                                if exists_side_effect:
                                    res = exists_side_effect(path)
                                    if res is not None:
                                        return res
                                return real_exists(path)

                            with patch('os.path.exists', side_effect=careful_exists):
                                try:
                                    mtg_curve.main()
                                    code = 0
                                except SystemExit as e:
                                    code = e.code if isinstance(e.code, int) else 0
                                return code, fake_out.getvalue(), fake_err.getvalue()

    def test_curve_basic(self):
        # Using uthros.json which has 1 card, CMC 3, Color U, Artifact
        code, out, err = self.run_main(['testdata/uthros.json', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("MANA CURVE ANALYSIS", out)
        self.assertIn("Global Average CMC: 3.00", out)
        self.assertIn("3      1   100.0%", out)
        self.assertIn("U         3.00      1", out)

    def test_curve_colorized(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--color'])
        self.assertEqual(code, 0)
        self.assertIn("\033[", out)

    def test_curve_filtering(self):
        # Filter for Creature - Uthros is an Artifact Spacecraft, not a creature by default (is_creature=False)
        code, out, err = self.run_main(['testdata/uthros.json', '--grep-type', 'Creature', '--no-color'])
        self.assertIn("No cards found matching the criteria.", err)

        # Filter for Artifact - should find it
        code, out, err = self.run_main(['testdata/uthros.json', '--grep-type', 'Artifact', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Global Average CMC: 3.00", out)

    def test_curve_rarity_filtering(self):
        # Uthros is rare
        code, out, err = self.run_main(['testdata/uthros.json', '--rarity', 'common', '--no-color'])
        self.assertIn("No cards found matching the criteria.", err)

    def test_curve_empty_input(self):
        # Test with a non-existent file (though mtg_open_file handles this)
        with patch('scripts.mtg_curve.jdecode.mtg_open_file', return_value=[]):
            code, out, err = self.run_main(['testdata/uthros.json'])
            self.assertIn("No cards found matching the criteria.", err)

    def test_curve_default_dataset_detection(self):
        def exists_check(path):
            if path == 'data/AllPrintings.json': return True
            return None

        with patch('scripts.mtg_curve.jdecode.mtg_open_file', return_value=[]):
            code, out, err = self.run_main(['-'], stdin_isatty=True, exists_side_effect=exists_check)
            self.assertIn("Notice: Using default dataset: data/AllPrintings.json", err)

    def test_curve_sample_option(self):
        with patch('scripts.mtg_curve.jdecode.mtg_open_file', return_value=[]) as mock_open_file:
            self.run_main(['testdata/uthros.json', '--sample', '1'])
            args, kwargs = mock_open_file.call_args
            self.assertTrue(kwargs.get('shuffle'))
            self.assertEqual(kwargs.get('seed'), None)

    def test_curve_seed_option(self):
        with patch('scripts.mtg_curve.jdecode.mtg_open_file', return_value=[]) as mock_open_file:
            self.run_main(['testdata/uthros.json', '--seed', '42'])
            args, kwargs = mock_open_file.call_args
            self.assertEqual(kwargs.get('seed'), 42)

    def test_curve_limit_option(self):
        # Create two mock cards
        card1 = Card({"name": "C1", "manaCost": "{1}", "types": ["Instant"]})
        card2 = Card({"name": "C2", "manaCost": "{2}", "types": ["Instant"]})
        with patch('scripts.mtg_curve.jdecode.mtg_open_file', return_value=[card1, card2]):
            code, out, err = self.run_main(['testdata/uthros.json', '--limit', '1', '--no-color'])
            self.assertIn("MANA CURVE ANALYSIS (1 match)", out)
            self.assertIn("Global Average CMC: 1.00", out)

    def test_curve_is_creature_logic(self):
        # Test that creatures and non-creatures are bucketed correctly in the bar chart
        creature = Card({"name": "Bear", "manaCost": "{1}{G}", "types": ["Creature"], "power": "2", "toughness": "2"})
        spell = Card({"name": "Growth", "manaCost": "{G}", "types": ["Instant"]})

        with patch('scripts.mtg_curve.jdecode.mtg_open_file', return_value=[creature, spell]):
            code, out, err = self.run_main(['testdata/uthros.json', '--no-color'])
            self.assertEqual(code, 0)
            # 1 CMC is non-creature -> should be '='
            # 2 CMC is creature -> should be '#'

            # Let's verify the bar chars specifically
            self.assertIn("[====================]", out)
            self.assertIn("[####################]", out)

    def test_curve_7_plus_bucket(self):
        big_card = Card({"name": "Emrakul", "manaCost": "{15}", "types": ["Creature"], "power": "15", "toughness": "15"})
        with patch('scripts.mtg_curve.jdecode.mtg_open_file', return_value=[big_card]):
            code, out, err = self.run_main(['testdata/uthros.json', '--no-color'])
            self.assertIn("7+", out)
            self.assertIn("100.0%", out)
            self.assertIn("[####################]", out)

    def test_curve_color_C_bucket(self):
        colorless = Card({"name": "Diamond", "manaCost": "{2}", "types": ["Artifact"]})
        with patch('scripts.mtg_curve.jdecode.mtg_open_file', return_value=[colorless]):
            code, out, err = self.run_main(['testdata/uthros.json', '--no-color'])
            self.assertIn("C         2.00      1", out)

    def test_curve_verbose(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--verbose'])
        # mtg_open_file with verbose=True might print to stderr, but mtg_curve itself doesn't use it much
        # except for the final summary if not quiet.
        self.assertEqual(code, 0)

    def test_curve_default_dataset_fallback(self):
        def exists_check(path):
            # Fail the script_dir based checks to trigger fallback to cwd check
            if '/data/AllPrintings.json' in path: return False
            if path == 'data/AllPrintings.json': return True
            return None

        with patch('scripts.mtg_curve.jdecode.mtg_open_file', return_value=[]):
            code, out, err = self.run_main(['-'], stdin_isatty=True, exists_side_effect=exists_check)
            self.assertIn("Notice: Using default dataset: data/AllPrintings.json", err)

    def test_curve_default_dataset_fallback_quiet(self):
        def exists_check(path):
            if '/data/AllPrintings.json' in path: return False
            if path == 'data/AllPrintings.json': return True
            return None

        with patch('scripts.mtg_curve.jdecode.mtg_open_file', return_value=[]):
            code, out, err = self.run_main(['-', '--quiet'], stdin_isatty=True, exists_side_effect=exists_check)
            self.assertEqual(err, "")

    def test_curve_color_autodetect_none(self):
        # Case where args.color is None and stdout is a tty
        code, out, err = self.run_main(['testdata/uthros.json'], stdout_isatty=True)
        self.assertEqual(code, 0)
        self.assertIn("\033[", out)

    def test_curve_bar_width_edge_cases(self):
        # Trigger "at least one block" logic
        # total_bar_len is relative to max_bucket_count.
        # Let's have two buckets.
        # Bucket 1: 100 cards (all creatures) -> max_bucket_count = 100, total_bar_len = 20
        # Bucket 2: 100 cards (99 creatures, 1 spell) -> total_bar_len = 20, c_width = round(99/100 * 20) = 20, nc_width = 0.
        # But spell exists, so nc_width should become 1 and c_width 19.

        cards = []
        for i in range(100):
            cards.append(Card({"name": f"C{i}", "manaCost": "{1}", "types": ["Creature"], "power": "1", "toughness": "1"}))
        for i in range(99):
            cards.append(Card({"name": f"D{i}", "manaCost": "{2}", "types": ["Creature"], "power": "1", "toughness": "1"}))
        cards.append(Card({"name": "S1", "manaCost": "{2}", "types": ["Instant"]}))

        # Also test the opposite: 1 creature, 99 spells
        for i in range(99):
            cards.append(Card({"name": f"E{i}", "manaCost": "{3}", "types": ["Instant"]}))
        cards.append(Card({"name": "C1", "manaCost": "{3}", "types": ["Creature"], "power": "1", "toughness": "1"}))

        with patch('scripts.mtg_curve.jdecode.mtg_open_file', return_value=cards):
            code, out, err = self.run_main(['testdata/uthros.json', '--no-color'])
            self.assertEqual(code, 0)
            # Verify that both types are represented in bars even if small
            self.assertIn("[###################=]", out) # 2 CMC
            self.assertIn("[#===================]", out) # 3 CMC

if __name__ == '__main__':
    unittest.main()
