import json
import os
import sys
import unittest
import tempfile
import pytest

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode, cardlib

class TestBadSetsFiltering(unittest.TestCase):
    def test_funny_set_filtering(self):
        # Create a temporary JSON file with a funny set and a regular set
        test_data = {
            "data": {
                "FUN": {
                    "name": "Funny Set",
                    "code": "FUN",
                    "type": "funny",
                    "cards": [
                        {
                            "name": "Funny Card",
                            "types": ["Creature"],
                            "supertypes": [],
                            "subtypes": [],
                            "text": "Funny text.",
                            "manaCost": "{R}",
                            "power": "1",
                            "toughness": "1",
                            "rarity": "common"
                        }
                    ]
                },
                "REG": {
                    "name": "Regular Set",
                    "code": "REG",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Regular Card",
                            "types": ["Creature"],
                            "supertypes": [],
                            "subtypes": [],
                            "text": "Regular text.",
                            "manaCost": "{G}",
                            "power": "2",
                            "toughness": "2",
                            "rarity": "common"
                        }
                    ]
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False, encoding='utf-8') as tmp:
            json.dump(test_data, tmp)
            tmp_path = tmp.name

        try:
            # Parse the file using mtg_open_file
            # We expect 'Funny Card' to be filtered out because type is 'funny'
            # causing 'FUN' to be in bad_sets.
            cards = jdecode.mtg_open_file(tmp_path, verbose=True)

            card_names = [c.name for c in cards]
            print(f"Loaded cards: {card_names}")

            # Names are lowercased by the library
            self.assertIn("regular card", card_names)
            self.assertNotIn("funny card", card_names)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
