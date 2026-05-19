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

def get_cost_metrics(card):
    """
    Analyzes the mana cost of a card face.
    Returns:
        - cmc: Mana Value
        - colored_pips: Total number of colored mana symbols
        - intensity: Ratio of colored pips to CMC (0.0 to 1.0)
        - max_commitment: Maximum number of pips of a single color
    """
    cmc = card.cost.cmc

    # We count how many symbols in the sequence are colored symbols
    colored_pips = 0
    # For commitment, we need to handle hybrid correctly.
    # Standard commitment (e.g. for devotion) counts a {W/U} as 1 W and 1 U.
    color_pips = Counter()

    for encoded_sym in card.cost.sequence:
        if encoded_sym == utils.mana_unary_counter:
            continue
        # sequence contains encoded symbols (like 'WW', 'UU', 'WU')
        sym = utils.mana_symall_decode.get(encoded_sym)
        if not sym or sym == utils.mana_X or sym == utils.mana_S or sym == utils.mana_E:
            continue

        # Check if it contains any WUBRG color
        is_colored = False
        for char in sym:
            if char in 'WUBRG':
                color_pips[char] += 1
                is_colored = True

        if is_colored:
            colored_pips += 1

    intensity = colored_pips / max(1, cmc)
    max_commitment = max(color_pips.values()) if color_pips else 0

    # Recursive for b-sides?
    # In this toolkit, we usually focus on the front face for curve/stats,
    # but we can provide the metrics for the front face here and aggregate in main.

    return cmc, colored_pips, intensity, max_commitment

def main():
    parser = argparse.ArgumentParser(
        description="Analyze mana cost intensity and colored pip distribution in a dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool evaluates the "mana intensity" of cards by analyzing colored pips relative to CMC.
It identifies 'pip-heavy' outliers and buckets cards by their color commitment.

Usage Examples:
  # Analyze cost intensity for a specific set
  python3 scripts/mtg_costs.py data/AllPrintings.json --set MOM

  # Find the most mana-intensive cards in a dataset
  python3 scripts/mtg_costs.py data/AllPrintings.json --limit 20

  # Analyze generated cards for cost balance
  python3 scripts/mtg_costs.py generated_cards.txt

  # Quickly analyze costs using the default dataset
  python3 scripts/mtg_costs.py "Legendary Creature"
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). Defaults to stdin (-). '
                             'If stdin is a terminal, AllPrintings.json is used if available.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save results. If not provided, results print to the console.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate a formatted table (Default).')
    fmt_group.add_argument('-j', '--json', action='store_true', help='Generate a structured JSON file.')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file.')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append', help='Only include cards matching a search pattern.')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
    filter_group.add_argument('--colors', action='append', help='Only include cards of specific colors.')
    filter_group.add_argument('--cmc', action='append', help='Only include cards with specific CMC values.')
    filter_group.add_argument('--mechanic', action='append', help='Only include cards with specific mechanics.')
    filter_group.add_argument('-n', '--limit', type=int, default=0, help='Only process the first N cards.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # Smart Positional Argument Handling
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

    # Format detection
    if not (args.json or args.csv or args.table):
        if args.outfile:
            if args.outfile.endswith('.json'): args.json = True
            elif args.outfile.endswith('.csv'): args.csv = True
            else: args.table = True
        else:
            args.table = True

    # Color detection
    use_color = args.color if args.color is not None else (sys.stdout.isatty() and not (args.json or args.csv))

    # Load data
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose, grep=args.grep,
                                  sets=args.set, rarities=args.rarity, colors=args.colors,
                                  cmcs=args.cmc, mechanics=args.mechanic)
    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching criteria.", file=sys.stderr)
        return

    # Analysis
    intensity_sum = 0
    commitment_buckets = Counter()
    outliers = []

    for card in cards:
        cmc, pips, intensity, commitment = get_cost_metrics(card)
        intensity_sum += intensity

        # Bucketing commitment
        if commitment == 0: bucket = "None"
        elif commitment == 1: bucket = "Single"
        elif commitment == 2: bucket = "Double"
        elif commitment == 3: bucket = "Triple"
        else: bucket = "Heavy"
        commitment_buckets[bucket] += 1

        # Outlier identification
        if intensity >= 0.7 or commitment >= 3:
            outliers.append({
                'name': card.display_name,
                'cost': card.cost.format(),
                'intensity': intensity,
                'commitment': commitment,
                'card': card
            })

    # Sort outliers by intensity descending
    outliers.sort(key=lambda x: (x['intensity'], x['commitment']), reverse=True)
    avg_intensity = intensity_sum / len(cards)

    # Prepare Results
    results = {
        'total_cards': len(cards),
        'avg_intensity': avg_intensity,
        'commitment_distribution': dict(commitment_buckets),
        'top_outliers': outliers[:20]
    }

    # Output
    output_f = open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout

    try:
        if args.json:
            # Clean up outliers for JSON
            json_outliers = []
            for o in results['top_outliers']:
                json_outliers.append({
                    'name': o['name'],
                    'cost': o['cost'],
                    'intensity': o['intensity'],
                    'commitment': o['commitment']
                })
            results['top_outliers'] = json_outliers
            output_f.write(json.dumps(results, indent=2) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Category', 'Metric', 'Value'])
            writer.writerow(['Summary', 'Total Cards', len(cards)])
            writer.writerow(['Summary', 'Avg Intensity', f"{avg_intensity:.2f}"])
            for bucket in ["None", "Single", "Double", "Triple", "Heavy"]:
                writer.writerow(['Commitment', bucket, commitment_buckets[bucket]])
        else:
            # Table Output
            utils.print_header("MANA COST INTENSITY ANALYSIS", count=len(cards), use_color=use_color, file=output_f)

            intensity_str = f"Global Average Intensity: {avg_intensity:.2f}"
            if use_color:
                intensity_str = utils.colorize(intensity_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
            print(f"  {intensity_str}\n", file=output_f)

            # 1. Commitment Distribution
            print(f"  {datalib.color_line('Color Commitment Distribution:', use_color)}", file=output_f)
            c_header = ["Commitment", "Count", "Percent", "Distribution"]
            if use_color:
                c_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in c_header]

            c_rows = [c_header]
            for bucket in ["None", "Single", "Double", "Triple", "Heavy"]:
                count = commitment_buckets[bucket]
                percent = (count / len(cards) * 100)
                bar = datalib.get_bar_chart(percent, use_color, color=utils.Ansi.CYAN)
                c_rows.append([bucket, datalib.color_count(count, use_color), f"{percent:5.1f}%", bar])

            datalib.add_separator_row(c_rows)
            datalib.printrows(datalib.padrows(c_rows, aligns=['l', 'r', 'r', 'l']), indent=4, file=output_f)
            print("", file=output_f)

            # 2. Top Pip-Heavy Outliers
            if outliers:
                print(f"  {datalib.color_line('Top Pip-Heavy Outliers:', use_color)}", file=output_f)
                o_header = ["Name", "Cost", "Intensity", "Commit", "Rarity"]
                if use_color:
                    o_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in o_header]

                o_rows = [o_header]
                for o in outliers[:20]:
                    card = o['card']
                    name = card.display_name
                    if use_color: name = utils.colorize(name, card._get_ansi_color())

                    int_str = f"{o['intensity']:.2f}"
                    if use_color and o['intensity'] >= 0.8:
                        int_str = utils.colorize(int_str, utils.Ansi.BOLD + utils.Ansi.RED)

                    commit_str = str(o['commitment'])
                    if use_color and o['commitment'] >= 3:
                        commit_str = utils.colorize(commit_str, utils.Ansi.BOLD + utils.Ansi.RED)

                    rarity = card.rarity_name
                    if use_color: rarity = utils.colorize(rarity, utils.Ansi.get_rarity_color(rarity))

                    o_rows.append([name, card.cost.format(ansi_color=use_color), int_str, commit_str, rarity])

                datalib.add_separator_row(o_rows)
                datalib.printrows(datalib.padrows(o_rows, aligns=['l', 'l', 'r', 'r', 'l']), indent=4, file=output_f)

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Cost Analysis", len(cards), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
