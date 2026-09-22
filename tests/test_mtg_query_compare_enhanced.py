import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import io

# Add scripts and lib to path
sys.path.append(os.path.join(os.getcwd(), 'scripts'))
sys.path.append(os.path.join(os.getcwd(), 'lib'))

import mtg_query

class TestMtgQueryCompareEnhanced(unittest.TestCase):

    def setUp(self):
        self.testdata_path = 'testdata/'

    def run_compare(self, args_list):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                with patch('sys.argv', ['mtg_query.py', 'compare'] + args_list):
                    try:
                        mtg_query.main()
                    except SystemExit:
                        pass
                    return fake_out.getvalue(), fake_err.getvalue()

    def test_compare_n_way(self):
        """Test that 3 cards can be compared."""
        output, _ = self.run_compare(['Beast Summoner', 'Black Lotus', 'Double Front', self.testdata_path])
        self.assertIn('Beast Summoner', output)
        self.assertIn('Black Lotus', output)
        self.assertIn('Double Front', output)
        # Check for 3 columns (excluding Field column)
        # We check if 'Beast Summoner' header and 'Black Lotus' header and 'Double Front' header are present
        lines = output.split('\n')
        header_line = next(l for l in lines if 'Field' in l)
        self.assertIn('Beast Summoner', header_line)
        self.assertIn('Black Lotus', header_line)
        self.assertIn('Double Front', header_line)

    def test_auto_similarity(self):
        """Test that providing one card triggers auto-similarity."""
        output, stderr = self.run_compare(['Uthros', self.testdata_path])
        self.assertIn('Notice: Only one card provided', stderr)
        self.assertIn('Uthros Research Craft', output)
        # Should have found Drake Nest as most similar
        self.assertIn('Drake Nest', output)

    def test_pool_comparison(self):
        """Test comparing a pool of cards via filters."""
        output, stderr = self.run_compare(['--grep', 'Station', self.testdata_path])
        self.assertIn('Comparing pool of', stderr)
        self.assertIn('Uthros Research Craft', output)

    def test_compare_json(self):
        """Test JSON output for N-way comparison."""
        output, _ = self.run_compare(['Beast Summoner', 'Black Lotus', 'Double Front', self.testdata_path, '--json'])
        data = json.loads(output)
        self.assertIn('card1', data)
        self.assertIn('card2', data)
        self.assertIn('card3', data)
        self.assertEqual(data['card1']['name'], 'Beast Summoner')
        self.assertEqual(data['card2']['name'], 'Black Lotus')

    def test_compare_outfile_plain_text(self):
        """Test saving plain text table output to a file via -o / --outfile."""
        outfile = 'test_compare_out.txt'
        try:
            output, _ = self.run_compare(['Beast Summoner', 'Black Lotus', self.testdata_path, '-o', outfile])
            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn('CARD COMPARISON', content)
            self.assertIn('Beast Summoner', content)
            self.assertIn('Black Lotus', content)
        finally:
            if os.path.exists(outfile):
                os.remove(outfile)

    def test_compare_outfile_json_autodetect(self):
        """Test auto-detecting JSON export from .json output filename extension."""
        outfile = 'test_compare_out.json'
        try:
            output, _ = self.run_compare(['Beast Summoner', 'Black Lotus', self.testdata_path, '-o', outfile])
            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertIn('card1', data)
            self.assertIn('card2', data)
            self.assertEqual(data['card1']['name'], 'Beast Summoner')
            self.assertEqual(data['card2']['name'], 'Black Lotus')
        finally:
            if os.path.exists(outfile):
                os.remove(outfile)

    def test_compare_outfile_csv_autodetect(self):
        """Test CSV format output via --csv and auto-detection from .csv filename extension."""
        outfile = 'test_compare_out.csv'
        try:
            output, _ = self.run_compare(['Beast Summoner', 'Black Lotus', self.testdata_path, '-o', outfile])
            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn('Field,Beast Summoner,Black Lotus', content)
            self.assertIn('Cost,{2}{G},{0}', content)
            self.assertIn('CMC,3,0', content)
        finally:
            if os.path.exists(outfile):
                os.remove(outfile)

if __name__ == '__main__':
    unittest.main()
