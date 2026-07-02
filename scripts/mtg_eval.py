#!/usr/bin/env python3
import sys
import os
import argparse
import json
import torch
from collections import OrderedDict

# Add lib and root directories to path
script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(script_dir, '../lib'))
sys.path.append(os.path.join(script_dir, '..'))

import utils
import cardlib
import datalib
import mtg_validate
from train import CharRNN, generate_text

def main():
    parser = argparse.ArgumentParser(
        description="Check how well an AI model works by creating and checking cards.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool checks AI model files. It creates a batch of cards,
checks if they follow the rules using scripts/mtg_validate.py, and calculates
how many cards followed the rules.

Usage Examples:
  # Evaluate a checkpoint by generating 100 cards
  python3 scripts/mtg_eval.py --checkpoint checkpoint.pt --count 100

  # Evaluate with higher creativity (temp)
  python3 scripts/mtg_eval.py --checkpoint checkpoint.pt --temp 1.0

  # Save details for cards that failed validation
  python3 scripts/mtg_eval.py --checkpoint checkpoint.pt --dump
"""
    )

    # Group: Model Options
    model_group = parser.add_argument_group('Model Options')
    model_group.add_argument('-c', '--checkpoint', default='checkpoint.pt',
                        help='Path to the model checkpoint file (Default: checkpoint.pt).')
    model_group.add_argument('-t', '--temp', type=float, default=0.8,
                        help='Creativity level for generation (Higher is more creative, Default: 0.8).')
    model_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')

    # Group: Evaluation Options
    eval_group = parser.add_argument_group('Evaluation Options')
    eval_group.add_argument('-n', '--count', type=int, default=50,
                        help='Number of cards to generate and validate (Default: 50).')
    eval_group.add_argument('-l', '--length', type=int, default=5000,
                        help='Character limit for the generation process (Default: 5000).')

    # Group: Output Options
    out_group = parser.add_argument_group('Output Options')
    out_group.add_argument('-j', '--json', action='store_true', help='Output results as structured JSON.')
    out_group.add_argument('-d', '--dump', action='store_true', help='Dump full text of failed cards.')
    out_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    out_group.add_argument('-q', '--quiet', action='store_true', help='Suppress progress bars.')

    # Color options
    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # Determine if we should use color
    use_color = args.color if args.color is not None else sys.stdout.isatty()

    if not os.path.exists(args.checkpoint):
        print(f"Error: Checkpoint file not found: {args.checkpoint}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Loading model from {args.checkpoint}...", file=sys.stderr)

    # Load Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    except Exception as e:
        print(f"Error loading checkpoint: {e}", file=sys.stderr)
        sys.exit(1)

    chars = checkpoint['vocab']
    char_to_idx = checkpoint['char_to_idx']
    idx_to_char = checkpoint['idx_to_char']
    vocab_size = len(chars)
    train_args = checkpoint['args']

    model = CharRNN(vocab_size, train_args.hidden_size, train_args.n_layers).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])

    if args.seed is not None:
        import numpy as np
        import random
        torch.manual_seed(args.seed)
        np.random.seed(args.seed)
        random.seed(args.seed)

    # Generation
    if not args.quiet:
        print(f"Generating {args.count} cards for evaluation...", file=sys.stderr)

    # We reuse generate_text but we need it to stop after args.count cards
    # generate_text takes args, but it uses args.length.
    # We'll wrap it to ensure we get enough cards.

    generated_raw = ""
    # Create a local args object for generate_text
    gen_args = argparse.Namespace(**vars(args))
    if not hasattr(gen_args, 'start_text'): gen_args.start_text = "|"
    # Initialize forcing attributes to None
    for attr in ['name', 'supertypes', 'types', 'loyalty', 'subtypes', 'rarity',
                 'powertoughness', 'manacost', 'bodytext_prepend', 'bodytext_append']:
        if not hasattr(gen_args, attr): setattr(gen_args, attr, None)

    # We use a large length to generate multiple cards
    generated_raw = generate_text(model, char_to_idx, idx_to_char, vocab_size, device, gen_args, length=args.length)

    # Split into cards
    card_sources = [c for c in generated_raw.split(utils.cardsep) if c.strip()]

    if len(card_sources) > args.count:
        card_sources = card_sources[:args.count]
    elif len(card_sources) < args.count:
        if not args.quiet:
            print(f"Warning: Only generated {len(card_sources)} cards (requested {args.count}). Increase --length.", file=sys.stderr)

    # Load as Card objects
    cards = []
    for src in card_sources:
        try:
            cards.append(cardlib.Card(src))
        except Exception:
            pass

    if not cards:
        print("Error: No cards were successfully generated/parsed.", file=sys.stderr)
        sys.exit(1)

    # Validation
    if not args.quiet:
        print(f"Validating generated cards...", file=sys.stderr)

    ((total_all, total_good, total_bad, total_uncovered),
     values) = mtg_validate.process_props(cards, dump=args.dump, quiet=args.quiet)

    accuracy = (total_good / total_all * 100) if total_all > 0 else 0

    # Output
    if args.json:
        result = {
            'checkpoint': args.checkpoint,
            'epoch': checkpoint.get('epoch', 'unknown'),
            'summary': {
                'total': total_all,
                'valid': total_good,
                'invalid': total_bad,
                'accuracy': accuracy
            },
            'properties': {p: {'total': v[0], 'good': v[1], 'bad': v[2], 'success_pct': (v[1]/v[0]*100 if v[0]>0 else 0)} for p, v in values.items()}
        }
        print(json.dumps(result, indent=2))
        return

    # Terminal Report
    utils.print_header("MODEL EVALUATION REPORT", use_color=use_color)
    print(f"  Checkpoint: {args.checkpoint}")
    print(f"  Epoch:      {checkpoint.get('epoch', 'unknown')}")
    print()

    # Accuracy Highlight
    acc_label = "Accuracy Score:"
    acc_val = f"{accuracy:.1f}%"
    if use_color:
        acc_label = utils.colorize(acc_label, utils.Ansi.BOLD + utils.Ansi.CYAN)
        color = utils.Ansi.BOLD + (utils.Ansi.GREEN if accuracy >= 90 else (utils.Ansi.YELLOW if accuracy >= 70 else utils.Ansi.RED))
        acc_val = utils.colorize(acc_val, color)

    print(f"  {acc_label} {acc_val}")
    print(f"  ({total_good} valid out of {total_all} generated cards)")
    print()

    # Breakdown Table
    header = ["Rule Check", "Checked", "Passed", "Failed", "Success %", "Chart"]
    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]
    for prop, (total, good, bad) in values.items():
        if total > 0:
            pct = (good / total * 100)
            bar = datalib.get_bar_chart(pct, use_color, color=utils.Ansi.BOLD + (utils.Ansi.GREEN if pct==100 else utils.Ansi.YELLOW))

            p_label = prop
            g_val = datalib.color_count(good, use_color)
            b_val = datalib.color_count(bad, use_color, utils.Ansi.BOLD + utils.Ansi.RED if bad > 0 else utils.Ansi.BOLD)

            if use_color:
                p_label = utils.colorize(prop, utils.Ansi.CYAN)

            rows.append([p_label, str(total), g_val, b_val, f"{pct:5.1f}%", bar])

    datalib.add_separator_row(rows)
    datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'r', 'r', 'r', 'l']), indent=2)
    print()

if __name__ == "__main__":
    main()
