import unittest
from unittest.mock import MagicMock, patch
import io
import sys
import os

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_balance import get_archetype_counts, main as balance_main
import scripts.mtg_balance

class TestMtgBalance(unittest.TestCase):

    def test_get_archetype_counts_monocolored(self):
        # Create a White card
        card_w = MagicMock()
        card_w.color_identity = "W"

        counts = get_archetype_counts([card_w])
        # White should contribute to UW, GW, BW, RW
        self.assertEqual(counts["UW"], 1)
        self.assertEqual(counts["GW"], 1)
        self.assertEqual(counts["BW"], 1)
        self.assertEqual(counts["RW"], 1)
        # Should not contribute to others
        self.assertEqual(counts["BU"], 0)
        self.assertEqual(counts["BR"], 0)
        self.assertEqual(counts["GR"], 0)
        self.assertEqual(counts["RU"], 0)
        self.assertEqual(counts["BG"], 0)
        self.assertEqual(counts["GU"], 0)

    def test_get_archetype_counts_multicolored(self):
        # Create a UW card
        card_uw = MagicMock()
        card_uw.color_identity = "UW"

        counts = get_archetype_counts([card_uw])
        self.assertEqual(counts["UW"], 1)
        # Should not contribute to others even if they share a color
        self.assertEqual(counts["GW"], 0)
        self.assertEqual(counts["BU"], 0)

    def test_get_archetype_counts_mixed(self):
        card_w = MagicMock()
        card_w.color_identity = "W"
        card_u = MagicMock()
        card_u.color_identity = "U"
        card_uw = MagicMock()
        card_uw.color_identity = "UW"

        counts = get_archetype_counts([card_w, card_u, card_uw])
        # UW gets from W, U, and UW
        self.assertEqual(counts["UW"], 3)
        # GW gets only from W
        self.assertEqual(counts["GW"], 1)
        # BU gets only from U
        self.assertEqual(counts["BU"], 1)
        # BR gets from none
        self.assertEqual(counts["BR"], 0)

    def test_get_archetype_counts_edge_cases(self):
        # Colorless card
        card_c = MagicMock()
        card_c.color_identity = ""
        # 3-color card
        card_wub = MagicMock()
        card_wub.color_identity = "BUW"

        counts = get_archetype_counts([card_c, card_wub])
        # Should not contribute to any 2-color archetypes
        for p in counts:
            self.assertEqual(counts[p], 0)

    def test_balance_main_single_file(self):
        card = MagicMock()
        card.color_identity = "UW"
        card.name = "Test Card"

        with patch('scripts.mtg_balance.jdecode.mtg_open_file', return_value=[card]):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_balance.py', 'test.json', '--no-color']):
                    balance_main()
                    output = fake_out.getvalue()
                    self.assertIn("ARCHETYPE BALANCE COMPARISON", output)
                    self.assertIn("Baseline: test.json (1 cards)", output)
                    self.assertIn("WU (Azorius)", output)
                    self.assertIn("100.0%", output)

    def test_balance_main_comparison(self):
        card1 = MagicMock()
        card1.color_identity = "W"
        card2 = MagicMock()
        card2.color_identity = "U"

        def mock_open(filename, **kwargs):
            if filename == 'base.json':
                return [card1]
            return [card2]

        with patch('scripts.mtg_balance.jdecode.mtg_open_file', side_effect=mock_open):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_balance.py', 'base.json', 'target.json', '--no-color']):
                    balance_main()
                    output = fake_out.getvalue()
                    self.assertIn("Baseline: base.json (1 cards)", output)
                    self.assertIn("% base.json", output)
                    self.assertIn("% target.json", output)
                    self.assertIn("Delta", output)

    def test_balance_main_filtering_args(self):
        # We just want to make sure these arguments are passed to mtg_open_file
        with patch('scripts.mtg_balance.jdecode.mtg_open_file', return_value=[]) as mock_open:
            with patch('sys.stderr', new=io.StringIO()):
                with patch('sys.argv', ['mtg_balance.py', 'test.json', '--set', 'MOM', '--rarity', 'rare', '--limit', '10']):
                    balance_main()
                    mock_open.assert_called_with('test.json', verbose=False, sets=['MOM'], rarities=['rare'])

    def test_balance_main_no_cards(self):
        with patch('scripts.mtg_balance.jdecode.mtg_open_file', return_value=[]):
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                with patch('sys.argv', ['mtg_balance.py', 'empty.json']):
                    balance_main()
                    self.assertIn("Warning: No cards found in empty.json", fake_err.getvalue())

    def test_balance_main_color(self):
        card = MagicMock()
        card.color_identity = "UW"

        mock_stdout = MagicMock(spec=io.TextIOBase)
        mock_stdout.isatty.return_value = True
        mock_stdout.write = MagicMock()
        captured_output = io.StringIO()
        mock_stdout.write.side_effect = captured_output.write

        with patch('scripts.mtg_balance.jdecode.mtg_open_file', return_value=[card]):
            with patch('sys.stdout', mock_stdout):
                with patch('sys.argv', ['mtg_balance.py', 'test.json', '--color']):
                    balance_main()
                    output = captured_output.getvalue()
                    self.assertIn("\033[", output)

    def test_balance_main_color_deltas(self):
        # Test green and red deltas
        card_base = MagicMock()
        card_base.color_identity = "UW" # 100% UW
        card_target = MagicMock()
        card_target.color_identity = "BU" # 100% BU, so UW delta is -100%

        def mock_open(filename, **kwargs):
            if filename == 'base.json':
                return [card_base]
            return [card_target]

        mock_stdout = MagicMock(spec=io.TextIOBase)
        mock_stdout.isatty.return_value = True
        mock_stdout.write = MagicMock()
        captured_output = io.StringIO()
        mock_stdout.write.side_effect = captured_output.write

        with patch('scripts.mtg_balance.jdecode.mtg_open_file', side_effect=mock_open):
            with patch('sys.stdout', mock_stdout):
                with patch('sys.argv', ['mtg_balance.py', 'base.json', 'target.json', '--color']):
                    balance_main()
                    output = captured_output.getvalue()
                    # Check for green (+100.0%) and red (-100.0%)
                    # Green is BOLD + GREEN (\033[1m\033[92m)
                    # Red is BOLD + RED (\033[1m\033[91m)
                    self.assertIn("\033[1m\033[92m+100.0%\033[0m", output)
                    self.assertIn("\033[1m\033[91m-100.0%\033[0m", output)

    def test_balance_main_autocolor(self):
        card = MagicMock()
        card.color_identity = "UW"

        mock_stdout = MagicMock(spec=io.TextIOBase)
        mock_stdout.isatty.return_value = True
        mock_stdout.write = MagicMock()
        captured_output = io.StringIO()
        mock_stdout.write.side_effect = captured_output.write

        with patch('scripts.mtg_balance.jdecode.mtg_open_file', return_value=[card]):
            with patch('sys.stdout', mock_stdout):
                # No --color or --no-color flag
                with patch('sys.argv', ['mtg_balance.py', 'test.json']):
                    balance_main()
                    output = captured_output.getvalue()
                    self.assertIn("\033[", output)

    def test_balance_main_quiet_verbose(self):
        card = MagicMock()
        card.color_identity = "UW"

        with patch('scripts.mtg_balance.jdecode.mtg_open_file', return_value=[card]):
            # Quiet should suppress summary
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_balance.py', 'test.json', '--quiet']):
                    balance_main()
                    self.assertNotIn("Operation Summary", fake_out.getvalue())

            # Verbose should pass verbose=True to mtg_open_file
            with patch('scripts.mtg_balance.jdecode.mtg_open_file', return_value=[card]) as mock_open:
                with patch('sys.stdout', new=io.StringIO()):
                    with patch('sys.argv', ['mtg_balance.py', 'test.json', '--verbose']):
                        balance_main()
                        mock_open.assert_called()
                        self.assertEqual(mock_open.call_args[1]['verbose'], True)

if __name__ == '__main__':
    unittest.main()
