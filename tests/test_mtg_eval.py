import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import json
import argparse
import io

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))

import mtg_eval

class TestMTGEval(unittest.TestCase):

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.CharRNN')
    @patch('mtg_eval.generate_text')
    @patch('mtg_validate.process_props')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mtg_eval_main_basic(self, mock_stdout, mock_process_props, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        # Setup mocks
        mock_exists.return_value = True

        # Mock checkpoint data
        mock_torch_load.return_value = {
            'vocab': ['a', 'b', '|', '\n'],
            'char_to_idx': {'a': 0, 'b': 1, '|': 2, '\n': 3},
            'idx_to_char': {0: 'a', 1: 'b', 2: '|', 3: '\n'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 5
        }

        # Mock generated text (2 cards)
        # Standard format: |types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name|
        card1 = "|creature|legendary|elf|&|&^^/&^^|@ has flying\\@ has trample|{GG}|O|uthros|"
        card2 = "|instant|||&|uncast target spell|{UU}|N|counterspell|"
        mock_generate.return_value = card1 + "\n\n" + card2 + "\n\n"

        # Mock validation results
        # values is OrderedDict of (total, good, bad)
        mock_process_props.return_value = (
            (2, 1, 1, 0), # (total_all, total_good, total_bad, total_uncovered)
            {'types': (2, 2, 0), 'pt': (1, 1, 0), 'color_pie': (2, 1, 1)}
        )

        # Run main with minimal args
        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '--count', '2', '--no-color']):
            mtg_eval.main()

        output = mock_stdout.getvalue()

        # Verify output
        self.assertIn("MODEL EVALUATION REPORT", output)
        self.assertIn("Checkpoint: fake.pt", output)
        self.assertIn("Epoch:      5", output)
        self.assertIn("Accuracy Score: 50.0%", output)
        self.assertIn("Success %", output)
        self.assertIn("Rule Check", output)
        self.assertIn("types", output)
        self.assertIn("pt", output)
        self.assertIn("color_pie", output)

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.CharRNN')
    @patch('mtg_eval.generate_text')
    @patch('mtg_validate.process_props')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mtg_eval_json_output(self, mock_stdout, mock_process_props, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 10
        }
        mock_generate.return_value = "|types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name|\n\n"
        mock_process_props.return_value = (
            (1, 1, 0, 0),
            {'types': (1, 1, 0)}
        )

        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '--json']):
            mtg_eval.main()

        output = mock_stdout.getvalue()
        result = json.loads(output)

        self.assertEqual(result['checkpoint'], 'fake.pt')
        self.assertEqual(result['epoch'], 10)
        self.assertEqual(result['summary']['accuracy'], 100.0)
        self.assertIn('types', result['properties'])

if __name__ == '__main__':
    unittest.main()
