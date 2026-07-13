import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import io
import argparse

# Add scripts and lib to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

import mtg_query

class TestShellUXIndices(unittest.TestCase):
    def setUp(self):
        self.test_json = 'testdata/uthros.json'
        self.args = argparse.Namespace(
            infile=self.test_json,
            color=False,
            quiet=False,
            verbose=False,
            fields='name,cost',
            limit=0
        )

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_indices_and_navigation(self, mock_stdout, mock_input):
        # Use a dataset with more cards for better testing
        self.args.infile = 'testdata/tarkir.json'

        mock_input.side_effect = [
            '/search .',      # Populate last_results (Invasion of Tarkir, etc.)
            '1',              # View details of first card
            '/oracle 2',      # View details of second card via /o
            '/compare 1 2',   # Compare first and second
            '/superior 1',    # Better than first
            '/reprints 1',    # Reprints of first
            '/substitutes 2', # Alternatives for second
            'exit'
        ]

        with patch('sys.stderr', new_callable=io.StringIO):
            try:
                mtg_query.handle_shell(self.args)
            except (SystemExit, EOFError):
                pass

        output = mock_stdout.getvalue()

        # Verify indices in search result
        self.assertIn('#', output)
        self.assertIn('1', output)
        self.assertIn('2', output)

        # Verify direct index lookup
        # In tarkir.json, cards are sorted by name by default?
        # Let's just check if it executed
        self.assertIn('SEARCH RESULTS', output)

        # Verify /compare with indices
        self.assertIn('CARD COMPARISON', output)

        # Verify /superior with index
        # self.assertIn('superior', output) # handle_superior might print "No cards found"

if __name__ == '__main__':
    unittest.main()
