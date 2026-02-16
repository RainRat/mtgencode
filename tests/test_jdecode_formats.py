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

class TestJDecodeFormats(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_file(self, filename, content):
        path = os.path.join(self.test_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_mtg_open_csv(self):
        csv_content = 'name,mana_cost,type,text,power,toughness,rarity\n"Test Card","{1}{W}","Creature","Lifelink","2","2","Common"\n'
        path = self.create_file("test.csv", csv_content)

        cards = jdecode.mtg_open_file(path, verbose=False)
        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertEqual(card.name, "test card")
        self.assertEqual(card.cost.format(), "{1}{W}")
        self.assertEqual(card.types, ["creature"])
        self.assertEqual(utils.from_unary(card.pt_p), "2")
        self.assertEqual(utils.from_unary(card.pt_t), "2")
        self.assertEqual(card.rarity, utils.rarity_common_marker)

    def test_mtg_open_jsonl(self):
        jsonl_content = json.dumps({"name": "Card 1", "types": ["Instant"], "rarity": "Uncommon"}) + "\n"
        jsonl_content += json.dumps({"name": "Card 2", "types": ["Sorcery"], "rarity": "Rare"}) + "\n"
        path = self.create_file("test.jsonl", jsonl_content)

        cards = jdecode.mtg_open_file(path, verbose=False)
        self.assertEqual(len(cards), 2)
        names = sorted([c.name for c in cards])
        self.assertEqual(names, ["card 1", "card 2"])

    def test_mtg_open_mse(self):
        # MSE format is indented text
        mse_content = """mse version: 0.3.8
game: magic
stylesheet: m15
card:
	name: Hybrid Wizard
	casting cost: 1W/U
	rarity: uncommon
	super type: Creature
	sub type: Wizard
	rule text:
		When Hybrid Wizard enters,
		draw a card.
	power: 1
	toughness: 2
card:
	name: Battle Card
	casting cost: 4
	rarity: rare
	super type: Battle
	sub type: Siege
	defense: 5
"""
        # We need to create a .mse-set zip file
        mse_path = os.path.join(self.test_dir, "test.mse-set")
        with zipfile.ZipFile(mse_path, 'w') as zf:
            zf.writestr('set', mse_content)

        cards = jdecode.mtg_open_file(mse_path, verbose=False)
        self.assertEqual(len(cards), 2)

        wizard = next(c for c in cards if c.name == "hybrid wizard")
        self.assertEqual(wizard.cost.format(), "{1}{W/U}")
        self.assertEqual(utils.from_unary(wizard.pt_p), "1")
        self.assertEqual(utils.from_unary(wizard.pt_t), "2")
        self.assertIn("when @ enters", wizard.text.text)
        self.assertIn("draw a card", wizard.text.text)

        battle = next(c for c in cards if c.name == "battle card")
        self.assertEqual(utils.from_unary(battle.loyalty), "5")

    def test_mse_complex_mana(self):
        mse_content = """card:
	name: All Hybrid
	casting cost: W/U2/RB/P10
	rarity: rare
	super type: Instant
"""
        # test mtg_open_mse_content directly
        srcs, bad = jdecode.mtg_open_mse_content(mse_content)
        self.assertIn("all hybrid", srcs)
        card_data = srcs["all hybrid"][0]
        self.assertEqual(card_data["manaCost"], "{W/U}{2/R}{B/P}{10}")

    def test_stdin_json_detection(self):
        data = {"name": "Stdin Card", "types": ["Land"], "rarity": "Common"}
        stdin_content = json.dumps(data)

        with patch('sys.stdin', StringIO(stdin_content)):
            cards = jdecode.mtg_open_file('-', verbose=False)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, "stdin card")

    def test_stdin_jsonl_detection(self):
        jsonl_content = json.dumps({"name": "Line 1", "types": ["Land"]}) + "\n"
        jsonl_content += json.dumps({"name": "Line 2", "types": ["Land"]})

        with patch('sys.stdin', StringIO(jsonl_content)):
            cards = jdecode.mtg_open_file('-', verbose=False)

        self.assertEqual(len(cards), 2)

    def test_stdin_csv_detection(self):
        # Card must be valid to be returned from CSV/JSON input
        csv_content = "name,mana_cost,type,rarity\nCSV Card,{G},Sorcery,Common"

        with patch('sys.stdin', StringIO(csv_content)):
            cards = jdecode.mtg_open_file('-', verbose=False)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, "csv card")

if __name__ == '__main__':
    unittest.main()
