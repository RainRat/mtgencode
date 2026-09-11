import os
import json
import runpy
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from scripts.sanity import check_lines, check_vocab, check_characters

class TestSanity(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.infile = os.path.join(self.tmpdir.name, "output.txt")

        # Create a sample encoded card file with labeled MTG cards (one standard, one with bside)
        card_content = (
            "|1Card One|7common|5Creature|32/2|2Flying\nWhen Card One enters the battlefield, draw a card.\n\n"
            "|1Card Two|7rare|5Instant|2Counter target spell.\n\n"
        )
        with open(self.infile, "w", encoding="utf-8") as f:
            f.write(card_content)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_check_lines_basic(self):
        with patch("builtins.print") as mock_print:
            check_lines(self.infile)
            mock_print.assert_called()
            printed_strings = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            self.assertTrue(any("prel:" in s for s in printed_strings))

    def test_check_lines_bside_and_empty_line(self):
        # Create mock cards including a card with bside and empty lines in separated parts
        mock_card = MagicMock()
        mock_card.name = "Mock Card"
        mock_card.text.text = "Mock Text"
        mock_card.text.encode.return_value = "mock encoded"

        mock_bside = MagicMock()
        mock_bside.text.encode.return_value = "mock bside encoded"
        mock_card.bside = mock_bside

        with patch("jdecode.mtg_open_file", return_value=[mock_card]):
            with patch("transforms.separate_lines") as mock_sep:
                # Return empty line in prel, postl, keyl, mainl, costl
                mock_sep.side_effect = [
                    ([""], [" "], ["\n"], ["\t"], ["   "]),
                    (["prel2"], ["key2"], ["main2"], ["cost2"], ["post2"])
                ]
                with patch("builtins.print") as mock_print:
                    check_lines("dummy.txt")
                    mock_print.assert_called()

    def test_check_vocab_basic(self):
        with patch("builtins.print") as mock_print:
            check_vocab(self.infile)
            mock_print.assert_called()

    def test_check_vocab_bside(self):
        mock_card = MagicMock()
        mock_card.text.vectorize.return_value = "word1 word2"
        mock_bside = MagicMock()
        mock_bside.text.vectorize.return_value = "word2 word3"
        mock_card.bside = mock_bside
        mock_card.encode.return_value = "mock card encoded"

        with patch("jdecode.mtg_open_file", return_value=[mock_card]):
            with patch("builtins.print") as mock_print:
                check_vocab("dummy.txt")
                mock_print.assert_called()

    def test_check_characters_no_vname(self):
        with patch("builtins.print") as mock_print:
            check_characters(self.infile, vname=None)
            mock_print.assert_called()

    def test_check_characters_with_vname(self):
        vocab_out = os.path.join(self.tmpdir.name, "vocab.json")
        with patch("builtins.print") as mock_print:
            check_characters(self.infile, vname=vocab_out)
            mock_print.assert_called()

        self.assertTrue(os.path.exists(vocab_out))
        with open(vocab_out, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("token_to_idx", data)
        self.assertIn("idx_to_token", data)

    def test_main_cli_no_flags(self):
        test_args = ["sanity.py", self.infile]
        with patch("sys.argv", test_args):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path("scripts/sanity.py", run_name="__main__")
            self.assertEqual(cm.exception.code, 1)

    def test_main_cli_lines(self):
        test_args = ["sanity.py", self.infile, "-lines"]
        with patch("sys.argv", test_args):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path("scripts/sanity.py", run_name="__main__")
            self.assertEqual(cm.exception.code, 0)

    def test_main_cli_vocab(self):
        test_args = ["sanity.py", self.infile, "-vocab"]
        with patch("sys.argv", test_args):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path("scripts/sanity.py", run_name="__main__")
            self.assertEqual(cm.exception.code, 0)

    def test_main_cli_chars(self):
        vocab_out = os.path.join(self.tmpdir.name, "vocab_cli.json")
        test_args = ["sanity.py", self.infile, "-chars", "--vocab_name", vocab_out]
        with patch("sys.argv", test_args):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path("scripts/sanity.py", run_name="__main__")
            self.assertEqual(cm.exception.code, 0)
        self.assertTrue(os.path.exists(vocab_out))

if __name__ == "__main__":
    unittest.main()
