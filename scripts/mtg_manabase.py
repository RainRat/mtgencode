#!/usr/bin/env python3
import sys
import os
import argparse
import math
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

def calculate_manabase(cards, target_lands, include_text=False):
    """
    Calculates the recommended basic land distribution based on mana pips.
    Returns a dictionary of land names and recommended counts.
    """
    pip_counts = Counter()
    total_pips = 0

    for card in cards:
        # We only count pips for non-land cards
        if card.is_land:
            continue

        # Count pips in casting cost
        for sym, count in card.cost.allsymbols.items():
            if sym.upper() in 'WUBRG':
                pip_counts[sym.upper()] += count
                total_pips += count

        if include_text:
            for cost in card.text.costs:
                for sym, count in cost.allsymbols.items():
                    if sym.upper() in 'WUBRG':
                        pip_counts[sym.upper()] += count
                        total_pips += count

        # Multi-faced cards
        if card.bside:
            for sym, count in card.bside.cost.allsymbols.items():
                if sym.upper() in 'WUBRG':
                    pip_counts[sym.upper()] += count
                    total_pips += count
            if include_text:
                for cost in card.bside.text.costs:
                    for sym, count in cost.allsymbols.items():
                        if sym.upper() in 'WUBRG':
                            pip_counts[sym.upper()] += count
                            total_pips += count

    if total_pips == 0:
        return {
            'Plains': 0, 'Island': 0, 'Swamp': 0, 'Mountain': 0, 'Forest': 0, 'Wastes': target_lands
        }, pip_counts, total_pips

    # Calculate recommended distribution
    land_map = {
        'W': 'Plains', 'U': 'Island', 'B': 'Swamp', 'R': 'Mountain', 'G': 'Forest'
    }
    recommendation = {name: 0 for name in land_map.values()}
    active_colors = [c for c in 'WUBRG' if pip_counts[c] > 0]

    # We use a proportional distribution with a minimum of 1 if a color is present
    # to ensure you can actually cast the single 1-pip card.
    # If we have more colors than lands, we prioritize the most frequent colors.
    num_min_alloc = min(len(active_colors), target_lands)
    sorted_active = sorted(active_colors, key=lambda c: pip_counts[c], reverse=True)

    for i in range(num_min_alloc):
        recommendation[land_map[sorted_active[i]]] = 1

    remaining_lands = target_lands - num_min_alloc

    # Proportional allocation of remaining slots
    if remaining_lands > 0 and total_pips > 0:
        shares = {c: (pip_counts[c] / total_pips) * remaining_lands for c in active_colors}
        for c in active_colors:
            allocated = int(math.floor(shares[c]))
            recommendation[land_map[c]] += allocated
            shares[c] -= allocated

        # Distribute any leftover lands to the highest decimal remainders
        final_remaining = target_lands - sum(recommendation.values())
        if final_remaining > 0:
            for c in sorted(active_colors, key=lambda c: shares[c], reverse=True):
                if final_remaining <= 0: break
                recommendation[land_map[c]] += 1
                final_remaining -= 1

    # Wastes for colorless remainder if no colors at all
    recommendation['Wastes'] = max(0, target_lands - sum(v for k, v in recommendation.items() if k != 'Wastes'))

    return recommendation, pip_counts, total_pips

def main():
    parser = argparse.ArgumentParser(
        description="Recommend a basic land distribution (Mana Base) for a decklist or card dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool calculates the proportional basic land distribution needed to support the spells in a deck.
It analyzes mana pips (W, U, B, R, G) in casting costs and recommends Plains, Islands, Swamps,
Mountains, and Forests accordingly.

Usage Examples:
  # Analyze a decklist and recommend 24 lands
  python3 scripts/mtg_manabase.py my_deck.txt --lands 24

  # Use the default dataset to calculate a mana base for a specific set (40-card Limited deck)
  python3 scripts/mtg_manabase.py data/AllPrintings.json --set MOM --lands 17

  # Include activation costs in the pip analysis
  python3 scripts/mtg_manabase.py my_deck.txt --include-text
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, encoded text, or decklist). '
                             'Defaults to stdin (-). If stdin is a TTY, AllPrintings.json is used if available.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save results. If not provided, results print to the console.')
    io_group.add_argument('--lands', type=int, default=24,
                        help='Target number of basic lands to recommend (Default: 24).')
    io_group.add_argument('--include-text', action='store_true',
                        help='Include mana symbols found in rules text (activation costs, etc.) in the analysis.')

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
    filter_group.add_argument('--cmc', action='append', help='Only include cards with specific CMC values.')
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress non-critical status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # UX Improvement: Smart positional argument handling
    if args.infile and args.infile != '-' and not os.path.exists(args.infile):
        if not args.grep:
            args.grep = [args.infile]
            args.infile = '-'

    # UX Improvement: Default Dataset
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

    # Auto-detect format from extension
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
                                  grep=args.grep, sets=args.set, rarities=args.rarity,
                                  cmcs=args.cmc,
                                  produces=getattr(args, 'produces', None),
                                  decklist_file=args.deck)

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Calculate Advisor logic
    recommendation, pips, total_pips = calculate_manabase(cards, args.lands, include_text=args.include_text)

    # Output preparation
    output_f = sys.stdout
    if args.outfile:
        if args.verbose:
            print(f"Writing results to: {args.outfile}", file=sys.stderr)
        output_f = open(args.outfile, 'w', encoding='utf-8')

    try:
        if args.json:
            result = {
                'total_cards': len(cards),
                'target_lands': args.lands,
                'pip_requirements': dict(pips),
                'total_pips': total_pips,
                'recommendation': recommendation
            }
            output_f.write(json.dumps(result, indent=2) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Category', 'Item', 'Value', 'Percent'])
            for c in 'WUBRG':
                percent = (pips[c] / total_pips * 100) if total_pips > 0 else 0
                writer.writerow(['Pip Requirement', c, pips[c], f"{percent:.2f}%"])
            for land, count in recommendation.items():
                percent = (count / args.lands * 100) if args.lands > 0 else 0
                writer.writerow(['Recommended Land', land, count, f"{percent:.2f}%"])
        else:
            # 1. Header
            utils.print_header("MANA BASE ADVISOR", count=len(cards), use_color=use_color, file=output_f)

            # 2. Pip Summary
            print(f"  {datalib.color_line('Spell Pip Requirements:', use_color)}", file=output_f)
            header = ["Color", "Pips", "Requirement %", "Distribution"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            pip_rows = [header]
            for c in 'WUBRG':
                count = pips[c]
                percent = (count / total_pips * 100) if total_pips > 0 else 0
                bar = datalib.get_bar_chart(percent, use_color, color=utils.Ansi.get_color_color(c))

                label = c
                if use_color:
                    label = utils.colorize(c, utils.Ansi.get_color_color(c))

                pip_rows.append([
                    label,
                    str(count),
                    f"{percent:5.1f}%",
                    bar
                ])

            datalib.add_separator_row(pip_rows)
            datalib.printrows(datalib.padrows(pip_rows, aligns=['l', 'r', 'r', 'l']), indent=4, file=output_f)
            print("", file=output_f)

            # 3. Recommendations
            rec_title = f"Recommended Land Distribution ({args.lands} lands):"
            print(f"  {datalib.color_line(rec_title, use_color)}", file=output_f)

            rec_header = ["Basic Land", "Recommended Count", "Source %", "Chart"]
            if use_color:
                rec_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in rec_header]

            rec_rows = [rec_header]
            land_order = ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes']
            for land in land_order:
                count = recommendation.get(land, 0)
                if count == 0 and land != 'Wastes': continue
                if land == 'Wastes' and count == 0 and total_pips > 0: continue

                percent = (count / args.lands * 100) if args.lands > 0 else 0

                color_char = land[0] if land != 'Wastes' else 'C'
                if land == 'Island': color_char = 'U'

                bar = datalib.get_bar_chart(percent, use_color, color=utils.Ansi.get_color_color(color_char))

                display_land = land
                if use_color:
                    display_land = utils.colorize(land, utils.Ansi.get_color_color(color_char))

                rec_rows.append([
                    display_land,
                    datalib.color_count(count, use_color),
                    f"{percent:5.1f}%",
                    bar
                ])

            datalib.add_separator_row(rec_rows)
            datalib.printrows(datalib.padrows(rec_rows, aligns=['l', 'r', 'r', 'l']), indent=4, file=output_f)
            print("", file=output_f)

            # Final summary to stdout if not quiet
            if not args.quiet:
                summary_list = []
                for land in land_order:
                    if recommendation.get(land, 0) > 0:
                        summary_list.append(f"{recommendation[land]} {land}")
                print("  Suggested: " + ", ".join(summary_list), file=output_f)

    finally:
        if args.outfile:
            output_f.close()

if __name__ == "__main__":
    main()
