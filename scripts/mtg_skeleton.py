#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv
from collections import defaultdict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib

def main():
    parser = argparse.ArgumentParser(
        description="Generate a 'Design Skeleton' (Set Skeleton) for a card dataset, bucketing by type and CMC.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The Design Skeleton helps you understand the mechanical curve and balance of your set.
It displays a 2D grid of card types (Creature, Instant, etc.) vs. mana costs (CMC 0-7+).

Usage Examples:
  # Generate skeleton for a dataset
  python3 scripts/mtg_skeleton.py data/AllPrintings.json --set MOM

  # Analyze the curve of a specific color identity
  python3 scripts/mtg_skeleton.py data/AllPrintings.json --identity "W"
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (MTGJSON, Scryfall, CSV, XML, MSE, or encoded text) or directory. '
                             'If this is not a valid path, it is treated as a search pattern (--grep). '
                             'Defaults to stdin (-). If stdin is a TTY, AllPrintings.json is used if available.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the results. If not provided, results print to the console.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate a formatted table (Default for terminal).')
    fmt_group.add_argument('-j', '--json', action='store_true', help='Generate a JSON file (Auto-detected for .json).')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file (Auto-detected for .csv).')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Randomize the order of cards before analyzing.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards (shorthand for --shuffle --limit N).')
    proc_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')

    # Group: Filtering Options
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for AND logic.')
    filter_group.add_argument('--vgrep', '--exclude', action='append', dest='vgrep',
                        help='Skip cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for OR logic.')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
    filter_group.add_argument('--colors', action='append', help='Only include cards of specific colors.')
    filter_group.add_argument('--identity', action='append', help='Only include cards with specific color identities.')
    filter_group.add_argument('--cmc', action='append', help='Only include cards with specific CMC values.')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow', help='Only include cards with specific Power values.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou', help='Only include cards with specific Toughness values.')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy', help='Only include cards with specific Loyalty or Defense values.')
    filter_group.add_argument('--mechanic', action='append', help='Only include cards with specific mechanical features.')
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck', help='Filter cards using a standard MTG decklist file.')
    filter_group.add_argument('--booster', type=int, default=0, help='Simulate opening N booster packs.')
    filter_group.add_argument('--box', type=int, default=0, help='Simulate opening N booster boxes.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # UX Improvement: Smart positional argument handling
    # If the user provides an infile that doesn't exist, but it might be a search query,
    # we treat it as such and default the input to stdin/AllPrintings.json.
    if args.infile and args.infile != '-' and not os.path.exists(args.infile):
        # If there are 2 positional arguments and the first isn't a file but the second is, swap them.
        if args.outfile and os.path.exists(args.outfile):
            query = args.infile
            args.infile = args.outfile
            args.outfile = None
            if not args.grep:
                args.grep = [query]
            else:
                args.grep.append(query)
        # If only one argument was provided (or both don't exist), treat it as a query.
        else:
            if not args.grep:
                args.grep = [args.infile]
            else:
                args.grep.append(args.infile)
            args.infile = '-'

    # UX Improvement: Default Dataset
    # If we are reading from stdin but it's an interactive terminal, use AllPrintings.json if it exists.
    if args.infile == '-' and sys.stdin.isatty():
        script_dir = os.path.dirname(os.path.realpath(__file__))
        default_data = os.path.join(script_dir, '../data/AllPrintings.json')
        if os.path.exists(default_data):
            args.infile = default_data
            if not args.quiet:
                print(f"Notice: Using default dataset: {args.infile}", file=sys.stderr)
        elif os.path.exists('data/AllPrintings.json'):
            args.infile = 'data/AllPrintings.json'
            if not args.quiet:
                print(f"Notice: Using default dataset: {args.infile}", file=sys.stderr)

    if args.sample > 0:
        args.shuffle = True
        args.limit = args.sample

    # Format detection
    if not (args.json or args.csv or args.table):
        if args.outfile:
            if args.outfile.endswith('.json'): args.json = True
            elif args.outfile.endswith('.csv'): args.csv = True
            else: args.table = True
        else:
            args.table = True

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and not (args.json or args.csv) and sys.stdout.isatty():
        use_color = True

    # Load and filter cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, vgrep=args.vgrep,
                                  sets=args.set, rarities=args.rarity,
                                  colors=args.colors, cmcs=args.cmc,
                                  pows=args.pow, tous=args.tou, loys=args.loy,
                                  mechanics=args.mechanic,
                                  identities=args.identity,
                                  decklist_file=args.deck,
                                  booster=args.booster, box=args.box,
                                  shuffle=args.shuffle, seed=args.seed)

    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Define types and CMC buckets
    tracked_types = ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land", "Battle"]
    cmc_buckets = [0, 1, 2, 3, 4, 5, 6, 7] # 7 means 7+

    # Matrix: matrix[type][cmc] = count
    matrix = defaultdict(lambda: defaultdict(int))

    for card in cards:
        # Determine CMC bucket
        cmc = int(card.cost.cmc)
        if cmc > 7:
            cmc = 7
        elif cmc < 0:
            cmc = 0

        # A card can have multiple types, but we usually want to bucket it by primary
        # We'll check in order of priority or just add to all that match?
        # Standard design skeletons usually bucket by primary type.
        # Let's count it for every type it has that is in our tracked list.
        found_any = False
        for t in tracked_types:
            if card._has_type(t):
                matrix[t][cmc] += 1
                found_any = True

        if not found_any:
            matrix["Other"][cmc] += 1

    all_rows = tracked_types + (["Other"] if any(matrix["Other"].values()) else [])
    grand_total = 0
    column_totals = defaultdict(int)

    # Prepare results object for JSON/CSV
    results = {
        'total_cards': len(cards),
        'skeleton': []
    }

    for t in all_rows:
        row_total = 0
        row_data = {'type': t, 'buckets': {}}
        for cmc in cmc_buckets:
            count = matrix[t][cmc]
            row_total += count
            column_totals[cmc] += count
            row_data['buckets'][str(cmc) if cmc < 7 else "7+"] = count

        row_data['total'] = row_total
        grand_total += row_total
        results['skeleton'].append(row_data)

    results['column_totals'] = {str(cmc) if cmc < 7 else "7+": column_totals[cmc] for cmc in cmc_buckets}
    results['grand_total'] = grand_total

    # Output
    output_f = sys.stdout
    if args.outfile:
        if args.verbose:
            print(f"Writing results to: {args.outfile}", file=sys.stderr)
        output_f = open(args.outfile, 'w', encoding='utf-8')

    try:
        if args.json:
            output_f.write(json.dumps(results, indent=2) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            header = ["Type"] + [str(c) if c < 7 else "7+" for c in cmc_buckets] + ["Total"]
            writer.writerow(header)
            for row in results['skeleton']:
                line = [row['type']] + [row['buckets'][str(c) if c < 7 else "7+"] for c in cmc_buckets] + [row['total']]
                writer.writerow(line)
            totals_line = ["TOTAL"] + [column_totals[cmc] for cmc in cmc_buckets] + [grand_total]
            writer.writerow(totals_line)
        elif not args.quiet:
            # Table Output
            header = ["Type / CMC"] + [str(c) if c < 7 else "7+" for c in cmc_buckets] + ["Total"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]
            for row_data in results['skeleton']:
                t = row_data['type']
                row_label = t
                if use_color:
                    color = utils.Ansi.CYAN
                    if t == "Creature": color = utils.Ansi.GREEN
                    elif t == "Land": color = utils.Ansi.BOLD
                    row_label = utils.colorize(t, color)

                row = [row_label]
                for cmc in cmc_buckets:
                    count = row_data['buckets'][str(cmc) if cmc < 7 else "7+"]
                    row.append(datalib.color_count(count, use_color) if count > 0 else "-")

                row.append(utils.colorize(str(row_data['total']), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(row_data['total']))
                rows.append(row)

            # Add separators
            datalib.add_separator_row(rows, index=1)
            datalib.add_separator_row(rows, index=len(rows))

            # Add totals row
            totals_label = "TOTAL"
            if use_color:
                totals_label = utils.colorize(totals_label, utils.Ansi.BOLD + utils.Ansi.YELLOW)

            totals_row = [totals_label]
            for cmc in cmc_buckets:
                count = column_totals[cmc]
                totals_row.append(utils.colorize(str(count), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(count))

            totals_row.append(utils.colorize(str(grand_total), utils.Ansi.BOLD + utils.Ansi.WHITE + utils.Ansi.UNDERLINE) if use_color else str(grand_total))
            rows.append(totals_row)

            # Print
            print(utils.colorize("DESIGN SKELETON", utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE) if use_color else "=== DESIGN SKELETON ===", file=output_f)
            datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r'] * (len(header) - 1)), indent=2, file=output_f)

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Skeleton Analysis", grand_total, 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
