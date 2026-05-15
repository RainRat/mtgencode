import unittest
from unittest.mock import patch, MagicMock
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

class TestMtgLlmValidate(unittest.TestCase):

    @patch('mtg_llm_validate.pipeline')
    @patch('jdecode.mtg_open_file')
    def test_main_table_output(self, mock_open_file, mock_pipeline):
        # Mock cards
        mock_card1 = MagicMock(spec=cardlib.Card)
        mock_card1.name = "Test Card 1"
        mock_card1.format.return_value = "Test Card 1 rules text"
        mock_card1.to_dict.return_value = {"name": "Test Card 1"}

        mock_card2 = MagicMock(spec=cardlib.Card)
        mock_card2.name = "Test Card 2"
        mock_card2.format.return_value = "Test Card 2 rules text"
        mock_card2.to_dict.return_value = {"name": "Test Card 2"}

        mock_open_file.return_value = [mock_card1, mock_card2]

        # Mock LLM pipeline
        mock_pipe = MagicMock()
        # Response format expected by our script
        mock_pipe.tokenizer.eos_token_id = 2
        # When called with 2 prompts, it should return a list with 2 elements, each being a list of dicts.
        mock_pipe.side_effect = lambda prompts, **kwargs: [
            [{'generated_text': f"{p} <|assistant|>\nJUDGMENT: {'VALID' if 'Card 1' in p else 'INVALID'}\nREASON: Reason"}]
            for p in prompts
        ]
        mock_pipeline.return_value = mock_pipe

        # Capture output
        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()):
            with patch('sys.argv', ['mtg_llm_validate.py', 'dummy.txt', '--no-color']):
                mtg_llm_validate.main()

        output = stdout.getvalue()
        self.assertIn("Test Card 1", output)
        self.assertIn("VALID", output)
        self.assertIn("Test Card 2", output)
        self.assertIn("INVALID", output)
        self.assertIn("Reason", output)

    @patch('mtg_llm_validate.pipeline')
    @patch('jdecode.mtg_open_file')
    def test_main_json_output(self, mock_open_file, mock_pipeline):
        mock_card = MagicMock(spec=cardlib.Card)
        mock_card.name = "JSON Card"
        mock_card.format.return_value = "JSON rules"
        mock_card.to_dict.return_value = {"name": "JSON Card"}
        mock_open_file.return_value = [mock_card]

        mock_pipe = MagicMock()
        mock_pipe.tokenizer.eos_token_id = 2
        mock_pipe.return_value = [[{'generated_text': "<|assistant|>\nJUDGMENT: VALID\nREASON: JSON reason"}]]
        mock_pipeline.return_value = mock_pipe

        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()):
            with patch('sys.argv', ['mtg_llm_validate.py', 'dummy.txt', '--json']):
                mtg_llm_validate.main()

        output = stdout.getvalue()
        data = json.loads(output)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "JSON Card")
        self.assertEqual(data[0]['llm_judgment'], "VALID")
        self.assertEqual(data[0]['llm_reason'], "JSON reason")

    @patch('mtg_llm_validate.pipeline')
    @patch('jdecode.mtg_open_file')
    def test_only_valid_filter(self, mock_open_file, mock_pipeline):
        mock_card1 = MagicMock(spec=cardlib.Card)
        mock_card1.name = "Valid Card"
        mock_card1.format.return_value = "Card 1"

        mock_card2 = MagicMock(spec=cardlib.Card)
        mock_card2.name = "Invalid Card"
        mock_card2.format.return_value = "Card 2"

        mock_open_file.return_value = [mock_card1, mock_card2]

        mock_pipe = MagicMock()
        mock_pipe.tokenizer.eos_token_id = 2
        mock_pipe.side_effect = lambda prompts, **kwargs: [
            [{'generated_text': f"{p} <|assistant|>\nJUDGMENT: {'VALID' if 'Card 1' in p else 'INVALID'}\nREASON: Reason"}]
            for p in prompts
        ]
        mock_pipeline.return_value = mock_pipe

        stdout = io.StringIO()
        with patch('sys.stdout', stdout), patch('sys.stderr', io.StringIO()):
            with patch('sys.argv', ['mtg_llm_validate.py', 'dummy.txt', '--only-valid', '--no-color']):
                mtg_llm_validate.main()

        output = stdout.getvalue()
        self.assertIn("Valid Card", output)
        self.assertNotIn("Invalid Card", output)

if __name__ == '__main__':
    unittest.main()
