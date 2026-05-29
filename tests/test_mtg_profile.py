import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import io
from contextlib import redirect_stdout, redirect_stderr

# Add lib to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
import scripts.mtg_analyze as mtg_analyze

class TestMtgProfile(unittest.TestCase):
    def test_profile_basic(self):
        # We use a real file from testdata for robustness
        test_file = 'testdata/uthros.json'
        if not os.path.exists(test_file):
            self.skipTest("testdata/uthros.json not found")

        # Mock sys.argv to call profile
        test_args = ['mtg_analyze.py', 'profile', test_file, '--colors', 'U', '--no-color']

        with patch('sys.argv', test_args):
            f = io.StringIO()
            with redirect_stdout(f):
                mtg_analyze.main()

            output = f.getvalue()
            self.assertIn("MECHANICAL IDENTITY PROFILE", output)
            self.assertIn("Avg CMC", output)
            self.assertIn("Top Signature Mechanics", output)
            self.assertIn("Top Signature Actions", output)
            self.assertIn("Top Signature Subtypes", output)
            self.assertIn("Spacecraft", output) # Unique subtype of Uthros

    def test_profile_empty(self):
        # Test with filters that match nothing
        test_file = 'testdata/uthros.json'
        if not os.path.exists(test_file):
            self.skipTest("testdata/uthros.json not found")

        test_args = ['mtg_analyze.py', 'profile', test_file, '--colors', 'R', '--no-color', '--quiet']

        with patch('sys.argv', test_args):
            f = io.StringIO()
            with redirect_stdout(f):
                mtg_analyze.main()

            output = f.getvalue()
            # Should not crash, but might print nothing or a warning if not quiet
            # In this case, mtg_analyze.check_cards handles it
            self.assertEqual(output.strip(), "")

    def test_profile_lift_logic(self):
        # Test lift calculation with a small controlled dataset
        # We'll use a directory search to include multiple cards
        test_dir = 'testdata/'
        if not os.path.exists(test_dir):
            self.skipTest("testdata/ directory not found")

        # Profile Elf cards
        test_args = ['mtg_analyze.py', 'profile', test_dir, '--grep', 'Elf', '--no-color', '--top', '5']

        with patch('sys.argv', test_args):
            f = io.StringIO()
            with redirect_stdout(f):
                mtg_analyze.main()

            output = f.getvalue()
            self.assertIn("MECHANICAL IDENTITY PROFILE", output)
            self.assertIn("Elf", output)
            self.assertIn("x", output) # Lift multiplier should be present

if __name__ == '__main__':
    unittest.main()
