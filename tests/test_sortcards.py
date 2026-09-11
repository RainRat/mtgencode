import unittest
from cardlib import Card
import sortcards

class TestSortCards(unittest.TestCase):
    def test_sort_battle(self):
        card_data = {
            "name": "Invasion of Test",
            "manaCost": "{2}{R}",
            "type": "Battle \u2014 Siege",
            "types": ["Battle"],
            "subtypes": ["Siege"],
            "defense": "5",
            "text": "Test text.",
            "rarity": "common"
        }
        card = Card(card_data)
        # sortcards.sortcards now expects Card objects

        classes = sortcards.sortcards([card])

        # The output keys contain encoded strings (or raw if present)
        # Since we created card from dict, it has no raw, so encode() is called.
        encoded = card.encode()

        self.assertIn(encoded, classes['battles'])
        self.assertNotIn(encoded, classes['other'])

    def test_sort_planeswalker(self):
        pw_data = {
            "name": "Jace Test",
            "manaCost": "{3}{U}{U}",
            "type": "Legendary Planeswalker \u2014 Jace",
            "types": ["Planeswalker"],
            "subtypes": ["Jace"],
            "loyalty": "5",
            "text": "+1: Draw a card.",
            "rarity": "mythic"
        }
        card = Card(pw_data)

        classes = sortcards.sortcards([card])
        encoded = card.encode()

        self.assertIn(encoded, classes['planeswalkers'])
        self.assertNotIn(encoded, classes['other'])

    def test_sort_rarity_and_cmc(self):
        rare_data = {
            "name": "Test Rare",
            "manaCost": "{1}{R}",
            "types": ["Creature"],
            "rarity": "Rare",
            "power": "2",
            "toughness": "2"
        }
        card = Card(rare_data)
        classes = sortcards.sortcards([card])
        encoded = card.encode()

        self.assertIn(encoded, classes['rare'])
        self.assertIn(encoded, classes['CMC 2'])
        self.assertNotIn(encoded, classes['common'])

    def test_sort_summary(self):
        card_data = {
            "name": "Summary Card",
            "manaCost": "{1}{W}",
            "types": ["Instant"],
            "rarity": "Uncommon"
        }
        card = Card(card_data)
        # Testing the summary output mode
        classes = sortcards.sortcards([card], use_summary=True)
        summary_str = card.summary()

        self.assertIn(summary_str, classes['instants'])
        self.assertIn(summary_str, classes['uncommon'])
        self.assertIn(summary_str, classes['CMC 2'])

    def test_dry_run_mode(self):
        import io
        import os
        import tempfile
        from unittest.mock import patch

        rare_data = {
            "name": "Test Dry Run Card",
            "manaCost": "{1}{R}",
            "types": ["Creature"],
            "rarity": "Rare",
            "power": "2",
            "toughness": "2"
        }
        card = Card(rare_data)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "output.txt")
            captured_stdout = io.StringIO()

            with patch("sys.stdout", captured_stdout):
                with patch("jdecode.mtg_open_file", return_value=[card]):
                    sortcards.main("dummy_input.json", out_file, dry_run=True, quiet=True)

            output = captured_stdout.getvalue()
            self.assertIn("Dry Run Summary: 1 card(s) matched.", output)
            self.assertIn("Category Breakdown:", output)
            self.assertIn("creatures: 1 card(s)", output)
            self.assertIn("Sample Preview (up to 10): Test Dry Run Card", output)
            self.assertFalse(os.path.exists(out_file))

    def test_cli_interactive_default_dataset(self):
        import io
        from unittest.mock import patch

        captured_stderr = io.StringIO()
        with patch("sys.stdin.isatty", return_value=True):
            with patch("os.path.exists", return_value=True):
                with patch("sys.argv", ["sortcards.py"]):
                    with patch("sys.stderr", captured_stderr):
                        with patch("sortcards.main") as mock_main:
                            sortcards.cli()
                            mock_main.assert_called_once()
                            args = mock_main.call_args[0]
                            self.assertTrue(args[0].endswith("AllPrintings.json"))
        stderr_val = captured_stderr.getvalue()
        self.assertIn("Notice: Using default dataset:", stderr_val)

    def test_cli_interactive_missing_dataset(self):
        import io
        from unittest.mock import patch

        captured_stderr = io.StringIO()
        with patch("sys.stdin.isatty", return_value=True):
            with patch("os.path.exists", return_value=False):
                with patch("sys.argv", ["sortcards.py"]):
                    with patch("sys.stderr", captured_stderr):
                        with self.assertRaises(SystemExit) as cm:
                            sortcards.cli()
                        self.assertEqual(cm.exception.code, 1)
        stderr_val = captured_stderr.getvalue()
        self.assertIn("Error: No input file specified and default dataset", stderr_val)

if __name__ == '__main__':
    unittest.main()
