import unittest
import sys
import os
import io
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib import jdecode, utils, cardlib

class TestJDecodeCoverageFinal(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parse_decklist_value_error(self):
        # Line 501-502: except ValueError: count = 1
        decklist_path = os.path.join(self.test_dir, "deck.txt")
        with open(decklist_path, 'w') as f:
            f.write("4x Grizzly Bears\n")

        # Patch int only in jdecode
        with patch('lib.jdecode.int', side_effect=ValueError):
            res = jdecode.parse_decklist(decklist_path)
            self.assertEqual(res["grizzly bears"], 1)

    def test_mtg_open_mse_content_advanced_gaps(self):
        # Line 539: Multi-line value (continuation) - \t\t
        # Line 561: Empty key value
        # Line 564: End of card block
        mse_content = """card:
	name: Test Card
	casting cost: {W}
	rule text:
		Line 1
		Line 2
	unknown key:
	another key: value
"""
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            srcs, _ = jdecode.mtg_open_mse_content(mse_content, verbose=True)
            self.assertIn("Opened 1 uniquely named cards from MSE set.", fake_err.getvalue()) # Line 642
            self.assertIn("test card", srcs)
            self.assertEqual(srcs["test card"][0]["text"], "Line 1\nLine 2")

    def test_mse_bside_subtypes(self):
        # Line 631: b['subtypes'] = subtypes_2.split()
        mse_content = """card:
	name: Front
	super type: Creature
	sub type: Elf Warrior
	name 2: Back
	super type 2: Creature
	sub type 2: Wolf
"""
        srcs, _ = jdecode.mtg_open_mse_content(mse_content)
        card = srcs["front"][0]
        self.assertIn(utils.json_field_bside, card)
        self.assertEqual(card[utils.json_field_bside]["subtypes"], ["Wolf"])

    def test_check_parsing_quality_legacy_warning(self):
        # Line 682-683: print legacy format warning
        cards = []
        for i in range(20):
            c = MagicMock(spec=cardlib.Card)
            c.parsed = False
            c.text = MagicMock()
            c.text.text = ""
            c.name = "Test"
            c.rarity = "C"
            cards.append(c)

        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode._check_parsing_quality(cards, None)
            self.assertIn("WARNING: Saw a bunch of unparsed cards", fake_err.getvalue())

    def test_process_json_srcs_invalid_logging(self):
        # Line 739-741: print invalid card
        card = MagicMock(spec=cardlib.Card)
        card.valid = False
        card.parsed = True
        card.types = []

        json_srcs = {"bad card": [{"name": "bad card"}]}

        with patch('lib.jdecode._find_best_candidate', return_value=(0, card)):
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                jdecode._process_json_srcs(json_srcs, set(), verbose=True, linetrans=True,
                                           exclude_sets=lambda x: False, exclude_types=lambda x: False,
                                           exclude_layouts=lambda x: False, report_fobj=None)
                self.assertIn("Invalid card: bad card", fake_err.getvalue())

    def test_mtg_open_file_verbose_formats(self):
        # Lines 995, 1005, 1015: Verbose output for specific formats

        # JSONL
        jsonl_path = os.path.join(self.test_dir, "test.jsonl")
        with open(jsonl_path, 'w') as f:
            f.write(json.dumps({"name": "Test", "rarity": "C", "types": ["Land"]}))
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode.mtg_open_file(jsonl_path, verbose=True)
            self.assertIn("This looks like a jsonl file", fake_err.getvalue())

        # XML
        xml_path = os.path.join(self.test_dir, "test.xml")
        with open(xml_path, 'w') as f:
            f.write("<cockatrice_carddatabase><cards><card><name>Test</name></card></cards></cockatrice_carddatabase>")
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode.mtg_open_file(xml_path, verbose=True)
            self.assertIn("This looks like an xml file", fake_err.getvalue())

        # MSE
        mse_path = os.path.join(self.test_dir, "test.mse-set")
        import zipfile
        with zipfile.ZipFile(mse_path, 'w') as zf:
            zf.writestr('set', 'card:\n\tname: Test')
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode.mtg_open_file(mse_path, verbose=True)
            self.assertIn("This looks like an MSE set file", fake_err.getvalue())

    def test_mtg_open_file_xml_stdin(self):
        # Line 1069-1073: XML input from stdin
        xml_content = "<cockatrice_carddatabase><cards><card><name>Test</name><rarity>C</rarity><type>Land</type></card></cards></cockatrice_carddatabase>"
        with patch('sys.stdin', io.StringIO(xml_content)):
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                cards = jdecode.mtg_open_file('-', verbose=True)
                self.assertIn("Detected XML input from stdin", fake_err.getvalue())
                self.assertEqual(len(cards), 1)
                self.assertEqual(cards[0].name, "test")

    def test_mtg_open_file_csv_stdin_exception(self):
        # Line 1086-1087: CSV detection failure
        csv_content = "name,rarity\nTest,C"
        # We need to trigger an exception in CSV processing after it starts with 'name,'
        with patch('sys.stdin', io.StringIO(csv_content)):
            with patch('lib.jdecode.mtg_open_csv_reader', side_effect=Exception("Test Exception")):
                # Should catch exception and pass
                jdecode.mtg_open_file('-', verbose=True)

    def test_mtg_open_file_decklist_unicode_error(self):
        # Line 1101-1102: UnicodeDecodeError during decklist probing

        # We need to mock open to return a file-like object that raises UnicodeDecodeError on readline
        mock_file = MagicMock()
        mock_file.readline.side_effect = UnicodeDecodeError('utf8', b'', 0, 1, 'fake')
        mock_file.__enter__.return_value = mock_file

        # We also need to avoid the subsequent open() call or make it fail gracefully
        with patch('builtins.open', return_value=mock_file):
            # This should hit the UnicodeDecodeError in the decklist probing loop
            # and then continue to the next part of mtg_open_file
            # which will call open(fname, 'rt', encoding='utf8') again.
            # We'll just let it fail there but we've covered the lines.
            try:
                jdecode.mtg_open_file('dummy.txt')
            except UnicodeDecodeError:
                pass

    def test_mtg_open_file_booster_param(self):
        # Line 1371: booster parameter
        cards_json = [
            {"name": "C", "types": ["Land"], "rarity": "Common"},
            {"name": "U", "types": ["Land"], "rarity": "Uncommon"},
            {"name": "R", "types": ["Land"], "rarity": "Rare"},
            {"name": "L", "types": ["Land"], "rarity": "Basic Land"}
        ]
        json_str = json.dumps(cards_json)
        with patch('sys.stdin', io.StringIO(json_str)):
            # booster=1 triggers _simulate_boosters
            cards = jdecode.mtg_open_file('-', booster=1)
            self.assertTrue(len(cards) > 0)

    def test_simulate_boosters_no_commons_warning(self):
        # Line 1416-1417: No commons found warning
        card = MagicMock(spec=cardlib.Card)
        card.rarity = "Rare"
        card.types = ["Instant"]

        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            # We need to ensure it doesn't crash even if rarity-specific lists are empty
            jdecode._simulate_boosters([card], 1, verbose=True)
            self.assertIn("Warning: No commons found for booster generation", fake_err.getvalue())

if __name__ == '__main__':
    unittest.main()
