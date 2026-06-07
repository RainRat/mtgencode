import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import io
import json
import os

# Add scripts and lib to path
current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_dir, '../scripts'))
sys.path.append(os.path.join(current_dir, '../lib'))

import mtg_llm_validate
import cardlib

class TestMtgLlmValidateGaps(unittest.TestCase):

    def test_parse_llm_response_fallback(self):
        mock_card = MagicMock(spec=cardlib.Card)
        res = mtg_llm_validate.parse_llm_response("Malformed output", mock_card)
        self.assertEqual(res['judgment'], 'UNKNOWN')
        self.assertEqual(res['reason'], 'Reason not found in LLM response.')

    @patch('urllib.request.urlopen')
    def test_validate_cards_llm_api_error_handling(self, mock_urlopen):
        mock_card = MagicMock(spec=cardlib.Card)
        mock_card.name = "Error Card"
        mock_card.format.return_value = "Rules"

        mock_urlopen.side_effect = Exception("API Down")

        cards = [mock_card]
        results = mtg_llm_validate.validate_cards_llm(
            cards, "model", "cpu", provider='api', api_url="http://test.api"
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['judgment'], 'UNKNOWN')
        self.assertIn("API Error: API Down", results[0]['reason'])

    @patch('mtg_llm_validate.validate_cards_llm')
    @patch('jdecode.mtg_open_file')
    def test_main_csv_output(self, mock_open_file, mock_validate):
        mock_card = MagicMock(spec=cardlib.Card)
        mock_card.name = "CSV Card"
        mock_card.text = MagicMock()
        mock_card.text.text = "Card text"
        mock_open_file.return_value = [mock_card]

        mock_validate.return_value = [{
            'card': mock_card,
            'judgment': 'VALID',
            'reason': 'Good card'
        }]

        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()):
            with patch('sys.argv', ['mtg_llm_validate.py', 'dummy.txt', '--csv']):
                mtg_llm_validate.main()

        output = stdout.getvalue()
        self.assertIn("name,judgment,reason,text", output)
        self.assertIn("CSV Card,VALID,Good card,Card text", output)

    @patch('mtg_llm_validate.validate_cards_llm')
    @patch('jdecode.mtg_open_file')
    def test_main_limit(self, mock_open_file, mock_validate):
        cards = [MagicMock(spec=cardlib.Card) for _ in range(3)]
        mock_open_file.return_value = cards
        mock_validate.return_value = []

        with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
            with patch('sys.argv', ['mtg_llm_validate.py', 'dummy.txt', '--limit', '2']):
                mtg_llm_validate.main()

        # Verify that validate_cards_llm was called with only 2 cards
        self.assertEqual(len(mock_validate.call_args[0][0]), 2)

    @patch('jdecode.mtg_open_file')
    @patch('os.path.exists')
    def test_main_smart_positional_grep(self, mock_exists, mock_open_file):
        # mock_exists returns False for the query and True for the file
        mock_exists.side_effect = lambda x: x == 'real_file.json'
        mock_open_file.return_value = []

        with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
            # mtg_llm_validate.py query real_file.json
            with patch('sys.argv', ['mtg_llm_validate.py', 'SomeQuery', 'real_file.json']):
                mtg_llm_validate.main()

        # Verify it swapped SomeQuery to grep and used real_file.json as infile
        mock_open_file.assert_called()
        args, kwargs = mock_open_file.call_args
        self.assertEqual(args[0], 'real_file.json')
        self.assertEqual(kwargs['grep'], ['SomeQuery'])

    @patch('jdecode.mtg_open_file')
    @patch('mtg_llm_validate.pipeline', None)
    def test_main_missing_transformers_exit(self, mock_open_file):
        mock_open_file.return_value = [MagicMock(spec=cardlib.Card)]
        with patch('sys.stderr', io.StringIO()):
            with patch('sys.argv', ['mtg_llm_validate.py', 'dummy.txt']):
                with self.assertRaises(SystemExit) as cm:
                    mtg_llm_validate.main()
                self.assertEqual(cm.exception.code, 1)

if __name__ == '__main__':
    unittest.main()
