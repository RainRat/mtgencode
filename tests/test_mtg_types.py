import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import io
import csv

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
import scripts.mtg_analyze as mtg_analyze

class TestMTGTypes(unittest.TestCase):

    def setUp(self):
        # Mock cards with various types and color identities
        self.card_w_creature = MagicMock()
        self.card_w_creature.color_identity = "W"
        self.card_w_creature._has_type.side_effect = lambda t: t == "Creature"

        self.card_u_instant = MagicMock()
        self.card_u_instant.color_identity = "U"
        self.card_u_instant._has_type.side_effect = lambda t: t == "Instant"

        self.card_multi_sorcery = MagicMock()
        self.card_multi_sorcery.color_identity = "UB"
        self.card_multi_sorcery._has_type.side_effect = lambda t: t == "Sorcery"

        self.card_colorless_artifact = MagicMock()
        self.card_colorless_artifact.color_identity = ""
        self.card_colorless_artifact._has_type.side_effect = lambda t: t == "Artifact"

        self.mock_cards = [
            self.card_w_creature,
            self.card_u_instant,
            self.card_multi_sorcery,
            self.card_colorless_artifact
        ]

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_basic_table_output(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_analyze.py', 'types', 'dummy.json', '--no-color']
        with patch('sys.argv', test_args):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        self.assertIn("TYPE / COLOR DISTRIBUTION", output)
        self.assertIn("Creature", output)
        self.assertIn("Instant", output)
        self.assertIn("Sorcery", output)
        self.assertIn("Artifact", output)
        self.assertIn("TOTAL", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_json_output(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_analyze.py', 'types', 'dummy.json', '--json', '--quiet']
        with patch('sys.argv', test_args):
            mtg_analyze.main()

        output_data = json.loads(mock_stdout.getvalue())
        self.assertEqual(output_data['primary']['total'], 4)

        matrix = output_data['primary']['matrix']
        self.assertEqual(matrix['Creature']['W'], 1)
        self.assertEqual(matrix['Instant']['U'], 1)
        self.assertEqual(matrix['Sorcery']['M'], 1)
        self.assertEqual(matrix['Artifact']['A'], 1)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_csv_output(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_analyze.py', 'types', 'dummy.json', '--csv', '--quiet']
        with patch('sys.argv', test_args):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)

        self.assertEqual(rows[0][0], "Type")
        # Check specific row
        creature_row = next(r for r in rows if r[0] == "Creature")
        # Header: Type, W, U, B, R, G, A, M, Total
        # W is index 1
        self.assertEqual(creature_row[1], "1")

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_comparison_mode(self, mock_stdout, mock_open_file):
        # First call for primary, second for comparison
        mock_open_file.side_effect = [
            self.mock_cards,
            self.mock_cards + [self.card_w_creature] # Add one more W creature
        ]

        test_args = ['mtg_analyze.py', 'types', 'dummy.json', '--compare', 'comp.json', '--no-color']
        with patch('sys.argv', test_args):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        self.assertIn("(COMPARISON)", output)
        # Check for delta indicator (Up arrow)
        self.assertIn("▲", output)

    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file')
    def test_filtering_propagation(self, mock_open_file, mock_exists):
        mock_exists.return_value = True
        mock_open_file.return_value = self.mock_cards

        test_args = [
            'mtg_analyze.py', 'dummy.json',
            '--set', 'MOM', '--rarity', 'rare', '-g', 'flying',
            '--cmc', '3', '--colors', 'W', '--identity', 'WU',
            '--pow', '2', '--tou', '2', '--loy', '3',
            '--mechanic', 'Flying', '--booster', '1', '--box', '1',
            '--shuffle', '--seed', '42', '--limit', '10'
        ]
        with patch('sys.argv', test_args), patch('sys.stdout', new_callable=io.StringIO):
            mtg_analyze.main()

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
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_smart_positional_args(self, mock_stdout, mock_open_file, mock_exists):
        mock_exists.side_effect = lambda p: p == 'existing.json'
        mock_open_file.return_value = self.mock_cards

        # Case 1: Query only
        test_args = ['mtg_analyze.py', 'types', 'Grizzly', '--quiet']
        with patch('sys.argv', test_args):
            mtg_analyze.main()
        self.assertEqual(mock_open_file.call_args[1]['grep'], ['Grizzly'])

        # Case 2: File and query
        test_args = ['mtg_analyze.py', 'types', 'existing.json', 'Bears', '--quiet']
        with patch('sys.argv', test_args):
            mtg_analyze.main()
        self.assertEqual(mock_open_file.call_args[0][0], 'existing.json')
        self.assertEqual(mock_open_file.call_args[1]['grep'], ['Bears'])

    @patch('sys.stdin.isatty', return_value=True)
    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file')
    def test_default_dataset_detection(self, mock_open_file, mock_exists, mock_isatty):
        mock_exists.side_effect = lambda p: p.endswith('AllPrintings.json')
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_analyze.py', 'types', '--quiet']
        with patch('sys.argv', test_args), patch('sys.stdout', new_callable=io.StringIO):
            mtg_analyze.main()

        self.assertIn('AllPrintings.json', mock_open_file.call_args[0][0])

    @patch('jdecode.mtg_open_file')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_no_cards_found(self, mock_stderr, mock_open_file):
        mock_open_file.return_value = []

        test_args = ['mtg_analyze.py', 'types', 'dummy.json']
        with patch('sys.argv', test_args):
            mtg_analyze.main()

        self.assertIn("No cards found", mock_stderr.getvalue())

if __name__ == '__main__':
    unittest.main()
