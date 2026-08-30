import unittest
import os
import sys
import tempfile
import io
from unittest.mock import patch

# Ensure repo root and scripts are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from scripts.mtg_csv_json import run_csv2json, run_json2csv, main as mtg_csv_json_main

class TestCSVJSONDryRun(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = os.path.join(self.temp_dir.name, "test_cards.csv")
        with open(self.csv_path, "w", encoding="utf-8") as f:
            f.write("name,mana_cost,type,subtypes,text,pt,rarity\n")
            f.write("Grizzly Bears,{1}{G},Creature,Bear,Vanilla creature,2/2,C\n")
            f.write("Front face // Back face,{1}{W} // {U},Creature // Instant,Human,,1/1 // ,U\n")

        self.json_path = "testdata/uthros.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_csv2json_dry_run_no_outfile(self):
        stdout_capture = io.StringIO()
        with patch('sys.stdout', stdout_capture):
            run_csv2json([self.csv_path, '--dry-run'])

        output = stdout_capture.getvalue()
        self.assertIn("=== CSV to JSON Conversion Summary (Dry Run) ===", output)
        self.assertIn("Total cards evaluated: 2", output)
        self.assertIn("Single-faced cards: 1", output)
        self.assertIn("Multi-faced cards: 1", output)
        self.assertIn("Grizzly Bears", output)

    def test_csv2json_dry_run_with_outfile_no_file_created(self):
        outfile = os.path.join(self.temp_dir.name, "output.json")
        stdout_capture = io.StringIO()
        with patch('sys.stdout', stdout_capture):
            run_csv2json([self.csv_path, outfile, '-p'])

        output = stdout_capture.getvalue()
        self.assertIn("=== CSV to JSON Conversion Summary (Dry Run) ===", output)
        self.assertFalse(os.path.exists(outfile))

    def test_csv2json_missing_outfile_without_dryrun_raises(self):
        stderr_capture = io.StringIO()
        with patch('sys.stderr', stderr_capture), self.assertRaises(SystemExit):
            run_csv2json([self.csv_path])

    def test_json2csv_dry_run_no_outfile(self):
        stdout_capture = io.StringIO()
        with patch('sys.stdout', stdout_capture):
            run_json2csv([self.json_path, '--dry-run'])

        output = stdout_capture.getvalue()
        self.assertIn("=== JSON to CSV Export Summary (Dry Run) ===", output)
        self.assertIn("Total cards evaluated: 1", output)
        self.assertIn("uthros research craft", output)

    def test_json2csv_dry_run_with_outfile_no_file_created(self):
        outfile = os.path.join(self.temp_dir.name, "output.csv")
        stdout_capture = io.StringIO()
        with patch('sys.stdout', stdout_capture):
            run_json2csv([self.json_path, outfile, '--preview'])

        output = stdout_capture.getvalue()
        self.assertIn("=== JSON to CSV Export Summary (Dry Run) ===", output)
        self.assertFalse(os.path.exists(outfile))

    def test_json2csv_missing_outfile_without_dryrun_raises(self):
        stderr_capture = io.StringIO()
        with patch('sys.stderr', stderr_capture), self.assertRaises(SystemExit):
            run_json2csv([self.json_path])

    def test_json2csv_dry_run_no_matching_cards(self):
        stdout_capture = io.StringIO()
        with patch('sys.stdout', stdout_capture):
            run_json2csv([self.json_path, '--dry-run', '--grep', 'NONEXISTENT_CARD_PATTERN_999'])

        output = stdout_capture.getvalue()
        self.assertIn("=== JSON to CSV Export Summary (Dry Run) ===", output)
        self.assertIn("Total cards evaluated: 0", output)

    def test_mtg_csv_json_main_autodetect_csv(self):
        stdout_capture = io.StringIO()
        with patch('sys.argv', ['mtg_csv_json.py', self.csv_path, '--dry-run']), patch('sys.stdout', stdout_capture):
            mtg_csv_json_main()

        output = stdout_capture.getvalue()
        self.assertIn("=== CSV to JSON Conversion Summary (Dry Run) ===", output)

    def test_mtg_csv_json_main_autodetect_json(self):
        stdout_capture = io.StringIO()
        with patch('sys.argv', ['mtg_csv_json.py', self.json_path, '--dry-run']), patch('sys.stdout', stdout_capture):
            mtg_csv_json_main()

        output = stdout_capture.getvalue()
        self.assertIn("=== JSON to CSV Export Summary (Dry Run) ===", output)

if __name__ == '__main__':
    unittest.main()
