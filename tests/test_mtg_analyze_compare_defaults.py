import unittest
from unittest.mock import MagicMock, patch
import io
import sys
import os

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_analyze import main as analyze_main, _resolve_compare_inputs

class TestMtgAnalyzeCompareDefaults(unittest.TestCase):

    @patch('sys.stdin.isatty', return_value=True)
    def test_compare_interactive_tty_empty_infiles(self, mock_isatty):
        # When infiles is empty and stdin is interactive, it should print error to stderr and exit(1)
        mock_args = MagicMock()
        mock_args.infiles = []

        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with self.assertRaises(SystemExit) as cm:
                _resolve_compare_inputs(mock_args)

            self.assertEqual(cm.exception.code, 1)
            err_msg = fake_err.getvalue()
            self.assertIn("Error: Please specify at least one file to compare, or pipe card data into standard input.", err_msg)

    @patch('sys.stdin.isatty', return_value=False)
    @patch('os.path.exists', return_value=False)
    def test_compare_non_interactive_empty_infiles(self, mock_exists, mock_isatty):
        # When infiles is empty and stdin is piped, it should default to ['-']
        mock_args = MagicMock()
        mock_args.infiles = []
        mock_args.quiet = True

        _resolve_compare_inputs(mock_args)
        self.assertEqual(mock_args.infiles, ['-'])

    @patch('sys.stdin.isatty', return_value=False)
    @patch('os.path.exists')
    def test_compare_one_infile_smart_baseline(self, mock_exists, mock_isatty):
        # Mock exists to say our custom file exists and AllPrintings.json exists
        def exists_side_effect(path):
            if 'AllPrintings.json' in path:
                return True
            if path == 'custom.json':
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        mock_args = MagicMock()
        mock_args.infiles = ['custom.json']
        mock_args.quiet = True

        _resolve_compare_inputs(mock_args)
        # It should have inserted data/AllPrintings.json (or another path) at index 0
        self.assertEqual(len(mock_args.infiles), 2)
        self.assertEqual(mock_args.infiles[1], 'custom.json')
        self.assertTrue(mock_args.infiles[0].endswith('AllPrintings.json'))

    @patch('sys.stdin.isatty', return_value=False)
    @patch('os.path.exists', return_value=False)
    def test_handle_balance_smart_defaults(self, mock_exists, mock_isatty):
        # Verify handle_balance processes standard input as default when infiles is empty and stdin is not interactive
        card1 = MagicMock()
        card1.name = "Grizzly Bears"
        card1.valid = True
        card1.parsed = True
        card1.cost = MagicMock()
        card1.cost.cmc = 2.0
        card1.cost.colors = "G"
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
        card1.color_identity = "G"
        card1.complexity_score = 10

        # When mtg_open_file is called for '-', return a list with card1
        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[card1]):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_analyze.py', 'balance', '--no-color']):
                    analyze_main()
                    output = fake_out.getvalue()
                    self.assertIn("ARCHETYPE BALANCE COMPARISON", output)

if __name__ == '__main__':
    unittest.main()
