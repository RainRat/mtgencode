import unittest
import os
import sys
import io
import tempfile
import argparse
import torch
import runpy
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import train

class TestTrainCore(unittest.TestCase):

    def setUp(self):
        self.device = torch.device("cpu")
        self.sample_cards = (
            "|1Grizzly Bears|5Creature|82/2|3{1^G}|2Bears are strong.\n\n"
            "|1Giant Growth|5Instant|9+3/+3|3{G}|2Pump target creature.\n\n"
            "|1Counterspell|5Instant|3{U^U}|2Counter target spell.\n\n"
        )

    def test_augment_card_randomize_mana(self):
        card_text = "|1Card|3{1^G^U}|\n\n"
        augmented = train.augment_card(card_text, randomize_fields=False, randomize_mana=True)
        self.assertTrue(augmented.startswith("|1Card|3{"))
        symbols = augmented.split('{')[1].split('}')[0].split('^')
        self.assertCountEqual(symbols, ['1', 'G', 'U'])

    def test_augment_card_randomize_fields(self):
        card_text = "|1Card|5Creature|82/2|3{1}|\n\n"
        augmented = train.augment_card(card_text, randomize_fields=True, randomize_mana=False)
        self.assertTrue(augmented.endswith("|\n\n"))
        fields = augmented.split('|')
        self.assertEqual(fields[-1], "\n\n")

    def test_augment_card_no_randomization(self):
        card_text = "|1Card|5Creature|\n\n"
        augmented = train.augment_card(card_text, randomize_fields=False, randomize_mana=False)
        self.assertEqual(augmented, card_text)

    def test_augment_card_single_field(self):
        card_text = "NoSeparators"
        augmented = train.augment_card(card_text, randomize_fields=True, randomize_mana=True)
        self.assertEqual(augmented, "NoSeparators")

    def test_char_dataset_initialization_and_len(self):
        dataset = train.CharDataset(self.sample_cards, seq_len=15)
        self.assertGreater(dataset.vocab_size, 0)
        self.assertEqual(len(dataset.cards), 3)
        self.assertEqual(len(dataset), len(dataset.data_str) - 15)

    def test_char_dataset_getitem(self):
        seq_len = 10
        dataset = train.CharDataset(self.sample_cards, seq_len=seq_len)
        x_idx, y_idx = dataset[0]
        self.assertIsInstance(x_idx, torch.Tensor)
        self.assertIsInstance(y_idx, torch.Tensor)
        self.assertEqual(x_idx.shape, torch.Size([seq_len]))
        self.assertEqual(y_idx.shape, torch.Size([seq_len]))
        self.assertEqual(y_idx[:-1].tolist(), x_idx[1:].tolist())

    def test_char_dataset_refresh_data_with_randomization(self):
        dataset = train.CharDataset(self.sample_cards, seq_len=10, randomize_fields=True, randomize_mana=True)
        prev_str = dataset.data_str
        dataset.refresh_data()
        self.assertGreater(len(dataset.data_str), 0)

    def test_char_rnn_forward_pass_and_hidden(self):
        vocab_size = 30
        hidden_size = 16
        n_layers = 2
        batch_size = 4
        seq_len = 8

        model = train.CharRNN(vocab_size, hidden_size, n_layers, dropout=0.0)
        hidden = model.init_hidden(batch_size, self.device)
        self.assertEqual(len(hidden), 2)
        self.assertEqual(hidden[0].shape, (n_layers, batch_size, hidden_size))
        self.assertEqual(hidden[1].shape, (n_layers, batch_size, hidden_size))

        dummy_input = torch.randint(0, vocab_size, (batch_size, seq_len), dtype=torch.long)
        out, (h_n, c_n) = model(dummy_input, hidden)
        self.assertEqual(out.shape, (batch_size, seq_len, vocab_size))
        self.assertEqual(h_n.shape, (n_layers, batch_size, hidden_size))

    def test_generate_text_basic(self):
        vocab = sorted(list(set(self.sample_cards)))
        char_to_idx = {c: i for i, c in enumerate(vocab)}
        idx_to_char = {i: c for i, c in enumerate(vocab)}
        vocab_size = len(vocab)

        model = train.CharRNN(vocab_size, hidden_size=16, n_layers=1, dropout=0.0)
        args = argparse.Namespace(length=30, temp=0.8, start_text="|")
        generated = train.generate_text(model, char_to_idx, idx_to_char, vocab_size, self.device, args, length=30, quiet=True)
        self.assertIsInstance(generated, str)
        self.assertTrue(generated.startswith("|"))
        self.assertGreaterEqual(len(generated), 30)

    def test_generate_text_with_whisper_attributes(self):
        vocab = sorted(list(set(self.sample_cards + "|legendary\n")))
        char_to_idx = {c: i for i, c in enumerate(vocab)}
        idx_to_char = {i: c for i, c in enumerate(vocab)}
        vocab_size = len(vocab)
        bar_idx = char_to_idx["|"]

        model = train.CharRNN(vocab_size, hidden_size=16, n_layers=1, dropout=0.0)
        args = argparse.Namespace(
            length=20,
            temp=0.8,
            start_text="|",
            name=None,
            supertypes="legendary",
            types=None,
            loyalty=None,
            subtypes=None,
            rarity=None,
            powertoughness=None,
            manacost=None,
            bodytext_prepend=None,
            bodytext_append=None,
        )

        with patch("numpy.random.choice", return_value=bar_idx):
            generated = train.generate_text(model, char_to_idx, idx_to_char, vocab_size, self.device, args, length=20, quiet=True)

        self.assertIn("legendary", generated)

    def test_train_dryrun_flags_coverage(self):
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
            f.write(self.sample_cards)
            tmp_path = f.name

        try:
            buf = io.StringIO()
            args = argparse.Namespace(
                mode="train",
                infile=tmp_path,
                checkpoint="cp.pt",
                dry_run=True,
                epochs=5,
                max_hours=2.5,
                batch_size=16,
                seq_len=20,
                hidden_size=32,
                n_layers=1,
                lr=0.001,
                dropout=0.1,
                resume=True,
                randomize_fields=True,
                randomize_mana=True,
            )
            with patch("sys.stdout", buf):
                train.train(args)

            out = buf.getvalue()
            self.assertIn("Max Hours: 2.5", out)
            self.assertIn("Randomize Fields: Enabled", out)
            self.assertIn("Randomize Mana: Enabled", out)
            self.assertIn("Resume Training: Enabled", out)

            buf_err = io.StringIO()
            with patch("builtins.open", side_effect=OSError("Read error")), patch("sys.stdout", buf_err):
                train.train(args)
            self.assertIn("0 card(s)", buf_err.getvalue())
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_train_and_sample_execution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = os.path.join(tmp_dir, "dataset.txt")
            checkpoint_path = os.path.join(tmp_dir, "model.pt")

            with open(dataset_path, "w", encoding="utf-8") as f:
                f.write(self.sample_cards * 5)

            train_args = argparse.Namespace(
                mode="train",
                infile=dataset_path,
                checkpoint=checkpoint_path,
                dry_run=False,
                epochs=2,
                max_hours=0,
                batch_size=4,
                seq_len=16,
                hidden_size=16,
                n_layers=1,
                lr=0.01,
                dropout=0.0,
                resume=False,
                randomize_fields=True,
                randomize_mana=True,
                sample_epochs=1,
                plot_loss=True,
                show_time=True,
                length=50,
                temp=0.8,
                start_text="|",
            )

            buf = io.StringIO()
            with patch("sys.stdout", buf), patch("matplotlib.pyplot.savefig") as mock_save:
                train.train(train_args)

            self.assertTrue(os.path.exists(checkpoint_path))
            train_output = buf.getvalue()
            self.assertIn("Epoch 1", train_output)
            self.assertIn("Sampling after epoch 1", train_output)
            self.assertIn("Epoch 2", train_output)
            mock_save.assert_called_once()

            resume_args = argparse.Namespace(
                mode="train",
                infile=dataset_path,
                checkpoint=checkpoint_path,
                dry_run=False,
                epochs=3,
                max_hours=0,
                batch_size=4,
                seq_len=16,
                hidden_size=16,
                n_layers=1,
                lr=0.01,
                dropout=0.0,
                resume=True,
                randomize_fields=False,
                randomize_mana=False,
                sample_epochs=0,
                plot_loss=False,
                show_time=False,
                length=50,
                temp=0.8,
                start_text="|",
            )
            resume_buf = io.StringIO()
            with patch("sys.stdout", resume_buf):
                train.train(resume_args)

            self.assertIn("Resuming from epoch 2", resume_buf.getvalue())

            sample_args = argparse.Namespace(
                mode="sample",
                checkpoint=checkpoint_path,
                dry_run=False,
                length=40,
                temp=0.8,
                start_text="|",
                name=None,
                supertypes=None,
                types=None,
                loyalty=None,
                subtypes=None,
                rarity=None,
                powertoughness=None,
                manacost=None,
                bodytext_prepend=None,
                bodytext_append=None,
            )
            sample_buf = io.StringIO()
            with patch("sys.stdout", sample_buf):
                train.sample(sample_args)

            sample_out = sample_buf.getvalue()
            self.assertGreaterEqual(len(sample_out.strip()), 1)

    def test_train_time_limit_handling_during_epoch(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = os.path.join(tmp_dir, "dataset.txt")
            checkpoint_path = os.path.join(tmp_dir, "model_limit.pt")

            with open(dataset_path, "w", encoding="utf-8") as f:
                f.write(self.sample_cards * 5)

            train_args = argparse.Namespace(
                mode="train",
                infile=dataset_path,
                checkpoint=checkpoint_path,
                dry_run=False,
                epochs=5,
                max_hours=0.0000001,
                batch_size=2,
                seq_len=16,
                hidden_size=16,
                n_layers=1,
                lr=0.01,
                dropout=0.0,
                resume=False,
                randomize_fields=False,
                randomize_mana=False,
                sample_epochs=0,
                plot_loss=False,
                show_time=False,
                length=50,
                temp=0.8,
                start_text="|",
            )

            buf = io.StringIO()
            with patch("sys.stdout", buf), patch("time.time", side_effect=[0, 0, 100, 200, 300, 400]):
                train.train(train_args)

            self.assertIn("Time limit", buf.getvalue())
            self.assertTrue(os.path.exists(checkpoint_path))

    def test_train_time_limit_before_epoch(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = os.path.join(tmp_dir, "dataset.txt")
            checkpoint_path = os.path.join(tmp_dir, "model_limit2.pt")

            with open(dataset_path, "w", encoding="utf-8") as f:
                f.write(self.sample_cards * 5)

            train_args = argparse.Namespace(
                mode="train",
                infile=dataset_path,
                checkpoint=checkpoint_path,
                dry_run=False,
                epochs=5,
                max_hours=0.001,
                batch_size=2,
                seq_len=16,
                hidden_size=16,
                n_layers=1,
                lr=0.01,
                dropout=0.0,
                resume=False,
                randomize_fields=False,
                randomize_mana=False,
                sample_epochs=0,
                plot_loss=False,
                show_time=False,
                length=50,
                temp=0.8,
                start_text="|",
            )

            buf = io.StringIO()
            with patch("sys.stdout", buf), patch("time.time", side_effect=[0, 10, 10, 10, 10, 10]):
                train.train(train_args)

            self.assertIn("Time limit of 0.001 hours reached before starting epoch", buf.getvalue())

    def test_plot_loss_exception_handling(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = os.path.join(tmp_dir, "dataset.txt")
            checkpoint_path = os.path.join(tmp_dir, "model_plot.pt")

            with open(dataset_path, "w", encoding="utf-8") as f:
                f.write(self.sample_cards * 5)

            train_args = argparse.Namespace(
                mode="train",
                infile=dataset_path,
                checkpoint=checkpoint_path,
                dry_run=False,
                epochs=1,
                max_hours=0,
                batch_size=4,
                seq_len=16,
                hidden_size=16,
                n_layers=1,
                lr=0.01,
                dropout=0.0,
                resume=False,
                randomize_fields=False,
                randomize_mana=False,
                sample_epochs=0,
                plot_loss=True,
                show_time=False,
                length=50,
                temp=0.8,
                start_text="|",
            )

            buf = io.StringIO()
            with patch("sys.stdout", buf), patch("matplotlib.pyplot.savefig", side_effect=OSError("Disk full")):
                train.train(train_args)

            self.assertIn("Could not plot loss: Disk full", buf.getvalue())

    def test_main_sample_invocation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            checkpoint_path = os.path.join(tmp_dir, "model_sample.pt")
            buf = io.StringIO()
            test_args = [
                "train.py",
                "--mode", "sample",
                "--checkpoint", checkpoint_path,
                "--dry-run"
            ]
            with patch.object(sys, "argv", test_args), patch("sys.stdout", buf):
                runpy.run_module("train", run_name="__main__")
            self.assertIn("Dry Run Summary: Neural network card generation configuration (sample mode).", buf.getvalue())

if __name__ == '__main__':
    unittest.main()
