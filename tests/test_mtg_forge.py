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

class TestMtgForge(unittest.TestCase):

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_scratch(self, mock_stdout, mock_open):
        # Test creating a card from scratch
        test_args = [
            'mtg_forge.py',
            '--name', 'Jules',
            '--cost', '{U}{R}',
            '--type', 'Legendary Creature - Human Engineer',
            '--pt', '2/3',
            '--text', 'T: Draw a card.',
            '--rarity', 'Rare'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Jules')
        self.assertEqual(output['manaCost'], '{U}{R}')
        self.assertEqual(output['types'], ['Creature'])
        self.assertEqual(output['supertypes'], ['Legendary'])
        self.assertEqual(output['subtypes'], ['Human', 'Engineer'])
        self.assertEqual(output['power'], '2')
        self.assertEqual(output['toughness'], '3')
        self.assertEqual(output['rarity'], 'rare')
        self.assertIn('Draw a card', output['text'])

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_reforge(self, mock_stdout, mock_open):
        # Mock base card
        mock_card = MagicMock()
        mock_card.name = "Grizzly Bears"
        mock_card.to_dict.return_value = {
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        }
        mock_open.return_value = [mock_card]

        test_args = [
            'mtg_forge.py',
            '--base', 'Grizzly Bears',
            '--pt', '3/3',
            '--name', 'Super Bears'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Super Bears')
        self.assertEqual(output['power'], '3')
        self.assertEqual(output['toughness'], '3')
        self.assertEqual(output['manaCost'], '{1}{G}')
        self.assertEqual(output['subtypes'], ['Bear'])

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_color_shift(self, mock_stdout, mock_open):
        # Mock base card
        mock_card = MagicMock()
        mock_card.name = "Green Forest Bear"
        mock_card.to_dict.side_effect = lambda: {
            'name': 'Green Forest Bear',
            'manaCost': '{1}{G}',
            'type': 'Creature - Forest Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'text': 'Forestwalk (unblockable if defending controls a Forest).',
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        }
        mock_open.return_value = [mock_card]

        # Shift to White (W)
        test_args = [
            'mtg_forge.py',
            '--base', 'Green Forest Bear',
            '--color-shift', 'W'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'White Plains Bear')
        self.assertEqual(output['manaCost'], '{1}{W}')
        self.assertIn('Plains', output['subtypes'])
        self.assertIn('Plains', output['text'])

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_color_shift_multicolor(self, mock_stdout, mock_open):
        # Mock base card
        mock_card = MagicMock()
        mock_card.name = "Green Bear"
        mock_card.to_dict.side_effect = lambda: {
            'name': 'Green Bear',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'text': 'Add {G}.',
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        }
        mock_open.return_value = [mock_card]

        # Shift to White-Blue (WU)
        test_args = [
            'mtg_forge.py',
            '--base', 'Green Bear',
            '--color-shift', 'WU'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['manaCost'], '{1}{W}{U}')
        self.assertEqual(output['name'], 'White and Blue Bear')
        self.assertIn('{W}{U}', output['text'])

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_buff_nerf(self, mock_stdout, mock_open):
        # Mock base card
        mock_card = MagicMock()
        mock_card.name = "Grizzly Bears"
        mock_card.to_dict.side_effect = lambda: {
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'loyalty': '3',
            'rarity': 'common'
        }
        mock_open.return_value = [mock_card]

        # Test Buff
        test_args = [
            'mtg_forge.py',
            '--base', 'Grizzly Bears',
            '--buff'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['power'], '3')
        self.assertEqual(output['toughness'], '3')
        self.assertEqual(output['loyalty'], '4')

        # Test Nerf
        mock_stdout.seek(0)
        mock_stdout.truncate(0)
        test_args = [
            'mtg_forge.py',
            '--base', 'Grizzly Bears',
            '--nerf'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['power'], '1')
        self.assertEqual(output['toughness'], '1')
        self.assertEqual(output['loyalty'], '2')

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_scale(self, mock_stdout, mock_open):
        # Mock base card
        mock_card = MagicMock()
        mock_card.name = "Grizzly Bears"
        mock_card.to_dict.side_effect = lambda: {
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        }
        mock_open.return_value = [mock_card]

        # Test Scale Up
        test_args = [
            'mtg_forge.py',
            '--base', 'Grizzly Bears',
            '--scale-up'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['power'], '3')
        self.assertEqual(output['toughness'], '3')
        self.assertEqual(output['manaCost'], '{2}{G}')

        # Test Scale Down
        mock_stdout.seek(0)
        mock_stdout.truncate(0)
        test_args = [
            'mtg_forge.py',
            '--base', 'Grizzly Bears',
            '--scale-down'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['power'], '1')
        self.assertEqual(output['toughness'], '1')
        self.assertEqual(output['manaCost'], '{G}')

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_encoded(self, mock_stdout):
        test_args = [
            'mtg_forge.py',
            '--name', 'Test',
            '--type', 'Instant',
            '--encoded'
        ]

        with patch('sys.argv', test_args):
            main()

        output = mock_stdout.getvalue()
        # Check standard encoded format: types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name
        # For Instant, no-name: |5instant|4|6|7|8|9|3|0|1test|
        self.assertIn('|5instant|', output)
        self.assertIn('|1test|', output)

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_summary(self, mock_stdout):
        test_args = [
            'mtg_forge.py',
            '--name', 'Test',
            '--type', 'Creature',
            '--pt', '1/1',
            '--summary'
        ]

        with patch('sys.argv', test_args):
            main()

        output = mock_stdout.getvalue()
        self.assertIn('Test', output)
        self.assertIn('Creature', output)
        self.assertIn('(1/1)', output)

if __name__ == '__main__':
    unittest.main()
