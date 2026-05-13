import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import io
import csv

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
import mtg_grid

class TestMTGGrid(unittest.TestCase):

    def setUp(self):
        # Mock cards with various attributes
        self.card1 = MagicMock()
        self.card1.color_identity = "W"
        self.card1.rarity_name = "rare"
        self.card1._has_type.side_effect = lambda t: t == "Creature"
        self.card1.cost.cmc = 3
        self.card1.pt_p = "&&&" # 3
        self.card1.pt_t = "&&&" # 3
        self.card1.loyalty = None
        self.card1.mechanics = ["Flying"]

        self.card2 = MagicMock()
        self.card2.color_identity = "UB"
        self.card2.rarity_name = "mythic"
        self.card2._has_type.side_effect = lambda t: t == "Sorcery"
        self.card2.cost.cmc = 5
        self.card2.pt_p = None
        self.card2.pt_t = None
        self.card2.loyalty = None
        self.card2.mechanics = ["Kicker", "Draw A Card"]

        self.mock_cards = [self.card1, self.card2]

    def test_bucket_numeric(self):
        self.assertEqual(mtg_grid.bucket_numeric(None), None)
        self.assertEqual(mtg_grid.bucket_numeric(0), "0")
        self.assertEqual(mtg_grid.bucket_numeric(3), "3")
        self.assertEqual(mtg_grid.bucket_numeric(6), "6")
        self.assertEqual(mtg_grid.bucket_numeric(7), "7+")
        self.assertEqual(mtg_grid.bucket_numeric(10), "7+")
        self.assertEqual(mtg_grid.bucket_numeric(-1), "0")
        self.assertEqual(mtg_grid.bucket_numeric("3"), "3")
        self.assertEqual(mtg_grid.bucket_numeric(3.5), "3")
        self.assertEqual(mtg_grid.bucket_numeric("invalid"), None)

    def test_get_color_group(self):
        self.assertEqual(mtg_grid.get_color_group(self.card1), "W")
        self.assertEqual(mtg_grid.get_color_group(self.card2), "M")

        card_colorless = MagicMock()
        card_colorless.color_identity = ""
        self.assertEqual(mtg_grid.get_color_group(card_colorless), "A")

    def test_get_card_type(self):
        self.assertEqual(mtg_grid.get_card_type(self.card1), "Creature")
        self.assertEqual(mtg_grid.get_card_type(self.card2), "Sorcery")

        card_other = MagicMock()
        card_other._has_type.return_value = False
        self.assertEqual(mtg_grid.get_card_type(card_other), "Other")

    def test_format_type(self):
        self.assertEqual(mtg_grid.format_type("Creature", False), "Creature")
        # Colorized output is harder to assert exactly without ANSI constants,
        # but we can check it's different
        self.assertNotEqual(mtg_grid.format_type("Creature", True), "Creature")
        self.assertIn("Creature", mtg_grid.format_type("Creature", True))

    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_smart_positional_args(self, mock_stdout, mock_open_file, mock_exists):
        mock_exists.side_effect = lambda p: p == 'existing.json'
        mock_open_file.return_value = self.mock_cards

        # Case 1: Query only
        test_args = ['mtg_grid.py', 'type', 'color', 'Grizzly', '--quiet']
        with patch('sys.argv', test_args):
            mtg_grid.main()
        self.assertEqual(mock_open_file.call_args[1]['grep'], ['Grizzly'])

        # Case 2: File and query (should not swap because row/col are fixed)
        # Wait, the script says:
        # if args.infile != '-' and not os.path.exists(args.infile):
        #    if not args.grep:
        #        args.grep = [args.infile]
        #        args.infile = '-'

        test_args = ['mtg_grid.py', 'type', 'color', 'nonexistent.json', '--quiet']
        with patch('sys.argv', test_args):
            mtg_grid.main()
        self.assertEqual(mock_open_file.call_args[1]['grep'], ['nonexistent.json'])
        self.assertEqual(mock_open_file.call_args[0][0], '-')

    @patch('sys.stdin.isatty', return_value=True)
    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file')
    def test_default_dataset_detection(self, mock_open_file, mock_exists, mock_isatty):
        mock_exists.side_effect = lambda p: p.endswith('AllPrintings.json')
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_grid.py', 'type', 'color', '--quiet']
        with patch('sys.argv', test_args), patch('sys.stdout', new_callable=io.StringIO):
            mtg_grid.main()

        self.assertIn('AllPrintings.json', mock_open_file.call_args[0][0])

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_table_output(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_grid.py', 'type', 'color', 'dummy.json', '--no-color', '--quiet']
        with patch('sys.argv', test_args):
            mtg_grid.main()

        output = mock_stdout.getvalue()
        self.assertIn("CARD TYPE vs COLOR IDENTITY", output)
        self.assertIn("Creature", output)
        self.assertIn("Sorcery", output)
        self.assertIn("TOTAL", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_json_output(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_grid.py', 'type', 'color', 'dummy.json', '--json', '--quiet']
        with patch('sys.argv', test_args):
            mtg_grid.main()

        data = json.loads(mock_stdout.getvalue())
        self.assertEqual(data['total_cards'], 2)
        self.assertEqual(data['matrix']['Creature']['W'], 1)
        self.assertEqual(data['matrix']['Sorcery']['M'], 1)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_csv_output(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_grid.py', 'type', 'color', 'dummy.json', '--csv', '--quiet']
        with patch('sys.argv', test_args):
            mtg_grid.main()

        reader = csv.reader(io.StringIO(mock_stdout.getvalue()))
        rows = list(reader)
        self.assertEqual(rows[0][0], "Card Type / Color Identity")
        # Find creature row
        creature_row = next(r for r in rows if r[0] == "Creature")
        # W is usually the first color in WUBRGAM
        self.assertEqual(creature_row[1], "1")

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mechanic_dimension(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = self.mock_cards

        test_args = ['mtg_grid.py', 'mechanic', 'color', 'dummy.json', '--json', '--quiet']
        with patch('sys.argv', test_args):
            mtg_grid.main()

        data = json.loads(mock_stdout.getvalue())
        # Flying (card 1) is W
        self.assertEqual(data['matrix']['Flying']['W'], 1)
        # Kicker (card 2) is M
        self.assertEqual(data['matrix']['Kicker']['M'], 1)
        # Draw A Card (card 2) is M
        self.assertEqual(data['matrix']['Draw A Card']['M'], 1)

    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file')
    def test_filtering_propagation(self, mock_open_file, mock_exists):
        mock_exists.return_value = True
        mock_open_file.return_value = self.mock_cards

        test_args = [
            'mtg_grid.py', 'type', 'color', 'dummy.json',
            '--set', 'MOM', '--rarity', 'rare', '-g', 'flying',
            '--cmc', '3', '--colors', 'W', '--identity', 'WU',
            '--pow', '2', '--tou', '2', '--mechanic', 'Flying',
            '--limit', '10', '--quiet'
        ]
        with patch('sys.argv', test_args), patch('sys.stdout', new_callable=io.StringIO):
            mtg_grid.main()

        kwargs = mock_open_file.call_args[1]
        self.assertEqual(kwargs['sets'], ['MOM'])
        self.assertEqual(kwargs['rarities'], ['rare'])
        self.assertEqual(kwargs['grep'], ['flying'])
        self.assertEqual(kwargs['cmcs'], ['3'])
        self.assertEqual(kwargs['colors'], ['W'])
        self.assertEqual(kwargs['identities'], ['WU'])
        self.assertEqual(kwargs['pows'], ['2'])
        self.assertEqual(kwargs['tous'], ['2'])
        self.assertEqual(kwargs['mechanics'], ['Flying'])

if __name__ == '__main__':
    unittest.main()
