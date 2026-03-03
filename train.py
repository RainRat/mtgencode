#!/usr/bin/env python3
import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import argparse
from tqdm import tqdm

class CharDataset(Dataset):
    def __init__(self, data, seq_len):
        self.data = data
        self.seq_len = seq_len
        self.chars = sorted(list(set(data)))
        self.char_to_idx = {char: idx for idx, char in enumerate(self.chars)}
        self.idx_to_char = {idx: char for idx, char in enumerate(self.chars)}
        self.vocab_size = len(self.chars)

    def __len__(self):
        return len(self.data) - self.seq_len

    def __getitem__(self, idx):
        x = self.data[idx : idx + self.seq_len]
        y = self.data[idx + 1 : idx + self.seq_len + 1]
        x_idx = torch.tensor([self.char_to_idx[char] for char in x], dtype=torch.long)
        y_idx = torch.tensor([self.char_to_idx[char] for char in y], dtype=torch.long)
        return x_idx, y_idx

class CharRNN(nn.Module):
    def __init__(self, vocab_size, hidden_size, n_layers, dropout=0.2):
        super(CharRNN, self).__init__()
        self.hidden_size = hidden_size
        self.n_layers = n_layers
        self.encoder = nn.Embedding(vocab_size, hidden_size)
        self.rnn = nn.LSTM(hidden_size, hidden_size, n_layers, dropout=dropout, batch_first=True)
        self.decoder = nn.Linear(hidden_size, vocab_size)

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
        data = f.read()

    dataset = CharDataset(data, args.seq_len)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

    model = CharRNN(dataset.vocab_size, args.hidden_size, args.n_layers, args.dropout).to(device)
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    if args.resume and os.path.exists(args.checkpoint):
        checkpoint = torch.load(args.checkpoint, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        start_epoch = checkpoint['epoch']
        print(f"Resuming from epoch {start_epoch}")
    else:
        start_epoch = 0

    model.train()
    for epoch in range(start_epoch, args.epochs):
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
    checkpoint = torch.load(args.checkpoint, map_location=device)
    
    chars = checkpoint['vocab']
    char_to_idx = checkpoint['char_to_idx']
    idx_to_char = checkpoint['idx_to_char']
    vocab_size = len(chars)
    
    train_args = checkpoint['args']
    model = CharRNN(vocab_size, train_args.hidden_size, train_args.n_layers).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    start_text = args.start_text if args.start_text else "|"
    x = torch.tensor([[char_to_idx[c] for c in start_text]], dtype=torch.long).to(device)
    hidden = model.init_hidden(1, device)
    
    generated = start_text
    
    with torch.no_grad():
        for _ in range(args.length):
            output, hidden = model(x, hidden)
            
            # Use temperature
            p = torch.softmax(output[0, -1] / args.temp, dim=0).cpu().numpy()
            char_idx = np.random.choice(vocab_size, p=p)
            
            char = idx_to_char[char_idx]
            generated += char
            x = torch.tensor([[char_idx]], dtype=torch.long).to(device)
            
    print(generated)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modern character-level RNN for MTG training.")
    parser.add_argument("--mode", choices=["train", "sample"], default="train")
    parser.add_argument("--infile", type=str, default="data/output.txt", help="Encoded card file for training")
    parser.add_argument("--checkpoint", type=str, default="checkpoint.pt", help="File to save/load model")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--seq_len", type=int, default=100)
    parser.add_argument("--hidden_size", type=int, default=256)
    parser.add_argument("--n_layers", type=int, default=2)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--resume", action="store_true")
    
    # Sample args
    parser.add_argument("--length", type=int, default=1000)
    parser.add_argument("--temp", type=float, default=0.8)
    parser.add_argument("--start_text", type=str, default="|")

    args = parser.parse_args()
    
    if args.mode == "train":
        train(args)
    else:
        sample(args)
