import unittest
from unittest.mock import patch, mock_open
import io
import sys
import os
import json
import csv

# Add project root to sys.path
sys.path.append(os.getcwd())

import scripts.mtg_analyze as mtg_analyze
from lib.cardlib import Card

class TestMtgPipsGaps(unittest.TestCase):

    def run_main(self, args, stdin_isatty=False, stdout_isatty=False, exists_side_effect=None):
        with patch('sys.argv', ['mtg_analyze.py'] + args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.stdout.isatty', return_value=stdout_isatty):
                    with patch('sys.stderr', new=io.StringIO()) as fake_err:
                        with patch('sys.stdin.isatty', return_value=stdin_isatty):
                            real_exists = os.path.exists
                            def careful_exists(path):
                                if exists_side_effect:
                                    res = exists_side_effect(path)
                                    if res is not None:
                                        return res
                                return real_exists(path)

                            with patch('os.path.exists', side_effect=careful_exists):
                                try:
                                    mtg_analyze.main()
                                    code = 0
                                except SystemExit as e:
                                    code = e.code if isinstance(e.code, int) else 0
                                return code, fake_out.getvalue(), fake_err.getvalue()

    def test_pips_table_output(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("MANA PIP DISTRIBUTION", out)
        self.assertIn("U", out)

    def test_pips_json_output(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--json'])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(any(d['symbol'] == 'U' for d in data))

    def test_pips_csv_output(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--csv'])
        self.assertEqual(code, 0)
        reader = csv.DictReader(io.StringIO(out))
        rows = list(reader)
        self.assertTrue(any(row['Symbol'] == 'U' for row in rows))

    def test_pips_sorting_name(self):
        card1 = Card({"name": "White Card", "manaCost": "{W}", "types": ["Spell"]})
        card2 = Card({"name": "Blue Card", "manaCost": "{U}", "types": ["Spell"]})

        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[card1, card2]):
            code, out, err = self.run_main(['testdata/uthros.json', '--sort', 'name', '--no-color'])
            self.assertEqual(code, 0)
            lines = [line for line in out.split('\n') if '%' in line]
            self.assertIn('U', lines[0])
            self.assertIn('W', lines[1])

    def test_pips_sorting_count_reverse(self):
        card1 = Card({"name": "White Card", "manaCost": "{W}{W}", "types": ["Spell"]})
        card2 = Card({"name": "Blue Card", "manaCost": "{U}", "types": ["Spell"]})

        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[card1, card2]):
            code, out, err = self.run_main(['testdata/uthros.json', '--sort', 'count', '--reverse', '--no-color'])
            self.assertEqual(code, 0)
            lines = [line for line in out.split('\n') if '%' in line]
            self.assertIn('U', lines[0])
            self.assertIn('W', lines[1])

    def test_pips_include_text(self):
        card = Card({"name": "Test", "manaCost": "{W}", "text": "{U}: Do something.", "types": ["Spell"]})

        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[card]):
            code, out, err = self.run_main(['testdata/uthros.json', '--json'])
            data = json.loads(out)
            symbols = [d['symbol'] for d in data]
            self.assertIn('W', symbols)
            self.assertNotIn('U', symbols)

            code, out, err = self.run_main(['testdata/uthros.json', '--json', '--include-text', '--no-color'])
            data = json.loads(out)
            symbols = [d['symbol'] for d in data]
            self.assertIn('W', symbols)
            self.assertIn('U', symbols)

    def test_pips_include_text_table_branch(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--include-text', '--no-color'])
        self.assertEqual(code, 0)
        self.assertIn("INCLUDES RULES TEXT", out)

    def test_pips_bside(self):
        card = Card({
            "name": "Front", "manaCost": "{W}", "types": ["Spell"],
            "bside": {"name": "Back", "manaCost": "{B}", "types": ["Spell"]}
        })
        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[card]):
            code, out, err = self.run_main(['testdata/uthros.json', '--json'])
            data = json.loads(out)
            symbols = [d['symbol'] for d in data]
            self.assertIn('W', symbols)
            self.assertIn('B', symbols)

    def test_pips_outfile_json_autodetect(self):
        card = Card({"name": "Uthros", "manaCost": "{U}", "types": ["Spell"]})
        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[card]):
            m = mock_open()
            with patch('builtins.open', m):
                code, out, err = self.run_main(['testdata/uthros.json', 'output.json'])
                self.assertEqual(code, 0)
                m.assert_any_call('output.json', 'w', encoding='utf-8')

    def test_pips_outfile_csv_autodetect(self):
        card = Card({"name": "Uthros", "manaCost": "{U}", "types": ["Spell"]})
        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[card]):
            m = mock_open()
            with patch('builtins.open', m):
                code, out, err = self.run_main(['testdata/uthros.json', 'output.csv'])
                self.assertEqual(code, 0)
                m.assert_any_call('output.csv', 'w', encoding='utf-8')

    def test_pips_outfile_default_table(self):
        card = Card({"name": "Uthros", "manaCost": "{U}", "types": ["Spell"]})
        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[card]):
            m = mock_open()
            with patch('builtins.open', m):
                code, out, err = self.run_main(['testdata/uthros.json', 'output.txt'])
                self.assertEqual(code, 0)
                m.assert_any_call('output.txt', 'w', encoding='utf-8')

    def test_pips_no_matches(self):
        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[]):
            code, out, err = self.run_main(['testdata/uthros.json'])
            self.assertEqual(code, 0)
            self.assertIn("No cards found matching the criteria.", err)

    def test_default_dataset_detection_local(self):
        def exists_check(path):
            if path == 'data/AllPrintings.json': return True
            return None

        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[]) as mock_open_file:
            code, out, err = self.run_main(['-'], stdin_isatty=True, exists_side_effect=exists_check)
            self.assertIn("Notice: Using default dataset: data/AllPrintings.json", err)
            mock_open_file.assert_called()

    def test_default_dataset_detection_fallback(self):
        def exists_check(path):
            # Fail the first relative join check (simulated by script_dir join)
            # but pass the second 'data/AllPrintings.json' check
            if path == 'data/AllPrintings.json': return True
            return False # script_dir based one will look like absolute path

        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[]) as mock_open_file:
            code, out, err = self.run_main(['-'], stdin_isatty=True, exists_side_effect=exists_check)
            self.assertIn("Notice: Using default dataset: data/AllPrintings.json", err)
            mock_open_file.assert_called()

    def test_shorthand_sample(self):
        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[]) as mock_open_file:
            code, out, err = self.run_main(['testdata/uthros.json', '--sample', '5'])
            self.assertEqual(code, 0)
            args, kwargs = mock_open_file.call_args
            self.assertTrue(kwargs.get('shuffle'))

    def test_pips_color_force(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--color'])
        self.assertEqual(code, 0)
        self.assertIn("\033[", out)

    def test_pips_color_autodetect(self):
        code, out, err = self.run_main(['testdata/uthros.json'], stdout_isatty=True)
        self.assertEqual(code, 0)
        self.assertIn("\033[", out)

    def test_pips_verbose(self):
        card = Card({"name": "Uthros", "manaCost": "{U}", "types": ["Spell"]})
        with patch('scripts.mtg_analyze.jdecode.mtg_open_file', return_value=[card]):
            with patch('scripts.mtg_analyze.open', mock_open(), create=True) as m:
                code, out, err = self.run_main(['testdata/uthros.json', 'output.json', '--verbose'])
                self.assertEqual(code, 0)
                self.assertIn("Writing results to:", err)

    def test_pips_quiet(self):
        code, out, err = self.run_main(['testdata/uthros.json', '--quiet'])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

if __name__ == '__main__':
    unittest.main()
