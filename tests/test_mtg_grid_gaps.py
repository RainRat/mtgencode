import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import io
import json
import csv

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
import mtg_grid

class TestMTGGridGaps(unittest.TestCase):

    def setUp(self):
        self.card = MagicMock()
        self.card.color_identity = "W"
        self.card.rarity_name = "common"
        self.card._has_type.side_effect = lambda t: t == "Creature"
        self.card.cost.cmc = 1
        self.card.pt_p = "&^" # 1
        self.card.pt_t = "&^" # 1
        self.card.loyalty = None
        self.card.mechanics = []

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_no_cards_found(self, mock_stdout, mock_open_file):
        mock_open_file.return_value = []

        # Test standard no cards found (prints to stderr)
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            with patch('sys.argv', ['mtg_grid.py', 'type', 'color', 'dummy.json']):
                mtg_grid.main()
            self.assertIn("No cards found matching criteria", mock_stderr.getvalue())

        # Test quiet mode
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            with patch('sys.argv', ['mtg_grid.py', 'type', 'color', 'dummy.json', '--quiet']):
                mtg_grid.main()
            self.assertEqual("", mock_stderr.getvalue())

    @patch('jdecode.mtg_open_file')
    def test_auto_format_detection(self, mock_open_file):
        mock_open_file.return_value = [self.card]

        # JSON detection
        with patch('sys.argv', ['mtg_grid.py', 'type', 'color', 'dummy.json', 'output.json']):
            with patch('builtins.open', unittest.mock.mock_open()) as mocked_file:
                mtg_grid.main()
                # Check if it tried to write JSON (starts with '{' or '[')
                handle = mocked_file()
                written = "".join(call.args[0] for call in handle.write.call_args_list)
                self.assertTrue(written.strip().startswith('{'))

        # CSV detection
        with patch('sys.argv', ['mtg_grid.py', 'type', 'color', 'dummy.json', 'output.csv']):
            with patch('builtins.open', unittest.mock.mock_open()) as mocked_file:
                mtg_grid.main()
                handle = mocked_file()
                written = "".join(call.args[0] for call in handle.write.call_args_list)
                self.assertIn("Card Type / Color Identity", written)

        # Table detection (default for other extensions)
        with patch('sys.argv', ['mtg_grid.py', 'type', 'color', 'dummy.json', 'output.txt', '--no-color']):
            with patch('builtins.open', unittest.mock.mock_open()) as mocked_file:
                mtg_grid.main()
                handle = mocked_file()
                written = "".join(call.args[0] for call in handle.write.call_args_list)
                self.assertIn("CARD TYPE vs COLOR IDENTITY", written)

    @patch('jdecode.mtg_open_file')
    def test_colorized_table_output(self, mock_open_file):
        mock_open_file.return_value = [self.card]

        # Case 1: row=type, col=color
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch('sys.argv', ['mtg_grid.py', 'type', 'color', 'dummy.json', '--color']):
                mtg_grid.main()
            output = mock_stdout.getvalue()
            self.assertIn("\033[", output)
            self.assertIn("TOTAL", output)
            self.assertIn("CARD TYPE vs COLOR IDENTITY", output)
            self.assertIn("Card Type / Color Identity", output)

        # Case 2: row=color, col=rarity
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch('sys.argv', ['mtg_grid.py', 'color', 'rarity', 'dummy.json', '--color']):
                mtg_grid.main()
            output = mock_stdout.getvalue()
            self.assertIn("COLOR IDENTITY vs RARITY", output)

    @patch('jdecode.mtg_open_file')
    def test_additional_dimensions(self, mock_open_file):
        # Card with P/T and Loyalty
        pw_card = MagicMock()
        pw_card.color_identity = "R"
        pw_card.rarity_name = "mythic"
        pw_card._has_type.side_effect = lambda t: t == "Planeswalker"
        pw_card.cost.cmc = 4
        pw_card.pt_p = None
        pw_card.pt_t = None
        pw_card.loyalty = "&^^^" # 3
        pw_card.mechanics = []

        creature_card = MagicMock()
        creature_card.color_identity = "G"
        creature_card.rarity_name = "uncommon"
        creature_card._has_type.side_effect = lambda t: t == "Creature"
        creature_card.cost.cmc = 2
        creature_card.pt_p = "&^^" # 2
        creature_card.pt_t = "&^^^" # 3
        creature_card.loyalty = None
        creature_card.mechanics = []

        mock_open_file.return_value = [pw_card, creature_card]

        # Test Power vs Toughness
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch('sys.argv', ['mtg_grid.py', 'power', 'toughness', 'dummy.json', '--json', '--quiet']):
                mtg_grid.main()
            data = json.loads(mock_stdout.getvalue())
            self.assertEqual(data['matrix']['2']['3'], 1)

        # Test Loyalty vs CMC
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch('sys.argv', ['mtg_grid.py', 'loyalty', 'cmc', 'dummy.json', '--json', '--quiet']):
                mtg_grid.main()
            data = json.loads(mock_stdout.getvalue())
            # pw has 3 loyalty, 4 CMC
            self.assertEqual(data['matrix']['3']['4'], 1)

    def test_format_type_coverage(self):
        # Test special types
        self.assertIn("\033[", mtg_grid.format_type("Creature", True))
        self.assertIn("\033[", mtg_grid.format_type("Land", True))
        # Test non-special type
        self.assertIn("\033[", mtg_grid.format_type("Sorcery", True))
        # Test no color
        self.assertEqual("Sorcery", mtg_grid.format_type("Sorcery", False))

    @patch('jdecode.mtg_open_file')
    def test_operation_summary_standard(self, mock_open_file):
        mock_open_file.return_value = [self.card]
        # Standard mode (not quiet) should print summary to stderr
        with patch('sys.stdout', new=io.StringIO()):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                with patch('sys.argv', ['mtg_grid.py', 'type', 'color', 'dummy.json', '--no-color']):
                    mtg_grid.main()
                self.assertIn("Grid Analysis complete", mock_stderr.getvalue())

    def test_bucket_numeric_extreme(self):
        # Coverage for v < 0 in bucket_numeric
        self.assertEqual(mtg_grid.bucket_numeric(-5), "0")
        # Coverage for non-intable float
        self.assertEqual(mtg_grid.bucket_numeric(float('nan')), None)

if __name__ == '__main__':
    unittest.main()
