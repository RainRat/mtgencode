import sys
import os
import unittest
import tempfile
import json
from collections import OrderedDict

# Ensure root is in pythonpath
sys.path.append(os.getcwd())

from scripts.analysis import get_statistics
from scripts.ngrams import build_ngram_model
import lib.jdecode as jdecode

class TestAnalysis(unittest.TestCase):
    def setUp(self):
        # Create a small dataset of cards in MTGJSON v5 format
        self.cards_data = {
            "data": {
                "TEST": {
                    "name": "Test Set",
                    "code": "TEST",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Plains",
                            "types": ["Land"],
                            "text": "{T}: Add {W}.",
                            "rarity": "Common"
                        },
                        {
                            "name": "Grizzly Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "text": "Bear power.",
                            "rarity": "Common",
                            "power": "2",
                            "toughness": "2"
                        }
                    ]
                }
            }
        }

        # Write to a temporary JSON file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.json_path = os.path.join(self.temp_dir.name, "test_cards.json")
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.cards_data, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_statistics_without_lm(self):
        stats = get_statistics(self.json_path, lm=None)
        self.assertIn('cards', stats)
        self.assertIn('props', stats)
        self.assertEqual(len(stats['cards']), 2)

    def test_get_statistics_with_lm_sep_true(self):
        cards = jdecode.mtg_open_file(self.json_path)
        # Build language model with sep=True
        lm = build_ngram_model(cards, n=2, separate_lines=True)

        # Test with sep=True
        stats = get_statistics(self.json_path, lm=lm, sep=True)
        self.assertIn('ngram', stats)
        ngram_stats = stats['ngram']
        self.assertIn('perp_mean', ngram_stats)
        self.assertIn('perp_per_mean', ngram_stats)

    def test_get_statistics_with_lm_sep_false(self):
        cards = jdecode.mtg_open_file(self.json_path)
        # Build language model with sep=False
        lm = build_ngram_model(cards, n=2, separate_lines=False)

        # Test with sep=False to exercise the else block
        stats = get_statistics(self.json_path, lm=lm, sep=False)
        self.assertIn('ngram', stats)
        ngram_stats = stats['ngram']
        self.assertIn('perp_mean', ngram_stats)
        self.assertIn('perp_per_mean', ngram_stats)

if __name__ == '__main__':
    unittest.main()
