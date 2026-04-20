#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv
from statistics import mean

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib
import transforms

def main():
    parser = argparse.ArgumentParser(
        description="Analyze and rank Magic: The Gathering cards by design complexity.",
        epilog='''
Complexity is calculated using a heuristic score:
  - Words: 1 pt each
  - Lines: 5 pts each
  - Mechanics: 8 pts each
  - Color Identity: 3 pts per color
  - X-cost/effect: +10 pts
  - Multi-faced: +25 pts (Transform, Split, etc.)

This helps identify "Complexity Creep" in generated datasets.
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (MTGJSON, Scryfall, CSV, XML, MSE, or encoded text). Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the results. If not provided, results print to the console.')

    # Group: Analysis Options
    analysis_group = parser.add_argument_group('Analysis Options')
    analysis_group.add_argument('-t', '--top', type=int, default=20,
                                help='Number of top complex cards to display in the ranking table (Default: 20).')
    analysis_group.add_argument('--sort', choices=['complexity', 'name', 'cmc'], default='complexity',
                                help='Primary sort for the ranking table (Default: complexity).')
    analysis_group.add_argument('--reverse', action='store_true', help='Reverse the sort order.')

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
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck', help='Filter cards using a standard MTG decklist file.')
    filter_group.add_argument('--limit', type=int, default=0, help='Only process the first N cards.')
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
                                  decklist_file=args.deck,
                                  shuffle=args.limit > 0, seed=args.seed)

    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Calculate scores and sort
    results = []
    for card in cards:
        # Title case the name for better reporting
        display_name = cardlib.titlecase(transforms.name_unpass_1_dashes(card.name))
        results.append({
            'name': display_name,
            'score': card.complexity_score,
            'cmc': card.cost.cmc,
            'type': card.get_type_line(separator='-'),
            'words': card.total_words,
            'lines': card.total_lines,
            'mechanics': len(card.mechanics),
            '_card': card # Internal use for colorization
        })

    # Primary sort
    if args.sort == 'complexity':
        results.sort(key=lambda x: x['score'], reverse=not args.reverse)
    elif args.sort == 'name':
        results.sort(key=lambda x: x['name'].lower(), reverse=args.reverse)
    elif args.sort == 'cmc':
        results.sort(key=lambda x: x['cmc'], reverse=not args.reverse)

    # Stats
    scores = [r['score'] for r in results]
    avg_score = mean(scores)
    max_score = max(scores)
    min_score = min(scores)

    # Output
    output_f = sys.stdout
    if args.outfile:
        if args.verbose:
            print(f"Writing results to: {args.outfile}", file=sys.stderr)
        output_f = open(args.outfile, 'w', encoding='utf-8')

    try:
        if args.json:
            # Clean up internal fields for JSON output
            json_results = []
            for r in results:
                rj = r.copy()
                del rj['_card']
                json_results.append(rj)

            out_data = {
                'summary': {
                    'count': len(json_results),
                    'average': round(avg_score, 2),
                    'max': max_score,
                    'min': min_score
                },
                'cards': json_results
            }
            output_f.write(json.dumps(out_data, indent=2) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Name', 'Score', 'CMC', 'Words', 'Lines', 'Mechanics', 'Type'])
            for r in results:
                writer.writerow([r['name'], r['score'], r['cmc'], r['words'], r['lines'], r['mechanics'], r['type']])
        else:
            # Table
            header = ["Rank", "Name", "Score", "Words", "Lines", "Mech", "Type"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]
            display_count = min(len(results), args.top)
            for i in range(display_count):
                r = results[i]
                rank = str(i + 1)
                name = r['name']
                score = str(r['score'])
                words = str(r['words'])
                lines = str(r['lines'])
                mech = str(r['mechanics'])
                ctype = r['type']

                if use_color:
                    rank = utils.colorize(rank, utils.Ansi.CYAN)
                    name = utils.colorize(name, r['_card']._get_ansi_color())
                    score = utils.colorize(score, utils.Ansi.BOLD + (utils.Ansi.RED if r['score'] > 50 else utils.Ansi.GREEN))
                    ctype = utils.colorize(ctype, utils.Ansi.GREEN)

                rows.append([rank, name, score, words, lines, mech, ctype])

            datalib.add_separator_row(rows)

            title = "CARD COMPLEXITY RANKING"
            print(utils.colorize(title, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE) if use_color else f"=== {title} ===")
            datalib.printrows(datalib.padrows(rows, aligns=['r', 'l', 'r', 'r', 'r', 'r', 'l']), indent=2)

            print("\n  " + (utils.colorize("DATASET STATISTICS", utils.Ansi.BOLD + utils.Ansi.CYAN) if use_color else "--- DATASET STATISTICS ---"))
            print(f"    Total Cards: {len(results)}")
            print(f"    Average Score: {avg_score:.2f}")
            print(f"    Highest Score: {max_score}")
            print(f"    Lowest Score:  {min_score}")

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Complexity Analysis", len(cards), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
