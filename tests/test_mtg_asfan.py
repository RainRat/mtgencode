import unittest
from unittest.mock import patch
import io
import sys
import os
import json

# Add lib and scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import mtg_asfan
import cardlib

class TestMtgAsfan(unittest.TestCase):

    def setUp(self):
        # Create a small sample dataset with specific rarities to test As-Fan calculation
        self.cards = [
            # 1 Common White Creature
            cardlib.Card({'name': 'Soldier', 'rarity': 'common', 'manaCost': '{W}', 'types': ['Creature']}),
            # 1 Common Blue Spell
            cardlib.Card({'name': 'Draw', 'rarity': 'common', 'manaCost': '{U}', 'types': ['Instant']}),
            # 1 Uncommon Red Creature
            cardlib.Card({'name': 'Goblin', 'rarity': 'uncommon', 'manaCost': '{R}', 'types': ['Creature']}),
            # 1 Rare Green Creature
            cardlib.Card({'name': 'Hydra', 'rarity': 'rare', 'manaCost': '{G}', 'types': ['Creature']}),
            # 1 Basic Forest
            cardlib.Card({'name': 'Forest', 'rarity': 'basic land', 'types': ['Land'], 'subtypes': ['Forest']})
        ]

    def test_calculate_asfan_basic(self):
        results = mtg_asfan.calculate_asfan(self.cards)

        # In this dataset:
        # Common pool (2 cards): 50% White, 50% Blue
        # As-Fan Colors: White = 0.5 * 10 = 5.0, Blue = 0.5 * 10 = 5.0
        self.assertAlmostEqual(results['colors']['W'], 5.0)
        self.assertAlmostEqual(results['colors']['U'], 5.0)

        # Uncommon pool (1 card): 100% Red
        # As-Fan Colors: Red = 1.0 * 3 = 3.0
        self.assertAlmostEqual(results['colors']['R'], 3.0)

        # Rare pool (1 card): 100% Green
        # As-Fan Colors: Green = 1.0 * 1 = 1.0
        self.assertAlmostEqual(results['colors']['G'], 1.0)

        # Land pool (1 card): 100% Green (from produced colors, but the counter is for casting cost)
        # In the current implementation, cards with no colors in cost return ['C']
        # The land slot is 1.0, so C As-Fan should be 1.0
        self.assertAlmostEqual(results['colors'].get('C', 0), 1.0)

    def test_calculate_asfan_types(self):
        results = mtg_asfan.calculate_asfan(self.cards)

        # Creature count in Common: 1/2 = 50% -> As-Fan = 0.5 * 10 = 5.0
        # Creature count in Uncommon: 1/1 = 100% -> As-Fan = 1.0 * 3 = 3.0
        # Creature count in Rare: 1/1 = 100% -> As-Fan = 1.0 * 1 = 1.0
        # Total Creature As-Fan = 5.0 + 3.0 + 1.0 = 9.0
        self.assertAlmostEqual(results['types']['Creature'], 9.0)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_table(self, mock_stdout, mock_open):
        mock_open.return_value = self.cards

        with patch('sys.argv', ['mtg_asfan.py', 'dummy.json', '--no-color']):
            mtg_asfan.main()

        output = mock_stdout.getvalue()
        self.assertIn("AS-FAN ANALYSIS", output)
        self.assertIn("Color Distribution", output)
        self.assertIn("Type Distribution", output)
        self.assertIn("Creature", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_json(self, mock_stdout, mock_open):
        mock_open.return_value = self.cards

        with patch('sys.argv', ['mtg_asfan.py', 'dummy.json', '--json']):
            mtg_asfan.main()

        output = json.loads(mock_stdout.getvalue())
        self.assertIn("primary", output)
        self.assertIn("colors", output["primary"])
        self.assertIn("types", output["primary"])

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_compare(self, mock_stdout, mock_open):
        # First call returns primary, second returns comparison
        mock_open.side_effect = [self.cards, self.cards]

        with patch('sys.argv', ['mtg_asfan.py', 'file1.json', '--compare', 'file2.json', '--no-color']):
            mtg_asfan.main()

        output = mock_stdout.getvalue()
        self.assertIn("AS-FAN ANALYSIS (COMPARISON)", output)
        self.assertIn("Delta", output)

    @patch('sys.stdin.isatty')
    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file')
    def test_smart_positional_args(self, mock_open, mock_exists, mock_isatty):
        # Case: "Grizzly Bears" -> Treat as query
        # We want to simulate that the default dataset DOES exist so it gets picked up

        def exists_side_effect(path):
            if 'AllPrintings.json' in path:
                return True
            if path == 'Grizzly Bears':
                return False
            return False

        mock_exists.side_effect = exists_side_effect
        mock_isatty.return_value = True
        mock_open.return_value = self.cards

        with patch('sys.argv', ['mtg_asfan.py', 'Grizzly Bears']):
            mtg_asfan.main()

        # Should have called open_file with some path that includes AllPrintings.json and grep=['Grizzly Bears']
        # We check the call args to verify
        self.assertTrue(mock_open.called)
        args, kwargs = mock_open.call_args
        self.assertIn('AllPrintings.json', args[0])
        self.assertEqual(kwargs['grep'], ['Grizzly Bears'])

if __name__ == '__main__':
    unittest.main()
