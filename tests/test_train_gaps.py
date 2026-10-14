import unittest
import sys
import os
import io
import tempfile
from unittest.mock import patch
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import train

class TestTrainGaps(unittest.TestCase):

    def test_augment_card_no_randomization(self):
        card = "|1Grizzly Bears|5Creature|82/2|3{1}{G}|Card body text\n\n"
        result = train.augment_card(card, randomize_fields=False, randomize_mana=False)
        self.assertEqual(result, card)

    def test_augment_card_field_and_mana_randomization(self):
        card = "|1Grizzly Bears|5Creature|82/2|3{1^G^W}|Card body text\n\n"
        result = train.augment_card(card, randomize_fields=True, randomize_mana=True)
        self.assertTrue(result.endswith("Card body text\n\n"))
        self.assertIn("1Grizzly Bears", result)
        self.assertIn("5Creature", result)

    def test_char_dataset(self):
        raw_data = "|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n|1Giant Growth|5Instant|9+3/+3|3{G}|\n\n"
        seq_len = 10
        dataset = train.CharDataset(raw_data, seq_len=seq_len, randomize_fields=True, randomize_mana=True)

        self.assertGreater(len(dataset), 0)
        self.assertEqual(len(dataset.cards), 2)

        x_idx, y_idx = dataset[0]
        self.assertIsInstance(x_idx, torch.Tensor)
        self.assertIsInstance(y_idx, torch.Tensor)
        self.assertEqual(x_idx.shape[0], seq_len)
        self.assertEqual(y_idx.shape[0], seq_len)

        dataset.refresh_data()
        self.assertGreater(len(dataset.data_str), 0)

    def test_char_rnn_model_and_bias_init(self):
        vocab_size = 30
        hidden_size = 16
        n_layers = 2
        model = train.CharRNN(vocab_size=vocab_size, hidden_size=hidden_size, n_layers=n_layers, dropout=0.1)

        device = torch.device("cpu")
        hidden = model.init_hidden(batch_size=2, device=device)
        self.assertEqual(len(hidden), 2)
        self.assertEqual(hidden[0].shape, (n_layers, 2, hidden_size))
        self.assertEqual(hidden[1].shape, (n_layers, 2, hidden_size))

        x = torch.randint(0, vocab_size, (2, 5))
        out, new_hidden = model(x, hidden)
        self.assertEqual(out.shape, (2, 5, vocab_size))

        for name, param in model.rnn.named_parameters():
            if 'bias' in name:
                n = param.size(0)
                start, end = n // 4, n // 2
                self.assertTrue(torch.allclose(param.data[start:end], torch.ones(end - start)))

    def test_generate_text_forced_attributes(self):
        raw_data = "|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n"
        dataset = train.CharDataset(raw_data, seq_len=5)
        model = train.CharRNN(dataset.vocab_size, hidden_size=16, n_layers=1)
        device = torch.device("cpu")

        parser = train.get_parser()
        args = parser.parse_args([
            '--mode', 'sample',
            '--types', 'creature',
            '--length', '20'
        ])

        pipe_idx = dataset.char_to_idx['|']
        buf = io.StringIO()
        with patch('numpy.random.choice', return_value=pipe_idx), patch('sys.stdout', buf):
            generated = train.generate_text(
                model,
                dataset.char_to_idx,
                dataset.idx_to_char,
                dataset.vocab_size,
                device,
                args,
                length=20,
                quiet=True
            )

        self.assertIsInstance(generated, str)
        self.assertIn("creature", generated)

    def test_train_non_dryrun_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            infile = os.path.join(tmpdir, "train_data.txt")
            checkpoint = os.path.join(tmpdir, "checkpoint.pt")

            with open(infile, "w", encoding="utf-8") as f:
                f.write("|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n" * 4)

            parser = train.get_parser()
            args = parser.parse_args([
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint,
                '--epochs', '1',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--sample_epochs', '1',
                '--plot_loss',
                '--show_time',
                '--randomize_fields',
                '--randomize_mana'
            ])

            plot_file = 'loss_plot.png'
            if os.path.exists(plot_file):
                os.remove(plot_file)

            try:
                buf = io.StringIO()
                with patch('sys.stdout', buf):
                    train.train(args)

                out = buf.getvalue()
                self.assertIn("Epoch 1 average loss", out)
                self.assertIn("Sampling after epoch 1", out)
                self.assertTrue(os.path.exists(checkpoint))
                self.assertTrue(os.path.exists(plot_file))
            finally:
                if os.path.exists(plot_file):
                    os.remove(plot_file)

    def test_train_plot_loss_exception_handling(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            infile = os.path.join(tmpdir, "train_data.txt")
            checkpoint = os.path.join(tmpdir, "checkpoint.pt")

            with open(infile, "w", encoding="utf-8") as f:
                f.write("|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n" * 4)

            parser = train.get_parser()
            args = parser.parse_args([
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint,
                '--epochs', '1',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--plot_loss'
            ])

            buf = io.StringIO()
            with patch('matplotlib.pyplot.savefig', side_effect=RuntimeError("Plotting error")), patch('sys.stdout', buf):
                train.train(args)

            out = buf.getvalue()
            self.assertIn("Could not plot loss:", out)

    def test_train_resume_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            infile = os.path.join(tmpdir, "train_data.txt")
            checkpoint = os.path.join(tmpdir, "checkpoint.pt")

            with open(infile, "w", encoding="utf-8") as f:
                f.write("|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n" * 4)

            parser = train.get_parser()
            args1 = parser.parse_args([
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint,
                '--epochs', '1',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1'
            ])
            buf1 = io.StringIO()
            with patch('sys.stdout', buf1):
                train.train(args1)

            self.assertTrue(os.path.exists(checkpoint))

            args2 = parser.parse_args([
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint,
                '--epochs', '2',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--resume'
            ])
            buf2 = io.StringIO()
            with patch('sys.stdout', buf2):
                train.train(args2)

            out2 = buf2.getvalue()
            self.assertIn("Resuming from epoch 1", out2)
            self.assertIn("Epoch 2 average loss", out2)

    def test_train_max_hours_before_epoch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            infile = os.path.join(tmpdir, "train_data.txt")
            checkpoint = os.path.join(tmpdir, "checkpoint.pt")

            with open(infile, "w", encoding="utf-8") as f:
                f.write("|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n" * 10)

            parser = train.get_parser()
            args = parser.parse_args([
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint,
                '--epochs', '5',
                '--batch_size', '1',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--max_hours', '0.0000000001'
            ])

            buf = io.StringIO()
            with patch('sys.stdout', buf):
                train.train(args)

            out = buf.getvalue()
            self.assertIn("Time limit", out)

    def test_train_max_hours_during_epoch_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            infile = os.path.join(tmpdir, "train_data.txt")
            checkpoint = os.path.join(tmpdir, "checkpoint.pt")

            with open(infile, "w", encoding="utf-8") as f:
                f.write("|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n" * 20)

            parser = train.get_parser()
            args = parser.parse_args([
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint,
                '--epochs', '5',
                '--batch_size', '1',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--max_hours', '1.0'
            ])

            real_time = train.time.time
            start_t = real_time()
            call_count = [0]

            def time_side_effect():
                call_count[0] += 1
                if call_count[0] > 2:
                    return start_t + 7200.0
                return real_time()

            buf = io.StringIO()
            with patch('train.time.time', side_effect=time_side_effect), patch('sys.stdout', buf):
                train.train(args)

            out = buf.getvalue()
            self.assertIn("Time limit", out)
            self.assertIn("Saving and stopping", out)
            self.assertTrue(os.path.exists(checkpoint))

    def test_sample_non_dryrun_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            infile = os.path.join(tmpdir, "train_data.txt")
            checkpoint = os.path.join(tmpdir, "checkpoint.pt")

            with open(infile, "w", encoding="utf-8") as f:
                f.write("|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n" * 4)

            parser = train.get_parser()
            train_args = parser.parse_args([
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint,
                '--epochs', '1',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1'
            ])
            with patch('sys.stdout', io.StringIO()):
                train.train(train_args)

            sample_args = parser.parse_args([
                '--mode', 'sample',
                '--checkpoint', checkpoint,
                '--length', '50',
                '--temp', '0.8',
                '--start_text', '|'
            ])

            buf = io.StringIO()
            with patch('sys.stdout', buf):
                train.sample(sample_args)

            out = buf.getvalue()
            self.assertGreater(len(out), 0)

if __name__ == '__main__':
    unittest.main()
