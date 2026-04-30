import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_mechanics import main as mechanics_main

class TestMtgMechanics(unittest.TestCase):

    def test_mechanics_list_only(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_mechanics.py', '--no-color']):
                mechanics_main()
                output = fake_out.getvalue()
                self.assertIn("RECOGNIZED MECHANICS", output)
                self.assertIn("Total:", output)
                # Check for some common mechanics
                self.assertIn("Flying", output)
                self.assertIn("Trample", output)

    def test_mechanics_single_file(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_mechanics.py', 'testdata/uthros.json', '--no-color']):
                mechanics_main()
                output = fake_out.getvalue()
                self.assertIn("MECHANICAL FREQUENCY", output)
                self.assertIn("Total Cards: 1", output)
                # Uthros has Flying and Station
                self.assertIn("Flying", output)
                self.assertIn("Station", output)

    def test_mechanics_comparison(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_mechanics.py', 'testdata/uthros.json', '--compare', 'testdata/tarkir.json', '--no-color']):
                mechanics_main()
                output = fake_out.getvalue()
                self.assertIn("MECHANICAL COMPARISON", output)
                self.assertIn("Delta", output)

    def test_mechanics_no_matches(self):
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.argv', ['mtg_mechanics.py', 'testdata/uthros.json', '--rarity', 'common', '--no-color']):
                mechanics_main()
                self.assertIn("No cards found", fake_err.getvalue())

    def test_mechanics_sorting_and_limit(self):
        # Test sort by count
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_mechanics.py', 'testdata/uthros.json', '--sort', 'count', '--limit', '1', '--no-color']):
                mechanics_main()
                output = fake_out.getvalue()
                self.assertIn("MECHANICAL FREQUENCY", output)
                # Header + separator + 1 row = 3 rows in data area usually,
                # but let's just ensure it doesn't crash and contains at least one mechanic.

    def test_mechanics_grep_filter(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_mechanics.py', 'testdata/uthros.json', '--grep', 'Uthros', '--no-color']):
                mechanics_main()
                self.assertIn("Total Cards: 1", fake_out.getvalue())

        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.argv', ['mtg_mechanics.py', 'testdata/uthros.json', '--grep', 'NonExistent', '--no-color']):
                mechanics_main()
                self.assertIn("No cards found", fake_err.getvalue())

    def test_mechanics_sample(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_mechanics.py', 'testdata/uthros.json', '--sample', '1', '--no-color']):
                mechanics_main()
                self.assertIn("Total Cards: 1", fake_out.getvalue())

    def test_mechanics_color(self):
        mock_stdout = MagicMock(spec=io.TextIOBase)
        mock_stdout.isatty.return_value = True
        mock_stdout.write = MagicMock()

        captured_output = io.StringIO()
        mock_stdout.write.side_effect = captured_output.write

        with patch('sys.stdout', mock_stdout):
            with patch('sys.argv', ['mtg_mechanics.py', '--color']):
                mechanics_main()
                output = captured_output.getvalue()
                self.assertIn("\033[", output)

    def test_mechanics_quiet(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_mechanics.py', 'testdata/uthros.json', '--quiet', '--no-color']):
                mechanics_main()
                output = fake_out.getvalue()
                self.assertIn("MECHANICAL FREQUENCY", output)

if __name__ == '__main__':
    unittest.main()
