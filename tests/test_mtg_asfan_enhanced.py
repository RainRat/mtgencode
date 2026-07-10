import unittest
from unittest.mock import patch
import io
import sys
import os

# Add lib and scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import scripts.mtg_analyze as mtg_analyze
import cardlib

class TestMtgAsfanEnhanced(unittest.TestCase):

    def setUp(self):
        # Create a sample dataset with mechanics and multicolored cards
        self.cards = [
            cardlib.Card({
                'name': 'Gold Flyer',
                'rarity': 'common',
                'manaCost': '{W}{U}',
                'types': ['Creature'],
                'text': 'Flying'
            }),
            cardlib.Card({
                'name': 'Monocolor',
                'rarity': 'common',
                'manaCost': '{G}',
                'types': ['Creature'],
                'text': 'Trample'
            })
        ]

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_enhanced_output(self, mock_stdout, mock_open):
        mock_open.return_value = self.cards

        with patch('sys.argv', ['mtg_analyze.py', 'asfan', 'dummy.json', '--no-color']):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        self.assertIn("AS-FAN ANALYSIS", output)
        self.assertIn("Color Distribution", output)
        self.assertIn("Type Distribution", output)

        # These are the missing sections we want to add
        self.assertIn("Mechanical Distribution", output)
        self.assertIn("Multicolored As-Fan", output)

        # Verify content within those sections
        self.assertIn("Flying", output)
        self.assertIn("Trample", output)

if __name__ == '__main__':
    unittest.main()
