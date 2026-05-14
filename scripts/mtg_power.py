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
        description="Analyze the creature power balance and curve efficiency in a dataset. "
                    "Calculates a 'Power Rating' relative to CMC to identify outliers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The Power Rating is a heuristic that evaluates a creature's combat efficiency.
A "Vanilla" 2/2 for 2 mana has a rating of 1.0.

How the rating is calculated:
  - Base Score: Power + Toughness
  - Keyword Bonuses: (e.g., Flying +1.5, Trample +1.0, Indestructible +3.0)
  - Rating: Score / (2 * CMC)

Usage Examples:
  # Find the most efficient creatures in a specific set
  python3 scripts/mtg_power.py data/AllPrintings.json --set MOM --limit 10

  # Compare average creature efficiency across rarities
  python3 scripts/mtg_power.py data/AllPrintings.json --rarity common --rarity rare

  # Analyze generated cards for balance issues
  python3 scripts/mtg_power.py generated_cards.txt
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, MSE, or encoded text). Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save results.')
    io_group.add_argument('-n', '--limit', type=int, default=20,
                        help='Number of top outliers to show (Default: 20).')
    io_group.add_argument('-j', '--json', action='store_true', help='Output in JSON format.')
    io_group.add_argument('--csv', action='store_true', help='Output in CSV format.')

    # Group: Filtering Options
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append', help='Filter by search pattern.')
    filter_group.add_argument('--set', action='append', help='Filter by set code.')
    filter_group.add_argument('--rarity', action='append', help='Filter by rarity.')
    filter_group.add_argument('--colors', action='append', help='Filter by colors.')
    filter_group.add_argument('--cmc', action='append', help='Filter by CMC.')
    filter_group.add_argument('--mechanic', action='append', help='Filter by mechanic.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color.')

    args = parser.parse_args()

    # Smart Positional Handling
    if args.infile != '-' and not os.path.exists(args.infile):
        if not args.grep:
            args.grep = [args.infile]
            args.infile = '-'

    # Default Dataset
    if args.infile == '-' and sys.stdin.isatty():
        script_dir = os.path.dirname(os.path.realpath(__file__))
        default_data = os.path.join(script_dir, '../data/AllPrintings.json')
        if os.path.exists(default_data):
            args.infile = default_data

    # Format & Color
    use_color = args.color if args.color is not None else (sys.stdout.isatty() and not (args.json or args.csv))

    # Load data - strictly creatures
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose, grep=args.grep,
                                  sets=args.set, rarities=args.rarity, colors=args.colors,
                                  cmcs=args.cmc, mechanics=args.mechanic)

    creatures = [c for c in cards if c.is_creature]

    if not creatures:
        if not args.quiet:
            print("No creatures found matching criteria.", file=sys.stderr)
        return

    # Analysis
    sorted_creatures = sorted(creatures, key=lambda c: c.power_rating, reverse=True)

    rarity_stats = defaultdict(list)
    color_stats = defaultdict(list)
    for c in creatures:
        rarity_stats[c.rarity_name].append(c.power_rating)
        ci = c.color_identity if c.color_identity else 'A'
        if len(ci) > 1: ci = 'M'
        color_stats[ci].append(c.power_rating)

    # Output
    output_f = open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout

    try:
        if args.json:
            result = {
                'total_creatures': len(creatures),
                'by_rarity': {r: sum(s)/len(s) for r, s in rarity_stats.items()},
                'by_color': {c: sum(s)/len(s) for c, s in color_stats.items()},
                'top_outliers': [
                    {
                        'name': c.display_name,
                        'rating': c.power_rating,
                        'cost': c.cost.format(),
                        'pt': c._get_pt_display(include_parens=False)
                    } for c in sorted_creatures[:args.limit]
                ]
            }
            output_f.write(json.dumps(result, indent=2) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Name', 'Rating', 'Cost', 'P/T', 'Rarity'])
            for c in sorted_creatures[:args.limit]:
                writer.writerow([c.display_name, c.power_rating, c.cost.format(), c._get_pt_display(include_parens=False), c.rarity_name])
        else:
            utils.print_header("POWER BALANCE ANALYSIS", count=len(creatures), use_color=use_color, file=output_f)

            # Top Outliers Table
            print(f"  {datalib.color_line('Top Power Outliers (Most Efficient):', use_color)}", file=output_f)
            header = ["Name", "Rating", "Cost", "P/T", "Rarity"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]
            for c in sorted_creatures[:args.limit]:
                name = c.display_name
                if use_color: name = utils.colorize(name, c._get_ansi_color())

                rating = str(c.power_rating)
                if use_color:
                    color = utils.Ansi.BOLD + utils.Ansi.GREEN if c.power_rating > 1.2 else (utils.Ansi.RED if c.power_rating < 0.8 else "")
                    rating = utils.colorize(rating, color)

                rarity = c.rarity_name
                if use_color: rarity = utils.colorize(rarity, utils.Ansi.get_rarity_color(rarity))

                rows.append([name, rating, c.cost.format(ansi_color=use_color), c._get_pt_display(ansi_color=use_color, include_parens=False), rarity])

            datalib.add_separator_row(rows)
            datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'l', 'r', 'l']), indent=4, file=output_f)
            print("", file=output_f)

            # Rarity Averages
            print(f"  {datalib.color_line('Average Efficiency by Rarity:', use_color)}", file=output_f)
            r_header = ["Rarity", "Avg Rating", "Count"]
            if use_color: r_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in r_header]
            r_rows = [r_header]

            rarity_order = {'mythic': 0, 'rare': 1, 'uncommon': 2, 'common': 3, 'basic land': 4, 'special': 5}
            for r in sorted(rarity_stats.keys(), key=lambda x: rarity_order.get(x.lower(), 6)):
                avg = sum(rarity_stats[r]) / len(rarity_stats[r])
                label = r
                if use_color: label = utils.colorize(r, utils.Ansi.get_rarity_color(r))
                r_rows.append([label, f"{avg:.3f}", str(len(rarity_stats[r]))])

            datalib.add_separator_row(r_rows)
            datalib.printrows(datalib.padrows(r_rows, aligns=['l', 'r', 'r']), indent=4, file=output_f)

    finally:
        if args.outfile:
            output_f.close()

if __name__ == "__main__":
    main()
