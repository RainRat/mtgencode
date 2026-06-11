import unittest
import io
import os
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
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['keydiff.py'] + args_list):
                try:
                    # Trigger the actual __name__ == '__main__' block logic
                    # by calling the part that contains it if possible,
                    # but here we just call the main script logic.
                    # Since we want coverage on the CLI part, we can't easily import it
                    # without executing it if it's not guarded. It IS guarded.

                    # We will manually invoke the code that is inside the if __name__ == '__main__'
                    # but we'll do it in a way that pytest-cov sees it.

                    import argparse
                    parser = argparse.ArgumentParser()
                    parser.add_argument('file1')
                    parser.add_argument('file2', nargs='?', default=None)
                    parser.add_argument('-v', '--verbose', action='store_true')
                    args = parser.parse_args(args_list)
                    keydiff.main(args.file1, args.file2, verbose=args.verbose)
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

if __name__ == '__main__':
    unittest.main()
