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

        # Mock cards
        card1 = MagicMock()
        card1.name = "White Bird"
        card1.valid = True
        card1.parsed = True
        card1.cost = MagicMock()
        card1.cost.cmc = 2.0
        card1.cost.colors = "W"
        card1.pt_p = "&^"
        card1.pt_t = "&^"
        card1.pt = "&^/&^"
        card1.loyalty = ""
        card1.rarity_name = "common"
        card1.types = ["creature"]
        card1.supertypes = []
        card1.subtypes = ["bird"]
        card1.text = MagicMock()
        card1.text.encode.return_value = "text"
        card1.text.text = "text"
        card1.text_lines = [card1.text]
        card1.text_words = ["text"]
        card1.mechanics = {"Flying"}
        card1.actions = set()
        card1.color_identity = "W"
        card1.complexity_score = 1.0

        card2 = MagicMock()
        card2.name = "Blue Bird"
        card2.valid = True
        card2.parsed = True
        card2.cost = MagicMock()
        card2.cost.cmc = 4.0
        card2.cost.colors = "U"
        card2.pt_p = "&^&^"
        card2.pt_t = "&^&^"
        card2.pt = "&^&^/&^&^"
        card2.loyalty = ""
        card2.rarity_name = "common"
        card2.types = ["creature"]
        card2.supertypes = []
        card2.subtypes = ["bird"]
        card2.text = MagicMock()
        card2.text.encode.return_value = "text"
        card2.text.text = "text"
        card2.text_lines = [card2.text]
        card2.text_words = ["text"]
        card2.mechanics = set()
        card2.actions = set()
        card2.color_identity = "U"
        card2.complexity_score = 3.0

        # Capture stdout
        with patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards') as mock_load:
            # First call for target_cards, second call for baseline_cards
            mock_load.side_effect = [[card1], [card1, card2]]
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                mtg_analyze.handle_profile(args)
                output = fake_out.getvalue()

                # Check for key sections
                self.assertIn("UNIQUE FEATURES PROFILE", output)
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
        with patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards', return_value=[]):
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                mtg_analyze.handle_profile(args)

if __name__ == "__main__":
    unittest.main()
