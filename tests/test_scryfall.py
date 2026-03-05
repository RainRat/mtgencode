import unittest
import sys
import os

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode, utils

class TestScryfallNormalization(unittest.TestCase):

    def test_normalize_basic_card(self):
        scryfall_card = {
            "object": "card",
            "name": "Shock",
            "mana_cost": "{R}",
            "type_line": "Instant",
            "oracle_text": "Shock deals 2 damage to any target.",
            "set": "m21",
            "collector_number": "159",
            "rarity": "common"
        }
        normalized = jdecode._normalize_scryfall_card(scryfall_card.copy())

        self.assertEqual(normalized['manaCost'], "{R}")
        self.assertEqual(normalized['text'], "Shock deals 2 damage to any target.")
        self.assertEqual(normalized['type'], "Instant")
        self.assertEqual(normalized['setCode'], "M21")
        self.assertEqual(normalized['number'], "159")
        self.assertEqual(normalized['types'], ["Instant"])

    def test_normalize_multifaced_card(self):
        scryfall_card = {
            "object": "card",
            "name": "Fire // Ice",
            "rarity": "uncommon",
            "card_faces": [
                {
                    "object": "card_face",
                    "name": "Fire",
                    "mana_cost": "{1}{R}",
                    "type_line": "Instant",
                    "oracle_text": "Fire deals 2 damage divided as you choose among one or two targets."
                },
                {
                    "object": "card_face",
                    "name": "Ice",
                    "mana_cost": "{1}{U}",
                    "type_line": "Instant",
                    "oracle_text": "Tap target permanent.\nDraw a card."
                }
            ]
        }
        normalized = jdecode._normalize_scryfall_card(scryfall_card.copy())

        # Main fields from first face
        self.assertEqual(normalized['name'], "Fire")
        self.assertEqual(normalized['manaCost'], "{1}{R}")
        self.assertEqual(normalized['text'], "Fire deals 2 damage divided as you choose among one or two targets.")

        # B-side fields from second face
        self.assertIn(utils.json_field_bside, normalized)
        bside = normalized[utils.json_field_bside]
        self.assertEqual(bside['name'], "Ice")
        self.assertEqual(bside['manaCost'], "{1}{U}")
        self.assertEqual(bside['text'], "Tap target permanent.\nDraw a card.")
        self.assertEqual(bside['types'], ["Instant"])

    def test_normalize_transform_card(self):
        scryfall_card = {
            "object": "card",
            "name": "Delver of Secrets // Insectile Aberration",
            "rarity": "uncommon",
            "card_faces": [
                {
                    "object": "card_face",
                    "name": "Delver of Secrets",
                    "mana_cost": "{U}",
                    "type_line": "Creature — Human Wizard",
                    "oracle_text": "At the beginning of your upkeep...",
                    "power": "1",
                    "toughness": "1"
                },
                {
                    "object": "card_face",
                    "name": "Insectile Aberration",
                    "mana_cost": "",
                    "type_line": "Creature — Human Insect",
                    "oracle_text": "Flying",
                    "power": "3",
                    "toughness": "2"
                }
            ]
        }
        normalized = jdecode._normalize_scryfall_card(scryfall_card.copy())

        self.assertEqual(normalized['power'], "1")
        self.assertEqual(normalized['toughness'], "1")
        self.assertEqual(normalized['subtypes'], ["Human", "Wizard"])

        bside = normalized[utils.json_field_bside]
        self.assertEqual(bside['power'], "3")
        self.assertEqual(bside['toughness'], "2")
        self.assertEqual(bside['subtypes'], ["Human", "Insect"])

    def test_normalize_planeswalker_and_battle(self):
        scryfall_card = {
            "object": "card",
            "name": "Test PW",
            "card_faces": [
                {
                    "object": "card_face",
                    "name": "PW Face",
                    "type_line": "Legendary Planeswalker",
                    "loyalty": "3"
                },
                {
                    "object": "card_face",
                    "name": "Battle Face",
                    "type_line": "Battle — Siege",
                    "defense": "5"
                }
            ]
        }
        normalized = jdecode._normalize_scryfall_card(scryfall_card.copy())
        self.assertEqual(normalized['loyalty'], "3")
        self.assertEqual(normalized[utils.json_field_bside]['defense'], "5")

    def test_mtg_open_json_obj_scryfall_list(self):
        # Scryfall Bulk Data is a list of card objects
        scryfall_list = [
            {"object": "card", "name": "Card A", "rarity": "common"},
            {"object": "card", "name": "Card B", "rarity": "rare"}
        ]
        allcards, bad_sets = jdecode.mtg_open_json_obj(scryfall_list)
        self.assertEqual(len(allcards), 2)
        self.assertIn("card a", allcards)
        self.assertIn("card b", allcards)

    def test_mtg_open_json_obj_scryfall_search_result(self):
        # Scryfall Search Result is a dict with "data" as a list
        scryfall_search = {
            "object": "list",
            "total_cards": 1,
            "has_more": False,
            "data": [
                {"object": "card", "name": "Search Card", "rarity": "uncommon"}
            ]
        }
        allcards, bad_sets = jdecode.mtg_open_json_obj(scryfall_search)
        self.assertEqual(len(allcards), 1)
        self.assertIn("search card", allcards)

    def test_normalize_edge_cases(self):
        # Non-dict
        self.assertEqual(jdecode._normalize_scryfall_card(123), 123)
        # Dict but not card or card_face
        not_a_card = {"object": "error", "code": "not_found"}
        self.assertEqual(jdecode._normalize_scryfall_card(not_a_card), not_a_card)

        # card_face directly
        face = {"object": "card_face", "mana_cost": "{W}", "oracle_text": "Hi"}
        normalized_face = jdecode._normalize_scryfall_card(face)
        self.assertEqual(normalized_face['manaCost'], "{W}")
        self.assertEqual(normalized_face['text'], "Hi")

if __name__ == '__main__':
    unittest.main()
