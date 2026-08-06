import unittest
import sys
import os
import io
import json
from unittest.mock import patch

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib import jdecode, utils, cardlib

class TestJDecodeGapsQA(unittest.TestCase):

    def test_format_mana_json_single_brace(self):
        self.assertEqual(jdecode._format_mana_json("{2UU}"), "{2}{U}{U}")
        self.assertEqual(jdecode._format_mana_json("{W}"), "{W}")

    def test_format_mana_json_multiple_braces(self):
        self.assertEqual(jdecode._format_mana_json("{2}{U}{U}"), "{2}{U}{U}")

    def test_mtg_open_xml_content_root_card(self):
        xml_text = """<cockatrice_carddatabase>
            <card><name>Test</name></card>
        </cockatrice_carddatabase>"""
        srcs, _ = jdecode.mtg_open_xml_content(xml_text)
        self.assertIn("test", srcs)

    def test_mtg_open_xml_content_no_name(self):
        xml_text = """<cockatrice_carddatabase><cards>
            <card><manacost>U</manacost></card>
        </cards></cockatrice_carddatabase>"""
        srcs, _ = jdecode.mtg_open_xml_content(xml_text)
        self.assertEqual(len(srcs), 0)

    def test_mtg_open_xml_content_pt_ambiguous(self):
        xml_text = """<cockatrice_carddatabase><cards>
            <card><name>C</name><type>Creature</type><pt>2</pt></card>
            <card><name>L</name><type>Land</type><pt>3</pt></card>
            <card><name>A</name><type>Artifact</type><pt>X</pt></card>
            <card><name>B</name><type>Battle</type><pt>5</pt></card>
            <card><name>P</name><type>Planeswalker</type><pt>3</pt></card>
        </cards></cockatrice_carddatabase>"""
        srcs, _ = jdecode.mtg_open_xml_content(xml_text)
        self.assertEqual(srcs["c"][0]["power"], "2")
        self.assertEqual(srcs["l"][0]["loyalty"], "3")
        self.assertEqual(srcs["a"][0]["pt"], "X")
        self.assertEqual(srcs["b"][0]["defense"], "5")
        self.assertEqual(srcs["p"][0]["loyalty"], "3")

    def test_mtg_open_xml_content_duplicate(self):
        xml_text = """<cockatrice_carddatabase><cards>
            <card><name>D</name></card>
            <card><name>D</name></card>
        </cards></cockatrice_carddatabase>"""
        srcs, _ = jdecode.mtg_open_xml_content(xml_text)
        self.assertEqual(len(srcs["d"]), 2)

    def test_mtg_open_xml_content_verbose(self):
        xml_text = """<cockatrice_carddatabase><cards><card><name>V</name></card></cards></cockatrice_carddatabase>"""
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode.mtg_open_xml_content(xml_text, verbose=True)
            self.assertIn("Opened 1 uniquely named cards from XML.", fake_err.getvalue())

    def test_mtg_open_json_obj_bside_mapping(self):
        mtgjson_data = {
            "data": {
                "TEST": {
                    "code": "TEST", "name": "Test Set", "type": "expansion",
                    "cards": [
                        {"name": "Front", "number": "1a", "rarity": "Common"},
                        {"name": "Back", "number": "1b", "rarity": "Common"},
                        {"name": "Orphan", "number": "2b", "rarity": "Common"}
                    ]
                }
            }
        }
        allcards, _ = jdecode.mtg_open_json_obj(mtgjson_data)
        self.assertIn("front", allcards)
        self.assertIn(utils.json_field_bside, allcards["front"][0])
        self.assertEqual(allcards["front"][0][utils.json_field_bside]["name"], "Back")
        self.assertNotIn("back", allcards)
        self.assertNotIn("orphan", allcards)

    def test_mtg_open_file_comprehensive_filtering(self):
        cards_json = {
            "data": {
                "TEST": {
                    "code": "TEST", "name": "Test Set", "type": "expansion",
                    "cards": [
                        {"name": "Shock", "manaCost": "{R}", "text": "Shock deals 2 damage.", "types": ["Instant"], "rarity": "Common"},
                        {"name": "Grizzly Bears", "manaCost": "{1}{G}", "text": "Vanilla.", "types": ["Creature"], "rarity": "Common", "power": "2", "toughness": "2"},
                        {"name": "Jace", "manaCost": "{1}{U}{U}", "text": "Scry.", "types": ["Planeswalker"], "rarity": "Mythic", "loyalty": "3", "mechanics": ["Scry"]},
                        {"name": "Ornithopter", "manaCost": "{0}", "text": "Flying.", "types": ["Artifact", "Creature"], "rarity": "Uncommon", "power": "0", "toughness": "2"},
                        {"name": "Custom", "rarity": "Special", "types": ["Instant"]}
                    ]
                }
            }
        }

        json_str = json.dumps(cards_json)

        def run_filter(**kwargs):
            with patch('sys.stdin', io.StringIO(json_str)):
                return jdecode.mtg_open_file('-', **kwargs)

        res = run_filter(grep_cost=["R"], vgrep_cost=["1"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "shock")

        res = run_filter(vgrep_cost=["R"])
        self.assertEqual(len([c for c in res if c.name == "shock"]), 0)

        res = run_filter(grep_pt=["2/2"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "grizzly bears")

        res = run_filter(vgrep_pt=["2/2"])
        self.assertEqual(len([c for c in res if c.name == "grizzly bears"]), 0)

        res = run_filter(grep_loyalty=["3"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "jace")

        res = run_filter(vgrep_loyalty=["3"])
        self.assertEqual(len([c for c in res if c.name == "jace"]), 0)

        res = run_filter(colors=["A"])
        self.assertEqual(len(res), 2)

        res = run_filter(colors=["R"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "shock")

        res = run_filter(cmcs=["0"])
        self.assertEqual(len(res), 2)

        res = run_filter(pows=["2"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "grizzly bears")

        res = run_filter(tous=["2"])
        self.assertEqual(len(res), 2)

        res = run_filter(loys=[">2"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "jace")

        res = run_filter(mechanics=["Scry"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "jace")

        res = run_filter(rarities=["Mythic", "Rare"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "jace")

        res = run_filter(rarities=["special"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "custom")

        res = run_filter(identities=["R"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "shock")

        res = run_filter(identities=["A"])
        self.assertEqual(len(res), 2)

        res = run_filter(id_counts=["0"])
        self.assertEqual(len(res), 2)

        res = run_filter(id_counts=["1"])
        self.assertEqual(len(res), 3)

        stats = {}
        res = run_filter(grep_name=["Shock"], stats=stats)
        self.assertEqual(stats['matched'], 1)
        self.assertEqual(stats['filtered'], 4)

    def test_mtg_open_file_shuffle(self):
        cards_json = [
            {"name": "A", "types": ["Instant"], "rarity": "Common"},
            {"name": "B", "types": ["Instant"], "rarity": "Common"},
            {"name": "C", "types": ["Instant"], "rarity": "Common"}
        ]
        json_str = json.dumps(cards_json)
        with patch('sys.stdin', io.StringIO(json_str)):
            res1 = jdecode.mtg_open_file('-', shuffle=True, seed=42)
        with patch('sys.stdin', io.StringIO(json_str)):
            res2 = jdecode.mtg_open_file('-', shuffle=True, seed=42)
        self.assertEqual([c.name for c in res1], [c.name for c in res2])

        with patch('sys.stdin', io.StringIO(json_str)):
            jdecode.mtg_open_file('-', shuffle=True, seed=None)

    def test_simulate_boxes_verbose(self):
        card = cardlib.Card({"name": "Test", "types": ["Instant"], "rarity": "Common"})
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode._simulate_boxes([card], 1, verbose=True)
            self.assertIn("Simulated 1 booster boxes", fake_err.getvalue())

    def test_parse_markdown_card_block_empty(self):
        self.assertIsNone(jdecode.parse_markdown_card_block("   \n   \n"))

    def test_parse_markdown_card_block_rarity_second_line(self):
        block = "**Grizzly Bears**\nCreature (Common)\n"
        res = jdecode.parse_markdown_card_block(block)
        self.assertEqual(res['rarity'], 'Common')
        self.assertEqual(res['type'], 'Creature')

    def test_parse_markdown_card_block_stats_second_line(self):
        block = "**Grizzly Bears** (Common)\nCreature (2/2)\n"
        res = jdecode.parse_markdown_card_block(block)
        self.assertEqual(res['power'], '2')
        self.assertEqual(res['toughness'], '2')

    def test_parse_markdown_card_block_loyalty_second_line(self):
        block = "**Jace** (Mythic)\nPlaneswalker [4]\n"
        res = jdecode.parse_markdown_card_block(block)
        self.assertEqual(res['loyalty'], '4')

    def test_parse_markdown_card_block_loyalty_third_line(self):
        block = "**Jace**\nPlaneswalker\n[4]\n"
        res = jdecode.parse_markdown_card_block(block)
        self.assertEqual(res['loyalty'], '4')

    def test_mtg_open_markdown_content_tables_followed_by_nontable(self):
        text = """
| Name | Type |
| --- | --- |
| CardA | Sorcery |

This is some non-table text.
"""
        srcs, _ = jdecode.mtg_open_markdown_content(text)
        self.assertIn("carda", srcs)

    def test_mtg_open_markdown_content_verbose_tables(self):
        text = """
| Name | Type |
| --- | --- |
| CardA | Sorcery |
"""
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode.mtg_open_markdown_content(text, verbose=True)
            self.assertIn("Parsed 1 rows from Markdown table(s).", fake_err.getvalue())

    def test_mtg_open_markdown_content_fallback_gaps(self):
        text = "**Grizzly Bears**\nCreature (2/2)\n\n\n\n**Grizzly Bears**\nCreature (2/2)\n"
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            srcs, _ = jdecode.mtg_open_markdown_content(text, verbose=True)
            self.assertIn("grizzly bears", srcs)
            self.assertEqual(len(srcs["grizzly bears"]), 2)
            self.assertIn("Opened 1 uniquely named cards from Markdown blocks.", fake_err.getvalue())

    @patch('os.path.isdir')
    @patch('os.walk')
    @patch('builtins.open')
    def test_mtg_open_file_dir_markdown(self, mock_open, mock_walk, mock_isdir):
        mock_isdir.return_value = True
        mock_walk.return_value = [('fake_dir', [], ['test.md'])]

        mock_file = io.StringIO("| Name | Type |\n| --- | --- |\n| CardA | Sorcery |")
        mock_open.return_value = mock_file

        res = jdecode.mtg_open_file('fake_dir', verbose=True)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, 'carda')

    @patch('builtins.open')
    def test_mtg_open_file_single_markdown_verbose(self, mock_open):
        mock_file = io.StringIO("| Name | Type |\n| --- | --- |\n| CardA | Sorcery |")
        mock_open.return_value = mock_file
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            res = jdecode.mtg_open_file('test.md', verbose=True)
            self.assertIn("This looks like a markdown file: test.md", fake_err.getvalue())
            self.assertEqual(len(res), 1)

    def test_mtg_open_file_stdin_markdown_verbose(self):
        text = "| Name | Type |\n| --- | --- |\n| CardA | Sorcery |"
        with patch('sys.stdin', io.StringIO(text)), patch('sys.stderr', new=io.StringIO()) as fake_err:
            res = jdecode.mtg_open_file('-', verbose=True)
            self.assertIn("Detected Markdown input from stdin.", fake_err.getvalue())
            self.assertEqual(len(res), 1)

    @patch('lib.jdecode.mtg_open_markdown_content')
    def test_mtg_open_file_stdin_markdown_exception(self, mock_md):
        mock_md.side_effect = ValueError("Mocked error")
        text = "| Name | Type |\n| --- | --- |\n| CardA | Sorcery |"
        with patch('sys.stdin', io.StringIO(text)):
            res = jdecode.mtg_open_file('-')
            self.assertTrue(mock_md.called)
            self.assertTrue(len(res) > 0)

    def test_mtg_open_file_set_reprint_activation(self):
        cards_json = {
            "data": {
                "LEA": {
                    "code": "LEA", "name": "Alpha", "type": "expansion",
                    "cards": [
                        {"name": "Grizzly Bears", "manaCost": "{1}{G}", "types": ["Creature"], "rarity": "Common", "power": "2", "toughness": "2", "number": "1"}
                    ]
                },
                "2ED": {
                    "code": "2ED", "name": "Unlimited", "type": "expansion",
                    "cards": [
                        {"name": "Grizzly Bears", "manaCost": "{1}{G}", "types": ["Creature"], "rarity": "Common", "power": "2", "toughness": "2", "number": "10"}
                    ]
                }
            }
        }
        json_str = json.dumps(cards_json)
        with patch('sys.stdin', io.StringIO(json_str)):
            res = jdecode.mtg_open_file('-', sets=["2ED"])
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0].set_code, "2ED")

if __name__ == '__main__':
    unittest.main()
