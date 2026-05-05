import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
import json
import io
import csv

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
import mtg_skeleton

class TestMTGSkeleton(unittest.TestCase):

    def setUp(self):
        # Mock cards with various types and CMCs
        self.card_creature_1 = MagicMock()
        self.card_creature_1.types = ["Creature"]
        self.card_creature_1._has_type.side_effect = lambda t: t == "Creature"
        self.card_creature_1.cost.cmc = 1

        self.card_instant_2 = MagicMock()
        self.card_instant_2.types = ["Instant"]
        self.card_instant_2._has_type.side_effect = lambda t: t == "Instant"
        self.card_instant_2.cost.cmc = 2

        self.card_other_10 = MagicMock()
        self.card_other_10.types = ["Kindle"] # Not in tracked_types
        self.card_other_10._has_type.side_effect = lambda t: False
        self.card_other_10.cost.cmc = 10 # Should go to 7+

        self.mock_cards = [self.card_creature_1, self.card_instant_2, self.card_other_10]

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_basic_skeleton_table(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_skeleton.py', 'dummy.json', '--no-color']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()

        output = mock_stdout.getvalue()
        self.assertIn("DESIGN SKELETON", output)
        self.assertIn("Creature", output)
        self.assertIn("Instant", output)
        self.assertIn("Other", output)
        self.assertIn("TOTAL", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_json_output(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_skeleton.py', 'dummy.json', '--json', '--quiet']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()

        output_data = json.loads(mock_stdout.getvalue())
        self.assertEqual(output_data['total_cards'], 3)
        self.assertEqual(output_data['grand_total'], 3)

        # Find creature row
        creature_row = next(r for r in output_data['skeleton'] if r['type'] == 'Creature')
        self.assertEqual(creature_row['buckets']['1'], 1)
        self.assertEqual(creature_row['total'], 1)

        # Find other row
        other_row = next(r for r in output_data['skeleton'] if r['type'] == 'Other')
        self.assertEqual(other_row['buckets']['7+'], 1)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_csv_output(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_skeleton.py', 'dummy.json', '--csv', '--quiet']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()

        output = mock_stdout.getvalue()
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)

        self.assertEqual(rows[0][0], "Type")
        # Find creature row
        creature_row = next(r for r in rows if r[0] == "Creature")
        self.assertEqual(creature_row[2], "1") # CMC 1 is at index 2 (Type=0, CMC0=1, CMC1=2)

    @patch('jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    def test_file_output_auto_detect_json(self, mock_file, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_skeleton.py', 'dummy.json', 'output.json', '--quiet']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()

        mock_file.assert_called_with('output.json', 'w', encoding='utf-8')
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        json.loads(written_data) # Verify it's valid JSON

    @patch('jdecode.mtg_open_file')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_no_cards_found(self, mock_stderr, mock_open_file):
        mock_open_file.return_value = []

        test_args = ['mtg_skeleton.py', 'dummy.json']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()

        self.assertIn("No cards found", mock_stderr.getvalue())

    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file')
    def test_filtering_propagation(self, mock_open_file, mock_exists):
        mock_exists.return_value = True
        mock_open_file.return_value = self.mock_cards

        test_args = [
            'mtg_skeleton.py', 'dummy.json',
            '--set', 'MOM', '--rarity', 'rare', '-g', 'flying',
            '--cmc', '3', '--colors', 'W', '--identity', 'WU',
            '--pow', '2', '--tou', '2', '--loy', '3',
            '--mechanic', 'Flying', '--booster', '1', '--box', '1',
            '--shuffle', '--seed', '42', '--limit', '10'
        ]
        with patch('sys.argv', test_args), patch('sys.stdout', new_callable=io.StringIO):
            mtg_skeleton.main()

        kwargs = mock_open_file.call_args[1]
        self.assertEqual(kwargs['sets'], ['MOM'])
        self.assertEqual(kwargs['rarities'], ['rare'])
        self.assertEqual(kwargs['grep'], ['flying'])
        self.assertEqual(kwargs['cmcs'], ['3'])
        self.assertEqual(kwargs['colors'], ['W'])
        self.assertEqual(kwargs['identities'], ['WU'])
        self.assertEqual(kwargs['pows'], ['2'])
        self.assertEqual(kwargs['tous'], ['2'])
        self.assertEqual(kwargs['loys'], ['3'])
        self.assertEqual(kwargs['mechanics'], ['Flying'])
        self.assertEqual(kwargs['booster'], 1)
        self.assertEqual(kwargs['box'], 1)
        self.assertTrue(kwargs['shuffle'])
        self.assertEqual(kwargs['seed'], 42)

    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file')
    def test_smart_positional_args(self, mock_open_file, mock_exists):
        # Case: infile is a query, no outfile
        mock_exists.side_effect = lambda p: p == 'data/AllPrintings.json' # Default exists, but 'MOM' doesn't
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_skeleton.py', 'MOM', '--quiet']
        with patch('sys.argv', test_args), patch('sys.stdout', new_callable=io.StringIO):
            mtg_skeleton.main()

        mock_open_file.assert_called()
        self.assertEqual(mock_open_file.call_args[1]['grep'], ['MOM'])

    @patch('jdecode.mtg_open_file')
    @patch('utils.print_operation_summary')
    def test_operation_summary(self, mock_summary, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_skeleton.py', 'dummy.json']
        with patch('sys.argv', test_args), patch('sys.stdout', new_callable=io.StringIO):
            mtg_skeleton.main()

        mock_summary.assert_called_with("Skeleton Analysis", 3, 0, quiet=False)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_verbose_quiet_flags(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        # Test quiet
        test_args = ['mtg_skeleton.py', 'dummy.json', '--quiet']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()
        self.assertEqual(mock_stdout.getvalue(), "")

        mock_stdout.truncate(0)
        mock_stdout.seek(0)

        # Test verbose
        test_args = ['mtg_skeleton.py', 'dummy.json', '--verbose', '--no-color']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()
        self.assertIn("DESIGN SKELETON", mock_stdout.getvalue())

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_sample_flag(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards
        test_args = ['mtg_skeleton.py', 'dummy.json', '--sample', '2', '--quiet']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()

        # Verify limit and shuffle were passed
        kwargs = mock_open_file.call_args[1]
        self.assertTrue(kwargs['shuffle'])
        # The script slices the cards returned from mtg_open_file

    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_smart_positional_args_with_outfile(self, mock_stdout, mock_open_file, mock_exists):
        # Case: infile is a query, outfile is a file that exists
        mock_exists.side_effect = lambda p: p == 'existing_file.json'
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_skeleton.py', 'query', 'existing_file.json', '--quiet']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()

        self.assertEqual(mock_open_file.call_args[0][0], 'existing_file.json')
        self.assertEqual(mock_open_file.call_args[1]['grep'], ['query'])

    @patch('sys.stdout.isatty', return_value=True)
    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_color_output_enabled(self, mock_stdout, mock_open_file, mock_isatty):
        mock_open_file.return_value = self.mock_cards
        test_args = ['mtg_skeleton.py', 'dummy.json']
        # Force color detection by mocking isatty
        with patch('sys.argv', test_args):
            mtg_skeleton.main()
        # If color was used, we should see ANSI escape codes
        self.assertIn("\033[", mock_stdout.getvalue())

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_force_color(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards
        test_args = ['mtg_skeleton.py', 'dummy.json', '--color']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()
        self.assertIn("\033[", mock_stdout.getvalue())

    @patch('os.path.exists', return_value=False)
    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_smart_positional_args_query_only(self, mock_stdout, mock_open_file, mock_exists):
        mock_open_file.return_value = self.mock_cards
        test_args = ['mtg_skeleton.py', 'query', '--quiet']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()
        self.assertEqual(mock_open_file.call_args[1]['grep'], ['query'])

    @patch('sys.stdin.isatty', return_value=True)
    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_default_dataset_detection(self, mock_stdout, mock_open_file, mock_exists, mock_isatty):
        mock_exists.side_effect = lambda p: p.endswith('AllPrintings.json')
        mock_open_file.return_value = self.mock_cards
        test_args = ['mtg_skeleton.py', '--quiet']
        with patch('sys.argv', test_args):
            mtg_skeleton.main()
        self.assertIn('AllPrintings.json', mock_open_file.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
