#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv
from collections import Counter

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib

def get_cost_metrics(card):
    """Calculates pip-related metrics for a card's mana cost."""
    # We focus on the front face for these metrics
    cmc = card.cost.cmc
    # Count colored pips (WUBRG)
    colored_pips = sum(count for sym, count in card.cost.allsymbols.items() if sym.upper() in 'WUBRG')

    intensity = colored_pips / max(1, cmc) if cmc > 0 else 0.0

    # Pip count category
    pip_category = "None"
    if colored_pips == 1: pip_category = "Single"
    elif colored_pips == 2: pip_category = "Double"
    elif colored_pips == 3: pip_category = "Triple"
    elif colored_pips >= 4: pip_category = "Heavy (4+)"

    return colored_pips, intensity, pip_category

def main():
    parser = argparse.ArgumentParser(
        description="Analyze the complexity and intensity of mana costs in a dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Color Intensity measures how "difficult" a card is to cast based on its colored mana requirements
relative to its total mana value (CMC).

Metrics:
  - Colored Pips: Total count of W, U, B, R, or G symbols in the casting cost.
  - Color Intensity: (Colored Pips / CMC). A 1/1 for {G} has an intensity of 1.0.
  - Pip Distribution: Breakdown of cards by how many colored pips they require.

Usage Examples:
  # Analyze cost intensity for a specific set
  python3 scripts/mtg_costs.py data/AllPrintings.json --set MOM

  # Find "pip-heavy" outliers in the entire dataset
  python3 scripts/mtg_costs.py data/AllPrintings.json --limit 20

  # Compare cost intensity across rarities
  python3 scripts/mtg_costs.py data/AllPrintings.json --rarity rare --rarity mythic
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). Defaults to stdin (-). '
                             'If stdin is a terminal, it attempts to use data/AllPrintings.json.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save results. If not provided, results print to the console.')
    io_group.add_argument('-n', '--limit', type=int, default=20,
                        help='Number of top intensity outliers to show (Default: 20).')
    io_group.add_argument('-j', '--json', action='store_true', help='Output results in JSON format.')
    io_group.add_argument('--csv', action='store_true', help='Output results in CSV format.')

    # Group: Filtering Options (Standard)
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

    # Load and filter cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose, grep=args.grep,
                                  sets=args.set, rarities=args.rarity, colors=args.colors,
                                  cmcs=args.cmc, mechanics=args.mechanic)

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Analysis
    results_list = []
    pip_dist = Counter()
    total_intensity = 0.0
    valid_count = 0

    for card in cards:
        if card.is_land: continue # Lands usually don't have costs

        pips, intensity, cat = get_cost_metrics(card)
        pip_dist[cat] += 1
        total_intensity += intensity
        valid_count += 1

        results_list.append({
            'name': card.display_name,
            'cost': card.cost.format(),
            'cmc': card.cost.cmc,
            'pips': pips,
            'intensity': intensity,
            'rarity': card.rarity_name,
            'color': card._get_ansi_color() if hasattr(card, '_get_ansi_color') else ""
        })

    if valid_count == 0:
        if not args.quiet:
            print("No cards with mana costs found for analysis.", file=sys.stderr)
        return

    # Sort by intensity (descending)
    sorted_results = sorted(results_list, key=lambda x: x['intensity'], reverse=True)
    avg_intensity = total_intensity / valid_count

    # Output preparation
    output_f = open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout
    use_color = args.color if args.color is not None else (sys.stdout.isatty() and not (args.json or args.csv))

    try:
        if args.json:
            result = {
                'total_analyzed': valid_count,
                'average_intensity': avg_intensity,
                'pip_distribution': dict(pip_dist),
                'top_intensity_cards': sorted_results[:args.limit]
            }
            output_f.write(json.dumps(result, indent=2) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Name', 'Cost', 'CMC', 'Pips', 'Intensity', 'Rarity'])
            for r in sorted_results[:args.limit]:
                writer.writerow([r['name'], r['cost'], r['cmc'], r['pips'], f"{r['intensity']:.2f}", r['rarity']])
        else:
            # Table Output
            utils.print_header("COLOR INTENSITY ANALYSIS", count=valid_count, use_color=use_color, file=output_f)

            avg_str = f"Average Color Intensity: {avg_intensity:.2f}"
            if use_color:
                avg_str = utils.colorize(avg_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
            output_f.write(f"  {avg_str}\n\n")

            # 1. Pip Distribution
            print(f"  {datalib.color_line('Pip Count Distribution:', use_color)}", file=output_f)
            d_header = ["Category", "Count", "Percent", "Distribution"]
            if use_color:
                d_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in d_header]

            d_rows = [d_header]
            for cat in ["None", "Single", "Double", "Triple", "Heavy (4+)"]:
                count = pip_dist[cat]
                percent = (count / valid_count * 100)
                bar = datalib.get_bar_chart(percent, use_color, color=utils.Ansi.CYAN)
                d_rows.append([cat, str(count), f"{percent:5.1f}%", bar])

            datalib.add_separator_row(d_rows)
            datalib.printrows(datalib.padrows(d_rows, aligns=['l', 'r', 'r', 'l']), indent=4, file=output_f)
            print("", file=output_f)

            # 2. Top Intensity Cards
            print(f"  {datalib.color_line('Top Intensity Outliers:', use_color)}", file=output_f)
            header = ["Name", "Cost", "CMC", "Pips", "Intensity", "Rarity"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]
            for r in sorted_results[:args.limit]:
                name = r['name']
                if use_color: name = utils.colorize(name, r['color'])

                intensity_str = f"{r['intensity']:.2f}"
                if use_color:
                    color = utils.Ansi.BOLD + utils.Ansi.RED if r['intensity'] >= 1.0 else (utils.Ansi.YELLOW if r['intensity'] >= 0.5 else "")
                    intensity_str = utils.colorize(intensity_str, color)

                rows.append([name, r['cost'], str(r['cmc']), str(r['pips']), intensity_str, r['rarity']])

            datalib.add_separator_row(rows)
            datalib.printrows(datalib.padrows(rows, aligns=['l', 'l', 'r', 'r', 'r', 'l']), indent=4, file=output_f)

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Cost Analysis", valid_count, 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
