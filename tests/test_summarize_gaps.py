import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os

sys.path.append(os.getcwd())

from scripts.mtg_analyze import main as summarize_cli_main

class TestSummarizeGaps(unittest.TestCase):

    def run_main(self, args, stdin_isatty=False, stdout_isatty=False):
        with patch('sys.argv', ['mtg_analyze.py', 'summary'] + args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.stderr', new=io.StringIO()) as fake_err:
                    with patch('sys.stdin.isatty', return_value=stdin_isatty):
                        with patch('sys.stdout.isatty', return_value=stdout_isatty):
                            try:
                                summarize_cli_main()
                                code = 0
                            except SystemExit as e:
                                code = e.code if isinstance(e.code, int) else 0
                            return code, fake_out.getvalue(), fake_err.getvalue()

    @patch('scripts.mtg_analyze.handle_summary')
    @patch('os.path.exists', return_value=True)
    def test_cli_basic(self, mock_exists, mock_handle):
        code, out, err = self.run_main(['test.json'])
        self.assertEqual(code, 0)
        mock_handle.assert_called_once()
        self.assertEqual(mock_handle.call_args[0][0].infile, 'test.json')

    @patch('scripts.mtg_analyze.handle_summary')
    def test_cli_smart_swap(self, mock_handle):
        # First exists, second doesn't: no swap
        def side_effect(path):
            if path == 'exists.json': return True
            return False

        with patch('os.path.exists', side_effect=side_effect):
            self.run_main(['exists.json', 'not_exists.json'])
            self.assertEqual(mock_handle.call_args[0][0].infile, 'exists.json')
            self.assertEqual(mock_handle.call_args[0][0].outfile, 'not_exists.json')

        mock_handle.reset_mock()
        # First doesn't exist, second does: swap
        with patch('os.path.exists', side_effect=side_effect):
            self.run_main(['query.json', 'exists.json'])
            self.assertEqual(mock_handle.call_args[0][0].infile, 'exists.json')
            self.assertEqual(mock_handle.call_args[0][0].grep, ['query.json'])

        mock_handle.reset_mock()
        # Only one argument, doesn't exist: treat as query
        with patch('os.path.exists', return_value=False):
            self.run_main(['query_only'])
            self.assertEqual(mock_handle.call_args[0][0].infile, '-')
            self.assertEqual(mock_handle.call_args[0][0].grep, ['query_only'])

        mock_handle.reset_mock()
        # Test append to existing grep
        with patch('os.path.exists', side_effect=side_effect):
            self.run_main(['query2.json', 'exists.json', '--grep', 'pattern1'])
            self.assertEqual(mock_handle.call_args[0][0].grep, ['pattern1', 'query2.json'])

        mock_handle.reset_mock()
        with patch('os.path.exists', return_value=False):
            self.run_main(['query_only', '--grep', 'pattern1'])
            self.assertEqual(mock_handle.call_args[0][0].grep, ['pattern1', 'query_only'])

    @patch('scripts.mtg_analyze.handle_summary')
    def test_cli_default_dataset(self, mock_handle):
        def side_effect(path):
            if 'AllPrintings.json' in path: return True
            return False

        with patch('os.path.exists', side_effect=side_effect):
            self.run_main(['-'], stdin_isatty=True)
            self.assertIn('AllPrintings.json', mock_handle.call_args[0][0].infile)

        mock_handle.reset_mock()
        # Test secondary default location
        def side_effect_alt(path):
            if path == 'data/AllPrintings.json': return True
            return False
        with patch('os.path.exists', side_effect=side_effect_alt):
            self.run_main(['-'], stdin_isatty=True)
            self.assertEqual(mock_handle.call_args[0][0].infile, 'data/AllPrintings.json')

    @patch('scripts.mtg_analyze.handle_summary')
    @patch('os.path.exists', return_value=True)
    def test_cli_sample_flag(self, mock_exists, mock_handle):
        self.run_main(['test.json', '--sample', '5'])
        self.assertTrue(mock_handle.call_args[0][0].shuffle)
        self.assertEqual(mock_handle.call_args[0][0].limit, 5)

    @patch('scripts.mtg_analyze.handle_summary')
    @patch('os.path.exists', return_value=True)
    def test_cli_filtering_flags(self, mock_exists, mock_handle):
        self.run_main(['test.json', '--rarity', 'common', '--rarity', 'uncommon', '--cmc', '3'])
        self.assertEqual(mock_handle.call_args[0][0].rarity, ['common', 'uncommon'])
        self.assertEqual(mock_handle.call_args[0][0].cmc, ['3'])

    @patch('scripts.mtg_analyze.handle_summary')
    @patch('os.path.exists', return_value=True)
    def test_cli_grep_flags(self, mock_exists, mock_handle):
        self.run_main(['test.json', '--grep-name', 'Elf', '--exclude-name', 'Flying'])
        self.assertEqual(mock_handle.call_args[0][0].grep_name, ['Elf'])
        self.assertEqual(mock_handle.call_args[0][0].exclude_name, ['Flying'])

if __name__ == '__main__':
    unittest.main()
