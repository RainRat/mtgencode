import unittest
from unittest.mock import patch
import io
import sys
import os

# Add lib and scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import scripts.mtg_analyze as mtg_analyze
import cardlib

class TestMtgMana(unittest.TestCase):

    def test_get_produced_colors_intrinsic(self):
        # Basic Forest
        card_forest = cardlib.Card({
            'name': 'Forest',
            'types': ['Land'],
            'subtypes': ['Forest']
        })
        self.assertEqual(card_forest.produced_colors, {'G'})

        # Dual Land
        card_volcanic = cardlib.Card({
            'name': 'Volcanic Island',
            'types': ['Land'],
            'subtypes': ['Island', 'Mountain']
        })
        self.assertEqual(card_volcanic.produced_colors, {'U', 'R'})

    def test_get_produced_colors_text(self):
        # Mana Creature
        card_elf = cardlib.Card({
            'name': 'Llanowar Elves',
            'types': ['Creature'],
            'text': '{T}: Add {G}.'
        })
        self.assertEqual(card_elf.produced_colors, {'G'})

        # Mana Artifact
        card_sol_ring = cardlib.Card({
            'name': 'Sol Ring',
            'types': ['Artifact'],
            'text': '{T}: Add {C}{C}.'
        })
        self.assertEqual(card_sol_ring.produced_colors, {'C'})

        # "Any Color"
        card_lotus = cardlib.Card({
            'name': 'Black Lotus',
            'types': ['Artifact'],
            'text': '{T}, Sacrifice @: Add three mana of any color.'
        })
        self.assertEqual(card_lotus.produced_colors, {'Any'})

    def test_get_mana_category(self):
        # Creature
        c = cardlib.Card({'name': 'Elf', 'types': ['Creature']})
        self.assertEqual(mtg_analyze.get_mana_category(c), 'Creature')

        # Artifact
        c = cardlib.Card({'name': 'Ring', 'types': ['Artifact']})
        self.assertEqual(mtg_analyze.get_mana_category(c), 'Artifact')

        # Land
        c = cardlib.Card({'name': 'Forest', 'types': ['Land']})
        self.assertEqual(mtg_analyze.get_mana_category(c), 'Land')

        # Spell
        c = cardlib.Card({'name': 'Ritual', 'types': ['Instant']})
        self.assertEqual(mtg_analyze.get_mana_category(c), 'Spell')

    def test_analyze_dataset(self):
        cards = [
            cardlib.Card({'name': 'Forest', 'types': ['Land'], 'subtypes': ['Forest']}),
            cardlib.Card({'name': 'Island', 'types': ['Land'], 'subtypes': ['Island']}),
            cardlib.Card({'name': 'Elf', 'types': ['Creature'], 'text': '{T}: Add {G}.'})
        ]
        stats = mtg_analyze.analyze_dataset(cards)

        self.assertEqual(stats['total_cards'], 3)
        self.assertEqual(stats['producer_count'], 3)
        self.assertEqual(stats['categories']['Land'], 2)
        self.assertEqual(stats['categories']['Creature'], 1)
        self.assertEqual(stats['colors']['G'], 2)
        self.assertEqual(stats['colors']['U'], 1)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_basic(self, mock_stdout, mock_open):
        # Mock jdecode to return some cards
        mock_open.return_value = [
            cardlib.Card({'name': 'Forest', 'types': ['Land'], 'subtypes': ['Forest']})
        ]

        # Run main with a dummy file
        with patch('sys.argv', ['mtg_analyze.py', 'mana', 'dummy.json', '--no-color']):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        self.assertIn("MANA PRODUCTION ANALYSIS", output)
        self.assertIn("Produced Colors", output)
        self.assertIn("G", output)

if __name__ == '__main__':
    unittest.main()
