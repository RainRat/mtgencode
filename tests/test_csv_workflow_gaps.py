import unittest
import sys
import os

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib.cardlib import Card
from lib import jdecode

class TestCSVWorkflowGaps(unittest.TestCase):

    def test_card_get_face_csv_data_loyalty(self):
        # Trigger line 1362 (loyalty instead of pt)
        card = Card({"name": "Jace", "types": ["Planeswalker"], "loyalty": "3", "rarity": "mythic"})
        csv_data = card._get_face_csv_data()
        # Name, Cost, Type, Subtypes, Text, Stat, Rarity
        self.assertEqual(csv_data[5], "3")
        self.assertEqual(csv_data[6], "M")

    def test_card_get_csv_data_bside(self):
        # Trigger lines 1379-1392 (bside merging)
        card_json = {
            "name": "Side A",
            "manaCost": "{1}{R}",
            "types": ["Instant"],
            "rarity": "Common",
            "bside": {
                "name": "Side B",
                "types": ["Sorcery"],
                "rarity": "Common"
            }
        }
        card = Card(card_json)
        csv_data = card._get_csv_data()
        self.assertEqual(csv_data[0].lower(), "side a // side b")
        # manaCost of Side B is empty, so it should just be {1}{R}
        self.assertEqual(csv_data[1], "{1}{R}")
        self.assertEqual(csv_data[2].lower(), "instant // sorcery")
        self.assertEqual(csv_data[6], "C // C")

    def test_card_get_csv_data_single_face(self):
        # Trigger line 1392 (no bside)
        card = Card({"name": "Shock", "manaCost": "{R}", "types": ["Instant"], "rarity": "Common"})
        csv_data = card._get_csv_data()
        self.assertEqual(csv_data[0].lower(), "shock")
        self.assertEqual(csv_data[1], "{R}")

    def test_split_csv_row_multi_face(self):
        # Trigger lines 53-68 in jdecode.py
        row = {
            'name': 'Fire // Ice',
            'mana_cost': '{1}{R} // {1}{U}',
            'type': 'Instant // Instant',
            'rarity': 'Uncommon'
        }
        split_result = jdecode._split_csv_row(row)
        self.assertIsInstance(split_result, tuple)
        front, back = split_result
        self.assertEqual(front['name'], 'Fire')
        self.assertEqual(back['name'], 'Ice')
        self.assertEqual(front['mana_cost'], '{1}{R}')
        self.assertEqual(back['mana_cost'], '{1}{U}')
        # Rarity does not have //, so both get 'Uncommon'
        self.assertEqual(front['rarity'], 'Uncommon')
        self.assertEqual(back['rarity'], 'Uncommon')

    def test_csv_row_to_dict_pt_guessing(self):
        # Trigger lines 103-106 in jdecode.py
        # Ambiguous pt: Creature -> Power
        row_creature = {'name': 'Bear', 'type': 'Creature', 'pt': '2'}
        d_creature = jdecode._csv_row_to_dict(row_creature)
        self.assertEqual(d_creature['power'], '2')
        self.assertNotIn('loyalty', d_creature)

        # Ambiguous pt: Non-Creature -> Loyalty
        # Use Artifact to avoid hitting the 'Planeswalker' check at line 96
        row_other = {'name': 'Relic', 'type': 'Artifact', 'pt': '3'}
        d_other = jdecode._csv_row_to_dict(row_other)
        self.assertEqual(d_other['loyalty'], '3')
        self.assertNotIn('power', d_other)

    def test_mtg_open_csv_reader_multi_face(self):
        # Trigger lines 120-123 in jdecode.py
        rows = [{
            'name': 'Fire // Ice',
            'mana_cost': '{1}{R} // {1}{U}',
            'type': 'Instant // Instant',
            'rarity': 'Uncommon'
        }]
        srcs, _ = jdecode.mtg_open_csv_reader(rows)
        self.assertIn('fire', srcs)
        card = srcs['fire'][0]
        self.assertEqual(card['name'], 'Fire')
        self.assertIn(jdecode.utils.json_field_bside, card)
        self.assertEqual(card[jdecode.utils.json_field_bside]['name'], 'Ice')

if __name__ == '__main__':
    unittest.main()
