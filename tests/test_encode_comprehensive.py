import os
import sys
import tempfile
import io
import json
import unittest
import runpy
from unittest.mock import patch, MagicMock

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import encode

class TestEncodeComprehensive(unittest.TestCase):
    def setUp(self):
        self.sample_json_data = {
            "data": {
                "TST": {
                    "code": "TST",
                    "name": "Test Set",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Opt",
                            "manaCost": "{U}",
                            "types": ["Instant"],
                            "text": "Scry 1. Draw a card.",
                            "setCode": "TST"
                        },
                        {
                            "name": "Grizzly Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "subtypes": ["Bear"],
                            "power": "2",
                            "toughness": "2",
                            "setCode": "TST"
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

    def test_invalid_encoding_raises_value_error(self):
        with self.assertRaises(ValueError) as cm:
            encode.main(self.temp_file.name, encoding='invalid_fmt', verbose=False)
        self.assertIn("unknown encoding: invalid_fmt", str(cm.exception))

    def test_encode_to_outfile(self):
        outfile = self.temp_file.name + ".out.txt"
        try:
            encode.main(self.temp_file.name, oname=outfile, verbose=False, quiet=True)
            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn("opt", content.lower())
            self.assertIn("grizzly bears", content.lower())
        finally:
            if os.path.exists(outfile):
                os.remove(outfile)

    def test_encode_vector_format(self):
        outfile = self.temp_file.name + ".vec.txt"
        try:
            encode.main(self.temp_file.name, oname=outfile, encoding='vec', verbose=False, quiet=True)
            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertTrue(len(content) > 0)
        finally:
            if os.path.exists(outfile):
                os.remove(outfile)

    def test_verbose_logging_and_sorting_limit(self):
        outfile = self.temp_file.name + ".verbose.txt"
        stderr_capture = io.StringIO()
        try:
            with patch('sys.stderr', stderr_capture):
                encode.main(
                    self.temp_file.name,
                    oname=outfile,
                    verbose=True,
                    sort='name',
                    randomize=True,
                    nolabel=True,
                    nolinetrans=True,
                    limit=1,
                    quiet=True
                )
            stderr_out = stderr_capture.getvalue()
            self.assertIn("Preparing to encode:", stderr_out)
            self.assertIn("Sorting cards by name.", stderr_out)
            self.assertIn("Randomizing order of symbols in manacosts.", stderr_out)
            self.assertIn("NOT labeling fields", stderr_out)
            self.assertIn("NOT using line reordering transformations", stderr_out)
            self.assertIn("Writing output to:", stderr_out)

            with open(outfile, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            self.assertTrue(len(lines) > 0)
        finally:
            if os.path.exists(outfile):
                os.remove(outfile)

    def test_verbose_default_random_order(self):
        outfile = self.temp_file.name + ".rand.txt"
        stderr_capture = io.StringIO()
        try:
            with patch('sys.stderr', stderr_capture):
                encode.main(
                    self.temp_file.name,
                    oname=outfile,
                    verbose=True,
                    nolabel=False,
                    quiet=True
                )
            stderr_out = stderr_capture.getvalue()
            self.assertIn("Randomizing order of cards", stderr_out)
        finally:
            if os.path.exists(outfile):
                os.remove(outfile)

    def test_writecards_exception_handling(self):
        mock_card_fail = MagicMock()
        mock_card_fail.encode.side_effect = Exception("Encode error")

        mock_card_pass = MagicMock()
        mock_card_pass.encode.return_value = "encoded_card"

        with patch('jdecode.mtg_open_file', return_value=[mock_card_fail, mock_card_pass]):
            out = io.StringIO()
            stderr_out = io.StringIO()
            with patch('sys.stdout', out), patch('sys.stderr', stderr_out):
                encode.main(self.temp_file.name, verbose=False, quiet=True)

            output = out.getvalue()
            self.assertIn("encoded_card", output)

    def test_cli_execution_with_arguments(self):
        outfile = self.temp_file.name + ".cli.txt"
        test_args = [
            'encode.py',
            self.temp_file.name,
            outfile,
            '--encoding', 'vec',
            '--sample', '1',
            '--sort', 'name',
            '--reverse',
            '--nolabel',
            '--nolinetrans',
            '-v',
            '-q'
        ]
        try:
            with patch('sys.argv', test_args):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path('encode.py', run_name='__main__')
                self.assertEqual(cm.exception.code, 0)
            self.assertTrue(os.path.exists(outfile))
        finally:
            if os.path.exists(outfile):
                os.remove(outfile)

    def test_cli_interactive_missing_default_infile(self):
        test_args = ['encode.py', '-']

        def custom_exists(path):
            if path.endswith('AllPrintings.json'):
                return False
            return True

        with patch('sys.argv', test_args), \
             patch('sys.stdin.isatty', return_value=True), \
             patch('os.path.exists', side_effect=custom_exists), \
             patch('sys.stderr', io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path('encode.py', run_name='__main__')
            self.assertEqual(cm.exception.code, 1)

if __name__ == '__main__':
    unittest.main()
