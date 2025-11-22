import sys
import os
import unittest

# Add lib and scripts directories to the path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

from cardlib import Card
import utils

class TestBattleEncoding(unittest.TestCase):

    def test_battle_defense_in_loyalty(self):
        # Create a mock Battle card json
        card_data = {
            "name": "Invasion of Test",
            "manaCost": "{2}{R}",
            "type": "Battle \u2014 Siege",
            "types": ["Battle"],
            "subtypes": ["Siege"],
            "defense": "5",
            "text": "Test text.",
            "rarity": "common"
        }

        card = Card(card_data)
        self.assertTrue(card.parsed)
        self.assertTrue(card.valid)

        # Check that defense is stored in loyalty field
        self.assertEqual(card.loyalty, utils.to_unary("5"))
        # self.assertEqual(card.loyalty_value, 5) # loyalty_value is None because value is unary string

        # Check encoding
        encoded = card.encode()
        # field_label_loyalty is '7'
        # So we expect |7&^^^^^|
        expected_segment = "|7" + utils.to_unary("5") + "|"
        self.assertIn(expected_segment, encoded)

        # Check formatting
        formatted = card.format()
        # Should use [[ ]]
        self.assertIn("[[5]]", formatted)

    def test_station_threshold_preservation(self):
        # Use realistic Station card text structure from testdata/uthros.json
        text_content = (
            "Station (Tap another creature you control: Put charge counters equal to its power on this Spacecraft. "
            "Station only as a sorcery. It's an artifact creature at 12+.)\n"
            "STATION 3+\n"
            "Whenever you cast an artifact spell, draw a card. Put a charge counter on this Spacecraft.\n"
            "STATION 12+\n"
            "Flying\n"
            "This Spacecraft gets +1/+0 for each artifact you control."
        )

        card_data = {
            "name": "Test Station",
            "type": "Artifact \u2014 Spacecraft",
            "types": ["Artifact"],
            "subtypes": ["Spacecraft"],
            "text": text_content,
            "power": "0",
            "toughness": "8",
            "rarity": "rare"
        }
        card = Card(card_data)
        self.assertTrue(card.parsed)

        # Text should contain unary versions of 3 and 12
        # Note: fields_from_json lowercases the text and converts numbers to unary.
        encoded_text = card.text.text

        # 3 -> &^^^
        unary_3 = utils.to_unary("3")
        # 12 -> &^^^^^^^^^^^^
        unary_12 = utils.to_unary("12")

        # "STATION 3+" becomes "station &^^^+" (after lowercase and unary conversion)
        # "STATION 12+" becomes "station &^^^^^^^^^^^^+"

        self.assertIn("station " + unary_3 + "+", encoded_text)
        self.assertIn("station " + unary_12 + "+", encoded_text)

        # Verify that the Station keyword itself is present (it was in the original text too)
        # The reminder text might be stripped or processed, but the keyword "station" should be there.
        self.assertIn("station", encoded_text)

if __name__ == '__main__':
    unittest.main()
