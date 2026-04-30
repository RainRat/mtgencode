import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os

# Add lib and scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import mtg_mana
import cardlib
import utils

class TestMtgMana(unittest.TestCase):

    def test_get_produced_colors_intrinsic(self):
        # Basic Forest
        card_forest = cardlib.Card({
            'name': 'Forest',
            'types': ['Land'],
            'subtypes': ['Forest']
        })
        self.assertEqual(mtg_mana.get_produced_colors(card_forest), {'G'})

        # Dual Land
        card_volcanic = cardlib.Card({
            'name': 'Volcanic Island',
            'types': ['Land'],
            'subtypes': ['Island', 'Mountain']
        })
        self.assertEqual(mtg_mana.get_produced_colors(card_volcanic), {'U', 'R'})

    def test_get_produced_colors_text(self):
        # Mana Dork
        card_elf = cardlib.Card({
            'name': 'Llanowar Elves',
            'types': ['Creature'],
            'text': '{T}: Add {G}.'
        })
        self.assertEqual(mtg_mana.get_produced_colors(card_elf), {'G'})

        # Mana Rock
        card_sol_ring = cardlib.Card({
            'name': 'Sol Ring',
            'types': ['Artifact'],
            'text': '{T}: Add {C}{C}.'
        })
        self.assertEqual(mtg_mana.get_produced_colors(card_sol_ring), {'C'})

        # "Any Color"
        card_lotus = cardlib.Card({
            'name': 'Black Lotus',
            'types': ['Artifact'],
            'text': '{T}, Sacrifice @: Add three mana of any color.'
        })
        self.assertEqual(mtg_mana.get_produced_colors(card_lotus), {'Any'})

    def test_get_category(self):
        # Dork
        c = cardlib.Card({'name': 'Elf', 'types': ['Creature']})
        self.assertEqual(mtg_mana.get_category(c), 'Dork')

        # Rock
        c = cardlib.Card({'name': 'Ring', 'types': ['Artifact']})
        self.assertEqual(mtg_mana.get_category(c), 'Rock')

        # Land
        c = cardlib.Card({'name': 'Forest', 'types': ['Land']})
        self.assertEqual(mtg_mana.get_category(c), 'Land')

        # Ritual
        c = cardlib.Card({'name': 'Ritual', 'types': ['Instant']})
        self.assertEqual(mtg_mana.get_category(c), 'Ritual')

    def test_analyze_dataset(self):
        cards = [
            cardlib.Card({'name': 'Forest', 'types': ['Land'], 'subtypes': ['Forest']}),
            cardlib.Card({'name': 'Island', 'types': ['Land'], 'subtypes': ['Island']}),
            cardlib.Card({'name': 'Elf', 'types': ['Creature'], 'text': '{T}: Add {G}.'})
        ]
        stats, producers = mtg_mana.analyze_dataset(cards)

        self.assertEqual(stats['total_cards'], 3)
        self.assertEqual(stats['producer_count'], 3)
        self.assertEqual(stats['categories']['Land'], 2)
        self.assertEqual(stats['categories']['Dork'], 1)
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
        with patch('sys.argv', ['mtg_mana.py', 'dummy.json', '--no-color']):
            mtg_mana.main()

        output = mock_stdout.getvalue()
        self.assertIn("MANA PRODUCTION ANALYSIS", output)
        self.assertIn("Land", output)
        self.assertIn("G", output)

if __name__ == '__main__':
    unittest.main()
