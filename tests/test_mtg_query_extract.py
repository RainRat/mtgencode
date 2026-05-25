import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import io
import json
import os
from scripts.mtg_query import handle_extract

class TestMtgQueryExtract(unittest.TestCase):
    def setUp(self):
        self.args = MagicMock()
        self.args.infile = 'test.json'
        self.args.set_code = 'TEST'
        self.args.card_name = 'Grizzly Bears'
        self.args.outfile = None
        self.args.verbose = False
        self.args.color = False
        self.args.quiet = False

    @patch('builtins.open', new_callable=mock_open, read_data='{"data": {"TEST": {"cards": [{"name": "Grizzly Bears"}]}}}')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_handle_extract_success(self, mock_stdout, mock_file):
        handle_extract(self.args)
        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Grizzly Bears')

    @patch('builtins.open', new_callable=mock_open, read_data='{"not_data": {}}')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_handle_extract_missing_data_key(self, mock_stderr, mock_file):
        handle_extract(self.args)
        self.assertIn("Error: 'data' key not found", mock_stderr.getvalue())

    @patch('builtins.open', new_callable=mock_open, read_data='{"data": {"OTHER": {}}}')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_handle_extract_set_not_found(self, mock_stderr, mock_file):
        handle_extract(self.args)
        self.assertIn("Error: Set code 'TEST' not found.", mock_stderr.getvalue())

    @patch('builtins.open', new_callable=mock_open, read_data='{"data": {"TEST": {"cards": [{"name": "Pikachu"}]}}}')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_handle_extract_card_not_found(self, mock_stderr, mock_file):
        handle_extract(self.args)
        self.assertIn("Error: Card 'Grizzly Bears' not found.", mock_stderr.getvalue())

    @patch('builtins.open', new_callable=mock_open, read_data='{"data": {"TEST": {"cards": [{"name": "Grizzly Bears"}]}}}')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_handle_extract_verbose(self, mock_stderr, mock_stdout, mock_file):
        self.args.verbose = True
        handle_extract(self.args)
        self.assertIn("Loading test.json...", mock_stderr.getvalue())
        self.assertIn("Grizzly Bears", mock_stdout.getvalue())

    @patch('builtins.open', new_callable=mock_open, read_data='{"data": {"ABC": {"cards": [{"name": "Grizzly Bears"}]}}}')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_handle_extract_any_set(self, mock_stdout, mock_file):
        self.args.set_code = 'ANY'
        handle_extract(self.args)
        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Grizzly Bears')

    @patch('builtins.open', side_effect=Exception("File not found"))
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_handle_extract_exception(self, mock_stderr, mock_file):
        handle_extract(self.args)
        self.assertIn("Error: File not found", mock_stderr.getvalue())

if __name__ == '__main__':
    unittest.main()
