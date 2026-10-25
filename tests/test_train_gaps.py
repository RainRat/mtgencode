import unittest
import sys
import os
import io
import tempfile
import torch
import numpy as np
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import train

class TestTrainGaps(unittest.TestCase):

    def test_augment_card_randomize_mana_and_fields(self):
        card_text = "|FieldA|FieldB|{W^U^B}|\n\n"
        augmented = train.augment_card(card_text, randomize_fields=True, randomize_mana=True)
        self.assertTrue(augmented.endswith("|\n\n"))

    def test_augment_card_no_randomization(self):
        card_text = "|Name|Type|{1}{G}|\n\n"
        augmented = train.augment_card(card_text, randomize_fields=False, randomize_mana=False)
        self.assertEqual(augmented, card_text)

    def test_char_dataset_initialization_and_indexing(self):
        raw_data = "|Grizzly Bears|Creature|2/2|{1}{G}|\n\n|Giant Growth|Instant|+3/+3|{G}|\n\n"
        dataset = train.CharDataset(raw_data, seq_len=10, randomize_fields=False, randomize_mana=False)

        self.assertGreater(dataset.vocab_size, 0)
        self.assertEqual(len(dataset), len(dataset.data_str) - 10)

        x, y = dataset[0]
        self.assertEqual(x.shape, (10,))
        self.assertEqual(y.shape, (10,))
        self.assertEqual(x.dtype, torch.long)
        self.assertEqual(y.dtype, torch.long)

    def test_char_dataset_unknown_char_fallback(self):
        raw_data = "ABC\n\nDEF\n\n"
        dataset = train.CharDataset(raw_data, seq_len=3)
        dataset.data_str = "A?B"
        x, y = dataset[0]
        self.assertEqual(x[1].item(), 0)

    def test_char_rnn_module_forward_and_hidden(self):
        vocab_size = 20
        hidden_size = 16
        n_layers = 2
        batch_size = 4
        seq_len = 10

        device = torch.device("cpu")
        model = train.CharRNN(vocab_size, hidden_size, n_layers, dropout=0.0).to(device)
        hidden = model.init_hidden(batch_size, device)

        self.assertEqual(hidden[0].shape, (n_layers, batch_size, hidden_size))
        self.assertEqual(hidden[1].shape, (n_layers, batch_size, hidden_size))

        x = torch.zeros((batch_size, seq_len), dtype=torch.long)
        output, new_hidden = model(x, hidden)

        self.assertEqual(output.shape, (batch_size, seq_len, vocab_size))
        self.assertEqual(new_hidden[0].shape, (n_layers, batch_size, hidden_size))

    def test_generate_text_with_forcing_attributes(self):
        parser = train.get_parser()
        args = parser.parse_args([
            '--mode', 'sample',
            '--length', '20',
            '--temp', '0.8',
            '--start_text', '|',
            '--supertypes', 'Legendary'
        ])

        vocab = sorted(list(" |Legendary\n0123456789"))
        char_to_idx = {c: i for i, c in enumerate(vocab)}
        idx_to_char = {i: c for i, c in enumerate(vocab)}
        vocab_size = len(vocab)
        device = torch.device("cpu")

        model = train.CharRNN(vocab_size, hidden_size=8, n_layers=1, dropout=0.0).to(device)

        # Force the model to generate '|' so field_count becomes 2, triggering whisper_map[2]
        with patch('numpy.random.choice', return_value=char_to_idx['|']):
            text = train.generate_text(model, char_to_idx, idx_to_char, vocab_size, device, args, length=30, quiet=True)

        self.assertIn("Legendary", text)

    def test_train_loop_execution_and_checkpoint(self):
        with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as dataset_file, \
             tempfile.NamedTemporaryFile('w+', delete=False, suffix='.pt') as cp_file:
            dataset_file.write("|Grizzly Bears|Creature|2/2|{1}{G}|\n\n" * 10)
            dataset_path = dataset_file.name
            cp_path = cp_file.name

        try:
            parser = train.get_parser()
            args = parser.parse_args([
                '--mode', 'train',
                '--infile', dataset_path,
                '--checkpoint', cp_path,
                '--epochs', '1',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--sample_epochs', '1',
                '--show_time'
            ])

            buf = io.StringIO()
            with patch('sys.stdout', buf):
                train.train(args)

            self.assertTrue(os.path.exists(cp_path))
            checkpoint = torch.load(cp_path, map_location='cpu', weights_only=False)
            self.assertEqual(checkpoint['epoch'], 1)
            self.assertIn('model_state_dict', checkpoint)
            self.assertIn('optimizer_state_dict', checkpoint)
        finally:
            if os.path.exists(dataset_path):
                os.remove(dataset_path)
            if os.path.exists(cp_path):
                os.remove(cp_path)

    def test_train_resume_and_time_limit(self):
        with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as dataset_file, \
             tempfile.NamedTemporaryFile('w+', delete=False, suffix='.pt') as cp_file:
            dataset_file.write("|Grizzly Bears|Creature|2/2|{1}{G}|\n\n" * 10)
            dataset_path = dataset_file.name
            cp_path = cp_file.name

        try:
            parser = train.get_parser()
            args1 = parser.parse_args([
                '--mode', 'train',
                '--infile', dataset_path,
                '--checkpoint', cp_path,
                '--epochs', '1',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1'
            ])

            with patch('sys.stdout', io.StringIO()):
                train.train(args1)

            args2 = parser.parse_args([
                '--mode', 'train',
                '--infile', dataset_path,
                '--checkpoint', cp_path,
                '--epochs', '2',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--resume',
                '--max_hours', '0.0000001'
            ])

            buf = io.StringIO()
            with patch('sys.stdout', buf):
                train.train(args2)

            out = buf.getvalue()
            self.assertIn("Resuming from epoch 1", out)
            self.assertIn("Time limit", out)
        finally:
            if os.path.exists(dataset_path):
                os.remove(dataset_path)
            if os.path.exists(cp_path):
                os.remove(cp_path)

    def test_train_plot_loss_option(self):
        with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as dataset_file, \
             tempfile.NamedTemporaryFile('w+', delete=False, suffix='.pt') as cp_file:
            dataset_file.write("|Grizzly Bears|Creature|2/2|{1}{G}|\n\n" * 5)
            dataset_path = dataset_file.name
            cp_path = cp_file.name

        plot_path = 'loss_plot.png'
        if os.path.exists(plot_path):
            os.remove(plot_path)

        try:
            parser = train.get_parser()
            args = parser.parse_args([
                '--mode', 'train',
                '--infile', dataset_path,
                '--checkpoint', cp_path,
                '--epochs', '1',
                '--batch_size', '2',
                '--seq_len', '10',
                '--hidden_size', '16',
                '--n_layers', '1',
                '--plot_loss'
            ])

            with patch('sys.stdout', io.StringIO()):
                train.train(args)

            if os.path.exists(plot_path):
                os.remove(plot_path)
        finally:
            if os.path.exists(dataset_path):
                os.remove(dataset_path)
            if os.path.exists(cp_path):
                os.remove(cp_path)

    def test_sample_from_checkpoint(self):
        with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as dataset_file, \
             tempfile.NamedTemporaryFile('w+', delete=False, suffix='.pt') as cp_file:
            dataset_file.write("|Grizzly Bears|Creature|2/2|{1}{G}|\n\n" * 5)
            dataset_path = dataset_file.name
            cp_path = cp_file.name

        try:
            parser = train.get_parser()
            train_args = parser.parse_args([
                '--mode', 'train',
                '--infile', dataset_path,
                '--checkpoint', cp_path,
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
                '--checkpoint', cp_path,
                '--length', '20',
                '--temp', '0.8'
            ])

            buf = io.StringIO()
            with patch('sys.stdout', buf):
                train.sample(sample_args)

            generated = buf.getvalue()
            self.assertGreater(len(generated), 0)
        finally:
            if os.path.exists(dataset_path):
                os.remove(dataset_path)
            if os.path.exists(cp_path):
                os.remove(cp_path)

if __name__ == '__main__':
    unittest.main()
