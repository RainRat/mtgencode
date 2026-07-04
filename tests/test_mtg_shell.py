import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, 'lib'))

from scripts.mtg_query import handle_shell

class TestMtgShell(unittest.TestCase):

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
        card.get_pt_display.return_value = "2/2"
        card.get_loyalty_display.return_value = ""
        card.get_face_tokens.return_value = []
        card.pt = "&&/&&"
        card.pt_p = "&&"
        card.pt_t = "&&"
        card.loyalty = ""
        card.supertypes = []
        card.types = ["creature"]
        card.subtypes = ["bear"]
        card.search.return_value = True

        return card

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('scripts.mtg_query._execute_search')
    @patch('scripts.mtg_query._execute_oracle')
    @patch('scripts.mtg_query.handle_sets')
    @patch('scripts.mtg_query.handle_functional')
    @patch('scripts.mtg_query.handle_compare_cards')
    @patch('scripts.mtg_query.handle_reprints')
    @patch('scripts.mtg_query.handle_superior')
    @patch('scripts.mtg_query.handle_inferior')
    @patch('scripts.mtg_query.handle_extract')
    @patch('os.system')
    def test_shell_commands(self, mock_system, mock_extract, mock_inf, mock_sup,
                            mock_rep, mock_comp, mock_func, mock_sets,
                            mock_oracle, mock_search, mock_load):
        card = self._create_mock_card()
        mock_load.return_value = [card]

        args = MagicMock()
        args.infile = "dummy.json"
        args.color = False

        commands = [
            "/search Grizzly",
            "/s Grizzly",
            "/oracle Grizzly",
            "/o Grizzly",
            "/random",
            "/r 2",
            "/sets M20",
            "/st M20",
            "/functional",
            "/f",
            "/compare Grizzly Bears",
            "/c Grizzly Bears",
            "/reprints Grizzly",
            "/rep Grizzly",
            "/superior Grizzly",
            "/sup Grizzly",
            "/inferior Grizzly",
            "/inf Grizzly",
            "/extract LEA Grizzly",
            "/e LEA Grizzly",
            "/help",
            "/h",
            "/?",
            "/clear",
            "Grizzly Bears",
            "",
            "/search \"unclosed quote",
            "/invalid",
            "/reprints",
            "/superior",
            "/inferior",
            "/extract LEA",
            "exit"
        ]

        with patch('builtins.input', side_effect=commands):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(args)
                output = fake_out.getvalue()

        self.assertEqual(mock_search.call_count, 2)
        self.assertEqual(mock_oracle.call_count, 5)
        self.assertEqual(mock_sets.call_count, 2)
        self.assertEqual(mock_func.call_count, 2)
        self.assertEqual(mock_comp.call_count, 2)
        self.assertEqual(mock_rep.call_count, 2)
        self.assertEqual(mock_sup.call_count, 2)
        self.assertEqual(mock_inf.call_count, 2)
        self.assertEqual(mock_extract.call_count, 2)
        self.assertEqual(mock_system.call_count, 1)

        self.assertIn("SHELL COMMANDS", output)
        self.assertIn("Unknown command: /invalid", output)
        self.assertIn("Error: No closing quotation", output)
        self.assertIn("Error: /reprints requires a card name.", output)
        self.assertIn("Error: /superior requires a card name.", output)
        self.assertIn("Error: /inferior requires a card name.", output)
        self.assertIn("Error: /extract requires <set_code> and <card_name>.", output)

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    def test_shell_exit_variants(self, mock_load):
        mock_load.return_value = [self._create_mock_card()]
        args = MagicMock()
        args.infile = "dummy.json"
        args.color = False

        exit_variants = ['exit', 'quit', '/exit', '/quit', 'q', '/q']
        for var in exit_variants:
            with patch('builtins.input', side_effect=[var]):
                with patch('sys.stdout', new=io.StringIO()):
                    handle_shell(args)

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    def test_shell_load_failure(self, mock_load):
        mock_load.return_value = []
        args = MagicMock()
        args.infile = "dummy.json"
        args.color = False
        args.quiet = False

        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            handle_shell(args)
            self.assertIn("Error: Could not load card database.", fake_err.getvalue())

if __name__ == '__main__':
    unittest.main()
