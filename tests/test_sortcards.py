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
        # sortcards expects old ordered, unlabeled format
        encoded = card.encode(fmt_ordered=fmt_ordered_old, fmt_labeled={})

        classes = sortcards.sortcards([encoded])

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
        encoded = card.encode(fmt_ordered=fmt_ordered_old, fmt_labeled={})

        classes = sortcards.sortcards([encoded])

        self.assertIn(encoded, classes['planeswalkers'])
        self.assertNotIn(encoded, classes['other'])

if __name__ == '__main__':
    unittest.main()
