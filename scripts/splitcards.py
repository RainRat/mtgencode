#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv

# Ensure lib is in path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import jdecode
import utils
import cardlib

def main():
    parser = argparse.ArgumentParser(description="Splits a card dataset into multiple files (e.g., train, validation, test).")

    # Input
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', help='Input card data (JSON, JSONL, CSV, MSE, or encoded text).')
    io_group.add_argument('--outputs', nargs='+', required=True,
                        help='Output filenames for each split (e.g., train.txt val.txt).')
    io_group.add_argument('--ratios', type=float, nargs='+', required=True,
                        help='Ratios for each split (e.g., 0.9 0.1). Must match the number of outputs and sum to 1.0.')

    # Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-f', '--format', choices=['text', 'json', 'jsonl', 'csv'], default='text',
                        help='Output format for the splits (default: text).')
    proc_group.add_argument('--shuffle', action='store_true', default=True,
                        help='Shuffle cards before splitting (default: True).')
    proc_group.add_argument('--no-shuffle', dest='shuffle', action='store_false',
                        help='Do not shuffle cards before splitting.')
    proc_group.add_argument('--seed', type=int, help='Seed for the random number generator.')
    proc_group.add_argument('-e', '--encoding', default='std', choices=utils.formats,
                        help="Encoding format if output is text (default: std).")

    # Logging
    log_group = parser.add_argument_group('Logging')
    log_group.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output.')
    log_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    args = parser.parse_args()

    if len(args.outputs) != len(args.ratios):
        print("Error: The number of outputs must match the number of ratios.", file=sys.stderr)
        sys.exit(1)

    if abs(sum(args.ratios) - 1.0) > 1e-6:
        if not args.quiet:
            print(f"Warning: Ratios sum to {sum(args.ratios):.4f}, normalizing to 1.0.", file=sys.stderr)
        total = sum(args.ratios)
        args.ratios = [r / total for r in args.ratios]

    # Load cards
    if not args.quiet:
        print(f"Loading cards from {args.infile}...", file=sys.stderr)

    # mtg_open_file handles format detection and basic filtering
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  shuffle=args.shuffle, seed=args.seed)

    total_cards = len(cards)
    if not args.quiet:
        print(f"Total cards loaded: {total_cards}", file=sys.stderr)

    if total_cards == 0:
        print("Error: No cards loaded.", file=sys.stderr)
        sys.exit(1)

    # Calculate split indices
    indices = []
    current = 0
    for i, ratio in enumerate(args.ratios):
        if i == len(args.ratios) - 1:
            # Last split gets the remainder to ensure we use all cards
            indices.append((current, total_cards))
        else:
            count = int(round(ratio * total_cards))
            indices.append((current, current + count))
            current += count

    # Write splits
    for i, (start, end) in enumerate(indices):
        outfile = args.outputs[i]
        split_cards = cards[start:end]

        if not args.quiet:
            print(f"Writing {len(split_cards)} cards to {outfile} (format: {args.format})...", file=sys.stderr)

        with open(outfile, 'w', encoding='utf8') as f:
            if args.format == 'json':
                json_data = [c.to_dict() for c in split_cards]
                json.dump(json_data, f, indent=2)
            elif args.format == 'jsonl':
                for c in split_cards:
                    f.write(json.dumps(c.to_dict()) + '\n')
            elif args.format == 'csv':
                fieldnames = ['name', 'mana_cost', 'type', 'subtypes', 'text', 'power', 'toughness', 'loyalty', 'rarity']
                writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
                writer.writeheader()
                for c in split_cards:
                    d = c.to_dict()
                    row = {
                        'name': d.get('name', ''),
                        'mana_cost': d.get('manaCost', ''),
                        'type': ' '.join(d.get('supertypes', []) + d.get('types', [])),
                        'subtypes': ' '.join(d.get('subtypes', [])),
                        'text': d.get('text', ''),
                        'power': d.get('power', ''),
                        'toughness': d.get('toughness', ''),
                        'loyalty': d.get('loyalty', d.get('defense', '')),
                        'rarity': d.get('rarity', ''),
                    }
                    writer.writerow(row)
            else: # text (encoded)
                # determine the encoding parameters
                # ENCODING_CONFIG from encode.py
                fmt_ordered = cardlib.fmt_ordered_default
                if args.encoding == 'named': fmt_ordered = cardlib.fmt_ordered_named
                elif args.encoding == 'noname': fmt_ordered = cardlib.fmt_ordered_noname
                elif args.encoding == 'old': fmt_ordered = cardlib.fmt_ordered_old
                elif args.encoding == 'norarity': fmt_ordered = cardlib.fmt_ordered_norarity

                for c in split_cards:
                    f.write(c.encode(fmt_ordered=fmt_ordered) + utils.cardsep)

    if not args.quiet:
        print("Dataset split successfully.", file=sys.stderr)

if __name__ == '__main__':
    main()
