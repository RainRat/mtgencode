import json
import os
import sys
import unittest
import tempfile
import shutil
import zipfile
from unittest.mock import patch
from io import StringIO

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode, utils, cardlib

class TestJDecodeGaps(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_mtg_open_mse_content_advanced(self):
        # Covers:
        # - multi-line rule text (same line and next line)
        # - split cards (name 2, etc.)
        # - duplicate names
        # - defense field
        mse_content = """card:
	name: Split Front
	casting cost: 1R
	rule text: First line
		Second line
	name 2: Split Back
	casting cost 2: 1B
	rule text 2: Back line
	defense: 5
card:
	name: Split Front
	casting cost: 1R
	rule text: Duplicate
"""
        srcs, _ = jdecode.mtg_open_mse_content(mse_content)

        self.assertIn("split front", srcs)
        self.assertEqual(len(srcs["split front"]), 2)

        card1 = srcs["split front"][0]
        self.assertEqual(card1["text"], "First line\nSecond line")
        self.assertEqual(card1["defense"], "5")

        self.assertIn(utils.json_field_bside, card1)
        bside = card1[utils.json_field_bside]
        self.assertEqual(bside["name"], "Split Back")
        self.assertEqual(bside["manaCost"], "{1}{B}")
        self.assertEqual(bside["text"], "Back line")

    def test_mtg_open_json_obj_duplicates(self):
        # Covers duplicate card names in MTGJSON and list formats

        # 1. MTGJSON format
        mtgjson_data = {
            "data": {
                "TEST": {
                    "code": "TEST", "name": "Test Set", "type": "expansion",
                    "cards": [
                        {"name": "Dup", "number": "1", "rarity": "Common"},
                        {"name": "Dup", "number": "2", "rarity": "Uncommon"}
                    ]
                }
            }
        }
        allcards, _ = jdecode.mtg_open_json_obj(mtgjson_data)
        self.assertEqual(len(allcards["dup"]), 2)

        # 2. List format
        list_data = [
            {"name": "ListDup", "rarity": "Common"},
            {"name": "ListDup", "rarity": "Rare"}
        ]
        allcards, _ = jdecode.mtg_open_json_obj(list_data)
        self.assertEqual(len(allcards["listdup"]), 2)

    def test_mtg_open_jsonl_invalid(self):
        # Covers JSONDecodeError
        jsonl_content = '{"name": "Valid"}\ninvalid json\n{"name": "Also Valid"}'
        allcards, _ = jdecode.mtg_open_jsonl_content(jsonl_content)
        self.assertEqual(len(allcards), 2)
        self.assertIn("valid", allcards)
        self.assertIn("also valid", allcards)

    def test_mtg_open_mse_invalid_zip(self):
        # Covers zip file missing 'set' file
        mse_path = os.path.join(self.test_dir, "empty.mse-set")
        with zipfile.ZipFile(mse_path, 'w') as zf:
            zf.writestr('not_set', 'content')

        with patch('sys.stderr', new=StringIO()) as fake_err:
            allcards, _ = jdecode.mtg_open_mse(mse_path, verbose=True)
            self.assertEqual(allcards, {})
            self.assertIn("Warning: 'set' file not found", fake_err.getvalue())

    def test_mtg_open_file_directory_all_types(self):
        # Covers directory scanning with all supported types

        # 1. JSON
        json_path = os.path.join(self.test_dir, "test.json")
        with open(json_path, 'w') as f:
            json.dump({"data": {"S": {"code":"S", "name":"S", "type":"expansion", "cards":[{"name":"J","types":["Land"],"rarity":"C"}]}}}, f)

        # 2. CSV
        csv_path = os.path.join(self.test_dir, "test.csv")
        with open(csv_path, 'w') as f:
            f.write("name,type,rarity\nC,Land,C")

        # 3. JSONL
        jsonl_path = os.path.join(self.test_dir, "test.jsonl")
        with open(jsonl_path, 'w') as f:
            f.write(json.dumps({"name":"L","types":["Land"],"rarity":"C"}))

        # 4. MSE
        mse_path = os.path.join(self.test_dir, "test.mse-set")
        with zipfile.ZipFile(mse_path, 'w') as zf:
            zf.writestr('set', 'card:\n\tname: M\n\tsuper type: Land\n\trarity: common')

        # 5. TXT (Encoded)
        txt_path = os.path.join(self.test_dir, "test.txt")
        with open(txt_path, 'w') as f:
            # Valid Land: |5land|1T|
            f.write("|5land|1T|")

        cards = jdecode.mtg_open_file(self.test_dir, verbose=True)
        names = sorted([c.name.lower() for c in cards])
        # Note: CSV results are also returned
        self.assertIn("j", names)
        self.assertIn("c", names)
        self.assertIn("l", names)
        self.assertIn("m", names)
        self.assertIn("t", names)

    def test_mtg_open_file_stdin_verbose(self):
        # Covers stdin format detection with verbose=True

        # 1. JSON
        with patch('sys.stdin', StringIO(json.dumps([{"name":"J","types":["Land"],"rarity":"C"}]))), \
             patch('sys.stderr', new=StringIO()) as fake_err:
            jdecode.mtg_open_file('-', verbose=True)
            self.assertIn("Detected JSON input from stdin", fake_err.getvalue())

        # 2. JSONL
        jsonl_content = json.dumps({"name":"L","types":["Land"],"rarity":"C"}) + "\n" + json.dumps({"name":"L2","types":["Land"]})
        with patch('sys.stdin', StringIO(jsonl_content)), \
             patch('sys.stderr', new=StringIO()) as fake_err:
            # We need to make sure it doesn't parse as regular JSON
            jdecode.mtg_open_file('-', verbose=True)
            self.assertIn("Detected JSONL input from stdin", fake_err.getvalue())

        # 3. CSV
        csv_content = "name,type,rarity\nC,Land,C"
        with patch('sys.stdin', StringIO(csv_content)), \
             patch('sys.stderr', new=StringIO()) as fake_err:
            jdecode.mtg_open_file('-', verbose=True)
            self.assertIn("Detected CSV input from stdin", fake_err.getvalue())

    def test_mtg_open_file_unparsed_report(self):
        # Covers reporting unparsed cards from encoded text to a file
        report_path = os.path.join(self.test_dir, "report.txt")
        # An unparsed card (no field separators that make sense)
        content = "This is not a card"
        txt_path = os.path.join(self.test_dir, "bad.txt")
        with open(txt_path, 'w') as f:
            f.write(content)

        # mtg_open_file for txt files doesn't fail parse easily unless it lacks separators
        # Actually Card constructor always returns something if there is content.
        # But if it doesn't match the expected format, it might have card.parsed = False.

        # Let's try a format it doesn't understand at all.
        content = "||||||||||||||||||||" # Too many fields
        with open(txt_path, 'w') as f:
            f.write(content)

        with patch('sys.stderr', new=StringIO()):
            jdecode.mtg_open_file(txt_path, report_file=report_path)

        self.assertTrue(os.path.exists(report_path))
        with open(report_path, 'r') as f:
            self.assertIn(content, f.read())

if __name__ == '__main__':
    unittest.main()
