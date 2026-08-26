import unittest
import tempfile
import os
import sys
import pickle
import runpy
from unittest.mock import patch, MagicMock

from scripts.ngrams import (
    NgramModelWrapper,
    update_ngrams,
    describe_bins,
    extract_language,
    build_ngram_model,
    main,
)
from lib.cardlib import Card


class TestNgrams(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ngram_model_wrapper(self):
        lang = [["when", "@", "enters"], ["enters", "the", "battlefield"]]
        wrapper = NgramModelWrapper(2, lang)
        perplexity = wrapper.perplexity(["when", "@"])
        self.assertIsInstance(perplexity, float)

        empty_perplexity = wrapper.perplexity([])
        self.assertEqual(empty_perplexity, 0.0)

    def test_update_ngrams(self):
        lines = [["when", "@", "enters", "the", "battlefield"]]
        gramdict = {}
        update_ngrams(lines, gramdict, 2)
        expected = {
            "when @": 1,
            "@ enters": 1,
            "enters the": 1,
            "the battlefield": 1,
        }
        self.assertEqual(gramdict, expected)

        # Update again to verify count incrementing
        update_ngrams(lines, gramdict, 2)
        self.assertEqual(gramdict["when @"], 2)

    def test_describe_bins(self):
        gramdict = {"a b": 1, "c d": 2, "e f": 5, "g h": 1500}
        bins = [1, 2, 10, 100, 1000]

        with patch("builtins.print") as mock_print:
            describe_bins(gramdict, bins)
            mock_print.assert_called()

    def test_extract_language(self):
        card = Card(
            "|5Creature|1Grizzly Bears|3{1}{G}|8&^^/&^^|9When @ enters the battlefield."
        )
        lang_sep = extract_language([card], separate_lines=True)
        self.assertTrue(len(lang_sep) > 0)

        lang_nosep = extract_language([card], separate_lines=False)
        self.assertTrue(len(lang_nosep) > 0)

    def test_build_ngram_model(self):
        card = Card(
            "|5Creature|1Grizzly Bears|3{1}{G}|8&^^/&^^|9When @ enters the battlefield."
        )
        lm = build_ngram_model([card], n=2, separate_lines=True, verbose=True)
        self.assertIsInstance(lm, NgramModelWrapper)

    def test_main_non_nltk(self):
        infile = "testdata/uthros.json"
        out_base = os.path.join(self.temp_dir.name, "out")

        main(infile, out_base, gmin=2, gmax=3, nltk=False, verbose=True)

        out_2g = out_base + ".2g"
        out_3g = out_base + ".3g"
        self.assertTrue(os.path.exists(out_2g))
        self.assertTrue(os.path.exists(out_3g))

        with open(out_2g, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertTrue(len(content) > 0)

    def test_main_invalid_gmin_gmax(self):
        infile = "testdata/uthros.json"
        out_base = os.path.join(self.temp_dir.name, "out")

        with self.assertRaises(SystemExit):
            main(infile, out_base, gmin=3, gmax=2, nltk=False)

    def test_main_nltk_mode(self):
        infile = "testdata/uthros.json"
        out_file = os.path.join(self.temp_dir.name, "model.pkl")

        main(
            infile,
            out_file,
            gmin=2,
            gmax=2,
            nltk=True,
            sep=True,
            verbose=True,
        )

        self.assertTrue(os.path.exists(out_file))
        with open(out_file, "rb") as f:
            model = pickle.load(f)
            self.assertIsInstance(model, NgramModelWrapper)

    def test_cli_execution(self):
        out_base = os.path.join(self.temp_dir.name, "cli_out")
        test_args = [
            "scripts/ngrams.py",
            "testdata/uthros.json",
            out_base,
            "--min",
            "2",
            "--max",
            "2",
        ]

        with patch.object(sys, "argv", test_args):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_module("scripts.ngrams", run_name="__main__")
            self.assertEqual(cm.exception.code, 0)

        self.assertTrue(os.path.exists(out_base + ".2g"))


if __name__ == "__main__":
    unittest.main()
