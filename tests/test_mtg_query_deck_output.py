import os
import sys
import unittest
import tempfile
import json
from unittest.mock import patch
from io import StringIO

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib import cardlib
from scripts import mtg_query


class TestMtgQueryDeckOutput(unittest.TestCase):

    def test_search_deck_output_stdout(self):
        test_card = cardlib.Card('|5instant|9target creature gets +&^^^/+&^^^ until end of turn.|3{G}|0O|1giant growth|')
        with patch('cli_utils.load_and_filter_cards', return_value=[test_card, test_card]):
            test_args = ['mtg_query.py', 'search', 'dummy.json', '--deck']
            with patch.object(sys, 'argv', test_args):
                with patch('sys.stdout', new_callable=StringIO) as fake_out:
                    mtg_query.main()
                    output = fake_out.getvalue().strip().splitlines()

        self.assertEqual(len(output), 1)
        self.assertEqual(output[0], '2 Giant Growth')

    def test_search_deck_outfile_autodetect(self):
        test_card1 = cardlib.Card('|5instant|9target creature gets +&^^^/+&^^^ until end of turn.|3{G}|0O|1giant growth|')
        test_card2 = cardlib.Card('|5creature|6bear|8&^^/&^^|3{1}{G}|0O|1grizzly bears|')

        tmp_deck = tempfile.NamedTemporaryFile(suffix='.deck', mode='w+', delete=False, encoding='utf-8')
        tmp_deck.close()

        try:
            with patch('cli_utils.load_and_filter_cards', return_value=[test_card1, test_card1, test_card2]):
                test_args = ['mtg_query.py', 'search', 'dummy.json', tmp_deck.name]
                with patch.object(sys, 'argv', test_args):
                    mtg_query.main()

            with open(tmp_deck.name, 'r', encoding='utf-8') as f:
                content = f.read().strip().splitlines()

            self.assertEqual(len(content), 2)
            self.assertIn('2 Giant Growth', content)
            self.assertIn('1 Grizzly Bears', content)
        finally:
            if os.path.exists(tmp_deck.name):
                os.remove(tmp_deck.name)


if __name__ == '__main__':
    unittest.main()
