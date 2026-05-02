import unittest
from unittest.mock import MagicMock, patch, mock_open
import io
import sys
import os
import json

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_subset import main as subset_main
import scripts.mtg_subset

class TestMtgSubset(unittest.TestCase):

    def setUp(self):
        self.card1 = MagicMock()
        self.card1.set_code = "MOM"
        self.card1.name = "Card A"
        self.card1.to_dict.return_value = {"name": "Card A", "set_code": "MOM"}

        self.card2 = MagicMock()
        self.card2.set_code = "ONE"
        self.card2.name = "Card B"
        self.card2.to_dict.return_value = {"name": "Card B", "set_code": "ONE"}

    @patch('scripts.mtg_subset.jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_subset_basic(self, mock_stdout, mock_file, mock_open_file):
        mock_open_file.return_value = [self.card1, self.card2]

        with patch('sys.argv', ['mtg_subset.py', 'input.json', 'output.json']):
            subset_main()

        # Verify mtg_open_file was called
        mock_open_file.assert_called_once()

        # Verify file write
        mock_file.assert_called_with('output.json', 'w', encoding='utf-8')

        # Capture the written content
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        data = json.loads(written_data)

        self.assertIn("data", data)
        self.assertIn("MOM", data["data"])
        self.assertIn("ONE", data["data"])
        self.assertEqual(data["data"]["MOM"]["cards"][0]["name"], "Card A")

    @patch('scripts.mtg_subset.jdecode.mtg_open_file')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_subset_no_matches(self, mock_stderr, mock_open_file):
        mock_open_file.return_value = []

        with patch('sys.argv', ['mtg_subset.py', 'input.json', 'output.json']):
            with self.assertRaises(SystemExit) as cm:
                subset_main()

            self.assertEqual(cm.exception.code, 1)
            self.assertIn("No cards matched the filters", mock_stderr.getvalue())

    @patch('scripts.mtg_subset.jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    def test_subset_filtering_args(self, mock_file, mock_open_file):
        mock_open_file.return_value = [self.card1]

        with patch('sys.argv', ['mtg_subset.py', 'in.json', 'out.json',
                                '--set', 'MOM', '--rarity', 'rare',
                                '--grep', 'test', '--cmc', '>2']):
            subset_main()

            mock_open_file.assert_called_with(
                'in.json', verbose=False,
                grep=['test'], vgrep=None,
                grep_name=None, vgrep_name=None,
                grep_types=None, vgrep_types=None,
                grep_text=None, vgrep_text=None,
                grep_cost=None, vgrep_cost=None,
                grep_pt=None, vgrep_pt=None,
                grep_loyalty=None, vgrep_loyalty=None,
                sets=['MOM'], rarities=['rare'],
                colors=None, cmcs=['>2'],
                pows=None, tous=None, loys=None,
                mechanics=None,
                identities=None, id_counts=None,
                decklist_file=None,
                booster=0, box=0,
                shuffle=False
            )

    @patch('scripts.mtg_subset.jdecode.mtg_open_file')
    @patch('sortlib.sort_cards')
    @patch('builtins.open', new_callable=mock_open)
    def test_subset_sorting(self, mock_file, mock_sort, mock_open_file):
        mock_open_file.return_value = [self.card1, self.card2]
        mock_sort.return_value = [self.card1, self.card2]

        with patch('sys.argv', ['mtg_subset.py', 'in.json', 'out.json', '--sort', 'name', '--reverse']):
            subset_main()
            mock_sort.assert_called_with([self.card1, self.card2], 'name', reverse=True, quiet=False)

    @patch('scripts.mtg_subset.jdecode.mtg_open_file')
    @patch('builtins.open', new_callable=mock_open)
    def test_subset_limit_and_sample(self, mock_file, mock_open_file):
        mock_open_file.return_value = [self.card1, self.card2]

        # Test limit
        with patch('sys.argv', ['mtg_subset.py', 'in.json', 'out.json', '--limit', '1']):
            subset_main()

            handle = mock_file()
            written_data = "".join(call.args[0] for call in handle.write.call_args_list)
            data = json.loads(written_data)
            # Only one card should be in the output
            total_cards = sum(len(s["cards"]) for s in data["data"].values())
            self.assertEqual(total_cards, 1)

        # Test sample (sets shuffle=True and limit=N)
        mock_open_file.reset_mock()
        with patch('sys.argv', ['mtg_subset.py', 'in.json', 'out.json', '--sample', '1']):
            subset_main()
            # Verify shuffle=True was passed to mtg_open_file
            args, kwargs = mock_open_file.call_args
            self.assertEqual(kwargs['shuffle'], True)

    @patch('scripts.mtg_subset.jdecode.mtg_open_file')
    @patch('builtins.open', side_effect=Exception("Write error"))
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_subset_write_error(self, mock_stderr, mock_file, mock_open_file):
        mock_open_file.return_value = [self.card1]

        with patch('sys.argv', ['mtg_subset.py', 'in.json', 'out.json']):
            with self.assertRaises(SystemExit) as cm:
                subset_main()

            self.assertEqual(cm.exception.code, 1)
            self.assertIn("Error writing subset to out.json", mock_stderr.getvalue())

if __name__ == '__main__':
    unittest.main()
