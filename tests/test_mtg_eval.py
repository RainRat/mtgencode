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

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.CharRNN')
    @patch('mtg_eval.generate_text')
    @patch('mtg_validate.process_props')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mtg_eval_positional_checkpoint(self, mock_stdout, mock_process_props, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 1
        }
        mock_generate.return_value = "|types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name|\n\n"
        mock_process_props.return_value = ((1, 1, 0, 0), {'types': (1, 1, 0)})

        with patch('sys.argv', ['mtg_eval.py', 'positional_model.pt', '--json']):
            mtg_eval.main()

        output = mock_stdout.getvalue()
        result = json.loads(output)
        self.assertEqual(result['checkpoint'], 'positional_model.pt')

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.CharRNN')
    @patch('mtg_eval.generate_text')
    @patch('mtg_validate.process_props')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mtg_eval_flag_override_and_default(self, mock_stdout, mock_process_props, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 1
        }
        mock_generate.return_value = "|types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name|\n\n"
        mock_process_props.return_value = ((1, 1, 0, 0), {'types': (1, 1, 0)})

        # Test flag override over positional
        with patch('sys.argv', ['mtg_eval.py', 'pos.pt', '-c', 'flag.pt', '--json']):
            mtg_eval.main()

        output = mock_stdout.getvalue()
        result = json.loads(output)
        self.assertEqual(result['checkpoint'], 'flag.pt')

        # Test default fallback when neither is provided
        mock_stdout.seek(0)
        mock_stdout.truncate(0)
        with patch('sys.argv', ['mtg_eval.py', '--json']):
            mtg_eval.main()

        output = mock_stdout.getvalue()
        result = json.loads(output)
        self.assertEqual(result['checkpoint'], 'checkpoint.pt')

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.CharRNN')
    @patch('mtg_eval.generate_text')
    @patch('mtg_validate.process_props')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mtg_eval_length_autoscale(self, mock_stdout, mock_process_props, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 1
        }
        mock_generate.return_value = "|types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name|\n\n"
        mock_process_props.return_value = ((1, 1, 0, 0), {'types': (1, 1, 0)})

        # Test 1: Count 100 cards with no --length -> length auto-scales to max(5000, 100 * 250) = 25000
        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '--count', '100', '--json']):
            mtg_eval.main()

        self.assertEqual(mock_generate.call_args[1]['length'], 25000)

        # Test 2: Explicit --length 1234 overrides auto-scaling
        mock_generate.reset_mock()
        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '--count', '100', '--length', '1234', '--json']):
            mtg_eval.main()

        self.assertEqual(mock_generate.call_args[1]['length'], 1234)

if __name__ == '__main__':
    unittest.main()
