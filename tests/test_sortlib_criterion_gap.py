import unittest
import os
import sys

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))
from sortlib import sort_cards

class TestSortlibCriterionGap(unittest.TestCase):
    def test_sort_cards_unknown_criterion(self):
        # Line 118: covers the 'else: return cards' branch when an unknown criterion is passed.
        cards = ["card1", "card2"]
        sorted_cards = sort_cards(cards, "unknown_criterion")
        self.assertEqual(cards, sorted_cards)

if __name__ == '__main__':
    unittest.main()
