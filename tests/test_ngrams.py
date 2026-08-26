import os
import tempfile
import unittest
import runpy
from unittest.mock import patch
from scripts import ngrams

class TestNgrams(unittest.TestCase):
    def test_main_non_nltk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            infile = os.path.join('testdata', 'tarkir.json')
            outfile = os.path.join(tmpdir, 'out_ngrams')
            ngrams.main(infile, outfile, gmin=2, gmax=2, nltk=False, verbose=False)

            expected_file = outfile + '.2g'
            self.assertTrue(os.path.exists(expected_file))
            with open(expected_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn(':', content)

    def test_main_cli_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            infile = os.path.join('testdata', 'tarkir.json')
            outfile = os.path.join(tmpdir, 'out_ngrams')
            test_args = ['ngrams.py', infile, outfile, '-min', '2', '-max', '2']
            with patch('sys.argv', test_args):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_module('scripts.ngrams', run_name='__main__')
                self.assertEqual(cm.exception.code, 0)

if __name__ == '__main__':
    unittest.main()
