import sys
import os
import unittest
from unittest.mock import patch

# Ensure lib and scripts are in path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
if libdir not in sys.path:
    sys.path.append(libdir)

import cardlib
import utils

class TestRecommendedCMC(unittest.TestCase):
    def test_basic_creature(self):
        # 2/2 for 2 mana
        d = {'name': 'Bears', 'types': ['Creature'], 'power': '2', 'toughness': '2', 'manaCost': '{1}{G}'}
        c = cardlib.Card(d)
        self.assertEqual(c.recommended_cmc, 2.0)
        self.assertEqual(c.power_rating, 1.0)

    def test_keywords(self):
        # 2/1 for 1 mana with Flying (1.5)
        # Score = 2 + 1 + 1.5 = 4.5
        # Fair MV = 4.5 / 2 = 2.25 -> 2.3
        d = {'name': 'Bird', 'types': ['Creature'], 'power': '2', 'toughness': '1', 'manaCost': '{U}', 'text': 'Flying'}
        c = cardlib.Card(d)
        self.assertEqual(c.recommended_cmc, 2.2)

    def test_negative_keywords(self):
        # 4/4 for 4 mana with Defender (-1.0)
        # Score = 4 + 4 - 1.0 = 7.0
        # Fair MV = 7.0 / 2 = 3.5
        d = {'name': 'Wall', 'types': ['Creature'], 'power': '4', 'toughness': '4', 'manaCost': '{4}', 'text': 'Defender'}
        c = cardlib.Card(d)
        self.assertEqual(c.recommended_cmc, 3.5)

    def test_non_creature(self):
        d = {'name': 'Growth', 'types': ['Instant'], 'manaCost': '{G}', 'text': 'Target creature gets +3/+3.'}
        c = cardlib.Card(d)
        self.assertEqual(c.recommended_cmc, 0.0)

    def test_bside(self):
        # Front: 2/2 (2.0), Back: 4/4 (4.0)
        d = {
            'name': 'Small', 'types': ['Creature'], 'power': '2', 'toughness': '2', 'manaCost': '{1}{G}',
            'bside': {'name': 'Big', 'types': ['Creature'], 'power': '4', 'toughness': '4', 'manaCost': '{4}{G}'}
        }
        c = cardlib.Card(d)
        self.assertEqual(c.recommended_cmc, 4.0)

if __name__ == '__main__':
    unittest.main()
