import sys
import runpy
import unittest
from unittest.mock import patch

class TestInteractiveDatasetAutodetect(unittest.TestCase):

    @patch('sys.stdin.isatty', return_value=True)
    @patch('os.path.exists')
    @patch('jdecode.mtg_open_file', return_value=[])
    def test_encode_interactive_default_dataset_exists(self, mock_open_file, mock_exists, mock_isatty):
        mock_exists.side_effect = lambda path: True if 'AllPrintings.json' in path else False
        with patch('sys.argv', ['encode.py']), patch('sys.stderr'):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path('encode.py', run_name='__main__')
            self.assertEqual(cm.exception.code, 0)
            mock_open_file.assert_called_once()
            fname_arg = mock_open_file.call_args[0][0]
            self.assertTrue(fname_arg.endswith('AllPrintings.json'))

    @patch('sys.stdin.isatty', return_value=True)
    @patch('os.path.exists', return_value=False)
    def test_encode_interactive_default_dataset_missing(self, mock_exists, mock_isatty):
        with patch('sys.argv', ['encode.py']), patch('sys.stderr'):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path('encode.py', run_name='__main__')
            self.assertEqual(cm.exception.code, 1)

    @patch('sys.stdin.isatty', return_value=True)
    def test_decode_interactive_missing_file_error(self, mock_isatty):
        with patch('sys.argv', ['decode.py']), patch('sys.stderr'):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path('decode.py', run_name='__main__')
            self.assertEqual(cm.exception.code, 1)

    @patch('sys.stdin.isatty', return_value=False)
    @patch('jdecode.mtg_open_file', return_value=[])
    def test_decode_non_interactive_stdin(self, mock_open_file, mock_isatty):
        with patch('sys.argv', ['decode.py']), patch('sys.stderr'):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path('decode.py', run_name='__main__')
            self.assertEqual(cm.exception.code, 0)
            mock_open_file.assert_called_once()
            fname_arg = mock_open_file.call_args[0][0]
            self.assertEqual(fname_arg, '-')

if __name__ == '__main__':
    unittest.main()
