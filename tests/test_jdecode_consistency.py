
import sys
import os
import unittest
from io import StringIO
from unittest.mock import patch
import tempfile
import shutil

# Ensure lib is in path
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if libdir not in sys.path:
    sys.path.append(libdir)

import jdecode
import utils
import cardlib

class TestJDecodeConsistency(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_exclude_types_stdin(self):
        # Conspiracy card: |5conspiracy|1backup plan|
        # Standard exclude_types includes 'conspiracy'
        card_text = "|5conspiracy|1backup plan|"

        with patch('sys.stdin', StringIO(card_text)):
             # This should return 0 cards if exclude_types is respected
             cards = jdecode.mtg_open_file('-', verbose=False)

        self.assertEqual(len(cards), 0, "Conspiracy card should be excluded when loading from stdin")

    def test_exclude_types_text_file(self):
        card_text = "|5conspiracy|1backup plan|"
        path = os.path.join(self.test_dir, 'cards.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(card_text)

        # This should return 0 cards if exclude_types is respected
        cards = jdecode.mtg_open_file(path, verbose=False)
        self.assertEqual(len(cards), 0, "Conspiracy card should be excluded when loading from single text file")

    def test_linetrans_text_file(self):
        # Card with lines that would be reordered by linetrans
        # Original:
        # destroy target creature.
        # flying
        # linetrans (True) should put 'flying' first.
        # |5creature|9destroy target creature.\flying|1test|

        # We need to use a format that linetrans actually affects.
        # In cardlib.py, text_pass_11_linetrans reorders lines.

        card_text = "|5creature|1test|9destroy target creature.\\flying|"
        path = os.path.join(self.test_dir, 'cards.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(card_text)

        # 1. With linetrans=True (default)
        cards_true = jdecode.mtg_open_file(path, verbose=False, linetrans=True)
        text_true = cards_true[0].text.encode()
        # linetrans should put 'flying' (keyline) before 'destroy...' (mainline)
        self.assertTrue(text_true.startswith("flying"), f"Expected text to start with 'flying', got: {text_true}")

        # 2. With linetrans=False
        cards_false = jdecode.mtg_open_file(path, verbose=False, linetrans=False)
        text_false = cards_false[0].text.encode()
        self.assertTrue(text_false.startswith("destroy"), f"Expected text to start with 'destroy', got: {text_false}")

if __name__ == '__main__':
    unittest.main()
