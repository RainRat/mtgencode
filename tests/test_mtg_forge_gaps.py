import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import io

# Add lib and scripts directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
scriptsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../scripts')
sys.path.append(libdir)
sys.path.append(scriptsdir)

from scripts.mtg_forge import (
    adjust_stat,
    scale_stat,
    scale_mana_cost,
    parse_sed_replace,
    apply_single_replacement,
    apply_color_shift,
    apply_buff_nerf,
    apply_scale,
    print_detailed_card,
    validate_forged_card
)
import cardlib
import utils

class TestMtgForgeGaps(unittest.TestCase):

    def test_adjust_stat_edge_cases(self):
        self.assertIsNone(adjust_stat(None, 2))
        self.assertEqual(adjust_stat("*", 1), "*")

        class BadObj:
            def __str__(self):
                raise RuntimeError("Format error")

        bad_obj = BadObj()
        self.assertEqual(adjust_stat(bad_obj, 1), bad_obj)

    def test_scale_stat_edge_cases(self):
        self.assertIsNone(scale_stat(None, 2.0))
        self.assertEqual(scale_stat("*", 2.0), "*")
        # Scaling down with multiply=False
        self.assertEqual(scale_stat("4", 2.0, multiply=False), "2")
        self.assertEqual(scale_stat("0", 2.0, multiply=False), "1")

        class BadObj:
            def __str__(self):
                raise RuntimeError("Format error")

        bad_obj = BadObj()
        self.assertEqual(scale_stat(bad_obj, 2.0), bad_obj)

    def test_scale_mana_cost_edge_cases(self):
        self.assertIsNone(scale_mana_cost(None, 2.0))
        self.assertEqual(scale_mana_cost("", 2.0), "")
        self.assertEqual(scale_mana_cost("{4}{G}", 2.0, multiply=False), "{2}{G}")

    def test_parse_sed_replace_flags_and_escapes(self):
        is_regex, pattern, replacement, flags = parse_sed_replace("s/hello/world/msi")
        self.assertTrue(is_regex)
        self.assertEqual(pattern, "hello")
        self.assertEqual(replacement, "world")
        import re
        self.assertTrue(flags & re.IGNORECASE)
        self.assertTrue(flags & re.MULTILINE)
        self.assertTrue(flags & re.DOTALL)

    def test_apply_single_replacement_missing_type_line(self):
        card_dict = {
            'name': 'Grizzly Bears',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'text': 'Vanilla.'
        }
        res = apply_single_replacement(card_dict, True, 'Bear', 'Wolf', 0)
        self.assertEqual(res['type'], 'Legendary Creature — Wolf')
        self.assertEqual(res['subtypes'], ['Wolf'])

    def test_apply_single_replacement_bside_recursion(self):
        card_dict = {
            'name': 'Front',
            'type': 'Creature - Bear',
            'bside': {
                'name': 'Back Bear',
                'type': 'Creature - Bear'
            }
        }
        res = apply_single_replacement(card_dict, False, 'Bear', 'Wolf', 0)
        self.assertEqual(res['name'], 'Front')
        self.assertEqual(res['bside']['name'], 'Back Wolf')
        self.assertEqual(res['bside']['type'], 'Creature - Wolf')

    def test_apply_color_shift_color_identity_fallback_and_bside(self):
        card_dict = {
            'name': 'Mystery Land',
            'colorIdentity': ['G'],
            'bside': {
                'name': 'Mystery Back',
                'colorIdentity': ['G']
            }
        }
        res = apply_color_shift(card_dict, 'R')
        self.assertEqual(res['colorIdentity'], ['R'])
        self.assertEqual(res['bside']['colorIdentity'], ['R'])

    def test_apply_color_shift_no_orig_colors_or_invalid_target(self):
        card_dict = {'name': 'Colorless Artifact'}
        self.assertEqual(apply_color_shift(card_dict, 'R'), card_dict)

        card_dict2 = {'name': 'Green Bear', 'colors': ['G']}
        self.assertEqual(apply_color_shift(card_dict2, 'XYZ'), card_dict2)

    def test_apply_buff_nerf_single_pt_and_bside(self):
        card_dict = {
            'name': 'Stat Card',
            'pt': '3',
            'bside': {
                'name': 'Stat Back',
                'pt': '1'
            }
        }
        res = apply_buff_nerf(card_dict, 2)
        self.assertEqual(res['pt'], '5')
        self.assertEqual(res['bside']['pt'], '3')

    def test_apply_scale_single_pt_and_bside(self):
        card_dict = {
            'name': 'Giant Card',
            'pt': '4',
            'bside': {
                'name': 'Giant Back',
                'pt': '2'
            }
        }
        res = apply_scale(card_dict, 2.0, multiply=True)
        self.assertEqual(res['pt'], '8')
        self.assertEqual(res['bside']['pt'], '4')

    def test_print_detailed_card_multi_face_rulings_color_pie(self):
        card_dict = {
            'name': 'Day Face',
            'manaCost': '{W}',
            'type': 'Creature - Human',
            'power': '1',
            'toughness': '1',
            'text': 'Draw three cards.',  # Color pie violation for mono-white
            'setCode': 'TST',
            'number': '12',
            'rulings': [{'date': '2023-01-01', 'text': 'Example ruling.'}],
            'legalities': {'standard': 'legal'},
            'bside': {
                'name': 'Night Face',
                'type': 'Creature - Werewolf',
                'power': '3',
                'toughness': '3',
                'text': 'Trample.'
            }
        }
        c = cardlib.Card(card_dict)

        out_f = io.StringIO()
        print_detailed_card(c, use_color=True, output_f=out_f)
        output = out_f.getvalue()

        self.assertIn('Day Face', output)
        self.assertIn('Night Face', output)
        self.assertIn('RULINGS', output)
        self.assertIn('Example ruling', output)
        self.assertIn('COLOR PIE:', output)
        self.assertIn('LEGALITIES:', output)

    def test_validate_forged_card_color_pie_break(self):
        card_dict = {
            'name': 'White Counterspell',
            'manaCost': '{W}{W}',
            'type': 'Instant',
            'text': 'Counter target spell.'
        }
        c = cardlib.Card(card_dict)

        stderr_io = io.StringIO()
        with patch('sys.stderr', stderr_io):
            validate_forged_card(c, use_color=True)

        err_output = stderr_io.getvalue()
        self.assertIn('failed design validation', err_output)
        self.assertIn('color_pie', err_output)

if __name__ == '__main__':
    unittest.main()
