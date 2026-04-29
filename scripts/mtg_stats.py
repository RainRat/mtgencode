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

def get_numeric_stats(card):
    """Extracts power, toughness, and loyalty as floats if possible."""
    p = utils.from_unary_single(card.pt_p)
    t = utils.from_unary_single(card.pt_t)
    l = utils.from_unary_single(card.loyalty)

    # In this project, we primarily analyze the front face for combat stats.
    # Recursive handling of b-sides for stats often creates noise in distributions
    # and is omitted here for consistency with mtg_curve.py.
    return p, t, l

def main():
    parser = argparse.ArgumentParser(
        description="Analyze creature combat stats (Power/Toughness) and Planeswalker loyalty in a dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool provides a detailed breakdown of combat stats across different colors and mana costs.
It helps designers ensure that the "size" of creatures in their set aligns with the color pie and curve.

Usage Examples:
  # Analyze stats for a specific set
  python3 scripts/mtg_stats.py data/AllPrintings.json --set MOM

  # Compare stats of rare creatures vs common creatures
  python3 scripts/mtg_stats.py data/AllPrintings.json --rarity rare --grep-type "Creature"
  python3 scripts/mtg_stats.py data/AllPrintings.json --rarity common --grep-type "Creature"

  # Find stats for only Red cards
  python3 scripts/mtg_stats.py data/AllPrintings.json --colors R
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, MSE, or encoded text). Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the results. If not provided, results print to the console.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate a formatted table (Default for terminal).')
    fmt_group.add_argument('--json', action='store_true', help='Generate a JSON file (Auto-detected for .json).')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file (Auto-detected for .csv).')

    # Group: Filtering Options (Standard)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append', help='Only include cards matching a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append', dest='vgrep', help='Exclude cards matching a search pattern.')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
    filter_group.add_argument('--colors', action='append', help='Only include cards of specific colors.')
    filter_group.add_argument('--identity', action='append', help='Only include cards with specific color identities.')
    filter_group.add_argument('--cmc', action='append', help='Only include cards with specific CMC values.')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow', help='Only include cards with specific Power values.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou', help='Only include cards with specific Toughness values.')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy', help='Only include cards with specific Loyalty or Defense values.')
    filter_group.add_argument('--mechanic', action='append', help='Only include cards with specific mechanical features.')
    filter_group.add_argument('--limit', type=int, default=0, help='Only process the first N cards.')
    filter_group.add_argument('--shuffle', action='store_true', help='Randomize card order.')
    filter_group.add_argument('--sample', type=int, default=0, help='Pick N random cards.')
    filter_group.add_argument('--seed', type=int, help='Seed for random generator.')

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

    # Format detection
    if not (args.json or args.csv or args.table):
        if args.outfile:
            if args.outfile.endswith('.json'): args.json = True
            elif args.outfile.endswith('.csv'): args.csv = True
            else: args.table = True
        else:
            args.table = True

    # Color detection
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
                                  shuffle=args.shuffle, seed=args.seed)

    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Data structures for analysis
    # 1. P/T per CMC
    cmc_stats = defaultdict(lambda: {'pow_sum': 0.0, 'tou_sum': 0.0, 'count': 0})
    # 2. P/T per Color
    color_stats = defaultdict(lambda: {'pow_sum': 0.0, 'tou_sum': 0.0, 'count': 0})
    # 3. P vs T distribution
    pt_dist = Counter()
    # 4. Loyalty stats
    loy_stats = []

    creature_count = 0

    for card in cards:
        p, t, l = get_numeric_stats(card)
        cmc = int(card.cost.cmc)
        bucket = cmc if cmc < 7 else 7
        if bucket < 0: bucket = 0

        if p is not None and t is not None:
            creature_count += 1
            # Global CMC bucket
            cmc_stats[bucket]['pow_sum'] += p
            cmc_stats[bucket]['tou_sum'] += t
            cmc_stats[bucket]['count'] += 1

            # Color breakdown
            card_colors = card.cost.colors or ['C']
            for c in card_colors:
                color_stats[c]['pow_sum'] += p
                color_stats[c]['tou_sum'] += t
                color_stats[c]['count'] += 1

            # Distribution
            pt_dist[(int(p), int(t))] += 1

        if l is not None:
            loy_stats.append(l)

    # Prepare results object
    results = {
        'total_cards': len(cards),
        'creatures_analyzed': creature_count,
        'cmc_curve': [],
        'color_breakdown': [],
        'pt_distribution': [],
        'loyalty': {}
    }

    # Process CMC curve
    for bucket in range(8):
        stats = cmc_stats[bucket]
        if stats['count'] > 0:
            results['cmc_curve'].append({
                'cmc': str(bucket) if bucket < 7 else "7+",
                'avg_pow': stats['pow_sum'] / stats['count'],
                'avg_tou': stats['tou_sum'] / stats['count'],
                'count': stats['count']
            })

    # Process color breakdown
    for c in 'WUBRGC':
        stats = color_stats[c]
        if stats['count'] > 0:
            results['color_breakdown'].append({
                'color': c,
                'avg_pow': stats['pow_sum'] / stats['count'],
                'avg_tou': stats['tou_sum'] / stats['count'],
                'count': stats['count']
            })

    # Process P vs T distribution (Top 10)
    for (p, t), count in pt_dist.most_common(10):
        results['pt_distribution'].append({
            'pt': f"{p}/{t}",
            'count': count,
            'percent': (count / creature_count * 100) if creature_count > 0 else 0
        })

    # Process loyalty
    if loy_stats:
        results['loyalty'] = {
            'avg': sum(loy_stats) / len(loy_stats),
            'min': min(loy_stats),
            'max': max(loy_stats),
            'count': len(loy_stats)
        }

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
            writer.writerow(['Metric', 'Category', 'Avg Pow', 'Avg Tou', 'Count'])
            for r in results['cmc_curve']:
                writer.writerow(['CMC Curve', r['cmc'], f"{r['avg_pow']:.2f}", f"{r['avg_tou']:.2f}", r['count']])
            for r in results['color_breakdown']:
                writer.writerow(['Color Breakdown', r['color'], f"{r['avg_pow']:.2f}", f"{r['avg_tou']:.2f}", r['count']])
        else:
            # Table Output
            utils.print_header("COMBAT STAT ANALYSIS", count=len(cards), use_color=use_color, file=output_f)

            if creature_count > 0:
                # 1. Combat Stat Curve
                print(f"  {datalib.color_line('Combat Stat Curve (Avg P/T per CMC):', use_color)}", file=output_f)
                header = ["CMC", "Avg Power", "Avg Tough", "Count", "Ratio"]
                if use_color:
                    header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

                rows = [header]
                for r in results['cmc_curve']:
                    ratio = r['avg_pow'] / r['avg_tou'] if r['avg_tou'] > 0 else 0
                    ratio_str = f"{ratio:.2f}"
                    if use_color:
                        if ratio > 1.1: ratio_str = utils.colorize(ratio_str, utils.Ansi.BOLD + utils.Ansi.RED)
                        elif ratio < 0.9: ratio_str = utils.colorize(ratio_str, utils.Ansi.BOLD + utils.Ansi.GREEN)

                    rows.append([
                        utils.colorize(r['cmc'], utils.Ansi.CYAN) if use_color else r['cmc'],
                        f"{r['avg_pow']:5.2f}",
                        f"{r['avg_tou']:5.2f}",
                        datalib.color_count(r['count'], use_color),
                        ratio_str
                    ])
                datalib.add_separator_row(rows)
                datalib.printrows(datalib.padrows(rows, aligns=['r', 'r', 'r', 'r', 'r']), indent=4)
                print("", file=output_f)

                # 2. Color Breakdown
                print(f"  {datalib.color_line('Average Stats by Color:', use_color)}", file=output_f)
                c_header = ["Color", "Avg Power", "Avg Tough", "Count"]
                if use_color:
                    c_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in c_header]

                c_rows = [c_header]
                for r in results['color_breakdown']:
                    c_rows.append([
                        utils.colorize(r['color'], utils.Ansi.get_color_color(r['color'])) if use_color else r['color'],
                        f"{r['avg_pow']:5.2f}",
                        f"{r['avg_tou']:5.2f}",
                        datalib.color_count(r['count'], use_color)
                    ])
                datalib.add_separator_row(c_rows)
                datalib.printrows(datalib.padrows(c_rows, aligns=['l', 'r', 'r', 'r']), indent=4)
                print("", file=output_f)

                # 3. Top P/T Combinations
                print(f"  {datalib.color_line('Popular P/T Combinations:', use_color)}", file=output_f)
                d_header = ["P/T", "Count", "Percent", "Frequency"]
                if use_color:
                    d_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in d_header]

                d_rows = [d_header]
                for r in results['pt_distribution']:
                    bar = datalib.get_bar_chart(r['percent'], use_color, color=utils.Ansi.RED)
                    d_rows.append([
                        utils.colorize(r['pt'], utils.Ansi.BOLD + utils.Ansi.RED) if use_color else r['pt'],
                        datalib.color_count(r['count'], use_color),
                        f"{r['percent']:5.1f}%",
                        bar
                    ])
                datalib.add_separator_row(d_rows)
                datalib.printrows(datalib.padrows(d_rows, aligns=['l', 'r', 'r', 'l']), indent=4)
                print("", file=output_f)
            else:
                print("  No creatures found for combat stat analysis.", file=output_f)

            if results['loyalty']:
                print(f"  {datalib.color_line('Loyalty Stats (Planeswalkers/Battles):', use_color)}", file=output_f)
                l = results['loyalty']
                print(f"    Average Loyalty: {l['avg']:.2f}", file=output_f)
                print(f"    Range:           {int(l['min'])} - {int(l['max'])}", file=output_f)
                print(f"    Count:           {l['count']}", file=output_f)
                print("", file=output_f)

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Stat Analysis", len(cards), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
