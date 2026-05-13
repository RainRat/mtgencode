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

def calculate_synergy(cards, min_freq=2):
    """
    Analyzes mechanical co-occurrence and synergy.
    Returns:
        - density_dist: Counter of mechanics per card
        - individual_counts: Counter of mechanics
        - pair_counts: Counter of (mech1, mech2) pairs
        - synergy_results: List of dicts with pair, count, lift, etc.
    """
    total_cards = len(cards)
    if total_cards == 0:
        return {}, Counter(), Counter(), []

    individual_counts = Counter()
    pair_counts = Counter()
    density_dist = Counter()

    for card in cards:
        mechs = sorted(list(card.mechanics))
        density_dist[len(mechs)] += 1

        for m in mechs:
            individual_counts[m] += 1

        for i in range(len(mechs)):
            for j in range(i + 1, len(mechs)):
                pair_counts[(mechs[i], mechs[j])] += 1

    synergy_results = []
    for (m1, m2), count in pair_counts.items():
        if count < min_freq:
            continue

        c1 = individual_counts[m1]
        c2 = individual_counts[m2]

        lift = (count * total_cards) / (c1 * c2)

        synergy_results.append({
            'pair': (m1, m2),
            'count': count,
            'lift': lift,
            'p_a_and_b': count / total_cards,
            'p_a': c1 / total_cards,
            'p_b': c2 / total_cards
        })

    return density_dist, individual_counts, pair_counts, synergy_results

def main():
    parser = argparse.ArgumentParser(
        description="Analyze mechanical synergy and co-occurrence in a card dataset. "
                    "Identifies which mechanics are frequently paired together and calculates 'Lift' to measure synergy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Synergy Scoring (Lift):
  Lift measures how much more often two mechanics appear together than would be expected if they were independent.
  - Lift > 1.0: Positive synergy (they appear together more than expected).
  - Lift = 1.0: Independence (no correlation).
  - Lift < 1.0: Negative synergy or interference (they appear together less than expected).

Usage Examples:
  # Analyze synergy in a specific set
  python3 scripts/mtg_synergy.py data/AllPrintings.json --set MOM

  # Analyze synergy in AI-generated designs
  python3 scripts/mtg_synergy.py generated_cards.txt

  # Find synergistic pairs with at least 5 occurrences
  python3 scripts/mtg_synergy.py data/AllPrintings.json --min-freq 5

  # Compare synergy between rarities
  python3 scripts/mtg_synergy.py data/AllPrintings.json --rarity common
  python3 scripts/mtg_synergy.py data/AllPrintings.json --rarity rare
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). Defaults to stdin (-). '
                             'If data/AllPrintings.json exists, it is used automatically when run interactively.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the results. If not provided, results print to the console.')

    # Group: Analysis Options
    analysis_group = parser.add_argument_group('Analysis Options')
    analysis_group.add_argument('--min-freq', type=int, default=2,
                                help='Minimum number of co-occurrences required to report a pair (Default: 2).')
    analysis_group.add_argument('--top', type=int, default=20,
                                help='Number of top synergistic pairs to show (Default: 20).')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate a formatted table (Default for terminal).')
    fmt_group.add_argument('--json', action='store_true', help='Generate a JSON file.')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file.')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for AND logic.')
    filter_group.add_argument('--grep-name', action='append', help='Only include cards whose name matches a search pattern.')
    filter_group.add_argument('--grep-type', action='append', help='Only include cards whose typeline matches a search pattern.')
    filter_group.add_argument('--grep-text', action='append', help='Only include cards whose rules text matches a search pattern.')
    filter_group.add_argument('--grep-cost', action='append', help='Only include cards whose mana cost matches a search pattern.')
    filter_group.add_argument('--grep-pt', action='append', help='Only include cards whose power/toughness matches a search pattern.')
    filter_group.add_argument('--grep-loyalty', action='append', help='Only include cards whose loyalty/defense matches a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append', dest='vgrep',
                        help='Skip cards matching a search pattern. Use multiple times for OR logic.')
    filter_group.add_argument('--exclude-name', action='append', help='Exclude cards whose name matches a search pattern.')
    filter_group.add_argument('--exclude-type', action='append', help='Exclude cards whose typeline matches a search pattern.')
    filter_group.add_argument('--exclude-text', action='append', help='Exclude cards whose rules text matches a search pattern.')
    filter_group.add_argument('--exclude-cost', action='append', help='Exclude cards whose mana cost matches a search pattern.')
    filter_group.add_argument('--exclude-pt', action='append', help='Exclude cards whose power/toughness matches a search pattern.')
    filter_group.add_argument('--exclude-loyalty', action='append', help='Exclude cards whose loyalty/defense matches a search pattern.')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
    filter_group.add_argument('--colors', action='append', help='Only include cards of specific colors.')
    filter_group.add_argument('--identity', action='append', help='Only include cards with specific color identities.')
    filter_group.add_argument('--id-count', action='append', help='Only include cards with specific color identity counts.')
    filter_group.add_argument('--cmc', action='append', help='Only include cards with specific CMC values.')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow', help='Only include cards with specific Power values.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou', help='Only include cards with specific Toughness values.')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy', help='Only include cards with specific Loyalty or Defense values.')
    filter_group.add_argument('--mechanic', action='append', help='Only include cards with specific mechanics.')
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck', help='Filter cards using a standard MTG decklist file.')
    filter_group.add_argument('--booster', type=int, default=0, help='Simulate opening N booster packs.')
    filter_group.add_argument('--box', type=int, default=0, help='Simulate opening N booster boxes.')
    filter_group.add_argument('--limit', type=int, default=0, help='Only process the first N cards.')
    filter_group.add_argument('--sample', type=int, default=0, help='Pick N random cards.')
    filter_group.add_argument('--seed', type=int, help='Seed for the random number generator.')

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
        default_data = 'data/AllPrintings.json'
        if os.path.exists(default_data):
            args.infile = default_data

    # Load cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, vgrep=args.vgrep,
                                  grep_name=args.grep_name, vgrep_name=args.exclude_name,
                                  grep_types=args.grep_type, vgrep_types=args.exclude_type,
                                  grep_text=args.grep_text, vgrep_text=args.exclude_text,
                                  grep_cost=args.grep_cost, vgrep_cost=args.exclude_cost,
                                  grep_pt=args.grep_pt, vgrep_pt=args.exclude_pt,
                                  grep_loyalty=args.grep_loyalty, vgrep_loyalty=args.exclude_loyalty,
                                  sets=args.set, rarities=args.rarity,
                                  colors=args.colors, cmcs=args.cmc,
                                  pows=args.pow, tous=args.tou, loys=args.loy,
                                  mechanics=args.mechanic,
                                  identities=args.identity, id_counts=args.id_count,
                                  decklist_file=args.deck,
                                  booster=args.booster, box=args.box,
                                  shuffle=(args.sample > 0 or args.limit > 0),
                                  seed=args.seed)
    if args.sample > 0:
        cards = cards[:args.sample]
    elif args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Analysis
    density_dist, ind_counts, pair_counts, synergy_results = calculate_synergy(cards, min_freq=args.min_freq)

    # Sort synergy by Lift (descending)
    synergy_results.sort(key=lambda x: x['lift'], reverse=True)

    # Format output
    if not (args.json or args.csv or args.table):
        if args.outfile:
            if args.outfile.endswith('.json'): args.json = True
            elif args.outfile.endswith('.csv'): args.csv = True
            else: args.table = True
        else:
            args.table = True

    use_color = args.color if args.color is not None else (sys.stdout.isatty() and not (args.json or args.csv))

    output_f = open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout

    try:
        if args.json:
            result = {
                'total_cards': len(cards),
                'density_distribution': {str(k): v for k, v in density_dist.items()},
                'synergy_pairs': synergy_results
            }
            output_f.write(json.dumps(result, indent=2) + '\n')
            return

        if args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Mechanic 1', 'Mechanic 2', 'Count', 'Lift', 'P(A&B)'])
            for r in synergy_results:
                m1, m2 = r['pair']
                writer.writerow([m1, m2, r['count'], f"{r['lift']:.2f}", f"{r['p_a_and_b']:.4f}"])
            return

        # Table Output
        utils.print_header("MECHANICAL SYNERGY ANALYSIS", count=len(cards), use_color=use_color, file=output_f)

        # 1. Density Distribution
        print(f"  {datalib.color_line('Mechanical Density (Mechanics per Card):', use_color)}", file=output_f)
        d_header = ["Mechanics", "Cards", "Percent", "Distribution"]
        if use_color:
            d_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in d_header]

        d_rows = [d_header]
        max_density = max(density_dist.keys()) if density_dist else 0
        for i in range(max_density + 1):
            count = density_dist.get(i, 0)
            percent = (count / len(cards) * 100)
            bar = datalib.get_bar_chart(percent, use_color, color=utils.Ansi.CYAN)
            d_rows.append([str(i), str(count), f"{percent:5.1f}%", bar])

        datalib.add_separator_row(d_rows)
        datalib.printrows(datalib.padrows(d_rows, aligns=['r', 'r', 'r', 'l']), indent=4, file=output_f)
        print("", file=output_f)

        # 2. Top Synergistic Pairs
        print(f"  {datalib.color_line('Top Synergistic Pairs (by Lift):', use_color)}", file=output_f)
        s_header = ["Mechanic Pair", "Count", "Lift Score", "Description"]
        if use_color:
            s_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in s_header]

        s_rows = [s_header]
        for r in synergy_results[:args.top]:
            m1, m2 = r['pair']
            pair_str = f"{m1} + {m2}"
            if use_color:
                pair_str = f"{utils.colorize(m1, utils.Ansi.CYAN)} + {utils.colorize(m2, utils.Ansi.CYAN)}"

            lift = r['lift']
            lift_str = f"{lift:6.2f}"
            if use_color:
                if lift > 2.0: lift_str = utils.colorize(lift_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
                elif lift < 1.0: lift_str = utils.colorize(lift_str, utils.Ansi.RED)

            desc = "Strong Synergy" if lift > 2.0 else ("Synergistic" if lift > 1.2 else "Expected")
            if lift < 0.8: desc = "Interference"

            s_rows.append([pair_str, str(r['count']), lift_str, desc])

        datalib.add_separator_row(s_rows)
        datalib.printrows(datalib.padrows(s_rows, aligns=['l', 'r', 'r', 'l']), indent=4, file=output_f)

    finally:
        if args.outfile:
            output_f.close()

if __name__ == "__main__":
    main()
