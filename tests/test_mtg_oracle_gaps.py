import unittest
from unittest.mock import patch
import io
import sys
import os

sys.path.append(os.getcwd())

from scripts.mtg_oracle import main as oracle_main

class TestMtgOracleGaps(unittest.TestCase):

    def run_main(self, args, stdin_isatty=False, stdin_content=None, stdout_isatty=False):
        with patch('sys.argv', ['mtg_oracle.py'] + args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.stderr', new=io.StringIO()) as fake_err:
                    with patch('sys.stdin', new=io.StringIO(stdin_content or "")):
                        with patch('sys.stdin.isatty', return_value=stdin_isatty):
                            with patch('sys.stdout.isatty', return_value=stdout_isatty):
                                try:
                                    oracle_main()
                                    code = 0
                                except SystemExit as e:
                                    code = e.code if isinstance(e.code, int) else 0
                                return code, fake_out.getvalue(), fake_err.getvalue()

    def test_main_basic_exact_match(self):
        code, out, err = self.run_main(['testdata/uthros.json', 'Uthros Research Craft', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Uthros Research Craft", out)
        self.assertIn("Artifact - Spacecraft", out)
        self.assertIn("Station 3+", out)

    def test_main_fuzzy_match_auto_fulfillment(self):
        code, out, err = self.run_main(['testdata/uthros.json', 'Uthrrs', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Uthros Research Craft", out)
        self.assertIn("Notice: Card 'Uthrrs' not found. Showing best match: Uthros Research Craft", err)

    def test_main_fuzzy_match_multiple_suggestions(self):
        # Use testdata/ which has multiple cards
        # Mock get_close_matches to return two keys that definitely exist in search_map
        # when processing testdata/
        with patch('scripts.mtg_oracle.difflib.get_close_matches',
                   return_value=['uthros research craft', 'invasion of tarkir']):
            code, out, err = self.run_main(['testdata/', 'Zzzzz', '--no-color'])
            self.assertIn("Card 'Zzzzz' not found.", out)
            self.assertIn("Did you mean:", out)
            self.assertIn("- Uthros Research Craft", out)
            self.assertIn("- Invasion of Tarkir", out)

    def test_main_fuzzy_match_no_suggestions(self):
        code, out, err = self.run_main(['testdata/uthros.json', 'Zzzzzzzzzzzz', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Card 'Zzzzzzzzzzzz' not found.", out)
        self.assertNotIn("Did you mean:", out)

    def test_main_partial_match(self):
        code, out, err = self.run_main(['testdata/uthros.json', 'Research', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Uthros Research Craft", out)

    def test_main_smart_positional_infile_as_query(self):
        with patch('os.path.exists', side_effect=lambda x: x == 'testdata/uthros.json'):
            code, out, err = self.run_main(['Uthros', '--no-color'])
            self.assertIn("No cards found matching the criteria", err)

    def test_main_default_dataset_detection(self):
        def mocked_exists(path):
            if 'AllPrintings.json' in path: return True
            if path == '-': return False
            return False

        with patch('os.path.exists', side_effect=mocked_exists):
            with patch('scripts.mtg_oracle.jdecode.mtg_open_file', return_value=[]) as mock_open:
                code, out, err = self.run_main(['-'], stdin_isatty=True)
                self.assertIn("Using default dataset", err)
                self.assertTrue(any('AllPrintings.json' in str(call) for call in mock_open.call_args_list))

    def test_main_smart_view_single(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Uthros Research Craft", out)
        self.assertIn("Station 3+", out)

    def test_main_smart_view_multiple(self):
        code, out, err = self.run_main(['testdata/', '--grep', 'Elf', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("[U] Beast Summoner", out)
        self.assertIn("[C] Double Front", out)
        self.assertNotIn("First ability", out)

    def test_main_smart_view_multiple_full_force(self):
        code, out, err = self.run_main(['testdata/', '--grep', 'Elf', '--full', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Beast Summoner", out)
        self.assertIn("First ability", out)
        self.assertIn("  ----------------------------------------", out)

    def test_main_sample(self):
        code, out, err = self.run_main(['testdata/', '--sample', '2', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Showing 2 of", out)

    def test_main_similar(self):
        code, out, err = self.run_main(['testdata/', 'Double Front', '--similar', '--no-color', '--verbose'])
        self.assertEqual(code, 0)
        self.assertIn("Loading similarity context", err)
        self.assertIn("SIMILAR CARDS", out)

    def test_main_similar_none_found(self):
        code, out, err = self.run_main(['testdata/uthros.json', 'Uthros', '--similar', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("No similar cards found.", out)

    def test_main_similar_color(self):
        code, out, err = self.run_main(['testdata/', 'Double Front', '--similar', '--color', '--verbose'])
        self.assertEqual(code, 0)
        self.assertIn("SIMILAR CARDS", out)
        self.assertIn("\x1b[", out)

    def test_main_filtering_and_sorting(self):
        code, out, err = self.run_main(['testdata/', '--rarity', 'rare', '--sort', 'name', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("Uthros Research Craft", out)
        self.assertIn("Invasion of Alara", out)

    def test_main_no_matches(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--grep', 'NonExistent', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("No cards found matching the criteria.", err)

    def test_main_scryfall_url(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("https://scryfall.com/card/eoc/7", out)

    def test_main_metadata_footer(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("SET: EOC #7", out)
        self.assertIn("ID: U", out)
        self.assertIn("SCORE:", out)

    def test_main_color_output(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--color'])
        self.assertEqual(code, 0)
        self.assertIn("\x1b[", out)

    def test_main_color_output_atty(self):
        code, out, err = self.run_main(['testdata/uthros.json'], stdout_isatty=True)
        self.assertEqual(code, 0)
        self.assertIn("\x1b[", out)

    def test_main_shorthand_flags(self):
        # Test -s (similar) and -G (gatherer)
        # We just check if they are accepted and trigger the right logic
        with patch('scripts.mtg_oracle.namediff.Namediff') as mock_nd:
            code, out, err = self.run_main(['testdata/uthros.json', 'Uthros', '-s', '-G', '--no-color', '--verbose'])
            self.assertEqual(code, 0)
            # gatherer=True effects:
            # 1. Rarity in parens on first line
            self.assertIn("Uthros Research Craft {2}{U} (rare)", out)
            # 2. P/T on typeline with em-dash
            self.assertIn("Artifact \u2014 Spacecraft (0/8)", out)
            # 3. Counters unpassed to "charge"
            self.assertIn("charge counter", out)
            self.assertTrue(mock_nd.called)

if __name__ == '__main__':
    unittest.main()
