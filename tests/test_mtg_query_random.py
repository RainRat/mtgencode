import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import io
import sys
import os
import random

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_query import main as query_main
import cardlib
import utils

class TestMtgQueryRandom(unittest.TestCase):

    def _create_mock_card(self, name="Grizzly Bears"):
        card = MagicMock()
        card.name = name
        card.display_name = name
        card.header.return_value = name
        card.summary.return_value = name
        card.get_text.return_value = "Vanilla creature"

        card.cost = MagicMock()
        card.cost.format.return_value = "{1}{G}"
        card.cost.cmc = 2
        card.cost.colors = ['G']
        card.cost.encode.return_value = "{^G}"

        card.is_creature = True
        card.is_battle = False
        card.tokens = []
        card.mechanics = set()
        card.actions = set()
        card.produced_colors = set()
        card.color_identity = "G"
        card.rarity = "O"
        card.rarity_name = "Common"
        card.complexity_score = 10
        card.power_rating = 1.0
        card.recommended_cmc = 2.0

        card.set_code = "LEA"
        card.number = "1"
        card.rulings = []
        card.bside = None
        card.get_type_line.return_value = "Creature - Bear"
        card._get_pt_display.return_value = "2/2"
        card._get_loyalty_display.return_value = ""
        card.get_face_tokens.return_value = []
        card.pt = "&&/&&"
        card.pt_p = "&&"
        card.pt_t = "&&"
        card.loyalty = ""
        card.supertypes = []
        card.types = ["creature"]
        card.subtypes = ["bear"]

        return card

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    def test_random_basic(self, mock_load):
        """Test basic random card display."""
        card = self._create_mock_card()
        mock_load.return_value = [card]

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_query.py', 'random', '--no-color']):
                query_main()
                output = fake_out.getvalue()
                # Basic random uses _execute_oracle which shows the card header
                self.assertIn("Grizzly Bears", output)

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    def test_random_count(self, mock_load):
        """Test random with a specific count."""
        cards = [self._create_mock_card(f"Card {i}") for i in range(5)]
        mock_load.return_value = cards

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            # Oracle view doesn't have a count header, it just prints cards
            with patch('sys.argv', ['mtg_query.py', 'random', '3', 'dummy.json', '--no-color']):
                query_main()
                output = fake_out.getvalue()
                matches = 0
                for i in range(5):
                    if f"Card {i}" in output:
                        matches += 1
                self.assertEqual(matches, 3)

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    def test_random_table(self, mock_load):
        """Test random with table output."""
        card = self._create_mock_card()
        mock_load.return_value = [card]

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_query.py', 'random', '--table', '--no-color']):
                query_main()
                output = fake_out.getvalue()
                self.assertIn("SEARCH RESULTS", output)
                self.assertIn("Grizzly Bears", output)
                self.assertIn("CMC", output)
                self.assertIn("Stats", output)

if __name__ == '__main__':
    unittest.main()
