import unittest
import sys
import os
import io
import tempfile
import shutil
from unittest.mock import patch

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib import jdecode

class TestJDecodeAutodetect(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_mtg_open_mse_content_coverage_gaps(self):
        # Triggers line 539 (multi-line pass), 561 (empty value), 564 (pass for non-indented/empty)
        # Note: 539 is hit because 'name' handling doesn't consume \t\t lines.
        mse_content = "card:\n\tname: Test Card\n\t\tignored continuation\n\trarity:\n\nnot_indented\n"

        srcs, _ = jdecode.mtg_open_mse_content(mse_content)
        self.assertIn("test card", srcs)
        self.assertEqual(srcs["test card"][0]["rarity"], "")

    def test_decklist_autodetect_by_extension(self):
        # Triggers line 1090
        deck_path = os.path.join(self.test_dir, "mydeck.deck")
        with open(deck_path, 'w') as f:
            f.write("1 Grizzly Bears")

        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            cards = jdecode.mtg_open_file(deck_path, verbose=True)
            self.assertIn("Detected " + deck_path + " as a decklist", fake_err.getvalue())
            self.assertEqual(len(cards), 0)

    def test_decklist_autodetect_by_content(self):
        # Triggers lines 1098-1100
        deck_path = os.path.join(self.test_dir, "mydeck.txt")
        with open(deck_path, 'w') as f:
            f.write("\n\n  4 Grizzly Bears") # Pattern within first 5 lines

        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            cards = jdecode.mtg_open_file(deck_path, verbose=True)
            self.assertIn("Detected " + deck_path + " as a decklist", fake_err.getvalue())
            self.assertEqual(len(cards), 0)

    def test_decklist_autodetect_binary_ignore(self):
        # Triggers line 1101 (UnicodeDecodeError)
        bin_path = os.path.join(self.test_dir, "binary.dat")
        with open(bin_path, 'wb') as f:
            f.write(b"\xff\xfe\xfd\xfc")

        with self.assertRaises(UnicodeDecodeError):
            jdecode.mtg_open_file(bin_path, verbose=True)

if __name__ == '__main__':
    unittest.main()
