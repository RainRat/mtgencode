import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os
import re
from argparse import Namespace

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_query import handle_shell
import utils

class TestMtgShell(unittest.TestCase):

    def setUp(self):
        self.args = Namespace(
            infile='dummy.json',
            color=False,
            quiet=False,
            fields='name,cost,type,stats,rarity',
            limit=0,
            sample=0,
            verbose=False,
            similar=False,
            full=False,
            gatherer=False,
            no_rulings=False,
            sort=None,
            reverse=False,
            delimiter=' | ',
            table=False,
            json=False,
            jsonl=False,
            csv=False,
            md_table=False,
            summary=False,
            text=False,
            outfile=None,
            grep_name=None,
            grep=None
        )

        # Create a mock card
        self.card = MagicMock()
        self.card.name = "Grizzly Bears"
        self.card.display_name = "Grizzly Bears"
        self.card.search.return_value = True
        self.card.search_name.return_value = True
        self.card.header.return_value = "Grizzly Bears Header"
        self.card.summary.return_value = "[O] Grizzly Bears {1}{G} • Creature - Bear • (2/2)"
        self.card.get_text.return_value = "Vanilla"
        self.card.bside = None
        self.card.cost = MagicMock()
        self.card.cost.cmc = 2
        self.card.cost.format.return_value = "{1}{G}"
        self.card.cost.colors = ["G"]
        self.card.is_creature = True
        self.card.is_planeswalker = False
        self.card.is_battle = False
        self.card.is_legendary = False
        self.card.is_permanent = True
        self.card.mechanics = set()
        self.card.actions = set()
        self.card.produced_colors = set()
        self.card.color_identity = "G"
        self.card.rarity_name = "Common"
        self.card.complexity_score = 5
        self.card.power_rating = 1.0
        self.card.recommended_cmc = 2.0
        self.card.legalities = {}
        self.card.rulings = []

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_exit(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['exit']

        handle_shell(self.args)
        self.assertIn("MTG Interactive Shell", mock_stdout.getvalue())

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_oracle_lookup(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['Grizzly Bears', 'exit']

        handle_shell(self.args)
        self.assertIn("Grizzly Bears Header", mock_stdout.getvalue())

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_slash_oracle_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/oracle Grizzly Bears', 'exit']

        handle_shell(self.args)
        self.assertIn("Grizzly Bears Header", mock_stdout.getvalue())

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_search_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/search Bears', 'exit']

        handle_shell(self.args)
        self.assertIn("SEARCH RESULTS", mock_stdout.getvalue())
        self.assertIn("Grizzly Bears", mock_stdout.getvalue())

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_help_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/help', 'exit']

        handle_shell(self.args)
        self.assertIn("SHELL COMMANDS", mock_stdout.getvalue())
        self.assertIn("/search", mock_stdout.getvalue())

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('os.system')
    def test_shell_clear_command(self, mock_os, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/clear', 'exit']

        handle_shell(self.args)
        mock_os.assert_called()

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_random_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/random', 'exit']

        handle_shell(self.args)
        self.assertIn("SEARCH RESULTS", mock_stdout.getvalue())

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_sets_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/sets', 'exit']

        with patch('scripts.mtg_query.handle_sets') as mock_sets:
            handle_shell(self.args)
            mock_sets.assert_called()

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_functional_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/functional', 'exit']

        with patch('scripts.mtg_query.handle_functional') as mock_func:
            handle_shell(self.args)
            mock_func.assert_called()

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_compare_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/compare "Grizzly Bears"', 'exit']

        with patch('scripts.mtg_query.handle_compare_cards') as mock_comp:
            handle_shell(self.args)
            mock_comp.assert_called()

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_reprints_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/reprints "Grizzly Bears"', 'exit']

        with patch('scripts.mtg_query.handle_reprints') as mock_rep:
            handle_shell(self.args)
            mock_rep.assert_called()

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_superior_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/superior "Grizzly Bears"', 'exit']

        with patch('scripts.mtg_query.handle_superior') as mock_sup:
            handle_shell(self.args)
            mock_sup.assert_called()

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_inferior_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/inferior "Grizzly Bears"', 'exit']

        with patch('scripts.mtg_query.handle_inferior') as mock_inf:
            handle_shell(self.args)
            mock_inf.assert_called()

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_extract_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/extract LEA "Grizzly Bears"', 'exit']

        with patch('scripts.mtg_query.handle_extract') as mock_ext:
            handle_shell(self.args)
            mock_ext.assert_called()

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_malformed_input(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/search "unbalanced quotes', 'exit']

        handle_shell(self.args)
        self.assertIn("Error: No closing quotation", mock_stdout.getvalue())

    @patch('scripts.mtg_query.cli_utils.load_and_filter_cards')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_unknown_command(self, mock_stdout, mock_input, mock_load):
        mock_load.return_value = [self.card]
        mock_input.side_effect = ['/unknown', 'exit']

        handle_shell(self.args)
        self.assertIn("Unknown command", mock_stdout.getvalue())

if __name__ == '__main__':
    unittest.main()
