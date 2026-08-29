import os
import sys
import tempfile
import io
import json
import unittest
import runpy
from unittest.mock import patch

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import encode

class TestEncodeDryRun(unittest.TestCase):
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

    def test_encode_main_dry_run_direct(self):
        stdout_capture = io.StringIO()
        with patch('sys.stdout', stdout_capture):
            encode.main(self.temp_file.name, dry_run=True, verbose=False)

        output = stdout_capture.getvalue()
        self.assertIn("Dry Run Summary: 2 card(s) matched for encoding.", output)
        self.assertIn("Encoding format: 'std'", output)
        self.assertIn("Set Code Breakdown:", output)
        self.assertIn("TST: 2 card(s)", output)
        self.assertIn("Opt", output)
        self.assertIn("Grizzly Bears", output)

    def test_encode_cli_dry_run_flags(self):
        target_outfile = self.temp_file.name + ".encoded.txt"
        try:
            for flag in ['-p', '--preview', '--dry-run']:
                stdout_capture = io.StringIO()
                test_args = ['encode.py', self.temp_file.name, target_outfile, flag, '-q']
                with patch('sys.argv', test_args), patch('sys.stdout', stdout_capture):
                    with self.assertRaises(SystemExit) as cm:
                        runpy.run_path('encode.py', run_name='__main__')
                    self.assertEqual(cm.exception.code, 0)

                output = stdout_capture.getvalue()
                self.assertIn("Dry Run Summary: 2 card(s) matched for encoding.", output)
                self.assertIn("Encoding format: 'std'", output)
                self.assertIn("Sample Preview", output)
                self.assertFalse(os.path.exists(target_outfile), f"Target output file {target_outfile} should not be created during dry run")
        finally:
            if os.path.exists(target_outfile):
                os.remove(target_outfile)

if __name__ == '__main__':
    unittest.main()
