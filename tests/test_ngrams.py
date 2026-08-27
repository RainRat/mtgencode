import os
import tempfile
import unittest
from unittest.mock import patch
import sys

from scripts import ngrams

class TestNgrams(unittest.TestCase):
    def test_update_ngrams_and_describe_bins(self):
        gramdict = {}
        lines = [["when", "@", "enters", "the", "battlefield"]]
        ngrams.update_ngrams(lines, gramdict, 2)
        self.assertEqual(gramdict["when @"], 1)
        self.assertEqual(gramdict["@ enters"], 1)

        # Test describe_bins output without error
        ngrams.describe_bins(gramdict, [1, 2, 5])

    def test_main_non_nltk(self):
        test_card_file = "testdata/uthros.json"
        if not os.path.exists(test_card_file):
            self.skipTest("testdata/uthros.json not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_prefix = os.path.join(tmpdir, "out")
            ngrams.main(test_card_file, out_prefix, gmin=2, gmax=2, nltk=False, verbose=True)

            out_file = out_prefix + ".2g"
            self.assertTrue(os.path.exists(out_file))

            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIsInstance(content, str)
                self.assertTrue(len(content) > 0)

    def test_main_nltk(self):
        test_card_file = "testdata/uthros.json"
        if not os.path.exists(test_card_file):
            self.skipTest("testdata/uthros.json not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "model.pkl")
            ngrams.main(test_card_file, out_file, gmin=2, gmax=2, nltk=True, sep=True, verbose=True)

            self.assertTrue(os.path.exists(out_file))

if __name__ == "__main__":
    unittest.main()
