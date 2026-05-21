import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os

sys.path.append(os.getcwd())

from scripts.mtg_analyze import main as summarize_cli_main

class TestSummarizeGaps(unittest.TestCase):

    def run_main(self, args, stdin_isatty=False, stdout_isatty=False):
        with patch('sys.argv', ['mtg_analyze.py'] + args):
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

    @patch('scripts.mtg_analyze.summarize_data')
    @patch('os.path.exists', return_value=True)
    def test_cli_basic(self, mock_exists, mock_summarize):
        code, out, err = self.run_main(['test.json'])
        self.assertEqual(code, 0)
        mock_summarize.assert_called_once()
        self.assertEqual(mock_summarize.call_args[0][0], 'test.json')

    @patch('scripts.mtg_analyze.summarize_data')
    def test_cli_smart_swap(self, mock_summarize):
        # First exists, second doesn't: no swap
        def side_effect(path):
            if path == 'exists.json': return True
            return False

        with patch('os.path.exists', side_effect=side_effect):
            self.run_main(['exists.json', 'not_exists.json'])
            self.assertEqual(mock_summarize.call_args[0][0], 'exists.json')
            self.assertEqual(mock_summarize.call_args[1]['oname'], 'not_exists.json')

        mock_summarize.reset_mock()
        # First doesn't exist, second does: swap
        with patch('os.path.exists', side_effect=side_effect):
            self.run_main(['query.json', 'exists.json'])
            self.assertEqual(mock_summarize.call_args[0][0], 'exists.json')
            self.assertEqual(mock_summarize.call_args[1]['grep'], ['query.json'])

        mock_summarize.reset_mock()
        # Only one argument, doesn't exist: treat as query
        with patch('os.path.exists', return_value=False):
            self.run_main(['query_only'])
            self.assertEqual(mock_summarize.call_args[0][0], '-')
            self.assertEqual(mock_summarize.call_args[1]['grep'], ['query_only'])

        mock_summarize.reset_mock()
        # Test append to existing grep
        with patch('os.path.exists', side_effect=side_effect):
            self.run_main(['query2.json', 'exists.json', '--grep', 'pattern1'])
            self.assertEqual(mock_summarize.call_args[1]['grep'], ['pattern1', 'query2.json'])

        mock_summarize.reset_mock()
        with patch('os.path.exists', return_value=False):
            self.run_main(['query_only', '--grep', 'pattern1'])
            self.assertEqual(mock_summarize.call_args[1]['grep'], ['pattern1', 'query_only'])

    @patch('scripts.mtg_analyze.summarize_data')
    def test_cli_default_dataset(self, mock_summarize):
        def side_effect(path):
            if 'AllPrintings.json' in path: return True
            return False

        with patch('os.path.exists', side_effect=side_effect):
            self.run_main(['-'], stdin_isatty=True)
            self.assertIn('AllPrintings.json', mock_summarize.call_args[0][0])

        mock_summarize.reset_mock()
        # Test secondary default location
        def side_effect_alt(path):
            if path == 'data/AllPrintings.json': return True
            return False
        with patch('os.path.exists', side_effect=side_effect_alt):
            self.run_main(['-'], stdin_isatty=True)
            self.assertEqual(mock_summarize.call_args[0][0], 'data/AllPrintings.json')

    @patch('scripts.mtg_analyze.summarize_data')
    @patch('os.path.exists', return_value=True)
    def test_cli_sample_flag(self, mock_exists, mock_summarize):
        self.run_main(['test.json', '--sample', '5'])
        self.assertTrue(mock_summarize.call_args[1]['shuffle'])
        self.assertEqual(mock_summarize.call_args[1]['limit'], 5)

    @patch('scripts.mtg_analyze.summarize_data')
    @patch('os.path.exists', return_value=True)
    def test_cli_filtering_flags(self, mock_exists, mock_summarize):
        self.run_main(['test.json', '--rarity', 'common', '--rarity', 'uncommon', '--cmc', '3'])
        self.assertEqual(mock_summarize.call_args[1]['rarities'], ['common', 'uncommon'])
        self.assertEqual(mock_summarize.call_args[1]['cmcs'], ['3'])

    @patch('scripts.mtg_analyze.summarize_data')
    @patch('os.path.exists', return_value=True)
    def test_cli_grep_flags(self, mock_exists, mock_summarize):
        self.run_main(['test.json', '--grep-name', 'Elf', '--exclude-name', 'Flying'])
        self.assertEqual(mock_summarize.call_args[1]['grep_name'], ['Elf'])
        self.assertEqual(mock_summarize.call_args[1]['vgrep_name'], ['Flying'])

if __name__ == '__main__':
    unittest.main()
