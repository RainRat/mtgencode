import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
import json
import io

# Add scripts directory to path to import mtg_subset
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
import mtg_subset

class TestMTGSubset(unittest.TestCase):

    def setUp(self):
        self.mock_card1 = MagicMock()
        self.mock_card1.set_code = 'MOM'
        self.mock_card1.to_dict.return_value = {'name': 'Card 1', 'setCode': 'MOM'}

        self.mock_card2 = MagicMock()
        self.mock_card2.set_code = 'ELD'
        self.mock_card2.to_dict.return_value = {'name': 'Card 2', 'setCode': 'ELD'}

        self.mock_cards = [self.mock_card1, self.mock_card2]

    @patch('jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_basic_subset_creation(self, mock_stdout, mock_file, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_subset.py', 'input.json', 'output.json', '--quiet']
        with patch('sys.argv', test_args):
            mtg_subset.main()

        # Verify mtg_open_file was called with the correct input file
        mock_open_file.assert_called_once()
        self.assertEqual(mock_open_file.call_args[0][0], 'input.json')

        # Verify file was written
        mock_file.assert_called_once_with('output.json', 'w', encoding='utf-8')

        # Capture the written content
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed_data = json.loads(written_data)

        # Verify structure
        self.assertIn('data', parsed_data)
        self.assertIn('MOM', parsed_data['data'])
        self.assertIn('ELD', parsed_data['data'])
        self.assertEqual(parsed_data['data']['MOM']['cards'][0]['name'], 'Card 1')
        self.assertEqual(parsed_data['data']['ELD']['cards'][0]['name'], 'Card 2')

    @patch('jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    def test_missing_set_code_defaults_to_cus(self, mock_file, mock_open_file):
        self.mock_card1.set_code = None
        mock_open_file.return_value = [self.mock_card1]

        test_args = ['mtg_subset.py', 'input.json', 'output.json', '--quiet']
        with patch('sys.argv', test_args):
            mtg_subset.main()

        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed_data = json.loads(written_data)

        self.assertIn('CUS', parsed_data['data'])

    @patch('jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    def test_filtering_flag_propagation(self, mock_file, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = [
            'mtg_subset.py', 'input.json', 'output.json', '--quiet',
            '--set', 'MOM', '--rarity', 'rare', '--grep', 'flying',
            '--cmc', '>2', '--colors', 'W', '--identity', 'WU',
            '--grep-name', 'Hero', '--exclude-name', 'Villain',
            '--grep-type', 'Creature', '--exclude-type', 'Land',
            '--grep-text', 'draw', '--exclude-text', 'discard',
            '--grep-cost', '{W}', '--exclude-cost', '{B}',
            '--grep-pt', '2/2', '--exclude-pt', '1/1',
            '--grep-loyalty', '3', '--exclude-loyalty', '5',
            '--id-count', '2', '--mechanic', 'Flying',
            '--booster', '1', '--box', '1'
        ]
        with patch('sys.argv', test_args):
            mtg_subset.main()

        # Verify flags were passed to mtg_open_file
        kwargs = mock_open_file.call_args[1]
        self.assertEqual(kwargs['sets'], ['MOM'])
        self.assertEqual(kwargs['rarities'], ['rare'])
        self.assertEqual(kwargs['grep'], ['flying'])
        self.assertEqual(kwargs['cmcs'], ['>2'])
        self.assertEqual(kwargs['colors'], ['W'])
        self.assertEqual(kwargs['identities'], ['WU'])
        self.assertEqual(kwargs['grep_name'], ['Hero'])
        self.assertEqual(kwargs['vgrep_name'], ['Villain'])
        self.assertEqual(kwargs['grep_types'], ['Creature'])
        self.assertEqual(kwargs['vgrep_types'], ['Land'])
        self.assertEqual(kwargs['grep_text'], ['draw'])
        self.assertEqual(kwargs['vgrep_text'], ['discard'])
        self.assertEqual(kwargs['grep_cost'], ['{W}'])
        self.assertEqual(kwargs['vgrep_cost'], ['{B}'])
        self.assertEqual(kwargs['grep_pt'], ['2/2'])
        self.assertEqual(kwargs['vgrep_pt'], ['1/1'])
        self.assertEqual(kwargs['grep_loyalty'], ['3'])
        self.assertEqual(kwargs['vgrep_loyalty'], ['5'])
        self.assertEqual(kwargs['id_counts'], ['2'])
        self.assertEqual(kwargs['mechanics'], ['Flying'])
        self.assertEqual(kwargs['booster'], 1)
        self.assertEqual(kwargs['box'], 1)

    @patch('jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    def test_limit_and_sample_flags(self, mock_file, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        # Test --limit
        test_args = ['mtg_subset.py', 'input.json', 'output.json', '--limit', '1', '--quiet']
        with patch('sys.argv', test_args):
            mtg_subset.main()

        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed_data = json.loads(written_data)

        # Should only contain one card
        total_cards = sum(len(s['cards']) for s in parsed_data['data'].values())
        self.assertEqual(total_cards, 1)

        mock_file.reset_mock()

        # Test --sample (shorthand for --shuffle --limit)
        test_args = ['mtg_subset.py', 'input.json', 'output.json', '--sample', '1', '--quiet']
        with patch('sys.argv', test_args):
            mtg_subset.main()

        kwargs = mock_open_file.call_args[1]
        self.assertTrue(kwargs['shuffle'])

    @patch('jdecode.mtg_open_file')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_no_cards_matched(self, mock_stderr, mock_open_file):
        mock_open_file.return_value = []

        test_args = ['mtg_subset.py', 'input.json', 'output.json']
        with patch('sys.argv', test_args), self.assertRaises(SystemExit) as cm:
            mtg_subset.main()

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("No cards matched", mock_stderr.getvalue())

    @patch('jdecode.mtg_open_file')
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_file_write_error(self, mock_stderr, mock_file, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_subset.py', 'input.json', 'output.json']
        with patch('sys.argv', test_args), self.assertRaises(SystemExit) as cm:
            mtg_subset.main()

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error writing subset", mock_stderr.getvalue())

    @patch('jdecode.mtg_open_file')
    @patch('sortlib.sort_cards')
    @patch('builtins.open', new_callable=mock_open)
    def test_sorting(self, mock_file, mock_sort, mock_open_file):
        mock_open_file.return_value = self.mock_cards
        mock_sort.return_value = self.mock_cards

        test_args = ['mtg_subset.py', 'input.json', 'output.json', '--sort', 'name', '--reverse', '--quiet']
        with patch('sys.argv', test_args):
            mtg_subset.main()

        mock_sort.assert_called_once_with(self.mock_cards, 'name', reverse=True, quiet=True)

    @patch('jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.print_operation_summary')
    def test_verbose_output(self, mock_summary, mock_file, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_subset.py', 'input.json', 'output.json']
        with patch('sys.argv', test_args):
            mtg_subset.main()

        mock_summary.assert_called_once_with("Subsetting", 2, 0, quiet=False)

if __name__ == '__main__':
    unittest.main()
