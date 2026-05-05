import unittest
from unittest.mock import patch, MagicMock, mock_open
import io
import sys
import os
import json

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.summarize import main as summarize_main
from lib.cardlib import Card

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

    @patch('scripts.summarize.jdecode.mtg_open_file')
    def test_main_basic(self, mock_open_file):
        card1 = self.create_sample_card()
        mock_open_file.return_value = [card1]

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            summarize_main('dummy.json', verbose=False, use_color=False)
            output = fake_out.getvalue()
            self.assertIn("DATASET SUMMARY", output)
            self.assertIn("1 valid cards", output)
            self.assertIn("COLORS & MANA", output)
            self.assertIn("CARD TYPES", output)

    @patch('scripts.summarize.jdecode.mtg_open_file')
    def test_main_json_output(self, mock_open_file):
        card1 = self.create_sample_card()
        mock_open_file.return_value = [card1]

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            summarize_main('dummy.json', verbose=False, json_out=True)
            output = fake_out.getvalue()
            data = json.loads(output)
            self.assertEqual(data['counts']['valid'], 1)
            self.assertIn('indices', data)

    @patch('scripts.summarize.jdecode.mtg_open_file')
    def test_main_outliers(self, mock_open_file):
        card1 = self.create_sample_card()
        mock_open_file.return_value = [card1]

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            summarize_main('dummy.json', verbose=False, outliers=True, use_color=False)
            output = fake_out.getvalue()
            self.assertIn("OUTLIER ANALYSIS", output)
            self.assertIn("Shortest Cardname", output)

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            summarize_main('dummy.json', verbose=False, dump_all=True, use_color=False)
            output = fake_out.getvalue()
            self.assertIn("OUTLIER ANALYSIS", output)

    @patch('scripts.summarize.jdecode.mtg_open_file')
    def test_main_filtering_propagation(self, mock_open_file):
        mock_open_file.return_value = []

        summarize_main('dummy.json', verbose=False, grep=['pattern'], rarities=['common'], cmcs=['>2'])

        mock_open_file.assert_called_once()
        args, kwargs = mock_open_file.call_args
        self.assertEqual(kwargs['grep'], ['pattern'])
        self.assertEqual(kwargs['rarities'], ['common'])
        self.assertEqual(kwargs['cmcs'], ['>2'])

    @patch('scripts.summarize.jdecode.mtg_open_file')
    def test_main_limit_and_sort(self, mock_open_file):
        card1 = self.create_sample_card(name="B")
        card2 = self.create_sample_card(name="A")

        mock_open_file.return_value = [card1, card2]

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            summarize_main('dummy.json', verbose=False, limit=1, sort='name')
            output = fake_out.getvalue()
            self.assertIn("1 valid cards", output)

    @patch('scripts.summarize.jdecode.mtg_open_file')
    @patch('scripts.summarize.open', new_callable=mock_open)
    def test_main_oname_auto_json(self, mock_file, mock_open_file):
        mock_open_file.return_value = []
        summarize_main('dummy.json', oname='summary.json', verbose=True)
        handle = mock_file()
        args, _ = handle.write.call_args_list[0]
        self.assertTrue(args[0].startswith('{'))

    @patch('scripts.summarize.jdecode.mtg_open_file')
    def test_main_empty_cards(self, mock_open_file):
        mock_open_file.return_value = []
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            summarize_main('dummy.json', verbose=False)
            output = fake_out.getvalue()
            self.assertIn("0 valid cards", output)

    @patch('scripts.summarize.jdecode.mtg_open_file')
    def test_main_color_options(self, mock_open_file):
        card1 = self.create_sample_card()
        mock_open_file.return_value = [card1]

        # Force color
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            summarize_main('dummy.json', verbose=False, use_color=True)
            output = fake_out.getvalue()
            self.assertIn("\033[", output)

if __name__ == '__main__':
    unittest.main()
