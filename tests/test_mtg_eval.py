import unittest
from unittest.mock import patch, MagicMock
import argparse
import os
import sys
import io

# Add lib and root directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
rootdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../')
sys.path.append(libdir)
sys.path.append(rootdir)

from scripts import mtg_eval

class TestMtgEval(unittest.TestCase):

    @patch('os.path.exists')
    @patch('torch.load')
    @patch('train.CharRNN')
    @patch('train.generate_text')
    @patch('mtg_validate.process_props')
    @patch('argparse.ArgumentParser.parse_args')
    def test_mtg_eval_basic(self, mock_args, mock_validate, mock_generate, mock_rnn, mock_torch_load, mock_exists):
        # Setup mocks
        mock_exists.return_value = True
        mock_args.return_value = argparse.Namespace(
            checkpoint='dummy.pt',
            count=2,
            temp=0.8,
            dump=False,
            seed=None,
            verbose=False,
            quiet=True
        )

        mock_torch_load.return_value = {
            'vocab': ['a', 'b'],
            'char_to_idx': {'a': 0, 'b': 1},
            'idx_to_char': {0: 'a', 1: 'b'},
            'model_state_dict': {},
            'args': argparse.Namespace(hidden_size=64, n_layers=1)
        }

        # Mock CharRNN instance
        mock_model = MagicMock()
        mock_rnn.return_value = mock_model

        # Generated text with 2 cards, 10 pipes each
        mock_generate.return_value = "|5creature|4|6cat|7|8&^^/&^^|9text|3{W}|0O|1name|\n\n|5creature|4|6bird|7|8&^/&^|9flying|3{U}|0O|1bird|"

        from scripts import mtg_validate
        mock_values = {prop: (0, 0, 0) for prop in mtg_validate.props}
        mock_values['types'] = (2, 2, 0)

        mock_validate.return_value = (
            (2, 2, 0, 0), # total_all, total_good, total_bad, total_uncovered
            mock_values
        )

        # Run main
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            mtg_eval.main()
            output = fake_out.getvalue()

        self.assertIn("MODEL EVALUATION REPORT", output)
        self.assertIn("Mechanical Accuracy Score: 100.0%", output)
        self.assertIn("types", output)

    @patch('os.path.exists')
    def test_mtg_eval_missing_checkpoint(self, mock_exists):
        mock_exists.return_value = False
        with patch('argparse.ArgumentParser.parse_args') as mock_args:
            mock_args.return_value = argparse.Namespace(checkpoint='missing.pt')
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                with self.assertRaises(SystemExit):
                    mtg_eval.main()
                self.assertIn("Error: Checkpoint file 'missing.pt' not found.", fake_err.getvalue())

if __name__ == '__main__':
    unittest.main()
