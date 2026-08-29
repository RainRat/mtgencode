import unittest
from unittest.mock import patch
import io
import sys
import os
import json

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from cardlib import Card
from scripts.mtg_complexity import main as complexity_main
from scripts.mtg_query import main as search_main

class TestMtgComplexity(unittest.TestCase):

    def test_card_complexity_properties(self):
        # Basic creature
        card_json = {
            "name": "Grizzly Bears",
            "manaCost": "{1}{G}",
            "types": ["Creature"],
            "subtypes": ["Bear"],
            "power": "2",
            "toughness": "2",
            "rarity": "Common",
            "text": ""
        }
        card = Card(card_json)
        self.assertEqual(card.total_words, 0)
        self.assertEqual(card.total_lines, 0)
        # 0 + 0*5 + 0*8 + 1*3 (G) = 3
        self.assertEqual(card.complexity_score, 3)

        # Complex card
        card_json2 = {
            "name": "Uthros Research Craft",
            "manaCost": "{2}{U}",
            "types": ["Artifact"],
            "subtypes": ["Spacecraft"],
            "power": "0",
            "toughness": "8",
            "rarity": "Rare",
            "text": "Flying\nWhenever @ attacks, draw a card.\nPut a % counter on @.\n{X}: Do something."
        }
        card2 = Card(card_json2)
        # Flying (1)
        # Whenever @ attacks, draw a card. (5)
        # Put a % counter on @. (5)
        # {X}: Do something. (3)
        # Total words: 1 + 5 + 4 + 3 = 13
        self.assertEqual(card2.total_words, 13)
        self.assertEqual(card2.total_lines, 4)
        # Mechanics: Flying, Triggered, Draw A Card, Counters, X-Cost/Effect, Activated = 6
        self.assertEqual(len(card2.mechanics), 6)
        self.assertEqual(card2.color_identity, "U")
        # Score: 13 (words) + 4*5 (lines) + 6*8 (mechanics) + 1*3 (CI) + 10 (X bonus) = 13 + 20 + 48 + 3 + 10 = 94
        self.assertEqual(card2.complexity_score, 94)

    def test_complexity_cli_basic(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_complexity.py', 'testdata/uthros.json', '--no-color']):
                complexity_main()
                output = fake_out.getvalue()
                self.assertIn("COMPLEXITY ANALYSIS", output)
                self.assertIn("Average Complexity Score: 107.00", output)
                self.assertIn("Uthros Research Craft", output)

    def test_complexity_cli_json(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_complexity.py', 'testdata/uthros.json', '--json']):
                complexity_main()
                output = fake_out.getvalue()
                data = json.loads(output)
                self.assertEqual(data['average_complexity'], 107.0)
                self.assertEqual(len(data['top_cards']), 1)
                self.assertEqual(data['top_cards'][0]['complexity'], 107)

    def test_search_complexity_field(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_query.py', 'search', 'testdata/uthros.json', '--fields', 'name,complexity', '--text', '--no-color']):
                search_main()
                output = fake_out.getvalue()
                self.assertIn("Uthros Research Craft | 107", output)

    def test_complexity_cli_csv(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_complexity.py', 'testdata/uthros.json', '--csv']):
                complexity_main()
                output = fake_out.getvalue()
                self.assertIn("Name,Complexity,Rarity,Type", output)
                self.assertIn("Uthros Research Craft,107,rare,", output)

    def test_complexity_cli_sample_and_shuffle(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_complexity.py', 'testdata/uthros.json', '--sample', '1', '--seed', '42', '--no-color']):
                complexity_main()
                output = fake_out.getvalue()
                self.assertIn("COMPLEXITY ANALYSIS", output)

    def test_complexity_cli_smart_grep_positional(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stdin.isatty', return_value=False), \
             patch('scripts.mtg_complexity.jdecode.mtg_open_file', return_value=[Card({
                 "name": "Nonexistent Match", "manaCost": "{1}", "types": ["Creature"],
                 "subtypes": [], "power": "1", "toughness": "1", "rarity": "Common", "text": ""
             })]) as mock_open:
            with patch('sys.argv', ['mtg_complexity.py', 'NonexistentSearchTerm', '--no-color']):
                complexity_main()
                output = fake_out.getvalue()
                self.assertIn("COMPLEXITY ANALYSIS", output)
                self.assertEqual(mock_open.call_args[0][0], '-')
                self.assertEqual(mock_open.call_args[1]['grep'], ['NonexistentSearchTerm'])

    def test_complexity_cli_default_dataset_tty(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()) as fake_err, \
             patch('sys.stdin.isatty', return_value=True), \
             patch('os.path.exists', return_value=True), \
             patch('scripts.mtg_complexity.jdecode.mtg_open_file', return_value=[Card({
                 "name": "Default Card", "manaCost": "{1}", "types": ["Creature"],
                 "subtypes": [], "power": "1", "toughness": "1", "rarity": "Common", "text": ""
             })]) as mock_open:
            with patch('sys.argv', ['mtg_complexity.py', '-']):
                complexity_main()
                err_out = fake_err.getvalue()
                self.assertIn("Notice: Using default dataset:", err_out)

    def test_complexity_cli_outfile(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tf:
            temp_path = tf.name
        try:
            with patch('sys.stderr', new=io.StringIO()):
                with patch('sys.argv', ['mtg_complexity.py', 'testdata/uthros.json', temp_path, '-v', '--no-color']):
                    complexity_main()
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn("COMPLEXITY ANALYSIS", content)
            self.assertIn("Uthros Research Craft", content)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_complexity_cli_color(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_complexity.py', 'testdata/uthros.json', '--color']):
                complexity_main()
                output = fake_out.getvalue()
                self.assertIn("\033[", output)

    def test_complexity_cli_smart_grep_appends(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stdin.isatty', return_value=False), \
             patch('scripts.mtg_complexity.jdecode.mtg_open_file', return_value=[Card({
                 "name": "Match", "manaCost": "{1}", "types": ["Creature"],
                 "subtypes": [], "power": "1", "toughness": "1", "rarity": "Common", "text": ""
             })]) as mock_open:
            with patch('sys.argv', ['mtg_complexity.py', 'SecondQuery', '-g', 'FirstQuery', '--no-color']):
                complexity_main()
                self.assertEqual(mock_open.call_args[1]['grep'], ['FirstQuery', 'SecondQuery'])

    def test_complexity_cli_colorless_and_summary(self):
        colorless_card = Card({
            "name": "Colorless Artifact", "manaCost": "{3}", "types": ["Artifact"],
            "subtypes": [], "rarity": "Uncommon", "text": "Draw a card."
        })

        multicolor_card = Card({
            "name": "Multicolor Spell", "manaCost": "{W}{U}", "types": ["Instant"],
            "subtypes": [], "rarity": "Rare", "text": "Draw a card."
        })

        with patch('sys.stdout', new=io.StringIO()) as fake_out, \
             patch('sys.stderr', new=io.StringIO()) as fake_err, \
             patch('scripts.mtg_complexity.jdecode.mtg_open_file', return_value=[colorless_card, multicolor_card]):
            with patch('sys.argv', ['mtg_complexity.py', 'testdata/uthros.json', '--color']):
                complexity_main()
                self.assertIn("\033[", fake_out.getvalue())
                self.assertIn("Complexity Analysis", fake_err.getvalue())

    def test_complexity_cli_no_matching_cards(self):
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.argv', ['mtg_complexity.py', 'testdata/uthros.json', '-g', 'NonExistentKeywordPattern']):
                complexity_main()
                err_out = fake_err.getvalue()
                self.assertIn("No cards found matching the criteria.", err_out)

    def test_complexity_cli_dry_run(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tf:
            temp_path = tf.name

        try:
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_complexity.py', 'testdata/uthros.json', temp_path, '--dry-run']):
                    complexity_main()
                    output = fake_out.getvalue()
                    self.assertIn("Dry Run Summary: 1 card(s) evaluated.", output)
                    self.assertIn("Average Complexity Score: 107.00", output)
                    self.assertIn("Sample Preview (up to 10): Uthros Research Craft (107)", output)

            # File should not have been opened or written to
            self.assertEqual(os.path.getsize(temp_path), 0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == '__main__':
    unittest.main()
