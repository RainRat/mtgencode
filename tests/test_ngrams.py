import sys
import os
import runpy
import tempfile
import unittest
import json
import csv
from unittest.mock import patch, MagicMock

# Ensure repo root and lib/scripts are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts import ngrams

class TestNgrams(unittest.TestCase):
    def setUp(self):
        self.sample_json = os.path.join(os.path.dirname(__file__), '../testdata/uthros.json')

    def test_dry_run_mode(self):
        with patch('sys.stdout') as mock_stdout:
            ngrams.main(fname=self.sample_json, gmin=2, gmax=3, dry_run=True)
            printed_text = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
            self.assertIn("Dry Run Summary", printed_text)
            self.assertIn("Evaluated 1 card(s)", printed_text)
            self.assertIn("2-gram", printed_text)
            self.assertIn("3-gram", printed_text)

    def test_describe_bins_overflow(self):
        gramdict = {'test_ngram': 2000}
        bins = [1, 2, 10, 100]
        lines = ngrams.describe_bins(gramdict, bins)
        self.assertEqual(lines, ['  100+: 1'])

    def test_dry_run_nltk(self):
        with patch('sys.stdout') as mock_stdout:
            ngrams.main(fname=self.sample_json, gmin=3, nltk=True, dry_run=True)
            printed_text = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
            self.assertIn("Dry Run Summary", printed_text)
            self.assertIn("NLTK Model Settings: n=3", printed_text)

    def test_ngram_file_writing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_prefix = os.path.join(tmpdir, 'output')
            ngrams.main(fname=self.sample_json, oname=out_prefix, gmin=2, gmax=3, verbose=True)

            file_2g = out_prefix + '.2g'
            file_3g = out_prefix + '.3g'
            self.assertTrue(os.path.exists(file_2g))
            self.assertTrue(os.path.exists(file_3g))

            with open(file_2g, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn("this spacecraft: 2", content)

    def test_nltk_model_pickle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_pkl = os.path.join(tmpdir, 'model.pkl')
            ngrams.main(fname=self.sample_json, oname=out_pkl, gmin=2, nltk=True, verbose=True)
            self.assertTrue(os.path.exists(out_pkl))

    def test_invalid_gram_sizes(self):
        with self.assertRaises(SystemExit):
            ngrams.main(fname=self.sample_json, oname="dummy", gmin=5, gmax=2)

        with self.assertRaises(SystemExit):
            ngrams.main(fname=self.sample_json, gmin=1, gmax=3, dry_run=True)

        with self.assertRaises(SystemExit):
            ngrams.main(fname=self.sample_json, gmin=5, gmax=2, dry_run=True)

    def test_missing_outfile_raises_error(self):
        with patch('sys.stdin.isatty', return_value=False), patch('sys.stdout.isatty', return_value=False):
            with self.assertRaises(SystemExit):
                ngrams.main(fname=self.sample_json, oname=None, dry_run=False)

    def test_missing_outfile_interactive_preview(self):
        with patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stderr') as mock_stderr, \
             patch('sys.stdout') as mock_stdout:
            ngrams.main(fname=self.sample_json, oname=None, dry_run=False)
            stderr_text = "".join(call.args[0] for call in mock_stderr.write.call_args_list)
            stdout_text = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
            self.assertIn("Notice: No output file specified. Running in dry-run preview mode.", stderr_text)
            self.assertIn("Dry Run Summary", stdout_text)

    def test_single_nonexistent_arg_as_outfile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_prefix = os.path.join(tmpdir, 'custom_output')
            with patch('os.path.exists', side_effect=lambda p: p == 'data/AllPrintings.json'), \
                 patch.object(ngrams.jdecode, 'mtg_open_file', return_value=[]) as mock_open:
                ngrams.main(fname=out_prefix, oname=None, dry_run=True)
                mock_open.assert_called_once_with('data/AllPrintings.json', verbose=False)

    def test_stdin_dash_not_resolved_as_outfile(self):
        with patch('os.path.exists', side_effect=lambda p: p == 'data/AllPrintings.json'), \
             patch.object(ngrams.jdecode, 'mtg_open_file', return_value=[]) as mock_open:
            ngrams.main(fname='-', oname=None, dry_run=True)
            mock_open.assert_called_once_with('-', verbose=False)

    def test_ngram_wrapper_empty_perplexity(self):
        wrapper = ngrams.NgramModelWrapper(2, [["a", "b"]])
        self.assertEqual(wrapper.perplexity([]), 0.0)

    def test_extract_language_not_separate_lines(self):
        mock_card = MagicMock()
        mock_card.text.vectorize.return_value = "hello world"
        result = ngrams.extract_language([mock_card], separate_lines=False)
        self.assertEqual(result, [["hello", "world"]])

    def test_main_fname_default_resolution(self):
        script_dir = os.path.dirname(os.path.realpath(ngrams.__file__))
        rel_data = os.path.join(script_dir, '../data/AllPrintings.json')

        with patch('os.path.exists', return_value=True), \
             patch('sys.stdin.isatty', return_value=False), \
             patch.object(ngrams.jdecode, 'mtg_open_file', return_value=[]) as mock_open:
            ngrams.main(fname=None, gmin=2, gmax=3, dry_run=True)
            mock_open.assert_called_once_with('data/AllPrintings.json', verbose=False)

        def mock_exists_side_effect(path):
            if path == 'data/AllPrintings.json':
                return False
            if path == rel_data:
                return True
            return False

        with patch('os.path.exists', side_effect=mock_exists_side_effect), \
             patch('sys.stdin.isatty', return_value=False), \
             patch.object(ngrams.jdecode, 'mtg_open_file', return_value=[]) as mock_open:
            ngrams.main(fname=None, gmin=2, gmax=3, dry_run=True)
            mock_open.assert_called_once_with(rel_data, verbose=False)

        with patch('os.path.exists', return_value=False), \
             patch('sys.stdin.isatty', return_value=False), \
             patch.object(ngrams.jdecode, 'mtg_open_file', return_value=[]) as mock_open:
            ngrams.main(fname=None, gmin=2, gmax=3, dry_run=True)
            mock_open.assert_called_once_with('-', verbose=False)

        with patch('os.path.exists', return_value=False), \
             patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stderr'):
            with self.assertRaises(SystemExit):
                ngrams.main(fname=None, gmin=2, gmax=3, dry_run=True)

    def test_cli_execution_main(self):
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts/ngrams.py'))
        with patch('sys.argv', ['ngrams.py', self.sample_json, '-p']), \
             patch('sys.stdout'):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path(script_path, run_name='__main__')
            self.assertEqual(cm.exception.code, 0)

        with patch('sys.argv', ['ngrams.py', self.sample_json, '-p', '-nltk', '-s', '-v', '-min', '3', '-max', '5']), \
             patch('sys.stdout'):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path(script_path, run_name='__main__')
            self.assertEqual(cm.exception.code, 0)

    def test_cli_outfile_flag_support(self):
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts/ngrams.py'))
        with tempfile.TemporaryDirectory() as tmpdir:
            out_flag = os.path.join(tmpdir, 'flag_output')
            with patch('sys.argv', ['ngrams.py', self.sample_json, '-o', out_flag, '-min', '2', '-max', '2']):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path(script_path, run_name='__main__')
                self.assertEqual(cm.exception.code, 0)
            self.assertTrue(os.path.exists(out_flag + '.2g'))

    def test_cli_outfile_flag_overrides_positional(self):
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts/ngrams.py'))
        with tempfile.TemporaryDirectory() as tmpdir:
            pos_out = os.path.join(tmpdir, 'pos_out')
            flag_out = os.path.join(tmpdir, 'flag_out')
            with patch('sys.argv', ['ngrams.py', self.sample_json, pos_out, '-o', flag_out, '-min', '2', '-max', '2']):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path(script_path, run_name='__main__')
                self.assertEqual(cm.exception.code, 0)
            self.assertTrue(os.path.exists(flag_out + '.2g'))
            self.assertFalse(os.path.exists(pos_out + '.2g'))

    def test_json_export_single_and_multi_gram(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Single gram size (.json file target)
            json_target = os.path.join(tmpdir, 'output.json')
            ngrams.main(fname=self.sample_json, oname=json_target, gmin=2, gmax=2, use_json=True, verbose=True)
            self.assertTrue(os.path.exists(json_target))
            with open(json_target, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.assertIsInstance(data, list)
                self.assertTrue(any(item.get('ngram') == 'this spacecraft' for item in data))

            # Multi gram range (.json file prefix)
            json_multi = os.path.join(tmpdir, 'multi.json')
            ngrams.main(fname=self.sample_json, oname=json_multi, gmin=2, gmax=3, use_json=True)
            target_2g = os.path.join(tmpdir, 'multi.2g.json')
            target_3g = os.path.join(tmpdir, 'multi.3g.json')
            self.assertTrue(os.path.exists(target_2g))
            self.assertTrue(os.path.exists(target_3g))

    def test_csv_export_single_and_multi_gram(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Single gram size (.csv file target)
            csv_target = os.path.join(tmpdir, 'output.csv')
            ngrams.main(fname=self.sample_json, oname=csv_target, gmin=2, gmax=2, use_csv=True, verbose=True)
            self.assertTrue(os.path.exists(csv_target))
            with open(csv_target, 'r', encoding='utf-8') as f:
                reader = list(csv.reader(f))
                self.assertEqual(reader[0], ['ngram', 'count'])
                self.assertTrue(any(row[0] == 'this spacecraft' and row[1] == '2' for row in reader[1:]))

            # Multi gram range (.csv file prefix)
            csv_multi = os.path.join(tmpdir, 'multi.csv')
            ngrams.main(fname=self.sample_json, oname=csv_multi, gmin=2, gmax=3, use_csv=True)
            target_2g = os.path.join(tmpdir, 'multi.2g.csv')
            target_3g = os.path.join(tmpdir, 'multi.3g.csv')
            self.assertTrue(os.path.exists(target_2g))
            self.assertTrue(os.path.exists(target_3g))

    def test_extension_auto_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, 'auto.json')
            ngrams.main(fname=self.sample_json, oname=json_path, gmin=2, gmax=2)
            self.assertTrue(os.path.exists(json_path))
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.assertIsInstance(data, list)

            csv_path = os.path.join(tmpdir, 'auto.csv')
            ngrams.main(fname=self.sample_json, oname=csv_path, gmin=2, gmax=2)
            self.assertTrue(os.path.exists(csv_path))
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = list(csv.reader(f))
                self.assertEqual(reader[0], ['ngram', 'count'])

    def test_json_and_csv_stdout(self):
        with patch('sys.stdout') as mock_stdout:
            ngrams.main(fname=self.sample_json, oname='-', gmin=2, gmax=2, use_json=True, dry_run=False)
            output = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
            data = json.loads(output)
            self.assertIsInstance(data, list)

        with patch('sys.stdout') as mock_stdout:
            ngrams.main(fname=self.sample_json, oname='-', gmin=2, gmax=2, use_csv=True, dry_run=False)
            output = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
            self.assertIn("ngram,count", output)

    def test_invalid_gram_size_json_csv(self):
        with self.assertRaises(SystemExit):
            ngrams.main(fname=self.sample_json, oname="dummy", gmin=5, gmax=2, use_json=True)

        with self.assertRaises(SystemExit):
            ngrams.main(fname=self.sample_json, oname="dummy", gmin=5, gmax=2, use_csv=True)

    def test_cli_json_and_csv_flags(self):
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts/ngrams.py'))
        with tempfile.TemporaryDirectory() as tmpdir:
            json_out = os.path.join(tmpdir, 'cli_out.json')
            with patch('sys.argv', ['ngrams.py', self.sample_json, json_out, '-j', '-min', '2', '-max', '2']):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path(script_path, run_name='__main__')
                self.assertEqual(cm.exception.code, 0)
            self.assertTrue(os.path.exists(json_out))

            csv_out = os.path.join(tmpdir, 'cli_out.csv')
            with patch('sys.argv', ['ngrams.py', self.sample_json, csv_out, '--csv', '-min', '2', '-max', '2']):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path(script_path, run_name='__main__')
                self.assertEqual(cm.exception.code, 0)
            self.assertTrue(os.path.exists(csv_out))

if __name__ == '__main__':
    unittest.main()
