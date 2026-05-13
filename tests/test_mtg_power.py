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

import scripts.mtg_power as mtg_power
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

    @patch('scripts.mtg_power.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('os.path.exists')
    def test_main_table(self, mock_exists, mock_stdout, mock_open):
        mock_open.return_value = self.sample_cards
        mock_exists.return_value = True

        with patch('sys.argv', ['mtg_power.py', 'dummy.json']):
            mtg_power.main()

        output = mock_stdout.getvalue()
        self.assertIn('POWER BALANCE ANALYSIS', output)
        self.assertIn('Bears', output)
        self.assertIn('Bird', output)
        self.assertIn('Broken Beast', output)
        self.assertNotIn('Divination', output) # Non-creatures excluded
        self.assertIn('Average Efficiency by Rarity', output)

    @patch('scripts.mtg_power.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('os.path.exists')
    def test_main_json(self, mock_exists, mock_stdout, mock_open):
        mock_open.return_value = self.sample_cards
        mock_exists.return_value = True

        with patch('sys.argv', ['mtg_power.py', 'dummy.json', '--json']):
            mtg_power.main()

        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertEqual(data['total_creatures'], 3)
        self.assertIn('top_outliers', data)
        self.assertEqual(data['top_outliers'][0]['name'], 'Broken Beast')

    @patch('scripts.mtg_power.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('os.path.exists')
    def test_main_no_creatures(self, mock_exists, mock_stdout, mock_open):
        mock_open.return_value = [self.sample_cards[3]] # Only the sorcery
        mock_exists.return_value = True

        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            with patch('sys.argv', ['mtg_power.py', 'dummy.json']):
                mtg_power.main()
            self.assertIn('No creatures found', mock_stderr.getvalue())

if __name__ == '__main__':
    unittest.main()
