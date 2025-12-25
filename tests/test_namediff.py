import unittest
import os
import json
import tempfile
import difflib
import sys

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

import namediff
import cardlib

class TestNamediff(unittest.TestCase):
    def test_list_split(self):
        l = [1, 2, 3, 4, 5]
        splits = namediff.list_split(l, 2)
        self.assertEqual(len(splits), 2)
        self.assertEqual(splits[0], [1, 2, 3])
        self.assertEqual(splits[1], [4, 5])

        splits = namediff.list_split(l, 10)
        self.assertEqual(len(splits), 5)
        self.assertEqual(splits[0], [1])

    def test_list_split_empty(self):
        l = []
        splits = namediff.list_split(l, 2)
        self.assertEqual(splits, [])

    def test_list_split_zero_or_negative(self):
        """Test list_split with zero or negative number of chunks."""
        l = [1, 2, 3]

        # Test n=0
        splits = namediff.list_split(l, 0)
        self.assertEqual(len(splits), 1)
        self.assertEqual(splits[0], l)

        # Test n=-1
        splits = namediff.list_split(l, -1)
        self.assertEqual(len(splits), 1)
        self.assertEqual(splits[0], l)

    def test_f_nearest_per_thread(self):
        """Test the worker function for parallel processing."""
        worknames = ["apple", "banana"]
        candidates = ["apple", "apricot", "banana", "bandana"]
        # workitem tuple structure: (worknames, names, n)
        workitem = (worknames, candidates, 1)

        results = namediff.f_nearest_per_thread(workitem)

        self.assertEqual(len(results), 2)
        # Check result for "apple"
        self.assertEqual(len(results[0]), 1)
        self.assertEqual(results[0][0][1], "apple")
        self.assertEqual(results[0][0][0], 1.0)

        # Check result for "banana"
        self.assertEqual(len(results[1]), 1)
        self.assertEqual(results[1][0][1], "banana")
        self.assertEqual(results[1][0][0], 1.0)

    def test_list_flatten(self):
        l = [[1, 2], [3], [4, 5]]
        flat = namediff.list_flatten(l)
        self.assertEqual(flat, [1, 2, 3, 4, 5])

    def test_f_nearest(self):
        name = "Dragon"
        candidates = ["Dragon", "Drogon", "Wagon", "Apple"]
        matchers = [difflib.SequenceMatcher(b=c, autojunk=False) for c in candidates]

        result = namediff.f_nearest(name, matchers, n=3)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "Dragon")
        self.assertEqual(result[0][0], 1.0)

        name = "Drago"
        result = namediff.f_nearest(name, matchers, n=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][1], "Dragon")

    def test_namediff_integration(self):
        test_data = {
            "data": {
                "TST": {
                    "name": "Test Set",
                    "code": "TST",
                    "type": "core",
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
                            "text": "Freeze target."
                        }
                    ]
                }
            }
        }

        # Use tempfile.mkstemp for robust temp file creation
        fd, tmp_path = tempfile.mkstemp(suffix='.json', text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(test_data, f)

            nd = namediff.Namediff(verbose=False, json_fname=tmp_path)

            # Check names loaded (cardlib usually lowercases names)
            self.assertIn("fireball", nd.names)

            # Test nearest name
            res = nd.nearest("firebal", n=1)
            self.assertEqual(res[0][1], "fireball")

            # Test nearest card
            c = cardlib.Card({
                "name": "Fireball",
                "types": ["Sorcery"],
                "manaCost": "{R}",
                "text": "Deal damage."
            })

            res_card = nd.nearest_card(c, n=1)
            self.assertEqual(len(res_card), 1)

            # Test parallel versions
            # Force threads=1 to avoid overhead/issues, but test the function call
            res_par = nd.nearest_par(["firebal"], n=1, threads=1)
            self.assertEqual(len(res_par), 1)
            # result is list of lists of tuples: [[(score, name)], ...]
            self.assertEqual(res_par[0][0][1], "fireball")

            res_card_par = nd.nearest_card_par([c], n=1, threads=1)
            self.assertEqual(len(res_card_par), 1)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
