import unittest
import io
import sys
import re
from lib.cardlib import Card, cap

class TestCardlibComprehensiveGaps(unittest.TestCase):
    def test_cap_helper_edge_cases(self):
        self.assertEqual(cap(""), "")
        # Standard sentence
        self.assertEqual(cap("draw a card"), "Draw a card")
        # Leading mana cost delimiter
        self.assertEqual(cap("{2U}, draw a card"), "{2U}, Draw a card")
        # Choice delimiter
        self.assertEqual(cap("[Choose one —] draw a card"), "[Choose one —] Draw a card")

    def test_set_loyalty_and_pt_verbose_warnings(self):
        card = Card({
            'name': 'Test Creature',
            'types': ['Creature'],
            'pt': '2/2',
            'rarity': 'common'
        }, verbose=True)

        stderr_backup = sys.stderr
        sys.stderr = io.StringIO()
        try:
            card._set_loyalty([(1, '3'), (2, '4')])
            err_output = sys.stderr.getvalue()
            self.assertIn("Multiple loyalty values for card 'test creature': 4", err_output)
            self.assertFalse(card.valid)

            sys.stderr = io.StringIO()
            # First value is invalid P/T format
            card._set_pt([(1, 'invalid_pt_format')])
            err_output = sys.stderr.getvalue()
            self.assertIn("Invalid P/T value for card 'test creature': invalid_pt_format", err_output)

            sys.stderr = io.StringIO()
            # Multiple P/T values
            card._set_pt([(1, '2/2'), (2, '3/3')])
            err_output = sys.stderr.getvalue()
            self.assertIn("Multiple P/T values for card 'test creature': 3/3", err_output)
        finally:
            sys.stderr = stderr_backup

    def test_add_printing_and_activate_printing(self):
        card = Card({
            'name': 'Test Land',
            'types': ['Land'],
            'rarity': 'common'
        })
        card.add_printing('LEA', 'common', '100', 'Limited Edition Alpha')
        # Duplicate addition ignored
        card.add_printing('LEA', 'common', '100', 'Limited Edition Alpha')
        card.add_printing('LEB', 'uncommon', '101', 'Limited Edition Beta')

        self.assertEqual(len(card.printings), 2)

        # Invalid activation
        self.assertFalse(card.activate_printing(''))
        self.assertFalse(card.activate_printing('NONEXISTENT'))

        # Valid activation
        self.assertTrue(card.activate_printing('LEB'))
        self.assertEqual(card.set_code, 'LEB')
        self.assertEqual(card.rarity, 'N')
        self.assertEqual(card.number, '101')

    def test_check_color_pie(self):
        # Card without mechanics/actions
        vanilla = Card({'name': 'Vanilla Artifact', 'types': ['Artifact'], 'rarity': 'common'})
        self.assertIsNone(vanilla.check_color_pie())

        # Card matching color pie
        black_deathtouch = Card({
            'name': 'Black Creature',
            'manaCost': '{B}',
            'types': ['Creature'],
            'pt': '1/1',
            'text': 'Deathtouch',
            'rarity': 'common'
        })
        self.assertTrue(black_deathtouch.check_color_pie())

        # Color pie break: Deathtouch on Blue
        blue_deathtouch = Card({
            'name': 'Blue Creature',
            'manaCost': '{U}',
            'types': ['Creature'],
            'pt': '1/1',
            'text': 'Deathtouch',
            'rarity': 'common'
        })
        pie_res = blue_deathtouch.check_color_pie()
        self.assertIsInstance(pie_res, str)
        self.assertIn("Color Pie Break: Deathtouch (Expected BGC)", pie_res)

    def test_encode_options(self):
        card = Card({
            'name': 'Test Spell',
            'manaCost': '{1}{U}',
            'types': ['Instant'],
            'text': 'Draw a card.\nDiscard a card.',
            'rarity': 'common'
        })

        # Test randomization and separators
        encoded = card.encode(randomize_fields=True, randomize_mana=True, randomize_lines=True, initial_sep=False, final_sep=False)
        self.assertIsInstance(encoded, str)

        # Verify initial_sep and final_sep flags omit leading/trailing separators
        encoded_no_seps = card.encode(initial_sep=False, final_sep=False)
        self.assertFalse(encoded_no_seps.startswith('|'))
        self.assertFalse(encoded_no_seps.endswith('|'))

    def test_to_mse_formatting(self):
        # Planeswalker with +X / -X loyalty costs
        pw = Card({
            'name': 'Test PW',
            'manaCost': '{3}{U}',
            'types': ['Planeswalker'],
            'loyalty': '4',
            'text': '+X: Draw X cards.\n-X: Target player mills X cards.',
            'rarity': 'rare'
        })
        mse_pw = pw.to_mse()
        self.assertIn('stylesheet: m15-planeswalker', mse_pw)
        self.assertIn('loyalty: 4', mse_pw)
        self.assertIn('loyalty cost 1: +X', mse_pw)

        # Battle card
        battle = Card({
            'name': 'Test Battle',
            'manaCost': '{2}{R}',
            'types': ['Battle'],
            'loyalty': '5',
            'text': 'When @ enters the battlefield, deals 3 damage to any target.',
            'rarity': 'uncommon'
        })
        mse_battle = battle.to_mse()
        self.assertIn('stylesheet: magic-m15-extra-improved', mse_battle)
        self.assertIn('defense: 5', mse_battle)

        # Split card (with B-side)
        split = Card({
            'name': 'Left Face',
            'manaCost': '{1}{R}',
            'types': ['Instant'],
            'text': 'Deals 2 damage to any target.',
            'rarity': 'common',
            'bside': {
                'name': 'Right Face',
                'manaCost': '{1}{G}',
                'types': ['Sorcery'],
                'text': 'Destroy target artifact.',
                'rarity': 'common'
            }
        })
        mse_split = split.to_mse()
        self.assertIn('stylesheet: new-split', mse_split)
        self.assertIn('name 2: Right Face', mse_split)

    def test_search_and_specific_search_methods(self):
        # Single-face planeswalker card
        card = Card({
            'name': 'Chandra, Flamecaller',
            'manaCost': '{4}{R}{R}',
            'supertypes': ['Legendary'],
            'types': ['Planeswalker'],
            'subtypes': ['Chandra'],
            'loyalty': '4',
            'text': '+1: Create two 3/1 red Elemental creature tokens.\n-X: @ deals X damage to each creature.',
            'rarity': 'mythic rare'
        })

        # Name search
        self.assertTrue(card.search_name(re.compile(r'Flamecaller', re.I)))
        self.assertFalse(card.search_name(re.compile(r'Jace', re.I)))

        # Types search
        self.assertTrue(card.search_types(re.compile(r'Planeswalker', re.I)))
        self.assertTrue(card.search_types(re.compile(r'Legendary', re.I)))

        # Text search
        self.assertTrue(card.search_text(re.compile(r'Elemental', re.I)))

        # Cost search
        self.assertTrue(card.search_cost(re.compile(r'\{4\}\{R\}\{R\}', re.I)))

        # P/T search (none for planeswalker)
        self.assertFalse(card.search_pt(re.compile(r'2/2', re.I)))

        # Loyalty search
        self.assertTrue(card.search_loyalty(re.compile(r'4', re.I)))

        # Rarity search
        self.assertTrue(card.search_rarity(re.compile(r'mythic', re.I)))

        # Mechanics search
        self.assertTrue(card.search_mechanics(re.compile(r'Token', re.I)))

        # Actions search
        self.assertTrue(card.search_actions(re.compile(r'Removal', re.I)))

        # Comprehensive search dispatcher
        self.assertTrue(card.search(re.compile(r'Flamecaller', re.I)))
        self.assertTrue(card.search(re.compile(r'Planeswalker', re.I)))
        self.assertTrue(card.search(re.compile(r'Token', re.I)))
        self.assertFalse(card.search(re.compile(r'NonexistentTerm', re.I)))

        # Multi-faced (b-side) card search
        split_card = Card({
            'name': 'Fire',
            'manaCost': '{1}{R}',
            'types': ['Instant'],
            'text': 'Fire deals 2 damage.',
            'rarity': 'uncommon',
            'bside': {
                'name': 'Ice',
                'manaCost': '{1}{U}',
                'types': ['Instant'],
                'text': 'Tap target permanent. Draw a card.',
                'rarity': 'uncommon'
            }
        })

        # Search b-side combined name and b-side fields
        self.assertTrue(split_card.search_name(re.compile(r'Fire // Ice', re.I)))
        self.assertTrue(split_card.search_name(re.compile(r'Ice', re.I)))
        self.assertTrue(split_card.search_text(re.compile(r'Draw a card', re.I)))
        self.assertTrue(split_card.search_cost(re.compile(r'\{1\}\{U\}', re.I)))
