import sys
import os
import unittest
from unittest.mock import patch
import io

# Add scripts and lib to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))

import mtg_query
import cardlib
import utils

class TestMtgSubstitutes(unittest.TestCase):
    def setUp(self):
        # Create a small pool of mock cards
        # 1. Lightning Bolt (The Target)
        self.bolt = cardlib.Card({
            'name': 'Lightning Bolt',
            'manaCost': '{R}',
            'types': ['Instant'],
            'text': 'Lightning Bolt deals 3 damage to any target.',
            'rarity': 'common'
        })

        # 2. Shock (Good substitute: same type, same color, same CMC, same action)
        self.shock = cardlib.Card({
            'name': 'Shock',
            'manaCost': '{R}',
            'types': ['Instant'],
            'text': 'Shock deals 2 damage to any target.',
            'rarity': 'common'
        })

        # 3. Play with Fire (Good substitute)
        self.pwf = cardlib.Card({
            'name': 'Play with Fire',
            'manaCost': '{R}',
            'types': ['Instant'],
            'text': 'Play with Fire deals 2 damage to any target. If a player was dealt damage this way, scry 1.',
            'rarity': 'uncommon'
        })

        # 4. Murder (Bad substitute: different color, different CMC)
        self.murder = cardlib.Card({
            'name': 'Murder',
            'manaCost': '{1}{B}{B}',
            'types': ['Instant'],
            'text': 'Destroy target creature.',
            'rarity': 'uncommon'
        })

        # 5. Grizzly Bears (Bad substitute: different type, no shared actions)
        self.bears = cardlib.Card({
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        })

        self.pool = [self.bolt, self.shock, self.pwf, self.murder, self.bears]

    def test_find_substitutes_basic(self):
        subs = mtg_query.find_substitutes(self.bolt, self.pool)
        sub_names = [c.name.lower() for c in subs]

        self.assertIn('shock', sub_names)
        self.assertIn('play with fire', sub_names)
        self.assertNotIn('Lightning Bolt', sub_names) # Should not include itself
        self.assertNotIn('Murder', sub_names) # Wrong color
        self.assertNotIn('Grizzly Bears', sub_names) # Wrong type/action

    def test_find_substitutes_empty(self):
        subs = mtg_query.find_substitutes(self.bolt, [])
        self.assertEqual(subs, [])

        subs = mtg_query.find_substitutes(None, self.pool)
        self.assertEqual(subs, [])

    def test_handle_substitutes_cli(self):
        # Mocking the dataset loading to use our small pool
        with patch('cli_utils.load_and_filter_cards') as mock_load:
            mock_load.return_value = self.pool

            # Mocking _execute_search to capture results
            with patch('mtg_query._execute_search') as mock_exec:
                args = patch('argparse.Namespace').start()
                args.query = 'Lightning Bolt'
                args.infile = '-'
                args.quiet = True
                args.limit = 10

                mtg_query.handle_substitutes(args)

                # Check that _execute_search was called with the correct substitutes
                self.assertTrue(mock_exec.called)
                subs = mock_exec.call_args[0][0]
                names = [c.name.lower() for c in subs]
                self.assertIn('shock', names)
                self.assertIn('play with fire', names)

if __name__ == '__main__':
    unittest.main()
