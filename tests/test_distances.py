import os
import sys
import tempfile
import unittest
import runpy
from unittest.mock import patch, MagicMock

import scripts.distances as distances

class TestDistances(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_main_file_not_found(self):
        non_existent = os.path.join(self.temp_dir.name, 'non_existent.json')
        with self.assertRaises(SystemExit) as cm:
            distances.main(non_existent, 'out.txt')
        self.assertEqual(cm.exception.code, 1)

    def test_main_dry_run(self):
        infile = os.path.join('testdata', 'tarkir.json')
        outfile = os.path.join(self.temp_dir.name, 'out.txt')

        with patch('sys.stdout') as mock_stdout:
            distances.main(infile, outfile, verbose=False, parallel=False, dry_run=True)

        self.assertFalse(os.path.exists(outfile))

    def test_cli_dry_run(self):
        infile = os.path.join('testdata', 'tarkir.json')
        outfile = os.path.join(self.temp_dir.name, 'out.txt')
        test_args = ['distances.py', infile, outfile, '--dry-run', '--parallel']

        with patch.object(sys, 'argv', test_args):
            with patch('sys.stdout') as mock_stdout:
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path(os.path.join('scripts', 'distances.py'), run_name='__main__')
                self.assertEqual(cm.exception.code, 0)
        self.assertFalse(os.path.exists(outfile))

    def test_cli_interactive_missing_default_infile(self):
        missing_default = os.path.join(self.temp_dir.name, 'output.txt')
        test_args = ['distances.py']

        with patch.object(distances, 'default_infile', missing_default if hasattr(distances, 'default_infile') else missing_default):
            with patch.object(sys, 'argv', test_args):
                with patch('sys.stdin.isatty', return_value=True):
                    with patch('scripts.distances.os.path.exists', return_value=False):
                        with self.assertRaises(SystemExit) as cm:
                            runpy.run_path(os.path.join('scripts', 'distances.py'), run_name='__main__')
                        self.assertEqual(cm.exception.code, 1)

if __name__ == '__main__':
    unittest.main()
