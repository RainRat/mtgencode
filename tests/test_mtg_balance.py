import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_balance import get_archetype_counts, main as balance_main
from lib.cardlib import Card

class TestMtgBalance(unittest.TestCase):

    def setUp(self):
        # Create some sample cards
        self.cards = [
            Card({"name": "W Card", "manaCost": "{W}", "types": ["Creature"]}),
            Card({"name": "U Card", "manaCost": "{U}", "types": ["Creature"]}),
            Card({"name": "WU Card", "manaCost": "{W}{U}", "types": ["Creature"]}),
            Card({"name": "UB Card", "manaCost": "{U}{B}", "types": ["Creature"]}),
            Card({"name": "Colorless Card", "manaCost": "{1}", "types": ["Artifact"]}),
            Card({"name": "WUB Card", "manaCost": "{W}{U}{B}", "types": ["Creature"]}),
        ]

    def test_get_archetype_counts(self):
        counts = get_archetype_counts(self.cards)

        # WU Card (identity WU) should count towards UW
        # W Card (identity W) should count towards all pairs with W: UW, GW, BW, RW
        # U Card (identity U) should count towards all pairs with U: UW, BU, RU, GU

        # UW (UW pair in code) count:
        # - W Card (+1)
        # - U Card (+1)
        # - WU Card (+1)
        # Total = 3
        self.assertEqual(counts["UW"], 3)

        # BU count:
        # - U Card (+1)
        # - UB Card (+1)
        # Total = 2
        self.assertEqual(counts["BU"], 2)

        # BR count:
        # - Monocolored cards with B or R? None in self.cards except B-inclusive multicolored.
        # Wait, B monocolored? No. R monocolored? No.
        # UB Card has B, but identity is 2 colors, so it ONLY counts for BU.
        # WUB Card has identity 3 colors, it shouldn't count for any 2-color pair based on logic.
        # Let's re-verify get_archetype_counts logic.
        # if len(identity) == 2: counts[identity] += 1
        # elif len(identity) == 1: for p in pairs: if identity in p: counts[p] += 1

        # So BR should be 0.
        self.assertEqual(counts["BR"], 0)

    def test_main_single_file(self):
        with patch('scripts.mtg_balance.jdecode.mtg_open_file') as mock_open:
            mock_open.return_value = self.cards
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_balance.py', 'dummy.json', '--no-color']):
                    balance_main()
                    output = fake_out.getvalue()
                    self.assertIn("ARCHETYPE BALANCE COMPARISON", output)
                    self.assertIn("Baseline: dummy.json", output)
                    self.assertIn("WU (Azorius)", output)
                    self.assertIn("50.0%", output) # 3/6 = 50%

    def test_main_multiple_files(self):
        cards2 = [
            Card({"name": "W Card", "manaCost": "{W}", "types": ["Creature"]}),
        ]
        with patch('scripts.mtg_balance.jdecode.mtg_open_file') as mock_open:
            mock_open.side_effect = [self.cards, cards2]
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_balance.py', 'base.json', 'target.json', '--no-color']):
                    balance_main()
                    output = fake_out.getvalue()
                    self.assertIn("Baseline: base.json", output)
                    self.assertIn("Delta", output)
                    # base.json WU is 50%. target.json WU: W card supports WU, GW, BW, RW.
                    # target.json has 1 card. W card is 100% of target.json.
                    # so WU in target is 100%. Delta is +50.0%.
                    self.assertIn("+50.0%", output)

    def test_main_filtering_and_limit(self):
        with patch('scripts.mtg_balance.jdecode.mtg_open_file') as mock_open:
            mock_open.return_value = self.cards
            with patch('sys.stdout', new=io.StringIO()):
                with patch('sys.argv', ['mtg_balance.py', 'dummy.json', '--limit', '2', '--set', 'MOM', '--rarity', 'rare']):
                    balance_main()
                    # Check if mtg_open_file was called with expected filters
                    mock_open.assert_called_with('dummy.json', verbose=False, sets=['MOM'], rarities=['rare'])
                    # self.cards[:2] should have been used.

    def test_main_no_cards(self):
        with patch('scripts.mtg_balance.jdecode.mtg_open_file') as mock_open:
            mock_open.return_value = []
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                with patch('sys.argv', ['mtg_balance.py', 'empty.json']):
                    balance_main()
                    self.assertIn("Warning: No cards found in empty.json", fake_err.getvalue())

    def test_main_quiet(self):
        with patch('scripts.mtg_balance.jdecode.mtg_open_file') as mock_open:
            mock_open.return_value = []
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                with patch('sys.argv', ['mtg_balance.py', 'empty.json', '--quiet']):
                    balance_main()
                    self.assertEqual(fake_err.getvalue(), "")

    def test_main_color_output(self):
        # We need to mock isatty or force color
        mock_stdout = MagicMock(spec=io.TextIOBase)
        mock_stdout.isatty.return_value = True

        captured_output = io.StringIO()
        mock_stdout.write.side_effect = captured_output.write

        with patch('scripts.mtg_balance.jdecode.mtg_open_file') as mock_open:
            mock_open.return_value = self.cards
            with patch('sys.stdout', mock_stdout):
                with patch('sys.argv', ['mtg_balance.py', 'dummy.json', '--color']):
                    balance_main()
                    output = captured_output.getvalue()
                    self.assertIn("\033[", output) # ANSI escape sequence

if __name__ == '__main__':
    unittest.main()
