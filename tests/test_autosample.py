import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import runpy

from scripts.autosample import extract_cp_name, find_best_cp, sample, process_dir, main


class TestAutosample(unittest.TestCase):
    def test_extract_cp_name_valid(self):
        filename = 'lm_lstm_epoch50.00_0.1870.t7'
        result = extract_cp_name(filename)
        self.assertEqual(result, (50.0, 0.1870))

    def test_extract_cp_name_invalid_format(self):
        self.assertIsNone(extract_cp_name('invalid_filename.t7'))
        self.assertIsNone(extract_cp_name('lm_lstm_epoch50.00_0.1870.txt'))
        self.assertIsNone(extract_cp_name('lm_lstm_epoch50.00_invalid.t7'))
        self.assertIsNone(extract_cp_name('lm_lstm_epoch50.00_0.1870_extra.t7'))

    def test_find_best_cp(self):
        with patch('os.listdir') as mock_listdir, patch('os.path.isfile') as mock_isfile:
            mock_listdir.return_value = [
                'lm_lstm_epoch10.00_0.2500.t7',
                'lm_lstm_epoch20.00_0.1500.t7',
                'lm_lstm_epoch30.00_0.1800.t7',
                'some_other_file.txt',
            ]
            mock_isfile.return_value = True

            best_cp = find_best_cp('/fake/dir')
            self.assertEqual(best_cp, os.path.join('/fake/dir', 'lm_lstm_epoch20.00_0.1500.t7'))

    def test_find_best_cp_empty_or_no_valid(self):
        with patch('os.listdir') as mock_listdir, patch('os.path.isfile') as mock_isfile:
            mock_listdir.return_value = ['other.txt', 'lm_lstm_epoch_bad.t7']
            mock_isfile.return_value = True
            self.assertIsNone(find_best_cp('/fake/dir'))

    def test_sample_file_exists(self):
        with patch('os.path.exists', return_value=True), patch('builtins.print') as mock_print:
            result = sample('/fake/cp.t7', 0.8, 500, seed=123, ident='out')
            self.assertFalse(result)
            mock_print.assert_called_with('/fake/cp.t7.out.0.8.txt already exists, skipping')

    def test_sample_file_does_not_exist(self):
        with patch('os.path.exists', return_value=False), \
             patch('builtins.open', unittest.mock.mock_open()) as mock_file, \
             patch('subprocess.run') as mock_run:
            sample('/fake/cp.t7', 0.8, 500, seed=123, ident='out')

            expected_outfile = '/fake/cp.t7.out.0.8.txt'
            expected_cmd = ['th', 'sample.lua', '/fake/cp.t7', '-temperature', '0.8', '-length', '500', '-seed', '123']
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            self.assertEqual(args[0], expected_cmd)

    def test_sample_default_seed(self):
        with patch('os.path.exists', return_value=False), \
             patch('builtins.open', unittest.mock.mock_open()), \
             patch('subprocess.run') as mock_run, \
             patch('random.randint', return_value=42):
            sample('/fake/cp.t7', 0.8, 500, seed=None, ident='out')
            args, kwargs = mock_run.call_args
            self.assertIn('-seed', args[0])
            self.assertIn('42', args[0])

    def test_process_dir(self):
        with patch('scripts.autosample.find_best_cp', return_value='/fake/best.t7') as mock_find, \
             patch('scripts.autosample.sample') as mock_sample, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.isdir') as mock_isdir, \
             patch('builtins.print') as mock_print:

            mock_listdir.side_effect = [
                ['subdir'],
                []
            ]
            mock_isdir.side_effect = lambda p: p.endswith('subdir')

            process_dir('/fake/cpdir', 0.8, 500, seed=123, ident='out', verbose=True)

            self.assertEqual(mock_find.call_count, 2)
            self.assertEqual(mock_sample.call_count, 2)
            mock_print.assert_any_call('processing /fake/cpdir')

    def test_main_invalid_dirs(self):
        with patch('os.path.isdir', side_effect=[False, True]):
            with self.assertRaises(ValueError):
                main('/bad/rnn', '/good/cp', 0.8, 500)

        with patch('os.path.isdir', side_effect=[True, False]):
            with self.assertRaises(ValueError):
                main('/good/rnn', '/bad/cp', 0.8, 500)

    def test_main_valid(self):
        with patch('os.path.isdir', return_value=True), \
             patch('os.chdir') as mock_chdir, \
             patch('scripts.autosample.process_dir') as mock_process:
            main('/good/rnn', '/good/cp', 0.8, 500, seed=123, ident='out', verbose=False)
            mock_chdir.assert_called_once_with('/good/rnn')
            mock_process.assert_called_once_with('/good/cp', 0.8, 500, seed=123, ident='out', verbose=False)

    def test_cli_execution(self):
        test_args = [
            'autosample.py',
            '/fake/rnn',
            '/fake/cp',
            '-t', '0.7',
            '-c', '1000',
            '-s', '999',
            '-i', 'test_ident',
            '-v'
        ]
        with patch.object(sys, 'argv', test_args), \
             patch('os.path.isdir', return_value=True), \
             patch('os.chdir'), \
             patch('os.listdir', return_value=[]), \
             patch('sys.exit') as mock_exit:
            runpy.run_path('scripts/autosample.py', run_name='__main__')
            mock_exit.assert_called_once_with(0)

    def test_cli_execution_default_seed(self):
        test_args = [
            'autosample.py',
            '/fake/rnn',
            '/fake/cp'
        ]
        with patch.object(sys, 'argv', test_args), \
             patch('os.path.isdir', return_value=True), \
             patch('os.chdir'), \
             patch('os.listdir', return_value=[]), \
             patch('sys.exit') as mock_exit:
            runpy.run_path('scripts/autosample.py', run_name='__main__')
            mock_exit.assert_called_once_with(0)


if __name__ == '__main__':
    unittest.main()
