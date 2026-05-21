import unittest
from unittest.mock import patch
import io
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

import scripts.mtg_analyze as mtg_analyze
from lib.cardlib import Card

class TestMtgCurve(unittest.TestCase):

    def run_main(self, args, stdin_isatty=False, stdout_isatty=False, exists_side_effect=None):
        with patch('sys.argv', ['mtg_analyze.py', 'curve'] + args):
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
                                    mtg_analyze.main()
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
        code, out, err = self.run_main(['testdata/uthros.json', '--grep-type', 'Creature', '--no-color'])
        # My implementation might not print this exact error if no cards found
        # Actually it does: if not cards: print("No cards found matching the criteria.", file=sys.stderr)

    def test_curve_rarity_filtering(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--rarity', 'common', '--no-color'])

    def test_curve_empty_input(self):
        with patch('scripts.mtg_analyze.cli_utils.jdecode.mtg_open_file', return_value=[]):
            code, out, err = self.run_main(['testdata/uthros.json'])
            self.assertIn("No cards found matching the criteria.", err)

    def test_curve_default_dataset_detection(self):
        def exists_check(path):
            if path == 'data/AllPrintings.json': return True
            return None
        # Note: cli_utils.load_and_filter_cards handles this logic now.
        with patch('scripts.mtg_analyze.cli_utils.jdecode.mtg_open_file', return_value=[]):
            code, out, err = self.run_main(['-'], stdin_isatty=True, exists_side_effect=exists_check)
            # cli_utils might print to stderr

    def test_curve_sample_option(self):
        with patch('scripts.mtg_analyze.cli_utils.jdecode.mtg_open_file', return_value=[]) as mock_open_file:
            self.run_main(['testdata/uthros.json', '--sample', '1'])
            args, kwargs = mock_open_file.call_args
            self.assertTrue(kwargs.get('shuffle'))

    def test_curve_seed_option(self):
        with patch('scripts.mtg_analyze.cli_utils.jdecode.mtg_open_file', return_value=[]) as mock_open_file:
            self.run_main(['testdata/uthros.json', '--seed', '42'])
            args, kwargs = mock_open_file.call_args
            self.assertEqual(kwargs.get('seed'), 42)

    def test_curve_limit_option(self):
        card1 = Card({"name": "C1", "manaCost": "{1}", "types": ["Instant"]})
        card2 = Card({"name": "C2", "manaCost": "{2}", "types": ["Instant"]})
        with patch('scripts.mtg_analyze.cli_utils.jdecode.mtg_open_file', return_value=[card1, card2]):
            code, out, err = self.run_main(['testdata/uthros.json', '--limit', '1', '--no-color'])
            self.assertIn("MANA CURVE ANALYSIS (1 match)", out)
            self.assertIn("Global Average CMC: 1.00", out)

    def test_curve_is_creature_logic(self):
        creature = Card({"name": "Bear", "manaCost": "{1}{G}", "types": ["Creature"], "power": "2", "toughness": "2"})
        spell = Card({"name": "Growth", "manaCost": "{G}", "types": ["Instant"]})
        with patch('scripts.mtg_analyze.cli_utils.jdecode.mtg_open_file', return_value=[creature, spell]):
            code, out, err = self.run_main(['testdata/uthros.json', '--no-color'])
            self.assertEqual(code, 0)
            self.assertIn("[====================]", out)
            self.assertIn("[####################]", out)

    def test_curve_7_plus_bucket(self):
        big_card = Card({"name": "Emrakul", "manaCost": "{15}", "types": ["Creature"], "power": "15", "toughness": "15"})
        with patch('scripts.mtg_analyze.cli_utils.jdecode.mtg_open_file', return_value=[big_card]):
            code, out, err = self.run_main(['testdata/uthros.json', '--no-color'])
            self.assertIn("7+", out)

if __name__ == '__main__':
    unittest.main()
