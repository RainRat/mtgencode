import unittest
from unittest.mock import MagicMock, patch
import io
import sys
import os

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_compare import format_delta, main as compare_main
import scripts.mtg_compare
import utils

class TestMtgCompare(unittest.TestCase):

    def test_format_delta_no_color(self):
        # Zero delta
        self.assertEqual(format_delta(5.0, 5.0), " -- ")
        # Positive delta
        self.assertEqual(format_delta(6.0, 5.0), "+1.0")
        # Negative delta
        self.assertEqual(format_delta(4.0, 5.0), "-1.0")
        # Percentage
        self.assertEqual(format_delta(15.0, 10.0, is_percent=True), "+5.0%")

    def test_format_delta_color_neutral(self):
        # Neutral significant change (Cyan)
        # Threshold for non-percent: 5% relative delta
        # 5.5 vs 5.0 is exactly 10% change, should be significant
        res = format_delta(5.5, 5.0, use_color=True, reverse_color=None)
        self.assertIn("\033[1m\033[96m+0.5\033[0m", res)

        # Non-significant change
        res = format_delta(5.01, 5.0, use_color=True, reverse_color=None)
        self.assertEqual(res, "+0.0") # Not significant, no color

    def test_format_delta_color_directional(self):
        # Good change (Green)
        res = format_delta(6.0, 5.0, use_color=True, reverse_color=False)
        self.assertIn("\033[1m\033[92m+1.0\033[0m", res)

        # Bad change (Red)
        res = format_delta(4.0, 5.0, use_color=True, reverse_color=False)
        self.assertIn("\033[1m\033[91m-1.0\033[0m", res)

        # Reversed: Good change (Green) when value decreases (e.g. CMC)
        res = format_delta(2.0, 3.0, use_color=True, reverse_color=True)
        self.assertIn("\033[1m\033[92m-1.0\033[0m", res)

    def test_format_delta_percent_significance(self):
        # Percent threshold is 2.0% absolute delta
        # 5% vs 2% = 3% delta (significant)
        res = format_delta(5.0, 2.0, is_percent=True, use_color=True, reverse_color=False)
        self.assertIn("\033[1m\033[92m+3.0%\033[0m", res)

        # 2.5% vs 1.0% = 1.5% delta (not significant)
        res = format_delta(2.5, 1.0, is_percent=True, use_color=True, reverse_color=False)
        self.assertEqual(res, "+1.5%")

    def test_compare_main_basic(self):
        card1 = MagicMock()
        card1.name = "Card 1"
        card1.valid = True
        card1.parsed = True
        card1.cost = MagicMock()
        card1.cost.cmc = 1.0
        card1.cost.colors = "W"
        card1.pt_p = "&^" # 1
        card1.pt_t = "&^" # 1
        card1.pt = "&^/&^"
        card1.loyalty = ""
        card1.rarity_name = "common"
        card1.types = ["creature"]
        card1.supertypes = []
        card1.subtypes = []
        card1.text = MagicMock()
        card1.text.encode.return_value = "text"
        card1.text.text = "text"
        card1.text_lines = [card1.text]
        card1.text_words = ["text"]
        card1.mechanics = set()
        card1.color_identity = "W"
        card1.complexity_score = 10

        with patch('scripts.mtg_compare.jdecode.mtg_open_file', return_value=[card1]):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_compare.py', 'test.json', '--no-color']):
                    compare_main()
                    output = fake_out.getvalue()
                    self.assertIn("DATASET COMPARISON", output)
                    self.assertIn("Total Cards", output)
                    self.assertIn("Avg CMC", output)
                    self.assertIn("1.0", output)

    def test_compare_main_two_files(self):
        card1 = MagicMock()
        card1.name = "Card 1"
        card1.valid = True
        card1.parsed = True
        card1.cost = MagicMock()
        card1.cost.cmc = 2.0
        card1.cost.colors = "R"
        card1.pt_p = "&^"
        card1.pt_t = "&^"
        card1.pt = "&^/&^"
        card1.loyalty = ""
        card1.rarity_name = "common"
        card1.types = ["creature"]
        card1.supertypes = []
        card1.subtypes = []
        card1.text = MagicMock()
        card1.text.encode.return_value = "text"
        card1.text.text = "text"
        card1.text_lines = [card1.text]
        card1.text_words = ["text"]
        card1.mechanics = set()
        card1.color_identity = "R"
        card1.complexity_score = 10

        card2 = MagicMock()
        card2.name = "Card 2"
        card2.valid = True
        card2.parsed = True
        card2.cost = MagicMock()
        card2.cost.cmc = 4.0
        card2.cost.colors = "U"
        card2.pt_p = "&^"
        card2.pt_t = "&^"
        card2.pt = "&^/&^"
        card2.loyalty = ""
        card2.rarity_name = "common"
        card2.types = ["creature"]
        card2.supertypes = []
        card2.subtypes = []
        card2.text = MagicMock()
        card2.text.encode.return_value = "text"
        card2.text.text = "text"
        card2.text_lines = [card2.text]
        card2.text_words = ["text"]
        card2.mechanics = set()
        card2.color_identity = "U"
        card2.complexity_score = 20

        def mock_open(filename, **kwargs):
            if filename == 'base.json':
                return [card1]
            return [card2]

        with patch('scripts.mtg_compare.jdecode.mtg_open_file', side_effect=mock_open):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_compare.py', 'base.json', 'target.json', '--no-color']):
                    compare_main()
                    output = fake_out.getvalue()
                    self.assertIn("DATASET COMPARISON", output)
                    self.assertIn("base.json", output)
                    self.assertIn("target.json", output)
                    self.assertIn("Avg CMC", output)
                    # Base CMC 2.0, Target CMC 4.0, Delta +2.0
                    self.assertIn("2.0", output)
                    self.assertIn("4.0", output)
                    self.assertIn("+2.0", output)

    def test_compare_main_filtering_args(self):
        with patch('scripts.mtg_compare.jdecode.mtg_open_file', return_value=[]) as mock_open:
            with patch('sys.stdout', new=io.StringIO()):
                with patch('sys.argv', ['mtg_compare.py', 'test.json', '--rarity', 'rare', '--set', 'MOM', '--limit', '5']):
                    compare_main()
                    # Check if args were passed to mtg_open_file
                    # get_stats_for_file is called for 'test.json'
                    args, kwargs = mock_open.call_args
                    self.assertEqual(args[0], 'test.json')
                    self.assertEqual(kwargs['rarities'], ['rare'])
                    self.assertEqual(kwargs['sets'], ['MOM'])

    def test_compare_main_color_force(self):
        card = MagicMock()
        card.name = "Test"
        card.valid = True
        card.parsed = True
        card.cost = MagicMock()
        card.cost.cmc = 1.0
        card.cost.colors = "W"
        card.pt_p = "&^"
        card.pt_t = "&^"
        card.pt = "&^/&^"
        card.loyalty = ""
        card.rarity_name = "common"
        card.types = ["creature"]
        card.supertypes = []
        card.subtypes = []
        card.text = MagicMock()
        card.text.encode.return_value = "text"
        card.text.text = "text"
        card.text_lines = [card.text]
        card.text_words = ["text"]
        card.mechanics = set()
        card.color_identity = "W"
        card.complexity_score = 10

        with patch('scripts.mtg_compare.jdecode.mtg_open_file', return_value=[card]):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                # Force color
                with patch('sys.argv', ['mtg_compare.py', 'test.json', '--color']):
                    compare_main()
                    output = fake_out.getvalue()
                    self.assertIn("\033[", output)

    def test_compare_main_no_color_force(self):
        card = MagicMock()
        card.name = "Test"
        card.valid = True
        card.parsed = True
        card.cost = MagicMock()
        card.cost.cmc = 1.0
        card.cost.colors = "W"
        card.pt_p = "&^"
        card.pt_t = "&^"
        card.pt = "&^/&^"
        card.loyalty = ""
        card.rarity_name = "common"
        card.types = ["creature"]
        card.supertypes = []
        card.subtypes = []
        card.text = MagicMock()
        card.text.encode.return_value = "text"
        card.text.text = "text"
        card.text_lines = [card.text]
        card.text_words = ["text"]
        card.mechanics = set()
        card.color_identity = "W"
        card.complexity_score = 10

        with patch('scripts.mtg_compare.jdecode.mtg_open_file', return_value=[card]):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                # Force no color
                with patch('sys.argv', ['mtg_compare.py', 'test.json', '--no-color']):
                    compare_main()
                    output = fake_out.getvalue()
                    self.assertNotIn("\033[", output)

    def test_compare_main_empty_dataset(self):
        with patch('scripts.mtg_compare.jdecode.mtg_open_file', return_value=[]):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_compare.py', 'empty.json', '--no-color']):
                    compare_main()
                    output = fake_out.getvalue()
                    # Should still print header and baseline row but with 0s
                    self.assertIn("DATASET COMPARISON", output)
                    self.assertIn("Total Cards", output)
                    self.assertIn("0", output)

    def test_compare_main_sample_args(self):
        with patch('scripts.mtg_compare.jdecode.mtg_open_file', return_value=[]):
            with patch('sys.stdout', new=io.StringIO()):
                # Test --sample flag which sets shuffle and limit
                with patch('sys.argv', ['mtg_compare.py', 'test.json', '--sample', '10']):
                    compare_main()
                    # We can't easily check the internal args object without more complex patching,
                    # but we can check if it at least runs without error.

if __name__ == '__main__':
    unittest.main()
