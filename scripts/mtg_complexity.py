#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib
from titlecase import titlecase

def main():
    parser = argparse.ArgumentParser(
        description="Analyze the design complexity of cards in a dataset. This tool calculates a 'Complexity Score' to help identify 'wordy' or mechanically dense cards.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The Complexity Score is a heuristic that measures how difficult a card is to read and understand. Higher scores indicate "wordier" cards or those with many mechanical features.

How the score is calculated:
  - Each word in the rules text: +1 point
  - Each line of rules text: +5 points
  - Each identified mechanic (e.g., Flying, Kicker): +8 points
  - Each color in the card's color identity: +3 points
  - If the card has an X in its cost or effect: +10 points
  - If the card has multiple faces (like Split or Transform cards): +25 points

Usage Examples:
  # Find the 10 most complex cards in the March of the Machine set
  python3 scripts/mtg_complexity.py data/AllPrintings.json --set MOM --limit 10

  # Quickly find wordy cards using the default dataset
  python3 scripts/mtg_complexity.py "Dragon"

  # Compare the average complexity of commons vs. rares
  python3 scripts/mtg_complexity.py data/AllPrintings.json --rarity common --rarity rare

  # Analyze the complexity of Blue cards with CMC 4 or more
  python3 scripts/mtg_complexity.py data/AllPrintings.json --colors U --cmc ">=4"

  # Find wordy cards that mention "Goblins"
  python3 scripts/mtg_complexity.py -g "Goblin"
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, MSE, or encoded text) or directory. '
                             'If this is not a valid path, it is treated as a search pattern (--grep). '
                             'Defaults to stdin (-). If stdin is a TTY, AllPrintings.json is used if available.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the results. If not provided, results print to the console.')
    io_group.add_argument('-n', '--limit', type=int, default=20,
                        help='Number of top complex cards to show in the table (Default: 20).')
    io_group.add_argument('-j', '--json', action='store_true', help='Output results in structured JSON format.')
    io_group.add_argument('--csv', action='store_true', help='Output results in CSV format.')

    # Group: Filtering Options
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
                        help='Only include cards from specific sets (e.g., MOM, MRD). Supports multiple sets (OR logic).')
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

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Shuffle the cards before processing.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards (shorthand for --shuffle --limit N).')
    proc_group.add_argument('--seed', type=int,
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
    # If the user provides a single argument that isn't a file, treat it as a search query.
    if args.infile and args.infile != '-' and not os.path.exists(args.infile) and not args.outfile:
        if not args.grep:
            args.grep = [args.infile]
        else:
            args.grep.append(args.infile)
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

    # Handle --sample
    if args.sample > 0:
        args.shuffle = True
        # Note: mtg_complexity uses --limit for the table display,
        # but mtg_open_file doesn't take limit.
        # We'll use a local limit for processing.
        process_limit = args.sample
    else:
        process_limit = 0

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty() and not (args.json or args.csv):
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

    if process_limit > 0:
        cards = cards[:process_limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Sort cards by complexity score (descending)
    sorted_cards = sorted(cards, key=lambda c: c.complexity_score, reverse=True)

    # Calculate global averages
    total_score = sum(c.complexity_score for c in cards)
    avg_score = total_score / len(cards)

    # Averages by Rarity
    rarity_stats = {}
    for c in cards:
        r = c.rarity_name
        if r not in rarity_stats:
            rarity_stats[r] = []
        rarity_stats[r].append(c.complexity_score)

    rarity_avg = {r: sum(scores)/len(scores) for r, scores in rarity_stats.items()}

    # Averages by Color Identity
    color_stats = {}
    for c in cards:
        ci = c.color_identity if c.color_identity else 'A'
        if ci not in color_stats:
            color_stats[ci] = []
        color_stats[ci].append(c.complexity_score)

    color_avg = {ci: sum(scores)/len(scores) for ci, scores in color_stats.items()}

    # Set up output writer
    output_f = sys.stdout
    if args.outfile:
        if args.verbose:
            print(f"Writing results to: {args.outfile}", file=sys.stderr)
        output_f = open(args.outfile, 'w', encoding='utf-8')

    try:
        if args.json:
            result = {
                'average_complexity': avg_score,
                'by_rarity': rarity_avg,
                'by_color': color_avg,
                'top_cards': [
                    {
                        'name': cardlib.titlecase(c.name.replace(utils.dash_marker, '-')),
                        'complexity': c.complexity_score,
                        'rarity': c.rarity_name,
                        'type': c.get_type_line()
                    } for c in sorted_cards[:args.limit]
                ]
            }
            output_f.write(json.dumps(result, indent=2) + '\n')
            return

        if args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Name', 'Complexity', 'Rarity', 'Type'])
            for c in sorted_cards[:args.limit]:
                writer.writerow([
                    cardlib.titlecase(c.name.replace(utils.dash_marker, '-')),
                    c.complexity_score,
                    c.rarity_name,
                    c.get_type_line()
                ])
            return

        # Terminal Output
        utils.print_header("COMPLEXITY ANALYSIS", count=len(cards), use_color=use_color, file=output_f)

        avg_str = f"Average Complexity Score: {avg_score:.2f}"
        if use_color:
            avg_str = utils.colorize(avg_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
        output_f.write(f"  {avg_str}\n\n")

        # Top Cards Table
        output_f.write(f"  {datalib.color_line('Top Complex Cards:', use_color)}\n")
        header = ['Name', 'Score', 'Rarity', 'Type']
        if use_color:
            header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

        rows = [header]
        for c in sorted_cards[:args.limit]:
            name = cardlib.titlecase(c.name.replace(utils.dash_marker, '-'))
            if use_color:
                name = utils.colorize(name, c._get_ansi_color())

            score = str(c.complexity_score)
            if use_color:
                score = utils.colorize(score, utils.Ansi.BOLD + utils.Ansi.MAGENTA)

            rarity = c.rarity_name
            if use_color:
                rarity = utils.colorize(rarity, utils.Ansi.get_rarity_color(rarity))

            rows.append([name, score, rarity, c.get_type_line()])

        datalib.add_separator_row(rows)
        datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'l', 'l']), indent=4, file=output_f)
        output_f.write('\n')

        # Rarity Averages Table
        output_f.write(f"  {datalib.color_line('Average Complexity by Rarity:', use_color)}\n")
        rarity_header = ['Rarity', 'Avg Score', 'Count']
        if use_color:
            rarity_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in rarity_header]

        r_rows = [rarity_header]
        # Priority sort rarities
        rarity_order = {'mythic': 0, 'rare': 1, 'uncommon': 2, 'common': 3, 'basic land': 4, 'special': 5}
        sorted_rarities = sorted(rarity_avg.keys(), key=lambda r: rarity_order.get(r.lower(), 6))

        for r in sorted_rarities:
            display_r = r
            if use_color:
                display_r = utils.colorize(r, utils.Ansi.get_rarity_color(r))
            r_rows.append([display_r, f"{rarity_avg[r]:.2f}", str(len(rarity_stats[r]))])

        datalib.add_separator_row(r_rows)
        datalib.printrows(datalib.padrows(r_rows, aligns=['l', 'r', 'r']), indent=4, file=output_f)
        output_f.write('\n')

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Complexity Analysis", len(cards), 0)

if __name__ == "__main__":
    main()
