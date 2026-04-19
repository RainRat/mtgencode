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
import transforms

def calculate_complexity(card):
    """
    Calculates a heuristic complexity score for a card.

    Heuristic:
    - 1 point per word in rules text.
    - 5 points per line of rules text.
    - 8 points per unique recognized mechanic.
    - 3 points per color in color identity.
    - 10 points if the card has an X in its mana cost.
    - 25 points bonus for multi-faced cards (Splits, Transforms, etc.).
    """
    score = 0

    # 1. Text Complexity (Words and Lines)
    # We use the unpassed text to get a better sense of human-readable complexity
    text = card.get_text(force_unpass=True)
    words = text.split()
    score += len(words)

    lines = [l for l in text.split('\n') if l.strip()]
    score += len(lines) * 5

    # 2. Mechanical Complexity
    mechanics = card.mechanics
    score += len(mechanics) * 8

    # 3. Mana/Color Complexity
    identity = card.color_identity
    score += len(identity) * 3

    if 'X' in card.cost.encode():
        score += 10

    # 4. Structural Complexity
    if card.bside:
        score += 25
        # Note: card.mechanics and card.color_identity already include b-side data
        # so we don't need to recursively call calculate_complexity for b-side
        # unless we want to sum word/line counts manually.

        # Add b-side words and lines
        b_text = card.bside.get_text(force_unpass=True)
        b_words = b_text.split()
        score += len(b_words)

        b_lines = [l for l in b_text.split('\n') if l.strip()]
        score += len(b_lines) * 5

        if 'X' in card.bside.cost.encode():
            score += 10

    return score

def main():
    parser = argparse.ArgumentParser(
        description="Analyze the 'Complexity Score' of Magic cards in a dataset.",
        epilog='''
Complexity Score is a heuristic metric combining text density, mechanical frequency,
structural properties, and mana complexity. It helps identify "complexity creep"
and evaluate the cognitive load of cards.
'''
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (MTGJSON, Scryfall, CSV, XML, MSE, or encoded text). Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the results. If not provided, results print to the console.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate a formatted table and summary (Default for terminal).')
    fmt_group.add_argument('--json', action='store_true', help='Generate a JSON file (Auto-detected for .json).')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file (Auto-detected for .csv).')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-t', '--top', type=int, default=10,
                        help='Limit the number of cards shown in the "Most Complex" table (Default: 10).')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Randomize card order before analysis.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards.')
    proc_group.add_argument('--seed', type=int, help='Seed for random generator.')

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
                                  booster=args.booster, box=args.box,
                                  shuffle=args.shuffle, seed=args.seed)

    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Analyze complexity
    results = []
    total_score = 0
    for card in cards:
        score = calculate_complexity(card)
        total_score += score
        results.append({
            'name': cardlib.titlecase(transforms.name_unpass_1_dashes(card.name)),
            'summary': card.summary(ansi_color=False),
            'score': score,
            'rarity': card.rarity_name
        })

    # Sort by complexity
    results.sort(key=lambda x: x['score'], reverse=True)

    avg_score = total_score / len(cards)
    median_score = results[len(results)//2]['score']

    # Output
    output_f = sys.stdout
    if args.outfile:
        if args.verbose:
            print(f"Writing results to: {args.outfile}", file=sys.stderr)
        output_f = open(args.outfile, 'w', encoding='utf-8')

    try:
        if args.json:
            out_data = {
                'average': avg_score,
                'median': median_score,
                'cards': results
            }
            output_f.write(json.dumps(out_data, indent=2) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Name', 'Score', 'Rarity', 'Summary'])
            for r in results:
                writer.writerow([r['name'], r['score'], r['rarity'], r['summary']])
        else:
            # Table
            header = ["Complexity", "Card Name", "Rarity", "One-line Summary"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]
            for r in results[:args.top]:
                score_str = datalib.color_count(r['score'], use_color, utils.Ansi.BOLD + utils.Ansi.RED if r['score'] > 100 else utils.Ansi.BOLD + utils.Ansi.YELLOW)
                name_str = utils.colorize(r['name'], utils.Ansi.BOLD) if use_color else r['name']
                rarity_str = r['rarity']
                if use_color:
                    rarity_str = utils.colorize(rarity_str, utils.Ansi.get_rarity_color(rarity_str))

                rows.append([score_str, name_str, rarity_str, r['summary']])

            datalib.add_separator_row(rows)

            title = "CARD COMPLEXITY ANALYSIS"
            print(utils.colorize(title, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE) if use_color else f"=== {title} ===")

            summary_header = f"  Average Complexity: {avg_score:.2f}  |  Median Complexity: {median_score:.2f}  |  Total Cards: {len(cards)}"
            print(utils.colorize(summary_header, utils.Ansi.BOLD + utils.Ansi.GREEN) if use_color else summary_header)
            print()

            print(f"  Most Complex Cards (Top {args.top}):")
            datalib.printrows(datalib.padrows(rows, aligns=['r', 'l', 'l', 'l']), indent=2)

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Complexity Analysis", len(cards), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
