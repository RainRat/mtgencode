#!/usr/bin/env python3
# Copyright 2026 Google LLC
import sys
import os
import argparse
import io
import torch
from contextlib import redirect_stdout

# Add lib and root directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
rootdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../')
sys.path.append(libdir)
sys.path.append(rootdir)

import utils
import cardlib
import mtg_validate
import train

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the quality of a trained MTG AI model checkpoint.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool generates a sample of cards from a model checkpoint and automatically
runs the validation suite to calculate a 'Mechanical Accuracy Score'.

Usage Examples:
  # Evaluate a specific checkpoint by generating 50 cards
  python3 scripts/mtg_eval.py checkpoint.pt --count 50

  # Evaluate and show details for cards that failed validation
  python3 scripts/mtg_eval.py checkpoint.pt --count 20 --dump
"""
    )

    parser.add_argument('checkpoint', help='Path to the model checkpoint (.pt file).')
    parser.add_argument('-c', '--count', type=int, default=100,
                        help='Number of cards to generate and evaluate (Default: 100).')
    parser.add_argument('-t', '--temp', type=float, default=0.8,
                        help='Sampling temperature (Default: 0.8).')
    parser.add_argument('-d', '--dump', action='store_true',
                        help='Show the text of cards that failed validation.')
    parser.add_argument('--seed', type=int, help='Random seed for sampling.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    args = parser.parse_args()

    if not os.path.exists(args.checkpoint):
        print(f"Error: Checkpoint file '{args.checkpoint}' not found.", file=sys.stderr)
        sys.exit(1)

    # 1. Load Model and Generate Cards
    if not args.quiet:
        print(f"Loading checkpoint and generating cards from {args.checkpoint}...", file=sys.stderr)

    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)

        chars = checkpoint['vocab']
        char_to_idx = checkpoint['char_to_idx']
        idx_to_char = checkpoint['idx_to_char']
        vocab_size = len(chars)

        train_args = checkpoint['args']
        model = train.CharRNN(vocab_size, train_args.hidden_size, train_args.n_layers).to(device)
        model.load_state_dict(checkpoint['model_state_dict'])

        # We need to construct a sample_args object for generate_text
        sample_args = argparse.Namespace(
            temp=args.temp,
            start_text="|",
            seed=args.seed,
            # Placeholder for forced attributes (all None)
            name=None, supertypes=None, types=None, loyalty=None, subtypes=None,
            rarity=None, powertoughness=None, manacost=None,
            bodytext_prepend=None, bodytext_append=None
        )

        # Increase heuristic length if count is high (approx 250 chars per card)
        gen_len = args.count * 250

        generated_text = train.generate_text(model, char_to_idx, idx_to_char, vocab_size, device, sample_args, length=gen_len)

    except Exception as e:
        print(f"Error during sampling: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Parse into Card objects
    raw_cards = generated_text.split(utils.cardsep)
    cards = []
    for rc in raw_cards:
        if rc.strip() and rc.count('|') >= 8: # Basic heuristic for a full card
            cards.append(cardlib.Card(rc))

    # Ensure we only evaluate the requested count
    cards = cards[:args.count]

    if not cards:
        print("Error: Could not parse any cards from the generated text. "
              "Check if your model was trained with the standard encoding.", file=sys.stderr)
        if args.verbose:
            print(f"Raw output sample:\n{generated_text[:500]}...", file=sys.stderr)
        sys.exit(1)

    # 3. Validate
    if not args.quiet:
        print(f"Validating {len(cards)} generated cards...", file=sys.stderr)

    ((total_all, total_good, total_bad, total_uncovered), values) = mtg_validate.process_props(
        cards, dump=args.dump, quiet=args.quiet
    )

    # 4. Report
    use_color = sys.stdout.isatty()

    utils.print_header("MODEL EVALUATION REPORT", use_color=use_color)
    print(f"  Checkpoint:  {args.checkpoint}")
    print(f"  Generated:   {total_all} cards")
    print(f"  Temperature: {args.temp}")
    print()

    # Accuracy Score
    accuracy = (total_good / total_all * 100) if total_all > 0 else 0
    score_color = utils.Ansi.BOLD
    if accuracy >= 80: score_color += utils.Ansi.GREEN
    elif accuracy >= 50: score_color += utils.Ansi.YELLOW
    else: score_color += utils.Ansi.RED

    score_str = f"Mechanical Accuracy Score: {accuracy:.1f}%"
    if use_color:
        score_str = utils.colorize(score_str, score_color)
    print(f"  {score_str}")
    print()

    # Property Breakdown Table
    import datalib
    rows = [[
        utils.colorize("Property", utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else "Property",
        "Success %",
        "Status"
    ]]

    for prop in mtg_validate.props:
        (total, good, bad) = values[prop]
        if total > 0:
            pct = (good / total * 100)
            bar = datalib.get_bar_chart(pct, use_color, color=utils.Ansi.CYAN)
            rows.append([prop, f"{pct:5.1f}%", bar])

    datalib.add_separator_row(rows)
    datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'l']), indent=4)
    print()

if __name__ == '__main__':
    main()
