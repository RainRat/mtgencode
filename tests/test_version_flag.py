import unittest
import sys
import os
import subprocess

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestVersionFlag(unittest.TestCase):

    def test_encode_version(self):
        for flag in ['-V', '--version']:
            out = subprocess.check_output([sys.executable, 'encode.py', flag], text=True)
            self.assertIn('mtgencode 1.0.0', out)

    def test_decode_version(self):
        for flag in ['-V', '--version']:
            out = subprocess.check_output([sys.executable, 'decode.py', flag], text=True)
            self.assertIn('mtgencode 1.0.0', out)

    def test_sortcards_version(self):
        for flag in ['-V', '--version']:
            out = subprocess.check_output([sys.executable, 'sortcards.py', flag], text=True)
            self.assertIn('mtgencode 1.0.0', out)

    def test_train_version(self):
        for flag in ['-V', '--version']:
            out = subprocess.check_output([sys.executable, 'train.py', flag], text=True)
            self.assertIn('mtgencode 1.0.0', out)

    def test_combinejson_version(self):
        for flag in ['-V', '--version']:
            out = subprocess.check_output([sys.executable, 'scripts/combinejson.py', flag], text=True)
            self.assertIn('mtgencode 1.0.0', out)

    def test_mtg_diff_version(self):
        for flag in ['-V', '--version']:
            out = subprocess.check_output([sys.executable, 'scripts/mtg_diff.py', flag], text=True)
            self.assertIn('mtgencode 1.0.0', out)

if __name__ == '__main__':
    unittest.main()
