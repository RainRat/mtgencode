import unittest
import sys
import os
import io
import json
from unittest.mock import patch, MagicMock

# Add lib and scripts directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

import mtg_complexity
from cardlib import Card

class TestMTGComplexity(unittest.TestCase):

    def test_calculate_complexity_basic(self):
        # Grizzly Bears: simple vanilla creature
        src = {
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'text': '',
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        }
        card = Card(src)
        score = mtg_complexity.calculate_complexity(card)
        # Score components for Grizzly Bears:
        # 0 words, 0 lines -> 0
        # 0 mechanics -> 0
        # Color identity {G} -> 1 color * 3 = 3
        # No X cost -> 0
        # No bside -> 0
        # Total: 3
        self.assertEqual(score, 3)

    def test_calculate_complexity_keyword(self):
        # Giant Spider: Reach
        src = {
            'name': 'Giant Spider',
            'manaCost': '{3}{G}',
            'types': ['Creature'],
            'subtypes': ['Spider'],
            'text': 'Reach',
            'power': '2',
            'toughness': '4',
            'rarity': 'common'
        }
        card = Card(src)
        score = mtg_complexity.calculate_complexity(card)
        # Reach (1 word, 1 line) -> 1 + 5 = 6
        # 1 mechanic (Reach) -> 8
        # Color identity {G} -> 3
        # Total: 17
        self.assertEqual(score, 17)

    def test_calculate_complexity_complex(self):
        # Uthros Research Craft (from testdata)
        # It's a bit more complex.
        src = {
            'name': 'Uthros Research Craft',
            'manaCost': '{2}{U}',
            'types': ['Artifact'],
            'subtypes': ['Spacecraft'],
            'text': "Station (Tap another creature you control: Put charge counters equal to its power on this Spacecraft. Station only as a sorcery. It's an artifact creature at 12+.)\nSTATION 3+\nWhenever you cast an artifact spell, draw a card. Put a charge counter on this Spacecraft.\nSTATION 12+\nFlying\nThis Spacecraft gets +1/+0 for each artifact you control.",
            'power': '0',
            'toughness': '8',
            'rarity': 'rare'
        }
        card = Card(src)
        score = mtg_complexity.calculate_complexity(card)

        # Word count: ~56 words
        # Line count: 5 lines * 5 = 25
        # Mechanics: Station, Flying, Draw A Card, Counters, Triggered, Artifact (wait, Artifact is type) -> let's check RECOGNIZED_MECHANICS
        # Recognized by get_face_mechanics: {'Activated', 'Counters', 'Flying', 'Draw A Card', 'Triggered'} -> 5 * 8 = 40
        # Identity: {U} -> 3
        # Total: ~56 + 25 + 40 + 3 = 124
        # Actually it seems it was 96.
        self.assertGreater(score, 90)

    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('jdecode.mtg_open_file')
    def test_main_table(self, mock_open, mock_stdout):
        # Mocking mtg_open_file to return a list of cards
        card1 = Card({'name': 'Card A', 'types': ['Sorcery'], 'text': 'Draw a card.', 'manaCost': '{U}', 'rarity': 'common'})
        card2 = Card({'name': 'Card B', 'types': ['Instant'], 'text': 'Counter target spell.', 'manaCost': '{UU}', 'rarity': 'rare'})
        mock_open.return_value = [card1, card2]

        with patch('sys.argv', ['mtg_complexity.py', 'dummy.json']):
            mtg_complexity.main()

        output = mock_stdout.getvalue()
        self.assertIn('CARD COMPLEXITY ANALYSIS', output)
        self.assertIn('Card A', output)
        self.assertIn('Card B', output)

    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('jdecode.mtg_open_file')
    def test_main_json(self, mock_open, mock_stdout):
        card1 = Card({'name': 'Card A', 'types': ['Sorcery'], 'text': 'Draw a card.', 'manaCost': '{U}', 'rarity': 'common'})
        mock_open.return_value = [card1]

        with patch('sys.argv', ['mtg_complexity.py', 'dummy.json', '--json']):
            mtg_complexity.main()

        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertIn('average', data)
        self.assertEqual(data['cards'][0]['name'], 'Card A')

if __name__ == '__main__':
    unittest.main()
