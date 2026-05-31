import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import argparse
import io

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import scripts.mtg_analyze as mtg_analyze

class TestMtgProfile(unittest.TestCase):

    def test_handle_profile_basic(self):
        # Create a mock args object
        args = argparse.Namespace(
            infile='test_dataset.json',
            top=10,
            color=False,
            quiet=True,
            verbose=False,
            grep=None, vgrep=None, grep_name=None, exclude_name=None,
            grep_type=None, exclude_type=None, grep_text=None, exclude_text=None,
            grep_cost=None, exclude_cost=None, grep_pt=None, exclude_pt=None,
            grep_loyalty=None, exclude_loyalty=None, set=None, rarity=None,
            colors=['W'], identity=None, id_count=None, cmc=None, pow=None,
            tou=None, loy=None, mechanic=None, action=None, deck=None,
            booster=0, box=0, limit=0, sample=0, shuffle=False, seed=None
        )

        # Capture stdout
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            mtg_analyze.handle_profile(args)
            output = fake_out.getvalue()

            # Check for key sections
            self.assertIn("MECHANICAL IDENTITY PROFILE", output)
            self.assertIn("Avg CMC", output)
            self.assertIn("Signature Mechanics", output)
            self.assertIn("Flying", output)
            self.assertIn("Signature Subtypes", output)
            self.assertIn("Bird", output)

            # Verify Lift for Flying (Subset 100%, Baseline 50% -> 2.00x)
            self.assertIn("2.00x", output)

    def test_handle_profile_empty(self):
        args = argparse.Namespace(
            infile='test_dataset.json',
            top=10,
            color=False,
            quiet=True,
            colors=['R'] # No Red cards in test_dataset
        )
        # Should not crash, just return or print a message via check_cards
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            mtg_analyze.handle_profile(args)
            # check_cards prints to stderr if not quiet, but here it is handled by the script

if __name__ == "__main__":
    unittest.main()
