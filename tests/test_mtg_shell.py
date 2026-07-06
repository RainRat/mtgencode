import unittest
from unittest.mock import patch, MagicMock
import io
import os
import argparse
import scripts.mtg_query as mtg_query

class TestMtgShell(unittest.TestCase):

    def setUp(self):
        self.test_file = "testdata/uthros.json"
        if not os.path.exists(self.test_file):
             # Create a small test file if it doesn't exist, though it should based on previous tool output
             import json
             with open(self.test_file, 'w') as f:
                 json.dump([
                     {
                         "name": "Uthros Research Craft",
                         "manaCost": "{4}",
                         "types": ["Artifact"],
                         "subtypes": ["Spacecraft"],
                         "text": "Flying",
                         "rarity": "Common",
                         "set": "TEST"
                     }
                 ], f)

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_basic_flow(self, mock_stdout, mock_input):
        # Sequence of inputs:
        # 1. /help
        # 2. Unknown command
        # 3. Empty line
        # 4. /search Uthros
        # 5. Uthros Research Craft (direct lookup)
        # 6. /exit
        mock_input.side_effect = [
            "/help",
            "/unknown",
            "",
            "/search Uthros",
            "Uthros Research Craft",
            "exit"
        ]

        args = argparse.Namespace(
            infile=self.test_file,
            color=False,
            fields='name,cost,type,stats,rarity',
            outfile=None,
            command='shell',
            quiet=False
        )

        with patch('scripts.mtg_query.handle_sets'): # Mock heavy sub-functions if needed
            mtg_query.handle_shell(args)

        output = mock_stdout.getvalue()
        self.assertIn("SHELL COMMANDS", output)
        self.assertIn("Unknown command: /unknown", output)
        self.assertIn("Uthros Research Craft", output)
        self.assertIn("Artifact", output)

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_commands(self, mock_stdout, mock_input):
        mock_input.side_effect = [
            "/s Uthros",
            "/o Uthros",
            "/r 1",
            "/rep", # Missing arg
            "/rep Uthros",
            "/sup", # Missing arg
            "/sup Uthros",
            "/inf", # Missing arg
            "/inf Uthros",
            "/e", # Missing arg
            "/e TEST Uthros",
            "/q"
        ]

        args = argparse.Namespace(
            infile=self.test_file,
            color=False,
            fields='name,cost,type,stats,rarity',
            outfile=None,
            command='shell',
            quiet=False
        )

        with patch('scripts.mtg_query.handle_sets'), \
             patch('scripts.mtg_query.handle_functional'), \
             patch('scripts.mtg_query.handle_compare_cards'), \
             patch('scripts.mtg_query.handle_reprints'), \
             patch('scripts.mtg_query.handle_superior'), \
             patch('scripts.mtg_query.handle_inferior'), \
             patch('scripts.mtg_query.handle_extract'):
            mtg_query.handle_shell(args)

        output = mock_stdout.getvalue()
        self.assertIn("Error: /reprints requires a card name.", output)
        self.assertIn("Error: /superior requires a card name.", output)
        self.assertIn("Error: /inferior requires a card name.", output)
        self.assertIn("Error: /extract requires <set_code> and <card_name>.", output)

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('os.system')
    def test_shell_misc(self, mock_os_system, mock_stdout, mock_input):
        mock_input.side_effect = [
            "/clear",
            "/sets",
            "/st",
            "/f",
            "/c cardA cardB",
            "quit"
        ]

        args = argparse.Namespace(
            infile=self.test_file,
            color=False,
            fields='name,cost,type,stats,rarity',
            outfile=None,
            command='shell',
            quiet=False
        )

        with patch('scripts.mtg_query.handle_sets') as mock_sets, \
             patch('scripts.mtg_query.handle_functional') as mock_func, \
             patch('scripts.mtg_query.handle_compare_cards') as mock_comp:
            mtg_query.handle_shell(args)

        mock_os_system.assert_called()
        self.assertEqual(mock_sets.call_count, 2)
        self.assertEqual(mock_func.call_count, 1)
        self.assertEqual(mock_comp.call_count, 1)

    @patch('builtins.input', side_effect=EOFError)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_eof(self, mock_stdout, mock_input):
        args = argparse.Namespace(
            infile=self.test_file,
            color=False,
            fields='name,cost,type,stats,rarity',
            outfile=None,
            command='shell',
            quiet=False
        )
        mtg_query.handle_shell(args)
        # Should just exit gracefully

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_shell_shlex_error(self, mock_stdout, mock_input):
        mock_input.side_effect = [
            '/search "unclosed quote',
            'exit'
        ]
        args = argparse.Namespace(
            infile=self.test_file,
            color=False,
            fields='name,cost,type,stats,rarity',
            outfile=None,
            command='shell',
            quiet=False
        )
        mtg_query.handle_shell(args)
        self.assertIn("Error: No closing quotation", mock_stdout.getvalue())

if __name__ == '__main__':
    unittest.main()
