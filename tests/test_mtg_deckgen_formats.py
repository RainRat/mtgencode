import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import io

# Add lib and scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import mtg_deckgen
import cardlib

class TestMtgDeckgenFormats(unittest.TestCase):

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_pauper(self, mock_stderr, mock_stdout, mock_open):
        """Test Pauper format: 60-card deck, only common cards selected."""
        common_creature = cardlib.Card({
            'name': 'Common Soldier',
            'types': ['Creature'],
            'manaCost': '{W}',
            'rarity': 'common',
            'text': ''
        })

        common_spell = cardlib.Card({
            'name': 'Common Shock',
            'types': ['Instant'],
            'manaCost': '{R}',
            'rarity': 'common',
            'text': ''
        })

        rare_creature = cardlib.Card({
            'name': 'Rare Dragon',
            'types': ['Creature'],
            'manaCost': '{3}{R}{R}',
            'rarity': 'rare',
            'text': ''
        })

        mock_open.return_value = [common_creature, common_spell, rare_creature]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'pauper']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        # Should contain common cards
        self.assertIn("Common Soldier", output)
        self.assertIn("Common Shock", output)
        # Should NOT contain rare cards!
        self.assertNotIn("Rare Dragon", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_limited(self, mock_stderr, mock_stdout, mock_open):
        """Test Limited format: 40-card deck size (approx 17 lands, 15 creatures, 8 spells)."""
        creature = cardlib.Card({
            'name': 'Limited Bear',
            'types': ['Creature'],
            'manaCost': '{1}{G}',
            'rarity': 'common',
            'text': ''
        })

        spell = cardlib.Card({
            'name': 'Limited Growth',
            'types': ['Instant'],
            'manaCost': '{G}',
            'rarity': 'common',
            'text': ''
        })

        mock_open.return_value = [creature, spell]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'limited', '--seed', '42']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Limited Bear", output)
        self.assertIn("Limited Growth", output)
        # Check that we have Forest or other basics
        self.assertIn("Forest", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_brawl_creature_commander(self, mock_stderr, mock_stdout, mock_open):
        """Test Brawl format with a legendary creature commander."""
        commander = cardlib.Card({
            'name': 'Brawl Galia',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })

        common_spell = cardlib.Card({
            'name': 'Brawl Goblin',
            'types': ['Creature'],
            'manaCost': '{1}{R}',
            'rarity': 'common',
            'text': ''
        })

        mock_open.return_value = [commander, common_spell]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'brawl', '--commander', 'Brawl Galia', '--seed', '1']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Brawl Galia", output)
        self.assertIn("Brawl Goblin", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_brawl_planeswalker_commander(self, mock_stderr, mock_stdout, mock_open):
        """Test Brawl format with a planeswalker commander."""
        commander = cardlib.Card({
            'name': 'Chandra Brawl',
            'supertypes': ['Legendary'],
            'types': ['Planeswalker'],
            'manaCost': '{1}{R}{R}',
            'rarity': 'mythic',
            'text': ''
        })

        common_spell = cardlib.Card({
            'name': 'Chandra Spell',
            'types': ['Instant'],
            'manaCost': '{R}',
            'rarity': 'common',
            'text': ''
        })

        mock_open.return_value = [commander, common_spell]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'brawl', '--commander', 'Chandra Brawl', '--seed', '1']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Chandra Brawl", output)
        self.assertIn("Chandra Spell", output)

if __name__ == '__main__':
    unittest.main()
