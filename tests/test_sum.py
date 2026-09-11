import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os
import tempfile
import runpy

# Add project root to sys.path
sys.path.append(os.getcwd())

from scripts.sum import calculate_stats, main as sum_main

class TestSumStats(unittest.TestCase):
    def test_calculate_stats_empty(self):
        nonempty, name_avg, name_dupes, card_avg, card_dupes = calculate_stats([])
        self.assertEqual(nonempty, 0)
        self.assertEqual(name_avg, 0.0)

    def test_calculate_stats_valid(self):
        data = [
            ['0', 'Card A', '1.0', '1.0'],
            ['1', 'Card B', '0.5', '0.8'],
            ['2', 'Card C', '0.6', '0.6']
        ]
        nonempty, name_avg, name_dupes, card_avg, card_dupes = calculate_stats(data)
        self.assertEqual(nonempty, 3)
        self.assertAlmostEqual(name_avg, (1.0 + 0.5 + 0.6) / 3)
        self.assertEqual(name_dupes, 1)
        self.assertAlmostEqual(card_avg, (1.0 + 0.8 + 0.6) / 3)
        self.assertEqual(card_dupes, 1)

    def test_calculate_stats_malformed_value(self):
        data = [
            ['0', 'Card A', 'not-a-float', '1.0'],
        ]
        nonempty, name_avg, name_dupes, card_avg, card_dupes = calculate_stats(data)
        self.assertEqual(nonempty, 0)
        self.assertEqual(name_avg, 0.0)

    def test_calculate_stats_index_error(self):
        # Even though CLI filters, this tests the robustness of the function
        data = [
            ['0', 'Card A', '1.0'] # Missing 4th element
        ]
        nonempty, name_avg, name_dupes, card_avg, card_dupes = calculate_stats(data)
        self.assertEqual(nonempty, 0)
        self.assertEqual(name_avg, 0.0)

class TestSumCLI(unittest.TestCase):
    def run_sum_main(self, args, stdout_isatty=False):
        with patch('sys.argv', ['sum.py'] + args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.stderr', new=io.StringIO()) as fake_err:
                    with patch('sys.stdout.isatty', return_value=stdout_isatty):
                        try:
                            sum_main()
                            code = 0
                        except SystemExit as e:
                            code = e.code if isinstance(e.code, int) else 0
                        return code, fake_out.getvalue(), fake_err.getvalue()

    def test_cli_missing_file(self):
        code, out, err = self.run_sum_main(['nonexistent.txt'])
        self.assertEqual(code, 1)
        self.assertIn("Error: File not found", err)

    def test_cli_valid_file(self):
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as tmp:
            tmp.write("0|Card A|1.0|0.8\n")
            tmp.write("1|Card B|0.5|0.4\n")
            tmp_path = tmp.name

        try:
            code, out, err = self.run_sum_main([tmp_path])
            self.assertEqual(code, 0)
            self.assertIn("DISTANCE SUMMARY", out)
            self.assertIn("Names", out)
            self.assertIn("Cards", out)
            # 0.75 is (1.0 + 0.5) / 2
            self.assertIn("0.7500", out)
            # 0.6 is (0.8 + 0.4) / 2
            self.assertIn("0.6000", out)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_cli_empty_file(self):
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as tmp:
            tmp_path = tmp.name

        try:
            code, out, err = self.run_sum_main([tmp_path])
            self.assertEqual(code, 0)
            self.assertIn("No valid distance data found", err)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_cli_color_force(self):
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as tmp:
            tmp.write("0|Card A|1.0|0.8\n")
            tmp_path = tmp.name

        try:
            # Test --color
            code, out, err = self.run_sum_main([tmp_path, '--color'], stdout_isatty=False)
            self.assertEqual(code, 0)
            self.assertIn("\033[", out) # ANSI escape code

            # Test --no-color
            code, out, err = self.run_sum_main([tmp_path, '--no-color'], stdout_isatty=True)
            self.assertEqual(code, 0)
            self.assertNotIn("\033[", out)

            # Test auto-color (isatty=True)
            code, out, err = self.run_sum_main([tmp_path], stdout_isatty=True)
            self.assertEqual(code, 0)
            self.assertIn("\033[", out)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_cli_invalid_content(self):
         with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as tmp:
            tmp.write("invalid line\n")
            tmp_path = tmp.name
         try:
            code, out, err = self.run_sum_main([tmp_path])
            self.assertEqual(code, 0)
            self.assertIn("No valid distance data found", err)
         finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_cli_read_error(self):
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            with patch('os.path.exists', return_value=True):
                code, out, err = self.run_sum_main(['somefile.txt'])
                self.assertEqual(code, 1)
                self.assertIn("Error reading somefile.txt", err)

    def test_cli_default_distances_txt_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dist_path = os.path.join(tmpdir, 'distances.txt')
            with open(dist_path, 'w', encoding='utf-8') as f:
                f.write("0|Card A|1.0|0.8\n")

            cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                with patch('sys.stdin.isatty', return_value=True):
                    code, out, err = self.run_sum_main([], stdout_isatty=True)
                    self.assertEqual(code, 0)
                    self.assertIn("DISTANCE SUMMARY", out)
            finally:
                os.chdir(cwd)

    def test_cli_default_no_distances_txt_interactive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                with patch('sys.stdin.isatty', return_value=True):
                    code, out, err = self.run_sum_main([])
                    self.assertEqual(code, 1)
                    self.assertIn("usage: sum.py", err)
            finally:
                os.chdir(cwd)

    def test_cli_stdin_pipe(self):
        stdin_data = "0|Card A|1.0|0.8\n1|Card B|0.6|0.4\n"
        with patch('sys.stdin', io.StringIO(stdin_data)):
            with patch('sys.stdin.isatty', return_value=False):
                code, out, err = self.run_sum_main([])
                self.assertEqual(code, 0)
                self.assertIn("DISTANCE SUMMARY", out)
                self.assertIn("0.8000", out)

    def test_main_cli_execution(self):
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as tmp:
            tmp.write("0|Card A|1.0|0.8\n")
            tmp_path = tmp.name

        try:
            with patch('sys.argv', ['sum.py', tmp_path]):
                with patch('sys.stdout', new=io.StringIO()) as fake_out:
                    with patch('sys.stderr', new=io.StringIO()):
                        runpy.run_path('scripts/sum.py', run_name='__main__')
                        self.assertIn("DISTANCE SUMMARY", fake_out.getvalue())
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
