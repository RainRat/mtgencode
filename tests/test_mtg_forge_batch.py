import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import io

# Add lib and scripts directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
scriptsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../scripts')
sys.path.append(libdir)
sys.path.append(scriptsdir)

from scripts.mtg_forge import main
import cardlib

class TestMtgForgeBatch(unittest.TestCase):

    def setUp(self):
        # Create concrete Card objects to avoid issues with mock attributes/to_dict
        self.cards = [
            cardlib.Card({
                'name': 'Grizzly Bears',
                'manaCost': '{1}{G}',
                'type': 'Creature - Bear',
                'types': ['Creature'],
                'subtypes': ['Bear'],
                'power': '2',
                'toughness': '2',
                'rarity': 'common',
                'setCode': 'M10'
            }),
            cardlib.Card({
                'name': 'Goblin Piker',
                'manaCost': '{1}{R}',
                'type': 'Creature - Goblin',
                'types': ['Creature'],
                'subtypes': ['Goblin'],
                'power': '2',
                'toughness': '1',
                'rarity': 'common',
                'setCode': 'M10'
            }),
            cardlib.Card({
                'name': 'Lightning Bolt',
                'manaCost': '{R}',
                'type': 'Instant',
                'types': ['Instant'],
                'text': 'Lightning Bolt deals 3 damage to any target.',
                'rarity': 'common',
                'setCode': 'M10'
            })
        ]

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_single_card_scratch_backward_compatibility(self, mock_stdout, mock_open):
        # Scratch single-card forge: --name "Unique Card"
        test_args = [
            'mtg_forge.py',
            '--name', 'Unique Card',
            '--cost', '{W}',
            '--type', 'Instant',
            '--text', 'Gain 3 life.'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Unique Card')
        self.assertEqual(output['manaCost'], '{W}')
        self.assertEqual(output['types'], ['Instant'])
        self.assertEqual(output['text'], 'Gain 3 life.')

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_single_card_reforge_backward_compatibility(self, mock_stdout, mock_open):
        # Reforge single card with --base
        mock_open.return_value = [self.cards[0]]

        test_args = [
            'mtg_forge.py',
            '--base', 'Grizzly Bears',
            '--pt', '3/3',
            '--name', 'Super Grizzly'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Super Grizzly')
        self.assertEqual(output['power'], '3')
        self.assertEqual(output['toughness'], '3')

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_batch_auto_detection(self, mock_stdout, mock_open):
        # Auto batch-mode when --base and --name are omitted
        mock_open.return_value = self.cards

        test_args = [
            'mtg_forge.py',
            '--buff', '1'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertTrue(isinstance(output, list))
        self.assertEqual(len(output), 3)
        # Verify first card (Grizzly Bears) got buffed (+1/+1) to 3/3
        self.assertEqual(output[0]['name'], 'Grizzly Bears')
        self.assertEqual(output[0]['power'], '3')
        self.assertEqual(output[0]['toughness'], '3')
        # Verify third card (Lightning Bolt) has no stats, unaffected by buff but still in list
        self.assertEqual(output[2]['name'], 'Lightning Bolt')
        self.assertNotIn('power', output[2])

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_batch_force_flag(self, mock_stdout, mock_open):
        # Force batch mode explicitly with --batch, even with field override like --rarity rare
        mock_open.return_value = self.cards

        test_args = [
            'mtg_forge.py',
            '--batch',
            '--rarity', 'rare'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertTrue(isinstance(output, list))
        self.assertEqual(len(output), 3)
        for card_dict in output:
            self.assertEqual(card_dict['rarity'], 'rare')

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_batch_transformations(self, mock_stdout, mock_open):
        # Batch color-shifting to blue
        mock_open.return_value = [self.cards[0], self.cards[1]]

        test_args = [
            'mtg_forge.py',
            '--batch',
            '--color-shift', 'blue'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(len(output), 2)
        self.assertEqual(output[0]['name'], 'Grizzly Bears')
        self.assertEqual(output[0]['manaCost'], '{1}{U}')
        self.assertEqual(output[0]['colorIdentity'], ['U'])

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_batch_encoded_output(self, mock_stdout, mock_open):
        mock_open.return_value = [self.cards[0], self.cards[1]]

        test_args = [
            'mtg_forge.py',
            '--batch',
            '--buff', '1',
            '--encoded'
        ]

        with patch('sys.argv', test_args):
            main()

        output = mock_stdout.getvalue()
        # Output should be two cards encoded, separated by cardsep (\n\n)
        self.assertIn('|5creature|', output)
        self.assertEqual(output.count('|5creature|'), 2)
        self.assertIn('8&^^^/&^^^', output) # grizzly bears buffed to 3/3

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_batch_summary_output(self, mock_stdout, mock_open):
        mock_open.return_value = [self.cards[0], self.cards[1]]

        test_args = [
            'mtg_forge.py',
            '--batch',
            '--buff', '1',
            '--summary'
        ]

        with patch('sys.argv', test_args):
            main()

        output = mock_stdout.getvalue()
        self.assertIn('Grizzly Bears', output)
        self.assertIn('Goblin Piker', output)
        self.assertIn('(3/3)', output) # grizzly bears buffed to 3/3
        self.assertIn('(3/2)', output) # goblin piker buffed to 3/2

if __name__ == '__main__':
    unittest.main()
