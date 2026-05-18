import unittest
from unittest.mock import MagicMock, patch
import io
import json
import sys
import os

# Add root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.mtg_costs import get_cost_metrics, main

class TestMtgCosts(unittest.TestCase):

    def test_get_cost_metrics(self):
        # Mock Card
        card = MagicMock()
        card.cost.cmc = 2.0
        card.cost.allsymbols = {'G': 2, '1': 0}

        pips, intensity, cat = get_cost_metrics(card)
        self.assertEqual(pips, 2)
        self.assertEqual(intensity, 1.0)
        self.assertEqual(cat, "Double")

        # CMC 0
        card.cost.cmc = 0.0
        card.cost.allsymbols = {'G': 0}
        pips, intensity, cat = get_cost_metrics(card)
        self.assertEqual(pips, 0)
        self.assertEqual(intensity, 0.0)
        self.assertEqual(cat, "None")

        # Heavy
        card.cost.cmc = 5.0
        card.cost.allsymbols = {'W': 2, 'U': 2, '1': 1}
        pips, intensity, cat = get_cost_metrics(card)
        self.assertEqual(pips, 4)
        self.assertEqual(intensity, 0.8)
        self.assertEqual(cat, "Heavy (4+)")

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_table(self, mock_stdout, mock_open):
        # Setup mock cards
        c1 = MagicMock()
        c1.is_land = False
        c1.display_name = "Bear"
        c1.cost.format.return_value = "{1}{G}"
        c1.cost.cmc = 2.0
        c1.cost.allsymbols = {'G': 1, '1': 1}
        c1.rarity_name = "common"
        c1._get_ansi_color.return_value = ""

        c2 = MagicMock()
        c2.is_land = False
        c2.display_name = "Triple Threat"
        c2.cost.format.return_value = "{U}{U}{U}"
        c2.cost.cmc = 3.0
        c2.cost.allsymbols = {'U': 3}
        c2.rarity_name = "rare"
        c2._get_ansi_color.return_value = ""

        mock_open.return_value = [c1, c2]

        with patch('sys.argv', ['mtg_costs.py', 'dummy.json', '--no-color']):
            main()

        output = mock_stdout.getvalue()
        self.assertIn("COLOR INTENSITY ANALYSIS", output)
        self.assertIn("Bear", output)
        self.assertIn("Triple Threat", output)
        self.assertIn("Average Color Intensity: 0.75", output)
        self.assertIn("Single", output)
        self.assertIn("Triple", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_json(self, mock_stdout, mock_open):
        c1 = MagicMock()
        c1.is_land = False
        c1.display_name = "Bear"
        c1.cost.format.return_value = "{1}{G}"
        c1.cost.cmc = 2.0
        c1.cost.allsymbols = {'G': 1, '1': 1}
        c1.rarity_name = "common"
        c1._get_ansi_color.return_value = ""

        mock_open.return_value = [c1]

        with patch('sys.argv', ['mtg_costs.py', 'dummy.json', '--json']):
            main()

        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertEqual(data['total_analyzed'], 1)
        self.assertEqual(data['top_intensity_cards'][0]['name'], "Bear")
        self.assertEqual(data['pip_distribution']['Single'], 1)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_no_cards(self, mock_stderr, mock_open):
        mock_open.return_value = []
        with patch('sys.argv', ['mtg_costs.py', 'dummy.json']):
            main()
        self.assertIn("No cards found", mock_stderr.getvalue())

if __name__ == '__main__':
    unittest.main()
