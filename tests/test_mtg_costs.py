import unittest
from unittest.mock import patch, MagicMock
import sys
import io
import json
import os

# Add the project root to the path
sys.path.append(os.getcwd())

import scripts.mtg_analyze as mtg_analyze
import lib.cardlib as cardlib

class TestMtgCosts(unittest.TestCase):

    def test_get_cost_metrics_vanilla(self):
        # Grizzly Bears: 1G (CMC 2, 1 colored pip)
        card = cardlib.Card({
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'types': ['Creature'],
            'rarity': 'common'
        })
        cmc, pips, intensity, commitment = mtg_analyze.get_cost_metrics(card)
        self.assertEqual(cmc, 2.0)
        self.assertEqual(pips, 1)
        self.assertEqual(intensity, 0.5)
        self.assertEqual(commitment, 1)

    def test_get_cost_metrics_heavy(self):
        # Gigantosaurus: GGGGG (CMC 5, 5 colored pips)
        card = cardlib.Card({
            'name': 'Gigantosaurus',
            'manaCost': '{G}{G}{G}{G}{G}',
            'types': ['Creature'],
            'rarity': 'rare'
        })
        cmc, pips, intensity, commitment = mtg_analyze.get_cost_metrics(card)
        self.assertEqual(cmc, 5.0)
        self.assertEqual(pips, 5)
        self.assertEqual(intensity, 1.0)
        self.assertEqual(commitment, 5)

    def test_get_cost_metrics_hybrid(self):
        # Hybrid: {W/U}{W/U} (CMC 2, 2 colored pips, Commitment 2 for both W and U)
        card = cardlib.Card({
            'name': 'Hybrid Card',
            'manaCost': '{W/U}{W/U}',
            'types': ['Instant'],
            'rarity': 'common'
        })
        cmc, pips, intensity, commitment = mtg_analyze.get_cost_metrics(card)
        self.assertEqual(cmc, 2.0)
        self.assertEqual(pips, 2)
        self.assertEqual(intensity, 1.0)
        self.assertEqual(commitment, 2)

    def test_get_cost_metrics_colorless(self):
        # Sol Ring: 1 (CMC 1, 0 colored pips)
        card = cardlib.Card({
            'name': 'Sol Ring',
            'manaCost': '{1}',
            'types': ['Artifact'],
            'rarity': 'uncommon'
        })
        cmc, pips, intensity, commitment = mtg_analyze.get_cost_metrics(card)
        self.assertEqual(cmc, 1.0)
        self.assertEqual(pips, 0)
        self.assertEqual(intensity, 0.0)
        self.assertEqual(commitment, 0)

    @patch('scripts.mtg_analyze.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_table(self, mock_stdout, mock_open):
        # Mock cards
        c1 = cardlib.Card({'name': 'C1', 'manaCost': '{G}', 'types': ['Creature'], 'rarity': 'common'})
        c2 = cardlib.Card({'name': 'C2', 'manaCost': '{1}{U}', 'types': ['Instant'], 'rarity': 'rare'})
        mock_open.return_value = [c1, c2]

        with patch('sys.argv', ['mtg_analyze.py', 'costs', 'dummy.json']):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        self.assertIn('MANA COST INTENSITY ANALYSIS', output)
        self.assertIn('Global Average Intensity: 0.75', output)
        self.assertIn('Single', output)
        self.assertIn('2', output)

    @patch('scripts.mtg_analyze.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_json(self, mock_stdout, mock_open):
        c1 = cardlib.Card({'name': 'C1', 'manaCost': '{G}', 'types': ['Creature'], 'rarity': 'common'})
        mock_open.return_value = [c1]

        with patch('sys.argv', ['mtg_analyze.py', 'costs', 'dummy.json', '--json']):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertEqual(data['total_cards'], 1)
        self.assertEqual(data['avg_intensity'], 1.0)
        self.assertEqual(data['commitment_distribution']['Single'], 1)

if __name__ == '__main__':
    unittest.main()
