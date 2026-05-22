import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os
import json
import csv

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

from scripts.mtg_manabase import main, calculate_manabase
import cardlib
from manalib import Manacost, Manatext

class TestMtgManabaseGaps(unittest.TestCase):

    def test_calculate_manabase_include_text(self):
        # Card with no pips in cost, but pips in activation
        card = MagicMock(spec=cardlib.Card)
        card.is_land = False
        card.cost = MagicMock(spec=Manacost)
        card.cost.allsymbols = {}
        card.text = MagicMock(spec=Manatext)

        act_cost = MagicMock(spec=Manacost)
        act_cost.allsymbols = {'R': 1}
        card.text.costs = [act_cost]
        card.bside = None

        # include_text=False (default)
        rec, pips, total = calculate_manabase([card], 10, include_text=False)
        self.assertEqual(total, 0)
        self.assertEqual(rec['Wastes'], 10)

        # include_text=True
        rec, pips, total = calculate_manabase([card], 10, include_text=True)
        self.assertEqual(total, 1)
        self.assertEqual(pips['R'], 1)
        self.assertEqual(rec['Mountain'], 10)

    def test_calculate_manabase_bside(self):
        # Card with pips on bside
        card = MagicMock(spec=cardlib.Card)
        card.is_land = False
        card.cost = MagicMock(spec=Manacost)
        card.cost.allsymbols = {'G': 1}
        card.text = MagicMock(spec=Manatext)
        card.text.costs = []

        bside = MagicMock()
        bside.cost = MagicMock(spec=Manacost)
        bside.cost.allsymbols = {'U': 1}
        bside.text = MagicMock(spec=Manatext)
        bside.text.costs = []

        card.bside = bside

        rec, pips, total = calculate_manabase([card], 10)
        self.assertEqual(total, 2)
        self.assertEqual(pips['G'], 1)
        self.assertEqual(pips['U'], 1)
        self.assertEqual(rec['Forest'], 5)
        self.assertEqual(rec['Island'], 5)

    def test_calculate_manabase_no_pips(self):
        # Only colorless spells
        card = MagicMock(spec=cardlib.Card)
        card.is_land = False
        card.cost = MagicMock(spec=Manacost)
        card.cost.allsymbols = {'C': 1}
        card.text = MagicMock(spec=Manatext)
        card.text.costs = []
        card.bside = None

        rec, pips, total = calculate_manabase([card], 10)
        self.assertEqual(total, 0)
        self.assertEqual(rec['Wastes'], 10)
        self.assertEqual(sum(rec.values()), 10)

    def test_calculate_manabase_is_land_skip(self):
        # Land with pips (like Dryad Arbor or a land with a cost for some reason)
        card = MagicMock(spec=cardlib.Card)
        card.is_land = True
        card.cost = MagicMock(spec=Manacost)
        card.cost.allsymbols = {'G': 1}
        card.text = MagicMock(spec=Manatext)
        card.text.costs = []
        card.bside = None

        rec, pips, total = calculate_manabase([card], 10)
        self.assertEqual(total, 0)
        self.assertEqual(rec['Wastes'], 10)

    def test_main_json_output(self):
        card = MagicMock(spec=cardlib.Card)
        card.is_land = False
        card.cost = MagicMock(spec=Manacost)
        card.cost.allsymbols = {'W': 1}
        card.text = MagicMock(spec=Manatext)
        card.text.costs = []
        card.bside = None

        with patch('jdecode.mtg_open_file', return_value=[card]):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_manabase.py', 'dummy.json', '--json']):
                    main()
                    output = fake_out.getvalue()
                    data = json.loads(output)
                    self.assertEqual(data['recommendation']['Plains'], 24)
                    self.assertEqual(data['total_pips'], 1)

    def test_main_csv_output(self):
        card = MagicMock(spec=cardlib.Card)
        card.is_land = False
        card.cost = MagicMock(spec=Manacost)
        card.cost.allsymbols = {'U': 1}
        card.text = MagicMock(spec=Manatext)
        card.text.costs = []
        card.bside = None

        with patch('jdecode.mtg_open_file', return_value=[card]):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_manabase.py', 'dummy.json', '--csv']):
                    main()
                    output = fake_out.getvalue()
                    reader = csv.DictReader(io.StringIO(output))
                    rows = list(reader)
                    # Check for Island recommendation
                    island_row = next(r for r in rows if r['Item'] == 'Island')
                    self.assertEqual(island_row['Value'], '24')

    def test_main_smart_positional_arg(self):
        # If file doesn't exist, it should be treated as a grep pattern
        with patch('os.path.exists', side_effect=lambda x: x == 'data/AllPrintings.json'):
            with patch('jdecode.mtg_open_file', return_value=[]) as mock_open:
                with patch('sys.stdin.isatty', return_value=True):
                    with patch('sys.stdout', new=io.StringIO()):
                        with patch('sys.argv', ['mtg_manabase.py', 'Dragon']):
                            main()
                            # Check that 'Dragon' was passed as grep
                            args, kwargs = mock_open.call_args
                            self.assertEqual(kwargs['grep'], ['Dragon'])
                            # And infile became default data
                            self.assertEqual(args[0], 'data/AllPrintings.json')

    def test_main_smart_dataset_detection(self):
        # Mocking file existence to trigger default dataset logic
        def side_effect(path):
            if path == 'data/AllPrintings.json': return True
            return False

        with patch('os.path.exists', side_effect=side_effect):
            with patch('sys.stdin.isatty', return_value=True):
                 with patch('jdecode.mtg_open_file', return_value=[]) as mock_open:
                     with patch('sys.stdout', new=io.StringIO()):
                         with patch('sys.argv', ['mtg_manabase.py']):
                             main()
                             self.assertEqual(mock_open.call_args[0][0], 'data/AllPrintings.json')

    def test_calculate_manabase_low_land_count(self):
        # 5 colors, 3 lands. This should NOT result in negative lands.
        cards = []
        for c in 'WUBRG':
            card = MagicMock(spec=cardlib.Card)
            card.is_land = False
            card.cost = MagicMock(spec=Manacost)
            card.cost.allsymbols = {c: 1}
            card.text = MagicMock(spec=Manatext)
            card.text.costs = []
            card.bside = None
            cards.append(card)

        # target_lands = 3.
        # Current bug: remaining_lands becomes 3 - 5 = -2.
        # Then share = (1/5) * -2 = -0.4. allocated = 0.
        # Plains starts at 1, stays at 1. Total = 5.
        # Wastes = 3 - 5 = -2!
        recommendation, pips, total = calculate_manabase(cards, 3)

        # We want to ensure no negative counts and sum is target_lands
        for val in recommendation.values():
            self.assertGreaterEqual(val, 0, f"Value for {val} is negative")
        self.assertEqual(sum(recommendation.values()), 3)

if __name__ == '__main__':
    unittest.main()
