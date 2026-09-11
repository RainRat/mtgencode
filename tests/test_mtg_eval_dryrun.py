import unittest
from unittest.mock import patch
import os
import sys
import io
import runpy

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))

import mtg_eval

class TestMTGEvalDryRun(unittest.TestCase):

    @patch('os.path.exists')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_dry_run_basic(self, mock_stdout, mock_exists):
        mock_exists.return_value = True

        with patch('sys.argv', ['mtg_eval.py', '--dry-run']):
            mtg_eval.main()

        output = mock_stdout.getvalue()
        self.assertIn("Dry Run Summary: AI Model Evaluation Parameters", output)
        self.assertIn("Checkpoint Path: checkpoint.pt (Found)", output)
        self.assertIn("Target Card Count: 50", output)
        self.assertIn("Generation Character Limit: 12500", output)
        self.assertIn("Sampling Temperature: 0.8", output)
        self.assertIn("Random Seed: Not set", output)
        self.assertIn("Device:", output)

    @patch('os.path.exists')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_dry_run_custom_options(self, mock_stdout, mock_exists):
        mock_exists.return_value = False

        with patch('sys.argv', ['mtg_eval.py', 'custom_cp.pt', '-n', '100', '-l', '30000', '-t', '1.2', '--seed', '12345', '-p']):
            mtg_eval.main()

        output = mock_stdout.getvalue()
        self.assertIn("Dry Run Summary: AI Model Evaluation Parameters", output)
        self.assertIn("Checkpoint Path: custom_cp.pt (Not found)", output)
        self.assertIn("Target Card Count: 100", output)
        self.assertIn("Generation Character Limit: 30000", output)
        self.assertIn("Sampling Temperature: 1.2", output)
        self.assertIn("Random Seed: 12345", output)

    @patch('os.path.exists')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_dry_run_preview_flag_alias(self, mock_stdout, mock_exists):
        mock_exists.return_value = True

        with patch('sys.argv', ['mtg_eval.py', '-c', 'model.pt', '--preview']):
            mtg_eval.main()

        output = mock_stdout.getvalue()
        self.assertIn("Dry Run Summary: AI Model Evaluation Parameters", output)
        self.assertIn("Checkpoint Path: model.pt (Found)", output)

    @patch('os.path.exists')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_dry_run_via_runpy(self, mock_stdout, mock_exists):
        mock_exists.return_value = True
        script_path = os.path.join(os.path.dirname(__file__), '../scripts/mtg_eval.py')

        with patch('sys.argv', ['mtg_eval.py', '--checkpoint', 'runpy_cp.pt', '--dry-run']):
            runpy.run_path(script_path, run_name='__main__')

        output = mock_stdout.getvalue()
        self.assertIn("Dry Run Summary: AI Model Evaluation Parameters", output)
        self.assertIn("Checkpoint Path: runpy_cp.pt (Found)", output)

if __name__ == '__main__':
    unittest.main()
