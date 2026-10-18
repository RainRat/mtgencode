import unittest
import sys
import os
import io
import tempfile
import torch
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import train

class TestTrainGaps(unittest.TestCase):

    def test_augment_card(self):
        card_text = "|1CardName|3Creature|8{G^1}|Body text.\n\n"
        augmented = train.augment_card(card_text, randomize_fields=True, randomize_mana=True)
        self.assertIn("Body text.\n\n", augmented)
        self.assertIn("1CardName", augmented)
        self.assertIn("3Creature", augmented)

    def test_char_dataset(self):
        raw_data = "|1CardOne|3Creature|\n\n|1CardTwo|3Instant|\n\n"
        dataset = train.CharDataset(raw_data, seq_len=10, randomize_fields=True, randomize_mana=True)
        self.assertGreater(len(dataset), 0)

        x_idx, y_idx = dataset[0]
        self.assertEqual(x_idx.shape[0], 10)
        self.assertEqual(y_idx.shape[0], 10)

        # Test refresh_data
        dataset.refresh_data()
        self.assertIsInstance(dataset.data_str, str)

    def test_char_rnn(self):
        vocab_size = 20
        hidden_size = 16
        n_layers = 1
        model = train.CharRNN(vocab_size, hidden_size, n_layers)

        device = torch.device("cpu")
        hidden = model.init_hidden(batch_size=2, device=device)
        self.assertEqual(hidden[0].shape, (1, 2, 16))
        self.assertEqual(hidden[1].shape, (1, 2, 16))

        x = torch.zeros((2, 5), dtype=torch.long)
        out, new_hidden = model(x, hidden)
        self.assertEqual(out.shape, (2, 5, 20))

    def test_generate_text_and_whisper_map(self):
        raw_data = "|1CardOne|2Legendary|3Creature|45|5Elf|6R|72/2|8{G}|9Pre|10App\n\n"
        dataset = train.CharDataset(raw_data, seq_len=5)
        model = train.CharRNN(dataset.vocab_size, hidden_size=16, n_layers=1)
        device = torch.device("cpu")

        parser = train.get_parser()
        args = parser.parse_args([
            '--mode', 'sample',
            '--start_text', '|',
            '--length', '100',
            '--temp', '0.8',
            '--name', 'Uthros'
        ])

        generated = train.generate_text(
            model=model,
            char_to_idx=dataset.char_to_idx,
            idx_to_char=dataset.idx_to_char,
            vocab_size=dataset.vocab_size,
            device=device,
            args=args,
            length=100,
            quiet=True
        )
        self.assertIsInstance(generated, str)
        self.assertIn("Uthros", generated)

    def test_train_dry_run_extra_flags(self):
        parser = train.get_parser()
        # Test dry-run exception handling when reading unreadable file
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write("test content")
            invalid_file = f.name

        try:
            args = parser.parse_args([
                '--mode', 'train',
                '--infile', invalid_file,
                '--max_hours', '2.5',
                '--randomize_fields',
                '--randomize_mana',
                '--resume',
                '--dry-run'
            ])
            buf = io.StringIO()
            with patch('builtins.open', side_effect=PermissionError("Access denied")), patch('sys.stdout', buf):
                train.train(args)

            out = buf.getvalue()
            self.assertIn("Max Hours: 2.5", out)
            self.assertIn("Randomize Fields: Enabled", out)
            self.assertIn("Randomize Mana: Enabled", out)
            self.assertIn("Resume Training: Enabled", out)
        finally:
            if os.path.exists(invalid_file):
                os.remove(invalid_file)

    def test_train_full_execution(self):
        raw_data = "|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n|1Giant Growth|5Instant|9+3/+3|3{G}|\n\n"
        with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8') as f_in:
            f_in.write(raw_data)
            infile = f_in.name

        checkpoint_path = tempfile.NamedTemporaryFile(delete=False).name

        try:
            parser = train.get_parser()
            test_args = [
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint_path,
                '--epochs', '2',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--randomize_fields',
                '--randomize_mana',
                '--sample_epochs', '1',
                '--plot_loss',
                '--show_time'
            ]
            args = parser.parse_args(test_args)

            buf = io.StringIO()
            with patch('sys.stdout', buf), patch('matplotlib.pyplot.savefig') as mock_savefig:
                train.train(args)

            self.assertTrue(os.path.exists(checkpoint_path))
            out = buf.getvalue()
            self.assertIn("Epoch 1 average loss:", out)
            self.assertIn("--- Sampling after epoch 1 ---", out)
            mock_savefig.assert_called_once_with('loss_plot.png')

            # Test resume training
            resume_args = parser.parse_args([
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint_path,
                '--epochs', '3',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--resume'
            ])
            buf_resume = io.StringIO()
            with patch('sys.stdout', buf_resume):
                train.train(resume_args)

            out_resume = buf_resume.getvalue()
            self.assertIn("Resuming from epoch 2", out_resume)

            # Test sample mode execution
            sample_args = parser.parse_args([
                '--mode', 'sample',
                '--checkpoint', checkpoint_path,
                '--length', '50',
                '--temp', '0.8'
            ])
            buf_sample = io.StringIO()
            with patch('sys.stdout', buf_sample):
                train.sample(sample_args)

            out_sample = buf_sample.getvalue()
            self.assertGreater(len(out_sample), 0)

        finally:
            if os.path.exists(infile):
                os.remove(infile)
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)

    def test_train_time_limit(self):
        raw_data = "|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n|1Giant Growth|5Instant|9+3/+3|3{G}|\n\n"
        with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8') as f_in:
            f_in.write(raw_data)
            infile = f_in.name

        checkpoint_path = tempfile.NamedTemporaryFile(delete=False).name

        try:
            parser = train.get_parser()

            # Time limit before starting epoch 1
            args1 = parser.parse_args([
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint_path,
                '--epochs', '5',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--max_hours', '0.0000001'
            ])
            buf1 = io.StringIO()
            with patch('sys.stdout', buf1), patch('time.time', side_effect=[1000.0, 2000.0, 3000.0]):
                train.train(args1)

            self.assertIn("Time limit", buf1.getvalue())

            # Time limit during epoch batch iteration
            args2 = parser.parse_args([
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint_path,
                '--epochs', '5',
                '--batch_size', '1',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--max_hours', '0.0000001'
            ])
            buf2 = io.StringIO()
            # Simulate time passing inside batch loop
            with patch('sys.stdout', buf2), patch('time.time', side_effect=[100.0, 100.0, 100.0, 5000.0, 5000.0, 5000.0]):
                train.train(args2)

            self.assertIn("Saving and stopping", buf2.getvalue())
            self.assertTrue(os.path.exists(checkpoint_path))

        finally:
            if os.path.exists(infile):
                os.remove(infile)
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)

    def test_plot_loss_exception_handling(self):
        raw_data = "|1CardOne|3Creature|\n\n"
        with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8') as f_in:
            f_in.write(raw_data)
            infile = f_in.name

        checkpoint_path = tempfile.NamedTemporaryFile(delete=False).name

        try:
            parser = train.get_parser()
            args = parser.parse_args([
                '--mode', 'train',
                '--infile', infile,
                '--checkpoint', checkpoint_path,
                '--epochs', '1',
                '--batch_size', '1',
                '--seq_len', '5',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--plot_loss'
            ])

            buf = io.StringIO()
            with patch('sys.stdout', buf), patch('matplotlib.pyplot.savefig', side_effect=RuntimeError("Plotting failed")):
                train.train(args)

            self.assertIn("Could not plot loss: Plotting failed", buf.getvalue())

        finally:
            if os.path.exists(infile):
                os.remove(infile)
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)

if __name__ == '__main__':
    unittest.main()
