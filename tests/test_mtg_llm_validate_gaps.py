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
        self.assertEqual(res['reason'], 'Reason not found in AI model response.')

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

    @patch('urllib.request.urlopen')
    def test_validate_cards_llm_api_verbose_error(self, mock_urlopen):
        mock_card = MagicMock(spec=cardlib.Card)
        mock_card.name = "Error Card Verbose"
        mock_card.format.return_value = "Rules"

        mock_urlopen.side_effect = Exception("Verbose API Failure")

        cards = [mock_card]
        stderr = io.StringIO()
        with patch('sys.stderr', stderr):
            results = mtg_llm_validate.validate_cards_llm(
                cards, "model", "cpu", provider='api', api_url="http://test.api", verbose=True
            )

        self.assertEqual(len(results), 1)
        self.assertIn("Error calling API for card 'Error Card Verbose': Verbose API Failure", stderr.getvalue())

    def test_validate_cards_llm_api_missing_url(self):
        mock_card = MagicMock(spec=cardlib.Card)
        with patch('sys.stderr', io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                mtg_llm_validate.validate_cards_llm([mock_card], "model", "cpu", provider='api', api_url=None)
            self.assertEqual(cm.exception.code, 1)

    @patch('mtg_llm_validate.pipeline')
    def test_validate_cards_llm_pipeline_init_exception(self, mock_pipeline):
        mock_pipeline.side_effect = Exception("CUDA Out of Memory")
        mock_card = MagicMock(spec=cardlib.Card)

        stderr = io.StringIO()
        with patch('sys.stderr', stderr):
            with self.assertRaises(SystemExit) as cm:
                mtg_llm_validate.validate_cards_llm([mock_card], "model", "cuda", provider='transformers', verbose=True)
            self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error initializing model: CUDA Out of Memory", stderr.getvalue())

    @patch('mtg_llm_validate.pipeline')
    def test_validate_cards_llm_transformers_response_formatting(self, mock_pipeline):
        mock_card = MagicMock(spec=cardlib.Card)
        mock_card.name = "Format Card"
        mock_card.format.return_value = "Format rules"

        mock_pipe = MagicMock()
        mock_pipe.tokenizer.eos_token_id = 2
        # Single dict output rather than list of dicts to test single output normalization
        mock_pipe.return_value = [{'generated_text': "Plain JUDGMENT: VALID\nREASON: Output without assistant tag"}]
        mock_pipeline.return_value = mock_pipe

        results = mtg_llm_validate.validate_cards_llm([mock_card], "model", "cpu", provider='transformers')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['judgment'], 'VALID')
        self.assertEqual(results[0]['reason'], 'Output without assistant tag')

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
    def test_main_no_cards_verbose(self, mock_open_file):
        mock_open_file.return_value = []
        stderr = io.StringIO()
        with patch('sys.stderr', stderr):
            with patch('sys.argv', ['mtg_llm_validate.py', 'dummy.txt', '-v']):
                mtg_llm_validate.main()

        self.assertIn("No cards found matching criteria.", stderr.getvalue())

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

    @patch('mtg_llm_validate.validate_cards_llm')
    @patch('jdecode.mtg_open_file')
    def test_main_dry_run_transformers(self, mock_open_file, mock_validate):
        mock_card = MagicMock(spec=cardlib.Card)
        mock_card.name = "DryRun Card"
        mock_open_file.return_value = [mock_card]

        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()):
            with patch('sys.argv', ['mtg_llm_validate.py', 'dummy.txt', '--dry-run', '--json', '--only-valid']):
                mtg_llm_validate.main()

        output = stdout.getvalue()
        self.assertIn("Dry Run Summary: 1 card(s) identified for AI validation.", output)
        self.assertIn("Model: TinyLlama/TinyLlama-1.1B-Chat-v1.0", output)
        self.assertIn("Provider: transformers", output)
        self.assertIn("Output Format: JSON (Only Valid)", output)
        self.assertIn("Sample Preview (up to 10): DryRun Card", output)
        mock_validate.assert_not_called()

    @patch('mtg_llm_validate.validate_cards_llm')
    @patch('jdecode.mtg_open_file')
    def test_main_dry_run_api_provider(self, mock_open_file, mock_validate):
        mock_card = MagicMock(spec=cardlib.Card)
        mock_card.name = "API DryRun Card"
        mock_open_file.return_value = [mock_card]

        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()):
            with patch('sys.argv', ['mtg_llm_validate.py', 'dummy.txt', '-p', '--provider', 'api', '--api-url', 'http://localhost:11434/v1/chat/completions']):
                mtg_llm_validate.main()

        output = stdout.getvalue()
        self.assertIn("Dry Run Summary: 1 card(s) identified for AI validation.", output)
        self.assertIn("Provider: api", output)
        self.assertIn("API URL: http://localhost:11434/v1/chat/completions", output)
        self.assertIn("Output Format: Table", output)
        self.assertIn("Sample Preview (up to 10): API DryRun Card", output)
        mock_validate.assert_not_called()

    @patch('mtg_llm_validate.validate_cards_llm')
    @patch('jdecode.mtg_open_file')
    def test_main_outfile_and_color_formatting(self, mock_open_file, mock_validate):
        card1 = MagicMock(spec=cardlib.Card)
        card1.name = "Valid Card"
        card2 = MagicMock(spec=cardlib.Card)
        card2.name = "Invalid Card"
        card3 = MagicMock(spec=cardlib.Card)
        card3.name = "Unknown Card"

        mock_open_file.return_value = [card1, card2, card3]

        mock_validate.return_value = [
            {'card': card1, 'judgment': 'VALID', 'reason': 'Ok'},
            {'card': card2, 'judgment': 'INVALID', 'reason': 'Bad'},
            {'card': card3, 'judgment': 'UNKNOWN', 'reason': 'Error'},
        ]

        m_open = mock_open()
        with patch('builtins.open', m_open), patch('sys.stderr', io.StringIO()):
            with patch('sys.argv', ['mtg_llm_validate.py', 'dummy.txt', 'out.txt', '--color']):
                mtg_llm_validate.main()

        m_open.assert_called_with('out.txt', 'w', encoding='utf8')
        handle = m_open()
        written = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn("Valid Card", written)
        self.assertIn("Invalid Card", written)
        self.assertIn("Unknown Card", written)

    @patch('urllib.request.Request')
    @patch('urllib.request.urlopen')
    def test_validate_cards_llm_api_with_key(self, mock_urlopen, mock_request_cls):
        mock_card = MagicMock(spec=cardlib.Card)
        mock_card.name = "Auth Card"
        mock_card.format.return_value = "Rules"

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "JUDGMENT: VALID\nREASON: OK"}}]
        }).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        mtg_llm_validate.validate_cards_llm(
            [mock_card], "model", "cpu", provider='api',
            api_url="http://test.api", api_key="secret-token"
        )

        mock_request_cls.assert_called_once()
        headers = mock_request_cls.call_args[1]['headers']
        self.assertEqual(headers["Authorization"], "Bearer secret-token")

    @patch('mtg_llm_validate.pipeline')
    def test_validate_cards_llm_device_selection(self, mock_pipeline):
        mock_card = MagicMock(spec=cardlib.Card)
        mock_card.format.return_value = "Rules"

        mock_pipe = MagicMock()
        mock_pipe.tokenizer.eos_token_id = 2
        mock_pipe.return_value = [[{'generated_text': "<|assistant|>\nJUDGMENT: VALID\nREASON: OK"}]]
        mock_pipeline.return_value = mock_pipe

        mtg_llm_validate.validate_cards_llm([mock_card], "model", device="cpu", provider='transformers')
        self.assertEqual(mock_pipeline.call_args[1]['device'], -1)

        mtg_llm_validate.validate_cards_llm([mock_card], "model", device="mps", provider='transformers')
        self.assertEqual(mock_pipeline.call_args[1]['device'], "mps")

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdin.isatty', return_value=True)
    @patch('os.path.exists', return_value=True)
    @patch('mtg_llm_validate.validate_cards_llm', return_value=[])
    def test_main_interactive_stdin_default_dataset(self, mock_validate, mock_exists, mock_isatty, mock_open_file):
        mock_open_file.return_value = []
        stderr = io.StringIO()

        with patch('sys.stdout', io.StringIO()), patch('sys.stderr', stderr):
            with patch('sys.argv', ['mtg_llm_validate.py']):
                mtg_llm_validate.main()

        self.assertIn("Notice: Using default dataset: data/AllPrintings.json", stderr.getvalue())
        mock_open_file.assert_called_with('data/AllPrintings.json', verbose=False, grep=None, sets=None, rarities=None, produces=None)

if __name__ == '__main__':
    unittest.main()
