#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv
from collections import Counter, defaultdict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib
from titlecase import titlecase

def get_color_identity_group(card):
    """Categorizes a card into one of the 7 primary color identity buckets."""
    identity = card.color_identity
    if not identity:
        return 'A' # Colorless
    if len(identity) > 1:
        return 'M' # Multicolored
    return identity # W, U, B, R, or G

def analyze_subtypes(cards, top_n=10):
    """
    Analyzes the subtypes (Creature types, etc.) across the dataset.
    Returns frequencies and distinctiveness scores.
    """
    color_subtypes = defaultdict(list)
    all_subtypes = []

    # Track how many cards of each color group are in the dataset
    color_card_counts = Counter()

    for card in cards:
        group = get_color_identity_group(card)
        color_card_counts[group] += 1

        # subtypes is already a list of strings
        subtypes = card.subtypes
        for s in subtypes:
            s_clean = titlecase(s.replace(utils.dash_marker, '-'))
            color_subtypes[group].append(s_clean)
            all_subtypes.append(s_clean)

    global_freq = Counter(all_subtypes)
    total_global_instances = sum(global_freq.values())

    if not all_subtypes:
        return {}

    stats = {
        'total_cards': len(cards),
        'global_freq': global_freq,
        'color_stats': {}
    }

    for group in 'WUBRGMA':
        instances = color_subtypes[group]
        if not instances:
            continue

        freq = Counter(instances)
        total_color_instances = sum(freq.values())

        # Calculate Distinctiveness (Significance score)
        # Score = (Freq in Color / Total Instances in Color) / (Freq Global / Total Instances Global)
        distinctiveness = {}
        for s, count in freq.items():
            color_prop = count / total_color_instances
            global_prop = global_freq[s] / total_global_instances
            distinctiveness[s] = color_prop / global_prop

        # Sort by distinctiveness
        top_distinct = sorted(
            [s for s in distinctiveness if freq[s] >= 1],
            key=lambda s: distinctiveness[s],
            reverse=True
        )[:top_n]

        stats['color_stats'][group] = {
            'top_signature': top_distinct,
            'freq': freq,
            'scores': distinctiveness,
            'total_instances': total_color_instances,
            'card_count': color_card_counts[group]
        }

    return stats

def main():
    parser = argparse.ArgumentParser(
        description="Analyze the distribution of card subtypes (Creature types, Artifact types, etc.) in a dataset. "
                    "Identifies popular subtypes and 'signature' subtypes characteristic of each color.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Analyze subtypes for the March of the Machine set
  python3 scripts/mtg_subtypes.py data/AllPrintings.json --set MOM

  # Find the most frequent subtypes in AI-generated cards
  python3 scripts/mtg_subtypes.py generated.txt

  # See the top 20 signature subtypes for each color
  python3 scripts/mtg_subtypes.py data/AllPrintings.json --top 20

  # Export subtype analysis to JSON
  python3 scripts/mtg_subtypes.py data/AllPrintings.json --json > subtypes.json
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, encoded text, etc.). Defaults to stdin (-). '
                             'If stdin is a terminal, AllPrintings.json is used automatically.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Optional path to save the results. If not provided, results print to the console.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate a formatted table for terminal view (Default).')
    fmt_group.add_argument('-j', '--json', action='store_true', help='Generate a structured JSON file (Auto-detected for .json).')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file (Auto-detected for .csv).')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-t', '--top', type=int, default=10,
                        help='Number of entries to show in tables (Default: 10).')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Shuffle the cards before processing.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards (shorthand for --shuffle --limit N).')
    proc_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append',
                        help='Only include cards matching a search pattern.')
    filter_group.add_argument('--set', action='append',
                        help='Only include cards from specific sets (e.g., MOM, MRD).')
    filter_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities.")
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors.")
    filter_group.add_argument('--identity', action='append',
                        help="Only include cards with specific color identities.")
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanics.')
    filter_group.add_argument('--booster', type=int, default=0,
                        help='Simulate opening N booster packs.')
    filter_group.add_argument('--box', type=int, default=0,
                        help='Simulate opening N booster boxes.')

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
    if args.infile != '-' and not os.path.exists(args.infile):
        if not args.grep:
            args.grep = [args.infile]
            args.infile = '-'

    # UX Improvement: Default Dataset
    if args.infile == '-' and sys.stdin.isatty():
        default_data = 'data/AllPrintings.json'
        if os.path.exists(default_data):
            args.infile = default_data
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

    # Load cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, sets=args.set, rarities=args.rarity,
                                  colors=args.colors, identities=args.identity,
                                  mechanics=args.mechanic,
                                  booster=args.booster, box=args.box,
                                  shuffle=args.shuffle or (args.sample > 0),
                                  seed=args.seed)

    if args.sample > 0:
        cards = cards[:args.sample]
    elif args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    stats = analyze_subtypes(cards, top_n=args.top)
    if not stats:
        if not args.quiet:
            print("No subtypes found in the dataset.", file=sys.stderr)
        return

    # Output preparation
    output_f = sys.stdout
    if args.outfile:
        output_f = open(args.outfile, 'w', encoding='utf-8')

    color_labels = {
        'W': 'White', 'U': 'Blue', 'B': 'Black', 'R': 'Red', 'G': 'Green',
        'M': 'Multi', 'A': 'Colorless'
    }

    try:
        if args.json:
            # Clean up for JSON
            json_stats = {
                'total_cards': stats['total_cards'],
                'global_freq': {k: v for k, v in stats['global_freq'].most_common()},
                'color_stats': stats['color_stats']
            }
            output_f.write(json.dumps(json_stats, indent=2) + '\n')

        elif args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Subtype', 'Count', 'Percent', 'Group', 'Distinctiveness'])

            # Global top
            for s, count in stats['global_freq'].most_common():
                percent = (count / sum(stats['global_freq'].values()) * 100)
                writer.writerow([s, count, f"{percent:.2f}%", "Global", "1.0000"])

            # Color stats
            for group, g_stats in stats['color_stats'].items():
                for s in g_stats['top_signature']:
                    count = g_stats['freq'][s]
                    percent = (count / g_stats['total_instances'] * 100)
                    score = g_stats['scores'][s]
                    writer.writerow([s, count, f"{percent:.2f}%", color_labels[group], f"{score:.4f}"])

        else: # --table
            utils.print_header("SUBTYPE DISTRIBUTION ANALYSIS", count=len(cards), use_color=use_color, file=output_f)

            # Global Top Table
            print(f"\n  {datalib.color_line('Top Subtypes Overall:', use_color)}", file=output_f)
            header = ["Subtype", "Count", "Percent", "Distribution"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]
            total_instances = sum(stats['global_freq'].values())
            for s, count in stats['global_freq'].most_common(args.top):
                percent = (count / total_instances * 100)
                bar = datalib.get_bar_chart(percent, use_color, color=utils.Ansi.CYAN)
                rows.append([
                    s,
                    datalib.color_count(count, use_color),
                    f"{percent:5.1f}%",
                    bar
                ])
            datalib.add_separator_row(rows)
            datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'r', 'l']), indent=4, file=output_f)

            # Color Breakdown Matrix
            print(f"\n  {datalib.color_line('Subtype Frequency by Color Identity (Count %):', use_color)}", file=output_f)
            c_header = ["Subtype", "W", "U", "B", "R", "G", "A", "M"]
            if use_color:
                c_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in c_header]

            c_rows = [c_header]
            top_subtypes = [s for s, _ in stats['global_freq'].most_common(args.top)]
            for s in top_subtypes:
                row = [s]
                percents = []
                for group in "WUBRGAM":
                    g_stat = stats['color_stats'].get(group, {'freq': {}, 'total_instances': 0})
                    count = g_stat['freq'].get(s, 0)
                    total = g_stat['total_instances']
                    percents.append((count / total * 100) if total > 0 else 0)

                max_p = max(percents) if percents else 0
                for i, group in enumerate("WUBRGAM"):
                    p = percents[i]
                    if p > 0:
                        val_str = f"{p:4.0f}%"
                        if use_color:
                            color = utils.Ansi.get_color_color(group)
                            if p == max_p and max_p > 0:
                                non_space = val_str.lstrip()
                                spaces = val_str[:len(val_str)-len(non_space)]
                                val = spaces + utils.colorize(non_space, color + utils.Ansi.UNDERLINE)
                            else:
                                val = utils.colorize(val_str, color)
                        else:
                            val = val_str
                    else:
                        val = "  - "
                    row.append(val)
                c_rows.append(row)
            datalib.add_separator_row(c_rows)
            datalib.printrows(datalib.padrows(c_rows, aligns=['l', 'r', 'r', 'r', 'r', 'r', 'r', 'r']), indent=4, file=output_f)

            # Signature Subtypes Table
            print(f"\n  {datalib.color_line('Signature Subtypes (Highly Distinctive):', use_color)}", file=output_f)
            s_header = ["Color", "Signature Subtypes (Ranked by Distinctiveness Score)", "Instances"]
            if use_color:
                s_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in s_header]

            s_rows = [s_header]
            for group in "WUBRGAM":
                if group not in stats['color_stats']: continue
                g_stat = stats['color_stats'][group]
                label = color_labels[group]
                if use_color:
                    label = utils.colorize(label, utils.Ansi.get_color_color(group))

                sig_words = ", ".join(g_stat['top_signature'])
                instances = str(g_stat['total_instances'])
                s_rows.append([label, sig_words, instances])

            datalib.add_separator_row(s_rows)
            datalib.printrows(datalib.padrows(s_rows, aligns=['l', 'l', 'r']), indent=4, file=output_f)

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Subtype Analysis", len(cards), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
