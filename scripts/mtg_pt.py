#!/usr/bin/env python3
import sys
import os
import argparse
from collections import defaultdict, Counter

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib

def get_pt_values(card):
    """Extracts numeric Power and Toughness from a card, handling multiple faces."""
    res = []

    def extract_single(c):
        p_val = utils.from_unary_single(c.pt_p)
        t_val = utils.from_unary_single(c.pt_t)
        if p_val is not None and t_val is not None:
            return p_val, t_val
        return None

    val = extract_single(card)
    if val:
        res.append(val)

    if card.bside:
        res.extend(get_pt_values(card.bside))

    return res

def main():
    parser = argparse.ArgumentParser(
        description="Analyze creature Power/Toughness distribution and combat balance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool provides a visual "Combat Grid" mapping Power vs. Toughness distribution.
It helps identify if a creature pool is Aggressive (P > T), Defensive (P < T), or Balanced.

Usage Examples:
  # Analyze P/T distribution for a set
  python3 scripts/mtg_pt.py data/AllPrintings.json --set MOM

  # Compare creature stats across blue and green cards
  python3 scripts/mtg_pt.py data/AllPrintings.json --colors UG
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (MTGJSON, Scryfall, CSV, XML, or encoded text). Defaults to stdin (-).')

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

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append',
                        help='Only include cards matching a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append', dest='vgrep',
                        help='Exclude cards matching a search pattern.')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
    filter_group.add_argument('--colors', action='append', help='Only include cards of specific colors.')
    filter_group.add_argument('--cmc', action='append', help='Only include cards with specific CMC values.')
    filter_group.add_argument('--mechanic', action='append', help='Only include cards with specific mechanics.')
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

    if args.sample > 0:
        args.shuffle = True
        args.limit = args.sample

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty():
        use_color = True

    # Load and filter cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, vgrep=args.vgrep,
                                  sets=args.set, rarities=args.rarity,
                                  colors=args.colors, cmcs=args.cmc,
                                  mechanics=args.mechanic,
                                  booster=args.booster, box=args.box,
                                  shuffle=args.shuffle, seed=args.seed)

    # Filter for creatures
    creatures = [c for c in cards if c.is_creature]

    if args.limit > 0:
        creatures = creatures[:args.limit]

    if not creatures:
        if not args.quiet:
            print("No creatures found matching the criteria.", file=sys.stderr)
        return

    # Data collection
    # matrix[power][toughness] = count
    matrix = defaultdict(lambda: defaultdict(int))

    color_stats = defaultdict(lambda: {'p': 0, 't': 0, 'count': 0})
    cmc_stats = defaultdict(lambda: {'p': 0, 't': 0, 'count': 0})

    orient_counts = Counter() # Aggressive, Defensive, Balanced

    total_entries = 0
    max_p = 0
    max_t = 0

    for c in creatures:
        pt_vals = get_pt_values(c)
        for p, t in pt_vals:
            # Grid data
            p_idx = int(p) if p == int(p) else 0 # simple truncate for now
            t_idx = int(t) if t == int(t) else 0

            # Bound for grid display
            if p_idx > 10: p_idx = 10
            if t_idx > 10: t_idx = 10

            matrix[p_idx][t_idx] += 1
            max_p = max(max_p, p_idx)
            max_t = max(max_t, t_idx)
            total_entries += 1

            # Orientation
            if p > t: orient_counts['Aggressive'] += 1
            elif p < t: orient_counts['Defensive'] += 1
            else: orient_counts['Balanced'] += 1

            # Color Stats
            colors = c.cost.colors if c.cost.colors else ['C']
            for color in colors:
                color_stats[color]['p'] += p
                color_stats[color]['t'] += t
                color_stats[color]['count'] += 1

            # CMC Stats
            cmc = int(c.cost.cmc)
            if cmc > 7: cmc = 7
            cmc_stats[cmc]['p'] += p
            cmc_stats[cmc]['t'] += t
            cmc_stats[cmc]['count'] += 1

    # 1. Header
    utils.print_header("COMBAT STAT ANALYSIS", count=len(creatures), use_color=use_color)
    print()

    # 2. Combat Grid
    print(f"  {datalib.color_line('Combat Grid (Power vs. Toughness):', use_color)}")

    grid_size = min(10, max(max_p, max_t))
    # Y axis: Power, X axis: Toughness
    header = ["P \\ T"] + [str(i) for i in range(grid_size + 1)] + ["Total"]
    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]
    col_totals = defaultdict(int)

    for p in range(grid_size + 1):
        row_label = str(p)
        if use_color:
            row_label = utils.colorize(row_label, utils.Ansi.CYAN)
        row = [row_label]
        row_total = 0
        for t in range(grid_size + 1):
            count = matrix[p][t]
            row.append(datalib.color_count(count, use_color) if count > 0 else "-")
            row_total += count
            col_totals[t] += count

        row.append(utils.colorize(str(row_total), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(row_total))
        rows.append(row)

    datalib.add_separator_row(rows)

    # Footer totals
    totals_label = "Total"
    if use_color:
        totals_label = utils.colorize(totals_label, utils.Ansi.BOLD + utils.Ansi.YELLOW)
    totals_row = [totals_label]
    grand_total = 0
    for t in range(grid_size + 1):
        count = col_totals[t]
        totals_row.append(utils.colorize(str(count), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(count))
        grand_total += count
    totals_row.append(utils.colorize(str(grand_total), utils.Ansi.BOLD + utils.Ansi.WHITE + utils.Ansi.UNDERLINE) if use_color else str(grand_total))
    rows.append(totals_row)

    datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r'] * (len(header) - 1)), indent=4)
    print()

    # 3. Orientation Summary
    print(f"  {datalib.color_line('Combat Orientation:', use_color)}")
    o_header = ["Category", "Count", "Percent", "Distribution"]
    if use_color:
        o_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in o_header]

    o_rows = [o_header]
    categories = [
        ('Aggressive (P > T)', orient_counts['Aggressive'], utils.Ansi.BOLD + utils.Ansi.RED),
        ('Defensive (P < T)', orient_counts['Defensive'], utils.Ansi.BOLD + utils.Ansi.BLUE),
        ('Balanced (P = T)', orient_counts['Balanced'], utils.Ansi.BOLD + utils.Ansi.GREEN),
    ]

    for label, count, color in categories:
        pct = (count / total_entries * 100) if total_entries > 0 else 0
        bar = datalib.get_bar_chart(pct, use_color, color=color)
        o_rows.append([
            utils.colorize(label, color) if use_color else label,
            datalib.color_count(count, use_color, color),
            f"{pct:5.1f}%",
            bar
        ])

    datalib.add_separator_row(o_rows)
    datalib.printrows(datalib.padrows(o_rows, aligns=['l', 'r', 'r', 'l']), indent=4)
    print()

    # 4. Color Stat Averages
    print(f"  {datalib.color_line('Average Stats by Color:', use_color)}")
    c_header = ["Color", "Avg Power", "Avg Toughness", "Ratio (P/T)"]
    if use_color:
        c_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in c_header]

    c_rows = [c_header]
    for color in ['W', 'U', 'B', 'R', 'G', 'C']:
        stats = color_stats[color]
        if stats['count'] == 0: continue

        avg_p = stats['p'] / stats['count']
        avg_t = stats['t'] / stats['count']
        ratio = avg_p / avg_t if avg_t > 0 else 0

        label = color
        if use_color:
            label = utils.colorize(color, utils.Ansi.get_color_color(color))

        c_rows.append([
            label,
            f"{avg_p:.2f}",
            f"{avg_t:.2f}",
            f"{ratio:.2f}"
        ])

    if len(c_rows) > 1:
        datalib.add_separator_row(c_rows)
        datalib.printrows(datalib.padrows(c_rows, aligns=['l', 'r', 'r', 'r']), indent=4)
    print()

    # 5. CMC Stat Averages
    print(f"  {datalib.color_line('Average Stats by CMC:', use_color)}")
    cmc_header = ["CMC", "Avg Power", "Avg Toughness", "Ratio (P/T)", "Count"]
    if use_color:
        cmc_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in cmc_header]

    cmc_rows = [cmc_header]
    for cmc in sorted(cmc_stats.keys()):
        stats = cmc_stats[cmc]
        if stats['count'] == 0: continue

        avg_p = stats['p'] / stats['count']
        avg_t = stats['t'] / stats['count']
        ratio = avg_p / avg_t if avg_t > 0 else 0

        label = str(cmc) if cmc < 7 else "7+"
        if use_color:
            label = utils.colorize(label, utils.Ansi.CYAN)

        cmc_rows.append([
            label,
            f"{avg_p:.2f}",
            f"{avg_t:.2f}",
            f"{ratio:.2f}",
            datalib.color_count(stats['count'], use_color)
        ])

    if len(cmc_rows) > 1:
        datalib.add_separator_row(cmc_rows)
        datalib.printrows(datalib.padrows(cmc_rows, aligns=['r', 'r', 'r', 'r', 'r']), indent=4)
    print()

    if not args.quiet:
        utils.print_operation_summary("Combat Analysis", total_entries, 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
