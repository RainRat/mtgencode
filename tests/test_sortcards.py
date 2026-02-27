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

    def test_sort_rarity_and_cmc(self):
        rare_data = {
            "name": "Test Rare",
            "manaCost": "{1}{R}",
            "types": ["Creature"],
            "rarity": "Rare",
            "power": "2",
            "toughness": "2"
        }
        card = Card(rare_data)
        classes = sortcards.sortcards([card])
        encoded = card.encode()

        self.assertIn(encoded, classes['rare'])
        self.assertIn(encoded, classes['CMC 2'])
        self.assertNotIn(encoded, classes['common'])

    def test_sort_summary(self):
        card_data = {
            "name": "Summary Card",
            "manaCost": "{1}{W}",
            "types": ["Instant"],
            "rarity": "Uncommon"
        }
        card = Card(card_data)
        # Testing the summary output mode
        classes = sortcards.sortcards([card], use_summary=True)
        summary_str = card.summary()

        self.assertIn(summary_str, classes['instants'])
        self.assertIn(summary_str, classes['uncommon'])
        self.assertIn(summary_str, classes['CMC 2'])

if __name__ == '__main__':
    unittest.main()
