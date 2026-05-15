import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import io

# Add project root and scripts directory to path
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/..')
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../scripts')

from scripts.mtg_subtypes import main, analyze_subtypes, get_color_identity_group
import cardlib

class TestMtgSubtypes(unittest.TestCase):

    def setUp(self):
        # Create some mock cards
        self.cards = []

        # White Weenie (Humans)
        for i in range(5):
            c = MagicMock(spec=cardlib.Card)
            c.name = f"White Human {i}"
            c.color_identity = "W"
            c.subtypes = ["human", "soldier"]
            self.cards.append(c)

        # Blue Fliers (Birds)
        for i in range(3):
            c = MagicMock(spec=cardlib.Card)
            c.name = f"Blue Bird {i}"
            c.color_identity = "U"
            c.subtypes = ["bird"]
            self.cards.append(c)

        # Red Goblins
        for i in range(4):
            c = MagicMock(spec=cardlib.Card)
            c.name = f"Red Goblin {i}"
            c.color_identity = "R"
            c.subtypes = ["goblin"]
            self.cards.append(c)

        # Multicolored Dragon
        c = MagicMock(spec=cardlib.Card)
        c.name = "Gold Dragon"
        c.color_identity = "UR"
        c.subtypes = ["dragon"]
        self.cards.append(c)

    def test_get_color_identity_group(self):
        c = MagicMock(spec=cardlib.Card)

        c.color_identity = ""
        self.assertEqual(get_color_identity_group(c), 'A')

        c.color_identity = "W"
        self.assertEqual(get_color_identity_group(c), 'W')

        c.color_identity = "UB"
        self.assertEqual(get_color_identity_group(c), 'M')

    def test_analyze_subtypes(self):
        stats = analyze_subtypes(self.cards)

        self.assertEqual(stats['total_cards'], 13)
        self.assertEqual(stats['global_freq']['Human'], 5)
        self.assertEqual(stats['global_freq']['Soldier'], 5)
        self.assertEqual(stats['global_freq']['Bird'], 3)
        self.assertEqual(stats['global_freq']['Goblin'], 4)
        self.assertEqual(stats['global_freq']['Dragon'], 1)

        # Check color stats
        self.assertIn('W', stats['color_stats'])
        self.assertEqual(stats['color_stats']['W']['card_count'], 5)
        self.assertIn('Human', stats['color_stats']['W']['top_signature'])

        self.assertIn('U', stats['color_stats'])
        self.assertIn('Bird', stats['color_stats']['U']['top_signature'])

        self.assertIn('M', stats['color_stats'])
        self.assertIn('Dragon', stats['color_stats']['M']['top_signature'])

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_table(self, mock_stdout, mock_open):
        mock_open.return_value = self.cards

        with patch('sys.argv', ['mtg_subtypes.py', 'dummy.json', '--no-color']):
            main()

        output = mock_stdout.getvalue()
        self.assertIn("SUBTYPE DISTRIBUTION ANALYSIS", output)
        self.assertIn("Top Subtypes Overall", output)
        self.assertIn("Human", output)
        self.assertIn("Soldier", output)
        self.assertIn("Bird", output)
        self.assertIn("Goblin", output)
        self.assertIn("Signature Subtypes", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_json(self, mock_stdout, mock_open):
        mock_open.return_value = self.cards

        with patch('sys.argv', ['mtg_subtypes.py', 'dummy.json', '--json']):
            main()

        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertEqual(data['total_cards'], 13)
        self.assertEqual(data['global_freq']['Human'], 5)
        self.assertIn('color_stats', data)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_csv(self, mock_stdout, mock_open):
        mock_open.return_value = self.cards

        with patch('sys.argv', ['mtg_subtypes.py', 'dummy.json', '--csv']):
            main()

        output = mock_stdout.getvalue()
        self.assertIn("Subtype,Count,Percent,Group,Distinctiveness", output)
        self.assertIn("Human,5,27.78%,Global,1.0000", output) # 5 / 18 instances = 27.78%

if __name__ == '__main__':
    unittest.main()
