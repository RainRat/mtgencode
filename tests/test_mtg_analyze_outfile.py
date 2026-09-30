# Copyright 2026 Google LLC
import os
import sys
import json
import unittest
import tempfile
from unittest.mock import patch

import scripts.mtg_analyze as mtg_analyze


class TestMTGAnalyzeOutfile(unittest.TestCase):
    """Unit tests for -o/--outfile flag support and extension format auto-detection in mtg_analyze.py."""

    def setUp(self):
        self.testdata_file = os.path.join(os.path.dirname(__file__), '../testdata/tarkir.json')

    def test_curve_outfile_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outfile = os.path.join(tmpdir, 'curve_output.txt')
            test_args = ['mtg_analyze.py', 'curve', self.testdata_file, '-o', outfile]
            with patch.object(sys, 'argv', test_args):
                mtg_analyze.main()

            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn('MANA CURVE ANALYSIS', content)

    def test_summary_outfile_json_autodetect(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outfile = os.path.join(tmpdir, 'summary_output.json')
            test_args = ['mtg_analyze.py', 'summary', self.testdata_file, '-o', outfile]
            with patch.object(sys, 'argv', test_args):
                mtg_analyze.main()

            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertIn('counts', data)
            self.assertIn('indices', data)

    def test_audit_outfile_json_autodetect(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outfile = os.path.join(tmpdir, 'audit_output.json')
            test_args = ['mtg_analyze.py', 'audit', self.testdata_file, '-o', outfile]
            with patch.object(sys, 'argv', test_args):
                mtg_analyze.main()

            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertIn('total_cards', data)
            self.assertIn('avg_cmc', data)

    def test_pips_outfile_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outfile = os.path.join(tmpdir, 'pips_output.json')
            test_args = ['mtg_analyze.py', 'pips', self.testdata_file, '-o', outfile]
            with patch.object(sys, 'argv', test_args):
                mtg_analyze.main()

            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertIsInstance(data, list)

    def test_complexity_outfile_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outfile = os.path.join(tmpdir, 'complexity_output.json')
            test_args = ['mtg_analyze.py', 'complexity', self.testdata_file, '--outfile', outfile]
            with patch.object(sys, 'argv', test_args):
                mtg_analyze.main()

            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertIn('primary', data)


if __name__ == '__main__':
    unittest.main()
