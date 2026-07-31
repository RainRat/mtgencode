import unittest
import sys
import os
import io
import json
import tempfile
from unittest.mock import patch

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib import jdecode, utils, cardlib

class TestJDecodeGapsQA(unittest.TestCase):

    def test_format_mana_json_single_brace(self):
        # Triggers line 231: if s.count('{') == 1: s = s[1:-1]
        self.assertEqual(jdecode._format_mana_json("{2UU}"), "{2}{U}{U}")
        self.assertEqual(jdecode._format_mana_json("{W}"), "{W}")

    def test_format_mana_json_multiple_braces(self):
        # Triggers line 233: else: return s
        self.assertEqual(jdecode._format_mana_json("{2}{U}{U}"), "{2}{U}{U}")

    def test_mtg_open_xml_content_root_card(self):
        # Triggers line 278: if cards_node is None: cards_node = root
        xml_text = """<cockatrice_carddatabase>
            <card><name>Test</name></card>
        </cockatrice_carddatabase>"""
        srcs, _ = jdecode.mtg_open_xml_content(xml_text)
        self.assertIn("test", srcs)

    def test_mtg_open_xml_content_no_name(self):
        # Triggers line 283: if not name: continue
        xml_text = """<cockatrice_carddatabase><cards>
            <card><manacost>U</manacost></card>
        </cards></cockatrice_carddatabase>"""
        srcs, _ = jdecode.mtg_open_xml_content(xml_text)
        self.assertEqual(len(srcs), 0)

    def test_mtg_open_xml_content_pt_ambiguous(self):
        # Triggers lines 314, 316, 322, 324, 326
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
        # Triggers line 330: allcards[cardname].append(card_dict)
        xml_text = """<cockatrice_carddatabase><cards>
            <card><name>D</name></card>
            <card><name>D</name></card>
        </cards></cockatrice_carddatabase>"""
        srcs, _ = jdecode.mtg_open_xml_content(xml_text)
        self.assertEqual(len(srcs["d"]), 2)

    def test_mtg_open_xml_content_verbose(self):
        # Triggers line 335: print statements when verbose=True
        xml_text = """<cockatrice_carddatabase><cards><card><name>V</name></card></cards></cockatrice_carddatabase>"""
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode.mtg_open_xml_content(xml_text, verbose=True)
            self.assertIn("Opened 1 uniquely named cards from XML.", fake_err.getvalue())

    def test_mtg_open_json_obj_bside_mapping(self):
        # Triggers line 208 and line 210
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

        # Helper to run filter with a fresh StringIO
        def run_filter(**kwargs):
            with patch('sys.stdin', io.StringIO(json_str)):
                return jdecode.mtg_open_file('-', **kwargs)

        # Test 1: grep_cost and vgrep_cost (lines 1153, 1156-1157)
        res = run_filter(grep_cost=["R"], vgrep_cost=["1"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "shock")

        # Trigger line 1157: vgrep_cost matches
        res = run_filter(vgrep_cost=["R"])
        self.assertEqual(len([c for c in res if c.name == "shock"]), 0)

        # Test 2: grep_pt and vgrep_pt (lines 1161, 1164-1165)
        res = run_filter(grep_pt=["2/2"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "grizzly bears")

        # Trigger line 1165: vgrep_pt matches
        res = run_filter(vgrep_pt=["2/2"])
        self.assertEqual(len([c for c in res if c.name == "grizzly bears"]), 0)

        # Test 3: grep_loyalty and vgrep_loyalty (lines 1169, 1172-1173)
        res = run_filter(grep_loyalty=["3"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "jace")

        # Trigger line 1173: vgrep_loyalty matches
        res = run_filter(vgrep_loyalty=["3"])
        self.assertEqual(len([c for c in res if c.name == "jace"]), 0)

        # Test 4: color filtering (line 1190+)
        # 'A' for artifact/colorless match cards without colors
        res = run_filter(colors=["A"])
        self.assertEqual(len(res), 2) # Ornithopter and Custom

        res = run_filter(colors=["R"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "shock")

        # Test 5: numeric filters (lines 1202-1239)
        # cmcs (1202)
        # Custom card also has 0 CMC (no manaCost)
        res = run_filter(cmcs=["0"])
        self.assertEqual(len(res), 2) # Ornithopter and Custom

        # pows (1212)
        res = run_filter(pows=["2"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "grizzly bears")

        # tous (1222)
        res = run_filter(tous=["2"])
        self.assertEqual(len(res), 2) # Bears and Thopter

        # loys (1232)
        res = run_filter(loys=[">2"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "jace")

        # Test 6: mechanics filtering (lines 1243-1250)
        res = run_filter(mechanics=["Scry"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "jace")

        # Test 7: rarities filtering (lines 1105, 1183)
        res = run_filter(rarities=["Mythic", "Rare"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "jace")

        res = run_filter(rarities=["special"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "custom")

        # Test 8: Identity filtering (lines 1251-1262)
        res = run_filter(identities=["R"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, "shock")

        res = run_filter(identities=["A"]) # Colorless identity
        self.assertEqual(len(res), 2) # Ornithopter and Custom

        # Test 9: Identity Count filtering (lines 1263-1272)
        res = run_filter(id_counts=["0"])
        self.assertEqual(len(res), 2) # Ornithopter and Custom

        res = run_filter(id_counts=["1"])
        self.assertEqual(len(res), 3) # Shock (R), Grizzly Bears (G), Jace (U)

        # Test 10: stats and reporting
        stats = {}
        res = run_filter(grep_name=["Shock"], stats=stats)
        self.assertEqual(stats['matched'], 1)
        self.assertEqual(stats['filtered'], 4)

    def test_mtg_open_file_shuffle(self):
        # Triggers lines 1286-1295
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

        # seed=None (line 1295)
        with patch('sys.stdin', io.StringIO(json_str)):
            jdecode.mtg_open_file('-', shuffle=True, seed=None)

    def test_simulate_boxes_verbose(self):
        # Triggers line 1319
        card = cardlib.Card({"name": "Test", "types": ["Instant"], "rarity": "Common"})
        # We need at least enough cards of each rarity for a pack if we want it to be realistic,
        # but _simulate_boosters has fallbacks.
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode._simulate_boxes([card], 1, verbose=True)
            self.assertIn("Simulated 1 booster boxes", fake_err.getvalue())

    def test_parse_markdown_card_block_empty_lines(self):
        # Covers line 508: lines is empty
        res = jdecode.parse_markdown_card_block("\n \n")
        self.assertIsNone(res)

    def test_parse_markdown_card_block_rarity_in_second_line_only(self):
        # Covers line 545-546: rarity is in second line, not first
        block = """**Lightning Bolt** {R}
Instant (common)
Lightning Bolt deals 3 damage."""
        res = jdecode.parse_markdown_card_block(block)
        self.assertEqual(res['rarity'], "common")
        self.assertEqual(res['type'], "Instant")

    def test_parse_markdown_card_block_loyalty_third_line(self):
        # Covers line 573: loyalty is on third line
        block = """**Jace** {1}{U}{U} (rare)
Planeswalker — Jace
[3]
+1: Draw."""
        res = jdecode.parse_markdown_card_block(block)
        self.assertEqual(res['loyalty'], "3")
        self.assertEqual(res['type'], "Planeswalker — Jace")

    def test_mtg_open_markdown_content_table_followed_by_text(self):
        # Covers line 616-617: table followed by text (non-pipe line)
        md_text = """| Name | Cost | Type | Stats | Rarity | Rules Text |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Grizzly Bears | {1}{G} | Creature — Bear | 2/2 | Common | Grizzly bears. |

This is trailing text.
"""
        srcs, _ = jdecode.mtg_open_markdown_content(md_text)
        self.assertIn("grizzly bears", srcs)

    def test_mtg_open_markdown_content_block_with_empty_strings(self):
        # Covers line 661: block is empty/only whitespace
        md_text = """**Card A** {G} (common)
Creature
1/1

---



---

**Card B** {W} (common)
Creature
1/1"""
        srcs, _ = jdecode.mtg_open_markdown_content(md_text)
        self.assertIn("card a", srcs)
        self.assertIn("card b", srcs)

    def test_mtg_open_markdown_content_duplicate_names(self):
        # Covers line 666: duplicate card name in blocks
        md_text = """**Bears** {1}{G} (common)
Creature
2/2

---

**Bears** {1}{G} (common)
Creature
2/2"""
        srcs, _ = jdecode.mtg_open_markdown_content(md_text)
        self.assertIn("bears", srcs)
        self.assertEqual(len(srcs["bears"]), 2)

    def test_mtg_open_markdown_content_verbose_logging(self):
        # Covers lines 653 and 671: verbose logging
        md_text_table = """| Name | Cost | Type | Stats | Rarity | Rules Text |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Grizzly Bears | {1}{G} | Creature — Bear | 2/2 | Common | Grizzly bears. |"""
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode.mtg_open_markdown_content(md_text_table, verbose=True)
            self.assertIn("Parsed 1 rows from Markdown table(s).", fake_err.getvalue())

        md_text_list = """**Bears** {1}{G} (common)
Creature
2/2"""
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode.mtg_open_markdown_content(md_text_list, verbose=True)
            self.assertIn("Opened 1 uniquely named cards from Markdown blocks.", fake_err.getvalue())

    def test_mtg_open_file_markdown_verbose(self):
        # Covers line 1223: mtg_open_file with single .md file and verbose=True
        fd, temp_path = tempfile.mkstemp(suffix=".md")
        try:
            with os.fdopen(fd, 'w') as tmp:
                tmp.write("""**Bears** {1}{G} (common)
Creature
2/2""")
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                jdecode.mtg_open_file(temp_path, verbose=True)
                self.assertIn("This looks like a markdown file:", fake_err.getvalue())
        finally:
            os.remove(temp_path)

    def test_mtg_open_file_stdin_markdown_verbose_and_error(self):
        # Covers line 1351: Detected Markdown input from stdin verbose
        # Covers lines 1356-1357: except (ValueError, TypeError) in Markdown Detection
        md_text = """**Bears** {1}{G} (common)
Creature
2/2"""
        with patch('sys.stdin', io.StringIO(md_text)), \
             patch('sys.stderr', new=io.StringIO()) as fake_err:
            jdecode.mtg_open_file('-', verbose=True)
            self.assertIn("Detected Markdown input from stdin.", fake_err.getvalue())

        # Trigger lines 1356-1357 by raising ValueError inside mtg_open_markdown_content
        with patch('sys.stdin', io.StringIO(md_text)), \
             patch('sys.stderr', new=io.StringIO()), \
             patch('lib.jdecode.mtg_open_markdown_content', side_effect=ValueError("Test")):
            # Should not raise exception
            res = jdecode.mtg_open_file('-', verbose=True)
            self.assertEqual(len(res), 1)
            self.assertFalse(res[0].valid)

    def test_mtg_open_file_set_filtering_no_set_code(self):
        # Covers line 1533: card with NO set_code is not filtered out
        fd, temp_path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, 'w') as tmp:
                tmp.write("|NoSet|1T|") # Name is T, Type is Land

            # Filter by sets=["TEST"]
            cards = jdecode.mtg_open_file(temp_path, sets=["TEST"])
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0].name, "T")
            self.assertIsNone(cards[0].set_code)
        finally:
            os.remove(temp_path)

if __name__ == '__main__':
    unittest.main()
