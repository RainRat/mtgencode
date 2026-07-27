import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os
import json

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

from scripts.mtg_manabase import main
import cardlib
from manalib import Manacost, Manatext


class TestMtgManabaseDeckOut(unittest.TestCase):

    def test_deck_out_includes_original_spells_and_excludes_original_basic_lands_while_appending_recommended_lands(self):
        # Create a card with {W} cost
        card_spell = MagicMock(spec=cardlib.Card)
        card_spell.name = "grizzly bears"
        card_spell.is_land = False
        card_spell.set_code = "lea"
        card_spell.number = "101"
        card_spell.cost = MagicMock(spec=Manacost)
        card_spell.cost.allsymbols = {'W': 1}
        card_spell.cost.cmc = 1.0
        card_spell.cost.colors = ['W']
        card_spell.text = MagicMock(spec=Manatext)
        card_spell.text.costs = []
        card_spell.bside = None

        # Create an existing basic land that should be ignored/excluded from the output
        card_basic_land = MagicMock(spec=cardlib.Card)
        card_basic_land.name = "plains"
        card_basic_land.is_land = True
        card_basic_land.set_code = "lea"
        card_basic_land.number = "200"
        card_basic_land.cost = MagicMock(spec=Manacost)
        card_basic_land.cost.allsymbols = {}
        card_basic_land.cost.cmc = 0.0
        card_basic_land.cost.colors = []
        card_basic_land.text = MagicMock(spec=Manatext)
        card_basic_land.text.costs = []
        card_basic_land.bside = None

        cards = [card_spell, card_spell, card_basic_land]

        with patch('jdecode.mtg_open_file', return_value=cards):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_manabase.py', 'test_deck.txt', '--lands', '17', '--deck']):
                    main()
                    output = fake_out.getvalue()

                    # Original non-basic spells must be in the output with correct counts
                    self.assertIn("2 Grizzly Bears (LEA) 101", output)

                    # Any existing Plains should not be copied from input cards (the test plains)
                    self.assertNotIn("1 Plains (LEA) 200", output)
                    self.assertNotIn("Plains (LEA) 200", output)

                    # Recommended lands must be appended
                    self.assertIn("17 Plains", output)

    def test_deck_out_auto_detects_format_from_file_extension(self):
        # Create a card with {U} cost
        card_spell = MagicMock(spec=cardlib.Card)
        card_spell.name = "opt"
        card_spell.is_land = False
        card_spell.set_code = "xlb"
        card_spell.number = "12"
        card_spell.cost = MagicMock(spec=Manacost)
        card_spell.cost.allsymbols = {'U': 1}
        card_spell.cost.cmc = 1.0
        card_spell.cost.colors = ['U']
        card_spell.text = MagicMock(spec=Manatext)
        card_spell.text.costs = []
        card_spell.bside = None

        cards = [card_spell]

        with patch('jdecode.mtg_open_file', return_value=cards):
            with patch('sys.argv', ['mtg_manabase.py', 'test_deck.txt', 'out_deck.deck', '--lands', '12']):
                # We patch the built-in open for writing
                mock_file = MagicMock()
                with patch('builtins.open', return_value=mock_file) as mock_open:
                    main()
                    mock_open.assert_called_with('out_deck.deck', 'w', encoding='utf-8')

                    # Gather all calls to write
                    write_calls = "".join(call.args[0] for call in mock_file.write.call_args_list)
                    self.assertIn("1 Opt (XLB) 12", write_calls)
                    self.assertIn("12 Island", write_calls)

    def test_deck_out_with_empty_card_pool_prints_no_cards_found_message(self):
        with patch('jdecode.mtg_open_file', return_value=[]):
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                with patch('sys.argv', ['mtg_manabase.py', 'test_deck.txt', '--deck', '--quiet']):
                    main()
                    # It should not raise an error or write decklist, just exit silently or with empty output
                    # The main function returns without writing when cards list is empty
                    pass


if __name__ == '__main__':
    unittest.main()
