import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import io
import tempfile
import runpy

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
scriptsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../scripts')
sys.path.append(libdir)
sys.path.append(scriptsdir)

import mtg_validate
import cardlib
import utils


class TestMtgValidateGaps(unittest.TestCase):

    def setUp(self):
        if 'color_pie' not in mtg_validate.props:
            mtg_validate.props['color_pie'] = mtg_validate.check_color_pie

    def test_tqdm_fallback(self):
        fallback_tqdm = mtg_validate.tqdm
        items = [1, 2, 3]
        self.assertEqual(list(fallback_tqdm(items)), [1, 2, 3])

    def test_rare_grams_with_gramdicts(self):
        card = cardlib.Card({"name": "Opt", "types": ["Instant"], "text": "Draw a card."})

        with patch.dict(mtg_validate.gramdicts, {2: {"draw a": 1, "a card": 5}}, clear=True):
            rares = mtg_validate.rare_grams(card, thresh=2, grams=2)
            self.assertEqual(rares, 1)
            self.assertIsNone(mtg_validate.rare_grams(card, grams=3))

    def test_rare_grams_unseen_ngram(self):
        card = cardlib.Card({"name": "Opt", "types": ["Instant"], "text": "Draw a card."})

        with patch.dict(mtg_validate.gramdicts, {2: {"something else": 10}}, clear=True):
            rares = mtg_validate.rare_grams(card, thresh=2, grams=2)
            self.assertEqual(rares, 2)

    def test_check_pt_station_and_battle(self):
        c_battle = cardlib.Card({"name": "Invasion", "types": ["Battle"], "defense": "4"})
        self.assertIsNone(mtg_validate.check_pt(c_battle))

        c_station = cardlib.Card({"name": "Station", "types": ["Artifact"], "text": "Station."})
        self.assertIsNone(mtg_validate.check_pt(c_station))

    def test_check_X_edge_cases(self):
        c = cardlib.Card({"name": "X Effect", "types": ["Instant"], "text": "{1}: Gain X life."})
        self.assertFalse(mtg_validate.check_X(c))

        c = cardlib.Card({"name": "Polukranos", "types": ["Creature"], "text": "{X}{X}{G}: Monstrosity X."})
        self.assertTrue(mtg_validate.check_X(c))

        c_unused = cardlib.Card({"name": "Unused X", "types": ["Artifact"], "text": "{X}: Deal 1 damage."})
        self.assertFalse(mtg_validate.check_X(c_unused))

    def test_check_X_multi_line(self):
        c = cardlib.Card({
            "name": "X Manager",
            "types": ["Enchantment"],
            "text": "X is the number of creatures you control.\nAt the beginning of your upkeep, gain X life."
        })
        self.assertTrue(mtg_validate.check_X(c))

    def test_check_X_additional_patterns(self):
        c1 = cardlib.Card({"name": "Baku", "types": ["Creature"], "text": "remove X % counters: Deal 1 damage for each counter removed."})
        self.assertTrue(mtg_validate.check_X(c1))

        c2 = cardlib.Card({"name": "Cauldron", "types": ["Artifact"], "text": "{X}: note the color of mana spent."})
        self.assertTrue(mtg_validate.check_X(c2))

        c3 = cardlib.Card({"name": "Reinforcer", "types": ["Instant"], "text": "reinforce X - pay {X} pay {X}"})
        self.assertTrue(mtg_validate.check_X(c3))

        c4 = cardlib.Card({"name": "Container", "types": ["Enchantment"], "text": "Put a counter with {X} on @."})
        self.assertTrue(mtg_validate.check_X(c4))

        c5 = cardlib.Card({"name": "Morpher", "types": ["Creature"], "text": "X is 3. Morph {X}. Additional cost to cast."})
        self.assertTrue(mtg_validate.check_X(c5))

    def test_check_planeswalkers_additional(self):
        c1 = cardlib.Card({
            "name": "Walker Cmd",
            "types": ["Planeswalker"],
            "loyalty": "3",
            "text": "+&^: Gain 1 life.\n-&^^: Draw a card.\ncan be your commander"
        })
        self.assertTrue(mtg_validate.check_planeswalkers(c1))

        c2 = cardlib.Card({
            "name": "Walker Flip",
            "types": ["Planeswalker"],
            "loyalty": "3",
            "text": "+&^: Gain 1 life.\n-&^^: Draw a card.\ncountertype % loyalty\ntransform @"
        })
        self.assertTrue(mtg_validate.check_planeswalkers(c2))

        c_bad = cardlib.Card({
            "name": "Bad Walker",
            "types": ["Planeswalker"],
            "loyalty": "3",
            "text": "+&^: Gain 1 life.\nInvalid rule line."
        })
        self.assertFalse(mtg_validate.check_planeswalkers(c_bad))

    def test_check_levelup_additional(self):
        c1 = cardlib.Card({"name": "L1", "types": ["Creature"], "text": "Level up {1}. countertype % level. level &^^+ 2/2."})
        self.assertTrue(mtg_validate.check_levelup(c1))

        c2 = cardlib.Card({"name": "L2", "types": ["Creature"], "text": "Creature with level up.\nlevel up {1}."})
        self.assertTrue(mtg_validate.check_levelup(c2))

        c3 = cardlib.Card({"name": "L3", "types": ["Creature"], "text": "level 1-2."})
        self.assertFalse(mtg_validate.check_levelup(c3))

    def test_check_activated_edge_cases(self):
        c_forecast = cardlib.Card({"name": "Forecast Card", "types": ["Instant"], "text": "Forecast - {1}{U}: Reveal..."})
        self.assertIsNone(mtg_validate.check_activated(c_forecast))

        c_grave = cardlib.Card({"name": "Grave Act", "types": ["Creature"], "text": "Return @ from your graveyard: Gain 1 life."})
        self.assertIsNone(mtg_validate.check_activated(c_grave))

        c_stack = cardlib.Card({"name": "Stack Act", "types": ["Creature"], "text": "When spell is on the stack: Gain 1 life."})
        self.assertIsNone(mtg_validate.check_activated(c_stack))

    def test_check_triggered_variants(self):
        c_upkeep = cardlib.Card({"name": "Upkeep", "types": ["Enchantment"], "text": "At the beginning of your upkeep, gain 1 life."})
        self.assertTrue(mtg_validate.check_triggered(c_upkeep))

        c_grave = cardlib.Card({"name": "Grave Trigger", "types": ["Creature"], "text": "when @ is in your graveyard, do something."})
        self.assertTrue(mtg_validate.check_triggered(c_grave))

        c_grave_from = cardlib.Card({"name": "Grave From", "types": ["Creature"], "text": "when @ is put into a graveyard from your graveyard, gain 1 life."})
        self.assertTrue(mtg_validate.check_triggered(c_grave_from))

        c_suspend = cardlib.Card({"name": "Suspended Trigger", "types": ["Creature"], "text": "when you do something, if @ is suspended, do more."})
        self.assertTrue(mtg_validate.check_triggered(c_suspend))

        c_leaves = cardlib.Card({"name": "Leaves", "types": ["Creature"], "text": "when @ leaves the battlefield, draw a card."})
        self.assertTrue(mtg_validate.check_triggered(c_leaves))

        c_dies = cardlib.Card({"name": "Dies", "types": ["Creature"], "text": "when @ dies, gain 1 life."})
        self.assertTrue(mtg_validate.check_triggered(c_dies))

        c_exile = cardlib.Card({"name": "Exile", "types": ["Creature"], "text": "when you cast a spell, if that card is exiled, gain 1 life."})
        self.assertTrue(mtg_validate.check_triggered(c_exile))

        c_haunt = cardlib.Card({"name": "Haunt", "types": ["Creature"], "text": "when the creature @ haunts dies, gain 1 life."})
        self.assertTrue(mtg_validate.check_triggered(c_haunt))

        c_cycle = cardlib.Card({"name": "Cycle", "types": ["Creature"], "text": "when you cycle @, draw a card."})
        self.assertTrue(mtg_validate.check_triggered(c_cycle))

        c_turn = cardlib.Card({"name": "Turn", "types": ["Creature"], "text": "when a creature enters, this turn gain 1 life."})
        self.assertTrue(mtg_validate.check_triggered(c_turn))

        c_lib = cardlib.Card({"name": "Lib", "types": ["Creature"], "text": "when a spell is cast from your library, draw a card."})
        self.assertTrue(mtg_validate.check_triggered(c_lib))

        c_discard = cardlib.Card({"name": "Discard", "types": ["Creature"], "text": "when you discard @, gain 1 life."})
        self.assertTrue(mtg_validate.check_triggered(c_discard))

        c_general = cardlib.Card({"name": "General", "types": ["Creature"], "text": "when a player casts a spell, draw a card."})
        self.assertTrue(mtg_validate.check_triggered(c_general))

    def test_check_quotes_variants(self):
        c_even = cardlib.Card({"name": "Quote Hack", "types": ["Instant"], "text": '\'"quote\'"'})
        self.assertTrue(mtg_validate.check_quotes(c_even))

        c_odd = cardlib.Card({"name": "Odd Quotes", "types": ["Instant"], "text": '"unclosed quote'})
        self.assertFalse(mtg_validate.check_quotes(c_odd))

    def test_check_shuffle_variants(self):
        c = cardlib.Card({"name": "Searcher", "types": ["Creature"], "text": "Whenever a player searches their library, they shuffle."})
        self.assertTrue(mtg_validate.check_shuffle(c))

    def test_check_chosen_variants(self):
        c = cardlib.Card({"name": "Opt", "types": ["Instant"], "text": "Discard a card chosen at random."})
        self.assertTrue(mtg_validate.check_chosen(c))

        c = cardlib.Card({"name": "Opt", "types": ["Instant"], "text": "If a card is chosen, do something."})
        self.assertTrue(mtg_validate.check_chosen(c))

    def test_check_color_pie(self):
        c = cardlib.Card({"name": "White Card", "types": ["Instant"], "manaCost": "{W}", "text": "Destroy target player."})
        with patch.object(cardlib.Card, 'check_color_pie', return_value="Invalid target"):
            self.assertFalse(mtg_validate.check_color_pie(c))

        with patch.object(cardlib.Card, 'check_color_pie', return_value=True):
            self.assertTrue(mtg_validate.check_color_pie(c))

    def test_process_props_uncovered_and_dump(self):
        c_uncovered = cardlib.Card({"name": "Plain Instant", "types": ["Instant"], "text": "Gain 3 life."})
        c_invalid_cp = cardlib.Card({"name": "Pie Card", "types": ["Instant"], "manaCost": "{W}"})

        def mock_check_cp(self_card):
            if "pie" in self_card.name.lower():
                return "Pie violation detail"
            return None

        cards = [c_uncovered, c_invalid_cp]
        props_copy = mtg_validate.props.copy()
        props_copy['color_pie'] = mtg_validate.check_color_pie
        with patch.dict(mtg_validate.props, props_copy, clear=True):
            with patch.object(cardlib.Card, 'check_color_pie', mock_check_cp):
                with patch('sys.stdout', new=io.StringIO()) as fake_out:
                    mtg_validate.process_props(cards, dump=True, uncovered=True, quiet=True)
                    out = fake_out.getvalue()
                    self.assertIn("---- uncovered ----", out)
                    self.assertIn("---- color_pie ---- (Pie violation detail)", out)

    def test_main_cli_console_summary_breakdown(self):
        cards = [
            cardlib.Card({"name": "Opt", "types": ["Instant"], "manaCost": "{U}"}),
            cardlib.Card({"name": "Bear", "types": ["Creature"], "power": "2", "toughness": "2", "manaCost": "{1}{G}"}),
            cardlib.Card({"name": "Bad Bear", "types": ["Creature"], "manaCost": "{1}{G}"})
        ]

        with patch('mtg_validate.jdecode.mtg_open_file', return_value=cards):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                mtg_validate.main('dummy.json', use_color=True, quiet=False)
                output = fake_out.getvalue()
                self.assertIn("VALIDATION SUMMARY", output)
                self.assertIn("PROPERTY BREAKDOWN", output)

    def test_main_outfile_and_color_and_sort(self):
        cards = [
            cardlib.Card({"name": "Opt", "types": ["Instant"], "manaCost": "{U}"}),
            cardlib.Card({"name": "Bear", "types": ["Creature"], "power": "2", "toughness": "2", "manaCost": "{1}{G}"})
        ]

        with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf8') as tmp:
            tmp_name = tmp.name

        try:
            with patch('mtg_validate.jdecode.mtg_open_file', return_value=cards):
                with patch('sys.stderr', new=io.StringIO()) as fake_err:
                    mtg_validate.main('dummy.json', oname=tmp_name, verbose=True, use_color=True, sort='cmc', quiet=False)
                    err_out = fake_err.getvalue()
                    self.assertIn("Writing validation report to:", err_out)

            with open(tmp_name, 'r', encoding='utf8') as f:
                content = f.read()
                self.assertIn("VALIDATION SUMMARY", content)
                self.assertIn("PROPERTY BREAKDOWN", content)
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

    def test_main_color_pie_flag(self):
        cards = [cardlib.Card({"name": "Opt", "types": ["Instant"], "manaCost": "{U}"})]
        with patch('mtg_validate.jdecode.mtg_open_file', return_value=cards):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                mtg_validate.main('dummy.json', color_pie=True, use_color=False, quiet=True)
                out = fake_out.getvalue()
                self.assertIn("VALIDATION SUMMARY", out)

    def test_cli_execution_via_runpy(self):
        script_path = os.path.join(scriptsdir, 'mtg_validate.py')

        cards = [cardlib.Card({"name": "Opt", "types": ["Instant"], "manaCost": "{U}"})]
        with patch('sys.argv', ['mtg_validate.py', '-p', '-q']):
            with patch('mtg_validate.jdecode.mtg_open_file', return_value=cards):
                with patch('sys.stdout', new=io.StringIO()) as fake_out:
                    with self.assertRaises(SystemExit) as cm:
                        runpy.run_path(script_path, run_name='__main__')
                    self.assertEqual(cm.exception.code, 0)
                    out = fake_out.getvalue()
                    self.assertIn("Dry Run Summary", out)

    def test_cli_interactive_default_dataset_fallback(self):
        script_path = os.path.join(scriptsdir, 'mtg_validate.py')
        cards = [cardlib.Card({"name": "Opt", "types": ["Instant"], "manaCost": "{U}"})]

        with patch('sys.argv', ['mtg_validate.py', '-p']), \
             patch('sys.stdin.isatty', return_value=True), \
             patch('os.path.exists', return_value=True), \
             patch('mtg_validate.jdecode.mtg_open_file', return_value=cards), \
             patch('sys.stderr', new=io.StringIO()) as fake_err, \
             patch('sys.stdout', new=io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path(script_path, run_name='__main__')
            self.assertEqual(cm.exception.code, 0)
            err = fake_err.getvalue()
            self.assertIn("Notice: Using default dataset:", err)


if __name__ == "__main__":
    unittest.main()
