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
from titlecase import titlecase

def main():
    parser = argparse.ArgumentParser(
        description="Profile the 10 primary two-color archetypes in a card dataset. "
                    "Identifies signpost cards, mechanical themes, and curve statistics for each pair.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Two-color archetypes analyzed:
  Allied: WU (Azorius), UB (Dimir), BR (Rakdos), RG (Gruul), GW (Selesnya)
  Enemy: WB (Orzhov), UR (Izzet), BG (Golgari), RW (Boros), GU (Simic)

Usage Examples:
  # Analyze archetypes in a specific set
  python3 scripts/mtg_archetypes.py data/AllPrintings.json --set MOM

  # Compare mechanics of a generated dataset against archetypes
  python3 scripts/mtg_archetypes.py generated_cards.txt
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). Defaults to stdin (-). '
                             'If stdin is a terminal, it attempts to use data/AllPrintings.json.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the analysis results. If not provided, results print to the console.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate a formatted table (Default for terminal).')
    fmt_group.add_argument('--json', action='store_true', help='Generate a JSON file (Auto-detected for .json).')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file (Auto-detected for .csv).')

    # Group: Analysis Options
    analysis_group = parser.add_argument_group('Analysis Options')
    analysis_group.add_argument('--min-cards', type=int, default=5,
                                help='Minimum number of cards required to profile an archetype (Default: 5).')
    analysis_group.add_argument('--top-mechanics', type=int, default=3,
                                help='Number of signature mechanics to show per archetype (Default: 3).')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for AND logic.')
    filter_group.add_argument('--grep-name', action='append',
                        help='Only include cards whose name matches a search pattern.')
    filter_group.add_argument('--grep-type', action='append',
                        help='Only include cards whose typeline matches a search pattern.')
    filter_group.add_argument('--grep-text', action='append',
                        help='Only include cards whose rules text matches a search pattern.')
    filter_group.add_argument('--grep-cost', action='append',
                        help='Only include cards whose mana cost matches a search pattern.')
    filter_group.add_argument('--grep-pt', action='append',
                        help='Only include cards whose power/toughness matches a search pattern.')
    filter_group.add_argument('--grep-loyalty', action='append',
                        help='Only include cards whose loyalty/defense matches a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append',
                        help='Skip cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for OR logic.')
    filter_group.add_argument('--exclude-name', action='append',
                        help='Exclude cards whose name matches a search pattern.')
    filter_group.add_argument('--exclude-type', action='append',
                        help='Exclude cards whose typeline matches a search pattern.')
    filter_group.add_argument('--exclude-text', action='append',
                        help='Exclude cards whose rules text matches a search pattern.')
    filter_group.add_argument('--exclude-cost', action='append',
                        help='Exclude cards whose mana cost matches a search pattern.')
    filter_group.add_argument('--exclude-pt', action='append',
                        help='Exclude cards whose power/toughness matches a search pattern.')
    filter_group.add_argument('--exclude-loyalty', action='append',
                        help='Exclude cards whose loyalty/defense matches a search pattern.')
    filter_group.add_argument('--set', action='append',
                        help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities. Supports full names (e.g., 'common', 'mythic') or shorthands: O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), L (Basic Land). Supports multiple values (OR logic).")
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G). Use 'C' or 'A' for colorless. Supports multiple values (OR logic).")
    filter_group.add_argument('--identity', action='append',
                        help="Only include cards with specific colors in their color identity (W, U, B, R, G). Use 'C' or 'A' for colorless. Supports multiple values (OR logic).")
    filter_group.add_argument('--id-count', action='append',
                        help='Only include cards with specific color identity counts. Supports inequalities, ranges, and multiple values (OR logic).')
    filter_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC (Converted Mana Cost) values. Supports inequalities (e.g., ">3", "<=2"), ranges (e.g., "1-4"), and multiple values (OR logic).')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow',
                        help='Only include cards with specific Power values. Supports inequalities, ranges, and multiple values (OR logic).')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou',
                        help='Only include cards with specific Toughness values. Supports inequalities, ranges, and multiple values (OR logic).')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy',
                        help='Only include cards with specific Loyalty or Defense values. Supports inequalities, ranges, and multiple values (OR logic).')
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanical features or keyword abilities (e.g., Flying, Activated, ETB Effect). Supports multiple values (OR logic).')
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file.')
    filter_group.add_argument('--booster', type=int, default=0,
                        help='Simulate opening N booster packs and search their contents.')
    filter_group.add_argument('--box', type=int, default=0,
                        help='Simulate opening N booster boxes (36 packs each) and search their contents.')
    filter_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    filter_group.add_argument('--shuffle', action='store_true',
                        help='Shuffle the cards before processing.')
    filter_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards (shorthand for --shuffle --limit N).')
    filter_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')

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
            if not getattr(args, 'quiet', False):
                print(f"Notice: Using default dataset: {args.infile}", file=sys.stderr)
        elif os.path.exists('data/AllPrintings.json'):
            args.infile = 'data/AllPrintings.json'
            if not getattr(args, 'quiet', False):
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
                                  shuffle=args.shuffle, seed=args.seed,
                                  booster=args.booster, box=args.box)

    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Define the 10 color pairs (alphabetically sorted to match card.color_identity)
    pairs = ["UW", "BU", "BR", "GR", "GW", "BW", "RU", "BG", "RW", "GU"]

    # Friendly labels for display
    pair_labels = {
        "UW": "WU (Azorius)", "BU": "UB (Dimir)", "BR": "BR (Rakdos)",
        "GR": "RG (Gruul)", "GW": "GW (Selesnya)", "BW": "WB (Orzhov)",
        "RU": "UR (Izzet)", "BG": "BG (Golgari)", "RW": "RW (Boros)", "GU": "GU (Simic)"
    }

    # Archetype buckets: {pair: [cards]}
    archetypes = {p: [] for p in pairs}

    # Global mechanic frequency
    global_mechanics = Counter()
    total_cards = len(cards)

    for card in cards:
        # Calculate global mechanic frequency
        for m in card.mechanics:
            global_mechanics[m] += 1

        # Assign to archetype buckets based on color identity
        identity = card.color_identity
        if len(identity) == 2:
            if identity in archetypes:
                archetypes[identity].append(card)
        elif len(identity) == 1:
            # For monocolored cards, add them to all archetypes that include their color
            for p in pairs:
                if identity in p:
                    archetypes[p].append(card)
        elif not identity:
            # Colorless cards support all archetypes? Usually better to skip them for specific archetype profiling
            # unless they are widely used. For now, we only profile color-affiliated cards.
            pass

    # Filter out empty archetypes or those with too few cards
    active_pairs = [p for p in pairs if len(archetypes[p]) >= max(1, args.min_cards)]

    if not active_pairs:
        if not args.quiet:
            print(f"Insufficient data to profile archetypes (minimum {args.min_cards} cards required per pair).", file=sys.stderr)
        return

    # Profile each archetype
    results = []

    for p in active_pairs:
        p_cards = archetypes[p]
        p_count = len(p_cards)

        # 1. Identify Signpost (Multicolored Uncommon)
        signpost = "None"
        uncommons = [c for c in p_cards if c.rarity == utils.rarity_uncommon_marker and len(c.color_identity) == 2]
        if uncommons:
            # Pick the first one as representative
            signpost = titlecase(uncommons[0].name)

        # 2. Calculate Signature Mechanics (Distinctiveness)
        p_mechanics = Counter()
        for c in p_cards:
            for m in c.mechanics:
                p_mechanics[m] += 1

        # Score = (Freq in Pair / Total in Pair) / (Freq Global / Total Global)
        distinctiveness = {}
        for m, count in p_mechanics.items():
            pair_prop = count / p_count
            global_prop = global_mechanics[m] / total_cards
            if global_prop > 0:
                distinctiveness[m] = pair_prop / global_prop

        top_m = sorted(distinctiveness.keys(), key=lambda m: (distinctiveness[m], p_mechanics[m]), reverse=True)[:args.top_mechanics]

        # 3. Curve Statistics
        avg_cmc = sum(c.cost.cmc for c in p_cards) / p_count
        creature_count = sum(1 for c in p_cards if c.is_creature)
        creature_pct = (creature_count / p_count * 100)

        results.append({
            "pair": p,
            "label": pair_labels[p],
            "count": p_count,
            "signpost": signpost,
            "mechanics": top_m,
            "avg_cmc": avg_cmc,
            "creature_pct": creature_pct
        })

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
            writer.writerow(['Archetype', 'Cards', 'Signpost Card', 'Top Mechanics', 'Avg CMC', 'Creature %'])
            for r in results:
                writer.writerow([
                    r['label'],
                    r['count'],
                    r['signpost'],
                    ", ".join(r['mechanics']),
                    f"{r['avg_cmc']:.2f}",
                    f"{r['creature_pct']:.1f}%"
                ])
        else:
            # Table Output
            utils.print_header("ARCHETYPE PROFILING", use_color=use_color, file=output_f)
            print(f"  Total cards analyzed: {total_cards}\n", file=output_f)

            header = ["Archetype", "Cards", "Signpost Card", "Top Mechanics", "Avg CMC", "Creature %", "Distribution"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]

            for r in results:
                label = r['label']
                signpost = r['signpost']
                mechanic_str = ", ".join(r['mechanics'])

                if use_color:
                    # Colorize the WU/UB/etc part of the label
                    code = label.split()[0]
                    name = " ".join(label.split()[1:])
                    colored_code = "".join([utils.colorize(c, utils.Ansi.get_color_color(c)) for c in code])
                    label = f"{colored_code} {name}"

                    signpost = utils.colorize(signpost, utils.Ansi.BOLD + utils.Ansi.CYAN) if signpost != "None" else signpost
                    mechanic_str = utils.colorize(mechanic_str, utils.Ansi.CYAN)

                bar = datalib.get_bar_chart(r['creature_pct'], use_color, color=utils.Ansi.GREEN)

                rows.append([
                    label,
                    datalib.color_count(r['count'], use_color),
                    signpost,
                    mechanic_str,
                    f"{r['avg_cmc']:.2f}",
                    f"{r['creature_pct']:5.1f}%",
                    bar
                ])

            datalib.add_separator_row(rows)
            datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'l', 'l', 'r', 'r', 'l']), indent=2, file=output_f)

            if not args.quiet:
                utils.print_operation_summary("Archetype Analysis", total_cards, 0, quiet=args.quiet)
    finally:
        if args.outfile:
            output_f.close()

if __name__ == "__main__":
    main()
