import os
import sys
import tempfile
import json
import unittest
import runpy
from unittest.mock import patch

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import encode

class TestEncodeOutfile(unittest.TestCase):
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
                        }
                    ]
                }
            }
        }
        self.temp_json = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(self.sample_json_data, self.temp_json)
        self.temp_json.close()

    def tearDown(self):
        if os.path.exists(self.temp_json.name):
            os.remove(self.temp_json.name)

    def test_encode_outfile_flag(self):
        target_outfile = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False)
        target_outfile.close()
        os.remove(target_outfile.name)

        try:
            test_args = ['encode.py', self.temp_json.name, '-o', target_outfile.name, '-q', '-s']
            with patch('sys.argv', test_args):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path('encode.py', run_name='__main__')
                self.assertEqual(cm.exception.code, 0)

            self.assertTrue(os.path.exists(target_outfile.name))
            with open(target_outfile.name, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn("opt", content.lower())
        finally:
            if os.path.exists(target_outfile.name):
                os.remove(target_outfile.name)

    def test_encode_outfile_flag_overrides_positional(self):
        positional_outfile = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False)
        positional_outfile.close()
        os.remove(positional_outfile.name)

        override_outfile = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False)
        override_outfile.close()
        os.remove(override_outfile.name)

        try:
            test_args = ['encode.py', self.temp_json.name, positional_outfile.name, '-o', override_outfile.name, '-q', '-s']
            with patch('sys.argv', test_args):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path('encode.py', run_name='__main__')
                self.assertEqual(cm.exception.code, 0)

            self.assertTrue(os.path.exists(override_outfile.name))
            self.assertFalse(os.path.exists(positional_outfile.name))
            with open(override_outfile.name, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn("opt", content.lower())
        finally:
            if os.path.exists(positional_outfile.name):
                os.remove(positional_outfile.name)
            if os.path.exists(override_outfile.name):
                os.remove(override_outfile.name)

    def test_encode_short_sample_flag(self):
        target_outfile = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False)
        target_outfile.close()
        os.remove(target_outfile.name)

        try:
            test_args = ['encode.py', self.temp_json.name, '-o', target_outfile.name, '-N', '1', '-q', '-s']
            with patch('sys.argv', test_args):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path('encode.py', run_name='__main__')
                self.assertEqual(cm.exception.code, 0)

            self.assertTrue(os.path.exists(target_outfile.name))
        finally:
            if os.path.exists(target_outfile.name):
                os.remove(target_outfile.name)

if __name__ == '__main__':
    unittest.main()
