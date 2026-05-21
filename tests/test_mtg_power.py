import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import io
import json

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))
sys.path.append(os.path.join(os.getcwd(), 'scripts'))

import scripts.mtg_analyze as mtg_analyze
import lib.cardlib as cardlib

class TestMtgPower(unittest.TestCase):
    def setUp(self):
        self.sample_cards = [
            cardlib.Card({
                'name': 'Bears',
                'manaCost': '{2}',
                'types': ['Creature'],
                'subtypes': ['Bear'],
                'power': '2',
                'toughness': '2',
                'rarity': 'common',
                'setCode': 'CUS'
            }),
            cardlib.Card({
                'name': 'Bird',
                'manaCost': '{U}',
                'types': ['Creature'],
                'subtypes': ['Bird'],
                'power': '1',
                'toughness': '1',
                'text': 'Flying',
                'rarity': 'common',
                'setCode': 'CUS'
            }),
            cardlib.Card({
                'name': 'Broken Beast',
                'manaCost': '{G}',
                'types': ['Creature'],
                'subtypes': ['Beast'],
                'power': '4',
                'toughness': '4',
                'rarity': 'rare',
                'setCode': 'CUS'
            }),
            cardlib.Card({
                'name': 'Divination',
                'manaCost': '{2}{U}',
                'types': ['Sorcery'],
                'text': 'Draw two cards.',
                'rarity': 'common',
                'setCode': 'CUS'
            })
        ]

    @patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('os.path.exists')
    def test_main_table(self, mock_exists, mock_stdout, mock_load):
        mock_load.return_value = self.sample_cards
        mock_exists.return_value = True

        with patch('sys.argv', ['mtg_analyze.py', 'power', 'dummy.json']):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        self.assertIn('POWER BALANCE ANALYSIS', output)
        self.assertIn('Bears', output)
        self.assertIn('Bird', output)
        self.assertIn('Broken Beast', output)
        # Note: Divination is a non-creature and excluded by power handler

    @patch('scripts.mtg_analyze.cli_utils.load_and_filter_cards')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('os.path.exists')
    def test_main_json(self, mock_exists, mock_stdout, mock_load):
        mock_load.return_value = self.sample_cards
        mock_exists.return_value = True

        with patch('sys.argv', ['mtg_analyze.py', 'power', 'dummy.json', '--json']):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertEqual(data['total'], 3)
        self.assertIn('top', data)
        self.assertEqual(data['top'][0]['name'], 'Broken Beast')

if __name__ == '__main__':
    unittest.main()
