import unittest
import sys
import os
import io
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib import jdecode, utils, cardlib

class TestJDecodeAutodetectQA(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_mtg_open_file_autodetect_decklist(self):
        # Create a file with decklist content but .txt extension
        deck_path = os.path.join(self.test_dir, "mydeck.txt")
        with open(deck_path, "w") as f:
            f.write("4 Grizzly Bears\n2 Giant Growth")

        with patch('lib.jdecode._hydrate_decklist') as mock_hydrate:
            mock_card = MagicMock(spec=cardlib.Card)
            mock_card.parsed = True
            mock_card.text = MagicMock()
            mock_card.text.text = "Some text"
            mock_card.name = "Grizzly Bears"
            mock_card.rarity = "O"

            mock_hydrate.return_value = [mock_card]

            cards = jdecode.mtg_open_file(deck_path, verbose=True)

            self.assertTrue(mock_hydrate.called)
            self.assertEqual(len(cards), 1)

    def test_mtg_open_file_no_autodetect_encoded(self):
        # Create a file that looks like encoded text
        enc_path = os.path.join(self.test_dir, "cards.txt")
        with open(enc_path, "w") as f:
            f.write("|5land|1T|") # Standard encoded land

        with patch('lib.jdecode._hydrate_decklist') as mock_hydrate:
            cards = jdecode.mtg_open_file(enc_path)
            self.assertFalse(mock_hydrate.called)
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0].name.lower(), 't')

    def test_mtg_open_file_unicode_decode_error(self):
        # Create a binary file that will cause UnicodeDecodeError when opened as 'rt'
        bin_path = os.path.join(self.test_dir, "binary.dat")
        with open(bin_path, "wb") as f:
            f.write(b"\xff\xfe\xfd\xfc")

        # This should hit the 'except UnicodeDecodeError: pass' in mtg_open_file
        # and then proceed to try to open it again as 'rt' later (which will also fail if it's still binary)

        with patch('lib.jdecode.print'):
            try:
                jdecode.mtg_open_file(bin_path)
            except UnicodeDecodeError:
                pass

    def test_mtg_open_mse_unhandled_lines(self):
        # Hits line 539: if line.startswith('\t\t'): pass
        # Hits line 564: elif line.strip() == '' or not line.startswith('\t'): pass
        mse_content = "mse-version: 2.0.0\n\ncard:\n\tname: Test\n\t\tThis should be ignored by the top-level branch\n\nNot a card line"

        # We just need to ensure it doesn't crash and processes what it can
        srcs, _ = jdecode.mtg_open_mse_content(mse_content)
        self.assertIn("test", srcs)

if __name__ == '__main__':
    unittest.main()
