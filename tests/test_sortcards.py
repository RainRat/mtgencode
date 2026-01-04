import unittest
from cardlib import Card, fmt_ordered_old
import sortcards

class TestSortCards(unittest.TestCase):
    def test_sort_battle(self):
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
        # sortcards.sortcards now expects Card objects

        classes = sortcards.sortcards([card])

        # The output keys contain encoded strings (or raw if present)
        # Since we created card from dict, it has no raw, so encode() is called.
        encoded = card.encode()

        self.assertIn(encoded, classes['battles'])
        self.assertNotIn(encoded, classes['other'])

    def test_sort_planeswalker(self):
        pw_data = {
            "name": "Jace Test",
            "manaCost": "{3}{U}{U}",
            "type": "Legendary Planeswalker \u2014 Jace",
            "types": ["Planeswalker"],
            "subtypes": ["Jace"],
            "loyalty": "5",
            "text": "+1: Draw a card.",
            "rarity": "mythic"
        }
        card = Card(pw_data)

        classes = sortcards.sortcards([card])
        encoded = card.encode()

        self.assertIn(encoded, classes['planeswalkers'])
        self.assertNotIn(encoded, classes['other'])

if __name__ == '__main__':
    unittest.main()
