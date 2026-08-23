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

import scripts.mtg_validate as mtg_validate

class TestMTGValidateDryRun(unittest.TestCase):
    def test_dry_run_direct(self):
        sample_json_data = {
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
                            "name": "Bear",
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
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(sample_json_data, f)
            tmp_input = f.name

        out_report = tmp_input + ".report"

        try:
            for flag in ['--dry-run', '--preview', '-p']:
                test_args = ['scripts/mtg_validate.py', tmp_input, out_report, flag, '-q']
                stdout_capture = io.StringIO()
                with patch('sys.argv', test_args), patch('sys.stdout', stdout_capture):
                    with self.assertRaises(SystemExit) as cm:
                        runpy.run_module('scripts.mtg_validate', run_name='__main__')
                    self.assertEqual(cm.exception.code, 0)

                output = stdout_capture.getvalue()
                self.assertIn("Dry Run Summary", output)
                self.assertIn("2 card(s) validated", output)
                self.assertIn("Valid Cards: 2 (100.0%)", output)
                self.assertIn("opt", output.lower())
                self.assertFalse(os.path.exists(out_report), f"Output report file {out_report} should not exist during dry run")

        finally:
            if os.path.exists(tmp_input):
                os.remove(tmp_input)
            if os.path.exists(out_report):
                os.remove(out_report)

if __name__ == '__main__':
    unittest.main()
