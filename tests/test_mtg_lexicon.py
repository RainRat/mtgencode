import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_lexicon import get_color_group, analyze_lexicon, main as lexicon_main
from lib.cardlib import Card

class TestMtgLexicon(unittest.TestCase):

    def test_get_color_group(self):
        card_w = MagicMock(spec=Card)
        card_w.cost = MagicMock()
        card_w.cost.colors = ['W']
        self.assertEqual(get_color_group(card_w), 'W')

        card_m = MagicMock(spec=Card)
        card_m.cost = MagicMock()
        card_m.cost.colors = ['U', 'B']
        self.assertEqual(get_color_group(card_m), 'M')

        card_a = MagicMock(spec=Card)
        card_a.cost = MagicMock()
        card_a.cost.colors = []
        self.assertEqual(get_color_group(card_a), 'A')

        card_no_cost = MagicMock(spec=Card)
        del card_no_cost.cost
        self.assertEqual(get_color_group(card_no_cost), 'A')

    def test_analyze_lexicon_logic(self):
        card1 = MagicMock(spec=Card)
        card1.cost = MagicMock()
        card1.cost.colors = ['W']
        card1.get_text.return_value = "Flying vigilance and something."

        card2 = MagicMock(spec=Card)
        card2.cost = MagicMock()
        card2.cost.colors = ['U']
        card2.get_text.return_value = "Flying search library."

        cards = [card1, card2]

        stats = analyze_lexicon(cards, top_n=5, min_len=4)

        self.assertIn('W', stats)
        self.assertIn('U', stats)
        self.assertIn('vigilance', stats['W']['top'])
        self.assertIn('flying', stats['U']['top'])
        self.assertNotIn('search', stats['U']['freq'])
        self.assertNotIn('library', stats['U']['freq'])
        self.assertNotIn('and', stats['W']['freq'])

    def test_analyze_lexicon_empty(self):
        self.assertEqual(analyze_lexicon([], top_n=5, min_len=4), {})

    @patch('scripts.mtg_lexicon.jdecode.mtg_open_file')
    def test_main_basic(self, mock_open):
        card1 = MagicMock(spec=Card)
        card1.cost = MagicMock()
        card1.cost.colors = ['W']
        card1.get_text.return_value = "Vigilance"
        mock_open.return_value = [card1]

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_lexicon.py', 'dummy.json', '--no-color']):
                lexicon_main()
                output = fake_out.getvalue()
                self.assertIn("COLOR LEXICON ANALYSIS", output)
                self.assertIn("White", output)
                self.assertIn("vigilance", output)

    @patch('scripts.mtg_lexicon.jdecode.mtg_open_file')
    def test_main_comparison(self, mock_open):
        card1 = MagicMock(spec=Card)
        card1.cost = MagicMock()
        card1.cost.colors = ['W']
        card1.get_text.return_value = "Vigilance"

        card2 = MagicMock(spec=Card)
        card2.cost = MagicMock()
        card2.cost.colors = ['W']
        card2.get_text.return_value = "Lifelink"

        mock_open.side_effect = [[card1], [card2]]

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.stderr', new=io.StringIO()):
                with patch('sys.argv', ['mtg_lexicon.py', 'f1.json', '--compare', 'f2.json', '--no-color']):
                    lexicon_main()
                    output = fake_out.getvalue()
                    self.assertIn("COLOR LEXICON ANALYSIS", output)
                    self.assertIn("COMPARISON: f2.json", output)
                    self.assertIn("*lifelink*", output)
                    self.assertIn("vigilance", output)

    @patch('scripts.mtg_lexicon.jdecode.mtg_open_file')
    def test_main_comparison_insufficient(self, mock_open):
        card1 = MagicMock(spec=Card)
        card1.cost = MagicMock()
        card1.cost.colors = ['W']
        card1.get_text.return_value = "Vigilance"

        card2 = MagicMock(spec=Card)
        card2.cost = MagicMock()
        card2.cost.colors = ['W']
        card2.get_text.return_value = "a b c"

        mock_open.side_effect = [[card1], [card2]]

        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.argv', ['mtg_lexicon.py', 'f1.json', '--compare', 'f2.json', '--no-color']):
                lexicon_main()
                self.assertIn("Insufficient card text in f2.json for comparison.", fake_err.getvalue())

    @patch('scripts.mtg_lexicon.jdecode.mtg_open_file')
    def test_main_no_cards(self, mock_open):
        mock_open.return_value = []
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.argv', ['mtg_lexicon.py', 'empty.json']):
                lexicon_main()
                self.assertIn("No cards found", fake_err.getvalue())

    @patch('scripts.mtg_lexicon.jdecode.mtg_open_file')
    def test_main_insufficient_text(self, mock_open):
        card1 = MagicMock(spec=Card)
        card1.cost = MagicMock()
        card1.cost.colors = ['W']
        card1.get_text.return_value = "a b c"
        mock_open.return_value = [card1]

        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.argv', ['mtg_lexicon.py', 'short.json']):
                lexicon_main()
                self.assertIn("Insufficient card text", fake_err.getvalue())

    @patch('scripts.mtg_lexicon.jdecode.mtg_open_file')
    def test_main_color_force(self, mock_open):
        card1 = MagicMock(spec=Card)
        card1.cost = MagicMock()
        card1.cost.colors = ['W']
        card1.get_text.return_value = "Vigilance"
        mock_open.return_value = [card1]

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_lexicon.py', 'dummy.json', '--color']):
                lexicon_main()
                output = fake_out.getvalue()
                self.assertIn("\033[", output)

    @patch('scripts.mtg_lexicon.jdecode.mtg_open_file')
    def test_main_limit(self, mock_open):
        card1 = MagicMock(spec=Card)
        card1.cost = MagicMock()
        card1.cost.colors = ['W']
        card1.get_text.return_value = "Vigilance"
        mock_open.return_value = [card1, card1, card1]

        with patch('sys.stdout', new=io.StringIO()):
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                with patch('sys.argv', ['mtg_lexicon.py', 'dummy.json', '--limit', '1', '--no-color']):
                    lexicon_main()
                    self.assertIn("Lexicon Analysis complete: 1 card processed.", fake_err.getvalue())

if __name__ == '__main__':
    unittest.main()
