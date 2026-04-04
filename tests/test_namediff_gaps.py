import unittest
import os
import json
import tempfile
import sys
from unittest.mock import patch, MagicMock

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

import namediff
import cardlib
import utils

class TestNamediffGaps(unittest.TestCase):
    def test_f_nearest_no_matchers(self):
        """Test f_nearest with empty matchers list (line 40)."""
        self.assertEqual(namediff.f_nearest("name", [], 3), [])

    def test_namediff_verbose_and_duplicates(self):
        """Test Namediff with verbose=True and duplicate card names (lines 63, 66, 74-75, 104-105, 113)."""
        # Trigger duplicate name branch (line 74-75) via bside with same name
        test_data = {
            "data": {
                "TST": {
                    "name": "Test Set",
                    "code": "TST",
                    "type": "core",
                    "cards": [
                        {
                            "name": "Fire",
                            "number": "1a",
                            "types": ["Instant"],
                            "bside": {
                                "name": "Fire", # Same name as parent
                                "number": "1b",
                                "types": ["Instant"]
                            }
                        }
                    ]
                }
            }
        }

        fd, tmp_path = tempfile.mkstemp(suffix='.json', text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(test_data, f)

            # Capture stdout to verify verbose logging
            from io import StringIO
            captured_output = StringIO()
            original_stdout = sys.stdout
            try:
                sys.stdout = captured_output
                nd = namediff.Namediff(verbose=True, json_fname=tmp_path)
            finally:
                sys.stdout = original_stdout

            output = captured_output.getvalue()

            self.assertIn("Setting up namediff...", output)
            self.assertIn("Reading names from:", output)
            self.assertIn("Duplicate name fire, ignoring.", output)
            self.assertIn("Read 1 unique cardnames", output)
            self.assertIn("Building SequenceMatcher objects.", output)
            self.assertIn("... Done.", output)

            self.assertEqual(len(nd.names), 1)
            self.assertIn("fire", nd.names)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_namediff_codes_mapping(self):
        """Test that codes are correctly mapped (line 82)."""
        # Line 82: if jcode and jnum: self.codes[name] = jcode + '/' + jnum + '.jpg'

        # We need the cards to be INSIDE a set in MTGJSON format
        # for jdecode to set the magicCardsInfoCode on each card.
        test_data = {
            "data": {
                "TST": {
                    "name": "Test Set",
                    "code": "TST",
                    "type": "core",
                    "magicCardsInfoCode": "tstcode",
                    "cards": [
                        {
                            "name": "Fireball",
                            "number": "1",
                            "types": ["Sorcery"]
                        }
                    ]
                }
            }
        }

        fd, tmp_path = tempfile.mkstemp(suffix='.json', text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(test_data, f)

            nd = namediff.Namediff(verbose=False, json_fname=tmp_path)

            self.assertIn("fireball", nd.codes)
            self.assertEqual(nd.codes["fireball"], "tstcode/1.jpg")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_nearest_par_tqdm_fallback(self):
        """Test nearest_par when tqdm is not available (line 131)."""
        test_data = {
            "data": {
                "TST": {
                    "name": "Test Set",
                    "code": "TST",
                    "type": "core",
                    "cards": [
                        {"name": "Fireball", "number": "1", "types": ["Sorcery"]}
                    ]
                }
            }
        }

        fd, tmp_path = tempfile.mkstemp(suffix='.json', text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(test_data, f)

            nd = namediff.Namediff(verbose=False, json_fname=tmp_path)

            # Refined mock for tqdm ImportError
            with patch.dict(sys.modules, {'tqdm': None}):
                res = nd.nearest_par(["firebal"], n=1, threads=1)
                self.assertEqual(len(res), 1)
                self.assertEqual(res[0][0][1], "fireball")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
