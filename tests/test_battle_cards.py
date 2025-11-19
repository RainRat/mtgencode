import sys
import os
import unittest

# Add lib and scripts directories to the path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
scriptsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../scripts')
sys.path.append(libdir)
sys.path.append(scriptsdir)

import jdecode
from mtg_validate import check_types, check_pt

class TestBattleCards(unittest.TestCase):

    def setUp(self):
        self.cards = jdecode.mtg_open_file('tests/battle_cards.json')
        self.battle_card = self.cards[0]

    def test_check_types_for_battle(self):
        self.assertTrue(check_types(self.battle_card))

    def test_check_pt_for_battle(self):
        self.assertIsNone(check_pt(self.battle_card))

if __name__ == '__main__':
    unittest.main()
