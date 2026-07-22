import unittest
import io
import sys
import os
import argparse
from unittest.mock import patch, MagicMock
from scripts.mtg_query import handle_shell

class TestMtgShell(unittest.TestCase):

    def setUp(self):
        self.test_json = "testdata/tarkir.json"
        # Mocking a basic args namespace
        self.args = argparse.Namespace(
            infile=self.test_json,
            quiet=False,
            color=False,
            verbose=False,
            limit=0,
            fields='name,cost,type,stats,rarity',
            json=False,
            grep=None,
            sort=None,
            reverse=False,
            table=False,
            outfile=None
        )

    def test_shell_exit(self):
        """Test exiting the shell."""
        with patch('builtins.input', side_effect=['exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                self.assertIn("MTG Interactive Shell", fake_out.getvalue())

    def test_shell_help(self):
        """Test the help command in the shell."""
        with patch('builtins.input', side_effect=['/help', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("SHELL COMMANDS", output)
                self.assertIn("/search", output)
                self.assertIn("/oracle", output)

    def test_shell_oracle_lookup(self):
        """Test looking up a card name (default oracle behavior)."""
        with patch('builtins.input', side_effect=['invasion of tarkir', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Invasion of Tarkir", output)

    def test_shell_compare_range(self):
        """Test the /compare command with index ranges and comma separation."""
        with patch('builtins.input', side_effect=['/search tarkir', '/compare 1-1, 1', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Invasion of Tarkir", output)

    def test_shell_compare_comma_fallback(self):
        """Test fallback and trailing commas in /compare command."""
        with patch('builtins.input', side_effect=['/search tarkir', '/compare 1,', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Invasion of Tarkir", output)
                self.assertIn("Battle", output)

    def test_shell_search(self):
        """Test the /search command."""
        with patch('builtins.input', side_effect=['/search tarkir', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                # Table output check
                self.assertIn("Invasion of Tarkir", output)

    def test_shell_random(self):
        """Test the /random command."""
        with patch('builtins.input', side_effect=['/random 1', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Invasion of Tarkir", output)

    def test_shell_sets(self):
        """Test the /sets command."""
        with patch('builtins.input', side_effect=['/sets CUS', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("CUS", output)
                self.assertIn("custom", output)

    def test_shell_functional(self):
        """Test the /functional command."""
        # Need at least 2 cards for functional to match if no grep.
        # Actually /functional uses load_and_filter_cards(args).
        with patch('builtins.input', side_effect=['/functional', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.stderr', new=io.StringIO()) as fake_err:
                    handle_shell(self.args)
                    err = fake_err.getvalue()
                    self.assertIn("No cards with the same mechanics found.", err)

    def test_shell_compare(self):
        """Test the /compare command."""
        # Comparing the same card with itself
        with patch('builtins.input', side_effect=['/compare "invasion of tarkir" "invasion of tarkir"', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Invasion of Tarkir", output)

    def test_shell_reprints(self):
        """Test the /reprints command."""
        with patch('builtins.input', side_effect=['/reprints "invasion of tarkir"', 'exit']):
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                handle_shell(self.args)
                err = fake_err.getvalue()
                self.assertIn("No functional reprints found for Invasion of Tarkir.", err)

    def test_shell_superior_inferior(self):
        """Test the /superior and /inferior commands."""
        with patch('builtins.input', side_effect=['/superior "invasion of tarkir"', '/inferior "invasion of tarkir"', 'exit']):
            with patch('sys.stderr', new=io.StringIO()) as fake_err:
                handle_shell(self.args)
                err = fake_err.getvalue()
                self.assertIn("No cards found that are superior to Invasion of Tarkir.", err)
                self.assertIn("No cards found that are inferior to Invasion of Tarkir.", err)

    def test_shell_extract(self):
        """Test the /extract command."""
        with patch('builtins.input', side_effect=['/extract CUS "invasion of tarkir"', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn('"name": "invasion of tarkir"', output)

    def test_shell_clear(self):
        """Test the /clear command."""
        with patch('builtins.input', side_effect=['/clear', 'exit']):
            with patch('os.system') as mock_system:
                handle_shell(self.args)
                mock_system.assert_called()

    def test_shell_malformed_input(self):
        """Test malformed shlex input."""
        with patch('builtins.input', side_effect=['/search "unclosed quote', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                self.assertIn("Error: No closing quotation", fake_out.getvalue())

    def test_shell_tab_completion(self):
        """Test the tab completion logic."""
        with patch('readline.set_completer') as mock_set_completer:
            with patch('builtins.input', side_effect=['exit']):
                handle_shell(self.args)
                self.assertTrue(mock_set_completer.called)
                completer = mock_set_completer.call_args[0][0]

                # Test command completion
                self.assertEqual(completer('/', 0), '/search ')
                self.assertEqual(completer('/s', 0), '/search ')
                self.assertEqual(completer('/s', 1), '/s ')

                # Test card name completion
                self.assertEqual(completer('inv', 0), 'Invasion of Tarkir')

    def test_shell_list_empty(self):
        """Test executing /list with an empty search history."""
        with patch('builtins.input', side_effect=['/list', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                self.assertIn("No previous search results to display.", fake_out.getvalue())

    def test_shell_list_populated(self):
        """Test executing /list (and /l and /results) after a search has been executed."""
        # 1. Test /list
        with patch('builtins.input', side_effect=['/search tarkir', '/list', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                # Ensure the search table displayed once for search and once for list
                self.assertEqual(output.count("Invasion of Tarkir"), 2)

        # 2. Test /l
        with patch('builtins.input', side_effect=['/search tarkir', '/l', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertEqual(output.count("Invasion of Tarkir"), 2)

        # 3. Test /results
        with patch('builtins.input', side_effect=['/search tarkir', '/results', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertEqual(output.count("Invasion of Tarkir"), 2)

    def test_shell_list_tab_completion(self):
        """Test the tab completion logic for /list, /l, and /results."""
        with patch('readline.set_completer') as mock_set_completer:
            with patch('builtins.input', side_effect=['exit']):
                handle_shell(self.args)
                self.assertTrue(mock_set_completer.called)
                completer = mock_set_completer.call_args[0][0]

                # Test command completion for /list, /l, /results
                self.assertEqual(completer('/li', 0), '/list')
                self.assertEqual(completer('/results', 0), '/results')
                self.assertEqual(completer('/l', 0), '/list')
                self.assertEqual(completer('/l', 1), '/l')

    def test_shell_unknown_command_suggestions(self):
        """Test suggestions for misspelled or unknown slash commands."""
        # 1. Close match '/searc' -> Suggests '/search'
        with patch('builtins.input', side_effect=['/searc', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Unknown command: /searc. Did you mean /search? Type /help for assistance.", output)

        # 2. Close match '/orcl' -> Suggests '/oracle'
        with patch('builtins.input', side_effect=['/orcl', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Unknown command: /orcl. Did you mean /oracle? Type /help for assistance.", output)

        # 3. No close match '/xyz' -> No suggestion
        with patch('builtins.input', side_effect=['/xyz', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Unknown command: /xyz. Type /help for assistance.", output)
                self.assertNotIn("Did you mean", output)

if __name__ == '__main__':
    unittest.main()
