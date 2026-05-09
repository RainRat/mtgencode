#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv
import re
from collections import Counter, defaultdict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib

# Standard Booster distribution: 10 Commons, 3 Uncommons, 1 Rare/Mythic, 1 Basic Land
BOOSTER_SLOTS = {
    utils.rarity_common_marker: 10.0,
    utils.rarity_uncommon_marker: 3.0,
    'RARE_SLOT': 1.0, # Rare or Mythic
    utils.rarity_basic_land_marker: 1.0
}

def calculate_asfan(cards):
    """
    Calculates As-Fan statistics for a dataset.
    Returns a dictionary of metrics mapped to their As-Fan values.
    """
    if not cards:
        return {}

    # Group cards by rarity
    rarity_pools = defaultdict(list)
    for card in cards:
        r = card.rarity
        if r in [utils.rarity_rare_marker, utils.rarity_mythic_marker]:
            rarity_pools['RARE_SLOT'].append(card)
        else:
            rarity_pools[r].append(card)

    def get_asfan_for_metric(metric_fn):
        total_asfan = 0.0
        for slot, slot_count in BOOSTER_SLOTS.items():
            pool = rarity_pools.get(slot, [])
            if pool:
                # Calculate probability of metric in this pool
                metric_count = sum(1 for card in pool if metric_fn(card))
                prob = metric_count / len(pool)
                total_asfan += prob * slot_count
        return total_asfan

    def get_asfan_for_counter(metric_extractor_fn):
        # metric_extractor_fn returns a list/set of keys for a card
        # We need to calculate As-Fan for EACH key
        all_keys = set()
        pool_counts = defaultdict(Counter)

        for slot in BOOSTER_SLOTS:
            pool = rarity_pools.get(slot, [])
            for card in pool:
                keys = metric_extractor_fn(card)
                for k in keys:
                    all_keys.add(k)
                    pool_counts[slot][k] += 1

        results = {}
        for k in all_keys:
            total_asfan = 0.0
            for slot, slot_count in BOOSTER_SLOTS.items():
                pool_len = len(rarity_pools.get(slot, []))
                if pool_len > 0:
                    prob = pool_counts[slot][k] / pool_len
                    total_asfan += prob * slot_count
            results[k] = total_asfan
        return results

    results = {}

    # 1. Colors & Color Identity
    results['colors'] = get_asfan_for_counter(lambda c: c.cost.colors or ['C'])
    results['identity'] = get_asfan_for_counter(lambda c: list(c.color_identity) or ['C'])

    # 2. Card Types
    tracked_types = ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land", "Battle"]
    results['types'] = get_asfan_for_counter(lambda c: [t for t in tracked_types if c._has_type(t)])

    # 3. Mechanics
    results['mechanics'] = get_asfan_for_counter(lambda c: list(c.mechanics))

    # 4. Multicolored As-Fan
    results['multicolored'] = get_asfan_for_metric(lambda c: len(c.cost.colors) > 1)

    # 5. Fixing As-Fan (Produces 2+ colors or Any)
    # Import locally to avoid circular dependency if any
    from mtg_mana import get_produced_colors
    results['fixing'] = get_asfan_for_metric(lambda c: len(get_produced_colors(c)) >= 2 or "Any" in get_produced_colors(c))

    return results

def main():
    parser = argparse.ArgumentParser(
        description="Calculate 'As-Fan' (As fanned) statistics for a card dataset. "
                    "As-Fan is the average number of cards with a certain characteristic "
                    "expected in a standard 15-card booster pack.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Standard Booster distribution used: 10 Common, 3 Uncommon, 1 Rare/Mythic, 1 Basic Land.

Usage Examples:
  # Analyze As-Fan for a specific set
  python3 scripts/mtg_asfan.py data/AllPrintings.json --set MOM

  # Compare As-Fan of a generated set vs official data
  python3 scripts/mtg_asfan.py data/AllPrintings.json --compare generated.txt --set MOM

  # Filter by keyword to see As-Fan for specific themes
  python3 scripts/mtg_asfan.py data/AllPrintings.json -g "Toxic"
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). Defaults to stdin (-). '
                             'If stdin is a terminal, it attempts to use data/AllPrintings.json.')
    io_group.add_argument('--compare', '-c',
                        help='Optional second dataset to compare against the primary input.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save results. If not provided, results print to the console.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('-S', '--table', action='store_true', help='Generate a formatted table (Default).')
    fmt_group.add_argument('-j', '--json', action='store_true', help='Generate a JSON file.')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file.')

    # Group: Filtering Options (Standard)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append', help='Only include cards matching a search pattern.')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--mechanic', action='append', help='Only include cards with specific mechanics.')
    filter_group.add_argument('-n', '--limit', type=int, default=0, help='Only process the first N cards from each input.')

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
    def load_data(path):
        if not path: return None
        cards = jdecode.mtg_open_file(path, verbose=args.verbose, grep=args.grep,
                                      sets=args.set, mechanics=args.mechanic)
        if args.limit > 0:
            cards = cards[:args.limit]
        return cards

    cards1 = load_data(args.infile)
    if not cards1:
        if not args.quiet:
            print(f"No cards found in {args.infile} matching criteria.", file=sys.stderr)
        return

    asfan1 = calculate_asfan(cards1)

    asfan2 = None
    if args.compare:
        cards2 = load_data(args.compare)
        if cards2:
            asfan2 = calculate_asfan(cards2)

    # Output
    output_f = open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout

    try:
        if args.json:
            result = {'primary': asfan1}
            if asfan2: result['comparison'] = asfan2
            output_f.write(json.dumps(result, indent=2) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            header = ['Category', 'Metric', os.path.basename(args.infile)[:15]]
            if asfan2: header.append(os.path.basename(args.compare)[:15])
            writer.writerow(header)

            for cat in sorted(asfan1.keys()):
                val = asfan1[cat]
                if isinstance(val, dict):
                    for k in sorted(val.keys()):
                        row = [cat, k, f"{val[k]:.2f}"]
                        if asfan2: row.append(f"{asfan2[cat].get(k, 0.0):.2f}")
                        writer.writerow(row)
                else:
                    row = ['General', cat, f"{val:.2f}"]
                    if asfan2: row.append(f"{asfan2.get(cat, 0.0):.2f}")
                    writer.writerow(row)
        else:
            # Table Output
            title = "AS-FAN ANALYSIS"
            if asfan2: title += " (COMPARISON)"
            utils.print_header(title, count=len(cards1), use_color=use_color, file=output_f)

            def print_table_section(section_title, data1, data2, keys=None, key_formatter=None):
                print(f"  {datalib.color_line(section_title, use_color)}", file=output_f)

                fname1 = os.path.basename(args.infile)[:15]
                header = ["Metric", fname1]
                if data2 is not None:
                    fname2 = os.path.basename(args.compare)[:15]
                    header.extend([fname2, "Delta"])
                else:
                    header.append("Frequency")

                if use_color:
                    header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

                rows = [header]

                if keys is None:
                    keys = sorted(data1.keys())

                for k in keys:
                    v1 = data1.get(k, 0.0)
                    display_k = key_formatter(k) if key_formatter else str(k)

                    if use_color:
                        if section_title.lower().startswith('color'):
                            display_k = utils.colorize(display_k, utils.Ansi.get_color_color(k))

                    row = [display_k, f"{v1:4.2f}"]
                    if data2 is not None:
                        v2 = data2.get(k, 0.0)
                        delta = v2 - v1
                        delta_str = f"{delta:+5.2f}"
                        if use_color:
                            if delta > 0.2: delta_str = utils.colorize(delta_str, utils.Ansi.GREEN)
                            elif delta < -0.2: delta_str = utils.colorize(delta_str, utils.Ansi.RED)
                        row.extend([f"{v2:4.2f}", delta_str])
                    else:
                        # For single dataset, show a small bar chart based on 15 max (booster size)
                        percent = (v1 / 15.0 * 100)
                        bar = datalib.get_bar_chart(percent, use_color)
                        row.append(bar)
                    rows.append(row)

                datalib.add_separator_row(rows)
                datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'r', 'r']), indent=4, file=output_f)
                print("", file=output_f)

            # General
            gen1 = {
                'Multicolored': asfan1['multicolored'],
                'Mana Fixing': asfan1['fixing']
            }
            gen2 = {
                'Multicolored': asfan2['multicolored'],
                'Mana Fixing': asfan2['fixing']
            } if asfan2 else None
            print_table_section("General Distribution:", gen1, gen2)

            # Colors
            print_table_section("Color Distribution (Casting Cost):", asfan1['colors'], asfan2['colors'] if asfan2 else None, keys='WUBRGC')

            # Types
            print_table_section("Type Distribution:", asfan1['types'], asfan2['types'] if asfan2 else None)

            # Top Mechanics
            top_mechs = sorted(asfan1['mechanics'].keys(), key=lambda x: asfan1['mechanics'][x], reverse=True)[:10]
            if asfan2:
                # Include mechanics from comparison set if they are top there too
                top_mechs2 = sorted(asfan2['mechanics'].keys(), key=lambda x: asfan2['mechanics'][x], reverse=True)[:10]
                top_mechs = sorted(list(set(top_mechs + top_mechs2)), key=lambda x: max(asfan1['mechanics'].get(x, 0), asfan2['mechanics'].get(x, 0)), reverse=True)

            if top_mechs:
                print_table_section("Top Mechanics As-Fan:", asfan1['mechanics'], asfan2['mechanics'] if asfan2 else None, keys=top_mechs)

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("As-Fan Analysis", len(cards1), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
