import sys
import os
import unittest
import tempfile
import shutil
import json
from unittest.mock import patch
from io import StringIO

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode, utils, cardlib

class TestJDecodeFile(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.report_file = os.path.join(self.test_dir, 'report.txt')

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_json(self, filename, content):
        path = os.path.join(self.test_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(content, f)
        return path

    def create_text(self, filename, content):
        path = os.path.join(self.test_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_open_directory(self):
        # Create two JSON files in the directory
        # Card A needs PT to be valid as a creature
        data1 = {
            "data": {
                "SET1": {
                    "code": "SET1", "name": "Set 1", "type": "expansion",
                    "cards": [{"name": "Card A", "types": ["Creature"], "rarity": "Common", "number": "1", "power": "1", "toughness": "1"}]
                }
            }
        }
        data2 = {
             "data": {
                "SET2": {
                    "code": "SET2", "name": "Set 2", "type": "expansion",
                    "cards": [{"name": "Card B", "types": ["Instant"], "rarity": "Uncommon", "number": "1"}]
                }
            }
        }
        self.create_json("set1.json", data1)
        self.create_json("set2.json", data2)

        # Also create a non-json file to ensure it's ignored
        self.create_text("ignore.txt", "garbage")

        cards = jdecode.mtg_open_file(self.test_dir, verbose=False)

        card_names = sorted([c.name for c in cards])
        self.assertEqual(card_names, ["card a", "card b"])

    def test_open_stdin(self):
        # Mock stdin with encoded card text
        # Must use labeled format because mtg_open_file uses Card() default which is labeled
        # Format: |5creature|4|6|7|81/1|9|3{RR}|0O|1goblin|

        card_text = "|5creature|4|6|7|8&/&|9|3{RR}|0O|1goblin|"

        with patch('sys.stdin', StringIO(card_text)):
             cards = jdecode.mtg_open_file('-', verbose=False)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, 'goblin')

    def test_open_text_file(self):
        # Encoded string for Brainstorm: Instant, Blue, Common
        # Card.encode: |5instant|4|6|7|8|9|3{UU}|0O|1brainstorm|
        card_text = "|5instant|4|6|7|8|9|3{UU}|0O|1brainstorm|"
        path = self.create_text("cards.txt", card_text)

        cards = jdecode.mtg_open_file(path, verbose=False)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, 'brainstorm')

    def test_report_file_json(self):
        # Test that unparsed cards from JSON are written to report file
        # A card without 'types' will fail parsing in Cardlib (parsed=False)
        data = {
            "data": {
                "FAIL": {
                    "code": "FAIL", "name": "Fail Set", "type": "expansion",
                    "cards": [
                        {"name": "Good Card", "types": ["Land"], "rarity": "Common"},
                        {"name": "Bad Card", "rarity": "Common"} # Missing types
                    ]
                }
            }
        }
        path = self.create_json("fail.json", data)

        # Capture stderr to avoid clutter
        with patch('sys.stderr', new=StringIO()):
             cards = jdecode.mtg_open_file(path, verbose=False, report_file=self.report_file)

        # Check valid cards
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, "good card")

        # Check report file
        self.assertTrue(os.path.exists(self.report_file))
        with open(self.report_file, 'r', encoding='utf-8') as f:
            report_content = f.read()
            # The report should contain JSON for the bad card
            self.assertIn('"name": "Bad Card"', report_content)

    def test_report_file_text(self):
        # Test that invalid cards from text file are written to report file

        # Valid: |5creature|4|6|7|8&/&|9|3{GG}|0O|1elf|
        valid_line = "|5creature|4|6|7|8&/&|9|3{GG}|0O|1elf|"
        # Invalid: Parsed (has fields) but invalid (missing name/types)
        invalid_line = "|0O|"

        content = valid_line + utils.cardsep + invalid_line

        path = self.create_text("mixed.txt", content)

        with patch('sys.stderr', new=StringIO()):
            cards = jdecode.mtg_open_file(path, verbose=False, report_file=self.report_file)

        # mtg_open_file for text input returns ALL parsed cards (unlike JSON which filters valid)
        # However, _check_parsing_quality runs at end, which might drop cards?
        # No, _check_parsing_quality just counts stats and warns, returns cards.

        self.assertEqual(len(cards), 2)
        self.assertTrue(cards[0].valid)
        self.assertFalse(cards[1].valid)

        # Check report file
        with open(self.report_file, 'r', encoding='utf-8') as f:
            report_content = f.read()
            self.assertIn(invalid_line, report_content)
            self.assertNotIn(valid_line, report_content)

if __name__ == '__main__':
    unittest.main()
