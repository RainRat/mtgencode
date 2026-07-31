import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import math

# Adjust path to import scripts and lib
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts'))
sys.path.insert(0, scripts_dir)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.analysis import mean_nonan, gmean_nonzero, get_statistics
from lib.cardlib import Card

class TestAnalysis(unittest.TestCase):
    def test_mean_nonan(self):
        # Test mean calculation ignoring NaN values
        self.assertEqual(mean_nonan([1.0, 2.0, float('nan'), 3.0]), 2.0)
        self.assertTrue(math.isnan(mean_nonan([float('nan')])))

    def test_gmean_nonzero(self):
        # Test geometric mean calculation ignoring zero and NaN values
        self.assertAlmostEqual(gmean_nonzero([2.0, 8.0, 0.0, float('nan')]), 4.0)
        self.assertEqual(gmean_nonzero([0.0, float('nan')]), 0.0)

    def test_get_statistics_sep_false(self):
        # Create a real temp file with cards
        with tempfile.NamedTemporaryFile(mode='w+', suffix='_epoch5_1.2.ident.0.5.txt', delete=False, encoding='utf-8') as tmp:
            tmp.write("|1Test Card|9This is test rules text.\n")
            tmp_path = tmp.name

        try:
            # Mock Language Model (lm)
            mock_lm = MagicMock()
            mock_lm.perplexity.return_value = 10.0

            # We will test both sep=False and sep=True
            # This will verify that the logic bug (NameError) is fixed when sep=False
            stats = get_statistics(tmp_path, lm=mock_lm, sep=False)

            self.assertIn('cards', stats)
            self.assertIn('cp', stats)
            self.assertEqual(stats['cp']['epoch'], 5.0)
            self.assertEqual(stats['cp']['vloss'], 1.2)
            self.assertEqual(stats['cp']['temp'], 0.5)
            self.assertEqual(stats['cp']['ident'], 'ident')

            self.assertIn('ngram', stats)
            # Verify that perp_per_max is correctly assigned and is equal to perp_per
            self.assertEqual(stats['ngram']['perp'][0], 10.0)

            # length of vectorize() of "This is test rules text."
            # Let's get the parsed Card object from stats['cards']
            card = stats['cards'][0]
            vtext_len = len(card.text.vectorize().split())
            self.assertAlmostEqual(stats['ngram']['perp_per'][0], 10.0 / float(vtext_len))
            self.assertAlmostEqual(stats['ngram']['perp_per_max'][0], 10.0 / float(vtext_len))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_get_statistics_sep_true(self):
        # Create a real temp file with cards
        with tempfile.NamedTemporaryFile(mode='w+', suffix='_epoch5_1.2.ident.0.5.txt', delete=False, encoding='utf-8') as tmp:
            tmp.write("|1Test Card|9Line one.\\Line two.\n")
            tmp_path = tmp.name

        try:
            # Mock Language Model (lm)
            mock_lm = MagicMock()
            mock_lm.perplexity.return_value = 12.0

            # Run with sep=True
            stats = get_statistics(tmp_path, lm=mock_lm, sep=True)

            self.assertIn('ngram', stats)
            # Verify that perp is computed and no NameError is raised
            self.assertNotEqual(len(stats['ngram']['perp']), 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_get_statistics_with_dist_file(self):
        # Create a real temp file with cards
        with tempfile.NamedTemporaryFile(mode='w+', suffix='_epoch1_2.0.ident.0.8.txt', delete=False, encoding='utf-8') as tmp:
            tmp.write("|1Test Card|9Some text.\n")
            tmp_path = tmp.name

        dist_path = tmp_path + ".dist"
        try:
            # Write fake .dist file content
            with open(dist_path, 'w', encoding='utf-8') as f:
                f.write("0|Test Card|1.0|0.8\n")
                f.write("1|Other Card|0.5|0.6\n")

            stats = get_statistics(tmp_path, lm=None)

            self.assertIn('dists', stats)
            self.assertAlmostEqual(stats['dists']['name_mean'], 0.75)
            self.assertAlmostEqual(stats['dists']['cbow_mean'], 0.7)
            self.assertEqual(stats['dists']['name_geomean'], gmean_nonzero([1.0, 0.5]))
            self.assertEqual(stats['dists']['cbow_geomean'], gmean_nonzero([0.8, 0.6]))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(dist_path):
                os.remove(dist_path)

if __name__ == '__main__':
    unittest.main()
