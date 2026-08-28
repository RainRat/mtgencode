import sys
import os
import tempfile
import unittest
from unittest.mock import patch

# Ensure repo root and lib/scripts are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts import ngrams

class TestNgrams(unittest.TestCase):
    def setUp(self):
        self.sample_json = os.path.join(os.path.dirname(__file__), '../testdata/uthros.json')

    def test_dry_run_mode(self):
        """Test dry-run mode prints n-gram summary without generating files."""
        with patch('sys.stdout') as mock_stdout:
            ngrams.main(fname=self.sample_json, gmin=2, gmax=3, dry_run=True)
            # Check stdout content calls
            printed_text = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
            self.assertIn("Dry Run Summary", printed_text)
            self.assertIn("Evaluated 1 card(s)", printed_text)
            self.assertIn("2-gram", printed_text)
            self.assertIn("3-gram", printed_text)

    def test_dry_run_nltk(self):
        """Test dry-run mode with NLTK model option."""
        with patch('sys.stdout') as mock_stdout:
            ngrams.main(fname=self.sample_json, gmin=3, nltk=True, dry_run=True)
            printed_text = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
            self.assertIn("Dry Run Summary", printed_text)
            self.assertIn("NLTK Model Settings: n=3", printed_text)

    def test_ngram_file_writing(self):
        """Test standard n-gram file generation and formatting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_prefix = os.path.join(tmpdir, 'output')
            ngrams.main(fname=self.sample_json, oname=out_prefix, gmin=2, gmax=3, verbose=True)

            file_2g = out_prefix + '.2g'
            file_3g = out_prefix + '.3g'
            self.assertTrue(os.path.exists(file_2g))
            self.assertTrue(os.path.exists(file_3g))

            with open(file_2g, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn("this spacecraft: 2", content)

    def test_nltk_model_pickle(self):
        """Test NLTK model creation and pickle dumping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_pkl = os.path.join(tmpdir, 'model.pkl')
            ngrams.main(fname=self.sample_json, oname=out_pkl, gmin=2, nltk=True, verbose=True)
            self.assertTrue(os.path.exists(out_pkl))

    def test_invalid_gram_sizes(self):
        """Test error exit on invalid gram sizes."""
        with self.assertRaises(SystemExit):
            ngrams.main(fname=self.sample_json, oname="dummy", gmin=5, gmax=2)

    def test_missing_outfile_raises_error(self):
        """Test error exit when outfile is omitted without --dry-run."""
        with self.assertRaises(SystemExit):
            ngrams.main(fname=self.sample_json, oname=None, dry_run=False)

if __name__ == '__main__':
    unittest.main()
