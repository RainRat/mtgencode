import io
import os
import sys
import tempfile
import unittest
import runpy
from unittest.mock import patch, MagicMock

import scripts.distances as distances

class TestDistances(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_main_file_not_found(self):
        non_existent = os.path.join(self.temp_dir.name, 'non_existent.json')
        with self.assertRaises(SystemExit) as cm:
            distances.main(non_existent, 'out.txt')
        self.assertEqual(cm.exception.code, 1)

    def test_main_dry_run(self):
        infile = os.path.join('testdata', 'tarkir.json')
        outfile = os.path.join(self.temp_dir.name, 'out.txt')

        with patch('sys.stdout') as mock_stdout:
            distances.main(infile, outfile, verbose=False, parallel=False, dry_run=True)

        self.assertFalse(os.path.exists(outfile))

    def test_cli_dry_run(self):
        infile = os.path.join('testdata', 'tarkir.json')
        outfile = os.path.join(self.temp_dir.name, 'out.txt')
        test_args = ['distances.py', infile, outfile, '--dry-run', '--parallel']

        with patch.object(sys, 'argv', test_args):
            with patch('sys.stdout') as mock_stdout:
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_module('scripts.distances', run_name='__main__')
                self.assertEqual(cm.exception.code, 0)
        self.assertFalse(os.path.exists(outfile))

    def test_cli_interactive_missing_default_infile(self):
        test_args = ['distances.py']

        real_exists = os.path.exists
        def fake_exists(path):
            if path == distances.default_infile or 'output.txt' in str(path):
                return False
            return real_exists(path)

        with patch.object(sys, 'argv', test_args):
            with patch('sys.stdin.isatty', return_value=True):
                with patch('os.path.exists', side_effect=fake_exists):
                    with patch('sys.stdout'):
                        with self.assertRaises(SystemExit) as cm:
                            runpy.run_module('scripts.distances', run_name='__main__')
                        self.assertEqual(cm.exception.code, 1)

    def test_main_stdin_dry_run(self):
        outfile = os.path.join(self.temp_dir.name, 'out.txt')
        sample_card = "Grizzly Bears|{1}{G}|Creature — Bear|2/2||\n"
        with patch('sys.stdin', io.StringIO(sample_card)), patch('sys.stdout'):
            distances.main('-', outfile, verbose=False, parallel=False, dry_run=True)
        self.assertFalse(os.path.exists(outfile))

    @patch('scripts.distances.CBOW')
    @patch('scripts.distances.Namediff')
    def test_main_sequential(self, mock_namediff_cls, mock_cbow_cls):
        infile = os.path.join('testdata', 'tarkir.json')
        outfile = os.path.join(self.temp_dir.name, 'out.txt')

        mock_nd = MagicMock()
        mock_nd.nearest.return_value = [(0.125, 'Sample Target')]
        mock_namediff_cls.return_value = mock_nd

        mock_cb = MagicMock()
        mock_cb.nearest.return_value = [(0.250, 'Sample Target Card')]
        mock_cbow_cls.return_value = mock_cb

        distances.main(infile, outfile, verbose=True, parallel=False, dry_run=False)

        self.assertTrue(os.path.exists(outfile))
        with open(outfile, 'r', encoding='utf8') as f:
            lines = f.readlines()
        self.assertGreater(len(lines), 0)
        first_fields = lines[0].strip().split('|')
        self.assertEqual(first_fields[0], '0')
        self.assertEqual(first_fields[2], '0.125')
        self.assertEqual(first_fields[3], '0.25')

    @patch('scripts.distances.CBOW')
    @patch('scripts.distances.Namediff')
    def test_main_parallel(self, mock_namediff_cls, mock_cbow_cls):
        infile = os.path.join('testdata', 'tarkir.json')
        outfile = os.path.join(self.temp_dir.name, 'out.txt')

        mock_nd = MagicMock()
        mock_nd.nearest_par.side_effect = lambda names, n=1: [[(0.125, 'Target')] for _ in names]
        mock_namediff_cls.return_value = mock_nd

        mock_cb = MagicMock()
        mock_cb.nearest_par.side_effect = lambda cards, n=1: [[(0.250, 'Target')] for _ in cards]
        mock_cbow_cls.return_value = mock_cb

        distances.main(infile, outfile, verbose=True, parallel=True, dry_run=False)

        self.assertTrue(os.path.exists(outfile))
        with open(outfile, 'r', encoding='utf8') as f:
            lines = f.readlines()
        self.assertGreater(len(lines), 0)
        first_fields = lines[0].strip().split('|')
        self.assertEqual(first_fields[0], '0')
        self.assertEqual(first_fields[2], '0.125')
        self.assertEqual(first_fields[3], '0.25')

    @patch('cbow.CBOW')
    @patch('namediff.Namediff')
    def test_cli_main_execution(self, mock_namediff_cls, mock_cbow_cls):
        infile = os.path.join('testdata', 'tarkir.json')
        outfile = os.path.join(self.temp_dir.name, 'out.txt')
        test_args = ['distances.py', infile, outfile, '-v', '-p']

        mock_nd = MagicMock()
        mock_nd.nearest_par.side_effect = lambda names, n=1: [[(0.1, 'Target')] for _ in names]
        mock_namediff_cls.return_value = mock_nd

        mock_cb = MagicMock()
        mock_cb.nearest_par.side_effect = lambda cards, n=1: [[(0.2, 'Target')] for _ in cards]
        mock_cbow_cls.return_value = mock_cb

        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_module('scripts.distances', run_name='__main__')
            self.assertEqual(cm.exception.code, 0)
        self.assertTrue(os.path.exists(outfile))

    @patch('scripts.distances.CBOW')
    @patch('scripts.distances.Namediff')
    def test_main_json_export_and_autodetect(self, mock_namediff_cls, mock_cbow_cls):
        import json
        infile = os.path.join('testdata', 'tarkir.json')
        outfile_explicit = os.path.join(self.temp_dir.name, 'out.txt')
        outfile_autodetect = os.path.join(self.temp_dir.name, 'out.json')

        mock_nd = MagicMock()
        mock_nd.nearest_par.side_effect = lambda names, n=1: [[(0.85, 'Target Name')] for _ in names]
        mock_namediff_cls.return_value = mock_nd

        mock_cb = MagicMock()
        mock_cb.nearest_par.side_effect = lambda cards, n=1: [[(0.92, 'Target Card')] for _ in cards]
        mock_cbow_cls.return_value = mock_cb

        # Test explicit --json
        distances.main(infile, outfile_explicit, verbose=False, parallel=True, use_json=True)
        self.assertTrue(os.path.exists(outfile_explicit))
        with open(outfile_explicit, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertIn('index', data[0])
        self.assertIn('name', data[0])
        self.assertEqual(data[0]['nearest_name_similarity'], 0.85)
        self.assertEqual(data[0]['nearest_card_similarity'], 0.92)

        # Test auto-detection via .json extension
        distances.main(infile, outfile_autodetect, verbose=False, parallel=True)
        self.assertTrue(os.path.exists(outfile_autodetect))
        with open(outfile_autodetect, 'r', encoding='utf-8') as f:
            data_auto = json.load(f)
        self.assertEqual(data, data_auto)

    @patch('scripts.distances.CBOW')
    @patch('scripts.distances.Namediff')
    def test_main_csv_export_and_autodetect(self, mock_namediff_cls, mock_cbow_cls):
        import csv
        infile = os.path.join('testdata', 'tarkir.json')
        outfile_explicit = os.path.join(self.temp_dir.name, 'out.txt')
        outfile_autodetect = os.path.join(self.temp_dir.name, 'out.csv')

        mock_nd = MagicMock()
        mock_nd.nearest_par.side_effect = lambda names, n=1: [[(0.75, 'Target Name')] for _ in names]
        mock_namediff_cls.return_value = mock_nd

        mock_cb = MagicMock()
        mock_cb.nearest_par.side_effect = lambda cards, n=1: [[(0.88, 'Target Card')] for _ in cards]
        mock_cbow_cls.return_value = mock_cb

        # Test explicit --csv
        distances.main(infile, outfile_explicit, verbose=False, parallel=True, use_csv=True)
        self.assertTrue(os.path.exists(outfile_explicit))
        with open(outfile_explicit, 'r', encoding='utf-8') as f:
            reader = list(csv.reader(f))
        self.assertGreater(len(reader), 1)
        self.assertEqual(reader[0], ['index', 'name', 'nearest_name_similarity', 'nearest_card_similarity'])
        self.assertEqual(reader[1][0], '0')
        self.assertEqual(reader[1][2], '0.75')
        self.assertEqual(reader[1][3], '0.88')

        # Test auto-detection via .csv extension
        distances.main(infile, outfile_autodetect, verbose=False, parallel=True)
        self.assertTrue(os.path.exists(outfile_autodetect))
        with open(outfile_autodetect, 'r', encoding='utf-8') as f:
            reader_auto = list(csv.reader(f))
        self.assertEqual(reader, reader_auto)

    @patch('scripts.distances.CBOW')
    @patch('scripts.distances.Namediff')
    def test_main_stdout_export(self, mock_namediff_cls, mock_cbow_cls):
        import json
        infile = os.path.join('testdata', 'tarkir.json')

        mock_nd = MagicMock()
        mock_nd.nearest_par.side_effect = lambda names, n=1: [[(0.5, 'Target Name')] for _ in names]
        mock_namediff_cls.return_value = mock_nd

        mock_cb = MagicMock()
        mock_cb.nearest_par.side_effect = lambda cards, n=1: [[(0.6, 'Target Card')] for _ in cards]
        mock_cbow_cls.return_value = mock_cb

        buf = io.StringIO()
        with patch('sys.stdout', buf):
            distances.main(infile, None, verbose=False, parallel=True, use_json=True)
        output_str = buf.getvalue()
        data = json.loads(output_str)
        self.assertIsInstance(data, list)

    @patch('cbow.CBOW')
    @patch('namediff.Namediff')
    def test_cli_json_and_csv_flags(self, mock_namediff_cls, mock_cbow_cls):
        infile = os.path.join('testdata', 'tarkir.json')
        outfile_json = os.path.join(self.temp_dir.name, 'custom_out.json')
        outfile_csv = os.path.join(self.temp_dir.name, 'custom_out.csv')

        mock_nd = MagicMock()
        mock_nd.nearest.return_value = [(0.4, 'Target')]
        mock_nd.nearest_par.side_effect = lambda names, n=1: [[(0.4, 'Target')] for _ in names]
        mock_namediff_cls.return_value = mock_nd

        mock_cb = MagicMock()
        mock_cb.nearest.return_value = [(0.5, 'Target')]
        mock_cb.nearest_par.side_effect = lambda cards, n=1: [[(0.5, 'Target')] for _ in cards]
        mock_cbow_cls.return_value = mock_cb

        # Test CLI -j
        test_args_json = ['distances.py', infile, outfile_json, '-j']
        with patch.object(sys, 'argv', test_args_json):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_module('scripts.distances', run_name='__main__')
            self.assertEqual(cm.exception.code, 0)
        self.assertTrue(os.path.exists(outfile_json))

        # Test CLI --csv
        test_args_csv = ['distances.py', infile, outfile_csv, '--csv']
        with patch.object(sys, 'argv', test_args_csv):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_module('scripts.distances', run_name='__main__')
            self.assertEqual(cm.exception.code, 0)
        self.assertTrue(os.path.exists(outfile_csv))

if __name__ == '__main__':
    unittest.main()
