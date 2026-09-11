import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure repo root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts import autosample


class TestAutoSample(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_extract_cp_name_valid(self):
        res = autosample.extract_cp_name("lm_lstm_epoch50.00_0.1870.t7")
        self.assertEqual(res, (50.0, 0.1870))

    def test_extract_cp_name_invalid_prefix(self):
        res = autosample.extract_cp_name("invalid_prefix_50.00_0.1870.t7")
        self.assertIsNone(res)

    def test_extract_cp_name_invalid_extension(self):
        res = autosample.extract_cp_name("lm_lstm_epoch50.00_0.1870.pt")
        self.assertIsNone(res)

    def test_sample_existing_outfile(self):
        cp_path = os.path.join(self.tmpdir.name, "lm_lstm_epoch1.00_0.5000.t7")
        outfile = cp_path + ".output.1.0.txt"
        with open(outfile, "w", encoding="utf-8") as f:
            f.write("already existing")

        with patch("builtins.print") as mock_print:
            res = autosample.sample(cp_path, 1.0, 100, seed=123, ident="output")
            self.assertFalse(res)
            mock_print.assert_called_with(f"{outfile} already exists, skipping")

    @patch("subprocess.run")
    def test_sample_new_file_explicit_seed(self, mock_run):
        cp_path = os.path.join(self.tmpdir.name, "lm_lstm_epoch1.00_0.5000.t7")
        outfile = cp_path + ".output.1.0.txt"

        autosample.sample(cp_path, 1.0, 100, seed=42, ident="output")

        self.assertTrue(os.path.exists(outfile))
        with open(outfile, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("th sample.lua", content)
        self.assertIn("-seed 42", content)
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_sample_new_file_default_seed(self, mock_run):
        cp_path = os.path.join(self.tmpdir.name, "lm_lstm_epoch1.00_0.5000.t7")
        autosample.sample(cp_path, 0.8, 50, seed=None, ident="custom")

        outfile = cp_path + ".custom.0.8.txt"
        self.assertTrue(os.path.exists(outfile))

    def test_find_best_cp(self):
        cpdir = os.path.join(self.tmpdir.name, "checkpoints")
        os.makedirs(cpdir)

        cp1 = "lm_lstm_epoch10.00_0.5000.t7"
        cp2 = "lm_lstm_epoch20.00_0.2000.t7"
        cp3 = "lm_lstm_epoch30.00_0.3500.t7"
        non_cp = "notes.txt"

        for f in [cp1, cp2, cp3, non_cp]:
            with open(os.path.join(cpdir, f), "w") as fp:
                fp.write("dummy")

        best = autosample.find_best_cp(cpdir)
        self.assertEqual(best, os.path.join(cpdir, cp2))

    def test_find_best_cp_empty(self):
        cpdir = os.path.join(self.tmpdir.name, "empty_checkpoints")
        os.makedirs(cpdir)
        best = autosample.find_best_cp(cpdir)
        self.assertIsNone(best)

    @patch("scripts.autosample.sample")
    def test_process_dir(self, mock_sample):
        cpdir = os.path.join(self.tmpdir.name, "checkpoints")
        subdir = os.path.join(cpdir, "sub")
        os.makedirs(subdir)

        cp_name = "lm_lstm_epoch10.00_0.3000.t7"
        with open(os.path.join(cpdir, cp_name), "w") as f:
            f.write("dummy")

        with patch("builtins.print") as mock_print:
            autosample.process_dir(cpdir, 1.0, 1000, seed=7, ident="test", verbose=True)
            printed = [call.args[0] for call in mock_print.call_args_list if call.args]
            self.assertTrue(any("processing " in p for p in printed))

        self.assertEqual(mock_sample.call_count, 1)

    def test_main_invalid_rnndir(self):
        cpdir = self.tmpdir.name
        with self.assertRaises(ValueError) as cm:
            autosample.main("/nonexistent/rnndir", cpdir, 1.0, 100)
        self.assertIn("bad rnndir", str(cm.exception))

    def test_main_invalid_cpdir(self):
        rnndir = self.tmpdir.name
        with self.assertRaises(ValueError) as cm:
            autosample.main(rnndir, "/nonexistent/cpdir", 1.0, 100)
        self.assertIn("bad cpdir", str(cm.exception))

    @patch("scripts.autosample.process_dir")
    def test_main_success(self, mock_process_dir):
        rnndir = os.path.join(self.tmpdir.name, "rnn")
        cpdir = os.path.join(self.tmpdir.name, "cp")
        os.makedirs(rnndir)
        os.makedirs(cpdir)

        orig_cwd = os.getcwd()
        try:
            autosample.main(rnndir, cpdir, 0.9, 500, seed=123, ident="out", verbose=True)
            self.assertEqual(os.getcwd(), os.path.realpath(rnndir))
            mock_process_dir.assert_called_once_with(cpdir, 0.9, 500, seed=123, ident="out", verbose=True)
        finally:
            os.chdir(orig_cwd)

    @patch("subprocess.run")
    def test_cli_execution_default_seed(self, mock_run):
        rnndir = os.path.join(self.tmpdir.name, "rnn")
        cpdir = os.path.join(self.tmpdir.name, "cp")
        os.makedirs(rnndir)
        os.makedirs(cpdir)

        cp_file = os.path.join(cpdir, "lm_lstm_epoch10.00_0.2500.t7")
        with open(cp_file, "w") as f:
            f.write("cp content")

        orig_cwd = os.getcwd()
        test_args = ["autosample.py", rnndir, cpdir, "-t", "0.7", "-c", "200", "-i", "run1", "-v"]
        try:
            with patch("sys.argv", test_args):
                with self.assertRaises(SystemExit) as cm:
                    import importlib
                    import scripts.autosample
                    # Reset sys.modules['__main__'] simulation via exec
                    with open("scripts/autosample.py") as f:
                        code = compile(f.read(), "scripts/autosample.py", "exec")
                        exec(code, {"__name__": "__main__"})
                self.assertEqual(cm.exception.code, 0)
        finally:
            os.chdir(orig_cwd)

        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_cli_execution_explicit_seed(self, mock_run):
        rnndir = os.path.join(self.tmpdir.name, "rnn")
        cpdir = os.path.join(self.tmpdir.name, "cp")
        os.makedirs(rnndir)
        os.makedirs(cpdir)

        cp_file = os.path.join(cpdir, "lm_lstm_epoch10.00_0.2500.t7")
        with open(cp_file, "w") as f:
            f.write("cp content")

        orig_cwd = os.getcwd()
        test_args = ["autosample.py", rnndir, cpdir, "-s", "999"]
        try:
            with patch("sys.argv", test_args):
                with self.assertRaises(SystemExit) as cm:
                    with open("scripts/autosample.py") as f:
                        code = compile(f.read(), "scripts/autosample.py", "exec")
                        exec(code, {"__name__": "__main__"})
                self.assertEqual(cm.exception.code, 0)
        finally:
            os.chdir(orig_cwd)

        mock_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
