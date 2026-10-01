import os
import sys
import tempfile
import json
import unittest
import runpy
from unittest.mock import patch

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import decode

class TestDecodeOutfile(unittest.TestCase):
    def setUp(self):
        # Create a temp encoded file
        self.temp_encoded = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8')
        self.temp_encoded.write("5instant|3{U}|9scry 1. draw a card.|1opt|\n\n")
        self.temp_encoded.close()

    def tearDown(self):
        if os.path.exists(self.temp_encoded.name):
            os.remove(self.temp_encoded.name)

    def test_decode_outfile_flag_json(self):
        target_outfile = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
        target_outfile.close()
        os.remove(target_outfile.name)

        try:
            test_args = ['decode.py', self.temp_encoded.name, '-o', target_outfile.name, '-q']
            with patch('sys.argv', test_args):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path('decode.py', run_name='__main__')
                self.assertEqual(cm.exception.code, 0)

            self.assertTrue(os.path.exists(target_outfile.name))
            with open(target_outfile.name, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['name'], 'Opt')
        finally:
            if os.path.exists(target_outfile.name):
                os.remove(target_outfile.name)

    def test_decode_outfile_flag_overrides_positional(self):
        positional_outfile = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False)
        positional_outfile.close()
        os.remove(positional_outfile.name)

        override_outfile = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
        override_outfile.close()
        os.remove(override_outfile.name)

        try:
            test_args = ['decode.py', self.temp_encoded.name, positional_outfile.name, '-o', override_outfile.name, '-q']
            with patch('sys.argv', test_args):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path('decode.py', run_name='__main__')
                self.assertEqual(cm.exception.code, 0)

            self.assertTrue(os.path.exists(override_outfile.name))
            self.assertFalse(os.path.exists(positional_outfile.name))
            with open(override_outfile.name, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['name'], 'Opt')
        finally:
            if os.path.exists(positional_outfile.name):
                os.remove(positional_outfile.name)
            if os.path.exists(override_outfile.name):
                os.remove(override_outfile.name)

if __name__ == '__main__':
    unittest.main()
