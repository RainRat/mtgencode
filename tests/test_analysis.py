import sys
import os
import unittest
import tempfile
import json
import math
from collections import OrderedDict
from io import StringIO
from unittest.mock import patch, MagicMock

# Ensure root is in pythonpath
sys.path.append(os.getcwd())

from scripts.analysis import get_statistics, print_statistics, main as analysis_main, gmean_nonzero
from scripts.ngrams import build_ngram_model
import lib.jdecode as jdecode

class TestAnalysis(unittest.TestCase):
    def setUp(self):
        self.cards_data = {
            "data": {
                "TEST": {
                    "name": "Test Set",
                    "code": "TEST",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Plains",
                            "types": ["Land"],
                            "text": "{T}: Add {W}.",
                            "rarity": "Common"
                        },
                        {
                            "name": "Grizzly Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "text": "Bear power.",
                            "rarity": "Common",
                            "power": "2",
                            "toughness": "2"
                        },
                        {
                            "name": "No Text Card",
                            "types": ["Instant"],
                            "text": "",
                            "rarity": "Common"
                        }
                    ]
                }
            }
        }

        self.temp_dir = tempfile.TemporaryDirectory()
        self.json_path = os.path.join(self.temp_dir.name, "test_cards.json")
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.cards_data, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_statistics_without_lm(self):
        stats = get_statistics(self.json_path, lm=None)
        self.assertIn('cards', stats)
        self.assertIn('props', stats)
        self.assertEqual(len(stats['cards']), 3)

    def test_get_statistics_with_lm_sep_true(self):
        cards = jdecode.mtg_open_file(self.json_path)
        lm = build_ngram_model(cards, n=2, separate_lines=True)

        stats = get_statistics(self.json_path, lm=lm, sep=True)
        self.assertIn('ngram', stats)
        ngram_stats = stats['ngram']
        self.assertIn('perp_mean', ngram_stats)
        self.assertIn('perp_per_mean', ngram_stats)

    def test_get_statistics_with_lm_sep_false(self):
        cards = jdecode.mtg_open_file(self.json_path)
        lm = build_ngram_model(cards, n=2, separate_lines=False)

        stats = get_statistics(self.json_path, lm=lm, sep=False)
        self.assertIn('ngram', stats)
        ngram_stats = stats['ngram']
        self.assertIn('perp_mean', ngram_stats)
        self.assertIn('perp_per_mean', ngram_stats)

    def test_get_statistics_checkpoint_parsing(self):
        epoch_path = os.path.join(self.temp_dir.name, "model_epoch50.00_0.1870.myid.1.0.txt")
        with open(epoch_path, 'w', encoding='utf-8') as f:
            json.dump(self.cards_data, f)

        stats = get_statistics(epoch_path, lm=None)
        self.assertIn('cp', stats)
        cp = stats['cp']
        self.assertEqual(cp['name'], 'model')
        self.assertEqual(cp['epoch'], 50.0)
        self.assertEqual(cp['vloss'], 0.187)
        self.assertEqual(cp['temp'], 1.0)
        self.assertEqual(cp['ident'], 'myid')

    def test_get_statistics_with_dist_file(self):
        dist_path = self.json_path + ".dist"
        lines = [
            "0|Plains|1.0|1.0",
            "1|Grizzly Bears|0.5|nan",
            "2|Other|0.0|0.0",
            "short_line_ignored",
            ""
        ]
        with open(dist_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

        stats = get_statistics(self.json_path, lm=None)
        self.assertIn('dists', stats)
        dists = stats['dists']
        self.assertEqual(len(dists['name']), 3)
        self.assertEqual(len(dists['cbow']), 3)
        self.assertAlmostEqual(dists['name_mean'], 0.5)
        self.assertAlmostEqual(dists['cbow_mean'], 0.5)
        self.assertAlmostEqual(dists['name_geomean'], 0.70710678)
        self.assertAlmostEqual(dists['cbow_geomean'], 1.0)

    def test_print_statistics_output_formatting(self):
        stats = OrderedDict([
            ('nested', OrderedDict([('key', 'value')])),
            ('simple_dict', {'a': 1}),
            ('simple_list', [1, 2, 3]),
            ('primitive', 12.34)
        ])

        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            print_statistics(stats)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("nested:", output)
        self.assertIn("  key: value", output)
        self.assertIn("simple_dict: <dict with 1 entries>", output)
        self.assertIn("simple_list: <list with 3 entries>", output)
        self.assertIn("primitive: 12.34", output)

    @patch('scripts.analysis.jdecode.mtg_open_file')
    @patch('scripts.analysis.ngrams.build_ngram_model')
    @patch('scripts.analysis.get_statistics')
    def test_analysis_main_execution(self, mock_get_stats, mock_build_model, mock_open_file):
        mock_cards = MagicMock()
        mock_open_file.return_value = mock_cards

        mock_lm = MagicMock()
        mock_build_model.return_value = mock_lm

        mock_stats = OrderedDict([('cards', [])])
        mock_get_stats.return_value = mock_stats

        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            analysis_main("dummy_file", verbose=True)
        finally:
            sys.stdout = sys.__stdout__

        mock_open_file.assert_called_once()
        mock_build_model.assert_called_once_with(mock_cards, 3, separate_lines=True, verbose=True)
        mock_get_stats.assert_called_once_with("dummy_file", lm=mock_lm, sep=True, verbose=True)

    def test_gmean_nonzero_empty(self):
        self.assertEqual(gmean_nonzero([]), 0.0)
        self.assertEqual(gmean_nonzero([0.0, math.nan]), 0.0)

    @patch('jdecode.mtg_open_file')
    @patch('ngrams.build_ngram_model')
    @patch('scripts.analysis.get_statistics')
    def test_main_cli_invocation(self, mock_get_stats, mock_build, mock_open):
        mock_open.return_value = []
        mock_build.return_value = None
        mock_get_stats.return_value = OrderedDict()

        import runpy
        with patch('sys.argv', ['scripts/analysis.py', 'some_infile', '-v']):
            runpy.run_path('scripts/analysis.py', run_name='__main__')

if __name__ == '__main__':
    unittest.main()
