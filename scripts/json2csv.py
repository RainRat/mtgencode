#!/usr/bin/env python3
import sys
import os
import argparse
import csv

# Ensure lib is in path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import jdecode
import cardlib

def main():
    parser = argparse.ArgumentParser(
        description="Converts MTG card data into the CSV format used by csv2json.py and the custom card template."
    )
    parser.add_argument('infile', help='Input card data (JSON, JSONL, MSE, ZIP, or encoded text)')
    parser.add_argument('outfile', help='Output CSV file path')
    parser.add_argument('--set', action='append', help='Filter by set code (e.g., MOM)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    # Load cards using the standard loader
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose, sets=args.set)

    if not cards:
        print("No cards found matching the criteria.", file=sys.stderr)
        return

    with open(args.outfile, 'w', encoding='utf8', newline='') as f:
        writer = csv.writer(f)
        # Header row compatible with csv2json.py
        writer.writerow(['name', 'mana_cost', 'type', 'subtypes', 'text', 'pt', 'rarity'])

        for card in cards:
            # Reconstruct the fields in the exact order csv2json.py expects

            # P/T or Loyalty/Defense
            pt_val = card._get_pt_display(include_parens=False)
            if not pt_val:
                pt_val = card._get_loyalty_display(include_parens=False)

            # Rarity shorthand
            rarity_short = cardlib.RARITY_MAP.get(card.rarity, card.rarity)

            row = [
                card.name,
                card.cost.format(),
                ' '.join(card.supertypes + card.types),
                ' '.join(card.subtypes),
                card.get_text(force_unpass=True),
                pt_val,
                rarity_short
            ]
            writer.writerow(row)

    if args.verbose:
        print(f"Successfully exported {len(cards)} cards to {args.outfile}")

if __name__ == '__main__':
    main()
