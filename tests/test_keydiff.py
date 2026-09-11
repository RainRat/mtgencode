import unittest
import io
import os
import json
import csv
import tempfile
from unittest.mock import patch
import scripts.keydiff as keydiff

class TestKeyDiff(unittest.TestCase):

    def test_parse_keyfile_basic(self):
        content = "key1: 10\nkey2: 20\nmalformed line\nkey3: 30"
        f = io.StringIO(content)
        d = {}
        keydiff.parse_keyfile(f, d, int)
        self.assertEqual(d, {"key1": 10, "key2": 20, "key3": 30})

    def test_merge_dicts(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}
        merged = keydiff.merge_dicts(d1, d2)
        self.assertEqual(merged, {
            "a": (1, None),
            "b": (2, 3),
            "c": (None, 4)
        })

    def run_main(self, args_list):
        import runpy
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['keydiff.py'] + args_list):
                try:
                    runpy.run_module('scripts.keydiff', run_name='__main__')
                    code = 0
                except SystemExit as e:
                    code = e.code if isinstance(e.code, int) else 0
                except Exception:
                    code = 1
                return code, fake_out.getvalue()

    def test_main_integration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            file2 = os.path.join(tmpdir, "f2.txt")

            with open(file1, "w") as f:
                f.write("apple: 10\nbanana: 20\n")
            with open(file2, "w") as f:
                f.write("apple: 15\ncherry: 5\n")

            code, out = self.run_main([file1, file2])
            self.assertEqual(code, 0)
            self.assertIn("shared: 1", out)
            self.assertIn("apple: 15/10 (2.25)", out)
            self.assertIn("1 only: 1", out)
            self.assertIn("banana: 20", out)
            self.assertIn("2 only: 1", out)
            self.assertIn("cherry: 5", out)

    def test_main_verbose(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            file2 = os.path.join(tmpdir, "f2.txt")

            with open(file1, "w") as f:
                f.write("a: 1\n")
            with open(file2, "w") as f:
                f.write("b: 1\n")

            code, out = self.run_main([file1, file2, "-v"])
            self.assertEqual(code, 0)
            self.assertIn("opening", out)
            self.assertIn("total 1", out)

    def test_main_zero_division_guard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            file2 = os.path.join(tmpdir, "f2.txt")

            with open(file1, "w") as f:
                f.write("a: 0\n")
            with open(file2, "w") as f:
                f.write("a: 10\n")

            # v1 is 0, so ratio should be 0.0 due to our guard
            code, out = self.run_main([file1, file2])
            self.assertEqual(code, 0)
            self.assertIn("a: 10/0 (0.0)", out)

    def test_main_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            file2 = os.path.join(tmpdir, "f2.txt")

            open(file1, "w").close()
            with open(file2, "w") as f:
                f.write("a: 10\n")

            code, out = self.run_main([file1, file2])
            self.assertEqual(code, 0)
            self.assertIn("shared: 0", out)
            self.assertIn("2 only: 1", out)

    def test_main_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            keydiff.main("nonexistent1.txt", "nonexistent2.txt", False)

    def test_main_cli_file_not_found(self):
        code, out = self.run_main(["nonexistent1.txt", "nonexistent2.txt"])
        self.assertEqual(code, 1)
        self.assertIn("Error:", out)

    def test_main_stdin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            with open(file1, "w") as f:
                f.write("apple: 10\n")

            stdin_content = io.StringIO("apple: 15\nbanana: 5\n")
            with patch('sys.stdin', stdin_content):
                code, out = self.run_main([file1, "-"])
                self.assertEqual(code, 0)
                self.assertIn("shared: 1", out)
                self.assertIn("2 only: 1", out)

    def test_main_omitted_file2_interactive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            with open(file1, "w") as f:
                f.write("apple: 10\n")

            with patch('sys.stdin.isatty', return_value=True):
                with patch('sys.stderr', new=io.StringIO()) as fake_err:
                    code, out = self.run_main([file1])
                    self.assertEqual(code, 1)
                    self.assertIn("usage: keydiff.py", fake_err.getvalue())

    def test_main_omitted_file2_non_interactive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            with open(file1, "w") as f:
                f.write("apple: 10\n")

            stdin_content = io.StringIO("apple: 20\n")
            with patch('sys.stdin', stdin_content):
                with patch('sys.stdin.isatty', return_value=False):
                    code, out = self.run_main([file1])
                    self.assertEqual(code, 0)
                    self.assertIn("shared: 1", out)

    def test_main_default_fname2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            with open(file1, "w") as f:
                f.write("apple: 10\n")

            stdin_content = io.StringIO("apple: 20\n")
            with patch('sys.stdin', stdin_content):
                with patch('sys.stdout', new=io.StringIO()) as fake_out:
                    keydiff.main(file1)
                    self.assertIn("shared: 1", fake_out.getvalue())

    def test_main_json_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            file2 = os.path.join(tmpdir, "f2.txt")

            with open(file1, "w") as f:
                f.write("apple: 10\nbanana: 20\n")
            with open(file2, "w") as f:
                f.write("apple: 15\ncherry: 5\n")

            code, out = self.run_main([file1, file2, "-j"])
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertIn("summary", data)
            self.assertEqual(data["summary"]["shared_count"], 1)
            self.assertEqual(data["summary"]["only_file1_count"], 1)
            self.assertEqual(data["summary"]["only_file2_count"], 1)
            self.assertEqual(data["shared"][0]["key"], "apple")
            self.assertEqual(data["only_file1"][0]["key"], "banana")
            self.assertEqual(data["only_file2"][0]["key"], "cherry")

    def test_main_csv_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            file2 = os.path.join(tmpdir, "f2.txt")

            with open(file1, "w") as f:
                f.write("apple: 10\nbanana: 20\n")
            with open(file2, "w") as f:
                f.write("apple: 15\ncherry: 5\n")

            code, out = self.run_main([file1, file2, "--csv"])
            self.assertEqual(code, 0)
            lines = out.strip().splitlines()
            self.assertEqual(lines[0], "Category,Key,Count1,Count2,Ratio")
            self.assertIn("Shared,apple,10,15,", out)
            self.assertIn("File1_Only,banana,20,,", out)
            self.assertIn("File2_Only,cherry,,5,", out)

    def test_main_outfile_auto_detect_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            file2 = os.path.join(tmpdir, "f2.txt")
            outfile = os.path.join(tmpdir, "out.json")

            with open(file1, "w") as f:
                f.write("apple: 10\n")
            with open(file2, "w") as f:
                f.write("apple: 20\n")

            code, out = self.run_main([file1, file2, "-o", outfile])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r') as f:
                data = json.load(f)
            self.assertEqual(data["summary"]["shared_count"], 1)

    def test_main_outfile_auto_detect_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            file2 = os.path.join(tmpdir, "f2.txt")
            outfile = os.path.join(tmpdir, "out.csv")

            with open(file1, "w") as f:
                f.write("apple: 10\n")
            with open(file2, "w") as f:
                f.write("apple: 20\n")

            code, out = self.run_main([file1, file2, "-o", outfile])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(outfile))
            with open(outfile, 'r') as f:
                content = f.read()
            self.assertIn("Category,Key,Count1,Count2,Ratio", content)

    def test_main_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "f1.txt")
            file2 = os.path.join(tmpdir, "f2.txt")

            with open(file1, "w") as f:
                f.write("apple: 10\nbanana: 20\n")
            with open(file2, "w") as f:
                f.write("apple: 15\ncherry: 5\n")

            code, out = self.run_main([file1, file2, "--dry-run"])
            self.assertEqual(code, 0)
            self.assertIn("Dry Run Summary:", out)
            self.assertIn("Base Keys", out)
            self.assertIn("Target Keys", out)
            self.assertIn("Shared: 1 key(s)", out)
            self.assertIn("Sample Shared Ratios Preview", out)

if __name__ == '__main__':
    unittest.main()
