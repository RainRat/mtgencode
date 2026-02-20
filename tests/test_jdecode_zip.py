import json
import os
import sys
import unittest
import tempfile
import shutil
import zipfile
import io
from unittest.mock import patch
from io import StringIO

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode, utils, cardlib

class TestJDecodeZip(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.zip_path = os.path.join(self.test_dir, "test_archive.zip")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_mtg_open_file_zip_all_formats(self):
        # Prepare contents
        json_content = {
            "data": {
                "Z": {
                    "code": "Z", "name": "ZipSet", "type": "expansion",
                    "cards": [{"name": "JsonCard", "types": ["Creature"], "rarity": "Common", "power": "1", "toughness": "1"}]
                }
            }
        }
        json_content2 = {
            "data": {
                "Z2": {
                    "code": "Z2", "name": "ZipSet2", "type": "expansion",
                    "cards": [{"name": "JsonCard", "types": ["Creature"], "rarity": "Uncommon", "power": "2", "toughness": "2"}]
                }
            }
        }
        csv_content = "name,type,rarity\nCsvCard,Land,Common"
        jsonl_content = json.dumps({"name": "JsonlCard", "types": ["Instant"], "rarity": "Uncommon"})
        txt_content = "|5sorcery|4|6|7|8|9|3{R}|0O|1TxtCard|"

        # MSE content with PW loyalty cost
        mse_set_content = """card:
\tname: MseCard
\tsuper type: Legendary Planeswalker
\tloyalty: 3
\tloyalty cost 1: +1
\trule text: First ability.
"""

        # Create the nested MSE zip
        mse_zip_io = io.BytesIO()
        with zipfile.ZipFile(mse_zip_io, 'w') as mse_zf:
            mse_zf.writestr('set', mse_set_content)
        mse_zip_data = mse_zip_io.getvalue()

        # Create the main ZIP archive
        with zipfile.ZipFile(self.zip_path, 'w') as zf:
            zf.writestr('cards1.json', json.dumps(json_content))
            zf.writestr('cards2.json', json.dumps(json_content2))
            zf.writestr('cards.csv', csv_content)
            zf.writestr('cards.jsonl', jsonl_content)
            zf.writestr('cards.txt', txt_content)
            zf.writestr('cards.mse-set', mse_zip_data)
            # Add a directory entry to ensure it's ignored (handled by not f.endswith('/'))
            zf.writestr('dir/', '')

        # Capture stderr to verify verbose output and cover verbose lines
        with patch('sys.stderr', new=StringIO()) as fake_err:
            cards = jdecode.mtg_open_file(self.zip_path, verbose=True)
            err_output = fake_err.getvalue()

        # Verify verbose messages
        self.assertIn(f"Opening ZIP archive {self.zip_path}...", err_output)
        self.assertIn("Loading cards1.json from ZIP...", err_output)
        self.assertIn("Loading cards2.json from ZIP...", err_output)
        self.assertIn("Loading cards.csv from ZIP...", err_output)
        self.assertIn("Loading cards.jsonl from ZIP...", err_output)
        self.assertIn("Loading cards.txt from ZIP...", err_output)
        self.assertIn("Loading cards.mse-set from ZIP...", err_output)

        # Verify cards were loaded
        names = sorted([c.name.lower() for c in cards])
        self.assertIn("jsoncard", names)
        # We now have two "jsoncard" entries in aggregated_srcs, but mtg_open_file
        # (via _process_json_srcs) picks the best one for each name.
        self.assertEqual(names.count("jsoncard"), 1)
        self.assertIn("csvcard", names)
        self.assertIn("jsonlcard", names)
        self.assertIn("txtcard", names)
        self.assertIn("msecard", names)
        self.assertEqual(len(cards), 5)

        # Specifically check the MSE card for loyalty
        mse_card = next(c for c in cards if c.name.lower() == "msecard")
        self.assertEqual(utils.from_unary(mse_card.loyalty), "3")

if __name__ == '__main__':
    unittest.main()
