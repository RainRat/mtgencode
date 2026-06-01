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

import scripts.mtg_analyze as mtg_analyze
import cardlib

class TestMtgInteraction(unittest.TestCase):

    def setUp(self):
        # Create sample cards with mechanics
        self.card1 = cardlib.Card({'name': 'Flying Haste', 'rarity': 'common', 'text': 'Flying, haste'})
        self.card2 = cardlib.Card({'name': 'Flying Trample', 'rarity': 'common', 'text': 'Flying, trample'})
        self.card3 = cardlib.Card({'name': 'Trample Haste', 'rarity': 'common', 'text': 'Trample, haste'})
        self.card4 = cardlib.Card({'name': 'Vanilla', 'rarity': 'common', 'text': ''})
        self.cards = [self.card1, self.card2, self.card3, self.card4]

    def test_calculate_interaction_basic(self):
        density_dist, ind_counts, pair_counts, interaction_results = mtg_analyze.calculate_interaction(self.cards, min_freq=1)

        # Density distribution:
        # card1: 2 (Flying, Haste)
        # card2: 2 (Flying, Trample)
        # card3: 2 (Trample, Haste)
        # card4: 0
        self.assertEqual(density_dist[2], 3)
        self.assertEqual(density_dist[0], 1)

        # Individual counts:
        # Flying: 2
        # Haste: 2
        # Trample: 2
        self.assertEqual(ind_counts['Flying'], 2)
        self.assertEqual(ind_counts['Haste'], 2)
        self.assertEqual(ind_counts['Trample'], 2)

        # Pair counts:
        # (Flying, Haste): 1
        # (Flying, Trample): 1
        # (Trample, Haste): 1
        self.assertEqual(pair_counts[('Flying', 'Haste')], 1)
        self.assertEqual(pair_counts[('Flying', 'Trample')], 1)
        self.assertEqual(pair_counts[('Haste', 'Trample')], 1)

        # Lift calculation for (Flying, Haste):
        # P(A and B) = 1/4 = 0.25
        # P(A) = 2/4 = 0.5
        # P(B) = 2/4 = 0.5
        # Lift = 0.25 / (0.5 * 0.5) = 1.0
        flying_haste = next(r for r in interaction_results if r['pair'] == ('Flying', 'Haste'))
        self.assertAlmostEqual(flying_haste['lift'], 1.0)

    def test_calculate_interaction_min_freq(self):
        # min_freq=2 should return no results for this dataset
        _, _, _, interaction_results = mtg_analyze.calculate_interaction(self.cards, min_freq=2)
        self.assertEqual(len(interaction_results), 0)

    def test_calculate_interaction_empty(self):
        density_dist, ind_counts, pair_counts, interaction_results = mtg_analyze.calculate_interaction([], min_freq=1)
        self.assertEqual(density_dist, {})
        self.assertEqual(len(ind_counts), 0)
        self.assertEqual(len(pair_counts), 0)
        self.assertEqual(len(interaction_results), 0)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_table(self, mock_stdout, mock_open):
        mock_open.return_value = self.cards

        with patch('sys.argv', ['mtg_analyze.py', 'interaction', 'dummy.json', '--no-color', '--min-freq', '1']):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        self.assertIn("MECHANICAL INTERACTION ANALYSIS", output)
        self.assertIn("Mechanical Density", output)
        self.assertIn("Top Interaction Pairs", output)
        self.assertIn("Flying + Haste", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_json(self, mock_stdout, mock_open):
        mock_open.return_value = self.cards

        with patch('sys.argv', ['mtg_analyze.py', 'interaction', 'dummy.json', '--json', '--min-freq', '1']):
            mtg_analyze.main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['total_cards'], 4)
        self.assertIn('density_distribution', output)
        self.assertIn('interaction_pairs', output)
        self.assertTrue(any(p['pair'] == ['Flying', 'Haste'] for p in output['interaction_pairs']))

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_csv(self, mock_stdout, mock_open):
        mock_open.return_value = self.cards

        with patch('sys.argv', ['mtg_analyze.py', 'interaction', 'dummy.json', '--csv', '--min-freq', '1']):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        self.assertIn("Mechanic 1,Mechanic 2,Count,Lift,P(A&B)", output)
        self.assertIn("Flying,Haste,1,1.00,0.2500", output)

    @patch('sys.stdin.isatty')
    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_smart_positional_args(self, mock_stdout, mock_open, mock_exists, mock_isatty):
        def exists_side_effect(path):
            if 'AllPrintings.json' in path: return True
            if path == 'Flying': return False
            return False

        mock_exists.side_effect = exists_side_effect
        mock_isatty.return_value = True
        mock_open.return_value = self.cards

        with patch('sys.argv', ['mtg_analyze.py', 'interaction', 'Flying']):
            mtg_analyze.main()

        self.assertTrue(mock_open.called)
        args, kwargs = mock_open.call_args
        self.assertIn('AllPrintings.json', args[0])
        self.assertEqual(kwargs['grep'], ['Flying'])

    @patch('jdecode.mtg_open_file')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_no_cards(self, mock_stderr, mock_open):
        mock_open.return_value = []

        with patch('sys.argv', ['mtg_analyze.py', 'interaction', 'dummy.json']):
            mtg_analyze.main()

        self.assertIn("No cards found matching the criteria.", mock_stderr.getvalue())

if __name__ == '__main__':
    unittest.main()
