import unittest
import sys
import os

# Add lib and scripts directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import cardlib

class TestColorPieValidation(unittest.TestCase):

    def test_mechanic_violations(self):
        # Blue creature with Deathtouch (Break: Deathtouch is BGC)
        break_card = cardlib.Card({
            'name': 'Spy',
            'manaCost': '{U}',
            'types': ['Creature'],
            'text': 'Deathtouch',
            'pt': '1/1'
        })
        res = break_card.check_color_pie()
        self.assertIsInstance(res, str)
        self.assertIn('Deathtouch', res)

        # Black creature with Deathtouch (Valid)
        valid_card = cardlib.Card({
            'name': 'Assassin',
            'manaCost': '{B}',
            'types': ['Creature'],
            'text': 'Deathtouch',
            'pt': '1/1'
        })
        self.assertTrue(valid_card.check_color_pie())

    def test_uncast_violation(self):
        # Green card with "uncast" (Break: Uncast is UC)
        break_card = cardlib.Card({
            'name': 'Nature\'s No',
            'manaCost': '{G}',
            'types': ['Instant'],
            'text': 'uncast target spell'
        })
        res = break_card.check_color_pie()
        self.assertIsInstance(res, str)
        self.assertIn('Uncast', res)

        # Blue card with "uncast" (Valid)
        valid_card = cardlib.Card({
            'name': 'Counterspell',
            'manaCost': '{UU}',
            'types': ['Instant'],
            'text': 'uncast target spell'
        })
        self.assertTrue(valid_card.check_color_pie())

    def test_mana_action(self):
        # Blue creature that adds mana (Break: Mana is GRC)
        break_card = cardlib.Card({
            'name': 'Mana Merfolk',
            'manaCost': '{U}',
            'types': ['Creature'],
            'text': 'T: Add {U}',
            'pt': '1/1'
        })
        # Note: In our current implementation, 'Mana' action is mapped to 'GRC'
        res = break_card.check_color_pie()
        self.assertIsInstance(res, str)
        self.assertIn('Mana', res)

        # Green creature that adds mana (Valid)
        valid_card = cardlib.Card({
            'name': 'Llanowar Elves',
            'manaCost': '{G}',
            'types': ['Creature'],
            'text': 'T: Add {G}',
            'pt': '1/1'
        })
        self.assertTrue(valid_card.check_color_pie())

    def test_no_relevant_features(self):
        # Vanilla 2/2 for 2 (Should return None, as it has no mechanics/actions mapped in the color pie)
        vanilla = cardlib.Card({
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'types': ['Creature'],
            'pt': '2/2'
        })
        self.assertIsNone(vanilla.check_color_pie())

    def test_colorless_defender(self):
        # Colorless artifact with Defender (Valid: Defender is WUBRGC)
        wall = cardlib.Card({
            'name': 'Wall',
            'types': ['Artifact', 'Creature'],
            'text': 'Defender',
            'pt': '0/4'
        })
        self.assertTrue(wall.check_color_pie())

if __name__ == '__main__':
    unittest.main()
