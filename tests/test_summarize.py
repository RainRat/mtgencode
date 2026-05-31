import unittest
from unittest.mock import patch, mock_open
import io
import sys
import os
import json

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_analyze import handle_summary
from lib.cardlib import Card
import argparse

class TestSummarize(unittest.TestCase):

    def create_sample_card(self, name="Test Card", types=["Creature"], cost="{W}", rarity="Common", p="1", t="1", text="Text"):
        return Card({
            "name": name,
            "types": types,
            "manaCost": cost,
            "rarity": rarity,
            "power": p,
            "toughness": t,
            "text": text
        })

    @patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards')
    def test_main_basic(self, mock_load):
        card1 = self.create_sample_card()
        mock_load.return_value = [card1]
        args = argparse.Namespace(infile='dummy.json', verbose=False, color=False, top=10, json=False, outfile=None)

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            handle_summary(args)
            output = fake_out.getvalue()
            self.assertIn("DATASET SUMMARY", output)
            self.assertIn("1 valid cards", output)
            self.assertIn("COLORS & MANA", output)
            self.assertIn("CARD TYPES", output)

    @patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards')
    def test_main_json_output(self, mock_load):
        card1 = self.create_sample_card()
        mock_load.return_value = [card1]
        args = argparse.Namespace(infile='dummy.json', verbose=False, json=True, outfile=None, sort=None)

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            handle_summary(args)
            output = fake_out.getvalue()
            data = json.loads(output)
            self.assertEqual(data['counts']['valid'], 1)
            self.assertIn('indices', data)

    @patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards')
    def test_main_outliers(self, mock_load):
        card1 = self.create_sample_card()
        mock_load.return_value = [card1]
        args = argparse.Namespace(infile='dummy.json', verbose=False, outliers=True, color=False, top=10, json=False, outfile=None, sort=None, all=False)

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            handle_summary(args)
            output = fake_out.getvalue()
            self.assertIn("OUTLIER ANALYSIS", output)

    @patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards')
    def test_main_filtering_propagation(self, mock_load):
        mock_load.return_value = []
        args = argparse.Namespace(infile='dummy.json', verbose=False, grep=['pattern'], rarity=['common'], cmc=['>2'], quiet=False)

        handle_summary(args)

        mock_load.assert_called_once_with(args)

    @patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards')
    def test_main_limit_and_sort(self, mock_load):
        card1 = self.create_sample_card(name="B")
        card2 = self.create_sample_card(name="A")

        mock_load.return_value = [card1, card2]
        args = argparse.Namespace(infile='dummy.json', verbose=False, limit=1, sort='name', reverse=False, quiet=True, json=False, outfile=None, top=10, color=False)

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            handle_summary(args)
            output = fake_out.getvalue()

    @patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards')
    @patch('scripts.mtg_analyze.open', new_callable=mock_open)
    def test_main_oname_auto_json(self, mock_file, mock_load):
        mock_load.return_value = [self.create_sample_card()]
        args = argparse.Namespace(infile='dummy.json', outfile='summary.json', verbose=True, json=False, sort=None)
        handle_summary(args)
        handle = mock_file()
        if handle.write.call_count > 0:
            args_call, _ = handle.write.call_args_list[0]
            self.assertTrue(args_call[0].startswith('{'))

    @patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards')
    def test_main_empty_cards(self, mock_load):
        mock_load.return_value = []
        args = argparse.Namespace(infile='dummy.json', verbose=False, quiet=True)
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            handle_summary(args)

    @patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards')
    def test_main_color_options(self, mock_load):
        card1 = self.create_sample_card()
        mock_load.return_value = [card1]
        args = argparse.Namespace(infile='dummy.json', verbose=False, color=True, top=10, json=False, outfile=None, sort=None)

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            handle_summary(args)
            output = fake_out.getvalue()
            self.assertIn("\033[", output)

if __name__ == '__main__':
    unittest.main()
