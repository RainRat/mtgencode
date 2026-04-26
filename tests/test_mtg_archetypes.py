import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_archetypes import main as archetypes_main

class TestMtgArchetypes(unittest.TestCase):

    def test_archetypes_basic(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_archetypes.py', 'testdata/tarkir.json', '--min-cards', '1', '--no-color']):
                archetypes_main()
                output = fake_out.getvalue()
                self.assertIn("ARCHETYPE PROFILING", output)
                self.assertIn("BR (Rakdos)", output)
                self.assertIn("RG (Gruul)", output)
                self.assertIn("UR (Izzet)", output)
                self.assertIn("RW (Boros)", output)
                self.assertIn("Total cards analyzed: 1", output)

    def test_archetypes_insufficient_data(self):
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.argv', ['mtg_archetypes.py', 'testdata/tarkir.json', '--no-color']):
                archetypes_main()
                output = fake_err.getvalue()
                self.assertIn("Insufficient data to profile archetypes", output)

    def test_archetypes_no_matches(self):
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.argv', ['mtg_archetypes.py', 'testdata/tarkir.json', '--rarity', 'common', '--no-color']):
                archetypes_main()
                output = fake_err.getvalue()
                self.assertIn("No cards found matching the criteria", output)

    def test_archetypes_filtering(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_archetypes.py', 'testdata/tarkir.json', '--grep', 'Invasion', '--min-cards', '1', '--no-color']):
                archetypes_main()
                self.assertIn("ARCHETYPE PROFILING", fake_out.getvalue())

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_archetypes.py', 'testdata/tarkir.json', '--limit', '1', '--min-cards', '1', '--no-color']):
                archetypes_main()
                self.assertIn("Total cards analyzed: 1", fake_out.getvalue())

    def test_archetypes_top_mechanics(self):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_archetypes.py', 'testdata/tarkir.json', '--min-cards', '1', '--top-mechanics', '1', '--no-color']):
                archetypes_main()
                output = fake_out.getvalue()
                self.assertTrue("X-Cost/Effect" in output or "Triggered" in output or "ETB Effect" in output)
                self.assertNotIn(",", output)

    def test_archetypes_color_mock(self):
        mock_stdout = MagicMock(spec=io.TextIOBase)
        mock_stdout.isatty.return_value = True
        mock_stdout.write = MagicMock()

        captured_output = io.StringIO()
        mock_stdout.write.side_effect = captured_output.write

        with patch('sys.stdout', mock_stdout):
            with patch('sys.argv', ['mtg_archetypes.py', 'testdata/tarkir.json', '--min-cards', '1', '--color']):
                archetypes_main()
                output = captured_output.getvalue()
                self.assertIn("\033[", output)

    def test_archetypes_verbose(self):
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.argv', ['mtg_archetypes.py', 'testdata/tarkir.json', '--verbose', '--min-cards', '1', '--no-color']):
                archetypes_main()
                self.assertIn("looks like a json file", fake_err.getvalue())

    def test_archetypes_quiet(self):
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.argv', ['mtg_archetypes.py', 'testdata/tarkir.json', '--rarity', 'common', '--quiet']):
                archetypes_main()
                self.assertEqual("", fake_err.getvalue().strip())

if __name__ == '__main__':
    unittest.main()
