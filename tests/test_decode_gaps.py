import os
import sys
import io
import json
import tempfile
import unittest
import runpy
from unittest.mock import patch

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import decode

class TestDecodeGaps(unittest.TestCase):
    def setUp(self):
        self.sample_json_data = {
            "data": {
                "TST": {
                    "code": "TST",
                    "name": "Test Set",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Lightning Bolt",
                            "manaCost": "{R}",
                            "types": ["Instant"],
                            "text": "Lightning Bolt deals 3 damage to any target.",
                            "rarity": "common",
                            "setCode": "TST",
                            "number": "1"
                        },
                        {
                            "name": "Counterspell",
                            "manaCost": "{U}{U}",
                            "types": ["Instant"],
                            "text": "Counter target spell.",
                            "rarity": "uncommon",
                            "setCode": "TST",
                            "number": "2"
                        }
                    ]
                }
            }
        }
        self.temp_file = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(self.sample_json_data, self.temp_file)
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_invalid_encoding(self):
        with self.assertRaises(ValueError) as cm:
            decode.main(self.temp_file.name, encoding='invalid_format', verbose=False)
        self.assertIn("unknown encoding", str(cm.exception))

    def test_incompatible_output_formats(self):
        with patch('sys.stderr', new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as cm:
                decode.main(self.temp_file.name, html=True, text=True, verbose=False)
            self.assertEqual(cm.exception.code, 1)

    def test_auto_extension_detection_all_types(self):
        extensions = [
            ('.jsonl', 'jsonl_out'),
            ('.md', 'md_out'),
            ('.mdt', 'md_table_out'),
            ('.sum', 'summary_out'),
            ('.summary', 'summary_out'),
            ('.tbl', 'table_out'),
            ('.table', 'table_out'),
            ('.mse-set', 'for_mse'),
            ('.deck', 'deck_out'),
            ('.dek', 'deck_out'),
            ('.xml', 'xml_out')
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            for ext, attr in extensions:
                out_path = os.path.join(tmp_dir, f"test_out{ext}")
                with patch('decode.jdecode.mtg_open_file', return_value=[]), \
                     patch('decode.utils.print_operation_summary'):
                    if ext in ['.mse-set']:
                        with patch('zipfile.ZipFile'), patch('os.path.isfile', return_value=False), \
                             patch('os.remove'), patch('builtins.open', unittest.mock.mock_open()):
                            decode.main('dummy.json', oname=out_path, verbose=False)
                    elif ext in ['.deck', '.dek']:
                        decode.main('dummy.json', oname=out_path, verbose=False)
                    else:
                        with patch('builtins.open', unittest.mock.mock_open()):
                            decode.main('dummy.json', oname=out_path, verbose=False)

    def test_stdout_export_json_jsonl_csv_summary_table_xml_md(self):
        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, json_out=True, verbose=False, quiet=True)
        res_json = json.loads(stdout_cap.getvalue())
        self.assertEqual(len(res_json), 2)
        names = [c['name'] for c in res_json]
        self.assertIn('Lightning Bolt', names)
        self.assertIn('Counterspell', names)

        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, jsonl_out=True, verbose=False, quiet=True)
        lines = [line for line in stdout_cap.getvalue().split('\n') if line.strip()]
        self.assertEqual(len(lines), 2)
        jsonl_names = [json.loads(line)['name'] for line in lines]
        self.assertIn('Lightning Bolt', jsonl_names)

        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, csv_out=True, verbose=False, quiet=True)
        csv_out = stdout_cap.getvalue()
        self.assertIn('Lightning Bolt', csv_out)
        self.assertIn('Counterspell', csv_out)

        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, table_out=True, verbose=False, quiet=True)
        tbl_out = stdout_cap.getvalue()
        self.assertIn('DECODED CARDS', tbl_out)
        self.assertIn('Lightning Bolt', tbl_out)

        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, summary_out=True, verbose=False, quiet=True)
        sum_out = stdout_cap.getvalue()
        self.assertIn('Lightning Bolt', sum_out)

        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, xml_out=True, verbose=False, quiet=True)
        xml_out = stdout_cap.getvalue()
        self.assertIn('<cockatrice_carddatabase version="4">', xml_out)
        self.assertIn('Lightning Bolt', xml_out)

        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, md_out=True, verbose=False, quiet=True)
        md_out = stdout_cap.getvalue()
        self.assertIn('Lightning Bolt', md_out)

        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, md_table_out=True, verbose=False, quiet=True)
        mdt_out = stdout_cap.getvalue()
        self.assertIn('| Name | Cost | CMC | Type | Stats | Rarity | Mechanics | Rules Text |', mdt_out)
        self.assertIn('Lightning Bolt', mdt_out)

    def test_file_export_formats(self):
        formats = [
            ('test.json', {'json_out': True}),
            ('test.jsonl', {'jsonl_out': True}),
            ('test.csv', {'csv_out': True}),
            ('test.sum', {'summary_out': True}),
            ('test.tbl', {'table_out': True}),
            ('test.md', {'md_out': True}),
            ('test.mdt', {'md_table_out': True}),
            ('test.xml', {'xml_out': True}),
            ('test.deck', {'deck_out': True}),
            ('test.txt', {'text': True}),
            ('test.html', {'html': True}),
        ]
        for filename, kwargs in formats:
            out_file = tempfile.NamedTemporaryFile('w', suffix=os.path.splitext(filename)[1], delete=False)
            out_file.close()
            try:
                decode.main(self.temp_file.name, oname=out_file.name, verbose=False, quiet=True, **kwargs)
                self.assertTrue(os.path.exists(out_file.name))
                self.assertGreater(os.path.getsize(out_file.name), 0)
            finally:
                if os.path.exists(out_file.name):
                    os.remove(out_file.name)

    def test_booster_box_decoding_headers(self):
        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, table_out=True, booster=1, verbose=False, quiet=True)
        out = stdout_cap.getvalue()
        self.assertIn('Pack', out)

        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, table_out=True, box=1, verbose=False, quiet=True)
        out = stdout_cap.getvalue()
        self.assertIn('Box', out)
        self.assertIn('Pack', out)

        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, booster=1, verbose=False, quiet=True)
        out = stdout_cap.getvalue()
        self.assertIn('== Pack', out)

        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, box=1, verbose=False, quiet=True)
        out = stdout_cap.getvalue()
        self.assertIn('=== Box', out)

    def test_cli_stdin_tty_check(self):
        test_args = ['decode.py', '-']
        stderr_cap = io.StringIO()
        with patch('sys.argv', test_args), \
             patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stderr', stderr_cap):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path('decode.py', run_name='__main__')
            self.assertEqual(cm.exception.code, 1)
        self.assertIn("No input file specified", stderr_cap.getvalue())

    def test_cli_mse_requires_outfile(self):
        test_args = ['decode.py', self.temp_file.name, '--mse']
        stderr_cap = io.StringIO()
        with patch('sys.argv', test_args), \
             patch('sys.stderr', stderr_cap):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path('decode.py', run_name='__main__')
            self.assertEqual(cm.exception.code, 2)
        self.assertIn("--mse requires an output filename", stderr_cap.getvalue())

    def test_cli_sample_shorthand(self):
        out_file = tempfile.NamedTemporaryFile('w', delete=False)
        out_file.close()
        test_args = ['decode.py', self.temp_file.name, out_file.name, '--sample', '1', '-q']
        try:
            with patch('sys.argv', test_args):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path('decode.py', run_name='__main__')
                self.assertEqual(cm.exception.code, 0)
            self.assertTrue(os.path.exists(out_file.name))
        finally:
            if os.path.exists(out_file.name):
                os.remove(out_file.name)

    def test_creativity_mode_text_md_html_forum(self):
        mock_nd = unittest.mock.MagicMock()
        mock_nd.nearest_par.side_effect = lambda names, n=3, quiet=False: [[(0.123, names[0])]] * len(names)
        mock_nd.names = {
            "lightning bolt": "Lightning Bolt",
            "counterspell": "Counterspell",
            "Lightning Bolt": "Lightning Bolt",
            "Counterspell": "Counterspell"
        }
        mock_nd.codes = {
            "lightning bolt": "TST/1.jpg",
            "counterspell": "TST/2.jpg",
            "Lightning Bolt": "TST/1.jpg",
            "Counterspell": "TST/2.jpg"
        }

        mock_cbow = unittest.mock.MagicMock()
        mock_cbow.nearest_par.side_effect = lambda cards, quiet=False: [[(0.456, cards[0].name)]] * len(cards)

        with patch('decode.Namediff', return_value=mock_nd), \
             patch('decode.CBOW', return_value=mock_cbow):

            # Plain text creativity mode
            stdout_cap = io.StringIO()
            with patch('sys.stdout', stdout_cap):
                decode.main(self.temp_file.name, creativity=True, verbose=False, quiet=True)
            txt_out = stdout_cap.getvalue()
            self.assertIn("~~ closest cards ~~", txt_out)
            self.assertIn("~~ closest names ~~", txt_out)

            # Markdown creativity mode
            stdout_cap = io.StringIO()
            with patch('sys.stdout', stdout_cap):
                decode.main(self.temp_file.name, creativity=True, md_out=True, verbose=False, quiet=True)
            md_out = stdout_cap.getvalue()
            self.assertIn("### ~~ closest cards ~~", md_out)

            # Forum creativity mode
            stdout_cap = io.StringIO()
            with patch('sys.stdout', stdout_cap):
                decode.main(self.temp_file.name, creativity=True, for_forum=True, verbose=False, quiet=True)
            forum_out = stdout_cap.getvalue()
            self.assertIn("[card]", forum_out)

            # HTML creativity mode
            stdout_cap = io.StringIO()
            with patch('sys.stdout', stdout_cap):
                decode.main(self.temp_file.name, creativity=True, html=True, verbose=False, quiet=True)
            html_out = stdout_cap.getvalue()
            self.assertIn("hover_img", html_out)

    def test_html_booster_output_nav_bar(self):
        mock_c1 = unittest.mock.MagicMock()
        mock_c1.pack_id = 1
        mock_c1.format.return_value = "<div>Card 1</div>"

        mock_c2 = unittest.mock.MagicMock()
        mock_c2.pack_id = 2
        mock_c2.format.return_value = "<div>Card 2</div>"

        with patch('decode.jdecode.mtg_open_file', return_value=[mock_c1, mock_c2]):
            stdout_cap = io.StringIO()
            with patch('sys.stdout', stdout_cap):
                decode.main('dummy.json', html=True, booster=2, verbose=False, quiet=True)
            out = stdout_cap.getvalue()
            self.assertIn('<ul id="nav-bar">', out)
            self.assertIn('<h2 id="pack_1"', out)
            self.assertIn('<h2 id="pack_2"', out)

    def test_html_color_segments_nav_bar(self):
        stdout_cap = io.StringIO()
        with patch('sys.stdout', stdout_cap):
            decode.main(self.temp_file.name, html=True, verbose=False, quiet=True)
        out = stdout_cap.getvalue()
        self.assertIn('<ul id="nav-bar">', out)
        self.assertIn('<h2 id=', out)

    def test_vdump_error_handling(self):
        mock_card_err = unittest.mock.MagicMock()
        mock_card_err.format.side_effect = Exception("Dump formatting error")

        with patch('decode.jdecode.mtg_open_file', return_value=[mock_card_err]):
            stdout_cap = io.StringIO()
            with patch('sys.stdout', stdout_cap):
                decode.main('dummy.json', vdump=True, verbose=False, quiet=True)
            out = stdout_cap.getvalue()
            self.assertIn("ERROR processing card: Dump formatting error", out)

    def test_mse_existing_set_file_safety(self):
        stderr_cap = io.StringIO()
        with patch('os.path.isfile', side_effect=lambda f: f == 'set'), \
             patch('sys.stderr', stderr_cap):
            decode.main(self.temp_file.name, oname='output.mse-set', for_mse=True, verbose=False, quiet=True)
        stderr_out = stderr_cap.getvalue()
        self.assertIn('ERROR: A file named "set" already exists', stderr_out)

    def test_export_card_exceptions_handling(self):
        mock_card_bad = unittest.mock.MagicMock()
        mock_card_bad.to_dict.side_effect = Exception("dict error")
        mock_card_bad.to_table_row.side_effect = Exception("table error")

        with patch('decode.jdecode.mtg_open_file', return_value=[mock_card_bad]):
            stdout_cap = io.StringIO()
            with patch('sys.stdout', stdout_cap):
                decode.main('dummy.json', json_out=True, verbose=False, quiet=True)
            self.assertEqual(stdout_cap.getvalue().strip(), "[]")

            stdout_cap = io.StringIO()
            with patch('sys.stdout', stdout_cap):
                decode.main('dummy.json', jsonl_out=True, verbose=False, quiet=True)
            self.assertEqual(stdout_cap.getvalue().strip(), "")

            stdout_cap = io.StringIO()
            with patch('sys.stdout', stdout_cap):
                decode.main('dummy.json', table_out=True, verbose=False, quiet=True)
            self.assertIn("DECODED CARDS", stdout_cap.getvalue())

if __name__ == '__main__':
    unittest.main()
