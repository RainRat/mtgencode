import unittest
import os
import json
import tempfile
import difflib
import sys
import io
from unittest.mock import patch

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

import namediff
import cardlib

class TestNamediffGaps(unittest.TestCase):
    def test_f_nearest_with_empty_matchers(self):
        self.assertEqual(namediff.f_nearest("apple", [], 3), [])

    def test_f_nearest_exact_match_priority(self):
        candidates = ["apple", "apricot", "banana"]
        matchers = [difflib.SequenceMatcher(b=c, autojunk=False) for c in candidates]

        res = namediff.f_nearest("apple", matchers, n=3)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], "apple")
        self.assertEqual(res[0][0], 1.0)

    def test_namediff_initialization_and_verbose_output(self):
        test_data = {
            "data": {
                "SET1": {
                    "name": "Set 1",
                    "code": "S1",
                    "type": "core",
                    "magicCardsInfoCode": "s1code",
                    "cards": [
                        {
                            "name": "Fireball",
                            "number": "1",
                            "types": ["Sorcery"],
                            "manaCost": "{R}",
                            "text": "Deal damage."
                        },
                        {
                            "name": "Iceball",
                            "number": "2",
                            "types": ["Sorcery"],
                            "manaCost": "{U}",
                            "text": "Frozen."
                        }
                    ]
                }
            }
        }

        fd, tmp_path = tempfile.mkstemp(suffix='.json', text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(test_data, f)

            captured_output = io.StringIO()
            with patch('sys.stdout', new=captured_output):
                nd = namediff.Namediff(verbose=True, json_fname=tmp_path)

            output = captured_output.getvalue()

            self.assertIn("Setting up namediff...", output)
            self.assertIn("Reading names from:", output)
            self.assertIn("Read 2 unique cardnames", output)
            self.assertIn("Building SequenceMatcher objects.", output)
            self.assertIn("... Done.", output)

            self.assertEqual(nd.codes["fireball"], "s1code/1.jpg")

            with patch('jdecode.mtg_open_json') as mock_open:
                jcard = {
                    "name": "Fireball",
                    "number": "1",
                    "types": ["Sorcery"],
                    "magicCardsInfoCode": "s1code",
                    "bside": {
                        "name": "Fireball",
                        "number": "1b",
                        "types": ["Sorcery"]
                    }
                }
                mock_open.return_value = ({"fireball": [jcard]}, set())

                captured_output2 = io.StringIO()
                with patch('sys.stdout', new=captured_output2):
                    namediff.Namediff(verbose=True, json_fname="dummy.json")
                output2 = captured_output2.getvalue()
                self.assertIn("Duplicate name fireball, ignoring.", output2)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_nearest_and_nearest_card_search(self):
        test_data = {
            "data": {
                "S1": {
                    "name": "S1", "code": "S1", "type": "core",
                    "cards": [{"name": "Fireball", "types": ["Sorcery"], "manaCost": "{R}"}]
                }
            }
        }
        fd, tmp_path = tempfile.mkstemp(suffix='.json', text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(test_data, f)
            nd = namediff.Namediff(verbose=False, json_fname=tmp_path)

            self.assertEqual(nd.nearest("firebal", n=1)[0][1], "fireball")

            c = cardlib.Card({"name": "Fireball", "types": ["Creature"], "manaCost": "{R}", "power":"1", "toughness":"1"})
            self.assertEqual(nd.nearest_card(c, n=1)[0][1], nd.cardstrings["fireball"])

            res = nd.nearest_card_par([c], n=1, threads=1)
            self.assertEqual(res[0][0][1], nd.cardstrings["fireball"])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_list_split_logic_with_various_inputs(self):
        self.assertEqual(namediff.list_split([], 3), [])
        self.assertEqual(namediff.list_split([1,2], 0), [[1,2]])
        self.assertEqual(namediff.list_split([1,2,3], 2), [[1,2], [3]])

    def test_nearest_par_with_tqdm_import_error(self):
        test_data = {
            "data": {
                "TST": {
                    "name": "Test Set",
                    "code": "TST",
                    "type": "core",
                    "cards": [
                        {"name": "Apple", "types": ["Creature"], "manaCost": "{G}"}
                    ]
                }
            }
        }

        fd, tmp_path = tempfile.mkstemp(suffix='.json', text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(test_data, f)

            nd = namediff.Namediff(verbose=False, json_fname=tmp_path)

            with patch.dict('sys.modules', {'tqdm': None}):
                res = nd.nearest_par(["appl"], n=1, threads=1)
                self.assertEqual(len(res), 1)
                self.assertEqual(res[0][0][1], "apple")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
