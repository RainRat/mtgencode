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

class TestMtgDeckgenManabase(unittest.TestCase):

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_commander_proportional_manabase(self, mock_stderr, mock_stdout, mock_open):
        """
        Verify that in Commander format, land allocation is proportional to the selected spell pips.
        """
        commander = cardlib.Card({
            'name': 'Uthros, the Glimmering',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'colorIdentity': ['R', 'G'],
            'rarity': 'rare',
            'text': ''
        })

        # All spells only cost Green ({G})
        green_spell = cardlib.Card({
            'name': 'Grizzly Bears',
            'types': ['Creature'],
            'manaCost': '{1}{G}',
            'rarity': 'common',
            'text': ''
        })

        # Mock the cards loaded from file
        mock_open.return_value = [commander, green_spell]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'commander', '--commander', 'Uthros, the Glimmering', '--creatures', '2', '--spells', '0', '--lands', '10']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        # Since green_spell has 1 green pip and commander has {R}{G}, there are more green pips (2) than red pips (1).
        # Green (Forest) should have more lands than Red (Mountain), but both should be present.
        lines = output.strip().split('\n')
        lands = {}
        for line in lines:
            parts = line.split(' ', 1)
            if len(parts) == 2 and parts[1].strip() in ['Forest', 'Mountain', 'Plains', 'Island', 'Swamp', 'Wastes']:
                lands[parts[1].strip()] = int(parts[0])

        self.assertIn('Forest', lands)
        self.assertIn('Mountain', lands)
        self.assertGreater(lands['Forest'], lands['Mountain'])
        self.assertEqual(sum(lands.values()), 10)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_standard_proportional_manabase(self, mock_stderr, mock_stdout, mock_open):
        """
        Verify that in Standard format, land allocation is proportional to spell pips.
        """
        # Blue spell
        blue_spell = cardlib.Card({
            'name': 'Counterspell',
            'types': ['Instant'],
            'manaCost': '{U}{U}',
            'rarity': 'common',
            'text': ''
        })

        # White spell
        white_spell = cardlib.Card({
            'name': 'Savannah Lions',
            'types': ['Creature'],
            'manaCost': '{W}',
            'rarity': 'common',
            'text': ''
        })

        # Mock the cards loaded from file
        mock_open.return_value = [blue_spell, white_spell]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'standard', '--creatures', '4', '--spells', '4', '--lands', '10']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        # Since counterspell has 2 blue pips and Savannah Lions has 1 white pip,
        # there should be significantly more Islands than Plains, but both should be present.
        lines = output.strip().split('\n')
        lands = {}
        for line in lines:
            parts = line.split(' ', 1)
            if len(parts) == 2 and parts[1].strip() in ['Forest', 'Mountain', 'Plains', 'Island', 'Swamp', 'Wastes']:
                lands[parts[1].strip()] = int(parts[0])

        self.assertIn('Island', lands)
        self.assertIn('Plains', lands)
        self.assertGreater(lands['Island'], lands['Plains'])
        self.assertEqual(sum(lands.values()), 10)

if __name__ == '__main__':
    unittest.main()
