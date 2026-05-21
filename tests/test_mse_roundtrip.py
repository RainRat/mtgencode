import sys
import os
import unittest
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

from lib.cardlib import Card
from lib import jdecode, utils

class TestMSERoundtrip(unittest.TestCase):

    def test_planeswalker_roundtrip_loyalty_costs(self):
        """
        Tests that Planeswalker loyalty costs are preserved when exporting to MSE
        and then reopening the MSE content.
        """
        pw_json = {
            "name": "Jace, the Mind Sculptor",
            "manaCost": "{2}{U}{U}",
            "types": ["Planeswalker"],
            "subtypes": ["Jace"],
            "text": "+2: Look at the top card of target player's library.\n0: Draw three cards.\n-1: Return target creature to its owner's hand.\n-12: Exile all cards from target player's library.",
            "loyalty": "3",
            "rarity": "Mythic"
        }
        card = Card(pw_json)
        mse_out = card.to_mse()

        # Verify MSE output has loyalty cost fields
        self.assertIn("loyalty cost 1: +2", mse_out)
        self.assertIn("loyalty cost 2: 0", mse_out)
        self.assertIn("loyalty cost 3: -1", mse_out)
        self.assertIn("loyalty cost 4: -12", mse_out)

        # Reopen
        srcs, _ = jdecode.mtg_open_mse_content(mse_out)
        self.assertIn("jace, the mind sculptor", srcs)
        reopened_json = srcs["jace, the mind sculptor"][0]

        # The bug is that reopened_json["text"] will lack the loyalty costs
        expected_text = "+2: Look at the top card of target player's library.\n0: Draw three cards.\n-1: Return target creature to its owner's hand.\n-12: Exile all cards from target player's library."

        # Normalized comparison (ignoring minor whitespace/case if needed, but let's be strict first)
        self.assertEqual(reopened_json["text"].strip(), expected_text)

    def test_planeswalker_roundtrip_with_x_costs(self):
        pw_json = {
            "name": "Nissa, Steward of Elements",
            "manaCost": "{X}{G}{U}",
            "types": ["Planeswalker"],
            "text": "+X: Scry X.\n-10: You win.",
            "loyalty": "X",
            "rarity": "Mythic"
        }
        card = Card(pw_json)
        mse_out = card.to_mse()

        self.assertIn("loyalty cost 1: +X", mse_out)
        self.assertIn("loyalty cost 2: -10", mse_out)

        srcs, _ = jdecode.mtg_open_mse_content(mse_out)
        reopened_json = srcs["nissa, steward of elements"][0]

        expected_text = "+X: Scry X.\n-10: You win."
        self.assertEqual(reopened_json["text"].strip(), expected_text)

if __name__ == '__main__':
    unittest.main()
