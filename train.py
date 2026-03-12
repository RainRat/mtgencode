#!/usr/bin/env python3
import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import argparse
import re
import random
from tqdm import tqdm

def augment_mana(text):
    """
    Finds mana costs in { } and shuffles symbols separated by ^.
    Example: {3^W^U} -> {W^3^U}
    """
    def shuffle_mana(match):
        content = match.group(1)
        symbols = content.split('^')
        random.shuffle(symbols)
        return '{' + '^'.join(symbols) + '}'
    
    return re.sub(r'\{([^{}]+)\}', shuffle_mana, text)

def augment_card(card_text, randomize_fields, randomize_mana):
    """
    Splits card by | and shuffles fields (except the last terminal field).
    Also shuffles mana symbols within brackets if enabled.
    """
    if randomize_mana:
        card_text = augment_mana(card_text)
    
    if randomize_fields:
        fields = card_text.split('|')
        if len(fields) > 1:
            # The last field usually contains the body text and trailing newlines
            terminal = fields[-1]
            shufflable = fields[:-1]
            random.shuffle(shufflable)
            card_text = '|'.join(shufflable + [terminal])
            
    return card_text

class CharDataset(Dataset):
    def __init__(self, raw_data, seq_len, randomize_fields=False, randomize_mana=False):
        self.seq_len = seq_len
        self.randomize_fields = randomize_fields
        self.randomize_mana = randomize_mana
        
        # Split by double newline to identify discrete cards
        self.cards = [c.strip() + '\n\n' for c in raw_data.split('\n\n') if c.strip()]
        
        # Create consistent vocab from raw data
        self.chars = sorted(list(set(raw_data)))
        self.char_to_idx = {char: idx for idx, char in enumerate(self.chars)}
        self.idx_to_char = {idx: char for idx, char in enumerate(self.chars)}
        self.vocab_size = len(self.chars)
        
        self.data_str = ""
        self.refresh_data()

    def refresh_data(self):
        """Augments cards and reconstructs the data string for the epoch."""
        processed_cards = []
        for card in self.cards:
            processed_cards.append(augment_card(card, self.randomize_fields, self.randomize_mana))
        
        # Shuffle the order of cards in the dataset
        random.shuffle(processed_cards)
        self.data_str = "".join(processed_cards)

    def __len__(self):
        return len(self.data_str) - self.seq_len

    def __getitem__(self, idx):
        x_str = self.data_str[idx : idx + self.seq_len]
        y_str = self.data_str[idx + 1 : idx + self.seq_len + 1]
        
        x_idx = torch.tensor([self.char_to_idx.get(c, 0) for c in x_str], dtype=torch.long)
        y_idx = torch.tensor([self.char_to_idx.get(c, 0) for c in y_str], dtype=torch.long)
        return x_idx, y_idx

class CharRNN(nn.Module):
    def __init__(self, vocab_size, hidden_size, n_layers, dropout=0.2):
        super(CharRNN, self).__init__()
        self.hidden_size = hidden_size
        self.n_layers = n_layers
        self.encoder = nn.Embedding(vocab_size, hidden_size)
        self.rnn = nn.LSTM(hidden_size, hidden_size, n_layers, dropout=dropout, batch_first=True)
        self.decoder = nn.Linear(hidden_size, vocab_size)
        
        self._apply_forget_gate_bias()

    def _apply_forget_gate_bias(self):
        """
        Adds 1.0 to the forget gate bias (Jozefowicz et al., 2015).
        In PyTorch LSTM, bias is [b_ig | b_fg | b_gg | b_og].
        """
        for name, param in self.rnn.named_parameters():
            if 'bias' in name:
                n = param.size(0)
                # Forget gate is the second quarter of the bias vector
                start, end = n // 4, n // 2
                param.data[start:end].fill_(1.0)

    def forward(self, x, hidden):
        x = self.encoder(x)
        out, hidden = self.rnn(x, hidden)
        out = self.decoder(out)
        return out, hidden

    def init_hidden(self, batch_size, device):
        return (torch.zeros(self.n_layers, batch_size, self.hidden_size).to(device),
                torch.zeros(self.n_layers, batch_size, self.hidden_size).to(device))

def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    with open(args.infile, 'r', encoding='utf-8') as f:
        raw_data = f.read()

    dataset = CharDataset(raw_data, args.seq_len, args.randomize_fields, args.randomize_mana)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

    model = CharRNN(dataset.vocab_size, args.hidden_size, args.n_layers, args.dropout).to(device)
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    if args.resume and os.path.exists(args.checkpoint):
        checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        start_epoch = checkpoint['epoch']
        print(f"Resuming from epoch {start_epoch}")
    else:
        start_epoch = 0

    model.train()
    for epoch in range(start_epoch, args.epochs):
        dataset.refresh_data() # Re-augment for each epoch
        total_loss = 0
        pbar = tqdm(dataloader, desc=f"Epoch {epoch+1}/{args.epochs}")
        for x, y in pbar:
            x, y = x.to(device), y.to(device)
            batch_size = x.size(0)
            hidden = model.init_hidden(batch_size, device)
            
            optimizer.zero_grad()
            output, _ = model(x, hidden)
            loss = criterion(output.transpose(1, 2), y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            pbar.set_postfix(loss=loss.item())

        avg_loss = total_loss / len(dataloader)
        print(f"Epoch {epoch+1} average loss: {avg_loss:.4f}")
        
        torch.save({
            'epoch': epoch + 1,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'vocab': dataset.chars,
            'char_to_idx': dataset.char_to_idx,
            'idx_to_char': dataset.idx_to_char,
            'args': args
        }, args.checkpoint)

def sample(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    
    chars = checkpoint['vocab']
    char_to_idx = checkpoint['char_to_idx']
    idx_to_char = checkpoint['idx_to_char']
    vocab_size = len(chars)
    
    train_args = checkpoint['args']
    model = CharRNN(vocab_size, train_args.hidden_size, train_args.n_layers).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    # Mapping of field indices (based on | count) to CLI arguments
    whisper_map = {
        1: args.name,
        2: args.supertypes,
        3: args.types,
        4: args.loyalty,
        5: args.subtypes,
        6: args.rarity,
        7: args.powertoughness,
        8: args.manacost,
        9: args.bodytext_prepend,
        10: args.bodytext_append
    }

    start_text = args.start_text if args.start_text else "|"
    x = torch.tensor([[char_to_idx.get(c, 0) for c in start_text]], dtype=torch.long).to(device)
    hidden = model.init_hidden(1, device)
    
    generated = start_text
    field_count = start_text.count('|')
    
    with torch.no_grad():
        i = 0
        while i < args.length:
            output, hidden = model(x, hidden)
            
            # Sample next character
            p = torch.softmax(output[0, -1] / args.temp, dim=0).cpu().numpy()
            char_idx = np.random.choice(vocab_size, p=p)
            char = idx_to_char[char_idx]
            
            # Track field count
            if char == '|':
                field_count += 1
            elif char == '\n':
                field_count = 0
            
            generated += char
            x = torch.tensor([[char_idx]], dtype=torch.long).to(device)
            i += 1

            # Forcing attribute logic: if a field is set, insert the text
            if char == '|' and field_count in whisper_map and whisper_map[field_count]:
                whisper_text = whisper_map[field_count]
                for w_char in whisper_text:
                    w_idx = char_to_idx.get(w_char, 0)
                    # Update the model with the forced text to keep it on track
                    x = torch.tensor([[w_idx]], dtype=torch.long).to(device)
                    output, hidden = model(x, hidden)
                    generated += w_char
                    i += 1
                
    print(generated)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a neural network to design Magic: The Gathering cards.")

    # Group: General Options
    gen_group = parser.add_argument_group('General Options')
    gen_group.add_argument("--mode", choices=["train", "sample"], default="train",
                        help="Choose 'train' to teach the AI using your data, or 'sample' to create new cards.")
    gen_group.add_argument("--infile", type=str, default="data/output.txt",
                        help="Path to the encoded card file for training. Default: data/output.txt")
    gen_group.add_argument("--checkpoint", type=str, default="checkpoint.pt",
                        help="File path to save or load the model. Default: checkpoint.pt")

    # Group: Training Parameters
    train_group = parser.add_argument_group('Training Parameters')
    train_group.add_argument("--epochs", type=int, default=10,
                        help="How many times the AI processes the entire dataset. Default: 10")
    train_group.add_argument("--batch_size", type=int, default=64,
                        help="Number of card fragments processed at once. Default: 64")
    train_group.add_argument("--seq_len", type=int, default=100,
                        help="Number of characters the AI remembers when predicting the next one. Default: 100")
    train_group.add_argument("--hidden_size", type=int, default=256,
                        help="The size of the AI's internal memory. Default: 256")
    train_group.add_argument("--n_layers", type=int, default=2,
                        help="The number of processing layers in the AI model. Default: 2")
    train_group.add_argument("--lr", type=float, default=0.001,
                        help="How quickly the AI updates its knowledge. Default: 0.001")
    train_group.add_argument("--dropout", type=float, default=0.2,
                        help="The percentage of information ignored during training to prevent memorization. Default: 0.2")
    train_group.add_argument("--resume", action="store_true",
                        help="Continue training from the existing checkpoint.")
    train_group.add_argument("--randomize_fields", action="store_true",
                        help="Randomly reorder card parts (like cost and types) during training. This helps the AI learn better.")
    train_group.add_argument("--randomize_mana", action="store_true",
                        help="Shuffle mana symbols within costs during training.")

    # Group: Generation Options
    sample_group = parser.add_argument_group('Generation Options')
    sample_group.add_argument("--length", type=int, default=1000,
                        help="Number of characters to generate. Default: 1000")
    sample_group.add_argument("--temp", type=float, default=0.8,
                        help="Controls AI creativity. Higher values result in more unusual cards; lower values make it more predictable. Default: 0.8")
    sample_group.add_argument("--start_text", type=str, default="|",
                        help="The text to start generation with. Default: '|'")

    # Group: Forcing Card Attributes
    prime_group = parser.add_argument_group('Forcing Card Attributes',
                                          'These options force specific fields to contain your chosen text. '
                                          'Note: These depend on the legacy encoding format (-e old).')
    prime_group.add_argument("--name", type=str, help="Force a specific card name.")
    prime_group.add_argument("--supertypes", type=str, help="Force specific supertypes (e.g., 'Legendary').")
    prime_group.add_argument("--types", type=str, help="Force specific card types (e.g., 'Creature').")
    prime_group.add_argument("--loyalty", type=str, help="Force a specific starting loyalty or defense.")
    prime_group.add_argument("--subtypes", type=str, help="Force specific subtypes (e.g., 'Elf Warrior').")
    prime_group.add_argument("--rarity", type=str, help="Force a specific rarity marker.")
    prime_group.add_argument("--powertoughness", type=str, help="Force a specific Power/Toughness (e.g., '&^^/&^^').")
    prime_group.add_argument("--manacost", type=str, help="Force a specific mana cost (e.g., '{WW}').")
    prime_group.add_argument("--bodytext_prepend", type=str, help="Force the start of the rules text.")
    prime_group.add_argument("--bodytext_append", type=str, help="Force text to appear at the end of the rules text.")

    args = parser.parse_args()
    
    if args.mode == "train":
        train(args)
    else:
        sample(args)
