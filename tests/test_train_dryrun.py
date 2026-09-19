import unittest
import sys
import os
import io
import tempfile
import runpy
from unittest.mock import patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import train

class TestTrainDryRun(unittest.TestCase):

    def test_train_dryrun_existing_dataset(self):
        with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8') as f:
            f.write("|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n|1Giant Growth|5Instant|9+3/+3|3{G}|\n\n")
            tmp_dataset = f.name

        try:
            buf = io.StringIO()
            test_args = [
                'train.py',
                '--mode', 'train',
                '--infile', tmp_dataset,
                '--checkpoint', 'nonexistent_cp.pt',
                '--epochs', '5',
                '--batch_size', '32',
                '--dry-run'
            ]
            parser = train.get_parser()
            with patch.object(sys, 'argv', test_args), patch('sys.stdout', buf):
                train.train(parser.parse_args(test_args[1:]))

            out = buf.getvalue()
            self.assertIn("Dry Run Summary: Neural network training configuration (train mode).", out)
            self.assertIn("Training Dataset:", out)
            self.assertIn("Exists", out)
            self.assertIn("2 card(s)", out)
            self.assertIn("Epochs: 5", out)
            self.assertIn("Batch Size: 32", out)
            self.assertFalse(os.path.exists('nonexistent_cp.pt'))
        finally:
            if os.path.exists(tmp_dataset):
                os.remove(tmp_dataset)

    def test_train_dryrun_missing_dataset(self):
        buf = io.StringIO()
        test_args = [
            'train.py',
            '--mode', 'train',
            '--infile', 'missing_file_xyz.txt',
            '--dry-run'
        ]
        parser = train.get_parser()
        with patch.object(sys, 'argv', test_args), patch('sys.stdout', buf):
            train.train(parser.parse_args(test_args[1:]))

        out = buf.getvalue()
        self.assertIn("Dry Run Summary: Neural network training configuration (train mode).", out)
        self.assertIn("Not Found", out)

    def test_sample_dryrun(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write("mock_checkpoint_data")
            tmp_cp = f.name

        try:
            buf = io.StringIO()
            test_args = [
                'train.py',
                '--mode', 'sample',
                '--checkpoint', tmp_cp,
                '--length', '500',
                '--temp', '0.9',
                '--name', 'Uthros',
                '--types', 'creature',
                '--dry-run'
            ]
            parser = train.get_parser()
            with patch.object(sys, 'argv', test_args), patch('sys.stdout', buf):
                train.sample(parser.parse_args(test_args[1:]))

            out = buf.getvalue()
            self.assertIn("Dry Run Summary: Neural network card generation configuration (sample mode).", out)
            self.assertIn("Checkpoint Model:", out)
            self.assertIn("Exists", out)
            self.assertIn("Generation Length: 500 characters", out)
            self.assertIn("Temperature: 0.9", out)
            self.assertIn("Forced Card Attributes:", out)
            self.assertIn("Name: Uthros", out)
            self.assertIn("Types: creature", out)
        finally:
            if os.path.exists(tmp_cp):
                os.remove(tmp_cp)

    def test_cli_execution_via_runpy(self):
        buf = io.StringIO()
        test_args = [
            'train.py',
            '--mode', 'train',
            '--dry-run'
        ]
        with patch.object(sys, 'argv', test_args), patch('sys.stdout', buf):
            runpy.run_module('train', run_name='__main__')

        out = buf.getvalue()
        self.assertIn("Dry Run Summary: Neural network training configuration (train mode).", out)

if __name__ == '__main__':
    unittest.main()
