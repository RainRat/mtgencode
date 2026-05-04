#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv
from collections import defaultdict, Counter

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib
from cardlib import RECOGNIZED_MECHANICS

def get_color_category(card):
    """Categorizes a card into W, U, B, R, G, C, or M based on color identity."""
    identity = card.color_identity
    if not identity:
        return 'C'
    if len(identity) > 1:
        return 'M'
    return identity[0]

def main():
    parser = argparse.ArgumentParser(
        description="Analyze the mechanical color pie distribution in a dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool generates a matrix showing how mechanical keywords (Flying, Trample, etc.)
are distributed across the Magic color pie (Color Identity).

Color Categories:
  W, U, B, R, G: Monocolored
  C: Colorless (no color identity)
  M: Multicolored (2+ colors in identity)

Usage Examples:
  # Analyze color pie for a specific set
  python3 scripts/mtg_colorpie.py data/AllPrintings.json --set MOM

  # Find mechanical density in rare cards
  python3 scripts/mtg_colorpie.py data/AllPrintings.json --rarity rare

  # Filter by specific mechanics and output to JSON
  python3 scripts/mtg_colorpie.py data/AllPrintings.json --mechanic Flying --mechanic Lifelink --json
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, MSE, or encoded text). Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save results.')

    # Group: Output Format
    fmt_group = io_group.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate a formatted table (Default for terminal).')
    fmt_group.add_argument('--json', action='store_true', help='Generate a JSON file.')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file.')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append', help='Pattern match cards.')
    filter_group.add_argument('--set', action='append', help='Specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Specific rarities.')
    filter_group.add_argument('--colors', action='append', help='Specific colors (casting cost).')
    filter_group.add_argument('--identity', action='append', help='Specific color identities.')
    filter_group.add_argument('--cmc', action='append', help='Specific CMC.')
    filter_group.add_argument('--mechanic', action='append', help='Only include cards with specific mechanics.')
    filter_group.add_argument('--limit', type=int, default=0, help='Limit processing.')
    filter_group.add_argument('--sample', type=int, default=0, help='Random sample.')
    filter_group.add_argument('--shuffle', action='store_true', help='Shuffle the cards.')
    filter_group.add_argument('--seed', type=int, help='Seed for random generator.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # Smart Positional Argument Handling
    if args.infile != '-' and not os.path.exists(args.infile):
        if not args.grep:
            args.grep = [args.infile]
            args.infile = '-'
            if sys.stdin.isatty():
                default_data = 'data/AllPrintings.json'
                if os.path.exists(default_data):
                    args.infile = default_data

    # Load cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, sets=args.set, rarities=args.rarity,
                                  colors=args.colors, identities=args.identity,
                                  cmcs=args.cmc, mechanics=args.mechanic,
                                  shuffle=(args.sample > 0 or args.shuffle), seed=args.seed)

    if args.sample > 0:
        cards = cards[:args.sample]
    elif args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Data structures for analysis
    color_categories = ['W', 'U', 'B', 'R', 'G', 'C', 'M']
    color_totals = Counter()
    matrix = defaultdict(Counter) # mechanic -> color -> count
    mechanic_totals = Counter()

    for card in cards:
        category = get_color_category(card)
        color_totals[category] += 1

        mechanics = card.mechanics
        for m in mechanics:
            matrix[m][category] += 1
            mechanic_totals[m] += 1

    # Sorting mechanics
    # We show recognized mechanics first, then any others found, sorted by frequency
    all_found_mechanics = sorted(list(mechanic_totals.keys()), key=lambda x: mechanic_totals[x], reverse=True)
    ordered_mechanics = [m for m in RECOGNIZED_MECHANICS if m in all_found_mechanics]
    ordered_mechanics += [m for m in all_found_mechanics if m not in RECOGNIZED_MECHANICS]

    # Output detection
    if not (args.json or args.csv or args.table):
        if args.outfile:
            if args.outfile.endswith('.json'): args.json = True
            elif args.outfile.endswith('.csv'): args.csv = True
            else: args.table = True
        else:
            args.table = True

    use_color = args.color if args.color is not None else (sys.stdout.isatty() and not (args.json or args.csv))

    if args.json:
        results = {
            'total_cards': len(cards),
            'color_totals': dict(color_totals),
            'mechanic_totals': dict(mechanic_totals),
            'matrix': {m: dict(matrix[m]) for m in ordered_mechanics}
        }
        out = json.dumps(results, indent=2)
        if args.outfile:
            with open(args.outfile, 'w', encoding='utf-8') as f:
                f.write(out + '\n')
        else:
            print(out)
        return

    if args.csv:
        output_f = open(args.outfile, 'w', encoding='utf-8', newline='') if args.outfile else sys.stdout
        writer = csv.writer(output_f)
        writer.writerow(['Mechanic'] + color_categories + ['Total'])
        for m in ordered_mechanics:
            row = [m]
            for c in color_categories:
                row.append(matrix[m][c])
            row.append(mechanic_totals[m])
            writer.writerow(row)
        if args.outfile:
            output_f.close()
        return

    # Table Output
    output_f = open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout

    utils.print_header("MECHANICAL COLOR PI ANALYSIS", count=len(cards), use_color=use_color, file=output_f)

    print(f"  {datalib.color_line('Matrix: Mechanic vs Color Identity (Monocolored, Colorless, Multicolored)', use_color)}", file=output_f)
    print(f"  {datalib.color_line('Values are Frequency % (Density in that color category)', use_color)}\n", file=output_f)

    # Header Row
    header = ["Mechanic"] + color_categories + ["Total"]
    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]

    for m in ordered_mechanics:
        row_label = m
        if use_color:
            row_label = utils.colorize(m, utils.Ansi.CYAN)

        row = [row_label]
        for c in color_categories:
            count = matrix[m][c]
            total = color_totals[c]
            percent = (count / total * 100) if total > 0 else 0

            if percent == 0:
                val = "  - "
            else:
                val = f"{percent:4.1f}%"
                if use_color:
                    # Highlight high density
                    color = utils.Ansi.get_color_color(c) if c in 'WUBRG' else (utils.Ansi.BOLD if c == 'C' else utils.Ansi.YELLOW)
                    if percent >= 20:
                        val = utils.colorize(val, utils.Ansi.BOLD + color)
                    elif percent >= 5:
                        val = utils.colorize(val, color)
            row.append(val)

        # Row Total
        total_percent = (mechanic_totals[m] / len(cards) * 100)
        total_str = f"{total_percent:4.1f}%"
        if use_color:
            total_str = utils.colorize(total_str, utils.Ansi.BOLD + utils.Ansi.WHITE)
        row.append(total_str)
        rows.append(row)

    # Column Totals (Card Counts)
    datalib.add_separator_row(rows)
    footer = ["CARD COUNT"]
    for c in color_categories:
        count = str(color_totals[c])
        if use_color:
            count = utils.colorize(count, utils.Ansi.get_color_color(c) if c in 'WUBRG' else utils.Ansi.BOLD)
        footer.append(count)
    footer.append(str(len(cards)))
    rows.append(footer)

    datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r'] * (len(header) - 1)), indent=4, file=output_f)
    print("", file=output_f)

    if not args.quiet:
        utils.print_operation_summary("Color Pie Analysis", len(cards), 0, quiet=args.quiet)

    if args.outfile:
        output_f.close()

if __name__ == "__main__":
    main()
