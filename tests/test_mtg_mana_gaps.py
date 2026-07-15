import unittest
from unittest.mock import patch, MagicMock
import io
import os
import sys
import json
import csv

# Add lib and scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import scripts.mtg_analyze as mtg_analyze
from lib.cardlib import Card

class TestMtgManaGaps(unittest.TestCase):

    def test_get_produced_colors_wastes(self):
        # Wastes as subtype
        card = Card({'name': 'Wastes', 'types': ['Land'], 'subtypes': ['Wastes']})
        self.assertEqual(card.produced_colors, {'C'})

        # Wastes as type
        card = Card({'name': 'Wastes', 'types': ['Wastes', 'Land']})
        self.assertEqual(card.produced_colors, {'C'})

    def test_get_produced_colors_hybrid_and_complex(self):
        # Hybrid symbols
        card = Card({'name': 'Hybrid', 'types': ['Artifact'], 'text': '{T}: Add {W/U}.'})
        self.assertEqual(card.produced_colors, {'W', 'U'})

        # Multiple symbols in one line
        card = Card({'name': 'Complex', 'types': ['Artifact'], 'text': '{T}: Add {R}{G} or {B}{B}.'})
        self.assertEqual(card.produced_colors, {'R', 'G', 'B'})

    def test_get_produced_colors_older_text(self):
        patterns = [
            ("Add one white mana", 'W'),
            ("Add two blue mana", 'U'),
            ("Add three black mana", 'B'),
            ("Add X red mana", 'R'),
            ("Add one green mana", 'G'),
            ("Add one colorless mana", 'C')
        ]
        for text, color in patterns:
            card = Card({'name': 'Old Text', 'types': ['Artifact'], 'text': text})
            self.assertEqual(card.produced_colors, {color}, f"Failed for pattern: {text}")

    def test_get_produced_colors_bside_recursion(self):
        # B-side produces Any
        bside_json = {'name': 'Back', 'types': ['Artifact'], 'text': '{T}: Add one mana of any color.'}
        card = Card({'name': 'Front', 'types': ['Enchantment'], 'bside': bside_json})
        self.assertEqual(card.produced_colors, {'Any'})

        # B-side produces specific color
        bside_json = {'name': 'Back', 'types': ['Land'], 'subtypes': ['Forest']}
        card = Card({'name': 'Front', 'types': ['Artifact'], 'bside': bside_json})
        self.assertEqual(card.produced_colors, {'G'})

    @patch('mtg_analyze.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_json_output(self, mock_stdout, mock_open):
        mock_open.return_value = [Card({'name': 'Forest', 'types': ['Land'], 'subtypes': ['Forest']})]

        with patch('sys.argv', ['mtg_analyze.py', 'mana', '-', '--json']):
            mtg_analyze.main()

        result = json.loads(mock_stdout.getvalue())
        self.assertIn('primary', result)
        self.assertEqual(result['primary']['colors']['G'], 1)

    @patch('mtg_analyze.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_csv_output(self, mock_stdout, mock_open):
        mock_open.return_value = [Card({'name': 'Forest', 'types': ['Land'], 'subtypes': ['Forest']})]

        with patch('sys.argv', ['mtg_analyze.py', 'mana', '-', '--csv']):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        reader = csv.DictReader(io.StringIO(output))
        rows = list(reader)
        self.assertTrue(any(row['Metric'] == 'Producer Count' and row['Value'] == '1' for row in rows))

    @patch('mtg_analyze.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_compare(self, mock_stdout, mock_open):
        # First call for primary, second for comparison
        mock_open.side_effect = [
            [Card({'name': 'Forest', 'types': ['Land'], 'subtypes': ['Forest']})],
            [Card({'name': 'Island', 'types': ['Land'], 'subtypes': ['Island']})]
        ]

        with patch('sys.argv', ['mtg_analyze.py', 'mana', 'file1.json', '--compare', 'file2.json', '--no-color']):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        self.assertIn("MANA PRODUCTION ANALYSIS (COMPARISON)", output)
        self.assertIn("Diff", output)

    @patch('mtg_analyze.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_smart_args(self, mock_stdout, mock_open):
        # Case 1: Infile doesn't exist, treated as query
        mock_open.return_value = [Card({'name': 'Lotus', 'types': ['Artifact'], 'text': 'Add any color.'})]

        with patch('os.path.exists', return_value=False):
            with patch('sys.argv', ['mtg_analyze.py', 'mana', 'Lotus', '--no-color']):
                # We need to mock sys.stdin.isatty to avoid it trying to load AllPrintings.json
                with patch('sys.stdin.isatty', return_value=False):
                    mtg_analyze.main()

        # Verify grep was passed to mtg_open_file
        mock_open.assert_called_with('-', verbose=False, grep=['Lotus'], vgrep=None,
                                    grep_name=None, vgrep_name=None, grep_types=None, vgrep_types=None,
                                    grep_text=None, vgrep_text=None, grep_cost=None, vgrep_cost=None,
                                    grep_pt=None, vgrep_pt=None, grep_loyalty=None, vgrep_loyalty=None,
                                    sets=None, rarities=None, colors=None, cmcs=None,
                                    pows=None, tous=None, loys=None, mechanics=None,
                                    actions=None,
                                    produces=None,
                                    color_pie_break=False,
                                    identities=None, id_counts=None,
                                    decklist_file=None, booster=0, box=0,
                                    shuffle=False, seed=None,
                                    complexities=None, ratings=None, fair_mvs=None,
                                    legalities=None)

    @patch('mtg_analyze.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_color_and_charts(self, mock_stdout, mock_open):
        mock_open.return_value = [
            Card({'name': 'Forest', 'types': ['Land'], 'subtypes': ['Forest']}),
            Card({'name': 'Elf', 'types': ['Creature'], 'text': '{T}: Add {G}.'})
        ]

        with patch('sys.argv', ['mtg_analyze.py', 'mana', '-', '--color']):
            mtg_analyze.main()

        output = mock_stdout.getvalue()
        # Check for ANSI escape codes (simplified check)
        self.assertIn("\033[", output)
        self.assertIn("MANA PRODUCTION ANALYSIS", output)
        self.assertIn("G", output)

    @patch('mtg_analyze.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_empty_dataset(self, mock_stdout, mock_open):
        mock_open.return_value = []

        with patch('sys.argv', ['mtg_analyze.py', 'mana', '-', '--quiet']):
            mtg_analyze.main()

        self.assertEqual(mock_stdout.getvalue(), "")

if __name__ == '__main__':
    unittest.main()
