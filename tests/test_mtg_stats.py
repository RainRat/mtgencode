import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import io
import json
import os
import csv
import re

# Add scripts and lib to path
current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_dir, '../scripts'))
sys.path.append(os.path.join(current_dir, '../lib'))

import scripts.mtg_analyze as mtg_analyze
import cardlib
import utils

class TestMtgStats(unittest.TestCase):

    def create_mock_card(self, name="Test Card", cmc=3, colors=None, pt_p=None, pt_t=None, loyalty=None, rarity="common"):
        mock_card = MagicMock(spec=cardlib.Card)
        mock_card.name = name
        mock_card.cost = MagicMock()
        mock_card.cost.cmc = cmc
        mock_card.cost.colors = colors if colors is not None else (['W'] if cmc > 0 else [])
        mock_card.pt_p = pt_p
        mock_card.pt_t = pt_t
        mock_card.loyalty = loyalty
        mock_card.rarity_name = rarity
        return mock_card

    def strip_ansi(self, s):
        return re.sub(r'\x1b\[[0-9;]*m', '', s)

    @patch('jdecode.mtg_open_file')
    def test_basic_stat_analysis(self, mock_open_file):
        # 3/3 for 3W
        card1 = self.create_mock_card("Grizzly", cmc=3, colors=['W'], pt_p='&^^^', pt_t='&^^^')
        # 1/1 for 1U
        card2 = self.create_mock_card("Merfolk", cmc=2, colors=['U'], pt_p='&^', pt_t='&^')

        mock_open_file.return_value = [card1, card2]

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', stderr), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', '--no-color']):
            mtg_analyze.main()

        output = stdout.getvalue()
        self.assertIn("COMBAT STAT ANALYSIS", output)
        self.assertIn("Combat Stat Curve", output)

        # Verify specific stats using whitespace-agnostic checks.
        self.assertRegex(output, r"(?m)^\s*3\s+3\.00\s+3\.00\s+1\s+1\.00$")
        self.assertRegex(output, r"(?m)^\s*2\s+1\.00\s+1\.00\s+1\s+1\.00$")
        self.assertIn("Color Breakdown (Avg P/T by Color):", output)
        self.assertRegex(output, r"(?m)^\s*W\s+3\.00\s+3\.00\s+1$")
        self.assertRegex(output, r"(?m)^\s*U\s+1\.00\s+1\.00\s+1$")

    @patch('jdecode.mtg_open_file')
    def test_json_output(self, mock_open_file):
        card = self.create_mock_card("Grizzly", cmc=3, colors=['G'], pt_p='&^^', pt_t='&^^')
        mock_open_file.return_value = [card]

        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', '--json']):
            mtg_analyze.main()

        output = stdout.getvalue()
        data = json.loads(output)
        self.assertEqual(data['total_cards'], 1)
        self.assertEqual(data['creatures_analyzed'], 1)
        self.assertEqual(data['cmc_curve'][0]['cmc'], "3")
        self.assertEqual(data['cmc_curve'][0]['avg_pow'], 2.0)
        self.assertEqual(data['color_breakdown'][0]['color'], "G")

    @patch('jdecode.mtg_open_file')
    def test_csv_output(self, mock_open_file):
        card = self.create_mock_card("Grizzly", cmc=3, colors=['R'], pt_p='&^^^', pt_t='&^')
        mock_open_file.return_value = [card]

        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', '--csv']):
            mtg_analyze.main()

        output = stdout.getvalue()
        reader = csv.DictReader(io.StringIO(output))
        rows = list(reader)

        cmc_row = next(r for r in rows if r['Metric'] == 'CMC Curve' and r['Category'] == '3')
        self.assertEqual(cmc_row['Avg Pow'], '3.00')
        self.assertEqual(cmc_row['Avg Tou'], '1.00')

        color_row = next(r for r in rows if r['Metric'] == 'Color Breakdown' and r['Category'] == 'R')
        self.assertEqual(color_row['Avg Pow'], '3.00')
        self.assertEqual(color_row['Avg Tou'], '1.00')

    @patch('jdecode.mtg_open_file')
    def test_loyalty_analysis(self, mock_open_file):
        # A planeswalker with loyalty 5
        card = self.create_mock_card("Walker", cmc=4, colors=['B'], loyalty='&^^^^^')
        mock_open_file.return_value = [card]

        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', '--no-color']):
            mtg_analyze.main()

        output = stdout.getvalue()
        self.assertIn("Loyalty Stats (Planeswalkers/Battles):", output)
        self.assertIn("Average Loyalty: 5.00", output)

    @patch('jdecode.mtg_open_file')
    def test_cmc_buckets_and_colorless(self, mock_open_file):
        # Test negative CMC (should bucket to 0), CMC 7+ bucket, and Colorless 'C'
        card_neg = self.create_mock_card("Neg", cmc=-1, colors=[], pt_p='&^', pt_t='&^')
        card_huge = self.create_mock_card("Huge", cmc=10, colors=['C'], pt_p='&^^^^^^^^^^', pt_t='&^^^^^^^^^^')

        mock_open_file.return_value = [card_neg, card_huge]

        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', '--no-color']):
            mtg_analyze.main()

        output = stdout.getvalue()
        self.assertRegex(output, r"(?m)^\s*0\s+1\.00\s+1\.00\s+1\s+1\.00$")
        self.assertRegex(output, r"(?m)^\s*7\+\s+10\.00\s+10\.00\s+1\s+1\.00$")
        self.assertIn("Color Breakdown (Avg P/T by Color):", output)
        self.assertRegex(output, r"(?m)^\s*C\s+5\.50\s+5\.50\s+2$")

    @patch('jdecode.mtg_open_file')
    def test_ansi_color_highlighting(self, mock_open_file):
        # Ratio > 1.1 (Red)
        card_red = self.create_mock_card("Red", cmc=1, colors=['R'], pt_p='&^^', pt_t='&^') # 2/1, ratio 2.0
        # Ratio < 0.9 (Green)
        card_green = self.create_mock_card("Green", cmc=2, colors=['G'], pt_p='&^', pt_t='&^^') # 1/2, ratio 0.5

        mock_open_file.return_value = [card_red, card_green]

        stdout = io.StringIO()
        # Test explicit --color (hits line 193)
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', '--color']):
            mtg_analyze.main()

        output = stdout.getvalue()
        self.assertIn("\x1b[91m2.00\x1b[0m", output)
        self.assertIn("\x1b[92m0.50\x1b[0m", output)

        # Test auto-color via isatty (hits line 195)
        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json']):
            with patch.object(stdout, 'isatty', return_value=True):
                mtg_analyze.main()
        output = stdout.getvalue()
        self.assertIn("\x1b[91m2.00\x1b[0m", output)

    @patch('jdecode.mtg_open_file')
    def test_no_creatures(self, mock_open_file):
        # Only a non-creature card
        card = self.create_mock_card("Sorcery", cmc=2, colors=['U'])
        mock_open_file.return_value = [card]

        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', '--no-color']):
            mtg_analyze.main()

        self.assertIn("No creatures found for combat stat analysis.", stdout.getvalue())

    @patch('jdecode.mtg_open_file')
    def test_empty_dataset(self, mock_open_file):
        mock_open_file.return_value = []

        stderr = io.StringIO()
        with patch('sys.stdout', io.StringIO()), patch('sys.stderr', stderr), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json']):
            mtg_analyze.main()

        self.assertIn("No cards found matching the criteria.", stderr.getvalue())

    @patch('builtins.open', new_callable=mock_open)
    @patch('jdecode.mtg_open_file')
    def test_outfile_format_detection(self, mock_open_file, mock_file):
        card = self.create_mock_card("Grizzly", cmc=3, colors=['G'], pt_p='&^^', pt_t='&^^')
        mock_open_file.return_value = [card]

        # Test .json detection
        with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', 'out.json']):
            mtg_analyze.main()

        # Verify it wrote JSON
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        try:
            json.loads(written_data)
        except json.JSONDecodeError:
            self.fail("Output file was not valid JSON even though it had .json extension")

        mock_file.reset_mock()
        # Test .csv detection
        with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', 'out.csv']):
            mtg_analyze.main()

        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn("Metric,Category,Avg Pow,Avg Tou,Count", written_data)

        # Test unknown extension (should default to table)
        mock_file.reset_mock()
        with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', 'out.txt', '--verbose']):
            mtg_analyze.main()

        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn("COMBAT STAT ANALYSIS", written_data)

    @patch('jdecode.mtg_open_file')
    def test_sample_and_limit(self, mock_open_file):
        cards = [self.create_mock_card(f"Card {i}", cmc=i) for i in range(10)]
        mock_open_file.return_value = cards

        # Test --limit
        with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', '--limit', '2']):
            mtg_analyze.main()

        # Test --sample (which sets shuffle=True and limit=N)
        with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'dummy.json', '--sample', '3']):
            mtg_analyze.main()

    @patch('jdecode.mtg_open_file')
    def test_smart_positional_args(self, mock_open_file):
        # Case where first arg is a query and second is a file (outfile)
        with patch('os.path.exists') as mock_exists:
            # dummy.json doesn't exist, real.json does
            mock_exists.side_effect = lambda x: x == 'real.json'

            # Test args.grep = [query] (hits line 152)
            with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'Grizzly', 'real.json']):
                mtg_analyze.main()

            mock_open_file.assert_called()
            args, kwargs = mock_open_file.call_args
            self.assertEqual(args[0], 'real.json')
            self.assertEqual(kwargs['grep'], ['Grizzly'])

            # Test grep.append(query) (hits line 154)
            mock_open_file.reset_mock()
            with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'Grizzly', 'real.json', '--grep', 'Bear']):
                mtg_analyze.main()
            args, kwargs = mock_open_file.call_args
            self.assertEqual(kwargs['grep'], ['Bear', 'Grizzly'])

            # Case where both are queries (should default to stdin/AllPrintings)
            mock_exists.side_effect = lambda x: False
            mock_open_file.reset_mock()
            with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'Grizzly', '--grep', 'Creature']):
                mtg_analyze.main()

            args, kwargs = mock_open_file.call_args
            self.assertEqual(args[0], '-')
            self.assertEqual(kwargs['grep'], ['Creature', 'Grizzly'])

            # Case where only one arg and it's a query
            mock_open_file.reset_mock()
            with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', 'Bear']):
                mtg_analyze.main()
            args, kwargs = mock_open_file.call_args
            self.assertEqual(args[0], '-')
            self.assertEqual(kwargs['grep'], ['Bear'])

    @patch('jdecode.mtg_open_file')
    def test_default_dataset_detection(self, mock_open_file):
        with patch('sys.stdin.isatty', return_value=True):
            with patch('os.path.exists') as mock_exists:
                # Mock it so the FIRST exists check (script-relative) is True
                mock_exists.side_effect = lambda x: 'AllPrintings.json' in x and 'app/scripts' in x

                with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats']):
                    mtg_analyze.main()

                mock_open_file.assert_called()

                # Mock it so the SECOND exists check (local data/) is True (hits lines 173-175)
                mock_exists.side_effect = lambda x: x == 'data/AllPrintings.json'
                mock_open_file.reset_mock()
                with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats']):
                    mtg_analyze.main()
                self.assertEqual(mock_open_file.call_args[0][0], 'data/AllPrintings.json')

                # Mock it so AllPrintings.json doesn't exist
                mock_exists.side_effect = lambda x: False
                mock_open_file.reset_mock()
                with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()), patch('sys.argv', ['mtg_analyze.py', 'stats', '-q']):
                    mtg_analyze.main()
                # Should still call with '-' but without default dataset
                mock_open_file.assert_called()
                self.assertEqual(mock_open_file.call_args[0][0], '-')

if __name__ == '__main__':
    unittest.main()
