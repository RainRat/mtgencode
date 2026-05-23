import sys
import os
import unittest
from unittest.mock import patch
import io

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
scriptsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../scripts')
sys.path.append(libdir)
sys.path.append(scriptsdir)

import mtg_validate
import cardlib

class TestMtgValidateGaps(unittest.TestCase):

    def test_main_cli_basic(self):
        cards = [
            cardlib.Card({"name": "Opt", "types": ["Instant"], "manaCost": "{U}"}),
            cardlib.Card({"name": "Bear", "types": ["Creature"], "power": "2", "toughness": "2", "manaCost": "{1}{G}"})
        ]

        with patch('mtg_validate.jdecode.mtg_open_file', return_value=cards):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                mtg_validate.main('dummy.json', quiet=True)
                output = fake_out.getvalue()
                self.assertIn("VALIDATION SUMMARY", output)
                self.assertIn("Valid Cards", output)
                self.assertIn("100.0%", output)

    def test_main_cli_with_invalid_cards(self):
        cards = [
            cardlib.Card({"name": "Bad Bear", "types": ["Creature"], "manaCost": "{1}{G}"})
        ]

        with patch('mtg_validate.jdecode.mtg_open_file', return_value=cards):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                mtg_validate.main('dummy.json', dump=True, quiet=True)
                output = fake_out.getvalue()
                self.assertIn("Invalid Cards", output)
                self.assertIn("---- pt ----", output)
                self.assertIn("Bad Bear", output)

    def test_rare_grams(self):
        card = cardlib.Card({"name": "Opt", "types": ["Instant"], "text": "Draw a card."})

        with patch.dict(mtg_validate.gramdicts, {2: {"draw a": 1, "a card": 5}}):
            rares = mtg_validate.rare_grams(card, thresh=2, grams=2)
            self.assertEqual(rares, 1)
            self.assertIsNone(mtg_validate.rare_grams(card, grams=3))

    def test_check_X_edge_cases(self):
        c = cardlib.Card({"name": "X Effect", "types": ["Instant"], "text": "{1}: Gain X life."})
        self.assertFalse(mtg_validate.check_X(c))

        c = cardlib.Card({"name": "Polukranos", "types": ["Creature"], "text": "{X}{X}{G}: Monstrosity X."})
        self.assertTrue(mtg_validate.check_X(c))

    def test_check_triggered_variants(self):
        c = cardlib.Card({"name": "Upkeep", "types": ["Enchantment"], "text": "At the beginning of your upkeep, gain 1 life."})
        self.assertTrue(mtg_validate.check_triggered(c))

        c = cardlib.Card({"name": "Grave Trigger", "types": ["Creature"], "text": "When @ is in your graveyard, do something."})
        self.assertTrue(mtg_validate.check_triggered(c))

        c = cardlib.Card({"name": "Suspended Trigger", "types": ["Creature"], "text": "When you do something, if @ is suspended, do more."})
        self.assertTrue(mtg_validate.check_triggered(c))

    def test_check_shuffle_variants(self):
        c = cardlib.Card({"name": "Searcher", "types": ["Creature"], "text": "Whenever a player searches their library, they shuffle."})
        self.assertTrue(mtg_validate.check_shuffle(c))

    def test_check_activated_edge_cases(self):
        c = cardlib.Card({"name": "Forecast Card", "types": ["Instant"], "text": "Forecast - {1}{U}: Reveal..."})
        self.assertIsNone(mtg_validate.check_activated(c))

    def test_check_chosen_variants(self):
        c = cardlib.Card({"name": "Opt", "types": ["Instant"], "text": "Discard a card chosen at random."})
        self.assertTrue(mtg_validate.check_chosen(c))

        c = cardlib.Card({"name": "Opt", "types": ["Instant"], "text": "If a card is chosen, do something."})
        self.assertTrue(mtg_validate.check_chosen(c))

if __name__ == "__main__":
    unittest.main()
