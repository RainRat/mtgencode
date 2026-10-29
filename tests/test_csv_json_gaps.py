import unittest
from unittest.mock import patch
import sys
import os
import io
import json
import tempfile
import runpy

# Add repo root and lib to sys.path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_csv_json import run_csv2json, run_json2csv, main as csv_json_main

class TestMtgCsvJsonGaps(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

        # Create a sample CSV file
        self.csv_path = os.path.join(self.tmpdir.name, "sample.csv")
        self.csv_content = (
            'name,manaCost,types,subtypes,text,pt,rarity\n'
            'Sample Card,{1}{G},Creature,Bear,When Sample Card enters,2/2,C\n'
        )
        with open(self.csv_path, "w", encoding="utf-8") as f:
            f.write(self.csv_content)

        # Create a sample MTGJSON file
        self.json_path = os.path.join(self.tmpdir.name, "sample.json")
        self.json_content = {
            "data": {
                "TEST": {
                    "code": "TEST",
                    "name": "Test Set",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Test Card",
                            "manaCost": "{U}",
                            "types": ["Instant"],
                            "text": "Draw a card.",
                            "rarity": "common"
                        }
                    ]
                }
            }
        }
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.json_content, f)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_run_csv2json_stdin_implicit_stdout_default(self):
        stdout_capture = io.StringIO()
        with patch('sys.stdin', io.StringIO(self.csv_content)), \
             patch('sys.stdout', stdout_capture):
            run_csv2json(['-'])

        output = stdout_capture.getvalue()
        data = json.loads(output)
        self.assertEqual(data['data']['CUS']['cards'][0]['name'], 'Sample Card')

    def test_run_json2csv_stdin_implicit_stdout_default(self):
        stdout_capture = io.StringIO()
        with patch('sys.stdin', io.StringIO(json.dumps(self.json_content))), \
             patch('sys.stdout', stdout_capture):
            run_json2csv(['-'])

        output = stdout_capture.getvalue()
        self.assertIn("name,mana_cost,type,subtypes,text,pt,rarity", output)
        self.assertIn("test card", output.lower())

    def test_run_json2csv_verbose_no_cards(self):
        stderr_capture = io.StringIO()
        with patch('sys.stderr', stderr_capture):
            run_json2csv([self.json_path, os.path.join(self.tmpdir.name, "out.csv"), '-v', '--grep', 'NonExistentCardNameQuery'])

        err_output = stderr_capture.getvalue()
        self.assertIn("No cards found matching the criteria.", err_output)

    def test_run_json2csv_verbose_success(self):
        csv_out = os.path.join(self.tmpdir.name, "verbose_success.csv")
        stdout_capture = io.StringIO()
        with patch('sys.stdout', stdout_capture):
            run_json2csv([self.json_path, csv_out, '-v'])

        out_output = stdout_capture.getvalue()
        self.assertIn("Successfully exported", out_output)

    def test_main_json2csv_subcommand(self):
        csv_out = os.path.join(self.tmpdir.name, "subcmd_out.csv")
        test_args = ['mtg_csv_json.py', 'json2csv', self.json_path, csv_out]
        with patch('sys.argv', test_args):
            csv_json_main()

        self.assertTrue(os.path.exists(csv_out))
        with open(csv_out, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("test card", content.lower())

    def test_main_autodetect_json2csv(self):
        csv_out = os.path.join(self.tmpdir.name, "autodetect_out.csv")
        test_args = ['mtg_csv_json.py', self.json_path, csv_out]
        with patch('sys.argv', test_args):
            csv_json_main()

        self.assertTrue(os.path.exists(csv_out))
        with open(csv_out, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("test card", content.lower())

    def test_main_tty_custom_csv_default(self):
        def mock_exists(path):
            if path in ["custom.csv", "custom.json"]:
                return True
            return False

        test_args = ['mtg_csv_json.py']
        with patch('sys.argv', test_args), \
             patch('sys.stdin.isatty', return_value=True), \
             patch('os.path.exists', side_effect=mock_exists), \
             patch('scripts.mtg_csv_json.run_csv2json') as mock_run_csv2json:
            csv_json_main()
            mock_run_csv2json.assert_called_once_with([])

    def test_main_tty_allprintings_default(self):
        def mock_exists(path):
            if path in ["data/AllPrintings.json", "data/AllPrintings.csv"]:
                return True
            return False

        test_args = ['mtg_csv_json.py']
        with patch('sys.argv', test_args), \
             patch('sys.stdin.isatty', return_value=True), \
             patch('os.path.exists', side_effect=mock_exists), \
             patch('scripts.mtg_csv_json.run_json2csv') as mock_run_json2csv:
            csv_json_main()
            mock_run_json2csv.assert_called_once_with([])

    def test_main_tty_no_infile_help_exit(self):
        test_args = ['mtg_csv_json.py']
        with patch('sys.argv', test_args), \
             patch('sys.stdin.isatty', return_value=True), \
             patch('os.path.exists', return_value=False), \
             patch('sys.stdout', new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as cm:
                csv_json_main()
            self.assertEqual(cm.exception.code, 0)

    def test_main_run_path_direct_execution(self):
        json_out = os.path.join(self.tmpdir.name, "run_path_out.json")
        test_args = ['mtg_csv_json.py', self.csv_path, json_out]
        with patch('sys.argv', test_args):
            runpy.run_path('scripts/mtg_csv_json.py', run_name='__main__')

        self.assertTrue(os.path.exists(json_out))

if __name__ == '__main__':
    unittest.main()
