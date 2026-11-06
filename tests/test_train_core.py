import unittest
import sys
import os
import io
import tempfile
import runpy
from unittest.mock import patch
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import train

class TestTrainCore(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.sample_cards = (
            "|1Grizzly Bears|5Creature|82/2|3{1}{G}|\n\n"
            "|1Giant Growth|5Instant|9+3/+3|3{G}|\n\n"
            "|1Lightning Bolt|5Instant|9Deal 3 damage.|3{R}|\n\n"
            "|1Counterspell|5Instant|9Counter spell.|3{U}{U}|\n\n"
        )
        self.dataset_path = os.path.join(self.tmpdir.name, "sample_data.txt")
        with open(self.dataset_path, "w", encoding="utf-8") as f:
            f.write(self.sample_cards)
        self.checkpoint_path = os.path.join(self.tmpdir.name, "checkpoint.pt")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_augment_card_randomize_mana(self):
        card = "|1Alpha|5Creature|3{W^U^B}|Text.\n\n"
        with patch("random.shuffle", side_effect=lambda lst: lst.reverse()):
            augmented_mana = train.augment_card(card, randomize_fields=False, randomize_mana=True)
            self.assertIn("{B^U^W}", augmented_mana)

    def test_augment_card_randomize_fields(self):
        card = "|1Alpha|5Creature|3{W^U^B}|Text.\n\n"
        with patch("random.shuffle", side_effect=lambda lst: lst.reverse()):
            augmented_fields = train.augment_card(card, randomize_fields=True, randomize_mana=False)
            self.assertTrue(augmented_fields.endswith("Text.\n\n"))

    def test_augment_card_no_augmentation(self):
        card = "|1Alpha|5Creature|3{W^U^B}|Text.\n\n"
        unchanged = train.augment_card(card, randomize_fields=False, randomize_mana=False)
        self.assertEqual(unchanged, card)

    def test_char_dataset_initialization_and_indexing(self):
        dataset = train.CharDataset(self.sample_cards, seq_len=20, randomize_fields=True, randomize_mana=True)
        self.assertGreater(dataset.vocab_size, 0)
        self.assertEqual(len(dataset.cards), 4)
        self.assertGreater(len(dataset), 0)

        x, y = dataset[0]
        self.assertEqual(x.shape, torch.Size([20]))
        self.assertEqual(y.shape, torch.Size([20]))
        self.assertEqual(x.dtype, torch.long)
        self.assertEqual(y.dtype, torch.long)

        dataset.refresh_data()
        self.assertEqual(len(dataset.cards), 4)

    def test_char_rnn_forget_gate_bias_and_forward_pass(self):
        vocab_size = 30
        hidden_size = 16
        n_layers = 2
        model = train.CharRNN(vocab_size, hidden_size, n_layers, dropout=0.1)

        for name, param in model.rnn.named_parameters():
            if 'bias' in name:
                n = param.size(0)
                start, end = n // 4, n // 2
                self.assertTrue(torch.all(param.data[start:end] == 1.0))

        batch_size = 4
        seq_len = 10
        device = torch.device("cpu")
        x = torch.zeros((batch_size, seq_len), dtype=torch.long)
        hidden = model.init_hidden(batch_size, device)

        self.assertEqual(hidden[0].shape, (n_layers, batch_size, hidden_size))
        self.assertEqual(hidden[1].shape, (n_layers, batch_size, hidden_size))

        out, next_hidden = model(x, hidden)
        self.assertEqual(out.shape, (batch_size, seq_len, vocab_size))
        self.assertEqual(next_hidden[0].shape, (n_layers, batch_size, hidden_size))

    def test_generate_text_with_whisper_attributes(self):
        chars = sorted(list(set(self.sample_cards + "Uthroslegendarycreature")))
        char_to_idx = {c: i for i, c in enumerate(chars)}
        idx_to_char = {i: c for i, c in enumerate(chars)}
        vocab_size = len(chars)
        device = torch.device("cpu")

        model = train.CharRNN(vocab_size, hidden_size=16, n_layers=1, dropout=0.0)

        parser = train.get_parser()
        args = parser.parse_args([
            '--length', '100',
            '--temp', '0.8',
            '--start_text', '|',
            '--name', 'Uthros',
            '--supertypes', 'legendary',
            '--types', 'creature'
        ])

        text = train.generate_text(model, char_to_idx, idx_to_char, vocab_size, device, args, length=60, quiet=True)
        self.assertIsInstance(text, str)
        self.assertGreaterEqual(len(text), 60)
        self.assertTrue(text.startswith('|'))

    def test_train_model_and_save_checkpoint(self):
        parser = train.get_parser()
        train_args = parser.parse_args([
            '--mode', 'train',
            '--infile', self.dataset_path,
            '--checkpoint', self.checkpoint_path,
            '--epochs', '2',
            '--batch_size', '2',
            '--seq_len', '15',
            '--hidden_size', '16',
            '--n_layers', '1',
            '--lr', '0.01',
            '--dropout', '0.0',
            '--sample_epochs', '1',
            '--show_time',
            '--randomize_fields',
            '--randomize_mana'
        ])

        buf = io.StringIO()
        with patch('sys.stdout', buf):
            train.train(train_args)

        self.assertTrue(os.path.exists(self.checkpoint_path))
        output = buf.getvalue()
        self.assertIn("Epoch 1 average loss:", output)
        self.assertIn("Sampling after epoch 1", output)
        self.assertIn("Epoch 2 average loss:", output)

    def test_resume_training_from_checkpoint(self):
        self.test_train_model_and_save_checkpoint()
        parser = train.get_parser()
        resume_args = parser.parse_args([
            '--mode', 'train',
            '--infile', self.dataset_path,
            '--checkpoint', self.checkpoint_path,
            '--epochs', '3',
            '--batch_size', '2',
            '--seq_len', '15',
            '--hidden_size', '16',
            '--n_layers', '1',
            '--resume'
        ])
        buf_resume = io.StringIO()
        with patch('sys.stdout', buf_resume):
            train.train(resume_args)
        self.assertIn("Resuming from epoch 2", buf_resume.getvalue())

    def test_sample_generation_from_checkpoint(self):
        self.test_train_model_and_save_checkpoint()
        parser = train.get_parser()
        sample_args = parser.parse_args([
            '--mode', 'sample',
            '--checkpoint', self.checkpoint_path,
            '--length', '50',
            '--temp', '0.8',
            '--name', 'Bears'
        ])
        buf_sample = io.StringIO()
        with patch('sys.stdout', buf_sample):
            train.sample(sample_args)
        self.assertGreater(len(buf_sample.getvalue().strip()), 0)

    def test_train_time_limit_reached(self):
        parser = train.get_parser()
        train_args = parser.parse_args([
            '--mode', 'train',
            '--infile', self.dataset_path,
            '--checkpoint', self.checkpoint_path,
            '--epochs', '5',
            '--batch_size', '2',
            '--seq_len', '15',
            '--hidden_size', '16',
            '--n_layers', '1',
            '--max_hours', '0.001'
        ])

        time_counter = [0.0]
        def fake_time():
            time_counter[0] += 5.0
            return time_counter[0]

        buf = io.StringIO()
        with patch('time.time', side_effect=fake_time), patch('sys.stdout', buf):
            train.train(train_args)

        self.assertIn("Time limit", buf.getvalue())

    def test_train_time_limit_reached_during_batch(self):
        parser = train.get_parser()
        train_args = parser.parse_args([
            '--mode', 'train',
            '--infile', self.dataset_path,
            '--checkpoint', self.checkpoint_path,
            '--epochs', '2',
            '--batch_size', '2',
            '--seq_len', '15',
            '--hidden_size', '16',
            '--n_layers', '1',
            '--max_hours', '0.001'
        ])

        calls = [0]
        def fake_time_batch():
            calls[0] += 1
            if calls[0] >= 3:
                return 1000.0
            return 0.0

        buf = io.StringIO()
        with patch('time.time', side_effect=fake_time_batch), patch('sys.stdout', buf):
            train.train(train_args)

        self.assertIn("Time limit of 0.001 hours reached during epoch", buf.getvalue())
        self.assertTrue(os.path.exists(self.checkpoint_path))

    def test_plot_loss_handles_figure_saving(self):
        parser = train.get_parser()
        train_args = parser.parse_args([
            '--mode', 'train',
            '--infile', self.dataset_path,
            '--checkpoint', self.checkpoint_path,
            '--epochs', '1',
            '--batch_size', '2',
            '--seq_len', '15',
            '--hidden_size', '16',
            '--n_layers', '1',
            '--plot_loss'
        ])

        buf = io.StringIO()
        with patch('matplotlib.pyplot.savefig') as mock_savefig, patch('sys.stdout', buf):
            train.train(train_args)

        self.assertIn("Loss plot saved to loss_plot.png", buf.getvalue())
        mock_savefig.assert_called_with('loss_plot.png')

    def test_plot_loss_handles_import_exception(self):
        parser = train.get_parser()
        train_args = parser.parse_args([
            '--mode', 'train',
            '--infile', self.dataset_path,
            '--checkpoint', self.checkpoint_path,
            '--epochs', '1',
            '--batch_size', '2',
            '--seq_len', '15',
            '--hidden_size', '16',
            '--n_layers', '1',
            '--plot_loss'
        ])

        buf = io.StringIO()
        with patch.dict('sys.modules', {'matplotlib.pyplot': None}), patch('sys.stdout', buf):
            train.train(train_args)

        self.assertIn("Could not plot loss:", buf.getvalue())

    def test_cli_main_train_and_sample(self):
        train_cli_args = [
            'train.py',
            '--mode', 'train',
            '--infile', self.dataset_path,
            '--checkpoint', self.checkpoint_path,
            '--epochs', '1',
            '--batch_size', '2',
            '--seq_len', '15',
            '--hidden_size', '16',
            '--n_layers', '1'
        ]
        with patch.object(sys, 'argv', train_cli_args), patch('sys.stdout', io.StringIO()):
            runpy.run_module('train', run_name='__main__')

        self.assertTrue(os.path.exists(self.checkpoint_path))

        sample_cli_args = [
            'train.py',
            '--mode', 'sample',
            '--checkpoint', self.checkpoint_path,
            '--length', '20'
        ]
        buf = io.StringIO()
        with patch.object(sys, 'argv', sample_cli_args), patch('sys.stdout', buf):
            runpy.run_module('train', run_name='__main__')
        self.assertGreater(len(buf.getvalue().strip()), 0)

if __name__ == '__main__':
    unittest.main()
