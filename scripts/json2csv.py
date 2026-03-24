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
import utils

def main():
    parser = argparse.ArgumentParser(
        description="Converts MTG card data into the CSV format used by csv2json.py and the custom card template."
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', help='Input card data (JSON, JSONL, MSE, ZIP, or encoded text).')
    io_group.add_argument('outfile', help='Output CSV file path.')

    # Group: Filtering Options
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, type, and text). Use multiple times for AND logic.')
    filter_group.add_argument('--grep-name', action='append',
                        help='Only include cards whose name matches a search pattern.')
    filter_group.add_argument('--grep-type', action='append',
                        help='Only include cards whose typeline matches a search pattern.')
    filter_group.add_argument('--grep-text', action='append',
                        help='Only include cards whose rules text matches a search pattern.')
    filter_group.add_argument('--grep-cost', action='append',
                        help='Only include cards whose mana cost matches a search pattern.')
    filter_group.add_argument('--grep-pt', action='append',
                        help='Only include cards whose power/toughness matches a search pattern.')
    filter_group.add_argument('--grep-loyalty', action='append',
                        help='Only include cards whose loyalty/defense matches a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append',
                        help='Exclude cards matching a search pattern (checks name, type, and text). Use multiple times for OR logic.')
    filter_group.add_argument('--exclude-name', action='append',
                        help='Exclude cards whose name matches a search pattern.')
    filter_group.add_argument('--exclude-type', action='append',
                        help='Exclude cards whose typeline matches a search pattern.')
    filter_group.add_argument('--exclude-text', action='append',
                        help='Exclude cards whose rules text matches a search pattern.')
    filter_group.add_argument('--exclude-cost', action='append',
                        help='Exclude cards whose mana cost matches a search pattern.')
    filter_group.add_argument('--exclude-pt', action='append',
                        help='Exclude cards whose power/toughness matches a search pattern.')
    filter_group.add_argument('--exclude-loyalty', action='append',
                        help='Exclude cards whose loyalty/defense matches a search pattern.')
    filter_group.add_argument('--set', action='append',
                        help='Only include cards from specific sets (e.g., MOM, MRD). Supports multiple sets (OR logic).')
    filter_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities. Supports full names or shorthands (O, N, A, Y, I, L). Supports multiple rarities.")
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G, C/A). Supports multiple colors.")
    filter_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC values. Supports inequalities and ranges.')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow',
                        help='Only include cards with specific Power values. Supports inequalities and ranges.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou',
                        help='Only include cards with specific Toughness values. Supports inequalities and ranges.')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy',
                        help='Only include cards with specific Loyalty or Defense values. Supports inequalities and ranges.')
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanical features or keyword abilities. Supports multiple values.')
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')

    args = parser.parse_args()

    # Load cards using the standard loader
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, vgrep=args.vgrep,
                                  grep_name=args.grep_name, vgrep_name=args.exclude_name,
                                  grep_types=args.grep_type, vgrep_types=args.exclude_type,
                                  grep_text=args.grep_text, vgrep_text=args.exclude_text,
                                  grep_cost=args.grep_cost, vgrep_cost=args.exclude_cost,
                                  grep_pt=args.grep_pt, vgrep_pt=args.exclude_pt,
                                  grep_loyalty=args.grep_loyalty, vgrep_loyalty=args.exclude_loyalty,
                                  sets=args.set, rarities=args.rarity,
                                  colors=args.colors, cmcs=args.cmc,
                                  pows=args.pow, tous=args.tou, loys=args.loy,
                                  mechanics=args.mechanic,
                                  decklist_file=args.deck)

    if not cards:
        if args.verbose:
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

    # Also print a standard summary for consistency
    utils.print_operation_summary("CSV Export", len(cards), 0, quiet=not args.verbose)

if __name__ == '__main__':
    main()
