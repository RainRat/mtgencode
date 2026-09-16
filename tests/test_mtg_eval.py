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
    def test_mtg_eval_more_cards_truncated(self, mock_stdout, mock_process_props, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 1
        }
        # Generate 3 cards when --count is 2
        card = "|types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name|\n\n"
        mock_generate.return_value = card * 3
        mock_process_props.return_value = ((2, 2, 0, 0), {'types': (2, 2, 0)})

        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '--count', '2', '--json']):
            mtg_eval.main()

        # Check process_props received exactly 2 cards
        passed_cards = mock_process_props.call_args[0][0]
        self.assertEqual(len(passed_cards), 2)

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.CharRNN')
    @patch('mtg_eval.generate_text')
    @patch('mtg_validate.process_props')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mtg_eval_card_parse_exception_handled(self, mock_stdout, mock_process_props, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 1
        }
        # First card is invalid raw syntax that throws in Card(), second is valid
        mock_generate.return_value = "invalid_card_raw\n\n|creature|||&|1/1|text|{1}|C|Name|\n\n"
        mock_process_props.return_value = ((1, 1, 0, 0), {'types': (1, 1, 0)})

        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '--json']):
            mtg_eval.main()

        output = mock_stdout.getvalue()
        result = json.loads(output)
        self.assertEqual(result['checkpoint'], 'fake.pt')

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

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.CharRNN')
    @patch('mtg_eval.generate_text')
    @patch('mtg_validate.process_props')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mtg_eval_quiet_passed_to_generate_text(self, mock_stdout, mock_process_props, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 1
        }
        mock_generate.return_value = "|types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name|\n\n"
        mock_process_props.return_value = ((1, 1, 0, 0), {'types': (1, 1, 0)})

        # Test quiet=False (default when -q is not passed)
        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '--json']):
            mtg_eval.main()

        self.assertFalse(mock_generate.call_args[1]['quiet'])

        # Test quiet=True when -q / --quiet is passed
        mock_generate.reset_mock()
        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '-q', '--json']):
            mtg_eval.main()

        self.assertTrue(mock_generate.call_args[1]['quiet'])

    @patch('train.tqdm')
    def test_generate_text_quiet_param(self, mock_tqdm):
        from train import generate_text
        import torch
        mock_model = MagicMock()
        mock_model.init_hidden.return_value = None
        mock_output = torch.zeros(1, 1, 2)
        mock_model.return_value = (mock_output, None)

        char_to_idx = {'|': 0, 'a': 1}
        idx_to_char = {0: '|', 1: 'a'}
        args = argparse.Namespace(start_text='|', temp=1.0)

        # Test quiet=True (disable=True)
        generate_text(mock_model, char_to_idx, idx_to_char, 2, torch.device('cpu'), args, length=5, quiet=True)
        self.assertTrue(mock_tqdm.call_args[1]['disable'])

        # Test quiet=False (disable=False)
        mock_tqdm.reset_mock()
        generate_text(mock_model, char_to_idx, idx_to_char, 2, torch.device('cpu'), args, length=5, quiet=False)
        self.assertFalse(mock_tqdm.call_args[1]['disable'])

    @patch('os.path.exists')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_mtg_eval_missing_checkpoint(self, mock_stderr, mock_exists):
        mock_exists.return_value = False
        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'missing.pt']):
            with self.assertRaises(SystemExit) as cm:
                mtg_eval.main()
            self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Checkpoint file not found: missing.pt", mock_stderr.getvalue())

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_mtg_eval_load_exception(self, mock_stderr, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.side_effect = RuntimeError("Corrupt file")
        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'corrupt.pt']):
            with self.assertRaises(SystemExit) as cm:
                mtg_eval.main()
            self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error loading checkpoint: Corrupt file", mock_stderr.getvalue())

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.CharRNN')
    @patch('mtg_eval.generate_text')
    @patch('mtg_validate.process_props')
    @patch('torch.manual_seed')
    @patch('numpy.random.seed')
    @patch('random.seed')
    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mtg_eval_verbose_and_seed(self, mock_stdout, mock_stderr, mock_rseed, mock_npseed, mock_tseed, mock_process_props, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 1
        }
        mock_generate.return_value = "|types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name|\n\n"
        mock_process_props.return_value = ((1, 1, 0, 0), {'types': (1, 1, 0)})

        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '-v', '--seed', '42', '--count', '10', '--json']):
            mtg_eval.main()

        stderr_output = mock_stderr.getvalue()
        self.assertIn("Loading model from fake.pt...", stderr_output)
        self.assertIn("Generating 10 cards for evaluation...", stderr_output)
        self.assertIn("Validating generated cards...", stderr_output)
        mock_tseed.assert_called_once_with(42)
        mock_npseed.assert_called_once_with(42)
        mock_rseed.assert_called_once_with(42)

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.CharRNN')
    @patch('mtg_eval.generate_text')
    @patch('mtg_validate.process_props')
    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mtg_eval_fewer_cards_warning(self, mock_stdout, mock_stderr, mock_process_props, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 1
        }
        mock_generate.return_value = "|types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name|\n\n"
        mock_process_props.return_value = ((1, 1, 0, 0), {'types': (1, 1, 0)})

        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '--count', '5', '--json']):
            mtg_eval.main()

        self.assertIn("Warning: Only generated 1 cards (requested 5). Increase --length.", mock_stderr.getvalue())

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.CharRNN')
    @patch('mtg_eval.generate_text')
    @patch('cardlib.Card')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_mtg_eval_no_cards_parsed(self, mock_stderr, mock_card, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 1
        }
        mock_generate.return_value = "invalid text that yields no cards\n\n"
        mock_card.side_effect = Exception("Parsing error")

        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt']):
            with self.assertRaises(SystemExit) as cm:
                mtg_eval.main()
            self.assertEqual(cm.exception.code, 1)

        self.assertIn("Error: No cards were successfully generated/parsed.", mock_stderr.getvalue())

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.CharRNN')
    @patch('mtg_eval.generate_text')
    @patch('mtg_validate.process_props')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mtg_eval_color_output(self, mock_stdout, mock_process_props, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 1
        }
        mock_generate.return_value = "|types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name|\n\n"
        mock_process_props.return_value = (
            (10, 5, 5, 0),
            {'types': (10, 5, 5)}
        )

        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '--color']):
            mtg_eval.main()

        output = mock_stdout.getvalue()
        self.assertIn("\033[", output)
        self.assertIn("Accuracy Score:", output)
        self.assertIn("50.0%", output)

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('mtg_eval.generate_text')
    @patch('mtg_validate.process_props')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_mtg_eval_main_execution(self, mock_stdout, mock_process_props, mock_generate, mock_torch_load, mock_exists):
        import runpy
        mock_exists.return_value = True
        mock_torch_load.return_value = {
            'vocab': ['a'], 'char_to_idx': {'a': 0}, 'idx_to_char': {0: 'a'},
            'args': argparse.Namespace(hidden_size=256, n_layers=2),
            'model_state_dict': {},
            'epoch': 1
        }
        mock_generate.return_value = "|types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name|\n\n"
        mock_process_props.return_value = ((1, 1, 0, 0), {'types': (1, 1, 0)})

        with patch('train.CharRNN.load_state_dict'):
            with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'fake.pt', '--json']):
                runpy.run_module('scripts.mtg_eval', run_name='__main__')

        output = mock_stdout.getvalue()
        result = json.loads(output)
        self.assertEqual(result['checkpoint'], 'fake.pt')

if __name__ == '__main__':
    unittest.main()
