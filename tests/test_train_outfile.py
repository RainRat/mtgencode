import unittest
import sys
import os
import io
import tempfile
import runpy
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import train

class TestTrainOutfile(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sample_dryrun_with_outfile_flag(self):
        buf = io.StringIO()
        outfile_path = os.path.join(self.temp_dir.name, 'output.txt')
        test_args = [
            'train.py',
            '--mode', 'sample',
            '-o', outfile_path,
            '--dry-run'
        ]
        parser = train.get_parser()
        args = parser.parse_args(test_args[1:])
        with patch.object(sys, 'argv', test_args), patch('sys.stdout', buf):
            train.sample(args)

        out = buf.getvalue()
        self.assertIn("Dry Run Summary: Neural network card generation configuration (sample mode).", out)
        self.assertIn("Sampling Parameters:", out)
        self.assertIn(f"Output Destination: {outfile_path}", out)
        self.assertFalse(os.path.exists(outfile_path))

    def test_sample_dryrun_default_console(self):
        buf = io.StringIO()
        test_args = [
            'train.py',
            '--mode', 'sample',
            '--dry-run'
        ]
        parser = train.get_parser()
        args = parser.parse_args(test_args[1:])
        with patch.object(sys, 'argv', test_args), patch('sys.stdout', buf):
            train.sample(args)

        out = buf.getvalue()
        self.assertIn("Output Destination: Console (sys.stdout)", out)

    @patch('torch.load')
    @patch('train.generate_text')
    @patch('train.CharRNN')
    def test_sample_writes_to_outfile_short_flag(self, mock_rnn, mock_gen, mock_torch_load):
        mock_torch_load.return_value = {
            'vocab': ['a', 'b', '|', '\n'],
            'char_to_idx': {'a': 0, 'b': 1, '|': 2, '\n': 3},
            'idx_to_char': {0: 'a', 1: 'b', 2: '|', 3: '\n'},
            'args': MagicMock(hidden_size=64, n_layers=1),
            'model_state_dict': {}
        }
        mock_gen.return_value = "|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n"

        outfile_path = os.path.join(self.temp_dir.name, 'sample_out.txt')
        test_args = [
            'train.py',
            '--mode', 'sample',
            '--checkpoint', 'dummy_checkpoint.pt',
            '-o', outfile_path
        ]
        parser = train.get_parser()
        args = parser.parse_args(test_args[1:])
        train.sample(args)

        self.assertTrue(os.path.exists(outfile_path))
        with open(outfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertEqual(content, "|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n")

    @patch('torch.load')
    @patch('train.generate_text')
    @patch('train.CharRNN')
    def test_sample_writes_to_outfile_long_flag(self, mock_rnn, mock_gen, mock_torch_load):
        mock_torch_load.return_value = {
            'vocab': ['a', 'b', '|', '\n'],
            'char_to_idx': {'a': 0, 'b': 1, '|': 2, '\n': 3},
            'idx_to_char': {0: 'a', 1: 'b', 2: '|', 3: '\n'},
            'args': MagicMock(hidden_size=64, n_layers=1),
            'model_state_dict': {}
        }
        mock_gen.return_value = "|1Lightning Bolt|5Instant|3{R}|"

        outfile_path = os.path.join(self.temp_dir.name, 'sample_long.txt')
        test_args = [
            'train.py',
            '--mode', 'sample',
            '--checkpoint', 'dummy_checkpoint.pt',
            '--outfile', outfile_path
        ]
        parser = train.get_parser()
        args = parser.parse_args(test_args[1:])
        train.sample(args)

        self.assertTrue(os.path.exists(outfile_path))
        with open(outfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertEqual(content, "|1Lightning Bolt|5Instant|3{R}|\n")

    @patch('torch.load')
    @patch('train.generate_text')
    @patch('train.CharRNN')
    def test_sample_writes_to_stdout_when_dash_or_none(self, mock_rnn, mock_gen, mock_torch_load):
        mock_torch_load.return_value = {
            'vocab': ['a', 'b', '|', '\n'],
            'char_to_idx': {'a': 0, 'b': 1, '|': 2, '\n': 3},
            'idx_to_char': {0: 'a', 1: 'b', 2: '|', 3: '\n'},
            'args': MagicMock(hidden_size=64, n_layers=1),
            'model_state_dict': {}
        }
        mock_gen.return_value = "|1Counterspell|5Instant|3{U}{U}|"

        # None (default)
        buf = io.StringIO()
        test_args = [
            'train.py',
            '--mode', 'sample',
            '--checkpoint', 'dummy_checkpoint.pt'
        ]
        parser = train.get_parser()
        args = parser.parse_args(test_args[1:])
        with patch('sys.stdout', buf):
            train.sample(args)
        self.assertIn("|1Counterspell|5Instant|3{U}{U}|", buf.getvalue())

        # '-' (stdout)
        buf_dash = io.StringIO()
        test_args_dash = [
            'train.py',
            '--mode', 'sample',
            '--checkpoint', 'dummy_checkpoint.pt',
            '-o', '-'
        ]
        args_dash = parser.parse_args(test_args_dash[1:])
        with patch('sys.stdout', buf_dash):
            train.sample(args_dash)
        self.assertIn("|1Counterspell|5Instant|3{U}{U}|", buf_dash.getvalue())

    def test_cli_execution_via_runpy_with_outfile(self):
        outfile_path = os.path.join(self.temp_dir.name, 'cli_test.txt')
        buf = io.StringIO()
        test_args = [
            'train.py',
            '--mode', 'sample',
            '-o', outfile_path,
            '--dry-run'
        ]
        with patch.object(sys, 'argv', test_args), patch('sys.stdout', buf):
            runpy.run_module('train', run_name='__main__')

        out = buf.getvalue()
        self.assertIn("Dry Run Summary: Neural network card generation configuration (sample mode).", out)
        self.assertIn(f"Output Destination: {outfile_path}", out)

if __name__ == '__main__':
    unittest.main()
