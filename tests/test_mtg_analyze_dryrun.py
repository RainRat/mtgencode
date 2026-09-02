import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import io

# Add scripts and lib directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
import mtg_analyze

class TestMTGAnalyzeDryRun(unittest.TestCase):

    def setUp(self):
        self.mock_card1 = MagicMock()
        self.mock_card1.name = 'Grizzly Bears'
        self.mock_card1.set_code = 'MOM'

        self.mock_card2 = MagicMock()
        self.mock_card2.name = 'Giant Growth'
        self.mock_card2.set_code = 'ELD'

        self.mock_cards = [self.mock_card1, self.mock_card2]

    @patch('cli_utils.load_and_filter_cards')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_dry_run_summary(self, mock_stdout, mock_load):
        mock_load.return_value = self.mock_cards

        test_args = ['mtg_analyze.py', 'summary', 'input.json', '--dry-run']
        with patch('sys.argv', test_args):
            mtg_analyze.main()

        out = mock_stdout.getvalue()
        self.assertIn("Dry Run Summary: 2 card(s) matched.", out)
        self.assertIn("Set Code Breakdown:", out)
        self.assertIn("MOM: 1 card(s)", out)
        self.assertIn("ELD: 1 card(s)", out)
        self.assertIn("Sample Preview (up to 10): Grizzly Bears, Giant Growth", out)

    @patch('cli_utils.load_and_filter_cards')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_preview_alias_curve(self, mock_stdout, mock_load):
        mock_load.return_value = self.mock_cards

        test_args = ['mtg_analyze.py', 'curve', 'input.json', '-p']
        with patch('sys.argv', test_args):
            mtg_analyze.main()

        out = mock_stdout.getvalue()
        self.assertIn("Dry Run Summary: 2 card(s) matched.", out)
        self.assertNotIn("MANA CURVE ANALYSIS", out)

    @patch('cli_utils.load_and_filter_cards')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_preview_audit(self, mock_stdout, mock_load):
        mock_load.return_value = self.mock_cards

        test_args = ['mtg_analyze.py', 'audit', 'input.json', '--preview']
        with patch('sys.argv', test_args):
            mtg_analyze.main()

        out = mock_stdout.getvalue()
        self.assertIn("Dry Run Summary: 2 card(s) matched.", out)
        self.assertNotIn("DESIGN HEALTH AUDIT", out)

if __name__ == '__main__':
    unittest.main()
