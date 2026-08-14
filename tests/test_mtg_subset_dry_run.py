import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
import io

# Add scripts directory to path to import mtg_subset
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
import mtg_subset

class TestMTGSubsetDryRun(unittest.TestCase):

    def setUp(self):
        self.mock_card1 = MagicMock()
        self.mock_card1.set_code = 'MOM'
        self.mock_card1.display_name = 'Lightning Bolt'
        self.mock_card1.to_dict.return_value = {'name': 'Lightning Bolt', 'setCode': 'MOM'}

        self.mock_card2 = MagicMock()
        self.mock_card2.set_code = 'ELD'
        self.mock_card2.display_name = 'Counterspell'
        self.mock_card2.to_dict.return_value = {'name': 'Counterspell', 'setCode': 'ELD'}

        self.mock_cards = [self.mock_card1, self.mock_card2]

    @patch('jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_dry_run_flag_output(self, mock_stdout, mock_file, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_subset.py', 'input.json', 'output.json', '--dry-run']
        with patch('sys.argv', test_args):
            mtg_subset.main()

        # Check stdout contains dry run information
        output = mock_stdout.getvalue()
        self.assertIn("[DRY RUN] Subset Preview for 'input.json':", output)
        self.assertIn("Matched Cards : 2", output)
        self.assertIn("Matched Sets  : 2", output)
        self.assertIn("- ELD: 1 card(s)", output)
        self.assertIn("- MOM: 1 card(s)", output)
        self.assertIn("- Lightning Bolt", output)
        self.assertIn("- Counterspell", output)
        self.assertIn("[DRY RUN] Preview complete. Output file 'output.json' was not created or modified.", output)

        # Confirm output file was NOT created or opened for writing
        mock_file.assert_not_called()

    @patch('jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_preview_alias_output(self, mock_stdout, mock_file, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_subset.py', 'input.json', 'output.json', '-p']
        with patch('sys.argv', test_args):
            mtg_subset.main()

        output = mock_stdout.getvalue()
        self.assertIn("[DRY RUN] Subset Preview", output)
        mock_file.assert_not_called()

    @patch('jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_dry_run_with_sample_truncation(self, mock_stdout, mock_file, mock_open_file):
        # Create 15 mock cards to test sample list truncation (>10)
        many_cards = []
        for i in range(15):
            c = MagicMock()
            c.set_code = 'MOM'
            c.display_name = f"Card {i+1}"
            c.to_dict.return_value = {'name': f"Card {i+1}", 'setCode': 'MOM'}
            many_cards.append(c)

        mock_open_file.return_value = many_cards

        test_args = ['mtg_subset.py', 'input.json', 'output.json', '--preview']
        with patch('sys.argv', test_args):
            mtg_subset.main()

        output = mock_stdout.getvalue()
        self.assertIn("Matched Cards : 15", output)
        self.assertIn("... and 5 more card(s)", output)
        mock_file.assert_not_called()

if __name__ == '__main__':
    unittest.main()
