import unittest
from unittest.mock import MagicMock
import sys
import os

# Add project root and scripts directory to path
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/..')
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../scripts')

from scripts.mtg_analyze import analyze_subtypes
import cardlib

class TestMtgSubtypesBug(unittest.TestCase):

    def test_analyze_subtypes_no_subtypes(self):
        # Create a mock card with no subtypes
        c = MagicMock(spec=cardlib.Card)
        c.color_identity = "W"
        c.subtypes = []
        cards = [c]

        # This should currently raise ZeroDivisionError because tot_gi will be 0
        try:
            stats = analyze_subtypes(cards)
            self.assertEqual(stats['total_cards'], 1)
        except ZeroDivisionError:
            self.fail("analyze_subtypes raised ZeroDivisionError with no subtypes")
        except Exception as e:
            self.fail(f"analyze_subtypes raised unexpected exception: {e}")

if __name__ == '__main__':
    unittest.main()
