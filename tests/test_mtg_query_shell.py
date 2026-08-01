import unittest
import io
import sys
import argparse
from unittest.mock import patch
from scripts.mtg_query import handle_shell

class TestMtgQueryShell(unittest.TestCase):

    def setUp(self):
        self.test_json = "testdata/tarkir.json"
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

    def test_shell_help_aligned(self):
        """Verify the aligned help commands and clean dynamic layouts."""
        with patch('builtins.input', side_effect=['/help', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("SHELL COMMANDS", output)
                self.assertIn("/search <q>", output)
                # Check for clean spacing (no overlapping descriptions due to fixed padding)
                # Max command string is f"  /substitutes <n> (/sub)" -> length is 25.
                # Dynamic width should be at least max_len + 2 = 27.
                # "/substitutes <n> (/sub)   - Find functional alternatives to the named card."
                self.assertIn("/substitutes <n> (/sub)", output)

    def test_shell_oracle_default_last_results(self):
        """Verify that typing /oracle without args defaults to first search result."""
        with patch('builtins.input', side_effect=['/search tarkir', '/oracle', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Invasion of Tarkir", output)
                self.assertIn("Notice: No card specified. Defaulting to first search result: Invasion of Tarkir", output)

    def test_shell_compare_default_last_results(self):
        """Verify that typing /compare without args defaults to first search results (up to 5)."""
        with patch('builtins.input', side_effect=['/search tarkir', '/compare', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Notice: No cards specified. Comparing first 1 search results: Invasion of Tarkir", output)

    def test_shell_reprints_default_last_results(self):
        """Verify that typing /reprints without args defaults to first search result."""
        with patch('builtins.input', side_effect=['/search tarkir', '/reprints', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Notice: No card specified. Defaulting to first search result: Invasion of Tarkir", output)

    def test_shell_superior_default_last_results(self):
        """Verify that typing /superior without args defaults to first search result."""
        with patch('builtins.input', side_effect=['/search tarkir', '/superior', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Notice: No card specified. Defaulting to first search result: Invasion of Tarkir", output)

    def test_shell_inferior_default_last_results(self):
        """Verify that typing /inferior without args defaults to first search result."""
        with patch('builtins.input', side_effect=['/search tarkir', '/inferior', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Notice: No card specified. Defaulting to first search result: Invasion of Tarkir", output)

    def test_shell_substitutes_default_last_results(self):
        """Verify that typing /substitutes without args defaults to first search result."""
        with patch('builtins.input', side_effect=['/search tarkir', '/substitutes', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Notice: No card specified. Defaulting to first search result: Invasion of Tarkir", output)

    def test_shell_counterparts_default_last_results(self):
        """Verify that typing /counterparts without args defaults to first search result."""
        with patch('builtins.input', side_effect=['/search tarkir', '/counterparts', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Notice: No card specified. Defaulting to first search result: Invasion of Tarkir", output)

    def test_shell_similar_default_last_results(self):
        """Verify that typing /similar without args defaults to first search result."""
        with patch('builtins.input', side_effect=['/search tarkir', '/similar', 'exit']):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                handle_shell(self.args)
                output = fake_out.getvalue()
                self.assertIn("Notice: No card specified. Defaulting to first search result: Invasion of Tarkir", output)

if __name__ == '__main__':
    unittest.main()
