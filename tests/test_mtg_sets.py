import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os
import json
import tempfile

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_sets import main as sets_main

class TestMtgSets(unittest.TestCase):

    def test_sets_basic(self):
        """Test basic listing of sets."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_sets.py', 'testdata/tarkir.json', '--no-color']):
                sets_main()
                output = fake_out.getvalue()
                self.assertIn("AVAILABLE SETS", output)
                self.assertIn("CUS", output)
                self.assertIn("custom", output)

    def test_sets_grep(self):
        """Test filtering sets by name/code."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_sets.py', 'testdata/tarkir.json', '--grep', 'CUS', '--no-color']):
                sets_main()
                output = fake_out.getvalue()
                self.assertIn("CUS", output)

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_sets.py', 'testdata/tarkir.json', '--grep', 'NONEXISTENT', '--no-color']):
                sets_main()
                output = fake_out.getvalue()
                self.assertNotIn("CUS", output)

    def test_sets_summarize(self):
        """Test the --summarize flag for profiling cards in sets."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_sets.py', 'testdata/tarkir.json', '--summarize', '--no-color']):
                sets_main()
                output = fake_out.getvalue()
                self.assertIn("SET SUMMARY", output)
                self.assertIn("DATASET SUMMARY", output)
                self.assertIn("1 unique card names", output)

    def test_sets_view(self):
        """Test the --view flag for listing cards in sets."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_sets.py', 'testdata/tarkir.json', '--view', '--no-color']):
                sets_main()
                output = fake_out.getvalue()
                self.assertIn("CARD LIST", output)
                self.assertIn("Invasion of Tarkir", output)

    def test_sets_sorting_limiting(self):
        """Test sorting and limiting flags."""
        # Limit 1
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_sets.py', 'testdata/tarkir.json', '--limit', '1', '--no-color']):
                sets_main()
                output = fake_out.getvalue()
                self.assertIn("AVAILABLE SETS (1 match)", output)

        # Shuffle and sample
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_sets.py', 'testdata/tarkir.json', '--sample', '1', '--no-color']):
                sets_main()
                output = fake_out.getvalue()
                self.assertIn("AVAILABLE SETS (1 match)", output)

        # Sorting
        for sort_key in ['code', 'name', 'type', 'count']:
             with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_sets.py', 'testdata/tarkir.json', '--sort', sort_key, '--reverse', '--no-color']):
                    sets_main()
                    output = fake_out.getvalue()
                    self.assertIn("AVAILABLE SETS", output)

    def test_sets_outfile(self):
        """Test writing output to a file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
            tf_path = tf.name

        try:
            with patch('sys.stdout', new=io.StringIO()):
                with patch('sys.argv', ['mtg_sets.py', 'testdata/tarkir.json', tf_path, '--no-color']):
                    sets_main()

            with open(tf_path, 'r') as f:
                content = f.read()
                self.assertIn("AVAILABLE SETS", content)
                self.assertIn("CUS", content)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_sets_error_handling(self):
        """Test behavior with invalid files."""
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.argv', ['mtg_sets.py', 'nonexistent.json']):
                with self.assertRaises(SystemExit):
                    sets_main()
                self.assertIn("Error loading", fake_err.getvalue())

    def test_sets_fallback_format(self):
        """Test handling of JSON files that are a dictionary of sets already (no 'data' key)."""
        fallback_data = {
            "TEST": {
                "code": "TEST",
                "name": "Test Set",
                "type": "expansion",
                "releaseDate": "2023-01-01",
                "cards": [{"name": "Test Card"}]
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
            json.dump(fallback_data, tf)
            tf_path = tf.name

        try:
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.argv', ['mtg_sets.py', tf_path, '--no-color']):
                    sets_main()
                    output = fake_out.getvalue()
                    self.assertIn("Test Set", output)
                    self.assertIn("TEST", output)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_sets_color_mock(self):
        """Test color output logic by mocking isatty."""
        mock_stdout = MagicMock(spec=io.TextIOBase)
        mock_stdout.isatty.return_value = True
        mock_stdout.write = MagicMock()

        captured_output = io.StringIO()
        mock_stdout.write.side_effect = captured_output.write

        with patch('sys.stdout', mock_stdout):
            with patch('sys.argv', ['mtg_sets.py', 'testdata/tarkir.json', '--color']):
                sets_main()
                output = captured_output.getvalue()
                self.assertIn("\033[", output)

if __name__ == '__main__':
    unittest.main()
