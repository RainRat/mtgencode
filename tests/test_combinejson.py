import json
import os
import runpy
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch
from scripts.combinejson import merge_dicts, main, _summarize_dataset

class TestCombineJson(unittest.TestCase):

    def test_merge_dicts_simple(self):
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        expected = {"a": 1, "b": 3, "c": 4}
        self.assertEqual(merge_dicts(dict1, dict2), expected)

    def test_merge_dicts_recursive(self):
        dict1 = {"set": {"code": "MOM", "cards": [1, 2]}}
        dict2 = {"set": {"cards": [3]}}
        expected = {"set": {"code": "MOM", "cards": [3]}}
        self.assertEqual(merge_dicts(dict1, dict2), expected)

    def test_merge_dicts_deep_recursive(self):
        dict1 = {"data": {"SET": {"name": "Old Name", "code": "SET"}}}
        dict2 = {"data": {"SET": {"name": "New Name"}}}
        expected = {"data": {"SET": {"name": "New Name", "code": "SET"}}}
        self.assertEqual(merge_dicts(dict1, dict2), expected)

    def test_main_cli(self):
        base_data = {"data": {"MOM": {"name": "March of the Machine"}}}
        custom_data = {"data": {"CUS": {"name": "Custom Set"}}}

        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = os.path.join(tmpdir, "base.json")
            custom_file = os.path.join(tmpdir, "custom.json")
            output_file = os.path.join(tmpdir, "output.json")

            with open(base_file, "w", encoding="utf-8") as f:
                json.dump(base_data, f)
            with open(custom_file, "w", encoding="utf-8") as f:
                json.dump(custom_data, f)

            with patch("sys.argv", ["combinejson.py", base_file, custom_file, output_file]):
                main()

            with open(output_file, "r", encoding="utf-8") as f:
                result = json.load(f)

            self.assertIn("MOM", result["data"])
            self.assertIn("CUS", result["data"])

    def test_encoding_bug_preservation(self):
        base_data = {"test": "base"}
        custom_data = {"card": "Special é"}

        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = os.path.join(tmpdir, "base.json")
            custom_file = os.path.join(tmpdir, "custom.json")
            output_file = os.path.join(tmpdir, "output.json")

            with open(base_file, "w", encoding="utf-8") as f:
                json.dump(base_data, f)
            with open(custom_file, "w", encoding="utf-8") as f:
                json.dump(custom_data, f)

            with patch("sys.argv", ["combinejson.py", base_file, custom_file, output_file]):
                main()

            with open(output_file, "r", encoding="utf-8") as f:
                result = json.load(f)

            self.assertEqual(result["card"], "Special é")

    def test_dry_run_flag(self):
        base_data = {"data": {"MOM": {"code": "MOM", "cards": [{"name": "Grizzly Bears"}]}}}
        custom_data = {"data": {"CUS": {"code": "CUS", "cards": [{"name": "Custom Bear"}]}}}

        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = os.path.join(tmpdir, "base.json")
            custom_file = os.path.join(tmpdir, "custom.json")
            output_file = os.path.join(tmpdir, "output.json")

            with open(base_file, "w", encoding="utf-8") as f:
                json.dump(base_data, f)
            with open(custom_file, "w", encoding="utf-8") as f:
                json.dump(custom_data, f)

            with patch("sys.argv", ["combinejson.py", base_file, custom_file, "--dry-run"]):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    main()
                    output = mock_stdout.getvalue()

            self.assertIn("Dry Run Summary: 2 card(s) in merged dataset.", output)
            self.assertIn("CUS: 1 card(s)", output)
            self.assertIn("MOM: 1 card(s)", output)
            self.assertIn("Sample Preview", output)
            self.assertFalse(os.path.exists(output_file))

    def test_missing_output_file_without_dry_run_raises_system_exit(self):
        with patch("sys.argv", ["combinejson.py", "base.json", "custom.json"]):
            with self.assertRaises(SystemExit):
                main()

    def test_file_not_found(self):
        with patch("sys.argv", ["combinejson.py", "nonexistent.json", "custom.json", "output.json"]):
            with patch("builtins.print") as mock_print:
                main()
                mock_print.assert_called()
                args, _ = mock_print.call_args
                self.assertTrue(any("Error" in arg for arg in args if isinstance(arg, str)))

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = os.path.join(tmpdir, "base.json")
            custom_file = os.path.join(tmpdir, "custom.json")
            output_file = os.path.join(tmpdir, "output.json")

            with open(base_file, "w", encoding="utf-8") as f:
                f.write("invalid json")
            with open(custom_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

            with patch("sys.argv", ["combinejson.py", base_file, custom_file, output_file]):
                with patch("builtins.print") as mock_print:
                    main()
                    mock_print.assert_called()
                    args, _ = mock_print.call_args
                    self.assertTrue(any("Invalid JSON" in arg for arg in args if isinstance(arg, str)))

    def test_summarize_dataset_data_key_with_list(self):
        data = {"data": {"SET": [{"name": "Card A"}, {"name": "Card B"}]}}
        total, breakdown, samples = _summarize_dataset(data)
        self.assertEqual(total, 2)
        self.assertEqual(breakdown["SET"], 2)
        self.assertEqual(samples, ["Card A", "Card B"])

    def test_summarize_dataset_direct_set_keys(self):
        data = {"SET1": {"cards": [{"name": "Card A"}]}, "SET2": {"cards": [{"name": "Card B"}]}}
        total, breakdown, samples = _summarize_dataset(data)
        self.assertEqual(total, 2)
        self.assertEqual(breakdown["SET1"], 1)
        self.assertEqual(breakdown["SET2"], 1)
        self.assertEqual(samples, ["Card A", "Card B"])

    def test_summarize_dataset_top_level_cards_list(self):
        data = {"code": "TST", "cards": [{"name": "Card A"}, {"name": "Card B"}]}
        total, breakdown, samples = _summarize_dataset(data)
        self.assertEqual(total, 2)
        self.assertEqual(breakdown["TST"], 2)
        self.assertEqual(samples, ["Card A", "Card B"])

    def test_summarize_dataset_generic_dict(self):
        data = {"key1": "val1", "key2": "val2"}
        total, breakdown, samples = _summarize_dataset(data)
        self.assertEqual(total, 2)
        self.assertEqual(len(breakdown), 0)
        self.assertEqual(samples, ["key1", "key2"])

    def test_summarize_dataset_top_level_list(self):
        data = [{"name": "Card A"}, "NonDictCard"]
        total, breakdown, samples = _summarize_dataset(data)
        self.assertEqual(total, 2)
        self.assertEqual(breakdown["UNKNOWN"], 2)
        self.assertEqual(samples, ["Card A", "NonDictCard"])

    def test_main_execution(self):
        base_data = {"key": "base"}
        custom_data = {"key": "custom"}

        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = os.path.join(tmpdir, "base.json")
            custom_file = os.path.join(tmpdir, "custom.json")
            output_file = os.path.join(tmpdir, "output.json")

            with open(base_file, "w", encoding="utf-8") as f:
                json.dump(base_data, f)
            with open(custom_file, "w", encoding="utf-8") as f:
                json.dump(custom_data, f)

            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts/combinejson.py"))
            test_args = ["combinejson.py", base_file, custom_file, output_file]
            with patch("sys.argv", test_args):
                runpy.run_path(script_path, run_name="__main__")

            with open(output_file, "r", encoding="utf-8") as f:
                result = json.load(f)

            self.assertEqual(result["key"], "custom")

if __name__ == "__main__":
    unittest.main()
